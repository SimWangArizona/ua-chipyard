#!/usr/bin/env python3
"""Install the cumulative patch and build the two benchmark configurations."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHIP = Path('/workspace/chipyard')


def main():
    subprocess.run([sys.executable, str(ROOT / 'scripts/preflight_handoff.py')], check=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run = ROOT / 'results' / (stamp + '-handoff-build')
    run.mkdir(parents=True)
    temp = ROOT / 'build/java-tmp'
    temp.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['_JAVA_OPTIONS'] = '-Xmx3G -XX:ActiveProcessorCount=2 -Djava.io.tmpdir=' + str(temp)
    result = {'status': 'FAIL', 'commands': [], 'logs': [], 'simulators': []}
    try:
        steps = [('install', [sys.executable, str(ROOT / 'scripts/install_s5.py')], ROOT)]
        steps += [(config, ['make', 'CONFIG=' + config, '-j2'], CHIP / 'sims/verilator')
                  for config in ('BaselineConfig', 'FineGrainedConfig')]
        for name, command, cwd in steps:
            log = run / (name + '.log')
            result['commands'].append(command)
            result['logs'].append(str(log))
            print('Running ' + name + '; log: ' + str(log), flush=True)
            with log.open('wb') as output:
                subprocess.run(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
        for config in ('BaselineConfig', 'FineGrainedConfig'):
            simulator = CHIP / 'sims/verilator' / ('simulator-chipyard.harness-' + config)
            if not simulator.is_file():
                raise RuntimeError('Build returned without expected simulator: ' + str(simulator))
            result['simulators'].append(str(simulator))
        result['status'] = 'PASS'
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        result['reason'] = str(error)
    except KeyboardInterrupt:
        result.update(status='INTERRUPTED', reason='Interrupted by user; inspect remaining build processes before retrying')
    (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('BUILD ' + result['status'] + '; evidence: ' + str(run), flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
