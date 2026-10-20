# buildstate-lib.sh -- sourced. Build state as a PRINTED PRECONDITION.
# Not a regression script: the name does not match regression-*.sh, so
# run-all-checks.sh's authoritative inventory does not discover it.
#
# WHY THIS EXISTS
#
# Four of this project's instrument errors were not wrong ideas. They were
# measurements taken against an artefact that was not the one intended:
#
#   OC-42  a "could not reproduce R-1 on arm64" taken against the tag
#          worktree's -DNDEBUG binary, with the assert compiled out. The
#          provenance canary would have said BUILD NDEBUG. It was not run.
#   OC-30  a matrix that printed a wall of REFUSED because a broken hex
#          literal meant its generator wrote no input files at all.
#   OC-23  a mutation whose sed edited the wrong line, so the "unmutated"
#          file under test was the mutated one's twin.
#   OC-41  a blast-radius figure from a harness that RE-IMPLEMENTED the two
#          production functions instead of calling them, and disagreed with
#          the tool.
#
# The common shape: **a measurement is about the artefact it ran against, and
# an artefact whose build state was not established is not evidence about the
# source.** So build state is printed with the result rather than remembered,
# and a result without its precondition line is visibly incomplete.
#
# THE PROBE
#
# `assert` leaves an undefined symbol (`__assert_fail` on glibc,
# `___assert_rtn` on Darwin) in any binary compiled without -DNDEBUG, and none
# in one compiled with it. That is structural -- a linker symbol, not emitted
# text -- so it works for all three tools and survives the source changing.
# The canary (tools/build-provenance-canary.sh) is stronger where it applies,
# because it also separates the repaired tree from the unrepaired one, but it
# classifies `ea_iid` only. Use both where both apply.
#
# USAGE
#
#   . "$(dirname "$0")/buildstate-lib.sh"
#   bs_print  <binary> [...]            # one precondition line per binary
#   bs_require <binary> LIVE|NDEBUG     # refuse on mismatch, exit 2
#   bs_canary <path-to-ea_iid> REPAIRED|UNREPAIRED   # when the canary applies
#
# bs_require is for a measurement that deliberately uses a particular build:
# declare which, and a mismatch refuses rather than proceeding.

bs_sha() {
    if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
    elif command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else echo "unknown-no-sha256-tool"; fi
}

# LIVE | NDEBUG | UNKNOWN
bs_asserts() {
    [ -x "$1" ] || { echo UNKNOWN; return; }
    if ! command -v nm >/dev/null 2>&1; then echo UNKNOWN; return; fi
    if [ "$(nm -u "$1" 2>/dev/null | grep -ci 'assert')" -gt 0 ]; then echo LIVE; else echo NDEBUG; fi
}

bs_print() {
    local b
    for b in "$@"; do
        if [ ! -e "$b" ]; then
            printf '[build-state] %-34s MISSING -- no measurement against this binary is interpretable\n' "$(basename "$b")"
            continue
        fi
        printf '[build-state] %-34s asserts=%-7s sha256=%s\n' \
            "$(basename "$b")" "$(bs_asserts "$b")" "$(bs_sha "$b" | cut -c1-16)"
    done
}

bs_require() { # bs_require <binary> <LIVE|NDEBUG>
    local b=$1 want=$2 got
    if [ ! -x "$b" ]; then
        echo "[build-state] REFUSED: $b is not an executable; nothing can be concluded from it." >&2
        exit 2
    fi
    got=$(bs_asserts "$b")
    printf '[build-state] %-34s asserts=%-7s sha256=%s  (required %s)\n' \
        "$(basename "$b")" "${got}" "$(bs_sha "$b" | cut -c1-16)" "${want}"
    if [ "${got}" != "${want}" ]; then
        echo "[build-state] REFUSED: ${b} has asserts=${got} but this measurement requires ${want}." >&2
        echo "[build-state]           A result from the wrong build is not a result (OC-43)." >&2
        exit 2
    fi
}

bs_canary() { # bs_canary <ea_iid> <REPAIRED|UNREPAIRED>
    local b=$1 want=$2 repo tree
    repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
    if [ ! -x "${repo}/tools/build-provenance-canary.sh" ]; then
        echo "[build-state] canary unavailable; asserts probe only" >&2
        return 0
    fi
    tree=$("${repo}/tools/build-provenance-canary.sh" "$b" 2>/dev/null \
           | sed -n 's/^canary: TREE *//p' | head -1)
    printf '[build-state] %-34s canary TREE=%-14s (required %s)\n' \
        "$(basename "$b")" "${tree:-UNAVAILABLE}" "${want}"
    if [ -n "${want}" ] && [ "${tree}" != "${want}" ]; then
        echo "[build-state] REFUSED: ${b} classifies as ${tree:-UNAVAILABLE}, not ${want}." >&2
        exit 2
    fi
}
