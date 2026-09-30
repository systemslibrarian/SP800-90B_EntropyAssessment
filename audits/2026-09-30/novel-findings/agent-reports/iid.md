# Area "iid" — adversarial audit of `ea_iid` (upstream 87c104d)

Work dir: `SCR/audit/work/iid/` (SCR = `/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad`).
Binaries: `SCR/audit/rel/cpp/ea_iid` (release, upstream flags) and `SCR/audit/asan/cpp/ea_iid` (ASan+UBSan). The five in-scope source files are byte-identical between the audit trees and the fork's `cpp/` at 1d26ab3.

**Spec text.** I did not work from memory: the SP 800-90B (Jan 2018) PDF was fetched read-only from nvlpubs.nist.gov (sha256 `9b0dd771…defe7`, saved as `work/iid/sp800-90b.pdf`, text in `work/iid/sp800-90b.txt`). Every spec quote below comes from that text.

**Machine note.** The 2-core box ran at load 15–20 the whole time because other audit areas were running. The 1e6-sample `ea_iid` runs took 2–25 minutes wall-clock. Where a failing input would have needed all 10,000 permutations, I only captured the chi-square and LRS stages, which print before the permutation stage.

---

## 1. Scope covered

**Files and functions read in full**
- `iid_main.cpp`: `main`, option parsing (`-i -c -a -t -v -q -l -o`), the H_original/H_bitstring/h_assessed logic, and the order of the three test batteries.
- `iid/permutation_tests.h`: every function. That covers `conversion1/2`, `excursion`, `alt_sequence1/2`, `num_/len_directional_runs`, `num_increases_decreases`, `find_collisions`, `avg/max_collision`, `periodicity`, `covariance`, `compression`, `run_tests` and helpers, `permutation_tests` (OpenMP loop, counters, early exit, final rule) and `populateTestCase`.
- `iid/chi_square_tests.h`: every function. That covers the cephes `lgam`/`igam`/`igamc`, `chi_square_pvalue`, `allocate_bins`, `independence_calc_*`, `binary_chi_square_independence`, `chi_square_independence`, `binary_goodness_of_fit`, `goodness_of_fit` and `chi_square_tests`.
- `iid/iid_test_case.h`, `iid_test_run.h`, `permutation_test_result.h`, `shared/test_case_base.h`, `test_run_base.h`: the JSON output.
- `shared/lrs_test.h`: `len_LRS_test`, `calc_collision_proportion`, `len_LRS32/64`, `calcSALCP32/64`, `sa2lcp32/64`.
- `shared/most_common.h`.
- `shared/utils.h` helpers used by ea_iid: `read_file_subset`, `xoshiro256starstar`, `xoshiro_jump`, `seed`, `randomRange64`, `FYshuffle`, `sum`, `calc_stats`, `calc_proportions`, `divide` and `n_choose_2`.

**Spec sections compared:** §3.1.1 (items 1–2), §3.1.2 (items 2 and 4), §3.1.3, §3.1.5.2, §5.1 (Fig. 4 and 5, Conversions I/II, 5.1.1–5.1.11), §5.2.1–5.2.5, §6.1 and §6.3.1.

### Conformance table

| Section | Algorithm/Test | Step | Code location | Matches? | Notes |
|---|---|---|---|---|---|
| §5.1 Fig 4 | permutation ranking | C0 if T'>T, C1 if T'=T | permutation_tests.h:662-668 | yes | C2 = T'<T. Ties are exact comparisons of identical code paths. |
| §5.1 Fig 4 | reject rule | (C0+C1≤5) or (C0≥9995) | :733 `C0+C1<=5 \|\| C1+C2<=5` | yes | Equivalent when all 10,000 rounds are counted. Early exit (:669-671) marks a test passed only once both sums exceed 5, and both sums can only grow, so the verdict is identical. Maintainer position #239. |
| §5.1 Fig 5 | Fisher–Yates | j∈[1,i] | utils.h:655-665, randomRange64 :614 | yes | Lemire's method without bias. Verified statistically (24 perms of n=4, χ²=26.7 on 23 df; range [0,5] χ²=5.2 on 5 df; no out-of-range values). data and rawdata swapped together. |
| §5.1 | Conversion I / II | 8-bit blocks, zero-pad last block, MSB-first | permutation_tests.h:27-50 | yes | Checked against the spec's worked example and 29 differential cases. |
| §5.1 | binary ⇔ k=2 | "when the input is binary, i.e., k = 2" | `alph_size==2` gates | yes | For §5 this gate is spec-literal. The H_bitstring side of the same gate is #253. |
| 5.1.1 | excursion | raw values, X̄ | :57-72, rawdata | yes | Floating ties are conservative (see §6). |
| 5.1.2-5.1.4 | directional runs / increases-decreases | −1 if s_i>s_{i+1}; binary uses Conv I | :80-187, :347-363 | yes | |
| 5.1.5-5.1.6 | runs based on median | median; binary uses 0.5 | :94-102, :365-379, utils.h:701-723 | yes | Computed on translated symbols, which is equivalent because translation preserves order. The reported median is a different matter (IID-03). |
| 5.1.7-5.1.8 | collisions | list C of window lengths; binary uses Conv II | :190-246 | yes | Empty C gives NaN, which fails the test (conservative, tiny inputs only). |
| 5.1.9 | periodicity p∈{1,2,8,16,32} | binary uses Conv I | :253-265, :398-416 | yes | `assert(n>=p)` aborts when n<32 (#261 family). |
| 5.1.10 | covariance | Σ s_i s_{i+p}; binary uses Conv I | :272-280, :418-436, :451-456 | yes | Raw values for k>2. |
| 5.1.11 | compression | "v v v" string, bzip2 | :287-334 | yes | Buffers correct (log10 width+2, NUL; 1.01×+600). blockSize100k=5 is a valid choice because the spec gives no parameter. |
| §5.2.1 | non-binary independence | e=p_i p_j L/2, bins ≥5, merge last, df=nbin−k | chi_square_tests.h:383-421, 531-558 | yes* | floor(L/2) is maintainer position #62. When df<1 the spec says "do not apply the test"; the code returns p=1 ("Passed"), which is equivalent. |
| §5.2.2 | non-binary GOF | e_i=c_i/10, 10 subsets, df=9(nbin−1) | :596-633 | yes* | (c_i/L)·⌊L/10⌋ is maintainer position #91. |
| §5.2.3 | binary independence | **"If m is 1, the test fails."** | :470-489, 649, 279-281 | **NO** | m=1 returns T=0, df=0, p=1 and the result is "Passed". **IID-01** |
| §5.2.3 | binary independence | m rule, ⌊L/m⌋ blocks, e, df=2^m−2 | :463-519 | yes | Spec example (p0=0.86, L=1000) gives m=2 as printed. |
| §5.2.4 | binary GOF | e0, e1, df=9 | :560-594 | yes | NaN when L<10, which "passes" (#261 family). |
| §5.2 | p-values | Q(df/2, T/2) | :368-370, cephes | yes | 252 grid points, df 1..65280, p from 1e-100 to 0.9999999, against mpmath: worst relative error 6.4e-11 and no verdict flips at 0.001. |
| §5.2.5 | LRS test | p_col, W, N=C(L−W+1,2), Pr(X≥1)<0.001 fails | lrs_test.h:617-716 | yes | Log-domain. Asserts: p_col≥1/k (#246, fix incomplete, §5) and p_col^W≥LDBL_MIN (#153). |
| §3.1.1 item 2, §3.1.2 item 4 | conditioned data IID testing | "treated as a binary string for testing purposes"; §5 tests on it | iid_main.cpp:255, 316, 334, 352 | **NO** | Under `-c` the §5 tests run on the packed symbols, while h' is computed on the bitstring. **IID-02** |
| §3.1.3 | H_I = min(H_orig, n·H_bitstring) | | iid_main.cpp:276-313 | text yes | JSON value is #251. Alphabet-size gate is #253. "First 1e6 bits may be ignored" is implemented as `-t` (:240). |
| §6.1, §6.3.1 | MCV | p_u = p̂ + z·sqrt(p̂(1−p̂)/(L−1)) | most_common.h:7-43 | yes | z_α is #22 / F07. |
| §3.1.1 item 1 | ≥1e6 samples | | iid_main.cpp:243 | warning only | #255. |

---

## 2. Tests run

- **Edge-length matrix.** `work/iid/edge/{gen.py,run.sh,rel.txt,asan.txt}`. Lengths 0–40, 47, 48, 63, 64, 100, 255, 256, 257, 300 and 1000, times five patterns (rand8, binary, constant, two-valued {3,200}, all-distinct), 256 files, run under both builds.
  - Release: empty is refused; constant gives "1 symbol" and exit −1.
  - Asserts, all on tiny inputs (#261 family):
    - `periodicity n>=p` for non-binary L<32 and binary L<256;
    - `p_colPower <= 1-LDBL_EPSILON` when W=0 (all-distinct);
    - `p_col >= 1/k` (all-distinct with k∈{3,6,7,9,12,…}).
  - ASan/UBSan: **no ASan memory errors**. UBSan reports only float divide-by-zero:
    - chi_square_tests.h:589 (binary GOF with L<10);
    - chi_square_tests.h:439;
    - utils.h:839 (`divide(0,0)` in avg_collision when there are no collisions).
  - The chi-square independence df is ≤0 for every rand8 file with L≤1000 (spec: do not apply; tool: "Passed").
- **Differential test against an independent literal implementation.** `work/iid/ref/{ref90b.py,compare.py,compare_rel2.txt}`, written from the spec text in Python with exact fractions and mpmath.
  - 30 inputs: L∈{300, 1001, 4007} × {rand8, 3-symbol, 4-bit, binary, biased binary, two-valued, geometric, period-29, drift, binary period}.
  - Compared: all 19 unpermuted §5.1 statistics, chi-square T/df/p (both tests), and LRS P_col/W/Pr.
  - Result: **0 mismatches**. per_4007 aborted at the LRS underflow assert (#153).
- **Metamorphic checks** (`work/iid/meta`), L=5000:
  - An order-preserving relabel leaves all rank- and equality-based statistics, chi-square and LRS identical.
  - An arbitrary bijection leaves collision, periodicity, GOF, W and P_col identical. The P_col difference was ≤1e-20.
  - Time reversal leaves excursion and GOF T equal up to rounding (≤3e-14).
  - Binary {0,1}→{5,9} changes only the excursion (×4 exactly), as the spec implies.
- **p-value numerics** (`work/iid/pval`): harness around `chi_square_pvalue` compared with mpmath; results in the table above.
- **RNG and shuffle** (`work/iid/rng/fy.cpp`): uniformity, the bound check, data/rawdata kept in step, and jumped streams distinct. All passed.
- **Threads** (`work/iid/threads`): OMP_NUM_THREADS 1/2/4/8 × 2 repeats on a failing L=2000 input (`mix.bin`, drift plus noise). In all 8 runs, 16 of the 19 tests stayed undecided and their C0+C1+C2 was exactly 10000, with no lost or duplicated rounds. The 3 decided tests stopped at 6–110 rounds. The verdict was Failed every time.
- **ThreadSanitizer.** `work/iid/tsan`, gcc -fsanitize=thread, run under `setarch -R`. The real race it found is IID-04. The other reports concern `C[][]` inside `omp critical` and are false positives, because TSan does not model libgomp's critical sections.
- **1e6-sample non-IID constructions** (`work/iid/noniid/gen.py`), chi-square and LRS stage only:

  | Input | Result |
  |---|---|
  | counter mod 256 | independence p=0, then **abort** at the LRS assert (#153) |
  | sine drift + noise | χ² fails (p=0/0) |
  | binary Markov P(stay)=0.6 | independence p=0 |
  | 8-bit random walk | χ² and LRS fail |
  | sorted 1000-blocks | χ² and LRS fail |
  | sticky8 (repeat previous sample with probability 0.01) | independence p=1.5e-237 |
  | pair4 (weak pairwise dependence) | independence p=0 |

  None of these clearly non-IID inputs passed. The two passes found are spec deviations (IID-01, IID-02), not weak tests.
- **Findings reproductions:** see each finding. Full 1e6 runs: `f01/run1.txt`, `run2.txt`; `f02/c_run1.txt`, `c_run2.txt`, `bits_run1.txt`, `noniid_c.txt`; `f01/noniid.txt`.

---

## 3. CONFIRMED NOVEL findings

### IID-01 — Binary chi-square independence with m = 1 is reported as PASSED; §5.2.3 says "If m is 1, the test fails"

Category **A** (entropy/verdict correctness). Confidence **HIGH**. Affected executable: `ea_iid`. The same function is used by `ea_restart`'s row/column IID testing, not exercised here.

**Location.** `cpp/iid/chi_square_tests.h`:
- `binary_chi_square_independence`, lines 470-489: the m search at 474-480, then `if (m < 2){ score = 0.0; df = 0; return; }` at 485-489.
- `chi_square_tests`, lines 649 and 664.
- `cephes_igamc`, lines 279-281, which returns 1.0 for a ≤ 0.

**SP 800-90B:** §5.2.3 step 2. **Valid ≥1,000,000-sample case: yes.**

**DIRECTION:** IID wrongly accepted, so the entropy is TOO HIGH. For the reproducer, the IID-track figure 0.0027051 exceeds the non-IID figure 0.0019686 on the same file (1.37×).

**Root cause.** SP 800-90B §5.2.3 step 2 reads: "Find the maximum integer m such that min(p0,p1)^m ⌊L/m⌋ ≥ 5. If m is greater than 11, set m = 11. **If m is 1, the test fails.** … The test is applied if m ≥ 2."

The code treats m = 1 as "not applicable": it returns score 0 and df 0. `chi_square_pvalue(0, 0)` calls `cephes_igamc(0, 0)`, whose `a <= 0` branch returns 1.0. Since 1.0 is not below 0.001, the independence test is reported as Passed, the chi-square battery as Passed, and JSON `passedChiSquareTests: true`.

The case is reachable for any binary dataset whose minority symbol count c satisfies (c/L)²·⌊L/2⌋ < 5. At L = 10^6 that is **c ≤ 3162**. The comment at line 491 ("Test is only run if m >= 2") reflects the draft-era behaviour (#28), not the final text.

**Minimal reproduction** (deterministic; the chi-square stage precedes the stochastic permutation stage):

```
cd SCR/audit/work/iid/f01
python3 -c "import random; r=random.Random(2); v=[1]*99+[0]*901; r.shuffle(v); open('min_m1_L1000.bin','wb').write(bytes(v))"
ea_iid -vvv min_m1_L1000.bin 1        # (99 ones: 0.099^2*500 = 4.9 < 5 -> m = 1)
```

1e6 conforming case (IID Bernoulli(0.002), 1988 ones):

```
python3 gen_bern.py 0.002 2026 bern002.bin   # gen_bern.py in f01/: bytes(1 if r.random()<p else 0 for 10**6 draws), random.Random(seed)
# sha256 df7cacae29c3b3352a38986f9bd9fe08c270cd4c0b3c64215e140973861696c3
ea_iid -vvv -o run1.json bern002.bin 1
```

Boundary files: `ones_3162.bin` gives m=1 and `ones_3163.bin` gives m=2 (see §4 note).

**Actual.** run1 was `-vvv`, 20 min under load. run2 was `-vv -o run2.json`, 12 min. Both runs are identical in the deterministic part, both runs passed all three batteries, and their permutation C tables differ only stochastically, with no starred test. Run1:

```
Loaded 1000000 samples of 2 distinct 1-bit-wide symbols
H_original = 0.0027050855620361102
Chi square independence: T = 0
Chi square independence: df = 0
Chi square independence: P-value = 1
Chi square goodness of fit: T = 5.6732502524878612 ... P-value = 0.7721227505025321
Chi square tests: Passed
Literal Longest Repeated Substring results: W = 4929 ... Pr(X >= 1) = 1
Length of longest repeated substring test: Passed
IID permutation tests: Passed
JSON: "passedChiSquareTests" : true, "passedIidPermutationTests" : true,
      "passedLongestRepeatedSubstringTest" : true, "hAssessed" : 0.0027050855620361102
```

The L=1000 file prints the same `T = 0 / df = 0 / P-value = 1 / Chi square tests: Passed`. With 100 ones it runs normally (m=2, df=2).

**Expected.** Per §5.2.3 the binary independence test **fails**. Per §3.1.2 item 2 the IID assumption is then not verified, so the non-IID track is mandatory.

On the same file, `ea_non_iid -vv bern002.bin 1` gives H_original = **0.0019686141144834844** (compression estimate). The IID track reports **0.0027050855620361102**, 37 % higher.

**Impact.** Every heavily biased binary source (minority fraction below about 0.316 % at 10^6 samples, scaling as sqrt(10/L)) gets its independence test waved through. The whole IID verdict then rests on the permutation and LRS tests, and the IID track can be selected where the spec forbids it.

The absolute entropies involved are small (below about 0.0046 bit/sample), but the verdict is wrong in the dangerous direction and the figure can exceed the non-IID assessment (1.37× here). It is not reachable for k > 2, since §5.2.1 has its own "df < 1 → do not apply" rule, which the code honours.

**Deduplication proof.** grep terms on all.md: `m is 1`, `m < 2`, `m<2`, `m >= 2`, `binary_chi_square_independence`, `df = 0`, `df=0`, `df == 0`, `do not apply`, `not applied`, `test fails`, `igamc`.
- Only #28 (draft-era, 2017) contains "If m is 1, the test fails", inside Joshua Hill's proposed Python, which itself returned `None` for m=1. It was closed as "addressed in the final SP800-90B document". The final text keeps "the test fails", and the C++ implements the draft "not applicable" behaviour.
- #93 (statistic iterated tuples, fixed), #235 (always run both χ² tests) and #12 (Python `assert df > 0`, non-binary, sub-minimum data) are different root causes.
- The exclusion map's `chi_square_tests.h` index (#60 #62 #63 #88–#93 #97 #120 #235; py #4 #12 #28 #29) contains no m=1 handling item.
- Not addressed by open PRs #251/#252/#256/#268/#270.

**Fix direction.** In `binary_chi_square_independence`, when m < 2, signal an explicit failure (for example `score = INFINITY; df = 1`, or a returned status) so that `chi_square_tests` sets `result = false` and prints "m = 1: binary independence test fails (SP 800-90B §5.2.3)". Update the comment at :491.

**Regression test.** `min_m1_L1000.bin` (above) must print "Failed chi square tests". The spec example (140 ones in 1000) must still yield m=2, df=2 and pass. The 1e6 boundary pair `ones_3162.bin` / `ones_3163.bin` must fail and run normally, respectively.

### IID-02 — `ea_iid -c` runs the §5 IID tests on the packed symbols, not on the conditioned binary string, so non-IID conditioned output passes and h' is overstated

Category **A**. Confidence **HIGH**. Affected executable: `ea_iid` (in `-c` mode).

**Location.** `cpp/iid_main.cpp:main`:
- lines 255 (`calc_stats(&data,…)`), 316 (`chi_square_tests(data.symbols, sample_size, alphabet_size, …)`), 334 (`len_LRS_test(data.symbols, …)`) and 352 (`permutation_tests(&data, …)`) all run unconditionally on the sample-level data;
- by contrast, lines 281-282 compute h' from `data.bsymbols` when `!initial_entropy`.

**SP 800-90B:** §3.1.1 item 2 ("The output of the conditioning component shall be concatenated … and **treated as a binary string for testing purposes**"), §3.1.2 item 4 (that dataset "is tested using the statistical tests described in Section 5"), and §3.1.5.2 ("shall be treated as a binary string").

**Valid ≥1,000,000-sample case: yes.**

**DIRECTION:** IID wrongly accepted, so h' is TOO HIGH: 0.99864 bit/bit reported, against a true 0.5 and a non-IID-track value of 0.40351 (2.47×).

**Root cause.** The usage text says: "-c … The samples are converted to a bitstring. Returns h' = min(H_bitstring)". The README says: "-c: Indicates the data is conditioned, and should only be assessed as a bitstring". The maintainer said in #139: "all such data is treated as a binary string only, irrespective of its actual raw format".

`main` follows this for the MCV estimate, but all three §5 batteries still receive `data.symbols` / `data.len` / `alph_size` (for example 256 byte values). A conditioned output whose bytes are IID but whose bits are dependent therefore passes the IID tests, and the bitstring MCV then reports near-full entropy per bit.

**Minimal reproduction** (`work/iid/f02`). The generator `nib_small.bin` is 20,000 bytes of `(r<<4)|r`, r uniform on 0..15, seed 7; `nib_small_bits.bin` is the same bytes expanded MSB-first, one bit per byte:

```
ea_iid -v -c nib_small.bin 8        -> h': 0.986982 ; ** Passed chi square tests ; ** Passed length of longest repeated substring test ; ** Passed IID permutation tests
ea_iid -v -c nib_small_bits.bin 1   -> h': 0.986982 ; independence p-value = 0.000000 ** Failed chi square tests ; Pr(X >= 1): 0.000000 ** Failed length of longest repeated substring test
```

That is the same conditioned data and the same h', but opposite IID verdicts depending only on how the bytes are packed.

**1e6 reproduction.** `python3 gen_nib.py` builds `nibdup.bin`: 1,000,000 bytes, seed 4242, sha256 `4f043adf…fc25`. It also builds the first 10^6 bits of it as `nibdup_bits_1e6.bin`, sha256 `097b5c88…7fae`.

**Actual, run 1** (`ea_iid -vvv -c -o c_run1.json nibdup.bin 8`) and **run 2** (`ea_iid -v -c -o c_run2.json nibdup.bin 8`):

```
Loaded 1000000 samples of 16 distinct 8-bit-wide symbols ; Number of Binary samples: 8000000
H_bitstring = 0.99863990110688217            (run 2: "h': 0.998640")
Chi square independence: T = 291.75447437146249, df = 240, P-value = 0.012513585787585843
Chi square goodness of fit: T = 130.88447635893525, df = 135, P-value = 0.58408842119161442
Chi square tests: Passed
Literal Longest Repeated Substring results: W = 9, Pr(X >= 1) = 0.9993083036985428
IID permutation tests: Passed        (both runs; the C tables differ stochastically, none starred)
c_run2.json: "hBitstring" : 0.99863990110688217, all three "passed…" : true, "errorLevel" : 0
```

**Expected.** The §5 tests on the conditioned binary string, via `ea_iid -vvv nibdup_bits_1e6.bin 1`, give:

```
Chi square independence: T = 330211.83704426914, df = 2046, P-value = 0      -> Failed
Chi square goodness of fit: P-value = 0.00054579                            -> Failed
Length of longest repeated substring: W = 67, Pr(X >= 1) = 3.39e-09          -> Failed
```

So the IID assumption is not verified, and the non-IID track applies. `ea_non_iid -vv -c nibdup.bin 8` gives **h' = H_bitstring = 0.40350695467166003**, with LZ78Y 0.687, MultiMCW 0.765 and Lag/MultiMMC 0.415. The true min-entropy is 4 bits per 8, i.e. 0.5 bit/bit.

`ea_iid -c` reports 0.99864, which is **2.47× the non-IID value and 2.0× the true value**. In §3.1.5.2, h_out = min(Output_Entropy, 0.999·n_out, h'·n_out), so an inflated h' raises h_out whenever the h' term binds.

**Impact.** Any user following the documented `ea_iid -c <file> 8` route for a non-vetted conditioner's output gets an IID verdict computed on an arbitrary byte chunking of the binary string. Within-byte or cross-byte bit dependencies that the §5 tests would catch on the binary string go untested, and h' can be overstated by up to the ratio of the per-bit MCV to the true per-bit entropy.

Declaring the data 1-bit-per-byte avoids the defect. Also, `ea_non_iid -c` is unaffected, because its estimators all use `bsymbols`.

**Deduplication proof.** grep terms on all.md: `ea_iid -c`, `conditioned`, `binary string`, `as a bitstring`, `initial_entropy`, `-c flag`, `3.1.5.2`, `3.1.1 item 2`, `Section 5`.
- Hits: #121, where J says ea_iid "would support" §3.1.2 test 3; #139, J's comment that -c data "is treated as a binary string only", which supports this finding; and #127/#139/#140 on `-t` semantics.
- #210 is about ea_conditioning's h' (different executable, fixed in #204). F20 and F23 in the prior audit concern `-t` truncation and JSON hAssessed.
- No item concerns which data the §5 batteries run on under `-c`. #251 (JSON hAssessed = 8.0, also visible in c_run2.json) is a separate, known reporting defect. #253 is not involved: h' is computed from bsymbols whenever `-c` is set.

**Fix direction.** Under `-c`, build a binary view `data_t bview = {word_size=1, alph_size=2, symbols=rawsymbols=bsymbols, len=blen, maxsymbol=1}` and pass it to `calc_stats`, `chi_square_tests`, `len_LRS_test` and `permutation_tests`. Alternatively, refuse `-c` with bits_per_symbol > 1 and ask for 1-bit-per-byte input. Document the cost: permutation testing on 8×L bits.

**Regression test.** `nib_small.bin` with `-c … 8` must produce the same three verdicts as `nib_small_bits.bin` with `-c … 1` (all Failed). IID byte data such as `r.randrange(256)` must still pass under `-c … 8`.

### IID-03 — Reported/JSON "median" is the median of translated symbol indices, not of the data (the mean next to it is raw)

Category **E** (reporting). Confidence **HIGH** (mechanism). Affected executable: `ea_iid`.

**Location.** `cpp/shared/utils.h:calc_stats:701-723` sorts `dp->symbols`, the translated values. `iid_main.cpp:258/263` prints it and `:269` stores it as `tc.median`, which becomes JSON `"median"` (`iid_test_case.h:33-34`). Meanwhile `rawmean` uses `rawsymbols`.

**SP 800-90B:** §5.1.5 step 1 (median of S). **Valid ≥1e6 case: yes.** **DIRECTION:** none; the verdict is unaffected (see below).

**Root cause.** Using the translated median inside `alt_sequence2` is correct, because translation preserves order and no sample lies strictly between two adjacent order statistics. The same number is then published as the dataset median.

**Reproduction.** Using `nibdup.bin` (above), `c_run2.json` has `"mean" : 127.557987, "median" : 8.0`, while the data's actual median is 136 (`python3 -c "d=sorted(open('nibdup.bin','rb').read()); print((d[499999]+d[500000])/2)"` prints 136.0). Text output shows `Raw Mean: 127.557987 / Median: 8.000000`.

**Expected.** Either report the median of the raw values, or label the field as a translated-index median.

**Impact.** Reporting only. A reviewer reading the JSON or text sees a median inconsistent with the stated mean and with the data. Binary data prints 0.5, which is spec-mandated. The verdict is unaffected.

**Deduplication.** grep `median`, `calc_stats`, `translated` in all.md. #82 (median formula, parity) and #15/#107 (conversion before the median tests) cover other things. The exclusion map's `calc_stats` index lists only #82.

**Fix.** Compute a raw median for reporting, or map it back through the translation table.

**Regression.** For `nibdup.bin`, JSON median must equal 136.

### IID-04 — Data race on `test_status[]` in the OpenMP permutation loop (TSan-confirmed; no wrong verdict observed)

Category **B** (UB). Confidence **MEDIUM** on existence, since TSan shows it; **LOW** on consequence. Affected executable: `ea_iid`. The same code is reached by `ea_restart`'s IID tests.

**Location.** `cpp/iid/permutation_tests.h:permutation_tests`:
- `bool test_status[num_tests]` (:587) is shared by the `omp parallel` region;
- it is **written** inside `omp critical(resultUpdate)` at :670;
- it is **read without synchronization** by `run_tests(…, test_status)` at :655, through every helper (for example :344, :351, :359-361, :400-412, :420-433, :440).

**SP:** n/a (implementation). **≥1e6 case:** yes, every multi-threaded run. **DIRECTION:** none observed.

**Evidence.** Built at `work/iid/tsan` with `g++ -fopenmp -O1 -g -fsanitize=thread` and run with `setarch x86_64 -R ./ea_iid_tsan -v r8_3000.bin 8`. TSan reports a race whose read is in `periodicity_tests … permutation_tests.h:411` and whose write is at :670. The other TSan reports, on `C[][]` at :662-676, are false positives from uninstrumented libgomp critical sections.

**Analysis.** This is a data race on a non-atomic object, which is undefined behaviour in C++11. With current compilers it is benign:
- the flag only changes from true to false;
- a stale read only computes an unneeded statistic;
- a statistic left un-updated can never be counted, because the counting branch re-reads the flag under the lock.

In differential runs with 1–8 threads, every undecided test's C0+C1+C2 was exactly 10000, and verdicts matched.

**Dedup.** grep `race`, `data race`, `thread safe`, `test_status`, `TSan`, `passed_count`. Only #45/#54 mention rand() thread-safety (fixed by #77). The exclusion map's permutation_tests threading items are #86 #97 #99, which are about performance and stack size.

**Fix.** Snapshot `test_status` into a thread-private array inside the critical section and pass that copy to `run_tests`, or use `std::atomic<bool>` with relaxed loads.

**Regression.** A TSan build shows no report whose frames lie in `run_tests` helpers.

---

## 4. Suspected / needing more work

- **IID-01 boundary at 10^6: done.** `f01/ones_3162.bin` gives `independence: T = 0, df = 0, P-value = 1, Chi square tests: Passed`. `f01/ones_3163.bin` gives `T = 0.16777801365130973, df = 2, P-value = 0.9195`. The boundary is exactly where §5.2.3 puts it.
- **IID-02 across more data shapes.** I only demonstrated nibble duplication. Any conditioner output with intra-byte dependence behaves the same way. Cross-byte bit dependencies aligned to byte boundaries could be caught by the byte-level tests anyway.
- **bzip2 block size 5 vs the `bzip2` default of 9** (§5.1.11 names [BZ2] without parameters). The permutation test stays valid, and only power against repeats more than about 500 kB apart differs. That case is also caught by the LRS test. I did not quantify it; no finding.
- **Excursion ties.** `(i+1)*rawmean` in double can split mathematically equal excursions, which moves a tie from C1 to C0 or C2. That can only increase rejections, so it is conservative, and at L ≤ 10^8 the probability of it happening is negligible.

---

## 5. EXCLUDED AS ALREADY KNOWN (rediscoveries)

- **`p_col >= 1/k` assert still fires** (`lrs_test.h:626`) → **#246, closed and "fixed" by #248, but the fix is incomplete** (reopen candidate). With counts computed exactly, `p_i = fl(1/k)` rounds below 1/k for k ∈ {3,6,7,9,12,14,15,17,18,19,21,23,24,27,…,255}. Every exactly-uniform dataset with such k therefore aborts.
  - 1e6 reproducer: `work/iid/f03/bal3.bin`, 1,000,002 samples of {10,20,30} with exactly 333,334 each, shuffled (seed 3), sha256 `2086beee…92d1`.
  - Result: `ea_iid -v -o bal3.json bal3.bin` gives "Assertion `p_col >= 1.0L / ((long double) k)' failed", rc 134 and no JSON. It reproduced twice.
  - Same root-cause family as #246 (a floating-point p_col compared strictly with 1/k). Joshua Hill's alternative suggestion in #246 (snap values near 1/k) would fix it.
- **LRS test aborts on long repeats** (`lrs_test.h:657`, `assert(p_colPower >= LDBL_MIN)`) → **#153 item 2** (maintainer: "can be detected"). At 1e6 samples, one duplicated 2,100-byte region in random 8-bit data aborts ea_iid with no verdict or JSON (`work/iid/k153/dup2100.bin`). So do the counter mod 256 input (`noniid/counter8.bin`) and a period-29 input at L=4007. The verdict is in fact decidable in logs (log Pr ≈ log N + W·log p_col ≪ log 0.001), so the abort is avoidable, but this is the known design.
- **Tiny-input asserts and NaN** → **#261/#262 family** (no minimum-length validation):
  - `periodicity assert(n>=p)` for L<32, or binary L<256;
  - W=0 `p_colPower <= 1-LDBL_EPSILON`;
  - binary GOF e0=0 for L<10, giving NaN, which is reported as a pass because NaN is not below 0.001;
  - `divide(0,0)` in avg_collision, giving NaN (conservative fail);
  - `lgam`/`calc_T` division by zero on tiny inputs.
- **JSON `hAssessed` = word size at default verbosity** → **#251** (seen again in `f02/c_run2.json`: hAssessed 8.0 with hBitstring 0.9986).
- **Min-entropy printed even when IID tests fail** → **#252**.
- **Two-valued multi-bit data takes the binary H path** (iid_main.cpp:281/290/300) → **#253**. The §5 binary gate itself is spec-literal (k=2).
- **Inferred width** → **#254**. **Sub-minimum L is a warning only** → **#255**. **`-l` arithmetic/hash** → **#260**. **sha256 on /dev/zero** → **#259**.
- **Run-to-run permutation variability, early exit, ~2 % per-round false failure** → **#220/#247/#239**.
- **floor(L/2)** in independence expectations → **#62**. **(c_i/L)·⌊L/10⌋** in GOF → **#91**.
- **`-t` in `-c` mode** → **F20 / #139 / #127 / #140**.
- **Non-binary independence df < 1 reported as "Passed"**: the spec explicitly says "If the value of degrees of freedom is less than one, do not apply the test". This is spec-consistent. The Python-era `assert df > 0` was #12.
- **`int sample_size = data.len`** (iid_main.cpp:250) and `unsigned int curlen` in compression: truncation above 2^31 samples, or about 1.07e9 samples at 4 chars each. Theoretical; falls under maintainer position #228 ("don't do that") and #226.

---

## 6. No-finding areas (attacked and held)

- **All 19 permutation statistics, both conversions, the median rule and binary handling**: they match a literal implementation on 30 inputs, and metamorphic invariances hold (§2).
- **Rank and tie counting** (strict > for C0, == for C1), the reject rule, and the early-exit equivalence proof.
- **Fisher–Yates and Lemire bounded integers** (bias and range), seeding from /dev/urandom, per-thread xoshiro jumps, and data/rawdata staying in step. The static mutex in `FYshuffle` serialises shuffles; that is a performance issue only.
- **OpenMP**: no lost or duplicated rounds at 1/2/4/8 threads, and verdicts are stable on failing input. The only real race is IID-04, which is benign.
- **Compression statistic**: string encoding identical to the spec, buffer sizes adequate (no ASan reports on 256 edge files, including k ≤ 10), and `rc != BZ_OK` is unreachable with the documented buffer bound.
- **Chi-square p-values** (cephes igamc) against mpmath: relative error ≤ 6.4e-11 up to df 65,280, with no threshold flips.
- **LRS test arithmetic**: log-domain, and P_col, W and Pr match the reference (Pr within 1e-9 relative).
- **Integer ranges**: covariance sums are 64-bit, periodicity sums are 32-bit (≤ L), and the collision sum is ≤ L. No overflow at L ≤ 2^31.
- **Seven clearly non-IID 1e6 constructions** (counter, drift, Markov, random walk, sorted blocks, sticky, pair) fail or abort. None passed except through IID-01 and IID-02.
- **MCV / H_original / n·H_bitstring**: correct at `-vvv`. The JSON defect at other verbosity levels is #251.
