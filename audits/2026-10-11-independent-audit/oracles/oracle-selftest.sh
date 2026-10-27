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
# OC-126: THE SUITE COUNTS ITSELF, AND DECLARES THE TOTAL.
#
# This script printed a verdict per case and no tally, so the only way to learn
# its size was to count its output by hand. CLOSING-INVENTORY.md said "12
# cases" in two places and the measured figure is 32 -- stale by 20, and the
# fifth instance of a hand-typed count drifting in this repository.
#
# skipped is counted separately and added in, so the declaration is invariant
# under EA_SKIP_SLOW_ORACLES: a skip is still a case this suite HAS, it is just
# a case that did not run. A declaration that changed with the flag would have
# to be stated twice, which is the defect again.
cases=0
skipped=0
DECLARED_CASES=32
chk() { # chk <label> <expected-exit> <expected-text-fragment> <cmd...>
    local label=$1 want=$2 frag=$3; shift 3
    local out rc
    out=$("$@" 2>&1); rc=$?
    if [ "${rc}" != "${want}" ]; then
        printf '  %-44s FAIL  exit %s, wanted %s\n' "${label}" "${rc}" "${want}"
        cases=$((cases + 1)); fails=$((fails + 1)); return
    fi
    if [ -n "${frag}" ] && ! printf '%s' "${out}" | grep -qF "${frag}"; then
        printf '  %-44s FAIL  exit %s but not for the stated reason\n' "${label}" "${rc}"
        printf '        wanted a mention of: %s\n' "${frag}"
        cases=$((cases + 1)); fails=$((fails + 1)); return
    fi
    cases=$((cases + 1))
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

# A FIXTURE THAT WAS NEVER BUILT IS NOT A NEGATIVE CONTROL (OC-87).
#
# The three python3 heredocs below build the mutated reports every case feeds
# to an oracle, and their exit status was never read. If one failed -- no
# python3, a KeyError on a report shaped differently, a full disk -- the
# fixtures would be ABSENT, and an oracle handed a path that does not exist
# REFUSES and exits 1. Exit 1 is the expected status for most of these cases.
# So a fixture builder that died would have turned every case it fed into a
# PASS for a reason that has nothing to do with the defect under test: A08's
# own lesson, in the file A08 produced.
#
# So: the builder's status is read, and every fixture it was supposed to write
# is asserted to exist before any case runs.
built() { # built <rc> <fixture>...
    local rc=$1; shift
    if [ "${rc}" -ne 0 ]; then
        echo "oracle-selftest: a fixture builder exited ${rc}; the cases below would" >&2
        echo "                 refuse for the absence of their input, not for the defect." >&2
        exit 2
    fi
    local f
    for f in "$@"; do
        [ -s "${work}/${f}" ] || {
            echo "oracle-selftest: fixture ${f} was not written; refusing to run cases on it" >&2
            exit 2; }
    done
}

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
built $? no_errorlevel.json short.json entropy10.json nonfinite.json unrelated.json notjson.txt

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
built $? f08_c02.json f08_width.json f08_samples.json
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
built $? verdict_flipped.json cutoff_wrong.json no_verdict.json verdict_string.json
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

echo
echo "c22c_source.py -- the ONE SOURCE's fast validation (OC-125)"
# WHY THESE CASES. The two-copies defect was invisible because a check that
# verified the wrong object still passed. The fast validation's whole job is to
# refuse a source it cannot stand behind, so every limb of that refusal needs
# its own negative control with its OWN distinct reason -- the discipline the
# four A08 fixtures taught, where the first version refused four times for one
# shared accidental cause and tested nothing.
#
# Each fixture changes exactly ONE thing in a COPY of the genuine source.
S="python3 ${here}/c22c_source.py"
python3 - "${here}/c22c_source.json" "${work}" <<'PYEOF2'
import json, os, sys
src, W = sys.argv[1], sys.argv[2]
base = json.load(open(src))

def w(name, mut):
    d = json.loads(json.dumps(base))
    mut(d)
    json.dump(d, open(os.path.join(W, name), 'w'), indent=2)

def drop_stamp_field(d):
    del d['rows'][0]['compression']['stamp']['validated_against']
w('c22c_no_provenance.json', drop_stamp_field)

def wrong_sha(d):
    st = d['rows'][0]['compression']['stamp']
    st['derivation_sha256'] = '0' * 64
w('c22c_stale_derivation.json', wrong_sha)

# THESE TWO FIXTURES ARE DERIVED FROM THE SOURCE, NOT WRITTEN. The first
# version assigned the value as a literal -- and c22c-copy-sweep.sh reported
# both, correctly: a fixture that names one of these numbers is another copy
# of it, which is the defect the fixtures are here to guard against. Third
# time the sweep caught its own author.
def float_value(d):
    c = d['rows'][0]['compression']
    c['value'] = float(c['value'])          # the same number, as a float
w('c22c_float_value.json', float_value)

def short_value(d):
    c = d['rows'][0]['compression']
    c['value'] = '%.3g' % float(c['value'])  # the same number, 3 digits
w('c22c_wrong_digits.json', short_value)

def round_down(d):
    d['rounding'] = 'nearest'
w('c22c_rounds_down.json', round_down)

def ascending(d):
    d['rows'] = list(reversed(d['rows']))
w('c22c_row_order.json', ascending)

def carried_proportion(d):
    d['families']['proportion']['carried'] = True
w('c22c_carried_proportion.json', carried_proportion)

def bad_commit(d):
    d['rows'][0]['compression']['stamp']['stamped_at_repo_commit'] = 'f' * 40
w('c22c_absent_commit.json', bad_commit)
PYEOF2
built $? c22c_no_provenance.json c22c_stale_derivation.json c22c_float_value.json \
         c22c_wrong_digits.json c22c_rounds_down.json c22c_row_order.json \
         c22c_carried_proportion.json c22c_absent_commit.json
chk "the genuine source validates"                0 ""                        $S --validate
chk "a missing provenance field is REFUSED"       1 "no validated_against"    $S --validate "${work}/c22c_no_provenance.json"
chk "a stamp whose derivation has changed"        1 "derivation changed"      $S --validate "${work}/c22c_stale_derivation.json"
chk "a float value loses its precision"           1 "not a string"            $S --validate "${work}/c22c_float_value.json"
chk "fewer digits than the source declares"       1 "significant digits"      $S --validate "${work}/c22c_wrong_digits.json"
chk "rounding that is not toward a larger term"   1 "subtracts too little"    $S --validate "${work}/c22c_rounds_down.json"
chk "rows in ascending n break the lookup"        1 "descending n order"      $S --validate "${work}/c22c_row_order.json"
chk "a CARRIED proportion value is refused"       1 "would be a copy"         $S --validate "${work}/c22c_carried_proportion.json"
chk "a commit id that is not in this repository"  1 "not a commit"            $S --validate "${work}/c22c_absent_commit.json"
chk "a source that does not exist"                1 "does not exist"          $S --validate "${work}/c22c_absent.json"
chk "an unrelated JSON document is not a source"  1 "schema"                  $S --validate "${work}/unrelated.json"

echo
echo "c22c-copy-sweep.sh -- one source per family value, with its own control"
chk "no second copy of any C22c family value"     0 "PASS" bash "${here}/c22c-copy-sweep.sh"

echo
echo "compression_ceiling_exact.py -- C22c's binding term, against the STANDARD (OC-86)"
# This is the only oracle here validated against something outside the project:
# SP 800-90B 6.3.4's own worked example, for which NIST publishes p = 0.5715.
# It is also the only independent computation of the value entropy_floor.py
# subtracts -- zalpha_ceiling_by_n.py prints "(production solve, not
# reimplemented here)" for exactly those two cells.
#
# ~55 s, which is why it is last. EA_SKIP_SLOW_ORACLES=1 skips it, and then says
# so as a SKIP rather than passing: a check that did not run supports no claim.
if [ "${EA_SKIP_SLOW_ORACLES:-0}" = "1" ]; then
    skipped=$((skipped + 1))
    printf '  %-44s SKIP  EA_SKIP_SLOW_ORACLES=1\n' "C22c compression ceiling vs the standard"
else
    # On ONE line deliberately: split across a backslash continuation, the
    # python3 invocation sits alone in statement position and
    # regression-deadguard.sh flags it as "status never read". It is read, by
    # chk -- but a baseline carrying a false positive is worse than one
    # carrying none, so the line is written the way the detector can read.
    chk "worked example, then both recorded ceilings" 0 "AGREES" python3 "${here}/compression_ceiling_exact.py"
fi

total=$((cases + skipped))
if [ "${total}" -ne "${DECLARED_CASES}" ]; then
    printf '  %-44s FAIL  declared %s, ran %s (+%s skipped)\n' \
        "the declared case count" "${DECLARED_CASES}" "${cases}" "${skipped}"
    fails=$((fails + 1))
fi

echo
printf 'oracle-selftest: %d of %d declared cases ran' "${cases}" "${DECLARED_CASES}"
[ "${skipped}" -ne 0 ] && printf ', %d skipped' "${skipped}"
printf '\n'
if [ "${fails}" -eq 0 ]; then echo "oracle-selftest: PASS"; exit 0; fi
echo "oracle-selftest: FAIL (${fails} case(s))"; exit 1
