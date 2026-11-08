#!/bin/zsh
# argv_driver.sh -- T7: map a fuzz file to an argv vector and exec one of the
# three tools.  Written for zsh 5.9 (/bin/zsh on this host); bash 3.2 cannot hold
# the bytes AFL produces in parameters.
#
# WHY A DRIVER.  afl-fuzz mutates a FILE.  The option parsers of ea_non_iid,
# ea_iid and ea_restart (TestRunUtils.h scanArgs / refuseOptionAfterOperand /
# versionOptionRequested / prescanOutputAndOperand; getopt; parse_unsigned_decimal;
# restart_main.cpp parseHIArgument) read argv, so something must turn the file into
# an argv.  The fork server fixes argv once at startup, which is why T7 runs with
# AFL_NO_FORKSRV=1: every execution is a fresh fork+exec of THIS script, which
# reads the current fuzz file, builds the argv and execs the instrumented binary.
# Coverage still flows because the instrumented binary maps __AFL_SHM_ID itself.
# Cost: ~20-50 execs/s instead of hundreds -- acceptable for a grammar this small.
#
# GRAMMAR (one token per line; a trailing newline is not a token):
#   line 1 exactly "N", "I" or "R"  -> ea_non_iid / ea_iid / ea_restart, consumed
#                                      (anything else: ea_non_iid, nothing consumed)
#   @F  -> <work>/bits-2000.bin     2,000 bytes in {0,1}: fits EVERY declared width 1..8
#   @G  -> <work>/bytes-2000.bin    2,000 bytes 0..255: fits only width 8 / inferred
#   @E  -> <work>/empty.bin         0 bytes ("is empty" refusal)
#   @X  -> <work>/does-not-exist.bin
#   @D  -> <work>                   a directory ("not a regular file" refusal)
#   @O  -> <work>/out/report.json   a legal -o target
#   any other token is passed verbatim, EXCEPT:
#     - a token with TWO OR MORE '/' is REJECTED.  One slash is allowed so the H_I
#       unit grammar (0.5/symbol, 0.5/bit, and misspellings such as 0.5/bits or
#       /symbol alone) stays reachable.  With the process cd'd into <work>, a
#       single-slash token can only name a path inside <work>, inside its parent
#       (../x), or directly under / (not writable here), so the fuzzer cannot write
#       a JSON report to an arbitrary path or read an arbitrary file.  A rejected
#       vector exits 0 without exec: AFL sees a dull input and loses interest.
#     - more than 32 tokens or a token longer than 256 bytes: rejected the same way.
#
# WHAT THIS CANNOT REACH (rule 18): ea_restart's estimators and its row/column
# matrix.  restart_main.cpp:694 refuses any file whose length is not exactly
# 1,000,000 bytes, with no EA_ALLOW_SHORT_DATASET escape, and the fixtures are
# 2,000 bytes.  T7 covers ea_restart's argv handling and H_I grammar only; the
# restart estimators need a 1,000,000-byte matrix, which is a heavy job per
# execution and is out of reach of a fuzzer on this host.
#
# Environment (set by run.sh / triage.sh):
#   FUZZ_DRIVER_BIN_DIR   directory holding ea_non_iid, ea_iid, ea_restart to exec
#   FUZZ_DRIVER_WORK      the work directory with the fixtures (created by run.sh)
#   FUZZ_DRIVER_PRINT=1   print "TOOL <tool>" and one "ARG <token>" per argument
#                         (or "REJECTED <why>") instead of executing -- the self-test
#                         and the triage record use this
#   EA_ALLOW_SHORT_DATASET=1 and OMP_NUM_THREADS=2 are inherited, not set here.

emulate -L zsh
setopt no_unset

: ${FUZZ_DRIVER_BIN_DIR:?FUZZ_DRIVER_BIN_DIR must name the directory of instrumented binaries}
: ${FUZZ_DRIVER_WORK:?FUZZ_DRIVER_WORK must name the work directory}

reject() {
    [[ -n ${FUZZ_DRIVER_PRINT:-} ]] && print -r -- "REJECTED $1"
    exit 0
}

f=${1:-}
[[ -n $f && -r $f ]] || reject "no readable input file"

content=$(<"$f")
if [[ -z $content ]]; then
    lines=()                       # an empty file is an empty argv, not one empty argument
else
    lines=("${(@f)content}")       # one token per line; empty lines in the middle are kept
fi

tool=ea_non_iid
if (( ${#lines} > 0 )); then
    case "${lines[1]}" in
        N) tool=ea_non_iid; lines=("${(@)lines[2,-1]}") ;;
        I) tool=ea_iid;     lines=("${(@)lines[2,-1]}") ;;
        R) tool=ea_restart; lines=("${(@)lines[2,-1]}") ;;
    esac
fi

(( ${#lines} <= 32 )) || reject "more than 32 tokens (${#lines})"

args=()
for a in "${(@)lines}"; do
    (( ${#a} <= 256 )) || reject "token longer than 256 bytes"
    case "$a" in
        '@F') a="$FUZZ_DRIVER_WORK/bits-2000.bin" ;;
        '@G') a="$FUZZ_DRIVER_WORK/bytes-2000.bin" ;;
        '@E') a="$FUZZ_DRIVER_WORK/empty.bin" ;;
        '@X') a="$FUZZ_DRIVER_WORK/does-not-exist.bin" ;;
        '@D') a="$FUZZ_DRIVER_WORK" ;;
        '@O') a="$FUZZ_DRIVER_WORK/out/report.json" ;;
        *)
            if [[ $a == */* ]]; then
                slashes=${#${a//[^\/]/}}
                (( slashes <= 1 )) || reject "two or more slashes in token (path-shaped): ${(q)a}"
            fi ;;
    esac
    args+=("$a")
done

if [[ -n ${FUZZ_DRIVER_PRINT:-} ]]; then
    print -r -- "TOOL $tool"
    for a in "${(@)args}"; do print -r -- "ARG ${(q)a}"; done
    exit 0
fi

[[ -x "$FUZZ_DRIVER_BIN_DIR/$tool" ]] || reject "binary not executable: $FUZZ_DRIVER_BIN_DIR/$tool"
cd "$FUZZ_DRIVER_WORK" || reject "cannot cd to work dir"
exec "$FUZZ_DRIVER_BIN_DIR/$tool" "${(@)args}"
