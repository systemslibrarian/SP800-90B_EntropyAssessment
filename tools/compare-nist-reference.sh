#!/usr/bin/env bash
#
# OC-107: re-run NIST's own selftest over all 11 reference datasets with the
# REPAIRED comparator, and report per dataset: pass/fail, the number of values
# compared, and the largest delta.
#
# `selftest` prints only a pass/fail summary and the names of the files that
# failed. That is enough to gate on and not enough to ANSWER THE QUESTION
# "does this fork agree with NIST's published reference outputs, and by how
# much" -- which needs the per-dataset value count and worst delta that
# compareresults.pl already computes and selftest discards.
#
# This does not modify `selftest` and does not replace it. It performs the SAME
# loop -- the same fixture list, the same `ea_non_iid -vv`, the same
# compareresults.pl -- in a scratch directory, so the .res files it produces
# never land in the repository and a concurrent `selftest` cannot clobber them.
# It takes the repository as an argument so it can be pointed at a worktree.
#
# WHY THE PER-DATASET DETAIL MATTERS. Until OC-73/OC-74, compareresults.pl did
# not compare the IDENTITY lines of the two reports, so it compared a 42-sample
# 3-symbol fixture as EQUAL to a 1,000,000-sample 179-symbol run: "Maximum
# delta: 6.93e-15", 98 values compared, exit 0. Every pass of the selftest
# before that repair is therefore unverified, which is why this is re-run
# rather than read off the record.
set -u
repo=${1:?usage: nist-11-datasets.sh <path-to-fork>}
repo=$(cd "${repo}" && pwd)
st="${repo}/cpp/selftest"
[ -x "${repo}/cpp/ea_non_iid" ] || { echo "no ea_non_iid; run 'make non_iid'" >&2; exit 2; }

# EXACTLY WHAT selftest SETS, AND WHY IT MATTERS HERE.
#
# Three of the eleven reference datasets (rand1_short, rand4_short,
# rand8_short) hold 10,000 samples. This fork ENFORCES SP 800-90B Section
# 3.1.1's 1,000,000-sample minimum, so without this escape the tool exits 255
# on those three and no assessment runs. selftest sets it at its line 23 for
# that reason, and a run that uses it announces on stdout that its result is
# NOT a compliant assessment.
#
# The first version of this driver did not set it, and would have reported
# three of eleven reference datasets as DISAGREEING -- a spurious alarm of
# exactly the kind this item was told ranks above everything else. The escape
# is therefore set here, and the table below marks which rows depend on it.
export EA_ALLOW_SHORT_DATASET=1

# Work in a scratch directory so the .res files this produces never land in the
# repository, and so a concurrent `selftest` run cannot clobber them.
work=$(mktemp -d "${TMPDIR:-/tmp}/nist11.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM
ln -s "${st}/refdata" "${work}/refdata"
cp "${st}/compareresults.pl" "${work}/compareresults.pl"

printf '%-26s %-6s %-9s %-14s %s\n' DATASET RESULT COMPARED 'MAX-DELTA' 'IDENTITY'
n=0; pass=0; fail=0
while read -r bfile; do
    [ -n "${bfile}" ] || continue
    res="${bfile/bin/res}"
    [ -f "${st}/refdata/${res}" ] || { printf '%-26s %-6s %s\n' "${bfile}" "NOREF" "refdata/${res} absent"; fail=$((fail+1)); continue; }
    n=$((n+1))
    # Never pipe the tool's output: SIGPIPE would kill it and $? would be the
    # reader's status. It is redirected, exactly as selftest does it.
    ( cd "${work}" && "${repo}/cpp/ea_non_iid" -vv "${repo}/bin/${bfile}" > "${res}" 2>"${res}.err" )
    rc=$?
    if [ "${rc}" -ne 0 ]; then
        printf '%-26s %-6s %s\n' "${bfile}" "FAIL" "ea_non_iid exited ${rc}"
        fail=$((fail+1)); continue
    fi
    out=$( cd "${work}" && perl ./compareresults.pl "${res}" "refdata/${res}" 2>&1 ); crc=$?
    delta=$(printf '%s\n' "${out}" | sed -n 's/^Maximum delta: //p' | tail -1)
    cmpd=$(printf '%s\n'  "${out}" | sed -n 's/.*: \([0-9][0-9]*\) value(s) compared.*/\1/p' | tail -1)
    ident=$(printf '%s\n' "${out}" | sed -n 's/.*identity \(.*\) matched.*/\1/p' | tail -1)
    short=""
    grep -q 'EA_ALLOW_SHORT_DATASET is set' "${work}/${res}" && short=" [short-dataset escape; NOT a compliant assessment]"
    # An empty extraction reads exactly like "nothing was wrong" (SHAPE-03), so
    # a missing count or delta is reported as unreadable rather than blank.
    [ -n "${cmpd}" ]  || cmpd="UNREADABLE"
    [ -n "${delta}" ] || delta="UNREADABLE"
    [ -n "${ident}" ] || ident="NOT-MATCHED"
    if [ "${crc}" -eq 0 ]; then
        printf '%-26s %-6s %-9s %-14s %s%s\n' "${bfile}" "PASS" "${cmpd}" "${delta}" "${ident}" "${short}"
        pass=$((pass+1))
    else
        printf '%-26s %-6s %-9s %-14s %s\n' "${bfile}" "FAIL" "${cmpd}" "${delta}" "${ident}"
        fail=$((fail+1))
        printf '%s\n' "${out}" | grep -E 'Significant difference|No corresponding|No reference|identity' | sed 's/^/      /'
    fi
done < <(awk '$1 == "input" { print $2 }' "${st}/fixture-manifest.txt")

echo
echo "datasets run: ${n}   agreeing: ${pass}   disagreeing: ${fail}"
uname -sm
"${repo}/cpp/ea_non_iid" --version 2>/dev/null | head -1
