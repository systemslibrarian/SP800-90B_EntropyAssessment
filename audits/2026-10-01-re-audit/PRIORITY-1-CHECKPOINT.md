# Completed Priority-1 review findings — checkpoint before expansion

Historical: **34fb906196f8d47da774c88928eff0d8ec08d618**.
Recorded current: **328ec20c146e43b4eed86424847a106539c70a5a**, master.
Original user checkout/index preserved unchanged, independently rechecked in probe 076. No review assessment or container is running. No repair, commit, push, upstream contact or agent launch occurred.

## Findings-first verdict table

| ID | Fresh verdict | Historical finding | Recorded current / limits |
|---|---|---|---|
| REV-001 | **CONFIRMED** historically | Contradictory unchanged-source/result claims exist alongside actual F09/N-01 changes | **Partially addressed**: README/tracker and BUILDING opening corrected. NOTICE only-decline and exact-reference claims remain. Each passage is separated in REV-001-REV-007.md. |
| REV-002 | **CONFIRMED** | GCC13.3 make non_iid fails on undeclared ULONG_MAX; actual F19 parent succeeds, introducing child fails | Current build independently fails identically. Native Apple-clang builds both pass. |
| REV-003 | **CONFIRMED** | Binary reset deletion compiles and runs, r=100275 vs independent/fixed17, yet unchanged full regression passes | Source/regression identical at current. Generic missing-Null-reset mutant is caught; tested target behavior agrees with independent complete traces. |
| REV-004 | **CONFIRMED** parser-path finding | GNU getopt diverts -inf/-1 to option rejection; POSIXLY_CORRECT reaches intended numeric checks; every case refuses | Full original default/POSIX suites each timed out later at valid H_I=0; no full-suite pass claimed. Relevant code unchanged. |
| REV-005 | **PARTIALLY SUPPORTED** | Hard-coded Clang/Homebrew infrastructure and exact GCC value 0.15932269772157898 vs required0.15932269772157773 reproduced | Native full unchanged suite passes. Linux adapted ASan run blocked by emulation/cgroup OOM even for trivial control; non-ASan exact value is not a sanitizer-suite pass. |
| REV-006 | **PARTIALLY SUPPORTED** | Ignored-status mutants pass absent-file/nonregular checks; readable-file artificial injection proves fixed rejection and mutant/parent continuation | Immediate parent's original absent-file PASS did **not** reproduce: garbage hash was nonempty; undefined data makes that nonportable. Current relevant sources identical. |
| REV-007 | **CONFIRMED** | Wrong rate unit: measurement implies0.933ms/bit, not0.94ms/thousand bits | Wrong sentence remains in recorded current. Minute/hour extrapolations use intended rate. Arithmetic only. |
| Known #242 | **CONFIRMED**, not new | new[]/scalar delete remains in simulateBound and prior audit explicitly records it | Default native ASan does not report it; explicitly enabled detector diagnoses full unchanged5m-round CLI. Linux ASan locally blocked. |

No genuinely new ASTRA ID assigned during this priority retest. Existing identifiers are preserved. Regression sensitivity gaps are not mislabeled as incorrect target repairs.

## Positive evidence obtained incidentally, with boundaries

- F09 reference: new literal §6.3.9 implementation validated against published example; all target/reference prediction/winner/scoreboard/run fields match199,998 binary rounds in both paths and114,144 original generic-fixture rounds. This does not finish all Priority-2 F09 claims (actual parent/full final-estimate analysis, additional boundary cases/errata, missing candidate fixture).
- N-06: full readable-file controls and proven artificial digest failure support current behavior for all three built tools; actual restart parent and compiling mutants continue. Original regression gap remains.
- Guard suite: genuine full native macOS pass; Linux sanitizer blocked; do not infer all four guard repairs independently verified from fixed-only execution.
- Numerical pin value0.12644573619604868 was actually computed in a full GCC ringOsc run and collision was minimum. The changed pin checker itself and mutation sensitivity are still pending.

## Method/platform qualifications

Host macOS26.6.2 arm64, Apple clang21.0.0, native long double8bytes/53significand bits. Isolated Ubuntu24.04 amd64 under emulation, GCC13.3.0, glibc2.39, long double16bytes/64significand bits. Two OpenMP threads, one CPU-heavy probe at a time. GCC ordinary failure was recorded first; functional probes add command-line-only -include climits. Every decisive test log has command/cwd/snapshot/environment/assertion pre-recorded and exit/duration/deadline result captured. Runtime/ASan details are in individual reports and COMMANDS.jsonl.

Full original restart probes046/047 timed out at approximately289seconds and were killed with their named containers. No simulator count or coverage was weakened. Default Linux sanitizer children died from cgroup OOM before main; independent control proves the environmental limitation. No Linux ASan clean claim. Native known-mismatch full CLI used original5million rounds. Source modifications exist only in explicitly named disposable copies.

Unavailable: checkpoint-6 markdown/archive and candidate-25.bin in the recorded search. No archive checksum or exact archived mutation replay is claimed. Available repository generators/PDF were checked against their supplied manifests before execution. Public fixtures' hashes, lengths, alphabets, sample counts and widths are saved. Original current/historical documents and all repair-parent maps are preserved.

Prior-review reporting cautions: r is longest run+1; the absent-file parent-pass outcome depends on undefined hash contents and was not reproduced here; original default/POSIX full-suite passes cannot be claimed from this audit's timeouts; suppressing alloc/dealloc mismatch/leaks never proves those properties clean; corrected current prose must not inherit historical defects wholesale. No claim of an invented error by the previous reviewer based solely on an unavailable archive or another platform's nonreproduction.

## Artifacts and resume

Primary files: REPORT.md, inventory.json (54 findings plus known-item/command records), COMMANDS.jsonl, NEXT.md. Detail: REV-001-REV-007.md, REV-002.md, REV-003.md, REV-004.md, REV-005.md, REV-006.md, KNOWN-242.md, BASELINES.md/baseline-map.json, fixture-manifest.json, mutation-evidence, captured, reference-results, hash-results, full logs. Frozen checkpoints each have MANIFEST.json and SHA256SUMS.

No endorsement yet as an independently verified pinned Noise to Numbers lab baseline: Priority-2 positive repair evidence and changed pin/refdata checks remain pending. The repository is useful as a **labeled diagnostic/teaching artifact** for portability and regression-sensitivity lessons, provided exact snapshots/platforms/known limitations are shown. That is distinct from trusting its entropy figures for production-security decisions or claiming physical entropy from synthetic/public diagnostic data.

Exact next unfinished work: wait for approval of Priority-2 stage; then begin F09 actual-parent/full-output comparison and pin/refdata evidence, followed by N-01 and remaining positive repair pre-fix/fixed/mutation triples. All Priority-3 incomplete/unresolved tasks remain unstarted in this audit. No running process to resume.