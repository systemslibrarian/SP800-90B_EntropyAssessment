#!/usr/bin/env bash
#
# OC-121, rule 14 applied to the last unreplicated sample-derived constraint.
#
# tools/outside-battery-check.cpp thresholds the top spectral line at 30.0x
# mean power, and that number is EMPIRICAL: "1.48x the observed clean max of
# 20.2 over 25 clean streams". A threshold set at 1.48x an observed maximum
# from 25 draws is exactly the shape rule 14 exists for -- and the companion
# measurement (OC-119) showed a clean-stream extremum moving by 0.0099 between
# two samples of 300.
#
# Its sibling threshold, 5.731 sigma, is NOT in this category: it is DERIVED
# (Bonferroni over 100,000 lags at family-wise alpha 0.001) and the 25 streams
# were its validation rather than its source. Rule 14 does not apply to it.
#
# Fresh seeds from 920000, clear of the pinned 0xA / 0xC0+i / sha 0..19 and of
# the 900000/910000 bases compression-window-tail.sh used.
set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../../.." && pwd)
tool="${repo}/tools/outside-battery-check"
[ -x "${tool}" ] || { echo "spectral-threshold-tail: no outside-battery-check" >&2; exit 2; }
DRAWS=${1:-60}
SEEDBASE=${2:-920000}
work=$(mktemp -d "${TMPDIR:-/tmp}/spec.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM

echo "draws=${DRAWS}  seedbase=${SEEDBASE}  recorded clean max=20.2 (n=25)  threshold=30.0"
echo "GEN SEED      TOP-LINE"
i=0
while [ "${i}" -lt "${DRAWS}" ]; do
    seed=$((SEEDBASE + i))
    if [ $((i % 2)) -eq 0 ]; then gen=mt; else gen=sha; fi
    GEN="${gen}" SEED="${seed}" OUT="${work}/s.bin" python3 - "${repo}" <<'PY'
import os, sys, random
sys.path.insert(0, os.path.join(sys.argv[1], 'audits/2026-10-11-independent-audit/generators'))
import blindspot_streams as B
gen, seed, out = os.environ['GEN'], int(os.environ['SEED']), os.environ['OUT']
# THE Random OBJECT IS HOISTED. Written inline as
#   bytes(random.Random(seed).getrandbits(1) for _ in range(B.N))
# it constructs a NEW generator seeded identically on every draw, so every bit
# comes out the same and the stream has ZERO VARIANCE. Caught by
# outside-battery-check's own degenerate-input guard -- "degenerate input (zero
# variance)" -- on 2 of the first 3 draws, which is the tool refusing rather
# than reporting a number about a constant stream.
if gen == 'mt':
    r = random.Random(seed)
    b = bytes(r.getrandbits(1) for _ in range(B.N))
else:
    b = bytes(B.sha_bits(seed, B.N))
open(out, 'wb').write(b)
PY
    # never pipe the subject: capture, then read
    "${tool}" "${work}/s.bin" > "${work}/out.txt" 2>&1
    top=$(sed -n 's/.*top line \([0-9.]*\)x mean power.*/\1/p' "${work}/out.txt" | head -1)
    [ -n "${top}" ] || top=UNREADABLE
    printf '%-3s %-9s %s\n' "${gen}" "${seed}" "${top}"
    i=$((i + 1))
done
