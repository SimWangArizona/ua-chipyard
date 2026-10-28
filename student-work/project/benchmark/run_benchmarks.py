"""Verify complete host/model or Rocket captures and report trial medians."""
import argparse
import csv
import io
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parent
SIZES = {1, 4, 7, 8, 16, 32}
FIELDS = "workload,size,implementation,trial,platform,status,cycles,instructions,cpi,host_elapsed_ns,checksum".split(",")


def summarize(text, expected_trials=3):
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != FIELDS:
        raise ValueError("Missing or unexpected CSV header (capture stdout only)")
    rows = list(reader)
    if not rows or any(r.get("status") != "PASS" or None in r or None in r.values() for r in rows):
        raise ValueError("Missing results, malformed rows, or failed correctness checks")
    groups = {}
    for r in rows:
        if r["platform"] not in {"host", "rocket_rv64"}:
            raise ValueError("Unknown measurement platform")
        if r["workload"] not in {"int8_matmul", "floyd_warshall"}:
            raise ValueError("Unknown workload")
        key = (r["platform"], r["workload"], int(r["size"]), r["implementation"])
        groups.setdefault(key, []).append(r)
        if r["platform"] == "host":
            if any(r[f] for f in ("cycles", "instructions", "cpi")) or int(r["host_elapsed_ns"]) < 0:
                raise ValueError("Host results must not contain Rocket counters")
        else:
            if r["host_elapsed_ns"] or "model" in r["implementation"]:
                raise ValueError("Model/host timing cannot be reported as hardware results")
            cycles, instructions = int(r["cycles"]), int(r["instructions"])
            if cycles <= 0 or instructions <= 0 or abs(float(r["cpi"])-cycles/instructions) > 0.000002:
                raise ValueError("Missing or inconsistent Rocket counters/CPI")
        int(r["checksum"])
    for platform, workload, _, impl in groups:
        sizes = {n for p, w, n, i in groups if (p,w,i) == (platform,workload,impl)}
        if sizes != SIZES:
            raise ValueError("Incomplete workload size sweep")
    summary = []
    for (platform, workload, n, impl), trials in sorted(groups.items()):
        if len(trials) != expected_trials or {int(r["trial"]) for r in trials} != set(range(1,expected_trials+1)):
            raise ValueError("Missing or duplicate trials")
        if len({r["checksum"] for r in trials}) != 1:
            raise ValueError("Inconsistent outputs across trials")
        base = groups.get((platform,workload,n,"baseline"))
        if not base:
            raise ValueError("Missing baseline measurements")
        if {r["checksum"] for r in base} != {r["checksum"] for r in trials}:
            raise ValueError("Implementation checksum differs from baseline")
        cycles = instructions = cpi = speedup = "-"
        if platform == "rocket_rv64":
            cycles = statistics.median(int(r["cycles"]) for r in trials)
            instructions = statistics.median(int(r["instructions"]) for r in trials)
            cpi = f'{statistics.median(float(r["cpi"]) for r in trials):.3f}'
            speedup = f'{statistics.median(int(r["cycles"]) for r in base)/cycles:.3f}'
        summary.append(f"| {platform} | {workload} | {n} | {impl} | PASS | {cycles} | {instructions} | {cpi} | {speedup} |")
    report = """# Benchmark results

All elements are checked against independent references by the benchmark.
This report also checks complete size/trial coverage and baseline checksums.
Values are medians across trials. Host/model runs validate the C adapter;
they provide no hardware cycles, CPI, or speedup evidence. Packing, dispatch,
and completion are inside the measured kernel call. DP acceleration and
CPU-native custom instructions require the respective teammates' implementations.
In-capture speedups use the baseline row on that capture's hardware. For the
proposal's final comparison, also capture the unmodified BaselineConfig run.

| Platform | Workload | N | Implementation | Correctness | Cycles | Instructions | CPI | Speedup |
|---|---|---:|---|---|---:|---:|---:|---:|
""" + "\n".join(summary) + "\n"
    return len(rows), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Summarize an existing CSV capture")
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be positive")
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    if args.csv:
        text = args.csv.read_text(encoding="utf-8")
        target = out / (args.csv.stem + "_report.md")
    else:
        text = subprocess.run([str(ROOT / "build/integrated_bench")],
                              check=True, capture_output=True, text=True).stdout
        (out / "host_baseline.csv").write_text(text, encoding="utf-8")
        target = out / "host_baseline_report.md"
    try:
        count, report = summarize(text,args.trials)
    except (ValueError, KeyError, TypeError) as error:
        raise SystemExit(str(error)) from error
    target.write_text(report,encoding="utf-8")
    print(f"Verified {count} measurements; report: {target}")


if __name__ == "__main__":
    main()
