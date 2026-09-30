#!/bin/bash
# usage: run.sh rel|asan
B=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/$1/cpp/ea_iid
export ASAN_OPTIONS=detect_leaks=0
for f in $(ls *.bin | sort -t_ -k1,1 -k2,2n); do
  out=$(timeout 120 $B -vvv $f 2>&1); rc=$?
  err=$(echo "$out" | grep -m1 -E "Assertion|ERROR: AddressSanitizer|runtime error|Symbol alphabet|empty|Error" | cut -c1-150)
  chi=$(echo "$out" | grep -m1 "Chi square tests" )
  lrs=$(echo "$out" | grep -m1 "Length of longest")
  perm=$(echo "$out" | grep -m1 "IID permutation tests")
  echo "$f rc=$rc | $chi | $lrs | $perm | $err"
done
