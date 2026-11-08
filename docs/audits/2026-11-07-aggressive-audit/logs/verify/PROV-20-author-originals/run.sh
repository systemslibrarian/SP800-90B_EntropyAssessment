#!/bin/bash
# PROV-20: contradictory mode flags (-i with -c, -a with -t) are resolved silently by the LAST one; no diagnostic.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-20 observed.txt
record_bin "$NONIID"
run_tool i_then_c "$out/ic.out" "$out/ic.err" "$NONIID" -i -c "$FIX8" 8
ic_rc=$RC; ic_h=$(grep "^h': " "$out/ic.out" | sed "s/^h': //"); ic_o=$(grepc '^H_original: ' "$out/ic.out")
log "  -i -c: rc=$ic_rc  h'=$ic_h  H_original lines=$ic_o  (conditioned mode won)"
run_tool c_then_i "$out/ci.out" "$out/ci.err" "$NONIID" -c -i "$FIX8" 8
ci_rc=$RC; ci_o=$(grep "^H_original: " "$out/ci.out" | sed 's/^H_original: //'); ci_h=$(grepc "^h': " "$out/ci.out")
log "  -c -i: rc=$ci_rc  H_original=$ci_o  h' lines=$ci_h  (initial mode won)"
run_tool a_then_t "$out/at.out" "$out/at.err" "$NONIID" -a -t -vv "$FIX8" 8
at_rc=$RC; log "  -a -t -vv: rc=$at_rc  Number of Binary Symbols line: $(grep '^Number of Binary Symbols' "$out/at.out")"
diag=$(cat "$out/ic.out" "$out/ic.err" "$out/ci.out" "$out/ci.err" "$out/at.out" "$out/at.err" | grep -c -i 'conflict\|both -i and -c\|overrid\|ignor' || true)
log "diagnostic lines about the contradiction in any of the six streams: $diag"
[ "$ic_rc" -eq 0 ] && [ "$ci_rc" -eq 0 ] && [ "$at_rc" -eq 0 ] && [ "$diag" -eq 0 ] && [ -n "$ic_h" ] && [ -n "$ci_o" ] && verdict PASS "-i -c assesses in -c mode, -c -i in -i mode, -a -t truncates; all exit 0 with no word about the contradiction"
verdict FAIL "rc=$ic_rc/$ci_rc/$at_rc diag=$diag"
