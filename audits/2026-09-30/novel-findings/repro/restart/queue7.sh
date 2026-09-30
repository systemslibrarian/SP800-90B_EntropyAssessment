#!/bin/bash
W=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/work/restart
A=$W/asanfast/ea_restart_asanfast
cd $W/data
run() { local tag=$1; shift; echo "### $tag: $*" > $tag.txt; ( time timeout 2400 "$@" ) >> $tag.txt 2>&1; echo "exit=$?" >> $tag.txt; }
ASAN_OPTIONS=detect_leaks=0 run asanf_default $A -n -v uni1.bin 1 1
ASAN_OPTIONS=detect_leaks=0:alloc_dealloc_mismatch=0 run asanf_n_uni1 $A -n -vv -o asanf_n_uni1.json uni1.bin 1 1
ASAN_OPTIONS=detect_leaks=0:alloc_dealloc_mismatch=0 run asanf_n_db100 $A -n -vv -o asanf_n_db100.json db100.bin 7 5.5
ASAN_OPTIONS=detect_leaks=0:alloc_dealloc_mismatch=0 run asanf_i_uni1 $A -i -vv -o asanf_i_uni1.json uni1.bin 1 1
echo QUEUE7-DONE > queue7.done
