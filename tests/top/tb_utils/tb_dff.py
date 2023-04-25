import typing as typ
from debug import log
from tests import top
from tests.top import uvm


class Monitor(top.RegMonitor):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)

    async def sample_seqitem_input(self, seqitem):
        await self.wait_(self.dvalid)
        await self.clkcycle
        seqitem.d = self.d.value.value.integer
        seqitem.dvalid = self.d.info.valid.value.integer
        self.log(f'observed input activity: {seqitem.d}')
        self.fork(self.sample_seqitem_output(seqitem))

    async def sample_seqitem_output(self, seqitem):
        await self.clkcycle
        seqitem.q = self.q.value.value.integer
        self.log(f'observed output activity: {seqitem.q}')
        self.score(seqitem)

    def score(self, seqitem):
        if seqitem.q == seqitem.d:
            super().seqitem_passed(seqitem)
        else:
            super().seqitem_failed(seqitem)


class DffTest(top.RegTest):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        attrs['parent'] = self
        self.agent = top.RegAgent(Monitor, *args, **attrs)


uvm.uvm_component_utils(DffTest)
