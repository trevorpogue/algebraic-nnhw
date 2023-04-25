import math
import typing as typ
import torch
from cocotb.triggers import Event
from debug import log
from nnhw.top import FIPMethod, nameof, varname
from tests import arith, top
from tests.arith.mxu_scoreboard import UVMScoreboard
from tests.arith.tb_pe import Monitor as PeMonitor
from tests.top.tb_utils.tb_triangle_buf import Monitor as TriangleMonitor


class Component(arith.Component):
    def __init__(self, *args, **attrs):
        super().__init__(self, *args, **attrs)


class MatMul(top.SequenceItem, Component):
    _m = None

    def __init__(self, *args, **attrs):
        top.SequenceItem.__init__(self, *args, **attrs)
        Component.__init__(self, *args, **attrs)
        self.a: torch.tensor = None
        self.b: torch.tensor = None
        self.c: torch.tensor = None
        self.data_attrs = [nameof(self.b), nameof(self.a), nameof(self.c), ]
        for key in self.data_attrs:
            setattr(self, key, torch.tensor([]))

    @property
    def m(self): return self.__class__._m

    @m.setter
    def m(self, value):
        """For synchronizing same m value across all class instances.
        m will still be randomized, but only once per simulation.
        """
        if self.__class__._m is None:
            self.__class__._m = value
            self.log(f'm: {self.__class__._m}')

    def int_range(self, width):
        return (-2 ** (width-1), 2 ** (width-1) - 1)

    def randomize(self):
        success = super().randomize()
        self.a = torch.randint(
            *self.int_range(self.A_WIDTH), (self.m, self.k))
        self.b = torch.randint(
            *self.int_range(self.B_WIDTH), (self.k, self.n))
        return success

    def __repr__(self): return str(self)

    def __str__(self):
        s = ''
        s += '{\n'
        for k in self.data_attrs:
            s += f"{repr(k)}:\n{self.__dict__[k]},\n"
        s += '}'
        return s


class Driver(top.Driver, Component):
    def __init__(self, *args, **attrs):
        top.Driver.__init__(self, *args, **attrs)
        Component.__init__(self, *args, **attrs)
        self.inputs = [self.dut.a, self.dut.b]
        self.log(self.dut)

    async def reset_phase(self, phase):
        for input in self.inputs:
            await self.reset_input(input)
        await super().reset_phase(phase)

    async def reset_input(self, q):
        q.info.valid <= 0
        q.info.new_tile_k <= 0
        q.value <= 0

    async def drive_seqitem(self, seqitem):
        self.fork(self.drive_a(seqitem))
        self.fork(self.drive_b(seqitem))
        await self.clk_posedges(seqitem.m)


class Monitor(top.Monitor, Component):
    def __init__(self, *args, **attrs):
        top.Monitor.__init__(self, *args, UVMScoreboard, **attrs)
        Component.__init__(self, *args, **attrs)

    async def sample_seqitem_input(self, seqitem):
        self.fork(self.sample_input(seqitem, self.akey))
        self.fork(self.sample_input(seqitem, self.bkey))
        self.fork(self.sample_seqitem_output(seqitem))
        await self.clkcycle

    async def sample_seqitem_output(self, seqitem):
        dtype = torch.int32
        iokey = self.ckey
        await self.wait_for_prev_call_to_finish(iokey)
        await super().wait_(self.dut.c.info.new_tile_k)
        self.score(seqitem)
        self.call_finished(iokey)

    def score(self, seqitem):
        expected = seqitem.copy()
        expected.c = self.scoreboard(seqitem)
        msg = f'\nobserved:\n{seqitem},\nexpected c:\n{expected.c}\n\n'
        top.Monitor.score(self, torch.equal(expected.c, seqitem.c, ), msg)


class UnitTest(top.Test, Component):
    def __init__(self, *args, **attrs):
        super().setattrs(**attrs)
        Component.__init__(self, *args, **attrs)
        self.total_seqitems = self.set(attrs, 2)
        seqitem = MatMul(**attrs)
        self.max_clk_cycles = self.set(
            attrs, self.total_seqitems * seqitem.MAX_M * 3)
        super().uvm_init(Driver, Monitor, MatMul, *args, **attrs)
        self.children(**attrs)

    def children(self, **attrs):
        attrs[nameof(self.parent)] = self
        attrs.pop(nameof(self.name))
        attrs.pop(nameof(self.dut), None)
        self.triangle_monitors(**attrs)


class MxuTest(top.Env, top.GroupTest):
    unittest_dutname = 'mxu_dut'
    UnitTest_ = UnitTest

    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        group_dut = self.dut.arith_duts if hasattr(
            self.dut, 'arith_duts') else self.dut
        self.unittests(group_dut, *args, **attrs)
