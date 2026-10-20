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
#   MinGW / MSVCRT     _assert, __imp__assert   (MEASURED on windows-latest)
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

BS_PATTERN='assert'          # matched case-insensitively against the symbol listing
BS_CALIBRATED=''             # yes | no, set by bs_calibrate
BS_MODE=''                   # undefined | full -- which listing discriminates here
BS_CAL_NOTE=''

# TWO LISTINGS, TRIED IN ORDER OF STRENGTH (OC-48).
#
# `nm -u` is the right question on ELF and Mach-O: an undefined symbol is a
# structural fact about what the binary must import, and nothing unrelated can
# masquerade as one. On PE/COFF it is blind -- a linked .exe resolves imports
# through an import table, so Windows gave an EMPTY /assert/i match for a
# binary that plainly had a reachable assert, and the probe refused. Refusing
# was correct. But the Windows run also measured that a FULL listing does
# discriminate there:
#
#   nm cal_live.exe | grep -i assert  ->  __imp__assert, _assert   (2)
#   nm cal_nd.exe   | grep -i assert  ->                           (0)
#
# so the platform can be taught, and that is an improvement rather than a
# correction. The full listing is WEAKER: any symbol whose name merely contains
# "assert" would read as LIVE, where an undefined-symbol match could not. So it
# is only ever the fallback, it must pass the same calibration, and every line
# produced through it is marked `via=full` so a reader can see which question
# was answered.
bs_syms() { # bs_syms <mode> <binary>
    case "$1" in
        undefined) nm -u "$2" 2>/dev/null ;;
        full)      nm    "$2" 2>/dev/null ;;
    esac
}

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
    # RESOLVE THE ARTEFACT WITH THE TOOL THAT WILL READ IT, NOT WITH THE SHELL.
    #
    # On MinGW gcc appends .exe when -o carries no suffix, so the compiler
    # returns 0 having written `live.exe`. The first attempt at this resolved
    # the name with `[ -f ]`, and that was wrong in a way worth recording: the
    # MSYS runtime resolves `live` to `live.exe` for stat(), so the shell said
    # the bare name existed, while native `nm`, handed the same string, looked
    # for a Win32 path that was not there and printed nothing -- with stderr
    # suppressed, indistinguishable from "this pattern does not discriminate".
    # The debug output showed `ls` listing live.exe and the resolver claiming
    # live, in the same block.
    #
    # So the resolution test must BE the use: pick the candidate `nm` can
    # actually read. Asking one layer a question and handing the answer to a
    # different layer is the error this whole audit is about (OC-48).
    bs_readable() { # bs_readable <base> -- echo the candidate nm can read
        local c
        for c in "$1" "$1.exe"; do
            [ -n "$(nm "$c" 2>/dev/null | head -1)" ] && { printf '%s' "$c"; return 0; }
        done
        return 1
    }
    local lb nb
    if ! lb=$(bs_readable "$d/live") || ! nb=$(bs_readable "$d/nd"); then
        BS_CAL_NOTE="the compiler reported success but nm could read neither calibration artefact (tried the bare name and .exe); nm said: $(nm "$d/live" 2>&1 | head -1)"
        rm -rf "$d"; return 0
    fi
    if [ -n "${BS_DEBUG:-}" ]; then
        printf '[build-state:debug] compiler=%s (%s)\n' "$cc" "$(command -v "$cc")" >&2
        printf '[build-state:debug] dir=%s\n' "$d" >&2
        ls -la "$d" >&2
        printf '[build-state:debug] live artefact=%s (exists=%s)  ndebug artefact=%s (exists=%s)\n' \
            "$lb" "$([ -f "$lb" ] && echo yes || echo no)" \
            "$nb" "$([ -f "$nb" ] && echo yes || echo no)" >&2
        printf '[build-state:debug] nm --version: %s\n' "$(nm --version 2>&1 | head -1)" >&2
        for dm in undefined full; do
            printf '[build-state:debug] %s listing, live, first 6 lines:\n' "$dm" >&2
            bs_syms "$dm" "$lb" | head -6 | sed 's/^/[build-state:debug]   /' >&2
            printf '[build-state:debug] %s listing, live, /assert/i matches: %s\n' \
                "$dm" "$(bs_syms "$dm" "$lb" | grep -ci assert)" >&2
        done
    fi
    local m
    for m in undefined full; do
        live=$(bs_syms "$m" "$lb"  | grep -ci "${BS_PATTERN}")
        ndebug=$(bs_syms "$m" "$nb" | grep -ci "${BS_PATTERN}")
        if [ "${live:-0}" -gt 0 ] && [ "${ndebug:-0}" -eq 0 ]; then
            BS_CALIBRATED=yes
            BS_MODE=$m
            BS_CAL_NOTE="pattern /${BS_PATTERN}/i discriminates in the ${m}-symbol listing; asserts-live symbol here is $(bs_syms "$m" "$lb" | grep -i "${BS_PATTERN}" | head -1 | tr -s ' ' | sed 's/^ *//')"
            [ "$m" = full ] && BS_CAL_NOTE="${BS_CAL_NOTE} -- NOTE: the undefined-symbol listing is blind on this platform (PE/COFF), so this is the weaker full-listing test"
            break
        fi
        BS_CAL_NOTE="pattern /${BS_PATTERN}/i does NOT discriminate on this host (${m} listing: live=${live:-0} ndebug=${ndebug:-0}); the symbol is named something this probe does not know"
    done
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
    local u n t
    t=$1
    for c in "$1" "$1.exe"; do
        if [ -n "$(nm "$c" 2>/dev/null | head -1)" ]; then t=$c; break; fi
    done
    u=$(bs_syms "${BS_MODE}" "$t")
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
        printf '[build-state] %-34s asserts=%-7s sha256=%s%s\n' \
            "$(basename "$b")" "$(bs_asserts "$b")" "$(bs_sha "$b" | cut -c1-16)" \
            "$([ "${BS_MODE}" = full ] && echo ' via=full')"
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
