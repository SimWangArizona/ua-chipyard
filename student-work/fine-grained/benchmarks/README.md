# Common benchmark integration

`common/` is a snapshot of the benchmark owner's supplied
`ece562_benchmark/ece562/` files. Its baseline kernels, golden algorithms,
input generator, trial count and workload sizes are reused. Do not edit these
files to optimize a baseline or silently alter workload policy.

`native_kernels.c` is the instruction owner's adapter. INT8 packs A-row and
strided B-column lanes inside the timed call and zero-pads tails. Floyd-Warshall
retains the INF guard and loop order and calls ADD_MIN. Hardware wrappers have
no software fallback; ADD_MAX is covered by the existing instruction tests.

The runner generates a separate driver from `common/benchmark.c`, recording a
unified compatibility patch. It selects one size per executable for resumption,
adds an input fingerprint outside timing, changes `%zu` to `%lu` (RV64 size_t
is unsigned long; course nano printf lacks the z modifier), and calculates
CPI on the host. Both workloads execute on the combined native core in separate
processes. No source in the teammate's original directory is changed.

Results report the original BaselineConfig software against native instructions
on FineGrainedConfig. The native core's ordinary software measurements remain
in raw CSV as a secondary control. The unchanged common reporter receives only
the primary paired records. Its stock text about pending custom integration
is template text; the main `benchmark_report.md` describes actual stage status.
