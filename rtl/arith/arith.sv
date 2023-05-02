`include "../top/define.svh"


// names with a, b represent data/signals related to the two matrices being
// multiplied, and c represents the output matrix. In other words:

// a is the featuremaps / layer input,
// b is the weights,
// c is data that will lead to the activations / layer output


module arith import globals::*;
    #(CONNECT_GEMM=TRUE, `IMPORT_ARITH)
    (fifobus layerio, weight, post_gemm_params,
     fifo_array_bus results,
     input LayerParams layer_params,
     input logic wrote_layerio_layer,
     input logic topclk,
     input logic pooling_clk,
     input logic padding_clk,
     input logic quantization_clk,
     input logic resetn,
     input logic top_ready,
     input logic start,
     input logic [TOTAL_SOFT_RESETS-1:0] soft_resetns,
     input logic wrote_inference
     );
    import RxTx::*;
    // control
    logic        post_gemm_ready;
    logic        clk; assign clk = topclk;
    //
    data #(Ajvec) a(.*);
    data #(Bjvec) b(.*);
    data #(Bjvec) _b(.*);
    data #(PostGemmParams) post_gemm_params_q(.*);
    data #(Ajvec) _a(.*);
    data #(Ajvec) c(.*);
    data #(Ajvec) _c(.*);
    data #(Cjvec) gemm_q(.clk, .resetn);
    data #(Cjvec) post_gemm_d(.clk, .resetn);

    localparam   DELAY0 = 1;
    ////////////////////////////////////////////////////////////////////
    `REG__(a_ready, layerio.rdready, DELAY0);
    `REG__(b_ready, weight.rdready, DELAY0);
    `REG__(pgp_ready, post_gemm_params.rdready2, DELAY0);
    `ONOFF__(prev_layer_written, wrote_layerio_layer | wrote_inference,
             layerio.q.info.last_elm,
             1, clk, soft_resetns[1])
    ////////////////////////////////////////////////////////////////////
    logic [1:0]  unread_a_tiles, unread_pgp_tiles;
    logic        a_rdreq_d, b_rdreq_d, pgp_rdreq_d;
    logic        new_a_tile_coming;
    logic        ready_for_a_tile, ready_for_b_tile, ready_for_pgp_tile;
    logic        _pgp_ready_for_a_tile1, _pgp_ready_for_a_tile2;
    logic        pgp_ready_for_a_tile1, pgp_ready_for_a_tile2;
    logic        pgp_ready_for_a_tile;
    logic        _ready_for_a_tile, _ready_for_b_tile;
    localparam   SAFE_DELAY1 = 1;
    localparam   SAFE_DELAY2 = 1;
    `COUNTER(unread_a_tiles, weight.q.info.new_tile_k
             - layerio.q.info.new_tile_k);
    `COUNTER(unread_pgp_tiles, layerio.q.info.new_tile_k
             - post_gemm_params.q.info.new_tile_k);
    `POSEDGE(_ready_for_a_tile, |unread_a_tiles,
             SZI>TILEBUF_RDLATENCY+2-SAFE_DELAY1?
             SAFE_DELAY1+SZI-TILEBUF_RDLATENCY-2 : SAFE_DELAY1);
    `POSEDGE(_ready_for_b_tile, !unread_a_tiles,
             {SZI>>1} > TILEBUF_RDLATENCY+5-SAFE_DELAY1?
             {SZI>>1} - TILEBUF_RDLATENCY+5+SAFE_DELAY1 : SAFE_DELAY1);
    `POSEDGE(_pgp_ready_for_a_tile1, !unread_pgp_tiles);
    `POSEDGE(_pgp_ready_for_a_tile2,
             (post_gemm_params.rdready2 & (unread_pgp_tiles == 1)));
    `ONOFF__(got_first_start, start, 0);
    `ONOFF(ready_for_a_tile, _ready_for_a_tile, a_rdreq_d);
    `ONOFF(ready_for_b_tile, _ready_for_b_tile | (start & !got_first_start),
           b_rdreq_d);
    `ONOFF(pgp_ready_for_a_tile1, _pgp_ready_for_a_tile1, a_rdreq_d);
    `ONOFF(pgp_ready_for_a_tile2, _pgp_ready_for_a_tile2, a_rdreq_d);
    assign pgp_ready_for_a_tile = pgp_ready_for_a_tile1
                                  | pgp_ready_for_a_tile2;
    assign a_rdreq_d = ready_for_a_tile
                       & prev_layer_written & layerio.rdready
                       & !layerio.half_full
                       & post_gemm_params.rdready
                       & pgp_ready_for_a_tile;
    `POSEDGE_(layerio.rdreq, a_rdreq_d, 1, a_rdreq_d);
    ////////////////////////////////////////////////////////////////////;

    `ONOFF__(done_inference, wrote_layerio_layer
             & layer_params.islastlayer & layer_params.islast_inbatch,
             !(layer_params.islastlayer & layer_params.islast_inbatch));
    assign b_rdreq_d
      = weight.rdready & post_gemm_ready
        & ready_for_b_tile
        & !done_inference
        & top_ready;
    `POSEDGE_(weight.rdreq, b_rdreq_d, 1, b_rdreq_d);
    ////////////////////////////////////////////////////////////////////

    localparam   DOUBLE_SHIFTVEC_DELAY = {SZI>>1} + SZI;
    localparam   DELAY1 = 1;
    localparam   GEMM_RD_DELAY_MINUS_PGPMEM_RD_DELAY = 2*SZI
                 - TILEBUF_RDLATENCY + DELAY1 + 8 - SAFE_DELAY2;
    localparam   C_WILL_BE_VALID_SOON_DELAY
                 = GEMM_RD_DELAY_MINUS_PGPMEM_RD_DELAY - DOUBLE_SHIFTVEC_DELAY;
    `POSEDGE(ready_for_pgp_tile, layerio.q.info.new_tile_k,
             C_WILL_BE_VALID_SOON_DELAY);
    `POSEDGE_(post_gemm_params.rdreq, pgp_rdreq_d, 1, pgp_rdreq_d);
    assign pgp_rdreq_d = ready_for_pgp_tile & post_gemm_params.rdready;

    logic [$clog2(MAX_TILE_SIZE_M)-1:0] padded_tile_size_n;
    `REG(padded_tile_size_n, layer_params.tile_size_m < MIN_TILE_SIZE_N?
         MIN_TILE_SIZE_N : layer_params.tile_size_m);
    pad_tile_size_n #(`EXPORT_ARITH) b_buf_u
      (.q(b), .d(weight.q),
       .start_tile_rd(weight.rdreq),
       .padded_tile_size_n,
       .clk, .resetn);
    pad_tile_size_n #(`EXPORT_ARITH) post_gemm_params_buf_u
      (.q(post_gemm_params_q), .d(post_gemm_params.q),
       .start_tile_rd(post_gemm_params.rdreq),
       .padded_tile_size_n,
       .clk, .resetn);

    localparam                          ADELAY = 0;
    `SHIFT_REG(a, layerio.q, ADELAY, a);
    `SHIFT_REG(a.info_master, layerio.q.info_slave, ADELAY, a_info_delay);

    gemm #(`EXPORT_ARITH) gemm_u
      (.c(gemm_q),
       .a,
       .b,
       .layer_params,
       .clk,
       .resetn);
    if (CONNECT_GEMM) begin
        assign layerio.wrreq = layerio.d.info.valid;
        assign layerio.d.value = c.value;
        assign layerio.d.info_master.value = c.info;
    end else begin
    end

    `ONOFF__(arith_ready, wrote_layerio_layer, '0);
    `WORDSWAP2(_a, a);
    `REG_DATA_COND(post_gemm_d, 1, gemm_q, _a);
    post_gemm #(`EXPORT_ARITH) post_gemm_u
      (.q(_c), .d(post_gemm_d),
       .results,
       .layer_params,
       .top_ready(arith_ready),
       .wrote_layerio_layer(wrote_layerio_layer | wrote_inference),
       .ready(post_gemm_ready),
       .params(post_gemm_params_q),
       .pooling_clk, .padding_clk, .quantization_clk,
       .clk, .resetn);
    `WORDSWAP2(c, _c);

    if (SIM | USE_RESULT_FIFOS_FULL) begin : sim
        localparam type _Gemm = logic [SZJ-1:0][31:0];
        data #(_Gemm) gemm_c(.*);
        data #(Cjvec) _gemm_c(.*);
        `FOR(genvar, I, SZJ) begin
            `SIGNED(assign gemm_c.value[I] =, B_SIGNED, _gemm_c.value[SZJ-I-1]);
        end
        assign gemm_c.info_master.value = _gemm_c.info;
        triangle_buf #(.SLOPE(-1)) gemm_triangle_u (.q(_gemm_c), .d(gemm_q));
        fifobus #(.Q(Ajvec), .D(Cjvec), .DEPTH(RESULT_FIFOS_DEPTH)) qfifo
          (.clk, .resetn);
        `REG3(qfifo.d.value, qfifo_d, _gemm_c.value);
        `REG3(qfifo.wrreq, qfifo_wrreq, _gemm_c.info.valid);
        `REG3(qfifo.rdreq, qfifo_rdreq, !qfifo.empty);
        `FIFO(qfifo);
        data #(Chainjvec) results_d(.*);
        data #(Chainjvec) dummy(.*);
        assign dummy.info_master.value.valid = '0;
        `REG_DATA_COND(results_d, 1, qfifo.q, dummy);
        if (USE_RESULT_FIFOS_FULL) begin
            `ASSIGN_RESULT(GEMM_RESULTS_SEL, results_d);
            `ASSIGN_RESULT(A_RESULTS_SEL, a);
            `ASSIGN_RESULT(B_RESULTS_SEL, b);
        end
    end
    if (SIM | USE_RESULT_FIFOS_FULL) begin : sample_pgp
        fifobus #(.Q(Ajvec), .D(PostGemmParams), .DEPTH(RESULT_FIFOS_DEPTH))
        qfifo (.clk, .resetn);
        `WORDSWAP_(qfifo.d.value, qfifo_d, post_gemm_params_q.value);
        `REG3(qfifo.wrreq, qfifo_wrreq, post_gemm_params_q.info.valid);
        `REG3(qfifo.rdreq, qfifo_rdreq, !qfifo.empty);
        `FIFO(qfifo);
        if (USE_RESULT_FIFOS_FULL) begin
            `ASSIGN_RESULT(POST_GEMM_PARAMS_RESULTS_SEL, qfifo.q);
        end
    end
endmodule


module pad_tile_size_n import globals::*; #(`IMPORT_ARITH)
    (data q, d, input logic start_tile_rd,
     input logic clk, resetn,
     input logic [$clog2(MAX_TILE_SIZE_M)-1:0] padded_tile_size_n,
     output logic done_in_3cc,
     output logic done);
    logic [$clog2(SZI)-1:0] counter;
    logic                   dvalid, dvalid_d;
    logic [$clog2(MAX_TILE_SIZE_M)-1:0] padded_tile_size_n_m1;
    logic [$clog2(MAX_TILE_SIZE_M)-1:0] padded_tile_size_n_m4;
    `REG(padded_tile_size_n_m1, padded_tile_size_n-1);
    `REG(padded_tile_size_n_m4, padded_tile_size_n-4);
    always_ff @(posedge clk or negedge resetn) if (~resetn) begin
        counter <= '0;
        dvalid <= '0;
    end else begin
        if (dvalid) counter <= counter + 1;
        if (dinfo_.new_tile_k) counter <= 0;
        dvalid <= dvalid_d;
    end
    always_comb begin
        dvalid_d = dvalid;
        if (counter == SZI - 1) dvalid_d = '0;
        if (dinfo_.new_tile_k) dvalid_d = '1;
    end
    logic      tile_rd_count_logic;
    Tiler::DIGIT tile_rd_count, tile_rd_count_d;
    // NOTE: following delays must be added to VALID_SOON_DELAY in accum_mem
    localparam DELAY0 = 1;
    localparam DELAY1 = 1;
    logic [$bits(d.value)-1:0] d_;
    Info dinfo_;
    `REG(tile_rd_count, tile_rd_count_d);
    `REG(tile_rd_count_logic, |tile_rd_count_d);
    `REG(d_, d.value, DELAY1);
    `REG(dinfo_, d.info, DELAY1);
    `REG2__(start_tile_rd_, start_tile_rd, DELAY1);
    `SHIFT_REG__(q.value, dvalid_d? d_ : '0, DELAY0, qvalue);
    `REG2_(q.info_master.value, dvalid_d? dinfo_ : '0, qinfo_delay, DELAY0);
    always_comb begin
        tile_rd_count_d = tile_rd_count;
        if (start_tile_rd_ | tile_rd_count_logic) begin
            tile_rd_count_d = tile_rd_count + 1;
        end
        if (tile_rd_count == padded_tile_size_n_m1) tile_rd_count_d = '0;
    end
    `POSEDGE(done, tile_rd_count == padded_tile_size_n_m1
             & (start_tile_rd_ | tile_rd_count_logic));
    `POSEDGE(done_in_3cc, tile_rd_count == padded_tile_size_n_m4
             & (start_tile_rd_ | tile_rd_count_logic));
endmodule
