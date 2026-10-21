#!/bin/bash
#
# Regression for NOVEL-02, N-10, and the verbosity coupling in the same block.
#
#   NOVEL-02  H_original and H_bitstring are initialised to data.word_size and
#             1.0 so the final min() is well defined whichever branch runs.
#             Both were copied into the report unconditionally, so a binary -i
#             run reported "hBitstring": 1.0 and a -c run reported
#             "hOriginal": <word size>, neither of which any estimator had
#             produced.
#
#   The assessed figure itself was computed only inside the "verbose > 2"
#   branch, so at any lower verbosity the report carried data.word_size. For
#   binary input under -i that is 1.0 against a correct 0.995: too high, which
#   is the dangerous direction. Upstream PR #251 addresses the same coupling
#   and is open and untouched.
#
#   N-10      The permutation tests use a median of translated symbol indices,
#             but stdout and JSON called it only "Median". JSON must name the
#             raw-value mean and translated-index median explicitly.

set -u

here=$(cd "$(dirname "$0")" && pwd)
# instrument rule 5, mechanised (OC-73)
. "${here}/labelread-lib.sh"
repo=$(cd "${here}/../.." && pwd)
tool="${here}/../ea_iid"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regij.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
note() { printf '%-54s %s\n' "$1" "$2"; }
[ -x "${tool}" ] || { echo "regression-iid-json: ${tool} missing (run 'make iid')" >&2; exit 2; }

# field <json> <name>  -> prints the value or "absent"
field() { python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
cs=d.get('testCases') or []
# An ea_iid report has exactly one test case. Assert it rather than taking the
# first of however many there are (OC-36's label rule: a positional read is
# checked where no label exists to anchor to).
assert len(cs)==1, 'expected exactly 1 testCase, got %d' % len(cs)
d=cs[0]
print(d.get(sys.argv[2], 'absent'))" "$1" "$2"; }

# Binary input under -i: no bitstring assessment is made, so hBitstring must
# be absent rather than the 1.0 initialiser.
"${tool}" -q -o "${work}/bin.json" "${repo}/bin/truerand_1bit.bin" 1 >/dev/null 2>&1
got=$(field "${work}/bin.json" hBitstring)
if [ "${got}" = "absent" ]; then
	note "binary -i omits hBitstring:" "absent"
else
	note "binary -i omits hBitstring:" "reported ${got}"
	fails=$((fails + 1))
fi

if python3 - "${work}/bin.json" <<'PY'
import json, sys
_d = json.load(open(sys.argv[1]))
_cs = _d.get("testCases") or []
assert len(_cs) == 1, "expected exactly 1 testCase, got %d" % len(_cs)
tc = _cs[0]
ok = ("rawMean" in tc and "translatedSymbolMedian" in tc
      and "mean" not in tc and "median" not in tc)
sys.exit(0 if ok else 1)
PY
then
	note "N-10 JSON uses explicit statistic names:" "rawMean and translatedSymbolMedian"
else
	note "N-10 JSON uses explicit statistic names:" "ambiguous or missing fields"
	fails=$((fails + 1))
fi

# Conditioned input: no literal assessment is made, so hOriginal must be
# absent. Use a standards-sized deterministic dependent input so it fails an
# early IID prerequisite instead of stochastically entering the very expensive
# 8,000,000-bit permutation battery.
python3 -c "open('$work/cond-dependent.bin','wb').write(bytes((0 if i & 1 else 255) for i in range(1000000)))"
"${tool}" -c -q -o "${work}/cond.json" "${work}/cond-dependent.bin" 8 >/dev/null 2>&1
got=$(field "${work}/cond.json" hOriginal)
if [ "${got}" = "absent" ]; then
	note "-c omits hOriginal:" "absent"
else
	note "-c omits hOriginal:" "reported ${got}"
	fails=$((fails + 1))
fi

# The assessed figure in the report must be the real one at any verbosity,
# and must equal what -vvv prints.
text=$("${tool}" -vvv "${repo}/bin/truerand_1bit.bin" 1 2>/dev/null \
	| tee "${work}/bin-vvv.txt" | sed -n 's/^Assessed min entropy: //p' | lr_one 'Assessed min entropy') || exit 1
json=$(field "${work}/bin.json" hAssessed)
if [ -n "${text}" ] && python3 -c "
import sys
t, j = float(sys.argv[1]), float(sys.argv[2])
sys.exit(0 if abs(t - j) <= 1e-12 * max(1.0, abs(t)) else 1)" "${text}" "${json}"; then
	note "hAssessed at -q matches the -vvv figure:" "${json}"
else
	note "hAssessed at -q matches the -vvv figure:" "json ${json} vs text ${text}"
	fails=$((fails + 1))
fi

# ABSENCE RULE (OC-36): the second clause below concludes from a MISSING line,
# so the output must first be shown to be a well-formed -vvv report. A usage
# message, an empty file and a crash all lack a bare "Median" line too, and
# without this check each would read as the repair being present.
if ! grep -qE '^Assessed min entropy:' "${work}/bin-vvv.txt"; then
	note "N-10 stdout labels the translated median:" "NOT A WELL-FORMED REPORT (no 'Assessed min entropy' line); nothing was concluded"
	fails=$((fails + 1))
elif grep -qE 'Translated Symbol Index Median(:| =)' "${work}/bin-vvv.txt" && \
   ! grep -qE '^[[:space:]]*Median(:| =)' "${work}/bin-vvv.txt"; then
	note "N-10 stdout labels the translated median:" "explicit"
else
	note "N-10 stdout labels the translated median:" "still says only Median"
	fails=$((fails + 1))
fi

# Positive semantic control: this sparse raw alphabet has raw mean 127.5 but
# translated indices 0 and 1, whose Section 5 median is 0.5. It is deliberately
# dependent so the valid one-million-sample run stops before permutations.
"${tool}" -i -v "${work}/cond-dependent.bin" 8 >"${work}/sparse.txt" 2>&1
if grep -q 'Raw Mean: 127.500000' "${work}/sparse.txt" && \
   grep -q 'Translated Symbol Index Median: 0.500000' "${work}/sparse.txt"; then
	note "N-10 sparse-alphabet domains are distinguishable:" "raw 127.5, translated 0.5"
else
	note "N-10 sparse-alphabet domains are distinguishable:" "labels or values wrong"
	fails=$((fails + 1))
fi

# And it must not be the word size placeholder.
if [ "${json}" = "1.0" ] || [ "${json}" = "1" ]; then
	note "hAssessed is not the word-size placeholder:" "still 1.0"
	fails=$((fails + 1))
else
	note "hAssessed is not the word-size placeholder:" "ok"
fi

# The values that ARE computed must still be present.
for pair in "bin.json:hOriginal" "cond.json:hBitstring"; do
	f=${pair%%:*}; k=${pair#*:}
	got=$(field "${work}/${f}" "${k}")
	if [ "${got}" != "absent" ]; then
		note "${f} still reports ${k}:" "${got}"
	else
		note "${f} still reports ${k}:" "absent"
		fails=$((fails + 1))
	fi
done

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-iid-json: PASS"
	exit 0
fi
echo "regression-iid-json: FAIL (${fails} checks)"
exit 1
