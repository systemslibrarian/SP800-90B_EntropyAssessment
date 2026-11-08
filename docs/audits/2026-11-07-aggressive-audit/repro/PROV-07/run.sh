#!/bin/bash
# PROV-07: ea_restart -s is documented "Accepted for compatibility and ignored", but a value below
#          DEFAULT_SIMULATION_ROUNDS (5,000,000) or 0 is REFUSED through a bare print_usage() with no reason line.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-07 observed.txt
record_bin "$RESTART"
log "usage text: $(grep -n 'Accepted for compatibility and ignored' "$repo/cpp/restart_main.cpp" | sed 's/^/restart_main.cpp:/')"
log "code:       $(grep -n 'inul < simulation_rounds' "$repo/cpp/restart_main.cpp" | sed 's/^/restart_main.cpp:/')"
bad=0; total=0
try() {  # try <value>
  local v="$1"
  run_tool "s_$v" "$out/s_$v.out" "$out/s_$v.err" "$RESTART" -n -s "$v" "$FIX8" 8 3/symbol
  local usage reason
  usage=$(grepc 'Usage is:' "$out/s_$v.out"); reason=$(grep -c -E '^(Error|Simulation count|\*\*\*)' "$out/s_$v.out" || true)
  log "  -s $v: rc=$RC usage-dump=$usage reason-lines=$reason first-stdout-line='$(sed -n 1p "$out/s_$v.out")'"
  total=$((total+1))
  [ "$RC" -ne 0 ] && [ "$usage" -ge 1 ] && [ "$reason" -eq 0 ] && bad=$((bad+1))
}
try 1000; try 4999999; try 0
log "bare-usage refusals: $bad of $total"
[ "$bad" -eq "$total" ] && verdict PASS "-s 1000 / -s 4999999 / -s 0 are refused with a bare usage dump (no reason line) although the usage text says the option is accepted and ignored"
verdict FAIL "only $bad of $total refused as predicted"
