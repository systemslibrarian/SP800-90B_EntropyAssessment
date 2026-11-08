#!/bin/bash
# PROV-16 negative control: ten ones instead of one. p_u = 0.9995 + 2.5758*sqrt(0.9995*0.0005/19999) = 0.99991 < 1,
# so no clamp: the estimate is a small POSITIVE number and no "-0" appears anywhere.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-16 control.txt
record_bin "$NONIID"
"$PY" -c 'import sys,random; L=20000; b=bytearray(L); r=random.Random(16)
for p in r.sample(range(L),10): b[p]=1
open(sys.argv[1],"wb").write(b)' "$out/ten-in-20000.bin"
log "input sha256 $(sha "$out/ten-in-20000.bin")  (20,000 samples: 19,990 x 0x00, ten 0x01 at seeded positions; width 1)"
run_tool vvv "$out/c_z.out" "$out/c_z.err" "$NONIID" -vvv -o "$out/c_z.json" "$out/ten-in-20000.bin" 1
grep '^Literal Most Common Value Estimate' "$out/c_z.out" | sed 's/^/  | /' | tee -a "$OBS"
h=$(jcase "$out/c_z.json" "Most Common Value" hOriginal)
log "JSON MCV hOriginal = $h ; lines with '-0' in the JSON: $(grep -c -- '-0' "$out/c_z.json" || true)"
ok=$("$PY" -c 'import sys; v=float(sys.argv[1]); print("OK" if v>0 else "NO")' "$h")
[ "$ok" = "OK" ] && [ "$RC" -eq 0 ] && verdict CONTROL-OK "with p_u < 1 the MCV estimate is positive ($h); the negative zero in run.sh is the clamp's -log2(1.0)"
verdict CONTROL-UNEXPECTED "rc=$RC h=$h"
