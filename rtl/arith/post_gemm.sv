`include "../top/define.svh"


module post_gemm import globals::*;
    // io shapes: Ajvec q, Civec d, PostGemmParams params
    #(`IMPORT_ARITH)
    (data q, d, params,
     fifo_array_bus results,
     output logic ready,
     input LayerParams layer_params,
     input logic pooling_clk,
     input logic padding_clk,
     input logic wrote_layerio_layer,
     input logic quantization_clk,
     input logic top_ready, clk, resetn);
    logic        pool_padding_ready, pooling_ready, c_padding_ready;
    assign ready = pool_padding_ready & pooling_ready & c_padding_ready;
    data #(Ajvec) quantization_q(.*);
    data #(Ajvec) pool_padding_d(.*);
    data #(Ajvec) pool_padding_q(.*);
    data #(Ajvec) pooling_q(.*);
    localparam   QUANTIZATION_BUF_DEPTH
                 = QUANTIZATION_CLK_FREQ < TOP_CLK_FREQ? TILE_BUF_DEPTH : 512;
    localparam   PADDING_BUF_DEPTH
                 = PADDING_CLK_FREQ < TOP_CLK_FREQ? TILE_BUF_DEPTH : 512;
    localparam   POOLING_BUF_DEPTH
                 = POOLING_CLK_FREQ < TOP_CLK_FREQ? TILE_BUF_DEPTH : 512;
    `POSEDGE__(pooling_start, top_ready, 4);
    quantization #(QUANTIZATION_BUF_DEPTH, QUANTIZATION_CLK_FREQ
                   == TOP_CLK_FREQ, `EXPORT_ARITH) quantization_u
                    (.q(quantization_q), .d, .params, .results,
                     .topclk(clk), .slowclk(quantization_clk), .resetn);
    `REG_DATA_COND(pool_padding_d, 1, quantization_q, d);
    Tiler::DIGIT c_cvalids, c_gemmvalids;

    if (DO_POOL_PADDING) begin : gen_pool_padding
        padding #(PADDING_BUF_DEPTH, RxTx::POOL_PADDING_RESULTS_SEL,
                  PADDING_CLK_FREQ == TOP_CLK_FREQ, `EXPORT_ARITH)
        pool_padding_u (.q(pool_padding_q), .d(pool_padding_d),
                        .results,
                        .wrote_layerio_layer,
                        .tile_size_m(layer_params.hw_size_padding),
                        .padding(layer_params.pool_padding),
                        .size_w(layer_params.size_w_gemm),
                        .size_h(layer_params.size_h_gemm),
                        .new_layer_edge(layer_params.new_layer_edge),
                        .layer_params_valid(layer_params.valid & top_ready),
                        .ready(pool_padding_ready),
                        .slowclk(padding_clk),
                        .resetn, .topclk(clk));
    end else begin : gen_pool_padding
        `SHIFTREG(pool_padding_q, pool_padding_d)
        assign pool_padding_ready = 1;
    end
    pooling #(POOLING_BUF_DEPTH, RxTx::POOLING_RESULTS_SEL,
              POOLING_CLK_FREQ == TOP_CLK_FREQ, `EXPORT_ARITH) pooling_u
                                (.q(pooling_q), .d(pool_padding_q),
                                 .results,
                                 .size(layer_params.pool_size),
                                 .size_w(layer_params.size_w_pool_padding),
                                 .size_h(layer_params.size_h_pool_padding),
                                 .stride(layer_params.pool_stride),
                                 .avg_pool_denom(layer_params.avg_pool_denom),
                                 .type_(layer_params.pool_type),
                                 .start(pooling_start),
                                 .topclk(clk),
                                 .slowclk(pooling_clk),
                                 .ready(pooling_ready),
                                 .resetn);
    padding #(PADDING_BUF_DEPTH, RxTx::C_RESULTS_SEL,
              PADDING_CLK_FREQ == TOP_CLK_FREQ, `EXPORT_ARITH)
    c_padding_u (.q(q), .d(pooling_q),
                 .results,
                 .wrote_layerio_layer,
                 .padding(layer_params.c_padding),
                 .tile_size_m(layer_params.total_c_padding_writes),
                 .size_w(layer_params.size_w_pooling),
                 .size_h(layer_params.size_h_pooling),
                 .layer_params_valid(layer_params.valid & top_ready),
                 .new_layer_edge(layer_params.new_layer_edge),
                 .ready(c_padding_ready),
                 .slowclk(padding_clk),
                 .resetn, .topclk(clk));
    if (SIM) begin : sim
        data #(Ajvec) q_(.clk, .resetn);
        `WORDSWAP2(q_, q);
    end
endmodule


`define PARAM_BUF(param, offset, width, DELAY0, _DELAY1=1) \
data #(logic [width-1:0]) param(.*); \
data #(logic [SZI-1:0][width-1:0]) param``_vec(.*); \
data #(logic [SZI-1:0][width-1:0]) _``param``_vec(.*); \
`SHIFT_REG___(param.value, params_.value[offset+width-1:offset], \
              DELAY0, param``_delay_u); \
`SHIFT_REG___(param.info_master.value, params_.info, DELAY0, \
              param``_info_delay_u); \
logic param``en0;\
logic param``en1;\
`REG(param``en0, params_.info.last_tile_k & params_.info.new_tile_k, DELAY0); \
`REG(param``en1, inputs_d.info.last_tile_k \
     & inputs_d.info.new_tile_k, DELAY0 -1); \
double_vecbuf #(SZI, width, width) param``_u \
(.q(_``param``_vec.value), .d(param.value), \
 .en({param``en1, param``en0}),\
 .clk, .resetn); \
`REG2_(param``_vec.value, _``param``_vec.value, param``_vec_value, _DELAY1); \
`REG2_(param``_vec.info_master.value, \
       _``param``_vec.info, param``_vec_info, _DELAY1);


module quantization import globals::*;
    // performs bias, quantization rescaling, and activation0
    // io shapes: Ajvec q, Civec d, PostGemmParams params
    #(BUF_DEPTH, SAME_CLK, `IMPORT_ARITH)
    (data q, d, params,
     fifo_array_bus results,
     input logic topclk, slowclk, resetn);
    logic        clk; assign clk = slowclk;
    typedef struct packed {
        logic [SZI-1:0][C_WIDTH-1:0] d;
        Info info;
        logic                        valid;
    }FromTopD;
    typedef struct                   packed {
        // Cjvec d;
        logic [$bits(PostGemmParams)-1:0] d;
        Info info;
        logic                             valid;
    }FromTopParams;
    typedef struct                        packed {
        logic [SZI-1:0][A_WIDTH-1:0]      q;
        Info qinfo;
        logic                             valid;
    }ToTop;
    FromTopD fromtop_d_topclk, inputs_d, _inputs_d;
    FromTopParams fromtop_params_topclk,
        inputs_params, _inputs_params;
    ToTop totop_topclk, outputs, outputs_;
    localparam                            DELAY0_ = 0;
    localparam                            DELAY00_ = 0;
    localparam                            DELAY000_ = 1;
    localparam                            DELAY1_ = 1;
    logic [MIN_TILE_SIZE_N-1:0]           d_last_tile_k_vec;
    logic [MIN_TILE_SIZE_N-1:0]           params_last_tile_k_vec;
    `SHIFTVEC2(d_last_tile_k_vec, d.info.last_tile_k, TRUE, RIGHT, 0, topclk);
    `SHIFTVEC2(params_last_tile_k_vec,
               params.info.last_tile_k, TRUE, RIGHT, 0, topclk);
    `REG(outputs_, outputs, DELAY000_);
    `REG(inputs_d, _inputs_d, DELAY0_);
    `REG(inputs_params, _inputs_params, DELAY00_);
    `REG(fromtop_d_topclk,
         {d.value, d.info, |d_last_tile_k_vec},
         DELAY1_, topclk);
    `REG(fromtop_params_topclk,
         {params.value, params.info,
          |params_last_tile_k_vec},
         DELAY1_, topclk);
    assign {q.value, q.info_master.value, filler} = totop_topclk;
    assign outputs.valid = outputs.qinfo.valid;
    clock_crossing_data #(.A2B(FromTopD), .B2A(ToTop),
                          .VALID_MEANS_NEW_DATA(TRUE),
                          .DEPTH_A2B(BUF_DEPTH),
                          .SAME_CLK(SAME_CLK)) clock_crossing_data_d_u
        (
         .clka_a2b(fromtop_d_topclk), .clkb_a2b(_inputs_d),
         .clka_b2a(totop_topclk), .clkb_b2a(outputs_),
         .clka(topclk), .clkb(slowclk), .resetn);
    clock_crossing_data #(.A2B(FromTopParams), .B2A(ToTop),
                          .VALID_MEANS_NEW_DATA(TRUE),
                          .DEPTH_A2B(BUF_DEPTH),
                          .SAME_CLK(SAME_CLK))
    clock_crossing_data_params_u
        (
         .clka_a2b(fromtop_params_topclk), .clkb_a2b(_inputs_params),
         .clka(topclk), .clkb(slowclk), .resetn);

    localparam                            D_DELAY = 3;
    localparam                            DELAY0000 = 1;
    localparam                            DELAY000 = 1;
    localparam                            DELAY00 = 1;
    localparam                            DELAY0 = 2;
    localparam                            DELAY1 = 2;
    localparam                            DELAY2 = 2;
    localparam                            DELAY3 = 0;
    localparam                            DELAY4 = 1;
    localparam                            DELAY5 = 0;
    localparam                            DELAY6 = 2;
    data #(PostGemmParams) params_(.*);
    signal #(Info) params_loaded(.*);
    import Instruc::*;
    `PARAM_BUF(za_bk, ZA_BK_OFFSET, ZA_BK_WIDTH, DELAY000);
    `PARAM_BUF(m_shift, M_SHIFT_OFFSET, M_SHIFT_WIDTH, DELAY000+DELAY00);
    `PARAM_BUF(m_val, M_VAL_OFFSET, M_VAL_WIDTH,
               DELAY000+DELAY00+DELAY0+DELAY1);
    `PARAM_BUF(activation_sel, ACTIVATION_OFFSET, ACTIVATION_WIDTH,
               DELAY000+DELAY00+DELAY0+DELAY1+DELAY2);
    `PARAM_BUF(zc, ZC_OFFSET, ZC_WIDTH,
               DELAY000+DELAY00+DELAY0+DELAY1+DELAY2+DELAY3+DELAY4+DELAY5);
    `REG2_(params_.value, inputs_params.d, params_value, DELAY0000);
    `REG2_(params_.info_master.value, inputs_params.info, params_info,
           DELAY0000);
    `SHIFT_REG___(params_loaded.value, params_.info, SZI-1, params_info);
    logic [SZI-1:0][C_WIDTH-1:0]          d_;
    logic [SZI-1:0][Instruc::M_SHIFT_WIDTH-1:0] m_shift_;
    logic [SZI-1:0][C_WIDTH-1:0]                res_za_bk;
    logic [SZI-1:0][A_WIDTH+3-1:0]              res_m_shift;
    logic [SZI-1:0][C_WIDTH+8+1-1:0]            res_m_mult;
    logic [SZI-1:0][A_WIDTH:0]                  activation;
    logic [SZI-1:0][A_WIDTH:0]                  activation0;
    logic [SZI-1:0][A_WIDTH:0]                  res_m_mult_shift;
    logic [SZI-1:0][Instruc::M_SHIFT_WIDTH-1:0] shift1;
    data #(Layeriovec) triangle_q(.clk, .resetn);
    data #(Layeriovec) triangle_d(.clk, .resetn);
    triangle_buf #(.SLOPE(-1)) c_triangle_u
        (.q(triangle_q), .d(triangle_d));
    assign outputs.q = triangle_q.value;
    assign outputs.qinfo = triangle_q.info;
    for (genvar I=0; I<SZI; I++) begin : g0
        logic [A_WIDTH:0]                              _activation;
        logic [C_WIDTH+8+1-1:0]                        multa, multb, multc;
        logic [M_VAL_WIDTH + A_WIDTH+3-1-1:0]          _multc;
        `REG3(d_[I], d_, inputs_d.d[I], D_DELAY);
        `SHIFT_REG___(res_za_bk[I], $signed(d_[I])
                      - $signed(za_bk_vec.value[I]) ,
                      DELAY00+DELAY0, res_za_bk);
        `REG3(m_shift_[I], m_shift_, m_shift_vec.value[I] - A_WIDTH, DELAY0);
        `SHIFT_REG___(res_m_shift[I], $signed(res_za_bk[I])>>>m_shift_[I],
                      DELAY1, a00);
        assign _multc
            = $signed(m_val_vec.value[I]) * $signed(res_m_shift[I]);
        assign multc = $signed(_multc);
        `REG2_(res_m_mult[I], multc, res_m_mult, DELAY2);
        `SHIFT_REG___(res_m_mult_shift[I], $signed(res_m_mult[I])>>>A_WIDTH,
                      DELAY3, a01);
        always_comb begin
            _activation = signed'(res_m_mult_shift[I]);
            if (res_m_mult_shift[I][A_WIDTH] && |activation_sel_vec.value[I])
                _activation = '0;
        end
        `REG2_(activation0[I], _activation, activation0, DELAY4)
        `SHIFT_REG___(activation[I], signed'(activation0[I]), DELAY5, a1);
        `SHIFT_REG___(triangle_d.value[I],
                      $signed(activation[I]) + $signed(zc_vec.value[I]),
                      DELAY6, a2);
    end
    localparam MODULE_DELAY = D_DELAY+DELAY00
               + DELAY1+DELAY0+DELAY2+DELAY3
               + DELAY4+DELAY5+DELAY6;
    `REG2_(triangle_d.info_master.value, inputs_d.info, qinfo, MODULE_DELAY);
    localparam RESULTS_SEL = RxTx::QUANTIZATION_RESULTS_SEL;
    if (SIM | USE_RESULT_FIFOS_FULL) begin : sim
        data #(Ajvec) q_(.clk, .resetn);
        `WORDSWAP2(q_, q);
        `ASSIGN_RESULT(RESULTS_SEL, q_, topclk);
    end
endmodule
