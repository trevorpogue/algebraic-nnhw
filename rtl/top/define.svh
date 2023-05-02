`ifndef __DEFINE_SVH__
`define __DEFINE_SVH__
`include "../top/utils.svh"
`include "../top/utils2.svh"

`define always_ff always_ff  // fixes auto-indent bug in emacs verilog-mode
`define always_comb always_comb  // fixes auto-indent bug in emacs verilog-mode
`define always_ff2 always_ff @(posedge clk or negedge resetn)
`define USE_RESULT_FIFOS_FULL 0
`define logic logic signed

`ifndef IMPORT_TOP
`define IMPORT_TOP \
// integer FIP_METHOD = globals::BASELINE, \
// integer FIP_METHOD = globals::FIP, \
integer FIP_METHOD = globals::FFIP, \
SZI = 64, \
SZJ = SZI, \
UNUSED0 = 0, \
UNUSED1 = 0, \
LAYERIO_WIDTH = 8, \
WEIGHT_WIDTH = LAYERIO_WIDTH, \
LAYERIO_SIGNED = globals::TRUE, \
WEIGHT_SIGNED = globals::TRUE, \
ACCUM_WIDTH = LAYERIO_WIDTH > 8? 44 : 28, \
CHAIN_WIDTH = FIP_METHOD == globals::BASELINE? \
LAYERIO_WIDTH + WEIGHT_WIDTH + $clog2(SZJ): \
LAYERIO_WIDTH + WEIGHT_WIDTH + $clog2(SZJ) + 1, \
LAYERIOMEM_SIZE = 0, \
MEM_MODULE= 0, \
MEM_ID= 0, \
TOP_SZJ = SZJ, \
\
D_MINUS_1 = (LAYERIO_SIGNED ^ WEIGHT_SIGNED), \
TOTAL_LAYERIOMEMS = 3, \
LAYERIOMEM0_SIZE = 1<<23, \
LAYERIOMEM1_SIZE = 1<<21, \
LAYERIOMEM2_SIZE = 1<<10, \
LAYERIOMEM0_SZJ = TOP_SZJ, \
LAYERIOMEM1_SZJ = TOP_SZJ, \
LAYERIOMEM2_SZJ = TOP_SZJ, \
// the constant 7 below is due to fifo wr speed in gemm_u: \
MIN_TILE_SIZE_N = (SZI + {SZI>>1} - 1) <= 7? 7 : SZI + {SZI>>1} - 1, \
integer  LAYERIOMEMS_SZJ[TOTAL_LAYERIOMEMS-1:0] = {LAYERIOMEM2_SZJ, LAYERIOMEM1_SZJ, LAYERIOMEM0_SZJ}, \
integer LAYERIOMEMS_SIZE[TOTAL_LAYERIOMEMS-1:0] = {LAYERIOMEM2_SIZE, LAYERIOMEM1_SIZE, LAYERIOMEM0_SIZE}, \
integer USE_SOFT_RESET = globals::TRUE, \
PGP_MEM_SIZE = 1<<22, \
RECORD_PERF_RESULTS = globals::TRUE, \
string RESULT_IO = "RESULT", \
integer RESULT_FIFOS_DEPTH = 1<<9, \
USE_RESULT_FIFOS = globals::FALSE, \
USE_RESULT_FIFOS_FULL = `USE_RESULT_FIFOS_FULL, \
LAYERIOMEM_DEPTH = $ceil(LAYERIOMEM_SIZE/(LAYERIO_WIDTH * TOP_SZJ)), \
type Layeriovec = logic [SZJ-1:0][LAYERIO_WIDTH-1:0], \
type TopLayeriovec = logic [TOP_SZJ-1:0][LAYERIO_WIDTH-1:0], \
Layeriovec0 = logic [LAYERIOMEM0_SZJ-1:0][LAYERIO_WIDTH-1:0], \
Layeriovec1 = logic [LAYERIOMEM1_SZJ-1:0][LAYERIO_WIDTH-1:0], \
Layeriovec2 = logic [LAYERIOMEM2_SZJ-1:0][LAYERIO_WIDTH-1:0], \
Weightvec = logic [SZJ-1:0][WEIGHT_WIDTH-1:0], \
integer FAST_COMPILE = globals::FALSE, \
BURST_COUNT = SZI, \
ADD_DELAY = 1, \
DUMMY = 0
`endif

`define DEVICE "SX"

`define EXPORT_TOP FIP_METHOD, SZI, SZJ, UNUSED0, UNUSED1, \
LAYERIO_WIDTH, WEIGHT_WIDTH, LAYERIO_SIGNED, WEIGHT_SIGNED, ACCUM_WIDTH, CHAIN_WIDTH, LAYERIOMEM_SIZE, MEM_MODULE, MEM_ID, TOP_SZJ

`define EXPORT_TOP_(FIP_METHOD=FIP_METHOD, SZI=SZI, SZJ=SZJ, UNUSED0=0, UNSUSED1=0, LAYERIO_WIDTH=LAYERIO_WIDTH, WEIGHT_WIDTH=WEIGHT_WIDTH, LAYERIO_SIGNED=LAYERIO_SIGNED, WEIGHT_SIGNED=WEIGHT_SIGNED, ACCUM_WIDTH=ACCUM_WIDTH, CHAIN_WIDTH=CHAIN_WIDTH, LAYERIOMEM_SIZE=LAYERIOMEM_SIZE, MEM_MODULE=MEM_MODULE, MEM_ID=MEM_ID, TOP_SZJ=SZJ) \
FIP_METHOD, SZI, SZJ, UNUSED0, UNUSED1, LAYERIO_WIDTH, WEIGHT_WIDTH, LAYERIO_SIGNED, WEIGHT_SIGNED, ACCUM_WIDTH, CHAIN_WIDTH, LAYERIOMEM_SIZE, MEM_MODULE, MEM_ID, TOP_SZJ

`define IMPORT_ARITH \
`IMPORT_TOP, \
integer SZI_FIP = FIP_METHOD > BASELINE? SZI+1 : SZI, \
PE_INPUT_DEPTH = FIP_METHOD > BASELINE? 4 : 2, \
SZJ_PE = SZJ/PE_INPUT_DEPTH, \
integer A_WIDTH = LAYERIO_WIDTH, \
B_WIDTH = WEIGHT_WIDTH, \
A_SIGNED = LAYERIO_SIGNED, \
B_SIGNED = WEIGHT_SIGNED, \
C_WIDTH = ACCUM_WIDTH, \
AMAT_WIDTH = FIP_METHOD == FFIP? A_WIDTH + 1 + D_MINUS_1 : A_WIDTH, \
BMAT_WIDTH = B_WIDTH + (FIP_METHOD == FFIP), \
type Enjvec = logic [SZJ-1:0], \
type Aivec = logic [SZI-1:0][A_WIDTH-1:0], \
type Ajvec = logic [SZJ-1:0][A_WIDTH-1:0], \
type Bivec = logic [SZI-1:0][B_WIDTH-1:0], \
type Bjvec = logic [SZJ-1:0][B_WIDTH-1:0], \
type Civec = logic [SZI-1:0][C_WIDTH-1:0], \
type Chainivec = logic [SZI-1:0][CHAIN_WIDTH-1:0], \
type Chainjvec = logic [SZJ-1:0][CHAIN_WIDTH-1:0], \
type MacIVec = logic [SZI-1:0][ACCUM_WIDTH-1:0], \
type MacJVec = logic [SZJ-1:0][ACCUM_WIDTH-1:0], \
type Cjvec = logic [SZJ-1:0][C_WIDTH-1:0], \
type A = logic [A_WIDTH-1:0],\
type B = logic [B_WIDTH-1:0],\
type C = logic signed [C_WIDTH-1:0], \
type AMatIvec = logic [SZI-1:0][AMAT_WIDTH-1:0], \
type AMatJvec = logic [SZJ-1:0][AMAT_WIDTH-1:0], \
type BMatIvec = logic [SZI-1:0][BMAT_WIDTH-1:0], \
type BMatJvec = logic [SZJ-1:0][BMAT_WIDTH-1:0], \
type AJIMatrix = AMatIvec[SZJ-1:0], \
type AIJMatrix = AMatJvec[SZI-1:0], \
type BJIMatrix = BMatIvec[SZJ-1:0], \
type BIJMatrix = BMatJvec[SZI-1:0], \
integer X_WIDTH = A_WIDTH + D_MINUS_1 + (FIP_METHOD != BASELINE), \
integer Y_WIDTH = X_WIDTH, \
RESAB_WIDTH = FIP_METHOD == BASELINE? A_WIDTH + B_WIDTH : \
X_WIDTH + Y_WIDTH, \
type X = `logic [X_WIDTH-1:0], \
type Y = `logic [Y_WIDTH-1:0], \
type Chain = logic [CHAIN_WIDTH-1:0], \
type PeA = `logic [PE_INPUT_DEPTH-1:0][AMAT_WIDTH-1:0], \
type PeB = `logic [PE_INPUT_DEPTH-1:0][BMAT_WIDTH-1:0], \
type AlphaJVec = logic [SZJ_PE-1:0][PE_INPUT_DEPTH-1:0][A_WIDTH-1:0], \
integer _DUMMY=0
//
`define EXPORT_ARITH `EXPORT_TOP

`define in(STATE) (state == STATE)
`define to(STATE) (next_state == STATE)

// utilities
`define SIGNED(ASSIGNMENT, BOOL, signal)\
if (BOOL) ASSIGNMENT signed'(signal);\
else ASSIGNMENT signal;
`define SGNED(ASSIGNMENT, signal)\
if (B_SIGNED) ASSIGNMENT signed'(signal);\
else ASSIGNMENT signal;
`define VEC(DEPTH, WIDTH) logic [DEPTH-1:0][WIDTH-1:0]
`define VECS(CNT, DEPTH, WIDTH) logic [CNT-1:0][DEPTH-1:0][WIDTH-1:0]
`define VEC0TYPE logic [DEPTH-1:0][WIDTH-1:0]
`define EXTND(d, width) {width{d}}
`define FOR(ITYPE, I, TOTAL) for (ITYPE I = 0; I != TOTAL; I++)
`define FOR(ITYPE, I, TOTAL) for (ITYPE I = 0; I != TOTAL; I++)

`define FIFO(fifobus, ASSIGN_INFO=globals::TRUE, fifo_module=fifo ) \
    fifo_module fifobus``_fifo_u (.io(fifobus)); \
    fifo_info #(ASSIGN_INFO) fifobus``_fifo_info_u (.io(fifobus));

`define INFOFIFO(fifobus, FIFOTYPE="FIFO") \
    infofifo #(FIFOTYPE) fifobus``_fifo_u(fifobus);
`define FMAXFIFO(fifobus, ASSIGN_INFO=TRUE ) \
    fmaxfifo fifobus``_fifo_u(fifobus);

`define IPFIFO__(fifobus, ASSIGN_INFO=globals::TRUE, fifo_module=fifo, nmspc, ip_module, resetn) \
if (!USE_FIFO_IP) begin \
    fifo_module nmspc``_u (.io(fifobus)); \
    fifo_info #(ASSIGN_INFO) nmspc``_info_u (.io(fifobus)); \
end else begin \
    localparam nmspc``_DEPTH = fifobus.DEPTH; \
    logic [$clog2(nmspc``_DEPTH)-1:0] nmspc``_wrusedw; \
    `REG2_(fifobus.half_full, nmspc``_wrusedw >= {(nmspc``_DEPTH)>>1}, \
           fifobus_half_full, 1, 1, fifobus.wrclk, resetn); \
    `REG2_(fifobus.almost_empty, fifobus.rdusedw < 2, \
           fifobus_almost_empty, 0, 1, fifobus.rdclk, resetn); \
    `REG3(fifobus.rdready, rdready, '1, 1, fifobus.rdclk, 0, resetn); \
    `REG3(fifobus.rdready2, rdready2, '1, 1, fifobus.rdclk, 0, resetn); \
    ip_module nmspc``_fifo_u \
        (\
         .data    (fifobus.d.value), \
         .q       (fifobus.q.value), \
         .wrreq   (fifobus.wrreq), \
         .rdreq   (fifobus.rdreq), \
         .rdempty (fifobus.empty), \
         .wrfull  (fifobus.full), \
         .wrclk   (fifobus.wrclk), \
         .rdclk   (fifobus.rdclk), \
         .wrusedw   (nmspc``_wrusedw), \
         .rdusedw   (fifobus.rdusedw), \
         .aclr(~resetn) \
         ); \
         fifo_info #(ASSIGN_INFO) nmspc``_info_u (.io(fifobus)); \
end
`define IPFIFO_1CLK(fifobus, ASSIGN_INFO=globals::TRUE, fifo_module=fifo, ip_module=fifo_1clk) \
if (!USE_FIFO_IP) begin \
    fifo_module nmspc``_u (.io(fifobus)); \
    fifo_info #(ASSIGN_INFO) nmspc``_info_u (.io(fifobus)); \
end else begin \
    localparam nmspc``_DEPTH = fifobus.DEPTH; \
    logic [$clog2(nmspc``_DEPTH)-1:0] nmspc``_wrusedw; \
    `REG2_(fifobus.half_full, nmspc``_wrusedw >= {(nmspc``_DEPTH)>>1}, \
           fifobus_half_full, 1, 1, fifobus.wrclk, fifobus.resetn); \
    `REG2_(fifobus.almost_empty, fifobus.rdusedw < 2, \
           fifobus_almost_empty, 0, 1, fifobus.rdclk, fifobus.resetn); \
    `REG3(fifobus.rdready, rdready, '1, 1, fifobus.rdclk, 0, fifobus.resetn); \
    `REG3(fifobus.rdready2, rdready2, '1, 1, fifobus.rdclk, 0, fifobus.resetn); \
    ip_module nmspc``_fifo_u \
        (\
         .data    (fifobus.d.value), \
         .q       (fifobus.q.value), \
         .wrreq   (fifobus.wrreq), \
         .rdreq   (fifobus.rdreq), \
         .empty (fifobus.empty), \
         .full  (fifobus.full), \
         .clock   (fifobus.clk), \
         .aclr(~fifobus.resetn) \
         ); \
         fifo_info #(ASSIGN_INFO) nmspc``_info_u (.io(fifobus)); \
end

`define IPFIFO___(fifobus, nmspc, ASSIGN_INFO=globals::TRUE, fifo_module=fifo, resetn)\
if (fifobus.DEPTH <= 512) begin \
    `IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo512, resetn);\
end else if (fifobus.DEPTH <= 1024) begin \
    `IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo1024, resetn)\
end else if (fifobus.DEPTH <= 2048) begin \
    `IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo2048, resetn);\
end else if (fifobus.DEPTH <= 4096) begin \
    `IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo4096, resetn);\
end else if (fifobus.DEPTH <= 8192) begin \
    `IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo8192, resetn);\
end else if (fifobus.DEPTH <= 16384) begin \
    `IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo16384, resetn);\
end else if (fifobus.DEPTH <= 32768) begin \
    `IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo32768, resetn);\
end else if (fifobus.DEPTH <= 65536) begin \
    `IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo65536, resetn);\
end

`define IPFIFO_(fifobus, nmspc, ASSIGN_INFO=globals::TRUE, fifo_module=fifo)\
`IPFIFO___(fifobus, nmspc, ASSIGN_INFO, fifo_module, fifobus.resetn)

`define IPFIFO_MAX(fifobus, nmspc, ASSIGN_INFO=globals::TRUE)\
`IPFIFO__(fifobus, ASSIGN_INFO, fifo_module, nmspc, dram_fifo17, fifobus.resetn);

`define IPFIFO(fifobus, ASSIGN_INFO=globals::TRUE, fifo_module=fifo) \
`IPFIFO_(fifobus, fifobus, ASSIGN_INFO, fifo_module)\

`define DPRAM_RDWR_CLKS(io, nmspc=io, module_name, rdclk, wrclk) \
module_name nmspc``_dpram_u \
        ( \
         .q(io.q.value), \
         .data(io.d.value), \
         .rdaddress({32'd0, io.rdaddress}), \
         .wraddress({32'd0, io.wraddress}), \
         .wren(io.wrreq), \
          .rdclock(rdclk), \
          .wrclock(wrclk) \
         ); \
    assign io.ready = 1'b1;

`define IPDPRAM(io, nmspc=io, module_name) `DPRAM_RDWR_CLKS(io, nmspc, module_name, io.clk, io.clk)
`define DPRAM(io_, nmspc=io_) dpram nmspc``_dpram_u(.io(io_));
`define SPRAM(io, nmspc=io) spram nmspc``_spram_u(io); \
spram_info nmspc``_spram_info_u(io);

`define LAYERIOMEM_INSTRUC_FIFOBUS(fifo_name)\
fifo_array_bus#(.I(TOTAL_LAYERIOMEMS), \
                .Q(Tiler::DIGIT), .DEPTH(INSTRUC_FIFOS_DEPTH), \
              .USE_RDWR_CLKS(TRUE)) fifo_name(.clk, .resetn); \
    assign fifo_name.wrclk = instruc_clk; \
    assign fifo_name.rdclk = layeriomem_clk;

`define WEIGHTMEM_INSTRUC_FIFOBUS(fifo_name)\
fifobus #(.Q(Tiler::DIGIT), .DEPTH(INSTRUC_FIFOS_DEPTH), \
          .USE_RDWR_CLKS(TRUE)) fifo_name(.clk, .resetn); \
assign fifo_name.wrclk = instruc_clk; \
assign fifo_name.rdclk = weightmem_clk;

`define INSTRUC_FIFOBUS(fifo_name, Q_)\
    fifobus #(.Q(Q_), .DEPTH(INSTRUC_FIFOS_DEPTH), \
              .USE_RDWR_CLKS(TRUE)) fifo_name(.clk, .resetn); \
assign fifo_name.wrclk = clk; \
assign fifo_name.rdclk = clk;

`define INSTRUC_FIFOBUS_QD(fifo_name, Q_, D_)\
    fifobus #(.Q(Q_), .D(D_), .DEPTH(INSTRUC_FIFOS_DEPTH) \
              ) fifo_name (.clk, .resetn); \

`define DATA(type, name) data #(type) name(.clk, .resetn);
`define ASSIGN_DATA(q, d, pre_op=assign) \
pre_op q.value = d.value; pre_op q.info_master.value = d.info;

// TAG:UPDATE_INFO
`define _INIT_INFO(q, op, pre_op= ;) \
    pre_op q.last_elm op '0; \
        pre_op q.last_tile_n_elm op '0; \
        pre_op q.last_w op '0; \
        pre_op q.new_tile_k op '0; \
        pre_op q.last_tile_k op '0; \
        pre_op q.first_tile_k op '0;

// TAG:UPDATE_INFO
`define _SET_INFO(q, op, d, pre_op= ;) \
    pre_op q.last_elm op d.last_elm; \
        pre_op q.last_tile_n_elm op d.last_tile_n_elm; \
        pre_op q.last_w op d.last_w; \
        pre_op q.new_tile_k op d.new_tile_k; \
        pre_op q.last_tile_k op d.last_tile_k; \
        pre_op q.first_tile_k op d.first_tile_k;

`define INIT_INFO_FF(q) `_INIT_INFO(q, <=);
`define INIT_INFO(q) `_INIT_INFO(q, =);
`define ASSIGN_INFO_FF(q, d) `_SET_INFO(q, <=, d);
`define ASSIGN_INFO(q, d) `_SET_INFO(q, =, d, assign);
`define SET_INFO(q, d) `_SET_INFO(q, =, d);

`define FIFOBUS_CP(fifobus_cp, original_fifobus) \
    localparam type fifobus_cp``_Q = original_fifobus.Q; \
    localparam type fifobus_cp``_D = original_fifobus.D; \
    localparam type fifobus_cp``_INFO = original_fifobus.INFO; \
localparam fifobus_cp``_DEPTH = original_fifobus.DEPTH; \
localparam fifobus_cp``_USE_RDWR_CLKS = original_fifobus.USE_RDWR_CLKS; \
localparam fifobus_cp``_RDREQ_AS_ACK = original_fifobus.RDREQ_AS_ACK; \
localparam fifobus_cp``_USE_REGS = original_fifobus.USE_REGS; \
localparam fifobus_cp``_WRLATENCY = original_fifobus.WRLATENCY; \
localparam fifobus_cp``_RDLATENCY = original_fifobus.RDLATENCY; \
fifobus #(.Q(fifobus_cp``_Q), \
          .D(fifobus_cp``_D), \
          .INFO(fifobus_cp``_INFO), \
          .DEPTH(fifobus_cp``_DEPTH), \
          .USE_RDWR_CLKS(fifobus_cp``_USE_RDWR_CLKS), \
          .RDREQ_AS_ACK(fifobus_cp``_RDREQ_AS_ACK), \
          .USE_REGS(fifobus_cp``_USE_REGS), \
          .WRLATENCY(fifobus_cp``_WRLATENCY), \
          .RDLATENCY(fifobus_cp``_RDLATENCY)) \
fifobus_cp(.clk(original_fifobus.clk), .resetn(original_fifobus.resetn)); \
if (original_fifobus.USE_RDWR_CLKS) begin \
    assign fifobus_cp.rdclk = original_fifobus.rdclk; \
    assign fifobus_cp.wrclk = original_fifobus.wrclk; \
end

`define FIFO_ARRAY_CP(fifobus_cp, original_fifobus, TOTAL) \
    localparam type fifobus_cp``_Q = original_fifobus.Q; \
    localparam type fifobus_cp``_D = original_fifobus.D; \
    localparam type fifobus_cp``_INFO = original_fifobus.INFO; \
localparam fifobus_cp``_DEPTH = original_fifobus.DEPTH; \
localparam fifobus_cp``_USE_RDWR_CLKS = original_fifobus.USE_RDWR_CLKS; \
localparam fifobus_cp``_RDREQ_AS_ACK = original_fifobus.RDREQ_AS_ACK; \
localparam fifobus_cp``_USE_REGS = original_fifobus.USE_REGS; \
localparam fifobus_cp``_WRLATENCY = original_fifobus.WRLATENCY; \
localparam fifobus_cp``_RDLATENCY = original_fifobus.RDLATENCY; \
fifo_array_bus #(.I(I), .Q(fifobus_cp``_Q), \
          .D(fifobus_cp``_D), \
          .INFO(fifobus_cp``_INFO), \
          .DEPTH(fifobus_cp``_DEPTH), \
          .USE_RDWR_CLKS(fifobus_cp``_USE_RDWR_CLKS), \
          .RDREQ_AS_ACK(fifobus_cp``_RDREQ_AS_ACK), \
          .USE_REGS(fifobus_cp``_USE_REGS), \
          .WRLATENCY(fifobus_cp``_WRLATENCY), \
          .RDLATENCY(fifobus_cp``_RDLATENCY)) \
fifobus_cp(.clk(original_fifobus.clk), .resetn(original_fifobus.resetn)); \
if (original_fifobus.USE_RDWR_CLKS) begin \
    assign fifobus_cp.rdclk = original_fifobus.rdclk; \
    assign fifobus_cp.wrclk = original_fifobus.wrclk; \
    `FOR(genvar, I, fifobus_cp.I) begin\
        assign fifobus_cp.ios[I].rdclk = fifobus_cp.rdclk;\
        assign fifobus_cp.ios[I].wrclk = fifobus_cp.wrclk;\
    end\
end

`define CONNECT_FIFOS3(writer, reader, clk_=clk, DELAY=1) \
`REG2_(reader.rdreq, ~reader.empty & ~writer.half_full, reader``_rdreq, \
       DELAY, 0, clk_, hard_resetn); \
`REG2_(writer.wrreq, reader.q.info.valid, writer``_wrreq, \
       DELAY, 0, clk_, hard_resetn); \
`REG2_(writer.d.value, reader.q.value, writer``_d, \
       DELAY, 0, clk_, hard_resetn);

`define CONNECT_FIFOS2(writer, reader, clk_=clk, DELAY=9) \
`REG2_(reader.rdreq, ~reader.empty & ~writer.half_full, reader``_rdreq, \
       0, 0, clk_); \
`REG2_(writer.wrreq, reader.q.info.valid, writer``_wrreq, \
       DELAY, 0, clk_); \
`REG2_(writer.d.value, reader.q.value, writer``_d, \
       DELAY, 0, clk_);

`define CONNECT_FIFOS1(writer, reader, clk_=clk, DELAY=9) \
`REG2_(reader.rdreq, ~reader.empty & ~writer.half_full, reader``_rdreq, \
       DELAY-1, 0, clk_); \
`REG2_(writer.wrreq, reader.q.info.valid, writer``_wrreq, \
       DELAY, 0, clk_); \
`REG2_(writer.d.value, reader.q.value, writer``_d, \
       DELAY, 0, clk_);

`define CONNECT_FIFOS(writer, reader) \
    assign reader.rdreq = ~reader.empty & ~writer.half_full; \
    assign writer.wrreq = reader.q.info.valid; \
    assign writer.d.value = reader.q.value;


`define CONNECT_FIFO_ARRAY_NMSPC(io_array, TOTAL, nmspc) \
localparam nmspc``_QWIDTH0 = $bits(io_array.Q); \
localparam nmspc``_DWIDTH0 = $bits(io_array.D); \
localparam type nmspc``_Q0 = logic [TOTAL-1:0][nmspc``_QWIDTH0-1:0]; \
localparam type nmspc``_D0 = logic [TOTAL-1:0][nmspc``_DWIDTH0-1:0]; \
nmspc``_Q0 nmspc``_q; \
nmspc``_D0 nmspc``_d; \
    `FOR(genvar, I, TOTAL) begin \
        assign io_array.ios[I].rdreq               = io_array.rdreq[I];\
        assign io_array.ios[I].wrreq               = io_array.wrreq[I];\
        if (SIM) begin\
            assign io_array.ios[I].d.value             = nmspc``_d[I]; \
            assign nmspc``_q[I] = io_array.ios[I].q.value; \
        end else begin\
            assign io_array.ios[I].d.value             = io_array.d.value[I]; \
            assign io_array.q.value[I]                 = io_array.ios[I].q.value;\
        end\
        assign io_array.q.info_master.value[I]     = io_array.ios[I].q.info;\
        assign io_array.empty[I]                   = io_array.ios[I].empty;\
        assign io_array.almost_empty[I]     = io_array.ios[I].almost_empty;\
        assign io_array.rdready[I]     = io_array.ios[I].rdready;\
        assign io_array.rdready2[I]     = io_array.ios[I].rdready2;\
        assign io_array.full[I]                    = io_array.ios[I].full;\
        assign io_array.half_full[I]               = io_array.ios[I].half_full;\
    end\
if (SIM) begin\
    assign io_array.q.value                 = nmspc``_q; \
    assign nmspc``_d = io_array.d.value;\
end
`define CONNECT_FIFO_ARRAY(io_array, TOTAL) \
`CONNECT_FIFO_ARRAY_NMSPC(io_array, TOTAL, io_array)

`define CONNECT_FIFO_ARRAY_(io_array, TOTAL) \
    `FOR(genvar, I, TOTAL) begin \
        assign io_array.rdreq[I]                   = io_array.ios[I].rdreq;\
        assign io_array.wrreq[I]                   = io_array.ios[I].wrreq;\
        assign io_array.d.value[I]                 = io_array.ios[I].d.value;\
        assign io_array.d.info_master.value[I]     = io_array.ios[I].d.info;\
        assign io_array.ios[I].q.value             = io_array.q.value[I];\
        assign io_array.ios[I].q.info_master.value = io_array.q.info[I];\
        assign io_array.ios[I].empty               = io_array.empty[I];\
        assign io_array.ios[I].full                = io_array.full[I];\
        assign io_array.ios[I].half_full           = io_array.half_full[I];\
    end

`define CONNECT_FIFO_ARRAY2(io_array, TOTAL) \
localparam io_array``_QWIDTH = $bits(io_array.Q); \
localparam io_array``_DWIDTH = $bits(io_array.D); \
localparam type io_array``_Q = logic [TOTAL-1:0][io_array``_QWIDTH-1:0]; \
localparam type io_array``_D = logic [TOTAL-1:0][io_array``_DWIDTH-1:0]; \
io_array``_Q io_array``_q; \
io_array``_D io_array``_d; \
    `FOR(genvar, I, TOTAL) begin \
        assign io_array.rdreq[I]                   = io_array.ios[I].rdreq;\
        assign io_array.ios[I].wrreq               = io_array.wrreq[I];\
        if (SIM) begin\
            assign io_array.ios[I].d.value             = io_array``_d[I]; \
            assign io_array``_q[I] = io_array.ios[I].q.value; \
        end else begin\
            assign io_array.ios[I].d.value             = io_array.d.value[I]; \
            assign io_array.q.value[I]                 = io_array.ios[I].q.value;\
        end\
        assign io_array.q.info_master.value[I]     = io_array.ios[I].q.info;\
        assign io_array.empty[I]                   = io_array.ios[I].empty;\
        assign io_array.full[I]                    = io_array.ios[I].full;\
        assign io_array.half_full[I]               = io_array.ios[I].half_full;\
    end\
if (SIM) begin\
    assign io_array.q.value                 = io_array``_q; \
    assign io_array``_d = io_array.d.value;\
end

`define CONNECT_DPRAM_ARRAY(io_array, TOTAL) \
localparam io_array``_QWIDTH3 = $bits(io_array.Q); \
localparam io_array``_DWIDTH3 = $bits(io_array.D); \
localparam type io_array``_D3 = logic [TOTAL-1:0][io_array``_DWIDTH3-1:0]; \
io_array``_D3 io_array``_d3; \
    `FOR(genvar, I, TOTAL) begin \
        assign io_array.ios[I].rdaddress           = io_array.rdaddress[I]; \
        assign io_array.ios[I].wraddress           = io_array.wraddress[I]; \
        assign io_array.ios[I].rdreq               = io_array.rdreq[I]; \
        assign io_array.ios[I].wrreq               = io_array.wrreq[I]; \
        if (SIM) begin\
            assign io_array.ios[I].d.value             = io_array``_d3[I]; \
        end else begin\
            assign io_array.ios[I].d.value             = io_array.d.value[I]; \
        end\
        assign io_array.ios[I].d.info_master.value = io_array.d.info[I]; \
        assign io_array.q.value[I]                 = io_array.ios[I].q.value; \
        assign io_array.q.info_master.value[I]     = io_array.ios[I].q.info; \
        assign io_array.ready[I]                   = io_array.ios[I].ready; \
    end\
if (SIM) begin\
    assign io_array``_d3 = io_array.d.value;\
end

`define CONNECT_DPRAM_ARRAY_(io_array, TOTAL) \
    localparam io_array``_QWIDTH2 = $bits(io_array.Q); \
    localparam io_array``_DWIDTH2 = $bits(io_array.D); \
    localparam type io_array``_D2 = logic [TOTAL-1:0][io_array``_DWIDTH2-1:0]; \
    io_array``_D2 io_array``_d2; \
    `FOR(genvar, I, TOTAL) begin \
        assign io_array.rdaddress[I]               = io_array.ios[I].rdaddress; \
        assign io_array.wraddress[I]               = io_array.ios[I].wraddress; \
        assign io_array.rdreq[I]                   = io_array.ios[I].rdreq; \
        assign io_array.wrreq[I]                   = io_array.ios[I].wrreq; \
        if (SIM) begin\
            assign io_array``_d2[I]                    = io_array.ios[I].d.value;\
        end else begin\
        assign io_array.d.value[I]                 = io_array.ios[I].d.value; \
        end\
        assign io_array.d.info_master.value[I]     = io_array.ios[I].d.info; \
        assign io_array.ios[I].q.value             = io_array.q.value[I]; \
        assign io_array.ios[I].q.info_master.value = io_array.q.info[I]; \
        assign io_array.ios[I].ready               = io_array.ready[I]; \
    end\
if (SIM) begin\
    assign io_array.d.value                 = io_array``_d2;\
end

`endif

`define DFIFOS_IPFIFO(ip_module) \
ip_module dfifos_fifo_u \
( \
  .data    (dfifos.ios[I].d.value), \
  .q       (dfifos.ios[I].q.value), \
  .wrreq   (dfifos.ios[I].wrreq), \
  .rdreq   (dfifos.ios[I].rdreq), \
  .rdempty (dfifos.ios[I].empty), \
  .wrfull  (dfifos.ios[I].full), \
  .wrclk   (dfifos.ios[I].wrclk), \
  .rdclk   (dfifos.ios[I].rdclk), \
  .wrusedw   (dfifos_wrusedw), \
  .aclr(~dfifos.ios[I].resetn) \
  );
