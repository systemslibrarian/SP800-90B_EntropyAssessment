#!/usr/bin/env bash
#
# OC-117: measure the DISTRIBUTION of the binding estimator's value on clean
# streams, so regression-outside-battery.sh's window can be set from a sample
# that has seen its tail instead of from five draws that had not.
#
# WHY. That check accepts the minimum-over-estimators in [0.8270, 0.8822],
# derived as 3 sd from "0.8546 +/- 0.0092" measured on FIVE clean streams
# (OC-16). OC-115 measured an ordinary draw of another source landing 0.00280
# inside the lower bound and a spread 9.7x wider than that +/- 0.0092. Widening
# the window from n = 5 would swap one under-sampled figure for another, so the
# tail is measured here instead.
#
# DISCIPLINE. Fresh seeds, the SAME two generators the corpus uses, read from
# blindspot_streams.py rather than reimplemented: Mersenne Twister via
# random.Random(seed).getrandbits(1), and SHA-256 counter mode keyed on
# 'sp90b-blindspot-%d'. The pinned corpus seeds (0xA, 0xC0+i, and sha 0..19)
# are EXCLUDED, so no draw here is one of the five the window came from.
#
# What is recorded per draw is what the check reads: WHICH estimator binds and
# its value. A draw where something other than Compression binds fails that
# check just as surely as one out of band, so both are counted.
set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../../.." && pwd)
tool="${repo}/cpp/ea_non_iid"
[ -x "${tool}" ] || { echo "compression-window-tail: no ea_non_iid" >&2; exit 2; }
DRAWS=${1:-200}
# A SECOND ARGUMENT, so a replication is a DIFFERENT SAMPLE and not a re-run of
# the same one. OC-119 needed this: the first n=300 sample was taken while the
# host later reported memory pressure, and the only way to test that sample is
# to draw an independent one. Any base clear of the pinned seeds works
# (0xA = 10, 0xC0+i = 192..196, sha 0..19).
SEEDBASE=${2:-900000}
work=$(mktemp -d "${TMPDIR:-/tmp}/ctail.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM

echo "draws=${DRAWS}  seedbase=${SEEDBASE}  N=1000000 samples  width=1  tool=$(basename "${tool}")"
echo "GEN SEED      BINDER                  VALUE"
i=0
while [ "${i}" -lt "${DRAWS}" ]; do
    # Fresh seeds well clear of the pinned ones (0xA = 10, 0xC0+i = 192..196,
    # sha 0..19). 900000+ cannot collide with any of them.
    seed=$((SEEDBASE + i))
    if [ $((i % 2)) -eq 0 ]; then gen=mt; else gen=sha; fi
    GEN="${gen}" SEED="${seed}" OUT="${work}/s.bin" python3 - "${repo}" <<'PY'
import os, sys, random, hashlib
sys.path.insert(0, os.path.join(sys.argv[1], 'audits/2026-10-11-independent-audit/generators'))
# Import the corpus generator so the discipline is READ, not reimplemented.
import blindspot_streams as B
gen, seed, out = os.environ['GEN'], int(os.environ['SEED']), os.environ['OUT']
if gen == 'mt':
    r = random.Random(seed)
    b = bytes(r.getrandbits(1) for _ in range(B.N))
else:
    b = bytes(B.sha_bits(seed, B.N))
open(out, 'wb').write(b)
PY
    out=$("${tool}" -i -a -v -v "${work}/s.bin" 1 2>&1)
    line=$(printf '%s\n' "${out}" | python3 -c '
import sys, re
d={}
for l in sys.stdin:
    m=re.match(r"^Literal (.*?) Estimate: min entropy = ([-0-9.e+]+)$", l.strip())
    if m: d[m.group(1)]=float(m.group(2))
if not d: print("NONE 0"); raise SystemExit
k=min(d, key=d.get)
print("%s %.9f" % (k.replace(" ","_"), d[k]))
')
    printf '%-3s %-9s %-23s %s\n' "${gen}" "${seed}" "${line% *}" "${line#* }"
    i=$((i + 1))
done
