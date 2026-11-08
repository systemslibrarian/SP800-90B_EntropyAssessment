#!/bin/bash
# PROV-15: the OpenSSL pin (openssl@3, BUILDING.md) is defeated by include/link ORDER: the generic Homebrew
#          prefix (-I/opt/homebrew/include, -L/opt/homebrew/lib) precedes -I/-L$(OPENSSL_PREFIX), and Homebrew
#          links the unversioned `openssl` formula there -- openssl@4 since 2026-11-07 19:28. The production
#          binaries now load libcrypto.4 from openssl@4 while the documentation and the pin say openssl@3.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-15 observed.txt
record_bin "$NONIID" "$IID" "$RESTART"
pinned="$(brew --prefix openssl@3 2>/dev/null || echo /opt/homebrew/opt/openssl@3)"
log "pinned prefix (brew --prefix openssl@3): $pinned ; pinned lib present: $(ls "$pinned/lib/libcrypto.3.dylib" 2>&1)"
log "Makefile order:"; grep -n 'OPENSSL_PREFIX\|^INC += \|^LDFLAGS += ' "$repo/cpp/Makefile" | sed 's/^/  Makefile:/' | tee -a "$OBS"
log "BUILDING.md pin:"; grep -n 'openssl@3 ' "$repo/BUILDING.md" | sed 's/^/  BUILDING.md:/' | tee -a "$OBS"
log "generic prefix symlinks:"; ls -la /opt/homebrew/include/openssl /opt/homebrew/lib/libcrypto.dylib 2>&1 | sed 's/^/  /' | tee -a "$OBS"
log "openssl@4 install receipt: $(ls -la /opt/homebrew/Cellar/openssl@4/*/INSTALL_RECEIPT.json 2>&1 | awk '{print $6, $7, $8, $9}')"
off=0; total=0
for b in "$NONIID" "$IID" "$RESTART"; do
  n=$(basename "$b"); otool -L "$b" > "$out/otool_$n.txt" 2>&1
  lc=$(grep -i libcrypto "$out/otool_$n.txt" | awk '{print $1}')
  total=$((total+1))
  case "$lc" in "$pinned"/*) log "  $n -> $lc (pinned)";; *) log "  $n -> $lc  (NOT the pinned prefix)"; off=$((off+1));; esac
done
log "production binaries not linked against the pinned openssl@3: $off of $total"
[ "$off" -ge 1 ] && verdict PASS "all three production binaries link /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib: the generic prefix precedes the pinned one on -I and -L, so the pin cannot pin"
verdict FAIL "every production binary links the pinned prefix"
