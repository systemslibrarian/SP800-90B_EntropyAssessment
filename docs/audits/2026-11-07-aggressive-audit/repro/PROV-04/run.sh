#!/bin/bash
# PROV-04: "Warning: Symbols appear to be narrower than described." is printed on stdout even under -q and
#          never reaches the JSON: errorMsg is set with errorLevel left 0, and GetBaseJson emits errorMessage
#          only when errorLevel != 0.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-04 observed.txt
record_bin "$NONIID"
log "fixture sha256 $(sha "$FIX4")  $FIX4 (10,000 samples, 4-bit values; declared 8 below)"
run_tool declared8_q "$out/w8.out" "$out/w8.err" "$NONIID" -q -o "$out/w8.json" "$FIX4" 8
log "stdout under -q (verbatim):"; sed 's/^/  | /' "$out/w8.out" | tee -a "$OBS"
nwarn=$(grepc 'Warning: Symbols appear to be narrower than described' "$out/w8.out")
log "warning lines on stdout under -q: $nwarn"
log "JSON errorLevel=$(jtop "$out/w8.json" errorLevel) errorMessage=$(jtop "$out/w8.json" errorMessage) bitsPerSymbol=$(jtop "$out/w8.json" bitsPerSymbol) bitsPerSymbolInferred=$(jtop "$out/w8.json" bitsPerSymbolInferred)"
log "JSON top-level keys: $(jkeys "$out/w8.json")"
log "JSON Overall.hAssessed=$(jcase "$out/w8.json" Overall hAssessed)"
if [ "$RC" -eq 0 ] && [ "$nwarn" -ge 1 ] && [ "$(jtop "$out/w8.json" errorLevel)" = "0" ] && [ "$(jtop "$out/w8.json" errorMessage)" = "<absent>" ]; then
  verdict PASS "the width-mismatch warning is printed on stdout despite -q, exit 0, and the JSON (errorLevel 0) carries no errorMessage, no warning field; a JSON-only consumer cannot see that the declared width was wrong"
fi
verdict FAIL "rc=$RC warnings=$nwarn errorLevel=$(jtop "$out/w8.json" errorLevel) errorMessage=$(jtop "$out/w8.json" errorMessage)"
