`include "../top/define.svh"


module wrote_layer_unit import globals::*, Tiler::DIGIT;
    // Keep track of how many writes took place and flag when a full
    // layer has been written
    #(
      // when TOTAL_WRREQS == 1 there will be fmax optimizations
      TOTAL_WRREQS=LAYERIOMEM_CLK_DIV,
      USE_ISLASTLAYER=FALSE)
    (
     input logic                    clk, resetn,
     input logic [TOTAL_WRREQS-1:0] wrreqs,
     input logic                    islastlayer,
     input                          DIGIT size,
     output logic                   wrote_layer,
     output logic                   writing_layer_next
     );
    DIGIT count, count_eq_size_m1;
    logic [$clog2(TOTAL_WRREQS):0]  wrreq_hotcount;
    DIGIT size_m1, size_m2;
    logic                           size_valid;
    logic                           size_is_1;
    logic                           _wrote_layer;
    assign wrote_layer = _wrote_layer & size_valid;
    `REG2__(wrreqs_, wrreqs);
    `REG(size_m1, size-1);
    `REG(size_m2, size-2);
    `REG__(writing_layerio_layer_next_, writing_layer_next);
    `ONOFF(count_eq_size_m1, (count == size_m2) && size_valid
           && wrreqs,
           writing_layerio_layer_next_);
    `REG(size_valid, |size);
    `REG(size_is_1, size == 1);
    if (TOTAL_WRREQS > 1) begin
        `always_comb begin
            wrreq_hotcount = 0;
            `FOR(int, I, TOTAL_WRREQS) begin
                wrreq_hotcount += wrreqs[I];
            end
        end
        assign writing_layer_next
            = ({count + wrreq_hotcount} >= size) && size;
    end else begin
        assign wrreq_hotcount = wrreqs;
        assign writing_layer_next
            = ((count_eq_size_m1 | size_is_1) && wrreqs) && size_valid;
    end
    `always_ff2 if (~resetn) begin
        count <= '0;
        _wrote_layer <= FALSE;
    end else begin
        _wrote_layer <= FALSE;
        count <= count + wrreq_hotcount;
        if (writing_layer_next) begin
            if (TOTAL_WRREQS > 1) begin
                count <= count + wrreq_hotcount - size;
            end else begin
                count <= '0;
            end
            if (USE_ISLASTLAYER)
                _wrote_layer <= !islastlayer;
            else
                _wrote_layer <= '1;
        end
    end
endmodule


module rdreqfifo_wrreq_unit import globals::*;
    // Modul purpose: The wrreq signal going into layeriomem is split across
    // several receiving fifos.  This means that each receiving fifo must
    // receive wrreqs at a lower frequency than the top layeriomem.
    // This module lowers that wrreq frequency.
    #(type W = logic [$clog2(MAX_W)-1:0])
    (
     input logic [$clog2(MAX_W)-1:0] size_w,
     input logic                     wrote_layerio_layer,
     logic                           en, clk, resetn,
     output logic                    q
     );
    W w, w_, size_w_div, size_w_m1;
    logic                            under_threshold;
    logic                            size_w_logic;
    always_comb begin
        if (size_w[$clog2(LAYERIOMEM_CLK_DIV)-1:0])
            size_w_div = {size_w>>$clog2(LAYERIOMEM_CLK_DIV)} + 1;
        else
            size_w_div = size_w >> $clog2(LAYERIOMEM_CLK_DIV);
        w_ = wrote_layerio_layer? 0 : w;
    end
    assign under_threshold = (w_ < size_w_div) && size_w_logic;
    `always_ff2 if (~resetn) begin
        w <= '0;
        size_w_m1 <= '0;
        size_w_logic <= '0;
    end else begin
        size_w_m1 <= size_w-1;
        size_w_logic <= |size_w;
        if (en) begin
            w <= w + 1;
            if (under_threshold) begin
                q <= '1;
            end else
                q <= '0;
            if (w_ == size_w_m1) begin
                w <= '0;
            end
        end else begin
            q <= '0;
        end
        if (wrote_layerio_layer)
            w <= '0;
    end
endmodule


module dfifo_addressmem_d_unit
    import globals::*; import Tiler::DIGIT;
    #(DEPTH, CLKDIV, LATENCY=0, type W = logic [$clog2(MAX_W)-1:0],
      type AddressmemAddress = logic [$clog2(DEPTH)-1:0],
      integer DIV_DEPTH = $ceil(DEPTH/CLKDIV)
      )
    (
     input logic                                islastlayer,
     input                                      DIGIT wr_offset,
     input                                      DIGIT rd_offset,
     input logic                                en, clk, resetn,
     input                                      DIGIT size,
     input                                      W size_w,
     input                                      DIGIT stride_w,
     output logic [$clog2(CLKDIV)-1:0]          dfifosel,
     output logic                               wrote_layerio_layer,
     output
     logic [CLKDIV-1:0] [$clog2(DIV_DEPTH)-1:0] layeriomem_addresses,
     output                                     AddressmemAddress addressmem_addresses
     );
    DIGIT																																							offset;
    logic [CLKDIV-1:0] [$clog2(DIV_DEPTH)-1:0]  layeriomem_addresses_d;
    AddressmemAddress addressmem_addresses_d;
    logic [$clog2(CLKDIV)-1:0]                  _dfifosel;
    logic                                       _writing_layerio_layer_next;
    `REG(wrote_layerio_layer, _writing_layerio_layer_next, 1);
    `REG(dfifosel, _dfifosel, LATENCY);
    `REG(addressmem_addresses, addressmem_addresses_d, LATENCY);
    `REG(layeriomem_addresses, layeriomem_addresses_d, LATENCY);
    W w, w_mod;
    AddressmemAddress _addressmem_addresses;
    logic [CLKDIV-1:0] [$clog2(DIV_DEPTH)-1:0]  _layeriomem_addresses;
    wrote_layer_unit #(1) wrote_layer_u
        (.wrreqs(en), .islastlayer, .size,
         .writing_layer_next(_writing_layerio_layer_next),
         .clk, .resetn);
    always_comb begin
        addressmem_addresses_d = _addressmem_addresses;
        layeriomem_addresses_d = _layeriomem_addresses;
        if (offset) begin
            if (offset == 1) begin
                addressmem_addresses_d
                    = $signed(DEPTH) - $signed(_addressmem_addresses)
                        - $signed(1);
                `FOR(int, I, CLKDIV)
                layeriomem_addresses_d[I]
                    = $signed(DIV_DEPTH) - $signed(_layeriomem_addresses[I])
                        - $signed(1);
            end else begin
                addressmem_addresses_d
                    = $signed(DEPTH) - $signed(offset)
                        + $signed(_addressmem_addresses);
                `FOR(int, I, CLKDIV)
                layeriomem_addresses_d[I]
                    = $signed(DIV_DEPTH)
                        - $signed({offset>>$clog2(LAYERIOMEM_CLK_DIV)})
                            + $signed(_layeriomem_addresses[I]);
            end
        end
    end
    logic got_1st_offset;
    `ONOFF(got_1st_offset, |size_w, |offset & !got_1st_offset);
    assign offset = wr_offset;
    `always_ff2 if (~resetn) begin
        _addressmem_addresses <= '0;
        _layeriomem_addresses <= '0;
    end else begin
        if (!got_1st_offset) begin
        end else if (_writing_layerio_layer_next) begin
        end
        if (en) begin
            _addressmem_addresses <= _addressmem_addresses + 1;
            `FOR(int, I, CLKDIV) if (_dfifosel == I) begin
                _layeriomem_addresses[I]
                    <= _layeriomem_addresses[I] + 1;
            end
        end
        if (_writing_layerio_layer_next) begin
            _addressmem_addresses <= '0;
            _layeriomem_addresses <= '0;
        end
    end
    `REG2__(stride_w_m1, stride_w - 1);
    `REG2__(size_w_m1, size_w - 1);
    `always_ff2 if (~resetn) begin
        w <= '0;
        w_mod <= '0;
        _dfifosel <= '0;
    end else begin
        if (en) begin
            w <= w + 1;
            w_mod <= w_mod + 1;
            if (w_mod == stride_w_m1) begin
                w_mod <= '0;
                _dfifosel <= _dfifosel + 1;
            end
            if (w == size_w_m1) begin
                _dfifosel <= '0;
                w <= '0;
                w_mod <= '0;
            end
        end
        if (_writing_layerio_layer_next) begin
            _dfifosel <= '0;
            w <= '0;
            w_mod <= '0;
        end
    end
endmodule


module look_ahead_instruc_loader import globals::*;
    #(TOTAL_FIELDS,
      FIELD_WIDTH,
      LOAD_DELAY=1,
      type Instruc = logic [TOTAL_FIELDS-1:0][FIELD_WIDTH-1:0],
      type Field = logic [FIELD_WIDTH-1:0]
      )
    (fifobus dfifo, input logic load, output Instruc q, next_q,
     output logic qvalid,
     output logic next_qvalid,
     output logic empty,
     input logic clk, resetn);
    logic        _next_qvalid;
    logic        next_load, next_empty;
    Instruc _next_q;
    fifobus #(.Q(Instruc)) qfifo(.clk, .resetn);
    `IPFIFO(qfifo);
    instruc_fields_loader #(TOTAL_FIELDS, FIELD_WIDTH) instruc_loader_u
        (.instruc(dfifo),
         .load(next_load),
         .q(_next_q),
         .qvalid(_next_qvalid),
         .empty(next_empty),
         .clk, .resetn);
    assign next_load = !next_empty & qfifo.empty;
    assign qfifo.wrreq = _next_qvalid;
    assign qfifo.d.value = _next_q;
    localparam   DELAY0 = 0;
    `REG2_(qfifo.rdreq, load, qfifo_rdreq, DELAY0);
    assign empty = qfifo.empty;
    `REG(q, qfifo.q.value, LOAD_DELAY-1);
    `REG(next_q, _next_q, LOAD_DELAY-1);
    `ONOFF(qvalid, qfifo.q.info.valid, '0, LOAD_DELAY-1);
    `ONOFF(next_qvalid, _next_qvalid, '0, LOAD_DELAY-1);
endmodule


module stride_fix import globals::*; import Tiler::*;
    // Modul purpose: Each memory gets different data based on:
    // laymeriomem_sel[w] = w / kernel_stride.
    // Therefore, when tiler dim TILE_COUNT_KERNEL_W_DIM passes the
    // kernel_stride border, that channel must now read from a different
    // layeriomem. This module sets up a layeriomem_sel signal to detect
    // and resolve this condition
    #(DEPTH, _WIDTH=$clog2(DEPTH), type _SEL = logic [DEPTH-1:0][_WIDTH-1:0])
    (output _SEL sel, input DIGIT count, stride,
     input logic en, pre_carry, clk, resetn);
    DIGIT count_mod_stride, stride_m1;
    logic [_WIDTH-1:0] count_over_stride, count_over_stride2;
    always_comb `FOR(int, I, DEPTH) begin
        sel[I] = I;
        if (count >= stride) begin
            sel[I] = count_over_stride;
            sel[I] = I - sel[I];
            if ($signed(sel[I]) < 0) sel[I] += DEPTH;
        end
    end
    `REG(stride_m1, stride-1);
    `always_ff2 if (~resetn) begin
        count_mod_stride <= '0;
        count_over_stride <= '0;
    end else begin
        if (en) begin
            count_mod_stride <= count_mod_stride + 1;
            if (count_mod_stride == stride_m1) begin
                count_over_stride <= count_over_stride + 1;
                count_mod_stride <= '0;
            end
        end
        if (pre_carry) begin
            count_mod_stride <= '0;
            count_over_stride <= '0;
        end
    end
endmodule
