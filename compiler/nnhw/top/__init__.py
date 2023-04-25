"""Simple general utilities and types (advanced utilities are in top.utils)"""

import copy
import pathlib as path
import typing as typ
from typing import List, Dict, NewType, Any
from collections import OrderedDict, UserDict, UserString, namedtuple
from copy import deepcopy
from enum import Enum, auto
import torch
from torch import Tensor
import typer
# exports:
from nnhw.top.utils import args2attrs, tolist
from varname import nameof as nameof  # example: name(self.x) returns 'x'
from attrs import define, asdict, field, Factory
from itertools import chain
import numpy as np
from math import ceil
import math


uint8 = typ.NewType('uint8', int)
uint24 = typ.NewType('uint24', int)
uint32 = typ.NewType('uint32', int)
# Auto = typ.NewType('Auto', int)


DTYPE = torch.int64


class StrEnum(str, Enum):
    """Enum with values optionally set to string form of the member names by
    setting their value = auto().
    """
    def _generate_next_value_(name, start, count, last_values):
        return name


class LowerStrEnum(str, Enum):
    """StrEnum with values optionally set to lower case string form of member
    names.
    """
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()


class IntEnum(int, Enum):
    """Enum with member values optionally set to auto incrementing ints
    starting at 0.
    """
    def _generate_next_value_(name, start, count, last_values):
        return count


class Op(LowerStrEnum):
    BOARD = auto()
    TEST_QUICK = auto()
    TEST_AFTER_COMPILE = auto()
    RUN = auto()
    TEST = auto()
    SIM1 = auto()
    SIM2 = auto()
    SIM3 = auto()
    SIM4 = auto()


class IO(LowerStrEnum):
    """Individual IO keys for the various ios probed in the Arith unit.
    Getting them from here avoids making magic strings."""
    A = auto()
    B = auto()
    POST_GEMM_PARAMS = auto()
    GEMM = auto()
    QUANTIZATION = auto()
    POOL_PADDING = auto()
    POOLING = auto()
    C = auto()
    RESULT = auto()


class IOs:
    """Groups of IO keys from the various ios probed in the Arith unit."""
    # CONV = [IO.A, IO.B, IO.POST_GEMM_PARAMS, IO.GEMM, self.]
    # CONV_OUTPUTS = [IO.GEMM, IO.QUANTIZATION]
    INPUTS = [IO.A, IO.B, IO.POST_GEMM_PARAMS]
    OUTPUTS = [IO.GEMM, IO.QUANTIZATION,
               IO.POOL_PADDING, IO.POOLING, IO.C, IO.RESULT]
    POST_CONV = [IO.POOL_PADDING, IO.POOLING, IO.C]
    ALL = list(IO.__members__.values())


def read_verilog_param(param, filepath: str, matchkey: str = r'(.*)',
                       ismacro=False):
    import re
    from utils import run
    from debug import log
    log_en = False
    pattern = rf'^( *[^/]+\w+ +)*\b{param} ?=? ?.* {matchkey}[,;]'
    if ismacro:
        pattern = rf'^ *[^/]*(`define) *{param} *(.*)'
    v = run(f"rg '{pattern}' {filepath}", ignore_errors=True)
    # log(repr(pattern))
    if v is None:
        return
    if v == '':
        return
    v = v.splitlines()[0]
    # log(repr(v))
    v = re.match(pattern, v).group(2)
    # log(repr(v))
    lshift_match = re.sub(r'[0-9]<<([0-9]*)', r'\1', v)
    if lshift_match != v:
        v = 2**int(lshift_match)
    elif re.search('TRUE', v):
        v = True
    elif re.search('FALSE', v):
        v = False
    elif isinstance(v, str) and (v[0] + v[-1] == '""'):
        v = v[1:-1]
    # log(repr(v))
    try:
        v = eval(v)
        # log(repr(v))
    except Exception:
        pass
    return v


class Path(StrEnum):
    """System file paths for important directories in the nnhw repo."""
    SRC = '/'.join(str(path.Path(__file__).parent.resolve()).split('/')[:-1])
    NNHW = '/'.join(SRC.split('/')[:-2])
    IP = NNHW + '/ip'
    RTL = NNHW + '/rtl'
    TESTS = NNHW + '/tests'
    SIM = NNHW + '/sim'
    SYNTH = NNHW + '/synth'
    BIN = NNHW + '/bin'
    INSTRUC_CACHE = NNHW + '/instruc_cache'


class QuantMode(LowerStrEnum):
    OFF = ''
    STATIC = auto()
    DYNAMIC = auto()


class Level(IntEnum):
    """Use this, for example, to set test or debug level instensity."""
    OFF = auto()
    LOW = auto()
    MED = auto()
    HIGH = auto()
    MAX = auto()


class AttrDict4(dict):
    """
    Have ability to access values like this:
        attr_dict['x'] = 1
    OR
        attr_dict.x = 1
    instead of only like this:
        attr_dict['x'] = 1
    """

    def __setattr__(self, key, value):
        super().__setitem__(key, value)
        super().__setattr__(key, value)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().__setattr__(key, value)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return ['']
        #     raise AttributeError

    def __str__(self):
        import sections
        s = f'{sections(**self)}'
        # if s[0:1] == '\n\n':
            # s = s[1:]
        return s


class AttrDict3(dict):
    """
    Have ability to access values like this:
        attr_dict['x'] = 1
    OR
        attr_dict.x = 1
    instead of only like this:
        attr_dict['x'] = 1
    """

    def __setattr__(self, key, value):
        super().__setitem__(key, value)
        super().__setattr__(key, value)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().__setattr__(key, value)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None
        #     raise AttributeError

    def __str__(self):
        import sections
        s = f'{sections(**self)}'
        # if s[0:1] == '\n\n':
            # s = s[1:]
        return s


class AttrDict(dict):
    """
    Have ability to access values like this:
        attr_dict['x'] = 1
    OR
        attr_dict.x = 1
    instead of only like this:
        attr_dict['x'] = 1
    """

    def __setattr__(self, key, value):
        super().__setitem__(key, value)
        super().__setattr__(key, value)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().__setattr__(key, value)

    # def __getattr__(self, key):
    #     try:
    #         return self[key]
    #     except KeyError:
    #         return None
        #     raise AttributeError

    def __str__(self):
        import sections
        s = f'{sections(**self)}'
        # if s[0:1] == '\n\n':
            # s = s[1:]
        return s


class AttrDict2(dict):
    """
    Have ability to access values like this:
        attr_dict['x'] = 1
    OR
        attr_dict.x = 1
    instead of only like this:
        attr_dict['x'] = 1
    """

    # def __init__(self, *args, **kwds): super().__init__(*args, **kwds)
    def setattr(self, key, value): super().__setattr__(key, value)
    def getattr(self, key): return super().__getattribute__(key)
    def __setattr__(self, key, value): self[key] = value

    def __str__(self):
        # return f'AttrDict({ppstr(dict(self))[:-1]})\n'
        import sections
        s = f'{sections(**self)}'
        # if s[0:1] == '\n\n':
        #     s = s[1:]
        # if s[-2:] == '\n\n':
        #     s = s[:-1]
        return s
    # def __str__(self): return super().__str__(dict(self))

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            try:
                return self.__getitem__(key.__name__)
            except AttributeError:
                raise KeyError

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError

    def copy(self):
        cpy = self.__class__()
        for k, v in self.items():
            cpy[k] = v
        for k, v in self.__dict__.items():
            cpy[k] = v
        return cpy

    def set_values_to_keys(self):
        for k in self:
            setattr(self, k, k)


class IJParam2(AttrDict):
    def __init__(self, i=0, j=0):
        self.i: int = i
        self.j: int = j

    def __iter__(self):
        for v in self.values():
            yield v


class ValueDict(AttrDict):
    def __iter__(self):
        for v in self.values():
            yield v


class FIPMethod(StrEnum):
    BASELINE = auto()
    FIP = auto()
    FFIP = auto()


def ppstr(obj):
    """Pretty printable string."""
    s = StrStream('')
    s += 'a'
    from rich import print as rpp

    # from pprintpp import pprint as pp
    rpp(obj, file=s,
        # expand_all=True
        )
    # pp(self, stream=s)
    return str(s)[1:]


def tensor_factory():
    return torch.tensor([])


# def Factory(cls, *args):
    # from attrs import Factory as Factory_
    # return Factory_(cls)


def attr(init, default=None, *factory_args, **factory_kwds):
    if callable(default):
        return field(init=init, default=Factory(
            default, *factory_args, **factory_kwds))
    else:
        return field(init=init, default=default)



def fromself(default=None, *args, **kwds):
    return attr(False, default, *args, takes_self=True, **kwds)

def noinit(default=None, *args, **kwds):
    return attr(False, default, *args, **kwds)

def init(default=None, *args, **kwds):
    return attr(True, default, *args, **kwds)


from nnhw.top.device import Device


class Pool(IntEnum):
    MAXPOOL2D = auto()
    AVGPOOL2D = auto()


class Pkg(IntEnum):
    MEM_CLK_DIV = 2


class TileDim(StrEnum):
    tile_fill = auto()
    tile_count = auto()


class Dim(StrEnum):
    Cin = auto()
    Cout = auto()
    H = auto()
    W = auto()
    Kernel = auto()
    K = auto()
    M = auto()
    N = auto()
    M0 = auto()
    M1 = auto()
    N0 = auto()
    N1 = auto()
    I = auto()
    J = auto()


tile_count, tile_fill = TileDim.tile_count, TileDim.tile_fill
M, N, K = Dim.M, Dim.N, Dim.K
Cin, Cout, H, W, Kernel = Dim.Cin, Dim.Cout, Dim.H, Dim.W, Dim.Kernel
Hin = 'Hin'
Hout = 'Hout'


class Data(LowerStrEnum):
    LAYERIO = auto()
    WEIGHT = auto()


class Mapping(LowerStrEnum):
    BASE = auto()
    HOST_GEMM = auto()
    DEVICE = auto()
    TB_GEMM = auto()
    DATA_TRANSFER = auto()
    TORCH = auto()


class Env(StrEnum):
    TESTLIST = auto()


def tilepad(size, tile_size):
    """Get the size to pad onto a dimension of size `size`
    in order to make it have a final size divisible by `tile_size`."""
    return ((tile_size - (size % tile_size)) % tile_size)


def test_paths():
    _2dirs_above_hostsrc = '/'.join(Path.SRC.split('/')[:-2])
    assert _2dirs_above_hostsrc == Path.NNHW, print(
        Path.SRC, Path.NNHW, _2dirs_above_hostsrc)


@define
class Dec2Hex:
    nbits: int = 8

    def __call__(self, digit, nbits=None):
        if nbits is None:
            nbits = self.nbits
        digit = ((digit + (1 << nbits)) % (1 << nbits))
        digit = f"0x{digit:02x}"
        if digit[0] == '-':
            digit = f'-{digit[3:]}'
        else:
            digit = f'{digit[2:]}'
        return digit


def _tohex1d(observed: torch.Tensor, expected: torch.Tensor = None, nbits=8,
                 dont_compare_negative_ones=False):
    if expected is None:
        expected = observed
    passed = True
    s = ''
    dont_compare = dont_compare_negative_ones and (
        prod(observed) == -1)
    eq = torch.equal(observed, expected) or dont_compare
    dec2hex = Dec2Hex(nbits)
    formatter = {'all': dec2hex}
    dec2hex.nbits = nbits
    observed = np.array2string(np.asarray(observed), formatter=formatter)
    expected = np.array2string(np.asarray(expected), formatter=formatter)
    if eq:
        row = observed
    else:
        passed = False
        row = (f'{observed}x {expected}c')
        if len(row) > 56:
            row = (f'{observed}x <\n{expected}c')
    s += row + '\n'
    return s, passed


def _tohex(observed: torch.Tensor, expected: torch.Tensor, nbits=8,
                 dont_compare_negative_ones=False):
    passed = True
    if len(observed.size()) == 1:
        dim, eq = _tohex1d(observed, expected, nbits,
                                dont_compare_negative_ones)
        return dim, eq
    s = ''
    for i, _ in enumerate(observed):
        dim, eq = _tohex(observed[i], expected[i], nbits,
                                dont_compare_negative_ones)
        s += dim
    s = '[' + s[:-1] + ']'
    s_ = ''
    for j, dim in enumerate(s.split('\n')):
        s_ += ('' if j == 0 else ' ') + dim + '\n'
    s = s_
    return s, passed


def tohex(observed: torch.Tensor, expected: torch.Tensor = None, nbits=None,
                 dont_compare_negative_ones=False, return_if_eq=False):
    if expected is None:
        expected = observed
    if not isinstance(observed, Tensor):
        observed = torch.tensor(list(observed))
    if not isinstance(expected, Tensor):
        expected = torch.tensor(list(observed))
    import torch
    if observed.dtype in [torch.float32, torch.float64]:
        return expected
    if nbits is None:
        e = expected
        if e.dtype in [torch.uint8, torch.int8]:
            nbits = 8
        elif e.dtype in [torch.int32]:
            nbits = 32
        elif e.dtype in [torch.int64]:
            nbits = 64
        else:
            nbits = 8
    if list(observed.size()) != list(expected.size()):
        s = f"observed/expected dims don't match:\n"
        s += f'observed.size(): {observed.size()}\n'
        s += f'expected.size(): {expected.size()}\n\n'
        s += f'observed:\n{tohex(observed)}\n\n'
        s += f'expected:\n{tohex(expected)}\n'
        s = s[:-1]
        passed = False
    else:
        if len(observed.size()) > 1:
            s, passed = _tohex(observed, expected, nbits,
                                dont_compare_negative_ones)
        else:
            s, passed = _tohex1d(observed, expected, nbits,
                              dont_compare_negative_ones)
        # s = '\n' + s + '\n'
        s = s[:-1]
    if return_if_eq:
        return s, passed
    else:
        return s


test_paths()


testlevel = Level.OFF


class Weight(torch.Tensor):
    """Layer's weight data."""
    pass


class Layerio(torch.Tensor):
    """Layer's input or output data."""
    pass


def varname(frame=1):
    """Return name of variable/attr being assigned on the LHS of this
    function's caller statement. Reduces magic string usage and makes
    refactoring easier and static analysis tool checking better. Example usage:
    >>> d = {}
    >>> self.x = d.setdefault(varname(), 'default_value')
    >>> print(d[name(self.x)])  # i.e. print(d['x'])
    'default_value'
    """
    from varname import varname as _varname
    return _varname(frame=frame)


def prod(list_):
    """ Return product of elements in list.

    Example:
    >>> product([2, 4])
    8
    """
    product = 1
    for x in list_:
        product *= x
    return product


def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)


def int_range(width, signed: bool):
    if signed:
        return (-2 ** (width-1), 2 ** (width-1) - 1)
    else:
        return (0, 2 ** (width))


def snake2cammel(snake_str: str) -> str:
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', '_', snake_str).lower()


class PP:
    def __str__(self):
        try:
            return ppstr(self.__dict__)
        except Exception:
            return ppstr(asdict(self))


@define
class IOTensors(AttrDict):
    a: Tensor = Factory(tensor_factory)
    b: Tensor = Factory(tensor_factory)
    post_gemm_params: Tensor = Factory(tensor_factory)
    gemm: Tensor = Factory(tensor_factory)
    quantization: Tensor = Factory(tensor_factory)
    pool_padding: Tensor = Factory(tensor_factory)
    pooling: Tensor = Factory(tensor_factory)
    c: Tensor = Factory(tensor_factory)
    result: Tensor = Factory(tensor_factory)

    def __str__(self):
        import sections
        # obj = sections(*IOs.ALL)
        obj = AttrDict()
        for io in IOs.ALL:
            obj[io] = AttrDict()
        # for io in IOs.ALL:
            obj[io].size = tuple(self[io].size())
            obj[io].stride = tuple(self[io].stride())
        return str(obj)


@define
class IOItems(AttrDict):
    a: Any = Factory(AttrDict)
    b: Any = Factory(AttrDict)
    post_gemm_params: Any = Factory(AttrDict)
    gemm: Any = Factory(AttrDict)
    quantization: Any = Factory(AttrDict)
    pool_padding: Any = Factory(AttrDict)
    pooling: Any = Factory(AttrDict)
    c: Any = Factory(AttrDict)
    result: Any = Factory(AttrDict)
    def __str__(self, ): return AttrDict.__str__(self)


@define
class MappedIOTensors(AttrDict):
    torch: IOTensors = Factory(IOTensors)
    device: IOTensors = Factory(IOTensors)

    def __str__(self):
        result = ''
        for k in asdict(self, recurse=False):
            result += f'{k}: {self[k]}'
        return result


@define
class IOTensors(AttrDict):
    a: Tensor = Factory(tensor_factory)
    b: Tensor = Factory(tensor_factory)
    post_gemm_params: Tensor = Factory(tensor_factory)
    gemm: Tensor = Factory(tensor_factory)
    quantization: Tensor = Factory(tensor_factory)
    pool_padding: Tensor = Factory(tensor_factory)
    pooling: Tensor = Factory(tensor_factory)
    c: Tensor = Factory(tensor_factory)
    result: Tensor = Factory(tensor_factory)

    def __str__(self):
        import sections
        # obj = sections(*IOs.ALL)
        obj = AttrDict()
        for io in IOs.ALL:
            obj[io] = AttrDict()
        # for io in IOs.ALL:
            obj[io].size = tuple(self[io].size())
            obj[io].stride = tuple(self[io].stride())
        return str(obj)


class Base():
    """Useful features for any subclass to inherit.
    """

    # def __init__(self, *args, **kwds): super().__init__(*args, **kwds)
    # @property
    # def __dict__(self): return self
    # def __setattr__(self, name, value): self[name] = value

    # def __getattr__(self, name):
    #     try:
    #         return self[name]
    #     except KeyError:
    #         raise AttributeError

    def key(self, attr_value):
        """Return key of self.attribute `attr` (the value).
        Use this instead of raw strings for attribute references to make
        refactoring easier.
        """
        key = None
        for k, v in self.__dict__.items():
            if v is attr_value:
                key = k
                break
        return key


class StrStream(UserString, typ.IO):
    """Used like a file obj but output is passed to a string instead.
    i.e. this is used for 'printing to a string' instead of an stream or file.
    """

    def write(self, s):
        self.data += s


class DeepCopyableTensorValues:
    def __deepcopy__(self, memo):
        """Tensors don't support deepcopy, so need to override deepcopy
        to accommodate this."""
        try:
            cpy = self.__class__(self.getattr('name'))
        except AttributeError or TypeError:
            cpy = self.__class__()
        memo[id(self)] = cpy
        for k, v in self.items():
            if isinstance(v, torch.Tensor):
                # setattr(cpy, k, v.detach().clone())
                setattr(cpy, k, v)
            else:
                setattr(cpy, k, deepcopy(v, memo))
        for k, v in self.__dict__.items():
            if isinstance(v, torch.Tensor):
                # cpy.setattr(k, v.detach().clone())
                cpy.setattr(k, v)
            else:
                cpy.setattr(k, deepcopy(v, memo))
        return cpy

    def printable_copy(self):
        """Suppress tensor attributes in str representation for pretty printing
        """
        # cpy = self.copy()
        cpy = copy.copy(self)
        try:
            cpy['name'] = self.name
            cpy.move_to_end('name', False)
            cpy = dict(cpy)
        except AttributeError or AttributeError:
            pass
        for k, v in cpy.items():
            if isinstance(v, torch.Tensor):
                cpy[k] = f'size: {v.size()}, stride: {v.stride()}'
            try:
                cpy[k] = v.printable_copy()
            except AttributeError:
                pass
        return cpy

    def __str__(self): return ppstr(self.printable_copy())
    def __repr__(self): return ppstr(self.printable_copy())


def not_inplace(method):
    """Convert an inplace method to an non-inpace one.
    See bottom of Space doctring for definition of inplace."""

    def wrapper(self, *args, **kwds):
        self = deepcopy(self)
        return method(self, *args, **kwds)
    return wrapper


IJParam = namedtuple('IJParam', 'i, j', defaults=[0, 0])


class MNKParam:
    def __init__(self, mn=0, nm=0, k=0):
        self.mn: int = mn
        self.nm: int = nm
        self.k: int = k
        pass

    @property
    def aslist(self):
        return [self.mn, self.nm, self.k]

    def mn_swapped(self):
        self = deepcopy(self)
        prev_mn = self.mn
        self.mn = self.nm
        self.nm = prev_mn
        return self

    def k_nm_swapped(self):
        self = deepcopy(self)
        prev_k = self.k
        self.k = self.nm
        self.nm = prev_k
        return self

    def __repr__(self): return str(self)
    def __str__(self): return str(self.aslist)


class Radix(LowerStrEnum):
    HEX = auto()
    DEC = auto()


class LayerType(LowerStrEnum):
    Conv2d = auto()
    Linear = auto()


def print_begin_end_async(method):
    async def wrapper(self, *args, **kwds):
        from debug import log
        logkwds = dict(value_only=True)
        # log(f'{method.__name__} begin', **logkwds)
        result = await method(self, *args, **kwds)
        # log(f'{method.__name__} end', **logkwds)
        return result
    return wrapper


def print_begin_end(method):
    def wrapper(self, *args, **kwds):
        from debug import log
        logkwds = dict(value_only=True)
        # log(f'{method.__name__} begin', **logkwds)
        result = method(self, *args, **kwds)
        # log(f'{method.__name__} end', **logkwds)
        return result
    return wrapper


class Levels:
    def __getattr__(self, key): return Level.OFF


def clog2(n): return ceil(math.log(n, 2))


# exports:
# from nnhw.top.cfg import Config
