`include "../top/define.svh"


`define IMPORT_UTILS_PKG \
typedef logic [WIDTH-1:0]            Scalar; \
typedef Scalar [DEPTH-1:0] Vec;


module dut import globals::*;
    #(`IMPORT_TOP, type TST=struct{logic en;})
    (input logic clk, resetn);
    localparam DEPTH = 8;
    localparam WIDTH = 8;
    `IMPORT_UTILS_PKG;
    duts duts(.clk, .resetn);
    // dram dram_u(.clk, .resetn);
    //     pe_duts pe_duts(.clk, .resetn);
    //     data #(Vec) dff_d(.*);
    //     data #(Vec) dff_q(.*);
    //     dff dff_u (.q(dff_q), .d(dff_d));
    //     shift_reg dff_info_u (.q(dff_q.info_master), .d(dff_d.info_slave));

    //     shiftvec_latencies shiftvec_latencies(.clk, .resetn);
    //     shift_reg_latency shift_reg_latency(.clk, .resetn);

    //     data #(Vec) add_shiftvec_d(.*);
    //     data #(Vec) add_shiftvec_q(.*);
    //     add_shiftvec add_shiftvec_u (.q(add_shiftvec_q), .d(add_shiftvec_d));

    //     data #(Vec) add_vec_d(.*);
    //     data #(Vec) add_vec_q(.*);
    //     data #(Vec) add_vec_x(.*);
    //     add_vec add_vec_u (.q(add_vec_q), .d(add_vec_d), .x(add_vec_x));

    //     data #(Scalar) double_vecbuf_d(.*);
    //     data #(Vec) double_vecbuf_q(.*);
    //     logic [1:0] double_vecbuf_en;
    //     double_vecbuf #(DEPTH, WIDTH) double_vecbuf_u
    //         (.q(double_vecbuf_q), .d(double_vecbuf_d), .en(double_vecbuf_en));

    //     data #(Vec) triangle_buf_d(.*);
    //     data #(Vec) triangle_buf_q(.*);
    //     triangle_buf #(.SLOPE(-1)) triangle_buf_u
    //         (.q(triangle_buf_q), .d(triangle_buf_d));
endmodule


module dram0 import globals::*;
    #(type Q=Dram::Q, D=Q, integer DEPTH=Dram::DEPTH,
     BURST_COUNT=1, RANGE=16)
    // #(type Q=logic [7:0], D=Q, integer DEPTH=Dram::DEPTH,
      // BURST_COUNT=Dram::BURST_COUNT, RANGE=DEPTH)
    (input logic clk, resetn);
    sprambus #(.Q(Q), .DEPTH(DEPTH),
               .USE_RDWR_ADDRESSES(FALSE)) dram(.*);
    emif_phy_bus dramphy (.pll_ref_clk(clk));
    mem_test #(.Q(Q), .D(D), .DEPTH(DEPTH),
               .BURST_COUNT(BURST_COUNT)) mem_test_u
        (.mem(dram), .clk, .resetn);
    dram_emif_fifo  #(.Q(Q), .D(D), .DEPTH(DEPTH),
                      .BURST_COUNT(BURST_COUNT)) weight_dram_u
        (.master(dram), .slave(dramphy));
endmodule


module dram import globals::*;
    #(`IMPORT_ARITH, type Q=Weightvec, D=Q, integer DEPTH=Dram::DEPTH,
      RANGE=16)
    // #(type Q=logic [7:0], D=Q, integer DEPTH=Dram::DEPTH,
    // BURST_COUNT=Dram::BURST_COUNT, RANGE=DEPTH)
    (input logic clk, clk2, resetn);
    fifobus #(.Q(Q), .DEPTH(DEPTH)) clka_dram(.clk(clk), .resetn);
    fifobus #(.Q(Q), .DEPTH(DEPTH)) clkb_dram(.clk(clk2), .resetn);
    `IPFIFO(clkb_dram);
    fifo_mem_test #(.Q(Q), .D(D), .DEPTH(DEPTH),
               .BURST_COUNT(BURST_COUNT)) mem_test_u
        (.mem(clka_dram), .clk, .resetn);

    clock_crossing_fifobus_interconnect
        #() clock_crossing_fifobus_interconnect_u
            (.clka_fifo(clka_dram), .clkb_fifo(clkb_dram),
             .clka(clk), .clkb(clkb_dram.clk), .resetn);
endmodule


module pe_duts import globals::*;
    #(`IMPORT_TOP)
    (input logic clk, resetn);
    for (genvar FIP_METHOD_=BASELINE; FIP_METHOD_<=FFIP; FIP_METHOD_++) begin
        localparam COVER_PARAM_NAME = "FIP_METHOD_";  // for sim
        pe_dut #(`EXPORT_TOP_(FIP_METHOD_)) pe_dut(.*);
    end
endmodule


module duts import globals::*;
    #(`IMPORT_TOP)
    (input logic clk, resetn);
    // for (genvar DUT_=0; DUT_<1; DUT_++) begin  // mxu
    // for (genvar DUT_=1; DUT_<2; DUT_++) begin  // gemm
    // for (genvar DUT_=2; DUT_<3; DUT_++) begin  // post_gemm
    // for (genvar DUT_=3; DUT_<4; DUT_++) begin  // arith
    // for (genvar DUT_=4; DUT_<5; DUT_++) begin  // instruc
    for (genvar DUT_=5; DUT_<6; DUT_++) begin  // top
        // for (genvar DUT_=1; DUT_<4; DUT_+=2) begin  // custom
        // for (genvar DUT_=0; DUT_<4; DUT_++) begin  // all
        localparam COVER_PARAM_NAME = "DUT_";  // for sim
        // for (genvar FIP_METHOD_=FIP; FIP_METHOD_<=FFIP; FIP_METHOD_++) begin
        // for (genvar FIP_METHOD_=FFIP; FIP_METHOD_<=FFIP; FIP_METHOD_++) begin
        // for (genvar FIP_METHOD_=FIP; FIP_METHOD_<=FIP; FIP_METHOD_++) begin
        // for (genvar FIP_METHOD_=BASELINE; FIP_METHOD_<=BASELINE; FIP_METHOD_++) begin
        for (genvar FIP_METHOD__=BASELINE; FIP_METHOD__<=BASELINE; FIP_METHOD__++) begin
            // localparam FIP_METHOD_ = FFIP;
            // localparam FIP_METHOD_ = FIP;
            // localparam FIP_METHOD_ = BASELINE;
            localparam FIP_METHOD_ = FIP_METHOD;
            // for (genvar FIP_METHOD_=BASELINE; FIP_METHOD_<=FFIP; FIP_METHOD_++) begin
            // for (genvar FIP_METHOD_=FIP; FIP_METHOD_<=FFIP; FIP_METHOD_++) begin
            localparam COVER_PARAM_NAME = "FIP_METHOD_";  // for sim
            dut_select #(DUT_, `EXPORT_TOP_(FIP_METHOD_,,,,,,,))
            dut_select (.*);
            // for (genvar SZI_=SZI*1; SZI_<SZI*3; SZI_+=SZI) begin
            //     localparam COVER_PARAM_NAME = "SZI_";  // for sim
            //     dut_select #(DUT_, `EXPORT_TOP_(FIP_METHOD_,SZI_,,,,,,))
            //     dut_select(.*);
            // end
            // for (genvar SZJ_=SZJ*2; SZJ_<SZJ*3; SZJ_+=SZJ) begin
            //     localparam COVER_PARAM_NAME = "SZJ_";  // for sim
            //     dut_select #(DUT_, `EXPORT_TOP_(FIP_METHOD_,,SZJ_,,,,,))
            //     dut_select(.*);
            // end
            // for (genvar LAYERIO_SIGNED_=0; LAYERIO_SIGNED_<2; LAYERIO_SIGNED_++)
            // begin
            //     localparam COVER_PARAM_NAME = "LAYERIO_SIGNED_";  // for sim
            //     for (genvar WEIGHT_SIGNED_=0; WEIGHT_SIGNED_<2; WEIGHT_SIGNED_++)
            //     begin
            //         localparam COVER_PARAM_NAME = "WEIGHT_SIGNED_";  // for sim
            //         dut_select #(DUT_, `EXPORT_TOP_(FIP_METHOD_,,,,,,,
            //                                  LAYERIO_SIGNED, WEIGHT_SIGNED,,,))
            //         dut_select(.*);
            //     end
            // end
        end
    end
endmodule


module dut_select import globals::*;
    #(DUT, `IMPORT_ARITH)
    (input logic clk, resetn);
    for (genvar DUT_=DUT; DUT_==0; DUT_++)  begin : mxu
        mxu_dut #(`EXPORT_ARITH) dut(.*);
    end
    for (genvar DUT_=DUT; DUT_==1; DUT_++)  begin  : gemm
        gemm_dut #(`EXPORT_ARITH) dut(.*);
    end
    for (genvar DUT_=DUT; DUT_==2; DUT_++)  begin  : post_gemm
        post_gemm_dut #(`EXPORT_ARITH) dut(.*);
    end
    for (genvar DUT_=DUT; DUT_==3; DUT_++)  begin : arith
        arith_dut #(`EXPORT_ARITH) dut(.*);
    end
    for (genvar DUT_=DUT; DUT_==4; DUT_++)  begin : instruc
        instruc_dut #(`EXPORT_TOP) dut(.*);
    end
    for (genvar DUT_=DUT; DUT_==5; DUT_++)  begin : top
        // top #(`EXPORT_TOP) dut(.CLK_50M_FPGA(clk), .pb(resetn));
        top_dut #(`EXPORT_TOP) dut(.clk);
    end
endmodule


module mxu_dut import globals::*;
    #(`IMPORT_ARITH)
    (input logic clk, resetn);
    data #(Ajvec) a(.clk, .resetn);
    data #(Bjvec) b(.clk, .resetn);
    data #(Civec) c(.clk, .resetn);
    signal #(Info) bmat0_info(.clk, .resetn);
    signal #(Info) binfo(.clk, .resetn);
    data #(Ajvec) a_(.*);
    data #(Bjvec) b_(.*);
    data #(Ajvec) triangle_a(.clk, .resetn);
    data #(Bjvec) triangle_b(.clk, .resetn);
    data #(Civec) triangle_c(.clk, .resetn);
    `SHIFT_REG(a_, a, 0, a_);
    `SHIFT_REG(a_.info_master, a.info_slave, 0, a_info_delay);
    pad_tile_n_to_szm #(`EXPORT_ARITH) b_buf_u (.q(b_), .d(b), .*);
    triangle_buf #(.SLOPE(PE_INPUT_DEPTH)) a_triangle_u (.q(triangle_a),
                                                         .d(a_));
    triangle_buf #(.SLOPE(PE_INPUT_DEPTH)) b_triangle_u (.q(triangle_b),
                                                         .d(b_));
    triangle_buf #(.SLOPE(-1)) c_triangle_u (.q(c), .d(triangle_c));
    mxu #(`EXPORT_ARITH) mxu_u(.a(triangle_a), .b(triangle_b), .c(triangle_c),
                               .bmat0_info, .binfo, .*);
endmodule


module gemm_dut import globals::*;
    #(`IMPORT_ARITH)
    (input logic clk, resetn);
    import Instruc::HostData;
    import Tiler::Instruc;
    signal #(Info) bmat0_info(.clk, .resetn);
    signal #(Info) binfo(.clk, .resetn);
    fifobus #(.D(Civec), .Q(Ajvec)) layerio(.*);
    fifobus #(.D(HostData), .Q(Bjvec)) weight(.*);
    assign layerio.empty = '0;
    assign layerio.full = '0;
    assign weight.empty = '0;
    assign weight.full = '0;
    assign weight.rdreq = ~weight.empty;
    assign layerio.rdreq = bmat0_info.value.valid & ~layerio.empty;
    assign layerio.wrreq = layerio.d.info.valid & ~layerio.full;
    data #(Ajvec) a_(.*);
    data #(Bjvec) b_(.*);
    data #(Ajvec) triangle_a(.*);
    data #(Bjvec) triangle_b(.*);
    data #(Civec) triangle_c(.*);
    data #(Civec) gemm_q(.clk, .resetn);
    `SHIFT_REG(a_, layerio.q, 0, a_);
    `SHIFT_REG(a_.info_master, layerio.q.info_slave, 0, a_info_delay);
    pad_tile_n_to_szm #(`EXPORT_ARITH) b_buf_u (.q(b_), .d(weight.q), .*);
    triangle_buf #(.SLOPE(PE_INPUT_DEPTH)) a_triangle_u (.q(triangle_a),
                                                         .d(a_));
    triangle_buf #(.SLOPE(PE_INPUT_DEPTH)) b_triangle_u (.q(triangle_b),
                                                         .d(b_));
    `ASSIGN_DATA(triangle_c, gemm_q);
    triangle_buf #(.SLOPE(-1)) c_triangle_u (.q(layerio.d), .d(triangle_c));
    gemm #(`EXPORT_ARITH) gemm_u
        (.c(gemm_q), .a(triangle_a), .b(triangle_b), .bmat0_info, .binfo, .*);
    // arith_u #(`EXPORT_ARITH) gemm_u
    // (.(gemm_q), .a(triangle_a), .b(triangle_b), .bmat0_info, .binfo, .*);
    // assign bmat0_info = gemm_u.bmat0_info;
endmodule


module post_gemm_dut import globals::*;
    #(`IMPORT_ARITH) (input logic clk, resetn);
    data #(Civec) d(.clk, .resetn);
    data #(PostGemmParams) params(.clk, .resetn);
    data #(Civec) c(.clk, .resetn);
    data #(Civec) dut_d(.clk, .resetn);
    data #(Aivec) dut_q(.clk, .resetn);
    signal #(Info) params_loaded(.*);
    `SHIFT_REG__(params_loaded.value, params.info, SZI+1, info);
    triangle_buf #(.SLOPE(1)) d_triangle_u (.q(dut_d), .d(d));
    triangle_buf #(.SLOPE(-1)) q_triangle_u (.q(c), .d(dut_q));
    post_gemm #(`EXPORT_ARITH) post_gemm_u(.q(dut_q), .d(dut_d), .params, .*);
endmodule


module arith_dut import globals::*;
    #(`IMPORT_ARITH) (input logic clk, resetn);
    import Instruc::HostData;
    import Tiler::Instruc;
    logic start;
    fifobus #(.D(Aivec), .Q(Ajvec)) layerio(.*);
    fifobus #(.D(HostData), .Q(Bjvec)) weight(.*);
    fifobus #(.D(HostData), .Q(PostGemmParams)) post_gemm_params(.*);
    arith #(`EXPORT_ARITH) arith_u (.layerio, .weight, .post_gemm_params,
                                    .start, .*);
    assign start = 1'b1;
    assign layerio.empty = '0;
    assign layerio.full = '0;
    assign weight.empty = '0;
    assign weight.full = '0;
    signal #(Info) bmat0_info(.*);
    assign bmat0_info.value = arith_u.bmat0_info.value;
endmodule


module instruc_dut import globals::*;
    #(`IMPORT_TOP) (input clk, resetn);
    import Instruc::HostData;
    import Tiler::Instruc;
    //// interfaces ////
    fifobus #(.D(Layeriovec), .Q(HostData)) result(.clk, .resetn);
    fifobus #(.D(HostData), .Q(HostData)) host_instruc(.clk, .resetn);
    fifobus #(.D(HostData), .Q(Layeriovec)) layerio(.clk, .resetn);
    fifobus #(.D(HostData), .Q(Weightvec)) weight(.clk, .resetn);
    fifobus #(.D(HostData), .Q(PostGemmParams)) post_gemm_params
        (.clk, .resetn);
    fifobus #(.D(HostData), .Q(Instruc)) layerio_rd_instruc (.clk, .resetn);
    fifobus #(.D(HostData), .Q(Instruc)) layerio_wr_instruc (.clk, .resetn);
    fifobus #(.D(HostData), .Q(Instruc)) weight_rd_instruc (.clk, .resetn);
    fifobus #(.D(HostData), .Q(Instruc)) post_gemm_params_rd_instruc
        (.clk, .resetn);
    fifobus #(.D(HostData), .Q(HostData)) top_instruc(.clk, .resetn);
    //// modules ////
    instruc instruc_u (
                       .host_instruc,
                       .layerio,
                       .weight,
                       .post_gemm_params,
                       .layerio_rd_instruc,
                       .layerio_wr_instruc,
                       .weight_rd_instruc,
                       .post_gemm_params_rd_instruc,
                       .top_instruc
                       );
    `FIFO(host_instruc);
    `FIFO(layerio);
    `FIFO(weight);
    `FIFO(post_gemm_params);
    assign layerio.rdreq = 1'b0;
    assign weight.rdreq = 1'b0;
    assign post_gemm_params.rdreq = 1'b0;
    assign layerio_rd_instruc.rdreq = 1'b0;
    assign layerio_wr_instruc.rdreq = 1'b0;
    assign weight_rd_instruc.rdreq = 1'b0;
    assign post_gemm_params_rd_instruc.rdreq = 1'b0;
    assign top_instruc.rdreq = 1'b0;
endmodule
