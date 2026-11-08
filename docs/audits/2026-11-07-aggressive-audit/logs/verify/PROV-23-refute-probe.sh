#!/bin/bash
# PROV-23 REFUTE probe (verifier, independent parser). Tiny inputs only; writes files, reads files; never pipes a tool into head/tail.
set -u
REPO=/Users/gmcas/repos/SP800-90B_EntropyAssessment
AUD=$REPO/docs/audits/2026-11-07-aggressive-audit
LOG=$AUD/logs/verify/PROV-23-refute.log
W=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/prov23
IID=$REPO/cpp/ea_iid
PY=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/venv/bin/python
[ -x "$PY" ] || PY="$(command -v python3)"
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
: > "$LOG"
log(){ printf '%s\n' "$*" >> "$LOG"; }
log "# PROV-23 REFUTE probe  $(date '+%Y-%m-%d %H:%M:%S %z')  host=$(uname -srm)  verifier=independent parser (not the author's run.sh)"
log "# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every run below is NON-COMPLIANT (short dataset); nothing over 20,000 samples; no build"
log "# repo git=$(cd $REPO && git rev-parse --short HEAD) branch=$(cd $REPO && git branch --show-current)"
log "binary sha256 $(shasum -a 256 $IID | awk '{print $1}')  $IID  (README claims 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349)"
# inputs: author's fair10k.bin (as-is), plus my own 20,000 fair bits (w=1) and 20,000 uniform bytes (w=8) -- length/width variation of the same mechanism
cp $AUD/repro/PROV-23/out/fair10k.bin $W/a_fair10k.bin
"$PY" -c 'import sys,random; r=random.Random(9123); open(sys.argv[1],"wb").write(bytes(r.randrange(2) for _ in range(20000)))' $W/b_fair20k_w1.bin
"$PY" -c 'import sys,random; r=random.Random(9124); open(sys.argv[1],"wb").write(bytes(r.randrange(256) for _ in range(20000)))' $W/c_unif20k_w8.bin
for f in a_fair10k.bin b_fair20k_w1.bin c_unif20k_w8.bin; do log "input sha256 $(shasum -a 256 $W/$f | awk '{print $1}')  $f  bytes=$(wc -c < $W/$f | tr -d " ")"; done
run(){ # run <tag> <input> <width>
  local tag=$1 in=$2 w=$3
  log ""; log "\$ $IID -vv -o $W/$tag.json $in $w"
  "$IID" -vv -o "$W/$tag.json" "$in" "$w" > "$W/$tag.out" 2> "$W/$tag.err"; rc=$?
  log "rc=$rc  stdout=$W/$tag.out ($(wc -c < $W/$tag.out) bytes) stderr=$W/$tag.err ($(wc -c < $W/$tag.err) bytes)"
  grep -n 'Chi square tests\|longest repeated substring test\|IID permutation tests' "$W/$tag.out" | sed 's/^/  console | /' >> "$LOG"
  # the console's own counter table (print_results), verbatim, so text and JSON can be compared
  awk '/statistic  C\[i\]\[0\]/{p=1} p{print "  console | " $0} /denotes failed test/{p=0}' "$W/$tag.out" >> "$LOG"
  "$PY" - "$W/$tag.json" >> "$LOG" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]))
print("  json top-level keys:", ",".join(sorted(d.keys())))
print("  json errorLevel=%s IID=%s" % (d.get('errorLevel'), d.get('IID')))
cases=d.get('testCases') or []
print("  json testCases=%d ; keys per case: %s" % (len(cases), ";".join(",".join(sorted(c.keys())) for c in cases)))
# every key anywhere in the document, so an absent denominator is a conclusion from a complete listing (instrument rule 2)
allkeys=set()
def walk(o):
    if isinstance(o,dict):
        for k,v in o.items(): allkeys.add(k); walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(d)
print("  json ALL keys (%d): %s" % (len(allkeys), ",".join(sorted(allkeys))))
pr=[c for c in cases if c.get('permutationTestResults')]
if not pr:
    print("  permutationTestResults: ABSENT or null (battery did not run)"); sys.exit(0)
res=pr[0]['permutationTestResults']
print("  permutationTestResults: %d objects; per-object keys: %s" % (len(res), " | ".join(",".join(sorted(r.keys())) for r in res)))
byit={r['iteration']:r for r in res}
stats=sorted(k for k in byit[0] if k not in ('iteration','dataLayout'))
stopped=full=sig_ok=sig_bad=0; fails=0
for s in stats:
    c0,c1,c2=(byit[i].get(s) for i in (0,1,2))
    tot=c0+c1+c2
    passcond=(c0+c1>5) and (c1+c2>5)
    if tot<10000:
        stopped+=1
        m=min(c0+c1,c1+c2)
        ok = passcond and m==6   # the stop rule's signature: both sums >5 and the smaller is EXACTLY 6
        sig_ok+=ok; sig_bad+= (not ok)
        tag="STOPPED sig=%s min(C0+C1,C1+C2)=%d" % ("OK" if ok else "BAD", m)
    else:
        full+=1
        tag="FULL-10000 passcond=%s" % passcond
        fails += (not passcond)
    print("  %-22s C0=%6g C1=%6g C2=%6g sum=%6g  %s" % (s,c0,c1,c2,tot,tag))
print("  SUMMARY: statistics=%d stopped=%d (signature OK=%d BAD=%d) full=%d (of which fail the pass condition=%d)" % (len(stats),stopped,sig_ok,sig_bad,full,fails))
PYEOF
}
run a $W/a_fair10k.bin 1
run b $W/b_fair20k_w1.bin 1
run c $W/c_unif20k_w8.bin 8
log ""; log "# interpretation key: STOPPED sig=OK means the counts are exactly what permutation_tests.h:672-674 produces at the first permutation where both pass sums exceed 5;"
log "#   a parsing artefact or a stale binary could not produce min(C0+C1,C1+C2)==6 on every stopped row. FULL-10000 rows must fail the pass condition (else they would have stopped)."
log "# done $(date '+%Y-%m-%d %H:%M:%S %z')"
