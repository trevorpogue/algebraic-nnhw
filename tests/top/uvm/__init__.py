import re
from copy import copy, deepcopy
import typing as typ
import uvm
from debug import log
from uvm.comps import UVMAgent, UVMDriver, UVMEnv, UVMMonitor, UVMScoreboard
from uvm.seq import UVMSequence, UVMSequenceItem, UVMSequencer
from cocotb.triggers import Event
from uvm.base.uvm_component import UVMComponent
from varname import nameof as nameof
# exports:
from uvm.macros import uvm_component_utils
from tests.top.uvm.base import Base
from nnhw.top import nameof, varname
import nnhw


camel2snake_pattern = re.compile(r'(?<!^)(?=[A-Z])')


def camel2snake(name): return camel2snake_pattern.sub('_', name).lower()


def always(method):
    """Driver version of an always block that acts every clk_cycle. (block
    logic executes 1 step BEFORE every clk_posedge)
    """
    async def wrapper(self, *args, **attrs):
        await self.clk_posedge
        while True:
            await method(self, *args, **attrs)
    return wrapper


def always_(method):
    """Monitor version of an always block that acts every clk_cycle.(block
    logic executes 1 step AFTER every clk_posedge)
    """
    async def wrapper(self, *args, **attrs):
        await self.clk_posedge
        await self.step
        while True:
            await method(self, *args, **attrs)
    return wrapper


def getbases(cls):
    cls.UVMBase = cls
    cls.UVMPythonBase = [None, *list(filter(
        lambda x: x.__name__.endswith('UVM' + cls.__name__),
        cls.mro()
    ))].pop()
    return cls


class Signal:
    def __init__(self, value=None):
        self.value = value


class SeqType:
    pass
###############################################################################
# UVM base classes


@getbases
class Component(Base, UVMComponent):
    pass


@getbases
class Sequence(Base, UVMSequence, SeqType):
    async def body(self):
        if not self._children.get(SequenceItem):
            self.log('no SequenceItem')
            log(self.__dict__)
            return
        self.seqitems = []
        for i in range(self.total_seqitems):
            self.seqitems.append(self._children[SequenceItem](**self.attrs))
        for seqitem in self.seqitems:
            await self.do_seqitem(seqitem)

    async def do_seqitem(self, seqitem):
        await self.start_item(seqitem)
        seqitem.randomize()
        await self.finish_item(seqitem)


@getbases
class SequenceItem(Base, UVMSequenceItem, SeqType):
    def __repr__(self): return self.__str__()

    def __str__(self):
        if not hasattr(self, 'data_attrs'):
            return super().__repr__()
        data = {}
        for k in self.data_attrs:
            v = getattr(self, k)
            data[k] = hex(v) if isinstance(v, int) else v
        return str(data)

    def copy(self):
        copy = self.__class__(**self.attrs)
        _nil = []
        for k in self.data_attrs:
            setattr(copy, k, deepcopy(getattr(self, k)))
        return copy


@getbases
class Sequencer(Base, UVMSequencer, SeqType):
    pass
###############################################################################


@getbases
class Driver(Base, UVMDriver):
    async def main_phase(self, phase):
        await self.clk_posedge
        for i in range(self.total_seqitems):
            seqitem = []
            await self.seq_item_port.get_next_item(seqitem)
            seqitem = seqitem[0]
            await self.drive_seqitem(seqitem)
            self.seq_item_port.item_done()


@getbases
class Monitor(Base, UVMMonitor, ):
    def __init__(self, *args, **attrs):
        Base.__init__(self, *args, **attrs)
        self.total_sampled_seqitems = 0
        self.total_passed_seqitems = 0
        self.total_failed_seqitems = 0
        self.sampled_seqitem_inputs = []
        self.all_seqitems_sampled = Event()
        self.elapsed_clk_cycles = 0
        self.timeout = Event()
        self.do_raise_objection = attrs.get(varname(), True)
        self.autosample = attrs.get(varname(), True)
        if not self.do_raise_objection:
            arbitrary_large_number = 1000000
            self.total_seqitems = arbitrary_large_number

    async def main_phase(self, phase):
        if not self.autosample:
            return
        if self.do_raise_objection:
            self.raise_objection(phase)
        forks = []
        forks.append(self.fork(self._sample_seqitem_input()))
        if not self.do_raise_objection:
            return
        self.fork(self.watchdog_timer(phase))
        await self.clk_posedge
        # await self.timeout.wait()
        joining_event = Event()
        self.fork(self.join_any_event(self.all_seqitems_sampled,
                                      joining_event))
        self.fork(self.join_any_event(self.timeout, joining_event))
        self.fork(self.join_any_event(self.top_timeout, joining_event))
        await joining_event.wait()
        if getattr(self, 'score_on_timeout', False) and self.timeout.data:
            self.score()
        self.log(
            f'total_passed_seqitems: {self.total_passed_seqitems} / '
            + f'{self.total_seqitems}'
        )
        for fork_ in forks:
            fork_.kill()
        self.drop_objection(phase)

    async def join_any_event(self, wait_event, joining_event):
        await wait_event.wait()
        joining_event.set()

    async def watchdog_timer(self, phase):
        log(self.max_clk_cycles, show_context=False)
        while True:
            self.elapsed_clk_cycles += 1
            if self.all_seqitems_sampled.is_set():
                return
            if self.elapsed_clk_cycles >= self.max_clk_cycles:
                self.error('Monitor timeout')
                self.timeout.set(True)
            await self.clkcycle

    async def _sample_seqitem_input(self):
        await self.clk_posedge
        for i in range(self.total_seqitems):
            await self.step
            await(self.sample_seqitem_input(
                self._children[SequenceItem](**self.attrs)))

    def seqitem_failed(self, msg=''):
        self.error(f'{msg}', self.total_sampled_seqitems)
        self.total_failed_seqitems += 1
        self._seqitem_done()

    def seqitem_passed(self, seqitem='', dummy_pass=False):
        if seqitem != '':
            seqitem = f':\n{seqitem}'
        if not dummy_pass:
            msg = (f'>>> PASS >>> seqitem no. {self.total_sampled_seqitems}'
                   + f'{seqitem}\n<<< PASS <<< seqitem no. {self.total_sampled_seqitems}')
            self.passed(msg)
        self.total_passed_seqitems += 1
        self._seqitem_done()

    def _seqitem_done(self):
        self.total_sampled_seqitems += 1
        if self.total_sampled_seqitems == self.total_seqitems:
            self.all_seqitems_sampled.set()

    def score(self, passed: bool, msg: str):
        if passed:
            self.seqitem_passed(msg)
        else:
            self.seqitem_failed(msg)


@getbases
class Scoreboard(Base, UVMScoreboard):
    pass
###############################################################################


# class Interface(nnhw.top.AttrDict):
class Interface(dict):
    """Like a dict of IOs but can also get a dict of only inputs or only
    outputs.
    """
    def __init__(self, inputs: dict, outputs: dict):
        self._inputs = list(inputs)
        self._outputs = list(outputs)
        self.update(inputs)
        self.update(outputs)

    @property
    def inputs(self): return {k: self[k] for k in self._inputs}
    @property
    def outputs(self): return {k: self[k] for k in self._outputs}

#exports
from tests.top.uvm.containers import Agent, Container, Env, Test, GroupTest
