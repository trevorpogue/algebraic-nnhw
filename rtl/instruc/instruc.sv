`include "../top/define.svh"


module instruc import globals::*;
    #(`IMPORT_ARITH)
    (fifobus host_instruc,
     fifobus layerio,
     fifobus weight,
     fifobus post_gemm_params,
     fifobus layer_params,
     fifo_array_bus layerio_rd_instrucs,
     fifo_array_bus layerio_wr_instrucs,
     fifobus weight_rd_instruc,
     fifobus post_gemm_params_rd_instruc,
     fifobus top_instruc,
     input logic [TOTAL_SOFT_RESETS-1:0] soft_resetns,
     input logic start, topclk, slowclk, resetn, hard_resetn
     );
    // Recieves and decodes instructions from pcie that contain information
    // like the weights or the tiling parameters which tell the memory
    // controller  how to traverse through the data.
    // globals instructions are received straight from pcie, then this module
    // decodes them into separate instructions for the gemm memory and
    // arithmetic_unit (sys_arr and post_gemmm_arith_u unit),

    import Instruc::*;
    logic        clk; assign clk = slowclk;
    opcodetype opcode;
    bodylentype bodylen, bodylen_m1, bodylen_m1_d, body_word_count;
    decoder_statetype state, next_state;
    typedef struct packed {
        logic      start;
        logic      valid;
    }FromTop;
    FromTop fromtop_topclk, fromtop_bottomclk;
    assign fromtop_topclk = {start, 1'b1};
    clock_crossing_data #(FromTop, FromTop, FALSE) clock_crossing_data_u
      (.clka_a2b(fromtop_topclk), .clkb_a2b(fromtop_bottomclk),
       .clka(topclk), .clkb(slowclk), .resetn);

    //// FSM logic ////
    logic          system_resetting, start_reset;
    logic          done_reset, got_run_instruc;
    logic          host_qvalid;
    assign host_qvalid = host_instruc.q.info.valid;
    assign got_run_instruc
      = (`in(GET_BODY)
         & (opcode == TOP_INSTRUC_OPCODE)
         & host_qvalid
         & (host_instruc.q.value[TOP_INSTRUC_WIDTH-1:0]
            == RUN_INSTRUC_VALUE));

    assign start_reset
      = ((opcode == TOP_INSTRUC_OPCODE)
         && `in(GET_BODY)
         & host_qvalid
         && (host_instruc.q.value & RESET_INSTRUC_MASK));

    `POSEDGE(done_reset_posedge, done_reset);
    `ONOFF2(system_resetting, start_reset, done_reset_posedge, 1, 0,
            clk, hard_resetn);
    `POSEDGE__(start_posedge, fromtop_bottomclk.start);
    assign next_state
      =
       `in(IDLE) & start_posedge? GET_HEADER:
       `in(IDLE)? IDLE:
       !host_qvalid? state:
       `in(GET_HEADER)? GET_BODY:
       got_run_instruc? IDLE:
       (body_word_count == bodylen_m1)
         | ((bodylen == 1) & !system_resetting)? GET_HEADER:
       state;

    `REG(bodylen_m1, bodylen_m1_d, 0);
    always_comb begin
        bodylen_m1_d = system_resetting? '1:
                       `in(GET_HEADER)? host_instruc.q.value:
                       {opcode, bodylen};
        bodylen_m1_d = bodylen - 1;
    end
    always_ff @(posedge clk or negedge resetn) begin
        if (~resetn) begin
            {opcode, bodylen} <= '0;
            state <= IDLE;
            body_word_count <= '0;
            done_reset <= 1'b0;
        end else begin
            done_reset <= 1'b1;
            state <= next_state;
            {opcode, bodylen}
              <=
                system_resetting? {opcode, bodylen}:
                `in(IDLE)? '0:
                !host_qvalid? {opcode, bodylen}:
                `in(GET_HEADER)? host_instruc.q.value:
                {opcode, bodylen};
            body_word_count
              <=
                system_resetting? body_word_count:
                `in(IDLE)? '0:
                !host_qvalid? body_word_count:
                `to(GET_HEADER)? '0:
                `in(GET_BODY)? body_word_count + 'b1:
                body_word_count;
        end
    end

    fifobus #(.D(HostData), .Q(Layeriovec)
              ,.DEPTH(INSTRUC_FIFOS_DEPTH)
              ) _layerio(.clk, .resetn);
    fifobus #(.D(HostData), .Q(Weightvec)
              ,.DEPTH(INSTRUC_FIFOS_DEPTH)
              ) _weight(.clk, .resetn);
    fifobus #(.D(HostData), .Q(PostGemmParams)
              ,.DEPTH(INSTRUC_FIFOS_DEPTH)
              ) _post_gemm_params
      (.clk, .resetn);
    fifobus #(.Q(Layeriovec)
              ,.DEPTH(INSTRUC_FIFOS_DEPTH)
              ,.USE_RDWR_CLKS(TRUE)
              ) _layerio2(.clk, .resetn);
    fifobus #(.Q(Weightvec)
              ,.DEPTH(INSTRUC_FIFOS_DEPTH)
              ,.USE_RDWR_CLKS(TRUE)
              ) _weight2(.clk, .resetn);
    fifobus #(.Q(PostGemmParams)
              ,.DEPTH(INSTRUC_FIFOS_DEPTH)
              ,.USE_RDWR_CLKS(TRUE)
              ) _post_gemm_params2
      (.clk, .resetn);
    assign _layerio2.wrclk = clk;
    assign _layerio2.rdclk = topclk;
    assign _weight2.wrclk = clk;
    assign _weight2.rdclk = topclk;
    assign _post_gemm_params2.wrclk = clk;
    assign _post_gemm_params2.rdclk = topclk;
    `FIFO(_layerio);
    `FIFO(_weight);
    `FIFO(_post_gemm_params);
    if (INSTRUC_CLK_FREQ == TOP_CLK_FREQ) begin
        `CONNECT_FIFOS1(layerio, _layerio, topclk);
        `CONNECT_FIFOS1(weight, _weight, topclk);
        `CONNECT_FIFOS1(post_gemm_params, _post_gemm_params, topclk);
    end else begin
        `CONNECT_FIFOS1(_layerio2, _layerio);
        `CONNECT_FIFOS1(_weight2, _weight);
        `CONNECT_FIFOS1(_post_gemm_params2, _post_gemm_params);
        `IPFIFO(_layerio2);
        `IPFIFO(_weight2);
        `IPFIFO(_post_gemm_params2);
        `CONNECT_FIFOS1(layerio, _layerio2, topclk);
        `CONNECT_FIFOS1(weight, _weight2, topclk);
        `CONNECT_FIFOS1(post_gemm_params, _post_gemm_params2, topclk);
    end

    `FIFOBUS_CP(_weight_rd_instruc, weight_rd_instruc);
    `FIFOBUS_CP(_post_gemm_params_rd_instruc, post_gemm_params_rd_instruc);
    `FIFOBUS_CP(_layer_params, layer_params);
    `FIFOBUS_CP(_top_instruc, top_instruc);
    localparam        FMAX_DELAY0 = 0;
    fifopad #(FMAX_DELAY0) weight_rd_instruc_fifopad_u
      (weight_rd_instruc, _weight_rd_instruc);
    fifopad #(FMAX_DELAY0) post_gemm_params_rd_instruc_fifopad_u
      (post_gemm_params_rd_instruc, _post_gemm_params_rd_instruc);
    fifopad #(FMAX_DELAY0) layer_params_fifopad_u
      (layer_params, _layer_params);
    fifopad #(FMAX_DELAY0) top_instruc_fifopad_u
      (top_instruc, _top_instruc);

    `CONNECT_FIFO_ARRAY2(layerio_rd_instrucs, layerio_rd_instrucs.I);
    `CONNECT_FIFO_ARRAY2(layerio_wr_instrucs, layerio_wr_instrucs.I);
    `FOR(genvar, I, layerio_wr_instrucs.I) begin
        logic resetn_;
        assign resetn_ = soft_resetns[I];
        `IPFIFO___(layerio_wr_instrucs.ios[I], wrfifo_I, TRUE, fifo, resetn_);
        `IPFIFO___(layerio_rd_instrucs.ios[I], rdfifo_I, TRUE, fifo, resetn_);
        assign layerio_wr_instrucs.ios[I].rdclk = layerio_wr_instrucs.rdclk;
        assign layerio_wr_instrucs.ios[I].wrclk = layerio_wr_instrucs.wrclk;
        assign layerio_rd_instrucs.ios[I].rdclk = layerio_rd_instrucs.rdclk;
        assign layerio_rd_instrucs.ios[I].wrclk = layerio_rd_instrucs.wrclk;
    end
    `IPFIFO(_weight_rd_instruc);
    `IPFIFO(_post_gemm_params_rd_instruc);
    `IPFIFO(_layer_params);
    `IPFIFO(_top_instruc);

    //// fifo logic ////
    `define FIFOS(x) { \
                       top_instruc.x, \
                       _weight.x, \
                       _post_gemm_params.x, \
                       post_gemm_params_rd_instruc.x, \
                       weight_rd_instruc.x, \
                       layerio_rd_instrucs.x[2], \
                       layerio_rd_instrucs.x[1], \
                       layerio_rd_instrucs.x[0], \
                       layerio_wr_instrucs.x[2], \
                       layerio_wr_instrucs.x[1], \
                       layerio_wr_instrucs.x[0], \
                       layer_params.x, \
                       _layerio.x \
                       }

    `define OPCODE_CASE(opcode, x) \
    ( \
      (opcode == LAYERIO_OPCODE)? _layerio.x: \
      (opcode == LAYER_PARAMS_OPCODE)? _post_gemm_params.x: \
      (opcode == LAYERIO0_WR_INSTRUC_OPCODE)? layerio_wr_instrucs.x[0]: \
      (opcode == LAYERIO1_WR_INSTRUC_OPCODE)? layerio_wr_instrucs.x[1]: \
      (opcode == LAYERIO2_WR_INSTRUC_OPCODE)? layerio_wr_instrucs.x[2]: \
      (opcode == LAYERIO0_RD_INSTRUC_OPCODE)? layerio_rd_instrucs.x[0]: \
      (opcode == LAYERIO1_RD_INSTRUC_OPCODE)? layerio_rd_instrucs.x[1]: \
      (opcode == LAYERIO2_RD_INSTRUC_OPCODE)? layerio_rd_instrucs.x[2]: \
      (opcode == WEIGHT_RD_INSTRUC_OPCODE)? weight_rd_instruc.x: \
      (opcode == POST_GEMM_PARAMS_RD_INSTRUC_OPCODE)? \
      post_gemm_params_rd_instruc.x: \
      (opcode == POST_GEMM_PARAMS_OPCODE)? _post_gemm_params.x: \
      (opcode == WEIGHT_OPCODE)? weight.x: \
      (opcode == TOP_INSTRUC_OPCODE)? top_instruc.x: \
      '1)

    `define ASSIGN_FIFOS(x, y, nmspc) \
    `REG2_(top_instruc.x, y, top_instruc_``nmspc); \
    `REG2_(_weight.x, y, _weight_``nmspc); \
    `REG2_(_post_gemm_params.x, y, _post_gemm_params_``nmspc); \
    `REG2_(post_gemm_params_rd_instruc.x, y, \
           post_gemm_params_rd_instruc_``nmspc); \
    `REG2_(weight_rd_instruc.x, y, weight_rd_instruc_``nmspc); \
    `REG2_(layerio_rd_instrucs.x[2], y, layerio2_rd_instruc_``nmspc); \
    `REG2_(layerio_rd_instrucs.x[1], y, layerio1_rd_instruc_``nmspc); \
    `REG2_(layerio_rd_instrucs.x[0], y, layerio0_rd_instruc_``nmspc); \
    `REG2_(layerio_wr_instrucs.x[2], y, layerio2_wr_instruc_``nmspc); \
    `REG2_(layerio_wr_instrucs.x[1], y, layerio1_wr_instruc_``nmspc); \
    `REG2_(layerio_wr_instrucs.x[0], y, layerio0_wr_instruc_``nmspc); \
    `REG2_(layer_params.x, y, layer_params_``nmspc); \
    `REG2_(_layerio.x, system_resetting? '0 : y, _layerio_``nmspc);

    logic [TOTAL_OUT_FIFOS-1:0] wrreq;
    logic                       rdready;
    always_comb begin
        rdready = ~`OPCODE_CASE(opcode, half_full)
        & !system_resetting & !`to(IDLE) & !`in(IDLE);
        wrreq = '0;
        wrreq[opcode] = host_qvalid;
    end
    `REG2_(host_instruc.rdreq, ~host_instruc.empty & rdready,
           host_instruc_rdreq, 0);
    `REG2_(`FIFOS(wrreq),
           wrreq & {TOTAL_OUT_FIFOS{`in(GET_BODY)}},
           fifos_wrreq);
    `ASSIGN_FIFOS(d.value, host_instruc.q.value, d_value);
    `undef ASSIGN_FIFOS
    `undef FIFOS
endmodule


module instruc_fields_loader
  #(
    TOTAL_FIELDS, FIELD_WIDTH,
    LOAD_DELAY=1,
    type Instruc = logic [TOTAL_FIELDS-1:0][FIELD_WIDTH-1:0]
    )
    (fifobus instruc,
     output Instruc q, logic empty, logic qvalid,
     input logic load, clk, resetn);
    Instruc instruc_buf;
    Instruc _q;
    Instruc __q;
    logic        _load;
    //
    `REG(_load, load & !empty, 0);
    logic        valid;
    `REG(valid, instruc.rdreq);
    `SHIFTVEC_EN_(instruc_buf, instruc.q.value, valid);
    logic [$clog2(TOTAL_FIELDS):0] instruc_buf_len;
    logic                          instruc_buf_almost_full;
    assign instruc.rdreq = !instruc.empty & !instruc_buf_almost_full;
    assign instruc_buf_almost_full = instruc_buf_len == TOTAL_FIELDS;
    always_ff @(posedge clk or negedge resetn) if (!resetn) begin
        instruc_buf_len <= '0;
        __q <= '0;
        empty <= '1;
    end else begin
        if (instruc.rdreq)
          instruc_buf_len <= instruc_buf_len + 1;
        if (instruc_buf_almost_full)
          empty <= '0;
        if (_load) begin
            instruc_buf_len <= 0;
            __q <= instruc_buf;
            empty <= '1;
        end
    end
    always_comb begin
        foreach(instruc_buf[I])
          _q[I] = __q[TOTAL_FIELDS-I-1];
    end
    `REG(q, _q, LOAD_DELAY-1);
    `POSEDGE(qvalid, _load, LOAD_DELAY);
endmodule
