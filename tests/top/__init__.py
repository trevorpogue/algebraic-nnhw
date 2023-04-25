import typing as typ
from debug import log
from uvm.macros import uvm_component_utils
from nnhw.top import FIPMethod, nameof, varname, prod
from tests import arith
from tests.top.uvm import (
    Driver, Monitor, Scoreboard, Sequence, SequenceItem, Sequencer, Signal,
    always, always_, camel2snake, getbases)
from tests.top.uvm.base import Base, non_overlapping_coroutine
from tests.top.uvm.containers import Agent, Container, Env, Test, GroupTest
import torch
import numpy as np

def debug2(method):
    def wrapper(self, *args, **kwds):
        log(f'begin {method.__qualname__}')
        value = method(self, *args, **kwds)
        log(f'end {method.__qualname__}')
        return value
    return wrapper


def debug(method):
    def wrapper(self, *args, **kwds):
        self.log(f'begin {method.__qualname__}')
        value = method(self, *args, **kwds)
        self.log(f'end {method.__qualname__}')
        return value
    return wrapper


class HexList(list):
    def __repr__(self): return str(self)

    def __str__(self):
        s = ''
        s += '\n    ['
        for i in self:
            s += f"{hex(i)[2:]}, "
        s += ']\n'
        return s


class DataSeqItem(SequenceItem):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.value: typ.Any = None
        self.data_attrs = [nameof(self.value)]
        self.rand(nameof(self.value), range(1, 2**self.dut.WIDTH.value))
###############################################################################
# Reg


class RegComponent:
    def __init__(self, *args, **attrs):
        nil = []
        self.DEPTH = self.dut.DEPTH.value if attrs.get(
            varname(), nil) is nil else attrs.get(varname())
        self.WIDTH = self.dut.WIDTH.value if attrs.get(
            varname(), nil) is nil else attrs.get(varname())
        self.q = self.dut.q if attrs.get(
            varname(), nil) is nil else attrs.get(varname())
        self.d = self.dut.d if attrs.get(
            varname(), nil) is nil else attrs.get(varname())
        self.signed = attrs.get(varname(), False)


class RegSeqItem(SequenceItem, RegComponent):
    def __init__(self, *args, **attrs):
        SequenceItem.__init__(self, *args, **attrs)
        RegComponent.__init__(self, *args, **attrs)
        self.d = None
        self.q = None
        self.rand(nameof(self.d), range(1, 2**self.WIDTH))
        self.data_attrs = [nameof(self.d), nameof(self.q)]


class RegDriver(Driver, RegComponent):
    def __init__(self, *args, **attrs):
        Driver.__init__(self, *args, **attrs)
        RegComponent.__init__(self, *args, **attrs)

    @property
    def dvalid(self): return self.d.info.valid
    @property
    def qvalid(self): return self.q.info.valid

    async def reset_phase(self, phase):
        self.d.info.valid <= 0
        self.d.value <= 0
        super().reset_phase(phase)

    async def drive_seqitem(self, seqitem):
        d = arith.signed(seqitem.d, self.WIDTH) if self.signed else seqitem.d
        self.log(f'driving seqitem:\n{d}')
        self.d.value <= seqitem.d
        self.d.info.valid <= 1
        await self.clk_posedge


class RegMonitor(Monitor, RegComponent):
    def __init__(self, *args, **attrs):
        Monitor.__init__(self, *args, **attrs)
        RegComponent.__init__(self, *args, **attrs)

    @property
    def dvalid(self): return self.d.info.valid
    @property
    def qvalid(self): return self.q.info.valid

    def score(self, seqitem):
        if seqitem.q != seqitem.d:
            super().seqitem_failed(seqitem)
        else:
            super().seqitem_passed(seqitem)


class RegAgent(Agent, RegComponent):
    def __init__(self, *args, **attrs):
        Agent.__init__(self, RegDriver, RegSeqItem, *args, **attrs)
        RegComponent.__init__(self, *args, **attrs)


class RegTest(Test, RegComponent):
    def __init__(self, *args, **attrs):
        self.max_clk_cycles = 20
        attrs[nameof(self.max_clk_cycles)] = self.max_clk_cycles
        Test.__init__(self, *args, **attrs)
        RegComponent.__init__(self, *args, **attrs)
###############################################################################
# Vec


class VecComponent(RegComponent):
    pass


class VecSeqItem(SequenceItem, VecComponent):
    def __init__(self, *args, **attrs):
        SequenceItem.__init__(self, *args, **attrs)
        VecComponent.__init__(self, *args, **attrs)
        self.q: typ.List[int] = HexList()
        self.d: typ.List[int] = HexList()
        self.data_attrs = [nameof(self.d), nameof(self.q)]

    def randomize(self, *args, **attrs):
        success = super().randomize(*args, **attrs)
        for i in range(self.DEPTH):
            dscalar = DataSeqItem(**self.attrs)
            success = success and dscalar.randomize()
            self.d += [dscalar.value]
        return success


class VecDriver(RegDriver):
    async def drive_seqitem(self, seqitem):
        self.log(f'driving seqitem:\n{seqitem.d}')
        self.d.info.valid <= 1
        for i in range(self.DEPTH):
            self.d.value[i] <= seqitem.d[i]
        await self.clk_posedge


class VecMonitor(RegMonitor):
    async def sample_seqitem_input(self, seqitem):
        await self.wait_(self.dvalid)
        for i in range(self.DEPTH):
            d = self.d.value[i].value.integer
            seqitem.d.insert(0, d)
        self.log(f'observed input:\n{seqitem.d}')
        self.fork(self.sample_seqitem_output(seqitem))
        await self.clkcycle


class VecAgent(VecComponent, Agent):
    def __init__(self, *args, **attrs):
        Agent.__init__(self, VecMonitor, VecDriver, VecSeqItem, *args, **attrs)
        VecComponent.__init__(self, *args, **attrs)


class VecTest(VecComponent, Test):
    def __init__(self, *args, **attrs):
        Test.__init__(self, *args, **attrs)
        VecComponent.__init__(self, *args, **attrs)
###############################################################################
