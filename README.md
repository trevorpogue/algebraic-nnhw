# Algebraic Methods for Deep Neural Network Accelerator Architectures

This repository contains the source code for a configurable machine learning hardware accelerator being used in the author's PhD research that implements proposed algebraic methods to improve performance and efficiency.

The organization is as follows:
- compiler
  - A compiler for parsing Python descriptions of ML models into accelerator instructions that allow it to accelerate the model.
- rtl
  - The SystemVerilog source code for the accelerator.
- sim
  - Scripts for setting up simulation environments for testing.
- tests
  - Test bench source code for verifying the accelerator in simulation using Cocotb.
- utils
  - Additional Python packages and scripts used in this project that the author created for general development utilities and aids.
