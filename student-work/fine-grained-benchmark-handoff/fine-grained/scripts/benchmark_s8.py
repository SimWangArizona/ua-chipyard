"""Run the common owner's benchmark on real baseline/native Rocket simulators."""
import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
import difflib
from pathlib import Path
import statistics
import subprocess
import shutil
import time
from datetime import datetime, timezone
from check_s8_baseline_code import check as check_baseline_code

ROOT = Path(__file__).resolve().parents[1]
CHIP = Path('/workspace/chipyard')
SIZES = (1, 4, 7, 8, 16, 32)
HEADER = 'workload,size,implementation,trial,platform,status,cycles,instructions,cpi,host_elapsed_ns,checksum'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--resume', type=Path)
    ap.add_argument('--timeout', type=int, default=28800)
    ap.add_argument('--workers', type=int, choices=range(1,9), default=6)
    ap.add_argument('--sizes', nargs='+', type=int, choices=SIZES, default=list(SIZES))
    args = ap.parse_args()
    sizes=sorted(set(args.sizes))
    run = args.resume or ROOT/'results'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-s8')
    run.mkdir(parents=True, exist_ok=True)
    snapshot = ROOT/'benchmarks/common'
    driver = (snapshot/'benchmark.c').read_text()
    driver = driver.replace('const size_t sizes[] = {1,4,7,8,16,32};', 'const size_t sizes[] = {ECE562_SINGLE_N};')
    driver = driver.replace('if (instructions) printf("%.6f",(double)cycles/(double)instructions);', '/* CPI is computed on the host; no target floating-point formatting. */')
    driver = driver.replace('if (dot) prepare_dot(n); else prepare_dp(n);', '''if (dot) prepare_dot(n); else prepare_dp(n);
        uint64_t ih = UINT64_C(14695981039346656037);
        for (size_t x = 0; x < n*n; ++x) {
            if (dot) { ih ^= (uint8_t)a[x]; ih *= UINT64_C(1099511628211);
                       ih ^= (uint8_t)b[x]; ih *= UINT64_C(1099511628211); }
            else { ih ^= (uint32_t)input[x]; ih *= UINT64_C(1099511628211); }
        }
        printf("INPUT,%s,%zu,%" PRIu64 "\\n", dot ? "int8_matmul" : "floyd_warshall", n, ih);''')
    # RV64 size_t is unsigned long; nano printf does not implement the z modifier.
    driver = driver.replace('%zu','%lu')
    if args.resume and (run/'driver.c').read_text() != driver:
        raise RuntimeError('Driver changed; create a new run instead of mixing results')
    (run/'driver.c').write_text(driver)
    (run/'driver-compatibility.patch').write_text(''.join(difflib.unified_diff(
        (snapshot/'benchmark.c').read_text().splitlines(True),driver.splitlines(True),
        fromfile='common/benchmark.c',tofile='driver.c')))
    manifest = {'source_sha256': {p.name:sha(p) for p in snapshot.iterdir() if p.is_file()},
                'native_sha256':sha(ROOT/'benchmarks/native_kernels.c'), 'driver_sha256':sha(run/'driver.c'),
                'trials':3,'sizes':sizes,'timeout_seconds':args.timeout,'workers':args.workers,'simulators':{},'binaries':{},
                'compiler':subprocess.check_output(['riscv64-unknown-elf-gcc','--version'],text=True).splitlines()[0]}
    manifest['instruction_sources']={str(p.relative_to(ROOT)):sha(p)
        for p in [ROOT/'FineGrainedConfig.scala',ROOT/'rocket-chip.patch',*sorted((ROOT/'include').glob('*.h'))]}
    rocket=CHIP/'generators/rocket-chip'
    manifest['rocket_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=rocket,text=True).strip()
    (run/'rocket.diff').write_text(subprocess.check_output(['git','diff'],cwd=rocket,text=True))
    if args.resume:
        old=json.loads((run/'manifest.json').read_text())
        for key in ('source_sha256','native_sha256','driver_sha256'):
            if old[key]!=manifest[key]: raise RuntimeError('Sources changed; do not reuse earlier measurements')
        if old.get('compiler')!=manifest['compiler']:
            raise RuntimeError('Compiler version changed; create a new run')
        if 'instruction_sources' in old and old['instruction_sources']!=manifest['instruction_sources']:
            raise RuntimeError('Instruction headers/configuration changed; create a new run')
    jobs = []
    for config in ('BaselineConfig','FineGrainedConfig'):
        sim = CHIP/'sims/verilator'/('simulator-chipyard.harness-'+config)
        if not sim.exists(): raise RuntimeError('Missing simulator '+str(sim))
        manifest['simulators'][config] = {'path':str(sim),'sha256':sha(sim)}
        if args.resume and old['simulators'][config]!=manifest['simulators'][config]:
            raise RuntimeError('Simulator changed; create a new run')
        for workload, define in (('int8_matmul','DOT_ONLY'),('floyd_warshall','DP_ONLY')):
            for n in sizes:
                stem = f'{config}-{workload}-{n}'
                binary = run/(stem+'.riscv')
                cmd = ['riscv64-unknown-elf-gcc','-std=gnu99','-O2','-Wall','-Wextra','-Werror','-fno-tree-vectorize',
                       '-march=rv64imafd','-mabi=lp64d','-mcmodel=medany','-I',str(snapshot),'-I',str(ROOT/'include'),
                       '-DECE562_RISCV_COUNTERS',f'-D{define}',f'-DECE562_SINGLE_N={n}',
                       '-specs=htif_nano.specs','-static','-T','htif.ld',str(run/'driver.c'),
                       str(snapshot/'dot_bench.c'),str(snapshot/'dp_bench.c')]
                if config == 'FineGrainedConfig': cmd += ['-DECE562_CUSTOM',str(ROOT/'benchmarks/native_kernels.c')]
                cmd += ['-o',str(binary)]
                if not binary.exists() or (args.resume and stem not in old.get('binaries',{})):
                    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    (run/(stem+'.build.log')).write_text('$ '+' '.join(cmd)+'\n'+result.stdout)
                    if result.returncode: raise RuntimeError(result.stdout)
                sim_command=[str(sim),'+permissive','+loadmem='+str(binary),'+permissive-off',str(binary)]
                previous=run/(stem+'.json')
                if previous.exists() and json.loads(previous.read_text())['status']=='PASS':
                    sim_command=json.loads(previous.read_text()).get('run_command',[str(sim),str(binary)])
                manifest['binaries'][stem]={'sha256':sha(binary),'compile_command':cmd,
                                             'run_command':sim_command}
                if args.resume and stem in old.get('binaries',{}) and old['binaries'][stem]['sha256']!=sha(binary):
                    raise RuntimeError('Binary changed; create a new run')
                dis = subprocess.check_output(['riscv64-unknown-elf-objdump','-d',str(binary)],text=True)
                (run/(stem+'.disassembly.txt')).write_text(dis)
                # Decode executable instruction words independently of objdump's mnemonic support.
                words = [int(line.split(':',1)[1].split()[0],16) for line in dis.splitlines()
                         if ':' in line and line.split(':',1)[0].strip().isalnum()
                         and line.split(':',1)[1].split() and len(line.split(':',1)[1].split()[0]) == 8]
                custom = [w for w in words if w & 127 == 11]
                if config == 'BaselineConfig' and custom: raise RuntimeError('Baseline contains custom opcode')
                if config == 'FineGrainedConfig' and not all(any((w>>25)==f and ((w>>12)&7)==0 for w in custom) for f in (1,3)):
                    raise RuntimeError('Native dot/min instructions missing')
                manifest['binaries'][stem]['custom_instruction_words']=[hex(w) for w in custom]
                jobs.append((config,workload,n,sim,binary,stem))
    # Independent cases have fresh simulator state; start expensive cases early.
    jobs.sort(key=lambda j:j[2]**3*(2 if j[0]=='FineGrainedConfig' else 1),reverse=True)
    check_baseline_code(run)
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Evidence: '+str(run),flush=True)
    def execute(job):
        config,workload,n,sim,binary,stem = job
        status = run/(stem+'.json')
        if status.exists() and json.loads(status.read_text())['status']=='PASS':
            saved=json.loads(status.read_text())
            raw=(run/(stem+'.log')).read_text(errors='replace')
            raw_rows=list(csv.DictReader(io.StringIO(HEADER+'\n'+'\n'.join(
                line for line in raw.splitlines() if line.startswith(workload+',')))))
            required={(impl,t) for impl in (('baseline',) if config=='BaselineConfig' else ('baseline','custom')) for t in (1,2,3)}
            if (saved['exit_code']!=0 or 'Verilog $finish' not in raw or raw_rows!=saved['records']
                or len(raw_rows)!=len(required) or {(r['implementation'],int(r['trial'])) for r in raw_rows}!=required
                or saved['input']!=[l for l in raw.splitlines() if l.startswith('INPUT,')]
                or len(saved['input'])!=1 or any(r['status']!='PASS' or int(r['size'])!=n
                    or int(r['cycles'])<=0 or int(r['instructions'])<=0 for r in raw_rows)):
                raise RuntimeError('Cached evidence failed revalidation: '+stem)
            print('RESUME '+stem,flush=True); return
        print('RUN '+stem,flush=True)
        log = run/(stem+'.log')
        if log.exists():
            history=run/'attempts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            history.mkdir(parents=True,exist_ok=True)
            shutil.copy2(log,history/log.name)
            if status.exists(): shutil.copy2(status,history/status.name)
            else: (history/(stem+'.json')).write_text(json.dumps({'status':'INTERRUPTED',
                  'reason':'Previous incomplete run; raw log retained before retry.'},indent=2))
        started=time.monotonic()
        with log.open('w') as out:
            sim_command=[str(sim),'+permissive','+loadmem='+str(binary),'+permissive-off',str(binary)]
            try: code = subprocess.run(['stdbuf','-oL']+sim_command,stdout=out,stderr=subprocess.STDOUT,timeout=args.timeout).returncode
            except subprocess.TimeoutExpired: code = -1
        text = log.read_text(errors='replace')
        lines = [line for line in text.splitlines() if line.startswith(workload+',')]
        records = list(csv.DictReader(io.StringIO(HEADER+'\n'+'\n'.join(lines))))
        expected = 3 if config == 'BaselineConfig' else 6
        implementations=('baseline',) if config=='BaselineConfig' else ('baseline','custom')
        observed={(r['implementation'],int(r['trial'])) for r in records}
        required={(impl,trial) for impl in implementations for trial in (1,2,3)}
        passed = (code == 0 and 'Verilog $finish' in text and len(records)==expected and observed==required
                  and all(r['status']=='PASS' and int(r['size'])==n and int(r['cycles'])>0
                          and int(r['instructions'])>0 for r in records)
                  and sum(l.startswith('INPUT,') for l in text.splitlines())==1)
        status.write_text(json.dumps({'status':'PASS' if passed else 'FAIL','exit_code':code,'records':records,
                                     'elapsed_seconds':time.monotonic()-started,'timeout_seconds':args.timeout,
                                     'run_command':sim_command,
                                     'input':[l for l in text.splitlines() if l.startswith('INPUT,')]},indent=2))
        print(('PASS ' if passed else 'FAIL ')+stem,flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(execute,jobs))
    rows=[]; stats={}; failures=[]
    for config,workload,n,sim,binary,stem in jobs:
        data=json.loads((run/(stem+'.json')).read_text())
        if data['status']!='PASS': failures.append(stem); continue
        stats[(config,workload,n)]=data
        for r in data['records']:
            r['config']=config
            r['cpi']=str(int(r['cycles'])/int(r['instructions']))
            rows.append(r)
    for w in ('int8_matmul','floyd_warshall'):
        for n in sizes:
            a=stats.get(('BaselineConfig',w,n)); b=stats.get(('FineGrainedConfig',w,n))
            if a and b and (a['input']!=b['input'] or len({r['checksum'] for d in (a,b) for r in d['records']})!=1):
                failures.append(f'input/output mismatch {w}/{n}')
    expected_rows=18*len(sizes)
    if len(rows)!=expected_rows: failures.append(f'Expected {expected_rows} records; got {len(rows)}')
    with (run/'results.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=HEADER.split(',')+['config']); writer.writeheader(); writer.writerows(rows)
    # Feed the owner's unchanged reporter only the primary BaselineConfig baseline
    # and native custom rows, avoiding mixing the secondary baseline into medians.
    with (run/'paired.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=HEADER.split(',')+['config']); writer.writeheader()
        writer.writerows(r for r in rows if r['config']=='BaselineConfig' or r['implementation']=='custom')
    if not failures:
        common=subprocess.run(['python3',str(snapshot/'run_benchmarks.py'),'--csv',str(run/'paired.csv')],
                              text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (run/'common-reporter.log').write_text(common.stdout)
        if common.returncode: failures.append('Common reporter failed')
        else:
            common_report=(snapshot/'results/rocket_report.md').read_text()
            (run/'common_report_raw.md').write_text(common_report)
            (run/'common_report.md').write_text(common_report.replace(
                'Custom and RoCC implementations are pending until hardware wrappers are provided.',
                'Native custom results are integrated here. Baseline rows are from BaselineConfig; custom rows are from FineGrainedConfig. RoCC is outside scope.'))
    full=sizes==list(SIZES)
    label='FAIL' if failures else ('PASS' if full else 'FOCUSED PROFILE PASS; full S8 remains incomplete')
    calibration_note=''
    if (run/'normal-load-controls/result.json').exists():
        calibration=json.loads((run/'normal-load-controls/result.json').read_text())
        if calibration['status']=='PASS':
            calibration_note=' Normal-load N=1/N=4 controls are saved separately and reproduce exactly the same per-trial cycles, instructions, input fingerprints and output checksums as fast loading.'
    report=['# S8 Rocket Benchmark Report','',f"Status: **{label}**. Sizes: {sizes}. Evidence: `{run}`.",'',
            'Unmodified common `dot_bench.c` and `dp_bench.c` run on BaselineConfig. Native adapters run on FineGrainedConfig. Common INT64 matrix reference and independent Dijkstra reference check every output element after one warm-up and each of three trials. Input fingerprints and output checksums must match across configurations.', '',
            'Baseline kernel source files match the supplied files byte for byte. Their executable instruction words also match across baseline/native binaries, as recorded in `baseline-code-equality.json`. The baseline-only ELF contains no custom opcode; native ELFs contain the DOT4_ACC/ADD_MIN opcode, funct3 and funct7 fields. Initial nano-printf `%zu` failures are retained in the earlier failed run; the compatibility patch fixes formatting in the integration driver.', '',
            'Both builds use GCC -O2, -fno-tree-vectorize, rv64imafd/lp64d, and the same HTIF runtime. Counters surround only synchronous kernel dispatch; input preparation, output reset, golden checks and printing are excluded. Native lane packing is included. CPI is calculated on the host to avoid target floating-point formatting. SimDRAM fast ELF loading (+loadmem) shortens unmeasured startup. Actual loading commands are retained per case. All primary rows use fast loading.'+calibration_note+' Numbers below are medians of three trials; speedup is baseline median cycles / native median cycles.', '',
            '| Workload | N | Baseline cycles | Native cycles | Baseline instructions | Native instructions | Baseline CPI | Native CPI | Speedup |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for w in ('int8_matmul','floyd_warshall'):
        for n in sizes:
            def median(config,impl,key):
                return statistics.median(float(r[key]) for r in rows if r['config']==config and r['workload']==w and int(r['size'])==n and r['implementation']==impl)
            if ('BaselineConfig',w,n) not in stats or ('FineGrainedConfig',w,n) not in stats: continue
            bc=median('BaselineConfig','baseline','cycles'); nc=median('FineGrainedConfig','custom','cycles')
            bi=median('BaselineConfig','baseline','instructions'); ni=median('FineGrainedConfig','custom','instructions')
            report.append(f'| {w} | {n} | {bc:.0f} | {nc:.0f} | {bi:.0f} | {ni:.0f} | {median("BaselineConfig","baseline","cpi"):.3f} | {median("FineGrainedConfig","custom","cpi"):.3f} | {bc/nc:.3f}x |')
    if not failures:
        report += ['', 'Measured observations:', '']
        for w in ('int8_matmul','floyd_warshall'):
            speedups=[]
            for n in sizes:
                base=statistics.median(int(r['cycles']) for r in rows if r['config']=='BaselineConfig'
                                       and r['workload']==w and int(r['size'])==n)
                native=statistics.median(int(r['cycles']) for r in rows if r['implementation']=='custom'
                                         and r['workload']==w and int(r['size'])==n)
                speedups.append(base/native)
            report.append(f'- {w}: native is faster in {sum(x>1 for x in speedups)}/{len(sizes)} sizes; N={sizes[-1]} cycle speedup is {speedups[-1]:.3f}x. Values below 1x represent a slowdown.')
        report += ['', 'Secondary ordinary-software control on the native core:', '',
                   '| Workload | N | BaselineConfig cycles | FineGrainedConfig baseline cycles | Ratio |',
                   '|---|---:|---:|---:|---:|']
        for w in ('int8_matmul','floyd_warshall'):
            for n in sizes:
                base=statistics.median(int(r['cycles']) for r in rows if r['config']=='BaselineConfig'
                                       and r['workload']==w and int(r['size'])==n)
                control=statistics.median(int(r['cycles']) for r in rows if r['config']=='FineGrainedConfig'
                                          and r['implementation']=='baseline' and r['workload']==w and int(r['size'])==n)
                report.append(f'| {w} | {n} | {base} | {control} | {base/control:.3f}x |')
    report += ['',f'{len(rows)} measured records retained. Failures: {failures}. A passing selected matrix checks {6*len(sizes)} warm-ups and {expected_rows} measured invocations ({24*len(sizes)} kernel calls), comparing {24*sum(n*n for n in sizes):,} output elements with independent references.','',
               'Instruction count and cycles need not decrease together: native lane packing adds instructions while DOT4 bypasses the baseline scalar multiplier (one bit per cycle, with early-out disabled). The ADD_MIN adapter preserves INF checks and writes the returned minimum for every valid candidate; the original baseline stores only when the distance improves. These adapter costs are included.', '',
               'FineGrainedConfig also executes the original baseline as a secondary control; these rows are retained in CSV. Its baseline runs before custom, so cache/order effects may affect comparisons. The native executable includes extra dispatch/code and may have a different instruction-cache layout. Small cases include fence/CSR counter and dispatch overhead; no overhead subtraction is applied. Speedup assumes equal clock frequency and is not physical timing or end-to-end application speedup. ADD_MAX is covered by earlier unit tests, not these workloads. RoCC is outside this stage. S3 remains deferred and the optional full S6 suite remains uncompleted.', '',
               'INT8 uses four signed packed lanes with zero-padding for N=1 and N=7 tails, including strided B-column extraction. DP retains the original loop order and INF guard and uses ADD_MIN. These straightforward adapters include packing costs and are not assumed to improve speed without measurements.', '',
               'Artifacts: `results.csv`, `manifest.json` (original source and simulator hashes), per-case compiler logs, disassembly, simulator logs, and JSON records. To resume, run `python3 scripts/benchmark_s8.py --resume '+str(run)+'`.']
    (run/'report.md').write_text('\n'.join(report)+'\n')
    (ROOT/'benchmark_report.md').write_text('\n'.join(report)+'\n')
    (run/'result.json').write_text(json.dumps({'status':'FAIL' if failures else 'PASS','full_s8':full,'sizes':sizes,'records':len(rows),'failures':failures},indent=2))
    print('S8 '+('FAIL' if failures else 'PASS')+'; report: '+str(ROOT/'benchmark_report.md'),flush=True)
    if failures: raise SystemExit(1)

if __name__ == '__main__': main()
