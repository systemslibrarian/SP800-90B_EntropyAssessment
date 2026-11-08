#!/bin/bash
#
# Regression for PROV-01 (aggressive audit, 2026-11-07): an option error parsed
# BEFORE -o left the previous run's complete report in place at the -o path.
#
# C14 claims the -o target with a fail-closed placeholder so that no failed run
# can leave a stale success behind -- and it made the claim inside getopt's
# `case 'o'`, which bound it to getopt's traversal order. Any usage-path exit
# reached while parsing an EARLIER option -- an unknown letter (-Z), a malformed
# -l or -s value -- exited 255 without claiming, and a complete errorLevel-0
# report from a previous run survived byte-identical at the path. Measured
# 2026-11-07 on all three tools (docs/audits/2026-11-07-aggressive-audit/repro/
# PROV-01). NOTICE's "It is never a stale success" was false for that ordering,
# and regression-output.sh could not see it: its C14 arm tests `-o` FIRST and
# nothing else.
#
# The repair claims the target from the argv prescan (scanArgs), which knows
# the -o path before getopt runs, immediately AFTER the A05 identity refusal.
#
# RULE 12 DECLARATION. The earlier claim lands on ground four repairs hold, and
# each pair is exercised below by the case it was built for, not by the suite:
#
#   * C14      the shapes its own regression tests -- `-o <stale>` with no
#              operand, and `-o <stale> -Z` -- must still be replaced. Those
#              are the CONTROL arms here: they held before this fix and must
#              hold after it.
#   * A05      `-o cap cap` must still be refused with NOTHING written, and so
#              must `-Z -o cap cap` -- the new ordering combined with the
#              alias -- and a symlink to the capture. The capture is compared
#              by digest after each.
#   * A04/F04  the prescan the claim now reads is the --version/cluster walk:
#              `-Z -qo p` (a cluster) must claim p, and `-o --version` must
#              still not print a banner.
#   * C08      the prescan's placeholder, getopt's, and the final report all go
#              through the atomic writer: no `.tmp.` debris survives, and a
#              run that reaches the writer replaces the placeholder with its
#              own report on every tool.
#
# RULE 7. The baseline -- a complete errorLevel-0 ea_non_iid report on the
# fixture -- is asserted accepted before any probe copies it; a baseline that
# cannot be produced is a HARNESS FAULT (exit 2), not a pass or a fail. The
# stale artefact planted for ea_iid and ea_restart is that same ea_non_iid
# report: what is tested is that the file is REPLACED, not that those tools
# can produce it.
#
# TO SEE IT FAIL (guide step 5): point REGRESSION_STALE_REPORT_BINDIR at a
# directory holding pre-fix ea_non_iid, ea_iid and ea_restart. Expected there:
# every "option error BEFORE -o" probe reports STALE and the script exits 1,
# while every control arm still passes.
#
# EA_ALLOW_SHORT_DATASET=1 on the 10,000-sample fixture bin/rand8_short.bin:
# the baseline is a NON-COMPLIANT short-dataset run (it exists only to be the
# stale artefact); the probes exit at option parsing and never read the data.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
bindir="${REGRESSION_STALE_REPORT_BINDIR:-${here}/..}"
# Build state as a printed precondition (instrument rule 4): the BINDIR
# override exists so this can be pointed at another build, which is exactly
# when a result must say which binary it measured.
. "${here}/buildstate-lib.sh"
# Labelled reads (instrument rule 5): every JSON field is read by key, and a
# missing key or a malformed file is a failure, never a default.
. "${here}/labelread-lib.sh"
bs_print "${bindir}/ea_non_iid" "${bindir}/ea_iid" "${bindir}/ea_restart"

for t in ea_non_iid ea_iid ea_restart; do
    [ -x "${bindir}/${t}" ] || { echo "regression-stale-report: ${bindir}/${t} missing (run 'make non_iid iid restart')" >&2; exit 2; }
done
command -v python3 >/dev/null 2>&1 || { echo "regression-stale-report: python3 not on PATH" >&2; exit 2; }
fixture="${repo}/bin/rand8_short.bin"
if [ ! -s "${fixture}" ]; then
    echo "regression-stale-report: HARNESS FAULT -- fixture ${fixture} is absent or empty; nothing can be assessed" >&2
    exit 2
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/ea-stale.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM

fails=0
# OC-126: every verdict is counted and the total is declared, so a loop that
# silently ran nothing cannot read as a pass.
cases=0
DECLARED_CASES=29
pass() { cases=$((cases + 1)); printf '  %-70s PASS\n' "$1"; }
fail() { cases=$((cases + 1)); printf '  %-70s FAIL  %s\n' "$1" "${2:-}"; fails=$((fails + 1)); }

sha_of() { local h; h=$( (command -v shasum >/dev/null && shasum -a 256 "$1") || sha256sum "$1" ); echo "${h%% *}"; }

# jfield <file> <key>: the field's JSON text, read by key. A file that is not
# JSON, or lacks the key, is an error with the reason named -- never an empty
# string that a comparison could mistake for a value.
jfield() {
    python3 - "$1" "$2" <<'PY' || return 1
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    sys.stderr.write("NOT JSON (%s): %s\n" % (sys.argv[1], e)); sys.exit(1)
if sys.argv[2] not in d:
    sys.stderr.write("KEY ABSENT (%s): %s\n" % (sys.argv[1], sys.argv[2])); sys.exit(1)
print(json.dumps(d[sys.argv[2]]))
PY
}
# jhas <file> <key>: 0 when the key is present, 1 when absent, 2 when the file
# is not JSON at all -- three outcomes, because "absent" and "unreadable" are
# different facts (instrument rule 2).
jhas() {
    python3 - "$1" "$2" <<'PY' || return $?
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    sys.stderr.write("NOT JSON (%s): %s\n" % (sys.argv[1], e)); sys.exit(2)
sys.exit(0 if sys.argv[2] in d else 1)
PY
}

# placeholder <file> <type>: the fail-closed placeholder claimReportTarget
# writes -- errorLevel -1, reportComplete false, the claiming tool's type, and
# the message telling a consumer to refuse the file. Reading the type proves
# WHICH tool wrote it, so a leftover from another arm cannot pass.
placeholder() {
    local f=$1 want=$2 el rc ty msg
    el=$(jfield "${f}" errorLevel | lr_one "errorLevel in $(basename "${f}")") || return 1
    rc=$(jfield "${f}" reportComplete | lr_one "reportComplete in $(basename "${f}")") || return 1
    ty=$(jfield "${f}" type | lr_one "type in $(basename "${f}")") || return 1
    msg=$(jfield "${f}" errorMessage | lr_one "errorMessage in $(basename "${f}")") || return 1
    [ "${el}" = "-1" ] || return 1
    [ "${rc}" = "false" ] || return 1
    [ "${ty}" = "\"${want}\"" ] || return 1
    case "${msg}" in *"Refuse this file"*) return 0 ;; esac
    return 1
}

# toolreport <file>: a report the TOOL wrote through the writer -- JSON with an
# errorLevel and WITHOUT the placeholder's reportComplete marker.
toolreport() {
    jhas "$1" errorLevel || return 1
    if jhas "$1" reportComplete; then return 1; fi
    return 0
}

# The tool is never piped (rule 17): stdout and stderr go to files and the
# exit status read is the tool's own. Runs from ${work} so the relative paths
# the A05 arms use (capture.bin, alias.bin) and the file named --version land
# there and nowhere else.
rc=0
run() { # run <name> <tool> <args...>
    local name=$1 tool=$2; shift 2
    ( cd "${work}" && EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" \
        "${bindir}/${tool}" "$@" > "${work}/${name}.out" 2> "${work}/${name}.err" )
    rc=$?
    return 0
}

# Per-tool trailing operands, so each tool gets a well-formed command line
# once -o is parsed: the probes must fail on the OPTION, not on the operands.
tail_for() { case "$1" in ea_restart) echo "8 3/symbol" ;; *) echo "8" ;; esac; }
# The placeholder type each tool's claimReportTarget writes.
type_for() { case "$1" in ea_non_iid) echo "non-IID" ;; ea_iid) echo "IID" ;; ea_restart) echo "restart" ;; esac; }
# The option whose VALUE is malformed, per tool: -l for the two assessment
# tools, -s (simulation count) for ea_restart, which has no -l.
badval_for() { case "$1" in ea_restart) echo "-s 5x" ;; *) echo "-l 5x,10" ;; esac; }

echo "== rule 7: the baseline is a complete errorLevel-0 report =="
good="${work}/good.json"
run baseline ea_non_iid -q -o "${good}" "${fixture}" 8
el=$(jfield "${good}" errorLevel | lr_one "baseline errorLevel") || el="(unreadable)"
ncases=$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1])).get("testCases") or []))' "${good}" 2>/dev/null || echo 0)
if [ "${rc}" -eq 0 ] && [ "${el}" = "0" ] && [ "${ncases}" -gt 0 ]; then
    pass "baseline: ea_non_iid -q -o wrote a complete errorLevel-0 report (${ncases} test cases, rc 0)"
else
    echo "regression-stale-report: HARNESS FAULT -- the baseline run did not produce a complete" >&2
    echo "    errorLevel-0 report (rc ${rc}, errorLevel ${el}, test cases ${ncases}). No stale" >&2
    echo "    artefact exists, so nothing below could be attributed to the claim. Refusing." >&2
    sed 's/^/    stderr: /' "${work}/baseline.err" >&2
    exit 2
fi
GOOD=$(sha_of "${good}")

# probe <name> <description> <tool> <args...>: ${work}/<name>.json is
# pre-loaded with the baseline report and named by the args as -o. The tool
# must exit non-zero, the file must CHANGE, and what replaces it must be the
# placeholder written by THIS tool.
probe() {
    local name=$1 desc=$2 tool=$3; shift 3
    local p="${work}/${name}.json" after
    cp "${good}" "${p}"
    run "${name}" "${tool}" "$@"
    after=$(sha_of "${p}")
    if [ "${rc}" -eq 0 ]; then
        fail "${desc}" "exited 0 on an option error"
    elif [ "${after}" = "${GOOD}" ]; then
        fail "${desc}" "STALE -- the previous complete report survived byte-identical (rc ${rc})"
    elif placeholder "${p}" "$(type_for "${tool}")"; then
        pass "${desc}: replaced by the fail-closed placeholder (rc ${rc})"
    else
        fail "${desc}" "replaced, but not by this tool's placeholder (rc ${rc})"
    fi
}

echo
echo "== an option error BEFORE -o must still claim the target (the defect) =="
for tool in ea_non_iid ea_iid ea_restart; do
    read -r -a tl <<<"$(tail_for "${tool}")"
    read -r -a bv <<<"$(badval_for "${tool}")"
    probe "pre_Z_${tool}"   "${tool} -Z -o p"                ${tool} -Z -o "${work}/pre_Z_${tool}.json" "${fixture}" "${tl[@]}"
    probe "pre_val_${tool}" "${tool} ${bv[*]} -o p"          ${tool} "${bv[@]}" -o "${work}/pre_val_${tool}.json" "${fixture}" "${tl[@]}"
    # A04/F04 pair: the -o is inside a CLUSTER, so the claim depends on the
    # shared walk's cluster arithmetic, the thing F04 got wrong.
    probe "pre_qo_${tool}"  "${tool} -Z -qo p (cluster, A04 pair)" ${tool} -Z -qo "${work}/pre_qo_${tool}.json" "${fixture}" "${tl[@]}"
done

echo
echo "== controls: the orderings the C14 regression already covers still hold =="
for tool in ea_non_iid ea_iid ea_restart; do
    read -r -a tl <<<"$(tail_for "${tool}")"
    probe "ctl_Z_${tool}"    "${tool} -o p -Z (C14 pair: error AFTER -o)"    ${tool} -o "${work}/ctl_Z_${tool}.json" -Z "${fixture}" "${tl[@]}"
    probe "ctl_noop_${tool}" "${tool} -o p (C14 pair: no operand)"          ${tool} -o "${work}/ctl_noop_${tool}.json"
done

echo
echo "== PAIR TEST, A05: the earlier claim still cannot reach the input =="
cp "${fixture}" "${work}/capture.bin"
CAP=$(sha_of "${work}/capture.bin")
ln -s capture.bin "${work}/alias.bin"
# alias_check <name> <description> <tool> <args...>: the identity refusal
# fired, the capture is byte-identical, and the run did not exit 0.
alias_check() {
    local name=$1 desc=$2 tool=$3; shift 3
    local refused=n same=n
    run "${name}" "${tool}" "$@"
    if grep -q 'same file as the' "${work}/${name}.err"; then refused=y; fi
    if [ "$(sha_of "${work}/capture.bin")" = "${CAP}" ]; then same=y; fi
    if [ "${rc}" -ne 0 ] && [ "${refused}" = y ] && [ "${same}" = y ]; then
        pass "${desc}: refused by identity, capture byte-identical (rc ${rc})"
    else
        fail "${desc}" "rc=${rc} refused=${refused} capture_identical=${same}"
    fi
}
for tool in ea_non_iid ea_iid ea_restart; do
    read -r -a tl <<<"$(tail_for "${tool}")"
    # The new ordering with the alias: the prescan must refuse BEFORE it claims.
    alias_check "a05_new_${tool}" "${tool} -Z -o capture.bin capture.bin" ${tool} -Z -o capture.bin capture.bin "${tl[@]}"
    # The ordinary A05 form, so the earlier repair is shown still doing its job.
    alias_check "a05_old_${tool}" "${tool} -o capture.bin capture.bin"    ${tool} -o capture.bin capture.bin "${tl[@]}"
done
alias_check a05_link "ea_non_iid -Z -o alias.bin (symlink to the capture)" ea_non_iid -Z -o alias.bin capture.bin 8
if [ -L "${work}/alias.bin" ]; then
    pass "the symlink alias is still a symlink (nothing was renamed over it)"
else
    fail "the symlink alias is still a symlink" "alias.bin is no longer a symlink"
fi

echo
echo "== PAIR TEST, A04/F04: --version as -o's VALUE is a filename, not a banner =="
rm -f "${work}/--version"
run a04 ea_non_iid -q -o --version "${fixture}" 8
banner=n
if grep -q 'Disclaimer: NIST-developed software' "${work}/a04.out"; then banner=y; fi
if [ "${rc}" -eq 0 ] && [ "${banner}" = n ] && [ -s "${work}/--version" ] && toolreport "${work}/--version"; then
    pass "ea_non_iid -o --version: no banner, a report named --version was written (rc 0)"
else
    fail "ea_non_iid -o --version" "rc=${rc} banner=${banner} report=$([ -s "${work}/--version" ] && echo present || echo absent)"
fi

echo
echo "== PAIR TEST, C08: a run that reaches the writer replaces the placeholder =="
for tool in ea_non_iid ea_iid ea_restart; do
    read -r -a tl <<<"$(tail_for "${tool}")"
    p="${work}/c08_${tool}.json"
    cp "${good}" "${p}"
    run "c08_${tool}" "${tool}" -q -o "${p}" "${fixture}" "${tl[@]}"
    # ea_non_iid completes on this fixture; ea_iid completes with a non-IID
    # verdict; ea_restart refuses 10,000 samples and writes its own error
    # report. Each of those goes through the writer AFTER two placeholder
    # claims, and each must end with the tool's report at -o, not the
    # placeholder.
    if toolreport "${p}"; then
        pass "${tool} -q -o p: -o holds the tool's own report, not the placeholder (rc ${rc})"
    else
        fail "${tool} -q -o p" "-o does not hold a report of the tool's own (rc ${rc})"
    fi
done
debris=$(find "${work}" -name '*.tmp.*' | grep -c .)
if [ "${debris}" -eq 0 ]; then
    pass "no temporary-file debris beside any report after every arm"
else
    fail "no temporary-file debris beside any report" "${debris} .tmp. file(s) left behind"
fi

echo
if [ "${cases}" -ne "${DECLARED_CASES}" ]; then
    printf '  %-70s FAIL  %s\n' "declared case count" "ran ${cases}, declared ${DECLARED_CASES}"
    fails=$((fails + 1))
fi
if [ "${fails}" -eq 0 ]; then
    printf 'regression-stale-report: PASS (%s checks)\n' "${cases}"
    exit 0
fi
printf 'regression-stale-report: FAIL (%s of %s checks)\n' "${fails}" "${cases}"
exit 1
