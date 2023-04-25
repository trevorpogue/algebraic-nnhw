import math
from collections import namedtuple
from copy import deepcopy
from math import ceil, floor
import torch
from torch import Tensor
from nnhw import instruc, top
from nnhw.mem import space as space_
from nnhw.mem.base import Reader, Space, Tiler, Writer
from nnhw.mem.layerio import LayerioTiler
from nnhw.mem.space import DimOrder
from nnhw.top import (
    IJParam, MNKParam, prod, Data, Dim, Mapping,
    K, M, N, tile_count, tile_fill, Cin, Cout, Kernel, H, W)


class WeightTiler(Tiler):
    def __init__(self,
                 tensor: torch.Tensor,
                 instrucs: instruc.Layer,
                 kernel_size: IJParam,
                 tile_size: MNKParam,
                 **kwds):
        self.tile_size = tile_size
        self.type = Data.WEIGHT
        self.mn = Dim.N
        self.nm = Dim.M
        self.instrucs = instrucs
        self.TensorDims_in = ['Cout', 'Cin', 'H', 'W', ]
        super().__init__(tensor, kernel_size, **kwds)
        self.moded_tile_size = deepcopy(self.tile_size)

    @top.args2attrs()
    def preprocess(self, other_tiler):
        super().preprocess(other_tiler)

    @property
    def _mn_space(self, ):
        space = Space(self._Cout_space)
        return space

    def remap(self, mapping: Mapping):
        # self._space = deepcopy(self._unmodified_base_space)
        self._space = self._unmodified_base_space
        super().remap(mapping)

    def postremap(self):
        if self.mapping not in [Mapping.DEVICE, Mapping.TB_GEMM]:
            return
        super().postremap()
        # -------- tile_count --------
        # -------- tile_fill --------
        self.space[tile_count].insertitem(1, M, self._tile_count_nm_space)
        self.space[tile_fill][self.mn].insert(0, self._filler_space)
        self.space[tile_count][self.mn].insert(0, self._filler_space)
        if self.mapping in [Mapping.TB_GEMM]:
            self.tb_gemm_postremap()

    @property
    def tensor_offset(self): return prod(
            self._unmodified_base_space._tensor_.size()) / self.sys_arr_size.j

    def _store_instrucs(self):
        super()._store_instrucs()
        if not self.push_instrucs_enable[0]:
            return
        tensor_offset = self.tensor_offset
        self.cum_tensor_size = getattr(self, 'cum_tensor_size', tensor_offset)
        if self.prev_tiler is not None:
            self.instrucs.offset = self.prev_tiler.cum_tensor_size
            self.cum_tensor_size = (
                self.prev_tiler.cum_tensor_size + tensor_offset)


class WeightReader(WeightTiler, Reader):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.TensorDims_in = ['Cout', 'Cin', 'H', 'W', ]
        self.TensorDims = ['H', 'W', 'Cin', 'Cout', ]
        self.permute_dims = [2, 3, 1, 0, ]

    @property
    def _Cout_space(self, ): return deepcopy(self._space[Cout])

    @property
    def _space_pad(self):
        Cout_pad = self._dim_pad(self._space[Cout].size, self.tile_size.mn)
        Hpad, Wpad = 0, 0
        return (0, Cout_pad, 0, self._Cin_pad, 0, Wpad, 0, Hpad, )


class PostGemmParamsReader(WeightTiler, Reader):
    def __init__(self, tensor, *args, **kwds):
        tensor = tensor.unsqueeze(1).unsqueeze(1).unsqueeze(1)
        WeightTiler.__init__(self, tensor, *args, **kwds)
        self.TensorDims = ['Cout', 'H', 'W', 'Cin', ]
        self.permute_dims = [0, 2, 3, 1, ]
        # self.TensorDims = ['Cout', 'Cin', 'H', 'W', 'Params']
        # Reader.__init__(self, tensor, *args, **kwds)
        # self.moded_tile_size.k = 1

    @property
    def _space_pad(self):
        Cout_pad = self._dim_pad(self._space[Cout].size, self.tile_size.mn)
        Hpad, Wpad = 0, 0
        return (0, self._Cin_pad, 0, Wpad, 0, Hpad, 0, Cout_pad, )

    @property
    def _Cout_space(self, ):
        space = deepcopy(self._space[Dim.Cout])
        if self.mapping in [Mapping.DEVICE]:
            for dim in space.dims:
                dim.stride //= self.sys_arr_size.j
                if dim.stride == 0:
                    dim.stride = 1
        return space

    @property
    def _Cin_pad(self): return 0

    @property
    def _Kernel_space(self, ):
        return Space(
            Dim.H, Dim.W,
            size=[1, 1],
            stride=self._HW_space.stride
        )

    def postremap(self):
        if self.mapping not in [Mapping.DEVICE, Mapping.TB_GEMM]:
            return
        super().postremap()
        self.space[tile_count][K] = deepcopy(
            self.other_tiler.space[tile_count][K])
        for dim in self.space[tile_count][K].leaves:
            dim.stride = 0

    @property
    def tensor_offset(self): return prod(
            self._unmodified_base_space._tensor_.size())
# -----------------------------------------------------------------------------


class WeightWriter(WeightTiler, Writer):
    """"""

    def remap(self, mapping: Mapping):
        self.mapping = mapping
        self.space = deepcopy(self._space)

    def _mnk_remap(self): self.space = deepcopy(self._space)
