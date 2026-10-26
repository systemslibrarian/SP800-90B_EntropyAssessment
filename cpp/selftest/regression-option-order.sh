#!/bin/bash
#
# Regression for OC-104: an option placed AFTER the file operand is refused.
#
# WHY THIS IS A BEHAVIOUR CHANGE AND NOT A REPAIR. Measured 2026-10-25 on both
# supported platforms:
#
#   glibc / x86-64 (CI step 5c)   getopt PERMUTES the command line.
#                                 `ea_non_iid -i -a f 1 -q -o r` parses -q and
#                                 -o, assesses f, and writes r.
#   BSD / macOS arm64             getopt STOPS at the first operand. The same
#                                 line leaves `-q -o r` as operands, so argc
#                                 after optind is 4 and the run dies on the
#                                 usage path with nothing assessed.
#
# One command line, two supported platforms, two different operations. Every
# guard reading the identity prescan is unarmed for the permuting case, because
# the prescan stops where BSD getopt stops -- so a `-o` after the operand never
# reaches outputTargetIsSafe. OC-102 measured that writeJsonReport's choke
# point still caught it, so no capture was at risk; but a guard that cannot be
# shown to be armed is recorded as unarmed, not as passing, and this one is
# unarmed by construction on one of the two platforms.
#
# RULE 12 DECLARATION. This change touches ground two earlier repairs touched,
# and both pairs are tested below by name:
#
#   * A04/F04 -- versionOptionRequested's cluster walk. The refusal and the
#     --version gate now share ONE walk of argv (scanArgs), because three
#     copies of that walk is precisely how F04 happened: the arithmetic was
#     repaired in the prescan and left wrong in the version gate, and the
#     bypass stayed open through a different spelling. PAIR TEST: the four F04
#     cluster forms must behave exactly as F04 left them.
#   * A05/F03 -- the identity prescan and the writeJsonReport choke point.
#     The refusal fires EARLIER than both. PAIR TEST: the permuted aliasing
#     form must now be refused by option order, with the capture byte
#     identical, and the ordinary aliasing form must still be refused by
#     identity.
#
# REGRESSION_OPTION_ORDER_BINDIR points the checks at another build, so they
# can be shown FAILING against a build without the refusal. Both runs are
# recorded in OC-104.

set -u

here=$(cd "$(dirname "$0")" && pwd)
bindir="${REGRESSION_OPTION_ORDER_BINDIR:-${here}/..}"
. "${here}/buildstate-lib.sh"
bs_print "${bindir}/ea_non_iid" "${bindir}/ea_iid" "${bindir}/ea_restart"

for t in ea_non_iid ea_iid ea_restart; do
    [ -x "${bindir}/${t}" ] || { echo "regression-option-order: ${bindir}/${t} missing (run 'make non_iid iid restart')" >&2; exit 2; }
done

work=$(mktemp -d "${TMPDIR:-/tmp}/ea-optorder.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM
fails=0
pass() { printf '  %-58s PASS\n' "$1"; }
fail() { printf '  %-58s FAIL  %s\n' "$1" "${2:-}"; fails=$((fails + 1)); }

# A 1-bit input the tools ACCEPT, so a refusal can never be confused with an
# input rejection, and so the control arm is known to assess. splitmix64 bit 0.
gen="${work}/gen.c"
cat > "${gen}" <<'GENEOF'
#include <stdio.h>
int main(void){ unsigned long long x=0x90B2026ULL;
  for(long i=0;i<1000000;i++){ x+=0x9E3779B97F4A7C15ULL; unsigned long long z=x;
    z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL;
    putchar((int)((z^(z>>31))&1ULL)); } return 0; }
GENEOF
cc -O1 -o "${work}/gen" "${gen}" 2>/dev/null || { echo "regression-option-order: no C compiler" >&2; exit 2; }
"${work}/gen" > "${work}/capture.bin"
[ -s "${work}/capture.bin" ] || { echo "regression-option-order: no input generated" >&2; exit 2; }
sha_of() { local h; h=$( (command -v shasum >/dev/null && shasum -a 256 "$1") || sha256sum "$1" ); echo "${h%% *}"; }
baseline=$(sha_of "${work}/capture.bin")

# The tool's output is NEVER piped: SIGPIPE would kill it and $? would be the
# reader's status, which is how four earlier probes answered the wrong question.
run() { # run <tool> <args...>  -> sets rc, OUT, ERR
    local tool=$1; shift
    ( cd "${work}" && "${bindir}/${tool}" "$@" >"${work}/out.txt" 2>"${work}/err.txt" )
    rc=$?
    return 0
}
refused()  { grep -q 'appears after the file operand' "${work}/err.txt"; }
assessed() { grep -qE '^(H_original|min\(H_r, H_c, H_I\)): [0-9]' "${work}/out.txt"; }
bannered() { grep -qE '^(non_iid|iid|restart) [0-9]+\.[0-9]+\.[0-9]+' "${work}/out.txt"; }

# Per-tool trailing operands, so each tool gets a well-formed command line.
tail_for() { case "$1" in ea_restart) echo "1 0.9" ;; *) echo "1" ;; esac; }
# NO -q IN THE LEAD OPTIONS. Quiet mode suppresses the result line, which
# would make assessed() read "no" for a perfectly successful run -- so every
# "nothing was assessed" assertion below would have passed whatever the tool
# did, and every control arm would have failed. Observed on this script's first
# run: 6 failures, all of them this. The signal has to be live in BOTH
# polarities or it is not a signal.
lead_for() { case "$1" in ea_non_iid) echo "-i -a" ;; *) echo "-i" ;; esac; }

echo "== the refusal fires, and names the offending argument =="
for tool in ea_non_iid ea_iid ea_restart; do
    read -r -a tl <<<"$(tail_for "${tool}")"
    read -r -a ld <<<"$(lead_for "${tool}")"
    # -q after the operand: the exact shape step 5c measured on glibc.
    run "${tool}" "${ld[@]}" capture.bin "${tl[@]}" -q
    if [ "${rc}" -ne 0 ] && refused && ! assessed; then
        if grep -q "'-q'" "${work}/err.txt"; then
            pass "${tool}: -q after the operand refused, named"
        else
            fail "${tool}: -q after the operand refused but not named" "stderr lacks '-q'"
        fi
    else
        fail "${tool}: -q after the operand" "rc=${rc} refused=$(refused && echo y || echo n) assessed=$(assessed && echo y || echo n)"
    fi
    # -o after the operand: the form that left the early aliasing guard unarmed.
    run "${tool}" "${ld[@]}" capture.bin "${tl[@]}" -o late.json
    if [ "${rc}" -ne 0 ] && refused && ! assessed && [ ! -e "${work}/late.json" ]; then
        pass "${tool}: -o after the operand refused, nothing written"
    else
        fail "${tool}: -o after the operand" "rc=${rc} report=$([ -e "${work}/late.json" ] && echo present || echo absent)"
    fi
    # A late --version: measured 2026-10-25 as exit 255 on BOTH platforms via
    # the usage path. It is still refused, but now by option order and with a
    # message that says which argument and what the correct form is.
    run "${tool}" "${ld[@]}" capture.bin "${tl[@]}" --version
    if [ "${rc}" -ne 0 ] && refused && ! assessed && ! bannered; then
        pass "${tool}: late --version refused, no banner, nothing assessed"
    else
        fail "${tool}: late --version" "rc=${rc} banner=$(bannered && echo y || echo n)"
    fi
done

echo
echo "== the well-formed forms are untouched =="
for tool in ea_non_iid ea_iid ea_restart; do
    read -r -a tl <<<"$(tail_for "${tool}")"
    read -r -a ld <<<"$(lead_for "${tool}")"
    rm -f "${work}/ctl.json"
    run "${tool}" "${ld[@]}" -o ctl.json capture.bin "${tl[@]}"
    if [ "${rc}" -eq 0 ] && assessed && grep -q '"errorLevel" : 0' "${work}/ctl.json" 2>/dev/null; then
        pass "${tool}: options before the operand still assess"
    else
        fail "${tool}: options before the operand" "rc=${rc} assessed=$(assessed && echo y || echo n)"
    fi
    # --version alone, the documented use, must still work.
    run "${tool}" --version
    if [ "${rc}" -eq 0 ] && bannered && ! refused; then
        pass "${tool}: --version alone still prints the banner"
    else
        fail "${tool}: --version alone" "rc=${rc} banner=$(bannered && echo y || echo n)"
    fi
    # "--" is the operator saying what they meant: everything after it is an
    # operand on every platform, so the refusal must NOT fire.
    rm -f "${work}/dd.json"
    run "${tool}" "${ld[@]}" -o dd.json -- capture.bin "${tl[@]}"
    if [ "${rc}" -eq 0 ] && assessed && ! refused; then
        pass "${tool}: -- separator is not refused"
    else
        fail "${tool}: -- separator" "rc=${rc} refused=$(refused && echo y || echo n)"
    fi
done

echo
echo "== PAIR TEST, A04/F04: the shared walk did not change the version gate =="
# F04's four cluster forms. The repaired behaviour is that --version used as
# -o's ARGUMENT is not a version request: the banner must NOT appear, and the
# run must proceed to assess (the argument is a filename, odd but legal).
# These all put their options BEFORE the operand, so the new refusal must stay
# silent on every one of them -- that is the pair interaction.
for form in "-o" "-vo" "-qo"; do
    rm -f "${work}/--version"
    run ea_non_iid -i -a ${form} --version capture.bin 1
    if ! refused && ! bannered; then
        pass "A04 pair: '${form} --version' no banner, not mis-refused"
    else
        fail "A04 pair: '${form} --version'" "refused=$(refused && echo y || echo n) banner=$(bannered && echo y || echo n)"
    fi
done
# -Z is an option the optstring does not list: whichever comes first, a
# --version or an unrecognised option, decides -- and an unrecognised one means
# the run must fail rather than print a banner.
run ea_non_iid -Z --version capture.bin 1
if [ "${rc}" -ne 0 ] && ! bannered; then
    pass "A04 pair: '-Z --version' fails, no banner"
else
    fail "A04 pair: '-Z --version'" "rc=${rc} banner=$(bannered && echo y || echo n)"
fi

echo
echo "== PAIR TEST, A05/F03: the refusal fires before the identity guard =="
# The permuted aliasing form. Before this change the early guard was unarmed
# here and the choke point caught it (OC-102). Now option order refuses it
# first -- and the capture must be byte identical either way.
cp "${work}/capture.bin" "${work}/perm.bin"
permbase=$(sha_of "${work}/perm.bin")
run ea_non_iid -i -a perm.bin 1 -o perm.bin
if [ "${rc}" -ne 0 ] && refused && [ "$(sha_of "${work}/perm.bin")" = "${permbase}" ]; then
    pass "A05 pair: permuted '-o <input>' refused by option order"
else
    fail "A05 pair: permuted '-o <input>'" "rc=${rc} refused=$(refused && echo y || echo n) sha_changed=$([ "$(sha_of "${work}/perm.bin")" = "${permbase}" ] && echo no || echo YES)"
fi
# And the ORDINARY aliasing form, options first, must still be refused by
# identity rather than by option order -- the earlier repair still doing its
# own job is the other half of the pair.
run ea_non_iid -i -a -o perm.bin perm.bin 1
if [ "${rc}" -ne 0 ] && ! refused && [ "$(sha_of "${work}/perm.bin")" = "${permbase}" ]; then
    pass "A05 pair: ordinary '-o <input>' still refused by identity"
else
    fail "A05 pair: ordinary '-o <input>'" "rc=${rc} refused_by_order=$(refused && echo y || echo n)"
fi

echo
[ "$(sha_of "${work}/capture.bin")" = "${baseline}" ] \
    && pass "the capture is byte identical after every case" \
    || fail "the capture is byte identical after every case" "SHA-256 moved"

echo
if [ "${fails}" -eq 0 ]; then
    echo "regression-option-order: PASS"
    exit 0
fi
echo "regression-option-order: FAIL (${fails})"
exit 1
