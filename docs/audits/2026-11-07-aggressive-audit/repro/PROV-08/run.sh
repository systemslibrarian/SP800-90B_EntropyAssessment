#!/bin/bash
# PROV-08 (HEAVY: every ea_restart run is exactly 1,000,000 samples; EA_ALLOW_SHORT_DATASET is not consulted there):
#          the H_I printf at restart_main.cpp:735 is unconditional, so -q still prints it.
#          The input is built so the sanity check fails immediately after that line (every row constant), which
#          keeps the CPU cost to the file read + counting (well under a second) while still exercising line 735.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-08 observed.txt
record_bin "$RESTART"
log "code: $(grep -n 'printf("H_I: %f' "$repo/cpp/restart_main.cpp" | sed 's/^/restart_main.cpp:/' | tr '\n' ';')"
heavy_guard "ea_restart requires a 1,000,000-sample matrix (restart_main.cpp:694), no test escape"
M="$out/rows-constant-1e6.bin"
"$PY" - "$M" <<'PYEOF'
import sys
L=1_000_000; b=bytearray(L)
for i in range(L): b[i]=(i//1000)&1      # row r is constant (r & 1): alphabet {0,1}, X_r = 1000 -> sanity check fails at once
open(sys.argv[1],'wb').write(b)
PYEOF
log "input sha256 $(sha "$M")  $M (1,000,000 samples, 1-bit, row r constant = r&1)"
run_tool restart_q "$out/q.out" "$out/q.err" "$RESTART" -n -q -o "$out/q.json" "$M" 1 0.5
log "stdout under -q (verbatim):"; sed 's/^/  | /' "$out/q.out" | tee -a "$OBS"
n=$(grepc '^H_I: ' "$out/q.out")
log "H_I lines under -q: $n ; JSON errorLevel=$(jtop "$out/q.json" errorLevel) errorClass=$(jtop "$out/q.json" errorClass) passedRestartSanityCheck=$(jtop "$out/q.json" passedRestartSanityCheck)"
[ "$n" -ge 1 ] && verdict PASS "-q still prints 'H_I: ...' (restart_main.cpp:735 is not gated on verbose)"
verdict FAIL "no H_I line under -q (rc=$RC)"
