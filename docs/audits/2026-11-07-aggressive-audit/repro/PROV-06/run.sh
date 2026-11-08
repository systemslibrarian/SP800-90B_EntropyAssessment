#!/bin/bash
# PROV-06: a repeated -o claims EVERY path with the fail-closed placeholder; only the last receives the report,
#          so the first path keeps a permanent "Refuse this file" placeholder after a run that exited 0.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-06 observed.txt
record_bin "$NONIID"
log "fixture sha256 $(sha "$FIX8")  $FIX8"
rm -f "$out/a.json" "$out/b.json"
run_tool repeated_o "$out/rep.out" "$out/rep.err" "$NONIID" -q -o "$out/a.json" -o "$out/b.json" "$FIX8" 8
log "a.json: errorLevel=$(jtop "$out/a.json" errorLevel) reportComplete=$(jtop "$out/a.json" reportComplete) testCases=$(jtop "$out/a.json" testCases) errorMessage=$(jtop "$out/a.json" errorMessage)"
log "b.json: errorLevel=$(jtop "$out/b.json" errorLevel) reportComplete=$(jtop "$out/b.json" reportComplete) Overall.hAssessed=$(jcase "$out/b.json" Overall hAssessed)"
log "stdout/stderr mention of the discarded first -o: stdout=$(grepc "a.json" "$out/rep.out") stderr=$(grepc "a.json" "$out/rep.err") (0 = no diagnostic)"
if [ "$RC" -eq 0 ] && [ "$(jtop "$out/a.json" errorLevel)" = "-1" ] && [ "$(jtop "$out/a.json" reportComplete)" = "false" ] && [ "$(jtop "$out/b.json" errorLevel)" = "0" ]; then
  verdict PASS "exit 0, b.json is the full report, a.json is left as a permanent placeholder (errorLevel -1, 'Refuse this file') with no diagnostic about the second -o"
fi
verdict FAIL "rc=$RC a.errorLevel=$(jtop "$out/a.json" errorLevel) b.errorLevel=$(jtop "$out/b.json" errorLevel)"
