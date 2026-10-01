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

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
tool="${here}/../ea_restart"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regrst.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
note() { printf '%-50s %s\n' "$1" "$2"; }
[ -x "${tool}" ] || { echo "regression-restart: ${tool} missing (run 'make restart')" >&2; exit 2; }

# ea_restart requires exactly 1,000,000 samples (a 1000 x 1000 restart matrix).
python3 -c "
import random, sys
r = random.Random(8)
open(sys.argv[1], 'wb').write(bytes(r.randrange(256) for _ in range(1000000)))
" "${work}/r8.bin"

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
if [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'must be nonnegative'; then
	note "N-04 negative H_I keeps its own message:" "refused as nonnegative"
else
	note "N-04 negative H_I keeps its own message:" "exit ${rc}, message changed"
	fails=$((fails + 1))
fi

for good in 3.2 8 0; do
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
	"${tool}" "${mode}" -o "${work}/err.json" "${work}/r8.bin" 4 3.2 >/dev/null 2>&1
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
if "${tool}" -n -o "${work}/ok.json" "${work}/r8.bin" 8 3.2 >/dev/null 2>&1 && \
   python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get('errorLevel')==0 else 1)" "${work}/ok.json"; then
	note "R-3 successful run still errorLevel 0:" "yes"
else
	note "R-3 successful run still errorLevel 0:" "changed"
	fails=$((fails + 1))
fi

# ---------------------------------------------------------------- N-06
for mode in -i -n; do
	rm -f "${work}/nf.json"
	"${tool}" "${mode}" -o "${work}/nf.json" "${work}/absent.bin" 8 4 >/dev/null 2>&1
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
"${tool}" -n -o "${work}/okh.json" "${work}/r8.bin" 8 3.2 >/dev/null 2>&1
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
	out=$("${tool}" -vv "${work}/db100.bin" 8 0.5 2>&1)

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
	note "R-2:" "skipped (generator unavailable)"
fi

# An ordinary restart dataset must be unaffected.
out=$("${tool}" -vv "${work}/r8.bin" 8 3.2 2>&1)
if printf '%s' "${out}" | grep -q 'Validation Test Passed'; then
	note "R-2 ordinary dataset unaffected:" "passed"
else
	note "R-2 ordinary dataset unaffected:" "verdict changed"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-restart: PASS"
	exit 0
fi
echo "regression-restart: FAIL (${fails} checks)"
exit 1
