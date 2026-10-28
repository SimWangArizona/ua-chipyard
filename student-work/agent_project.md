# Implementation Outline: Fine-Grained Custom Instructions

## 1. Scope and project alignment

Implement the CPU/ISA portion of the ECE 562 proposal, **Specialization Granularity on RISC-V: Custom Instructions versus RoCC Accelerators** (`ece_562_project.pdf`). The deliverables are native Rocket instructions, software interfaces, and basic correctness tests for:

- A four-lane signed packed INT8 dot-product/accumulate operation.
- A fused signed add-min/max operation for dynamic-programming kernels.
- Operand extraction, decode controls, execution logic, and register writeback.

The PDF is the current project reference. The existing `student-work/project_proposal.md` describes an earlier shared-RoCC, two-command design; it should not define the native-instruction implementation. The PDF does not finalize instruction encodings, operand transport, arithmetic widths, or overflow behavior. The choices below are proposed implementation decisions to settle before coding.

The two independent RoCC accelerators and full workload/performance evaluation belong to the other team members. This work supplies a compatible arithmetic contract and native-instruction interface for their integration.

## 2. Existing files to reuse

| Existing file | How it supports this work |
| --- | --- |
| `docs/isa-extension.md` | Native instruction workflow: encoding, decode row, ALU logic, core parameter, configuration, and patch persistence. |
| `course/patches/clamp8/rocket-chip.patch` | Concrete example modifying `CustomInstructions.scala`, `IDecode.scala`, `ALU.scala`, and `RocketCore.scala`. |
| `course/patches/clamp8/Clamp8Config.scala` | Template for enabling a native extension through a student configuration. |
| `course/configs/CourseRocketConfig.scala` | Unchanged `BaselineConfig`: one Rocket core, slow iterative multiplication, no branch predictor/FPU, and small blocking caches. |
| `course/benchmarks/clamp8_test.c` | Template for `.insn` wrappers, reference comparison, directed tests, and PASS/FAIL reporting. |
| `course/benchmarks/Makefile` | Reference cross-compilation, linking, and disassembly settings. |
| `course/benchmarks/metrics.h`, `hpm.h` | Existing measurement interface for integration microbenchmarks. |
| `compose.yaml`, `scripts/course-entrypoint.sh` | Persistent `student-work/` mount and course container startup. |

Rocket implementation sources live inside the container under `/workspace/chipyard/generators/rocket-chip/src/main/scala/rocket/`; they are not included in this local course repository. Inspect the actual container revision before choosing function codes or editing decode controls. Keep custom artifacts in `student-work/`, which maps to `/workspace/student-work`; course files are mounted read-only.

## 3. Define the instruction contract

### Arithmetic semantics

- **DOT4_ACC:** `result32 = wrap32(c + sum(a[i] * b[i]))`, for `i = 0..3`. Each lane is signed INT8; lane `i` occupies bits `[8*i+7 : 8*i]` of its packed 32-bit word.
- **ADD_MAX:** `result32 = max_signed(wrap32(a + b), c)`.
- **ADD_MIN:** `result32 = min_signed(wrap32(a + b), c)`.
- Proposed common contract: signed 32-bit accumulator/DP operands, modulo-2^32 arithmetic, and sign-extension of the final 32-bit result to the RV64 destination register. No saturation. Align this contract with both RoCC owners and the verification owner.
- Specify which upper input bits are ignored, how min/max is selected, and behavior when the destination is `x0`.

### Resolve the three-input requirement

Both operations require three logical inputs, while the existing native R-type example reads only `rs1` and `rs2`. Encoding an `rs3` field or reusing `rd` as an accumulator does not automatically provide a third register-file read port, forwarding, or dependency tracking.

Use a packed two-register interface as the initial implementation candidate:

| Operation | `rs1` contents | `rs2` contents | Output |
| --- | --- | --- | --- |
| DOT4_ACC | `a_packed` in bits 31:0; `c` in bits 63:32 | `b_packed` in bits 31:0; upper bits ignored | Sign-extended `result32` in `rd` |
| ADD_MIN/MAX | `a` in bits 31:0; `c` in bits 63:32 | `b` in bits 31:0; upper bits ignored | Sign-extended `result32` in `rd` |

This permits one native arithmetic instruction using Rocket's existing two source operands. Software packing is additional work: expose it in the wrappers and include it in end-to-end measurements. If a true three-register interface is required instead, revise the plan to include register-file ports, source selection, bypassing, stalls, and instruction encoding; do not assume the clamp8 patch alone supports it.

### Encoding and latency

- Allocate distinct instruction patterns and publish an opcode/funct table for DOT4_ACC and ADD_MIN/MAX. Check overlap with CLAMP8, other enabled instructions, and team RoCC allocations.
- The course native example rejects simultaneous RoCC and native-custom use because the generic RoCC decoder claims custom opcodes. Initially use separate native and RoCC configurations for the proposal's comparisons. Different opcode allocations alone do not remove this decoder conflict; combined support would require explicit decode changes.
- Start with an Execute-stage combinational datapath, subject to elaboration and available timing checks. Four parallel multipliers plus an adder tree may lengthen the critical path. If a multicycle implementation is necessary, specify latency, stall/ready behavior, replay handling, and writeback arbitration before adding it.

## 4. Hardware implementation tasks

| Area | Planned change | Completion condition |
| --- | --- | --- |
| Instruction patterns | Add distinct `BitPat` definitions in `CustomInstructions.scala`. | All intended encodings decode uniquely. |
| Decode | Add rows in `IDecode.scala` that read both sources, select the custom operation, and enable integer destination writeback. | Instructions are legal only when enabled; source dependency controls are correct. |
| Core configuration | Add enable parameters and conditional decode-table entries in `RocketCore.scala`; derive student configurations from `BaselineConfig`. | Baseline remains unchanged; dot-only, DP-only, and both-native configurations elaborate. |
| Operand extraction | Slice packed inputs and explicitly sign-extend INT8 lanes and signed 32-bit fields. | Lane order and signedness match the software contract. |
| Dot-product datapath | Implement four signed 8-by-8 multipliers, width-safe reduction, and accumulator addition. | Products use 16 bits; the exact four-product sum uses at least 18 signed bits; only the specified final result wraps to 32 bits. |
| DP datapath | Add the low 32-bit operands, truncate to 32 bits, then perform signed min/max against `c`. | Overflow occurs before comparison; equal and mixed-sign operands behave correctly. |
| Result selection | Add verified unused ALU function codes and output selection, or a dedicated execution result mux if needed. | Existing ALU behavior is preserved; widths and signed extension are explicit. |
| Pipeline/writeback | Route the custom result through the existing pipeline and integer writeback path. Review bypass, source stalls, flushes, and `rd = x0`. | Dependent instructions receive the right result with no unintended writes or stale operands. |

## 5. Software interface

- Provide C/C++ callable wrappers such as `dot4_acc_hw(a_packed, b_packed, c)`, `add_max_hw(a, b, c)`, and `add_min_hw(a, b, c)`.
- Provide explicit packing helpers using unsigned shifts and masks so signed values do not cause undefined shifts or overflow.
- Emit the finalized encodings with GNU `.insn` inline assembly; use operand constraints that accurately describe source reads and destination writes without unnecessary fixed-register bindings.
- Provide portable reference functions with explicit wraparound semantics. Use unsigned arithmetic or wider intermediates rather than overflowing signed C expressions.
- Keep reference-only execution available on `BaselineConfig`; custom-instruction binaries require a configuration that enables the extension.
- Inspect generated disassembly to confirm field encodings and register operands, and record compiler/optimization settings for reproducibility.

## 6. Basic correctness testing

1. **Dot-product directed cases:** zeros; all-positive/all-negative lanes; mixed signs; single active lanes to verify packing order; `-128` and `127`; positive/negative accumulators; accumulator wraparound.
2. **DP directed cases:** zero and equal operands; positive/negative sums; signed comparison across zero; `INT32_MIN`/`INT32_MAX`; both overflow directions; separate min and max checks.
3. **Deterministic randomized cases:** compare each hardware operation with its reference and report inputs, expected result, actual result, and seed on failure.
4. **Pipeline/register cases:** immediate producer-to-custom dependencies, custom-to-consumer chains, consecutive custom operations, legal source/destination aliases, load-to-custom dependencies, and writes to `x0`. Verify RV64 sign-extension as well as the low 32 bits.
5. **Configuration checks:** extension-disabled encodings take the expected illegal-instruction path; existing integer operations still work when the extension is enabled. Use an appropriate trap test harness for the disabled case.

Start with standalone bare-metal instruction tests modeled on `clamp8_test.c`. Add focused Chisel/datapath tests if supported by the container's existing test infrastructure. Correctness tests must pass before collecting performance data.

## 7. Planned artifacts and handoff

Suggested layout under `student-work/fine-grained/` (these are planned files, not existing implementations):

| Artifact | Purpose |
| --- | --- |
| `isa_spec.md` | Final arithmetic, packing, encoding, latency, and configuration contract. |
| `rocket-chip.patch` | Reapplicable native-instruction changes against the documented container revision. |
| `FineGrainedConfig.scala` | Dot-only, DP-only, and combined native configurations derived from the unchanged baseline. |
| `include/fine_grained.h` | C/C++ wrappers, packing helpers, and reference functions. |
| `tests/fine_grained_test.c` | Directed, randomized, and instruction-level integration checks. |
| `Makefile` | Student-local test build and disassembly targets using the course toolchain settings. |
| `README.md` | Patch application, configuration installation, build/run steps, and known limitations. |
| `results/` | Correctness logs, encoding/disassembly checks, and optional basic microbenchmark results. |

Handoff to teammates: finalized operation semantics, wrappers, input layout, native configurations, reproducible test results, and packing/instruction-count overhead. The benchmark owner can reuse `metrics.h`/`hpm.h` to compare baseline, native, and RoCC versions with identical data and checksums.

## 8. Implementation order and acceptance criteria

1. **Interface specification:** inspect the actual Rocket revision and finalize widths, overflow, third-operand transport, opcode allocation, and min/max support with the team.
2. **Native integration:** follow the clamp8 pattern to add feature gating and decode; implement ADD_MIN/MAX and DOT4_ACC datapaths and result routing.
3. **Software and unit correctness:** build wrappers/reference functions, inspect disassembly, and pass directed/randomized and dependency tests in the appropriate Verilator configurations.
4. **Reproducible handoff:** save the patch and configuration files in persistent storage, verify application to a clean source revision, and document commands and limitations.

The CPU/ISA task is complete when both operation families have explicit semantics, execute correctly through Rocket decode/execution/writeback, are callable from C/C++, pass basic correctness tests, and can be rebuilt from the saved student artifacts. Full application benchmarking and architectural analysis remain shared project integration work.
