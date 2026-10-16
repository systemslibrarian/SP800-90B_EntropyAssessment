#!/bin/bash

set -eu

repo=$(cd "$(dirname "$0")/../.." && pwd)
cd "$repo"

expected_commit=ea87f1e1321594a421b949c855bf4e59da0a72c5
expected_tree=f1b97935a6a6e0eea91fa15e4a1c65100ddb6789
expected_repository=https://github.com/systemslibrarian/SP800-90B_EntropyAssessment.git

test "$(git rev-parse HEAD)" = "$expected_commit"
test "$(git rev-parse 'HEAD^{tree}')" = "$expected_tree"
test "$(git remote get-url origin)" = "$expected_repository"
git diff --quiet --
git diff --cached --quiet --

cpp/selftest/harness-inventory-mutation-test.sh

set +e
bash cpp/selftest/run-all-checks.sh
strict_status=$?
set -e
if [ "$(uname -s)/$(uname -m)" = "Darwin/arm64" ]; then
  test "$strict_status" -eq 1
else
  test "$strict_status" -eq 0
fi

bash cpp/selftest/run-all-checks.sh --allow-known-platform-deltas

scratch=$(mktemp -d "${TMPDIR:-/tmp}/sp80090b-ind02-rerun.XXXXXX")
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
python3 - "$scratch/period-two.bin" <<'PY'
import sys
with open(sys.argv[1], "wb") as f:
    f.write(bytes(i & 1 for i in range(1_000_000)))
PY

set +e
cpp/ea_iid -i -q -o "$scratch/period-two.json" "$scratch/period-two.bin" 1
period_status=$?
set -e
test "$period_status" -eq 1
python3 - "$scratch/period-two.json" <<'PY'
import json, sys
x = json.load(open(sys.argv[1], encoding="utf-8"))
case = x["testCases"][0]
assert x["errorLevel"] == 2
assert x["IID"] is False
assert x["assessmentComplete"] is True
assert "hAssessed" not in case
assert case["passedLongestRepeatedSubstringTest"] is False
assert x["assessedSampleCount"] == 1_000_000
PY

echo "IND-02 repair rerun: PASS"
