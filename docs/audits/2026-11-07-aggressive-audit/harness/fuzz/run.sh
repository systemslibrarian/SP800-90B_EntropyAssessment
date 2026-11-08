#!/bin/bash
# run.sh -- the AFL++ campaign for the 2026-11-07 aggressive audit.
#
#   usage: run.sh [FUZZ_DIR] [MINUTES] [--targets T1,T3,...] [--variant plain|asan]
#                 [--dry-run] [--preflight-only] [--no-preflight] [--force]
#     --preflight-only  run the baseline / instrumentation / seed / edge checks and
#                       write the record, but start no fuzzer (a rehearsal; with
#                       FUZZ_LOGS_DIR_OVERRIDE=<dir> it leaves nothing in logs/)
#     FUZZ_DIR  where build.sh put bin/ and seeds.py put seeds/ (default <scratchpad>/fuzz)
#     MINUTES   per-target cap (default 30, hard cap 120 -- brief rule 4).  Each target's
#               table default (fuzz_common.sh) is used when it is smaller than the cap.
#
# THIS IS A HEAVY JOB.  One afl-fuzz instance at a time, targets in sequence, and
# it refuses to start while another heavy job is visible (unless --force).
#
# TARGETS (fuzz_common.sh target_field; every one runs with EA_ALLOW_SHORT_DATASET=1
# and OMP_NUM_THREADS=2 in the environment):
#   T1 ea_non_iid -i -a @@            inferred width            asan   25 min
#   T2 ea_non_iid -i -a @@ 8          declared 8                asan   20 min
#   T3 ea_non_iid -i -a @@ 1          declared 1 (binary path)  asan   20 min
#   T4 ea_non_iid -c -a @@ 8          conditioned view          plain  15 min
#   T5 ea_non_iid -l 1,17 -i @@       subset arithmetic         plain  15 min
#   T6 ea_iid -i -a @@ 4              IID battery               plain  20 min
#   T7 argv_driver.sh @@              option parsing, H_I grammar, all three tools  plain 25 min
#   T8 ea_restart -n @@ 8 0.5/symbol  the second intake copy    asan   10 min
#   = 150 fuzz-minutes; with build (~8 min), per-target start-up and triage the
#   whole phase fits in roughly 3 hours of wall clock.
#
# WHY EA_ALLOW_SHORT_DATASET=1 EVERYWHERE.  Without it every input shorter than
# 1,000,000 samples exits at dataset_meets_minimum (utils.h:294-317) before any
# estimator runs, and a fuzzer would spend its whole budget on the intake refusal.
# The escape changes exactly one thing: the exit after the warning is skipped and
# nonCompliantShortDataset is set.  It adds no code path of its own.  So a
# memory-safety defect found inside an estimator here is in code a COMPLIANT
# (>= 1,000,000-sample) file executes too, with these named exceptions, which a
# compliant file can NEVER take and which are therefore escape-only:
#   - the decline branches for too little data: collision_test.h:47 (v < 2),
#     compression_test.h:128 (num_blocks < 1002), multi_mcw_test.h:16 (len <= 4096),
#     lag_test.h decline, multi_mmc_test.h:187 (len < 3) and :30, lz78y_test.h:137
#     (len < B+2) and :30, lrs_test.h:155/:390 (v == 0: no repeated substring --
#     impossible at 10^6 samples over <= 256 symbols);
#   - the IID chi-square "m = 1" failure path at tiny alphabets/counts;
#   - and for T5 specifically: the estimators run on the 17-sample block only under
#     the escape (the gate counts the LOADED samples); T5's compliant-reachable
#     content is the subset ARITHMETIC (offset, past-end, short last block), which
#     runs before the gate.
#   ea_restart (T8) has NO escape at restart_main.cpp:694, so T8 reaches read_file
#   and the post-read checks only; that is the point of T8 (the duplicate intake).
# triage.sh re-runs each unique crash on an input TILED to 1,000,000 bytes without
# the escape, which is the measured answer to "reachable with a compliant file?"
# for that input (and only for that input -- rule 18).
#
# T6 AND EA_TEST_RANDOM_SOURCE.  The task asked for EA_TEST_RANDOM_SOURCE to point
# at a fixed file so the permutation tests are deterministic.  It is set, but READ
# THE CODE: utils.h:794-810 seed() opens "/dev/urandom" by a literal string;
# EA_TEST_RANDOM_SOURCE is read only by TestRunUtils.h:129-130 and used only for
# writeJsonReport's temporary-file suffix (:478), which T6 never calls (no -o).  So
# the permutation verdict on a borderline input is nondeterministic by design
# (iid-permutation.md s.2.1), AFL will report lower "stability" for T6, and a T6
# crash that depends on the shuffle may not replay from its input alone.  No
# environment knob changes that without a code change, which this phase does not
# make.
#
# macOS NOTES.  (1) The crash reporter (com.apple.ReportCrash) is loaded on this
# host; afl-fuzz refuses to start with it ("Crash reporter detected") unless
# AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1.  Unloading it is better (faster crash
# handling, no .ips flood in ~/Library/Logs/DiagnosticReports):
#     launchctl unload -w /System/Library/LaunchAgents/com.apple.ReportCrash.plist
# run.sh prints which path it took.  (2) -m is a no-op on Darwin (RLIMIT_AS is not
# enforced for malloc); the asan variant gets -m none because afl-fuzz insists on
# it with ASan, and memory is bounded by ASan's hard_rss_limit_mb instead.
# (3) kern.sysv.shmmax is 4 MiB here, ample for these maps (recorded).
# (4) -V counts FUZZ time only; start-up (seed calibration) is extra.
#
# OUTPUTS: <FUZZ_DIR>/out/<T>/default/{queue,crashes,hangs,fuzzer_stats};
# logs/fuzz-<T>.log (afl-fuzz, AFL_NO_UI), logs/fuzz-preflight-<T>-*.log, and
# logs/fuzz/RUN-RECORD.md (the labelled record: binaries by sha256, seeds by
# manifest, pre-flight outcomes, per-target stats).  Then run triage.sh.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fuzz_common.sh"

FUZZ="$FUZZ_DIR_DEFAULT"
MINUTES="$MINUTES_DEFAULT"
TARGETS="$TARGET_IDS"
VARIANT_OVERRIDE=""
DRY=0; PREFLIGHT=1; PREFLIGHT_ONLY=0; FORCE=0
pos=0
while [ $# -gt 0 ]; do
    case "$1" in
        --targets) TARGETS="$(echo "$2" | tr ',' ' ')"; shift 2 ;;
        --targets=*) TARGETS="$(echo "${1#--targets=}" | tr ',' ' ')"; shift ;;
        --variant) VARIANT_OVERRIDE="$2"; shift 2 ;;
        --variant=*) VARIANT_OVERRIDE="${1#--variant=}"; shift ;;
        --dry-run) DRY=1; shift ;;
        --no-preflight) PREFLIGHT=0; shift ;;
        --preflight-only) PREFLIGHT_ONLY=1; shift ;;
        --force) FORCE=1; shift ;;
        -h|--help) sed -n '2,80p' "$0"; exit 0 ;;
        --*) die "unknown option $1" ;;
        *) pos=$((pos + 1)); if [ "$pos" -eq 1 ]; then FUZZ="$1"; elif [ "$pos" -eq 2 ]; then MINUTES="$1"; else die "too many positional arguments"; fi; shift ;;
    esac
done
case "$MINUTES" in ''|*[!0-9]*) die "MINUTES must be a positive integer (got '$MINUTES')" ;; esac
[ "$MINUTES" -ge 1 ] || die "MINUTES must be >= 1"
if [ "$MINUTES" -gt "$MINUTES_HARD_CAP" ]; then note "MINUTES $MINUTES exceeds the hard cap; using $MINUTES_HARD_CAP"; MINUTES="$MINUTES_HARD_CAP"; fi
for T in $TARGETS; do target_field "$T" tool >/dev/null; done
if [ -n "$VARIANT_OVERRIDE" ]; then case "$VARIANT_OVERRIDE" in plain|asan) ;; *) die "--variant must be plain or asan" ;; esac; fi

SEEDS="$FUZZ/seeds"
OUTROOT="$FUZZ/out"
WORK7="$FUZZ/work/T7"
DRIVER="$FUZZ_HARNESS_DIR/argv_driver.sh"
mkdir -p "$FUZZ_LOGS_DIR"
RUNREC="$FUZZ_LOGS_DIR/RUN-RECORD.md"

# ---- resolve the variant actually available for a target -------------------
variant_for() {
    local T=$1 v
    v="${VARIANT_OVERRIDE:-$(target_field "$T" variant)}"
    if [ "$(target_field "$T" tool)" = argv_driver ]; then
        [ -x "$FUZZ/bin/$v/ea_non_iid" ] || v=plain
    else
        [ -x "$FUZZ/bin/$v/$(target_field "$T" tool)" ] || v=plain
    fi
    echo "$v"
}
bin_for() {   # the executable afl-fuzz is given
    local T=$1 v=$2
    if [ "$(target_field "$T" tool)" = argv_driver ]; then echo "$DRIVER"; else echo "$FUZZ/bin/$v/$(target_field "$T" tool)"; fi
}
# the command array for a target with @@ replaced by $3 (prints one element per line)
cmd_lines() {
    local T=$1 v=$2 input=$3 a
    bin_for "$T" "$v"
    for a in $(target_field "$T" args); do
        if [ "$a" = "@@" ]; then printf '%s\n' "$input"; else printf '%s\n' "$a"; fi
    done
}
# environment for a target as "VAR=value" lines
env_lines() {
    local T=$1 v=$2
    echo "EA_ALLOW_SHORT_DATASET=1"; echo "OMP_NUM_THREADS=2"
    echo "AFL_SKIP_CPUFREQ=1"; echo "AFL_NO_AFFINITY=1"; echo "AFL_NO_UI=1"; echo "AFL_AUTORESUME=1"
    echo "AFL_CRASHING_SEEDS_AS_NEW_CRASH=1"
    [ "$REPORTCRASH_LOADED" = yes ] && echo "AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1"
    if [ "$v" = asan ]; then echo "ASAN_OPTIONS=$ASAN_OPTIONS_FUZZ"; echo "UBSAN_OPTIONS=$UBSAN_OPTIONS_FUZZ"; fi
    case "$T" in
        T6) echo "EA_TEST_RANDOM_SOURCE=$SEEDS/fixture/random-source-64k.bin" ;;
        T7) echo "AFL_NO_FORKSRV=1"; echo "AFL_SKIP_BIN_CHECK=1"; echo "AFL_MAP_SIZE=$MAPSIZE7"
            echo "FUZZ_DRIVER_BIN_DIR=$FUZZ/bin/$v"; echo "FUZZ_DRIVER_WORK=$WORK7" ;;
    esac
}
# run a target's command once on an input, output to files; echo the rc
run_once() {   # T variant input outprefix timeout_secs
    local T=$1 v=$2 input=$3 pre=$4 to=$5 rc=0
    local -a cmd envs
    cmd=(); while IFS= read -r l; do cmd+=("$l"); done < <(cmd_lines "$T" "$v" "$input")
    envs=(); while IFS= read -r l; do envs+=("$l"); done < <(env_lines "$T" "$v")
    ( cd "$FUZZ" && run_with_timeout "$to" env "${envs[@]}" "${cmd[@]}" ) < /dev/null > "$pre.out" 2> "$pre.err" || rc=$?
    echo "$rc" > "$pre.rc"
    echo "$rc"
}

# ---- preconditions (a dry run only reports them) ------------------------------
req() { if [ "$DRY" -eq 1 ]; then note "dry-run: would refuse: $*"; else die "$*"; fi; }
need_cmd afl-fuzz "brew install afl++"
need_cmd afl-showmap ""
[ -f "$FUZZ/BUILD-RECORD.txt" ] || req "no $FUZZ/BUILD-RECORD.txt -- run build.sh first"
if [ -f "$FUZZ/BUILD-RECORD.txt" ]; then grep -q "build_result: OK" "$FUZZ/BUILD-RECORD.txt" || req "BUILD-RECORD.txt does not say build_result: OK -- fix the build first"; fi
[ -f "$SEEDS/MANIFEST.txt" ] || req "no $SEEDS/MANIFEST.txt -- run seeds.py --out $SEEDS first"
[ -x "$VENV_PY" ] || req "python not found at $VENV_PY"
[ -x "$DRIVER" ] || req "driver not executable: $DRIVER"
busy="$(heavy_jobs_running)"
if [ -n "$busy" ] && [ "$FORCE" -ne 1 ] && [ "$DRY" -ne 1 ]; then
    echo "Another heavy job appears to be running (brief rule 4):" >&2; echo "$busy" >&2
    die "refusing to fuzz; --force only after checking the slot is free"
fi
if launchctl list 2>/dev/null | grep -q '\.ReportCrash'; then REPORTCRASH_LOADED=yes; else REPORTCRASH_LOADED=no; fi
MAPSIZE7=65536
AFL_RT_NOTES=""
for t in $TOOLS; do
    for v in plain asan; do
        b="$FUZZ/bin/$v/$t"; [ -x "$b" ] || continue
        m="$(afl_map_size_of "$b")"
        if [ -n "$m" ]; then
            [ "$m" -gt "$MAPSIZE7" ] && MAPSIZE7="$m"
            AFL_RT_NOTES="$AFL_RT_NOTES $v/$t=map:$m"
        else
            AFL_RT_NOTES="$AFL_RT_NOTES $v/$t=NO-AFL-RUNTIME"
        fi
    done
done

# ---- the plan ----------------------------------------------------------------
plan_table() {
    printf '%-3s %-11s %-24s %-5s %-7s %-6s %-6s %-5s  %s\n' T tool args seeds var min -G -t note
    local total=0
    for T in $TARGETS; do
        v="$(variant_for "$T")"; m="$(target_minutes_capped "$T" "$MINUTES")"; total=$((total + m))
        printf '%-3s %-11s %-24s %-5s %-7s %-6s %-6s %-5s  %s\n' "$T" "$(target_field "$T" tool)" "$(target_field "$T" args)" \
            "$(target_field "$T" seeds)" "$v" "$m" "$(target_field "$T" maxlen)" "$(target_field "$T" timeout)" "$(target_field "$T" note | cut -c1-70)..."
    done
    echo "total fuzz minutes: $total (plus ~1 min start-up per target; -V counts fuzz time only)"
}
if [ "$DRY" -eq 1 ]; then
    echo "DRY RUN -- plan for FUZZ_DIR=$FUZZ, per-target cap $MINUTES min, ReportCrash loaded: $REPORTCRASH_LOADED, AFL_MAP_SIZE for T7: $MAPSIZE7"
    plan_table
    exit 0
fi

# ---- the record header -------------------------------------------------------
{
    echo "# RUN-RECORD -- AFL++ campaign, 2026-11-07 aggressive audit"
    echo
    echo "- started_utc: $(now_utc)"
    echo "- fuzz_dir: \`$FUZZ\`"
    echo "- host: $(uname -m) $(sw_vers -productVersion 2>/dev/null || uname -r); $(sysctl -n hw.ncpu) CPUs; $(( $(sysctl -n hw.memsize) / 1073741824 )) GB; load $(sysctl -n vm.loadavg)"
    echo "- afl: $(afl-fuzz -h 2>&1 | head -1 | sed 's/\x1b\[[0-9;]*m//g')"
    echo "- kern.sysv.shmmax: $(sysctl -n kern.sysv.shmmax); AFL_MAP_SIZE for T7: $MAPSIZE7"
    echo "- AFL runtime per binary (AFL_DUMP_MAP_SIZE probe):$AFL_RT_NOTES"
    echo "- ReportCrash loaded: $REPORTCRASH_LOADED $([ "$REPORTCRASH_LOADED" = yes ] && echo '(AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 set; crash handling is slower; consider: launchctl unload -w /System/Library/LaunchAgents/com.apple.ReportCrash.plist)')"
    echo "- per-target cap: $MINUTES min; targets: $TARGETS; variant override: ${VARIANT_OVERRIDE:-none}"
    echo "- EA_ALLOW_SHORT_DATASET=1 and OMP_NUM_THREADS=2 on EVERY execution: nothing here is a compliant assessment."
    echo "- seeds manifest: \`$SEEDS/MANIFEST.txt\` sha256 $(sha256_of "$SEEDS/MANIFEST.txt")"
    echo
    echo "## binaries (instrument rule 4)"
    echo
    echo "| role | path | sha256 |"
    echo "|---|---|---|"
    for v in plain asan; do for t in $TOOLS; do b="$FUZZ/bin/$v/$t"; [ -x "$b" ] && echo "| fuzz $v | \`$b\` | \`$(sha256_of "$b")\` |"; done; done
    for t in $TOOLS; do [ -f "$CPP_DIR/$t" ] && echo "| production (NOT fuzzed; for contrast) | \`cpp/$t\` | \`$(sha256_of "$CPP_DIR/$t")\` |"; done
    echo "| driver | \`$DRIVER\` | \`$(sha256_of "$DRIVER")\` |"
    echo
    echo "## plan"
    echo
    echo '```'
    plan_table
    echo '```'
    echo
} > "$RUNREC"
note "record: $RUNREC"

# ---- T7 work dir and fixtures --------------------------------------------------
mkdir -p "$WORK7/out" "$OUTROOT"
for f in bits-2000.bin bytes-2000.bin empty.bin; do cp "$SEEDS/fixture/$f" "$WORK7/$f"; done
rm -f "$WORK7/does-not-exist.bin"
( cd "$WORK7" && shasum -a 256 bits-2000.bin bytes-2000.bin empty.bin ) > "$WORK7/FIXTURE-SHA256.before.txt"

# ---- seeds check (the corpus is what the manifest says it is) -----------------
{
    echo "## seeds check"
    echo
    echo '```'
    "$VENV_PY" "$FUZZ_HARNESS_DIR/seeds.py" --out "$SEEDS" --check 2>&1 || { echo "SEEDS CHECK FAILED"; }
    echo '```'
    echo
} >> "$RUNREC"
"$VENV_PY" "$FUZZ_HARNESS_DIR/seeds.py" --out "$SEEDS" --check >/dev/null 2>&1 || die "seeds.py --check failed; see $RUNREC"

# ---- pre-flight ----------------------------------------------------------------
SKIP_LIST=""
if [ "$PREFLIGHT" -eq 1 ]; then
    { echo "## pre-flight (baseline accepted, instrument live, every seed run once, edge cases)"; echo; } >> "$RUNREC"
    for T in $TARGETS; do
        v="$(variant_for "$T")"; tool="$(target_field "$T" tool)"; skip=""
        pre="$LOGS_DIR/fuzz-preflight-$T"
        good="$SEEDS/$(target_field "$T" good_seed)"
        exp="$(target_field "$T" expect_rc)"
        # (a) baseline
        rc="$(run_once "$T" "$v" "$good" "$pre-baseline" 60)"
        last="$(tail -1 "$pre-baseline.out" 2>/dev/null | cut -c1-100)"
        base="rc=$rc (expected $exp); last stdout line: '$last'"
        if [ "$rc" != "$exp" ]; then skip="baseline rc $rc != expected $exp"; fi
        if [ "$T" = T8 ] && ! grep -q "does not contain 1000000 samples" "$pre-baseline.out"; then skip="${skip:+$skip; }T8 baseline refused for a reason other than the matrix length"; fi
        # (a') T7 driver self-test + mutation-built negative control
        if [ "$tool" = argv_driver ]; then
            FUZZ_DRIVER_PRINT=1 FUZZ_DRIVER_BIN_DIR="$FUZZ/bin/$v" FUZZ_DRIVER_WORK="$WORK7" "$DRIVER" "$good" > "$pre-driver-print.log" 2>&1 || true
            expect_print="$(printf 'TOOL ea_non_iid\nARG -i\nARG -a\nARG %s\nARG 8\n' "$WORK7/bits-2000.bin")"
            if [ "$(cat "$pre-driver-print.log")" != "$expect_print" ]; then skip="${skip:+$skip; }driver mapped the good seed differently than expected (see $pre-driver-print.log)"; fi
            printf '%s\n' "-i" "-a" "/etc/passwd" "8" > "$WORK7/neg-slash.txt"
            FUZZ_DRIVER_PRINT=1 FUZZ_DRIVER_BIN_DIR="$FUZZ/bin/$v" FUZZ_DRIVER_WORK="$WORK7" "$DRIVER" "$WORK7/neg-slash.txt" > "$pre-driver-neg.log" 2>&1 || true
            if ! grep -q '^REJECTED' "$pre-driver-neg.log"; then skip="${skip:+$skip; }driver did NOT reject a path-shaped token (negative control failed)"; fi
            base="$base; driver print-mode matched; slash-token negative control: $(head -1 "$pre-driver-neg.log")"
        fi
        # (b) instrumentation liveness on the good seed
        envs=(); while IFS= read -r l; do envs+=("$l"); done < <(env_lines "$T" "$v")
        cmd=(); while IFS= read -r l; do cmd+=("$l"); done < <(cmd_lines "$T" "$v" "$good")
        smo=(-q -t 20000 -o "$OUTROOT/$T.showmap"); [ "$v" = asan ] && smo+=(-m none)
        mkdir -p "$OUTROOT"
        ( cd "$FUZZ" && env "${envs[@]}" afl-showmap "${smo[@]}" -- "${cmd[@]}" ) > "$pre-showmap.log" 2>&1 || true
        tuples=0; [ -f "$OUTROOT/$T.showmap" ] && tuples="$(grep -c . "$OUTROOT/$T.showmap" || true)"
        [ "$tuples" -gt 0 ] || skip="${skip:+$skip; }afl-showmap saw 0 tuples (instrumentation not live for this command)"
        # (c) every seed once
        # exit statuses: 0 assessed, 1 IID verdict failed, 255 the tool's refusal
        # (exit(-1)), 124 our cap, 128+n a signal (134 SIGABRT = an assert fired)
        seedlog="$pre-seeds.log"; : > "$seedlog"; nseed=0; nsig=0; nto=0; nref=0; nok=0
        mkdir -p "$OUTROOT/$T/seed-crashes"
        for s in "$SEEDS/$(target_field "$T" seeds)"/*; do
            [ -f "$s" ] || continue
            nseed=$((nseed + 1))
            src="$(run_once "$T" "$v" "$s" "$FUZZ/work/seedrun" 30)"
            what="exit"
            case "$src" in
                0) nok=$((nok + 1)); what="assessed" ;;
                255) nref=$((nref + 1)); what="refused" ;;
                124) nto=$((nto + 1)); what="TIMEOUT" ;;
                1[3-9][0-9]|2[0-4][0-9]|25[0-4]|12[89]) nsig=$((nsig + 1)); what="SIGNAL $((src - 128))"
                    cp "$s" "$OUTROOT/$T/seed-crashes/"; cp "$FUZZ/work/seedrun.err" "$OUTROOT/$T/seed-crashes/$(basename "$s").err"; cp "$FUZZ/work/seedrun.out" "$OUTROOT/$T/seed-crashes/$(basename "$s").out" ;;
            esac
            printf '%-40s rc=%-4s %s\n' "$(basename "$s")" "$src" "$what" >> "$seedlog"
        done
        # (d) the empty file, once (afl-fuzz skips empty seeds)
        edge="n/a"
        if [ "$tool" != argv_driver ]; then
            erc="$(run_once "$T" "$v" "$SEEDS/edge/empty.bin" "$pre-edge-empty" 30)"
            if grep -q "is empty" "$pre-edge-empty.out" 2>/dev/null; then ewhy="the 'is empty' refusal line is present"
            elif grep -q "at or past the end" "$pre-edge-empty.out" 2>/dev/null; then ewhy="refused as past-end (utils.h:385; the expected refusal under -l, which runs before the empty check)"
            else ewhy="NEITHER 'is empty' NOR 'at or past the end' in stdout -- refused for another reason, or not refused"; fi
            edge="empty.bin rc=$erc (expected 255); $ewhy"
        fi
        {
            echo "### $T ($tool, $v)"
            echo
            echo "- baseline (\`$(basename "$good")\`): $base"
            echo "- instrumentation: afl-showmap tuples = $tuples"
            echo "- seeds run once: $nseed seeds: $nok assessed (exit 0), $nref refused (exit 255), $nsig exited by SIGNAL (input + stderr + stdout copied to \`out/$T/seed-crashes/\`; triage.sh re-runs them), $nto hit the 30 s cap; per-seed status in \`logs/$(basename "$seedlog")\`"
            echo "- edge: $edge"
            if [ -n "$skip" ]; then echo "- **SKIPPED: $skip**"; else echo "- pre-flight: OK"; fi
            echo
        } >> "$RUNREC"
        [ -n "$skip" ] && SKIP_LIST="$SKIP_LIST $T"
        note "preflight $T: $([ -n "$skip" ] && echo "SKIP ($skip)" || echo "ok, tuples=$tuples, seeds=$nseed assessed=$nok refused=$nref signal=$nsig")"
    done
fi

# ---- the campaign --------------------------------------------------------------
if [ "$PREFLIGHT_ONLY" -eq 1 ]; then
    { echo "## campaign"; echo; echo "NOT RUN: --preflight-only. Targets that would have been skipped:${SKIP_LIST:- none}."; echo; echo "finished_utc: $(now_utc)"; } >> "$RUNREC"
    note "preflight-only: no fuzzer started; record $RUNREC"
    exit 0
fi
{ echo "## campaign"; echo; echo "| T | variant | minutes | wall s | afl rc | execs | execs/s | corpus | crashes | hangs | stability | map cvg | log |"; echo "|---|---|---|---|---|---|---|---|---|---|---|---|---|"; } >> "$RUNREC"
for T in $TARGETS; do
    case " $SKIP_LIST " in *" $T "*) echo "| $T | - | - | - | SKIPPED (pre-flight) | | | | | | | | |" >> "$RUNREC"; continue ;; esac
    v="$(variant_for "$T")"; tool="$(target_field "$T" tool)"
    mins="$(target_minutes_capped "$T" "$MINUTES")"; secs=$((mins * 60))
    out="$OUTROOT/$T"; mkdir -p "$out"
    envs=(); while IFS= read -r l; do envs+=("$l"); done < <(env_lines "$T" "$v")
    cmd=(); while IFS= read -r l; do cmd+=("$l"); done < <(cmd_lines "$T" "$v" "@@")
    dicts=()
    if [ "$tool" = argv_driver ]; then
        dicts+=(-x "$SEEDS/dict/argv.dict")
        for d in "$FUZZ/dict"/auto-*.dict; do [ -f "$d" ] && [ "${#dicts[@]}" -lt 8 ] && dicts+=(-x "$d"); done
    else
        dicts+=(-x "$SEEDS/dict/bytes.dict")
        [ -f "$FUZZ/dict/auto-$tool.dict" ] && dicts+=(-x "$FUZZ/dict/auto-$tool.dict")
    fi
    mem=(); [ "$v" = asan ] && mem=(-m none)
    log="$LOGS_DIR/fuzz-$T.log"
    {
        echo "# afl-fuzz $T started $(now_utc)"
        echo "# env: ${envs[*]}"
        echo "# cmd: afl-fuzz -i $SEEDS/$(target_field "$T" seeds) -o $out -V $secs -t $(target_field "$T" timeout) -G $(target_field "$T" maxlen) -s $AFL_RNG_SEED -T $T ${mem[*]} ${dicts[*]} -- ${cmd[*]}"
    } > "$log"
    note "fuzzing $T ($tool, $v) for $mins min -> $out"
    t0=$(date +%s); rc=0
    ( cd "$FUZZ" && env "${envs[@]}" afl-fuzz -i "$SEEDS/$(target_field "$T" seeds)" -o "$out" -V "$secs" \
        -t "$(target_field "$T" timeout)" -G "$(target_field "$T" maxlen)" -s "$AFL_RNG_SEED" -T "$T" \
        "${mem[@]}" "${dicts[@]}" -- "${cmd[@]}" ) >> "$log" 2>&1 || rc=$?
    t1=$(date +%s)
    st="$out/default/fuzzer_stats"
    stat_of() { grep -m1 "^$1 *:" "$st" 2>/dev/null | sed 's/^[^:]*: *//' || true; }
    ncr="$(ls "$out/default/crashes" 2>/dev/null | grep -c '^id:' || true)"
    nhg="$(ls "$out/default/hangs" 2>/dev/null | grep -c '^id:' || true)"
    echo "| $T | $v | $mins | $((t1 - t0)) | $rc | $(stat_of execs_done) | $(stat_of execs_per_sec) | $(stat_of corpus_count) | $ncr | $nhg | $(stat_of stability) | $(stat_of bitmap_cvg) | \`logs/$(basename "$log")\` |" >> "$RUNREC"
    note "  done: rc=$rc execs=$(stat_of execs_done) crashes=$ncr hangs=$nhg"
done

# ---- T7 fixture integrity (an A05 bypass would show here) -------------------------
case " $TARGETS " in *" T7 "*)
    ( cd "$WORK7" && shasum -a 256 bits-2000.bin bytes-2000.bin empty.bin ) > "$WORK7/FIXTURE-SHA256.after.txt"
    {
        echo
        echo "## T7 fixture integrity"
        echo
        if diff -q "$WORK7/FIXTURE-SHA256.before.txt" "$WORK7/FIXTURE-SHA256.after.txt" >/dev/null; then
            echo "- fixtures unchanged after T7 (sha256 before == after): the -o aliasing guard (A05) held for every vector tried."
        else
            echo "- **FIXTURES CHANGED during T7** -- a vector wrote to an input path. A05 bypass candidate. Diff:"
            echo '```'; diff "$WORK7/FIXTURE-SHA256.before.txt" "$WORK7/FIXTURE-SHA256.after.txt" || true; echo '```'
        fi
    } >> "$RUNREC" ;;
esac

{
    echo
    echo "## what this record cannot see (rule 18)"
    echo
    echo "- A seed that AFL skipped silently (empty files) is covered only by the one-shot edge run above."
    echo "- The heavy-job check is a process-name heuristic; it cannot see a heavy job it does not match."
    echo "- T6's permutation verdict is nondeterministic (seed() reads /dev/urandom; EA_TEST_RANDOM_SOURCE does not reach it)."
    echo "- A crash here is under Homebrew clang 23 instrumentation; it is not a finding until triage.sh reproduces it under the Apple-clang sanitizer build or the production binary."
    echo "- Inputs are capped at -G bytes per target; a defect needing a longer input is out of reach of this campaign."
    echo
    echo "finished_utc: $(now_utc)"
    echo
    echo "Next: \`harness/fuzz/triage.sh $FUZZ\` (writes logs/fuzz/TRIAGE.md)."
} >> "$RUNREC"
note "campaign finished; record $RUNREC"
