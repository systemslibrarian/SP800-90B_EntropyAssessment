#!/bin/bash
# Analysis-phase probe for the aggregation component (non_iid_main.cpp lines 344-680).
# Tiny inputs (5,000 and 20,000 samples), EA_ALLOW_SHORT_DATASET=1, OMP_NUM_THREADS=2.
# Every output goes to a file; exit statuses are recorded in analysis-aggregation-probe-exit.log.
set -u
root=/Users/gmcas/repos/SP800-90B_EntropyAssessment
aud=$root/docs/audits/2026-11-07-aggressive-audit
bin=$root/cpp/ea_non_iid
logs=$aud/logs
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
: > "$logs/analysis-aggregation-probe-exit.log"
shasum -a 256 "$bin" "$aud/corpus/lag-rand8-5000.bin" "$aud/corpus/intake-lsb0-shifted-7bit-20000.bin" > "$logs/analysis-aggregation-probe-sha256.log"
run() { # name, args...
  local name=$1; shift
  "$bin" "$@" > "$logs/analysis-aggregation-$name.log" 2>&1
  echo "$name rc=$? :: $*" >> "$logs/analysis-aggregation-probe-exit.log"
}
f8=$aud/corpus/lag-rand8-5000.bin
f7=$aud/corpus/intake-lsb0-shifted-7bit-20000.bin
run probe1-i-vvv   -i -a -vvv -o "$logs/analysis-aggregation-probe1-i.json" "$f8" 8
run probe1-i-vv    -i -a -vv  "$f8" 8
run probe1-c-vvv   -c -a -vvv -o "$logs/analysis-aggregation-probe1-c.json" "$f8" 8
run probe1-c-vv    -c -a -vv  "$f8" 8
run probe3-i-t-vvv -i -t -vvv "$f8" 8
run probe4-i-inferred-vvv -i -a -vvv -o "$logs/analysis-aggregation-probe4-inferred.json" "$f7"
run probe4-c-inferred-vvv -c -a -vvv -o "$logs/analysis-aggregation-probe4-c-inferred.json" "$f7"
