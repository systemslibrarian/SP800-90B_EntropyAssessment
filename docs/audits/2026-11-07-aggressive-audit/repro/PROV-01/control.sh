#!/bin/bash
# PROV-01 negative control: the SAME option error placed AFTER -o. This is the shape
# cpp/selftest/regression-output.sh tests: the C14 placeholder replaces the stale report.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-01 control.txt
record_bin "$NONIID" "$IID" "$RESTART"
run_tool baseline "$out/c_baseline.out" "$out/c_baseline.err" "$NONIID" -q -o "$out/c_good.json" "$FIX8" 8
[ "$RC" -eq 0 ] || verdict CONTROL-UNEXPECTED "baseline did not exit 0 (rc=$RC)"
GOOD=$(sha "$out/c_good.json"); log "c_good.json sha256 $GOOD errorLevel=$(jtop "$out/c_good.json" errorLevel)"
replaced=0; total=0
ctl() {  # ctl <name> <cmd...>
  local name="$1"; shift
  cp "$out/c_good.json" "$out/c_stale_$name.json"
  run_tool "$name" "$out/c_$name.out" "$out/c_$name.err" "$@"
  local after; after=$(sha "$out/c_stale_$name.json")
  total=$((total+1))
  if [ "$RC" -ne 0 ] && [ "$after" != "$GOOD" ] && [ "$(jtop "$out/c_stale_$name.json" errorLevel)" = "-1" ]; then
    log "  $name: replaced by the placeholder (errorLevel -1, reportComplete $(jtop "$out/c_stale_$name.json" reportComplete)), rc=$RC"
    replaced=$((replaced+1))
  else
    log "  $name: UNEXPECTED (rc=$RC, sha after=$after, errorLevel $(jtop "$out/c_stale_$name.json" errorLevel))"
  fi
}
ctl noniid_Z  "$NONIID"  -o "$out/c_stale_noniid_Z.json" -Z "$FIX8" 8
ctl iid_Z     "$IID"     -o "$out/c_stale_iid_Z.json" -Z "$FIX8" 8
ctl restart_Z "$RESTART" -o "$out/c_stale_restart_Z.json" -Z "$FIX8" 8 3/symbol
log "placeholder replacements: $replaced of $total"
[ "$replaced" -eq "$total" ] && verdict CONTROL-OK "with -o parsed FIRST the same -Z error replaces the stale report with the fail-closed placeholder (the only ordering regression-output.sh tests)"
verdict CONTROL-UNEXPECTED "a control did not behave as the C14 design says"
