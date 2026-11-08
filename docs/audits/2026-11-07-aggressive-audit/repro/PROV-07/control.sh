#!/bin/bash
# PROV-07 negative control (two arms):
#   (a) -s 5000000 is accepted: parsing proceeds to the data read and the run fails LATER on the 10,000-sample
#       fixture with the specific size refusal, no usage dump;
#   (b) -s 1000x (not a decimal) IS given a reason line -- the tool can explain an -s refusal when it wants to.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-07 control.txt
record_bin "$RESTART"
run_tool s_5000000 "$out/c_s_5000000.out" "$out/c_s_5000000.err" "$RESTART" -n -s 5000000 "$FIX8" 8 3/symbol
ua=$(grepc 'Usage is:' "$out/c_s_5000000.out"); sz=$(grepc 'does not contain 1000000 samples' "$out/c_s_5000000.out")
log "  (a) -s 5000000: rc=$RC usage-dump=$ua size-refusal-line=$sz"
run_tool s_1000x "$out/c_s_1000x.out" "$out/c_s_1000x.err" "$RESTART" -n -s 1000x "$FIX8" 8 3/symbol
rb=$(grepc 'Simulation count must be an unsigned decimal integer' "$out/c_s_1000x.out")
log "  (b) -s 1000x: rc=$RC reason-line=$rb"
[ "$ua" -eq 0 ] && [ "$sz" -eq 1 ] && [ "$rb" -eq 1 ] && verdict CONTROL-OK "-s 5000000 is accepted (the run reaches the data-size refusal, no usage dump); a non-decimal -s gets a reason line -- only in-range values below 5e6 get the silent usage dump"
verdict CONTROL-UNEXPECTED "a=$ua/$sz b=$rb"
