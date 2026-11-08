#!/bin/bash
# PROV-17 negative control (two arms):
#   (a) the same line WITHOUT the trailing -q: '--' is honoured and the run assesses (exit 0 under the escape);
#   (b) the same line WITHOUT '--': the refusal is then correctly reasoned (glibc would permute -q into an option).
#       Its stderr is byte-identical to run.sh's, which is what shows the message cannot tell the two cases apart.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-17 control.txt
record_bin "$NONIID"
run_tool dashdash_only "$out/c_dd.out" "$out/c_dd.err" "$NONIID" -i -- "$FIX1" 1
a_rc=$RC; log "  (a) '-i -- file 1': rc=$a_rc  Assessed line present: $(grepc 'H_original' "$out/c_dd.out")"
run_tool no_dashdash_late_q "$out/c_nd.out" "$out/c_nd.err" "$NONIID" -i "$FIX1" 1 -q
b_rc=$RC
if cmp -s "$out/c_nd.err" "$here/out/dd.err"; then same="byte-identical"; else same="different"; fi
log "  (b) '-i file 1 -q' (no --): rc=$b_rc ; stderr vs run.sh's stderr: $same"
[ "$a_rc" -eq 0 ] && [ "$b_rc" -ne 0 ] && verdict CONTROL-OK "'--' is honoured when nothing option-shaped follows the operands (exit 0); the refusal text for the with-'--' and without-'--' lines is $same, so the operator cannot tell a true permutation hazard from a line that already disambiguated"
verdict CONTROL-UNEXPECTED "a_rc=$a_rc b_rc=$b_rc"
