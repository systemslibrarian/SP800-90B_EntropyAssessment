#!/bin/bash
# PROV-22 negative control: k = 0 and k = 1 (threads 0 and 1) agree with the canonical jump -- the defect needs
# a second iteration of the loop to see the stale accumulators.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-22 control.txt
"$PY" "$here/model.py" 1 > "$out/model1.out" 2>&1; mrc=$?
sed 's/^/  model: /' "$out/model1.out" | tee -a "$OBS"
[ "$mrc" -eq 0 ] && verdict CONTROL-OK "k = 0 and k = 1 equal the canonical jump; only threads >= 2 are affected"
verdict CONTROL-UNEXPECTED "model rc=$mrc"
