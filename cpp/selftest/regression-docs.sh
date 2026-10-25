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
# instrument rule 5, mechanised (OC-73)
. "${here}/labelread-lib.sh"
repo=$(cd "${here}/../.." && pwd)
cd "${repo}" || exit 2

# DOCS_CORE -- the documents whose own text the specific checks below read.
# FORK-DIVERGENCE-AND-TRUST.md is in the core set (OC-91): it cites
# tools/measure-divergence.sh, audits/WITHDRAWN-VERIFICATIONS.md,
# WHAT-A-GREEN-SUITE-ESTABLISHES.md and INDEPENDENT-REVIEW-BOUNDARY.md, and a
# document whose referenced paths are not checked rots silently when one of
# them moves.
DOCS_CORE="README.md NOTICE BUILDING.md FORK-DIVERGENCE-AND-TRUST.md audits/README.md audits/BUG-REPAIR-GUIDE.md audits/2026-09-30/README.md audits/2026-09-30/FINDINGS-TRACKER.md"
TRACKER=audits/2026-09-30/FINDINGS-TRACKER.md

# THE SCOPE WAS THE HOLE (F12 / OC-85).
#
# The stale-claim check ran over DOCS_CORE -- seven files named by hand -- and
# the file F12 found the withdrawn interval claim in,
# audits/2026-10-11-independent-audit/CLOSING-INVENTORY.md, was not one of them.
# A rule that says "a withdrawn claim is withdrawn everywhere or nowhere" cannot
# be enforced over a hand-picked subset of everywhere. The pattern list was
# fine; the scope was the defect.
#
# Scope is now EVERY TRACKED MARKDOWN FILE plus NOTICE, minus the dated audit
# REPORTS, which guide rule 2 forbids editing because they are evidence of what
# was believed when they produced a figure. Excluding them is an exclusion and
# therefore stated: the one unexempted hit a repository-wide sweep finds is
# audits/2026-10-01-re-audit/REPORT.md:16, a corrected "0.94 ms per thousand
# bits" inside such a report -- and correcting it there would destroy the record
# of the error.
#
# THE EXCLUSION IS PER FILE, NOT PER DIRECTORY. audits/2026-09-30 is in the
# canonical frozen set (audits/enum-instruments.sh), but its README.md and
# FINDINGS-TRACKER.md are living documents that happen to sit in a dated
# directory -- the tracker has been edited this campaign -- so they stay in
# scope. Both counts are printed, so the scope is visible rather than implied.
DOCS_FROZEN_RE='^audits/(2026-09-30/(AUDIT\.md|novel-findings/|phase2-focused/)|2026-10-01-re-audit/|2026-10-02-doc-review/)'
# --cached AND --others, SO A DOCUMENT IS IN SCOPE WHILE IT IS BEING WRITTEN
# (OC-89). `git ls-files` alone lists TRACKED files, so a new document escaped
# every check here until the commit that added it -- which is exactly the window
# in which it is being drafted. Observed: audits/WITHDRAWN-VERIFICATIONS.md
# passed this script while untracked and failed the assertive-form check the
# moment it was committed. --exclude-standard keeps .gitignore honoured, so
# build output does not enter scope.
DOCS_LS="git ls-files --cached --others --exclude-standard"
DOCS_ALL=$(${DOCS_LS} '*.md' NOTICE 2>/dev/null | sort -u | grep -Ev "${DOCS_FROZEN_RE}")
DOCS_N=$(printf '%s\n' "${DOCS_ALL}" | grep -c .)
DOCS_SKIPPED=$(${DOCS_LS} '*.md' NOTICE 2>/dev/null | sort -u | grep -Ec "${DOCS_FROZEN_RE}")

fails=0
note() { printf '  %-52s %s\n' "$1" "$2"; }
bad()  { note "$1" "$2"; fails=$((fails + 1)); }

# An extraction that matches nothing produces an empty accumulator, and an empty
# accumulator reads exactly like "nothing was wrong". Every extraction below
# therefore declares the minimum number of items it must find. A count under the
# floor means the pattern has stopped matching these documents, so the check
# verifies nothing -- reported as a failure, not as a pass.
#
# A floor rather than an exact count, deliberately: these documents grow, and a
# hand-maintained exact total is the very defect audits/README.md demonstrates
# (it claims 585 tracked files against an actual 739).
# verify-fixture-inventory.sh can assert an exact 11/11 because its corpus is
# frozen by design; documentation references are not. Each floor sits well under
# the count observed at f069898, which is recorded beside it.
nwords() { echo "$#"; }
floor() { # floor <label> <observed> <minimum>
    if [ "$2" -lt "$3" ]; then
        bad "${1}:" "extracted only $2 item(s), floor is $3 - the pattern no longer matches, so this check verifies nothing"
        return 1
    fi
    note "${1}:" "$2 item(s) extracted (floor $3)"
    return 0
}

# A SCANNER THAT DID NOT RUN SUPPORTS NO CLAIM (SHAPE-03, flagged on this file
# by regression-deadguard.sh).
#
# Every check below collects offending locations into a variable and reports
# "yes" when it comes back EMPTY. An empty accumulator is therefore
# indistinguishable from a scanner that crashed, was killed, or never started --
# a missing python3, a syntax error in the heredoc, an unreadable repo. The
# scan's EXIT STATUS is the only thing that separates "found nothing" from "did
# not look", so it is now read, and a non-zero status fails the check instead of
# passing it.
#
# This was caught by this repository's own dead-guard detector, which flagged
# "verification command in statement position, status never read, no set -e" on
# this file while the file was being edited to tighten a different check.
# A SCAN THAT DID NOT RUN IS A THIRD OUTCOME, NOT A FAILURE (OC-89).
#
# OC-79 made these scans stop reporting a PASS when their interpreter was
# absent. They then reported a FAIL -- which is not a false pass, but is still
# the wrong answer: a defect was not found, an environment was not present, and
# the operator needs to fix a different thing in each case. Now that
# run-all-checks.sh counts "could not run" as its own category (F11/OC-84),
# the distinction has somewhere to go.
#
# So an unrunnable scan increments `cannot`, not `fails`, and this script exits
# 2. Exit 2 is the suite's established "could not run"; it still counts against
# the suite's exit status, so nothing is excused by it.
cannot=0
scanned() { # scanned <rc> <label>  -- 0 if the scan actually ran
    if [ "$1" -ne 0 ]; then
        note "${2} -- THE SCAN DID NOT RUN (exit $1), so its silence means nothing:" "no result"
        cannot=$((cannot + 1))
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------- 1. SHAs
missing=""
# Taken from the fields that actually assert a commit. Scanning for bare hex
# instead would also catch SHA-256 prefixes of data files and the mantissa of
# numbers like 1.44440015503733e-13, neither of which is a commit.
shas=$( { grep -ohE 'Commit [0-9a-f]{7,40}\.' NOTICE | sed 's/^Commit //; s/\.$//'
          grep -ohE '^- \*\*Fork fix commit:\*\* `[0-9a-f]{7,40}`' "${TRACKER}" | grep -ohE '[0-9a-f]{7,40}'
          grep -ohE '`87c104d[0-9a-f]*`' NOTICE "${TRACKER}" | tr -d '`'
        } | sort -u )
floor "commit SHA extraction from NOTICE and the tracker" "$(nwords ${shas})" 10   # 23 at f069898
for h in ${shas}; do
    git cat-file -e "${h}^{commit}" 2>/dev/null || missing="${missing} ${h}"
done
if [ -z "${missing}" ]; then note "every commit SHA in NOTICE and the tracker resolves:" "yes"
else bad "commit SHAs that do not resolve:" "${missing}"; fi

# -------------------------------------------------------- 2. referenced paths
missing=""
refpaths=$(grep -ohE '`[A-Za-z0-9_][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]+\.(sh|py|cpp|h|md|pl|txt|pdf)`' ${DOCS_CORE} | tr -d '`' | sort -u)
floor "repo-path extraction from the docs" "$(nwords ${refpaths})" 20   # 64 at f069898
for f in ${refpaths}; do
    [ -e "${f}" ] && continue
    find . -path ./.git -prune -o -path "*/${f}" -print 2>/dev/null | grep -q . && continue
    # A path the documentation explicitly describes as a former or original
    # location is supposed to be absent; that is the point of saying it moved.
    if grep -h -- "${f}" ${DOCS_CORE} 2>/dev/null \
         | grep -qiE "original path|exists only on|was moved|moved from|former|renamed"; then
        continue
    fi
    missing="${missing} ${f}"
done
if [ -z "${missing}" ]; then note "every repo path referenced in the docs exists:" "yes"
else bad "referenced paths that do not exist:" "${missing}"; fi

# ------------------------------------------------- 3. markdown link targets
missing=""
mdlinks=$(grep -ohE '\]\([A-Za-z0-9_][A-Za-z0-9_./-]*\.(md|sh|pdf|txt)\)' ${DOCS_CORE} | sed 's/^](//; s/)$//' | sort -u)
floor "markdown link extraction from the docs" "$(nwords ${mdlinks})" 5   # 11 at f069898
for l in ${mdlinks}; do
    found=0
    for d in . audits audits/2026-09-30; do [ -e "${d}/${l}" ] && found=1; done
    [ "${found}" -eq 0 ] && missing="${missing} ${l}"
done
if [ -z "${missing}" ]; then note "every local markdown link target resolves:" "yes"
else bad "markdown links that do not resolve:" "${missing}"; fi

# -------------------------------------------- 4. regressions the tracker names
missing=""
trackernamed=$(grep -oE 'cpp/selftest/regression-[a-z0-9-]+\.sh' "${TRACKER}" | sort -u)
floor "regression-script names extracted from the tracker" "$(nwords ${trackernamed})" 8   # 14 at f069898
for f in ${trackernamed}; do
    [ -f "${f}" ] || missing="${missing} ${f}"
done
if [ -z "${missing}" ]; then note "every regression the tracker names exists:" "yes"
else bad "regressions named but absent:" "${missing}"; fi

# --------------------------------- 5. tracker counts match the tracker itself
mismatch=""
for st in NEEDS-FIX UPSTREAM-FIX-PENDING FIXED-UPSTREAM-VERIFY FORK-FIX-REQUIRED FORK-FIXED SUPPORTED-SCOPE-FIXED EXCLUDED-UNSUPPORTED BLOCKED-HARDWARE VERIFIED; do
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
        | sed -n 's/^Assessed min entropy: //p' | lr_one 'Assessed min entropy') || fails=$((fails + 1))
    wrong=""
    # Total across all the documents, not per document: most of them legitimately
    # quote no pinned figure, but if NONE of them does any more then the pattern
    # has stopped matching and the comparison below is vacuous.
    allpinned=$(grep -ohE '0\.12644573619[0-9]+' ${DOCS_CORE} | sort -u)
    floor "pinned-figure extraction across the docs" "$(nwords ${allpinned})" 1   # 2 at f069898
    for d in ${DOCS_CORE}; do
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

# ------------------------------------------- 8. supported build is bounded
# The supported product scope is exactly the three assessed and regression-
# tested programs. Inspect make's forced dry-run plan rather than grepping one
# variable, so a future indirect dependency on ea_conditioning also fails.
build_plan=$(make -Bn -C cpp all 2>&1); build_plan_rc=$?
missing_supported=""
for b in ea_non_iid ea_iid ea_restart; do
    printf '%s\n' "${build_plan}" | grep -qE "(^|[[:space:]])-o[[:space:]]+${b}([[:space:]]|$)" || missing_supported="${missing_supported} ${b}"
done
unexpected=$(printf '%s\n' "${build_plan}" | sed -nE 's/.* -o (ea_conditioning|ea_transpose)( |$).*/\1/p' | sort -u | tr '\n' ' ')
if [ "${build_plan_rc}" -eq 0 ] && [ -z "${missing_supported}" ] && [ -z "${unexpected}" ]; then
    note "make all builds exactly the supported programs:" "ea_non_iid ea_iid ea_restart"
else
    bad "supported build plan drifted:" "exit ${build_plan_rc}; missing${missing_supported:- none}; unexpected ${unexpected:-none}"
fi

# --------------------------- 9. the quoted rate matches the measured table
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

# ------------------------ 10. claims that were false before must not reappear
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
 # WITHDRAWN BY OC-49, and F12 found two of these still asserted. The interval
 # claim was a sweep in steps of 0.02 read as a statement about every point;
 # the 683 was computed at a rounded H_I = 0.70 and reported at the real 0.696,
 # where it is 684. The third entry is the same sweep's boundary conclusion,
 # which the superseding note did not even list as a site (OC-85).
 "identical at every H_I from 0.50 to 0.989"
 "identical from 0.50 to 0.989"
 "identical below H_I"
 "cutoff is 683"
 "cutoff of 683"
 "683 as the restart cutoff"
 "gap first becomes non-zero"
)
# A block that quotes the wrong wording while describing its correction is a
# record, not a reassertion. Exemption is judged over the whole paragraph the
# phrase sits in, not its line, for the same wrapping reason.
hit=$(python3 - "${DOCS_ALL}" "${STALE_CLAIMS[@]}" <<'PY'
import re, sys

docs   = sys.argv[1].split()
claims = sys.argv[2:]
# A correction note is recognised by explicit correction framing, not by a bare
# date. "until 2026-" alone was too loose: NOTICE's statement-of-changes
# paragraph opens "Until 2026-09-30 nothing outside the build files was
# touched", which would have exempted the very sentence this check exists to
# catch. The markers below all require a saying-verb or the word Correction.
# F12 (OC-85) added the framings that legitimate quotations here actually use.
# Three of the four surviving sites were correct quotation-with-correction --
# "The claim was ...", "The project claimed ...", "It read: ..." -- and were
# reported as defects because the marker list did not know those phrasings.
# A check that cannot tell a quotation from an assertion fails the honest
# writer and nobody else.
#
# The window stays ONE PARAGRAPH rather than widening to include the paragraph
# before. Widening it was the other option and is a real loosening: a
# superseding note two paragraphs up would then exempt anything below it. The
# narrower fix is to require the marker in the same paragraph as the dead
# claim, which is also what makes the correction visible to a reader who lands
# mid-document.
EXEMPT = re.compile(r'Correction \(2026-|said "|still said|had been corrected'
                    r'|was headed|headed "|which those two contradict'
                    r'|factor of 1000|a prior session'
                    r'|the claim was|project claimed|it read:|this section said'
                    r'|this cell read|WITHDRAWN|withdrawn|SUPERSEDED|superseded'
                    r'|supersedes|is false|does NOT hold|NOT identical|retire'
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
hitrc=$?
if ! scanned "${hitrc}" "stale-claim scan"; then :
elif [ -z "${hit}" ]; then
    note "no previously-corrected claim has reappeared:" \
         "none, over ${DOCS_N} file(s); ${DOCS_SKIPPED} dated report(s) excluded"
else bad "stale claims present again:" "${hit}"; fi
# A SCOPE OF ZERO FINDS NOTHING. The widened list comes from `git ls-files`, so
# a failure there -- not a git work tree, no index -- would make this check
# silently examine no files and report "none".
if [ "${DOCS_N}" -lt 10 ]; then
    bad "the stale-claim scan's document list is implausibly small:" "${DOCS_N} file(s)"
fi

# ------------------------------- 11. NIST attributions in cpp/ comments
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
nistrc=$?
if ! scanned "${nistrc}" "NIST-attribution scan"; then :
elif [ -z "${nistsrc}" ]; then note "no NIST attribution in cpp/ comments:" "none"
else bad "NIST attributions in cpp/ (the sweep is incomplete):" "${nistsrc}"; fi

# ---------------------------------------------------------------- the floor
# "CERTIFIED FLOOR" IS A RETIRED TERM (F02 / OC-78).
#
# This check used to require a width/reading qualifier beside the phrase, on the
# grounds that the claim held at width 1 for the F07 reading. That was the wrong
# guard for the wrong claim: NO reading is certified. C22a's 8.08e-15 is a
# PRODUCT OF TWO GRID MAXIMA and only one factor's argmax was ever examined --
# the other is attained at r = 2, the first value in its swept list -- and
# C22c's ceiling is a maximum over an 801-point scan. The aggregate takes the
# WEAKEST status of its terms, so the label is MEASURED FLOOR.
#
# So the phrase is retired, and it is retired THE SAME WAY a vacated rule
# number is: prose may still DISCUSS it, and must mark it as retired where it
# does. That convention already exists in this tree for "rule N (vacated)" and
# it was chosen there over widening an exemption list, for the same reason.
#
# ONE FILE IS EXEMPT, AND BY A STATED MECHANISM RATHER THAN BY NAME.
# ORCHESTRATOR-CHECKS.md is an append-only dated record: entries OC-1..OC-77
# were written before the retirement and must not be edited to say something
# their authors did not know, because an entry is the only account of what was
# believed when it produced a figure. Such a file is exempt for occurrences
# under an entry heading BELOW the retirement point, and only while it carries
# a file-level retirement notice near its head. A file with no notice gets no
# exemption, and an occurrence under OC-78 or later is judged like any other.
echo
RETIRED_AT_OC=78
floorbad=$(
RETIRED_AT_OC="${RETIRED_AT_OC}" python3 - "${repo}" <<'FLOORPY'
import os, re, sys
root = sys.argv[1]
retired_at = int(os.environ['RETIRED_AT_OC'])
pat = re.compile(r'certified\s+floor', re.I)
# A paragraph that marks the phrase retired, superseded or false. "not a floor"
# is NOT in this list any more: it described a different distinction (margin vs
# floor) and would have exempted most of the old sites unchanged.
# STEMS, not exact words: the first draft required "retired" and failed on a
# paragraph of this very entry that said "the phrase this entry retires".
retired = re.compile(r'retire|supersede|withdraw|is false|was wrong|no longer|'
                     r'read "measured floor"|OC-78|MEASURED FLOOR', re.I)
notice = re.compile(r'RETIRED TERM\s*--|RETIRED TERM\s*—', re.I)
heading = re.compile(r'^##\s*OC-(\d+)\b', re.M)
hits = []
for base, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
    for f in files:
        if not f.endswith(('.md', '.py', '.sh', '.txt')):
            continue
        p = os.path.join(base, f)
        try:
            raw = open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        # the file-level notice must appear in the first 4000 characters: a
        # notice buried at the end is not a notice.
        has_notice = bool(notice.search(raw[:4000]))
        # entry boundaries, for the append-only-record exemption
        bounds = [(m.start(), int(m.group(1))) for m in heading.finditer(raw)]
        for m in pat.finditer(raw):
            if has_notice and bounds:
                prior = [n for off, n in bounds if off < m.start()]
                if prior and prior[-1] < retired_at:
                    continue        # a dated entry written before the retirement
            lo = raw.rfind('\n\n', 0, m.start()) + 1
            hi = raw.find('\n\n', m.end())
            ctx = raw[lo: hi if hi > 0 else len(raw)]
            if not retired.search(ctx):
                hits.append('%s:%d' % (os.path.relpath(p, root), raw.count('\n', 0, m.start()) + 1))
print(' '.join(sorted(set(hits))))
FLOORPY
)
floorrc=$?
if ! scanned "${floorrc}" "\"certified floor\" retirement scan"; then
    :
elif [ -z "${floorbad}" ]; then
    note "\"certified floor\" is retired and every use says so:" "yes"
else
    bad "\"certified floor\" used without marking it retired:" "${floorbad}"
fi

# AND THE ASSERTIVE FORMS CANNOT BE WRITTEN AT ALL, ONLY QUOTED (OC-88).
#
# The paragraph-marker rule above governs the PHRASE. It does not stop a
# sentence that ASSERTS the retired claim while a retirement marker sits
# elsewhere in the same paragraph -- and that is precisely how
# oracles/entropy_floor.py came to assert, four times in one comment block,
# that a reading is a certified floor while printing MEASURED FLOOR.
#
# So the assertive constructions -- "is a certified floor", "are certified
# floors", "prints a certified floor" and their kin -- must additionally be
# INSIDE QUOTATION MARKS at the site: a double quote, a single quote, a
# backtick or a markdown emphasis marker within a short window on both sides.
# Reported speech is allowed; assertion is not. This is stricter than the
# paragraph rule rather than a different version of it, and it is the half that
# answers "no reading is certified".
echo
assertbad=$(
RETIRED_AT_OC="${RETIRED_AT_OC}" python3 - "${DOCS_ALL}" <<'ASSERTPY'
import os, re, sys
docs = sys.argv[1].split()
retired_at = int(os.environ['RETIRED_AT_OC'])
# the assertive forms, not the bare noun phrase
ASSERT = re.compile(r'\b(?:is|are|was|were|be|becomes?|prints?|printed|yields?|gives?|'
                    r'remains?|stays?|counts? as)\s+(?:a|an|both|the|two)?\s*'
                    r'(?:\w+\s+){0,3}?certified\s+floors?\b', re.I)
heading = re.compile(r'^##\s*OC-(\d+)\b', re.M)
notice = re.compile(r'RETIRED TERM\s*(?:--|—)', re.I)
# Built from code points, not written as a literal: a literal mixing a single
# quote and a backtick inside a $( ... ) heredoc is parsed by bash at RUN
# time -- bash -n does not reach it -- and died with "unexpected EOF while
# looking for matching" the quote character itself.
QUOTE = ''.join(chr(c) for c in (0x22, 0x27, 0x60, 0x2a, 0x201c, 0x201d, 0x2018, 0x2019))
hits = []
for d in docs:
    try:
        raw = open(d, encoding='utf-8', errors='replace').read()
    except OSError:
        continue
    has_notice = bool(notice.search(raw[:4000]))
    bounds = [(m.start(), int(m.group(1))) for m in heading.finditer(raw)]
    for m in ASSERT.finditer(raw):
        if has_notice and bounds:
            prior = [n for off, n in bounds if off < m.start()]
            if prior and prior[-1] < retired_at:
                continue
        # a quotation mark within 90 characters on BOTH sides of the match
        before = raw[max(0, m.start() - 90):m.start()]
        after = raw[m.end():m.end() + 90]
        if any(c in before for c in QUOTE) and any(c in after for c in QUOTE):
            continue
        hits.append('%s:%d' % (os.path.relpath(d), raw.count('\n', 0, m.start()) + 1))
print(' '.join(sorted(set(hits))))
ASSERTPY
)
assertrc=$?
if ! scanned "${assertrc}" "assertive certified-floor scan"; then
    :
elif [ -z "${assertbad}" ]; then
    note "no document ASSERTS a certified floor (only quotes one):" "yes"
else
    bad "a certified floor is ASSERTED, not quoted, at:" "${assertbad}"
fi

# EVERY RECORDED gh COMMAND THAT USES A DEFAULT REPOSITORY MUST NAME ONE
# (OC-93).
#
# This checkout has two remotes -- `origin` (the fork) and `upstream`
# (`usnistgov`) -- and `gh` with no `-R` resolves to UPSTREAM. The two
# repositories share their name, visibility and default branch, so an
# unqualified read returns a PLAUSIBLE ANSWER ABOUT THE WRONG TREE rather than
# failing. Measured: an unqualified `gh repo view --json ...hasIssuesEnabled`
# returned `true`, which is upstream's value -- the fork's is `false` -- and
# every other field it printed was identical between the two.
#
# So a command recorded in the documentation is a command someone will run, and
# it names its target or it is a defect. Subcommands that do NOT use a default
# repository are exempt by name, with the reason: `gh api` takes an explicit
# path (unless it interpolates {owner}/{repo}), `gh auth` is account-scoped,
# and `gh repo set-default` takes the repository as a positional argument --
# that one is the fix, not the hazard.
echo
ghbad=$(python3 - "${DOCS_ALL}" <<'GHPY'
import os, re, sys
docs = sys.argv[1].split()
# subcommands that resolve a DEFAULT repository when none is named
DEFAULTED = r'run|workflow|pr|issue|release|cache|secret|variable|label|ruleset'
CALL = re.compile(r'\bgh\s+(' + DEFAULTED + r')\s+[a-z-]+([^\n`]*)')
hits = []
for d in docs:
    try:
        raw = open(d, encoding='utf-8', errors='replace').read()
    except OSError:
        continue
    for m in CALL.finditer(raw):
        tail = m.group(2)
        # named either with -R/--repo, or by a shell variable that obviously
        # carries one ("$FORK"), or the line is prose ABOUT the hazard
        if re.search(r'-R[ =]|--repo[ =]', tail):
            continue
        # IS THIS A COMMAND, OR A MENTION OF ONE? A command someone will run
        # lives in a fenced block; prose discussing the hazard quotes the bare
        # form mid-sentence and must be able to. The first draft used a
        # single-line marker window and flagged two passages that exist to
        # explain this very defect -- one of them because the word "bare" sat
        # at the end of the previous line.
        #
        # So: inside a fence, -R is required with NO exemption, because a fence
        # is an instruction. Outside one, the surrounding PARAGRAPH must mark
        # the hazard -- the same window every other check in this file uses.
        fences = [mm.start() for mm in re.finditer(r'^```', raw, re.M)]
        in_fence = sum(1 for f in fences if f < m.start()) % 2 == 1
        if in_fence:
            # A RECORD MUST BE ABLE TO QUOTE A BAD COMMAND VERBATIM, INCLUDING
            # IN A FENCE -- that is what the evidence IS. "No exemption inside
            # a fence" was too absolute and flagged OC-93's own quotation of
            # the unqualified call it was reporting.
            #
            # The convention is a label ON THE COMMAND: a trailing
            # `# no -R` / `# unqualified` / `# NOT A COMMAND` comment. It
            # cannot be used to smuggle a runnable instruction through, because
            # the label is the statement that it is not one.
            line_start = raw.rfind('\n', 0, m.start()) + 1
            line_end = raw.find('\n', m.end())
            cmdline = raw[line_start: line_end if line_end > 0 else len(raw)]
            if re.search(r'#\s*(no\s+-R|unqualified|NOT A COMMAND)', cmdline, re.I):
                continue
        else:
            lo = raw.rfind('\n\n', 0, m.start()) + 1
            hi = raw.find('\n\n', m.end())
            para = raw[lo: hi if hi > 0 else len(raw)]
            # STEMS, not exact words. "resolves to" missed a paragraph saying
            # "resolved the repository to" -- the same slip the certified-floor
            # check made with "retire"/"retires". Second instance; stem by
            # default.
            if re.search(r'not optional|OC-93|resolv|attempted dispatch|wrong tree'
                         r'|bare\s|named either|unqualified|default repositor', para, re.I):
                continue
        hits.append('%s:%d%s' % (os.path.relpath(d), raw.count('\n', 0, m.start()) + 1,
                                 ' (in a code fence)' if in_fence else ''))
print(' '.join(sorted(set(hits))))
GHPY
)
ghrc=$?
if ! scanned "${ghrc}" "recorded-gh-command scan"; then
    :
elif [ -z "${ghbad}" ]; then
    note "every recorded gh command names its repository:" "yes"
else
    bad "a recorded gh command would resolve to the default repository:" "${ghbad}"
fi

# THE WITHDRAWN-VERIFICATION REGISTER MUST BE COMPLETE (OC-88).
#
# A withdrawal recorded only in the chronological entry that performed it is a
# withdrawal nobody finds, so audits/WITHDRAWN-VERIFICATIONS.md carries one
# entry per withdrawn verification with five fields. The fifth -- WHAT LEANED
# ON IT -- is the one that is easy to omit and the only reason the others
# matter, so its absence is a failure like any other.
#
# This checks the register's SHAPE, not its truth: that every WV- entry has all
# five fields, and that there is at least one entry, because an empty register
# would pass a field check trivially (SHAPE-03).
echo
WVREG="${repo}/audits/WITHDRAWN-VERIFICATIONS.md"
if [ ! -f "${WVREG}" ]; then
    bad "the withdrawn-verification register is missing:" "${WVREG}"
else
    wvbad=$(python3 - "${WVREG}" <<'WVPY'
import re, sys
raw = open(sys.argv[1], encoding='utf-8').read()
FIELDS = ('CLAIM', 'WITHDRAWN', 'REASON', 'WHAT NOW STANDS', 'WHAT LEANED ON IT')
parts = re.split(r'^## (WV-\d+)[^\n]*$', raw, flags=re.M)
# parts = [preamble, id, body, id, body, ...]
bad = []
n = 0
for i in range(1, len(parts) - 1, 2):
    wid, body = parts[i], parts[i + 1]
    n += 1
    for f in FIELDS:
        if not re.search(r'\*\*%s\b' % re.escape(f), body):
            bad.append('%s:missing-%s' % (wid, f.replace(' ', '-')))
    if not re.search(r'\b20\d\d-\d\d-\d\d\b', body):
        bad.append('%s:no-date' % wid)
if n == 0:
    bad.append('the-register-has-no-entries')
print(' '.join(bad))
WVPY
)
    wvrc=$?
    if ! scanned "${wvrc}" "withdrawn-verification register scan"; then
        :
    elif [ -z "${wvbad}" ]; then
        note "every withdrawn verification carries its five fields:" \
             "yes, over $(grep -c '^## WV-' "${WVREG}") entries"
    else
        bad "withdrawn-verification entries are incomplete:" "${wvbad}"
    fi
fi

# THE INSTRUMENT INVENTORY'S STATED COUNT MUST MATCH THE ENUMERATOR (OC-90).
#
# audits/INSTRUMENT-INVENTORY.md stated "70 live" in six places, none of them
# naming when it was measured, while the enumerator printed 73. A count written
# in prose drifts from the thing that computes it; the enumerator is the
# authority and this check is what makes that true rather than asserted.
#
# It compares the LIVE figure only. The frozen figure is fixed by construction
# -- dated evidence does not grow -- and the inventory says so.
echo
INVDOC="${repo}/audits/INSTRUMENT-INVENTORY.md"
if [ ! -f "${INVDOC}" ] || [ ! -x "${repo}/audits/enum-instruments.sh" ]; then
    bad "the instrument inventory or its enumerator is missing:" "${INVDOC}"
else
    inv_live=$(sh "${repo}/audits/enum-instruments.sh" "${repo}" 2>/dev/null \
               | sed -n 's/^live:[[:space:]]*\([0-9][0-9]*\).*/\1/p' | head -1)
    # [0-9][0-9]* and [[:space:]], not \+ and a literal space: \+ is a GNU
    # extension that BSD sed (macOS) treats as a literal plus, and the
    # enumerator pads its label with several spaces. The first draft matched
    # nothing and reported "cannot compare" -- which failed closed, correctly,
    # and was still the wrong answer.
    if [ -z "${inv_live}" ]; then
        bad "the enumerator printed no live count:" "cannot compare"
    elif grep -q "\*\*${inv_live}\*\* at \`" "${INVDOC}"; then
        note "the instrument inventory's live count matches the enumerator:" "${inv_live}"
    else
        bad "the inventory's stated live count disagrees with the enumerator:" \
            "enumerator says ${inv_live}; no '**${inv_live}** at <commit>' in the inventory"
    fi
fi

# THE DIVERGENCE DOCUMENT'S FIGURES ARE RE-DERIVED, NOT TRUSTED (OC-91).
#
# FORK-DIVERGENCE-AND-TRUST.md's previous version described a branch that had
# been merged and deleted, said "66 commits ahead" when it was 179, and gave a
# category table off by more than a factor of 1.5 -- none of it labelled with
# when it had been measured. Its section 6 now promises that the figures are
# enforced; this is what makes that a mechanism rather than a promise.
#
# tools/measure-divergence.sh prints the figures from git at HEAD. Every one it
# prints must appear in the document, and the document must name the commit it
# was measured at. A figure the script prints and the document does not carry
# is drift; so is a commit label that is not HEAD's.
echo
DIVDOC="${repo}/FORK-DIVERGENCE-AND-TRUST.md"
DIVTOOL="${repo}/tools/measure-divergence.sh"
if [ ! -f "${DIVDOC}" ] || [ ! -x "${DIVTOOL}" ]; then
    bad "the divergence document or its measurement script is missing:" "${DIVDOC}"
else
    # MEASURE AT THE COMMIT THE DOCUMENT NAMES, NOT AT HEAD.
    #
    # Measuring at HEAD made this fail on the very commit that wrote the
    # figures -- committing the rewrite added files and insertions, so the
    # document was "stale" before anyone read it. A check that fails on every
    # commit is a check that gets bypassed.
    #
    # So two questions, asked separately:
    #   1. is the document internally consistent -- do its figures match a
    #      re-measurement AT THE COMMIT IT NAMES? That is a hard failure, and
    #      it stays true however far HEAD moves.
    #   2. is it STALE -- how far behind HEAD is that commit? Also a hard
    #      failure, but at a threshold, so ordinary work does not trip it.
    div_at=$(sed -n 's/^\*\*Measured at commit `\([0-9a-f]\{7,40\}\)`.*/\1/p' "${DIVDOC}" | head -1)
    if [ -z "${div_at}" ]; then
        bad "the divergence document does not name the commit it was measured at:" \
            "expected a line starting '**Measured at commit \`<sha>\`'"
        div_at=HEAD
    fi
    divout=$(sh "${DIVTOOL}" "${div_at}" 2>&1)
    divrc=$?
    if ! scanned "${divrc}" "divergence measurement"; then
        :
    else
        divbad=""
        # the commit the document says it was measured at must be HEAD's
        want_sha=$(printf '%s\n' "${divout}" | sed -n 's/^measured-at-commit:[[:space:]]*//p')
        grep -q "\`${want_sha}\`" "${DIVDOC}" || divbad="${divbad} commit(${want_sha})"
        # and each figure the script derives must appear, formatted with commas
        # as the document writes them
        for pair in "commits-ahead" "production" "harness" "ci" "evidence" "docs"; do
            case "${pair}" in
              commits-ahead)
                v=$(printf '%s\n' "${divout}" | sed -n 's/^commits-ahead:[[:space:]]*//p')
                grep -q "\*\*${v} commits ahead" "${DIVDOC}" || divbad="${divbad} ahead(${v})" ;;
              *)
                ins=$(printf '%s\n' "${divout}" | sed -n "s/^${pair} *files=[0-9]* *insertions=\\([0-9]*\\).*/\\1/p")
                [ -n "${ins}" ] || continue
                # the document writes thousands with commas
                pretty=$(printf '%s' "${ins}" | sed -e :a -e 's/\(.*[0-9]\)\([0-9]\{3\}\)/\1,\2/;ta')
                grep -q "| ${pretty} |" "${DIVDOC}" \
                    || grep -q "\*\*${pretty}\*\*" "${DIVDOC}" \
                    || divbad="${divbad} ${pair}(${pretty})" ;;
            esac
        done
        if [ -z "${divbad}" ]; then
            note "the divergence document's figures match a re-measurement:" \
                 "at ${want_sha}"
        else
            bad "the divergence document's figures have drifted:" "${divbad}"
        fi
        # STALENESS, as its own question. 40 commits: this document is rewritten
        # when the state it describes moves materially, not on every commit --
        # OC-77..OC-91 is fifteen record entries over about twenty-five commits
        # -- so 40 is roughly "a round of work has happened since". The commit
        # must also be an ANCESTOR of HEAD: a document naming a commit that is
        # not in this history was measured somewhere else.
        DIV_STALE_AFTER=40
        behind=$(printf '%s\n' "${divout}" | sed -n 's/^behind-head:[[:space:]]*//p')
        if ! git merge-base --is-ancestor "${div_at}" HEAD 2>/dev/null; then
            bad "the divergence document names a commit that is not an ancestor of HEAD:" "${div_at}"
        elif [ -n "${behind}" ] && [ "${behind}" -gt "${DIV_STALE_AFTER}" ]; then
            bad "the divergence document is stale:" \
                "measured ${behind} commits behind HEAD (threshold ${DIV_STALE_AFTER}); re-measure and rewrite what moved"
        else
            note "the divergence document's measurement is current:" \
                 "${behind:-?} commit(s) behind HEAD, threshold ${DIV_STALE_AFTER}"
        fi
    fi
fi

# AND THE ORACLE MUST NOT PRINT IT. The prose check above cannot see what a
# program emits at run time, and the label the oracle PRINTS is the one a reader
# acts on.
#
# THE CHECK LOOKS AT CODE, NOT AT COMMENTS. Its first draft grepped the file for
# the quoted string and failed on the two COMMENTS that explain the retirement
# -- so writing down why the label was removed would have kept the check red
# forever, and the only way to make it green would have been to stop explaining.
# A check that punishes the explanation of a repair is worse than no check.
echo
oraclebad=$(
python3 - "${repo}/audits/2026-10-11-independent-audit/oracles/entropy_floor.py" <<'ORACLEPY'
import io, sys, tokenize
path = sys.argv[1]
hits = []
try:
    with io.open(path, 'rb') as fh:
        for tok in tokenize.tokenize(fh.readline):
            # STRING tokens only: a comment is tokenize.COMMENT and is skipped,
            # which is the whole point. A docstring is a STRING and IS judged --
            # a docstring is output a reader can see via --help.
            if tok.type == tokenize.STRING and 'CERTIFIED FLOOR' in tok.string:
                hits.append('%s:%d' % (path.split('/')[-1], tok.start[0]))
except (OSError, tokenize.TokenError, IndentationError, SyntaxError) as e:
    print('UNREADABLE: %s' % e)
    raise SystemExit(0)
print(' '.join(hits))
ORACLEPY
)
oraclerc=$?
if ! scanned "${oraclerc}" "entropy_floor.py literal scan"; then
    :
elif [ -z "${oraclebad}" ]; then
    note "entropy_floor.py has no \"CERTIFIED FLOOR\" string literal:" "yes"
else
    bad "entropy_floor.py still carries the retired label in code:" "${oraclebad}"
fi

# AND THE STATUS VOCABULARY MUST BE DEFINED WHERE IT IS USED. A composite label
# is worth nothing if the reader cannot find out what MEASURED means.
echo
vocabbad=""
# Written as an explicit `if` rather than `grep -q ... || var=...`: the second
# form reads the status perfectly well, but regression-deadguard.sh's pattern C
# flags it as "status never read" and a baseline carrying a false positive is
# worse than one carrying none.
for w in PROVED DERIVED MEASURED; do
    if ! grep -q "^#   ${w}" "${repo}/audits/2026-10-11-independent-audit/oracles/entropy_floor.py" 2>/dev/null; then
        vocabbad="${vocabbad} ${w}"
    fi
done
if [ -z "${vocabbad}" ]; then
    note "the floor's PROVED/DERIVED/MEASURED vocabulary is defined:" "yes"
else
    bad "the floor prints a status with no definition for:" "${vocabbad}"
fi

# ---------------------------------------------------------------- rule numbers
# OC-68: a cited rule number with no definition fails this check. The guide's
# instrument list was headed "Three rules" while containing five, numbered
# 1,2,3,4,5,4, so build-state and labelled-read were BOTH "rule 4" and rule 3's
# own text cited "rule 4" with two referents. Separately, "RULE 12" was cited
# three times, defined nowhere here, with a different principle ascribed at
# each site. Numbering is cheap to get wrong and expensive to follow, so it is
# checked rather than remembered.
#
# THE CONVENTION: prose that DISCUSSES a retired number writes it as
# "rule N (vacated)". The check exempts a citation whose surrounding paragraph
# says the number has no definition, is vacated, or is not reused -- so writing
# the marker is how you discuss a dead number without asserting it. This was
# not invented for convenience: the check caught OC-68's own prose about rule
# 10 on its first full-suite run, which is the check working on its author.
#
# AND THE TIMING IS PART OF THE RULE. This check passed when run directly and
# failed in the suite, because I ran it BEFORE writing the text it would judge.
# A check run before the writing it judges is the same shape as reading a
# figure in the command that writes it. The suite run is the one that counts,
# and it runs after the text exists.
echo
rulebad=$(
python3 - "${repo}" <<'PY'
import os, re, sys
root = sys.argv[1]
guide = os.path.join(root, 'audits', 'BUG-REPAIR-GUIDE.md')
try:
    g = open(guide, encoding='utf-8', errors='replace').read()
except OSError:
    print('BUG-REPAIR-GUIDE.md unreadable'); raise SystemExit

# DEFINED: numbered entries in the instrument list, and "### Rule N" headings.
defined = set(int(m) for m in re.findall(r'^\s{2,}(\d+)\.\s+\*\*', g, re.M))
defined |= set(int(m) for m in re.findall(r'^###\s+Rule\s+(\d+)\s+—', g, re.M))
# VACATED: a heading that says so is not a definition.
vacated = set(int(m) for m in re.findall(r'^###\s+Rule\s+(\d+)\s+—\s*VACATED', g, re.M))
defined -= vacated
rdefined = set(re.findall(r'^###\s+Record discipline\s+(R\d+)\s+—', g, re.M))

hits = []
for base, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
    for f in files:
        if not f.endswith(('.md', '.sh', '.py')):
            continue
        path = os.path.join(base, f)
        try:
            raw = open(path, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        # [1-9] because there is no rule 0, and the lookahead because
        # "rule 0.5" in prose ("raw 2.0 vs rule 0.5") matched as rule 0.
        for m in re.finditer(r'\b[Rr]ule\s+([1-9]\d*)\b(?!\.\d)', raw):
            n = int(m.group(1))
            if n in defined:
                continue
            line = raw.count('\n', 0, m.start()) + 1
            ctx = raw[max(0, m.start()-90): m.end()+90]
            # a citation that itself says the number is undefined or vacated is fine
            if re.search(r'no definition|undefined|VACATED|not reused|vacated', ctx, re.I):
                continue
            hits.append('%s:%d(rule %d)' % (os.path.relpath(path, root), line, n))
        for m in re.finditer(r'\bRecord discipline\s+(R\d+)\b', raw):
            if m.group(1) not in rdefined:
                line = raw.count('\n', 0, m.start()) + 1
                hits.append('%s:%d(%s)' % (os.path.relpath(path, root), line, m.group(1)))
print(' '.join(sorted(set(hits))))
PY
)
rulerc=$?
if ! scanned "${rulerc}" "rule-citation scan"; then
    :
elif [ -z "${rulebad}" ]; then
    note "every cited rule number has a definition:" "yes"
else
    bad "cited rule numbers with no definition:" "${rulebad}"
fi

# ------------------------------------------------- the suite's scope statement
# OC-76: WHAT-A-GREEN-SUITE-ESTABLISHES.md states counts with the command to
# recompute each. Its truth depends on repository state (rule 11), so the
# counts are checked rather than trusted -- a scope statement that has gone
# stale is worse than none, because it is cited.
echo
SCOPE="${here}/WHAT-A-GREEN-SUITE-ESTABLISHES.md"
if [ ! -f "${SCOPE}" ]; then
    bad "the suite's scope statement is missing:" "${SCOPE}"
else
    sbad=""
    n_mut=$(ls "${here}"/*mutation-test.sh "${here}"/regression-deadguard.sh 2>/dev/null | grep -c .)
    n_pres=$(grep -lE 'HARNESS FAULT|is absent or empty|INPUT-DID-NOT-REACH' "${here}"/*.sh 2>/dev/null | grep -c .)
    n_hard=$(grep -lE 'echo .*[0-9]+ (of|values|comparisons|files|checks)' "${here}"/*.sh 2>/dev/null | grep -c .)
    n_scripts=$(grep -c '' "${here}/regression-script-inventory.txt")
    # The counts sit inside markdown table cells, so no end-of-line anchor:
    # match the arrow and the number as a token. The first version anchored on
    # "$" and reported every count stale, which is a detector that cannot pass.
    grep -qE "→ ${n_mut}( \||$)"   "${SCOPE}" || sbad="${sbad} mutation-harness-count(${n_mut})"
    grep -qE "→ ${n_pres}( \||$)"  "${SCOPE}" || sbad="${sbad} input-presence-count(${n_pres})"
    grep -qE "→ ${n_hard}( \||$)"  "${SCOPE}" || sbad="${sbad} hardcoded-claim-count(${n_hard})"
    grep -q "| ${n_scripts} |" "${SCOPE}" || sbad="${sbad} regression-script-count(${n_scripts})"
    if [ -z "${sbad}" ]; then
        note "the suite's scope statement matches the tree:" "yes"
    else
        bad "the scope statement's counts are stale:" "${sbad}"
    fi
fi

echo
# COULD NOT RUN is reported BEFORE pass/fail, because an incomplete run's
# verdict on the checks it did reach is not the verdict on the file.
if [ "${cannot}" -ne 0 ]; then
    echo "regression-docs: COULD NOT RUN (${cannot} scan(s) did not execute; ${fails} of the rest failed)"
    exit 2
fi
if [ "${fails}" -eq 0 ]; then echo "regression-docs: PASS"; exit 0; fi
echo "regression-docs: FAIL (${fails} checks)"
exit 1
