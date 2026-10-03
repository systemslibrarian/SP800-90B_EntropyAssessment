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

# --------------------------- 8. the quoted rate matches the measured table
# The permutation-cost rate was stated in ms where the measurements give
# seconds, a factor of 1000, while the run times derived from it were right.
# Recompute from the table in BUILDING.md rather than trusting the sentence.
rate_row=$(grep -oE '^\| 400,000 \| [0-9.]+ s \|' BUILDING.md | grep -oE '[0-9.]+ s' | grep -oE '[0-9.]+')
if [ -n "${rate_row}" ]; then
    want_s=$(python3 -c "print('%.2f' % (${rate_row} / 400000 * 1000))")
    if grep -q "${want_s} \*\*seconds\*\* per thousand bits" BUILDING.md; then
        note "quoted permutation rate matches the table:" "${want_s} s per thousand bits"
    else
        bad "quoted permutation rate does not match the table:" "table implies ${want_s} s per thousand bits"
    fi
else
    note "permutation rate check:" "skipped (table row not found)"
fi

# ------------------------- 9. claims that were false before must not reappear
# Each of these was in the documentation after the fork had been modified, and
# each had to be corrected. They are listed verbatim so a reintroduction fails.
#
# Matching normalises whitespace first. The previous version of this check
# matched line by line, and these documents are wrapped at about 72 columns, so
# the most load-bearing phrasings ("after NIST's review", "agreed with several
# of them") were split across two lines and could not be found: the guard read
# green against the exact sentences it had been added to block. That is the
# vacuous guard FINDINGS-TRACKER.md forbids ("a regression is assumed vacuous
# until it has failed"), so each phrase is now searched with \s+ between its
# words, which spans the wrap. Observed to fail against the wrapped sentence
# before this was committed.
STALE_CLAIMS=(
 "Nothing that affects a reported min-entropy figure has been changed"
 "builds and ships only"
 "without changing anything that can alter a reported min-entropy"
 "set of estimators that run are exactly upstream"
 "Only ea_non_iid is built and distributed"
 "Only \`ea_non_iid\` is built and shipped"
 "No reported min-entropy figure changes for any dataset"
 "No semantics-preserving optimisation was found"
 "it changed only from producing"
 "0.94 ms per thousand bits"
 "After NIST reviewed"
 "after NIST's review"
 "accepted by NIST"
 "NIST called"
 "pending NIST"
 "NIST-accepted"
 "put to NIST"
 "awaiting an answer"
 "agreed with several of them"
)
# A block that quotes the wrong wording while describing its correction is a
# record, not a reassertion. Exemption is judged over the whole paragraph the
# phrase sits in, not its line, for the same wrapping reason.
hit=$(python3 - "${DOCS}" "${STALE_CLAIMS[@]}" <<'PY'
import re, sys

docs   = sys.argv[1].split()
claims = sys.argv[2:]
# A correction note is recognised by explicit correction framing, not by a bare
# date. "until 2026-" alone was too loose: NOTICE's statement-of-changes
# paragraph opens "Until 2026-09-30 nothing outside the build files was
# touched", which would have exempted the very sentence this check exists to
# catch. The markers below all require a saying-verb or the word Correction.
EXEMPT = re.compile(r'Correction \(2026-|said "|still said|had been corrected'
                    r'|was headed|headed "|which those two contradict'
                    r'|factor of 1000|a prior session'
                    r'|until 2026-\d\d-\d\d[^.]{0,80}?(said|stated|read|headed|asserted|claimed)',
                    re.I)
hits = []

def paragraph(raw, a, b):
    s = raw.rfind('\n\n', 0, a); s = 0 if s < 0 else s + 2
    e = raw.find('\n\n', b);     e = len(raw) if e < 0 else e
    return raw[s:e]

for d in docs:
    try:
        raw = open(d, encoding='utf-8').read()
    except OSError:
        continue
    for c in claims:
        words = c.split()
        if not words:
            continue
        pat = re.compile(r'\s+'.join(map(re.escape, words)))
        for m in pat.finditer(raw):
            if EXEMPT.search(paragraph(raw, m.start(), m.end())):
                continue
            hits.append('%s:%d:"%s"' % (d, raw.count('\n', 0, m.start()) + 1, c))
    # "are identical to upstream" is only wrong unqualified; the negated and
    # commit-scoped forms are correct and must not trip this.
    for m in re.finditer(r'(sources|files)[^.]{0,40}are\s+identical\s+to\s+upstream', raw):
        if re.search(r'no longer|were identical', paragraph(raw, m.start(), m.end()), re.I):
            continue
        hits.append('%s:%d:unqualified-identical-claim' % (d, raw.count('\n', 0, m.start()) + 1))

print(' '.join(hits))
PY
)
if [ -z "${hit}" ]; then note "no previously-corrected claim has reappeared:" "none"
else bad "stale claims present again:" "${hit}"; fi

# ------------------------------- 10. NIST attributions in cpp/ comments
# Every reply on this fork's upstream issues and pull requests came from
# @joshuaehill, who is not a NIST account and who deferred to "the NIST folks"
# on PR #268. The 2026-10-02 sweep corrected the documents; three comments
# under cpp/ were missed, and this script did not look there, so README.md
# could claim the sweep was complete while it was not. Source comments are read
# as evidence too, so they are held to the same rule. A block that says "not a
# NIST account" is recording the distinction, not asserting a NIST position.
nistsrc=$(python3 - <<'PY'
import glob, os, re

files = sorted(set(
    glob.glob('cpp/*.cpp') + glob.glob('cpp/*.h') + glob.glob('cpp/*/*.h')
    + glob.glob('cpp/selftest/*.sh')
    + ['cpp/Makefile', 'cpp/selftest/selftest', 'cpp/selftest/compareresults.pl',
       'cpp/selftest/generate-refdata']))

# This script is the one file that must contain the forbidden phrasings: they
# are its data. It is therefore the single exclusion, and a NIST attribution
# written into this file would not be caught here.
files = [f for f in files if os.path.basename(f) != 'regression-docs.sh']

VERB = re.compile(r"NIST(?:'s)?\s+(?:has\s+|have\s+|does\s+not\s+|did\s+not\s+|never\s+)?"
                  r"(accept\w*|agree\w*|ask\w*|call\w*|regard\w*|disput\w*|prefer\w*"
                  r"|decid\w*|review\w*|reads?\b|position\b|view\b)", re.I)
ALT  = re.compile(r"(accepted|agreed|reviewed|confirmed|endorsed)\s+by\s+NIST", re.I)
OK   = re.compile(r"not a NIST account|No NIST account|anyone upstream", re.I)
hits = []

for f in files:
    if not os.path.isfile(f):
        continue
    raw = open(f, encoding='utf-8', errors='replace').read()
    for pat in (VERB, ALT):
        for m in pat.finditer(raw):
            s = raw.rfind('\n\n', 0, m.start()); s = 0 if s < 0 else s + 2
            e = raw.find('\n\n', m.end());      e = len(raw) if e < 0 else e
            if OK.search(raw[s:e]):
                continue
            hits.append('%s:%d' % (f, raw.count('\n', 0, m.start()) + 1))

print(' '.join(sorted(set(hits))))
PY
)
if [ -z "${nistsrc}" ]; then note "no NIST attribution in cpp/ comments:" "none"
else bad "NIST attributions in cpp/ (the sweep is incomplete):" "${nistsrc}"; fi

echo
if [ "${fails}" -eq 0 ]; then echo "regression-docs: PASS"; exit 0; fi
echo "regression-docs: FAIL (${fails} checks)"
exit 1
