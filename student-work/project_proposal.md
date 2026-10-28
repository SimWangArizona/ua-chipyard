# Project Proposal: Comparing DP4A and DPX Specialization on RISC-V

## Research Question

This project asks which of two specialized operations provides a larger performance improvement over a minimal RISC-V baseline, and which architectural mechanisms explain the difference. The first operation is a fused four-element signed INT8 dot product, modeled on NVIDIA DP4A:

```text
rd = rs3 + sum(rs1.byte[i] * rs2.byte[i]), i = 0..3
```

The second is a fused add-maximum operation, modeled on NVIDIA DPX:

```text
rd = max(rs1 + rs2, rs3)
```

DP4A targets packed INT8 matrix kernels, while DPX targets dynamic-programming recurrences. Although both operations fuse common arithmetic patterns, they replace different amounts and types of baseline work. In particular, DP4A can eliminate four expensive multiplications, whereas DPX primarily eliminates an addition, comparison, and selection or branch. The project will determine whether this difference in computation saved per invocation produces a corresponding difference in kernel and application speedup.

## Baseline and Proposed Modification

The provided baseline is `BaselineConfig` in `course/configs/CourseRocketConfig.scala`. It contains one in-order, five-stage, 64-bit Rocket core. The configuration has no branch predictor or floating-point unit, uses a deliberately slow iterative multiplier/divider with one-bit unrolling and no early-out, and includes 4 KiB direct-mapped instruction and data caches. The data cache is blocking, and the design has no last-level cache. Eight hardware performance counters are enabled. This configuration is an appropriate reference because it exposes both multiplication latency and control-flow overhead while keeping the rest of the processor fixed.

The proposed modification is a single Rocket Custom Coprocessor (RoCC) module containing two independent arithmetic datapaths. One datapath will perform a four-way signed INT8 multiply followed by an adder tree and 32-bit accumulation. The other will perform a signed 32-bit addition followed by a signed maximum comparison. A function field in the custom instruction will select the operation, while both operations will use the same RoCC command queue and response interface. Sharing the interface avoids confounding the comparison with two different communication mechanisms.

Both target expressions have three source operands, but the standard RoCC command directly supplies only `rs1` and `rs2`; its `rd` field identifies a destination but does not provide the old destination value. The initial implementation will therefore use a two-command protocol. A `SET_ACC` command will first copy `rs3` into an internal accelerator register. A subsequent `DP4A` or `DPX_MAX` command will consume `rs1` and `rs2`, combine them with the stored third operand, and return the result to `rd`. This preserves the mathematical semantics while making the implementation feasible with the existing course RoCC infrastructure. The fixed cost of this protocol will be measured explicitly rather than hidden. If time permits, a packed two-register, single-command interface will be evaluated as an optimization to quantify how much performance is limited by RoCC communication rather than arithmetic.

Three modified processor configurations will be derived from the unchanged `BaselineConfig`: `DP4AConfig`, enabling only DP4A; `DPXConfig`, enabling only DPX; and `DualAccelConfig`, enabling both functions in the shared module. Keeping all core, cache, and memory parameters identical will allow cycle differences to be attributed to the proposed specialization. The dual configuration will be a secondary experiment that tests whether combining the functions introduces interference or overhead; it will not replace the isolated DP4A-versus-DPX comparison.

## Proposed Methodology

The proposed hardware/software evaluation framework is shown below. The benchmark runs as normal RISC-V software on the Rocket core. When the program encounters a custom operation, Rocket sends its decoded operands and function field through the RoCC command interface. The shared accelerator selects either the DP4A or DPX datapath and returns the result through the RoCC response interface for write-back to the RISC-V register file.

```text
                    RISC-V benchmark software
             (INT8 matrix kernel or DP kernel)
                              |
                              | standard and custom instructions
                              v
     +-----------------------------------------------------+
     |                 Baseline Rocket Core                |
     |                                                     |
     |  Fetch -> Decode -> Execute -> Memory -> Write-back |
     |                       |                    ^        |
     |                       | RoCC command       | result |
     +-----------------------|--------------------|--------+
                             v                    |
                 +---------------------------------------+
                 |       Shared RoCC Accelerator         |
                 |                                       |
                 |  Command queue and funct decoder      |
                 |            |              |           |
                 |            v              v           |
                 |   +---------------+  +--------------+  |
                 |   | DP4A datapath |  | DPX datapath |  |
                 |   | 4 x INT8 mul  |  | signed add   |  |
                 |   | + adder tree  |  | + signed max |  |
                 |   +-------+-------+  +------+-------+  |
                 |           +-----------+              |
                 |                       |              |
                 |                response mux          |
                 +-----------------------|--------------+
                                         |
                                         +----> rd

     Performance counters observe cycles, retired instructions,
     branches, multiplier stalls, loads, and cache misses.
```

The core and memory hierarchy remain unchanged between experiments. `DP4AConfig` and `DPXConfig` selectively enable one datapath, while `DualAccelConfig` enables both behind the same RoCC interface. Consequently, the main experimental variable is the specialized operation rather than a change to the processor pipeline or cache organization.

Two workload families will be developed. The DP4A workload will use packed signed INT8 dot products as the inner operation of a matrix-multiplication kernel. Inputs will be packed before the measured region when measuring arithmetic-kernel speedup. A second end-to-end measurement will include packing costs so that the reported application result does not assume free data preparation. The DPX workload will use a dynamic-programming kernel whose recurrence repeatedly evaluates a signed add-maximum expression, such as a grid maximum-path or simplified sequence-alignment recurrence. Each workload will have a portable C reference implementation and an accelerated implementation operating on identical input data.

Correctness will be established before performance is measured. Directed tests will cover zero, positive, negative, and boundary operands, including `INT8_MIN`, `INT8_MAX`, `INT32_MIN`, and `INT32_MAX`. Randomized tests will compare each accelerated result against its C reference. The project will define 32-bit two's-complement wraparound behavior for arithmetic overflow and signed comparison after truncation. Complete benchmark outputs and checksums must match between baseline and accelerated executions.

The primary experiments will use the following controlled comparisons:

| Workload | Reference configuration | Modified configuration | Purpose |
|---|---|---|---|
| INT8 matrix kernel | `BaselineConfig`, C implementation | `DP4AConfig`, accelerated implementation | Measure DP4A benefit |
| Dynamic-programming kernel | `BaselineConfig`, C implementation | `DPXConfig`, accelerated implementation | Measure DPX benefit |
| INT8 matrix kernel | `DP4AConfig` | `DualAccelConfig` | Test combined-design interference |
| Dynamic-programming kernel | `DPXConfig` | `DualAccelConfig` | Test combined-design interference |

Each kernel will be evaluated with at least one small working set intended to fit in the 4 KiB data cache and one larger working set that exceeds it. The small case will emphasize execution and invocation costs; the large case will show whether cache misses and memory traffic limit the attainable application speedup. Measurements will use the existing `metrics.h` and `hpm.h` framework. The main metrics will be elapsed cycles, retired instructions, CPI, load count, multiply count, branch count, multiply/divide stall cycles, branch-direction misses, and instruction- and data-cache misses. Accelerator call count and average cycles per logical operation will also be recorded.

Speedup will be calculated as baseline cycles divided by modified cycles for both the target kernel and the complete benchmark. Retired-instruction reduction and cycles saved per invocation will help separate instruction-count benefits from RoCC overhead. The measured application speedup will also be compared with an Amdahl's-law prediction based on the fraction of baseline time spent in the accelerated region. Multiple runs will be collected for each configuration, with identical binaries and inputs where applicable.

The expected explanation is that DP4A will benefit more from specialization because it replaces four iterative multiplications plus extraction and accumulation instructions. On this baseline, multiplication can generate substantial `md_stall` time. DPX replaces fewer arithmetic instructions, although it may still benefit by eliminating control flow on a processor without branch prediction. If DPX obtains little or no speedup, the invocation latency of the two-command RoCC protocol is a likely mechanism; if both accelerators lose effectiveness on large data sets, increased `dc_miss` behavior would indicate that memory, rather than arithmetic, has become the bottleneck. These measurements will therefore answer not only which operation is faster, but why the observed speedups differ.
