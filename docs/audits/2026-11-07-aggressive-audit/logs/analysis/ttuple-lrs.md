# Analysis: t-Tuple estimate (§6.3.5), LRS estimate (§6.3.6), and the shared suffix-array code

Audit 2026-11-07, analysis phase. Branch `audit/2026-11-07`. Component files:
`cpp/shared/lrs_test.h` (all 771 lines read), `cpp/shared/utils.h` helpers
(`calc_proportions` :967, `n_choose_2` :1027, `ZALPHA_L` :76, `uint128_t` :80,
`read_file` symbol translation :499–546), callers `cpp/non_iid_main.cpp:460–515`,
`cpp/restart_main.cpp:955–1005, 1117–1120`, `cpp/iid_main.cpp:388–413, 504–505`,
`cpp/conditioning_main.cpp:400–412`. Library: libdivsufsort 2.0.1 from Homebrew,
`typedef int32_t saidx_t` (`/opt/homebrew/include/divsufsort.h:55`).

Spec text: `reference/sp800-90b.pages.txt`, §6.3.5 PDF p. 55–56, §6.3.6 PDF p. 56–57,
§5.2.5 PDF p. 47 (the IID LRS test also lives in this file and shares `calcSALCP32`).

Binary measured (instrument rule 4): `cpp/ea_non_iid`
sha256 `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`.
Every probe run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NON-COMPLIANT
by construction (ground rule 5). Probe script and outputs:
`logs/analysis-ttuple-lrs-probe.py`, `logs/analysis-ttuple-lrs-probe.log`,
`logs/analysis-ttuple-lrs-<case>.out`, `logs/analysis-ttuple-lrs-probe-manifest.json`,
`logs/analysis-ttuple-lrs-E-report.json`.

**Headline.** No CRITICAL or HIGH candidate found in this component. The suffix-array
tuple counting (Kaufer's algorithm over Kasai's LCP) reproduces the spec's brute-force
`Q[t]`, `u`, `v`, `Σ C(C_i,2)`, `p̂`, `p_u` and the min-entropy to relative 1e-12 on
six inputs × two views at widths 1, 2, 3 and 8, including the `Q[2] = 35` cutoff
boundary and a period-7 input with `v = 293`/`879`. The one systematic permissive
delta is the documented `D-1`/`C22c` constant (binary64 quantile vs the text's
2.576): measured `+1.0e-6 … +1.4e-5` bit on the probe inputs. Everything else found is
LOW: a `-0.0` reaching the report, a duplicated assert, an unreachable-but-unguarded NaN
path, and `pow`/`log2` spelled without the `l` suffix in two places.

---

## 1. The spec, step by step

### 1.1 §6.3.5 t-Tuple Estimate (PDF p. 55–56)

Quoted:

> "The frequency of the t-tuple (r1, r2, …, rt) in S = (s1, …, sL) is the number of
> i's such that si = r1, si+1 = r2, …, si+t-1 = rt. It should be noted that the tuples
> can overlap." (PDF p. 55)

> "1. Find the largest t such that the number of occurrences of the most common t-tuple
> in S is at least 35.
> 2. Let Q[i] store the number of occurrences of the most common i-tuple in S for
> i = 1, ..., t. […]
> 3. For i = 1 to t, let P[i] = Q[i] / (L-i+1), and compute an estimate on the maximum
> individual sample value probability as Pmax[i] = P[i]^(1/i). Let p̂max =
> max(Pmax[1], …, Pmax[t]).
> 4. Calculate an upper bound on the probability of the most common value p_u as
> p_u = min(1, p̂max + 2.576 · sqrt(p̂max(1 − p̂max)/(L − 1))),
> 5. The entropy estimate is calculated as –log2(p_u)." (PDF p. 56)

Fixed points: overlapping counts; cutoff **35, inclusive** ("at least"); positions
counted `L − i + 1`; bound direction **upper** on `p` (hence lower on entropy);
`p_u` clamped at 1; constant 2.576 as printed. Undefined when no t exists (no symbol
occurs 35 times) — the text gives no fallback.

Worked example (cutoff 3, L = 21): `Q = [9, 4, 3]`, `p̂max = 0.5405`, `p_u = 0.8276`,
`H = 0.273`.

### 1.2 §6.3.6 LRS Estimate (PDF p. 56–57)

> "1. Find the smallest u such that the number of occurrences of the most common
> u-tuple in S is less than 35.
> 2. Find the largest v such that the number of occurrences of the most common v-tuple
> in S is at least 2, and the most common (v+1)-tuple in S occurs once. In other words,
> v is the largest length that a tuple repeat occurs. If v < u, this estimate cannot be
> computed.
> 3. For W = u to v, compute the estimated W-tuple collision probability
> P_W = Σ_i C(C_i, 2) / C(L−W+1, 2), where Ci is the number of occurrences of the ith
> unique W-tuple. Compute the estimated average collision probability per string
> symbol as Pmax,W = P_W^(1/W). Let p̂ = max(Pmax,u, …, Pmax,v).
> 4. […] p_u = min(1, p̂ + 2.576 · sqrt(p̂(1 − p̂)/(L − 1))),
> 5. The entropy estimate is calculated as –log2(p_u)." (PDF p. 56–57)

Fixed points: `u` is the same quantity as `t + 1` from §6.3.5; `v` = LRS length;
decline iff `v < u`; denominator `C(L − W + 1, 2)`; max over W; same bound and clamp.

Worked example (cutoff 3): `u = 4, v = 5, P4 = 0.0131, P5 = 0.0074, Pmax,4 = 0.3381,
Pmax,5 = 0.3744, p̂ = 0.3744, p_u = 0.6531, H = 0.6146`.

### 1.3 §5.2.5 Length of the Longest Repeated Substring Test (PDF p. 47) — IID battery

> "1. Find the proportion p_i of each possible input value x_i in S […]
> 2. Calculate the collision probability as pcol = Σ_{i=1}^{k} p_i².
> 3. Find the length of the longest repeated substring W […]
> 4. The number of overlapping subsequences of length W in S is L–W+1, and the number
> of pairs of overlapping subsequences is C(L − W + 1, 2).
> 5. Let X be a binomially distributed random variable with parameters N = C(L−W+1, 2)
> and a probability of success pcol^W. Calculate […] Pr(X ≥ 1) = 1 − (1 − pcol^W)^N.
> The test fails if Pr (X ≥ 1) is less than 0.001."

Fixed points: pass iff `Pr(X ≥ 1) ≥ 0.001` (inclusive); `N = C(L−W+1, 2)`.

---

## 2. Spec → code map, with disagreements quoted

### 2.1 Suffix array and LCP (`lrs_test.h:16–112`)

- `calcSALCP32` :84–97: `sa[0] = n` (empty-suffix sentinel), `divsufsort(text, sa+1, n)`
  fills `sa[1..n]`, `assert(res==0)` (fail-closed on allocation failure; asserts are
  live — no `-DNDEBUG` in `cpp/Makefile` or `BUILD-LINES.md`).
  **LOW (dead check):** :89–90 asserts `sa.size() == n+1` twice; the second was
  evidently meant for `lcp`. Both callers pass `lcp` of size ≥ n+1 (`L(n+2)` at :119,
  `lcp(sample_size+1)` at :597), so nothing is out of bounds today; the guard that would
  catch a future caller is missing.
- `sa2lcp32` :16–47: Kasai. `rank(n+1)`, `rank[sa[i]] = i` for i ∈ [0, n] — `sa` is a
  permutation of [0, n], in bounds. `lcp[0] = -1`, `lcp[1] = 0` (rank-1 suffix's
  predecessor is the empty suffix). Loop :33–46: `k = rank[i]`, `j = sa[k-1]` (k ≥ 2 so
  k−1 ≥ 1), compares guarded by `i+h < n && j+h < n`, writes `lcp[k]` for k ∈ [2, n].
  When `k == 1` the computation is skipped and `h` is decremented; by the Kasai
  invariant `lcp[rank[i]] ≥ h_prev − 1` and `lcp[1] = 0`, so `h_prev ≤ 1` there and `h`
  becomes 0 — correct. `assert(n > 1)` :20: n = 1 would abort, but a 1-sample input is
  refused at intake ("Symbol alphabet consists of 1 symbol") before reaching here
  (measured, case F). No out-of-bounds read found in either function.

### 2.2 `SAalgs32` set-up (`:117–163`)

- `L` has n+2 entries; after `calcSALCP32`, `L.erase(L.begin())` and `L[n] = 0`
  (:138–139) give Kaufer's convention: `L[0] = 0`, `L[1..n−1]` = LCP of adjacent sorted
  non-empty suffixes, `L[n] = 0` sentinel that forces the final flush. `assert(L[0]==0)`.
- `v = max L[0..n−1]` :144–147 — spec step 2 of §6.3.6 (LRS length). `L[n] = 0` is
  excluded from the max; harmless.
- `v == 0` → both estimates declined with `-1.0` (:155–160, fork repair for upstream
  #261). Spec: no t exists and `v < u = 1`, so both are undefined; declining is the only
  reading. Callers skip a negative (`non_iid_main.cpp:469, 480, 496, 506`;
  `restart_main.cpp:972–1000`; `conditioning_main.cpp:405, 410`) and record
  `*_not_run = true`. Unreachable at ≥ 1,000,000 samples with k ≤ 256 (pigeonhole).

### 2.3 Tuple counts Q[t] — Kaufer's algorithm (`:165–229`)

`Q(v+1, 1)`, `A(v+2, 0)`, `I(v+3, 0)`. `I[1..j]` is a strictly increasing stack of the
distinct LCP levels with a non-zero `A` in the current run; `A[level]` holds (count − 1)
of suffixes attributed to that level; on an LCP drop (:179–219) levels above `L[i]` are
collapsed downward (`A[I[j]] += A[I[j+1]]`), and `Q[t]` is raised to `A+1` wherever it
is smaller, with the jump `t = I[j]` (:203) justified by the monotonicity
`Q[t] ≤ Q[t−1] ≤ … ≤ Q[1]` that the algorithm maintains. Bounds: `t ∈ (L[i], L[i−1]] ⊆
[1, v]` (asserted :186), `I` values are L values ∈ [0, v] so `A[I[·]]` ∈ [0, v] ⊂ [0, v+1],
`j < v` asserted before every push (:224), `I[j+1] ≤ I[v+1]` inside `I(v+3)`. `A` is
`saidx_t` (int32): `A ≤ n < INT32_MAX` so `A+1` (:194) cannot overflow; `A[I[j]] += c+1`
(:227) is computed in `long` and narrowed to a value ≤ n.

**Verified by brute force (not by reading alone):** the probe computes `Q[t]` from the
spec's definition (dictionary of overlapping slices) and gets identical `t`, `u`, `v`
on every case (log, "MATCH" lines). The period-7 case has `Q[1..6] = 43` on all six
levels — only an overlapping count gives that.

### 2.4 §6.3.5 steps 1–5 (`:231–272`)

| spec | code | verdict |
|---|---|---|
| step 1, largest t with Q[t] ≥ 35 | `for(u=1; (u<=v) && (Q[u] >= 35); u++);` :232, `t = u−1`; asserts :234–236 | inclusive `>= 35` — matches "at least 35"; measured at the boundary (case D: `Q[2] = 35` → `t = 2`) |
| step 3, `P[i] = Q[i]/(L−i+1)` | `((long double)Q[i])/((long double)(n-i+1))` :243 | match |
| step 3, `Pmax[i] = P[i]^(1/i)`, max | `powl(curP, 1.0L/i)`, `if(curPMax > Pmax)` :244–248 | match, max direction |
| step 4, `2.576` | `ZALPHA_L = 2.575829303548900384158L` :254 | **DOCUMENTED DIVERGENCE D-1 / C22c** — permissive; measured `+1.0e-6 … +1.4e-5` bit on probe inputs (log, "code − text" lines). Not re-reported. |
| step 4, `/(L−1)` | `/((long double)(n - 1))` :254 | match |
| step 4, `min(1, ·)` | `if(pu > 1.0L) pu = 1.0L;` :255–257 | match |
| step 5, `−log2(p_u)` | `t_tuple_res = (double)-log2l(pu)` :259 | match; yields `-0.0` when `p_u == 1` (see 2.8) |
| no t exists | `Pmax == -1` → prints "No strings are repeated 35 times", returns −1 :269–272 | consistent with the text's silence; measured (cases A, G) |

`n` here is the length of the data view passed: `data.len` for Literal, `data.blen`
for Bitstring (callers at `non_iid_main.cpp:468, 479`). That is the "L" of the view
being assessed, as §3.1.5/§6.1 intend.

### 2.5 §6.3.6 steps 1–5 (`:274–346`)

| spec | code | verdict |
|---|---|---|
| step 1, u | same `u` as §6.3.5 (:232) | match (the two sections define the same quantity) |
| step 2, decline iff v < u | `if(v>=u) {…} else { printf("LRS Estimate: v<u. Can't Run LRS Test."); lrs_res = -1.0; }` :275, 342–346 | match |
| step 3, `Σ C(C_i,2)` | `S(v+1)` uint64; flush loop :279–311 accumulates `((A[t]+1)*A[t])>>1` where `A[t]` = count − 1 (:301); `assert(S[t] >= priorS)` | match; brute-force identical on all cases |
| step 3, `/C(L−W+1,2)` | `choices = ((n-i)*(n-i+1))>>1` :317 = `(n−W+1)(n−W)/2` | match |
| step 3, `P_W^(1/W)`, max | `pow(curP, 1.0/((long double)i))`, `if(Pmax < curPMax)` :319–323 | match in value. **LOW:** `pow`, not `powl` (`SAalgs64` :554 uses `powl`); with `<cmath>` and `using namespace std` the `long double` overload is selected, and on arm64 `long double == double` anyway, so no measured effect here; on x87 it is at most a last-ulp difference. |
| step 4 | `:326–329` as in 2.4 | D-1 again |
| step 5 | `lrs_res = (double)-log2l(pu)` :331 | match |

Flush-loop correctness (:279–311): a drop from `L[i−1] ≥ u` to `L[i]` flushes levels
`t ∈ (max(L[i], u−1), L[i−1]]` into `S[t]`, carries the surviving count into
`A[max(L[i], u)]` (:306) and zeroes the level above. The `L[n] = 0` sentinel ends
every run. Stress-measured on case E (`v = 293`, `u = 63`; Bitstring `v = 879`,
`u = 187`) and the mixed-level cases C/D — all MATCH.

`S[i] > 0` for every `i ∈ [u, v]` (a prefix of the repeated v-tuple repeats), so
`pow(0, ·)` never occurs; `Q[i] ≥ 35` for `i < u`, so no `log(0)`; `p_u ∈ (0, 1]` so
`log2l` is finite. **No NaN is reachable in this component** by that argument; see 2.8
for what the callers would do if one were.

### 2.6 Widths and sizes

- 32/64 dispatch `:587–593`: `n < INT32_MAX` → `SAalgs32`. The 64-bit path (and
  `uint128_t` arithmetic) is reachable only at ≥ 2,147,483,647 samples — far outside the
  1M–8M target profile, and **not measured** here. Differences from the 32-bit twin:
  `assert(n <= SAINDEX64_MAX - 1)`, `powl` (correct), `lrs_res = -log2(pu)` :567
  (`log2` without the `l`; same overload remark as above).
- Overflow guards: `(mult assert)` :133 states `n(n+1) ≤ UINT64_MAX`, which bounds
  `(A+1)·A` (:301) and `(n−i)(n−i+1)` (:317) for all n < 2^31. `S[t]` ≤ C(n,2) < 2^61.
- `long int n` on LLP64 (Windows) is 32-bit, but `data.len` is `long` there too and the
  callers refuse > INT_MAX (`iid_main.cpp:393`), so there is no path where `n` exceeds
  the type. `%ld` formats match `long`.
- Memory at 8M bits: `sa` 32 MB + `L` 32 MB + `rank` 32 MB (transient) + divsufsort
  internal — well inside 16 GB.
- 1-bit vs 8-bit: at `alph_size ≤ 2` under `-i` only the Literal view runs
  (`non_iid_main.cpp:467`); at `alph_size > 2` both. `bsymbols` are built from the
  **masked raw** symbols, not the translated ones (`utils.h:520–538`, comment "using
  the non-mapped data"); the probe's Bitstring brute force does the same and matches.
  A bijective translation does not change tuple equality, so Literal counts are
  translation-invariant.

### 2.7 §5.2.5 `len_LRS_test` (`:643–771`) — the IID LRS test

- `calc_proportions(data, p, L)` (`utils.h:967`) does `p[data[i]]++` into `p(k)`.
  **In bounds because** `read_file` translates so that every `symbols[i] < alph_size`
  (`utils.h:506–545`), `restart_main` passes translated `rdata/cdata` with
  `data.alph_size` (:830–831, :1118–1119), and `iid_main -c` passes bits with `k = 2`
  (:383, :412). I found no caller where `k` is smaller than the number of distinct values
  present.
- `p_col = Σ p_i²` in `long double` from `double p_i` (:628–635, upstream, PR #248).
- **R-1 clamp** :674–677 `if(p_col < 1/k) p_col = 1/k`. Direction: by Cauchy–Schwarz
  the true `p_col ≥ 1/k` with equality only at uniform, so the clamp moves a rounded
  value **up to at most the true value**; a higher `p_col` makes `Pr(X ≥ 1)` larger and a
  PASS likelier, so relative to the *computed* value it is permissive by a rounding error
  (~1e-17 relative, ×W ≈ 1e-15 in the log statistic), and relative to the *exact*
  value it is conservative or equal. The only way it could overstate is `k` < distinct
  count, excluded above. **I could not break it.** Platform: the bound is formed in
  `long double` on both formats; CI measured 117/255 (53-bit) and 155/255 (x87) sizes
  aborting pre-repair (FDT A.1).
- `p_col ≥ 1 − LDBL_EPSILON` → PASS (:682–690): spec gives `Pr = 1`. Correct.
- `W = len_LRS32(data, L)` :695–699: max of `lcp[0..L]` (`lcp[0] = −1`, so `W ≥ 0`).
- **C18** :713 `n_choose_2((int64_t)L − (int64_t)W + 1)`; `utils.h:1027–1030` multiplies
  in `int64_t` with `assert(n ≤ INT_MAX)`. `L − W + 1 ≤ INT_MAX + 1` only when `W = 0`
  with `L = INT_MAX`, impossible (`W = 0` needs `L ≤ k ≤ 256`). Cannot break.
- **#153 log domain** :704, :768–770: pass iff `W·ln p_col ≥ ln(1 − 0.999^(1/N))`,
  derived from `1 − (1 − p^W)^N ≥ 0.001` by monotone steps (comment :759–767);
  `-expm1l(logl(0.999L)/N)` keeps the `1 − 0.999^(1/N) ≈ 1e-3/N` difference exact at
  `N ~ 5e11`. Inclusive `>=` matches "fails if … less than 0.001". The verbose
  `Pr(X ≥ 1)` (:738–755) is display only; the decision does not use it. `N = 0` is
  impossible (`W ≤ L − 1`).

### 2.8 Degenerate results and what the callers' `min()` sees

- Declined estimators return `−1.0`; every caller tests `>= 0` (or `>= 0.0`) before
  folding into `min()` and sets `*_not_run` (non_iid) — a declined estimate is visible
  in the report, not silently dropped. In the probe (case A, G) the Literal t-Tuple is
  declined and `H_original` is formed from the others.
- **LOW, measured:** `p̂ = 1` (every tuple position repeats, case E period-7) gives
  `p_u = 1` and `-log2l(1.0L) = -0.0`. `-0.0 >= 0.0` is true, so it is accepted;
  `std::min` propagates it; stdout prints `Literal LRS Estimate: min entropy = -0`,
  `H_original = -0`, `Assessed min entropy: -0` (`logs/analysis-ttuple-lrs-E_period7_n300_w3.out:53,100–101`),
  and the JSON report carries `-0.0` seven times
  (`logs/analysis-ttuple-lrs-E-report.json`). Numerically zero entropy — the
  conservative figure — so direction neutral; a strict downstream parser that rejects a
  negative entropy would see a well-formed `-0.0`. The same shape exists in MultiMMC and
  LZ78Y on that input (lines 83, 97), so it is not specific to this component.
- **LOW, design note:** the `>= 0` guards treat a NaN exactly like a decline — a NaN
  would be silently excluded from `min()` and marked "not run". I argued in 2.5 that no
  NaN is reachable from this component; the guard would not distinguish one if it were.

---

## 3. Prior repairs touching this component, and how I would try to break each

| repair | where | how to break | status after this analysis |
|---|---|---|---|
| **R-1** clamp `p_col ≥ 1/k` (OC-41, 2026-10-19) | `lrs_test.h:674–677` | (a) pass a `k` smaller than the distinct count — needs a caller bypassing `read_file`'s translation: none found (`utils.h:542–544`, `restart_main.cpp:830`, `iid_main.cpp:383,412`); (b) exactly balanced k = 3, 6, 7, 9, 12 at 1M (the original reproducer) must complete on arm64 **and** x87 CI; (c) `-c` bitstring exactly balanced (k = 2, never tripped — power of two); (d) `k = 1` — refused at intake before the call | not broken; direction conservative w.r.t. exact value |
| **C18** `n_choose_2` in `int64_t` (OC-53) | `utils.h:1027`, `lrs_test.h:713` | push `L − W + 1` past `INT_MAX` (impossible with `W ≥ 1` once `L > 256`); re-run the Windows CI job that measured it (OC-48) | not broken |
| **#153** log-domain decision | `lrs_test.h:704, 768–770` | force `p_col^W < LDBL_MIN`: needs `W·log2(1/p_col) > 1022` — e.g. k = 256 uniform with `W > 127`, or bits with `W > 1022` — a repeat that long is itself a FAIL; check that the else-branch of the verbose print (:743–749) prints 0 and the decision still says FAIL | not broken; decision independent of the print |
| **#261** `v == 0` decline | `lrs_test.h:155–160` | 2 distinct bytes; 256 distinct bytes once each; width 1 `\x00\x01`; both estimates must be declined and the report must show `literal_not_run` (`regression-estimator-guards.sh:170, 228` covers `two.bin`) | not broken |
| **R-2** restart `>= 0` folds | `restart_main.cpp:972–1000` | de Bruijn B(100,3) (`regression-restart.sh:256–270`) where LRS declines; also a t-Tuple decline — unreachable at 1M with k ≤ 256 | not broken |
| **#246/#248** proportion accumulation (upstream) | `utils.h:967` | unchanged from upstream; the R-1 clamp covers the residual | n/a |
| iid `INT_MAX` refusal protecting `const int L` | `iid_main.cpp:393` | `-c` at width 8 with > 268,435,455 samples — heavy, not run | not measured |
| D-1 / C22c constant | `utils.h:76`, `lrs_test.h:254, 326` | not a repair; measured deltas `+1.0e-6 … +1.4e-5` bit here | DOCUMENTED DIVERGENCE |

---

## 4. Edge-case inputs that separate a correct from an incorrect implementation

Constructions are exact; `★` marks the ones where the wrong implementation reports
**higher** entropy. Scaled versions (1M samples) belong to the execution phase.

1. **★ Cutoff boundary `Q[t] = 35`.** Filler from 200 byte values in 20-byte random
   blocks; insert `A B C` (250,251,252) 34 times and a 35th `A B` without `C`. Brute
   force: `Q = [35, 35, 34, 3]` → `t = 2`, `u = 3`, `v = 4`. An implementation using
   `> 35` gets `t = 1`, `p̂max = 35/824 = 0.042` instead of `(35/823)^(1/2) = 0.206`,
   and reports ≈ 4.3 bits instead of 2.04. **Measured: code gives `t = 2`, MATCH**
   (case D). At 1M: same construction with the filler scaled.
2. **★ Overlapping vs non-overlapping counts.** Period-7 string over 7 symbols
   (case E): every `t ≤ 6`-tuple occurs 43 times only if overlaps count; a
   non-overlapping counter gives ≈ 43/t and a far higher entropy. **Measured MATCH.**
   At 1M: `(0,3,1,6,2,5,4)` repeated — expect `H ≈ 0`.
3. **★ Denominator `L − i + 1` vs `L − i` vs `L`.** Large `t` makes the denominator
   sensitive: case E has `t = 62`, `L = 300` (`239` vs `238` is 0.4 %, visible at the
   1e-12 tolerance). **Measured MATCH.** Using `L` (too large) understates `P` and
   overstates entropy.
4. **★ LRS sum `Σ C(C_i, 2)` vs `Σ C_i` or `C(ΣC_i, 2)`.** Case C (k = 4 biased,
   `u = 5, v = 11`) and D (`u = 3, v = 4`) have several distinct repeated W-tuples per
   level; the three formulas differ by factors. **Measured MATCH.**
5. **LRS decline `v < u`.** de Bruijn B(100,3) at 1M (existing R-2 generator): every
   3-tuple once, every 2-tuple ≈ 100 times → `u = 3 > v = 2`. Must print
   `v<u. Can't Run LRS Test` and omit `lrsRes`. **Single-term LRS `u = v`:** insert
   `A B C` 36 times each followed by a *different* fourth byte, filler k = 200 — then
   `Q[3] ≥ 36`, `Q[4] = 2` (chance) → `u = v = 4`, one term in the max.
6. **`p̂ = 1` → `p_u = 1` → `-0.0`.** Case E (measured). At 1M: any purely periodic
   input. Checks the clamp `min(1, ·)` and how `-0.0` is reported/parsed downstream.
7. **No repeat at all.** `\x00\x01` and the 256-byte permutation → `v = 0`, both
   declined, `literal_not_run = true` (regression exists).
8. **Width consistency.** The same bit sequence as a width-1 file and packed MSB-first
   into width-8 bytes: the width-8 **Bitstring** t-Tuple/LRS lines must equal the
   width-1 **Literal** lines exactly (same `L`, same string). Distinguishes LSB/MSB
   packing errors in `bsymbols` construction.
9. **Doubled block (F17 timing, not a correctness case).** 1M = one 500 KB random
   block twice → `v = 500,000`, `S[W] = 1` for all `W ∈ [u, v]`, LRS `p̂ → 0.99995`,
   `H ≈ 7e-5` bit — correct, but the LRS flush loop (`:286–304`) has no jump
   optimisation and costs `O(n·m)` for block length `m`; the t-Tuple loop does jump.
   Known as F17 (`NOT-A-BUG`, tracker :1107). Heavy — execution phase, and a
   wall-clock measurement, not a figure.
10. **Full-byte random at 1M** (case G shape): Literal `Q[1] ≈ 3906 ≥ 35` so t-Tuple
    runs with `t = 1` and LRS with `u = 2, v ≈ 3`; Bitstring `t ≈ 17`, `v ≈ 45`.
    Checks `pow` precision on `P_v = 1/C(8e6,2) ≈ 3e-14` raised to `1/45`.

---

## 5. Probe record (instrument rules 2, 4, 5)

Script `logs/analysis-ttuple-lrs-probe.py`; comparison log
`logs/analysis-ttuple-lrs-probe.log`; per-case stdout `logs/analysis-ttuple-lrs-<case>.out`;
inputs in the scratchpad with sha256 in `logs/analysis-ttuple-lrs-probe-manifest.json`.

Self-check of the brute force against the standard's own examples (cutoff 3, Z = 2.576):
§6.3.5 → `t=3, Q=[9,4,3], 0.5405, 0.8276, 0.273`; §6.3.6 → `u=4, v=5, P4=0.0131,
P5=0.0074, 0.3381, 0.3744, 0.3744, 0.6531, 0.6146` — all reproduced to the printed
digits, so the probe implements the text, not the code.

| case | n | w | views | t-Tuple | LRS | note |
|---|---|---|---|---|---|---|
| A spec example | 21 | 2 | Lit, Bit | declined (Q[1]=9) both — correct | MATCH both (`u=1 v=5`; `u=1 v=10`) | exit 0 |
| B bits p=0.3 | 4000 | 1 | Lit | MATCH `t=13` | MATCH `u=14 v=25` | exit 0 |
| C k=4 biased | 1200 | 8 | Lit, Bit | MATCH `t=4`; `t=36` | MATCH `u=5 v=11`; `u=37 v=92` | exit 0 |
| D cutoff boundary | 824 | 8 | Lit, Bit | MATCH `t=2` (Q[2]=35) | MATCH `u=3 v=4` | exit 0 |
| E period 7 | 300 | 3 | Lit, Bit | MATCH `t=62`; `t=186` | MATCH `u=63 v=293`, `H=-0`; `u=187 v=879` | exit 0; JSON `-0.0` |
| F constant | 500 | 1 | — | not reached | not reached | exit 255, intake refusal "Symbol alphabet consists of 1 symbol" |
| G random bytes | 2000 | 8 | Lit, Bit | declined (Q[1]=18) Lit — correct; MATCH Bit `t=9` | MATCH `u=1 v=2`; `u=10 v=27` | exit 0 |

"MATCH" = integers equal and every float within relative 1e-12 of the brute-force value
computed with `Z = 2.5758293035489008`. The D-1 delta (code − text) measured on these
inputs: `+2.4e-6, +6.7e-6, +1.0e-6, +1.4e-5, +1.8e-6, +2.5e-6, +1.0e-6, +1.8e-6` bit.

---

## 6. What this analysis does not establish

- Nothing at ≥ 200,000 samples was run (analysis phase). The 1M-scale behaviours in §4
  are predictions from the code, not measurements.
- `SAalgs64` and the `uint128_t` arithmetic were read, not executed; they are reachable
  only at ≥ 2^31 − 1 samples.
- x87 80-bit `long double` effects (the `pow`/`log2` spellings) were not measured on this
  host, which has a 53-bit `long double`.
- `len_LRS_test`'s decision was analysed and its repairs read; the probe exercised
  `ea_non_iid` only, so §5.2.5 was not executed here (the IID fail-closed regression and
  the iid label capture at `reference/cpp-verbose-labels-iid.txt:27–30` cover a run).
- Out of this component's scope but noticed: the `alph_size > 2` gate at
  `non_iid_main.cpp:467` (two-symbol data at a declared width > 1 runs the Literal view
  only) is the withdrawn PR #256 question — documented in NOTICE lines 340–364 as the
  fork's accepted upstream reading, not re-reported here.
