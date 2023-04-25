`include "../top/define.svh"


package Dram;
    localparam SIM_DEPTH = 1<<20;
    localparam SYNTH_DEPTH = 1<<25;
    localparam DEPTH = globals::SIM? SIM_DEPTH : SYNTH_DEPTH;
    localparam WIDTH = 576;
    typedef logic [WIDTH-1:0] Q;
endpackage


package Tiler;
    // NOTE: when updating TOTAL_DIGITS,
    // must also update nnhw.config.TOTAL_DIGITS
    localparam TOTAL_DIGITS = 9;
    localparam TOTAL_PARAMS = TOTAL_DIGITS*2 + 1;
    localparam DIGIT_WIDTH = globals::LAYER_PARAM_WIDTH;
    typedef logic [DIGIT_WIDTH-1:0] DIGIT;
    typedef logic [TOTAL_DIGITS-1:0][DIGIT_WIDTH-1:0] DIGITS;
    typedef enum logic {READER, WRITER} rdwr_type;

    localparam   MS_TILE_FILL_DIM = 2;
    localparam   TILE_FILL_MH_DIM = 2;
    localparam   TILE_FILL_MW_DIM = 1;
    localparam   LS_TILE_COUNT_K_DIM = MS_TILE_FILL_DIM + 1; // 3
    localparam   MS_TILE_COUNT_K_DIM = LS_TILE_COUNT_K_DIM + 2;  // 5
    localparam   TILE_COUNT_MW_DIM = MS_TILE_COUNT_K_DIM + 1;  // 6
    localparam   MS_TILE_COUNT_M_DIM = MS_TILE_COUNT_K_DIM + 2;  // 7
    localparam   MS_TILE_COUNT_N_DIM = MS_TILE_COUNT_M_DIM + 1;  // 8
    localparam   TILE_COUNT_KERNEL_W_DIM = MS_TILE_FILL_DIM + 2;  // 4
    localparam   TILE_COUNT_KERNEL_H_DIM = MS_TILE_FILL_DIM + 1;  // 3
    localparam   TILE_FILL_H_DIM = 2;
    localparam   TILE_FILL_W_DIM = 1;
    localparam   TILE_FILL_CIN_DIM = 0;

	localparam   WEIGHT_TILE_FILL_N_COUT_DIM = 1;

    typedef logic [TOTAL_PARAMS-1:0][DIGIT_WIDTH-1:0] Instruc;
endpackage // mem


package Layeriomem;
    import globals::*;
    import Tiler::*;
endpackage
