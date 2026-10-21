#!/bin/bash
#
# Wires the two static dead-guard detectors (OC-72), which until now ran
# nothing and were run by nothing.
#
# WHY A BASELINE AND NOT A GATE ON ZERO. The detectors flag a pattern, not a
# defect: the original sweep resolved 98 flags to 7 real dead guards, so
# gating on "no flags" would fail permanently and gating on nothing is what
# they did before. Instead the flag SET is pinned, the same shape as
# known-platform-deltas.txt:
#
#   * a NEW flag fails -- a guard has acquired the pattern, and it is read by
#     hand before the baseline moves;
#   * a DISAPPEARED flag fails -- a flagged line is gone, which is usually a
#     repair but is sometimes a deleted guard, and the difference matters;
#   * the count alone is NOT the check, because two offsetting changes would
#     leave it unmoved.
#
# A moved baseline is a deliberate statement. Regenerate with
# EA_DEADGUARD_REBASE=1 and say in the commit which flags changed and why.

set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
BASE="${here}/deadguard-baseline.txt"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-deadguard.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM

command -v python3 >/dev/null 2>&1 || {
    echo "regression-deadguard: python3 not on PATH; the detectors cannot run" >&2
    exit 2
}

# The detectors expect $SP/sweep/<name>/ trees. Only the fork is present here;
# the other two roots are TruePad's and are deliberately absent -- this
# repository does not read that one.
mkdir -p "${work}/sweep"
ln -s "${repo}" "${work}/sweep/fork-master"
mkdir -p "${work}/sweep/fork-repair" "${work}/sweep/truepad"

SP="${work}" python3 "${repo}/audits/2026-10-11-independent-audit/deadguard.py" > "${work}/dg.out" 2>&1 || {
    echo "regression-deadguard: deadguard.py failed" >&2; cat "${work}/dg.out" >&2; exit 2; }

# PROVENANCE IS DECLARED, NOT ASSUMED (rule 4 / OC-72). The detectors used to
# hardcode "fork @ master f069898" for whatever was placed under them.
grep '^provenance: fork @' "${work}/dg.out" | sed 's/^/  [provenance] /'

python3 - "${work}/deadguard.json" > "${work}/flags.txt" <<'PY'
import json, sys
# One stable line per flag: file, pattern class, and the detail. The LINE
# NUMBER is deliberately excluded -- it moves whenever anything above it is
# edited, and that is a real "legitimately differs" claim, justified here by
# the self-comparison in the baseline header rather than assumed (rule 8).
rows = {"%s|%s|%s" % (f["file"], f["pattern"], f["detail"]) for f in json.load(open(sys.argv[1]))}
print("\n".join(sorted(rows)))
PY

if [ "${EA_DEADGUARD_REBASE:-0}" = "1" ]; then
    cp "${work}/flags.txt" "${BASE}"
    echo "regression-deadguard: baseline REBASED to $(grep -c '' "${BASE}") flags -- say in the commit what changed and why"
    exit 0
fi

[ -s "${BASE}" ] || {
    echo "regression-deadguard: no baseline at ${BASE}; create it with EA_DEADGUARD_REBASE=1" >&2
    exit 2
}

added=$(comm -13 "${BASE}" "${work}/flags.txt")
gone=$(comm -23 "${BASE}" "${work}/flags.txt")
printf '  %-44s %s\n' "flags now" "$(grep -c '' "${work}/flags.txt")"
printf '  %-44s %s\n' "flags in the pinned baseline" "$(grep -c '' "${BASE}")"

fails=0
if [ -n "${added}" ]; then
    echo "  NEW FLAGS (a guard has acquired the pattern; read each by hand):"
    printf '%s\n' "${added}" | sed 's/^/    + /'
    fails=$((fails + 1))
fi
if [ -n "${gone}" ]; then
    echo "  FLAGS GONE (usually a repair, sometimes a deleted guard -- say which):"
    printf '%s\n' "${gone}" | sed 's/^/    - /'
    fails=$((fails + 1))
fi

if [ "${fails}" -eq 0 ]; then echo "regression-deadguard: PASS (flag set unchanged)"; exit 0; fi
echo "regression-deadguard: FAIL (the flag set moved; rebase deliberately if correct)"
exit 1
