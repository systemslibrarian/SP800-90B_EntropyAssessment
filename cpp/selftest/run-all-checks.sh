#!/bin/bash
#
# Run every check in this directory and report one summary.
#
# regression-script-inventory.txt is the authoritative, version-controlled
# inventory.  Discovery is checked against that inventory before any test is
# run: adding, deleting, or renaming a script without deliberately updating the
# inventory is an incomplete suite and fails closed.
#
# Exit status is 0 only if every check passed. selftest is expected to exit 1
# on macOS arm64 for the pre-existing platform deltas in upstream #155; pass
# --allow-known-platform-deltas to treat that specific case as a pass, and
# nothing else.

set -u

here=$(cd "$(dirname "$0")" && pwd)
cd "${here}" || exit 2

allow_platform=0
[ "${1:-}" = "--allow-known-platform-deltas" ] && allow_platform=1

# A06 (OC-56): replaced by an expected-result manifest. The filename list it
# used to be excused ANY mismatch in these two files -- any estimator, any
# magnitude, any direction, any platform.
DELTA_MANIFEST="known-platform-deltas.txt"
here_cmp="./check-platform-deltas.py"
REGRESSION_INVENTORY="regression-script-inventory.txt"
EXPECTED_REGRESSION_SCRIPTS=22
EXPECTED_TOTAL_CHECKS=24

inventory_error() {
    echo "run-all-checks: regression inventory error: $*" >&2
    exit 2
}

[ -f "${REGRESSION_INVENTORY}" ] || inventory_error "${REGRESSION_INVENTORY} is missing"

inventory_names=""
inventory_count=0
while IFS= read -r name || [ -n "${name}" ]; do
    case "${name}" in
        regression-[A-Za-z0-9]*.sh) ;;
        *) inventory_error "malformed entry ${name:-<empty>}" ;;
    esac
    case " ${inventory_names} " in
        *" ${name} "*) inventory_error "duplicate entry ${name}" ;;
    esac
    [ -f "./${name}" ] || inventory_error "required script ${name} is missing"
    [ -x "./${name}" ] || inventory_error "required script ${name} is not executable"
    inventory_names="${inventory_names} ${name}"
    inventory_count=$((inventory_count + 1))
done < "${REGRESSION_INVENTORY}"

[ "${inventory_count}" -eq "${EXPECTED_REGRESSION_SCRIPTS}" ] ||
    inventory_error "expected ${EXPECTED_REGRESSION_SCRIPTS} entries, found ${inventory_count}"

discovered_names=""
discovered_count=0
for script in ./regression-*.sh; do
    [ -e "${script}" ] || continue
    name=$(basename "${script}")
    case " ${inventory_names} " in
        *" ${name} "*) ;;
        *) inventory_error "unexpected script ${name}" ;;
    esac
    case " ${discovered_names} " in
        *" ${name} "*) inventory_error "duplicate discovered script ${name}" ;;
    esac
    discovered_names="${discovered_names} ${name}"
    discovered_count=$((discovered_count + 1))
done

[ "${discovered_count}" -eq "${inventory_count}" ] ||
    inventory_error "expected ${inventory_count} scripts, discovered ${discovered_count}"

pass=0; fail=0; failed=""
# Exit 2 from a regression means it could not run — a prerequisite was absent —
# as distinct from exit 1, a regression it detected. Both count against this
# script's exit status, because a check that did not execute supports no claim,
# but they are reported apart so the operator knows whether to fix the
# environment or the code.
cannot=0; couldnot=""
# BUILD STATE MUST SURVIVE THE AGGREGATOR (rule 4, OC-66).
#
# This captured each script's output and, on success, printed only the label --
# so every `[build-state]` line the declaring scripts emit was thrown away one
# layer up. Rule 4's stated point is that a result WITHOUT that line is visibly
# incomplete, and the aggregator made every result look the same.
#
# Measured: binaries built -DNDEBUG, all three digests differing and the probe
# reporting asserts=NDEBUG against asserts=LIVE, then the full suite run on both
# arms. The verdicts were IDENTICAL CHECK FOR CHECK, 22 passed 0 failed on each,
# and neither output contained the string "build-state". The suite could not
# distinguish a build with every assert in lrs_test.h compiled out, and said
# nothing about which it had measured. No verdict flipped, so it was not a live
# false pass -- it is OC-42's exact error made undetectable again.
bs_seen=0; bs_silent=""
run() { # run <label> <command...>
    local label=$1; shift
    local out rc
    out=$("$@" 2>&1); rc=$?
    # Surface the declarations rather than discarding them, and record which
    # scripts made none so silence is visible instead of equivalent.
    local decl
    decl=$(printf '%s\n' "${out}" | grep -E '^\[build-state\]' || true)
    if [ -n "${decl}" ]; then
        bs_seen=$((bs_seen + 1))
    else
        bs_silent="${bs_silent} ${label}"
    fi
    if [ "${rc}" -eq 0 ]; then
        printf '  %-34s PASS\n' "${label}"
        [ -n "${decl}" ] && printf '%s\n' "${decl}" | sed 's/^/      /'
        pass=$((pass + 1))
        return
    fi
    if [ "${rc}" -eq 2 ]; then
        printf '  %-34s COULD NOT RUN (exit 2)\n' "${label}"
        printf '%s\n' "${out}" | tail -4 | sed 's/^/        /'
        cannot=$((cannot + 1)); couldnot="${couldnot} ${label}"
        return
    fi
    printf '  %-34s FAIL (exit %s)\n' "${label}" "${rc}"
    # 20 LINES, NOT 4 (OC-90). A member that fails is the one place where more
    # output is worth the noise, and four lines was not enough to diagnose a
    # regression-docs failure that reproduced only on Linux: the tail showed
    # the last check, which had passed, and said nothing about which of the
    # twenty above it had not. The COULD NOT RUN branch keeps its short tail --
    # its reason is in its last line by construction.
    printf '%s\n' "${out}" | tail -20 | sed 's/^/        /'
    fail=$((fail + 1)); failed="${failed} ${label}"
}

# THE TOOLS THE SUITE NEEDS ARE CHECKED ONCE, HERE, AND BY RUNNING THEM
# (OC-89).
#
# F11/OC-84 gave this script a third outcome; OC-79 stopped one member
# reporting a PASS when its interpreter was absent. The sweep that followed
# measured what the other members do, with `python3` replaced on PATH by a stub
# that exits 127: four report COULD NOT RUN (exit 2) and THIRTEEN report FAIL
# (exit 1). None reports a pass -- but a FAIL says "this code is broken" when
# the truth is "this host is missing a tool", and those need different actions
# from the operator.
#
# The aggregator is the right place for it: a missing python3 is a property of
# the host, not of any one member, and refusing the whole run once is more
# honest than thirteen members each discovering it separately.
#
# AND EACH TOOL IS RUN, NOT MERELY FOUND. `command -v` answers a different
# question: the sweep's own stub is a file on PATH with the execute bit set, so
# `command -v python3` succeeds and `python3 -c pass` exits 127. "Present" and
# "works" are different claims and only the second one matters here.
missing=""
req_run() {  # req_run <label> <command...>  -- the command must succeed
    # SHIFT the label off before running. The first draft did not, so it ran
    # `python3 python3 -c pass` -- python3 trying to execute a FILE named
    # python3 -- which fails on a perfectly healthy host. It would have refused
    # every run. Caught because the test printed "python3 perl" as missing on a
    # machine where both plainly work.
    local label=$1; shift
    if ! "$@" >/dev/null 2>&1; then
        missing="${missing} ${label}"
    fi
}
req_any() {  # req_any <label> -- any one of the remaining args, run as a word
    local label=$1; shift
    local c
    for c in "$@"; do
        if ${c} >/dev/null 2>&1; then return 0; fi
    done
    missing="${missing} ${label}"
}
req_run python3 python3 -c pass
req_run perl perl -e 1
req_any "shasum-or-sha256sum" "shasum --version" "sha256sum --version"
# cc is used by the members that compile a fixture generator or a probe.
req_run cc cc --version
if [ -n "${missing}" ]; then
    echo "run-all-checks: COULD NOT RUN -- these tools are absent or do not work:${missing}" >&2
    echo "                No check below is reported, because a suite that cannot run its" >&2
    echo "                members has no verdict on them. Install them and re-run." >&2
    exit 2
fi

for b in ../ea_non_iid ../ea_iid ../ea_restart; do
    [ -x "${b}" ] || { echo "run-all-checks: $(basename "${b}") is missing; run 'make non_iid iid restart' first" >&2; exit 2; }
done

echo "pinned figure and reference comparison"
run pin-check ./pin-check.sh --prove-nonvacuous

# selftest against NIST's reference data. Its failure on the known platform
# files is reported either way; --allow-known-platform-deltas decides whether
# it counts against the exit status.
out=$(./selftest 2>&1); rc=$?
rm -f ./*.res
if [ "${rc}" -eq 0 ]; then
    printf '  %-34s PASS\n' "selftest"; pass=$((pass + 1))
else
    line=$(printf '%s' "${out}" | grep -E '^selftest: FAIL')
    files=$(printf '%s' "${line}" | sed 's/^.*files)://')
    nfiles=0
    for f in ${files}; do nfiles=$((nfiles + 1)); done
    # selftest exited non-zero. If it printed no "selftest: FAIL" summary line,
    # or that line names no file, there is nothing to classify and the run must
    # NOT be excused. This used to fail open: an empty classification left
    # only_known=1, so with --allow-known-platform-deltas the harness printed
    # "PASS (only the known upstream #155 platform files)" and exited 0 when no
    # file had been compared at all -- a green that named the two excused files
    # while selftest had died before reaching them. The flag is the documented
    # macOS invocation, so that was the path normally run. Observed to fail
    # against a selftest stub that exits non-zero printing no summary line.
    if [ -z "${line}" ] || [ "${nfiles}" -eq 0 ]; then
        printf '  %-34s FAIL (exit %s, no "selftest: FAIL" summary line to classify)\n' "selftest" "${rc}"
        printf '%s\n' "${out}" | tail -4 | sed 's/^/        /'
        fail=$((fail + 1)); failed="${failed} selftest"
    elif [ "${allow_platform}" -eq 1 ]; then
        # A06 (OC-56): the exception is no longer a filename list. Every
        # reported difference must match an EXPECTED-RESULT ROW for THIS
        # platform on file, estimator and field, and be within that row's
        # tolerance; every row listed for this platform must have been
        # observed; and the platform identity itself must match. Anything
        # else fails, with the flag enabled.
        verdict=$(printf '%s\n' "${out}" | SELFTEST_DELTA_MANIFEST="${DELTA_MANIFEST}" \
                  PLAT_S="$(uname -s)" PLAT_M="$(uname -m)" \
                  PLAT_CC="$(${CXX:-c++} --version 2>&1 | head -1)" \
                  python3 "${here_cmp}" 2>&1)
        vrc=$?
        if [ "${vrc}" -eq 0 ]; then
            printf '  %-34s PASS (%s)\n' "selftest" "$(printf '%s' "${verdict}" | head -1)"
            pass=$((pass + 1))
        else
            printf '  %-34s FAIL (the platform-delta exception does NOT cover this)\n' "selftest"
            printf '        %s\n' "${line}"
            printf '%s\n' "${verdict}" | sed 's/^/        /'
            fail=$((fail + 1)); failed="${failed} selftest"
        fi
    else
        printf '  %-34s FAIL\n' "selftest"
        printf '        %s\n' "${line}"
        printf '        a known-platform-delta exception exists but was not requested; see known-platform-deltas.txt\n'
        fail=$((fail + 1)); failed="${failed} selftest"
    fi
fi

echo
echo "regression scripts (authoritative inventory verified)"
found=0
while IFS= read -r name || [ -n "${name}" ]; do
    s="./${name}"
    found=$((found + 1))
    run "$(basename "${s}" .sh)" "${s}"
done < "${REGRESSION_INVENTORY}"

if [ "${found}" -ne "${EXPECTED_REGRESSION_SCRIPTS}" ]; then
    echo "run-all-checks: executed ${found} regression scripts; expected ${EXPECTED_REGRESSION_SCRIPTS}" >&2
    fail=$((fail + 1)); failed="${failed} regression-inventory"
fi

# F11 (OC-84): THE TOTAL IS THREE CATEGORIES, NOT TWO.
#
# This was `total=$((pass + fail))`, omitting `cannot` -- while the build-state
# line thirteen lines below counted `pass + fail + cannot`. The same script
# disagreed with itself about how many checks it had run, and the consequences
# compounded. Measured, with one regression made to exit 2:
#
#   run-all-checks: executed 22 total checks; expected 23        <- false
#   build-state: 4 of 24 checks declared the artefact they measured   <- 24
#   run-all-checks: 22 passed, 1 failed, 1 could not run
#   failed: total-check-count
#
# Three wrong numbers from one missing term. 23 checks DID execute, one of them
# could not run; the "1 failed" was entirely manufactured by this guard; and it
# inflated the build-state denominator to 24 by adding the failure it had just
# invented to a line that was counting correctly. The condition it claimed to
# detect -- a check that did not run -- was already reported on its own line.
#
# A check that could not run WAS executed and supports no claim. It belongs in
# the total and against the exit status, which it already was; it was only
# missing from the arithmetic. The total is now computed ONCE and both sites
# read it, so they cannot drift apart again.
total=$((pass + fail + cannot))
if [ "${total}" -ne "${EXPECTED_TOTAL_CHECKS}" ]; then
    echo "run-all-checks: executed ${total} total checks; expected ${EXPECTED_TOTAL_CHECKS}" >&2
    fail=$((fail + 1)); failed="${failed} total-check-count"
    total=$((pass + fail + cannot))
fi

echo
# BUILD-STATE COVERAGE IN THE SUMMARY (rule 4, OC-66). A reader must be able to
# tell, from the summary alone, whether this run said anything about the
# artefacts it measured. The count is printed on its own line, ABOVE the
# summary, so the summary line itself stays byte-identical -- the inventory
# mutation harness matches that line exactly and the comment below depends on
# it.
printf 'build-state: %d of %d checks declared the artefact they measured\n' \
    "${bs_seen}" "${total}"
if [ "${bs_seen}" -eq 0 ]; then
    echo "build-state: NO CHECK DECLARED ONE. This run is silent about whether it" >&2
    echo "             measured an asserts-live build or a -DNDEBUG one, and the two" >&2
    echo "             are indistinguishable from its verdicts (OC-66)." >&2
fi

# The summary line stays byte-identical when nothing was skipped: the repair
# branch's harness-inventory-mutation-test.sh matches it exactly.
if [ "${cannot}" -eq 0 ]; then
    echo "run-all-checks: ${pass} passed, ${fail} failed (${found} regression scripts discovered)"
else
    echo "run-all-checks: ${pass} passed, ${fail} failed, ${cannot} could not run (${found} regression scripts discovered)"
    echo "could-not-run:${couldnot}"
fi
[ "${fail}" -eq 0 ] && [ "${cannot}" -eq 0 ] && exit 0
[ "${fail}" -eq 0 ] || echo "failed:${failed}"
exit 1
