#!/bin/bash
# PROV-13: non-binary chi-square independence test with nbin <= k gives df <= 0; SP 800-90B 5.2.1 says
#          "If the value of degrees of freedom is less than one, do not apply the test." The tool instead
#          prints df = -1, P-value = 1 (Cephes igamc returns 1.0 for a <= 0) and counts the test as PASSED.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-13 observed.txt
record_bin "$IID"
"$PY" "$here/gen.py" "$out/dfneg.bin" 2000 2000 1992,4,4 > "$out/gen.out"
log "input $(cat "$out/gen.out") sha256 $(sha "$out/dfneg.bin")  (corpus/iid-chisq-dfneg.bin was 7aed588a0c91bada25332b13b6e3af94ea8daae8c84764dccc0a5ea4c816224e)"
run_tool iid_vvv "$out/df.out" "$out/df.err" "$IID" -vvv -o "$out/df.json" "$out/dfneg.bin" 2
df=$(grep '^Chi square independence: df = ' "$out/df.out" | sed 's/.*= //')
pv=$(grep '^Chi square independence: P-value = ' "$out/df.out" | sed 's/.*= //')
T=$(grep '^Chi square independence: T = ' "$out/df.out" | sed 's/.*= //')
passed=$(grepc '^Chi square tests: Passed' "$out/df.out")
grep '^Chi square' "$out/df.out" | sed 's/^/  | /' | tee -a "$OBS"
jp=$("$PY" -c 'import json,sys; cs=[c for c in json.load(open(sys.argv[1]))["testCases"] if "passedChiSquareTests" in c]; assert len(cs)==1, len(cs); print(json.dumps(cs[0]["passedChiSquareTests"]), json.dumps(cs[0]["ranChiSquareTests"]))' "$out/df.json")
log "JSON passedChiSquareTests/ranChiSquareTests: $jp ; rc=$RC errorLevel=$(jtop "$out/df.json" errorLevel) IID=$(jtop "$out/df.json" IID)"
log "JSON keys carrying df, T, p-value or 'applied': $("$PY" -c 'import json,sys
def walk(o,a):
    if isinstance(o,dict):
        for k,v in o.items(): a.add(k); walk(v,a)
    elif isinstance(o,list):
        for v in o: walk(v,a)
a=set(); walk(json.load(open(sys.argv[1])),a); h=[k for k in a if any(s in k.lower() for s in ("df","degrees","pvalue","p_value","applied","chisquaret"))]; print(",".join(sorted(h)) or "none")' "$out/df.json")"
ok=$("$PY" -c 'import sys; df=int(sys.argv[1]); pv=float(sys.argv[2]); print("DEFECT" if df < 1 and pv == 1.0 else "NODEFECT")' "$df" "$pv")
[ "$ok" = "DEFECT" ] && [ "$passed" -eq 1 ] && printf '%s' "$jp" | grep -q '^true' && verdict PASS "df = $df (< 1) printed with P-value = 1 and 'Chi square tests: Passed'; JSON passedChiSquareTests true -- a test the standard says not to apply is reported as applied and passed"
verdict FAIL "df=$df pv=$pv passed=$passed json=$jp"
