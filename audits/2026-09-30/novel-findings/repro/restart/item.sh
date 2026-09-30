#!/bin/bash
# print item N from all.md
awk -v n="$1" 'BEGIN{p=0} /^######## #/{ split($2,a,"#"); p=(a[2]==n) } p' /tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/gh/all.md
