This repository contains the source code for the accelerator that can be parameterized to contain the baseline, FIP, or FFIP MXUs.
The organization is as follows:
- compiler
  - A compiler for parsing Python models into accelerator instructions that allow it to accelerate the model. This part also includes code for running models on the accelerator and reading back results and performance counters.
- rtl
  - Synthesizable SystemVerilog source code for the accelerator.
- sim
  - Scripts for setting up simulation environments for testing.
- tests
  - UVM-based testbench source code for verifying the accelerator in simulation using Cocotb.
- utils
  - Additional Python packages and scripts used in this project that the author created for general development utilities and aids.
