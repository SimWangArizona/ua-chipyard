"""Reuse the owner's reporter for a complete small profile while full runs continue."""
import csv
import json
from pathlib import Path
import subprocess
import sys
from benchmark_s8 import HEADER, ROOT
from check_s8_baseline_code import check

run=Path(sys.argv[1])
check(run)
rows=[]
for config in ('BaselineConfig','FineGrainedConfig'):
    for w in ('int8_matmul','floyd_warshall'):
        for n in (1,4,7,8):
            data=json.loads((run/f'{config}-{w}-{n}.json').read_text())
            assert data['status']=='PASS' and data['exit_code']==0
            for r in data['records']:
                if config=='FineGrainedConfig' and r['implementation']!='custom': continue
                r['config']=config
                r['cpi']=str(int(r['cycles'])/int(r['instructions']))
                rows.append(r)
for w in ('int8_matmul','floyd_warshall'):
    for n in (1,4,7,8):
        a=json.loads((run/f'BaselineConfig-{w}-{n}.json').read_text())
        b=json.loads((run/f'FineGrainedConfig-{w}-{n}.json').read_text())
        assert a['input']==b['input'] and len({r['checksum'] for d in (a,b) for r in d['records']})==1
assert len(rows)==48
capture=run/'paired-small.csv'
with capture.open('w',newline='') as out:
    writer=csv.DictWriter(out,fieldnames=HEADER.split(',')+['config'])
    writer.writeheader(); writer.writerows(rows)
common=ROOT/'benchmarks/common'
result=subprocess.run([sys.executable,str(common/'run_benchmarks.py'),'--csv',str(capture)],
                      stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(run/'small-common-reporter.log').write_text(result.stdout)
if result.returncode: raise RuntimeError(result.stdout)
report=(common/'results/rocket_report.md').read_text()
report=report.replace('# Benchmark results', '# S8 Small-Scale Benchmark Report')
report=report.replace('Custom and RoCC implementations are pending until hardware wrappers are provided.',
    'This **focused profile passes** for N=1,4,7,8. Full S8 is still running: N=16/32 native comparisons are not complete. Baseline rows are unmodified software on BaselineConfig; custom rows are native adapters on FineGrainedConfig. RoCC is outside scope.')
report += '\nThe selected 16 cases preserve one verified warm-up and three trials per implementation: 72 measured records including the native core baseline control. The table includes only the 48 primary paired records. Input fingerprints and output checksums match across configurations; independent references check every element. The baseline source files are byte-identical to the supplied files, and baseline kernel executable words match across both configurations (24 function comparisons across the prepared binaries).\n'
report += '\nBoth builds use -O2, -fno-tree-vectorize and rv64imafd/lp64d. Timing includes kernel dispatch and native packing; generation, reset, reference checking and printing are excluded. CPI is calculated on the host. Speedup below 1 means slower. Tiny cases include counter/dispatch overhead; native dispatch/code layout differs from the baseline-only program. These are cycle speedups assuming equal clock frequency, not measured physical timing. ADD_MAX remains covered by earlier unit tests rather than these workloads.\n'
report += f'\nEvidence: `{run}`. Files: `paired-small.csv`, per-case JSON/logs, `manifest.json`, `baseline-code-equality.json` and `normal-load-controls/result.json`. The final full report will be `benchmark_report.md`.\n'
(ROOT/'benchmark_report_small.md').write_text(report)
(run/'report-small.md').write_text(report)
print('PASS: focused report saved to '+str(ROOT/'benchmark_report_small.md'))
