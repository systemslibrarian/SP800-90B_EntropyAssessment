#!/bin/bash
# run_one.sh -- run ONE tool invocation the way the audit rules require.
#
#   run_one.sh <name> [--short] -- <binary> <args...>
#
# * stdout -> logs/experiments/<name>.stdout, stderr -> <name>.stderr, exit status -> <name>.rc
#   (guide rule 17: the artefact is a file and the consumer reads the file and the producer's status;
#   nothing is piped into head/tail for a verdict);
# * <name>.meta records the command, the start/end time, OMP_NUM_THREADS, whether
#   EA_ALLOW_SHORT_DATASET was set, and the sha256 of the binary and of every argument that is an
#   existing regular file (instrument rule 4: name the binary every measurement ran against);
# * OMP_NUM_THREADS=2 always (brief rule 4); EA_ALLOW_SHORT_DATASET=1 ONLY with --short, which
#   marks the run non-compliant (brief rule 5) -- never use --short on a compliant-size input.
# A <name>.rc of 124 means the optional TIMEOUT (seconds, env) expired.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
aud="$(cd "$here/../.." && pwd)"
logdir="$aud/logs/experiments"
mkdir -p "$logdir"

name="$1"; shift
short=0
if [ "${1:-}" = "--short" ]; then short=1; shift; fi
if [ "${1:-}" = "--" ]; then shift; fi
if [ $# -lt 1 ]; then echo "usage: run_one.sh <name> [--short] -- <binary> <args...>" >&2; exit 2; fi

export OMP_NUM_THREADS=2
if [ $short = 1 ]; then export EA_ALLOW_SHORT_DATASET=1; else unset EA_ALLOW_SHORT_DATASET; fi

meta="$logdir/$name.meta"
{
  echo "name: $name"
  echo "start: $(date '+%Y-%m-%dT%H:%M:%S%z')"
  echo "cwd: $(pwd)"
  echo "host: $(uname -srm)"
  echo "OMP_NUM_THREADS: $OMP_NUM_THREADS"
  echo "EA_ALLOW_SHORT_DATASET: ${EA_ALLOW_SHORT_DATASET:-<unset>}"
  printf 'cmd:'; for a in "$@"; do printf ' %q' "$a"; done; echo
  for a in "$@"; do
    if [ -f "$a" ]; then echo "sha256 $(shasum -a 256 "$a" | awk '{print $1}')  $a  ($(wc -c < "$a" | tr -d ' ') bytes)"; fi
  done
} > "$meta"

if [ -n "${TIMEOUT:-}" ] && command -v timeout >/dev/null 2>&1; then
  timeout "$TIMEOUT" "$@" > "$logdir/$name.stdout" 2> "$logdir/$name.stderr"
  rc=$?
else
  "$@" > "$logdir/$name.stdout" 2> "$logdir/$name.stderr"
  rc=$?
fi
echo "$rc" > "$logdir/$name.rc"
{
  echo "end: $(date '+%Y-%m-%dT%H:%M:%S%z')"
  echo "rc: $rc"
  for a in "$@"; do
    case "$a" in *.json) if [ -f "$a" ]; then echo "report sha256 $(shasum -a 256 "$a" | awk '{print $1}')  $a"; else echo "report MISSING  $a"; fi;; esac
  done
} >> "$meta"
echo "$name: rc=$rc  ($logdir/$name.{stdout,stderr,rc,meta})"
exit 0
