#!/bin/bash
# NOTE: -vv (verbose 3) is the level at which the estimators print their intermediates; -vvv prints none (PROV-05).
# PROV-03: the JSON "Most Common Value" element carries ONE mcvEstimateMode/PHat/PU triple although two MCV
#          estimates ran (Bitstring then Literal into the same tc631); under -i the triple is the LITERAL one
#          and the Bitstring triple appears nowhere in the report (F23 sub-claim a).
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-03 observed.txt
record_bin "$NONIID"
log "fixture sha256 $(sha "$FIX8")  $FIX8 (10,000 samples, 8-bit)"
run_tool i8_vv "$out/m8.out" "$out/m8.err" "$NONIID" -i -vv -o "$out/m8.json" "$FIX8" 8
[ "$RC" -eq 0 ] || verdict FAIL "tool rc=$RC"
get() { grep "^$1 Most Common Value Estimate: $2 = " "$out/m8.out" | sed 's/.*= //'; }
bmode=$(get Bitstring "Mode count"); bphat=$(get Bitstring "p-hat"); bpu=$(get Bitstring "p_u")
lmode=$(get Literal "Mode count");   lphat=$(get Literal "p-hat");   lpu=$(get Literal "p_u")
log "text Bitstring MCV: mode=$bmode p-hat=$bphat p_u=$bpu"
log "text Literal   MCV: mode=$lmode p-hat=$lphat p_u=$lpu"
jmode=$(jcase "$out/m8.json" "Most Common Value" mcvEstimateMode); jphat=$(jcase "$out/m8.json" "Most Common Value" mcvEstimatePHat); jpu=$(jcase "$out/m8.json" "Most Common Value" mcvEstimatePU)
jhb=$(jcase "$out/m8.json" "Most Common Value" hBitstring); jho=$(jcase "$out/m8.json" "Most Common Value" hOriginal)
log "JSON 'Most Common Value': mcvEstimateMode=$jmode mcvEstimatePHat=$jphat mcvEstimatePU=$jpu hBitstring=$jhb hOriginal=$jho"
ntriples=$("$PY" -c 'import json,sys; c=[x for x in json.load(open(sys.argv[1]))["testCases"] if x["testCaseDesc"]=="Most Common Value"][0]; print(len([k for k in c if k.startswith("mcvEstimate")]))' "$out/m8.json")
log "number of mcvEstimate* keys on that element: $ntriples (two estimates ran; 3 keys = one triple)"
log "occurrences of the Bitstring mode count '$bmode' anywhere in the JSON text: $(grepc "$bmode" "$out/m8.json")"
res=$("$PY" - "$jmode" "$jphat" "$jpu" "$lmode" "$lphat" "$lpu" "$bmode" "$bphat" "$bpu" <<'PYEOF'
import sys
j=list(map(float,sys.argv[1:4])); l=list(map(float,sys.argv[4:7])); b=list(map(float,sys.argv[7:10]))
eq=lambda a,c: all(abs(x-y)<=1e-12*max(1,abs(x)) for x,y in zip(a,c))
print("json==literal:",eq(j,l),"json==bitstring:",eq(j,b),"literal!=bitstring:",not eq(l,b))
print("DEFECT" if eq(j,l) and not eq(j,b) and not eq(l,b) else "NODEFECT")
PYEOF
)
log "$res"
printf '%s' "$res" | grep -q '^DEFECT$' && verdict PASS "under -i the single JSON MCV triple is the Literal one; the Bitstring triple (printed at -vv) is not in the report because the Literal call overwrote the shared tc631"
verdict FAIL "triples did not separate as predicted"
