#!/bin/bash
# PROV-11 negative control: drop the operand. The C14 placeholder written at -o parse time DOES carry
# "type": "non-IID" (non_iid_main.cpp:82) / "IID" (iid_main.cpp:79), so the schema has the field and the
# tool knows its own name.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-11 control.txt
record_bin "$NONIID" "$IID"
run_tool placeholder_n "$out/c_p.out" "$out/c_p.err" "$NONIID" -o "$out/c_p.json"
tp=$(jtop "$out/c_p.json" type); log "ea_non_iid placeholder (no operand): rc=$RC errorLevel=$(jtop "$out/c_p.json" errorLevel) type=$tp"
run_tool placeholder_i "$out/c_pi.out" "$out/c_pi.err" "$IID" -o "$out/c_pi.json"
tpi=$(jtop "$out/c_pi.json" type); log "ea_iid placeholder (no operand): rc=$RC errorLevel=$(jtop "$out/c_pi.json" errorLevel) type=$tpi"
[ "$tp" = '"non-IID"' ] && [ "$tpi" = '"IID"' ] && verdict CONTROL-OK "the placeholders name the tool ('non-IID', 'IID'); the completed reports in run.sh say the empty string"
verdict CONTROL-UNEXPECTED "placeholder types: $tp $tpi"
