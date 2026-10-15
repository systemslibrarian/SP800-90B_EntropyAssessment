#!/usr/bin/env python3
"""Vacuous-success detector, v2.

A guard loop is vacuous-safe only if the emptiness or size of THE THING BEING
ITERATED is asserted. Testing the failure accumulator afterwards does not count:
an empty input set leaves the accumulator empty too, which reads as success.
"""
import os, re, json
SP = os.environ['SP']
out = []
FAILWORD = re.compile(r'fails=\$\(\(|FAIL=\$\(\(|\bbad\s|\bfail\s|exit 1|missing=\"?\$\{?missing', re.I)

for d, label in [('fork-master','fork @ master f069898'), ('fork-repair','fork @ repair 2d4b135'), ('truepad','TruePad @ HEAD')]:
    base = f'{SP}/sweep/{d}'
    for dirpath, _, files in os.walk(base):
        for fn in sorted(files):
            if not fn.endswith('.sh'): continue
            p = os.path.join(dirpath, fn); rel = os.path.relpath(p, base)
            src = open(p, encoding='utf-8', errors='replace').read()
            lines = src.split('\n')
            for i, l in enumerate(lines):
                m = re.match(r'^\s*for\s+(\w+)\s+in\s+(.+?)\s*;?\s*do\s*$', l) or \
                    re.match(r'^\s*for\s+(\w+)\s+in\s+(.+)$', l)
                if not m: continue
                var, src_expr = m.group(1), m.group(2)
                # only extraction-driven loops: command substitution, or a variable
                drives = re.findall(r'\$\{?(\w+)\}?', src_expr)
                is_cmdsub = '$(' in src_expr or '`' in src_expr
                if not is_cmdsub and not drives: continue
                j = i + 1; depth = 1
                while j < len(lines) and depth:
                    if re.match(r'^\s*(for|while|until)\b', lines[j]): depth += 1
                    if re.match(r'^\s*done\b', lines[j]): depth -= 1
                    j += 1
                body = '\n'.join(lines[i+1:j])
                if not FAILWORD.search(body): continue
                # is the SIZE/emptiness of the driving set asserted anywhere in the script?
                names = set(drives)
                guarded = False
                for n in names:
                    if re.search(r'\[\s*-z\s+"?\$\{?%s\}?"?\s*\]' % n, src) and 'exit' in src: guarded = True
                    if re.search(r'\$\{#%s' % n, src): guarded = True
                    if re.search(r'%s_count|count.*%s' % (n, n), src, re.I): guarded = True
                if is_cmdsub and not names: guarded = False
                if guarded: continue
                out.append(dict(repo=label, file=rel, line=i+1, var=var,
                                driver=src_expr[:80], snippet=l.strip()[:110]))
json.dump(out, open(SP+'/vacuous2.json','w'), indent=1)
print('vacuous-success candidates:', len(out))
for f in out: print(f"  {f['repo']:24s} {f['file']}:{f['line']}  (loop var ${f['var']})\n      {f['snippet']}")
