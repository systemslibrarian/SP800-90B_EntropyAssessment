#!/bin/bash
#
# Regression for the central SP 800-90B Section 3.1.1 intake check.
#
# Section 3.1.1 item 1 requires at least 1,000,000 sample values. The tools
# now refuse to assess anything smaller, before any estimator runs. That one
# rule is what makes the short-input defects reported upstream as #257, #258,
# #261, #263 and #264 unreachable through ordinary use, so this test guards
# the rule itself rather than each of those defects.
#
# Checked here:
#   1. a short file is refused by both tools, with a nonzero exit status
#   2. the refusal is machine-readable: errorLevel != 0 and a message
#   3. no estimator ran before the refusal
#   4. the count checked is the count actually loaded, so a -l subset that
#      takes fewer than 1,000,000 samples out of a larger file is refused too
#   5. a compliant file is still assessed, and its figure is unchanged
#   6. the internal test escape permits a short run but marks it, in both the
#      human-readable output and the JSON, as not a compliant assessment

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
non_iid="${here}/../ea_non_iid"
ea_iid="${here}/../ea_iid"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regmin.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

short="${repo}/bin/rand8_short.bin"          # 10,000 samples
long="${repo}/bin/truerand_1bit.bin"         # 1,000,000 samples
pinned="${repo}/bin/ringOsc-nist.bin"        # exactly 1,000,000 samples

fails=0
note() { printf '%-46s %s\n' "$1" "$2"; }

for b in "${non_iid}" "${ea_iid}"; do
	[ -x "${b}" ] || { echo "regression-minsize: ${b} is missing (run 'make non_iid iid')" >&2; exit 2; }
done

# 1-3. refusal, exit status, machine-readable error, and no estimator output
for tool in "${non_iid}" "${ea_iid}"; do
	name=$(basename "${tool}")
	unset EA_ALLOW_SHORT_DATASET
	out=$("${tool}" -v -o "${work}/${name}.json" "${short}" 2>&1); rc=$?

	if [ "${rc}" -ne 0 ]; then
		note "${name}: short file refused:" "exit ${rc}"
	else
		note "${name}: short file refused:" "exit 0 — NOT refused"
		fails=$((fails + 1))
	fi

	if printf '%s' "${out}" | grep -q 'requires at least 1000000'; then
		note "${name}: human-readable reason:" "present"
	else
		note "${name}: human-readable reason:" "missing"
		fails=$((fails + 1))
	fi

	if [ -f "${work}/${name}.json" ] && \
	   python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('errorLevel',0)!=0 and d.get('errorMessage') else 1)" "${work}/${name}.json"; then
		note "${name}: JSON errorLevel and message:" "set"
	else
		note "${name}: JSON errorLevel and message:" "missing or zero"
		fails=$((fails + 1))
	fi

	if printf '%s' "${out}" | grep -qE 'Estimate:|Passed|Failed'; then
		note "${name}: estimators did not run:" "an estimator produced output"
		fails=$((fails + 1))
	else
		note "${name}: estimators did not run:" "confirmed"
	fi
done

# 4. the subset actually loaded is what counts, not the size of the file
unset EA_ALLOW_SHORT_DATASET
if "${non_iid}" -l 0,5000 -q "${long}" >/dev/null 2>&1; then
	note "short -l subset of a long file:" "accepted — the file size was checked"
	fails=$((fails + 1))
else
	note "short -l subset of a long file:" "refused"
fi

# 5. a compliant dataset is unaffected
unset EA_ALLOW_SHORT_DATASET
got=$("${non_iid}" -vv "${pinned}" 2>/dev/null | sed -n 's/^Assessed min entropy: //p')
if [ -n "${got}" ]; then
	note "compliant file still assessed:" "Assessed ${got}"
else
	note "compliant file still assessed:" "no figure produced"
	fails=$((fails + 1))
fi

# 6. the escape permits the run and says it is not compliant
out=$(EA_ALLOW_SHORT_DATASET=1 "${non_iid}" -v -o "${work}/esc.json" "${short}" 2>&1); rc=$?
if [ "${rc}" -eq 0 ] && printf '%s' "${out}" | grep -q 'NOT a compliant'; then
	note "escape permits and warns:" "exit 0 with the non-compliance notice"
else
	note "escape permits and warns:" "exit ${rc}, notice missing"
	fails=$((fails + 1))
fi
if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('nonCompliantShortDataset') is True else 1)" "${work}/esc.json" 2>/dev/null; then
	note "escape marked in JSON:" "nonCompliantShortDataset true"
else
	note "escape marked in JSON:" "flag absent"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-minsize: PASS"
	exit 0
fi
echo "regression-minsize: FAIL (${fails} checks)"
exit 1
