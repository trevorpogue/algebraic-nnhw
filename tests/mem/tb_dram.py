from tests.top import uvm


"""Test logic is implemented in RTL."""


class Monitor(uvm.Monitor):
    async def sample_seqitem_input(self, seqitem):
        pass


class DramTest(uvm.Test):
    def __init__(self, *args, **attrs):
        super().setattrs(**attrs)
        self.total_seqitems = self.set(attrs, 1)
        self.max_clk_cycles = self.set(attrs, 1000)
        super().uvm_init(uvm.SequenceItem, Monitor, *args, **attrs)

    async def reset_phase(self, phase):
        self.raise_objection(phase)
        self.fork(self.always_clk(self.dut.clk2, self.clk_period*4))
        await super().reset_phase(phase)
        self.drop_objection(phase)
