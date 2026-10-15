#!/usr/bin/env python3
"""Find `|| fallback` on a command that can BOTH print to stdout and exit nonzero.

The hazard is specific: inside a command substitution, if the command prints
output and then exits nonzero, the `||` fallback ALSO runs and appends its own
output. The captured value is then the concatenation of both, which typically
breaks the test that consumes it -- and breaks it in the direction of success.

`grep -c` is the canonical case: on an empty file it prints "0" and exits 1.
Others that print-then-fail: diff, cmp, comm, find (prints hits, exits 1 on a
traversal error), timeout (passes output through, exits 124), make, jq, and any
`python3 -c` that prints before raising.
"""
import os, re, json, sys

# commands that can print on stdout and still exit nonzero
PRINTS_AND_FAILS = r'(grep\s+-[a-zA-Z]*c|grep\s+-c|diff|cmp|comm|find|timeout|make|jq|python3?\s+-c|perl\s+-[a-zA-Z]*e|node\s+-[ep])'
# a fallback that itself writes to stdout
PRINTING_FALLBACK = r'(echo|printf|cat|true\s*&&\s*echo)'

CMDSUB = re.compile(r'\$\(([^()]*\|\|[^()]*)\)')
PLAIN  = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*=)?\$?\(?.*\|\|.*$')

def scan(path, rel, repo, out):
    try: lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    except Exception: return
    for i, l in enumerate(lines):
        if '||' not in l: continue
        for m in CMDSUB.finditer(l):
            inner = m.group(1)
            left, _, right = inner.partition('||')
            if re.search(PRINTS_AND_FAILS, left) and re.search(PRINTING_FALLBACK, right):
                out.append(dict(repo=repo, file=rel, line=i+1, klass='A-value-corruption',
                                snippet=l.strip()[:150]))
            elif re.search(PRINTS_AND_FAILS, left) and re.search(r'\b(true|:)\s*$', right.strip()):
                out.append(dict(repo=repo, file=rel, line=i+1, klass='B-status-masked',
                                snippet=l.strip()[:150]))
        # assignment form outside $(): X=$(cmd) || X=default  -- the SAFE idiom
        if re.search(r'=\$\([^)]*\)\s*\|\|\s*[A-Za-z_]', l):
            out.append(dict(repo=repo, file=rel, line=i+1, klass='C-safe-idiom',
                            snippet=l.strip()[:150]))

out = []
SP = os.environ['SP']
for d, label in [('fork-master','fork @ master'), ('fork-repair','fork @ repair 2d4b135'), ('truepad','TruePad @ HEAD')]:
    base = f'{SP}/sweep/{d}'
    for dirpath, _, files in os.walk(base):
        for fn in sorted(files):
            if fn.endswith(('.sh','.bash','.yml','.yaml')):
                p = os.path.join(dirpath, fn)
                scan(p, os.path.relpath(p, base), label, out)
json.dump(out, open(SP+'/orfallback.json','w'), indent=1)
import collections
print('flags:', len(out), dict(collections.Counter(f['klass'] for f in out)))
for k in ['A-value-corruption','B-status-masked','C-safe-idiom']:
    rows=[f for f in out if f['klass']==k]
    if not rows: continue
    print(f'\n===== {k} ({len(rows)}) =====')
    for f in rows: print(f"  {f['repo']:22s} {f['file']}:{f['line']}\n      {f['snippet']}")
