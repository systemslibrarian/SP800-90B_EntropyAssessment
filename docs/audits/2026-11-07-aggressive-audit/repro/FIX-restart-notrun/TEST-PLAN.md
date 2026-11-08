# FIX-restart-notrun — test plan

Finding: AA-04 / PROV-10 (`repro/PROV-10/`, `logs/analysis/restart.md` S1 and E5, the X6
decision in `logs/experiments/CHAIN-2.log` lines 139-151).
Fix branch: `fix/restart-notrun`, one commit on `master` `04c1ccc`, in the worktree
`/Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-3`.
Regression: `cpp/selftest/regression-restart-notrun.sh` (exit 0 correct / 1 defect present /
2 could not run; honours `REGRESSION_RESTART_TOOL`).

This file was written inside the worktree because the fixing session's harness refused a
write to the shared checkout's `docs/audits/2026-11-07-aggressive-audit/repro/FIX-restart-notrun/`;
it is NOT part of the fix commit. Copy it to that path.

**Nothing was compiled in the fixing session** (the heavy slot was busy). The checker was
dry-run against the RECORDED pre-fix report instead — see "What has already been shown"
below. The observations this plan asks for are the first ones against a binary.

## HEAVY

`ea_restart` accepts exactly 1,000,000 samples (`restart_main.cpp` requires `data.len ==
MIN_SIZE`; `EA_ALLOW_SHORT_DATASET` is not consulted on that path), so every step below
that runs the tool is a 1,000,000-sample run by the brief's definition. Measured cost of the
one run the test makes: `ea_restart -n -v -o` on the de Bruijn matrix took 6 s wall on this
host (x6, 2026-11-07, `logs/experiments/x6-restart.meta`), plus ~10 s for the Python
generator. Memory is modest (one 1 MB matrix and its transpose). Run one at a time with the
heavy slot, `OMP_NUM_THREADS=2`.

## 1. Build the fixed `ea_restart` out of tree

From `BUILD-LINES.md` (the production line, `-o` into scratch). `S` is a scratch directory.

```sh
S=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/fix-restart-notrun
mkdir -p "$S"
cd /Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-3/cpp && \
clang++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 \
  -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include \
  -I/opt/homebrew/opt/openssl@3/include restart_main.cpp -o "$S/ea_restart-fixed" \
  -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
  -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto
shasum -a 256 "$S/ea_restart-fixed"      # record it (instrument rule 4)
```

## 2. Master's binary

Two acceptable sources; the first is cheaper.

- **The production binary** `/Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart`,
  sha256 `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c` (built 2026-11-07
  19:29 from the audit branch, whose `cpp/` is identical to master's: `git diff --stat master
  audit/2026-11-07 -- cpp/` is empty). Verify the digest before using it. Do NOT overwrite it.
- **Or rebuild master out of tree**, for a clean same-compiler pair:
  ```sh
  cd /Users/gmcas/repos/SP800-90B_EntropyAssessment && git worktree add "$S/master-wt" master
  cd "$S/master-wt/cpp" && clang++ <the same line as above> restart_main.cpp -o "$S/ea_restart-master" <same libs>
  ```

## 3. Show the regression FAILING against master's binary (HEAVY, one run)

```sh
cd /Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-3/cpp/selftest
REGRESSION_RESTART_TOOL=/Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart \
  OMP_NUM_THREADS=2 ./regression-restart-notrun.sh > "$S/rrn-master.log" 2>&1; echo "rc=$?"
```

Expected: `rc=1`, last line `regression-restart-notrun: FAIL (3 checks)`. Every `baseline:` line
must read `yes` / a value (the pre-fix run IS accepted: exit 0, validation passed, errorLevel 0,
the row LRS estimate declined exactly once and the `LRS Test` case has `h_c` and lacks `h_r`),
and exactly these three check lines fail:

```
LRS Test carries rowEstimateNotRun true:                   <absent> (the decline is silent)
Overall carries hAssessed = min(h_r, h_c, h_i):            hAssessed <absent>, min 0.5, difference <absent>
hAssessed agrees with the printed min(H_r, H_c, H_I):      json <absent>, text 0.500000
```

If any `baseline:` line is not `yes`, the script says `PRECONDITION FAILED` and reads no
checks — that would mean the binary or the fixture is not what this plan assumes; stop and
read the log rather than counting it as a FAIL of the right kind.

## 4. Show it PASSING against the fixed binary (HEAVY, one run)

```sh
REGRESSION_RESTART_TOOL="$S/ea_restart-fixed" OMP_NUM_THREADS=2 \
  ./regression-restart-notrun.sh > "$S/rrn-fixed.log" 2>&1; echo "rc=$?"
```

Expected: `rc=0`, last line `regression-restart-notrun: PASS`, first line
`[build-state] ea_restart-fixed  asserts=LIVE sha256=<first 16 of the digest from step 1>`,
and

```
LRS Test carries rowEstimateNotRun true:                   yes
LRS Test carries no columnEstimateNotRun (that estimate ran): yes
no other case carries a row or column flag:                none
Overall carries hAssessed = min(h_r, h_c, h_i):            0.5 (min 0.5)
hAssessed agrees with the printed min(H_r, H_c, H_I):      text 0.500000
a declined estimator is not an error:                      errorLevel 0
```

The figures to expect in the report (from x6, unchanged by the fix): `LRS Test` `h_c`
6.4427235787946389; `Overall` `h_r` 6.5833315234342944, `h_c` 6.3726857695387142, `h_i` 0.5,
and now `hAssessed` 0.5 (H_I binds).

## 5. The -q path (HEAVY, one run, optional but cheap once the matrix exists)

The field must not depend on verbosity — that was half the finding. Reuse a generated matrix
(the test deletes its own; regenerate with
`python3 audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py 100 11 "$S/db100.bin"`):

```sh
OMP_NUM_THREADS=2 "$S/ea_restart-fixed" -n -q -o "$S/q.json" "$S/db100.bin" 8 0.5/symbol > "$S/q.out" 2>&1; echo "rc=$?"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); c=[x for x in d["testCases"] if x["testCaseDesc"]=="Overall"]; assert len(c)==1; print(c[0].get("hAssessed"))' "$S/q.json"
```

Expected: `rc=0`, `q.out` empty, printed `0.5`.

## 6. The rule-12 pairs and the rest of the suite (HEAVY: the suite)

The suite reads `cpp/ea_non_iid`, `cpp/ea_iid`, `cpp/ea_restart` beside `cpp/selftest/`. In the
WORKTREE those do not exist, so build all three there with the step-1 line (`-o ea_non_iid`
etc., in the worktree's `cpp/`; this does not touch the main checkout's production binaries).
`non_iid_test_case.h` is included by `ea_non_iid` too, so its binary changes; its report does
not (the two new flags default false and are never set there) — pin-check's figure
`0.12644573619604868` must be unchanged.

```sh
cd /Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-3/cpp/selftest
./regression-restart.sh      > "$S/rr.log"  2>&1; echo "rc=$?"   # R-2, NOVEL-03, C16 pair tests; expect PASS
./regression-notrun.sh       > "$S/rn.log"  2>&1; echo "rc=$?"   # F05 pair test; expect PASS (ea_non_iid unchanged in behaviour)
./run-all-checks.sh --allow-known-platform-deltas > "$S/suite.log" 2>&1; echo "rc=$?"
./regression-docs.sh         > "$S/docs.log" 2>&1; echo "rc=$?"
```

Expected from the suite: `run-all-checks: 27 passed, 0 failed (25 regression scripts
discovered)` and `build-state: 6 of 27 checks declared the artefact they measured` (was 5 of
26; the new member declares). Expected from regression-docs: `PASS` — on the fix tree WITHOUT
binaries it already reports the count checks green (scope statement matches, 9 inventory rows /
12 occurrences, live instruments 88) and fails only the pinned-figure check, which compares the
documents' figure against the current build. If `build-state:` does not read `6 of 27`,
`cpp/selftest/WHAT-A-GREEN-SUITE-ESTABLISHES.md` precondition 3 and its closing paragraph
carry that figure as DERIVED and must be corrected to what was measured.

Already run on the fix tree in the fixing session (no binary needed): `regression-deadguard.sh`
PASS (flag set unchanged at 40 — the first draft of the test added one pattern-C flag and was
corrected); `harness-inventory-mutation-test.sh` PASS (5 of 5).

## 7. x86-64

`.github/workflows/x86-64-platform-facts.yml` runs `run-all-checks.sh` (it reads
`EXPECTED_TOTAL_CHECKS` from the script, so the 27 needs no workflow edit) and
`regression-restart.sh` explicitly. The new script runs through the suite there. Nothing in the
fix is platform-shaped (two booleans and a `min` of three doubles already computed), but per
the guide's reporting rule: until that workflow has run on the fix, every PASS above is a
Darwin arm64 claim.

## What has already been shown (without a build)

The CHECKER was exercised by replaying the recorded x6 pre-fix run through a stub tool
(scratchpad `replay/`: copies a given JSON to the `-o` path, prints the recorded stdout, exits
`REPLAY_RC`):

| replay | result |
|---|---|
| `x6-restart.json` as recorded (pre-fix) | `FAIL (3 checks)` — exactly the three lines in step 3; all baseline lines `yes` |
| the same report with the two fields added | `PASS` |
| mutation: a `columnEstimateNotRun` on `T-Tuple Test` (whose estimate ran) | `FAIL (1 checks)`: "no other case carries a row or column flag: T-Tuple Test" |
| mutation: `hAssessed` set to `h_c` instead of the minimum | `FAIL (2 checks)`: difference 5.87…, json 6.37… vs text 0.500000 |
| mutation: `columnEstimateNotRun` on `LRS Test` (its estimate ran) | `FAIL (1 checks)`: "no columnEstimateNotRun: true" |
| mutation: `LRS Test` given an `h_r` (fixture no longer exercises the defect) | `PRECONDITION FAILED`, exit 1, no checks read |
| mutation: a second case labelled `Overall` | `PRECONDITION FAILED` (labelled read refused: matched 2), exit 1 |
| mutation: tool exit status 1 with a correct report | `PRECONDITION FAILED`, exit 1 |

That establishes the checker can fail and fails for the named reason (rule 7). It establishes
NOTHING about either binary; steps 3 and 4 do that.
