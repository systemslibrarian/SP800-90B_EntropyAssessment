#!/bin/bash
# PROV-19 negative control: the placeholder (drop the operand) DOES carry the key, as false.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-19 control.txt
record_bin "$NONIID"
run_tool placeholder "$out/c_p.out" "$out/c_p.err" "$NONIID" -o "$out/c_p.json"
rp=$(jtop "$out/c_p.json" reportComplete); log "placeholder: rc=$RC errorLevel=$(jtop "$out/c_p.json" errorLevel) reportComplete=$rp"
[ "$rp" = "false" ] && verdict CONTROL-OK "the placeholder writes reportComplete: false; the completed reports in run.sh omit the key instead of writing true"
verdict CONTROL-UNEXPECTED "placeholder reportComplete=$rp"
