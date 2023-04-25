`include "../top/define.svh"

// macros and modules for synthesizable logic drivers & monitors
// so that the DUT doesn't get optimized away due to outputs not
// being monitored by anything or inputs having no driver

`define MONITOR_(q_, d_, nmspc, clk_=clk, resetn_=resetn) \
monitor #($bits(d_)) nmspc``_monitor_u(.q(q_), .d(d_), .clk(clk_), .resetn(resetn_));

`define MONITOR(q_, d_, clk_=clk, resetn_=resetn) \
`MONITOR_(q_, d_, q_, clk_, resetn_)

module monitor import globals::*;
    // produce a 1-bit output from an N-bit input to be passed to a top-level
    // output pin. Low-latency computations are performed on the data
    // so as to not affect the DUT fmax
    #(BITS, WIDTH=2,
      // make _BITS divisible by WIDTH, take ceiling if not such that
      // it is divisible:
      _BITS = (BITS%WIDTH) == 0? BITS :
      ((BITS/WIDTH)+1)*WIDTH,
      DEPTH=_BITS/WIDTH,
      type VEC=logic [DEPTH-1:0][WIDTH-1:0],
      integer DELAY=8)
    (output logic q, input VEC d, logic clk, resetn);
    data #(VEC) qadd_d(.clk, .resetn);
    data #(VEC) qadd_q(.clk, .resetn);
    if (BITS < 2*WIDTH) begin
        assign qadd_q.value = qadd_d.value;
    end else begin
        add_shiftvec #(0, FALSE) qadd_u(.q(qadd_q), .d(qadd_d));
    end
    `REG2_(qadd_d.value, d, qadd_d, DELAY/2-1);
    `REG(q, ^qadd_q.value[0], DELAY/2+1);
endmodule


`define DRIVER_(q_, d_, nmspc, clk_=clk, resetn_=resetn) \
driver #($bits(q_)) nmspc``_driver_u(.q(q_), .d(d_), .clk(clk_), .resetn(resetn_));
`define DRIVER(q_, d_, clk_=clk, resetn_=resetn) \
`DRIVER_(q_, d_, q_, clk_, resetn_)

module driver
    // take a 1-bit input (probably from a top-level input pin)
    // and use it to drive a N-bit signal (for stimulating dut inputs)
    #(BITS, type VEC=logic [BITS-1:0], integer DELAY = 8)
    (output VEC q, input logic d, logic clk, resetn);
    logic d_;
    VEC _q;
    `REG(d_, d, DELAY/2-1);
    `SHIFTVEC_(_q, d_);
    `REG(q, _q, DELAY/2+1);
endmodule


`define FIFOAGENT_(fifo_, q_, d_, nmspc, WRDRIVER_=TRUE, RDDRIVER_=TRUE, WRMONITOR_=TRUE, RDMONITOR_=TRUE, ASSIGN_DINFO=TRUE) \
fifoagent #(.WRDRIVER(WRDRIVER_), .RDDRIVER(RDDRIVER_), \
            .WRMONITOR(WRMONITOR_), .RDMONITOR(RDMONITOR_)) \
nmspc``_fifoagent_u (.fifo(fifo_), .q(q_), .d(d_));

`define FIFOAGENT(fifo, q, d, WRDRIVER=TRUE, RDDRIVER=TRUE) \
`FIFOAGENT_(fifo, q, d, fifo, WRDRIVER, RDDRIVER, WRDRIVER, RDDRIVER)

module fifoagent import globals::*;
    // A fifobus driver & monitor
    // It supports fifos with rd/wr clocks
    // and can be customized to drive and/or monitor write and/or read logic
    #(WRDRIVER=TRUE, RDDRIVER=TRUE,
      WRMONITOR=WRDRIVER, RDMONITOR=RDDRIVER,
      ASSIGN_DINFO=TRUE)
    (fifobus fifo, output logic q, input logic d);
    logic resetn; assign resetn = fifo.resetn;
    localparam TOTAL_CLKS = 2;
    localparam WRCLK = 0;
    localparam RDCLK = 1;
    typedef fifo.D D;
    logic [TOTAL_CLKS-1:0] _q;
    D _d_wrclk;
    logic                  _d_rdclk;
    if (WRDRIVER) begin
        `DRIVER_(_d_wrclk, d, dwrclk, fifo.wrclk);
    end
    if (RDDRIVER) begin
        `DRIVER_(_d_rdclk, d, drdclk, fifo.rdclk);
    end
    always_comb begin
        if (RDDRIVER)
            fifo.rdreq = _d_rdclk;
        if (WRDRIVER) begin
            fifo.wrreq = _d_wrclk;
            fifo.d.value = _d_wrclk;
        end
        if (ASSIGN_DINFO)
            fifo.d.info_master.value = _d_wrclk;
    end
    if (RDMONITOR) begin
        `MONITOR_(_q[RDCLK], {fifo.q.value, fifo.q.info, fifo.empty,
                              fifo.almost_empty, fifo.rdready, fifo.rdready2,
                              fifo.rdready2},  // to make even # of bits
                  qrdclk, fifo.rdclk);
    end
    if (WRMONITOR) begin
        `MONITOR_(_q[WRCLK], {fifo.full, fifo.half_full}, qwrclk, fifo.wrclk);
    end
    assign q = ^_q;
endmodule
