# from src.bk.abc_tiler import ATiler, BTiler, CTiler
import math
import unittest
from collections import namedtuple
from copy import deepcopy
from math import ceil, floor
import numpy as np
import sections
import torch
from debug import log
from nnhw.tiler import ATiler, BTiler, Space
from nnhw.tiler.tiler0.abc_tiler import ATiler as ATiler2
from nnhw.tiler.tiler0.abc_tiler import BTiler as BTiler2
from utils import AttrDict, ijParam


class Obj:
    pass


class TilerTest:

    def assert_dict(self, test_value, expected_value, *args, **kwds):
        attr = 'tensor'
        info_msg = (f"got       `{attr}` = `{test_value}`\n"
                    + f"expected `{attr}` = `{expected_value}`")
        err_msg = "\nERROR:\n" + info_msg
        log(info_msg)
        self.assertEqual(test_value, expected_value, err_msg)

    def assert_eval(self, tiler, tensor, test_expected):
        for expression, expected_value in test_expected.items():
            log(expression)
            test_value = eval(expression)
            # log(test_value)
            info_msg = (f"{expression}\n\n"
                        + "expected:\n\n"
                        + f"`{expected_value}`\n\ngot:\n\n`{test_value}`")
            err_msg = "\n\nERROR: " + info_msg
            # log(info_msg)
            self.assertEqual(test_value, expected_value, err_msg)

    def test_top(self,):
        kernel_size = 1
        # kernel_size = 3
        if self.type == 'B':
            kernel_size = self.tsize.H
        kernel_stride = 1
        test_kwds = {
            # 'sys_arr_size': ijParam(i=4, j=2),
            'sys_arr_size': ijParam(i=2, j=2),
            'kernel_size': ijParam(i=kernel_size, j=kernel_size),
            'kernel_stride': ijParam(i=kernel_stride, j=kernel_stride),
            'pool_stride': ijParam(i=1, j=1),
        }
        if self.type == 'A':
            tiler = ATiler(**test_kwds)
        if self.type == 'B':
            tiler = BTiler(**test_kwds)
        x = self.gen_tensor(test_kwds['kernel_size'])

        counter = tiler(x)
        log(counter)
        x_expect = self.validation_data(x, test_kwds).squeeze()
        # log(x_expect)
        # log(x_test)
        # assert x_expect.squeeze().tolist() == x_test.squeeze().tolist()
        assert torch.sum(x_expect) == torch.sum(counter.data)
        assert torch.sum(x_expect) == torch.sum(counter.data)

    def validation_data(self, x, test_kwds):
        test_kwds = deepcopy(test_kwds)
        # if self.type == 'B':
        # x = x.permute(0, 2, 3, 1)
        test_kwds['kernel_size'] = np.array(test_kwds['kernel_size'])
        test_kwds['kernel_stride'] = np.array(test_kwds['kernel_stride'])
        test_kwds['pool_stride'] = np.array(test_kwds['kernel_stride'])
        # test_kwds.pool_tile_size = test_kwds.pool_size
        conv = Obj()
        conv.__dict__ = deepcopy(test_kwds)
        conv.stride = test_kwds['kernel_stride']
        conv.out_chan_size = np.array(
            [math.floor(self.tsize.H/conv.stride[0]),
             math.floor(self.tsize.W/conv.stride[1])])
        if self.type == 'A':
            tiler = ATiler2(test_kwds['sys_arr_size'])
        if self.type == 'B':
            tiler = BTiler2(test_kwds['sys_arr_size'])
        x = tiler(x, conv)
        return x

    def gen_tensor(self, kernel_size):
        return torch.randint(low=1, high=9, size=self.tsize)


# class BTilerTest:
class BTilerTest(TilerTest, unittest.TestCase):
    def __init__(self, *args, **kwds):
        self.type = 'B'
        super().__init__(*args, **kwds)
        self.TensorDims = namedtuple('TensorDims', 'Cout Cin H W',
                                     defaults=[0, 0, 0, 0])
        # self.tsize = self.TensorDims(Cout=63, Cin=8, H=32, W=16)
        self.tsize = self.TensorDims(Cout=2, Cin=2, H=4, W=4) # self.tsize = self.TensorDims(Cout=2, Cin=2, H=2, W=2)


# class ATilerTest:
class ATilerTest(TilerTest, unittest.TestCase):
    def __init__(self, *args, **kwds):
        self.type = 'A'
        super().__init__(*args, **kwds)
        self.TensorDims = namedtuple('TensorDims', 'Cin H W',
                                     defaults=[0, 0, 0])
        # self.tsize = self.TensorDims(Cin=29, H=16, W=7)
        # self.tsize = self.TensorDims(Cin=2, H=8, W=4)
        self.tsize = self.TensorDims(Cin=2, H=4, W=4)

    def gen_tensor(self, kernel_size):
        x = super().gen_tensor(kernel_size).unsqueeze(0)
        return torch.nn.ZeroPad2d(floor(kernel_size.j/2))(x)
