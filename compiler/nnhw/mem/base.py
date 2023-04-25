from abc import ABC, abstractmethod
from copy import deepcopy
from torch import Tensor
from nnhw.mem import space as space_
from nnhw.mem.space import DimOrder, Space
from nnhw.top import (
    IJParam, args2attrs, prod, tolist, varname, nameof,
    Data, Dim, Mapping, K, M, N, tile_count, tile_fill,
    H, W, Cin, Kernel, Cout)
from debug import log


class Tiler(ABC):
    """Extracts the memory traversal instructions for performing GEMM and
    mapping NN convolution to GEMM. Bulk of this work is done by Space
    objects (in space.py).

    The instructions consist of size and stride
    parameters. Each size and stride parameter is passed into a space
    on the device to tell it its range and increment size, respectively. There
    are an array of space on the device that each get one of these parameter
    pairs and each space corresponds to a dimension in a data tensor mapped
    onto a memory in the device."""

    ###########################################################################
    # PUBLIC API
    ###########################################################################
    def __init__(self, tensor, kernel_size, *args, **kwds):
        self.tensor = tensor
        self.kernel_size = kernel_size
        self.mapping = Mapping.BASE
        self.push_instrucs_enable = kwds[varname()]
        self.space = Space()  # assigned later
        for k, v in kwds.items():
            setattr(self, k, v)

    @args2attrs()
    def preprocess(self, other_tiler):
        """Must be called once before using following API.
        other_tiler is a tiler of the opposing data type, i.e. a weight tiler
        if self.is a layerio tiler and vice-versa.
        """
        self._parse_base_space(self.tensor)  #.detach().clone())


    # @abstractmethod
    def remap(self, ) -> None: ...

    @property
    def data(self) -> Tensor:
        """Return memory data mapped to set shape in the form of a tensor."""
        if self.mapping in [Mapping.HOST_GEMM, Mapping.TB_GEMM]:
            data = self.space.flattened_data()
        else:
            data = self.space.data
        return data

    def update_tensor_(self, tensor):
        self._unmodified_base_space._tensor_ = tensor.permute(
            *self.permute_dims)
        self._unmodified_base_space._update_stride_()
        self._unmodified_base_space._update_size_()
        # self._space = deepcopy(self._unmodified_base_space)
        # self.space._tensor_ = self._tensor
        # self.space._tensor_ = self._tensor
        # self.space._update_stride_()
        # self.space._update_size_()
        self.parent.remap(self.mapping)
        return self
    ###########################################################################

    def _parse_base_space(self, tensor):
        if tensor.size(0) == 1:
            tensor = tensor.squeeze(0)
        tensor = tensor.permute(self.permute_dims)
        tensor = tensor.contiguous()
        self._space = Space(
            self.__class__.__name__, (), *self.TensorDims,
            tensor=tensor, dims_from_tensor=True
        )
        self._space.pad_(self._space_pad)
        self._unmodified_base_space = self._space
        # self._unmodified_base_space = deepcopy(self._space)

    @property
    def _tensor(self): return self._space._tensor_
    # def _tensor(self): return self._space._tensor_.detach().clone()
    # -------------------------------------------------------------------------
    @property
    def _filler_space(self, ): return Space(' < Filler > ')
    @property
    def _nm_space(self, ): return self.other_tiler._mn_space
    # @property
    # def _Cin_space(self, ): return deepcopy(self._space[Dim.Cin])

    def _filler_space_(self, number=None):
        if number is not None:
            name = f' < Filler{number} > '
        else:
            name = ' < Filler > '
        space = Space(name)
        return space

    @property
    def _Cin_space(self, ):
        space = deepcopy(self._space[Dim.Cin])
        if self.mapping in [Mapping.DEVICE]:
            space.size //= self.sys_arr_size.j
            if space.size == 0:
                space.size = 1
        return space

    @property
    def _tile_count_nm_space(self, ):
        tile_count, tile_fill = space_.Dim.tile_count, space_.Dim.tile_fill
        space = Space()
        space.size = prod(
            self.other_tiler.space[tile_count][self.nm]('size', list))
        space.stride = 0
        return space

    @property
    def _HW_space(self, ):
        space = deepcopy(Space(self._space[H], self._space[W]))
        if self.mapping in [Mapping.DEVICE]:
            for dim in space.dims:
                dim.stride //= self.sys_arr_size.j
                if dim.stride == 0:
                    dim.stride = 1
        return space

    @property
    def _Cin_pad(self):
        return self._dim_pad(self._space[Cin].size, self.tile_size.k)

    def _dim_pad(self, size, tile_size):
        return ((tile_size - (size % tile_size)) % tile_size)

    def _store_instrucs(self, instruc=None):
        if not self.push_instrucs_enable[0]:
            return
        from nnhw.instruc import MemInstrucs
        if isinstance(self.instrucs, MemInstrucs):
            instruc = self.instrucs[1] if instruc is None else instruc
        else:
            instruc = self.instrucs if instruc is None else instruc
        instruc.size = self.space.size
        instruc.stride = self.space.stride

    def remap(self, mapping: Mapping):
        self.mapping = mapping
        if mapping is Mapping.BASE:
            self.space = deepcopy(self._space)
            self.space._tensor_ = self._tensor
        if mapping is Mapping.DATA_TRANSFER:
            self.space = deepcopy(self._space)
            self.space._tensor_ = self._tensor
        if mapping in [Mapping.DEVICE, ]:
            self._mnk_remap()
            tile_size = deepcopy(self.moded_tile_size)
            tile_size.k = 1
            self.space.unflatten_(
                tile_size.aslist, dim_order=DimOrder.tile_dominant)
        if mapping in [Mapping.TB_GEMM]:
            self._mnk_remap()
            self.space.unflatten_(
                self.moded_tile_size.aslist, dim_order=DimOrder.tile_dominant)
        if mapping is Mapping.HOST_GEMM:
            self._mnk_remap()
            self.space.unflatten_(
                self.moded_tile_size.aslist, dim_order=DimOrder.child_dominant)
            if self.type == Data.WEIGHT:
                self.space.permute_(Dim.K, self.mn)
            self.space.pop(self.nm, None)

    def postremap(self):
        if not self.mapping in [Mapping.DEVICE, Mapping.TB_GEMM]:
            return
        NM0, NM1 = self.nm + '0', self.nm + '1'
        self.space[tile_count].pop(self.nm, None)
        self.space[tile_fill].pop(self.nm, None)
        self.space[tile_fill][K].pop(Kernel, None)

    def tb_gemm_postremap(self):
        MN, NM = self.mn, self.nm
        NM0, NM1 = self.nm + '0', self.nm + '1'
        self.space = Space(
            self.space.name,
            self.space[tile_count],
            self.space[tile_fill][MN],
            self.space[tile_fill][K],
            tensor=self._tensor,
        )

    def _mnk_remap(self, ):
        self.space = Space(
            self.__class__.__name__, (),
            self.mn, self.nm, Dim.K, tensor=self._tensor
        )
        self.space[self.mn] = self._mn_space
        self.space[K][Kernel] = self._Kernel_space
        self.space[K][Cin] = self._Cin_space

    @property
    def _Kernel_space(self, ):
        return Space(
            H, W,
            size=tolist(self.kernel_size),
            stride=self._HW_space.stride
        )


class Reader(Tiler):
    pass


class Writer(Tiler):
    pass
    # def __init__(self, *args, **kwds):
    #     super().__init__(*args, **kwds)
    #     self.tile_size = ijParam(
    #         i=self.sys_arr_size.i,
    #         # nm=sys_arr_size.i,
    #         j=self.sys_arr_size.j)

    # @property
    # def _space_pad(self): return 0, 0, 0, 0, 0, 0
