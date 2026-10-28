"""Validate and archive the prepared English-language benchmark handoff."""
import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from contextlib import nullcontext
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE / 'fine-grained-benchmark-handoff/fine-grained'
ORIGINAL = HERE / 'fine-grained'
ARCHIVE = HERE / 'fine-grained-benchmark-handoff.zip'


def main():
    files = [p for p in ROOT.rglob('*') if p.is_file() and p.name != 'PACKAGE_SHA256.json']
    for path in files:
        text = path.read_text(encoding='utf-8')
        assert not any('\u4e00' <= char <= '\u9fff' for char in text), path
        if path.suffix == '.py':
            ast.parse(text, filename=str(path))
    # Verify that handoff preparation did not change the proven implementation.
    for name in ('include', 'tests'):
        for original in (ORIGINAL / name).iterdir():
            if original.is_file():
                assert original.read_bytes() == (ROOT / name / original.name).read_bytes()
    for name in ('rocket-chip.patch', 'FineGrainedConfig.scala', 'benchmarks/native_kernels.c',
                 'scripts/benchmark_s8.py', 'scripts/check_s8_baseline_code.py',
                 'scripts/install_s4.py', 'scripts/install_s5.py', 'scripts/verify.py'):
        assert (ROOT / name).read_bytes() == (ORIGINAL / name).read_bytes(), name
    for original in (ORIGINAL / 'benchmarks/common').iterdir():
        if original.is_file():
            assert original.read_bytes() == (ROOT / 'benchmarks/common' / original.name).read_bytes()
    refs = ROOT / 'reference-results'
    records = []
    cases = sorted(refs.glob('*Config-*.json'))
    assert len(cases) == 24
    for case in cases:
        data = json.loads(case.read_text())
        log = case.with_suffix('.log').read_text()
        assert data['status'] == 'PASS' and data['exit_code'] == 0
        assert 'Verilog $finish' in log
        expected = 3 if case.name.startswith('BaselineConfig-') else 6
        assert len(data['records']) == expected
        assert all(row['status'] == 'PASS' for row in data['records'])
        records.extend(data['records'])
    assert len(records) == 108
    with (refs / 'paired.csv').open(newline='') as stream:
        assert len(list(csv.DictReader(stream))) == 72
    # Exercise the unchanged teammate reporter against the primary historical CSV.
    validation = HERE / 'fine-grained-handoff-validation'
    (validation / 'reporter').mkdir(parents=True, exist_ok=True)
    (validation / 'extracted').mkdir(parents=True, exist_ok=True)
    with nullcontext(validation / 'reporter') as temporary:
        reporter = Path(temporary) / 'run_benchmarks.py'
        reporter.write_bytes((ROOT / 'benchmarks/common/run_benchmarks.py').read_bytes())
        subprocess.run([sys.executable, str(reporter), '--csv', str(refs / 'paired.csv')],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert (Path(temporary) / 'results/rocket_report.md').is_file()
    manifest = {'algorithm': 'SHA256', 'files': {
        str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(files)}}
    (ROOT / 'PACKAGE_SHA256.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'scripts/preflight_handoff.py'), '--offline'], check=True)
    with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob('*')):
            if path.is_file():
                archive.write(path, 'fine-grained/' + path.relative_to(ROOT).as_posix())
    with nullcontext(validation / 'extracted') as temporary:
        with zipfile.ZipFile(ARCHIVE) as archive:
            assert archive.testzip() is None
            archive.extractall(temporary)
        extracted = Path(temporary) / 'fine-grained'
        subprocess.run([sys.executable, str(extracted / 'scripts/preflight_handoff.py'), '--offline'], check=True)
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    ARCHIVE.with_suffix('.zip.sha256').write_text(digest + '  ' + ARCHIVE.name + '\n', encoding='ascii')
    print('PASS: source equality, English text scan, Python syntax, 24 historical simulator logs, common reporter, extracted archive hashes')
    print('Archive: ' + str(ARCHIVE))
    print('Bytes: ' + str(ARCHIVE.stat().st_size))
    print('SHA256: ' + digest)
    print('Docker was unavailable: no new simulator build or hardware benchmark was executed during packaging.')


if __name__ == '__main__':
    main()
