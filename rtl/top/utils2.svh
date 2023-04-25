`ifndef __UTILS2_SVH__
`define __UTILS2_SVH__

`define _REG2(q_, d_, nmspc, LATENCY_, RESET_VALUE_, clk_=clk, resetn_=resetn) \
`SHIFT_REG___(q_, d_, LATENCY_, nmspc``_reg, logic, clk_, resetn_, RESET_VALUE_)

`define REG2__(q, d, LATENCY=1, RESET_VALUE_=0, clk_=clk, resetn_=resetn) \
logic [$bits(d)-1:0] q; \
`_REG2(q, d, q, LATENCY, RESET_VALUE_, clk_, resetn_)

`define REG2_(q, d, nmspc, LATENCY=1, RESET_VALUE_=0, clk_=clk, resetn_=resetn)\
`_REG2(q, d, nmspc, LATENCY, RESET_VALUE_, clk_, resetn_)

`define REG3(q, nmspc, d, LATENCY=1, clk_=clk, RESET_VALUE_=0, resetn_=resetn) \
`_REG2(q, d, nmspc, LATENCY, RESET_VALUE_, clk_, resetn_)

`define REG2(q, d, LATENCY=1, clk_=clk, resetn_=resetn) \
`REG(q, d, LATENCY, clk_, resetn_)

`define REG_COND(q, cond, a, b, LATENCY=1) \
`REG3(q, q, cond? a : b, LATENCY);

`define REG_COND_(q, nmspc, cond, a, b, LATENCY=1) \
`REG3(q, nmspc, cond? a : b, LATENCY);

`define REG_DATA_COND(q, cond, a, b, LATENCY=1) \
`REG3(q.value, q``_value, cond? a.value : b.value, LATENCY, q.clk); \
`REG3(q.info_master.value, q``_info, cond? a.info : b.info, LATENCY, q.clk)

`define REG_DATA_COND_(q, nmspc, cond, a, b, LATENCY=1) \
`REG3(q.value, nmspc``_value, cond? a.value : b.value, LATENCY, q.clk); \
`REG3(q.info_master.value, nmspc``_info, cond? a.info : b.info, LATENCY, q.clk)

`define COUNTER_(type_, nmspc, q, en, stride, clk_=clk, RESET_VALUE=0, resetn_=resetn) \
`ifdef SIM \
type_ nmspc; \
`REG3(nmspc, nmspc, q + stride, 1, clk_, RESET_VALUE, resetn_) \
`endif

`define COUNTER(q, stride, reset=0, clk_=clk, RESET_VALUE=0, resetn_=resetn) \
`REG3(q, q, reset? '0 : q + $bits(q)'(stride), 1, clk_, RESET_VALUE, resetn_) \

`define SIMCOUNTER(q, stride, reset=0, clk_=clk, RESET_VALUE=0, resetn_=resetn) \
`ifndef TEST_FMAX\
if (SIM || SYNTH_DEBUG) begin \
    `COUNTER(q, stride, reset, clk_, RESET_VALUE, resetn_) \
end\
`endif

`define SIMWORDSWAP_(q_, nmspc, d_, LATENCY_=1, clk_=clk, WORD_WIDTH_=$bits(Instruc::HostData)) \
if (SIM) begin \
				`WORDSWAP_(q_, nmspc, d_, LATENCY_, clk_, WORD_WIDTH_); \
end else begin \
    `REG3(q_, nmspc, d_, LATENCY_, clk_); \
end

`define SYNTHWORDSWAP_(q_, nmspc, d_, LATENCY_=1, clk_=clk, WORD_WIDTH_=$bits(Instruc::HostData)) \
if (SIM) begin \
    `REG3(q_, nmspc, d_, LATENCY_, clk_); \
end else begin \
    `WORDSWAP_(q_, nmspc, d_, LATENCY_, clk_, WORD_WIDTH_); \
end

`define WORDSWAP_(q_, nmspc, d_, LATENCY_=1, clk_=clk, WORD_WIDTH_=$bits(Instruc::HostData)) \
wordswap #(.DWIDTH($bits(q_)), .LATENCY(LATENCY_), .WORD_WIDTH(WORD_WIDTH_)) \
nmspc``wordswap_u(.q(q_), .d(d_), .clk(clk_), .resetn)

`define WORDSWAP(q, d, LATENCY=1, clk_=clk) `WORDSWAP_(q, q, d, LATENCY, clk_)

`define WORDSWAP2_(q, nmspc, d, WORD_WIDTH=A_WIDTH, LATENCY=0, clk_=clk) \
`WORDSWAP_(q.value, nmspc``_value, d.value, LATENCY, clk_, WORD_WIDTH); \
`REG3(q.info_master.value, nmspc``_info, d.info, LATENCY)

`define WORDSWAP2(q, d, WORD_WIDTH=A_WIDTH, LATENCY=0, clk_=clk) \
`WORDSWAP2_(q, q, d, WORD_WIDTH, LATENCY, clk_)

`define ASSIGN_RESULT(RESULTS_SEL, d_, clk_=clk); \
`SYNTHWORDSWAP_(results.d.value[RESULTS_SEL], RESULTS_SEL``_d, d_.value, 1, clk_); \
`REG3(results.wrreq[RESULTS_SEL], RESULTS_SEL``_wrreq, d_.info.valid, 1, clk_);

`define ASSIGN_RESULT2(RESULTS_SEL, d_); \
`REG3(results.d.value[RESULTS_SEL], RESULTS_SEL``_d, d_.value); \
`REG3(results.wrreq[RESULTS_SEL], RESULTS_SEL``_wrreq, d_.info.valid);

`define ONOFF4(q_, on_, off_=0, LATENCY_=1, nmspc, clk_=clk, resetn_=resetn, RESET_VAL_=0) \
dff_on_off #(.LATENCY(LATENCY_), .WIDTH($bits(q_)), .RESET_VAL(RESET_VAL_), \
													.PRIORITIZE_ON(FALSE)) \
nmspc``_onoff_u (.q(q_), .on(on_), .off(off_), .clk(clk_), .resetn(resetn_));

`define ONOFF3(q_, on_, off_=0, LATENCY=1, clk_=clk, resetn_=resetn) \
`ONOFF4(q_, on_, off_, LATENCY, q_, clk_, resetn_)
`endif
