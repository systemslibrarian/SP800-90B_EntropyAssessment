#!/bin/bash
# PROV-11: "type" is the empty string in every real ea_non_iid / ea_iid report (never assigned on the success
#          or error paths), while the C14 placeholder writes "non-IID"/"IID" and ea_restart writes "Restart".
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-11 observed.txt
record_bin "$NONIID" "$IID"
run_tool noniid_ok "$out/t_n.out" "$out/t_n.err" "$NONIID" -q -o "$out/t_n.json" "$FIX1" 1
tn=$(jtop "$out/t_n.json" type); log "ea_non_iid success report: rc=$RC errorLevel=$(jtop "$out/t_n.json" errorLevel) type=$tn IID=$(jtop "$out/t_n.json" IID)"
run_tool iid_fail "$out/t_i.out" "$out/t_i.err" "$IID" -q -o "$out/t_i.json" "$FIX8" 8
ti=$(jtop "$out/t_i.json" type); log "ea_iid report (battery outcome rc=$RC): errorLevel=$(jtop "$out/t_i.json" errorLevel) type=$ti assessmentMode=$(jtop "$out/t_i.json" assessmentMode)"
run_tool noniid_err "$out/t_e.out" "$out/t_e.err" "$NONIID" -q -o "$out/t_e.json" "$out/does-not-exist.bin" 8
te=$(jtop "$out/t_e.json" type); log "ea_non_iid error report (missing input): rc=$RC errorLevel=$(jtop "$out/t_e.json" errorLevel) type=$te"
log "assignments of testRun.type in the mains: non_iid_main.cpp=$(grep -c 'testRun.type' "$repo/cpp/non_iid_main.cpp" || true) iid_main.cpp=$(grep -c 'testRun.type' "$repo/cpp/iid_main.cpp" || true) restart_main.cpp(.type =)=$(grep -c '\.type = ' "$repo/cpp/restart_main.cpp" || true)"
[ "$tn" = '""' ] && [ "$ti" = '""' ] && [ "$te" = '""' ] && verdict PASS "type is the empty string in the ea_non_iid success report, the ea_iid report and the ea_non_iid error report"
verdict FAIL "type values: noniid=$tn iid=$ti err=$te"
