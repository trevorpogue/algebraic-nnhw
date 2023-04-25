`include "../top/define.svh"


module fifo
    // NOTE: DEPTH must be power of 2
    (interface io);
    typedef io.D D;
    typedef io.Q Q;
    localparam DBITS = $bits(D);
    localparam QBITS = $bits(Q);
    localparam Q_GTE_D = QBITS >= DBITS;
    localparam Q_OVER_D_WIDTH = Q_GTE_D? QBITS / DBITS : 1;
    localparam D_OVER_Q_WIDTH = Q_GTE_D? 1 : DBITS / QBITS;
    localparam Q_OVER_D_WIDTH_CLOG2 = $clog2(Q_OVER_D_WIDTH);
    localparam D_OVER_Q_WIDTH_CLOG2 = $clog2(D_OVER_Q_WIDTH);
    localparam Q_OVER_D_WIDTH_POW2 = 1<<Q_OVER_D_WIDTH_CLOG2;
    localparam D_OVER_Q_WIDTH_POW2 = 1<<D_OVER_Q_WIDTH_CLOG2;
    localparam D_OVER_Q_BITSEL = D_OVER_Q_WIDTH_CLOG2>0?
               D_OVER_Q_WIDTH_CLOG2-1:
               D_OVER_Q_WIDTH_CLOG2;
    localparam DEPTH = Q_GTE_D? io.DEPTH*Q_OVER_D_WIDTH_POW2 :
               io.DEPTH*D_OVER_Q_WIDTH_POW2;
    localparam MEM_DEPTH = io.DEPTH;
    localparam DEPTH_OVER_2 = io.DEPTH/2;
    localparam USE_RDWR_CLKS = io.USE_RDWR_CLKS;
    localparam RDREQ_AS_ACK = io.RDREQ_AS_ACK;
    localparam USE_REGS = io.USE_REGS;
    localparam WRLATENCY = io.WRLATENCY;
    localparam RDLATENCY = io.RDLATENCY;
    typedef logic [$clog2(DEPTH)-1:0] RdWrAddress;
    typedef logic [$clog2(DEPTH):0]   RdWrAddressCompare;
    RdWrAddress rd_address;
    RdWrAddressCompare rd_address_plus_depth,
        wr_address_plus_inc,
        wr_address_plus_depth;
    RdWrAddress wr_address;
    RdWrAddress rd_address_d;
    RdWrAddress wr_address_d;
    RdWrAddress wr_address_mod;
    RdWrAddress wr_address_mod_d;
    logic [DBITS-1:0]                 d;
    logic [QBITS-1:0]                 q, _q;
    logic                             clk, resetn;
    assign clk = io.clk; assign resetn = io.resetn;
    localparam                        RDLATENCY_IN = RDLATENCY/2;
    localparam                        RDLATENCY_OUT = (RDLATENCY+1)/2;
    logic                             wrreq, rdreq;
    logic                             empty_d, full_d, half_full_d;
    logic                             almost_empty_d;
    logic                             _full;
    `REG(rdreq, io.rdreq, 0);
    `REG2_(io.empty, empty_d, empty, 1, 1);
    `REG2_(io.almost_empty, almost_empty_d, almost_empty, 1, 1);
    `REG(rd_address, rd_address_d, 1);
    assign io.q.value = _q;
    `REG3(_q, qvalue, q, RDLATENCY-1);
    `REG(d, io.d.value, WRLATENCY-1);
    `REG(wrreq, io.wrreq, WRLATENCY-1);
    `REG(wr_address, wr_address_d, 1);
    `REG(wr_address_mod, wr_address_mod_d, 1);
    `REG2_(io.rdready, '1, rdready);
    `REG2_(io.rdready2, '1, rdready2);
    `REG2_(io.full, full_d, full, WRLATENCY, 1);
    `REG2_(_full, full_d, _full, 1, 1);
    `REG2_(io.half_full, half_full_d, half_full, WRLATENCY, 1);
    if (Q_GTE_D && USE_REGS) begin : g1
        reg [MEM_DEPTH-1:0][Q_OVER_D_WIDTH_POW2-1:0][DBITS-1:0] mem;
    end else if (Q_GTE_D) begin : g1
        reg [0:Q_OVER_D_WIDTH_POW2-1][DBITS-1:0] mem[MEM_DEPTH-1:0];
    end else if (!Q_GTE_D && USE_REGS) begin : g1
        reg [MEM_DEPTH-1:0][D_OVER_Q_WIDTH_POW2-1:0][QBITS-1:0] mem;
    end else begin : g1
        reg [D_OVER_Q_WIDTH_POW2-1:0][QBITS-1:0] mem[MEM_DEPTH-1:0];
    end
    always_ff @(posedge io.rdclk) begin
        if (Q_GTE_D) begin
            if (!RDREQ_AS_ACK) begin
                if (rdreq)
                    q <= g1.mem[rd_address >> Q_OVER_D_WIDTH_CLOG2]
                         [0:Q_OVER_D_WIDTH-1];
            end else begin
                q <= g1.mem[rd_address >> Q_OVER_D_WIDTH_CLOG2]
                     [0:Q_OVER_D_WIDTH-1];
            end
        end else begin
            if (!RDREQ_AS_ACK) begin
                if (rdreq)
                    q <= g1.mem[rd_address >> D_OVER_Q_WIDTH_CLOG2]
                         [rd_address[D_OVER_Q_BITSEL:0]];
            end else
                q <= g1.mem[rd_address >> D_OVER_Q_WIDTH_CLOG2]
                     [rd_address[D_OVER_Q_BITSEL:0]];
        end
    end
    always_ff @(posedge io.wrclk) begin
        if (wrreq)
            if (Q_GTE_D) begin
                g1.mem[wr_address >> Q_OVER_D_WIDTH_CLOG2]
                    [wr_address & Q_OVER_D_WIDTH_POW2-1] <= d;
            end else begin
                g1.mem[wr_address >> D_OVER_Q_WIDTH_CLOG2] <= d;
            end
    end
    always_comb begin
        rd_address_d = rd_address;
        wr_address_d = wr_address;
        wr_address_mod_d = wr_address_mod;
        if (rdreq & !io.empty) rd_address_d += Q_OVER_D_WIDTH_POW2;
        if (wrreq & !_full) wr_address_d += D_OVER_Q_WIDTH_POW2;
        if (wrreq & !_full) wr_address_mod_d += D_OVER_Q_WIDTH_POW2;
        if (Q_GTE_D) begin
            if (wr_address_mod_d >= Q_OVER_D_WIDTH) begin
                wr_address_mod_d = '0;
                wr_address_d += Q_OVER_D_WIDTH_POW2 - Q_OVER_D_WIDTH;
            end
        end else begin
        end
        // full
        rd_address_plus_depth
            = rd_address_d + (DEPTH * (rd_address_d <= wr_address_d));
        wr_address_plus_inc = (wr_address_d + D_OVER_Q_WIDTH_POW2);
        full_d = rd_address_plus_depth <= wr_address_plus_inc;
        // half full
        half_full_d = rd_address_plus_depth
                      <= wr_address_plus_inc + DEPTH_OVER_2;
        // empty
        wr_address_plus_depth
            = wr_address_d + (DEPTH * (wr_address_d < rd_address_d));
        empty_d = wr_address_plus_depth - rd_address_d < Q_OVER_D_WIDTH_POW2;
        almost_empty_d
            = wr_address_plus_depth - rd_address_d < {Q_OVER_D_WIDTH_POW2<<1};
    end
endmodule


module infofifo import globals::*;
    #(string FIFOTYPE = "FIFO") (fifobus io);
    logic clk, resetn;
    assign resetn = io.resetn;
    assign clk = io.clk;
    localparam type _Q = io.Q;
    localparam type _D = io.D;
    localparam type _INFO = io.INFO;
    localparam type D = logic [$bits(_INFO)+$bits(_D)-1:0];
    localparam type Q = logic [$bits(_INFO)+$bits(_Q)-1:0];
    localparam DEPTH = io.DEPTH;
    localparam WRLATENCY = io.WRLATENCY;
    localparam RDLATENCY = io.RDLATENCY;
    localparam RDREQ_AS_ACK = io.RDREQ_AS_ACK;
    localparam USE_REGS = io.USE_REGS;
    localparam USE_RDWR_CLKS = io.USE_RDWR_CLKS;
    fifobus #(Q, D, _INFO, DEPTH, USE_RDWR_CLKS, RDREQ_AS_ACK, USE_REGS,
              WRLATENCY, RDLATENCY) _io(.clk, .resetn);
    _INFO info;
    if (FIFOTYPE == "IPFIFO") begin
        `IPFIFO(_io);
    end else if (FIFOTYPE == "LOOK_AHEAD_FIFO") begin
        look_ahead_fifo look_ahead_fifo(.io(_io));
    end else begin
        `FIFO(_io);
    end
    assign _io.rdreq               = io.rdreq;
    assign _io.rdack               = io.rdack;
    assign _io.wrreq               = io.wrreq;
    assign _io.d.value             = {io.d.info, io.d.value};
    logic      qvalid;
    `REG(qvalid, io.rdreq, RDLATENCY);
    always_comb begin
        info = '0;
        io.q.value                 = '0;
        if (qvalid) begin
            io.q.value                 = _io.q.value;
            info = _io.q.value[$bits(_Q)+$bits(_INFO)-1-:$bits(_INFO)];
            info.valid = qvalid;
        end
    end
    assign io.q.info_master.value = info;
    assign io.empty                   = _io.empty;
    assign io.almost_empty                   = _io.almost_empty;
    assign io.full                    = _io.full;
    assign io.half_full               = _io.half_full;
endmodule


module dpram import globals::*;
    #() (dprambus io);
    logic clk, resetn;
    assign resetn = io.resetn;
    assign clk = io.clk;
    typedef io.D D;
    localparam DEPTH = io.DEPTH;
    logic [$bits(D)-1:0] mem[DEPTH-1:0];
    D q;
    `SHIFT_REG__(io.q.value, q, io.LATENCY-1, ioq);
    assign io.ready = 1'b1;
    always_ff @(posedge io.clk) begin
        if (io.wrreq) mem[io.wraddress] <= io.d.value;
        q <= mem[io.rdaddress];
    end
endmodule


module spram import globals::*;
    #() (sprambus io);
    typedef io.D D;
    localparam USE_RDWR_ADDRESSES = io.USE_RDWR_ADDRESSES;
    localparam DEPTH = io.DEPTH;
    logic      clk, resetn;
    assign resetn = io.resetn;
    assign clk = io.clk;
    logic [$bits(D)-1:0] mem[DEPTH-1:0];
    assign io.ready = 1'b1;
    D q, _q;
    `REG(_q, q, io.RDLATENCY-1);
    assign io.q.value = _q;
    always_ff @(posedge io.clk)
        if (io.wrreq) mem[io.address] <= io.d.value;
        else q <= mem[io.address];
endmodule


module spram_info import globals::*;
    #(ASSIGN_INFO=TRUE) (interface io);
    logic clk, resetn;
    localparam RDLATENCY = io.RDLATENCY;
    assign resetn = io.resetn;
    assign clk = io.clk;
    if (ASSIGN_INFO) begin
        typedef io.INFO INFO_;
        INFO_ info;
        `always_ff @(posedge clk or negedge resetn) if (~resetn) begin
            info <= '0;
        end else begin
            if (io.rdreq) begin
                info <= io.d.info;
            end else begin
                info <= '0;
            end
            info.valid <= (io.rdreq);
        end
        `SHIFT_REG__(io.q.info_master.value, info, RDLATENCY-1, io_info);
    end
endmodule


module fifo_info import globals::*;
    #(ASSIGN_INFO=TRUE) (interface io);
    logic clk, resetn;
    localparam RDLATENCY = io.RDLATENCY;
    assign resetn = io.resetn;
    localparam USE_RDWR_CLKS = io.USE_RDWR_CLKS;
    if (USE_RDWR_CLKS) begin
        assign clk = io.rdclk;
    end else begin
        assign clk = io.clk;
    end
    if (ASSIGN_INFO) begin
        typedef io.INFO INFO_;
        INFO_ info;
        `always_ff @(posedge clk or negedge resetn) if (~resetn) begin
            info <= '0;
        end else begin
            if (io.rdreq & ~io.empty) begin
                info <= io.d.info;
            end else begin
                info <= '0;
            end
            info.valid <= (io.rdreq & ~io.empty);
        end
        `SHIFT_REG__(io.q.info_master.value, info, RDLATENCY-1, io_info);
    end
endmodule


module fifobus_delay import globals::*;
    #(ASSIGN_INFO=TRUE)
    (fifobus io);

endmodule


module fmaxfifo import globals::*;
    #(ASSIGN_INFO=TRUE)
    (fifobus io);
    logic clk, resetn;
    assign clk = io.clk; assign resetn = io.resetn;
    localparam type Q = io.Q;
    localparam type D = io.D;
    localparam type INFO = io.INFO;
    localparam DEPTH = io.DEPTH;
    localparam RDREQ_AS_ACK = io.RDREQ_AS_ACK;
    fifobus #(.Q(Q), .D(D), .INFO(INFO)
              ,.DEPTH(DEPTH)
              ,.RDREQ_AS_ACK(RDREQ_AS_ACK)
              ,.USE_RDWR_CLKS(TRUE)
              ) d(.*);
    fifobus #(.Q(Q), .D(D), .INFO(INFO)
              ,.DEPTH(1)
              ,.RDREQ_AS_ACK(RDREQ_AS_ACK)
              ,.USE_RDWR_CLKS(TRUE)
              ) q(.*);
    `IPFIFO(d, FALSE);
    logic      dqvalid;
    `REG_(dqvalid, d.rdreq, 1, dqvalid);
    `IPFIFO(q, ASSIGN_INFO);
    assign d.rdreq = ~d.empty & ~q.full;
    assign q.wrreq = dqvalid;
    assign q.d.value = d.q.value;

    always_comb begin
        d.rdclk = clk;
        d.wrclk = clk;
        q.rdclk = clk;
        q.wrclk = clk;
        d.wrreq = io.wrreq;
        d.d.value = io.d.value;
        io.full = d.full;
        io.half_full = d.half_full;
        q.rdreq = io.rdreq;
        io.q.value = q.q.value;
        if (ASSIGN_INFO)
            io.q.info_master.value = q.q.info;
        io.empty = q.empty;
    end
endmodule

module _fifo_dgtq_faster_rdclk import globals::*;
    // use when $bits(d) > bits(q) and rdclk is faster than wrclk
    #(ASSIGN_INFO=TRUE)
    (fifobus io);
    logic rdclk, wrclk, resetn;
    assign rdclk = io.rdclk; assign wrclk = io.wrclk;
    assign resetn = io.resetn;
    localparam DEPTH = io.DEPTH;
    if (0 && ($bits(io.D) == 1024) && ($bits(io.Q) == 512)) begin
        logic [$clog2(DEPTH)-1:0] wrusedw;
        `REG2_(io.half_full, wrusedw >= {(DEPTH)>>1},
               io_half_full, 1, 1, io.wrclk, resetn);
        `REG2_(io.almost_empty, io.rdusedw < 2,
               io_almost_empty, 0, 1, io.rdclk, resetn);
        `REG3(io.rdready, rdready, '1, 1, io.rdclk, 0, resetn);
        `REG3(io.rdready2, rdready2, '1, 1, io.rdclk, 0, resetn);
        fifo_dgtq_faster_rdclk_8b fifo_u
            (
             .data    (io.d.value),
             .q       (io.q.value),
             .wrreq   (io.wrreq),
             .rdreq   (io.rdreq),
             .rdempty (io.empty),
             .wrfull  (io.full),
             .wrclk   (io.wrclk),
             .rdclk   (io.rdclk),
             .wrusedw   (wrusedw),
             .rdusedw   (io.rdusedw)
             );
    end else if (($bits(io.D) == 2048) && ($bits(io.Q) == 1024)) begin
        logic [$clog2(DEPTH)-1:0] wrusedw;
        `REG2_(io.half_full, wrusedw >= {(DEPTH)>>1},
               io_half_full, 1, 1, io.wrclk, resetn);
        `REG2_(io.almost_empty, io.rdusedw < 2,
               io_almost_empty, 0, 1, io.rdclk, resetn);
        `REG3(io.rdready, rdready, '1, 1, io.rdclk, 0, resetn);
        `REG3(io.rdready2, rdready2, '1, 1, io.rdclk, 0, resetn);
        fifo_dgtq_faster_rdclk_16b fifo_u
            (
             .data    (io.d.value),
             .q       (io.q.value),
             .wrreq   (io.wrreq),
             .rdreq   (io.rdreq),
             .rdempty (io.empty),
             .wrfull  (io.full),
             .wrclk   (io.wrclk),
             .rdclk   (io.rdclk),
             .wrusedw   (wrusedw),
             .rdusedw   (io.rdusedw)
             );
    end else begin
        __fifo_dgtq_faster_rdclk #(ASSIGN_INFO) fifo_u(io);
    end
endmodule


module __fifo_dgtq_faster_rdclk import globals::*;
    // use when $bits(d) > bits(q) and rdclk is faster than wrclk
    #(ASSIGN_INFO=TRUE)
    (fifobus io);
    logic rdclk, wrclk, resetn;
    assign rdclk = io.rdclk; assign wrclk = io.wrclk;
    assign resetn = io.resetn;
    localparam type Q = io.Q;
    localparam type D = io.D;
    localparam type INFO = io.INFO;
    localparam DEPTH = io.DEPTH;
    localparam RDREQ_AS_ACK = io.RDREQ_AS_ACK;
    localparam RDLATENCY = io.RDLATENCY;
    localparam WRLATENCY = io.WRLATENCY;
    fifobus #(.Q(D), .D(D), .INFO(INFO)
              ,.DEPTH(DEPTH)
              ,.RDREQ_AS_ACK(RDREQ_AS_ACK)
              ,.USE_RDWR_CLKS(TRUE)
              ) d(.clk(wrclk), .resetn);
    fifobus #(.Q(Q), .D(D), .INFO(INFO)
              ,.DEPTH(DEPTH)
              ,.RDLATENCY(RDLATENCY)
              ,.WRLATENCY(WRLATENCY)
              ,.RDREQ_AS_ACK(RDREQ_AS_ACK)
              ) q(.clk(rdclk), .resetn);
    `IPFIFO(d, FALSE);
    logic      dqvalid;
    `REG_(dqvalid, d.rdreq, 1, dqvalid, rdclk);
    `FIFO(q, ASSIGN_INFO);
    assign d.rdreq = ~d.empty & ~q.full;
    assign q.wrreq = dqvalid;
    assign q.d.value = d.q.value;

    always_comb begin
        d.rdclk = rdclk;
        d.wrclk = wrclk;
        d.wrreq = io.wrreq;
        d.d.value = io.d.value;
        io.full = d.full;
        io.half_full = d.half_full;
        q.rdreq = io.rdreq;
        io.q.value = q.q.value;
        if (ASSIGN_INFO)
            io.q.info_master.value = q.q.info;
        io.empty = q.empty;
        io.almost_empty = q.almost_empty;
    end
endmodule


`define FIFOPAD_REG0(signal, clk) \
`REG3(padded_slave.signal, signal, master.signal, DELAY, clk);
`define FIFOPAD_REG1(signal, clk) \
`REG3(master.signal, signal, padded_slave.signal, DELAY, clk);

module fifopad import globals::*;
    // add extra registers between fifo IOs
    #(DELAY = FMAX_DELAY, ASSIGN_DINFO=TRUE, ASSIGN_QINFO=TRUE)
    (fifobus padded_slave, master);
    logic rdclk; assign rdclk = master.rdclk;
    logic wrclk; assign wrclk = master.wrclk;
    logic resetn; assign resetn = master.resetn;
    if (ASSIGN_DINFO) begin
        `REG3(master.d.info_master.value, dinfo, padded_slave.d.info, DELAY, wrclk);
    end
    if (ASSIGN_QINFO) begin
        `REG3(padded_slave.q.info_master.value, q_info, master.q.info, DELAY, rdclk);
    end
    `REG3(master.d.value, d, padded_slave.d.value, DELAY, wrclk);
    `REG3(padded_slave.q.value, q, master.q.value, DELAY, rdclk);
    `FIFOPAD_REG1(rdreq, rdclk);
    `FIFOPAD_REG0(rdready, rdclk);
    `FIFOPAD_REG0(rdready2, rdclk);
    `FIFOPAD_REG0(rdusedw, rdclk);
    `FIFOPAD_REG0(empty, rdclk);
    `FIFOPAD_REG0(almost_empty, rdclk);
    `FIFOPAD_REG1(wrreq, wrclk);
    `FIFOPAD_REG0(full, wrclk);
    `FIFOPAD_REG0(half_full, wrclk);
endmodule
