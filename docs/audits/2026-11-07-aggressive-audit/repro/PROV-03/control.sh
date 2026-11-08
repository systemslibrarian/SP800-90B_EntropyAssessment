#!/bin/bash
# PROV-03 negative control: a 1-bit file under -i. Only the Literal MCV runs (alph_size 2, no bitstring
# branch), so one estimate -> one triple, and the JSON triple is unambiguous and equals the only text triple.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-03 control.txt
record_bin "$NONIID"
log "fixture sha256 $(sha "$FIX1")  $FIX1 (10,000 samples, 1-bit)"
run_tool i1_vv "$out/m1.out" "$out/m1.err" "$NONIID" -i -vv -o "$out/m1.json" "$FIX1" 1
[ "$RC" -eq 0 ] || verdict CONTROL-UNEXPECTED "tool rc=$RC"
log "Bitstring MCV lines in text: $(grepc '^Bitstring Most Common Value Estimate' "$out/m1.out") (0 expected)"
lmode=$(grep "^Literal Most Common Value Estimate: Mode count = " "$out/m1.out" | sed 's/.*= //')
jmode=$(jcase "$out/m1.json" "Most Common Value" mcvEstimateMode)
log "text Literal mode=$lmode ; JSON mcvEstimateMode=$jmode"
ok=$("$PY" -c 'import sys; print("OK" if float(sys.argv[1])==float(sys.argv[2]) else "NO")' "$lmode" "$jmode")
[ "$ok" = "OK" ] && [ "$(grepc '^Bitstring Most Common Value Estimate' "$out/m1.out")" = "0" ] && verdict CONTROL-OK "one MCV estimate ran, one triple in the JSON, and it matches the only triple printed; the ambiguity needs two estimates sharing tc631"
verdict CONTROL-UNEXPECTED "control did not behave as predicted"
