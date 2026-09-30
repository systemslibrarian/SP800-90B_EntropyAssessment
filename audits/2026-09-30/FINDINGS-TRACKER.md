# Findings tracker — 2026-09-30 audits

The canonical list of every finding from the three 2026-09-30 audit rounds of `usnistgov/SP800-90B_EntropyAssessment` at upstream `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`.

**Sources.** Every cell is taken from the originating document:
- F-series: [`AUDIT.md`](AUDIT.md), plus §4 of the novel-findings report for rows re-verified later.
- N/R-series: [`novel-findings/REPORT.md`](novel-findings/REPORT.md).
- NOVEL-series: [`phase2-focused/REPORT.md`](phase2-focused/REPORT.md).

**Columns.**
- *Severity / importance* quotes the category, direction and confidence the source report states; no new severities were assigned.
- *Upstream status* was read from GitHub on 2026-09-30. Re-check it before relying on it.
- *Fork fix status* refers to branches of `systemslibrarian/SP800-90B_EntropyAssessment`. Fork `master` carries no estimator changes.
- *Regression test?* is "no" everywhere: no automated regression test has been added to any repository. "Described" means the report specifies one.
- *Dangerous direction* means the reported entropy is too HIGH, or an IID/restart gate wrongly passes.

## Summary

| Series | Findings | Filed upstream (open) | Residual of a closed upstream item | Audit-only / not filed |
|---|---:|---|---|---|
| F (first wave) | 30 | F01 #253, F02 #254, F03/F05 #255, F04 #258, F11 #263, F12 #264, F15 #261, F16 #257, F18 #259, F19 #260 | — | F06–F10, F13, F14, F20–F30 (F07 → closed #22; F17 → closed #214/#163/#52) |
| N (novel findings) | 11 | N-02 #271 | — | N-01, N-03–N-11 |
| R (residuals) | 3 | — | R-1 #246, R-2 #178, R-3 #183 | all three (not reported upstream) |
| NOVEL (phase 2) | 3 | NOVEL-01 #272 | — | NOVEL-02, NOVEL-03 |

Findings in the dangerous direction that still apply to normal-size (≥ 10^6) input:
- **F01, F02, F05:** filed.
- **N-01:** audit-only.
- **N-02:** filed (#271).
- **F06 and F28:** spec-level, not code defects.

## F-series (first-wave audit of ea_non_iid)

| ID | Title | Category | Severity / importance (as stated in source) | Component | Normal-size (≥ 10^6) input? | Dangerous direction? | Reproduction? | Regression test? | Upstream issue/PR | Upstream status (2026-09-30) | Fork fix status | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F01 | Two-valued multi-bit data assessed as binary; n×H_bitstring omitted | A entropy | Too HIGH; VERIFIED (0.9216 vs 0.1796 per §3.1.3) | ea_non_iid (same gate in ea_iid) | yes | yes | yes | no | #253, PR #256 | #253 open; PR #256 open | Fix branch `fix/bitstring-gate-word-size` (PR #256); not merged into fork master | AUDIT.md (F01) | Same root cause also in iid_main.cpp:280-299 (novel-findings §3) |
| F02 | Default bits_per_symbol inference narrows width, changes n×H_bitstring | A entropy | Too HIGH vs declared-width computation; VERIFIED (3.739 vs 1.539) | ea_non_iid (also ea_conditioning -i) | yes | yes | yes | no | #254 | open | none | AUDIT.md (F02) | Width choice is a spec-reading decision for maintainers (AUDIT) |
| F03 | Sub-minimum sample counts invisible in JSON (errorLevel 0) | E reporting | Too HIGH at sub-minimum sizes; VERIFIED | ea_non_iid | no | yes | yes | no | #255 (related #238) | #255 open; #238 open | none | AUDIT.md (F03) | Filed together with F05 |
| F04 | Literal MultiMCW skipped for 64 ≤ L ≤ 4095; off-by-one message | A entropy | Too HIGH; VERIFIED (mechanism) | ea_non_iid | no | yes | yes | no | #258 (dup #265) | #258 open; #265 closed (not planned, duplicate) | none | AUDIT.md (F04) |  |
| F05 | Skipped estimators (−1) silently omitted from minimum/JSON | A/E | Too HIGH, unbounded in principle; mechanism VERIFIED; de Bruijn LRS v<u verified at exactly 10^6 | ea_non_iid | yes | yes | yes | no | #255 | open | none | AUDIT.md (F05); novel-findings/REPORT.md §4 |  |
| F06 | Compression step 8 returns 1.0 when X̄′ exceeds uniform expectation | A (spec-literal) | Too HIGH (+15–42 % on constructed sources); UNVERIFIED attacker claim | ea_non_iid | yes | yes | generator in AUDIT | no | — | not filed | none | AUDIT.md (F06) | Spec-literal behaviour, not a code divergence |
| F07 | Z = 2.5758293 instead of the printed 2.576 | A (constant) | Too HIGH by ≤ 5e-6 bit/bit; UNVERIFIED | all estimators | yes | yes (≤ 5e-6) | yes | no | #22 | closed (completed) | none | AUDIT.md (F07) | Deliberate full-precision value (#22) |
| F08 | P_local recurrence iterated to convergence instead of x = x₁₀ | A (numerics) | Too HIGH < 1e-10; UNVERIFIED | predictors | yes | yes (< 1e-10) | no | no | — (related closed #133) | not filed | none | AUDIT.md (F08) |  |
| F09 | Generic MultiMMC: a Null winner prediction does not reset the run | A entropy | TOO LOW; VERIFIED (r 6603 vs spec 24; MultiMMC 0.0021 vs 0.93; assessed figure unchanged) | ea_non_iid (MultiMMC, multi_mmc_test.h:211-228) | no (shown at 114,146 samples) | no | yes (`generators/noniid/f09gen.py 3 300`) | no (described: expect r = 24) | — | not filed | none | novel-findings/REPORT.md §4; novel-findings/logs/noniid/out/f09b_run1.txt | No upstream item |
| F10 | Generic MultiMMC chained lookup skips deeper orders | A (either) | Mechanism only; no C/r effect at shipped constants; needs more work | ea_non_iid | unknown | unknown | instrumented harness | no | — | not filed | none | novel-findings/agent-reports/noniid-estimators.md |  |
| F11 | Compression admits exactly 1001 blocks (v = 1): σ̂ divides by zero | A (tiny inputs) | AUDIT: dangerous direction did not reproduce (−0); #263 records 1.0 (NaN) or −0 | ea_non_iid | no (6006–6011 bits) | tiny inputs only | yes | no | #263, PR #270 | #263 open; PR #270 open | Fix branch `fix/compression-min-test-blocks` (PR #270); not merged into fork master | AUDIT.md (F11) | Filed after the AUDIT round-2 note |
| F12 | Collision estimate with v ≤ 1 (2–5 binary samples) → NaN, prints 1 | A (tiny inputs) | AUDIT: no dangerous figure in any config (later assert/ASan) | ea_non_iid | no | estimator-level only | yes | no | #264 | open | none | AUDIT.md (F12) |  |
| F13 | NaN folded by std::min discards earlier minima | A (theoretical) | No producer at ≥ 10^6 in any tool (novel-findings audit) | ea_non_iid | no | theoretical | no | no | — | not filed | none | AUDIT.md (F13); novel-findings/REPORT.md §4 |  |
| F14 | Compression dict[] index stored in unsigned int (> 2^32 blocks) | A entropy | TOO HIGH (1.0 vs 0 in harness); needs > 25.77 Gbit and ≈ 650 GB RAM end-to-end | ea_non_iid (compression_test.h:97) | no | yes (only > 25.8 Gbit) | harness logs | no | — | not filed | none | novel-findings/REPORT.md §4; novel-findings/logs/noniid/out/f14_big.log | Latent in the size range #217/#226 enabled |
| F15 | assert() aborts on tiny/repeat-free inputs (asserts live) | D robustness | Neither; VERIFIED | ea_non_iid (LRS, LZ78Y, MultiMMC) | no | no | yes | no | #261 (dup #262) | #261 open; #262 closed (not planned, duplicate) | none | AUDIT.md (F15) |  |
| F16 | Binary MultiMMC heap over-read for 4 ≤ L ≤ 16 | B memory | Neither; VERIFIED (ASan) | ea_non_iid (multi_mmc_test.h:38) | no | no | yes | no | #257, PR #268 (dup PR #269) | #257 open; PR #268 open; PR #269 closed | Fix branch `fix/multimmc-binary-overread` (PR #268); not merged into fork master | AUDIT.md (F16) |  |
| F17 | LRS stage quadratic on inputs with long repeats | D (performance) | Neither; VERIFIED; known | ea_non_iid (lrs_test.h) | yes | no | yes | no | #214, #163, #52 | closed | none | AUDIT.md (F17) | Known; not refiled |
| F18 | sha256_file reads to EOF: hang on /dev/zero, FIFO | D availability | Neither; VERIFIED | all tools (TestRunUtils.h) | n/a (non-regular files) | no | yes | no | #259 (dup #266) | #259 open; #266 closed (not planned, duplicate) | none | AUDIT.md (F18) |  |
| F19 | -l offset overflow; subset runs record whole-file SHA-256 | C integrity | Neither/either; VERIFIED | ea_non_iid / ea_iid (-l) | n/a (command line) | no | yes | no | #260 (dup #267) | #260 open; #267 closed (not planned, duplicate) | none | AUDIT.md (F19) |  |
| F20 | -t truncation also applied under -c | A (either) | Mechanism reproduces; maintainer position in #127/#139/#140 | ea_non_iid | yes | either | yes | no | — (#127/#139/#140 discussion) | not filed | none | AUDIT.md (F20); novel-findings/REPORT.md §4 |  |
| F21 | Bit order within a symbol (MSB-first) changes H_bitstring | A (convention) | Either; UNVERIFIED | ea_non_iid | yes | either | no | no | — (#71 discussion) | not filed | none | AUDIT.md (F21) | Spec does not fix bit order |
| F22 | H_bitstring built from raw values (encoding-dependent) | A (spec-consistent) | Either; UNVERIFIED | ea_non_iid | yes | either | no | no | — | not filed | none | AUDIT.md (F22) |  |
| F23 | Reporting: JSON keeps literal MCV only; -c hAssessed = n×h′; rounding | E reporting | Neither; partly reproduces | ea_non_iid | yes | no | partly | no | — (partly #179, #251) | not filed | none | AUDIT.md (F23); novel-findings/REPORT.md §4 |  |
| F24 | prediction_estimate_function: FMA NaN vs −inf near x = 1/p | numerics | Neither; UNVERIFIED | predictors | n/a | no | no | no | — | not filed | none | AUDIT.md (F24) |  |
| F25 | calc_p_local termination guarantee for very large N | numerics | Either; THEORETICAL | predictors | no | either | no | no | — | not filed | none | AUDIT.md (F25) |  |
| F26 | Markov estimate has no confidence adjustment | spec-consistent | Either; matches the final spec | ea_non_iid | no (small L) | either | no | no | — | not filed | none | AUDIT.md (F26) | Spec, not code |
| F27 | SP 800-90B Appendix G.2 Table 3 row labels offset by 5 | spec erratum | Neither | specification | n/a | no | no | no | — | not filed | n/a | AUDIT.md (F27) | Spec erratum, not code |
| F28 | Deterministic sources with long memory score near full entropy | spec limitation | Too HIGH (whole battery); spec limitation | whole battery | yes | yes (spec-level) | generators in AUDIT | no | — | not filed | n/a | AUDIT.md (F28) | Spec limitation, not code |
| F29 | Single-estimator blind spots | spec limitation | Too HIGH per estimator; neither overall | individual estimators | yes | per estimator only | no | no | — | not filed | n/a | AUDIT.md (F29) | Spec limitation |
| F30 | LRS estimates collision entropy (can exceed min-entropy) | spec-consistent | Too HIGH per estimator; other estimators bound the figure | ea_non_iid (LRS) | yes | per estimator only | no | no | — | not filed | n/a | AUDIT.md (F30) | Spec says so explicitly |

## N-series (novel-findings audit, all executables)

| ID | Title | Category | Severity / importance (as stated in source) | Component | Normal-size (≥ 10^6) input? | Dangerous direction? | Reproduction? | Regression test? | Upstream issue/PR | Upstream status (2026-09-30) | Fork fix status | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N-01 | Binary chi-square independence reports Passed when m = 1 (§5.2.3 says the test fails) | A entropy / IID gate | TOO HIGH (IID wrongly accepted); 1.42× in repro; report priority 1 | ea_iid (also ea_restart -i) | yes | yes | yes | no (described: ones_3162 must fail; ones_3163 df = 2) | — | not filed (audit-only) | none | novel-findings/REPORT.md N-01; novel-findings/repro/verify/ones3162_iid.json; phase2-focused/logs/evidence/json/iid_p002.1.json | Independently rediscovered by the phase-2 audit (+38 %) |
| N-02 | ea_iid -c runs IID tests on packed symbols, not the conditioned bitstring | A entropy / IID gate | TOO HIGH (h′ 2.47× in repro); report priority 2 | ea_iid -c | yes | yes | yes | no (described) | #271 | open | none | novel-findings/REPORT.md N-02; novel-findings/repro/verify/nibdup_iidc.json; novel-findings/repro/n02-fresh/ISSUE-N02.md | Filed upstream as #271 |
| N-03 | ea_conditioning -n -i on an all-zero conditioned file: assert abort; -DNDEBUG heap over-read | D/B | None (correct h′ = 0); report priority after R-1 | ea_conditioning | yes | no | yes | no (described) | — | not filed | none | novel-findings/REPORT.md N-03; novel-findings/logs/conditioning/ndebug/ | Possible comment on #261 per report |
| N-04 | ea_restart H_I = nan passes checks → UB/SIGSEGV; H_I = abc → 0 | B/D | None | ea_restart | yes | no | yes | no | — (#195 is a different path) | not filed | none | novel-findings/REPORT.md N-04; phase2-focused/logs/evidence/restart_HI_fuzz.log | Rediscovered by the phase-2 audit |
| N-05 | Conditioning JSON binds -i file hash to an h′ not measured from it | C integrity | HIGH (behaviour) / MEDIUM (severity) | ea_conditioning | yes | no | yes | no | — | not filed | none | novel-findings/REPORT.md N-05; novel-findings/repro/verify/both.json |  |
| N-06 | sha256_file() failure ignored: uninitialised bytes in JSON sha256 | B/C | Low | ea_iid, ea_non_iid, ea_restart, ea_conditioning | yes | no | yes | no | — | not filed | none | novel-findings/REPORT.md N-06; novel-findings/repro/verify/nf1.json; phase2-focused/logs/evidence/json/ne.json | Rediscovered by the phase-2 audit |
| N-07 | TOCTOU between the hash pass and the data pass | C (hardening) | LOW–MEDIUM severity | all mains | yes | no | yes (LD_PRELOAD shim) | no | — | not filed | none | novel-findings/REPORT.md N-07; novel-findings/repro/verify/toctou_shim.c | Distinct from #259/#260 |
| N-08 | Numeric CLI arguments parsed permissively (octal -l, atoi, strtoul base 0) | D/E | None or lower | ea_non_iid, ea_iid, ea_restart, ea_conditioning, ea_transpose | n/a | no | yes | no | — (#260 is -l arithmetic) | not filed | none | novel-findings/REPORT.md N-08; novel-findings/logs/io/ | Optional hardening issue per report |
| N-09 | Output-file write failures never checked | E | None | multiple (+ ea_transpose) | n/a | no | yes | no | — | not filed | none | novel-findings/REPORT.md N-09; novel-findings/logs/io/ |  |
| N-10 | Reporting-only: IID median of translated indices; conditioning JSON "IID": false; restart -i mean/median 0.0 | E | None | ea_iid, ea_conditioning, ea_restart | yes | no | yes | no | — | not filed | none | novel-findings/REPORT.md N-10 |  |
| N-11 | ea_conditioning aborts (assert) for accepted n_in/n_out ≥ 1,073,741,823 | D | LOW relevance | ea_conditioning | n/a | no | yes | no | — | not filed | none | novel-findings/REPORT.md N-11; novel-findings/logs/conditioning/asanlogs/ |  |

## R-series (residuals of closed upstream fixes)

| ID | Title | Category | Severity / importance (as stated in source) | Component | Normal-size (≥ 10^6) input? | Dangerous direction? | Reproduction? | Regression test? | Upstream issue/PR | Upstream status (2026-09-30) | Fork fix status | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R-1 | Residual of #246: p_col ≥ 1/k assert on exactly balanced counts (k = 3, 6, 7, 9, 12, …) | D (abort) | Actionable residual; reproduces at 10^6 | ea_iid (lrs_test.h:626) | yes | no | yes | no | #246 (PR #248) | #246 closed (completed); residual not reported upstream | none | novel-findings/REPORT.md §3; novel-findings/repro/verify/bal3_1.log | Phase-2 audit reproduced k = 3, 6, 7, 12 |
| R-2 | Residual of #178: restart folds t-tuple/LRS −1 into H_r/H_c (false restart failure) | A entropy | TOO LOW (false restart failure) | ea_restart (restart_main.cpp:632/636/647/651) | yes | no | yes | no | #178 | closed (completed); residual not reported upstream | none | novel-findings/REPORT.md §3; novel-findings/repro/verify/dbr1.log |  |
| R-3 | Residual/regression of #183: ea_restart -i writes JSON errorLevel 0 on read failure (merge 4d68e47) | E reporting | Regression after #183 was closed | ea_restart (restart_main.cpp:324) | yes | no | yes | no | #183 | closed (completed); regression not reported upstream | none | novel-findings/REPORT.md §3; novel-findings/repro/verify/r_iid.json; phase2-focused/logs/evidence/json/w4i.json | Rediscovered by the phase-2 audit |

## NOVEL-series (phase-2 focused audit)

| ID | Title | Category | Severity / importance (as stated in source) | Component | Normal-size (≥ 10^6) input? | Dangerous direction? | Reproduction? | Regression test? | Upstream issue/PR | Upstream status (2026-09-30) | Fork fix status | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOVEL-01 | selftest never compares H_original/H_bitstring/Assessed; exit status reflects only the last file | E (verification tooling) | Masks TOO-HIGH regressions; "the one worth filing" (phase-2) | cpp/selftest (compareresults.pl, selftest) | yes (reference 10^6 files) | no by itself | yes | no (described: both mutants must fail) | #272 | open | none | phase2-focused/REPORT.md NOVEL-01; phase2-focused/repro/issue272/ | Filed text has one rounded table cell (see phase2 MANIFEST) |
| NOVEL-02 | ea_iid JSON emits never-computed placeholders (hBitstring 1.0 for binary; hOriginal = word size under -c) | E reporting | Low | ea_iid (iid_main.cpp:272-284) | yes | no | yes | no | — (distinct from PR #251) | not filed (audit-only) | none | phase2-focused/REPORT.md NOVEL-02; phase2-focused/logs/evidence/json/iid_c_r8.json |  |
| NOVEL-03 | ea_restart -i JSON merges row and column permutation results under identical labels | E reporting | Low | ea_restart (restart_main.cpp:791,800) | yes | no | yes | no | — (introduced with PR #250) | not filed (audit-only) | none | phase2-focused/REPORT.md NOVEL-03; phase2-focused/logs/evidence/json/rst_i.json |  |

## Other upstream items referenced by the audits (known; not audit findings)

| Upstream item | What the audits recorded | Status (2026-09-30) |
|---|---|---|
| #153 | IID LRS test aborts at `assert(p_colPower >= LDBL_MIN)` on one duplicated ≥ 2,049-byte region; detection by design | closed |
| #195 | ea_restart `k_effective` assertion | open |
| #251 (PR) | ea_iid JSON `hAssessed` computed only at `-vvv` | open |
| #252 (PR) | ea_iid / restart `-i` report a figure when IID tests fail; `"IID": true` constant | open |
| #262, #265, #266, #267 | duplicates of #261, #258, #259, #260 respectively | closed (not planned) |
| #269 (PR) | duplicate of PR #268 | closed |
| #56, #95, #209, PR #224 | restart cutoff by simulation instead of the literal binomial rule (intended deviation) | closed |
| #236 / PR #237 | manually maintained VERSION macro (tag v1.1.8 prints 1.1.7) | #236 open |
