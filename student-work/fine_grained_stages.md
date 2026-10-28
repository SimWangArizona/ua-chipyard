# Fine-Grained Instructions: Incremental Implementation and Verification Plan

## Purpose and scope

This plan refines `agent_project.md` into independently verifiable stages for the CPU/ISA work in the current PDF proposal, *Specialization Granularity on RISC-V: Custom Instructions versus RoCC Accelerators*. Its goals are to implement native Rocket packed signed INT8 dot-product/accumulate and fused signed add-min/max instructions, expose C/C++ interfaces, and verify decode, arithmetic, dependencies, and architectural writeback.

The active scope is ordinary baseline software versus fine-grained native instructions. RoCC implementation, tests, and measurements are outside this work. Full application evaluation remains coordinated with the benchmark owner; this work provides baseline/native correctness and measurement interfaces. The older `project_proposal.md` shared-RoCC design is not the implementation contract for this work.

## Existing documentation and components to reuse

Reviewed the local `docs/` guides and corresponding course files on 2026-10-14. The table distinguishes components already used by the scaffold from integrations still to implement. Reading a guide or compiling a test does not establish a hardware PASS.

| Documentation | Existing component / mechanism | Concrete reuse and stage | Current integration |
| --- | --- | --- | --- |
| [Getting started](../docs/getting-started.md) | `env.sh`, persistent `/workspace/student-work`, installed `riscv-tests` | S0: load environment per shell; S3: run `rv64ui-p-simple` on the actual baseline simulator before project tests. | Environment loading used; ISA simulation pending. |
| [Running programs](../docs/running-programs.md) | Chipyard `tests/CMakeLists.txt`, `add_executable`, `add_dump_target`, `hello` example | S2/S3: reuse the toolchain/runtime and disassembly workflow. Keep student tests in the persistent directory; use CMake only if a later test needs Chipyard's existing build integration. | Student-local runner already uses the course compiler/linker conventions; no duplicate CMake pipeline needed. |
| [Benchmarks](../docs/benchmarks.md) | `course/configs/CourseRocketConfig.scala`, `course/benchmarks/Makefile`, `isp_bench.c` | S3: build `BaselineConfig`; S7: execute the same unmodified ISP binary on baseline/native systems and compare `CHECKSUM` as an ordinary-software regression. | Baseline settings and build conventions reused; ISP regression pending. |
| [Performance counters](../docs/performance-counters.md) | `mcycle`, `minstret`; course `metrics.h` and `hpm.h` provide the reusable implementation | S3: establish baseline measurement format; S7: measure equivalent baseline/native regions and compute CPI and cycle speedup on the host. | Headers inspected; current correctness tests are not performance benchmarks. Integration pending. |
| [Custom configurations](../docs/custom-configurations.md) | Config fragments, `++` composition, `make find-configs` | S4/S5/S6: derive DP-only, dot-only, and combined-native configurations from `BaselineConfig`; verify discovery before building. | Planned; native Scala configurations do not exist yet. |
| [Cache configurations](../docs/cache-configurations.md) | Generated system JSON and cache capacity checks | S3/S7: verify actual I/D cache parameters across baseline/native generated systems instead of assuming config composition preserved them. | Planned verification; changing cache size is outside this experiment. |
| [ISA extension](../docs/isa-extension.md) | `course/patches/clamp8/rocket-chip.patch`, `Clamp8Config.scala`, `clamp8_test.c` | S2: `.insn` and reference checking; S4/S5: four-file native implementation pattern, two-source decode, result mux and feature gating; S7: patch persistence/reapplication. | Wrapper/test pattern reused; Rocket hardware changes pending. |
| [Quiz 3 instructions](../docs/quizzes/quiz3_instructions.md) | `scripts/quiz-run`, ISP phase measurements | Optional S3 measurement smoke test; use the ISP phase/checksum convention for regression evidence. | Script inspected; it is specific to baseline ISP, not a general project runner. |
| [Troubleshooting](../docs/troubleshooting.md) | No substantive content in this checkout | Use the troubleshooting section of `isa-extension.md` for patch/configuration mismatch and wrong-simulator diagnosis. | No additional implementation to reuse from the empty guide. |

`docs/rocc.md` was reviewed for interface context only. No RoCC module, runtime, or test is required by this plan.

### Resolve documentation differences using the actual project

- `getting-started.md`, `running-programs.md`, and `custom-configurations.md` use `CourseRocketConfig` for general examples. This proposal and `benchmarks.md` explicitly select **`BaselineConfig`**. Substitute that name in baseline build/run commands; do not accidentally benchmark against the larger course core.
- The general guides discourage edits to Rocket unless required by an assignment. Native ISA implementation is precisely the intended exception demonstrated by `isa-extension.md`: modify the relevant Rocket files through a saved patch, with features disabled by default.
- The actual `scripts/install-course-configs.sh` installs only course Scala files. Explicitly link future student configuration files after the hardware patch exists. Use `make find-configs` to confirm discovery; do not assume restart installs them.
- Some tutorial prose alternates between `tests/` and `tests/build/` output paths. Locate actual generated files before running them. Our runner avoids this ambiguity by writing artifacts to its own timestamped result directory.
- The clamp8 tutorial's simple Execute-stage timing is an implementation example. It does not establish timing feasibility for four multipliers and an accumulator. Preserve the existing timing qualification in S5/S7.

### Reuse the measurement headers rather than writing new counter code

For future baseline/native performance programs, include `metrics.h` with compiler flag `-I/workspace/course/benchmarks`; it includes `hpm.h`. Keep course headers read-only and record their revision or hashes with benchmark evidence.

Use the existing interface as follows (a pattern for future benchmark code, not an already implemented target):

```c
#include "metrics.h"
volatile uint64_t sink;

/* Once during initialization, before measurements: */
hpm_setup();

/* Place each measured region in its own block because macros declare locals. */
{
    BENCH_BEGIN();
    sink = run_kernel_and_return_result(); /* Replace with the actual workload. */
    BENCH_END("dot_sw");
}
```

- `BENCH_BEGIN`/`BENCH_END` sample all counters before printing; reuse that ordering. Define the required `sink`, keep results observable, and inspect optimized assembly so computation is neither removed nor moved outside the intended measurement window. The course CSR helpers are not a general compiler barrier.
- Call `hpm_setup()` once before measurements. `BaselineConfig` already requests eight performance counters; preserve that setting in native configurations.
- Reuse columns `cycles`, `instret`, `branch`, `load`, `mul`, `bp_dir_ms`, `bp_tgt_ms`, `md_stall`, `ic_miss`, and `dc_miss`. Validate event-set ordering against the actual `RocketCore.scala` and event encoding against `CSR.scala` as directed by `hpm.h` before interpreting HPM results.
- The `mul` counter represents existing multiply-instruction events; it does not automatically count each of the four internal products of DOT4_ACC. Track logical custom-operation count separately and do not interpret a falling `mul` count as less mathematical work.
- Measure repeated operations to amortize overhead; `metrics.h` recommends regions above roughly 10,000 cycles. Keep input initialization, correctness comparisons, and printing outside kernel-only regions. Match warm-up policy and measurement boundaries between versions.
- Compute `CPI = cycles / instret` and `cycle_speedup = baseline_cycles / native_cycles` on the host. The course nano runtime does not provide floating-point `printf`, and baseline has no FPU. Label cycle speedup as assuming equal clock period; it is not a demonstrated physical runtime speedup if the added datapath changes the achievable clock.

### Reuse existing software to validate the baseline and ordinary instructions

S3 should first execute the installed integer smoke test after building the baseline:

```bash
cd /workspace/chipyard/sims/verilator
./simulator-chipyard.harness-BaselineConfig \
  "$RISCV/riscv64-unknown-elf/share/riscv-tests/isa/rv64ui-p-simple"
```

For an optional S3 counter smoke test and S7 regression, build the existing ISP program with a persistent output directory:

```bash
mkdir -p /workspace/student-work/fine-grained/results/course-isp
make -C /workspace/course/benchmarks \
  OUTDIR=/workspace/student-work/fine-grained/results/course-isp \
  /workspace/student-work/fine-grained/results/course-isp/isp_bench.riscv
```

Run that same ELF on `BaselineConfig` and, once implemented, `FineGrainedConfig`; retain its hash, outputs, and identical `CHECKSUM` values. This reuses an existing unrelated workload to detect ordinary-software regressions. It does not replace element-by-element validation of the project's INT8 matrix and DP workloads. `quiz-run` currently hardcodes the baseline simulator and `/workspace/output/isp_bench.riscv`, so use direct simulator commands when choosing a native configuration or persistent output path.

### Validate baseline versus native workloads explicitly

The existing unit-test runner is a foundation, not a complete workload comparison. Reuse the benchmark owner's `ece562_benchmark/ece562/` workload and golden implementations in S8; put only native adapters and integration scripts under `fine-grained/benchmarks/`. The following checkpoints describe preparation and final S8 integration, not a requirement to develop duplicate public benchmarks:

| Checkpoint | Required evidence |
| --- | --- |
| S3 preparation / S8 baseline workload | Reuse ordinary C/C++ dot/matrix and DP kernels, fixed shared inputs/seed, compiler flags, ELF hash, and baseline output. Disassemble executable code to confirm no custom opcodes are used. |
| S4/S5 wrappers / S8 accelerated kernels | Call existing native wrappers from equivalent kernel adapters; reuse identical inputs and output layout. Compare every required output value against the supplied golden result, with checksum as supplementary evidence. |
| S8 baseline/native comparison | Use the benchmark owner's common timing interface with matching optimization, dimensions, warm-up, and timing boundaries; coordinate any course-counter integration with that owner. Include native packing/setup costs in the measured kernel and report any separately measured prepacked variant explicitly. |

For baseline regression, the **same ordinary binary** runs on both configurations. For acceleration measurements, **different baseline/native binaries** implement the same computation, because only the native version emits the new instructions. Do not run a custom-instruction workload on baseline except in the dedicated illegal-instruction test.

### Verify generated hardware and reuse builds

- Following `cache-configurations.md`, inspect each configuration's generated JSON under `sims/verilator/generated-src/chipyard.harness.TestHarness.<Config>/`. Check the actual generated filename. Baseline D-cache should report 64 sets, 64-byte blocks, and 4096 bytes, implying one way; verify the I-cache similarly where metadata is available. Review Scala configuration/source for properties not represented in JSON, including multiplier settings and feature gates.
- Follow the rebuild distinction in `benchmarks.md` and `running-programs.md`: software or input changes require only software rebuilds/reruns; Rocket or configuration changes require rebuilding affected simulators. Record which binary and simulator were paired.
- Use `Clamp8Config.scala`'s `RocketCoreConfig(_.copy(...))` plus `new BaselineConfig` pattern to enable only the intended feature fields, rather than constructing a new tile that might silently alter baseline settings.
- Reuse `git apply --check`, tracked patch inspection, and fresh-session reapplication from `isa-extension.md`. Include new files and only this task's changes; the tutorial's broad `git add -A` should not pull unrelated work into the saved patch.
- Current S0–S2 PASS results remain software/environment evidence. Counter integration, generated-JSON checks, ISP/ISA simulation, and complete baseline/native workload measurements listed here are future gates, not work already completed by this documentation review.

## Stable structure: avoid rewriting the project at every stage

- Keep this document as the stable roadmap. Update only a relevant stage if its scope changes.
- Keep arithmetic/encoding decisions in `fine-grained/isa_spec.md`. Encoding constants live in `include/fg_encoding.h`, included by `fg_contract.h` for C/C++; assembly shares the pure encoding header. Other tests must reuse those headers instead of duplicating encodings.
- Keep portable semantics in `include/fg_reference.h`, assembly wrappers in `include/fg_hw.h`, arithmetic tests in `tests/test_arithmetic.c`, and instruction-sequence tests in `tests/test_pipeline.c`.
- Use the same arithmetic vectors first against the reference and then against hardware. `FG_HARDWARE` selects real assembly; it never substitutes a software result for a hardware result. DP-only and dot-only binaries can be built independently.
- Record progress in `fine-grained/STATUS.md`; append evidence and decisions rather than rewriting prior results. The runner creates a new timestamped results directory for every invocation.
- Maintain one cumulative `rocket-chip.patch` against the recorded clean Rocket revision. After a hardware stage, regenerate that patch to include prior stages and new files. Do not stack overlapping snapshots on an already patched tree.
- A stage is complete only when its stated exit criteria are met. A successful compile is not a successful hardware test. Changing the contract invalidates affected downstream results and requires targeted reruns.

## Constraints and implementation rules

1. Use the course RV64 Rocket baseline; retain its cache, core, multiplier, and memory settings for comparisons. Do not edit instructor files in `course/`.
2. Persist student files under `student-work/`. Container source/build changes can disappear when the disposable container exits. Save the patch, configuration source, logs, and exact build commands before exiting.
3. Initial contract: four signed INT8 lanes, signed 32-bit accumulator/DP values, 32-bit wraparound, signed comparison after wrapping, and sign-extended 64-bit writeback. No saturation. The current contract is a candidate for team alignment, not a claim that the PDF specifies these details.
4. Initial operand transport: `rs1 = {c[31:0], a[31:0]}`, `rs2[31:0] = b`; ignore `rs2[63:32]`. This avoids adding a third read port. Software packing costs count in end-to-end measurements.
5. Initial encoding: custom-0, funct3=0, funct7=1/2/3 for DOT4_ACC/ADD_MAX/ADD_MIN. Confirm team allocation before freezing the interface. These patterns overlap Rocket's generic RoCC custom decoder; use separate native and RoCC configurations unless explicit decode partitioning is implemented.
6. Enable new operations conditionally. Reserve distinct ALU controls after inspecting the actual revision; do not assume a function code is safe solely because it is numerically unused.
7. Preserve existing source hazard detection, bypass, stalls, flush, and integer writeback behavior. `rd=x0` must discard the result. Both source registers must be declared as read in decode.
8. Start with combinational execution only if the datapath fits the intended timing budget. Verilator functional success does not prove clock timing or physical area. A multicycle design requires a separate handshake/hazard design review and new tests.
9. Use unsigned bit-pattern manipulation and explicit width conversions in C/C++; signed overflow must not be used to model wrapping arithmetic.
10. Tests must report failures and return nonzero. Missing tools/simulators are BLOCKED, not PASS. Simulator timeouts are failures, not proof of an illegal-instruction trap.
11. Do not overwrite unrelated student work or automatically reset/apply patches over a dirty Rocket tree. Record source revision and changes with test results.

## Stage map

| Stage | Work and files primarily affected | Validation gate | Exit criterion |
| --- | --- | --- | --- |
| S0: Environment | Inspect Docker mount, tools, Rocket revision, existing modifications, decode, and ALU controls. | `make env` | Required tools execute and inspected source revision is recorded. This does not imply a simulator exists. |
| S1: Arithmetic contract | `isa_spec.md`, `fg_contract.h`, `fg_reference.h`, arithmetic tests. | `make reference` | Directed vectors and deterministic random comparisons pass in C and C++, at O0/O2 with undefined-behavior checking. Team agreement is a separate prerequisite to freezing v1. |
| S2: Software encoding | `fg_hw.h`, `encoding_probe.c`; compile all future test binaries. | `make wrappers` | C/C++ wrappers compile at O0/O2; O2 object instruction fields are verified; all bare-metal test binaries link. Hardware execution remains unverified. |
| S3: Baseline simulation | Build the unchanged `BaselineConfig`; run reference-only tests on Rocket. | `make baseline` | The actual baseline simulator exits successfully with `FG PASS reference`. |
| S4: DP instruction | Feature parameter/config, ADD_MIN/MAX patterns, two-source decode, packed extraction, adder, signed compare, output mux; focused tests in `test_dp.c`. | `make dp` and `make dp-pipeline` | Both DP operations execute on `FineGrainedDPConfig`, pass known-answer/boundary/random cases and basic dependencies, preserve upper-input ignoring, and produce full sign-extended writeback. |
| S5: Dot instruction | DOT4_ACC decode, four signed multipliers, width-safe reduction/accumulation, dot-only config, focused `test_dot.c`; preserve S4 in cumulative patch. | `make dot`, `make dot-pipeline`; `build_s5.py` also rebuilds/retests S4. | `FineGrainedDotConfig` passes lane/sign/extrema/wrap/random/raw-writeback checks and basic dependencies; S4 arithmetic and dependency regression remain passing. |
| S6: Pipeline integration | Combined native configuration; link focused dot/DP suites in one program and add cross-family dependency chains. | `make all-hw` (focused default) and `make pipeline` | Both families work together: 2,964 arithmetic checks and 23 pipeline checks including mixed dot/min/max chains pass on the combined core. |
| S7: Reproducibility and regression | Saved patch/configs, weak-HTIF trap harness, installed ISA regressions, clean-checkout patch replay and fresh-output reproduction. | `make s7-build`; repeat subsets with `make s7-isa` / `make s7-traps`. | 16 selected ISA runs and 32 feature-gate probes pass; patch replay reproduces sources; fresh RTL/C++ build passes focused arithmetic/pipeline gates; instructions/logs are documented. |
| S8: Common benchmark integration | Reuse `ece562_benchmark/ece562/`; add native `dot_custom`/`dp_custom` adapters and RV64 build/run integration under student storage. | PASS: 24 simulator cases, 108 measured records and 36 verified warm-ups; see `fine-grained/benchmark_report.md`. | All six supplied sizes passed for both workloads; custom encodings are present; inputs/results match baseline; configuration-labelled measurements and reports are retained. |

S0 -> S1 -> S2 -> S3 precedes hardware integration. S4 and S5 share the contract and decode infrastructure but can be developed separately. S6 requires both; S7 closes instruction regression/reproduction. S8 requires S3-S6 and uses the reproducible artifacts from S7 for the final benchmark handoff; baseline-only benchmark preparation can begin earlier. Existing stage numbers remain unchanged. No phase requires rewriting the entire test program or roadmap.

2026-10-14 exception authorized by user: defer the long S3 reference simulation
after the baseline ISA smoke test ran to normal finish, and proceed to S4. S3
remains unpassed; complete a focused baseline smoke/reference gate before final
baseline/native comparisons. This exception does not waive S4 hardware tests.

## Detailed hardware checkpoints

### S4: First native implementation (DP)

1. Inspect `CustomInstructions.scala`, `IDecode.scala`, `ALU.scala`, and `RocketCore.scala` in `/workspace/chipyard/generators/rocket-chip/src/main/scala/rocket/`.
2. Add feature gating and nonoverlapping native patterns. Follow `course/patches/clamp8/rocket-chip.patch`, but enable both register reads and preserve the full 64-bit packed input.
3. Extract `a`, `b`, and `c`; form the 32-bit sum before signed comparison. Do not compare a widened untruncated sum.
4. Route the sign-extended result to ordinary integer writeback. Derive `FineGrainedDPConfig` from `BaselineConfig` without changing unrelated parameters.
5. Build the simulator and run `make dp`. Fix failures within the DP implementation; keep existing contract and wrapper tests as regression gates.

S4 implementation artifacts are `fine-grained/rocket-chip.patch`,
`FineGrainedConfig.scala`, and `scripts/install_s4.py`. The installer applies the
saved patch and links the config; it does not reset dirty sources. Run it after
`source env.sh`, then build `FineGrainedDPConfig`. `make dp` now runs a focused
suite of 15 known-answer triples, 125 boundary triples and 128 random triples,
checking raw results, ignored high bits, and C wrappers (1,608 checks). Run
`make dp-pipeline` for 14 basic DP-only dependency/writeback checks; full combined
pipeline regression stays in S6. Increase random coverage via
`python3 scripts/verify.py dp --random-cases 2000 --timeout 600` when needed.

### S5: Dot implementation

1. Reuse the two-source packing/decode infrastructure. Enable `FineGrainedDotConfig` independently of DP.
2. Extract four signed 8-bit lanes from each packed word. Use 16-bit signed products and at least an 18-bit signed four-product sum.
3. Add the signed accumulator with adequate intermediate width, truncate the final result to 32 bits, and sign-extend to RV64.
4. Build and run `make dot`; verify negative lanes, distinct lane positions, all `-128` products, and accumulator overflow.

S5 implementation uses ALU code 21, an independent `useFineGrainedDot` gate,
16-bit signed products, two 17-bit pair sums, an 18-bit dot sum and a 33-bit
accumulator sum before truncation. DP gate/semantics remain independent.
`FineGrainedDotConfig` enables only dot hardware; `FineGrainedConfig` is defined
for the later S6 combined gate.

Install/upgrade using `fine-grained/scripts/install_s5.py`. The current
`rocket-chip.patch` contains both S4/S5; `patches/s4.patch` preserves S4 history.
Do not apply both patches sequentially. A fresh container needs only the
cumulative patch and student configuration link. The installer checks the base
revision, refuses unrelated changes and verifies clean-base patch reproduction.

Run `python3 /workspace/student-work/fine-grained/scripts/build_s5.py` after
loading the environment. It limits JVM heap/processor resources, builds dot-only,
runs dot arithmetic/dependency gates, then rebuilds/retests DP-only. The final
`S5 PASS` requires all six steps; repeated tests do not require a rebuild when
hardware is unchanged.

`make dot` runs 339 input triples (15 known answers, 16 lane-position pairs,
180 packed-pattern/accumulator combinations and 128 seeded random triples), with
1,356 checks including raw 64-bit results and public wrappers. The known cases
include +65536 reduction and both accumulator overflow directions. Host vector
validation uses an independent wide oracle; hardware mode always executes real
assembly. `make dot-pipeline` adds seven adjacent producer/consumer, alias, x0,
load-use, consecutive-custom and flush checks. `test_arithmetic.c` retains the
larger suite for S6; combined validation is still a separate gate.

### S6 and S7: Architectural behavior and final handoff

- Build `FineGrainedConfig` enabling both native families, then run both arithmetic and pipeline gates.
- Default `all-hw` links `test_all.c`, `test_dot.c`, and `test_dp.c` into one combined-core test with 128 random triples per family. This replaces the slow default repetition of the original large software-reference suite; it does not waive instruction-level known-answer/boundary/random checks. Default timeout is 600 seconds for this gate. The original suite remains available as `python3 scripts/verify.py all-hw --full --timeout 1800`; an earlier timeout remains recorded and is not labelled PASS.
- Combined `pipeline` includes the 21 per-family checks plus two adjacent dot/min/max dependency chains (positive and negative results), for 23 checks. The dot-only and DP-only gates retain 7 and 14 checks respectively. No hardware rebuild is required for this test-only change.
- `test_pipeline.c` uses single assembly blocks to enforce adjacency; ordinary C expressions alone cannot guarantee the intended hazard sequence.
- S7 trap harness is implemented in `test_traps.c`/`trap_probes.S` using the installed HTIF weak handler and verified four-argument ABI. Check `mcause == 2`, exact PC/instruction, trap counts, destination preservation and recovery by four-byte PC advance. A hang or timeout does not satisfy it. Actual PASS evidence is recorded in `STATUS.md`.
- Run applicable existing `rv64ui`/`rv64um` ISA tests on baseline and combined-native simulators; record exactly which tests ran. Add replay/multicycle tests if the execution design introduces those mechanisms.
- Reapply the cumulative patch to a clean checkout of the recorded base revision, install student configurations, rebuild, and repeat the relevant gates. Include new source files in the patch without staging unrelated changes.
- Document functional latency separately from unmeasured physical timing. Provide wrappers, semantics, baseline/native results, and packing overhead details to the benchmark owner.

S7 commands: `make s7-build` builds missing BaselineConfig and a combined
simulator in a new private output directory, then runs regression/reproduction.
Shared Scala/toolchain caches are reused; prior validated outputs and working
sources are preserved. `make s7-isa` selects eight installed integer/branch/load/
store/multiply/divide binaries on baseline and combined (16 runs).
`make s7-traps` executes eight controlled probes on each of baseline, dot-only,
DP-only and combined; expected trap counts are 8/6/4/2 respectively. Wrong funct3
and unallocated funct7 remain illegal on every configuration. `make s7` repeats
all gates with the fresh simulator path recorded under `build/`; a new container
must rebuild missing ephemeral binaries rather than treating past logs as new
execution evidence. `verify_s7.py --part patch` uses a full clean detached Rocket
checkout, applies the saved patch and checks file equality without resetting the
working source. Cold regeneration of the entire Chipyard toolchain is not part
of this gate; physical timing and complete ISA coverage remain unmeasured.

### S8: Verify native instructions with the supplied common benchmark

**Status:** PASS. Native adapters and `scripts/benchmark_s8.py` completed all 24 simulator cases for N=1,4,7,8,16,32, retaining 108 measured records and 36 verified warm-ups. Independent references checked 33,840 output elements. Evidence: `fine-grained/results/20261015T002635Z-s8/result.json`; full report: `fine-grained/benchmark_report.md`. N=32 INT8 speedup is 1.890x; DP speedup is 0.713x (a slowdown). Correctness passed independently of speedup. This stage integrates the instruction owner's code into the benchmark owner's infrastructure; it does not take over public baseline, golden-model, or reporting development. RoCC is outside scope.

**Source:** [ece562_benchmark/ece562](../ece562_benchmark/ece562/). Preserve the supplied files and record their revision or hashes. This host directory is not mounted by the current `compose.yaml`; explicitly copy a versioned snapshot into `/workspace/student-work/fine-grained/benchmarks/common/` or add an agreed read-only mount before container builds. Do not assume a `/workspace/ece562_benchmark` path exists.

| Supplied file | Reuse in this stage |
| --- | --- |
| `bench.h` | Existing `dot_custom` and `dp_custom` interface, row-major square matrices, `MAX_N=32`, and `INF=999`. |
| `dot_bench.c` | Unmodified ordinary-C INT8 matrix-multiplication baseline. |
| `dp_bench.c` | Unmodified Floyd-Warshall baseline with guarded INF arithmetic. |
| `benchmark.c` | Fixed input generation, independent INT64 matrix/Dijkstra references, elementwise checks, warm-up, trials, checksums, and CSV output. |
| `Makefile` | `ECE562_CUSTOM` via `CPPFLAGS` and adapter files via `EXTRA_SOURCES`; retain a separate RV64 build recipe rather than silently using the default host compiler. |
| `run_benchmarks.py` | Common CSV aggregation and median reports; coordinate any Rocket-portability changes with its owner. |
| `host_report.md` | Existing host baseline evidence only; not proof of Rocket/custom correctness. |

Implemented execution path (2026-10-14): `make s8` runs `scripts/benchmark_s8.py`.
The source snapshot is byte-identical to the supplied seven files, verified in
`benchmarks/source_provenance.json`. The integration generates and saves a
compatibility patch: per-size specialization, an input fingerprint, removal of
floating CPI formatting, and `%zu` -> `%lu` for course nano printf. Each workload
runs on the combined native core in a separate process for resumability rather
than one long integrated executable. All six sizes, one warm-up and three trials
are retained, including the native core's ordinary-software control. SimDRAM
`+loadmem` accelerates unmeasured ELF loading; normal/fast N=1/N=4 controls are
retained and compared exactly by `scripts/calibrate_s8_loadmem.py`. Primary
captures use the same fast-loading policy. `scripts/progress_s8.py <run-dir>`
writes `benchmark_progress.md`, explicitly labelled partial, while long tests
run. The final `benchmark_report.md` is generated after the whole matrix.

#### S8.1: Native workload adapters

Create `fine-grained/benchmarks/native_kernels.c` implementing exactly:

```c
void dot_custom(size_t n, const int8_t *a,
                const int8_t *b, int32_t *out);
void dp_custom(size_t n, int32_t *path);
```

- `dot_custom`: retain matrix indexing; pack four consecutive elements of A's row and four corresponding elements of B's column; call `dot4_acc_hw` with the current accumulator. B-column values are strided, so four consecutive memory bytes are not the correct vector. Handle `n % 4` by zero-padding unused lanes or an explicitly documented scalar tail. Sizes 1 and 7 exercise tail handling; n=1 requires no DOT4 invocation if a scalar tail is chosen, so prove actual custom execution with larger sizes.
- `dp_custom`: preserve the baseline k/i/j order and the `a != INF && b != INF` guard; replace the candidate/update pair with `add_min_hw(a,b,current)`. Do not remove the sentinel guard merely because the native instruction can perform addition.
- Use `fg_hw.h` and its unsigned packing/sign conversion helpers; convert results to the signed `int32_t` output representation safely. All supplied matrix sums fit INT32 for n<=32, so wrapping and exact results agree on these inputs.
- Provide both adapter functions when building the shared driver, unless separately verified build specialization removes the unused references. Build with `ECE562_CUSTOM`, never `ECE562_ROCC`, and never substitute reference functions for hardware wrappers.

#### S8.2: RV64 runtime and measurement prerequisites

1. Build a baseline-only ELF without `ECE562_CUSTOM`; build a baseline-plus-custom ELF with the adapters. Use the course cross-compiler/HTIF runtime and matching optimization settings, retaining the supplied `-fno-tree-vectorize` policy. Use separate output directories or force a rebuild when flags/sources change: the supplied Makefile does not track command-line flag changes.
2. Enable `ECE562_RISCV_COUNTERS` to avoid the POSIX `clock_gettime` host path. Verify access to `cycle`/`instret` CSRs in the actual runtime; if necessary agree on machine-mode CSR reads with the benchmark owner.
3. Before Rocket runs, remove target-side floating-point CPI calculation/printing in the integration copy with an explicit recorded compatibility patch. Baseline has no FPU and the course nano runtime lacks floating-point printf. Output integer cycles/instructions and compute CPI on the host; update the shared reporting path with the owner's agreement so a blank target CPI does not produce a blank final report.
4. Confirm integer CSV formatting works with the actual HTIF library. Keep input/golden generation, reset/copy operations, verification, checksum calculation, and printing outside the timed invocation as the supplied driver does. Retain its memory/compiler ordering and synchronous-return requirement for the adapters.
5. Keep all packing performed inside a native adapter within the measured call. If exploring prepacking, report preparation cost and separate kernel-only/end-to-end regions explicitly with an equivalent baseline boundary. Do not mix course `BENCH_END` table output into the common CSV without a parser change.

#### S8.3: Correctness and actual-instruction execution

Run the baseline-only ELF on `BaselineConfig`; run the custom-enabled ELF on the corresponding native configuration. Start with dot-only/DP-only workload programs and their matching configurations, then run the integrated program on `FineGrainedConfig`. Do not execute a custom-enabled program on BaselineConfig except in the dedicated trap test.

- Reuse sizes **1, 4, 7, 8, 16, 32**, the dot seed **562**, DP graph construction, and default **TRIALS=3**. Every warm-up and measured invocation must match every golden output element.
- Expected default measured records: baseline integrated run = **36 rows** (2 workloads x 6 sizes x 3 trials); baseline-plus-custom integrated run = **72 rows**. Warm-ups are checked but not output as trial rows. Treat missing rows, failed warm-ups, nonzero exits, timeouts, or FAIL status as failure; retain process exit status as well as CSV.
- Inspect executable disassembly: baseline-only code must contain no allocated custom instructions; native adapters must contain the intended DOT4_ACC/ADD_MIN fields. Successful output alone is insufficient if an adapter accidentally calls the ordinary baseline.
- Compare the standalone baseline results with baseline rows and custom rows from the native run. Verify identical input data (input hashes or a diagnostic capture outside timing), every output element, and matching per-workload/per-size checksums; retain the benchmark source hash establishing the shared generator.
- This DP workload exercises **ADD_MIN only**. Keep ADD_MAX unit tests from S4/S6 mandatory. Keep existing signed-overflow, negative-DP, raw 64-bit sign-extension, aliases, stalls, and flush tests: this workload suite does not cover them fully.

#### S8.4: Evidence and acceptance

Save timestamped logs, raw CSVs, compatibility patch, adapter source, exact commands/flags, workload source hashes, ELF/simulator hashes, configuration names, and elementwise correctness outcomes under `fine-grained/results/`. Host timing is not Rocket-cycle evidence.

Coordinate with the benchmark owner to merge baseline/native captures or otherwise provide paired data to `run_benchmarks.py --csv`. Its input must be clean CSV; remove simulator messages without losing raw logs. The current `platform=rocket_rv64` field does not identify configuration, so attach an explicit configuration manifest or extend the agreed schema. Check cross-implementation checksum equality even when cycle fields are absent; the current reporter performs that particular comparison only in its cycle-speedup branch.

Report median cycles/instructions, host-computed CPI, and baseline/native cycle speedup for every size. The native run's internal baseline rows are a useful secondary control; the primary reference remains ordinary software on **BaselineConfig**, not software on the modified core. Match warm-up and trial policy, and disclose fixed implementation ordering/cache effects and counter overhead for tiny cases.

**Exit criterion:** complete default baseline/custom records; all elementwise checks and cross-run input/output comparisons pass; real custom encodings are present and execute on Rocket; ADD_MAX and instruction-level regressions remain passing; paired measurements and reports are configuration-labelled and reproducible. No performance improvement is required to pass correctness, and no speedup is claimed before measurement.

**Responsibility boundary:** the instruction owner supplies adapters, native build/configuration details, and instruction-level debugging. The benchmark owner maintains common datasets, golden models, workload policy, CSV/reporting infrastructure, and the shared measurement methodology. Register S8 in `STATUS.md` when integration starts. Run `make s8` (alias `make benchmark`) after sourcing the container environment. The runner compiles separate workload/size binaries to preserve completed cases and allow `make s8 RESUME=/workspace/student-work/fine-grained/results/<timestamp>-s8`. Both workloads run on the combined native configuration; all three trials and one warm-up are retained.

## Running the existing test harness

Inside the running Docker container:

```bash
cd /workspace/chipyard
source env.sh
cd /workspace/student-work/fine-grained
make software       # S0 + S1 + S2; no simulator build required
make baseline       # S3, after building BaselineConfig
make dp             # S4, after implementing/building FineGrainedDPConfig
make dp-pipeline    # S4 DP-only dependency checks on FineGrainedDPConfig
make dot            # S5, after implementing/building FineGrainedDotConfig
make dot-pipeline   # S5 dot-only dependencies on FineGrainedDotConfig
make all-hw         # S6 arithmetic on FineGrainedConfig
make pipeline       # S6 architectural sequences on FineGrainedConfig
```

To build baseline, run `make CONFIG=BaselineConfig` in `/workspace/chipyard/sims/verilator`. Hardware configurations and their Scala files are future stage deliverables. The current local `scripts/install-course-configs.sh` links only `course/configs/*.scala`; it does **not** automatically install student configurations despite the broader README description. When a student configuration is created, explicitly link it into `/workspace/chipyard/generators/chipyard/src/main/scala/config/` before building.

The runner can use an explicitly selected simulator and timeout:

```bash
python3 scripts/verify.py dp --simulator /absolute/path/to/simulator --timeout 600
```

Each run writes live subprocess output to `results/<UTC timestamp>-<stage>/run.log`, per-command logs, `result.json`, build artifacts, and a snapshot of tracked Rocket changes. JSON includes commands, source hashes, revision/status, and simulator hash when applicable. Directory timestamps are UTC; status notes use the project date. Timeouts terminate the subprocess group; keyboard interruption records INTERRUPTED. Generated results are git-ignored; preserve selected evidence deliberately for the final handoff.

Runner exit codes: 0 = PASS, 1 = FAIL, 2 = BLOCKED. GNU Make may translate a failing recipe to its own nonzero status; consult `result.json` for the exact gate outcome. The runner never installs hardware or automatically compiles a large simulator as a side effect of checking for one.

## Updating progress

After each stage, update only its row in `fine-grained/STATUS.md` and append a short entry containing the date, modified files, command, evidence path, outcome, and remaining issue. Preserve failed-run logs. Contract changes get a new version and a small change note in `isa_spec.md`; then rerun affected stages. Hardware-only changes normally require the relevant hardware gate and S6 regression, not a rewrite of completed software stages.
