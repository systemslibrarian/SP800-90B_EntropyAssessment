# Priority-2 positive claims — independently observed coverage

Historical target34fb906196f8d47da774c88928eff0d8ec08d618; recorded current328ec20c146e43b4eed86424847a106539c70a5a. Reviewed implementation files are identical between them (initial Git diff and targeted SHA-256 checks); changed pin script tested separately. Native macOS26.6.2 arm64 Apple clang21 unless a row explicitly says GCC13.3 emulated x86-64. Every meaningful mutant is separate, compiles, and reaches the intended behavior. No tolerance, fixture or algorithm coverage was reduced to obtain a pass. Full current/historical claims remain separate from old audit prose.

## F09 mathematics, original dataset and final minimum

- Independent literal §6.3.9 reference and full prediction/run comparisons are documented in REV-003.md. The official May29,2025 errata file was fetched and preserved with URL/hash; its two proposed changes concern §5.2.4's critical value and §6.3.1's worked example, not MultiMMC or m1 chi-square.
- Actual F09 parent6b60f9d3adc37b245bef03175ffe8e7eec8afe5b: literal MultiMMC C7089/N114144/r6603; estimate0.00211176482535928.
- Fixed target: same C/N, r24, estimate0.93188950992564512.
- Complete original fixture outputs083/084 show the **same final0.0008876062538599284**, equal to **literal t-tuple**. Bitstring minimum is0.00014524819243532969 per bit, or0.0011619855394826375 per8-bit sample, so it does not bind. The result is not inferred by looking at MultiMMC alone.
- The meaningful generic missing-Null-reset mutant is caught by the unchanged regression; binary regression sensitivity remains the separate confirmed REV-003 gap. Supported correctness is fixture-scoped, not proof for every input.
- candidate-25.bin remains unavailable. Its claimed hash/counts/final-minimum change are **BLOCKED**, not invented or inferred from a different generated input. No physical-entropy conclusion follows from any diagnostic fixture.

## Numerical pin and full reference corpus

Full unchanged selftests completed, all11 files each:

| Platform | Historical target | Actual F09 parent | Complete verbose parent/fixed outputs |
|---|---|---|---|
| macOS arm64 clang21 | exit1, exactly biased-random-bytes and ringOsc-nist fail | same exit1 and same eight offending predictor fields | Byte-identical for all11 files |
| Linux x86-64 userland GCC13.3 under emulation, disclosed -include climits | exit0,11/11 pass | exit0,11/11 pass | Byte-identical for all11 files |

The actual comparator uses **min(absolute delta, relative delta)** against1e-10, not a purely relative metric as some documentation calls it. No tolerance was changed. Native deltas are observed on both baselines, supporting their pre-F09 provenance; Linux success neither proves nor refutes macOS behavior. Finite corpus agreement is not universal numerical equivalence. Complete outputs are in corpus-results and comparison in p2-corpus-comparison.json.

Both historical/current pin scripts actually invoke ea_non_iid and parse its assessed result. They compute0.12644573619604868 on the validated ringOsc sample and pass the fixed reference tolerance; the original64-byte perturbation computes0.12643698121829336 and is rejected. A compiling/reachable source mutant adding0.01 to the binding collision return makes final0.13644573619604869; the unchanged current pin rejects it (exit1). The expected pin was not changed, no hard-coded estimator output was inserted, and the check is demonstrably nonvacuous on these cases. A pin is not a proof of all unchanged paths.

## Repair verification triples

All tests below are the claimed original **full regression**, transferred byte-for-byte into actual-parent copies if absent there. The test transfer is not a repair. Relevant stdout was reviewed in full via093 and per-probe logs; incidental failures from other not-yet-fixed parent code are not mistaken for the targeted failure.

| ID | Actual pre-fix behavior | Fixed and positive controls | Meaningful mutation caught | Scope/limit |
|---|---|---|---|---|
| F02 | parent0e1ffcd lacks effective/inferred width metadata in both tools | all4 inferred/declared cases pass; inference remains4 | shared JSON width omission fails4 checks | Metadata only; default-width dispute stays open |
| F19 | parent21b0a315 accepts wrapped offset and zero-count subset, lacks provenance | all7 checks pass, requested700000/actual300000, unchanged whole-file digest | overflow-check bypass accepts wrapped request; caught specifically | Original regression is non-IID/LP64; REV-002 build defect separate |
| F05 | parent69b6094 omits actual deBruijn/short-input skipped flags | real1m-sample LRS decline recorded, errorLevel0,4 no-skip controls pass | flag omission caught in2 cases | Reporting only; declined estimators not rewritten |
| F03/F04 | global parent134d377 assesses short files/subsets without error | both tools reject short input; compliant pin and marked escape succeed | intake bypass fails11 intended checks | Guard dispositions, **not** underlying algorithm repairs |
| F11 | parented88de9 v1 inputs produce NaN/inf | v1 declines; v2 finite and public control | old block threshold caught by4 compression assertions | Native ASan; no Linux full-suite claim |
| F12 | parentc0ee84a five-bit collision produces unmeasured1/NaN | declines; full native suite/public control pass | omitted v0/1 guard caught by2 collision assertions | Additional direct v0/combination coverage not exhaustive |
| F15 | parentc217f20 aborts on two/distinct256/binary3/17/18 | all6 current cases complete; repeat-free decline/report | restored32-bit repeat-free assert caught | **Five**, not six, listed parent cases abort: binary19 already passes.64-bit suffix-array and every separate guard not mutation-verified |
| F16 | parentc2f1dcd overreads lengths4,5,8,12,16 | all listed short cases decline and full native public control passes | L<4 mutant compiles, restores intended ASan overreads, caught | Listed lengths; not universal sanitizer assurance |
| N-01 | parentc748c0c m1 reports Passed, no reason | m1 fails; m2 and binary/nonbinary public controls pass | m1-applied-true mutant caught | Chi-square repair, **not** full aggregate IID propagation |
| N-02 | parentda0265c tests packed conditioned symbols and passes chi/LRS | original full10k regression completes175s; -c fails, -i passes | packed-view mutant caught by both conditioned checks | Original80k-bit/noncompliant test fixture; no1m-conditioned performance claim |
| R-2 | parent23dca69 deBruijn LRS genuinely declines, H_r=-1/false validation failure | unchanged full restart suite passes, H_r6.583332, ordinary control passes | unguarded row-LRS fold givesH_r=-1 and is caught | Full native original5m-round simulation retained |
| R-3 | parentdb7a2ba IID read failure JSON lacks error level | both modes show real read error, successful control0 | wrong-report-object mutation caught specifically in-i | Other parent failures not used as evidence |
| NOVEL-01 | parent55a7f65 misses both final-combination mutants and discards first-file failure | full272 suite catches specifically Assessed min entropy; accumulated exit1 | comparator-summary and exit-discard mutants separately caught | Original reference mismatch only in disposable test data; user refdata untouched |

### N-01 independent derivation and #252

Here m is the **non-overlapping block length**, selected as the maximum up to11 with min(p0,p1)^m*floor(L/m)>=5, not alphabet size. The verified PDF explicitly says m1 fails. Independent exact-rational cases were generated, not copied from repaired code:

-40 balanced bits with5 of each2-bit block: m2, T=0, df2, passes.
-39-bit prefix: m1; parent/mutant pass incorrectly, fixed returns applied=false/battery=false.
-40bits of0011 repeated: m2, T20, df2, independence fails; confirms fixed code did not simply force all outcomes to pass/fail.
-Allzero/allone40-bit direct-unit cases: fixed m1 fails before NaN goodness-of-fit; not ordinary CLI acceptance claims.
-1m bits with3162 ones: m1, fixed fails;3163 ones: m2, T0.9594061826805214 from exact rational model, implemented T0.95940618268052147, passes. Full CLI runs complete on parent/fixed/mutant.

The repaired1m m1 CLI still exits0 with errorLevel0 and IID=true, but explicitly records passedChiSquareTests=false and reports an entropy figure. This is the known **#252** aggregate-reporting limitation, not a refutation of N-01's chi-square correction. Do not call the entire IID decision safely propagated. Complete direct and CLI evidence: n01-analysis.json, n01-fixture-reference.json, n01-cli-results, logs/p2-n01-*.

## Failed/limited work preserved

The first native guard-triple invocation accidentally put the earlier Linux-only compiler adapter on PATH; all12 calls failed at compiler infrastructure before testing. Those results are preserved separately, not counted as pre-fix failures or mutation detections. The native capture-only wrapper then allowed the **unchanged native compiler command/assertions** to run, giving the substantive results above. No guard or tolerance was weakened. Original scripts sometimes intentionally redirect child stdout/stderr to /dev/null; top-level trace/outputs and scratch JSON/fixtures are preserved, but discarded internal bytes cannot retrospectively be called captured. Decisive direct probes preserve their full outputs.

F14 remains structural-only; no end-to-end >2^32-block numerical evidence yet. N-04/NOVEL-02 unfinished claims and all nine unresolved statuses remain for Priority3. No “all verified” conclusion is made.