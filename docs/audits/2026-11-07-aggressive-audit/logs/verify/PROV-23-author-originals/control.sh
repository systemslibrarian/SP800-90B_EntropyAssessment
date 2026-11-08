#!/bin/bash
# PROV-23 negative control: an input with ANTI-correlated lag-64 bit dependence (b_i = NOT b_{i-64} w.p. 0.75).
# Within any window shorter than 64 bits the bits are independent and fair, so the 11-bit chi-square tuples and
# the decile goodness-of-fit pass; complemented copies create no long repeats, so LRS passes; but periodicity(8)
# on Conversion-I bytes (lag 8 bytes = 64 bits) is far BELOW every permutation's, so C0 reaches 10,000: that
# statistic never satisfies both pass conditions, is evaluated for all 10,000 permutations, and its C-sum is
# exactly 10,000 -- the "out of 10,000" a consumer expects, which the passing statistics never reach.
# (A first attempt with POSITIVE lag-64 copying failed GOF and LRS first -- variance inflation and long repeats --
#  and the battery was skipped; that run is kept in logs/repro/PROV-23-control.first-attempt.log.)
# (The verdict is seeded from /dev/urandom; if chi-square or LRS fail first the battery is skipped and this
#  control cannot show its contrast -- it says so rather than guessing.)
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-23 control.txt
record_bin "$IID"
"$PY" -c 'import sys,random
r=random.Random(2323); L=10000; b=[0]*L
for i in range(L):
    b[i]= (1-b[i-64]) if (i>=64 and r.random()<0.75) else r.randrange(2)
open(sys.argv[1],"wb").write(bytes(b))' "$out/lag64anti.bin"
log "input sha256 $(sha "$out/lag64anti.bin")  (10,000 bits, b_i = 1-b_{i-64} w.p. 0.75 else fresh, seed 2323)"
run_tool iid "$out/c_p.out" "$out/c_p.err" "$IID" -vv -o "$out/c_p.json" "$out/lag64anti.bin" 1
log "rc=$RC errorLevel=$(jtop "$out/c_p.json" errorLevel) IID=$(jtop "$out/c_p.json" IID)"
grep -i 'chi square\|longest repeated\|permutation' "$out/c_p.out" | grep -i 'pass\|fail' | sed 's/^/  | /' | tee -a "$OBS"
res=$("$PY" - "$out/c_p.json" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]))
cs=[c for c in d['testCases'] if 'permutationTestResults' in c]
res=(cs[0]['permutationTestResults'] if cs else None) or []
if not res: print("NOPERM: permutation battery did not run (an earlier deterministic test failed)"); sys.exit(0)
byit={r['iteration']:r for r in res}
stats=[k for k in byit.get(0,{}) if k not in ('iteration','dataLayout')]
full=[]
for s in sorted(stats):
    tot=sum(int(byit[i].get(s,0)) for i in (0,1,2))
    if tot==10000: full.append("%s(C0=%d,C1=%d,C2=%d)" % (s,byit[0].get(s,0),byit[1].get(s,0),byit[2].get(s,0)))
print("statistics evaluated for all 10,000 permutations:", ", ".join(full) if full else "none")
print("FULL" if full else "NOFULL")
PYEOF
)
log "$res"
printf '%s' "$res" | grep -q '^FULL$' && verdict CONTROL-OK "a failing statistic runs the full 10,000 permutations and its C-sum is 10,000; the passing statistics in run.sh stop early with sums of a few dozen, and the report does not say which happened"
printf '%s' "$res" | grep -q '^NOPERM' && verdict CONTROL-UNEXPECTED "the permutation battery was skipped on this input (deterministic test failed first); regenerate with a different seed"
verdict CONTROL-UNEXPECTED "no statistic ran to 10,000: $res"
