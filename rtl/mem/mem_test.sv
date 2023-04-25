module mem_test
    #(type Q=Dram::Q, D=Q,
      integer DEPTH=Dram::DEPTH, BURST_COUNT=1, RANGE=16)
    (sprambus mem, output logic keep_synth,
     input logic clk, input logic resetn);
    import globals::*;
    localparam   D_MULT_FACTOR = mem.WIDTH / $clog2(RANGE);
    logic [$clog2(mem.DEPTH)-1:0] validation_address;
    logic [$clog2(mem.DEPTH)-1:0] wrong_score, correct_score;
    logic [$clog2(BURST_COUNT)-1:0] burst_count;
    logic [mem.WIDTH-1:0]           validation_val;
    logic                           at_last_address;
    logic                           start;
    logic                           in_rdstate, in_wrstate;

    typedef enum                    {RD, WR} RdWrState;
    RdWrState rdwrstate;

    assign in_rdstate = (rdwrstate == RD);
    assign in_wrstate = (rdwrstate == WR);

    dff_on_off  #(0) start_u (.q(start), .on(mem.ready), .off('0),
                              .clk, .resetn);

    counter #(RANGE)
    address_u (.count(mem.address), .en(mem.ready), .carry(at_last_address),
               .clk, .resetn);

    counter #(.RANGE(BURST_COUNT))
    burst_count_u (.count(burst_count), .en(mem.ready),
                   .clk, .resetn);

    counter #(.RANGE(2), .INIT_VAL(1))
    rdwrstate_u (.count({rdwrstate}), .carry(),
                 .en(at_last_address & mem.ready), .clk, .resetn);

    assign mem.d.value = in_wrstate?
                         {D_MULT_FACTOR
                          {mem.address[$clog2(RANGE)-1:0]}} : keep_synth;
    assign mem.d.info_master.value = '0;
    assign mem.rdreq = in_rdstate & start;
    assign mem.wrreq = in_wrstate & start;
    assign validation_val = {D_MULT_FACTOR{validation_address[$clog2(RANGE)-1:0]}};
    assign keep_synth = validation_val ^ mem.wrreq ^ mem.ready
                        ^ correct_score ^ wrong_score;

    counter #(RANGE)
    validation_address_u (.count(validation_address), .en(mem.q.info.valid),
                          .clk, .resetn);

    counter #(RANGE)
    wrong_score_counter_u (.count(wrong_score),
                           .en((mem.q.value !== validation_val)
                               & mem.q.info.valid),
                           .clk, .resetn);

    counter #(RANGE)
    correct_score_counter_u (.count(correct_score),
                             .en((mem.q.value === validation_val)
                                 & mem.q.info.valid),
                             .clk, .resetn);
endmodule


module fifo_mem_test
    #(type Q=Dram::Q, D=Q,
      integer DEPTH=Dram::DEPTH, BURST_COUNT=1, RANGE=16)
    (fifobus mem, output logic keep_synth,
     input logic clk, input logic resetn);
    import globals::*;
    localparam   WIDTH = $bits(D);
    localparam   D_MULT_FACTOR = WIDTH / $clog2(RANGE);
    logic [$clog2(mem.DEPTH)-1:0] validation_address;
    logic [$clog2(mem.DEPTH)-1:0] wrong_score, correct_score;
    logic [$clog2(BURST_COUNT)-1:0] burst_count;
    logic [WIDTH-1:0]               validation_val;
    logic                           at_last_address;
    logic                           start;
    logic                           in_rdstate, in_wrstate;

    typedef enum                    {RD, WR} RdWrState;
    RdWrState rdwrstate;

    assign in_rdstate = (rdwrstate == RD);
    assign in_wrstate = (rdwrstate == WR);

    dff_on_off  #(0) start_u (.q(start), .on(mem.rdready), .off('0),
                              .clk, .resetn);

    typedef logic [$clog2(DEPTH)-1:0] Address;
    Address address;
    counter #(RANGE)
    address_u (.count(address), .en(mem.rdready), .carry(at_last_address),
               .clk, .resetn);

    counter #(.RANGE(BURST_COUNT))
    burst_count_u (.count(burst_count), .en(mem.rdready),
                   .clk, .resetn);

    counter #(.RANGE(2), .INIT_VAL(1))
    rdwrstate_u (.count({rdwrstate}), .carry(),
                 .en(at_last_address & mem.rdready), .clk, .resetn);

    assign mem.d.value = in_wrstate?
                         {D_MULT_FACTOR
                          {address[$clog2(RANGE)-1:0]}} : keep_synth;
    assign mem.d.info_master.value = '0;
    assign mem.rdreq = in_rdstate & start;
    assign mem.wrreq = in_wrstate & start;
    assign validation_val = {D_MULT_FACTOR{validation_address[$clog2(RANGE)-1:0]}};
    assign keep_synth = validation_val ^ mem.wrreq ^ mem.rdready
                        ^ correct_score ^ wrong_score;

    counter #(RANGE)
    validation_address_u (.count(validation_address), .en(mem.q.info.valid),
                          .clk, .resetn);

    counter #(RANGE)
    wrong_score_counter_u (.count(wrong_score),
                           .en((mem.q.value !== validation_val)
                               & mem.q.info.valid),
                           .clk, .resetn);

    counter #(RANGE)
    correct_score_counter_u (.count(correct_score),
                             .en((mem.q.value === validation_val)
                                 & mem.q.info.valid),
                             .clk, .resetn);
endmodule
