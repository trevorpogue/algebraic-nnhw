import unittest
import torch
from debug import log
from nnhw.instruc import encoder
from nnhw import instruc
from nnhw.rxtx import DeviceController
from nnhw.top.cfg import config


class TestEncoder(unittest.TestCase):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.device = DeviceController()
        config.send_model = True

    def test(self):
        self.xtest_arith_instruc()
        self.xtest_b_instruc()
        self.xtest_b_instruc_large()

    def xtest_arith_instruc(self):
        name = instruc.Name.POST_GEMM_PARAMS
        decoded_instruc = instruc.PostGemmParamsInstruc(name)
        decoded_instruc.zc = 1
        decoded_instruc.za_bk = 2
        decoded_instruc.m_val = 3
        decoded_instruc.m_shift = 3
        decoded_instruc.activation = 1
        decoded_instruc.concat_fields()
        encoder.push_instruc(decoded_instruc)
        self.device.send_model()
        encoded_instruc = encoder.read_back_encoded_instrucs()
        opcode = instruc.Opcode[name]
        header = [opcode, 0, 0, 2]  # opcode, len_b3, len_b2, len_b1, len_b0
        body = list(bytes(decoded_instruc.value.item().to_bytes(8, 'big')))
        assert encoded_instruc == header + body

    def xtest_tiler_instruc(self):
        name = instruc.Name.LAYERIO_RD_INSTRUC
        decoded_instruc = instruc.MemInstruc(name)
        decoded_instruc.offset = 3
        decoded_instruc.stride = [2**16 + 2, 255] * 42
        decoded_instruc.range = [2**24 + 2**16 + 2**8 + 1, 0] * 42
        encoder.push_instruc(decoded_instruc)
        self.device.send_model()
        encoded_instruc = encoder.read_back_encoded_instrucs()
        opcode = instruc.Opcode[name]
        header = [opcode, 0, 0, 169]  # opcode, len_b3, len_b2, len_b1, len_b0
        offset = 3
        range = [
            0, 0,
            1, 1, 1, 1,
            0, 0, 0, 0,
        ] * 42
        stride = [
            0, 0,
            0, 1, 0, 2,
            0, 0, 0, 255,
        ] * 42
        assert encoded_instruc == header + [offset] + range + stride

    def xtest_b_instruc(self):
        name = instruc.Name.WEIGHT
        decoded_instruc = instruc.DataInstruc(name)
        decoded_instruc.value = torch.tensor([0, 2, -2, 255])
        encoder.push_instruc(decoded_instruc)
        self.device.send_model()
        encoded_instruc = encoder.read_back_encoded_instrucs()
        opcode = instruc.Opcode[name]
        header = [opcode, 0, 0, 1]  # opcode, len_b3, len_b2, len_b1, len_b0
        data = [0, 2, 254, 255]  # body data
        assert encoded_instruc == header + data

    def xtest_b_instruc_large(self):
        name = instruc.Name.WEIGHT
        decoded_instruc = instruc.DataInstruc(name)
        decoded_instruc.value = torch.tensor([0, 2, -2, 255] * 257)
        encoder.push_instruc(decoded_instruc)
        self.device.send_model()
        encoded_instruc = encoder.read_back_encoded_instrucs()
        opcode = instruc.Opcode[name]
        header = [opcode, 0, 1, 1]  # opcode, len_b3, len_b2, len_b1, len_b0
        data = [0, 2, 254, 255] * 257  # body data
        assert encoded_instruc == header + data
