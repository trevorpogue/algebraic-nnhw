import pathlib
import typing as typ
from copy import deepcopy
from enum import Enum
from typing import Dict, List, Literal, NewType, Union
import numpy as np
import torch
from nnhw import instruc, top
from nnhw.top import Path, chain, IO, prod, tohex, noinit, IntEnum
from nnhw.instruc import (InstrucName, DecodedInstruc)
from debug import log
from attrs import define, field, Factory
from nnhw.top.device import Device


def isin(value, values):
    value_isin_values = False
    for v in values.__members__.values():
        if value == v:
            value_isin_values = True
            break
    return value_isin_values


@define
class Encoder:
    """
    Performs a simple coding transformation on the encoded_instruction data
    before being sent to device.
    The coding involves pre-pending an encoded_instruction id
    tag, the length of the incoming encoded_instruction data, followed by the
    encoded_instructions data/body.
    Encoded_Instruction bodies can contain the raw input/weight
    data, quantization parameters, counter sizes/strides for tiling, and
    possibly a couple other types of data.
    """
    device: Device = noinit()

###############################################################################
# Public API
###############################################################################
    def __call__(self, decoded_instrucs: instruc.Instruc,
                 fname: str, device: Device) -> None:
        """Encode the pushed decoded inatrucs and write them to file."""
        # set ndarray dtype as big-endian uint32 with extra dim splitting the 4
        # bytes into 4 uint8's:
        self.device = device
        encoded_instrucs = np.array([], dtype='>u4').view('uint8').flatten()
        for instruc_ in decoded_instrucs:
            encoded_instruc = self._encode_instruc(instruc_)
            encoded_instrucs = np.concatenate(
                (encoded_instrucs, encoded_instruc), axis=None)
        self._write_encoded_instrucs_to_file(encoded_instrucs, fname)

    def read_back_encoded_instrucs(self, prefix: str = ''
                                   ) -> typ.List[top.uint8]:
        """Read previously encoded instrucs back from file."""
        from nnhw.top.cfg import config
        if config.istest:
            return []
        fname = f'{prefix}'
        with open(self.instruc_path(fname), 'rb') as f:
            encoded_instruc = f.read()
        return list(encoded_instruc)

###############################################################################
# non-public methods
###############################################################################

# -----------------------------------------------------------------------------
# coding:
# genarate header, convert 32-bit int arrays to bytes, etc.
# no compression or anything fancy, just directly convert data to byte/hex file
# with a simple header - an opcode + len of following data in words

    def _encode_instruc(self, decoded_instruc: DecodedInstruc) -> np.ndarray:
        encoded_instruc = []
        for field in decoded_instruc.values():
            encoded_instruc_ = self._field_tolist(
                decoded_instruc.name, field)
            encoded_instruc_ = self._pad(decoded_instruc.name,
                                         encoded_instruc_)
            encoded_instruc = np.concatenate(
                (encoded_instruc, encoded_instruc_), axis=None)
        encoded_instruc = self._add_header(
            decoded_instruc.name, encoded_instruc)
        return self._to_ndarray(decoded_instruc.name, encoded_instruc)

    def _field_tolist(self, decoded_instruc_name: str, field):
        if decoded_instruc_name == InstrucName.LAYERIO:
            field = field.to(self.device.atype)
        if decoded_instruc_name == InstrucName.WEIGHT:
            field = field.to(self.device.btype)
        if decoded_instruc_name == InstrucName.POST_GEMM_PARAMS:
            data = field
            field = []
            for chan_i in range(data.size(0)):
                field += list(data[chan_i].item().to_bytes(8, 'big'))
        if isinstance(field, torch.Tensor):
            field = field.flatten()
        field = np.array(field)
        return field

    def _pad(self, decoded_instruc_name: InstrucName,
             list_: List[int]) -> List[int]:
        len_ = list_.size
        new_list = []
        if decoded_instruc_name == InstrucName.WRITE2_REG:
            if list_.item() == 0:
                # is stall command
                pad_n = len_ % 2
                new_list += [0] * pad_n
        if (decoded_instruc_name in [
                InstrucName.LAYERIO, InstrucName.WEIGHT,
                InstrucName.POST_GEMM_PARAMS
        ]):
            pad_n = len_ % 4
            new_list += [0] * pad_n
        new_list = np.array(new_list)
        return np.concatenate((list_, new_list), axis=None)

    def _add_header(self, decoded_instruc_name: InstrucName,
                    encoded_instruc: List[int]) -> List[int]:
        body_len = [encoded_instruc.size]
        if (decoded_instruc_name in [
                InstrucName.LAYERIO, InstrucName.WEIGHT,
                InstrucName.POST_GEMM_PARAMS
        ]):
            body_len[0] /= 4
        body_len = np.array(
            body_len, dtype=np.uint32
        ).astype('>u4').view('uint8').flatten()
        body_len = body_len.tolist()
        Opcode = instruc.get_opcodes(self.device)
        header = ([Opcode[decoded_instruc_name]]
                  + body_len[1:])
        if (decoded_instruc_name in [
                InstrucName.LAYERIO, InstrucName.WEIGHT,
                InstrucName.POST_GEMM_PARAMS
        ]):
            pass
        else:
            header = np.array(
                header, dtype=np.uint8
            ).view('>u4').flatten().tolist()
        header = np.array(header)
        return np.concatenate((header, encoded_instruc), axis=None)

    def _to_ndarray(self, decoded_instruc_name: InstrucName,
                    encoded_instruc: List[int]):
        if (decoded_instruc_name in [
                InstrucName.LAYERIO, InstrucName.WEIGHT,
                InstrucName.POST_GEMM_PARAMS
        ]):
            encoded_instruc = encoded_instruc.astype(dtype=np.uint8).flatten()
        else:
            encoded_instruc = encoded_instruc.astype(dtype=np.uint32).astype(
                '>u4').flatten()
            encoded_instruc = encoded_instruc.view('uint8').flatten()
        return encoded_instruc

# -----------------------------------------------------------------------------
# file io

    def instruc_path(self, fname: str) -> str:
        return Path.INSTRUC_CACHE + '/' + fname + '.instruc'

    def _write_encoded_instrucs_to_file(
            self, encoded_instruc: np.ndarray, prefix: str = ''
    ) -> None:
        from nnhw.top.cfg import config
        if config.istest:
            return
        log_en = config.debuglevels.encoder
        fname = str(prefix)
        encoded_instruc = encoded_instruc.tostring()
        encoded_instruc_len = len(encoded_instruc)
        fpath = self.instruc_path(fname)
        log(fpath)
        with open(fpath, 'wb') as f:
            f.write(encoded_instruc)
        fsize = pathlib.Path(fpath).stat().st_size
        assert fsize == encoded_instruc_len, print(fsize, encoded_instruc_len)
