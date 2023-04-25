`include "../top/define.svh"


module weight_reader import globals::*;
    // This module holds the counter tree for controlling the data
    // access patturns for WEIGHT or LAYERIO data blocks
    import Tiler::*;
    #(RDWR_TYPE, DATA_TYPE, ID, DEPTH, BURST_COUNT=1,
      INSTRUC_LOAD_DELAY=2)
    (fifobus master, interface slave, fifobus instruc,
     input DIGIT total_weight_reads_all_layers,
     input logic start, clk, resetn);
    logic [TOTAL_DIGITS-1:0] at_last_values;
    logic [TOTAL_DIGITS-1:0] at_4th_last_values;
    logic [TOTAL_DIGITS-1:0] at_2nd_last_values;
    logic                    load_instruc;
    DIGITS counts;
    DIGIT offset;
    logic [$clog2(DEPTH)-1:0] address;
    logic                     master_req;
    logic                     new_tile_k;
    logic [TOTAL_DIGITS-1:0]  carries;
    logic [TOTAL_DIGITS-1:0]  at_first_values;
    logic                     valid;
    logic                     first_master_req, got_first_master_req;
    logic                     instruc_valid;
    logic                     _instruc_valid;
    logic                     at_last_elm;
    logic                     at_4th_last_elm;
    logic                     instruc_empty;
    logic                     start_or_4th_last_elm;
    logic                     instruc_not_loaded;
    DIGITS strides_normalized;
    DIGITS strides;
    DIGITS sizes;
    Instruc instruc_q;
    logic                     almost_read_full_tile, ready;
    logic                     __master_req, _master_req;
    DIGIT c_total_reads, c_qvalids;
    localparam                type   D = master.D;
    `SIMCOUNTER(c_total_reads, master_req);
    `SIMCOUNTER(c_qvalids, master.q.info.valid);
    fifobus #(.Q(D)) dfifo(.clk, .resetn);
    typedef enum              logic [1:0] {IDLE, GET_INSTRUC, COUNT} State;
    State state, next_state;
    `POSEDGE(load_instruc, (!instruc_empty) & `in(GET_INSTRUC));
    `always_ff2 if (~resetn) state <= IDLE;
    else state <= next_state;
    always_comb begin
        next_state = state;
        case (state)
            IDLE: if (start) next_state = GET_INSTRUC;
            GET_INSTRUC: if (load_instruc) next_state = COUNT;
            COUNT: if (at_last_elm & valid) next_state = GET_INSTRUC;
        endcase
    end
    `REG(master_req, dfifo.q.info.valid, 0);
    D dfifo_d;
    `REG(dfifo_d, master.d.value);
    assign dfifo.d.value = dfifo_d;
    `REG3(dfifo.d.info_master.value, dfifo_info, master.d.info);
    `REG3(dfifo.wrreq, dfifo_wrreq, __master_req);
    `REG3(dfifo.rdreq, dfifo_rdreq,
          `in(COUNT) & `to(COUNT) & slave.ready & !dfifo.empty, 0);
    `INFOFIFO(dfifo, "IPFIFO");
    `REG(ready,
         slave.ready
         & !dfifo.half_full
         & `in(COUNT));
    always_comb begin
        slave.rdreq = master_req;
        master.q.value = slave.q.value;
        slave.rdaddress = address;
        master.rdready = ready;
        master.rdready2 = ready;
        __master_req = master.rdreq;
        master.q.info_master.value = slave.q.info;
        slave.d.info_master.value = master.d.info;
        master.empty = ~slave.ready | !ready;
    end

    localparam DELAY0 = 0;
    `always_comb begin
        offset = instruc_q[TOTAL_DIGITS*2];
    end
    `always_comb begin
        sizes = instruc_q[TOTAL_DIGITS-1:0];
        strides = instruc_q[TOTAL_DIGITS*2-1:TOTAL_DIGITS];
        `FOR(int, I, TOTAL_DIGITS) begin
            strides_normalized[I] = 1;
        end
    end
    multi_digit_counter #(DIGIT_WIDTH, TOTAL_DIGITS, $clog2(DEPTH), ID)
    counter_u
        (.offset(offset),
         .strides(strides),
         .strides_normalized(strides_normalized),
         .sizes(sizes),
         .en(master_req),
         .totalcount(address),
         .stride_valid('1),
         .counts,
         .carries,
         .at_last_values,
         .at_first_values,
         .clk, .resetn(resetn));
    instruc_fields_loader #(TOTAL_PARAMS, DIGIT_WIDTH,
                            INSTRUC_LOAD_DELAY) instruc_loader_u
        (.instruc, .qvalid(_instruc_valid), .empty(instruc_empty),
         .load(load_instruc), .clk, .resetn, .q(instruc_q));
    `POSEDGE(first_master_req, master_req & !got_first_master_req, 0);
    `REG__(new_tile_k_off, new_tile_k & master_req);
    `ONOFF(new_tile_k, carries[MS_TILE_FILL_DIM] | first_master_req,
           new_tile_k_off, 0);
    `ONOFF(got_first_master_req, first_master_req, 0);
    assign valid = master_req;
    assign at_last_elm = &at_last_values;
    `always_comb begin
        master.d.info_master.value.last_w = '0;
        if (sizes[TILE_COUNT_MW_DIM] > 1) begin
            master.d.info_master.value.last_w
                = &at_last_values[TILE_COUNT_MW_DIM:0]
                  & valid;
        end else begin
            master.d.info_master.value.last_w
                = &at_last_values[TILE_FILL_MW_DIM:0] & valid;
        end
    end
    assign master.d.info_master.value.last_elm = &at_last_values
                                                 & valid;
    assign master.d.info_master.value.first_tile_k
        = &at_first_values[MS_TILE_COUNT_K_DIM:LS_TILE_COUNT_K_DIM]
          & valid;
    assign master.d.info_master.value.last_tile_k
        = &at_last_values[MS_TILE_COUNT_K_DIM:LS_TILE_COUNT_K_DIM]
          & valid;
    assign master.d.info_master.value.last_tile_n_elm
        = &at_last_values[MS_TILE_COUNT_N_DIM-1:0] & valid;
    assign master.d.info_master.value.valid = valid;
    assign master.d.info_master.value.new_tile_k = new_tile_k;
endmodule


module weight_writer import globals::*;
    // This module holds the counter tree for controlling the data
    // access patturns for WEIGHT or LAYERIO data blocks
    import Tiler::*;
    #(RDWR_TYPE, DATA_TYPE, ID, DEPTH,
      INSTRUC_LOAD_DELAY=2)
    (fifobus master, interface slave, fifobus instruc,
     input DIGIT total_weight_reads_all_layers,
     input logic start, clk, resetn);
    logic [TOTAL_DIGITS-1:0] at_last_values;
    logic [TOTAL_DIGITS-1:0] at_4th_last_values;
    logic                    load_instruc;
    DIGITS counts;
    DIGIT offset;
    logic [$clog2(DEPTH)-1:0] address;
    logic                     master_req;
    logic                     new_tile_k;
    logic [TOTAL_DIGITS-1:0]  carries;
    logic [TOTAL_DIGITS-1:0]  at_first_values;
    logic                     valid;
    logic                     first_master_req, got_first_master_req;
    logic                     instruc_valid;
    logic                     _instruc_valid;
    logic                     at_last_elm;
    logic                     at_4th_last_elm;
    logic                     instruc_empty;
    logic                     start_or_4th_last_elm;
    DIGITS strides_normalized;
    DIGITS strides;
    DIGITS sizes;
    Instruc instruc_q;
    logic                     almost_read_full_tile, ready;
    logic                     __master_req, _master_req;
    DIGIT c_total_reads, c_qvalids;
    `SIMCOUNTER(c_total_reads, master_req);
    `SIMCOUNTER(c_qvalids, master.q.info.valid);
    localparam                type   D = master.D;
    fifobus #(.Q(D)) dfifo(.clk, .resetn);
    `REG(master_req, dfifo.q.info.valid, 0);
    D dfifo_d;
    `REG(dfifo_d, master.d.value);
    assign dfifo.d.value = dfifo_d;
    `REG3(dfifo.d.info_master.value, dfifo_info, master.d.info);
    `REG3(dfifo.wrreq, dfifo_wrreq, __master_req);
    `REG3(dfifo.rdreq, dfifo_rdreq, ready & !dfifo.empty, 0);
    `INFOFIFO(dfifo, "IPFIFO");
    `REG(ready, !dfifo.half_full);
    always_comb begin
        slave.wraddress = address;
        slave.wrreq = master_req;
        slave.d.value = dfifo.q.value;
        master.full = ~slave.ready;
        master.half_full = ~slave.ready;
        __master_req = master.wrreq;
    end
    counter_digit #($clog2(DEPTH))
    counter_u (.en(master_req),
               .size('1),
               .stride(1),
               .count(address),
               .clk, .resetn(resetn));
    assign instruc_valid = 1;
endmodule


module clock_crossing_weightmem_interconnect
    import globals::*; import Tiler::*;
    #(type Q=logic, integer BURST_COUNT, DATA_TYPE = WEIGHT,
      BUFDEPTH = 1, MEM_DIV=1)
    (fifobus clka_fifo, clkb_fifo, sprambus slave,
     input DIGIT total_layer_reads,
     input DIGIT total_writes,
     input DIGIT total_weight_reads_all_layers_topclk,
     input hard_resetn,
     output DIGIT total_weight_reads_all_layers_memclk,
     input logic start,
     input logic load,
     input logic rdready,
     output logic          mem_q_clk_wrready,
     input logic wrote_layerio_layer,
     input logic new_model,
     input logic layer_params_valid,
     input logic loading_params_valid,
     input logic [$clog2(MAX_TILE_SIZE_M)-1:0] tile_size,
     data mem_q,
     input logic topclk, memclk, resetn);
    logic        clk; assign clk = topclk;
    logic        tile_rd_ready, start_tile_rd, two_tiles_rd_ready;
    logic        clka_wrready, clkb_wrready;
    logic        model_loaded;
    localparam   QFIFO_DEPTH = TILE_BUF_DEPTH;
    typedef Q Q_;
    data #(Q_) q(.clk, .resetn);
    `INSTRUC_FIFOBUS(_clka_fifo, Q_);
    logic        half_full, full;
    `ONOFF(model_loaded, totop_topclk.wrote_layer, new_model,
           1, clk, hard_resetn);
    `ONOFF__(got_1st_start_after_model_loaded, model_loaded & start, new_model,
             1, clk, hard_resetn);
    `POSEDGE__(model_loaded_posedge, model_loaded);
    logic        tilebuf_wrote_layer;
    assign tilebuf_wrote_layer = (model_loaded_posedge |
                                  (got_1st_start_after_model_loaded & start));
    tilebuf #(.Q(Q_),
              .QFIFO_DEPTH(BUFDEPTH),
              .BURST_COUNT(BURST_COUNT),
              .DATA_TYPE(DATA_TYPE)
              ) tile_buf_u
        (// interfaces
         .layerfifo(_clka_fifo),
         .q,
         // outputs
         .half_full(half_full),
         .full(full),
         .tile_rd_ready,
         .two_tiles_rd_ready,
         // inputs
         .wrote_layer(tilebuf_wrote_layer),
         .total_layer_reads(total_layer_reads),
         .tile_size,
         .start_tile_rd,
         .tile_size_valid(layer_params_valid),
         .clk, .resetn
         );
    logic [$clog2(MEM_DIV)-1:0] wrparity;
    `COUNTER(wrparity, 1'b1, wrparity == MEM_DIV-1);
    assign clka_fifo.q.value             = q.value;
    assign clka_fifo.q.info_master.value = q.info;
    assign clka_fifo.full                = full | _clka_fifo.full;
    assign clka_fifo.half_full = half_full | _clka_fifo.half_full | wrparity;
    assign clka_fifo.rdready = tile_rd_ready & model_loaded;
    assign clka_fifo.rdready2 = two_tiles_rd_ready & model_loaded;
    assign clka_fifo.empty = !tile_rd_ready | !model_loaded;
    assign _clka_fifo.wrreq              = clka_fifo.wrreq;
    assign _clka_fifo.d.value            = clka_fifo.d.value;
    `REG(start_tile_rd, clka_fifo.rdreq, 0);
    typedef struct              packed {
        DIGIT total_writes;
        DIGIT total_weight_reads_all_layers;
        logic                   valid;
    }FromTop;
    typedef struct              packed {
        logic                   wrote_layer;
        logic                   valid;
    }ToTop;
    FromTop fromtop_topclk, fromtop_bottomclk;
    ToTop totop_topclk, totop_bottomclk;
    logic                       dummy;
    `REG(fromtop_topclk, {total_writes, total_weight_reads_all_layers_topclk,
                          loading_params_valid});
    assign total_weight_reads_all_layers_memclk
        = fromtop_bottomclk.total_weight_reads_all_layers;
    assign totop_bottomclk.valid = '1;
    localparam                  ASSIGN_CLKA_Q = FALSE;
    clock_crossing_fifobus_interconnect #(.ASSIGN_CLKA_Q(ASSIGN_CLKA_Q))
    clock_crossing_fifobus_interconnect_u
        (.clka_fifo(_clka_fifo), .clkb_fifo,
         .clka_wrready, .clkb_wrready,
         .clka(topclk), .clkb(memclk), .resetn);
    clock_crossing_data
        #(FromTop, ToTop) clock_crossing_data_u
            (.clka_a2b(fromtop_topclk),
             .clkb_a2b(fromtop_bottomclk),
             .clka_b2a(totop_topclk),
             .clkb_b2a(totop_bottomclk),
             .clka(topclk), .clkb(memclk), .resetn);
    logic                       wrote_layer;
    `ONOFF__(got_wrote_layer, wrote_layer, totop_bottomclk.wrote_layer,
             1, memclk);
    assign totop_bottomclk.wrote_layer = got_wrote_layer & rdready;
    wrote_layer_unit #(1, FALSE) wrote_layer_u
        (.size(fromtop_bottomclk.total_writes),
         .wrote_layer(wrote_layer),
         .wrreqs(clkb_fifo.wrreq), .clk(memclk), .resetn);

    typedef struct              packed {
        Q q;
        Info info;
    }ToTopQ;
    ToTopQ totopq_topclk, totopq_bottomclk;
    logic                       dummy2;
    if (DATA_TYPE == WEIGHT) begin
        assign _clka_fifo.q.value = totopq_topclk.q;
        assign _clka_fifo.q.info_master.value = totopq_topclk.info;
        assign totopq_bottomclk = {mem_q.value, mem_q.info};
        clock_crossing_data
            #(.A2B(logic), .B2A(ToTopQ),
              .DEPTH_B2A(BUFDEPTH),
              .VALID_MEANS_NEW_DATA(TRUE),
              .ZERODEFAULT(TRUE)) clock_crossing_q_u
                (.clka_b2a(totopq_topclk),
                 .clkb_b2a(totopq_bottomclk),
                 .clkb_wrready(mem_q_clk_wrready),
                 .clka(topclk), .clkb(mem_q.clk), .resetn);
    end else if (DATA_TYPE == POST_GEMM_PARAMS) begin
        localparam BUFDEPTH = 32;
        fifobus #(.D(PGP2), .Q(PGP),
                  .USE_RDWR_CLKS(TRUE), .DEPTH(BUFDEPTH)) qfifo(.clk, .resetn);
        _fifo_dgtq_faster_rdclk qfifo_u (qfifo);
        assign qfifo.wrclk = memclk;
        assign qfifo.rdclk = topclk;
        assign qfifo.wrreq = mem_q.info.valid;
        assign qfifo.d.value = mem_q.value;
        assign qfifo.rdreq = !qfifo.empty;
        fifobus #(.Q(Info), .D(logic [$bits(Info)*WEIGHTMEM_CLK_DIV-1:0]),
                  .DEPTH(BUFDEPTH),
                  .USE_RDWR_CLKS(TRUE)) info_fifo (.clk, .resetn);
        _fifo_dgtq_faster_rdclk info_fifo_u (info_fifo);
        assign info_fifo.wrclk = memclk;
        assign info_fifo.rdclk = topclk;
        assign info_fifo.wrreq = slave.rdreq;
        Info info1, info0;
        always_comb begin
            `INIT_INFO(info0);
            `INIT_INFO(info1);
            info0.valid = '0;
            info1.valid = '0;
            if (slave.d.info.valid) begin
                info0 = slave.d.info;
                info1 = slave.d.info;
                info0.last_w = 0;
                info0.last_tile_n_elm = 0;
                info0.last_elm = 0;
                info1.new_tile_k = 0;
            end
        end
        assign info_fifo.d.value = {info1, info0};
        assign info_fifo.rdreq = qfifo.rdreq;
        Info info;
        always_comb begin
            `INIT_INFO(info);
            info.valid = info_fifo.q.info.valid;
            if (info.valid) begin
                info = info_fifo.q.value;
            end
        end
        assign _clka_fifo.q.info_master.value = info;
        assign _clka_fifo.q.value = qfifo.q.value;
    end
endmodule


module dram_width_matcher import globals::*;
    #(BUFDEPTH)
    (sprambus master, slave, input logic clk2, output logic ready);
    logic clk, resetn;
    assign clk = master.clk; assign resetn = master.resetn;
    localparam type MQ = master.Q;
    localparam type SQ = slave.Q;
    localparam MBITS = $bits(MQ);
    localparam SBITS = $bits(SQ);
    localparam _DIV = 1<<($clog2(MBITS/SBITS));
    localparam DIV = MBITS > SBITS? _DIV : 1;
    localparam MDEPTH = master.DEPTH;
    localparam SDEPTH = slave.DEPTH;
    typedef logic [$clog2(MDEPTH)-1:0] MAddress;
    typedef logic [$clog2(SDEPTH)-1:0] SAddress;
    fifobus #(.D(SAddress), .Q(SAddress),
              .DEPTH(BUFDEPTH)) wraddress_fifo (.clk, .resetn);
    fifobus #(.D(MQ), .Q(SQ), .DEPTH(BUFDEPTH)) dfifo (.clk, .resetn);
    `FIFO(dfifo);
    `FIFO(wraddress_fifo);
    logic [$clog2(DIV)-1:0]            wrparity, wrparity_;
    `COUNTER(wrparity, dfifo.rdreq, dfifo.rdreq & (wrparity == DIV-1));
    `REG(wrparity_, wrparity);
    MQ _d;
    Tiler::DIGIT c__io_wrreqs, c__io_rdreqs;
    Tiler::DIGIT c_io_wrreqs, c_io_rdreqs;
    `SIMCOUNTER(c__io_wrreqs, slave.wrreq);
    `SIMCOUNTER(c_io_wrreqs, master.wrreq);
    `SIMCOUNTER(c__io_rdreqs, slave.rdreq);
    `SIMCOUNTER(c_io_rdreqs, master.rdreq);
    assign wraddress_fifo.d.value = master.wraddress;
    assign wraddress_fifo.wrreq = master.wrreq;
    assign wraddress_fifo.rdreq = dfifo.rdreq & !wrparity;
    assign dfifo.d.value = _d;
    assign dfifo.wrreq = master.wrreq;
    assign dfifo.rdreq = !dfifo.empty;
    assign slave.d.value = dfifo.q.value;
    `WORDSWAP_(_d, _d, master.d.value, 0, clk, SBITS);
    assign slave.wrreq = dfifo.q.info.valid;
    assign slave.wraddress = {wraddress_fifo.q.value<<$clog2(DIV)} + wrparity_;
    assign slave.rdreq = master.rdreq;
    assign slave.d.info_master.value = master.d.info;
    assign slave.rdaddress = master.rdaddress << $clog2(DIV);
    assign ready = dfifo.empty;
    fifobus #(.D(SQ), .Q(MQ), .DEPTH(BUFDEPTH)) qfifo(.clk(clk2), .resetn);
    localparam                         INFOBITS = $bits(Info);
    localparam                         _Info_BITS = 1<<$clog2(INFOBITS);
    typedef logic [_Info_BITS-1:0]     _Info;
    fifobus #(.D(_Info), .Q(logic [_Info_BITS*DIV-1:0]),
              .DEPTH(BUFDEPTH)) info_fifo (.clk(clk2), .resetn);
    `FIFO(qfifo);
    `FIFO(info_fifo);
    assign qfifo.wrreq = slave.q.info.valid;
    assign qfifo.d.value = slave.q.value;
    assign qfifo.rdreq = !qfifo.empty;
    assign info_fifo.wrreq = slave.q.info.valid;
    assign info_fifo.d.value = slave.q.info;
    assign info_fifo.rdreq = qfifo.rdreq;
    Info info;
    always_comb begin
        `INIT_INFO(info);
        info.valid = info_fifo.q.info.valid;
        if (info.valid) begin
            info = info_fifo.q.value
                   [_Info_BITS*(DIV-1)+INFOBITS-1 : _Info_BITS*(DIV-1)];
        end
    end
    assign master.q.value = qfifo.q.value;
    assign master.q.info_master.value = info;
    assign master.ready = !dfifo.half_full
                          & !wraddress_fifo.half_full & slave.ready;
endmodule
