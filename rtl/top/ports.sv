input logic             CLK_50M_FPGA, //1.8V - 50MHz
                        input             CLK_ENET_FPGA_P,  // 125 MHz
                        input wire [3:0] sw,
                        input wire [3:0] pb,
                        output logic [3:0] led,

                        // DDR4 io
                        output wire [0:0]  mem_ck,
                        output wire [0:0]  mem_ck_n,
                        output wire [16:0] mem_a,
                        output wire [0:0]  mem_act_n,
                        output wire [1:0]  mem_ba,
                        output wire [0:0]  mem_bg,
                        output wire [0:0]  mem_cke,
                        output wire [0:0]  mem_cs_n,
                        output wire [0:0]  mem_odt,
                        output wire [0:0]  mem_reset_n,
                        output wire [0:0]  mem_par,

                        input wire [0:0]   mem_alert_n,
                        input wire         global_reset_reset_n,
                        input wire pll_ref_clk,
                        input wire         oct_rzqin,

                        inout wire [8:0]   mem_dqs,
                        inout wire [8:0]   mem_dqs_n,
                        inout wire [71:0]  mem_dq,
                        inout wire [8:0]   mem_dbi_n,

                        // pcie
                        input        pcie_perstn,
                        input        pcie_refclk,
                        input [7:0]  pcie_rx,
                        output [7:0] pcie_tx,
                        output [3:0] user_led
