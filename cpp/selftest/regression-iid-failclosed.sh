#!/bin/bash
#
# Regression for the standards-valid upstream #153/#252 family.
#
# Every generated input contains exactly 1,000,000 samples.  For each declared
# width, a deterministic uniform-looking source has one 2,100-sample region
# duplicated.  This preserves ordinary chi-square margins while forcing a long
# repeat.  Before #153 was repaired the IID LRS calculation formed p_col^W and
# aborted when that value underflowed.  Before #252 was repaired a failed IID
# battery could still return success and expose a final entropy estimate.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
iid="${here}/../ea_iid"
restart="${here}/../ea_restart"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regiid-failclosed.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
note() { printf '%-61s %s\n' "$1" "$2"; }
[ -x "${iid}" ] || { echo "regression-iid-failclosed: ${iid} missing (run 'make iid')" >&2; exit 2; }
[ -x "${restart}" ] || { echo "regression-iid-failclosed: ${restart} missing (run 'make restart')" >&2; exit 2; }

python3 - "${work}" <<'PY'
from pathlib import Path
import random
import sys

out = Path(sys.argv[1])
for width in range(1, 9):
    rng = random.Random(153_000 + width)
    mask = (1 << width) - 1
    data = bytearray(rng.randrange(mask + 1) for _ in range(1_000_000))
    data[500_000:502_100] = data[0:2_100]
    (out / f"dup2100-w{width}.bin").write_bytes(data)

# This valid 1000 x 1000 restart matrix is deterministic and strongly
# dependent along both dimensions.
(out / "restart-checker.bin").write_bytes(bytes(
    ((index // 1000) + (index % 1000)) & 1
    for index in range(1_000_000)
))
PY

for width in 1 2 3 4 5 6 7 8; do
    input="${work}/dup2100-w${width}.bin"
    report="${work}/dup2100-w${width}.json"
    log="${work}/dup2100-w${width}.log"
    set +e
    "${iid}" -vvv -o "${report}" "${input}" "${width}" >"${log}" 2>&1
    rc=$?
    set -e

    if [ "${rc}" -ne 1 ]; then
        note "width ${width} failed IID suite returns status 1:" "got ${rc}"
        fails=$((fails + 1))
        continue
    fi

    if python3 - "${report}" "${log}" "${width}" <<'PY'
import json
import math
import re
import sys

report, log_path, width = sys.argv[1], sys.argv[2], int(sys.argv[3])
data = json.load(open(report, encoding="utf-8"))
_cs = (data)["testCases"]
assert len(_cs) == 1, "expected exactly 1 testCase, got %d" % len(_cs)
case = _cs[0]
text = open(log_path, encoding="utf-8").read()

if data.get("errorLevel") != 2:
    raise SystemExit("errorLevel is not 2")
if data.get("IID") is not False or data.get("assessmentComplete") is not True:
    raise SystemExit("IID rejection is not complete")
if data.get("bitsPerSymbol") != width or data.get("assessedSampleCount") != 1_000_000:
    raise SystemExit("width or sample count mismatch")
if len(data.get("sha256", "")) != 64 or data.get("sha256Scope") != "assessed-sample-bytes":
    raise SystemExit("assessed-byte identity is incomplete")
if "hAssessed" in case:
    raise SystemExit("failed IID run exposed hAssessed")
if not case.get("ranChiSquareTests") or not case.get("ranLongestRepeatedSubstringTest"):
    raise SystemExit("required #153 path was not executed")
if case.get("passedChiSquareTests") is not True:
    raise SystemExit("control did not pass chi-square tests")
if case.get("passedLongestRepeatedSubstringTest") is not False:
    raise SystemExit("LRS did not reject")
if case.get("ranIidPermutationTests") is not False:
    raise SystemExit("permutation suite was not skipped after decisive rejection")

p_match = re.search(r"P_col = ([0-9.eE+-]+)", text)
w_match = re.search(r"W = ([0-9]+)", text)
if not p_match or not w_match:
    raise SystemExit("missing LRS evidence")
p_col, repeat = float(p_match.group(1)), int(w_match.group(1))
if repeat < 2_100:
    raise SystemExit("forced repeat was not observed")

# Independent SP 800-90B 5.2.5 decision calculation.  Comparing logarithms
# avoids the underflow that caused #153.  Rejection requires Pr(X >= 1) < .001.
substrings = 1_000_000 - repeat + 1
pairs = substrings * (substrings - 1) // 2
log_expected_collisions = math.log(pairs) + repeat * math.log(p_col)
if not log_expected_collisions < math.log(-math.log(0.999)):
    raise SystemExit("independent LRS oracle did not reject")
PY
    then
        note "width ${width}, 1M samples, #153/#252 rejection:" "PASS"
    else
        note "width ${width}, 1M samples, #153/#252 rejection:" "FAIL"
        tail -8 "${log}" | sed 's/^/    /'
        fails=$((fails + 1))
    fi
done

set +e
"${restart}" -i -q -o "${work}/restart.json" "${work}/restart-checker.bin" 0.8 >/dev/null 2>&1
restart_rc=$?
set -e
if [ "${restart_rc}" -eq 1 ] && python3 - "${work}/restart.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
_cs = (d)["testCases"]
assert len(_cs) == 1, "expected exactly 1 testCase, got %d" % len(_cs)
t = _cs[0]
ok = (
    d.get("errorLevel") == 2
    and d.get("IID") is False
    and d.get("assessmentComplete") is True
    and d.get("assessedSampleCount") == 1_000_000
    and "h_i" not in t and "h_r" not in t and "h_c" not in t
)
raise SystemExit(0 if ok else 1)
PY
then
    note "IID restart failure returns no entropy award:" "PASS"
else
    note "IID restart failure returns no entropy award:" "FAIL (status ${restart_rc})"
    fails=$((fails + 1))
fi

# Positive controls: the reviewed million-sample binary and nonbinary fixtures
# must still complete a passing IID battery and expose a finite final estimate.
for control in truerand_1bit:1 truerand_8bit:8; do
    name=${control%:*}
    width=${control#*:}
    report="${work}/${name}.json"
    set +e
    "${iid}" -q -o "${report}" "${repo}/bin/${name}.bin" "${width}" >/dev/null 2>&1
    rc=$?
    set -e
    if [ "${rc}" -eq 0 ] && python3 - "${report}" <<'PY'
import json, math, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
_cs = (d)["testCases"]
assert len(_cs) == 1, "expected exactly 1 testCase, got %d" % len(_cs)
t = _cs[0]
h = t.get("hAssessed")
ok = (
    d.get("errorLevel") == 0
    and d.get("IID") is True
    and d.get("assessmentComplete") is True
    and d.get("assessedSampleCount") == 1_000_000
    and t.get("ranChiSquareTests") is True
    and t.get("ranLongestRepeatedSubstringTest") is True
    and t.get("ranIidPermutationTests") is True
    and isinstance(h, (int, float)) and math.isfinite(h) and h >= 0
)
raise SystemExit(0 if ok else 1)
PY
    then
        note "positive ${name}, 1M samples:" "PASS"
    else
        note "positive ${name}, 1M samples:" "FAIL (status ${rc})"
        fails=$((fails + 1))
    fi
done

echo
if [ "${fails}" -eq 0 ]; then
    echo "regression-iid-failclosed: PASS"
    exit 0
fi
echo "regression-iid-failclosed: FAIL (${fails} checks)"
exit 1
