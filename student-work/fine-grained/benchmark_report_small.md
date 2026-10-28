# S8 Small-Scale Benchmark Report

Correctness checks compare every output element against an independent reference.
The table reports medians across trials. Host timings in the raw CSV are for
local execution only; Rocket cycles, CPI and speedup remain blank for host runs.
This **focused profile passes** for N=1,4,7,8. Full S8 has now passed all six sizes, including N=16/32; see [the complete report](benchmark_report.md). Baseline rows are unmodified software on BaselineConfig; custom rows are native adapters on FineGrainedConfig. RoCC is outside scope.

| Platform | Workload | N | Implementation | Correctness | Cycles | Instructions | CPI | Speedup |
|---|---|---:|---|---|---:|---:|---:|---:|
| rocket_rv64 | floyd_warshall | 1 | baseline | PASS | 58 | 40 | 1.450 | 1.000 |
| rocket_rv64 | floyd_warshall | 1 | custom | PASS | 239 | 119 | 2.008 | 0.243 |
| rocket_rv64 | floyd_warshall | 4 | baseline | PASS | 1474 | 883 | 1.669 | 1.000 |
| rocket_rv64 | floyd_warshall | 4 | custom | PASS | 2157 | 1678 | 1.285 | 0.683 |
| rocket_rv64 | floyd_warshall | 7 | baseline | PASS | 7321 | 4260 | 1.719 | 1.000 |
| rocket_rv64 | floyd_warshall | 7 | custom | PASS | 10410 | 8314 | 1.252 | 0.703 |
| rocket_rv64 | floyd_warshall | 8 | baseline | PASS | 10828 | 6199 | 1.747 | 1.000 |
| rocket_rv64 | floyd_warshall | 8 | custom | PASS | 15067 | 12146 | 1.240 | 0.719 |
| rocket_rv64 | int8_matmul | 1 | baseline | PASS | 82 | 37 | 2.216 | 1.000 |
| rocket_rv64 | int8_matmul | 1 | custom | PASS | 241 | 157 | 1.535 | 0.340 |
| rocket_rv64 | int8_matmul | 4 | baseline | PASS | 2962 | 634 | 4.672 | 1.000 |
| rocket_rv64 | int8_matmul | 4 | custom | PASS | 1903 | 1511 | 1.259 | 1.556 |
| rocket_rv64 | int8_matmul | 7 | baseline | PASS | 15317 | 2905 | 5.273 | 1.000 |
| rocket_rv64 | int8_matmul | 7 | custom | PASS | 8791 | 7357 | 1.195 | 1.742 |
| rocket_rv64 | int8_matmul | 8 | baseline | PASS | 22735 | 4230 | 5.375 | 1.000 |
| rocket_rv64 | int8_matmul | 8 | custom | PASS | 12646 | 10403 | 1.216 | 1.798 |

The selected 16 cases preserve one verified warm-up and three trials per implementation: 72 measured records including the native core baseline control. The table includes only the 48 primary paired records. Input fingerprints and output checksums match across configurations; independent references check every element. The baseline source files are byte-identical to the supplied files, and baseline kernel executable words match across both configurations (24 function comparisons across the prepared binaries).

Both builds use -O2, -fno-tree-vectorize and rv64imafd/lp64d. Timing includes kernel dispatch and native packing; generation, reset, reference checking and printing are excluded. CPI is calculated on the host. Speedup below 1 means slower. Tiny cases include counter/dispatch overhead; native dispatch/code layout differs from the baseline-only program. These are cycle speedups assuming equal clock frequency, not measured physical timing. ADD_MAX remains covered by earlier unit tests rather than these workloads.

Evidence: `/workspace/student-work/fine-grained/results/20261015T002635Z-s8`. Files: `paired-small.csv`, per-case JSON/logs, `manifest.json`, `baseline-code-equality.json` and `normal-load-controls/result.json`. The final full report will be `benchmark_report.md`.
