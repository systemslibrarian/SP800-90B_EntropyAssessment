#!/bin/bash
# PROV-10 (HEAVY: 1,000,000-sample ea_restart -n run, several minutes): the restart JSON has NO field for
#          min(H_r, H_c, H_I) -- "Overall" carries h_r, h_c, h_i only -- and a declined estimator (LRS, 6.3.6 step 2
#          "v < u") is silently omitted: restart_main.cpp sets literal_not_run at ZERO sites.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-10 observed.txt
record_bin "$RESTART"
log "grep -c not_run cpp/restart_main.cpp = $(grep -c not_run "$repo/cpp/restart_main.cpp" || true) ; cpp/non_iid_main.cpp = $(grep -c not_run "$repo/cpp/non_iid_main.cpp")"
GEN="$repo/audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py"
[ -f "$GEN" ] || verdict FAIL "generator missing: $GEN"
heavy_guard "ea_restart -n on a 1,000,000-sample 8-bit de Bruijn B(100,3) matrix (ten estimators on rows and columns)"
DB="$out/db100.bin"
"$PY" "$GEN" 100 11 "$DB" > "$out/gen.out" 2>&1 || verdict FAIL "generator failed: $(cat "$out/gen.out")"
log "input sha256 $(sha "$DB")  $DB ($(cat "$out/gen.out"))"
run_tool restart_n "$out/r.out" "$out/r.err" "$RESTART" -n -q -o "$out/r.json" "$DB" 8 0.5/symbol
log "rc=$RC errorLevel=$(jtop "$out/r.json" errorLevel) passedRestartSanityCheck=$(jtop "$out/r.json" passedRestartSanityCheck)"
log "Overall: h_r=$(jcase "$out/r.json" Overall h_r) h_c=$(jcase "$out/r.json" Overall h_c) h_i=$(jcase "$out/r.json" Overall h_i) hAssessed=$(jcase "$out/r.json" Overall hAssessed) retMinEntropy=$(jcase "$out/r.json" Overall retMinEntropy)"
ok_keys=$("$PY" -c 'import json,sys; c=[x for x in json.load(open(sys.argv[1]))["testCases"] if x["testCaseDesc"]=="Overall"][0]; print(" ".join(sorted(c.keys())))' "$out/r.json")
log "Overall keys: $ok_keys"
log "LRS Test: h_r=$(jcase "$out/r.json" "LRS Test" h_r) h_c=$(jcase "$out/r.json" "LRS Test" h_c) literalEstimateNotRun=$(jcase "$out/r.json" "LRS Test" literalEstimateNotRun) bitstringEstimateNotRun=$(jcase "$out/r.json" "LRS Test" bitstringEstimateNotRun)"
minf=$("$PY" -c 'import json,sys; c=[x for x in json.load(open(sys.argv[1]))["testCases"] if x["testCaseDesc"]=="Overall"][0]; print("%.17g" % min(c["h_r"],c["h_c"],c["h_i"]))' "$out/r.json" 2>/dev/null || echo "<n/a>")
log "min(h_r,h_c,h_i) recomputed by the consumer: $minf (the tool prints this only at verbose > 0, restart_main.cpp:1222; nothing in the JSON holds it)"
nomin=0; [ "$(jcase "$out/r.json" Overall hAssessed)" = "<absent>" ] && nomin=1
silent=0; [ "$(jcase "$out/r.json" "LRS Test" h_r)" = "<absent>" ] && [ "$(jcase "$out/r.json" "LRS Test" literalEstimateNotRun)" = "<absent>" ] && silent=1
[ "$RC" -eq 0 ] && [ "$nomin" -eq 1 ] && [ "$silent" -eq 1 ] && verdict PASS "success report: no field carries min(H_r,H_c,H_I); the LRS row estimate is absent with no not-run flag"
[ "$RC" -eq 0 ] && [ "$nomin" -eq 1 ] && verdict PASS "success report has no field for min(H_r,H_c,H_I) (the not-run half did not reproduce on this input: LRS h_r=$(jcase "$out/r.json" "LRS Test" h_r))"
verdict FAIL "rc=$RC nomin=$nomin silent=$silent"
