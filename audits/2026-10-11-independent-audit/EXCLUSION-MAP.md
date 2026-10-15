# Prior findings rechecked — 2026-10-11/12 independent audit

Every prior finding this round looked at again, with the disposition each
auditor reached and the evidence behind it. Where two auditors rechecked the
same finding independently, both rows are kept; a disagreement between them is
itself a result and is not reconciled away here.

122 distinct prior findings were rechecked, in 149 separate rechecks.

## 590c83a regression-docs.sh check 9 (wrapped stale claims)

- **Previously repaired and still resolved** — `build-portability-harness-docs`
  The matcher finds four phrase occurrences today — README.md:19 'After NIST reviewed', NOTICE:36 'agreed with several of them', NOTICE:140 "after NIST's review", BUILDING.md:14 'After NIST reviewed' — and all four sit inside 'Correction (2026-10-02)' paragraphs, which is exactly what the EXEMPT regex is for; I read each paragraph to confirm. Running the same matcher over FORK-DIVERGENCE-AND-TRUST.md and AGENTS.md (which the DOCS list omits) found nothing. regression-docs: PASS in both suite logs.

## 590c83a run-all-checks fail-open (empty selftest classification)

- **Previously repaired and still resolved** — `build-portability-harness-docs`
  run-all-checks.sh:72-75 fails when selftest exits non-zero with no 'selftest: FAIL' summary line or with a line naming no file; my stub tests exercised the adjacent branches and reached lines 76-78 and 79-84 as documented. The magnitude blindness beside it is new (finding build-portability-harness-docs-2).

## #153

- **Still open on master (and upstream); repaired and resolved on the repair branch (a3dde6f) — fail-closed verified and decision proven equivalent** — `estimators-ttuple-lrs`
  master/upstream ea_iid abort rc=134 at lrs_test.h:683/:657 on alternating-1bit, period6-1bit, repeated-block-1bit (runs/iid153); repair rc=1, JSON errorLevel 2, IID false, W=999998/999994/995904, Pr=0; exact Pr ~1e-301027 (fail correct); algebraic equivalence W*ln p_col >= ln(-expm1(ln0.999/N)) derived; 192,032-point boundary scan with 0 disagreements (numerics.json D).
- **Reproduces on master; fixed on the repair branch** — `memory-safety-fuzz`
  Master ASan ea_iid on fixtures/valid/period6-1bit.bin -> rc 134 'Assertion failed: (p_colPower >= LDBL_MIN), function len_LRS_test, file lrs_test.h, line 683'; also on alternating-1bit and repeated-block-1bit. The short-file fuzz hit lrs_test.h:683 47 times and :684 91 times. The repair branch deletes both asserts and works in the log domain (diffs/repair-vs-master-production.diff, lrs_test.h hunk), giving rc 1 with errorLevel 2 'IID test suite failed' and passedLongestRepeatedSubstringTest false - so those 138 short-input aborts are retired as well.

## #153 (IID LRS p_colPower underflow assert on valid data)

- **Confirmed still OPEN on master (inherited, len_LRS_test byte-identical to upstream); RESOLVED on repair** — `iid-track`
  master alternating-1bit and period6-1bit: 'Assertion failed: (p_colPower >= LDBL_MIN), function len_LRS_test, file lrs_test.h, line 683', exit 134, no JSON despite -o. Repair: W=999998/999994, Pr(X>=1)=0, 'Failed', exit 1 (runs/repair-period6-1bit.out).

## #155 (platform deltas)

- **New specific contributor identified (IIDT-1)** — `iid-track`
  Excursion value is FMA-contracted on Apple clang/arm64 (bit-identical to math.fma emulation); non-FMA builds will print different trailing digits.

## #195

- **Reproduces on a VALID fixture; memory-safe and fail-closed under -DNDEBUG** — `memory-safety-fuzz`
  Release ea_restart -n -v fixtures/valid/uniform-1bit.bin 8 5 -> 'Warning: Symbols appear to be narrower than described.' then rc 134 'Assertion failed: (k_effective <= k), function simulateBound, file restart_main.cpp, line 134.' Control H_I = 1 -> rc 0. The same run in the -DNDEBUG+ASan build -> rc 255 in 25 s '*** Restart Sanity Check Failed ***' with no sanitizer output, so the assert is guarding a condition the sanity check would also catch. Also reproduced with 3-symbol width-2 data at H_I 2.0 / 1.9 / 1.6 in the CLI fuzz.

## #252

- **Ordering symptom reconfirmed on master (not my dimension); repair branch fails closed** — `estimators-ttuple-lrs`
  master ea_iid printed 'Assessed min entropy: 0.99628863984762794' and 'Chi square tests: Failed' before the #153 abort on alternating-1bit; repair prints 'IID test suite failed: no IID min-entropy estimate was awarded' with hAssessed absent.

## #252 (ea_iid reports hAssessed despite failed IID tests)

- **Previously repaired but only on the unmerged branch** — `build-portability-harness-docs`
  regression-iid-failclosed.sh on the repair branch asserts errorLevel 2, IID false, no hAssessed on the failing case and a finite hAssessed on the truerand_1bit/truerand_8bit positive controls. I did not re-derive the #252 behaviour (estimator-reporting lane), but I did find that this regression's #153 half is platform-coupled (finding build-portability-harness-docs-4).

## #252 (ea_iid reports hAssessed/exit 0 despite failed IID tests)

- **Confirmed still OPEN on master; RESOLVED on repair 2d4b135** — `iid-track`
  master ones3161 (1M, chi-square Failed m=1): exit 0, JSON IID:true, errorLevel:0, hAssessed 0.00435833449306757 present, passedChiSquareTests:false (runs/master-ones3161.json). Repair: alternating/period6/markov-stay99/markov-stay60 -> exit 1, IID:false, errorLevel:2, assessmentComplete:true, no hAssessed.

## -DNDEBUG behaviour (prior audit record)

- **Previously repaired and still resolved** — `build-portability-harness-docs`
  The shipped build has NDEBUG undefined (probe: 'NDEBUG NOT defined (asserts live)'), and no assert in the 100-site inventory contains a side effect that -DNDEBUG would delete. The prior audit's record that a -O2 -DNDEBUG build matches the release build's final figures on valid non-IID and restart controls is consistent with my arithmetic: with the #153 assert compiled out, p_colPower flushes to 0, log1pl(-0) = -0, and len_LRS_test returns false — a conservative IID rejection, not an inflated estimate.

## BUILDING.md "Upstream observations" item 1 (errorMsg never formatted)

- **Previously repaired but incomplete** — `output-automation-contracts`
  The behaviour reproduces as documented ("errorMessage": "Error: '%s' is empty\n" from ea_non_iid, ea_iid and ea_restart in both modes), but the note itself is out of date for the fork: it names two sites at upstream line numbers 184 and 226 where fork master has four (utils.h:233, :303, :441, :468), and it calls the field errorMsg where the emitted JSON key is errorMessage (finding 9).

## C-01

- **Still open on master; repair verified effective** — `restart`
  Fresh ASan run of $S/wt/master-asan/cpp/ea_restart -n -v -o … uniform-1bit.bin 1 0.9 → alloc-dealloc-mismatch, dealloc restart_main.cpp:161, alloc :124, from main:479, exit 134, no JSON, 25.30 s ($A/out/asan2/c01_master.txt). My own ASan build of 2d4b135 → exit 0, JSON written, no report ($A/out/asan2/c01_repair.txt). Reported as restart-4.
- **Still open on master; confirmed on GCC/Linux; repair-branch fix verified effective** — `linux-x86-docker`
  ASan is unusable under this emulation, so I instrumented the replaceable global allocation functions in a separate TU linked against the UNMODIFIED restart_main.cpp at production flags. A complete `ea_restart -n` run on a 1000x1000 uniform matrix (exit 0, 232s, H_r 7.718814) reported `operator new[](10000000) -> 0x4003f68010` then `*** MISMATCH: scalar operator delete(0x4003f68010) on memory from operator new[](10000000)`, total mismatches = 1. The same instrumentation against the repair branch's restart_main.cpp (which reads `delete[] results;`) on a complete run (exit 0, 328s) reported `operator delete[](...) matched operator new[]`, total mismatches = 0. out/T9b-optrace-O2.log, out/T18-repair-c01.log
- **Previously repaired but only on the repair branch; still open on master, confirmed to fire on every ea_restart run** — `memory-safety-fuzz`
  Master ASan ea_restart -n fixtures/valid/uniform-1bit.bin 1 0.9 -> rc 1 in 67 s 'alloc-dealloc-mismatch (operator new [] vs operator delete)'. All four battery rows (restart_n_u1 217 s, restart_i_u1 196 s, restart_n_u8 95 s, restart_i_u8 71 s) rc 1 with the same report. At function level: harness_ndebug simbound 5.0251553006530614e-06 2 0.9 100000 -> rc 1 with the delete frame at simulateBound(double, int, double, unsigned long) restart_main.cpp:161 and the new[] at :124, in both the assert and the -DNDEBUG build. Repair branch: restart_main.cpp:163 is 'delete[] results;' and bin-repair-asan/ea_restart is rc 0 clean in 319 s. With ASAN_OPTIONS=alloc_dealloc_mismatch=0 the master binary runs to completion rc 0 'Validation Test Passed' with no other sanitizer output, so C-01 is the only memory defect on that path.

## C-01 (6f84ad7 + b3db7ab, repair branch)

- **Previously repaired but incomplete — the fix is correct, the regression is not** — `regression-quality-reconciliation`
  The `delete results` -> `delete[] results` hunk is correct and the shipped control does fail against an ASan build of the unrepaired code (alloc-dealloc-mismatch at restart_main.cpp:161, rc=134). But the control passes against the unrepaired release build, passed against the unrepaired ASan build before b3db7ab, has ungated assertions, and is never run by the suite — finding regression-quality-reconciliation-2. raw/c01/c01.log, raw/c01/b3db7ab/pre-b3db7ab.log, raw/c01/vacuity/stub.out

## F01

- **Withdrawal holds; master equals upstream** — `intake-noniid-aggregation`
  grep -c of the `(data.alph_size > 2) || !initial_entropy` gate = 14 in upstream, master and repair; upstream->master diff touches none of them. Sparse 3-symbol fixture takes the bitstring branch (hAssessed 0.7799495163832836 = 8 x 0.09749368954791045) on all builds.

## F01 (withdrawn 2026-10-03)

- **Not reproduced or ruled out; withdrawal stands** — `regression-quality-reconciliation`
  `ea_non_iid -i -vv bin/truerand_1bit.bin 8` gives bitsPerSymbol 8, bitsPerSymbolInferred false, 2 distinct symbols and H_original 0.82967708323411438 — the same figure as the width-1 run, consistent with two-valued multi-bit data being treated as binary per §4.4.2/§5. raw/comp/n_noniid_w8_on1.json

## F01 (withdrawn: two-valued multi-bit data treated as binary)

- **No new evidence; behaviour verified correct** — `iid-track`
  small/s-2bit-twoval-20000 ({1,2}): binary path with conversions on translated 0/1 and raw values for excursion/compression; all 28 keys equal reference.

## F02

- **Previously repaired and still resolved** — `intake-noniid-aggregation`
  bitsPerSymbol/bitsPerSymbolInferred present and correct in all 27 matrix reports and the width tests; declared 8 on 2-bit data: inferred=false, hAssessed 0.72588171195065776 vs inferred 1.6775707280453183 (inference unchanged, as documented).

## F02 (97571de)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-width.sh fails 4 checks against 21b0a31 ('wrong or missing (expected 4, inferred true)'); master suite PASS. Scope note: the fields were never added to ea_restart — see finding regression-quality-reconciliation-7. raw/mut-p-0e1ffcd-regression-width.log

## F02 (bitsPerSymbol in JSON)

- **Not applied to ea_restart on master; present on repair** — `restart`
  git show --stat 97571de touches iid_main.cpp, non_iid_main.cpp, selftest/regression-width.sh and shared/test_run_base.h but NOT restart_main.cpp. Every master ea_restart JSON lacks bitsPerSymbol/bitsPerSymbolInferred; every repair ea_restart JSON written after read_file has them (bps 1 for 1-bit data, bps 8 with bitsPerSymbolInferred false when declared). Recorded as a scope observation rather than re-reported as a finding.

## F02 (symbol width in JSON, commit 97571de)

- **Previously repaired but incomplete** — `output-automation-contracts`
  bitsPerSymbol and bitsPerSymbolInferred are present and correct in every ea_non_iid and ea_iid report, including the inferred-width case (uniform-sparse-8bit gives bitsPerSymbol 8, bitsPerSymbolInferred true). But ea_restart never assigns either field on master: grep over restart_main.cpp finds no bitsPerSymbol assignment, and r-ok.json (a successful 1,000,000-sample restart run) has no bitsPerSymbol key. Fixed on the repair branch, whose rp-riid.json carries bitsPerSymbol 1 and bitsPerSymbolInferred false. See finding 6.

## F02/F03/F04 (intake-level)

- **Not in scope, observed consistent** — `predictors`
  All short datasets required EA_ALLOW_SHORT_DATASET=1 and were marked nonCompliantShortDataset; 1M fixtures ran without the escape. Recorded only because every short-dataset number above depends on that guard behaving as documented.

## F03 / F04 (1,000,000-sample intake guard, commit c2f1dcd)

- **Previously repaired and still resolved** — `output-automation-contracts`
  999,999 samples refused with exit 255, errorLevel -1 and errorMessage "Error: dataset contains 999999 samples; SP 800-90B Section 3.1.1 requires at least 1000000.", with and without -o, on ea_non_iid and ea_iid. EA_ALLOW_SHORT_DATASET=1 permits the run with nonCompliantShortDataset true; the values 0, true, yes and empty all still refuse, confirming the strcmp(allow,"1") contract.

## F03/F04

- **Previously repaired and still resolved** — `intake-noniid-aggregation`
  999,999-byte file: rc 255, JSON errorLevel -1 with the §3.1.1 message; 1,000,000 accepted; -l subsets of 200000/500000/999999 refused; escape sets nonCompliantShortDataset. MultiMCW 4096 skip only reachable via the escape (tiny positive control).
- **repair scope does not include ea_conditioning -i (never claimed)** — `conditioning-transpose`
  dataset_meets_minimum callers: iid_main.cpp:263, non_iid_main.cpp:264 only; 125,000-byte file assessed with errorLevel 0 (out/pi_125k.json) while ea_non_iid refuses it (out/ref_noniid_rand8_125k.log)

## F03/F04 (1M intake guard)

- **Previously repaired and still resolved** — `restart`
  999,999 / 1,000,001 / 1,500,000 / 2,000,000-sample files are all refused with '*** Error: data (len = N) does not contain 1000000 samples ***', errorLevel -1, exit 255, in both -n and -i; EA_ALLOW_SHORT_DATASET=1 does not loosen ea_restart.

## F03/F04 (c2f1dcd)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-minsize.sh fails 11 checks against 134d377 ('ea_non_iid: short file refused: exit 0 — NOT refused', 'escape marked in JSON: flag absent'). Composition: a short -l block is refused with errorLevel -1 and the escape requires the exact string '1'. raw/mut-p-c2f1dcd-regression-minsize.log, raw/comp/comp.log

## F03/F04 1M intake guard (c2f1dcd) and the EA_ALLOW_SHORT_DATASET escape

- **Previously repaired and still resolved** — `build-portability-harness-docs`
  shared/utils.h:199 dataset_meets_minimum returns true at 'dp->len >= MIN_SIZE' before getenv is consulted, so the variable cannot affect a compliant-size run. Proven on two 1,000,000-byte fixtures (truerand_1bit.bin sha256 f9ea8832..., truerand_4bit.bin sha256 489bc841...): -vv stdout byte-identical with and without the variable (diff exit 0, cmp identical, 111 lines, zero notice lines in the 'with' run), and the -q -o JSON equal apart from dateTimeStamp/commandline with nonCompliantShortDataset absent in both. Short inputs still refused with status 255 on all three tools. LOG.md [R20].

## F05

- **Previously repaired and still resolved** — `intake-noniid-aggregation`
  No 1M fixture declines any estimator (no NotRun keys in 27 reports). 700-byte escaped control: Compression bitstringEstimateNotRun, T-Tuple and MultiMCW literalEstimateNotRun appear; Overall min taken over the rest (5.0690663275190335 = hOriginal).

## F05 (dfe325a)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-notrun.sh fails 2 checks against 6b60f9d ("compliant input, LRS cannot run, is recorded: flags ''"). But its only 1,000,000-sample case is in a silent-skip branch — finding regression-quality-reconciliation-4, confirmed by execution. raw/mut-p-69b6094-regression-notrun.log, raw/skipopen/skipopen-notrun.log

## F05 (not-run reporting, commit dfe325a)

- **Previously repaired and still resolved** — `output-automation-contracts`
  literalEstimateNotRun appeared on Compression, T-Tuple and MultiMCW for in/decl20.bin and on Compression and MultiMCW for in/decl200.bin, with exit 0 and errorLevel 0 as designed. A declined test case contains only testCaseDesc plus the flag. No 1,000,000-sample fixture produced a decline, so the flag's reachability at supported sizes is undemonstrated.

## F09

- **Previously repaired and still resolved** — `predictors`
  Master r=19 / H=0.30220817363257124 vs upstream r=808737 / H=9.6698296585688969e-06 on data/f10_exploit_8bit_1M.bin (and 15 vs 737856 on the second fixture); C identical in both builds, so only the run accounting differs. out/cmp_f10_1M.log, out/cmp_f10over_1M.log.

## F09 (69b6094)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  Generic path: regression-multimmc.sh reports 'r = 6603, expected 24' against 6b60f9d and r = 24 on master; refdata figure 7.9268088197517388 matches refdata/truerand_8bit.res:93 on both. Diff re-read: winner_correct flag, run reset at end of round, both MultiMMC paths. Binary path does not discriminate — finding regression-quality-reconciliation-6. raw/mut-p-69b6094-regression-multimmc.log

## F10

- **Confirmed (was UNCONFIRMED)** — `predictors`
  See predictors-1: two 1,000,000-sample 8-bit fixtures at the shipped constants where the tool's MultiMMC C/r differ from a spec-literal reference (809998/19 vs 765068/18; 741174/15 vs 741364/15), a chained/unchained simulator pair that reproduces each side exactly, and a proof that binary data cannot exercise the mechanism.

## F11 (c0ee84a)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-estimator-guards.sh against ed88de9: '#263 compression declines at v=1 (v1_nan): ran anyway' and 'no NaN/inf sigma-hat: NaN or inf still produced'; 13 checks fail. Decline is spec-derived (§6.3.4 step 5, 1/(v-1)). raw/mut-p-c0ee84a-regression-estimator-guards.log

## F11, F12, F14, F15, F16, F18, F19, N-01, N-04, R-2, R-3

- **Previously repaired and still resolved** — `memory-safety-fuzz`
  No counter-example in 12,688 file-fuzz processes, 262 CLI runs, 230 harness cases x 2 builds, 57 conditioning grid runs or 49 1M battery runs. Specifically: F16's 'L < D_MMC+1' guard at multi_mmc_test.h:36 exactly covers the S[d+1] read at :58 and MultiMMC L 15/16/17/18 is clean in both builds; F15's 'L < B_len+3' guard at lz78y_test.h:28 and the 'L < 3' guard at lag_test.h:46 hold for L 16-20 and L 2-130; F14's int64_t dict[] at compression_test.h:104 carries a static_assert on the element width; F19's subset-overflow check at utils.h:267-278 refuses every overflowing -l in the CLI fuzz and -l 1,1500000 gives rc 255 with subsetActualSamples 500000; F18 refuses non-regular files from the path check at TestRunUtils.h:124-138; N-04's errno reset at restart_main.cpp:332 is the only such reset in the tree and is correct. F12/R-2's '-1' guards hold in ea_non_iid and ea_restart (the ea_conditioning gap is finding memory-safety-fuzz-7).

## F12 (c217f20)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-estimator-guards.sh against c0ee84a: '#264 collision declines at v=1: ran anyway', 'no unmeasured 1.0 from NaN: still produced'; 9 checks fail. The commit also adds the `ret_min_entropy >= 0` guards at both call sites, which is the part that keeps -1 out of the minimum. raw/mut-p-c217f20-regression-estimator-guards.log

## F13

- **Not reproduced or ruled out at the aggregation level** — `intake-noniid-aggregation`
  std::min(NaN,0.3)=NaN and min(8.0,NaN*8)=8 confirm the hazard mechanism; only most_common and markov_test are folded unguarded and neither can return NaN/negative for len>1 and alph_size>=2 (source trace in REPORT §2); every other call is guarded `>= 0`, which rejects NaN into the not-run flag.
- **Not reproduced or ruled out within this dimension** — `memory-safety-fuzz`
  No NaN reached std::min in any of the runs recorded here, and the integer/UB sanitizers reported no float-cast-overflow on any supported path (the only such report was the CLI-unreachable harness case compressionperm L=1 maxsym=0 at permutation_tests.h:297).
- **Not applicable to this dimension's path** — `predictors`
  predictionEstimate uses min(1.0, finite) and fmax (NaN-safe); relEpsilonEqual returns false on NaN by an explicit isnan check at utils.h:93. No NaN reached a std::min call in any run or sweep.

## F14 (6b60f9d)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  Proxy only (the end-to-end case needs >25.8 Gbit). 'F14 narrowing the dictionary fails the build: it BUILT — the guard is not protecting' against all three pre-F14 parents; and I supplied the missing clean-build control: clean copy rc=0, narrowed copy rc=2 with the exact static_assert at compression_test.h:108. raw/f14/f14.log

## F15

- **Previously repaired and still resolved** — `estimators-ttuple-lrs`
  lrs_test.h diff upstream->master is exactly the two v==0 decline hunks; unreachable at L>=1e6 (L>k forces a repeated symbol, v>=1); -vv output byte-identical to upstream on all 19 fixtures; regression-estimator-guards.sh #261 section covers 2-byte/256-byte inputs.
- **Previously repaired and still resolved** — `predictors`
  lag_test.h:46 declines at L<3 and lz78y_test.h:28 at L<B_len+3 (the former asserts are absent from master-vs-upstream-production.diff); no SIGABRT in any of ~60 tool runs, including 1-sample-class edge probes through the harness.

## F15 (21b0a31)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-estimator-guards.sh #261 block: 5 of 6 cases 'ABORTED (exit 134)' against c2f1dcd/ed88de9/c0ee84a, plus 'repeat-free data declines and reports: missing decline or figure'. raw/mut-p-ed88de9-regression-estimator-guards.log

## F15 (asserts -> decline in LRS/lag/LZ78Y)

- **Partially applicable: the two LRS asserts that abort here were not among those converted** — `linux-x86-docker`
  shared/lrs_test.h still carries `assert(p_col >= 1.0L/k)` at :652 and `assert(p_colPower >= LDBL_MIN)` at :683, both of which abort ea_iid on valid 1,000,000-sample data on this platform (findings 1 and rechecked #153), while the comment at lrs_test.h:150 documents the t-tuple/LRS assert that F15 did convert. No new evidence against the F15 repair itself

## F16

- **Previously repaired and still resolved** — `predictors`
  multi_mmc_test.h:36 declines when L < D_MMC+1 before the init loop that reads S[d+1]; the generic path's own `d < N` guard keeps its init in bounds. Both verified by source inspection against the diff hunks.

## F16 (ed88de9)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-estimator-guards.sh #257 block against c2f1dcd: 'heap-buffer-overflow STILL PRESENT' at L=4,5,8,12,16 and 'declines below D_MMC+1: no decline reported'; 19 checks fail. The ASan binary is built from cpp/non_iid_main.cpp, i.e. production source. raw/mut-p-ed88de9-regression-estimator-guards.log

## F18

- **Previously repaired and still resolved** — `intake-noniid-aggregation`
  master refuses FIFO, directory, /dev/null in <1 s (rc 255, 'not a regular file'); upstream hangs on the FIFO (rc 124 at 10 s) and reads /dev/null as empty.
- **partially applies to ea_conditioning (S_ISREG check lives in sha256_file whose status is ignored); ea_transpose never calls it; no hangs observed** — `conditioning-transpose`
  -i directory, /dev/zero, /dev/null -> rc 255 without hang (out/probe_i.log); transpose same (out/probe_transpose.log)

## F18 (non-regular file refusal, commit cdb5cd6)

- **Previously repaired and still resolved** — `output-automation-contracts`
  A FIFO and a directory are both refused with exit 255 and "is not a regular file." on stderr, with no hang; the 20-second timeout was not reached.

## F18 / N-06 (cdb5cd6)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-nonregular.sh fails 8 checks against 21b0a31 — '/dev/zero: TIMED OUT — still hangs', FIFO likewise, and 'absent file no hash invented: errorLevel set, sha256 absent' failing. The ringOsc hash literal in that script is the file's real SHA-256 (verified). raw/mut-p-0e1ffcd-regression-nonregular.log

## F19

- **Previously repaired and still resolved** — `intake-noniid-aggregation`
  -l -1,1000000 -> 'subset offset overflows'; -l 5,1000000 -> 'at or past the end'; -l 1,0 refused; -l 1,1500000 -> requested 1500000 / actual 500000. Whole-file sha256 retained under -l by documented policy (master -l 1 and -l 0 both report 24dca96b... while assessing bytes hashing 927adc2d... / f1e45880...).
- **holds in ea_transpose on master and repair** — `conditioning-transpose`
  -l -1, -l 2^64, -l 4611686018427387904 -> 'subset offset overflows' rc 255 (out/probe_transpose.log)

## F19 (-l subset overflow and provenance, commit 0e1ffcd)

- **Previously repaired but incomplete** — `output-automation-contracts`
  subsetIndex, subsetRequestedSamples and subsetActualSamples exist, and `-l index,0` is refused with a specific message. But the refusal writes its JSON report only when -o was parsed first: `-l 0,0 -o j.json` exits 255 with no report at all, while `-o j.json -l 0,0` writes errorLevel -1 correctly. The fork's new -l index,0 path therefore inherits the upstream `if (jsonOutput)` placement. See finding 4.

## F19 (-l subset overflow/provenance)

- **Previously repaired and still resolved** — `restart`
  ea_transpose '-l 2' on a 2,000,000-sample file → 'Error: subset offset 2000000 is at or past the end of the 2000000-byte file.' exit 255 (upstream instead says the file 'is empty'); '-l -1' → 'Error: subset offset overflows: index 18446744073709551615 x 1000000 samples.' exit 255 (upstream: 'fseek failed'); '-l 1' on a 1,500,000-sample file → 'Data must be 1000000 samples.' exit 255.

## F19 (0e1ffcd)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-subset.sh fails 5 checks against 21b0a31 ('offset multiplication overflow: exit 0', 'zero-sample subset request: exit 0', 'subset provenance in JSON: missing or wrong', 'short final block recorded: not recorded'). Its sha256-scope assertion cannot discriminate — finding regression-quality-reconciliation-5. raw/mut-p-0e1ffcd-regression-subset.log

## F20

- **NOT-A-BUG confirmed as documented behaviour** — `intake-noniid-aggregation`
  -c -t uniform-8bit: 'Number of Binary Symbols: 1000000', hAssessed 6.860666277243958 vs -c -a 7.411307998619576.

## F20 (-t with -c) — NOT-A-BUG list

- **Not reproduced or ruled out; stays not-a-bug** — `regression-quality-reconciliation`
  `-c -t` on uniform-8bit: 1,000,000 binary symbols, H_bitstring 0.85758328465549472, Assessed 6.8606662772439577; `-c -a`: 8,000,000 binary symbols, 0.92641349982744703, Assessed 7.4113079986195762. Both rc=0 and internally consistent (Assessed = H_bitstring x word_size). No new evidence. raw/comp/f_c_t_8bit.out, raw/comp/g_c_a_8bit.out

## F21

- **NOT-A-BUG; documentation gap noted** — `intake-noniid-aggregation`
  utils.h:419 MSB-first within declared width; no documentation found in README/BUILDING/NOTICE/usage (finding 6).

## F23

- **Sub-claims (a) and (b) now Confirmed by execution (finding 4); (c) is a display choice** — `intake-noniid-aggregation`
  Bitstring MCV p-hat/p_u overwritten by literal values in JSON (2/4/8-bit, sparse); -c hAssessed 7.411307998619576 = 8 x hBitstring while text prints h' 0.926413; identical on upstream and repair.

## F23 (reporting composite: literal MCV intermediates only; -c hAssessed = n x h'; text rounding)

- **Confirmed - promoted from UNCONFIRMED** — `output-automation-contracts`
  All three sub-claims reproduce on 1,000,000-sample fixtures. -c hAssessed = word_size x h': console `h': 0.902880` versus JSON hAssessed 3.611520397580104 on uniform-4bit (finding 1). Literal MCV intermediates only: the -i report's Most Common Value test case carries the literal triple (mode 63128) while the bitstring pass's triple (mode 2000402, visible in the -c report) is overwritten (finding 11). Text rounding: default verbosity prints `H_original: 0.000002` where the value is 1.5940282592698827e-06 and `-0.000000` where it is -0.0.

## F24

- **Not reproduced or ruled out (NOT-A-BUG verdict stands), with new reachability evidence** — `predictors`
  predictors-3: the p>r/(r+1) region is entered three times in a compliant 1M run (instrumented build: 1-p*x = 4.06e-17, res = -22.400981671664788); the shipped arithmetic yields no NaN, an isolated harness call does, and tiny-positive / zero / NaN all give the same correct decision. min entropy reported 2.6692268306908263e-07.

## F25

- **Not reproduced or ruled out within this dimension** — `memory-safety-fuzz`
  A 101,304-call sweep of prediction_estimate_function produced 10,199 non-finite results, every one with r >= 2^31 or r = 2^62 (absurd run lengths); none with r <= N <= 2^31. The assert(p < 1.0L) at utils.h:922 is reachable from calc_p_local only if p_global' equals 1-2^-53, which needs about 1e15 predictions. No termination failure or memory problem observed; the numerical-termination question belongs to the estimator dimension.
- **Not reproduced or ruled out** — `predictors`
  predictors-4: ITERMAX=1076 cannot bind before bracket collapse; no ITERMAX exit in ~1500 harness calls (N up to 2^62) or in instrumented production runs; every early exit returns a value at or above the root, so a failed search is conservative.

## F27

- **Spec erratum, not code** — `predictors`
  The independent reference reproduces 22/24 Appendix G.2 Table 3 rows within 6e-5; the two deviating rows are offset by one label (r=60/65 computing the table's r=65/70 entries), i.e. the table's labelling, not the implementation.

## F30

- **NOT-A-BUG confirmed and quantified** — `estimators-ttuple-lrs`
  biased-p01-1bit: LRS 0.028728360513137544 vs true min-entropy 0.0145 (1.98x) and t-tuple 0.013438455878728644; markov-stay99: LRS 0.032316 vs t-tuple 0.014558; final assessment takes the minimum so the LRS figure is never reported as H_original here (runs/master-vv).

## HARNESS-AUD-01

- **Previously repaired but only on the unmerged branch — still fully open on master** — `build-portability-harness-docs`
  Master: in a private copy with a stub ea_non_iid replaying the committed references, all 11 fixtures present -> 'selftest: PASS (11 files)' exit 0; after deleting bin/normal.bin AND refdata/normal.res -> 'selftest: PASS (10 files)' exit 0. Coverage silently drops with no signal. Repair branch: my own nine mutations all fail closed (delete pair, rename pair, tamper a .res digit -> 'SHA-256 mismatch', add an uninventoried .bin, delete pair plus its manifest lines -> 'expected 11 inputs and 11 references, found 10 and 10', and ./selftest -> 'FAIL (fixture inventory incomplete or untrusted)'), with the positive control printing manifest SHA-256 a472090aa8ddf2143385a00a69ce425bf61c43965ac0b83516dd83cbf1bde132. LOG.md [R8], [R10].

## HARNESS-AUD-01 (65de84c, repair branch)

- **Previously repaired and still resolved (repair branch); still open on master** — `regression-quality-reconciliation`
  With bin/ reduced to one file, master's selftest reports 'selftest: PASS (1 files)' rc=0; the repair's reports "fixture-inventory: missing mandatory input 'biased-random-bits.bin'" and 'selftest: FAIL (fixture inventory incomplete or untrusted)' rc=1. regression-selftest-inventory.sh rejects all 7 of its own mutations. raw/harness/master-selftest.out, raw/harness/repair-selftest.out, raw/harness/inv.out

## HARNESS-AUD-01, IND-02, N-08, N-10, NOVEL-03

- **Repair-branch-only repairs, confirmed present there and absent on master, but not exercised in this dimension** — `memory-safety-fuzz`
  Read from diffs/repair-vs-master-production.diff: N-08's parse_unsigned_decimal appears at restart_main.cpp:222 on the repair branch (and does NOT close finding memory-safety-fuzz-11, verified by execution); NOVEL-03's dataLayout parameter is the only change to permutation_tests.h, which is why MS-3 and MS-8 stand there.

## IID #153 / #252 (a3dde6f + 007d0e7, repair branch)

- **Previously repaired and still resolved (repair branch)** — `regression-quality-reconciliation`
  regression-iid-failclosed.sh fails 11 checks against c01fb43, including 'width 1 failed IID suite returns status 1: got 134' (the #153 underflow abort) at every width 1-8 and 'IID restart failure returns no entropy award: FAIL (status 134)'. The script carries an independent §5.2.5 log-domain oracle over 1,000,000-sample fixtures plus two positive controls. 007d0e7's half is caught by regression-271 against a3dde6f ("LRS test: got '', expected 'Failed'"), i.e. the suite caught a regression introduced by a repair. raw/mut-r-c01fb43-regression-iid-failclosed.log, raw/mut-r-a3dde6f-regression-271.log

## IND-02

- **Previously repaired but only on the unmerged branch — still open on master** — `build-portability-harness-docs`
  Repair branch, my own mutations: adding regression-evil.sh -> 'run-all-checks: regression inventory error: unexpected script regression-evil.sh' exit 2; deleting regression-minsize.sh -> 'required script regression-minsize.sh is missing' exit 2. The predecessor's broader set adds rename -> exit 2, non-executable -> exit 2, and inventory-count mismatch -> exit 2. Master simply reports a different discovered count and exits 0 in both cases. Limits recorded: script content is not checked (an inventoried script replaced by 'exit 0' passes), and an editor who changes the inventory plus EXPECTED_REGRESSION_SCRIPTS together passes. LOG.md [R10].

## IND-02 (ea87f1e, repair branch)

- **Previously repaired and still resolved, with a scope gap** — `regression-quality-reconciliation`
  harness-inventory-mutation-test.sh returns rc=1 with master's run-all-checks ('deleted script did not fail as required (exit 0)') and rc=0 with the repair's, passing the complete/deletion/injection/rename/duplicate controls. The inventory covers only regression-*.sh — finding regression-quality-reconciliation-3. raw/harness/ind02-master.out, raw/harness/ind02-repair.out

## Makefile all scope (repair)

- **verified: master plans five programs, repair exactly three, guard present** — `conditioning-transpose`
  make -Bn -C cpp all dry runs (LOG close-out); repair cpp/selftest/regression-docs.sh lines 131-144

## N-01 (binary chi-square m=1)

- **Previously repaired and still resolved on master and repair** — `iid-track`
  chi/ones3161-1bit.bin (min_p^2*500000=4.99596): master prints 'm = 1, test fails per SP 800-90B 5.2.3', 'Chi square tests: Failed'; upstream 87c104d prints T=0, df=0, P-value=1, 'Passed'. chi/ones3163-1bit.bin: m=2, T=1.8136895574363689, df=2, p=0.4038 identical to reference. With L=1e6 and p=0.5, m=11 (df=2046); m=1 needs <3163 ones or zeros.

## N-01 (c8799f4)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-chisquare.sh fails 2 checks against c748c0c ("m = 1 fails the chi-square battery: got 'Passed', expected 'Failed'", 'm = 1 reported with its reason: missing'); m>=2 and both NIST controls still pass. Expected value is SP 800-90B §5.2.3 verbatim. Fixtures are 100,000 samples under the escape — finding regression-quality-reconciliation-8. raw/mut-p-c8799f4-regression-chisquare.log

## N-02 (-c IID tests on bitstring)

- **Previously repaired and still resolved on master and repair** — `iid-track`
  -c -t uniform-8bit: 'Number of Binary samples: 1000000', Binary=true, m=11/df=2046, Bitstring LRS W=37, all 28 keys equal reference on the truncated MSB-first bitstring (runs/master-c-t-uniform-8bit.cmp.txt, runs/repair-c-t-uniform-8bit.cmp.txt, 0 mismatches).

## N-02 (134d377)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-271.sh fails 2 checks against da0265c (chi-square and LRS 'got Passed, expected Failed' under -c) while the -i contrast still passes. Composition: under -c -l the bitstring length follows the subset ('Number of Binary samples: 300000'). Fixture is 10,000 samples under the escape. raw/mut-p-134d377-regression-271.log, raw/comp/e_iid_c_short_l.out

## N-03

- **still present on master and repair (identical source); re-confirmed on arm64 macOS with new over-read site** — `conditioning-transpose`
  constant-1bit.bin -n -i: rc 134 assert most_common.h:14 (master, master-asan); NDEBUG+ASan heap-buffer-overflow READ markov_test.h:48 from conditioning_main.cpp:392; -c iid NDEBUG rc 0 h'=-0 (out/probe_i.log)
- **Reproduces; mechanism now identified (see finding memory-safety-fuzz-5)** — `memory-safety-fuzz`
  ea_conditioning -n -i on an all-zero file: assert build rc 134 'Assertion failed: (len > 1), function most_common, file most_common.h, line 14.'; -DNDEBUG+ASan rc 1 heap-buffer-overflow READ of size 1 in markov_test, one byte before a 1-byte region allocated by read_file_subset. Root cause traced to conditioning_main.cpp:364 word_size = 0 -> utils.h:403 blen = 0 -> utils.h:406 malloc(0), with markov_test.h:48 'data[len-1]' as the out-of-bounds instruction. ea_non_iid and ea_iid refuse the same data (rc 255, 'alphabet consists of 1 symbol').

## N-04

- **Previously repaired and still resolved** — `restart`
  nan/NAN/inf/-inf/1e400/''/'1.5abc'/'3 ' all give errorLevel -1 "H_I must be a finite decimal number: '…'."; -1 gives 'H_I must be nonnegative: -1.000000.'; 9 on width 8 gives "H_I (9.000000) must be at most 'bits_per_symbol' (8)." Upstream positive control: nan asserts at restart_main.cpp:152 (exit 134) and '' is silently accepted as 0.0 and run to 'Validation Test Passed' with errorLevel 0. Residual gap reported separately as restart-13 (strtod still accepts hex floats).

## N-04 (db7a2ba)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-restart.sh against c748c0c: nan and NAN 'CRASHED (signal, exit 134)', and abc / 1.5x / empty / 3.2e all 'exit 0, expected a refusal'; the three valid-H_I controls still run. On master all eight bad values are refused with exit 255. raw/mut-p-c8799f4-regression-restart.log, raw/skipopen/skipopen.log

## N-04 (restart H_I strtod, commit db7a2ba)

- **Previously repaired and still resolved** — `output-automation-contracts`
  `ea_restart -n ... 1 abc` and `... 1 nan` are both refused with exit 255 and the specific message "H_I must be a finite decimal number: 'abc'." / "'nan'."; -0.5 is refused as nonnegative and 2.0 as exceeding bits_per_symbol. No crash, and the JSON carries each message.

## N-05

- **still present** — `conditioning-transpose`
  out/pi_n05_both.json (sha256 965b4aa1... with CLI h_p 0.99) and out/pi_n05_vetted.json (vetted run records file hash)

## N-06

- **Previously repaired and still resolved** — `intake-noniid-aggregation`
  Hash failure on master (dir, /dev/null, FIFO, chmod 000, nonexistent) yields rc 255 'Error: could not hash the input file.' with sha256 absent from the JSON; upstream prints an empty hash and continues to a read failure.
- **still present in ea_conditioning (documented as unrepaired there); new evidence: garbage sha256 is the h' argv text** — `conditioning-transpose`
  out/pi_n06.json 'sha256': '0.9'; out/n06_0.85.json '0.85'; out/n06_0.123456.json '0.123456'; rc 0 errorLevel 0
- **Previously repaired and still resolved** — `restart`
  Every ea_restart run prints the SHA-256 of the input and the JSON carries it; a missing file gives 'Error: could not hash the input file.' with errorLevel -1 and no sha256 field on master (repair: 'could not stat the input file.'); directories and /dev/null are refused as non-regular files.
- **Previously repaired but incomplete: three programs fixed, ea_conditioning untouched** — `memory-safety-fuzz`
  non_iid_main.cpp:192-207 sets hash[0] = '\0' and checks sha256_file's return (exit -1 with errorLevel -1 on failure). conditioning_main.cpp:519-522 does neither: release rc 0 with JSON '"sha256" : "300"', pattern-init build rc 1 with a stack-buffer-overflow READ of size 70 in strlen. TestRunUtils.h:104-207 confirmed to leave outputBuffer untouched on all six failure branches.

## N-06 (fd83a43)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-restart.sh against c748c0c: 'N-06 -i no hash invented on failure: errorLevel 0 or a sha256 was reported'; master and the repair build both report 'errorLevel set, sha256 absent' in both modes and the real hash on a valid run. raw/mut-p-c8799f4-regression-restart.log

## N-06 (sha256 status, commits fd83a43 / cdb5cd6)

- **Previously repaired and still resolved** — `output-automation-contracts`
  On every hash failure (missing, mode 000, directory, FIFO) the run exits 255 and the report omits sha256 entirely rather than publishing stack bytes; on success the field is the correct digest (9f68f2a1f0741e37d29ead66ac7bf84bfc39d9c9022c5ff668f37d4983a27898 for uniform-1bit.bin, matching the manifest).

## N-07

- **Open on master (documented policy); Previously repaired and still resolved on the repair branch** — `intake-noniid-aggregation`
  2M file -l 1,1000000: master/upstream sha256 = whole file 24dca96b...; repair = 927adc2d... (tail -c 1000000) with sha256Scope 'assessed-sample-bytes' and assessedSampleCount 1000000; -l 0 -> f1e45880... (head); whole-file run -> same hash as before on all builds. Repair hashes dp->symbols immediately after fread, before masking.
- **Still open on master; repair verified effective** — `restart`
  Master prints "Opening file: '…' (SHA-256 hash …)"; the repair branch prints "Loaded file: '…' (SHA-256 hash … of assessed bytes)" and adds sha256Scope 'assessed-sample-bytes' and assessedSampleCount 1000000 to the JSON ($A/out/iid/repair_uniform_i.json, $A/out/recheck/shuge_repair.txt).
- **Not re-tested (outside this dimension)** — `memory-safety-fuzz`
  Hash-of-pathname versus assessed bytes is a provenance/reporting question. I verified only the memory-safety properties of sha256_file (single err: label, fclose + delete[] + EVP_MD_CTX_free on every path, sha256_hash_string writes exactly 65 bytes into char[65]).

## N-07 (c01fb43, repair branch)

- **Previously repaired but incomplete — the fix is correct, the regression cannot fail** — `regression-quality-reconciliation`
  Fix verified behaviourally: -l 1,700000 gives sha256 = SHA-256 of tail -c 300000 (51bd286d...2533), sha256Scope assessed-sample-bytes, assessedSampleCount 300000, and it composes with -c and the escape. Regression is inert: the hunk-revert mutant yields AssertionError then 'PASS' rc=0 — finding regression-quality-reconciliation-1. raw/n07-reverify.log, raw/n07scope/n07scope.log

## N-08

- **Open on master with a new vector (finding 2); resolved on the repair branch** — `intake-noniid-aggregation`
  Master accepts 1,1000000abc / 0x / +1 / whitespace / ERANGE-saturated -l values and atoi-truncated bits (4294967304 -> 8, full run); repair refuses all 29 malformed forms tried, accepting only decimal 01 and 08.
- **open on master for conditioning_main.cpp (strtoul base 0: '010' -> 8); repair 2d4b135 fixes ea_transpose -l only** — `conditioning-transpose`
  out/edge_cond_master.log ('n_in = 010' -> n_in = 8); out/probe_transpose.log (master -l 1abc/0x1 accepted; repair refuses)
- **Previously repaired but incomplete** — `restart`
  repair restart_main.cpp:222 and :267 use parse_unsigned_decimal for -s and bits_per_symbol ('-s 5000000abc' and '8abc' refused on repair, accepted on master; ea_transpose '-l 0x1'/'1abc' refused on repair, accepted on master). But H_I is still strtod at repair :306, so '0x1', '0x1p3' and ' 3' are accepted on BOTH trees — reported as restart-13.

## N-08 (031d7ee, repair branch)

- **Previously repaired and still resolved, with one untested hunk** — `regression-quality-reconciliation`
  6 checks fail against a3dde6f ('N-08 ea_non_iid refuses width 8x: exit 255, parser accepted it' and five more across regression-width/subset/restart). The transpose_main.cpp hunk is covered by nothing — finding regression-quality-reconciliation-9. raw/mut-r-a3dde6f-regression-width.log

## N-08 (permissive atoi / strtol parsing)

- **Previously repaired but incomplete** — `output-automation-contracts`
  Still open on master as an output-contract problem: `ea_non_iid -o j.json uniform-1bit.bin 3x` exits 0 and reports bitsPerSymbol 3 with bitsPerSymbolInferred false, i.e. the report asserts an operator-supplied width of 3 from the string "3x". Fixed on the repair branch, where the same command exits 255 with "Invalid bits per symbol: expected an unsigned decimal integer from 1 through 8."

## N-08 (permissive integer parsing)

- **Open on master; one further site observed but not retested** — `linux-x86-docker`
  restart_main.cpp:219-224 parses `-s` with `strtoul(optarg, NULL, 10)` and then rejects 0, ULONG_MAX (its overflow sentinel, which is also a legitimate value) and anything below DEFAULT_SIMULATION_ROUNDS (5,000,000) by calling the [[noreturn]] print_usage(). Recorded as an implementation choice; I did not re-run the N-08 reproductions

## N-09

- **Previously repaired and still resolved** — `intake-noniid-aggregation`
  Success path with -o /nonexistent-dir/x.json, -o <dir>, -o /dev/full: rc 255 with stderr message on master and repair; upstream rc 0 silent. Refusal path + unwritable -o: rc 255 with both messages.
- **still present in ea_conditioning and ea_transpose (documented as unrepaired there)** — `conditioning-transpose`
  -v -o /nonexistent_dir_xyz/out.json 8 8 8 7 -> rc 0, no file; -o /dev/full -> rc 0 (out/edge_cond_master.log + LOG section 4); transpose /dev/full not exercisable on macOS (fopen EPERM)
- **Previously repaired and still resolved** — `restart`
  '-o /nonexistent_dir/x.json' on the sanity-fail path and '-o /dev/full' (absent on macOS, so the open fails) on the success path both print 'Error: could not open the output file …', withhold 'Validation Test Passed' and exit 255, on master and on repair ($A/out/n09/).
- **Previously repaired but incomplete: three programs fixed, ea_conditioning untouched** — `memory-safety-fuzz`
  ea_non_iid / ea_iid / ea_restart with -o /dev/full and -o /nonexistent/dir/out.json -> rc 255 (repair holds; -o /dev/zero correctly gives rc 0 because the device is writable). ea_conditioning with the same values, plus -o <directory> -> rc 0 with no report, at conditioning_main.cpp:550-553, :569-572, :688-691 (raw/condgrid, raw/patsweep/err_cond_badout).

## N-09 (47d6624)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-output.sh fails 3 checks against c748c0c ('-o into a missing directory: exit 0, expected a refusal naming the output file', for all three tools); writable-path controls wrote 2475 and 2092 bytes. Composition with #252 verified: an unwritable report wins (exit 255, error printed) over the IID-failure status. The /dev/full half is skipped on macOS. raw/mut-p-c8799f4-regression-output.log, raw/comp-repair/n09x252.log

## N-09 (report write checked, commit 47d6624)

- **Previously repaired and still resolved** — `output-automation-contracts`
  Positive control against upstream: `$S/wt/upstream/cpp/ea_non_iid -o out/nodir/x.json uniform-1bit.bin 1` exits 0 with no file and no diagnostic; master exits 255 with "Error: could not open the output file ...". Also verified on a genuinely full filesystem (2 MB HFS+ RAM disk, 0 bytes available): exit 255, no file. The residual gap is a signal during the write, which no post-close check can cover (finding 13).

## N-10

- **still present (conditioning half)** — `conditioning-transpose`
  out/edge2_n_ciid_125k.json 'IID': false with -c iid; no vetted field; JSON nw is min(nw,n_in) in all 700 grid records
- **Still open on master; repair effective, and the master defect is worse than recorded** — `restart`
  Master's -i JSON emits "mean": 0.0 and "median": 0.0 for every dataset because tcOverallIid.mean/.median are never assigned; repair emits rawMean 0.499595 / translatedSymbolMedian 0.5 for the same input. Escalated and reported as restart-5 (fabricated values, not merely ambiguous labels).

## N-10 (094189c, repair branch)

- **Previously repaired and still resolved (repair branch); master still emits mean/median** — `regression-quality-reconciliation`
  regression-iid-json.sh fails 3 checks against a3dde6f ('N-10 JSON uses explicit statistic names: ambiguous or missing fields', 'stdout labels the translated median: still says only Median', 'sparse-alphabet domains are distinguishable: labels or values wrong'). Master's IID report still carries mean 0.5001566666666667 / median 0.5, confirming it is open there. raw/mut-r-a3dde6f-regression-iid-json.log, raw/comp/e_iid_c_short_l.json

## N-10 (ambiguous stats labels: median)

- **Still open on master (label only); resolved on repair; shown to have no numeric effect** — `iid-track`
  master prints 'Median = 1' for raw alphabet {0,17,255} (translated index); repair prints 'Translated Symbol Index Median = 1' / JSON translatedSymbolMedian. Executed: §5.1.5/5.1.6 statistics with raw median 17.0 vs translated 1.0 identical (446367 / 35); two-valued {1,2}: raw 2.0 vs rule 0.5 identical (10077 / 15); symbol_map_down_table assigned in increasing symbol order (order-preserving).

## N-10 (reporting-only: ea_iid median of translated indices; conditioning IID hard-coded false; restart -i mean/median always 0.0)

- **Previously repaired but incomplete** — `output-automation-contracts`
  The restart clause still reproduces on master: `ea_restart -i -o r.json uniform-1bit.bin 1 0.5` reports mean 0.0 and median 0.0 where the computed values are 0.500831 and 0.5 (finding 7). Fixed on the repair branch (rawMean 0.500831, translatedSymbolMedian 0.5). The hard-coded IID constant is unfixed on both branches for NonIidTestRun, which ea_non_iid and `ea_restart -n` use, so the repair's verdict treatment applies only to IidTestRun (finding 3). The label work also left `iteration` naming the C[i][0..2] counter index on both branches (finding 15).

## N-11

- **still present** — `conditioning-transpose`
  -v 1073741823 256 256 300 rc 134; -v 8 1073741823 8 7 rc 134; -v 4294967295 8 8 7 rc 134; -v 8 8 1073741823 7 rc 0 (out/edge_cond_master.log); 1073741822 control not run (RAM budget)
- **Reproduces; the abort is at :602 and fires before any large mpfr allocation** — `memory-safety-fuzz`
  ea_conditioning -v with n_in 1073741823, n_in UINT_MAX or n_out UINT_MAX -> 'Assertion failed: (mpfr_get_emax() > maxval), conditioning_main.cpp:602'. nw UINT_MAX is clamped to n_in and is fine. n_in 1e6 completes rc 0 in 107 s; 1e7 and 1e8 hit the 300 s timeout with no crash (resource only). While confirming this I found that the companion assert on the next line can never fail (finding memory-safety-fuzz-12).

## NOVEL-01

- **Previously repaired but incomplete** — `linux-x86-docker`
  The widened compareresults.pl parser does compare `Assessed min entropy`, `H_original` and `H_bitstring` (present in refdata in the `: ` / ` = ` forms), but `H_bitstring Per Symbol` is collected and has no counterpart in any of the 11 reference files (grep -c = 0; refdata byte-identical to upstream's), and the extra-item branch does not set $retstatus, so selftest exits 0 while printing it for 5 files. See finding linux-x86-docker-4

## NOVEL-01 (#272, da0265c)

- **Previously repaired and still resolved** — `build-portability-harness-docs`
  cpp/selftest/selftest:55-60 propagates compareresults.pl's exit status and names every failed file; compareresults.pl collects the final combined figures (H_original, H_bitstring, 'Assessed min entropy') as its comment claims — 65 labelled lines collected from a reference file, including those four. Confirmed by the T3/T4 controls (truncated new output and an injected nan both exit 1). A different fail-open in the same script remains: an empty REFERENCE (finding build-portability-harness-docs-3).

## NOVEL-01 (da0265c)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-272.sh fails 3 checks against 55a7f65 — both source mutants 'NOT CAUGHT — the mutant passed the comparison' and 'selftest exit status: ZERO despite a mismatch in biased-random-bits — the #272 fault'. The script builds baseline + 2 mutants from production source and guards its own patterns. raw/mut-p-da0265c-regression-272.log

## NOVEL-01 (selftest final figures, commit da0265c) / PR #251 verbosity coupling

- **Previously repaired and still resolved** — `output-automation-contracts`
  ea_non_iid's JSON is byte-identical across -q, none, -v, -vv and -vvv for all four fixtures tested (testCases sha256 prefixes 6d34fd1dd588, ab284dbd219f, be06faafd21e, bffc42fb7fdd), so hAssessed no longer depends on verbosity. The console's final figure still changes format with verbosity, and under -c changes meaning (finding 1), which is a separate matter.

## NOVEL-02 (9f64f62)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-iid-json.sh fails all 4 checks against 47d6624 (rc=1, 834 s): hBitstring 'reported 1.0', hOriginal 'reported 8.0', 'hAssessed at -q matches the -vvv figure: json 1.0 vs text 0.99504301513122573', 'still 1.0'; both positive controls pass. Master run PASS rc=0 in 1324 s, and I reproduced its asserted cond.json figure 0.9981992801198275 to 17 digits with an independent MCV oracle. raw/mut-p-9f64f62-regression-iid-json-retry.log, raw/pos/master-regression-iid-json.log

## NOVEL-02 (ea_iid h_assessed placeholder / verbosity coupling)

- **Previously repaired and still resolved on master** — `iid-track`
  uniform-4bit master JSON identical for -q, -vv, -vvv (OMP1/OMP8) excluding commandline/timestamp/C counters: hAssessed 3.9713307321587794 in all.

## NOVEL-02 (ea_iid placeholders, commit 9f64f62)

- **Previously repaired but incomplete** — `output-automation-contracts`
  Holds for ea_iid: a binary -i report omits hBitstring and reports hAssessed 0.993899026278285 equal to hOriginal and to the -vvv "Assessed min entropy" line; a -c report omits hOriginal. But the same class of defect survives in ea_restart -i, whose mean and median are published as the 0.0 class defaults because the emission gate tests against -1 (finding 7).

## NOVEL-03

- **Still open on master; repair verified effective** — `restart`
  Master's permutationTestResults is 6 entries with iteration 0,1,2,0,1,2 and no layout key ($A/out/iid/master_lrsdup_i.json); repair labels them (0,'rows') (1,'rows') (2,'rows') (0,'columns') (1,'columns') (2,'columns') ($A/out/iid/repair_uniform_i.json).

## NOVEL-03 (25fbb54, repair branch)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  Hunk-revert mutation (the `testResultJson["dataLayout"] = dataLayout;` emission removed from iid/permutation_test_result.h:41) makes restart-report-label-test exit 1 with 'result 0 is not labelled rows iteration 0'; the unmutated source gives 'restart-report-label-test: PASS (rows 0,1,2; columns 0,1,2)' rc=0. regression-restart.sh gates on that exit status and also fails if the test will not build. raw/novel03/novel03.log

## NOVEL-03 (dataLayout labels)

- **Repaired on repair branch (verified present)** — `iid-track`
  repair JSON permutationTestResults[*].dataLayout = 'input' (runs/repair-uniform-4bit.json, runs/repair-c-t-uniform-8bit.json).

## NOVEL-03 (restart -i row/column labels)

- **Previously repaired but incomplete** — `output-automation-contracts`
  Still open on master: `ea_restart -i -o r.json uniform-1bit.bin 1 0.5` yields six permutationTestResults with iteration 0,1,2,0,1,2 and nothing identifying rows from columns. The repair branch adds dataLayout rows|columns, which resolves the row/column ambiguity, but keeps the name `iteration` for what is the C[i][0..2] counter index (finding 15).

## R-1

- **OVERTURNED 'NOT-REPRODUCED-HERE on arm64' — reproduces on this arm64 build for k=25 (L=1e6), 17, 100, 250; still unrepaired on master and repair branch** — `estimators-ttuple-lrs`
  runs/r1/*: rc=134 assert lrs_test.h:652 on master, upstream, repair, master-asan ea_iid and master ea_restart -i; controls k=3,16 pass; numerics.json A (53-bit: 117/255 k fail; 64-bit: 155/255 incl. 3,6,7,9,12).
- **Open, and now reproduced on this platform with a materially wider scope** — `linux-x86-docker`
  rc 134 at shared/lrs_test.h:652 for bal3/bal6/bal7/bal12; no JSON with -o; oracle margins -3.70e-17 to -9.26e-18; sweep TOTAL_FAIL=155 of 255 alphabet sizes; ea_restart ruled out (18/18 divisor-k margins >= 0); still aborts on the repair branch. See finding linux-x86-docker-1
- **Previously recorded as not reproducible on arm64; it DOES reproduce, with new evidence (finding memory-safety-fuzz-1)** — `memory-safety-fuzz`
  The tracker's attempts used k <= 16, where the rounding error has the opposite sign (k = 2, 8, 16 have margin exactly 0 because 1/k is exact in binary). A margin scan found 702 negative-margin (k,L) pairs with k >= 17, and four of them abort the release binary: bal25_1e6.bin, bal17_1000008.bin, bal21_1000020.bin, bal23_1000017.bin all give rc 134 at lrs_test.h:652, with bal16/bal20/bal24 as passing controls. Also rc 134 on the repair branch and on upstream 87c104d (its line 626); rc 0 under -DNDEBUG.

## R-1 (LRS p_col assert on 80-bit long double)

- **Previously repaired but incomplete or regressed — still not reproducible on arm64, but its sibling assert two lines below is** — `build-portability-harness-docs`
  assert(p_col >= 1.0L/k) at lrs_test.h:652 did not fire on any of the six 1M fixtures tried. The guards that follow it are reachable: lrs_test.h:683 aborts (finding build-portability-harness-docs-1), and the p_col > 1 - LDBL_EPSILON early return at :658 is platform-dependent in principle but unreachable in practice — with n samples the minority count would have to satisfy 2c/n < 2.2e-16, i.e. c < 1 for any n up to 1e9, so only exactly-constant data takes it and that behaves identically on both widths.

## R-1 / upstream #153

- **Previously recorded as not reproducible on arm64 — NOW REPRODUCED on arm64** — `restart`
  $S/wt/master/cpp/ea_restart -i -v -o … $A/data/circ985_1bit.bin 1 0.05 → 'Assertion failed: (p_colPower >= LDBL_MIN), function len_LRS_test, file lrs_test.h, line 683.', exit 134, no JSON, after the sanity check had passed. Upstream same at :657; repair clean. Reported as restart-2.

## R-2

- **Previously repaired and still resolved** — `restart`
  'if (ret_min_entropy >= 0)' guards both the row and column folds for all eight estimators that can decline (restart_main.cpp:596/603, 636/643, 671/677, 690/696, 713/720, 734/741, 754/761, 775/782). MCV and Markov are unguarded and that is correct (neither has a -1 return; non_iid_main.cpp leaves Markov unguarded too). The decline path is not reachable at 1,000,000 samples; the degenerate circ985 -n run returned ten finite positive estimates per dataset.

## R-2 (d892b90)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-restart.sh against c748c0c: 'R-2 the -1 sentinel is not folded in: H_r is -1 (still folded)' and 'no false validation failure: still fails validation', with the precondition asserted ('the LRS estimate really does decline: yes'). On the repaired build H_r 6.583332 and validation passes. Its block can be silently skipped — finding regression-quality-reconciliation-4. raw/mut-p-c8799f4-regression-restart.log, raw/skipopen/skipopen.log

## R-3

- **Previously repaired and still resolved** — `restart`
  '-n -v -o … block0_8bit.bin 4 2' → 'Incorrect bit width specification: Data (8) does not fit within described bit width: 4.', exit 255, JSON errorLevel -1 with 'Error: Incorrect bit width specification: …' ($A/out/recheck/r3.{txt,json}). Same in -i.

## R-3 (23dca69)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  regression-restart.sh against c748c0c: 'R-3 -i read failure recorded in JSON: errorLevel 0 or no message'; on the repaired build both modes report 'errorLevel set with a message' and a successful run still reports errorLevel 0. raw/mut-p-c8799f4-regression-restart.log

## R-3 (restart read-failure JSON, commit 23dca69)

- **Previously repaired and still resolved** — `output-automation-contracts`
  `ea_restart -i -o j.json empty.bin 1 0.5` writes the IID report object with errorLevel -1 (not 0) and carries read_file's message across from testRunNonIid; the -n case writes the non-IID object. Both exit 255.

## REV-002

- **Previously repaired and still resolved** — `linux-x86-docker`
  `make non_iid iid restart` and `make all` compile clean on GCC 13.3 / Ubuntu 24.04.5 / x86-64 with upstream default flags (MAKE_ALL_EXIT=0, 2m36s); a tiny program confirms ULONG_MAX=18446744073709551615 is visible. The <climits> repair b75e763 holds. out/T2-build-default.log, out/T2c-build-all.log

## REV-003 (8f0469c)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  The pre-8f0469c script, run against the pre-F09 build, printed 'F09 binary path still produces a run length: r = 17' — a value with no assertion, confirming the original defect. The replacement does assert a value. But it does not discriminate the F09 defect — finding regression-quality-reconciliation-6. raw/rev003-old-multimmc-vs-preF09.log

## REV-005 (8f0469c)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  Confirmed by the two values the mutant runs print: this platform produces 0.15932269772157773 while refdata records 0.15932269772157898, a 7.8e-15 relative difference that the old literal rejected and the new refdata+1e-9 comparison accepts. raw/mut-p-ed88de9-regression-estimator-guards.log

## REV-006 (590c83a)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  With a selftest stub that exits 1 printing no summary line, parent 06dff41 reported 'selftest PASS (only the known upstream #155 platform files)' rc=0 (fail-open reproduced) while master reports 'FAIL (exit 1, no "selftest: FAIL" summary line to classify)' rc=1. raw/harness/rev006-master, raw/harness/rev006-parent-06dff41

## Repair branch 2d4b135 overall

- **Builds and passes on GCC/Linux** — `linux-x86-docker`
  `make all` exit 0 with GCC default flags, building ea_iid, ea_non_iid, ea_restart only (the documented narrowed `all` scope); selftest 11/11 PASS with deltas identical to master; C-01 verified fixed; R-1 and the errorMsg comma-operator sites (repair utils.h:395, :569) still present. out/T8-repair.log, out/T18-repair-c01.log

## Upstream #153 (LRS p_colPower underflow assert on valid alternating data)

- **Previously repaired but incomplete** — `output-automation-contracts`
  Reproduces on master through a supported workflow: `ea_iid -i -o i-period6.json $S/fixtures/valid/period6-1bit.bin 1` (1,000,000 samples) exits 134 with `Assertion failed: (p_colPower >= LDBL_MIN), function len_LRS_test, file lrs_test.h, line 683.` and writes NO report despite -o. Output-contract consequences: a fourth undocumented exit status, no machine-readable record of the run, a stale report left at the -o path, and scrambled diagnostic ordering because stdout is block-buffered when redirected while the assert text goes to unbuffered stderr. Fixed on the repair branch: the same command exits 1 with a complete report (errorLevel 2) and no abort.

## Upstream #252 (ea_iid reports hAssessed / exit 0 despite failed IID tests)

- **Previously repaired but incomplete** — `output-automation-contracts`
  Still open on master and now demonstrated by execution: a dataset that fails all three batteries yields exit 0, errorLevel 0, "IID": true and hAssessed 0.794629991529219 (finding 2). Fixed on the repair branch: exit 1, errorLevel 2, "IID": false, hAssessed absent, with the new errorMessage "IID test suite failed; no IID min-entropy estimate was awarded."

## build scope (876ba05, repair branch)

- **Previously repaired and still resolved** — `regression-quality-reconciliation`
  `make -Bn all` plans ea_conditioning ea_iid ea_non_iid ea_restart ea_transpose on master and ea_iid ea_non_iid ea_restart on the repair branch; regression-docs.sh asserts it ('make all builds exactly the supported programs: ea_non_iid ea_iid ea_restart'). raw/harness, $S/logs/repair-run-all-checks.log

## upstream #153

- **Previously repaired but only on the unmerged branch; reproduced on master with new evidence that the trigger window is platform-dependent** — `build-portability-harness-docs`
  Master arm64: ea_iid -q fixtures/valid/alternating-1bit.bin 1 -> exit 134, 'igamc: UNDERFLOW' then 'Assertion failed: (p_colPower >= LDBL_MIN), function len_LRS_test, file lrs_test.h, line 683.'; and ea_iid -q ldbl/lrs2000-1bit.bin 1 (uniform 1-bit with one duplicated 2,000-sample region) -> exit 134 at the same assert with chi-square passing. Measured abort window W in [1023, 16382] on arm64 versus empty on x86-64 GCC. See finding build-portability-harness-docs-1. LOG.md [R11]-[R13].
- **Open, and NOT platform-dependent (reproduces on x86-64 as well as arm64)** — `linux-x86-docker`
  `OMP_NUM_THREADS=2 ./ea_iid /tmp/fx/alternating-1bit.bin 1` on the 1,000,000-sample alternating fixture -> `igamc: UNDERFLOW` then `Assertion 'p_colPower >= LDBL_MIN' failed` at shared/lrs_test.h:683, rc 134, 0s. With p_col = 0.5 and W ~ L, 0.5^W is far below even the 80-bit LDBL_MIN (3.3621e-4932 = 2^-16382), so the 64-bit-mantissa platform does not help. Unlike R-1 this one needs no long-double-width explanation. out/T11-i153.log

## upstream #155

- **Previously repaired but incomplete or regressed — the deltas reproduce exactly as documented; what is incomplete is the harness's handling of them** — `build-portability-harness-docs`
  All eleven references regenerated with generate-refdata semantics: 9 clean, biased-random-bytes 7 significant differences (max 3.65934130219792e-10), ringOsc-nist 1 (1.5468587521994e-10) — exactly BUILDING's table and NOTICE's 'eight predictor values'. But --allow-known-platform-deltas excuses those two files by name at any magnitude (finding build-portability-harness-docs-2), and BUILDING.md:176 misstates the count as three (finding build-portability-harness-docs-8). LOG.md [R19], regen/run.log.
- **Confirmed as a platform delta; the two macOS-failing files pass on Linux and the mechanism is now isolated** — `linux-x86-docker`
  Strict selftest PASSes 11/11 on Linux (max delta 1.00808250635964e-13) where macOS FAILs biased-random-bytes.bin and ringOsc-nist.bin; I reproduced the macOS cause (MultiMCW min entropy delta 1.5468587521994e-10) with compareresults.pl against my own macOS .res. Mechanism traced to long double width in prediction_estimate_function. See finding linux-x86-docker-2

## upstream #195

- **Still open on master, upstream AND the repair branch** — `restart`
  assert(k_effective <= k) at restart_main.cpp:134 (upstream/repair :133) aborts with exit 134 and no JSON on three distinct 1,000,000-sample triggers (stuck_msb_7of8 declared width 8 with H_I 7.5; stuck_lsb_8bit with H_I 7.5; sparse3_2bit with H_I 1.6) and via H_I '0x1p3' on colconst8. Reported as restart-3.

## upstream #252 (analogue in ea_restart)

- **Open on master, fixed on the repair branch** — `restart`
  master -i on iid_lrsdup_1bit.bin: '** Failed length of longest repeated substring test' yet 'Validation Test Passed... min(H_r, H_c, H_I): 0.900000', exit 0, JSON errorLevel 0 and "IID": true. Independently reproduced with a failed permutation test on the PERMS-shortened build. Repair: exit 1, errorLevel 2, no estimate. Reported as restart-1.

