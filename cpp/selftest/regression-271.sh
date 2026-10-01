#!/bin/bash
#
# Regression for upstream issue #271: under -c, the Section 5 IID tests must
# run on the conditioned output treated as a binary string (data.bsymbols),
# not on the packed multi-bit symbols.
#
# The dataset is the nibble-duplicate construction from the audit: every byte
# is (x << 4) | x for a uniform 4-bit x, so the high nibble repeats the low
# nibble. As 8-bit symbols it looks like 16 equiprobable values and passes the
# IID tests; as a bitstring the repetition is plainly visible and the tests
# fail. Before the fix both views produced the same verdicts, because both were
# computed from the symbols.
#
# Asserting on chi-square and the longest-repeated-substring test only: those
# are deterministic. The permutation battery seeds itself from /dev/urandom and
# its verdict is not reproducible run to run, so it is not asserted on here.
#
# The dataset is deliberately small so this runs in seconds; that is below the
# SP 800-90B Section 3.1.1 minimum the tools now enforce, so the internal
# test escape is set, exactly as the selftest harness does.

set -u

here=$(cd "$(dirname "$0")" && pwd)
ea_iid="${here}/../ea_iid"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-reg271.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

export EA_ALLOW_SHORT_DATASET=1

fails=0
note() { printf '%-42s %s\n' "$1" "$2"; }

if [ ! -x "${ea_iid}" ]; then
	echo "regression-271: ${ea_iid} is missing (run 'make iid' first)" >&2
	exit 2
fi

python3 - "${work}/nibdup.bin" <<'PY'
import random, sys
r = random.Random(4242)
# Same construction and seed as the preserved audit reproducer, at a size that
# keeps the permutation battery quick.
data = bytes(((x << 4) | x) for x in (r.randrange(16) for _ in range(10000)))
open(sys.argv[1], 'wb').write(data)
PY
[ -s "${work}/nibdup.bin" ] || { echo "regression-271: could not generate the dataset" >&2; exit 2; }

verdict() { # verdict <mode> <test name fragment>
	local mode=$1 frag=$2
	"${ea_iid}" "${mode}" -v "${work}/nibdup.bin" 2>/dev/null \
		| grep -E "\*\* (Passed|Failed) ${frag}" \
		| sed -E 's/^\*\* (Passed|Failed).*/\1/' | head -1
}

# Under -c the tests see the bitstring, where the nibble repetition is visible.
for t in "chi square tests:Failed" "length of longest repeated substring test:Failed"; do
	frag=${t%:*}; want=${t#*:}
	got=$(verdict -c "${frag}")
	if [ "${got}" = "${want}" ]; then
		note "-c (bitstring) ${frag}:" "${got} (as required)"
	else
		note "-c (bitstring) ${frag}:" "got '${got}', expected '${want}'"
		fails=$((fails + 1))
	fi
done

# Under -i the same bytes are tested as 8-bit symbols, which cannot see the
# repetition. This is the contrast that makes the check above meaningful: if
# both modes agreed, the tests would not be reading the bitstring.
for t in "chi square tests:Passed" "length of longest repeated substring test:Passed"; do
	frag=${t%:*}; want=${t#*:}
	got=$(verdict -i "${frag}")
	if [ "${got}" = "${want}" ]; then
		note "-i (8-bit symbols) ${frag}:" "${got} (as required)"
	else
		note "-i (8-bit symbols) ${frag}:" "got '${got}', expected '${want}'"
		fails=$((fails + 1))
	fi
done

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-271: PASS"
	exit 0
fi
echo "regression-271: FAIL (${fails} checks)"
exit 1
