#!/bin/bash
# build.sh -- AFL++-instrumented, OUT-OF-TREE builds of ea_non_iid, ea_iid and
# ea_restart for the fuzzing phase of the 2026-11-07 aggressive audit.
#
#   usage: build.sh [OUT_DIR] [--variant plain|asan|both] [--force]
#          OUT_DIR defaults to <scratchpad>/fuzz (fuzz_common.sh FUZZ_DIR_DEFAULT)
#
# THIS IS A HEAVY JOB (brief rule 4): six compiles.  It refuses to start while
# another heavy job is visible unless --force is given.  It never writes under
# cpp/ (brief rule 3): every binary goes to OUT_DIR/bin/<variant>/<tool> via -o.
#
# THE COMPILE LINE is BUILD-LINES.md's production line verbatim, run from cpp/,
# with three changes and nothing else:
#   1. clang++  ->  afl-clang-fast++       (AFL++ 5.03c, PCGUARD instrumentation)
#   2. -O2 kept, -g ADDED                  (symbolised frames for triage)
#   3. -o <OUT_DIR>/bin/<variant>/<tool>   (out of tree)
# AFL_DONT_OPTIMIZE=1 stops afl-cc from appending -funroll-loops / -O3 of its own,
# so the optimisation flags are exactly the production ones.  The compile logs
# carry afl-cc's AFL_DEBUG dump of the real clang invocation.
#
# THE COMPILER IS NOT THE PRODUCTION COMPILER.  afl-clang-fast++ wraps Homebrew
# clang 23.1.5 (its instrumentation pass is built against that LLVM); production
# is Apple clang 21.  Same SDK, same libraries (otool -L is recorded), different
# code generator.  A crash found here is a crash of THE SOURCE under Homebrew
# clang; triage.sh re-runs every crash input under the Apple-clang asan_ubsan build
# (harness/sanitizers) and under the production binary, and the record says which
# of the three reproduced it.
#
# VARIANTS
#   plain  afl-clang-fast++ only.  Finds hard crashes (SIGSEGV/SIGBUS/SIGABRT,
#          asserts) and hangs.  Child RSS ~ production (tens of MB on <= 16 KB
#          inputs); afl-fuzz itself ~150 MB.  Exec speed ~ production.
#   asan   AFL_USE_ASAN=1 AFL_USE_UBSAN=1 on top.  Finds silent heap/stack
#          over-reads and UB (trap-on-error, so UB is a SIGILL/SIGTRAP crash; the
#          Apple asan_ubsan build at triage prints the message).  MEMORY: ASan
#          reserves ~16+ TB of VIRTUAL address space for shadow on arm64, which is
#          why afl-fuzz MUST run it with -m none (run.sh does); RESIDENT memory per
#          child on these inputs is ~40-150 MB (shadow pages touched + 32 MB
#          quarantine cap + redzones), 2-3x slower execs.  One ASan fuzz job on this
#          16 GB host stays well under 1 GB RSS; the ban is on running it BESIDE
#          another heavy job (the differential, a sanitizer run), not on the variant.
#          ASAN_OPTIONS hard_rss_limit_mb=3072 (run.sh) turns a runaway allocation
#          into a recorded crash instead of swap.
#
# The record (OUT_DIR/BUILD-RECORD.txt, copied to logs/fuzz-build-record.log) names
# every binary by sha256 (instrument rule 4), the source state (git HEAD, dirty
# files, per-file sha256), the compiler, the exact flags, the linked libraries,
# the AFL map size, and an afl-showmap tuple count on a 64-byte probe that proves
# the instrumentation is live (a fuzzer whose map stays empty finds nothing and
# says nothing -- the instrument must be shown able to see before its silence
# means anything).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fuzz_common.sh"

OUT="$FUZZ_DIR_DEFAULT"
VARIANT_SEL="both"
FORCE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --variant) VARIANT_SEL="$2"; shift 2 ;;
        --variant=*) VARIANT_SEL="${1#--variant=}"; shift ;;
        --force) FORCE=1; shift ;;
        -h|--help) sed -n '2,60p' "$0"; exit 0 ;;
        --*) die "unknown option $1" ;;
        *) OUT="$1"; shift ;;
    esac
done
case "$VARIANT_SEL" in
    plain) VARIANT_LIST="plain" ;;
    asan)  VARIANT_LIST="asan" ;;
    both)  VARIANT_LIST="plain asan" ;;
    *) die "--variant must be plain, asan or both" ;;
esac

# ---- guards ----------------------------------------------------------------
need_cmd afl-clang-fast++ "brew install afl++"
need_cmd afl-showmap "part of afl++"
need_cmd shasum ""
need_cmd otool "Xcode command line tools"
case "$OUT" in
    "$CPP_DIR"*) die "OUT_DIR $OUT is inside cpp/ -- brief rule 3 forbids writing there" ;;
esac
[ -f "$CPP_DIR/non_iid_main.cpp" ] || die "cannot find $CPP_DIR/non_iid_main.cpp"
busy="$(heavy_jobs_running)"
if [ -n "$busy" ] && [ "$FORCE" -ne 1 ]; then
    echo "Another heavy job appears to be running (brief rule 4: one heavy job at a time):" >&2
    echo "$busy" >&2
    die "refusing to build; re-run with --force only if you have checked the slot is free"
fi

mkdir -p "$OUT/bin/plain" "$OUT/bin/asan" "$OUT/dict" "$OUT/build-logs" "$OUT/smoke" "$LOGS_DIR"
REC="$OUT/BUILD-RECORD.txt"
: > "$REC"
rec() { printf '%s\n' "$*" >> "$REC"; }

rec "# BUILD-RECORD -- AFL++ instrumented builds, 2026-11-07 aggressive audit"
rec "date_utc: $(now_utc)"
rec "host: $(uname -a)"
rec "cpu: $(sysctl -n hw.ncpu) logical ($(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || echo '?')P+$(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null || echo '?')E); mem_bytes: $(sysctl -n hw.memsize)"
rec "out_dir: $OUT"
rec "variants: $VARIANT_LIST"
rec ""
rec "## source state"
rec "git_head: $(git -C "$REPO_ROOT" rev-parse HEAD)"
rec "git_branch: $(git -C "$REPO_ROOT" branch --show-current)"
dirty="$(git -C "$REPO_ROOT" status --porcelain -- cpp/ || true)"
if [ -n "$dirty" ]; then rec "git_dirty_cpp: YES"; printf '%s\n' "$dirty" | sed 's/^/  /' >> "$REC"; else rec "git_dirty_cpp: no"; fi
rec "source_sha256 (what was compiled):"
( cd "$CPP_DIR" && shasum -a 256 non_iid_main.cpp iid_main.cpp restart_main.cpp shared/*.h non_iid/*.h iid/*.h ) | sed 's/^/  /' >> "$REC"
rec ""
rec "## compilers"
rec "afl_clang_fast_version:"
afl-clang-fast++ --version 2>&1 | sed 's/^/  /' >> "$REC"
rec "afl_fuzz_version: $(afl-fuzz -h 2>&1 | head -1 | sed 's/\x1b\[[0-9;]*m//g')"
rec "production_compiler (for contrast, NOT used here):"
clang++ --version 2>&1 | sed 's/^/  /' >> "$REC"
rec "production_binaries (for contrast, NOT used here):"
for t in $TOOLS; do
    if [ -f "$CPP_DIR/$t" ]; then rec "  $(sha256_of "$CPP_DIR/$t")  cpp/$t"; else rec "  (absent)  cpp/$t"; fi
done
rec ""
rec "## compile line (BUILD-LINES.md production line; clang++ -> afl-clang-fast++, -g added, -o out of tree)"
rec "  cd cpp && afl-clang-fast++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 -g \\"
rec "    -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include \\"
rec "    -I/opt/homebrew/opt/openssl@3/include <main>.cpp -o <OUT>/bin/<variant>/<tool> \\"
rec "    -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \\"
rec "    -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto"
rec "  env (all variants): AFL_DONT_OPTIMIZE=1 AFL_DEBUG=1 AFL_LLVM_DICT2FILE=<OUT>/dict/auto-<tool>.dict (plain only)"
rec "  env (asan variant): AFL_USE_ASAN=1 AFL_USE_UBSAN=1"
rec ""

# a 64-byte probe for the instrumentation smoke test: bytes in {0,1}, two symbols
PROBE="$OUT/smoke/probe-64-bits.bin"
perl -e 'print map { chr((($_ * 7) + 3) % 2) } 0..63' > "$PROBE"
rec "## smoke probe: $PROBE sha256 $(sha256_of "$PROBE") (64 bytes in {0,1}; EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2)"
rec ""

main_of() { case "$1" in ea_non_iid) echo non_iid_main.cpp ;; ea_iid) echo iid_main.cpp ;; ea_restart) echo restart_main.cpp ;; esac; }
smoke_args() {   # args after the binary for afl-showmap, probe already substituted
    case "$1" in
        ea_non_iid) echo "-i -a $PROBE 1" ;;
        ea_iid)     echo "-i -a $PROBE 1" ;;
        ea_restart) echo "-n $PROBE 1 0.5" ;;   # exits 255 (len != 1,000,000); the map is still written
    esac
}

overall_rc=0
for variant in $VARIANT_LIST; do
    rec "## variant: $variant"
    for tool in $TOOLS; do
        main="$(main_of "$tool")"
        bin="$OUT/bin/$variant/$tool"
        log="$OUT/build-logs/$variant-$tool.log"
        note "compiling $tool ($variant) -> $bin"
        envs=(AFL_DONT_OPTIMIZE=1 AFL_DEBUG=1)
        if [ "$variant" = "asan" ]; then envs+=(AFL_USE_ASAN=1 AFL_USE_UBSAN=1); fi
        if [ "$variant" = "plain" ]; then envs+=("AFL_LLVM_DICT2FILE=$OUT/dict/auto-$tool.dict"); fi
        t0=$(date +%s)
        rc=0
        ( cd "$CPP_DIR" && env "${envs[@]}" afl-clang-fast++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 -g \
              -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include \
              -I/opt/homebrew/opt/openssl@3/include "$main" -o "$bin" \
              -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
              -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto ) > "$log" 2>&1 || rc=$?
        t1=$(date +%s)
        if [ "$rc" -ne 0 ] || [ ! -x "$bin" ]; then
            rec "  $tool: COMPILE FAILED rc=$rc after $((t1 - t0)) s; log $log"
            echo "COMPILE FAILED for $tool ($variant), rc=$rc. Last lines of $log:" >&2
            tail -20 "$log" >&2
            overall_rc=1
            continue
        fi
        sha="$(sha256_of "$bin")"
        size="$(file_size "$bin")"
        mapsize="$(afl_map_size_of "$bin")"
        [ -n "$mapsize" ] || mapsize="? (the AFL_DUMP_MAP_SIZE probe did not return an integer: no AFL runtime in this binary?)"
        rec "  $tool:"
        rec "    binary:   $bin"
        rec "    sha256:   $sha"
        rec "    size:     $size bytes; compile time $((t1 - t0)) s; log $log"
        rec "    dsym:     $([ -d "$bin.dSYM" ] && echo "$bin.dSYM" || echo "(none -- one-step clang usually emits one; symbolisation will fall back to the symbol table)")"
        rec "    afl_map_size: $mapsize"
        rec "    real_cc_line (afl-cc AFL_DEBUG dump, first line):"
        grep -m1 -E "afl-compiler-rt|SanitizerCoverage|fpass-plugin|fsanitize-coverage" "$log" | cut -c1-600 | sed 's/^/      /' >> "$REC" || rec "      (not found in log)"
        rec "    otool -L:"
        otool -L "$bin" | tail -n +2 | sed 's/^/      /' >> "$REC"
        # instrumentation liveness: afl-showmap must record > 0 tuples on the probe
        map="$OUT/smoke/$variant-$tool.map"
        sm_env=(EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 AFL_SKIP_CPUFREQ=1 AFL_NO_AFFINITY=1)
        sm_opts=(-q -t 20000 -o "$map")
        if [ "$variant" = "asan" ]; then sm_env+=("ASAN_OPTIONS=$ASAN_OPTIONS_FUZZ" "UBSAN_OPTIONS=$UBSAN_OPTIONS_FUZZ"); sm_opts+=(-m none); fi
        # shellcheck disable=SC2046
        smrc=0; env "${sm_env[@]}" afl-showmap "${sm_opts[@]}" -- "$bin" $(smoke_args "$tool") > "$OUT/smoke/$variant-$tool.showmap.log" 2>&1 || smrc=$?
        tuples=0; [ -f "$map" ] && tuples="$(grep -c . "$map" || true)"
        rec "    showmap:  rc=$smrc tuples=$tuples (map $map; log $OUT/smoke/$variant-$tool.showmap.log)"
        if [ "$tuples" -eq 0 ]; then
            rec "    INSTRUMENTATION DEAD: zero tuples on the probe -- this binary must not be fuzzed"
            echo "INSTRUMENTATION DEAD for $tool ($variant): zero tuples. See $OUT/smoke/$variant-$tool.showmap.log" >&2
            overall_rc=1
        fi
        note "  sha256 $sha  tuples $tuples  (${rc}, $((t1 - t0)) s)"
    done
    rec ""
done

if [ -d "$OUT/dict" ] && ls "$OUT/dict"/auto-*.dict >/dev/null 2>&1; then
    rec "## auto dictionaries (AFL_LLVM_DICT2FILE, from compared constants; run.sh passes them with -x)"
    for d in "$OUT/dict"/auto-*.dict; do rec "  $(grep -c . "$d" || true) entries  $d"; done
    rec ""
fi
rec "## memory and scheduling notes"
rec "  plain: child RSS ~ production; afl-fuzz ~150 MB.  asan: -m none REQUIRED (ASan shadow is a"
rec "  multi-TB virtual reservation); resident per child ~40-150 MB on <= 16 KB inputs; 2-3x slower."
rec "  Either variant is ONE heavy job.  Never run a fuzzer beside the differential or a sanitizer run."
rec "  These binaries are NOT the production binaries and were built by a DIFFERENT compiler"
rec "  (Homebrew clang 23.1.5 via afl-clang-fast++ vs Apple clang 21).  triage.sh re-runs every"
rec "  crash input under the Apple-clang asan_ubsan build and the production binary before anything"
rec "  is called a finding."
rec "build_result: $([ "$overall_rc" -eq 0 ] && echo OK || echo 'FAILED (see above)')"
cp "$REC" "$LOGS_DIR/fuzz-build-record.log"
note "record: $REC (copy: $LOGS_DIR/fuzz-build-record.log)"
exit "$overall_rc"
