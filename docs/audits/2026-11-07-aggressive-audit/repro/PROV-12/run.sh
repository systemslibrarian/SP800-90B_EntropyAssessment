#!/bin/bash
# PROV-12: invalid UTF-8 in argv is transcoded lossily into the JSON "commandline": jsoncpp's
#          valueToQuotedString() consumes the ASCII byte FOLLOWING a stray continuation byte as its continuation,
#          so 'ea_' 0x80 'Z' 'q' becomes 'ea_' U+FFFD 'q' -- the 'Z' is gone. ("filename" is argv[optind] verbatim
#          and gets the same treatment on a filesystem that accepts such names; APFS refuses them, so argv[0] is used.)
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-12 observed.txt
record_bin "$NONIID"
log "fixture sha256 $(sha "$FIX1")  $FIX1"
# bash $'...' with octal escapes builds the raw bytes: \200 = 0x80, \377 = 0xFF, \376 = 0xFE
A1=$'ea_\200Zq'
A2=$'ea_\377\376q'
log "argv[0] bytes (hex): $(printf '%s' "$A1" | xxd -p)   and   $(printf '%s' "$A2" | xxd -p)"
log "\$ ( exec -a <ea_ 80 5a 71> $NONIID -q -o out/u1.json $FIX1 1 )"
( exec -a "$A1" "$NONIID" -q -o "$out/u1.json" "$FIX1" 1 ) > "$out/u1.out" 2> "$out/u1.err"; RC=$?; echo "$RC" > "$out/u1.out.rc"
log "rc[argv0-80Zq]=$RC errorLevel=$(jtop "$out/u1.json" errorLevel)"
log "\$ ( exec -a <ea_ ff fe 71> $NONIID -q -o out/u2.json $FIX1 1 )"
( exec -a "$A2" "$NONIID" -q -o "$out/u2.json" "$FIX1" 1 ) > "$out/u2.out" 2> "$out/u2.err"; RC2=$?; echo "$RC2" > "$out/u2.out.rc"
log "rc[argv0-fffeq]=$RC2 errorLevel=$(jtop "$out/u2.json" errorLevel)"
log "raw bytes of the commandline token in u1.json: $(grep -o '"commandline" : "[^ ]*' "$out/u1.json" | xxd -p | tr -d '\n')"
res=$("$PY" - "$out/u1.json" "$out/u2.json" <<'PYEOF'
import json,sys
d1=json.load(open(sys.argv[1])); d2=json.load(open(sys.argv[2]))
a1=d1['commandline'].split(' ')[0]; a2=d2['commandline'].split(' ')[0]
print("argv[0] sent  : ea_ 80 'Z' 'q'   -> commandline token 0 = %r  (codepoints %s)" % (a1, " ".join("U+%04X"%ord(c) for c in a1)))
print("argv[0] sent  : ea_ FF FE 'q'    -> commandline token 0 = %r  (codepoints %s)" % (a2, " ".join("U+%04X"%ord(c) for c in a2)))
lostZ = ('Z' not in a1) and a1.startswith('ea_�')
twofffd = a2 == 'ea_��q'
print("'Z' swallowed:", lostZ, "; FF FE -> two U+FFFD:", twofffd)
print("DEFECT" if lostZ else "NODEFECT")
PYEOF
)
log "$res"
printf '%s' "$res" | grep -q '^DEFECT$' && [ "$RC" -eq 0 ] && verdict PASS "a stray 0x80 continuation byte in argv swallows the following ASCII 'Z' in the JSON commandline (valid JSON, exit 0, no diagnostic)"
verdict FAIL "rc=$RC; see the transcoding result above"
