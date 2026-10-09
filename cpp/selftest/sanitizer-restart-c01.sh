#!/bin/bash

# C-01 focused sanitizer control. Run after building ea_restart with
# AddressSanitizer and UndefinedBehaviorSanitizer; the input is the exact
# 1,000 x 1,000 restart dimension required by SP 800-90B Section 3.1.4.

set -u

here=$(cd "$(dirname "$0")" && pwd)
tool=${EA_RESTART_SANITIZER_BIN:-"$here/../ea_restart"}
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-c01.XXXXXX") || exit 2
trap 'rm -rf "$work"' EXIT HUP INT TERM

[ -x "$tool" ] || { echo "sanitizer-restart-c01: missing executable $tool" >&2; exit 2; }

python3 - "$work/restart.bin" <<'PY'
import random, sys
rng = random.Random(0xC01)
with open(sys.argv[1], "wb") as out:
    out.write(bytes(rng.getrandbits(1) for _ in range(1_000_000)))
PY

ASAN_OPTIONS=${ASAN_OPTIONS:-halt_on_error=1:abort_on_error=1} \
UBSAN_OPTIONS=${UBSAN_OPTIONS:-halt_on_error=1:print_stacktrace=1} \
    "$tool" -n -q -o "$work/result.json" "$work/restart.bin" 1 0.8
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "sanitizer-restart-c01: FAIL (exit $rc)" >&2
    exit "$rc"
fi

python3 - "$work/result.json" <<'PY'
import json, math, sys
doc = json.load(open(sys.argv[1]))
assert doc["errorLevel"] == 0
overall = next(case for case in doc["testCases"] if case.get("testCaseDesc") == "Overall")
for key in ("h_r", "h_c", "h_i"):
    assert isinstance(overall[key], (int, float)) and math.isfinite(overall[key])
assert abs(overall["h_i"] - 0.8) <= 1e-12
PY

echo "sanitizer-restart-c01: PASS"
