`include "../top/define.svh"


module counter
    #(integer RANGE=2, INC_SZ=1, INIT_VAL=0)
    (input logic en, logic clk, logic resetn, logic reset,
     logic [$clog2(RANGE)-1:0] init_val,
     output logic              carry, logic [$clog2(RANGE)-1:0] count,
     logic                     complete,
     logic                     complete_n,
     logic                     counting);
    logic                      carry_buf;
    assign complete_n = ~complete;
    assign carry = (count >= (RANGE-INC_SZ));
    always_ff @(posedge clk or negedge resetn) begin
        if (~resetn) begin
            count <= INIT_VAL;
            counting <= 1'd0;
            carry_buf <= 1'd0;
        end
        else begin
            if (en) count <= $bits(count)'(count + INC_SZ);
            if (carry & en) count <= '0;
            if (en) counting <= 1'd1;
            else if (carry_buf) counting <= 1'd0;
            if (carry | en)
                carry_buf <= carry;
            if (carry)
                complete <= 1;
            else if (en)
                complete <= 0;
        end
    end
endmodule


module dram_emif_fifo import globals::*;
    #(type Q=Dram::Q, D=Q,
      integer DEPTH=Dram::DEPTH, BURST_COUNT=1, RANGE=16,
      WAIT_FOR_CAL=1, FAST_COMPILE=FALSE)
    (sprambus master, emif_phy_bus slave,
     input logic dram_q_clk_wrready,
     input logic tilebuf_wrready,
     input logic hard_resetn
     ,output dram_clk
     );
    // this modulde lets its user control the dram from a simple sp_mem
    // interace
    // where the sprambus is an avalon memory-mapped (amm) interface for
    // a single port mem/ram
    // it contains appropriate fifos for connecting two amm interfaces using
    // different clocks
    logic        clk, resetn;
    assign clk = master.clk; assign resetn = master.resetn;
    logic        emif_clk, cal_success;
    logic        emif_rdreq, emif_wrreq;
    logic        reqvalid, start_top_ff, start_top;
    logic        ready_for_new_burst;
    sprambus #(.Q(Q), .DEPTH(DEPTH)) emif(.clk(emif_clk), .resetn);
    Q _ammq;
    assign dram_clk = emif_clk;
    assign master.q.value = _ammq;
    assign master.q.info_master.value = emif.q.info;
    always_ff @(posedge clk or negedge resetn)
        if (~resetn) begin
            start_top_ff <= 1'b0;
        end else begin
            start_top_ff <= 1'b1;
        end
    typedef struct packed {
        logic      tilebuf_wrready;
        logic      valid;
    }FromTop;
    typedef struct packed {
        logic      cal_success;
        logic      valid;
    }ToTop;
    ToTop totop_topclk, totop_bottomclk;
    FromTop fromtop_topclk, fromtop_bottomclk;
    assign fromtop_topclk = {tilebuf_wrready, 1'b1};
    assign totop_bottomclk = {cal_success, 1'b1};
    clock_crossing_data
        #(FromTop, ToTop) weightmemclk_clock_crossing_data_u
            (
             .clka_a2b(fromtop_topclk),
             .clkb_a2b(fromtop_bottomclk),
             .clka_b2a(totop_topclk),
             .clkb_b2a(totop_bottomclk),
             .clka(clk), .clkb(emif_clk), .resetn);

    localparam     FIFO_WIDTH = $bits(Q)+128;
    typedef logic [FIFO_WIDTH-1:0] FifoD;
    fifobus #(.D(FifoD), .Q(FifoD), .DEPTH(DRAM_FIFOS_DEPTH)
              ,.USE_RDWR_CLKS(TRUE)
              )
    to_emif_fifo (.resetn);
    fifobus #(.D(FifoD), .Q(FifoD), .DEPTH(DRAM_FIFOS_DEPTH)
              ,.USE_RDWR_CLKS(TRUE)
              )
    to_top_fifo (.resetn);
    assign to_top_fifo.rdclk = clk;
    assign to_top_fifo.wrclk = emif_clk;
    assign to_emif_fifo.rdclk = emif_clk;
    assign to_emif_fifo.wrclk = clk;

    assign start_top = WAIT_FOR_CAL? totop_topclk.cal_success
                       : start_top_ff;
    assign master.ready = start_top & !to_emif_fifo.half_full;
    logic                          _ready;
    assign _ready = start_top & !to_emif_fifo.full;

    assign to_emif_fifo.wrreq = (master.rdreq | master.wrreq) & _ready;
    `ONOFF__(got_rdreq, (emif_rdreq & to_emif_fifo.q.info.valid), emif.ready,
             1, emif_clk);
    assign to_emif_fifo.rdreq = emif.ready & !to_emif_fifo.empty
                                & dram_q_clk_wrready
                                & ready_for_new_burst
                                & !(emif_rdreq & to_emif_fifo.q.info.valid)
                                    & !got_rdreq;
    logic [$clog2(DEPTH)-1:0]      to_emif_address;
    always_comb begin
        to_emif_address = master.address;
        to_emif_fifo.d.value = { master.d.value,
                                 to_emif_address,
                                 master.rdreq,
                                 master.wrreq,
                                 master.d.info
                                 };
    end
    logic to_emif_rdreq_buf;
    logic to_emif_empty_buf;
    localparam DELAY0 = 0;
    assign to_emif_rdreq_buf = to_emif_fifo.rdreq;
    assign to_emif_empty_buf = emif.ready;
    assign {emif.d.value,
            emif.address,
            emif_rdreq,
            emif_wrreq,
            emif.d.info_master.value
            } = to_emif_fifo.q.value;
    localparam DELAY1 = 0;
    assign to_top_fifo.d.value = {_ammq, emif.q.info};
    assign to_top_fifo.rdreq = !to_top_fifo.empty & start_top;
    logic      master_qvalid;
    assign to_top_fifo.wrreq = '0;
    localparam DELAY2 = 2;
    `REG_(master_qvalid, to_top_fifo.rdreq, 1 + DELAY2, master_valid);
    `IPFIFO(to_emif_fifo);
    `IPFIFO(to_top_fifo);
    assign emif.rdreq = emif_rdreq & reqvalid & emif.ready;
    assign emif.wrreq = emif_wrreq & reqvalid & emif.ready;
    dff_on_off reqvalid_u (.q(reqvalid),
                           .on(to_emif_rdreq_buf),
                           .off(emif.ready),
                           .clk(emif_clk), .resetn);

    dram_emif #(.Q(Q), .D(D), .DEPTH(DEPTH),
                .BURST_COUNT(BURST_COUNT),
                .FAST_COMPILE(FAST_COMPILE)) dram_emif
        (.phy(slave), .amm(emif), .cal_success, .emif_clk,
         .ammq(_ammq), .ready_for_new_burst, .hard_resetn);
endmodule


module dram_emif import globals::*;
    #(type Q=Dram::Q, D=Q,
      integer DEPTH=Dram::DEPTH, BURST_COUNT=1, RANGE=16, FAST_COMPILE=FALSE)
    (emif_phy_bus phy, sprambus amm, output logic cal_success,
     output logic ready_for_new_burst,
     emif_clk, input logic hard_resetn, output Q ammq);
    logic         resetn, clk;
    Q _ammq;
    `REG(ammq, _ammq);
    assign resetn = amm.resetn;
    logic [$clog2(amm.DEPTH)-1:0] address;
    logic [$clog2(BURST_COUNT)-1:0] rd_burst_count;

    logic                           emif_ready;
    logic                           rd_burst_init, rd_burst_en;
    logic                           dram_qvalid;
    Q dram_q;
    logic                           cal_fail;
    assign emif_clk = clk;
    assign rd_burst_en = (amm.rdreq | (rd_burst_count > 0)) & amm.ready;
    assign rd_burst_init = amm.rdreq & amm.ready & (rd_burst_count === 0);

    counter #(.RANGE(BURST_COUNT)) rd_burst_state_u
        (.count(rd_burst_count), .en(rd_burst_en), .clk, .resetn);

    logic                           last_req_was_rdreq;
    `ONOFF(last_req_was_rdreq, amm.rdreq, amm.rdreq);
    `REG(ready_for_new_burst,
         (!last_req_was_rdreq & !amm.rdreq)
         | (rd_burst_count === 0) & !rd_burst_init);

    fifobus #(.Q(Info), .DEPTH(DRAM_FIFOS_DEPTH)) info_fifo(.clk, .resetn);
    `FIFO(info_fifo);
    assign info_fifo.wrreq = rd_burst_en & amm.ready;
    assign info_fifo.rdreq = dram_qvalid;
    always_comb begin
        info_fifo.d.value = '0;
        info_fifo.d.value.valid = amm.d.info.valid;
        if (amm.d.info.valid) begin
            info_fifo.d.value.new_tile_k = amm.d.info.new_tile_k
                                           & rd_burst_init;
        end
    end
    Info _info;
    assign _info = info_fifo.q.value;
    always_comb begin
        amm.q.info_master.value = '0;
        if (info_fifo.q.info.valid) begin
            amm.q.info_master.value = _info;
        end
        amm.q.info_master.value.valid = info_fifo.q.info.valid;
    end
    if (SIM) begin : gemif
        sprambus #(.Q(Q), .DEPTH(DEPTH)) dram(.*);
        assign _ammq = dram.q.value;
        assign dram.d.value = amm.d.value;
        assign dram.wrreq = amm.wrreq;
        assign dram.rdreq = rd_burst_init;
        assign dram.address = amm.address;
        assign dram_qvalid = dram.q.info.valid;
        assign dram_q = dram.q.value;
        assign amm.ready = dram.ready;
        behav_dram #(.BURST_COUNT(BURST_COUNT))
        behav_dram (.io(dram), .pll_ref_clk(phy.pll_ref_clk),
                    .cal_success, .emif_usr_clk(clk), .resetn(resetn));
    end else begin : gemif
        // DDR4 External Memory Infterface IP
        assign amm.ready = emif_ready & cal_success;
        // The ddr_emif_ip lets the ddr memory be controlled from an amm
        //  interface
        if (`DEVICE == "SX") begin
            ddr4
`include  "ddr4_inst.sv"
                end else begin
                    ddr4_gx1150
`include  "ddr4_inst.sv"
                        end
    end
endmodule
