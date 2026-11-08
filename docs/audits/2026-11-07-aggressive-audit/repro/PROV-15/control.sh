#!/bin/bash
# PROV-15 negative control: a binary built from the SAME Makefile BEFORE openssl@4 arrived on this host
# (cpp/ea_conditioning, 2026-10-20) links the pinned openssl@3 -- same recipe, different day, different library:
# the Makefile does not pin, the host state decides.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-15 control.txt
record_bin "$COND"
otool -L "$COND" > "$out/otool_ea_conditioning.txt" 2>&1
lc=$(grep -i libcrypto "$out/otool_ea_conditioning.txt" | awk '{print $1}')
log "ea_conditioning -> $lc"
log "openssl@4 Cellar mtime: $(date -r /opt/homebrew/Cellar/openssl@4 '+%Y-%m-%d %H:%M:%S' 2>&1) ; ea_conditioning mtime: $(date -r "$COND" '+%Y-%m-%d %H:%M:%S')"
case "$lc" in /opt/homebrew/opt/openssl@3/*) verdict CONTROL-OK "the October build from the same Makefile links the pinned openssl@3; the 2026-11-07 builds link openssl@4 because the generic prefix moved under them";; esac
verdict CONTROL-UNEXPECTED "ea_conditioning links $lc"
