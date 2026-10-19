#!/bin/bash
# OC-29: the joint behaviour of C16 and C23 on the restart sanity gate. Builds
# ea_restart four ways from the SAME source -- neither fix, C16 only, C23 only,
# both -- using the audit-only knobs EA_RESTART_WITHOUT_C16_FIX /
# EA_RESTART_WITHOUT_C23_FIX, then runs three inputs through each:
#   sane      H_I = 7 on a matrix with X_max = 24 (exact cutoff 23, old cutoff 27)
#   underflow H_I = 1e-400 on a matrix with X_max = 20
#   scale     H_I = 0.875 meant per bit (= 7/symbol) given as a bare number
# The pre-C16 parse does not accept '/symbol', so the sane input is written
# '7' for those builds and '7/symbol' for the C16 builds: same intent, the
# only syntax each accepts.
set -u
repo=$(cd "$(dirname "$0")/../../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/c16c23.XXXXXX"); trap 'rm -rf "$work"' EXIT
python3 - "$work" <<'PY'
import random, sys
def mk(X, path):
    r = random.Random(0xC23ACC); d = bytearray(r.getrandbits(8) for _ in range(1000000))
    col = [i*1000+17 for i in range(1000)]
    for i in col:
        if d[i] == 0: d[i] = 1
    for i in col[:X]: d[i] = 0
    open(path, 'wb').write(bytes(d))
mk(24, sys.argv[1] + '/x24.bin'); mk(20, sys.argv[1] + '/x20.bin')
PY
build() { # build <name> <extra CXX flags>
    (cd "$repo/cpp" && make -B CXX="clang++ $2" restart >"$work/build-$1.log" 2>&1 && cp ea_restart "$work/ea_restart.$1") || { echo "build $1 failed"; exit 2; }
}
build neither "-DEA_RESTART_WITHOUT_C16_FIX -DEA_RESTART_WITHOUT_C23_FIX"
build c16only "-DEA_RESTART_WITHOUT_C23_FIX"
build c23only "-DEA_RESTART_WITHOUT_C16_FIX"
build both ""
(cd "$repo/cpp" && make -B restart >/dev/null 2>&1)     # leave the tree's binary as the shipped build
run() { # run <variant> <matrix> <H_I>
    local out rc cut
    out=$(OMP_NUM_THREADS=4 "$work/ea_restart.$1" -v -n "$work/$2" 8 "$3" 2>&1); rc=$?
    cut=$(printf '%s' "$out" | sed -n 's/.*X_cutoff: \([0-9]*\).*/\1/p')
    if printf '%s' "$out" | grep -qE 'must be|must state'; then echo "REFUSED (exit $rc)"
    elif printf '%s' "$out" | grep -q 'Sanity Check Failed'; then echo "REJECTED by sanity check, X_cutoff $cut"
    elif printf '%s' "$out" | grep -q 'Sanity Check Passed'; then echo "ACCEPTED by sanity check, X_cutoff $cut"
    else echo "other (exit $rc): $(printf '%s' "$out" | tail -1)"; fi
}
printf '%-9s | %-42s | %-36s | %s\n' variant "sane: H_I 7, X_max 24 (exact cutoff 23)" "underflow: H_I 1e-400, X_max 20" "scale: 0.875 meant per bit, bare"
printf '%s\n' "----------|--------------------------------------------|--------------------------------------|------------------------------------"
for v in neither c16only c23only both; do
    case $v in neither|c23only) sane=7 ;; *) sane=7/symbol ;; esac
    printf '%-9s | %-42s | %-36s | %s\n' "$v" "$(run $v x24.bin $sane)" "$(run $v x20.bin 1e-400)" "$(run $v x20.bin 0.875)"
done
