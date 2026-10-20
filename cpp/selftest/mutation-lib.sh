# mutation-lib.sh -- sourced by every mutation harness in this directory.
# Not a regression script: the name deliberately does not match regression-*.sh,
# so run-all-checks.sh's authoritative inventory does not discover it.
#
# WHY THIS EXISTS
#
# "Show that the mutation landed" was adopted as a rule after OC-23 and was,
# until now, a thing to remember. It was forgotten repeatedly, and every time it
# was forgotten the harness reported a verdict it had not earned:
#
#   OC-23  a sed edited the wrong line; the run PASSED and the mutation was
#          recorded as not caught until the sed was fixed.
#   OC-23  two extraction patterns matched the wrong number inside a longer
#          string ("256" out of "SHA-256", "731" out of "5.731"), and one
#          searched for a stream name the generator builds from a format
#          string: three false FAILURES.
#   OC-30  a broken hex literal meant the matrix generator wrote no files, and
#          every cell printed REFUSED -- a uniform, plausible-looking column
#          that actually meant "no input".
#   OC-31  a route-2 test passed "./--version" where the code matched
#          "--version"; it PASSED against the build it was supposed to fail.
#
# That is roughly one instrument error per round of work, every round, found
# only by looking. A process with that base rate must not assume it finds them
# all, so the rule is mechanised here instead of remembered.
#
# THE CONTRACT
#
# A mutation that did not land may produce NEITHER a pass NOR a fail. It
# produces a third outcome, MUTATION-DID-NOT-APPLY, which is counted separately
# and fails the harness. The guard's response is evaluated only after the
# mutation is shown to have taken effect:
#
#   * for a mutation to a FILE or DIRECTORY, by comparing digests before and
#     after (mut_begin / mut_expect_*);
#   * for a mutation to an ARGUMENT or INPUT, by asserting the value the code
#     under test actually received, not the value the harness meant to send
#     (mut_value), which is precisely what the OC-31 route-2 test got wrong;
#   * for a mutation applied by REBUILDING with different flags, by asserting
#     the binary differs from the clean build (mut_binary).
#
# AND THE BASELINE MUST BE ASSERTED ACCEPTED (OC-54).
#
# A fourth way to earn a verdict you did not deserve, found when an outside
# audit was reproduced: four negative fixtures, each built FROM SCRATCH to
# trigger a different refusal, were all refused for ONE SHARED ACCIDENTAL
# REASON -- they used the wrong key for the test-case label, so every one died
# on "no test case labelled Overall" and not one of the four properties was
# exercised. Four refusals for the wrong reason is indistinguishable from four
# working guards, and stopping there would have meant reporting a real finding
# as already fixed.
#
# So: mut_baseline asserts that the UNMUTATED artifact is ACCEPTED, before any
# negative is tried. A fixture set that refuses everything then fails as broken
# instead of passing as thorough. Build negatives by MUTATING a genuine
# artifact one field at a time, so a refusal is attributable to the one thing
# that changed.
#
# USAGE
#
#   . "$(dirname "$0")/mutation-lib.sh"
#   mut_baseline "the pinned corpus" some_command --args   # MUST be accepted
#   mut_begin "deleted script" "$root/cpp/selftest/regression-docs.sh"
#   rm "$root/cpp/selftest/regression-docs.sh"
#   mut_expect_fail "deleted script" some_command --args
#   ...
#   mut_summary "harness-name"   # prints the tally and returns the exit status

MUT_PASS=0
MUT_BASELINE_OK=""      # yes once an unmutated baseline has been shown accepted
MUT_NEGATIVE_SEEN=""    # yes once any negative fixture has been evaluated
MUT_FAIL=0
MUT_NOAPPLY=0
MUT_FAIL_LABELS=""
MUT_NOAPPLY_LABELS=""
MUT_TARGET=""
MUT_BEFORE=""

mut_note() { printf '  %-54s %s\n' "$1" "$2"; }

# mut_baseline <label> <cmd...> -- the UNMUTATED artifact must be ACCEPTED.
#
# Call this BEFORE any negative fixture. It is the control that makes every
# later refusal attributable: if the baseline is refused, the fixtures share a
# defect that has nothing to do with the properties under test, and the harness
# says so rather than counting a wall of refusals as thoroughness (OC-54).
mut_baseline() {
    local label=$1; shift
    if "$@" >/dev/null 2>&1; then
        MUT_BASELINE_OK=yes
        mut_note "baseline: ${label}" "ACCEPTED -- later refusals are attributable"
    else
        MUT_BASELINE_OK=no
        MUT_FAIL=$((MUT_FAIL + 1))
        MUT_FAIL_LABELS="${MUT_FAIL_LABELS} baseline:${label}"
        mut_note "baseline: ${label}" "*** REFUSED -- the FIXTURES are broken, not the guard ***"
        echo "  mutation-lib: the unmutated baseline was refused. Every negative result below" >&2
        echo "  is unattributable: a shared accidental refusal reason looks exactly like a" >&2
        echo "  working guard (OC-54). Fix the fixture construction before reading anything." >&2
    fi
}

# Digest of a file, or of a directory's complete contents and layout. A missing
# target digests as ABSENT, which is itself a change worth detecting.
mut_digest() {
    if [ -d "$1" ]; then
        ( cd "$1" && find . -print0 2>/dev/null | sort -z | while IFS= read -r -d '' f; do
            if [ -f "$f" ]; then printf '%s %s\n' "$f" "$(mut_sha "$f")"; else printf '%s DIR\n' "$f"; fi
          done ) | mut_sha -
    elif [ -e "$1" ]; then
        mut_sha "$1"
    else
        printf 'ABSENT'
    fi
}

mut_sha() {
    if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
    elif command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else echo "mutation-lib: no SHA-256 utility" >&2; exit 2; fi
}

# Snapshot the target before the mutation is applied.
mut_begin() {
    MUT_TARGET="$2"
    MUT_BEFORE="$(mut_digest "$2")"
}

mut_noapply() {
    mut_note "$1" "MUTATION-DID-NOT-APPLY ($2)"
    MUT_NOAPPLY=$((MUT_NOAPPLY + 1))
    MUT_NOAPPLY_LABELS="${MUT_NOAPPLY_LABELS} $1"
}

mut_landed() {
    [ -n "${MUT_TARGET}" ] || { mut_noapply "$1" "mut_begin was never called"; return 1; }
    if [ "$(mut_digest "${MUT_TARGET}")" = "${MUT_BEFORE}" ]; then
        mut_noapply "$1" "${MUT_TARGET} is unchanged"
        return 1
    fi
    return 0
}

# The guard must reject the mutated state: nonzero exit, and optionally a
# message matching a pattern.
mut_expect_fail() {
    MUT_NEGATIVE_SEEN=yes
    local label=$1; shift
    local pattern=""
    case "$1" in --match=*) pattern="${1#--match=}"; shift ;; esac
    mut_landed "${label}" || return 1
    local out rc
    out=$("$@" 2>&1); rc=$?
    if [ "${rc}" -eq 0 ]; then
        mut_note "${label}" "FAIL (the guard accepted the mutated state)"
        MUT_FAIL=$((MUT_FAIL + 1)); MUT_FAIL_LABELS="${MUT_FAIL_LABELS} ${label}"
        return 1
    fi
    if [ -n "${pattern}" ] && ! printf '%s' "${out}" | grep -q -- "${pattern}"; then
        mut_note "${label}" "FAIL (rejected, but not for the stated reason: want '${pattern}')"
        MUT_FAIL=$((MUT_FAIL + 1)); MUT_FAIL_LABELS="${MUT_FAIL_LABELS} ${label}"
        return 1
    fi
    mut_note "${label}" "rejected (exit ${rc})"
    MUT_PASS=$((MUT_PASS + 1))
    return 0
}

# The positive control: the UNmutated state must be accepted. No landing check,
# because nothing was mutated.
mut_expect_pass() {
    # A positive control that passes BEFORE any negative has been tried is
    # exactly the baseline rule 7 requires, so recognise it rather than making
    # every harness say the same thing twice. After a negative it is a
    # "restored" control, which is a different and weaker claim: it shows the
    # mutations did not leak, not that the construction was ever sound.
    local label=$1; shift
    local out rc
    out=$("$@" 2>&1); rc=$?
    if [ "${rc}" -ne 0 ]; then
        mut_note "${label}" "FAIL (positive control rejected, exit ${rc})"
        MUT_FAIL=$((MUT_FAIL + 1)); MUT_FAIL_LABELS="${MUT_FAIL_LABELS} ${label}"
        return 1
    fi
    mut_note "${label}" "accepted"
    MUT_PASS=$((MUT_PASS + 1))
        [ -z "${MUT_NEGATIVE_SEEN}" ] && MUT_BASELINE_OK=yes
    return 0
}

# A mutation to a value rather than a file: assert the value the code under test
# RECEIVED equals the value the harness intended. <observed> must be read back
# from the system under test (an echoed command line, a recorded filename, a
# printed parameter), never re-derived from the harness's own variable.
mut_value() {
    local label=$1 intended=$2 observed=$3
    if [ "${intended}" != "${observed}" ]; then
        mut_noapply "${label}" "intended '${intended}' but the code received '${observed}'"
        return 1
    fi
    return 0
}

mut_summary() {
    if [ -z "${MUT_BASELINE_OK}" ]; then
        MUT_FAIL=$((MUT_FAIL + 1))
        MUT_FAIL_LABELS="${MUT_FAIL_LABELS} no-baseline-asserted"
        mut_note "baseline" "*** NEVER ASSERTED -- this harness cannot attribute its refusals ***"
    fi
    local name=$1
    local total=$((MUT_PASS + MUT_FAIL + MUT_NOAPPLY))
    printf '%s: %d of %d mutations landed and were caught' "${name}" "${MUT_PASS}" "${total}"
    [ "${MUT_FAIL}" -ne 0 ] && printf ', %d NOT CAUGHT' "${MUT_FAIL}"
    [ "${MUT_NOAPPLY}" -ne 0 ] && printf ', %d DID NOT APPLY' "${MUT_NOAPPLY}"
    printf '\n'
    [ "${MUT_FAIL}" -ne 0 ] && printf '%s: not caught:%s\n' "${name}" "${MUT_FAIL_LABELS}"
    [ "${MUT_NOAPPLY}" -ne 0 ] && printf '%s: did not apply (the harness is broken, not the guard):%s\n' "${name}" "${MUT_NOAPPLY_LABELS}"
    if [ "${MUT_FAIL}" -eq 0 ] && [ "${MUT_NOAPPLY}" -eq 0 ]; then
        printf '%s: PASS\n' "${name}"
        return 0
    fi
    printf '%s: FAIL\n' "${name}"
    return 1
}
