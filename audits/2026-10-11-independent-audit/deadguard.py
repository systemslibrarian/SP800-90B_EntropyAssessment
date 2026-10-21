#!/usr/bin/env python3
"""Flag shell scripts that can exit 0 on a path where a verification step did not pass.

Patterns:
  A  no `set -e`/errexit, and the script's last meaningful command is an
     unconditional success message -> exit status is the echo's, not the test's
  B  interpreter heredoc (python/perl/node/ruby) in statement position with its
     exit status never read -> asserts inside it cannot fail the script
  C  status-bearing verification command in statement position, status unread
  D  pipeline whose meaningful command is upstream of a pipe, without pipefail
"""
import os, re, sys, json

INTERP = re.compile(r'^\s*(python3?|perl|node|ruby|jq)\b')
HEREDOC_START = re.compile(r"<<-?\s*'?([A-Za-z_][A-Za-z0-9_]*)'?\s*$")
VERIFY_CMD = re.compile(r'^\s*(python3?|perl|node|ruby|jq|grep|egrep|cmp|diff|test|\[|shasum|sha256sum|assert)\b')
SUCCESS_ECHO = re.compile(r'^\s*(echo|printf)\b.*\b(PASS|OK\b|SUCCESS|passed|All checks)', re.I)
CONTROL = re.compile(r'^\s*(if|elif|else|fi|while|until|for|done|case|esac|then|\}|\{|#|$)')
ASSIGN = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_]*=')
STATUSREAD = re.compile(r'\$\?')
CONDITIONAL = re.compile(r'(\|\||&&|;\s*then|^\s*if\b|^\s*!\s|\bexit\b)')

def analyse(path, rel, repo):
    try: src = open(path, encoding='utf-8', errors='replace').read()
    except Exception: return []
    lines = src.split('\n')
    has_e = bool(re.search(r'^\s*set\s+-[a-z]*e|set\s+-o\s+errexit', src, re.M))
    has_pipefail = 'pipefail' in src
    out = []

    # map heredoc bodies so we don't analyse their contents as shell
    inheredoc = None
    heredoc_cmd_line = {}   # line index of heredoc-opening command -> terminator line
    shell_lines = []
    i = 0
    while i < len(lines):
        l = lines[i]
        if inheredoc is None:
            m = HEREDOC_START.search(l)
            if m:
                term = m.group(1); start = i
                j = i + 1
                while j < len(lines) and lines[j].strip() != term:
                    j += 1
                heredoc_cmd_line[start] = j
                shell_lines.append((i, l))
                i = j + 1
                continue
            shell_lines.append((i, l))
        i += 1

    def next_shell_line(after):
        for idx, l in shell_lines:
            if idx > after and l.strip() and not l.strip().startswith('#'):
                return idx, l
        return None, None

    # B: interpreter heredoc in statement position, status unread
    for start, term in heredoc_cmd_line.items():
        cmd = lines[start]
        if not INTERP.match(cmd): continue
        if CONDITIONAL.search(cmd): continue
        if ASSIGN.match(cmd): continue
        nidx, nline = next_shell_line(term)
        checked = bool(nline and (STATUSREAD.search(nline) or re.match(r'^\s*(rc|status|ret)=\$\?', nline)))
        body = '\n'.join(lines[start+1:term])
        has_assert = bool(re.search(r'\bassert\b|\braise\b|sys\.exit|\bdie\b', body))
        if not checked:
            out.append(dict(repo=repo, file=rel, line=start+1, pattern='B',
                            has_set_e=has_e, verifies=has_assert,
                            snippet=cmd.strip()[:100],
                            detail=('heredoc carries assertions; ' if has_assert else '')
                                   + ('no set -e, status never read' if not has_e else 'set -e present')))
    # A: unconditional terminal success message without set -e
    last_meaningful = None
    for idx, l in shell_lines:
        if l.strip() and not l.strip().startswith('#'): last_meaningful = (idx, l)
    if last_meaningful and SUCCESS_ECHO.match(last_meaningful[1]) and not has_e:
        out.append(dict(repo=repo, file=rel, line=last_meaningful[0]+1, pattern='A',
                        has_set_e=False, verifies=False,
                        snippet=last_meaningful[1].strip()[:100],
                        detail='script ends with an unconditional success message and has no set -e: '
                               'exit status is the message, not the verification'))
    # C / D: statement-position verification commands with unread status
    for idx, l in shell_lines:
        if idx in heredoc_cmd_line: continue
        s = l.strip()
        if not s or s.startswith('#') or CONTROL.match(l): continue
        if ASSIGN.match(l): continue
        if not VERIFY_CMD.match(l): continue
        if CONDITIONAL.search(l): continue
        nidx, nline = next_shell_line(idx)
        if nline and STATUSREAD.search(nline): continue
        if '|' in s and not has_pipefail:
            out.append(dict(repo=repo, file=rel, line=idx+1, pattern='D', has_set_e=has_e, verifies=True,
                            snippet=s[:100],
                            detail='verification command upstream of a pipe, no pipefail'
                                   + ('' if has_e else ', no set -e')))
        elif not has_e:
            out.append(dict(repo=repo, file=rel, line=idx+1, pattern='C', has_set_e=False, verifies=True,
                            snippet=s[:100], detail='verification command in statement position, status never read, no set -e'))
    return out


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

roots = [('fork-master', 'fork'), ('fork-repair', 'fork-repair'), ('truepad', 'TruePad')]
SP = os.environ['SP']
all_f = []
for d, name in roots:
    base = f'{SP}/sweep/{d}'
    label = tree_label(base, name)
    print('provenance:', label)
    for dirpath, _, files in os.walk(base):
        for fn in sorted(files):
            if not fn.endswith('.sh'): continue
            p = os.path.join(dirpath, fn)
            all_f += analyse(p, os.path.relpath(p, base), label)
json.dump(all_f, open(SP + '/deadguard.json', 'w'), indent=1)
import collections
print('flags:', len(all_f))
print('by pattern:', dict(collections.Counter(f['pattern'] for f in all_f)))
print('by repo:', dict(collections.Counter(f['repo'] for f in all_f)))
print('files touched:', len({(f['repo'], f['file']) for f in all_f}))
