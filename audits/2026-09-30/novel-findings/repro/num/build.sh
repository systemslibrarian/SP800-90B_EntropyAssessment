#!/bin/bash
# usage: build.sh <name> <cxx> <flags...>   builds ea_non_iid, ea_iid, ea_restart into W/b/<name>
W=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/work/num
name=$1; cxx=$2; shift 2
out=$W/b/$name; mkdir -p $out
cd $W/src
LIBS="-lbz2 -lpthread -ldivsufsort -ldivsufsort64 -ljsoncpp -lcrypto"
for t in non_iid iid restart; do
  $cxx -std=c++11 "$@" -I/usr/include/jsoncpp ${t}_main.cpp -o $out/ea_$t $LIBS > $out/build_$t.log 2>&1 || { echo "FAIL $name $t"; tail -5 $out/build_$t.log; }
done
echo "built $name"
