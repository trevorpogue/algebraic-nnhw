// =======================================================
//  Written & Designed by Trevor Pogue
// ======================================================

`include "../../rtl/top/define.svh"
`include "../../rtl/top/utils.svh"
`include "../../rtl/top/synth_agents.svh"
// `timescale 1 ps / 1 ps


// module top import globals::*;
module fifo_dgtq_faster_rdclk_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din, logic [TOTAL_DUTS-1:0] clks, resetn);
    logic clk; assign clk = clks[0];
    localparam CLKDIV = LAYERIOMEM_CLK_DIV;
    localparam type D = logic [CLKDIV-1:0][SZI-1:0][A_WIDTH-1:0];
    // dut inputs
    // dut outputs
    // dut interfaces
    fifobus #(.Q(Layeriovec) ,.D(D) ,.USE_RDWR_CLKS(TRUE)
              ,.RDREQ_AS_ACK(TRUE)
              ,.DEPTH(8)
              ,.RDLATENCY(3)
              ,.WRLATENCY(3)) fifo(.clk, .resetn);
    assign fifo.wrclk = clk;
    assign fifo.rdclk = clk;
    // synth
    `FIFOAGENT(fifo, qout, din);
    // dut
    _fifo_dgtq_faster_rdclk qfifo_u(fifo);
endmodule


// module top import globals::*;
module weight_tiler_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_CLKS = 1, TOTAL_DUTS = 2)
    (output logic qout, input logic din, logic [TOTAL_CLKS-1:0] clks, resetn);
    logic clk; assign clk = clks[0];
    localparam type Q = Weightvec;
    localparam DBITS = 1;
    logic [TOTAL_DUTS-1:0] q;
    logic [DBITS-1:0]      d;
    `DRIVER(d, din);
    // dut inputs
    // dut interfaces
    `INSTRUC_FIFOBUS(master, Q);
    assign master.wrclk = clk;
    assign master.rdclk = clk;
    fifobus #(.Q(Tiler::DIGIT), .DEPTH(INSTRUC_FIFOS_DEPTH),
              .USE_RDWR_CLKS(TRUE)) rd_instruc(.clk, .resetn);
    assign rd_instruc.wrclk = clk;
    assign rd_instruc.rdclk = clk;
    `IPFIFO(rd_instruc);
    // dut outputs
    // synth
    `FIFOAGENT(master, q[0], din);
    `FIFOAGENT(rd_instruc, q[1], din, TRUE, FALSE);
    assign qout = ^q;
    // dut
    localparam             POST_GEMM_PARAMS_MEM_DEPTH
                           = PGP_MEM_SIZE / Instruc::POST_GEMM_PARAMS_WORD_WIDTH;
    sprambus #(.Q(PostGemmParams), .DEPTH(POST_GEMM_PARAMS_MEM_DEPTH),
               .USE_RDWR_ADDRESSES(TRUE)) srambus (.clk, .resetn);
    spram #() sram_u (srambus);
    weight_tiler #(Tiler::READER, POST_GEMM_PARAMS, 0,
                   POST_GEMM_PARAMS_MEM_DEPTH, `EXPORT_ARITH)
    reader_u (.master,
              .slave(srambus),
              .instruc(rd_instruc),
              .start(d[0]),
              .topclk(clk),
              .memclk(clk),
              .resetn);
endmodule


// module top import globals::*;
module test_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din,
     pooling_clk, padding_clk, clk2, clk, resetn);
    localparam type Q = Layeriovec;
    // localparam DBITS = $bits(LayerParams);
    // localparam DBITS = 512;
    localparam DBITS = 19*16;

    localparam TOTAL_FIFOS = 1;
    logic [TOTAL_DUTS+TOTAL_FIFOS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0]  d;
    fifobus #(.Q(Layeriovec), .DEPTH(4)) layerio(.clk, .resetn);
    `FIFO(layerio);
    `DRIVER_(d, din, d0, clk);
    `MONITOR_(q[0], d, qdut);
    `FIFOAGENT_(layerio, q[1], din, layerio, TRUE, TRUE, TRUE, TRUE, TRUE);
    assign qout = ^q;
endmodule


// module top import globals::*;
module mxu_and_quantization_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 2)
    (output logic qout, input logic din, clk2, clk, resetn);
    localparam type Q = PostGemmParams;
    localparam DBITS = $bits(PostGemmParams)+$bits(Civec);
    logic [TOTAL_DUTS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0] d;
    logic                             c_will_be_valid_soon, ready_for_a_tile;

    data #(Q) qdata(.clk, .resetn);
    data #(Q) ddata(.clk, .resetn);
    data #(Q) params(.clk, .resetn);
    `MONITOR_(q[0], {qdata.value, qdata.info}, qdut)
    `DRIVER_(d[0], din, d0, clk);
    assign ddata.value = d[0];
    assign ddata.info_master.value = d[0]>>1;
    assign params.value = d[0]>>2;
    assign params.info_master.value = d[0]>>3;
    assign qout = ^q;
    quantization #(`EXPORT_ARITH) quantization_u
        (
         // interfaces
         .d(ddata), .params, .q(qdata),
         // outputs
         // inputs
         .clk, .resetn);



    logic                             ready_for_a_tile2;
    data #(Layeriovec) a2(.clk(clk2), .resetn);
    data #(Weightvec) b2(.clk(clk2), .resetn);
    data #(Civec) c2(.clk(clk2), .resetn);
    `MONITOR_(q[1], {ready_for_a_tile2, c2.value, c2.info}, qdut1, clk2)
    `DRIVER_(d[1], din, d1, clk2);
    assign a2.value = d[1];
    assign a2.info_master.value = d[1]>>1;
    assign b2.value = d[1]>>2;
    assign b2.info_master.value = d[1]>>3;
    mxu #(`EXPORT_ARITH) mxu_u
        (
         // interfaces
         .a(a2), .b(b2), .c(c2),
         // outputs
         .ready_for_a_tile(ready_for_a_tile2),
         // inputs
         .clk(clk2), .resetn);
endmodule


// module top import globals::*;
module gemm_and_mxu_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 2)
    (output logic qout, input logic din, clk2, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Weightvec);
    logic [TOTAL_DUTS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0] d;
    logic                             c_will_be_valid_soon, ready_for_a_tile;
    data #(Layeriovec) a(.clk, .resetn);
    data #(Weightvec) b(.clk, .resetn);
    data #(Civec) c(.clk, .resetn);
    `MONITOR_(q[0], {c_will_be_valid_soon, ready_for_a_tile,
                     c.value, c.info}, qdut0)
    `DRIVER_(d[0], din, d0, clk);
    assign a.value = d[0];
    assign a.info_master.value = d[0]>>1;
    assign b.value = d[0]>>2;
    assign b.info_master.value = d[0]>>3;
    assign qout = ^q;
    gemm #(`EXPORT_ARITH) gemm_u
        (
         // interfaces
         .a, .b, .c,
         // outputs
         .c_will_be_valid_soon,
         .ready_for_a_tile,
         // inputs
         .clk, .resetn);
    logic                             ready_for_a_tile2;
    data #(Layeriovec) a2(.clk(clk2), .resetn);
    data #(Weightvec) b2(.clk(clk2), .resetn);
    data #(Civec) c2(.clk(clk2), .resetn);
    `MONITOR_(q[1], {ready_for_a_tile2, c2.value, c2.info}, qdut1, clk2)
    `DRIVER_(d[1], din, d1, clk2);
    assign a2.value = d[1];
    assign a2.info_master.value = d[1]>>1;
    assign b2.value = d[1]>>2;
    assign b2.info_master.value = d[1]>>3;
    mxu #(`EXPORT_ARITH) mxu_u
        (
         // interfaces
         .a(a2), .b(b2), .c(c2),
         // outputs
         .ready_for_a_tile(ready_for_a_tile2),
         // inputs
         .clk(clk2), .resetn);
endmodule


// module top import globals::*;
module accum_mem_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din, weightmem_clk, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Layeriovec);
    logic [TOTAL_DUTS-1:0] q;
    logic [DBITS-1:0]      d;
    logic                  c_will_be_valid_soon;
    data #(Q) qdata(.clk, .resetn);
    data #(Q) ddata(.clk, .resetn);
    `MONITOR_(q[0], {c_will_be_valid_soon, qdata.value, qdata.info}, qdut)
    `DRIVER(d, din);
    assign ddata.value = d;
    assign ddata.info_master.value = d;
    assign qout = ^q;
    accum_mem #(`EXPORT_ARITH) accum_mem_u
        (
         // interfaces
         .q(qdata), .d(ddata),
         // outputs
         .c_will_be_valid_soon,
         // inputs
         .clk, .resetn);
endmodule


// module top import globals::*;
module mxu_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din, weightmem_clk, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Weightvec);
    logic [TOTAL_DUTS-1:0] q;
    logic [DBITS-1:0]      d;
    logic                  ready_for_a_tile;
    data #(Layeriovec) a(.clk, .resetn);
    data #(Weightvec) b(.clk, .resetn);
    data #(Civec) c(.clk, .resetn);
    `MONITOR_(q[0], {ready_for_a_tile, c.value, c.info}, qdut)
    `DRIVER(d, din);
    assign a.value = d;
    assign a.info_master.value = d>>1;
    assign b.value = d>>2;
    assign b.info_master.value = d>>3;
    assign qout = ^q;
    mxu #(`EXPORT_ARITH) gemm_u
        (
         // interfaces
         .q(qdata), .d(ddata),
         // outputs
         .ready_for_a_tile,
         // inputs
         .clk, .resetn);
endmodule


// module top import globals::*;
module padding_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din, weightmem_clk, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Layeriovec);
    logic [TOTAL_DUTS-1:0] q;
    logic [DBITS-1:0]      d;
    logic                  ready;
    data #(Q) qdata(.clk, .resetn);
    data #(Q) ddata(.clk, .resetn);
    `MONITOR_(q[0], {ready, qdata.value, qdata.info}, qdut)
    `DRIVER(d, din);
    assign ddata.value = d;
    assign ddata.info_master.value = d;
    assign qout = ^q;
    padding #(`EXPORT_ARITH) padding_u
        (
         // interfaces
         .q(qdata), .d(ddata),
         // outputs
         .ready,
         // inputs
         .padding(d),
         .size_w(d>>1),
         .size_h(d>>2),
         .layer_params_valid(d>>3),
         .slowclk(weightmem_clk),
         .topclk(clk), .resetn);
endmodule


// module top import globals::*;
module pad_tile_n_to_szm_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din, weightmem_clk, clk, resetn);
    localparam type Q = Weightvec;
    localparam DBITS = $bits(LayerParams);
    logic [TOTAL_DUTS-1:0] q;
    logic [DBITS-1:0]      d;
    logic                  padded_tile_n_to_szm;
    data #(Q) qdata(.clk, .resetn);
    data #(Q) ddata(.clk, .resetn);
    `MONITOR_(q[0], {padded_tile_n_to_szm, qdata.value, qdata.info}, qdut)
    `DRIVER(d, din);
    assign ddata.value = d;
    assign ddata.info_master.value = d;
    assign qout = ^q;
    pad_tile_n_to_szm #(`EXPORT_ARITH) pad_tile_n_to_szm_u
        (
         // interfaces
         .q(qdata), .d(ddata),
         // outputs
         .padded_tile_n_to_szm,
         // inputs
         .layer_params(d),
         .start_tile_rd(d),
         .clk, .resetn);
endmodule


// module top import globals::*;
module post_gemm_and_mxu_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 2)
    (output logic qout, input logic din,
     pooling_clk, padding_clk, quantization_clk, clk2, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Weightvec);
    logic [TOTAL_DUTS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0] d;
    logic                             ready;
    data #(Civec) ddata(.clk, .resetn);
    data #(PostGemmParams) params(.clk, .resetn);
    data #(Aivec) qdata(.clk, .resetn);
    `MONITOR_(q[0], {ready, qdata.value, qdata.info}, qdut0)
    `DRIVER_(d[0], din, d0, clk);
    assign ddata.value = d[0];
    assign ddata.info_master.value = d[0]>>1;
    assign params.value = d[0]>>2;
    assign params.info_master.value = d[0]>>3;
    assign qout = ^q;
    post_gemm #(`EXPORT_ARITH) post_gemm_u
        (
         // interfaces
         .q(qdata), .d(ddata), .params,
         // outputs
         .ready,
         // inputs
         .layer_params(d),
         .top_ready(d),
         .pooling_clk, .padding_clk, .quantization_clk,
         .clk, .resetn);
    logic                             ready_for_a_tile2;
    data #(Layeriovec) a2(.clk(clk2), .resetn);
    data #(Weightvec) b2(.clk(clk2), .resetn);
    data #(Civec) c2(.clk(clk2), .resetn);
    `MONITOR_(q[1], {ready_for_a_tile2, c2.value, c2.info}, qdut1, clk2)
    `DRIVER_(d[1], din, d1, clk2);
    assign a2.value = d[1];
    assign a2.info_master.value = d[1]>>1;
    assign b2.value = d[1]>>2;
    assign b2.info_master.value = d[1]>>3;
    mxu #(`EXPORT_ARITH) mxu_u
        (
         // interfaces
         .a(a2), .b(b2), .c(c2),
         // outputs
         .ready_for_a_tile(ready_for_a_tile2),
         // inputs
         .clk(clk2), .resetn);
endmodule


// module top import globals::*;
module dram import globals::*;
    #(type Q=Dram::Q, D=Q, integer DEPTH=Dram::DEPTH,
      BURST_COUNT=1, RANGE=16)
    // #(type Q=logic [7:0], D=Q, integer DEPTH=Dram::DEPTH,
    // BURST_COUNT=Dram::BURST_COUNT, RANGE=DEPTH)
    (`include "ports.sv", output logic clk, input logic din, output logic qout);
    Q ammq;
    logic keep_synth;
    logic clk125;
    assign clk125 = CLK_ENET_FPGA_P;
    assign resetn = pb[0];
    // `MONITOR_(qout, {ammq, keep_synth}, qout);
    pll pll_u (
               .rst      (~pb[1]),
               .refclk   (clk125),
               .locked   (),

               .outclk_3 (clk)
               );
    emif_phy_bus dramphy
        (
         .pll_ref_clk (pll_ref_clk   ), //   input, width = 1,
         .oct_rzqin   (oct_rzqin     ), //   input, width = 1,
         .mem_ck      (mem_ck        ),	//  output, width = 1,
         .mem_ck_n    (mem_ck_n      ),	//  output, width = 1,
         .mem_a       (mem_a         ),	//  output, width = 17,
         .mem_act_n   (mem_act_n     ),	//  output, width = 1,
         .mem_ba      (mem_ba        ),	//  output, width = 2,
         .mem_bg      (mem_bg        ),	//  output, width = 1,
         .mem_cke     (mem_cke       ),	//  output, width = 1,
         .mem_cs_n    (mem_cs_n      ),	//  output, width = 1,
         .mem_odt     (mem_odt       ),	//  output, width = 1,
         .mem_reset_n (mem_reset_n   ),	//  output, width = 1,
         .mem_par     (mem_par       ),	//  output, width = 1,
         .mem_alert_n (mem_alert_n   ),	//   input, width = 1,
         .mem_dqs     (mem_dqs       ),	//   inout, width = 9,
         .mem_dqs_n   (mem_dqs_n     ),	//   inout, width = 9,
         .mem_dq      (mem_dq        ),	//   inout, width = 72
         .mem_dbi_n   (mem_dbi_n     )	//   inout, width = 9,
         );
    sprambus #(.Q(Q), .DEPTH(DEPTH),
               .USE_RDWR_ADDRESSES(FALSE)) dram(.*);
    dram_emif_fifo  #(.Q(Q), .D(D), .DEPTH(DEPTH),
                      .BURST_COUNT(BURST_COUNT)) weight_dram_u
        (.master(dram), .slave(dramphy)
         // ,.ammq(ammq)
         );
    mem_test #(.Q(Q), .D(D), .DEPTH(DEPTH),
               .BURST_COUNT(BURST_COUNT)) mem_test_u
        (.mem(dram),
         // .keep_synth,
         .clk, .resetn);
endmodule


// module top import globals::*;
module dram2 import globals::*;
    #(`IMPORT_ARITH, type Q=Weightvec, D=Q, integer DEPTH=32,
      RANGE=16)
    // #(type Q=logic [7:0], D=Q, integer DEPTH=Dram::DEPTH,
    // BURST_COUNT=Dram::BURST_COUNT, RANGE=DEPTH)
    (input CLK_ENET_FPGA_P,
     input wire [3:0] pb,
     output logic     clk, input logic din,
     output logic     qout);
    Q ammq;
    logic             keep_synth;
    logic             clk125;
    logic             weightmem_clk;
    assign clk125 = CLK_ENET_FPGA_P;
    assign resetn = pb[0];
    `MONITOR_(qout, {clka_dram.d.value}, qout);
    pll pll_u (
               .rst      (~pb[1]),
               .refclk   (clk125),
               .locked   (),
               .outclk_0 (clk),
               .outclk_3 (weightmem_clk)
               );

    fifobus #(.Q(Q), .DEPTH(DEPTH)) clka_dram(.clk(clk), .resetn);
    fifobus #(.Q(Q), .DEPTH(DEPTH)) clkb_dram(.clk(weightmem_clk), .resetn);
    `IPFIFO(clkb_dram);

    fifo_mem_test #(.Q(Q), .D(D), .DEPTH(DEPTH),
                    .BURST_COUNT(BURST_COUNT)) mem_test_u
        (.mem(clka_dram),
         // .keep_synth,
         .clk, .resetn);

    clock_crossing_fifobus_interconnect
        #() clock_crossing_fifobus_interconnect_u
            (.clka_fifo(clka_dram), .clkb_fifo(clkb_dram),
             .clka(clk), .clkb(clkb_dram.clk), .resetn);
endmodule


// module top import globals::*;
module top_and_mxu_dut2 import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 2)
    (output logic qout, input logic din, clk2, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Weightvec);
    localparam TOTAL_FIFOS = 0;
    logic [TOTAL_DUTS+TOTAL_FIFOS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0]  d;
    assign qout = q[1];
    logic                              ready_for_a_tile2;
    data #(Layeriovec) a2(.clk(clk2), .resetn);
    data #(Weightvec) b2(.clk(clk2), .resetn);
    data #(Civec) c2(.clk(clk2), .resetn);
    `MONITOR_(q[1], {ready_for_a_tile2, c2.value, c2.info}, qdut2, clk2)
    `DRIVER_(d[1], din, d1, clk2);
    assign a2.value = d[1];
    assign a2.info_master.value = d[1]>>1;
    assign b2.value = d[1]>>2;
    assign b2.info_master.value = d[1]>>3;
    mxu #(`EXPORT_ARITH) mxu_u
        (
         // interfaces
         .a(a2), .b(b2), .c(c2),
         // outputs
         .ready_for_a_tile(ready_for_a_tile2),
         // inputs
         .clk(clk2), .resetn);
endmodule


// module top import globals::*;
module gemm_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din, weightmem_clk, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Weightvec);
    logic [TOTAL_DUTS-1:0] q;
    logic [DBITS-1:0]      d;
    logic                  c_will_be_valid_soon, ready_for_a_tile;
    data #(Layeriovec) a(.clk, .resetn);
    data #(Weightvec) b(.clk, .resetn);
    data #(Civec) c(.clk, .resetn);
    `MONITOR_(q[0], {c_will_be_valid_soon, ready_for_a_tile,
                     c.value, c.info}, qdut)
    `DRIVER(d, din);
    assign a.value = d;
    assign a.info_master.value = d>>1;
    assign b.value = d>>2;
    assign b.info_master.value = d>>3;
    assign qout = ^q;
    gemm #(`EXPORT_ARITH) gemm_u
        (
         // interfaces
         .a, .b, .c,
         // outputs
         .c_will_be_valid_soon,
         .ready_for_a_tile,
         // inputs
         .clk, .resetn);
endmodule


// module top import globals::*;
module mem_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_CLKS=2)
    (`include "ports.sv", output logic qout, input logic din,
     instruc_clk, weightmem_clk, layeriomem_clk,
     pooling_clk, padding_clk, quantization_clk, clk2, clk, resetn);
    import Instruc::HostData;
    // logic [$bits(LayerParams)-1:0] d;
    LayerParams d;
    `INSTRUC_FIFOBUS(layerio, Layeriovec);
    `INSTRUC_FIFOBUS(weight, Weightvec);
    `INSTRUC_FIFOBUS(post_gemm_params, PostGemmParams);
    `LAYERIOMEM_INSTRUC_FIFOBUS(layerio_rd_instruc);
    `LAYERIOMEM_INSTRUC_FIFOBUS(layerio_wr_instruc);
    `WEIGHTMEM_INSTRUC_FIFOBUS(weight_rd_instruc);
    `WEIGHTMEM_INSTRUC_FIFOBUS(post_gemm_params_rd_instruc);
    `DRIVER(d, din, clk);
    localparam    TOTAL_FIFOS = 7;
    logic [TOTAL_FIFOS-1:0] _q;
    `FIFOAGENT(layerio, _q[0], din);
    `FIFOAGENT(weight, _q[1], din);
    `FIFOAGENT(post_gemm_params, _q[2], din);
    `FIFOAGENT(layerio_rd_instruc, _q[3], din, TRUE, FALSE);
    `FIFOAGENT(layerio_wr_instruc, _q[4], din, TRUE, FALSE);
    `FIFOAGENT(weight_rd_instruc, _q[5], din, TRUE, FALSE);
    `FIFOAGENT(post_gemm_params_rd_instruc, _q[6], din, TRUE, FALSE);
    assign qout = ^_q;
    `IPFIFO(layerio_rd_instruc);
    `IPFIFO(layerio_wr_instruc);
    `IPFIFO(weight_rd_instruc);
    `IPFIFO(post_gemm_params_rd_instruc);
    if (FAST_COMPILE) begin : g0
        emif_phy_bus dramphy(.pll_ref_clk(pll_ref_clk));
    end else begin : g0
        emif_phy_bus dramphy
            (
             .pll_ref_clk (pll_ref_clk   ), //   input, width = 1,
             .oct_rzqin   (oct_rzqin     ), //   input, width = 1,
             .mem_ck      (mem_ck        ),	//  output, width = 1,
             .mem_ck_n    (mem_ck_n      ),	//  output, width = 1,
             .mem_a       (mem_a         ),	//  output, width = 17,
             .mem_act_n   (mem_act_n     ),	//  output, width = 1,
             .mem_ba      (mem_ba        ),	//  output, width = 2,
             .mem_bg      (mem_bg        ),	//  output, width = 1,
             .mem_cke     (mem_cke       ),	//  output, width = 1,
             .mem_cs_n    (mem_cs_n      ),	//  output, width = 1,
             .mem_odt     (mem_odt       ),	//  output, width = 1,
             .mem_reset_n (mem_reset_n   ),	//  output, width = 1,
             .mem_par     (mem_par       ),	//  output, width = 1,
             .mem_alert_n (mem_alert_n   ),	//   input, width = 1,
             .mem_dqs     (mem_dqs       ),	//   inout, width = 9,
             .mem_dqs_n   (mem_dqs_n     ),	//   inout, width = 9,
             .mem_dq      (mem_dq        ),	//   inout, width = 72
             .mem_dbi_n   (mem_dbi_n     )	//   inout, width = 9,
             );
    end
    mem #(`EXPORT_ARITH) mem_u (.layerio,
                                .weight,
                                .post_gemm_params,
                                .layerio_rd_instruc,
                                .layerio_wr_instruc,
                                .weight_rd_instruc,
                                .post_gemm_params_rd_instruc,
                                .dramphy(g0.dramphy),
                                .layer_params(d),
                                .start(d),
                                .topclk(clk),
                                .layeriomem_clk,
                                .weightmem_clk,
                                .resetn
                                );
endmodule


// module top import globals::*;
module arith_and_mxu import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 2)
    (output logic qout, input logic din, instruc_clk,
     pooling_clk, padding_clk, quantization_clk, clk2, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Weightvec);
    localparam TOTAL_FIFOS = 3;
    logic [TOTAL_DUTS+TOTAL_FIFOS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0]  d;
    Civec synth_q;
    Info synth_q_info;
    Civec synth_mxu;
    fifobus #(.Q(Layeriovec), .DEPTH(4)) layerio(.clk, .resetn);
    fifobus #(.Q(Weightvec), .DEPTH(4)) weight(.clk, .resetn);
    fifobus #(.Q(PostGemmParams), .DEPTH(4)) post_gemm_params(.clk, .resetn);
    `IPFIFO(layerio);
    `IPFIFO(weight);
    `IPFIFO(post_gemm_params);
    `DRIVER_(d[0], din, d0, clk);
    `FIFOAGENT_(layerio, q[0], din, layerio, TRUE, FALSE, TRUE, TRUE, TRUE);
    // `FIFOAGENT_(layerio, q[0], din, layerio, FALSE, FALSE, TRUE, TRUE, TRUE);
    `FIFOAGENT_(weight, q[1], din, weight, TRUE, FALSE, TRUE, TRUE, TRUE);
    `FIFOAGENT_(post_gemm_params, q[2], din, post_gemm_params, TRUE, FALSE,
                TRUE, TRUE, TRUE);
    `MONITOR_(q[3], {synth_q, synth_q_info}, qdut)
    // `MONITOR_(q[3], {synth_q, synth_q_info, synth_mxu}, qdut)
    // `MONITOR_(q[3], {layerio.d.value, layerio.d.info}, qdut);
    assign qout = ^q;
    arith #(FALSE, `EXPORT_ARITH) arith_u
        (.layerio, .weight, .post_gemm_params,
         .layer_params(d[0]),
         .wrote_layerio_layer(d[0]),
         .start(d[0]),
         .pooling_clk,
         .padding_clk,
         .quantization_clk,
         .synth_q,
         .synth_q_info,
         .synth_mxu,
         .topclk(clk), .resetn);
    logic                              ready_for_a_tile2;
    data #(Layeriovec) a2(.clk(clk2), .resetn);
    data #(Weightvec) b2(.clk(clk2), .resetn);
    data #(Civec) c2(.clk(clk2), .resetn);
    `MONITOR_(q[4], {ready_for_a_tile2, c2.value, c2.info}, qdut2, clk2)
    `DRIVER_(d[1], din, d1, clk2);
    assign a2.value = d[1];
    assign a2.info_master.value = d[1]>>1;
    assign b2.value = d[1]>>2;
    assign b2.info_master.value = d[1]>>3;
    mxu #(`EXPORT_ARITH) mxu_u
        (
         // interfaces
         .a(a2), .b(b2), .c(c2),
         // outputs
         .ready_for_a_tile(ready_for_a_tile2),
         // inputs
         .clk(clk2), .resetn);
endmodule


// module top import globals::*;
module pooling_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din, pooling_clk, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Layeriovec);
    logic [TOTAL_DUTS-1:0] q;
    logic [DBITS-1:0]      d;
    logic                  ready;
    data #(Q) qdata(.clk, .resetn);
    data #(Q) ddata(.clk, .resetn);
    `MONITOR_(q[0], {ready, qdata.value, qdata.info}, qdut)
    `DRIVER(d, din);
    assign ddata.value = d;
    assign ddata.info_master.value = d;
    assign qout = ^q;
    fifo_array_bus #(.I(RxTx::TOTAL_RESULT_FIFOS),
                     .Q(Layeriovec), .DEPTH(RESULT_FIFOS_DEPTH)) results
        (.clk, .resetn);
    pooling #(`EXPORT_ARITH) pooling_u
        (
         // interfaces
         .q(qdata), .d(ddata),
         .results,
         // outputs
         .ready,
         // inputs
         .size(d),
         .size_w(d>>1),
         .size_h(d>>2),
         .stride(d>>3),
         .avg_pool_denom(d>>4),
         .type_(d>>5),
         .start(d),
         .topclk(clk),
         .slowclk(pooling_clk), .resetn);
endmodule



// module top import globals::*, Tiler::DIGIT;
module tilebuf_dut import globals::*, Tiler::DIGIT;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din, logic [TOTAL_DUTS-1:0] clk, resetn);
    localparam    DBITS = 1024;
    logic [TOTAL_DUTS-1:0][DBITS-1:0] d;
    logic [1:0]                       q;
    typedef Weightvec Q;
    `FOR(genvar, I, TOTAL_DUTS) begin
        `DRIVER_(d[I], din, dI, clk[I]);
    end
    // dut inputs
    // dut interfaces
    fifobus #(.Q(Weightvec), .DEPTH(INSTRUC_FIFOS_DEPTH)) layerfifo
        (.clk(clk[0]), .resetn);
    data #(Q) dut_q(.clk, .resetn);
    // dut outputs
    logic half_full, full, tile_rd_ready;
    `MONITOR_(q[0], {dut_q.value, dut_q.info,
                     half_full, full, tile_rd_ready}, q0, clk[0]);
    `FIFOAGENT(layerfifo, q[1], din, TRUE, FALSE);
    assign qout = ^q;
    tilebuf #(Weightvec, MAX_TILE_SIZE_M) tilebuf_u
        (
         // interfaces
         .layerfifo,
         .q(dut_q),
         // outputs
         .half_full,
         .full,
         .tile_rd_ready,
         // inputs
         .wrote_layer(d[0]),
         .start_tile_rd(d[0]),
         .total_layer_reads(d[0]),
         .tile_size(d[0]),
         .tile_size_valid(d[0]),
         .clk(clk[0]), .resetn
         );
endmodule


// module top import globals::*;
module arith_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din,
     pooling_clk, padding_clk, quantization_clk, clk2, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams);
    localparam TOTAL_FIFOS = 3;
    logic [TOTAL_DUTS+TOTAL_FIFOS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0]  d;
    Aivec synth_q;
    Civec synth_gemm;
    Info synth_q_info;
    Civec synth_mxu;
    fifobus #(.Q(Layeriovec), .DEPTH(4)) layerio(.clk, .resetn);
    fifobus #(.Q(Weightvec), .DEPTH(4)) weight(.clk, .resetn);
    fifobus #(.Q(PostGemmParams), .DEPTH(4)) post_gemm_params(.clk, .resetn);
    `FIFO(layerio);
    `FIFO(weight);
    `FIFO(post_gemm_params);
    `DRIVER_(d[0], din, d0, clk);
    `FIFOAGENT_(layerio, q[0], din, layerio, TRUE, FALSE, TRUE, TRUE, TRUE);
    `FIFOAGENT_(weight, q[1], din, weight, TRUE, FALSE, TRUE, TRUE, TRUE);
    `FIFOAGENT_(post_gemm_params, q[2], din, post_gemm_params, TRUE, FALSE,
                TRUE, TRUE, TRUE);
    `MONITOR_(q[3], {synth_q, synth_q_info, d[0]}, qdut)
    fifobus #(.Q(Weightvec), .DEPTH(INSTRUC_FIFOS_DEPTH)) layerfifo
        (.clk(clk[0]), .resetn);
    data #(Q) dut_q(.clk, .resetn);
    // `MONITOR_(q[3], {synth_gemm, synth_q_info, d[0]}, qdut)
    // `MONITOR_(q[3], {synth_q, synth_q_info, synth_mxu}, qdut)
    // `MONITOR_(q[3], {layerio.d.value, layerio.d.info}, qdut);
    assign qout = ^q;
    arith #(FALSE, `EXPORT_ARITH) arith_u
        (.layerio, .weight, .post_gemm_params,
         .results,
         .layer_params(d[0]),
         .wrote_layerio_layer(d[0]),
         .start(d[0]),
         .pooling_clk,
         .padding_clk,
         .quantization_clk,
         .synth_q,
         .synth_q_info,
         .synth_mxu,
         .synth_gemm,
         .top_ready(1),
         .topclk(clk),
         .resetn);
endmodule


// module top import globals::*;
module test_large_mem_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (output logic qout, input logic din,
     input logic clk, resetn);
    localparam   type Q = Layeriovec;
    localparam   DBITS = $bits(Q);
    logic        q;
    logic [DBITS-1:0] d;
    dprambus #(.Q(Q), .DEPTH(LAYERIOMEM_DEPTH)) dpram(.clk, .resetn);
    `DRIVER(d, din);
    `MONITOR(q, {dpram.q.value});
    assign qout = ^q;
    `DPRAM(dpram);
    always_comb begin
        dpram.wraddress = d;
        dpram.rdaddress = d;
        dpram.d.value = d;
        dpram.rdreq = d;
        dpram.wrreq = d[1];
    end
endmodule


// module top import globals::*;
module layeriomem_topclk_dut import globals::*;
    #(`IMPORT_ARITH, TOTAL_CLKS=2)
    (output logic qout, input logic din,
     instruc_clk, layeriomem_clk, weightmem_clk, clk, resetn);
    import Instruc::HostData;
    // logic [$bits(LayerParams)-1:0] d;
    LayerParams d;
    `INSTRUC_FIFOBUS(layerio, Layeriovec);
    `LAYERIOMEM_INSTRUC_FIFOBUS(layerio_rd_instruc);
    `LAYERIOMEM_INSTRUC_FIFOBUS(layerio_wr_instruc); `DRIVER(d, din, clk);
    localparam    TOTAL_FIFOS = 3;
    logic [TOTAL_FIFOS-1:0] _q;
    logic                   q2;
    logic                   wrote_layerio_layer;
    `FIFOAGENT(layerio, _q[0], din);
    `FIFOAGENT(layerio_rd_instruc, _q[1], din, TRUE, FALSE);
    `FIFOAGENT(layerio_wr_instruc, _q[2], din, TRUE, FALSE);
    `MONITOR(q2, {wrote_layerio_layer});
    assign qout = ^_q ^ q2;
    `IPFIFO(layerio_rd_instruc);
    `IPFIFO(layerio_wr_instruc);
    layeriomem_topclk #(`EXPORT_ARITH) layeriomem_topclk_u
        (// interfaces
         .layerio,
         .layerio_rd_instruc,
         .layerio_wr_instruc,
         // outputs
         .wrote_layerio_layer,
         // iputs
         .start(d),
         .layer_params(d),
         .topclk(clk),
         // .memclk(layeriomem_clk),
         .memclk(layeriomem_clk),
         .resetn
         );
endmodule


// module top import globals::*, Tiler::DIGIT;
module layerio_utils_dut import globals::*, Tiler::DIGIT;
    #(`IMPORT_ARITH, TOTAL_DUTS = 3)
    (output logic qout, input logic din, logic [TOTAL_DUTS-1:0] clk, resetn);
    localparam    DBITS = 1024;
    logic [TOTAL_DUTS-1:0][DBITS-1:0] d;
    logic [TOTAL_DUTS-1:0]            q;
    logic [TOTAL_DUTS-1:0]            wrote_layerio_layer;
    logic                             wrote_layer;
    logic [$clog2(LAYERIOMEM_CLK_DIV)-1:0] dfifosel;
    logic [LAYERIOMEM_CLK_DIV-1:0]
                                           [$clog2(LAYERIOMEM_DEPTH)-1:0]
                                           layeriomem_addresses;
    DIGIT addressmem_addresses;
    logic                                  q0;
    //
    `FOR(genvar, I, TOTAL_DUTS) begin
        `DRIVER_(d[I], din, dI, clk[I]);
    end
    `MONITOR_(q[0], {wrote_layerio_layer[0],
                     wrote_layer}, q0, clk[0]);
    `MONITOR_(q[1], {wrote_layerio_layer[1], q0}, q1, clk[1]);
    `MONITOR_(q[2], {wrote_layerio_layer[2],
                     dfifosel, layeriomem_addresses,
                     addressmem_addresses}, q2, clk[2]);
    assign qout = ^q;
    //
    wrote_layer_unit #(1) wrote_layer_u
        (.wrreqs(d[0]), .islastlayer(d[0]), .size(d[0]),
         .writing_layer_next(wrote_layerio_layer[0]),
         .wrote_layer,
         .clk(clk[0]), .resetn);
    //
    rdreqfifo_wrreq_unit rdreqfifo_wrreq_u
        (.q(q0), .size_w(d[1]),
         .wrote_layerio_layer(wrote_layerio_layer[1]),
         .en(d[1]),
         .clk(clk[1]), .resetn);
    //
    dfifo_addressmem_d_unit
        #(LAYERIOMEM_DEPTH, LAYERIOMEM_CLK_DIV, 3) dfifo_addressmem_d_unit_u
            (.dfifosel, .en(d[2]),
             .stride_w(d[2]),
             .size_w(d[2]),
             .size(d[2]),
             .islastlayer(d[2]),
             .wrote_layerio_layer(wrote_layerio_layer[2]),
             .addressmem_addresses,
             .layeriomem_addresses, .clk(clk[2]), .resetn);
endmodule


    `ifndef SYNTH_TOP
module top import globals::*;
    `else
module gemm_and_mxu_dut import globals::*;
    `endif
    #(`IMPORT_ARITH, TOTAL_DUTS = 2)
    (output logic qout, input logic din, clk2, clk, resetn);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Weightvec);
    logic [TOTAL_DUTS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0] d;
    logic                             c_will_be_valid_soon, ready_for_a_tile;
    data #(Layeriovec) a(.clk, .resetn);
    data #(Weightvec) b(.clk, .resetn);
    data #(Civec) c(.clk, .resetn);
    `MONITOR_(q[0], {c_will_be_valid_soon, ready_for_a_tile,
                     c.value, c.info}, qdut0)
    `DRIVER_(d[0], din, d0, clk);
    assign a.value = d[0];
    assign a.info_master.value = d[0]>>1;
    assign b.value = d[0]>>2;
    assign b.info_master.value = d[0]>>3;
    assign qout = ^q;
    gemm #(`EXPORT_ARITH) gemm_u
        (
         // interfaces
         .a, .b, .c,
         // outputs
         // .c_will_be_valid_soon,
         // .ready_for_a_tile,
         // inputs
         .clk, .resetn);
    logic                             ready_for_a_tile2;
    data #(Layeriovec) a2(.clk(clk2), .resetn);
    data #(Weightvec) b2(.clk(clk2), .resetn);
    data #(Civec) c2(.clk(clk2), .resetn);
    `MONITOR_(q[1], {ready_for_a_tile2, c2.value, c2.info}, qdut1, clk2)
    `DRIVER_(d[1], din, d1, clk2);
    assign a2.value = d[1];
    assign a2.info_master.value = d[1]>>1;
    assign b2.value = d[1]>>2;
    assign b2.info_master.value = d[1]>>3;
    // mxu #(`EXPORT_ARITH) mxu_u
    //     (
    //      // interfaces
    //      .a(a2), .b(b2), .c(c2),
    //      // outputs
    //      .ready_for_a_tile(ready_for_a_tile2),
    //      // inputs
    //      .clk(clk2), .resetn);
endmodule

    `ifdef SYNTH_TOP
module top import globals::*;
    `else
module top_dut import globals::*;
    `endif
    #(`IMPORT_ARITH, TOTAL_DUTS = 1)
    (`include "ports.sv", output logic qout, input logic din,
    `ifdef TEST_FMAX
     input
    `else
     output
    `endif
     logic instruc_clk, weightmem_clk, layeriomem_clk,
     pooling_clk, padding_clk, quantization_clk, clk);
    localparam type Q = Layeriovec;
    localparam DBITS = $bits(LayerParams)+$bits(Weightvec);
    logic [TOTAL_DUTS-1:0] q;
    logic [TOTAL_DUTS-1:0][DBITS-1:0] d;
    `DRIVER_(d[0], din, d0, clk);
    assign qout = ^q;
    top_dut #(`EXPORT_ARITH) top_u
        (`include "connect_ports.sv",
         .qout(q[0]), .din,
         .padding_clk, .pooling_clk, .quantization_clk,
         .layeriomem_clk, .weightmem_clk, .instruc_clk,
         .clk
         );
endmodule
