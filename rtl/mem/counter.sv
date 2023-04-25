`include "../top/define.svh"


module counter_digit import globals::TRUE, globals::FALSE;
    #(WIDTH, INITIAL_VALUE_NORMALIZED=0)
    (input logic en, logic clk, logic resetn,
     logic [WIDTH-1:0] size,
     logic [WIDTH-1:0] stride,
     logic [WIDTH-1:0] stride_normalized,
     logic             stride_valid,
     output logic      carry, pre_carry,
     logic             at_last_value,
     logic             at_2nd_last_value,
     logic             at_4th_last_value,
     logic             at_first_value,
     logic             at_last_value_of_multiple,
     logic             at_first_value_of_multiple,
     logic [WIDTH-1:0] count,
     logic [WIDTH-1:0] count_normalized
     );
    logic [WIDTH-1:0]  count_d;
    logic [WIDTH-1:0]  count_init;
    always_comb begin
        count_init = '0;
        if (INITIAL_VALUE_NORMALIZED > 0)
            count_init = {stride>>$clog2(globals::LAYERIOMEM_CLK_DIV)}
                         *INITIAL_VALUE_NORMALIZED;
        count_d = count;
        if (stride_valid & (count_d == 0))
            count_d = count_init;
        if (en) count_d = $bits(count)'(count_d + stride);
        if (pre_carry & en) count_d = count_init;
    end
    logic [WIDTH+1:0] stride_normalized_lshft2;
    always_comb begin
        stride_normalized_lshft2 = stride_normalized<<2;
        pre_carry = FALSE;
        at_last_value = FALSE;
        at_2nd_last_value = FALSE;
        at_4th_last_value = FALSE;
        at_first_value = count_normalized == FALSE;
        if (size <= stride_normalized) begin
            at_last_value = TRUE;
        end else begin
            at_last_value = (count_normalized >= (size-stride_normalized));
        end
        if (size < stride_normalized_lshft2) begin
            at_4th_last_value = TRUE;
        end else begin
            if (stride_normalized_lshft2 > count_normalized)
                at_4th_last_value =  TRUE;
            else
                at_4th_last_value = (count_normalized
                                     >= (size-stride_normalized_lshft2));
        end
        if (size <= {stride_normalized<<1}) begin
            at_2nd_last_value = TRUE;
        end else begin
            if ({stride_normalized<<1} > count_normalized)
                at_2nd_last_value = TRUE;
            else
                at_2nd_last_value = (count_normalized
                                     >= (size-{stride_normalized<<1}));
        end
        if (en) begin
            pre_carry = at_last_value;
        end
        at_last_value_of_multiple = at_last_value & (size > stride_normalized);
        at_first_value_of_multiple = at_first_value & (size > stride_normalized);
    end
    always_ff @(posedge clk or negedge resetn) begin
        if (~resetn) begin
            count <= '0;
            count_normalized <= INITIAL_VALUE_NORMALIZED;
            carry <= 1'b0;
        end else begin
            count <= count_d;
            if (en) count_normalized
                <= $bits(count)'(count_normalized + stride_normalized);
            if (pre_carry & en) count_normalized <= INITIAL_VALUE_NORMALIZED;
            carry <= pre_carry;
        end
    end
endmodule // counter

`define _COUNTER(INITIAL_VALUE_NORMALIZED_) \
counter_digit \
#(.WIDTH(DIGIT_WIDTH), \
  .INITIAL_VALUE_NORMALIZED(INITIAL_VALUE_NORMALIZED_)) digits_u \
( \
  .en(carry_ins[I]), \
  .carry(_carries[I]), \
  .pre_carry(pre_carries[I]), \
  .at_first_value(_at_first_values[I]), \
  .at_last_value(_at_last_values[I]), \
  .at_2nd_last_value(_at_2nd_last_values[I]), \
  .at_4th_last_value(_at_4th_last_values[I]), \
  .at_first_value_of_multiple(_at_first_values_of_multiple[I]), \
  .at_last_value_of_multiple(_at_last_values_of_multiple[I]), \
  .count(digits[I]), \
  .count_normalized(counts_normalized[I]), \
  .size(sizes[I]), \
  .stride(strides[I]), \
  .stride_normalized(strides_normalized[I]), \
  .stride_valid, \
  .clk, .resetn \
  );

module multi_digit_counter
    #(DIGIT_WIDTH, TOTAL_DIGITS, OFFSET_WIDTH, ID = 0)
    (input logic en, clk, resetn,
     logic [TOTAL_DIGITS-1:0][DIGIT_WIDTH-1:0]        sizes,
     logic [TOTAL_DIGITS-1:0][DIGIT_WIDTH-1:0]        strides,
     logic [TOTAL_DIGITS-1:0][DIGIT_WIDTH-1:0]        strides_normalized,
     logic [OFFSET_WIDTH-1:0]                         offset,
     logic                                            stride_valid,
     output logic [TOTAL_DIGITS-1:0]                  carry_ins,
     output logic [TOTAL_DIGITS-1:0]                  carries,
     output logic [TOTAL_DIGITS-1:0]                  pre_carries,
     output logic [TOTAL_DIGITS-1:0][DIGIT_WIDTH-1:0] counts,
     output logic [TOTAL_DIGITS-1:0][DIGIT_WIDTH-1:0] counts_normalized,
     output logic [TOTAL_DIGITS-1:0]                  at_first_values,
     output logic [TOTAL_DIGITS-1:0]                  at_last_values,
     output logic [TOTAL_DIGITS-1:0]                  at_2nd_last_values,
     output logic [TOTAL_DIGITS-1:0]                  at_4th_last_values,
     output logic [TOTAL_DIGITS-1:0]                  at_first_values_of_multiple,
     output logic [TOTAL_DIGITS-1:0]                  at_last_values_of_multiple,
     logic [OFFSET_WIDTH-1:0]                         totalcount
     );

    logic [TOTAL_DIGITS-1:0][DIGIT_WIDTH-1:0]         digits;

    logic [TOTAL_DIGITS-1:0]                          _carries;
    logic [TOTAL_DIGITS-1:0]                          _at_first_values;
    logic [TOTAL_DIGITS-1:0]                          _at_last_values;
    logic [TOTAL_DIGITS-1:0]                          _at_2nd_last_values;
    logic [TOTAL_DIGITS-1:0]                          _at_4th_last_values;
    logic [TOTAL_DIGITS-1:0]                          _at_first_values_of_multiple;
    logic [TOTAL_DIGITS-1:0]                          _at_last_values_of_multiple;
    logic [DIGIT_WIDTH-1:0]                           _totalcount;

    assign carry_ins = {pre_carries, en};
    localparam                                        DELAY0 = 0;
    `REG(carries, _carries, DELAY0);
    `REG(at_first_values, _at_first_values, DELAY0);
    `REG(at_last_values, _at_last_values, DELAY0);
    `REG(at_2nd_last_values, _at_2nd_last_values, DELAY0);
    `REG(at_4th_last_values, _at_4th_last_values, DELAY0);
    `REG(at_first_values_of_multiple, _at_first_values_of_multiple, DELAY0);
    `REG(at_last_values_of_multiple, _at_last_values_of_multiple, DELAY0);
    `REG(totalcount, _totalcount, DELAY0);
    `REG(counts, digits, DELAY0);

    generate
        for (genvar I = 0; I < TOTAL_DIGITS; I++) begin
            if (I == Tiler::TILE_FILL_MW_DIM) begin
                `_COUNTER(ID);
            end else begin
                `_COUNTER(0);
            end
        end
    endgenerate

    always_comb begin
        _totalcount = offset;
        for (int I = 0; I < Tiler::TOTAL_DIGITS; I++) begin
            _totalcount = _totalcount + digits[I];
        end
    end
endmodule
