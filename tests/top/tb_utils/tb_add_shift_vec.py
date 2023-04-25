import typing as typ
from debug import log
from tests.top import nameof
from tests import top


class Monitor(top.VecMonitor):
    async def sample_seqitem_output(self, observed: top.VecSeqItem):
        expected = observed.copy()
        for i, ir in enumerate(reversed(range(self.DEPTH))):
            d = expected.d[i]
            if i == 0:
                expected.q += [d]
            else:
                q = self.q.value[ir+1].value.integer
                expected.q += [(q + d) % (2 ** self.WIDTH)]
        await self.clkcycle
        for i, ir in enumerate(reversed(range(self.DEPTH))):
            observed.q += [self.q.value[ir].value.integer]
        self.score(observed, expected)

    def score(self, observed, expected):
        failed = False
        for attr in observed.data_attrs:
            if observed.__dict__[attr] != expected.__dict__[attr]:
                failed = True
        msg = f'observed:\n{observed}, expected:\n{expected}'
        if failed:
            super().seqitem_failed(msg)
        else:
            super().seqitem_passed(msg)


class AddShiftVecTest(top.VecTest):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.total_seqitems = self.DEPTH
        attrs[nameof(self.total_seqitems)] = self.DEPTH
        attrs[nameof(self.parent)] = self
        # attrs[name(self.log_en)] = True
        self.agent = top.VecAgent(*args, Monitor, **attrs)
