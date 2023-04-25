`include "../top/define.svh"


interface emif_phy_bus
    (
     input wire         pll_ref_clk,
     input wire         oct_rzqin,
     output wire [0:0]  mem_ck,
     output wire [0:0]  mem_ck_n,
     output wire [16:0] mem_a,
     output wire [0:0]  mem_act_n,
     output wire [1:0]  mem_ba,
     output wire [0:0]  mem_bg,
     output wire [0:0]  mem_cke,
     output wire [0:0]  mem_cs_n,
     output wire [0:0]  mem_odt,
     output wire [0:0]  mem_reset_n,
     output wire [0:0]  mem_par,
     input wire [0:0]   mem_alert_n,
     inout wire [8:0]   mem_dqs,
     inout wire [8:0]   mem_dqs_n,
     inout wire [71:0]  mem_dq,
     inout wire [8:0]   mem_dbi_n
     );
    logic               resetn;
endinterface


interface pcie_controller_bus
    (
     input        perstn,
     input        refclk,
     input [7:0]  rx,
     output [7:0] tx,
     output [3:0] led
     );
endinterface


interface signal #(type VALUE=logic)
    (input logic clk, logic resetn);
    VALUE value;
    modport slave (input value, clk, resetn);
    modport master (output value, input clk, resetn);
endinterface


interface signalslave #(type VALUE=logic)
    (input VALUE value);
    modport slave (input value);
endinterface


interface signalmaster #(type VALUE=logic)
    (output VALUE value, input logic clk, logic resetn);
    modport master (output value, input clk, resetn);
endinterface


interface dataslave #(type VALUE=logic, INFO=globals::Info)
    (input VALUE value);
    INFO info;
    logic         clk, resetn;
    signal #(INFO) info_master(.*); assign info = info_master.value;
    signal #(INFO) info_slave(.*); assign info_slave.value = info;
    modport slave (input value);
endinterface


interface datamaster #(type VALUE=logic, INFO=globals::Info)
    (output VALUE value, input logic clk, logic resetn);
    INFO info;
    signal #(INFO) info_master(.*); assign info = info_master.value;
    signal #(INFO) info_slave(.*); assign info_slave.value = info;
    modport master (output value, input clk, resetn);
endinterface


interface data #(type VALUE=logic[7:0][7:0],
                 INFO=globals::Info)
    (input logic clk, logic resetn);
    VALUE value;
    INFO info;
    signal #(INFO) info_slave(.*); assign info_slave.value = info;
    signal #(INFO) info_master(.*); assign info = info_master.value;
endinterface


interface fifobus
    // NOTE: when updating these parameters order or names,
    // must also update `FIFOBUS_CP macro
    #(
      parameter type Q = logic,
      parameter type D = Q,
      parameter type INFO = globals::Info,
      integer   DEPTH = 512,
      USE_RDWR_CLKS = globals::FALSE,
      RDREQ_AS_ACK = globals::FALSE,
      USE_REGS = globals::FALSE,
      WRLATENCY = 1,
      RDLATENCY = 1
      )
    (input logic clk, resetn);
    logic       rdclk, wrclk;
    logic       empty, almost_empty, full;
    logic       rdreq, wrreq;
    logic       half_full;
    logic       rdready, rdready2;
    logic       wrready;
    logic [$clog2(DEPTH)-1:0] rdusedw;
    logic signed [$clog2(DEPTH):0]	rdack;  // for look_ahead_fifobus
    data #(.VALUE(D), .INFO(INFO)) d(.*);
    data #(.VALUE(Q), .INFO(INFO)) q(.*);
    if (!USE_RDWR_CLKS) begin
        assign rdclk = clk;
        assign wrclk = clk;
    end
endinterface


interface pooling_fifo_array_bus
    #(
      parameter I = 2,
      parameter type Q = logic,
      parameter type D = Q,
      parameter type INFO = globals::Info,
      integer   DEPTH = 16,
      USE_RDWR_CLKS = globals::FALSE,
      RDREQ_AS_ACK = globals::TRUE,
      USE_REGS = globals::FALSE,
      WRLATENCY = 1,
      RDLATENCY = 1
      )
    (input logic clk, resetn);
    logic [I-1:0] empty, full;
    logic [I-1:0] rdreq, wrreq;
    logic [I-1:0] half_full;
    logic [I-1:0] rdclk, wrclk;
    localparam    type _INFO = INFO[I-1:0];
    localparam    type _D = D[I-1:0];
    localparam    type _Q = Q[I-1:0];
    data #(.VALUE(_D), .INFO(_INFO)) d(.*);
    data #(.VALUE(_Q), .INFO(_INFO)) q(.*);
    fifobus #(Q, D, INFO, DEPTH, USE_RDWR_CLKS, RDREQ_AS_ACK, USE_REGS,
              WRLATENCY, RDLATENCY) ios[I-1:0](.clk, .resetn);
    if (!USE_RDWR_CLKS) begin
        assign rdclk = clk;
        assign wrclk = clk;
    end
endinterface


interface fifo_array_bus
    #(
      parameter I = 2,
      parameter type Q = logic,
      parameter type D = Q,
      parameter type INFO = globals::Info,
      integer   DEPTH = 16,
      USE_RDWR_CLKS = globals::FALSE,
      RDREQ_AS_ACK = globals::TRUE,
      USE_REGS = globals::FALSE,
      WRLATENCY = 1,
      RDLATENCY = 1,
      type _D = D[I-1:0],
      type _Q = Q[I-1:0],
      type _INFO = INFO[I-1:0]
      )
    (input logic clk, resetn);
    logic [I-1:0] empty, full, almost_empty;
    logic [I-1:0] rdreq, wrreq, rdready, rdready2, wrready;
    logic [I-1:0] half_full;
    logic [I-1:0] rdclk, wrclk;
    data #(.VALUE(_D), .INFO(_INFO)) d(.*);
    data #(.VALUE(_Q), .INFO(_INFO)) q(.*);
    fifobus #(Q, D, INFO, DEPTH, USE_RDWR_CLKS, RDREQ_AS_ACK, USE_REGS,
              WRLATENCY, RDLATENCY) ios[I-1:0](.clk, .resetn);
    if (!USE_RDWR_CLKS) begin
        assign rdclk = clk;
        assign wrclk = clk;
    end
endinterface


interface dpram_array_bus
    #(parameter I = 2,
      parameter type Q = logic,
      parameter type D = Q,
      parameter DEPTH = 16,
      parameter type INFO = globals::Info,
      integer   LATENCY = 1
      )
    (input logic clk, resetn);
    localparam  WIDTH = $bits(D);
k    localparam  type _INFO = INFO[I-1:0];
    localparam  type _D = D[I-1:0];
    localparam  type _Q = Q[I-1:0];
    data #(.VALUE(_D), .INFO(_INFO)) d(.*);
    data #(.VALUE(_Q), .INFO(_INFO)) q(.*);
    logic [I-1:0] rdreq, wrreq, ready;
    logic [I-1:0] reset;
    logic [I-1:0][$clog2(DEPTH)-1:0] wraddress, rdaddress;
    dprambus #(Q, D, DEPTH, INFO, LATENCY) ios[I-1:0](.clk, .resetn);
endinterface


interface slave_arbitrated_fifo_bus import globals::*;
    #(I)
				(fifobus master,
					input logic [$clog2(_TOTAL_LAYERIOMEMS)-1:0] wrsel, rdsel);
    `FIFO_ARRAY_CP(mems, master, I);
    always_comb begin
        master.q.value = mems.q.value[rdsel];
        master.q.info_master.value = mems.q.info[rdsel];
        master.full = mems.full[wrsel];
        master.half_full = mems.half_full[wrsel];
        master.empty = mems.empty[rdsel];
        master.almost_empty = mems.almost_empty[rdsel];
        master.rdready = mems.rdready[rdsel];
        master.rdready2 = mems.rdready2[rdsel];
        master.wrready = mems.wrready[wrsel];
        `FOR(int, J, I) begin
            mems.wrreq[J] = wrsel == J? master.wrreq : '0;
            mems.rdreq[J] = rdsel == J? master.rdreq : '0;
            mems.d.value[J] = wrsel == J? master.d.value : '0;
            mems.d.info_master.value[J] = wrsel == J?
                                          master.d.info_master.value : '0;
        end
    end
endinterface


interface wr_arbitrated_fifo_bus import globals::FALSE; import globals::TRUE; #
    (
     parameter type Q = logic,
     parameter type D = Q,
     parameter type INFO = globals::Info
     )
    // Arbitrate control over 1 slave fifo from 2 master fifo if's
    // where one if reads and writes to the slave and the other if only writes
    (input logic clk, input logic resetn, fifobus slave);
    fifobus #(.D(D), .Q(Q), .INFO(INFO)) writer_reader(.*);
    fifobus #(.D(D), .Q(Q), .INFO(INFO)) writer(.*);
    logic      prioritize_writer;
    assign prioritize_writer = writer.wrreq;
    always_comb begin
        slave.wrreq = prioritize_writer? writer.wrreq : writer_reader.wrreq;
        slave.d.value = prioritize_writer? writer.d.value :
                        writer_reader.d.value;
        slave.rdreq = writer_reader.rdreq;
        writer_reader.q.value = slave.q.value;
        writer_reader.q.info_master.value = slave.q.info;
        writer_reader.full = slave.full;
        writer_reader.half_full = slave.half_full;
        writer_reader.almost_empty = slave.almost_empty;
        writer_reader.empty = slave.empty;
        writer_reader.rdready = slave.rdready;
        writer_reader.rdready2 = slave.rdready2;
        writer.full = slave.full;
        writer.half_full = slave.half_full;
        writer.d.info_master.value = slave.d.info;
    end
endinterface


module wr_arbitrated_fifo_bus2 import globals::FALSE; import globals::TRUE; #
    (
     parameter type Q = logic,
     parameter type D = Q,
     parameter type INFO = globals::Info
     )
    // Arbitrate control over 1 slave fifo from 2 master fifo if's
    // where one if reads and writes to the slave and the other if only writes
    (input logic clk, input logic resetn, fifobus slave, writer_reader,
     writer);
    logic      prioritize_writer;
    assign prioritize_writer = writer.wrreq;
    always_comb begin
        slave.wrreq = prioritize_writer? writer.wrreq : writer_reader.wrreq;
        slave.d.value = prioritize_writer? writer.d.value :
                        writer_reader.d.value;
        slave.rdreq = writer_reader.rdreq;
        writer_reader.q.value = slave.q.value;
        writer_reader.q.info_master.value = slave.q.info;
        writer_reader.full = slave.full;
        writer_reader.half_full = slave.half_full;
        writer_reader.almost_empty = slave.almost_empty;
        writer_reader.empty = slave.empty;
        writer_reader.rdready = slave.rdready;
        writer_reader.rdready2 = slave.rdready2;
        writer.full = slave.full;
        writer.half_full = slave.half_full;
        writer.d.info_master.value = slave.d.info;
    end
endmodule


interface sprambus import globals::*;
    #(parameter type Q = logic,
      parameter type D = Q,
      parameter DEPTH = 16,
      parameter USE_RDWR_ADDRESSES = FALSE,
      parameter type INFO = globals::Info,
      integer   RDLATENCY = 1
      )(input logic clk, resetn);
    // the data type is variable (at synthesis time) and passed as a parameter
    localparam  WIDTH = $bits(D);
    logic [$clog2(DEPTH)-1:0] address;
    logic                     rdreq, wrreq, ready;
    logic [$clog2(DEPTH)-1:0] wraddress, rdaddress;
    if (USE_RDWR_ADDRESSES) begin
        assign address = wrreq? wraddress : rdaddress;
    end
    logic                         reset;
    data #(.VALUE(D), .INFO(INFO)) d(.clk(clk), .resetn);
    data #(.VALUE(Q), .INFO(INFO)) q(.clk(clk), .resetn);
    assign reset = ~resetn;
endinterface


interface dprambus
    #(parameter type Q = logic,
      parameter type D = Q,
      parameter DEPTH = 16,
      parameter type INFO = globals::Info,
      integer   LATENCY = 1
      )
    (input logic clk, resetn);
    localparam  WIDTH = $bits(D);
    logic [$clog2(DEPTH)-1:0] wraddress, rdaddress;
    data #(.VALUE(D), .INFO(INFO)) d(.clk(), .resetn);
    data #(.VALUE(Q), .INFO(INFO)) q(.clk(), .resetn);
    logic                     rdreq, wrreq, ready;
    logic                     reset;
endinterface
