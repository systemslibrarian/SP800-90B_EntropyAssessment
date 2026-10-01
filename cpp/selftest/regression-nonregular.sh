#!/bin/bash
#
# Fork hardening regression, upstream #259.
#
# NIST does not regard this as a defect: @joshuaehill on #259, "I'm not sure
# this is a bug, it's more of an observation that when the user does wildly
# wrong things, marginally bad stuff might occur." It is fixed here anyway
# because a tool that hangs forever on a mistyped path is awkward to drive from
# a harness. This test exists so the hardening is not lost, not as evidence of
# a standards defect.
#
# sha256_file read to EOF before any size check, so a character device never
# ended the loop; a FIFO blocked even earlier, inside fopen. The file type is
# now established from the path before the file is opened.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regnr.XXXXXX") || exit 2
trap 'rm -f "${work}/fifo"; rm -rf "${work}"' EXIT

fails=0
skipped=0
note() { printf '%-44s %s\n' "$1" "$2"; }

refuses_promptly() { # refuses_promptly <label> <path>
	local label=$1 path=$2 out rc
	out=$(timeout 10 "${here}/../ea_non_iid" -q "${path}" 2>&1); rc=$?
	if [ "${rc}" -eq 124 ]; then
		note "${label}:" "TIMED OUT — still hangs"
		fails=$((fails + 1))
	elif [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'not a regular file'; then
		note "${label}:" "refused promptly"
	else
		note "${label}:" "exit ${rc}, expected a prompt refusal"
		fails=$((fails + 1))
	fi
}

for tool in ea_non_iid ea_iid; do
	[ -x "${here}/../${tool}" ] || { echo "regression-nonregular: ${tool} missing" >&2; exit 2; }
done

if [ -c /dev/zero ]; then refuses_promptly "character device /dev/zero" /dev/zero
else note "character device:" "skipped (no /dev/zero)"; skipped=$((skipped + 1)); fi

if [ -c /dev/urandom ]; then refuses_promptly "character device /dev/urandom" /dev/urandom
else note "character device /dev/urandom:" "skipped"; skipped=$((skipped + 1)); fi

if mkfifo "${work}/fifo" 2>/dev/null; then refuses_promptly "FIFO" "${work}/fifo"
else note "FIFO:" "skipped (mkfifo unavailable)"; skipped=$((skipped + 1)); fi

refuses_promptly "directory" "${work}"

# A regular file must still be hashed and assessed.
got=$("${here}/../ea_non_iid" -vv "${repo}/bin/ringOsc-nist.bin" 2>/dev/null | sed -n 's/.*SHA-256 hash \([0-9a-f]\{64\}\).*/\1/p' | head -1)
if [ "${got}" = "7d37dc3795e9b2927beb779008d7f4b4630dd7f2c058a2b14cee9d41a658dd68" ]; then
	note "regular file still hashed:" "hash unchanged"
else
	note "regular file still hashed:" "got '${got}'"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-nonregular: PASS${skipped:+ (${skipped} skipped)}"
	exit 0
fi
echo "regression-nonregular: FAIL (${fails} checks)"
exit 1
