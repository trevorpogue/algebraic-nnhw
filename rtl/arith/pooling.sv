`include "../top/define.svh"


module pooling import globals::*;
    // io shapes: Ajvec q, Aivec d
    #(BUF_DEPTH=TILE_BUF_DEPTH, RESULTS_SEL=RxTx::POOLING_RESULTS_SEL,
      SAME_CLK=FALSE, `IMPORT_ARITH)
    (data q, d,
     fifo_array_bus results,
     input logic [$clog2(MAX_POOL_SIZE)-1:0] size,
     logic [$clog2(MAX_W)-1:0] size_w,
     logic [$clog2(MAX_H)-1:0] size_h,
     input logic [$clog2(MAX_POOL_SIZE)-1:0] stride,
     input logic [$clog2(MAX_AVGPOOL_DENOM)-1:0] avg_pool_denom,
     input logic [1:0] type_,
     input logic start,
     input logic topclk, slowclk, resetn,
     output logic ready
     );
    logic [$clog2(MAX_POOL_SIZE)-1:0] _size;
    logic [$clog2(MAX_POOL_SIZE)-1:0] _stride;
    logic [$clog2(MAX_AVGPOOL_DENOM)-1:0] _avg_pool_denom;
    logic                                 clk, en;
    logic                                 type_eq_avgpool2d;
    logic                                 type_eq_maxpool2d;
    data #(logic [$bits(q.VALUE)-1:0]) _q(.clk(topclk), .resetn);
    localparam                            DELALY0 = 1;
    `REG(en, size > 1, 1, topclk);
    `REG_DATA_COND(q, en, _q, d, DELALY0);

    if (SIM | USE_RESULT_FIFOS_FULL) begin : sim
        data #(Ajvec) q_(.clk(topclk), .resetn);
        `WORDSWAP2(q_, q);
        `ASSIGN_RESULT(RESULTS_SEL, q_, topclk);
    end
    assign clk = slowclk;
    localparam    TOTAL_FIFOS = MAX_POOL_SIZE;
    localparam    TOTAL_FIFOS_POW2 = 1<<$clog2(TOTAL_FIFOS);
    localparam    RDLATENCY = 1;
    fifobus #(.Q(Ajvec), .DEPTH(2<<$clog2(MAX_W))
              ,.WRLATENCY(3)
              ,.RDLATENCY(RDLATENCY)) fifos[TOTAL_FIFOS](.*);
    `FOR(genvar, FIFO, TOTAL_FIFOS) begin : gfifos
        look_ahead_fifo look_ahead_fifo(.io(fifos[FIFO]));
    end

    logic [$clog2(MAX_W)-1:0]               size_w_m1;
    logic [$clog2(MAX_POOL_SIZE)-1:0]       size_m1;
    logic [$clog2(MAX_H)-1:0]               size_h_m1;
    logic [$clog2(MAX_H):0]                 size_h_m1_mstride;

    typedef struct                          packed {
        logic [$clog2(MAX_W)-1:0]           size_w;
        logic [$clog2(MAX_H)-1:0]           size_h;
    `ifdef VARPOOLING
        logic [$clog2(MAX_POOL_SIZE)-1:0]   size;
        logic [$clog2(MAX_POOL_STRIDE)-1:0] stride;
        logic [$clog2(MAX_AVGPOOL_DENOM)-1:0] avg_pool_denom;
    `endif
        logic [1:0]                           type_;
        logic                                 start;
        logic                                 valid;
    }FromTop;
    typedef struct                            packed {
        logic [SZI-1:0][A_WIDTH-1:0]          d;
        Info dinfo;
        logic                                 valid;
    }FromTop2;
    typedef struct                            packed {
        logic [SZI-1:0][A_WIDTH-1:0]          q;
        Info qinfo;
        logic                                 valid;
    }ToTop;
    logic                                     ready1, ready2;
    assign ready = (size <= 1) | ready1 & ready2;
    FromTop fromtop_topclk, inputs, _inputs;
    FromTop2 fromtop_topclk2, inputs2;
    ToTop totop_topclk, outputs, outputs_, outputs_d;
    `REG(type_eq_avgpool2d, inputs.type_ == AVGPOOL2D);
    `REG(type_eq_maxpool2d, inputs.type_ == MAXPOOL2D);
    localparam                                DELAY0 = 2;
    `REG(outputs_, outputs, DELAY0);
    logic                                     filler;
    `ONOFF__(start_top, start, en, 1, topclk);
    always_comb begin
        _size = 3;
        _stride = 2;
        _avg_pool_denom = avg_pool_denom == 9? 9 : 49;
    `ifdef VARPOOLING
        _size = inputs.size;
        _stride = inputs.stride;
        _avg_pool_denom = inputs.avg_pool_denom;
    `endif
    end
    assign outputs_d.valid = outputs_d.qinfo.valid;
    assign fromtop_topclk = {size_w, size_h,
    `ifdef VARPOOLING
                             size,
                             stride,
                             avg_pool_denom,
    `endif
                             type_, start_top, en};
    assign fromtop_topclk2 = {d.value, d.info, d.info.valid & en};
    assign {_q.value, _q.info_master.value, filler} = totop_topclk;
    `POSEDGE__(start_posedge, inputs.start, 1);
    clock_crossing_data #(.A2B(FromTop),
                          .RDREQ_AS_ACK(TRUE),
                          .DEPTH_A2B(BUF_DEPTH),
                          .SAME_CLK(SAME_CLK)
                          ) clock_crossing_data_u
        (.clka_a2b(fromtop_topclk), .clkb_a2b(_inputs),
         .clka_wrready(ready1),
         .clka(topclk), .clkb(slowclk), .resetn);
    clock_crossing_data #(.A2B(FromTop2), .B2A(ToTop),
                          .VALID_MEANS_NEW_DATA(TRUE), .RDREQ_AS_ACK(FALSE),
                          .DEPTH_A2B(BUF_DEPTH),
                          .SAME_CLK(SAME_CLK)) clock_crossing_data_u2
        (.clka_a2b(fromtop_topclk2), .clkb_a2b(inputs2),
         .clka_b2a(totop_topclk), .clkb_b2a(outputs_),
         .clka_wrready(ready2),
         .clka(topclk), .clkb(slowclk), .resetn);

    Info info, info_d, ored_fifo_info;
    logic [TOTAL_FIFOS-1:0][$bits(Info)-1:0]            infos;
    logic                                               rdreq, fifos_qvalid;
    logic [TOTAL_FIFOS-1:0][SZI-1:0][A_WIDTH-1:0]       values;
    logic [TOTAL_FIFOS-1:0]                             empties, _empties;
    logic [TOTAL_FIFOS-1:0]                             wrreqs;
    logic [TOTAL_FIFOS-1:0]                             qvalids;
    logic signed [$clog2(MAX_W):0]                      ack_row_inc;
    logic [$clog2(MAX_W):0]                             total_acks_per_row;
    logic                                               total_acks_per_row_eq_size_w_m1;
    logic [$clog2(MAX_W):0]                             total_acks_per_row_d;
    logic [$clog2(MAX_W):0]                             total_acks_per_row_p1;
    logic [$clog2(MAX_H):0]                             row;
    logic [$clog2(MAX_H):0]                             row_d;
    logic                                               row_lt_size_h_m1_mstride;
    logic signed [TOTAL_FIFOS-1:0][$clog2(MAX_W):0]     rdacks;
    //
    logic [$clog2(TOTAL_FIFOS)-1:0]                     wr_fifo_sel;
    logic                                               at_last_wr_fifo_sel;
    logic [$clog2(TOTAL_FIFOS)-1:0]                     rd_fifo_state;
    logic                                               rd_fifo_state_lt_size_m1;
    logic [$clog2(TOTAL_FIFOS)-1:0]                     rd_fifo_state_p1;
    logic [$clog2(TOTAL_FIFOS)-1:0]                     rd_fifo_state_d;
    logic [$clog2(TOTAL_FIFOS)-1:0]                     rd_fifo_state_;
    logic                                               rd_fifo_state_eq_size_m1;
    logic [$clog2(TOTAL_FIFOS)-1:0]                     wr_fifo_sel_d;
    //
    logic [TOTAL_FIFOS_POW2-1:0][$clog2(TOTAL_FIFOS):0] overlap_fifos_sel;
    logic [TOTAL_FIFOS_POW2-1:0][$clog2(TOTAL_FIFOS):0] overlap_fifos_sel_d;
    logic [$clog2(MAX_POOL_SIZE)-1:0]                   overlap;
    //
    logic [SZI-1:0][A_WIDTH+$clog2(MAX_POOL_SIZE*MAX_POOL_SIZE)-1:0]
                   poolval;
    logic [SZI-1:0][A_WIDTH+$clog2(MAX_POOL_SIZE*MAX_POOL_SIZE)-1:0]
                   poolval_;
    logic [SZI-1:0][A_WIDTH+$clog2(MAX_POOL_SIZE*MAX_POOL_SIZE)-1:0]
                   poolval__;
    Ajvec poolval_div;
    logic [SZI-1:0][A_WIDTH+$clog2(MAX_POOL_SIZE*MAX_POOL_SIZE)-1:0]
                   poolval_d;
    //
    localparam                                                       DELAY1 = 4;
    localparam                                                       DELAY2 = 8;
    `REG(inputs, _inputs, DELAY1);
    `REG(poolval_, poolval, DELAY1);
    `REG(poolval__, poolval_, DELAY2);
    `FOR(genvar, I, SZI) begin
        `REG2_(poolval_div[I], poolval_[I] / _avg_pool_denom,
               poolval_div_I, DELAY2);
    end
    `REG2_(outputs.q, outputs_d.q, outputs_q, 0);
    `REG2_(outputs.qinfo, outputs_d.qinfo, outputs_qinfo, DELAY1+DELAY2);
    `REG2_(outputs.valid, outputs_d.valid, outputs_valid, DELAY1+DELAY2);

    always_comb begin
        if (fifos_qvalid & rd_fifo_state_ == 0)
            poolval_d = '0;
        else
            poolval_d = poolval;
        `FOR(integer, I, SZI) begin
            `FOR(integer, FIFO, TOTAL_FIFOS) begin
                if (type_eq_maxpool2d) begin
                    if (qvalids[FIFO] & (values[FIFO][I] > poolval_d[I]))
                        poolval_d[I] = values[FIFO][I];
                end else begin
                    if (qvalids[FIFO])
                        poolval_d[I] += values[FIFO][I];
                end
            end  // I
        end
    end

    `FOR(genvar, FIFO, TOTAL_FIFOS) begin
        assign fifos[FIFO].wrreq = wrreqs[FIFO];
        assign fifos[FIFO].d.value = inputs2.d;
        assign fifos[FIFO].d.info_master.value = inputs2.dinfo;
        assign fifos[FIFO].rdreq = rdreq;
        assign fifos[FIFO].rdack = signed'(rdacks[FIFO]);
        assign empties[FIFO] = fifos[FIFO].empty;
        assign qvalids[FIFO] = fifos[FIFO].q.info.valid;
        assign infos[FIFO] = fifos[FIFO].q.info;
        assign values[FIFO] = fifos[FIFO].q.value;
    end
    always_comb begin
        wrreqs = '0;
        wrreqs[wr_fifo_sel] = inputs2.dinfo.valid;
        rdacks = '0;
        if (rdreq) begin
            `FOR(int, I, TOTAL_FIFOS) begin
                if (rd_fifo_state_lt_size_m1
                    | (total_acks_per_row_eq_size_w_m1))
                    rdacks[I] = 1;
                else
                    rdacks[I] = ack_row_inc;
            end
        end
        for (int i=0; i<overlap; i++) begin
            if (rdreq & (total_acks_per_row_eq_size_w_m1)
                & (row_lt_size_h_m1_mstride))
                rdacks[overlap_fifos_sel[i]] -= total_acks_per_row_p1;
        end
    end
    always_comb begin
        if (fifos_qvalid & (rd_fifo_state_ == 0))
            info_d = '0;
        else
            info_d = info;
        ored_fifo_info = '0;
        if (fifos_qvalid) begin
            `FOR(int, FIFO, TOTAL_FIFOS) begin
                if (qvalids[FIFO])
                    info_d |= infos[FIFO];
                if (qvalids[FIFO])
                    ored_fifo_info |= infos[FIFO];
            end
        end
        `FOR(integer, I, SZI) begin
            outputs_d.q[I] = poolval__[I];
        end
        if (type_eq_avgpool2d)
            `FOR(integer, I, SZI) begin
                outputs_d.q[I] = poolval_div[I];
            end
        `INIT_INFO(outputs_d.qinfo);
        if (outputs_d.qinfo.valid) begin
            `SET_INFO(outputs_d.qinfo, info);
        end
        wr_fifo_sel_d = wr_fifo_sel;
        rd_fifo_state_d = rd_fifo_state;
        at_last_wr_fifo_sel = '0;
        if (rdreq) rd_fifo_state_d = rd_fifo_state_p1;
        if (rd_fifo_state_d == _size) rd_fifo_state_d = '0;
        if (outputs_d.qinfo.last_tile_n_elm) rd_fifo_state_d = '0;
        overlap_fifos_sel_d = overlap_fifos_sel;
        if (start_posedge | ored_fifo_info.last_tile_n_elm) begin
            for (int i=0; i<overlap; i++)
                overlap_fifos_sel_d[i] = _stride + i;
        end else if (ored_fifo_info.last_w) begin
            for (int i=0; i<overlap; i++) begin
                overlap_fifos_sel_d[i] += _stride;
                if (overlap_fifos_sel_d[i] >= _size)
                    overlap_fifos_sel_d[i] -= _size;
            end
        end
        if (inputs2.dinfo.valid) begin
            if (inputs2.dinfo.last_w) wr_fifo_sel_d += 1;
            at_last_wr_fifo_sel = wr_fifo_sel_d == _size;
            if (at_last_wr_fifo_sel) wr_fifo_sel_d = '0;
        end
    end

    assign last_elm = inputs2.dinfo.last_elm;
    always_comb begin
        _empties = '0;
        `FOR(int, I, MAX_POOL_SIZE) begin
            if (I < _size)
                _empties[I] = empties[I];
        end
        if (_size < 2)
            _empties = '1;
    end
    `REG(rdreq, !_empties, 0);
    always_comb begin
    end
    `REG(size_h_m1, inputs.size_h-1);
    `REG(size_w_m1, inputs.size_w-1);
        `ifdef VARPOOLING
    `REG(size_m1, _size-1);
    `REG(overlap, _size - _stride);
    `REG(ack_row_inc, -(_size - _stride) + signed'(1));
        `else
    assign size_m1 = _size-1;
    assign overlap = _size - _stride;
    assign ack_row_inc = -(_size - _stride) + signed'(1);
        `endif
    `REG(size_h_m1_mstride, size_h_m1-_stride);
    always_comb begin
        total_acks_per_row_d = total_acks_per_row;
        if (rdreq) begin
            if (rd_fifo_state_lt_size_m1) begin
                total_acks_per_row_d = total_acks_per_row + 1;
            end else begin
                total_acks_per_row_d = signed'(total_acks_per_row)
                    + signed'(ack_row_inc);
            end
            if (rdreq & (total_acks_per_row_eq_size_w_m1)) begin
                total_acks_per_row_d = '0;
            end
        end
        if (outputs_d.qinfo.last_elm) begin
            total_acks_per_row_d <= '0;
        end
    end
    always_comb begin
        row_d = row;
        if (ored_fifo_info.valid) begin
            if (ored_fifo_info.last_w) begin
                row_d = row + _stride;
                if (row == size_h_m1_mstride)
                    row_d = '0;
            end
        end
    end
    `REG(total_acks_per_row, total_acks_per_row_d);
    `REG(total_acks_per_row_eq_size_w_m1, total_acks_per_row_d == size_w_m1);
    `REG(total_acks_per_row_p1, total_acks_per_row_d+1);
    `REG(rd_fifo_state, rd_fifo_state_d);
    `REG(rd_fifo_state_p1, rd_fifo_state_d+1);
    `REG(rd_fifo_state_lt_size_m1, rd_fifo_state_d < size_m1);
    `REG(row_lt_size_h_m1_mstride, row_d < size_h_m1_mstride);
    `REG(row, row_d);
    `REG(rd_fifo_state_eq_size_m1, rd_fifo_state == size_m1);
    `REG(rd_fifo_state_, rd_fifo_state);
    `REG(fifos_qvalid, rdreq, RDLATENCY);
    always_ff @(posedge clk or negedge resetn) if (~resetn) begin
        wr_fifo_sel <= '0;
        outputs_d.qinfo.valid <= 1'b0;
        info <= 1'b0;
        overlap_fifos_sel <= '0;
        poolval <= '0;
    end else begin
        overlap_fifos_sel <= overlap_fifos_sel_d;
        wr_fifo_sel <= wr_fifo_sel_d;
        poolval <= poolval_d;
        info <= info_d;
        if (fifos_qvalid && (rd_fifo_state_eq_size_m1))
            outputs_d.qinfo.valid <= 1'b1;
        else
            outputs_d.qinfo.valid <= 1'b0;
        if (inputs2.dinfo.last_tile_n_elm) begin
            wr_fifo_sel <= '0;
        end
        if (outputs_d.qinfo.last_tile_n_elm) begin
            poolval <= '0;
            outputs_d.qinfo.valid <= 1'b0;
            info <= 1'b0;
        end
    end
endmodule
