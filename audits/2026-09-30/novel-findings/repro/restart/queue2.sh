#!/bin/bash
SCR=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad
W=$SCR/audit/work/restart; A=$SCR/audit/asan/cpp
cd $W/data
while [ ! -f queue1.done ]; do sleep 10; done
run() { local tag=$1; shift; echo "### $tag: $*" > $tag.txt; ( time timeout 1800 "$@" ) >> $tag.txt 2>&1; echo "exit=$?" >> $tag.txt; }
# 1) default ASan options: expect alloc-dealloc-mismatch at restart_main.cpp:160 (known, PR #242)
ASAN_OPTIONS=detect_leaks=0 run asan_default $A/ea_restart -n -v uni1.bin 1 1
# 2) continue past the known mismatch to exercise the rest of the restart path
ASAN_OPTIONS=detect_leaks=0:alloc_dealloc_mismatch=0 run asan_n_uni1 $A/ea_restart -n -vv -o asan_n_uni1.json uni1.bin 1 1
ASAN_OPTIONS=detect_leaks=0:alloc_dealloc_mismatch=0 run asan_i_uni1 $A/ea_restart -i -vv -o asan_i_uni1.json uni1.bin 1 1
echo QUEUE2-DONE > queue2.done
