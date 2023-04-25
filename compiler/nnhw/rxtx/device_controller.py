import subprocess
from click_spinner import spinner
import asyncio
from asyncio import create_task as fork
import sys
from typing import NewType
import torch
from torch import Tensor
from nnhw import instruc
from nnhw.instruc import Encoder
from nnhw.top import Path, tohex, DTYPE, prod, print_begin_end, Level
from utils import mkdir, mv, rm, cp, run
from fabric import Connection
import time
from debug import log
tp = Connection('tp')


Output = NewType('Output', Tensor)


class DeviceController:
    """Send/receive data to/from device."""

    def __init__(self):
        self.loaded_nn = None

    def send(self, input):
        """Send an input to device.
        Could be initial image data or intermediate data."""
        ...

    def receive(self) -> Output:
        """Receive output from device.
        Could be intermediate data or final result."""
        ...

    def send_model(self, instruc_fname, sync=True):
        """
        Send coded model data (also referred to as intrucs/params) to device.
        This is relatively easy due to the simple xillybus pcie driver, which
        lets data be sent to a FIFO on the device by using a simple `cat`
        command on the host.
        """
        sync = True
        from timeit import default_timer as timer
        start = timer()
        instrucpath = Encoder().instruc_path(instruc_fname)
        if sync:
            end = timer()
            start = timer()
            run(f'{Path.BIN}/lcl2remote_sync {instrucpath}')
        if 1:
            try:
                cmd = tp.run(f'~/bin/wxillybus_32.sh {instrucpath}', hide=True)
                stdout = cmd.stdout
                end = timer()
                return stdout
            except Exception as e:
                s = ''
                s += str(e)
                log(instruc_fname)
                log(e)
                quit()
        end = timer()

    def _wait_for_host(self, display_msg=True):
        is_first_try = True
        while True:
            try:
                tp = Connection('tp')
                tp.run('ls', hide=True)
                break
            except Exception as e:
                from debug import log
                if is_first_try and display_msg:
                    print('\nWaiting for remote server to boot up.\n')
                is_first_try = False
                time.sleep(5)

    def wait_for_host(self, display_msg=True):
        if display_msg:
            with spinner():
                self._wait_for_host(display_msg)
        else:
            self._wait_for_host(display_msg)

    def tx(self, instruc_fname, sync=True):
        self.wait_for_host(True)
        result = self.send_model(instruc_fname, sync)

    def rx(self): return asyncio.run(self._rx())

    async def _rx(self):
        from nnhw.top.cfg import config
        from nnhw.top.main import main
        timeout = ('3'
                   if prod(main.program.layers[0].expected.torch.a.size())
                   > config.max_printable_io_size else '1')
        timeout = '1'
        timeout = '2'
        log(timeout, context=False)
        self.wait_for_host(False)
        tp = Connection('tp')
        tp.run(f'~/bin/rxillybus_32.sh {timeout}', hide=True)
        datafile = '/home/trevor/xillybus.log'
        run(f'~/nnhw/bin/remote2lcl_sync {datafile}')
        with open(datafile, 'rb') as f:
            result = f.read()
        return torch.tensor(list(result), dtype=DTYPE)

    def rxtx(self, instruc_fname, sync=True) -> Tensor:
        self.tx(f'{instruc_fname}', sync)
        x = asyncio.run(self._rx())
        return x

    def load_nn(self, instruc_fname) -> None:
        self.tx(f'{instruc_fname}')
        self.loaded_nn = instruc_fname
