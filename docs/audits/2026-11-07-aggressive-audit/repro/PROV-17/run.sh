#!/bin/bash
# PROV-17: the OC-104 option-after-operand refusal fires on a command line that ALREADY carries '--' before the
#          operand, with a reason that is false for this shape (after '--' neither glibc nor BSD permutes) and
#          advice that is already satisfied ("separate the operands with '--'").
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-17 observed.txt
record_bin "$NONIID"
run_tool dashdash_late_q "$out/dd.out" "$out/dd.err" "$NONIID" -i -- "$FIX1" 1 -q
log "stderr (verbatim):"; sed 's/^/  | /' "$out/dd.err" | tee -a "$OBS"
r1=$(grepc 'depends on the C' "$out/dd.err"); r2=$(grepc "separate the" "$out/dd.err"); r3=$(grepc 'Nothing has been written' "$out/dd.err")
log "refusal markers: 'depends on the C library'=$r1 'separate the operands'=$r2 'Nothing has been written'=$r3 ; rc=$RC"
log "code: scanArgs consumes a pre-operand '--' at TestRunUtils.h:$(grep -n 'if (strcmp(a, \"--\") == 0) { s->dashDashAt = i; i++; break; }' "$repo/cpp/shared/TestRunUtils.h" | cut -d: -f1); the late-option loop stops only at a '--' AFTER the first operand (:$(grep -n 'if (strcmp(a, \"--\") == 0) return;' "$repo/cpp/shared/TestRunUtils.h" | cut -d: -f1))"
[ "$RC" -ne 0 ] && [ "$r1" -ge 1 ] && [ "$r2" -ge 1 ] && verdict PASS "'-i -- file 1 -q' is refused with the C-library-dependence reason and told to add a '--' it already has; both libcs would have refused this line on the usage path (argc 3) -- a wrong-reason refusal"
verdict FAIL "rc=$RC r1=$r1 r2=$r2"
