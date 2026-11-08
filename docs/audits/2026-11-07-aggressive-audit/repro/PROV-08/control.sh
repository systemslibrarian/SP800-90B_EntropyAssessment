#!/bin/bash
# PROV-08 negative control (HEAVY, same input): without -q the H_I line is expected output (verbose 1), so its
# presence is not a defect there. The difference run.sh shows is that -q removes every OTHER verbose-1 line
# (e.g. "*** Restart Sanity Check Failed ***") but not this one.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-08 control.txt
record_bin "$RESTART"
heavy_guard "ea_restart requires a 1,000,000-sample matrix"
M="$out/rows-constant-1e6.bin"
[ -f "$M" ] || "$PY" -c 'import sys
L=1_000_000; b=bytearray(L)
for i in range(L): b[i]=(i//1000)&1
open(sys.argv[1],"wb").write(b)' "$M"
run_tool restart_v1 "$out/c_v1.out" "$out/c_v1.err" "$RESTART" -n -o "$out/c_v1.json" "$M" 1 0.5
log "stdout at verbose 1 (verbatim):"; sed 's/^/  | /' "$out/c_v1.out" | tee -a "$OBS"
n=$(grepc '^H_I: ' "$out/c_v1.out"); f=$(grepc 'Restart Sanity Check Failed' "$out/c_v1.out")
log "H_I lines: $n ; sanity-failed lines: $f"
[ "$n" -ge 1 ] && [ "$f" -ge 1 ] && verdict CONTROL-OK "at verbose 1 both the H_I line and the verdict line print; -q (run.sh) suppresses the verdict line but not H_I"
verdict CONTROL-UNEXPECTED "H_I=$n failed=$f rc=$RC"
