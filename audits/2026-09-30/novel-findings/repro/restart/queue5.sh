#!/bin/bash
SCR=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad
W=$SCR/audit/work/restart; B=$SCR/audit/rel/cpp
cd $W/data
while [ ! -f queue3.done ]; do sleep 10; done
echo "### bnd22 (rerun, timeout 900)" > bnd22b.txt
timeout 900 stdbuf -oL $B/ea_restart -n -vv bnd22.bin 8 7.5 >> bnd22b.txt 2>&1 &
PID=$!
# stop once the sanity verdict is printed (the estimator battery is not needed for this boundary check)
until grep -q "Sanity Check" bnd22b.txt || ! kill -0 $PID 2>/dev/null; do sleep 3; done
sleep 1; kill $PID 2>/dev/null; wait $PID; echo "exit=$? (killed after sanity verdict)" >> bnd22b.txt
echo QUEUE5-DONE > queue5.done
