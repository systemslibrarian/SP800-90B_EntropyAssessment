#!/bin/bash
#
# Regression for NOVEL-02 and the verbosity coupling in the same block.
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

set -u

here=$(cd "$(dirname "$0")" && pwd)
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
d=json.load(open(sys.argv[1]))['testCases'][0]
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

# Conditioned input: no literal assessment is made, so hOriginal must be absent.
"${tool}" -c -q -o "${work}/cond.json" "${repo}/bin/truerand_8bit.bin" 8 >/dev/null 2>&1
got=$(field "${work}/cond.json" hOriginal)
if [ "${got}" = "absent" ]; then
	note "-c omits hOriginal:" "absent"
else
	note "-c omits hOriginal:" "reported ${got}"
	fails=$((fails + 1))
fi

# The assessed figure in the report must be the real one at any verbosity,
# and must equal what -vvv prints.
text=$("${tool}" -vvv "${repo}/bin/truerand_1bit.bin" 1 2>/dev/null | sed -n 's/^Assessed min entropy: //p' | head -1)
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
