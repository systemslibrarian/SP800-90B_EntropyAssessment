#!/bin/bash
#
# OC-121: no mutated constant survives in the floor oracle or the pinned
# manifests. Runs LAST in the suite.
#
# WHY. A mutation battery killed mid-arm left a LIVE C22c MUTATION in
# entropy_floor.py -- 3.3599e-3 -> 3.3700e-3, the constant every entropy figure
# in this project subtracts. Nothing downstream announced it. It was caught by
# `git status`, which is not a check and is not run by anything.
#
# WHY IT COMPARES VALUES AND NOT MARKERS. A marker search -- grep for
# "MUTATED" or similar -- passes trivially against a mutation that removed its
# own marker, which is every mutation this repository's batteries perform:
# they substitute one numeric literal for another and leave no marker at all.
# So this reads the constants OUT and compares them to recorded values.
#
# WHY NOT `git diff`. Because a mutation that was COMMITTED would pass a
# working-tree diff, and because this must also hold in a release tarball with
# no git history. The values are recorded here, in this file.
#
# EXIT  0 all constants match   1 a constant differs   2 could not run

set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
FLOOR="${repo}/audits/2026-10-11-independent-audit/oracles/entropy_floor.py"
MANIFEST="${here}/known-platform-deltas.txt"
fails=0
note() { printf '  %-56s %s\n' "$1" "$2"; }
bad()  { note "$1" "$2"; fails=$((fails + 1)); }

command -v python3 >/dev/null 2>&1 || {
    echo "regression-constants: python3 not on PATH; cannot read the constants" >&2
    exit 2; }
[ -r "${FLOOR}" ] || { echo "regression-constants: ${FLOOR} unreadable" >&2; exit 2; }

# ---- the floor's constants, read out of the module rather than grepped ------
# Importing it means a syntax error or a renamed symbol is a FAILURE here
# rather than a silent pass, which a grep could not distinguish.
out=$(FLOORPATH="${FLOOR}" python3 - <<'PY'
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("floor", os.environ["FLOORPATH"])
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except BaseException as e:            # a SystemExit from argv parsing is fine
    if not isinstance(e, SystemExit):
        print("IMPORTFAIL %s" % e); raise SystemExit(0)
# RECORDED VALUES. Each is a figure the published floor subtracts or reports.
WANT = {
    "C22A_PER_N":      "8.08e-15",
    "C22C 1e6 compression": "3.3599e-3",
    "C22C 1e6 collision":   "7.84e-4",
    "C22C 1e6 proportion":  "6.887e-5",
    "C22C 8e6 compression": "2.1644e-3",
    "C22C 8e6 collision":   "4.66e-4",
    "C22C 8e6 proportion":  "6.887e-5",
}
got = {}
got["C22A_PER_N"] = repr(getattr(m, "C22A_PER_N", None))
fam = dict(getattr(m, "C22C_FAMILIES_BY_N", ()))
for n, tag in ((10**6, "1e6"), (8 * 10**6, "8e6")):
    d = fam.get(n, {})
    for key in ("compression", "collision", "proportion"):
        got["C22C %s %s" % (tag, key)] = repr(d.get(key))
for k, want in WANT.items():
    g = got.get(k)
    ok = (g is not None) and (float(g) == float(want))
    print("%s|%s|%s|%s" % ("OK" if ok else "DIFF", k, want, g))
PY
)
rc=$?
if [ "${rc}" -ne 0 ] || [ -z "${out}" ]; then
    echo "regression-constants: could not read the floor's constants" >&2
    exit 2
fi
if printf '%s\n' "${out}" | grep -q '^IMPORTFAIL'; then
    bad "the floor oracle does not import:" "$(printf '%s\n' "${out}" | head -1)"
fi
n_checked=0
while IFS='|' read -r verdict key want got; do
    [ "${verdict}" = OK ] || [ "${verdict}" = DIFF ] || continue
    n_checked=$((n_checked + 1))
    if [ "${verdict}" = OK ]; then
        note "${key}" "${want}"
    else
        bad "${key} HAS BEEN CHANGED" "recorded ${want}, found ${got}"
    fi
done <<EOF
${out}
EOF

# An empty read is not a pass (SHAPE-03): declare the floor.
if [ "${n_checked}" -lt 7 ]; then
    bad "constants actually compared:" "${n_checked}, expected at least 7"
fi

# ---- the platform manifest's tolerances -----------------------------------
if [ -r "${MANIFEST}" ]; then
    rows=$(grep -c '^delta ' "${MANIFEST}" || true)
    tols=$(grep '^delta ' "${MANIFEST}" | awk -F'|' '{print $4}' | sort -u | tr '\n' ' ')
    if [ "${rows}" -eq 8 ] && [ "${tols}" = "1e-9 " ]; then
        note "platform manifest: 8 rows, all tolerance 1e-9" "unchanged"
    else
        bad "the platform manifest's shape changed" "${rows} rows, tolerances: ${tols}"
    fi
else
    bad "the platform manifest is unreadable:" "${MANIFEST}"
fi

echo
if [ "${fails}" -eq 0 ]; then
    echo "regression-constants: PASS (${n_checked} floor constants + the manifest)"
    exit 0
fi
echo "regression-constants: FAIL (${fails})"
exit 1
