// =======================================================
//  Written & Designed by Trevor Pogue
// ======================================================

`include "define.svh"
`include "../../rtl/top/synth_agents.svh"


module top_dut import globals::*;
    #(`IMPORT_ARITH)
    (`include "ports.sv",
     output logic qout,
     input logic din
`ifdef SIM
     ,input logic padding_clk, pooling_clk, quantization_clk,
     input logic layeriomem_clk, weightmem_clk, instruc_clk,
     input logic clk
`else
`ifdef TEST_FMAX
     ,input logic padding_clk, pooling_clk, quantization_clk,
     input logic layeriomem_clk, weightmem_clk, instruc_clk,
     input logic clk
`else
     ,output logic padding_clk, pooling_clk, quantization_clk,
     output logic layeriomem_clk, weightmem_clk, instruc_clk,
     output logic clk
`endif
`endif
     // input logic resetn
     );
    import Instruc::HostData;
    import RxTx::*;
`ifdef SIM
    // for cocotb to read:
    localparam    LAYERIOMEM_CLK_DIV_ = LAYERIOMEM_CLK_DIV;
    localparam    WEIGHTMEM_CLK_DIV_ = WEIGHTMEM_CLK_DIV;
    localparam    TOP_CLK_FREQ_ = TOP_CLK_FREQ;
    localparam    LAYERIOMEM_CLK_FREQ_ = TOP_CLK_FREQ/LAYERIOMEM_CLK_DIV;
    localparam    WEIGHTMEM_CLK_FREQ_ = TOP_CLK_FREQ/WEIGHTMEM_CLK_DIV;
    localparam    POOLING_CLK_FREQ_ = POOLING_CLK_FREQ;
    localparam    PADDING_CLK_FREQ_ = PADDING_CLK_FREQ;
    localparam    QUANTIZATION_CLK_FREQ_ = QUANTIZATION_CLK_FREQ;
    localparam    INSTRUC_CLK_FREQ_ = INSTRUC_CLK_FREQ;
    localparam    USE_SOFT_RESET_ = USE_SOFT_RESET;
`endif
    logic         resetn;
    logic         clk50, clk125, rxtx_clk;
    logic         reset, hard_resetn, hard_reset;
    logic [TOTAL_SOFT_RESETS-1:0] soft_resets;
    logic [TOTAL_SOFT_RESETS-1:0] soft_resetns;
    logic                         start, layer_params_valid;
    logic                         layer_params_loader_empty;
    logic                         _wrote_layerio_layer;
    logic                         input_layeriomem_wrote_layer;
    logic                         wrote_inference;
    logic [1023:0]                d;
    LayerParams layer_params_q;
    LayerParams __layer_params_q;
    LayerParamsFifoQ _layer_params_q;
    TopInstruc regs, regwr;

    // result fifo
    fifobus #(.Q(Layeriovec), .DEPTH(RESULT_FIFO_DEPTH)
              ,.USE_RDWR_CLKS(TRUE)) result(.*);

    // top_instruc fifo
    fifobus #(.Q(TopInstruc), .DEPTH(512)
              ,.USE_RDWR_CLKS(TRUE)) top_instruc(.clk, .resetn(hard_resetn));
    assign top_instruc.wrclk = instruc_clk;
    assign top_instruc.rdclk = clk;

    assign regwr = top_instruc.q.info.valid? top_instruc.q.value : '0;
    `REG_COND(regs, top_instruc.q.info.valid, top_instruc.q.value, regs);
    `REG__(top_ready, !result.half_full);

    //// interfaces ////////////////////////////////////////////
    `IPFIFO(result);
    assign result.rdclk = rxtx_clk;
    assign result.wrclk = clk;
    fifo_array_bus #(.I(RxTx::TOTAL_RESULT_FIFOS),
                     .Q(Layeriovec), .DEPTH(RESULT_FIFOS_DEPTH)) results
        (.clk, .resetn);

    // result_ fifo
    fifobus #(.Q(HostData), .D(Layeriovec), .DEPTH(512)) result_
        (.clk(rxtx_clk), .resetn);
    `FIFO(result_);

    // host_instruc fifo
    fifobus #(.Q(HostData), .DEPTH(512)
              ,.USE_RDWR_CLKS(TRUE)) host_instruc(.clk, .resetn(hard_resetn));
    `IPFIFO(host_instruc);
    assign host_instruc.rdclk = instruc_clk;
    assign host_instruc.wrclk = rxtx_clk;

    // data fifos
    `INSTRUC_FIFOBUS(layerio, Layeriovec);
    `INSTRUC_FIFOBUS(input_layerio, Layeriovec);
    `INSTRUC_FIFOBUS(weight, Weightvec);
    `INSTRUC_FIFOBUS(post_gemm_params, PostGemmParams);

    // layer_params fifo
    fifobus #(.Q(LayerParam), .DEPTH(INSTRUC_FIFOS_DEPTH)
              ,.USE_RDWR_CLKS(TRUE)) layer_params
        (.clk, .resetn);
    assign layer_params.wrclk = instruc_clk;
    assign layer_params.rdclk = clk;

    // mem instruc fifos
    `LAYERIOMEM_INSTRUC_FIFOBUS(layerio_rd_instrucs);
    `LAYERIOMEM_INSTRUC_FIFOBUS(layerio_wr_instrucs);
    `WEIGHTMEM_INSTRUC_FIFOBUS(weight_rd_instruc);
    `WEIGHTMEM_INSTRUC_FIFOBUS(post_gemm_params_rd_instruc);

    // rxtx fifos
    fifobus #(.Q(HostData), .DEPTH(512)) rx
        (.clk(rxtx_clk), .resetn(hard_resetn));
    fifobus #(.Q(HostData), .DEPTH(512)) tx
        (.clk(rxtx_clk), .resetn);
    logic                         _done_inference_section;
`include "interconnect.sv"
    if (FAST_COMPILE) begin
        assign rxtx_clk = clk;
        `IPFIFO(rx);
        `IPFIFO(tx);
    end else if (SIM) begin
        `IPFIFO(rx);
        `IPFIFO(tx);
        assign tx.rdreq = 1;
    end else begin
        pcie rxtx_u (.pcie, .rx, .tx, .clk(rxtx_clk));
    end

    //// modules & logic ////////////////////////////////////////////
    if (FAST_COMPILE) begin
        `DRIVER(d, din);
        `MONITOR(qout, {layerio.d.value,
                        layerio.wrreq
                        & layer_params_q.islastlayer});
        assign host_instruc.d.value = d;
        assign host_instruc.wrreq = d;
    end else begin
        `CONNECT_FIFOS3(result_, result, rxtx_clk, 1);
        `CONNECT_FIFOS3(tx, result_, rxtx_clk, 1);
        `CONNECT_FIFOS3(host_instruc, rx, rxtx_clk, 1);
    end

    `POSEDGE(start, regs.run);
    `REG2_(top_instruc.rdreq, ~top_instruc.empty, top_instruc_rdreq);

    logic last_layer, last_layer_;
    logic done_inference;
    logic [CLOG2_MAX_TIMEOUT-1:0] timer;
    logic [$clog2(CLOG2_MAX_TIMEOUT)-1:0] default_timeout_bit;
    logic                                 timeout, _timeout,
                                          done_inference_section;
    `ONOFF__(timer_en, regwr.start_timer | regwr.restart_timer,
             regwr.stop_timer, 1, clk, hard_resetn);
    `COUNTER(timer, timer_en, regwr.restart_timer, clk, 0, hard_resetn);
    assign default_timeout_bit = 29;
    `REG_COND(_timeout, regs.timeout_bit, timer[regs.timeout_bit],
              timer[default_timeout_bit]);
    `POSEDGE(timeout, _timeout);
    `ONOFF__(done_inference_section_onoff, _done_inference_section,
             done_inference_section)
    `POSEDGE(done_inference_section, done_inference_section_onoff
             & layer_params_qvalid, 1);
    localparam                            FINISH_WRITING2FIFO_DELAY = 10;
    `REG(last_layer_, last_layer, FINISH_WRITING2FIFO_DELAY);
    `REG__(last_elm, layerio.d.info.last_elm,
           FINISH_WRITING2FIFO_DELAY);
    `REG(_done_inference_section,
         timeout | (last_elm & layer_params_q.islastlayer));
    assign last_layer = layerio.d.info.valid
                        & layer_params_q.islastlayer
                        & layer_params_q.islast_inbatch;
    `REG(done_inference, layerio.d.info.last_elm
         & layer_params_q.islastlayer
         & layer_params_q.islast_inbatch);
    Tiler::DIGIT c_load_layer_params, c_load_instrucs;
    logic                                 load_instrucs;
    logic                                 load_instrucs_;
    `SIMCOUNTER(c_load_layer_params, load_layer_params, '0);
    `SIMCOUNTER(c_load_instrucs, load_instrucs_, '0);
    logic [6:0]                           doing_reset;
    `REG__(got_reset, |regwr.resets)
    `COUNTER(doing_reset, got_reset | |doing_reset,
             |regwr.resets, clk, 0, hard_resetn);
    logic                                 do_record_timer;
    `ONOFF(do_record_timer, regwr.record_timer);
    if (USE_RESULT_FIFOS) begin : resparser
        result_parser result_parser_u
            (.result, .results,
             .start((results.half_full & !doing_reset & !regwr.resets)
                    | regwr.get_results),
             .clk, .resetn);
        data #(logic [CLOG2_MAX_TIMEOUT-1:0]) timer_data(.clk, .resetn);
        assign timer_data.value = timer;
        assign timer_data.info_master.value = regwr.record_timer;
        if (USE_RESULT_FIFOS_FULL) begin
        end else begin
            `ASSIGN_RESULT(PERF_RESULTS_SEL, timer_data);
            `SYNTHWORDSWAP_(results.d.value[RESULT_RESULTS_SEL], resd,
                            layerio.d.value);
            `REG3(results.wrreq[RESULT_RESULTS_SEL], reswrreq, last_layer);
        end
    end else begin : resparser
        if (RESULT_IO == "RESULT") begin : io
            Layeriovec out;
            always_comb begin if (do_record_timer) begin
                out = done_inference? timer : layerio.d.value;
            end else begin
                out = layerio.d.value;
            end end
            `REG3(result.wrreq, reswrreq, last_layer
                  | (do_record_timer & done_inference));
            `SYNTHWORDSWAP_(result.d.value, resd, out);
        end else if (RESULT_IO == "C") begin : io
            `REG3(result.wrreq, reswrreq,
                  layerio.d.info.valid);
            `SYNTHWORDSWAP_(result.d.value, resd,
                            layerio.d.value);
        end else if (RESULT_IO == "A") begin : io
            `REG3(result.wrreq, reswrreq,
                  layerio.q.info.valid);
            `SYNTHWORDSWAP_(result.d.value, resd,
                            layerio.q.value);
        end else if (RESULT_IO == "B") begin : io
            `REG3(result.wrreq, reswrreq, weight.q.info.valid);
            `SYNTHWORDSWAP_(result.d.value, resd, weight.q.value);
        end else if (RESULT_IO == "POST_GEMM_PARAMS") begin : io
            `REG3(result.wrreq, reswrreq, post_gemm_params.q.info.valid);
            `SYNTHWORDSWAP_(result.d.value, resd, post_gemm_params.q.value);
        end
    end
    logic          arith_wrote_layer;
    `POSEDGE(arith_wrote_layer, _wrote_layerio_layer | load_flag2, 2);
    assign result.d.info_master.value.valid = result.wrreq;
    logic          load_input;
    assign load_input = layer_params_q.new_layer_edge
                        & layer_params_q.load_input;
    `POSEDGE(load_instrucs_, load_instrucs);
    dff_on_off #(.LATENCY(16), .RESET_VAL(1)) load_instruc_u
        (.q(load_instrucs),
         .on(load_input | (_wrote_layerio_layer & layer_params_q.islastlayer)),
         .off(load_instrucs),
         .clk, .resetn);
    instruc #(`EXPORT_ARITH) instruc_u (.soft_resetns,
                                        .start(load_instrucs_),
                                        .host_instruc,
                                        .layerio(input_layerio),
                                        .weight,
                                        .post_gemm_params,
                                        .layer_params,
                                        .layerio_rd_instrucs,
                                        .layerio_wr_instrucs,
                                        .weight_rd_instruc,
                                        .post_gemm_params_rd_instruc,
                                        .top_instruc,
                                        .topclk(clk),
                                        .slowclk(instruc_clk),
                                        .resetn(resetn),
                                        .hard_resetn(hard_resetn)
                                        );
    mem #(`EXPORT_ARITH) mem_u (.layerio,
                                .input_layerio,
                                .input_layeriomem_wrote_layer,
                                .weight,
                                .post_gemm_params,
                                .layerio_rd_instrucs,
                                .layerio_wr_instrucs,
                                .weight_rd_instruc,
                                .post_gemm_params_rd_instruc,
                                .layer_params(layer_params_q),
                                .dramphy,
                                .start,
                                .load(regwr.load),
                                .wrote_layerio_layer(_wrote_layerio_layer),
                                .wrote_inference,
                                .topclk(clk),
                                .layeriomem_clk,
                                .weightmem_clk,
                                .hard_resetn,
                                .soft_resetns,
                                .resetn
                                );

    arith #(TRUE, `EXPORT_ARITH) arith_u
        (.soft_resetns,
         .start,
         .layerio(layerio),
         .results,
         .weight,
         .post_gemm_params,
         .wrote_inference('0),
         .layer_params(layer_params_q),
         .wrote_layerio_layer(arith_wrote_layer),
         .topclk(clk),
         .top_ready,
         .pooling_clk, .padding_clk, .quantization_clk,
         .resetn
         );
endmodule
