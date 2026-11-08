#!/usr/bin/env bash
# build.sh -- out-of-tree sanitizer builds of ea_non_iid, ea_iid, ea_restart
# (2026-11-07 aggressive audit, sanitizer phase).  HEAVY: six compiles, run serially.
#
# Usage:
#   build.sh [SAN_DIR] [--variant asan_ubsan|tsan|all] [--tool non_iid|iid|restart|all]
#            [--skip-existing]
#
#   SAN_DIR   output root; default = the session scratchpad's san/ directory (below).
#             Binaries land in SAN_DIR/<variant>/ea_<tool>.  NOTHING is written under cpp/:
#             the production binaries cpp/ea_* are hashed before and after and the script
#             exits 3 if any of them changed (brief, ground rule 3).
#
# What it does, in order:
#   1. hashes the three production binaries;
#   2. for each variant x tool runs the EXACT production compile line captured in
#      ../../BUILD-LINES.md, from cpp/, with "-O2" replaced by
#      "-O1 -g -fno-omit-frame-pointer <sanitizer flags>" and an explicit -o into SAN_DIR;
#      -Werror=ignored-optimization-argument is KEPT so a silently dropped flag fails the
#      build; compiler output goes to SAN_DIR/<variant>/ea_<tool>.build.log;
#   3. smoke-runs each binary with --version (the sanitizer runtime must load and the tool
#      must print its version and exit 0);
#   4. probes LeakSanitizer support ON THIS HOST (ASAN_OPTIONS=detect_leaks=1 with --version;
#      an unsupporting runtime prints "detect_leaks is not supported on this platform" and
#      dies).  run.sh reads the answer from the record instead of assuming it;
#   5. re-hashes the production binaries (exit 3 on any change);
#   6. writes SAN_DIR/BUILD-RECORD.txt: labelled key=value lines -- host, compiler, libomp,
#      sanitizer runtime dylibs with sha256, one `binary=` line per build (variant, tool,
#      sha256, bytes, build exit, seconds, smoke exit, exact command), lsan_supported=.
#
# Variants:
#   asan_ubsan  -fsanitize=address,undefined -fno-sanitize-recover=undefined
#               -fsanitize=float-divide-by-zero,implicit-conversion,nullability
#               NOTE: implicit-conversion, nullability and float-divide-by-zero are NOT in
#               the "undefined" group, so -fno-sanitize-recover=undefined leaves them
#               recoverable; whether a run stops at the first of those is decided at run
#               time by UBSAN_OPTIONS halt_on_error (run.sh sets 1, and re-runs with 0 so
#               the rest of the input is still seen).
#   tsan        -fsanitize=thread.  Homebrew libomp is not TSan-instrumented; see
#               tsan-libomp.supp and README.md for what that does to the signal.
#
# Exit: 0 all requested builds and smokes succeeded; 1 a build or smoke failed (record still
# written); 2 usage / guard refusal; 3 a production binary changed (never expected).

set -u

HERE=$(cd "$(dirname "$0")" && pwd)
AUDIT=$(cd "$HERE/../.." && pwd)
REPO=$(cd "$AUDIT/../../.." && pwd)
CPP="$REPO/cpp"
SAN_DEFAULT=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/san

SAN=""
VARIANTS="asan_ubsan tsan"
TOOLS="non_iid iid restart"
SKIP_EXISTING=0

while [ $# -gt 0 ]; do
    case "$1" in
        --variant) shift; [ "$1" = all ] && VARIANTS="asan_ubsan tsan" || VARIANTS="$1" ;;
        --tool) shift; [ "$1" = all ] && TOOLS="non_iid iid restart" || TOOLS="$1" ;;
        --skip-existing) SKIP_EXISTING=1 ;;
        -h|--help) sed -n '2,45p' "$0"; exit 0 ;;
        -*) echo "build.sh: unknown option $1" >&2; exit 2 ;;
        *) if [ -z "$SAN" ]; then SAN=$1; else echo "build.sh: one SAN_DIR only" >&2; exit 2; fi ;;
    esac
    shift
done
[ -z "$SAN" ] && SAN=$SAN_DEFAULT
mkdir -p "$SAN" || { echo "build.sh: cannot create $SAN" >&2; exit 2; }
SAN=$(cd "$SAN" && pwd)

# Guard: the output root must not be inside cpp/ (or be cpp/ itself).
case "$SAN/" in
    "$CPP"/*) echo "build.sh: REFUSING: SAN_DIR $SAN is inside $CPP" >&2; exit 2 ;;
esac
for t in non_iid iid restart; do
    [ -f "$CPP/${t}_main.cpp" ] || { echo "build.sh: $CPP/${t}_main.cpp not found" >&2; exit 2; }
done

sha256_of() { shasum -a 256 "$1" | cut -d' ' -f1; }
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

RECORD="$SAN/BUILD-RECORD.txt"
TMPREC="$RECORD.partial"
: > "$TMPREC"
rec() { printf '%s\n' "$*" >> "$TMPREC"; }

rec "# BUILD-RECORD -- written by build.sh (sha256 $(sha256_of "$0")) at $(now)"
rec "# One labelled key=value line per fact.  Read by key (instrument rule 5), never by position."
rec "host=$(uname -a)"
rec "compiler=$(clang++ --version 2>/dev/null | sed -n 1p)"
rec "compiler_path=$(command -v clang++)"
rec "libomp=$(brew list --versions libomp 2>/dev/null || echo unknown)"
rec "libomp_dylib_sha256=$(sha256_of /opt/homebrew/opt/libomp/lib/libomp.dylib 2>/dev/null || echo unknown)"
rec "cpp_dir=$CPP"
rec "san_dir=$SAN"
rec "git_head=$(cd "$REPO" && git rev-parse HEAD 2>/dev/null) branch=$(cd "$REPO" && git rev-parse --abbrev-ref HEAD 2>/dev/null)"

# 1. production binaries, before.
PROD_BEFORE=""
for t in non_iid iid restart; do
    if [ -f "$CPP/ea_$t" ]; then h=$(sha256_of "$CPP/ea_$t"); else h=absent; fi
    PROD_BEFORE="$PROD_BEFORE $t=$h"
    rec "production_binary=cpp/ea_$t sha256_before=$h"
done

# The exact production line (BUILD-LINES.md), with -O2 replaced.  Kept as one array per
# segment so the record shows the command exactly as executed.
BASE_FLAGS="-std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include"
OPT_SAN="-O1 -g -fno-omit-frame-pointer"
TAIL_FLAGS="-Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include -I/opt/homebrew/opt/openssl@3/include"
LIBS="-L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto"
san_flags() {
    case "$1" in
        asan_ubsan) echo "-fsanitize=address,undefined -fno-sanitize-recover=undefined -fsanitize=float-divide-by-zero,implicit-conversion,nullability" ;;
        tsan) echo "-fsanitize=thread" ;;
        *) echo "build.sh: unknown variant $1" >&2; exit 2 ;;
    esac
}

FAIL=0
for v in $VARIANTS; do
    SFLAGS=$(san_flags "$v")
    mkdir -p "$SAN/$v"
    for t in $TOOLS; do
        out="$SAN/$v/ea_$t"
        blog="$SAN/$v/ea_$t.build.log"
        cmd="clang++ $BASE_FLAGS $OPT_SAN $SFLAGS $TAIL_FLAGS ${t}_main.cpp -o $out $LIBS"
        if [ $SKIP_EXISTING -eq 1 ] && [ -x "$out" ]; then
            echo "[$v/ea_$t] exists, --skip-existing: not rebuilt"
            rec "binary=$out variant=$v tool=$t sha256=$(sha256_of "$out") bytes=$(wc -c < "$out" | tr -d ' ') build_exit=skipped build_seconds=0 smoke_exit=na cmd=\"$cmd\""
            continue
        fi
        echo "[$v/ea_$t] $(now) building ..."
        t0=$(date +%s)
        ( cd "$CPP" && $cmd ) > "$blog" 2>&1
        rc=$?
        t1=$(date +%s)
        warnings=$(grep -c 'warning:' "$blog")
        if [ $rc -ne 0 ] || [ ! -x "$out" ]; then
            echo "[$v/ea_$t] BUILD FAILED (exit $rc), see $blog"
            rec "binary=$out variant=$v tool=$t sha256=absent bytes=0 build_exit=$rc build_seconds=$((t1 - t0)) warnings=$warnings smoke_exit=na cmd=\"$cmd\""
            FAIL=1
            continue
        fi
        # 3. smoke: the runtime must load and the tool must answer --version with exit 0.
        vlog="$SAN/$v/ea_$t.version.log"
        if [ "$v" = asan_ubsan ]; then
            ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 UBSAN_OPTIONS=print_stacktrace=1 "$out" --version > "$vlog" 2>&1
        else
            TSAN_OPTIONS=report_bugs=1:halt_on_error=0 OMP_NUM_THREADS=2 "$out" --version > "$vlog" 2>&1
        fi
        src=$?
        vout=$(tr '\n' ' ' < "$vlog" | cut -c1-120)
        h=$(sha256_of "$out")
        echo "[$v/ea_$t] built in $((t1 - t0)) s, $warnings warning(s); sha256 $h; --version exit $src: $vout"
        [ $src -eq 0 ] || FAIL=1
        rec "binary=$out variant=$v tool=$t sha256=$h bytes=$(wc -c < "$out" | tr -d ' ') build_exit=$rc build_seconds=$((t1 - t0)) warnings=$warnings smoke_exit=$src smoke_output=\"$vout\" cmd=\"$cmd\""
        # runtime dylibs this binary loads (the measurement ran against these too).
        otool -L "$out" 2>/dev/null | grep -o '/[^ ]*libclang_rt[^ ]*' | while read -r dy; do
            if [ -f "$dy" ]; then rec "runtime_dylib=$dy for=$v/ea_$t sha256=$(sha256_of "$dy")"; else rec "runtime_dylib=$dy for=$v/ea_$t sha256=missing"; fi
        done
    done
done

# 4. LeakSanitizer support probe (asan_ubsan only; any built tool will do -- use the first).
LSAN=unprobed
for t in $TOOLS; do
    b="$SAN/asan_ubsan/ea_$t"
    [ -x "$b" ] || continue
    plog="$SAN/asan_ubsan/lsan-probe.log"
    ASAN_OPTIONS=detect_leaks=1:abort_on_error=0 "$b" --version > "$plog" 2>&1
    prc=$?
    if grep -q 'detect_leaks is not supported' "$plog"; then LSAN=no
    elif [ $prc -eq 0 ]; then LSAN=yes
    else LSAN=unknown; fi
    rec "lsan_supported=$LSAN probe_binary=$b probe_exit=$prc probe_log=$plog probe_output=\"$(tr '\n' ' ' < "$plog" | cut -c1-160)\""
    break
done
[ "$LSAN" = unprobed ] && rec "lsan_supported=unprobed reason=no-asan_ubsan-binary-built"
echo "LeakSanitizer on this host: $LSAN"

# 5. production binaries, after.
CHANGED=0
for t in non_iid iid restart; do
    if [ -f "$CPP/ea_$t" ]; then h=$(sha256_of "$CPP/ea_$t"); else h=absent; fi
    case " $PROD_BEFORE " in
        *" $t=$h "*) rec "production_binary=cpp/ea_$t sha256_after=$h unchanged=yes" ;;
        *) rec "production_binary=cpp/ea_$t sha256_after=$h unchanged=NO"; CHANGED=1 ;;
    esac
done

# Any file newly present directly under cpp/ since the start is reported (none expected).
rec "written=$(now)"
mv "$TMPREC" "$RECORD"
echo "record: $RECORD"

if [ $CHANGED -eq 1 ]; then
    echo "build.sh: A PRODUCTION BINARY UNDER cpp/ CHANGED DURING THIS BUILD. This must never happen; read $RECORD." >&2
    exit 3
fi
exit $FAIL
