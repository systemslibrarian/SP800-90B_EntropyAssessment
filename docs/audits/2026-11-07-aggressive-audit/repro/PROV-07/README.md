# PROV-07 -- ea_restart -s refuses values below 5,000,000 (and 0) with a bare usage dump although documented 'Accepted for compatibility and ignored'

**Provisional ID:** PROV-07 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** MEDIUM by the brief's table (a wrong refusal); the analysis ranked it LOW because only a legacy, now-meaningless option is affected
**Direction:** wrong refusal (neutral on figures)
**Component:** cpp/restart_main.cpp:main() :449-458 (`if((inul == 0) || (inul == ULONG_MAX) || (inul < simulation_rounds)) { print_usage(); }` with simulation_rounds = DEFAULT_SIMULATION_ROUNDS 5000000UL, :27); usage text :205-206; `(void) simulation_rounds; // -s is accepted and ignored` :753.
**Spec:** n/a (CLI contract).
**Prior-fix interaction (rule 12):** N-08 (031d7ee) made the -s parse strict-decimal (and added the only reason line, for a non-decimal); C23 (7a0be01) replaced the simulation with the exact cutoff, making -s meaningless but leaving the range check. regression-restart.sh:88-96 tests only the N-08 spellings (5000000x, +5000000, 0x5000000) and cannot see this.
**Analysis-phase source (re-checked here):** logs/analysis/cli-build.md 2.3, 4.8 and 9.6 (MEASURED there); restart.md S4.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: -s 1000, -s 4999999, -s 0 each exit 255 with 'Usage is: ...' as the first and only block and zero reason lines; control: -s 5000000 proceeds to the data-size refusal (no usage dump), -s 1000x gets 'Simulation count must be an unsigned decimal integer.'

**What this reproducer does not establish:** None of the runs read a 1,000,000-sample matrix; the refusal happens at option parsing.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-07-observed.log` and `PROV-07-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`  ea_restart

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-07 observed.txt  2026-11-07 21:56:11 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
usage text: restart_main.cpp:205:    printf("\t -s <simulation count>: Accepted for compatibility and ignored: the sanity-check cutoff is\n");
code:       restart_main.cpp:454:		if((inul == 0) || (inul == ULONG_MAX) || (inul < simulation_rounds)) {
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart -n -s 1000 /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8 3/symbol
rc[s_1000]=255  stdout=s_1000.out stderr=s_1000.err
  -s 1000: rc=255 usage-dump=1 reason-lines=0 first-stdout-line='Usage is: ea_restart [-i|-n] [-v] [-q] [-s <simulation count>] <file_name> [bits_per_symbol] <H_I>'
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart -n -s 4999999 /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8 3/symbol
rc[s_4999999]=255  stdout=s_4999999.out stderr=s_4999999.err
  -s 4999999: rc=255 usage-dump=1 reason-lines=0 first-stdout-line='Usage is: ea_restart [-i|-n] [-v] [-q] [-s <simulation count>] <file_name> [bits_per_symbol] <H_I>'
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart -n -s 0 /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8 3/symbol
rc[s_0]=255  stdout=s_0.out stderr=s_0.err
  -s 0: rc=255 usage-dump=1 reason-lines=0 first-stdout-line='Usage is: ea_restart [-i|-n] [-v] [-q] [-s <simulation count>] <file_name> [bits_per_symbol] <H_I>'
bare-usage refusals: 3 of 3
RESULT: PASS -- -s 1000 / -s 4999999 / -s 0 are refused with a bare usage dump (no reason line) although the usage text says the option is accepted and ignored
```

### control.txt (verbatim)

```
# PROV-07 control.txt  2026-11-07 21:56:12 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart -n -s 5000000 /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8 3/symbol
rc[s_5000000]=255  stdout=c_s_5000000.out stderr=c_s_5000000.err
  (a) -s 5000000: rc=255 usage-dump=0 size-refusal-line=1
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart -n -s 1000x /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8 3/symbol
rc[s_1000x]=255  stdout=c_s_1000x.out stderr=c_s_1000x.err
  (b) -s 1000x: rc=255 reason-line=1
RESULT: CONTROL-OK -- -s 5000000 is accepted (the run reaches the data-size refusal, no usage dump); a non-decimal -s gets a reason line -- only in-range values below 5e6 get the silent usage dump
```
