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

KNOWN_PLATFORM_FILES="biased-random-bytes.bin ringOsc-nist.bin"
REGRESSION_INVENTORY="regression-script-inventory.txt"
EXPECTED_REGRESSION_SCRIPTS=17
EXPECTED_TOTAL_CHECKS=19

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
run() { # run <label> <command...>
    local label=$1; shift
    local out rc
    out=$("$@" 2>&1); rc=$?
    if [ "${rc}" -eq 0 ]; then
        printf '  %-34s PASS\n' "${label}"
        pass=$((pass + 1))
        return
    fi
    printf '  %-34s FAIL (exit %s)\n' "${label}" "${rc}"
    printf '%s\n' "${out}" | tail -4 | sed 's/^/        /'
    fail=$((fail + 1)); failed="${failed} ${label}"
}

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
    only_known=1
    nfiles=0
    for f in ${files}; do
        nfiles=$((nfiles + 1))
        case " ${KNOWN_PLATFORM_FILES} " in *" ${f} "*) ;; *) only_known=0 ;; esac
    done
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
    elif [ "${only_known}" -eq 1 ] && [ "${allow_platform}" -eq 1 ]; then
        printf '  %-34s PASS (only the known upstream #155 platform files)\n' "selftest"
        pass=$((pass + 1))
    else
        printf '  %-34s FAIL\n' "selftest"
        printf '        %s\n' "${line}"
        [ "${only_known}" -eq 1 ] && printf '        these are the known upstream #155 platform files; --allow-known-platform-deltas accepts exactly these\n'
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

total=$((pass + fail))
if [ "${total}" -ne "${EXPECTED_TOTAL_CHECKS}" ]; then
    echo "run-all-checks: executed ${total} total checks; expected ${EXPECTED_TOTAL_CHECKS}" >&2
    fail=$((fail + 1)); failed="${failed} total-check-count"
fi

echo
echo "run-all-checks: ${pass} passed, ${fail} failed (${found} regression scripts discovered)"
[ "${fail}" -eq 0 ] && exit 0
echo "failed:${failed}"
exit 1
