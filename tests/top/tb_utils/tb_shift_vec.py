import typing as typ
from math import ceil
from debug import log
from tests import top
from nnhw.top import nameof, varname


class Monitor(top.Monitor):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.q, self.d = self.dut.q, self.dut.d
        self.D_WIDTH = self.dut.d.value.value.n_bits
        self.Q_WIDTH = self.dut.q.value.value.n_bits
        self.DEPTH = ceil(self.Q_WIDTH / self.D_WIDTH)
        self.WIDTH = self.D_WIDTH
        self.dvec: typ.List[int] = []
        self.qvec: typ.List[int] = []

    @property
    def dvalid(self): return self.dut.d.info.valid
    # @property
    # def qvalid(self): return self.dut.q.info.valid

    async def sample_seqitem_input(self, seqitem):
        await self.wait_(self.dvalid)
        d = self.d.value.value.integer
        self.dvec.insert(0, d)
        seqitem.d = d
        self.log(f'observed input activity:\n{d}')
        self.fork(self.sample_seqitem_output(seqitem))
        await self.clkcycle

    async def sample_seqitem_output(self, seqitem):
        await self.clkcycles(self.DEPTH)
        q = self.dut.sim.last_q_scalar.value.integer
        self.qvec.insert(0, q)
        seqitem.q = q
        self.score()

    def score(self):
        dvec = self.dvec[:self.DEPTH]
        dvec = self.dvec[len(self.dvec)-len(self.qvec):]
        if not self.qvec == dvec:
            super().seqitem_failed(f'dvec {dvec}, qvec {self.qvec}')
        else:
            super().seqitem_passed()


class UnitTest(top.Test):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.cleanup(attrs)
        self.agent = top.RegAgent(Monitor, *args, **attrs)


class Modules(top.Env):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.cleanup(attrs)
        self.module = UnitTest(
            *args, **attrs,
            dut=self.dut.module_u,
            name=varname())
        self.macro = UnitTest(
            *args, **attrs,
            dut=self.dut.macro_u,
            name=varname())


class Latencies(top.Env):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.cleanup(attrs)
        # self.latency0 = Modules(
            # *args, **attrs, dut=getattr(self.dut, varname()), name=varname())
        self.latency1 = Modules(
            *args, **attrs, dut=getattr(self.dut, varname()), name=varname())
        self.latency4 = Modules(
            *args, **attrs, dut=getattr(self.dut, varname()), name=varname())


class ShiftVecTest(top.Env):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.cleanup(attrs)
        self.latencies = Latencies(
            *args, **attrs,
            dut=self.dut.shift_vec_latencies,
            name=varname())
