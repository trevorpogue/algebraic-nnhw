ddr_emif_ip
    (
     // emif user signals
     .emif_usr_reset_n    (phy.resetn),                 //  output, width = 1
     .emif_usr_clk        (clk),            //  output, width = 1
     .amm_ready_0         (emif_ready),                            //  output, width = 1
     .amm_read_0          (rd_burst_init),
     .amm_write_0         (amm.wrreq),                       //   input, width = 1,   .write
     .amm_address_0       (amm.address),                      //   input, width = 25,  .address
     .amm_readdata_0      (_ammq),                            //  output, width = 576, .readdata
     .amm_writedata_0     (amm.d.value),    //   input, width = 576, .writedata
     .amm_burstcount_0    (BURST_COUNT),             //   input, width = 7,   .burstcount
     .amm_byteenable_0    (72'hffffffffffffffffff),                           //   input, width = 72,  .byteenable
     .amm_readdatavalid_0 (dram_qvalid),             //  output, width = 1,   .readdatavalid

     // DDR PHY IO
     .global_reset_n      (hard_resetn),               //   input, width = 1,  global_reset_n.reset_n
     .pll_ref_clk         (phy.pll_ref_clk),									//   input, width = 1,   pllpll_clk.clk
     .oct_rzqin           (phy.oct_rzqin),                //   input, width = 1,   oct.oct_rzqi++=n
     .mem_ck              (phy.mem_ck        ),						//  output, width = 1,   mem.mem_ck
     .mem_ck_n            (phy.mem_ck_n      ),						//  output, width = 1,   .mem_ck_n
     .mem_a               (phy.mem_a         ),						//  output, width = 17,  .mem_a
     .mem_act_n           (phy.mem_act_n     ),						//  output, width = 1,   .mem_act_n
     .mem_ba              (phy.mem_ba        ),						//  output, width = 2,   .mem_ba
     .mem_bg              (phy.mem_bg        ),						//  output, width = 1,   .mem_bg
     .mem_cke             (phy.mem_cke       ),						//  output, width = 1,   .mem_cke
     .mem_cs_n            (phy.mem_cs_n      ),						//  output, width = 1,   .mem_cs_n
     .mem_odt             (phy.mem_odt       ),						//  output, width = 1,   .mem_odt
     .mem_reset_n         (phy.mem_reset_n   ),						//  output, width = 1,   .mem_reset_n
     .mem_par             (phy.mem_par       ),						//  output, width = 1,   .mem_par
     .mem_alert_n         (phy.mem_alert_n   ),						//   input, width = 1,   .mem_alert_n
     .mem_dqs             (phy.mem_dqs       ),						//   inout, width = 9,   .mem_dqs
     .mem_dqs_n           (phy.mem_dqs_n     ),						//   inout, width = 9,   .mem_dqs_n
     .mem_dq              (phy.mem_dq        ),						//   inout, width = 72,  .mem_dq
     .mem_dbi_n           (phy.mem_dbi_n     ),						//   inout, width = 9,   .mem_dbi_n
     .local_cal_success   (cal_success),							//  output, width = 1,   status.local_cal_success
     .local_cal_fail      (cal_fail)									//  output, width = 1,   .local_cal_fail
     );
