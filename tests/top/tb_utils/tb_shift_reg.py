import typing as typ
from cocotb.triggers import FallingEdge, RisingEdge, Timer
from debug import log
from nnhw.top import nameof, varname
from tests import top


class Monitor(top.Monitor):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.q, self.d = self.dut.q, self.dut.d
        self.dvec: typ.List[int] = []
        self.qvec: typ.List[int] = []
        self.DEPTH = self.dut.DEPTH.value

    @property
    def dvalid(self): return self.dut.d.info.valid
    @property
    def qvalid(self): return self.dut.q.info.valid

    async def sample_seqitem_input(self, seqitem):
        await self.wait_(self.dvalid)
        d = self.d.value.value.integer
        seqitem.d = d
        self.dvec.insert(0, d)
        self.log(f'observed input activity:\n{d}')
        self.fork(self.sample_seqitem_output(seqitem))
        await self.clkcycle

    async def sample_seqitem_output(self, seqitem):
        await self.clkcycles(self.DEPTH)
        q = self.dut.q.value.value.integer
        self.qvec.insert(0, q)
        self.log(f'observed output activity:\n{q}')
        seqitem.q = q
        self.score(seqitem)

    def score(self, seqitem):
        dvec = self.dvec[len(self.dvec)-len(self.qvec):]
        if not seqitem.q == seqitem.d or self.qvec != dvec:
            super().seqitem_failed(f'dvec {dvec}, qvec {self.qvec}')
        else:
            super().seqitem_passed()


class UnitTest(top.RegTest):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.cleanup(attrs)
        self.agent = top.RegAgent(Monitor, *args, **attrs)


class ParentTest(top.Env):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.cleanup(attrs)
        for i in range(self.dut.TOTAL_DUTS.value):
            dutname = top.camel2snake(self.__class__.__name__) + str(i)
            childname = top.camel2snake(self.Child.__name__) + str(i)
            setattr(self, dutname, self.Child(
                *args, **attrs, dut=getattr(self.dut, dutname),
                name=childname))


class Module(ParentTest):
    Child = UnitTest


class Latency(ParentTest):
    Child = Module


class ShiftRegTest(top.Env):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.cleanup(attrs)
        self.latency = Latency(
            *args, **attrs,
            dut=self.dut.shift_reg_latency,
            name=varname())
