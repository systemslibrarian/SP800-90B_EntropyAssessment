#!/bin/bash
#
# Regression for A06 (outside read-only audit, 2026-10-20).
#
# --allow-known-platform-deltas used to excuse any mismatch whose FILENAME was
# one of two names, inspecting neither the estimator, the field, the magnitude,
# the direction nor the platform. An isolated controller fed it a deliberate
# change from 0.85 to 0.01 in one of those files and it was ACCEPTED. A guard
# that cannot tell a 1e-10 last-digit platform difference from a 0.84 collapse
# is not guarding.
#
# The exception is now an expected-result manifest (known-platform-deltas.txt)
# checked by check-platform-deltas.py. This holds the four failures the audit
# requires, each WITH THE FLAG ENABLED, plus the positive control.
#
# The negatives are built by MUTATING a genuine selftest transcript one field
# at a time (rule 7), and the unmutated transcript is asserted ACCEPTED FIRST,
# so a refusal here is attributable to the one thing that changed.

set -u
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-platdelta.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM
fails=0
CC_ID="$(${CXX:-c++} --version 2>&1 | head -1)"

check() { # check <transcript> [uname-s] [uname-m] [cc]
    SELFTEST_DELTA_MANIFEST="${here}/known-platform-deltas.txt" \
    PLAT_S="${2:-$(uname -s)}" PLAT_M="${3:-$(uname -m)}" PLAT_CC="${4:-${CC_ID}}" \
    python3 "${here}/check-platform-deltas.py" < "$1" > "${work}/out" 2>&1
    return $?
}
expect() { # expect <label> <0|1> <must-appear> <transcript> [plat...]
    local label=$1 want=$2 frag=$3; shift 3
    check "$@"; local rc=$?
    if [ "${rc}" != "${want}" ]; then
        printf '  %-50s FAIL  rc %s, wanted %s\n' "${label}" "${rc}" "${want}"
        sed 's/^/        /' "${work}/out"; fails=$((fails + 1)); return
    fi
    if [ -n "${frag}" ] && ! grep -qF "${frag}" "${work}/out"; then
        printf '  %-50s FAIL  right verdict, wrong reason\n' "${label}"
        printf '        wanted a mention of: %s\n' "${frag}"
        sed 's/^/        /' "${work}/out"; fails=$((fails + 1)); return
    fi
    printf '  %-50s PASS\n' "${label}"
}

# A genuine transcript. selftest is slow, so reuse a cached one if the caller
# has it; otherwise produce one.
genuine="${work}/genuine.out"
if [ -n "${REGRESSION_SELFTEST_TRANSCRIPT:-}" ] && [ -s "${REGRESSION_SELFTEST_TRANSCRIPT}" ]; then
    cp "${REGRESSION_SELFTEST_TRANSCRIPT}" "${genuine}"
else
    ( cd "${here}" && ./selftest > "${genuine}" 2>&1; rm -f ./*.res )
fi
if ! grep -q 'Significant difference for' "${genuine}"; then
    echo "regression-platform-deltas: this platform reports no differences at all, so the"
    echo "  exception is never exercised here. SKIPPED (not a pass): the manifest cannot be"
    echo "  checked against a transcript that has nothing in it."
    exit 0
fi

# THE BASELINE FIRST (rule 7): the unmutated transcript must be ACCEPTED.
expect "baseline: the genuine transcript is accepted" 0 "within tolerance" "${genuine}" || true
if ! check "${genuine}"; then
    echo "  regression-platform-deltas: the baseline was REFUSED, so every negative below is" >&2
    echo "  unattributable. Either the manifest is stale for this host or the transcript is" >&2
    echo "  not this host's. Nothing is concluded." >&2
    exit 1
fi

# 1. a large change in a named file
sed 's/delta: 1.5468587521994e-10/delta: 0.84/' "${genuine}" > "${work}/big.out"
expect "1. a LARGE delta in a named file fails" 1 "delta TOO LARGE" "${work}/big.out"

# 2. an unexpected estimator in a named file
sed 's/Literal MultiMCW Prediction Estimate: min entropy/Literal Compression Estimate: min entropy/' \
    "${genuine}" > "${work}/unexp.out"
expect "2. an UNEXPECTED estimator fails" 1 "UNEXPECTED difference" "${work}/unexp.out"

# 3. a listed comparison that stops being reported
grep -v "Literal Lag Prediction Estimate: P_local" "${genuine}" > "${work}/miss.out"
expect "3. a MISSING comparison fails" 1 "MISSING comparison" "${work}/miss.out"

# 4. the wrong platform, with the flag enabled
expect "4. the WRONG PLATFORM fails" 1 "no manifest block matches" \
       "${genuine}" Linux x86_64 "g++ (Ubuntu 13.3.0)"

# and a manifest that cannot be read must refuse, not wave through
SELFTEST_DELTA_MANIFEST="${work}/nope.txt" PLAT_S="$(uname -s)" PLAT_M="$(uname -m)" \
    PLAT_CC="${CC_ID}" python3 "${here}/check-platform-deltas.py" < "${genuine}" >/dev/null 2>&1
[ $? -eq 2 ] && printf '  %-50s PASS\n' "5. an unreadable manifest refuses (rc 2)" \
             || { printf '  %-50s FAIL\n' "5. an unreadable manifest refuses (rc 2)"; fails=$((fails + 1)); }

if [ "${fails}" -eq 0 ]; then echo "regression-platform-deltas: PASS"; exit 0; fi
echo "regression-platform-deltas: FAIL (${fails} case(s))"; exit 1
