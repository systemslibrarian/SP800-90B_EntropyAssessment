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
# F08 FIXTURES (OC-83). Three defects the outside audit found in this oracle,
# each exercised by changing ONE thing and each refused for ITS OWN stated
# reason -- the expected-text fragments below are distinct on purpose, because
# four refusals for one shared accidental reason is how the first version of
# this file looked while testing nothing.
python3 - "${report}" "${work}" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1])); w = sys.argv[2]

def overall(e):
    for c in e['testCases']:
        if str(c.get('caseLabel', '')) == 'Overall':
            return c
    return e['testCases'][-1]

def put(name, mut):
    e = json.loads(json.dumps(d)); mut(e)
    json.dump(e, open("%s/%s" % (w, name), 'w'), indent=3)

# (1) the two readings of the same measurement disagree: hOriginal 0.8 against
#     hAssessed 0.1. The old oracle printed a NOTE telling the reader to stop,
#     and then printed two floor figures.
def m1(e):
    c = overall(e); c['hOriginal'] = 0.8; c['hAssessed'] = 0.1
put('f08_c02.json', m1)
# (2) a width that cannot exist. `if not w` tested truthiness only.
put('f08_width.json', lambda e: e.update(bitsPerSymbol=1.5))
# (3) 125,000 eight-bit samples: 1,000,000 BITS, one eighth of 3.1.1's sample
#     minimum, and only the bit count was ever checked.
def m3(e):
    e['bitsPerSymbol'] = 8; e['assessedSampleCount'] = 125000
    c = overall(e); c['hOriginal'] = 6.75
    if 'hAssessed' in c: c['hAssessed'] = 6.75
put('f08_samples.json', m3)
PYEOF
chk "hAssessed inconsistent with h' is REFUSED"    1 "C02 relation does not hold"   $F "${work}/f08_c02.json"
chk "a fractional symbol width is refused"        1 "integer width of 1-8"         $F "${work}/f08_width.json"
chk "a bit count is not a sample count"           1 "is not a sample count"        $F "${work}/f08_samples.json"

echo
echo "restart_decision_exact.py -- 0 agrees, 1 disagrees, 2 cannot decide (A07)"
D="python3 ${here}/restart_decision_exact.py"
if [ -n "${restart}" ] && [ -s "${restart}" ]; then
    chk "a genuine restart report DECIDES and agrees"  0 "A. INDEPENDENT DECISION"  $D "${restart}"
    # F07 FIXTURES. Each changes ONE thing, so each exercises one limb.
    #
    # The old single fixture changed the cutoff AND the verdict flag together
    # and was labelled "a wrong tool cutoff exits 1". Under the three-statement
    # structure it still exits 1 -- but because the FLAG disagrees, not because
    # the cutoff does, so the label named the wrong cause. Two fixtures now,
    # one per cause, which is the same discipline as the four A08 fixtures that
    # once all refused for one shared accidental reason.
    python3 - "${restart}" "${work}" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1])); w = sys.argv[2]

def put(name, **kw):
    e = dict(d); e.update(kw)
    for k, v in list(kw.items()):
        if v is None:
            e.pop(k, None)
    open("%s/%s" % (w, name), 'w').write(json.dumps(e))

# (1) ONLY the tool's reported verdict is flipped. Its cutoff is untouched, so
#     the recomputation the old oracle performed still says ACCEPT -- which is
#     exactly why the old oracle printed AGREE and exited 0 on this fixture.
put('verdict_flipped.json', passedRestartSanityCheck=(not d['passedRestartSanityCheck']))
# (2) ONLY the cutoff is wrong, the verdict left as the tool reported it. This
#     makes the tool's verdict not follow from its own figures.
put('cutoff_wrong.json', restartXcutoff=400)
# (3) the verdict is absent: incomplete evidence, not agreement.
put('no_verdict.json', passedRestartSanityCheck=None)
# (4) the verdict is present but not a boolean: not guessed.
put('verdict_string.json', passedRestartSanityCheck='yes')
PYEOF
    chk "agreement follows the tool's VERDICT not its cutoff" 1 "DISAGREE"        $D "${work}/verdict_flipped.json"
    chk "a verdict not implied by the tool's own figures"     1 "CONTRADICTS ITSELF" $D "${work}/cutoff_wrong.json"
    chk "no reported verdict is INCOMPLETE, not agreement"    2 "INCOMPLETE"      $D "${work}/no_verdict.json"
    chk "a non-boolean verdict is refused, not interpreted"   2 "not a boolean"   $D "${work}/verdict_string.json"
    # (5) a log stating both verdicts is not one run's verdict.
    { echo "H_I: 0.900000"; echo "X_max: 17"; echo "X_cutoff: 605";
      echo "Restart Sanity Check Passed"; echo "Restart Sanity Check Failed"; } \
      > "${work}/both_verdicts.log"
    chk "a log stating BOTH verdicts is refused"              2 "will not choose" \
        $D --from-log "${work}/both_verdicts.log"
fi
chk "an unrelated JSON document cannot decide"       2 "CANNOT DECIDE"             $D "${work}/unrelated.json"
chk "a non-JSON file cannot decide"                  2 "CANNOT DECIDE"             $D "${work}/notjson.txt"
chk "a path that does not exist cannot decide"        2 "CANNOT DECIDE"             $D "${work}/absent.json"
chk "no arguments at all cannot decide"              2 ""                          $D

if [ "${fails}" -eq 0 ]; then echo; echo "oracle-selftest: PASS"; exit 0; fi
echo; echo "oracle-selftest: FAIL (${fails} case(s))"; exit 1
