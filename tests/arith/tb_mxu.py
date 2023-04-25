import math
from nnhw.top.cfg import config
import typing as typ
from math import ceil
import torch
from cocotb.triggers import Event
from debug import log
from nnhw.top import (
    FIPMethod, nameof, varname, IO, IOs, Device, DTYPE, Mapping,
    K, M, N, tile_count, tile_fill, tohex)
from tests import arith, top
from tests.arith.tb_pe import Monitor as PeMonitor
from tests.top import uvm
from tests.top.tb_utils.tb_triangle_buf import Monitor as TriangleMonitor


class MatMul(top.SequenceItem):
    def __init__(self, *args, **attrs):
        top.SequenceItem.__init__(self, *args, **attrs)
        self.MAX_M = 2 * self.SZI  # only used to set a watchdog timeout
        self.MIN_M = math.ceil(2 * self.SZI) if self.SZI == 4 else (
            math.ceil(1.5 * self.SZI))
        self.data_attrs = []

    def int_range(self, width, signed: bool):
        if signed:
            return (-2 ** (width-1), 2 ** (width-1) - 1)
        else:
            return (0, 2 ** (width))

    def __repr__(self): return str(self)

    def __str__(self):
        s = ''
        s += '{\n'
        for k in self.data_attrs:
            s += f"{repr(k)}:\n{getattr(self, k)},\n"
        s += '}'
        return s


class Monitor(top.Monitor):
    def __init__(self, *args, **attrs):
        top.Monitor.__init__(self, *args, **attrs)
        self.autoscore = attrs.get(varname(), True)

    async def sample_seqitem_input(self, seqitem):
        for iokey in IO.__members__:
            self.fork(self.sample_seqitem_io(seqitem, iokey))

    async def sample_seqitem_io(self, seqitem, iokey, tile_sizes=None,
                                tile_i=None):
        if tile_sizes is None:
            tile_sizes = seqitem.tile_sizes
        do_logging = True
        do_logging = False
        if do_logging:
            log(f'{iokey} sampling begin')
            log(tile_sizes)
        if iokey in IOs.OUTPUTS:
            await self.sample_seqitem_output(seqitem, iokey, tile_sizes,
                                             tile_i)
        else:
            await self._sample_input(seqitem, iokey, tile_sizes, tile_i)
        if do_logging:
            log(f'{iokey} sampling end')

    async def _sample_input(self, seqitem, iokey, tile_sizes, tile_i):
        await self.wait_for_prev_call_to_finish(iokey)
        WIDTH = config.device.WIDTHS[iokey]
        input = self.bus[iokey]
        if iokey in [IO.A]:
            MN = tile_sizes[M]
        else:
            MN = tile_sizes[N]
        await self.sample_input(seqitem, iokey, input, WIDTH, MN, tile_sizes,
                                 tile_i)

    async def sample_input(self, seqitem, iokey, input, WIDTH, MN, tile_sizes,
                           tile_i):
        K_ = tile_sizes[K]
        if iokey == IO.POST_GEMM_PARAMS:
            K_ = 1
        for mn in range(MN):
            dvec = []
            await self.wait_(self.bus[iokey].info.valid)
            for k in range(K_):
                if iokey == IO.POST_GEMM_PARAMS:
                    d = self.sample(input.value)
                else:
                    d = self.sample(input.value[k])
                if config.device.SIGNED[iokey]:
                    d = arith.sign_extend(d, WIDTH)
                dvec.insert(0, d)
            t = torch.tensor(dvec, dtype=torch.uint8)
            await self.clkcycle
            tensor = torch.tensor([dvec], dtype=DTYPE)
            self.cat_tensors(iokey, seqitem, tensor, tile_i, mn)
        self.call_finished(iokey)

    def cat_tensors(self, iokey, seqitem, tensor_cat, tile_i, mn):
        tensor = seqitem.observed[Mapping.DEVICE][iokey]
        if tile_i is None:
            seqitem.observed[Mapping.DEVICE][iokey] = (
                torch.cat((tensor, tensor_cat), 0) if tensor.size(0)
                else tensor_cat)
        else:
            tensor[tile_i][mn] = tensor_cat.squeeze(0)

    async def sample_seqitem_output(
            self, seqitem, iokey, tile_sizes, tile_i=None):
        await self.wait_for_prev_call_to_finish(iokey)
        output = self.bus[iokey]
        if getattr(self, 'scoring', False):
            output = self.dut.arith_u.gemm_u.mxu_
            await super().wait_(output.info.new_tile_k)
        d = config.device
        ts = tile_sizes
        tsn = ts[N]
        M_ = tile_sizes[M]
        N_ = tsn
        for mn in range(M_):
            qvec = []
            await self.wait_(output.info.valid)
            for i in range(N_):
                q = (self.sample(output.value[i])
                     & (2**config.device.WIDTHS[iokey]-1))
                if config.device.SIGNED[iokey]:
                    q = arith.sign_extend(q, config.device.WIDTHS[iokey])
                qvec.insert(0, q)
            tensor_cat = torch.tensor([qvec], dtype=DTYPE)
            self.cat_tensors(iokey, seqitem, tensor_cat, tile_i, mn)
            await self.clkcycle
        if getattr(self, 'scoring', False):
            self.score(seqitem, iokey)
        self.call_finished(iokey)

    def score(self, seqitem, c_key='c'):
        if not self.autoscore:
            return
        expected = seqitem.copy()
        setattr(expected, c_key, self.scoreboard(seqitem))
        msg = f'\nobserved:\n{seqitem},\nexpected {c_key}:\n'
        msg += f'{getattr(expected, c_key)}\n\n'
        top.Monitor.score(
            self, torch.equal(getattr(expected, c_key),
                              getattr(seqitem, c_key), ), msg)
