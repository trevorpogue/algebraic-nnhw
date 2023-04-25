from nnhw.top import (
    AttrDict, IJParam2, IntEnum, MNKParam, FIPMethod, nameof, prod,
    varname, Pool, tilepad, sign_extend, LowerStrEnum, auto, noinit, ppstr,
    PP, int_range, IO, IOs, Device, DTYPE, Mapping, tohex, IJParam,
    Cin, Cout, H, Hin, Hout, K, M, N, W, tile_count, tile_fill, tilepad,
    IOItems, MappedIOTensors, IOTensors, LayerType, Level, print_begin_end)
import torch
from torch import Tensor
from math import ceil, sqrt
from copy import copy, deepcopy
from itertools import chain
import typing as typ
from typing import Any, Iterator, Iterable, List
from attrs import define, asdict, Factory
from random import randrange
from nnhw import instruc
from debug import log
import numpy as np
from nnhw.arith import Layer
from nnhw.top.cfg import config
from nnhw.rxtx.device_controller import DeviceController


device_controller = DeviceController()


@define
class NN(list):
    device: Device = noinit(Device)
    position: int = noinit(0)
    parent_size: int = noinit(1)
    total_sections: int = noinit(1)
    section_takes_input: List[bool] = noinit(list)
    section_batch_sizes: List[int] = noinit(list)
    first_layer_positions_for_each_section: List[int] = noinit(list)
    linear_inputs: Tensor = None
    compiler: Any = None
    input_load_pos: int = None
    batch_pos: int = None

    @property
    def total_layers(self) -> int: return len(self)
    @property
    def model_instruc_name(self) -> str: return f'nn{self.position}_model'
    @property
    def reset_instruc_name(self) -> str: return f'reset'
    @property
    def isfirst(self): return self.position == 0
    @property
    def islast(self): return self.position >= self.parent_size - 1
    def full_instruc_name(self, i) -> str: return f'full{i}'

    def control_instruc_name(self, nn_section_i=0) -> str:
        return f'nn{self.position}_control{nn_section_i}'

    def inference_instruc_name(self, batch_i=0) -> str:
        return f'nn_input{batch_i}'

    def __init__(self, *args):
        list.__init__(self, args)
        self.total_sections = 1
        self.section_takes_input = [True]
        self.section_batch_sizes = [self[0].batch_size]
        self.first_layer_positions_for_each_section = [0]
        self.input_load_pos: int = config.input_load_pos
        self.batch_pos: int = 0

    def shallow_copy(self, layers: 'NN' = None):
        if layers is None:
            layers = self
        cp = NN(*layers)
        cp.device = self.device
        cp.position = self.position
        cp.parent_size = self.parent_size
        cp.total_sections = self.total_sections
        cp.section_takes_input = self.section_takes_input
        cp.section_batch_sizes = self.section_batch_sizes
        cp.first_layer_positions_for_each_section = (
            self.first_layer_positions_for_each_section)
        return cp


    def __getitem__(self, k: Any) -> Layer: return super().__getitem__(k)
    def __iter__(self) -> 'NN': return super().__iter__()
    def __next__(self) -> Layer: return super().__next__()

    def compile_input(self, x=None, batch_i=0):
        layer = self[0].copy(is_a_padder=True)
        device = copy(self.device)
        layer.Cin = x.size(1)
        nn = self.__class__(layer)
        nn.finalize(device, log_en=False)
        layer = nn[0]
        original_x = x
        x = layer.pad_input(x)
        padded_x = x
        layer.expected.torch.a = x.detach().clone()
        layer.update_mem()
        layer.mem.remap(Mapping.DEVICE)
        instruc_x = layer.mem.device_a_mod
        x = self[0].pad_input(original_x)
        self[0].expected.torch.a = x
        self[0].update_mem()
        self._post_finalize(log_en=False, batch_i=batch_i)
        from nnhw.instruc import Encoder, regs
        instrucs = [instruc.Layerio(instruc_x),
                    instruc.Write2Reg(regs.TIMEOUT_BIT, 31),
                    ]
        from timeit import default_timer as timer
        start = timer()
        if not config.istest:
            Encoder()(instrucs, self.inference_instruc_name(batch_i), self.device)
        end = timer()

    def __call__(self, x=None):
        if not len(self):
            return x
        if x is None:
            x = self[0].partsel_io_cin(IO.A)
        self._run(x)

    def drive_instruc(self, instruc_fname, islast=False, sync=False):
        # if not sync:
        log(f'sending {instruc_fname}', show_context=False)
        if islast:
            x = device_controller.rxtx(instruc_fname, sync)
            return x
        else:
            device_controller.tx(instruc_fname, sync)
        import time

    def send_instrucs(self, sync=False):
        nn = self
        self.drive_instruc(nn.full_instruc_name(0), False, True)
        return self.drive_instruc(nn.full_instruc_name(1), True, True)
        self.drive_instruc(nn.reset_instruc_name, sync=sync)
        self.drive_instruc(nn.control_instruc_name(), sync=sync)
        if nn.total_sections > 1:
            self.drive_instruc(nn.control_instruc_name(2), sync=sync)
        self.drive_instruc(nn.model_instruc_name, sync=sync)
        batch_size = nn[0].batch_size
        result = None
        for section in range(min(nn.total_sections, 2)):
            for i in range(nn.section_batch_sizes[section]):
                if (i > 0) or (section > 0):
                    islast_instruc = nn.total_sections > 1 and section > 0
                    result = self.drive_instruc(nn.control_instruc_name(
                        section), islast_instruc, sync=sync)
                if nn.section_takes_input[section]:
                    islast_instruc = nn.total_sections == 1
                    res = self.drive_instruc(
                        nn.inference_instruc_name(i), islast_instruc,
                        sync=sync)
                    if islast_instruc:
                        result = res
        return result

    def _run(self, x, ):
        if config.onboard:
            data = self.send_instrucs(sync=False)
        else:
            data = torch.zeros((4000,), dtype=self.device.atype)
        nn = self
        c = nn[-1].expected.torch.c
        batch_size = nn[0].batch_size
        print('scoring data')
        nn = self[-1]
        itr = [nn] if list(config.ios2score) == [IO.RESULT] else self
        passed = True
        log.ln()
        read_perf_results = config.read_perf_results
        x = data
        for layer in itr:
            total_ios_size = layer.set_ios_from_1d_tensor(x)
            x = x[total_ios_size:].clone()
            msg, passed_ = layer.score()
            passed = passed and passed_
            if msg:
                log(f'{msg}', max_nof_lines=-1, show_context=False)
        msg = 'PASSED' if passed else 'FAILED'
        log.ln()
        log(f'{msg}')
        return self[-1].expected.torch.c

    def compile(self, device, save=True):
        self.device = device
        self.finalize(device)
        from nnhw.instruc.compiler import Compiler
        self.compiler = Compiler(device=device)
        self.compiler(self, save=save)
        return self

    def finalize(self, device: Device, log_en=True):
        dummy_last_layer = Layer()
        self.append(dummy_last_layer)
        prev_layer = None
        for i, layer in enumerate(self):
            self._finalize_layer(
                layer, i, len(self) - 1, prev_layer, device)
            prev_layer = layer
        first_linear_layer = None
        for layer in self:
            if layer.islinear:
                first_linear_layer = layer
                break
        if first_linear_layer:
            layer = first_linear_layer.prev
            self.linear_inputs = torch.zeros((
                self[0].batch_size, layer.Cout, layer.HWs_ef.c.i,
                layer.HWs_ef.c.j), dtype=device.atype)
        self._post_finalize(log_en=True)
        self.pop(-1)

    def flatten_io(self, layer, io):
        ios = layer.expected.torch
        if config.debuglevels.program is Level.MAX and io is IO.A:
            log(ios[io].size())
            log(tohex(ios[io]))
        ios[io] = ios[io].flatten(1)
        for i in range(2):
            ios[io] = ios[io].unsqueeze(-1)
        ios[io] = ios[io].contiguous()
        if io is IO.A:
            strides = list(ios[io].stride())
            sizes = list(ios[io].size())
            strides[-1] = 0
            sizes[-1] = self.device.min_tile_size_m
            ios[io] = ios[io].as_strided(sizes, strides)
        if config.debuglevels.program is Level.MAX and io is IO.A:
            log(ios[io].size())
            log(ios[io].stride())
            log(tohex(ios[io]))

    def _post_finalize(self, log_en=True, batch_i=0):
        log_en = True
        prev_layer = None
        for i, layer in enumerate(self):
            if prev_layer is not None:
                c = prev_layer.expected.torch.c
                if layer.is_second_linear_after_conv:
                    c = c.permute(0, 1, 3, 2)
                layer.expected.torch.a = c
            if layer.is_first_linear_after_conv:
                sz = layer.parent[0].batch_size
                c = prev_layer.expected.torch.c
                self.linear_inputs[batch_i] = c[0]
                c = self.linear_inputs[-1].unsqueeze(0)
                for i in reversed(range(sz-1)):
                    c = torch.cat((self.linear_inputs[i].unsqueeze(0), c), 2)
                layer.expected.torch.a = c
            layer.post_finalize(log_en)
            if not config.fast:
                if layer.position < layer.parent_size:
                    layer.compute_expected_outputs()
            if prev_layer is not None:
                prev_layer.next = layer
            prev_layer = layer
            if log_en and layer.position < layer.parent_size and (
                    config.debuglevels.mem and not layer.is_a_padder):
                layer.mem._debuglogging()

    def _finalize_layer(
            self, layer: Layer, position, parent_size, prev_layer: Layer,
            device: Device):
        layer.parent = self
        layer.config = config
        layer.position = position
        layer.parent_size = parent_size
        layer.device = copy(device)
        layer.prev = prev_layer
        layer.pre_finalize()
        layer.rdmem = 0
        layer.wrmem = 0
        if layer.position >= 1:
            layer.rdmem = 1
            layer.prev.wrmem = 1
        if layer.residual:
            layer.rdmem = layer.residual
        if prev_layer is not None:
            layer.original_cin = layer.prev.original_cout
        else:
            layer.original_cin = layer.Cin
        if layer.islinear:
            if (layer.prev.islinear and not layer.prev.prev.islinear):
                layer.prev.wrmem = 0
                layer.rdmem = 0
            if layer.prev is not None and not layer.prev.islinear:
                layer.prev.wrmem = 2
                layer.rdmem = 2
                self.total_sections = 3
                self.section_takes_input += [False]
                self.section_batch_sizes += [1]
                self.first_layer_positions_for_each_section += [layer.position]
            if not layer.prev or not layer.prev.islinear:
                final_hin = ceil(sqrt(layer.min_tile_size_m))
                layer.padding = ceil((final_hin - 1) / 2)
        if prev_layer is not None:
            prev_layer.c_padding = layer.padding
            layer.padding = 0
            prev_layer.finalize()
            layer.original_hin = prev_layer.HWs_ef.pooling.i
            layer.Hin = prev_layer.HWs_ef.c.i
            layer.Win = prev_layer.HWs_ef.c.j
            layer.Cin = prev_layer.Cout
        elif layer.padding > 0:
            layer.original_hin = layer.Hin
            layer.Hin += layer.padding * 2
            layer.Win += layer.padding * 2
            layer.padding = 0
        else:
            layer.original_hin = layer.Hin
        layer.original_cout = layer.Cout
        if layer.is_first_linear_after_conv:
            layer.Hin *= layer.parent[0].batch_size
        if layer.is_second_linear_after_conv:
            layer.Win = layer.Hin
            layer.Hin = 1
        if layer.islinear and not layer.is_a_padder:
            if not layer.prev:
                layer.kernel_size = layer.original_hin
            elif not layer.prev.islinear:
                layer.kernel_size = layer.prev.HWs_ef.pooling.i
                layer.stride = layer.prev.HWs_ef.pooling.i
            else:
                layer.kernel_size = 1
        if layer.position == len(self)-1:
            layer.finalize()

    def __str__(self):
        import sections
        s = ''
        s = f'{self.__class__}('
        for layer in self:
            s += str(layer)[:-1]
        s = s + ')\n'
        return s


def _isnn(obj): return isinstance(obj, NN)


@define
class Program(list):
    input: Tensor = noinit()
    @property
    def batch_size(self): return self.layers[0].batch_size
    @property
    def total_layers(self): return sum(map(len, self.nns))
    @property
    def total_conv_layers(self):
        x = 0
        for layer in self.layers:
            if not layer.islinear:
                x += 1
        return x
    @property
    def total_linear_layers(self):
        x = 0
        for layer in self.layers:
            if layer.islinear:
                x += 1
        return x
    @property
    def layers(self): return list(chain(*self.nns))
    @property
    def nns(self) -> Iterable[NN]: return list(filter(_isnn, self))

    def __call__(self, x: Tensor = None):
        nns = self.nns
        for nn in nns:
            x = nn(x)
        layer = self.layers[-1]
        if layer.config.read_perf_results:
            if len(layer.config.perf_counters) > 1:
                self.read_perf_counters(layer.config.perf_counters)
            else:
                self.read_perf_counter(layer.config.perf_counters)
        return x

    def copy(self, device, batch_i=0):
        layers = []
        for layer in self.layers:
            layers.append(layer.copy())
        prev_layer = None
        for layer in layers:
            if prev_layer:
                layer.padding = prev_layer.c_padding
                prev_layer.c_padding = 0
            prev_layer = layer
        cpy = self.__class__(*layers)
        cpy = cpy.finalize(device)
        for orig, cp in zip(self.layers, cpy.layers):
            cp.pgp_fields = orig.pgp_fields
            ios = copy(IOs.ALL)
            ios = dict(zip(ios, ios))
            for io in ios:
                for tensors in ['expected', 'optimized']:
                    for mapping in [Mapping.TORCH, Mapping.DEVICE]:
                        cp[tensors][mapping][io] = orig[tensors][mapping][
                            io].detach().clone()
        for orig, cp in zip(self.nns, cpy.nns):
            cp.device = orig.device
        cpy[0].batch_pos = batch_i
        return cpy

    def read_perf_counter(self, counters=None):
        bs = config.batch_size
        if not isinstance(bs, list):
            bs = [bs]
        for batch_size in bs:
            self._read_perf_counter(counters, batch_size)

    def _read_perf_counter(self, counters=None, batch_size=1):
        if counters is not None:
            ccs = counters[0]
        from nnhw.top.cfg import device
        ops_est = 0
        ops = 0
        nn = self[0]
        for i in range(self.total_conv_layers):
            layer: Layer = nn[i]
            ops += layer.ops()
            ops_est += layer.ops_inefficient()
        ops *= batch_size
        ops_est *= batch_size
        first_linear_pos = i + 1
        clock_freq = config.freq * 1e6
        for i in range(self.total_linear_layers):
            layer = nn[i + first_linear_pos]
            ops += layer.ops()
            ops_est += layer.ops_inefficient()
        ccs_est = ops_est / prod(device.MXU_SIZE)
        instd_macs_without_quant = (prod(device.MXU_SIZE) + device.MXU_SZJ) / 2
        instd_macs_with_quant = instd_macs_without_quant + device.MXU_SZJ
        dsp_rows_penalty = instd_macs_with_quant / instd_macs_without_quant
        SZJ = device.MXU_SZJ
        input_time = prod(self.layers[0].expected.torch.a.size())*SZJ/48/4/16
        perfect_ccs = ops / prod(device.MXU_SIZE)
        period = 1/clock_freq
        if counters is None:
            ccs = ccs_est
        time = ccs * period
        gops = ops * 2 / time / 1e9
        ops_ps_roof = prod(device.MXU_SIZE) * clock_freq * 2 /1e9
        inferences_ps = batch_size / time
        clock_freq /= 1e6
        ops = ops/1e9
        kwds = dict(context=False)
        log.ln()
        s = (
            f'{config.max_model.__name__}, '
            f'{device.LAYERIO_WIDTH}b, '
            f'{SZJ}x{SZJ}, '
            f'fmax={clock_freq}, '
            f'batch_size={batch_size}, '
        )
        s = s[:-2]
        log(f'{s}', **kwds)
        # log(device.FIP_METHOD, value_only=True)
        gops_per_dsp = gops/instd_macs_with_quant*2
        log(f'GOPS            = {gops}', **kwds)
        # log(f'GOPS/DSP        = {gops_per_dsp}', **kwds)
        # log(f'###############', **kwds)
        # **kwds)
        # log(f'GOP/s roof      = {ops_ps_roof}', **kwds)
        # log(f'inferences/s    = {inferences_ps}', **kwds)
        # log(time, **kwds)
        # log(f'Goperations     = {ops}', **kwds)
        # log(f'efficiency      = {perfect_ccs / ccs / dsp_rows_penalty}', **kwds)
        log(f'efficiency      = {gops / ops_ps_roof}', **kwds)
        # log(ccs, context=False, **kwds)
        # log(perfect_ccs, context=False, **kwds)
        # log(batch_size, context=False, **kwds), **kwds

    def read_perf_counters(self, counters):
        """Read perf counters for all layers"""
        log(counters)
        counters_ = counters
        counters = []
        for cc in counters_:
            if cc:
                counters.append(cc)
        counters = counters[-len(self.layers):]
        if len(counters) < len(self.layers):
            log('modifying counters')
            counters.append(counters[-1])
            counters.append(counters[-1])
            counters = counters[1:]
        prev_cc = 0
        ccs = []
        for cc in counters:
            ccs.append(cc-prev_cc)
            prev_cc = cc
        for layer, cc in zip(self.layers, ccs):
            log(layer.efficiency(cc))
        total_ops = 0
        for layer in self.layers:
            device: Device = layer.device
            total_ops += layer.ops()
        log(total_ops)
        s = 0
        for layer in self.layers:
            log(layer.ops() / total_ops)
            s += layer.ops() / total_ops
        log(s)
        perfect_ccs = total_ops / prod(device.MXU_SIZE)
        log(perfect_ccs)
        log(counters)
        log(perfect_ccs / counters[-1])

    def compile_input(self, device, x=None, batch_i=0):
        layer0 = self.nns[0][0]
        batch_size = layer0.batch_size
        if x is not None:
            batch_size = x.size(0)
        else:
            assert False
        self.nns[0].compile_input(x[0].unsqueeze(0), batch_i)

    def finalize(self, device, save=True):
        for i, nn in enumerate(self.nns):
            nn.position = i
            nn.parent_size = len(self)
        [nn.finalize(device) for nn in self.nns]
        return self

    def compile(self, device, save=True):
        for i, nn in enumerate(self.nns):
            nn.position = i
            nn.parent_size = len(self)
        [nn.compile(device, save) for nn in self.nns]
        return self

    def load(self):
        from nnhw.rxtx.device_controller import DeviceController
        device_controller = DeviceController()
        nn = self.nns[0]
        log(f'sending nn {nn.control_instruc_name}', value_only=True)
        device_controller.tx(nn.control_instruc_name)
        log(f'sending nn {nn.model_instruc_name}', value_only=True)
        device_controller.load_nn(nn.model_instruc_name)

    def __init__(self, *args):
        superlist = []
        nn = []
        for arg in args:
            if isinstance(arg, Layer):
                nn.append(arg)
            else:
                if len(nn):
                    superlist.append(NN(*nn))
                    nn = []
                superlist.append(arg)
        if len(nn):
            superlist.append(NN(*nn))
            nn = []
        list.__init__(self, superlist)
    def __next__(self) -> NN: return super().__next__()

    def __str__(self):
        result = ''
        for seqitem in self:
            result += f'{seqitem}'
        return result

    def nns_str(self):
        result = ''
        for seqitem in self.nns:
            result += f'{seqitem}'
        return result
