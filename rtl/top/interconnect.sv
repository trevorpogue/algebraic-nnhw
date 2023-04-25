// this file is for supporting top level logic (pll, reset setup etc)
// or for the overly verbose setup (emif, and to a lesser extent, pcie)

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
pcie_controller_bus pcie (.perstn(pcie_perstn),
                          .refclk(pcie_refclk),
                          .rx(pcie_rx),
                          .tx(pcie_tx),
                          .led(led));

assign clk50 = CLK_50M_FPGA;
assign clk125 = CLK_ENET_FPGA_P;

`ifndef SIM
logic padding_clk, pooling_clk, quantization_clk;
logic layeriomem_clk, weightmem_clk, instruc_clk;
logic clk;

`ifndef TEST_FMAX
logic _padding_clk, _quantization_clk, _pooling_clk, _instruc_clk;
pll
`include  "pll_inst.sv"
    assign instruc_clk = INSTRUC_CLK_FREQ == TOP_CLK_FREQ? clk:_instruc_clk;
assign pooling_clk = POOLING_CLK_FREQ == TOP_CLK_FREQ? clk:_pooling_clk;
assign padding_clk = PADDING_CLK_FREQ == TOP_CLK_FREQ? clk:_padding_clk;
assign quantization_clk = QUANTIZATION_CLK_FREQ == TOP_CLK_FREQ?
                          clk:_quantization_clk;
`endif
`endif

assign hard_resetn = pb[0];
assign hard_reset = !hard_resetn;
fifobus #(.Q(logic [TOTAL_SOFT_RESETS-1:0])
          ,.USE_RDWR_CLKS(TRUE)
          ,.DEPTH(RESET_FIFO_DEPTH)) resetfifo
    (.clk, .resetn);
`IPFIFO(resetfifo)
assign resetfifo.wrclk = clk;
assign resetfifo.rdclk = clk50;
`POSEDGE_(resetfifo.wrreq, (|top_instruc.q.value.resets
                            & top_instruc.q.info.valid
                            & !resetfifo.half_full),
          1, resetfifo_wrreq);
`REG3(resetfifo.d.value, resetd, top_instruc.q.value.resets);
`REG2_(resetfifo.rdreq, !resetfifo.empty, resetfifo_rdreq, 1, 0, clk50);
`FOR(genvar, I, TOTAL_SOFT_RESETS) begin
    logic [7:0] reset_instruc;
    `SHIFTVEC_(reset_instruc, resetfifo.q.value[I] & resetfifo.q.info.valid,
               clk50);
    always_ff @(posedge clk50) begin
        soft_resets[I] <= |reset_instruc | hard_reset;
    end
end

assign soft_resetns = ~soft_resets;
if (USE_SOFT_RESET) begin
    assign reset = (hard_reset | |soft_resets);
end else begin
    assign reset = hard_reset;
end

assign resetn = !reset;

// layer_param loading logic
typedef struct packed {
    logic      valid;
}FromTop;
typedef struct packed {
    logic      post_gemm_params_rd_instruc_rdreq;
    logic      valid;
}ToTop;
ToTop totop_topclk, totop_weightmemclk;
logic layer_params_qvalid;
assign totop_weightmemclk = {post_gemm_params_rd_instruc.rdreq,
                             post_gemm_params_rd_instruc.rdreq};
clock_crossing_data #(FromTop, ToTop, TRUE, FALSE,
                      TILE_BUF_DEPTH) weightmemclk_clock_crossing_data_u
    (.clka_b2a(totop_topclk), .clkb_b2a(totop_weightmemclk),
     .clka(clk), .clkb(weightmem_clk), .resetn);
assign loadflag = totop_topclk.post_gemm_params_rd_instruc_rdreq;
`ONOFF__(previously_got_loadflag, loadflag);
`POSEDGE__(first_loadflag, loadflag & !previously_got_loadflag);
logic finished_first_layer, layer_params_valid_off;
`ONOFF(finished_first_layer, layerio.d.info.last_elm, layer_params_valid_off);
`REG(layer_params_valid_off,
     _wrote_layerio_layer & layer_params_valid & layer_params_q.islastlayer
     & layer_params_q.islast_inbatch & finished_first_layer);
`ONOFF(layer_params_valid,
       ((_wrote_layerio_layer | first_loadflag))
       & !layer_params_valid_off,
       layer_params_valid_off, 2)
logic load_flag2, load_flag1, load_flag0;
logic load_layer_params;
`ONOFF(load_flag0, (layer_params_q.islastlayer
                    & !layer_params_q.islast_inbatch
                    & wrote_inference & !layer_params_q.in_last_inference),
       load_layer_params);
`ONOFF(load_flag1, input_layeriomem_wrote_layer & layer_params_q.valid,
       load_flag2);
`REG(load_flag2, load_flag0 & load_flag1);
`POSEDGE(load_layer_params,_wrote_layerio_layer | first_loadflag | load_flag2);
instruc_fields_loader #(TOTAL_LAYER_PARAMS, $bits(LayerParam), 2)
layer_params_loader_u
    (.instruc(layer_params),
     .empty(layer_params_loader_empty),
     .load(load_layer_params),
     .qvalid(layer_params_qvalid),
     .clk, .resetn, .q(_layer_params_q));
`REG(layer_params_q, __layer_params_q, 1);
`always_ff2 if (~resetn) begin
    __layer_params_q <= '0;
end else begin
    __layer_params_q.valid <= '0;
    if (layer_params_valid) begin
        __layer_params_q.new_layer_edge <= layer_params_qvalid;
        __layer_params_q.inputmem_size_w_c <= _layer_params_q.inputmem_size_w_c;
        __layer_params_q.inputmem_total_layer_reads <= _layer_params_q.inputmem_total_layer_reads;
        __layer_params_q.inputmem_tile_size_m <= _layer_params_q.inputmem_tile_size_m;
        __layer_params_q.total_inference_writes <= _layer_params_q.total_inference_writes;
        __layer_params_q.in_last_inference <= _layer_params_q.in_last_inference;
        __layer_params_q.load_input <= _layer_params_q.load_input;
        __layer_params_q.tile_size_m <= _layer_params_q.tile_size_m;
        __layer_params_q.size_w_gemm <= _layer_params_q.size_w_gemm;
        __layer_params_q.size_h_gemm <= _layer_params_q.size_h_gemm;
        __layer_params_q.size_w_pool_padding <= _layer_params_q.size_w_pool_padding;
        __layer_params_q.size_h_pool_padding <= _layer_params_q.size_h_pool_padding;
        __layer_params_q.size_w_pooling <= _layer_params_q.size_w_pooling;
        __layer_params_q.size_h_pooling <= _layer_params_q.size_h_pooling;
        __layer_params_q.total_weight_writes_all_layers <= _layer_params_q.total_weight_writes_all_layers;
        __layer_params_q.total_pgp_writes_all_layers <= _layer_params_q.total_pgp_writes_all_layers;
        __layer_params_q.total_weight_reads_all_layers <= _layer_params_q.total_weight_reads_all_layers;
        __layer_params_q.total_pgp_reads_all_layers <= _layer_params_q.total_pgp_reads_all_layers;
        __layer_params_q.total_layerio_reads <= _layer_params_q.total_layerio_reads;
        __layer_params_q.total_weight_reads <= _layer_params_q.total_weight_reads;
        __layer_params_q.hw_size_padding <= _layer_params_q.hw_size_padding;
        __layer_params_q.total_c_padding_writes <= _layer_params_q.total_c_padding_writes;
        __layer_params_q.size_w_c <= _layer_params_q.size_w_c;
        __layer_params_q.c_padding <= _layer_params_q.c_padding;
        __layer_params_q.pool_size <= _layer_params_q.pool_size;
        __layer_params_q.pool_stride <= _layer_params_q.pool_stride;
        __layer_params_q.pool_padding <= _layer_params_q.pool_padding;
        __layer_params_q.avg_pool_denom <= _layer_params_q.avg_pool_denom;
        __layer_params_q.pool_type <= _layer_params_q.pool_type;
        __layer_params_q.islastlayer <= _layer_params_q.islastlayer;
        __layer_params_q.islast_inbatch <= _layer_params_q.islast_inbatch;
        __layer_params_q.layeriomem_wrsel <= _layer_params_q.layeriomem_wrsel;
        __layer_params_q.layeriomem_rdsel <= _layer_params_q.layeriomem_rdsel;
        __layer_params_q.loading_params_valid <= _layer_params_q.loading_params_valid;
        __layer_params_q.valid <= _layer_params_q.valid;
    end
end
