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


def tree_label(base, name):
    """DERIVE the provenance label from the tree under test (OC-72).

    Both detectors hardcoded 'fork @ master f069898' as the label for whatever
    was placed under them, and HEAD is now 108 commits past that commit. A
    measurement asserting an artefact identity it never established is the
    class these detectors were WRITTEN to find, so they carried it themselves.

    If the directory is a git work tree, report its actual branch and short
    SHA, and say when it is dirty -- a dirty tree is not the commit it names.
    If it is not a git tree (the sweep copies files into a scratch dir), say
    UNESTABLISHED with the digest of what was actually read, rather than
    inventing a commit.
    """
    import subprocess, hashlib, os as _os
    def _git(*a):
        try:
            r = subprocess.run(('git', '-C', base) + a, capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None
    sha = _git('rev-parse', '--short', 'HEAD')
    if sha:
        br = _git('rev-parse', '--abbrev-ref', 'HEAD') or '?'
        dirty = _git('status', '--porcelain')
        return '%s @ %s %s%s' % (name, br, sha, ' (DIRTY)' if dirty else '')
    # not a git tree: identify by content, and say the commit is unestablished
    h = hashlib.sha256()
    for dp, _, fs in _os.walk(base):
        for fn in sorted(fs):
            fp = _os.path.join(dp, fn)
            h.update(_os.path.relpath(fp, base).encode())
            try:
                with open(fp, 'rb') as fh:
                    h.update(fh.read())
            except OSError:
                pass
    return '%s @ COMMIT-UNESTABLISHED (tree sha256 %s)' % (name, h.hexdigest()[:16])

for d, name in [('fork-master','fork'), ('fork-repair','fork-repair'), ('truepad','TruePad')]:
    base = f'{SP}/sweep/{d}'
    label = tree_label(base, name)
    print('provenance:', label)
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
