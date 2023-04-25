import typing as typ
from debug import log
from tests.top import nameof
from tests import top


class SeqItem(top.VecSeqItem):
    def __init__(self, *args, **attrs):
        super().__init__(self, *args, **attrs)
        self.q: typ.List[int] = top.HexList()
        self.d: typ.List[int] = top.HexList()
        self.x: typ.List[int] = top.HexList()
        self.data_attrs = [nameof(self.d), nameof(self.x), nameof(self.q)]

    def randomize(self, *args, **attrs):
        success = True
        for i in range(self.DEPTH):
            for attr in [nameof(self.d), nameof(self.x)]:
                scalar = top.DataSeqItem(**self.attrs)
                success = success and scalar.randomize()
                self.__dict__[attr] += [scalar.value]
        return success


class Driver(top.VecDriver):
    async def reset_phase(self, phase):
        self.dut.x.value <= 0
        super().reset_phase(phase)

    async def drive_seqitem(self, seqitem):
        self.log(f'driving seqitem:\n{seqitem}')
        self.dut.d.info.valid <= 1
        for i in range(self.DEPTH):
            self.dut.d.value[i] <= seqitem.d[i]
            self.dut.x.value[i] <= seqitem.x[i]
        await self.clkcycle


class Monitor(top.VecMonitor):
    async def sample_seqitem_input(self, seqitem):
        await self.wait_(self.dvalid)
        for i in range(self.DEPTH):
            d = self.dut.d.value[i].value.integer
            x = self.dut.x.value[i].value.integer
            seqitem.d.insert(0, d)
            seqitem.x.insert(0, x)
        self.log(f'observed input:\n{seqitem}')
        self.fork(self.sample_seqitem_output(seqitem))
        await self.clkcycle

    async def sample_seqitem_output(self, observed: top.VecSeqItem):
        expected = observed.copy()
        for i, ir in enumerate(reversed(range(self.DEPTH))):
            d = expected.d[i]
            x = expected.x[i]
            expected.q += [(x + d) % (2 ** self.WIDTH)]
        await self.clkcycle
        for i, ir in enumerate(reversed(range(self.DEPTH))):
            observed.q += [self.q.value[ir].value.integer]
        self.score(observed, expected)

    def score(self, observed, expected):
        passed = True
        for attr in observed.data_attrs:
            if observed.__dict__[attr] != expected.__dict__[attr]:
                passed = False
        msg = f'observed:\n{observed}, expected:\n{expected}'
        top.Monitor.score(self, passed, msg)


class AddVecTest(top.VecTest):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.total_seqitems = self.DEPTH
        attrs[nameof(self.total_seqitems)] = self.DEPTH
        attrs[nameof(self.parent)] = self
        # attrs[name(self.log_en)] = True
        self.agent = top.VecAgent(*args, Driver, Monitor, SeqItem, **attrs)
