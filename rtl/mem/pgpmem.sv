`include "../top/define.svh"


module pgpmem import globals::*;
    (sprambus io, data mem_q);
    logic clk, resetn;
    assign clk = io.clk; assign resetn = io.resetn;
    localparam _DEPTH = io.DEPTH;
    localparam DEPTH = _DEPTH/WEIGHTMEM_CLK_DIV;
    localparam BUFDEPTH = 32;
    typedef io.Q Q;
    typedef logic [$clog2(DEPTH)-1:0] Address;
    fifobus #(.Q(Address), .DEPTH(BUFDEPTH)) wraddress_fifo (.clk, .resetn);
    fifobus #(.Q(PGP2), .D(PGP), .DEPTH(BUFDEPTH)) dfifo (.clk, .resetn);
    sprambus #(.Q(PGP2), .DEPTH(DEPTH), .USE_RDWR_ADDRESSES(TRUE)) _io
        (.clk, .resetn);
    `SPRAM(_io)
    `FIFO(dfifo);
    `FIFO(wraddress_fifo);
    logic [$clog2(WEIGHTMEM_CLK_DIV)-1:0] wrparity;
    `COUNTER(wrparity, io.wrreq, io.wrreq & (wrparity == WEIGHTMEM_CLK_DIV-1));
    PGP2 _d;
    Tiler::DIGIT c__io_wrreqs, c__io_rdreqs;
    Tiler::DIGIT c_io_wrreqs, c_io_rdreqs;
    `SIMCOUNTER(c__io_wrreqs, _io.wrreq);
    `SIMCOUNTER(c_io_wrreqs, io.wrreq);
    `SIMCOUNTER(c__io_rdreqs, _io.rdreq);
    `SIMCOUNTER(c_io_rdreqs, io.rdreq);
    assign wraddress_fifo.d.value = io.wraddress>>$clog2(WEIGHTMEM_CLK_DIV);
    assign wraddress_fifo.wrreq = io.wrreq & !wrparity;
    assign wraddress_fifo.rdreq = dfifo.rdreq;
    assign dfifo.d.value = io.d.value;
    assign dfifo.wrreq = io.wrreq;
    assign dfifo.rdreq = !dfifo.empty & !wraddress_fifo.empty;
    assign _io.d.value = _d;
    `WORDSWAP_(_d, _d, dfifo.q.value, 0, clk, $bits(Q));
    assign _io.wrreq = dfifo.q.info.valid;
    assign _io.wraddress = wraddress_fifo.q.value;
    assign _io.rdreq = io.rdreq;
    assign _io.rdaddress = io.rdaddress >> $clog2(WEIGHTMEM_CLK_DIV);
    `REG3(io.q.info_master.value, infoq, io.d.info);
    assign io.ready = !dfifo.half_full
                      & !wraddress_fifo.half_full;
    `ASSIGN_DATA(mem_q, _io.q);
endmodule
