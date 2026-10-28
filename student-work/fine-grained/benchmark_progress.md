# S8 Benchmark Progress

**COMPLETE / PASS:** 24/24 cases passed. See `benchmark_report.md` for the complete S8 report.
Evidence: `/workspace/student-work/fine-grained/results/20261015T002635Z-s8`. Only complete, normally finished cases are included.

| Workload | N | Baseline cycles | Native cycles | Cycle speedup |
|---|---:|---:|---:|---:|
| int8_matmul | 1 | 82 | 241 | 0.340x |
| int8_matmul | 4 | 2962 | 1903 | 1.556x |
| int8_matmul | 7 | 15317 | 8791 | 1.742x |
| int8_matmul | 8 | 22735 | 12646 | 1.798x |
| int8_matmul | 16 | 179125 | 95697 | 1.872x |
| int8_matmul | 32 | 1435836 | 759559 | 1.890x |
| floyd_warshall | 1 | 58 | 239 | 0.243x |
| floyd_warshall | 4 | 1474 | 2157 | 0.683x |
| floyd_warshall | 7 | 7321 | 10410 | 0.703x |
| floyd_warshall | 8 | 10828 | 15067 | 0.719x |
| floyd_warshall | 16 | 84014 | 117774 | 0.713x |
| floyd_warshall | 32 | 662383 | 929319 | 0.713x |

Each case preserves one verified warm-up and three trials. Golden checks compare every output element. Baseline software runs on BaselineConfig; custom adapters run on FineGrainedConfig. Full metrics, CPI, checksums and configuration manifests remain in the timestamped evidence. The final report will be `benchmark_report.md` after the complete matrix passes.
