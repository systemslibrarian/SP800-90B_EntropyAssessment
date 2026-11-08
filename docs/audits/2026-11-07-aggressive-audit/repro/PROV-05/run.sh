#!/bin/bash
# PROV-05: -vvv (verbose 4) prints NO per-estimator lines; every estimator prints at verbose == 3 exactly,
#          while the main's summary prints at verbose > 2. Usage says "-v ... Can be used multiple times."
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-05 observed.txt
record_bin "$NONIID"
log "fixture sha256 $(sha "$FIX8")  $FIX8"
run_tool vvv "$out/vvv.out" "$out/vvv.err" "$NONIID" -vvv "$FIX8" 8
n_est=$(grepc 'min entropy = ' "$out/vvv.out"); n_sum=$(grepc '^Assessed min entropy: ' "$out/vvv.out"); n_lines=$(wc -l < "$out/vvv.out" | tr -d ' ')
log "-vvv: per-estimator 'min entropy = ' lines: $n_est ; 'Assessed min entropy:' lines: $n_sum ; total stdout lines: $n_lines"
log "-vvv stdout (verbatim):"; sed 's/^/  | /' "$out/vvv.out" | tee -a "$OBS"
log "usage text for -v: $(grep -n 'Can be used multiple times' "$repo/cpp/non_iid_main.cpp" | sed 's/^/non_iid_main.cpp:/')"
[ "$RC" -eq 0 ] && [ "$n_est" -eq 0 ] && [ "$n_sum" -eq 1 ] && verdict PASS "-vvv prints the summary but zero per-estimator lines: more -v flags give LESS output than -vv"
verdict FAIL "rc=$RC est_lines=$n_est summary_lines=$n_sum"
