This repository contains the core portions of the accelerator RTL and compiler source code developed as part of the following journal publication:

T. E. Pogue and N. Nicolici, "Fast Inner-Product Algorithms and Architectures for Deep Neural Network Accelerators," in IEEE Transactions on Computers, vol. 73, no. 2, pp. 495-509, Feb. 2024, doi: 10.1109/TC.2023.3334140.

https://ieeexplore.ieee.org/abstract/document/10323219

https://arxiv.org/abs/2311.12224

We introduce a new algorithm called the Free-pipeline Fast Inner Product (FFIP) and its hardware architecture that improve an under-explored fast inner-product algorithm (FIP) proposed by Winograd in 1968. Unlike the unrelated Winograd minimal filtering algorithms for convolutional layers, FIP is applicable to all machine learning (ML) model layers that can mainly decompose to matrix multiplication, including fully-connected, convolutional, recurrent, and attention/transformer layers. We implement FIP for the first time in an ML accelerator then present our FFIP algorithm and generalized architecture which inherently improve FIP's clock frequency and, as a consequence, throughput for a similar hardware cost. Finally, we contribute ML-specific optimizations for the FIP and FFIP algorithms and architectures. We show that FFIP can be seamlessly incorporated into traditional fixed-point systolic array ML accelerators to achieve the same throughput with half the number of multiply-accumulate (MAC) units, or it can double the maximum systolic array size that can fit onto devices with a fixed hardware budget. Our FFIP implementation for non-sparse ML models with 8 to 16-bit fixed-point inputs achieves higher throughput and compute efficiency than the best-in-class prior solutions on the same type of compute platform.

<p align="center"><img src="https://github.com/trevorpogue/algebraic-nnhw/assets/12535207/11a7d485-04a3-4e9d-b9fb-91c35c80086f" height="770"/> &ensp; <img src="https://github.com/trevorpogue/algebraic-nnhw/assets/12535207/d9b956a2-25fa-4173-8ba9-8fd27d02f0c1" height="770"/></p>


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

\
&nbsp;
\
&nbsp;
  

