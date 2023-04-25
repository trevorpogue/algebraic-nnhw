`include "../top/define.svh"


module dff import globals::*;
    // Q flip-flop with async resetn
    // io shapes: any q, any d (both same shape)
    #(integer RESET_VALUE=0)
    (interface q, d);
    logic clk, resetn; assign clk = q.clk; assign resetn = q.resetn;
    //
    // Variable types in interfaces must be assigned through modports
    // for synthesis. Next code block ensures this even if q is not a modport:
    // See https://sutherland-hdl.com/papers/2013-SNUG-SV_Synthesizable-SystemVerilog_paper.pdf page 32 for more detail.
    typedef q.VALUE VALUE;
    localparam DEPTH = $size(VALUE, 1);
    localparam WIDTH = $bits(VALUE) / DEPTH;
    typedef logic [DEPTH-1:0][WIDTH-1:0] Vec;
    Vec _q, _d;
    assign q.value = _q;
    assign _d = d.value;
    //
    always_ff @(posedge clk or negedge resetn)
      if (~resetn) _q <= RESET_VALUE;
      else begin
          _q <= _d;
      end
endmodule


module shiftvec import globals::*;
    // Shift register with q.value containing all the parallel output.
    // Will shift by however many bits are required to contain d.value's type.
    //
    // NO_DELAY=TRUE will make q.value's output appear the same as
    // it would with NO_DELAY=FALSE, but 1 cc earlier
    //
    // io shapes: vector q, scalar d
    #(NO_DELAY=FALSE, DIRECTION=RIGHT, RESET_VALUE=0)
    (interface q, d);
    logic clk, resetn; assign clk = q.clk; assign resetn = q.resetn;
    typedef q.VALUE Q;
    typedef d.VALUE D;
    localparam DWIDTH = $bits(D);
    localparam QWIDTH = $bits(Q);
    localparam DEPTH = QWIDTH/DWIDTH;
    localparam WIDTH = DWIDTH;
    typedef logic [DEPTH-1:0][WIDTH-1:0] Vec;
    data #(Vec) q_dff(.clk, .resetn);
    data #(Vec) d_dff(.clk, .resetn);
    `REG3(q_dff.value, q_dff, d_dff.value, 1, clk, RESET_VALUE, resetn);
`define _first_q_scalar (DIRECTION == RIGHT)? \
    q_dff.value[DEPTH-1] : q_dff.value[0];
`define _last_q_scalar (DIRECTION == RIGHT)? \
    q_dff.value[0] : q_dff.value[DEPTH-1];
    if (DIRECTION == RIGHT) begin
        assign d_dff.value = DEPTH > 1? {d.value, q_dff.value[DEPTH-1:1]}
                             : d.value;
        assign q.value = NO_DELAY? d_dff.value : q_dff.value;
    end else begin  // else left shift
        assign d_dff.value = {q_dff.value, d.value};
        assign q.value = NO_DELAY? d_dff.value : q_dff.value;
    end
    if (SIM) begin : sim
        logic [WIDTH-1:0] first_q_scalar, last_q_scalar;
        assign first_q_scalar = `_first_q_scalar;
        assign last_q_scalar = `_last_q_scalar;
    end
endmodule


module shift_reg import globals::*;
    // Shift register with classical non-parallel q.value output.
    // The depth of the shift register is determined by LATENCY

    // io shapes: scalar q, scalar d (both same size)
    #(parameter LATENCY=1, DIRECTION=RIGHT, RESET_VALUE=0)
    (interface q, d);
    logic clk, resetn; assign clk = q.clk; assign resetn = q.resetn;
    typedef q.VALUE VALUE;
    localparam DEPTH = LATENCY;
    localparam WIDTH = $bits(VALUE);
    if (LATENCY == 0) assign q.value = d.value;
    else begin
        logic clk, resetn; assign clk = q.clk; assign resetn = q.resetn;
        typedef logic [DEPTH-1:0][WIDTH-1:0] Vec;
        data #(Vec) q_vec(.clk, .resetn);
        shiftvec #(.RESET_VALUE(RESET_VALUE), .DIRECTION(DIRECTION))
        shiftvec(.d, .q(q_vec));
        assign q.value = (DIRECTION == RIGHT)? q_vec.value[0]
                         : q_vec.value[DEPTH-1];
    end
endmodule


module add_vec import globals::*;
    // perform addition on every element of two vectors, and register the
    // output D type expected to have two dimensions
    // set SUB to TRUE to do subtraction instead of addition

    // io shapes: vector q, vector d, vector x (all same size)
    #(parameter SUB=FALSE, USE_EN=FALSE)
    (data q, data d, x, input logic en, input logic enen);
    typedef q.VALUE VALUE;
    logic   clk, resetn; assign clk = q.clk; assign resetn = q.resetn;
    localparam DEPTH = $size(VALUE, 1);
    localparam WIDTH = $bits(VALUE) / DEPTH;
`define ADD_SUB(a, b) SUB? a - b : a + b
    typedef logic [DEPTH-1:0] Envec;
    Envec envec;
    Envec _envec;
    if (USE_EN) begin
        `SHIFTVEC_EN_(_envec, en, enen);
        assign envec = {enen, _envec[DEPTH-1:1]};
    end
    generate
        for (genvar I = 0; I != DEPTH; I++) begin
            always_ff @(posedge clk or negedge resetn) if (~resetn) begin
                q.value[I] <= '0;
                q.info_master.value <= '0;
            end else begin
                if (USE_EN)
                  // q.value[I] <= envec.value[DEPTH-1]? `ADD_SUB
                  q.value[I] <= envec[I]? `ADD_SUB
                                (d.value[I], x.value[I]) : d.value[I];
                else
                  q.value[I] <= `ADD_SUB(d.value[I], x.value[I]);
                q.info_master.value <= d.info_slave.value;
            end
        end
    endgenerate
`undef ADD_SUB
endmodule


module add_vec2 import globals::*;
    // perform addition on every element of two vectors, and register the
    // output D type expected to have two dimensions
    // set SUB to TRUE to do subtraction instead of addition

    // io shapes: vector q, vector d, vector x (all same size)
    #(type Q, D, X, integer SUB=FALSE)
    (output Q q, Info qinfo, input D d, Info dinfo, X x, logic en, clk, resetn);
    localparam DEPTH = $size(Q, 1);
    localparam WIDTH = $bits(Q) / DEPTH;
`define ADD_SUB(a, b) SUB? a - b : a + b
				Info _qinfo; Q _q;
				assign qinfo = _qinfo; assign q = _q;
    always_ff @(posedge clk or negedge resetn) if (~resetn) begin
        _qinfo <= '0;
    end else begin
        _qinfo <= dinfo;
    end
    generate
        for (genvar I = 0; I != DEPTH; I++) begin
            always_ff @(posedge clk or negedge resetn) if (~resetn) begin
                _q[I] <= '0;
            end else begin
                _q[I] <= `ADD_SUB(d[I], x[I]);
            end
        end
    endgenerate
`undef ADD_SUB
endmodule


module triangle_buf2 import globals::*;
		#(type D, integer SLOPE=1, LATENCY=1, EXTRA_INFO_LATENCY=0)
    // io shapes: vector q, vector d (both same size)
    (output D q, Info qinfo, input D d, Info dinfo, logic clk, resetn);
    localparam	DEPTH = $size(D, 1);
    localparam	WIDTH = $bits(D) / DEPTH;
    localparam	LATENCY_CONDITION = SLOPE > 0;
    localparam	MODULE_LATENCY = LATENCY_CONDITION? LATENCY + EXTRA_INFO_LATENCY
               : DEPTH - 1 + LATENCY + EXTRA_INFO_LATENCY;
    `REG(qinfo, dinfo, MODULE_LATENCY);
    for (genvar i=0; i!=DEPTH; i=i+1) begin : gen
        localparam REG_DEPTH = (SLOPE<0)? -i/SLOPE + LATENCY
                   : ((DEPTH-1-i)/SLOPE) + LATENCY;
        typedef logic [WIDTH-1:0]	Scalar;
        `REG3(q[i], qval, d[i], REG_DEPTH);
    end
endmodule


module triangle_buf #(parameter SLOPE=1, LATENCY=1, EXTRA_INFO_LATENCY=0)
    // io shapes: vector q, vector d (both same size)
    (interface q, interface d);
    logic   clk, resetn; assign clk = q.clk; assign resetn = q.resetn;
    typedef q.VALUE VALUE;
    localparam DEPTH = $size(VALUE, 1);
    localparam WIDTH = $bits(VALUE) / DEPTH;
    localparam LATENCY_CONDITION = SLOPE > 0;
    localparam MODULE_LATENCY = LATENCY_CONDITION? LATENCY + EXTRA_INFO_LATENCY
               : DEPTH - 1 + LATENCY + EXTRA_INFO_LATENCY;
    `REG3(q.info_master.value, qinfo, d.info, MODULE_LATENCY);
    for (genvar i=0; i!=DEPTH; i=i+1) begin : gen
        localparam REG_DEPTH = (SLOPE<0)? -i/SLOPE + LATENCY
                   : ((DEPTH-1-i)/SLOPE) + LATENCY;
        typedef logic [WIDTH-1:0] Scalar;
        `REG3(q.value[i], qval, d.value[i], REG_DEPTH);
    end
endmodule


module add_shiftvec import globals::*;
    #(RESET_VALUE=0, ASSIGN_INFO=TRUE) (interface q, d);
    // io shapes: vector q, vector d (both same size)
    logic   clk, resetn; assign clk = q.clk; assign resetn = q.resetn;
    typedef q.VALUE VALUE;
    localparam DEPTH = $size(VALUE, 1);
    localparam WIDTH = $bits(VALUE) / DEPTH;
    localparam SHIFT_DEPTH = 1;
    localparam MODULE_LATENCY = 1;
    if (ASSIGN_INFO) begin
        `REG3(q.info_master.value, qinfo, d.info, MODULE_LATENCY);
    end
    always_ff @(posedge clk) if (~resetn) begin
        for (int I = 0; I != DEPTH; I++) q.value[I] <= RESET_VALUE;
    end else begin
        q.value[DEPTH-1:DEPTH-1-SHIFT_DEPTH]
          <= (d.value[DEPTH-1:DEPTH-1-SHIFT_DEPTH]);
        for (int I = 0; I != DEPTH-SHIFT_DEPTH; I++)
          q.value[I] <= q.value[I+SHIFT_DEPTH] + (d.value[I]);
    end
endmodule


module dff_on_off import globals::*;
    #(LATENCY=1, WIDTH=1, PRIORITIZE_ON=TRUE, RESET_VAL=0)
    (input logic on, input logic off,
     output logic [WIDTH-1:0] q, input logic clk, input logic resetn);
    logic [WIDTH-1:0]         _q;
    always_ff @(posedge clk or negedge resetn) begin
        if (~resetn) _q <= RESET_VAL;
        else begin
            if (PRIORITIZE_ON) begin
                if (off)  _q <= '0;
                if (on) _q <= '1;
            end else begin
                if (on) _q <= '1;
                if (off)  _q <= '0;
            end
        end
    end
    if (LATENCY==0)
      if (PRIORITIZE_ON) begin
          assign q = ~resetn? '0 : on? '1 : off? '0 : _q;
      end else begin
          assign q = ~resetn? '0 : off? '0 : on? '1 : _q;
      end
    else begin
        `SHIFT_REG_(q, _q, LATENCY-1);
    end
endmodule


module ack
  #(LATENCY=1, WIDTH=1, PRIORITIZE_ON=globals::TRUE,
    type D = logic [WIDTH-1:0])
    (input logic ack, input D d,
     output D q, input logic clk, input logic resetn);
    D d_, q_;
    logic   ack_;
    `REG(d_, d);
    `POSEDGE__(en0, (d_ != d), 0);
    if (LATENCY==0) begin
        `REG(q_, q);
        `REG(ack_, ack);
        assign q = ~resetn? '0 : en0 | ack_? d : q_;
    end else begin
        `REG(q, en0 | ack? d : q, LATENCY);
    end
endmodule


module ackfifo import globals::*;
    #(LATENCY=0, type D = logic)
    (input logic ack, input D d,
     output logic ready, output D q, input logic clk, input logic resetn);
    fifobus #(.Q(D), .DEPTH(32),
              .RDREQ_AS_ACK(globals::TRUE)) fifo(.clk, .resetn);
    `FIFO(fifo);
    `REG3(fifo.d.value, fifo_d, d, LATENCY);
    `REG3(fifo.wrreq, fifo_wrreq, d, LATENCY);
    `REG3(fifo.rdreq, fifo_rdreq, ack, LATENCY);
    `REG(q, !fifo.empty, LATENCY);
    `REG(ready, !fifo.half_full, LATENCY);
endmodule


module posedge_ #(LATENCY=1)
    (input logic d, output logic q, input logic clk, input logic resetn);
    logic         d_;
    `REG(d_, d);
    `REG(q, d & !d_, LATENCY);
endmodule


module shiftvec_en
  #(WIDTH, DEPTH, type Vec = logic [DEPTH-1:0][WIDTH-1:0],
    type Scalar = logic [WIDTH-1:0])
    (output Vec q, input Scalar d, input logic en, clk, resetn);
    Vec d_dff, q_dff;
    assign d_dff = DEPTH > 1? {d, q_dff[DEPTH-1:1]} : d;
    assign q = q_dff;
    always_ff @(posedge clk or negedge resetn) if (~resetn) begin
        q_dff <= '0;
    end else if (en) begin
        q_dff <= d_dff;
    end
endmodule


module shiftvec_
  #(WIDTH, DEPTH, type Vec = logic [DEPTH-1:0][WIDTH-1:0],
    type Scalar = logic [WIDTH-1:0])
    (output Vec q, input Scalar d, input logic clk, input logic resetn);
    Vec d_dff, q_dff;
    assign d_dff = DEPTH > 1? {d, q_dff[DEPTH-1:1]} : d;
    assign q = q_dff;
    `REG(q_dff, d_dff);
endmodule


module reg_
  #(WIDTH, LATENCY, DEPTH = LATENCY, type Vec = logic [DEPTH-1:0][WIDTH-1:0],
    type Scalar = logic [WIDTH-1:0], int RESET_VALUE=0)
    (output Scalar q, input Scalar d, input logic clk, input logic resetn);
    Vec d_dff, q_dff;
    if (LATENCY == 0) assign q = d;
    else begin
        assign d_dff = LATENCY > 1? {d, q_dff[DEPTH-1:1]} : d;
        assign q = q_dff[0];
        `always_ff @(posedge clk or negedge resetn) if (~resetn) begin
            q_dff <= RESET_VALUE? '1 : '0;
        end else begin
            q_dff <= d_dff;
        end
    end
endmodule


module clock_crossing_data import globals::*;
    #(
      type A2B = struct packed {
        logic                              data;
        logic                              valid;
        },
      type B2A = struct packed {
        logic                              data;
        logic                              valid;
        },
      integer VALID_MEANS_NEW_DATA=FALSE,
      RDREQ_AS_ACK=FALSE,
      DEPTH_A2B = USE_SMALL_BUF? SMALL_BUF_DEPTH : 512,
      DEPTH_B2A = USE_SMALL_BUF? SMALL_BUF_DEPTH : 512,
      WRLATENCY = 2, RDLATENCY = 3,
      _A2B_BITS = $bits(A2B),
      _B2A_BITS = $bits(B2A),
      type _A2B = logic [_A2B_BITS-1:0],
      type _B2A = logic [_B2A_BITS-1:0],
      integer ZERODEFAULT=TRUE,
						SAME_CLK=FALSE)
    (
     input        _A2B clka_a2b,
     output       _A2B clkb_a2b,
     input        _B2A clkb_b2a,
     output       _B2A clka_b2a,
     output logic clka_wrready,
     output logic clkb_wrready,
     input logic  clka, clkb, resetn);
    logic									clka_half_full, clkb_half_full;
				if (SAME_CLK) begin
								assign clka_wrready = 1;
								assign clkb_wrready = 1;
        `REG(clkb_a2b, clka_a2b, 1, clka);
        `REG(clka_b2a, clkb_b2a, 1, clka);
				end else begin
								assign clka_wrready = !clka_half_full;
								assign clkb_wrready = !clkb_half_full;
        clock_crossing_data_oneway
          #(_A2B, VALID_MEANS_NEW_DATA,
            RDREQ_AS_ACK, DEPTH_A2B, WRLATENCY, RDLATENCY, ZERODEFAULT)
        a2b_fifo_u
          (.q(clkb_a2b), .d(clka_a2b),
           .half_full(clka_half_full),
           .wrclk(clka), .rdclk(clkb), .resetn);
        clock_crossing_data_oneway
          #(_B2A, VALID_MEANS_NEW_DATA, RDREQ_AS_ACK, DEPTH_B2A,
            WRLATENCY, RDLATENCY, ZERODEFAULT)
        b2a_fifo_u
          (.q(clka_b2a), .d(clkb_b2a),
           .half_full(clkb_half_full),
           .wrclk(clkb), .rdclk(clka), .resetn);
				end
endmodule


module clock_crossing_data_oneway import globals::*;
    #(type VALUE,
      integer VALID_MEANS_NEW_DATA=FALSE, // otherwise data is sampled every cc
      RDREQ_AS_ACK=FALSE, DEPTH = 8,
      WRLATENCY = 2, RDLATENCY = 3, ZERODEFAULT=TRUE)
    (input VALUE d, output VALUE q,
     output logic half_full,
     input logic  wrclk, rdclk, resetn);
    logic         clk; assign clk = wrclk;
    logic         fifo_qvalid;
    typedef VALUE VALUE_;
    VALUE_ fifo_q;
    VALUE_ _q_d, _q;
    VALUE_ fifo_d_;
    localparam    FMAX_DELAY0 = 0;
    localparam    RDDELAY2 = FMAX_DELAY0 + 1;  // tunable from 0 - inf
    localparam    DELAY0   = FMAX_DELAY0 + 1;  // tunable from 0 to 1
    localparam    DELAY1   = FMAX_DELAY0 + 1;  // tunable from 0 - inf
    localparam    DELAY2   = FMAX_DELAY0 + 1;  // only works for 0
    fifobus #(.Q(VALUE), .USE_RDWR_CLKS(TRUE)
              ,.RDLATENCY(RDDELAY2)
              ,.WRLATENCY(WRLATENCY)
              // not intended to be fed data faster than its reading rate
              ,.DEPTH(DEPTH)
              ) fifo(.clk, .resetn);
    logic         fifo_wrreq_d;
    `IPFIFO(fifo);
    `REG2_(fifo_d_, d, fifo_d_, 1, 0, wrclk);
    assign fifo_wrreq_d = VALID_MEANS_NEW_DATA? d[0] :
                          (d != fifo_d_) & d[0];
    `REG2_(fifo.wrreq, fifo_wrreq_d, fifo_wrreq, DELAY0, 0, wrclk);
    `REG2_(fifo.d.value, d, fifo_d_value, DELAY0, 0, wrclk);
    `REG2_(fifo.rdreq, !fifo.empty, fifo_rdreq, DELAY1, 0, rdclk);
    assign half_full = fifo.half_full;
    `ONOFF__(got_first_rdvalue, fifo.rdreq, '0, 1+DELAY2, rdclk);
    if (ZERODEFAULT) begin
        `REG2_(q, _q, q, 1, 0, rdclk);
    end else begin
        `REG2_(q, _q[0]? _q : q, q, 1, 0, rdclk);
    end
    `REG2_(_q, _q_d, _q, 1, 0, rdclk);
    `REG2_(fifo_q, fifo.q.value, fifo_q, DELAY2, 0, rdclk);
    `REG2_(fifo_qvalid, fifo.q.info.valid, fifo_qvalid, DELAY2, 0, rdclk);
    always_comb begin
        _q_d = '0;
        _q_d[0] = fifo_qvalid;
        if (RDREQ_AS_ACK) begin
            if (got_first_rdvalue)
              _q_d = fifo_q;
        end else if (VALID_MEANS_NEW_DATA) begin
            if (fifo_qvalid)
              _q_d = fifo_q;
        end else begin
            if (_q[0])
              _q_d = fifo_q;
        end
    end
    assign fifo.wrclk = wrclk; assign fifo.rdclk = rdclk;
endmodule


module clock_crossing_fifobus_interconnect import globals::*;
    #(
      type A2B = struct packed {
        logic                              start;
        },
      type B2A = struct packed {
        logic                              start;
        }, integer ASSIGN_CLKA_Q=TRUE)
    (fifobus clka_fifo, clkb_fifo,
     input A2B clka_a2b,
     output       A2B clkb_a2b,
     input        B2A clkb_b2a,
     output       B2A clka_b2a,
     output logic clka_wrready,
     output logic clkb_wrready,
     input logic  clka, clkb, resetn);
    typedef clka_fifo.Q QQ;
    typedef clka_fifo.D DD;
    localparam    DBITS = $bits(DD);
    localparam    QBITS = $bits(QQ);

    logic [1:0]   _clka_wrready, _clkb_wrready;
    assign clka_wrready = &_clka_wrready;
    assign clkb_wrready = &_clkb_wrready;
    typedef struct packed {
        logic [DBITS-1:0] d;
        Info dinfo;
        logic             wrreq;
        logic             rdreq;
        A2B extra;
        logic             valid;
    }_A2B;
    typedef struct        packed {
        logic [QBITS-1:0] q;
        Info qinfo;
        B2A extra;
        logic             valid;
    }_B2A0;
    typedef struct        packed {
        logic             full;
        logic             half_full;
        logic             empty;
        logic             rdready;
        logic             rdready2;
        logic             valid;
    }_B2A1;
    _A2B _clka_a2b, _clkb_a2b;
    _B2A0 _clka_b2a0, _clkb_b2a0;
    _B2A1 _clka_b2a1, _clkb_b2a1;
    always_comb begin
        //////////////////////////////////////////////////////////////
        // a2b

        _clka_a2b.valid = (clka_fifo.wrreq | clka_fifo.rdreq);

        _clka_a2b.wrreq = clka_fifo.wrreq;
        clkb_fifo.wrreq = _clkb_a2b.wrreq;
        _clka_a2b.rdreq = clka_fifo.rdreq;
        clkb_fifo.rdreq = _clkb_a2b.rdreq;

        _clka_a2b.d = clka_fifo.d.value;
        clkb_fifo.d.value = _clkb_a2b.d;

        _clka_a2b.extra = clka_a2b;
        clkb_a2b = _clkb_a2b.extra;

        //////////////////////////////////////////////////////////////
        // b2a

        _clkb_b2a0.q = clkb_fifo.q.value;
        _clkb_b2a0.qinfo = clkb_fifo.q.info;
        if (ASSIGN_CLKA_Q) begin
            clka_fifo.q.value = _clka_b2a0.q;
            clka_fifo.q.info_master.value = _clka_b2a0.qinfo;
        end

        _clkb_b2a1.empty = clkb_fifo.empty;
        clka_fifo.empty = _clka_b2a1.empty;
        _clkb_b2a1.full = clkb_fifo.full;
        clka_fifo.full = _clka_b2a1.full;
        _clkb_b2a1.half_full = clkb_fifo.half_full;
        clka_fifo.half_full = _clka_b2a1.half_full | !clka_wrready;
        _clkb_b2a1.rdready = clkb_fifo.rdready;
        clka_fifo.rdready = _clka_b2a1.rdready & clka_wrready;
        _clkb_b2a1.rdready2 = clkb_fifo.rdready2;
        clka_fifo.rdready2 = _clka_b2a1.rdready2 & clka_wrready;

        _clkb_b2a0.extra = clkb_b2a;
        clka_b2a = _clka_b2a0.extra;

        _clkb_b2a0.valid = 1;
        _clkb_b2a1.valid = 1;
    end
    clock_crossing_data
      #(.A2B(_A2B), .B2A(_B2A0), .VALID_MEANS_NEW_DATA(TRUE),
        .ZERODEFAULT(TRUE)) u0
        (.clka_a2b(_clka_a2b), .clkb_a2b(_clkb_a2b),
         .clka_b2a(_clka_b2a0), .clkb_b2a(_clkb_b2a0),
         .clka_wrready(_clka_wrready[0]), .clkb_wrready(_clkb_wrready[0]),
         .clka, .clkb, .resetn);
    clock_crossing_data
      #(.A2B(_A2B), .B2A(_B2A1), .VALID_MEANS_NEW_DATA(TRUE),
        .ZERODEFAULT(FALSE)) u1
        (.clka_a2b('0),
         .clka_b2a(_clka_b2a1), .clkb_b2a(_clkb_b2a1),
         .clka_wrready(_clka_wrready[1]), .clkb_wrready(_clkb_wrready[1]),
         .clka, .clkb, .resetn);
endmodule


module wordswap import globals::*;
    // Swap the word order of `d.value`.
    // Example: wordswap(64'h01234567,89ABEF == 32'h89ABEF,01234567
    #(DWIDTH=1, LATENCY=1,
      WORD_WIDTH=$bits(Instruc::HostData), type _Q = logic [DWIDTH-1:0])
    (output _Q q, input _Q d, logic clk, resetn);
    localparam SIZE = DWIDTH / WORD_WIDTH;
    typedef logic [SIZE-1:0][WORD_WIDTH-1:0] WordSwap;
    WordSwap d__;
    WordSwap d_;
    `REG3(d__, d__, d, LATENCY);
    `FOR(genvar, I, SIZE) assign d_[I] = d__[SIZE-I-1];
    assign q = d_;
endmodule
