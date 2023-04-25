from nnhw import top


class IP:
    do_full_compile = True
    _already_vlogged = False
    _already_vsimed = False
    base_vlog = (
        ''
        + 'source $QSYS_SIMDIR/mentor/msim_setup.tcl\n'
        + 'dev_com\n'
        + 'com\n'
    )
    base_vsim = (
        ''
        + '-L work_lib '
    )

    def __init__(self, *args, **attrs):
        self.setattrs(**attrs)
        self.dir = top.Path.IP + '/' + self.dir

    def setattrs(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

    def vlog_top_line(self):
        return 'set QSYS_SIMDIR ' + self.dir + '/' + self.name + '/sim\n'

    def vlog(self):
        s = ''
        if self.running_locally:
            qpath = '/home/trevor/intelFPGA_pro/21.3/quartus\n'
        else:
            qpath = '/CMC/tools/intel/intelFPGA_pro/20.1/quartus\n'
        if not self.__class__._already_vlogged:
            s += ('set QUARTUS_INSTALL_DIR '
                  + qpath)
        s += self.vlog_top_line()
        s += self.base_vlog
        s += '\n'
        self.__class__.already_vlogded = True
        return s

    def vsim(self):
        s = ''
        if not self.__class__._already_vsimed:
            s += self.base_vsim
        s += '-L ' + self.name + ' '
        self.__class__._already_vsimed = True
        return s


class DPRAM(IP):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.base_vlog = self.__class__.base_vlog
        self.base_vsim += (
            ''
            + '-L altera_ver -L lpm_ver -L sgate_ver -L altera_mf_ver '
            + '-L altera_lnsim_ver -L twentynm_ver -L twentynm_hssi_ver '
            + '-L twentynm_hip_ver -L ram_2port_2021 '
            + f'-L {self.name} '
        )
        if self.do_full_compile:
            self.base_vlog += 'dev_com\n'
            self.base_vlog += 'com\n'


class FIFO(IP):
    def __init__(self, *args, **attrs):
        super().__init__(*args, **attrs)
        self.base_vlog = self.__class__.base_vlog
        self.base_vsim += (
            ''
            + '-L altera_ver -L lpm_ver -L sgate_ver -L altera_mf_ver '
            + '-L altera_lnsim_ver -L twentynm_ver -L twentynm_hssi_ver '
            + '-L twentynm_hip_ver -L fifo_1910 '
            + f'-L {self.name} '
        )
        if self.do_full_compile:
            self.base_vlog += 'dev_com\n'
            self.base_vlog += 'com\n'


class DSP(IP):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.base_vlog = self.__class__.base_vlog
        self.base_vsim = self.__class__.base_vsim
        self.base_vsim += (
            ''
            + '-L altera_ver -L lpm_ver -L sgate_ver -L altera_mf_ver -L altera_lnsim_ver -L twentynm_ver -L twentynm_hssi_ver -L twentynm_hip_ver -L altera_a10_native_fixed_point_dsp_1910 '
            + f'-L {self.name} '
        )
        if self.do_full_compile:
            self.base_vlog += 'dev_com\n'
            self.base_vlog += 'com\n'


class DSPNoChainin(DSP):
    pass
