# Upstream submission triage — production-code delta

Date: 2026-10-09  
Fork branch: `repair/2026-10-09-verified-defects`  
Upstream repository: `usnistgov/SP800-90B_EntropyAssessment`  
Upstream source checked: `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`

No upstream issue, comment, or pull request was created or modified while
preparing this triage. The fork is 70 commits ahead of the unchanged upstream
source at the time of review. That history is not a suitable upstream patch as
one unit: independent root causes, fork policy, report schema changes, build
portability, and audit machinery must stay separate.

## Recommended first submissions

1. **C-01 — suitable for a focused PR after coordination with open PR #242.**
   The defect is general C++ undefined behaviour, is reached by a valid
   1000×1000 restart input, and does not depend on TruePad. The smallest patch
   is the one-token `delete` → `delete[]` correction from `6f84ad7`, plus the
   alloc/dealloc-mismatch ASan reproducer and one valid-result control. Do not
   send PR #242's unrelated warning cleanup. Because
   [PR #242](https://github.com/usnistgov/SP800-90B_EntropyAssessment/pull/242)
   is still open and already contains the source correction, first ask whether
   maintainers prefer that PR split or a new focused PR; do not create a
   duplicate silently.

2. **IID #153 residual — suitable for a reopened/new residual issue, then a
   narrow PR.** The valid one-million-sample underflow abort is general and the
   upstream issue itself identified log-domain calculation as the remedy.
   Submit only the log-domain comparison in `shared/lrs_test.h` from
   `a3dde6f`, the clause-derived boundary oracle, the exact valid reproducer,
   and widths 1–8 controls. Do not combine it with verdict/reporting changes.
   [Issue #153](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/153)
   is closed, so the submission must explain why the supported-input residual
   is outside its completed disposition.

3. **IID #252 fail-closed aggregation — contribute to the existing PR rather
   than opening a competitor.**
   [PR #252](https://github.com/usnistgov/SP800-90B_EntropyAssessment/pull/252)
   is open and currently changes `ea_iid` only. The smallest complete change
   should make the aggregate verdict depend on chi-square, LRS, and permutation
   outcomes; return nonzero on rejection; set JSON `IID` false; distinguish a
   completed rejection from an input/tool error; omit the final accepted
   entropy; and apply the same rule to IID restart rows and columns. Preserve
   component values as diagnostics. The relevant fork code is `007d0e7`, with
   deterministic period-two negative controls. Do not submit the combined
   `a3dde6f`/#153 history wholesale.

4. **N-01 binary chi-square `m = 1` — suitable for a new issue plus focused
   PR.** This is general standards correctness on valid inputs and can wrongly
   accept dependent data. The minimum patch is the decision correction in
   `c8799f4`, a one-million-sample positive control, a dependent negative
   control, and the independent §5.2.3 calculation. It must not be bundled
   with other IID reporting work.

5. **N-02 conditioned IID test representation — suitable for a PR against
   existing issue #271.** The behavior is general. The smallest patch is the
   `data.bsymbols` test view under `-c` from `134d377`, leaving `-i` unchanged,
   with one valid multi-bit negative control and binary/nonbinary controls.
   The submission must state the 8× permutation-cost consequence for `-c -a`.
   [Issue #271](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/271)
   remains open.

6. **NOVEL-03 restart permutation labels — suitable for a focused PR.** It is
   a general report-integrity defect introduced by upstream JSON reporting,
   not a TruePad customization. Submit only the `dataLayout` propagation from
   `25fbb54` and the synthetic JSON-population unit proving `rows` 0–2 and
   `columns` 0–2. No stochastic permutation run or estimator change is needed.

## Exhaustive production-delta classification

| Fork commit(s) / repair | General or fork-specific? | Upstream suitability | Smallest defensible submission |
|---|---|---|---|
| `d240098`, `06c693c`, `7ce69e9` — macOS/Homebrew/OpenMP/arm64 Makefile support | General portability | Suitable as one platform PR, after a clean macOS build record; separate from estimator work. | Darwin-only include/library discovery, Apple-clang OpenMP flags, and arm64 default without changing Linux flags. Add a documented macOS build control; no audit prose. |
| `876ba05` — supported target boundary | Fork/TruePad release policy | **Not suitable upstream.** Upstream intentionally exposes all utilities. | Keep local. Upstream could independently add named target groups, but not this product-specific exclusion. |
| `134d377` — conditioned IID bitstring view | General standards behavior | Strong PR candidate for open issue #271. | One view-selection change plus exact valid fixtures and cost disclosure. |
| `c2f1dcd` — one-million-sample intake enforcement | General SP 800-90B application rule, with fork-specific JSON detail | Suitable, but as a dedicated policy PR tied to #255/#257/#258/#261/#263/#264 rather than mixed estimator patches. | Central guard before estimators in `ea_non_iid` and `ea_iid`, nonzero exit, explicit noncompliance JSON, exact 999,999/1,000,000 controls. Decide separately whether any development override belongs upstream. |
| `ed88de9` — binary MultiMMC short-length over-read | General memory safety | Do not open a new PR while [#268](https://github.com/usnistgov/SP800-90B_EntropyAssessment/pull/268) is open. Revise or replace it only with maintainer agreement. | Estimator declines (or an upstream-chosen production assert) when `L < D_MMC+1`, plus ASan negative control. Pair operationally, but not in one commit, with the central sample minimum. |
| `c0ee84a` — compression `v < 2` guard | General numeric safety | Existing [PR #270](https://github.com/usnistgov/SP800-90B_EntropyAssessment/pull/270) is the right vehicle. | The local estimator guard and direct-call regression only; keep central sample enforcement separate. |
| `c217f20` — collision `v <= 1` guard and fallible combination | General numeric safety | Suitable after issue #264 discussion; lower priority because supported CLI intake now excludes its tiny reproducer. | Estimator returns no result, caller ignores only that sentinel, direct-call NaN control, and a valid-input unchanged control. |
| `21b0a31` — lag/LZ78Y/LRS decline instead of assert | General robustness, mostly outside valid CLI inputs | Issue discussion first; not a combined PR as-is. | Split by estimator/invariant. Submit only a case with a supported-input or library-call contract and a nonvacuous reproducer. Do not ask upstream to assess undersized data. |
| `0e1ffcd` — subset arithmetic/provenance | General CLI/report correctness | Suitable for issue #260, but split the undisputed arithmetic from hash-policy questions. | First PR: multiplication overflow, zero size, EOF checks. Second only if schema is agreed: `subsetIndex`, requested count, actual count. Preserve whole-file hash semantics unless separately changed. |
| `97571de` — effective width in JSON | General report provenance | Strong small PR for issue #254. | Add `bitsPerSymbol` and whether it was inferred; do not change inference or add a policy warning in the same submission. |
| `cdb5cd6` — reject nonregular inputs | General hardening | Not recommended unless upstream requests it; the upstream response treated this as abnormal input, not a tool defect. | If invited, only `fstat`/regular-file refusal and FIFO/device timeout controls. |
| `c8799f4` — binary chi-square `m=1` verdict | General valid-input correctness | Strong new issue/PR candidate. | One decision fix, §5.2.3 oracle, exact one-million-sample positive/negative controls. |
| `db7a2ba` — strict restart `H_I` | General CLI and memory-safety hardening | Suitable focused PR. | `strtod` full-consumption and finite checks, keep the existing range check, JSON/nonzero error tests for NaN/Inf/suffixes plus valid controls. |
| `23dca69` — restart IID read error written to wrong object | General report correctness | Strong tiny PR, identified as a residual/regression of closed #183. | Correct the selected report object and test both `-i` and `-n` read failures. |
| `d892b90` — restart folds no-result sentinel | General valid-input correctness (false rejection/too low) | Suitable issue then PR. | Guard only the fallible estimator folds, with the exact one-million-sample de Bruijn control and ordinary unchanged control. |
| `fd83a43` — restart ignores hash failure | General integrity/safety | Suitable focused PR, possibly with report-write handling if maintainers want one I/O series. | Check status, omit digest on failure, set the correct report error, and test absent/unreadable input. |
| `47d6624` — report write failures | General CLI/report integrity | Suitable PR, but keep the helper and three supported call-site conversions together. | One checked JSON writer, nonzero open/flush/close failure behavior, writable positive control. Add conditioning/transpose separately if upstream requires all tools in scope. |
| `9f64f62` — computed-only IID fields and verbosity-independent aggregate | General report correctness | Contribute to open [PR #251](https://github.com/usnistgov/SP800-90B_EntropyAssessment/pull/251), not a duplicate. | PR #251's verbosity-independent calculation plus omission of uncomputed fields; keep #252 verdict gating separate. |
| `6b60f9d` — 64-bit compression dictionary indices | General theoretical large-input correctness | Issue first; low priority until upstream accepts function-level evidence. | Type-only change plus boundary harness. State that end-to-end input needs impractical memory; do not overclaim runtime validation. |
| `69b6094` — MultiMMC Null prediction run handling | General estimator correctness (repairs a too-low component) | Suitable issue first, then a narrow PR after independent mathematical review. | Binary and generic predictor-update corrections together, controlled oracle fixture, and proof that final aggregation is not silently raised without the repaired estimator being binding. |
| `dfe325a` — record estimators producing no value | General diagnostic schema | Issue/schema discussion first. | Add only an explicit not-run/no-result list; do not turn a legitimate estimator decline into assessment failure or success. |
| `b75e763` — explicit `<climits>` include | General compile portability | Suitable only folded into the smallest source PR that needs `ULONG_MAX`; too small for a standalone PR. | One include and a compiler control. |
| `590c83a` production-file delta | Comment/attribution correction only | No upstream code submission needed. | None. Preserve the local attribution correction. |
| `6f84ad7`, `b3db7ab` — C-01 | General memory safety | Strong focused PR after coordination with open #242. | One-token `delete[]` fix plus ASan detector-positive, vulnerable-parent, and exact valid fixed controls. |
| `c01fb43` — N-07 assessed-byte identity | General integrity problem, but current contract is shaped by TruePad provenance needs | **Not suitable upstream as-is.** It redefines `sha256`, conflicting with the upstream preference recorded on #260 for a whole-file hash. | Retain whole-file `sha256`; add a separately named `assessedSha256` over the immutable buffer or redesign around one verified snapshot. Specify subset identity and TOCTOU semantics before code. |
| `a3dde6f` — #153 calculation plus #252 data model | Two general defects combined locally | **Do not submit this commit wholesale.** | Split into (a) the #153 log-domain numeric patch and (b) the #252 verdict/report model. Each needs its own reproducer and review. |
| `007d0e7` — IID and restart fail-closed behavior | General standards/report behavior | Contribute to open PR #252. | Add nonzero status, false IID verdict, completion state, omitted accepted entropy, restart parity, and deterministic controls. |
| `031d7ee` — N-08 strict integer parsing | General CLI hygiene | Suitable only after extending the same parser contract and tests to upstream's conditioning CLI; current fork patch is intentionally supported-scope only. | Shared unsigned-decimal helper, all direct integer arguments in all upstream-built tools, overflow/sign/suffix/octal tests, unchanged valid decimal controls. |
| `094189c` — N-10 statistic semantics | General report clarity; current JSON rename is compatibility-sensitive | Issue first, not a direct PR as-is. | First submit the uncontroversial restart assignment and explicit stdout label. Agree JSON backward compatibility and conditioning track semantics before renaming fields. |
| `25fbb54` — NOVEL-03 row/column labels | General report integrity | Strong focused PR candidate. | One `dataLayout` field propagated by the report helper plus a deterministic six-result unit test. |

## Non-production but generally useful upstream work

- The final-output selftest coverage from `da0265c` remains a strong candidate
  for open [issue #272](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/272).
  The smallest submission compares every required final field, aggregates all
  file failures, proves a missing reference is fatal, and exits nonzero.
- The fork's authoritative script/fixture inventories are general harness
  hardening, but should be offered separately from mathematical fixes. Their
  mutation controls—not their TruePad attestation metadata—are upstream-relevant.
- TruePad executable attestation, fork pinning, production approval policy, and
  `productionApprovalEnabled = false` are integration/release-governance
  controls and do not belong in the NIST estimator repository.

## Submission order

The lowest-risk maintenance reduction is: C-01 coordination, #153 residual,
#252 collaboration, N-01, #271, then NOVEL-03 and the small restart/reporting
repairs. Schema and provenance proposals (N-07/N-10) should wait for contract
agreement. Fork scope policy (`876ba05`) should remain local.
