#!/bin/bash
# PROV-12 negative control: the same argv[0] without the stray byte round-trips exactly.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-12 control.txt
record_bin "$NONIID"
log "\$ ( exec -a 'ea_Zq' $NONIID -q -o out/c_u.json $FIX1 1 )"
( exec -a 'ea_Zq' "$NONIID" -q -o "$out/c_u.json" "$FIX1" 1 ) > "$out/c_u.out" 2> "$out/c_u.err"; RC=$?; echo "$RC" > "$out/c_u.out.rc"
tok=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["commandline"].split(" ")[0])' "$out/c_u.json")
log "rc=$RC commandline token 0 = '$tok'"
[ "$RC" -eq 0 ] && [ "$tok" = "ea_Zq" ] && verdict CONTROL-OK "valid ASCII argv[0] round-trips exactly; the lost 'Z' in run.sh is the transcoder's doing"
verdict CONTROL-UNEXPECTED "rc=$RC tok=$tok"
