#!/bin/bash
# PROV-20 negative control: the unambiguous single flag gives exactly the figure the contradictory pair gave,
# which is what shows the pair was resolved by position, not by any rule the operator was told about.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-20 control.txt
record_bin "$NONIID"
run_tool c_only "$out/c_c.out" "$out/c_c.err" "$NONIID" -c "$FIX8" 8
c_h=$(grep "^h': " "$out/c_c.out" | sed "s/^h': //"); log "  -c alone: rc=$RC h'=$c_h"
ic_h=$(grep "^h': " "$here/out/ic.out" 2>/dev/null | sed "s/^h': //")
log "  run.sh's -i -c gave h'=$ic_h"
[ "$RC" -eq 0 ] && [ -n "$c_h" ] && [ "$c_h" = "$ic_h" ] && verdict CONTROL-OK "-c alone and -i -c print the same h' ($c_h): the earlier -i was silently discarded"
verdict CONTROL-UNEXPECTED "rc=$RC c_h=$c_h ic_h=$ic_h (run run.sh first)"
