# Findings tracker — canonical defect work queue

This file is the authoritative work queue for every defect found in `usnistgov/SP800-90B_EntropyAssessment` by the 2026-09-30 audits (upstream baseline `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`).

A confirmed finding stays in this queue until it is **technically resolved**. An upstream issue being closed, rejected or abandoned, or its discussion stopping, does not resolve it. Deduplicating copied source or evidence does not resolve it either. Findings are never deleted from this file.

## AI Repair Queue

A coding agent can take work from this queue by selecting findings whose **State** is `NEEDS-FIX`, `FORK-FIX-REQUIRED` or `FIXED-UPSTREAM-VERIFY`. The full procedure is [`../BUG-REPAIR-GUIDE.md`](../BUG-REPAIR-GUIDE.md). For each selected finding the agent must:

1. Reproduce the defect first, using the finding's **Reproduce** commands; confirm the stated failure.
2. Inspect current upstream `master` (`git fetch upstream` and read the affected source).
3. Determine whether upstream has already fixed it (issue/PR state *and* code).
4. If fixed upstream: run the reproduction and the regression check against upstream, then update this tracker (`VERIFIED` once a regression test passes).
5. If not fixed: repair it in this fork.
6. Add a permanent regression test for the finding.
7. Run the relevant tests: the selftest (and, until NOVEL-01 is fixed, check the "Assessed min entropy" lines separately) plus an ASan/UBSan build where memory or UB is involved.
8. Commit the repair separately: one finding (or one shared root cause) per commit. Never combine unrelated fixes.
9. Record the resulting commit SHA, regression test path, verification result and date in the finding's entry below.

## States

| State | Meaning |
|---|---|
| `NEEDS-FIX` | Confirmed defect with no merged fix anywhere. It may be filed upstream; a fix is still needed. |
| `UPSTREAM-FIX-PENDING` | Confirmed; an upstream pull request proposing a fix is open. Watch it. If it closes unmerged → `FORK-FIX-REQUIRED`. |
| `FIXED-UPSTREAM-VERIFY` | Upstream merged a fix or closed the issue as fixed; the code and regression test still need verifying here. |
| `FORK-FIX-REQUIRED` | Upstream closed, rejected or abandoned the item (or closed a related item) without fixing this defect; the fork must fix it. |
| `FORK-FIXED` | This fork contains the correction and a regression test proving it. |
| `VERIFIED` | Resolution confirmed: upstream or fork code corrected and the regression test passes. |
| `NOT-A-BUG` | Spec-consistent, spec limitation/erratum, deliberate upstream design, or no observable effect. Kept for the record; not in the queue. |
| `UNCONFIRMED` | Reported but not yet confirmed. Needs verification before it can enter the queue; not in the queue until then. |

**Resolution rule.** A confirmed bug is resolved only when (A) the relevant upstream code is actually corrected and the regression test passes, or (B) this fork contains the correction and a regression test proving it. If upstream closes, rejects or abandons a confirmed bug without fixing it, its state becomes `FORK-FIX-REQUIRED`.

## Queue summary (upstream status last checked 2026-09-30)

- Confirmed defects: **30**.
  - `NEEDS-FIX`: 24
  - `UPSTREAM-FIX-PENDING`: 3
  - `FIXED-UPSTREAM-VERIFY`: 0
  - `FORK-FIX-REQUIRED`: 3
  - `FORK-FIXED`: 0
  - `VERIFIED`: 0
- Unconfirmed or not-a-bug items (not in the queue): **17**; see the end of this file.
- All commands below run from `cpp/` of this fork after `make`. The fork's C++ sources (`cpp/*.cpp`, `cpp/iid/`, `cpp/non_iid/`, `cpp/shared/`) are identical to upstream `87c104d`, so every line reference holds for both. The fork adds only build/doc files: macOS Makefile support, `cpp/selftest/pin-check.sh`, `BUILDING.md`, `NOTICE` and a README pointer. `../audits/2026-09-30/` holds the generators and evidence. Evidence paths are relative to this file.
- Reproduction audit (2026-09-30): every Reproduce block below was re-run, unmodified, on a clean build of fork `master` `237d85c`; 29 of 30 show the stated `BUG:` output. The exception is **F14**. Its harness (`novel-findings/repro/num/f14/`) demonstrates the mechanism on the unmodified function, but an end-to-end run needs more than 25.8 Gbit of input and about 650 GB RAM.

| ID | State | Dangerous direction? | Upstream issue / PR | Next action |
|---|---|---|---|---|
| [F01](#f01) | `UPSTREAM-FIX-PENDING` | yes (too HIGH: 0.9216 vs 0.1796) | #253 / PR #256 | Watch PR #256. If it is closed unmerged, set FORK-FIX-REQUIRED and merge the fix branch into the fork with the regression test. |
| [F02](#f02) | `NEEDS-FIX` | yes (too HIGH vs the declared-width computation) | #254 / — | Check #254 for a maintainer decision. Without one, fork fix: record `word_size` (and whether it was inferred) in JSON and warn; consider requiring bits_per_symbol. |
| [F03](#f03) | `NEEDS-FIX` | yes (a figure is emitted for non-conforming data) | #255 (related #238) / — | Fork fix if upstream stays silent: add a machine-readable warning to the JSON. |
| [F04](#f04) | `NEEDS-FIX` | yes (a missing estimator can only raise the minimum) | #258 (dup #265) / — | Fork fix: remove the 4096 guard and implement Null windows per §6.3.7; compare against a literal reference. |
| [F05](#f05) | `NEEDS-FIX` | yes (unbounded in principle) | #255 / — | Fork fix: record skipped estimators in the JSON test cases and set a warning. |
| [F09](#f09) | `NEEDS-FIX` | no (TOO LOW: MultiMMC 0.0021 vs 0.93; assessed figure unchanged) | — / — | Decide whether to file upstream; fork fix: reset `run_len` when the winner has no prediction. |
| [F11](#f11) | `UPSTREAM-FIX-PENDING` | tiny inputs only (NaN case reports 1.0) | #263 / PR #270 | Watch PR #270; if closed unmerged, set FORK-FIX-REQUIRED and merge `fix/compression-min-test-blocks`. |
| [F12](#f12) | `NEEDS-FIX` | estimator-level only (tiny inputs; later estimators abort) | #264 / — | Fork fix: require v ≥ 2 and return −1 (skipped) otherwise. |
| [F14](#f14) | `NEEDS-FIX` | yes (only above 25.8 Gbit of input) | — / — | Low priority. Fork fix: change the element type to a 64-bit integer; no practical end-to-end test. |
| [F15](#f15) | `NEEDS-FIX` | no | #261 (dup #262) / — | Fork fix: validate minimum lengths before estimators run; keep the asserts as internal checks. |
| [F16](#f16) | `UPSTREAM-FIX-PENDING` | no (memory safety) | #257 / PR #268 (dup PR #269 closed) | Watch PR #268; if closed unmerged, set FORK-FIX-REQUIRED and merge `fix/multimmc-binary-overread`. |
| [F18](#f18) | `NEEDS-FIX` | no (availability) | #259 (dup #266) / — | Fork fix: stat the path and refuse non-regular files. |
| [F19](#f19) | `NEEDS-FIX` | no (hostile/mistaken command line; report integrity) | #260 (dup #267) / — | Fork fix: checked multiplication, reject samples = 0, hash the loaded buffer. |
| [N-01](#n-01) | `NEEDS-FIX` | yes (IID wrongly accepted: 1.42× in the novel audit, +38 % in phase 2) | — / — | Recommended to file upstream (report draft A). Fork fix: treat m < 2 as a failure in chi_square_tests. |
| [N-02](#n-02) | `NEEDS-FIX` | yes (IID wrongly accepted; h′ 2.47× in repro) | #271 / — | Watch #271. Fork fix: pass `data.bsymbols, data.blen, 2` to the three batteries under -c, or refuse -c. |
| [N-03](#n-03) | `NEEDS-FIX` | no (correct h′ = 0) | — / — | Fork fix: guard blen < 2 / single-valued bitstring in computeEntropyOfConditionedData. |
| [N-04](#n-04) | `NEEDS-FIX` | no | — (#195 is a different path) / — | Fork fix: parse H_I with strtod + end-pointer + std::isfinite. |
| [N-05](#n-05) | `NEEDS-FIX` | no (report integrity) | — / — | Fork fix: reject contradictory arguments. |
| [N-06](#n-06) | `NEEDS-FIX` | no (report integrity / UB) | — / — | Fork fix: check sha256_file() and initialise the buffer. |
| [N-07](#n-07) | `NEEDS-FIX` | no (hardening) | — / — | Fork fix: hash the loaded buffer (shares the fix with F19). |
| [N-08](#n-08) | `NEEDS-FIX` | no (none or lower) | — (#260 is -l arithmetic) / — | Fork fix: a shared strict integer parser. |
| [N-09](#n-09) | `NEEDS-FIX` | no | — / — | Fork fix: check stream state after close and the fclose return. |
| [N-10](#n-10) | `NEEDS-FIX` | no | — / — | Fork fix: label/compute the fields correctly. |
| [N-11](#n-11) | `NEEDS-FIX` | no (low relevance) | — / — | Fork fix: validate n_in/n_out/nw against the supported exponent range. |
| [R-1](#r-1) | `FORK-FIX-REQUIRED` | no (abort, no JSON) | #246 (closed) / PR #248 (merged; incomplete) | Fork fix (upstream closed without fixing this path); optionally comment on #246. |
| [R-2](#r-2) | `FORK-FIX-REQUIRED` | no (TOO LOW: false failure) | #178 (closed) / — | Fork fix: add the >= 0 guards to the four folds. |
| [R-3](#r-3) | `FORK-FIX-REQUIRED` | no (report integrity) | #183 (closed) / — | Fork fix: set testRunIid.errorLevel and pass the IID run to read_file. |
| [NOVEL-01](#novel-01) | `NEEDS-FIX` | no by itself (it masks TOO-HIGH regressions) | #272 / — | Watch #272. Fork fix: extend the regex and accumulate the exit status. |
| [NOVEL-02](#novel-02) | `NEEDS-FIX` | no | — (distinct from PR #251) / — | Fork fix: assign only inside the computing branches. |
| [NOVEL-03](#novel-03) | `NEEDS-FIX` | no | — (introduced with PR #250) / — | Fork fix: separate test cases for rows and columns. |

## Confirmed findings

### F01

**Multi-bit data with exactly two observed values is assessed as binary; the n×H_bitstring term (§3.1.3) is never computed**

- **State:** `UPSTREAM-FIX-PENDING`
- **Dangerous direction:** yes (too HIGH: 0.9216 vs 0.1796)
- **Affected source:** `cpp/non_iid_main.cpp` main(): every bitstring branch is gated on `data.alph_size > 2` (lines 263, 285, 305, 325, 351, 375, 395, 419, 443, 467, 491); the same gate is in `cpp/iid_main.cpp`:280-299 (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "import random;r=random.Random(12345);b=[r.randrange(2) for _ in range(10**6)];open('t.bin','wb').write(bytes(2*x for x in b))"
  ./ea_non_iid -vv t.bin      # BUG: no 'Bitstring' lines; Assessed min entropy: 0.92162256445118362
  ./ea_non_iid -vv t.bin 8    # BUG: Assessed 0.92162256445118362
  ```
- **Expected (correct) behaviour:** Bitstring estimators run whenever the sample width n > 1: `t.bin` inferred 2-bit → Assessed 0.17960299911578648; declared 8 → 0.31779050350127225 (values measured on the PR #256 branch)
- **Evidence / reproducer:** [`AUDIT.md`](AUDIT.md) row F01 and its verification record; upstream #253
- **Regression test:** none yet — add: `t.bin` must report 0.17960299911578648 (inferred) and 0.31779050350127225 (declared 8)
- **Upstream NIST issue:** #253
- **Upstream NIST PR:** PR #256
- **Current upstream status:** issue open; PR open
- **Current fork status:** fix branch `fix/bitstring-gate-word-size` (tip `49089c8`, proposed upstream); not merged into fork `master`
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Watch PR #256. If it is closed unmerged, set FORK-FIX-REQUIRED and merge the fix branch into the fork with the regression test.

### F02

**Omitted bits_per_symbol: width inferred from the data narrows n and changes n×H_bitstring (up to 2.4×); inferred width not in JSON**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** yes (too HIGH vs the declared-width computation)
- **Affected source:** `cpp/shared/utils.h` read_file_subset() / read_file(): the "Do we need to establish the word size?" branch (lines 264-277 / 429-443); `cpp/non_iid_main.cpp`:492 uses `data.word_size`. Also reached from `ea_conditioning -i` (computeEntropyOfConditionedData sets `word_size = 0`) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "import random;r=random.Random(2);open('w4.bin','wb').write(bytes(r.randrange(16) for _ in range(10**6)))"
  ./ea_non_iid -vv w4.bin      # 16 distinct 4-bit-wide symbols; Assessed 3.7390649510685936
  ./ea_non_iid -vv w4.bin 8    # Assessed 1.53859949156400 (last digits vary by platform: 1.5385994915639978 / 1.5385994915640164)
  ```
- **Expected (correct) behaviour:** The width used for n must be the submitter-documented sample width (§3.2.2 req. 6). Inference must not silently change it, and the JSON must record the width used. Which width is normative is a maintainer decision.
- **Evidence / reproducer:** [`AUDIT.md`](AUDIT.md) row F02; upstream #254
- **Regression test:** none yet — add: JSON records the width used; an inferred width that is narrower than declared is flagged
- **Upstream NIST issue:** #254
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Check #254 for a maintainer decision. Without one, fork fix: record `word_size` (and whether it was inferred) in JSON and warn; consider requiring bits_per_symbol.

### F03

**Sub-minimum sample counts (< 10^6) produce a figure with JSON errorLevel 0 and no message**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** yes (a figure is emitted for non-conforming data)
- **Affected source:** `cpp/non_iid_main.cpp`:245 (stdout warning only); `cpp/shared/test_run_base.h` TestRunBase::GetBaseJson() (errorMessage emitted only when errorLevel != 0) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "import random;r=random.Random(777);P=3000;p=[r.randrange(2) for _ in range(P)];open('p2000.bin','wb').write(bytes(p[i%P] for i in range(2000)))"
  ./ea_non_iid -q -o o.json p2000.bin   # BUG: o.json errorLevel 0, no errorMessage
  ./ea_non_iid -vv p2000.bin            # Assessed 0.61486314415516563 (same source at 10^6: 1.29e-06)
  ```
- **Expected (correct) behaviour:** The JSON report flags a sample count below the §3.1.1 minimum (warning field or non-zero errorLevel)
- **Evidence / reproducer:** [`AUDIT.md`](AUDIT.md) row F03; upstream #255
- **Regression test:** none yet — add: p2000.bin JSON carries the sub-minimum flag
- **Upstream NIST issue:** #255 (related #238)
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix if upstream stays silent: add a machine-readable warning to the JSON.
- **Notes:** Filed with F05

### F04

**Literal MultiMCW skipped for 64 ≤ L ≤ 4095 although §6.3.7 defines it for L > 63; warning text off by one**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** yes (a missing estimator can only raise the minimum)
- **Affected source:** `cpp/non_iid/multi_mcw_test.h` multi_mcw_test(): `if(len < W[NUM_WINS-1]+1) return -1.0;` (lines 16-19) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "import random;r=random.Random(9);open('m4095.bin','wb').write(bytes(r.randrange(256) for _ in range(4095)))"
  python3 -c "import random;r=random.Random(9);open('m4096.bin','wb').write(bytes(r.randrange(256) for _ in range(4096)))"
  ./ea_non_iid -vv m4095.bin 8   # BUG: Literal MultiMCW absent; 'need more than 4096'
  ./ea_non_iid -vv m4096.bin 8   # MultiMCW runs
  ```
- **Expected (correct) behaviour:** MultiMCW runs for every L > 63, with windows larger than i sitting out (step 3a.ii, frequent_j = Null); the message states the enforced threshold
- **Evidence / reproducer:** [`AUDIT.md`](AUDIT.md) row F04; upstream #258 (reproduction section)
- **Regression test:** none yet — add: m4095.bin prints a Literal MultiMCW estimate
- **Upstream NIST issue:** #258 (dup #265)
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: remove the 4096 guard and implement Null windows per §6.3.7; compare against a literal reference.

### F05

**Estimators that cannot run (−1) are silently dropped from the minimum and from the JSON; reachable at 10^6 (de Bruijn LRS v < u)**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** yes (unbounded in principle)
- **Affected source:** `cpp/non_iid_main.cpp`: the `if (ret_min_entropy >= 0)` / `bin_lrs_res >= 0.0` guards (lines 327-340, 353-385, 397-483); `cpp/shared/test_case_base.h` TestCaseBase::GetBaseJson() (the −1 sentinel omits the key) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "import random;r=random.Random(777);P=3000;p=[r.randrange(2) for _ in range(P)];open('p2000.bin','wb').write(bytes(p[i%P] for i in range(2000)))"
  ./ea_non_iid -q -o o.json p2000.bin      # BUG: compression and MultiMCW test cases carry no value; errorLevel 0
  python3 ../audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py 100 11 db100.bin   # 10^6 samples
  ./ea_non_iid -vv -o db.json db100.bin 8   # BUG: 'LRS Estimate: v<u. Can't Run LRS Test.'; db.json errorLevel 0
  ```
- **Expected (correct) behaviour:** The report lists every estimator that could not run and flags it (warning or errorLevel)
- **Evidence / reproducer:** [`AUDIT.md`](AUDIT.md) row F05; [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §4 (F05 at 10^6); upstream #255
- **Regression test:** none yet — add: JSON lists skipped estimators for p2000.bin and db100.bin
- **Upstream NIST issue:** #255
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: record skipped estimators in the JSON test cases and set a warning.

### F09

**Generic MultiMMC: a Null prediction from the winning sub-predictor does not reset the run of correct predictions (r over-counted)**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (TOO LOW: MultiMMC 0.0021 vs 0.93; assessed figure unchanged)
- **Affected source:** `cpp/non_iid/multi_mmc_test.h` multi_mmc_test() generic path: `run_len = 0` only inside `if(found_x)` (lines 211-228) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/novel-findings/generators/noniid/f09gen.py 3 300 f09b.bin   # needs fillsteps.py from the same dir; SHA-256 1e2ae594…c534
  ./ea_non_iid -vv f09b.bin 8   # BUG: Literal MultiMMC r = 6603
  ```
- **Expected (correct) behaviour:** §6.3.9: a Null prediction is incorrect, so r = 24 (literal reference: `novel-findings/oracle/noniid/ref90b.py`, `novel-findings/repro/noniid/h/`)
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §4; `novel-findings/logs/noniid/out/f09b_run1.txt`; `novel-findings/agent-reports/noniid-estimators.md` §3a
- **Regression test:** none yet — add: f09b.bin must give MultiMMC r = 24
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Decide whether to file upstream; fork fix: reset `run_len` when the winner has no prediction.

### F11

**Compression estimate admits exactly 1001 blocks (v = 1): σ̂ divides by v−1 = 0 → NaN (reports 1.0) or inf (−0)**

- **State:** `UPSTREAM-FIX-PENDING`
- **Dangerous direction:** tiny inputs only (NaN case reports 1.0)
- **Affected source:** `cpp/non_iid/compression_test.h` compression_test(): guard `num_blocks <= d` (lines 106-109); σ̂ at line 131 (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 - <<'PY'
  import random
  r=random.Random(11); bits=[r.randrange(2) for _ in range(6006)]
  A=bits[:]; A[6000:6006]=A[5994:6000]
  B=bits[:]; B[6000:6006]=[1-x for x in B[5994:6000]]
  open('v1_nan.bin','wb').write(bytes(A)); open('v1_inf.bin','wb').write(bytes(B))
  PY
  ./ea_non_iid -vv v1_nan.bin 1   # BUG: Literal Compression Estimate: sigma-hat = -nan, min entropy = 1
  ./ea_non_iid -vv v1_inf.bin 1   # BUG: sigma-hat = inf, min entropy = -0
  ```
- **Expected (correct) behaviour:** The estimate requires v ≥ 2 test blocks (§6.3.4 step 5 divides by v−1); with fewer, it is refused and reported as skipped
- **Evidence / reproducer:** upstream #263 (reproduction); [`AUDIT.md`](AUDIT.md) row F11
- **Observed output (second verification pass, fork `master` build, macOS arm64, Apple clang 21; the Reproduce block above quotes a Linux GCC run, which prints `-nan` where clang prints `nan`):**
  ```
  v1_nan.bin   Literal Compression Estimate: X-bar = 0
               Literal Compression Estimate: sigma-hat = nan
               Literal Compression Estimate: X-bar' = nan
               Literal Compression Estimate: Could Not Find p. Proceeding with the lower bound for p.
               Literal Compression Estimate: p = 0.015625
               Literal Compression Estimate: min entropy = 1
               Assessed min entropy: 0.80718158433086451     (other estimators bind, so the 1.0 does not reach the figure)

  v1_inf.bin   Literal Compression Estimate: X-bar = 7.1799090900149345
               Literal Compression Estimate: sigma-hat = inf
               Literal Compression Estimate: X-bar' = -inf
               Literal Compression Estimate: Found p.
               Literal Compression Estimate: p = 1
               Literal Compression Estimate: min entropy = -0
               Assessed min entropy: -0                       (becomes the whole reported figure)
  ```
  For comparison: 1000 blocks are refused by the existing guard, and 1002 blocks give a finite sigma-hat = 1.8930014049997954.
- **Correction history:** A first verification pass recorded this finding as "DID NOT REPRODUCE (dangerous direction)", on the grounds that the 0/0 NaN branch needs degenerate data and that it was not filed. A second verification pass superseded both points: the input above is 6006 **random** bits with only the final 6-bit block edited, which is not degenerate data, and both branches reproduce. It was filed upstream as #263 with fix PR #270. [`AUDIT.md`](AUDIT.md) row F11 carries the same correction.
- **Regression test:** none yet — add: v1_nan.bin / v1_inf.bin report the compression estimate as not run
- **Upstream NIST issue:** #263
- **Upstream NIST PR:** PR #270
- **Current upstream status:** issue open; PR open
- **Current fork status:** fix branch `fix/compression-min-test-blocks` (tip `4401e93`, proposed upstream); not merged into fork `master`
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Watch PR #270; if closed unmerged, set FORK-FIX-REQUIRED and merge `fix/compression-min-test-blocks`.

### F12

**Collision estimate with v ≤ 1 (2–5 binary samples): σ̂ = NaN and the estimator prints min-entropy 1 unmeasured**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** estimator-level only (tiny inputs; later estimators abort)
- **Affected source:** `cpp/non_iid/collision_test.h` collision_test(): σ̂ at line 40 with no minimum v; NaN falls through the X<2.0 / X<2.5 tests (lines 40-72) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "open('b5.bin','wb').write(bytes([0,1,1,0,1]))"
  stdbuf -o0 ./ea_non_iid -vv b5.bin 1   # BUG: Literal Collision Estimate: v = 1, sigma-hat = -nan, min entropy = 1
  # the run then aborts at lz78y_test.h:17 (F15); stdbuf keeps the Collision lines when the output is piped
  ```
- **Expected (correct) behaviour:** Collision estimate refused (reported as not run) when v < 2
- **Evidence / reproducer:** upstream #264 (reproduction); [`AUDIT.md`](AUDIT.md) row F12
- **Correction history:** A first verification pass recorded this finding as "DID NOT REPRODUCE", on the grounds that no dangerous figure arises in any configuration, and did not file it. A second verification pass superseded that framing: the estimator does print `min entropy = 1` from an unmeasured NaN comparison (quoted in the Reproduce block above) before the run aborts at `lz78y_test.h:17`, so the value is produced and would enter the reported minimum if those aborts were ever turned into skips. It was filed upstream as #264 with exactly that caveat. [`AUDIT.md`](AUDIT.md) row F12 carries the same correction.
- **Regression test:** none yet — add: b5.bin collision reported as not run
- **Upstream NIST issue:** #264
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: require v ≥ 2 and return −1 (skipped) otherwise.

### F14

**Compression dict[] stores block indices in unsigned int: above 2^32 blocks D_i inflates and the estimate becomes 1.0**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** yes (only above 25.8 Gbit of input)
- **Affected source:** `cpp/non_iid/compression_test.h`:97 `unsigned int dict[]` (upstream `87c104d`)
- **Reproduce:**
  ```sh
  # harness: novel-findings/repro/num/f14/f14.cpp with novel-findings/repro/num/src/non_iid/compression_test_w.h
  # end-to-end needs > 2^32 blocks (> 25.77 Gbit) and ~650 GB RAM; the harness calls the unmodified function
  # on 2^32 + 10^9 blocks (memfd) and gets 1.0 vs 0 for the control (625 s x2)
  ```
- **Expected (correct) behaviour:** Block indices stored in a 64-bit type (`long dict[]`); the estimate is unchanged by input size
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §4; `novel-findings/logs/noniid/out/f14_big.log`, `f14_mid.log`
- **Regression test:** none yet — add: static check or harness run confirming 64-bit indices
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30: not run end to end (needs > 25.8 Gbit of input and ~650 GB RAM); mechanism shown by the harness in the original audit
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Low priority. Fork fix: change the element type to a 64-bit integer; no practical end-to-end test.
- **Notes:** Latent in the size range #217/#226 enabled

### F15

**assert() aborts (no message, no JSON) on tiny or repeat-free inputs; asserts are live in the shipped build**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no
- **Affected source:** `cpp/shared/lrs_test.h`:149 SAalgs32 `assert((v>0) && (v < n))`; `cpp/non_iid/multi_mmc_test.h`:21 `assert(L>3)`; `cpp/non_iid/lz78y_test.h`:17-18; `cpp/shared/most_common.h`:14 (upstream `87c104d`)
- **Reproduce:**
  ```sh
  printf '\x00\x01' > f2.bin; ./ea_non_iid f2.bin                                     # lrs_test.h:149
  python3 -c "open('f3.bin','wb').write(bytes([0,1,0]))"; ./ea_non_iid f3.bin          # multi_mmc_test.h:21
  python3 -c "open('f17.bin','wb').write(bytes([i&1 for i in range(17)]))"; ./ea_non_iid f17.bin   # lz78y_test.h:18
  ```
- **Expected (correct) behaviour:** Input length and repeat structure validated at intake; refusal with a message and JSON errorLevel −1
- **Evidence / reproducer:** upstream #261 (reproductions); [`AUDIT.md`](AUDIT.md) row F15
- **Regression test:** none yet — add: each input exits cleanly with a message
- **Upstream NIST issue:** #261 (dup #262)
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: validate minimum lengths before estimators run; keep the asserts as internal checks.
- **Notes:** N-03 is a separate ≥10^6 path

### F16

**Binary MultiMMC reads one byte past the sample buffer for 4 ≤ L ≤ 16 (heap over-read)**

- **State:** `UPSTREAM-FIX-PENDING`
- **Dangerous direction:** no (memory safety)
- **Affected source:** `cpp/non_iid/multi_mmc_test.h` binaryMultiMMCPredictionEstimate(): initialisation loop reads `S[d+1]` for d < 16 (lines 33-40; ASan at line 38) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  make non_iid CXXFLAGS='-std=c++11 -fopenmp -O1 -g -fsanitize=address,undefined -I/usr/include/jsoncpp'
  printf '\x00\x01\x00\x01\x00\x01\x00\x01' > f8.bin
  ./ea_non_iid f8.bin   # BUG: AddressSanitizer heap-buffer-overflow multi_mmc_test.h:38
  make non_iid          # restore the normal build
  ```
- **Expected (correct) behaviour:** No out-of-bounds read for any L (loop bounded by `d+1 < L`)
- **Evidence / reproducer:** upstream #257 (ASan trace); [`AUDIT.md`](AUDIT.md) row F16
- **Regression test:** none yet — add: ASan build clean for L ∈ {4,5,8,12,16}
- **Upstream NIST issue:** #257
- **Upstream NIST PR:** PR #268 (dup PR #269 closed)
- **Current upstream status:** issue open; PR #268 open
- **Current fork status:** fix branch `fix/multimmc-binary-overread` (tip `1bb4468`, proposed upstream); not merged into fork `master`
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Watch PR #268; if closed unmerged, set FORK-FIX-REQUIRED and merge `fix/multimmc-binary-overread`.

### F18

**sha256_file reads to EOF with no size/type check: hangs forever on /dev/zero, /dev/urandom, FIFOs**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (availability)
- **Affected source:** `cpp/shared/TestRunUtils.h` sha256_file(): `while(!feof(file))` loop (lines 100-116); called before read_file_subset in every main (upstream `87c104d`)
- **Reproduce:**
  ```sh
  timeout 6 ./ea_non_iid /dev/zero; echo "exit=$?"   # BUG: exit=124, no output
  ```
- **Expected (correct) behaviour:** Non-regular files refused (fstat + S_ISREG) before hashing
- **Evidence / reproducer:** upstream #259; [`AUDIT.md`](AUDIT.md) row F18
- **Regression test:** none yet — add: /dev/zero exits promptly with an error
- **Upstream NIST issue:** #259 (dup #266)
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: stat the path and refuse non-regular files.

### F19

**-l index,samples: offset multiplication wraps, samples=0 ignores the index, and the recorded SHA-256 is of the whole file**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (hostile/mistaken command line; report integrity)
- **Affected source:** `cpp/shared/utils.h` read_file_subset(): `subsetIndex*subsetSize` unchecked and the `subsetSize == 0` sentinel (lines 209-222); `cpp/non_iid_main.cpp`:178-181 (whole-file hash) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  ./ea_non_iid -vv -l 2,9223372036854775808 ../bin/truerand_1bit.bin 1   # BUG: loads the whole file, not block 2
  ./ea_non_iid -q -o sub.json -l 4,1000 ../bin/truerand_1bit.bin 1       # BUG: sub.json sha256 = whole-file hash
  ```
- **Expected (correct) behaviour:** Overflow and samples = 0 rejected; the JSON hash identifies the assessed bytes
- **Evidence / reproducer:** upstream #260; [`AUDIT.md`](AUDIT.md) row F19
- **Regression test:** none yet — add: both commands refused / hash of subset recorded
- **Upstream NIST issue:** #260 (dup #267)
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: checked multiplication, reject samples = 0, hash the loaded buffer.
- **Notes:** N-07 (TOCTOU) has the same fix direction

### N-01

**Binary chi-square independence reports Passed when m = 1; SP 800-90B §5.2.3 says "If m is 1, the test fails"**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** yes (IID wrongly accepted: 1.42× in the novel audit, +38 % in phase 2)
- **Affected source:** `cpp/iid/chi_square_tests.h` binary_chi_square_independence(): `if (m < 2) { score = 0.0; df = 0; return; }` (lines 485-489); chi_square_tests() :649 p-value of (0,0) = 1, :664 fails only if p < 0.001 (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 - <<'EOF'
  import random
  for n in (3162,3163):
      r=random.Random(n); b=bytearray(1000000)
      for i in r.sample(range(1000000),n): b[i]=1
      open(f'ones_{n}.bin','wb').write(b)
  EOF
  ./ea_iid -vvv ones_3162.bin 1 | grep -E 'independence|Chi square tests'   # BUG: T = 0, df = 0, P-value = 1; Chi square tests: Passed
  ./ea_iid -vvv ones_3163.bin 1 | grep -E 'independence|Chi square tests'   # df = 2 (boundary)
  ```
- **Expected (correct) behaviour:** m = 1 makes the chi-square battery fail, so the data is not IID (non-IID track: ea_non_iid gives 0.003068 for ones_3162.bin)
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-01; `novel-findings/repro/verify/ones3162_iid.json`, `ones3162_iid.log`, `ones3162_non.log`; `phase2-focused/logs/evidence/json/iid_p002.1.json`
- **Regression test:** none yet — add (from report): ones_3162.bin must fail the chi-square tests; ones_3163.bin computes df = 2
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Recommended to file upstream (report draft A). Fork fix: treat m < 2 as a failure in chi_square_tests.
- **Notes:** Also reachable via ea_restart -i

### N-02

**ea_iid -c runs the §5 IID tests on packed symbols instead of the conditioned binary string (§3.1.1 item 2, §3.1.5.2)**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** yes (IID wrongly accepted; h′ 2.47× in repro)
- **Affected source:** `cpp/iid_main.cpp` main(): under `-c` h′ comes from `data.bsymbols` (:282) but chi_square_tests (:316), len_LRS_test (:334) and permutation_tests (:352) receive `data.symbols` (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "import random; r=random.Random(4242); open('nib_dup.bin','wb').write(bytes(((x<<4)|x) for x in (r.randrange(16) for _ in range(1000000))))"
  ./ea_iid -c -v -o c.json nib_dup.bin 8   # BUG: all IID tests pass, h' = 0.998640
  ./ea_non_iid -c -v nib_dup.bin 8         # h' = 0.403507 (true value 0.5)
  ```
- **Expected (correct) behaviour:** Under -c the IID tests run on the bitstring and fail for nib_dup.bin (control on the bitstring: independence p = 0, LRS fails)
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-02; `novel-findings/repro/verify/nibdup_iidc.json`, `nibdup_iidc.log`, `nibdup_nonc.log`, `nibbits.log`; `novel-findings/repro/n02-fresh/ISSUE-N02.md`
- **Regression test:** none yet — add (from report): ea_iid -c nib_dup.bin 8 must fail the IID tests
- **Upstream NIST issue:** #271
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Watch #271. Fork fix: pass `data.bsymbols, data.blen, 2` to the three batteries under -c, or refuse -c.

### N-03

**ea_conditioning -n -i on an all-zero conditioned dataset: assert abort, no JSON; with -DNDEBUG a heap over-read and a wild write**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (correct h′ = 0)
- **Affected source:** `cpp/conditioning_main.cpp` computeEntropyOfConditionedData() (lines 364-384, no single-symbol/length guard); `cpp/shared/utils.h` read_file_subset() infers word_size 0 → blen 0; `cpp/shared/most_common.h`:14 (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "open('zero1e6.bin','wb').write(bytes(1000000))"
  ./ea_conditioning -n 512 256 256 300 -i zero1e6.bin -o z.json   # BUG: Assertion 'len > 1' failed, rc 134, no z.json
  ```
- **Expected (correct) behaviour:** h′ = 0 (or a JSON refusal); never infer width 0; NDEBUG+ASan build clean
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-03; `novel-findings/logs/conditioning/ndebug/`
- **Regression test:** none yet — add (from report): zero1e6.bin gives h′ = 0 or a JSON refusal and the NDEBUG+ASan build is clean
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: guard blen < 2 / single-valued bitstring in computeEntropyOfConditionedData.

### N-04

**ea_restart accepts H_I = nan (passes both range checks) → float→int UB and out-of-bounds stack write → SIGSEGV; non-numeric H_I becomes 0**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no
- **Affected source:** `cpp/restart_main.cpp` main(): `H_I = atof(argv[0])` (:293), checks at :294 and :343 are false for NaN; simulateBound():127, simulateCount():92 `counts[(int)floor(u/p)]++` (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/phase2-focused/generators/gen_w.py w   # w/r8.bin = 10^6 random bytes
  ./ea_restart -n w/r8.bin 8 nan   # BUG: SIGSEGV, rc 139
  ./ea_restart -n w/r8.bin 8 abc   # BUG: accepted as 0 -> 'Validation Test Passed'
  ```
- **Expected (correct) behaviour:** Non-finite or non-numeric H_I refused (strtod with end check, isfinite)
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-04; `phase2-focused/logs/evidence/restart_HI_fuzz.log`; `novel-findings/logs/restart/data/nan_nan.txt`
- **Regression test:** none yet — add: nan/abc refused with a message
- **Upstream NIST issue:** — (#195 is a different path)
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: parse H_I with strtod + end-pointer + std::isfinite.

### N-05

**ea_conditioning JSON binds the -i file's name and SHA-256 to an h′ that did not come from it (CLI h′ given too, or vetted mode)**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (report integrity)
- **Affected source:** `cpp/conditioning_main.cpp` main(): hashes and records `-i` whenever given (:515-523); uses the CLI h′ when argc == 5 (:558-576); vetted mode never reads the file (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "import random;r=random.Random(8);open('cond8.bin','wb').write(bytes(r.randrange(256) for _ in range(125000)))"
  ./ea_conditioning -n 512 256 256 300 -i cond8.bin -o measured.json        # h_p 0.83447, h_out 213.625
  ./ea_conditioning -n 512 256 256 300 0.99 -i cond8.bin -o both.json   # BUG: same filename+sha256, h_p 0.99, h_out 253.44, errorLevel 0
  ```
- **Expected (correct) behaviour:** h′ together with -i (and -i under -v) rejected, or the JSON records the h′ source and omits an unused hash
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-05; `novel-findings/repro/verify/measured.json`, `both.json`, `vet.json`
- **Regression test:** none yet — add: both.json command refused or h′ source recorded
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: reject contradictory arguments.

### N-06

**sha256_file() failure ignored by every main: uninitialised stack bytes land in the JSON "sha256"**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (report integrity / UB)
- **Affected source:** `cpp/shared/TestRunUtils.h` sha256_file() returns −1 (:62); ignored at `cpp/non_iid_main.cpp`:179, `cpp/iid_main.cpp`:199, `cpp/restart_main.cpp`:247, `cpp/conditioning_main.cpp`:521; `char hash[65]` uninitialised (upstream `87c104d`)
- **Reproduce:**
  ```sh
  ./ea_conditioning -n 512 256 256 300 0.9 -i nope.bin -o nf.json   # BUG: rc 0, errorLevel 0 for a missing file; sha256 = uninitialised bytes
  ./ea_restart -n -o ne.json nope.bin 8 4                             # BUG: sha256 uninitialised
  # the sha256 content is undefined behaviour: garbage in most runs, the field omitted when the first byte happens to be 0.
  # rc 0 / errorLevel 0 from ea_conditioning is deterministic
  ```
- **Expected (correct) behaviour:** Return value checked; errorLevel/message set; hash zero-initialised
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-06; `novel-findings/repro/verify/nf1.json`, `nf2.json`; `phase2-focused/logs/evidence/json/ne.json`
- **Regression test:** none yet — add: missing file gives errorLevel −1 and no sha256 field
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: check sha256_file() and initialise the buffer.

### N-07

**TOCTOU: the hash pass and the data pass open the file separately, so a concurrent rewrite binds one file's hash to another file's figure**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (hardening)
- **Affected source:** `cpp/shared/TestRunUtils.h`:72 (hash fopen) vs `cpp/shared/utils.h`:181 (data fopen); same pattern in all four mains (upstream `87c104d`)
- **Reproduce:**
  ```sh
  gcc -shared -fPIC -o toctou_shim.so ../audits/2026-09-30/novel-findings/repro/verify/toctou_shim.c -ldl
  cp ../bin/truerand_8bit.bin t.bin
  TOCTOU_PATH=t.bin TOCTOU_SRC=../bin/biased-random-bytes.bin TOCTOU_N=2 LD_PRELOAD=./toctou_shim.so ./ea_non_iid -q -o toc.json t.bin 8
  # BUG: toc.json sha256 = truerand_8bit (c7e56911...) but hAssessed = 0.25774087100648113 (biased-random-bytes)
  ```
- **Expected (correct) behaviour:** The hash is computed over the buffer that is assessed
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-07; `novel-findings/repro/verify/toctou_shim.c`, `t1.json`, `t2.json`, `ctl.json`
- **Regression test:** none yet — add: shim run produces a hash matching the assessed bytes
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: hash the loaded buffer (shares the fix with F19).

### N-08

**Numeric CLI arguments parsed permissively (strtoull/strtoul base 0, atoi, no end check): -l 010 = block 8, bits "8x" = 8, n_out 0256 = 174**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (none or lower)
- **Affected source:** `cpp/non_iid_main.cpp`:120, :137, :186; `cpp/iid_main.cpp`:179; `cpp/restart_main.cpp`:265; `cpp/conditioning_main.cpp`:104; `cpp/transpose_main.cpp` -l parse (upstream `87c104d`)
- **Reproduce:**
  ```sh
  ./ea_non_iid -l 010,20000 ../bin/truerand_8bit.bin 8   # BUG: same as -l 8,20000 (6.36327), not -l 10,20000 (6.37041)
  ./ea_non_iid ../bin/truerand_8bit.bin 8x              # BUG: accepted as 8
  ./ea_conditioning -v 512 0256 256 300                   # BUG: n_out = 174
  ```
- **Expected (correct) behaviour:** Decimal-only parsing with end-pointer and errno checks; signs rejected
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-08; `novel-findings/logs/io/l_8,1000.json`, `l_010,1000.json`, `l_10,1000.json`
- **Regression test:** none yet — add: each command refused
- **Upstream NIST issue:** — (#260 is -l arithmetic)
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: a shared strict integer parser.

### N-09

**Output-file write failures never checked: -o /dev/full or a missing directory exits 0; ea_transpose can leave a truncated column file with exit 0**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no
- **Affected source:** every main: `ofstream` JSON writes never checked; `cpp/transpose_main.cpp`:112 `fclose` unchecked (upstream `87c104d`)
- **Reproduce:**
  ```sh
  ./ea_non_iid -o /dev/full ../bin/truerand_1bit.bin 1; echo $?             # BUG: 0
  ./ea_non_iid -o /nonexistent_dir/x.json ../bin/truerand_1bit.bin 1; echo $?   # BUG: 0
  ```
- **Expected (correct) behaviour:** Non-zero exit and a message when the report cannot be written
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-09; `novel-findings/logs/io/`
- **Regression test:** none yet — add: both commands exit non-zero
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: check stream state after close and the fclose return.

### N-10

**Reporting-only: ea_iid "Median" is of translated indices; conditioning JSON hard-codes "IID": false and omits vetted/track; restart -i JSON mean/median always 0.0**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no
- **Affected source:** `cpp/shared/utils.h` calc_stats() (median from `dp->symbols`); `cpp/non_iid/non_iid_test_run.h`:30 (IID const false, reused by conditioning_main.cpp:509); `cpp/restart_main.cpp` tcOverallIid mean/median never assigned (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/phase2-focused/generators/gen_w.py w
  python3 -c "import random;r=random.Random(8);open('cond8.bin','wb').write(bytes(r.randrange(256) for _ in range(125000)))"
  python3 -c "import random; r=random.Random(4242); open('nib_dup.bin','wb').write(bytes(((x<<4)|x) for x in (r.randrange(16) for _ in range(1000000))))"
  ./ea_iid -v nib_dup.bin 8 | grep -E 'Raw Mean|^[[:space:]]+Median:'     # BUG: Raw Mean 127.557987 beside Median 8.000000 (a translated index)
  python3 -c "d=sorted(open('nib_dup.bin','rb').read()); print((d[499999]+d[500000])/2)"   # the data median: 136.0
  ./ea_conditioning -n 512 256 256 300 -c iid -i cond8.bin -o x.json   # BUG: "IID": false
  ./ea_restart -i -o r.json w/r8.bin 8 7.5                              # BUG: "mean": 0.0, "median": 0.0
  ```
- **Expected (correct) behaviour:** Values reported with their true meaning; conditioning JSON records the track
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-10; `phase2-focused/logs/evidence/json/rst_i.json`
- **Regression test:** none yet — add: JSON fields as expected
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: label/compute the fields correctly.

### N-11

**ea_conditioning aborts (assert) for accepted n_in/n_out ≥ 1,073,741,823 (MPFR emax)**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no (low relevance)
- **Affected source:** `cpp/conditioning_main.cpp`:602 `assert(mpfr_get_emax() > maxval)`; inputs accepted up to UINT_MAX (upstream `87c104d`)
- **Reproduce:**
  ```sh
  ./ea_conditioning -v 1073741823 256 256 300   # BUG: Assertion 'mpfr_get_emax() > maxval' failed
  timeout 20 ./ea_conditioning -v 1073741822 256 256 300; echo "exit=$?"   # control: exit=124 (passes the emax check, still computing; no assert)
  ```
- **Expected (correct) behaviour:** Range-checked against emax (or mpfr_set_emax raised) with a clear refusal
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-11; `novel-findings/logs/conditioning/asanlogs/`
- **Regression test:** none yet — add: refusal message, no abort
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: validate n_in/n_out/nw against the supported exponent range.

### R-1

**Residual of #246: len_LRS_test asserts p_col ≥ 1/k and aborts when every symbol count is exactly equal and 1/k rounds down (k = 3, 6, 7, 9, 12, …)**

- **State:** `FORK-FIX-REQUIRED`
- **Dangerous direction:** no (abort, no JSON)
- **Affected source:** `cpp/shared/lrs_test.h`:626 len_LRS_test() `assert(p_col >= 1.0L / ((long double) k))`; `cpp/shared/utils.h` calc_proportions() (PR #248 fixed accumulation only) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 -c "import random;r=random.Random(7);a=[i%3 for i in range(1000002)];r.shuffle(a);open('bal3.bin','wb').write(bytes(a))"
  ./ea_iid bal3.bin 2   # BUG: lrs_test.h:626 assertion, rc 134, no JSON
  ```
- **Expected (correct) behaviour:** Completes normally (clamp p_col to 1/k when within rounding, or exact integer Σc²/L²)
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §3 R-1; `novel-findings/repro/verify/bal3_1.log`, `bal3_2.log`, `unbal3.json`
- **Regression test:** none yet — add: bal3.bin completes; also k = 6, 7, 12 (phase-2 gen_w.py bal_k*.bin)
- **Upstream NIST issue:** #246 (closed)
- **Upstream NIST PR:** PR #248 (merged; incomplete)
- **Current upstream status:** #246 closed (completed) without covering this case; residual not reported
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix (upstream closed without fixing this path); optionally comment on #246.

### R-2

**Residual of #178: ea_restart folds a t-tuple/LRS −1 ("cannot run") into H_r/H_c, giving a false restart failure**

- **State:** `FORK-FIX-REQUIRED`
- **Dangerous direction:** no (TOO LOW: false failure)
- **Affected source:** `cpp/restart_main.cpp` main(): `H_r = min(row_lrs_res, H_r)` etc. without the `>= 0` guard (:632, :636, :647, :651) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py 100 11 db100.bin
  ./ea_restart -vv db100.bin 8 0.5   # BUG: 'LRS Estimate: v<u', H_r: -1.000000, Validation Testing Failed
  # (numerics-asserts.md has the B(256,3) 10^6-prefix generator used by the coordinator: db256_3.bin)
  ```
- **Expected (correct) behaviour:** Estimates that could not run (−1) are excluded from H_r/H_c: db100.bin with H_I = 0.5 must not fail on H_r = −1; the coordinator's db256_3.bin passes with H_r = 0.585208
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §3 R-2; `novel-findings/repro/verify/dbr1.log`, `dbr2.log`; `novel-findings/agent-reports/numerics-asserts.md` (NUM-03)
- **Regression test:** none yet — add (from report): db100.bin and db256_3.bin with H_I = 0.5 pass validation (db256_3: H_r = 0.585208)
- **Upstream NIST issue:** #178 (closed)
- **Upstream NIST PR:** —
- **Current upstream status:** #178 closed (completed); restart path never patched; residual not reported
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: add the >= 0 guards to the four folds.

### R-3

**Regression of #183: ea_restart -i writes JSON errorLevel 0 on an input read failure (sets testRunNonIid, writes testRunIid; merge 4d68e47)**

- **State:** `FORK-FIX-REQUIRED`
- **Dangerous direction:** no (report integrity)
- **Affected source:** `cpp/restart_main.cpp` main(): read_file failure branch (:319-339), line 324 `testRunNonIid.errorLevel = -1` under `if (iid)` (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/phase2-focused/generators/gen_w.py w
  ./ea_restart -i -o r.json w/r8.bin 4 3.2; echo $?   # BUG: exit 255 but r.json "errorLevel": 0, no errorMessage
  ```
- **Expected (correct) behaviour:** errorLevel −1 with the read error message in the IID JSON
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §3 R-3; `novel-findings/repro/verify/r_iid.json`, `r_non.json`; `phase2-focused/logs/evidence/json/w4i.json`
- **Regression test:** none yet — add: r.json errorLevel −1
- **Upstream NIST issue:** #183 (closed)
- **Upstream NIST PR:** —
- **Current upstream status:** #183 closed (completed); regressed later by merge 4d68e47; not reported
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: set testRunIid.errorLevel and pass the IID run to read_file.

### NOVEL-01

**selftest never compares H_original, H_bitstring or "Assessed min entropy", and its exit status reflects only the last file**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no by itself (it masks TOO-HIGH regressions)
- **Affected source:** `cpp/selftest/compareresults.pl` resultsHash() (lines 65-66: keyword filter + `label = number` regex); `cpp/selftest/selftest` (lines 3-8: exit codes never combined) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  bash ../audits/2026-09-30/phase2-focused/repro/issue272/repro.sh   # fresh upstream clone; baseline, 2 mutants, refdata edit
  # BUG: every run prints identical 'Maximum delta' lines and exits 0 while the Assessed figures change
  ```
- **Expected (correct) behaviour:** Summary figures compared; any mismatching file makes ./selftest exit non-zero
- **Evidence / reproducer:** [`phase2-focused/REPORT.md`](phase2-focused/REPORT.md) NOVEL-01; `phase2-focused/repro/issue272/`; `phase2-focused/logs/issue272/`
- **Regression test:** none yet — add (from report): both mutants must make ./selftest exit non-zero
- **Upstream NIST issue:** #272
- **Upstream NIST PR:** —
- **Current upstream status:** issue open
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Watch #272. Fork fix: extend the regex and accumulate the exit status.
- **Notes:** Until fixed, check "Assessed min entropy" separately when running the selftest (e.g. `cpp/selftest/pin-check.sh`)

### NOVEL-02

**ea_iid JSON emits never-computed placeholders: hBitstring 1.0 for binary input, hOriginal = word size under -c**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no
- **Affected source:** `cpp/iid_main.cpp` main(): `H_original = data.word_size`, `H_bitstring = 1.0` assigned to tc unconditionally (lines 272-284) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/phase2-focused/generators/gen_w.py w
  ./ea_iid -q -o a.json w/iid_p002.bin 1   # BUG: "hBitstring": 1.0
  ./ea_iid -c -q -o b.json w/r8.bin 8      # BUG: "hOriginal": 8.0
  ```
- **Expected (correct) behaviour:** Fields omitted when not computed (as ea_non_iid does)
- **Evidence / reproducer:** [`phase2-focused/REPORT.md`](phase2-focused/REPORT.md) NOVEL-02; `phase2-focused/logs/evidence/json/iid_p002.1.json`, `iid_c_r8.json`
- **Regression test:** none yet — add: a.json has no hBitstring; b.json has no hOriginal
- **Upstream NIST issue:** — (distinct from PR #251)
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: assign only inside the computing branches.

### NOVEL-03

**ea_restart -i JSON appends row and column permutation results under identical iteration labels (no row/column tag)**

- **State:** `NEEDS-FIX`
- **Dangerous direction:** no
- **Affected source:** `cpp/restart_main.cpp`:791, :800 both call permutation_tests(..., tcOverallIid); `cpp/iid/permutation_tests.h`:730 populateTestCase() (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/phase2-focused/generators/gen_w.py w
  ./ea_restart -i -q -o r.json w/r8.bin 8 7.5   # BUG: 6 permutationTestResults, iteration 0,1,2,0,1,2
  ```
- **Expected (correct) behaviour:** Separate, labelled row and column results
- **Evidence / reproducer:** [`phase2-focused/REPORT.md`](phase2-focused/REPORT.md) NOVEL-03; `phase2-focused/logs/evidence/json/rst_i.json`
- **Regression test:** none yet — add: r.json has labelled row/column blocks
- **Upstream NIST issue:** — (introduced with PR #250)
- **Upstream NIST PR:** —
- **Current upstream status:** not filed
- **Current fork status:** no fix in the fork
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Fork fix: separate test cases for rows and columns.

## Unconfirmed and not-a-bug items (not in the repair queue)

These are recorded so that nothing is lost. An `UNCONFIRMED` item enters the queue as `NEEDS-FIX` once verified; a `NOT-A-BUG` item re-enters only if its reason stops holding.

| ID | Title | Label | Reason (from the source report) | Evidence | Next action |
|---|---|---|---|---|---|
| F06 | Compression step 8 returns 1.0 when X̄′ exceeds the uniform expectation | `NOT-A-BUG` | Spec-literal behaviour (§6.3.4 step 8); weakness of the standard, not a code divergence. UNVERIFIED attacker claim. | AUDIT.md F06 | None (spec comment, not a code fix) |
| F07 | Z = 2.5758293 instead of the printed 2.576 | `NOT-A-BUG` | Deliberate full precision, closed upstream #22; ≤ 5e-6 bit/bit. | AUDIT.md F07; #22 | None |
| F08 | P_local recurrence iterated to convergence instead of x = x₁₀ | `NOT-A-BUG` | Deliberate upstream change (#133, PR #134 merged); effect < 1e-10. UNVERIFIED. | AUDIT.md F08 | None |
| F10 | Generic MultiMMC chained lookup skips deeper orders | `UNCONFIRMED` | Mechanism shown with an instrumented copy; no C/r effect at the shipped constants. Needs more work. | novel-findings/agent-reports/noniid-estimators.md; novel-findings/repro/noniid/instr/ | Verify whether any shipped-constant input changes C or r; promote to NEEDS-FIX if so |
| F13 | NaN folded by std::min discards earlier minima | `UNCONFIRMED` | No NaN producer at ≥ 10^6 in any tool (novel-findings audit); tiny-input producers are F11/F12. | AUDIT.md F13; novel-findings/REPORT.md §4 | Treat as hardening when fixing F11/F12 |
| F17 | LRS stage quadratic on inputs with long repeats | `NOT-A-BUG` | Cost inherent to §6.3.6 when v ≈ L; maintainers closed #214/#163/#52 as working correctly. | AUDIT.md F17 | None |
| F20 | -t truncation also applied under -c | `NOT-A-BUG` | Documented option semantics per maintainer position in #127/#139/#140. | AUDIT.md F20; novel-findings/REPORT.md §4 | Re-open only if the §3.1.5.2 reading changes |
| F21 | MSB-first bit order within a symbol changes H_bitstring | `NOT-A-BUG` | The spec does not fix bit order (convention; #71 discussion). UNVERIFIED. | AUDIT.md F21 | None |
| F22 | H_bitstring built from raw values (encoding-dependent) | `NOT-A-BUG` | Spec-consistent per AUDIT. UNVERIFIED. | AUDIT.md F22 | None |
| F23 | Reporting: JSON keeps literal MCV intermediates only; -c hAssessed = n×h′; text rounding | `UNCONFIRMED` | Partly reproduces; partly covered by #179 and PR #251. | AUDIT.md F23; novel-findings/REPORT.md §4 | Verify each sub-claim; file the unique part |
| F24 | prediction_estimate_function: FMA NaN vs −inf near x = 1/p | `NOT-A-BUG` | Guard decision unchanged in all tested states (AUDIT). UNVERIFIED. | AUDIT.md F24 | None |
| F25 | calc_p_local termination guarantee for very large N | `UNCONFIRMED` | Theoretical beyond the measured range. | AUDIT.md F25; BUILDING.md precision audit | Test at N ≈ 2^31 if large inputs matter |
| F26 | Markov estimate has no confidence adjustment | `NOT-A-BUG` | Matches the final spec (§6.3.3 has no ε term). | AUDIT.md F26 | None |
| F27 | Appendix G.2 Table 3 row labels offset by 5 | `NOT-A-BUG` | Spec erratum, not code. | AUDIT.md F27 | None (spec erratum) |
| F28 | Deterministic sources with long memory score near full entropy | `NOT-A-BUG` | Spec limitation of the estimator battery, not code. | AUDIT.md F28 | None |
| F29 | Single-estimator blind spots | `NOT-A-BUG` | Spec limitation; the battery minimum covers them. | AUDIT.md F29 | None |
| F30 | LRS estimates collision entropy (can exceed min-entropy) | `NOT-A-BUG` | Spec says so explicitly; other estimators bound the figure. | AUDIT.md F30 | None |

## Other upstream items referenced by the audits (known; not audit findings)

| Upstream item | What the audits recorded | Status (2026-09-30) |
|---|---|---|
| #153 | IID LRS test aborts at `assert(p_colPower >= LDBL_MIN)` on one duplicated ≥ 2,049-byte region; detection by design | closed |
| #195 | ea_restart `k_effective` assertion | open |
| #251 (PR) | ea_iid JSON `hAssessed` computed only at `-vvv` | open |
| #252 (PR) | ea_iid / restart `-i` report a figure when IID tests fail; `"IID": true` constant | open |
| #262, #265, #266, #267 | duplicates of #261, #258, #259, #260 | closed (not planned) |
| #269 (PR) | duplicate of PR #268 | closed |
| #56, #95, #209, PR #224 | restart cutoff by simulation instead of the literal binomial rule (intended deviation) | closed |
| #236 / PR #237 | manually maintained VERSION macro (tag v1.1.8 prints 1.1.7) | #236 open |

## Sources

- F-series: [`AUDIT.md`](AUDIT.md), the first-wave audit, with rows re-assessed in §4 of the novel-findings report.
- N/R-series: [`novel-findings/REPORT.md`](novel-findings/REPORT.md).
- NOVEL-series: [`phase2-focused/REPORT.md`](phase2-focused/REPORT.md).
- Upstream states: read from GitHub on 2026-09-30.
