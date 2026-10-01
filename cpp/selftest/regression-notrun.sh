#!/bin/bash
#
# Regression for F05: an estimator that could not produce a value must be
# visible in the report.
#
# The JSON omits a value both when an estimator does not apply to the branch
# being run and when it applies but could not produce a result, so a consumer
# could not tell that the reported minimum had been taken over fewer than the
# ten estimators SP 800-90B 6.2 lists. A missing estimator can only raise the
# minimum, which is the dangerous direction.
#
# This is deliberately NOT an error. @joshuaehill on #255: "There are
# instances where binary estimators can't produce an estimate but where the
# result is not an error ... This is not an error, and should not be flagged
# as one." errorLevel stays 0 and the checks below enforce that.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
tool="${here}/../ea_non_iid"
gen="${repo}/audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regnr5.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
note() { printf '%-54s %s\n' "$1" "$2"; }
[ -x "${tool}" ] || { echo "regression-notrun: ${tool} missing (run 'make non_iid')" >&2; exit 2; }

flags() { python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
out=[]
for tc in d['testCases']:
    for k,tag in (('literalEstimateNotRun','literal'),('bitstringEstimateNotRun','bitstring')):
        if tc.get(k): out.append(tc['testCaseDesc']+'/'+tag)
print(';'.join(sorted(out)))" "$1"; }
errlevel() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['errorLevel'])" "$1"; }

# A de Bruijn B(100,3) sequence is exactly 1,000,000 samples, so it is a
# compliant dataset, and its LRS estimate genuinely cannot be computed
# (SP 800-90B 6.3.6 step 2, v < u). The skip must be visible.
if [ -f "${gen}" ] && python3 "${gen}" 100 11 "${work}/db100.bin" >/dev/null 2>&1; then
	"${tool}" -q -o "${work}/db.json" "${work}/db100.bin" 8 >/dev/null 2>&1
	got=$(flags "${work}/db.json")
	if printf '%s' "${got}" | grep -q 'LRS Test/literal'; then
		note "compliant input, LRS cannot run, is recorded:" "${got}"
	else
		note "compliant input, LRS cannot run, is recorded:" "flags '${got}'"
		fails=$((fails + 1))
	fi
	if [ "$(errlevel "${work}/db.json")" = "0" ]; then
		note "a skipped estimator is not an error:" "errorLevel 0"
	else
		note "a skipped estimator is not an error:" "errorLevel $(errlevel "${work}/db.json")"
		fails=$((fails + 1))
	fi
else
	note "de Bruijn case:" "skipped (generator unavailable)"
fi

# Ordinary NIST samples must carry no flags at all: a false positive here
# would make the field useless.
for f in truerand_8bit truerand_1bit ringOsc-nist normal; do
	"${tool}" -q -o "${work}/${f}.json" "${repo}/bin/${f}.bin" >/dev/null 2>&1
	got=$(flags "${work}/${f}.json")
	if [ -z "${got}" ]; then
		note "${f}.bin carries no skip flags:" "none"
	else
		note "${f}.bin carries no skip flags:" "${got}"
		fails=$((fails + 1))
	fi
done

# A short dataset skips several estimators; each must be named.
python3 -c "
import random, sys
r = random.Random(777); P = 3000
p = [r.randrange(2) for _ in range(P)]
open(sys.argv[1], 'wb').write(bytes(p[i % P] for i in range(2000)))" "${work}/short.bin"
EA_ALLOW_SHORT_DATASET=1 "${tool}" -q -o "${work}/short.json" "${work}/short.bin" >/dev/null 2>&1
got=$(flags "${work}/short.json")
if printf '%s' "${got}" | grep -q 'Compression' && printf '%s' "${got}" | grep -q 'Multi Most Common in Window'; then
	note "short input names the estimators that cannot run:" "${got}"
else
	note "short input names the estimators that cannot run:" "flags '${got}'"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-notrun: PASS"
	exit 0
fi
echo "regression-notrun: FAIL (${fails} checks)"
exit 1
