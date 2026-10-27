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

# OC-121: RESTORE ON EVERY EXIT PATH, INCLUDING SIGNAL AND KILL.
#
# THIS SCRIPT HAD NO TRAP AT ALL. A background verification of it was killed
# mid-arm and left a LIVE C22c MUTATION in entropy_floor.py -- 3.3599e-3 ->
# 3.3700e-3, the constant every entropy figure in this project subtracts.
# Nothing downstream would have announced it; it was caught by `git status`.
# That is the most dangerous mechanism in this repository, and the absence of a
# trap is why a kill could leave it behind.
#
# The file currently under mutation is now tracked and restored by a trap that
# fires on EXIT, HUP, INT and TERM -- not only on clean completion.
MUTATING=""
restore_mutating() {
    if [ -n "${MUTATING}" ] && [ -e "${MUTATING}" ]; then
        if git checkout -- "${MUTATING}" 2>/dev/null; then
            echo "band1: restored ${MUTATING} on exit" >&2
        else
            echo "band1: *** COULD NOT RESTORE ${MUTATING} -- CHECK IT BY HAND ***" >&2
        fi
        MUTATING=""
    fi
}
trap 'restore_mutating' EXIT HUP INT TERM

caught=0; missed=0; noapply=0; ctlfail=0
digest() { local h; h=$( (command -v shasum >/dev/null && shasum -a 256 "$1") || sha256sum "$1" ); echo "${h%% *}"; }
note() { printf '  %-44s %-22s %s\n' "$1" "$2" "${3:-}"; }

# OC-120: THE TREE IS RE-CHECKED BEFORE EVERY ARM, NOT ONLY AT THE START.
#
# This script refused to START on a dirty tree but not to CONTINUE when the
# tree went dirty under it. In OC-117 that happened: files were edited in the
# working tree while the battery ran, and `git checkout --` restored over
# those edits and DESTROYED them. The digest check caught that no verdict had
# been earned, which is why two arms reported RESTORE FAILED -- but the edits
# were already gone.
#
# So each arm now re-checks the file it is about to mutate, and REFUSES rather
# than restoring over something that changed.
arm_tree_is_clean() {   # arm_tree_is_clean <file> -- 0 if safe to mutate
    git diff --quiet -- "$1" && git diff --cached --quiet -- "$1"
}

# run_pair <label> <mech> <file> <old> <new> <test-cmd...>
run_pair() {
    local label=$1 mech=$2 file=$3 old=$4 new=$5; shift 5
    local before after ctl_rc mut_rc
    if [ ! -f "${file}" ]; then note "${label}" "FILE ABSENT" "${file}"; noapply=$((noapply+1)); return; fi
    if ! arm_tree_is_clean "${file}"; then
        note "${label}" "REFUSED" "${file} has uncommitted changes; restoring would destroy them"
        noapply=$((noapply+1)); return
    fi
    before=$(digest "${file}")

    # THE CONTROL ARM FIRST. A case that was already failing cannot be used to
    # judge a mutation, and reporting "CAUGHT" from it would be a false result.
    "$@" >/dev/null 2>&1; ctl_rc=$?
    if [ "${ctl_rc}" -ne 0 ]; then
        note "${label}" "CONTROL FAILED" "exit ${ctl_rc} before any mutation (${mech})"
        ctlfail=$((ctlfail+1)); return
    fi

    MUTATING="${file}"
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
    MUTATING=""
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

# ---------------------------------------------------------------- C22c (OC-125)
#
# THESE THREE ARMS CHANGED TARGET AND CHECKER, AND BOTH CHANGES MATTER.
#
# TARGET. They used to mutate a literal in entropy_floor.py. The six C22c
# family values now live in exactly one place, c22c_source.json, and nothing
# else records them -- including this file, which is why the old and new
# strings are ASKED FOR rather than written here. A battery that named the
# number it replaces would be the seventh copy of it, and c22c-copy-sweep.sh
# reports this file when it is.
#
# CHECKER. They used to run oracle-selftest.sh, and both reported NOT CAUGHT.
# THAT VERDICT WAS A STATEMENT ABOUT THAT CHECKER, NOT ABOUT THE REPOSITORY,
# and it must not be read as an unguarded tree: regression-constants.sh has
# pinned these values since OC-121 and would have caught the same mutation.
# What oracle-selftest could not catch was the two-copies defect itself -- it
# re-derived the ceiling and compared it against a SECOND copy in
# compression_ceiling_exact.py, so it was green no matter what the floor
# subtracted. The checker is now the repository's actual guard, so a verdict
# here is a statement about the repository.
# THE OLD AND NEW STRINGS ARE ASKED FOR, NEVER WRITTEN. c22c_source.py has
# --value, --perturb and --stamp-sha for exactly this; the perturbation lives
# there rather than in a heredoc here, both so this file names no number and
# because the heredoc made regression-deadguard.sh flag these arms twice.
C="python3 ${O}/c22c_source.py"

for _fam_n in "compression 1000000" "compression 8000000" "collision 1000000"; do
    set -- ${_fam_n}
    _fam=$1; _n=$2
    _old=$(${C} --value "${_fam}" "${_n}") || { echo "band1: cannot read the C22c source" >&2; exit 2; }
    _new=$(${C} --perturb "${_old}") || { echo "band1: cannot perturb the value" >&2; exit 2; }
    run_pair "C22c ${_fam} ceiling, n=${_n}" "acedae5+ada37a1, now OC-125" \
        "${O}/c22c_source.json" "${_old}" "${_new}" \
        bash cpp/selftest/regression-constants.sh
done

# THE STAMP IS A MECHANISM TOO, so it gets an arm. The fast validation refuses
# when a stamp's recorded derivation sha256 stops matching the file in the
# tree -- that is what stops an edited derivation from quietly leaving a stale
# value behind. Breaking the recorded sha must therefore FAIL the suite; if it
# does not, editing a derivation is silent again.
_sha=$(${C} --stamp-sha compression 1000000) || { echo "band1: cannot read the C22c stamp" >&2; exit 2; }
run_pair "C22c stamp: the derivation sha256" "OC-125" \
    "${O}/c22c_source.json" "${_sha}" "${_sha%??}00" \
    bash cpp/selftest/regression-constants.sh

run_pair "the oracles' exit contract" "b072bf7" \
    "${O}/restart_decision_exact.py" 'sys.exit(2)' 'sys.exit(0)' \
    bash "${O}/oracle-selftest.sh"

# THIS ARM'S MUTATION WAS ABSORBED BY A COINCIDENCE (found OC-126).
#
# It replaces a pinned figure with 0.8547 and requires the guard to notice that
# the record no longer cites it. The guard's citation test was a BARE SUBSTRING
# grep, and at b9531b8 `OC-116..OC-118` wrote the measured mean 0.854784 into
# ORCHESTRATOR-CHECKS.md -- so "0.8547" was still found, in the middle of an
# unrelated number, and the arm reported NOT CAUGHT from OC-125 on. That is why
# this arm was CAUGHT at OC-105 and NOT CAUGHT later with no change to either
# the guard or the arm: the DOCUMENT moved under both of them.
#
# Two repairs, not one. The guard is anchored so a figure must be cited as a
# figure (OC-126, in regression-outside-battery.sh). And the arm now asserts
# that its replacement value is ABSENT from the cited document before it will
# draw a verdict -- because a mutation to a value the document happens to
# contain tests nothing, and the next number written into a 12,000-line record
# could re-create exactly this situation in silence.
# AND THE FIRST VERSION OF THIS PRECONDITION MADE THE ARM UNUSABLE, WITHIN THE
# HOUR, BY MY OWN HAND. Writing the OC-126 entry put "0.8547" into
# ORCHESTRATOR-CHECKS.md seven times -- documenting this very defect -- so the
# precondition fired, the arm reported MUTATION-DID-NOT-APPLY, and the battery
# went INCONCLUSIVE. The hazard named in the comment above re-created itself
# immediately, which is the strongest evidence that a FIXED replacement value is
# the wrong design.
#
# So the arm SEARCHES for a replacement instead of asserting one: increment the
# last digit until a value is found that the cited document does not cite, and
# refuse only if every candidate is taken. The mutation stays a one-digit change
# to a pinned figure -- what the arm is named for -- and it cannot be absorbed by
# whatever number the record happens to contain today.
_cite_doc="audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md"
_cited() { grep -qE "(^|[^0-9.])${1//./\\.}([^0-9]|$)" "${_cite_doc}"; }
# NINE CANDIDATES WAS THE SAME HAZARD AT A SLOWER RATE. Every record of this
# arm's output cites the value it chose, which burns that candidate; nine
# entries would have exhausted the list and the arm would have refused for a
# reason unrelated to the guard. So: the one-digit neighbours first, then every
# other 0.85xx -- 99 candidates, no duplicates (verified in isolation, OC-126).
_cands() {
    echo 0.8547 0.8548 0.8549 0.8541 0.8542 0.8543 0.8544 0.8545 0.8540
    local a b
    for a in 0 1 2 3 5 6 7 8 9; do for b in 0 1 2 3 4 5 6 7 8 9; do echo "0.85${a}${b}"; done; done
}
_repl=""
for _cand in $(_cands); do
    _cited "${_cand}" || { _repl="${_cand}"; break; }
done
if [ -z "${_repl}" ]; then
    note "outside-battery pinned figures" "MUTATION-DID-NOT-APPLY" \
         "every candidate replacement for 0.8546 is cited in ${_cite_doc}"
    noapply=$((noapply+1))
else
    # the control for the search itself: the value it chose must be absent, and
    # the value being replaced must be present, or the arm is testing nothing.
    if ! _cited 0.8546; then
        note "outside-battery pinned figures" "MUTATION-DID-NOT-APPLY" \
             "0.8546 is not cited in ${_cite_doc}; the guard would refuse before any mutation"
        noapply=$((noapply+1))
    else
        run_pair "outside-battery pinned figures (0.8546 -> ${_repl})" "feef1a1" \
            cpp/selftest/regression-outside-battery.sh \
            'for fig in 8538.7 59.938 40.21 0.8546; do' \
            "for fig in 8538.7 59.938 40.21 ${_repl}; do" \
            bash cpp/selftest/regression-outside-battery.sh
    fi
fi

# THIS ARM MUTATED A STRING THE ENFORCEMENT DOES NOT READ (found OC-125).
#
# It replaced the first occurrence of `11207ca`, which is a HISTORICAL mention
# on line 87 -- part of the record of what the document's previous version got
# wrong. The enforcement reads two other things: the commit named on line 3
# (`**Measured at commit `<sha>``) and the FIGURES it re-measures at that
# commit. Measured on the current tree: mutating `11207ca` leaves
# regression-docs.sh byte-identical and exit 0. The arm was testing nothing,
# and the document was re-measured from `11207ca` to `34ceb59` at `cdc2969`,
# which is when the anchor went stale.
#
# The arm is named for the FIGURE enforcement, so it mutates a figure. The
# re-measurement then reports `figures have drifted: ahead(197)` and exits 1.
# Mutating the measured-at commit instead exits 2 -- "THE SCAN DID NOT RUN, so
# its silence means nothing" -- which is also a refusal, and also correct, but
# it tests the staleness limb rather than the figure limb.
#
# WHY THE PREVIOUS RUN SAID CAUGHT IS NOT ESTABLISHED. The battery reported
# CAUGHT for this arm on 2026-10-26 with the SAME mutation, against a tree
# whose regression-docs.sh is byte-identical and whose line 87 is byte-identical
# to now. That verdict cannot be reproduced and is not explained here. It is
# recorded as unexplained rather than quietly replaced.
run_pair "the divergence-figure enforcement" "4ad3095" \
    FORK-DIVERGENCE-AND-TRUST.md \
    '**197 commits ahead' '**196 commits ahead' \
    bash cpp/selftest/regression-docs.sh

run_pair "mutation-lib's landing contract" "65b00d8" \
    cpp/selftest/mutation-lib.sh \
    'MUTATION-DID-NOT-APPLY' 'MUTATION-DID-NOT-APPLY-X' \
    bash cpp/selftest/harness-inventory-mutation-test.sh

# ---------------------------------------------------------------------------
# OC-117: the mechanisms OC-105 did NOT cover.
#
# OC-105 reported "9 of 15 mutated". That CONFLATED ARMS WITH MECHANISMS: its
# nine arms covered EIGHT of the fifteen band-1 mechanisms, because c2f2b94
# took two arms and acedae5/ada37a1 shared two. Seven were uncovered, one of
# which (5c3353f, two instrument RULES) has no runnable case at all. The six
# workable ones follow.
# ---------------------------------------------------------------------------

run_pair "the canary's input precondition" "8ff739d" \
    tools/build-provenance-canary.sh \
    'EXPECTED_SHA="327773dd47cc480794f205f306aadd20972e258d9b0b880b7d12ad992e0b468c"' \
    'EXPECTED_SHA="327773dd47cc480794f205f306aadd20972e258d9b0b880b7d12ad992e0b468d"' \
    bash tools/build-provenance-canary.sh cpp/ea_iid

run_pair "C23's recomputed cutoff decision" "5074fff" \
    cpp/selftest/regression-restart.sh '1:572:570' '1:572:571' \
    bash cpp/selftest/regression-restart.sh

run_pair "C23's cutoff-method gate" "7a0be01" \
    cpp/selftest/regression-restart.sh \
    "d.get('restartCutoffMethod') == 'exact-multinomial-maximum'" \
    "d.get('restartCutoffMethod') == 'printed-binomial-SUPERSEDED'" \
    bash cpp/selftest/regression-restart.sh

# 210aed6 needs a REBUILD, which run_pair does not do, so it gets its own arm.
# The mutation removes O_EXCL from the temporary's open -- the primitive oac-13
# introduced so the temporary cannot land on an existing file -- and the F03
# cases of regression-output-aliasing.sh are what must notice.
atomic_write_pair() {
    local label="atomic report write (O_EXCL)" mech="210aed6"
    local b="${work_a:=$(mktemp -d "${TMPDIR:-/tmp}/ea-atomic.XXXXXX")}"
    rm -rf "${b}"; mkdir -p "${b}"
    cp -R cpp "${b}/cpp" || { note "${label}" "SETUP FAILED"; noapply=$((noapply+1)); return; }
    # control: build the copy UNMUTATED and confirm the regression passes there,
    # so a failure later cannot be blamed on the copy or the compiler.
    ( cd "${b}/cpp" && rm -f *.o ea_non_iid ea_iid ea_restart && make -j4 non_iid iid restart ) >/dev/null 2>&1
    if ! REGRESSION_OUTPUT_BINDIR="${b}/cpp" bash cpp/selftest/regression-output-aliasing.sh >/dev/null 2>&1; then
        note "${label}" "CONTROL FAILED" "the unmutated copy already fails (${mech})"
        ctlfail=$((ctlfail+1)); rm -rf "${b}"; return
    fi
    # THE HEREDOC'S STATUS IS READ. regression-deadguard.sh flagged this as a
    # pattern-B dead guard the moment it was written -- an interpreter heredoc
    # carrying an assertion whose exit status nobody reads -- and it was right:
    # a missing anchor would have made the assert fail silently. Caught by the
    # detector on the very first suite run after this arm was added, which is
    # the baseline mechanism doing its job rather than a baseline to rebase.
    if ! python3 - "${b}/cpp/shared/TestRunUtils.h" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = 'int flags = O_WRONLY | O_CREAT | O_EXCL;'
if old not in s:
    sys.stderr.write('band1: O_EXCL anchor not found in %s\n' % p)
    raise SystemExit(1)
open(p, 'w').write(s.replace(old, 'int flags = O_WRONLY | O_CREAT;', 1))
PY
    then
        note "${label}" "MUTATION-DID-NOT-APPLY" "the O_EXCL anchor was not found"
        noapply=$((noapply + 1)); rm -rf "${b}"; return
    fi
    ( cd "${b}/cpp" && rm -f *.o ea_non_iid ea_iid ea_restart && make -j4 non_iid iid restart ) >/dev/null 2>&1
    if ! grep -q 'O_WRONLY | O_CREAT;' "${b}/cpp/shared/TestRunUtils.h"; then
        note "${label}" "MUTATION-DID-NOT-APPLY" "O_EXCL still present"
        noapply=$((noapply+1)); rm -rf "${b}"; return
    fi
    REGRESSION_OUTPUT_BINDIR="${b}/cpp" bash cpp/selftest/regression-output-aliasing.sh >/dev/null 2>&1
    local mrc=$?
    rm -rf "${b}"
    if [ "${mrc}" -ne 0 ]; then
        note "${label}" "CAUGHT" "control 0, mutant ${mrc} (${mech})"
        caught=$((caught+1))
    else
        note "${label}" "NOT CAUGHT" "control 0, mutant 0 -- unguarded (${mech})"
        missed=$((missed+1))
    fi
}
atomic_write_pair

note "canary 3-way re-signaturing (b12247c)" "NOT MUTATED" "needs four builds; declared, not claimed"
note "canary long-double widening (9aa991d)" "NOT MUTATED" "needs an 80-bit host; binary128 stays NOT RUN"
note "two instrument rules (5c3353f)" "NO RUNNABLE CASE" "rule text, not a mechanism (OC-100)"

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
