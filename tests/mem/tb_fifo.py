import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, Timer
from debug import log


async def initial_reset(vif):
    vif.resetn <= 1
    await FallingEdge(vif.clk)
    await FallingEdge(vif.clk)
    vif.resetn <= 0
    await FallingEdge(vif.clk)
    await FallingEdge(vif.clk)
    vif.resetn <= 1


async def always_clk(dut, ncycles=1000, period=10):
    dut.clk <= 0
    n = 0
    print("EEE starting always_clk")
    half_period = period / 2
    while n < 2*ncycles:
        n += 1
        await Timer(half_period, "NS")
        next_val = not dut.clk.value
        dut.clk <= int(next_val)


async def monitor(vif, name='monitor', only_q=True):
    while True:
        await RisingEdge(vif.clk)
        if not only_q:
            log('---- ' + name + ' ----')
            log(f'wrreq = {vif.wrreq}')
            try:
                log(f'd = {vif.d.value.integer}')
            except ValueError:
                log(f'd = {vif.d}')
            log(f'rdreq = {vif.rdreq}')
        try:
            log(f'> {name} q = {vif.q.value.integer}')
        except ValueError:
            log(f'> {name} q = {vif.q}')


async def scoreboard(fifo, bfm):
    assert fifo.q.value.binstr == bfm.q.value.binstr


@cocotb.test()
async def tb(dut):
    vif = dut
    fifo = dut.fifo
    bfm = dut.bfm
    total_cycles = 100
    cocotb.fork(always_clk(vif, total_cycles))
    cocotb.fork(monitor(bfm, 'bfm ', False))
    cocotb.fork(monitor(fifo, 'fifo'))
    cocotb.fork(scoreboard(fifo, bfm))
    bfm.rdreq <= 0
    bfm.wrreq <= 0
    await initial_reset(vif)
    while not fifo.wrready.value:
        Timer(1)
    while not bfm.wrready.value:
        Timer(1)
    await RisingEdge(vif.clk)
    bfm.d <= 1
    bfm.wrreq <= 1
    await RisingEdge(vif.clk)
    bfm.d <= 2
    await RisingEdge(vif.clk)
    bfm.d <= 3
    bfm.rdreq <= 1
