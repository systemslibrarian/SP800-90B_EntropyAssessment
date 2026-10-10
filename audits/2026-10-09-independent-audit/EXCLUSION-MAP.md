# Prior-finding exclusion map

This map prevents rediscovery. The canonical source is
`audits/2026-09-30/FINDINGS-TRACKER.md`; the 2026-10-01 re-audit supplies the
REV dispositions and parent/fix/mutant evidence. “Upstream response” below
means repository contributor feedback, principally @joshuaehill of KeyPair
Consulting. It is not an official NIST statement.

Affected baseline for F/N/R/NOVEL/C findings is upstream 1.1.8 commit
`87c104d` unless a row says otherwise. A fork repair means present by audited
fork `106d31c`. Issue and PR numbers refer to
`usnistgov/SP800-90B_EntropyAssessment`.

## F01–F30

| ID | Existing allegation | Disposition and supporting discussion | Repair/current audit treatment |
|---|---|---|---|
| F01 | Two-valued multi-bit input takes binary path | **NOT-A-BUG / withdrawn.** #253 and PR #256; upstream contributor argued “binary” follows the translated two-symbol alphabet. No NIST account answered. | No production change; withdrawal `106d31c`. Excluded absent new official or supported-domain contrary evidence. |
| F02 | Inferred width can change `n×H_bitstring`; width absent from JSON | Confirmed; #254 accepted reporting value but disputed warning/default policy. | Fork `97571de` records effective/inferred width. Regression passes. Remaining default is accepted policy, not new. |
| F03 | Sub-million input emits successful assessment | Confirmed; #255/#238, contributor agreed minimum should be enforced. | Globally guarded by `c2f1dcd`; regression passes. Short data tested only for safe rejection. |
| F04 | MultiMCW skipped for 64≤L≤4095 | Confirmed mechanism; #258/duplicate #265; contributor preferred global 1M minimum. | `c2f1dcd` makes path unreachable in ordinary use; estimator code unchanged. Excluded outside supported input. |
| F05 | Legitimate estimator no-result silently omitted | Confirmed at valid size; #255 distinguished no-result from fatal error. | `dfe325a` records not-run flags without falsely failing assessment. Regression passes. |
| F06 | Compression step 8 can return 1 for constrained sources | **NOT-A-BUG / standard limitation.** §6.3.4-literal; #69/#70/#223 context. | No code repair. Do not treat black-box estimator limitation as divergence. |
| F07 | Full normal quantile rather than printed 2.576 | **NOT-A-BUG / intended.** #22, PR #69. | No repair; independent oracle reports both. Difference tiny and known. |
| F08 | Predictor recurrence converges rather than stopping at x10 | **NOT-A-BUG / intended upstream deviation.** #133, merged PR #134. | No repair. Historical effect <1e-10. |
| F09 | MultiMMC Null winner failed to reset correct run | Confirmed but conservative direction; not filed upstream. | `69b6094`; historical literal oracle and mutant evidence, current regression pass. |
| F10 | MultiMMC chained lookup skips deeper orders | **UNCONFIRMED consequence.** Instrumented/scaled model changed behavior; no C/r change at shipped 100,000-entry constant. | No repair. Reopen only with shipped-constant, valid-input effect. |
| F11 | Compression v=1 divides by zero | Confirmed tiny-input estimator defect; #263, PR #270; contributor preferred minimum plus guard. | `c0ee84a`, also unreachable via global minimum. Regression passes; not new. |
| F12 | Collision v≤1 produces NaN/full entropy | Confirmed estimator-level tiny-input issue; #264. | `c217f20`, also globally unreachable. Regression passes; not new. |
| F13 | NaN folded by `std::min` drops prior minimum | **UNCONFIRMED reachability.** No ≥1M producer found; F11/F12 were tiny producers. | No separate repair. Do not report without a valid-input producer. |
| F14 | Compression dictionary indices wrap beyond 2^32 blocks | Confirmed structural mechanism; >25.8 Gbit and ~650 GB end-to-end. Not filed. | `6b60f9d`; historical function-level evidence. Full end-to-end remains infeasible, not a new finding. |
| F15 | Assertions on short/repeat-free estimator input | Confirmed availability issue; #261/duplicate #262; upstream response relied on 1M minimum. | `21b0a31`; regression passes. Short assessment behavior excluded. |
| F16 | Binary MultiMMC over-read at 4≤L≤16 | Confirmed memory error; #257, PRs #268/#269; contributor called it real. | `ed88de9` plus global minimum. Regression passes. |
| F17 | LRS can be quadratic on long repeats | **NOT-A-BUG / accepted limitation.** #52/#163/#214 closed as expected algorithmic cost. | No repair. Performance was bounded; no new label. |
| F18 | Nonregular file can hang during hashing | Upstream contributor classified as hardening, #259/duplicate #266. | Fork hardening `cdb5cd6`; regression passes. Not presented as accepted standards defect. |
| F19 | Subset arithmetic/zero length/partial block/provenance | Confirmed; #260/duplicate #267, contributor viewed overflow guard low priority and whole-file hash reasonable. | `0e1ffcd`; valid subset and regression pass. Whole-file versus assessed-subset identity distinction retained. |
| F20 | `-t` also truncates under `-c` | **NOT-A-BUG / documented semantics.** #127/#139/#140. | No repair. This audit exercised both `-t` and `-a`. |
| F21 | MSB-first bit order changes bitstring result | **NOT-A-BUG / convention unspecified.** #71/#125. | No repair. Representation must be recorded by caller. |
| F22 | Bitstring uses raw-value encoding | **NOT-A-BUG / deliberate design.** #71/PR #72/#125/#147. | No repair. Width/representation provenance remains required. |
| F23 | Literal-only intermediates and conditioned/report rounding inconsistencies | **UNCONFIRMED composite.** Partly #179/PR #251. | Reproduced `-c` `hAssessed=n×h'`; kept under F23, not new. |
| F24 | FMA NaN versus −inf near predictor boundary | **NOT-A-BUG / no decision effect found.** Adjacent #133/#134. | No repair. Reopen only with reachable result/verdict impact. |
| F25 | `calc_p_local` termination at very large N | **UNCONFIRMED theoretical.** | No repair; ≥2^31-scale test not run. Recorded untested. |
| F26 | Markov has no confidence adjustment | **NOT-A-BUG.** Final §6.3.3 has none; draft history #20/#21. | No repair. |
| F27 | Appendix G.2 Table 3 labels offset | **NOT-A-BUG in code / publication erratum.** | No code repair. |
| F28 | Deterministic long-memory sources can score high | **NOT-A-BUG / estimator-battery limitation.** #47/#70/#223. | No claim that software fixtures prove unpredictability. |
| F29 | Individual estimator blind spots | **NOT-A-BUG / battery limitation.** #70/#150/#223. | Only final minimum is relevant; no single-estimator defect inferred. |
| F30 | LRS estimates collision entropy, possibly above min-entropy | **NOT-A-BUG / explicit method.** #163 context. | Other estimators and final minimum are required. |

## N, R, NOVEL, and carried findings

| ID | Existing finding | Disposition/discussion | Repair/current audit treatment |
|---|---|---|---|
| N-01 | Binary chi-square m=1 wrongly passes | Confirmed, dangerous IID acceptance; not filed. | Fork `c8799f4`; regression passes. Existing #252 can still misreport aggregate IID success and is separate. |
| N-02 | Conditioned IID tests packed symbols, not conditioned bitstring | Confirmed; #271, contributor accepted bitstring remedy. | Fork `134d377`; regression passes. Full 8-bit `-c -a` cost remains high. |
| N-03 | `ea_conditioning -n -i` constant data assert/over-read/wild write | Confirmed in unbuilt tool; not filed. | **DEFERRED-NOT-BUILT.** TruePad does not build/use `ea_conditioning`; existing blocker if that scope changes. |
| N-04 | Restart accepts NaN/non-numeric H_I | Confirmed; distinct from #195. | Fork `db7a2ba`; regression passes. |
| N-05 | Conditioning JSON hashes/names input unrelated to supplied h′ | Confirmed in unbuilt tool; not filed. | **DEFERRED-NOT-BUILT.** Existing blocker if conditioning tool is enabled. |
| N-06 | Ignored SHA-256 failure reports stack bytes | Confirmed; not filed. | `cdb5cd6` for non-IID/IID, `fd83a43` restart; regression passes. Unbuilt program instances remain. |
| N-07 | Hash/read TOCTOU can bind one file's hash to another's estimate | Confirmed hardening/integrity issue; not filed. | **NEEDS-FIX.** Still present and relevant to TruePad; kept as existing blocker. |
| N-08 | Permissive/base-0 numeric parsing | Confirmed; not filed; #260 only adjacent. | **NEEDS-FIX.** Current code still contains mixed permissive parsing. No dangerous supported-path increase established. |
| N-09 | JSON/file write failure exits success | Confirmed; not filed. | Fork `47d6624` for shipped tools; regression passes. Unbuilt tools retain instances. |
| N-10 | Mislabelled/ambiguous JSON fields | Confirmed reporting issue; not filed. | **NEEDS-FIX.** Current. No new identity assigned. |
| N-11 | Conditioning MPFR exponent limit assertion | Confirmed in unbuilt tool; not filed. | **DEFERRED-NOT-BUILT.** Existing blocker only if enabled. |
| R-1 | Balanced alphabets can trip LRS long-double assertion | Confirmed elsewhere; residual of closed #246/merged PR #248. | **NOT-REPRODUCED-HERE** for original case on arm64; no fork fix. x86-64 80-bit check remains. |
| R-2 | Restart folds estimator no-result sentinel into entropy | Confirmed residual of closed #178. | Fork `d892b90`; regression passes. |
| R-3 | Restart IID read failure writes success JSON | Confirmed regression of closed #183. | Fork `23dca69`; regression passes. |
| NOVEL-01 | Selftest omitted final fields and returned only last comparison status | Confirmed; #272 contributor supported checking/stopping. | Fork `da0265c`, later guard repair `590c83a`; regressions pass. Distinct new missing-count issue is HARNESS-AUD-01. |
| NOVEL-02 | IID JSON emitted uncomputed placeholders | Confirmed; distinct from open PR #251. | Fork `9f64f62`; regression passes. |
| NOVEL-03 | Restart IID row/column permutation results have identical labels | Confirmed; introduced with PR #250, not filed. | **NEEDS-FIX.** Current reporting blocker; no value change. |
| C-01 | Restart array freed with scalar delete | Known upstream PR #242; no merged correction in audited baselines. | **NEEDS-FIX.** Reproduced on valid 1000×1000 sanitizer run, exit 6. |

## 2026-10-01 re-audit findings

These describe evidence quality, portability, or regressions around the fork;
they are not reissued as new defects.

| ID | Disposition in prior re-audit | Status at `106d31c` / treatment here |
|---|---|---|
| REV-001 | Confirmed historical contradictory documentation; corrections incomplete at the reviewed snapshot | Later documentation commits `5922ff8`, `45c156d`, `9802717`, `106d31c` correct major claims. Remaining statements are treated narrowly, not as proof. |
| REV-002 | Confirmed GCC build regression: undeclared `ULONG_MAX` after F19 | Repaired by `b75e763` adding `<climits>`. Native current build passes; current GCC rerun not performed. |
| REV-003 | Confirmed binary MultiMMC regression did not catch a reset mutant, while generic mutant was caught | Regression repaired in `8f0469c`; historical independent trace retained. Current regression suite passes. |
| REV-004 | Confirmed parser-path difference under GNU getopt/POSIXLY_CORRECT; all cases refused | Recorded as CLI portability behavior. Current macOS run did not re-execute GNU getopt matrix. |
| REV-005 | Partially supported: regression script/compiler assumptions and exact GCC numeric delta; Linux ASan blocked | Guard portability updated in `8f0469c`; strict macOS delta remains visible. Current Linux/x86-64 sanitizer still untested. |
| REV-006 | Partially supported: hash-status mutations exposed inadequate guards; one UB-dependent absent-file symptom did not reproduce | Guards repaired in `590c83a`; missing binary propagation and all current regressions pass. |
| REV-007 | Confirmed documentation rate-unit error | Documentation correction included in `5922ff8`; no new benchmark was inferred. |

## Other known upstream items explicitly encountered

| Item | Current audit observation | Classification |
|---|---|---|
| #22 | Full-precision normal quantile matches independent oracle | Intended known deviation; F07 |
| #127/#139/#140 | Conditioned truncation semantics | Accepted documented behavior; F20 |
| #153 | Valid 1M alternating IID input aborts at LRS `p_colPower >= LDBL_MIN` | Existing upstream issue; current blocker for IID robustness, not new |
| #155 | Two of 11 reference files differ on macOS arm64 | Existing platform delta; strict suite correctly fails |
| #178/#183 | Restart sentinel/read-report regressions | Fork repairs R-2/R-3 pass |
| #195 | Restart assertion path | Existing known path; not conflated with N-04 |
| #236 | OpenMP/xoshiro jump behavior | Existing discussion; no new output error demonstrated |
| PR #242 | Restart alloc/dealloc correction proposed | Existing C-01; sanitizer-reproduced |
| PR #251 | IID reporting despite failed tests / verbosity reporting work | Existing valid-input acceptance blocker; TruePad does not invoke `ea_iid` |
| #252 | IID JSON can report success/entropy with a required test failed | Existing blocker; historical valid-input reproducer retained |
| #253–#272 | Fork's 2026 issue/PR set | Actual saved issue/comment evidence under `logs/upstream/`; contributor replies are not NIST statements |

## Reopening rule applied

No rejected or out-of-scope finding was reopened. A future reopening requires
either a reproducible failure within the applicable sample/representation
domain or a distinct fail-closed/safety defect for invalid input. Merely
producing a figure from an undersized dataset under the explicit internal
override is not assessment-correctness evidence.
