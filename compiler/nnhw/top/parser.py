from nnhw.arith import Layer, NN, Program
from nnhw.top import (
    AttrDict, IJParam2, IntEnum, MNKParam, FIPMethod, nameof, prod,
    varname, Pool, tilepad, sign_extend, LowerStrEnum, auto, noinit, ppstr,
    PP, int_range, IO, IOs, Device, DTYPE, Mapping, tohex, IJParam,
    Cin, Cout, H, Hin, Hout, K, M, N, W, tile_count, tile_fill,
    IOItems, MappedIOTensors, IOTensors, LayerType, init, sign_extend,
    Device)
from attrs import define, asdict, Factory
from torch.nn import Module as TorchLayer
from torch.nn import Module as TorchModel
import torch
from debug import log
from torch import nn, Tensor
from copy import deepcopy, copy
from torch.nn.quantized.modules import Quantize
from math import floor
from nnhw.top.quantization_parser import (
    layer_params, model_quantstub, to_int_repr, parse_pgps)


@define
class Parser:
    f"""Convert a pytorch model to the internal {NN} class fed to Compiler"""
    Hin = 223
    nn: NN = noinit(NN)
    device: Device = noinit()
    prev_fused_layer: TorchLayer = noinit()
    prev_fused_newlayer: TorchLayer = noinit()

    def __call__(self, model: TorchModel, device: Device):
        self.device = device
        layer = []
        self.prev_fused_layer = None
        self.prev_fused_newlayer = None
        prev_layer = None
        i = 0
        for layer in model.modules():
            if self.supports(layer):
                self.parse_layer(layer, model)
                i += 1
                if i == 1:
                    break
        return self.nn

    def supports(self, layer):
        return self.is_fused_layer(layer) or self.is_pool_layer(layer)

    def is_conv_layer(self, layer: TorchLayer):
        from torch.nn.intrinsic.quantized.modules.conv_relu import ConvReLU2d
        from torch.nn.quantized.modules.conv import Conv2d
        return isinstance(layer, ConvReLU2d) or isinstance(layer, Conv2d)

    def is_linear_layer(self, layer: TorchLayer):
        return False
        from torch.nn.intrinsic.quantized.modules.linear_relu import LinearReLU
        return isinstance(layer, LinearReLU)

    def is_maxpool_layer(self, layer: TorchLayer):
        return isinstance(layer, nn.MaxPool2d)

    def is_avgpool_layer(self, layer: TorchLayer):
        return isinstance(layer, nn.AvgPool2d)

    def is_relu_layer(self, layer: TorchLayer):
        from torch.nn.intrinsic.quantized.modules.conv_relu import ConvReLU2d
        from torch.nn.intrinsic.quantized.modules.linear_relu import LinearReLU
        from itertools import repeat
        return isinstance(layer, ConvReLU2d) or isinstance(layer, LinearReLU)

    def is_fused_layer(self, layer: TorchLayer):
        return self.is_conv_layer(layer) or self.is_linear_layer(layer)

    def is_pool_layer(self, layer: TorchLayer):
        return self.is_maxpool_layer(layer) or self.is_avgpool_layer(layer)

    def get_params(self, layer: TorchLayer,
                   model: TorchModel):
        torchparams = layer_params(layer)
        torchparams_ = copy(torchparams)
        params = AttrDict(dict(randomize_inputs=False))
        if self.is_conv_layer(layer):
            params.kernel_size = torchparams['kernel_size'][0]
            params.stride = torchparams['stride'][0]
            params.Cin = torchparams['in_channels']
            params.Cout = torchparams['out_channels']
            params.padding = torchparams['padding'][0]
            params.Hin = self.Hin
        elif self.is_linear_layer(layer):
            params.Cin = torchparams['in_features']
            params.Cout = torchparams['out_features']
            params.type = LayerType.Linear
        elif self.is_pool_layer(layer):
            params.pool_size = torchparams['kernel_size']
            params.pool_stride = torchparams.get('stride')
        if self.is_fused_layer(layer):
            params.b = to_int_repr(layer.weight())
            bias = layer.bias()
            params.do_relu = self.is_relu_layer(layer)
            log(params.do_relu)
            params.pgp_fields = parse_pgps(
                self.device, layer, self.prev_fused_layer, model,
                params.do_relu)
        return params

    def parse_layer(self, layer: TorchLayer, model):
        params = self.get_params(layer, model)
        newlayer = None
        if (self.is_fused_layer(layer)
            or (self.is_pool_layer(layer)
                and self.prev_fused_newlayer is None)):
            newlayer = Layer(**params)
            self.prev_fused_newlayer = newlayer
            self.prev_fused_layer = layer
        elif self.is_pool_layer(layer):
            for k, v in params.items():
                setattr(self.prev_fused_newlayer, k, v)
        if newlayer:
            self.nn.append(newlayer)


_parser = Parser()


def parse(model: TorchModel, device: Device):
    return _parser(model, device)
