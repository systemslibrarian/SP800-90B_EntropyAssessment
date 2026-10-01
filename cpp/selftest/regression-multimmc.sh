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
#
# OBSERVED FAILING (2026-10-01). The binary-path check below replaced one that
# asserted only that a run length existed, which nothing could fail. Against a
# build with the binary reset removed -- mutation confirmed by source SHA-256
# changing bbcd1d0d02e5bae0 -> d9f61b5c44fdc7e8, by the marker being present in
# the compiled source, and by the binary differing from the clean build -- the
# mutant reports r = 100275 where the clean build reports 17, and this script
# then prints:
#
#     F09 binary path matches an independent reference: tool r = 100275, reference r = 17
#     regression-multimmc: FAIL (1 checks)
#
# The old check passed that same build. Re-run that way before trusting any
# change to this file: a check that has only been seen passing is an untested
# assertion that it can fail.

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

# The binary path carries the same logic and needs its own expected value.
#
# This check used to assert only that the binary path produced *a* run length,
# which nothing could fail: a mutant with the binary reset removed reports
# r = 100275 against a correct 17 and still passed. An expected value is now
# asserted, derived independently below rather than copied from the tool.
python3 - "${work}" <<'PY'
import random, sys
w = sys.argv[1]
r = random.Random(99)
open(w + "/bits.bin", "wb").write(bytes(r.randrange(2) for _ in range(200000)))
PY

# Independent reference for the binary path, implementing SP 800-90B 6.3.9
# directly: D = 16 subpredictors over a binary alphabet, prediction from the
# most frequent successor of the length-(d+1) prefix, the run of correct
# predictions ending on anything that is not a correct prediction by the
# winner (wrong, Null, or no prediction while i-2 < winner). r is one greater
# than the longest run, per step 6.
want=$(python3 - "${work}/bits.bin" <<'PY'
import sys
S = open(sys.argv[1], 'rb').read()
L = len(S)
D = 16
MAX_ENTRIES = 100000
d_dict = [dict() for _ in range(D)]
entries = [0] * D
scoreboard = [0] * D
winner = 0
run = 0
maxrun = 0
for d in range(D):
    if d < L - 2:
        d_dict[d][S[:d+1]] = {S[d+1]: 1}
        entries[d] = 1
for i in range(2, L):
    cur_winner = winner
    winner_correct = False
    found = False
    for d in range(D):
        if d > i - 2:
            break
        key = S[i-d-1:i]
        if d == 0 or found:
            post = d_dict[d].get(key)
            found = post is not None
        if found:
            post = d_dict[d][key]
            best = max(post, key=lambda y: (post[y], y))
            if best == S[i]:
                scoreboard[d] += 1
                if scoreboard[d] >= scoreboard[winner]:
                    winner = d
                if d == cur_winner:
                    winner_correct = True
            if S[i] in post:
                post[S[i]] += 1
            elif entries[d] < MAX_ENTRIES:
                post[S[i]] = 1
                entries[d] += 1
        elif entries[d] < MAX_ENTRIES:
            d_dict[d][key] = {S[i]: 1}
            entries[d] += 1
    if winner_correct:
        run += 1
        maxrun = max(maxrun, run)
    else:
        run = 0
print(maxrun + 1)
PY
)
got=$("${tool}" -vv "${work}/bits.bin" 1 2>/dev/null | sed -n 's/^Literal MultiMMC Prediction Estimate: r = //p' | head -1)
if [ -z "${want}" ] || [ -z "${got}" ]; then
	note "F09 binary path run length:" "could not compute want='${want}' got='${got}'"
	fails=$((fails + 1))
elif [ "${got}" = "${want}" ]; then
	note "F09 binary path matches an independent reference:" "r = ${got}"
else
	note "F09 binary path matches an independent reference:" "tool r = ${got}, reference r = ${want}"
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
