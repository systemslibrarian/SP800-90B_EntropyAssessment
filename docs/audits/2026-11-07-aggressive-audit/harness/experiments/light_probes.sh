#!/bin/bash
# light_probes.sh -- the ONLY tool runs of the planning phase: nine runs, each on <= 20,000
# samples with EA_ALLOW_SHORT_DATASET=1 (non-compliant by construction), OMP_NUM_THREADS=2,
# every output to a file under logs/experiments/ (run_one.sh), then check_run.py on each.
#   X3: production binary vs the C++ model where NO saturation occurs (cap 100,000 > 20,000):
#       the model's (C, r) must be printed exactly by the tool, or the model is wrong.
#   X2: direction check of the four chain files at 20,000 samples (indicative only).
set -u
here="$(cd "$(dirname "$0")" && pwd)"
aud="$(cd "$here/../.." && pwd)"
repo="$(cd "$aud/../../.." && pwd)"
V="${PY:-/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/venv/bin/python}"
tool="$repo/cpp/ea_non_iid"
data="$aud/corpus/experiments"
logs="$aud/logs/experiments"
run="$here/run_one.sh"
mkdir -p "$logs"

# X3 (declared 8; the data uses 248 of 256 values so inference gives 8 as well)
"$run" x3-probe-prefix20000        --short -- "$tool" -i -a -v -v -o "$logs/x3-probe-prefix20000.json"        "$data/x3-mmc-orphan-fill-8bit-prefix20000.bin" 8
"$run" x3-probe-scaled-naive       --short -- "$tool" -i -a -v -v -o "$logs/x3-probe-scaled-naive.json"       "$data/x3-mmc-orphan-naive-scaled-cap3000-8bit-20000.bin" 8
"$run" x3-probe-scaled-gadget      --short -- "$tool" -i -a -v -v -o "$logs/x3-probe-scaled-gadget.json"      "$data/x3-mmc-orphan-gadget-scaled-cap3000-8bit-20000.bin" 8
# X2 (width omitted = inferred; packed7 also declared 8)
"$run" x2a-probe-packed7-inferred  --short -- "$tool" -i -a -v -v -o "$logs/x2a-probe-packed7-inferred.json"  "$data/x2a-chain-lag1-p09-packed7-prefix20000.bin"
"$run" x2a-probe-packed7-declared8 --short -- "$tool" -i -a -v -v -o "$logs/x2a-probe-packed7-declared8.json" "$data/x2a-chain-lag1-p09-packed7-prefix20000.bin" 8
"$run" x2a-probe-lsbpad-inferred   --short -- "$tool" -i -a -v -v -o "$logs/x2a-probe-lsbpad-inferred.json"   "$data/x2a-chain-lag1-p09-lsbpad-8bit-prefix20000.bin"
"$run" x2b-probe-packed7-inferred  --short -- "$tool" -i -a -v -v -o "$logs/x2b-probe-packed7-inferred.json"  "$data/x2b-chain-lag20-p09-packed7-prefix20000.bin"
"$run" x2b-probe-packed7-declared8 --short -- "$tool" -i -a -v -v -o "$logs/x2b-probe-packed7-declared8.json" "$data/x2b-chain-lag20-p09-packed7-prefix20000.bin" 8
"$run" x2b-probe-lsbpad-inferred   --short -- "$tool" -i -a -v -v -o "$logs/x2b-probe-lsbpad-inferred.json"   "$data/x2b-chain-lag20-p09-lsbpad-8bit-prefix20000.bin"

echo "---- checks"
for n in x3-probe-prefix20000 x3-probe-scaled-naive x3-probe-scaled-gadget \
         x2a-probe-packed7-inferred x2a-probe-packed7-declared8 x2a-probe-lsbpad-inferred \
         x2b-probe-packed7-inferred x2b-probe-packed7-declared8 x2b-probe-lsbpad-inferred; do
  "$V" "$here/check_run.py" "$n" --json "$logs/$n.json"
done
echo "---- X3: Literal MultiMMC C and r as printed (labelled grep of the stdout files)"
for n in x3-probe-prefix20000 x3-probe-scaled-naive x3-probe-scaled-gadget; do
  echo "$n:"; grep -E "^Literal MultiMMC Prediction Estimate: (C|r|N|min entropy) = " "$logs/$n.stdout"
done
echo "---- X2: the binding bitstring estimator per run"
for n in x2a-probe-packed7-inferred x2a-probe-packed7-declared8 x2a-probe-lsbpad-inferred x2b-probe-packed7-inferred x2b-probe-packed7-declared8 x2b-probe-lsbpad-inferred; do
  echo "$n:"; grep -E "^Bitstring .* Estimate: min entropy = |^Literal .* Estimate: min entropy = |^H_original = |^H_bitstring|^Assessed" "$logs/$n.stdout"
done
