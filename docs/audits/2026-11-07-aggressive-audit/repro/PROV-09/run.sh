#!/bin/bash
# PROV-09 (HEAVY: 1,000,000-sample ea_restart -i run): the IID-suite failure report from ea_restart carries
#          errorLevel 2 but NO errorClass, unlike ea_iid's identical outcome (errorLevel 2, errorClass "statistical")
#          and unlike every other failure path in restart_main.cpp.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-09 observed.txt
record_bin "$RESTART"
ln=$(grep -n 'IID restart test suite failed; no IID restart entropy estimate was awarded' "$repo/cpp/restart_main.cpp" | cut -d: -f1)
log "code: restart_main.cpp:$ln sets errorLevel = 2 and errorMsg; errorClass assignments in that block (lines 1149-1167): $(sed -n 1149,1167p "$repo/cpp/restart_main.cpp" | grep -c errorClass || true)"
heavy_guard "ea_restart -i on a 1,000,000-sample matrix (chi-square + LRS on rows and columns before the deterministic failure)"
M="$out/checkerboard-1e6.bin"
"$PY" - "$M" <<'PYEOF'
import sys
L=1_000_000; b=bytes(((i + i//1000) & 1) for i in range(L))   # the N-10 checkerboard: rows and columns alternate 0101..., chi-square fails deterministically
open(sys.argv[1],'wb').write(b)
PYEOF
log "input sha256 $(sha "$M")  $M (1,000,000 samples, 1-bit checkerboard)"
run_tool restart_i "$out/cb.out" "$out/cb.err" "$RESTART" -i -q -o "$out/cb.json" "$M" 1 0.5
log "rc=$RC JSON errorLevel=$(jtop "$out/cb.json" errorLevel) errorClass=$(jtop "$out/cb.json" errorClass) errorMessage=$(jtop "$out/cb.json" errorMessage) IID=$(jtop "$out/cb.json" IID) assessmentComplete=$(jtop "$out/cb.json" assessmentComplete)"
[ "$RC" -eq 1 ] && [ "$(jtop "$out/cb.json" errorLevel)" = "2" ] && [ "$(jtop "$out/cb.json" errorClass)" = "<absent>" ] && verdict PASS "restart IID-suite failure: exit 1, errorLevel 2, errorClass ABSENT (ea_iid writes errorClass 'statistical' for the same outcome)"
verdict FAIL "rc=$RC errorLevel=$(jtop "$out/cb.json" errorLevel) errorClass=$(jtop "$out/cb.json" errorClass)"
