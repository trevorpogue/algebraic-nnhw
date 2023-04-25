import typing as typ
from math import ceil
from debug import log
from tests.top import nameof
from tests import top
import math


class Monitor(top.Monitor):
    def __init__(self, *args, **attrs):
        top.Monitor.__init__(self, top.VecSeqItem, *args, **attrs)
        self.SLOPE = self.dut.SLOPE.value
        self.DEPTH = math.ceil(abs(self.dut.DEPTH.value / self.SLOPE))
        self.d, self.q = self.dut.d, self.dut.q
        self.neg_slope = False
        if self.SLOPE < 0:
            self.neg_slope = True
            self.SLOPE = abs(self.SLOPE)

    @property
    def dvalid(self): return self.d.info.valid
    @property
    def qvalid(self): return self.q.info.valid

    def get_index(self, i, j):
        if self.neg_slope:
            return i * self.SLOPE + j
        else:
            return i * self.SLOPE + j

    @property
    def depth_range(self): return range(
            self.DEPTH) if self.neg_slope else reversed(range(self.DEPTH))

    @property
    def slope_range(self): return range(
            self.SLOPE) if self.neg_slope else reversed(range(self.SLOPE))

    async def sample_seqitem_input(self, seqitem):
        await self.wait_(self.dvalid)
        for i in self.depth_range:
            for j in self.slope_range:
                d = self.sample(self.d.value[self.get_index(i, j)])
                if self.neg_slope:
                    seqitem.d.insert(0, d)
                else:
                    seqitem.d.append(d)
        self.log(f'observed input:\n{seqitem.d}')
        self.fork(self.sample_seqitem_output(seqitem))
        await self.clkcycle

    async def sample_seqitem_output(self, seqitem):
        for i in self.depth_range:
            for j in self.slope_range:
                q = self.sample(self.q.value[self.get_index(i, j)])
                if self.neg_slope:
                    seqitem.q.insert(0, q)
                else:
                    seqitem.q.append(q)
            await self.clkcycle
        self.log(f'observed output:\n{seqitem}')
        self.score(seqitem)

    def score(self, seqitem):
        top.Monitor.score(self, seqitem.q == seqitem.d, seqitem)


class TriangleBufTest(top.VecTest):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.total_seqitems = self.DEPTH
        attrs[nameof(self.total_seqitems)] = self.DEPTH
        attrs[nameof(self.parent)] = self
        # attrs[nameof(self.log_en)] = True
        self.agent = top.VecAgent(Monitor, *args, **attrs)
