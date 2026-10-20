#!/bin/bash
#
# Self-test for the audit's own oracles (A07, A08).
#
# WHY. An outside audit pointed these two tools at malformed and unrelated
# input and got exit 0 and a printed figure from both. They are the tools that
# produced figures the project CITES, so "the comparison exited zero having
# compared nothing" matters more here than in the thing being audited.
#
# Every case below is a NEGATIVE control with its own distinct expected reason,
# because four refusals for one shared accidental reason would look exactly
# like four working guards. That happened while writing this: the first
# versions of the A08 fixtures used the wrong case-label key, so all four
# refused on "no test case labelled Overall" and none of the four defects was
# actually exercised. The fixtures are therefore built FROM A GENUINE REPORT.
#
#   oracle-selftest.sh [path-to-a-genuine-ea_non_iid-report]
#
# With no argument it builds one, which needs the tools and about a minute.

set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/oracle-selftest.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM
fails=0
chk() { # chk <label> <expected-exit> <expected-text-fragment> <cmd...>
    local label=$1 want=$2 frag=$3; shift 3
    local out rc
    out=$("$@" 2>&1); rc=$?
    if [ "${rc}" != "${want}" ]; then
        printf '  %-44s FAIL  exit %s, wanted %s\n' "${label}" "${rc}" "${want}"
        fails=$((fails + 1)); return
    fi
    if [ -n "${frag}" ] && ! printf '%s' "${out}" | grep -qF "${frag}"; then
        printf '  %-44s FAIL  exit %s but not for the stated reason\n' "${label}" "${rc}"
        printf '        wanted a mention of: %s\n' "${frag}"
        fails=$((fails + 1)); return
    fi
    printf '  %-44s PASS  (exit %s)\n' "${label}" "${rc}"
}

# ---------------------------------------------------------------- fixtures
report=${1:-}
if [ -z "${report}" ]; then
    cat > "${work}/gen.c" <<'GENEOF'
#include <stdio.h>
int main(void){ unsigned long long x=0x90B2026ULL;
  for(long i=0;i<1000000;i++){ x+=0x9E3779B97F4A7C15ULL; unsigned long long z=x;
    z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL;
    putchar((int)((z^(z>>31))&1ULL)); } return 0; }
GENEOF
    cc -O1 -o "${work}/gen" "${work}/gen.c" 2>/dev/null || { echo "no C compiler" >&2; exit 2; }
    "${work}/gen" > "${work}/bits.bin"
    OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} "${repo}/cpp/ea_non_iid" -i -a -q \
        -o "${work}/rep.json" "${work}/bits.bin" 1 >/dev/null 2>&1
    "${repo}/cpp/ea_restart" -i -q -o "${work}/restart.json" "${work}/bits.bin" 1 0.696/bit >/dev/null 2>&1
    report="${work}/rep.json"
    restart="${work}/restart.json"
else
    restart=""
fi
[ -s "${report}" ] || { echo "oracle-selftest: no genuine report to mutate" >&2; exit 2; }

python3 - "${report}" "${work}" <<'PYEOF'
import json, sys, os
src, W = sys.argv[1], sys.argv[2]
base = json.load(open(src))
def w(name, mut):
    d = json.loads(json.dumps(base)); mut(d)
    open(os.path.join(W, name), 'w').write(json.dumps(d, indent=1))
w('no_errorlevel.json', lambda d: d.pop('errorLevel'))
def short(d):
    for c in d['testCases']: c['nonCompliantShortDataset'] = True
w('short.json', short)
def ten(d):
    for c in d['testCases']:
        if (c.get('testCaseDesc') or '') == 'Overall':
            c['hAssessed'] = 10.0; c['hOriginal'] = 10.0
w('entropy10.json', ten)
s = json.dumps(base, indent=1)
i = s.rindex('"hAssessed"'); j = s.index(',', i)
open(os.path.join(W, 'nonfinite.json'), 'w').write(s[:i] + '"hAssessed": NaN' + s[j:])
open(os.path.join(W, 'unrelated.json'), 'w').write('{"hello":"world"}')
open(os.path.join(W, 'notjson.txt'), 'w').write('this is not json at all\n')
PYEOF

echo "entropy_floor.py -- validate the evidence before emitting anything (A08)"
F="python3 ${here}/entropy_floor.py"
chk "a genuine report still produces a FLOOR"     0 "FLOOR"                        $F "${report}"
chk "errorLevel absent is NOT 'errorLevel is 0'"  1 "has no 'errorLevel'"          $F "${work}/no_errorlevel.json"
chk "nonCompliantShortDataset refused"            1 "nonCompliantShortDataset"     $F "${work}/short.json"
chk "10 bits from a 1-bit symbol refused"         1 "exceeds the 1-bit ceiling"    $F "${work}/entropy10.json"
chk "a nonfinite JSON token refused"              1 "NaN and Infinity"             $F "${work}/nonfinite.json"
chk "an unrelated JSON document refused"          1 ""                             $F "${work}/unrelated.json"

echo
echo "restart_decision_exact.py -- 0 agrees, 1 disagrees, 2 cannot decide (A07)"
D="python3 ${here}/restart_decision_exact.py"
if [ -n "${restart}" ] && [ -s "${restart}" ]; then
    chk "a genuine restart report DECIDES and agrees"  0 "DECISION:"               $D "${restart}"
    python3 - "${restart}" "${work}/disagree.json" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
d['restartXcutoff'] = 400; d['passedRestartSanityCheck'] = False
open(sys.argv[2], 'w').write(json.dumps(d))
PYEOF
    chk "a wrong tool cutoff exits 1, not 0"          1 "DISAGREE"                 $D "${work}/disagree.json"
fi
chk "an unrelated JSON document cannot decide"       2 "CANNOT DECIDE"             $D "${work}/unrelated.json"
chk "a non-JSON file cannot decide"                  2 "CANNOT DECIDE"             $D "${work}/notjson.txt"
chk "a path that does not exist cannot decide"        2 "CANNOT DECIDE"             $D "${work}/absent.json"
chk "no arguments at all cannot decide"              2 ""                          $D

if [ "${fails}" -eq 0 ]; then echo; echo "oracle-selftest: PASS"; exit 0; fi
echo; echo "oracle-selftest: FAIL (${fails} case(s))"; exit 1
