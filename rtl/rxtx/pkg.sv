`include "../top/define.svh"


package RxTx;
	localparam FIFO_WIDTH = 32;
    localparam RESULT_RESULTS_SEL = 0;
    localparam PERF_RESULTS_SEL = 1;

	localparam TOTAL_RESULT_FIFOS = `USE_RESULT_FIFOS_FULL? 8 : 2;
    localparam A_RESULTS_SEL = 0;
    localparam B_RESULTS_SEL = A_RESULTS_SEL + 1;
    localparam POST_GEMM_PARAMS_RESULTS_SEL = B_RESULTS_SEL + 1;
    localparam GEMM_RESULTS_SEL = POST_GEMM_PARAMS_RESULTS_SEL + 1;
    localparam QUANTIZATION_RESULTS_SEL = GEMM_RESULTS_SEL + 1;
    localparam POOL_PADDING_RESULTS_SEL = QUANTIZATION_RESULTS_SEL + 1;
    localparam POOLING_RESULTS_SEL = POOL_PADDING_RESULTS_SEL + 1;
    localparam C_RESULTS_SEL = POOLING_RESULTS_SEL + 1;
endpackage
