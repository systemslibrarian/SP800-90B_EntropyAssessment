# PROV-17 -- OC-104 refusal fires on a line already carrying '--' with a false reason and advice already satisfied

**Provisional ID:** PROV-17 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (wrong-reason refusal; both C libraries would refuse this line on the usage path anyway, so only the message is wrong)
**Direction:** neutral (wrong-reason refusal)
**Component:** cpp/shared/TestRunUtils.h:scanArgs() :183 (a pre-operand '--' is consumed and ends the option walk) and :214-222 (the late-option loop stops only at a '--' AFTER the first operand); refuseOptionAfterOperand() :363-385 prints the reason.
**Spec:** n/a (CLI contract). OC-104 itself is a DOCUMENTED DIVERGENCE (FORK-DIVERGENCE-AND-TRUST.md A.3) and is not re-reported; only the message on this shape is.
**Prior-fix interaction (rule 12):** OC-104 (36cafb3); A04 (663f9ae) introduced dashDashAt for versionOptionRequested(), which the late-option loop does not consult. regression-option-order.sh tests `-- capture.bin 1` without a trailing option-shaped operand and cannot see it.
**Analysis-phase source (re-checked here):** logs/analysis/cli-build.md 4.7 and 9.7 (MEASURED dashdash-then-late-q rc=255).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: `-i -- rand1_short.bin 1 -q` -> exit 255 with 'what this command line MEANS depends on the C library ... separate the operands with '--''. Control (a): `-i -- rand1_short.bin 1` assesses (exit 0); control (b): the no-'--' line produces byte-identical stderr, so the message cannot distinguish the two cases.

**What this reproducer does not establish:** glibc behaviour after '--' is from the documented getopt semantics (no permutation past '--'), not measured here.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-17-observed.log` and `PROV-17-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`  ea_non_iid

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-17 observed.txt  2026-11-07 21:56:19 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -i -- /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1 -q
rc[dashdash_late_q]=255  stdout=dd.out stderr=dd.err
stderr (verbatim):
  | Error: '-q' looks like an option but appears after the file operand '/Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin'.
  |        Refusing to run: what this command line MEANS depends on the C
  |        library. glibc rearranges it and parses '-q'; BSD and macOS treat
  |        it as another operand and fail on the usage path. One line, two
  |        supported platforms, two different operations -- and guessing which
  |        was wanted is worse than refusing. Nothing has been written.
  | 
  |        Put every option BEFORE the file:
  |          ea_non_iid [-i|-c] [-a|-t] [-v] [-q] [-l <index>,<samples>] [-o <file>] <file_name> [bits_per_symbol]
  |        If '-q' is meant as an operand and not an option, separate the
  |        operands with '--'.
refusal markers: 'depends on the C library'=1 'separate the operands'=1 'Nothing has been written'=1 ; rc=255
code: scanArgs consumes a pre-operand '--' at TestRunUtils.h:183; the late-option loop stops only at a '--' AFTER the first operand (:217)
RESULT: PASS -- '-i -- file 1 -q' is refused with the C-library-dependence reason and told to add a '--' it already has; both libcs would have refused this line on the usage path (argc 3) -- a wrong-reason refusal
```

### control.txt (verbatim)

```
# PROV-17 control.txt  2026-11-07 21:56:20 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -i -- /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1
rc[dashdash_only]=0  stdout=c_dd.out stderr=c_dd.err
  (a) '-i -- file 1': rc=0  Assessed line present: 1
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -i /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1 -q
rc[no_dashdash_late_q]=255  stdout=c_nd.out stderr=c_nd.err
  (b) '-i file 1 -q' (no --): rc=255 ; stderr vs run.sh's stderr: byte-identical
RESULT: CONTROL-OK -- '--' is honoured when nothing option-shaped follows the operands (exit 0); the refusal text for the with-'--' and without-'--' lines is byte-identical, so the operator cannot tell a true permutation hazard from a line that already disambiguated
```
