#!/bin/bash
# PROV-01: an option error BEFORE -o exits non-zero and leaves the PREVIOUS success report in place (all three tools).
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-01 observed.txt
record_bin "$NONIID" "$IID" "$RESTART"
log "fixture sha256 $(sha "$FIX8")  $FIX8 (10,000 samples, 8-bit)"
# Baseline: a complete errorLevel-0 report (the artefact a stale-success hazard needs).
run_tool baseline "$out/baseline.out" "$out/baseline.err" "$NONIID" -q -o "$out/good.json" "$FIX8" 8
[ "$RC" -eq 0 ] || verdict FAIL "baseline did not exit 0 (rc=$RC); no success artefact to test with"
ncases=$("$PY" -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["testCases"]))' "$out/good.json")
log "good.json errorLevel=$(jtop "$out/good.json" errorLevel) testCases=$ncases"
[ "$(jtop "$out/good.json" errorLevel)" = "0" ] || verdict FAIL "baseline report is not errorLevel 0"
GOOD=$(sha "$out/good.json"); log "good.json sha256 $GOOD"
survived=0; total=0
probe() {  # probe <name> <cmd...>   -- the command names $out/stale_<name>.json as its -o
  local name="$1"; shift
  cp "$out/good.json" "$out/stale_$name.json"
  run_tool "$name" "$out/$name.out" "$out/$name.err" "$@"
  local after; after=$(sha "$out/stale_$name.json")
  total=$((total+1))
  if [ "$RC" -ne 0 ] && [ "$after" = "$GOOD" ]; then
    log "  $name: STALE SUCCESS SURVIVED -- stale_$name.json is byte-identical to good.json (errorLevel $(jtop "$out/stale_$name.json" errorLevel)), tool rc=$RC"
    survived=$((survived+1))
  else
    log "  $name: NOT reproduced (rc=$RC, errorLevel now $(jtop "$out/stale_$name.json" errorLevel), reportComplete $(jtop "$out/stale_$name.json" reportComplete))"
  fi
}
probe noniid_Z  "$NONIID"  -Z -o "$out/stale_noniid_Z.json" "$FIX8" 8
probe noniid_l  "$NONIID"  -l 5x,10 -o "$out/stale_noniid_l.json" "$FIX8" 8
probe iid_Z     "$IID"     -Z -o "$out/stale_iid_Z.json" "$FIX8" 8
probe restart_Z "$RESTART" -Z -o "$out/stale_restart_Z.json" "$FIX8" 8 3/symbol
log "stale-success survivals: $survived of $total probes"
[ "$survived" -eq "$total" ] && verdict PASS "an option error parsed BEFORE -o exits 255 without claiming the target; the previous success report survives byte-identical (ea_non_iid x2, ea_iid, ea_restart)"
verdict FAIL "only $survived of $total probes left the stale report in place"
