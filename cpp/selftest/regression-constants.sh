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
# THE C22c FAMILY VALUES ARE PINNED BY DIGEST, NOT BY VALUE (OC-125). This
# file used to carry all six of them as literals:
#
#     "C22C 1e6 compression": "3.3599e-3",   ... and five more
#
# which made it the sixth of seven places the same six numbers were recorded.
# One source for each family value is the rule now, and a literal here would
# break it. So what is recorded instead is a sha256 over the carried values in
# canonical form -- a hash, held OUTSIDE the file it covers, which is still a
# comparison of values rather than of markers while being one 64-character
# string. A mutation to any carried value changes it.
#
# Three distinct C22c checks, because they fail for three different reasons:
#
#   SHAPE     c22c_source.py --validate: every stamp present, every stamp's
#             derivation still at the sha256 the value was stamped against,
#             every value at the declared precision. Milliseconds.
#   VALUES    the digest. Detects a drift in a carried number.
#   WIRING    the floor's effective C22C_FAMILIES_BY_N must EQUAL what the
#             source says. This is the one that catches a floor rewired back
#             to literals of its own, which the digest and the shape check
#             would both pass.
#
# Re-deriving the numbers is a separate, slow check: c22c_derive.py, run on
# demand and by .github/workflows/c22c-source-check.yml. A forty-second
# derivation does not belong in a suite that has to stay fast.
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
EXPECT_DIGEST="0345092696b52c91a99efa8af422807a30de1230d538d01ccd41422727cbdea7"
EXPECT_DIGEST_LINES=4
out=$(FLOORPATH="${FLOOR}" WANT_DIGEST="${EXPECT_DIGEST}" \
      WANT_DIGEST_LINES="${EXPECT_DIGEST_LINES}" python3 - <<'PY'
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("floor", os.environ["FLOORPATH"])
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except BaseException as e:            # a SystemExit from argv parsing is fine
    if not isinstance(e, SystemExit):
        print("IMPORTFAIL %s" % e); raise SystemExit(0)
# RECORDED VALUES. C22A_PER_N is recorded here because it has only ever had
# one home; the C22c family values are NOT, for the reason in the header.
WANT = {"C22A_PER_N": "8.08e-15"}
got = {"C22A_PER_N": repr(getattr(m, "C22A_PER_N", None))}
for k, want in WANT.items():
    g = got.get(k)
    ok = (g is not None) and (float(g) == float(want))
    print("%s|%s|%s|%s" % ("OK" if ok else "DIFF", k, want, g))

# ---- C22c: shape, then values by digest, then the wiring -------------------
sys.path.insert(0, os.path.dirname(os.environ["FLOORPATH"]))
try:
    import c22c_source as SRC
except Exception as e:
    print("DIFF|C22c source module|importable|%s" % e)
    raise SystemExit(0)
try:
    SRC.validate()
    print("OK|C22c source shape|stamped and well-formed|validated")
except Exception as e:
    print("DIFF|C22c source shape|stamped and well-formed|%s" % e)
    raise SystemExit(0)
try:
    digest, canon = SRC.values_digest()
    lines = len(canon.splitlines())
except Exception as e:
    print("DIFF|C22c values digest|computable|%s" % e)
    raise SystemExit(0)
print("%s|C22c values digest|%s|%s"
      % ("OK" if digest == os.environ["WANT_DIGEST"] else "DIFF",
         os.environ["WANT_DIGEST"], digest))
print("%s|C22c values covered by the digest|%s|%s"
      % ("OK" if str(lines) == os.environ["WANT_DIGEST_LINES"] else "DIFF",
         os.environ["WANT_DIGEST_LINES"], lines))

# THE WIRING. The floor must be using the source's numbers, not numbers of its
# own that happen to be right today. Compared as floats, exactly, because that
# is what gets subtracted.
src_fam = dict(SRC.families_by_n())
floor_fam = dict(getattr(m, "C22C_FAMILIES_BY_N", ()))
for n in sorted(src_fam, reverse=True):
    for key in SRC.FAMILIES_ALL:
        want_v = src_fam[n].get(key)
        got_v = floor_fam.get(n, {}).get(key)
        ok = (got_v is not None) and (repr(got_v) == repr(want_v))
        print("%s|C22c wiring n=%d %s|%r|%r"
              % ("OK" if ok else "DIFF", n, key, want_v, got_v))
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

# AN EMPTY READ IS NOT A PASS, AND NEITHER IS A SHORT ONE (SHAPE-03). The
# expected SET is declared, not a count: a check that agrees with whatever it
# was given is a defect, and a count alone cannot say WHICH row went missing.
EXPECT_KEYS="C22A_PER_N
C22c source shape
C22c values digest
C22c values covered by the digest
C22c wiring n=8000000 collision
C22c wiring n=8000000 compression
C22c wiring n=8000000 proportion
C22c wiring n=1000000 collision
C22c wiring n=1000000 compression
C22c wiring n=1000000 proportion"
got_keys=$(printf '%s\n' "${out}" | awk -F'|' '/^(OK|DIFF)\|/ {print $2}' | sort)
want_keys=$(printf '%s\n' "${EXPECT_KEYS}" | sort)
if [ "${got_keys}" != "${want_keys}" ]; then
    bad "the set of constants compared is not the expected set" \
        "$(printf '%s\n' "${EXPECT_KEYS}" | wc -l | tr -d ' ') expected, ${n_checked} seen"
    miss=$(comm -23 <(printf '%s\n' "${want_keys}") <(printf '%s\n' "${got_keys}"))
    extra=$(comm -13 <(printf '%s\n' "${want_keys}") <(printf '%s\n' "${got_keys}"))
    [ -n "${miss}" ]  && printf '        missing:    %s\n' "$(printf '%s' "${miss}" | tr '\n' ';')"
    [ -n "${extra}" ] && printf '        unexpected: %s\n' "$(printf '%s' "${extra}" | tr '\n' ';')"
fi

# ---- ONE SOURCE for each family value, swept, with its own control ---------
SWEEP="${repo}/audits/2026-10-11-independent-audit/oracles/c22c-copy-sweep.sh"
if [ -x "${SWEEP}" ] || [ -r "${SWEEP}" ]; then
    if sweep_out=$(bash "${SWEEP}" 2>&1); then
        note "one source per family value (swept, with control)" "no second copy"
    else
        bad "a SECOND COPY of a C22c family value exists" "c22c-copy-sweep.sh FAILED"
        printf '%s\n' "${sweep_out}" | sed -n '/FAIL/,$p' | head -20 | sed 's/^/        /'
    fi
else
    bad "the one-source sweep is missing:" "${SWEEP}"
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
    echo "regression-constants: PASS (${n_checked} constants, the C22c digest, the sweep, the manifest)"
    exit 0
fi
echo "regression-constants: FAIL (${fails})"
exit 1
