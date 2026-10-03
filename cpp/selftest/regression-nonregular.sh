#!/bin/bash
#
# Fork hardening regression, upstream #259.
#
# No NIST account has replied to #259. The upstream respondent there is
# @joshuaehill (Joshua E. Hill, KeyPair Consulting), who is not a NIST account:
# "I'm not sure this is a bug, it's more of an observation that when the user
# does wildly wrong things, marginally bad stuff might occur." It is fixed here
# anyway because a tool that hangs forever on a mistyped path is awkward to
# drive from a harness. This test exists so the hardening is not lost, not as
# evidence of a standards defect.
#
# sha256_file read to EOF before any size check, so a character device never
# ended the loop; a FIFO blocked even earlier, inside fopen. The file type is
# now established from the path before the file is opened.
#
# Also covers N-06 for ea_iid, and REV-006's sustained half. The stat/S_ISREG
# check and the status check both live in the SHARED sha256_file
# (cpp/shared/TestRunUtils.h), so every program that calls it is affected, but
# this script used to assert ea_iid merely EXISTED and then exercise only
# ea_non_iid. The independent re-audit of 2026-10-01 confirmed that gap: an
# ea_iid build that ignores sha256_file's status passed the whole script. The
# ea_restart half is covered by regression-restart.sh's N-06 block, whose
# JSON assertions this file follows deliberately. Both tools are now run for
# every case, and an unhashable input must be refused with errorLevel set and
# no sha256 invented. Observed to fail against an ea_iid rebuilt with the
# status check removed.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regnr.XXXXXX") || exit 2
trap 'rm -f "${work}/fifo"; rm -rf "${work}"' EXIT

fails=0
skipped=0
note() { printf '%-44s %s\n' "$1" "$2"; }

TOOLS="ea_non_iid ea_iid"

refuses_promptly() { # refuses_promptly <label> <path>
	local label=$1 path=$2 out rc tool
	for tool in ${TOOLS}; do
		out=$(timeout 10 "${here}/../${tool}" -q "${path}" 2>&1); rc=$?
		if [ "${rc}" -eq 124 ]; then
			note "${tool} ${label}:" "TIMED OUT — still hangs"
			fails=$((fails + 1))
		elif [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q 'not a regular file'; then
			note "${tool} ${label}:" "refused promptly"
		else
			note "${tool} ${label}:" "exit ${rc}, expected a prompt refusal"
			fails=$((fails + 1))
		fi
	done
}

# N-06 / REV-006: a file that cannot be hashed must stop the run, and no
# sha256 may appear in the report. Same assertions as regression-restart.sh's
# N-06 block, applied to the two programs this script covers.
refuses_unhashable() { # refuses_unhashable <label> <path>
	local label=$1 path=$2 rc tool
	for tool in ${TOOLS}; do
		rm -f "${work}/nf.json"
		timeout 10 "${here}/../${tool}" -q -o "${work}/nf.json" "${path}" 8 >/dev/null 2>&1
		rc=$?
		if [ "${rc}" -eq 0 ]; then
			note "${tool} ${label} exits nonzero:" "exit 0 — the run continued"
			fails=$((fails + 1))
			continue
		fi
		if python3 - "${work}/nf.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
# errorLevel must be set, and no sha256 may be reported for a file that
# could not be hashed. An uninitialised buffer sometimes reads as empty, so
# a present-but-empty field is accepted here and a present value is not.
sys.exit(0 if d.get("errorLevel", 0) != 0 and not d.get("sha256") else 1)
PY
		then
			note "${tool} ${label} no hash invented:" "errorLevel set, sha256 absent"
		else
			note "${tool} ${label} no hash invented:" "report is wrong or absent"
			fails=$((fails + 1))
		fi
	done
}

for tool in ${TOOLS}; do
	[ -x "${here}/../${tool}" ] || { echo "regression-nonregular: ${tool} missing" >&2; exit 2; }
done

if [ -c /dev/zero ]; then refuses_promptly "character device /dev/zero" /dev/zero
else note "character device:" "skipped (no /dev/zero)"; skipped=$((skipped + 1)); fi

if [ -c /dev/urandom ]; then refuses_promptly "character device /dev/urandom" /dev/urandom
else note "character device /dev/urandom:" "skipped"; skipped=$((skipped + 1)); fi

if mkfifo "${work}/fifo" 2>/dev/null; then refuses_promptly "FIFO" "${work}/fifo"
else note "FIFO:" "skipped (mkfifo unavailable)"; skipped=$((skipped + 1)); fi

refuses_promptly "directory" "${work}"

refuses_unhashable "absent file" "${work}/absent.bin"

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
