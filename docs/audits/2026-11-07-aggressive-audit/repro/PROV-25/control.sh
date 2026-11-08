#!/bin/bash
# PROV-25 negative control: the same claim about iid_main.cpp is TRUE -- the guard exists there.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-25 control.txt
n=$(grep -c 'INT_MAX' "$repo/cpp/iid_main.cpp" || true)
log "grep -n INT_MAX cpp/iid_main.cpp:"; grep -n 'INT_MAX' "$repo/cpp/iid_main.cpp" | cut -c1-140 | sed 's/^/  iid_main.cpp:/' | tee -a "$OBS"
[ "$n" -ge 1 ] && verdict CONTROL-OK "iid_main.cpp carries the INT_MAX refusal the comment describes ($n references); non_iid_main.cpp does not"
verdict CONTROL-UNEXPECTED "iid_main.cpp has no INT_MAX either"
