#!/bin/bash
# PROV-02 negative control: the same -c run on a 1-bit file. word_size = 1, so the text h' and the JSON
# hAssessed carry the same number; the unit trap exists only when the packing width exceeds 1.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-02 control.txt
record_bin "$NONIID"
log "fixture sha256 $(sha "$FIX1")  $FIX1 (10,000 samples, 1-bit)"
run_tool c1_default "$out/c1.out" "$out/c1.err" "$NONIID" -c -o "$out/c1.json" "$FIX1" 1
[ "$RC" -eq 0 ] || verdict CONTROL-UNEXPECTED "tool rc=$RC"
hprime=$(grep "^h': " "$out/c1.out" | sed "s/^h': //")
hA=$(jcase "$out/c1.json" Overall hAssessed); hB=$(jcase "$out/c1.json" Overall hBitstring); dws=$(jcase "$out/c1.json" Overall dataWordSize)
log "stdout h': $hprime ; JSON hAssessed=$hA hBitstring=$hB dataWordSize=$dws"
ok=$("$PY" -c 'import sys; hA,hp,dws=map(float,sys.argv[1:4]); print("OK" if abs(hA-hp)<1e-5 and dws==1 else "NO")' "$hA" "$hprime" "$dws")
[ "$ok" = "OK" ] && verdict CONTROL-OK "at word_size 1 the text h' and JSON hAssessed agree to the printed precision; the x8 gap in run.sh is the packing width"
verdict CONTROL-UNEXPECTED "text and JSON disagree even at word_size 1"
