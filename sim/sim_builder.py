import glob
import os
import pathlib
import re
import shutil
from os import environ as env
from pathlib import Path
from subprocess import run
from invoke import run as sh
from nnhw import top
from .ip import FIFO, IP


def write_file(fname, fstring):
    with open(fname, 'w') as f:
        f.write(fstring)


def snake2cammel(name: str):
    return ''.join(word.title() for word in name.split('_'))


def test(method):
    def wrapper(self, *args, **kwds):
        self.tests.append(f'{snake2cammel(method.__name__)}Test')
        return method(self, *args, **kwds)
    return wrapper


class SimBuilder:
    camel2snake_pattern = re.compile(r'(?<!^)(?=[A-Z])')
    from nnhw.top.cfg import config
    rm_build_dir = config.rm_sim_dir

    def __init__(self, srclists=[], testlist=[]):
        self.sources = []
        self.tests = []
        self.ips = []
        self.cli_params = {}
        self.test_module_dir = top.Path.NNHW
        self.test_module_name = 'tests'
        self.dut_top_level_module = 'dut'
        self.vlog_defines = ('+define+SIM=1')
        for src in srclists:
            if isinstance(src, str):
                getattr(self, src)()
            else:
                src(self)
        for test in testlist:
            self.tests.append(f'{snake2cammel(test)}Test')

    def run(self):
        self.do_template_dir = top.Path.SIM
        self.builds_dir = f'{top.Path.SIM}/builds'
        self.build_dir = f'{self.builds_dir}/{self.sim_dir}'
        self.test_path_name = self.__dict__.get(
            'test_path_name', self.test_module_name)
        self.test_module_path = (self.test_module_dir + '/'
                                 + self.test_path_name)
        self.run_sh_path = f'{self.builds_dir}/run'
        if self.rm_build_dir:
            shutil.rmtree(self.build_dir, ignore_errors=True)

        shutil.rmtree(f'{self.build_dir}/{self.test_module_name}',
                      ignore_errors=True)
        Path(self.builds_dir).mkdir(exist_ok=True)
        Path(self.build_dir).mkdir(exist_ok=True)
        self.gen_vlog_do()
        self.gen_vsim_do()
        self.gen_run_sh()
        for fpath in (
                glob.glob(self.do_template_dir + '/*.do')):
            sh(f'cp {fpath} {self.build_dir}')
        shutil.rmtree(
            f'{self.build_dir}/{self.test_module_path}', ignore_errors=True)
        shutil.rmtree(f'{self.build_dir}/work', ignore_errors=True)
        sh(f'cp -r {self.test_module_path} {self.build_dir}/')
        sh(f'bash {self.run_sh_path}')

    def src(self, src: str): self.sources.append(src)

    def parse_sources(self, root, sources):
        for i, src in enumerate(sources.copy()):
            sources[i] = root + '/' + src
        return sources

    def gen_vlog_do(self):
        s = ''
        for ip in self.ips:
            s += ip.vlog()
        vlog_base = ('vlog -work work +define+COCOTB_SIM -sv '
                     + '-timescale 1ns/1ps -mfcu '
                     + '+acc '
                     )
        for fname in self.sources:
            s += vlog_base + ' ' + self.vlog_defines + ' ' + fname + '\n'
        write_file(self.build_dir + '/vlog.do', s)

    def gen_vsim_do(self):
        s = ''
        s += self.gen_test_vsim_cmd('')
        write_file(self.build_dir + '/vsim.do', s)

    def gen_test_vsim_cmd(self, test):
        s = ''
        s += f'vsim '
        for k, v in self.cli_params.items():
            s += f'-g{k}={v} '
        s += (
            '-L work '
            + ' -pli $env(LIBCOCOTB_LOC) '
        )
        for ip in self.ips:
            s += ip.vsim()
        s += self.dut_top_level_module + '\n'
        s += 'set WildcardFilter [lsearch -not -all -inline $WildcardFilter Memory]\n'
        s += 'log -r /*\n'
        s += 'onbreak resume\n'
        s += 'run -all\n'
        s += '\n'
        return s

    def gen_run_sh(self):
        s = ''
        s += '#!/usr/bin/env bash\n'
        if self.running_locally:
            s += 'export LM_LICENSE_FILE=~/LR-085446_License.dat\n'
        else:
            s += 'export LM_LICENSE_FILE=~/LR-063367_License.dat\n'
        s += 'export LIBPYTHON_LOC=$(cocotb-config --libpython)\n'
        s += 'export WAVE_FILE=../wave\n'
        s += f'export TESTS=\'{self.tests}\'\n'
        s += f'export CLI_PARAMS=\'{repr(self.cli_params)}\'\n'
        s += ('export LIBCOCOTB_LOC=$(cocotb-config '
              + '--lib-name-path vpi questa)\n')
        _sed = r"s/[#']\([^#]\|$\)/\1/g"
        q = '"'
        sed = ''
        sed += f' | sed {q}{_sed}{q}'
        sed += '\n'
        s += 'export MODULE=' + self.test_module_name + '\n'
        s += f'cd {self.build_dir}\n'
        s += 'echo "starting vsim"\n'

        local_vsim = '~/intelFPGA_pro/22.2/questa_fse/bin/vsim'
        remote_vsim = '~/intelFPGA_pro/21.4/questa_fse/bin/vsim'
        if self.running_locally:
            term_vsim = local_vsim
        else:
            term_vsim = remote_vsim
        s_terminal = f'{term_vsim} -c -do sim.do 2>&1' + sed
        s_terminal += 'echo "done vsim"\n'
        s_gui = 'source ../_gui_run&\n'
        s_gui += (f'{local_vsim} -view vsim.wlf -do '
                 + 'startup_load_previous_wave.do\n')
        s_gui_ = '#!/usr/bin/env bash\n'
        s_gui_ += 'sleep 12\n'
        change_window_name = (
            f'xdotool search --name ".*Intel Starter FPGA Edition-64.*" '
            + f'set_window --name "{self.sim_dir}"\n'
        )
        echo_change_window_name = (
            f'xdotool search --name \'".*Intel Starter FPGA Edition-64'
            + f'.*"\' set_window --name \'"{self.sim_dir}"\'\n'
        )
        s_gui_ += 'echo ' + f'"{echo_change_window_name}"'
        s_terminal = s + s_terminal
        s_gui = s + s_gui
        write_file(self.run_sh_path, s_terminal)
        write_file(self.builds_dir + '/gui_run', s_gui)
        write_file(self.builds_dir + '/_gui_run', s_gui_)
