from debug import log
import sys
import typing as typ
from typing import List, Dict
import torch
from nnhw import top
from typing import Any
from nnhw.top import (
    IOs, IO, LowerStrEnum, auto, Op, Path,
    FIPMethod, IJParam2, AttrDict, noinit, DTYPE,
    Pool, Device, ppstr, Level, Levels, tohex, ValueDict, LayerType, QuantMode,
    print_begin_end, prod, int_range
)
from attr import define, Factory, field
import random
import os
import numpy as np
from torch.nn import Module as TorchNN
from torch import Tensor
import shutup
from nnhw.top.cfg import Config, config
from nnhw.arith import Program, NN, Layer


@define
class Main:
    config: Config
    program: Program = noinit()
    programs: List[Program] = noinit()
    input: Tensor = noinit()

    def __call__(self):
        self.setup()
        self.run()

    def setup(self):
        self.log_setup()
        self.sim_setup()
        seed = int.from_bytes(os.urandom(8), byteorder="big") & (2 ** 32 - 1)
        seed = 25
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        config = self.config
        logkwds = dict(show_context=False)
        if config.debuglevels.config:
            log.raw(f'seed = {seed}\n')
            log(config.rtl_path(), **logkwds)
            log(config.operation, **logkwds)
            log(config.testlevels.program, **logkwds)
            log(config.from_torch_model, **logkwds)
            log.raw(f"'{config.rtl_path()}'\n")
        if config.debuglevels.device:
            log(config.ios2score)
            log(config.ios2show)
            log(config.device, context=False)
        if config.from_torch_model:
            if config.from_torch_model:
                from nnhw.top.nnhw import NNHW
                NNHW()()
                from nnhw.top.parser import Parser
                self.program = Program(Parser()(config.model, config.device))
        else:
            config.define_program(self, Program, NN, Layer)

    def setup_input(self):
        layer0 = self.program[0][0]
        batch_size = layer0.batch_size
        device = self.config.device
        io = IO.A
        _batch_size = batch_size
        if self.config.repeat_input:
            _batch_size = 1
        sizes = layer0.torch_io_sizes(self.config.larger_size_mult,
                                      _batch_size)
        self.input = torch.randint(
            *int_range(device.WIDTHS[io], signed=device.SIGNED[io]),
            sizes[io], dtype=DTYPE)
        x = []
        if config.set_values_to_indexes:
            self.input = layer0.set_a_values_to_indexes(self.input)
        if self.config.repeat_input:
            if config.partsel_ios:
                _x = layer0.partsel_io_cin(self.input[0].unsqueeze(0))
            else:
                _x = self.input[0].unsqueeze(0)
        for i in range(batch_size):
            if self.config.repeat_input:
                x.append(_x.detach().clone())
            else:
                if config.partsel_ios:
                    x.append(layer0.partsel_io_cin(self.input[i].unsqueeze(0)))
                else:
                    x.append(self.input[i].unsqueeze(0))
        x = torch.cat(tuple(x), 0)
        self.input = x

    def run(self):
        if self.config.from_torch_model:
            self.set_result_from_torch_model()
        if self.config.from_torch_model:
            x = self.input
        program = self.program
        self.program.compile(self.config.device)
        nn = self.program.nns[0]
        self.programs = []
        device = self.config.device
        self.setup_input()
        from timeit import default_timer as timer
        start = timer()
        batch_size = main.program.batch_size
        if self.config.repeat_input:
            self.program.compile_input(device, self.input[
                batch_size-1].unsqueeze(0), batch_size-1)
            for layer in nn:
                if not layer.islinear:
                    last_conv_layer = layer
            inpt = last_conv_layer.expected.torch.c
        for n in range(batch_size):
            if self.config.repeat_input and batch_size > 1:
                nn.linear_inputs[n] = inpt
            else:
                self.program.compile_input(
                    device, self.input[n].unsqueeze(0), n)
            if self.is_sim:
                program = main.program.copy(device, n)
                self.programs.append(program)
        if self.config.repeat_input:
            self.program.compile_input(device, self.input[
                batch_size-1].unsqueeze(0), batch_size-1)
        end = timer()
        nn.compiler.compile_full_instruc(nn)
        if self.config.debuglevels.program:
            kwds = dict(value_only=True)
            log('\n', **kwds)
            log(self.program, **kwds)
        if self.config.istest:
            pass
            for layer in self.program.layers:
                self.test_score(layer)
            self.test()
        if self.config.operation == Op.TEST_AFTER_COMPILE:
            self.test_after_compile()
        if self.config.onboard:
            from nnhw import instruc
            from nnhw.instruc import regs
            self.program()

    def set_result_from_torch_model(self):
        layer = self.program.layers[-1]
        p = layer.pgp_fields
        out = self.real_output
        log(p.mc)
        log(p.zc.size())
        log(out.size())
        for ci, x in enumerate(out[0]):
            out[0][ci] = out[0][ci] / p.mc + p.zc[ci]
        out = out.trunc().to(torch.uint8)
        self.output = out
        for io in [IO.C, IO.RESULT]:
            if io not in layer.ios:
                continue
            setattr(layer, io, self.output)
        for io in [IO.A]:
            if io not in layer.ios:
                continue
            setattr(layer, io, self.input)

    @property
    def is_sim(self): return self.config.operation.startswith('sim')
    @property
    def istest(self): return self.config.operation.startswith('test')
    @property
    def onboard(self): return self.config.operation is Op.BOARD

    def test_score(self, layer):
        msg, passed = layer.score(
        )
        if msg:
            log(msg, max_nof_lines=-1, value_only=True)

    def test(self):
        from .test_main import Test
        Test(self)

    def test_gpt(self):
        from transformers import GPT2ForSequenceClassification
        from transformers import GPT2Config
        # from transformers import SequenceClassifierOutputWithPast
        import torch
        c = GPT2Config()
        m = GPT2ForSequenceClassification(c)
        x = torch.ones((1, 8), dtype=torch.int64)
        x = m(
            x,
        )
        log(x.logits.tolist())

    def test_quick(self):
        """"""
        from .test_main import Test
        Test(self)

    def test_after_compile(self):
        pass

    def log_setup(self):
        from debug import log
        import re
        suffix = self.config.operation
        from nnhw import synth
        if self.config.onboard:
            suffix = self.config.rtl_path().split('/')
            suffix = suffix[-3] + '\\' + suffix[-2]
        if self.config.is_sim:
            size = self.config.device.SZI
            suffix = f'{suffix}'
        if not log.file_was_set:
            log.files = [Path.NNHW + '/log.py',
                         Path.NNHW + '/log-'
                         + re.sub('_', '-', suffix + '.py')]
            log.file_was_set = True

    def sim_setup(self):
        if self.config.sim_dir:
            self.config.sim_dir = self
            from utils import run
            if not os.environ.get('MODULE'):  # if not running in cocotb
                from nnhw.sim import main
                main()
                quit()
        from nnhw.rxtx.device_controller import DeviceController
        if self.config.operation == Op.TEST_QUICK:
            self.test_quick()
            quit()


main = Main(config)
