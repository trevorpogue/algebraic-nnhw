from cocotb import fork
from cocotb.triggers import Edge, FallingEdge, RisingEdge, Timer
from debug import log
from tests.instruc import sequences as seq
from tests import top
from tests.top import uvm
from tests.top.uvm.base import non_overlapping_coroutine
from nnhw.instruc import pkg


class Driver(uvm.Driver):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.opcode = 0

    async def reset_phase(self, phase):
        await self.reset_master_fifo(self.dut.rx)
        for fifo in self.slave_fifos:
            await self.reset_slave_fifo(fifo)
        await super().reset_phase(phase)

    async def reset_master_fifo(self, fifo):
        fifo.wrreq <= 0
        fifo.d.value <= 0

    async def reset_slave_fifo(self, fifo):
        pass

    async def drive_seqitem(self, instruc):
        await self.drive_instruc(instruc.encoded)

    async def drive_instruc(self, instruc):
        instruc.opcode = self.opcode
        self.opcode = (self.opcode + 1) % len(self.opcodes)
        await self.drive_word(instruc.header)
        for word in instruc.body:
            await self.drive_word(word)
        self.dut.rx.wrreq <= 0
        self.log(f'drove encoded instruc {instruc}')

    async def drive_word(self, word):
        while self.dut.rx.half_full.value:
            self.dut.rx.wrreq <= 0
            await self.clk_posedges_(self.dut.rxtx_clk)
        self.dut.rx.d.value <= word
        self.dut.rx.wrreq <= 1
        await self.clk_posedges_(self.dut.rxtx_clk)


class Monitor(top.Monitor):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

    async def sample_seqitem_input(self, seqitem):
        self.fork(self.sample_seqitem(seqitem))
        # await self._sample_seqitem(seqitem)

    async def sample_seqitem(self, seqitem):
        forks = []
        forks.append(self.fork(
            self.get_encoded_instruc(seqitem.encoded)
        ))
        forks.append(self.fork(self.get_decoded_instruc(seqitem.decoded)))
        await self.join(*forks)
        self.score(seqitem)

    @non_overlapping_coroutine
    async def get_encoded_instruc(self, instruc):
        fifo = self.dut.rx
        await self.wait_(fifo.wrreq)
        instruc.set_header(fifo.d.value.value)
        await self.clkcycles(1)
        await self.get_instruc_body(instruc, fifo)
        self.log(f'observed encoded instruc {instruc}')

    @non_overlapping_coroutine
    async def get_decoded_instruc(self, instruc):
        forks = []
        for fifo in self.slave_fifos:
            forks.append(fork(self.wait_(fifo.wrreq)))
        await self.join_any(*forks)
        for fifo, opcode in zip(self.slave_fifos, self.opcodes):
            if bool(fifo.wrreq.value):
                break
        self.log(f'observing decoded instruc for opcode {opcode}')
        decoded = instruc
        decoded.opcode = opcode
        decoded.set_header(instruc.parent.encoded.header)
        await self.get_instruc_body(decoded, fifo)
        self.log(f'observed decoded instruc for opcode {opcode}')

    async def get_instruc_body(self, instruc, fifo):
        for i in range(instruc.bodylen):
            instruc.body += [fifo.d.value.value.integer]
            await self.wait_(fifo.wrreq)
            await self.clkcycle

    def score(self, seqitem):
        encoded_instruc = seqitem.encoded
        decoded_instruc = seqitem.decoded
        success = True
        for attr in encoded_instruc.data_attrs:
            input_value = getattr(encoded_instruc, attr)
            decoded_value = getattr(decoded_instruc, attr)
            if not input_value == decoded_value:
                success = False
        msg = (f'\nobserved:\n{decoded_instruc},'
               + f'\nexpected c:\n{encoded_instruc}\n\n')
        top.Monitor.score(self, success, msg)


class UnitTest(top.Test):
    def __init__(self, *args, **attrs):
        super().setattrs(*args, **attrs)
        self.log_en = self.set(attrs, True)
        dir(self.dut)  # solves a cocotb bug when getting dut
        try:
            self.dut = self.set(attrs, self.dut.instruc[4].dut)
        except AttributeError:
            return
        self.set_globals(attrs)
        self.total_seqitems = self.set(attrs, 10)
        self.max_clk_cycles = self.set(attrs, 1000)
        super().uvm_init(Driver, Monitor, seq.InstrucDecoding,
                         *args, **attrs)

    def set_globals(self, attrs):
        fifos = [
            self.dut.layerio,
            self.dut.weight,
            self.dut.post_gemm_params,
            self.dut.weight_rd_instruc,
            self.dut.post_gemm_params_rd_instruc,
            self.dut.top_instruc,
        ]
        self.slave_fifos = self.set(attrs, fifos)
        self.opcodes = self.set(attrs, range(pkg.TOTAL_OPCODES))


class InstrucTest(top.GroupTest):
    UnitTest_ = UnitTest
