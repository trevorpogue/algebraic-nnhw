import typing as typ
from math import ceil
from debug import log
from uvm.macros import uvm_component_utils
from varname import nameof as nameof
from tests import top
from tests.top import uvm
from tests.top.tb_utils.tb_shift_vec import Monitor as ShiftVecMonitor
from varname import nameof as nameof


class EnDriver(top.RegDriver):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        if self.DEPTH == 4:
            self.post_seqitem_delay = ceil(self.DEPTH)
        else:
            self.post_seqitem_delay = ceil(self.DEPTH/2)

    async def reset_phase(self, phase):
        self.raise_objection(phase)
        self.dut.en <= 0
        self.dut.d.info.new_tile_k <= 0
        super().reset_phase(phase)
        self.drop_objection(phase)

    async def drive_seqitem(self, seqitem: top.VecSeqItem):
        self.log(f'driving en0')
        self.dut.d.info.new_tile_k <= 1
        self.dut.en[0] <= 1
        await self.clk_posedge
        self.dut.d.info.new_tile_k <= 0
        self.dut.en[0] <= 0
        await super().clkcycles(self.DEPTH - 1)

        self.log(f'driving en1')
        self.dut.en[1] <= 1
        self.dut.en[0] <= 0
        self.dut.d.info.new_tile_k <= 0
        if self.post_seqitem_delay > 0:
            await super().clkcycles(1)
            self.dut.en[1] <= 0
        await super().clkcycles(self.post_seqitem_delay - 1)


class Monitor(top.RegMonitor):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.total_dvalids = 0

    async def sample_seqitem_input(self, seqitem):
        await super().wait_(self.dut.en[0])
        while True:
            await super().wait_(self.dvalid)
            self.total_dvalids += 1
            d = self.dut.d.value.value.integer
            seqitem.d.insert(0, d)
            if (self.total_dvalids % self.DEPTH) == 0:
                break
            await super().clkcycle
        self.log(f'observed input activity:\n{seqitem.d}')
        self.log('got dvalids')
        self.fork(self.sample_seqitem_output(seqitem))

    async def sample_seqitem_output(self, seqitem: top.VecSeqItem):
        await super().wait_(self.dut.q.info.new_tile_k)
        self.log('got_qvalids')
        for i in reversed(range(self.DEPTH)):
            q = self.dut.q.value[i].value.integer
            seqitem.q += [q]
        await super().clkcycle
        self.score(seqitem)

    def score(self, seqitem: top.VecSeqItem):
        failed = False
        msg = ''
        msg += f'\n{seqitem}'
        if seqitem.q != seqitem.d:
            failed = True
        if failed:
            super().seqitem_failed(msg)
        else:
            super().seqitem_passed(msg)


class EnAgent(uvm.Agent):
    def __init__(self, *args, **attrs):
        super().__init__(EnDriver, top.RegSeqItem, *args, **attrs)


class DoubleVecbufTest(top.RegTest):
    def __init__(self, *args, **attrs):
        super().__init__(top.RegSeqItem, *args, **attrs)
        assert self.DEPTH >= 4
        total_sequences = 2
        self.max_clk_cycles = self.DEPTH * (total_sequences * 4)
        attrs[nameof(self.max_clk_cycles)] = self.max_clk_cycles
        attrs[nameof(self.parent)] = self
        attrs[nameof(self.total_seqitems)] = total_sequences * self.DEPTH * 2
        prev_log_en = self.log_en
        attrs[nameof(self.log_en)] = False
        self.reg_agent = top.RegAgent(*args, **attrs)
        attrs[nameof(self.log_en)] = prev_log_en
        attrs[nameof(self.dut)] = self.dut
        attrs[nameof(self.total_seqitems)] = total_sequences
        self.monitor = Monitor(top.VecSeqItem, *args, **attrs)
        self.en_agent = EnAgent(*args, **attrs)


uvm_component_utils(DoubleVecbufTest)
