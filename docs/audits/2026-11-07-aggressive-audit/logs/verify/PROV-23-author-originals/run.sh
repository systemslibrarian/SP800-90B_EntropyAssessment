#!/bin/bash
# PROV-23: the JSON permutationTestResults carry C0/C1/C2 ("iteration" 0/1/2) as PARTIAL counts -- the battery stops
#          evaluating a statistic once both pass conditions hold (permutation_tests.h:672-674) -- and no field says
#          how many of the 10,000 permutations were evaluated. A consumer reading C0 as "out of 10,000" misreads the rank.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-23 observed.txt
record_bin "$IID"
"$PY" -c 'import sys,random; r=random.Random(23); open(sys.argv[1],"wb").write(bytes(r.randrange(2) for _ in range(10000)))' "$out/fair10k.bin"
log "input sha256 $(sha "$out/fair10k.bin")  (10,000 fair bits, seed 23, width 1)"
run_tool iid "$out/p.out" "$out/p.err" "$IID" -q -o "$out/p.json" "$out/fair10k.bin" 1
log "rc=$RC errorLevel=$(jtop "$out/p.json" errorLevel) IID=$(jtop "$out/p.json" IID)"
res=$("$PY" - "$out/p.json" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]))
cs=[c for c in d['testCases'] if 'permutationTestResults' in c]; assert len(cs)==1
res=cs[0]['permutationTestResults'] or []
byit={r['iteration']:r for r in res}
stats=[k for k in byit.get(0,{}) if k not in ('iteration','dataLayout')]
partial=0; full=0
for s in sorted(stats):
    tot=sum(int(byit[i].get(s,0)) for i in (0,1,2))
    tag="partial" if tot<10000 else "full"
    if tot<10000: partial+=1
    else: full+=1
    print("  %-22s C0=%5d C1=%5d C2=%5d  sum=%5d  %s" % (s,byit[0].get(s,0),byit[1].get(s,0),byit[2].get(s,0),tot,tag))
keys=set()
def walk(o):
    if isinstance(o,dict):
        for k,v in o.items(): keys.add(k); walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(d)
known={'permutationTestResults','passedIidPermutationTests','ranIidPermutationTests','assessedSampleCount'}
denom=[k for k in keys if k not in known and any(t in k.lower() for t in ('evaluated','rounds','total','denominator','permutations','permcount','nperm','iterationsrun'))]
print("statistics with partial counts: %d of %d ; keys that could name the number of permutations evaluated: %s" % (partial,len(stats),",".join(sorted(denom)) or "none"))
print("DEFECT" if partial>0 and not denom else "NODEFECT")
PYEOF
)
log "$res"
printf '%s' "$res" | grep -q '^DEFECT$' && verdict PASS "the counters are partial (early termination) and nothing in the report states the number of permutations evaluated per statistic"
verdict FAIL "rc=$RC; see table"
