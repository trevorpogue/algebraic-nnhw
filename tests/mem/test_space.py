import math
import unittest
from copy import deepcopy
from math import ceil, floor
import sections
import torch
from debug import log
from torch import nn
from nnhw import Space


class SpaceTest(unittest.TestCase):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.count_depth_1_test = 0

    def test_tile(self,):
        log.section('1.0')
        tile_sizes = [0]
        sizes = [4,   4,  4, 4]
        strides = [1000, 100, 10, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        init_attrs['name'] = ['3', '2', '1', '0']
        expected_attrs = {'size': [4, 4, 4, 4],
                          'stride': [1000, 100, 10, 1]}
        space = Space(**init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        log.section('1.1')
        tile_sizes = [1]
        sizes = [4,   4,  4, 4]
        strides = [1000, 100, 10, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        init_attrs['name'] = ['3', '2', '1', '0']
        expected_attrs = {'size': [4, 4, 4, 4, 1],
                          'stride': [1000, 100, 10, 1, 1]}
        space = Space(**init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        log.section('1.2')
        tile_sizes = [4]
        sizes = [4,   4,  4, 4]
        strides = [1000, 100, 10, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        init_attrs['name'] = ['3', '2', '1', '0']
        expected_attrs = {'size': [4, 4, 4, 4, ],
                          'stride': [1000, 100, 10, 1, ]}
        space = Space(*range(len(sizes)), **init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        log.section('test stage 1')
        self.depth_1_test(tile_sizes=1, sizes=8, strides=1)
        self.depth_1_test(tile_sizes=2, sizes=8, strides=1)
        self.depth_1_test(tile_sizes=[2, 2], sizes=[8, 8], strides=[8, 1])
        self.depth_1_test(tile_sizes=[2, 2, 2], sizes=[
                          8, 8, 8], strides=[64, 8, 1])

        log.section('test stage 2')
        log.section('2.1')
        tile_sizes = [5, 2]
        sizes = [10, 8]
        strides = [2, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        expected_attrs = {'size': [2, 4, 5, 2, ], 'stride': [10, 2, 2, 1, ]}
        space = Space(*range(len(sizes)), **init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        log.section('2.1.1')
        tile_sizes = [2, 2]
        sizes = [8, 8]
        strides = [8, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        expected_attrs = {'size': [4, 2, 4, 2, ], 'stride': [16, 8, 2, 1, ]}
        space = Space(*range(len(sizes)), **init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes,
                         dim_order='child_dominant')

        log.section('2.2')
        tile_sizes = [2, 2]
        sizes = [8, 8]
        strides = [8, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        expected_attrs = {'size': [4, 4, 2, 2, ], 'stride': [16, 2, 8, 1, ]}
        space = Space(*range(len(sizes)), **init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        log.section('2.3')
        tile_sizes = [2, 2]
        sizes = [8, 8]
        strides = [8, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        expected_attrs = {'size': [4, 4, 2, 2, ], 'stride': [16, 2, 8, 1, ]}
        space = Space(*range(len(sizes)), **init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        log.section('2.4')
        tile_sizes = [4, 4]
        sizes = [8, 8]
        strides = [8, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        expected_attrs = {'size': [2, 2, 4, 4, ], 'stride': [32, 4, 8, 1, ]}
        space = Space(*range(len(sizes)), **init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        log.section('2.5')
        tile_sizes = [4, 2]
        sizes = [8, 8]
        strides = [8, 1]
        init_attrs = self.init_attrs(tile_sizes, sizes, strides)
        expected_attrs = {'size': [2, 4, 4, 2, ], 'stride': [32, 2, 8, 1, ]}
        space = Space(**init_attrs)
        space = Space(*range(len(sizes)), **init_attrs)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        log.section('2.6')
        ms_leaf, ls_leaf = 0, 1
        ms_child, ls_child = 0, 1
        # tile_fill, tile_count = 0, 1
        tile_sizes = [2, 2]
        tile_strides = [1, 1]
        sizes_ms_child = [8, 8]
        strides_ms_child = [512, 64]
        init_attrs_ms = self.init_attrs(tile_sizes,
                                        sizes_ms_child, strides_ms_child)
        sizes_ls_child = [8, 8]
        strides_ls_child = [8, 1]
        init_attrs_ls = self.init_attrs(tile_sizes,
                                        sizes_ls_child, strides_ls_child)
        expected_attrs = {'size': [
            # tile_count
            # ms child
            sizes_ms_child[ms_leaf],  # ms leaf
            math.ceil(sizes_ms_child[ls_leaf]\
                      / (tile_sizes[ms_child]*tile_strides[ms_child])),  # ls leaf
            # ls child
            sizes_ls_child[ms_leaf],  # ms leaf
            math.ceil(sizes_ls_child[ls_leaf]\
                      / (tile_sizes[ls_child]*tile_strides[ls_child])),  # ls leaf
            # tile_fill
            # ms child
            1,  # ms leaf
            tile_sizes[ms_child],  # ls leaf
            # ls child
            1,  # ms leaf
            tile_sizes[ls_child],  # ls leaf
        ], 'stride': [
            # tile_count
            # ms child
            strides_ms_child[ms_leaf],  # ms leaf
            tile_sizes[ms_child] * tile_strides[ms_child]\
            * strides_ms_child[ls_leaf],  # ls leaf
            # ls child
            strides_ls_child[ms_leaf],  # ms leaf
            tile_sizes[ls_child] * tile_strides[ls_child]\
            * strides_ls_child[ls_leaf],  # ls leaf
            # tile_fill
            # ms child
            0,  # ms leaf
            strides_ms_child[ls_leaf] * tile_strides[ms_child],  # ls leaf
            # ls child
            0,  # ms leaf
            strides_ls_child[ls_leaf] * tile_strides[ls_child],  # ls leaf
        ]
        }
        del_count = 0
        expected_attrs_copy = deepcopy(expected_attrs)
        for i, (size, stride) in enumerate(zip(expected_attrs_copy['size'],
                                               expected_attrs_copy['stride'])):
            if size == 1 and stride == 0:
                expected_attrs['size'].pop(i-del_count)
                expected_attrs['stride'].pop(i-del_count)
                del_count += 1

        space = Space()
        space_ms = Space(0, 1, **init_attrs_ms)
        space_ls = Space(0, 1, **init_attrs_ls)
        # ms_ls = ['ms', 'ls']
        space['child_ms'] = space_ms
        space['child_ls'] = space_ls
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

        mn = Space('mn', (), 'H', 'W',
                   size=[224, 224],
                   stride=[10000, 100])
        k = Space('k', (), ['kernel', (), 'H', 'W'], 'Cin',
                  # k = Space('k', ('kernel', ('H', 'W'), 'Cin'),
                  size=[[16, 16], 4],
                  stride=[[10000, 100], 1])
        space = Space(mn, k)
        tile_sizes = [64, 2]
        expected_attrs = {'size': [
            # tile_count
            mn.leaves['H'].size, ceil(mn.leaves['W'].size/tile_sizes[0]),
            *k['kernel'].sizes, ceil(k.leaves['Cin'].size/tile_sizes[1]),
            # tile_fill
            *tile_sizes],
            'stride': [
            # tile_count
                10000, 6400, 10000, 100, 2,
            # tile_fill
                100, 1,
        ],
        }
        self.assert_main(None, expected_attrs, space, tile_sizes)

        mn = Space('mn', (), 'H', 'W',
                   size=[224, 224],
                   stride=[10000, 100])
        k = Space('k', (), ['kernel', (), 'H', 'W'], 'Cin',
                  size=[[16, 16], 4],
                  stride=[[10000, 100], 1])
        space = Space(mn, k)
        tile_sizes = [64, 2]
        expected_attrs = {'size': [
            mn.leaves['H'].size,
            ceil(mn.leaves['W'].size/tile_sizes[0]),
            tile_sizes[0],
            *k['kernel'].sizes, ceil(k.leaves['Cin'].size/tile_sizes[1]),
            tile_sizes[1],
        ],
            'stride': [
                10000, 6400,  # tile_count
                100,  # tile_fill
                10000, 100, 2,  # tile count
                1,  # tile_fil
        ],
        }
        self.assert_main(None, expected_attrs, space, tile_sizes,
                         dim_order='interleaved')

    def init_attrs(self, tile_sizes, sizes, strides):
        # d = []
        # for i, (tile_size, size, stride) in enumerate(zip(tile_sizes, sizes,
        # strides)):
        return {
            'size': sizes,
            'stride': strides,
        }

    def expected_attrs(self, tile_sizes, sizes, strides):
        d = {'size': [], 'stride': []}
        for tile_size, size, stride in zip(
                tolist(tile_sizes), tolist(sizes), tolist(strides)):
            d['size'].append(math.ceil(size / tile_size))
            d['stride'].append(tile_size*stride)
        for tile_size, size, stride in zip(
                tolist(tile_sizes), tolist(sizes), tolist(strides)):
            d['size'].append(tile_size)
            d['stride'].append(stride)
        return d

    def attrs(self, tile_sizes, sizes, strides):
        return self.init_attrs(tile_sizes, sizes, strides),\
            self.expected_attrs(tile_sizes, sizes, strides)

    def depth_1_test(self, tile_sizes, sizes, strides):
        log(f'---- depth_1_test {self.count_depth_1_test} ----')
        self.count_depth_1_test += 1
        init_attrs, expected_attrs = self.attrs(tile_sizes, sizes, strides)
        if isinstance(sizes, list):
            args = range(len(sizes))
            space = Space(*args, **init_attrs)
        #     log(args)
        #     log(init_attrs)
        #     log(space)
        else:
            space = Space(**init_attrs)
        # for i, d in enumerate(init_attrs):
        # space[f'child_{i}'] = Space(**d)
        self.assert_main(init_attrs, expected_attrs, space, tile_sizes)

    def assert_main(self, init_attrs, expected_attrs, space, tile_size,
                    dim_order='tile_dominant', method='tile'):
        # if self.debug_mode: print(space)
        pre_size = space.sizes
        pre_stride = space.strides
        # log(space)
        has_tensor = False
        if space.hastensor:
            has_tensor = True
            expected_tensor = space.data.detach().clone()
        if method == 'tile':
            space.unflatten_(tile_size, dim_order=dim_order)
        #     if space.hastensor:
        #         if not isinstance(tile_size, list):
        #             expected_tensor = unflatten(expected_tensor)
        #         else:
        #             for i, t in enumerate(tile_size):
        #                 unflatten = nn.Unflatten(i, (space[i]('sizes', list)))
        #                 expected_tensor = unflatten(expected_tensor)
        #     # if method == 'flatten':
        print_space = sections(
            pre_size=pre_size,
            pre_stride=pre_stride,
            tile_size=tile_size,
            size=space.size,
            stride=space.stride,
        )
        print_attrs = deepcopy(expected_attrs)
        print_attrs['pre_size'] = pre_size
        print_attrs['pre_stride'] = pre_stride
        print_attrs['tile_size'] = tile_size
        print_attrs['size'] = expected_attrs['size']
        print_attrs['stride'] = expected_attrs['stride']
        # log(err_msg)
        # log(space)
        attr_list = ['pre_size', 'pre_stride', 'tile_size',
                     'size', 'stride']
        max_attr_len = max(list(map(len, attr_list)))
        for attrname in attr_list:
            pad = ' ' * (max_attr_len - len(attrname))
            if 0:
                log.raw(f"got       '{attrname}'" + pad
                        + f" = {print_space(attrname)}\n"
                        )
                # if test_value != expected_value:
                log.raw(f"expected  '{attrname}'" + pad
                    + f" = {print_attrs[attrname]}\n\n")
        for attrname, expected_value in expected_attrs.items():
            test_value = space(attrname)
            info_msg = f"got       '{attrname}' = {test_value}\nexpected  "\
                f"'{attrname}' = {expected_value}"
            # log(info_msg)
            err_msg = "\nERROR:\n" + info_msg
            self.assertEqual(test_value, expected_value, err_msg)
        assert space.hastensor == has_tensor
        if space.hastensor:
            # log(space.tensor.size(), expected_tensor.size(), space)
            # assert torch.equal(space.tensor, expected_tensor)
            assert list(space._tensor.size()) == space('size', list)

    def test_flatten_basic(self):
        log.section('test_flatten_basic')
        space = Space(size=[4, 2], stride=[2, 1])
        expected_attrs = dict(size=8, stride=1)
        space_cpy = space.flatten(names=False)
        self.assert_main(None, expected_attrs, space_cpy, [1],
                         method='flatten')
        space.flatten_(names=False)
        self.assert_main(None, expected_attrs, space, [1], method='flatten')

    def test_flatten(self):
        log.section('test_flatten')
        mn = Space('mn', (), 'H', 'W',
                   size=[224, 224],
                   stride=[10000, 100])
        k = Space('k', (), ['kernel', (), 'H', 'W'], 'Cin',
                  size=[[16, 16], 4],
                  stride=[[10000, 100], 1])
        space = Space(mn, k)
        orig_space = deepcopy(space)
        tile_sizes = [56, 2]
        expected_attrs = {'size': [
            # tile_count
            mn.leaves['H'].size, ceil(mn.leaves['W'].size/tile_sizes[0]),
            *k['kernel'].sizes, ceil(k.leaves['Cin'].size/tile_sizes[1]),
            # tile_fill
            *tile_sizes],
            'stride': [
            # tile_count
                10000, 5600, 10000, 100, 2,
            # tile_fill
                100, 1,
        ],
        }
        self.assert_main(None, expected_attrs, space, tile_sizes)
        space.flatten_(names=False)
        expected_attrs = dict(size=prod(orig_space.size),
                              stride=orig_space.stride[-1])
        self.assert_main(None, expected_attrs, space, tile_sizes,
                         method='flatten')

    def test_tensor(self):
        log.section('1')
        tile_sizes = 2
        sizes = [4, 2]
        t = torch.zeros(sizes)
        expected_tensor = t.detach().clone()
        # expected_tensor = torch.tensor([])
        s = Space(tensor=t, dims_from_tensor=True,)
        log(s.hastensor)
        strides = s.stride
        assert strides == [2, 1]
        expected_attrs = {'size': [4, 2],
                          'stride': [2, 1]}
        self.assert_main(None, expected_attrs, s, tile_sizes)
        test_passed = torch.equal(s.data, expected_tensor)
        if not test_passed:
            log(s, expected_tensor)

        log.section('2')
        tile_sizes = 2
        sizes = [4, 4]
        t = torch.zeros(sizes)
        expected_tensor = torch.zeros(sizes)
        # expected_tensor = torch.tensor([])
        s = Space(tensor=t, dims_from_tensor=True)
        strides = s.stride
        assert strides == [4, 1]
        expected_attrs = {'size': [4, 2, 2],
                          'stride': [4, 2, 1]}
        self.assert_main(None, expected_attrs, s, tile_sizes)
        # test_passed = torch.equal(s.data, expected_tensor)
        # test_passed = torch.equal(s.data.size, expected_tensor.size())
        # if not test_passed:
            # log(s, expected_tensor.size())


def prod(xs):
    prod = 1
    for x in xs:
        prod *= x
    return prod


def tolist(x):
    return x if isinstance(x, list) else [x]
# #
# test = SpaceTest()
# test()


if __name__ == '__main__':
    unittest.main()
