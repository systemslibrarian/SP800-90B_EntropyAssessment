# Independent SP 800-90B fork audit — Priority-1 and Priority-2 complete

Review ID: `2026-10-01-astra-7dcecac1`.

## Priority-2 positive-repair summary

Actual immediate-parent/fixed/meaningful-mutant triples were run for every tested repair (F02, F03, F04, F05, F09, F11, F12, F15, F16, F19, N-01, N-02, R-2, R-3, NOVEL-01). Each shows the claimed pre-fix defect on its real parent, a passing fixed build with valid positive controls, and a compiling mutant caught by the unchanged original regression. Full detail, scope, and limits: POSITIVE-REPAIRS.md and inventory.json.

Key numbers: F09's original fixture final estimate is `0.0008876062538599284` on both the actual parent and fixed build (literal t-tuple binds; MultiMMC alone moves from `0.00211176482535928` to `0.93188950992564512`). All 11 reference-corpus files are byte-identical between parent and fixed on both macOS (2/11 known platform predictor deltas on both) and GCC/Linux (11/11 pass on both). The pin script computes `0.12644573619604868` on both historical and current scripts and correctly rejects both its built-in perturbation and a new compiling estimator mutant. N-01's chi-square m=1 fix is confirmed, but the known #252 aggregate-reporting gap means a failed chi-square test can still coexist with `errorLevel=0`/`IID:true`/a reported entropy figure — this is a pre-existing reporting limitation, not a defect in the retested fix.

Not completed in this review: F14 end-to-end >2^32-block numeric evidence (structural-only), the nine originally-unresolved IDs (F01, N-03, N-05, N-07, N-08, N-10, N-11, NOVEL-03, R-1), and the checkpoint-6/candidate-25.bin material, which remains unavailable (BLOCKED). These would be Priority-3 scope and were not approved/started.

## Findings first

- **REV-001: CONFIRMED historically; current corrections are real but incomplete.** The current README/tracker and BUILDING opening no longer make their historical unchanged-source/result claims. NOTICE's only-decline summary and BUILDING's exact-reference claim remain overbroad. See REV-001-REV-007.md for passage-by-passage scope.
- **REV-007: CONFIRMED in both snapshots.** The recorded current BUILDING still says “0.94 ms per thousand bits.” The measurement implies 0.933 ms/bit or 0.933 s/thousand bits; the minute/hour extrapolations use the intended rate. No fresh benchmark was run.
- **REV-002: CONFIRMED in both snapshots on GCC 13.3.** The actual F19 parent builds; F19 child/historical/current fail with undeclared ULONG_MAX. All use installed dependencies and unchanged source/build commands. Native macOS builds pass; Linux x86-64 execution is emulated, not native timing evidence. See REV-002.md.
- **REV-005: PARTIALLY SUPPORTED.** Native unchanged guard suite passes. Unchanged Linux script fails its compiler assumptions. The exact GCC compression value `0.15932269772157898` is independently reproduced and fails the script's expected `0.15932269772157773`. Full Linux ASan execution is blocked by cgroup OOM under emulation, even for a trivial correct control; those killed child processes are not clean evidence. See REV-005.md.
- **REV-003: CONFIRMED.** The fixed binary behavior matches an independently derived reference (r=17); a compiling/reachable binary reset mutant yields r=100275 and the full unchanged regression still passes. A separate generic missing-Null-reset mutant yields r=6603 and is caught. All target/reference intermediate fields agree over the tested binary and generic fixtures. This is a binary regression gap, not an incorrect tested implementation. See REV-003.md.
- **REV-004: CONFIRMED parser-path difference.** Default GNU getopt rejects -inf/-1 as options; POSIXLY_CORRECT reaches the intended numeric checks. All refuse. Both full original suites timed out later at H_I=0; those full-suite results remain incomplete. See REV-004.md.
- **REV-006: PARTIALLY SUPPORTED.** Hash-status mutants pass the original inadequate checks; explicit readable-file digest failure proves fixed tools reject and mutants/actual restart parent continue. The prior immediate-parent absent-file PASS did not reproduce here: undefined hash bytes were nonempty. That local difference is not a cross-platform refutation. See REV-006.md.
- **Known #242 remains.** Native default ASan/UBSan full restart runs without reporting the mismatch; explicitly enabling alloc_dealloc_mismatch diagnoses new[]/scalar delete on the full unchanged 5,000,000-round valid-input path. This is previously documented, not a new finding. See KNOWN-242.md.
- Remaining runtime review findings and repair claims are PENDING. This is not a completed execution audit.

## Scope and preservation

- User checkout: `/Users/gmcas/repos/SP800-90B_EntropyAssessment`.
- Historical reviewed snapshot supplied: `34fb906196f8d47da774c88928eff0d8ec08d618` (not yet resolved).
- Recorded current branch: `master`; tip: `328ec20c146e43b4eed86424847a106539c70a5a`.
- Initial working tree and index are clean, including untracked-file enumeration. Exact status and empty diffs are saved separately. This observation is scoped to probe 001, not assumed indefinitely.
- Review artifacts are outside the user checkout, in this directory.
- No reviewed source/documentation will be repaired. No reset, clean, stash, commit, push, issue, PR, or upstream contact is authorized.
- Builds, instrumentation, and mutations will use detached worktrees or disposable copies only.
- No agents have been launched; explicit approval is required to launch any.
- Before an execution stage expected to exceed ten minutes, provide its estimated runtime/resources/evidence and wait for approval.

## Evidence standard

Every execution probe must have a pre-execution command record, cwd, snapshot, selected non-secret environment, intended assertion, complete stdout/stderr files, exit status, duration, and timeout/interruption status. Probes have a maximum 290-second process-group budget. A timeout is incomplete evidence. Only one CPU-heavy probe runs at a time.

VERIFIED repair evidence requires an appropriate pre-fix behavioral failure, fixed passing case with valid controls, and a compiling/reachable meaningful mutation caught by the claimed regression. Source inspection, observation, and inference will be labeled separately. Historical and recorded-current results will not be conflated.

## Environment and access

Observed in probe 001: terminal, filesystem, and complete local Git access are available. The checkout is non-shallow, has no partial-clone/promisor configuration, and all 3,348 reachable object inventory lines were enumerated without missing objects. No applicable AGENTS.md, CLAUDE.md, or .github instruction files were found in the checkout/ancestor search. Source access will use local objects/files, not browser snippets.

- OS: macOS 26.6.2 (25G83), Darwin 25.6.0; architecture: arm64.
- Git: 2.54.0 (Apple Git-157).
- Python: 3.14.7 at `/opt/homebrew/opt/python@3.14/bin/python3.14`.
- `make`, Apple `clang++`/`g++`, Homebrew, pkg-config, coreutils timeout, and Docker CLI are on PATH. GCC 13/14/15 executables and Valgrind were not found under those names. Compiler identity/version, dependency availability, Docker engine, long-double format, and sanitizer behavior remain PENDING.
- This differs from the previous Linux x86-64/GCC 13.3 environment. No cross-platform verdict follows from capability discovery.

Evidence: `logs/001-access-state-instructions.{stdout,stderr,result.json}`, `initial-working-tree.status`, `initial-working-tree.diff`, `initial-index.diff`, `initial-changed-files.json`. Exit 0; 0.285 seconds; no timeout/interruption. No build or assessment has run.

Probe 004 created separate detached historical/current worktrees under the review directory and rechecked the user checkout: status exactly matches the initial capture. Apple clang is 21.0.0 (`clang-2100.3.34.2`); `/usr/bin/g++` is also Clang, not GCC. Homebrew GCC 16.2.0 is installed as `g++-16` (the earlier absence check covered only versions 13–15). Installed dependencies: jsoncpp 1.9.8; libdivsufsort Homebrew 2.0.1 (pkg-config metadata 2.0.0); libomp 23.1.2; OpenSSL 3.6.4; MPFR 4.2.2; GMP 6.3.0. Host RAM 16 GiB; 10 physical CPUs. An existing Colima Docker engine is available: server 29.5.2, Linux arm64, kernel 6.8.0-117-generic. This establishes an isolated Linux runtime, not yet an x86-64 execution environment. No packages installed or builds run yet. Evidence: `environment-discovery.json`, `worktrees-initial.json`, `logs/004-rev-environment-worktrees.*`; exit 0, 3.595 seconds, no timeout/interruption.

## Original evidence availability

The user supplied a review brief. The exact names Findings-So-Far.md, SP800-90B-Independent-Review-Checkpoint-6.md, SP800-90B-Review-Checkpoint-6-Evidence.zip, and candidate-25.bin were searched in the entire checkout and to depth three under Downloads, Documents, and Desktop. No matches or search errors were observed (attachment-availability.json). This does not prove absence everywhere, but none was supplied or found in these locations. Consequently archive checksum verification, exact checkpoint-6 mutation replay, and the candidate-25.bin numerical claim are presently BLOCKED by unavailable evidence. Continue independent source/local-fixture checks; do not invent an original fixture.

## Baseline map and inventory

Probe 002 resolved all supplied commits and all recorded repair commits/parents from local Git. It independently parsed both complete tracker blobs: each has 30 confirmed-queue IDs and 17 outside-queue IDs. inventory.json now includes all 47 original IDs plus REV-001–REV-007 (54 entries), all PENDING independent testing. Full historical/current claim text is in tracker-inventory.json; the complete repair/parent table is in BASELINES.md and baseline-map.json.

| Baseline | Full SHA |
|---|---|
| Documented upstream | `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289` |
| Audit reproduction snapshot | `237d85c8399817bbd492af7a67481707deb3be00` |
| Pre-second-pass snapshot | `c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4` |
| Historical reviewed snapshot | `34fb906196f8d47da774c88928eff0d8ec08d618` |
| Recorded current tip | `328ec20c146e43b4eed86424847a106539c70a5a` |
| F09 repair | `69b6094b01144a0301cc941fa692dee9b060f0a6` |
| F09 actual immediate parent | `6b60f9d3adc37b245bef03175ffe8e7eec8afe5b` |
| N-01 repair | `c8799f4e88128223b201c852a54ea6e26a85d06c` |
| N-01 actual immediate parent | `c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4` |
| F19 repair | `0e1ffcd518f9e06d06603186039955df89094a74` |
| F19 actual immediate parent | `21b0a31545be5d4ae7966fcb2917c6e1cd4b48a2` |

Both reported F09/N-01 immediate parents are correct. The pre-second-pass snapshot does not predate every first-pass repair and must not be used indiscriminately.

Both trackers independently count 18 claimed VERIFIED, 2 RESOLVED-BY-GLOBAL-GUARD, 1 FORK-HARDENING, and 9 unresolved (3 DEFERRED-NOT-BUILT, 1 NOT-REPRODUCED-HERE, 1 SPEC-INTERPRETATION-PENDING, 4 NEEDS-FIX). These are verified **inventory counts**, not independently verified repairs. The nine unresolved IDs are F01, N-03, N-05, N-07, N-08, N-10, N-11, NOVEL-03, and R-1.

Three commits follow the historical snapshot. All C++ implementation files and the existing REV-related regression scripts are unchanged between historical and current. Documentation changed; pin-check.sh changed; regression-docs.sh and run-all-checks.sh were added. No historical numerical pin-script result may silently be carried over to the changed current script. Exact changed-path lists and documentation diffs are preserved.

Repository operating guidance was also read in full: audits/README.md and audits/BUG-REPAIR-GUIDE.md. Historical records must remain unmodified. This findings-only audit does not follow the guide's repair/commit/upstream-contact steps; the user's narrower authorization governs.

Evidence: `logs/002-baselines-inventory-evidence.{stdout,stderr,result.json}`, `baseline-map.json`, `BASELINES.md`, `tracker-inventory.json`, `snapshots/`, `historical-current-*.names`, `historical-current-documentation.diff`, `historical-current-history.txt`. Probe 002 exited 0 in 1.632 seconds with no timeout/interruption.

## Prior review verdicts

All seven REV findings now have fresh verdicts. The delivered summary is PRIORITY-1-CHECKPOINT.md; detailed evidence is in the per-finding reports and inventory. Known issue #242 remains a known issue, not a new ASTRA finding. Priority-2/3 coverage is still pending and separately approval-gated.

Probe 005 read and compared the historical/current document evidence, checked recorded-current bytes against the user files, preserved the actual F09/N-01 repair diffs, and independently computed the rates using Decimal arithmetic. Exit 0; 0.132 seconds; no timeout/interruption. Evidence and precise numbered passages: REV-001-REV-007.md, documentation-evidence.json, and logs/005-rev001-rev007-documentation.*.

Documentation checkpoint 002 was saved by probe 006: 60 frozen files verified; SHA256SUMS SHA-256 `17b51a67f72ce0fede1fba1ee05816cec1e59a76c6822d2b1fef3be3b2d92e07`. Exit 0, 0.132 seconds, no timeout/interruption.

## Initial checkpoint delivery

Probe 003 saved `checkpoints/001-initial-inventory`: 43 frozen files, every copy SHA-256-verified, with all 54 finding IDs validated as unique and complete. SHA-256 of its SHA256SUMS file: `e04583c157e480e8a7dd91d56b4eb64c7e532027111b028653cff8ceaf50ee58`. Exit 0, 0.073 seconds, no timeout/interruption. Completion metadata is outside the frozen checkpoint because checkpoint creation was in progress at its capture time.

The seven REV retests plus known #242 were explicitly approved in the user's question response after delivery of the initial checkpoint. The approved estimate is 30–60 minutes, one CPU-heavy probe at a time, at most two OpenMP threads, and approximately 2–4 GB of disposable storage. No single probe exceeds 290 seconds. Detached builds, parent/child comparisons, regression-sensitivity mutations, and labeled hash fault injection will add behavioral evidence. Availability of a Linux/GCC runtime is not yet established. No agents were proposed or approved. Priority-2/3 expansion remains separately gated and must follow delivery of the seven REV verdicts.

## Limitations and teaching-lab suitability

Positive-repair, reference-corpus, and numerical-pin evidence is now complete for the tested IDs (see Priority-2 summary above and POSITIVE-REPAIRS.md); it is scoped to the fixtures, platforms, and mutations actually exercised, not a universal compatibility or production-security conclusion. The nine originally-unresolved IDs and the checkpoint-6/candidate-25.bin material remain outside this review's scope. With those limits stated, the repository is suitable as a labeled diagnostic/teaching artifact. See PRIORITY-1-CHECKPOINT.md and POSITIVE-REPAIRS.md.

## Build/runtime probe ledger

| Probe | Snapshot/platform | Observation | Qualification |
|---|---|---|---|
| 007 | Historical, macOS arm64 Apple clang 21 | Unmodified `make non_iid` exits 0 in 1.730 s; 13 compile warnings plus ignored optimization-flag warning recorded in full stderr | No compiler adapter/pre-include; OMP_NUM_THREADS=2 only. Native success does not refute prior Linux/GCC failure. No assessment run yet. |
| 008 | Recorded current, same native platform | Unmodified `make non_iid` exits 0 in 1.203 s; warnings retained | Separate current build, no adapter/pre-include; GCC verdict still pending. |
| 009 | Existing local Docker engine | Available images enumerated; no Ubuntu 24.04 image currently present. Exit 0, 0.444 s | No container started/changed. An official amd64 Ubuntu image will be fetched for isolated GCC 13/glibc testing; successful emulated execution must be established before claiming that platform coverage. |
| 010 | Official Ubuntu 24.04 requested linux/amd64 | Pull succeeds, exit 0, 4.310 s; digest sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3 | Image fetch only; execution not yet verified; no reviewed sources uploaded. |

Review-tooling failure before attempted probe 011: an editor operation reported success but its runner option and new dependency recipe were not present on subsequent filesystem reads. The first invocation failed at argument parsing (`--next-check` unrecognized); **no Docker build or reviewed-code probe ran**. The observed error is saved in logs/011a-harness-setup.stderr and .result.json. Duration/process exit were not returned by that terminal invocation and are not invented. The external parent directory was created explicitly, edits reapplied, and both files read back successfully before retry. This is a harness/persistence limitation, not a reviewed-program defect.
### Execution record 011-isolated-linux-dependencies

- Snapshot: diagnostic environment for 34fb906196f8d47da774c88928eff0d8ec08d618; no reviewed sources in build context
- Intended assertion: Build isolated amd64 GCC 13 with declared dependencies from pinned Ubuntu; preserve infrastructure failures separately from reviewed-source failures.
- Observed process exit: 125; duration: 0.038 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/011-isolated-linux-dependencies.stdout, logs/011-isolated-linux-dependencies.stderr, logs/011-isolated-linux-dependencies.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 012-isolated-linux-dependencies-legacy

- Snapshot: diagnostic environment for 34fb906196f8d47da774c88928eff0d8ec08d618; no reviewed sources in build context
- Intended assertion: Retry dependency installation without unsupported Docker --progress flag; no source/compiler semantics changed; record actual emulation and package results.
- Observed process exit: 0; duration: 56.230 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/012-isolated-linux-dependencies-legacy.stdout, logs/012-isolated-linux-dependencies-legacy.stderr, logs/012-isolated-linux-dependencies-legacy.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 013-linux-snapshot-copies

- Snapshot: historical/current plus actual F19 F09 N-06 baselines; see linux-sources.json
- Intended assertion: Create new disposable copies from exact Git archives and record image architecture/digest; user checkout remains read-only.
- Observed process exit: 0; duration: 0.989 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/013-linux-snapshot-copies.stdout, logs/013-linux-snapshot-copies.stderr, logs/013-linux-snapshot-copies.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 014-linux-compiler-arithmetic

- Snapshot: Linux image sha256:988c78ea80c9ef1a1292f6b42dd8fdad2d058c2d723a01d5e700b79541dcf957
- Intended assertion: Establish actual GCC version, glibc/libraries, sizeof(long double), significand bits, and two-thread cap under linux/amd64 emulation; no assumption of native x86 hardware.
- Observed process exit: 0; duration: 1.241 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/014-linux-compiler-arithmetic.stdout, logs/014-linux-compiler-arithmetic.stderr, logs/014-linux-compiler-arithmetic.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 015-gcc-historical-unmodified

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Ordinary make non_iid under GCC 13.3 with dependencies present, no pre-include or source adapter; establish whether F19 introduced ULONG_MAX failure.
- Observed process exit: 2; duration: 2.685 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/015-gcc-historical-unmodified.stdout, logs/015-gcc-historical-unmodified.stderr, logs/015-gcc-historical-unmodified.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 016-gcc-current-unmodified

- Snapshot: 328ec20c146e43b4eed86424847a106539c70a5a
- Intended assertion: Ordinary make non_iid under GCC 13.3 with dependencies present, no pre-include or source adapter; establish whether F19 introduced ULONG_MAX failure.
- Observed process exit: 2; duration: 2.424 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/016-gcc-current-unmodified.stdout, logs/016-gcc-current-unmodified.stderr, logs/016-gcc-current-unmodified.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 017-gcc-f19-parent-unmodified

- Snapshot: 21b0a31545be5d4ae7966fcb2917c6e1cd4b48a2
- Intended assertion: Ordinary make non_iid under GCC 13.3 with dependencies present, no pre-include or source adapter; establish whether F19 introduced ULONG_MAX failure.
- Observed process exit: 0; duration: 10.605 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/017-gcc-f19-parent-unmodified.stdout, logs/017-gcc-f19-parent-unmodified.stderr, logs/017-gcc-f19-parent-unmodified.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 018-gcc-f19-child-unmodified

- Snapshot: 0e1ffcd518f9e06d06603186039955df89094a74
- Intended assertion: Ordinary make non_iid under GCC 13.3 with dependencies present, no pre-include or source adapter; establish whether F19 introduced ULONG_MAX failure.
- Observed process exit: 2; duration: 2.694 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/018-gcc-f19-child-unmodified.stdout, logs/018-gcc-f19-child-unmodified.stderr, logs/018-gcc-f19-child-unmodified.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 019-native-guard-suite-unmodified

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run the entire unchanged estimator-guards regression on its native macOS/Homebrew environment with Bash trace preserving internal captured outputs; do not weaken exact comparisons or suppress sanitizers.
- Observed process exit: 0; duration: 3.126 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/019-native-guard-suite-unmodified.stdout, logs/019-native-guard-suite-unmodified.stderr, logs/019-native-guard-suite-unmodified.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 020-linux-guard-suite-unmodified

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Attempt the entire unchanged guard script in GCC Linux before adaptations; distinguish hard-coded compiler/Homebrew assumptions from numerical or estimator failure.
- Observed process exit: 2; duration: 0.280 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/020-linux-guard-suite-unmodified.stdout, logs/020-linux-guard-suite-unmodified.stderr, logs/020-linux-guard-suite-unmodified.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 021-prepare-compiler-capture-adapters

- Snapshot: diagnostic wrappers only; historical source unchanged
- Intended assertion: Mark reviewed adapter/capture scripts executable and record their hashes; do not edit regression assertions or reviewed source.
- Observed process exit: 0; duration: 0.077 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/021-prepare-compiler-capture-adapters.stdout, logs/021-prepare-compiler-capture-adapters.stderr, logs/021-prepare-compiler-capture-adapters.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 022-linux-guard-suite-gcc-adapter

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run the complete unchanged guard assertions with disclosed clang-to-GCC/Homebrew flag adapter and -include climits; retain default sanitizer behavior, exact F14 comparison, captured fixtures and actual build diagnostics.
- Observed process exit: 1; duration: 98.108 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/022-linux-guard-suite-gcc-adapter.stdout, logs/022-linux-guard-suite-gcc-adapter.stderr, logs/022-linux-guard-suite-gcc-adapter.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 023-gcc-historical-functional-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Build functional diagnostic executables after original GCC failure: the ONLY addition is command-line -include climits; source/optimization/OpenMP semantics unchanged. This is not an unmodified-build pass.
- Observed process exit: 0; duration: 63.512 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/023-gcc-historical-functional-build.stdout, logs/023-gcc-historical-functional-build.stderr, logs/023-gcc-historical-functional-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 024-gcc-current-functional-build

- Snapshot: 328ec20c146e43b4eed86424847a106539c70a5a
- Intended assertion: Build functional diagnostic executables after original GCC failure: the ONLY addition is command-line -include climits; source/optimization/OpenMP semantics unchanged. This is not an unmodified-build pass.
- Observed process exit: 0; duration: 15.923 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/024-gcc-current-functional-build.stdout, logs/024-gcc-current-functional-build.stderr, logs/024-gcc-current-functional-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 025-gcc-f09-parent-functional-build

- Snapshot: 6b60f9d3adc37b245bef03175ffe8e7eec8afe5b
- Intended assertion: Build functional diagnostic executables after original GCC failure: the ONLY addition is command-line -include climits; source/optimization/OpenMP semantics unchanged. This is not an unmodified-build pass.
- Observed process exit: 0; duration: 18.781 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/025-gcc-f09-parent-functional-build.stdout, logs/025-gcc-f09-parent-functional-build.stderr, logs/025-gcc-f09-parent-functional-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 026-gcc-hash-parent-functional-build

- Snapshot: d892b909fd8df0a8019a777b2cc9965ec9667d95
- Intended assertion: Build functional diagnostic executables after original GCC failure: the ONLY addition is command-line -include climits; source/optimization/OpenMP semantics unchanged. This is not an unmodified-build pass.
- Observed process exit: 0; duration: 23.067 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/026-gcc-hash-parent-functional-build.stdout, logs/026-gcc-hash-parent-functional-build.stderr, logs/026-gcc-hash-parent-functional-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 027-linux-asan-infrastructure

- Snapshot: sanitizer control, no reviewed estimator code
- Intended assertion: Determine whether GCC ASan can run even a trivial correct program under the 3GiB emulated container; record memory-event counters and default versus detect_leaks=0 separately.
- Observed process exit: 0; duration: 7.855 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/027-linux-asan-infrastructure.stdout, logs/027-linux-asan-infrastructure.stderr, logs/027-linux-asan-infrastructure.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 028-validate-fixtures-specification

- Snapshot: fixtures from 328ec20c146e43b4eed86424847a106539c70a5a; F09 original manifest hashes
- Intended assertion: Check available generator and specification SHA-256 against recorded manifests before execution; reproduce original available F09 fixture exactly, characterize all public samples and binary/restart regression fixtures, and extract spec text.
- Observed process exit: 0; duration: 2.316 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/028-validate-fixtures-specification.stdout, logs/028-validate-fixtures-specification.stderr, logs/028-validate-fixtures-specification.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 029-gcc-complete-ringosc-output

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compute every estimator and final value on validated ringOsc fixture with GCC 13.3 functional build; compare literal compression to guard exact string without weakening it. This is NOT a full sanitizer-suite pass.
- Observed process exit: 0; duration: 6.686 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/029-gcc-complete-ringosc-output.stdout, logs/029-gcc-complete-ringosc-output.stderr, logs/029-gcc-complete-ringosc-output.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 030-portability-evidence-analysis

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compare computed GCC compression output to the unchanged exact string, record native long-double characteristics, and locate specification section 6.3.9 for independent MultiMMC derivation.
- Observed process exit: 0; duration: 0.603 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/030-portability-evidence-analysis.stdout, logs/030-portability-evidence-analysis.stderr, logs/030-portability-evidence-analysis.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 031-portability-checkpoint

- Snapshot: historical/current and exact F19 parents as recorded
- Intended assertion: Freeze REV-002 and REV-005 completed findings with all build/guard logs, fixture manifests, adapter source and explicit sanitizer environmental exclusions.
- Observed process exit: 0; duration: 0.336 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/031-portability-checkpoint.stdout, logs/031-portability-checkpoint.stderr, logs/031-portability-checkpoint.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 032-mmc-independent-binary-reference

- Snapshot: independent PDF-derived reference, no fork implementation copied
- Intended assertion: Validate literal specification worked example then compute every prediction, winner, scoreboard, correct/run state for the exact 200000-sample binary regression fixture. Expected r is NOT supplied to the reference.
- Observed process exit: 0; duration: 1.880 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/032-mmc-independent-binary-reference.stdout, logs/032-mmc-independent-binary-reference.stderr, logs/032-mmc-independent-binary-reference.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 033-mmc-disposable-copies

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Prepare fresh distinct copies for binary mutation, generic mutation, and trace instrumentation; no user source or regression changes.
- Observed process exit: 0; duration: 0.441 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/033-mmc-disposable-copies.stdout, logs/033-mmc-disposable-copies.stderr, logs/033-mmc-disposable-copies.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 033b-validate-mmc-harness-syntax

- Snapshot: review tooling only
- Intended assertion: Validate actual Python syntax after the pre-execution harness indentation error; no behavioral claim follows from compilation of review tooling.
- Observed process exit: 1; duration: 0.038 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/033b-validate-mmc-harness-syntax.stdout, logs/033b-validate-mmc-harness-syntax.stderr, logs/033b-validate-mmc-harness-syntax.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 033c-validate-mmc-harness-syntax

- Snapshot: review tooling only
- Intended assertion: Validate actual Python syntax after replacing the faulty final loop; prior syntax failures are harness errors, not target/mutant observations.
- Observed process exit: 0; duration: 0.037 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/033c-validate-mmc-harness-syntax.stdout, logs/033c-validate-mmc-harness-syntax.stderr, logs/033c-validate-mmc-harness-syntax.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 034-mmc-binary-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile the identified meaningful mutant with ordinary native flags. Compilation failure is NOT mutation sensitivity.
- Observed process exit: 0; duration: 1.297 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/034-mmc-binary-mutant-build.stdout, logs/034-mmc-binary-mutant-build.stderr, logs/034-mmc-binary-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 035-mmc-generic-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile the identified meaningful mutant with ordinary native flags. Compilation failure is NOT mutation sensitivity.
- Observed process exit: 0; duration: 0.869 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/035-mmc-generic-mutant-build.stdout, logs/035-mmc-generic-mutant-build.stderr, logs/035-mmc-generic-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 036-mmc-instrumented-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile observation-only trace hooks and diagnostic generic dispatch; preserve all estimator math/count logic.
- Observed process exit: 0; duration: 0.492 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/036-mmc-instrumented-build.stdout, logs/036-mmc-instrumented-build.stderr, logs/036-mmc-instrumented-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 037-mmc-regression-fixed

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Execute the ENTIRE unchanged original MultiMMC regression against fixed; capture scratch fixtures before its original cleanup. No assertion or fixture replacement.
- Observed process exit: 0; duration: 7.771 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/037-mmc-regression-fixed.stdout, logs/037-mmc-regression-fixed.stderr, logs/037-mmc-regression-fixed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 038-mmc-regression-binary-mutant

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Execute the ENTIRE unchanged original MultiMMC regression against binary-mutant; capture scratch fixtures before its original cleanup. No assertion or fixture replacement.
- Observed process exit: 0; duration: 7.570 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/038-mmc-regression-binary-mutant.stdout, logs/038-mmc-regression-binary-mutant.stderr, logs/038-mmc-regression-binary-mutant.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 039-mmc-regression-generic-mutant

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Execute the ENTIRE unchanged original MultiMMC regression against generic-mutant; capture scratch fixtures before its original cleanup. No assertion or fixture replacement.
- Observed process exit: 1; duration: 7.509 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/039-mmc-regression-generic-mutant.stdout, logs/039-mmc-regression-generic-mutant.stderr, logs/039-mmc-regression-generic-mutant.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 040-mmc-trace-binary

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe every prediction, winner, scoreboard and run state on the identical validated binary fixture; compare to independently derived reference, not to another fork output.
- Observed process exit: 0; duration: 0.549 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/040-mmc-trace-binary.stdout, logs/040-mmc-trace-binary.stderr, logs/040-mmc-trace-binary.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 041-mmc-trace-forced-generic

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe every prediction, winner, scoreboard and run state on the identical validated binary fixture; compare to independently derived reference, not to another fork output.
- Observed process exit: 0; duration: 0.774 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/041-mmc-trace-forced-generic.stdout, logs/041-mmc-trace-forced-generic.stderr, logs/041-mmc-trace-forced-generic.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 042-mmc-independent-generic-reference

- Snapshot: independent specification implementation; original available F09 fixture
- Intended assertion: Compute generic F09 counts/run directly from literal specification with dictionary cap 100000 and no expected count/run supplied; retain full prediction/scoreboard traces.
- Observed process exit: 0; duration: 1.530 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/042-mmc-independent-generic-reference.stdout, logs/042-mmc-independent-generic-reference.stderr, logs/042-mmc-independent-generic-reference.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 043-mmc-target-generic-trace

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618 observation-only instrumented copy
- Intended assertion: Record actual generic predictions and run states on the exact original F09 fixture without changing dictionary limits, winning logic, or arithmetic.
- Observed process exit: 0; duration: 0.983 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/043-mmc-target-generic-trace.stdout, logs/043-mmc-target-generic-trace.stderr, logs/043-mmc-target-generic-trace.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 044-mmc-complete-trace-comparison

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618 target, independent spec reference, diagnostic mutants
- Intended assertion: Compare every prediction, scoreboard, winner and run field for binary/forced-generic and original F09 data; validate regression scripts are byte-identical and captured generated fixtures match the reference inputs.
- Observed process exit: 0; duration: 0.239 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/044-mmc-complete-trace-comparison.stdout, logs/044-mmc-complete-trace-comparison.stderr, logs/044-mmc-complete-trace-comparison.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 045-mmc-checkpoint

- Snapshot: historical=34fb906196f8d47da774c88928eff0d8ec08d618 current=328ec20c146e43b4eed86424847a106539c70a5a
- Intended assertion: Freeze completed REV-003 evidence including full intermediate traces, unchanged regression/fixture hashes and meaningful compiling mutant diffs.
- Observed process exit: 0; duration: 0.505 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/045-mmc-checkpoint.stdout, logs/045-mmc-checkpoint.stderr, logs/045-mmc-checkpoint.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 046-linux-restart-original-gnu

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Execute the complete unchanged restart regression under default GNU getopt with the disclosed header-only GCC build; capture exact -inf/-1 diagnostics and all subsequent coverage. A 290-second timeout is incomplete, not a suite pass.
- Observed process exit: -9; duration: 289.079 s; timeout: True; interruption: False; harness: None.
- Complete evidence: logs/046-linux-restart-original-gnu.stdout, logs/046-linux-restart-original-gnu.stderr, logs/046-linux-restart-original-gnu.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 047-linux-restart-original-posix

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Execute the complete unchanged restart regression with POSIXLY_CORRECT=1, keeping all original simulation/assessment coverage and comparing parser diagnostics; any timeout remains incomplete evidence.
- Observed process exit: -9; duration: 289.094 s; timeout: True; interruption: False; harness: None.
- Complete evidence: logs/047-linux-restart-original-posix.stdout, logs/047-linux-restart-original-posix.stderr, logs/047-linux-restart-original-posix.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 048-restart-parser-paths

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Complete the exact bounded -inf/-1 cases in both GNU/default and POSIX configurations and prove all refuse while parser paths differ; do not apply partial results to timed-out full-suite coverage.
- Observed process exit: 0; duration: 0.644 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/048-restart-parser-paths.stdout, logs/048-restart-parser-paths.stderr, logs/048-restart-parser-paths.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 049-prepare-hash-regression-copies

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Create separate disposable ignored-status mutation targets and extract the ORIGINAL N-06 absent-file checks verbatim, since full original suites have been attempted and timed out before reaching that section.
- Observed process exit: 0; duration: 0.422 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/049-prepare-hash-regression-copies.stdout, logs/049-prepare-hash-regression-copies.stderr, logs/049-prepare-hash-regression-copies.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 050-hash-mutant-iid-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile one ignored-hash-status mutant; function must still be called and compile must succeed before behavioral sensitivity can be asserted.
- Observed process exit: 0; duration: 14.740 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/050-hash-mutant-iid-build.stdout, logs/050-hash-mutant-iid-build.stderr, logs/050-hash-mutant-iid-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 051-hash-mutant-non_iid-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile one ignored-hash-status mutant; function must still be called and compile must succeed before behavioral sensitivity can be asserted.
- Observed process exit: 0; duration: 12.722 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/051-hash-mutant-non_iid-build.stdout, logs/051-hash-mutant-non_iid-build.stderr, logs/051-hash-mutant-non_iid-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 052-hash-mutant-restart-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile one ignored-hash-status mutant; function must still be called and compile must succeed before behavioral sensitivity can be asserted.
- Observed process exit: 0; duration: 15.825 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/052-hash-mutant-restart-build.stdout, logs/052-hash-mutant-restart-build.stderr, logs/052-hash-mutant-restart-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 053-hash-shim-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Build explicit EVP_DigestInit_ex fault injection with a proof marker and a pass-through control; no reviewed source altered.
- Observed process exit: 0; duration: 0.763 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/053-hash-shim-build.stdout, logs/053-hash-shim-build.stderr, logs/053-hash-shim-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 054-original-n06-fixed

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run original absent-file N-06 assertions verbatim for both -i and -n; this is section-only after full-suite timeout, not a full restart-suite pass.
- Observed process exit: 0; duration: 0.572 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/054-original-n06-fixed.stdout, logs/054-original-n06-fixed.stderr, logs/054-original-n06-fixed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 055-original-n06-immediate-parent

- Snapshot: d892b909fd8df0a8019a777b2cc9965ec9667d95
- Intended assertion: Run original absent-file N-06 assertions verbatim for both -i and -n; this is section-only after full-suite timeout, not a full restart-suite pass.
- Observed process exit: 2; duration: 0.516 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/055-original-n06-immediate-parent.stdout, logs/055-original-n06-immediate-parent.stderr, logs/055-original-n06-immediate-parent.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 056-original-n06-ignored-status-mutant

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run original absent-file N-06 assertions verbatim for both -i and -n; this is section-only after full-suite timeout, not a full restart-suite pass.
- Observed process exit: 0; duration: 0.591 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/056-original-n06-ignored-status-mutant.stdout, logs/056-original-n06-ignored-status-mutant.stderr, logs/056-original-n06-ignored-status-mutant.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 057-original-nonregular-fixed

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run the ENTIRE unchanged nonregular regression. The IID-only mutant's ea_non_iid remains byte-identical to fixed; determine whether ea_iid is executed at all.
- Observed process exit: 0; duration: 4.341 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/057-original-nonregular-fixed.stdout, logs/057-original-nonregular-fixed.stderr, logs/057-original-nonregular-fixed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 058-original-nonregular-iid-mutant

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run the ENTIRE unchanged nonregular regression. The IID-only mutant's ea_non_iid remains byte-identical to fixed; determine whether ea_iid is executed at all.
- Observed process exit: 0; duration: 4.221 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/058-original-nonregular-iid-mutant.stdout, logs/058-original-nonregular-iid-mutant.stderr, logs/058-original-nonregular-iid-mutant.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 059-hash-control-non_iid

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. control non_iid: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 0; duration: 22.432 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/059-hash-control-non_iid.stdout, logs/059-hash-control-non_iid.stderr, logs/059-hash-control-non_iid.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 060-hash-control-iid

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. control iid: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 0; duration: 96.731 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/060-hash-control-iid.stdout, logs/060-hash-control-iid.stderr, logs/060-hash-control-iid.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 061-hash-control-restart

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. control restart: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 0; duration: 111.477 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/061-hash-control-restart.stdout, logs/061-hash-control-restart.stderr, logs/061-hash-control-restart.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 062-hash-injected-fixed-non_iid

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. injected-fixed non_iid: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 255; duration: 0.132 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/062-hash-injected-fixed-non_iid.stdout, logs/062-hash-injected-fixed-non_iid.stderr, logs/062-hash-injected-fixed-non_iid.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 063-hash-injected-fixed-iid

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. injected-fixed iid: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 255; duration: 0.122 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/063-hash-injected-fixed-iid.stdout, logs/063-hash-injected-fixed-iid.stderr, logs/063-hash-injected-fixed-iid.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 064-hash-injected-fixed-restart

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. injected-fixed restart: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 255; duration: 0.174 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/064-hash-injected-fixed-restart.stdout, logs/064-hash-injected-fixed-restart.stderr, logs/064-hash-injected-fixed-restart.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 065-hash-injected-mutant-non_iid

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. injected-mutant non_iid: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 0; duration: 20.973 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/065-hash-injected-mutant-non_iid.stdout, logs/065-hash-injected-mutant-non_iid.stderr, logs/065-hash-injected-mutant-non_iid.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 066-hash-injected-mutant-iid

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. injected-mutant iid: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 0; duration: 63.891 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/066-hash-injected-mutant-iid.stdout, logs/066-hash-injected-mutant-iid.stderr, logs/066-hash-injected-mutant-iid.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 067-hash-injected-mutant-restart

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. injected-mutant restart: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 0; duration: 111.080 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/067-hash-injected-mutant-restart.stdout, logs/067-hash-injected-mutant-restart.stderr, logs/067-hash-injected-mutant-restart.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 068-hash-injected-parent-restart

- Snapshot: d892b909fd8df0a8019a777b2cc9965ec9667d95
- Intended assertion: ARTIFICIAL digest-initialization failure on validated readable PUBLIC file, with pass-through positive controls. injected-parent restart: verify proof marker, exit, JSON error/hash/testCases, and complete assessment or early refusal. No simulation/coverage reductions.
- Observed process exit: 0; duration: 110.895 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/068-hash-injected-parent-restart.stdout, logs/068-hash-injected-parent-restart.stderr, logs/068-hash-injected-parent-restart.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 069-hash-outcomes-analysis

- Snapshot: historical target, actual restart hash parent, isolated ignored-status mutants
- Intended assertion: Assert injected failure actually occurred, all fixed tools reject with errorLevel=-1/no hash/no assessment, controls assess with correct hash, and all mutants/parent continue; prove relevant current source identities.
- Observed process exit: 1; duration: 0.076 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/069-hash-outcomes-analysis.stdout, logs/069-hash-outcomes-analysis.stderr, logs/069-hash-outcomes-analysis.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 069b-hash-outcomes-analysis

- Snapshot: historical target, actual restart hash parent, ignored-status mutants
- Intended assertion: Evaluate unchanged assertions over actual injection results; tolerate non-UTF8 display from parent uninitialized hash while preserving raw logs byte-for-byte. First analysis failed decoding, not target behavior.
- Observed process exit: 0; duration: 0.076 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/069b-hash-outcomes-analysis.stdout, logs/069b-hash-outcomes-analysis.stderr, logs/069b-hash-outcomes-analysis.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 070-native-restart-direct-asan-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Build native ASan/UBSan restart source without changing allocation/deallocation, simulation constants or assessment semantics. Direct harness is a separate bounded function-call test.
- Observed process exit: 0; duration: 2.867 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/070-native-restart-direct-asan-build.stdout, logs/070-native-restart-direct-asan-build.stderr, logs/070-native-restart-direct-asan-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 071-native-restart-full-asan-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Build native ASan/UBSan restart source without changing allocation/deallocation, simulation constants or assessment semantics. Direct harness is a separate bounded function-call test.
- Observed process exit: 0; duration: 2.439 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/071-native-restart-full-asan-build.stdout, logs/071-native-restart-full-asan-build.stderr, logs/071-native-restart-full-asan-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 072-known242-native-default-direct

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618 unchanged simulateBound, direct diagnostic harness
- Intended assertion: Observe default native ASan/UBSan behavior for the existing new[]/scalar delete mismatch in unchanged simulateBound; 64-round direct function test is not a full restart assessment or statistical validation.
- Observed process exit: 0; duration: 0.340 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/072-known242-native-default-direct.stdout, logs/072-known242-native-default-direct.stderr, logs/072-known242-native-default-direct.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 073-known242-native-enabled-direct

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618 unchanged simulateBound direct harness
- Intended assertion: Enable alloc_dealloc_mismatch explicitly after default macOS run did not diagnose it; prove exact new[]/scalar delete mismatch, not unrelated crash or harness failure.
- Observed process exit: -6; duration: 0.235 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/073-known242-native-enabled-direct.stdout, logs/073-known242-native-enabled-direct.stderr, logs/073-known242-native-enabled-direct.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 074-known242-native-full-default

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run full unchanged restart CLI with original 5000000 simulation rounds and default native ASan/UBSan settings; no leak or mismatch suppression configured. A default non-diagnostic run does not erase known #242.
- Observed process exit: 0; duration: 29.209 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/074-known242-native-full-default.stdout, logs/074-known242-native-full-default.stderr, logs/074-known242-native-full-default.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 075-known242-native-full-enabled

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Same full CLI and original 5000000 rounds, enabling only ASAN alloc_dealloc_mismatch=1; prove known mismatch on normal valid-input path without source modifications or reduced simulation coverage.
- Observed process exit: -6; duration: 13.291 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/075-known242-native-full-enabled.stdout, logs/075-known242-native-full-enabled.stderr, logs/075-known242-native-full-enabled.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 076-preservation-after-rev

- Snapshot: 328ec20c146e43b4eed86424847a106539c70a5a
- Intended assertion: Verify original working tree/index/branch state still matches capture and no review executable/container is running before delivering the seven-REV checkpoint.
- Observed process exit: 0; duration: 0.186 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/076-preservation-after-rev.stdout, logs/076-preservation-after-rev.stderr, logs/076-preservation-after-rev.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 077-seven-rev-verdict-checkpoint

- Snapshot: historical=34fb906196f8d47da774c88928eff0d8ec08d618 current=328ec20c146e43b4eed86424847a106539c70a5a
- Intended assertion: Freeze and checksum all completed seven-REV findings, known242 result, full logs/reference/mutations, original inventory and exact baseline map before requesting broader audit approval.
- Observed process exit: 0; duration: 0.710 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/077-seven-rev-verdict-checkpoint.stdout, logs/077-seven-rev-verdict-checkpoint.stderr, logs/077-seven-rev-verdict-checkpoint.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 078-p2-exact-parent-copies

- Snapshot: exact repair parents from baseline-map.json; mutation bases historical34fb906
- Intended assertion: Prepare actual immediate-parent snapshots and isolated mutation copies for each Priority-2 repair, never using one pre-pass snapshot for every repair.
- Observed process exit: 0; duration: 3.489 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/078-p2-exact-parent-copies.stdout, logs/078-p2-exact-parent-copies.stderr, logs/078-p2-exact-parent-copies.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 079-spec-errata-download

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Fetch official errata as evidence and preserve source URL/hash; no repository source fetched from browser snippets.
- Observed process exit: 0; duration: 0.667 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/079-spec-errata-download.stdout, logs/079-spec-errata-download.stderr, logs/079-spec-errata-download.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 080-native-target-tools

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Ordinary native build, no pre-includes; mutant only alters binding collision return, not pin script.
- Observed process exit: 0; duration: 2.794 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/080-native-target-tools.stdout, logs/080-native-target-tools.stderr, logs/080-native-target-tools.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 081-native-f09-parent-build

- Snapshot: 6b60f9d3adc37b245bef03175ffe8e7eec8afe5b
- Intended assertion: Ordinary native build, no pre-includes; mutant only alters binding collision return, not pin script.
- Observed process exit: 0; duration: 0.938 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/081-native-f09-parent-build.stdout, logs/081-native-f09-parent-build.stderr, logs/081-native-f09-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 082-pin-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Ordinary native build, no pre-includes; mutant only alters binding collision return, not pin script.
- Observed process exit: 0; duration: 0.919 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/082-pin-mutant-build.stdout, logs/082-pin-mutant-build.stderr, logs/082-pin-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 083-f09-full-fixed

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compute COMPLETE original F09 output and binding final minimum on actual fixed; short-data escape is explicit for original114146-sample diagnostic fixture.
- Observed process exit: 0; duration: 1.205 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/083-f09-full-fixed.stdout, logs/083-f09-full-fixed.stderr, logs/083-f09-full-fixed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 084-f09-full-parent

- Snapshot: 6b60f9d3adc37b245bef03175ffe8e7eec8afe5b
- Intended assertion: Compute COMPLETE original F09 output and binding final minimum on actual parent; short-data escape is explicit for original114146-sample diagnostic fixture.
- Observed process exit: 0; duration: 1.566 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/084-f09-full-parent.stdout, logs/084-f09-full-parent.stderr, logs/084-f09-full-parent.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 085-corpus-native-fixed

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run every one of11 original corpus files under the unchanged selftest and tolerance; preserve all verbose per-file outputs; a known platform delta remains a failure.
- Observed process exit: 1; duration: 23.470 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/085-corpus-native-fixed.stdout, logs/085-corpus-native-fixed.stderr, logs/085-corpus-native-fixed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 086-corpus-native-parent

- Snapshot: 6b60f9d3adc37b245bef03175ffe8e7eec8afe5b
- Intended assertion: Run every one of11 original corpus files under the unchanged selftest and tolerance; preserve all verbose per-file outputs; a known platform delta remains a failure.
- Observed process exit: 1; duration: 20.913 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/086-corpus-native-parent.stdout, logs/086-corpus-native-parent.stderr, logs/086-corpus-native-parent.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 087-corpus-gcc-fixed

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run complete11-file unchanged selftest under GCC13.3 emulated x86 with disclosed header pre-include; no tolerance/fixture changes. Timeout not pass.
- Observed process exit: 0; duration: 94.952 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/087-corpus-gcc-fixed.stdout, logs/087-corpus-gcc-fixed.stderr, logs/087-corpus-gcc-fixed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 088-corpus-gcc-parent

- Snapshot: 6b60f9d3adc37b245bef03175ffe8e7eec8afe5b
- Intended assertion: Run complete11-file unchanged selftest under GCC13.3 emulated x86 with disclosed header pre-include; no tolerance/fixture changes. Timeout not pass.
- Observed process exit: 0; duration: 107.382 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/088-corpus-gcc-parent.stdout, logs/088-corpus-gcc-parent.stderr, logs/088-corpus-gcc-parent.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 089-pin-historical

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run actual pin script including its64-byte perturbation; the source-level binding-result mutant must be rejected without adjusting the expected value/tolerance.
- Observed process exit: 0; duration: 0.456 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/089-pin-historical.stdout, logs/089-pin-historical.stderr, logs/089-pin-historical.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 090-pin-current

- Snapshot: 328ec20c146e43b4eed86424847a106539c70a5a
- Intended assertion: Run actual pin script including its64-byte perturbation; the source-level binding-result mutant must be rejected without adjusting the expected value/tolerance.
- Observed process exit: 0; duration: 0.691 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/090-pin-current.stdout, logs/090-pin-current.stderr, logs/090-pin-current.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 091-pin-changed-binding-result

- Snapshot: 328ec20c146e43b4eed86424847a106539c70a5a
- Intended assertion: Run actual pin script including its64-byte perturbation; the source-level binding-result mutant must be rejected without adjusting the expected value/tolerance.
- Observed process exit: 1; duration: 0.593 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/091-pin-changed-binding-result.stdout, logs/091-pin-changed-binding-result.stderr, logs/091-pin-changed-binding-result.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 092-corpus-f09-analysis

- Snapshot: historical34fb906 and actual F09 parent6b60f9d
- Intended assertion: Compare every complete verbose corpus output parent/fixed per platform, and derive original F09 binding final minimum from all estimator outputs; do not infer universal equivalence.
- Observed process exit: 0; duration: 0.048 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/092-corpus-f09-analysis.stdout, logs/092-corpus-f09-analysis.stderr, logs/092-corpus-f09-analysis.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f02-f02-parent-build

- Snapshot: 0e1ffcd518f9e06d06603186039955df89094a74
- Intended assertion: Compile actual f02-parent for f02 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 2.271 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f02-f02-parent-build.stdout, logs/p2-f02-f02-parent-build.stderr, logs/p2-f02-f02-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f02-f02-parent-regression

- Snapshot: 0e1ffcd518f9e06d06603186039955df89094a74
- Intended assertion: Run COMPLETE claimed regression-width.sh unchanged on f02-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 31.428 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f02-f02-parent-regression.stdout, logs/p2-f02-f02-parent-regression.stderr, logs/p2-f02-f02-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f02-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual fixed for f02 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 2.206 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f02-fixed-build.stdout, logs/p2-f02-fixed-build.stderr, logs/p2-f02-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f02-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-width.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 34.399 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f02-fixed-regression.stdout, logs/p2-f02-fixed-regression.stderr, logs/p2-f02-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f02-f02-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual f02-mutant for f02 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 2.754 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f02-f02-mutant-build.stdout, logs/p2-f02-f02-mutant-build.stderr, logs/p2-f02-f02-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f02-f02-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-width.sh unchanged on f02-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 38.495 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f02-f02-mutant-regression.stdout, logs/p2-f02-f02-mutant-regression.stderr, logs/p2-f02-f02-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f19-f19-parent-build

- Snapshot: 21b0a31545be5d4ae7966fcb2917c6e1cd4b48a2
- Intended assertion: Compile actual f19-parent for f19 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.271 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f19-f19-parent-build.stdout, logs/p2-f19-f19-parent-build.stderr, logs/p2-f19-f19-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f19-f19-parent-regression

- Snapshot: 21b0a31545be5d4ae7966fcb2917c6e1cd4b48a2
- Intended assertion: Run COMPLETE claimed regression-subset.sh unchanged on f19-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 1.275 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f19-f19-parent-regression.stdout, logs/p2-f19-f19-parent-regression.stderr, logs/p2-f19-f19-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f19-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual fixed for f19 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.044 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f19-fixed-build.stdout, logs/p2-f19-fixed-build.stderr, logs/p2-f19-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f19-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-subset.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 0.650 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f19-fixed-regression.stdout, logs/p2-f19-fixed-regression.stderr, logs/p2-f19-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f19-f19-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual f19-mutant for f19 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 0.981 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f19-f19-mutant-build.stdout, logs/p2-f19-f19-mutant-build.stderr, logs/p2-f19-f19-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f19-f19-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-subset.sh unchanged on f19-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 0.938 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f19-f19-mutant-regression.stdout, logs/p2-f19-f19-mutant-regression.stderr, logs/p2-f19-f19-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f05-f05-parent-build

- Snapshot: 69b6094b01144a0301cc941fa692dee9b060f0a6
- Intended assertion: Compile actual f05-parent for f05 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 0.986 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f05-f05-parent-build.stdout, logs/p2-f05-f05-parent-build.stderr, logs/p2-f05-f05-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f05-f05-parent-regression

- Snapshot: 69b6094b01144a0301cc941fa692dee9b060f0a6
- Intended assertion: Run COMPLETE claimed regression-notrun.sh unchanged on f05-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 17.512 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f05-f05-parent-regression.stdout, logs/p2-f05-f05-parent-regression.stderr, logs/p2-f05-f05-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f05-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual fixed for f05 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.247 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f05-fixed-build.stdout, logs/p2-f05-fixed-build.stderr, logs/p2-f05-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f05-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-notrun.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 15.801 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f05-fixed-regression.stdout, logs/p2-f05-fixed-regression.stderr, logs/p2-f05-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f05-f05-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual f05-mutant for f05 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 0.989 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f05-f05-mutant-build.stdout, logs/p2-f05-f05-mutant-build.stderr, logs/p2-f05-f05-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f05-f05-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-notrun.sh unchanged on f05-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 17.196 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f05-f05-mutant-regression.stdout, logs/p2-f05-f05-mutant-regression.stderr, logs/p2-f05-f05-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-global-global-parent-build

- Snapshot: 134d377c981af58a4dcf19c5669b73a1b64a7c35
- Intended assertion: Compile actual global-parent for global with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 2.579 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-global-global-parent-build.stdout, logs/p2-global-global-parent-build.stderr, logs/p2-global-global-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-global-global-parent-regression

- Snapshot: 134d377c981af58a4dcf19c5669b73a1b64a7c35
- Intended assertion: Run COMPLETE claimed regression-minsize.sh unchanged on global-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 1.046 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-global-global-parent-regression.stdout, logs/p2-global-global-parent-regression.stderr, logs/p2-global-global-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-global-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual fixed for global with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 2.323 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-global-fixed-build.stdout, logs/p2-global-fixed-build.stderr, logs/p2-global-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-global-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-minsize.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 0.795 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-global-fixed-regression.stdout, logs/p2-global-fixed-regression.stderr, logs/p2-global-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-global-global-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual global-mutant for global with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 2.409 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-global-global-mutant-build.stdout, logs/p2-global-global-mutant-build.stderr, logs/p2-global-global-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-global-global-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-minsize.sh unchanged on global-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 1.117 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-global-global-mutant-regression.stdout, logs/p2-global-global-mutant-regression.stderr, logs/p2-global-global-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f11-f11-parent-regression

- Snapshot: ed88de934a5dbe2ebedf34da8b42d1642ca5e7ac
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f11-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.295 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f11-f11-parent-regression.stdout, logs/p2-f11-f11-parent-regression.stderr, logs/p2-f11-f11-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f11-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.131 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f11-fixed-regression.stdout, logs/p2-f11-fixed-regression.stderr, logs/p2-f11-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f11-f11-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f11-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.087 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f11-f11-mutant-regression.stdout, logs/p2-f11-f11-mutant-regression.stderr, logs/p2-f11-f11-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f12-f12-parent-regression

- Snapshot: c0ee84af1a191b92f9679c101834f27fecbff7e5
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f12-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.139 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f12-f12-parent-regression.stdout, logs/p2-f12-f12-parent-regression.stderr, logs/p2-f12-f12-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f12-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.131 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f12-fixed-regression.stdout, logs/p2-f12-fixed-regression.stderr, logs/p2-f12-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f12-f12-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f12-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.083 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f12-f12-mutant-regression.stdout, logs/p2-f12-f12-mutant-regression.stderr, logs/p2-f12-f12-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f15-f15-parent-regression

- Snapshot: c217f20f347dd3dbb759edce1ebc0389524027a8
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f15-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.086 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f15-f15-parent-regression.stdout, logs/p2-f15-f15-parent-regression.stderr, logs/p2-f15-f15-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f15-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.140 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f15-fixed-regression.stdout, logs/p2-f15-fixed-regression.stderr, logs/p2-f15-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f15-f15-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f15-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.136 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f15-f15-mutant-regression.stdout, logs/p2-f15-f15-mutant-regression.stderr, logs/p2-f15-f15-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f16-f16-parent-regression

- Snapshot: c2f1dcd16264db2f7a1d23c1c85f14c61860b552
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f16-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.139 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f16-f16-parent-regression.stdout, logs/p2-f16-f16-parent-regression.stderr, logs/p2-f16-f16-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f16-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.145 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f16-fixed-regression.stdout, logs/p2-f16-fixed-regression.stderr, logs/p2-f16-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f16-f16-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f16-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 2; duration: 0.134 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f16-f16-mutant-regression.stdout, logs/p2-f16-f16-mutant-regression.stderr, logs/p2-f16-f16-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f11-f11-parent-native-regression

- Snapshot: ed88de934a5dbe2ebedf34da8b42d1642ca5e7ac
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f11-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 3.738 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f11-f11-parent-native-regression.stdout, logs/p2-f11-f11-parent-native-regression.stderr, logs/p2-f11-f11-parent-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f11-fixed-native-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 2.711 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f11-fixed-native-regression.stdout, logs/p2-f11-fixed-native-regression.stderr, logs/p2-f11-fixed-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f11-f11-mutant-native-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f11-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 2.707 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f11-f11-mutant-native-regression.stdout, logs/p2-f11-f11-mutant-native-regression.stderr, logs/p2-f11-f11-mutant-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f12-f12-parent-native-regression

- Snapshot: c0ee84af1a191b92f9679c101834f27fecbff7e5
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f12-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 3.355 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f12-f12-parent-native-regression.stdout, logs/p2-f12-f12-parent-native-regression.stderr, logs/p2-f12-f12-parent-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f12-fixed-native-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 2.874 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f12-fixed-native-regression.stdout, logs/p2-f12-fixed-native-regression.stderr, logs/p2-f12-fixed-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f12-f12-mutant-native-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f12-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 2.658 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f12-f12-mutant-native-regression.stdout, logs/p2-f12-f12-mutant-native-regression.stderr, logs/p2-f12-f12-mutant-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f15-f15-parent-native-regression

- Snapshot: c217f20f347dd3dbb759edce1ebc0389524027a8
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f15-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 3.258 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f15-f15-parent-native-regression.stdout, logs/p2-f15-f15-parent-native-regression.stderr, logs/p2-f15-f15-parent-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f15-fixed-native-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 2.680 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f15-fixed-native-regression.stdout, logs/p2-f15-fixed-native-regression.stderr, logs/p2-f15-fixed-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f15-f15-mutant-native-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f15-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 2.736 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f15-f15-mutant-native-regression.stdout, logs/p2-f15-f15-mutant-native-regression.stderr, logs/p2-f15-f15-mutant-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f16-f16-parent-native-regression

- Snapshot: c2f1dcd16264db2f7a1d23c1c85f14c61860b552
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f16-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 3.764 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f16-f16-parent-native-regression.stdout, logs/p2-f16-f16-parent-native-regression.stderr, logs/p2-f16-f16-parent-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f16-fixed-native-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 2.730 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f16-fixed-native-regression.stdout, logs/p2-f16-fixed-native-regression.stderr, logs/p2-f16-fixed-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-f16-f16-mutant-native-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-estimator-guards.sh unchanged on f16-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 3.198 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-f16-f16-mutant-native-regression.stdout, logs/p2-f16-f16-mutant-native-regression.stderr, logs/p2-f16-f16-mutant-native-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-n01-parent-build

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Compile actual n01-parent for n01 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.126 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-n01-parent-build.stdout, logs/p2-n01-n01-parent-build.stderr, logs/p2-n01-n01-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-n01-parent-regression

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Run COMPLETE claimed regression-chisquare.sh unchanged on n01-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 25.204 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-n01-parent-regression.stdout, logs/p2-n01-n01-parent-regression.stderr, logs/p2-n01-n01-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual fixed for n01 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.161 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-fixed-build.stdout, logs/p2-n01-fixed-build.stderr, logs/p2-n01-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-chisquare.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 23.782 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-fixed-regression.stdout, logs/p2-n01-fixed-regression.stderr, logs/p2-n01-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-n01-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual n01-mutant for n01 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.159 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-n01-mutant-build.stdout, logs/p2-n01-n01-mutant-build.stderr, logs/p2-n01-n01-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-n01-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-chisquare.sh unchanged on n01-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 29.825 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-n01-mutant-regression.stdout, logs/p2-n01-n01-mutant-regression.stderr, logs/p2-n01-n01-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n02-n02-parent-build

- Snapshot: da0265c94d746e885b57daa8af4a710cd10193c4
- Intended assertion: Compile actual n02-parent for n02 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.239 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n02-n02-parent-build.stdout, logs/p2-n02-n02-parent-build.stderr, logs/p2-n02-n02-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n02-n02-parent-regression

- Snapshot: da0265c94d746e885b57daa8af4a710cd10193c4
- Intended assertion: Run COMPLETE claimed regression-271.sh unchanged on n02-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 0.521 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n02-n02-parent-regression.stdout, logs/p2-n02-n02-parent-regression.stderr, logs/p2-n02-n02-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n02-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual fixed for n02 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.098 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n02-fixed-build.stdout, logs/p2-n02-fixed-build.stderr, logs/p2-n02-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n02-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-271.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 175.142 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n02-fixed-regression.stdout, logs/p2-n02-fixed-regression.stderr, logs/p2-n02-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n02-n02-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual n02-mutant for n02 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.456 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n02-n02-mutant-build.stdout, logs/p2-n02-n02-mutant-build.stderr, logs/p2-n02-n02-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n02-n02-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-271.sh unchanged on n02-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 0.550 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n02-n02-mutant-regression.stdout, logs/p2-n02-n02-mutant-regression.stderr, logs/p2-n02-n02-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-novel01-novel01-parent-regression

- Snapshot: 55a7f65e52b1764532ae67678e0fba2e41580347
- Intended assertion: Run COMPLETE claimed regression-272.sh unchanged on novel01-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 36.858 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-novel01-novel01-parent-regression.stdout, logs/p2-novel01-novel01-parent-regression.stderr, logs/p2-novel01-novel01-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-novel01-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-272.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 38.076 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-novel01-fixed-regression.stdout, logs/p2-novel01-fixed-regression.stderr, logs/p2-novel01-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-novel01-novel01-compare-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-272.sh unchanged on novel01-compare-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 36.729 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-novel01-novel01-compare-mutant-regression.stdout, logs/p2-novel01-novel01-compare-mutant-regression.stderr, logs/p2-novel01-novel01-compare-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-novel01-novel01-exit-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-272.sh unchanged on novel01-exit-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 37.501 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-novel01-novel01-exit-mutant-regression.stdout, logs/p2-novel01-novel01-exit-mutant-regression.stderr, logs/p2-novel01-novel01-exit-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 093-positive-triples-overview

- Snapshot: actual parents/fixed/mutants per p2-source-map.json
- Intended assertion: Collect all full regression stdout results for intended-reason review; no verification from exit status alone.
- Observed process exit: 0; duration: 0.039 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/093-positive-triples-overview.stdout, logs/093-positive-triples-overview.stderr, logs/093-positive-triples-overview.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-parent-build

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Build direct chi-square driver; old void/bool signature adapter is disclosed and does not change behavior.
- Observed process exit: 0; duration: 0.712 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-parent-build.stdout, logs/p2-n01-direct-parent-build.stderr, logs/p2-n01-direct-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-parent-m2_minimal_balanced

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.281 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-parent-m2_minimal_balanced.stdout, logs/p2-n01-direct-parent-m2_minimal_balanced.stderr, logs/p2-n01-direct-parent-m2_minimal_balanced.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-parent-m1_minimal_below

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-parent-m1_minimal_below.stdout, logs/p2-n01-direct-parent-m1_minimal_below.stderr, logs/p2-n01-direct-parent-m1_minimal_below.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-parent-m2_applied_failed

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.007 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-parent-m2_applied_failed.stdout, logs/p2-n01-direct-parent-m2_applied_failed.stderr, logs/p2-n01-direct-parent-m2_applied_failed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-parent-m1_allzero_direct

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-parent-m1_allzero_direct.stdout, logs/p2-n01-direct-parent-m1_allzero_direct.stderr, logs/p2-n01-direct-parent-m1_allzero_direct.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-parent-m1_allone_direct

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-parent-m1_allone_direct.stdout, logs/p2-n01-direct-parent-m1_allone_direct.stderr, logs/p2-n01-direct-parent-m1_allone_direct.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-parent-ones3162

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.009 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-parent-ones3162.stdout, logs/p2-n01-direct-parent-ones3162.stderr, logs/p2-n01-direct-parent-ones3162.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-parent-ones3163

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.010 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-parent-ones3163.stdout, logs/p2-n01-direct-parent-ones3163.stderr, logs/p2-n01-direct-parent-ones3163.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-cli-parent-ones3162

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Run complete compliant-million-sample IID CLI to distinguish chi-square result, overall exit and JSON #252 reporting; no shortened permutation coverage.
- Observed process exit: 0; duration: 10.061 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-cli-parent-ones3162.stdout, logs/p2-n01-cli-parent-ones3162.stderr, logs/p2-n01-cli-parent-ones3162.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-cli-parent-ones3163

- Snapshot: c748c0caa1e7ea5c903bd42fb6159c9b5d1254f4
- Intended assertion: Run complete compliant-million-sample IID CLI to distinguish chi-square result, overall exit and JSON #252 reporting; no shortened permutation coverage.
- Observed process exit: 0; duration: 12.539 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-cli-parent-ones3163.stdout, logs/p2-n01-cli-parent-ones3163.stderr, logs/p2-n01-cli-parent-ones3163.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Build direct chi-square driver; old void/bool signature adapter is disclosed and does not change behavior.
- Observed process exit: 0; duration: 0.765 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-fixed-build.stdout, logs/p2-n01-direct-fixed-build.stderr, logs/p2-n01-direct-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-fixed-m2_minimal_balanced

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.235 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-fixed-m2_minimal_balanced.stdout, logs/p2-n01-direct-fixed-m2_minimal_balanced.stderr, logs/p2-n01-direct-fixed-m2_minimal_balanced.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-fixed-m1_minimal_below

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.006 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-fixed-m1_minimal_below.stdout, logs/p2-n01-direct-fixed-m1_minimal_below.stderr, logs/p2-n01-direct-fixed-m1_minimal_below.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-fixed-m2_applied_failed

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-fixed-m2_applied_failed.stdout, logs/p2-n01-direct-fixed-m2_applied_failed.stderr, logs/p2-n01-direct-fixed-m2_applied_failed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-fixed-m1_allzero_direct

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-fixed-m1_allzero_direct.stdout, logs/p2-n01-direct-fixed-m1_allzero_direct.stderr, logs/p2-n01-direct-fixed-m1_allzero_direct.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-fixed-m1_allone_direct

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-fixed-m1_allone_direct.stdout, logs/p2-n01-direct-fixed-m1_allone_direct.stderr, logs/p2-n01-direct-fixed-m1_allone_direct.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-fixed-ones3162

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.011 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-fixed-ones3162.stdout, logs/p2-n01-direct-fixed-ones3162.stderr, logs/p2-n01-direct-fixed-ones3162.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-fixed-ones3163

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.010 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-fixed-ones3163.stdout, logs/p2-n01-direct-fixed-ones3163.stderr, logs/p2-n01-direct-fixed-ones3163.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-cli-fixed-ones3162

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run complete compliant-million-sample IID CLI to distinguish chi-square result, overall exit and JSON #252 reporting; no shortened permutation coverage.
- Observed process exit: 0; duration: 9.014 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-cli-fixed-ones3162.stdout, logs/p2-n01-cli-fixed-ones3162.stderr, logs/p2-n01-cli-fixed-ones3162.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-cli-fixed-ones3163

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run complete compliant-million-sample IID CLI to distinguish chi-square result, overall exit and JSON #252 reporting; no shortened permutation coverage.
- Observed process exit: 0; duration: 16.194 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-cli-fixed-ones3163.stdout, logs/p2-n01-cli-fixed-ones3163.stderr, logs/p2-n01-cli-fixed-ones3163.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Build direct chi-square driver; old void/bool signature adapter is disclosed and does not change behavior.
- Observed process exit: 0; duration: 0.713 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-mutant-build.stdout, logs/p2-n01-direct-mutant-build.stderr, logs/p2-n01-direct-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-mutant-m2_minimal_balanced

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.175 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-mutant-m2_minimal_balanced.stdout, logs/p2-n01-direct-mutant-m2_minimal_balanced.stderr, logs/p2-n01-direct-mutant-m2_minimal_balanced.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-mutant-m1_minimal_below

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-mutant-m1_minimal_below.stdout, logs/p2-n01-direct-mutant-m1_minimal_below.stderr, logs/p2-n01-direct-mutant-m1_minimal_below.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-mutant-m2_applied_failed

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-mutant-m2_applied_failed.stdout, logs/p2-n01-direct-mutant-m2_applied_failed.stderr, logs/p2-n01-direct-mutant-m2_applied_failed.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-mutant-m1_allzero_direct

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-mutant-m1_allzero_direct.stdout, logs/p2-n01-direct-mutant-m1_allzero_direct.stderr, logs/p2-n01-direct-mutant-m1_allzero_direct.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-mutant-m1_allone_direct

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.005 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-mutant-m1_allone_direct.stdout, logs/p2-n01-direct-mutant-m1_allone_direct.stderr, logs/p2-n01-direct-mutant-m1_allone_direct.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-mutant-ones3162

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.083 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-mutant-ones3162.stdout, logs/p2-n01-direct-mutant-ones3162.stderr, logs/p2-n01-direct-mutant-ones3162.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-direct-mutant-ones3163

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Observe all binary chi-square return paths, m1/m2 boundary and independent rational T controls without invoking unrelated permutation workload.
- Observed process exit: 0; duration: 0.010 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-direct-mutant-ones3163.stdout, logs/p2-n01-direct-mutant-ones3163.stderr, logs/p2-n01-direct-mutant-ones3163.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-cli-mutant-ones3162

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run complete compliant-million-sample IID CLI to distinguish chi-square result, overall exit and JSON #252 reporting; no shortened permutation coverage.
- Observed process exit: 0; duration: 10.798 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-cli-mutant-ones3162.stdout, logs/p2-n01-cli-mutant-ones3162.stderr, logs/p2-n01-cli-mutant-ones3162.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-n01-cli-mutant-ones3163

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run complete compliant-million-sample IID CLI to distinguish chi-square result, overall exit and JSON #252 reporting; no shortened permutation coverage.
- Observed process exit: 0; duration: 12.052 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-n01-cli-mutant-ones3163.stdout, logs/p2-n01-cli-mutant-ones3163.stderr, logs/p2-n01-cli-mutant-ones3163.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r2-r2-parent-build

- Snapshot: 23dca69717430188e1475258a26cb35f64251878
- Intended assertion: Compile actual r2-parent for r2 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.577 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r2-r2-parent-build.stdout, logs/p2-r2-r2-parent-build.stderr, logs/p2-r2-r2-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r2-r2-parent-regression

- Snapshot: 23dca69717430188e1475258a26cb35f64251878
- Intended assertion: Run COMPLETE claimed regression-restart.sh unchanged on r2-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 67.953 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r2-r2-parent-regression.stdout, logs/p2-r2-r2-parent-regression.stderr, logs/p2-r2-r2-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r2-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual fixed for r2 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.557 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r2-fixed-build.stdout, logs/p2-r2-fixed-build.stderr, logs/p2-r2-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r2-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-restart.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 67.186 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r2-fixed-regression.stdout, logs/p2-r2-fixed-regression.stderr, logs/p2-r2-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r2-r2-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual r2-mutant for r2 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.671 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r2-r2-mutant-build.stdout, logs/p2-r2-r2-mutant-build.stderr, logs/p2-r2-r2-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r2-r2-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-restart.sh unchanged on r2-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 66.007 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r2-r2-mutant-regression.stdout, logs/p2-r2-r2-mutant-regression.stderr, logs/p2-r2-r2-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r3-r3-parent-build

- Snapshot: db7a2bafaa1617339b4cd6249d4640974c7a0e8c
- Intended assertion: Compile actual r3-parent for r3 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.564 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r3-r3-parent-build.stdout, logs/p2-r3-r3-parent-build.stderr, logs/p2-r3-r3-parent-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r3-r3-parent-regression

- Snapshot: db7a2bafaa1617339b4cd6249d4640974c7a0e8c
- Intended assertion: Run COMPLETE claimed regression-restart.sh unchanged on r3-parent; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 62.236 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r3-r3-parent-regression.stdout, logs/p2-r3-r3-parent-regression.stderr, logs/p2-r3-r3-parent-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r3-fixed-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual fixed for r3 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.767 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r3-fixed-build.stdout, logs/p2-r3-fixed-build.stderr, logs/p2-r3-fixed-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r3-fixed-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-restart.sh unchanged on fixed; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 0; duration: 63.287 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r3-fixed-regression.stdout, logs/p2-r3-fixed-regression.stderr, logs/p2-r3-fixed-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r3-r3-mutant-build

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Compile actual r3-mutant for r3 with ordinary native flags. Source/header mutations only in named disposable copies; compile failure is not behavioral sensitivity.
- Observed process exit: 0; duration: 1.625 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r3-r3-mutant-build.stdout, logs/p2-r3-r3-mutant-build.stderr, logs/p2-r3-r3-mutant-build.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record p2-r3-r3-mutant-regression

- Snapshot: 34fb906196f8d47da774c88928eff0d8ec08d618
- Intended assertion: Run COMPLETE claimed regression-restart.sh unchanged on r3-mutant; preserve every original fixture/assertion/tolerance and original simulation/permutation coverage. No full-suite pass on timeout.
- Observed process exit: 1; duration: 61.324 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/p2-r3-r3-mutant-regression.stdout, logs/p2-r3-r3-mutant-regression.stderr, logs/p2-r3-r3-mutant-regression.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 094-record-positive-triples

- Snapshot: actual parents/fixed/mutants in p2-source-map.json
- Intended assertion: Update only external finding inventory with reviewed, scoped pre-fix/fixed/mutation evidence; retain uncertainty, platform limits and failed harness attempts.
- Observed process exit: 0; duration: 0.019 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/094-record-positive-triples.stdout, logs/094-record-positive-triples.stderr, logs/094-record-positive-triples.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 095-n01-independent-outcome-analysis

- Snapshot: N01 actual parentc748c0c historicalfixed34fb906 compiling m1 mutant
- Intended assertion: Compare direct chi-square statistics to independently computed exact-rational expectations and inspect complete1m-sample CLI JSON/exit separately from chi-square result.
- Observed process exit: 0; duration: 0.039 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/095-n01-independent-outcome-analysis.stdout, logs/095-n01-independent-outcome-analysis.stderr, logs/095-n01-independent-outcome-analysis.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 096-record-f09-restart-positives

- Snapshot: actual F09 R2 R3 parents and historical fixed34fb906
- Intended assertion: Record reviewed F09/R2/R3 positive repair triples in external inventory with scope and unresolved limitations; do not conflate original native suite passes with Linux timeouts.
- Observed process exit: 0; duration: 0.041 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/096-record-f09-restart-positives.stdout, logs/096-record-f09-restart-positives.stderr, logs/096-record-f09-restart-positives.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.

### Execution record 097-positive-claims-checkpoint

- Snapshot: historical/current and actual repair parents per baseline map
- Intended assertion: Freeze complete positive-repair triple/corpus/pin evidence and updated scoped inventory after this batch; retain all failed harness and timeout results.
- Observed process exit: 0; duration: 2.370 s; timeout: False; interruption: False; harness: None.
- Complete evidence: logs/097-positive-claims-checkpoint.stdout, logs/097-positive-claims-checkpoint.stderr, logs/097-positive-claims-checkpoint.result.json.
- Assertion evaluation pending unless explicitly resolved in a finding section. Process exit alone does not establish the claim.
