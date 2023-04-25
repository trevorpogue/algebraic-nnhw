`include "../top/define.svh"


module tilebuf
    import globals::*;
    #(type Q,
      integer QFIFO_DEPTH=TILE_BUF_DEPTH,
      integer USE_WROTE_LAYER_AS_EN=FALSE,
      type DIGIT = Tiler::DIGIT,
      integer MAX_TILE_SIZE=MAX_TILE_SIZE_M,
      DATA_TYPE = LAYERIO,
      BURST_COUNT = 1
      )
    (fifobus layerfifo, data q,
     output logic half_full, full,
     output logic tile_rd_ready,
     output logic two_tiles_rd_ready,
     input logic                     wrote_layer,
     input logic start_tile_rd,
     input                           DIGIT total_layer_reads,
     input logic [$clog2(MAX_TILE_SIZE)-1:0] tile_size,
     input logic tile_size_valid,
     input logic                     clk, resetn);
    localparam                       IN_DELAY0 = 1;
    localparam                       RD_DELAY0 = 0;
    localparam                       RD_DELAY1 = 1;
    localparam                       RD_DELAY2 = 1;
    localparam                       RD_LATENCY = RD_DELAY0 + RD_DELAY1 + RD_DELAY2 + 1;
    DIGIT total_layer_reads_over_burst_count;
    `REG2__(wrote_layer_0, wrote_layer, IN_DELAY0);
    `REG2__(total_reads_0, total_layer_reads, IN_DELAY0);
    `REG2__(tile_size_0, tile_size, IN_DELAY0);
    `REG2__(tile_size_valid_0,tile_size_valid, IN_DELAY0);
    logic                            start_tile_rd_0;
    logic [1:0]                      start_tile_rd_counter;
    logic                            _start_tile_rd_0;
    `ONOFF__(got_start_tile_rd, start_tile_rd, _start_tile_rd_0, 0);
    `POSEDGE(_start_tile_rd_0, got_start_tile_rd & tile_rd_ready);
    `REG(start_tile_rd_0, _start_tile_rd_0, 0);
    logic                            tile_size_valid_;
    logic [$clog2(QFIFO_DEPTH)-1:0]  tile_rd_count, tile_size_m1;
    logic [$clog2(QFIFO_DEPTH)-1:0]  tile_rd_count_d;
    DIGIT layer_rd_count, layer_rd_count_d;
    logic [$clog2(MAX_LAYERS)-1:0]   unread_layer_count, unread_layer_count_d;
    logic                            unread_layer_count_logic;
    DIGIT layer_tiles_rd_count, layer_tiles_rd_count_d;
    logic [$clog2(QFIFO_DEPTH)-1:0]  qfifo_size, qfifo_size_d, qfifo_size_;
    logic [$clog2(QFIFO_DEPTH)-1:0]  future_qfifo_size, future_qfifo_size_d;
    fifobus #(.Q(Q), .DEPTH(QFIFO_DEPTH)
              ,.WRLATENCY(1)
              ,.RDLATENCY(RD_DELAY2)
              ) qfifo(.clk, .resetn);
    fifobus #(.Q(logic), .DEPTH(MAX_LAYERS)
              ,.WRLATENCY(1)
              ,.RDLATENCY(RD_DELAY2)) wrote_layer_fifo
        (.clk, .resetn);
    logic                            _layer_rd_en;
    logic                            layer_rd_en, tile_rd_en;
    logic                            done_reading_layer;
    logic                            start_layer_rd;
    logic                            done_reading_layer_tiles;
    DIGIT total_reads_m1;
    DIGIT total_reads_m2;
    DIGIT total_reads_gt1;
    Info qinfo;
    always_comb begin
        qinfo = qfifo.q.info;
    end

    `REG_(q.value, qfifo.q.value, RD_DELAY1, qvalue);
    `REG_(q.info_master.value, qinfo, RD_DELAY1, qinfo);

    `REG(tile_size_valid_, tile_size_valid_0, 1);
    assign half_full = future_qfifo_size[$clog2(QFIFO_DEPTH)-1];
    assign full = qfifo.full;
    `INFOFIFO(qfifo, "IPFIFO");
    `IPFIFO(wrote_layer_fifo);
    `REG(tile_rd_en, |tile_rd_count, 1);
    `ONOFF(_layer_rd_en, start_layer_rd, done_reading_layer);
    assign layer_rd_en = _layer_rd_en & !half_full & !layerfifo.empty
                         & layerfifo.rdready & layerfifo.rdready2;

    if (USE_WROTE_LAYER_AS_EN) begin
        `ONOFF(start_layer_rd, wrote_layer & !start_layer_rd, start_layer_rd);
    end else begin
        assign start_layer_rd = tile_size_valid & !wrote_layer_fifo.empty;
    end
    `REG(tile_rd_ready,
         (qfifo_size_d >= tile_size)
         & tile_size_valid_
         & unread_layer_count_logic);
    `REG(two_tiles_rd_ready,
         (qfifo_size_d >= {tile_size<<1})
         & tile_size_valid_
         & unread_layer_count_logic);

    assign done_reading_layer = (layer_rd_count == total_reads_m1)
        && layer_rd_en;

    `REG_(wrote_layer_fifo.wrreq, wrote_layer_0, 1, wrote_layer);
    assign wrote_layer_fifo.rdreq = start_layer_rd;

    always_comb begin
        layer_rd_count_d = layer_rd_count;
        if (layer_rd_en) begin
            layer_rd_count_d += BURST_COUNT;
        end
    end
    assign layerfifo.rdreq = layer_rd_en;
    assign qfifo.wrreq                 = layerfifo.q.info.valid;
    assign qfifo.d.value               = layerfifo.q.value;
    assign qfifo.d.info_master.value   = layerfifo.q.info;
    assign qfifo.rdreq                 = tile_rd_en;

    localparam DELAY0 = 0;
    `REG(qfifo_size_, qfifo_size, DELAY0);
    `REG(future_qfifo_size, future_qfifo_size_d);
    `REG(tile_rd_count, tile_rd_count_d);
    `REG(layer_tiles_rd_count, layer_tiles_rd_count_d);
    always_comb begin
        layer_tiles_rd_count_d = layer_tiles_rd_count;
        if (tile_rd_en) begin
            layer_tiles_rd_count_d = layer_tiles_rd_count_d + 1;
        end
        if (done_reading_layer_tiles)
            layer_tiles_rd_count_d = '0;
        tile_rd_count_d = tile_rd_count;
        if (tile_rd_count_d > 0)
            tile_rd_count_d -= 1;
        if (start_tile_rd_0)
            tile_rd_count_d += tile_size;
    end
    logic total_reads_eq_1;
    `always_ff2 if (~resetn) begin
        layer_rd_count <= '0;
        qfifo_size <= '0;
        unread_layer_count <= '0;
        tile_size_m1 <= '0;
        total_reads_m1 <= '1;
        total_reads_m2 <= '1;
        total_reads_gt1 <= '0;
        done_reading_layer_tiles <= '0;
        total_reads_eq_1 <= '0;
    end else begin
        total_reads_m2 <= total_reads_0 - 2;
        total_reads_m1 <= total_reads_0 - BURST_COUNT;
        total_reads_eq_1 <= total_reads_0 == 1;
        done_reading_layer_tiles
            <= (layer_tiles_rd_count == total_reads_m1) & tile_rd_en;
        // | total_reads_eq_1;
        total_reads_gt1 <= total_reads_0 > 1;
        tile_size_m1 <= tile_size_0 - 1;
        qfifo_size <= qfifo_size_d;
        layer_rd_count <= layer_rd_count_d;
        unread_layer_count <= unread_layer_count_d;
        unread_layer_count_logic <= |unread_layer_count_d;
        if (layer_rd_en) if (done_reading_layer)
            layer_rd_count <= '0;
    end
    DIGIT c_qfifo_writes, c_qfifo_reads, c_layerfifo_writes,
        c_layerfifo_reads;
    DIGIT c_qfifo_writes2, c_qfifo_reads2, c_layerfifo_writes2,
        c_layerfifo_reads2, c_layerfifo_reads3;
    `SIMCOUNTER(c_layerfifo_writes, layerfifo.wrreq & !layerfifo.full
                ,wrote_layer
                );
    `SIMCOUNTER(c_layerfifo_writes2, layerfifo.wrreq
                ,wrote_layer
                );
    `SIMCOUNTER(c_qfifo_writes, qfifo.wrreq && !qfifo.full
                );
    `SIMCOUNTER(c_qfifo_writes2, qfifo.wrreq
                );
    `SIMCOUNTER(c_qfifo_reads, qfifo.rdreq & !qfifo.empty
                );
    `SIMCOUNTER(c_qfifo_reads2, qfifo.rdreq
                );
    `SIMCOUNTER(c_layerfifo_reads, layerfifo.rdreq & !layerfifo.empty
                );
    `SIMCOUNTER(c_layerfifo_reads2, layerfifo.rdreq
                );
    `SIMCOUNTER(c_layerfifo_reads3, layerfifo.q.info.valid
                );
    always_comb begin
        case({qfifo.wrreq, start_tile_rd_0})
            2'b00: qfifo_size_d = qfifo_size;
            2'b01: qfifo_size_d = qfifo_size - tile_size_0;
            2'b10: qfifo_size_d = qfifo_size + 1;
            2'b11: qfifo_size_d = qfifo_size - tile_size_m1;
        endcase
        case({layer_rd_en, start_tile_rd_0})
            2'b00: future_qfifo_size_d = future_qfifo_size;
            2'b01: future_qfifo_size_d = future_qfifo_size - tile_size_0;
            2'b10: future_qfifo_size_d = future_qfifo_size + BURST_COUNT;
            2'b11: future_qfifo_size_d
                = future_qfifo_size + BURST_COUNT - tile_size_0;
        endcase
    end
    `ONOFF__(en, start_tile_rd, done_reading_layer_tiles_, 0);
    `REG(done_reading_layer_tiles_, done_reading_layer_tiles);
    if (USE_WROTE_LAYER_AS_EN) begin
        assign unread_layer_count_d = wrote_layer_0;
    end else begin
        always_comb
            case({wrote_layer_0, done_reading_layer_tiles & en})
                2'b00: unread_layer_count_d = unread_layer_count;
                2'b01: unread_layer_count_d = unread_layer_count - 1;
                2'b10: unread_layer_count_d = unread_layer_count + 1;
                2'b11: unread_layer_count_d = unread_layer_count;
            endcase
    end
endmodule
