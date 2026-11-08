#!/bin/bash
# PROV-16: when p_u clamps to exactly 1 the MCV estimate is -log2(1.0) = IEEE negative zero; the text prints
#          "min entropy = -0" and the JSON carries -0.0 (hOriginal on the MCV element and, since every later
#          min() keeps it, hAssessed). Cosmetic, conservative, but "-0.0" is what a consumer must parse.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-16 observed.txt
record_bin "$NONIID"
"$PY" -c 'import sys; L=20000; b=bytearray(L); b[12345]=1; open(sys.argv[1],"wb").write(b)' "$out/one-in-20000.bin"
log "input sha256 $(sha "$out/one-in-20000.bin")  (20,000 samples: 19,999 x 0x00, one 0x01 at index 12345; declared width 1)"
run_tool vvv "$out/z.out" "$out/z.err" "$NONIID" -vvv -o "$out/z.json" "$out/one-in-20000.bin" 1
grep '^Literal Most Common Value Estimate' "$out/z.out" | sed 's/^/  | /' | tee -a "$OBS"
grep '^Assessed min entropy' "$out/z.out" | sed 's/^/  | /' | tee -a "$OBS"
log "raw JSON text lines containing '-0': "; grep -n -- '-0' "$out/z.json" | sed 's/^/  | /' | tee -a "$OBS"
res=$("$PY" - "$out/z.json" <<'PYEOF'
import json,math,sys
d=json.load(open(sys.argv[1]))
mcv=[c for c in d['testCases'] if c['testCaseDesc']=='Most Common Value'][0]; ov=[c for c in d['testCases'] if c['testCaseDesc']=='Overall'][0]
h=mcv['hOriginal']; ha=ov['hAssessed']
neg=lambda v: v==0.0 and math.copysign(1.0,v)<0
print("MCV hOriginal = %r (negative zero: %s) ; Overall hAssessed = %r (negative zero: %s) ; str compare to '0': %s" % (h,neg(h),ha,neg(ha), str(h)=='0'))
print("DEFECT" if neg(h) else "NODEFECT")
PYEOF
)
log "$res"
printf '%s' "$res" | grep -q '^DEFECT$' && [ "$RC" -eq 0 ] && verdict PASS "p_u clamps to 1 -> -log2(1.0) = -0.0: text 'min entropy = -0', JSON hOriginal -0.0 on the MCV element (and hAssessed -0.0)"
verdict FAIL "rc=$RC $res"
