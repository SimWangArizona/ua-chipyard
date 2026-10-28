#!/usr/bin/env python3
"""Build baseline and isolated fresh combined outputs; execute all S7 gates."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
CHIP=Path('/workspace/chipyard')


def main():
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    directory=ROOT/'results'/(stamp+'-s7-build')
    directory.mkdir(parents=True)
    tmp=ROOT/'build/java-tmp'; tmp.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env['_JAVA_OPTIONS']='-Xmx3G -XX:ActiveProcessorCount=2 -Djava.io.tmpdir='+str(tmp)
    # A new directory forces fresh RTL/Verilator outputs; shared toolchain/Scala caches remain reusable.
    fresh_dir=CHIP/'sims/verilator'/('s7-fresh-'+stamp)
    fresh_dir.mkdir()
    fresh=fresh_dir/'simulator-chipyard.harness-FineGrainedConfig'
    report={'stage':'s7-build','status':'FAIL','utc':stamp,'fresh_output_directory':str(fresh_dir),'commands':[]}
    try:
        subprocess.run([sys.executable,ROOT/'scripts/install_s5.py'],env=env,check=True)
        jobs=[('baseline-build',['make','CONFIG=BaselineConfig','-j2'],CHIP/'sims/verilator'),
              ('fresh-combined-build',['make','CONFIG=FineGrainedConfig','sim_dir='+str(fresh_dir),'-j2'],CHIP/'sims/verilator'),
              ('s7-checks',[sys.executable,ROOT/'scripts/verify_s7.py','--fresh-simulator',fresh],ROOT)]
        for name,cmd,cwd in jobs:
            report['commands'].append([str(x) for x in cmd])
            log=directory/(name+'.log')
            print('Running '+name+'; log: '+str(log),flush=True)
            with log.open('wb') as output:
                subprocess.run(cmd,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
            if name=='fresh-combined-build':
                (ROOT/'build/s7-fresh-simulator.path').write_text(str(fresh)+'\n')
        report['status']='PASS'
    except (OSError,subprocess.CalledProcessError) as exc: report['reason']=str(exc)
    except KeyboardInterrupt: report.update(status='INTERRUPTED',reason='Stopped by user')
    (directory/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('S7 '+report['status']+'; evidence: '+str(directory),flush=True)
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())
