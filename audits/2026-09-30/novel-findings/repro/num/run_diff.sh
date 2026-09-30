#!/bin/bash
W=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/work/num
BIN=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/rel/bin
for b in gcc_nocontract clang_native clang_fast clang_sse2_nocontract gcc_O0; do
  for f in $BIN/*.bin; do
    bf=$(basename $f .bin)
    [ -s $W/runs/${b}_${bf}.res ] && grep -q "Assessed" $W/runs/${b}_${bf}.res && continue
    timeout 1200 $W/b/$b/ea_non_iid -vv $f > $W/runs/${b}_${bf}.res 2>&1
  done
done
echo DONE > $W/runs/ALLDONE
