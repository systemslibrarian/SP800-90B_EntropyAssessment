# Regression ledger — 2026-10-11/12 independent audit

Commit-by-commit verdicts on the fork's own repairs: whether each still holds,
and whether the test that guards it would actually notice if it stopped
holding. The second question is the one that found something.

## Method

Every fork repair was read as a production diff and checked for the failure
modes that make a repair worthless — suppressing output, forcing universal
failure, or bypassing a computation just to satisfy a test. None of the 31
repairs does any of those. The four "decline instead of compute" repairs
(F11 §6.3.4, F12 §6.3.2, F15 §6.3.5/6.3.6, F16 §6.3.9) decline on
spec-derived preconditions, and the `-1` sentinel they return is kept out of
the minimum by guards that are themselves part of F12 and R-2.

Each repair was then **mutation tested**: the production hunk was reverted, or
the defect re-introduced, in a detached worktree at the repair's parent commit,
and the guarding regression was run to see whether it failed. **25 of the 28
mutants that could be built and run were caught**, each with the exact line
that failed. Pinned literals were checked for authenticity rather than assumed:
`pin-check`'s `0.12644573619605429` is byte-identical to the reference data, and
the asserted `cond.json` figure `0.9981992801198275` was reproduced to all 17
digits with an independent MCV oracle.

The suite also caught a regression that one of the repairs itself introduced:
`a3dde6f` skipped the LRS test, `regression-271` failed, and `007d0e7`
restored it. That is the discipline working.

## Repairs on master

| Prior finding | Commit | Verdict | Evidence |
|---|---|---|---|
| F02 | `97571de` | Previously repaired and still resolved | regression-width.sh fails 4 checks against 21b0a31 ('wrong or missing (expected 4, inferred true)'); master suite PASS. Scope note: the fields were never added to ea_restart — see finding regression-quality-reconciliation-7. raw/mut-p-0e1ffcd-regression-width.log |
| F03/F04 | `c2f1dcd` | Previously repaired and still resolved | regression-minsize.sh fails 11 checks against 134d377 ('ea_non_iid: short file refused: exit 0 — NOT refused', 'escape marked in JSON: flag absent'). Composition: a short -l block is refused with errorLevel -1 and the escape requires the exact string '1'. raw/mut-p-c2f1dcd-regression-minsize.log, raw/comp/comp.log |
| F05 | `dfe325a` | Previously repaired and still resolved | regression-notrun.sh fails 2 checks against 6b60f9d ("compliant input, LRS cannot run, is recorded: flags ''"). But its only 1,000,000-sample case is in a silent-skip branch — finding regression-quality-reconciliation-4, confirmed by execution. raw/mut-p-69b6094-regression-notrun.log, raw/skipopen/skipopen-notrun.log |
| F09 | `69b6094` | Previously repaired and still resolved | Generic path: regression-multimmc.sh reports 'r = 6603, expected 24' against 6b60f9d and r = 24 on master; refdata figure 7.9268088197517388 matches refdata/truerand_8bit.res:93 on both. Diff re-read: winner_correct flag, run reset at end of round, both MultiMMC paths. Binary path does not discriminate — finding regression-quality-reconciliation-6. raw/mut-p-69b6094-regression-multimmc.log |
| F11 | `c0ee84a` | Previously repaired and still resolved | regression-estimator-guards.sh against ed88de9: '#263 compression declines at v=1 (v1_nan): ran anyway' and 'no NaN/inf sigma-hat: NaN or inf still produced'; 13 checks fail. Decline is spec-derived (§6.3.4 step 5, 1/(v-1)). raw/mut-p-c0ee84a-regression-estimator-guards.log |
| F12 | `c217f20` | Previously repaired and still resolved | regression-estimator-guards.sh against c0ee84a: '#264 collision declines at v=1: ran anyway', 'no unmeasured 1.0 from NaN: still produced'; 9 checks fail. The commit also adds the `ret_min_entropy >= 0` guards at both call sites, which is the part that keeps -1 out of the minimum. raw/mut-p-c217f20-regression-estimator-guards.log |
| F14 | `6b60f9d` | Previously repaired and still resolved | Proxy only (the end-to-end case needs >25.8 Gbit). 'F14 narrowing the dictionary fails the build: it BUILT — the guard is not protecting' against all three pre-F14 parents; and I supplied the missing clean-build control: clean copy rc=0, narrowed copy rc=2 with the exact static_assert at compression_test.h:108. raw/f14/f14.log |
| F15 | `21b0a31` | Previously repaired and still resolved | regression-estimator-guards.sh #261 block: 5 of 6 cases 'ABORTED (exit 134)' against c2f1dcd/ed88de9/c0ee84a, plus 'repeat-free data declines and reports: missing decline or figure'. raw/mut-p-ed88de9-regression-estimator-guards.log |
| F16 | `ed88de9` | Previously repaired and still resolved | regression-estimator-guards.sh #257 block against c2f1dcd: 'heap-buffer-overflow STILL PRESENT' at L=4,5,8,12,16 and 'declines below D_MMC+1: no decline reported'; 19 checks fail. The ASan binary is built from cpp/non_iid_main.cpp, i.e. production source. raw/mut-p-ed88de9-regression-estimator-guards.log |
| F18 / N-06 | `cdb5cd6` | Previously repaired and still resolved | regression-nonregular.sh fails 8 checks against 21b0a31 — '/dev/zero: TIMED OUT — still hangs', FIFO likewise, and 'absent file no hash invented: errorLevel set, sha256 absent' failing. The ringOsc hash literal in that script is the file's real SHA-256 (verified). raw/mut-p-0e1ffcd-regression-nonregular.log |
| F19 | `0e1ffcd` | Previously repaired and still resolved | regression-subset.sh fails 5 checks against 21b0a31 ('offset multiplication overflow: exit 0', 'zero-sample subset request: exit 0', 'subset provenance in JSON: missing or wrong', 'short final block recorded: not recorded'). Its sha256-scope assertion cannot discriminate — finding regression-quality-reconciliation-5. raw/mut-p-0e1ffcd-regression-subset.log |
| N-01 | `c8799f4` | Previously repaired and still resolved | regression-chisquare.sh fails 2 checks against c748c0c ("m = 1 fails the chi-square battery: got 'Passed', expected 'Failed'", 'm = 1 reported with its reason: missing'); m>=2 and both NIST controls still pass. Expected value is SP 800-90B §5.2.3 verbatim. Fixtures are 100,000 samples under the escape — finding regression-quality-reconciliation-8. raw/mut-p-c8799f4-regression-chisquare.log |
| N-02 | `134d377` | Previously repaired and still resolved | regression-271.sh fails 2 checks against da0265c (chi-square and LRS 'got Passed, expected Failed' under -c) while the -i contrast still passes. Composition: under -c -l the bitstring length follows the subset ('Number of Binary samples: 300000'). Fixture is 10,000 samples under the escape. raw/mut-p-134d377-regression-271.log, raw/comp/e_iid_c_short_l.out |
| N-04 | `db7a2ba` | Previously repaired and still resolved | regression-restart.sh against c748c0c: nan and NAN 'CRASHED (signal, exit 134)', and abc / 1.5x / empty / 3.2e all 'exit 0, expected a refusal'; the three valid-H_I controls still run. On master all eight bad values are refused with exit 255. raw/mut-p-c8799f4-regression-restart.log, raw/skipopen/skipopen.log |
| N-06 | `fd83a43` | Previously repaired and still resolved | regression-restart.sh against c748c0c: 'N-06 -i no hash invented on failure: errorLevel 0 or a sha256 was reported'; master and the repair build both report 'errorLevel set, sha256 absent' in both modes and the real hash on a valid run. raw/mut-p-c8799f4-regression-restart.log |
| N-09 | `47d6624` | Previously repaired and still resolved | regression-output.sh fails 3 checks against c748c0c ('-o into a missing directory: exit 0, expected a refusal naming the output file', for all three tools); writable-path controls wrote 2475 and 2092 bytes. Composition with #252 verified: an unwritable report wins (exit 255, error printed) over the IID-failure status. The /dev/full half is skipped on macOS. raw/mut-p-c8799f4-regression-output.log, raw/comp-repair/n09x252.log |
| R-2 | `d892b90` | Previously repaired and still resolved | regression-restart.sh against c748c0c: 'R-2 the -1 sentinel is not folded in: H_r is -1 (still folded)' and 'no false validation failure: still fails validation', with the precondition asserted ('the LRS estimate really does decline: yes'). On the repaired build H_r 6.583332 and validation passes. Its block can be silently skipped — finding regression-quality-reconciliation-4. raw/mut-p-c8799f4-regression-restart.log, raw/skipopen/skipopen.log |
| R-3 | `23dca69` | Previously repaired and still resolved | regression-restart.sh against c748c0c: 'R-3 -i read failure recorded in JSON: errorLevel 0 or no message'; on the repaired build both modes report 'errorLevel set with a message' and a successful run still reports errorLevel 0. raw/mut-p-c8799f4-regression-restart.log |
| NOVEL-01 | `da0265c` | Previously repaired and still resolved | regression-272.sh fails 3 checks against 55a7f65 — both source mutants 'NOT CAUGHT — the mutant passed the comparison' and 'selftest exit status: ZERO despite a mismatch in biased-random-bits — the #272 fault'. The script builds baseline + 2 mutants from production source and guards its own patterns. raw/mut-p-da0265c-regression-272.log |
| NOVEL-02 | `9f64f62` | Previously repaired and still resolved | regression-iid-json.sh fails all 4 checks against 47d6624 (rc=1, 834 s): hBitstring 'reported 1.0', hOriginal 'reported 8.0', 'hAssessed at -q matches the -vvv figure: json 1.0 vs text 0.99504301513122573', 'still 1.0'; both positive controls pass. Master run PASS rc=0 in 1324 s, and I reproduced its asserted cond.json figure 0.9981992801198275 to 17 digits with an independent MCV oracle. raw/mut-p-9f64f62-regression-iid-json-retry.log, raw/pos/master-regression-iid-json.log |
| REV-003 | `8f0469c` | Previously repaired and still resolved | The pre-8f0469c script, run against the pre-F09 build, printed 'F09 binary path still produces a run length: r = 17' — a value with no assertion, confirming the original defect. The replacement does assert a value. But it does not discriminate the F09 defect — finding regression-quality-reconciliation-6. raw/rev003-old-multimmc-vs-preF09.log |
| REV-005 | `8f0469c` | Previously repaired and still resolved | Confirmed by the two values the mutant runs print: this platform produces 0.15932269772157773 while refdata records 0.15932269772157898, a 7.8e-15 relative difference that the old literal rejected and the new refdata+1e-9 comparison accepts. raw/mut-p-ed88de9-regression-estimator-guards.log |
| REV-006 | `590c83a` | Previously repaired and still resolved | With a selftest stub that exits 1 printing no summary line, parent 06dff41 reported 'selftest PASS (only the known upstream #155 platform files)' rc=0 (fail-open reproduced) while master reports 'FAIL (exit 1, no "selftest: FAIL" summary line to classify)' rc=1. raw/harness/rev006-master, raw/harness/rev006-parent-06dff41 |
| F20 | `-t with -c` | Not reproduced or ruled out; stays not-a-bug | `-c -t` on uniform-8bit: 1,000,000 binary symbols, H_bitstring 0.85758328465549472, Assessed 6.8606662772439577; `-c -a`: 8,000,000 binary symbols, 0.92641349982744703, Assessed 7.4113079986195762. Both rc=0 and internally consistent (Assessed = H_bitstring x word_size). No new evidence. raw/comp/f_c_t_8bit.out, raw/comp/g_c_a_8bit.out |
| F01 | `withdrawn 2026-10-03` | Not reproduced or ruled out; withdrawal stands | `ea_non_iid -i -vv bin/truerand_1bit.bin 8` gives bitsPerSymbol 8, bitsPerSymbolInferred false, 2 distinct symbols and H_original 0.82967708323411438 — the same figure as the width-1 run, consistent with two-valued multi-bit data being treated as binary per §4.4.2/§5. raw/comp/n_noniid_w8_on1.json |

## Repairs on the unmerged repair branch (`2d4b135`)

| Prior finding | Commit | Verdict | Evidence |
|---|---|---|---|
| HARNESS-AUD-01 | `65de84c` | Previously repaired and still resolved (repair branch); still open on master | With bin/ reduced to one file, master's selftest reports 'selftest: PASS (1 files)' rc=0; the repair's reports "fixture-inventory: missing mandatory input 'biased-random-bits.bin'" and 'selftest: FAIL (fixture inventory incomplete or untrusted)' rc=1. regression-selftest-inventory.sh rejects all 7 of its own mutations. raw/harness/master-selftest.out, raw/harness/repair-selftest.out, raw/harness/inv.out |
| C-01 | `6f84ad7 + b3db7ab` | Previously repaired but incomplete — the fix is correct, the regression is not | The `delete results` -> `delete[] results` hunk is correct and the shipped control does fail against an ASan build of the unrepaired code (alloc-dealloc-mismatch at restart_main.cpp:161, rc=134). But the control passes against the unrepaired release build, passed against the unrepaired ASan build before b3db7ab, has ungated assertions, and is never run by the suite — finding regression-quality-reconciliation-2. raw/c01/c01.log, raw/c01/b3db7ab/pre-b3db7ab.log, raw/c01/vacuity/stub.out |
| N-07 | `c01fb43` | Previously repaired but incomplete — the fix is correct, the regression cannot fail | Fix verified behaviourally: -l 1,700000 gives sha256 = SHA-256 of tail -c 300000 (51bd286d...2533), sha256Scope assessed-sample-bytes, assessedSampleCount 300000, and it composes with -c and the escape. Regression is inert: the hunk-revert mutant yields AssertionError then 'PASS' rc=0 — finding regression-quality-reconciliation-1. raw/n07-reverify.log, raw/n07scope/n07scope.log |
| IID #153 / #252 | `a3dde6f + 007d0e7` | Previously repaired and still resolved (repair branch) | regression-iid-failclosed.sh fails 11 checks against c01fb43, including 'width 1 failed IID suite returns status 1: got 134' (the #153 underflow abort) at every width 1-8 and 'IID restart failure returns no entropy award: FAIL (status 134)'. The script carries an independent §5.2.5 log-domain oracle over 1,000,000-sample fixtures plus two positive controls. 007d0e7's half is caught by regression-271 against a3dde6f ("LRS test: got '', expected 'Failed'"), i.e. the suite caught a regression introduced by a repair. raw/mut-r-c01fb43-regression-iid-failclosed.log, raw/mut-r-a3dde6f-regression-271.log |
| IND-02 | `ea87f1e` | Previously repaired and still resolved, with a scope gap | harness-inventory-mutation-test.sh returns rc=1 with master's run-all-checks ('deleted script did not fail as required (exit 0)') and rc=0 with the repair's, passing the complete/deletion/injection/rename/duplicate controls. The inventory covers only regression-*.sh — finding regression-quality-reconciliation-3. raw/harness/ind02-master.out, raw/harness/ind02-repair.out |
| N-08 | `031d7ee` | Previously repaired and still resolved, with one untested hunk | 6 checks fail against a3dde6f ('N-08 ea_non_iid refuses width 8x: exit 255, parser accepted it' and five more across regression-width/subset/restart). The transpose_main.cpp hunk is covered by nothing — finding regression-quality-reconciliation-9. raw/mut-r-a3dde6f-regression-width.log |
| N-10 | `094189c` | Previously repaired and still resolved (repair branch); master still emits mean/median | regression-iid-json.sh fails 3 checks against a3dde6f ('N-10 JSON uses explicit statistic names: ambiguous or missing fields', 'stdout labels the translated median: still says only Median', 'sparse-alphabet domains are distinguishable: labels or values wrong'). Master's IID report still carries mean 0.5001566666666667 / median 0.5, confirming it is open there. raw/mut-r-a3dde6f-regression-iid-json.log, raw/comp/e_iid_c_short_l.json |
| NOVEL-03 | `25fbb54` | Previously repaired and still resolved | Hunk-revert mutation (the `testResultJson["dataLayout"] = dataLayout;` emission removed from iid/permutation_test_result.h:41) makes restart-report-label-test exit 1 with 'result 0 is not labelled rows iteration 0'; the unmutated source gives 'restart-report-label-test: PASS (rows 0,1,2; columns 0,1,2)' rc=0. regression-restart.sh gates on that exit status and also fails if the test will not build. raw/novel03/novel03.log |
| build scope | `876ba05` | Previously repaired and still resolved | `make -Bn all` plans ea_conditioning ea_iid ea_non_iid ea_restart ea_transpose on master and ea_iid ea_non_iid ea_restart on the repair branch; regression-docs.sh asserts it ('make all builds exactly the supported programs: ea_non_iid ea_iid ea_restart'). raw/harness, $S/logs/repair-run-all-checks.log |

## What this means for merging the repair branch

These are two different claims and the evidence for one does not carry the
other. Kept apart deliberately.

### Claim 1 — repairs supported by a guard that was seen to fail

For each of these, the production hunk was reverted (or the defect
re-introduced) and the named guard **failed, with the assertion that failed
recorded**. This is what the mutation testing and the pinned-literal checks are
evidence for, and it is all they are evidence for.

| Repair | Commit | Guard seen to fail | What it printed against the unrepaired code |
|---|---|---|---|
| F02 | `97571de` | `regression-width.sh` | 4 checks: "wrong or missing (expected 4, inferred true)" |
| F03/F04 | `c2f1dcd` | `regression-minsize.sh` | 11 checks: "short file refused: exit 0 — NOT refused" |
| F09 (generic path) | `69b6094` | `regression-multimmc.sh` | "r = 6603, expected 24" |
| F11 | `c0ee84a` | `regression-estimator-guards.sh` | 13 checks: "#263 compression declines at v=1: ran anyway" |
| F12 | `c217f20` | `regression-estimator-guards.sh` | 9 checks: "#264 collision declines at v=1: ran anyway" |
| F15 | `21b0a31` | `regression-estimator-guards.sh` | 5 of 6 cases "ABORTED (exit 134)" |
| F16 | `ed88de9` | `regression-estimator-guards.sh` | 19 checks: "heap-buffer-overflow STILL PRESENT" at L = 4, 5, 8, 12, 16 |
| F18 / N-06 | `cdb5cd6` | `regression-nonregular.sh` | 8 checks: "/dev/zero: TIMED OUT — still hangs" |
| F19 (overflow, provenance) | `0e1ffcd` | `regression-subset.sh` | 5 checks: "offset multiplication overflow: exit 0" |
| N-01 | `c8799f4` | `regression-chisquare.sh` | 2 checks: "m = 1 fails the chi-square battery: got 'Passed'" |
| N-02 | `134d377` | `regression-271.sh` | 2 checks: chi-square and LRS "got Passed, expected Failed" under `-c` |
| N-04 | `db7a2ba` | `regression-restart.sh` | `nan`/`NAN` "CRASHED (signal, exit 134)"; `abc`, `1.5x`, empty, `3.2e` "exit 0, expected a refusal" |
| N-06 | `fd83a43` | `regression-restart.sh` | "no hash invented on failure: errorLevel 0 or a sha256 was reported" |
| N-09 | `47d6624` | `regression-output.sh` | 3 checks: "-o into a missing directory: exit 0, expected a refusal" |
| R-3 | `23dca69` | `regression-restart.sh` | "-i read failure recorded in JSON: errorLevel 0 or no message" |
| NOVEL-01 | `da0265c` | `regression-272.sh` | 3 checks, including "selftest exit status: ZERO despite a mismatch" |
| NOVEL-02 | `9f64f62` | `regression-iid-json.sh` | all 4 checks: "json 1.0 vs text 0.99504301513122573" |
| REV-006 | `590c83a` | `run-all-checks.sh` classification | parent `06dff41` reported PASS rc=0 on a stub exiting 1; master reports FAIL rc=1 |
| HARNESS-AUD-01 | `65de84c` *(repair)* | `regression-selftest-inventory.sh` | rejects all 7 of its own mutations; selftest FAIL rc=1 with `bin/` reduced to one file |
| IID #153 / #252 | `a3dde6f` + `007d0e7` *(repair)* | `regression-iid-failclosed.sh` | 11 checks: "width 1 failed IID suite returns status 1: got 134" at every width 1-8. `007d0e7`'s half was caught by `regression-271` against `a3dde6f` |
| IND-02 | `ea87f1e` *(repair)* | `harness-inventory-mutation-test.sh` | rc=1 against master's `run-all-checks` ("deleted script did not fail as required") |
| N-08 (parser hunks) | `031d7ee` *(repair)* | `regression-width.sh`, `-subset`, `-restart` | 6 checks: "ea_non_iid refuses width 8x: exit 255, parser accepted it" |
| N-10 | `094189c` *(repair)* | `regression-iid-json.sh` | 3 checks: "JSON uses explicit statistic names: ambiguous or missing fields" |

### Claim 2 — repairs supported only by a guard that cannot fail, or by no guard

Nothing in Claim 1 applies here. The mutation result above says nothing about
these, and the pinned literals say nothing about them either.

| Repair | Commit | Why its guard does not hold it |
|---|---|---|
| **C-01** | `6f84ad7` + `b3db7ab` *(repair)* | `sanitizer-restart-c01.sh` has its assertions in an unchecked heredoc under an unconditional `PASS`; it also passes against the unrepaired **release** build, passed against the unrepaired ASan build before `b3db7ab`, and **is in no inventory, so no suite ever runs it**. The fix itself (`delete` → `delete[]`) is correct and does fail an ASan build of the unrepaired code when run by hand. |
| **N-07** | `c01fb43` *(repair)* | `regression-input-identity.sh` is inert: the hunk-revert mutant yields `AssertionError` then `PASS` rc=0. The fix was confirmed behaviourally by the auditor instead (`-l 1,700000` → `sha256` = SHA-256 of the 300,000 assessed bytes, `sha256Scope` `assessed-sample-bytes`), but no test holds it. |
| **N-08**, `transpose_main.cpp` hunk | `031d7ee` *(repair)* | Covered by nothing. The parser hunks are in Claim 1; this one is not. |
| **All of `ea_conditioning`** | — | Exercised by no regression at all, on either branch. |
| **F14** | `6b60f9d` | No end-to-end guard is possible here (> 25.8 Gbit of input). Supported by a build-time control only: a clean copy builds rc=0 and a narrowed-dictionary copy fails rc=2 on the `static_assert` at `compression_test.h:108`. That control was seen to fire, but it guards the type, not the behaviour. |

### Claim 3 — guarded, but conditionally or partially

Placing these in Claim 1 unqualified would be the error worth avoiding: their
guards *were* seen to fail, but only under a condition that is not itself
guaranteed.

| Repair | Commit | The condition |
|---|---|---|
| **F05** | `dfe325a` | `regression-notrun.sh` fails 2 checks against `6b60f9d` — but its only 1,000,000-sample case sits in a branch skipped when `gen_debruijn.py` is absent, and the skip does not reach the exit status. Guarded only while that file stays in the frozen audits archive. |
| **R-2** | `d892b90` | `regression-restart.sh` printed "H_r is -1 (still folded)" against `c748c0c` — in the same skippable de Bruijn branch. Same condition. |
| **F09**, binary path | `69b6094` | The generic path is in Claim 1. The binary-path check agrees with the tool on both sides of the repair, so it does not discriminate the defect. |
| **F02** on `ea_restart` | `97571de` | The width fields were never added to `ea_restart`, so the guard covers two of the three tools. |
| **F19**, sha256 scope | `0e1ffcd` | The overflow and provenance assertions are in Claim 1; the sha256-scope assertion is satisfied by both of the fork's two incompatible scope policies, so it discriminates nothing. |
| **N-01**, **N-02** | `c8799f4`, `134d377` | Their guards fail as described, but on 100,000- and 10,000-sample fixtures under `EA_ALLOW_SHORT_DATASET`. Both are IID-decision repairs tested only below the compliance minimum. |

### Bearing on the merge

The repair branch should land on the strength of Claim 1, which is substantial,
and on the auditor's direct behavioural verification of C-01 and N-07. It
should not land on the belief that its suite will keep those two in place,
because for C-01 and N-07 the suite is inert — and in C-01's case not even
wired up. Those two guards need rewriting, and `regression-notrun.sh` and
`regression-restart.sh` need their skip to reach the exit status. See
`DEAD-GUARD-SWEEP.md` for the full sweep and `C08-harness-cannot-fail` in
`REPORT.md`.
