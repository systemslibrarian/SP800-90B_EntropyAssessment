#!/bin/bash
# PROV-15 REFUTE-lens verification probe. Tiny: one 10,000-byte fixture run, two preprocessor-only
# header-resolution checks (no compile, no link), filesystem/man-page reads. No build. Nothing in cpp/ is written.
set -u
REPO=/Users/gmcas/repos/SP800-90B_EntropyAssessment
V=$REPO/docs/audits/2026-11-07-aggressive-audit/logs/verify
LOG=$V/PROV-15-refute.log
: > "$LOG"
log(){ printf '%s\n' "$*" >> "$LOG"; }
log "# PROV-15-refute.log  $(date '+%Y-%m-%d %H:%M:%S %z')  host=$(uname -srm)  git=$(cd "$REPO" && git rev-parse --short HEAD) branch=$(cd "$REPO" && git branch --show-current)"
log "# lens: REFUTE. env for the one tool run: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 (NON-COMPLIANT short-dataset run, 10,000 samples)"
log ""
log "## 0. Binary identity (instrument rule 4)"
for b in ea_non_iid ea_iid ea_restart ea_conditioning; do
  log "sha256 $(shasum -a 256 "$REPO/cpp/$b" | awk '{print $1}')  cpp/$b  (mtime $(date -r "$REPO/cpp/$b" '+%Y-%m-%d %H:%M:%S'))"
done
log "README sha256s: 1ad1568c.. ea_non_iid, 22f1319a.. ea_iid, 4d7ba82b.. ea_restart, b7a55528.. ea_conditioning"
log ""
log "## 1. otool -L re-measured now (not from the reproducer's files)"
for b in ea_non_iid ea_iid ea_restart ea_conditioning; do
  otool -L "$REPO/cpp/$b" > "$V/PROV-15-otool-$b.txt" 2>&1
  log "  $b -> $(grep -i libcrypto "$V/PROV-15-otool-$b.txt" | awk '{print $1}')  (rc otool=$?)"
done
log ""
log "## 2. Objection: does the relink change any REPORTED value? The only OpenSSL-dependent output is the input SHA-256 (utils.h:217 EVP_Digest)."
FIX=$REPO/bin/rand8_short.bin
log "fixture: $FIX  size=$(wc -c < "$FIX" | tr -d " ") bytes  shasum=$(shasum -a 256 "$FIX" | awk '{print $1}')"
cd "$REPO"
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
log "\$ EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 cpp/ea_non_iid -i -v -o $V/PROV-15-rand8.json bin/rand8_short.bin 8"
cpp/ea_non_iid -i -v -o "$V/PROV-15-rand8.json" bin/rand8_short.bin 8 > "$V/PROV-15-rand8.stdout" 2> "$V/PROV-15-rand8.stderr"; RC=$?
log "rc=$RC  stdout=PROV-15-rand8.stdout stderr=PROV-15-rand8.stderr json=PROV-15-rand8.json"
log "stdout line matching 'SHA-256': $(grep -c 'SHA-256' "$V/PROV-15-rand8.stdout") match(es)"
grep 'SHA-256' "$V/PROV-15-rand8.stdout" | sed 's/^/  stdout: /' >> "$LOG"
TOOL_STDOUT=$(grep 'SHA-256' "$V/PROV-15-rand8.stdout" | sed -n 's/.*SHA-256 hash \([0-9a-f]*\).*/\1/p')
TOOL_JSON=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("sha256","<absent>")); print(d.get("sha256Scope","<absent>"), file=sys.stderr)' "$V/PROV-15-rand8.json" 2> "$V/PROV-15-rand8.scope.txt")
log "  json sha256 (labelled read of key 'sha256'): $TOOL_JSON   sha256Scope=$(cat "$V/PROV-15-rand8.scope.txt")"
SHASUM=$(shasum -a 256 "$FIX" | awk '{print $1}')
log "  shasum -a 256 of the fixture:                $SHASUM"
if [ -n "$TOOL_STDOUT" ] && [ "$TOOL_STDOUT" = "$SHASUM" ] && [ "$TOOL_JSON" = "$SHASUM" ]; then
  log "  => MATCH: the openssl@4-linked binary's SHA-256 equals shasum (stdout and JSON). No reported value differs by this relink."
else
  log "  => MISMATCH or missing: stdout='$TOOL_STDOUT' json='$TOOL_JSON' shasum='$SHASUM'"
fi
log "  live-comparison control: shasum of a DIFFERENT fixture bin/rand1_short.bin = $(shasum -a 256 "$REPO/bin/rand1_short.bin" | awk '{print $1}')"
if [ "$TOOL_JSON" != "$(shasum -a 256 "$REPO/bin/rand1_short.bin" | awk '{print $1}')" ]; then log "  control: differs from the tool's digest, so the comparison above can fail (rule 7)"; else log "  control: UNEXPECTED equality"; fi
log "  Assessed min entropy line(s): $(grep -c 'min entropy' "$V/PROV-15-rand8.stdout")"
grep -i 'min entropy\|H_original\|H_bitstring' "$V/PROV-15-rand8.stdout" | sed 's/^/  stdout: /' >> "$LOG"
log ""
log "## 3. Objection: is the search-path ORDER really the mechanism? Minimal mutation of the -I order, preprocessor only (clang++ -E on a 2-line file; no compile, no link)."
P=$V/PROV-15-hdr-probe.cpp
printf '#include <openssl/opensslv.h>\nconst char *v = OPENSSL_VERSION_TEXT;\n' > "$P"
clang++ -E -I/opt/homebrew/include -I/opt/homebrew/opt/openssl@3/include "$P" -o "$V/PROV-15-hdr-generic-first.i" 2> "$V/PROV-15-hdr-generic-first.err"; r1=$?
clang++ -E -I/opt/homebrew/opt/openssl@3/include -I/opt/homebrew/include "$P" -o "$V/PROV-15-hdr-pinned-first.i" 2> "$V/PROV-15-hdr-pinned-first.err"; r2=$?
log "  generic first (Makefile:71 order)  rc=$r1  -> $(grep 'const char \*v' "$V/PROV-15-hdr-generic-first.i")   header: $(grep -m1 -o '"/opt/homebrew/[^"]*opensslv.h"' "$V/PROV-15-hdr-generic-first.i")"
log "  pinned first (the swap)            rc=$r2  -> $(grep 'const char \*v' "$V/PROV-15-hdr-pinned-first.i")   header: $(grep -m1 -o '"/opt/homebrew/[^"]*opensslv.h"' "$V/PROV-15-hdr-pinned-first.i")"
log "  link half: what -lcrypto resolves to in each -L directory, in Makefile:72 order:"
ls -la /opt/homebrew/lib/libcrypto.dylib /opt/homebrew/opt/openssl@3/lib/libcrypto.dylib 2>&1 | sed 's/^/    /' >> "$LOG"
man ld 2>/dev/null | col -b > "$V/PROV-15-man-ld.txt"
log "  man ld on -L (verbatim):"
grep -A3 '^ *-L *dir' "$V/PROV-15-man-ld.txt" | sed 's/^/    /' >> "$LOG"
log ""
log "## 4. Objection: was the control (ea_conditioning, built 2026-10-20) built with the same INC/LDFLAGS order?"
log "  commits that changed the INC/LDFLAGS lines: $(cd "$REPO" && git log --format='%h %ad' --date=short -S'LDFLAGS += -L$(BREW_PREFIX)/lib -L$(OPENSSL_PREFIX)/lib' -- cpp/Makefile | tr '\n' ';')"
log "  Makefile commits since 2026-10-19: $(cd "$REPO" && git log --since=2026-10-19 --format='%h %ad' --date=short -- cpp/Makefile | tr '\n' ';')"
log "  b53ff5d Makefile diff lines touching INC/LDFLAGS/OPENSSL: $(cd "$REPO" && git show b53ff5d -- cpp/Makefile | grep -c '^[-+].*\(INC +=\|LDFLAGS +=\|OPENSSL_PREFIX\)')"
log ""
log "## 5. Homebrew facts (local filesystem only)"
log "  openssl@3.rb keg_only lines: $(grep -c -i 'keg_only' /opt/homebrew/Cellar/openssl@3/3.6.4/.brew/openssl@3.rb)   openssl@4.rb keg_only lines: $(grep -c -i 'keg_only' /opt/homebrew/Cellar/openssl@4/4.1.0/.brew/openssl@4.rb)"
log "  /opt/homebrew/var/homebrew/linked entries matching ssl: $(ls /opt/homebrew/var/homebrew/linked/ | grep -i ssl | tr '\n' ' ')"
log "  openssl@4 receipt: installed_on_request=$(python3 -c 'import json;print(json.load(open("/opt/homebrew/Cellar/openssl@4/4.1.0/INSTALL_RECEIPT.json"))["installed_on_request"])') time=$(python3 -c 'import json,datetime;print(datetime.datetime.fromtimestamp(json.load(open("/opt/homebrew/Cellar/openssl@4/4.1.0/INSTALL_RECEIPT.json"))["time"]).isoformat())')"
log "  afl++ receipt lists openssl@4 as runtime dependency: $(python3 -c 'import json;d=json.load(open("/opt/homebrew/Cellar/afl++/5.03c/INSTALL_RECEIPT.json"));print(any(x.get("full_name")=="openssl@4" for x in d.get("runtime_dependencies",[])))')"
log ""
log "## 6. Is the earlier (pre-audit) binary's libcrypto recorded anywhere? (bears on the 'explains b61cf8c7 -> 1ad1568c, CERTAIN' sub-claim)"
log "  files mentioning b61cf8c7 in the repo tree: $(cd "$REPO" && grep -rl 'b61cf8c7' --include='*.md' --include='*.txt' --include='*.log' --include='*.json' . 2>/dev/null | grep -v '^./.git/' | tr '\n' ' ')"
log "  lines that name b61cf8c7 together with a libcrypto path (an otool record of that binary) outside this verify dir: $(cd "$REPO" && grep -rn 'b61cf8c7' . 2>/dev/null | grep -v '^./.git/\|logs/verify/' | grep -c 'libcrypto')  (0 = the pre-audit binary's dependency was never captured)"
log "  otool capture files anywhere under the audit dir naming b61cf8c7: $(cd "$REPO/docs/audits/2026-11-07-aggressive-audit" && grep -rl 'b61cf8c7' logs repro 2>/dev/null | grep -v 'logs/verify/' | grep -c 'otool')"
log ""
log "# end"
