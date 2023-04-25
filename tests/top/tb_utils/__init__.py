"""No longer using below test, instead using the individual tests in this
submodule now.
"""

from debug import log
from nnhw import top
from tests.top import uvm


class UtilsTest(uvm.Test):
    from .tb_dff import DffTest
    from .tb_shift_vec import ShiftVecTest
    from .tb_shift_reg import ShiftRegTest

    def __init__(self, *args, **attrs):
        self.max_clk_cycles = attrs.setdefault('max_clk_cycles', 20)
        self.total_seqitems = attrs.setdefault('total_seqitems', 8)
        super().__init__(**attrs)
        attrs['parent'] = self
        # attrs['log_en'] = False
        self.shift_vec_test = self.ShiftVecTest(**attrs)
        self.shift_reg_test = self.ShiftRegTest(**attrs)
        self.dff_test = self.DffTest(**attrs)


uvm.uvm_component_utils(UtilsTest)
