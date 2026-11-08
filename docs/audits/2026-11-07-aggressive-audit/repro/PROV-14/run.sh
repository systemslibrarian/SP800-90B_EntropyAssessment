#!/bin/bash
# PROV-14: cpp/Makefile's two compiler-flag probes write their test translation unit to a FIXED, predictable
#          path: `/tmp/.ea_fs_$$.c` in make syntax is `/tmp/.ea_fs_$.c` after make's $$ -> $ rewrite, and `$.`
#          is not a shell parameter expansion, so every build on the machine uses the literal same file.
#          No make is run here (the project Makefile's probes compile, and the phase forbids compiling); the
#          expansion is shown with sh and by reading the Makefile. Set EA_REPRO_ALLOW_MAKE=1 to also run a
#          two-line scratch makefile whose only recipe is an echo.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-14 observed.txt
MK="$repo/cpp/Makefile"
log "Makefile sha256 $(sha "$MK")"
log "Makefile lines carrying the probe path (grep -n 'ea_fs_\\$\\$\\|ea_wf_\\$\\$'):"
grep -n 'ea_fs_\$\$\|ea_wf_\$\$' "$MK" | cut -c1-160 | sed 's/^/  Makefile:/' | tee -a "$OBS"
nfixed=$(grep -c '/tmp/\.ea_[fw][sf]_\$\$\.c' "$MK" || true)
log "occurrences of the fixed /tmp/.ea_*_\$\$.c path in the Makefile: $nfixed"
log "GNU make, 'Variables in Recipes'/'The shell Function': a double dollar sign '\$\$' is passed to the shell as a single '\$'."
p1=$(sh -c 'printf "%s\n" /tmp/.ea_fs_$.c'); p2=$(sh -c 'printf "%s\n" /tmp/.ea_fs_$.c')
log "what the shell receives and expands, twice: '$p1' and '$p2'  (identical: '\$.' is not a parameter expansion in sh)"
if [ "${EA_REPRO_ALLOW_MAKE:-0}" = "1" ]; then
  cat > "$out/scratch.mk" <<'MKEOF'
X := $(shell printf '%s' /tmp/.ea_fs_$$.c)
all:
	@printf 'shell-function=%s recipe=%s\n' '$(X)' /tmp/.ea_fs_$$.c
MKEOF
  m=$(make -s -f "$out/scratch.mk" 2>&1); log "scratch makefile (echo only): $m"
else
  log "(scratch make step skipped: EA_REPRO_ALLOW_MAKE not set; the cli-build analysis measured shell-expanded=/tmp/.ea_fs_\$.c recipe-expanded=/tmp/.ea_fs_\$.c the same way)"
fi
log "a planted file at that path right now: $(ls -la '/tmp/.ea_fs_$.c' 2>&1)"
[ "$nfixed" -ge 2 ] && [ "$p1" = '/tmp/.ea_fs_$.c' ] && [ "$p1" = "$p2" ] && verdict PASS "both flag probes use the literal path /tmp/.ea_fs_\$.c (and .ea_wf_\$.c): fixed, world-writable directory, predictable; concurrent builds race and a planted file/symlink is compiled by the probe (denial of build; on GCC the sabotage can only ADD -ffloat-store)"
verdict FAIL "nfixed=$nfixed p1=$p1 p2=$p2"
