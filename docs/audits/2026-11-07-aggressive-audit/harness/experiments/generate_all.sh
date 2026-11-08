#!/bin/bash
# generate_all.sh -- write every experiment input (X1..X7) deterministically and verify the
# manifest.  Pure Python; runs no tool.  Log: logs/experiments/generate-all.log
set -u
here="$(cd "$(dirname "$0")" && pwd)"
aud="$(cd "$here/../.." && pwd)"
V="${PY:-/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/venv/bin/python}"
mkdir -p "$aud/logs/experiments"
log="$aud/logs/experiments/generate-all.log"
{
  echo "START $(date '+%Y-%m-%dT%H:%M:%S%z')  python=$V"
  for g in x1_f02_pair x2_stuck_lsb_chain x3_multimmc_orphans x4_degenerate x5_c_gate x6_restart_decline x7_boundary; do
    echo "== $g"
    "$V" "$here/$g.py"; echo "rc=$?"
  done
  echo "== check"
  "$V" "$here/x1_f02_pair.py" --check; echo "rc=$?"
  "$V" "$here/x2_stuck_lsb_chain.py" --check; echo "rc=$?"
  "$V" "$here/x3_multimmc_orphans.py" --check; echo "rc=$?"
  "$V" "$here/x4_degenerate.py" --check; echo "rc=$?"
  "$V" "$here/x5_c_gate.py" --check; echo "rc=$?"
  "$V" "$here/x6_restart_decline.py" --check; echo "rc=$?"
  "$V" "$here/x7_boundary.py" --check; echo "rc=$?"
  echo "END $(date '+%Y-%m-%dT%H:%M:%S%z')"
} > "$log" 2>&1
tail -3 "$log"
echo "log: $log"
