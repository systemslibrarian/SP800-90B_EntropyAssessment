#!/bin/bash
# PROV-04 negative control: the same file declared at its true width (4). No warning on stdout, same JSON shape.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-04 control.txt
record_bin "$NONIID"
run_tool declared4_q "$out/w4.out" "$out/w4.err" "$NONIID" -q -o "$out/w4.json" "$FIX4" 4
log "stdout under -q (verbatim):"; sed 's/^/  | /' "$out/w4.out" | tee -a "$OBS"
nwarn=$(grepc 'Warning: Symbols appear to be narrower than described' "$out/w4.out")
log "warning lines: $nwarn ; JSON errorLevel=$(jtop "$out/w4.json" errorLevel) bitsPerSymbol=$(jtop "$out/w4.json" bitsPerSymbol) errorMessage=$(jtop "$out/w4.json" errorMessage) hAssessed=$(jcase "$out/w4.json" Overall hAssessed)"
[ "$RC" -eq 0 ] && [ "$nwarn" -eq 0 ] && verdict CONTROL-OK "declared at the true width: no warning, identical JSON shape -- the declared-8 run differs only by the lost warning"
verdict CONTROL-UNEXPECTED "rc=$RC warnings=$nwarn"
