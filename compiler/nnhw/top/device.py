from nnhw.top import (
    FIPMethod, IJParam2, noinit, IO, AttrDict, ppstr, Op)
from typing import Dict, Any
from attrs import define, field, asdict
import torch
import re
from nnhw.top import read_verilog_param, Path
from debug import log
from math import ceil


@define
class Device(AttrDict):
    """Data structure defining the FPGA architecture to compile for."""
    SZI: int = 0
    SZJ: int = 0
    FIP_METHOD: str = FIPMethod.BASELINE
    USE_SOFT_RESET: bool = True
    RECORD_PERF_RESULTS: int = 0
    RESULT_IO: str = "C"
    RESULT_FIFOS_DEPTH: int = 2**16
    USE_RESULT_FIFOS: bool = False
    USE_RESULT_FIFOS_FULL: bool = False
    LAYERIOMEM_SIZE: int = 2**18
    LAYERIOMEM_CLK_DIV: int = 4
    PGP_MEM_SIZE: int = 2**21
    WEIGHTMEM_SIZE: int = 2**31
    WEIGHTMEM_WIDTH: int = 2**9
    A_WIDTH: int = 8
    B_WIDTH: int = 8
    C_WIDTH: int = 32
    LAYERIO_WIDTH: int = 8
    MAC_WIDTH: int = 32
    MAX_TILE_SIZE_M: int = 128
    OTHER_MAX_W: int = 128
    MAX_W: int = 128
    MAX_H: int = 128
    LAYER_PARAM_WIDTH: int = 32
    DO_POOL_PADDING: int = 0
    LAYERIO_SIGNED: int = False
    WEIGHT_SIGNED: int = False
    TOTAL_LAYERIOMEMS: int = 0
    LAYERIOMEM0_SIZE: int = 0
    LAYERIOMEM0_SZJ: int = 0
    LAYERIOMEM1_SIZE: int = 0
    LAYERIOMEM1_SZJ: int = 0
    LAYERIOMEM2_SIZE: int = 0
    LAYERIOMEM2_SZJ: int = 0
    M_VAL_WIDTH: int = 8
    M_VAL_OFFSET: int = 48
    ZA_BK_WIDTH: int = 32
    ZA_BK_OFFSET: int = 16
    ACTIVATION_WIDTH: int = 2
    ACTIVATION_OFFSET: int = 14
    M_SHIFT_WIDTH: int = 6
    M_SHIFT_OFFSET: int = 8
    ZC_WIDTH: int = 8
    ZC_OFFSET: int = 0
    TOTAL_DIGITS: int = 0
    BURST_COUNT: int = 0
    WEIGHTMEM_CLK_DIV: int = 0
    MXU_SZI: int = 0
    MXU_SZJ: int = 0

    @property
    def macros(self): return [
    ]
    @property
    def min_tile_size_m(self): return 1

    def next_highest_pow2(self, n):
        pow2 = 1
        while pow2 <= n:
            pow2 *= 2
        return pow2/2

    def load_model(self, nn: 'arith.NN'):
        from nnhw.rxtx.device_controller import DeviceController
        device_controller = DeviceController()
        device_controller.load_nn(nn.model_instruc_name)

    def send_instruc(self, instruc: 'instruc.Instruc'):
        from nnhw.rxtx.device_controller import DeviceController
        from nnhw.instruc import Encoder
        Encoder()([instruc], instruc.name)
        DeviceController().tx(instruc.name)

    def __attrs_post_init__(self):
        assert self.MXU_SIZE.i == self.MXU_SIZE.j, print(
            'Only supportin MXU_SIZE i == j')

    def set_from_verilog_params(self, rtl_path, config):
        file_path = rtl_path + '/top/define.svh'
        for file in ['/top/define.svh', '/top/pkg.sv', '/instruc/pkg.sv',
                     '/mem/pkg.sv']:
            self._set_from_verilog_params(rtl_path, file, config)
        self.FIP_METHOD = read_verilog_param('FIP_METHOD', file_path)
        self.FIP_METHOD = re.sub(r'.*::(\w+)', r'\1', self.FIP_METHOD)
        self.FIP_METHOD = FIPMethod.__members__[self.FIP_METHOD]
        self.RESULT_IO = self.RESULT_IO.lower()
        self.LAYERIOMEM0_SZJ = self.SZJ
        self.LAYERIOMEM1_SZJ = self.SZJ
        self.LAYERIOMEM2_SZJ = self.SZJ
        for i in range(3):
            k = f'LAYERIOMEM{i}_SIZE'
            v = getattr(self, k)
            v *= self.SZJ/(self.next_highest_pow2(self.SZJ))
            setattr(self, k, v)

    def _set_from_verilog_params(self, rtl_path, file='define.svh',
                                 config=None):
        file_path = rtl_path + file
        for k in self:
            v = read_verilog_param(k, file_path, ismacro=k in self.macros)
            if v is not None:
                if v == 'LAYERIO_WIDTH':
                    v = self.A_WIDTH
                if v == 'LAYERIO_SIGNED':
                    v = self.LAYERIO_SIGNED
                if v == 'WEIGHT_WIDTH':
                    v = self.A_WIDTH
                if v == 'WEIGHT_SIGNED':
                    v = self.WEIGHT_SIGNED
                if v in asdict(self):
                    v = getattr(self, k)
                if k == 'SZI' and config.istest:
                    v = config.mxu_size
                if k == 'SZJ':
                    v = self.SZI
                self[k] = v
                v = self.get(k, v)
        if config.istest:
            self.A_WIDTH = config.bw
            self.B_WIDTH = config.bw
            self.LAYERIO_WIDTH = config.bw
            self.WEIGHT_WIDTH = config.bw
        self.MXU_SZI = self.SZI
        self.MXU_SZJ = self.SZI

    @property
    def MXU_SIZE(self): return IJParam2(self.SZI, self.SZJ)
    @property
    def atype(self): return (torch.int8 if self.LAYERIO_SIGNED else torch.uint8)
    @property
    def btype(self): return (torch.int8 if self.WEIGHT_SIGNED else torch.uint8)
    @property
    def gemm_type(self): return (
            torch.int8 if self.WEIGHT_SIGNED or self.LAYERIO_SIGNED
            else torch.uint8)

    @property
    def dtypes(self) -> Dict[IO, Any]:
        return AttrDict({
            IO.A: self.atype,
            IO.B: self.btype,
            IO.POST_GEMM_PARAMS: torch.int64,
            IO.GEMM: torch.int32,
            IO.QUANTIZATION: self.atype,
            IO.POOL_PADDING: self.atype,
            IO.POOLING: self.atype,
            IO.C: self.atype,
            IO.RESULT: self.atype,
        })

    @property
    def WIDTHS(self) -> Dict[IO, int]: return AttrDict({
            IO.A: self.A_WIDTH,
            IO.B: self.B_WIDTH,
            IO.POST_GEMM_PARAMS: 62,
            IO.GEMM: self.C_WIDTH,
            IO.QUANTIZATION: self.A_WIDTH,
            IO.POOL_PADDING: self.A_WIDTH,
            IO.POOLING: self.A_WIDTH,
            IO.C: self.A_WIDTH,
            IO.RESULT: self.A_WIDTH,
        })

    @property
    def SIGNED(self) -> Dict[IO, int]: return AttrDict({
            IO.A: self.LAYERIO_SIGNED,
            IO.B: self.WEIGHT_SIGNED,
            IO.POST_GEMM_PARAMS: False,
            IO.GEMM: True,
            IO.QUANTIZATION: False,
            IO.POOL_PADDING: False,
            IO.POOLING: False,
            IO.C: self.LAYERIO_SIGNED,
            IO.RESULT: self.LAYERIO_SIGNED,
    })
    for member in FIPMethod.__members__.values():
        if FIP_METHOD == member:
            FIP_METHOD = member

    def __str__(self):
        return ppstr(asdict(self))
