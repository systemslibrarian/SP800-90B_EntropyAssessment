#!/bin/bash
# Independent re-run of PROV-01 by the CLASSIFY verifier, 2026-11-08. Tiny probe: 10,000 samples, EA_ALLOW_SHORT_DATASET=1 (NON-COMPLIANT), OMP_NUM_THREADS=2.
set -u
repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment
V=$repo/docs/audits/2026-11-07-aggressive-audit/logs/verify/PROV-01
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
OBS=$V/verify-observed.txt; : > "$OBS"
log(){ printf '%s\n' "$*" >> "$OBS"; }
sha(){ shasum -a 256 "$1" | awk '{print $1}'; }
el(){ python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d.get("errorLevel","<absent>"),d.get("reportComplete","<absent>"))' "$1"; }
log "# verify-observed.txt $(date '+%Y-%m-%d %H:%M:%S %z') host=$(uname -srm) git=$(git -C $repo rev-parse --short HEAD) branch=$(git -C $repo branch --show-current)"
log "# env EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- NON-COMPLIANT short-dataset runs"
for b in ea_non_iid ea_iid ea_restart; do log "binary sha256 $(sha $repo/cpp/$b) cpp/$b"; done
log "fixture sha256 $(sha $repo/bin/rand8_short.bin) bin/rand8_short.bin"
run(){ local lab=$1; shift; log "\$ $*"; "$@" > "$V/$lab.out" 2> "$V/$lab.err"; RC=$?; echo $RC > "$V/$lab.rc"; log "rc[$lab]=$RC"; }
# baseline
run base $repo/cpp/ea_non_iid -q -o "$V/good.json" $repo/bin/rand8_short.bin 8
G=$(sha "$V/good.json"); log "good.json sha256 $G errorLevel/reportComplete: $(el $V/good.json)"
probe(){ # probe <label> <expect:STALE|REPLACED> <cmd...>; the -o path must be $V/t_<label>.json
  local lab=$1 exp=$2; shift 2; cp "$V/good.json" "$V/t_$lab.json"
  run "$lab" "$@"
  local a; a=$(sha "$V/t_$lab.json"); local st
  if [ "$a" = "$G" ]; then st=STALE; else st=REPLACED; fi
  log "  $lab: file=$st (errorLevel/reportComplete now: $(el $V/t_$lab.json)) rc=$RC expected=$exp $([ "$st" = "$exp" ] && echo AS-EXPECTED || echo CONTRARY)"
}
# defect probes: option error BEFORE -o
probe nZ   STALE    $repo/cpp/ea_non_iid -Z -o "$V/t_nZ.json" $repo/bin/rand8_short.bin 8
probe nl   STALE    $repo/cpp/ea_non_iid -l 5x,10 -o "$V/t_nl.json" $repo/bin/rand8_short.bin 8
probe iZ   STALE    $repo/cpp/ea_iid -Z -o "$V/t_iZ.json" $repo/bin/rand8_short.bin 8
probe rZ   STALE    $repo/cpp/ea_restart -Z -o "$V/t_rZ.json" $repo/bin/rand8_short.bin 8 3/symbol
# OC-104 refusal (option after operand) -- runs before getopt, so also before the claim
probe n104 STALE    $repo/cpp/ea_non_iid -o "$V/t_n104.json" $repo/bin/rand8_short.bin 8 -v
# controls: same error AFTER -o
probe cZ   REPLACED $repo/cpp/ea_non_iid -o "$V/t_cZ.json" -Z $repo/bin/rand8_short.bin 8
probe cl   REPLACED $repo/cpp/ea_non_iid -o "$V/t_cl.json" -l 5x,10 $repo/bin/rand8_short.bin 8
probe ciZ  REPLACED $repo/cpp/ea_iid -o "$V/t_ciZ.json" -Z $repo/bin/rand8_short.bin 8
probe crZ  REPLACED $repo/cpp/ea_restart -o "$V/t_crZ.json" -Z $repo/bin/rand8_short.bin 8 3/symbol
# regression-output.sh's own shape: -o then nothing
probe cno  REPLACED $repo/cpp/ea_non_iid -o "$V/t_cno.json"
log "stderr of nZ: $(cat $V/nZ.err)"
log "stdout line1 of n104: $(sed -n 1p $V/n104.out)"
log "stderr of n104: $(cat $V/n104.err)"
log "DONE"
