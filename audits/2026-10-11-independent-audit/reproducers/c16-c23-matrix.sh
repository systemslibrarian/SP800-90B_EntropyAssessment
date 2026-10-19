#!/bin/bash
# OC-30: the joint behaviour of C16 and C23 on the restart sanity gate, with the
# C23 axis corrected. Builds ea_restart from the SAME source with the audit-only
# knobs, then runs four inputs through each build.
#
# THE C23 AXIS HAS THREE STATES, not two, because the first repair attempt
# (a5005bd, superseded) was itself a defect and the record must be able to show it:
#   upstream-sim  EA_RESTART_WITHOUT_C23_FIX        upstream's 5,000,000-round simulation of the
#                                                   multinomial maximum: right statistic, non-deterministic
#   printed-bin   EA_RESTART_C23_PRINTED_BINOMIAL   SP 800-90B 3.1.4.3 step 5 as printed: WRONG
#                                                   statistic, rejects correctly-operating sources
#   exact         (default)                         exact distribution of the multinomial maximum
#                                                   (Levin): right statistic, deterministic
#
# INPUTS
#   fullent   a genuinely FULL-ENTROPY 8-bit matrix at H_I = 8. The correct
#             verdict is ACCEPT, by construction: the data is drawn uniformly.
#             This is the column that exposes the printed formula.
#   sane      X_max = 24 at H_I = 7. Corrected cutoff 27, printed 23.
#   underflow H_I = 1e-400, X_max = 20.  (C16)
#   scale     H_I = 0.875 meant per bit, given bare, 8-bit symbol.  (C16)
#
# The pre-C16 parse cannot take '/symbol', so H_I is written bare for those
# builds and '<v>/symbol' for the C16 builds: same intent, the only syntax each
# accepts. Synthetic data throughout: these are claims about the instrument.
set -u
repo=$(cd "$(dirname "$0")/../../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/c16c23.XXXXXX"); trap 'rm -rf "$work"' EXIT
python3 - "$work" <<'PY'
import random, sys
out = sys.argv[1]
def forced(X, path):                       # column 17 forced to exactly X zeros
    r = random.Random(0xC23ACC); d = bytearray(r.getrandbits(8) for _ in range(1000000))
    col = [i*1000+17 for i in range(1000)]
    for i in col:
        if d[i] == 0: d[i] = 1
    for i in col[:X]: d[i] = 0
    open(path, 'wb').write(bytes(d))
forced(24, out + '/x24.bin'); forced(20, out + '/x20.bin')
r = random.Random(0xF0113E7)
open(out + '/fullent8.bin', 'wb').write(bytes(r.getrandbits(8) for _ in range(1000000)))
PY
# A missing input must never be reported as a refusal: the first run of this
# script had a broken generator and printed a uniform wall of "REFUSED" that
# actually meant "no such file". Fail closed instead.
for f in x24.bin x20.bin fullent8.bin; do
    [ -s "$work/$f" ] || { echo "generator did not write $f; refusing to classify" >&2; exit 2; }
done
python3 - "$work" <<'PY2'
import hashlib, sys
for f in ('x24.bin', 'x20.bin', 'fullent8.bin'):
    d = open(sys.argv[1] + '/' + f, 'rb').read()
    print("input %-14s %d bytes sha256 %s" % (f, len(d), hashlib.sha256(d).hexdigest()))
PY2

sha() { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi; }
# Each build here IS the mutation, so its landing has to be asserted: a flag
# that silently did nothing would give a row of plausible results for a build
# that is not the one named. Every variant's binary must differ from every
# other's. mutation-lib.sh records why this is mechanised rather than assumed.
build() { # build <name> <extra CXX flags>
    (cd "$repo/cpp" && make -B CXX="clang++ $2" restart >"$work/build-$1.log" 2>&1 \
        && cp ea_restart "$work/ea_restart.$1") || { echo "build $1 failed"; exit 2; }
    local d; d=$(sha "$work/ea_restart.$1")
    local prev
    for prev in $BUILT; do
        if [ "$d" = "$(sha "$work/ea_restart.$prev")" ]; then
            echo "MUTATION-DID-NOT-APPLY: build '$1' is byte-identical to '$prev'," >&2
            echo "  so its flags ($2) changed nothing. Refusing to report a matrix." >&2
            exit 2
        fi
    done
    BUILT="$BUILT $1"
    printf 'build %-16s sha256 %s\n' "$1" "$d"
}
BUILT=""
build sim_oldparse   "-DEA_RESTART_WITHOUT_C23_FIX -DEA_RESTART_WITHOUT_C16_FIX"
build sim_strict     "-DEA_RESTART_WITHOUT_C23_FIX"
build printed_strict "-DEA_RESTART_C23_PRINTED_BINOMIAL"
build exact_oldparse "-DEA_RESTART_WITHOUT_C16_FIX"
build exact_strict   ""
(cd "$repo/cpp" && make -B restart >/dev/null 2>&1)   # leave the tree's binary as the shipped build
run() { # run <variant> <matrix> <H_I>
    local out rc cut
    out=$(OMP_NUM_THREADS=4 "$work/ea_restart.$1" -v -n "$work/$2" 8 "$3" 2>&1); rc=$?
    cut=$(printf '%s' "$out" | sed -n 's/.*X_cutoff: \([0-9]*\).*/\1/p' | head -1)
    if printf '%s' "$out" | grep -qE 'Error reading file|could not open|is empty'; then echo "NO INPUT (harness fault)"
    elif printf '%s' "$out" | grep -qE 'must be|must state'; then echo "REFUSED"
    elif printf '%s' "$out" | grep -q 'Sanity Check Failed'; then echo "REJECT (cut $cut)"
    elif printf '%s' "$out" | grep -q 'Sanity Check Passed'; then echo "accept (cut $cut)"
    else echo "other rc=$rc"; fi
}
printf '%-14s %-10s | %-16s | %-14s | %-11s | %s\n' build C23 "fullent 8-bit H_I 8" "sane X_max 24" "underflow" "wrong scale"
printf '%s\n' "---------------------------|------------------|----------------|-------------|-------------"
for v in sim_oldparse sim_strict printed_strict exact_oldparse exact_strict; do
    case $v in *oldparse) sane=7; hi8=8; c16=old ;; *) sane=7/symbol; hi8=8/symbol; c16=strict ;; esac
    case $v in sim_*) axis=upstream-sim ;; printed_*) axis=printed-bin ;; *) axis=exact ;; esac
    printf '%-14s %-10s | %-16s | %-14s | %-11s | %s\n' "$c16/$axis" "$axis" \
        "$(run $v fullent8.bin $hi8)" "$(run $v x24.bin $sane)" \
        "$(run $v x20.bin 1e-400)" "$(run $v x20.bin 0.875)"
done
echo
echo "Expected: fullent must be ACCEPTED by every correct build (the data is uniform by"
echo "construction) and is REJECTED by printed-bin. underflow and wrong scale must be"
echo "REFUSED wherever C16 is strict. sane is accepted by the correct statistic (24 <= 27)"
echo "and rejected by printed-bin (24 > 23)."
echo
echo "## Determinism: the exact method is reproducible, the simulation is not"
for v in sim_strict exact_strict; do
    printf '  %-14s X_cutoff at H_I 8/symbol over 5 runs:' "$v"
    for i in 1 2 3 4 5; do
        printf ' %s' "$(OMP_NUM_THREADS=4 "$work/ea_restart.$v" -v -n "$work/fullent8.bin" 8 8/symbol 2>&1 | sed -n 's/.*X_cutoff: \([0-9]*\).*/\1/p' | head -1)"
    done; echo
done
echo
echo "## Cost: the exact method replaces a 5,000,000-round simulation"
for v in sim_strict exact_strict; do
    st=$(python3 -c 'import time; print(time.time())')
    OMP_NUM_THREADS=4 "$work/ea_restart.$v" -v -n "$work/fullent8.bin" 8 8/symbol >/dev/null 2>&1
    python3 -c "import sys,time; print('  %-14s full run: %.1f s' % ('$v', time.time()-$st))"
done
