# Sanitizer phase -- harness

Written 2026-11-07 (analysis phase; nothing here has been compiled or run against a sanitizer
binary yet -- the heavy slot was taken). Everything below is to be RUN LATER by the orchestrator.

## Files

| file | what |
|---|---|
| `build.sh [SAN_DIR]` | builds `ea_non_iid`, `ea_iid`, `ea_restart` out of tree into `SAN_DIR/{asan_ubsan,tsan}/` with the exact BUILD-LINES.md line (`-O2` -> `-O1 -g -fno-omit-frame-pointer` + sanitizer flags), smoke-runs `--version`, probes LeakSanitizer support, verifies the production binaries did not change, writes `SAN_DIR/BUILD-RECORD.txt` |
| `run.sh` | the stages below; one log file per run; resumable; `--quick`; `--dry-run`; writes `logs/sanitizers/RESULTS.md` via `summarize.py` |
| `gen_inputs.py` | deterministic generated inputs (1 MiB random-source file, two 1000x1000 restart matrices, the full-battery `ea_iid` input); refuses if its output's sha256 differs from the recorded one |
| `summarize.py` | RESULTS.md writer; `--selftest` proves its detector and TSan triage can fail (fixtures built from the real source's pragma line ranges) |
| `tsan-libomp.supp` | TSan suppressions for libomp internals ONLY; the file explains why that is nearly all it can do |

Default `SAN_DIR` = `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/san`.
Logs: `docs/audits/2026-11-07-aggressive-audit/logs/sanitizers/<variant>/ea_<tool>-<input>.<tag>.log`.
NOTE: the repo-root `.gitignore` ignores `*.log`, so the per-run logs are untracked; `RESULTS.md`, `ENV.txt` and `BUILD-RECORD.txt` (copy it in) are the committed record.

## How to run (heavy slot; one job at a time)

```sh
H=/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/harness/sanitizers
$H/summarize.py --selftest                  # ~1 s, no binaries needed
$H/build.sh                                 # HEAVY, ~6-12 min (6 compiles, serial)
$H/run.sh --dry-run                         # prints the plan with heavy markers and model estimates
$H/run.sh --quick                           # stage a only, model 8 min (allow 10-20)
$H/run.sh                                   # stages a,b,c,d,e, model ~45 min (allow 45-90; e alone ~10-25)
$H/run.sh --stages tsan                     # HEAVY, 10 threads, model 43 min (allow 25-60)
$H/run.sh --summarize-only                  # rewrite RESULTS.md from whatever logs exist
```
`run.sh` skips any input whose log already carries the `## exit:` trailer (`--force` re-runs);
a log without the trailer is a killed run and is re-run. Stage `e` and `tsan` runs are marked
`heavy=yes` (>= 200,000 samples); stage `a` also contains eight 1,000,000-sample runs.

## Stages and duration estimates

Anchors (production binaries, 2 threads, 20,000 samples, `logs/sanitizers-calibration-*.log`,
binaries in `logs/sanitizers-calibration-binaries.sha256`): `ea_non_iid` 8-bit `-i -a` 0.31 s,
1-bit 0.024 s, 8-bit `-c` 0.07 s; `ea_iid` random 3-bit (early stop) 0.16 s; `ea_iid` full
10,000-round battery (1-bit lag-32 input) 1.34 s. Scaled linearly in n (LRS is n log n, so
~1.3x low at 1e6), x5 for `-O1` + ASan/UBSan, x10 for TSan. **Model estimates, not
measurements.** `run.sh --dry-run` prints them per run.

| stage | variant | what | runs | est. |
|---|---|---|---|---|
| a | asan_ubsan | `bin/*.bin` as `cpp/selftest/selftest` runs them (`ea_non_iid -vv`, width inferred; refdata's inferred width recorded), fixture sha256 checked; + `ea_iid -vv` on the three 10,000-sample files | 14 | model 8 min; allow 10-20 (three 8-bit and two 4-bit 1e6 files dominate) |
| b | asan_ubsan | `corpus/*-50000.bin` at MANIFEST width, `-i -a -vv` and `-c -vv`; byte-identical (sha, width, flags) runs aliased; + `-l 1,20000` subset and `-o` JSON runs | 106 (90 distinct + 16 aliases) | model 6 min; allow 8-12 |
| c | asan_ubsan | every other small `corpus/*.bin`: `ea_non_iid -vv` at the name-declared width AND at the tool-inferred width; `ea_iid -vv` once | 179 | model 11 min (a 2 s floor per run); allow 5-12 |
| d | asan_ubsan | `ea_iid -i -a -v` / `-c -v` on distinct 50k files (+ generated full-battery file, + `-o`) | 106 | model 10 min; allow 5-15 (most inputs stop at chi-square or stop the battery early; the generated lag-32 file runs all 10,000 rounds) |
| e | asan_ubsan | **heavy** `ea_restart` on generated 1000x1000 matrices: 1-bit `-n`, 8-bit `-n`, 1-bit `-i` (live permutation region), 1-bit `-n -o` | 4 | model 10 min; allow 10-25 |
| tsan | tsan | **heavy**, `OMP_NUM_THREADS=10`, three inputs per tool (below) | 9 | model 43 min (restart -i dominates); allow 25-60 |

`--quick` = stage a. ASan runs use `OMP_NUM_THREADS=2`.

### Options the runs use
```
ASAN_OPTIONS=detect_leaks=<1 if BUILD-RECORD says lsan_supported=yes else 0>:abort_on_error=1:halt_on_error=1:strict_string_checks=1:detect_stack_use_after_return=1:check_initialization_order=1:strict_init_order=1
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1:report_error_type=1
TSAN_OPTIONS=halt_on_error=0:second_deadlock_stack=1:history_size=3:print_suppressions=1:suppressions=tsan-libomp.supp   (+ OMP_WAIT_POLICY=passive; --tsan-active-wait drops it)
EA_ALLOW_SHORT_DATASET=1  only for n < 1,000,000 (header line `short_dataset_escape`)
EA_TEST_RANDOM_SOURCE=<SAN_DIR>/inputs/random-source-1MiB.bin
```
`-fno-sanitize-recover=undefined` makes the `undefined` group fatal at compile time; the
`implicit-conversion`, `nullability` and `float-divide-by-zero` groups are recoverable, so
`halt_on_error=1` stops the run at the first of those. When that happens run.sh re-runs the
input once with `halt_on_error=0` into `<log>.ubsan-continue.log` so the rest of that input's
reports are seen (`--no-ubsan-continue` disables). ASan errors stay fatal in both passes.

LeakSanitizer: Apple's arm64 runtime may refuse `detect_leaks=1` ("detect_leaks is not
supported on this platform", and the process dies). build.sh probes this with `--version` and
records `lsan_supported=`; run.sh reads it and sets `detect_leaks` accordingly -- it does not
assume. If 0, leaks are simply not checked, and ENV.txt and RESULTS.md say so.

### EA_TEST_RANDOM_SOURCE does not seed the permutation tests
Read from `cpp/` (not assumed): `shared/utils.h:794-811 seed()` opens `"/dev/urandom"`
unconditionally. `EA_TEST_RANDOM_SOURCE` is `g_randomSourcePath` in
`shared/TestRunUtils.h:129`, read once (8 bytes) at `:478` to name the temporary file beside a
`-o` JSON report (OC-121). So the generated 1 MiB file makes the `-o` path's temp-file suffix
fixed, and nothing else; `ea_iid`'s battery remains nondeterministic run to run (the rule-8
memory: this field is nondeterministic by design). The sanitizer verdict does not depend on it.

## `#pragma omp` inventory (every site under `cpp/`, read 2026-11-07, selftest/ excluded)

| site | construct | reached by |
|---|---|---|
| `iid/permutation_tests.h:625` | `#pragma omp parallel` | `ea_iid` (any input that passes chi-square AND LRS: `iid_main.cpp:515-517`), `ea_restart -i` (`restart_main.cpp:1127,1134`, rows then columns) |
| `iid/permutation_tests.h:651` | `#pragma omp for` over `PERMS = 10000` rounds | same |
| `iid/permutation_tests.h:661` | `#pragma omp critical(resultUpdate)` -- updates `C[][]`, `test_status[]`, `passed_count`, `completed` | same; contended for all 10,000 rounds only when a test is never decided (the generated lag-32 input) |
| `iid/permutation_tests.h:714` | `#pragma omp critical(verboseOutput)` | same, at **verbose == 2 exactly** (`-v` once; `-vv` is verbose 3 and skips it) |
| `iid/permutation_tests.h:722` | `#pragma omp atomic` on `completed` (else-branch once `passed_count >= 19`) | same, on early-stop inputs (random data) |
| `restart_main.cpp:307` | `#pragma omp parallel` in `simulateBound()` | **dead in the production build**: `simulateBound` is called only under `#ifdef EA_RESTART_WITHOUT_C23_FIX` (`restart_main.cpp:742`); the shipped cutoff is `exactMultinomialMaxBound` |
| `restart_main.cpp:315` | `#pragma omp for` | same (dead) |
| `non_iid_main.cpp` and every header it includes | **none** | `ea_non_iid` has no parallel region at all; `-fopenmp` only links the runtime |

Runtime calls: `omp_get_thread_num()` at `permutation_tests.h:649,709` and `restart_main.cpp:313`;
`omp_get_num_threads()` at `permutation_tests.h:709`.

Shared-state facts the TSan stage targets (from reading the source; the analysis log
`logs/analysis/iid-permutation.md` section 2.11 reached the same reading independently):
`test_status[]` is written inside `critical(resultUpdate)` (:673) and READ outside it by
`run_tests` (:658) and the helpers; `passed_count` (thread-private copy, but recomputed inside the
critical from the shared `test_status`) gates the loop at :653; `completed` is incremented inside
the critical (:679) AND via `omp atomic` (:723) -- two mechanisms on one variable. All three are
formally data races under C++11 and benign for the verdict by the analysis agent's reading;
TSan is expected to report the first and third (classes CROSSES_CRITICAL / ATOMIC_VS_PLAIN).

### TSan inputs (three per tool)
| tool | input | why |
|---|---|---|
| `ea_iid` | `csprng-8bit-50000.bin` 8, `-i -a -v` | early-stop battery: threads take the `omp atomic` else-branch while others are still in the critical |
| `ea_iid` | `csprng-1bit-50000.bin` 1, `-i -a -v` | same at width 1 |
| `ea_iid` | generated `iid-lag32copy-q030-1bit-50000.bin` 1, `-i -a -v` | full 10,000-round battery: maximal critical-section contention (measured at 20k on production: chi-square and LRS pass, battery runs to completion and fails) |
| `ea_non_iid` | `csprng-8bit-50000.bin` 8; `csprng-1bit-50000.bin` 1; `overwidth-7bit-50000.bin` 7 | **controls**: no `#pragma omp` in the translation unit; a report would implicate the runtime or build, not the tool's threading |
| `ea_restart` | `restart-1bit-1000x1000.bin 1 0.9 -n`; `restart-8bit-1000x1000.bin 8 7.0/symbol -n` | **controls**: the tool's own parallel region is dead code in this build |
| `ea_restart` | `restart-1bit-1000x1000.bin 1 0.9 -i` | the one `ea_restart` path with a live parallel region (permutation battery on 1e6 rows and 1e6 columns); heavy |

### Why TSan on this host is a triage, not a verdict
Homebrew libomp 23.1.2 is not TSan-instrumented and ships no Archer/OMPT tool (`nm` finds no
`ompt_start_tool`). TSan therefore never sees the happens-before established by libomp's
barriers, fork/join or `omp critical` locks (kmp queuing/TAS locks, not pthread mutexes). Correctly
synchronized tool code will be reported. `summarize.py` derives the critical/atomic/parallel line
ranges from the source and classes every report; **SAME_CRITICAL is the expected false-positive
class and TSan cannot tell it from a real race here**; CROSSES_CRITICAL, ATOMIC_VS_PLAIN,
DIFFERENT_CRITICALS and PARALLEL_PLAIN are genuine unsynchronized accesses by construction and
need the code read and an owner decision. The suppressions file hides libomp-internal frames only
(and on Darwin, `ignore_noninstrumented_modules=1` already does most of that); it never names tool
code. A clean signal needs a TSan-built libomp (`-DLIBOMP_TSAN_SUPPORT=ON`) or Archer; neither is
built in this phase. `OMP_WAIT_POLICY=passive` is set to reduce spin-wait noise; it changes the
runtime's waiting, not the tool's semantics.

## Stage e: the restart matrices
`gen_inputs.py` writes two 1,000,000-byte row-dataset files (1,000 restarts x 1,000 samples) from
the SHA-256 keystream and reports X_max over rows and columns: 1-bit 548/554, 8-bit 15/15 (this
host, 2026-11-07). H_I is chosen with margin so the 3.1.4.3 sanity check passes and the estimators
are actually exercised: 1-bit `0.9` (p = 2^-0.9 = 0.536, Binomial(1000) mean 536, sd 15.8; the exact
multinomial-maximum cutoff at alpha = 5e-6 is ~600 > 554), 8-bit `7.0/symbol` (p = 1/128, mean 7.8,
sd 2.8; cutoff ~21 > 15). The tool prints `X_cutoff` and `X_max` at `-v`; RESULTS.md's outcome column
says COMPLETED-SANITY-CHECK-FAILED if the margin was misjudged. If it was, lower H_I and re-run with
`--force`. These are not a compliance claim about any device; they exist to drive the code.

## Inputs whose sha256 is checked before running
Stage a against `cpp/selftest/fixture-manifest.txt`; stages b and d against `corpus/MANIFEST.txt`;
generated inputs against `gen_inputs.py`'s own EXPECTED table. A mismatch is a
`SKIPPED-INPUT-SHA-MISMATCH` row, never a run.

## What this phase cannot see
Listed at the top of every RESULTS.md: unmatched report formats; wrong numbers from clean runs;
unexecuted paths; leaks when LSan is unsupported; later reports on an input after the first
recoverable UBSan report (only the continue pass sees them); libomp's happens-before; and the 8-bit
full-battery case for `ea_iid` -- no 8-bit input that passes both chi-square tests yet fails a
permutation test was found at 20,000 samples (lag-32 copying at q = 0.05 fails independence at
p = 2.5e-8 and GOF at p = 3.8e-4), so maximal critical-section contention is exercised at width 1 only.
