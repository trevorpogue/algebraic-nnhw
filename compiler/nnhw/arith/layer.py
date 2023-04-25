from nnhw.top import (
    AttrDict, IJParam2, IntEnum, MNKParam, FIPMethod, nameof, prod,
    varname, Pool, sign_extend, LowerStrEnum, auto, noinit, ppstr,
    PP, int_range, IO, IOs, Device, DTYPE, Mapping, tohex, IJParam,
    Cin, Cout, H, Hin, Hout, K, M, N, W, tile_count, tile_fill, tilepad,
    IOItems, MappedIOTensors, IOTensors, Level, fromself, LayerType,
    print_begin_end, init, clog2)
import torch
from torch import Tensor
from math import ceil
from copy import copy, deepcopy
from itertools import chain
import typing as typ
from typing import Any, Iterator, Iterable, List
from attrs import define, asdict, Factory
from random import randrange
from nnhw import instruc
from debug import log
import numpy as np
from nnhw.arith import scoreboard as scb
from nnhw.top.cfg import Config, config
from torch.nn import functional as F


@define
class Layer(AttrDict):
    batch_size: int = 1
    Cin: int = 1
    Cout: int = Factory(lambda self: self.Cin, takes_self=True)
    Hin: int = 1
    Win: int = Factory(lambda self: self.Hin, takes_self=True)
    kernel_size: int = 1
    stride: int = 1
    pool_size: int = 0
    pool_stride: int = 0
    pool_type: int = Pool.MAXPOOL2D
    padding: int = 0
    pool_padding: int = 0
    do_conv: bool = True
    do_relu: bool = True
    type: LayerType = LayerType.Conv2d
    #
    is_a_padder: bool = False
    m_tiling_succeeded: bool = noinit(False)
    device: Device = init()
    scoreboard: scb.LayerScoreboard = init()
    c_padding: int = 0
    position: int = noinit()
    parent_size: int = noinit()
    expected: MappedIOTensors = noinit(Factory(MappedIOTensors))
    observed: MappedIOTensors = noinit(Factory(MappedIOTensors))
    optimized: MappedIOTensors = noinit(Factory(MappedIOTensors))
    HWs_ef: IOItems = noinit(Factory(AttrDict))
    HWs: IOItems = noinit(Factory(AttrDict))
    mem: 'Mem' = noinit()
    prev: 'Layer' = noinit()
    next: 'Layer' = noinit()
    instrucs: instruc.Layer = noinit()
    #
    parent: Any = noinit()  # NN type
    tile_size_w: int = noinit(0)
    tile_counts: AttrDict = noinit()
    tile_sizes: AttrDict = noinit()
    ts_ef: AttrDict = noinit()  # effective tile size
    ts_0: AttrDict = noinit()  # original tile size
    ios: IOs = noinit(lambda: dict.fromkeys(IOs.ALL))
    #
    randomize_inputs: bool = True
    a: Tensor = init()
    b: Tensor = init()
    post_gemm_params: Tensor = init()
    c: Tensor = init()
    result: Tensor = init()
    from nnhw.top.quantization_parser import PostGemmParams
    pgp_fields: PostGemmParams = init()
    config: Config = init()
    original_hin: int = 0
    original_cin: int = 0
    original_cout: int = 0
    rdmem: int = 0  # layeriomem
    wrmem: int = 0  # layeriomem
    residual: int = 0  # layeriomem id
    special_size_m: bool = False

    @property
    def ts(self): return self.tile_sizes
    @property
    def tc(self): return self.tile_counts
    @property
    def a_padding(self): return self.padding
    @property
    def kernel_stride(self): return self.stride
    @property
    def isfirst(self): return self.position == 0
    @property
    def islast(self): return self.position >= self.parent_size - 1
    @property
    def total_input_tiles(self): return prod(self.tc.values())
    @property
    def islinear(self): return self.type is LayerType.Linear
    @property
    def section(self):
        nn = self.parent
        section = 0
        for i, position in enumerate(
                nn.first_layer_positions_for_each_section):
            if self.position >= position:
                section = i
        return section
    @property
    def isfirst_insection(self):
        nn = self.parent
        section = self.section
        positions = nn.first_layer_positions_for_each_section
        return self.position == positions[section]
    @property
    def islast_insection(self):
        nn = self.parent
        section = self.section
        positions = nn.first_layer_positions_for_each_section
        if len(positions) <= section + 1:
            return self.islast
        return self.position + 1 >= positions[section+1]
    @property
    def is_first_linear_after_conv(self):
        return (self.islinear
                and self.prev is not None
                and not self.prev.islinear)
    @property
    def is_second_linear_after_conv(self):
        return (self.islinear
                and self.prev is not None
                and self.prev.is_first_linear_after_conv)

    def copy(self, **overriding_attrs):
        cpy = self.__class__(
            Cin=self.Cin, Cout=self.Cout, Hin=self.Hin, Win=self.Win,
            batch_size=self.batch_size,
            kernel_size=self.kernel_size,
            stride=self.stride,
            pool_size=self.pool_size,
            pool_stride=self.pool_stride,
            pool_type=self.pool_type,
            padding=self.padding,
            c_padding=self.c_padding,
            pool_padding=self.pool_padding,
            do_conv=self.do_conv,
            do_relu=self.do_relu,
            scoreboard=scb.LayerScoreboard(device=self.device, layer=self),
            device=self.device,
            config=self.config,
            type=self.type, **overriding_attrs
        )
        return cpy

    def finalize(self):
        self.scoreboard = scb.LayerScoreboard(device=self.device, layer=self)
        self.instrucs = instruc.Layer.from_device(self.device)
        self._init_misc()
        self._init_HWs()
        self._init_tile_sizes()
        self._init_torch_inputs()
        self._init_pgps()
        self.ios = deepcopy(self.config.ios2score)
        if not self.islast:
            self.ios.pop(IO.RESULT, None)
        if not self.do_conv:
            for io in [IO.POST_GEMM_PARAMS, IO.GEMM, IO.QUANTIZATION, ]:
                self.ios.pop(io, None)

    def efficiency(self, ccs):
        if not ccs:
            return -1
        return self.ops() / prod(self.device.MXU_SIZE) / ccs

    def best_ops_for_mxu(self):
        result = prod(self.kernel_size)
        if not self.islinear:
            result *= prod(self.HWs_ef.gemm)
        result = (self.Cin * self.Cout * result)
        return result

    def ops_inefficient(self):
        gemm = self.HWs_ef.gemm
        ksize = self.kernel_size
        Cin = self.Cin
        dram_freq = 267
        device = self.device
        dut_freq = self.config.freq
        min_tile_size_n = max(device.MXU_SZI*1.5-1, 7)
        bspeed = device.MXU_SZI * dut_freq / dram_freq
        width = device.MXU_SZI * device.LAYERIO_WIDTH
        membw = config.bmembw
        while membw < width:
            bspeed *= 2
            width /= 2
        bspeed = max(min_tile_size_n, bspeed)
        rdpenalty = 1
        tsizem_mult = (gemm.j + (gemm.j % device.LAYERIOMEM_CLK_DIV))/gemm.j
        tszm = self.ts[M]
        aspeed = tszm * tsizem_mult
        rdpenalty = max(bspeed/tszm, aspeed/tszm)
        if self.is_first_linear_after_conv:
            rdpenalty = max(rdpenalty, (tszm * device.LAYERIOMEM_CLK_DIV)/tszm)
        Cout = self.Cout
        if self.position == 0 and self.config.use_layer1_optimization2:
            ksz = self.kernel_size.i
            ksz = ceil(ksz /self.kernel_stride.i)
            ksize = [ksz, ksz]
            Cin = device.MXU_SZJ
        result = prod(ksize) * gemm.i * gemm.j * Cin * Cout
        result *= rdpenalty
        return result

    def ops(self):
        ksize = self.kernel_size
        orig_cin = self.original_cin
        result = prod(ksize)
        result *= prod(self.HWs_ef.gemm)
        result = (orig_cin * self.original_cout * result)
        return result

    def map_output_torch2device(self, x):
        return self.scoreboard.map_output_torch2device(x)

    def score_visualization(self, io: IO):
        return scb.score_visualization(self, Mapping.DEVICE, io)

    def _init_pgps(self):
        kwds = dict(context=False, log_en=False)
        from nnhw.top.quantization_parser import PostGemmParams
        if self.randomize_inputs:
            self.pgp_fields = PostGemmParams(self.device).from_concatted_value(
                self.expected.torch.post_gemm_params)
            self.pgp_fields.m_shift = randrange(9, 16)
            self.pgp_fields.activation = int(self.do_relu)
            self.pgp_fields.finalize()
        self.post_gemm_params = self.pgp_fields.value
        self.expected.torch.post_gemm_params = self.pgp_fields.value

    def post_finalize(self, log_en=True):
        self.set_observed_ios_to_ones()
        for io in IOs.ALL:
            self.optimized.torch[io] = self.expected.torch[io]
        self.update_mem()
        d = self.device
        for exp in ['expected', 'observed']:
            for dvc in ['device', 'torch']:
                for io in IOs.ALL:
                    self[exp][dvc][io] = self[exp][dvc][io].to(d.dtypes[io])
        layer = self
        if self.position < self.parent_size:
            self._test(log_en)

    def set_values_to_indexes(self):
        self.set_a_values_to_indexes()
        self.set_b_values_to_indexes()

    sec_sel = 15

    def set_a_values_to_indexes(self, x=None):
        # for debugging
        if x is None:
            x = self.expected.torch.a
        szi = self.device.MXU_SZI
        szj = self.device.MXU_SZJ
        for cin, cx in enumerate(x[0]):
            for h, hx in enumerate(cx):
                for w, wx in enumerate(hx):
                    # x[0][cin][h][w] = (w*len(cx) + h)*16 + int(cin/szj)
                    sec = h + int(cin/szj)
                    # x[0][cin][h][w] = int(sec == self.sec_sel)
                    # gemm sections
                    # v = int(sec in [0, 3]) and not cin%4
                    v = sec
                    # v = int(sec == self.sec_sel)
                    # v = int(sec == 1)
                    # v = int(sec == 3)
                    # v = int(sec == 12)
                    # v += 1
                    v = 1
                    # v = 255
                    # v *= -1
                    # v = v * int(not cin%4)
                    x[0][cin][h][w] = v
        return x

    def set_b_values_to_indexes(self, x=None):
        # for debugging
        if x is None:
            x = self.expected.torch.b
        szi = self.device.MXU_SZI
        szj = self.device.MXU_SZJ
        for cout, coutx in enumerate(x):
            for cin, cinx in enumerate(coutx):
                for h, hx in enumerate(cinx):
                    for w, wx in enumerate(hx):
                        v = x[cout][cin][h][w]
                        x[cout][cin][h][w] = sum([
                            int(cin / szj),
                            int(cout / szi)*2,
                            h, w, 1,
                        ]) * -1
                        x[cout][cin][h][w] = sum([
                            # int(cin),
                            int(cout/szj),
                        ])
                        # sec = int((cout>=4)) + int(cin/szj)*2
                        # sec = int((cout>=4))*2 + int(cin/szj)
                        sec = int(cout/szi) + int(cin/szj)
                        # x[cout][cin][h][w] = int(sec == self.sec_sel)
                        # v = sec  # gemm
                        v = sec
                        # v = int(sec == self.sec_sel)
                        # v = int(sec == 2)
                        # v = int(sec == 12)
                        # v = int(sec == 3)
                        # v += 1
                        v = 1
                        # v *= -1
                        # v = gemm_sec  # gemm sections
                        # v = v * int(not cin%4)
                        # v *= 255
                        x[cout][cin][h][w] = v
        return x

    def __str__(self):
        cpy = AttrDict()
        print_using_sections = False
        hws = AttrDict()
        for k, v in self.HWs.items():
            hws[k] = list(v.values())
        tileparams = dict()
        for dim in [M, N, K]:
            for d in [self.tc, self.ts]:
                v = d[dim]
                if tileparams.get(dim):
                    tileparams[dim.value] += f'|{v}'
                else:
                    tileparams[dim.value] = str(v)
        kernel = dict(kernel=dict(size=self.kernel_size.i,
                                  stride=self.stride.j))
        cpy.type = self.type.value
        cpy.channels = dict(Cin=self.Cin, Cout=self.Cout)
        cpy.kernel = kernel
        cpy.HWs = str(hws) if print_using_sections else hws
        cpy.tileparams = tileparams
        cpy.position = dict(position=f'{self.position+1}/{self.parent_size}')
        cpy.original_cin = {varname(), getattr(self, varname())}
        cpy.original_cout = {varname(), getattr(self, varname())}
        if print_using_sections:
            s = str(cpy)
        else:
            s = ppstr(list(cpy.values()))
        if self.config.debuglevels.program > Level.LOW:
            s = s[:-2] + f'expected:\n' + str(self.expected) + '}\n'
        if self.config.debuglevels.program > Level.MED:
            s += f'observed:\n' + str(self.observed) + ',\n'
        a, b = self.expected.device.a, self.expected.device.b
        if self.config.debuglevels.program > Level.HIGH:
            for io in [IO.A, IO.B, IO.C, IO.RESULT]:
                if (prod(self.expected.device[io].size())
                        < self.config.max_printable_io_size):
                    s += (f'expected.device.{io}:\n'
                          + tohex(self.expected.device[io]) + ',\n')
        return s

    def compute_expected_outputs(self):
        self.scoreboard.compute_expected_outputs(self)
        for io in [IO.C, IO.RESULT]:
            if io in self.ios and getattr(self, io) is not None:
                v = getattr(self, io)
                self.expected.torch[io] = v

    def fix_pow2_fifo_zeros(self, x):
        dims = AttrDict()
        xsize = x.size(0)
        szi = self.device.MXU_SIZE.i
        clog_szi = 2**clog2(szi)
        dims.sizes = [ceil(xsize/clog_szi), szi]
        dims.strides = [clog_szi, 1]
        return x.as_strided(dims.sizes, dims.strides).flatten().contiguous()

    def set_ios_from_1d_tensor(self, data):
        total_ios_size = 0
        data_size = data.size(0)
        data = data.clone()
        ios = self.config.ios2score
        szi = self.device.MXU_SIZE.i
        for io in ios:
            io_size = prod(self.expected.device[io].size())
            io_size *= ceil(self.device.WIDTHS[io]
                                    / self.device.WIDTHS[IO.A])
            io_size *= 2**clog2(szi)/szi
            io_size = ceil(io_size)
            total_ios_size += io_size
        total_perf_size = self.device.MXU_SIZE.j
        if self.config.read_perf_results:
            total_ios_size += total_perf_size
        if data_size < total_ios_size:
            new_data = torch.ones((total_ios_size,)) * -1 - 1
            new_data[:data_size] = data[:data_size]
            data = new_data
        if data_size > total_ios_size:
            data = data[:total_ios_size]
        ios = list(ios)
        if self.config.read_perf_results:
            ios += ['perf']
        for io in ios:
            if io == 'perf':
                io_size = total_perf_size
            else:
                io_size = prod(self.expected.device[io].size())
                io_size *= ceil(self.device.WIDTHS[io]
                                / self.device.WIDTHS[IO.A])
                io_size *= 2**clog2(szi)/szi
                io_size = ceil(io_size)
            x = data[:io_size].clone()
            if io != 'perf':
                x = self.fix_pow2_fifo_zeros(x)
            data = data[io_size:]
            if io == IO.POST_GEMM_PARAMS:
                x = torch.from_numpy(np.asarray(
                    x, dtype=np.uint8).view('>i8').astype('<i8'))
            if io in ['perf']:
                x = x[-4:]
            if io in [IO.GEMM, 'perf']:
                x = torch.from_numpy(np.asarray(
                    x, dtype=np.uint8).view('>i4').astype('<i4'))
            if io == 'perf':
                self.config.perf_counters = x.tolist()
            else:
                self.set_io_from_1d_tensor(io, x.clone())
        return total_ios_size

    def set_io_from_1d_tensor(self, io: str, x: Tensor):
        if io != 'perf':
            expected = self.expected.device[io].detach().clone().contiguous()
            expected_size = list(expected.size())
        else:
            expected = self.expected.device[io].detach().clone().contiguous()
            expected_size = list(expected.size())
        xsize = x.size(0)
        new_io = torch.ones((prod(expected_size), ), dtype=DTYPE) * -1 - 1
        new_io[:xsize] = x[:xsize].clone()
        x = new_io
        x = x.as_strided(expected_size, expected.stride())
        self.observed.device[io] = x

    def score(self): return self.scoreboard(self)

    def pre_finalize(self): pass

    def set_observed_ios_to_ones(self):
        sizes = self.device_io_sizes()
        for iokey in self.ios:
            self.observed.device[iokey] = (torch.ones(
                sizes[iokey], dtype=DTYPE).contiguous()) * -1

    def torch_io_sizes(self, larger_size_mult=1, N=1):
        sizes = IOItems()
        sizes[IO.A] = (N, self.Cin,
                       self.HWs_ef.a.i,
                       self.HWs_ef.a.j,)
        cout_mult = (int(larger_size_mult)
                     if larger_size_mult else 1)
        sizes[IO.B] = (cout_mult*self.Cout, self.Cin, *self.kernel_size)
        sizes[IO.POST_GEMM_PARAMS] = (cout_mult*self.Cout, )
        for iokey in IOs.OUTPUTS:
            sizes[iokey] = (1, cout_mult*self.Cout, *getattr(self.HWs_ef, iokey))
        return sizes

    def device_io_sizes(self):
        sizes = IOItems()
        total_input_tiles = prod(self.tc.values())
        total_output_tiles = (total_input_tiles // self.tc[K])
        d = self.device
        tsn = self.ts[N]
        sizes[IO.POST_GEMM_PARAMS] = (
            total_input_tiles,
            self.ts[N],
            1,
        )
        sizes[IO.A] = (
            total_input_tiles,
            self.ts[M],
            self.ts[K],
        )
        sizes[IO.B] = (
            total_input_tiles,
            self.ts[N],
            self.ts[K],
        )
        sizes[IO.GEMM] = (
            total_output_tiles,
            self.ts[M],
            tsn,
        )
        for iokey in IOs.OUTPUTS:
            sizes[iokey] = (
                self.tc[N], prod(self.HWs[iokey]),
                tsn)
        return sizes

    def _strided_size_i(self, i_size, kernel_i_size, kernel_i_stride):
        return ceil((i_size-kernel_i_size) / kernel_i_stride + 1)

    def _to_ijparam(self, x): return x if isinstance(
            x, IJParam2) else IJParam2(x, x)

    def _strided_size(self, ij_sizes, kernel_sizes, kernel_strides):
        ij_sizes = self._to_ijparam(ij_sizes)
        kernel_sizes = self._to_ijparam(kernel_sizes)
        kernel_strides = self._to_ijparam(kernel_strides)
        result = IJParam2()
        for ij in ['i', 'j']:
            result[ij] = self._strided_size_i(
                ij_sizes[ij],
                kernel_sizes[ij],
                kernel_strides[ij])
        return result

    def _init_misc(self, ):
        for k in nameof(self.kernel_size, self.pool_stride, self.pool_size):
            if isinstance(self[k], int):
                self[k] = max(1, self[k])
        ijParam_attr_keys = nameof(self.kernel_size, self.stride)
        ijParam_attr_values = (self.kernel_size, self.stride)
        for k, v in zip(ijParam_attr_keys, ijParam_attr_values):
            if isinstance(self[k], int):
                self[k] = IJParam2(v, v)

    def _init_HWs(self, effective_or_actual='effective'):
        self._init_HWs_()
        self._init_HWs_('actual')

    def _init_HWs_(self, effective_or_actual='effective'):
        eoa = effective_or_actual
        d = self.device
        if self.Hin == 1 and self.Win == 1:
            self.Win == self.device.min_tile_size_m
        HWs = AttrDict()
        i = self.Hin if eoa == 'effective' else ceil(self.Hin)
        HWs.a = IJParam2(i, self.Win)
        HWs.gemm = self._strided_size(
            HWs.a, self.kernel_size, self.stride)
        HWs.quantization = HWs.gemm
        HWs.pool_padding = IJParam2(
            HWs.gemm.i + self.pool_padding*2,
            HWs.gemm.j + self.pool_padding*2,
        )
        HWs.pooling = self._strided_size(
            HWs.pool_padding, self.pool_size, self.pool_stride)
        HWs.c = IJParam2(
            HWs.pooling.i + self.c_padding*2,
            HWs.pooling.j + self.c_padding*2,
        )
        HWs.result = IJParam2(
            HWs.pooling.i + self.c_padding*2,
            HWs.pooling.j + self.c_padding*2,
        )
        if eoa == 'effective':
            self.HWs_ef = HWs
        else:
            self.HWs = HWs

    @property
    def min_tile_size_m(self):
        if self.islinear:
            if self.special_size_m:
                return max(ceil(self.device.MXU_SIZE.i * 1.5) - 1,
                           self.device.min_tile_size_m)
            else:
                return 1
        else:
            return self.device.min_tile_size_m

    def _init_tile_sizes(self, ):
        log_en = self.isfirst
        d = self.device
        ts_ef = AttrDict()  # tile_sizes
        ts_ef.M = prod(self.HWs_ef.gemm)
        ts_ef.N = self.device.MXU_SZJ
        ts_ef.K = self.device.MXU_SZI
        self.m_tiling_succeeded = False
        for tile_size_m in reversed(range(self.HWs_ef.gemm.j,
                                  self.device.MAX_TILE_SIZE_M+1,
                                  self.HWs_ef.gemm.j,
                                  )):
            if tile_size_m < self.min_tile_size_m:
                continue
            if (prod(self.HWs_ef.gemm) % tile_size_m) == 0:
                # tile_size_M = tile_size_M / 2
                ts_ef.M = tile_size_m
                self.m_tiling_succeeded = True
                break
        ts_0 = copy(ts_ef)
        ts_ef.M = ts_0.M
        ts = copy(ts_ef)
        ts_ef.N = ts_0.N
        ts_ef.K = ts_0.K
        ts.M = ceil(ts_0.M)
        ts.K = ts_0.K
        # log(ts_0)
        # log(ts_ef)
        # log(ts)
        pads = {Cin: tilepad(self.Cin, ts_ef.K),
                Cout: tilepad(self.Cout, ts_ef.N),}
        self.Cin += pads[Cin]
        self.Cout += pads[Cout]
        tc = AttrDict()
        tc.M = ceil(prod(self.HWs_ef.gemm) / ts_ef.M)
        tc.N = ceil(self.Cout / ts_ef.N)
        tc.K = ceil((self.Cin * prod(self.kernel_size)) / ts_ef.K)
        self.tile_sizes, self.ts_ef, self.ts_0 = ts, ts_ef, ts_0
        self.tile_counts = tc
        # for d in [self.ts, self.ts_ef, self.ts_0, self.tc]:
        #     for k in [M, N, K]:
        #         d[k] = d[k.lower()]

    def pad_input(self, x: Tensor, size=None):
        size = self.Cin if size is None else size
        _, Cin, _, _ = x.size()
        cin_pad = tilepad(Cin, size)
        pad = (0, 0, 0, 0, cin_pad, 0, 0, 0)
        return F.pad(x, pad)

    def partsel_io_cin(self, io):
        if isinstance(io, str):
            io = self.expected.torch[io]
        else:
            assert isinstance(io, Tensor)
        size = io.size()
        sel = self.device.LAYERIOMEM0_SZJ
        sel = 3
        return io[0:1, -sel:]

    def _init_torch_inputs(self):
        ios = copy(self.ios)
        d = self.device
        sizes = self.torch_io_sizes(self.config.larger_size_mult)
        if not self.randomize_inputs:
            Cout, Cin, _, _ = self.b.size()
            cin_pad = tilepad(Cin, d.MXU_SZJ)
            cout_pad = tilepad(Cout, self.tile_size0[N])
            pad = (0, 0, 0, 0, 0, cin_pad, 0, cout_pad)
            self.b = F.pad(self.b, pad)
            self.post_gemm_params = F.pad(self.pgp_fields.value, (0, cout_pad))
            pad = (0, 0, 0, 0, 0, 0, 0, cout_pad)
            self.c = F.pad(self.c, pad)
            self.result = F.pad(self.result, pad)
            self.a = self.pad_input(self.a)
            for io in [IO.A, IO.B, IO.POST_GEMM_PARAMS, IO.C, IO.RESULT]:
                ios.pop(io)
                self.expected.torch[io] = getattr(self, io)
        for io in ios:
            self.randomize_io(io, sizes)
        if self.config.set_values_to_indexes:
            self.set_values_to_indexes()

    def randomize_io(self, io, sizes=None):
        if sizes is None:
            sizes = self.torch_io_sizes(self.config.larger_size_mult)
        size0 = 1 if io is IO.A else self.Cout
        self.expected.torch[io] = torch.randint(
                *int_range(self.device.WIDTHS[io],
                           signed=self.device.SIGNED[io]),
                sizes[io], dtype=DTYPE)[:size0]


    def update_mem(self, ):
        f"""Map {self.expected.torch} to {self.expected.torch} after
        changing {self.expected.torch} to new values."""
        hwout = self.HWs.gemm
        c_tile_size_m = (
            ceil((hwout.i-self.pool_size+1
                  )/self.pool_stride) + 2*self.c_padding
        ) * (
            ceil((hwout.j-self.pool_size+1
                  )/self.pool_stride) + 2*self.c_padding
        )
        tile_size = MNKParam(
            mn=self.ts[M],
            nm=self.ts[N],
            k=self.ts[K],
        )
        padder = torch.nn.ZeroPad2d(self.c_padding)
        mem_c = self.expected[Mapping.TORCH][IO.QUANTIZATION]
        mem_c = self.scoreboard.pool(mem_c, Pool.AVGPOOL2D)
        mem_c = padder(mem_c)
        if self.isfirst:
            prev_mem = None
        else:
            prev_mem = self.prev.mem
        import nnhw
        a = self.expected.torch.a
        b = self.expected.torch.b
        if self.config.use_layer1_optimization2 and self.isfirst:
            from nnhw.arith import Layer1Opt
            a, b = Layer1Opt.remap_ab(self)
        d = self.device
        self.mem = nnhw.mem.Mem(
            a, b,
            self.expected.torch.post_gemm_params,
            mem_c,
            self.instrucs,
            self,
            must_access_tiled_data=True,
            sys_arr_size=IJParam(d.MXU_SZI, d.SZJ),
            prev_mem=prev_mem,
            tile_size=tile_size,
            c_tile_size_m=c_tile_size_m,
            device=self.device,
        )
        mem = self.mem
        if not config.fast:
            mem.remap(Mapping.TB_GEMM)
        if any([
                self.position >= self.parent_size,
                self.is_a_padder
        ]):
            return
        for io in IOs.INPUTS:
            if io in self.ios:
                self.expected.device[io] = getattr(mem, io).data

    def _test(self, log_en=True):
        try:
            # log(self)
            self.__test()
        except Exception:
            log(self)
            self.__test()

    def __test(self, ):
        d = self.device
        if self.isfirst and not self.is_a_padder:
            assert self.Cin <= self.device.MXU_SZJ
        k = self.kernel_size
        s = self.stride
        xi = max((k.i - s.i), 0)
        xj = max((k.j - s.j), 0)
        # assert ((self.HWs_ef.a.i-xi) % s.i) == 0
        # assert ((self.HWs_ef.a.j-xj) % s.j) == 0
        hw = self.HWs_ef.pool_padding
        assert ((hw.i-self.pool_size) % self.pool_stride) == 0, print(
            f'hw {hw}')
        assert ((hw.j-self.pool_size) % self.pool_stride) == 0, print(
            f'hw {hw}')
        assert self.HWs_ef.a.j >= self.kernel_size.j
        assert self.HWs_ef.a.i >= self.kernel_size.i
        assert self.tc[K] >= prod(self.kernel_size), log(
            self.tc[K], prod(self.kernel_size))
        assert self.ts[M] >= self.min_tile_size_m, log(
                self.ts, self.min_tile_size_m)
        assert self.m_tiling_succeeded
        if not self.islinear and not config.compare_mem_sz:
            if hw in [self.HWs_ef.quantization, self.HWs_ef.pool_padding,
                      self.HWs_ef.pooling, self.HWs_ef.c, self.HWs_ef.result]:
                assert hw.i <= self.device.MAX_H
                assert hw.j <= self.device.MAX_W

    #  for compatibility with older code:
    @property
    def HW_in(self): return self.HWs.a
    @property
    def HW_out(self): return self.HWs.gemm


from nnhw.mem import Mem
