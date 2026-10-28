"""Retain normal-load controls and capture fast-load primary rows on identical ELFs."""
import concurrent.futures
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
from benchmark_s8 import HEADER

run=Path(sys.argv[1])
controls=run/'normal-load-controls'
controls.mkdir(exist_ok=True)
sim=Path('/workspace/chipyard/sims/verilator/simulator-chipyard.harness-BaselineConfig')

def check(n):
    stem=f'BaselineConfig-int8_matmul-{n}'
    for suffix in ('.json','.log'):
        shutil.copy2(run/(stem+suffix),controls/(stem+suffix))
    old=json.loads((controls/(stem+'.json')).read_text())
    binary=run/(stem+'.riscv')
    cmd=[str(sim),'+permissive','+loadmem='+str(binary),'+permissive-off',str(binary)]
    log=controls/(stem+'.fast.log')
    print('CALIBRATE N='+str(n),flush=True)
    with log.open('w') as out:
        code=subprocess.run(['stdbuf','-oL']+cmd,stdout=out,stderr=subprocess.STDOUT,timeout=1200).returncode
    text=log.read_text()
    rows=list(csv.DictReader(io.StringIO(HEADER+'\n'+'\n'.join(
        l for l in text.splitlines() if l.startswith('int8_matmul,')))))
    inputs=[l for l in text.splitlines() if l.startswith('INPUT,')]
    assert code==0 and 'Verilog $finish' in text and len(rows)==3 and all(r['status']=='PASS' for r in rows)
    assert inputs==old['input']
    assert [(r['cycles'],r['instructions'],r['checksum']) for r in rows]==[
        (r['cycles'],r['instructions'],r['checksum']) for r in old['records']]
    data={'status':'PASS','exit_code':code,'records':rows,'input':inputs,'run_command':cmd,
          'normal_load_control':str(controls/(stem+'.json'))}
    shutil.copy2(log,run/(stem+'.log'))
    (run/(stem+'.json')).write_text(json.dumps(data,indent=2))
    print('CALIBRATION PASS N='+str(n),flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(check,(1,4)))
(controls/'result.json').write_text(json.dumps({'status':'PASS','sizes':[1,4],
    'comparison':'Exact per-trial cycles, instructions, checksum and input fingerprints on identical ELFs.'},indent=2))
