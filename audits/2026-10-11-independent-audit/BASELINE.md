# Baseline — 2026-10-11/12 independent audit

Everything the audit's conclusions are relative to. Recorded before the
finders ran; re-verified 2026-10-12.

## Code under audit

| Role | Ref | Commit |
|---|---|---|
| Primary target | `master` (= `origin/master`, clean tree) | `f06989802622a9d2c0991c7052890f1dc9cddb17` |
| Secondary target | `repair/2026-10-09-verified-defects` (unmerged, 17 commits ahead of master) | `2d4b135f4f46db3ec360b4c31fa795eb934ce38c` |
| Upstream baseline (= merge base) | `usnistgov/SP800-90B_EntropyAssessment` `master` | `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289` |

The fork is 57 commits ahead of upstream; upstream is 0 commits ahead of the
merge base, so every difference is fork-introduced. Upstream PR
[#273](https://github.com/usnistgov/SP800-90B_EntropyAssessment/pull/273)
(opened 2026-10-10 by `systemslibrarian`) carries the `NOVEL-03` dataLayout
patch and is not merged.

## Host and toolchain

| Item | Value |
|---|---|
| Host | Apple M5, 10 cores, 16 GB RAM, macOS 26.6.2, arm64 (`darwin25.6.0`) |
| Compiler | Apple clang 21.0.0 (`clang-2100.3.34.2`) |
| Release flags | `-std=c++11 -Xpreprocessor -fopenmp -O2 -ffloat-store` (Makefile Darwin block) |
| Sanitizer flags | `-std=c++11 -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=undefined` |
| `sizeof(long double)` | 8 (arm64) — 64-bit mantissa platforms are **not** represented; see the platform caveat below |
| OpenSSL | 3.6.4 | 
| libomp | 23.1.2 |
| jsoncpp | 1.9.8 |
| libdivsufsort | 2.0.1 |
| GMP / MPFR | 6.3.0 / 4.2.2 |
| Python | 3.14.7 with mpmath 1.4.1 (no numpy, no scipy) |

Four worktrees were built from these sources for comparison: `master` (release),
`master-asan` (ASan+UBSan), `repair` (release), `upstream` (release, built with
explicit `-L` flags because upstream's Makefile has no working Darwin library
path).

## Specification text

SP 800-90B (January 2018) plus the NIST errata sheet dated 2025-05-29. Section
and step citations in the findings refer to that text. One finding
(`EST-5`) concerns an arithmetic inconsistency in errata item 2 itself, not in
this repository.

## Deterministic fixtures

Generator `audits/2026-10-09-independent-audit/generators/valid_fixtures.py`,
seed `0x90b20261009`, SHA-256 per file in the generated `manifest.json`.
Nineteen files, 1,000,000 samples each (`subset-source-1bit.bin` has
2,000,000): `constant`, `near-constant`, `biased-p01`, `uniform`,
`alternating`, `period6`, `markov-stay99`, `drift`, `repeated-block`
(1-bit); `uniform-{2..8}bit`; `uniform-sparse-8bit` (symbols {0,17,255}).
Finders generated further datasets themselves and recorded seed and SHA-256
for each.

## Standing caveats

1. **One platform.** Every execution result is from arm64 macOS with a 64-bit
   `long double`. Upstream issue #155 and this audit's `EST-3` both concern
   quantities that differ in their last digits on 80-bit `long double`
   (x86-64) builds. A Linux x86-64 GCC verification was commissioned as its
   own dimension; its outcome is recorded in `COVERAGE.md`, and where it did
   not complete, the affected claims say so.
2. **Non-determinism.** `ea_iid` and `ea_restart` seed their permutation and
   simulation batteries from `/dev/urandom`; repeated runs differ. Statistical
   claims about those tools rest on repeated trials or on deterministic
   calculation, as each finding states.
3. **Audit only.** No production file was modified, nothing was committed, and
   no upstream issue or pull request was created, commented on, or closed.
   Authorization for the defensive audit is recorded in `AGENTS.md`.
4. **Evidence, not proof.** Passing tests and clean batteries are coverage
   evidence. They do not establish estimator correctness for all inputs.
