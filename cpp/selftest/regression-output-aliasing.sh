#!/bin/bash
#
# Regression for A05 and A04 (outside read-only audit, 2026-10-20).
#
# A05, THE ONE THAT DESTROYS DATA. C14 claims the -o path with a placeholder as
# soon as the path is known, so no run can leave a stale success behind. That
# repair moved an irreversible write EARLIER than the assessment, and
# `-o capture.bin capture.bin` replaced a 1,000,000-byte capture with a
# ~600-byte error report before a single sample was read. Measured on all three
# tools, exit 255. In January the input is a physical capture that cannot be
# recreated, so this test guards the one failure the project cannot absorb.
#
# The guard is file IDENTITY, not string equality, so this checks every alias
# form that names the same bytes: the same path, "./" prefixed, an absolute
# path, a path through "..", a HARD LINK and a SYMLINK.
#
# A04. The --version prescan did not know that -o consumes a following
# argument, so `-o --version data 1` printed the version and exited 0 with
# nothing assessed and any previous report left in place -- exit status 0 with a
# stale report, which is the fail-open C14 exists to prevent, reached through
# the option parser instead of through an error path.
#
# REGRESSION_OUTPUT_BINDIR points the checks at another build, so they can be
# shown FAILING against a build that predates the fix.

set -u

here=$(cd "$(dirname "$0")" && pwd)
bindir="${REGRESSION_OUTPUT_BINDIR:-${here}/..}"
. "${here}/buildstate-lib.sh"
bs_print "${bindir}/ea_non_iid" "${bindir}/ea_iid" "${bindir}/ea_restart"

work=$(mktemp -d "${TMPDIR:-/tmp}/ea-alias.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM
fails=0
pass() { printf '  %-52s PASS\n' "$1"; }
fail() { printf '  %-52s FAIL  %s\n' "$1" "${2:-}"; fails=$((fails + 1)); }

# A 1-bit input the tools accept, so a refusal cannot be confused with an input
# rejection. splitmix64 bit 0: no short period, and it passes the required
# tests (an LCG's low bits do not -- the audit's own instrument error).
gen="${work}/gen.c"
cat > "${gen}" <<'GENEOF'
#include <stdio.h>
int main(void){ unsigned long long x=0x90B2026ULL;
  for(long i=0;i<1000000;i++){ x+=0x9E3779B97F4A7C15ULL; unsigned long long z=x;
    z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL;
    putchar((int)((z^(z>>31))&1ULL)); } return 0; }
GENEOF
cc -O1 -o "${work}/gen" "${gen}" 2>/dev/null || { echo "regression-output-aliasing: no C compiler" >&2; exit 2; }
"${work}/gen" > "${work}/capture.bin"
baseline=$( (command -v shasum >/dev/null && shasum -a 256 "${work}/capture.bin") \
            || sha256sum "${work}/capture.bin" )
baseline=${baseline%% *}
[ -s "${work}/capture.bin" ] || { echo "regression-output-aliasing: no input generated" >&2; exit 2; }

sha_of() { local h; h=$( (command -v shasum >/dev/null && shasum -a 256 "$1") || sha256sum "$1" ); echo "${h%% *}"; }

run_tool() { # run_tool <tool> <outpath> -- always against capture.bin
    local tool=$1 out=$2
    case "${tool}" in
        ea_restart) ( cd "${work}" && "${bindir}/${tool}" -i -q -o "${out}" capture.bin 1 0.9 >/dev/null 2>&1 ) ;;
        ea_iid)     ( cd "${work}" && "${bindir}/${tool}" -i -q -o "${out}" capture.bin 1     >/dev/null 2>&1 ) ;;
        *)          ( cd "${work}" && "${bindir}/${tool}" -i -a -q -o "${out}" capture.bin 1  >/dev/null 2>&1 ) ;;
    esac
    return $?
}

# ---- A05: every alias form must be refused, with the capture untouched ----
ln    "${work}/capture.bin" "${work}/hardlink.bin" 2>/dev/null
ln -s capture.bin           "${work}/symlink.bin"  2>/dev/null
mkdir -p "${work}/sub"
for tool in ea_non_iid ea_iid ea_restart; do
    for alias in "capture.bin" "./capture.bin" "${work}/capture.bin" \
                 "sub/../capture.bin" "hardlink.bin" "symlink.bin"; do
        [ "${alias}" = "hardlink.bin" ] && [ ! -e "${work}/hardlink.bin" ] && continue
        [ "${alias}" = "symlink.bin"  ] && [ ! -e "${work}/symlink.bin"  ] && continue
        run_tool "${tool}" "${alias}"; rc=$?
        now=$(sha_of "${work}/capture.bin")
        label="${tool} -o ${alias}"
        if [ "${now}" != "${baseline}" ]; then
            fail "${label}" "THE CAPTURE WAS DESTROYED"
            "${work}/gen" > "${work}/capture.bin"      # restore for the next case
        elif [ "${rc}" -eq 0 ]; then
            fail "${label}" "accepted an output that is the input (exit 0)"
        else
            pass "${label}  refused, capture intact"
        fi
    done
done

# ---- the positive control: a distinct -o path must still assess ----
rm -f "${work}/report.json"
if run_tool ea_non_iid "report.json" && [ -s "${work}/report.json" ] \
   && grep -q '"errorLevel" : 0' "${work}/report.json"; then
    pass "control: a distinct -o path still assesses"
else
    fail "control: a distinct -o path still assesses" "the guard refuses a legitimate run"
fi
[ "$(sha_of "${work}/capture.bin")" = "${baseline}" ] \
    && pass "control: the capture is untouched by a successful run" \
    || fail "control: the capture is untouched by a successful run" "input changed"

# ---- A04: -o --version must not print a version and exit 0 ----
for tool in ea_non_iid ea_iid ea_restart; do
    case "${tool}" in
        ea_restart) out=$( ( cd "${work}" && "${bindir}/${tool}" -i -o --version absent-data 1 0.9 ) 2>&1 ); rc=$? ;;
        *)          out=$( ( cd "${work}" && "${bindir}/${tool}" -i -o --version absent-data 1 ) 2>&1 ); rc=$? ;;
    esac
    label="${tool} -o --version absent-data"
    # Assert on the VERSION BANNER, not on the word "version": the usage text
    # documents a --version option, so grepping for the word matched the usage
    # output and failed a tool that had behaved correctly. An assertion must
    # key on a signal only the thing it is testing can produce (OC-48).
    if [ "${rc}" -eq 0 ]; then
        fail "${label}" "exited 0 with nothing assessed"
    elif printf '%s' "${out}" | grep -q 'Disclaimer: NIST-developed software'; then
        fail "${label}" "printed the version banner: --version was taken as an option, not as -o's argument"
    else
        pass "${label}  refused (exit ${rc}), no version banner"
    fi
done

# and the control for THAT assertion: a real --version must still print it
if "${bindir}/ea_non_iid" --version 2>&1 | grep -q 'Disclaimer: NIST-developed software'; then
    pass "control: a real --version still prints the banner"
else
    fail "control: a real --version still prints the banner" "the option was broken, not fixed"
fi

if [ "${fails}" -eq 0 ]; then
    echo "regression-output-aliasing: PASS"
    exit 0
fi
echo "regression-output-aliasing: FAIL (${fails} case(s))"
exit 1
