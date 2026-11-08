#!/bin/bash
#
# run.sh -- determinism and thread-count phase of the 2026-11-07 aggressive audit.
# TO BE RUN LATER, when the machine's single heavy-job slot is free (ground rule 4).
#
# WHAT IT RUNS (full mode; thread counts 1, 2 and 10, plus a second run at 10):
#   ea_non_iid -i -a -vv -o <json> <file> [bps]
#       on every bin/*.bin with NO width argument (exactly as cpp/selftest/selftest does;
#       the width is inferred, and the inferred width is read back from the 'Loaded ...
#       distinct N-bit-wide symbols' line), and on the four corpus files
#       csprng-1bit-1000000, csprng-8bit-1000000, two9010-8bit-1000000,
#       period255-8bit-1000000 with their DECLARED width from corpus/MANIFEST.txt
#       (regenerated with harness/gen_corpus.py if absent or not matching the manifest).
#   ea_iid -i -a -vv -o <json> <file>
#       on bin/truerand_1bit.bin and bin/truerand_8bit.bin:
#       arm a: default /dev/urandom, two runs at the top thread count;
#       arm b: EA_TEST_RANDOM_SOURCE=<fixed 1 MiB file> at 1, 2, 10 threads + a repeat at 10.
#       The source says the variable does NOT reach seed() (utils.h:797 opens the literal
#       "/dev/urandom"; the variable is read only at TestRunUtils.h:129 for the report
#       temp-file suffix at :478), so the PREDICTION is that arm b varies exactly like arm
#       a.  The arm is run as specified so the record shows the measurement, not the reading.
#   ea_restart -n -vv -o <json> <matrix> <bps> <H_I>
#       on two deterministic 1000 x 1000 matrices (harness/determinism/gen_inputs.py):
#       1-bit with H_I 0.9, 8-bit with H_I 7.5/symbol; 1, 2, 10 threads + a repeat at 10.
#       Is ea_restart threaded?  Its only `#pragma omp` is in simulateBound()
#       (restart_main.cpp:307-316), called only under #ifdef EA_RESTART_WITHOUT_C23_FIX
#       (:745), which the production compile line (BUILD-LINES.md) does not define; -i
#       would thread through permutation_tests() (:1127, :1134).  So under -n NO parallel
#       region executes and the thread count should change nothing.
#   then harness/determinism/compare_runs.py   -> <out>/RESULTS.md
#        harness/determinism/compare_linux.py  -> <out>/compare-linux.md (+ .tsv)
#        harness/determinism/xoshiro_model.py  -> <out>/xoshiro-model.log
#
# RECORD DISCIPLINE
#   rule 17: every tool writes stdout/stderr to FILES; the exit status is read from $?
#            immediately and written to <tag>.rc; nothing is piped into head/tail.
#   instrument rule 4: the sha256 of the binary is recorded in every run's .meta, BEFORE
#            and AFTER the run (a rebuild during the phase would show as a change), and in
#            <out>/binaries.sha256; every input's sha256 is in <out>/inputs.sha256.
#   instrument rule 2: compare_runs.py accepts a run as evidence only if it is well-formed
#            (rc, final marker, non-placeholder JSON).
#   ground rule 4: in full mode the script REFUSES to start while another heavy job is
#            running (diff_driver.py, afl-fuzz, an ea_* binary, a sanitizer build, make),
#            unless --force.  It never runs two tool processes at once.
#
# SMOKE MODE (--smoke): a plumbing check allowed while the heavy slot is taken -- 20,000-
#   sample prefixes (EA_ALLOW_SHORT_DATASET=1, so every run is marked NON-COMPLIANT by the
#   tool), thread counts 1 and 2 only, ea_restart NOT run (it needs exactly 1,000,000
#   samples), output under <out>/smoke/ so it never mixes with the real results.
#
# Usage: run.sh [--smoke] [--only non_iid,iid,restart,compare,linux,model] [--threads "1 2 10"] [--force]
# Env:   DET_PYTHON (python with numpy, for gen_corpus.py)   DET_OUT (default <audit>/logs/determinism)
#        DET_NON_IID_BIN / DET_IID_BIN / DET_RESTART_BIN (default cpp/ea_*; point DET_IID_BIN at an
#        out-of-tree fixed-seed build to make arm b a real fixed-seed arm; the sha256 is recorded)

set -u

here=$(cd "$(dirname "$0")" && pwd)
AUDIT=$(cd "$here/../.." && pwd)
REPO=$(cd "$AUDIT/../../.." && pwd)
PY=${DET_PYTHON:-/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/venv/bin/python}
if [ ! -x "$PY" ]; then PY=$(command -v python3); fi
OUT=${DET_OUT:-$AUDIT/logs/determinism}
NON_IID_BIN=${DET_NON_IID_BIN:-$REPO/cpp/ea_non_iid}
IID_BIN=${DET_IID_BIN:-$REPO/cpp/ea_iid}
RESTART_BIN=${DET_RESTART_BIN:-$REPO/cpp/ea_restart}

MODE=full
THREADS="1 2 10"
ONLY=""
FORCE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --smoke) MODE=smoke ;;
        --only) shift; ONLY=$1 ;;
        --threads) shift; THREADS=$1 ;;
        --force) FORCE=1 ;;
        -h|--help) sed -n '2,60p' "$0"; exit 0 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
    shift
done
SHORT=0
if [ "$MODE" = smoke ]; then
    OUT="$OUT/smoke"
    THREADS="1 2"
    SHORT=1
fi
mkdir -p "$OUT" || exit 2
RUNLOG="$OUT/run.log"

log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" | tee -a "$RUNLOG"; }
want() { # want <step>: true when --only is empty or names the step
    [ -z "$ONLY" ] && return 0
    case ",$ONLY," in *",$1,"*) return 0 ;; esac
    return 1
}
sha256() { "$PY" -c 'import hashlib,sys
h=hashlib.sha256()
with open(sys.argv[1],"rb") as f:
    for b in iter(lambda: f.read(1<<20), b""): h.update(b)
print(h.hexdigest())' "$1"; }
fsize() { "$PY" -c 'import os,sys; print(os.path.getsize(sys.argv[1]))' "$1"; }
fmtime() { "$PY" -c 'import os,sys,datetime; print(datetime.datetime.fromtimestamp(os.path.getmtime(sys.argv[1])).isoformat(timespec="seconds"))' "$1"; }
maxthreads() { local m=0 t; for t in $THREADS; do [ "$t" -gt "$m" ] && m=$t; done; echo "$m"; }
TMAX=$(maxthreads)

log "determinism phase: mode=$MODE threads='$THREADS' out=$OUT repo=$REPO python=$PY"

# ---------------------------------------------------------------- preflight
for b in "$NON_IID_BIN" "$IID_BIN" "$RESTART_BIN"; do
    if [ ! -x "$b" ]; then log "REFUSED: binary missing or not executable: $b"; exit 2; fi
done
{
    echo "date=$(date '+%Y-%m-%dT%H:%M:%S%z')"
    echo "mode=$MODE"
    echo "threads=$THREADS"
    echo "uname_a=$(uname -a)"
    echo "uname_s=$(uname -s)"
    echo "uname_m=$(uname -m)"
    clang++ --version > "$OUT/compiler-version.txt" 2>&1
    echo "compiler=$(sed -n '1p' "$OUT/compiler-version.txt")"
    echo "hw.ncpu=$(sysctl -n hw.ncpu 2>/dev/null)"
    echo "hw.memsize=$(sysctl -n hw.memsize 2>/dev/null)"
    echo "cpu=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)"
    echo "sw_vers=$(sw_vers 2>/dev/null | tr '\n' ' ')"
    echo "git_head=$(git -C "$REPO" rev-parse HEAD 2>/dev/null)"
    echo "git_branch=$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo "git_dirty=$(git -C "$REPO" status --porcelain 2>/dev/null | wc -l | tr -d ' ') paths modified or untracked"
    echo "omp_runtime=$(otool -L "$NON_IID_BIN" 2>/dev/null | grep -o '[^ ]*libomp[^ ]*')"
    echo "python=$("$PY" --version 2>&1)"
} > "$OUT/host.txt"
{
    for b in "$NON_IID_BIN" "$IID_BIN" "$RESTART_BIN"; do
        printf '%s  %s  (%s bytes, mtime %s)\n' "$(sha256 "$b")" "$b" "$(fsize "$b")" "$(fmtime "$b")"
    done
} > "$OUT/binaries.sha256"
log "binaries recorded in $OUT/binaries.sha256"

# heavy-job guard (ground rule 4)
pgrep -fl 'diff_driver\.py|afl-fuzz|/ea_non_iid |/ea_iid |/ea_restart |fsanitize|(^| )make( |$)' > "$OUT/heavy-guard.txt" 2>/dev/null
if [ -s "$OUT/heavy-guard.txt" ]; then
    if [ "$MODE" = full ] && [ "$FORCE" -ne 1 ]; then
        log "REFUSED: another heavy job is running (ground rule 4); see $OUT/heavy-guard.txt; re-run when it is done or pass --force"
        cat "$OUT/heavy-guard.txt" | tee -a "$RUNLOG"
        exit 3
    fi
    log "note: other jobs running (recorded in heavy-guard.txt); continuing because mode=$MODE force=$FORCE"
fi

# corpus (full mode only; smoke uses prefixes cut by gen_inputs.py from the 50,000 files)
NEEDED="csprng-1bit-1000000.bin csprng-8bit-1000000.bin two9010-8bit-1000000.bin period255-8bit-1000000.bin"
if [ "$MODE" = full ] && want non_iid; then
    "$PY" "$AUDIT/harness/gen_corpus.py" --check > "$OUT/corpus-check.log" 2>&1
    echo "exit=$?" >> "$OUT/corpus-check.log"
    missing=0
    for n in $NEEDED; do
        if ! grep -qE "^OK +$n\$" "$OUT/corpus-check.log"; then missing=1; log "corpus: $n not OK in the manifest check"; fi
    done
    if [ "$missing" -eq 1 ]; then
        log "corpus: regenerating csprng, two9010, period255 at n=1,000,000 (deterministic; manifest merged)"
        "$PY" "$AUDIT/harness/gen_corpus.py" --families csprng,two9010,period255 --widths 1,8 --sizes 1000000 --no-smoke > "$OUT/corpus-regen.log" 2>&1
        echo "exit=$?" >> "$OUT/corpus-regen.log"
        "$PY" "$AUDIT/harness/gen_corpus.py" --check > "$OUT/corpus-check-after.log" 2>&1
        echo "exit=$?" >> "$OUT/corpus-check-after.log"
        for n in $NEEDED; do
            if ! grep -qE "^OK +$n\$" "$OUT/corpus-check-after.log"; then log "REFUSED: $n still not OK after regeneration"; exit 2; fi
        done
    fi
fi

# deterministic inputs (restart matrices, fixed random source, smoke prefixes)
INPUTS="$OUT/inputs"
if [ "$MODE" = smoke ]; then
    "$PY" "$here/gen_inputs.py" --out "$INPUTS" --smoke > "$OUT/gen-inputs.log" 2>&1
else
    "$PY" "$here/gen_inputs.py" --out "$INPUTS" > "$OUT/gen-inputs.log" 2>&1
fi
echo "exit=$?" >> "$OUT/gen-inputs.log"
"$PY" "$here/gen_inputs.py" --out "$INPUTS" --check > "$OUT/gen-inputs-check.log" 2>&1
rc=$?; echo "exit=$rc" >> "$OUT/gen-inputs-check.log"
if [ "$rc" -ne 0 ]; then log "REFUSED: generated inputs do not verify; see $OUT/gen-inputs-check.log"; exit 2; fi
FIXED_SOURCE="$INPUTS/fixed-random-source-1MiB.bin"

# ---------------------------------------------------------------- one tool run
# run_tool <tool> <bin> <casedir> <tag> <threads> <rep> <arm> <extra_env or -> <input> -- <args...>
run_tool() {
    local tool=$1 bin=$2 casedir=$3 tag=$4 threads=$5 rep=$6 arm=$7 extra=$8 input=$9
    shift 9
    [ "$1" = "--" ] && shift
    mkdir -p "$casedir"
    local so="$casedir/$tag.stdout.txt" se="$casedir/$tag.stderr.txt" meta="$casedir/$tag.meta"
    local bsha_before bsha_after isha start end rc
    bsha_before=$(sha256 "$bin")
    isha=$(sha256 "$input")
    local extra_show="" rnd_src=""
    case "$extra" in
        EA_TEST_RANDOM_SOURCE=*) rnd_src=${extra#EA_TEST_RANDOM_SOURCE=}; extra_show=" $extra" ;;
    esac
    log "  $tool $(basename "$casedir") $tag (threads=$threads$extra_show) ..."
    start=$(date +%s)
    (
        unset EA_ALLOW_SHORT_DATASET EA_TEST_RANDOM_SOURCE
        export OMP_NUM_THREADS="$threads"
        if [ "$SHORT" -eq 1 ]; then export EA_ALLOW_SHORT_DATASET=1; fi
        if [ "$extra" != "-" ]; then export "$extra"; fi
        cd "$REPO" && exec "$bin" "$@"
    ) > "$so" 2> "$se"
    rc=$?
    end=$(date +%s)
    echo "$rc" > "$casedir/$tag.rc"
    bsha_after=$(sha256 "$bin")
    {
        echo "tool=$tool"
        echo "binary=$bin"
        echo "binary_sha256=$bsha_before"
        echo "binary_sha256_after=$bsha_after"
        echo "input=$input"
        echo "input_sha256=$isha"
        echo "threads=$threads"
        echo "rep=$rep"
        echo "arm=$arm"
        echo "OMP_NUM_THREADS=$threads"
        echo "EA_ALLOW_SHORT_DATASET=$([ "$SHORT" -eq 1 ] && echo 1)"
        echo "EA_TEST_RANDOM_SOURCE=$rnd_src"
        echo "start_epoch=$start"
        echo "end_epoch=$end"
        echo "wall_seconds=$((end - start))"
        echo "rc=$rc"
        echo "cmd=$bin $*"
    } > "$meta"
    if [ "$bsha_before" != "$bsha_after" ]; then log "  WARNING: $bin changed during the run ($bsha_before -> $bsha_after)"; fi
    log "  -> rc=$rc wall=$((end - start))s"
}

# ---------------------------------------------------------------- inputs.sha256
{
    echo "# sha256  bytes  path   (every input this phase reads)"
    for f in "$REPO"/bin/*.bin; do printf '%s  %s  %s\n' "$(sha256 "$f")" "$(fsize "$f")" "$f"; done
    for n in $NEEDED; do f="$AUDIT/corpus/$n"; [ -f "$f" ] && printf '%s  %s  %s\n' "$(sha256 "$f")" "$(fsize "$f")" "$f"; done
    for f in "$INPUTS"/*.bin; do printf '%s  %s  %s\n' "$(sha256 "$f")" "$(fsize "$f")" "$f"; done
} > "$OUT/inputs.sha256"

# ---------------------------------------------------------------- ea_non_iid
if want non_iid; then
    log "== ea_non_iid matrix =="
    # case list: "<path>|<bps or ->"
    CASES=""
    if [ "$MODE" = smoke ]; then
        CASES="$INPUTS/smoke-csprng-1bit-20000.bin|1 $INPUTS/smoke-csprng-8bit-20000.bin|8"
    else
        for f in "$REPO"/bin/*.bin; do CASES="$CASES $f|-"; done
        for n in $NEEDED; do
            bps=$(awk -F'\t' -v n="$n" '$1 == n { print $2 }' "$AUDIT/corpus/MANIFEST.txt")
            if [ -z "$bps" ]; then log "REFUSED: $n has no manifest row for its declared width"; exit 2; fi
            CASES="$CASES $AUDIT/corpus/$n|$bps"
        done
    fi
    for entry in $CASES; do
        f=${entry%|*}; bps=${entry##*|}
        case=$(basename "$f" .bin)
        casedir="$OUT/non_iid/$case"
        for t in $THREADS; do
            tag="t$t-r1"
            if [ "$bps" = "-" ]; then
                run_tool non_iid "$NON_IID_BIN" "$casedir" "$tag" "$t" 1 - - "$f" -- -i -a -vv -o "$casedir/$tag.json" "$f"
            else
                run_tool non_iid "$NON_IID_BIN" "$casedir" "$tag" "$t" 1 - - "$f" -- -i -a -vv -o "$casedir/$tag.json" "$f" "$bps"
            fi
        done
        tag="t$TMAX-r2"
        if [ "$bps" = "-" ]; then
            run_tool non_iid "$NON_IID_BIN" "$casedir" "$tag" "$TMAX" 2 - - "$f" -- -i -a -vv -o "$casedir/$tag.json" "$f"
        else
            run_tool non_iid "$NON_IID_BIN" "$casedir" "$tag" "$TMAX" 2 - - "$f" -- -i -a -vv -o "$casedir/$tag.json" "$f" "$bps"
        fi
    done
fi

# ---------------------------------------------------------------- ea_iid
if want iid; then
    log "== ea_iid matrix (arm a: /dev/urandom; arm b: EA_TEST_RANDOM_SOURCE=$FIXED_SOURCE) =="
    if [ "$MODE" = smoke ]; then
        IID_CASES="$INPUTS/smoke-csprng-1bit-20000.bin $INPUTS/smoke-csprng-8bit-20000.bin"
    else
        IID_CASES="$REPO/bin/truerand_1bit.bin $REPO/bin/truerand_8bit.bin"
    fi
    for f in $IID_CASES; do
        case=$(basename "$f" .bin)
        casedir="$OUT/iid/$case"
        for r in 1 2; do
            tag="a-t$TMAX-r$r"
            run_tool iid "$IID_BIN" "$casedir" "$tag" "$TMAX" "$r" a - "$f" -- -i -a -vv -o "$casedir/$tag.json" "$f"
        done
        for t in $THREADS; do
            tag="b-t$t-r1"
            run_tool iid "$IID_BIN" "$casedir" "$tag" "$t" 1 b "EA_TEST_RANDOM_SOURCE=$FIXED_SOURCE" "$f" -- -i -a -vv -o "$casedir/$tag.json" "$f"
        done
        tag="b-t$TMAX-r2"
        run_tool iid "$IID_BIN" "$casedir" "$tag" "$TMAX" 2 b "EA_TEST_RANDOM_SOURCE=$FIXED_SOURCE" "$f" -- -i -a -vv -o "$casedir/$tag.json" "$f"
    done
fi

# ---------------------------------------------------------------- ea_restart
if want restart; then
    if [ "$MODE" = smoke ]; then
        mkdir -p "$OUT/restart"
        echo "ea_restart NOT RUN in smoke mode: it requires exactly 1,000,000 samples (restart_main.cpp:694 data.len != MIN_SIZE), above the 20,000-sample probe limit." > "$OUT/restart/SKIPPED.txt"
        log "== ea_restart skipped in smoke mode (needs exactly 1,000,000 samples) =="
    else
        log "== ea_restart matrix (-n; the only omp region is dead code in production) =="
        # "<path>|<bps>|<H_I>"
        for entry in "$INPUTS/restart-csprng-1bit-1000x1000.bin|1|0.9" "$INPUTS/restart-csprng-8bit-1000x1000.bin|8|7.5/symbol"; do
            f=${entry%%|*}; rest=${entry#*|}; bps=${rest%%|*}; hi=${rest#*|}
            case=$(basename "$f" .bin)
            casedir="$OUT/restart/$case"
            for t in $THREADS; do
                tag="t$t-r1"
                run_tool restart "$RESTART_BIN" "$casedir" "$tag" "$t" 1 - - "$f" -- -n -vv -o "$casedir/$tag.json" "$f" "$bps" "$hi"
            done
            tag="t$TMAX-r2"
            run_tool restart "$RESTART_BIN" "$casedir" "$tag" "$TMAX" 2 - - "$f" -- -n -vv -o "$casedir/$tag.json" "$f" "$bps" "$hi"
        done
    fi
fi

# ---------------------------------------------------------------- model, comparisons
if want model; then
    "$PY" "$here/xoshiro_model.py" > "$OUT/xoshiro-model.log" 2>&1
    echo "exit=$?" >> "$OUT/xoshiro-model.log"
    log "xoshiro model: $(grep '^RESULT:' "$OUT/xoshiro-model.log")"
fi
RC_RUNS=0
if want compare; then
    if [ "$MODE" = smoke ]; then
        "$PY" "$here/compare_runs.py" --out "$OUT" --smoke > "$OUT/compare-runs.log" 2>&1
    else
        "$PY" "$here/compare_runs.py" --out "$OUT" > "$OUT/compare-runs.log" 2>&1
    fi
    RC_RUNS=$?
    echo "exit=$RC_RUNS" >> "$OUT/compare-runs.log"
    log "compare_runs.py exit $RC_RUNS -> $OUT/RESULTS.md"
fi
RC_LINUX=0
if want linux; then
    if [ "$MODE" = smoke ]; then
        # plumbing exercise only: the .res files cpp/selftest/selftest leaves behind, if any
        if ls "$REPO"/cpp/selftest/*.res > /dev/null 2>&1; then
            "$PY" "$here/compare_linux.py" --out "$OUT" --host-res-dir "$REPO/cpp/selftest" --report-name compare-linux-smoke-preview > "$OUT/compare-linux.log" 2>&1
            RC_LINUX=$?
        else
            echo "no cpp/selftest/*.res to preview against" > "$OUT/compare-linux.log"
        fi
    else
        "$PY" "$here/compare_linux.py" --out "$OUT" --all-host-runs > "$OUT/compare-linux.log" 2>&1
        RC_LINUX=$?
    fi
    echo "exit=$RC_LINUX" >> "$OUT/compare-linux.log"
    log "compare_linux.py exit $RC_LINUX -> see $OUT/compare-linux*.md"
fi

log "done: RESULTS.md=$OUT/RESULTS.md compare_runs=$RC_RUNS compare_linux=$RC_LINUX"
if [ "$RC_RUNS" -ne 0 ] || [ "$RC_LINUX" -ne 0 ]; then exit 1; fi
exit 0
