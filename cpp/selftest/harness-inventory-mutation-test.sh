#!/bin/bash
# Standalone mutation controls for run-all-checks.sh's own script inventory.
# Uses inert local stubs so it tests coverage accounting without rerunning the
# expensive estimators.  It does not use the TruePad wrapper.

set -u

here=$(cd "$(dirname "$0")" && pwd)
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

expect_pass() {
    label=$1; root=$2
    output=$("${root}/cpp/selftest/run-all-checks.sh" 2>&1); rc=$?
    if [ "${rc}" -ne 0 ] || ! printf '%s\n' "${output}" | grep -q 'run-all-checks: 19 passed, 0 failed (17 regression scripts discovered)'; then
        echo "harness-inventory-mutation-test: ${label} positive control failed (exit ${rc})" >&2
        printf '%s\n' "${output}" >&2
        exit 1
    fi
}

expect_inventory_failure() {
    label=$1; root=$2; pattern=$3
    output=$("${root}/cpp/selftest/run-all-checks.sh" 2>&1); rc=$?
    if [ "${rc}" -eq 0 ] || ! printf '%s\n' "${output}" | grep -q "${pattern}"; then
        echo "harness-inventory-mutation-test: ${label} did not fail as required (exit ${rc})" >&2
        printf '%s\n' "${output}" >&2
        exit 1
    fi
}

positive="${scratch}/positive"
make_case "${positive}"
expect_pass "complete inventory" "${positive}"

missing="${scratch}/missing"
make_case "${missing}"
rm "${missing}/cpp/selftest/regression-docs.sh"
expect_inventory_failure "deleted script" "${missing}" 'required script regression-docs.sh is missing'

extra="${scratch}/extra"
make_case "${extra}"
printf '#!/bin/sh\nexit 0\n' > "${extra}/cpp/selftest/regression-injected.sh"
chmod +x "${extra}/cpp/selftest/regression-injected.sh"
expect_inventory_failure "injected script" "${extra}" 'unexpected script regression-injected.sh'

renamed="${scratch}/renamed"
make_case "${renamed}"
mv "${renamed}/cpp/selftest/regression-docs.sh" "${renamed}/cpp/selftest/regression-docs-renamed.sh"
expect_inventory_failure "renamed script" "${renamed}" 'required script regression-docs.sh is missing'

duplicate="${scratch}/duplicate"
make_case "${duplicate}"
printf '%s\n' 'regression-docs.sh' >> "${duplicate}/cpp/selftest/regression-script-inventory.txt"
expect_inventory_failure "duplicate inventory entry" "${duplicate}" 'duplicate entry regression-docs.sh'

echo "harness-inventory-mutation-test: PASS (complete, deletion, injection, rename, duplicate controls)"
