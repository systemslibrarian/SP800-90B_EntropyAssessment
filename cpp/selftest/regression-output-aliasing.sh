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

# Does this platform's ln / ln -s actually produce an alias? Measured on
# throwaway files: write through one name, read through the other.
aliases_here() { # aliases_here <mk-cmd...> -- returns 0 if the two names are one file
    rm -f "${work}/p.a" "${work}/p.b"
    printf 'first' > "${work}/p.a"
    "$@" >/dev/null 2>&1 || return 1
    [ -e "${work}/p.b" ] || return 1
    printf 'second' > "${work}/p.a"
    [ "$(cat "${work}/p.b" 2>/dev/null)" = "second" ]
}
HARDLINK_IS_ALIAS=no; SYMLINK_IS_ALIAS=no
aliases_here ln    "${work}/p.a" "${work}/p.b" && HARDLINK_IS_ALIAS=yes
( cd "${work}" && rm -f p.b ) ; aliases_here sh -c "cd '${work}' && ln -s p.a p.b" && SYMLINK_IS_ALIAS=yes
rm -f "${work}/p.a" "${work}/p.b"
printf '  platform link semantics: hard link aliases=%s  symlink aliases=%s\n' \
    "${HARDLINK_IS_ALIAS}" "${SYMLINK_IS_ALIAS}"
mkdir -p "${work}/sub"
for tool in ea_non_iid ea_iid ea_restart; do
    for alias in "capture.bin" "./capture.bin" "${work}/capture.bin" \
                 "sub/../capture.bin" "hardlink.bin" "symlink.bin"; do
        # VERIFY THE PREMISE BEFORE ASSERTING THE CONCLUSION, and do it with
        # tools that exist. The first version used python3, which is NOT on
        # PATH in the MSYS2 shell, so on Windows every case SKIPPED for a
        # reason unrelated to aliasing and the guard went untested -- honest,
        # and useless. The spelling variants of one path are the same file BY
        # CONSTRUCTION and need no check. Only the hard link and the symlink
        # need one, because MSYS2 emulates symlinks by COPYING unless
        # winsymlinks is set, and a copy is a different file the guard should
        # correctly allow. That is established once, on throwaway files, by
        # writing through one name and reading through the other.
        case "${alias}" in
            hardlink.bin) [ "${HARDLINK_IS_ALIAS}" = yes ] || {
                printf '  %-52s SKIP  ln does not alias on this platform\n' "${tool} -o ${alias}"; continue; } ;;
            symlink.bin)  [ "${SYMLINK_IS_ALIAS}" = yes ] || {
                printf '  %-52s SKIP  ln -s does not alias on this platform (MSYS2 copies)\n' "${tool} -o ${alias}"; continue; } ;;
        esac
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
rm -f "${work}/report.json" "${work}/control.out"
( cd "${work}" && "${bindir}/ea_non_iid" -i -a -q -o report.json capture.bin 1 ) \
    > "${work}/control.out" 2>&1
if [ -s "${work}/report.json" ] && grep -q '"errorLevel" : 0' "${work}/report.json"; then
    pass "control: a distinct -o path still assesses"
elif grep -q 'could not put the report in place' "${work}/control.out"; then
    # C24: Windows rename() refuses an existing destination, and C14's
    # placeholder has already created one, so NO report can be written there.
    # That is a separately tracked defect, not this guard refusing a legitimate
    # run, and the distinction is read off the tool's own message rather than
    # guessed from the platform.
    printf '  %-52s SKIP  C24: no report can be written on this platform\n' \
        "control: a distinct -o path still assesses"
else
    fail "control: a distinct -o path still assesses" "the guard refuses a legitimate run"
fi
[ "$(sha_of "${work}/capture.bin")" = "${baseline}" ] \
    && pass "control: the capture is untouched by a successful run" \
    || fail "control: the capture is untouched by a successful run" "input changed"

# ---- F03: THE TEMPORARY IS A WRITE PATH TOO ----
#
# A05's guard checks the FINAL report path. The temporary beside it was
# `<report>.tmp.<pid>` and was opened with std::ios::trunc, which FOLLOWS A
# SYMLINK -- so an attacker who can write in the report's directory plants a
# symlink there aimed at the capture and the tool truncates its own input,
# while the guard at the front door reports nothing wrong.
#
# Measured against the pre-repair build (HEAD before this repair), all three
# tools: the 1,000,000-byte capture came back 798 bytes of report JSON, rename()
# then renamed THE SYMLINK so the -o path became a permanent alias of the
# capture, and the A05 guard fired on the SECOND write and printed "Nothing has
# been written; the input is untouched" -- a sentence both halves of which were
# false by then.
#
# The pid is not guessed. The planter below is `exec`ed into the tool, so the
# symlink is planted at the planter's OWN pid and the tool inherits it: the
# planted name is EXACTLY the name the pre-repair writer computes. A test that
# covered a pid RANGE instead could miss, and a miss would be indistinguishable
# from the repair working (and did miss, twice: the 2500 `ln` processes doing
# the planting consumed the very pid range being planted into).
if [ "${SYMLINK_IS_ALIAS}" = yes ]; then
    cat > "${work}/plantexec.c" <<'PLANTEOF'
/* plantexec <report-path> <capture-path> <tool> [args...]
   Plant a symlink at <report-path>.tmp.<my pid> aimed at <capture-path>, then
   become the tool, which inherits that pid. */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc, char **argv) {
    char link[8192];
    if (argc < 4) return 3;
    snprintf(link, sizeof link, "%s.tmp.%ld", argv[1], (long) getpid());
    if (symlink(argv[2], link) != 0) { perror("plantexec: symlink"); return 3; }
    fprintf(stderr, "plantexec: planted %s\n", link);
    execv(argv[3], &argv[3]);
    perror("plantexec: execv");
    return 4;
}
PLANTEOF
    if cc -O1 -o "${work}/plantexec" "${work}/plantexec.c" 2>/dev/null; then
        for tool in ea_non_iid ea_iid ea_restart; do
            rm -f "${work}/f03.json" "${work}"/f03.json.tmp.*
            "${work}/gen" > "${work}/capture.bin"
            case "${tool}" in
                ea_restart) set -- -i -q -o f03.json capture.bin 1 0.9 ;;
                ea_iid)     set -- -i -q -o f03.json capture.bin 1 ;;
                *)          set -- -i -a -q -o f03.json capture.bin 1 ;;
            esac
            # execv(argv[3], &argv[3]): the tool path is given ONCE and
            # becomes the tool's own argv[0].
            ( cd "${work}" && "${work}/plantexec" f03.json capture.bin \
                             "${bindir}/${tool}" "$@" ) >/dev/null 2>&1
            # the planted link's name is <report>.tmp.<pid>; find it by shape
            link=$(ls "${work}"/f03.json.tmp.* 2>/dev/null | head -1)
            now=$(sha_of "${work}/capture.bin")
            label="${tool} symlink planted at the temp path"
            if [ "${now}" != "${baseline}" ]; then
                fail "${label}" "THE CAPTURE WAS DESTROYED THROUGH THE TEMPORARY"
            elif [ -z "${link}" ]; then
                # The planted link is gone. Either the tool renamed it onto the
                # report path (the pre-repair failure) or it was never planted
                # (the test did not run). Both are refusals to pass: a test that
                # cannot show its mechanism fired supports no claim (rule 7).
                fail "${label}" "the planted symlink is gone; this test proved nothing"
            elif [ -L "${work}/f03.json" ]; then
                fail "${label}" "the -o path is now a symlink to the capture"
            else
                pass "${label}  refused, capture intact, link untouched"
            fi
        done
        rm -f "${work}/f03.json" "${work}"/f03.json.tmp.*
        "${work}/gen" > "${work}/capture.bin"
    else
        printf '  %-52s SKIP  no symlink() on this platform\n' "F03 temp-path symlink"
    fi
else
    printf '  %-52s SKIP  ln -s does not alias here (MSYS2 copies)\n' "F03 temp-path symlink"
fi

# ---- A04 / F04: a --version that is really -o's ARGUMENT, in every spelling ----
#
# F04 (OC-80): A04's repair tested the LAST character of the cluster and then
# required the cluster to be exactly two characters, so it fired for "-o" and
# for nothing else. "-vo --version" and "-qo --version" are the same request
# written as a cluster and the bypass stayed fully open. Measured on all three
# tools against the pre-repair build: exit 0, version banner printed, nothing
# assessed, no report written -- A04 verbatim through a different spelling.
#
# THE SPELLINGS ARE A LOOP, NOT A CASE. Three spellings here; the repair is a
# left-to-right cluster walk that is correct for every length, so a fourth
# spelling needs no new code, only a new row.
#
# "-Z --version" is in the list for a reason: it was open on the pre-repair
# build too, found by this repair's own control set rather than by the audit. An
# unrecognised option now makes the prescan return false so getopt reports it.
#
# It is "-Z" and not "-Z -o", which was the first draft and tested nothing: the
# "-o" that followed consumed "--version" as its argument on the pre-repair
# build as well, so the row passed on both arms and looked like a control that
# had found nothing rather than a case that was never exercised.
for tool in ea_non_iid ea_iid ea_restart; do
  for spell in "-o" "-vo" "-qo" "-Z"; do
    # shellcheck disable=SC2086
    case "${tool}" in
        ea_restart) out=$( ( cd "${work}" && "${bindir}/${tool}" -i ${spell} --version absent-data 1 0.9 ) 2>&1 ); rc=$? ;;
        *)          out=$( ( cd "${work}" && "${bindir}/${tool}" -i ${spell} --version absent-data 1 ) 2>&1 ); rc=$? ;;
    esac
    label="${tool} ${spell} --version absent-data"
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
done

# ---- and the controls for the F04 repair: it must not break the opposite case
#
# Every row below behaves IDENTICALLY on the pre-repair build, which is what
# makes them controls: they establish that the cluster walk narrowed nothing.
# The one that matters most is the attached-argument form, because the condition
# the repair removed ("the cluster is exactly two characters") was there to stop
# the old last-character test misfiring on "-oNAME".
#
# THE SIGNAL IS errorLevel 0, NOT THE PRESENCE OF A FIELD. A first draft keyed
# "assessed" on assessedSampleCount, which an ERROR report also carries -- a run
# that printed "*** No assessment was performed. ***" and exited 255 was scored
# as having assessed 1000 samples. An assertion must key on a signal only the
# thing it is testing can produce.
ctl_assess() { # ctl_assess <label> <args...>
    local label=$1; shift
    rm -f "${work}/f04ctl.json"
    local out rc
    out=$( ( cd "${work}" && "${bindir}/ea_non_iid" "$@" ) 2>&1 ); rc=$?
    if printf '%s' "${out}" | grep -q 'Disclaimer: NIST-developed software'; then
        fail "control: ${label}" "printed the version banner"
    elif [ "${rc}" -ne 0 ]; then
        if printf '%s' "${out}" | grep -q 'could not put the report in place'; then
            printf '  %-52s SKIP  C24: no report can be written on this platform\n' "control: ${label}"
        else
            fail "control: ${label}" "exit ${rc}"
        fi
    elif [ -s "${work}/f04ctl.json" ] && grep -q '"errorLevel" : 0' "${work}/f04ctl.json"; then
        pass "control: ${label}  assessed, no banner"
    else
        fail "control: ${label}" "exit 0 but no completed report"
    fi
}
ctl_assess "-o NAME still assesses"        -i -a -q -o f04ctl.json capture.bin 1
ctl_assess "-oNAME (attached) still assesses" -i -a -q -of04ctl.json capture.bin 1
ctl_assess "-vo NAME (cluster) still assesses" -i -a -q -vo f04ctl.json capture.bin 1
ctl_assess "-qo NAME (cluster) still assesses" -i -a -q -qo f04ctl.json capture.bin 1
rm -f "${work}/f04ctl.json"

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
