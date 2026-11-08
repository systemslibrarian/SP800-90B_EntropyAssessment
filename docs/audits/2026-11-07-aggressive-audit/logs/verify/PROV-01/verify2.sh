#!/bin/bash
# PROV-01 verifier addendum: the exit-0 orderings (--version before -o) and the A05 alias refusal. Tiny probes, EA_ALLOW_SHORT_DATASET=1 (NON-COMPLIANT), OMP_NUM_THREADS=2.
set -u
repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment
V=$repo/docs/audits/2026-11-07-aggressive-audit/logs/verify/PROV-01
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
OBS=$V/verify2-observed.txt; : > "$OBS"
log(){ printf '%s\n' "$*" >> "$OBS"; }
sha(){ shasum -a 256 "$1" | awk '{print $1}'; }
el(){ python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d.get("errorLevel","<absent>"),d.get("reportComplete","<absent>"))' "$1"; }
log "# verify2-observed.txt $(date '+%Y-%m-%d %H:%M:%S %z') host=$(uname -srm) git=$(git -C $repo rev-parse --short HEAD)"
log "binary sha256 $(sha $repo/cpp/ea_non_iid) cpp/ea_non_iid"
[ -s "$V/good.json" ] || { log "no good.json from verify.sh"; exit 1; }
G=$(sha "$V/good.json"); log "good.json sha256 $G (from verify.sh)"
run(){ local lab=$1; shift; log "\$ $*"; "$@" > "$V/$lab.out" 2> "$V/$lab.err"; RC=$?; echo $RC > "$V/$lab.rc"; log "rc[$lab]=$RC"; }
probe(){ local lab=$1; shift; cp "$V/good.json" "$V/t_$lab.json"; run "$lab" "$@"; local a; a=$(sha "$V/t_$lab.json"); local st; if [ "$a" = "$G" ]; then st=STALE; else st=REPLACED; fi; log "  $lab: file=$st (errorLevel/reportComplete now: $(el $V/t_$lab.json)) rc=$RC"; }
# --version as an option BEFORE -o: the version gate exits 0 before getopt
probe ver1 $repo/cpp/ea_non_iid --version -o "$V/t_ver1.json" $repo/bin/rand8_short.bin 8
log "  ver1 stdout line1: $(sed -n 1p $V/ver1.out)"
# --version AFTER -o: still the pre-getopt gate (scans argv up to the operand)
probe ver2 $repo/cpp/ea_non_iid -o "$V/t_ver2.json" --version $repo/bin/rand8_short.bin 8
log "  ver2 stdout line1: $(sed -n 1p $V/ver2.out)"
# wrong operand count AFTER -o (claim already made)
probe cnt $repo/cpp/ea_non_iid -o "$V/t_cnt.json" $repo/bin/rand8_short.bin 8 9 10
log "DONE"
