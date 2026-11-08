#!/usr/bin/env bash
# run.sh -- sanitizer phase runner (2026-11-07 aggressive audit).  See README.md.
#
# Usage:
#   run.sh [--quick] [--stages a,b,c,d,e,tsan] [--all] [--force] [--dry-run]
#          [--san-dir DIR] [--asan-threads N] [--tsan-threads N] [--timeout-scale K]
#          [--no-ubsan-continue] [--tsan-active-wait] [--summarize-only]
#
#   default stages  a,b,c,d,e   (every ASan+UBSan stage; e is the heavy ea_restart stage)
#   --quick         stage a only (the self-test corpus bin/*.bin through ea_non_iid as
#                   cpp/selftest/selftest runs it, plus ea_iid on its three 10,000-sample files)
#   --all           a,b,c,d,e,tsan
#   --force         re-run inputs that already have a complete log (default: skip them)
#   --dry-run       print the plan (one line per run, with the heavy marker and a model
#                   duration estimate) and exit; needs no binaries
#   --summarize-only  only (re)write logs/sanitizers/RESULTS.md from the logs present
#
# Stages (variant asan_ubsan unless stated; OMP_NUM_THREADS=2):
#   a  bin/*.bin   -- the 11 self-test inputs, `-vv`, width INFERRED exactly as
#                     cpp/selftest/selftest does (it passes no width; refdata declares what was
#                     inferred, recorded per run); fixture sha256 checked against
#                     cpp/selftest/fixture-manifest.txt first.  8 of the 11 are >= 1e6 samples.
#   b  corpus/*-50000.bin at the MANIFEST width: `-i -a -vv` and `-c -vv`; identical
#                     (sha256, width, flags) runs are aliased, not repeated; plus a `-l 1,20000`
#                     subset run and a `-o` JSON-report run.
#   c  every other small corpus/*.bin (agent-made edge files): ea_non_iid `-vv` at the width
#                     inferred from the file NAME (table in infer_width) and again with the
#                     width inferred by the tool; ea_iid `-vv` once.
#   d  ea_iid on the distinct 50,000-sample files: `-i -a -v` and `-c -v` (verbose 2 is the
#                     level that enters permutation_tests.h's critical(verboseOutput) and prints
#                     one progress line per round, so the log carries the round count); plus the
#                     generated iid-lag32copy-q030-1bit-50000.bin (full 10,000-round battery,
#                     measured on the production binary at 20,000) and one `-o` JSON run.
#   e  HEAVY: ea_restart on the two generated 1000x1000 matrices (`-n -v`, 1-bit with H_I 0.9
#                     and 8-bit with 7.0/symbol), the 1-bit matrix in `-i` mode (the one path on
#                     which ea_restart has a LIVE parallel region: permutation_tests on 1e6 rows
#                     and 1e6 columns), and one `-o` JSON run.  1,000,000 samples each.
#   tsan  HEAVY: the tsan binaries, OMP_NUM_THREADS=10, three inputs per tool (README.md).
#
# Every run writes ONE file, logs/sanitizers/<variant>/ea_<tool>-<input>.<tag>.log, with a
# `## key: value` header (binary and input sha256, exact command, env, timeout), the tool's
# stdout+stderr verbatim, and a trailer (exit, wall seconds, sanitizer_report yes/no, the
# first report line, tool_outcome).  The verdict is read FROM THE FILE after the producer has
# exited (guide rule 17); nothing is piped into head/tail.  A log without the `## exit:`
# trailer is a killed run and is re-run on resume.
#
# EA_ALLOW_SHORT_DATASET=1 is set ONLY for inputs below 1,000,000 samples and the header says
# so (brief, ground rule 5).  EA_TEST_RANDOM_SOURCE points at the generated 1 MiB file; by
# reading cpp/ it reaches only the -o report's temporary-file name (TestRunUtils.h:129,478):
# the permutation-test seed is /dev/urandom unconditionally (utils.h:794-811), so ea_iid's
# battery is NOT reproducible run to run and no option here changes that.

set -u

HERE=$(cd "$(dirname "$0")" && pwd)
AUDIT=$(cd "$HERE/../.." && pwd)
REPO=$(cd "$AUDIT/../../.." && pwd)
CPP="$REPO/cpp"
CORPUS="$AUDIT/corpus"
BINDIR="$REPO/bin"
SELFTEST_DIR="$CPP/selftest"
LOGROOT="$AUDIT/logs/sanitizers"
SAN_DEFAULT=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/san
PY_DEFAULT=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/venv/bin/python
SUPP="$HERE/tsan-libomp.supp"
TAB=$'\t'

SAN=$SAN_DEFAULT
STAGES="a,b,c,d,e"
FORCE=0
DRYRUN=0
ASAN_THREADS=2
TSAN_THREADS=10
TIMEOUT_SCALE=1
UBSAN_CONTINUE=1
TSAN_PASSIVE=1
SUMMARIZE_ONLY=0

while [ $# -gt 0 ]; do
    case "$1" in
        --quick) STAGES="a" ;;
        --all) STAGES="a,b,c,d,e,tsan" ;;
        --stages) shift; STAGES=$1 ;;
        --force) FORCE=1 ;;
        --dry-run) DRYRUN=1 ;;
        --san-dir) shift; SAN=$1 ;;
        --asan-threads) shift; ASAN_THREADS=$1 ;;
        --tsan-threads) shift; TSAN_THREADS=$1 ;;
        --timeout-scale) shift; TIMEOUT_SCALE=$1 ;;
        --no-ubsan-continue) UBSAN_CONTINUE=0 ;;
        --tsan-active-wait) TSAN_PASSIVE=0 ;;
        --summarize-only) SUMMARIZE_ONLY=1 ;;
        -h|--help) sed -n '2,60p' "$0"; exit 0 ;;
        *) echo "run.sh: unknown argument $1" >&2; exit 2 ;;
    esac
    shift
done

PY=${PYTHON:-$PY_DEFAULT}
[ -x "$PY" ] || PY=$(command -v python3)

# GNU timeout (coreutils): exit 124 on expiry; -k sends KILL after the grace period.
TIMEOUT_BIN=""
for cand in gtimeout timeout /opt/homebrew/bin/gtimeout; do
    if command -v "$cand" >/dev/null 2>&1 && "$cand" --version 2>/dev/null | grep -q 'GNU coreutils'; then TIMEOUT_BIN=$(command -v "$cand"); break; fi
done
if [ -z "$TIMEOUT_BIN" ] && [ $DRYRUN -eq 0 ] && [ $SUMMARIZE_ONLY -eq 0 ]; then
    echo "run.sh: GNU timeout not found (brew install coreutils)" >&2; exit 2
fi

sha256_of() { shasum -a 256 "$1" | cut -d' ' -f1; }
bytes_of() { wc -c < "$1" | tr -d ' '; }
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
tmo() { echo $(( $1 * TIMEOUT_SCALE )); }
stage_selected() { case ",$STAGES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }

mkdir -p "$LOGROOT/asan_ubsan" "$LOGROOT/tsan" "$SAN/json"
WORK="$SAN/work"; mkdir -p "$WORK"
PLAN="$WORK/plan.txt"; : > "$PLAN"
DEDUPE="$WORK/dedupe.txt"; : > "$DEDUPE"

summarize() {
    "$PY" "$HERE/summarize.py" --log-root "$LOGROOT" --san-dir "$SAN" --out "$LOGROOT/RESULTS.md"
}
if [ $SUMMARIZE_ONLY -eq 1 ]; then summarize; exit $?; fi

# ---------------------------------------------------------------------------------------
# binaries, record, inputs
# ---------------------------------------------------------------------------------------
RECORD="$SAN/BUILD-RECORD.txt"
LSAN=unknown
bin_sha_recorded() { # variant tool -> sha256 from BUILD-RECORD (labelled read)
    sed -n "s|^binary=$SAN/$1/ea_$2 .* sha256=\([0-9a-f]*\) .*|\1|p" "$RECORD" | sed -n 1p
}
if [ $DRYRUN -eq 0 ]; then
    [ -f "$RECORD" ] || { echo "run.sh: $RECORD not found -- run build.sh first (instrument rule 4: no unrecorded binary is measured)" >&2; exit 2; }
    LSAN=$(sed -n 's/^lsan_supported=\([a-z]*\).*/\1/p' "$RECORD" | sed -n 1p)
    [ -n "$LSAN" ] || LSAN=unknown
fi
BINSHA_non_iid_asan_ubsan=""; BINSHA_iid_asan_ubsan=""; BINSHA_restart_asan_ubsan=""
BINSHA_non_iid_tsan=""; BINSHA_iid_tsan=""; BINSHA_restart_tsan=""
check_binary() { # variant tool -> 0 if present and matches the record
    local v=$1 t=$2 b="$SAN/$1/ea_$2" rec got
    [ -x "$b" ] || { echo "run.sh: missing binary $b" >&2; return 1; }
    rec=$(bin_sha_recorded "$v" "$t"); got=$(sha256_of "$b")
    if [ -z "$rec" ]; then echo "run.sh: $b has no binary= line in $RECORD" >&2; return 1; fi
    if [ "$rec" != "$got" ]; then echo "run.sh: $b sha256 $got differs from the recorded $rec -- rebuild or re-record" >&2; return 1; fi
    eval "BINSHA_${t}_${v}=$got"
    return 0
}
bin_sha() { eval "printf '%s' \"\$BINSHA_$2_$1\""; }

# generated inputs (deterministic; refuses on a sha mismatch with its own record)
INPUTS="$SAN/inputs"
"$PY" "$HERE/gen_inputs.py" --out "$INPUTS" > "$WORK/gen_inputs.out" 2>&1 || { cat "$WORK/gen_inputs.out"; echo "run.sh: gen_inputs.py refused" >&2; exit 2; }
RANDSRC="$INPUTS/random-source-1MiB.bin"
input_field() { # name key -> value from INPUTS.txt (labelled)
    sed -n "s|^name=$1 .*[[:space:]]$2=\([^[:space:]]*\).*|\1|p" "$INPUTS/INPUTS.txt" | sed -n 1p
}

# ---------------------------------------------------------------------------------------
# sanitizer runtime options
# ---------------------------------------------------------------------------------------
LEAKS=1; [ "$LSAN" = yes ] || LEAKS=0
ASAN_OPTS="detect_leaks=$LEAKS:abort_on_error=1:halt_on_error=1:strict_string_checks=1:detect_stack_use_after_return=1:check_initialization_order=1:strict_init_order=1"
UBSAN_OPTS="print_stacktrace=1:halt_on_error=1:report_error_type=1"
UBSAN_OPTS_CONTINUE="print_stacktrace=1:halt_on_error=0:report_error_type=1"
TSAN_OPTS="halt_on_error=0:second_deadlock_stack=1:history_size=3:print_suppressions=1:suppressions=$SUPP"

# ---------------------------------------------------------------------------------------
# duration model (seconds, asan_ubsan unless noted).  Anchors: production binaries, 2 threads,
# 20,000 samples (logs/sanitizers-calibration-*.log): ea_non_iid 8-bit -i -a 0.31 s, 1-bit
# 0.024 s, 8-bit -c 0.07 s; ea_iid random (early stop) 0.16 s, full battery 1.34 s.  Scaled
# linearly in n (LRS is n log n: underestimates by ~1.3x at 1e6), times 5 for -O1 + ASan/UBSan,
# times 10 for TSan.  Estimates, not measurements.
# ---------------------------------------------------------------------------------------
est_non_iid() { # n width mode(ia|c)
    local n=$1 w=$2 m=$3
    if [ "$m" = c ]; then echo $(( 2 + 25 * n / 1000000 )); return; fi
    if [ "$w" = 1 ]; then echo $(( 2 + 10 * n / 1000000 )); else echo $(( 2 + 100 * n / 1000000 )); fi
}
est_iid() { echo $(( 3 + 5 * $1 / 50000 )); }   # most inputs stop at chi-square or stop the battery early; the full-battery file gets its own est

# ---------------------------------------------------------------------------------------
# the plan: one line per run, |-separated:
#   stage|variant|tool|logname|input|operands|n|timeout|heavy|est|note|flags
# ---------------------------------------------------------------------------------------
plan_add() {
    local stage=$1 variant=$2 tool=$3 logname=$4 input=$5 operands=$6 n=$7 tmo_=$8 heavy=$9 est=${10} note=${11}
    shift 11
    printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' "$stage" "$variant" "$tool" "$logname" "$input" "$operands" "$n" "$tmo_" "$heavy" "$est" "$note" "$*" >> "$PLAN"
}
heavy_of() { if [ "$1" -ge 200000 ]; then echo yes; else echo no; fi; }
dedupe_seen() { # key -> prints the first logname, or returns 1
    local line
    line=$(grep -m1 -F -- "$1$TAB" "$DEDUPE") || return 1
    printf '%s\n' "${line#*$TAB}"
}
dedupe_record() { printf '%s\t%s\n' "$1" "$2" >> "$DEDUPE"; }

# Width a corpus edge file's NAME declares.  Prints "-" when the name says nothing (the run
# then lets the tool infer).  What this cannot see: a file whose name lies about its width;
# the second, tool-inferred run on every file is the control for that.
infer_width() {
    case "$1" in
        *-1bit*|*_w1_*|*rand1-*|perm-p1-bits*|collision-*|iid-chisq-bin140|intake-allzero-*|markov-*) echo 1 ;;
        *-8bit*|*_w8_*|*rand8-*|*counter8-*|perm-p3-two-values*|lag-k3-tieheavy-*) echo 8 ;;
        *-7bit*) echo 7 ;;
        *-4bit*) echo 4 ;;
        perm-p2-k8-*) echo 3 ;;
        mmc-worked-example-*|iid-chisq-dfneg|iid-chisq-ex11|iid-chisq-ex12) echo 2 ;;
        *) echo "-" ;;
    esac
}

plan_stage_a() {
    local name sha f base n w note
    [ -f "$SELFTEST_DIR/fixture-manifest.txt" ] || { echo "run.sh: $SELFTEST_DIR/fixture-manifest.txt missing" >&2; return; }
    while read -r kind name sha; do
        [ "$kind" = input ] || continue
        f="$BINDIR/$name"; base=${name%.bin}
        if [ ! -f "$f" ]; then plan_add a asan_ubsan non_iid "$base.selftest-vv" "$f" "" 0 "$(tmo 1800)" no 0 "MISSING-INPUT" -vv; continue; fi
        n=$(bytes_of "$f")
        w=$(sed -n 's/^Loaded [0-9]* samples of [0-9]* distinct \([0-9]*\)-bit-wide symbols.*/\1/p' "$SELFTEST_DIR/refdata/$base.res" 2>/dev/null | sed -n 1p)
        note="refdata_inferred_width:${w:-unknown}"
        if [ "$(sha256_of "$f")" != "$sha" ]; then note="SHA-MISMATCH-vs-fixture-manifest"; fi
        plan_add a asan_ubsan non_iid "$base.selftest-vv" "$f" "" "$n" "$(tmo 1800)" "$(heavy_of "$n")" "$(est_non_iid "$n" "${w:-8}" ia)" "$note" -vv
        if [ "$n" -lt 1000000 ]; then
            plan_add a asan_ubsan iid "$base.vv" "$f" "" "$n" "$(tmo 600)" no "$(est_iid "$n")" "$note (extra: not in selftest)" -vv
        fi
    done < "$SELFTEST_DIR/fixture-manifest.txt"
}

plan_stage_b() {
    local name bps n sha rest f base got note mode flags key first
    while IFS="$TAB" read -r name bps n sha rest; do
        case "$name" in '#'*|'') continue ;; esac
        case "$name" in *-50000.bin) ;; *) continue ;; esac
        f="$CORPUS/$name"; base=${name%.bin}
        if [ ! -f "$f" ]; then plan_add b asan_ubsan non_iid "$base.ia-w$bps" "$f" "$bps" "$n" "$(tmo 600)" no 0 "MISSING-INPUT" -i -a -vv; continue; fi
        got=$(sha256_of "$f"); note=""
        [ "$got" = "$sha" ] || note="SHA-MISMATCH-vs-MANIFEST:$got"
        for mode in ia c; do
            if [ "$mode" = ia ]; then flags="-i -a -vv"; else flags="-c -vv"; fi
            key="$got|$bps|$flags"
            if first=$(dedupe_seen "$key"); then
                plan_add b asan_ubsan non_iid "$base.$mode-w$bps" "$f" "$bps" "$n" "$(tmo 600)" no 0 "alias_of:$first" $flags
            else
                dedupe_record "$key" "$base.$mode-w$bps"
                plan_add b asan_ubsan non_iid "$base.$mode-w$bps" "$f" "$bps" "$n" "$(tmo 600)" no "$(est_non_iid "$n" "$bps" "$mode")" "$note" $flags
            fi
        done
    done < "$CORPUS/MANIFEST.txt"
    # extras: the -l subset path (20,000 of 50,000 samples) and the -o JSON report path.
    f="$CORPUS/csprng-8bit-50000.bin"
    if [ -f "$f" ]; then
        plan_add b asan_ubsan non_iid "csprng-8bit-50000.l1-20000.ia-w8" "$f" "8" 20000 "$(tmo 600)" no 5 "subset -l 1,20000" -i -a -vv -l 1,20000
        plan_add b asan_ubsan non_iid "csprng-8bit-50000.o.ia-w8" "$f" "8" 50000 "$(tmo 600)" no 8 "JSON report via -o (exercises writeJsonReport; EA_TEST_RANDOM_SOURCE matters here)" -i -a -vv -o @JSON@
    fi
}

plan_stage_c() {
    local f base n w
    for f in "$CORPUS"/*.bin; do
        [ -f "$f" ] || continue
        base=$(basename "$f" .bin)
        case "$base" in *-1000000|*-999999|*-50000) continue ;; esac
        n=$(bytes_of "$f")
        w=$(infer_width "$base")
        if [ "$w" != "-" ]; then
            plan_add c asan_ubsan non_iid "$base.vv-w$w" "$f" "$w" "$n" "$(tmo 300)" "$(heavy_of "$n")" "$(est_non_iid "$n" "$w" ia)" "name-declared width $w" -vv
        fi
        plan_add c asan_ubsan non_iid "$base.vv-winf" "$f" "" "$n" "$(tmo 300)" "$(heavy_of "$n")" "$(est_non_iid "$n" 8 ia)" "tool-inferred width" -vv
        if [ "$w" != "-" ]; then
            plan_add c asan_ubsan iid "$base.vv-w$w" "$f" "$w" "$n" "$(tmo 300)" "$(heavy_of "$n")" "$(est_iid "$n")" "name-declared width $w" -vv
        else
            plan_add c asan_ubsan iid "$base.vv-winf" "$f" "" "$n" "$(tmo 300)" "$(heavy_of "$n")" "$(est_iid "$n")" "tool-inferred width" -vv
        fi
    done
}

plan_stage_d() {
    local name bps n sha rest f base got note mode flags key first
    while IFS="$TAB" read -r name bps n sha rest; do
        case "$name" in '#'*|'') continue ;; esac
        case "$name" in *-50000.bin) ;; *) continue ;; esac
        f="$CORPUS/$name"; base=${name%.bin}
        [ -f "$f" ] || continue
        got=$(sha256_of "$f"); note=""
        [ "$got" = "$sha" ] || note="SHA-MISMATCH-vs-MANIFEST:$got"
        for mode in ia c; do
            if [ "$mode" = ia ]; then flags="-i -a -v"; else flags="-c -v"; fi
            key="iid|$got|$bps|$flags"
            if first=$(dedupe_seen "$key"); then
                plan_add d asan_ubsan iid "$base.$mode-v-w$bps" "$f" "$bps" "$n" "$(tmo 1200)" no 0 "alias_of:$first" $flags
            else
                dedupe_record "$key" "$base.$mode-v-w$bps"
                plan_add d asan_ubsan iid "$base.$mode-v-w$bps" "$f" "$bps" "$n" "$(tmo 1200)" no "$(est_iid "$n")" "$note" $flags
            fi
        done
    done < "$CORPUS/MANIFEST.txt"
    f="$INPUTS/iid-lag32copy-q030-1bit-50000.bin"
    plan_add d asan_ubsan iid "iid-lag32copy-q030-1bit-50000.ia-v-w1" "$f" "1" 50000 "$(tmo 1200)" no 20 "generated: passes chi-square+LRS, permutation battery runs all 10,000 rounds (measured at 20,000 on production)" -i -a -v
    f="$CORPUS/csprng-8bit-50000.bin"
    [ -f "$f" ] && plan_add d asan_ubsan iid "csprng-8bit-50000.o.ia-v-w8" "$f" "8" 50000 "$(tmo 1200)" no 5 "JSON report via -o" -i -a -v -o @JSON@
}

plan_stage_e() {
    local f1="$INPUTS/restart-1bit-1000x1000.bin" f8="$INPUTS/restart-8bit-1000x1000.bin" h1 h8
    h1=$(input_field restart-1bit-1000x1000.bin H_I); h8=$(input_field restart-8bit-1000x1000.bin H_I)
    plan_add e asan_ubsan restart "restart-1bit-1000x1000.n-v-w1-hi$h1" "$f1" "1 $h1" 1000000 "$(tmo 3600)" yes 40 "non-IID restart; X_max rows/cols $(input_field restart-1bit-1000x1000.bin X_max_rows)/$(input_field restart-1bit-1000x1000.bin X_max_cols) (gen_inputs)" -n -v
    plan_add e asan_ubsan restart "restart-8bit-1000x1000.n-v-w8-hi7.0symbol" "$f8" "8 $h8" 1000000 "$(tmo 3600)" yes 240 "non-IID restart; X_max rows/cols $(input_field restart-8bit-1000x1000.bin X_max_rows)/$(input_field restart-8bit-1000x1000.bin X_max_cols)" -n -v
    plan_add e asan_ubsan restart "restart-1bit-1000x1000.i-v-w1-hi$h1" "$f1" "1 $h1" 1000000 "$(tmo 3600)" yes 300 "IID restart: the only ea_restart path with a LIVE parallel region (permutation_tests on rows and columns)" -i -v
    plan_add e asan_ubsan restart "restart-1bit-1000x1000.o.n-v-w1-hi$h1" "$f1" "1 $h1" 1000000 "$(tmo 3600)" yes 40 "JSON report via -o" -n -v -o @JSON@
}

plan_stage_tsan() {
    local f1="$INPUTS/restart-1bit-1000x1000.bin" f8="$INPUTS/restart-8bit-1000x1000.bin" h1 h8
    h1=$(input_field restart-1bit-1000x1000.bin H_I); h8=$(input_field restart-8bit-1000x1000.bin H_I)
    # ea_iid: the ONLY tool whose production build contains a live `#pragma omp` region
    # (iid/permutation_tests.h:625-722).  Early-stop inputs exercise the atomic else-branch
    # (:722) concurrently with the critical section; the lag-32 input keeps all threads in
    # the critical section for 10,000 rounds.
    plan_add tsan tsan iid "csprng-8bit-50000.ia-v-w8" "$CORPUS/csprng-8bit-50000.bin" "8" 50000 "$(tmo 1800)" yes 60 "early-stop battery, 8-bit" -i -a -v
    plan_add tsan tsan iid "csprng-1bit-50000.ia-v-w1" "$CORPUS/csprng-1bit-50000.bin" "1" 50000 "$(tmo 1800)" yes 60 "early-stop battery, 1-bit" -i -a -v
    plan_add tsan tsan iid "iid-lag32copy-q030-1bit-50000.ia-v-w1" "$INPUTS/iid-lag32copy-q030-1bit-50000.bin" "1" 50000 "$(tmo 1800)" yes 120 "full 10,000-round battery: maximal critical-section contention" -i -a -v
    # ea_non_iid: NO `#pragma omp` anywhere in its translation unit -- a control.  A TSan
    # report here cannot come from the tool's threading (it has none) and would point at
    # the runtime or the build.
    plan_add tsan tsan non_iid "csprng-8bit-50000.ia-vv-w8" "$CORPUS/csprng-8bit-50000.bin" "8" 50000 "$(tmo 1800)" yes 20 "CONTROL: no omp pragma in ea_non_iid" -i -a -vv
    plan_add tsan tsan non_iid "csprng-1bit-50000.ia-vv-w1" "$CORPUS/csprng-1bit-50000.bin" "1" 50000 "$(tmo 1800)" yes 10 "CONTROL: no omp pragma in ea_non_iid" -i -a -vv
    plan_add tsan tsan non_iid "overwidth-7bit-50000.ia-vv-w7" "$CORPUS/overwidth-7bit-50000.bin" "7" 50000 "$(tmo 1800)" yes 20 "CONTROL: no omp pragma in ea_non_iid; overwidth intake path" -i -a -vv
    # ea_restart: its own `#pragma omp parallel` (restart_main.cpp:307) is inside
    # simulateBound(), compiled only under EA_RESTART_WITHOUT_C23_FIX -- dead in this build.
    # -n runs are controls; -i reaches permutation_tests' live region on 1e6-sample rows/cols.
    plan_add tsan tsan restart "restart-1bit-1000x1000.n-v-w1-hi$h1" "$f1" "1 $h1" 1000000 "$(tmo 3600)" yes 180 "CONTROL: parallel region dead in production build" -n -v
    plan_add tsan tsan restart "restart-8bit-1000x1000.n-v-w8-hi7.0symbol" "$f8" "8 $h8" 1000000 "$(tmo 3600)" yes 900 "CONTROL: parallel region dead in production build" -n -v
    plan_add tsan tsan restart "restart-1bit-1000x1000.i-v-w1-hi$h1" "$f1" "1 $h1" 1000000 "$(tmo 3600)" yes 1200 "LIVE parallel region via permutation_tests on rows and columns" -i -v
}

# ---------------------------------------------------------------------------------------
# classification of one finished log (reads the FILE; rule 17).  States what it cannot see:
# a report in a format these regexes do not match, a wrong number printed by a run that
# completed, a crash that printed nothing (classified SIGNAL-n, not explained).
# ---------------------------------------------------------------------------------------
classify() { # log rc tmo tool wall
    local log=$1 rc=$2 tmo_=$3 tool=$4 wall=$5 first n_sum outcome rounds battery
    first=$(sed -n '/^## --- tool output ---$/,/^## --- end of tool output ---$/p' "$log" | grep -m1 -E '^==[0-9]+==ERROR: |: runtime error: |^WARNING: ThreadSanitizer: |^==[0-9]+==WARNING: [A-Za-z]*Sanitizer')
    n_sum=$(grep -c -E '^SUMMARY: (Address|UndefinedBehavior|Thread|Leak)Sanitizer: |^WARNING: ThreadSanitizer: ' "$log")
    if [ -n "$first" ]; then echo "## sanitizer_report: yes" >> "$log"; else echo "## sanitizer_report: no" >> "$log"; fi
    echo "## sanitizer_report_count: $n_sum" >> "$log"
    echo "## first_report_line: ${first:--}" >> "$log"
    if [ "$rc" -eq 124 ] || { [ "$rc" -eq 137 ] && [ "$wall" -ge "$tmo_" ]; }; then outcome=TIMEOUT
    elif [ -n "$first" ]; then outcome=SANITIZER
    elif [ "$rc" -ge 128 ]; then outcome="SIGNAL-$((rc - 128))"
    elif grep -q 'Assessed min entropy:' "$log"; then outcome=COMPLETED
    elif grep -q 'min(H_r, H_c, H_I):' "$log"; then outcome=COMPLETED
    elif grep -q 'IID test suite failed' "$log"; then outcome=COMPLETED-IID-BATTERY-FAILED
    elif grep -q 'Validation Testing Failed' "$log"; then outcome=COMPLETED-VALIDATION-FAILED
    elif grep -q 'Restart Sanity Check Failed' "$log"; then outcome=COMPLETED-SANITY-CHECK-FAILED
    elif grep -q -E 'Usage is:|Error|No entropy awarded|does not contain|refus' "$log"; then outcome=REFUSED
    else outcome=UNCLASSIFIED; fi
    echo "## tool_outcome: $outcome" >> "$log"
    if [ "$tool" = iid ] || [ "$tool" = restart ]; then
        rounds=$(grep -c 'of Permutation test rounds' "$log")
        if grep -q 'Beginning permutation tests' "$log"; then battery=reached; elif grep -q 'Skipped IID permutation tests' "$log"; then battery=skipped-after-required-test-failure; else battery=not-seen; fi
        echo "## permutation_battery: $battery" >> "$log"
        echo "## permutation_progress_lines: $rounds" >> "$log"
    fi
    printf '%s' "$outcome"
}

# ---------------------------------------------------------------------------------------
# one run
# ---------------------------------------------------------------------------------------
N_RUN=0; N_SKIP=0; N_ALIAS=0; N_REPORT=0; N_BAD=0
run_one() {
    local stage=$1 variant=$2 tool=$3 logname=$4 input=$5 operands=$6 n=$7 tmo_=$8 heavy=$9 est=${10} note=${11} flags=${12}
    local bin="$SAN/$variant/ea_$tool" log="$LOGROOT/$variant/ea_$tool-$logname.log"
    local threads=$ASAN_THREADS
    [ "$variant" = tsan ] && threads=$TSAN_THREADS
    if [ $DRYRUN -eq 1 ]; then
        printf '%-4s %-10s %-10s heavy=%-3s est=%5ss n=%-8s ops=%-14s %s %s %s%s\n' "$stage" "$variant" "ea_$tool" "$heavy" "$est" "$n" "${operands:-<inferred>}" "$flags" "$(basename "$input")" "-> $(basename "$log")" "${note:+  [$note]}"
        return
    fi
    if [ $FORCE -eq 0 ] && [ -f "$log" ] && grep -q '^## exit: ' "$log"; then
        N_SKIP=$((N_SKIP + 1)); echo "skip  $(basename "$log") (complete log exists)"; return
    fi
    mkdir -p "$(dirname "$log")"
    local insha="-" inbytes="-"
    if [ -f "$input" ]; then insha=$(sha256_of "$input"); inbytes=$(bytes_of "$input"); fi
    local short=no
    [ "$n" -lt 1000000 ] && short=yes
    # header
    {
        echo "## stage: $stage"; echo "## variant: $variant"; echo "## tool: ea_$tool"
        echo "## binary: $bin"; echo "## binary_sha256: $(bin_sha "$variant" "$tool")"
        echo "## input: $input"; echo "## input_sha256: $insha"; echo "## input_bytes: $inbytes"
        echo "## operands: ${operands:-<width inferred by the tool>}"; echo "## flags: $flags"
        echo "## short_dataset_escape: $short"; echo "## heavy: $heavy"; echo "## note: $note"
        echo "## timeout_seconds: $tmo_"; echo "## threads: $threads"; echo "## start: $(now)"
    } > "$log"
    case "$note" in
        alias_of:*)
            { echo "## alias_of: ${note#alias_of:}"; echo "## --- tool output ---"; echo "## --- end of tool output ---"; echo "## exit: -"; echo "## wall_seconds: 0"; echo "## sanitizer_report: see-alias"; echo "## first_report_line: -"; echo "## tool_outcome: ALIAS"; } >> "$log"
            N_ALIAS=$((N_ALIAS + 1)); echo "alias $(basename "$log") -> ${note#alias_of:}"; return ;;
        SHA-MISMATCH*|MISSING-INPUT*)
            { echo "## --- tool output ---"; echo "## --- end of tool output ---"; echo "## exit: -"; echo "## wall_seconds: 0"; echo "## sanitizer_report: not-run"; echo "## first_report_line: -"; echo "## tool_outcome: SKIPPED-INPUT-${note%%:*}"; } >> "$log"
            N_BAD=$((N_BAD + 1)); echo "SKIP  $(basename "$log"): $note"; return ;;
    esac
    # command and environment
    local -a cmd envs ops
    cmd=("$bin")
    local tok
    for tok in $flags; do
        if [ "$tok" = "@JSON@" ]; then cmd+=("$SAN/json/ea_$tool-$logname.json"); else cmd+=("$tok"); fi
    done
    cmd+=("$input")
    if [ -n "$operands" ]; then for tok in $operands; do cmd+=("$tok"); done; fi
    envs=("OMP_NUM_THREADS=$threads" "EA_TEST_RANDOM_SOURCE=$RANDSRC")
    [ "$short" = yes ] && envs+=("EA_ALLOW_SHORT_DATASET=1")
    if [ "$variant" = asan_ubsan ]; then envs+=("ASAN_OPTIONS=$ASAN_OPTS" "UBSAN_OPTIONS=$UBSAN_OPTS")
    else envs+=("TSAN_OPTIONS=$TSAN_OPTS"); [ $TSAN_PASSIVE -eq 1 ] && envs+=("OMP_WAIT_POLICY=passive"); fi
    { echo "## env: ${envs[*]}"; echo "## cmd: ${cmd[*]}"; echo "## --- tool output ---"; } >> "$log"
    local t0 t1 rc wall outcome
    t0=$(date +%s)
    env "${envs[@]}" "$TIMEOUT_BIN" -k 15 "$tmo_" "${cmd[@]}" >> "$log" 2>&1
    rc=$?
    t1=$(date +%s); wall=$((t1 - t0))
    { echo "## --- end of tool output ---"; echo "## exit: $rc"; echo "## wall_seconds: $wall"; echo "## end: $(now)"; } >> "$log"
    outcome=$(classify "$log" "$rc" "$tmo_" "$tool" "$wall")
    N_RUN=$((N_RUN + 1))
    case "$outcome" in SANITIZER) N_REPORT=$((N_REPORT + 1)) ;; TIMEOUT|SIGNAL-*|UNCLASSIFIED) N_BAD=$((N_BAD + 1)) ;; esac
    printf '%-9s %4ss exit=%-3s %s\n' "$outcome" "$wall" "$rc" "$(basename "$log")"
    # UBSan recoverable classes stop the run at the first report under halt_on_error=1; a
    # second pass with halt_on_error=0 collects the rest of that input's reports.  ASan and
    # the `undefined` group stay fatal (not compiled recoverable), so only these continue.
    if [ "$variant" = asan_ubsan ] && [ $UBSAN_CONTINUE -eq 1 ] && [ "$outcome" = SANITIZER ]; then
        local firstline
        firstline=$(sed -n 's/^## first_report_line: //p' "$log" | sed -n 1p)
        case "$firstline" in
            *"runtime error: implicit conversion"*|*"-integer-truncation"*|*"-sign-change"*|*"null pointer passed"*|*"nullability"*|*"division by zero"*|*"runtime error: "*)
                local log2="${log%.log}.ubsan-continue.log"
                if [ $FORCE -eq 1 ] || [ ! -f "$log2" ] || ! grep -q '^## exit: ' "$log2"; then
                    local -a envs2
                    envs2=()
                    for tok in "${envs[@]}"; do case "$tok" in UBSAN_OPTIONS=*) envs2+=("UBSAN_OPTIONS=$UBSAN_OPTS_CONTINUE") ;; *) envs2+=("$tok") ;; esac; done
                    sed -n '1,/^## --- tool output ---$/p' "$log" | sed '$d' > "$log2"
                    { echo "## rerun_of: $(basename "$log")"; echo "## rerun_reason: first report was a recoverable UBSan class; halt_on_error=0 to see the rest"; echo "## env: ${envs2[*]}"; echo "## cmd: ${cmd[*]}"; echo "## --- tool output ---"; } >> "$log2"
                    t0=$(date +%s)
                    env "${envs2[@]}" "$TIMEOUT_BIN" -k 15 "$tmo_" "${cmd[@]}" >> "$log2" 2>&1
                    rc=$?
                    t1=$(date +%s); wall=$((t1 - t0))
                    { echo "## --- end of tool output ---"; echo "## exit: $rc"; echo "## wall_seconds: $wall"; echo "## end: $(now)"; } >> "$log2"
                    outcome=$(classify "$log2" "$rc" "$tmo_" "$tool" "$wall")
                    printf '%-9s %4ss exit=%-3s %s (UBSan continue pass, %s report lines)\n' "$outcome" "$wall" "$rc" "$(basename "$log2")" "$(sed -n 's/^## sanitizer_report_count: //p' "$log2")"
                fi ;;
        esac
    fi
}

# ---------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------
stage_selected a && plan_stage_a
stage_selected b && plan_stage_b
stage_selected c && plan_stage_c
stage_selected d && plan_stage_d
stage_selected e && plan_stage_e
stage_selected tsan && plan_stage_tsan

if [ $DRYRUN -eq 1 ]; then
    echo "# plan (dry run): stages=$STAGES san=$SAN logs=$LOGROOT"
    echo "# est = model estimate in seconds for this variant (README.md: anchored on four production measurements, not measured on sanitizer binaries)"
fi

if [ $DRYRUN -eq 0 ]; then
    NEED_V=""
    stage_selected a || stage_selected b || stage_selected c || stage_selected d || stage_selected e && NEED_V="asan_ubsan"
    stage_selected tsan && NEED_V="$NEED_V tsan"
    for v in $NEED_V; do for t in non_iid iid restart; do check_binary "$v" "$t" || exit 2; done; done
    {
        echo "# ENV -- written by run.sh at $(now)"
        echo "host=$(uname -a)"
        echo "stages=$STAGES force=$FORCE san_dir=$SAN build_record_sha256=$(sha256_of "$RECORD")"
        echo "lsan_supported_per_build_record=$LSAN detect_leaks_used=$LEAKS"
        echo "asan_threads=$ASAN_THREADS tsan_threads=$TSAN_THREADS timeout_scale=$TIMEOUT_SCALE ubsan_continue=$UBSAN_CONTINUE tsan_passive_wait=$TSAN_PASSIVE"
        echo "timeout_bin=$TIMEOUT_BIN"
        echo "ASAN_OPTIONS=$ASAN_OPTS"
        echo "UBSAN_OPTIONS=$UBSAN_OPTS"
        echo "UBSAN_OPTIONS_continue=$UBSAN_OPTS_CONTINUE"
        echo "TSAN_OPTIONS=$TSAN_OPTS"
        echo "EA_TEST_RANDOM_SOURCE=$RANDSRC sha256=$(sha256_of "$RANDSRC") reaches=TestRunUtils.h:478 (-o temporary-file suffix only; permutation seed is /dev/urandom, utils.h:797)"
        echo "suppressions_sha256=$(sha256_of "$SUPP")"
        echo "gen_inputs_sha256=$(sha256_of "$HERE/gen_inputs.py") run_sh_sha256=$(sha256_of "$0")"
    } > "$LOGROOT/ENV.txt"
fi

TOTAL_EST=0
while IFS='|' read -r stage variant tool logname input operands n tmo_ heavy est note flags; do
    [ -n "$stage" ] || continue
    TOTAL_EST=$((TOTAL_EST + est))
    run_one "$stage" "$variant" "$tool" "$logname" "$input" "$operands" "$n" "$tmo_" "$heavy" "$est" "$note" "$flags"
done < "$PLAN"

if [ $DRYRUN -eq 1 ]; then
    echo "# $(wc -l < "$PLAN" | tr -d ' ') planned runs; model total ~$TOTAL_EST s (~$((TOTAL_EST / 60)) min) excluding UBSan continue passes"
    exit 0
fi

echo "runs=$N_RUN skipped(existing)=$N_SKIP aliases=$N_ALIAS sanitizer_reports=$N_REPORT timeouts/signals/unclassified/skipped-input=$N_BAD"
summarize
echo "results: $LOGROOT/RESULTS.md"
exit 0
