`include "define.svh"


package globals;
    typedef enum logic {FALSE=0, TRUE=1} Bool;
    typedef enum logic {LEFT, RIGHT} Direction;
    typedef enum logic {NEG, POS} Edge;
    typedef enum logic {IMASTER, JMASTER} IJMaster;

`ifdef SIM
    localparam   SIM = TRUE;
    localparam   FMAX = FALSE;
`else
    localparam   SIM = FALSE;
    localparam   FMAX = TRUE;
`endif
`ifdef DUT
    localparam string DUT = `DUT;
`else
    localparam string DUT = "top";
`endif
`ifdef USE_FIFO_IP
    localparam        USE_FIFO_IP = TRUE;
`elsif SIM
    localparam        USE_FIFO_IP = FALSE;
`else
    localparam        USE_FIFO_IP = TRUE;
`endif
`ifdef USE_LAYERIO_DPRAM_IP
    localparam        USE_LAYERIO_DPRAM_IP = TRUE;
`elsif SIM
    localparam        USE_LAYERIO_DPRAM_IP = FALSE;
`else
    localparam        USE_LAYERIO_DPRAM_IP = TRUE;
`endif
    localparam        TOP_CLK_FREQ = 400; // absolute value doesn't matter (just the relative value with the other FREQ params)
    localparam        INSTRUC_CLK_FREQ = TOP_CLK_FREQ/2; // in MHz
    localparam        LAYERIOMEM_CLK_DIV = 2;
    localparam        WEIGHTMEM_CLK_DIV = 2;
    localparam        QUANTIZATION_CLK_FREQ = TOP_CLK_FREQ; // in MHz
    localparam        POOLING_CLK_FREQ = TOP_CLK_FREQ/5; // in MHz
    localparam        PADDING_CLK_FREQ = TOP_CLK_FREQ/2;
    localparam        TOTAL_SOFT_RESETS = 3;

    typedef enum      integer {BASELINE=0, FFIP=1, FIP=2} FIPMethod;
    typedef enum	logic [1:0] {WEIGHT, LAYERIO, POST_GEMM_PARAMS, CType}
					datatype;

	localparam        FMAX_DELAY = FMAX? 8 : 0;
    localparam        PGPBITS = 64;
    typedef logic [PGPBITS-1:0] PostGemmParams;
    typedef logic [PGPBITS-1:0] PGP;
    typedef logic [PGPBITS*WEIGHTMEM_CLK_DIV-1:0] PGP2;
    typedef struct    packed {
        // NOTE: if adding signal here, also update code with TAG:UPDATE_INFO
        logic         last_elm;
        logic         last_tile_n_elm;
        logic         last_w;
        logic         last_tile_k;
        logic         first_tile_k;
        logic         new_tile_k;
        logic         valid;
    } Info;
    localparam        CLOG2_MAX_TIMEOUT = 32;
    localparam                        LAYER_PARAM_WIDTH = 28;
    typedef logic [LAYER_PARAM_WIDTH-1:0] LayerParam;
    typedef struct                        packed {
        logic                             get_results;
        logic                             record_timer;
        logic                             stop_timer;
        logic                             restart_timer;
        logic                             start_timer;
        logic                             load;
        logic [$clog2(CLOG2_MAX_TIMEOUT)-1:0] timeout_bit;
        logic [TOTAL_SOFT_RESETS-1:0]         resets;
        logic                                 run;
    } TopInstruc;

    localparam        DO_POOL_PADDING = FALSE;
    localparam        TILEBUF_RDLATENCY = 5;
    localparam        USE_SMALL_BUF = FALSE;
    localparam        MAX_TILE_SIZE_M = 340;
    localparam        SMALL_BUF_DEPTH = 32;
    localparam        MAX_PADDING = 7;
    localparam        MAX_W = 1<<7;
    localparam        MAX_H = MAX_W;
    localparam        INSTRUC_FIFOS_DEPTH = 512;
    localparam        DRAM_FIFOS_DEPTH = USE_SMALL_BUF? SMALL_BUF_DEPTH
                      : 512;

    localparam        TILE_BUF_DEPTH = 3*(MAX_TILE_SIZE_M+1);
    localparam        RESULT_FIFO_DEPTH = 512;
`ifdef SYNTH_DEBUG
    localparam        SYNTH_DEBUG = TRUE;
`else
    localparam        SYNTH_DEBUG = FALSE;
`endif
    localparam        RESET_FIFO_DEPTH = 4;

    typedef struct    packed {
        logic [31:0]  en;
    } Options;

    localparam        MAX_LAYERS = 128;
    localparam        MAX_A_WIDTH = 16;
    localparam        MAX_POOL_SIZE = 7;
    localparam        MAX_POOL_STRIDE = MAX_POOL_SIZE;
    localparam        MAX_AVGPOOL_DENOM = MAX_POOL_SIZE*MAX_POOL_SIZE;
    typedef enum      integer {MAXPOOL2D=0, AVGPOOL2D=1} PoolType;

    localparam                            INPUTMEM = 0;
    localparam                            LINEAR_MEM = 2;
    localparam           TOTAL_LAYER_PARAMS = 34;
    typedef struct       packed {
        LayerParam new_layer_edge;  // don't count this in TOTAL_LAYER_PARAMS
        LayerParam inputmem_size_w_c;
        LayerParam inputmem_total_layer_reads;
        LayerParam inputmem_tile_size_m;
        LayerParam total_inference_writes;
        LayerParam in_last_inference;
        LayerParam load_input;
        LayerParam tile_size_m;
        LayerParam size_w_gemm;
        LayerParam size_h_gemm;
        LayerParam size_w_pool_padding;
        LayerParam size_h_pool_padding;
        LayerParam size_w_pooling;
        LayerParam size_h_pooling;
        LayerParam total_weight_writes_all_layers;
        LayerParam total_pgp_writes_all_layers;
        LayerParam total_weight_reads_all_layers;
        LayerParam total_pgp_reads_all_layers;
        LayerParam total_layerio_reads;
        LayerParam total_weight_reads;
        LayerParam hw_size_padding;
        LayerParam total_c_padding_writes;
        LayerParam size_w_c;
        LayerParam c_padding;
        LayerParam pool_size;
        LayerParam pool_stride;
        LayerParam pool_padding;
        LayerParam avg_pool_denom;
        LayerParam pool_type;
        LayerParam islastlayer;
        LayerParam islast_inbatch;
        LayerParam layeriomem_wrsel;
        LayerParam layeriomem_rdsel;
        LayerParam loading_params_valid;
        LayerParam valid;
    } LayerParamsFifoQ;

    localparam           _TOTAL_LAYERIOMEMS = 3;
    typedef struct       packed {
        logic new_layer_edge;  // don't count this in TOTAL_LAYER_PARAMS
        LayerParam inputmem_size_w_c;
        LayerParam inputmem_total_layer_reads;
        logic [$clog2(MAX_TILE_SIZE_M)-1:0] inputmem_tile_size_m;
        LayerParam total_inference_writes;
        logic in_last_inference;
        logic load_input;
        logic [$clog2(MAX_TILE_SIZE_M)-1:0] tile_size_m;
        LayerParam size_w_gemm;
        LayerParam size_h_gemm;
        LayerParam size_w_pool_padding;
        LayerParam size_h_pool_padding;
        LayerParam size_w_pooling;
        LayerParam size_h_pooling;
        LayerParam total_weight_writes_all_layers;
        LayerParam total_pgp_writes_all_layers;
        LayerParam total_weight_reads_all_layers;
        LayerParam total_pgp_reads_all_layers;
        LayerParam total_layerio_reads;
        LayerParam total_weight_reads;
        LayerParam hw_size_padding;
        LayerParam total_c_padding_writes;
        LayerParam size_w_c;
        logic [$clog2(MAX_PADDING)-1:0] c_padding;
        logic [$clog2(MAX_POOL_SIZE)-1:0] pool_size;
        logic [$clog2(MAX_POOL_SIZE)-1:0] pool_stride;
        logic [$clog2(MAX_PADDING)-1:0]   pool_padding;
        logic [$clog2(MAX_AVGPOOL_DENOM)-1:0] avg_pool_denom;
        logic [1:0] pool_type;
        logic islastlayer;
        logic islast_inbatch;
        logic [$clog2(_TOTAL_LAYERIOMEMS)-1:0] layeriomem_wrsel;
        logic [$clog2(_TOTAL_LAYERIOMEMS)-1:0] layeriomem_rdsel;
        logic loading_params_valid;
        logic valid;
    } LayerParams;
endpackage
