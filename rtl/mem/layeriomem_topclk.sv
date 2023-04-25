`include "../top/define.svh"


module layeriomem_topclk
    import globals::*; import Tiler::*;
    #(`IMPORT_ARITH)
    (fifobus layerio, fifobus layerio_rd_instruc, fifobus layerio_wr_instruc,
     input LayerParam size_w_c,
     output logic wrote_layerio_layer,
     output logic wrote_inference,
     input logic start, input LayerParams layer_params,
     input logic topclk, memclk, resetn, soft_resetn, hard_resetn);
    localparam   CLKDIV = LAYERIOMEM_CLK_DIV;
    localparam   DEPTH = LAYERIOMEM_DEPTH;
    logic        clk;
    localparam   FMAX_DELAY0 = 0;
    localparam   integer DIV_DEPTH = $ceil(DEPTH/CLKDIV);
    typedef logic [$clog2(DEPTH)-1:0] AddressmemAddress;
    typedef logic [$clog2(DIV_DEPTH)-1:0] LayeriomemAddress;
    `FIFOBUS_CP(_layerio, layerio);
    fifopad #(FMAX_DELAY0) layerio_fifopad_u(layerio, _layerio);
    typedef logic [CLKDIV-1:0][SZJ-1:0][A_WIDTH-1:0] QfifoD;
    typedef struct                                   packed {
        AddressmemAddress addressmem_address;
        LayeriomemAddress addressmem_d;
        Layeriovec layerio_d;
    } DfifoD;
    typedef struct                                   packed {
        DIGIT total_inference_writes;
        logic                                        layer_params_islastlayer;
        logic                                        layer_params_valid;
        logic                                        start;
        logic                                        valid;
    } FromTop;
    typedef struct                                   packed {
        logic                                        wrote_inference;
        DIGIT next_stride_tile_fill_w;
        DIGIT size_tile_fill_w;
        DIGIT total_layerio_writes;
        DIGIT wr_offset;
        DIGIT rd_offset;
        logic                                        rd_instruc_qvalid;
        logic                                        next_rd_instruc_qvalid;
        logic                                        wrote_layerio_layer;
        logic                                        valid;
    }ToTop;
    logic                                            wrote_layerio_layer_;
    logic [$clog2(CLKDIV)-1:0]                       dfifosel;
    logic [CLKDIV-1:0]                               dfifosel_1hot;
    AddressmemAddress addressmem_addresses;
    logic [CLKDIV-1:0] [$clog2(DIV_DEPTH)-1:0]       layeriomem_addresses;
    FromTop fromtop_topclk, fromtop_memclk;
    ToTop totop_topclk, totop_memclk;

    `POSEDGE(wrote_layerio_layer, totop_topclk.wrote_layerio_layer);
    assign wrote_inference = totop_topclk.wrote_inference;
    assign totop_memclk.valid = 1'b1;
    assign clk = topclk;
    assign fromtop_topclk = {layer_params.total_inference_writes,
                             layer_params.islastlayer,
                             layer_params.valid,
                             start, 1'b1};
    clock_crossing_data #(FromTop, ToTop) clock_crossing_data_u
        (.clka_a2b(fromtop_topclk), .clkb_a2b(fromtop_memclk),
         .clka_b2a(totop_topclk), .clkb_b2a(totop_memclk),
         .clka(topclk), .clkb(memclk), .resetn);

    localparam                                       DFIFOS_DEPTH = TILE_BUF_DEPTH;
    fifobus #(.Q(logic), .USE_RDWR_CLKS(TRUE)
              ,.DEPTH(TILE_BUF_DEPTH)) rdreqfifo(.clk, .resetn);
    fifo_array_bus #(.I(CLKDIV), .Q(DfifoD) ,.USE_RDWR_CLKS(TRUE)
                     ,.DEPTH(DFIFOS_DEPTH)) dfifos(.clk, .resetn);
    // QFIFO_DEPTH doesn't need to be big (theoretically can be 1)
    localparam                                       QFIFO_DEPTH = 8;
    localparam                                       QFIFO_WRLATENCY = 3;
    localparam                                       QFIFO_RDLATENCY = 5;
    localparam                                       QINFO_FIFO_DELAY = 2;
    fifobus #(.Q(Layeriovec) ,.D(QfifoD) ,.USE_RDWR_CLKS(TRUE)
              ,.RDREQ_AS_ACK(TRUE)
              ,.DEPTH(QFIFO_DEPTH)
              ,.RDLATENCY(QFIFO_RDLATENCY)
              ,.WRLATENCY(QFIFO_WRLATENCY)) qfifo(.clk, .resetn);
    fifobus #(.Q(Info), .D(Info[CLKDIV-1:0]), .USE_RDWR_CLKS(TRUE)
              ,.RDREQ_AS_ACK(TRUE)
              ,.DEPTH(QFIFO_DEPTH)
              ,.RDLATENCY(QFIFO_RDLATENCY-QINFO_FIFO_DELAY)
              ,.WRLATENCY(QFIFO_WRLATENCY)) qinfo_fifo(.clk, .resetn);
    `IPFIFO(rdreqfifo);
    `CONNECT_FIFO_ARRAY(dfifos, CLKDIV);
    _fifo_dgtq_faster_rdclk qfifo_u(qfifo);
    _fifo_dgtq_faster_rdclk qinfo_fifo_u(qinfo_fifo);
    `FOR(genvar, I, CLKDIV) begin : gtilers
        if (!USE_FIFO_IP) begin
            fifo dfifos_u (.io(dfifos.ios[I]));
            fifo_info #(TRUE) dfifos_info_u (.io(dfifos.ios[I]));
        end else begin
            logic [$clog2(DFIFOS_DEPTH)-1:0] dfifos_wrusedw;
            `REG3(dfifos.ios[I].half_full, half_full,
                  dfifos_wrusedw >= {(DFIFOS_DEPTH)>>1});
            if (DFIFOS_DEPTH <= 512) begin
                `DFIFOS_IPFIFO(dram_fifo512);
            end else if (DFIFOS_DEPTH <= 1024) begin
                `DFIFOS_IPFIFO(dram_fifo1024);
            end else if (DFIFOS_DEPTH <= 2048) begin
                `DFIFOS_IPFIFO(dram_fifo2048);
            end else if (DFIFOS_DEPTH <= 4096) begin
                `DFIFOS_IPFIFO(dram_fifo4096);
            end else if (DFIFOS_DEPTH <= 8192) begin
                `DFIFOS_IPFIFO(dram_fifo8192);
            end else if (DFIFOS_DEPTH <= 16384) begin
                `DFIFOS_IPFIFO(dram_fifo16384);
            end
            fifo_info #(TRUE) dfifos_info_u (.io(dfifos.ios[I]));
        end
    end

    localparam                               ADDRESS_U_LATENCY = 3;
    `REG2__(layerio_wrreq_, _layerio.wrreq, ADDRESS_U_LATENCY);
    `REG2__(layerio_d_value_, _layerio.d.value, ADDRESS_U_LATENCY);
    dfifo_addressmem_d_unit
        #(DEPTH, CLKDIV, ADDRESS_U_LATENCY) address_u
            (
             // outputs
             .addressmem_addresses, .layeriomem_addresses,
             // inputs
             .wr_offset(totop_topclk.wr_offset),
             .rd_offset(totop_topclk.rd_offset),
             .dfifosel,
             .en(_layerio.wrreq),
             .wrote_layerio_layer(wrote_layerio_layer_),
             .stride_w(totop_topclk.next_stride_tile_fill_w),
             .size_w(size_w_c),
             .size(totop_topclk.total_layerio_writes),
             .islastlayer(layer_params.islastlayer),
             .clk(topclk), .resetn);
    rdreqfifo_wrreq_unit rdreqfifo_wrreq_u
        (.q(rdreqfifo.wrreq), .size_w(totop_topclk.size_tile_fill_w),
         .wrote_layerio_layer(wrote_layerio_layer_),
         .en(_layerio.rdreq),
         .clk(topclk), .resetn);
    DIGIT c_rdreqfifo_wrreqs, c_qfifo_rdreqs;
    `SIMCOUNTER(c_rdreqfifo_wrreqs, rdreqfifo.wrreq);
    `SIMCOUNTER(c_qfifo_rdreqs, qfifo.rdreq);

    assign _layerio.empty = '0;
    always_comb begin
        rdreqfifo.d.value = _layerio.rdreq;
        rdreqfifo.wrclk = topclk;
        qinfo_fifo.rdclk = clk;
        qfifo.rdclk = clk;
        _layerio.q.value = qfifo.q.value;
    end
    localparam DELAY0 = 1;  // not tunable
    `REG2_(qfifo.rdreq, ~qfifo.almost_empty, qfifordreq, DELAY0);
    `REG2_(qinfo_fifo.rdreq, ~qfifo.almost_empty, qinfo_fifo_rdreq, DELAY0);
    `REG2_(_layerio.q.info_master.value,
           qinfo_fifo.q.info.valid? qinfo_fifo.q.value : '0,
           layerio_qinfo, QINFO_FIFO_DELAY)

    assign dfifosel_1hot = 1<<dfifosel;
    `FOR(genvar, I, CLKDIV) begin
        assign dfifos.ios[I].wrclk = topclk;
    end

    always_ff @(posedge clk or negedge resetn)
        `FOR(int, I, CLKDIV) begin
            if (~resetn) begin
                dfifos.wrreq[I] <= '0;
                dfifos.d.value[I].addressmem_address <= '0;
                dfifos.d.value[I].addressmem_d <= '0;
                dfifos.d.value[I].layerio_d <= '0;
            end else begin
                dfifos.wrreq[I] <= dfifosel_1hot[I] & {CLKDIV{layerio_wrreq_}};
                dfifos.d.value[I].addressmem_address <= addressmem_addresses;
                dfifos.d.value[I].addressmem_d
                    <= layeriomem_addresses[dfifosel];
                dfifos.d.value[I].layerio_d <= layerio_d_value_;
            end
        end
    assign _layerio.full = dfifos.full[0] | !totop_topclk.next_rd_instruc_qvalid | rdreqfifo.full;
    assign _layerio.half_full = dfifos.half_full[0] | !totop_topclk.next_rd_instruc_qvalid | rdreqfifo.half_full;
    assign _layerio.rdready = !_layerio.half_full;
    assign _layerio.rdready2 = !_layerio.half_full;

    layeriomem_memclk #(FromTop, `EXPORT_ARITH) layeriomem_memclk_u
        (.dfifos, .rdreqfifo,
         .layerio_rd_instruc, .layerio_wr_instruc,
         .qfifo, .qinfo_fifo,
         .total_layerio_writes(totop_memclk.total_layerio_writes),
         .wr_offset(totop_memclk.wr_offset),
         .wrote_inference(totop_memclk.wrote_inference),
         .rd_offset(totop_memclk.rd_offset),
         .wrote_layerio_layer(totop_memclk.wrote_layerio_layer),
         .next_stride_tile_fill_w(totop_memclk.next_stride_tile_fill_w),
         .size_tile_fill_w(totop_memclk.size_tile_fill_w),
         .rd_instruc_qvalid(totop_memclk.rd_instruc_qvalid),
         .next_rd_instruc_qvalid(totop_memclk.next_rd_instruc_qvalid),
         .start_(fromtop_memclk.start),
         .fromtop(fromtop_memclk),
         .clk(memclk),
         .resetn,
         .soft_resetn, .hard_resetn);
endmodule
