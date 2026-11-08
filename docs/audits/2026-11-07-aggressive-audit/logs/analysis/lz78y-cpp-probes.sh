#!/bin/bash
# Analysis-phase probes of the production ea_non_iid at the LZ78Y length boundaries.
# EA_ALLOW_SHORT_DATASET=1 is set: every run here is NON-COMPLIANT by construction (brief rule 5).
set -u
cd "$(dirname "$0")/../.." || exit 2
BIN=/Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
shasum -a 256 "$BIN" > logs/analysis-lz78y-binary.sha256
run() { # file width
  local f=$1 w=$2 log="logs/analysis-lz78y-cpp-${1%.bin}.log"
  "$BIN" -i -v -v "corpus/$f" "$w" > "$log" 2>&1; local rc=$?
  echo "exit=$rc" >> "$log"
  echo "=== $f width $w -> $log (exit $rc) ==="
  grep -n "LZ78Y\|Assessed\|Warning\|H_original\|H_bitstring\|exit=\|Incorrect\|non-compliant\|SHORT" "$log"
}
run lz78y_w8_L18_C1.bin 8
run lz78y_w8_L18_C0.bin 8
run lz78y_w8_L17.bin 8
run lz78y_w1_L19.bin 1
run lz78y_w1_L18.bin 1
