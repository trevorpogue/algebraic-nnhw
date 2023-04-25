import re
from cocotb.triggers import Event
import typing as typ
from typing import Callable, List, Optional, Tuple
from uvm import uvm_info
from cocotb import fork
import cocotb
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer
from debug import log
from uvm import UVMObject
from uvm.base.uvm_phase import UVMPhase
from uvm.comps.uvm_test import UVMTest
# exports:
from nnhw.top import nameof, varname
from varname import nameof as nameof


def non_overlapping_coroutine(method):
    f"""Decorator to ensure that the previous call to a coroutine completes
    before starting
    the next. This allows N executions of an async fn to be forked all at once,
    and they will all still be executed sequentially without overlapping. Class
    using this decorator must inherit class defined next to use.
    """

    async def wrapper(self, *args, **kwds):
        iokey = method.__qualname__
        await self.wait_for_prev_call_to_finish(iokey)
        await method(self, *args, **kwds)
        self.call_finished(iokey)
    return wrapper


class NonOverlappingCoroutines:
    f"""Base class required for a class to inherit in order for it to use the
    {non_overlapping_coroutine} decorator.
    """

    def __init__(self, *args, **attrs):
        self.completed_coro_counts = dict()
        self.started_coro_counts = dict()

    async def wait_for_prev_call_to_finish(self, coro_key):
        e = Event()
        e.data = 0
        self.completed_coro_counts.setdefault(coro_key, e)
        self.started_coro_counts.setdefault(coro_key, 0)
        while (self.started_coro_counts[coro_key]
               > self.completed_coro_counts[coro_key].data):
            await self.completed_coro_counts[coro_key].wait()
        self.started_coro_counts[coro_key] += 1

    def call_finished(self, coro_key):
        self.completed_coro_counts[coro_key].set(
            self.completed_coro_counts[coro_key].data + 1)
        self.completed_coro_counts[coro_key].clear()


class Base(NonOverlappingCoroutines):
    msgs = []
    test_failed = {}
    top_errors = []
    def __init__(self, *args, **attrs):
        self.setattrs(**attrs)
        self.uvm_init(*args, **attrs)

    def uvm_init(self, *args, **attrs):
        if self.UVMPythonBase is not None:
            try:
                self.UVMPythonBase.__init__(self, self.name, self.parent)
            except TypeError:
                self.UVMPythonBase.__init__(self, self.name)
        attrs[nameof(self.parent)] = self
        attrs.pop(nameof(self.name), None)
        self.collect_uvm_args(*args, **attrs)
        self.post_uvm_init(*args, **attrs)

    def setattrs(self, **attrs):
        NonOverlappingCoroutines.__init__(self)
        self.set_default_attrs(**attrs)
        self.getdut(**attrs)

    def cleanup(self, attrs):
        attrs[nameof(self.parent)] = self
        attrs.pop(nameof(self.dut), None)
        attrs.pop(nameof(self.name), None)

    def set_default_attrs(self, **attrs):
        # try:
            # from varname import varname
            # self.default_name = varname(frame=3)
        # except:
        from tests.top.uvm import Container, camel2snake
        self.default_name = camel2snake(
            self.__class__.__name__ if self.isinstance(Container)
            else self.__class__.UVMBase.__name__)
        self._children = {}
        self.parent: Optional[UVMObject] = self.setdefault(attrs, None)
        self.top: UVMObject = self.setdefault(attrs, None)
        self.parse_name(attrs)
        if self.isinstance(UVMTest):
            self.errors = self.set(attrs, [])
            self.passes = self.set(attrs, [])
        else:
            self.errors: List[[Tuple[UVMObject, str]]] = self.setdefault(
                attrs, self.test_parent().errors)
            self.passes: List[[Tuple[UVMObject, str]]] = self.setdefault(
                attrs, self.test_parent().passes)
        for k, v in attrs.items():
            setattr(self, k, v)
        self.attrs = attrs
        self._clk = attrs.get('clk', self.top.clk)

    def getdut(self, **attrs):
        if hasattr(self, 'dut'):
            return
        self.dut = attrs.get(varname())
        if self.dut is None:
            default_dutname = re.sub('(.*?)(_test|_env|_agent)?',
                                     r'\1', self.test_parent().name) + '_u'
            try:
                parent_dut = self.parent.dut
            except AttributeError:
                parent_dut = self.top
            default_dut = getattr(parent_dut, default_dutname, parent_dut)
            self.dut = attrs.setdefault(varname(), default_dut)

    def collect_uvm_args(self, *args, **attrs):
        from tests.top.uvm import SequenceItem
        attrs.pop('name', None)
        uvm_cls_args = {}
        for cls in args:
            if not hasattr(cls, 'mro'):
                continue
            if UVMObject in cls.mro():  # if arg is a uvm class
                uvm_cls_args[cls.UVMBase] = cls
        seqitem_cls_args = []
        if uvm_cls_args.get(SequenceItem):
            seqitem_cls_args.append(uvm_cls_args.get(SequenceItem))

        for k, cls in uvm_cls_args.items():
            if self.isinstance(SequenceItem):
                continue
            if SequenceItem in cls.mro():
                obj = cls
                name = obj.__name__
            else:
                obj = cls(*seqitem_cls_args, **attrs)
                name = obj.name
            self._children[k] = obj
            setattr(self, name, obj)

    def post_uvm_init(self, *args, **attrs):
        test_parent = self.test_parent()
        test_parent_name = ''
        if test_parent is not self:
            test_parent_name = re.sub('(.*?)(_test|_env|_agent)?',
                                      r'\1', test_parent.name) + '_'
        if self._children:
            self.fillin_missing_uvmchildren(**attrs)

    def fillin_missing_uvmchildren(self, **attrs):
        from tests.top.uvm import (
            Container, Sequence, SequenceItem, Sequencer, Monitor,
            Scoreboard)
        if not self.isinstance(SequenceItem) and not self._children.get(
                SequenceItem):
            self.log('Does not contain a SequenceItem.')
            self.log(f'{nameof(self._children)}: {self._children}')
            raise ValueError(f'{self.path_name} does not contain a SequenceItem.')
        if self.isinstance(Monitor):
            cls = Scoreboard
            if not self._children.get(cls):
                self._children[cls] = cls(self._children[SequenceItem], **attrs)
                setattr(self, self._children[cls].name, self._children[cls])
        if self.isinstance(Container):
            for cls in [Sequence, Sequencer]:
                if not self._children.get(cls):
                    self._children[cls] = cls(
                        self._children[SequenceItem], **attrs)

    def set(self, attrs, value):
        """Set attrs item to self.caller attr name/value."""
        from varname import varname
        name = varname()
        attrs[name] = value
        return value

    def setdefault(self, attrs, default, callable_default=False):
        """Set attrs item to self.caller attr name/value if in self.__dict__.
        else set attrs item and self.caller attr to default.
        optionally use return value from callable default as default.
        """
        from varname import varname
        name = varname()
        if hasattr(self, name):
            default = getattr(self, name)
        else:
            nil = []
            attrs_val = attrs.get(name, nil)
            if attrs_val is nil:
                if callable_default:
                    default = default()
            else:
                default = attrs_val
            setattr(self, name, default)
        attrs[name] = default
        return default

    def isinstance(self, cls): return isinstance(self, cls)

    def test_parent(self):
        node = self
        while node.parent and not node.isinstance(UVMTest):
            node = node.parent
        return node

    def fork(self, coroutine): return fork(coroutine)
    async def delay(self, amount): await Timer(amount, self.time_unit)
    @property
    async def clkcycle(self): await self.delay(self.clk_period)
    @property
    async def clk_posedge(self): await RisingEdge(self._clk)
    async def clk_posedges(self, n): await ClockCycles(self._clk, n)
    async def clk_posedges_(self, clk, n=1): await ClockCycles(clk, n)
    @property
    async def clk_negedge(self): await FallingEdge(self._clk)
    async def posedge(self, signal): await RisingEdge(signal)
    async def negedge(self, signal): await FallingEdge(signal)
    @property
    async def step(self): await Timer(1, 'step')

    @property
    def time(self):
        from uvm.base.uvm_globals import uvm_sim_time
        return uvm_sim_time()

    async def join_any(self, *coroutines):
        """Join first coroutines."""
        # for c in coroutines:
            # await cocotb.triggers.Join(c)
        await cocotb.triggers.First(*coroutines)

    async def join(self, *coroutines):
        """Join all coroutines."""
        # for c in coroutines:
            # await cocotb.triggers.Join(c)
        if coroutines:
            await cocotb.triggers.Combine(*coroutines)

    async def clkcycles(self, n):
        for i in range(n):
            await self.clkcycle

    def raise_objection(self, phase: UVMPhase):
        phase.raise_objection(self)
        self.raised_objections.append((phase, self))

    def drop_objection(self, phase: UVMPhase):
        phase.drop_objection(self)
        self.raised_objections.remove((phase, self))

    def error(self, msg: str, total_seqitems=None):
        logmsg = msg
        num_msg =  f' seqitem no. {total_seqitems}' if total_seqitems else ''
        if logmsg != '':
            logmsg = f' >>> ERROR >>>{num_msg}:\n{msg}\n'
            logmsg += f'<<< ERROR <<<{num_msg}'
        self.errors.append((self, msg))
        self.top_errors.append((self, msg))
        self.log(f'{logmsg}')
        self.test_failed[self.test_parent()] = True
        if self.parent is not None and self.parent.isinstance(UVMTest):
            self.parent.passed(log_en=False)

    def passed(self, msg: str = '', log_en=True):
        self.passes.append((self, msg))
        if log_en:
            self.log(msg)
        if self.parent:
            self.parent.passed(log_en=False)

    async def wait(
            self, signal, condition: Optional[Callable] = None):
        using_base_condition = condition is None
        if using_base_condition:
            def condition(x): return bool(x.value)
        while not condition(signal):
            if using_base_condition:
                await self.posedge(signal)
            else:
                await self.clkcycle

    async def wait_(
            self, signal, condition: Optional[Callable] = None):
        await self.wait(signal, condition)
        await self.step

    def log(self, var, *more_vars, logger=uvm_info):
        # msg = str(msg)
        name = self.path_name
        prev_info_level = log.infolevel
        log.as_str = True
        log.infolevel = 'low'
        msg = log(var, *more_vars, frame=2, max_nof_lines=-1)
        log.as_str = False
        log.infolevel = prev_info_level
        msg = f'{name} @ {self.time}:\n{msg}'
        log_en = self.log_en
        do_print = True
        do_print = False
        if do_print:
            print(msg)
        # log.raw(msg)
        # for selectively printing messages only from failing tests at end:
        self.msgs.append((msg, self, logger, log_en, do_print))

    def parse_name(self, attrs):
        self.name: Optional[UVMObject] = self.setdefault(
            attrs, self.default_name)
        if self.parent is not None:
            self.path_name = self.parent.path_name + '.' + self.name
        else:
            self.path_name = self.name
        return self.name

    def connect_phase(self, phase):
        from tests.top.uvm import Driver, Monitor, Scoreboard, Sequencer
        super().connect_phase(phase)
        if (self._children.get(Driver) and self._children.get(Sequencer)):
            self._children[Driver].seq_item_port.connect(
                self._children[Sequencer].seq_item_export)

    async def main_phase(self, phase):
        from tests.top.uvm import Driver, Sequence, Sequencer
        if (
                self._children.get(Driver)
                and self._children.get(Sequencer)
                and self._children.get(Sequencer)
        ):
            self.fork(self._children[Sequence].start(
                self._children[Sequencer], None))

    def sample(self, signal):
        try:
            return signal.value.integer
        except ValueError:
            return -1
            self.log(signal.__class__)
            self.log(f'WARNING: got X')
