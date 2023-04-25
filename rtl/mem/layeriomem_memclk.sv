`include "../top/define.svh"


module layeriomem_memclk
    import Layeriomem::*; import globals::*; import Tiler::*;
    #(type FromTop = logic, `IMPORT_ARITH)
    (fifobus layerio_rd_instruc, layerio_wr_instruc, rdreqfifo,
     qfifo, qinfo_fifo,
     fifo_array_bus dfifos,
     input logic start_, input FromTop fromtop,
     output logic wrote_layerio_layer,
     output logic wrote_inference,
     output DIGIT next_stride_tile_fill_w,
     output DIGIT size_tile_fill_w,
     output DIGIT total_layerio_writes,
     output DIGIT wr_offset,
     output DIGIT rd_offset,
     output logic next_rd_instruc_qvalid,
     output logic rd_instruc_qvalid,
     input logic clk, soft_resetn, resetn, hard_resetn);
`include "layeriomem_memclk_setup.sv"
    `POSEDGE(start, start_);
    assign total_layerio_writes = wrsizes[0];
    assign next_stride_tile_fill_w = next_strides[TILE_FILL_W_DIM];
    assign next_strides = next_rd_instruc_q[TOTAL_DIGITS*2-1:TOTAL_DIGITS];
    assign next_sizes = next_rd_instruc_q[TOTAL_DIGITS-1:0];
    assign sizes = rd_instruc_q[TOTAL_DIGITS-1:0];
    assign wr_offset = wr_instruc_q[TOTAL_PARAMS-1];
    assign rd_offset = rd_instruc_q[TOTAL_PARAMS-1];
    assign strides = rd_instruc_q[TOTAL_DIGITS*2-1:TOTAL_DIGITS];
    `FOR(genvar, I, CLKDIV) begin : connect_fifo_arrays
        assign dfifos_qvalid[I] = dfifos.q.info[I].valid;
        assign dfifos.ios[I].rdclk = clk;
        assign dfifos.rdreq[I] = !dfifos.empty[I] & !wrtilers.full[I];
        assign wrtilers.wrreq[I] = dfifos.q.info[I].valid;
        assign wrtilers.d.value[I] = dfifos.ios[I].q.value;
    end

    `REG(layeriomem_sel_, layeriomem_sel);
    stride_fix #(LAYERIOMEM_CLK_DIV) layeriomem_sel_u
        (.sel(layeriomem_sel), .count(counts[TILE_COUNT_KERNEL_W_DIM]),
         .stride(strides[TILE_FILL_W_DIM]),
         .en(ens[TILE_COUNT_KERNEL_W_DIM]),
         .pre_carry(pre_carries[TILE_COUNT_KERNEL_W_DIM]),
         .clk, .resetn);
    logic [CLKDIV-1:0][$bits(LayeriomemAddress)-1:0] addressmems_d;
    `FOR(genvar, I, CLKDIV) begin
        assign addressmems.rdaddress[I] = tilermems.rdaddress[layeriomem_sel[I]];
        assign addressmems.rdreq[I] = rdtilers.rdreq[layeriomem_sel[I]];
        assign addressmems.wrreq[I] = dfifos_qvalid[I];
        assign addressmems.wraddress[I] = dfifos.q.value[I].addressmem_address;
        if (SIM) assign addressmems_d[I] = dfifos.q.value[I].addressmem_d;
        else assign addressmems.d.value[I] = dfifos.q.value[I].addressmem_d;
        assign layeriomems.rdaddress[I] = addressmems.q.value[I];
    end
    if (SIM) assign addressmems.d.value = addressmems_d;
    `always_ff2 if (~resetn) `FOR(int, I, CLKDIV) layeriomems.rdreq[I] <= '0;
    else `FOR(int, I, CLKDIV) layeriomems.rdreq[I] <= addressmems.rdreq[I];
    assign size_tile_fill_w = sizes[TILE_FILL_W_DIM];
    assign last_rdtiler_in_edgecase = size_tile_fill_w[$clog2(CLKDIV)-1:0]-1;
    DIGIT c_rdreqfifo_rdreqs, c_rdtilers_rdreqs, c_qfifo_dvalids, c_qfifo_wrreqs;
    logic [CLKDIV-1:0] qinfo_dvalids;
    `FOR(genvar, I, CLKDIV) assign
        qinfo_dvalids[I] = qinfo_fifo.d.value[I].valid;
    `SIMCOUNTER(c_rdreqfifo_rdreqs, rdreqfifo.rdreq);
    `SIMCOUNTER(c_rdtilers_rdreqs, $countones(rdtilers.rdreq));
    `SIMCOUNTER(c_qfifo_dvalids, $countones(qinfo_dvalids));
    `SIMCOUNTER(c_qfifo_wrreqs, qfifo.wrreq);
    always_comb begin
        rdreqfifo.rdclk = clk;
        rdreqfifo.rdreq = ~rdreqfifo.empty & rd_instruc_qvalid
                          & fromtop.layer_params_valid;
        `FOR(int, I, CLKDIV) begin
            rdtilers.rdreq[I] = rdreqfifo.q.info.valid;
        end
        if (at_last_values[TILE_FILL_MW_DIM]) begin
            `FOR(int, I, CLKDIV) begin
                if (I > last_rdtiler_in_edgecase)
                    rdtilers.rdreq[I] = 0;
            end
        end
    end
    assign load_rd_instruc = writing_layerio_layer_next;

    QfifoD qfifo_d;
    always_comb begin
        `FOR(int, I, CLKDIV) begin
            qfifo.d.value[qfifo_sel[I]] = qfifo_d[I];
            qinfo_fifo.d.value[I] = qinfo_fifo_d[I];
            qinfo_fifo.d.value[I].valid = qinfo_fifo_dvalids[I];
            if (I != last_rdtiler_in_edgecase) begin
                qinfo_fifo.d.value[I].last_w = '0;
                qinfo_fifo.d.value[I].last_elm = '0;
                qinfo_fifo.d.value[I].last_tile_n_elm = '0;
            end
            if (I > 0) qinfo_fifo.d.value[I].new_tile_k = '0;
        end
        qfifo.wrclk = clk;
        qinfo_fifo.wrclk = clk;
        qfifo.wrreq = qinfo_fifo.d.value[0].valid;
        qinfo_fifo.wrreq = qinfo_fifo.d.value[0].valid;
    end
    localparam DELAY0 = 2;
    `FOR(genvar, I, CLKDIV) begin
        `REG3(qfifo_d[I], qfifo_dI, layeriomems.q.value[I], DELAY0);
        `REG3(qinfo_fifo_d[I], qinfo_fifo_dI, rdtilers.q.info[I], DELAY0);
    end
    `REG(count_, counts[TILE_COUNT_KERNEL_W_DIM],
         rdtilers.RDLATENCY + DELAY0);
    `REG(pre_carry_, pre_carries[TILE_COUNT_KERNEL_W_DIM],
         rdtilers.RDLATENCY + DELAY0);
    `REG(en_, ens[TILE_COUNT_KERNEL_W_DIM], rdtilers.RDLATENCY + DELAY0);
    `REG(qinfo_fifo_dvalids, rdtilers.rdreq, rdtilers.RDLATENCY + DELAY0)
    stride_fix #(LAYERIOMEM_CLK_DIV) qfifo_sel_u
        (.sel(qfifo_sel), .count(count_),
         .stride(strides[TILE_FILL_W_DIM]),
         .en(en_),
         .pre_carry(pre_carry_),
         .clk, .resetn);
endmodule
