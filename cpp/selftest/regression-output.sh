#!/bin/bash
#
# Regression for N-09 and for C14 (audit OC-31): a report that cannot be
# written must fail the run, a stale report must never survive a failed run,
# and --version must not be honoured as a filename.
#
# REGRESSION_OUTPUT_BINDIR points the checks at another build -- used to show
# them FAILING against the tag build unrepaired-reference-2026-10-15.
#
# Every JSON report write was an unchecked ofstream, so "-o /dev/full" or a
# path in a directory that does not exist produced no file and exited 0. A
# caller that reads the exit status and then opens the report would read a
# stale file, or none, believing the run had succeeded.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
bindir="${REGRESSION_OUTPUT_BINDIR:-${here}/..}"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regout.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
skipped=0
note() { printf '%-52s %s\n' "$1" "$2"; }

python3 -c "
import random, sys
r = random.Random(8)
open(sys.argv[1], 'wb').write(bytes(r.randrange(256) for _ in range(1000000)))
" "${work}/r8.bin"

# run <label> <expect-ok|expect-fail> <tool> <args...>
check_fail() {
	local label=$1; shift
	local out rc
	out=$("$@" 2>&1 >/dev/null); rc=$?
	if [ "${rc}" -ge 128 ] && [ "${rc}" -le 160 ]; then
		note "${label}:" "CRASHED (signal, exit ${rc})"
		fails=$((fails + 1))
	elif [ "${rc}" -ne 0 ] && printf '%s' "${out}" | grep -q "output file"; then
		note "${label}:" "refused (exit ${rc})"
	else
		note "${label}:" "exit ${rc}, expected a refusal naming the output file"
		fails=$((fails + 1))
	fi
}

for pair in "ea_non_iid:${repo}/bin/truerand_1bit.bin 1" "ea_iid:${repo}/bin/truerand_1bit.bin 1"; do
	tool=${pair%%:*}; args=${pair#*:}
	[ -x "${bindir}/${tool}" ] || { echo "regression-output: ${tool} missing" >&2; exit 2; }
	if [ -c /dev/full ]; then
		check_fail "${tool} -o /dev/full" "${bindir}/${tool}" -o /dev/full ${args}
	else
		note "${tool} -o /dev/full:" "skipped (no /dev/full)"; skipped=$((skipped + 1))
	fi
	check_fail "${tool} -o into a missing directory" "${bindir}/${tool}" -o "${work}/no_such_dir/x.json" ${args}
done

[ -x "${bindir}/ea_restart" ] || { echo "regression-output: ea_restart missing" >&2; exit 2; }
if [ -c /dev/full ]; then
	check_fail "ea_restart -o /dev/full" "${bindir}/ea_restart" -n -o /dev/full "${work}/r8.bin" 8 3.2/symbol
else
	note "ea_restart -o /dev/full:" "skipped (no /dev/full)"; skipped=$((skipped + 1))
fi
check_fail "ea_restart -o into a missing directory" "${bindir}/ea_restart" -n -o "${work}/no_such_dir/x.json" "${work}/r8.bin" 8 3.2/symbol

# A writable path must still work and produce a non-empty report.
for t in "ea_non_iid:${repo}/bin/truerand_1bit.bin 1" "ea_restart:-n ${work}/r8.bin 8 3.2/symbol"; do
	tool=${t%%:*}; args=${t#*:}
	out="${work}/${tool}.json"
	if "${bindir}/${tool}" -q -o "${out}" ${args} >/dev/null 2>&1 && [ -s "${out}" ]; then
		note "${tool} writable -o still works:" "wrote $(wc -c < "${out}" | tr -d ' ') bytes"
	else
		note "${tool} writable -o still works:" "failed or empty"
		fails=$((fails + 1))
	fi
done

echo
# ---------------------------------------------------------------- C14 route 1
# A stale -o report must never survive a failed run (XR-01 / oac-4). Writing an
# error report on every failure path cannot close this: a usage-path exit, an
# assert or a signal reaches none of them. The target is claimed with a
# fail-closed placeholder when -o is parsed, so after ANY run the file is this
# run's report or a report saying the assessment did not complete.
good="${work}/c14-good.json"
if ! OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}" "${bindir}/ea_non_iid" -q -o "${good}" "${repo}/bin/truerand_1bit.bin" 1 >/dev/null 2>&1; then
	note "C14 baseline good run wrote a report:" "FAILED to produce one"; fails=$((fails + 1))
else
	for t in ea_non_iid ea_iid ea_restart; do
		stale="${work}/c14-stale-${t}.json"
		cp "${good}" "${stale}"
		# A usage-path exit AFTER -o is parsed: no arguments follow, so the tool
		# prints usage and exits without ever reaching the report writer.
		"${bindir}/${t}" -o "${stale}" >/dev/null 2>&1; rc=$?
		if [ "${rc}" -eq 0 ]; then
			note "C14 ${t} usage path exits nonzero:" "exited 0"; fails=$((fails + 1))
		fi
		if cmp -s "${stale}" "${good}"; then
			note "C14 ${t} leaves no stale report:" "STALE -- the previous run's report survived byte-identical"
			fails=$((fails + 1))
		elif python3 - "${stale}" <<-'PY'
			import json, sys
			try: d = json.load(open(sys.argv[1]))
			except Exception: sys.exit(1)
			sys.exit(0 if (d.get('errorLevel') != 0 and not (d.get('testCases') or [])) else 1)
			PY
		then
			note "C14 ${t} leaves no stale report:" "replaced by a fail-closed report"
		else
			note "C14 ${t} leaves no stale report:" "the file is neither stale nor a valid error report"
			fails=$((fails + 1))
		fi
	done
fi

# ---------------------------------------------------------------- C14 route 2
# --version is documented as an option. It was matched anywhere in argv,
# including argv[0] and the input filename, so a file named "--version" made the
# tool print its version and exit 0 with nothing assessed and no report (oac-16).
vdir="${work}/vdir"; mkdir -p "${vdir}"
cp "${repo}/bin/truerand_1bit.bin" "${vdir}/--version"
# The input to this check is a VALUE -- the exact operand string -- so the
# landing assertion is that the tool received it, read back from the tool
# itself, never from the harness's own variable. The first version of this
# check passed "./--version" where the code matches "--version"; it passed
# against the build it was meant to fail and proved nothing (OC-31). A run
# that cannot be shown to have received the string reports
# INPUT-DID-NOT-REACH-THE-TOOL, which is neither a pass nor a fail for the
# guard: see mutation-lib.sh for why that third outcome exists.
[ -f "${vdir}/--version" ] || { note "C14 setup: a file named --version exists:" "it does not"; fails=$((fails + 1)); }
for t in ea_non_iid ea_iid; do
	out=$(cd "${vdir}" && EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}" \
		"${bindir}/${t}" -q -o "${work}/c14-v-${t}.json" -- "--version" 1 2>&1); rc=$?
	banner=0; printf '%s' "${out}" | grep -q 'Disclaimer: NIST-developed software' && banner=1
	received=0
	# The version banner is itself proof the string reached the scan. Otherwise
	# the tool's own recorded command line must contain it.
	if [ "${banner}" -eq 1 ]; then
		received=1
	elif [ -s "${work}/c14-v-${t}.json" ] && python3 - "${work}/c14-v-${t}.json" <<-'PY'
		import json, sys
		try: d = json.load(open(sys.argv[1]))
		except Exception: sys.exit(1)
		sys.exit(0 if '--version' in (d.get('commandline') or '') else 1)
		PY
	then
		received=1
	fi
	if [ "${received}" -eq 0 ]; then
		note "C14 ${t} does not take a filename as --version:" "INPUT-DID-NOT-REACH-THE-TOOL (rc ${rc}); the guard was not tested"
		fails=$((fails + 1))
	elif [ "${banner}" -eq 1 ]; then
		note "C14 ${t} does not take a filename as --version:" "printed the version and assessed nothing"
		fails=$((fails + 1))
	else
		note "C14 ${t} does not take a filename as --version:" "assessed the file (rc ${rc}), operand confirmed in the recorded command line"
	fi
done
# and the option itself must still work
for t in ea_non_iid ea_iid ea_restart; do
	out=$("${bindir}/${t}" --version 2>&1); rc=$?
	if [ "${rc}" -eq 0 ] && printf '%s' "${out}" | grep -q "1\.1\.8"; then
		note "C14 ${t} --version still works as an option:" "yes"
	else
		note "C14 ${t} --version still works as an option:" "rc ${rc}, output changed"
		fails=$((fails + 1))
	fi
done

if [ "${fails}" -eq 0 ]; then
	echo "regression-output: PASS${skipped:+ (${skipped} skipped)}"
	exit 0
fi
echo "regression-output: FAIL (${fails} checks)"
exit 1
