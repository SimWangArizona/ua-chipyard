#!/usr/bin/env python3
"""Check shipped files and evidence, then the supported course environment."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CHIP = Path('/workspace/chipyard')
REV = '55bcad0f59436de98ea510334121de8546b9e9d7'


def require(condition, message):
    if not condition:
        raise SystemExit('BLOCKED: ' + message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Check the package without requiring Docker or a toolchain')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'PACKAGE_SHA256.json').read_text())
    for name, expected in manifest['files'].items():
        path = ROOT / name
        require(path.is_file(), 'Missing package file: ' + name)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                'Package file changed: ' + name + '; retain a pristine package for verification')
    refs = ROOT / 'reference-results'
    result = json.loads((refs / 'result.json').read_text())
    require(result['status'] == 'PASS' and result['full_s8'] and result['records'] == 108,
            'Historical full-run summary is incomplete')
    with (refs / 'results.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == 108 and all(row['status'] == 'PASS' for row in rows),
            'Historical CSV is incomplete or contains failures')
    code = json.loads((refs / 'baseline-code-equality.json').read_text())
    require(code['status'] == 'PASS' and len(code['comparisons']) == 24,
            'Historical baseline machine-code comparison is incomplete')
    print('PASS: package hashes; historical 108 records and 24 baseline code comparisons')
    if args.offline:
        return
    require(CHIP.is_dir(), 'Run inside the UA course Docker container at /workspace/chipyard')
    for command in ('git', 'make', 'java', 'verilator', 'g++', 'stdbuf',
                    'riscv64-unknown-elf-gcc', 'riscv64-unknown-elf-objdump'):
        require(shutil.which(command) is not None, 'Missing ' + command + '; source /workspace/chipyard/env.sh')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CHIP / 'generators/rocket-chip', text=True).strip()
    require(revision == REV, 'Unsupported Rocket revision: ' + revision)
    course = CHIP / 'generators/chipyard/src/main/scala/config/CourseRocketConfig.scala'
    require(course.is_file(), 'CourseRocketConfig.scala is not installed; run the course configuration installer')
    require(course.read_text() == (ROOT / 'course-reference/CourseRocketConfig.scala').read_text(),
            'Course baseline differs from the supplied reference; inspect before benchmarking')
    print('PASS: supported Rocket revision, course baseline, and required tools')


if __name__ == '__main__':
    main()
