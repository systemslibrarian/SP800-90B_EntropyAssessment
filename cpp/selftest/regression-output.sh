#!/bin/bash
#
# Regression for N-09: a report that cannot be written must fail the run.
#
# Every JSON report write was an unchecked ofstream, so "-o /dev/full" or a
# path in a directory that does not exist produced no file and exited 0. A
# caller that reads the exit status and then opens the report would read a
# stale file, or none, believing the run had succeeded.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
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
	[ -x "${here}/../${tool}" ] || { echo "regression-output: ${tool} missing" >&2; exit 2; }
	if [ -c /dev/full ]; then
		check_fail "${tool} -o /dev/full" "${here}/../${tool}" -o /dev/full ${args}
	else
		note "${tool} -o /dev/full:" "skipped (no /dev/full)"; skipped=$((skipped + 1))
	fi
	check_fail "${tool} -o into a missing directory" "${here}/../${tool}" -o "${work}/no_such_dir/x.json" ${args}
done

[ -x "${here}/../ea_restart" ] || { echo "regression-output: ea_restart missing" >&2; exit 2; }
if [ -c /dev/full ]; then
	check_fail "ea_restart -o /dev/full" "${here}/../ea_restart" -n -o /dev/full "${work}/r8.bin" 8 3.2
else
	note "ea_restart -o /dev/full:" "skipped (no /dev/full)"; skipped=$((skipped + 1))
fi
check_fail "ea_restart -o into a missing directory" "${here}/../ea_restart" -n -o "${work}/no_such_dir/x.json" "${work}/r8.bin" 8 3.2

# A writable path must still work and produce a non-empty report.
for t in "ea_non_iid:${repo}/bin/truerand_1bit.bin 1" "ea_restart:-n ${work}/r8.bin 8 3.2"; do
	tool=${t%%:*}; args=${t#*:}
	out="${work}/${tool}.json"
	if "${here}/../${tool}" -q -o "${out}" ${args} >/dev/null 2>&1 && [ -s "${out}" ]; then
		note "${tool} writable -o still works:" "wrote $(wc -c < "${out}" | tr -d ' ') bytes"
	else
		note "${tool} writable -o still works:" "failed or empty"
		fails=$((fails + 1))
	fi
done

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-output: PASS${skipped:+ (${skipped} skipped)}"
	exit 0
fi
echo "regression-output: FAIL (${fails} checks)"
exit 1
