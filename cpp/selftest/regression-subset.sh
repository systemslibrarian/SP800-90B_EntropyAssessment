#!/bin/bash
#
# Regression for the -l subset path, upstream #260.
#
# Checked:
#   1. subsetIndex * subsetSize is checked for overflow and refused, instead
#      of wrapping and assessing different data under the requested block's
#      name ("-l 4,4611686018427387904" wrapped to offset 0 and reported the
#      whole file's figure)
#   2. an offset at or past the end of the file is refused
#   3. "-l index,0" is refused, instead of being taken as "no subset" and
#      assessing the whole file with the index ignored
#   4. an ordinary subset still works
#   5. the report says which block was asked for, how many samples were asked
#      for, and how many were actually obtained, so a short final block is
#      visible
#   6. sha256 identifies the exact bytes consumed by the estimator, closing
#      N-07; subset provenance identifies where those bytes came from
#   7. N-08: subset numbers are unsigned decimal, consume the whole field,
#      and do not accept C-style octal, a leading sign, or trailing text

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
tool="${here}/../ea_non_iid"
iid_tool="${here}/../ea_iid"
sample="${repo}/bin/truerand_1bit.bin"      # 1,000,000 samples
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regsub.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
note() { printf '%-44s %s\n' "$1" "$2"; }
[ -x "${tool}" ] || { echo "regression-subset: ${tool} missing (run 'make non_iid')" >&2; exit 2; }
[ -x "${iid_tool}" ] || { echo "regression-subset: ${iid_tool} missing (run 'make iid')" >&2; exit 2; }

refused() { # refused <label> <expected text> <args...>
	local label=$1 want=$2; shift 2
	local out rc
	out=$("${tool}" -q "$@" "${sample}" 2>&1); rc=$?
	if [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q "${want}"; then
		note "${label}:" "refused"
	else
		note "${label}:" "exit ${rc}, expected a refusal mentioning '${want}'"
		fails=$((fails + 1))
	fi
}

refused "offset multiplication overflow" "offset overflows"        -l 4,4611686018427387904
refused "offset past end of file"        "past the end"            -l 5,1000000
refused "zero-sample subset request"     "greater than zero"       -l 3,0

# N-08 used strtoull(..., base 0), accepted a leading plus sign, and did not
# check that the second field ended at the end of the argument.  A ten-byte
# file makes the octal/decimal distinction without running any estimator:
# block 8 exists, while decimal block 10 starts exactly at EOF.
python3 -c "open('$work/ten.bin','wb').write(bytes(range(10)))"
for candidate in "${tool}" "${iid_tool}"; do
	name=$(basename "${candidate}")
	out=$("${candidate}" -q -l 010,1 "${work}/ten.bin" 2>&1); rc=$?
	if [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'at or past the end'; then
		note "N-08 ${name} treats 010 as decimal 10:" "yes"
	else
		note "N-08 ${name} treats 010 as decimal 10:" "no (exit ${rc})"
		fails=$((fails + 1))
	fi

	for bad in '+0,1' '0,+1' '0,1x' '0,0x1'; do
		out=$("${candidate}" -q -l "${bad}" "${work}/absent.bin" 2>&1); rc=$?
		if [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'unsigned decimal'; then
			note "N-08 ${name} refuses -l ${bad}:" "refused"
		else
			note "N-08 ${name} refuses -l ${bad}:" "exit ${rc}, parser accepted it"
			fails=$((fails + 1))
		fi
	done
done

# An ordinary subset must still work and carry its provenance.
if "${tool}" -q -o "${work}/ok.json" -l 0,1000000 "${sample}" >/dev/null 2>&1; then
	note "ordinary subset accepted:" "yes"
else
	note "ordinary subset accepted:" "refused"
	fails=$((fails + 1))
fi

if python3 - "${work}/ok.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
ok = (d.get("subsetIndex") == 0
      and d.get("subsetRequestedSamples") == 1000000
      and d.get("subsetActualSamples") == 1000000)
sys.exit(0 if ok else 1)
PY
then
	note "subset provenance in JSON:" "index, requested and actual present"
else
	note "subset provenance in JSON:" "missing or wrong"
	fails=$((fails + 1))
fi

# A short final block must be visible as such.
EA_ALLOW_SHORT_DATASET=1 "${tool}" -q -o "${work}/short.json" -l 1,700000 "${sample}" >/dev/null 2>&1
if python3 - "${work}/short.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
sys.exit(0 if d.get("subsetRequestedSamples") == 700000 and d.get("subsetActualSamples") == 300000 else 1)
PY
then
	note "short final block recorded:" "requested 700000, actual 300000"
else
	note "short final block recorded:" "not recorded"
	fails=$((fails + 1))
fi

# sha256 must identify the exact assessed subset. For block zero this happens
# to equal the file hash, but the scope and count make that meaning explicit.
whole=$(shasum -a 256 "${sample}" 2>/dev/null | cut -d' ' -f1)
[ -n "${whole}" ] || whole=$(sha256sum "${sample}" | cut -d' ' -f1)
got=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('sha256',''))" "${work}/ok.json")
scope=$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d.get('sha256Scope',''),d.get('assessedSampleCount',''))" "${work}/ok.json")
if [ "${got}" = "${whole}" ] && [ "${scope}" = "assessed-sample-bytes 1000000" ]; then
	note "sha256 identifies assessed block zero:" "yes"
else
	note "sha256 identifies assessed block zero:" "wrong (${got}; ${scope})"
	fails=$((fails + 1))
fi

# The short block's digest must be the trailing 300,000 assessed bytes, not
# the whole-file digest from a separate pathname read.
tail -c 300000 "${sample}" >"${work}/tail.bin"
tail_hash=$(shasum -a 256 "${work}/tail.bin" 2>/dev/null | cut -d' ' -f1)
[ -n "${tail_hash}" ] || tail_hash=$(sha256sum "${work}/tail.bin" | cut -d' ' -f1)
short_hash=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('sha256',''))" "${work}/short.json")
if [ "${short_hash}" = "${tail_hash}" ]; then
	note "short-block hash binds consumed bytes:" "yes"
else
	note "short-block hash binds consumed bytes:" "got '${short_hash}'"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-subset: PASS"
	exit 0
fi
echo "regression-subset: FAIL (${fails} checks)"
exit 1
