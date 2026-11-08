#!/bin/bash
# PROV-13 negative control: same generator, same L and k, balanced counts (700/650/650) so nbin > k.
# df >= 1, the p-value is a genuine tail probability in (0,1), and the test is really applied.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-13 control.txt
record_bin "$IID"
"$PY" "$here/gen.py" "$out/balanced.bin" 2000 2001 700,650,650 > "$out/c_gen.out"
log "input $(cat "$out/c_gen.out") sha256 $(sha "$out/balanced.bin")"
run_tool iid_vvv "$out/bal.out" "$out/bal.err" "$IID" -vvv -o "$out/bal.json" "$out/balanced.bin" 2
df=$(grep '^Chi square independence: df = ' "$out/bal.out" | sed 's/.*= //')
pv=$(grep '^Chi square independence: P-value = ' "$out/bal.out" | sed 's/.*= //')
grep '^Chi square' "$out/bal.out" | sed 's/^/  | /' | tee -a "$OBS"
ok=$("$PY" -c 'import sys; df=int(sys.argv[1]); pv=float(sys.argv[2]); print("OK" if df >= 1 and 0.0 < pv < 1.0 else "NO")' "$df" "$pv")
log "rc=$RC df=$df pv=$pv -> $ok"
[ "$ok" = "OK" ] && verdict CONTROL-OK "with nbin > k the test is applied: df = $df, P-value = $pv in (0,1); the df = -1 / P = 1 pair in run.sh is the not-applicable case misreported"
verdict CONTROL-UNEXPECTED "df=$df pv=$pv rc=$RC"
