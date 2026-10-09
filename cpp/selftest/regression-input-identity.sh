#!/bin/bash

# N-07 deterministic pathname-replacement regression. A test-only build stops
# after loading and hashing the assessment bytes. The pathname is then replaced
# before the estimator resumes. The result must remain bound to snapshot A,
# while the pathname names B. Production builds contain no synchronization hook.

set -u

here=$(cd "$(dirname "$0")" && pwd)
cpp=$(cd "$here/.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regidentity.XXXXXX") || exit 2
tool="$cpp/ea_non_iid_identity_test"
pid=
cleanup() {
    if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then kill -KILL "$pid" >/dev/null 2>&1 || true; fi
    rm -f "$tool"
    rm -rf "$work"
}
trap cleanup EXIT HUP INT TERM

make -C "$cpp" non_iid_identity_test >/dev/null || exit 2
python3 - "$work/a.bin" "$work/b.bin" <<'PY'
import sys
n = 1_000_000
open(sys.argv[1], "wb").write(bytes(i & 1 for i in range(n)))
open(sys.argv[2], "wb").write(bytes((i // 17) & 1 for i in range(n)))
PY

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}

a_hash=$(hash_file "$work/a.bin")
b_hash=$(hash_file "$work/b.bin")
cp "$work/a.bin" "$work/input.bin"

EA_TEST_INPUT_IDENTITY_MARKER="$work/loaded.marker" \
    "$tool" -q -o "$work/result.json" "$work/input.bin" 1 >"$work/tool.log" 2>&1 &
pid=$!

waited=0
while [ ! -f "$work/loaded.marker" ] && kill -0 "$pid" >/dev/null 2>&1; do
    sleep 1
    waited=$((waited + 1))
    [ "$waited" -lt 30 ] || { echo "regression-input-identity: marker timeout" >&2; exit 1; }
done
[ -f "$work/loaded.marker" ] || { echo "regression-input-identity: tool exited before snapshot marker" >&2; exit 1; }

mv "$work/b.bin" "$work/input.bin"
kill -CONT "$pid"
wait "$pid"
rc=$?
pid=
[ "$rc" -eq 0 ] || { echo "regression-input-identity: assessment exited $rc" >&2; cat "$work/tool.log" >&2; exit 1; }

python3 - "$work/result.json" "$a_hash" "$b_hash" "$(hash_file "$work/input.bin")" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
assert sys.argv[2] != sys.argv[3]
assert sys.argv[3] == sys.argv[4]
assert doc["sha256"] == sys.argv[2]
assert doc["sha256Scope"] == "assessed-sample-bytes"
assert doc["assessedSampleCount"] == 1_000_000
overall = next(case for case in doc["testCases"] if case.get("testCaseDesc") == "Overall")
assert overall["hAssessed"] == 0
PY

echo "regression-input-identity: PASS (replacement rejected as result identity; assessed snapshot retained)"
