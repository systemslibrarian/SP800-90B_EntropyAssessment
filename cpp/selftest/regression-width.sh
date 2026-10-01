#!/bin/bash
#
# Regression for upstream #254: the symbol width the assessment used must be
# visible in the JSON report.
#
# @joshuaehill: "Certainly reporting the evident symbol width in JSON would be
# useful. Reporting this 'not a mapping' as a warning isn't useful." So the
# width inference itself is unchanged and no warning was added; only the
# report gained the width, and a flag saying whether it was given or inferred.
#
# NIST's sample truerand_4bit.bin holds 4-bit values in bytes, so it exercises
# both paths: inferred as 4-bit by default, assessed as 8-bit when declared.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regwidth.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
note() { printf '%-50s %s\n' "$1" "$2"; }

check() { # check <tool> <label> <expected width> <expected inferred> [declared width]
	local tool=$1 label=$2 width=$3 inferred=$4 declared=${5:-}
	local json="${work}/$(basename "${tool}")-${label// /_}.json"

	if [ -n "${declared}" ]; then
		"${here}/../${tool}" -q -o "${json}" "${repo}/bin/truerand_4bit.bin" "${declared}" >/dev/null 2>&1
	else
		"${here}/../${tool}" -q -o "${json}" "${repo}/bin/truerand_4bit.bin" >/dev/null 2>&1
	fi

	if python3 - "${json}" "${width}" "${inferred}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
sys.exit(0 if d.get("bitsPerSymbol") == int(sys.argv[2])
         and d.get("bitsPerSymbolInferred") == (sys.argv[3] == "true") else 1)
PY
	then
		note "${tool} ${label}:" "bitsPerSymbol ${width}, inferred ${inferred}"
	else
		note "${tool} ${label}:" "wrong or missing (expected ${width}, inferred ${inferred})"
		fails=$((fails + 1))
	fi
}

for tool in ea_non_iid ea_iid; do
	[ -x "${here}/../${tool}" ] || { echo "regression-width: ${tool} missing" >&2; exit 2; }
	check "${tool}" "inferred width" 4 true
	check "${tool}" "declared width" 8 false 8
done

# The inference itself must not have changed: 4-bit data still infers 4.
got=$("${here}/../ea_non_iid" -vv "${repo}/bin/truerand_4bit.bin" 2>/dev/null \
	| sed -n 's/^Loaded .* distinct \([0-9]*\)-bit-wide symbols$/\1/p' | head -1)
if [ "${got}" = "4" ]; then
	note "inference unchanged for 4-bit data:" "still infers 4"
else
	note "inference unchanged for 4-bit data:" "inferred ${got}"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-width: PASS"
	exit 0
fi
echo "regression-width: FAIL (${fails} checks)"
exit 1
