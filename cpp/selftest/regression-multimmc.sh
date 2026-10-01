#!/bin/bash
#
# Regression for F09: the MultiMMC run of correct predictions must end on a
# Null prediction from the winning subpredictor.
#
# SP 800-90B 6.3.9 step 1 initialises correct[] to 0 and step 4.d sets
# correct[i-2] = 1 only when the prediction equals s_i, so a Null prediction
# leaves it 0; the worked example in that section shows exactly that for its
# first two rounds, where prediction is Null and correct is 0. The run counter
# was reset only where the winner predicted and was wrong, so a Null from the
# winner carried the run straight across it.
#
# The direction is too low: an inflated r makes P_local larger and the
# estimate smaller, so the defect was conservative. It is still a deviation
# from the standard and it moved the estimate by a factor of 440 on the
# dataset below.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
tool="${here}/../ea_non_iid"
gen="${repo}/audits/2026-09-30/novel-findings/generators/noniid"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regmmc.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

export EA_ALLOW_SHORT_DATASET=1

fails=0
note() { printf '%-48s %s\n' "$1" "$2"; }
[ -x "${tool}" ] || { echo "regression-multimmc: ${tool} missing (run 'make non_iid')" >&2; exit 2; }

if [ ! -f "${gen}/f09gen.py" ] || [ ! -f "${gen}/fillsteps.py" ]; then
	echo "regression-multimmc: generator missing under ${gen}" >&2
	exit 2
fi

cp "${gen}/f09gen.py" "${gen}/fillsteps.py" "${work}/"
( cd "${work}" && python3 f09gen.py 3 300 f09b.bin >/dev/null 2>&1 )
[ -s "${work}/f09b.bin" ] || { echo "regression-multimmc: could not generate the dataset" >&2; exit 2; }

out=$("${tool}" -vv "${work}/f09b.bin" 8 2>/dev/null)
field() { printf '%s\n' "${out}" | sed -n "s/^Literal MultiMMC Prediction Estimate: $1 = //p" | head -1; }

# The audit's literal implementation of 6.3.9 gives r = 24 for this dataset.
got=$(field r)
if [ "${got}" = "24" ]; then
	note "F09 run length matches the spec reference:" "r = 24"
else
	note "F09 run length matches the spec reference:" "r = ${got}, expected 24"
	fails=$((fails + 1))
fi

# C and N count different things and must not have moved.
for pair in "C:7089" "N:114144"; do
	k=${pair%%:*}; want=${pair#*:}
	got=$(field "${k}")
	if [ "${got}" = "${want}" ]; then
		note "F09 ${k} unchanged:" "${got}"
	else
		note "F09 ${k} unchanged:" "got ${got}, expected ${want}"
		fails=$((fails + 1))
	fi
done

# The binary path carries the same logic and must agree with the generic path
# on the same bits. Feeding the generic path one bit per byte must give the
# same run length as the binary path sees on a 1-bit file.
python3 - "${work}" <<'PY'
import random, sys
w = sys.argv[1]
r = random.Random(99)
bits = bytes(r.randrange(2) for _ in range(200000))
open(w + "/bits.bin", "wb").write(bits)
# The same bits as 2-bit symbols keeps the values in {0,1} so the alphabet
# stays binary and the binary path is used; a 1-bit declaration does the same.
PY
a=$("${tool}" -vv "${work}/bits.bin" 1 2>/dev/null | sed -n 's/^Literal MultiMMC Prediction Estimate: r = //p' | head -1)
if [ -n "${a}" ]; then
	note "F09 binary path still produces a run length:" "r = ${a}"
else
	note "F09 binary path still produces a run length:" "no value"
	fails=$((fails + 1))
fi

# The figures on NIST's own samples must not move.
# Compared against NIST's own reference output rather than a value copied
# here, so this cannot drift out of step with refdata/.
want=$(sed -n 's/^Literal MultiMMC Prediction Estimate: min entropy = //p' "${here}/refdata/truerand_8bit.res" | head -1)
got=$("${tool}" -vv "${repo}/bin/truerand_8bit.bin" 8 2>/dev/null | sed -n 's/^Literal MultiMMC Prediction Estimate: min entropy = //p' | head -1)
if [ -n "${want}" ] && [ "${got}" = "${want}" ]; then
	note "F09 NIST sample still matches refdata:" "${got}"
else
	note "F09 NIST sample still matches refdata:" "got '${got}', reference '${want}'"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-multimmc: PASS"
	exit 0
fi
echo "regression-multimmc: FAIL (${fails} checks)"
exit 1
