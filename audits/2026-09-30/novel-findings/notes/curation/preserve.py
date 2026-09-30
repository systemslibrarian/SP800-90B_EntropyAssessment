#!/usr/bin/env python3
"""Build NOVEL-FINDINGS-PRESERVATION/ (outside Git state). Reads git objects only; never writes Git."""
import os, re, sys, hashlib, subprocess, shutil, datetime

REPO = '/workspaces/SP800-90B_EntropyAssessment'
DEST = os.path.join(REPO, 'NOVEL-FINDINGS-PRESERVATION')
SCR = '/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad'
UPSTREAM_TREE = '/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/bae8c694-6a48-4fd3-83f6-685460129aee/scratchpad/up'
BASELINE = '87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289'
REPORT = 'audits/2026-09-30-novel-findings-audit.md'
MAXTEXT = 2_000_000

SKIP_DIRS = {'venv', '.venv', 'pylib', 'site-packages', '__pycache__', '.git', 'node_modules', 'site'}
SKIP_TOP = {'audit/rel', 'audit/asan'}  # build trees (binaries)
SKIP_EXT = {'.bin', '.col', '.so', '.a', '.o', '.exe', '.whl', '.pem', '.pyc', '.pyi', '.npy', '.npz', '.pkl',
            '.fits', '.gz', '.pdf', '.copy', '.typed', '.f', '.f90', '.f95', '.pyf', '.pxd', '.pyx', '.APACHE',
            '.BSD', '.dat', '.raw', '.zip', '.tar'}
KEEP_BINARY = {'audit/verify/f09b.bin'}  # generator not preserved per the report; small (114 KB)
SECRET_RE = re.compile(rb'(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|'
                       rb'Authorization:\s*(token|Bearer)\s+\S+|(GH|GITHUB)_TOKEN\s*=\s*\S+)')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], check=True, capture_output=True).stdout


upstream_hashes = set()
for dp, dn, fn in os.walk(UPSTREAM_TREE):
    for f in fn:
        upstream_hashes.add(sha(os.path.join(dp, f)))

os.makedirs(DEST, exist_ok=False)
copied, skipped = [], {}
def skip(reason, rel):
    skipped.setdefault(reason, []).append(rel)

# 1. Branch deliverables straight from the committed objects at HEAD
head = git('rev-parse', 'HEAD').decode().strip()
branch = git('rev-parse', '--abbrev-ref', 'HEAD').decode().strip()
for src, dst in [(REPORT, 'report/2026-09-30-novel-findings-audit.md'),
                 ('full_source.txt', 'branch-files/full_source.txt'),
                 ('NIST.SP.800-90B.pdf', 'branch-files/NIST.SP.800-90B.pdf')]:
    data = git('show', f'{head}:{src}')
    out = os.path.join(DEST, dst)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'wb').write(data)
    copied.append(dst)

# 2. Filtered copy of the audit workspace
token = os.environ.get('GITHUB_TOKEN', '').encode() or None
for top in ['audit', 'n02-fresh']:
    root = os.path.join(SCR, top)
    for dp, dn, fn in os.walk(root):
        reldir = os.path.relpath(dp, SCR)
        if any(reldir == t or reldir.startswith(t + '/') for t in SKIP_TOP):
            for f in fn: skip('build tree (binaries)', os.path.join(reldir, f))
            dn[:] = []
            continue
        keep = []
        for d in dn:
            if d in SKIP_DIRS or d.endswith('.dist-info') or d.endswith('.egg-info'):
                skip('dependency/cache directory', os.path.join(reldir, d) + '/')
            else:
                keep.append(d)
        dn[:] = keep
        for f in fn:
            rel = os.path.join(reldir, f)
            p = os.path.join(dp, f)
            try:
                size = os.path.getsize(p)
                with open(p, 'rb') as fh:
                    head8k = fh.read(8192)
            except OSError:
                skip('unreadable (permission 000 test fixture)', rel); continue
            if rel in KEEP_BINARY:
                pass
            elif head8k[:4] == b'\x7fELF':
                skip('ELF binary', rel); continue
            elif os.path.splitext(f)[1] in SKIP_EXT:
                skip('generated input / binary data / dependency artefact', rel); continue
            elif b'\x00' in head8k:
                skip('binary content', rel); continue
            elif size > MAXTEXT:
                skip('text file > 2 MB', rel); continue
            elif os.path.splitext(f)[1] in {'.h', '.cpp', '.c', '.pl', ''} and sha(p) in upstream_hashes:
                skip('verbatim upstream 87c104d source copy', rel); continue
            blob = open(p, 'rb').read()
            if SECRET_RE.search(blob) or (token and token in blob):
                skip('POSSIBLE CREDENTIAL - excluded', rel); continue
            out = os.path.join(DEST, 'workspace', rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(p, out)
            copied.append(os.path.join('workspace', rel))

# 3. Final credential sweep over everything copied (including branch files)
for rel in copied:
    blob = open(os.path.join(DEST, rel), 'rb').read()
    if SECRET_RE.search(blob) or (token and token in blob):
        print('CREDENTIAL HIT, removing:', rel)
        os.remove(os.path.join(DEST, rel)); copied.remove(rel)

json_out = {'head': head, 'branch': branch, 'copied': copied, 'skipped': {k: len(v) for k, v in skipped.items()}}
open('/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/bae8c694-6a48-4fd3-83f6-685460129aee/scratchpad/preserve_skipped.txt', 'w', errors='backslashreplace').write(
    '\n'.join(f'{k}\t{r!r}' for k, v in skipped.items() for r in v))
open('/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/bae8c694-6a48-4fd3-83f6-685460129aee/scratchpad/preserve_copied.txt', 'w', errors='backslashreplace').write('\n'.join(repr(c) for c in copied))
print(json_out['head'], json_out['branch'], len(copied), json_out['skipped'])
