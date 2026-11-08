#!/bin/bash
# PROV-18 (EXCLUDED-SCOPE: ea_conditioning is outside the supported build, cpp/Makefile SUPPORTED_TARGETS):
#          computeEntropyOfConditionedData() folds collision_test()'s -1.0 "declined" sentinel (v < 2) straight
#          into h' (conditioning_main.cpp:388-389, no `>= 0` guard, unlike every other fallible estimator in the
#          same function), so h' = -1 and h_out = min(..., h' x n_out) goes negative.
#          NOT RUN here: the binary cpp/ea_conditioning (built 2026-10-20) predates source changes to headers it
#          includes, and rebuilding is a build. Set EA_REPRO_FORCE=1 to run the stale binary anyway.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-18 observed.txt
[ -x "$COND" ] || verdict NOT-RUN "EXCLUDED-SCOPE: cpp/ea_conditioning is not built; building it is a build (forbidden this phase)"
record_bin "$COND"
log "fold without guard: $(grep -n 'collision_test(data.bsymbols' "$repo/cpp/conditioning_main.cpp" | sed 's/^/conditioning_main.cpp:/')"
log "sentinel:           $(grep -n 'return -1.0;' "$repo/cpp/non_iid/collision_test.h" | sed 's/^/collision_test.h:/' | tr '\n' ' ')"
log "intake in ea_conditioning: dataset_meets_minimum calls = $(grep -c dataset_meets_minimum "$repo/cpp/conditioning_main.cpp" || true) ; alph_size<=1 refusal = $(grep -c 'alph_size <= 1' "$repo/cpp/conditioning_main.cpp" || true)"
newer=$(find "$repo/cpp/conditioning_main.cpp" "$repo/cpp/shared" "$repo/cpp/non_iid" -type f -newer "$COND" | sed "s|$repo/||" | tr '\n' ' ')
log "sources newer than the binary: ${newer:-none}"
if [ -n "$newer" ] && [ "${EA_REPRO_FORCE:-0}" != "1" ]; then
  verdict NOT-RUN "EXCLUDED-SCOPE and STALE: cpp/ea_conditioning predates $newer; not run (EA_REPRO_FORCE=1 overrides)"
fi
"$PY" -c 'import sys; open(sys.argv[1],"wb").write(bytes([0,1,1]))' "$out/tiny.bin"
log "input sha256 $(sha "$out/tiny.bin")  (3 samples: 0x00 0x01 0x01; inferred width 1 -> bitstring 0,1,1: one collision, v = 1 < 2)"
run_tool cond_n "$out/cond.out" "$out/cond.err" "$COND" -n -i "$out/tiny.bin" 8 8 8 7.0
grep "^h' = \|^h_out\|h_out" "$out/cond.out" | sed 's/^/  | /' | tee -a "$OBS"
hp=$(grep "^h' = " "$out/cond.out" | sed "s/^h' = //")
ok=$("$PY" -c 'import sys
try: print("DEFECT" if float(sys.argv[1]) < 0 else "NODEFECT")
except Exception as e: print("NOPARSE")' "${hp:-x}")
[ "$ok" = "DEFECT" ] && verdict PASS "h' = $hp: the -1 decline sentinel was folded into h'"
verdict FAIL "rc=$RC h'='$hp' ($ok)"
