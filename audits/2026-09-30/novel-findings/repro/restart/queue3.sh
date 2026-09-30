#!/bin/bash
SCR=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad
W=$SCR/audit/work/restart; B=$SCR/audit/rel/cpp
cd $W/data
while [ ! -f queue2.done ]; do sleep 10; done
# sanity-check boundary (H_I = 7.5, tool cutoff expected 22): 22 -> pass, 23 -> fail. Stop after the sanity verdict.
for x in 22 23; do
  echo "### bnd$x" > bnd$x.txt
  timeout 150 stdbuf -oL $B/ea_restart -n -vv bnd$x.bin 8 7.5 >> bnd$x.txt 2>&1; echo "exit=$?" >> bnd$x.txt
done
# thread-count / repeatability of the simulated cutoff (unmodified simulateBound via harness)
for t in 1 2 4; do
  OMP_NUM_THREADS=$t timeout 900 $W/src/simcut 7.5 256 5000000 3 >> simcut.txt 2>&1
  OMP_NUM_THREADS=$t timeout 900 $W/src/simcut 1 2 5000000 3 >> simcut.txt 2>&1
done
# second independent reproduction of the de Bruijn LRS -1 leak, quiet JSON mode
( time timeout 1500 $B/ea_restart -n -q -o db100_r2.json db100.bin 7 5.5 ) > db100_r2.txt 2>&1; echo "exit=$?" >> db100_r2.txt
echo QUEUE3-DONE > queue3.done
