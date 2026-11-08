# TEST-PLAN -- FIX-stale-report (PROV-01: a stale success survives an option error before -o)

- **Branch:** `fix/stale-report`, commit `c8b0bc6d0c68c271a07f91ee23203a471604f4ae`, from master `04c1ccc`.
- **Worktree:** `/Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-1` (call it `$W` below).
- **Nothing was compiled by the fixing agent** (heavy slot busy). The PASS half of the
  evidence is this plan's to produce. The FAIL half is already measured (section 0).
- The regression sets `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` itself and uses the
  10,000-sample fixture `bin/rand8_short.bin`; only sections 4 (one arm) and 5 are heavy.
- `$S` is any scratch directory, e.g.
  `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/<session>/scratchpad/fix-stale-report`.
  Never `-o` into `cpp/` of the main checkout: its three binaries are the production
  build the reproducer pack reads (brief ground rule 3).

## 0. Already measured without a build (2026-11-08, Darwin 25.6.0 arm64) -- logs in this directory

| what | result | log |
|---|---|---|
| `regression-stale-report.sh` against the **production binaries** (`ea_non_iid` `1ad1568c…`, `ea_iid` `22f1319a…`, `ea_restart` `4d7ba82b…`, built 2026-11-07 from `1151b22`, whose `cpp/` is byte-identical to master `04c1ccc`: `git diff --stat 1151b22 master -- cpp` is empty) | **FAIL (9 of 29 checks)** -- exactly the nine "option error BEFORE -o" probes report `STALE -- the previous complete report survived byte-identical (rc 255)`; the baseline, the 6 control arms, the 8 A05 arms, the A04 arm and the 4 C08 arms all PASS. This is the rule-7 / guide step 5 observation: the test can fail, and fails only where the defect is. | `observed-FAIL-on-master-binaries.log` |
| `regression-deadguard.sh` on the fix tree | PASS, flag set unchanged at 40 (the new `.sh` acquired no dead-guard shape) | `deadguard-on-fix-tree.log` |
| `sh audits/enum-instruments.sh .` with the new script staged | `live: 88 (78 mechanical + 10 reviewed)`; INSTRUMENT-INVENTORY.md and CLOSING-INVENTORY.md say 88 | (in the commit message) |
| `regression-docs.sh` on the fix tree **without** a built `cpp/ea_non_iid` | FAIL (2 checks), **both check 6** (the pinned figure needs the current build: `[ -x cpp/ea_non_iid ] || fails++`, then the macOS figure quoted in NOTICE/BUILDING matches neither the Linux reference nor the absent build). Every other check passes, including all count comparisons this fix touches: scope statement, 9 inventory rows / 12 occurrences, instrument count 88, rule citations. | `regression-docs-on-unbuilt-fix-tree.log` |

## 1. Build the fixed binaries out of tree (HEAVY -- one at a time, serialized)

From `docs/audits/2026-11-07-aggressive-audit/BUILD-LINES.md`, with `-o` into scratch:

```sh
W=/Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-1
S=<scratch>/fix-stale-report; mkdir -p "$S/fixed"
git -C "$W" rev-parse --short HEAD    # expect c8b0bc6
cd "$W/cpp" && clang++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 \
  -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include \
  -I/opt/homebrew/opt/openssl@3/include non_iid_main.cpp -o "$S/fixed/ea_non_iid" \
  -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
  -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto
# same line with  iid_main.cpp -o "$S/fixed/ea_iid"   and   restart_main.cpp -o "$S/fixed/ea_restart"
shasum -a 256 "$S"/fixed/ea_*    # record (instrument rule 4); they must differ from the three production digests above
```

A compile error here is a finding against this fix: the change is one added
statement per tool inside the existing A05 block plus comments, and it uses only
`claimReportTarget`, `preOut` and `commandline`, all already in scope.

## 2. Show the regression FAILING against master's binary

Option A -- no build needed: the production binaries ARE master's `cpp/` (section 0).

```sh
cd "$W/cpp/selftest"
REGRESSION_STALE_REPORT_BINDIR=/Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp \
  ./regression-stale-report.sh > "$S/stale-master.log" 2>&1; echo "rc=$?"
grep -c 'STALE -- the previous complete report survived' "$S/stale-master.log"   # expect 9
tail -1 "$S/stale-master.log"    # expect: regression-stale-report: FAIL (9 of 29 checks)
```

Expected: `rc=1`; the three `[build-state]` lines name the production digests.

Option B -- a build whose provenance is master itself, if the record wants it
stated without the `1151b22 == 04c1ccc` inference:

```sh
mkdir -p "$S/master-src" && git -C "$W" archive master cpp bin | tar -x -C "$S/master-src"
# build the three tools from "$S/master-src/cpp" with the section-1 line, -o "$S/master/ea_*"
REGRESSION_STALE_REPORT_BINDIR="$S/master" ./regression-stale-report.sh > "$S/stale-master-B.log" 2>&1; echo "rc=$?"
```

## 3. Show the regression PASSING against the fixed binary

```sh
cd "$W/cpp/selftest"
REGRESSION_STALE_REPORT_BINDIR="$S/fixed" ./regression-stale-report.sh > "$S/stale-fixed.log" 2>&1; echo "rc=$?"
tail -1 "$S/stale-fixed.log"     # expect: regression-stale-report: PASS (29 checks)
grep -c ' PASS$' "$S/stale-fixed.log"   # expect 29
```

Expected: `rc=0`; the `[build-state]` lines name the section-1 digests, `asserts=LIVE`.
Read the nine probe lines: each must say `replaced by the fail-closed placeholder (rc 255)`.

## 4. The pairs' own regressions against the fixed binary (rule 12)

Each earlier repair's regression, pointed at the fixed build, must still pass:

```sh
cd "$W/cpp/selftest"
REGRESSION_OUTPUT_BINDIR="$S/fixed"       ./regression-output.sh          > "$S/pair-output.log" 2>&1;   echo "C14/N-09 rc=$?"
REGRESSION_OUTPUT_BINDIR="$S/fixed"       ./regression-output-aliasing.sh > "$S/pair-aliasing.log" 2>&1; echo "A05/A04 rc=$?"   # 46 checks
REGRESSION_OPTION_ORDER_BINDIR="$S/fixed" ./regression-option-order.sh    > "$S/pair-order.log" 2>&1;    echo "OC-104 rc=$?"
```

Expected: all `rc=0`. `regression-output.sh` on macOS skips its three `/dev/full`
cases and says so; that is pre-existing. The aliasing and option-order scripts
generate a 1,000,000-byte input and run the tools on it -- count each as one
heavy job.

## 5. The full suite on the fixed tree (HEAVY: pin-check and selftest run the estimators on 1e6 samples)

`run-all-checks.sh` reads `../ea_non_iid`, `../ea_iid`, `../ea_restart` relative to
`cpp/selftest`. Copy the fixed binaries into the **worktree's** `cpp/` (all three names
are in `.gitignore`, so the tree stays clean) -- never into the main checkout's `cpp/`:

```sh
cp "$S"/fixed/ea_non_iid "$S"/fixed/ea_iid "$S"/fixed/ea_restart "$W/cpp/"
cd "$W/cpp/selftest"
./run-all-checks.sh --allow-known-platform-deltas > "$S/suite.log" 2>&1; echo "suite rc=$?"
grep -E '^run-all-checks:|^build-state:' "$S/suite.log"
```

Expected:

- `run-all-checks: 27 passed, 0 failed (25 regression scripts discovered)`, `rc=0`.
- `build-state: 6 of 27 checks declared the artefact they measured`. **If the number is
  not 6**, WHAT-A-GREEN-SUITE-ESTABLISHES.md precondition 3 was derived, not measured
  (5 measured 2026-10-27 plus this member, which prints `bs_print` lines): correct it to
  the measured value in a follow-up commit on this branch and say so. `regression-docs.sh`
  does not check that figure, only its denominator.

Then, with the binary now present in the worktree:

```sh
./regression-docs.sh > "$S/docs.log" 2>&1; echo "docs rc=$?"        # expect PASS; the two section-0 failures were check 6, unbuilt
./harness-inventory-mutation-test.sh > "$S/inv-mut.log" 2>&1; echo "rc=$?"   # expect 5 of 5 landed (counts derived from run-all-checks.sh)
git -C "$W" status --short                                             # expect empty: the copied binaries are ignored
```

## 6. The PROV-01 reproducer, if the production binaries are ever rebuilt from this fix

`repro/PROV-01/run.sh` reads the production binaries through `repro/_lib.sh`
(`NONIID="$repo/cpp/ea_non_iid"` etc.; no override variable). Against a build that
contains this fix it must report `RESULT: FAIL` (defect absent, exit 1) -- that is the
reproducer's own pass/fail polarity -- and `control.sh` must still report `CONTROL-OK`.
`regression-stale-report.sh` carries the same four probes plus the `-l`/`-s` and cluster
forms per tool, so sections 2-3 are the equivalent measurement without touching the
production build; rebuilding it is the owner's decision (brief ground rule 3).

## 7. x86-64 (optional, CI only)

Pushing `fix/stale-report` to `systemslibrarian/SP800-90B_EntropyAssessment` runs
`.github/workflows/x86-64-platform-facts.yml`, whose suite gate derives its expected
counts from `run-all-checks.sh` (`$((TOTAL - 1)) passed, 0 failed, 1 could not run`).
The Darwin observation in section 0 is evidence about Darwin only (guide step 5). Never
dispatch anything to `usnistgov` (brief ground rule 1).

## What a PASS here establishes, and what it does not

Establishes: after any `-o <path>` run on these three tools that fails at option
parsing -- before or after `-o`, flat or clustered -- `<path>` holds this run's
placeholder (errorLevel -1, reportComplete false, the tool's type, "Refuse this file")
and never the previous run's report; the A05 identity refusal still precedes every write;
the atomic writer still replaces the placeholder with the tool's own report.

Does not establish: anything about an abort or signal between the prescan claim and the
first write (that window existed before and is covered by C14's placeholder design, not by
this test); anything on Windows (`MoveFileExA` path, CI-owned); anything about the two
`-o` values of a doubled `-o`, which is read-verified (E2 in prior-repairs.md) and not
probed here.

## A correction to the record this fix was briefed from

`repro/PROV-01/README.md` and `logs/analysis/prior-repairs.md` cite the C14 claim as
`97fbc6c`. That object does not exist; the C14 commit is **`97bfc6c`**
(`fix(C14): close both permissive routes on the status channel; …`, 2026-10-19). The
fix's commit message and NOTICE entry use the resolving SHA. The record files are the
audit's own and were left as written; the orchestrator should correct them.
