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
from debug import log
import numpy as np
from nnhw.arith import Layer
from nnhw.top.cfg import Config, config
from torch.nn import functional as F


@define
class Layer1Opt(AttrDict):
    @classmethod
    def remap_ab(self, layer: Layer):
        new_size_i = layer.kernel_size.i
        new_size_j = layer.kernel_size.j
        new_size_i = layer.kernel_stride.i
        new_size_j = layer.kernel_stride.j
        # new_size = 2
        a, b = self.remap_a(
            layer, new_size_i, new_size_j), self.remap_b(
                layer, new_size_i, new_size_j)
        # self.kernel_size.i = ceil(self.kernel_size.i/new_size)
        layer.optimized.torch.a = a
        layer.optimized.torch.b = b
        return a, b

    @classmethod
    def remap_a(self, layer: Layer, new_size_i, new_size_j):
        # x = self.expected.torch.a.detach().clone()
        x = layer.partsel_io_cin(IO.A)
        # log(x.size())
        cin_dim = 1
        cin = 3
        x = x.flip(cin_dim)
        sizes = AttrDict()
        strides = AttrDict()
        for i, key in enumerate(['N', 'Cin', 'H', 'W']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        new_h_size = ceil(sizes.H/layer.kernel_stride.i)
        new_w_size = sizes.W
        if new_size_j > 1:
            new_w_size = ceil(sizes.W/layer.kernel_stride.j)
        new_sizes = [
            sizes.N,
            cin,
            new_size_i,
            new_size_j,
            new_h_size,
            new_w_size,
        ]
        stride_w = strides.W
        if new_size_j > 1:
            stride_w = strides.W*layer.kernel_stride.j
        new_strides = [
            strides.N,
            strides.Cin,
            strides.H,
            strides.W,
            strides.H*layer.kernel_stride.i,
            stride_w,
        ]
        pad = (0, 0, 0, 0, 0, 0, 0, 1)
        x = F.pad(x, pad)
        x = x.as_strided(new_sizes, new_strides).contiguous()
        new_cin = cin*new_size_i*new_size_j
        x = x.reshape((
            1,
            new_cin,
            new_h_size,
            new_w_size))
        x = x.flip(cin_dim)
        d = layer.device
        SZJ = d.MXU_SZJ
        pad = tilepad(cin*new_size_i, SZJ)
        pad = tilepad(new_cin, SZJ)
        pad = (0, 0, 0, 0, pad, 0, 0, 0)
        # log(x.size())
        x = F.pad(x, pad)
        x = x.contiguous()
        # log(x.size())
        # log(x)
        kwds = dict(show_context=False)
        return x

    @classmethod
    def remap_b(self, layer: Layer, new_size_i, new_size_j):
        x = layer.expected.torch.b.detach().clone()
        n = 4
        cin_dim = 1
        cin = 3
        padn = 1
        pad = (0, padn, 0, padn, 0, 0, 0, 0)
        x = F.pad(x, pad).contiguous()
        x = x.flip(cin_dim)
        sizes = AttrDict()
        strides = AttrDict()
        for i, key in enumerate(['Cout', 'Cin', 'H', 'W']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        pad = (0, 0, 0, 0, 0, 0, 0, 1)
        x = F.pad(x, pad)
        new_h_size = ceil((sizes.H - padn)/layer.kernel_stride.i)
        new_w_size = sizes.W
        if new_size_j > 1:
            new_w_size = ceil((sizes.W - padn)/layer.kernel_stride.j)
        new_sizes = [
            sizes.Cout,
            cin,
            new_size_i,
            new_size_j,
            new_h_size,
            new_w_size,
        ]
        stride_w = strides.W
        if new_size_j > 1:
            stride_w = strides.W*layer.kernel_stride.j
        new_strides = [
            strides.Cout,
            strides.Cin,
            strides.H,
            strides.W,
            strides.H*layer.kernel_stride.i,
            stride_w,
        ]
        new_cin = cin*new_size_i*new_size_j
        x = x.as_strided(new_sizes, new_strides)
        x = x.reshape((sizes.Cout,
                       new_cin,
                       new_h_size,
                       new_w_size,))
        x = x.flip(cin_dim)
        d = layer.device
        SZJ = d.MXU_SZJ
        pad = tilepad(new_cin, SZJ)
        pad = (0, 0, 0, 0, pad, 0, 0, 0)
        x = F.pad(x, pad)
        x = x.contiguous()
        kwds = dict(show_context=False)
        return x


@define
class ParaTile(AttrDict):
    x = 0
    @classmethod
    def remap_ab(self, layer: Layer):
        ios = AttrDict()
        log_en = not layer.position
        log_en = False
        ios.a = self.remap_a(layer, layer.expected.torch.a, log_en)
        ios.b = self.remap_b(layer)
        for ios_ in ['optimized']:
            for io in [IO.A, IO.B]:
                layer[ios_].torch[io] = ios[io]
        return ios.a, ios.b

    @classmethod
    def remap_a(self, layer: Layer, x: Tensor, log_en=False):
        L = layer
        sz = AttrDict()  # size
        st = AttrDict()  # stride
        for i, key in enumerate(['N', 'Cin', 'H', 'W']):
            sz[key] = x.size(i)
            st[key] = x.stride(i)
        # log('here')
        log(L)
        log(sz)
        log(x)
        d = layer.device
        #
        ts, tc = layer.ts, layer.tc
        ts_m, ts_k = ts[M], ts[K]
        tc_m, tc_k = tc[M], tc[K]
        ts_h, tc_h = ceil(ts_m/L.HWs_ef.gemm.j), tc_m
        #
        nsz = [
            # Cin
            ceil(sz.Cin/L.ts_ef.K),  # Cin tile_count
            1,  # M tile_fill 1
            L.ts_ef.K,  # Cin tile_fill
            # H
            tc_h,  # tile_count
            ts_h,  # tile_fill 0
            # W
            sz.W,
        ]
        nst = [
            # Cin
            st.Cin * L.ts_ef.K,  # Cin tile_count
            st.H * ts_h,  # M tile_fill 1
            st.Cin,  # Cin tile_fill
            # H
            st.H * ts_h,  # tile_count
            st.H,  # tile_fill 0
            # W
            st.W,
        ]
        log(nsz)
        x = x.as_strided(nsz, nst).contiguous()
        nsz = [
            1,
            prod(nsz[:-3]),
            prod(nsz[-3:-1]),
            nsz[-1],
        ]
        x = x.reshape(nsz).contiguous()
        log(x.size())
        log(x)
        return x

    @classmethod
    def remap_b(self, layer: Layer):
        L = layer
        log_en = L.isfirst
        x = layer.expected.torch.b
        sz = AttrDict()  # size
        st = AttrDict()  # stride
        for i, key in enumerate(['Cout', 'Cin', 'H', 'W']):
            sz[key] = x.size(i)
            st[key] = x.stride(i)
        # log(L)
        # log(sz)
        # log(x)
        # log(ts_n)
        # log(ts_k)
        d = layer.device
        #
        ts, tc = layer.ts, layer.tc
        ts_n, ts_k = ts[N], ts[K]
        tc_n, tc_k = tc[N], tc[K]
        #
        nsz = [
            # Cout
            tc_n,  # tile_count
            ts_n,  # tile_fill 0
            # Cin
            ceil(sz.Cin/L.ts_ef.K),  # Cin tile_count
            1,  # Cout tile_fill 1
            L.ts_ef.K,  # Cin tile_fill
            # W
            sz.H,
            sz.W,
        ]
        # st.Cout = 0
        nst = [
            # Cout
            st.Cout * ts_n * 1,  # tile_count
            st.Cout,  # tile_fill 0
            # Cin
            st.Cin * L.ts_ef.K,  # Cin tile_count
            st.Cout * ts_n,  # Cout tile_fill 1
            st.Cin,  # Cin tile_fill
            # W
            st.H,
            st.W,
        ]
        # log(nsz[:-5])
        # log(nsz[-5:-2])
        # log(nsz[-2])
        # log(nsz[-1])
        x = x.as_strided(nsz, nst).contiguous()
        nsz = [
            prod(nsz[:-5]),
            prod(nsz[-5:-2]),
            nsz[-2],
            nsz[-1],
        ]
        # log(nsz)
        x = x.reshape(nsz).contiguous()
        # log(x.size())
        # log(x)
        # log.ln()
        return x
