from math import ceil, floor
from typing import Any, List, NewType, Union
import cocotb
from debug import log
from nnhw.instruc import encoder, pkg
from nnhw.rxtx import DeviceController
from tests.top import uvm
from random import randrange
from nnhw.top import FIPMethod, nameof, varname
from nnhw import instruc


uint8 = NewType('uint8', int)
uint24 = NewType('uint24', int)
uint32 = NewType('uint32', int)

device = DeviceController()


class InstrucWord(uvm.SequenceItem):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.data: uint32 = 0
        self.data = randrange(2 ** pkg.WORD_WIDTH)
        self.data_attrs = nameof(self.data)


class InstrucByte(uvm.SequenceItem):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.data: uint8 = 0
        self.data = randrange(2 ** pkg.BYTE_WIDTH)
        self.data_attrs = nameof(self.data)


class Instruc(uvm.SequenceItem):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.opcode: uint8 = 0
        self.bodylen: uint24 = 0
        self.body: List[uint32] = []
        self.data_attrs = nameof(self.opcode, self.bodylen, self.body, )

    def randomize(self):
        self.opcode = randrange(pkg.TOTAL_OPCODES)
        self.bodylen = randrange(1, 8)
        self.body = []
        for i in range(self.bodylen):
            word = InstrucWord(**self.attrs)
            self.body += [word.data]

    def __str__(self):
        s = ''
        prefix = '    '
        s += f'{prefix}{self.opcode}, {self.bodylen},\n'
        s += self.body_str()
        return s

    def body_str(self):
        s = ''
        prefix = '    '
        for word in self.body:
            s += f'{prefix}{word:X}\n'
        return s

    @property
    def header(self): return (self.opcode * 2**24) + self.bodylen

    def set_header(self, word):
        self.set_header_from_bytes(self.word2bytes(word))

    def set_header_from_bytes(self, header_bytes):
        self.opcode = header_bytes[0]
        self.bodylen = self.bytes2word(header_bytes[1:4])

    def bytes2word(self, bytes): return int.from_bytes(bytes[0:4], 'big')

    def word2bytes(self, word: Union[int, cocotb.binary.BinaryValue]):
        if word.__class__ is cocotb.binary.BinaryValue:
            word = word.integer
        return word.to_bytes(4, 'big')


class InstrucDecoding(uvm.SequenceItem):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.cleanup(kwds)
        self.encoded = Instruc(*args, **kwds)
        self.decoded = Instruc(*args, **kwds)
        self.data_attrs = nameof(self.encoded, self.decoded)

    def randomize(self):
        self.encoded.randomize()
