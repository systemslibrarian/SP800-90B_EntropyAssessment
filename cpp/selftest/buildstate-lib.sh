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
# THE PROBE, AND HOW IT AVOIDS MOVING THE PAROCHIALISM ONE LAYER DOWN
#
# `assert` leaves an undefined symbol in any binary compiled without -DNDEBUG
# and none in one compiled with it. That is structural -- a linker symbol, not
# emitted text -- so unlike the canary's first signature it survives the source
# changing and works for all three tools. But the SYMBOL NAME is itself
# platform-specific:
#
#   glibc / Linux      __assert_fail
#   Darwin / BSD       __assert_rtn, __assert
#   MSVC               _wassert
#
# so a probe keyed on a name list can fail exactly the way the message-text
# canary failed, one layer down -- and worse, SILENTLY, reading "no symbol I
# recognise" as a confident NDEBUG. Absence of a symbol it was not looking for
# is no answer at all.
#
# So the probe CALIBRATES ITSELF on the host before any verdict is trusted: it
# compiles two tiny programs, one with a reachable assert and one with -DNDEBUG,
# and requires its pattern to match the first and not the second. If that
# discrimination cannot be demonstrated -- no compiler, no nm, an unfamiliar
# naming scheme -- every verdict becomes UNKNOWN and bs_require REFUSES. That is
# the canary's INDETERMINATE rule applied here: a probe that cannot establish
# its answer reports that it cannot (OC-45).
#
# The canary (tools/build-provenance-canary.sh) is stronger where it applies,
# because it also separates the repaired tree from the unrepaired one, but it
# classifies `ea_iid` only. Use both where both apply.
#
# USAGE
#
#   . "$(dirname "$0")/buildstate-lib.sh"
#   bs_calibration                      # print whether the probe can discriminate here
#   bs_print  <binary> [...]            # one precondition line per binary
#   bs_require <binary> LIVE|NDEBUG     # refuse on mismatch, exit 2
#   bs_canary <path-to-ea_iid> REPAIRED|UNREPAIRED   # when the canary applies
#
# bs_require is for a measurement that deliberately uses a particular build:
# declare which, and a mismatch refuses rather than proceeding.

BS_PATTERN='assert'          # matched case-insensitively against nm -u output
BS_CALIBRATED=''             # yes | no, set by bs_calibrate
BS_CAL_NOTE=''

bs_calibrate() {
    [ -n "${BS_CALIBRATED}" ] && return 0
    BS_CALIBRATED=no
    local cc d live ndebug
    if ! command -v nm >/dev/null 2>&1; then BS_CAL_NOTE='no nm on this host'; return 0; fi
    cc=''
    for c in cc gcc clang c99; do if command -v "$c" >/dev/null 2>&1; then cc=$c; break; fi; done
    [ -z "${cc}" ] && { BS_CAL_NOTE='no C compiler to calibrate with'; return 0; }
    d=$(mktemp -d "${TMPDIR:-/tmp}/bscal.XXXXXX") || { BS_CAL_NOTE='no temp dir'; return 0; }
    printf '#include <assert.h>\nint main(int c,char**v){assert(c>0);return (int)(long)v;}\n' > "$d/p.c"
    if ! "$cc" -O0 -o "$d/live" "$d/p.c" 2>/dev/null \
       || ! "$cc" -O0 -DNDEBUG -o "$d/nd" "$d/p.c" 2>/dev/null; then
        BS_CAL_NOTE='calibration programs did not build'; rm -rf "$d"; return 0
    fi
    live=$(nm -u "$d/live" 2>/dev/null | grep -ci "${BS_PATTERN}")
    ndebug=$(nm -u "$d/nd" 2>/dev/null | grep -ci "${BS_PATTERN}")
    if [ "${live:-0}" -gt 0 ] && [ "${ndebug:-0}" -eq 0 ]; then
        BS_CALIBRATED=yes
        BS_CAL_NOTE="pattern /${BS_PATTERN}/i discriminates; asserts-live symbol here is $(nm -u "$d/live" 2>/dev/null | grep -i "${BS_PATTERN}" | head -1 | tr -s ' ' | sed 's/^ *//')"
    else
        BS_CAL_NOTE="pattern /${BS_PATTERN}/i does NOT discriminate on this host (live=${live:-0} ndebug=${ndebug:-0}); the symbol is named something this probe does not know"
    fi
    rm -rf "$d"
    return 0
}

bs_calibration() {
    bs_calibrate
    printf '[build-state] calibration: %s -- %s\n' \
        "$([ "${BS_CALIBRATED}" = yes ] && echo OK || echo FAILED)" "${BS_CAL_NOTE}"
}

bs_sha() {
    if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
    elif command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else echo "unknown-no-sha256-tool"; fi
}

# LIVE | NDEBUG | UNKNOWN. NDEBUG is returned ONLY when the pattern has been
# shown to discriminate on this host and nm produced symbols to look through.
# Otherwise UNKNOWN: never conclude from an absence that was not calibrated for.
bs_asserts() {
    [ -x "$1" ] || { echo UNKNOWN; return; }
    bs_calibrate
    [ "${BS_CALIBRATED}" = yes ] || { echo UNKNOWN; return; }
    local u n
    u=$(nm -u "$1" 2>/dev/null)
    [ -z "${u}" ] && { echo UNKNOWN; return; }   # stripped, unreadable, or not an object file
    n=$(printf '%s\n' "${u}" | grep -ci "${BS_PATTERN}")
    if [ "${n}" -gt 0 ]; then echo LIVE; else echo NDEBUG; fi
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
    if [ "${got}" = UNKNOWN ]; then
        echo "[build-state] REFUSED: the build state of ${b} CANNOT BE ESTABLISHED here." >&2
        echo "[build-state]           ${BS_CAL_NOTE}" >&2
        echo "[build-state]           A probe that cannot establish its answer says so; it does" >&2
        echo "[build-state]           not read absence as NDEBUG (OC-45)." >&2
        exit 2
    fi
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
