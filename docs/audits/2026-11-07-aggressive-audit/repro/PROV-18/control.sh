#!/bin/bash
# PROV-18 negative control (EXCLUDED-SCOPE, same staleness guard): a 20,000-byte conditioned file has thousands
# of collisions, collision_test returns a value in [0,1], and h' stays in [0,1].
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-18 control.txt
[ -x "$COND" ] || verdict NOT-RUN "EXCLUDED-SCOPE: cpp/ea_conditioning is not built"
record_bin "$COND"
newer=$(find "$repo/cpp/conditioning_main.cpp" "$repo/cpp/shared" "$repo/cpp/non_iid" -type f -newer "$COND" | wc -l | tr -d ' ')
[ "$newer" -gt 0 ] && [ "${EA_REPRO_FORCE:-0}" != "1" ] && verdict NOT-RUN "EXCLUDED-SCOPE and STALE: $newer source files are newer than cpp/ea_conditioning"
"$PY" -c 'import sys,random; r=random.Random(18); open(sys.argv[1],"wb").write(bytes(r.randrange(256) for _ in range(20000)))' "$out/rand20k.bin"
log "input sha256 $(sha "$out/rand20k.bin")  (20,000 random bytes)"
run_tool cond_n "$out/c_cond.out" "$out/c_cond.err" "$COND" -n -i "$out/rand20k.bin" 8 8 8 7.0
hp=$(grep "^h' = " "$out/c_cond.out" | sed "s/^h' = //")
log "rc=$RC h' = $hp"
ok=$("$PY" -c 'import sys
try: v=float(sys.argv[1]); print("OK" if 0.0 <= v <= 1.0 else "NO")
except Exception: print("NOPARSE")' "${hp:-x}")
[ "$ok" = "OK" ] && verdict CONTROL-OK "with enough collisions h' is in [0,1]"
verdict CONTROL-UNEXPECTED "rc=$RC h'='$hp'"
