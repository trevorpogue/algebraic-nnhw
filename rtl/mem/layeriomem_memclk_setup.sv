`include "../top/define.svh"



logic        start;
localparam CLKDIV = LAYERIOMEM_CLK_DIV;
localparam DEPTH = LAYERIOMEM_DEPTH;
localparam INSTRUC_LOAD_DELAY = 2;
typedef logic [$clog2(DEPTH)-1:0] AddressmemAddress;
typedef logic [$clog2(DEPTH/CLKDIV)-1:0] LayeriomemAddress;
localparam integer DIV_DEPTH = $ceil(DEPTH/CLKDIV);
logic [CLKDIV-1:0] dfifos_qvalid;
logic [CLKDIV-1:0][$clog2(CLKDIV)-1:0] layeriomem_sel;
logic [CLKDIV-1:0][$clog2(CLKDIV)-1:0] qfifo_sel;
logic [CLKDIV-1:0][$clog2(CLKDIV)-1:0] layeriomem_sel_;
typedef logic [LAYERIO_WIDTH*SZJ-1:0] Q;
fifo_array_bus #(.I(CLKDIV), .Q(Layeriovec), .DEPTH(DEPTH),
                 .RDLATENCY(2)) rdtilers
    (.clk, .resetn);
fifo_array_bus #(.I(CLKDIV), .Q(Layeriovec), .DEPTH(DEPTH)) wrtilers
    (.clk, .resetn);
dpram_array_bus #(.I(CLKDIV), .Q(LayeriomemAddress), .DEPTH(DEPTH)) addressmems
    (.clk, .resetn(hard_resetn));
dpram_array_bus #(.I(CLKDIV), .Q(Q), .DEPTH(DIV_DEPTH)) layeriomems
    (.clk, .resetn(hard_resetn));
dpram_array_bus #(.I(CLKDIV), .Q(Q), .DEPTH(DEPTH)) tilermems
    (.clk, .resetn(hard_resetn));
typedef logic [CLKDIV-1:0][SZI-1:0][A_WIDTH-1:0] QfifoD;

logic [CLKDIV-1:0]         qinfo_fifo_dvalids;

DIGITS             sizes;
DIGITS             counts;
logic [TOTAL_DIGITS-1:0]  ens;
logic [TOTAL_DIGITS-1:0]  carries;
logic [TOTAL_DIGITS-1:0]  pre_carries;
DIGIT             count_;
logic             pre_carry_;
logic             en_;
logic [CLKDIV-1:0][$bits(Info)-1:0] qinfo_fifo_d;
Instruc next_rd_instruc_q, rd_instruc_q, wr_instruc_q;
logic        load_rd_instruc;
logic        _load_rd_instruc;
logic start_or_last_elm;
DIGITS next_sizes, next_strides, strides, wrsizes;
logic [TOTAL_DIGITS-1:0] at_last_values;
logic [$clog2(CLKDIV)-1:0] total_unused_rdtilers_in_edgecase;
logic [$clog2(CLKDIV)-1:0] tmp;
logic [$clog2(CLKDIV)-1:0] last_rdtiler_in_edgecase;
logic at_last_elm;
logic rd_instruc_empty;
logic writing_layerio_layer_next;

`CONNECT_FIFO_ARRAY(rdtilers, CLKDIV);
`CONNECT_FIFO_ARRAY(wrtilers, CLKDIV);
`CONNECT_DPRAM_ARRAY(layeriomems, CLKDIV);
`CONNECT_DPRAM_ARRAY_(tilermems, CLKDIV);
`CONNECT_DPRAM_ARRAY(addressmems, CLKDIV);

`FOR(genvar, I, CLKDIV) begin : gdprams
    if ((MEM_ID != LINEAR_MEM) | (I == 0)) begin
        `DPRAM(addressmems.ios[I], addressmems);
        `DPRAM(layeriomems.ios[I], layeriomems);
    end
end

`FOR(genvar, I, CLKDIV) begin : gtilers
    assign layeriomems.wraddress[I]               = tilermems.wraddress[I];
    assign layeriomems.wrreq[I]                   = tilermems.wrreq[I];
    assign layeriomems.d.value[I]                 = tilermems.d.value[I];
    assign layeriomems.d.info_master.value[I]     = tilermems.d.info[I];
    assign tilermems.q.value[I]             = layeriomems.q.value[I];
    assign tilermems.q.info_master.value[I] = layeriomems.q.info[I];
    assign tilermems.ready[I]               = layeriomems.ready[I];
    if (I == 0) begin : gtilers0
        layerio_reader #(READER, LAYERIO, I, DEPTH, `EXPORT_ARITH)
        layerio_reader_u
            (.master(rdtilers.ios[I]), .slave(tilermems.ios[I]),
             .start(start),
             .instruc_q_in(rd_instruc_q), .counts(counts),
             .ens,
             .carries,
             .pre_carries,
             .at_last_elm,
             .wrote_layerio_layer,
             .at_last_values,
             .clk,
             .resetn
             );
        layerio_writer0 #(WRITER, LAYERIO, I, DEPTH,
                          `EXPORT_ARITH)
        layerio_writer_u
            (.master(wrtilers.ios[I]), .slave(tilermems.ios[I]),
             .instruc(layerio_wr_instruc),
             .instruc_q_out(wr_instruc_q),
             .wrote_layerio_layer,
             .sizes_out(wrsizes),
             .clk,
             .resetn
             );
    end else begin : gtilers_gt_0
        layerio_reader #(READER, LAYERIO, I, DEPTH,
                         `EXPORT_ARITH)
        layerio_reader_u
            (.master(rdtilers.ios[I]), .slave(tilermems.ios[I]),
             .start(start), .instruc_q_in(rd_instruc_q),
             .wrote_layerio_layer,
             .instruc_q_in_valid(rd_instruc_qvalid),
             .clk,
             .resetn
             );
        layerio_writer_gt0 #(WRITER, LAYERIO, I, DEPTH,
                             `EXPORT_ARITH)
        layerio_writer_u
            (.master(wrtilers.ios[I]), .slave(tilermems.ios[I]),
             .wrote_layerio_layer,
             .instruc_q_in(wr_instruc_q),
             .clk,
             .resetn
             );
    end
end

wrote_layer_unit wrote_layer_u
    (.size(total_layerio_writes),
     .wrreqs(wrtilers.wrreq),
     .islastlayer(fromtop.layer_params_islastlayer),
     .wrote_layer(wrote_layerio_layer),
     .writing_layer_next(writing_layerio_layer_next),
     .clk, .resetn);

wrote_layer_unit wrote_inference_u
    (.size(fromtop.total_inference_writes),
     .wrreqs(wrtilers.wrreq),
     .islastlayer(fromtop.layer_params_islastlayer),
     .wrote_layer(wrote_inference),
     .clk, .resetn);

look_ahead_instruc_loader
    #(TOTAL_PARAMS, DIGIT_WIDTH,
      INSTRUC_LOAD_DELAY)  rd_instruc_loader_u
        (.dfifo(layerio_rd_instruc),
         .load(load_rd_instruc),
         .qvalid(rd_instruc_qvalid),
         .next_qvalid(next_rd_instruc_qvalid),
         .next_q(next_rd_instruc_q), .q(rd_instruc_q),
         .empty(rd_instruc_empty),
         .clk, .resetn);
