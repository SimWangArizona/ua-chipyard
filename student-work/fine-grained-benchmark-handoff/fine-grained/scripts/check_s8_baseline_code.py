"""Verify that the original baseline kernels have identical executable words."""
import hashlib
import json
from pathlib import Path
import re
import sys

def words(path,name):
    active=False
    result=[]
    for line in path.read_text().splitlines():
        label=re.match(r'^[0-9a-f]+ <([^>]+)>:$',line)
        if label:
            if active: break
            active=label.group(1)==name
        elif active:
            instruction=re.match(r'^\s*[0-9a-f]+:\s+([0-9a-f]{4}(?:[0-9a-f]{4})?)\s',line)
            if instruction: result.append(instruction.group(1))
    if not result: raise RuntimeError('Missing baseline symbol '+name)
    return result

def check(run):
    results=[]
    for base in sorted(run.glob('BaselineConfig-*.disassembly.txt')):
        native=run/base.name.replace('BaselineConfig-','FineGrainedConfig-',1)
        for name in ('dot_baseline','dp_baseline'):
            a=words(base,name); b=words(native,name)
            if a!=b: raise RuntimeError('Baseline machine code differs: '+base.name+'/'+name)
            results.append({'case':base.name,'function':name,'instructions':len(a),
                            'instruction_words_sha256':hashlib.sha256(' '.join(a).encode()).hexdigest()})
    if not results: raise RuntimeError('No baseline disassembly')
    (run/'baseline-code-equality.json').write_text(json.dumps({'status':'PASS','comparisons':results},indent=2))
    return results

if __name__=='__main__':
    comparisons=check(Path(sys.argv[1]))
    print(f'PASS: {len(comparisons)} baseline function comparisons; executable words identical across configurations.')
