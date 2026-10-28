"""Run host verification, or summarize an existing Rocket CSV capture."""
import argparse
import csv
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--csv", type=Path, help="Summarize captured CSV instead of running host code")
args = parser.parse_args()
out = ROOT / "results"
out.mkdir(exist_ok=True)
if args.csv:
    text = args.csv.read_text()
else:
    text = subprocess.run([str(ROOT / "build/integrated_bench")],
                          check=True, capture_output=True, text=True).stdout
    (out / "host_baseline.csv").write_text(text)
rows = list(csv.DictReader(text.splitlines()))
if not rows or any(r["status"] != "PASS" for r in rows):
    raise SystemExit("Missing results or failed correctness checks")
groups = {}
for r in rows:
    groups.setdefault((r["platform"], r["workload"], int(r["size"]), r["implementation"]), []).append(r)
summary = []
for (platform, workload, n, impl), trials in sorted(groups.items()):
    if len({r["checksum"] for r in trials}) != 1:
        raise SystemExit("Inconsistent outputs across trials")
    cycles = statistics.median(int(r["cycles"]) for r in trials) if trials[0]["cycles"] else None
    instructions = statistics.median(int(r["instructions"]) for r in trials) if trials[0]["instructions"] else None
    cpi = statistics.median(float(r["cpi"]) for r in trials) if trials[0]["cpi"] else None
    base = groups.get((platform, workload, n, "baseline"))
    speedup = "—"
    if cycles and base and all(r["cycles"] for r in base):
        if {r["checksum"] for r in base} != {r["checksum"] for r in trials}:
            raise SystemExit("Implementation checksum differs from baseline")
        speedup = f'{statistics.median(int(r["cycles"]) for r in base)/cycles:.3f}'
    summary.append(f"| {platform} | {workload} | {n} | {impl} | PASS | {cycles if cycles is not None else '—'} | {instructions if instructions is not None else '—'} | {f'{cpi:.3f}' if cpi is not None else '—'} | {speedup} |")
report = """# Benchmark results

Correctness checks compare every output element against an independent reference.
The table reports medians across trials. Host timings in the raw CSV are for
local execution only; Rocket cycles, CPI and speedup remain blank for host runs.
Custom and RoCC implementations are pending until hardware wrappers are provided.

| Platform | Workload | N | Implementation | Correctness | Cycles | Instructions | CPI | Speedup |
|---|---|---:|---|---|---:|---:|---:|---:|
""" + "\n".join(summary) + "\n"
target = out / ("rocket_report.md" if args.csv else "host_report.md")
target.write_text(report)
print(f"Verified {len(rows)} measurements; report: {target}")
