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

roots = [('fork-master', 'fork @ master f069898'), ('fork-repair', 'fork @ repair 2d4b135'), ('truepad', 'TruePad @ HEAD')]
SP = os.environ['SP']
all_f = []
for d, label in roots:
    base = f'{SP}/sweep/{d}'
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
