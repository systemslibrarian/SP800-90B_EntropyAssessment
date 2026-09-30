#!/bin/bash
# usage: getissue.sh N [N...]
F=/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/gh/all.md
for n in "$@"; do
awk -v n="$n" 'BEGIN{p=0} /^######## #/{ split($2,a,"#"); p=(a[2]==n)?1:0 } /^######## PR REVIEW/{p=0} p' $F
done
