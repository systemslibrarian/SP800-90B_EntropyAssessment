# SP 800-90B EntropyAssessment: Phase-2 focused novel-findings audit (second session)

Date: 2026-09-30. Report only; nothing was filed or posted upstream. The shared checkout was never built in or modified.

## Baseline

| Item | Value |
|---|---|
| Commit | upstream `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289` (= upstream master HEAD), exported with `git archive` to a scratch directory |
| Compiler | g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 |
| Platform | Linux 6.8.0-1064-azure x86_64, glibc 2.39, 2 vCPU, 7.7 GB RAM |
| Build | stock `cpp/Makefile`: `-std=c++11 -fopenmp -O2 -ffloat-store -march=native`; all five binaries built |
| Self-test | `cd selftest && ./selftest`: all 11 files, max delta 4.3e-15 … 1.0e-13 (PASS) |
| Sanitizers | yes: `-O1 -g -fsanitize=address,undefined,float-cast-overflow` (scratch tree) |
| Spec | `NIST.SP.800-90B.pdf` (Jan 2018), text-extracted |
| Issue/PR dump | 188 issues + 82 PRs with comments (gh, 16:16); re-fetched at the end: one new item, #271 |

Binaries: ea_iid, ea_non_iid, ea_restart, ea_conditioning, ea_transpose. "selftest" is a shell script plus `compareresults.pl`, not a binary.

## Existing-findings exclusion map

**Read:** every upstream issue and PR body and comment.

**Also treated as known** (per the user's instruction):
- the fork's `AUDIT-2026-09-30.md` (F01–F30);
- the parallel session's `audits/2026-09-30-novel-findings-audit.md` (N-01…N-11, R-1…R-3), commit 0e685f6.

**Key roots:**
- #253 alph_size==2 gate
- #254 width inference
- #255 JSON invisibility
- #257 MultiMMC over-read
- #258 MultiMCW < 4096
- #259 unbounded hash
- #260 `-l` arithmetic and hash scope
- #261/#262 asserts on tiny inputs
- #263/#264 v ≤ 1 NaN
- PRs #256/#268/#270
- #168 conditioning NaN (the prompt's "#193" is actually "read bits")
- #195 `k_effective` assert
- #236/PR #237 manual VERSION macro
- #246/PR #248 `p_col` assert
- #251 IID hAssessed only at `-vvv`
- #252 IID figure despite a failed IID test
- #56/#95/#209/#224 simulated restart cutoff
- #212/#220/#247 stochastic results
- #153 LDBL_MIN assert
- #178 −1 folding
- #183 restart JSON
- #22 Z = 2.5758
- #214/#163/#52 LRS time
- #271 (new today; the parallel N-02)

## Mission work log (A–J)

**A: restart and transpose.**
- Shapes 999×1000, 1000×1001, empty, missing file and constant were all refused with JSON errorLevel −1, except the `-i` read-error path (= R-3).
- Random 8-bit 1000×1000 with H_I = 7.5 passed (66 s).
- Also checked: the §3.1.4 text against the code, and §6.2 (no bitstring step, so restart conforms).
- H_I fuzz: `nan` gives SIGSEGV (= N-04); `abc` becomes 0.
- New item: restart `-i` JSON with duplicate unlabelled permutation blocks (NOVEL-03).
- Rejected: the sanity-check simulation vs the binomial rule (known #56/#95/#209).

**B: conditioning.**
- Read in full.
- The `-i` file hash with a CLI h′ (= N-05); the all-zero file (= N-03); `sha256` garbage (= N-06).
- MPFR rounding up at the final `mpfr_get_ld(RNDN)`: ≤ 0.5 ULP of a long double, about 1.4e-17 bit at n_out = 256. No finding.

**C: IID.**
- §5.1/§5.2 read against the code: early-exit equivalence, conversions, median rule and bins all correct.
- m = 1 binary independence passes; re-derived independently. Full `ea_iid` pass on Bernoulli(0.002045), with IID H 0.0027851 vs non-IID 0.0020159 (+38 %). This is the parallel audit's N-01.
- Balanced k ∈ {3, 6, 7, 12} still hits the #246 assert (= R-1).
- New item: IID JSON placeholder values (NOVEL-02).

**D: selftest, golden vectors and version.**
- Comparator ignores the reported figures, and the exit status reflects only the last file (NOVEL-01, demonstrated with two mutants).
- Version: the v1.1.8 tag prints 1.1.7, and master prints 1.1.8 but includes #248/#250 (known #236 / PR #237).

**E: oracles, written from the PDF only.**
- Estimators: MCV, Markov, t-Tuple, LRS, Lag, LZ78Y, plus P_global′/P_local with x₁₀.
- All spec worked examples reproduce.
- Compared against `ea_non_iid -vv` on fair, p = 0.9, 3-symbol skewed and 8-bit uniform data at L = 64, 4096 and 10⁶: 12 files, 0 mismatches.
  - Worst relative difference: 3.7e-11 (P_local tolerance 1e-6).
- Bijection {0,1} (1-bit) vs {17,201} (8-bit): identical, 0.860078706179634.
- {0,255}: no bitstring pass, which confirms only #253.

**F: JSON contract.** Mostly covered by #251/#252/#255, R-3, N-05/06/09/10. New items: NOVEL-02 and NOVEL-03.

**G: portability.**
- No 32-bit/LLP64 or aarch64 toolchain here: untested.
- OpenMP and compiler variation were covered by the parallel audit.

**H: resources.** Linear on conforming inputs:

| Input | Wall | Peak RSS |
|---|---|---|
| 8-bit 10⁶ | 19 s | 290 MB |
| 8-bit 4·10⁶ | 71 s | 412 MB |
| binary 10⁷ | 6.5 s | 141 MB |
| conditioning `-i` on 8·10⁶ bits | 4.5 s | 109 MB |

No finding.

**I: CLI.** Covered by N-04/N-08/N-09. Nothing new.

**J: shared code.**
- The symbol map, bitstring conversion (masked raw, MSB-first) and `min()` fold were read.
- `static mutex` in FYshuffle serialises shuffles: performance only.
- No finding.

**Sanitizers.** ASan/UBSan runs on the restart error paths, `ea_non_iid`/`ea_conditioning` 4096-sample files, `ea_iid` p0.002 and transpose were clean, except the known N-04 NaN→int UB (`restart_main.cpp:92, 132`).

## Confirmed NOVEL findings

### NOVEL-01: `selftest` cannot detect an error in the reported figure, and its exit status reflects only the last file

- **Category:** E (verification tooling). **Confidence:** HIGH.
- **Affected:** `cpp/selftest/compareresults.pl`:65-66 and `cpp/selftest/selftest`:3-8. Checks the ea_non_iid output printed at `non_iid_main.cpp:511,516,519`.
- **SP 800-90B:** §3.1.3 (the H_I combination the harness should protect).
- **Valid ≥1e6 case:** yes (the shipped 1e6 reference files). **Direction:** none by itself; it masks TOO HIGH regressions.
- **Robustness/testing-tooling only:** yes.

**Root cause.**
- `resultsHash` keeps only lines that contain `Estimate:` or `Assessed` and match `^label = number$`.
  - `H_original = …` and `H_bitstring = …` have neither keyword.
  - `Assessed min entropy: …` uses a colon.
  - So all three reported figures are dropped from both the reference and the new output. On truerand_8bit.res, 94 per-estimator lines are compared and these 3 never are.
- `selftest` runs compareresults once per file and never combines the exit codes, so the script's status is that of the last file only.

**Reproduction** (scratch copy of 87c104d):

```sh
cp -r up mut && cd mut/cpp
sed -i 's|        h_assessed = min(h_assessed, H_bitstring \* data.word_size);|        /* mutant */|' non_iid_main.cpp
make non_iid && cd selftest && ./selftest; echo $?
```

Mutant 2 instead deletes `if (initial_entropy) { h_assessed = min(h_assessed, H_original); }`.

For the exit-status defect, edit one value in `refdata/biased-random-bits.res` of an unmodified build and run `./selftest; echo $?`.

**Actual.**
- Both mutants print output identical to the correct build: the same "Maximum delta" line for all 11 files, no "Significant difference", exit 0.
- The reported figures change:

| File | Correct | Mutant 1 (n×H_bitstring dropped) | Mutant 2 (H_original dropped) |
|---|---|---|---|
| normal.bin | 4.1001 | 5.5291 | — |
| truerand_8bit.bin | 7.2339 | 7.8651 | — |
| biased-random-bytes.bin | 0.2577 | 0.2912 | — |
| rand8_short.bin | 5.8609 | 6.6364 | — |
| ringOsc-nist.bin | 0.1264 | — | 1.0 |
| biased-random-bits.bin | 0.0178 | — | 1.0 |

  - Mutant 1 raised 6 of the 11 files; mutant 2 set all 5 binary files to 1.0.
- Refdata edit: "Significant difference … delta 0.0803" is printed for file 1, but `selftest` exits 0.

**Expected.**
- The reported H_original, H_bitstring and assessed figure are compared (their reference values are already in refdata).
- Any file's mismatch makes `selftest` exit non-zero.

**Impact.**
- The only shipped regression check cannot catch an error in the final §3.1.3 combination, in either direction.
- The fork's BUILDING.md:137 describes it as checking "1e-10 relative per reported value", and the parallel audit used it as its baseline. It does not check what it is believed to check.
- Pending PRs that change the combination (#256 for #253) get no protection from it.
- Refdata dates from 2019-05-02 and still uses the old `H_original:` format, which is also ignored.

**Deduplication.**
- Searched "compareresults", "selftest", "Assessed min entropy", "regex", "exit status" across all 271 items.
- Only #155/#219 (Windows deltas), #203/#231 (broken builds) and #94 (the request that created the selftest).
- Not in AUDIT F01–F30, and not in N/R.

**Fix direction.**
- Match `label = value` and `label: value`, and whitelist the three summary lines.
- Treat an extra key as a failure.
- Accumulate the exit status in `selftest`.

**Regression test.** Both mutants above must make `./selftest` exit non-zero.

### NOVEL-02: `ea_iid` JSON reports never-computed placeholder figures

- **Category:** E. **Confidence:** HIGH. **Affected:** ea_iid, `iid_main.cpp:272-284`. **SP:** §3.1.3.
- **Valid ≥1e6:** yes. **Direction:** none (misleading provenance). **Tooling only:** no, it affects lab automation that reads the JSON.

**Root cause.** `H_original = word_size` and `H_bitstring = 1.0` are initial values that are assigned to the test case unconditionally. ea_non_iid only sets these fields when it computes them.

**Reproduction.**
```sh
ea_iid -q -o a.json iid_p002.bin 1     # binary input
ea_iid -c -q -o b.json r8.bin 8        # conditioned mode
```

**Actual.**
- a.json: `"hBitstring": 1.0`, although no bitstring assessment runs for binary input.
- b.json: `"hOriginal": 8.0`, although H_original is never computed under `-c`.
- `hAssessed` 1.0 and 8.0 are #251 and are not counted here.

**Expected.** Omit the fields, as ea_non_iid does via its −1 sentinel.

**Impact.** Low. Any min() a consumer takes is unaffected, but the report shows full-entropy numbers that were never measured.

**Deduplication.** #251 fixes only `hAssessed` (a verbosity gate); this is an unconditional default. Not in N-10 or #238.

**Fix.** Assign `tc.h_original` / `tc.h_bitstring` only inside the branches that compute them.

### NOVEL-03: `ea_restart -i` JSON merges row and column permutation results under the same labels

- **Category:** E. **Confidence:** HIGH. **Affected:** `restart_main.cpp:791,800` → `permutation_tests.h:730` (`populateTestCase`). **SP:** §3.1.2(3).
- **Valid ≥1e6:** yes. **Direction:** none.

**Root cause.** PR #250 added the column call with the same `tcOverallIid`, so `populateTestCase` appends a second 3-entry block.

**Reproduction.** `ea_restart -i -q -o r.json r8.bin 8 7.5` (random 1000×1000).

**Actual.**
- `permutationTestResults` has 6 entries with `iteration` = [0,1,2,0,1,2]. Excursion is [6,0,11,6,0,6]: the row and column counters differ but carry no row/column tag.
- `passedIidPermutationTests` is row && column, so a failure cannot be attributed.

**Expected.** Separate, labelled row and column results.

**Impact.** Low. Automated evidence review cannot tell which dataset produced which counts.

**Deduplication.** #244/PR #250 introduced the call but not the reporting; N-10(c) is mean/median 0.0 only.

## Suspected findings needing more work

None new. The IID `int sample_size` truncation above 2³¹ samples could not be run here (also rejected by the parallel audit).

## EXCLUDED AS ALREADY KNOWN

These are my rediscoveries from this session, with what they map to:

| Rediscovery | Maps to |
|---|---|
| Binary independence m = 1 passes (same file shape; my +38 % impact) | parallel N-01 |
| restart `-i` read-error JSON errorLevel 0, regression 4d68e477 | parallel R-3 / #183 |
| `sha256_file` return ignored → uninitialised `sha256` in JSON | parallel N-06 |
| restart H_I = `nan` SIGSEGV, `abc` → 0 | parallel N-04 |
| conditioning `-i` hash bound to a CLI h′ (code only) | parallel N-05 |
| all-zero conditioned file → `word_size` 0 | parallel N-03 |
| balanced k = 3/6/7/12 `p_col` assert | #246 (parallel R-1) |
| restart LRS −1 folded (code only) | #178 (parallel R-2) |
| IID/restart figure despite a failed IID test | #252 |
| IID `hAssessed` default | #251 |
| {0,255} treated as binary; IID gate | #253 |
| conditioning `-i` width inference | #254 |
| v1.1.8 / master version string | #236 / PR #237 |
| restart cutoff above binomial | #56/#95/#209/#224 |
| `k_effective` assert | #195 |
| LDBL_MIN assert | #153 |
| TOCTOU | parallel N-07 |
| `-l` octal | parallel N-08 / #260 family |

## No-finding areas

- **Mission E:** all six estimators vs the spec oracle.
- **Mission H:** resources.
- **Mission J:** shared helpers.
- **Restart:** orientation and §6.2 scope.
- **Markov/Lag/LZ78Y/MultiMCW:** code read against the spec text.
- **Conditioning rounding:** ≤ 1.4e-17 bit.
- **Mission G:** untested (no toolchain).
