#!/bin/bash
SCR=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad
W=$SCR/audit/work/restart; B=$SCR/audit/rel/cpp
cd $W/data
# A. second independent reproduction of RESTART-03 (quiet JSON mode)
( time timeout 2400 $B/ea_restart -n -q -o db100_r2.json db100.bin 7 5.5 ) > db100_r2.txt 2>&1; echo "exit=$?" >> db100_r2.txt
# B. sanity boundary X_max == 22 at H_I = 7.5 (stop after the sanity verdict)
echo "### bnd22 (rerun)" > bnd22b.txt
timeout 1200 stdbuf -oL $B/ea_restart -n -vv bnd22.bin 8 7.5 >> bnd22b.txt 2>&1 &
PID=$!
until grep -q "Sanity Check" bnd22b.txt || ! kill -0 $PID 2>/dev/null; do sleep 3; done
sleep 1; kill $PID 2>/dev/null; wait $PID; echo "exit=$? (killed after sanity verdict)" >> bnd22b.txt
# C. thread-count / repeatability of simulateBound (unmodified, via harness)
for t in 1 2 4; do
  OMP_NUM_THREADS=$t timeout 1200 $W/src/simcut 7.5 256 5000000 2 >> simcut.txt 2>&1
  OMP_NUM_THREADS=$t timeout 1200 $W/src/simcut 1 2 5000000 2 >> simcut.txt 2>&1
done
echo QUEUE6-DONE > queue6.done
