# from debug import log
# from utils import run
# from nnhw.top import Path
# log.file = Path.NNHW + '/log' + run('pwd')[:-1].split('/')[-1][-1] + '.py'
import typing as typ
from os import environ as env
from typing import List, Tuple
import cocotb
from uvm.base import run_test
from cocotb.triggers import Event
from uvm import UVMObject
from uvm.base.uvm_phase import UVMPhase
# from nnhw.top import name
from nnhw.top import nameof, varname
from tests.arith.tb_double_vecbuf import DoubleVecbufTest
# from tests.arith.tb_mxu import MxuTest as MxuTest
# from tests.arith.tb_gemm import GemmTest
# from tests.arith.tb_post_gemm import PostGemmTest
# from tests.arith.tb_arith import ArithTest
from tests.arith.tb_pe import PeTest
from tests.instruc.tb_instruc import InstrucTest
from tests.top.tb_top import TopTest
from tests.top import uvm
from tests.top.tb_utils import UtilsTest
from tests.top.tb_utils.tb_add_shift_vec import AddShiftVecTest
from tests.top.tb_utils.tb_add_vec import AddVecTest
from tests.top.tb_utils.tb_dff import DffTest
from tests.top.tb_utils.tb_shift_reg import ShiftRegTest
from tests.top.tb_utils.tb_shift_vec import ShiftVecTest
from tests.top.tb_utils.tb_triangle_buf import TriangleBufTest
from tests.mem.tb_dram import DramTest


class TopTestList(uvm.Test):
    def __init__(self, dut, **attrs):
        self.parent = None
        self.dut = dut
        self.is_toplevel_test = True
        self.top = attrs.setdefault(varname(), self.dut)
        self.max_clk_cycles = attrs.setdefault(varname(), 200000)
        self.top_timeout = attrs.setdefault(varname(), Event())
        self.total_seqitems = attrs.setdefault(varname(), 4)
        self.clk_period = attrs.setdefault(varname(), 10)
        self.time_unit = attrs.setdefault(varname(), 'NS')
        self.log_en = attrs.setdefault(varname(), None)
        self.raised_objections: List[
            Tuple[UVMPhase, UVMObject]] = attrs.setdefault(varname(), [])

        super().__init__(**attrs, name='sim')
        attrs[nameof(self.is_toplevel_test)] = False
        attrs[nameof(self.parent)] = self
        attrs.pop(nameof(self.dut), None)
        # attrs['log_en'] = False
        tests = eval(env['TESTS'])
        for Test in tests:
            Test(**attrs)


@cocotb.test()
async def tb(dut):
    # uvm.base.uvm_top.finish_on_completion = False
    # testname = env['UVM_TESTNAME']
    # log(testname)
    # ExperimentTest()
    TopTestList(dut)
    await run_test()
    # await uvm.base.run_test('ExperitTest', dut)
