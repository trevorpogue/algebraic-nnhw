`include "../top/define.svh"


module layerio_writer0 import globals::*;
    // This module holds the counter tree for controlling the data
    // access patturns for WEIGHT or LAYERIO data blocks
    import Tiler::*;
    #(RDWR_TYPE, DATA_TYPE, ID, DEPTH, `IMPORT_ARITH)
    (fifobus master, interface slave, fifobus instruc,
     input logic clk, resetn, wrote_layerio_layer,
     output logic load_instruc,
     output logic [TOTAL_DIGITS-1:0] at_2nd_last_values,
     output DIGITS counts,
     output DIGITS sizes_out,
     output Instruc instruc_q_out
     );
    localparam   integer DIV_DEPTH = $ceil(DEPTH/LAYERIOMEM_CLK_DIV);
    DIGIT offset;
    logic [$clog2(DEPTH)-1:0] address;
    logic [$clog2(DEPTH)-1:0] __address;
    logic                     master_req;

    logic                     instruc_valid;
    logic                     _instruc_valid;
    logic                     at_last_elm;
    logic                     instruc_empty;
    logic                     start_or_2nd_last_elm;
    logic                     load_instruc_;
    logic                     init, _init, got_init;
    DIGITS strides;
    DIGITS sizes;
    Instruc instruc_q;
    Instruc _instruc_q;
    logic                     at_2nd_last_value;
    always_comb begin
        __address = address;
        if (offset)
            if (offset == 1)
                __address = $signed(DIV_DEPTH)-$signed(address)-$signed(1);
            else
                __address = $signed(DIV_DEPTH)
                    -$signed({offset>>$clog2(LAYERIOMEM_CLK_DIV)})
                        +$signed(address);
    end
    always_comb begin
        slave.wraddress = $signed(__address);
        slave.wrreq = master.wrreq;
        slave.d.value = master.d.value;
        master.full = ~slave.ready;
        master_req = master.wrreq;
    end

    localparam DELAY0 = 1;
    assign instruc_q_out = instruc_q;
    `REG(instruc_q, _instruc_q, DELAY0);
    `always_comb begin
        offset = instruc_q[TOTAL_DIGITS*2];
    end
    `always_comb begin
        sizes = instruc_q[TOTAL_DIGITS-1:0];
        sizes_out = sizes;
        strides = instruc_q[TOTAL_DIGITS*2-1:TOTAL_DIGITS];
    end
    assign at_2nd_last_values = at_2nd_last_value? '1 : '0;
    counter_digit #($clog2(DEPTH)+1)
    counter_u (.en(master_req),
               .at_2nd_last_value(at_2nd_last_value),
               .size(sizes[0]),
               .stride(strides[0]),
               .stride_normalized(1),
               .count(address),
               .stride_valid(1),
               .clk, .resetn(resetn & !wrote_layerio_layer));
    `ONOFF(got_init, _init, 0);
    `ONOFF(_init, !instruc_empty & !got_init, load_instruc);
    `POSEDGE(init, _init);
    `ACK__(wrote_layerio_layer_ack, wrote_layerio_layer, load_instruc);
    assign load_instruc = (wrote_layerio_layer_ack | init) & !instruc_empty;
    `REG(load_instruc_, load_instruc);
    `ONOFF(start_or_2nd_last_elm, (at_2nd_last_elm), load_instruc_, 0);
    `ONOFF(instruc_valid, load_instruc, at_2nd_last_elm, 2);
    instruc_fields_loader #(TOTAL_PARAMS, DIGIT_WIDTH) instruc_loader_u
        (.instruc, .qvalid(_instruc_valid), .empty(instruc_empty),
         .load(load_instruc), .clk, .resetn, .q(_instruc_q));
    assign at_2nd_last_elm = &at_2nd_last_values & master_req;
endmodule


module layerio_writer_gt0 import globals::*;
    // This module holds the counter tree for controlling the data
    // access patturns for WEIGHT or LAYERIO data blocks
    import Tiler::*;
    #(RDWR_TYPE, DATA_TYPE, ID, DEPTH, `IMPORT_ARITH)
    (fifobus master, interface slave,
     input logic clk, resetn, wrote_layerio_layer,
     output logic load_instruc,
     output DIGITS counts,
     output DIGITS sizes_out,
     input Instruc instruc_q_in);
    localparam   integer DIV_DEPTH = $ceil(DEPTH/LAYERIOMEM_CLK_DIV);
    DIGIT offset;
    logic [$clog2(DEPTH)-1:0] address;
    logic [$clog2(DEPTH)-1:0] __address;
    logic                     master_req;

    logic                     instruc_empty;
    logic                     load_instruc_;
    logic                     init, _init, got_init;
    DIGITS strides;
    DIGITS sizes;
    Instruc instruc_q;
    Instruc _instruc_q;
    always_comb begin
        __address = address;
        if (offset)
            if (offset == 1)
                __address = $signed(DIV_DEPTH)-$signed(address)-$signed(1);
            else
                __address = $signed(DIV_DEPTH)
                    -$signed({offset>>$clog2(LAYERIOMEM_CLK_DIV)})
                        +$signed(address);
    end
    always_comb begin
        slave.wraddress = $signed(__address);
        slave.wrreq = master.wrreq;
        slave.d.value = master.d.value;
        master.full = ~slave.ready;
        master_req = master.wrreq;
    end

    localparam DELAY0 = 0;
    assign instruc_q = instruc_q_in;
    `always_comb begin
        offset = instruc_q[TOTAL_DIGITS*2];
    end
    `always_comb begin
        sizes = instruc_q[TOTAL_DIGITS-1:0];
        sizes_out = sizes;
        strides = instruc_q[TOTAL_DIGITS*2-1:TOTAL_DIGITS];
    end
    counter_digit #($clog2(DEPTH)+1)
    counter_u (.en(master_req),
               .size(sizes[0]),
               .stride(strides[0]),
               .stride_normalized(1),
               .count(address),
               .stride_valid(1),
               .clk, .resetn(resetn & !wrote_layerio_layer));
endmodule


module layerio_reader import globals::*;
    // This module holds the counter tree for controlling the data
    // access patturns for WEIGHT or LAYERIO data blocks
    import Tiler::*;
    #(RDWR_TYPE, DATA_TYPE, ID, DEPTH, `IMPORT_ARITH)
    (fifobus master, interface slave,
     input logic start, clk, resetn, wrote_layerio_layer,
     output logic load_instruc,
     output logic [TOTAL_DIGITS-1:0] at_last_values,
     output DIGITS counts,
     output logic [TOTAL_DIGITS-1:0]  ens,
     output logic [TOTAL_DIGITS-1:0]  pre_carries,
     output logic [TOTAL_DIGITS-1:0]  carries,
     output DIGITS sizes_out,
     input Instruc instruc_q_in,
     input Instruc instruc_q_in_valid,
     output logic at_last_elm
     );
    DIGIT offset;
    logic [$clog2(DEPTH)-1:0] address;
    logic [$clog2(DEPTH)-1:0] __address;
    logic                     master_req;
    logic [TOTAL_DIGITS-1:0]  at_first_values;
    logic                     valid;
    logic                     first_master_req, got_first_master_req;
    DIGITS strides_normalized;
    DIGITS strides;
    DIGITS sizes;
    Instruc instruc_q;
    logic                     at_last_value;
    logic                     stride_valid;
    always_comb begin
        __address = address;
        if (offset)
            if (offset == 1)
                __address = $signed(DEPTH)-$signed(address)-$signed(1);
            else
                __address = $signed(DEPTH)
                    -$signed(offset)
                        +$signed(address);
    end
    always_comb begin
        master_req = master.rdreq;
        slave.rdreq = master_req;
        master.q.value = slave.q.value;
        slave.rdaddress = $signed(__address);
        master.empty = ~slave.ready;
    end

    localparam DELAY0 = 0;
    assign instruc_q = instruc_q_in;
    `always_comb begin
        offset = instruc_q[TOTAL_DIGITS*2];
    end
    `always_comb begin
        sizes = instruc_q[TOTAL_DIGITS-1:0];
        sizes_out = sizes;
        strides = instruc_q[TOTAL_DIGITS*2-1:TOTAL_DIGITS];
        stride_valid = '1;
        `FOR(int, I, TOTAL_DIGITS) begin
            strides_normalized[I] = 1;
        end
        stride_valid = instruc_q_in_valid;
        strides[TILE_FILL_MW_DIM] <<= $clog2(LAYERIOMEM_CLK_DIV);
        strides_normalized[TILE_FILL_MW_DIM]
            <<= $clog2(LAYERIOMEM_CLK_DIV);
    end
    multi_digit_counter #(DIGIT_WIDTH, TOTAL_DIGITS, $clog2(DEPTH), ID)
    counter_u
        (.offset('0),
         .strides(strides),
         .strides_normalized(strides_normalized),
         .sizes(sizes),
         .en(master_req),
         .totalcount(address),
         .stride_valid,
         .counts,
         .carries(carries),
         .pre_carries(pre_carries),
         .carry_ins(ens),
         .at_last_values,
         .at_first_values,
         .clk, .resetn(resetn & !wrote_layerio_layer));
    fifo_info fifo_info_u(master);
    `POSEDGE(first_master_req, master_req & !got_first_master_req, 0);
    `REG__(new_tile_k_off, master.d.info_master.value.new_tile_k & master_req);
    `ONOFF_(master.d.info_master.value.new_tile_k,
            carries[MS_TILE_FILL_DIM] | first_master_req,
            new_tile_k_off, 0, new_tile_k);
    `ONOFF(got_first_master_req, first_master_req, 0);
    assign valid = master_req;
    assign at_last_elm = &at_last_values & valid;
    `always_comb begin
        master.d.info_master.value.last_w = '0;
        if (sizes[TILE_COUNT_MW_DIM] > 1) begin
            master.d.info_master.value.last_w
                = &at_last_values[TILE_COUNT_MW_DIM:0]
                  & valid;
        end else begin
            master.d.info_master.value.last_w
                = &at_last_values[TILE_FILL_MW_DIM:0] & valid;
        end
    end
    assign master.d.info_master.value.last_elm = &at_last_values
                                                 & valid;
    assign master.d.info_master.value.first_tile_k
        = &at_first_values[MS_TILE_COUNT_K_DIM:LS_TILE_COUNT_K_DIM]
          & valid;
    assign master.d.info_master.value.last_tile_k
        = &at_last_values[MS_TILE_COUNT_K_DIM:LS_TILE_COUNT_K_DIM]
          & valid;
    assign master.d.info_master.value.last_tile_n_elm
        = &at_last_values[MS_TILE_COUNT_N_DIM-1:0] & valid;
    assign master.d.info_master.value.valid = valid;
endmodule
