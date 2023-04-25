from __future__ import annotations
from nnhw import arith
import typing as typ
from nnhw.mem.base import Tiler
from nnhw.mem.space import Space
from nnhw.mem.layerio import LayerioReader, LayerioWriter
from nnhw.mem.weight import (PostGemmParamsReader, WeightReader, WeightTiler)
from math import ceil
import torch
from nnhw.top import (
    IJParam, Layerio, LowerStrEnum, MNKParam, StrEnum, Weight, auto,
    nameof, prod, varname, K, M, N, tile_count, tile_fill, Cout, H, W, Cin,
    Mapping, Level, print_begin_end, AttrDict)
from debug import log
from nnhw.top.device import Device


class Mem:
    """Collects the device tiler instructions that allow the device memory to
    traverse elements in the order necessary to perform GEMM and for the device
    to simultaneously perform conv-to-GEMM/GEMM-to-conv mapping.

    This is done when running Mem.mapped() with a certan mapping. In hardware,
    the mapping would determine the order in which memory elements are read
    from and written to. In software here, it updates the dimension sizes
    and strides representing the underlying tensor data view. Running mapped
    will do this to the tensor in software and also extract the necessary
    instructions required to send to the device in order for the device memory
    to have the analogous mapping as the tensor here in software.

    Some mappings may be suitable for direct input to torch GEMM matmul
    method, while others are suitable for the order in which to write
    layerio/weight data to device.

    Mem has an underlying data tensor and the remapping done in Mem.mapped()
    is analogous to performing a bunch of memory mapping operations on the
    tensor such as torch.as_strided, torch.reshape, torch.pad, torch.permute.
    The difference is that Mem completely abstracts all the individual and
    confusing combinations of torch operations required to map conv data to
    gemm and back, and also those required extract the device tiler
    instructions for the device to mimic the same mapping as well at the
    appropriate stage in the algorithm.

    The core logic for enabling this functionality is in the Tiler class /
    subclasses and the Space class.
    """

    ###########################################################################
    # PUBLIC API
    ###########################################################################
    # @top.args2attrs()
    def __init__(
            self,
            layer_input: Layerio,
            weight: Weight,
            post_gemm_params: Weight,
            layer_output: typ.Optional[Layerio],
            instrucs: 'instruc.Layer',
            layer: arith.Layer,
            gemm_output: typ.Optional[torch.Tensor] = None,
            tile_size: typ.Optional[MNKParam] = None,
            must_access_tiled_data: bool = False,
            sys_arr_size: typ.Optional[IJParam] = None,
            prev_mem: 'Mem' = None,
            c_tile_size_m: int = None,
            device: Device = None,
    ):
        f"""must_access_tiled_data is needed when using any method using
            {Space._as_strided_tensor}) but this is compute expensive
            so only use when needed. Only needed because tiling size
            changes done in {WeightTiler.postremap}.
            """
        from debug import log
        self.log = log
        self.push_instrucs_enable = [True]
        self.device = device
        kwds = {}
        kwds[nameof(self.push_instrucs_enable)] = self.push_instrucs_enable
        kwds[nameof(sys_arr_size)] = sys_arr_size
        kwds[nameof(must_access_tiled_data)] = must_access_tiled_data
        kwds['parent'] = self
        kwds['is_linear_layer'] = layer.islinear
        self.layer = layer
        prev_tilers = {}
        if prev_mem:
            for key in ['a', 'b', 'post_gemm_params_reader', 'c']:
                prev_tilers[key] = getattr(prev_mem, key)
        self.sys_arr_size = sys_arr_size
        if tile_size is None:
            tile_size = MNKParam(
                mn=sys_arr_size.i * 2,
                nm=sys_arr_size.i,
                k=sys_arr_size.j)
            edit_tile_size = True
            edit_tile_size = False
        else:
            edit_tile_size = False
        self.tile_size = tile_size
        self.layer_params = layer
        self.instrucs = instrucs
        self.layerio_reader = LayerioReader(
            layer_input,
            instrucs.layerio_rd_instrucs,
            layer.kernel_size,
            layer.kernel_stride,
            layer.pool_stride,
            layer.padding,
            tile_size,
            edit_tile_size,
            prev_tiler=prev_tilers.get('c', None),
            **kwds,
        )
        self.weight_reader = WeightReader(
            weight,
            instrucs.weight_rd_instruc,
            layer.kernel_size,
            tile_size.mn_swapped(),
            prev_tiler=prev_tilers.get('b', None),
            **kwds,
        )
        self.post_gemm_params_reader = PostGemmParamsReader(
            post_gemm_params,
            instrucs.post_gemm_params_rd_instruc,
            layer.kernel_size,
            tile_size.mn_swapped(),
            prev_tiler=prev_tilers.get('post_gemm_params_reader', None),
            **kwds,
        )
        if layer_output is not None:
            if c_tile_size_m is not None:
                tile_size.mn = c_tile_size_m
            self.layerio_writer = LayerioWriter(
                layer_output,
                instrucs.layerio_wr_instrucs,
                layer.kernel_size,
                layer.kernel_stride, layer.pool_stride,
                layer.padding,
                tile_size.k_nm_swapped(),
                edit_tile_size,
                prev_tiler=None if layer.isfirst else self.a,
                **kwds,
            )
            self.layerio_writer.preprocess(self.weight_reader)
        self.layerio_reader.preprocess(self.weight_reader)
        self.weight_reader.preprocess(self.layerio_reader)
        self.post_gemm_params_reader.preprocess(self.layerio_reader)
        self._base_tilers = self._tilers

    def remap(self, mapping: Mapping) -> Mem:
        """Do in-place memory remapping of a certain type. See Mem docstring
        for more detail.
        """
        tilers = self._base_tilers
        for k, tiler in tilers.items():
            tiler.remap(mapping)
            setattr(self, k, tiler)
        self.weight_reader.postremap()
        self.post_gemm_params_reader.postremap()
        self.layerio_reader.postremap()
        if hasattr(self, 'layerio_writer'):
            self.layerio_writer.postremap()
        if self.push_instrucs_enable[0]:
            if mapping in [Mapping.DEVICE]:
                for k, tiler in tilers.items():
                    # if (isinstance(tiler, self.a.__class__)
                            # or isinstance(tiler, self.c.__class__)):
                        # for i in range(self.device.TOTAL_LAYERIOMEMS):
                            # tiler._store_instrucs(i, tiler.instrucs[i])
                    if isinstance(tiler, self.a.__class__):
                        tiler._store_instrucs(
                            self.layer.rdmem,
                            tiler.instrucs[self.layer.rdmem])
                    elif isinstance(tiler, self.c.__class__):
                        tiler._store_instrucs(
                            self.layer.wrmem,
                            tiler.instrucs[self.layer.wrmem])
                    else:
                        tiler._store_instrucs()
        return self
    ###########################################################################

    @property
    def a(self): return self.layerio_reader
    @property
    def b(self): return self.weight_reader
    @property
    def c(self): return self.layerio_writer
    @property
    def post_gemm_params(self): return self.post_gemm_params_reader

    def base_tensor(self, key):
        return getattr(self, key)._unmodified_base_space._tensor_

    @property
    def device_a(self): return self.base_tensor('a')
    @property
    def device_c(self): return self.base_tensor('c')
    @property
    def device_b(self): return self.base_tensor('b')

    @property
    def device_a_mod(self):
        t = self.base_tensor('a').detach().clone()
        stride = t.stride()
        stride = {Cin: stride[0], H: stride[1], W: stride[2], }
        size = t.size()
        size = {Cin: size[0], H: size[1], W: size[2], }
        t = t.as_strided(
            (
                ceil(size[Cin]/self.sys_arr_size.j),
                size[H],
                size[W],
                self.sys_arr_size.j,
            ),
            (
                stride[Cin]*self.sys_arr_size.j,
                stride[H],
                stride[W],
                stride[Cin],
            )
        ).contiguous()
        return t

    @property
    def device_b_mod(self):
        t = self.base_tensor('b').detach().clone()
        stride = t.stride()
        stride = {H: stride[0], W: stride[1], Cin: stride[2], Cout: stride[3]}
        size = t.size()
        size = {H: size[0], W: size[1], Cin: size[2], Cout: size[3]}
        t = t.as_strided(
            (
                size[H],
                size[W],
                ceil(size[Cin]/self.sys_arr_size.j),
                ceil(size[Cout]/self.sys_arr_size.i),
                self.sys_arr_size.i,
                self.sys_arr_size.j,
            ),
            (
                stride[H],
                stride[W],
                stride[Cin]*self.sys_arr_size.j,
                stride[Cout]*self.sys_arr_size.i,
                stride[Cout],
                stride[Cin],
            )
        ).contiguous()
        return t

    @property
    def device_post_gemm_params(self): return self.base_tensor(
            'post_gemm_params_reader')

    def _debuglogging(self, ):
        from nnhw.top.cfg import config
        from copy import deepcopy
        # self = deepcopy(self)
        self.push_instrucs_enable[0] = False
        kwds = dict(context=False, value_only=True)
        if config.debuglevels.mem >= Level.HIGH:
            self.remap(Mapping.BASE)
            # self.log(f'{Mapping.BASE}', **kwds)
            self.log(self.layerio_reader.space, **kwds)
            # self.log(f'{Mapping.BASE}', **kwds)
            self.log(self.weight_reader.space, **kwds)
            # self.log(f'{Mapping.BASE}', **kwds)
            self.log(self.layerio_writer.space, **kwds)
            # self.log(f'{Mapping.BASE}')
            # self.log(self.post_gemm_params_reader.space)

        if config.debuglevels.mem >= Level.LOW:
            self.remap(Mapping.DEVICE)
            # self.log(f'{Mapping.DEVICE}', **kwds)
            if config.debuglevels.mem >= Level.MED:
                self.log(self.weight_reader.space, **kwds)
                self.log(self.post_gemm_params_reader.space, **kwds)
            # self.log(f'{Mapping.DEVICE}', **kwds)
            self.log(self.layerio_reader.space, **kwds)
            # self.log(f'{Mapping.DEVICE}')
            # self.log(self.layerio_writer.space)
            # self.log(f'{Mapping.DEVICE}')
            # self.log(self.post_gemm_params_reader.space)
        # self.remap(Mapping.TB_GEMM)

        # if config.DEBUGLEVEL >= Level.MED:
        #     self.remap(Mapping.TB_GEMM)
        #     self.log(f'{Mapping.TB_GEMM}')
        #     self.log(self.weight_reader.space)
        #     self.log(f'{Mapping.TB_GEMM}')
        #     self.log(self.layerio_reader.space)
        #     self.log(f'{Mapping.TB_GEMM}')
        #     self.log(self.layerio_writer.space)
        #     self.log(f'{Mapping.TB_GEMM}')
        #     self.log(self.post_gemm_params_reader.space)
        self.push_instrucs_enable[0] = True

    def _test_gemm(
            self,
            expected_gemm_output: torch.Tensor,
            expected_layer_output: Layerio
    ) -> None:
        from nnhw.top.cfg import config
        self.push_instrucs_enable[0] = False
        if self.config.testlevels.mem is Level.OFF:
            self.push_instrucs_enable[0] = True
            return
        self.remap(Mapping.HOST_GEMM)
        if self.config.testlevels.mem is Level.HIGH:
            self.remap(Mapping.DEVICE)
            self.remap(Mapping.DATA_TRANSFER)
            self.remap(Mapping.HOST_GEMM)
        self.n = prod(self.b.space[N][tile_fill]('size', list))
        self.tile_n = prod(self.b.space[N][tile_count]('size', list))
        observed_output = self.layerio_reader.data.matmul(
            self.weight_reader.data)
        self.assert_tensor_equal(observed_output, expected_gemm_output)
        config.setdefault('x', 0)
        if config.x == 0:
            config.x += 1
            self.push_instrucs_enable[0] = True
            return
        self.must_access_tiled_data = True
        self.b.must_access_tiled_data = True
        self.log(self.b.data)
        observed_output = self.test_tb_gemm()
        self.assert_tensor_equal(observed_output, expected_gemm_output)
        self.log(observed_output)
        self.must_access_tiled_data = False
        self.b.must_access_tiled_data = False
        self.push_instrucs_enable[0] = True

    def test_tb_gemm(self):
        self.remap(Mapping.TB_GEMM)
        self.log(self.b.data)
        aspc = self.a.space
        adata = self.a.data
        bdata = self.b.data
        self.tile_counts = {
            M: prod(aspc[tile_count][M]('size', list)),
            N: self.tile_n,
            K: prod(aspc[tile_count][K]('size', list)),
        }
        self.log(aspc)
        self.tile_sizes = {
            M: prod(aspc[M]('size', list)),
            N: self.n,
            K: prod(aspc[K]('size', list)),
        }
        self.sizes = {
            M: self.tile_sizes[M] * self.tile_counts[M],
            N: self.tile_sizes[N] * self.tile_counts[N],
            K: self.tile_sizes[K] * self.tile_counts[K],
        }
        dtype = torch.int32
        c = torch.zeros((self.sizes[M], self.sizes[N]), dtype=dtype)
        self.log(self.tile_counts)
        self.log(self.tile_sizes)
        donetile1 = False
        donetile1 = True
        for m in range(self.tile_counts[M]):
            for n in range(self.tile_counts[N]):
                ctile = torch.zeros((self.tile_sizes[M], self.tile_sizes[N]),
                                    dtype=dtype)
                for k in range(self.tile_counts[K]):
                    atile_i = (m * self.tile_counts[N] * self.tile_counts[K]
                               + n * self.tile_counts[K]
                               + k)
                    btile_i = atile_i
                    a = adata[atile_i]
                    b = bdata[
                        btile_i,
                        0:self.tile_sizes[N],
                        0:self.tile_sizes[K],
                    ].transpose(0, 1)
                    _ctile = torch.matmul(a, b)
                    ctile += _ctile
                    if not donetile1:
                        self.log(a, b)
                c[
                    m*self.tile_sizes[M]:(m+1)*self.tile_sizes[M],
                    n*self.tile_sizes[N]:(n+1)*self.tile_sizes[N],
                ] = ctile
                if not donetile1:
                    self.log(ctile)
                donetile1 = True
        return c

    def assert_tensor_equal(self, observed, expected):
        from nnhw.top.cfg import config
        observed_sum = torch.sum(observed)
        expected_sum = torch.sum(expected)
        if not observed.size() == expected.size():
            self.log(observed.size())
            self.log(expected.size())
            self.log(observed)
            self.log(expected)
            assert False
        if not torch.equal(observed, expected):
            diff_percent = ((observed_sum - expected_sum).abs()
                            / expected_sum * 100).item()
            self.log(observed)
            self.log(expected)
            self.log(diff_percent)
            assert False

    @property
    def _tilers(self) -> typ.Dict[str, Tiler]:
        return {key: value for key, value in self.__dict__.items()
                if isinstance(value, Tiler)}


from nnhw import instruc
