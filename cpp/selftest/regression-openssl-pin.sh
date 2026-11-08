#!/bin/bash
#
# Regression for PROV-15 (aggressive audit, 2026-11-07): the OpenSSL pin was
# defeated by include/link ORDER.
#
# WHY. cpp/Makefile's Darwin block names openssl@3 (OPENSSL_PREFIX), and
# BUILDING.md's dependency table pins it, but both -I and -L listed the GENERIC
# Homebrew prefix first:
#
#     INC     += -I$(BREW_PREFIX)/include -I$(OPENSSL_PREFIX)/include
#     LDFLAGS += -L$(BREW_PREFIX)/lib     -L$(OPENSSL_PREFIX)/lib
#
# and the generic prefix is where Homebrew links the UNVERSIONED `openssl`
# formula. On 2026-11-07 installing afl++ pulled in openssl@4 and re-pointed
# /opt/homebrew/include/openssl and /opt/homebrew/lib/libcrypto.dylib at 4.1.0;
# the three production binaries built that minute load
# /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib (otool -L, 3 of 3), while
# cpp/ea_conditioning built from the SAME Makefile on 2026-10-20 loads the
# pinned libcrypto.3.dylib. Same recipe, different day, different library: the
# host decided, not the Makefile. No estimator figure moves -- OpenSSL computes
# only the SHA-256 of the input -- but the binaries' sha256 changed with no
# source change, and the pin table was false for them.
#
# WHAT THIS CHECKS, in two halves:
#
#   1. the Makefile's dry-run (`make -n non_iid`, written to a file and read
#      back, rule 17): on the ea_non_iid compile line the pinned prefix's -I
#      precedes the generic prefix's -I, and likewise for -L. This half fails
#      against master's Makefile TEXT whatever is installed, so it does not
#      need openssl@4 present to be shown failing (see the commit).
#   2. the built binaries, where present: `otool -L` names exactly one
#      libcrypto load command, and it is under the pinned prefix.
#
# The prefixes are derived the way the Makefile derives them and then passed to
# make EXPLICITLY, so the tokens asserted below are the ones the Makefile was
# given rather than whatever `?=` would have found.
#
# RULE 12 DECLARATION. This change moves two lines that d240098 (NOTICE,
# 2026-09-30, "cpp/Makefile: on macOS add Homebrew's include and library
# prefixes, and OpenSSL 3's keg-only prefix") introduced. That repair's job is
# that libdivsufsort, jsoncpp and openssl@3 are FOUND at all; this one changes
# only the order. PAIR TEST: all four -I/-L tokens must still be on the compile
# line, each exactly once -- only their order may have changed.
#
# PLATFORM. The pin lives in the Makefile's Darwin block only; elsewhere the
# Makefile names no OpenSSL prefix and there is no order to assert. Off macOS
# this exits 2 -- COULD NOT RUN, which run-all-checks.sh reports apart from
# both pass and fail -- the way regression-platform-deltas.sh abstains on
# Linux (OC-66). A skip that returned 0 would be counted as a pass, and that
# is instrument rule 2's defect wearing a platform guard.
#
# SEAMS, so the check can be pointed at another build and shown FAILING:
#   REGRESSION_OPENSSL_PIN_MAKEFILE  the Makefile to dry-run   (default ../Makefile)
#   REGRESSION_OPENSSL_PIN_BINDIR    where the binaries are     (default ..)
#   REGRESSION_OPENSSL_PIN_DRYRUN    a captured `make -n` transcript to read
#                                    instead of running make (the source used
#                                    is printed either way)

set -u

here=$(cd "$(dirname "$0")" && pwd)
# instrument rule 5, mechanised (OC-73)
. "${here}/labelread-lib.sh"
# instrument rule 4: a measurement names the artefact it was taken from
. "${here}/buildstate-lib.sh"

host=$(uname -s)
if [ "${host}" != "Darwin" ]; then
    echo "regression-openssl-pin: the OpenSSL pin lives in cpp/Makefile's Darwin block only. On"
    echo "  ${host} the Makefile names no OpenSSL prefix and there is no -I/-L order to assert, so"
    echo "  nothing here can be checked. COULD NOT RUN (exit 2): neither a pass nor a failure."
    exit 2
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/ea-opensslpin.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM
fails=0
notmeasured=0
pass() { printf '  %-66s PASS\n' "$1"; }
fail() { printf '  %-66s FAIL  %s\n' "$1" "${2:-}"; fails=$((fails + 1)); }

# The two prefixes, derived as the Makefile derives them (same command, same
# fallback). They must differ, or "which comes first" is not a question.
generic=$(brew --prefix 2>/dev/null) || generic=/opt/homebrew
pinned=$(brew --prefix openssl@3 2>/dev/null) || pinned="${generic}/opt/openssl@3"
[ -n "${generic}" ] || generic=/opt/homebrew
[ -n "${pinned}" ] || pinned="${generic}/opt/openssl@3"
echo "  generic Homebrew prefix: ${generic}"
echo "  pinned OpenSSL prefix:   ${pinned}"
if [ "${pinned}" = "${generic}" ]; then
    echo "regression-openssl-pin: the pinned and generic prefixes coincide (${pinned}); the" >&2
    echo "  order of two identical paths asserts nothing. COULD NOT RUN (exit 2)." >&2
    exit 2
fi

echo
echo "== 1. the Makefile's dry-run: the pinned prefix precedes the generic one on -I and -L =="
dry="${work}/dryrun.txt"
if [ -n "${REGRESSION_OPENSSL_PIN_DRYRUN:-}" ]; then
    cp "${REGRESSION_OPENSSL_PIN_DRYRUN}" "${dry}" 2>/dev/null || {
        echo "regression-openssl-pin: cannot read REGRESSION_OPENSSL_PIN_DRYRUN=${REGRESSION_OPENSSL_PIN_DRYRUN}" >&2
        exit 2; }
    echo "  dry-run source: REGRESSION_OPENSSL_PIN_DRYRUN=${REGRESSION_OPENSSL_PIN_DRYRUN} (make was NOT run)"
else
    mf="${REGRESSION_OPENSSL_PIN_MAKEFILE:-${here}/../Makefile}"
    [ -f "${mf}" ] || { echo "regression-openssl-pin: no Makefile at ${mf}" >&2; exit 2; }
    mf="$(cd "$(dirname "${mf}")" && pwd)/$(basename "${mf}")"
    cppdir=$(cd "${here}/.." && pwd)
    # RULE 17: the plan is written to a file and read from the file, and the
    # producer's own exit status is read -- never `make -n | grep`. The
    # environment's LDFLAGS/CXXFLAGS are unset so `+=` appends to the
    # Makefile's values and not to whatever the caller's shell carried.
    ( unset LDFLAGS CXXFLAGS CPPFLAGS INC
      make -n -C "${cppdir}" -f "${mf}" BREW_PREFIX="${generic}" OPENSSL_PREFIX="${pinned}" non_iid
    ) > "${dry}" 2> "${work}/dryrun.err"
    rc=$?
    echo "  dry-run source: make -n -f ${mf} non_iid  (make exit ${rc})"
    if [ "${rc}" -ne 0 ]; then
        echo "regression-openssl-pin: make -n exited ${rc}; a plan that was not produced cannot be read." >&2
        sed 's/^/    /' "${work}/dryrun.err" >&2
        exit 2
    fi
fi

# INSTRUMENT RULE 2 before any order is read: the plan must contain the
# ea_non_iid compile line, and INSTRUMENT RULE 5: exactly one of it. An empty
# plan (a stale .o, a target that no longer exists) is not evidence of order.
line=$(grep -E 'non_iid_main\.cpp -o ea_non_iid( |$)' "${dry}" \
       | lr_one "the ea_non_iid compile line in the dry-run") || {
    echo "regression-openssl-pin: the dry-run holds no readable ea_non_iid compile line; COULD NOT RUN (exit 2)." >&2
    exit 2; }
printf '  compile line: %s\n' "${line}"
printf '%s\n' "${line}" | tr ' \t' '\n\n' | grep -v '^$' > "${work}/tokens.txt"

tokpos() { # tokpos <token> -- its 1-based position on the compile line, required exactly once
    grep -nxF -- "$1" "${work}/tokens.txt" | sed 's/:.*//' | lr_one "token $1 on the compile line"
}

# PAIR TEST (rule 12, d240098): every one of the four tokens is still there,
# exactly once. Only their order is this repair's business.
tokens_ok=1
iP=""; iG=""; lP=""; lG=""
for want in "iP=-I${pinned}/include" "iG=-I${generic}/include" "lP=-L${pinned}/lib" "lG=-L${generic}/lib"; do
    var=${want%%=*}; tok=${want#*=}
    if p=$(tokpos "${tok}" 2> "${work}/lr.err"); then
        pass "PAIR d240098: ${tok} is on the line once (token ${p})"
        eval "${var}=\${p}"
    else
        fail "PAIR d240098: ${tok} on the line exactly once" "$(tr '\n' ' ' < "${work}/lr.err")"
        tokens_ok=0
    fi
done

if [ "${tokens_ok}" -eq 1 ]; then
    if [ "${iP}" -lt "${iG}" ]; then
        pass "-I: the pinned prefix (token ${iP}) precedes the generic one (token ${iG})"
    else
        fail "-I: the pinned prefix precedes the generic one" \
             "generic at token ${iG}, pinned at ${iP}: the preprocessor takes ${generic}/include/openssl first, whatever formula Homebrew linked there"
    fi
    if [ "${lP}" -lt "${lG}" ]; then
        pass "-L: the pinned prefix (token ${lP}) precedes the generic one (token ${lG})"
    else
        fail "-L: the pinned prefix precedes the generic one" \
             "generic at token ${lG}, pinned at ${lP}: -lcrypto resolves to ${generic}/lib/libcrypto.dylib first, whatever it points at today"
    fi
else
    fail "the -I/-L order (not read: a token was missing or duplicated above)" ""
fi

echo
echo "== 2. the built binaries: libcrypto is loaded from the pinned prefix =="
bindir="${REGRESSION_OPENSSL_PIN_BINDIR:-${here}/..}"
present=0
for t in ea_non_iid ea_iid ea_restart; do
    b="${bindir}/${t}"
    if [ ! -x "${b}" ]; then
        printf '  %-66s not built here; not measured\n' "${t}"
        continue
    fi
    present=$((present + 1))
    bs_print "${b}"
    otool -L "${b}" > "${work}/otool_${t}.txt" 2> "${work}/otool_${t}.err"
    rc=$?
    if [ "${rc}" -ne 0 ]; then
        printf '  %-66s otool -L exited %s; not measured\n' "${t}" "${rc}"
        sed 's/^/        /' "${work}/otool_${t}.err"
        notmeasured=1
        continue
    fi
    # Anchored on the library's name and otool's own "(compatibility" marker,
    # never on a line number or a field position.
    lc=$(sed -n 's/^[[:space:]]*\([^[:space:]]*libcrypto[^[:space:]]*\) (compatibility .*/\1/p' \
             "${work}/otool_${t}.txt" | lr_one "the libcrypto load command of ${t}" 2> "${work}/lr.err") || {
        fail "${t}: exactly one libcrypto load command" "$(tr '\n' ' ' < "${work}/lr.err")"
        continue; }
    case "${lc}" in
        "${pinned}"/*) pass "${t} loads ${lc}" ;;
        *) fail "${t} loads libcrypto from the pinned prefix" "loads ${lc}; the pin is ${pinned}" ;;
    esac
done
if [ "${present}" -eq 0 ]; then
    echo "  no built binary in ${bindir}: the load command was not measured (the Makefile text was)."
    notmeasured=1
fi

echo
if [ "${fails}" -ne 0 ]; then
    echo "regression-openssl-pin: FAIL (${fails})"
    exit 1
fi
if [ "${notmeasured}" -ne 0 ]; then
    echo "regression-openssl-pin: the Makefile text passed, but no binary was measured; COULD NOT RUN (exit 2)."
    exit 2
fi
echo "regression-openssl-pin: PASS"
exit 0
