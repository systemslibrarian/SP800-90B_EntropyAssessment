# Regression and existing-blocker ledger

## Current suite

| Check | Result | Evidence |
|---|---|---|
| Explicit release build: `non_iid iid restart` | PASS, exit 0 | `logs/build-supported.log` |
| Strict `run-all-checks.sh` | FAIL, exit 1: 15 pass, one known #155 selftest failure; 14 regressions executed | `logs/run-all-strict.log` |
| Narrow platform-delta mode | PASS, exit 0: exactly the two #155 files excused | `logs/run-all-platform-deltas.log` |
| Missing binary propagation | PASS control: wrapper exits 2 | `logs/wrapper-missing-binary.log` |
| ASan/UBSan supported builds | PASS after explicit libomp include; first failed configuration preserved | `logs/build-asan-ubsan.log` |
| Clang static analyzer | PASS; only chi-square dead stores | `logs/clang-static-analyzer.log` |
| Bounded invalid-input sanitizer matrix | 40/40 reject with status 255; no new sanitizer fault | `logs/asan-invalid-input-bounded.log` |
| OMP 1 versus 8 non-IID | exact JSON identity | `logs/openmp-reproducibility.log` |
| TruePad targeted integration/extraction tests | PASS: 10 files, 71 tests | `logs/truepad-targeted-tests.log` |

The strict failure is not converted to a pass in the main verdict. The
platform-delta run separately demonstrates the allow-list behavior.

## Repaired findings checked

“Current regression” means the corresponding unchanged script was among the
14 passing scripts. “Historical triple” means the 2026-10-01 re-audit ran the
actual parent, fixed commit, positive control, and meaningful mutant.

| Existing ID | Repair | Current evidence | Historical sensitivity evidence |
|---|---|---|---|
| F02 | `97571de` width provenance | `regression-width` PASS | parent/fix/mutant triple |
| F03/F04 | `c2f1dcd` 1M intake guard | `regression-minsize` PASS | parent/fix/mutant triple for global guard |
| F05 | `dfe325a` explicit no-result fields | `regression-notrun` PASS | parent/fix/mutant triple |
| F09 | `69b6094` MultiMMC Null reset | `regression-multimmc` PASS | literal oracle, parent/fix/mutant; repaired regression per REV-003 |
| F11/F12 | `c0ee84a` / `c217f20` estimator guards | `regression-estimator-guards` PASS | parent/fix/mutant triples |
| F14 | `6b60f9d` 64-bit dictionary indices | guard regression PASS | structural/function-level evidence; full >2^32-block execution remains infeasible |
| F15/F16 | `21b0a31` / `ed88de9` decline/over-read guards | estimator guard scripts PASS | parent/fix/mutant triples |
| F18 | `cdb5cd6` regular-file hardening | `regression-nonregular` PASS | parent/fix/mutant triple |
| F19 | `0e1ffcd` subset checks/provenance | `regression-subset` PASS plus valid 1M subset | parent/fix/mutant triple |
| N-01 | `c8799f4` m=1 failure | `regression-chisquare` PASS | parent/fix/mutant triple; #252 remains separate |
| N-02 | `134d377` conditioned IID bitstring tests | `regression-271` PASS | parent/fix/mutant triple |
| N-04 | `db7a2ba` strict restart H_I | `regression-restart` PASS | prior repair evidence |
| N-06 | `cdb5cd6`/`fd83a43` hash status | nonregular/restart scripts PASS | REV-006 fault-injection evidence |
| N-09 | `47d6624` report-write status | `regression-output` PASS | prior repair evidence |
| R-2/R-3 | `d892b90` / `23dca69` restart errors | `regression-restart` PASS | parent/fix/mutant triples |
| NOVEL-01 | `da0265c`, guards `590c83a` | `regression-272`, `regression-docs`, pin PASS | parent/fix/mutant and REV-006 evidence |
| NOVEL-02 | `9f64f62` computed-only IID JSON | `regression-iid-json` PASS | prior repair evidence |
| REV-002 | `b75e763` `<climits>` | Apple clang build PASS | prior GCC parent/child proof; current GCC untested |
| REV-003/005 | `8f0469c` regression corrections | affected current scripts PASS | historical mutants/cross-platform analysis |
| REV-006 | `590c83a` nonvacuous guards | current suite and missing-binary mutation PASS | historical status-injection mutants |

## Existing unresolved blockers on current supported build

| ID | Current applicability | Observation |
|---|---|---|
| C-01 | `ea_restart`, used by TruePad | **Reproduced** with valid 1000×1000 input under ASan: alloc/dealloc mismatch, exit 6. |
| N-07 | non-IID/IID/restart; TruePad reopens paths | **Present by inspection.** Hash and data reads are separate; integration prehash does not make later reads atomic. |
| N-08 | numeric CLI parsing | **Present by inspection.** TruePad supplies fixed strict arguments, reducing its exposure; standalone CLI remains permissive. |
| N-10 | report semantics | **Present by inspection.** Primarily integrity/labeling, no new rate increase shown. |
| NOVEL-03 | restart IID reports | **Present by inspection.** Row and column test labels collide; TruePad uses non-IID restart, so direct product path is unaffected. |
| R-1 | IID LRS on 80-bit long double platforms | **Unverified on this arm64 host.** Original platform-specific reproduction not run. |
| #153 | `ea_iid` valid data | **Observed** on 1M alternating samples: release assertion and no JSON. `-DNDEBUG` crossed the assertion point but was interrupted after 10m08s with no JSON; no verdict inferred. TruePad does not invoke IID tool. |
| #252 / PR #251 family | `ea_iid` aggregate verdict/reporting | Existing valid-input reproducer from prior evidence; not rerun to completion here. TruePad does not invoke IID tool. |
| N-03/N-05/N-11 | `ea_conditioning` | **Deferred / not built or shipped.** Becomes blocking if TruePad enables that program. |

## New harness controls

- `HARNESS-AUD-01`: removing one complete fixture/reference pair changes
  `PASS (11 files)` to `PASS (10 files)` without changing exit 0.
- `TP-AUD-01`: substituting ignored executables is not detected even with a
  selftest record that states it is not passing.
- TruePad's targeted unit tests pass, but their passing state does not cover
  either negative mutation above.
