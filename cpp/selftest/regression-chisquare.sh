#!/bin/bash
#
# Regression for N-01: SP 800-90B 5.2.3 says of the binary chi-square
# independence test, "m = 11. If m is 1, the test fails. ... The test is
# applied if m >= 2."
#
# binary_chi_square_independence() returned score 0 with df 0 when m = 1. A
# chi-square statistic of 0 on 0 degrees of freedom has a p-value of exactly 1,
# and the caller fails only when the p-value is below 0.001, so the condition
# the standard says must fail the test was reported as a pass. A dataset too
# biased to form 2-bit blocks with the required expected count could therefore
# be declared IID.
#
# m = 1 exactly when min(p0,p1)^2 * (L/2) < 5. The two datasets below sit on
# either side of that boundary at L = 100,000, which keeps the permutation
# battery quick; they are below the Section 3.1.1 minimum, so the internal
# test escape is set, as the selftest harness does.

set -u

here=$(cd "$(dirname "$0")" && pwd)
ea_iid="${here}/../ea_iid"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regchi.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

export EA_ALLOW_SHORT_DATASET=1

fails=0
note() { printf '%-46s %s\n' "$1" "$2"; }
[ -x "${ea_iid}" ] || { echo "regression-chisquare: ${ea_iid} missing (run 'make iid')" >&2; exit 2; }

python3 - "${work}" <<'PY'
import random, sys
w = sys.argv[1]
for name, ones in (("m1", 999), ("m2", 1200)):
    L = 100000
    r = random.Random(ones)
    b = bytearray(L)
    for i in r.sample(range(L), ones):
        b[i] = 1
    open("%s/chi_%s.bin" % (w, name), "wb").write(bytes(b))
PY

verdict() { "${ea_iid}" -vvv "${work}/chi_$1.bin" 1 2>/dev/null | sed -n 's/^Chi square tests: //p' | head -1; }

# m = 1: the standard says the test fails.
got=$(verdict m1)
if [ "${got}" = "Failed" ]; then
	note "m = 1 fails the chi-square battery:" "Failed (as SP 800-90B 5.2.3 requires)"
else
	note "m = 1 fails the chi-square battery:" "got '${got}', expected 'Failed'"
	fails=$((fails + 1))
fi

# The reason must be the m = 1 rule, not an unrelated failure.
if "${ea_iid}" -vvv "${work}/chi_m1.bin" 1 2>/dev/null | grep -q 'm = 1, test fails per SP 800-90B 5.2.3'; then
	note "m = 1 reported with its reason:" "present"
else
	note "m = 1 reported with its reason:" "missing"
	fails=$((fails + 1))
fi

# m >= 2: the test is applied as usual and this dataset passes it.
got=$(verdict m2)
if [ "${got}" = "Passed" ]; then
	note "m >= 2 still applies the test:" "Passed"
else
	note "m >= 2 still applies the test:" "got '${got}', expected 'Passed'"
	fails=$((fails + 1))
fi

# Ordinary datasets, binary and non-binary, must be unaffected.
for s in truerand_1bit:1 truerand_8bit:8; do
	f=${s%:*}; w=${s#*:}
	got=$("${ea_iid}" -vvv "${here}/../../bin/${f}.bin" "${w}" 2>/dev/null | sed -n 's/^Chi square tests: //p' | head -1)
	if [ "${got}" = "Passed" ]; then
		note "${f} unaffected:" "Passed"
	else
		note "${f} unaffected:" "got '${got}', expected 'Passed'"
		fails=$((fails + 1))
	fi
done

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-chisquare: PASS"
	exit 0
fi
echo "regression-chisquare: FAIL (${fails} checks)"
exit 1
