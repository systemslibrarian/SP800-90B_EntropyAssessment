# Compression estimate (SP 800-90B §6.3.4) — analysis-phase record

Date 2026-11-07. Branch `audit/2026-11-07`. Component: `cpp/non_iid/compression_test.h`
(267 lines, read in full) and the helpers it uses from `cpp/shared/utils.h`
(`INOPENINTERVAL`/`INCLOSEDINTERVAL` :39-40, `RELEPSILON`/`ABSEPSILON`/`DBL_INFINITY`/
`ITERMAX`/`ZALPHA` :70-76, `relEpsilonEqual` :115-196), plus the call sites
`cpp/non_iid_main.cpp:434-460` and `cpp/restart_main.cpp:930-946`.

Everything measured below ran against `cpp/ea_non_iid` sha256
`1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` on Darwin arm64
(Apple clang 21), with `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`, so **every run here is
non-compliant by construction** (brief ground rule 5). Raw logs:
`logs/analysis-compression-gcheck.log`, `logs/analysis-compression-ref.json`,
`logs/analysis-compression-run-<case>.out`, `logs/analysis-compression-run-rc.log`,
`logs/analysis-compression-diff.log`, `logs/analysis-compression-quantisation.log`.

**Headline.** No deviation from §6.3.4 in the overstating direction was found. The `G(z)`
loop is algebraically the spec's printed double sum (verified symbolically below and
numerically to 2.6e-14 relative over 65 (d, N, z) cases, including the standard's own
worked example: p = 0.571484 against NIST's 0.5715, H = 0.134536 against 0.1345); the
confidence bound, the search direction and every search-failure exit go the conservative
way except the two spec-mandated "no solution → 1" paths; X̄, σ̂, X̄′ are bit-identical to
an independent transliteration of the spec on every tiny input tried. What remains are
LOW items: an un-carried bisection quantisation that reaches ~1e-7 bit only at the cap, a
dead-on-arm64 truncation branch, a reporting asymmetry in `ea_restart`, and a Windows
`long` question nobody has measured for this file.

A probe fault worth recording (memory: "my own probes answer the wrong question"): the
first eight runs were refused with "Error reading file." because this shell is zsh and
`set -- $spec` does not word-split, so the tool received a path ending in " 1". The
misnamed logs were deleted and the runs redone from an explicit bash script. The refusal
was the probe's, not the tool's.

---

## 1. The spec, step by step (quoted)

§6.3.4 (PDF p. 53): *"This entropy estimation method is only applied to binary inputs.
Given the input S = (s1, …, sL), where si ∈ A = {0,1},"* — and §6.2 (PDF p. 49): *"The
Collision, Markov and Compression estimates are only applied to binary inputs."*

| step | text (PDF page) | constants / rounding / direction |
|---|---|---|
| 1 | *"Let b = 6. Create a new sequence S′ = (s′1, …, s′⌊L/b⌋) by dividing S into non-overlapping b-bit blocks. If L is not a multiple of b, discard the extra data."* (p. 53) | b = 6; floor; tail discarded |
| 2a | *"Create the dictionary from the first d = 1000 elements of S′"* (p. 54) | d = 1000 |
| 2b | *"Use the remaining v = ⌊L/b⌋ − d observations, (s′d+1, …, s′⌊L/b⌋), for testing."* (p. 54) | v = N − d, N = ⌊L/b⌋ |
| 3 | *"Initialize the dictionary dict to an all zero array of size 2^b. For i from 1 to d, let dict[s′i] = i. The value of dict[s′i] is the index of the last occurrence of each s′i in the dictionary."* (p. 54) | 1-based indices; 0 = never seen |
| 4 | *"For i from d+1 to ⌊L/b⌋: i. If dict[s′i] is non-zero, then Di−d = i − dict[s′i]. Update the dictionary … dict[s′i] = i. ii. If dict[si] is zero, add that value to the dictionary, i.e., dict[s′i] = i. Let Di−d = i."* (p. 54) | D ≥ 1 always |
| 5 | *"Calculate the sample mean X̄ and sample standard deviation σ̂ of (log2(D1), …, log2(Dv))"*: X̄ = Σ log2 Di / v; *"c = 0.5907"*; σ̂ = c · sqrt( Σ(log2 Di)² / (v−1) − X̄² ) (p. 54, footnote 13: *"a correction factor is applied to the standard deviation … This correction factor reduces the standard deviation"*) | divisor v−1 → needs v ≥ 2; c < 1 raises X̄′ |
| 6 | *"Compute the lower-bound of the confidence interval for the mean, based on a normal distribution using X̄′ = X̄ − 2.576 σ̂ / √v."* (p. 54) | LOWER bound; 2.576 printed |
| 7 | *"Using a binary search, solve for the parameter p, such that … X̄′ = G(p) + (2^b − 1) G(q), where G(z) = (1/v) Σ_{t=d+1}^{L} Σ_{u=1}^{t} log2(u) F(z,t,u), F(z,t,u) = z²(1−z)^{u−1} if u < t; z(1−z)^{t−1} if u = t, and q = (1−p)/(2^b − 1). The bounds of the binary search should be 2^−b and 1."* (pp. 54-55) | outer limit printed as **L** (see §1.1) |
| 8 | *"If the binary search yields a solution, then the min-entropy is … −log2(p)/b. If the search does not yield a solution, then the min-entropy estimation is: min-entropy = 1."* (p. 55) | no-solution → **1** (permissive by design) |

Worked example (p. 55): *"d = 4 (instead of 1000), L = 48 … v = 4 … D1 = 5, D2 = 6, D3 = 7,
and D4 = 7 … X̄ = 2.6304 and σ̂ = 0.9074, and the value for step 6 is X̄′ = 1.4617. The value
of p that solves the equation in step 7 is 0.5715, and the min-entropy estimate is 0.1345."*

Bitstring length for the 8-bit path, §3.1.3 (PDF p. 20): *"the sequential dataset that
contains L samples (each having n bits) is considered as a bitstring of size nL. The bits
after the first 1 000 000 bits may be ignored."*

### 1.1 The outer-sum limit is printed as L but means ⌊L/b⌋

The printed `Σ_{t=d+1}^{L}` cannot be literal: D is defined only for t = d+1..⌊L/b⌋ and the
1/v normalisation makes G an expectation over exactly v positions. The worked example
settles it: with the outer sum to N = 8 the solve gives p = 0.571484 (NIST 0.5715); with
the sum to L = 48 it gives p = 0.720406, H = 0.0789 (`analysis-compression-gcheck.log`).
The code, the fork's oracle (`compression_ceiling_exact.py:21`) and every known
implementation use N. **Spec typo, not a code defect; direction if taken literally:
understates.**

### 1.2 Algebra: the C++ `G` equals the printed double sum

Write a_i = log2(i)(1−z)^{i−1} (a_1 = 0) and A_k = Σ_{i=1}^{k−1} a_i. Then

    G(z) = (1/v) [ z² Σ_{t=d+1}^{N} A_t  +  z Σ_{t=d+1}^{N} a_t ]
         = (1/v) [ z² ( (N−d) A_{d+1} + Σ_{i=d+1}^{N−1} (N−i) a_i )  +  z ( A_{N+1} − A_{d+1} ) ]

(the first bracket by counting, for each u = i, the number of t in [d+1, N] with t > i:
N−d when i ≤ d, N−i when d < i ≤ N−1). `compression_test.h:17-84` computes exactly these
three pieces — `Ad1` = A_{d+1} (lines 39-48), `firstSum` = Σ (N−i) a_i + (N−d) A_{d+1}
(lines 52-75), `Ai` = A_{N+1} (lines 57, 78-81) — and returns
`1/(double)v * z*(z*firstSum + (Ai - Ad1))` (line 83). The u index runs over i with
B_i = (1−z)^{i−1} seeded as `Bi = Bterm` = B_2 at line 36 and advanced after each use
(lines 44, 70), so the exponent is u−1 as printed; the u = t term carries the single
factor z (the `z*(…)` outside) and the u < t terms carry z² (the `z*firstSum` inside).

Numerically (`analysis-compression-gcheck.log`): three evaluations — the printed double sum
(`G_brute`), the reordering above (`G_reord`), and a line-by-line double-arithmetic
transliteration of the C++ loop (`G_cpp`) — agree to a worst relative difference of
**2.58e-14** over d ∈ {4, 1000}, N ∈ {8, 1002, 1003, 1010, 1250}, and 13 values of z from
1e-9 to 0.999, and all three give p = 0.571484, H = 0.134536 for the worked example.

---

## 2. Step → code map, with the disagreements and non-disagreements spelled out

| spec | code (`compression_test.h`) | verdict |
|---|---|---|
| step 1, b = 6, N = ⌊L/b⌋, tail discarded | `:94 b = 6`; `:115 num_blocks = len/b` (integer division); block i reads `data[i*b + j]`, j < 6, so the last index is `num_blocks*b − 1 ≤ len − 1` (`:137`, `:145`) | matches; in bounds |
| step 2a/2b, d = 1000, v = N − d | `:114 d = 1000`; `:142 v = num_blocks - d` | matches |
| step 3, dict zeroed, 1-based index | `:134 dict[i] = 0`; `:135-139 … dict[block] = i+1` for i = 0..d−1 | matches (1-based) |
| step 4, D = i − dict or D = i | `:146 log2(i+1-dict[block])` with 0-based i, so the 1-based index is i+1; unseen → dict = 0 → D = i+1 = the index (4.b.ii); seen → D = (i+1) − dict (4.b.i); then `:148 dict[block] = i+1` | matches; D ≥ 1 so **no log of zero** |
| step 5, X̄, Σ(log2 D)², divisor v−1, c = 0.5907 | `:146-147` Kahan sums; `:152 X /= v`; `:153 sigma = 0.5907 * sqrt(sigma/(v-1.0) - X*X)` | matches; NaN impossible for v ≥ 2 (§2.2) |
| step 6, X̄′ = X̄ − 2.576 σ̂/√v (lower) | `:164 X -= ZALPHA * sigma/sqrt(v)` with `utils.h:75 ZALPHA 2.5758293035489008` | direction correct (lower bound); constant is the **documented divergence D-1 / C22c** |
| step 7, search p on [2^−b, 1] | `:168 if(com_exp(1.0/alph_size, …) > X)` else `p = -1`; `:169-170 ldomain = 1/64, hdomain = 1`; `:185 for(j<ITERMAX=1076)`; `:187` stop when `relEpsilonEqual(pVal, X, DBL_MIN, DBL_EPSILON, 4)`; `:190-196` `X < pVal → lbound = p` else `hbound = p` | com_exp is decreasing in p, so X < pVal means p too small → raise lbound: **correct direction** |
| step 7, G and q | `:86-89 com_exp`: `q = (1-p)/(alph_size-1)`, `G(p) + (alph_size-1)*G(q)` with `alph_size = 1<<6 = 64` (`:96`) | matches |
| step 8, −log2(p)/b, else 1 | `:250-258`: `p > 1/64 → entEst = -log2(p)/b`; else `p = 1/64, entEst = 1.0` | matches |
| §3.1.3 bitstring truncation | `non_iid_main.cpp:344 if (!all_bits && data.blen > MIN_SIZE) data.blen = MIN_SIZE` | spec-sanctioned ("may be ignored"); `-a` uses all bits |
| §6.2 binary only | `non_iid_main.cpp:437` bitstring path when `alph_size > 2 || !initial_entropy`; `:448` literal path when `initial_entropy && alph_size == 2`; `restart_main.cpp:884 if (data.alph_size == 2)` | matches; symbols are translated to 0..k−1 first (`utils.h:542-543`), so the `& 0x1` at `:137/:145` is sound |

### 2.1 The search exits, one by one, with direction

- `:187` equality within 4 ULP → p is the midpoint whose com_exp is within 4 ULP(X̄′) of
  the target. Either side of the true root (see §2.4).
- `:200-203 lbound >= hbound → p = fmin(fmax(lbound,hbound), hdomain)`: takes the larger p
  → **lower** entropy. Unreachable (midpoints are strictly interior).
- `:206-210` bounds leave the domain → `p = ldomain` → entEst = 1.0. **Permissive**, but
  unreachable: lbound/hbound are only ever set to interior midpoints.
- `:213-217 !INCLOSEDINTERVAL(X, lvalue, hvalue) → p = ldomain` → 1.0. **Permissive.**
  Reachable only if X̄′ or a pVal is NaN (an ordinary X̄′ always lies between
  com_exp(lbound) and com_exp(hbound) by construction of :190-196; the initial ±inf
  sentinels make the first check true). NaN is excluded in §2.2, so this is a dormant
  fail-open branch, not a live one.
- `:224-227` midpoint not strictly inside → `p = hbound`; `:232-235` cycle → `p = hbound`;
  `:241-244` non-monotone pVal → `p = hbound`. All take the **larger p → lower entropy**.
- `:168` `com_exp(1/64) > X` false (X̄′ at/above the uniform expectation, or NaN) → `p = -1`
  → 1.0. This is step 8 as written; tracker row **F06 NOT-A-BUG** ("spec-literal
  behaviour … weakness of the standard"). Measured live on two inputs below (g, h).

### 2.2 NaN / inf / log(0) / division by small counts

- `log2(i+1-dict[block])`: argument ≥ 1 (dict ≤ i), so ≥ 0, finite. int64_t → double exact
  below 2^53.
- σ̂ radicand: Σx²/(v−1) − X̄² = (v·Var + X̄²)/(v−1) ≥ X̄²/(v−1), i.e. a relative margin of
  1/(v−1) over the subtracted X̄², which is ≥ 7e-7 at v ≤ 1.4e6 — eleven orders above the
  Kahan-summed rounding. So the radicand is ≥ 0 for every v ≥ 2 and is exactly +0.0 when
  all D = 1. **The #263 guard (`:128-131`, v ≥ 2) is sufficient to exclude NaN and inf, not
  merely to avoid 0/0.** At v = 1 the divisor v−1.0 = 0 → 0/0 (NaN) or x/0 (inf), the F11
  mechanism; now unreachable.
- G has no NaN source for z ∈ (0, 1): `Bterm = 1−z` ∈ (0,1), `log2l(i)` finite, all products
  finite, `1/(double)v` finite. The search never evaluates z = 0 or z = 1 (midpoints only).
- `relEpsilonEqual` returns false for NaN (`utils.h:128`), so a NaN pVal would fall to the
  `:213` exit and award 1.0 — the dormant branch above.

### 2.3 Integer widths and sizes

- `long len, i, num_blocks, v` and `int d, j, b`. On LP64 (this host, Linux) `long` is 64-bit:
  `i*b + j` cannot overflow below 1.5e18 bits. The F14 repair (`:104 int64_t dict[alph_size]`,
  `:108 static_assert(sizeof(dict[0]) >= 8)`) keeps the 1-based block index intact above
  2^32 blocks; `i+1-dict[block]` is int64_t arithmetic.
- `G(double z, int d, long num_blocks)` loops `for(long i=d+1; i<=num_blocks-1; i++)` and
  scales by `(long double)(num_blocks-i)`; `assert(d>0); assert(num_blocks>d)` (`:29-30`)
  cannot fire because `:128` requires num_blocks ≥ d+2 first (asserts are live: the build
  line in `BUILD-LINES.md` carries no `-DNDEBUG`).
- On LLP64 (Windows) `long` is 32-bit, but `data_t.len/blen` are `long` too, so the first
  overflow is the intake's, not this file's (8-bit samples × ≥ 268,435,456 → blen > 2^31).
  Not reachable from the 1,000,000-sample target profile (blen = 8e6). **Unmeasured here;
  FORK-DIVERGENCE A.1/C18 already records that "a sweep of the remaining long arithmetic on
  LLP64 has not been done."**
- Minimum legal count: `:128 num_blocks < d + 2` → declines with `return -1.0`; callers test
  `>= 0` (`non_iid_main.cpp:439`, `:450`; `restart_main.cpp:937`, `:944`).

### 2.4 The termination tolerance is an un-carried quantisation (LOW, either direction)

`:187` accepts any midpoint with |com_exp(p) − X̄′| ≤ 4 ULP(X̄′) (relEpsilonEqual with
maxRelFactor = DBL_EPSILON also accepts a relative difference ≤ 2.2e-16, i.e. ~1 ULP). A
p with com_exp(p) = X̄′ + 3 ULP is *below* the true root (com_exp decreasing) and gives a
*higher* H. Measured (`analysis-compression-diff.log`):

| case | ULP residual of the tool's p | H(tool) − H(reference root) |
|---|---|---|
| a (1-bit, N = 2002, H ≈ 0.61) | +3.00 ULP | **+1.68e-14 bit** (tool higher) |
| d (8-bit, N = 2666, H ≈ 0.68) | −2.00 ULP | −2.48e-14 bit (tool lower) |

Derived at N = 166,666 (`analysis-compression-quantisation.log`, pure Python using the
transliterated G): because com_exp is stationary at p = 2^−b (the C22c argmax argument in
`compression_ceiling_exact.py:173-187`), dH/dX̄′ diverges at the cap, and an X̄′ of
cap − 4 ULP solves to **H = 0.99999990, i.e. 9.8e-8 bit below 1**. That is the largest H
quantisation the tolerance can produce; at H₀ ∈ {0.95, 0.85, 0.70, 0.61} the shift is at or
below the probe solver's own ~1e-13 resolution (the figures printed there are bounded by
that resolution, not clean derivatives). The entropy floor carries `C22a` for P_local's
bisection only (`entropy_floor.py:107`, `:541`); nothing carries this one. At the device's
operating point (H ≈ 0.85) it is below 1e-12 bit, so this is a bookkeeping gap, not a risk.
The tolerance and the 4-ULP choice are upstream (commit `9408ab8`), not the fork's.

### 2.5 The `underflowTruncate` branch is dead on this host at z ≈ 1/64 (neutral)

`:61-67` break when `(double)((N−i)·a_i)` is not > 0. On Apple arm64 `long double` is
binary64, and B_i = (63/64)^{i−1} does not reach zero: once B_i is the smallest denormal
2^−1074, `2^−1074 × 0.984375` rounds back to 2^−1074, so `Bi` sticks there and the loop runs
all N−1−d iterations adding terms of ~1e-318 (the probe confirms: no break at N = 166,666 or
1,333,333). On x86-64 the 80-bit `Bi` keeps shrinking and the `(double)` cast reaches 0 at
i ≈ 48,000, so the branch fires. The skipped/kept terms are < 1e-300 against a `firstSum`
of ~5e7, so G agrees across the two paths to ~1e-16 — consistent with the recorded
platform class (ringOsc `0.15932269772157773` macOS vs `…898` Linux, 7.8e-15 relative,
`regression-estimator-guards.sh:271-276`). Cost only; no direction. Not a defect.

### 2.6 Degenerate-but-legal inputs: what the final min() sees

- v = 1 (1001 blocks): declines, `bitstring_not_run`/`literal_not_run` set in
  `non_iid_main.cpp:443/:454`; the assessed figure comes from the other estimators
  (measured, case c: 0.6898 from the rest).
- v = 2 (1002 blocks): **always −0** when X̄ > 0. Proof: with two values,
  Σx²/(v−1) − X̄² = x1² + x2² − (x1+x2)²/4 ≥ X̄², so σ̂ ≥ 0.5907·X̄ and
  ZALPHA·0.5907/√2 = 1.0759 > 1, hence X̄′ ≤ X̄(1 − 1.0759) < 0 → every com_exp(p) > X̄′ →
  lbound → 1 → `p = hbound = 1` → `-log2(1)/6 = -0`. Measured on b and e. Direction:
  conservative (the min() sees 0). The #263 regression's "still runs at v=2" is true in the
  sense of "produces a finite σ̂"; the figure it produces is −0.
- All blocks identical: X̄ = σ̂ = X̄′ = 0 → p → 1 → −0. (The all-zero *file* never reaches the
  estimator: `alph_size == 1` → "No entropy awarded", rc 255; measured, case f.)
- `ea_restart`: `rdata`/`cdata` are the whole 1,000,000-sample matrix in row/column order
  (`restart_main.cpp:714`, `:782`, calls with `data.len`), so N = 166,666 and the estimator
  runs; a decline there (`:937`, `:944`) sets **no** not-run marker, unlike `non_iid_main`.
  Unreachable at the mandated size; reporting asymmetry only.

### 2.7 Measured against an independent transliteration of the spec

`comp_ref.py` implements steps 1-8 from the text (blocks MSB-first; dictionary 1-based;
D as in step 4; `math.fsum`; divisor v−1; c = 0.5907; Z = ZALPHA for comparison with the
tool and Z = 2.576 for information; G by the §1.2 reordering; bisection returning the
conservative end of the final bracket). `analysis-compression-diff.log`:

| case | construction | tool X̄ / σ̂ / X̄′ vs ref | tool p vs ref | tool H | note |
|---|---|---|---|---|---|
| a | 12,012 random bits (seed 20261107), N = 2002, v = 1002 | identical / identical / identical | rel −7.0e-14 | 0.6114942520414326 | Found p; `-c` (Bitstring path) bit-identical to the Literal path |
| b | 6,012 random bits, v = 2 | identical | p = 1 both | −0 | X̄′ = −0.64 |
| c | 6,006 random bits, v = 1 | — | — | declined | "need at least 1002 blocks of 6 bits" |
| d | 2,000 random bytes, Bitstring N = 2666 | identical / 1 ULP / identical | rel +1.0e-13 | 0.68452125863359969 | assessed 5.476 (8 × …) |
| e | 1000-block dictionary over 62 values, 2 novel test blocks | identical | p = 1 both | −0 | X̄ = 9.97 but v = 2 forces X̄′ < 0 |
| g | blocks cycle 0..63, N = 2002 | identical | not found both | **1** | X̄ = 6 > cap 5.2177 → step 8; LRS gives 1.9e-5 and binds |
| h | 6,000 zero bits then 6,012 random | identical | not found both | **1** | X̄′ = 5.33 > cap → step 8; MCV 0.39; t-Tuple −0 binds |

Also for information: the documented D-1/C22c divergence measured on these inputs is
**+7.63e-6 bit** (a) and **+9.59e-6 bit** (d) relative to the printed 2.576 — inside the
carried C22c ceiling (3.36e-3 at n = 1e6), and rule 8 says it is not a finding.

---

## 3. Prior repairs touching this component, and how I tried / would try to break them

| repair | what it did | break attempts |
|---|---|---|
| **#263 / F11** `c0ee84a` (`:117-131`, v ≥ 2) | declines at num_blocks < d+2 | (i) 1001 blocks → declined, no σ̂ printed (case c, measured). (ii) 1002 blocks → runs, but **always −0** (§2.6, proved and measured on b, e) — not a defect, but the regression's wording "smallest usable case" oversells it. (iii) Width: the guard counts 6-bit blocks of the *bitstring*, so an 8-bit file of 751 bytes (6008 bits, 1001 blocks) declines and 752 bytes runs — same boundary. (iv) Could NaN return at v ≥ 2? No: radicand ≥ X̄²/(v−1) (§2.2). (v) Flags: `-c`, `-a`, `-t` do not bypass it (the length arrives already truncated). |
| **F14** `6b60f9d` (`:97-108`, int64_t dict) | 64-bit block index | Reaching 2^32 blocks needs 25.8 Gbit; cannot be exercised here. The `static_assert` guards the *type*, and `regression-estimator-guards.sh:243-253` proves narrowing fails the build. LLP64: `long i` is 32-bit, `i*b` overflows at 358M blocks, but `data_t.len` (also `long`) cannot hold such a length there — the intake's overflow comes first. **Windows arithmetic for this file is unmeasured** (CI exists; brief says analysis only). |
| **C22c / D-1** `ZALPHA` (`utils.h:75`) | exact quantile, not 2.576 | Measured +7.6e-6 / +9.6e-6 bit on a / d, inside the carried ceiling. The ceiling's own derivation (`compression_ceiling_exact.py`) uses the §1.2 reordering with N = ⌊L/b⌋; my independent `G_reord` and the C++ agree with it on the worked example. To break the ceiling one would need a σ̂ above Popoviciu's bound 0.5907·log2(N)/2 — impossible since every log2 D ∈ [0, log2 N]. |
| **dfe325a** not-run reporting (`non_iid_main.cpp:443, :454`) | flags a declined estimator in the report | `regression-notrun.sh:84-96` checks only `ea_non_iid`. `restart_main.cpp:936-946` has no `else` branch, so a declined compression there would be silently absent. Unreachable at 1e6 samples; a mutation that forces `return -1.0` would show the asymmetry. |
| upstream `6950b6d` (`:168` "only search if it could work") | X̄′ ≥ cap → 1.0 without a search | Live on g and h (measured). Spec step 8; F06 NOT-A-BUG. An attacker-shaped input (de Bruijn-like block cycling) is caught by LRS/t-Tuple/MultiMMC, never by Compression. |
| upstream `f980507` (search-failure exits) | explicit exits | The two `p = ldomain` exits (`:208`, `:215`) default to full entropy and are reachable only via NaN, which §2.2 excludes. A dormant fail-open; flipping them to `p = hbound` would cost nothing and remove the class. Suggestion, not a finding. |

Interaction note (rule 12): #263 and F14 both touch `compression_test.h`; the regression
declares both. Nothing here changes either.

---

## 4. Edge-case inputs that separate a correct from an incorrect implementation

Where a wrong implementation would report HIGHER entropy is marked **(↑)**.

1. **Adjacent repeated block (D = 1).** Any random 1-bit input of ≥ 6012 bits has one
   (case a: D_min = 1). An off-by-one in step 4 (`i − dict` with 0-based i, or no `+1`) gives
   log2(0) = −inf → σ̂ NaN → step-8 fallback → **1.0 (↑)**. Correct: finite X̄ equal to the
   spec reference (measured).
2. **Divisor v vs v−1 in σ̂.** Using v gives a smaller σ̂, higher X̄′, higher H **(↑)**. Case a
   separates them at the 6th digit of σ̂ (1.0276249… with v−1). The refdata check
   (`ringOsc-nist.res` at 1e-9) would also catch it.
3. **c applied twice or to X̄′ instead of σ̂.** Twice → smaller σ̂ **(↑)**. Case a's printed σ̂
   is the discriminator.
4. **Sign of the step-6 bound.** `X += …` instead of `X -= …` raises X̄′ **(↑)**. Case a: X̄′
   must be *below* X̄ (5.1294 < 5.2130); case b: X̄′ must be negative.
5. **Search direction.** Moving `hbound` on `X < pVal` converges to the lower domain edge →
   p → 1/64 → **H → 1 (↑)** on every input. Case a's p = 0.0786 refutes it in one run.
6. **Outer-sum limit.** To N+1 or N−1: shifts of order a_N/v ≈ 1e-300 at N ≥ 1002 —
   undetectable and irrelevant; the discriminating case is the **worked example (d = 4,
   N = 8)**, where N−1 or L = 48 move p to the third digit (0.5715 only at N).
7. **Bit order inside a block.** Any fixed bijection on 6-bit values leaves D unchanged, so
   reversing the bit order within every block must give a bit-identical estimate. A good
   mutation *control* for the harness (an implementation sensitive to it has a dictionary
   bug).
8. **Cap behaviour (step 8).** Blocks cycling 0..63 (case g): X̄ = 6 exactly, σ̂ = 0.112,
   X̄′ = 5.9909 > cap 5.2177 → "Could Not Find p" → 1.0 — spec-literal; a *correct*
   implementation gives 1.0 here and the battery's LRS gives 1.9e-5. An implementation
   returning 0 or crashing is wrong in the conservative direction. (F06; documented.)
9. **Startup-stuck source (case h).** 6,000 zero bits then random: the 63 first-occurrence
   distances are ≥ 1001 and lift X̄′ above the cap → Compression 1.0 while MCV says 0.39.
   Demonstrates that this estimator alone can award full entropy to a half-dead capture;
   the min() rescues it. Documented class, useful as a battery control.
10. **Exactly 1001 vs 1002 blocks.** 6,006 bits (or 751 bytes) must decline; 6,012 bits (752
    bytes) must run and report −0. A guard at `num_blocks <= d` (upstream's) admits 1001 and
    produces NaN → 1.0 **(↑)** on data whose last block repeats the previous one — the F11
    reproducer (tracker rows 330-375).
11. **Length not a multiple of 6.** 6,017 bits: 5 tail bits discarded; a reader that rounds
    up or indexes `num_blocks*6 + j` reads past the buffer (HIGH class, not entropy). A
    sanitizer run on this length belongs to the execution phase.
12. **Near-cap data to exercise §2.4.** An input with X̄′ within a few ULP below the cap would
    show the 9.8e-8-bit quantisation ceiling; constructing one needs σ̂ ≠ 0 with X̄ − Zσ̂/√v =
    cap − ε, which is a search over block sequences — academic.
13. **8-bit `-a` vs default.** With `-a`, N = 1,333,333 and the search's q → 0 branch runs
    the second G loop to full length without truncation (~1.3e6 iterations × 2 G × ~50
    bisection steps): correctness unaffected, time only. Default `-t` gives N = 166,666 and a
    wider CI (more conservative). Both are spec-sanctioned.

---

## 5. Suspicions (none confirmed as findings)

| # | title | direction | severity | status |
|---|---|---|---|---|
| S1 | 4-ULP termination tolerance → H quantisation not carried in the floor; ≤ 9.8e-8 bit at the cap, ≤ 1e-13 at H ≤ 0.95; measured +1.68e-14 (a), −2.48e-14 (d) | either | LOW | measured at tiny N; derived at N = 166,666 |
| S2 | `restart_main.cpp:936-946` sets no not-run marker when compression declines (asymmetric with `non_iid_main.cpp:443/:454`) | neutral | LOW | source-confirmed; unreachable at 1e6 |
| S3 | `underflowTruncate` dead on arm64 at z ≈ 1/64 (denormal 2^−1074 × 63/64 rounds to itself); fires on x86-64 | neutral | LOW | derived; consistent with the recorded 7.8e-15 platform class |
| S4 | LLP64 `long` arithmetic in this file unmeasured (bounded by the intake's own `long`) | unknown | LOW | not reproduced; Windows only |
| S5 | Two `p = ldomain` search-failure exits default to full entropy; reachable only through a NaN that §2.2 excludes | overstates if ever reached | LOW | dormant |
| S6 | Decline warning `:129` prints unconditionally, including in `-q` JSON mode (siblings do the same) | neutral | LOW | source-confirmed |
| S7 | Spec text prints the outer sum to L; implementation and worked example use ⌊L/b⌋ | neutral | documentation | verified via the worked example |

Documented divergences touched, per brief rule 8: **D-1 / C22c** (ZALPHA; measured here
+7.6e-6 and +9.6e-6 bit, inside the carried ceiling) and **F06** (step-8 fallback to 1).
Neither is reported as a finding.

## 6. What this record does not establish

- Anything at compliant size (≥ 1,000,000 samples): every run here used the short-dataset
  escape; the arithmetic at N = 166,666 and 1,333,333 is argued, not run.
- Windows/LLP64 behaviour of this file (S4).
- That the C++ `G` is numerically within any stated bound of the *infinite-precision* G at
  N ≈ 1.3e6; the 2.6e-14 agreement is among three double-precision evaluations at N ≤ 1250.
- Whether S1's quantisation ever lands on the permissive side at the device's operating
  point by more than the 1e-13 the probe can resolve.
