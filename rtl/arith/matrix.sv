`include "../top/define.svh"


interface matrix import globals::*;
    // contains SZI vectors each of size SZJ and vice-versa (transposed)
    // can probe the matrix in both normal or transposed positions

    #(SZI=1, SZJ=1, WIDTH=1, IJMASTER=IMASTER, type INFO=Info)
    (input clk, resetn);
    logic [SZJ-1:0][SZI-1:0][WIDTH-1:0] ivecs;
    logic [SZI-1:0][SZJ-1:0][WIDTH-1:0] jvecs;
    `VEC(SZJ, WIDTH)    top_vec;
    `VEC(SZI, WIDTH)    right_vec;
    INFO info;
    signal #(INFO) info_slave(.*); assign info_slave.value = info;
    signal #(INFO) info_master(.*); assign info = info_master.value;

    assign right_vec = ivecs[0];;
    assign top_vec = jvecs[SZI-1];
    if (IJMASTER == IMASTER)
        `FOR(genvar, I, SZI) begin `FOR(genvar, J, SZJ) begin
            assign jvecs[I][J] = ivecs[J][I];
        end end
    else // (IJMASTER == JMASTER)
        `FOR(genvar, I, SZI) begin `FOR(genvar, J, SZJ) begin
            assign ivecs[J][I] = jvecs[I][J];
        end end
    // in wave viewer, add mat signal below to view entire matrix at
    // once. It is for sim convenience not required for synthesis.
    // It can only be used up to a certain size though due to sim limits
    if (SZI*SZJ <= 64) begin : gmat
        `VECS(SZI, SZJ, WIDTH) mat;
        `FOR(genvar, I, SZI) begin `FOR(genvar, J, SZJ) begin
            assign mat[I][J] = ivecs[J][I];
        end end
    end else begin : gmat
        // if too large to store, still keep signal slot in wave for future
        // sims with smaller feasible sizes
        `VEC (SZJ, WIDTH) mat;
        assign mat = top_vec;
    end
endinterface
