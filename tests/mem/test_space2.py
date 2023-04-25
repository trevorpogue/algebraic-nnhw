import math
import typing as typ
import unittest
from copy import copy, deepcopy
from math import ceil, floor
from random import randrange
import sections
import torch
from cocotb.triggers import Event
from debug import log
from torch import nn
import nnhw
from nnhw.mem import space as space_
from nnhw.mem.dim import Cin, Cout, H, K, Kernel, M, N, W, tile_count, tile_fill
from nnhw.mem.space import DimOrder, Space
from nnhw.top import FIPMethod, IJParam, MNKParam, nameof, prod, varname


class ConvParams():
    def __init__(self, *args, **attrs):
        self.parent = attrs['parent']
        self.kernel_size: IJParam = None
        self.kernel_stride: IJParam = None
        self.pool_size: IJParam = None
        self.pool_stride: IJParam = None
        # sizes:
        self.Cin: int = None
        self.Cout: int = None
        self.HW_in: IJParam = None
        self.HW_out: IJParam = None
        self.padding: int = None
        self.kernel_size = 1
        self.pool_size = 1

    def randomize(self):
        self.kernel_stride = randrange(1, 2)
        self.pool_stride = randrange(1, 2)
        ijParam_attr_keys = nameof(
            self.kernel_size, self.kernel_stride,
            self.pool_size, self.pool_stride,
        )
        ijParam_attr_values = (
            self.kernel_size, self.kernel_stride,
            self.pool_size, self.pool_stride,
        )
        for k, v in zip(ijParam_attr_keys, ijParam_attr_values):
            setattr(self, k, IJParam(v, v))
        self.Cin = self.parent.sizes[K]
        self.Cout = self.parent.sizes[N]
        self.HW_in = IJParam(ceil(2),
                             ceil(self.parent.sizes[M]/2))
        self.HW_out = IJParam(
            ceil(self.HW_in.i / self.kernel_stride.i),
            ceil(self.HW_in.j / self.kernel_stride.j)
        )
        self.padding = ceil(1/2) - 1
        return self


class Conv2d():
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.layerinput: torch.tensor = None
        self.weight: torch.tensor = None
        self.layeroutput: torch.tensor = None
        self.instrucs = nnhw.instruc.Instrucs()  # not used but for nnhw.mem.Mem api
        self.A_WIDTH = 8
        self.A_SIGNED = 0
        self.B_WIDTH = 8
        self.B_SIGNED = 1
        self.SZI = 4
        self.SZJ = 4
        self.n = self.SZI
        self.m = math.ceil(self.SZI * 2)
        self.k = self.SZJ
        self.sys_arr_size = IJParam(i=self.SZI, j=self.SZJ)
        self.a = None
        self.b = None
        self.c = None
        self.tile_sizes = {M: self.m, N: self.n, K: self.k}
        self.total_tiles = {
            M: 2,
            N: 2,
            K: 1,
        }
        self.sizes = {}
        for k in self.tile_sizes:
            self.sizes[k] = ceil(self.tile_sizes[k]
                                 * self.total_tiles[k])
        self.mem = None
        attrs['parent'] = self
        self.conv_params = ConvParams(*args, **attrs)

    def int_range(self, width, signed: bool):
        if signed:
            return (-2 ** (width-1), 2 ** (width-1))
        else:
            return (0, 2 ** (width))

    def randomize(self):
        self.conv_params.randomize()
        conv = self.conv_params
        self.layerinput = torch.randint(
            *self.int_range(self.A_WIDTH, signed=self.A_SIGNED),
            (1, conv.Cin, *conv.HW_in))
        self.layeroutput = torch.randint(
            *self.int_range(self.A_WIDTH, signed=self.A_SIGNED),
            (1, conv.Cout, *conv.HW_out))
        log((conv.Cout, conv.Cin, *conv.kernel_size))
        self.weight = torch.randint(
            *self.int_range(self.B_WIDTH, signed=self.B_SIGNED),
            (conv.Cout, conv.Cin, *conv.kernel_size))
        self.mem = nnhw.mem.Mem(
            self.layerinput,
            self.weight,
            self.layeroutput,
            self.instrucs,
            self.conv_params,
            tile_size = MNKParam(
                mn=self.sys_arr_size.i * 2,
                nm=self.sys_arr_size.i,
                k=self.sys_arr_size.j),
            must_access_tiled_data=True,
        )
        self.c = self.compute_c()
        self.mem.remap(nnhw.mem.Mapping.DEVICE)
        tiler = self.mem.layerio_reader
        space = tiler.space
        MatDim = nnhw.mem.Dim
        TileDim = space_.Dim
        tile_count, tile_fill = TileDim.tile_count, TileDim.tile_fill
        M, N, K = MatDim.M, MatDim.N, MatDim.K
        return self

    def compute_c(self):
        self.mem.remap(nnhw.mem.Mapping.HOST_GEMM)
        c = self.mem.layerio_reader.data.matmul(self.mem.weight_reader.data)
        stride_size = [
            self.conv_params.Cout,
            self.conv_params.HW_out.i,
            self.conv_params.HW_out.j
        ]
        stride = [
            1,
            self.conv_params.Cout*self.conv_params.HW_out.j,
            self.conv_params.Cout,
        ]
        return c.as_strided(stride_size, stride)


def data(tiler: nnhw.mem.base.Tiler) -> torch.Tensor:
    space = tiler.space
    # log(tiler.__class__, space)
    MN, NM = tiler.mn, tiler.nm
    NM0, NM1 = tiler.nm + '0', tiler.nm + '1'
    new_leaf_dims = [
        space[tile_count],
        Space(space[tile_fill][NM0],
              space[tile_fill][MN],
              space[tile_fill][NM1]),
        space[tile_fill][K],
    ]
    log('here')
    return space.flattened_data(new_leaf_dims, )


def test():
    seqitem = Conv2d().randomize()
    data(seqitem.mem.weight_reader)
