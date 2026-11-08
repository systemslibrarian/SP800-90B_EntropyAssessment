# FIX-multimmc-lookup — test plan

Fix branch: `fix/multimmc-lookup`, created from `master` (04c1ccc), in the worktree
`/Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-4`.
Finding: F10 / C01 (FORK-DIVERGENCE-AND-TRUST.md A.1; FINDINGS.md of this audit; experiment X3,
`logs/experiments/CHAIN-2.log`). Code change: `cpp/non_iid/multi_mmc_test.h`, both paths — every
depth is looked up independently, as SP 800-90B 6.3.9 step 4.b.i (PDF p. 61) is written.
Regression: `cpp/selftest/regression-multimmc-lookup.sh`.

The fix was WRITTEN WITHOUT A BUILD (the heavy slot was busy). Nothing below has been run against a
compiled fix; the pre-fix figures the test asserts against come from the C++-transcribed model that
equalled the tool exactly on both 1,000,000-sample X3 files, and the post-fix figures from the
spec-literal model and `reference/py90b/multimmc.py`, which agree exactly. This plan is how the
orchestrator turns those into observations (guide step 5: a regression is observed to fail, not
reasoned to fail).

Every tool run below: `OMP_NUM_THREADS=2`; outputs to files, never piped into head/tail (rule 17);
read the producer's exit status; name the binary by sha256 (instrument rule 4 — the test prints a
`[build-state]` line itself).

## 0. Scratch area

```sh
S=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fix-multimmc-lookup
mkdir -p "$S/master" "$S/fix"
```

## 1. Build master's binary and the fix's binary, out of tree (HEAVY, one at a time)

The exact production line from `BUILD-LINES.md`, with `-o` into the scratch area. The main checkout is
on `master` at 04c1ccc and must stay as it is: do NOT write `cpp/ea_non_iid` there.

Master (source: the main checkout, which is master):

```sh
cd /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp && clang++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 \
  -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include \
  -I/opt/homebrew/opt/openssl@3/include non_iid_main.cpp -o "$S/master/ea_non_iid" \
  -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
  -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto > "$S/build-master.log" 2>&1; echo $? > "$S/build-master.rc"
```

(If the main checkout is no longer at 04c1ccc, build from `git worktree add "$S/master-tree" 04c1ccc`
and `cd "$S/master-tree/cpp"` instead.)

Fix (source: the fix worktree):

```sh
cd /Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-4/cpp && clang++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 \
  -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include \
  -I/opt/homebrew/opt/openssl@3/include non_iid_main.cpp -o "$S/fix/ea_non_iid" \
  -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
  -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto > "$S/build-fix.log" 2>&1; echo $? > "$S/build-fix.rc"
```

Both `.rc` files must read `0` and both logs must be empty of warnings about `multi_mmc_test.h`.
Record `shasum -a 256 "$S/master/ea_non_iid" "$S/fix/ea_non_iid"` in `$S/binaries.sha256`.

Expect the master binary to behave as the production binary (sha256
`1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`) did in the light probes of
2026-11-08 (section 5).

## 2. Show the regression FAILING against master's binary

```sh
cd /Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-4/cpp/selftest
REGRESSION_MULTIMMC_LOOKUP_BINDIR="$S/master" OMP_NUM_THREADS=2 ./regression-multimmc-lookup.sh \
  > "$S/master-run.out" 2> "$S/master-run.err"; echo $? > "$S/master-run.rc"
```

Expected (read the files, not a pipe): `master-run.rc` = `1`; `master-run.out` ends with
`regression-multimmc-lookup: FAIL (4 checks)` and contains exactly these four failing lines
(predicted by the model; the orchestrator records what was actually printed):

```
  F10 gadget 104,000 x 8-bit: Literal C (chained: 2288):           got '2288', expected 2409
  F10 x F09 gadget 104,000 x 8-bit: Literal r (chained: 12):       got '12', expected 20
  F10 naive 104,000 x 8-bit: Literal C (chained: 1998):            got '1998', expected 1911
  F10 x F09 naive 104,000 x 8-bit: Literal r (chained: 17):        got '17', expected 16
```

and every other line passing: the 6.3.9 worked example (3/3/7), the two 20,000-sample BASELINE arms
(Literal 96/2/19998 and Bitstring 81118/16/159998 against the spec model), the three PAIR #257 arms
(20,000 bits 9896/13/19998; 16 bits decline; 17 bits 5/4/15), and the `N = 103998` lines. A failing
BASELINE or PAIR line against master means the fixture or the model is wrong, NOT the defect, and
the fix must not be trusted until that is understood (rule 7). The `[build-state]` line must name
`$S/master/ea_non_iid`'s sha256.

## 3. Show the regression PASSING against the fix's binary

```sh
REGRESSION_MULTIMMC_LOOKUP_BINDIR="$S/fix" OMP_NUM_THREADS=2 ./regression-multimmc-lookup.sh \
  > "$S/fix-run.out" 2> "$S/fix-run.err"; echo $? > "$S/fix-run.rc"
```

Expected: `fix-run.rc` = `0`; `regression-multimmc-lookup: PASS`; `[build-state]` names
`$S/fix/ea_non_iid`'s sha256; the heavy arm line reads `NOT RUN`.

## 4. The compliant-size X3 files (HEAVY: two 1,000,000-sample runs per binary; serialise)

```sh
EA_REGRESSION_HEAVY=1 REGRESSION_MULTIMMC_LOOKUP_BINDIR="$S/master" OMP_NUM_THREADS=2 ./regression-multimmc-lookup.sh \
  > "$S/master-heavy.out" 2> "$S/master-heavy.err"; echo $? > "$S/master-heavy.rc"
EA_REGRESSION_HEAVY=1 REGRESSION_MULTIMMC_LOOKUP_BINDIR="$S/fix" OMP_NUM_THREADS=2 ./regression-multimmc-lookup.sh \
  > "$S/fix-heavy.out" 2> "$S/fix-heavy.err"; echo $? > "$S/fix-heavy.rc"
```

Expected against master: the four 104,000-sample failures plus four more — gadget C `506288` for
`534409`, r `12` for `20`; naive C `449998` for `421911`, r `17` for `16` — these four are the
figures the production binary PRINTED in X3 (`x3-gadget-tool.stdout`, `x3-naive-tool.stdout`), so
they are measured, not modelled. Expected against the fix: PASS. The fixtures are regenerated by the
test and digest-checked against the X3 manifest (`095aeaf1…`, `cf6e4f28…`) before any figure is read.

## 5. What was run on 2026-11-08 without a build (for the record)

All against the production binary sha256 `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`,
`EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`, each at most 20,000 samples, outputs in the session
scratchpad `probe/`:

| input | tool printed (Literal MultiMMC C / r / N) | spec-literal model |
|---|---|---|
| 6.3.9 worked example (9 symbols, width 2) | 3 / 3 / 7 | 3 / 3 / 7 |
| X3 fill prefix, 20,000 x 8-bit (sha256 5948b470…) | 96 / 2 / 19998; Bitstring 81118 / 16 / 159998 | identical |
| 20,000 bits (sha256 cbc08c8b…) | 9896 / 13 / 19998 | identical |
| 16 bits | declines: "not enough samples to run multiMMC test (need more than 16)" | — |
| 17 bits | 5 / 4 / 15 | identical |

Derivations (no tool run): the 104,000-sample fixtures' spec-literal values were computed by the
embedded model and by `py90b.multimmc` (`--k-mode=observed`) — gadget C=2409 r=20, naive C=1911
r=16, both agree; the chained values 2288/12 and 1998/17 come from the C++-transcribed model
(`harness/experiments/x3_multimmc_orphans.py` `mmc_cpp`, replicated in the scratchpad), which equalled
the tool on both X3 files. The replica generator reproduces the X3 manifest digests for the 1,000,000-
sample files and the 20,000 prefix byte for byte. Sweep: at 100,240 samples the two models give the
same C and r (only the scoreboards differ, depth 1 still winning from the fill phase); 104,000 is the
smallest sweep point at which C and r separate.

Refdata: `py90b.multimmc` on `bin/truerand_8bit.bin` (8), `biased-random-bytes.bin` (8),
`normal.bin` (8) and `truerand_4bit.bin` (4) gives C and r IDENTICAL to the `Literal MultiMMC` lines in
`cpp/selftest/refdata/*.res` (3948/3, 799884/73, 19209/4, 62518/6), each with the cap bound, so no
reference figure is DERIVED to move; the other seven samples are 1-bit or 10,000 samples long and
cannot reach the mechanism. This is a derivation; section 6 measures it.

## 6. What else to run (in the fix worktree, after the binaries exist)

The suite needs `../ea_non_iid`, `../ea_iid`, `../ea_restart` beside `cpp/selftest/` IN THE FIX
WORKTREE (not the main checkout). Build `iid_main.cpp` and `restart_main.cpp` with the same line into
`/Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-4/cpp/` (two more
HEAVY jobs, serialised) and copy `$S/fix/ea_non_iid` there. Then, from that `cpp/selftest/`:

```sh
./run-all-checks.sh --allow-known-platform-deltas > "$S/suite.out" 2>&1; echo $? > "$S/suite.rc"
#   expect: run-all-checks: 27 passed, 0 failed (25 regression scripts discovered)
#   expect: build-state: 6 of 27 checks declared the artefact they measured   (was 5 of 26)
./regression-docs.sh > "$S/docs.out" 2>&1; echo $? > "$S/docs.rc"        # expect PASS
./harness-inventory-mutation-test.sh > "$S/inv.out" 2>&1; echo $? > "$S/inv.rc"   # expect 5 of 5
./regression-deadguard.sh > "$S/dg.out" 2>&1; echo $? > "$S/dg.rc"       # expect PASS, 40 flags (already run: unchanged)
```

`selftest` runs inside `run-all-checks.sh`. The `Literal MultiMMC` lines of every `refdata/*.res` must
still match (section 5 derives that they do). IF ANY MultiMMC LINE DIFFERS, STOP: guide ground rule 5
applies — a deliberate figure change regenerates only the affected files, in a commit that explains the
change — and the derivation in section 5 was wrong somewhere, which must be understood first.

Also worth one run each: `regression-multimmc.sh` (F09's own regression; it must still pass — r = 24
on its dataset, truerand_8bit's Literal MultiMMC figure unchanged) and
`regression-estimator-guards.sh` (#257's decline under ASan; it builds its own sanitizer binary,
HEAVY).

## 7. Record the observations, then the owner's record

1. Put the four observed failing lines and the two binaries' sha256 into the `OBSERVED FAILING`
   section of `regression-multimmc-lookup.sh` and into the fix commit's message (amend on the fix
   branch before it is merged, or a follow-up commit; guide step 5 and step 8).
2. Not done by this fix and left to the owner (guide step 9, one commit each): the tracker's F10 row
   (`UNCONFIRMED` → `FORK-FIXED` with the commit, test path and verification); `FORK-DIVERGENCE-AND-TRUST.md`
   A.1 `C01/F10` (`NOT REPAIRED` → repaired, and the table at line 608); `audits/2026-10-11-independent-audit/oracles/entropy_floor.py`'s
   `C01 = 3.69e-4` margin term, which the floor oracle applies above width 1 and which this repair
   removes the reason for; FINDINGS.md of this audit, which names the offered branch
   `fix/multimmc-independent-lookup` while the branch is `fix/multimmc-lookup`.
3. x86-64: the x86-64 workflow runs the suite on push; the test's expected values are integers from
   the standard's algorithm, so nothing platform-dependent is compared, but say which platform each
   run was on when reporting (guide step 5).
