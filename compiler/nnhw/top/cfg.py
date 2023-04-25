"""Global configuration parameters."""

from debug import log
import sys
import typing as typ
from typing import List, Dict
import torch
from nnhw import top
from typing import Any
# exports:
from nnhw.top import (
    IOs, IO, LowerStrEnum, auto, Op, Path,
    FIPMethod, IJParam2, AttrDict, noinit, DTYPE,
    Pool, Device, ppstr, Level, Levels, tohex, ValueDict, LayerType, QuantMode,
    print_begin_end
)
from attr import define, Factory, field
import random
import os
import numpy as np
from torch.nn import Module as TorchNN
from torch import Tensor
import shutup


shutup.please()


@define
class Config(AttrDict):
    _set_values_to_indexes = False
    @property
    def ios2score(self):
        result = top.IOs.ALL[:-1]
        if self.onboard:
            result = [self.device.RESULT_IO]
            result = [IO.RESULT]
        result = dict(zip(result, result))
        if self.is_sim:
            result.pop(IO.POST_GEMM_PARAMS, None)
        if self.use_layer1_optimization2:
            result.pop(IO.A, None)
            result.pop(IO.B, None)
            result.pop(IO.POST_GEMM_PARAMS, None)
        return result

    @property
    def ios2show(self):
        result = top.IOs.ALL
        result = dict(zip(result, result))
        return result

    def init(self):
        """"""
        if self.istest:
            pass
            self.debuglevels.scoreboard = Level.OFF
        else:
            self.show_incorrect_ios = True
        # self.score_from_result_fifo = self.device.USE_RESULT_FIFOS

        self.read_perf_results = all([
            self.device.RECORD_PERF_RESULTS,
            (self.is_sim and self.score_from_result_fifo) or self.onboard])
        self.read_perf_results = True
        if self.testlevels.program >= Level.MAX:
            # self.do_mem_optimization = True
            self.use_layer1_optimization2 = True  # optimization in compiler
        # self.sim_max_cc_mult_factor = 0.5
        self.sim_max_cc_mult_factor = 1
        # if self.score_from_result_fifo:
            # self.sim_max_cc_mult_factor *= 2
        self.fast = self.istest and self.testlevels.program == Level.MAX
        self.repeat_input = self.fast

    max_model = None
    batch_size = 1
    # probe_result_io = True
    max_printable_io_size = 1e3
    # rm_sim_dir = True
    # sim_max_time = 503e2

    class DebugLevels(Levels):
        pass
        # device: Level = Level.LOW
        # config: Level = Level.LOW
        # program: Level = Level.LOW
        # scoreboard: Level = Level.LOW
        # scoreboard: Level = Level.MED
        # compiler: Level = Level.HIGH
        # encoder: Level = Level.LOW
        # program: Level = Level.LOW
        # mem: Level = Level.LOW
        # mem: Level = Level.MED
        # mem: Level = Level.HIGH
        # config: Level = Level.OFF
        # device: Level = Level.OFF
        # scoreboard: Level = Level.OFF
        # program: Level = Level.OFF

    bw = 16
    freq = 346.26
    # bw = 8
    # freq = 387.75

    mxu_size = 64
    bmembw = 576

    # from_torch_model = True
    # use_layer1_optimization2 = True
    input_load_pos = 1
    compare_mem_sz = True
    # use_board_rtl = True
    ############################################################
    # operation = Op.BOARD
    # operation = Op.TEST_QUICK
    # operation = Op.TEST
    operation = Op.SIM1
    # operation = Op.SIM2
    # _set_values_to_indexes = True

    class TestLevels(Levels):
        program: Level = Level.LOW
        # program: Level = Level.MED
        # program: Level = Level.HIGH
        # program: Level = Level.MAX

    def define_program(self, main, Program, NN, Layer):
        self.update_model()
        if self.testlevels.program <= Level.LOW:
            main.program = Program(
                Layer(),
                Layer(),
            )
        elif self.testlevels.program <= Level.MED:
            d = self.device
            cout = d.MXU_SZI * 1
            k = 1
            stride = 1
            h = 3 1
            w = h
            main.program = Program(
                Layer(Cout=cout, kernel_size=k, stride=stride,
                      batch_size=1,
                      Hin=k+h*stride,
                      Win=k+w*stride,
                      ),
                Layer(Cout=cout, kernel_size=k, stride=stride,
                      batch_size=1,
                      Hin=k+h*stride,
                      Win=k+w*stride,
                      ),
                # Layer(batch_size=2),
                # Layer(),
                # Layer(type=LayerType.Linear),
            )
        elif self.testlevels.program <= Level.HIGH:
            cout = self.device.SZI * 3
            k = 3
            stride = 1
            hw = 2
            main.program = Program(
                Layer(Cout=cout, kernel_size=k, stride=stride,
                      batch_size=4,
                      Hin=k+hw*stride,
                      # padding=1,
                      # pool_size=3, pool_stride=2
                      ),
                Layer(Cout=cout, kernel_size=k, stride=stride,
                      batch_size=1,
                      Hin=k+hw*stride,
                      padding=1,
                      pool_size=3, pool_stride=2
                      ),
                Layer(Cout=cout),
                Layer(type=LayerType.Linear, Cout=cout),
                Layer(type=LayerType.Linear, Cout=cout),
                Layer(type=LayerType.Linear, Cout=1),
            )
        elif self.testlevels.program <= Level.MAX:
            main.program = self.max_model()

    testlevels: TestLevels = TestLevels()
    set_values_to_indexes = (testlevels.program < Level.MAX
                             ) and _set_values_to_indexes
    ###########################################################################
    def update_model(self, ):
        device = self.device
        model: str = self.max_model.__name__
        device.MAX_W = (128)
        device.MAX_H = device.MAX_W

    def __getattr__(self, key): return None

    def rtl_path(self):
        from nnhw.synth.cli import synth_path
        from nnhw.synth.program_config import config as program_config
        result = Path.RTL
        if self.use_board_rtl or self.onboard:
            result = synth_path(cfg=program_config)
            result += '/rtl'
        return result

    def __attrs_post_init__(self):
        self.device.set_from_verilog_params(self.rtl_path(), self)
        self.sim_dir = (self.operation.value if self.is_sim else None)
        self.init()

    sim_dir: str = ''
    @property
    def is_sim(self): return self.operation.startswith('sim')
    @property
    def istest(self): return self.operation.startswith('test')
    @property
    def onboard(self): return self.operation is Op.BOARD


    perf_counters: list = []
    input: Tensor = noinit()
    output: Tensor = noinit()
    real_output: Tensor = noinit()
    device: Device = Factory(Device)
    debuglevels: DebugLevels = DebugLevels()


config: Config = Config()
device: Device = config.device
