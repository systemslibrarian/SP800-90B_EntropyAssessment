# Standards and implementation coverage matrix

Status meanings: **verified** is evidence from this audit; **prior** relies on
identified historical evidence; **blocked** was not completed; **N/A** is
outside the supported TruePad path.

| Requirement / risk | Source path | Independent expectation | This audit | Prior coverage / remaining gap |
|---|---|---|---|---|
| §3.1.1 sequential minimum | `shared/utils.h`, `non_iid_main.cpp`, `iid_main.cpp` | ≥1,000,000 sample values, not bytes/bits by assumption | **verified** ordinary sub-minimum cases reject; valid 1M cases run at every supported width 1..8 | F03 global guard; concatenated-chunk provenance not represented by CLI |
| §3.1.1 conditioned count | `non_iid_main.cpp` `-c -t/-a` | ≥1M outputs, assessed as bitstring | **verified** `-t` 1M bits; `-a` 8M bits on 1M 8-bit symbols | F20 is accepted option semantics; physical conditioning assumptions untested |
| §3.1.2 IID decision | `iid_main.cpp`, `iid/*` | all required Section 5 tests decide claim | uniform pass verified; alternating valid case hits known #153; drift incomplete | N-01/N-02 repaired on fork; existing #252 incomplete-result acceptance remains |
| §3.1.3 non-IID aggregation | `non_iid_main.cpp` | binary: min original/submitter; nonbinary: min(original,n×bitstring,submitter) | **verified** sparse/4-bit/8-bit values and fields; no new mismatch | F01 withdrawn; F02 width reporting repaired; F23 reporting remains unconfirmed |
| §3.1.3 truncation/subsets | `shared/utils.h`, mains | any assessed subset still ≥1M samples and accurately identified | **verified** second 1M subset of 2M; bad offset rejected | F19 repair and subset provenance regression pass |
| §3.1.4 restart dimensions | `restart_main.cpp` | 1000 restarts ×1000 samples | **verified** exact valid matrix runs; periodic matrix sanity-rejected | simulated cutoff is upstream policy, not official erratum |
| §3.1.4 restart aggregation | `restart_main.cpp` | sanity plus row/column estimates, final min with H_I | **verified** uniform control `hr=.838909`, `hc=.829529`, `hi=.8` | R-2/R-3 pass; NOVEL-03 row/column labels unresolved |
| §3.1.4 IID restart track | `restart_main.cpp -i`, `iid/*` | test row and column datasets and constrain by H_I | **verified** valid 1000×1000 uniform matrix passes, `hr=hc=.993899`, `hi=.8` | Confirms existing N-10/NOVEL-03 reporting defects; TruePad uses `-n` |
| §6.3.1 MCV | `shared/most_common.h`, `utils.h` | clause-derived confidence formula | **verified** constant-source analytic check, worked-example calculation, and exact full-quantile implementation comparison | F07/#22 retained; potential errata uses a rounded intermediate rather than changing the formula |
| §6.3.2 collision | `non_iid/collision_test.h` | finite result or explicit no-result | regression passes; valid battery exercised | F12 fixed; no separate large analytic oracle this audit |
| §6.3.3 Markov | `non_iid/markov_test.h` | finite bound for binary chain | P(stay)=.99 control yields low estimate | F26 is spec-consistent; no exhaustive transition oracle |
| §6.3.4 compression | `non_iid/compression_test.h` | sufficient blocks; finite root/search | biased fixture binds conservatively | F06 accepted standard limitation; F11/F14 repairs covered historically |
| §6.3.5 t-tuple | `non_iid/tuple_test.h` / suffix-array code | repeat statistics constrain periodic data | periodic/repeated-block controls produce zero/near-zero aggregate | fixed-parent mutation evidence reused; no new standalone oracle |
| §6.3.6 LRS | `non_iid/lrs_test.h` | collision-based result or explicit no-result | repeated-block control; IID alternating exposes known #153 | F05 no-result reporting repaired; F17 performance limitation accepted |
| §6.3.7 MultiMCW | `non_iid/multi_mcw_test.h` | predictor update/tie rules | valid battery and existing regressions | F04 unreachable under minimum; literal independent oracle is historical |
| §6.3.8 lag predictor | `non_iid/lag_test.h` | score/tie/run behavior | valid dependent controls; strict regressions | no new clause-by-clause oracle |
| §6.3.9 MultiMMC | `non_iid/multi_mmc_test.h` | Null prediction ends correct run | regression pass; historical parent/fix/mutant evidence reused | F09 repaired; F10 remains unconfirmed at shipped constants |
| §6.3.10 LZ78Y | `non_iid/lz78y_test.h` | finite result or explicit no-result | valid battery and guards | F15 repair covered historically; deterministic blind spots are spec limits |
| Search/numerics | `shared/utils.h` | converge, no NaN/Inf in accepted result | valid outputs finite; static/sanitizer checks; MCV oracle | F08/F24/F25 dispositions retained; architecture coverage incomplete |
| Symbol remapping/width | `shared/utils.h` | record effective width and conversion | **verified** every supported width 1..8 at 1M symbols, plus sparse alphabet | F02 behavior/reporting remains a documented policy choice |
| JSON write/error paths | mains and `test_run_*` | failure nonzero; no false complete report | existing regression pass; TruePad checks subprocess status | N-09 repaired; changing/stale-file integration still N-07 concern |
| Text/JSON verdict agreement | mains | same final value and success/failure | checked across battery/restart; no new disagreement | N-10/NOVEL-03 remain reporting blockers |
| Selftest integrity | `cpp/selftest/*` | compare exact reviewed corpus; propagate every failure | **failed** missing pair passes (`HARNESS-AUD-01`); binary failure propagates | NOVEL-01 and REV-006 fixes still pass |
| Memory lifetime | all three mains/shared | no UB on valid input | **failed** restart ASan reproduces existing C-01 | macOS leaks unavailable; Linux/Windows not run |
| OpenMP reproducibility | estimator/restart parallel regions | deterministic non-IID output; documented stochastic paths | non-IID 1 vs 8 threads byte-identical | IID/restart stochastic cross-thread distributions not deeply quantified |
| Input identity | hash + read paths | assessed bytes match claimed identity | fork records hashes; **existing N-07** separate hash/read persists | dynamic changing-file race not executed |
| TruePad sample contract | TruePad qualifier | exact 1-bit byte encoding and counts | **verified** strict size/value/sidecar/restart metadata gates | actual capture/hardware unavailable |
| TruePad tool identity | TruePad qualifier/setup | exact approved build and passing suite before assessment | **failed** `TP-AUD-01` | direct invalid acceptance reproduced |
| TruePad source pin | TruePad lock/setup/docs | one reviewed fork SHA and upstream base | **failed** `TP-AUD-02` | implementation and governing design conflict |
| TruePad fail-closed parsing | TruePad qualifier | reject nonzero, incomplete, nonfinite, stale destination, wrong hashes | code review + 71 targeted tests pass | protection is conditional on authentic tools |
| Toeplitz length/budget | TruePad extraction | `m` within stated entropy/LHL budget; seed `n+m-1` | code review + targeted tests pass | physical conditional entropy is unestablished |
| Seed distribution/independence | TruePad docs/code | uniform independent seed or explicit computational model | contract documents distinction | **blocked** no seed authority or physical evidence |
| Health/restart/operating range | deployment evidence | characterize real source and continuously monitor it | **blocked** synthetic matrices only | required before production reliance |

## Fixture coverage

All ordinary fixtures contain exactly 1,000,000 sample bytes. The subset source
contains 2,000,000 sample bytes. Exact generator, seed, counts, and hashes are
in `generators/valid_fixtures.py` and `logs/fixture-manifest.json`.

Covered distributions/dependencies: constant, nearly constant, extremely
biased binary, approximately uniform data at every width 1 through 8, sparse alphabet,
alternating, period-six, high-persistence Markov, two-regime drift, repeated
block, valid subset, conditioned truncated/all-data, and restart matrices.

Statistical software fixtures demonstrate program behavior only. Passing an
IID battery or receiving a high estimate does not demonstrate a physical
entropy source or unpredictability.
