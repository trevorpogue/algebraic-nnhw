`include "../top/define.svh"


module look_ahead_fifo import globals::*;
    (interface io);
    localparam WRLATENCY = io.WRLATENCY;
    localparam RDLATENCY = io.RDLATENCY;
    logic      clk, resetn;
    assign clk = io.clk; assign resetn = io.resetn;
    localparam type IO_D = io.D;
    localparam type _INFO = io.INFO;
    localparam type FIFO_D = logic [$bits(IO_D)+$bits(_INFO)-1:0];
    localparam DEPTH = io.DEPTH;
    localparam DEPTH_OVER_2 = io.DEPTH/2;
    FIFO_D d;
    logic [$bits(FIFO_D)-1:0] mem[DEPTH-1:0];
    typedef logic [$clog2(DEPTH):0] RdWrAddressCompare;
    typedef logic [$clog2(DEPTH)-1:0] RdWrAddress;
    _INFO fifo_info, io_info;
    RdWrAddress          rdack;
    logic                             wrreq, rdreq;
    localparam                        DELAY0 = 0;
    localparam                        DELAY1 = 2;
    RdWrAddress rd_address_d;
    RdWrAddress wr_address_d;
    RdWrAddressCompare rd_address_plus_depth,
        wr_address_plus_inc,
        wr_address_plus_depth;
    dprambus #(.Q(FIFO_D), .INFO(_INFO), .DEPTH(DEPTH)) dpram(.clk, .resetn);
    localparam                        DELAY2 = 0;
    `REG_(io.q.value, dpram.q.value, RDLATENCY-1, ioq);
    `REG_(io.q.info_master.value, io_info, RDLATENCY-1, ioinfo);
    `DPRAM(dpram);
    `REG(rdack, io.rdack, DELAY0);
    `REG(rdreq, io.rdreq, DELAY0);
    `REG_(dpram.wrreq, io.wrreq, WRLATENCY-1, wrreq);
    `REG_(dpram.d.value, {io.d.info, io.d.value}, WRLATENCY-1, d);

    always_ff @(posedge io.clk or negedge io.resetn) if (~io.resetn) begin
        dpram.wraddress <= '0;
        dpram.rdaddress <= '0;
    end else begin
        dpram.wraddress <= wr_address_d;
        dpram.rdaddress <= rd_address_d;
    end

    logic rdreq_buf;
    `REG(rdreq_buf, rdreq & !io.empty, RDLATENCY);
    assign fifo_info = dpram.q.value[$bits(IO_D)+$bits(_INFO)-1:$bits(IO_D)];
    assign io_info.valid = rdreq_buf;
    `ASSIGN_INFO(io_info, fifo_info);

    logic empty_d, full_d, half_full_d;
    `REG2_(io.empty, empty_d, empty, 1, 1);
    `REG2_(io.full, full_d, full, 1, 1);
    `REG2_(io.half_full, half_full_d, half_full, WRLATENCY, 1);

    always_comb begin
        rd_address_d = dpram.rdaddress;
        wr_address_d = dpram.wraddress;
        if (!io.empty)
            rd_address_d = signed'(rd_address_d) + signed'(rdack);
        if (!io.full & dpram.wrreq) wr_address_d += 1;
        // full
        rd_address_plus_depth
            = rd_address_d + (DEPTH * (rd_address_d <= wr_address_d));
        wr_address_plus_inc = (wr_address_d + 1);
        full_d = rd_address_plus_depth <= wr_address_plus_inc;
        half_full_d = rd_address_plus_depth
                      <= wr_address_plus_inc + DEPTH_OVER_2;
        // empty
        empty_d = wr_address_d == rd_address_d;
    end
endmodule
