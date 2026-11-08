#!/bin/bash
# fuzz_common.sh -- shared paths, helpers and THE TARGET TABLE for the AFL++ phase
# of the 2026-11-07 aggressive audit.  Sourced by build.sh, run.sh and triage.sh;
# not meant to be executed.  One table, three readers, so the argv that was fuzzed
# is the argv that is re-run at triage (one walk of the table, the F04 lesson).
#
# Everything here is bash 3.2 compatible (macOS /bin/bash): no associative arrays,
# no mapfile, no ${var,,}.

FUZZ_HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT_DIR="$(cd "$FUZZ_HARNESS_DIR/../.." && pwd)"
REPO_ROOT="$(cd "$AUDIT_DIR/../../.." && pwd)"
CPP_DIR="$REPO_ROOT/cpp"
# FUZZ_LOGS_DIR_OVERRIDE redirects every log and record (a rehearsal must not leave
# artefacts in the audit's logs/).
LOGS_DIR="${FUZZ_LOGS_DIR_OVERRIDE:-$AUDIT_DIR/logs}"
FUZZ_LOGS_DIR="$LOGS_DIR/fuzz"

# The session scratchpad named in the task.  Everything heavy (binaries, AFL
# output directories, work dirs) lives here, never in the repository.
SCRATCHPAD_DEFAULT="/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad"
FUZZ_DIR_DEFAULT="$SCRATCHPAD_DEFAULT/fuzz"
VENV_PY="$SCRATCHPAD_DEFAULT/venv/bin/python"

TOOLS="ea_non_iid ea_iid ea_restart"
VARIANTS="plain asan"

MINUTES_DEFAULT=30      # per-target cap when $2 is not given
MINUTES_HARD_CAP=120    # the brief: "Cap any fuzzing run at 2 hours"
AFL_RNG_SEED=20261107   # afl-fuzz -s: a fixed fuzzer RNG so a campaign can be replayed

# ---- helpers ---------------------------------------------------------------
sha256_of() { shasum -a 256 "$1" | awk '{print $1}'; }
# File size in bytes without stat(1): GNU coreutils' stat sits first in PATH on this
# host (gnubin), where `stat -f` means file SYSTEM; BSD stat wants -f %z.  wc -c
# reads the same on both.
file_size() { wc -c < "$1" | tr -d ' '; }
now_utc()   { date -u +%Y-%m-%dT%H:%M:%SZ; }
die()       { echo "FATAL: $*" >&2; exit 2; }
note()      { echo "[$(date +%H:%M:%S)] $*"; }
need_cmd()  { command -v "$1" >/dev/null 2>&1 || die "missing command: $1 ($2)"; }

# Run a command with a wall-clock cap.  Prefers GNU timeout (coreutils is in
# PATH on this host: /opt/homebrew/opt/coreutils/libexec/gnubin), falls back to
# gtimeout, then to perl's alarm.  Exit 124 means the cap fired in every case.
run_with_timeout() {
    local secs=$1; shift
    if command -v timeout >/dev/null 2>&1 && timeout --version 2>/dev/null | grep -q GNU; then
        timeout -k 5 "$secs" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout -k 5 "$secs" "$@"
    else
        perl -e 'my $s = shift; $SIG{ALRM} = sub { exit 124 }; alarm $s; exec @ARGV or exit 127' "$secs" "$@"
    fi
}

# The AFL++ coverage-map size an instrumented binary needs.  The afl-compiler-rt
# runtime prints exactly one integer and exits when AFL_DUMP_MAP_SIZE=1 is set,
# before main() runs.  An UNinstrumented binary has no such runtime: it runs main
# with no arguments, prints its usage and exits 255.  So the answer is accepted
# only when the whole stdout is a single integer; anything else prints nothing
# (and tells the caller the AFL runtime is absent).  Never fails under set -e.
afl_map_size_of() {
    local out
    out="$(AFL_DUMP_MAP_SIZE=1 "$1" 2>/dev/null < /dev/null || true)"
    out="$(printf '%s' "$out" | tr -d '[:space:]')"
    case "$out" in ''|*[!0-9]*) printf '' ;; *) printf '%s' "$out" ;; esac
}

# Is another heavy job running?  Prints the matching process lines (empty when
# none).  This is a heuristic over process names and cannot see a heavy job that
# does not match the pattern (rule 18); it is a guard, not a proof.
heavy_jobs_running() {
    ps -axo pid,pcpu,rss,command 2>/dev/null \
      | grep -E 'afl-fuzz|afl-showmap|afl-tmin|diff_driver\.py|/ea_non_iid |/ea_iid |/ea_restart |clang\+\+|afl-clang|afl-cc' \
      | grep -v -E 'grep -E|fuzz_common|run\.sh|triage\.sh|build\.sh' || true
}

# ---- the target table ------------------------------------------------------
# Fields: tool args seeds variant minutes maxlen timeout expect_rc good_seed note
#   tool      ea_non_iid | ea_iid | ea_restart | argv_driver
#   args      argv with @@ where afl-fuzz substitutes the input file
#   seeds     seed sub-directory under <fuzz>/seeds
#   variant   default build variant (plain | asan); run.sh --variant overrides
#   minutes   default per-target fuzz minutes before the $2 cap is applied
#   maxlen    afl-fuzz -G (bytes)
#   timeout   afl-fuzz -t
#   expect_rc exit status the GOOD seed must produce in the pre-flight
#   good_seed the seed used as the accepted baseline
TARGET_IDS="T1 T2 T3 T4 T5 T6 T7 T8"

target_field() {
    local T=$1 f=$2
    local tool args seeds variant minutes maxlen timeout expect_rc good_seed note
    case "$T" in
      T1) tool=ea_non_iid; args="-i -a @@";           seeds=w8;   variant=asan;  minutes=25; maxlen=16384; timeout=2000+; expect_rc=0;   good_seed=w8/rnd-00064.bin
          note="initial estimate, width INFERRED from the data (utils.h:458-470): the OR-of-all-bytes path and the 0..8 alphabet table" ;;
      T2) tool=ea_non_iid; args="-i -a @@ 8";         seeds=w8;   variant=asan;  minutes=20; maxlen=16384; timeout=2000+; expect_rc=0;   good_seed=w8/rnd-00064.bin
          note="declared 8 bits: no refusal possible on width, every byte value legal; the bitstring is 8x the file" ;;
      T3) tool=ea_non_iid; args="-i -a @@ 1";         seeds=w1;   variant=asan;  minutes=20; maxlen=16384; timeout=2000+; expect_rc=0;   good_seed=w1/rnd-00064.bin
          note="declared 1 bit: the binary path (no H_bitstring), plus the 'wider than declared' refusal whenever a byte > 1 appears" ;;
      T4) tool=ea_non_iid; args="-c -a @@ 8";         seeds=w8;   variant=plain; minutes=15; maxlen=16384; timeout=2000+; expect_rc=0;   good_seed=w8/rnd-00064.bin
          note="conditioned (-c) view: bitstring estimators only, h' path (non_iid_main.cpp -c branch)" ;;
      T5) tool=ea_non_iid; args="-l 1,17 -i @@";      seeds=w8;   variant=plain; minutes=15; maxlen=16384; timeout=2000+; expect_rc=0;   good_seed=w8/rnd-00064.bin
          note="subset arithmetic (utils.h:363-405): offset 17, files <= 17 bytes refused past-end, 18..34 bytes load a SHORT block, larger load 17" ;;
      T6) tool=ea_iid;     args="-i -a @@ 4";         seeds=w4;   variant=plain; minutes=20; maxlen=4096;  timeout=5000+; expect_rc=0;   good_seed=w4/rnd-00064.bin
          note="IID battery at declared 4 bits: chi-square, LRS, 10,000-permutation tests (early-terminating on pass; a FAILING input runs all 10,000 -- hence -G 4096 and -t 5000+)" ;;
      T7) tool=argv_driver; args="@@";                seeds=argv; variant=plain; minutes=25; maxlen=1024;  timeout=5000+; expect_rc=0;   good_seed=argv/basic-i-a-8.txt
          note="argv fuzzer: one token per line, optional first line N|I|R picks the tool; placeholders @F @G @E @X @D @O; runs WITHOUT the forkserver (each exec builds a fresh argv)" ;;
      T8) tool=ea_restart; args="-n @@ 8 0.5/symbol"; seeds=w8;   variant=asan;  minutes=10; maxlen=16384; timeout=2000+; expect_rc=255; good_seed=w8/rnd-00064.bin
          note="ea_restart's SEPARATE intake copy read_file (utils.h:549-735) and the post-read checks up to restart_main.cpp:694; the estimators are UNREACHABLE (len != 1,000,000 is refused unconditionally)" ;;
      *) die "unknown target id '$T'" ;;
    esac
    eval "printf '%s\n' \"\$$f\""
}

# Minutes actually granted to a target: min(table default, cap).
target_minutes_capped() {
    local T=$1 cap=$2
    local m; m=$(target_field "$T" minutes)
    if [ "$m" -gt "$cap" ]; then echo "$cap"; else echo "$m"; fi
}

# ASan runtime options.  afl-fuzz insists on abort_on_error=1 and symbolize=0
# when ASAN_OPTIONS is set by the user.  handle_abort=0 keeps an assert() a plain
# SIGABRT so the "Assertion failed" line stays the classifier's signal.
# hard_rss_limit_mb turns a memory blow-up into an ASan abort (a crash record)
# instead of swapping the 16 GB host.
ASAN_OPTIONS_FUZZ="abort_on_error=1:detect_leaks=0:malloc_context_size=0:symbolize=0:allocator_may_return_null=1:detect_odr_violation=0:handle_segv=1:handle_sigbus=1:handle_abort=0:handle_sigfpe=1:handle_sigill=1:quarantine_size_mb=32:hard_rss_limit_mb=3072"
UBSAN_OPTIONS_FUZZ="abort_on_error=1:symbolize=0:print_stacktrace=0"
# Triage wants the opposite: a symbolised report with a stack.
ASAN_OPTIONS_TRIAGE="abort_on_error=1:detect_leaks=0:symbolize=1:allocator_may_return_null=1:handle_abort=0:print_stacktrace=1"
UBSAN_OPTIONS_TRIAGE="abort_on_error=1:symbolize=1:print_stacktrace=1:halt_on_error=1"

# ---- crash classification (used by triage.sh; here so it can be unit-tested) ----
# classify prefix rc -> "CLASS|KEY|DETAIL"
classify() {
    local pre=$1 rc=$2 line kind frame fn loc last
    if [ "$rc" = NA ]; then echo "NA|NA|build not available"; return; fi
    if [ "$rc" = 124 ]; then echo "TIMEOUT|TIMEOUT|cap fired"; return; fi
    # Each test reads the captured LINE, never a pipeline's exit status (which
    # depends on whether the caller set pipefail).
    line="$(grep -h -m1 -E 'ERROR: AddressSanitizer: ' "$pre.err" 2>/dev/null || true)"
    if [ -n "$line" ]; then
        kind="$(printf '%s' "$line" | sed -E 's/.*AddressSanitizer: ([A-Za-z0-9_-]+).*/\1/')"
        frame="$(grep -h -m1 -E '^[[:space:]]*#0 ' "$pre.err" 2>/dev/null | sed -E 's/^[[:space:]]*#0 0x[0-9a-f]+ in //; s/ \(in [^)]*\)//; s/\+0x[0-9a-f]+//' | cut -c1-120)"
        echo "ASAN:$kind|ASAN:$kind@${frame:-?}|$line"; return
    fi
    line="$(grep -h -m1 -E 'runtime error: ' "$pre.err" 2>/dev/null || true)"
    if [ -n "$line" ]; then
        loc="$(printf '%s' "$line" | sed -E 's/: runtime error:.*//' | sed -E 's#.*/##')"
        kind="$(printf '%s' "$line" | sed -E 's/.*runtime error: //' | cut -c1-60)"
        echo "UBSAN:$kind|UBSAN:$kind@$loc|$line"; return
    fi
    line="$( { grep -h -m1 -E 'Assertion failed:|: Assertion `' "$pre.err" 2>/dev/null; grep -h -m1 -E 'Assertion failed:|: Assertion `' "$pre.out" 2>/dev/null; } | head -1 || true)"
    if [ -n "$line" ]; then
        # macOS libc:  Assertion failed: (expr), function F, file FILE, line N.
        fn="$(printf '%s' "$line" | sed -nE 's/.*, function ([^,]+), file .*/\1/p')"
        loc="$(printf '%s' "$line" | sed -nE 's/.*, file ([^,]+), line ([0-9]+).*/\1:\2/p')"
        if [ -z "$loc" ]; then
            # glibc:  prog: FILE:N: FUNCTION: Assertion `expr' failed.
            loc="$(printf '%s' "$line" | sed -nE 's/^(.*: )?([^: ]+:[0-9]+): .*Assertion.*/\2/p' | sed -E 's#.*/##')"
            fn="$(printf '%s' "$line" | sed -nE 's/.*:[0-9]+: ([^:]+): Assertion.*/\1/p')"
        fi
        echo "ASSERT|ASSERT@${fn:-?}@${loc:-?}|$line"; return
    fi
    # 255 is the tools' own refusal status (exit(-1)); 129..254 is 128+signal as the
    # shell and timeout(1) report it (134 SIGABRT, 139 SIGSEGV, 133 SIGTRAP, 132 SIGILL,
    # 138 SIGBUS).  The tools exit only 0, 1 or 255 on their own paths.
    if [ "$rc" != 255 ] && [ "$rc" -ge 128 ] 2>/dev/null; then echo "SIGNAL:$((rc - 128))|SIGNAL:$((rc - 128))|exit $rc, no sanitizer/assert report in stderr"; return; fi
    last="$(tail -1 "$pre.out" 2>/dev/null | cut -c1-80)"
    echo "EXIT:$rc|EXIT:$rc|not reproduced (exit $rc$([ "$rc" = 255 ] && printf ' = the tool'"'"'s refusal status')); last stdout line: '$last'"
}

