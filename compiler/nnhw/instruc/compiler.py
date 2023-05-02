import nnhw
from nnhw import instruc
from nnhw.instruc import DecodedInstruc
from nnhw.top import (
    AttrDict, IJParam, IJParam2, IntEnum, MNKParam, FIPMethod,
    nameof, prod, IO, IOs, Device, DTYPE,
    varname, Pool, tilepad, LowerStrEnum, auto, noinit, Mapping,
    Cin, Cout, H, Hin, Hout, K, M, N, W, tile_count, tile_fill, Level,
    tohex, tilepad)
from debug import log
import torch
from torch import Tensor
from math import ceil
from attrs import define, field, Factory
import typing as typ
from typing import Any
from typing import List, Dict
from copy import copy, deepcopy
from dataclasses import dataclass
from random import randrange
import random
from nnhw.top.cfg import config
import numpy as np


@define
class Compiler:
    device: Device
    control_instrucs: List[List[DecodedInstruc]] = noinit([])
    last_control_instrucs: List[List[DecodedInstruc]] = noinit([])
    first_layer_wr_instrucs: List[List[DecodedInstruc]] = noinit([])
    first_layer_params_instruc: List[List[DecodedInstruc]] = noinit([])
    model_instrucs: List[DecodedInstruc] = noinit(list)
    total_weight_writes_all_layers: int = noinit(0)
    total_pgp_writes_all_layers: int = noinit(0)
    total_weight_reads_all_layers: int = noinit(0)
    total_pgp_reads_all_layers: int = noinit(0)
    mem_requirements: AttrDict = noinit(AttrDict)
    offset_margin: int = 8
    max_accum_size: int = noinit(0)

    def __call__(self, nn: 'NN', save=True):
        self.total_weight_writes_all_layers = 0
        self.total_pgp_writes_all_layers = 0
        self.total_weight_reads_all_layers = 0
        self.total_pgp_reads_all_layers = 0
        self.model_instrucs += [instruc.Load()]
        for section in range(nn.total_sections):
            self.control_instrucs.append([])
            self.last_control_instrucs.append([])
        self._compile_nn_instrucs(nn)
        from nnhw.instruc import Encoder
        from nnhw.instruc import regs
        kwds = dict(show_context=False)
        d = self.device
        acumm_bw = ceil(self.log2(self.max_accum_size))
        if not config.compare_mem_sz:
            assert d.LAYERIO_WIDTH*2-1 + acumm_bw <= d.MAC_WIDTH
        if save and not config.istest:
            Encoder()([instruc.Reset()], nn.reset_instruc_name, self.device)
            Encoder()([instruc.Reset0()], 'reset0', self.device)
            Encoder()([instruc.Reset1()], 'reset1', self.device)
            Encoder()([instruc.Reset2()], 'reset2', self.device)
            Encoder()([instruc.Load()], 'load', self.device)
            Encoder()([instruc.Stall()], 'stall', self.device)
            Encoder()([instruc.Run()], 'run', self.device)
            Encoder()([instruc.StartTimer()], 'start_timer', self.device)
            Encoder()([instruc.RestartTimer()], 'restart_timer', self.device)
            Encoder()([instruc.RecordTimer()], 'record_timer', self.device)
            Encoder()([instruc.StopTimer()], 'stop_timer', self.device)
            Encoder()([instruc.GetResults()], 'get_results', self.device)
            Encoder()(self.first_layer_params_instruc,
                      'first_layer_params_instruc', self.device)
            Encoder()(self.first_layer_wr_instrucs,
                      'first_layer_wr_instrucs', self.device)
            Encoder()(self.model_instrucs, nn.model_instruc_name, self.device)
            for section in range(nn.total_sections):
                Encoder()(self.control_instrucs[section],
                          nn.control_instruc_name(section), self.device)
            Encoder()(self.last_control_instrucs[0],
                      nn.control_instruc_name() + '_last', self.device)
        self._test(nn)
        if config.debuglevels.compiler:
            self._debug(nn)

    def compile_full_instruc(self, nn: 'NN'):
        batch_size = nn[0].batch_size
        from nnhw.instruc import Encoder
        encoder = Encoder()
        instrucs = []
        rb = encoder.read_back_encoded_instrucs
        instrucs += rb('reset')
        instrucs += rb('first_layer_params_instruc')
        instrucs += rb('first_layer_wr_instrucs')
        ctrl0_name = nn.control_instruc_name(0)
        if batch_size == 1:
            ctrl0_name += '_last'
        instrucs += rb(ctrl0_name)
        instrucs += rb('load')
        instrucs += rb(nn.model_instruc_name)
        instrucs += rb('record_timer')
        instrucs = np.array(instrucs, dtype=np.uint8)
        encoder._write_encoded_instrucs_to_file(
            instrucs, nn.full_instruc_name(0))
        instrucs = []
        sent_reset = False
        instrucs += rb('restart_timer')
        for i in range(nn[0].batch_size):
            if i < batch_size - 1:
                instrucs += rb('first_layer_wr_instrucs')
            if i < batch_size - 2:
                instrucs += rb(nn.control_instruc_name(0))
            if i == batch_size - 2:
                instrucs += rb(nn.control_instruc_name(0) + '_last')
            if (i == 0) and nn.total_sections > 1:
                instrucs += rb(nn.control_instruc_name(2))
            if (i == batch_size - 1) and nn.total_sections > 1:
                instrucs += rb(nn.control_instruc_name(1))
            _i = i
            if config.repeat_input:
                _i = batch_size-1
            instrucs += rb(nn.inference_instruc_name(_i))
            instrucs += rb('run')
        if nn.total_sections > 1:
            instrucs += rb('run')
        instrucs = np.array(instrucs, dtype=np.uint8)
        encoder._write_encoded_instrucs_to_file(
            instrucs, nn.full_instruc_name(1))

    def io_size(self, layer, io):
        data = layer.expected.torch[io]
        if config.use_layer1_optimization2 and layer.isfirst:
            data = layer.optimized.torch[io]
        device = layer.device
        res = prod(data.size()) * device.WIDTHS[io]
        res *= device.LAYERIO_WIDTH / 8
        return res

    def _test(self, nn):
        logkwds = dict(show_context=False, log_en=config.debuglevels.compiler)
        total_weight_size_all_layers: int = 0
        total_pgp_size_all_layers: int = 0
        self.mem_requirements.max_layeriomem0_size = 0
        self.mem_requirements.max_layeriomem_size = 0
        for layer in nn:
            layer.mem.remap(Mapping.DEVICE)
            layer.tile_size_w = layer.mem.a.space[tile_fill][M][W].size
        for layer in nn:
            memdata = AttrDict()
            memdata.layeriomem_size = (
                self.io_size(layer, IO.A)
                * self.layeriomem_ratio(layer.tile_size_w))
            if not any([layer.isfirst, layer.islast]
                       ) and layer.wrmem == layer.rdmem:
                memdata.layeriomem_size += (
                    self.io_size(layer, IO.C)
                    * self.layeriomem_ratio(layer.next.tile_size_w))
            if layer.isfirst:
                memdata.layeriomem_size *= (layer.device.SZJ
                                            /layer.Cin)
            memkey = ('max_layeriomem0_size' if layer.isfirst else
                      'max_layeriomem_size')
            if memdata.layeriomem_size > self.mem_requirements[memkey]:
                self.mem_requirements[memkey] = memdata.layeriomem_size
            memdata.weightmem_size = (
                prod(layer.instrucs.weight.value.size()
                     ) * layer.device.B_WIDTH)
            memdata.pgp_mem_size = (
                prod(layer.instrucs.post_gemm_params.value.size())
                * layer.device.WIDTHS[IO.POST_GEMM_PARAMS])
            total_weight_size_all_layers += memdata.weightmem_size
            total_pgp_size_all_layers += memdata.pgp_mem_size
            _memdata = deepcopy(memdata)
            for k, v in _memdata.items():
                memdata[k] = self.log2(v)
            memdata.total_layerio_reads = self.log2(
                layer.instrucs.layer_params.total_layerio_reads)
            memdata.total_weight_reads = self.log2(
                layer.instrucs.layer_params.total_weight_reads)
            mem_requirements = memdata
            memstr = f'LAYERIOMEM{layer.rdmem}_SIZE'
            if not config.compare_mem_sz:
                assert _memdata.layeriomem_size <= layer.device[memstr], log(
                    _memdata.layeriomem_size, layer.device[memstr],
                    layer.position, layer.islinear, memstr)
            assert (memdata.total_layerio_reads
                    < layer.device.LAYER_PARAM_WIDTH)
            for k in ['total_weight_reads',
                      'total_layerio_reads',]:
                v = memdata[k]
                assert (v < layer.device.LAYER_PARAM_WIDTH), log(
                    k, v, layer.device.LAYER_PARAM_WIDTH)
        self.mem_requirements.total_weight_size_all_layers = (
            self.log2(total_weight_size_all_layers))
        self.mem_requirements.total_pgp_size_all_layers = (
            self.log2(total_pgp_size_all_layers))
        assert total_weight_size_all_layers < self.device.WEIGHTMEM_SIZE
        assert (self.total_weight_reads_all_layers
                < self.device.WEIGHTMEM_SIZE)
        for k in ['total_weight_reads_all_layers',
                  'total_pgp_reads_all_layers']:
            v = getattr(self, k)

    def _debug(self, nn):
        logkwds = dict(show_context=False)
        if config.debuglevels.compiler > Level.LOW:
            for layer in nn:
                log(layer.instrucs)

    def log2(self, val):
        import math
        return round((math.log2(val)) * 100) / 100

    def layeriomem_ratio(self, tile_size_w):
        result = (
            (tile_size_w + tilepad(
                tile_size_w, self.device.LAYERIOMEM_CLK_DIV))
            / tile_size_w
        )
        return result

    def _compile_nn_instrucs(self, nn):
        for layer in nn:
            mem = layer.mem
            mem.remap(Mapping.DEVICE)  # get instrucs
            if layer.islast:
                layer.next.mem.remap(Mapping.DEVICE)  # get instrucs
        for layer in nn:
            self._compile_ios(layer)
            self._compile_layer_params(layer)
        for layer in nn:
            self._set_nn_param(layer.instrucs.layer_params, nn)
        for layer in nn:
            accum_size = layer.tile_sizes[K] * layer.tile_counts[K]
            if accum_size > self.max_accum_size:
                self.max_accum_size = accum_size
            section = layer.section
            if layer.isfirst:
                self._compile_first_layerio_wr_instruc(layer)
            for instrc in layer.instrucs.values():
                if instrc.name in nameof(
                        layer.instrucs.layerio_rd_instrucs):
                    section_ = section
                    if (layer.isfirst_insection
                        and section == 1 and nn.total_sections > 1):
                        section_ = 2
                    self.control_instrucs[section_] += [
                        instrc[layer.rdmem]]
                    self.last_control_instrucs[section_] += [
                        instrc[layer.rdmem]]
                elif instrc.name in nameof(
                        layer.instrucs.layerio_wr_instrucs):
                    section_ = section
                    if (layer.islast_insection
                        and section == 0 and nn.total_sections > 1):
                        instrc[layer.wrmem].size[-1] *= (
                            layer.parent[0].batch_size)
                        section_ = 2
                    self.control_instrucs[section_] += [
                        instrc[layer.wrmem]]
                    self.last_control_instrucs[section_] += [
                        instrc[layer.wrmem]]
                elif instrc.name in ['layer_params']:
                    cp = copy(instrc)
                    self.control_instrucs[section] += [cp]
                    instrc.load_input = 0
                    instrc.in_last_inference = 1
                    instrc.total_inference_writes = -1
                    self.last_control_instrucs[section] += [instrc]
                elif instrc.name not in ['post_gemm_params', 'weight']:
                    self.control_instrucs[section] += [instrc]
                    self.last_control_instrucs[section] += [instrc]
            for instrc in layer.instrucs.values():
                if instrc.name in ['post_gemm_params', 'weight']:
                    self.model_instrucs += [instrc]
        kwds = dict(show_context=False)
        for layer in nn:
            ins = layer.instrucs
            rdins = ins.layerio_rd_instrucs[layer.rdmem]
            wrins = ins.layerio_wr_instrucs[layer.wrmem]

    def _set_nn_param(self, layer_params, nn):
        from nnhw.instruc import Write2Reg, regs
        for k in ['total_weight_writes_all_layers',
                    'total_pgp_writes_all_layers',
                    'total_weight_reads_all_layers',
                    'total_pgp_reads_all_layers', ]:
            k: str = k
            v = getattr(self, k)
            setattr(layer_params, k, v)
            v = self.log2(getattr(self, k))
            assert (v < self.device.LAYER_PARAM_WIDTH), log(
                k, v, self.device.LAYER_PARAM_WIDTH)
        layer = nn[0]
        d = {'size_w_c': self.size_w_c(layer),
             'total_layer_reads': prod(
                 layer.instrucs.layerio_rd_instrucs[layer.rdmem].size),
             'tile_size_m': layer.tile_sizes[M],
             }
        for k, v in d.items():
            k = 'inputmem_' + k
            setattr(layer_params, k, v)

    def _compile_ios(self, layer):
        """Compile and write instructions to a file. See nnhw.instruc.encoder
        for more detail."""
        mem = layer.mem
        layer.instrucs.weight.value = mem.device_b_mod.to(self.device.btype)
        layer.instrucs.post_gemm_params.value = mem.device_post_gemm_params
        layer.instrucs.layerio_wr_instrucs[layer.wrmem].size[-1] = ceil(prod(
            (*layer.HWs.c, layer.tile_counts[N])))

    def size_w_c(self, layer):
        size_w_c = layer.HWs.a.j
        if config.use_layer1_optimization2 and layer.isfirst:
            size_w_c = ceil(layer.HWs.a.j/ layer.kernel_stride.j)
        return size_w_c

    def _compile_first_layerio_wr_instruc(self, layer):
        kwds = dict(show_context=False,
                    log_en=config.debuglevels.compiler > Level.LOW)
        device_tensor_a = layer.mem.device_a_mod
        prev_layerio_wr_instruc = deepcopy(
            layer.instrucs.layerio_wr_instrucs[layer.rdmem])
        layerio0_wr_instruc = layer.instrucs.layerio_wr_instrucs[layer.rdmem]
        layerio0_wr_instruc.size = [0] * (self.device.TOTAL_DIGITS-1) + [
            ceil(prod(device_tensor_a.size()) / layer.device.MXU_SIZE.j)]
        layerio0_wr_instruc.stride = [0] * (
            self.device.TOTAL_DIGITS-1) + [1]
        layerio0_wr_instruc.offset = 1
        if layer.HWs.a.j > 1 and config.do_mem_optimization:
            layerio0_wr_instruc.offset = (layerio0_wr_instruc.size[-1]
                                          + self.offset_margin)
        first_layer_params_instruc = instruc.LayerParams()
        first_layer_params_instruc.size_w_c = self.size_w_c(layer)
        first_layer_params_instruc.layeriomem_wrsel = 0
        first_layer_params_instruc.valid = 0
        section = layer.section
        self.first_layer_params_instruc += [first_layer_params_instruc]
        self.first_layer_wr_instrucs += [layerio0_wr_instruc]
        layer.instrucs.layerio_wr_instrucs[layer.rdmem] = (
            prev_layerio_wr_instruc)
        self._set_nn_param(first_layer_params_instruc, layer.parent)

    def _compile_layer_params(self, layer):
        layer_params = layer.instrucs.layer_params
        if hasattr(layer_params, 'do_conv'):
            layer_params.size_w_gemm = 0
        for iokey in IOs.POST_CONV + [IO.GEMM]:
            if iokey != IO.C:
                key = 'size_h_' + iokey
                setattr(layer_params, key, layer.HWs[iokey].i)
            key = 'size_w_' + iokey
            setattr(layer_params, key, layer.HWs[iokey].j)
        if config.use_layer1_optimization2 and layer.isfirst:
            count_k_kernel_h_dim = 5
            count_k_kernel_w_dim = 4
            count_m_h_dim = 7
            count_m_w_dim = 6
            fill_m_h_dim = 2
            fill_m_w_dim = 1
            for space in [layer.instrucs.layerio_rd_instrucs[layer.rdmem],
                          layer.instrucs.weight_rd_instruc,
                          layer.instrucs.post_gemm_params_rd_instruc]:
                size = space.size
                size[-count_k_kernel_h_dim-1] = ceil(
                    size[-count_k_kernel_h_dim-1] / layer.kernel_stride.i)
                size[-count_k_kernel_w_dim-1] = ceil(
                    size[-count_k_kernel_w_dim-1] / layer.kernel_stride.j)
                pass
            stride = layer.instrucs.layerio_rd_instrucs[layer.rdmem].stride
            stride[-fill_m_h_dim-1] = ceil(
                stride[-fill_m_h_dim-1] / layer.kernel_stride.i)
            stride[-count_m_h_dim-1] = ceil(
                stride[-count_m_h_dim-1] / layer.kernel_stride.i)
            stride[-fill_m_w_dim-1] = ceil(
                stride[-fill_m_w_dim-1] / layer.kernel_stride.j)
            stride[-count_m_w_dim-1] = ceil(
                stride[-count_m_w_dim-1] / layer.kernel_stride.j)
        if layer.is_first_linear_after_conv:
            count_Cin_dim = -3-1
            fill_Cin_dim = -0-1
            count_m_h_dim = -7-1
            fill_m_h_dim = -2-1
            space = layer.instrucs.layerio_rd_instrucs[layer.rdmem]
            stride = space.stride
            size = space.size
            stride[count_Cin_dim] = stride[fill_m_h_dim]
            stride[fill_m_h_dim] *= size[count_Cin_dim]
        layer_params.total_layerio_reads = prod(
            layer.instrucs.layerio_rd_instrucs[layer.rdmem].size)
        layer_params.layeriomem_wrsel = layer.wrmem
        layer_params.layeriomem_rdsel = layer.rdmem
        layer_params.tile_size_m = layer.tile_sizes[M]
        layer_params.total_weight_reads = prod(
            layer.instrucs.weight_rd_instruc.size)
        self._set_offsets(layer)
        batch_size = layer.parent[0].batch_size
        total_weight_reads_all_layers = layer_params.total_weight_reads
        total_pgp_reads_all_layers = prod(
            layer.instrucs.post_gemm_params_rd_instruc.size)
        if not layer.islinear:
            total_weight_reads_all_layers *= batch_size
            total_pgp_reads_all_layers *= batch_size
        self.total_weight_reads_all_layers += total_weight_reads_all_layers
        self.total_pgp_reads_all_layers += total_pgp_reads_all_layers
        self.total_weight_writes_all_layers += int(prod(
            layer.instrucs.weight.value.size()) / layer.device.MXU_SIZE.j)
        self.total_pgp_writes_all_layers += prod(
            layer.instrucs.post_gemm_params.value.size())
        layer.instrucs.post_gemm_params_rd_instruc.size[-2] /= (
                self.device.WEIGHTMEM_CLK_DIV)
        layer.instrucs.weight_rd_instruc.size[-2] /= (
                self.device.SZI)
        layer.instrucs.post_gemm_params_rd_instruc.stride[-2] *= (
                self.device.WEIGHTMEM_CLK_DIV)
        layer.instrucs.weight_rd_instruc.stride[-2] *= (
                self.device.SZI)
        layer_params.size_w_c = layer.HWs.c.j
        if layer.is_first_linear_after_conv:
            layer_params.size_w_c *= layer.parent[0].batch_size
        layer_params.pool_size = layer.pool_size
        layer_params.pool_stride = layer.pool_stride
        layer_params.avg_pool_denom = layer.pool_size ** 2
        layer_params.pool_padding = layer.pool_padding
        layer_params.c_padding = layer.c_padding
        layer_params.pool_type = layer.pool_type
        section  = layer.section
        layerislast = layer.islast_insection
        layer_params.islastlayer = layerislast
        nn = layer.parent
        layer_params.islast_inbatch = (section == nn.total_sections-1
                                 ) or (section > 0)
        layer_params.hw_size_padding = (
            prod(layer.HWs.pool_padding) * layer.tile_counts[N])
        layer_params.total_c_padding_writes = (
            prod(layer.HWs.c) * layer.tile_counts[N])
        layer_params.valid = 1
        layer_params.loading_params_valid = (not layer.islast)
        if layer.position == layer.parent.input_load_pos:
            layer_params.load_input = 1
        if layer.islast_insection:
            layer_params.total_inference_writes = int(prod(
                layer.expected.device.c.size()) / layer.device.MXU_SIZE.j)

    def _set_offsets(self, layer):
        reader = layer.instrucs.layerio_rd_instrucs[layer.rdmem]
        writer = layer.instrucs.layerio_wr_instrucs[layer.wrmem]
        szj = layer.device.MXU_SIZE.j
        reader_size = ceil(prod(layer.optimized.torch.a.size()) / szj)
        writer_size = ceil(prod(layer.optimized.torch.c.size()) / szj)
        if config.do_mem_optimization:
            if layer.isfirst:
                reader.offset *= reader_size + self.offset_margin

from nnhw.arith import Layer, NN
