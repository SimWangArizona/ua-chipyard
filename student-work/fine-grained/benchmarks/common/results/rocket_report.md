# Benchmark results

Correctness checks compare every output element against an independent reference.
The table reports medians across trials. Host timings in the raw CSV are for
local execution only; Rocket cycles, CPI and speedup remain blank for host runs.
Custom and RoCC implementations are pending until hardware wrappers are provided.

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
| rocket_rv64 | floyd_warshall | 16 | baseline | PASS | 84014 | 46959 | 1.789 | 1.000 |
| rocket_rv64 | floyd_warshall | 16 | custom | PASS | 117774 | 94474 | 1.247 | 0.713 |
| rocket_rv64 | floyd_warshall | 32 | baseline | PASS | 662383 | 367725 | 1.801 | 1.000 |
| rocket_rv64 | floyd_warshall | 32 | custom | PASS | 929319 | 754258 | 1.232 | 0.713 |
| rocket_rv64 | int8_matmul | 1 | baseline | PASS | 82 | 37 | 2.216 | 1.000 |
| rocket_rv64 | int8_matmul | 1 | custom | PASS | 241 | 157 | 1.535 | 0.340 |
| rocket_rv64 | int8_matmul | 4 | baseline | PASS | 2962 | 634 | 4.672 | 1.000 |
| rocket_rv64 | int8_matmul | 4 | custom | PASS | 1903 | 1511 | 1.259 | 1.556 |
| rocket_rv64 | int8_matmul | 7 | baseline | PASS | 15317 | 2905 | 5.273 | 1.000 |
| rocket_rv64 | int8_matmul | 7 | custom | PASS | 8791 | 7357 | 1.195 | 1.742 |
| rocket_rv64 | int8_matmul | 8 | baseline | PASS | 22735 | 4230 | 5.375 | 1.000 |
| rocket_rv64 | int8_matmul | 8 | custom | PASS | 12646 | 10403 | 1.216 | 1.798 |
| rocket_rv64 | int8_matmul | 16 | baseline | PASS | 179125 | 31102 | 5.759 | 1.000 |
| rocket_rv64 | int8_matmul | 16 | custom | PASS | 95697 | 79069 | 1.210 | 1.872 |
| rocket_rv64 | int8_matmul | 32 | baseline | PASS | 1435836 | 238830 | 6.012 | 1.000 |
| rocket_rv64 | int8_matmul | 32 | custom | PASS | 759559 | 618857 | 1.227 | 1.890 |
