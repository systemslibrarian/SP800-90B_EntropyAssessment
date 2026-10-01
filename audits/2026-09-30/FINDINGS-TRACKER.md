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

Since 2026-09-30 each repaired finding also carries two further fields, so that
NIST's position and this fork's position are never conflated:

| Upstream disposition | Meaning |
|---|---|
| `ACCEPTED` | NIST agreed it is a defect and agreed with the remedy. |
| `ACCEPTED-DIFFERENT-FIX` | NIST agreed something is wrong but prefers a different remedy, usually enforcing the 1,000,000-sample minimum. |
| `DISPUTED` | NIST does not agree it is a defect. Fork behaviour is not changed to match our reading while this stands. |
| `HARDENING-NOT-BUG` | NIST regards it as abnormal input rather than a defect. |
| `LOW-PRIORITY` | NIST has no objection to a fix but does not consider it important. |
| `PENDING` | Filed, no substantive NIST response yet. |
| `NOT-FILED` | A confirmed defect that has not been reported upstream. The fork may still repair it; doing so is not a statement about NIST's view. |

| Fork disposition | Meaning |
|---|---|
| `NEEDS-FIX` | Not repaired here. |
| `FIX-IN-PROGRESS` | Being repaired now. |
| `VERIFIED` | Repaired here, with a regression test that fails against the pre-fix build. |
| `RESOLVED-BY-GLOBAL-GUARD` | Unreachable through ordinary use because of the Section 3.1.1 intake check; any estimator-level guard is recorded separately. |
| `SPEC-INTERPRETATION-PENDING` | Held: the behaviour turns on a reading of the standard that NIST has not settled. The fork follows upstream unchanged. |
| `FORK-HARDENING` | Repaired here as robustness, not as a standards defect. |
| `DEFERRED-NOT-BUILT` | In a program this fork does not build (ea_conditioning), so a repair could not be reproduced or regression-tested here. |
| `NOT-REPRODUCED-HERE` | Confirmed elsewhere but does not reproduce on this platform; a repair cannot be regression-tested here. |

**Resolution rule.** A confirmed bug is resolved only when (A) the relevant upstream code is actually corrected and the regression test passes, or (B) this fork contains the correction and a regression test proving it. If upstream closes, rejects or abandons a confirmed bug without fixing it, its state becomes `FORK-FIX-REQUIRED`.

## Queue summary (upstream status last checked 2026-09-30)

- Confirmed defects: **30**.
  - `NEEDS-FIX`: 7
  - `UPSTREAM-FIX-PENDING`: 1
  - `FIXED-UPSTREAM-VERIFY`: 0
  - `FORK-FIX-REQUIRED`: 1
  - `FORK-FIXED`: 21
  - `VERIFIED`: 0

  Fork disposition across all 30: `VERIFIED` 18, `RESOLVED-BY-GLOBAL-GUARD` 2,
  `FORK-HARDENING` 1, `DEFERRED-NOT-BUILT` 3, `NOT-REPRODUCED-HERE` 1,
  `SPEC-INTERPRETATION-PENDING` 1, `NEEDS-FIX` 4.

  `FORK-FIXED` is a state, not a quality claim, and the 21 are not all the
  same kind of thing. Read them by fork disposition:

  - **18 `VERIFIED`** — repaired here, each with a regression test that fails
    against the pre-fix build.
  - **2 `RESOLVED-BY-GLOBAL-GUARD`** (F03, F04) — *not* corrected. The
    underlying behaviour is unchanged; the Section 3.1.1 intake check makes it
    unreachable through ordinary use. If that check were ever relaxed, these
    return.
  - **1 `FORK-HARDENING`** (F18) — fixed here as robustness. NIST does not
    regard it as a defect and it must not be cited as one.

  They came from two passes on 2026-09-30: 11 from the first, 10 from the
  second, after NIST's review.

  Of the 9 not fixed: 3 are in ea_conditioning, which this fork does not build;
  1 does not reproduce on this platform (R-1, a long double width question);
  1 is held pending NIST's reading (F01); and 4 remain open work (N-07, N-08,
  N-10, NOVEL-03), each with its next step recorded.

  No upstream issue or pull request was modified in either pass.
- Unconfirmed or not-a-bug items (not in the queue): **17**; see the end of this file.
- All commands below run from `cpp/` of this fork after `make`. **The fork's C++ sources are no longer identical to upstream `87c104d`.** They were when this file was written; two repair passes on 2026-09-30 then corrected defects in `cpp/shared/`, `cpp/non_iid/`, `cpp/iid/` and the `*_main.cpp` programs, each listed in [`../../NOTICE`](../../NOTICE) with its commit and recorded against its finding below. Line references in findings that predate those passes may therefore be a few lines out, and a reproduction may now show the repaired behaviour rather than the `BUG:` line: check the finding's own state before concluding anything from a reproduction that no longer fails. `../audits/2026-09-30/` holds the generators and evidence. Evidence paths are relative to this file.
- Reproduction audit (2026-09-30): every Reproduce block below was re-run, unmodified, on a clean build of fork `master` `237d85c`; 29 of 30 show the stated `BUG:` output. The exception is **F14**. Its harness (`novel-findings/repro/num/f14/`) demonstrates the mechanism on the unmodified function, but an end-to-end run needs more than 25.8 Gbit of input and about 650 GB RAM.

| ID | State | Dangerous direction? | Upstream issue / PR | Next action |
|---|---|---|---|---|
| [F01](#f01) | `UPSTREAM-FIX-PENDING` | yes (too HIGH: 0.9216 vs 0.1796) | #253 / PR #256 | Obtain one clarification before doing anything: when bits_per_symbol is declared explicitly as 8 for a two-value alphabet such as {33, 211}, is the dataset still binary for the purposes of §3.1.3, so that the n x H_bitstring term is correctly omitted? If yes, record that reading and close #253 and PR #256. If no, the gate needs to distinguish declared width from observed alphabet. Do not merge PR #256 into the fork until this is answered. |
| [F02](#f02) | `FORK-FIXED` | yes (too HIGH vs the declared-width computation) | #254 / — | None in this fork. The default-width question stays with NIST on #254. |
| [F03](#f03) | `FORK-FIXED` | yes (a figure is emitted for non-conforming data) | #255 (related #238) / — | None for the sub-minimum half. How a legitimate no-estimate result should appear is tracked separately as F05. |
| [F04](#f04) | `FORK-FIXED` | yes (a missing estimator can only raise the minimum) | #258 (dup #265) / — | None unless NIST decides §6.3.7 should run for L > 63, which would be a behaviour change this fork should not make first. |
| [F05](#f05) | `FORK-FIXED` | yes (unbounded in principle) | #255 / — | None. |
| [F09](#f09) | `FORK-FIXED` | no (TOO LOW: MultiMMC 0.0021 vs 0.93; assessed figure unchanged) | — / — | None. |
| [F11](#f11) | `FORK-FIXED` | tiny inputs only (NaN case reports 1.0) | #263 / PR #270 | Watch PR #270. If NIST prefers to rely only on the intake minimum, the local guard can stay as defence in depth. |
| [F12](#f12) | `FORK-FIXED` | estimator-level only (tiny inputs; later estimators abort) | #264 / — | None. |
| [F14](#f14) | `FORK-FIXED` | yes (only above 25.8 Gbit of input) | — / — | An end-to-end confirmation would need a machine with the memory for it. |
| [F15](#f15) | `FORK-FIXED` | no | #261 (dup #262) / — | None. |
| [F16](#f16) | `FORK-FIXED` | no (memory safety) | #257 / PR #268 (dup PR #269 closed) | PR #268 still carries the one-line bound. Decide with NIST whether to update it to the failure return or close it in favour of the intake minimum. Nothing was changed upstream from this fork. |
| [F18](#f18) | `FORK-FIXED` | no (availability) | #259 (dup #266) / — | None. Do not present this as a NIST-accepted defect. |
| [F19](#f19) | `FORK-FIXED` | no (hostile/mistaken command line; report integrity) | #260 (dup #267) / — | None. |
| [N-01](#n-01) | `FORK-FIXED` | yes (IID wrongly accepted: 1.42× in the novel audit, +38 % in phase 2) | — / — | None in the fork. Consider reporting upstream. |
| [N-02](#n-02) | `FORK-FIXED` | yes (IID wrongly accepted; h′ 2.47× in repro) | #271 / — | None. Note the cost: under -c -a with multi-bit symbols the permutation battery now runs on eight times as much data and did not finish in 40 minutes on a 1,000,000-sample 8-bit file; -t bounds it. |
| [N-03](#n-03) | `NEEDS-FIX` | no (correct h′ = 0) | — / — | Decide whether to build ea_conditioning locally for test purposes. Building it for testing does not change what the fork ships, but it is the owner's call. |
| [N-04](#n-04) | `FORK-FIXED` | no | — (#195 is a different path) / — | None. |
| [N-05](#n-05) | `NEEDS-FIX` | no (report integrity) | — / — | Same decision as N-03. |
| [N-06](#n-06) | `FORK-FIXED` | no (report integrity / UB) | — / — | Decide whether to build ea_conditioning for test purposes; until then its instance stands. |
| [N-07](#n-07) | `NEEDS-FIX` | no (hardening) | — / — | Decide the shape first: keep sha256 as the whole-file hash and add a second, separately named digest of the assessed buffer, or re-read and compare. Do not silently redefine sha256. |
| [N-08](#n-08) | `NEEDS-FIX` | no (none or lower) | — (#260 is -l arithmetic) / — | Parse every numeric argument decimal-only with an end-pointer and errno check, rejecting signs where a count is expected. Mechanical but it touches five files. |
| [N-09](#n-09) | `FORK-FIXED` | no | — / — | The two programs this fork does not build still carry the defect. |
| [N-10](#n-10) | `NEEDS-FIX` | no | — / — | Decide per item whether the value or its label should change; the conditioning half waits on the N-03 decision. |
| [N-11](#n-11) | `NEEDS-FIX` | no (low relevance) | — / — | Same decision as N-03. |
| [R-1](#r-1) | `FORK-FIX-REQUIRED` | no (abort, no JSON) | #246 (closed) / PR #248 (merged; incomplete) | Reproduce on an x86-64 build with 80-bit long double, then fix (clamp p_col to 1/k within rounding, or compute the collision proportion as an exact integer ratio) with a regression that fails there. |
| [R-2](#r-2) | `FORK-FIXED` | no (TOO LOW: false failure) | #178 (closed) / — | None. |
| [R-3](#r-3) | `FORK-FIXED` | no (report integrity) | #183 (closed) / — | None. |
| [NOVEL-01](#novel-01) | `FORK-FIXED` | no by itself (it masks TOO-HIGH regressions) | #272 / — | None. Note that selftest now exits 1 on macOS arm64 because of the pre-existing platform deltas in upstream #155. |
| [NOVEL-02](#novel-02) | `FORK-FIXED` | no | — (distinct from PR #251) / — | Watch PR #251 for the upstream shape of the hAssessed half. |
| [NOVEL-03](#novel-03) | `NEEDS-FIX` | no | — (introduced with PR #250) / — | Give populateTestCase() a row/column tag, or use two test cases. Reporting-only; no figure changes. |

## Confirmed findings

### F01

**Multi-bit data with exactly two observed values is assessed as binary; the n×H_bitstring term (§3.1.3) is never computed**

- **State:** `UPSTREAM-FIX-PENDING`
- **Upstream disposition:** `DISPUTED`
- **Fork disposition:** `SPEC-INTERPRETATION-PENDING`
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
- **Current upstream status:** #253 open, PR #256 open, both untouched. @joshuaehill disputes the premise: "I'm not sure this actually is a problem as the whole issue seems to turn on the phrase 'If the sequential dataset is not binary' ... both are binary (that is there are two symbols in both alphabets). I think the current behavior is correct."
- **Current fork status:** HELD. The fork follows upstream behaviour unchanged and PR #256 is NOT merged here. Changing it would encode our reading of "binary" over NIST's while the question is open.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Obtain one clarification before doing anything: when bits_per_symbol is declared explicitly as 8 for a two-value alphabet such as {33, 211}, is the dataset still binary for the purposes of §3.1.3, so that the n x H_bitstring term is correctly omitted? If yes, record that reading and close #253 and PR #256. If no, the gate needs to distinguish declared width from observed alphabet. Do not merge PR #256 into the fork until this is answered.

### F02

**Omitted bits_per_symbol: width inferred from the data narrows n and changes n×H_bitstring (up to 2.4×); inferred width not in JSON**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED-DIFFERENT-FIX`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-width.sh
- **Upstream NIST issue:** #254
- **Upstream NIST PR:** —
- **Current upstream status:** #254 open. @joshuaehill: “Certainly reporting the evident symbol width in JSON would be useful. Reporting this ‘not a mapping’ as a warning isn’t useful.”
- **Current fork status:** JSON now carries bitsPerSymbol and bitsPerSymbolInferred. The inference algorithm and the existing stdout warning are unchanged, and no new warning was added. Whether the inferred width is the right default remains open with NIST and is not decided here.
- **Fork fix commit:** `97571de`
- **Verification:** regression-width.sh passes: both tools report width 4 inferred on truerand_4bit.bin and width 8 when 8 is declared; the inference still yields 4.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None in this fork. The default-width question stays with NIST on #254.

### F03

**Sub-minimum sample counts (< 10^6) produce a figure with JSON errorLevel 0 and no message**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED`
- **Fork disposition:** `RESOLVED-BY-GLOBAL-GUARD`
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
- **Regression test:** cpp/selftest/regression-minsize.sh
- **Upstream NIST issue:** #255 (related #238)
- **Upstream NIST PR:** —
- **Current upstream status:** #255 open. @joshuaehill: “A sub-1000000 sample input should probably be treated as an error.”
- **Current fork status:** Datasets below 1,000,000 samples are refused before any estimator runs, with a nonzero exit and errorLevel/errorMessage in JSON.
- **Fork fix commit:** `c2f1dcd`
- **Verification:** regression-minsize.sh passes: both tools refuse, no estimator output appears, and the JSON carries the error.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None for the sub-minimum half. How a legitimate no-estimate result should appear is tracked separately as F05.
- **Notes:** Filed with F05

### F04

**Literal MultiMCW skipped for 64 ≤ L ≤ 4095 although §6.3.7 defines it for L > 63; warning text off by one**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED-DIFFERENT-FIX`
- **Fork disposition:** `RESOLVED-BY-GLOBAL-GUARD`
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
- **Regression test:** cpp/selftest/regression-minsize.sh
- **Upstream NIST issue:** #258 (dup #265)
- **Upstream NIST PR:** —
- **Current upstream status:** #258 open. @joshuaehill: “This would be addressed by enforcing a 1000000 sample minimum.”
- **Current fork status:** No MultiMCW rewrite was attempted. With the intake check in place, 64 <= L <= 4095 cannot reach an estimator through ordinary use, so the skipped-estimator path is unreachable rather than corrected.
- **Fork fix commit:** `c2f1dcd`
- **Verification:** regression-minsize.sh passes. The 4096 threshold in multi_mcw_test.h is unchanged and still applies if the estimator is called directly.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None unless NIST decides §6.3.7 should run for L > 63, which would be a behaviour change this fork should not make first.

### F05

**Estimators that cannot run (−1) are silently dropped from the minimum and from the JSON; reachable at 10^6 (de Bruijn LRS v < u)**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-notrun.sh
- **Upstream NIST issue:** #255
- **Upstream NIST PR:** —
- **Current upstream status:** #255 open. @joshuaehill drew the distinction this implements: “There are instances where binary estimators can’t produce an estimate but where the result is not an error ... This is not an error, and should not be flagged as one.”
- **Current fork status:** Each test case carries literalEstimateNotRun or bitstringEstimateNotRun when the estimator applied but declined, omitted otherwise. errorLevel is untouched, so a skip is recorded as a fact rather than flagged as an error.
- **Fork fix commit:** `dfe325a`
- **Verification:** A de Bruijn B(100,3) sequence, a compliant 1,000,000-sample dataset whose LRS estimate genuinely cannot be computed, now names that skip with errorLevel still 0. truerand_8bit, truerand_1bit, ringOsc-nist and normal carry no flags. A short dataset names both estimators it cannot run.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None.
- **Classification:** JSON and reporting, covering a too-high direction

### F09

**Generic MultiMMC: a Null prediction from the winning sub-predictor does not reset the run of correct predictions (r over-counted)**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `VERIFIED`
- **Dangerous direction:** no (TOO LOW: MultiMMC 0.0021 vs 0.93; assessed figure unchanged)
- **Affected source:** `cpp/non_iid/multi_mmc_test.h` multi_mmc_test() generic path: `run_len = 0` only inside `if(found_x)` (lines 211-228) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/novel-findings/generators/noniid/f09gen.py 3 300 f09b.bin   # needs fillsteps.py from the same dir; SHA-256 1e2ae594…c534
  ./ea_non_iid -vv f09b.bin 8   # BUG: Literal MultiMMC r = 6603
  ```
- **Expected (correct) behaviour:** §6.3.9: a Null prediction is incorrect, so r = 24 (literal reference: `novel-findings/oracle/noniid/ref90b.py`, `novel-findings/repro/noniid/h/`)
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §4; `novel-findings/logs/noniid/out/f09b_run1.txt`; `novel-findings/agent-reports/noniid-estimators.md` §3a
- **Regression test:** cpp/selftest/regression-multimmc.sh
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** Not filed upstream.
- **Current fork status:** Both MultiMMC implementations now end the run of correct predictions on anything that is not a correct prediction by the winner: wrong, Null, or no prediction at all. SP 800-90B 6.3.9 step 1 initialises correct[] to 0 and step 4.d sets it to 1 only on a match, and the worked example in that section shows Null giving 0.
- **Fork fix commit:** `69b6094`
- **Verification:** On the audit's dataset r falls from 6603 to 24, the value the audit's literal implementation produces, and the estimate rises from 0.00211176482535928 to 0.93188950992564512. No figure on NIST's reference data moved: the pinned figure is unchanged, selftest differs on the same two files and the same eight predictor values as before, and the Literal MultiMMC figure on truerand_8bit.bin still matches refdata exactly.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None.
- **Classification:** correctness, direction too low

### F11

**Compression estimate admits exactly 1001 blocks (v = 1): σ̂ divides by v−1 = 0 → NaN (reports 1.0) or inf (−0)**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED-DIFFERENT-FIX`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-estimator-guards.sh (#263 section)
- **Upstream NIST issue:** #263
- **Upstream NIST PR:** PR #270
- **Current upstream status:** #263 open; PR #270 open and untouched. @joshuaehill: “This fix seems fine, but this would be addressed by enforcing a 1000000 sample minimum.”
- **Current fork status:** Both remedies are present: the intake check makes it unreachable, and compression_test itself now requires two test blocks so a direct call cannot divide by zero.
- **Fork fix commit:** `c0ee84a`
- **Verification:** regression-estimator-guards.sh passes: both 1001-block inputs decline, no NaN or inf sigma-hat is produced, and a 1002-block input still runs with sigma-hat 1.8930014049997954.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Watch PR #270. If NIST prefers to rely only on the intake minimum, the local guard can stay as defence in depth.

### F12

**Collision estimate with v ≤ 1 (2–5 binary samples): σ̂ = NaN and the estimator prints min-entropy 1 unmeasured**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED-DIFFERENT-FIX`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-estimator-guards.sh (#264 section)
- **Upstream NIST issue:** #264
- **Upstream NIST PR:** —
- **Current upstream status:** #264 open. @joshuaehill: “This would be addressed by enforcing a 1000000 sample minimum.”
- **Current fork status:** collision_test requires two collisions and declines otherwise. This also required guarding its result in non_iid_main.cpp: it was the one fallible estimator whose value was folded into the minimum unconditionally.
- **Fork fix commit:** `c217f20`
- **Verification:** regression-estimator-guards.sh passes: a five-sample binary input declines and no unmeasured 1.0 is produced.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None.

### F14

**Compression dict[] stores block indices in unsigned int: above 2^32 blocks D_i inflates and the estimate becomes 1.0**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-estimator-guards.sh (F14 section)
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** Not filed upstream.
- **Current fork status:** dict[] holds int64_t rather than unsigned int, with a static_assert keeping the element type at least 64-bit. int64_t rather than long because long is 32-bit on LLP64 targets, where the truncation would start at 4 Gbit rather than 25.8 Gbit.
- **Fork fix commit:** `6b60f9d`
- **Verification:** The end-to-end case cannot be run here (more than 25.8 Gbit of input and hundreds of GB of RAM). Verified instead that figures on real data are unchanged (ringOsc-nist.bin still 0.15932269772157773, pin-check unchanged) and that the compile-time guard is real: the regression narrows the type back in a scratch copy and the build refuses.
- **Reproduction last re-run:** 2026-09-30: not run end to end (needs > 25.8 Gbit of input and ~650 GB RAM); mechanism shown by the harness in the original audit
- **Last upstream-status check:** 2026-09-30
- **Required next action:** An end-to-end confirmation would need a machine with the memory for it.
- **Notes:** Latent in the size range #217/#226 enabled
- **Classification:** arithmetic safety, direction too high

### F15

**assert() aborts (no message, no JSON) on tiny or repeat-free inputs; asserts are live in the shipped build**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED-DIFFERENT-FIX`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-estimator-guards.sh (#261 section)
- **Upstream NIST issue:** #261 (dup #262)
- **Upstream NIST PR:** —
- **Current upstream status:** #261 open. @joshuaehill: “The cited examples would all be resolved if a minimum sample size of 1000000 was enforced.”
- **Current fork status:** The minimum is enforced, and the three assert sites now decline instead of aborting, so direct estimator calls cannot kill the process. The v < n half of the LRS assert is a genuine invariant and stays an assert.
- **Fork fix commit:** `21b0a31`
- **Verification:** regression-estimator-guards.sh passes: six inputs that previously exited 134 no longer abort, and repeat-free data both declines and still reports a figure.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None.
- **Notes:** N-03 is a separate ≥10^6 path

### F16

**Binary MultiMMC reads one byte past the sample buffer for 4 ≤ L ≤ 16 (heap over-read)**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-estimator-guards.sh (#257 section)
- **Upstream NIST issue:** #257
- **Upstream NIST PR:** PR #268 (dup PR #269 closed)
- **Current upstream status:** #257 open; PR #268 open and untouched. @joshuaehill: “This is a real bug”, and he asked for a failure return rather than the bound PR #268 proposes: “It would be better to return a failure flag (or a result like -1.0) in the instance where L < D_MMC+1.”
- **Current fork status:** Implemented as NIST asked: the estimator returns -1.0 below D_MMC+1 rather than bounding the loop and continuing on a partial model.
- **Fork fix commit:** `ed88de9`
- **Verification:** AddressSanitizer: L = 4, 5, 8, 12, 16 produce no sanitizer error where each previously reported heap-buffer-overflow at multi_mmc_test.h; a compliant dataset stays sanitizer-clean.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** PR #268 still carries the one-line bound. Decide with NIST whether to update it to the failure return or close it in favour of the intake minimum. Nothing was changed upstream from this fork.

### F18

**sha256_file reads to EOF with no size/type check: hangs forever on /dev/zero, /dev/urandom, FIFOs**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `HARDENING-NOT-BUG`
- **Fork disposition:** `FORK-HARDENING`
- **Dangerous direction:** no (availability)
- **Affected source:** `cpp/shared/TestRunUtils.h` sha256_file(): `while(!feof(file))` loop (lines 100-116); called before read_file_subset in every main (upstream `87c104d`)
- **Reproduce:**
  ```sh
  timeout 6 ./ea_non_iid /dev/zero; echo "exit=$?"   # BUG: exit=124, no output
  ```
- **Expected (correct) behaviour:** Non-regular files refused (fstat + S_ISREG) before hashing
- **Evidence / reproducer:** upstream #259; [`AUDIT.md`](AUDIT.md) row F18
- **Regression test:** cpp/selftest/regression-nonregular.sh
- **Upstream NIST issue:** #259 (dup #266)
- **Upstream NIST PR:** —
- **Current upstream status:** #259 open. @joshuaehill: “I’m not sure this is a bug, it’s more of an observation that when the user does wildly wrong things, marginally bad stuff might occur.” Not disputed here.
- **Current fork status:** Fixed in the fork as robustness only. The file type is taken from the path with stat() before the file is opened, because a FIFO blocks inside fopen. sha256_file’s status is now checked too; it had been discarded, leaving the hash buffer uninitialised on failure.
- **Fork fix commit:** `cdb5cd6`
- **Verification:** regression-nonregular.sh passes: /dev/zero, /dev/urandom, a FIFO and a directory are refused within 10 seconds; a regular file hashes unchanged.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None. Do not present this as a NIST-accepted defect.

### F19

**-l index,samples: offset multiplication wraps, samples=0 ignores the index, and the recorded SHA-256 is of the whole file**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `LOW-PRIORITY`
- **Fork disposition:** `VERIFIED`
- **Dangerous direction:** no (hostile/mistaken command line; report integrity)
- **Affected source:** `cpp/shared/utils.h` read_file_subset(): `subsetIndex*subsetSize` unchecked and the `subsetSize == 0` sentinel (lines 209-222); `cpp/non_iid_main.cpp`:178-181 (whole-file hash) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  ./ea_non_iid -vv -l 2,9223372036854775808 ../bin/truerand_1bit.bin 1   # BUG: loads the whole file, not block 2
  ./ea_non_iid -q -o sub.json -l 4,1000 ../bin/truerand_1bit.bin 1       # BUG: sub.json sha256 = whole-file hash
  ```
- **Expected (correct) behaviour:** Overflow and samples = 0 rejected; the JSON hash identifies the assessed bytes
- **Evidence / reproducer:** upstream #260; [`AUDIT.md`](AUDIT.md) row F19
- **Regression test:** cpp/selftest/regression-subset.sh
- **Upstream NIST issue:** #260 (dup #267)
- **Upstream NIST PR:** —
- **Current upstream status:** #260 open. @joshuaehill: “There’s no harm in checking for an overflow, but I don’t view this change as being high priority”, and “I think that the SHA sum acting on the file is the most reasonable behavior ... the file hash is more useful in this setting.”
- **Current fork status:** Overflow and out-of-range offsets are refused, and -l index,0 is refused. The sha256 field still hashes the whole file, as NIST preferred; subsetIndex, subsetRequestedSamples and subsetActualSamples identify the assessed part alongside it. No second hash was added.
- **Fork fix commit:** `0e1ffcd`
- **Verification:** regression-subset.sh passes all seven checks, including that a short final block is recorded as requested 700000 / actual 300000 and that sha256 still matches the whole file.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None.
- **Notes:** N-07 (TOCTOU) has the same fix direction

### N-01

**Binary chi-square independence reports Passed when m = 1; SP 800-90B §5.2.3 says "If m is 1, the test fails"**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-chisquare.sh
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** Not filed upstream. This pass does not touch upstream; the finding is a candidate to report once the owner decides.
- **Current fork status:** binary_chi_square_independence() now returns whether the test was applied, and chi_square_tests() fails the battery when m = 1, as SP 800-90B 5.2.3 requires. Reachable with a compliant dataset: fewer than about 3163 ones in 10^6 bits gives m = 1.
- **Fork fix commit:** `c8799f4`
- **Verification:** 999 ones in 100,000 bits (m = 1) now fails and names the rule; 1200 ones (m >= 2) still passes with a real statistic; truerand_1bit and truerand_8bit unaffected. The regression fails against the pre-fix build.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None in the fork. Consider reporting upstream.
- **Notes:** Also reachable via ea_restart -i
- **Classification:** correctness (IID wrongly accepted)

### N-02

**ea_iid -c runs the §5 IID tests on packed symbols instead of the conditioned binary string (§3.1.1 item 2, §3.1.5.2)**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-271.sh
- **Upstream NIST issue:** #271
- **Upstream NIST PR:** —
- **Current upstream status:** #271 open. @joshuaehill: “the appropriate behavior when doing iid testing is to run the Section 5 tests on the data as a binary string (data.bsymbols), and this does not presently occur. This functionality should be added, consistent with remedy 1 in this issue. Remedy 2 is not a reasonable fix.”
- **Current fork status:** Remedy 1 implemented: under -c the Section 5 batteries and their baseline statistics read a view onto data.bsymbols. -i is unchanged, and -c on binary input is unchanged because the view is then identical to the data.
- **Fork fix commit:** `134d377`
- **Verification:** regression-271.sh passes and fails against the pre-fix build: on the nibble-duplicate dataset -c now fails chi-square and LRS where it passed all three before, while -i on the same bytes still passes.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None. Note the cost: under -c -a with multi-bit symbols the permutation battery now runs on eight times as much data and did not finish in 40 minutes on a 1,000,000-sample 8-bit file; -t bounds it.

### N-03

**ea_conditioning -n -i on an all-zero conditioned dataset: assert abort, no JSON; with -DNDEBUG a heap over-read and a wild write**

- **State:** `NEEDS-FIX`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `DEFERRED-NOT-BUILT`
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
- **Current fork status:** In ea_conditioning, which this fork deliberately does not build: that is the only program linking MPFR and GMP, and keeping them out of what the fork ships is a standing decision. A repair could not be reproduced or regression-tested in this pass.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Decide whether to build ea_conditioning locally for test purposes. Building it for testing does not change what the fork ships, but it is the owner's call.

### N-04

**ea_restart accepts H_I = nan (passes both range checks) → float→int UB and out-of-bounds stack write → SIGSEGV; non-numeric H_I becomes 0**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-restart.sh
- **Upstream NIST issue:** — (#195 is a different path)
- **Upstream NIST PR:** —
- **Current upstream status:** Not filed upstream.
- **Current fork status:** H_I is parsed with strtod, requiring the whole argument to be consumed and the value to be finite. atof() returned 0.0 for unparseable text and accepted nan/inf, and a NaN H_I passed both range checks before reaching (int)floor(u/p), which is undefined behaviour indexing counts[] out of bounds.
- **Fork fix commit:** `db7a2ba`
- **Verification:** nan, NAN, inf, -inf, abc, 1.5x, 3.2e and an empty argument are refused with no signal, where the pre-fix build aborts with SIGABRT on nan. Negative H_I keeps its own message; 0, 3.2 and 8 still run.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None.
- **Classification:** arithmetic safety leading to memory unsafety

### N-05

**ea_conditioning JSON binds the -i file's name and SHA-256 to an h′ that did not come from it (CLI h′ given too, or vetted mode)**

- **State:** `NEEDS-FIX`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `DEFERRED-NOT-BUILT`
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
- **Current fork status:** In ea_conditioning; see N-03. Not reproduced or repaired in this pass.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Same decision as N-03.

### N-06

**sha256_file() failure ignored by every main: uninitialised stack bytes land in the JSON "sha256"**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-nonregular.sh and regression-restart.sh (N-06 section)
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** Not filed upstream.
- **Current fork status:** Three of the four programs now check sha256_file()'s status and zero the buffer, so a failure is a clean refusal rather than stack bytes in the report. The fourth instance, conditioning_main.cpp:521, is NOT fixed: this fork does not build ea_conditioning, so a change there could not be reproduced or regression-tested.
- **Fork fix commit:** `cdb5cd6 (ea_non_iid, ea_iid) and fd83a43 (ea_restart)`
- **Verification:** A missing input in ea_restart -i and -n exits 255 with errorLevel -1, a message and no sha256 field; a valid run records the file's true hash. ea_non_iid and ea_iid were verified in the previous pass.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Decide whether to build ea_conditioning for test purposes; until then its instance stands.
- **Classification:** report integrity and undefined behaviour

### N-07

**TOCTOU: the hash pass and the data pass open the file separately, so a concurrent rewrite binds one file's hash to another file's figure**

- **State:** `NEEDS-FIX`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `NEEDS-FIX`
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
- **Current fork status:** Not repaired. The obvious remedy, hashing the buffer that was assessed, would change what the sha256 field means, and NIST asked for the opposite on #260: @joshuaehill, “I think that the SHA sum acting on the file is the most reasonable behavior ... the file hash is more useful in this setting.” A repair therefore has to keep the whole-file hash and add a separate integrity check, which is a design decision rather than a mechanical fix.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Decide the shape first: keep sha256 as the whole-file hash and add a second, separately named digest of the assessed buffer, or re-read and compare. Do not silently redefine sha256.

### N-08

**Numeric CLI arguments parsed permissively (strtoull/strtoul base 0, atoi, no end check): -l 010 = block 8, bits "8x" = 8, n_out 0256 = 174**

- **State:** `NEEDS-FIX`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `NEEDS-FIX`
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
- **Current fork status:** Not repaired in this pass. The H_I instance, which was the one that crashed, is fixed under N-04; the remaining permissive parses (strtoull/strtoul base 0 for -l, atoi for bits_per_symbol, the conditioning arguments) are unchanged. They mis-read rather than crash: -l 010 means block 8, and a trailing character is ignored so “8x” is accepted as 8.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Parse every numeric argument decimal-only with an end-pointer and errno check, rejecting signs where a count is expected. Mechanical but it touches five files.

### N-09

**Output-file write failures never checked: -o /dev/full or a missing directory exits 0; ea_transpose can leave a truncated column file with exit 0**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `VERIFIED`
- **Dangerous direction:** no
- **Affected source:** every main: `ofstream` JSON writes never checked; `cpp/transpose_main.cpp`:112 `fclose` unchecked (upstream `87c104d`)
- **Reproduce:**
  ```sh
  ./ea_non_iid -o /dev/full ../bin/truerand_1bit.bin 1; echo $?             # BUG: 0
  ./ea_non_iid -o /nonexistent_dir/x.json ../bin/truerand_1bit.bin 1; echo $?   # BUG: 0
  ```
- **Expected (correct) behaviour:** Non-zero exit and a message when the report cannot be written
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §2 N-09; `novel-findings/logs/io/`
- **Regression test:** cpp/selftest/regression-output.sh
- **Upstream NIST issue:** —
- **Upstream NIST PR:** —
- **Current upstream status:** Not filed upstream.
- **Current fork status:** The 39 report writes across the three programs this fork builds are now one checked helper, writeJsonReport() in shared/TestRunUtils.h, which checks both the open and the close. The three success paths exit nonzero when the report cannot be written. conditioning_main.cpp and transpose_main.cpp still have unchecked writes and are not built here.
- **Fork fix commit:** `47d6624`
- **Verification:** All three tools refuse with a nonzero exit naming the output file and no signal; writable paths still produce non-empty reports. A double free introduced in the restart cleanup during this change was caught by testing and corrected; an AddressSanitizer build of that path is clean.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** The two programs this fork does not build still carry the defect.
- **Classification:** CLI and error handling

### N-10

**Reporting-only: ea_iid "Median" is of translated indices; conditioning JSON hard-codes "IID": false and omits vetted/track; restart -i JSON mean/median always 0.0**

- **State:** `NEEDS-FIX`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `NEEDS-FIX`
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
- **Current fork status:** Not repaired. Partly in ea_conditioning (see N-03) and partly a question of what the reported value should mean rather than a defect with one correct answer: ea_iid's “Median” is the median of translated symbol indices, which is what SP 800-90B 5.1.5/5.1.6 need for the tests but is not the median of the sample values a reader would expect.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Decide per item whether the value or its label should change; the conditioning half waits on the N-03 decision.

### N-11

**ea_conditioning aborts (assert) for accepted n_in/n_out ≥ 1,073,741,823 (MPFR emax)**

- **State:** `NEEDS-FIX`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `DEFERRED-NOT-BUILT`
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
- **Current fork status:** In ea_conditioning; see N-03. Not reproduced or repaired in this pass.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Same decision as N-03.

### R-1

**Residual of #246: len_LRS_test asserts p_col ≥ 1/k and aborts when every symbol count is exactly equal and 1/k rounds down (k = 3, 6, 7, 9, 12, …)**

- **State:** `FORK-FIX-REQUIRED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `NOT-REPRODUCED-HERE`
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
- **Current fork status:** Investigated on 2026-09-30 and it does NOT reproduce on this platform. The assert compares a floating-point sum against an exact bound, and the margin depends on the width of long double: 64-bit on arm64 macOS, 80-bit under GCC on x86. Measured here for exactly balanced alphabets at L near 10^6: the margin p_col - 1/k is exactly 0 for k = 2, 3, 4, 7, 8, 9, 16 and +2.78e-17 for k = 5, 6, 12, so the assert holds for every k tried and ea_iid bal3.bin 2 completes with exit 0. A zero margin satisfies the assert, which tests `p_col >= 1/k` inclusively, so what was measured here is not itself a defect; it shows the predicate sits exactly on its bound and so is sensitive to rounding. The defect recorded against this finding is the abort observed on an x86-64 build with 80-bit long double, which was not reproduced here and is not re-asserted on this platform's evidence. Not repaired, because a fix could not be regression-tested on this machine: the regression would pass before and after.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Reproduce on an x86-64 build with 80-bit long double, then fix (clamp p_col to 1/k within rounding, or compute the collision proportion as an exact integer ratio) with a regression that fails there.

### R-2

**Residual of #178: ea_restart folds a t-tuple/LRS −1 ("cannot run") into H_r/H_c, giving a false restart failure**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-restart.sh (R-2 section)
- **Upstream NIST issue:** #178 (closed)
- **Upstream NIST PR:** —
- **Current upstream status:** Residual of upstream #178, which is closed. Not re-filed.
- **Current fork status:** The t-tuple and LRS folds into H_r/H_c are guarded with >= 0, as ten of the twenty folds in the file already were. The two collision folds are guarded as well, since collision_test became fallible in c217f20.
- **Fork fix commit:** `d892b90`
- **Verification:** On a de Bruijn B(100,3) sequence of exactly 1,000,000 samples, where the LRS estimate genuinely declines, H_r is now 6.583332 instead of -1 and the run passes validation. An ordinary restart dataset is unchanged. The regression also asserts the precondition so it cannot pass vacuously.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None.
- **Classification:** correctness, direction too low (false validation failure)

### R-3

**Regression of #183: ea_restart -i writes JSON errorLevel 0 on an input read failure (sets testRunNonIid, writes testRunIid; merge 4d68e47)**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `VERIFIED`
- **Dangerous direction:** no (report integrity)
- **Affected source:** `cpp/restart_main.cpp` main(): read_file failure branch (:319-339), line 324 `testRunNonIid.errorLevel = -1` under `if (iid)` (upstream `87c104d`)
- **Reproduce:**
  ```sh
  python3 ../audits/2026-09-30/phase2-focused/generators/gen_w.py w
  ./ea_restart -i -o r.json w/r8.bin 4 3.2; echo $?   # BUG: exit 255 but r.json "errorLevel": 0, no errorMessage
  ```
- **Expected (correct) behaviour:** errorLevel −1 with the read error message in the IID JSON
- **Evidence / reproducer:** [`novel-findings/REPORT.md`](novel-findings/REPORT.md) §3 R-3; `novel-findings/repro/verify/r_iid.json`, `r_non.json`; `phase2-focused/logs/evidence/json/w4i.json`
- **Regression test:** cpp/selftest/regression-restart.sh (R-3 section)
- **Upstream NIST issue:** #183 (closed)
- **Upstream NIST PR:** —
- **Current upstream status:** Regression of upstream #183, which is closed. Not re-filed.
- **Current fork status:** The read-failure branch sets the error on the report object it actually writes, and carries read_file()'s message across in IID mode.
- **Fork fix commit:** `23dca69`
- **Verification:** Declaring 4 bits per symbol for byte-valued data now yields errorLevel -1 and the real message in both -i and -n, where -i previously reported errorLevel 0; a successful run still reports 0.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None.
- **Classification:** report integrity

### NOVEL-01

**selftest never compares H_original, H_bitstring or "Assessed min entropy", and its exit status reflects only the last file**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `ACCEPTED`
- **Fork disposition:** `VERIFIED`
- **Dangerous direction:** no by itself (it masks TOO-HIGH regressions)
- **Affected source:** `cpp/selftest/compareresults.pl` resultsHash() (lines 65-66: keyword filter + `label = number` regex); `cpp/selftest/selftest` (lines 3-8: exit codes never combined) (upstream `87c104d`)
- **Reproduce:**
  ```sh
  bash ../audits/2026-09-30/phase2-focused/repro/issue272/repro.sh   # fresh upstream clone; baseline, 2 mutants, refdata edit
  # BUG: every run prints identical 'Maximum delta' lines and exits 0 while the Assessed figures change
  ```
- **Expected (correct) behaviour:** Summary figures compared; any mismatching file makes ./selftest exit non-zero
- **Evidence / reproducer:** [`phase2-focused/REPORT.md`](phase2-focused/REPORT.md) NOVEL-01; `phase2-focused/repro/issue272/`; `phase2-focused/logs/issue272/`
- **Regression test:** cpp/selftest/regression-272.sh
- **Upstream NIST issue:** #272
- **Upstream NIST PR:** —
- **Current upstream status:** #272 open. @joshuaehill: “it surely wouldn’t hurt to check” the final results, and “I think the selftest ought to stop on observing a mismatch”.
- **Current fork status:** Both gaps closed: compareresults.pl now collects H_original, H_bitstring, H_bitstring Per Symbol and Assessed min entropy, and selftest exits nonzero naming every failing sample. It runs all samples rather than stopping at the first, so one failure does not hide the rest.
- **Fork fix commit:** `da0265c`
- **Verification:** regression-272.sh passes: both preserved mutants are caught, and caught specifically by a final-figure key rather than an estimator key. The old script reported “Maximum delta: 1.44440015503733e-13” and exit 0 for the mutant that reports 7.8651 against a reference of 7.2338.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** None. Note that selftest now exits 1 on macOS arm64 because of the pre-existing platform deltas in upstream #155.
- **Notes:** Until fixed, check "Assessed min entropy" separately when running the selftest (e.g. `cpp/selftest/pin-check.sh`)

### NOVEL-02

**ea_iid JSON emits never-computed placeholders: hBitstring 1.0 for binary input, hOriginal = word size under -c**

- **State:** `FORK-FIXED`
- **Upstream disposition:** `PENDING`
- **Fork disposition:** `VERIFIED`
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
- **Regression test:** cpp/selftest/regression-iid-json.sh
- **Upstream NIST issue:** — (distinct from PR #251)
- **Upstream NIST PR:** —
- **Current upstream status:** Not filed as NOVEL-02. Upstream PR #251, by another contributor, addresses the same verbosity coupling for hAssessed and is open and untouched.
- **Current fork status:** ea_iid records only the figures it computed, and the assessed figure is computed separately from printing it. Previously a binary -i report carried hBitstring 1.0 and a -c report carried hOriginal = word size, and hAssessed was the word size at any verbosity below -vvv: 1.0 against a correct 0.9950430151312257.
- **Fork fix commit:** `9f64f62`
- **Verification:** binary -i omits hBitstring and reports hAssessed 0.9950430151312257, matching the -vvv text; -c omits hOriginal and still reports hBitstring; -vvv text output unchanged.
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Watch PR #251 for the upstream shape of the hAssessed half.
- **Classification:** JSON and reporting, with a too-high reported figure

### NOVEL-03

**ea_restart -i JSON appends row and column permutation results under identical iteration labels (no row/column tag)**

- **State:** `NEEDS-FIX`
- **Upstream disposition:** `NOT-FILED`
- **Fork disposition:** `NEEDS-FIX`
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
- **Current fork status:** Not repaired in this pass. ea_restart -i runs the permutation battery twice, over rows and then over columns, and both populate the same test case, so the JSON carries six results under iteration labels 0,1,2,0,1,2 with nothing saying which pass each came from.
- **Fork fix commit:** — (not yet fixed on fork `master`)
- **Verification:** re-run the Reproduce commands; the `BUG:` lines must instead show the expected behaviour, and the regression test must pass
- **Reproduction last re-run:** 2026-09-30, clean build of fork `master` `237d85c` (Linux x86-64, GCC 13, -O2): reproduces as written
- **Last upstream-status check:** 2026-09-30
- **Required next action:** Give populateTestCase() a row/column tag, or use two test cases. Reporting-only; no figure changes.

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

## Independent re-audit findings (REV series, 2026-10-01)

An independent re-audit on 2026-10-01 re-tested the prior findings and the
claimed repairs. It confirmed the repairs: fifteen findings verified as
actual-parent / fixed / meaningful-mutant triples, the pinned figure computed
on both the historical and current scripts, and the eleven-file reference
corpus byte-identical between parent and fixed builds on both macOS and
GCC/Linux. Its own scope statement is the right one: the evidence holds for
the fixtures, platforms and mutations exercised, and is not a
universal-compatibility or production-security certification.

It also found five defects, four of them in work done by the repair passes.
They are recorded here because this file is the canonical defect queue; the
re-audit's own write-up and evidence archive live outside the checkout.

| ID | What was wrong | Class | Disposition | Fixed by |
|---|---|---|---|---|
| REV-001 | NOTICE still said estimator changes "changed only" to declining, which F09 and N-01 contradict. The same sentence had been corrected in BUILDING.md and missed here. | documentation | `VERIFIED` | `c11c9a8` |
| REV-002 | `make non_iid` failed under GCC 13.3 on undeclared `ULONG_MAX`, introduced by the #260 subset overflow check. Apple clang builds it, so the macOS-only workflow did not catch it. | portability (build break) | `VERIFIED` | `b75e763` (a prior session) |
| REV-003 | `regression-multimmc.sh` asserted only that the binary path produced *a* run length. A mutant with the binary reset removed reports r = 100275 against a correct 17 and passed. | test integrity (vacuous check) | `VERIFIED` | `8f0469c` |
| REV-005 | `regression-estimator-guards.sh` compared the compression estimate against a literal that is this platform's value, so it raised a false alarm on Linux, where refdata records the other value. | test integrity (false failure) | `VERIFIED` | `8f0469c` |
| REV-007 | BUILDING.md stated the permutation cost as "0.94 ms per thousand bits"; the measurements give 0.94 seconds, a factor of 1000. The derived run times were computed from the measured rate and were always correct. | documentation | `VERIFIED` | `c11c9a8` |

REV-004 and REV-006 were raised and are **not** recorded as defects here.
REV-004 observes that GNU `getopt` misroutes `-inf` and `-1` as options before
the numeric checks see them; both configurations refuse the input either way,
so the behaviour is correct and the note is about which code path refuses it.
REV-006 could not reproduce the absent-file issue it was testing for, because
the undefined hash bytes happened to be non-empty on that run; the N-06 repair
and its regression stand.

Two of the four defects introduced here were in regression tests, not in the
tool: one that could not fail, and one that failed on the platform the project
targets. Both read as green. `cpp/selftest/regression-docs.sh` now also checks
that the quoted permutation rate matches the measured table, and carries both
corrected phrasings verbatim so they cannot reappear.

Three claims in the re-audit remain **BLOCKED** rather than confirmed or
refuted, by its own account: F14's end-to-end evidence above 2^32 blocks, a
`checkpoint-6` archive, and a `candidate-25.bin` fixture, none of which were
located. They are not counted as findings in either direction.

## Open questions put to NIST (2026-09-30, awaiting an answer)

Posted by the fork owner on the upstream threads, not by the repair pass. Two
of them gate work that is deliberately not done:

| Thread | Question | What is blocked |
|---|---|---|
| PR [#256](https://github.com/usnistgov/SP800-90B_EntropyAssessment/pull/256) / [#253](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/253) | If `bits_per_symbol=8` is supplied explicitly for a two-symbol alphabet such as `{33, 211}`, is that dataset still binary for §3.1.3, so the `n x H_bitstring` term is correctly omitted? | F01. The fork follows upstream behaviour unchanged and PR #256 is not merged here until this is answered. |
| PR [#268](https://github.com/usnistgov/SP800-90B_EntropyAssessment/pull/268) / [#257](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/257) | Should the PR be revised to return failure locally as defence in depth, or superseded by the central 1,000,000-sample intake check? | Nothing in the fork: both are implemented here (`ed88de9`, `c2f1dcd`). Only the shape of the upstream PR is waiting. |

Agreements confirmed on the same date, all already implemented here: remedy 1
for [#271](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/271)
(commit `134d377`), the selftest strengthening for
[#272](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/272)
(commit `da0265c`), the 1,000,000-sample minimum as the user-facing remedy for
the short-input family (commit `c2f1dcd`), narrowing
[#255](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/255) to
sub-minimum input being an error rather than flagging legitimate no-result
estimates, keeping the whole-file hash on
[#260](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/260) and
adding subset provenance instead, limiting
[#254](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/254) to
reporting the effective width in JSON, and treating
[#259](https://github.com/usnistgov/SP800-90B_EntropyAssessment/issues/259) as
fork hardening rather than a standards defect.

## Sources

- F-series: [`AUDIT.md`](AUDIT.md), the first-wave audit, with rows re-assessed in §4 of the novel-findings report.
- N/R-series: [`novel-findings/REPORT.md`](novel-findings/REPORT.md).
- NOVEL-series: [`phase2-focused/REPORT.md`](phase2-focused/REPORT.md).
- Upstream states: read from GitHub on 2026-09-30.
