# Benchmark results

Correctness checks compare every output element against an independent reference.
The table reports medians across trials. Host timings in the raw CSV are for
local execution only; Rocket cycles, CPI and speedup remain blank for host runs.
Custom and RoCC implementations are pending until hardware wrappers are provided.

| Platform | Workload | N | Implementation | Correctness | Cycles | Instructions | CPI | Speedup |
|---|---|---:|---|---|---:|---:|---:|---:|
| host | floyd_warshall | 1 | baseline | PASS | — | — | — | — |
| host | floyd_warshall | 4 | baseline | PASS | — | — | — | — |
| host | floyd_warshall | 7 | baseline | PASS | — | — | — | — |
| host | floyd_warshall | 8 | baseline | PASS | — | — | — | — |
| host | floyd_warshall | 16 | baseline | PASS | — | — | — | — |
| host | floyd_warshall | 32 | baseline | PASS | — | — | — | — |
| host | int8_matmul | 1 | baseline | PASS | — | — | — | — |
| host | int8_matmul | 4 | baseline | PASS | — | — | — | — |
| host | int8_matmul | 7 | baseline | PASS | — | — | — | — |
| host | int8_matmul | 8 | baseline | PASS | — | — | — | — |
| host | int8_matmul | 16 | baseline | PASS | — | — | — | — |
| host | int8_matmul | 32 | baseline | PASS | — | — | — | — |
