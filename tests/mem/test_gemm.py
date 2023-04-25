import unittest
from collections import namedtuple
from math import ceil, floor
import torch
from nnhw.tiler import ATiler, BTiler
from utils import ijParam


class GemmTest(unittest.TestCase):
    def setUp(self):
        self.ATensorDims = namedtuple(
            'TensorDims', 'Cout Cin H W', defaults=[0, 0, 0, 0])
        self.BTensorDims = namedtuple(
            'TensorDims', 'Cin H W', defaults=[0, 0, 0])
        asize = self.TensorDims(Cout=4, Cin=4, H=4, W=4)
        bsize = self.TensorDims(Cin=2, H=4, W=4)
        kernel_size = 1
        kernel_stride = 1
        kwds = {
            'sys_arr_size': ijParam(i=2, j=2),
            'kernel_size': ijParam(i=kernel_size, j=kernel_size),
            'kernel_stride': ijParam(i=kernel_stride, j=kernel_stride),
            'pool_stride': ijParam(i=1, j=1),
        }
        self.atiler = ATiler(**kwds)
        self.btiler = BTiler(**kwds)
        a = self.gen_tensor(asize)
        self.a = torch.nn.ZeroPad2d(floor(kernel_size.j/2))(a)
        self.b = self.gen_tensor(bsize)

    def gen_tensor(self, size):
        return torch.randint(low=1, high=9, size=size)

    def test_gemm(self):
        pass
