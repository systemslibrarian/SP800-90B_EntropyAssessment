#!/bin/bash
# Standalone mutation controls for run-all-checks.sh's own script inventory.
# Uses inert local stubs so it tests coverage accounting without rerunning the
# expensive estimators.  It does not use the TruePad wrapper.

set -u

here=$(cd "$(dirname "$0")" && pwd)
. "${here}/mutation-lib.sh"

# OC-126: declared here, asserted against the runtime tally by mut_summary,
# and read from here by regression-docs.sh. One number, three places that
# must agree, and a drift anywhere fails rather than printing a new total.
MUT_DECLARED=5

scratch=$(mktemp -d "${TMPDIR:-/tmp}/sp80090b-harness-inventory.XXXXXX") || exit 2
trap 'rm -rf "${scratch}"' EXIT HUP INT TERM

make_case() {
    root=$1
    mkdir -p "${root}/cpp/selftest"
    cp "${here}/run-all-checks.sh" "${here}/regression-script-inventory.txt" "${root}/cpp/selftest/"
    for helper in pin-check.sh selftest; do
        printf '#!/bin/sh\nexit 0\n' > "${root}/cpp/selftest/${helper}"
        chmod +x "${root}/cpp/selftest/${helper}"
    done
    while IFS= read -r name || [ -n "${name}" ]; do
        printf '#!/bin/sh\nexit 0\n' > "${root}/cpp/selftest/${name}"
        chmod +x "${root}/cpp/selftest/${name}"
    done < "${here}/regression-script-inventory.txt"
    for tool in ea_non_iid ea_iid ea_restart; do
        printf '#!/bin/sh\nexit 0\n' > "${root}/cpp/${tool}"
        chmod +x "${root}/cpp/${tool}"
    done
}

# The positive control: the unmutated stub tree must report the exact summary.
#
# DERIVED, NOT HARDCODED (OC-54). This used to compare against the literal
# "20 passed, 0 failed (18 regression scripts discovered)", and registering one
# new regression script made the control fail for a reason that had nothing to
# do with the mutations -- a hardcoded count inside a harness is itself a
# staleness trap, and a failing positive control invalidates every negative
# result beneath it. The numbers now come from run-all-checks.sh's own
# authoritative constants.
EXPECTED_SUMMARY=$(
    checks=$(sed -n 's/^EXPECTED_TOTAL_CHECKS=\([0-9]*\)$/\1/p' "${here}/run-all-checks.sh" | head -1)
    scripts=$(sed -n 's/^EXPECTED_REGRESSION_SCRIPTS=\([0-9]*\)$/\1/p' "${here}/run-all-checks.sh" | head -1)
    if [ -z "${checks}" ] || [ -z "${scripts}" ]; then
        echo "UNREADABLE"
    else
        printf 'run-all-checks: %s passed, 0 failed (%s regression scripts discovered)' "${checks}" "${scripts}"
    fi
)
if [ "${EXPECTED_SUMMARY}" = "UNREADABLE" ]; then
    echo "harness-inventory-mutation-test: cannot read the expected counts from" >&2
    echo "  run-all-checks.sh; refusing to run rather than compare against a guess." >&2
    exit 2
fi

expect_pass() {
    label=$1; root=$2
    output=$("${root}/cpp/selftest/run-all-checks.sh" 2>&1); rc=$?
    if [ "${rc}" -ne 0 ] || ! printf '%s\n' "${output}" | grep -qF "${EXPECTED_SUMMARY}"; then
        echo "harness-inventory-mutation-test: ${label} positive control failed (exit ${rc})" >&2
        printf '%s\n' "${output}" >&2
        exit 1
    fi
    mut_note "${label}" "accepted with the expected summary"
    MUT_PASS=$((MUT_PASS + 1))
    # This IS the unmutated baseline, so record it as such: mut_summary refuses
    # to report success for a harness that never showed one accepted (OC-54).
    MUT_BASELINE_OK=yes
}

# 2026-10-19: the landing of each mutation is asserted through mutation-lib.sh.
# Before this, a mutation that silently did not apply reported "did not fail as
# required", blaming run-all-checks for a broken harness. See mutation-lib.sh.
expect_inventory_failure() {
    label=$1; root=$2; pattern=$3
    mut_expect_fail "${label}" "--match=${pattern}" "${root}/cpp/selftest/run-all-checks.sh"
}

positive="${scratch}/positive"
make_case "${positive}"
expect_pass "complete inventory" "${positive}"

missing="${scratch}/missing"
make_case "${missing}"
mut_begin "deleted script" "${missing}/cpp/selftest"
rm "${missing}/cpp/selftest/regression-docs.sh"
expect_inventory_failure "deleted script" "${missing}" 'required script regression-docs.sh is missing'

extra="${scratch}/extra"
make_case "${extra}"
mut_begin "injected script" "${extra}/cpp/selftest"
printf '#!/bin/sh\nexit 0\n' > "${extra}/cpp/selftest/regression-injected.sh"
chmod +x "${extra}/cpp/selftest/regression-injected.sh"
expect_inventory_failure "injected script" "${extra}" 'unexpected script regression-injected.sh'

renamed="${scratch}/renamed"
make_case "${renamed}"
mut_begin "renamed script" "${renamed}/cpp/selftest"
mv "${renamed}/cpp/selftest/regression-docs.sh" "${renamed}/cpp/selftest/regression-docs-renamed.sh"
expect_inventory_failure "renamed script" "${renamed}" 'required script regression-docs.sh is missing'

duplicate="${scratch}/duplicate"
make_case "${duplicate}"
mut_begin "duplicate inventory entry" "${duplicate}/cpp/selftest/regression-script-inventory.txt"
printf '%s\n' 'regression-docs.sh' >> "${duplicate}/cpp/selftest/regression-script-inventory.txt"
expect_inventory_failure "duplicate inventory entry" "${duplicate}" 'duplicate entry regression-docs.sh'

mut_summary "harness-inventory-mutation-test"
