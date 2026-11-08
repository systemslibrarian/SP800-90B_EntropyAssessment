# Analysis: IID chi-square tests (§5.2.1–§5.2.4) and the LRS length test (§5.2.5)

Audit 2026-11-07, analysis phase. Branch `audit/2026-11-07`. Component files, every line read:
`cpp/iid/chi_square_tests.h` (728 lines), `cpp/shared/lrs_test.h` `len_LRS32/64` (:595–621),
`calc_collision_proportion` (:628–635) and `len_LRS_test` (:643–771), `cpp/iid_main.cpp` (586 lines).
Helpers read: `cpp/shared/utils.h` `calc_proportions` (:967–977), `n_choose_2` (:1027–1030),
`divide` (:1083–1085), `relEpsilonEqual` (:115–), `read_file_subset` symbol translation (:499–546),
`dataset_meets_minimum` (:294–316), `MIN_SIZE` (:42). Second caller read at its call site:
`cpp/restart_main.cpp:830–831, 1093–1125` (`int sample_size = data.len`, `int alphabet_size = data.alph_size`;
rows AND columns must both pass).

Spec text: `reference/sp800-90b.pages.txt`, §5 intro PDF p. 37, §5.2 PDF p. 43–47.

Binary measured (instrument rule 4): `cpp/ea_iid`
sha256 `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349` (not rebuilt; production binary).
Every probe used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` on inputs of 100–2,000 samples and is
NON-COMPLIANT by construction (brief ground rule 5). Probe script, manifest with input sha256s, driver log
and per-run outputs: `logs/analysis-iid-chisq-probe.py`, `logs/analysis-iid-chisq-probe-manifest.txt`,
`logs/analysis-iid-chisq-probe.log`, `logs/analysis-iid-chisq-{ex11,bin140,ex12,dfneg}.out`;
inputs at `corpus/iid-chisq-*.bin`.

**Headline.** No CRITICAL or HIGH candidate in this component. The binning, pair counting, m-selection
and degrees of freedom reproduce all three of the standard's worked examples exactly (Example 11:
T = 3.4571 vs the text's 3.46, df = 3; §5.2.3's p1 = 0.14, L = 1000 example: m = 2, df = 2;
Example 12: nbin = 3, GOF df = 18). The §5.2.5 decision is a correct monotone transform of the
printed inequality, inclusive at the boundary, and all three fork repairs that touch it (R-1, #153,
C18) move only in the conservative or value-preserving direction; I could not construct a break.
One suspicion is CONFIRMED by measurement and is LOW: when the non-binary independence test has
nbin ≤ k, the standard says "do not apply the test" and the tool instead prints a negative or zero
df with a p-value of exactly 1 and counts the test as *passed* — the verdict is the same as the
standard's non-application, so the direction is neutral, but the report misdescribes what happened
and the pass rests on an incidental Cephes guard. Two literal-text parity items (floor(L/2) and
p_i·floor(L/10) where the text prints L/2 and c_i/10) and one spec typo (27.887 for 27.877) are
recorded as D-class characterisations, not defects.

---

## 1. The spec, step by step

### 1.0 What a chi-square failure means (§5 intro, PDF p. 37)

> "These tests take the sequence S = (s1,…,sL), where si ∈ A = {x1,…,xk}, as input, and test the
> hypothesis that the values in S are IID. If the hypothesis is rejected by any of the tests, the
> values in S are assumed to be non-IID."

So a chi-square or LRS *failure* removes the IID track; the min-entropy figure then comes from the
§6.3 battery (min over ten estimators) instead of the MCV estimate alone. Because the IID figure is
MCV and the non-IID figure is `min(MCV, …)`, **any wrongful IID acceptance can only raise the figure**
— that is the direction this component can overstate in, and it is what N-01 was.

### 1.1 §5.2.1 Independence, non-binary (PDF p. 43–44)

> "1. Find the proportion p_i of each x_i in S, i.e., p_i = (number of x_i in S)/L. Calculate the
> expected number of occurrences of each possible pair (z_i, z_j) in S, as e_{i,j} = p_i p_j L/2.
> 2. Allocate the possible (z_i, z_j) pairs, starting from the smallest e_{i,j}, into bins such that
> the expected value of each bin is at least five. The expected value of a bin is equal to the sum
> of the e_{i,j} values of the pairs that are included in the bin. After allocating all pairs, if the
> expected value of the last bin is less than five, merge the last two bins. Let nbin be the number
> of bins constructed using this procedure."

> "1. Let o be a list of nbin counts, each initialized to 0. For j=1 to L-1:
> a. If the pair (s_j, s_{j+1}) is in bin i, increment o_i by 1. b. Let j = j+2.
> 2. The test statistic is calculated as T = Σ_{i=1}^{nbin} (o_i − E(Bin_i))² / E(Bin_i). The test
> fails if T is greater than the critical value of the Chi-square test statistic with
> (nbin –1) – (k–1) = nbin –k degrees of freedom when the probability of type I error is chosen as
> 0.001. **If the value of degrees of freedom is less than one, do not apply the test.**"

Fixed points: non-overlapping pairs (stride 2; floor(L/2) pairs are counted though the text prints
L/2 in e_{i,j}); bins closed at ≥ 5 ("at least five"), last-bin merge when < 5; df = nbin − k;
fail iff T > χ²_{0.999}(df) (strict); **not applied** when df < 1. The text does not say in which
order tied e_{i,j} are placed. Example 11 (PDF p. 44): k = 3, p = 0.21/0.41/0.38, L = 100,
sorted e = 2.21, 3.99, 3.99, 4.31, 4.31, 7.22, 7.79, 7.79, 8.41 → 6 bins
{(1,1),(1,3)} {(3,1),(1,2)} {(2,1),(3,3)} {(2,3)} {(3,2)} {(2,2)}, o = 7, 6, 10, 8, 12, 7,
T = 3.46, df = 3, critical value 16.266.

### 1.2 §5.2.2 Goodness-of-fit, non-binary (PDF p. 45)

> "1. Let c_i be the number of occurrences of x_i in the entire dataset S, and let e_i = c_i/10 …
> 3. Starting from List[1], allocate the sample values into bins. Assign consecutive List[i] values to
> a bin until the sum of the e_i for those binned items is at least five, then begin assigning the
> following List[i] value(s) to the next bin. If the expected value of the last bin is less than five,
> merge the last two bins. …
> 1. Partition S into ten non-overlapping sequences of length ⌊L/10⌋ … If L is not a multiple of 10,
> the remaining samples are not used. 2. T = 0. 3. For d = 0 to 9, 3.1 For i = 1 to nbin,
> 3.1.1 Let o_i be the total number of times the samples in Bin i appear in S_d. 3.1.2 T = T + (o_i − E_i)²/E_i.
> The test fails if the test statistic T is greater than the critical value of chi-square with
> 9(nbin −1) degrees of freedom when the type I error is chosen as 0.001."

Example 12: k = 4, c = 43, 55, 52, 10 → e = 4.3, 5.5, 5.2, 1.0 → List = [4, 1, 3, 2] → bins
{4,1} (5.3), {3} (5.2), {2} (5.5) → nbin = 3 (so df = 18).

### 1.3 §5.2.3 Independence, binary (PDF p. 45–46)

> "1. Let p0 and p1 be the proportion of zeroes and ones in S …
> 2. Find the maximum integer m such that min(p0, p1)^m ⌊L/m⌋ ≥ 5. If m is greater than 11, set
> m = 11. **If m is 1, the test fails.** For example, for p0 = 0.14, p1 = 0.86, and L = 1000, m = 2.
> The test is applied if m ≥ 2.
> 1. Initialize T to 0. 2. Partition S into non-overlapping m-bit blocks … If L is not a multiple of
> m, discard the remaining bits. 3. For each possible m-bit tuple (a1, …, am): a. Let o be the number
> of times that the pattern occurs in the input B. b. Let w be the number of ones in the tuple.
> c. Let e = p1^w (p0)^{m−w} ⌊L/m⌋. d. T = T + (o−e)²/e.
> The test fails if the test statistic T is greater than the critical value of chi-square with 2^m–2
> degrees of freedom, when the type I error is chosen as 0.001."

Worked check of the text's example: 0.14²·⌊1000/2⌋ = 9.8 ≥ 5; 0.14³·333 = 0.91 < 5 → m = 2.

### 1.4 §5.2.4 Goodness-of-fit, binary (PDF p. 46–47)

> "1. Let p be the proportion of ones in the entire sequence S … 2. Partition S into ten
> non-overlapping subsets of length ⌊L/10⌋ … remaining bits are discarded. 3. Initialize T to 0.
> 4. Let the expected number of zeros and ones in each sub-sequence S_d be e0 = (1 − p)⌊L/10⌋,
> e1 = p⌊L/10⌋. 5. For d = 0 to 9: … T = T + (o0 − e0)²/e0 + (o1 − e1)²/e1.
> T is a chi-square random variable with nine degrees of freedom. The test fails if T is larger
> than the critical value at 0.001, which is 27.887."

Note the text's constant. The 0.999 quantile of χ²(9) is **27.87716** (computed here by bisection on
the regularised upper gamma, `logs/analysis` driver run; `Q(4.5, 27.877/2) = 0.00100006`,
`Q(4.5, 27.887/2) = 0.000996228`). 27.887 is a transcription slip in the text.

### 1.5 §5.2.5 Length of the longest repeated substring (PDF p. 47)

> "1. Find the proportion p_i of each possible input value x_i in S … 2. Calculate the collision
> probability as p_col = Σ_{i=1}^{k} p_i². 3. Find the length of the longest repeated substring W, i.e.,
> find the largest W such that, for at least one i ≠ j, s_i = s_j, s_{i+1} = s_{j+1}, …, s_{i+W−1} = s_{j+W−1}.
> 4. The number of overlapping subsequences of length W in S is L–W+1, and the number of pairs of
> overlapping subsequences is C(L−W+1, 2). 5. Let X be a binomially distributed random variable with
> parameters N = C(L−W+1, 2) and a probability of success p_col^W. Calculate … Pr(X ≥ 1) = 1 − (1 − p_col^W)^N.
> The test fails if Pr(X ≥ 1) is less than 0.001."

Fixed points: pass iff Pr(X ≥ 1) ≥ 0.001 (inclusive pass); overlapping repeats count (i ≠ j only);
N = C(L−W+1, 2).

---

## 2. Spec → code map, with every disagreement quoted

### 2.1 Caller: `iid_main.cpp`

- Input: `read_file_subset` masks to `word_size` bits and translates the alphabet down to
  `0..alph_size-1` (`utils.h:506–545`), so every `symbols[i] < alph_size`. Under `-c`, `testdata`
  is a view onto `bsymbols` with `alph_size = 2`, `word_size = 1` (:378–386); bits are built from the
  un-translated masked values (`utils.h:520–535`) so the bitstring is the raw bit pattern. `-t`
  truncates `blen` to `MIN_SIZE` before the view is taken (:343), so h′ and the §5 tests see the same
  truncated bitstring.
- `testdata.len > INT_MAX` → refused (:393–408). So `test_sample_size` (`int`) is `≤ INT_MAX` and every
  `int` index expression below is in range; also makes `n_choose_2`'s `assert(n ≤ INT_MAX)` reachable
  only with `W = 0`, impossible at compliant sizes (W = 0 needs L ≤ k ≤ 256).
- `chi_square_tests(testdata.symbols, test_sample_size, test_alphabet_size, verbose)` (:480) and
  `len_LRS_test(…)` (:504–505) both always run; permutation tests only if both pass (:515);
  `iid_test_suite_pass = chi && LRS && perm` (:529–530); failure → `errorLevel 2`, no `hAssessed`,
  exit 1 (:534–546). Fail-closed as documented (#252/#271).
- What the JSON carries (`iid/iid_test_case.h:41–46`): `passedChiSquareTests`, `ranChiSquareTests`,
  `passedLongestRepeatedSubstringTest`, … — booleans only. **No df, T, p-value, m, nbin, W or p_col
  reaches the report**; those exist only on stdout at `-vv`/`-vvv`. This matters for 2.3(d) below.

### 2.2 p-value routine: `chi_square_pvalue` (:368–370) over Cephes `igamc` (:274–336)

- `p = igamc(df/2, T/2)` = Q(k/2, T/2) = 1 − CDF_{χ²_k}(T). Fail iff `p < 0.001` (:693, :723).
  Equivalent to the text's "T greater than the critical value" by monotonicity; at an exact tie both
  pass. Checked numerically: `Q(1.5, 16.266/2) = 0.00100011` (Example 11's critical value),
  `Q(1.5, 3.46/2) = 0.3260` — the tool printed `P-value = 0.32636628350523372` for T = 3.4571 (ex11).
- Guards: `igamc(a, x)`: `if ((x <= 0) || (a <= 0)) return 1.0` (:279–281). So **T = 0 → p = 1** (correct,
  perfect fit) and **df ≤ 0 → p = 1** (see 2.3(d)). `ax < -MAXLOG` → prints `igamc: UNDERFLOW` to
  stderr and returns 0 (:289–292) → p = 0 → FAIL — correct direction for astronomically large T.
- NaN/inf: a NaN or inf `T` reaches the continued fraction, `t` becomes NaN, `while (t > MACHEP)` exits,
  the function returns NaN, and `pvalue < 0.001` is **false → PASS**. I could not make T NaN or inf
  from this component: every bin expectation is > 0 (every translated symbol is present, so
  p_i > 0; bins hold ≥ 1 entry; see 2.3(b)), the binary `e ≥ 5` by the m-selection, and
  `T ≤ (L/2)²/5 ≈ 5e10` at L = 1e6. Recorded as a robustness note only — no input reaches it.

### 2.3 §5.2.1 `chi_square_independence` (:543–570) and helpers

(a) **Expectation** `independence_calc_expectations` (:383–394):
`e[index].expectation = p[i] * p[j] * floor(sample_size * 0.5);` — the text prints `p_i p_j L/2`.
Identical for even L (L = 1,000,000). For odd L the code uses ⌊L/2⌋, which is the number of pairs
actually counted in step 1 (both code and text count ⌊L/2⌋ pairs), so the code is self-consistent
and the text is not. Relative difference ≤ 1/L. **D-class literal-text parity**, not a defect;
a verdict can flip only if a p-value sits within ~1e-6 of 0.001. Direction indeterminate and
negligible. Upstream code unchanged.

(b) **Binning** `allocate_bins` (:396–421), input sorted by `expectationOrder` (:534–537: ascending
expectation, ties by ascending tuple index i·k+j):
```
for each entry (ascending):
    if(current_expectation >= 5.0) { close bin; start new }   // before adding this entry
    assign entry to current bin; current_expectation += e
if((current_bin != 0) && (current_expectation < 5.0)) merge last into previous
else push last
```
This is exactly "assign … until the sum is at least five, then begin assigning the following to the
next bin; if the last bin is < 5 merge the last two". Traced by hand on Example 11 → 6 bins with the
spec's membership (tie (1,3) before (3,1) matches the spec's table because (1,3) has the smaller tuple
index). **Measured** (`analysis-iid-chisq-ex11.out:14–16`): `T = 3.4571197058750198`, `df = 3`,
`P-value = 0.326`. Spec: 3.46, 3, (critical 16.266 → not rejected). Reproduced.
Bounds: `i` in the merge loop is `unsigned`; termination is guaranteed because `current_bin != 0`
implies `e[0].bin == 0 < current_bin`. Every bin has expectation > 0 (each holds ≥ 1 entry and all
e_{i,j} > 0). All bins except possibly a lone bin 0 are ≥ 5 after the merge.
Tie order is a spec ambiguity: with equal e the bin *boundaries* are fixed but the *membership* of
tied pairs is not, so T depends on the secondary sort. The code's choice matches Example 11; a
reference implementation must use the same order or the differential will show spurious T deltas
(edge case 6 below).

(c) **Observed** `independence_calc_observed` (:423–428): `for(int j = 0; j < sample_size-1; j+=2)`
→ pairs (0,1),(2,3),…, ⌊L/2⌋ of them — the text's stride-2 loop. `index = data[j]*alphabet_size +
data[j+1]` < k² ≤ 65,536 fits `uint16_t`; after the re-sort by `tupleOrder` (:559) `e[index].tuple == index`
so the lookup is a direct table. `o` is `vector<int>`, counts ≤ L/2 ≤ INT_MAX/2. No overflow:
`j + 2 ≤ sample_size ≤ INT_MAX`.

(d) **Degrees of freedom and the "do not apply" rule** — `df = bin_expectations.size() - alphabet_size;`
(:569). `size_t − int` wraps when nbin < k and the assignment to `int df` yields the negative value
(implementation-defined pre-C++20, modular in practice; not UB). Then `chi_square_pvalue(score, df)`
→ `igamc(a ≤ 0, ·)` → **1.0** → `pvalue < 0.001` false → the independence test is counted as PASSED.
The text: "If the value of degrees of freedom is less than one, do not apply the test."
**MEASURED** (`analysis-iid-chisq-dfneg.out:14–20`, L = 2,000, k = 3, counts 1992/4/4, hand-derived
sorted e = 0.004×4, 1.992×4, 992.016 → bins {0.016+1.992·3 = 5.992}, {1.992+992.016} → nbin = 2):
```
Chi square independence: T = 0.17059228241416982
Chi square independence: df = -1
Chi square independence: P-value = 1
Chi square goodness of fit: T = 0
Chi square goodness of fit: df = 0
Chi square goodness of fit: P-value = 1
Chi square tests: Passed
```
The battery then passed LRS and the permutation tests and awarded `Assessed min entropy:
0.00052001850873112214` (:73). Assessment: the *verdict* coincides with the standard's (a test that is
not applied does not reject; §5 intro: rejection needs a test to fail), so the direction is
**neutral**; what is wrong is the *description* — a negative df and a p-value of 1 are printed as if a
valid test had been evaluated, the JSON `passedChiSquareTests: true` cannot distinguish "applied and
passed" from "not applicable", and the pass is produced by Cephes' `a <= 0` guard rather than by a
decision the code makes. Reachability at compliant size (DERIVED, not measured): every pair with
e_{i,j} ≥ 5 closes a bin by itself, so nbin ≥ #{e_{i,j} ≥ 5} and the remaining mass (≈ 5e5 at
L = 1e6) sits in bins of 5–10 unless carried by a few huge entries; nbin ≤ k therefore forces one
symbol to carry ≳ 99 % of the mass, where the MCV estimate is already ≤ −log2(0.99) ≈ 0.015 bit/symbol.
The overstatement potential of a wrongful IID acceptance here is bounded by that figure.
**Severity LOW; suspicion → confirmed as a reporting deviation.** Also reachable through
`ea_restart -i` (same function, rows and columns).

(e) **GOF `df = 0` is consistent, not a defect**: with nbin = 1 every subset's o equals ⌊L/10⌋ exactly,
T = 0 identically, and χ² with 0 df has nothing to test; both ex11 (L = 100, e = 2.1/4.1/3.8 → one bin
after the merge) and dfneg show `T = 0, df = 0, P-value = 1`. The text gives no df < 1 rule for GOF;
the only difference from "not applied" is again the printed p-value.

### 2.4 §5.2.2 `goodness_of_fit` (:608–645)

- `e[j].expectation = p[j] * floor((double) sample_size / 10.0);` (:617) = (c_j/L)·⌊L/10⌋ — the text prints
  `e_i = c_i/10`. Identical when 10 | L (L = 1e6). For other L the code's E sums to the subset length
  ⌊L/10⌋ (the text's sums to L/10 — more than the subset holds). Relative difference ≤ 9/L.
  **D-class literal-text parity**; the standard's own binary variant (§5.2.4 step 4) uses the code's
  form, `p⌊L/10⌋`. Upstream code unchanged.
- Binning: same `allocate_bins`; hand-traced Example 12 → bins {1.0, 4.3}, {5.2}, {5.5} → nbin = 3.
  **Measured** (`analysis-iid-chisq-ex12.out:15–16`): `Chi square goodness of fit: df = 18` = 9·(3−1). Reproduced.
- Observed: `goodness_of_fit_calc_observed(data + j*block_size, e, o, block_size)` for j = 0..9 (:636–640),
  `block_size = sample_size/10` (:632) — S_d = s[d⌊L/10⌋ .. (d+1)⌊L/10⌋), remainder dropped. T accumulates
  `calc_T` per subset — the text's double sum. `df = 9*(bin_expectations.size()-1)` (:644).
  `j*block_size ≤ 9·(L/10) < L ≤ INT_MAX`: no overflow.

### 2.5 §5.2.3 `binary_chi_square_independence` (:460–532)

- p1 = Σ data[i] / L in double (:466–471); exact for L < 2^53.
- m-selection (:474–483):
  ```
  int m = 11; int threshhold = 5;
  while(m > 1){ if (pow(min_p, m) * (sample_size / m) >= threshhold) break; else m--; }
  ```
  `sample_size / m` is integer division = ⌊L/m⌋. Starts at 11 (the text's cap) and descends; since
  min_p ≤ 0.5 the quantity is decreasing in m, so the first m that satisfies is the maximum. ≥ 5
  inclusive as written. **Measured** on the text's own example (`analysis-iid-chisq-bin140.out:12`,
  L = 1000, 140 ones): `df = 2` → m = 2. Reproduced.
- **N-01 repair** (:488–499, fork commit c8799f4): `if (m < 2) { score = 0.0; df = 0; return false; }` and
  the caller (:663–676) fails the battery and prints the reason. Pre-repair this returned (0, 0) →
  `igamc(0, 0) = 1` → pass: exactly the 2.3(d) shape, at the place where the text explicitly says "fails".
  Boundary arithmetic checked: at L = 1e6, 3162 ones → min_p²·⌊L/2⌋ = 4.999122 (m = 1, FAIL);
  3163 → 5.002285 (m = 2, applied). A tie exactly at 5 would need c² = 10^7 — no integer; the
  `>=` boundary is therefore never exercised by rounding at L = 1e6.
  Note the repair returns from `chi_square_tests` *before* the GOF test (:675), so on an m = 1 input the
  GOF statistic is neither computed nor printed. Fail-closed; cosmetic only.
- Blocks (:505–516): `block_count = sample_size / m` = ⌊L/m⌋, remainder discarded; tuple index built
  MSB-first (`symbol = (symbol << 1) | data[i*m+j]`) — any bijection is fine since all 2^m tuples are
  enumerated. `i*m + j < L ≤ INT_MAX`. `occ` is `vector<int>(1 << m)`, m ≤ 11.
- Expectation and T (:518–526): `e = pow(p1, w) * pow(p0, m - w) * block_count` with `w = __builtin_popcount(i)`
  — the text's step 3c. The smallest e is the all-minority tuple, `min_p^m ⌊L/m⌋ ≥ 5` by construction,
  so **e ≥ 5 > 0 for every tuple: no division by a small or zero count** (this is what the m rule buys).
- `df = pow(2, m) - 2` (:529): exact in double for m ≤ 11, converted to int. Text: 2^m − 2. ✓
- Input assumption: `data[i] ∈ {0,1}`. Holds for every caller: translated two-symbol alphabets
  (`-i`, including a two-valued file declared at a wider width — the F01/PR #256 decision, documented
  in NOTICE), and `-c` bits. `ea_restart -i` passes translated rows/columns.

### 2.6 §5.2.4 `binary_goodness_of_fit` (:572–606)

- `sublength = sample_size / 10` (:575); `p = divide(ones, sample_size)` over the *entire* S (:582) —
  the text's step 1 (p over S including the discarded remainder). `e0 = (1-p)·sublength`,
  `e1 = p·sublength` (:586–587) — step 4 exactly, including the floor. Ten subsets `data[i*sublength + j]`
  (:589–599), `o0 = sublength − o1`, T as step 5b (:601). `df = 9` (:605).
- Critical value: the code tests `igamc(4.5, T/2) < 0.001`, i.e. T > 27.87716, where the text prints
  27.887. Code is **stricter by 0.01 in T** (fails where the printed constant would pass for
  T ∈ (27.877, 27.887]) — conservative; D-class, and the standard's constant is the one in error.
- e0, e1 > 0 whenever 0 < p < 1 and L ≥ 10; both hold for any admitted input (alph_size ≥ 2 and
  L ≥ 1e6, or the test escape at L ≥ 100 in practice).

### 2.7 `chi_square_tests` (:647–728) — assembly

Independence (binary or not) → p → `result = false` if p < 0.001 (:693–695); then GOF → same (:723–725);
returns the conjunction. Both tests always run (except the m = 1 early return). Verbose levels 2 and 3
print T, df, p. Nothing here is width-dependent beyond the `alphabet_size == 2` dispatch (:657, :702).

### 2.8 §5.2.5 `len_LRS_test` (:643–771)

- Step 1: `calc_proportions(data, p, L)` (`utils.h:967–977`) does `p[data[i]]++` into `vector<double> p(k)`;
  in bounds because every caller passes translated data with `k = alph_size` (iid_main :480/:505 via
  `testdata`; restart :1118–1119 with `data.alph_size`; `-c` passes bits with k = 2).
- Step 2: `p_col = Σ powl((long double) p[i], 2.0L)` (:628–635). **R-1 clamp** (:674–677):
  `if(p_col < 1.0L/k) p_col = 1.0L/k`. By Cauchy–Schwarz the exact Σp_i² ≥ 1/k with equality only at
  uniform, so the clamp moves a rounded-low value *up to at most the exact value*. A larger p_col makes
  Pr(X ≥ 1) larger (pass likelier), so relative to the *rounded* value it is permissive by ≤ ~1e-17
  relative (×W ≈ 1e-15 in the log statistic — no integer-count input sits that close to the boundary),
  and relative to the *exact* value it is conservative or equal. The only way it could overstate is
  `k` smaller than the number of distinct values present — excluded by the translation above.
  Documented in FORK-DIVERGENCE A.1 (R-1). I could not break it.
- `p_col > 1 − LDBL_EPSILON` → PASS with `Pr(X ≥ 1) = 1.0` (:682–690): text gives Pr = 1 exactly. ✓
  Unreachable anyway (alph_size = 1 is refused at `iid_main.cpp:329`).
- Step 3: `W = len_LRS32(data, L)` (:694–699; `len_LRS64` only if L ≥ INT32_MAX, which the INT_MAX
  refusal makes unreachable for `ea_iid`). `len_LRS32` (:595–607): `sa(L+1)`, `lcp(L+1)`,
  `calcSALCP32` (divsufsort + Kasai; validated against brute force by the t-tuple/LRS analysis,
  `logs/analysis/ttuple-lrs.md §2.1`), `W = max lcp[0..L]` with `lcp[0] = −1`, `lcp[1] = 0` → W ≥ 0.
  The LCP of adjacent sorted suffixes is the longest repeated substring, overlapping repeats included
  (text: "for at least one i ≠ j"). `L < SAINDEX_MAX` → `L + 1 ≤ INT_MAX`, no signed overflow in the
  vector sizes or the `j <= sample_size` loop.
- Step 4: `N = n_choose_2((int64_t) L − (int64_t) W + 1)` (:713), `utils.h:1027–1030` computes `(n*n − n)/2`
  in `int64_t` with `assert(0 ≤ n ≤ INT_MAX)` (**C18** repair, OC-53). W ≤ L − 1 → n ≥ 2 → N ≥ 1 > 0.
- Step 5, decision (:704, :768–770):
  ```
  const long double logCollisionPower = ((long double)W) * logl(p_col);
  const long double logDecisionThreshold = logl(-expm1l(logl(0.999L) / ((long double)N)));
  return logCollisionPower >= logDecisionThreshold;
  ```
  Derivation, each step monotone: Pr ≥ 0.001 ⇔ (1−p^W)^N ≤ 0.999 ⇔ log(1−p^W) ≤ log(0.999)/N
  ⇔ p^W ≥ 1 − exp(log 0.999/N) = −expm1(log 0.999/N) ⇔ W·log p ≥ log(−expm1(log 0.999/N)).
  Inclusive `>=` = the text's "fails if … less than 0.001". `expm1l` preserves the ~2e-15 difference
  from 1 at N ≈ 5e11 that `1 − expl(…)` would destroy; **#153** repair (a3dde6f) replaced the
  pre-repair `powl(p_col, W)` + `assert(≥ LDBL_MIN)` abort. W = 0 → `0·logl(p_col) = 0 ≥ negative` → PASS
  (text: p^0 = 1 → Pr = 1). The verbose `Pr(X ≥ 1)` (:738–755) is display only; the decision never
  reads it, and its underflow branch prints 0 rather than aborting.
  Width check at L = 1e6, p_col = 0.5 (1-bit): threshold = ln(1.0005e-3 / 4.9996e11) = −33.845;
  −0.6931·W ≥ −33.845 ⇔ W ≤ 48.83 → W = 48 PASS, W = 49 FAIL. Matches the first-order form
  N·2^−W < 0.001 that `regression-iid-failclosed.sh:102–108` uses as its independent oracle.
- Platform: on this host `long double` is binary64; `logl/expm1l` are then the double routines. The
  decision compares two finite negative numbers of magnitude ~30–35 with ~1e-14 absolute error; a flip
  needs an input within that of the boundary, impossible with integer counts except by construction
  at a measure-zero tie. The `Pr` print differs between 53-bit and 80-bit `long double` in its trailing
  digits (regression-platform-deltas territory), the decision does not.

### 2.9 What the final `min()` sees from this component

Nothing numeric. The component yields three booleans; a `false` removes the IID path (no `hAssessed`,
exit 1). Its only influence on a reported figure is the binary one described in 1.0: a wrongful
`true` lets MCV stand alone. There is no NaN-drops-the-minimum hazard here; the NaN-reads-as-pass
hazard (2.2) is unreachable from any input I could construct.

---

## 3. Prior repairs touching this component, and how I tried to break each

| repair | where | break attempts (analysis; execution-phase items marked) | result |
|---|---|---|---|
| **N-01** m = 1 fails (c8799f4; `regression-chisquare.sh`) | `chi_square_tests.h:488–499, 663–676` | (a) bypass via a non-binary alphabet: the m rule exists only for k = 2, and a two-valued file at any declared width is translated to k = 2 (F01 decision) — no bypass; (b) `-c` path: 8-bit bytes mostly 0x00 with rare 0x01/0x02/0x03 → `-i` sees k = 4 (no m rule) while `-c` sees 8e6 bits with ~1,300 ones → m = 1 → must FAIL under `-c` (edge case 3; EXECUTION); (c) `-q`/JSON: the `return false` is unconditional on verbosity (:675), only the message is gated — fine; (d) boundary 3162/3163 ones at L = 1e6 (EXECUTION, 1e6 samples); (e) `ea_restart -i` rows/cols: same function, AND of both (:1093–1095) — no bypass; (f) mutate `return false` → `return true` out of tree and confirm the regression catches it (rule 7; EXECUTION). | not broken on analysis |
| **#153** log-domain LRS decision (a3dde6f, `regression-iid-failclosed.sh`) | `lrs_test.h:704, 738–755, 768–770` | (a) p_col^W just above/below LDBL_MIN on binary64 (1-bit, W ≈ 1,022): both branches of the print must agree with the decision, which does not depend on the branch (EXECUTION); (b) W = L − 1 (a two-period string "0101…") → N = 1, threshold = ln(0.001): pass iff p_col^W ≥ 1e-3 — a 1-bit alternating string has p_col = 0.5, W = L − 2 → FAIL, correct; (c) W = 0 → PASS (shown above); (d) N overflow: int64, n ≤ INT_MAX asserted. | not broken |
| **R-1** clamp (0adef7a) | `lrs_test.h:674–677` | (a) exact balance k = 3 at L = 999,999 must not abort on arm64 and x86 (EXECUTION; the CI measured 117/255 and 155/255 sizes pre-repair); (b) a FAIL→PASS flip needs the exact-vs-rounded difference (~1e-17) to straddle the threshold — not constructible with integer counts; (c) `k` < distinct count — no caller. | not broken; conservative w.r.t. exact |
| **C18** int64 `n_choose_2` (473cd5f) | `lrs_test.h:713`, `utils.h:1027–1030` | LP64 host: bit-identical by construction; LLP64 measured by CI (OC-48/53). Only a Windows job can re-test. | not testable here |
| **#271** `-c` runs §5 on the bitstring (134d377, `regression-271.sh`) | `iid_main.cpp:378–386, 412–414` | (a) `-c` at width 1: `bsymbols` aliases `symbols` — identical view, fine; (b) `-c -t`: both h′ and the tests see the truncated `blen` (:343 precedes :378) — consistent; (c) `-c` with inferred width (no width argument) changes the bitstring (F02, documented) — expected, not a break. | not broken |
| **INT_MAX refusal** for the `int` test paths | `iid_main.cpp:393–408` | needs > 268,435,455 8-bit samples under `-c` (a 268 MB file; heavy) — NOT RUN. Source argument: every `int` expression in 2.3–2.6 is bounded by `sample_size`. | not measured |

---

## 4. Edge-case inputs that separate a correct implementation from an incorrect one

Severity ordering: items where a wrong implementation reports HIGHER entropy first.

1. **N-01 boundary at compliant size (overstates if wrong).** L = 1,000,000 bits; A: 3,162 ones,
   B: 3,163 ones (seeded positions). Correct: A → `m = 1, test fails` → `IID test suite failed`,
   figure from `ea_non_iid` (tracker: 0.003068); B → `df = 2`, applied. Wrong (upstream shape):
   A passes chi-square and, if LRS + permutations pass, awards MCV ≈ 0.0043 (1.4× the non-IID figure).
2. **`-c` bias through the bitstring (overstates if wrong).** L = 1,000,000 bytes: 999,000 × 0x00 and
   ~333 each of 0x01, 0x02, 0x03. `-i`: k = 4, non-binary tests. `-c`: 8,000,000 bits with ~1,333 ones,
   min_p²·4e6 ≈ 0.7 < 5 → m = 1 → chi-square must FAIL. An implementation that runs the §5 tests on
   the packed symbols under `-c` (pre-#271) or lacks the m rule would accept.
3. **LRS test exactly at the W threshold (overstates if `>` or mis-formed N).** L = 1,000,000 random
   bits (seed fixed), verify natural W < 48 with an independent suffix-array/brute oracle, then copy a
   48-bit window to a far position (variant A) or a 49-bit window (variant B), re-verify W. Correct:
   A PASS, B FAIL (threshold W ≤ 48.83 at p_col ≈ 0.5, N = C(L−W+1, 2); the exact threshold is
   `ln(−expm1(ln 0.999/N))`). An implementation using C(L, 2), L−W, or `>` flips exactly one of the pair.
4. **Negative df "not applied" (neutral verdict; reporting deviation — the confirmed LOW).**
   L = 1,000,000, k = 3, counts 999,992/4/4 at seeded positions. Correct per text: independence test
   not applied (nbin = 2, df = −1) and the report should say so. This tool: `df = -1`, `P-value = 1`,
   `Passed` (measured at L = 2,000: `analysis-iid-chisq-dfneg.out:14–20`). A reference that treats
   df < 1 as FAIL would under-report; one that treats it as PASS matches the tool's verdict; the
   differential driver must special-case it.
5. **Exact balance k = 3 at L = 999,999 (R-1).** 333,333 of each of three byte values, seeded order.
   Must complete (no abort) on arm64 and x86-64 and give the same LRS verdict as the one-sample-moved
   neighbour (333,334/333,333/333,332).
6. **Tied expectations (spec ambiguity; pins the reference's tie order).** Uniform 4-symbol data
   L = 1,000,000 → all 16 e_{i,j} = 31,250 → nbin = 16, df = 12; GOF: 4 equal e_i → nbin = 4, df = 27.
   T is unaffected here (every pair is its own bin) — the tie-sensitive case is k = 3 with two pairs
   below 5 and equal: counts chosen so e_{(1,3)} = e_{(3,1)} < 5 with the rest ≥ 5, where the two tied
   pairs merge into one bin regardless of order (T unaffected) — so the order only matters when three
   or more tied small pairs straddle a bin boundary: e.g. k = 4 with three rare symbols of equal
   count c (so 6 rare-rare off-diagonal pairs tie) and c chosen so cumulative sums cross 5 mid-tie.
   Construct: L = 1,000,000, counts 997,000 / 1,000 / 1,000 / 1,000 → rare-rare e = 0.5 each (9 pairs,
   6 tied off-diagonal + 3 tied diagonal) → bins close every 10 rare pairs; the 10th and 11th tied
   pairs land in different bins and T depends on which tuples those are. Reference must sort ties by
   i·k + j ascending to match.
7. **L odd and L ≢ 0 (mod 10) at compliant size (literal-text parity).** L = 1,000,001 and 1,000,005,
   random 8-bit. Compare T against a literal-text reference (L/2, c_i/10): expect relative deltas
   ≤ 1e-6 and ≤ 9e-6 with no verdict change; a verdict flip would need p within that of 0.001.
8. **GOF single bin (degenerate, must not crash).** L = 1,000,000: 999,960 × 0x00 plus 40 distinct
   other byte values once each → e_i = 0.1 ×40 → all 41 symbols in one bin → `df = 0, T = 0, P = 1`.
9. **Binary GOF constant check.** A 1-bit input engineered so T ∈ (27.877, 27.887): the tool FAILS
   (exact quantile), a literal-text implementation with 27.887 PASSES. Construction: 10 subsets of
   100,000 bits with ones-counts chosen so Σ(o1−e1)²/(e1) + Σ(o0−e0)²/e0 ≈ 27.882 given p = overall
   proportion; solve for counts offline. Demonstrates the D-class item; conservative direction.

---

## 5. What this analysis does not establish

- No compliant-size (≥ 1e6) run was made; every measurement is at 100–2,000 samples under the test
  escape. The df < 1 reachability bound at L = 1e6 is DERIVED, not measured (edge case 4 measures it).
- The suffix-array correctness of `W` is taken from the t-tuple/LRS analysis's brute-force comparison
  (`ttuple-lrs.md §2.1`), which exercised `ea_non_iid`; `len_LRS32` shares `calcSALCP32` but was not
  separately brute-force-checked here beyond the three probes' W values being plausible (21 of 100 for
  Example 11's data — the standard's own example sequence fails §5.2.5; 34 of 1,000; 9 of 160; 815 of
  2,000 for the 99.6 %-skewed input).
- Cephes `igamc` accuracy for a ≈ 16,000 (k = 256 independence df ≈ 32,000) was reasoned, not measured;
  the differential against `reference/py90b` should include a k = 256 case.
- Windows/LLP64 and 80-bit `long double` behaviour is CI-only (C18, R-1); nothing here re-measures it.
- The `-c` path at > 268M samples (the INT_MAX refusal) was not run.
