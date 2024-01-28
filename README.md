This repository contains the source code for ML hardware architectures that require nearly half the number of multiplier units to achieve the same performance, by executing alternative inner-product algorithms that trade nearly half the multiplications for low-bitwidth additions, while still producing identical output as the conventional inner product. See the following journal publication for the full details:

T. E. Pogue and N. Nicolici, "Fast Inner-Product Algorithms and Architectures for Deep Neural Network Accelerators," in IEEE Transactions on Computers, vol. 73, no. 2, pp. 495-509, Feb. 2024, doi: 10.1109/TC.2023.3334140.
<!-- keywords: {Hardware;Systolic arrays;Computer architecture;Throughput;Adders;Machine learning;Computational modeling;Algorithms;hardware acceleration;arithmetic complexity;AI; Artificial Intelligence;Deep learning;DL;ML;Large language model;LLM;Transformer;Neural network;NN;DNN} -->

Article URL: https://ieeexplore.ieee.org/abstract/document/10323219

Open-access version: https://arxiv.org/abs/2311.12224

Abstract: We introduce a new algorithm called the Free-pipeline Fast Inner Product (FFIP) and its hardware architecture that improve an under-explored fast inner-product algorithm (FIP) proposed by Winograd in 1968. Unlike the unrelated Winograd minimal filtering algorithms for convolutional layers, FIP is applicable to all machine learning (ML) model layers that can mainly decompose to matrix multiplication, including fully-connected, convolutional, recurrent, and attention/transformer layers. We implement FIP for the first time in an ML accelerator then present our FFIP algorithm and generalized architecture which inherently improve FIP's clock frequency and, as a consequence, throughput for a similar hardware cost. Finally, we contribute ML-specific optimizations for the FIP and FFIP algorithms and architectures. We show that FFIP can be seamlessly incorporated into traditional fixed-point systolic array ML accelerators to achieve the same throughput with half the number of multiply-accumulate (MAC) units, or it can double the maximum systolic array size that can fit onto devices with a fixed hardware budget. Our FFIP implementation for non-sparse ML models with 8 to 16-bit fixed-point inputs achieves higher throughput and compute efficiency than the best-in-class prior solutions on the same type of compute platform.

The following diagram shows an overview of the ML accelerator system implemented in this source code:
<p align="center"><img src="https://github.com/trevorpogue/algebraic-nnhw/assets/12535207/11a7d485-04a3-4e9d-b9fb-91c35c80086f" width="450"/></p>

The FIP and FFIP systolic array/MXU processing elements (PE)s shown below in (b) and (c) implement the FIP and FFIP inner-product algorithms and each individually provide the same effective computational power as the two baseline PEs shown in (a) combined which implement the baseline inner product as in previous systolic-array ML accelerators:
<p align="center"><img src="https://github.com/trevorpogue/algebraic-nnhw/assets/12535207/d9b956a2-25fa-4173-8ba9-8fd27d02f0c1" width="450"/></p>

The source code organization is as follows:
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

The files rtl/top/define.svh and rtl/top/pkg.sv contain a number of configurable parameters such as FIP_METHOD in define.svh which defines the systolic array type (baseline, FIP, or FFIP), SZI and SZJ which define the systolic array height/width, and LAYERIO_WIDTH/WEIGHT_WIDTH which define the input bitwidths.

The directory rtl/arith includes mxu.sv and mac_array.sv which contain the RTL for the baseline, FIP, and, FFIP systolic array architectures (depending on the value of the parameter FIP_METHOD).
