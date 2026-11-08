#!/bin/bash
# PROV-19: schema asymmetry -- the C14 placeholder carries "reportComplete": false, but no completed report
#          (success or error) carries "reportComplete" at all. A consumer that requires reportComplete == true
#          rejects every valid report; one that tests != false works by accident of the omission.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-19 observed.txt
record_bin "$NONIID" "$IID"
run_tool success "$out/s.out" "$out/s.err" "$NONIID" -q -o "$out/s.json" "$FIX1" 1
rs=$(jtop "$out/s.json" reportComplete); log "ea_non_iid success: rc=$RC errorLevel=$(jtop "$out/s.json" errorLevel) reportComplete=$rs"
run_tool error "$out/e.out" "$out/e.err" "$NONIID" -q -o "$out/e.json" "$out/does-not-exist.bin" 8
re=$(jtop "$out/e.json" reportComplete); log "ea_non_iid input error: rc=$RC errorLevel=$(jtop "$out/e.json" errorLevel) reportComplete=$re"
run_tool iid "$out/i.out" "$out/i.err" "$IID" -q -o "$out/i.json" "$FIX8" 8
ri=$(jtop "$out/i.json" reportComplete); log "ea_iid statistical failure: rc=$RC errorLevel=$(jtop "$out/i.json" errorLevel) reportComplete=$ri"
log "writers of 'reportComplete' in cpp/: $(grep -rn 'reportComplete' "$repo/cpp" --include='*.cpp' --include='*.h' | sed "s|$repo/||" | cut -d: -f1,2 | tr '\n' ' ')"
[ "$rs" = "<absent>" ] && [ "$re" = "<absent>" ] && [ "$ri" = "<absent>" ] && verdict PASS "no completed report carries reportComplete; only the placeholder does (false)"
verdict FAIL "reportComplete present somewhere: success=$rs error=$re iid=$ri"
