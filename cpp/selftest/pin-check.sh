#!/usr/bin/env bash
# pin-check.sh -- assert the min-entropy that ea_non_iid reports for a
# committed sample of real captured noise.
#
#   ./pin-check.sh [path/to/ea_non_iid]          # default: ../ea_non_iid
#   ./pin-check.sh --prove-nonvacuous [binary]   # also perturb the sample
#                                                # and require a FAIL
#
# Sample:    bin/ringOsc-nist.bin (1,000,000 one-bit samples; upstream
#            file, unchanged, SHA-256 checked below). Its estimates
#            (MCV 0.99, collision 0.126) show heavy serial correlation,
#            which no CSPRNG stream exhibits.
# Expected:  the value in upstream's own reference output,
#            cpp/selftest/refdata/ringOsc-nist.res (Linux x86-64, GCC).
# Tolerance: relative 1e-9. Justification: upstream's selftest accepts
#            1e-10 per estimator; the largest cross-platform delta seen
#            on any estimator is ~3.7e-10 (macOS arm64, this fork) and
#            ~3.2e-10 (Windows 10, upstream issue #155). The overall
#            figure on this sample differs by 4.4e-14 between platforms.
#            A real change to the estimator or input moves the figure by
#            >= 1e-5, four orders of magnitude above the tolerance.
#            Exact per-platform values are recorded in BUILDING.md.
set -u
cd "$(dirname "$0")"

PROVE=0
if [ "${1:-}" = "--prove-nonvacuous" ]; then PROVE=1; shift; fi
BIN=${1:-../ea_non_iid}
SAMPLE=../../bin/ringOsc-nist.bin
SAMPLE_SHA256=7d37dc3795e9b2927beb779008d7f4b4630dd7f2c058a2b14cee9d41a658dd68
EXPECTED=0.12644573619605429
RELTOL=1e-9

if [ ! -x "$BIN" ]; then echo "pin-check: no executable at $BIN" >&2; exit 2; fi
if [ ! -f "$SAMPLE" ]; then echo "pin-check: sample $SAMPLE missing" >&2; exit 2; fi

# Run the tool exactly as upstream's selftest does (-vv prints the
# assessed figure with 17 significant digits and the input's SHA-256).
run_tool() {
    "$BIN" -vv "$1" 2>/dev/null
}

check() {  # $1 = output text, $2 = label; prints verdict; returns 0 on pass
    local out=$1 label=$2 sha got
    sha=$(printf '%s\n' "$out" | sed -n 's/.*SHA-256 hash \([0-9a-f]\{64\}\).*/\1/p' | head -1)
    got=$(printf '%s\n' "$out" | sed -n 's/^Assessed min entropy: //p' | head -1)
    if [ -z "$got" ]; then
        echo "$label: FAIL (no 'Assessed min entropy' line in output)"
        return 1
    fi
    awk -v a="$EXPECTED" -v b="$got" -v tol="$RELTOL" -v sha="$sha" -v want="$SAMPLE_SHA256" -v label="$label" -v plat="$(uname -sm)" '
    BEGIN {
        d = a - b; if (d < 0) d = -d
        m = (a > b) ? a : b; if (m < 0) m = -m
        rel = (m > 0) ? d / m : 0
        printf "%s: platform=%s expected=%s got=%s reldelta=%.3g tol=%s\n", label, plat, a, b, rel, tol
        ok = (rel < tol)
        if (label == "sample" && sha != want) { printf "%s: FAIL sample SHA-256 %s != %s\n", label, sha, want; ok = 0 }
        if (ok) { printf "%s: PASS\n", label; exit 0 } else { printf "%s: FAIL\n", label; exit 1 }
    }'
}

status=0
check "$(run_tool "$SAMPLE")" sample || status=1

if [ $PROVE -eq 1 ]; then
    # Perturbation that is known to move the figure (~7e-5 relative):
    # zero a 64-byte block in the middle of the sample. (Note: flipping a
    # single bit often leaves the collision estimate, which is the minimum
    # on this sample, unchanged, so a bigger perturbation is used.)
    tmp=$(mktemp "${TMPDIR:-/tmp}/pin-check.XXXXXX") || exit 2
    cp "$SAMPLE" "$tmp"
    dd if=/dev/zero of="$tmp" bs=1 seek=500000 count=64 conv=notrunc 2>/dev/null
    if check "$(run_tool "$tmp")" perturbed; then
        echo "perturbed: ERROR -- perturbed sample still passes; the pin is vacuous"
        status=1
    else
        echo "perturbed: expected FAIL observed (check is not vacuous)"
    fi
    rm -f "$tmp"
fi

exit $status
