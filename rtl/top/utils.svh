`ifndef __UTILS_SVH__
`define __UTILS_SVH__


`define NMSPC(a) a

`ifndef SIM
`define SHIFT_REG___(q_, d_, LATENCY_=1, nmspc, type=`logic , clk_=clk, resetn_=resetn, RESET_VALUE_=0) \
reg_ #(.WIDTH($bits(q_)), .LATENCY(LATENCY_), .RESET_VALUE(RESET_VALUE_)) \
`NMSPC(nmspc)_reg_u(.q(q_), .d(d_), .clk(clk_), .resetn(resetn_));
`else

`define SHIFT_REG___(q, d, LATENCY=1, nmspc, type_=logic signed , clk=clk, resetn=resetn, RESET_VALUE=0) \
localparam         `NMSPC(nmspc)_WIDTH = $bits(q); \
localparam         `NMSPC(nmspc)_DEPTH = LATENCY; \
typedef logic [`NMSPC(nmspc)_DEPTH-1:0][`NMSPC(nmspc)_WIDTH-1:0] `NMSPC(nmspc)_Vec; \
typedef type_ [`NMSPC(nmspc)_WIDTH-1:0] `NMSPC(nmspc)_Scalar; \
`NMSPC(nmspc)_Vec `NMSPC(nmspc)_d_dff, `NMSPC(nmspc)_q_dff; \
`NMSPC(nmspc)_Scalar `NMSPC(nmspc)_d; \
`NMSPC(nmspc)_Scalar `NMSPC(nmspc)_q; \
assign `NMSPC(nmspc)_d = d; \
assign q = `NMSPC(nmspc)_q; \
if (LATENCY == 0) assign `NMSPC(nmspc)_q = `NMSPC(nmspc)_d; \
else begin \
    assign `NMSPC(nmspc)_d_dff = LATENCY > 1? {`NMSPC(nmspc)_d, `NMSPC(nmspc)_q_dff[`NMSPC(nmspc)_DEPTH-1:1]} : `NMSPC(nmspc)_d; \
						assign `NMSPC(nmspc)_q = `NMSPC(nmspc)_q_dff[0]; \
    always_ff @(posedge clk or negedge resetn) if (~resetn) begin \
        `NMSPC(nmspc)_q_dff <= RESET_VALUE? '1 : '0; \
    end else begin \
        `NMSPC(nmspc)_q_dff <= `NMSPC(nmspc)_d_dff; \
    end \
end
`endif

`define SHIFTREG(q_, d_, LATENCY_=1, clk_=clk, resetn_=resetn) \
`SHIFT_REG___(q_.value, d_.value, LATENCY_, q_``_value, logic, clk_, resetn_)\
`SHIFT_REG___(q_.info_master.value, d_.info, LATENCY_,\
														q_``_info, logic, clk_, resetn_)

`define SHIFT_REG(q_, d_, LATENCY_=1, nmspc, clk_=clk, resetn_=resetn) \
`SHIFT_REG___(q_.value, d_.value, LATENCY_, nmspc``_reg, logic, clk_, resetn_)


`define SHIFT_REG__(q_, d_, LATENCY_=1, nmspc, clk_=clk, resetn_=resetn) \
`SHIFT_REG___(q_, d_, LATENCY_, nmspc``_reg, logic, clk_, resetn_)
`define SHIFT_REG_(q, d, LATENCY=1, clk_=clk, resetn_=resetn) \
    `SHIFT_REG__(q, d, LATENCY, q, clk_, resetn_)
//
`define REG(q, d, LATENCY=1, clk_=clk, resetn_=resetn) \
    `SHIFT_REG__(q, d, LATENCY, q, clk_, resetn_)

`define REG_(q, d, LATENCY=1, nmspc, clk_=clk, resetn_=resetn) \
    `SHIFT_REG__(q, d, LATENCY, nmspc, clk_, resetn_)

`define REG__(q, d, LATENCY=1, clk_=clk, resetn_=resetn) \
    logic q; \
    `SHIFT_REG__(q, d, LATENCY, q, clk_, resetn_)

`define SHIFTVEC2_(q_, nmspc, d_, NO_DELAY=globals::FALSE, DIRECTION=globals::RIGHT, RESET_VALUE=0, clk_=clk, resetn_=resetn) \
localparam nmspc``DWIDTH = $bits(d_); \
localparam nmspc``QWIDTH = $bits(q_); \
localparam nmspc``DEPTH = nmspc``QWIDTH/nmspc``DWIDTH; \
localparam nmspc``WIDTH = nmspc``DWIDTH; \
typedef logic [nmspc``DEPTH-1:0][nmspc``WIDTH-1:0] nmspc``Vec; \
nmspc``Vec nmspc``q``dff; \
nmspc``Vec nmspc``d``dff; \
`REG3(nmspc``q``dff, nmspc``q``dff, nmspc``d``dff, 1, \
			clk_, RESET_VALUE, resetn_); \
if (DIRECTION == RIGHT) begin \
    assign nmspc``d``dff \
			= nmspc``DEPTH > 1? {d_``, nmspc``q``dff[nmspc``DEPTH-1:1]}\
				: d_``; \
        assign q_`` = NO_DELAY? nmspc``d``dff : nmspc``q``dff;\
                      end else begin  // else left shift \
                          assign nmspc``d``dff = {nmspc``q``dff, d_``}; \
                            assign q_`` = NO_DELAY? nmspc``d``dff : nmspc``q``dff;\
                                          end\

`define SHIFTVEC2(q_, d_, NO_DELAY=globals::FALSE, DIRECTION=globals::RIGHT, RESET_VALUE=0, clk_=clk, resetn_=resetn) \
`SHIFTVEC2_(q_, q_, d_, NO_DELAY, DIRECTION, RESET_VALUE, clk_, resetn_);


`define SHIFTVEC3_(q_, nmspc, d_, clk_=clk, resetn_=resetn, NO_DELAY=globals::FALSE, DIRECTION=globals::RIGHT, RESET_VALUE=0) \
typedef q_``.VALUE nmspc``Q; \
typedef d_``.VALUE nmspc``D; \
localparam nmspc``DWIDTH = $bits(nmspc``D); \
localparam nmspc``QWIDTH = $bits(nmspc``Q); \
localparam nmspc``DEPTH = nmspc``QWIDTH/nmspc``DWIDTH; \
localparam nmspc``WIDTH = nmspc``DWIDTH; \
typedef logic [nmspc``DEPTH-1:0][nmspc``WIDTH-1:0] nmspc``Vec; \
nmspc``Vec nmspc``q``dff; \
nmspc``Vec nmspc``d``dff; \
`REG3(nmspc``q``dff, nmspc``q``dff, nmspc``d``dff, 1, \
						clk_, RESET_VALUE, resetn_); \
if (DIRECTION == RIGHT) begin \
    assign nmspc``d``dff \
						= nmspc``DEPTH > 1? {d_``.value, nmspc``q``dff[nmspc``DEPTH-1:1]}\
								: d_``.value; \
      assign q_``.value = NO_DELAY? nmspc``d``dff : nmspc``q``dff;\
end else begin  // else left shift \
    assign nmspc``d``dff = {nmspc``q``dff, d_``.value}; \
      assign q_``.value = NO_DELAY? nmspc``d``dff : nmspc``q``dff;\
end\

`define SHIFTVEC3(q_, d_, NO_DELAY=globals::FALSE, DIRECTION=globals::RIGHT, RESET_VALUE=0) \
`SHIFTVEC3_(q_, q_, d_, clk, resetn, NO_DELAY, DIRECTION, RESET_VALUE);


`define SHIFTVEC_ENVEC_(q_, nmspc, d_, envec, clk_=clk, resetn_=resetn, NO_DELAY=globals::FALSE, DIRECTION=globals::RIGHT, RESET_VALUE=0) \
localparam nmspc``DWIDTH = $bits(d_); \
localparam nmspc``QWIDTH = $bits(q_); \
localparam nmspc``DEPTH = nmspc``QWIDTH/nmspc``DWIDTH; \
localparam nmspc``WIDTH = nmspc``DWIDTH; \
typedef logic [nmspc``DEPTH-1:0][nmspc``WIDTH-1:0] nmspc``Vec; \
nmspc``Vec nmspc``q``dff; \
nmspc``Vec nmspc``d``dff; \
`DFF_ENVEC_(nmspc``q``dff, nmspc``q``dff_dff, nmspc``d``dff, envec,\
 clk_, resetn_, RESET_VALUE); \
if (DIRECTION == RIGHT) begin \
    assign nmspc``d``dff = nmspc``DEPTH > 1? {d_``, nmspc``q``dff[nmspc``DEPTH-1:1]} : d_``; \
      assign q_`` = NO_DELAY? nmspc``d``dff : nmspc``q``dff; \
end else begin  // else left shift \
    assign nmspc``d``dff = {nmspc``q``dff, d_``}; \
      assign q_`` = NO_DELAY? nmspc``d``dff : nmspc``q``dff; \
end\

`define DFF_ENVEC_(q_, nmspc, d_, envec, clk_=clk, resetn_=resetn, RESET_VALUE=0) \
localparam nmspc``DEPTH = $size(q_, 1);\
localparam nmspc``WIDTH = $bits(q_) / nmspc``DEPTH;\
typedef logic [nmspc``DEPTH-1:0][nmspc``WIDTH-1:0] nmspc``Vec;\
nmspc``Vec nmspc``_q, nmspc``_d;\
assign q_ = nmspc``_q;\
assign nmspc``_d = d_;\
always_ff @(posedge clk_ or negedge resetn_)\
if (~resetn_) nmspc``_q <= RESET_VALUE;\
else begin\
				for (int I=0; I!=nmspc``DEPTH; I++)\
						nmspc``_q[I] <= envec[I]? nmspc``_d[I] : nmspc``_q[I];\
																						end


`define DFF_ENVEC(q_, d_, envec, clk_=clk, resetn_=resetn, RESET_VALUE=0) \
`DFF_ENVEC_(q_, q_, d_, envec, clk_, resetn_, RESET_VALUE);

`define SHIFTVEC_ENVEC(q_, d_, envec, NO_DELAY=globals::FALSE, DIRECTION=globals::RIGHT, RESET_VALUE=0) \
`SHIFTVEC_ENVEC_(q_, q_, d_, envec, clk, resetn, NO_DELAY, DIRECTION, RESET_VALUE);


`define SHIFTVEC(q_, d_, nmspc, clk_=clk, resetn_=resetn) \
shiftvec_ #(.WIDTH($bits(d_.VALUE)), .DEPTH($bits(q_.VALUE) / nmspc``_WIDTH)) \
    `NMSPC(nmspc)_shiftvec_u(.q(q_.value), .d(d_.value), .clk(clk_), .resetn(resetn_));


`define SHIFTVEC__(q_, d_, nmspc, clk_=clk, resetn_=resetn) \
    shiftvec_ #(.WIDTH($bits(d_)), .DEPTH($bits(q_)/$bits(d_))) \
    `NMSPC(nmspc)_shiftvec_u(.q(q_), .d(d_), .clk(clk_), .resetn(resetn_));
//
`define SHIFTVEC_(q, d, clk_=clk, resetn_=resetn) \
`SHIFTVEC__(q, d, q, clk_, resetn_)


`define SHIFTVEC_EN__(q_, d_, en_, nmspc, clk_=clk, resetn_=resetn) \
shiftvec_en #(.WIDTH($bits(d_)), .DEPTH($bits(q_)/$bits(d_))) \
 `NMSPC(nmspc)_shiftvec_en_u(.q(q_), .d(d_), .clk(clk_), .en(en_), .resetn(resetn_));
    //
`define SHIFTVEC_EN_(q, d, en, clk_=clk, resetn_=resetn) \
 `SHIFTVEC_EN__(q, d, en, q, clk_, resetn_)


`define ONOFF_(q_, on_, off_=0, LATENCY_=1, nmspc, clk_=clk, resetn_=resetn, RESET_VAL_=0) \
dff_on_off #(.LATENCY(LATENCY_), .WIDTH($bits(q_)), .RESET_VAL(RESET_VAL_)) \
nmspc``_onoff_u (.q(q_), .on(on_), .off(off_), .clk(clk_), .resetn(resetn_));

`define ONOFF(q_, on_, off_=0, LATENCY=1, clk_=clk, resetn_=resetn) \
    `ONOFF_(q_, on_, off_, LATENCY, q_, clk_, resetn_)

`define ONOFF2(q_, on_, off_=0, RESET_VAL=0, LATENCY=1, clk_=clk, resetn_=resetn) \
`ONOFF_(q_, on_, off_, LATENCY, q_, clk_, resetn_, RESET_VAL)

`define ONOFF__(q_, on_, off_=0, LATENCY=1, clk_=clk, resetn_=resetn) \
    logic q_; \
    `ONOFF_(q_, on_, off_, LATENCY, q_, clk_, resetn_)


`define POSEDGE_(q_, d_, LATENCY_=1, nmspc, clk_=clk, resetn_=resetn) \
    posedge_ #(.LATENCY(LATENCY_)) nmspc``_posedge_u \
    (.q(q_), .d(d_), .clk(clk_), .resetn(resetn_));

`define POSEDGE(q_, d_, LATENCY=1, clk_=clk, resetn_=resetn) \
    `POSEDGE_(q_, d_, LATENCY, q_, clk_, resetn_)

`define POSEDGE__(q_, d_, LATENCY=1, clk_=clk, resetn_=resetn) \
    logic q_; \
    `POSEDGE_(q_, d_, LATENCY, q_, clk_, resetn_)


`define ACK_(q_, d_, ack_, LATENCY_=1, nmspc, clk_=clk, resetn_=resetn) \
    ack #(.LATENCY(LATENCY_), .WIDTH($bits(q_))) nmspc``_ack_u \
    (.q(q_), .d(d_), .ack(ack_), .clk(clk_), .resetn(resetn_));
//
`define ACK(q_, d_, ack_, LATENCY_=1, clk_=clk, resetn_=resetn) \
 `ACK_(q_, d_, ack_, LATENCY_, q_, clk_, resetn_);

`define ACK__(q_, d_, ack_, LATENCY_=1, clk_=clk, resetn_=resetn) \
logic q_; \
`ACK_(q_, d_, ack_, LATENCY_, q_, clk_, resetn_);

`define ACKFIFO2(q_, d_, ack_, ready_, LATENCY=0, clk_=clk, resetn_=resetn) \
logic q_``_ackfifo_q; \
`REG(q_, q_``_ackfifo_q, LATENCY-1, clk_, resetn_) \
ackfifo q_``_ackfifo_u(.q(q_``_ackfifo_q), .d(d_), .ack(ack_), .clk(clk_), .resetn(resetn_), .ready(ready_));

`define ACKFIFO(q_, d_, ack_, LATENCY=0, clk_=clk, resetn_=resetn) \
logic q_``_ackfifo_q; \
`REG(q_, q_``_ackfifo_q, LATENCY-1, clk_, resetn_) \
ackfifo q_``_ackfifo_u(.q(q_``_ackfifo_q), .d(d_), .ack(ack_), .clk(clk_), .resetn(resetn_));

`define ACKFIFO__(q_, d_, ack_, clk_=clk, resetn_=resetn) \
logic q_; \
ackfifo q_``_ackfifo_u(.q(q_), .d(d_), .ack(ack_), .clk(clk_), .resetn(resetn_));

`endif
