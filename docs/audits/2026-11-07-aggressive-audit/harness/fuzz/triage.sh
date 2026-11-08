#!/bin/bash
# triage.sh -- re-run every crash and hang the AFL++ campaign saved, classify, dedup
# by top stack frame, and write logs/fuzz/TRIAGE.md.
#
#   usage: triage.sh [FUZZ_DIR] [--san-dir DIR] [--no-compliant-check] [--max-compliant N]
#                    [--tmin] [--force]
#     --san-dir DIR         directory holding the Apple-clang asan_ubsan builds from
#                           harness/sanitizers (ea_non_iid, ea_iid, ea_restart; the
#                           names ea_<tool>.asan_ubsan / -asan_ubsan / _asan_ubsan are
#                           also accepted).  Default search order: $SAN_DIR, then
#                           <scratchpad>/san/asan_ubsan (where harness/sanitizers/build.sh
#                           puts them: SAN_DIR/<variant>/ea_<tool>), then
#                           <scratchpad>/sanitizers/asan_ubsan, <scratchpad>/sanitizers,
#                           <audit>/harness/sanitizers/bin/asan_ubsan, <audit>/harness/sanitizers/bin
#     --no-compliant-check  skip the tiled-to-1,000,000 re-run (a heavy run per unique key)
#     --max-compliant N     at most N unique keys get the tiled re-run (default 6)
#     --tmin                also minimise one input per unique key with afl-tmin (slow)
#
# EVERY INPUT IS RE-RUN THREE WAYS, each to its own stdout/stderr/rc files under
# logs/fuzz/triage/<T>/<kind>/<id>.<build>.{out,err,rc} (never piped; rule 17):
#   san   the Apple-clang asan_ubsan build  -- the authoritative, symbolised report
#   fuzz  the Homebrew-clang AFL build that found it (asan variant if built, else plain)
#   prod  cpp/<tool>, the production binary -- does the SHIPPED build crash on it?
# The argv is the target table's (fuzz_common.sh), so what is re-run is what was
# fuzzed; T7 inputs go back through argv_driver.sh with FUZZ_DRIVER_BIN_DIR pointed
# at each build in turn.
#
# CLASSIFICATION (labelled reads of the .err/.out files; instrument rule 5):
#   ASAN:<kind>@<frame0>         "ERROR: AddressSanitizer: <kind>" + first "#0 ... in <fn> <file:line>"
#   UBSAN:<kind>@<file:line>     "<file>:<line>:<col>: runtime error: <kind>"
#   ASSERT@<fn>@<file>:<line>    "Assertion failed: (...), function <fn>, file <file>, line <n>."
#   SIGNAL:<n>                   exit status >= 128 with none of the above (prod has no reports)
#   TIMEOUT                      the cap fired (exit 124)
#   EXIT:<n>                     ran to completion -- NOT reproduced; the last stdout line is quoted
#                                (255 is the tools' own refusal status, exit(-1); not a signal)
# The dedup key is the san classification when a san build exists, else the fuzz one.
#
# "REACHABLE WITH A COMPLIANT FILE?"  For each unique key (file targets only) the
# first input is TILED to exactly 1,000,000 bytes and re-run under the san build
# WITHOUT EA_ALLOW_SHORT_DATASET (300 s cap; 900 s for T8, whose 1,000,000-byte input
# runs the whole restart assessment).  A crash there is reachable by a compliant
# file: YES.  Anything else is NOT SHOWN -- tiling changes the data's period and
# can mask a size-dependent defect (rule 18) -- and the record says what the tiled
# run did instead.  This is a heavy run per key, serialised, and skipped (with the
# reason) if another heavy job is visible.
#
# The paths the escape alone reaches (decline branches for too little data) are
# listed in run.sh's header and repeated in TRIAGE.md so a reader can tell an
# escape-only abort from a shipped-path defect.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fuzz_common.sh"

FUZZ="$FUZZ_DIR_DEFAULT"
SAN_DIR_OPT="${SAN_DIR:-}"
COMPLIANT=1; MAXC=6; TMIN=0; FORCE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --san-dir) SAN_DIR_OPT="$2"; shift 2 ;;
        --san-dir=*) SAN_DIR_OPT="${1#--san-dir=}"; shift ;;
        --no-compliant-check) COMPLIANT=0; shift ;;
        --max-compliant) MAXC="$2"; shift 2 ;;
        --tmin) TMIN=1; shift ;;
        --force) FORCE=1; shift ;;
        -h|--help) sed -n '2,50p' "$0"; exit 0 ;;
        --*) die "unknown option $1" ;;
        *) FUZZ="$1"; shift ;;
    esac
done
[ -d "$FUZZ/out" ] || die "no $FUZZ/out -- run run.sh first"
[ -x "$VENV_PY" ] || die "python not found at $VENV_PY"
DRIVER="$FUZZ_HARNESS_DIR/argv_driver.sh"
WORK7="$FUZZ/work/T7"
TRI="$FUZZ_LOGS_DIR/triage"; mkdir -p "$TRI"
OUTMD="$FUZZ_LOGS_DIR/TRIAGE.md"

# ---- builds -------------------------------------------------------------------
find_san_bin() {   # tool -> path or empty; prints the search to stderr-ish log
    local t=$1 d n
    for d in "$SAN_DIR_OPT" "$SCRATCHPAD_DEFAULT/san/asan_ubsan" \
             "$SCRATCHPAD_DEFAULT/sanitizers/asan_ubsan" "$SCRATCHPAD_DEFAULT/sanitizers" \
             "$AUDIT_DIR/harness/sanitizers/bin/asan_ubsan" "$AUDIT_DIR/harness/sanitizers/bin"; do
        [ -n "$d" ] && [ -d "$d" ] || continue
        for n in "$t" "$t.asan_ubsan" "$t-asan_ubsan" "${t}_asan_ubsan"; do
            [ -x "$d/$n" ] && { echo "$d/$n"; return; }
        done
    done
    echo ""
}
SAN_SEARCHED="${SAN_DIR_OPT:+$SAN_DIR_OPT, }$SCRATCHPAD_DEFAULT/san/asan_ubsan, $SCRATCHPAD_DEFAULT/sanitizers/asan_ubsan, $SCRATCHPAD_DEFAULT/sanitizers, $AUDIT_DIR/harness/sanitizers/bin/asan_ubsan, $AUDIT_DIR/harness/sanitizers/bin"
SAN_non_iid="$(find_san_bin ea_non_iid)"; SAN_iid="$(find_san_bin ea_iid)"; SAN_restart="$(find_san_bin ea_restart)"
san_bin() { case "$1" in ea_non_iid) echo "$SAN_non_iid" ;; ea_iid) echo "$SAN_iid" ;; ea_restart) echo "$SAN_restart" ;; esac; }
FUZZ_VARIANT=plain; [ -x "$FUZZ/bin/asan/ea_non_iid" ] && FUZZ_VARIANT=asan
fuzz_bin() { echo "$FUZZ/bin/$FUZZ_VARIANT/$1"; }
prod_bin() { echo "$CPP_DIR/$1"; }
# a directory that holds all three san binaries under their plain names (for the driver)
SAN_DRIVER_DIR=""
if [ -n "$SAN_non_iid" ] && [ -n "$SAN_iid" ] && [ -n "$SAN_restart" ]; then
    SAN_DRIVER_DIR="$FUZZ/work/san-bin"; mkdir -p "$SAN_DRIVER_DIR"
    ln -sf "$SAN_non_iid" "$SAN_DRIVER_DIR/ea_non_iid"; ln -sf "$SAN_iid" "$SAN_DRIVER_DIR/ea_iid"; ln -sf "$SAN_restart" "$SAN_DRIVER_DIR/ea_restart"
fi

# ---- one execution ------------------------------------------------------------
# exec_case T build input prefix timeout [escape=1|0]  -> echoes rc
exec_case() {
    local T=$1 build=$2 input=$3 pre=$4 to=$5 escape=${6:-1} tool bin rc=0 a
    tool="$(target_field "$T" tool)"
    local -a envs cmd
    envs=(OMP_NUM_THREADS=2)
    [ "$escape" = 1 ] && envs+=(EA_ALLOW_SHORT_DATASET=1)
    case "$build" in
        san)  envs+=("ASAN_OPTIONS=$ASAN_OPTIONS_TRIAGE" "UBSAN_OPTIONS=$UBSAN_OPTIONS_TRIAGE") ;;
        fuzz) envs+=("ASAN_OPTIONS=$ASAN_OPTIONS_TRIAGE" "UBSAN_OPTIONS=$UBSAN_OPTIONS_TRIAGE")
              [ -x /opt/homebrew/opt/llvm/bin/llvm-symbolizer ] && envs+=(ASAN_SYMBOLIZER_PATH=/opt/homebrew/opt/llvm/bin/llvm-symbolizer) ;;
    esac
    if [ "$tool" = argv_driver ]; then
        local bindir
        case "$build" in san) bindir="$SAN_DRIVER_DIR" ;; fuzz) bindir="$FUZZ/bin/$FUZZ_VARIANT" ;; prod) bindir="$CPP_DIR" ;; esac
        [ -n "$bindir" ] || { echo "NA" > "$pre.rc"; echo NA; return; }
        envs+=("FUZZ_DRIVER_BIN_DIR=$bindir" "FUZZ_DRIVER_WORK=$WORK7")
        cmd=("$DRIVER" "$input")
    else
        case "$build" in san) bin="$(san_bin "$tool")" ;; fuzz) bin="$(fuzz_bin "$tool")" ;; prod) bin="$(prod_bin "$tool")" ;; esac
        [ -n "$bin" ] && [ -x "$bin" ] || { echo "NA" > "$pre.rc"; echo NA; return; }
        cmd=("$bin")
        for a in $(target_field "$T" args); do if [ "$a" = "@@" ]; then cmd+=("$input"); else cmd+=("$a"); fi; done
    fi
    ( cd "$FUZZ" && run_with_timeout "$to" env "${envs[@]}" "${cmd[@]}" ) < /dev/null > "$pre.out" 2> "$pre.err" || rc=$?
    echo "$rc" > "$pre.rc"; echo "$rc"
}

# classify() lives in fuzz_common.sh so it can be unit-tested by sourcing.

# ---- collect inputs ----------------------------------------------------------------
INPUTS="$TRI/inputs.list"; : > "$INPUTS"
for T in $TARGET_IDS; do
    for kind in crashes hangs; do
        for f in "$FUZZ/out/$T/default/$kind"/id:*; do [ -f "$f" ] && printf '%s|%s|%s\n' "$T" "$kind" "$f" >> "$INPUTS"; done
    done
    for f in "$FUZZ/out/$T/seed-crashes"/*; do
        [ -f "$f" ] || continue; case "$f" in *.err) continue ;; esac
        printf '%s|%s|%s\n' "$T" "seed-crashes" "$f" >> "$INPUTS"
    done
done
NIN="$(grep -c . "$INPUTS" || true)"
note "triage: $NIN inputs; san build: ${SAN_non_iid:-NOT FOUND}; fuzz variant: $FUZZ_VARIANT"

# ---- run them ---------------------------------------------------------------------
ROWS="$TRI/rows.tsv"; : > "$ROWS"    # T kind path size san_class san_key san_detail fuzz_class fuzz_key fuzz_detail prod_class prod_detail primary_key
while IFS='|' read -r T kind path; do
    [ -n "$T" ] || continue
    id="$(printf '%s' "$(basename "$path")" | tr -c 'A-Za-z0-9._-' '_')"
    d="$TRI/$T/$kind"; mkdir -p "$d"
    to=30; [ "$kind" = hangs ] && to=90
    size="$(file_size "$path")"
    rs="$(exec_case "$T" san  "$path" "$d/$id.san"  "$to")"; cs="$(classify "$d/$id.san"  "$rs")"
    rf="$(exec_case "$T" fuzz "$path" "$d/$id.fuzz" "$to")"; cf="$(classify "$d/$id.fuzz" "$rf")"
    rp="$(exec_case "$T" prod "$path" "$d/$id.prod" "$to")"; cp_="$(classify "$d/$id.prod" "$rp")"
    sk="$(printf '%s' "$cs" | cut -d'|' -f2)"; fk="$(printf '%s' "$cf" | cut -d'|' -f2)"
    primary="$sk"; [ "$primary" = NA ] && primary="$fk"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$T" "$kind" "$path" "$size" \
        "$(printf '%s' "$cs" | cut -d'|' -f1)" "$sk" "$(printf '%s' "$cs" | cut -d'|' -f3)" \
        "$(printf '%s' "$cf" | cut -d'|' -f1)" "$fk" "$(printf '%s' "$cf" | cut -d'|' -f3)" \
        "$(printf '%s' "$cp_" | cut -d'|' -f1)" "$(printf '%s' "$cp_" | cut -d'|' -f3)" "$primary" >> "$ROWS"
done < "$INPUTS"

# ---- dedup by primary key -----------------------------------------------------------
KEYS="$TRI/keys.tsv"; : > "$KEYS"   # key count targets first_path first_T
if [ -s "$ROWS" ]; then
    awk -F'\t' '{ k=$13; c[k]++; if (!(k in first)) { first[k]=$3; ft[k]=$1 } if (index(t[k], $1)==0) t[k]=t[k] " " $1 } END { for (k in c) printf "%s\t%d\t%s\t%s\t%s\n", k, c[k], t[k], first[k], ft[k] }' "$ROWS" | sort -t$'\t' -k2,2nr > "$KEYS"
fi
NKEYS="$(grep -c . "$KEYS" || true)"

# ---- compliant-size re-run per unique key --------------------------------------------
COMPL="$TRI/compliant.tsv"; : > "$COMPL"   # key outcome detail
if [ "$COMPLIANT" -eq 1 ] && [ "$NKEYS" -gt 0 ]; then
    n=0
    while IFS=$'\t' read -r key count targets first firstT; do
        [ -n "$key" ] || continue
        case "$key" in EXIT:*|NA) printf '%s\t%s\t%s\n' "$key" "not run" "key is not a crash" >> "$COMPL"; continue ;; esac
        tool="$(target_field "$firstT" tool)"
        if [ "$tool" = argv_driver ]; then printf '%s\t%s\t%s\n' "$key" "n/a" "argv target: the input is a command line, not data" >> "$COMPL"; continue; fi
        if [ "$n" -ge "$MAXC" ]; then printf '%s\t%s\t%s\n' "$key" "not run" "--max-compliant $MAXC reached" >> "$COMPL"; continue; fi
        if [ "$(file_size "$first")" -eq 0 ]; then printf '%s\t%s\t%s\n' "$key" "not run" "empty input cannot be tiled" >> "$COMPL"; continue; fi
        busy="$(heavy_jobs_running)"
        if [ -n "$busy" ] && [ "$FORCE" -ne 1 ]; then printf '%s\t%s\t%s\n' "$key" "SKIPPED" "heavy slot busy: $(printf '%s' "$busy" | head -1 | cut -c1-80)" >> "$COMPL"; continue; fi
        n=$((n + 1))
        tiled="$TRI/tiled-$(printf '%s' "$key" | tr -c 'A-Za-z0-9' '_' | cut -c1-60).bin"
        "$VENV_PY" - "$first" "$tiled" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
b = open(src, "rb").read()
n = 1000000
reps = (n + len(b) - 1) // len(b)
open(dst, "wb").write((b * reps)[:n])
PY
        build=san; [ -n "$(san_bin "$tool")" ] || build=fuzz
        to=300; [ "$firstT" = T8 ] && to=900
        pre="$TRI/tiled-$(printf '%s' "$key" | tr -c 'A-Za-z0-9' '_' | cut -c1-60)"
        rc="$(exec_case "$firstT" "$build" "$tiled" "$pre" "$to" 0)"
        cl="$(classify "$pre" "$rc")"
        extra=""
        [ "$firstT" = T5 ] && extra=" (T5 loads 17 samples whatever the file size: the gate refuses it without the escape, so this check cannot reach the estimator path for T5)"
        printf '%s\t%s\t%s\n' "$key" "$(printf '%s' "$cl" | cut -d'|' -f1)" "$build build, tiled to 1,000,000 bytes, no escape, cap ${to}s: $(printf '%s' "$cl" | cut -d'|' -f3)$extra" >> "$COMPL"
    done < "$KEYS"
fi

# ---- optional afl-tmin ----------------------------------------------------------------
TMINS="$TRI/tmin.tsv"; : > "$TMINS"
if [ "$TMIN" -eq 1 ] && [ "$NKEYS" -gt 0 ]; then
    while IFS=$'\t' read -r key count targets first firstT; do
        [ -n "$key" ] || continue; case "$key" in EXIT:*|NA|TIMEOUT) continue ;; esac
        tool="$(target_field "$firstT" tool)"; [ "$tool" = argv_driver ] && continue
        bin="$(fuzz_bin "$tool")"; min="$TRI/min-$(printf '%s' "$key" | tr -c 'A-Za-z0-9' '_' | cut -c1-60).bin"
        args=(); for a in $(target_field "$firstT" args); do if [ "$a" = "@@" ]; then args+=("@@"); else args+=("$a"); fi; done
        mem=(); [ "$FUZZ_VARIANT" = asan ] && mem=(-m none)
        ( cd "$FUZZ" && env EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 "ASAN_OPTIONS=$ASAN_OPTIONS_FUZZ" afl-tmin -i "$first" -o "$min" -t 5000 "${mem[@]}" -- "$bin" "${args[@]}" ) > "$min.log" 2>&1 || true
        printf '%s\t%s\t%s\n' "$key" "$([ -f "$min" ] && file_size "$min" || echo '-')" "$min" >> "$TMINS"
    done < "$KEYS"
fi

# ---- TRIAGE.md -------------------------------------------------------------------------
rel() { printf '%s' "$1" | sed "s#^$REPO_ROOT/##"; }
{
    echo "# TRIAGE -- AFL++ campaign crashes and hangs, 2026-11-07 aggressive audit"
    echo
    echo "- date_utc: $(now_utc)"
    echo "- fuzz_dir: \`$FUZZ\`; inputs triaged: $NIN; unique keys: $NKEYS"
    echo "- every re-run: OMP_NUM_THREADS=2, EA_ALLOW_SHORT_DATASET=1 (except the tiled compliant-size runs), caps 30 s (crashes) / 90 s (hangs); stdout/stderr/rc per run under \`logs/fuzz/triage/<T>/<kind>/\`"
    echo
    echo "## builds (instrument rule 4)"
    echo
    echo "| role | tool | path | sha256 |"
    echo "|---|---|---|---|"
    for t in $TOOLS; do
        b="$(san_bin "$t")"; if [ -n "$b" ]; then echo "| san (Apple clang asan_ubsan, authoritative) | $t | \`$b\` | \`$(sha256_of "$b")\` |"; else echo "| san | $t | **NOT FOUND** (searched: $SAN_SEARCHED) | |"; fi
        b="$(fuzz_bin "$t")"; if [ -x "$b" ]; then echo "| fuzz ($FUZZ_VARIANT, Homebrew clang 23 + AFL) | $t | \`$b\` | \`$(sha256_of "$b")\` |"; fi
        b="$(prod_bin "$t")"; if [ -x "$b" ]; then echo "| prod (shipped build) | $t | \`cpp/$t\` | \`$(sha256_of "$b")\` |"; fi
    done
    echo
    echo "## summary by unique key (dedup by sanitizer class + top frame; san key when available, else fuzz key)"
    echo
    echo "| key | count | targets | first input | fuzz build | san build | production | tiled to 10^6, no escape | reachable with a compliant file? |"
    echo "|---|---|---|---|---|---|---|---|---|"
    if [ -s "$KEYS" ]; then
        while IFS=$'\t' read -r key count targets first firstT; do
            [ -n "$key" ] || continue
            row="$(awk -F'\t' -v k="$key" '$13==k {print; exit}' "$ROWS")"
            fc="$(printf '%s' "$row" | cut -f8)"; sc="$(printf '%s' "$row" | cut -f5)"; pc="$(printf '%s' "$row" | cut -f11)"
            comp="$(awk -F'\t' -v k="$key" '$1==k {print $2 " -- " $3; exit}' "$COMPL")"; [ -n "$comp" ] || comp="not run"
            co="$(printf '%s' "$comp" | cut -d' ' -f1)"
            case "$co" in
                ASAN:*|UBSAN:*|ASSERT|SIGNAL:*) reach="**YES** (reproduced on the tiled 1,000,000-byte input without the escape)" ;;
                n/a) reach="n/a (argv target)" ;;
                TIMEOUT) reach="NOT SHOWN (tiled run hit the cap)" ;;
                not|SKIPPED) reach="not run" ;;
                *) reach="NOT SHOWN (tiled run: $co)" ;;
            esac
            echo "| \`$key\` | $count |$targets | \`$(rel "$first")\` | $fc | $sc | $pc | $comp | $reach |"
        done < "$KEYS"
    else
        echo "| (no crashes or hangs were saved by the campaign) | | | | | | | | |"
    fi
    echo
    echo "## every input"
    echo
    echo "| T | kind | input | bytes | san | fuzz | prod | san detail |"
    echo "|---|---|---|---|---|---|---|---|"
    if [ -s "$ROWS" ]; then
        while IFS=$'\t' read -r T kind path size sc sk sd fc fk fd pc pd pk; do
            echo "| $T | $kind | \`$(rel "$path")\` | $size | $sc | $fc | $pc | $(printf '%s' "$sd" | cut -c1-140 | sed 's/|/\\|/g') |"
        done < "$ROWS"
    else
        echo "| (none) | | | | | | | |"
    fi
    if [ -s "$TMINS" ]; then
        echo; echo "## afl-tmin minimised inputs"; echo; echo "| key | bytes | path |"; echo "|---|---|---|"
        while IFS=$'\t' read -r key sz p; do echo "| \`$key\` | $sz | \`$(rel "$p")\` |"; done < "$TMINS"
    fi
    echo
    echo "## reading the classes"
    echo
    echo "- EXIT:n in the san column means the authoritative build did NOT reproduce the crash (exit n, last stdout line quoted in the detail files). A crash only under the fuzz build is a Homebrew-clang-23 codegen or instrumentation artefact until shown otherwise; a crash only under the fuzz AND san builds but not production is a sanitizer-detected silent defect (the production binary runs past it) and is still a finding."
    echo "- ASSERT rows are the tool's own assert() aborts (SIGABRT). An assert reached only through the escape's decline paths (below) is not reachable by a compliant file; the tiled column is the measurement."
    echo "- TIMEOUT rows from T6 are expected for inputs that FAIL the permutation battery (all 10,000 permutations run); the hang is the battery's cost, not a loop defect, unless the tiled or 90 s re-run shows otherwise."
    echo
    echo "## escape-only paths (a compliant file never takes these; run.sh header)"
    echo
    echo "collision_test.h:47 (v < 2), compression_test.h:128 (num_blocks < 1002), multi_mcw_test.h:16 (len <= 4096), lag_test.h decline, multi_mmc_test.h:187 (len < 3) and :30, lz78y_test.h:137 (len < B+2) and :30, lrs_test.h:155/:390 (v == 0), the IID chi-square m = 1 failure, and for T5 the estimator run on the 17-sample block."
    echo
    echo "## what this triage cannot see (rule 18)"
    echo
    echo "- A crash that depends on the exact input LENGTH or period: tiling to 1,000,000 bytes changes both, so NOT SHOWN is not NOT REACHABLE."
    echo "- A T6 crash that depends on the permutation shuffle (seed() reads /dev/urandom): it may not replay from the input alone; three re-runs were made, not thirty."
    echo "- UB classes the fuzz build traps without a message (AFL_USE_UBSAN is trap-on-error); only the san build names them."
    echo "- Anything beyond the 30/90 s caps, or beyond --max-compliant $MAXC tiled runs."
    echo "- If the san build was NOT FOUND, every san column is NA and the fuzz key stands in for it; re-run triage.sh --san-dir once harness/sanitizers has built."
    echo
    echo "## next"
    echo
    echo "For each key marked YES (or ASAN/UBSAN under the san build on a shipped path): write \`repro/AA-NN/\` per AUDIT-BRIEF.md with the input, the exact command and env, the observed (these files), the expected, a negative control (the good seed through the same command), and the binaries by sha256 above."
} > "$OUTMD"
cp "$OUTMD" "$LOGS_DIR/fuzz-triage.log"
note "wrote $OUTMD ($NIN inputs, $NKEYS unique keys)"
