`include "../top/define.svh"

module gemm import globals::*;
    #(`IMPORT_ARITH)
    (data a,
     data b,
     data c,
     input LayerParams layer_params,
     input logic clk,
     input logic resetn
     );
    data #(Chainivec) mxu(.*);
    mxu #(`EXPORT_ARITH) mxu_u
      (.a(a.value), .ainfo(a.info), .b(b.value), .binfo(b.value),
       .c(mxu.value), .cinfo(mxu.info_master.value), .clk, .resetn);
    data #(Chainivec) mxu_(.*);
    data #(Civec) mxu__(.*);
    assign mxu__.info_master.value = layer_params.size_w_gemm?
                                     mxu_.info : a.info;
    `FOR(genvar, I, SZI) begin
        Chain x;
        assign x = mxu_.value[I];
        assign mxu__.value[I] = layer_params.size_w_gemm?
                                A_SIGNED? $signed(x) : x
                                : A_SIGNED? $signed(a.value) : a.value;
    end
    data #(Civec) _c(.*);
    triangle_buf #(.SLOPE(-1)) d_u (.q(mxu_), .d(mxu));
    accum_mem #(Civec, `EXPORT_ARITH) accum_mem_u
      (.q(_c.value), .qinfo(_c.info_master.value),
       .d(mxu__.value), .dinfo(mxu__.info), .clk, .resetn);
    triangle_buf #(.SLOPE(1)) q_u (.q(c), .d(_c));
    assign synth_mxu = mxu_.value;
    assign synth_gemm = c.value;
endmodule


module accum_mem import globals::*;
    #(type D, `IMPORT_ARITH)
    (output D q, Info qinfo, input D d, Info dinfo, logic clk, resetn);
    fifobus #(.Q(Civec), .DEPTH(MAX_TILE_SIZE_M)) fifo (.clk, .resetn);
    `IPFIFO_1CLK(fifo);
    localparam   MODULE_LATENCY = SZI;
    Civec sum; Info suminfo;
    Civec _sum; Info _suminfo;
    Civec d_; Info d_info;
    Civec _d; Info _dinfo;
    Civec fifo_q;
    Civec _q;
    Info _info;
    add_vec2 #(Civec, Civec, Civec) add_u
      (.d(d_), .dinfo(d_info), .x(fifo_q), .q(_sum),
       .qinfo(_suminfo),
       .en(!d_info.first_tile_k & d_info.valid), .clk, .resetn);
    localparam   DELAY0 = 1;
    localparam   DELAY1 = 1;
    localparam   DELAY2 = 1;
    localparam   DELAY3 = 1;
    localparam   DELAY4 = 1;  // NOTE: this can be min 3 if using 2clk fifo
    `REG(fifo_q, fifo.q.value, DELAY2);
    `REG(sum, _sum, DELAY0)
    `REG(suminfo, _suminfo, DELAY0)
    `REG(_d, d, DELAY4);
    `REG(_dinfo, dinfo, DELAY4);
    `REG(d_, _d, DELAY2 + DELAY1 + 1);
    `REG(d_info, _dinfo, DELAY2 + DELAY1 + 1);
    `REG_(fifo.rdreq, ~_dinfo.first_tile_k & _dinfo.valid,
          DELAY1, fifo_rdreq_u);
    `REG_(fifo.wrreq, dinfo.first_tile_k?
          ~dinfo.last_tile_k & dinfo.valid & ~fifo.full :
          !suminfo.first_tile_k?
          ~suminfo.last_tile_k & suminfo.valid & ~fifo.full :
          '0,
          DELAY1, fifo_wrreq_u);
    `REG_(fifo.d.value, dinfo.first_tile_k? d : sum,
          DELAY1, fifo_d_u);
    `REG(q, _q, DELAY3);
    `REG(qinfo, _info, DELAY3);
    always_comb begin
        _q = sum;
        `INIT_INFO(_info);
        _info.valid = suminfo.last_tile_k? suminfo.valid : '0;
        if (_info.valid) begin
            `SET_INFO(_info, suminfo);
            _info.new_tile_k = suminfo.last_tile_k?
                               suminfo.new_tile_k : '0;
        end
    end
endmodule
