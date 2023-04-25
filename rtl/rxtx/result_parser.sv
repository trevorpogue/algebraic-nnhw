`include "../top/define.svh"


module result_parser import globals::*;
    (fifobus result,
     fifo_array_bus results,
     output logic done,
     input logic start, clk, resetn);
    import RxTx::*;
    localparam TOTAL_INPUT_FIFOS = results.I;
    logic [TOTAL_INPUT_FIFOS-1:0] fifo_rdsel, fifo_rdsel_d, fifo_wrsel;
    `ONOFF__(en, start, results.empty[fifo_wrsel] & fifo_rdsel_d == 0);
    `REG(done, fifo_rdsel & !fifo_rdsel_d, 2);
    assign fifo_rdsel_d
        =
          !en? '0:
         results.empty[fifo_rdsel] & (fifo_rdsel
                                      == RxTx::TOTAL_RESULT_FIFOS-1)? '0:
         results.empty[fifo_rdsel]? fifo_rdsel + 1:
          fifo_rdsel;
    localparam                    FIFOS_RDLATENCY = results.RDLATENCY;
    `REG(fifo_rdsel, fifo_rdsel_d);
    `REG(fifo_wrsel, fifo_rdsel, FIFOS_RDLATENCY);
    localparam                    DELAY0 = 1;
    `REG3(result.d.value, result_d, results.q.value[fifo_rdsel], DELAY0);
    logic                         results_qvalid;
    assign results_qvalid = results.q.info[fifo_rdsel].valid;
    `REG3(result.wrreq, result_wrreq, results_qvalid, DELAY0);
    logic [TOTAL_INPUT_FIFOS-1:0]   rdreq_d;
    always_comb begin
        rdreq_d = '0;
        if (en)
            rdreq_d[fifo_rdsel] = !result.half_full;
    end
    `REG3(results.rdreq, rdreq, rdreq_d, DELAY0);
    `CONNECT_FIFO_ARRAY(results, results.I);
    `FOR(genvar, I, RxTx::TOTAL_RESULT_FIFOS) begin
        `IPFIFO_(results.ios[I], resultsI);
    end
endmodule
