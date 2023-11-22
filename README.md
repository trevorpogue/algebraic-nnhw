This repository contains for reference the core portions of the accelerator RTL and compiler source code developed as part of the following journal publication:

T. E. Pogue and N. Nicolici, "Fast Inner-Product Algorithms and Architectures for Deep Neural Network Accelerators," in IEEE Transactions on Computers, doi: 10.1109/TC.2023.3334140.

https://doi.org/10.1109/TC.2023.3334140

https://arxiv.org/abs/2311.12224

The organization is as follows:
- compiler
  - A compiler for parsing Python model descriptions into accelerator instructions that allow it to accelerate the model. This part also includes code for interfacing with a PCIe driver for initiating model execution on the accelerator, reading back results and performance counters, and testing the correctness of the results.
- rtl
  - Synthesizable SystemVerilog RTL.
- sim
  - Scripts for setting up simulation environments for testing.
- tests
  - UVM-based testbench source code for verifying the accelerator in simulation using Cocotb.
- utils
  - Additional Python packages and scripts used in this project that the author created for general development utilities and aids.
