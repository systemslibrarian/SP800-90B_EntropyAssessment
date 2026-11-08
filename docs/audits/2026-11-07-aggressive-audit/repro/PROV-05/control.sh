#!/bin/bash
# PROV-05 negative control: one fewer -v. -vv (verbose 3) prints every per-estimator line.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-05 control.txt
record_bin "$NONIID"
run_tool vv "$out/vv.out" "$out/vv.err" "$NONIID" -vv "$FIX8" 8
n_est=$(grepc 'min entropy = ' "$out/vv.out"); n_sum=$(grepc '^Assessed min entropy: ' "$out/vv.out")
log "-vv: per-estimator 'min entropy = ' lines: $n_est ; 'Assessed min entropy:' lines: $n_sum"
grep 'min entropy = ' "$out/vv.out" | sed 's/^/  | /' | tee -a "$OBS"
[ "$RC" -eq 0 ] && [ "$n_est" -ge 10 ] && verdict CONTROL-OK "-vv prints $n_est per-estimator lines; adding a third -v (run.sh) removes all of them"
verdict CONTROL-UNEXPECTED "rc=$RC est_lines=$n_est"
