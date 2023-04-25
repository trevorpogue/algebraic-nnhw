`include "../top/define.svh"


module pcie import globals::*;
 (pcie_controller_bus pcie,
                 fifobus rx,
             fifobus tx,
             output logic clk
                 );
    // From the rtl designers perspective, data is sent/received through
    // easy fifo interfaces. From the software developers perspective, data is
    // sent/received through cat commands or, if preferred, a C code driver.
    // it implements direct-memory-access (DMA) with the host and exploits an
    // intel/altera DMA pcie controller IP, then abstracts the interface furthr
    // to the simple interface explained above.
    // See http://xillybus.com/ for more info.

    // Clock and quiesce
    wire        quiesce;

    // Memory array
    reg [7:0]   demoarray[0:31];


    // Wires related to /dev/xillybus_mem_8
    wire        user_r_mem_8_rden;
    wire        user_r_mem_8_empty;
    reg [7:0]   user_r_mem_8_data;
    wire        user_r_mem_8_eof;
    wire        user_r_mem_8_open;
    wire        user_w_mem_8_wren;
    wire        user_w_mem_8_full;
    wire [7:0]  user_w_mem_8_data;
    wire        user_w_mem_8_open;
    wire [4:0]  user_mem_8_addr;
    wire        user_mem_8_addr_update;

    // Wires related to /dev/xillybus_read_32
    wire        user_r_read_32_rden;
    wire        user_r_read_32_empty;
    wire        user_r_read_32_eof;
    wire        user_r_read_32_open;

    // Wires related to /dev/xillybus_read_8
    wire        user_r_read_8_rden;
    wire        user_r_read_8_empty;
    wire [7:0]  user_r_read_8_data;
    wire [7:0]  user_r_read_8_data_mod;
    wire        user_r_read_8_eof;
    wire        user_r_read_8_open;

    // Wires related to /dev/xillybus_write_32
    wire        user_w_write_32_wren;
    wire        user_w_write_32_full;
    wire        user_w_write_32_open;

    // Wires related to /dev/xillybus_write_8
    wire        user_w_write_8_wren;
    wire        user_w_write_8_full;
    wire [7:0]  user_w_write_8_data;
    wire [7:0]  user_w_write_8_data_mod;
    wire        user_w_write_8_open;

    wire [3:0][7:0] user_r_read_32_data;
    wire [3:0][7:0] user_w_write_32_data;
    wire [3:0][7:0] _user_r_read_32_data;
    wire [3:0][7:0] _user_w_write_32_data;
    `FOR(genvar, I, 4) assign _user_w_write_32_data[I]
        = user_w_write_32_data[4-I-1];
    `FOR(genvar, I, 4) assign user_r_read_32_data[I]
        = _user_r_read_32_data[4-I-1];
    //
    assign rx.d.value = _user_w_write_32_data;
    assign _user_r_read_32_data = tx.q.value;
    assign user_w_write_8_data_mod = user_w_write_8_data - 1;
    assign user_r_read_8_data_mod = user_r_read_8_data - 1;

    xillybus xillybus_ins (

                           // tx
                           // Ports related to /dev/xillybus_mem_8
                           // FPGA to CPU signals:
                           .user_r_mem_8_rden(user_r_mem_8_rden),
                           .user_r_mem_8_empty(user_r_mem_8_empty),
                           .user_r_mem_8_data(user_r_mem_8_data),
                           .user_r_mem_8_eof(user_r_mem_8_eof),
                           .user_r_mem_8_open(user_r_mem_8_open),

                           // rx
                           // CPU to FPGA signals:
                           .user_w_mem_8_wren(user_w_mem_8_wren),
                           .user_w_mem_8_full(user_w_mem_8_full),
                           .user_w_mem_8_data(user_w_mem_8_data),
                           .user_w_mem_8_open(user_w_mem_8_open),

                           // Address signals:
                           .user_mem_8_addr(user_mem_8_addr),
                           .user_mem_8_addr_update(user_mem_8_addr_update),

                           // tx
                           // Ports related to /dev/xillybus_read_32
                           // FPGA to CPU signals:
                           .user_r_read_32_rden(tx.rdreq),
                           .user_r_read_32_empty(tx.empty),
                           .user_r_read_32_data(user_r_read_32_data),
                           .user_r_read_32_eof(user_r_read_32_eof),
                           .user_r_read_32_open(user_r_read_32_open),

                           // rx
                           // Ports related to /dev/xillybus_write_32
                           // CPU to FPGA signals:
                           .user_w_write_32_wren(rx.wrreq),
                           .user_w_write_32_full(rx.full),
                           .user_w_write_32_data(user_w_write_32_data),
                           .user_w_write_32_open(user_w_write_32_open),

                           // tx
                           // Ports related to /dev/xillybus_read_8
                           // FPGA to CPU signals:
                           .user_r_read_8_rden(user_r_read_8_rden),
                           .user_r_read_8_empty(user_r_read_8_empty),
                           .user_r_read_8_data(user_r_read_8_data_mod),
                           .user_r_read_8_eof(user_r_read_8_eof),
                           .user_r_read_8_open(user_r_read_8_open),

                           // rxtx
                           // Ports related to /dev/xillybus_write_8
                           // CPU to FPGA signals:
                           .user_w_write_8_wren(user_w_write_8_wren),
                           .user_w_write_8_full(user_w_write_8_full),
                           .user_w_write_8_data(user_w_write_8_data),
                           .user_w_write_8_open(user_w_write_8_open),

                           // Signals to top level
                           .pcie_perstn(pcie.perstn),
                           .pcie_refclk(pcie.refclk),
                           .pcie_rx(pcie.rx),
                           .bus_clk(clk),
                           .pcie_tx(pcie.tx),
                           .quiesce(quiesce),
                           .user_led(pcie.led)
                           );
    // DRAMFIFO
    `IPFIFO(rx);
    `IPFIFO(tx);

    assign  user_r_mem_8_empty = 0;
    assign  user_r_mem_8_eof = 0;
    assign  user_w_mem_8_full = 0;
    assign  user_r_read_8_eof = 0;

    assign  user_r_read_32_eof = 0;
endmodule
