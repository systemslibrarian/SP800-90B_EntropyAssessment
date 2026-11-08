#!/bin/bash
# PROV-21: `--version -Z` prints the version banner and exits 0 although the line carries an unknown option:
#          versionOptionRequested() lets --version win whenever it PRECEDES the unknown option (TestRunUtils.h:321).
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-21 observed.txt
record_bin "$NONIID" "$IID" "$RESTART"
ok=0; total=0
for t in "$NONIID" "$IID" "$RESTART"; do
  n=$(basename "$t"); run_tool "$n" "$out/$n.out" "$out/$n.err" "$t" --version -Z
  banner=$(grep -c -E '^(non_iid|iid|restart) [0-9]+\.[0-9]+' "$out/$n.out" || true); ill=$(grepc 'illegal option' "$out/$n.err"); usage=$(grepc 'Usage is:' "$out/$n.out")
  log "  $n --version -Z: rc=$RC banner-line='$(sed -n 1p "$out/$n.out")' banner=$banner 'illegal option' on stderr=$ill usage-dump=$usage"
  total=$((total+1)); [ "$RC" -eq 0 ] && [ "$banner" -ge 1 ] && [ "$ill" -eq 0 ] && [ "$usage" -eq 0 ] && ok=$((ok+1))
done
log "code: $(sed -n 321,323p "$repo/cpp/shared/TestRunUtils.h" | tr -s ' ' | tr '\n' ' ')"
[ "$ok" -eq "$total" ] && verdict PASS "all three tools exit 0 with a banner on '--version -Z'; the unknown option after --version is never reported"
verdict FAIL "$ok of $total behaved as predicted"
