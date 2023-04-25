`include "../top/define.svh"

// This is a DRAM behavioural model

// avoids simulating the dram IP which can take days to simulate
// Note: BURST_COUNT must be a multiple of mem DEPTH
//
// if NOT_READY_PERIOD > 0 then behav_dram will NOT be ready once every
// NOT_READY_PERIOD cc's
//
// if NOT_READY_PERIOD < 0 then behav_dram will ONLY be ready once every
// abs(NOT_READY_PERIOD) cc's
//
// if NOT_READY_PERIOD == 0 then behav_dram will always be ready
module behav_dram #(CAL_DELAY = 10,
                    NOT_READY_PERIOD = -3,
                    BURST_COUNT=1)
    (sprambus io, input logic pll_ref_clk,
     output logic cal_success, output logic emif_usr_clk, input logic resetn);
    logic [io.DEPTH-1:0][io.WIDTH-1:0] data;
    logic [$clog2(io.DEPTH)-1:0]       final_address, base_address, not_ready_count;
    logic [$clog2(BURST_COUNT)-1:0]    rdburst_count, wrburst_count;
    logic                              clk, ready;
    logic                              rdburst_init, rdburst_en;
    logic                              wrburst_init, wrburst_en;

    assign clk = emif_usr_clk;
    assign emif_usr_clk = pll_ref_clk;

    assign io.ready = ready & cal_success;

    counter #(.RANGE(CAL_DELAY)) cal_delay_u
        (.count(), .en(!cal_success), .carry(cal_success), .clk,
         .resetn);

    if (signed'(NOT_READY_PERIOD) > 0) begin
        counter #(.RANGE(NOT_READY_PERIOD)) not_ready_count_u
            (.count(not_ready_count), .en('1),
             .complete_n(ready),
             .clk, .resetn);
    end else if (signed'(NOT_READY_PERIOD) < 0) begin
        counter #(.RANGE(-NOT_READY_PERIOD)) not_ready_count_u
            (.count(not_ready_count), .en('1),
             .complete(ready),
             .clk, .resetn);
    end else begin
        assign ready = 1'b1;
    end

    always_ff @(posedge clk or negedge resetn) begin
        if (~resetn) begin
            io.q.info_master.value.valid <= 1'b0;
            io.q.value <= '0;
            base_address <= '0;
        end else begin
            io.q.info_master.value.valid <= rdburst_en;
            io.q.value <= data[final_address];
            if (rdburst_init | wrburst_init) base_address <= io.address;
            if (wrburst_en) data[final_address] <= io.d.value;
        end
    end // always_ff @ (posedge clk)

    always_comb begin
        rdburst_init = io.rdreq & io.ready;
        wrburst_init = io.wrreq & (wrburst_count == 0) & io.ready;
        rdburst_en = (io.rdreq | (rdburst_count > 0)) & io.ready;
        wrburst_en = io.wrreq & io.ready;

        if (rdburst_init | wrburst_init)
            final_address = io.address;
        else if (rdburst_en) begin
            final_address = base_address + rdburst_count;
        end else begin
            final_address = base_address + wrburst_count;
        end
    end // always_comb

    counter #(.RANGE(BURST_COUNT)) rdburst_state_u
        (.count(rdburst_count), .en(rdburst_en), .clk, .resetn);

    counter #(.RANGE(BURST_COUNT)) wrburst_state_u
        (.count(wrburst_count), .en(wrburst_en), .clk, .resetn);
endmodule
