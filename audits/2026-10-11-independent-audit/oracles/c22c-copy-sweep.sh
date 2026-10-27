#!/bin/bash
#
# ONE SOURCE FOR EACH C22c FAMILY VALUE -- enforced, with a positive control.
#
# WHY (OC-125). The two-copies defect was found because someone asked where a
# number came from. The sweep exists because a THIRD copy nobody has found is
# exactly the shape of that finding: before this fix the six family ceilings
# were recorded in seven places at three precisions, and the pair that mattered
# -- the copy that was subtracted and the copy a derivation verified -- was only
# two of the seven.
#
#   entropy_floor.py              C22C_FAMILIES_BY_N   all 6    SUBTRACTED
#   compression_ceiling_exact.py  SCAN                 comp x2  compared
#   compression_ceiling_exact.py  TABULATED            comp x2  compared
#   zalpha_ceiling_by_n.py        REC_COLL             coll x2  compared
#   zalpha_ceiling_by_n.py        REC_COMP             comp x2  printed
#   regression-constants.sh                            all 6    pinned
#   band1-pair-mutations.sh                            3        mutated
#
# All seven are gone. The values live in c22c_source.json; every consumer reads
# it; the fast suite pins a DIGEST rather than a second copy; and the mutation
# battery asks the source for the string it replaces instead of naming it.
#
# SCOPE, DECLARED. Two different rules, because they answer two questions.
#
#   COLLAPSED -- the six family ceilings (3 families x 2 bitstring lengths) and
#     the record's three-figure publications of those same six. Exactly one
#     recording of each is permitted, in c22c_source.json. Everything else must
#     read it.
#
#   CROSS-CHECKED, NOT COLLAPSED -- the derivations' INPUTS: z_tool, z_spec, d
#     and b. Each derivation states these independently on purpose, so that a
#     disagreement between two independent statements surfaces as a
#     disagreement between two derivations, which is the behaviour wanted. What
#     is enforced is that the statements are IDENTICAL STRINGS.
#
#   OUT OF SCOPE -- prose. A .md document cannot be a consumer, and the audit
#     record is full of tables quoting these values as they stood at the time;
#     rewriting history to satisfy a sweep would be the wrong direction. The
#     sweep reads executable and data files only.
#
# HOW A COPY IS RECOGNISED. In Python, every ast.Constant that is not a
# docstring -- a number, or a string whose ENTIRE text is a number, because the
# copy this fix removed was `SCAN = {10 ** 6: "3.3599e-3", ...}` and a
# string-literal copy is still a copy. Prose that happens to quote a value
# inside a longer string is not a recording and is not reported; the whole
# string has to parse as a decimal. In shell, YAML and JSON, every numeric
# token on a line that is not a comment. A value matches if it agrees with a
# family ceiling to 3 significant figures (relative 5e-4, which is the most a
# 3-figure rounding can differ by), so a recording at ANY precision is caught,
# including ones nobody thought to write a pattern for.
#
# IT CAUGHT ITS AUTHOR ON ITS FIRST RUN. c22c_derive.py was written carrying
# the record's five published three-figure values as constants, to seed the
# source with -- and the sweep reported all five. They are read forward out of
# the existing source now, and a generator that cannot invent a published
# figure is a better generator. That is the control that matters: the sweep
# found a copy nobody had thought of, which is the thing it exists for.
#
# THE POSITIVE CONTROL TESTS THE DISCRIMINATION, NOT THE LIVENESS. "The sweep
# found something" is a weak control; what can actually be wrong here is the
# comment-and-docstring rule, because that is the rule that decides what is
# invisible. So the control builds a file in a temporary directory containing
# the SAME family value three times -- once as a live constant, once in a `#`
# comment, once in a docstring -- and requires the sweep to report exactly the
# first. A sweep that reported none of the three would pass a liveness control
# that only asked whether it found the copy it was given.
#
# Usage: c22c-copy-sweep.sh            sweep the repository, then the control
#        c22c-copy-sweep.sh --no-control   sweep only (for a caller that has
#                                          already run the control)
set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../../.." && pwd)
control=1
for a in "$@"; do
    case "$a" in
        --no-control) control=0 ;;
        *) echo "c22c-copy-sweep: unknown option $a" >&2; exit 2 ;;
    esac
done

scan() { # scan <allow-the-one-source: 1|0> <root>...
    python3 - "$@" <<'PYEOF'
import ast, json, os, re, sys
from decimal import Decimal, InvalidOperation

allow_source = sys.argv[1] == '1'
roots = sys.argv[2:]
here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else None

SOURCE_NAME = 'c22c_source.json'
CODE_EXT = ('.py', '.sh', '.yml', '.yaml', '.json', '.c', '.cpp', '.h', '.pl')
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.github-cache'}
REL = Decimal('5e-4')          # the most a 3-significant-figure rounding differs
NUM = re.compile(r'(?<![0-9A-Za-z_.])([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)')

# The targets come FROM the one source, so this file carries no copy either.
src_path = None
for root in roots:
    cand = os.path.join(root, SOURCE_NAME)
    if os.path.exists(cand):
        src_path = cand
        break
if src_path is None:
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if SOURCE_NAME in filenames:
                src_path = os.path.join(dirpath, SOURCE_NAME)
                break
        if src_path:
            break
if src_path is None:
    print("c22c-copy-sweep: the one source %s is not in %s. There is nothing "
          "to enforce one-ness against; refusing." % (SOURCE_NAME, roots))
    raise SystemExit(2)

doc = json.load(open(src_path))
targets = []        # (label, Decimal)
for row in doc['rows']:
    for fam in ('compression', 'collision'):
        targets.append(('%s n=%d' % (fam, row['n']), Decimal(row[fam]['value'])))
        targets.append(('%s n=%d record' % (fam, row['n']),
                        Decimal(row[fam]['record_3fig'])))
targets.append(('proportion record',
                Decimal(doc['families']['proportion']['record_3fig'])))
z_inputs = {k: doc['inputs'][k] for k in ('z_tool', 'z_spec')}

def matches(text):
    try:
        v = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    # Decimal accepts 'nan', 'snan' and 'Infinity', and comparing one of those
    # raises rather than returning False -- which is how the first run of this
    # sweep died, on a string constant somewhere in the tree. A non-finite
    # token is not a recording of a ceiling.
    if not v.is_finite() or v == 0:
        return None
    for label, t in targets:
        if abs(v - t) <= REL * t:
            return label
    return None

findings = []     # (path, line, label, text, how)

def py_constants(path, text):
    """Every non-docstring constant, with its line. Comments are invisible."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        print("c22c-copy-sweep: %s does not parse (%s); a file that cannot be "
              "read cannot be cleared." % (path, exc))
        raise SystemExit(2)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, 'body', None)
            if body and isinstance(body[0], ast.Expr) and \
               isinstance(body[0].value, ast.Constant) and \
               isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and id(node) not in docstrings:
            if isinstance(node.value, bool):
                continue
            if isinstance(node.value, (int, float)):
                yield node.lineno, repr(node.value)
            elif isinstance(node.value, str):
                yield node.lineno, node.value

def line_tokens(text):
    for i, line in enumerate(text.splitlines(), 1):
        s = line.lstrip()
        if s.startswith('#') or s.startswith('//'):
            continue
        body = line.split('#', 1)[0] if not s.startswith('"') else line
        for m in NUM.finditer(body):
            yield i, m.group(1)

for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if not fn.endswith(CODE_EXT):
                continue
            path = os.path.join(dirpath, fn)
            if allow_source and os.path.abspath(path) == os.path.abspath(src_path):
                continue
            try:
                text = open(path, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            gen = py_constants(path, text) if fn.endswith('.py') else line_tokens(text)
            how = 'live constant' if fn.endswith('.py') else 'non-comment token'
            for lineno, tok in gen:
                label = matches(tok)
                if label:
                    findings.append((os.path.relpath(path, roots[0]), lineno,
                                     label, tok, how))

# The inputs are cross-checked for string identity rather than collapsed.
zbad = []
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if not fn.endswith('.py'):
                continue
            path = os.path.join(dirpath, fn)
            text = open(path, encoding='utf-8', errors='replace').read()
            for name, want in z_inputs.items():
                var = 'Z_TOOL' if name == 'z_tool' else 'Z_SPEC'
                for m in re.finditer(re.escape(var) + r'\s*=\s*mpf\("([^"]+)"\)', text):
                    if m.group(1) != want:
                        zbad.append((os.path.relpath(path, roots[0]), var,
                                     m.group(1), want))

out = {'findings': findings, 'zbad': zbad, 'source': os.path.relpath(src_path, roots[0]),
       'targets': len(targets)}
print(json.dumps(out))
PYEOF
    rc=$?
    # THE STATUS IS READ HERE, EXPLICITLY, AND NOT ONLY BY THE CALLER.
    # regression-deadguard.sh's pattern B reads the line after a heredoc
    # terminator; the caller's `res=$(scan ...) || exit 2` is too far away for
    # it to see, so the function returns the status by name. A baseline
    # carrying a false positive is worse than one carrying none.
    return ${rc}
}

fails=0
echo "c22c one-source sweep"
echo

res=$(scan 1 "${repo}") || { echo "c22c-copy-sweep: the sweep could not run"; exit 2; }
n_find=$(printf '%s' "${res}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["findings"]))')
n_targ=$(printf '%s' "${res}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["targets"])')
n_zbad=$(printf '%s' "${res}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["zbad"]))')
printf '  %-54s %s\n' "family values enforced to one source" "${n_targ} target(s)"
if [ "${n_find}" -eq 0 ]; then
    printf '  %-54s PASS  no second copy in any executable or data file\n' "second copies"
else
    printf '  %-54s FAIL  %s\n' "second copies" "${n_find} found"
    printf '%s' "${res}" | python3 -c '
import json, sys
for p, line, label, tok, how in json.load(sys.stdin)["findings"]:
    print("        %s:%s  %s as a %s  -> %s" % (p, line, tok, how, label))'
    fails=$((fails + 1))
fi
if [ "${n_zbad}" -eq 0 ]; then
    printf '  %-54s PASS  identical strings everywhere\n' "inputs cross-checked (not collapsed)"
else
    printf '  %-54s FAIL  %s disagreement(s)\n' "inputs cross-checked" "${n_zbad}"
    printf '%s' "${res}" | python3 -c '
import json, sys
for p, var, got, want in json.load(sys.stdin)["zbad"]:
    print("        %s  %s = %s, the source says %s" % (p, var, got, want))'
    fails=$((fails + 1))
fi

# ----------------------------------------------------------------- the control
if [ "${control}" -eq 1 ]; then
    echo
    echo "positive control -- the same value three ways, in a temporary tree"
    cdir=$(mktemp -d "${TMPDIR:-/tmp}/c22c-sweep-control.XXXXXX") || exit 2
    trap 'rm -rf "${cdir}" "${cdir}.scan"' EXIT HUP INT TERM
    cp "${here}/c22c_source.json" "${cdir}/" || { echo "  no source to copy"; exit 2; }
    val=$(python3 "${here}/c22c_source.py" --value compression 1000000) || exit 2
    cat > "${cdir}/control.py" <<EOF
"""A docstring that names ${val} and must stay invisible."""
# A comment that names ${val} and must stay invisible.
LIVE = ${val}
EOF
    cres=$(scan 1 "${cdir}") || { echo "  the control sweep could not run"; exit 2; }
    # THE RESULT GOES TO A FILE, NOT A PIPE. `printf ... | python3 - <<EOF`
    # reads the PROGRAM from the heredoc, so the pipe is never read and
    # json.load(sys.stdin) sees end-of-file -- which is how the first run of
    # this control died, with a JSONDecodeError that looked like a malformed
    # scan rather than a plumbing mistake. The path is an argument.
    printf '%s' "${cres}" > "${cdir}.scan"
    python3 - "${val}" "${cdir}.scan" <<'PYEOF'
import json, sys
val = sys.argv[1]
d = json.load(open(sys.argv[2]))
f = [x for x in d['findings'] if x[0] == 'control.py']
lines = sorted(x[1] for x in f)
ok_live   = lines == [3]
ok_doc    = 1 not in lines
ok_cmt    = 2 not in lines
def say(label, ok):
    print('  %-54s %s' % (label, 'PASS' if ok else 'FAIL'))
say('the live constant on line 3 is REPORTED', ok_live)
say('the docstring on line 1 is not', ok_doc)
say('the # comment on line 2 is not', ok_cmt)
if not ok_live:
    print('        reported lines: %s -- the sweep cannot see a copy it was'
          % lines)
    print('        handed, so the clean result above supports nothing')
raise SystemExit(0 if (ok_live and ok_doc and ok_cmt) else 1)
PYEOF
    rc=$?
    if [ "${rc}" -ne 0 ]; then fails=$((fails + 1)); fi
fi

echo
if [ "${fails}" -eq 0 ]; then
    echo "c22c-copy-sweep: PASS"
    exit 0
fi
echo "c22c-copy-sweep: FAIL (${fails})"
exit 1
