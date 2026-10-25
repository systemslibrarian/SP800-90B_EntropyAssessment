#!/bin/sh
#
# Print the fork-divergence figures FORK-DIVERGENCE-AND-TRUST.md quotes, so
# that document's counts can be re-derived instead of trusted.
#
# WHY A SCRIPT AND NOT A PARAGRAPH. The document's previous figures described a
# branch (`repair/2026-10-09-verified-defects` at 9556649) that was merged and
# deleted, said "66 commits ahead", and gave a four-row category table -- none
# of it labelled with when it had been measured, and all of it false by the
# time anyone read it. A count written in prose drifts from the thing that
# computes it. regression-docs.sh re-runs this and fails if the document's
# stated figures disagree.
#
# The upstream base is the common ancestor and is FIXED: this fork is zero
# commits behind, so base..HEAD is the whole divergence.
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
cd "${root}" || exit 2
BASE=${EA_UPSTREAM_BASE:-87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289}

git rev-parse --verify --quiet "${BASE}^{commit}" >/dev/null || {
    echo "measure-divergence: upstream base ${BASE} is not in this repository." >&2
    echo "                    Fetch it, or set EA_UPSTREAM_BASE. No figure is printed," >&2
    echo "                    because a divergence measured against a missing base is" >&2
    echo "                    not a measurement." >&2
    exit 2
}

head_sha=$(git rev-parse --short=7 HEAD)
head_date=$(git log -1 --format=%ad --date=short HEAD)
behind=$(git rev-list --count "HEAD..${BASE}")
ahead=$(git rev-list --count "${BASE}..HEAD")

printf 'measured-at-commit: %s\n' "${head_sha}"
printf 'measured-at-date:   %s\n' "${head_date}"
printf 'upstream-base:      %s\n' "$(git rev-parse --short=7 "${BASE}")"
printf 'commits-ahead:      %s\n' "${ahead}"
printf 'commits-behind:     %s\n' "${behind}"

git diff --numstat "${BASE}..HEAD" | python3 -c '
import sys
# The categories are by PATH, and the boundaries are stated rather than
# inferred: production code is what ships, the harness is what tests it, CI is
# what runs it elsewhere, and evidence is everything the audits wrote.
def cat(f):
    if f.startswith("cpp/selftest/") or f.startswith("tools/"): return "harness"
    if f.startswith(".github/"): return "ci"
    if f.startswith("cpp/") or f == "Makefile": return "production"
    if f.startswith("audits/") or f.startswith("repairs/"): return "evidence"
    return "docs"
agg = {}
nbin = 0
for line in sys.stdin:
    p = line.split("\t")
    if len(p) < 3: continue
    a, d, f = p[0], p[1], p[2].strip()
    if a == "-":
        nbin += 1
        continue
    k = cat(f)
    v = agg.setdefault(k, [0, 0, 0])
    v[0] += 1; v[1] += int(a); v[2] += int(d)
tf = ti = td = 0
for k in ("production", "harness", "ci", "evidence", "docs"):
    f, i, d = agg.get(k, [0, 0, 0])
    tf += f; ti += i; td += d
    print("%-12s files=%-5d insertions=%-7d deletions=%d" % (k, f, i, d))
print("%-12s files=%-5d" % ("binary", nbin))
print("%-12s files=%-5d insertions=%-7d deletions=%d" % ("TOTAL-text", tf, ti, td))
f, i, d = agg.get("production", [0, 0, 0])
print("executable-churn: %d lines across %d files" % (i + d, f))
'
