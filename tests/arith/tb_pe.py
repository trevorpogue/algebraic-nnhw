import typing as typ
from cocotb.triggers import Event
from cocotb import fork
from debug import log
from nnhw.top import FIPMethod, nameof, varname
from tests import arith, top


class Component(arith.Component):
    pass


class PeExec(top.SequenceItem, Component):
    def __init__(self, *args, **attrs):
        top.SequenceItem.__init__(self, *args, **attrs)
        Component.__init__(self, *args, **attrs)
        self.a = [None] * self.PE_INPUT_DEPTH
        self.b = [None] * self.PE_INPUT_DEPTH
        self.c = [None] * self.PE_INPUT_DEPTH
        self.data_attrs = [nameof(self.a), nameof(self.b), nameof(self.c), ]

    def __repr__(self): return str(self)

    def __str__(self):
        s = ''
        s += '{\n'
        for k in self.data_attrs:
            s += f"{repr(k)}:\n{self.__dict__[k]},\n"
        s += '}'
        return s


class Monitor(top.Monitor, Component):
    def __init__(self, *args, **attrs):
        top.Monitor.__init__(self, *args, PeExec, **attrs)
        Component.__init__(self, *args, **attrs)
        self.akey = 'a'
        self.bkey = 'b'
        self.got_input_events = {self.akey: [], self.bkey: []}
        for i in range(self.PE_INPUT_DEPTH):
            self.got_input_events[self.akey].append(Event())
            self.got_input_events[self.bkey].append(Event())

    async def sample_seqitem_input(self, seqitem):
        forks = []
        for a_or_b_key in [self.akey, self.bkey]:
            for op_index in range(self.PE_INPUT_DEPTH):
                forks.append(fork(self.sample_input(seqitem, a_or_b_key, op_index)
                ))
        await self.join(*forks)
        self.fork(self.sample_seqitem_output(seqitem))
        await self.clkcycle

    async def sample_input(self, seqitem, a_or_b_key, op_index):
        signal = (self.dut.genblk1[op_index].a
                  if a_or_b_key == self.akey
                  else self.dut.genblk1[op_index].b)
        await self.wait_(signal.info.valid)
        WIDTH = (self.AMAT_WIDTH if a_or_b_key == self.akey
                 else self.BMAT_WIDTH)
        value = signal.value.value.integer
        input_is_signed = (self.A_SIGNED if a_or_b_key == self.akey
                           else self.B_SIGNED)
        if input_is_signed or self.FIP_METHOD is top.FIPMethod.FFIP:
            value = arith.signed(value, WIDTH)
        seqitem.__dict__[a_or_b_key][op_index] = value
        self.log(f'{a_or_b_key}{op_index} observed input:\n{value}')

    async def sample_seqitem_output(self, seqitem):
        await self.clkcycles(self.DSP_LATENCY)
        seqitem.c = arith.signed(
            self.dut.res.value.integer, self.C_WIDTH)
        self.log(f'observed output:\n{seqitem.c}')
        self.score(seqitem)

    def score(self, seqitem):
        expected_output = self.pe_behav(seqitem)
        msg = f'\nobserved:\n{seqitem},\nexpected_output:\n{expected_output}'
        top.Monitor.score(self, seqitem.c == expected_output, msg)

    def pe_behav(self, seqitem):
        a, b = seqitem.a, seqitem.b
        c = None
        if self.FIP_METHOD is FIPMethod.FFIP:
            c = a[0] * a[1] + a[2] * a[3]
        elif self.FIP_METHOD is FIPMethod.FIP:
            c = ((a[0] + b[1]) * (a[1] + b[0])
                 + (a[2] + b[3]) * (a[3] + b[2]))
        else:
            assert self.FIP_METHOD is FIPMethod.BASELINE
            c = a[0] * b[0] + a[1] * b[1]
        return c


class UnitTest(top.Test, Component):
    def __init__(self, *args, **attrs):
        super().setattrs(**attrs)
        Component.__init__(self, *args, **attrs)
        super().uvm_init(*args, **attrs)
        dir(self.dut)  # required to fix cocotb dut attr access bug
        attrs[nameof(self.parent)] = self
        attrs.pop(nameof(self.name))
        self.total_seqitems = self.set(attrs, 8)
        self.max_clk_cycles = self.set(
            attrs, self.DSP_LATENCY * self.total_seqitems + 4)
        self.d = self.set(attrs, None)
        self.q = self.set(attrs, self.dut.res)
        self.monitor = self.set(attrs, Monitor(*args, PeExec, **attrs))
        for i in range(self.PE_INPUT_DEPTH):
            aname = f'a{i}'
            bname = f'b{i}'
            attrs['d'] = self.dut.genblk1[i].a
            setattr(self, aname, top.RegAgent(
                *args, **attrs, name=aname, WIDTH=self.AMAT_WIDTH))
            attrs['d'] = self.dut.genblk1[i].b
            setattr(self, bname, top.RegAgent(
                *args, **attrs, name=bname, WIDTH=self.BMAT_WIDTH))


class PeTest(top.GroupTest):
    UnitTest_ = UnitTest
