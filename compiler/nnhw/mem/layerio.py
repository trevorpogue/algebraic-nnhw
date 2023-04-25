from collections import namedtuple
from copy import deepcopy
from math import ceil, floor
import snoop
import torch
from torch import Tensor
from nnhw import instruc, top
from nnhw.mem import space as space_
from nnhw.mem.base import Reader, Space, Tiler, Writer
from nnhw.mem.space import DimOrder
from nnhw.top import (
    IJParam, MNKParam, prod, Data, Dim, Mapping, K, M, N,
    tile_count, tile_fill, Kernel, Cin, H, W, nameof)
from debug import log

# snoop.install(columns='')


class LayerioTiler(Tiler):
    # @top.args2attrs()
    def __init__(self,
                 tensor: torch.Tensor,
                 instrucs: instruc.MemInstruc,
                 kernel_size: IJParam,
                 kernel_stride: IJParam,
                 pool_stride: IJParam,
                 padding: int,
                 tile_size: MNKParam,
                 edit_tile_size: bool,
                 **kwds,
                 ):
        self.tensor = tensor
        self.instrucs = instrucs
        self.kernel_size = kernel_size
        self.kernel_stride = kernel_stride
        self.pool_stride = pool_stride
        self.padding = padding
        self.edit_tile_size = edit_tile_size
        self.type = Data.LAYERIO
        self.mn = Dim.M
        self.nm = Dim.N  # the self.mn of the other_tiler
        self.TensorDims_in = ['Cin', 'H', 'W', ]
        # self.TensorDims = ['H', 'W', 'Cin', ]
        # self.permute_dims = [1, 2, 0, ]
        self.TensorDims = ['Cin', 'H', 'W', ]
        self.permute_dims = [0, 1, 2, ]
        self.pool_size = pool_stride  # conv.pool_stride
        self.tile_size = tile_size
        super().__init__(tensor, kernel_size, **kwds)
        self.moded_tile_size = deepcopy(self.tile_size)

    @property
    def _HW_space(self, ):
        space = deepcopy(Space(self._space[H], self._space[W]))
        return space

    @property
    def _space_pad(self):
        """
        Return pad sizes, two per dimension for each side of the dimension. The
        two-element tuples have to appear in reversed order compared to how
        tensor dims are defined as per torch.nn.functional.pad.
        """
        Hpad, Wpad = 0, 0
        return 0, self._Cin_pad, 0, Wpad, 0, Hpad,

    def remap(self, mapping: Mapping):
        self._space = deepcopy(self._unmodified_base_space)
        super().remap(mapping)

    @property
    def _mn_space(self):
        space = self._HW_space
        hw_out = self.parent.layer_params.HW_out
        space.size = list(hw_out)
        space.stride = (space('stride', Tensor) * Tensor(
            list(self.kernel_stride))).to(torch.int32).tolist()
        return space
# -----------------------------------------------------------------------------

    def _mnk_remap(self, ):
        super()._mnk_remap()
        self._pad_tile_size_mn()

    # @snoop
    def _pad_tile_size_mn(self, ):
        if not self.edit_tile_size:
            return
        H_size = self.space[self.mn][Dim.H].size
        W_size = self.space[self.mn][Dim.W].size
        tsize = W_size * H_size
        next_tsize = tsize / 7
        tile_size = self.tile_size.mn
        while ((next_tsize > tile_size)
               and (next_tsize % H_size) == 0):
            tsize = next_tsize
            next_tsize /= 2
        if tsize < tile_size:
            tsize = tile_size
        self.moded_tile_size = top.MNKParam(
            mn=tsize, nm=tile_size, k=self.tile_size.k)

    def get_offset(self, i, instruc):
        if self.prev_tiler is None:
            instruc.offset = 1
        else:
            prev_instrucs = self.prev_tiler.instrucs[i]
            instruc.offset = prev_instrucs.offset

    def _store_instrucs(self, i, instruc, ):
        super()._store_instrucs(instruc)
        if not self.push_instrucs_enable[0]:
            return
        self.get_offset(i, instruc)
# -----------------------------------------------------------------------------

    def postremap(self):
        if not self.mapping in [Mapping.DEVICE, Mapping.TB_GEMM]:
            return
        super().postremap()
        self.space[tile_count].insertitem(0, N, self._tile_count_nm_space)
        if self.mapping in [Mapping.TB_GEMM]:
            self.tb_gemm_postremap()


class LayerioWriter(LayerioTiler, Writer):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

    @property
    def _Cout_space(self): return super()._Cin_space

    def _mnk_remap(self):
        self.space = Space(
            self.__class__.__name__, (),
            M, N, K, tensor=self._tensor)
        self.space[M] = self._HW_space
        self.space[K][Kernel] = self._Kernel_space
        for dim in self.space[K][Kernel]:
            dim.size = 1
            dim.stride = 0
        self.space[K][Cin] = self._Cout_space
        self._pad_tile_size_mn()

    def postremap(self):
        if self.mapping not in [Mapping.DEVICE, Mapping.TB_GEMM]:
            return
        Tiler.postremap(self)
        offset = 0
        self.space[tile_count].insertitem(offset + 0, N, self._filler_space)
        kspace = self.space[tile_count][K]
        mspace = self.space[tile_count][M]
        self.space[tile_count].pop(K)
        self.space[tile_count].pop(M)
        self.space[tile_count].insert(1, kspace)
        self.space[tile_count].append(mspace)
        if self.mapping in [Mapping.TB_GEMM]:
            self.tb_gemm_postremap()

    def _store_instrucs(self, i, instruc):
        from nnhw.top.cfg import config
        if not self.push_instrucs_enable[0]:
            return
        instruc.size = [0] * (config.device.TOTAL_DIGITS-1) + [
            prod(self.space.size)]
        instruc.stride = [0] * (config.device.TOTAL_DIGITS-1) + [1]
        self.get_offset(i, instruc)

    def get_offset(self, i, instruc):
        if self.prev_tiler is None:
            instruc.offset = 0
        else:
            prev_instrucs = self.prev_tiler.instrucs[i]
            instruc.offset = int(not prev_instrucs.offset)


class LayerioReader(LayerioTiler, Reader):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        # self.TensorDims_in = ['Cin', 'H', 'W', ]
        # self.TensorDims = ['Cin', 'H', 'W', ]
        # self.permute_dims = [0, 1, 2, ]

    @property
    def _space_pad(self):
        """
        Return pad sizes, two per dimension for each side of the dimension. The
        two-element tuples have to appear in reversed order compared to how
        tensor dims are defined as per torch.nn.functional.pad.
        """
        Hpad, Wpad = 0, 0
        min_tile_size_m = ceil(self.sys_arr_size.i * 1.5)
        # if (self._space[H].size
        #        + Hpad)*self._space[W].size/prod(
        #            self.kernel_stride) < min_tile_size_m:
        #     print(min_tile_size_m)
        #     print(self._space[H].size)
        #     print(self._space[W].size)
        #     print(self.kernel_stride)
        #     print((self._space[H].size + Hpad)*self._space[W].size/prod(
        #            self.kernel_stride))
            # assert False, log('Internal assertion')
        # Hpad = self._dim_pad(self._space[Dim.H].size, self.tile_size.m)
        # Wpad = self._dim_pad(self._space[Dim.W].size, self.tile_size.m)
        return 0, self._Cin_pad, 0, Wpad, 0, Hpad,
