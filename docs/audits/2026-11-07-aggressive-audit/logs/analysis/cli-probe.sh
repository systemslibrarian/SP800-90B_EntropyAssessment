#!/bin/bash
# CLI analysis probes (2026-11-07, component: command-line and build hardening).
# Tiny inputs only (2,000 samples), EA_ALLOW_SHORT_DATASET=1, OMP_NUM_THREADS=2,
# every tool output to a file under logs/; exit statuses recorded by label
# (instrument rule 5: labelled reads). Nothing here is a compliant assessment.
set -u
repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment
aud=$repo/docs/audits/2026-11-07-aggressive-audit
NI=$repo/cpp/ea_non_iid; II=$repo/cpp/ea_iid; RS=$repo/cpp/ea_restart
corp=$aud/corpus; logs=$aud/logs
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
work=$(mktemp -d "${TMPDIR:-/tmp}/cli-probe.XXXXXX") || exit 2

python3 - "$corp" <<'PY'
import random, sys
c = sys.argv[1]
r = random.Random(20261107)
open(f"{c}/cli-rand1-2000.bin","wb").write(bytes(r.randrange(2) for _ in range(2000)))
PY
shasum -a 256 "$corp/cli-rand1-2000.bin" > "$logs/analysis-cli-corpus-sha256.log"
shasum -a 256 "$NI" "$II" "$RS" > "$logs/analysis-cli-binaries-sha256.log"
F=$corp/cli-rand1-2000.bin
: > "$logs/analysis-cli-exitcodes.log"
run() { # run <label> <cmd...>; stdout+stderr to a labelled file; rc to the exitcodes log
  local label=$1; shift
  ( cd "$work" && "$@" ) > "$logs/analysis-cli-$label.log" 2>&1
  echo "$label rc=$?" >> "$logs/analysis-cli-exitcodes.log"
}
# Q1: ea_restart -s is documented "accepted and ignored"; the code refuses values < 5,000,000.
run restart-s-1000        "$RS" -n -s 1000     /nonexistent/x.bin 1 0.5
run restart-s-4999999     "$RS" -n -s 4999999  /nonexistent/x.bin 1 0.5
run restart-s-5000000     "$RS" -n -s 5000000  /nonexistent/x.bin 1 0.5
run restart-s-6000000     "$RS" -n -s 6000000  /nonexistent/x.bin 1 0.5
run restart-s-0           "$RS" -n -s 0        /nonexistent/x.bin 1 0.5
# Q2: OC-104 refusal fires on a line that already carries "--" before the operand
run dashdash-then-late-q  "$NI" -i -- /nonexistent/x.bin 1 -q
run dashdash-control      "$NI" -i -q -- /nonexistent/x.bin 1
# Q3: negative number after the operand is a value, not an option (both tools)
run negative-bits         "$NI" /nonexistent/x.bin -1
run restart-negative-HI   "$RS" -n /nonexistent/x.bin 1 -0.5
run restart-neg-inf-HI    "$RS" -n /nonexistent/x.bin 1 -inf
# Q4: --version ordering relative to an unknown option
run version-then-Z        "$NI" --version -Z
run Z-then-version        "$NI" -Z --version
run version-alone-iid     "$II" --version
# Q5: repeated -o: both targets claimed, only the last receives the report
rm -f "$work/a.json" "$work/b.json"
run repeated-o            "$NI" -q -o a.json -o b.json "$F" 1
cp "$work/a.json" "$logs/analysis-cli-repeated-o-a.json" 2>/dev/null; cp "$work/b.json" "$logs/analysis-cli-repeated-o-b.json" 2>/dev/null
# Q6: -l malformed shapes
run l-trailing-comma      "$NI" -q -l 5,   "$F"
run l-leading-comma       "$NI" -q -l ,5   "$F"
run l-no-comma            "$NI" -q -l 5    "$F"
run l-zero-count          "$NI" -q -l 0,0  "$F"
run l-index-ulongmax      "$NI" -q -l 18446744073709551615,1 "$F"
run l-count-ulongmax      "$NI" -q -l 0,18446744073709551615 "$F"
# Q7: conflicting mode flags: last one wins, no diagnostic
run i-then-c              "$NI" -v -i -c "$F" 1
run c-then-i              "$NI" -v -c -i "$F" 1
run a-then-t              "$NI" -v -a -t "$F" 1
# Q8: quiet success prints nothing and exits 0 (status-only channel)
run quiet-success         "$NI" -q "$F" 1
# Q9: bits_per_symbol boundaries and shapes
for b in 0 9 1.0 "1 " 01 " 1" 08 256 18446744073709551616; do
  run "bits-[$b]" "$NI" -q "$F" "$b"
done
# Q10: ea_restart -q still prints the H_I line? (needs a 1e6 input; NOT RUN here -- heavy). Source-confirmed only.
# Q11: an unknown long option before the operand
run long-unknown          "$NI" --help "$F" 1
run long-unknown2         "$NI" --versionX "$F" 1
# Q12: "-" alone as the operand
run dash-operand          "$NI" -q - 1
rm -rf "$work"
echo done
