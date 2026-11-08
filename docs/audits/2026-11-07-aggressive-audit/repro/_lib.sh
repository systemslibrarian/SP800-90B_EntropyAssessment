# _lib.sh -- shared helpers for the 2026-11-07 reproducer pack (bash 3.2 compatible).
# Sourced by every run.sh and control.sh in this directory tree. Nothing here
# builds, nothing here runs a binary on more than 20,000 samples unless the
# calling script is explicitly marked HEAVY and EA_REPRO_HEAVY=1 is set.
#
# Conventions (AUDIT-BRIEF.md ground rule 6; audits/BUG-REPAIR-GUIDE.md):
#   instrument rule 4 -- every measurement names the binary sha256 (record_bin)
#   instrument rule 5 -- JSON reads are labelled (jtop/jcase by key and testCaseDesc), never positional
#   rule 17          -- tool output is written to a file and read from the file; the producer's rc is recorded
#   PASS   = the defect IS present (run.sh);  CONTROL-OK = the negative control does NOT show it (control.sh)
repro_init() {   # repro_init <ID> <observed-file-name>
  ID="$1"; OBSNAME="${2:-observed.txt}"
  here="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  audit="$(cd "$here/../.." && pwd)"
  repo="$(cd "$audit/../../.." && pwd)"
  out="$here/out"; mkdir -p "$out"
  OBS="$here/$OBSNAME"; : > "$OBS"
  NONIID="$repo/cpp/ea_non_iid"; IID="$repo/cpp/ea_iid"; RESTART="$repo/cpp/ea_restart"; COND="$repo/cpp/ea_conditioning"
  FIX8="$repo/bin/rand8_short.bin"; FIX4="$repo/bin/rand4_short.bin"; FIX1="$repo/bin/rand1_short.bin"
  PY=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/venv/bin/python
  [ -x "$PY" ] || PY="$(command -v python3)"
  export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2
  log "# $ID $OBSNAME  $(date '+%Y-%m-%d %H:%M:%S %z')  host=$(uname -srm)"
  log "# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated"
  log "# repo=$repo  git=$(cd "$repo" && git rev-parse --short HEAD 2>/dev/null) branch=$(cd "$repo" && git branch --show-current 2>/dev/null)"
}
log() { printf '%s\n' "$*" | tee -a "$OBS"; }
sha() { shasum -a 256 "$1" | awk '{print $1}'; }
record_bin() { local b; for b in "$@"; do log "binary sha256 $(sha "$b")  $b  (mtime $(date -r "$b" '+%Y-%m-%d %H:%M:%S'))"; done; }
# run_tool <label> <stdout-file> <stderr-file> <cmd...>   -> sets RC
run_tool() {
  local label="$1" so="$2" se="$3"; shift 3
  log "\$ $*"
  "$@" > "$so" 2> "$se"; RC=$?
  echo "$RC" > "$so.rc"
  log "rc[$label]=$RC  stdout=$(basename "$so") stderr=$(basename "$se")"
}
jtop() { "$PY" - "$1" "$2" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1])); k=sys.argv[2]
print(json.dumps(d[k]) if k in d else "<absent>")
PYEOF
}
jcase() { "$PY" - "$1" "$2" "$3" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1])); desc=sys.argv[2]; k=sys.argv[3]
cases=[c for c in (d.get('testCases') or []) if c.get('testCaseDesc')==desc]
if not cases: print("<no-case>"); sys.exit(0)
c=cases[0]
print(json.dumps(c[k]) if k in c else "<absent>")
PYEOF
}
jkeys() { "$PY" -c 'import json,sys; print(" ".join(sorted(json.load(open(sys.argv[1])).keys())))' "$1"; }
grepc() { grep -c -- "$1" "$2" 2>/dev/null || true; }
verdict() {  # verdict <PASS|FAIL|CONTROL-OK|CONTROL-UNEXPECTED|NOT-RUN> <message>
  log "RESULT: $1 -- $2"
  mkdir -p "$audit/logs/repro"; cp "$OBS" "$audit/logs/repro/$ID-$(basename "$OBS" .txt).log"
  case "$1" in PASS|CONTROL-OK) exit 0;; NOT-RUN) exit 3;; *) exit 1;; esac
}
heavy_guard() {  # heavy_guard "<why heavy>"
  if [ "${EA_REPRO_HEAVY:-0}" != "1" ]; then
    verdict NOT-RUN "HEAVY: $1. Not run in this phase (brief ground rule 4: a run on >= 200,000 samples is a heavy job). Re-run with EA_REPRO_HEAVY=1 when the heavy-job slot is free."
  fi
  log "# EA_REPRO_HEAVY=1: running the heavy step"
}
