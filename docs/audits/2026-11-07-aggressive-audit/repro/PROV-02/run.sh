#!/bin/bash
# PROV-02: under -c the stdout figure h' is PER BIT (SP 800-90B 3.1.5.2) while the JSON hAssessed is word_size x h'
#          (per packed symbol), under the same name the -i report uses for its per-sample figure, with no unit field.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-02 observed.txt
record_bin "$NONIID"
log "fixture sha256 $(sha "$FIX8")  $FIX8 (10,000 samples, 8-bit)"
run_tool c8_default "$out/c8.out" "$out/c8.err" "$NONIID" -c -o "$out/c8.json" "$FIX8" 8
[ "$RC" -eq 0 ] || verdict FAIL "tool rc=$RC"
hprime=$(grep "^h': " "$out/c8.out" | sed "s/^h': //")
log "stdout line:            h': $hprime        (printf \"\\nh': %f\\n\", H_bitstring -- per bit)"
hA=$(jcase "$out/c8.json" Overall hAssessed); hB=$(jcase "$out/c8.json" Overall hBitstring)
dws=$(jcase "$out/c8.json" Overall dataWordSize); hO=$(jcase "$out/c8.json" Overall hOriginal)
log "JSON Overall.hAssessed   = $hA"
log "JSON Overall.hBitstring  = $hB"
log "JSON Overall.dataWordSize= $dws"
log "JSON Overall.hOriginal   = $hO"
unitkeys=$("$PY" - "$out/c8.json" <<'PYEOF'
import json,sys
def walk(o,acc):
    if isinstance(o,dict):
        for k,v in o.items():
            acc.add(k); walk(v,acc)
    elif isinstance(o,list):
        for v in o: walk(v,acc)
acc=set(); walk(json.load(open(sys.argv[1])),acc)
hits=sorted(k for k in acc if 'unit' in k.lower() or 'perbit' in k.lower() or 'persymbol' in k.lower() or 'mode' == k.lower() or 'hprime' in k.lower())
print(",".join(hits) if hits else "none")
PYEOF
)
log "JSON keys naming a unit/mode/h-prime anywhere in the document: $unitkeys"
# second run at -vvv for the 17-digit text figures (no h' line exists at this level)
run_tool c8_vvv "$out/c8v.out" "$out/c8v.err" "$NONIID" -c -vvv -o "$out/c8v.json" "$FIX8" 8
grep "^H_bitstring = \|^H_bitstring Per Symbol = \|^Assessed min entropy: \|^h': " "$out/c8v.out" | while IFS= read -r l; do log "  -vvv text: $l"; done
log "  -vvv text has an h' line: $(grepc "^h': " "$out/c8v.out") (0 expected -- only the 'Assessed' label exists at this level)"
res=$("$PY" - "$hA" "$hB" "$dws" "$hprime" <<'PYEOF'
import sys
hA,hB,dws,hp=map(float,sys.argv[1:5])
same_unit_as_text = abs(hA-hp) < 1e-5
is_n_times_hprime = abs(hA - dws*hB) <= 1e-12*max(1.0,abs(hA)) and abs(dws*hp - hA) < 1e-5*dws
print("ratio hAssessed/hBitstring = %.17g ; hAssessed == dataWordSize*hBitstring: %s ; hAssessed equals the text h': %s" % (hA/hB, is_n_times_hprime, same_unit_as_text))
print("DEFECT" if (is_n_times_hprime and not same_unit_as_text and dws>1) else "NODEFECT")
PYEOF
)
log "$res"
case "$res" in *DEFECT) ;; esac
if printf '%s' "$res" | grep -q '^DEFECT$'; then
  verdict PASS "stdout h' is per bit; JSON hAssessed = dataWordSize x h' (x8 here) under the same key name as the -i per-sample figure; no unit or mode field in the report"
fi
verdict FAIL "hAssessed did not equal dataWordSize x h' or equalled the text figure"
