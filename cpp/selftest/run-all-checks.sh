#!/bin/bash
#
# Run every check in this directory and report one summary.
#
# The scripts are DISCOVERED, not listed. That is deliberate: a
# hand-maintained list in a document drifted out of date twice, and anyone
# following it ran half the suite believing they had run all of it. Adding a
# regression-*.sh file here is enough to get it run.
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
    only_known=1
    for f in $(printf '%s' "${line}" | sed 's/^.*files)://'); do
        case " ${KNOWN_PLATFORM_FILES} " in *" ${f} "*) ;; *) only_known=0 ;; esac
    done
    if [ "${only_known}" -eq 1 ] && [ "${allow_platform}" -eq 1 ]; then
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
echo "regression scripts (discovered)"
found=0
for s in ./regression-*.sh; do
    [ -e "${s}" ] || continue
    found=$((found + 1))
    run "$(basename "${s}" .sh)" "${s}"
done
[ "${found}" -eq 0 ] && { echo "  none found — that is itself wrong" >&2; fail=$((fail + 1)); }

echo
echo "run-all-checks: ${pass} passed, ${fail} failed (${found} regression scripts discovered)"
[ "${fail}" -eq 0 ] && exit 0
echo "failed:${failed}"
exit 1
