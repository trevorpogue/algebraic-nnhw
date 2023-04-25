`include "../top/define.svh"


module layeriomem
    import Layeriomem::*; import globals::*; import Tiler::*;
    #(`IMPORT_ARITH)
    (fifobus layerio, fifobus layerio_rd_instruc, fifobus layerio_wr_instruc,
     input LayerParam size_w_c,
     input LayerParam total_layer_reads,
     input logic [$clog2(MAX_TILE_SIZE_M)-1:0] tile_size_m,
     input logic start, input LayerParams layer_params,
     input logic done_writing,
     output logic wrote_layerio_layer,
     output logic wrote_inference,
     input logic topclk, memclk, resetn, soft_resetn, hard_resetn);
    logic        clk; assign clk = topclk;

    localparam   DEPTH = LAYERIOMEM_DEPTH;
    DIGIT layer_rd_count;
    DIGIT tile_rd_count;
    logic        tile_rd_ready, start_tile_rd, two_tiles_rd_ready;
    localparam   QFIFO_DEPTH = TILE_BUF_DEPTH;
    fifobus #(.Q(TopLayeriovec), .DEPTH(DEPTH)) _layerio(.clk, .resetn);
    fifobus #(.Q(Layeriovec), .DEPTH(DEPTH)) __layerio(.clk, .resetn);
    data #(TopLayeriovec) q(.clk, .resetn);
    localparam   LAYERIOMEM_SIZE_ = LAYERIOMEM_SIZE;
    localparam   LAYERIOMEM_DEPTH_ = LAYERIOMEM_DEPTH;
    localparam   SZJ_ = SZJ;
    logic        wrote_layer;
    assign								wrote_layer = wrote_layerio_layer;
    layeriomem_topclk #(`EXPORT_ARITH) layeriomem_topclk_u
        (.layerio(__layerio), .layerio_rd_instruc, .layerio_wr_instruc,
         .size_w_c,
         .start, .wrote_layerio_layer, .wrote_inference, .layer_params,
         .topclk, .memclk,
         .resetn,
         .soft_resetn,
         .hard_resetn);
    if (FALSE) begin
        fill_mxu #(`EXPORT_ARITH)
        fill_mxu (.slave(__layerio), .master(_layerio), .layer_params,
                  .clk, .resetn);
    end else begin
        always_comb begin
            __layerio.rdreq = _layerio.rdreq;
            __layerio.wrreq = _layerio.wrreq;
            __layerio.d.value = _layerio.d.value;
            __layerio.d.info_master.value = _layerio.d.info;
            _layerio.half_full = __layerio.half_full;
            _layerio.full = __layerio.full;
            _layerio.empty = __layerio.empty;
            _layerio.rdready = __layerio.rdready;
            _layerio.rdready2 = __layerio.rdready2;
            _layerio.q.value = __layerio.q.value;
            _layerio.q.info_master.value = __layerio.q.info;
        end
    end
    logic                           half_full;
    logic                           tilebuf_en;
    tilebuf #(.Q(TopLayeriovec)
              ,.QFIFO_DEPTH((MAX_TILE_SIZE_M+1)*3)
              ,.DATA_TYPE(LAYERIO)
              ) tile_buf_u
        (.layerfifo(_layerio),
         .wrote_layer(wrote_layer),
         .total_layer_reads,
         .tile_size(tile_size_m),
         .half_full(half_full),
         .start_tile_rd,
         .tile_rd_ready,
         .two_tiles_rd_ready,
         .tile_size_valid(done_writing),
         .q, .clk, .resetn
         );
    assign layerio.q.value             = q.value;
    assign layerio.q.info_master.value = q.info;
    assign layerio.full                = _layerio.full;
    assign layerio.half_full           = _layerio.half_full;
    assign layerio.rdready = tile_rd_ready;
    assign layerio.rdready2 = tile_rd_ready;
    assign layerio.empty = !tile_rd_ready;
    assign _layerio.wrreq              = layerio.wrreq;
    assign _layerio.d.value            = layerio.d.value;
    `REG(start_tile_rd, layerio.rdreq, 0);
endmodule


module fill_mxu import globals::*;
    #(`IMPORT_ARITH)
    (fifobus slave, master,
     input LayerParams layer_params,
     input logic clk, resetn);
    localparam   KERNEL_STRIDE = 2; localparam  KERNEL_SIZE = 5;
    localparam   SZ = (KERNEL_SIZE+(KERNEL_STRIDE-1))/KERNEL_STRIDE;
    localparam   TOTALBUFS = SZ;
    localparam   BUFDEPTH = MAX_W/KERNEL_STRIDE*SZ;
    logic [SZ-1:0] col_en, col_en_d;
    logic          col_en_d0, row_en_d0;
    Info dinfo, dinfo2, dinfo3;
    Layeriovec d;
    fifo_array_bus #(.I(TOTALBUFS), .Q(Layeriovec),
                     .DEPTH(BUFDEPTH)) bufs(.clk, .resetn);
    fifobus #(.Q(Info), .DEPTH(BUFDEPTH)) infofifo(.clk, .resetn);
    `CONNECT_FIFO_ARRAY(bufs, SZ);
    `REG(d, slave.q.value, SZ);
    `REG(dinfo, slave.q.info, SZ);
    `REG(dinfo2, slave.q.info, SZ-1);
    `IPFIFO_1CLK(infofifo);
    `FOR(genvar, I, SZ) begin
        `IPFIFO_1CLK(bufs.ios[I]);
        assign bufs.d.value[I] = d;
    end

    logic [TOTALBUFS-1:0] wrreqs;
    always_comb begin
        col_en_d = col_en;
        if (~resetn) begin
            col_en_d = 1'b1;
        end else begin
            if (dinfo.valid) col_en_d = {col_en, col_en_d0};
            if (dinfo.last_w) col_en_d = 1'b1;
        end
    end
    `ONOFF_(col_en_d0, dinfo2.last_w, slave.q.info.last_w, 1,
            col_en_d0, clk, resetn, 1);
    always_ff @(posedge clk or negedge resetn) begin
        col_en <= col_en_d;
    end
    `ONOFF__(new_tile_k, dinfo2.new_tile_k, infofifo.wrreq);
    always_comb begin
        `FOR(int, COL, SZ) begin
            bufs.wrreq[COL] = '0;
            if (col_en[COL]) bufs.wrreq[COL] = dinfo.valid;
        end
    end
    logic thing;
    always_comb begin
        slave.rdreq = master.rdreq;
        slave.wrreq = master.wrreq;
        slave.d.value = master.d.value;
        master.half_full = slave.half_full;
        master.full = slave.full;
        master.empty = slave.empty;
        master.rdready = slave.rdready;
        master.rdready2 = slave.rdready2;
        bufs.rdreq = bufs.empty? '0 : '1;
        infofifo.rdreq = !bufs.empty;
        infofifo.wrreq = bufs.wrreq[SZ-1];
        dinfo3 = dinfo;
        dinfo3.new_tile_k = new_tile_k;
        infofifo.d.value = dinfo3;
    end
    TopLayeriovec q;
    `FOR(genvar, I, SZ) begin
        assign q[I*SZ+SZ-1:I*SZ] = bufs.q.value[I];
    end
    assign master.q.value = q[SZ*SZ-1:0];
    always_comb begin
        master.q.info_master.value = '0;
        if (infofifo.q.info.valid)
            master.q.info_master.value = infofifo.q.value;
    end
endmodule
