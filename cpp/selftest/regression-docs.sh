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

DOCS="README.md NOTICE BUILDING.md audits/README.md audits/BUG-REPAIR-GUIDE.md audits/2026-09-30/README.md audits/2026-09-30/FINDINGS-TRACKER.md"
TRACKER=audits/2026-09-30/FINDINGS-TRACKER.md

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
scanned() { # scanned <rc> <label>  -- 0 if the scan actually ran
    if [ "$1" -ne 0 ]; then
        bad "${2} -- THE SCAN DID NOT RUN (exit $1), so its silence means nothing:" "no result"
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
refpaths=$(grep -ohE '`[A-Za-z0-9_][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]+\.(sh|py|cpp|h|md|pl|txt|pdf)`' ${DOCS} | tr -d '`' | sort -u)
floor "repo-path extraction from the docs" "$(nwords ${refpaths})" 20   # 64 at f069898
for f in ${refpaths}; do
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
mdlinks=$(grep -ohE '\]\([A-Za-z0-9_][A-Za-z0-9_./-]*\.(md|sh|pdf|txt)\)' ${DOCS} | sed 's/^](//; s/)$//' | sort -u)
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
    allpinned=$(grep -ohE '0\.12644573619[0-9]+' ${DOCS} | sort -u)
    floor "pinned-figure extraction across the docs" "$(nwords ${allpinned})" 1   # 2 at f069898
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
hitrc=$?
if ! scanned "${hitrc}" "stale-claim scan"; then :
elif [ -z "${hit}" ]; then note "no previously-corrected claim has reappeared:" "none"
else bad "stale claims present again:" "${hit}"; fi

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
if [ "${fails}" -eq 0 ]; then echo "regression-docs: PASS"; exit 0; fi
echo "regression-docs: FAIL (${fails} checks)"
exit 1
