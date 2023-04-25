from nnhw import top
from nnhw.top import FIPMethod, nameof, varname, AttrDict
from nnhw.sim import ip
from nnhw.sim.sim_builder import SimBuilder, test
import socket
from debug import log


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


class Sim(SimBuilder):

    local_ips = '192.168.68.'
    if get_ip().startswith(local_ips):
        running_locally = True
    else:
        running_locally = False
    running_locally = True

    def unit_test_sources(self):
        self.vlog_defines += '+DUT="top"'
        ip_attrs = {}
        USE_FIFO_IP = False
        USE_DPRAM_IP = True
        USE_LAYERIO_DPRAM_IP = False
        USE_DSP_IP = False
        ip_attrs['do_full_compile'] = self.rm_build_dir
        ip_attrs['running_locally'] = self.running_locally
        self.vlog_defines += f'+FIP_METHOD={FIPMethod.FIP}'
        if USE_LAYERIO_DPRAM_IP:
            self.vlog_defines += '+USE_LAYERIO_DPRAM_IP=1'
        if USE_FIFO_IP:
            self.vlog_defines += '+USE_FIFO_IP=1'
            fifos = [
                'fifo_1clk',
                'dram_fifo512',
                'dram_fifo1024',
                'dram_fifo2048',
                'dram_fifo4096',
                'dram_fifo8192',
                'dram_fifo16384',
                'dram_fifo32768', 'dram_fifo65536', 'dram_fifo_max',
            ]
            for fifo in fifos:
                self.ips += [ip.FIFO(dir='mem', name=fifo, **ip_attrs)]
        if USE_DSP_IP:
            for base in ['dsp_chainin', 'dsp_nochainin', ]:
                for typ in ['', '_inlat1', '_inlat1_pl1']:
                    name = base + typ
                    self.ips += [ip.DSPNoChainin(
                        dir='arith/fixed_point',
                        name=name, **ip_attrs)]
        from nnhw.top.cfg import config
        rtl_path = config.rtl_path()
        self.src(f'{rtl_path}/top/pkg.sv')
        self.src(f'{rtl_path}/rxtx/pkg.sv')
        self.src(f'{rtl_path}/rxtx/result_parser.sv')
        self.src(f'{rtl_path}/instruc/pkg.sv')
        self.src(f'{rtl_path}/mem/pkg.sv')
        self.src(f'{rtl_path}/mem/fifo.sv')
        self.src(f'{rtl_path}/mem/look_ahead_fifo.sv')
        self.src(f'{rtl_path}/top/if.sv')
        self.src(f'{rtl_path}/top/utils.sv')
        self.src(f'{rtl_path}/instruc/instruc.sv')
        self.src(f'{rtl_path}/mem/behav_dram.sv')
        self.src(f'{rtl_path}/mem/dram.sv')
        self.src(f'{rtl_path}/mem/counter.sv')
        self.src(f'{rtl_path}/mem/weightmem.sv')
        self.src(f'{rtl_path}/mem/pgpmem.sv')
        self.src(f'{rtl_path}/mem/layeriomem_tiler.sv')
        self.src(f'{rtl_path}/mem/layeriomem_utils.sv')
        self.src(f'{rtl_path}/mem/layeriomem_memclk.sv')
        self.src(f'{rtl_path}/mem/layeriomem_topclk.sv')
        self.src(f'{rtl_path}/mem/layeriomem.sv')
        self.src(f'{rtl_path}/mem/mem.sv')
        self.src(f'{rtl_path}/mem/tilebuf.sv')
        self.src(f'{rtl_path}/mem/mem_test.sv')
        self.src(f'{rtl_path}/arith/matrix.sv')
        self.src(f'{rtl_path}/arith/double_vecbuf.sv')
        self.src(f'{rtl_path}/arith/mac_array.sv')
        self.src(f'{rtl_path}/arith/mxu.sv')
        self.src(f'{rtl_path}/arith/gemm.sv')
        self.src(f'{rtl_path}/arith/pooling.sv')
        self.src(f'{rtl_path}/arith/padding.sv')
        self.src(f'{rtl_path}/arith/post_gemm.sv')
        self.src(f'{rtl_path}/arith/arith.sv')
        self.src(f'{rtl_path}/top/top.sv')
        self.src(f'{rtl_path}/top/tests_dut.sv')

    def experiment_sources(self):
        self.src(f'{top.Path.RTL}/top/experiment/experiment.sv')

    from nnhw.top.cfg import config
    sim_dir = config.operation

def unit_tests():
    srclists = [Sim.unit_test_sources, ]
    enabled_tests = [
        'top',
    ]
    Sim(srclists, enabled_tests).run()


def experiment():
    srclists = [Sim.experiment_sources]
    testlist = []
    Sim(srclists, testlist).run()


def main():
    unit_tests()
