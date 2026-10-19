#!/bin/bash
#
# Regressions for ea_restart.
#
# Covered:
#   N-04  H_I was parsed with atof(), which cannot report a failure. "abc"
#         became 0 and the run reported a verdict for an entropy nobody
#         supplied; "nan" passed both range checks, because every comparison
#         with NaN is false, and then reached (int)floor(u/p) with p = NaN,
#         which is undefined behaviour indexing counts[] out of bounds.
#   N-06  sha256_file()'s status was discarded and its buffer left
#         uninitialised, so a failure put stack bytes into the report's
#         "sha256" field and the run continued and exited 0.
#   R-2   An estimate that could not be computed returns -1, and that sentinel
#         was folded into H_r/H_c as if it were an entropy, failing an
#         otherwise valid restart dataset.
#   R-3   An -i run that could not read its input wrote a JSON report saying
#         errorLevel 0: the error level was set on the non-IID report object
#         while the IID one was written.
#   N-08  Integer options must be unsigned decimal strings consumed in full.
#   N-10  IID restart JSON must carry the actual baseline statistics under
#         names that identify the raw-value and translated-index domains.
#   NOVEL-03 Restart row and column permutation result groups must carry
#         distinct layout labels rather than repeating bare iterations 0-2.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
# REGRESSION_RESTART_TOOL points this script at another build, for showing it
# FAIL against a pre-repair binary (the tag build): a regression that has only
# ever been seen passing is an untested assertion.
tool="${REGRESSION_RESTART_TOOL:-${here}/../ea_restart}"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regrst.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
# A case that could not run is not a pass. Counted apart from a failure because
# the cause is environmental, not a regression, but it still reaches the exit
# status: a guard that never executed supports no claim.
cannot_run=0
note() { printf '%-50s %s\n' "$1" "$2"; }
[ -x "${tool}" ] || { echo "regression-restart: ${tool} missing (run 'make restart')" >&2; exit 2; }

# ---------------------------------------------------------- NOVEL-03
# This exercises the exact JSON population helper with synthetic counters. It
# avoids a vacuous source grep and avoids the cost and randomness of two full
# permutation batteries over a million samples.
label_test="${here}/restart-report-label-test"
build_out=$(make -s -C "${here}/.." selftest/restart-report-label-test 2>&1); build_rc=$?
if [ "${build_rc}" -ne 0 ]; then
	note "NOVEL-03 row/column label test builds:" "failed (exit ${build_rc})"
	printf '%s\n' "${build_out}" | tail -4 | sed 's/^/    /'
	fails=$((fails + 1))
elif out=$("${label_test}" 2>&1); then
	note "NOVEL-03 permutation groups are labelled:" "rows 0-2, columns 0-2"
else
	note "NOVEL-03 permutation groups are labelled:" "failed"
	printf '%s\n' "${out}" | tail -4 | sed 's/^/    /'
	fails=$((fails + 1))
fi

# ea_restart requires exactly 1,000,000 samples (a 1000 x 1000 restart matrix).
python3 -c "
import random, sys
r = random.Random(8)
open(sys.argv[1], 'wb').write(bytes(r.randrange(256) for _ in range(1000000)))
" "${work}/r8.bin"

# ---------------------------------------------------------------- N-08
# Use an absent input so a permissive pre-fix parse is distinguishable from a
# parser refusal without running the restart simulation.
for bad in 8x +8 0x8; do
	out=$("${tool}" -n "${work}/absent.bin" "${bad}" 1 2>&1); rc=$?
	if [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'unsigned decimal'; then
		note "N-08 restart refuses width ${bad}:" "refused"
	else
		note "N-08 restart refuses width ${bad}:" "exit ${rc}, parser accepted it"
		fails=$((fails + 1))
	fi
done

for bad in 5000000x +5000000 0x5000000; do
	out=$("${tool}" -n -s "${bad}" "${work}/absent.bin" 8 1 2>&1); rc=$?
	if [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'unsigned decimal'; then
		note "N-08 restart refuses -s ${bad}:" "refused"
	else
		note "N-08 restart refuses -s ${bad}:" "exit ${rc}, parser accepted it"
		fails=$((fails + 1))
	fi
done

# ---------------------------------------------------------------- N-10
# H_I=0 makes the restart sanity bound permissive, while this deterministic
# period-two matrix fails an IID test before the expensive permutation stage.
# It is nevertheless a standards-sized 1000 x 1000 restart capture, so the
# report path is exercised with the required sample count and dimensions.
# A checkerboard: rows AND columns alternate, so X_max is 500 in both and the
# 3.1.4.3 sanity check passes at H_I = 1 (cutoff 570). The earlier row-only
# alternation had constant columns (X_max 1000) and passed only because H_I
# was 0, which C16 made inadmissible.
python3 -c "open('$work/alternating.bin','wb').write(bytes(((i + i // 1000) & 1) for i in range(1000000)))"
"${tool}" -i -q -o "${work}/alternating.json" "${work}/alternating.bin" 1 1 >/dev/null 2>&1
rc=$?
if [ "${rc}" -ne 0 ] && python3 - "${work}/alternating.json" <<'PY'
import json, math, sys
d = json.load(open(sys.argv[1]))
tc = d.get("testCases", [{}])[0]
ok = (math.isclose(tc.get("rawMean", -1), 0.5)
      and math.isclose(tc.get("translatedSymbolMedian", -1), 0.5)
      and "mean" not in tc and "median" not in tc)
sys.exit(0 if ok else 1)
PY
then
	note "N-10 restart reports actual named statistics:" "rawMean 0.5, translatedSymbolMedian 0.5"
else
	note "N-10 restart reports actual named statistics:" "missing, zero, or ambiguously named"
	fails=$((fails + 1))
fi

# ---------------------------------------------------------------- N-04
# Each of these must be refused, with a nonzero exit and no crash.
for bad in nan NAN inf -inf abc 1.5x "" 3.2e; do
	out=$("${tool}" -n "${work}/r8.bin" 8 "${bad}" 2>&1); rc=$?
	label=${bad:-'(empty)'}
	# A signal shows as 128+N (134 SIGABRT, 139 SIGSEGV); exit(-1) from the
	# usage path shows as 255, which is a refusal, not a crash.
	if [ "${rc}" -ge 128 ] && [ "${rc}" -le 160 ]; then
		note "N-04 H_I='${label}' does not crash:" "CRASHED (signal, exit ${rc})"
		fails=$((fails + 1))
	elif [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'must be a finite decimal number'; then
		note "N-04 H_I='${label}' refused:" "refused (exit ${rc})"
	else
		note "N-04 H_I='${label}' refused:" "exit ${rc}, expected a refusal"
		fails=$((fails + 1))
	fi
done

# A negative value is still caught by the existing range check, with its own
# message, and valid values still run.
out=$("${tool}" -n "${work}/r8.bin" 8 -1 2>&1); rc=$?
# Since C16 a leading '-' fails the grammar before any sign check, so either refusal message is the correct one.
if [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -qE 'must be greater than zero|must be a finite decimal number'; then
	note "N-04 negative H_I refused with a reason:" "refused"
else
	note "N-04 negative H_I refused with a reason:" "exit ${rc}, no reason given"
	fails=$((fails + 1))
fi

for good in 3.2/symbol 8/symbol 0.4/bit; do
	if "${tool}" -n "${work}/r8.bin" 8 "${good}" >/dev/null 2>&1; then
		note "N-04 valid H_I=${good} still runs:" "ran"
	else
		note "N-04 valid H_I=${good} still runs:" "refused"
		fails=$((fails + 1))
	fi
done

# ---------------------------------------------------------------- R-3
# r8.bin holds byte values, so declaring 4 bits per symbol makes read_file
# fail. The report must say so, in both modes.
for mode in -i -n; do
	rm -f "${work}/err.json"
	"${tool}" "${mode}" -o "${work}/err.json" "${work}/r8.bin" 4 3.2/symbol >/dev/null 2>&1
	rc=$?
	if [ "${rc}" -eq 0 ]; then
		note "R-3 ${mode} read failure exits nonzero:" "exit 0"
		fails=$((fails + 1))
	elif python3 - "${work}/err.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
sys.exit(0 if d.get("errorLevel", 0) != 0 and d.get("errorMessage") else 1)
PY
	then
		note "R-3 ${mode} read failure recorded in JSON:" "errorLevel set with a message"
	else
		note "R-3 ${mode} read failure recorded in JSON:" "errorLevel 0 or no message"
		fails=$((fails + 1))
	fi
done

# A run that succeeds must still report errorLevel 0.
rm -f "${work}/ok.json"
if "${tool}" -n -o "${work}/ok.json" "${work}/r8.bin" 8 3.2/symbol >/dev/null 2>&1 && \
   python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get('errorLevel')==0 else 1)" "${work}/ok.json"; then
	note "R-3 successful run still errorLevel 0:" "yes"
else
	note "R-3 successful run still errorLevel 0:" "changed"
	fails=$((fails + 1))
fi

# ---------------------------------------------------------------- N-06
for mode in -i -n; do
	rm -f "${work}/nf.json"
	"${tool}" "${mode}" -o "${work}/nf.json" "${work}/absent.bin" 8 4/symbol >/dev/null 2>&1
	rc=$?
	if [ "${rc}" -eq 0 ]; then
		note "N-06 ${mode} unhashable input exits nonzero:" "exit 0"
		fails=$((fails + 1))
	elif python3 - "${work}/nf.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
# errorLevel must be set, and no sha256 may be reported for a file that
# could not be hashed.
sys.exit(0 if d.get("errorLevel", 0) != 0 and not d.get("sha256") else 1)
PY
	then
		note "N-06 ${mode} no hash invented on failure:" "errorLevel set, sha256 absent"
	else
		note "N-06 ${mode} no hash invented on failure:" "errorLevel 0 or a sha256 was reported"
		fails=$((fails + 1))
	fi
done

# A valid run must still record the real hash of the file.
rm -f "${work}/okh.json"
"${tool}" -n -o "${work}/okh.json" "${work}/r8.bin" 8 3.2/symbol >/dev/null 2>&1
want=$(shasum -a 256 "${work}/r8.bin" 2>/dev/null | cut -d' ' -f1)
[ -n "${want}" ] || want=$(sha256sum "${work}/r8.bin" | cut -d' ' -f1)
got=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('sha256',''))" "${work}/okh.json" 2>/dev/null)
if [ "${got}" = "${want}" ]; then
	note "N-06 valid run records the real hash:" "matches"
else
	note "N-06 valid run records the real hash:" "got '${got}'"
	fails=$((fails + 1))
fi

# ---------------------------------------------------------------- R-2
# A de Bruijn B(100,3) sequence is exactly 1,000,000 samples in which every
# 3-tuple occurs once and every 2-tuple about 100 times, so the LRS estimate
# hits "v < u, cannot be computed" (SP 800-90B 6.3.6 step 2) and returns -1.
gen="${repo}/audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py"
if [ -f "${gen}" ] && python3 "${gen}" 100 11 "${work}/db100.bin" >/dev/null 2>&1; then
	out=$("${tool}" -vv "${work}/db100.bin" 8 0.5/symbol 2>&1)

	if printf '%s' "${out}" | grep -q "v<u. Can't Run LRS Test"; then
		note "R-2 the LRS estimate really does decline:" "yes (precondition holds)"
	else
		note "R-2 the LRS estimate really does decline:" "no; this input no longer exercises R-2"
		fails=$((fails + 1))
	fi

	if printf '%s' "${out}" | grep -qE '^H_r: -1'; then
		note "R-2 the -1 sentinel is not folded in:" "H_r is -1 (still folded)"
		fails=$((fails + 1))
	else
		note "R-2 the -1 sentinel is not folded in:" "H_r $(printf '%s' "${out}" | sed -n 's/^H_r: //p' | head -1)"
	fi

	if printf '%s' "${out}" | grep -q 'Validation Test Passed'; then
		note "R-2 no false validation failure:" "passed"
	else
		note "R-2 no false validation failure:" "still fails validation"
		fails=$((fails + 1))
	fi
else
	note "R-2:" "COULD NOT RUN (no generator at ${gen})"
	cannot_run=$((cannot_run + 1))
fi

# An ordinary restart dataset must be unaffected.
out=$("${tool}" -vv "${work}/r8.bin" 8 3.2/symbol 2>&1)
if printf '%s' "${out}" | grep -q 'Validation Test Passed'; then
	note "R-2 ordinary dataset unaffected:" "passed"
else
	note "R-2 ordinary dataset unaffected:" "verdict changed"
	fails=$((fails + 1))
fi

# ---------------------------------------------------------- C16 + C23
# Two permissive defects on the one restart gate (OC-11, OC-27, OC-29):
#   C16  H_I was accepted at any scale and at 0: '1e-400' underflowed to 0,
#        giving X_cutoff 1000 and two vacuous gates with exit 0; a per-bit
#        figure for an 8-bit symbol passed every range check and produced a
#        wrong cutoff silently. Now: strict grammar, no underflow, H_I > 0,
#        and for a multi-bit symbol the scale must be stated (/symbol, /bit).
#   C23  The cutoff was an order statistic of the simulated MAXIMUM over all
#        2^H_I symbols where 3.1.4.3 step 5 specifies one Binomial(1000, p):
#        2 to 5 counts too permissive at every H_I. Now computed exactly.
# Shown failing against the tag build (unrepaired-reference-2026-10-15) via
# REGRESSION_RESTART_TOOL; see logs/c23/regression-restart-vs-tag.log.
mk_matrix() { # mk_matrix <out> <X zeros in column 17>  (generators/c23_forced_count.py, inline)
	python3 - "$1" "$2" <<-'PY'
	import random, sys
	r = random.Random(0xC23ACC)
	d = bytearray(r.getrandbits(8) for _ in range(1000000))
	col = [i * 1000 + 17 for i in range(1000)]
	for idx in col:
	    if d[idx] == 0: d[idx] = 1
	for idx in col[:int(sys.argv[2])]: d[idx] = 0
	open(sys.argv[1], 'wb').write(bytes(d))
	PY
}
mk_matrix "${work}/x24.bin" 24
mk_matrix "${work}/x20.bin" 20
mk_matrix "${work}/x1000.bin" 1000          # X_max = 1000 fails every cutoff at once, so the cutoff line is cheap to read

# C16: refusals. Each must exit nonzero without a crash and say why.
for bad in 1e-400 0 0x1p3 ' 3' '3 ' 3/sym 7 3.2; do      # '7' and '3.2' are bare numbers for an 8-bit symbol
	out=$("${tool}" -n "${work}/x20.bin" 8 "${bad}" 2>&1); rc=$?
	if [ "${rc}" -ge 128 ] && [ "${rc}" -le 160 ]; then
		note "C16 H_I='${bad}' refused:" "CRASHED (signal, exit ${rc})"; fails=$((fails + 1))
	elif [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -qE 'must be a finite decimal number|must be greater than zero|must state its scale'; then
		note "C16 H_I='${bad}' refused:" "refused (exit ${rc})"
	else
		note "C16 H_I='${bad}' refused:" "exit ${rc}, ACCEPTED or wrong message"; fails=$((fails + 1))
	fi
done
# C16: the stated scale resolves. 0.875/bit on an 8-bit symbol IS 7/symbol: same cutoff.
c_sym=$("${tool}" -v -n "${work}/x1000.bin" 8 7/symbol 2>&1 | sed -n 's/.*X_cutoff: \([0-9]*\).*/\1/p')
c_bit=$("${tool}" -v -n "${work}/x1000.bin" 8 0.875/bit 2>&1 | sed -n 's/.*X_cutoff: \([0-9]*\).*/\1/p')
if [ -n "${c_sym}" ] && [ "${c_sym}" = "${c_bit}" ]; then
	note "C16 0.875/bit resolves to 7/symbol:" "both give X_cutoff ${c_sym}"
else
	note "C16 0.875/bit resolves to 7/symbol:" "X_cutoff ${c_sym:-?} vs ${c_bit:-?}"; fails=$((fails + 1))
fi
# A 1-bit symbol may take a bare number (the scales coincide).
"${tool}" -n -q -o "${work}/bare1.json" "${work}/alternating.bin" 1 0.9 >/dev/null 2>&1
if grep -q restartXcutoff "${work}/bare1.json" 2>/dev/null; then
	note "C16 bare H_I still accepted for 1-bit symbols:" "accepted (report carries restartXcutoff)"
else
	note "C16 bare H_I still accepted for 1-bit symbols:" "refused, or report lacks the sanity-check fields"; fails=$((fails + 1))
fi

# C23: the cutoff equals SP 800-90B 3.1.4.3 step 5 computed in exact rational
# arithmetic (oracles/restart_cutoff_anchor.py, alpha = 0.000005) at 32 values
# of H_I -- a pin from a different implementation of the standard's sum.
cbad=0
for pair in 0.25:890 0.5:769 0.75:662 1:570 1.25:490 1.5:421 1.75:362 2:312 2.25:269 2.5:232 2.75:200 3:173 3.25:150 3.5:130 3.75:113 4:99 4.25:86 4.5:76 4.75:66 5:58 5.25:51 5.5:45 5.75:40 6:36 6.25:32 6.5:28 6.75:25 7:23 7.25:21 7.5:19 7.75:17 8:15; do
	h=${pair%%:*}; want=${pair#*:}
	got=$("${tool}" -v -n "${work}/x1000.bin" 8 "${h}/symbol" 2>&1 | sed -n 's/.*X_cutoff: \([0-9]*\).*/\1/p')
	[ "${got}" = "${want}" ] || { cbad=$((cbad + 1)); note "C23 cutoff at H_I=${h}:" "got ${got:-?}, exact ${want}"; }
done
if [ "${cbad}" -eq 0 ]; then
	note "C23 X_cutoff equals the exact 3.1.4.3 cutoff:" "32 of 32 H_I values (0.25 .. 8)"
else
	note "C23 X_cutoff equals the exact 3.1.4.3 cutoff:" "${cbad} of 32 differ"; fails=$((fails + 1))
fi
# C23: the acceptance decision. X_max 24 at H_I = 7 is above the exact cutoff 23
# (Pr[X >= 24] = 2.2e-06 < alpha) and the pre-repair tool accepted it (cutoff 27).
out=$("${tool}" -v -n -o "${work}/x24.json" "${work}/x24.bin" 8 7/symbol 2>&1); rc=$?
if [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'Restart Sanity Check Failed' && python3 - "${work}/x24.json" <<-'PY'
	import json, sys
	d = json.load(open(sys.argv[1]))
	sys.exit(0 if (d.get('restartXmax') == 24 and d.get('restartXcutoff') == 23 and d.get('passedRestartSanityCheck') is False and d.get('errorLevel') != 0) else 1)
	PY
then
	note "C23 X_max 24 at H_I 7 is REJECTED, and the JSON says why:" "X_cutoff 23, passedRestartSanityCheck false"
else
	note "C23 X_max 24 at H_I 7 is REJECTED, and the JSON says why:" "exit ${rc}; accepted, or fields missing"; fails=$((fails + 1))
fi
out=$("${tool}" -v -n "${work}/x20.bin" 8 7/symbol 2>&1)
if printf '%s' "${out}" | grep -q 'Restart Sanity Check Passed'; then
	note "C23 X_max 20 at H_I 7 still passes the sanity check:" "passed"
else
	note "C23 X_max 20 at H_I 7 still passes the sanity check:" "did not pass"; fails=$((fails + 1))
fi

echo
if [ "${cannot_run}" -ne 0 ]; then
	echo "regression-restart: COULD NOT RUN (${cannot_run} case(s) had no input; ${fails} of the cases that ran failed)"
	exit 2
fi
if [ "${fails}" -eq 0 ]; then
	echo "regression-restart: PASS"
	exit 0
fi
echo "regression-restart: FAIL (${fails} checks)"
exit 1
