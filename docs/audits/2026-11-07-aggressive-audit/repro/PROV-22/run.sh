#!/bin/bash
# PROV-22: xoshiro_jump(k, s) (utils.h:765-789) is not k canonical jumps for k >= 2 -- the accumulators are
#          declared outside the loop and never re-zeroed -- so OpenMP threads 2+ (permutation_tests.h:649) start
#          at a J-linear image of the seed rather than at k x 2^128. Reproduced by a transcription of the C
#          (model.py), not by the binary: no observable output of ea_iid depends on the offset, and the phase forbids
#          an instrumented build. Code-vs-comment defect; neutral.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-22 observed.txt
record_bin "$IID"
log "source sha256 $(sha "$repo/cpp/shared/utils.h")  cpp/shared/utils.h ; xoshiro_jump at lines $(grep -n 'void xoshiro_jump' "$repo/cpp/shared/utils.h" | cut -d: -f1)-"
sed -n 765,789p "$repo/cpp/shared/utils.h" | sed 's/^/  | /' | tee -a "$OBS"
log "caller: permutation_tests.h:$(grep -n 'xoshiro_jump(omp_get_thread_num()' "$repo/cpp/iid/permutation_tests.h" | cut -d: -f1)"
"$PY" "$here/model.py" 4 > "$out/model4.out" 2>&1; mrc=$?
sed 's/^/  model: /' "$out/model4.out" | tee -a "$OBS"
log "model exit (0 = every k agrees with canonical): $mrc"
k2=$(grep -c 'k=2 equals S1 xor S2 .*? True' "$out/model4.out" || true)
[ "$mrc" -ne 0 ] && [ "$k2" -eq 1 ] && verdict PASS "k >= 2 diverges from k canonical jumps and k = 2 equals S1 xor S2 exactly as the un-reset accumulators predict (model-level reproduction)"
verdict FAIL "model rc=$mrc k2=$k2"
