package Instruc;
    localparam WORD_WIDTH = RxTx::FIFO_WIDTH;
    localparam POST_GEMM_PARAMS_WORD_WIDTH = 64;
    localparam OPCODE_WIDTH = 8;
    localparam BODYLEN_WIDTH = 24;
    localparam HEADER_WIDTH = OPCODE_WIDTH + BODYLEN_WIDTH;
    localparam DATA_FIFO_WIDTH = 512;

    localparam LAYERIO_OPCODE = 0;
    localparam LAYER_PARAMS_OPCODE = LAYERIO_OPCODE+1;
    localparam LAYERIO0_WR_INSTRUC_OPCODE = LAYER_PARAMS_OPCODE+1;
    localparam LAYERIO1_WR_INSTRUC_OPCODE = LAYERIO0_WR_INSTRUC_OPCODE+1;
    localparam LAYERIO2_WR_INSTRUC_OPCODE = LAYERIO1_WR_INSTRUC_OPCODE+1;
    localparam LAYERIO0_RD_INSTRUC_OPCODE = LAYERIO2_WR_INSTRUC_OPCODE+1;
    localparam LAYERIO1_RD_INSTRUC_OPCODE = LAYERIO0_RD_INSTRUC_OPCODE+1;
    localparam LAYERIO2_RD_INSTRUC_OPCODE = LAYERIO1_RD_INSTRUC_OPCODE+1;
    localparam WEIGHT_RD_INSTRUC_OPCODE = LAYERIO2_RD_INSTRUC_OPCODE+1;
    localparam POST_GEMM_PARAMS_RD_INSTRUC_OPCODE =WEIGHT_RD_INSTRUC_OPCODE+1;
    localparam POST_GEMM_PARAMS_OPCODE = POST_GEMM_PARAMS_RD_INSTRUC_OPCODE+1;
    localparam WEIGHT_OPCODE = POST_GEMM_PARAMS_OPCODE+1;
    localparam TOP_INSTRUC_OPCODE = WEIGHT_OPCODE+1;

    localparam TOP_INSTRUC_WIDTH = 2;
    localparam RESET_INSTRUC_MASK = 6;
    localparam RUN_INSTRUC_VALUE = 1;

    localparam TOTAL_OPCODES = 13;
    localparam TOTAL_OUT_FIFOS = TOTAL_OPCODES;

    typedef enum logic [1:0] {IDLE, GET_HEADER, GET_BODY} decoder_statetype;
    typedef logic [OPCODE_WIDTH-1:0] opcodetype;
    typedef logic [BODYLEN_WIDTH-1:0] bodylentype;

    typedef logic [WORD_WIDTH-1:0]    HostData;

    localparam                        M_VAL_WIDTH = 8;
    localparam                        M_VAL_OFFSET = 48;
    localparam                        ZA_BK_WIDTH = 32;
    localparam                        ZA_BK_OFFSET = 16;
    localparam                        ACTIVATION_WIDTH = 2;
    localparam                        ACTIVATION_OFFSET = 14;
    localparam                        M_SHIFT_WIDTH = 6;
    localparam                        M_SHIFT_OFFSET = 8;
    localparam                        ZC_WIDTH = 8;
    localparam                        ZC_OFFSET = 0;
endpackage
