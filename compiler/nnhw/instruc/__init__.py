import copy
import typing as typ
from typing import Tuple, List
from collections import UserString
from enum import auto
from nnhw.top import (
    IntEnum, varname, init, noinit, AttrDict2, LowerStrEnum, snake2cammel,
    nameof, StrEnum, Enum)
import torch
from nnhw import top
from attrs import define, Factory, asdict
from math import ceil
from dataclasses import dataclass
import re
from debug import log


class pkg(IntEnum):
    """Python equivalent for instruc_pkg in rtl sv code.
    Values have to be manually synchronized for now.
    """
    POST_GEMM_PARAMS_WORD_WIDTH = 64

    WORD_WIDTH = 32
    BYTE_WIDTH = 8
    OPCODE_WIDTH = 8
    BODYLEN_WIDTH = 24
    HEADER_WIDTH = OPCODE_WIDTH + BODYLEN_WIDTH

    TOP_INSTRUC_WIDTH = 2

    TOTAL_OPCODES = 8
    TOTAL_OUT_FIFOS = TOTAL_OPCODES


class DecodedInstruc(AttrDict2):
    pass


class Instruc(DecodedInstruc):
    def __init__(self, name=None):
        super().__init__()
        if name is not None:
            self.setattr(nameof(name), name)

    def str(self):
        obj = copy.copy(self)
        for k, v in self.__dict__.items():
            obj.setattr(k, v)
            obj[k] = v
        return obj._str()

    def __str__(self):
        obj = copy.copy(self)
        for k, v in self.__dict__.items():
            obj.setattr(k, v)
            obj[k] = v
        return str(self.name)

    def _str(self): return super().__str__()
    def __repr__(self): return str(self)


class EncodedInstruc(AttrDict2):
    def __init__(self, data: Instruc):
        self.opcode: top.uint8 = 0
        self.bodylen: top.uint24 = 0
        self.data: Instruc = data
        self.setattr('name', self.data.name)

    @property
    def header(self): return (self.opcode * 2**24) + self.bodylen


class DataInstruc(Instruc, top.DeepCopyableTensorValues):
    def __init__(self, name, value=torch.Tensor([])):
        super().__init__(name)
        self.value = value


class MemInstruc(Instruc):
    def __init__(self, name, *args, **kwds):
        """These attrs represent the values of the value fields / parameters
        contained in a mem_u instruc.
        """
        self.offset: int = 0
        self.stride: typ.List[int] = []
        self.size: typ.List[int] = []
        super().__init__(name, *args, **kwds)


@define
class Reg:
    name: str
    width: int
    value: int = 0

    @property
    def offset(self):
        result = 0
        for reg in regs:
            if reg.name == self.name:
                break
            result += reg.width
        return result

    def instruc_value(self, value=None):
        if value is None:
            value = self.value
        return value * 2**self.offset


@define
class Regs(AttrDict2):
    RUN: Reg = Reg(varname(), 1, 1)
    RESET0: Reg = Reg(varname(), 1, 1)
    RESET1: Reg = Reg(varname(), 1, 1)
    RESET2: Reg = Reg(varname(), 1, 1)
    TIMEOUT_BIT: Reg = Reg(varname(), 5, 0)
    LOAD: Reg = Reg(varname(), 1, 1)
    START_TIMER: Reg = Reg(varname(), 1, 1)
    RESTART_TIMER: Reg = Reg(varname(), 1, 1)
    STOP_TIMER: Reg = Reg(varname(), 1, 1)
    RECORD_TIMER: Reg = Reg(varname(), 1, 1)
    GET_RESULTS: Reg = Reg(varname(), 1, 1)
    STALL: Reg = Reg(varname(), 1, 0)

    def __iter__(self):
        for v in self.values():
            yield v


regs = Regs()


class Write2Reg(Instruc):
    name = snake2cammel(re.sub(r'.*\.(\w+)$', r'\1', __qualname__))

    def __init__(self, reg: regs, value=None):
        if value is None:
            value = reg.value
        super().__init__(self.name)
        self.value = reg.instruc_value(value)


class Stall(Write2Reg):
    def __init__(self): super().__init__(regs.STALL)

class Run(Write2Reg):
    def __init__(self): super().__init__(regs.RUN)

class Reset0(Write2Reg):
    def __init__(self): super().__init__(regs.RESET0)

class Reset1(Write2Reg):
    def __init__(self): super().__init__(regs.RESET1)

class Reset2(Write2Reg):
    def __init__(self): super().__init__(regs.RESET2)


class Reset(Write2Reg):
    def __init__(self):
        super().__init__(regs.RESET1)
        reset0 = Reset0()
        reset1 = Reset1()
        reset2 = Reset1()
        self.value = reset0.value | reset1.value | reset2.value


class Load(Write2Reg):
    def __init__(self): super().__init__(regs.LOAD)


class GetResults(Write2Reg):
    def __init__(self): super().__init__(regs.GET_RESULTS)


class RecordTimer(Write2Reg):
    def __init__(self): super().__init__(regs.RECORD_TIMER)


class StopTimer(Write2Reg):
    def __init__(self): super().__init__(regs.STOP_TIMER)


class RestartTimer(Write2Reg):
    def __init__(self): super().__init__(regs.RESTART_TIMER)


class StartTimer(Write2Reg):
    def __init__(self): super().__init__(regs.START_TIMER)


class Layerio(DataInstruc):
    name = snake2cammel(re.sub(r'.*\.(\w+)$', r'\1', __qualname__))

    def __init__(self, value):
        super().__init__(self.name, value)


class LayerParams(DataInstruc):
    name = snake2cammel(re.sub(r'.*\.(\w+)$', r'\1', __qualname__))

    def __init__(self, *args, **kwds):
        self.inputmem_size_w_c: top.int32 = 0
        self.inputmem_total_layer_reads: top.int32 = 0
        self.inputmem_tile_size_m: top.int32 = 0
        self.total_inference_writes: top.int32 = -1
        self.in_last_inference: top.int32 = 0
        self.load_input: top.int32 = 0
        self.tile_size_m: top.int32 = 0
        self.size_w_gemm: top.int32 = 0
        self.size_h_gemm: top.int32 = 0
        self.size_w_pool_padding: top.int32 = 0
        self.size_h_pool_padding: top.int32 = 0
        self.size_w_pooling: top.int32 = 0
        self.size_h_pooling: top.int32 = 0
        self.total_weight_writes_all_layers: top.int32 = 0
        self.total_pgp_writes_all_layers: top.int32 = 0
        self.total_weight_reads_all_layers: top.int32 = 0
        self.total_pgp_reads_all_layers: top.int32 = 0
        self.total_layerio_reads: top.int32 = 0
        self.total_weight_reads: top.int32 = 0
        self.hw_size_padding: top.int32 = 0
        self.total_c_padding_writes: top.int32 = 0
        self.size_w_c: top.int32 = 0
        self.c_padding: top.int32 = 0
        self.pool_size: top.int32 = 0
        self.pool_stride: top.int32 = 0
        self.pool_padding: top.int32 = 0
        self.avg_pool_denom: top.int32 = 9
        self.pool_type: top.int32 = 0
        self.islastlayer: top.int32 = 0
        self.islast_inbatch: top.int32 = 0
        self.layeriomem_wrsel: top.int32 = 0
        self.layeriomem_rdsel: top.int32 = 0
        self.loading_params_valid: top.int32 = 1
        self.valid: top.int32 = 1
        Instruc.__init__(self)


class PostGemmParams(DataInstruc):
    name = snake2cammel(re.sub(r'.*\.(\w+)$', r'\1', __qualname__))

    def setattr(self, k, v):
        super().setattr(k, v)
        if k not in ['value', 'name']:
            raise AttributeError

    def __init__(self):
        super().__init__(self.name)


class MemInstrucs(list):
    def __init__(self, name):
        self.name = name
        super().__init__()


@define
class Layer(AttrDict2):
    layer_params: LayerParams = init(lambda: LayerParams())
    layerio_wr_instrucs: MemInstrucs = init(lambda: MemInstrucs(varname()))
    layerio_rd_instrucs: MemInstrucs = init(lambda: MemInstrucs(varname()))
    weight_rd_instruc: MemInstruc = init(lambda: MemInstruc(varname()))
    post_gemm_params_rd_instruc: MemInstruc = init(
        lambda: MemInstruc(varname()))
    post_gemm_params: PostGemmParams = init(
        lambda: PostGemmParams())
    weight: DataInstruc = init(lambda: DataInstruc(varname()))
    #
    Name = LowerStrEnum(varname(), ' '.join([
        k.upper() for k in __annotations__]))

    @classmethod
    def from_device(cls, device: 'Device'):
        obj = cls()
        for i in range(device.TOTAL_LAYERIOMEMS):
            obj.layerio_wr_instrucs.append(MemInstruc(
                f'layerio_{i}_wr_instruc'))
            obj.layerio_rd_instrucs.append(MemInstruc(
                f'layerio_{i}_rd_instruc'))
        return obj


InstrucName = LowerStrEnum(
    varname(), ' '.join([
        Layerio.name.upper(),
        *Layer.Name.__members__,
        Write2Reg.name.upper(),
    ]))


def rdwr_instruc_opcodes(type_, device: 'Device'):
    instruc_opcodes = []
    for i in range(device.TOTAL_LAYERIOMEMS):
        instruc_opcodes.append(f'layerio_{i}_{type_}_instruc')
    return instruc_opcodes


def get_opcodes(device: 'Device'):
    instruc_names = [Layerio.name, InstrucName.LAYER_PARAMS, ]
    instruc_names += rdwr_instruc_opcodes('wr', device)
    instruc_names += rdwr_instruc_opcodes('rd', device)
    for k, v in InstrucName.__members__.items():
        if v not in [InstrucName.LAYERIO,
                     InstrucName.LAYER_PARAMS,
                     InstrucName.LAYERIO_WR_INSTRUCS,
                     InstrucName.LAYERIO_RD_INSTRUCS]:
            instruc_names += [v]
    Opcode = top.IntEnum(varname(), instruc_names)
    return Opcode


from .encoder import Encoder
from nnhw.top.device import Device
