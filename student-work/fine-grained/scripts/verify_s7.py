#!/usr/bin/env python3
"""S7: patch replay, ordinary ISA, feature-gate traps, fresh-output reproduction."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
CHIP=Path('/workspace/chipyard')
CONFIGS={'baseline':'BaselineConfig','dot':'FineGrainedDotConfig',
         'dp':'FineGrainedDPConfig','combined':'FineGrainedConfig'}
ISA_TESTS=['rv64ui-p-simple','rv64ui-p-add','rv64ui-p-sub','rv64ui-p-beq',
           'rv64ui-p-ld','rv64ui-p-sd','rv64um-p-mul','rv64um-p-div']


class Blocked(Exception):
    pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part',choices=['all','patch','isa','traps','reproduce'],default='all')
    parser.add_argument('--timeout',type=int,default=300)
    parser.add_argument('--fresh-simulator',type=Path)
    parser.add_argument('--config',choices=list(CONFIGS),help='Select one configuration for isa/traps debugging')
    args=parser.parse_args()
    if args.config and args.part not in ('isa','traps'):
        parser.error('--config is only supported for isa/traps')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    result_dir=ROOT/'results'/(stamp+'-s7-'+args.part)
    result_dir.mkdir(parents=True)
    report={'stage':'s7','part':args.part,'config_filter':args.config,'utc':stamp,'status':'FAIL','commands':[],
            'simulators':{},'isa_tests':[],'trap_profiles':[]}
    for name in ['rocket-chip.patch','FineGrainedConfig.scala','include/fg_encoding.h',
                 'tests/test_traps.c','tests/trap_probes.S']:
        report.setdefault('source_sha256',{})[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    log=(result_dir/'run.log').open('w')

    def note(text):
        print(text,flush=True); log.write(text+'\n'); log.flush()

    def run(command,cwd=ROOT,echo=True,limit=None):
        command=[str(x) for x in command]
        report['commands'].append(command)
        note('$ '+' '.join(command))
        capture=result_dir/('command-%03d.log'%len(report['commands']))
        start=time.monotonic()
        with capture.open('wb') as output,capture.open('r',errors='replace') as reader:
            proc=subprocess.Popen(command,cwd=cwd,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
            chunks=[]
            try:
                while True:
                    text=reader.read()
                    if text:
                        chunks.append(text); log.write(text); log.flush()
                        if echo: print(text,end='',flush=True)
                    if proc.poll() is not None:
                        text=reader.read()
                        if text:
                            chunks.append(text); log.write(text); log.flush()
                            if echo: print(text,end='',flush=True)
                        break
                    if time.monotonic()-start>(limit or args.timeout):
                        raise RuntimeError('command timed out before validation completed')
                    time.sleep(0.2)
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGKILL); proc.wait()
            if proc.returncode:
                raise RuntimeError('command exit status '+str(proc.returncode))
            return ''.join(chunks)

    def simulator(key):
        config=CONFIGS[key]
        path=CHIP/'sims/verilator'/('simulator-chipyard.harness-'+config)
        if not path.is_file(): raise Blocked('Missing simulator '+str(path))
        report['simulators'][config]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        return path

    try:
        rocket=CHIP/'generators/rocket-chip'
        report['rocket_revision']=run(['git','rev-parse','HEAD'],rocket).strip()
        report['rocket_status']=run(['git','status','--short'],rocket).strip()
        if args.part in ('all','patch','reproduce'):
            run([sys.executable,ROOT/'scripts/install_s5.py'])
            report['patch_replay']='PASS: clean-base reconstruction equals installed source'
            clean=CHIP/('s7-clean-source-'+stamp)
            run(['git','clone','--shared','--no-checkout',rocket,clean])
            run(['git','checkout','--detach',report['rocket_revision']],clean)
            if run(['git','status','--porcelain'],clean).strip():
                raise RuntimeError('Reproduction checkout is not clean before patch')
            run(['git','apply','--check',ROOT/'rocket-chip.patch'],clean)
            run(['git','apply',ROOT/'rocket-chip.patch'],clean)
            run(['git','diff','--check'],clean)
            for name in ['ALU.scala','CustomInstructions.scala','IDecode.scala','RocketCore.scala']:
                relative=Path('src/main/scala/rocket')/name
                if (clean/relative).read_bytes()!=(rocket/relative).read_bytes():
                    raise RuntimeError('Clean-checkout source mismatch: '+name)
            report['clean_checkout_replay']={'status':'PASS','path':str(clean),'base_revision':report['rocket_revision']}
        if args.part in ('all','isa'):
            if not os.environ.get('RISCV'): raise Blocked('source /workspace/chipyard/env.sh first')
            isa_dir=Path(os.environ['RISCV'])/'riscv64-unknown-elf/share/riscv-tests/isa'
            for key in ([args.config] if args.config else ['baseline','combined']):
                sim=simulator(key)
                for name in ISA_TESTS:
                    binary=isa_dir/name
                    if not binary.is_file(): raise Blocked('Missing installed ISA test '+str(binary))
                    text=run([sim,binary])
                    if 'Verilog $finish' not in text or '*** FAILED ***' in text:
                        raise RuntimeError('ISA simulator did not finish normally: '+name)
                    report['isa_tests'].append({'config':CONFIGS[key],'test':name,'status':'PASS',
                                               'elf_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()})
                    note('ISA PASS '+CONFIGS[key]+' '+name)
        if args.part in ('all','traps'):
            for key,dot,dp,want_traps in [('baseline',0,0,8),('dot',1,0,6),('dp',0,1,4),('combined',1,1,2)]:
                if args.config and key!=args.config: continue
                sim=simulator(key)
                binary=result_dir/(key+'-traps.riscv')
                run(['riscv64-unknown-elf-gcc','-std=gnu99','-O2','-Wall','-Wextra','-Werror',
                     '-march=rv64imafd','-mabi=lp64d','-mcmodel=medany','-I',ROOT/'include',
                     '-DFG_ENABLE_DOT='+str(dot),'-DFG_ENABLE_DP='+str(dp),
                     '-specs=htif_nano.specs','-static','-T','htif.ld',
                     ROOT/'tests/test_traps.c',ROOT/'tests/trap_probes.S','-o',binary])
                dump=run(['riscv64-unknown-elf-objdump','-d',binary],echo=False)
                binary.with_suffix('.dump').write_text(dump)
                text=run([sim,binary])
                if 'FG PASS traps' not in text or 'traps='+str(want_traps)+' expected_traps='+str(want_traps) not in text:
                    raise RuntimeError('Trap marker/count mismatch: '+key)
                report['trap_profiles'].append({'config':CONFIGS[key],'status':'PASS',
                                               'probes':8,'traps':want_traps})
                note('TRAPS PASS '+CONFIGS[key])
        if args.part in ('all','reproduce'):
            marker=ROOT/'build/s7-fresh-simulator.path'
            fresh=args.fresh_simulator or (Path(marker.read_text().strip()) if marker.is_file() else
                CHIP/'sims/verilator/s7-fresh/simulator-chipyard.harness-FineGrainedConfig')
            if not fresh.is_file(): raise Blocked('Missing fresh-output reproduction simulator '+str(fresh))
            report['fresh_simulator']={'path':str(fresh),'sha256':hashlib.sha256(fresh.read_bytes()).hexdigest()}
            for gate,limit in [('all-hw',600),('pipeline',300)]:
                text=run([sys.executable,ROOT/'scripts/verify.py',gate,'--simulator',fresh],limit=limit+30)
                if 'PASS: '+gate not in text: raise RuntimeError('Fresh build gate missing PASS: '+gate)
            report['fresh_output_reproduction']='PASS'
        report['status']='PASS'; code=0
    except Blocked as exc:
        report.update(status='BLOCKED',reason=str(exc)); code=2
    except KeyboardInterrupt:
        report.update(status='INTERRUPTED',reason='Stopped by user'); code=130
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        report.update(status='FAIL',reason=str(exc)); code=1
    note('S7 '+args.part+(' '+args.config if args.config else '')+' '+report['status']+' '+report.get('reason',''))
    (result_dir/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    note('Evidence: '+str(result_dir)); log.close()
    return code


if __name__=='__main__':
    sys.exit(main())
