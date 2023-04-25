`include "../top/define.svh"


`define IMPORT_DOUBLE_VECBUF \
integer DEPTH=8, WIDTH0=8, WIDTH1=WIDTH0,\
type Info = globals::Info,\
integer EN0_SHIFT_DEPTH = 2, \
type Data0Vec = logic [DEPTH-1:0][WIDTH0-1:0], \
type Data1Vec = logic [DEPTH-1:0][WIDTH1-1:0], \
type En1Vec = logic [DEPTH-1:0], type En0Vec = logic [DEPTH/2-1:0]
`define EXPORT_DOUBLE_VECBUF DEPTH, WIDTH0, WIDTH1, Info


module double_vecbuf import globals::*;
    #(`IMPORT_DOUBLE_VECBUF)
    (output            Data1Vec q,
     input logic [WIDTH0-1:0] d,
     input logic [1:0] en,
     input             Info dinfo, output Info qinfo,
     input logic       clk, resetn);
    localparam   MODULE_LATENCY = DEPTH * 2 + 1;
    localparam WIDTH = WIDTH1;  // for sim
    `REG(qinfo, dinfo, MODULE_LATENCY);

    // buf0
    localparam     D_BITS = EN0_SHIFT_DEPTH*WIDTH0;
    typedef logic [D_BITS-1:0] D;
    D data0_d;
    En0Vec envec0;
    Data0Vec data0_q;
    `SHIFTVEC2(data0_d, d, TRUE);
    `SHIFTVEC_ENVEC(data0_q, data0_d, envec0);

    // buf1
    Data1Vec data1_d;
    En1Vec envec1;
    assign data1_d = data0_q;
    `DFF_ENVEC(q, data1_d, envec1);
    `SHIFTVEC__(envec1, en[1], en1);

    // envec0 logic
    typedef logic
                 [DEPTH/2-1:0][EN0_SHIFT_DEPTH-1:0] RLShiftEn;
    typedef logic [EN0_SHIFT_DEPTH-1:0] En0D;
    RLShiftEn lshift;
    En0D rshift_d_, rshift_d;
    En0D rshift_d__;
    RLShiftEn rshift_q;
    logic [EN0_SHIFT_DEPTH-1:0]         lshift_qscalar;
    logic [EN0_SHIFT_DEPTH-1:0]         rshift_qscalar;
    En0D lshift_d;
    assign lshift_d = rshift_qscalar;
    `REG(lshift_qscalar, lshift_d, DEPTH/2);
`define EN_D_FLIPPED 2'b11 ^ rshift_d
`define DEPTH_DELAY (lshift_qscalar == rshift_d__) \
    && (rshift_d__ != 0)
    assign rshift_d__ = en[1] & en[0]? `EN_D_FLIPPED : rshift_d_;
    always_ff @(posedge clk or negedge resetn) if (~resetn)
    begin
        rshift_d <= 2'b01;
        rshift_d_ <= '0;
    end else begin
        if (en[0] & en[1])
            rshift_d_ <= `EN_D_FLIPPED;
        else if (en[0])
            rshift_d_ <= rshift_d;
        else if (`DEPTH_DELAY)
            rshift_d_ <= '0;
        if (en[1])
            rshift_d <= `EN_D_FLIPPED;
    end  // always_ff
    `SHIFTVEC2(rshift_q, rshift_d__, TRUE)
    `REG(rshift_qscalar, rshift_d__, DEPTH/2)
`undef EN_D_FLIPPED
`undef DEPTH_DELAY
    `SHIFTVEC2(lshift, lshift_d, TRUE, LEFT);
    for (genvar I=0; I!=DEPTH/2; I++)
        assign envec0[I] = |rshift_q[I]
                      & |(rshift_q[I] ^ lshift[I]);
endmodule
