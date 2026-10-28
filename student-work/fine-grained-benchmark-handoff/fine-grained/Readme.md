# Fine-Grained Instruction Benchmark Handoff

This package reproduces the native Rocket custom-instruction comparison using the team's common benchmark. Run it inside the existing UA Compute course Docker environment. No RoCC implementation is required or included.

## 1. Copy the package into the existing Docker workspace

Extract the ZIP on the host. It contains one top-level directory named `fine-grained`. Copy that directory into the `student-work` directory of your UA Chipyard checkout. The course Compose file mounts it at `/workspace/student-work/fine-grained`.

Do not overwrite an existing `fine-grained` directory containing your work or results. Rename the newly extracted directory to `fine-grained-handoff` if necessary, and replace `/workspace/student-work/fine-grained` in the commands below with that path. Scripts locate their package directory automatically; Chipyard itself must remain at `/workspace/chipyard`.

Open a terminal in your already running course container. If you use a host terminal, find the container with `docker ps` and enter it using `docker exec -it <container-id> bash`. The remaining commands are **Linux commands inside the container**, not PowerShell commands.

```bash
cd /workspace/chipyard
source env.sh
cd /workspace/student-work/fine-grained
python3 scripts/preflight_handoff.py
```

Source `env.sh` once in each new shell. The supported image is `ghcr.io/tosiron/ua-chipyard:fall2026-v1`; the required Rocket revision is `55bcad0f59436de98ea510334121de8546b9e9d7`. Preflight checks package hashes, the compiler, course configuration, and source revision. It does not modify Rocket.

The installed `CourseRocketConfig.scala` must match `course-reference/CourseRocketConfig.scala` (line-ending differences are allowed). The normal course entrypoint installs this configuration. If it is missing, run `/workspace/course-scripts/install-course-configs.sh` and repeat preflight. If it differs, inspect the difference with the team before running a comparison. Do not replace a different baseline silently.

## 2. Install the native instructions and build both simulators

```bash
python3 scripts/build_handoff.py
```

This command applies the supplied cumulative Rocket patch, links `FineGrainedConfig.scala`, and builds these standard simulator paths in sequence:

```text
/workspace/chipyard/sims/verilator/simulator-chipyard.harness-BaselineConfig
/workspace/chipyard/sims/verilator/simulator-chipyard.harness-FineGrainedConfig
```

The installer accepts a clean matching Rocket checkout or the exact already installed patch. It refuses unrelated Rocket modifications and occupied configuration paths. An existing RoCC or other custom-instruction patch may conflict: coordinate a separate course checkout/container rather than resetting or overwriting another implementation. Do not apply this cumulative patch together with an older S4 patch.

The build uses two Make jobs and a 3 GB Java heap with two active Java processors. It records logs under `results/<timestamp>-handoff-build/`. Compilation can take substantial time; a quiet terminal does not imply failure. In a second container terminal, use `tail -f` on the log path printed by the script. Build success ends with `BUILD PASS` and an exit status of zero. This is a build check, not a performance result.

## 3. Verify custom arithmetic and pipeline behavior

```bash
python3 scripts/verify.py all-hw --timeout 1800
python3 scripts/verify.py pipeline --timeout 1800
```

The combined arithmetic suite checks 2,964 results and the pipeline suite checks 23 dependency/alias/flush cases, including DOT4_ACC, ADD_MIN, and ADD_MAX. Each command must finish with PASS and exit zero. A timeout, missing simulator, or illegal instruction is not a pass. These focused checks do not require rerunning the deferred historical S3 suite.

## 4. Run a short performance profile first

```bash
python3 scripts/benchmark_s8.py --sizes 1 4 7 8 --workers 4 --timeout 28800
```

This runs both workloads on both configurations, with one checked warm-up and three measured trials per implementation. It exercises real custom instructions, including partial packed lanes. N=4/7/8 previously showed INT8 acceleration. N=1 is dominated by overhead and should not be expected to accelerate.

The short profile is a focused comparison, not a full S8 pass. Check `full_s8: false` in its `result.json` and the focused-profile label in its report. Do not add N=16/32 to that same evidence directory: the full matrix needs a new run.

## 5. Run the complete six-size benchmark

```bash
python3 scripts/benchmark_s8.py --workers 4 --timeout 28800
```

Default sizes are N=1,4,7,8,16,32 for INT8 matrix multiplication and Floyd-Warshall dynamic programming. N denotes the matrix/graph dimension, not the number of packed lanes. The full matrix contains 24 simulator cases and 108 measured records, including ordinary-software controls on the native core. Its primary comparison contains 72 records.

Large cases can take hours in Verilator. `--timeout 28800` is eight hours **per simulator case**, not a prediction of total runtime. Adjust `--workers` from 1 through 8 to match available CPU/memory. Simulations are independent; concurrency does not change simulated cycle counters. Keep the same sources, toolchain, simulators, inputs, and measurement policy throughout one run.

The runner prints the evidence path at startup and saves each completed case separately. For example, in a second container terminal:

```bash
cd /workspace/student-work/fine-grained
ls -td results/*-s8
# Replace this example with the actual evidence path printed by your run:
python3 scripts/progress_s8.py /workspace/student-work/fine-grained/results/<timestamp>-s8
cat benchmark_progress.md
tail -n 10 results/<timestamp>-s8/FineGrainedConfig-int8_matmul-32.log
```

Angle-bracket placeholders must be replaced before executing. Do not launch a second benchmark runner against a directory while its first runner is still active.

If a run was interrupted, wait until its old processes have stopped and resume using the same size list:

```bash
# Resume a full matrix:
python3 scripts/benchmark_s8.py --resume /workspace/student-work/fine-grained/results/<timestamp>-s8 --workers 4 --timeout 28800
# For a short profile, also supply: --sizes 1 4 7 8
```

Resume revalidates and skips passing cases; incomplete/failed cases are retried with prior logs archived. Do not mix evidence after changing sources, compiler, or simulator binaries. Start a fresh run instead. Recreating a disposable container may require reinstalling the patch and rebuilding simulators; persisted source files alone do not preserve container-local build outputs.

## 6. Read the results

After the selected matrix finishes, open `benchmark_report.md` in this package directory. It contains median cycles, instructions, CPI, and cycle speedup. That file reflects the **latest completed selected profile** and can be overwritten by a subsequent run; each timestamped directory retains its own `report.md`.

For a complete S8 result, require all of the following:

- The process exits zero and prints `S8 PASS`.
- `results/<timestamp>-s8/result.json` has `status: "PASS"`, `full_s8: true`, `records: 108`, and no failures.
- All 24 case JSON files are PASS, with normal simulator completion.
- Input fingerprints and output checksums agree across configurations; independent references check every output element.

Key artifacts:

| File | Purpose |
| --- | --- |
| `report.md` | Per-run performance report with median measurements and limitations |
| `results.csv` | All 108 measured records for a full run, with configuration labels |
| `paired.csv` | 72 primary records: BaselineConfig ordinary software versus FineGrainedConfig custom |
| `manifest.json` | Compiler, source/configuration, ELF, and simulator hashes; exact commands |
| `baseline-code-equality.json` | Equality of ordinary baseline kernel instruction words across paired binaries |
| `*.log`, `*.json` | Per-case raw output, counters, checksums, and completion status |
| `*.disassembly.txt` | Baseline/custom opcode checks and compiled executable code |
| `driver-compatibility.patch` | Explicit changes to the integration driver, separate from common sources |

Speedup is median baseline cycles divided by median custom cycles. A value above 1 is faster; below 1 is slower. CPI is cycles divided by retired instructions. Lower CPI alone does not establish acceleration.

## 7. Expected findings and fairness rules

Previously measured full-run results are under `reference-results/`; these are historical evidence, not results from your machine. `reference-results/report.md` includes all six sizes. At N=32:

| Workload | Baseline cycles | Custom cycles | Speedup |
| --- | ---: | ---: | ---: |
| INT8 matrix multiplication | 1,435,836 | 759,559 | 1.890x |
| Floyd-Warshall DP | 662,383 | 929,319 | 0.713x |

INT8 gains from four signed INT8 products plus accumulation per DOT4_ACC, bypassing the course baseline's slow scalar multiplier. DP is correct but the current adapter is slower: operand packing and storing every valid minimum add overhead. Do not promise or report DP acceleration. ADD_MAX is unit-tested but is not exercised by these workloads. Exact counters may differ after toolchain/layout changes; preserve local evidence and report the measured values.

The baseline `dot_bench.c` and `dp_bench.c` are unchanged copies of the team's supplied code. Keep the baseline on BaselineConfig and native callbacks on FineGrainedConfig. Both use the same compiler flags, inputs, seed, dimensions, reference models, warm-up count, and three trials. Native packing is inside the measured kernel. Initialization, references, verification, and printing are outside it. Primary runs use `+loadmem` for unmeasured ELF startup; saved N=1/4 controls show matching counters/checksums with normal loading. Timing assumes equal clock frequency; this is not a physical timing or area study. Small profiles include dispatch/counter overhead and no overhead subtraction.

## 8. Package contents and troubleshooting

| Path | Role |
| --- | --- |
| `rocket-chip.patch`, `FineGrainedConfig.scala` | Native Rocket decode/datapath patch and course-baseline-derived configurations |
| `include/`, `isa_spec.md` | ISA contract, inline assembly wrappers, reference helpers |
| `benchmarks/common/` | Original team benchmark snapshot, retained without edits |
| `benchmarks/native_kernels.c` | DOT4_ACC matrix kernel and ADD_MIN DP adapter |
| `scripts/install_s4.py`, `install_s5.py` | Existing revision-checked cumulative installer; historical names retained |
| `scripts/build_handoff.py`, `preflight_handoff.py` | Handoff build workflow and integrity/environment checks |
| `tests/`, `scripts/verify.py` | Arithmetic, wrapper, and pipeline checks |
| `scripts/benchmark_s8.py`, `check_s8_baseline_code.py` | Benchmark execution, evidence validation, and report generation |
| `course-reference/` | Expected course baseline configuration for comparison, not automatic replacement |
| `reference-results/` | Earlier complete passing run, including raw simulator logs and CSV |
| `PACKAGE_SHA256.json` | Hashes of all shipped files except this manifest itself |

If the compiler is missing, source `/workspace/chipyard/env.sh` in the same shell. If custom instructions trap, check that you built and selected FineGrainedConfig, not BaselineConfig. If a build fails, inspect the printed build log and its `result.json`; do not interpret partial output as success. If a simulation times out, retain its evidence, increase the timeout if appropriate, and resume after confirming the prior runner has stopped.

This source-only handoff excludes prebuilt simulators, ELF binaries, generated RTL, toolchains, and cached build directories. Build locally in the course image. Package creation checked archive hashes and reference evidence; Docker was not running on the packaging host, so the new handoff build workflow was not executed there. The included unchanged kernels, wrappers, patch and benchmark runner come from the previously completed full S8 run.
