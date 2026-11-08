#!/bin/bash
# PROV-24 REFUTE probe (verifier, 2026-11-08). Tiny inputs only (<= 256 samples). Nothing built.
# Objections tested:
#   P1  the identical 20-sample input WITHOUT EA_ALLOW_SHORT_DATASET  -> is it refused before any estimator? (reachability)
#   P2  -l 0,20 subset of a 10,000-byte fixture WITHOUT the escape   -> is the subset counted on loaded samples and refused?
#   P3/P4  under the escape, 31 vs 32 non-binary samples              -> is the boundary exactly n < p = 32 (assert) / n >= 32 (runs)?
#   P5/P6  under the escape, 248 vs 256 binary samples                -> conversion1 gives ceil(n/8) = 31 / 32: same boundary after /8?
# Every tool run writes stdout/stderr to files; rc is read from the producer; JSON reads are labelled (rule 17, instrument rule 5).
set -u
V=/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/verify
REPO=/Users/gmcas/repos/SP800-90B_EntropyAssessment
IID=$REPO/cpp/ea_iid
FIX8=$REPO/bin/rand8_short.bin
LOG=$V/PROV-24-refute.log
PY=$(command -v python3)
: > "$LOG"
log() { printf '%s\n' "$*" | tee -a "$LOG"; }
sha() { shasum -a 256 "$1" | awk '{print $1}'; }
jtop() { "$PY" -c 'import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception as e:
    print("<unreadable:%s>"%type(e).__name__); sys.exit(0)
k=sys.argv[2]; print(json.dumps(d[k]) if k in d else "<absent>")' "$1" "$2"; }
# run <tag> <env-escape 0|1> <args...>   (the -o file is $V/PROV-24-<tag>.json)
run() {
  local tag="$1" esc="$2"; shift 2
  local so="$V/PROV-24-$tag.out" se="$V/PROV-24-$tag.err" js="$V/PROV-24-$tag.json"
  rm -f "$js"
  if [ "$esc" = 1 ]; then
    log "\$ EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 ea_iid -q -o $(basename "$js") $*"
    EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 "$IID" -q -o "$js" "$@" > "$so" 2> "$se"; rc=$?
  else
    log "\$ (no EA_ALLOW_SHORT_DATASET) OMP_NUM_THREADS=2 ea_iid -q -o $(basename "$js") $*"
    env -u EA_ALLOW_SHORT_DATASET OMP_NUM_THREADS=2 "$IID" -q -o "$js" "$@" > "$so" 2> "$se"; rc=$?
  fi
  echo "$rc" > "$so.rc"
  local asr; asr=$(grep -c -- 'Assertion failed' "$se" 2>/dev/null || true)
  log "  rc=$rc  assertion-lines(stderr)=$asr  json.errorLevel=$(jtop "$js" errorLevel)  json.errorMsg=$(jtop "$js" errorMsg)  json.nonCompliantShortDataset=$(jtop "$js" nonCompliantShortDataset)  json.assessmentComplete=$(jtop "$js" assessmentComplete)"
  log "  stderr (verbatim, every line):"; sed 's/^/    | /' "$se" | tee -a "$LOG"
  log "  stdout lines matching Error|Warning|requires|Assertion (labelled grep, not positional):"; grep -n -E 'Error|Warning|requires|Assertion' "$so" | sed 's/^/    | /' | tee -a "$LOG"
  log ""
}
log "# PROV-24 REFUTE probe  $(date '+%Y-%m-%d %H:%M:%S %z')  host=$(uname -srm)"
log "# repo=$REPO git=$(cd "$REPO" && git rev-parse --short HEAD) branch=$(cd "$REPO" && git branch --show-current)"
log "# EA_ALLOW_SHORT_DATASET in the caller's environment at start: ${EA_ALLOW_SHORT_DATASET-<unset>}"
log "binary sha256 $(sha "$IID")  $IID  (mtime $(date -r "$IID" '+%Y-%m-%d %H:%M:%S'))"
log "README (repro/PROV-24) claims ea_iid sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349"
log "fixture sha256 $(sha "$FIX8")  $FIX8  ($(wc -c < "$FIX8" | tr -d " ") bytes)"
log ""
# inputs
"$PY" - "$V" <<'PYEOF'
import sys, random
V=sys.argv[1]
ex=[0,1,1,2,0,1,2,2,0,1,0,1,1,0,2,2,1,0,2,1]           # the 20 samples of SP 800-90B 6.3.1's worked example (PDF p. 50)
open(f"{V}/PROV-24-ex20.bin","wb").write(bytes(ex))
cyc=(ex*2)
open(f"{V}/PROV-24-nb31.bin","wb").write(bytes(cyc[:31]))
open(f"{V}/PROV-24-nb32.bin","wb").write(bytes(cyc[:32]))
r=random.Random(24)
bits=[r.randrange(2) for _ in range(256)]
open(f"{V}/PROV-24-b248.bin","wb").write(bytes(bits[:248]))
open(f"{V}/PROV-24-b256.bin","wb").write(bytes(bits[:256]))
PYEOF
for f in ex20 nb31 nb32 b248 b256; do log "input sha256 $(sha "$V/PROV-24-$f.bin")  PROV-24-$f.bin  ($(wc -c < "$V/PROV-24-$f.bin" | tr -d " ") bytes)"; done
log ""
log "== P1: the reproducer's own 20-sample input, NO escape =="
run p1-ex20-noescape 0 "$V/PROV-24-ex20.bin"
log "== P2: -l 0,20 subset of the 10,000-byte 8-bit fixture, NO escape =="
run p2-l20-noescape 0 -l 0,20 "$FIX8"
log "== P3: escape, 31 non-binary samples (n < p = 32) =="
run p3-nb31-escape 1 "$V/PROV-24-nb31.bin"
log "== P4: escape, 32 non-binary samples (n = p = 32) =="
run p4-nb32-escape 1 "$V/PROV-24-nb32.bin"
log "== P5: escape, 248 binary samples (conversion1 -> ceil(248/8) = 31 < 32) =="
run p5-b248-escape 1 "$V/PROV-24-b248.bin"
log "== P6: escape, 256 binary samples (conversion1 -> 32) =="
run p6-b256-escape 1 "$V/PROV-24-b256.bin"
log "# end of probe"
