# S8 Rocket Benchmark Report

Status: **PASS**. Sizes: [1, 4, 7, 8, 16, 32]. Evidence: `/workspace/student-work/fine-grained/results/20261015T002635Z-s8`.

Unmodified common `dot_bench.c` and `dp_bench.c` run on BaselineConfig. Native adapters run on FineGrainedConfig. Common INT64 matrix reference and independent Dijkstra reference check every output element after one warm-up and each of three trials. Input fingerprints and output checksums must match across configurations.

Baseline kernel source files match the supplied files byte for byte. Their executable instruction words also match across baseline/native binaries, as recorded in `baseline-code-equality.json`. The baseline-only ELF contains no custom opcode; native ELFs contain the DOT4_ACC/ADD_MIN opcode, funct3 and funct7 fields. Initial nano-printf `%zu` failures are retained in the earlier failed run; the compatibility patch fixes formatting in the integration driver.

Both builds use GCC -O2, -fno-tree-vectorize, rv64imafd/lp64d, and the same HTIF runtime. Counters surround only synchronous kernel dispatch; input preparation, output reset, golden checks and printing are excluded. Native lane packing is included. CPI is calculated on the host to avoid target floating-point formatting. SimDRAM fast ELF loading (+loadmem) shortens unmeasured startup. Actual loading commands are retained per case. All primary rows use fast loading. Normal-load N=1/N=4 controls are saved separately and reproduce exactly the same per-trial cycles, instructions, input fingerprints and output checksums as fast loading. Numbers below are medians of three trials; speedup is baseline median cycles / native median cycles.

| Workload | N | Baseline cycles | Native cycles | Baseline instructions | Native instructions | Baseline CPI | Native CPI | Speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| int8_matmul | 1 | 82 | 241 | 37 | 157 | 2.216 | 1.535 | 0.340x |
| int8_matmul | 4 | 2962 | 1903 | 634 | 1511 | 4.672 | 1.259 | 1.556x |
| int8_matmul | 7 | 15317 | 8791 | 2905 | 7357 | 5.273 | 1.195 | 1.742x |
| int8_matmul | 8 | 22735 | 12646 | 4230 | 10403 | 5.375 | 1.216 | 1.798x |
| int8_matmul | 16 | 179125 | 95697 | 31102 | 79069 | 5.759 | 1.210 | 1.872x |
| int8_matmul | 32 | 1435836 | 759559 | 238830 | 618857 | 6.012 | 1.227 | 1.890x |
| floyd_warshall | 1 | 58 | 239 | 40 | 119 | 1.450 | 2.008 | 0.243x |
| floyd_warshall | 4 | 1474 | 2157 | 883 | 1678 | 1.669 | 1.285 | 0.683x |
| floyd_warshall | 7 | 7321 | 10410 | 4260 | 8314 | 1.719 | 1.252 | 0.703x |
| floyd_warshall | 8 | 10828 | 15067 | 6199 | 12146 | 1.747 | 1.240 | 0.719x |
| floyd_warshall | 16 | 84014 | 117774 | 46959 | 94474 | 1.789 | 1.247 | 0.713x |
| floyd_warshall | 32 | 662383 | 929319 | 367725 | 754258 | 1.801 | 1.232 | 0.713x |

Measured observations:

- int8_matmul: native is faster in 5/6 sizes; N=32 cycle speedup is 1.890x. Values below 1x represent a slowdown.
- floyd_warshall: native is faster in 0/6 sizes; N=32 cycle speedup is 0.713x. Values below 1x represent a slowdown.

Secondary ordinary-software control on the native core:

| Workload | N | BaselineConfig cycles | FineGrainedConfig baseline cycles | Ratio |
|---|---:|---:|---:|---:|
| int8_matmul | 1 | 82 | 300 | 0.273x |
| int8_matmul | 4 | 2962 | 3150 | 0.940x |
| int8_matmul | 7 | 15317 | 15534 | 0.986x |
| int8_matmul | 8 | 22735 | 22961 | 0.990x |
| int8_matmul | 16 | 179125 | 179333 | 0.999x |
| int8_matmul | 32 | 1435836 | 1435806 | 1.000x |
| floyd_warshall | 1 | 58 | 218 | 0.266x |
| floyd_warshall | 4 | 1474 | 1580 | 0.933x |
| floyd_warshall | 7 | 7321 | 7533 | 0.972x |
| floyd_warshall | 8 | 10828 | 10949 | 0.989x |
| floyd_warshall | 16 | 84014 | 84055 | 1.000x |
| floyd_warshall | 32 | 662383 | 662618 | 1.000x |

108 measured records retained. Failures: []. A passing selected matrix checks 36 warm-ups and 108 measured invocations (144 kernel calls), comparing 33,840 output elements with independent references.

Instruction count and cycles need not decrease together: native lane packing adds instructions while DOT4 bypasses the baseline scalar multiplier (one bit per cycle, with early-out disabled). The ADD_MIN adapter preserves INF checks and writes the returned minimum for every valid candidate; the original baseline stores only when the distance improves. These adapter costs are included.

FineGrainedConfig also executes the original baseline as a secondary control; these rows are retained in CSV. Its baseline runs before custom, so cache/order effects may affect comparisons. The native executable includes extra dispatch/code and may have a different instruction-cache layout. Small cases include fence/CSR counter and dispatch overhead; no overhead subtraction is applied. Speedup assumes equal clock frequency and is not physical timing or end-to-end application speedup. ADD_MAX is covered by earlier unit tests, not these workloads. RoCC is outside this stage. S3 remains deferred and the optional full S6 suite remains uncompleted.

INT8 uses four signed packed lanes with zero-padding for N=1 and N=7 tails, including strided B-column extraction. DP retains the original loop order and INF guard and uses ADD_MIN. These straightforward adapters include packing costs and are not assumed to improve speed without measurements.

Artifacts: `results.csv`, `manifest.json` (original source and simulator hashes), per-case compiler logs, disassembly, simulator logs, and JSON records. To resume, run `python3 scripts/benchmark_s8.py --resume /workspace/student-work/fine-grained/results/20261015T002635Z-s8`.
