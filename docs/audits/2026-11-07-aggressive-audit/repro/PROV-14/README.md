# PROV-14 -- Makefile flag probes use the fixed, predictable path /tmp/.ea_fs_$.c (make's $$ -> $; `$.` is not a shell expansion)

**Provisional ID:** PROV-14 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (build hygiene; denial-of-build by a planted file; no numeric effect)
**Direction:** neutral
**Component:** cpp/Makefile:45 (FLOAT_STORE := $(shell ... /tmp/.ea_fs_$$.c ...)) and :49 (IGNORED_FLAG_IS_ERROR := $(shell ... /tmp/.ea_wf_$$.c ...)).
**Spec:** n/a (build hygiene).
**Prior-fix interaction (rule 12):** OC-121 (b53ff5d) introduced both probes.
**Analysis-phase source (re-checked here):** logs/analysis/cli-build.md 5.1 and 9.8 (MEASURED with a two-line makefile: shell-expanded=/tmp/.ea_fs_$.c recipe-expanded=/tmp/.ea_fs_$.c).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED without running make: the Makefile carries the `$$` path twice (grep), and `sh -c 'printf "%s\n" /tmp/.ea_fs_$.c'` prints the literal '/tmp/.ea_fs_$.c' twice (identical). The scratch-make confirmation is gated behind EA_REPRO_ALLOW_MAKE=1 because this phase forbids make; the cli-build agent measured it. Control: mktemp gives two different paths.

**What this reproducer does not establish:** No build was run, so the race/plant consequences are argued from the recipe, not demonstrated.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-14-observed.log` and `PROV-14-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- (no production binary run: source/model only)

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-14 observed.txt  2026-11-07 21:56:17 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
Makefile sha256 c89066a2c73afee3aabf8877ade4ec36813f1770bb00e359b005c0f8fac18d0e
Makefile lines carrying the probe path (grep -n 'ea_fs_\$\$\|ea_wf_\$\$'):
  Makefile:45:FLOAT_STORE := $(shell printf 'int main(void){return 0;}' > /tmp/.ea_fs_$$.c 2>/dev/null;     if $(CXX) -x c++ -ffloat-store -c /tmp/.ea_fs_$$.c -o /dev/null
  Makefile:49:IGNORED_FLAG_IS_ERROR := $(shell printf 'int main(void){return 0;}' > /tmp/.ea_wf_$$.c 2>/dev/null;     if $(CXX) -x c++ -Werror=ignored-optimization-argumen
occurrences of the fixed /tmp/.ea_*_$$.c path in the Makefile: 2
GNU make, 'Variables in Recipes'/'The shell Function': a double dollar sign '$$' is passed to the shell as a single '$'.
what the shell receives and expands, twice: '/tmp/.ea_fs_$.c' and '/tmp/.ea_fs_$.c'  (identical: '$.' is not a parameter expansion in sh)
(scratch make step skipped: EA_REPRO_ALLOW_MAKE not set; the cli-build analysis measured shell-expanded=/tmp/.ea_fs_$.c recipe-expanded=/tmp/.ea_fs_$.c the same way)
a planted file at that path right now: ls: cannot access '/tmp/.ea_fs_$.c': No such file or directory
RESULT: PASS -- both flag probes use the literal path /tmp/.ea_fs_$.c (and .ea_wf_$.c): fixed, world-writable directory, predictable; concurrent builds race and a planted file/symlink is compiled by the probe (denial of build; on GCC the sabotage can only ADD -ffloat-store)
```

### control.txt (verbatim)

```
# PROV-14 control.txt  2026-11-07 21:56:17 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
mktemp twice: '/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-14/out/.ea_fs_iJRnO6.c' and '/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-14/out/.ea_fs_pRTnW4.c'  (different: yes)
RESULT: CONTROL-OK -- mktemp yields a fresh, unpredictable path per probe; the Makefile's $$ form yields the same literal path every time (run.sh)
```
