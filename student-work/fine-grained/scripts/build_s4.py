#!/usr/bin/env python3
"""Restore/build/test S4 with bounded JVM memory; run after source env.sh."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHIP = Path('/workspace/chipyard')


def main(stage='s4'):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence = ROOT/'results'/(stamp+'-'+stage+'-build')
    evidence.mkdir(parents=True)
    temporary = ROOT/'build/java-tmp'
    temporary.mkdir(parents=True,exist_ok=True)
    environment = os.environ.copy()
    # _JAVA_OPTIONS is processed after the environment's default 8 GB heap.
    # Limits apply to this build only, not Docker or the user's system settings.
    environment['_JAVA_OPTIONS'] = '-Xmx3G -XX:ActiveProcessorCount=2 -Djava.io.tmpdir=' + str(temporary)
    report = {'status':'FAIL','utc':stamp,'jvm_options':environment['_JAVA_OPTIONS'],'commands':[]}
    try:
        installer='install_s5.py' if stage=='s5' else 'install_s4.py'
        subprocess.run([sys.executable,ROOT/'scripts'/installer],check=True,env=environment)
        jobs = (
            ('build',['make','CONFIG=FineGrainedDPConfig','-j2'],CHIP/'sims/verilator'),
            ('dp',[sys.executable,ROOT/'scripts/verify.py','dp','--timeout','600'],ROOT),
            ('dp-pipeline',[sys.executable,ROOT/'scripts/verify.py','dp-pipeline','--timeout','600'],ROOT))
        if stage=='s5':
            jobs = (
                ('dot-build',['make','CONFIG=FineGrainedDotConfig','-j2'],CHIP/'sims/verilator'),
                ('dot',[sys.executable,ROOT/'scripts/verify.py','dot','--timeout','600'],ROOT),
                ('dot-pipeline',[sys.executable,ROOT/'scripts/verify.py','dot-pipeline','--timeout','600'],ROOT),
                ('dp-regression-build',['make','CONFIG=FineGrainedDPConfig','-j2'],CHIP/'sims/verilator'),
                ('dp-regression',[sys.executable,ROOT/'scripts/verify.py','dp','--timeout','600'],ROOT),
                ('dp-pipeline-regression',[sys.executable,ROOT/'scripts/verify.py','dp-pipeline','--timeout','600'],ROOT))
        for name,command,cwd in jobs:
            report['commands'].append([str(x) for x in command])
            log = evidence/(name+'.log')
            print('Running '+name+'; log: '+str(log),flush=True)
            with log.open('wb') as output:
                subprocess.run(command,cwd=cwd,env=environment,stdout=output,stderr=subprocess.STDOUT,check=True)
        report['status'] = 'PASS'
    except (OSError,subprocess.CalledProcessError) as exc:
        report['reason'] = str(exc)
    except KeyboardInterrupt:
        report.update(status='INTERRUPTED',reason='Interrupted by user')
    (evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(stage.upper()+' '+report['status']+'; evidence: '+str(evidence),flush=True)
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())
