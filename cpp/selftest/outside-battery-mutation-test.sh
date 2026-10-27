#!/bin/bash
#
# Mutation controls for the outside-battery corpus checks (OC-23, mechanised
# 2026-10-19). Every one of these was previously run by hand from a shell and
# recorded in the audit; none was repeatable, and one of them -- a sed that
# edited the wrong line -- passed and was briefly recorded as the check failing
# to fire. They are now a harness, and each mutation's landing is asserted
# through mutation-lib.sh before the guard's response is judged.
#
# Not a regression script: the name deliberately does not match regression-*.sh,
# matching the convention of harness-inventory-mutation-test.sh, so
# run-all-checks.sh's authoritative inventory does not discover it. It is the
# mutation control FOR regression-outside-battery.sh, which is in that
# inventory.
#
# The corpus is 31 one-million-sample streams. Generating it takes about a
# minute; OUTSIDE_BATTERY_WORK is honoured so a prepared corpus can be reused.
#
# EXIT  0 every mutation landed and was caught   1 otherwise   2 could not run
set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
. "${here}/mutation-lib.sh"

# OC-126: declared here, asserted against the runtime tally by mut_summary,
# and read from here by regression-docs.sh. One number, three places that
# must agree, and a drift anywhere fails rather than printing a new total.
MUT_DECLARED=9


guard="${here}/regression-outside-battery.sh"
manifest="${here}/outside-battery-corpus.txt"
[ -r "${guard}" ] && [ -r "${manifest}" ] || { echo "outside-battery-mutation-test: guard or manifest missing" >&2; exit 2; }

scratch=$(mktemp -d "${TMPDIR:-/tmp}/ea-obcmut.XXXXXX") || exit 2
trap 'rm -rf "${scratch}"' EXIT HUP INT TERM

work="${OUTSIDE_BATTERY_WORK:-${scratch}/corpus}"
mkdir -p "${work}"

# One run to populate and verify the corpus. If this fails, nothing below means
# anything, so it exits 2 rather than reporting a mutation result.
if ! OUTSIDE_BATTERY_WORK="${work}" "${guard}" >"${scratch}/baseline.log" 2>&1; then
    echo "outside-battery-mutation-test: baseline run failed; nothing below is interpretable" >&2
    tail -5 "${scratch}/baseline.log" >&2
    exit 2
fi
mut_note "baseline: the pinned corpus is accepted" "accepted"
MUT_PASS=$((MUT_PASS + 1))

run_with() { # run_with <manifest> [cite-root]
    if [ "$#" -ge 2 ]; then
        OUTSIDE_BATTERY_CORPUS="$1" OUTSIDE_BATTERY_CITE_ROOT="$2" OUTSIDE_BATTERY_WORK="${work}" "${guard}"
    else
        OUTSIDE_BATTERY_CORPUS="$1" OUTSIDE_BATTERY_WORK="${work}" "${guard}"
    fi
}

# ---- 1. a stream removed from the manifest. THIS IS THE CASE THAT USED TO PASS:
# the digests all matched, the count was never checked, and "0 of 25" silently
# became 0 of 24.
m="${scratch}/m-removed.txt"
mut_begin "stream removed from the manifest" "${m}"
grep -v '^mt mt02 ' "${manifest}" > "${m}"
# THE BASELINE FIRST (OC-54). Every mutation below is expected to be REFUSED,
# and a set of negatives that all refuse for one shared accidental reason looks
# exactly like a set of working guards. Asserting the unmutated manifest is
# ACCEPTED, before any of them, is what makes each later refusal attributable.
mut_baseline "the unmutated pinned corpus" run_with "${manifest}"

mut_expect_fail "stream removed from the manifest" "--match=family mt short or long" run_with "${m}"

# ---- 2. a stream added to the manifest
m="${scratch}/m-added.txt"
mut_begin "stream added to the manifest" "${m}"
{ cat "${manifest}"; echo "sha sha20 0000000000000000000000000000000000000000000000000000000000000000"; } > "${m}"
mut_expect_fail "stream added to the manifest" "--match=family sha short or long" run_with "${m}"

# ---- 3. an unlisted stream present in the corpus directory
mut_begin "unlisted stream present on disk" "${work}"
cp "${work}/mt00.bin" "${work}/zz_unlisted.bin"
mut_expect_fail "unlisted stream present on disk" "--match=unlisted stream present" run_with "${manifest}"
rm -f "${work}/zz_unlisted.bin"

# ---- 4. a digest changed. The first attempt at this one edited the wrong line
# and the run passed; the landing assertion below is what would have caught it.
m="${scratch}/m-digest.txt"
mut_begin "digest changed" "${m}"
sed 's/^mt mt02 7a915424/mt mt02 7a915425/' "${manifest}" > "${m}"
if cmp -s "${m}" "${manifest}"; then
    mut_noapply "digest changed" "the sed matched nothing; mt02's digest prefix must have changed"
else
    mut_expect_fail "digest changed" "--match=DIGEST MISMATCH mt02" run_with "${m}"
fi

# ---- 5. a listed name the generator cannot build
m="${scratch}/m-unbuildable.txt"
mut_begin "listed stream the generator cannot build" "${m}"
sed 's/^defect F_xor30 .*/defect H_nonexistent 1111111111111111111111111111111111111111111111111111111111111111/' "${manifest}" > "${m}"
mut_expect_fail "listed stream the generator cannot build" "--match=generator cannot produce" run_with "${m}"
rm -f "${work}/H_nonexistent.bin"

# ---- 6. a cited count in the record disagreeing with the expectation
cite="${scratch}/cite"
mkdir -p "${cite}/tools" "${cite}/audits/2026-10-11-independent-audit/generators"
cp "${repo}/tools/outside-battery-check.cpp" "${cite}/tools/"
cp "${repo}/audits/2026-10-11-independent-audit/generators/blindspot_streams.py" "${cite}/audits/2026-10-11-independent-audit/generators/"
mut_begin "a cited 0/N in the record changed to 0/24" "${cite}/audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md"
sed 's|\*\*0/25\*\* over 5\.731|**0/24** over 5.731|' \
    "${repo}/audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md" \
    > "${cite}/audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md"
mut_expect_fail "a cited 0/N in the record changed to 0/24" "--match=citation disagrees" run_with "${manifest}" "${cite}"

# ---- 7. the coordinated edit: the manifest AND the script's own expectation,
# the way someone tidying up would do it. This is the one that passed before the
# counts were anchored outside both files.
m="${scratch}/m-coord.txt"
g="${here}/.obc-coordinated-control.sh"
mut_begin "coordinated edit: manifest and script expectation together" "${m}"
grep -v '^mt mt02 ' "${manifest}" | sed 's/^#   mt         5 /#   mt         4 /' > "${m}"
sed 's/^EXPECT_MT=5;/EXPECT_MT=4;/' "${guard}" > "${g}"
chmod +x "${g}"
trap 'rm -rf "${scratch}" "${g}"' EXIT HUP INT TERM
if ! grep -q 'EXPECT_MT=4;' "${g}"; then
    mut_noapply "coordinated edit: manifest and script expectation together" "the script edit did not apply"
else
    run_coord() { OUTSIDE_BATTERY_CORPUS="${m}" OUTSIDE_BATTERY_WORK="${work}" "${g}"; }
    mut_expect_fail "coordinated edit: manifest and script expectation together" "--match=citation disagrees" run_coord
fi
rm -f "${g}"

# ---- the restored control
mut_expect_pass "restored control: the pinned corpus is accepted again" run_with "${manifest}"

mut_summary "outside-battery-mutation-test"
