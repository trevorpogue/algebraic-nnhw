from nnhw.top import (
    AttrDict, AttrDict2, IJParam2, IntEnum, MNKParam, FIPMethod, nameof, prod,
    varname, Pool, tilepad, sign_extend, LowerStrEnum, auto, noinit, ppstr,
    PP, int_range, IO, IOs, Device, DTYPE, Mapping, tohex, IJParam,
    Cin, Cout, H, Hin, Hout, K, M, N, W, tile_count, tile_fill,
    IOItems, MappedIOTensors, IOTensors, LayerType, init, sign_extend)
from attrs import define, asdict, Factory
from torch.nn import Module as TorchLayer
from torch.nn import Module as TorchModel
import torch
from debug import log
from torch import nn, Tensor
from copy import deepcopy, copy
from torch.nn.quantized.modules import Quantize
from math import floor
from nnhw.top.device import Device


def layer_params(layer: TorchLayer) -> dict:
    torchparams = layer.__dict__
    if torchparams is None:
        torchparams = layer._modules.get('0')
        if torchparams is not None:
            torchparams = torchparams.__dict__
    if torchparams is None:
        torchparams = layer._modules
    return AttrDict(torchparams)


def model_quantstub(model: TorchLayer) -> Quantize:
    for m in model.modules():
        if isinstance(m, Quantize):
            return m


def to_int_repr(x):
    """int_repr() performs the following (or maybe floor instead of round):
    x = ((x/m_x) + z_x).round()
    x would now be in uint8 int8 repr
    """
    x = x.int_repr()
    return x


@define
class PostGemmParams(AttrDict):
    """These attrs represent the values of the value fields / parameters
    contained in an arith_u instruc.
    """
    from nnhw.top.device import Device
    device: Device
    m_val: int = noinit()
    za_bk: int = noinit()  # this also contains scaled bias
    m_shift: int = noinit()
    zc: int = noinit()
    activation: int = noinit()
    #
    mc: int = noinit()

    signed_params = ['zc', 'm_val', 'za_bk']
    signed_params = dict(zip(signed_params, signed_params))

    def from_concatted_value(self, value: Tensor):
        cout = value.size(0)
        for k in self:
            self[k] = torch.zeros_like(value)
        for i in range(cout):
            for k in self:
                self[k][i] = self.mask(k, value[i].item() >> self.offset(k))
                if self.signed_params.get(k):
                    self[k][i] = sign_extend(self[k][i].item(), self.width(k))
        return self

    def mask(self, k, value): return value & (2**self.width(k)-1)
    def width(self, k): return self.device[k.upper() + '_WIDTH']
    def offset(self, k): return self.device[k.upper() + '_OFFSET']

    def __iter__(self):
        for k in ['m_val', 'za_bk', 'm_shift', 'zc', 'activation']:
            yield k

    def items(self):
        values = [getattr(self, k) for k in self]
        return zip(self, values)

    def cout(self):
        cout = 1
        for name, value in self.items():
            if isinstance(value, torch.Tensor):
                if value.size(0) > cout:
                    cout = value.size(0)
        return cout

    def finalize(self):
        """Set all fields to 1d tensor of size `cout`."""
        cout = self.cout()
        for name, value in self.items():
            if not isinstance(value, torch.Tensor):
                self[name] = torch.tensor([value] * cout, dtype=torch.int64)
            else:
                self[name] = value.to(torch.int64)

    @property
    def value(self) -> torch.Tensor:
        """Return the concatenation of all fields as a int64."""
        cout = self.cout()
        t = torch.zeros(cout, dtype=torch.int64)
        for chan_i in range(cout):
            for key in self:
                t[chan_i] += self.shift_field(key, chan_i)
        return t

    def shift_field(self, key, chan_i=None):
        value = getattr(self, key)
        if chan_i is not None:
            value = value[chan_i]
        field = self.mask(key, value) * 2**self.offset(key)
        return field


class QuantizationParser():
    """
    Extracts the necessary quantization parameters for the device
    quantization parameter transfer instructions.
    Comments/code in this class use the following notation:
    'float' refers to data in the same repr as when not using quantization.
    'real' refers to quantized data that has the same range as
    its float repr, but with the same nof bins/nof possible values as its
    quantized or integer form.
    'int' repr refers to data in the same resolution AND range
    as the data type that computation will be done on (i.e. integers).
    'quantized' should refer to the same form as 'int', however be careful when
    discerning this word's usage because torch/tensor functions typically are
    referring to the above definition of 'real' when using the word 'quantized'
    'a', 'b', 'c' are the input, weight, output, respectively.
    'z_x' refers to zero point of data x, 'm_x' is the scaling factor for data
    x. See paper "Quantization and Training of Neural Networks for
    Efficient Integer-Arithmetic-Only Inference", which these concepts are
    from. The z_x, m_x notation is similar as in the paper except that the
    paper uses s_x instead of m_x, and 1/2/3 instead of a/b/c when referring to
    the data.
    """
    def __call__(self, device: Device, layer: TorchLayer,
                 prev_layer: TorchLayer, model: TorchModel, do_relu):
        pgps = PostGemmParams(device)
        if prev_layer:
            layer_params_ = layer_params(prev_layer)
            pgps.ma = layer_params_.scale
            pgps.za = layer_params_.zero_point
        else:
            quantstub = model_quantstub(model)
            pgps.ma = quantstub.scale.item()
            pgps.za = quantstub.zero_point.item()
        try:
            pgps.mb = layer.weight().q_per_channel_scales()
        except AttributeError:
            pgps.mb = layer.weight().q_scale()
        pgps.mc = layer.scale
        pgps.m = pgps.ma*pgps.mb/pgps.mc
        b = layer.weight()
        bias = layer.bias()
        pgps.m_val, pgps.m_shift = self.float2int(
            pgps.m, device.M_VAL_WIDTH)
        pgps.zc = int(layer.zero_point)
        pgps.za_bk = self.get_za_bk(pgps, b, bias)
        pgps.activation = int(do_relu)
        pgps.finalize()
        for k in pgps:
            v = pgps[k]
            if isinstance(v, int):
                v = torch.tensor([v], dtype=torch.int64)
            else:
                v = v.to(torch.int64)
        return pgps

    def float2int(self, x: torch.Tensor, width: int):
        f"""{x} is a 1-d Tensor"""
        m_val = torch.zeros_like(x).to(torch.int64)
        m_shift = torch.zeros_like(x).to(torch.int64)
        for i, x_ in enumerate(x):
            m_val[i], m_shift[i] = self.float2int_(x_.item(), width)
        return m_val.to(torch.int64), m_shift.to(torch.int64)

    def float2int_(self, x, width):
        n = 0
        max_ = 2**(width-1)
        while abs(x*2) < max_:
            x *= 2
            n += 1
        x = floor(x)
        return x, n

    def get_za_bk(self, qparams, b, bias):
        b = to_int_repr(b).to(torch.float64)
        za_bk = b.sum((1, 2, 3)).mul(float(qparams.za))
        za_bk = za_bk.detach().clone().to(torch.float64)
        return self.scale_bias(za_bk, qparams, bias)

    def scale_bias(self, za_bk, qparams, bias):
        from itertools import repeat
        za_bk = za_bk.detach().clone().to(
            torch.float64)
        for i, (m, mc, n, b) in enumerate(zip(
                qparams.m,
                repeat(qparams.mc),
                qparams.m_shift.to(torch.float64),
                bias.to(torch.float64)
        )):
            za_bk[i] -= (b/m/mc).round()
        return za_bk


_quantization_parser = QuantizationParser()


def parse_pgps(device: Device, layer: TorchLayer, prev_layer: TorchLayer,
               model: TorchModel, do_relu: bool):
    return _quantization_parser(device, layer, prev_layer, model, do_relu)
