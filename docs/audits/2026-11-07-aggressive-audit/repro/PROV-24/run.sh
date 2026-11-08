#!/bin/bash
# PROV-24: under the test escape, ea_iid on an input shorter than the largest periodicity lag (p = 32) aborts:
#          `assert(n>=p)` in periodicity() (permutation_tests.h:256) -> SIGABRT, exit 134. F15-class (tiny inputs),
#          reachable only with EA_ALLOW_SHORT_DATASET=1; fail-closed (the -o placeholder stays).
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-24 observed.txt
record_bin "$IID"
"$PY" -c 'import sys; open(sys.argv[1],"wb").write(bytes([0,1,1,2,0,1,2,2,0,1,0,1,1,0,2,2,1,0,2,1]))' "$out/ex20.bin"
log "input sha256 $(sha "$out/ex20.bin")  (the 20 samples of SP 800-90B 6.3.1's worked example, PDF p. 50; width inferred 2)"
run_tool iid "$out/ab.out" "$out/ab.err" "$IID" -q -o "$out/ab.json" "$out/ex20.bin"
log "stderr (verbatim):"; sed 's/^/  | /' "$out/ab.err" | tee -a "$OBS"
asr=$(grepc 'Assertion failed' "$out/ab.err")
log "rc=$RC assertion lines=$asr ; ab.json errorLevel=$(jtop "$out/ab.json" errorLevel) reportComplete=$(jtop "$out/ab.json" reportComplete)"
log "code: $(grep -n 'assert(n>=p)' "$repo/cpp/iid/permutation_tests.h" | sed 's/^/permutation_tests.h:/' | tr '\n' ' ')"
[ "$RC" -eq 134 ] && [ "$asr" -ge 1 ] && verdict PASS "SIGABRT (exit 134) from assert(n>=p) in periodicity() on a 20-sample input under the escape; the C14 placeholder is what remains at -o"
verdict FAIL "rc=$RC assertion=$asr"
