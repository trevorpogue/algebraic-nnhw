`include "../top/define.svh"

module gemm import globals::*;
    #(`IMPORT_ARITH)
    (data a, b, c,
     input logic clk, resetn
     );
    localparam integer MXU_SZJ = SZJ;
    localparam         IN_WIDTH = LAYERIO_WIDTH;
    localparam         OUT_WIDTH = CHAIN_WIDTH;
    localparam         type MXUQ = logic [0:0][MXU_SZJ-1:0][CHAIN_WIDTH-1:0];
    MacJVec accum_mem_q; Info accum_mems_info;
    MXUQ mxu; Info mxus_info;
    mxu_wrapper #(Ajvec, Bivec, MXU,
                  `EXPORT_TOP_(,,MXU_SZJ,,,IN_WIDTH,IN_WIDTH)) mxus_u
        (.c(mxu), .cinfo(mxus_info),
         .a(a), .ainfo(a.info), .b(b), .binfo(b.info), .clk, .resetn);
    accum_mem_wrapper #(MacJVec, MXU, OUT_WIDTH, SZJ, MXU_SZJ,
                        `EXPORT_TOP_(,,MXU_SZJ,,,,,,,,CHAIN_WIDTH))
    accum_mems_u
        (.q(accum_mem_q), .qinfo(accum_mems_info),
         .d(mxu), .dinfo(mxus_info), .clk, .resetn);
    Info _cinfo;
    assign c.info_master.value = _cinfo;
    triangle_buf2 #(.D(Cjvec), .SLOPE(1)) q_u
        (.q(c.value), .qinfo(_cinfo),
         .d(accum_mem_q), .dinfo(accum_mems_info), .clk, .resetn);
endmodule


module mxu_wrapper import globals::*;
    #(type A_, B_, C_, integer `IMPORT_ARITH)
    (output C_ c, Info cinfo, input A_ a, Info ainfo, B_ b, Info binfo,
     logic clk, resetn);
    Chainjvec _mxu; Info _mxuinfo;
    Chainjvec sign_extended_q; Info sign_extended_qinfo;
    mxu #(`EXPORT_ARITH) mxu_u
        (.a(a[MXU_I]), .ainfo(ainfo),
         .b(b[MXU_I]), .binfo(binfo),
         .c(_mxu),
         .cinfo(_mxuinfo),
         .clk, .resetn);
    sign_extender #(Chainjvec, `EXPORT_ARITH) sign_extender_u
        (.q(sign_extended_q), .qinfo(sign_extended_qinfo),
         .d(_mxu), .dinfo(_mxuinfo),
         .clk, .resetn);
    assign c[MXU_I] = sign_extended_q;
    if (MXU_I == 0) assign cinfo = sign_extended_qinfo;
endmodule


module sign_extender import globals::*;
    #(type D, `IMPORT_ARITH)
    (output D q, Info qinfo, input D d, Info dinfo, logic clk, resetn);
    localparam DELAY0 = 0; `REG(qinfo, dinfo, DELAY0);
    localparam integer ABW_OVER2 = A_WIDTH/2;
    localparam integer BBW_OVER2 = B_WIDTH/2;
    `FOR(genvar, I, SZJ) begin
        Chain x;
        Chain y, z;
        assign q[I] = y;
        assign x = d[I];
        `always_comb begin
            y = x;
            z = x;
        end
    end
endmodule


module accum_mem_wrapper import globals::*;
    #(type Q, D, integer OUT_WIDTH, TSZJ, MXU_SZJ, `IMPORT_ARITH)
    (output Q q, Info qinfo, input D d, Info dinfo, logic clk, resetn);
    localparam type __D = logic [0:0][SZJ-1:0][OUT_WIDTH-1:0];
    __D __d; Info __dinfo;
    logic [0:0][SZJ-1:0][ACCUM_WIDTH-1:0] _d; Info _dinfo;
    assign __d = d;
    assign _dinfo = dinfo;
    `SIGNED(assign _d[0][0] =, B_SIGNED, __d[0][0]);
    MacIVec _d_; Info _d_info;
    MacIVec _q; Info _qinfo;
    assign _d_info = _dinfo;
    assign _d_ = _d;
    accum_mem #(MacIVec, `EXPORT_ARITH) accum_mem_u
        (.q(_q), .qinfo(_qinfo), .d(_d_), .dinfo(_d_info), .clk, .resetn);
    assign q = _q;
    assign qinfo = _qinfo;
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
