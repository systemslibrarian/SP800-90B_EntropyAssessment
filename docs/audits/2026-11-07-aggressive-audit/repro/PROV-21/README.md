# PROV-21 -- `--version -Z` prints the banner and exits 0 on a malformed line (the unknown option is never reported)

**Provisional ID:** PROV-21 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (exit 0 with nothing assessed, the F04 shape, for the reversed ordering only; the operator did ask for the version)
**Direction:** neutral
**Component:** cpp/shared/TestRunUtils.h:versionOptionRequested() :321-323 (`if (s.rejectAt >= 0 && s.rejectAt < s.versionAt) return false;` -- the unknown option wins only when it comes FIRST).
**Spec:** n/a (CLI contract).
**Prior-fix interaction (rule 12):** A04/F04 (663f9ae, b63aff1) -- the repair's own comment says returning true past an unrecognised option 'would be exit 0 with nothing assessed, which is F04 itself'; OC-104 runs ahead of it.
**Analysis-phase source (re-checked here):** logs/analysis/cli-build.md section 3 (version-then-Z rc=0), 7 (A04 row) and 9.13.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED for all three tools: `--version -Z` -> exit 0, banner line 'non_iid 1.1.8' / 'iid 1.1.8' / 'restart 1.1.8', no 'illegal option', no usage dump. Control: `-Z --version` -> exit 255, 'illegal option -- Z', usage.

**What this reproducer does not establish:** Whether a harness ever appends options after --version is unknown.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-21-observed.log` and `PROV-21-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`  ea_iid
- `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`  ea_non_iid
- `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`  ea_restart

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-21 observed.txt  2026-11-07 21:56:23 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid --version -Z
rc[ea_non_iid]=0  stdout=ea_non_iid.out stderr=ea_non_iid.err
  ea_non_iid --version -Z: rc=0 banner-line='non_iid 1.1.8' banner=1 'illegal option' on stderr=0 usage-dump=0
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid --version -Z
rc[ea_iid]=0  stdout=ea_iid.out stderr=ea_iid.err
  ea_iid --version -Z: rc=0 banner-line='iid 1.1.8' banner=1 'illegal option' on stderr=0 usage-dump=0
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart --version -Z
rc[ea_restart]=0  stdout=ea_restart.out stderr=ea_restart.err
  ea_restart --version -Z: rc=0 banner-line='restart 1.1.8' banner=1 'illegal option' on stderr=0 usage-dump=0
code:  if (s.rejectAt >= 0 && s.rejectAt < s.versionAt) return false;  if (s.dashDashAt >= 0 && s.dashDashAt < s.versionAt) return false;  return true; 
RESULT: PASS -- all three tools exit 0 with a banner on '--version -Z'; the unknown option after --version is never reported
```

### control.txt (verbatim)

```
# PROV-21 control.txt  2026-11-07 21:56:24 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -Z --version
rc[Z_then_version]=255  stdout=c_zv.out stderr=c_zv.err
  -Z --version: rc=255 banner=0 'illegal option'=1 usage=1
RESULT: CONTROL-OK -- -Z before --version is refused (exit 255, 'illegal option -- Z'); the same two flags in the other order exit 0
```
