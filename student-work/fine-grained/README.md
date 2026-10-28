# Fine-Grained Instruction Verification

Roadmap: [../fine_grained_stages.md](../fine_grained_stages.md). Current progress: [STATUS.md](STATUS.md). Candidate instruction interface: [isa_spec.md](isa_spec.md).

## Fresh-container path to benchmark results

Use the UA course Docker image with this repository checked out, so this directory
is mounted at `/workspace/student-work/fine-grained`. The Rocket checkout must be
at revision `55bcad0f59436de98ea510334121de8546b9e9d7`; the installer checks
this and refuses unrelated Rocket source changes. Run the following **inside one
container shell**. The course entrypoint normally installs `BaselineConfig`.

```bash
cd /workspace/chipyard
source env.sh
export _JAVA_OPTIONS='-Xmx3G -XX:ActiveProcessorCount=2'
cd /workspace/student-work/fine-grained
python3 scripts/install_s5.py
cd /workspace/chipyard/sims/verilator
make CONFIG=BaselineConfig -j2
make CONFIG=FineGrainedConfig -j2
cd /workspace/student-work/fine-grained
make all-hw
make pipeline
python3 scripts/benchmark_s8.py --sizes 1 4 7 8 --workers 4 --timeout 28800
```

`install_s5.py` applies the cumulative DOT4_ACC and ADD_MIN/ADD_MAX patch and
links the student configuration. The two `make` commands build the simulator
paths required by S8; neither `make software` nor `make s7-build` alone creates
both at those standard paths. `make all-hw` and `make pipeline` must finish with
PASS before using the benchmark result. The last command is a **short profile**:
its `result.json` reports `full_s8: false`, even when all selected cases pass.

For the complete six-size S8 run, after the short profile has finished, start a
**new** benchmark run:

```bash
cd /workspace/student-work/fine-grained
python3 scripts/benchmark_s8.py --workers 4 --timeout 28800
```

The runner prints a timestamped directory under `results/`. A complete result
requires `S8 PASS` and `result.json` with `status: "PASS"`, `full_s8: true`,
`records: 108`, and no failures. Read that directory's `report.md` and CSV files;
the root `benchmark_report.md` is overwritten by the most recent selected run.
N=32 simulations can take hours. If interrupted, resume only after the old runner
has stopped, replacing the timestamp below with the actual evidence directory:

```bash
python3 scripts/benchmark_s8.py --resume /workspace/student-work/fine-grained/results/<timestamp>-s8 --workers 4 --timeout 28800
```

The earlier completed full report is included in this repository as historical
evidence; a fresh run must produce its own passing evidence.

Inside the course Docker container:

```bash
cd /workspace/chipyard
source env.sh
cd /workspace/student-work/fine-grained
make software
```

This runs environment inspection, portable reference tests, C/C++ wrapper compilation, instruction-field checks, and compilation/linking of future simulator tests. It does not implement or execute custom hardware.

Run stages independently with `make env`, `make reference`, or `make wrappers`. After building the appropriate simulator, use `make baseline`, `make dp`, `make dot`, `make all-hw`, or `make pipeline`. All commands preserve prior runs in `results/`; missing prerequisites are reported as BLOCKED.

## S4 native DP installation and tests

S4 adds ADD_MAX and ADD_MIN to Rocket's native integer execution path. The feature
is disabled by default and enabled by `FineGrainedDPConfig`. Dot-product hardware
is still a later stage. In a fresh course container, restore the saved patch/config:

```bash
cd /workspace/chipyard
source env.sh
python3 /workspace/student-work/fine-grained/scripts/install_s4.py
cd /workspace/chipyard/sims/verilator
make CONFIG=FineGrainedDPConfig -j2
cd /workspace/student-work/fine-grained
make dp
make dp-pipeline
```

For a small-memory container, use the bounded-resource build/test driver after
loading the environment:

```bash
python3 /workspace/student-work/fine-grained/scripts/build_s4.py
```

It limits its Java heap to 3 GB and Java processor count to two, saves separate
build/test logs, and runs both S4 gates only after a successful simulator build.
These are process-local limits, not changes to Docker Desktop settings.

The installer refuses unrelated dirty Rocket sources or occupied configuration
paths. It checks the saved patch against clean files from the recorded base
revision without resetting the actual checkout. Its initial code-generation mode
is for the S4-only patch; when S5 updates the cumulative patch, installation uses
that saved patch instead.

`make dp` runs `test_dp.c`: 15 hand-written known-answer triples, 125 boundary
triples, and 128 deterministic random triples. Each triple checks raw ADD_MAX and
ADD_MIN results, ignored upper source bits, and both C wrappers: 1,608 checks in
total. Raw results validate all 64 writeback bits. Increase random coverage with:

```bash
python3 scripts/verify.py dp --random-cases 2000 --timeout 600
```

`make dp-pipeline` executes 14 adjacent instruction checks for the two DP
operations on the DP-only core (producer/consumer, register aliases, x0,
load-use, custom chains and branch flush). The full combined `make pipeline`
remains an S6 gate requiring dot hardware too.

The runner now writes subprocess output live into `run.log` and keeps per-command
logs. A timeout stops the complete subprocess group; interrupting the Python
runner records `INTERRUPTED`, never PASS. S3 was deferred by user request; that
does not invalidate S4 development or substitute for a baseline reference PASS.

## S5 native dot-product installation and tests

The cumulative `rocket-chip.patch` now includes S4 and S5. Do not apply the old
S4 snapshot and cumulative patch consecutively. `scripts/install_s5.py` installs
the cumulative patch on a fresh clean source tree or upgrades an exact S4 tree;
it refuses unrelated changes. `patches/s4.patch` preserves the previous stage.

After sourcing the environment, the complete bounded-resource S5 driver is:

```bash
python3 /workspace/student-work/fine-grained/scripts/build_s5.py
```

It builds `FineGrainedDotConfig`, runs dot arithmetic and dot-only dependencies,
then rebuilds/retests `FineGrainedDPConfig` to protect S4. Logs are saved in a new
`results/<timestamp>-s5-build/` directory. A final `S5 PASS` requires all steps.

Once the dot simulator exists, independently repeat tests with:

```bash
cd /workspace/student-work/fine-grained
make dot
make dot-pipeline
```

`test_dot.c` exercises 15 known answers, 16 lane-position pairs, 180 packed-input
and accumulator boundary combinations and 128 random triples. Its 1,356 hardware
checks cover the reference value, actual raw 64-bit writeback, ignored high bits
of rs2, and the public C wrapper. Dot-only dependencies add seven checks. Increase
random coverage with `verify.py dot --random-cases 2000 --timeout 600` if needed.
The former full dot coverage remains available via `test_arithmetic.c` for S6.

`FineGrainedConfig` enabling both families is defined for S6; passing individual
S4/S5 tests does not yet constitute mixed-operation integration validation.

## S6 combined-core validation

Once `FineGrainedConfig` is built, run `make all-hw` and `make pipeline`.
`all-hw` now links the focused dot and DP suites into **one program** on the
combined simulator: 1,356 dot checks plus 1,608 DP checks (2,964 total), with
progress messages and a 600-second default timeout. It still executes actual
custom instructions; it does not fall back to software or claim the original
large suite passed. `pipeline` runs 23 checks, including two back-to-back
dot/min/max chains spanning both instruction families.

The original 2,000-random-case arithmetic suite remains available explicitly:

```bash
python3 scripts/verify.py all-hw --full --timeout 1800
```

The old full-suite timeout is retained as failed execution evidence. Consult
`STATUS.md` for the focused S6 outcome. Software-only test changes require no
simulator rebuild. A simulation timeout is not evidence of arithmetic mismatch.

## S7 regression, feature gates and reproduction

After loading the environment, build missing baseline and independent fresh
combined outputs, then execute all S7 checks:

```bash
cd /workspace/student-work/fine-grained
make s7-build
```

This driver uses the same 3 GB/two-processor JVM limits. It keeps validated
simulators and working sources intact; the fresh combined build uses a new
container-local output directory. Existing toolchain/Scala caches are reused,
but RTL/Verilator/C++ outputs are regenerated. It verifies clean-base patch
replay and runs the fresh simulator's focused arithmetic/pipeline gates.

For repeat checks with existing simulators:

```bash
make s7-isa       # 8 installed ISA binaries on baseline and combined: 16 runs
make s7-traps     # 8 controlled probes on each of four configurations: 32 probes
make s7          # all gates, using the recorded fresh simulator path
```

`build/s7-fresh-simulator.path` identifies the latest successful fresh-output
build. It is a container path, not a portable saved simulator; after a disposable
container is removed, repeat `s7-build`. Individual debugging is available with
`verify_s7.py --part traps --config dp` or `--part isa --config combined`.

- ISA list: `rv64ui-p-simple/add/sub/beq/ld/sd` and `rv64um-p-mul/div`.
  These are selected ordinary-instruction regression tests, not the entire ISA suite.
- Trap profiles: baseline expects 8 traps; dot-only 6; DP-only 4; combined 2.
  Legal operations execute twice each; unallocated funct7 and wrong funct3 must
  always trap. The test checks cause 2, exact fault PC and instruction, optional
  mtval (zero or exact word), trap counts, unchanged destination and continuation.
- `test_traps.c` overrides the **weak HTIF handler**, using the ABI verified from
  the installed `trap_entry`: `(mepc, mcause, mtval, saved_gprs) -> next_mepc`.
  The runtime preserves the GPR frame and executes mret; the test skips exactly
  four bytes. Unexpected exceptions exit with failure, not a timeout-based PASS.
- `trap_probes.S` shares opcode constants from `fg_encoding.h`, which is included
  by `fg_contract.h`. Public C/C++ wrappers/encodings remain unchanged.
- `verify_s7.py --part patch` checks the persistent patch on a complete clean
  detached Rocket checkout and compares all four patched files with the running
  sources, without resetting the user's checkout. Preserve selected result JSONs
  and logs; S7 PASS does not establish physical timing or benchmark speedup.

| File | Responsibility |
| --- | --- |
| `include/fg_contract.h` | Encoding constants, packing, explicit sign conversion |
| `include/fg_encoding.h` | Single encoding-constant source shared with assembly probes |
| `include/fg_reference.h` | Portable arithmetic semantics |
| `include/fg_hw.h` | Actual RV64 inline assembly; no software fallback |
| `tests/test_arithmetic.c` | Known answers, boundary combinations, independent oracle, deterministic random cases; reused for hardware |
| `tests/encoding_probe.c` | Compile-only C/C++ interface and instruction-field probes |
| `tests/test_pipeline.c` | Explicit assembly sequences for dependencies, aliases, x0, load-use, and branch flush |
| `tests/test_dp.c` | Focused S4 known-answer, signed boundary, random and raw writeback tests |
| `tests/test_dot.c` | Focused S5 lane/sign/wrap/random/raw-writeback tests with independent oracle |
| `FineGrainedConfig.scala`, `rocket-chip.patch` | Persistent native DP configuration and Rocket implementation patch |
| `scripts/install_s4.py` | Safe patch/config installation and clean-base patch reproducibility check |
| `scripts/install_s5.py`, `scripts/build_s5.py` | Cumulative S5 upgrade, bounded-resource build/test and S4 regression |
| `tests/test_traps.c`, `tests/trap_probes.S` | Precise illegal-instruction recovery and feature-gate checks |
| `scripts/verify_s7.py`, `scripts/build_s7.py` | Ordinary ISA, trap matrix, clean patch replay and fresh-output reproduction |
| `scripts/verify.py` | Independent gates, build commands, PASS/FAIL/BLOCKED handling, persistent evidence |
| `benchmarks/common/`, `benchmarks/native_kernels.c` | Original common benchmark snapshot and native workload adapters |
| `scripts/benchmark_s8.py` | Resumable real Rocket measurements, configuration-labelled CSV and Markdown report |
| `scripts/check_s8_baseline_code.py`, `scripts/calibrate_s8_loadmem.py` | Baseline executable-word equality and normal/fast loading controls |
| `scripts/progress_s8.py`, `scripts/report_s8_small.py` | Explicitly partial progress and complete focused comparison during long runs |

The optional full arithmetic suite uses 1,000 boundary triples, 16 lane-placement pairs, 2,000 random triples with seed `0x05622026`, and seven known-answer/packing checks. It checks all 64 result bits in hardware mode. Host reference checks use both C and C++, O0 and O2, and undefined-behavior sanitization.

S4-S7 focused hardware gates have passed; consult `STATUS.md` for evidence and
the deferred S3/optional full S6 limitations.

## S8 common benchmark

After sourcing `/workspace/chipyard/env.sh`, run in this directory:

```bash
make s8
# Resume completed cases from an existing run without rerunning them:
make s8 RESUME=/workspace/student-work/fine-grained/results/<timestamp>-s8
```

`scripts/benchmark_s8.py` uses the supplied common source snapshot in
`benchmarks/common/` and the real native adapters in `benchmarks/native_kernels.c`.
The original teammate files remain unchanged. Both built simulators are required;
the runner does not build Rocket automatically. Up to six independent simulations run
concurrently. Each workload/size has its own ELF and logs, so slow cases do not
discard completed cases. The per-case timeout defaults to 28800 seconds. SimDRAM `+loadmem` bypasses slow ELF transfer; it is outside kernel measurement and is validated against normal loading.

The matrix contains six sizes, two workloads, one verified warm-up and three
trials per implementation: 36 BaselineConfig rows and 72 FineGrainedConfig rows.
The latter includes an ordinary baseline control. Primary speedup compares
BaselineConfig baseline with FineGrainedConfig custom, using identical inputs.
`benchmark_report.md` contains the latest report; timestamped evidence includes
CSV, input fingerprints, compiler logs, disassembly, simulator logs and hashes.
Compatibility changes to the integration driver are saved separately; target
CPI formatting is replaced by host calculation. RoCC is outside this stage.
