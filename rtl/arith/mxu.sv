`include "../top/define.svh"
`include "double_vecbuf.sv"


// names with a, b represent data/signals related to the two matrices being
// multiplied, and c represents the output matrix. In other words:

// a is the featuremaps / layer input,
// b is the weights,
// c is data that will lead to the activations / layer output


module mxu import globals::*;
    // io shapes: jvector a, jvector b, ivector c
    #(`IMPORT_ARITH)
    (input Ajvec a, Info ainfo,
     Bjvec b, Info binfo,
     output      Chainivec c, Info cinfo,
     input logic clk, resetn);

    Ajvec __a; Info __ainfo;
    Bjvec __b; Info __binfo;
    Ajvec triangle_a; Info triangle_ainfo;
    Bjvec triangle_b; Info triangle_binfo;
    Ajvec a_; Info a_info;
    Chainivec _c; Info _cinfo;
    Chainivec __c; Info __cinfo;
    BMatJvec _b; Info _binfo;

    assign __a = a; assign __b = b;
    assign __ainfo = ainfo; assign __binfo = binfo;
    localparam   FMAX_DELAY0 = 0;
    triangle_buf2 #(.D(Ajvec), .SLOPE(PE_INPUT_DEPTH), .LATENCY(FMAX_DELAY0))
    a_triangle_u (.q(triangle_a), .qinfo(triangle_ainfo),
                  .d(__a), .dinfo(__ainfo), .clk, .resetn);
    triangle_buf2 #(.D(Bjvec), .SLOPE(PE_INPUT_DEPTH), .LATENCY(FMAX_DELAY0))
    b_triangle_u (.q(triangle_b), .qinfo(triangle_binfo),
                  .d(__b), .dinfo(__binfo), .clk, .resetn);
    matrix #(SZI, SZJ, AMAT_WIDTH) amat(.*);
    matrix #(SZI, SZJ, BMAT_WIDTH) bmat(.*);
    Chainivec pe_mat_q;
    Info pe_mat_qinfo;
    Chain alpha;
    AlphaJVec alpha_vec;
    localparam   A_DELAY = 1;
    `REG(a_, triangle_a, A_DELAY);
    `REG(a_info, triangle_ainfo, A_DELAY);
    triangle_buf2 #(.D(Chainivec), .SLOPE(-1)) d_u
        (.q(__c), .qinfo(__cinfo), .d(_c), .dinfo(_cinfo), .clk, .resetn);
    assign c = __c; assign cinfo = __cinfo;
    if (FIP_METHOD == FFIP) begin : model
        ffip_a_buf_and_preadders #(`EXPORT_ARITH) a_buf_u
            (.q(amat), .bmat, .d(a_), .dinfo(a_info),
             .alpha_vec, .clk, .resetn);
        y_generator #(`EXPORT_ARITH) b_buf_u0
            (.q(_b), .d(triangle_b), .qinfo(_binfo), .dinfo(triangle_binfo),
             .clk, .resetn);
        b_buf #(`EXPORT_ARITH) b_buf_u(.q(bmat), .d(_b),
                                       .dinfo(_binfo),
                                       .ainfo(triangle_ainfo),
                                       .qinfo(bmat.info_master.value),
                                       .clk, .resetn);
        alpha_add #(`EXPORT_ARITH) alpha_add_u
            (.q(_c), .qinfo(_cinfo), .d(pe_mat_q), .dinfo(pe_mat_qinfo),
             .alpha, .clk, .resetn);
    end else if (FIP_METHOD == FIP) begin : model
        a_buf #(`EXPORT_ARITH) a_buf_u(.q(amat), .d(a_),
                                       .dinfo(a_info),
                                       .qinfo(amat.info_master.value),
                                       .clk, .resetn);
        b_buf #(`EXPORT_ARITH) b_buf_u(.q(bmat), .d(triangle_b),
                                       .dinfo(triangle_binfo),
                                       .ainfo(triangle_ainfo),
                                       .qinfo(bmat.info_master.value),
                                       .clk, .resetn);
        alpha_add #(`EXPORT_ARITH) alpha_add_u
            (.q(_c), .qinfo(_cinfo), .d(pe_mat_q), .dinfo(pe_mat_qinfo),
             .alpha, .clk, .resetn);
        assign alpha_vec = amat.top_vec;
    end else begin : model
        a_buf #(`EXPORT_ARITH) a_buf_u(.q(amat), .d(a_),
                                       .dinfo(a_info),
                                       .qinfo(amat.info_master.value),
                                       .clk, .resetn);
        b_buf #(`EXPORT_ARITH) b_buf_u(.q(bmat), .d(triangle_b),
                                       .dinfo(triangle_binfo),
                                       .ainfo(triangle_ainfo),
                                       .qinfo(bmat.info_master.value),
                                       .clk, .resetn);
        assign _c = pe_mat_q;
        assign _cinfo = pe_mat_qinfo;
    end
    mac_array #(`EXPORT_ARITH) pe_mat_u
        (.q(pe_mat_q),
         .qinfo(pe_mat_qinfo),
         .amat(amat), .bmat(bmat),
         .amatinfo(amat.info), .bmatinfo(bmat.info),
         .alpha_vec, .alpha, .clk, .resetn);
endmodule


module ffip_a_buf_and_preadders import globals::*;
    #(`IMPORT_ARITH)
    (interface q, bmat,
     input Ajvec d, Info dinfo,
     output AlphaJVec alpha_vec,
     input logic clk, resetn);
    Ajvec _d;
    Ajvec alpha_d;
    always_ff @(posedge clk) `FOR (int, J, SZJ) begin
        `SIGNED(_d[J] <=, A_SIGNED, d[J]);
        alpha_d[J] <= _d[J];
    end
    assign alpha_vec = alpha_d;
    `REG3(q.info_master.value, info_delay, dinfo, 2);
`define a(i, j) q.ivecs[j][i]
`define b(i, j) bmat.ivecs[j][i]
    generate
        for (genvar K = 0; K < SZJ; K += 2) begin
            always_ff @(posedge clk) begin
                if (B_SIGNED) begin
                    `a(SZI-1, K) <= signed'(_d[K+1]) + signed'(`b(SZI-1, K));
                    `a(SZI-1, K+1) <= signed'(_d[K]) + signed'(`b(SZI-1, K+1));
                end else begin
                    `a(SZI-1, K) <= _d[K+1] + `b(SZI-1, K);
                    `a(SZI-1, K+1) <= _d[K] + `b(SZI-1, K+1);
                end
            end
        end
        for (genvar K = 0; K < SZJ; K += 1) begin
            for (genvar MN = SZI-2; MN >= 0; MN -= 1) begin
                always_ff @(posedge clk) begin
                    if (B_SIGNED) begin
                        `a(MN, K) <= signed'(`a(MN+1, K)) + signed'(`b(MN, K));
                    end else begin
                        `a(MN, K) <= `a(MN+1, K) + `b(MN, K);
                    end
                end
            end
        end
    endgenerate
`undef a
`undef b
endmodule


module y_generator import globals::*;
    #(`IMPORT_ARITH)
    (output BMatJvec q, Info qinfo,
     input Bjvec d, Info dinfo, input logic clk, resetn);
    Bjvec _d;
    `REG(_d, d);
    `REG(qinfo, dinfo);
    for (genvar J = 0; J < SZJ; J++) begin
        if (B_SIGNED) begin
            assign q[J] = (-signed'(d[J]) + signed'(_d[J]));
        end else begin
            assign q[J] = (-signed'({1'b0, d[J]}) + signed'({1'b0, _d[J]}));
        end
    end
endmodule


module a_buf import globals::*;
    // io shapes: matrix q, vector d, matrix bmat
    #(`IMPORT_ARITH)
    (interface q, output Info qinfo, input Ajvec d, Info dinfo,
     input logic clk, resetn);
    `REG(qinfo, dinfo, 1);
    for (genvar J = 0; J < SZJ; J++) begin : ivecs
        `SHIFTVEC2_(q.ivecs[J], qJ, d[J]);
    end
endmodule


module b_buf import globals::*;
    // io shapes: matrix qmat, vector d
    #(`IMPORT_ARITH)
    (interface q, output Info qinfo, input BMatJvec d,
     Info dinfo, input Info ainfo, input logic clk, resetn);
    logic [SZJ-1:0] envec0;
    logic [SZJ-1:0] envec1;
    logic [PE_INPUT_DEPTH-1:0] load0bus;
    assign load0bus = {PE_INPUT_DEPTH{dinfo.new_tile_k}};
    logic [PE_INPUT_DEPTH-1:0] load1bus;
    assign load1bus = {PE_INPUT_DEPTH{ainfo.new_tile_k}};
    `SHIFTVEC2(envec0, load0bus, TRUE);
    `SHIFTVEC2(envec1, load1bus, TRUE);
    localparam                 MODULE_LATENCY = 1;
    `SHIFT_REG_(qinfo, dinfo, MODULE_LATENCY);
    for (genvar J = 0; J < SZJ; J++) begin : ivecs
        double_vecbuf #(SZI, BMAT_WIDTH, BMAT_WIDTH) data_mat0_u
                    (.q(q.ivecs[J]), .d(d[J]),
                     .en({envec1[J], envec0[J]}),
                     .clk, .resetn);
    end
endmodule


module alpha_add import globals::*;
    #(`IMPORT_ARITH)
    (output Chainivec q, Info qinfo,
     input Chainivec d, Info dinfo,
     input Chain alpha, logic clk, resetn);
    // io shapes: vector q, vector d, scalar alpha
    Chainivec _d; Info _dinfo;
    Chainivec _q; Info _qinfo;
    Chain _alpha;
    `REG(_d, d);
    `REG(_dinfo, dinfo);
    `REG(_alpha, alpha);
    Chainivec right_alpha_vec;
    `SHIFTVEC2(right_alpha_vec, _alpha, TRUE);
    add_vec2 #(.Q(Chainivec), .D(Chainivec), .X(Chainivec), .SUB(TRUE)) add_u
        (.q(_q), .qinfo(_qinfo), .d(_d), .dinfo(_dinfo), .x(right_alpha_vec),
         .clk, .resetn);
    localparam MODULE_LATENCY = 2;
    localparam DELAY0 = 1;
    `REG(q, _q, DELAY0);
    `REG(qinfo, _qinfo, DELAY0);
endmodule
