#!/bin/bash
# PROV-02 REFUTE probe. Tiny: 10,000-sample fixture, EA_ALLOW_SHORT_DATASET=1, OMP_NUM_THREADS=2.
# Questions it settles, each read from a FILE the tool wrote (rule 17), by LABEL (instrument rule 5):
#  Q1  under -i on the same 8-bit fixture, is Overall.hAssessed per SAMPLE (= min(dws, hOriginal, dws*hBitstring))?
#      If yes, hAssessed carries the same unit (per word_size-bit sample) in BOTH modes, so the key is unit-consistent.
#  Q2  under -c, does the JSON record the mode? (top-level "commandline" -- the reproducer's key-walk never looked there)
#  Q3  under -c, is the per-bit h' present in the JSON? (Overall.hBitstring == text h' to %f precision)
#  Q4  under -c -vvv, does the text label the per-symbol unit? ("H_bitstring Per Symbol = ...")
set -u
repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment
audit=$repo/docs/audits/2026-11-07-aggressive-audit
LOG=$audit/logs/verify/PROV-02-refute.log
D=$audit/logs/verify/PROV-02-refute.d
BIN=$repo/cpp/ea_non_iid
FIX=$repo/bin/rand8_short.bin
PY=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/venv/bin/python
[ -x "$PY" ] || PY="$(command -v python3)"
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
: > "$LOG"
log() { printf '%s\n' "$*" | tee -a "$LOG"; }
sha() { shasum -a 256 "$1" | awk '{print $1}'; }
log "# PROV-02 REFUTE probe  $(date '+%Y-%m-%d %H:%M:%S %z')  host=$(uname -srm)"
log "# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- NON-COMPLIANT short-dataset runs (10,000 samples); test purposes only"
log "# repo=$repo git=$(cd "$repo" && git rev-parse --short HEAD) branch=$(cd "$repo" && git branch --show-current)"
log "binary sha256 $(sha "$BIN")  $BIN  (mtime $(date -r "$BIN" '+%Y-%m-%d %H:%M:%S'))"
log "README.md of PROV-02 names sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f"
log "fixture sha256 $(sha "$FIX")  $FIX  ($(wc -c < "$FIX" | tr -d " ") bytes)"
log "python: $PY"
run() { # run <label> <args...>
  local lab="$1"; shift
  log "\$ $BIN $*"
  "$BIN" "$@" > "$D/$lab.out" 2> "$D/$lab.err"; local rc=$?
  echo "$rc" > "$D/$lab.rc"
  log "rc[$lab]=$rc  stdout=$lab.out stderr=$lab.err  (stderr bytes: $(wc -c < "$D/$lab.err" | tr -d " "))"
}
jcase() { "$PY" - "$1" "$2" "$3" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1])); desc=sys.argv[2]; k=sys.argv[3]
cases=[c for c in (d.get('testCases') or []) if c.get('testCaseDesc')==desc]
if not cases: print("<no-case>"); sys.exit(0)
c=cases[0]; print(json.dumps(c[k]) if k in c else "<absent>")
PYEOF
}
jtop() { "$PY" - "$1" "$2" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1])); k=sys.argv[2]
print(json.dumps(d[k]) if k in d else "<absent>")
PYEOF
}

log ""
log "## Q1: -i on the same 8-bit fixture -- what unit does Overall.hAssessed carry there?"
run i8 -i -o "$D/i8.json" "$FIX" 8
i_hA=$(jcase "$D/i8.json" Overall hAssessed); i_hO=$(jcase "$D/i8.json" Overall hOriginal)
i_hB=$(jcase "$D/i8.json" Overall hBitstring); i_dws=$(jcase "$D/i8.json" Overall dataWordSize)
log "JSON(-i) Overall: hAssessed=$i_hA hOriginal=$i_hO hBitstring=$i_hB dataWordSize=$i_dws"
log "text(-i) lines:"; grep "^H_original: \|^H_bitstring: \|^min(H_original, " "$D/i8.out" | while IFS= read -r l; do log "    $l"; done
q1=$("$PY" - "$i_hA" "$i_hO" "$i_hB" "$i_dws" <<'PYEOF'
import sys
hA,hO,hB,dws=map(float,sys.argv[1:5])
recon=min(dws,hO,dws*hB)
print("recomputed min(dws, hOriginal, dws*hBitstring) = %.17g ; equals hAssessed bit-for-bit: %s ; hAssessed/dws (per bit) = %.17g" % (recon, recon==hA, hA/dws))
print("Q1: hAssessed under -i is PER SAMPLE (bounded by dws=%g, formed as dws*hBitstring when the bitstring binds): %s" % (dws, "YES" if recon==hA and hA>1.0 else "NO"))
PYEOF
)
log "$q1"

log ""
log "## Q2/Q3: -c on the same fixture -- is the mode recorded, and is the per-bit h' in the JSON?"
run c8 -c -o "$D/c8.json" "$FIX" 8
c_hA=$(jcase "$D/c8.json" Overall hAssessed); c_hB=$(jcase "$D/c8.json" Overall hBitstring)
c_dws=$(jcase "$D/c8.json" Overall dataWordSize); c_hO=$(jcase "$D/c8.json" Overall hOriginal)
c_cmd=$(jtop "$D/c8.json" commandline)
hp=$(grep "^h': " "$D/c8.out" | sed "s/^h': //")
log "JSON(-c) Overall: hAssessed=$c_hA hBitstring=$c_hB dataWordSize=$c_dws hOriginal=$c_hO"
log "JSON(-c) top-level commandline = $c_cmd"
log "text(-c) h' line value: $hp"
q23=$("$PY" - "$c_hA" "$c_hB" "$c_dws" "$hp" "$c_cmd" "$i_hA" "$i_dws" <<'PYEOF'
import sys,json
hA,hB,dws,hp=map(float,sys.argv[1:5]); cmd=json.loads(sys.argv[5]); i_hA=float(sys.argv[6]); i_dws=float(sys.argv[7])
toks=cmd.split()
print("Q2: commandline tokens contain '-c': %s ; contain '-i': %s" % ('-c' in toks, '-i' in toks))
print("Q3: Overall.hBitstring printed with %%f = %.6f ; text h' = %.6f ; equal: %s" % (hB, hp, ("%.6f"%hB)==("%.6f"%hp)))
print("    hAssessed == dws*hBitstring bit-for-bit: %s ; hAssessed/dws = %.17g (per bit, == hBitstring: %s)" % (hA==dws*hB, hA/dws, hA/dws==hB))
print("UNIT COMPARISON: -i hAssessed=%.17g per %g-bit sample ; -c hAssessed=%.17g per %g-bit sample ; both <= dws: %s" % (i_hA, i_dws, hA, dws, i_hA<=i_dws and hA<=dws))
print("    the -i figure divided by dws = %.17g per bit ; the -c figure divided by dws = %.17g per bit" % (i_hA/i_dws, hA/dws))
PYEOF
)
log "$q23"

log ""
log "## Q4: -c -vvv -- does the text label the per-symbol unit?"
run c8v -c -vvv -o "$D/c8v.json" "$FIX" 8
grep "^H_bitstring = \|^H_bitstring Per Symbol = \|^Assessed min entropy: " "$D/c8v.out" | while IFS= read -r l; do log "    $l"; done
log "Q4: a line labelled 'H_bitstring Per Symbol' exists: $(grep -c '^H_bitstring Per Symbol = ' "$D/c8v.out")"

log ""
log "## Control that the probe CAN fail (my-own-probes rule): a 1-bit file, where per-bit == per-sample, must give ratio 1"
FIX1=$repo/bin/rand1_short.bin
log "fixture sha256 $(sha "$FIX1")  $FIX1"
run c1 -c -o "$D/c1.json" "$FIX1" 1
log "JSON(-c,1-bit) Overall: hAssessed=$(jcase "$D/c1.json" Overall hAssessed) hBitstring=$(jcase "$D/c1.json" Overall hBitstring) dataWordSize=$(jcase "$D/c1.json" Overall dataWordSize)"
log ""
log "## Static facts recorded alongside (read from the tree, not measured here)"
log "upstream-identical: git diff upstream/master HEAD -- cpp/non_iid_main.cpp has no hunk touching h_assessed/h'/Per Symbol lines: $(cd "$repo" && git diff upstream/master HEAD -- cpp/non_iid_main.cpp | grep -c "h_assessed\|h':\|Per Symbol\|H_bitstring \* data.word_size") hunks-lines"
log "fork commits touching h_assessed in non_iid_main.cpp (git log -S): $(cd "$repo" && git log --format=%h -S"h_assessed" -- cpp/non_iid_main.cpp | tr '\n' ' ')"
log "default verbosity: $(grep -n 'int verbose = 1' "$repo/cpp/non_iid_main.cpp")"
log "END"
