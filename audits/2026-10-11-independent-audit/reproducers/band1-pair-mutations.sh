#!/bin/bash
#
# OC-105 -- the band-1 undeclared repair-interaction pairs, each tested BY
# BREAKING THE EARLIER MECHANISM.
#
# WHAT A PAIR TEST ACTUALLY IS. OC-100 banded 66 undeclared pairs: 27 reach a
# figure (band 1) over 15 distinct earlier mechanisms, 39 reach only a claim
# (band 2). It then reported that 14 of the 15 mechanisms "were exercised this
# campaign" -- which means each mechanism's own case was RUN AND PASSED. That
# is not a pair test. The risk a pair carries is that the LATER repair undid
# the EARLIER one, and a passing test cannot distinguish "the earlier mechanism
# still works" from "nothing checks the earlier mechanism any more".
#
# So each entry here BREAKS the earlier mechanism and asserts that the case
# which is supposed to catch it FAILS. Three outcomes, never two:
#
#   CAUGHT              control passed, mutant failed -- the pair is tested
#   NOT CAUGHT          control passed, mutant ALSO passed -- nothing guards it
#   MUTATION-DID-NOT-APPLY  the file did not change; no verdict is earned
#   CONTROL FAILED      the case was already failing; no verdict is earned
#
# The last two exist because of mutation-lib.sh's contract and for the same
# reason: a mutation that did not land may produce neither a pass nor a fail.
#
# RESTORATION IS `git checkout --`, so this script REFUSES to run on a dirty
# tree rather than destroy uncommitted work.

set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../../.." && pwd)
cd "${repo}" || exit 2

if [ -n "$(git status --porcelain)" ]; then
    echo "band1-pair-mutations: the working tree is dirty." >&2
    echo "  This script restores mutated files with 'git checkout --', which would" >&2
    echo "  discard uncommitted work. Commit or stash first." >&2
    exit 2
fi

caught=0; missed=0; noapply=0; ctlfail=0
digest() { local h; h=$( (command -v shasum >/dev/null && shasum -a 256 "$1") || sha256sum "$1" ); echo "${h%% *}"; }
note() { printf '  %-44s %-22s %s\n' "$1" "$2" "${3:-}"; }

# run_pair <label> <mech> <file> <old> <new> <test-cmd...>
run_pair() {
    local label=$1 mech=$2 file=$3 old=$4 new=$5; shift 5
    local before after ctl_rc mut_rc
    if [ ! -f "${file}" ]; then note "${label}" "FILE ABSENT" "${file}"; noapply=$((noapply+1)); return; fi
    before=$(digest "${file}")

    # THE CONTROL ARM FIRST. A case that was already failing cannot be used to
    # judge a mutation, and reporting "CAUGHT" from it would be a false result.
    "$@" >/dev/null 2>&1; ctl_rc=$?
    if [ "${ctl_rc}" -ne 0 ]; then
        note "${label}" "CONTROL FAILED" "exit ${ctl_rc} before any mutation (${mech})"
        ctlfail=$((ctlfail+1)); return
    fi

    OLD="${old}" NEW="${new}" python3 - "${file}" <<'PY'
import os, sys
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
old, new = os.environ['OLD'], os.environ['NEW']
if old in s:
    open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
PY
    after=$(digest "${file}")
    if [ "${before}" = "${after}" ]; then
        note "${label}" "MUTATION-DID-NOT-APPLY" "anchor not found in ${file}"
        noapply=$((noapply+1)); return
    fi

    "$@" >/dev/null 2>&1; mut_rc=$?
    git checkout -- "${file}"
    if [ "$(digest "${file}")" != "${before}" ]; then
        note "${label}" "RESTORE FAILED" "${file} did not return to its committed state"
        noapply=$((noapply+1)); return
    fi

    if [ "${mut_rc}" -ne 0 ]; then
        note "${label}" "CAUGHT" "control 0, mutant ${mut_rc} (${mech})"
        caught=$((caught+1))
    else
        note "${label}" "NOT CAUGHT" "control 0, mutant 0 -- unguarded (${mech})"
        missed=$((missed+1))
    fi
}

echo "band-1 pair mutations -- breaking the EARLIER mechanism of each pair"
echo

O="audits/2026-10-11-independent-audit/oracles"

run_pair "A02/A06 platform-delta manifest" "c2f2b94" \
    cpp/selftest/known-platform-deltas.txt \
    'delta ringOsc-nist.bin|Literal MultiMCW Prediction Estimate|min entropy|1e-9|1.5468587521994e-10' \
    '' \
    bash cpp/selftest/regression-platform-deltas.sh

run_pair "A02/A06 the tolerance itself" "c2f2b94" \
    cpp/selftest/known-platform-deltas.txt \
    'Bitstring MultiMMC Prediction Estimate|min entropy|1e-9|3.65934130219792e-10' \
    'Bitstring MultiMMC Prediction Estimate|min entropy|1e-30|3.65934130219792e-10' \
    bash cpp/selftest/regression-platform-deltas.sh

run_pair "C22c compression ceiling, n=1e6" "acedae5+ada37a1" \
    "${O}/entropy_floor.py" '3.3599e-3' '3.3700e-3' \
    bash "${O}/oracle-selftest.sh"

run_pair "C22c compression ceiling, n=8e6" "acedae5+ada37a1" \
    "${O}/entropy_floor.py" '2.1644e-3' '2.1700e-3' \
    bash "${O}/oracle-selftest.sh"

run_pair "OC-67 per-family denominator" "6b4717e" \
    "${O}/entropy_floor.py" "'collision': 7.84e-4" "'collision': 7.90e-4" \
    bash "${O}/oracle-selftest.sh"

run_pair "the oracles' exit contract" "b072bf7" \
    "${O}/restart_decision_exact.py" 'sys.exit(2)' 'sys.exit(0)' \
    bash "${O}/oracle-selftest.sh"

run_pair "outside-battery pinned figures" "feef1a1" \
    cpp/selftest/regression-outside-battery.sh \
    'for fig in 8538.7 59.938 40.21 0.8546; do' \
    'for fig in 8538.7 59.938 40.21 0.8547; do' \
    bash cpp/selftest/regression-outside-battery.sh

run_pair "the divergence-figure enforcement" "4ad3095" \
    FORK-DIVERGENCE-AND-TRUST.md \
    '11207ca' '1120700' \
    bash cpp/selftest/regression-docs.sh

run_pair "mutation-lib's landing contract" "65b00d8" \
    cpp/selftest/mutation-lib.sh \
    'MUTATION-DID-NOT-APPLY' 'MUTATION-DID-NOT-APPLY-X' \
    bash cpp/selftest/harness-inventory-mutation-test.sh

echo
printf 'band1-pair-mutations: %d CAUGHT, %d NOT CAUGHT, %d no-apply/restore, %d control-failed\n' \
    "${caught}" "${missed}" "${noapply}" "${ctlfail}"
# NOT CAUGHT is the finding this script exists to produce, so it does not fail
# the script; an unusable arm does, because an unusable arm is no measurement.
if [ "${noapply}" -ne 0 ] || [ "${ctlfail}" -ne 0 ]; then
    echo "band1-pair-mutations: INCONCLUSIVE (an arm produced no verdict)"
    exit 2
fi
echo "band1-pair-mutations: COMPLETE"
exit 0
