#!/bin/bash
# PROV-14 negative control: the mktemp form the fix would use. Two calls give two different paths in a
# directory the caller owns; nothing is predictable and nothing collides.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-14 control.txt
t1=$(mktemp "$out/.ea_fs_XXXXXX.c"); t2=$(mktemp "$out/.ea_fs_XXXXXX.c")
log "mktemp twice: '$t1' and '$t2'  (different: $([ "$t1" != "$t2" ] && echo yes || echo no))"
rm -f "$t1" "$t2"
[ "$t1" != "$t2" ] && verdict CONTROL-OK "mktemp yields a fresh, unpredictable path per probe; the Makefile's \$\$ form yields the same literal path every time (run.sh)"
verdict CONTROL-UNEXPECTED "mktemp returned the same path twice"
