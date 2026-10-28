"""Write a clearly labelled partial report from completed S8 cases only."""
import json
from pathlib import Path
import statistics
import sys
from benchmark_s8 import ROOT, SIZES

run=Path(sys.argv[1])
data={}
for config in ('BaselineConfig','FineGrainedConfig'):
    for w in ('int8_matmul','floyd_warshall'):
        for n in SIZES:
            p=run/f'{config}-{w}-{n}.json'
            if p.exists():
                case=json.loads(p.read_text())
                data[(config,w,n)]=case
passed=sum(d['status']=='PASS' for d in data.values())
summary=json.loads((run/'result.json').read_text()) if (run/'result.json').exists() else {}
complete=passed==24 and summary.get('status')=='PASS' and summary.get('full_s8') is True
lines=['# S8 Benchmark Progress','',
       ('**COMPLETE / PASS:** 24/24 cases passed. See `benchmark_report.md` for the complete S8 report.' if complete else
        f'**RUNNING / PARTIAL:** {passed}/24 cases have passed. This is not a completed S8 report.'),
       f'Evidence: `{run}`. Only complete, normally finished cases are included.','',
       '| Workload | N | Baseline cycles | Native cycles | Cycle speedup |',
       '|---|---:|---:|---:|---:|']
for w in ('int8_matmul','floyd_warshall'):
    for n in SIZES:
        values=[]
        for config,impl in (('BaselineConfig','baseline'),('FineGrainedConfig','custom')):
            case=data.get((config,w,n))
            values.append(statistics.median(int(r['cycles']) for r in case['records'] if r['implementation']==impl)
                          if case and case['status']=='PASS' else None)
        bc,nc=values
        lines.append(f'| {w} | {n} | {bc if bc is not None else "Pending"} | {nc if nc is not None else "Pending"} | {f"{bc/nc:.3f}x" if bc is not None and nc is not None else "Pending"} |')
lines += ['', 'Each case preserves one verified warm-up and three trials. Golden checks compare every output element. Baseline software runs on BaselineConfig; custom adapters run on FineGrainedConfig. Full metrics, CPI, checksums and configuration manifests remain in the timestamped evidence. The final report will be `benchmark_report.md` after the complete matrix passes.']
(ROOT/'benchmark_progress.md').write_text('\n'.join(lines)+'\n')
print(f'S8 progress: {passed}/24 cases PASS',flush=True)
