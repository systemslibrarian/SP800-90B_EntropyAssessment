#!/bin/bash
SCR=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad
W=$SCR/audit/work/restart; B=$SCR/audit/rel/cpp
cd $W/data
# wait for the de Bruijn run to finish (single heavy process at a time)
while pgrep -f "ea_restart -n -vv -o db100_r1.json" >/dev/null; do sleep 5; done
run() { local tag=$1; shift; echo "### $tag: $*" > $tag.txt; ( time timeout 1500 "$@" ) >> $tag.txt 2>&1; echo "exit=$?" >> $tag.txt; }
run uni1_r   $B/ea_restart -n -vv -o uni1_r.json uni1.bin 1 1
run uni1T_r  $B/ea_restart -n -vv -o uni1T_r.json uni1.T.bin 1 1
run uni1_ni  $B/ea_non_iid -vv uni1.bin 1
run uni1T_ni $B/ea_non_iid -vv uni1.T.bin 1
run shift1_r $B/ea_restart -n -vv -o shift1_r.json shift1.bin 1 0.9
run altcol1_r $B/ea_restart -n -vv -o altcol1_r.json altcol1.bin 1 1
run db100_ni $B/ea_non_iid -vv db100.bin 7
echo QUEUE1-DONE > queue1.done
