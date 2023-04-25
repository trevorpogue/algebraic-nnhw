`include "../top/define.svh"


module mem import globals::*;
    #(`IMPORT_ARITH)
    (fifobus layerio, input_layerio, fifobus weight, fifobus post_gemm_params,
     fifo_array_bus layerio_rd_instrucs,
     fifo_array_bus layerio_wr_instrucs,
     fifobus weight_rd_instruc,
     fifobus post_gemm_params_rd_instruc,
     emif_phy_bus dramphy,
     input LayerParams layer_params,
     input logic start, topclk, layeriomem_clk, weightmem_clk,
     resetn,
     input logic [TOTAL_SOFT_RESETS-1:0] soft_resetns,
     input logic hard_resetn,
     input logic load,
`ifdef SYNTH_DEBUG
     output Weightvec dram_d,
`endif
     output logic input_layeriomem_wrote_layer,
     output logic wrote_layerio_layer,
     output logic wrote_inference
     );
    logic         clk; assign clk = topclk;
    Tiler::DIGIT         total_weight_reads_all_layers_memclk;
    fifobus #(.D(logic), .Q(logic)) dummy(.clk(weightmem_clk), .resetn);
    logic         dram_clk, dram_q_clk_wrready, weight_tilebuf_wrready;
    //
    /////////////////////////////////////////////////////////////////////////
    // memories
    //
    localparam    BUFDEPTH = USE_SMALL_BUF? SMALL_BUF_DEPTH
                  : TILE_BUF_DEPTH;
    localparam integer POST_GEMM_PARAMS_MEM_DEPTH
                       = $ceil(PGP_MEM_SIZE / Instruc::POST_GEMM_PARAMS_WORD_WIDTH);
    // weight memories
    sprambus #(.Q(PostGemmParams), .DEPTH(POST_GEMM_PARAMS_MEM_DEPTH),
               .USE_RDWR_ADDRESSES(TRUE)) post_gemm_params_sram
        (.clk(weightmem_clk), .resetn(hard_resetn));
    typedef logic [B_WIDTH*SZJ-1:0] DramMQ;
    localparam                      MBITS = B_WIDTH*SZJ;
    localparam                      SBITS = Dram::WIDTH;
    localparam                      _DIV = 1<<($clog2(MBITS/SBITS));
    localparam                      DIV = MBITS > SBITS? _DIV : 1;
    data #(PGP2) pgp_q(.clk(weightmem_clk), .resetn);
    pgpmem post_gemm_params_sram_u (post_gemm_params_sram, pgp_q);
    data #(Weightvec) dram_q(.clk(dram_clk), .resetn);

    localparam                      MWIDTH = $bits(DramMQ);
    localparam                      _BURST_MULT = 1<<$clog2(MBITS/$bits(Dram::Q));
    localparam                      BURST_MULT = MWIDTH > $bits(Dram::Q)? _BURST_MULT : 1;
    localparam                      _BURST_COUNT = BURST_COUNT * BURST_MULT;
    localparam                      SWIDTH = MWIDTH / BURST_MULT;
    typedef logic [SWIDTH-1:0]      DramSQ;
    logic                           dram_width_matcher_ready;

    sprambus #(.Q(DramMQ), .DEPTH(Dram::DEPTH),
               .USE_RDWR_ADDRESSES(TRUE)) dram(.clk(weightmem_clk), .resetn);
    sprambus #(.Q(DramSQ), .DEPTH(Dram::DEPTH),
               .USE_RDWR_ADDRESSES(TRUE)) _dram(.clk(weightmem_clk),
                                                .resetn);
    dram_width_matcher #(128) width_matcher_u
        (.master(dram), .slave(_dram),
         .clk2(dram_clk),
         .ready(dram_width_matcher_ready));
    `ASSIGN_DATA(dram_q, dram.q);
    dram_emif_fifo #(.Q(DramSQ), .D(DramSQ),
                     .DEPTH(Dram::DEPTH),
                     .BURST_COUNT(_BURST_COUNT),
                     .FAST_COMPILE(FAST_COMPILE))
    weight_dram_u (.master(_dram), .slave(dramphy),
                   .tilebuf_wrready(!weight.half_full),
                   .dram_q_clk_wrready,
                   .hard_resetn, .dram_clk
                   );

    //
    // layerio memory & tiler
    logic [$clog2(_TOTAL_LAYERIOMEMS)-1:0] wrsel, rdsel;
    assign wrsel = layer_params.layeriomem_wrsel;
    assign rdsel = layer_params.layeriomem_rdsel;
    slave_arbitrated_fifo_bus #(TOTAL_LAYERIOMEMS) layerio_arb
        (.master(layerio), .wrsel(wrsel), .rdsel(rdsel));
    `CONNECT_FIFO_ARRAY_NMSPC(layerio_arb.mems, TOTAL_LAYERIOMEMS, layerios);
    logic [TOTAL_LAYERIOMEMS-1:0]          wrote_layerio_layer_;
    logic [TOTAL_LAYERIOMEMS-1:0]          wrote_inference_;
    `REG(wrote_layerio_layer, wrote_layerio_layer_[wrsel]);
    `REG(wrote_inference, wrote_inference_[wrsel]);
    `REG(input_layeriomem_wrote_layer, wrote_layerio_layer_[INPUTMEM]);
    `FOR(genvar, I, TOTAL_LAYERIOMEMS) begin
        logic resetn_, done_writing;
        localparam MEM_MODULE_ = SZJ == 56? I : -1;
        LayerParam size_w_c;
        LayerParam total_layer_reads;
        logic [$clog2(MAX_TILE_SIZE_M)-1:0] tile_size_m;
        assign done_writing = rdsel == I;
        always_comb begin
            if (I == INPUTMEM) begin
                if ((wrsel == I) | (rdsel == I)) begin
                    size_w_c = layer_params.size_w_c;
                    total_layer_reads = layer_params.total_layerio_reads;
                    tile_size_m = layer_params.tile_size_m;
                end else begin
                    size_w_c = layer_params.inputmem_size_w_c;
                    total_layer_reads = layer_params.inputmem_total_layer_reads;
                    tile_size_m = layer_params.inputmem_tile_size_m;
                end
            end else begin
                size_w_c = layer_params.size_w_c;
                total_layer_reads = layer_params.total_layerio_reads;
                tile_size_m = layer_params.tile_size_m;
            end
        end
        assign resetn_ = soft_resetns[I];
        if (I == INPUTMEM) begin
            `INSTRUC_FIFOBUS(_layerio, Layeriovec);
            wr_arbitrated_fifo_bus2 #(.D(Layeriovec),
                                      .Q(Layeriovec)) layerio_arb_u
                (.slave(_layerio), .writer(input_layerio),
                 .writer_reader(layerio_arb.mems.ios[I]),
                 .clk, .resetn);
            layeriomem #(`EXPORT_TOP_(,LAYERIOMEMS_SZJ[I], LAYERIOMEMS_SZJ[I],
                                      ,,,,,,,,LAYERIOMEMS_SIZE[I], MEM_MODULE_,
                                      I, SZJ))
            layeriomem_u
                (.layerio(_layerio),
                 .layerio_rd_instruc(layerio_rd_instrucs.ios[I]),
                 .layerio_wr_instruc(layerio_wr_instrucs.ios[I]),
                 .start,
                 .wrote_layerio_layer(wrote_layerio_layer_[I]),
                 .wrote_inference(wrote_inference_[I]),
                 .done_writing,
                 .size_w_c,
                 .total_layer_reads,
                 .tile_size_m,
                 .layer_params,
                 .topclk, .memclk(layeriomem_clk),
                 .resetn(resetn_),
                 .soft_resetn(resetn_),
                 .hard_resetn);
        end else begin
            layeriomem #(`EXPORT_TOP_(,LAYERIOMEMS_SZJ[I], LAYERIOMEMS_SZJ[I],
                                      ,,,,,,,,LAYERIOMEMS_SIZE[I], MEM_MODULE_,
                                      I, SZJ))
            layeriomem_u
                (.layerio(layerio_arb.mems.ios[I]),
                 .layerio_rd_instruc(layerio_rd_instrucs.ios[I]),
                 .layerio_wr_instruc(layerio_wr_instrucs.ios[I]),
                 .start, .wrote_layerio_layer(wrote_layerio_layer_[I]),
                 .wrote_inference(wrote_inference_[I]),
                 .size_w_c,
                 .done_writing,
                 .total_layer_reads,
                 .tile_size_m,
                 .layer_params,
                 .topclk, .memclk(layeriomem_clk),
                 .resetn(resetn_),
                 .soft_resetn(resetn_),
                 .hard_resetn);
        end
    end //////////////////////////////////////////////////////////////////
    // clock crossing weight fifo interconnect
    //
    fifobus #(.Q(Weightvec),
              .DEPTH(INSTRUC_FIFOS_DEPTH)
              ) clkb_weight
        (.clk(weightmem_clk), .resetn);
    fifobus #(.Q(PostGemmParams),
              .DEPTH(INSTRUC_FIFOS_DEPTH)) clkb_post_gemm_params
        (.clk(weightmem_clk), .resetn);
    typedef struct packed {
        logic      start;
        logic      valid;
    } A2B;
    A2B clka_a2b, clkb_a2b;
    assign clka_a2b.start = start;
    assign clka_a2b.valid = 1;
    clock_crossing_data
        #(A2B) clock_crossing_weight_u
            (.clka_a2b, .clkb_a2b,
             .clka(topclk), .clkb(weightmem_clk), .resetn);

    //////////////////////////////////////////////////////////////////////
    // weight tilers
    //
    weight_reader #(Tiler::READER, POST_GEMM_PARAMS, 0,
                    POST_GEMM_PARAMS_MEM_DEPTH,
                    WEIGHTMEM_CLK_DIV
                    )
    pgp_reader_u
        (.master(clkb_post_gemm_params),
         .slave(post_gemm_params_sram),
         .instruc(post_gemm_params_rd_instruc),
         .start(clkb_a2b.start),
         .total_weight_reads_all_layers(total_weight_reads_all_layers_memclk),
         .clk(weightmem_clk), .resetn);
    weight_writer #(Tiler::WRITER, POST_GEMM_PARAMS, 0,
                    POST_GEMM_PARAMS_MEM_DEPTH)
    pgp_writer_u (.master(clkb_post_gemm_params),
                  .slave(post_gemm_params_sram),
                  .instruc(dummy),
                  .start(clkb_a2b.start),
                  .clk(weightmem_clk), .resetn);
    //
    // external memory tiler controllers
    weight_reader #(Tiler::READER, WEIGHT, 0, Dram::DEPTH,
                    BURST_COUNT)
    weight_reader_u
        (.master(clkb_weight),
         .slave(dram),
         .instruc(weight_rd_instruc),
         .start(clkb_a2b.start),
         .total_weight_reads_all_layers(total_weight_reads_all_layers_memclk),
         .clk(weightmem_clk), .resetn);
    weight_writer #(Tiler::WRITER, WEIGHT, 0, Dram::DEPTH)
    weight_writer_u (.master(clkb_weight),
                     .slave(dram),
                     .instruc(dummy),
                     .start(clkb_a2b.start),
                     .clk(weightmem_clk), .resetn);
    //
    clock_crossing_weightmem_interconnect
        #(Weightvec, BURST_COUNT, WEIGHT, BUFDEPTH, BURST_MULT)
    weightmem_interconnect_u
        (.clka_fifo(weight), .clkb_fifo(clkb_weight),
         .start,
         .load,
         .wrote_layerio_layer,
         .rdready(dram_width_matcher_ready),
         .mem_q_clk_wrready(dram_q_clk_wrready),
         .new_model(load),
         .hard_resetn,
         .mem_q(dram_q),
         .slave(dram),
         .total_writes(layer_params.total_weight_writes_all_layers),
         .total_layer_reads(layer_params.total_weight_reads_all_layers),
         .layer_params_valid(layer_params.valid),
         .total_weight_reads_all_layers_topclk
         (layer_params.total_weight_reads_all_layers),
         .total_weight_reads_all_layers_memclk,
         .loading_params_valid(layer_params.loading_params_valid),
         .tile_size(SZI),
         .topclk, .memclk(weightmem_clk), .resetn);
    //
    clock_crossing_weightmem_interconnect
        #(PostGemmParams,
          WEIGHTMEM_CLK_DIV
          ,POST_GEMM_PARAMS
          ,BUFDEPTH
          ,1
          )
    post_gemm_params_mem_interconnect_u
        (.clka_fifo(post_gemm_params), .clkb_fifo(clkb_post_gemm_params),
         .load,
         .wrote_layerio_layer,
         .hard_resetn,
         .rdready('1),
         .new_model(load),
         .mem_q(pgp_q),
         .slave(post_gemm_params_sram),
         .total_writes(layer_params.total_pgp_writes_all_layers),
         .total_layer_reads(layer_params.total_weight_reads_all_layers),
         .layer_params_valid(layer_params.valid),
         .loading_params_valid(layer_params.loading_params_valid),
         .tile_size(SZI),
         .topclk, .memclk(weightmem_clk), .resetn);
endmodule
