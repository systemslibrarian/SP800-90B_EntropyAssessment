#!/bin/bash
# PROV-09 negative control (LIGHT): the same outcome from ea_iid -- IID battery fails on the 10,000-sample
# 8-bit fixture -- carries errorLevel 2 AND errorClass "statistical" (iid_main.cpp:535-537).
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-09 control.txt
record_bin "$IID"
log "fixture sha256 $(sha "$FIX8")  $FIX8"
run_tool iid_fail "$out/c_iid.out" "$out/c_iid.err" "$IID" -q -o "$out/c_iid.json" "$FIX8" 8
log "rc=$RC JSON errorLevel=$(jtop "$out/c_iid.json" errorLevel) errorClass=$(jtop "$out/c_iid.json" errorClass) errorMessage=$(jtop "$out/c_iid.json" errorMessage) IID=$(jtop "$out/c_iid.json" IID) assessmentComplete=$(jtop "$out/c_iid.json" assessmentComplete)"
[ "$RC" -eq 1 ] && [ "$(jtop "$out/c_iid.json" errorLevel)" = "2" ] && [ "$(jtop "$out/c_iid.json" errorClass)" = '"statistical"' ] && verdict CONTROL-OK "ea_iid encodes the same statistical rejection as errorLevel 2 + errorClass 'statistical'; the restart path (run.sh) omits the class"
verdict CONTROL-UNEXPECTED "rc=$RC errorLevel=$(jtop "$out/c_iid.json" errorLevel) errorClass=$(jtop "$out/c_iid.json" errorClass)"
