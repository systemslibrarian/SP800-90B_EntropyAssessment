#!/bin/bash
#
# Claims check for the living documentation.
#
# The code in this fork has regression tests; the prose did not, and it drifted
# out of true twice. Both times the documentation still told a reader the fork
# was unmodified after it had been modified, and both times a narrow grep for a
# remembered phrasing missed it. This script checks the claims that can be
# checked mechanically, so the next drift fails a test instead of needing to be
# noticed.
#
# Living documents only. Everything under audits/2026-09-30/novel-findings/,
# phase2-focused/ and AUDIT.md is evidence captured on a date and is not
# checked here: those statements are scoped to a past commit and are supposed
# to stay as they were.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
cd "${repo}" || exit 2

DOCS="README.md NOTICE BUILDING.md audits/README.md audits/BUG-REPAIR-GUIDE.md audits/2026-09-30/README.md audits/2026-09-30/FINDINGS-TRACKER.md"
TRACKER=audits/2026-09-30/FINDINGS-TRACKER.md

fails=0
note() { printf '  %-52s %s\n' "$1" "$2"; }
bad()  { note "$1" "$2"; fails=$((fails + 1)); }

# ---------------------------------------------------------------- 1. SHAs
missing=""
# Taken from the fields that actually assert a commit. Scanning for bare hex
# instead would also catch SHA-256 prefixes of data files and the mantissa of
# numbers like 1.44440015503733e-13, neither of which is a commit.
shas=$( { grep -ohE 'Commit [0-9a-f]{7,40}\.' NOTICE | sed 's/^Commit //; s/\.$//'
          grep -ohE '^- \*\*Fork fix commit:\*\* `[0-9a-f]{7,40}`' "${TRACKER}" | grep -ohE '[0-9a-f]{7,40}'
          grep -ohE '`87c104d[0-9a-f]*`' NOTICE "${TRACKER}" | tr -d '`'
        } | sort -u )
for h in ${shas}; do
    git cat-file -e "${h}^{commit}" 2>/dev/null || missing="${missing} ${h}"
done
if [ -z "${missing}" ]; then note "every commit SHA in NOTICE and the tracker resolves:" "yes"
else bad "commit SHAs that do not resolve:" "${missing}"; fi

# -------------------------------------------------------- 2. referenced paths
missing=""
for f in $(grep -ohE '`[A-Za-z0-9_][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]+\.(sh|py|cpp|h|md|pl|txt|pdf)`' ${DOCS} | tr -d '`' | sort -u); do
    [ -e "${f}" ] && continue
    find . -path ./.git -prune -o -path "*/${f}" -print 2>/dev/null | grep -q . && continue
    # A path the documentation explicitly describes as a former or original
    # location is supposed to be absent; that is the point of saying it moved.
    if grep -h -- "${f}" ${DOCS} 2>/dev/null \
         | grep -qiE "original path|exists only on|was moved|moved from|former|renamed"; then
        continue
    fi
    missing="${missing} ${f}"
done
if [ -z "${missing}" ]; then note "every repo path referenced in the docs exists:" "yes"
else bad "referenced paths that do not exist:" "${missing}"; fi

# ------------------------------------------------- 3. markdown link targets
missing=""
for l in $(grep -ohE '\]\([A-Za-z0-9_][A-Za-z0-9_./-]*\.(md|sh|pdf|txt)\)' ${DOCS} | sed 's/^](//; s/)$//' | sort -u); do
    found=0
    for d in . audits audits/2026-09-30; do [ -e "${d}/${l}" ] && found=1; done
    [ "${found}" -eq 0 ] && missing="${missing} ${l}"
done
if [ -z "${missing}" ]; then note "every local markdown link target resolves:" "yes"
else bad "markdown links that do not resolve:" "${missing}"; fi

# -------------------------------------------- 4. regressions the tracker names
missing=""
for f in $(grep -oE 'cpp/selftest/regression-[a-z0-9-]+\.sh' "${TRACKER}" | sort -u); do
    [ -f "${f}" ] || missing="${missing} ${f}"
done
if [ -z "${missing}" ]; then note "every regression the tracker names exists:" "yes"
else bad "regressions named but absent:" "${missing}"; fi

# --------------------------------- 5. tracker counts match the tracker itself
mismatch=""
for st in NEEDS-FIX UPSTREAM-FIX-PENDING FIXED-UPSTREAM-VERIFY FORK-FIX-REQUIRED FORK-FIXED VERIFIED; do
    claimed=$(grep -oE "^  - \`${st}\`: [0-9]+" "${TRACKER}" | grep -oE '[0-9]+$' | head -1)
    [ -z "${claimed}" ] && continue
    actual=$(grep -cE "^- \*\*State:\*\* \`${st}\`" "${TRACKER}")
    [ "${claimed}" = "${actual}" ] || mismatch="${mismatch} ${st}(says ${claimed}, is ${actual})"
done
total=$(grep -cE '^- \*\*State:\*\*' "${TRACKER}")
claimed_total=$(grep -oE 'Confirmed defects: \*\*[0-9]+\*\*' "${TRACKER}" | grep -oE '[0-9]+' | head -1)
[ "${total}" = "${claimed_total}" ] || mismatch="${mismatch} total(says ${claimed_total}, is ${total})"
if [ -z "${mismatch}" ]; then note "tracker counts match its own sections:" "yes (${total} findings)"
else bad "tracker count mismatches:" "${mismatch}"; fi

# ------------------------------------------- 6. the pinned value is one value
pinned=$(sed -n 's/^EXPECTED=//p' "${here}/pin-check.sh" | head -1)
if [ -z "${pinned}" ]; then bad "pinned value readable from pin-check.sh:" "not found"
else
    # Two values are legitimate: pin-check.sh's EXPECTED, which is NIST's
    # Linux reference, and whatever this build actually produces, which the
    # docs quote as this platform's figure. Anything else is drift.
    observed=""
    # This script runs from the repository root, so the paths are repo-relative.
    [ -x cpp/ea_non_iid ] && observed=$(cpp/ea_non_iid -vv bin/ringOsc-nist.bin 2>/dev/null \
        | sed -n 's/^Assessed min entropy: //p' | head -1)
    wrong=""
    for d in ${DOCS}; do
        for v in $(grep -ohE '0\.12644573619[0-9]+' "${d}" | sort -u); do
            [ "${v}" = "${pinned}" ] && continue
            [ -n "${observed}" ] && [ "${v}" = "${observed}" ] && continue
            wrong="${wrong} ${d}:${v}"
        done
    done
    if [ -z "${wrong}" ]; then
        note "pinned figures quoted in docs are consistent:" "reference ${pinned}, this build ${observed:-unbuilt}"
    else bad "pinned figures matching neither reference nor build:" "${wrong}"; fi
fi

# ------------------------------------------------------- 7. LGPL isolation
leak=""
for b in cpp/ea_non_iid cpp/ea_iid cpp/ea_restart; do
    [ -x "${b}" ] || continue
    n=$( { otool -L "${b}" 2>/dev/null || ldd "${b}" 2>/dev/null; } | grep -ci -E 'mpfr|gmp')
    m=$(nm -u "${b}" 2>/dev/null | grep -c -E '_mpfr|gmp')
    [ "${n}" = "0" ] && [ "${m}" = "0" ] || leak="${leak} ${b}"
done
cond=$(grep -c 'COND_LIB' cpp/Makefile)
if [ -z "${leak}" ] && [ "${cond}" -ge 1 ]; then note "no built program links MPFR or GMP:" "confirmed"
else bad "MPFR/GMP linkage found in:" "${leak}"; fi

# ------------------------- 8. claims that were false before must not reappear
# Each of these was in the documentation after the fork had been modified, and
# each had to be corrected. They are listed verbatim so a reintroduction fails.
STALE_CLAIMS=(
 "Nothing that affects a reported min-entropy figure has been changed"
 "builds and ships only"
 "without changing anything that can alter a reported min-entropy"
 "set of estimators that run are exactly upstream"
 "Only ea_non_iid is built and distributed"
 "Only \`ea_non_iid\` is built and shipped"
 "No reported min-entropy figure changes for any dataset"
 "No semantics-preserving optimisation was found"
)
hit=""
for c in "${STALE_CLAIMS[@]}"; do
    for d in ${DOCS}; do
        grep -F -q "${c}" "${d}" 2>/dev/null && hit="${hit} ${d}:\"${c}\""
    done
done
# "are identical to upstream" is only wrong unqualified; the negated and
# commit-scoped forms are correct and must not trip this.
for d in ${DOCS}; do
    grep -nE "(sources|files)[^.]{0,40}are identical to upstream" "${d}" 2>/dev/null \
        | grep -viE "no longer|were identical" | grep -q . && hit="${hit} ${d}:unqualified-identical-claim"
done
if [ -z "${hit}" ]; then note "no previously-corrected claim has reappeared:" "none"
else bad "stale claims present again:" "${hit}"; fi

echo
if [ "${fails}" -eq 0 ]; then echo "regression-docs: PASS"; exit 0; fi
echo "regression-docs: FAIL (${fails} checks)"
exit 1
