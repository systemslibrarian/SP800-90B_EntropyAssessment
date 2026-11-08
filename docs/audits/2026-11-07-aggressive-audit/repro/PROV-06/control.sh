#!/bin/bash
# PROV-06 negative control: a single -o to the same first path. It receives the complete report.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-06 control.txt
record_bin "$NONIID"
rm -f "$out/a1.json"
run_tool single_o "$out/single.out" "$out/single.err" "$NONIID" -q -o "$out/a1.json" "$FIX8" 8
log "a1.json: errorLevel=$(jtop "$out/a1.json" errorLevel) reportComplete=$(jtop "$out/a1.json" reportComplete) Overall.hAssessed=$(jcase "$out/a1.json" Overall hAssessed)"
[ "$RC" -eq 0 ] && [ "$(jtop "$out/a1.json" errorLevel)" = "0" ] && verdict CONTROL-OK "one -o: the path holds the complete report; the placeholder in run.sh is the second -o's doing"
verdict CONTROL-UNEXPECTED "rc=$RC errorLevel=$(jtop "$out/a1.json" errorLevel)"
