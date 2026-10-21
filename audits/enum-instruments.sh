#!/bin/sh
# Enumerate instruments BY BEHAVIOUR, not by extension.
#
# Membership test, in order:
#   1. tracked by git (an untracked file is not part of the record), and
#   2. it RUNS, by one of three behaviours:
#        a. the executable bit is set, or the first two bytes are "#!"
#           -- this is what finds cpp/selftest/selftest, generate-refdata and
#           compareresults.pl without naming them;
#        b. it is a CI workflow definition, a verdict-emitting artefact that is
#           never executed locally;
#        c. SOMETHING IN THE TREE INVOKES IT -- sourced, or compiled and then
#           run. NOT MECHANISED, and the attempt is recorded because it
#           matters: a git-grep for the basename near an invocation verb took
#           the live count from 61 to 112, admitting every prose mention of a
#           filename in a .md file, while STILL missing the C++ reproducers
#           whose only build line lives in a comment inside themselves. And
#           file(1) cannot stand in for it: asked about these it answers
#           "c program text, ASCII text" for BOTH a C++ reproducer and a POSIX
#           shell library, so it would admit the library under a
#           "compilable source" test.
#
#           So limb (c) is a REVIEWED LIST with a reason per member, printed by
#           this script, not a pattern. Nine members, below. A judgement that
#           cannot be mechanised without false positives is better stated than
#           approximated -- the approximation here was wrong by 51.
#   3. not a compiled build artefact (file(1) says Mach-O/ELF), because those
#      are OUTPUTS of counted sources, and
#   4. not pure data (.md .txt .json .res .bin .pdf .sha256 .pyc).
#
# No extension list. The four artefacts an extension glob could not see --
# cpp/selftest/selftest, generate-refdata, compareresults.pl and a .mjs
# reproducer -- are found by rule 2 without being named.
set -u
root=${1:-.}
cd "$root" || exit 2
LIVE="cpp/selftest tools .github audits/2026-10-11-independent-audit audits/2026-10-09-independent-audit repairs"
FROZEN="audits/2026-09-30 audits/2026-10-01-re-audit audits/2026-10-02-doc-review"

enumerate() {
    for d in $1; do
        [ -d "$d" ] || continue
        git ls-files "$d" 2>/dev/null
    done | while IFS= read -r f; do
        [ -f "$f" ] || continue
        case "$f" in
            *.md|*.txt|*.json|*.res|*.bin|*.pdf|*.sha256|*.pyc|*/__pycache__/*) continue ;;
        esac
        # compiled outputs are not instruments
        case "$(file -b "$f" 2>/dev/null)" in
            *Mach-O*|*ELF*|*"ar archive"*) continue ;;
        esac
        if [ -x "$f" ]; then printf '%s\n' "$f"; continue; fi
        case "$(head -c2 "$f" 2>/dev/null)" in '#!') printf '%s\n' "$f"; continue ;; esac
        case "$f" in .github/workflows/*.yml) printf '%s\n' "$f"; continue ;; esac
        # (2c) is NOT mechanised here, deliberately. See NOT-MECHANISED below.
    done
}
# LIMB (2c): the reviewed list, with the behaviour that qualifies each.
# Two sourced libraries, which produce no verdict alone and every verdict
# through their callers; and seven compilable sources whose built form produces
# a figure the record cites. Their COMPILED artefacts are excluded by rule (3).
LIMB_C="cpp/selftest/buildstate-lib.sh:sourced-by-6-instruments
cpp/selftest/mutation-lib.sh:sourced-by-3-mutation-harnesses
cpp/selftest/restart-report-label-test.cpp:compiled-by-cpp/Makefile
tools/outside-battery-check.cpp:compiled-by-its-own-documented-build-line
audits/2026-10-11-independent-audit/reproducers/c22_bound.cpp:production-harness-for-OC-22
audits/2026-10-11-independent-audit/reproducers/c18_llp64_overflow.c:reproduces-C18-exactly
audits/2026-10-11-independent-audit/reproducers/f13_nan_reachability.c:F13-reachability-probe
audits/2026-10-11-independent-audit/reproducers/r1_pcol_sweep.cpp:R1-blast-radius
audits/2026-10-11-independent-audit/reproducers/nanorder.cpp:NaN-ordering-probe
audits/2026-10-11-independent-audit/reproducers/atomic_report_write.cpp:C08-atomic-write"

limb_c_count() { printf '%s\n' "$LIMB_C" | grep -c . ; }

if [ "${2:-}" = "--list" ]; then
    enumerate "$LIVE"
    printf '%s\n' "$LIMB_C" | cut -d: -f1
    exit 0
fi
if [ "${2:-}" = "--why" ]; then
    printf 'limb (a/b), mechanical -- executable, shebang, or CI workflow:\n'
    enumerate "$LIVE" | sed 's/^/  /'
    printf '\nlimb (c), reviewed -- sourced or compiled, with the reason:\n'
    printf '%s\n' "$LIMB_C" | sed 's/^/  /'
    exit 0
fi
mech=$(enumerate "$LIVE" | wc -l | tr -d ' ')
lc=$(limb_c_count)
printf 'live:   %s  (%s mechanical + %s reviewed)\n' "$((mech + lc))" "$mech" "$lc"
# A BEHAVIOUR RULE IS PRESENT-TENSE, SO IT DOES NOT GOVERN FROZEN EVIDENCE.
# Nothing invokes a frozen artefact now, and nothing should: what qualified it
# was being invoked THEN. This rule gives 32 where the historical count is 79,
# and reporting 32 as the frozen set would silently retire 47 artefacts that
# were instruments when they produced evidence the record still cites. So this
# script ASSERTS the live number and STATES the frozen one as historical,
# naming what its own rule would have said so the gap is visible.
frozen_by_this_rule=$(enumerate "$FROZEN" | wc -l | tr -d ' ')
printf 'frozen: 79  (historical; this present-tense rule would say %s -- see\n' "$frozen_by_this_rule"
printf '             audits/INSTRUMENT-INVENTORY.md for why it does not govern\n'
printf '             dated evidence)\n'
