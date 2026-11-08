#!/bin/bash
# PROV-24 negative control: the same 20 samples repeated five times (L = 100 >= 32). No assert; the battery runs.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-24 control.txt
record_bin "$IID"
"$PY" -c 'import sys; open(sys.argv[1],"wb").write(bytes([0,1,1,2,0,1,2,2,0,1,0,1,1,0,2,2,1,0,2,1]*5))' "$out/ex100.bin"
log "input sha256 $(sha "$out/ex100.bin")  (100 samples = the worked example x5; width inferred 2)"
run_tool iid "$out/c_ab.out" "$out/c_ab.err" "$IID" -q -o "$out/c_ab.json" "$out/ex100.bin"
asr=$(grepc 'Assertion failed' "$out/c_ab.err")
log "rc=$RC assertion lines=$asr ; c_ab.json errorLevel=$(jtop "$out/c_ab.json" errorLevel) assessmentComplete=$(jtop "$out/c_ab.json" assessmentComplete)"
[ "$RC" -ne 134 ] && [ "$asr" -eq 0 ] && verdict CONTROL-OK "at L = 100 the battery completes (rc $RC, a verdict); the abort in run.sh is L = 20 < p = 32"
verdict CONTROL-UNEXPECTED "rc=$RC assertion=$asr"
