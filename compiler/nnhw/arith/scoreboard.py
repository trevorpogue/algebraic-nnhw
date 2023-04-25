from nnhw.top import (
    AttrDict, IJParam2, IntEnum, MNKParam, FIPMethod, nameof, prod,
    varname, Pool, tilepad, sign_extend, LowerStrEnum, auto, noinit, ppstr,
    PP, int_range, IO, IOs, Device, DTYPE, Mapping, tohex,
    Cin, Cout, H, Hin, Hout, K, M, N, W, tile_count, tile_fill, tilepad,
    IOItems, MappedIOTensors, Level, init, Radix)
from debug import log
import torch
from torch import nn
from math import ceil
from attrs import define, field, asdict
from attrs import Factory
import typing as typ
from typing import List, Any, Dict
from copy import copy, deepcopy
from dataclasses import dataclass
from random import randrange
from nnhw.mem import Mem
from nnhw import arith
from nnhw.top.cfg import config


@define
class PostGemmScoreboard():
    device: Device
    layer: 'arith.Layer' = None

    def quant_add_and_scale(self, c=None):
        get_c = c is not None
        data = AttrDict()
        if get_c:
            c = c.detach().clone()
            c = c.squeeze(0)
            data.res_za_bk = torch.zeros_like(c)
            data.c1 = torch.zeros_like(c)
            data.a0 = torch.zeros_like(c)
            data.a1 = torch.zeros_like(c)
        Cout_ = self.layer.tile_counts[N] * self.layer.tile_sizes[N]
        size = (Cout_,)
        for chan_i in range(Cout_):
            t = self._quant_add_and_scale(data, c, chan_i)
            if get_c:
                c[chan_i] = t
        return c.unsqueeze(0)

    def _quant_add_and_scale(self, data, c, chan_i):
        get_c = c is not None
        ci = chan_i
        d = self.device
        p = self.layer.pgp_fields
        if not get_c:
            return
        width_t = torch.tensor([self.device.WIDTHS[IO.A]])
        width = self.device.WIDTHS[IO.A]
        c[ci] -= p.za_bk[ci].to(torch.int64)
        data.res_za_bk[ci] = c[ci].detach().clone()
        c[ci] = self.rshift(
            c[ci], p.m_shift[ci]-width)
        c[ci] = sign_extend(c[ci] & ((2**(width+3))-1),
                            width+3)
        c[ci].mul_(p.m_val[ci].to(torch.int64))
        c[ci] = self.rshift(c[ci], width_t)
        width = self.device.WIDTHS[IO.A] + 1
        c[ci] = sign_extend(c[ci] & ((2**width)-1), width)
        data.c1[ci] = c[ci].detach().clone()
        c[ci] &= 511
        data.a0[ci] = c[ci].detach().clone()
        c[ci] = sign_extend(c[ci], self.device.WIDTHS[IO.A] + 1)
        if p.activation[ci]:
            c[ci] = nn.ReLU()(c[ci])
        data.a1[ci] = sign_extend(c[ci].detach().clone(), 9)
        c[ci] = (c[ci] + p.zc[ci]) & 255
        return c[ci]

    def rshift(self, t, c):
        div_val, mul_val = None, None
        if c.item() >= 0:
            div_val = torch.tensor([2]).to(torch.int64)**c.to(torch.int64)
        else:
            mul_val = torch.tensor([2]).to(torch.int64)**(c.to(torch.int64)*-1)
        if div_val is not None:
            return t.div(div_val, rounding_mode='floor').to(torch.int64)
        else:
            return t.mul(mul_val).to(torch.int64)


def str_pad(s, final_len, pad=' '):
    cur_len = max(map(len, s.split('\n')))
    return pad * (final_len - cur_len)


def pad_str(s, final_len, left=True, pad=' '):
    if left:
        return str_pad(s, final_len, pad) + s
    else:
        return s + str_pad(s, final_len, pad)


@define
class ScoreItem(AttrDict):
    value: Any = 0
    m_tile_i: Any = 0
    index0: Any = 0
    index1: Any = 0
    index_location0: Any = 0
    index_location1: Any = 0

    def __call__(self, max_lens: 'ScoreItem'):
        s = ''
        suffixes = [' [', ' m [', ', ', ']i [', ', ', ']%']
        for i, (k, v) in enumerate(self.items()):
            if k != ScoreItem.m_tile_i.__name__:
                s += f'{pad_str(v, max_lens[k], i)}{suffixes[i]}'
        return s + '\n'


@define
class ScoreVisualizer(AttrDict):
    layer: 'arith.Layer'
    mapping: Mapping
    io: IO
    observed: torch.Tensor = noinit()
    expected: torch.Tensor = noinit()
    total_dividers: int = noinit(0)
    results: Dict[str, ScoreItem] = init(dict)
    radix: Radix = Radix.HEX

    def _value_i(self, i, x, indexes, offset):
        if self.radix is Radix.HEX:
            return x[indexes]
        else:
            return x[indexes].tolist()

    def value_i(self, i, indexes, offset):
        item = ScoreItem()
        if self.radix is Radix.HEX:
            observed, expected = None, None
            if config.show_incorrect_ios:
                observed = self._value_i(i, self.observed, indexes, offset)
                expected = self._value_i(i, self.expected, indexes, offset)
            else:
                observed = self._value_i(i, self.expected, indexes, offset)
            item.value = tohex(observed, expected,
                               nbits=self.layer.device.WIDTHS[self.io])
        else:
            item.value = (
                f'{self._value_i(i, self.observed, indexes, offset)} '
                f'{self._value_i(i, self.expected, indexes, offset)}')
        item.index0, item.index1 = self.printable_indexes(indexes)
        item.index_location0, item.index_location1 = self.index_location(
            i, indexes)
        item.m_tile_i = str(int(int(item.index1) / self.layer.tile_sizes[M]))
        return item

    def index_location(self, i, indexes):
        denom = torch.tensor(self.expected.size()[:-1]) - 1
        for j, x in enumerate(denom):
            # avoid divide by 0 error when dim has size of 1
            if not x:
                indexes[j], denom[j] = 1, 1
        indexes = torch.tensor(indexes)
        result = (indexes / denom)
        result = (result * 1000).tolist()
        # result = list(map(round, result))
        for i, v in enumerate(result):
            result[i] = round(v / 10)
        return str(result[0]), str(result[1])

    def printable_indexes(self, indexes, astuple=True):
        result = torch.tensor(indexes).tolist()
        return str(result[0]), str(result[1])

    def parse_indexes(self, indexes, i, offset):
        indexes = list(indexes[i].clone())
        if offset == 0:
            return indexes
        if indexes[-1] + offset < 0:
            indexes[0] -= 1
            indexes[-1] = self.expected.size(1) + offset
        elif indexes[-1] + offset >= self.expected.size(1):
            indexes[0] += 1
            indexes[-1] = offset - 1
        else:
            indexes[-1] += offset
        return indexes

    def offset_is_valid(self, indexes, i, offset):
        result = False
        try:
            indexes = self.parse_indexes(indexes, i, offset)
            result = indexes[-1] >= 0
            result = result and indexes[0] >= 0
            self._value_i(i, self.expected, indexes, offset)
        except:
            result = False
        return result

    def show(self, indexes, i, offset=0):
        if not self.offset_is_valid(indexes, i, offset):
            return
        indexes = self.parse_indexes(indexes, i, offset)
        offset_msg = ''
        if offset:
            offset_msg = offset if offset < 1 else f'+{offset}'
        k = f'{self.printable_indexes(indexes)}'
        self.results[k] = self.value_i(i, indexes, offset)

    def __call__(self): return str(self)

    def add_divider(self, indexes=None):
        if (indexes is not None) and (not prod(indexes.size())):
            return
        divider = '#--------------------\n'
        self[f'divider{self.total_dividers}'] = divider
        self.total_dividers += 1

    def match_data(
            self, data_a_indexes, data_a, data2match,
            match_correct_values=True):
        kwds = dict(value_only=True)
        log('matching:', **kwds)
        for i in range(4):
            if i >= data_a_indexes.size(0):
                continue
            indexes = data_a_indexes[i]
            value = data_a[list(indexes)]
            matches = (data2match == value).nonzero().tolist()
            if len(matches) > config.max_printable_io_size/2:
                matches = (matches[:int(config.max_printable_io_size/2)-4]
                           + ['...'] + matches[:-4])
            log(f'{nameof(matches)} {i}: {matches}',
                **kwds)

    def __str__(self):
        self.total_dividers = 0
        self.observed = self.layer.observed[self.mapping][self.io]
        self.expected = self.layer.expected[self.mapping][self.io]
        obs = self.observed.detach().clone().contiguous()
        exp = self.expected.detach().clone().contiguous()
        c_exp = self.layer.expected.device.c.detach().clone().contiguous()
        # only compare whole rows at a time by making a unique id per row
        # based on row values # (not guaranteed to work but expecteed to
        # for almost all values):
        obs = obs.prod(2) - obs.sum(2)
        exp = exp.prod(2) - exp.sum(2)
        c_exp = c_exp.prod(2) - c_exp.sum(2)
        correct_i = (exp == obs).nonzero()
        incorrect_i = (exp != obs).nonzero()
        if self.layer.config.from_torch_model:
            error_threshold = 1
            correct_i = ((exp - obs).abs() <= error_threshold)
            incorrect_i = ((exp - obs).abs() > error_threshold)
        all_i = (exp == exp).nonzero()
        # if config.debuglevels.scoreboard > Level.LOW:
            # self.match_data(incorrect_i, obs, c_exp)
        self.show(all_i, 0)
        self.show(all_i, 1)
        self.show(all_i, -1)
        indexes2show = 8**config.debuglevels.scoreboard
        for indexes in [correct_i, incorrect_i]:
            for i in [0, -1]:
                for offset in range(-3, indexes2show):
                    # if indexes is correct_i and offset >= 4:
                        # continue
                    self.show(indexes, i, offset)
        results = {}
        max_lens = ScoreItem()
        for item in self.results.values():
            for k, v in item.items():
                if len(v) > max_lens[k]:
                    max_lens[k] = max(map(len, v.split('\n')))
        for k, v in self.results.items():
            new_key = (f'{pad_str(v.index0, max_lens.index0, True, "0")} '
                       f'{pad_str(v.index1, max_lens.index1, True, "0")}')
            results[new_key] = self.results[k]
        self.results = dict(sorted(results.items()))
        s = ''
        for k, v in self.results.items():
            s += f'{v(max_lens)}'
        return s[:-1]


def score_visualization(layer: 'arith.Layer', mapping: Mapping, io: IO):
    return ScoreVisualizer(layer, mapping, io)()


class LayerScoreboard(PostGemmScoreboard):
    def __call__(
            self,
            layer: 'arith.Layer',
            mapping=Mapping.DEVICE,
            # output_ios_mapping=Mapping.TORCH,
            # use_errors_as_inputs=True,
            use_errors_as_inputs=False,
    ):
        from nnhw.arith import Layer, NN
        layer: Layer = layer
        ios = layer.ios
        if ios != list(IOs.ALL) and ios != list(IOs.ALL)[:-1]:
            use_errors_as_inputs = False
        # #####################################
        # get missing device mapped tensors
        observed, expected = layer.observed, layer.expected
        for io in IOs.INPUTS:
            if io not in config.ios2score:
                continue
            if io not in layer.ios:
                continue
            #     self.map_inputs_device2torch(layer.mem, layer.observed)
            # not this:
            observed.torch[io] = expected.torch[io]
        from nnhw.arith import ParaTile
        for io in IOs.OUTPUTS:
            if io not in config.ios2score:
                continue
            if io not in layer.ios:
                continue
            observed.torch[io] = self.map_output_device2torch(
                observed.device[io], layer.HWs[io])
        self.compute_expected_outputs(layer, use_errors_as_inputs)
        observed, expected = layer.observed[mapping], layer.expected[mapping]
        assertions = IOItems()
        for io in IOs.ALL:
            assertions[io] = True
        for io in ios:
            observed[io] = observed[io].to(self.device.dtypes[io])
            expected[io] = expected[io].to(self.device.dtypes[io])
            assertions[io] = torch.equal(observed[io], expected[io])
            if layer.config.from_torch_model:
                error_score = (((observed[io] - expected[io]).abs() > 1).sum()
                               / prod(observed[io].size()) * 100)
                error_threshold = 20
                assertions[io] = error_score < error_threshold
        msg = f''
        header = '##' + '-' * 77 + '\n'
        nn: NN = layer.parent
        for io in ios:
            # if io not in config.ios2show:
                # continue
            if not config.debuglevels.scoreboard:
                continue
            for mapping in [mapping]:
                observed, expected = layer.observed[mapping], layer.expected[
                    mapping]
                size = prod(expected[io].size())
                incorrect_count = torch.sum(
                    observed[io] != expected[io]).item()
                is_correct_str = (
                    f'Passed' if assertions[io] else f'Error'
                    + f' | {incorrect_count} / {size}'
                    + f' ({round(incorrect_count / size * 10000)/100} %)'
                    + f' errors')
                io_msg = f'{io} {layer.position} {is_correct_str}\n'
                hextensor = self.score_visualization(layer, mapping, io)
                if (config.debuglevels.scoreboard >= Level.MED
                    or (io == IO.RESULT)
                    or (io == IO.C and layer.islast and (IO.RESULT not in ios))
                    or not assertions[io]
                    or io in config.ios2show
                    ):
                    sec = layer.section
                    posns = nn.first_layer_positions_for_each_section
                    if sec < len(posns)-1:
                        outof = posns[sec+1] - posns[sec]
                    else:
                        outof = len(nn) - posns[sec]
                    pos = (layer.position - posns[sec])
                    sec_str = f'{layer.type} {pos+1}/{outof}'
                    io_msg = (
                        f'{io} {sec_str} layer {layer.position+1}/{len(nn)} '
                        f'batch {nn.batch_pos+1}/{nn[0].batch_size} '
                        f'{is_correct_str}:\n{hextensor}\n{io} '
                        f'{is_correct_str}\n'
                    )
                    if not assertions[io]:
                        io_msg = f'\n{header}{io_msg}{header}'
                msg += io_msg
        if msg and msg[-1] == '\n':
            msg = msg[:-1]
        if config.debuglevels.scoreboard <= Level.LOW:
            if layer.position:
                msg = ''
        passed = all(assertions.values())
        return msg, passed

    def score_visualization(self, layer, mapping, io):
        observed = layer.observed[mapping][io]
        expected = layer.expected[mapping][io]
        debug_level = config.debuglevels.scoreboard
        if debug_level < Level.HIGH and mapping == Mapping.TORCH:
            return ''
        if max(prod(observed.size()), prod(expected.size())
               ) > config.max_printable_io_size and (
               debug_level > Level.MED):
            debug_level = Level.MED
        # if config.in_sim:
            # debug_level = Level.HIGH
        # elif debug_level < Level.HIGH and mapping == Mapping.DEVICE:
        return score_visualization(layer, mapping, io)
        # else:
        #     return tohex(
        #         observed, expected,
        #         self.device.WIDTHS[io],
        #     )

    def compute_expected_outputs(
            self,
            layer: 'arith.Layer',
            use_errors_as_inputs=False,
    ):
        ios = layer.expected
        observed, expected = layer.observed.torch, layer.expected.torch
        ios = (observed if use_errors_as_inputs else expected)
        if layer.do_conv:
            expected.gemm = self.compute_gemm(ios.a, ios.b)
            expected.quantization = self.quant_add_and_scale(ios.gemm)
        pool_padder = torch.nn.ZeroPad2d(layer.pool_padding)
        c_padder = torch.nn.ZeroPad2d(layer.c_padding)
        expected.pool_padding = pool_padder(
            ios.quantization if layer.do_conv else ios.a)
        expected.pooling = self.pool(ios.pool_padding)
        if not config.from_torch_model or not layer.islast:
            expected.c = c_padder(ios.pooling)
            expected.result = expected.c.clone()
        ios = AttrDict()
        from nnhw.arith import ParaTile
        for io in IOs.OUTPUTS:
            ios = expected
            layer.expected.device[io] = self.map_output_torch2device(ios[io])
        kwds = dict(show_context=False,
                    log_en=layer.config.debuglevels.scoreboard)

    def compute_gemm(self, a, b):
        data = self.conv2d(a, b)
        return self._process_mxu(data)

    def conv2d(self, a, b):
        if len(a.size()) == 3:
            a = a.unsqueeze(0)
        if len(b.size()) == 3:
            b = b.unsqueeze(0)
        layer = torch.nn.Conv2d(
            in_channels=self.layer.Cin,
            out_channels=self.layer.Cout,
            kernel_size=self.layer.kernel_size,
            stride=self.layer.kernel_stride,
            padding=0,
            bias=False,
        )
        layer.weight = torch.nn.Parameter(
            self.layer.expected[Mapping.TORCH][IO.B].to(torch.float),
            requires_grad=False,
        )
        c = layer(a.to(torch.float))
        return c.to(DTYPE)

    def _process_mxu(self, c):
        if self.device.FIP_METHOD != FIPMethod.BASELINE:
            seqitem = AttrDict()
            seqitem.a = self.map_input_torch2gemm(IO.A)
            seqitem.b = self.map_input_torch2gemm(IO.B)
            seqitem.dtype = DTYPE
            from nnhw.arith.matmul import MatMulScoreboard
            beta = MatMulScoreboard().get_beta(seqitem)
            for i, _ in enumerate(c[0]):
                c[0, i] += beta[i]
        return c

    def map_input_torch2gemm(self, iokey):
        """Transform a from 4-d to 2-d for matmul."""
        if iokey is IO.A:
            return self._map_a_torch2gemm(iokey)
        elif iokey is IO.B:
            return self._map_b_torch2gemm(iokey)

    def _map_a_torch2gemm(self, iokey):
        log_en = True
        log_en = False
        x = self.layer.expected.torch.a
        x = x.detach().clone()
        sizes = AttrDict()
        strides = AttrDict()
        for i, key in enumerate(['N', 'Cin', 'H', 'W']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        new_sizes = AttrDict()
        new_sizes.H = sizes.H
        new_sizes.W = sizes.W
        new_sizes.Cin = sizes.Cin
        new_strides = AttrDict()
        new_strides.H = strides.H
        new_strides.W = strides.W
        new_strides.Cin = strides.Cin
        # self._mapping_debug(
        #     x, sizes, strides, new_sizes, new_strides, 'x in', log_en)
        x = x.as_strided(list(new_sizes.values()),
                         list(new_strides.values())).contiguous()
        pad = tilepad(sizes.Cin, self.layer.tile_sizes[N])
        from torch.nn import functional as F
        x = F.pad(x, (pad, 0, 0, 0, 0, 0))
        sizes = AttrDict()
        strides = AttrDict()
        for i, key in enumerate(['H', 'W', 'Cin']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        import sections
        dims = sections(
            sections('M', (), 'H_out', 'W_out'),
            sections('K', (), 'kernel_tile', 'kernel_i', 'kernel_j'),
            child_sizes=property(lambda self: [prod(child.size)
                                               for child in self]),
        )
        dims['M']['H_out'].size = self.layer.HWs_ef.gemm.i
        dims['M']['W_out'].size = self.layer.HWs_ef.gemm.j
        dims['K']['kernel_tile'].size = sizes.Cin
        dims['K']['kernel_i'].size = self.layer.kernel_size.i
        dims['K']['kernel_j'].size = self.layer.kernel_size.j
        dims['M']['H_out'].stride       = strides.H * self.layer.stride.i
        dims['M']['W_out'].stride       = strides.W * self.layer.stride.j
        dims['K']['kernel_tile'].stride = strides.Cin
        dims['K']['kernel_i'].stride    = strides.H
        dims['K']['kernel_j'].stride    = strides.W
        self._mapping_debug(
            x, sizes, strides, new_sizes, new_strides, 'x first as_strided',
            log_en)
        log(dims)
        # self._mapping_debug(
        #     x, sizes, strides, dims.sizes, dims.strides, 'x first as_strided',
        #     log_en)
        x = x.as_strided(dims.sizes, dims.strides).contiguous()
        # self._mapping_debug(
            # x, sizes, strides, dims.sizes, dims.sizes, 'x second as_strided',
            # log_en)
        x = x.reshape(dims.child_sizes).contiguous()
        # self._mapping_debug(
            # x, sizes, strides, dims.children.sizes, dims.children.sizes,
            # 'x out', log_en)
        return x

    def _map_b_torch2gemm(self, iokey):
        reshape_size = [
            self.layer.Cout,
            self.layer.Cin
            * self.layer.kernel_size.i*self.layer.kernel_size.j,
           ]
        x = self.layer.expected.torch.b.reshape(reshape_size).permute(1, 0)
        return x

    def _mapping_debug(self, x, sizes, strides, new_sizes, new_strides,
                      msg='', log_en=False):
        if log_en:
            log.ln()
        log(msg)
        log(strides)
        log(sizes)
        log(x.stride())
        log(x.size())
        log(new_strides)
        log(new_sizes)
        if log_en:
            log.ln()
        # log(x)

    def map_output_device2torch(self, x, HW):
        # log_en = True
        # log_en = False
        x = x.detach().clone().contiguous()
        sizes = AttrDict()
        strides = AttrDict()
        for i, key in enumerate(['tile_count_N', 'HW', 'tile_size_N']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        new_sizes = [
            sizes.tile_count_N,
            sizes.tile_size_N,
            sizes.HW,
        ]
        new_strides = [
            strides.tile_count_N,
            strides.tile_size_N,
            strides.HW,
        ]
        # self._mapping_debug(
            # x, sizes, strides, new_sizes, new_strides, 'x in', log_en)
        x = x.as_strided(new_sizes, new_strides).contiguous()
        x = x.reshape((
            sizes.tile_count_N*sizes.tile_size_N,
            sizes.HW,
        )).contiguous()
        sizes = AttrDict()
        strides = AttrDict()
        for i, key in enumerate(['Cout', 'HW']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        new_sizes = [
            sizes.Cout,
            HW.i,
            HW.j,
        ]
        new_strides = [
            strides.Cout,
            HW.j*strides.HW,
            strides.HW,
        ]
        # self._mapping_debug(
            # x, sizes, strides, new_sizes, new_strides, 'x first as_strided',
            # log_en)
        x = x.as_strided(new_sizes, new_strides)
        x = x.contiguous()
        x = x.unsqueeze(0)
        sizes = AttrDict()
        strides = AttrDict()
        for i, key in enumerate(['Cout', 'i', 'j']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        # self._mapping_debug(
            # x, sizes, strides, new_sizes, new_strides, 'x out', log_en)
        return x

    def map_output_torch2device(self, x):
        # log_en = True
        # log_en = False
        x = x.detach().clone()
        sizes = AttrDict()
        strides = AttrDict()
        for i, key in enumerate(['N', 'Cout', 'H', 'W']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        new_sizes = [
            sizes.H,
            sizes.W,
            sizes.Cout
        ]
        new_strides = [
            strides.H,
            strides.W,
            strides.Cout
        ]
        # self._mapping_debug(
            # x, sizes, strides, new_sizes, new_strides, 'x in', log_en)
        x = x.as_strided(new_sizes, new_strides).contiguous()
        d = self.device
        ts = self.layer.tile_sizes
        tsn = ts[N]
        pad = tilepad(sizes.Cout, tsn)
        from torch.nn import functional as F
        x = F.pad(x, (pad, 0, 0, 0, 0, 0))
        for i, key in enumerate(['H', 'W', 'Cout']):
            sizes[key] = x.size(i)
            strides[key] = x.stride(i)
        new_sizes = [
            self.layer.tc[N],
            sizes.H*sizes.W,
            tsn,
        ]
        new_strides = [
            self.layer.tile_sizes[N]*strides.Cout,
            strides.W,
            strides.Cout,
        ]
        # self._mapping_debug(
            # x, sizes, strides, new_sizes, new_strides, 'x first as_strided',
            # log_en)
        x = x.as_strided(new_sizes, new_strides).contiguous()
        # self._mapping_debug(
            # x, sizes, strides, new_sizes, new_strides, 'x out', log_en)
        return x

    def pool(self, c, type_=None, padding=0):
        type_ = self.layer.pool_type
        if self.layer.pool_size <= 1:
            return c
        if type_ is Pool.MAXPOOL2D:
            pool = torch.nn.MaxPool2d(kernel_size=self.layer.pool_size,
                                stride=self.layer.pool_stride,
                                padding=padding)
        elif type_ is Pool.AVGPOOL2D:
            pool = torch.nn.AvgPool2d(kernel_size=self.layer.pool_size,
                                stride=self.layer.pool_stride,
                                padding=padding)
        c = pool(c.to(torch.float)).to(DTYPE)
        return c
