#!/bin/bash
# build_and_test.sh <worktree> <topic> <regression-script-basename>
#
# For one fix branch checked out in <worktree>: (1) copy MASTER's production binaries into the
# worktree's cpp/ (gitignored there) and run the fix's regression script -- it must FAIL (the defect
# is present; rule 7: a check that has only been seen passing is untested); (2) `make all` in the
# worktree so the fixed Makefile/sources produce the fixed binaries in place, run the script again --
# it must PASS; (3) run the full suite in the worktree with --allow-known-platform-deltas -- expect
# "<N+1> passed, 0 failed" where the branch bumped the counts. Every output to a file under
# logs/fixes/<topic>/ (rule 17); binary sha256s recorded (instrument rule 4).
set -u
WT=$1; TOPIC=$2; REG=$3
AUD=$(cd "$(dirname "$0")/../.." && pwd)
MAIN=$(cd "$AUD/../../.." && pwd)
OUT="$AUD/logs/fixes/$TOPIC"; mkdir -p "$OUT"
export OMP_NUM_THREADS=2
say() { printf '%s\n' "$*" | tee -a "$OUT/SUMMARY.txt"; }
: > "$OUT/SUMMARY.txt"
say "fix: $TOPIC  worktree: $WT  branch: $(git -C "$WT" branch --show-current)  commit: $(git -C "$WT" rev-parse --short HEAD)  $(date)"
# 1. master's binaries into the worktree
for t in ea_non_iid ea_iid ea_restart; do cp "$MAIN/cpp/$t" "$WT/cpp/$t"; done
shasum -a 256 "$WT"/cpp/ea_non_iid "$WT"/cpp/ea_iid "$WT"/cpp/ea_restart > "$OUT/binaries-master.sha256"
say "step 1: regression against MASTER's binaries (expect FAIL)"
( cd "$WT/cpp/selftest" && bash "./$REG" ) > "$OUT/1-regression-on-master.log" 2>&1; rc1=$?
say "  rc=$rc1  $( [ $rc1 -ne 0 ] && echo 'FAILED as expected (defect present)' || echo 'UNEXPECTED PASS -- the test cannot see the defect')"
# 2. build the fix
say "step 2: make all in the worktree (fixed sources/Makefile)"
( cd "$WT/cpp" && rm -f ea_non_iid ea_iid ea_restart && make all ) > "$OUT/2-build.log" 2>&1; rcb=$?
say "  build rc=$rcb  warnings=$(grep -c 'warning:' "$OUT/2-build.log")"
shasum -a 256 "$WT"/cpp/ea_non_iid "$WT"/cpp/ea_iid "$WT"/cpp/ea_restart > "$OUT/binaries-fixed.sha256" 2>/dev/null
for t in ea_non_iid ea_iid ea_restart; do otool -L "$WT/cpp/$t" 2>/dev/null | grep -i crypto | sed "s#^#$t: #"; done >> "$OUT/binaries-fixed.sha256"
if [ $rcb -ne 0 ]; then say "  BUILD FAILED -- stopping"; exit 2; fi
say "step 3: regression against the FIXED binaries (expect PASS)"
( cd "$WT/cpp/selftest" && bash "./$REG" ) > "$OUT/3-regression-on-fixed.log" 2>&1; rc3=$?
say "  rc=$rc3  $( [ $rc3 -eq 0 ] && echo 'PASS' || echo 'FAIL -- the fix does not satisfy its own test')"
say "step 4: full suite in the worktree"
( cd "$WT/cpp/selftest" && ./run-all-checks.sh --allow-known-platform-deltas ) > "$OUT/4-run-all-checks.log" 2>&1; rc4=$?
say "  rc=$rc4  $(grep -E '^run-all-checks:' "$OUT/4-run-all-checks.log" | tail -1)"
grep -E '^failed:|FAIL' "$OUT/4-run-all-checks.log" | head -12 >> "$OUT/SUMMARY.txt"
say "done $(date)"
exit 0
