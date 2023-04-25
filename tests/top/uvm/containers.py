import typing as typ
import uvm
from debug import log
from uvm import UVMObject, uvm_error, uvm_fatal, uvm_info
from uvm.base.uvm_object_globals import UVM_ERROR, UVM_FATAL
from uvm.comps import UVMAgent, UVMDriver, UVMEnv, UVMMonitor, UVMScoreboard
from uvm.comps.uvm_test import UVMTest
from varname import nameof as nameof
from tests.top.uvm import Base
from tests.top import uvm
# exports:


class Container(Base):
    header = '-' * 79

    @property
    def is_toplevel_test(self):
        return self.isinstance(
            UVMTest) and self.test_parent()._is_toplevel_test

    @is_toplevel_test.setter
    def is_toplevel_test(self, value):
        self._is_toplevel_test = value


@uvm.getbases
class Agent(Container, UVMAgent, ):
    pass


@uvm.getbases
class Env(Container, UVMEnv, ):
    pass


@uvm.getbases
class Test(Container, UVMTest, ):

    async def reset_phase(self, phase):
        if not self.is_toplevel_test:
            return
        self.raise_objection(phase)
        self.fork(self.always_clk(
            self.top.clk, self.clk_period, is_top_clk=True))
        await self.clk_negedge
        self.top.resetn <= 1
        await self.clk_negedge
        self.top.resetn <= 0
        await self.clk_posedge
        self.top.resetn <= 1
        self.drop_objection(phase)

    async def run_phase(self, phase):
        self.raise_objection(phase)
        await self.delay(10)
        self.drop_objection(phase)

    async def always_clk(self, clk, period, is_top_clk=False, delay=0):
        clk <= 1
        n = 0
        half_period = period / 2
        await self.delay(delay)
        while True:
            n += 1
            await self.delay(half_period)
            clk <= int(not clk.value)
            if is_top_clk and n >= 2*self.max_clk_cycles:
                break
        if not is_top_clk:
            return
        self.top_timeout.set()
        for phase, obj in self.raised_objections:
            self.log(f'obj: {obj.path_name}, phase: {phase.name}')
            if obj.isinstance(UVMMonitor):
                obj.log(
                    f'total_sampled_seqitems: {obj.total_sampled_seqitems} / '
                    + f'{obj.total_seqitems}'
                )
            obj.error('Test timeout')
            obj.drop_objection(phase)
            self.error(f'Timeout on {obj.path_name}')

    def check_phase(self, phase):
        """Erase log output then only re-print messages from failed tests."""
        if not self.is_toplevel_test:
            return
        log.as_str = False
        # log.raw('', mode='w')
        log.raw('\n')
        log.header('-')
        log.raw('\n')
        for (msg, obj, logger, log_en, done_print) in self.msgs:
            test_failed = self.test_failed.get(obj.test_parent())
            if log_en is True or (test_failed and log_en is not False):
                log.raw(msg)
                # if not done_print:
                    # print(msg)

    def report_phase(self, phase):
        return
        self.report_errors()

    def report_errors(self):
        s = ''
        if self.errors:
            s += self.header + '\n'
            s += self.path_name + ' ERRORS:\n'
        for obj, msg in self.errors:
            s += msg + '\n'
        if self.is_toplevel_test:
            s += self.header + '\n'
        if self.errors:
            s += '\n'
            log.raw(s)
            if not log.use_stdout:
                print(s, end='')
        if self.is_toplevel_test:
            log.raw(f'{self.header}\n')
            if not log.use_stdout:
                print(self.header)

    def final_phase(self, phase):
        if self.is_toplevel_test:
            self.top_final_phase()
        else:
            self.subtest_final_phase()

    def subtest_final_phase(self):
        s = ''
        name = self.path_name
        if self.errors:
            s += f'{name}:\n    '
            s += "!! FAILED !!"
        elif self.passes:
            s += f'{name}:\n    '
            s += "PASSED"
        elif self.isinstance(UVMTest):
            s += f'{name}:\n    '
            s += "!! NO ASSERTIONS TESTED !!"
        assert self.errors is self.test_parent().errors
        if not self.isinstance(UVMTest):
            return
        if s:
            log.raw(f'{s}\n')
            if not log.use_stdout:
                print(s)

    def top_final_phase(self):
        from uvm.base.uvm_report_server import UVMReportServer
        server = UVMReportServer.get_server()
        name = self.path_name
        s = f'{name}:\n    '
        if (server.get_severity_count(UVM_FATAL) or
                server.get_severity_count(UVM_ERROR)
                or len(self.top_errors)):
            logger = uvm_fatal
            s += "!! FAILED !!"
        elif self.passes:
            logger = uvm_info
            s += "PASSED"
        else:
            logger = uvm_info
            s += "!! NO ASSERTIONS TESTED !!"
        log.raw(f'{self.header}\n')
        log.raw(f'{s}\n')
        log.raw(f'{self.header}\n')
        if not log.use_stdout:
            print(self.header)
            print(s)
            print(self.header)


class GroupTest(Env):
    """To be subclassed so that below method can be used. See its docstring"""
    grouptest_dutname: str = 'duts'  # override this - sv inst name
    unittest_dutname: str = 'dut_select'  # override this - sv inst name
    # UVM Test cls to test the unittest_dut:
    UnitTest_: typ.Type[object] = 'OverrideThis'

    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        if self.grouptest_dutname is None:
            self.grouptest_dutname = uvm.camel2snake(
                self.__class__.__name__[:-4]) + '_duts'
        group_dut = getattr(self.dut, self.grouptest_dutname, self.dut)
        if self.unittest_dutname is None:
            self.unittest_dutname = self.grouptest_dutname[:-1]
        self.unittests(group_dut, *args, **attrs)

    def unittests(self, group_dut, *args, **attrs):
        """Recursively instantiate unittests for duts defined in genblks that
        iterate over coverage parameters. genblks and unit duts must be coded
        in a specific way, see usage example from a dut tested by a subclass to
        this class.
        """
        _ = dir(self.dut)
        i = 0
        block_prefix = 'genblk'
        self.cleanup(attrs)
        from tests.top import FIPMethod
        while True:
            i += 1
            cover_block_name = f'{block_prefix}{i}'
            if not hasattr(group_dut, cover_block_name):
                break
            cover_block = getattr(group_dut, cover_block_name)
            for blocki in cover_block:
                cover_param_name = repr(blocki.COVER_PARAM_NAME.value)[2:-1]
                cover_param_value = getattr(blocki, cover_param_name)
                if cover_param_name == 'FIP_METHOD_':
                    for k, v in FIPMethod.__members__.items():
                        if cover_param_value == v:
                            cover_param_value = k
                testname = f'g{i}.{cover_param_name[:-1]}={cover_param_value}'
                # this is mysteriously needed before accessing blocki attrs:
                _ = dir(blocki)
                if hasattr(blocki, f'{block_prefix}1'):
                    next_group_dut = blocki
                    Test_ = self.__class__
                else:
                    next_group_dut = getattr(blocki, self.unittest_dutname,
                                             None)
                    if next_group_dut is None:
                        continue
                    Test_ = self.UnitTest_
                setattr(self, testname,
                        Test_(
                            *args, **attrs,
                            dut=next_group_dut,
                            name=testname,
                        )
                        )
