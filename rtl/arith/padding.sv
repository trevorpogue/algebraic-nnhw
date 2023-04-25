`include "../top/define.svh"


module padding import globals::*;
    // io shapes: Ajvec q, Ajvec d
    #(BUF_DEPTH=TILE_BUF_DEPTH, RESULTS_SEL=RxTx::C_RESULTS_SEL,
      SAME_CLK=FALSE, `IMPORT_ARITH)
    (data q, d,
     fifo_array_bus results,
     output logic ready,
     input logic [$clog2(MAX_PADDING)-1:0] padding,
     input logic new_layer_edge,
     logic [$clog2(MAX_W)-1:0] size_w,
     logic [$clog2(MAX_H)-1:0] size_h,
     input logic wrote_layerio_layer,
     logic layer_params_valid,
     LayerParam tile_size_m,
     logic slowclk,
     logic topclk, resetn);
    localparam USE_TILEBUF = FALSE;
    logic      clk; assign clk = slowclk;
    logic      en;
    logic      new_layer_edge_;
    localparam DELAY5 = 1;
    `REG(en, |padding, DELAY5, topclk);
    `REG(new_layer_edge_, new_layer_edge, DELAY5, topclk);
    data #(logic [$bits(q.VALUE)-1:0]) _q(.clk(topclk), .resetn);
    logic      tile_rd_ready, start_tile_rd;
    logic [3:0] _ready;
    localparam  DELALY0 = 1;
    if (!USE_TILEBUF) begin
        `REG_DATA_COND(q, en, _q, d, DELALY0);
        assign _ready[3] = 1'b1;
    end else begin
        `REG_DATA_COND_(qfifo.d, qfifo_d, en, _q, d, DELALY0);
        `REG3(qfifo.wrreq, qfifo_wrreq, qfifo.d.info.valid, 0, topclk);
        assign qfifo.rdready = 1;
        assign qfifo.rdready2 = 1;
        fifobus #(.Q(Ajvec), .DEPTH(BUF_DEPTH)) qfifo
            (.clk(topclk), .resetn);
        `INFOFIFO(qfifo, "IPFIFO");
        `REG(start_tile_rd, tile_rd_ready);
        logic half_full;
        assign _ready[3] = !half_full & !qfifo.half_full;
        tilebuf #(Layeriovec) tile_buf_u
            (.layerfifo(qfifo),
             .wrote_layer(wrote_layerio_layer),
             .total_layer_reads(tile_size_m),
             .tile_size(tile_size_m),
             .half_full,
             .start_tile_rd,
             .tile_rd_ready,
             .tile_size_valid(layer_params_valid),
             .q, .clk(topclk), .resetn
             );
    end

    if (SIM | USE_RESULT_FIFOS_FULL) begin : sim
        data #(Ajvec) q_(.clk(topclk), .resetn);
        `WORDSWAP2(q_, q);
        `ASSIGN_RESULT(RESULTS_SEL, q_, topclk);
    end
    fifobus #(.Q(logic [$bits(Ajvec)+$bits(Info)-1:0])
              ,.DEPTH(BUF_DEPTH)
              ,.RDREQ_AS_ACK(TRUE)
              ) d_fifo(.clk, .resetn);
    logic  _write_zero;
    logic  write_zero;
    fmaxfifo #(.ASSIGN_INFO(FALSE)) fmaxfifo_u(.io(d_fifo));

    typedef struct packed {
        logic [$clog2(MAX_PADDING)-1:0] padding;
        logic [$clog2(MAX_W)-1:0]       size_w;
        logic [$clog2(MAX_H)-1:0]       size_h;
        logic                           new_layer_edge;
        logic                           valid;
    }FromTop;
    typedef struct                      packed {
        logic [SZI-1:0][A_WIDTH-1:0] d;
        Info dinfo;
        logic                             valid;
    }FromTop2;
    typedef struct                        packed {
        logic [SZI-1:0][A_WIDTH-1:0] q;
        Info qinfo;
        logic                             ready;
        logic                             valid;
    }ToTop;
    typedef struct                        packed {
        logic                             _ready;
        logic                             valid;
    }ToTop2;
    assign ready = &_ready;
    FromTop fromtop_topclk, inputs, _inputs;
    FromTop2 fromtop_topclk2, inputs2;
    ToTop totop_topclk, outputs, outputs_;
    ToTop2 totop2_topclk;
    localparam                            DELAY4 = 2;
    `REG(outputs_, outputs, DELAY4);
    `REG(inputs, _inputs, DELAY4);
    logic                                 filler, filler2, filler3;
    assign outputs.valid = outputs.qinfo.valid | outputs.ready;
    assign fromtop_topclk = {padding, size_w, size_h, new_layer_edge_,
                             layer_params_valid & en};
    assign fromtop_topclk2 = {d.value, d.info, d.info.valid & en};
    assign {_q.value, _q.info_master.value, filler3, filler} = totop_topclk;
    assign {_ready[0], filler2} = totop2_topclk;
    clock_crossing_data #(.A2B(FromTop),
                          .RDREQ_AS_ACK(TRUE),
                          .SAME_CLK(SAME_CLK)) clock_crossing_data_u
        (.clka_a2b(fromtop_topclk), .clkb_a2b(_inputs),
         .clka_b2a(totop2_topclk), .clkb_b2a(outputs_),
         .clka_wrready(_ready[1]),
         .clka(topclk), .clkb(slowclk), .resetn);
    clock_crossing_data #(.A2B(FromTop2), .B2A(ToTop),
                          .VALID_MEANS_NEW_DATA(TRUE),
                          .DEPTH_A2B(BUF_DEPTH),
                          .SAME_CLK(SAME_CLK)) clock_crossing_data_u2
        (.clka_a2b(fromtop_topclk2), .clkb_a2b(inputs2),
         .clka_b2a(totop_topclk), .clkb_b2a(outputs_),
         .clka_wrready(_ready[2]),
         .clka(topclk), .clkb(slowclk), .resetn);

    localparam                            DELAY0 = 1;
    localparam                            DELAY1 = 0;
    `REG_(d_fifo.d.value, {inputs2.dinfo, inputs2.d}, DELAY0, d_fifo_d);
    `REG_(d_fifo.wrreq, inputs2.dinfo.valid, DELAY0, d_fifo_wrreq);
    `REG(write_zero, _write_zero, DELAY0);
    `REG_(d_fifo.rdreq, !_write_zero & !d_fifo.empty, DELAY1, d_fifo_rdreq);
    Info _info;
    assign _info = d_fifo.q.value[$bits(Bjvec)+$bits(Info)-1:$bits(Bjvec)] ;
    always_comb begin
        `INIT_INFO(d_fifo.q.info_master.value);
        if (d_fifo.q.info_master.value.valid) begin
            `SET_INFO(d_fifo.q.info_master.value, _info);
        end
    end
    `SHIFT_REG__(d_fifo.q.info_master.value.valid, d_fifo.rdreq, 1,
                 d_fifo_valid);

    logic do_padding;
    logic _do_padding;
    logic [$clog2(MAX_H)-1:0] row, _row, row_;
    logic [$clog2(MAX_W)-1:0] col, _col, col_;
    logic [$clog2(MAX_PADDING)-1:0] _padding;
    logic [$clog2(MAX_PADDING)+1:0] _padding_m1;
    logic [$clog2(MAX_PADDING)+1:0] _padding_ls1_m1;
    logic [$clog2(MAX_PADDING)+1:0] padding_m1;
    logic                           row_gte_size_h_plus_padding;
    logic                           row_lt_padding;
    logic                           col_lt_padding;
    logic                           col_gte_size_w_plus_padding;
    logic [$clog2(MAX_PADDING)+1:0] size_h_plus_padding;
    logic [$clog2(MAX_PADDING)+1:0] size_w_plus_padding;
    logic [$clog2(MAX_PADDING)+1:0] size_w_plus_2padding;
    logic [$clog2(MAX_PADDING)+1:0] size_w_plus_padding_minus1;
    logic [$clog2(MAX_PADDING)+1:0] size_h_plus_padding_minus1;
    logic [$clog2(MAX_PADDING)+1:0] size_h_plus_2padding_minus1;
    logic [$clog2(MAX_PADDING)+1:0] size_w_plus_2padding_minus1;
    logic                           last_elm, last_elm_ack;
    logic                           last_tile_n_elm, last_tile_n_elm_ack;
    logic                           last_w;
    logic                           layer_params_valid_;
    `REG(layer_params_valid_, inputs.valid);
    `REG2_(_padding_m1, _padding-1, _padding_m1, 1, 1);
    `REG2_(_padding_ls1_m1, {_padding<<1} - 1, _padding_ls1_m1, 1, 1);
    `REG2_(padding_m1, inputs.padding-1, padding_m1, 1, 1);
    `REG(col_, col);
    `REG(row_, row);
    `ACK(last_elm, d_fifo.q.info.last_elm, last_elm_ack | !do_padding, 0);
    `ACK(last_tile_n_elm, d_fifo.q.info.last_tile_n_elm,
         last_tile_n_elm_ack | !do_padding, 0);

    assign outputs.ready = d_fifo.empty | !do_padding;

    `POSEDGE__(do_padding_on_edge,
               (inputs.new_layer_edge && (inputs.padding > 0)), 1);
    `ONOFF(_do_padding, do_padding_on_edge,
           outputs.qinfo.last_elm, 1);
    assign do_padding = _do_padding & !outputs.qinfo.last_elm;
    assign _padding = do_padding? inputs.padding : '0;

    logic                           increment_col;
    logic                           increment_row;
    assign increment_col = _write_zero | (!d_fifo.empty);
    always_comb begin
        _row = row;
        _col = col;
        outputs.qinfo = '0;
        outputs.q = '0;
        _write_zero = '0;
        increment_row = '0;
        _write_zero |= row_gte_size_h_plus_padding;
        _write_zero |= row_lt_padding;
        _write_zero |= col_lt_padding;
        _write_zero |= col_gte_size_w_plus_padding;
        `SET_INFO(outputs.qinfo, d_fifo.q.info);
        outputs.qinfo.last_elm = '0;
        outputs.qinfo.last_tile_n_elm = '0;
        outputs.qinfo.last_w = last_w;
        outputs.qinfo.new_tile_k = '0;
        last_tile_n_elm_ack = '0;
        last_elm_ack = '0;
        if (!do_padding)
            _write_zero = FALSE;
        if (increment_col) begin
            _col += 1;
        end
        if (d_fifo.q.info.valid) begin
            outputs.q = d_fifo.q.value;
            outputs.qinfo.valid = 1'b1;
        end else if (write_zero) begin
            outputs.qinfo.valid = 1'b1;
        end
        if (outputs.qinfo.valid)
            outputs.qinfo.new_tile_k = (col_ == 0) & (row_ == 0);
        if (col_ == (size_w_plus_2padding_minus1)) begin
            if  (row_ == (size_h_plus_2padding_minus1)) begin
                outputs.qinfo.last_tile_n_elm = last_tile_n_elm;
                last_tile_n_elm_ack = '1;
                outputs.qinfo.last_elm = last_elm;
                last_elm_ack = '1;
            end
        end
        if (col == (size_w_plus_2padding_minus1)) begin
            if  (row == (size_h_plus_2padding_minus1)) begin
                _row = '0;
            end else begin
                _row += 1;
                increment_row = '1;
            end
        end
        if (col == (size_w_plus_2padding_minus1))
            _col = '0;
    end

    counter_flags counter_flags_u (.en(outputs.qinfo.valid),
                                   .reset(!do_padding),
                                   .size_w(size_w_plus_2padding),
                                   .layer_params_valid(layer_params_valid_),
                                   .last_w(last_w), .clk, .resetn);

    localparam DELAY2 = 0;
    localparam DELAY3 = 1;
    `REG(row_gte_size_h_plus_padding,
         (increment_row & (row >= size_h_plus_padding_minus1))
         | (!increment_row & (row >= size_h_plus_padding)),
         DELAY3);
    `REG(row_lt_padding,
         (increment_row & (row < padding_m1))
         | (!increment_row & (row < _padding)),
         DELAY3);
    `REG(col_lt_padding,
         (increment_col & (col < padding_m1))
         | (!increment_col & (col < _padding)),
         DELAY3);
    `REG(col_gte_size_w_plus_padding,
         (increment_col & (col >= size_w_plus_padding_minus1))
         | (!increment_col & (col >= size_w_plus_padding))
         , DELAY3);
    always_ff @(posedge clk or negedge resetn) if (~resetn) begin
        row <= '0;
        col <= '0;
    end else if (!do_padding) begin
        row <= '0;
        col <= '0;
    end else begin
        row <= _row;
        col <= _col;
        size_h_plus_padding <= inputs.size_h + _padding;
        size_w_plus_padding <= inputs.size_w + _padding;
        size_w_plus_2padding <= inputs.size_w + {_padding<<1};
        size_h_plus_2padding_minus1 <= inputs.size_h + _padding_ls1_m1;
        size_w_plus_2padding_minus1 <= inputs.size_w + _padding_ls1_m1;
        size_w_plus_padding_minus1 <= inputs.size_w + _padding_m1;
        size_h_plus_padding_minus1 <= inputs.size_h + _padding_m1;
    end
endmodule


module counter_flags import globals::*;
    (output logic              last_w,
     input logic [$clog2(MAX_W)-1:0] size_w,
     input logic                     reset,
     input logic                     layer_params_valid,
     input logic                     en, clk, resetn);
    logic [$clog2(MAX_W)-1:0]        w;
    logic [$clog2(MAX_W)-1:0]        size_w_m1;
    logic                            size_w_m1_logic;
    `REG(size_w_m1, size_w-1)
    `REG(size_w_m1_logic, |size_w_m1);
    `always_ff2 if (~resetn) begin
        w <= '0;
    end else if (reset) begin
        w <= '0;
    end else if (en && size_w_m1_logic) begin
        w <= w + 1;
        if (last_w)
            w <= '0;
    end
    assign last_w = layer_params_valid? size_w_m1_logic
                    && (w == size_w_m1) && en : '0;
endmodule
