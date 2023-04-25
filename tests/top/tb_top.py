import random
from nnhw.arith import Layer, NN
from nnhw.top.main import main
from nnhw.top.cfg import config, device
from typing import List, Dict, Any
from cocotb.triggers import Event
from copy import deepcopy
from enum import auto
from math import ceil
import torch
from cocotb import fork
from debug import log
import nnhw
from nnhw import instruc
from nnhw.instruc import (Encoder)
from nnhw.rxtx import DeviceController
from nnhw.top import (
    AttrDict, IJParam, IntEnum, MNKParam, FIPMethod, nameof, prod,
    varname, Pool, args2attrs, IO, IOs, Device, DTYPE,
    Cin, Cout, H, Hin, Hout, K, M, N, W, tile_count, tile_fill, Mapping,
    StrEnum, LowerStrEnum, tohex, noinit, tilepad, print_begin_end_async)
from tests import arith, top
from tests.arith import tb_mxu
from tests.instruc import tb_instruc
from tests.top import uvm
from attrs import define, field, Factory, asdict
from utils import run
from nnhw.arith.matmul import MatMulScoreboard
import numpy as np


main()


@define
class Clock(AttrDict):
    freq: float = noinit()  # in MHz
    period: int = noinit()  # in ns
    delay: int = noinit()  # in ns
    ratio: float = noinit(1)  # how much slower it is compared to top clk
    signal: Any = noinit()  # cocotb signal


@define
class Clocks(AttrDict):
    top: Clock = noinit(Factory(Clock))
    clk50: Clock = noinit(Factory(Clock))
    layeriomem: Clock = noinit(Factory(Clock))
    weightmem: Clock = noinit(Factory(Clock))
    quantization: Clock = noinit(Factory(Clock))
    pooling: Clock = noinit(Factory(Clock))
    padding: Clock = noinit(Factory(Clock))
    instruc: Clock = noinit(Factory(Clock))
    rxtx: Clock = noinit(Factory(Clock))
    pll_ref: Clock = noinit(Factory(Clock))

    @classmethod
    def from_dut(cls, dut):
        self = cls()
        # clock names
        Clk = LowerStrEnum(varname(), ' '.join(Clocks()).upper())
        CLKS = Clk.__members__.values()
        SPECIAL_CLKS = [Clk.RXTX, Clk.PLL_REF, Clk.CLK50]
        self = Clocks()
        self.top.period = self.clk_nsperiod_from_mhzfreq(
            dut.TOP_CLK_FREQ_.value)
        self.top.freq = self.clk_mhzfreq_from_nsperiod(
            self.top.period)
        for k in CLKS:
            k: str = k
            if k not in [Clk.TOP, Clk.CLK50]:
                self[k].signal = getattr(
                    dut, k.lower() + '_clk')
            if k not in [Clk.TOP, *SPECIAL_CLKS]:
                self[k].freq = getattr(
                    dut, k.upper() + '_CLK_FREQ_').value
        self.top.signal = dut.clk
        self.clk50.signal = dut.CLK_50M_FPGA
        for k in CLKS:
            if k not in SPECIAL_CLKS:
                self[k].period = self.clk_nsperiod_from_mhzfreq(
                    self[k].freq)
                # period is rounded so have to update frequency after
                self[k].freq = self.clk_mhzfreq_from_nsperiod(
                    self[k].period)
        #
        self.rxtx.period = self.top.period + 3
        self.pll_ref.period = self.top.period + 2
        self.clk50.period = 20
        for clk in SPECIAL_CLKS:
            self[clk].freq = self.clk_mhzfreq_from_nsperiod(self[clk].period)
        #
        delays = list(range(len(CLKS)-1))
        random.shuffle(delays)
        delays.insert(0, 0)
        for i, k in enumerate(CLKS):
            self[k].ratio = self.clk_ratio(k)
            self[k].delay = delays[i]
        return(self)

    def clk_nsperiod_from_mhzfreq(self, mhz_clk_freq):
        result = round(1/mhz_clk_freq*1e3)
        result = result + (result % 2)
        return result

    def clk_mhzfreq_from_nsperiod(self, ns_clk_period):
        return 1/ns_clk_period*1e3

    def clk_ratio(self, clk_key):
        return self[clk_key].period / self.top.period


# clock names
Clk = LowerStrEnum(varname(), ' '.join(Clocks()).upper())
CLKS = Clk.__members__.values()

# Clocks who's frequency isn't know / can't be referenced in dut:
SPECIAL_CLKS = [Clk.RXTX, Clk.PLL_REF, Clk.CLK50]


class Scoreboard(top.Scoreboard, arith.Component):
    def __init__(self, *args, **attrs):
        top.Scoreboard.__init__(self, *args, **attrs)
        arith.Component.__init__(self, *args, **attrs)

    def __call__(self, seqitem):
        return MatMulScoreboard()(seqitem.a, seqitem.b)


class Monitor(top.Monitor):

    def __init__(self, *args, **attrs):
        top.Monitor.__init__(self, *args, Scoreboard, **attrs)
        self.cleanup(attrs)
        self.mxu_monitors = AttrDict()
        self.mxu_scorers = AttrDict()
        self.programs = main.programs
        attrs.pop(nameof(self.clk_period))
        for io in IOs.ALL:
            # didn't design mxu_monitor with different clocks in mind,
            # so have instantiate one for each clock for now
            self.mxu_monitors[io] = tb_mxu.Monitor(
                *args, tb_mxu.MatMul, **attrs,
                name=f'mxu_monitors[{io}]',
                autosample=False,
                autoscore=False,
                clk_period=self.clks[self.iokey2clk_mapping(io)].period,
               )
            self.mxu_scorers[io] = tb_mxu.Monitor(
                *args, tb_mxu.MatMul, **attrs,
                name=f'mxu_scorers[{io}]',
                autosample=False,
                autoscore=False,
                scoring=True,
                clk_period=self.clks[self.iokey2clk_mapping(io)].period,
               )
        self.batches = AttrDict(dict(current=0, sampled=0))
        self.layers = AttrDict(dict(current=0, sampled=0))
        self.score_on_timeout = True

    def iokey2clk_mapping(self, io) -> Clk:
        return Clk.TOP

    def next_layer(self, key):
        self.programs[self.batches[key]]
        layer: Layer = self.programs[self.batches[key]].layers[
            self.layers[key]]
        self.layers[key] += 1
        last_in_batch = self.batches[key] == (main.program.batch_size - 1)
        last_conv_layer_b4_linear = (
            not layer.islinear
            and (layer.islast or (layer.next and layer.next.islinear)))
        last_layer_in_last_batch = last_in_batch and layer.islast
        if last_conv_layer_b4_linear and not last_in_batch:
            self.batches[key] += 1
            self.layers[key] = 0
        if last_layer_in_last_batch:
            self.layers[key] = 0
            self.batches[key] = 0
        return layer

    @print_begin_end_async
    async def sample_seqitem_input(self, _):
        layer = self.next_layer('current')
        forks = []
        if config.score_from_result_fifo:
            if not hasattr(self, 'initted_result_fifo_sampling'):
                for nn in main.program.nns:
                    forks.append(self.fork(self.sample_result_fifo(nn)))
            self.initted_result_fifo_sampling = True
        else:
            forks.append(self.fork(self.sample_inputs(layer)))
            forks.append(self.fork(self.sample_outputs(layer)))
        self.fork(self.wait_for_sampling_to_finish(forks))

    def add_linear_ios_to_all_programs(self):
        for program in self.programs[:-1]:
            for layer in program.layers:
                if layer.section > 1:
                    orig = self.programs[-1].layers[layer.position]
                    for io in IOs.ALL:
                        for tensors in ['observed']:
                            for mapping in [Mapping.TORCH, Mapping.DEVICE]:
                                layer[tensors][mapping][io] = orig[tensors][
                                    mapping][io].detach().clone()

    async def wait_for_sampling_to_finish(self, forks):
        await self.join(*forks)
        await self.clkcycles(self.extra_ccs_at_end)
        if config.score_from_result_fifo:
            self.parse_result_fifo()
        if main.program.batch_size > 1:
            self.add_linear_ios_to_all_programs()
        self.score()

    @print_begin_end_async
    async def sample_outputs(self, layer):
        forks = []
        for i in range(layer.tile_counts[N]):
            forks.append(self.fork(self.sample_outputs_N_tile(layer, i)))
        await self.join(*forks)

    @print_begin_end_async
    async def sample_outputs_N_tile(self, layer: Layer, tile_i):
        forks = []
        for iokey in IOs.OUTPUTS:
            if iokey in layer.ios:
                forks.append(self.fork(self.sample_outputs_N_tile_io(
                    iokey, layer, tile_i)))
        await self.join(*forks)

    @print_begin_end_async
    async def sample_outputs_N_tile_io(self, iokey, layer, tile_i):
        d, ts = config.device, layer.tile_sizes
        tile_sizes = AttrDict({
            M: prod(layer.HWs[iokey]),
            N: layer.tile_sizes[N],
            K: layer.tile_sizes[K],})
        await self.mxu_monitors[iokey].sample_seqitem_io(
            layer, iokey, tile_sizes, tile_i)

    @print_begin_end_async
    async def sample_inputs(self, layer):
        forks = []
        for tile_i in range(layer.total_input_tiles):
            forks.append(self.fork(self.sample_io_tile_set(layer, tile_i)))

    @print_begin_end_async
    async def sample_io_tile_set(self, layer, tile_i):
        forks = []
        for iokey in IOs.INPUTS:
            if iokey in layer.ios:
                forks.append(self.fork(
                    self.mxu_monitors[iokey].sample_seqitem_io
                    (layer, iokey, tile_i=tile_i)))
        score_mxu = True
        score_mxu = False
        if score_mxu:
            for iokey in [IO.A, IO.B, IO.GEMM]:
                self.fork(
                    self.mxu_scorers[iokey].sample_seqitem_io(
                        tb_mxu.MatMul(
                            **self.attrs, tile_sizes=layer.tile_sizes),
                        iokey))

    @print_begin_end_async
    async def sample_result_fifo(self, nn: NN):
        await self.wait_for_prev_call_to_finish(nn.position)
        self.result = []
        while not bool(self.dut.resparser.result_parser_u.done.value):
            await self.wait_(self.dut.result.wrreq)
            for i in reversed(range(device.MXU_SIZE.i)):
                d = self.sample(self.dut.result.d.value[i])
            self.result.append(d)
            await self.clkcycle

    def parse_result_fifo(self):
        self.result = torch.tensor(self.result, dtype=torch.uint8)
        for layer in main.program.layers:
            total_ios_size = layer.set_ios_from_1d_tensor(self.result)
            self.result = self.result[total_ios_size:]

    def score(self):
        layer = self.next_layer('sampled')
        if not config.score_from_result_fifo:
            msg, passed = layer.score()
            msg += '\n'
            return top.Monitor.score(self, passed, msg)
        if hasattr(self, 'scored_result_fifo_sampling'):
            return
        for layer in main.program.layers:
            msg, passed = layer.score()
            msg += '\n'
            top.Monitor.score(self, passed, msg)
        self.scored_result_fifo_sampling = True


class Driver(tb_instruc.Driver):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.attrs = attrs

    async def main_phase(self, phase):
        await self.clk_posedge
        for i, nn in enumerate(main.program.nns):
            await self.drive_instruc(nn.full_instruc_name(0))
            await self.clk_posedges(100)
            await self.drive_instruc(nn.full_instruc_name(1))

    def bytes2word(self, bytes): return int.from_bytes(bytes[0:4], 'big')

    async def drive_instruc(self, instruc_fname):
        instruc_bytes = Encoder().read_back_encoded_instrucs(instruc_fname)
        byte_count = 0
        instruc_word_list = []
        log(f'sending {instruc_fname}', show_context=False)
        while byte_count < len(instruc_bytes):
            instruc_word_list += [self.bytes2word(instruc_bytes[
                byte_count:byte_count+4])]
            byte_count += 4
        for word in instruc_word_list:
            await self.drive_word(word)
        self.dut.rx.wrreq <= 0


class UnitTest(top.Test):
    def __init__(self, *args, **attrs):
        super().setattrs(**attrs)
        dir(self.dut)  # solves a cocotb bug when getting self.dut
        try:
            self.dut = self.set(attrs, self.dut.top[5].dut)
        except AttributeError:
            return
        self.attrs = attrs
        self.clks = self.set(self.attrs, Clocks.from_dut(self.dut))
        self.clk_period = self.set(attrs, self.clks.top.period)
        total_layers = (
            main.program.total_conv_layers * main.program.batch_size
            + main.program.total_linear_layers)
        self.total_seqitems = self.set(attrs, total_layers)
        self.log_en = self.set(attrs, False)
        self.log_en = self.set(attrs, True)
        tb_instruc.UnitTest.set_globals(self, attrs)
        self.set_bus(attrs)
        self.get_instrucs_from_file()
        self.extra_ccs_at_end = self.set(self.attrs, 100)
        max_ccs = self.calculate_needed_sim_time()
        self.max_clk_cycles = self.set(attrs, max_ccs)
        max_sim_time_nn_seconds = self.max_clk_cycles * self.clks.top.period
        log.raw(f'max_sim_time_nn_seconds = {max_sim_time_nn_seconds}\n')
        log.raw(f'self.clk_period = {self.clk_period}\n')
        super().uvm_init(Driver, Monitor, uvm.SequenceItem, *args, **attrs)

    def calculate_needed_sim_time(self):
        from nnhw.top.cfg import config
        if config.sim_max_time is not None:
            return config.sim_max_time / self.clks.top.period
        ccs = AttrDict()
        ccs.decode = self.total_instrucs_wordlen * self.clks.rxtx.ratio
        for iokey in IOs.OUTPUTS:
            ccs[iokey] = 0
        ccs.mem_read = 0
        ccs.unknown = 0
        ccs.mem_read += 250
        if True or config.score_from_result_fifo:
            ccs.result_parser = 0
            for layer in main.program.layers:
                for x in layer.expected.device.values():
                    ccs.result_parser += prod(x.size())
        for layer in main.program.layers:
            layer: Layer = layer
            ccs.gemm += device.MXU_SIZE.i * 12  # ccs.quantization += 60
            ccs.quantization += 52
            pooling_padding_lat = 13
            if layer.pool_padding:
                ccs.pool_padding += pooling_padding_lat
            if layer.pool_size:
                ccs.pooling += pooling_padding_lat
            if layer.c_padding:
                ccs.c += pooling_padding_lat
            #
            tile_size = self.dut.LAYERIOMEM_CLK_DIV_.value
            layeriomem_ratio = (
                (layer.tile_size_w
                 + tilepad(layer.tile_size_w, tile_size))
                / layer.tile_size_w
            )
            ccs.mem_read += layer.tile_sizes[M] * prod(
                layer.tile_counts.values()) * layeriomem_ratio
            ccs.pool_padding += (
                self.tensor_ccs(layer, IO.POOL_PADDING)
                - self.tensor_ccs(layer, IO.QUANTIZATION))
            if (self.tensor_ccs(layer, IO.POOLING)
                    != self.tensor_ccs(layer, IO.POOL_PADDING)):
                ccs.pooling += self.tensor_ccs(layer, IO.POOL_PADDING)
            ccs.c += (
                self.tensor_ccs(layer, IO.C)
                - self.tensor_ccs(layer, IO.POOLING))
        for iokey in IOs.OUTPUTS:
            if iokey == IO.GEMM:
                continue
            clk_key = Clk.POOLING if iokey in [
                IO.POOL_PADDING, IO.C] else iokey
            if iokey == IO.RESULT:
                clk_key = Clk.TOP
            ccs[iokey] *= self.clks[clk_key].ratio
        result = int(sum(ccs.values())) * config.sim_max_cc_mult_factor
        result += self.extra_ccs_at_end
        result *= main.program.layers[0].batch_size
        return result

    def tensor_ccs(self, layer, iokey, clk_key=Clk.TOP):
        return prod(list(layer.expected[Mapping.DEVICE][iokey].size())
                    ) / device.MXU_SIZE.j

    def set_bus(self, attrs):
        arith_u = self.dut.arith_u
        post_gemm_u = arith_u.post_gemm_u
        quantization_u = post_gemm_u.quantization_u
        try:
            pool_padding_u = post_gemm_u.gen_pool_padding.pool_padding_u
            pool_padding = pool_padding_u.sim.q_
        except AttributeError:
            pool_padding = quantization_u.sim.q_
        pooling_u = post_gemm_u.pooling_u
        c_padding_u = post_gemm_u.c_padding_u
        self.bus = self.set(
            attrs,
            uvm.Interface(inputs={
                IO.A: self.dut.layerio.q,
                IO.B: arith_u.b,
                IO.POST_GEMM_PARAMS: self.dut.post_gemm_params.q,
            }, outputs={
                IO.GEMM: arith_u.sim.gemm_c,
                IO.QUANTIZATION: quantization_u.sim.q_,
                IO.POOL_PADDING: pool_padding,
                IO.POOLING: pooling_u.sim.q_,
                IO.C: c_padding_u.sim.q_,
                IO.RESULT: self.dut.result.d,
            })
        )
        if (not config.score_from_result_fifo) and config.probe_result_io:
            self.bus[device.RESULT_IO] = self.dut.result.d

    async def reset_phase(self, phase):
        self.raise_objection(phase)
        for i, k in enumerate(CLKS):
            fork(self.always_clk(self.clks[k].signal,
                                 self.clks[k].period,
                                 delay=self.clks[k].delay,
                                 ))
        await super().reset_phase(phase)
        await self.clk_negedge
        self.dut.pb <= 255
        await self.clk_posedges(8)
        self.dut.pb <= 0
        await self.clk_posedges(2)
        self.dut.pb <= 255
        self.drop_objection(phase)

    def set_device_from_verilog(self):
        verilog_params = arith.VerilogParams(self.dut)
        for k in asdict(device):
            if k != nameof(device.SZJ):
                setattr(device, k, getattr(verilog_params, k))

    def get_instrucs_from_file(self):
        for nn in main.program.nns:
            instruc_bytes0 = Encoder().read_back_encoded_instrucs(
                nn.model_instruc_name)
            instruc_bytes1 = Encoder().read_back_encoded_instrucs(
                nn.control_instruc_name())
            instruc_bytes2 = Encoder().read_back_encoded_instrucs(
                nn.inference_instruc_name(0))
            self.total_instrucs_wordlen = len(
                instruc_bytes0) + len(instruc_bytes1) + len(instruc_bytes2)


class TopTest(uvm.GroupTest):
    UnitTest_ = UnitTest
