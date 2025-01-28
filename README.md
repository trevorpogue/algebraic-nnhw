# Algebraic Enhancements for GEMM & AI Accelerators
This repository contains the source code for a GEMM & deep learning hardware accelerator system used to validate proposed systolic array hardware architectures that implement under-explored or proposed efficient matrix multiplication algorithms in hardware, to compute the same output with less hardware resources or execution time.
The results achieved:
* Up to 3× faster CNN inference than state-of-the-art accelerators implemented on the same type of compute platform
* \>2× higher mults/multiplier/clock cycle
* Low area, high clock frequency

### Publications & PhD Thesis
The accelerator system was used to validate the systolic array hardware architectures proposed in the following publications:
* [1] &#8202; T. E. Pogue and N. Nicolici, "**Fast Inner-Product Algorithms and Architectures for Deep Neural Network Accelerators**," in IEEE Transactions on Computers, vol. 73, no. 2, pp. 495-509, Feb. 2024, doi: [10.1109/TC.2023.3334140](https://doi.org/10.1109/TC.2023.3334140). Public Full-text: https://arxiv.org/abs/2311.12224
  * Matrix multiplication and deep learning hardware architectures that require **half the multipliers** to achieve the same performance, by executing alternative inner-product algorithms that trade half the multiplications for cheap low-bitwidth additions. The proposed systolic arrays can be seamlessly swapped into existing systolic array systems to double performance per MAC unit with no other functionality or design changes required in the rest of the system and no hidden tradeoffs.
* [2] &#8202; T. E. Pogue and N. Nicolici, "**Karatsuba Matrix Multiplication and its Efficient Custom Hardware Implementations**," in IEEE Transactions on Computers, early access, Jan. 2025, doi: [10.1109/TC.2025.3525606](https://doi.org/10.1109/TC.2025.3525606). Public Full-text: https://arxiv.org/abs/2501.08889,
  * We propose the extension of Karatsuba multiplication to matrix multiplication (KMM) to reduce the complexity of integer matrix multiplication, and we present custom hardware implementations for KMM that provide area or execution time improvements for matrix multiplication and deep learning accelerators
* [3] &#8202; T. E. Pogue and N. Nicolici, "**Strassen Multisystolic Array Hardware Architectures**," in IEEE Transactions on Very Large Scale Integration (VLSI) Systems, early access, Jan. 2025, doi: [10.1109/TVLSI.2025.3530785](https://doi.org/10.1109/TVLSI.2025.3530785). Public Full-text: [Strassen_Multisystolic_Array_Hardware_Architectures.pdf](https://github.com/user-attachments/files/18552609/Strassen_Multisystolic_Array_Hardware_Architectures.pdf)
  * First efficient custom hardware implementations for Strassen's fast matrix multiplication algorithm, which achieve state-of-the-art performance in a deep learning accelerator
* [4] &#8202; T. E. Pogue, "**Algebraic Enhancements for Systolic Arrays**", Ph.D. dissertation, Department of Electrical and Computer Engineering, McMaster University, Hamilton, 2025.  [Online]. Available: https://macsphere.mcmaster.ca/handle/11375/30640
  * Ph.D. thesis covering the above three methods, as well as more background on deep learning acceleration, algebraic enhancements, the presented deep learning accelerator system design, and future work

### Ph.D. Thesis Abstract
The field of deep learning has seen increasing breakthroughs and commercial adoption in recent years for enabling a wide range of applications including image and speech recognition, multimedia generation, information summarization, and human-like chatbots. This has led to a growing need for hardware that can quickly and efficiently perform deep learning inference, which increasingly requires massive amounts of computational power.

To address this need, recent years have seen many works for optimizing deep learning inference in hardware. Systolic arrays are an efficient class of hardware designs to use as a starting point for this application. However, after hardware-oriented deep learning model optimizations reach their limits, after the known parallelism for executing their compute patterns in hardware is exhausted, and after technology scaling slows to a halt, there is an accelerator wall that limits further improvement on the implementation side.

In this thesis, we contribute to this field through an under-explored direction by presenting new efficient matrix multiplication algorithms and/or their systolic array hardware architectures that increase performance-per-area by reducing the workload at the algebraic level, and thus by computing the same result from a re-arranged compute pattern requiring fewer or cheaper operations to be performed in hardware. We evaluate our architectures in an end-to-end deep learning accelerator, demonstrating their ability to increase the performance-per-area of hardware accelerators beyond their normal theoretical limits.

### Why Increase Performance Per MAC?
The majority of the computational workload in deep learning models can commonly be mapped to matrix multiplication, which consists of a series of multiply-accumulate operations. For all deep learning accelerators, unless additional algebraic innovations are used, the throughput is ultimately limited by the maximum number of multiply-accumulate operations that can be performed per clock cycle.
Due to this, deep learning accelerators contain a large number of MAC units, causing multipliers and MAC units to commonly be one of the hardware area-dominant resources in GEMM and deep learning accelerators, and an accelerator's throughput can be directly limited by how many multipliers its hardware budget can afford. For example, in FPGA implementations, the DSP units (which instantiate MAC units) can often run out before the LUT and register resources.

As a result, surpassing this theoretical performance per multiplier limit should be a key area of interest for advancing the field of deep learning acceleration. However, this research direction has been under-explored. In this work, we continue in this under-explored direction by providing algebraic enhancements for matrix multiplication algorithms and their custom hardware implementations for the application of matrix multiplication and deep learning acceleration.

### Scope of Contributions
The contributions in [1]-[4] are relevant for the following scope of applications:
* **Matrix multiplication and deep learning inference**: The proposed systolic array hardware architectures from [1]-[4] improve dense matrix multiplication acceleration in general, and therefore can also be exploited in accelerator systems for accelerating all DNN models/layers that can mainly decompose to matrix multiplication, including fully-connected layers, CNNs, RNNs, and attention layers/transformer models.
* **Fixed-point data types, same numerical stability**: Most of the contributions focus on fixed-point data types and quantized neural network inference, and the presented algorithms/hardware architectures produce identical output as conventional algorithms/architectures and cause no changes to numerical stability.
* **FPGA and ASIC**: Results were validated on FPGA, but the proposed architectures are general and most improvements are applicable to both custom integrated circuit and FPGA implementations
* **Systolic arrays, seamless system integration**: The proposed architectures are systolic arrays, which are an efficient type of design for GEMM & deep learning acceleration (e.g., the Google TPU). It may also be possible to extend some of the concepts to non-systolic array designs in future work. Additionally, they increase performance-per-area but have otherwise identical functionality and interfaces as traditional systolic arrays. I.e., the algebraic enhancements are fully self-contained within the systolic arrays and do not require additional pre or post-processing steps. This means they can be easily/seamlessly swapped with traditional systolic arrays in existing accelerator systems to increase performance per MAC unit with little or no other changes required in the rest of the system and no hidden tradeoffs.

### Results Preview
Synthesis and performance results when combining the architectures from [1] and [3] compared to state-of-the-art accelerators implemented on similar compute platforms achieved up to 3× faster CNN inference, 2× higher mults/multiplier/clock cycle, and \>40% higher clock frequency:

![image](https://github.com/user-attachments/assets/8a29e8a7-744a-4079-a241-d13173342255)
See [[1]](https://arxiv.org/abs/2311.12224), [[2]](https://arxiv.org/abs/2501.08889), [[3]](https://github.com/user-attachments/files/18552609/Strassen_Multisystolic_Array_Hardware_Architectures.pdf), [[4]](https://macsphere.mcmaster.ca/handle/11375/30640) for more results.

#

### Accelerator System Overview

The following diagram shows the deep learning accelerator system implemented in this source code used to host and validate the systolic arrays proposed in [1]-[4]. The system implementation is specialized for performing inference of non-sparse DNN models with fixed-point/quantized inputs consisting of convolutional layers, fully-connected layers, and pooling layers. All DNN layers are fully accelerated in hardware and it can accelerate ML models with arbitrary layer dimensions/kernel sizes all on a single hardware design. Input bitwidths and systolic array dimensions are parametrizable. The system is also a highly-optimized GEMM accelerator in general.

<p align="center"><img src="https://github.com/trevorpogue/algebraic-nnhw/assets/12535207/11a7d485-04a3-4e9d-b9fb-91c35c80086f" width="450"/></p>

System Block Diagram Overview:
* Matrix Multiply Unit (MXU) / systolic array
  * Contains a systolic array architecture for performing matrix multiplication
  * For each method in [1]-[4], different proposed systolic arrays/MXUs are swapped for the MXU in the above system figure
* GEMM Unit
  * Contains the MXU as well as SRAM and addition logic for accumulating matrix tiles to allow GEMM execution of arbitrarily-sized matrices
* Post-GEMM Unit
  * Contains neural network-specific functions to be performed on the matrix multiplication outputs. This includes adding the bias values, inter-layer rescaling for quantization, activation, padding, and pooling.
* Memory Unit
  * Contains memory access control logic and on-chip SRAM memory for holding layer activations
  * Implements efficient caching & memory access HW algorithms, mapping convolution to GEMM in-place without data duplication/delay
  * Uses memory partitioning schemes allowing SRAM memory and control to run at half or quarter clock rate while outputting new data at full clock rate, to improve overall system frequency and power
* Off-chip DDR DRAM memory for weights
* RxTx Unit
  * PCIe interface to host
* Instruction Unit
  * For decoding accelerator instructions sent from the host that allow the system to accelerate ML models with arbitrary layer dimensions/kernel sizes all on a single hardware design

#

### Source Code Overview
- compiler
  - A compiler for parsing Python ML model descriptions into accelerator instructions that allow it to accelerate ML models with arbitrary layer dimensions/kernel sizes. This part also includes code for interfacing with a PCIe driver for initiating model execution on the accelerator, reading back results and performance counters, and testing the correctness of the results
- rtl
  - Synthesizable SystemVerilog accelerator RTL
- sim
  - Scripts for setting up simulation environments for verification
- tests
  - UVM testbench source code for verifying the accelerator in simulation, written in Python and cocotb
- utils
  - Additional Python packages and scripts used in this project created for general development utilities and aids

The files rtl/top/define.svh and rtl/top/pkg.sv contain a number of configurable parameters such as FIP_METHOD in define.svh which defines the systolic array type (e.g., baseline, FIP, or FFIP [1]), SZI and SZJ which define the systolic array height/width, and LAYERIO_WIDTH/WEIGHT_WIDTH which define the input bitwidths.

The directory rtl/arith includes mxu.sv and mac_array.sv which contain the RTL for the baseline and some of the proposed systolic array architectures (FIP and FFIP [1]) depending on the value of the parameter FIP_METHOD.

#

### Additional Documentation
For more documentation on the accelerator system, refer to [[1]](https://arxiv.org/abs/2311.12224) and Chapter 3 from [[4]](https://macsphere.mcmaster.ca/handle/11375/30640). For more details on the proposed systolic array architectures and algebraic enhancements validated in this accelerator system, see [[1]](https://arxiv.org/abs/2311.12224), [[2]](https://arxiv.org/abs/2501.08889), [[3]](https://github.com/user-attachments/files/18552609/Strassen_Multisystolic_Array_Hardware_Architectures.pdf), [[4]](https://macsphere.mcmaster.ca/handle/11375/30640), as well as the [Ph.D. defence slideshow](https://github.com/user-attachments/files/18552009/pogue_trevor_e_november2024_phd_defence.pdf).


<!-- keywords: {Hardware;Systolic arrays;Computer architecture;throughput;performance;Machine learning;Computational modeling;algorithms;hardware acceleration;arithmetic complexity;complexity;parallel processing;Winograd;Karatsuba;Strassen;matrix multiplication;PyTorch;AI;artificial intelligence;ML;machine learning;DL;deep learning;DNN;deep neural network;NN;Large language model;LLM;GPT;transformer} -->
