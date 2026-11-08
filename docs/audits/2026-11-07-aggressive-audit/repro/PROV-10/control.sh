#!/bin/bash
# PROV-10 negative control (HEAVY, same bytes): ea_non_iid -o on the de Bruijn file marks the declined LRS
# estimate (literalEstimateNotRun: true, F05 repair) and its "Overall" element carries the assessed minimum
# (hAssessed). The restart tool shares the estimator but not the reporting.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-10 control.txt
record_bin "$NONIID"
GEN="$repo/audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py"
heavy_guard "ea_non_iid on the 1,000,000-sample de Bruijn file"
DB="$out/db100.bin"
[ -f "$DB" ] || "$PY" "$GEN" 100 11 "$DB" > "$out/c_gen.out" 2>&1 || verdict CONTROL-UNEXPECTED "generator failed"
log "input sha256 $(sha "$DB")  $DB"
run_tool noniid "$out/c_n.out" "$out/c_n.err" "$NONIID" -q -o "$out/c_n.json" "$DB" 8
log "rc=$RC errorLevel=$(jtop "$out/c_n.json" errorLevel) LRS literalEstimateNotRun=$(jcase "$out/c_n.json" "LRS Test" literalEstimateNotRun) lrsRes=$(jcase "$out/c_n.json" "LRS Test" lrsRes) Overall.hAssessed=$(jcase "$out/c_n.json" Overall hAssessed)"
[ "$RC" -eq 0 ] && [ "$(jcase "$out/c_n.json" "LRS Test" literalEstimateNotRun)" = "true" ] && [ "$(jcase "$out/c_n.json" Overall hAssessed)" != "<absent>" ] && verdict CONTROL-OK "ea_non_iid flags the declined LRS estimate and carries the assessed minimum; ea_restart (run.sh) does neither"
verdict CONTROL-UNEXPECTED "rc=$RC flag=$(jcase "$out/c_n.json" "LRS Test" literalEstimateNotRun)"
