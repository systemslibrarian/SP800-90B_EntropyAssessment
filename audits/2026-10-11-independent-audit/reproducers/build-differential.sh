#!/bin/bash
# Build-differential validation (REPAIR-STRATEGY route 4): the same input through
# an asserts-live ea_iid and a -DNDEBUG ea_iid must give the SAME answer. No
# reference corpus is consulted; agreement between the two builds is the check.
#
#   build-differential.sh <ea_iid asserts-live> <ea_iid -DNDEBUG> [W ...]
#
# Inputs are generated from the audit's fixed seed (generators/c07_lrs_fixtures.py
# site B, and tools/build-provenance-canary.sh for W=20000): a 1,000,000-bit
# stream with a repeated block of length W implanted, so the longest repeated
# substring is >= W. These are inputs whose correct verdict is known BY
# CONSTRUCTION (route 2): a 20,000-bit exact repeat is astronomically improbable
# under IID, so the only correct outcome is a refused IID figure.
#
# PASS requires, for every W:  identical exit code, identical "** Failed" /
# "** Passed" lines, identical JSON after dropping run-specific fields, and
# NO hAssessed in either JSON.  Exit 0 only then.
set -u
LIVE=$1; NDEBUG=$2; shift 2
WS=${*:-"2000 20000"}
PROG=build-differential
work=$(mktemp -d "${TMPDIR:-/tmp}/${PROG}.XXXXXX") || exit 2
trap 'rm -rf "$work"' EXIT HUP INT TERM
fails=0

norm_json() {  # drop fields that legitimately differ between runs/builds
    python3 - "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for k in ("dateTimeStamp", "filename", "sha256", "toolVersion", "commandline"):
    d.pop(k, None)
print(json.dumps(d, sort_keys=True, indent=1))
PY
}

for W in $WS; do
    IN="$work/lrsrep-$W.bin"
    python3 - "$IN" "$W" <<'PY'
import random, sys, hashlib
r = random.Random(0x90B2026C07)
b = bytearray(r.getrandbits(1) for _ in range(1000000))
W = int(sys.argv[2])
b[600000:600000 + W] = bytes(b[1000:1000 + W])
d = bytes(b)
open(sys.argv[1], 'wb').write(d)
print("input W=%d sha256 %s" % (W, hashlib.sha256(d).hexdigest()))
PY
    for tag in live ndebug; do
        bin=$LIVE; [ "$tag" = ndebug ] && bin=$NDEBUG
        rm -f "$work/$tag.json"
        OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} "$bin" -i -v -o "$work/$tag.json" "$IN" 1 >"$work/$tag.out" 2>&1
        echo $? >"$work/$tag.rc"
    done
    rc_l=$(cat "$work/live.rc"); rc_n=$(cat "$work/ndebug.rc")
    echo "W=$W  exit: asserts-live=$rc_l  ndebug=$rc_n"
    grep -hE '^\*\* (Failed|Passed)|IID test suite|Assertion failed|hAssessed|min-entropy' "$work/live.out" | sed 's/^/  live:   /'
    grep -hE '^\*\* (Failed|Passed)|IID test suite|Assertion failed|hAssessed|min-entropy' "$work/ndebug.out" | sed 's/^/  ndebug: /'
    ok=1
    [ "$rc_l" = "$rc_n" ] || { echo "  DIVERGE: exit codes differ"; ok=0; }
    if ! diff <(grep -E '^\*\* (Failed|Passed)' "$work/live.out") <(grep -E '^\*\* (Failed|Passed)' "$work/ndebug.out") >/dev/null; then
        echo "  DIVERGE: per-test verdict lines differ"; ok=0
    fi
    for tag in live ndebug; do
        if [ -s "$work/$tag.json" ]; then
            if grep -q hAssessed "$work/$tag.json"; then echo "  FAIL: $tag published hAssessed on a known-non-IID input"; ok=0; fi
            norm_json "$work/$tag.json" >"$work/$tag.norm" 2>/dev/null || echo '{}' >"$work/$tag.norm"
        else
            echo "(no json)" >"$work/$tag.norm"
        fi
    done
    if ! diff "$work/live.norm" "$work/ndebug.norm" >/dev/null; then
        echo "  DIVERGE: JSON differs after normalisation"; diff "$work/live.norm" "$work/ndebug.norm" | head -20 | sed 's/^/    /'; ok=0
    fi
    [ "$ok" -eq 1 ] && echo "  AGREE: both builds refuse identically" || fails=$((fails + 1))
done
if [ "$fails" -eq 0 ]; then echo "$PROG: PASS"; exit 0; fi
echo "$PROG: FAIL ($fails input(s) diverged or published a figure)"; exit 1
