`include "../top/define.svh"


module mac_array import globals::*;
    // io shapes: vector q, vector alpha_vec, scalar alpha, matrix amat,
    // matrix bmat
    #(`IMPORT_ARITH)
    (output Chainivec q,
     output Info qinfo,
     output Chain alpha,
     input  AlphaJVec alpha_vec,
            interface amat, bmat,
     input  Info amatinfo, bmatinfo,
     logic  clk, resetn);
    matrix #(SZI_FIP, SZJ_PE, CHAIN_WIDTH, JMASTER) res_mat(.*);
    localparam QDELAY = 2;
    localparam DELAY1 = 1;
    localparam MODULE_LATENCY
               = DELAY1 + SZJ_PE - 1 + QDELAY;
    `REG(q, res_mat.right_vec[SZI-1:0], QDELAY);
    `REG(qinfo, amatinfo, MODULE_LATENCY);
    if (FIP_METHOD > BASELINE) begin
        `REG3(alpha, alpha_value, res_mat.right_vec[SZI_FIP-1], QDELAY);
    end
    wire [SZI_FIP-1:0][SZJ_PE-1:0][63:0] dsp_chainout;
    `FOR(genvar, I, SZI_FIP) begin : gi `FOR(genvar, J, SZJ_PE) begin : gj
        PeA a; PeB b; Chain res;
        Chain chainin, chainout;
        localparam             CHAIN_IN = (J < SZJ_PE-1);
        localparam             CHAIN_OUT = (J > 0);
        X[1:0] x;
        Y[1:0] y0, y1;
        X[PE_INPUT_DEPTH-1:0] _a;
        Y[PE_INPUT_DEPTH-1:0] _b;
        PeA a_;
        PeB b_;
        `FOR (genvar, I, PE_INPUT_DEPTH) begin
            `SIGNED(assign _a[I] =, A_SIGNED, a_[I]);
            `SIGNED(assign _b[I] =, B_SIGNED, b_[I]);
        end
        `REG(a_, a, 0);
        `REG(b_, b, 0);
        if (FIP_METHOD == FFIP) begin
            `SIGNED(assign x[0] =, A_SIGNED, a_[0]);
            `SIGNED(assign y0[0] =, A_SIGNED, a_[1]);
            `SIGNED(assign x[1] =, A_SIGNED, a_[2]);
            `SIGNED(assign y0[1] =, A_SIGNED, a_[3]);
        end else if (FIP_METHOD == FIP) begin
            `SIGNED(assign x[0] =, B_SIGNED,  _a[0] + _b[1]);
            `SIGNED(assign y0[0] =, B_SIGNED, _a[1] + _b[0]);
            `SIGNED(assign x[1] =, B_SIGNED,  _a[2] + _b[3]);
            `SIGNED(assign y0[1] =, B_SIGNED, _a[3] + _b[2]);
        end else begin
            `SIGNED(assign x[0] =, A_SIGNED,  _a[0]);
            `SIGNED(assign y0[0] =, B_SIGNED, _b[0]);
            `SIGNED(assign x[1] =, A_SIGNED,  _a[1]);
            `SIGNED(assign y0[1] =, B_SIGNED, _b[1]);
        end
        assign y1 = '0;
        X ax, bx;
        Y ay, by;
        always_comb begin
            ax = x[0];
            ay = y0[0];
            bx = x[1];
            by = y0[1];
        end
        X ax_, bx_, ayz_, byz_;
        Chain _res;
        Chain chainin_;
        Chain _res_d, res_d;
        assign ax_ =  ax; assign bx_ =  bx;
        assign ayz_ = ay; assign byz_ = by;
        if (CHAIN_IN) begin
                dsp_chainin
        `include  "dsp_chainin_inst.sv"
        end else begin
                dsp_nochainin
        `include  "dsp_nochainin_inst.sv"
        end
        assign res_mat.jvecs[I][J] = res;
        `FOR (genvar, INPUT, PE_INPUT_DEPTH) begin : ginput
        `define VEC_IX J*PE_INPUT_DEPTH + INPUT
            if ((FIP_METHOD == BASELINE) || (I < (SZI_FIP-1))) begin
                if (FIP_METHOD == FFIP) begin
                    assign a[INPUT] = (amat.jvecs[I][`VEC_IX]);
                    assign b[INPUT] = 'x;
                end else begin
                    `SIGNED(assign a[INPUT] =, A_SIGNED,
                            amat.jvecs[I][`VEC_IX]);
                    `SIGNED(assign b[INPUT] =, B_SIGNED,
                            bmat.jvecs[I][`VEC_IX]);
                end
            end else begin
                `SIGNED(assign a[INPUT] =, A_SIGNED, alpha_vec[J][INPUT]);
                assign b[INPUT] = '0;
            end
        `undef VEC_IX
        end
    end end // I J
    `FOR(genvar, I, SZI_FIP) begin `FOR(genvar, J, SZJ_PE) begin
        localparam CHAIN_IN = (J < SZJ_PE-1);
        if (CHAIN_IN) assign gi[I].gj[J].chainin = gi[I].gj[J+1].chainout;
        else assign gi[I].gj[J].chainin = '0;
    end end // I J
endmodule
