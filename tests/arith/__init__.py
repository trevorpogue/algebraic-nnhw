import math
import torch
from cocotb.triggers import Event
from debug import log
from nnhw.top import FIPMethod, nameof, varname, DTYPE, IO, IOs, Device
from tests import top
from utils import args2attrs
from itertools import repeat


def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)


def signed(n, WIDTH):
    most_negative_value = 2 ** (WIDTH - 1)
    if n >= most_negative_value:
        return n - 2 ** WIDTH
    else:
        return n


class VerilogParams:
    def __init__(self, dut):
        self.set_verilog_params(dut)

    def set_verilog_params(self, dut):
        self.dtype = DTYPE
        self.A_WIDTH: int = dut.A_WIDTH.value
        self.B_WIDTH: int = dut.B_WIDTH.value
        self.A_SIGNED: int = dut.A_SIGNED.value
        self.B_SIGNED: int = dut.B_SIGNED.value
        self.C_WIDTH: int = dut.C_WIDTH.value
        self.AMAT_WIDTH: int = dut.AMAT_WIDTH.value
        self.BMAT_WIDTH: int = dut.BMAT_WIDTH.value
        self.WIDTH: int = dut.A_WIDTH.value  # default width
        self.FIP_METHOD: str = dut.FIP_METHOD.value
        self.FIP_METHOD: FIPMethod = dut.FIP_METHOD.value
        for member in FIPMethod.__members__.values():
            if self.FIP_METHOD == member:
                self.FIP_METHOD = member
        self.PE_INPUT_DEPTH: int = dut.PE_INPUT_DEPTH.value
        self.DSP_LATENCY: int = dut.DSP_LATENCY.value
        self.SZI: int = dut.SZI.value
        self.SZJ: int = dut.SZJ.value
        self.SZJ_PE: int = dut.SZJ_PE.value
        self.USE_SOFT_RESET = dut.USE_SOFT_RESET_.value
        self.inputkeys = [IO.A, IO.B]
        self.iokeys = [IO.A, IO.B, IO.C, IO.GEMM]


class Component(VerilogParams):
    f"""This class has been replaced by {IO} and {Device} but is kept
    here for backwards compatibility for old code depending on it."""
    a_key = IO.A
    b_key = IO.B
    post_gemm_params_key = IO.POST_GEMM_PARAMS
    gemm_key = IO.GEMM
    quantization_key = IO.QUANTIZATION
    pool_padding_key = IO.POOL_PADDING
    pooling_key = IO.POOLING
    c_key = IO.C
    conv_io_keys = [a_key, b_key, post_gemm_params_key,
                     gemm_key, quantization_key]
    conv_outputs_keys = [gemm_key, quantization_key]
    post_conv_io_keys = [pool_padding_key, pooling_key, c_key]
    io_keys = [a_key, b_key, post_gemm_params_key, gemm_key,
               quantization_key, pool_padding_key, pooling_key, c_key]

    def __init__(self, *args, **attrs):
        self.set_verilog_params(self.dut)
