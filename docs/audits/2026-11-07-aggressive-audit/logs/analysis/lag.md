# Lag prediction estimate (SP 800-90B §6.3.8) — analysis-phase record

Date: 2026-11-07. Branch `audit/2026-11-07`. Analysis agent for component "Lag".
Binary every probe ran against: `cpp/ea_non_iid` sha256
`1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` (Darwin arm64,
Apple clang 21, production flags; `long double` is IEEE binary64 on this target).
Every probe used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`, inputs ≤ 20,000
samples, and is therefore NON-COMPLIANT by construction. Nothing here was piped;
every verdict below was read back from a file under `logs/`.

Files produced:

| file | what |
|---|---|
| `logs/analysis/lag-probe.py` (+ `lag_probe.py` import copy) | spec transcription from PDF p. 59–60 + input generator + per-spec figures |
| `logs/analysis/lag-compare.py` | labelled-read comparison of C++ `-vv` lines against the spec figures |
| `logs/analysis/lag-assert-search.py` | double-precision simulation of `prediction_estimate_function` over 240 near-periodic constructions |
| `logs/analysis-lag-spec-figures.json` | spec figures for every input, worked-example self-check |
| `logs/analysis-lag-compare.log` | the comparison (13 inputs, both paths) |
| `logs/analysis-lag-assert-search.log` | the 240-row search |
| `logs/analysis-lag-cpp-<input>.log`, `logs/analysis-lag-cpp-exitcodes.log`, `logs/analysis-lag-cpp-binary.sha256` | raw tool output, exit status per run, binary identity |
| `corpus/lag-*.bin` (16 files) | the tiny inputs, sha256 recorded in the JSON and in `analysis-lag-assert-search.log` |

**Headline.** The Lag core (`cpp/non_iid/lag_test.h`) is spec-exact: on 13 tiny inputs
covering both symbol paths, ties, periods 127/128/129, C = 0, and the L = 3 boundary,
every C, r and N matched an independent transcription of the spec text exactly, and
P_global / P_global′ matched bit-for-bit (the spec's worked example is reproduced by the
transcription first). No overstatement path was found in Lag or in the shared predictor
helper. What remains are documented divergences, two LOW usability warts, and
low-confidence crash suspicions on live asserts, each recorded below with the reason it
is believed unreachable.

This agent has read `cpp/`, so NOTHING in `logs/analysis/` may be used as the independent
reference under `reference/py90b/`.

---

## 1. The spec, transcribed step by step

All quotes from `reference/sp800-90b.pages.txt`, §6.3.8 (PDF p. 59–60).

> "The lag predictor contains several subpredictors, each of which predicts the next
> output, based on a specified lag. The lag predictor keeps a scoreboard that records the
> number of times that each subpredictor was correct, and uses the subpredictor with the
> most correct predictions to predict the next value." (p. 59)

Given S = (s1, …, sL), si ∈ A = {x1, …, xk}:

1. **Step 1** (p. 59): "Let D = 128, and N = L −1. Let lag be a list of D values, each
   initialized to Null. Let correct be a list of N Boolean values, each initialized to 0."
2. **Step 2**: "Let scoreboard be a list of D counters, each initialized to 0. Let winner = 1."
3. **Step 3**: "For i = 2 to L:
   a. For d = 1 to D: i. If (d < i), lagd = si−d, ii. Else lagd = Null.
   b. Let prediction = lagwinner.
   c. If (prediction = si,) let correcti-1 = 1.
   d. Update the scoreboard. For d = 1 to D: i. If (lagd = si) 1. Let scoreboardd =
   scoreboardd +1. 2. If scoreboardd ≥ scoreboardwinner, let winner = d."
   - Note the tie rule: `≥`, scanned in **increasing d**, against the **live**
     `scoreboard_winner` (winner may already have moved earlier in the same d loop).
     The worked example (p. 60) confirms: at i = 9, scoreboard becomes (0, 3, 3) and
     the winner used at i = 10 is **2** — the lag updated this round took the tie.
   - For Lag the prediction is never Null: winner = 1 initially and lag_1 = s_{i−1}
     exists for every i ≥ 2; any later winner d was valid when chosen and stays valid.
4. **Step 4**: "Let C be the number of ones in correct."
5. **Step 5** (p. 59): "Calculate the predictor's global performance as P_global = C/N.
   The upper bound of the 99 % confidence interval on P_global, denoted P′_global is
   calculated as: 1 − 0.01^(1/N) if P_global = 0; min(1, P_global + 2.576
   √(P_global(1−P_global)/(N−1))) otherwise, where 2.576 corresponds to the Z(1−0.005)
   value." — an **upper** bound; denominator **N − 1**; printed constant 2.576.
6. **Step 6** (p. 59–60): "Let r be one greater than the length of the longest run of
   ones in correct. Use a binary search to solve the following for P_local:
   0.99 = (1 − P_local x)/((r + 1 − r x) q) × 1/x^(N+1), where q = 1 − P_local and
   x = x10, derived by iterating the recurrence relation x_j = 1 + q P_local^r x_{j−1}^(r+1)
   for j from 1 to 10, and x0 = 1. Note that solving for P_local using the logarithm of
   these equations is robust against overflows. Table 3 in Appendix G.2 provides some
   pre-calculated values of P_local." — the text fixes **x = x10**; no bracket, tolerance
   or termination rule for the binary search is given.
7. **Step 7** (p. 60): "The min-entropy is the negative logarithm of the greater
   performance metric min-entropy = −log2(max(P′_global, P_local, 1/k))."

Worked example (p. 60), D = 3, S = (2,1,3,2,1,3,1,3,1,2): "correct = (0, 0, 0, 1, 1, 0,
0, 0, 0). Then, P_global = 0.2222, P′_global = 0.6008, P_local = 0.1167, and the resulting
min-entropy estimate is 0.735."

**Self-check of the transcription** (`analysis-lag-probe.log`): `selfcheck_pass=True` —
correct = (0,0,0,1,1,0,0,0,0), P′ = 0.6008586, P_local(x10) = 0.1167007, H = 0.7349025.

Appendix G.2 (p. 83–84) states the design intent — "In order to make the predictor
estimates lean toward a conservative underestimate of min-entropy, P_global is replaced by
P′_global" and "basing the min-entropy estimate on max(P′_global, P_local)". Table 3
(L = 1 000 000) gives e.g. r = 4 → 0.0100, r = 10 → 0.1614, r = 36 → 0.6157 (F27 in the
2026-09-30 audit records rows 55..155 as mislabelled by 5 — spec erratum).

---

## 2. Map to the C++, with disagreements quoted

### 2.1 `cpp/non_iid/lag_test.h` — steps 1–4, 6 (counting)

Lines are from the file as read on this branch (118 lines).

| spec | code | verdict |
|---|---|---|
| D = 128 | `#define D_LAG 128U` (:4), `LAGMASK (D_LAG-1)` (:5) | exact |
| N = L − 1 | `predictionEstimate(correctCount, L-1, maxRunOfCorrects, k, "Lag", …)` (:117) | exact |
| scoreboard zeroed, winner = 1 | `long scoreboard[D_LAG] = {0}; int winner = 0;` (:32–33) — 0-based offset = d − 1 | exact |
| 3b/3c prediction = lag_winner = s_{i−winner}; correct if = s_i | `if (curSymbol == S[i - winner - 1])` (:70), with C++ i = spec i − 1 and winner = d − 1 → `S[i−d]` ≡ s_{(i+1)−d} | exact |
| run of ones in correct, r = run + 1 | `curRunOfCorrects++ / maxRunOfCorrects` (:72–75), reset `curRunOfCorrects = 0` on a miss (:77); r = `max_run_len+1` in utils.h | exact |
| 3d: for d = 1..D, if lag_d = s_i, scoreboard_d++, `≥` → winner = d | ring buffer of the **current symbol's** positions, scanned from `end−1` downwards (:82–103): positions descend ⇒ `curOffset = i − pos − 1` ascends ⇒ **d ascends**; `curScore = ++scoreboard[curOffset]; if (curScore >= highScore) { winner = curOffset; highScore = curScore; }` (:92–97) | exact; `highScore == scoreboard[winner]` is an invariant (scoreboard only grows; it grows at `winner` only through this branch, which then updates `highScore`) |
| lag_d defined only for d < i, d ≤ 128 | `cutoff = (i >= D_LAG) ? (i - D_LAG) : 0` (:83); only `buf >= cutoff` counted (:87); position `i − 128` ⇒ d = 128 counted, `i − 129` dropped; `assert(curOffset < D_LAG)` (:91) | exact (inclusive at 128) |
| ring holds ≤ 128 positions | capacity check `(uint8_t)(end - start) == D_LAG` → `start++` (:108) | the 128 most recent occurrences of a symbol are exactly the occurrences within the last 128 positions, so nothing countable is ever evicted |
| first symbol has no prediction | `ringBuffers[S[0]]` seeded with position 0 (:60–62); loop `for (long i = 1; i < L; i++)` (:65) — L − 1 predictions | exact |

Index safety: `S[i − winner − 1]` — `winner` was set at some i0 < i from `curOffset ≤ i0 − 1`,
so `i − winner − 1 ≥ 1`; at i = 1 `winner = 0` → `S[0]`. `ringBuffers[S[i]]` with `new
lagBuf[k]` (:51) is in range because `read_file_subset` maps symbols to `[0, alph_size)`
(`cpp/shared/utils.h:542–544`: `if(dp->alph_size < dp->maxsymbol + 1) … symbols[i] =
symbol_map_down_table[…]`), the bitstring path passes k = 2 over 0/1 bits, and
`alph_size <= 1` is refused at `cpp/non_iid_main.cpp:329` before any estimator runs
(`assert(k >= 2)` at :41 is therefore unreachable from a file).

The fork's one change (commit `21b0a31`, upstream #261): :43–49 replaced an `assert(L > 2)`
with `if(L < 3) { printf("*** Warning: not enough samples to run lag test (need at least %d)
***", 3); return -1.0; }`. Measured: `lag-L2-1bit.bin` prints the warning, exit 0, a report is
still produced; `lag-L3-1bit.bin` / `lag-L3-8bit.bin` run with N = 2 (labels C = 0, r = 1,
N = 2, P′ = 0.9, H = 0.1520…), no NaN.

### 2.2 `cpp/shared/utils.h` — steps 5–7 (`predictionEstimate`, :1200–1256)

| spec | code | verdict |
|---|---|---|
| P_global = C/N | `p_global = (double)C/(double)N;` (:1209) | exact |
| P′ = 1 − 0.01^(1/N) if P_global = 0 | `else p_globalPrime = 1.0 - pow(0.01, 1.0/(double)N);` (:1230) | exact |
| P′ = min(1, P + 2.576 √(P(1−P)/(N−1))) | `if(p_global > 0) p_globalPrime = min(1.0, p_global + ZALPHA*sqrt((p_global*(1.0-p_global))/((double)N-1.0)));` (:1229) with `#define ZALPHA 2.5758293035489008` (:75) | **DOCUMENTED DIVERGENCE D-1 / C22c / F07**: binary64 quantile instead of the printed 2.576. Direction: the code's P′ is **smaller** ⇒ entropy **higher**. Measured on the probes (compare log): rand1-20000 Literal 0.98870005256784343 (ZALPHA) vs 0.98869832481904063 (2.576) = **+1.73e-6 bit** at N = 19 999; rand8-5000 Literal 7.5006495702 vs 7.5006128455 = **+3.67e-5 bit/symbol** at N = 4 999. Shrinks as 1/√N; the floor carries it as C22c. Not re-reported. |
| max(P′, P_local, 1/k) | `curMax = 1.0/k; … curMax = fmax(curMax, p_globalPrime);` (:1207, :1232) then P_local only `if((curMax < 1.0) && (prediction_estimate_function(curMax, max_run_len+1, N) > log(0.99)))` (:1233–1236) | **skip optimisation** (upstream `ea1bcf7`): P_local is computed only when f(curMax) > ln 0.99, i.e. when P_local > curMax (f is decreasing in p). Checked on every probe where the tool printed "P_local can't change the result": the spec's P_local was ≤ curMax in all 11 such cases (compare log, "consistent"). Not a divergence in the result. |
| −log2(max(…)) | `entEst = -log2(curMax);` (:1238) | exact; prints `-0` when curMax = 1 (LOW, cosmetic) |

### 2.3 `prediction_estimate_function` (:1087–1109) and `calc_p_local` (:1111–1198)

```
1099  for(int i = 0; (i <= 65) && ((x - xlast) > (LDBL_EPSILON*x)); i++) {
1100      xlast = x;
1101      x = 1.0L + q*powl(p, r)*powl(x, r+1.0L);
1103      assert(x >= xlast);
1105      assert(p*x <= 1.0L);
1108  return((double)(logl(1.0L-p*x) - logl((r+1.0L-r*x)*q) - (N+1.0L)*logl(x)));
```

- **x = x10 vs. converged** (F08, upstream #133): the text fixes x = x10; the code iterates
  up to 66 times to an `LDBL_EPSILON` stopping rule. **Measured:** the transcription computed
  P_local both ways on all 13 inputs (N = 2 … 39 999, r = 1 … 19 998, including r ≈ N) and
  the two agree to **all 17 printed digits** on every one (`analysis-lag-spec-figures.json`,
  `P_local_x10` vs `P_local_converged`). At the root, q·p^r·x^(r+1) ≈ 0.01/(N+1), so
  x10 − x∞ is of order (0.01/N)^11 — far below double resolution. The tracker's "< 1e-10,
  UNVERIFIED" is therefore confirmed and very loose. Documented, not re-reported.
- **Bisection** (`calc_p_local`): bracket `[ldomain = curMax, hdomain = 1.0]` (:1122–1125);
  `if(log_alpha < pVal) lbound = p; else hbound = p;` (:1142–1148) — correct direction
  for a decreasing f; termination by `relEpsilonEqual(pVal, log_alpha, DBL_MIN, DBL_EPSILON,
  4)` (:1139), by `lbound >= hbound` → `p = fmin(fmax(lbound,hbound),hdomain)` (:1152–1155),
  or by any broken invariant → `p = hdomain` (:1159, :1165) or `p = hbound` (:1175, :1183,
  :1192). Every early exit returns a value **≥ the true P_local** (hbound side) except the
  epsilon exit, whose quantisation is the floor term C22a. **Measured on the probes:** C++
  P_local − spec P_local = −9.88e-15, +5.88e-15, −5.66e-15 (three inputs where P_local bound;
  min-entropy differences ≤ 1.43e-14 bit, both signs) — this is evaluation noise from the
  cancellation in `(r+1−r·x)` at r ≈ N, not the bisection; it is the same mechanism the
  independent audit localised to long-double width (`COVERAGE.md:276`) and that
  `cpp/selftest/known-platform-deltas.txt` tolerates at 1e-9. Below every printed figure.
- **Exterior root / F24.** For p > r/(r+1) the smallest root is x = 1/p exactly, so
  `1.0L − p*x` is 0 (→ `logl` = −inf) or, under FMA contraction, a residual of either sign
  (→ −inf-like or NaN). Either way the guard `… > log(0.99)` is false and P_local is skipped,
  which is the right decision because P_local < r/(r+1) always. **Measured on this binary:**
  `lag-assert-control-1bit-20000.bin` (C = 19991, r = 4998, N = 19999, P′ =
  0.99996421172365146 > r/(r+1) = 0.99979996) and `lag-assert-px1-1bit-20000.bin` (C = 19989,
  r = 4072, P′ = 0.99990717807584273, simulated p·x == 1.0 exactly) both exit 0 and print
  "P_local can't change the result." The decision is unaffected by NaN-vs-−inf, as F24 said.
- Inside the bisection the exterior region is never visited: midpoints climb only while
  below P_local, and 1 − P_local ≈ ln(N/0.01)/r exceeds 1/(r+1) by a factor ≳ 7 for every
  N ≥ 10, so the first midpoint above P_local is still below r/(r+1). (Derivation; not a
  measurement. The invariant checks fail closed if it were ever wrong.)

### 2.4 Things the task said to look at, and what the lines say

- **Direction of the bound**: P′ is an upper bound (+Z·σ, `min(1, …)`), :1229. Every probe's
  P′ ≥ P_global (e.g. 0.50393 ≥ 0.49482).
- **Binary-search direction / tolerance / termination**: §2.3; fail-closed on every exit.
- **log of zero**: `logl(1.0L−p*x)` can be `logl(0)` only in the exterior-root case, where the
  result (−inf or NaN) leads to the same skip; `log2(curMax)` has curMax ≥ 1/k > 0.
- **Division by small counts**: `(double)N−1.0` at :1229 needs N ≥ 2 ⇒ L ≥ 3 — the `L < 3`
  guard; `C/N` with N ≥ 2. The F13 NaN producer (N = 1) is unreachable: `assert(k >= 2)`
  aside, `alph_size <= 1` is refused and L = 2 declines.
- **NaN propagation into min()**: `min(1.0, x)` returns 1.0 for x = NaN (comment at
  :1211–1228, F13); `fmax(curMax, p_local)` ignores NaN; `-log2(NaN)` would be NaN and
  `if (ret_min_entropy >= 0)` at `non_iid_main.cpp:553/564` would then record the estimator as
  **not run** rather than fold it — a would-be silent drop, but no NaN producer exists for
  N ≥ 2 (C ≤ N ⇒ 0 ≤ P ≤ 1 ⇒ the sqrt argument is finite and ≥ 0).
- **int vs long, overflow**: positions, counts and `L` are `long`; `winner` is `int` < 128;
  `cutoff` mixes `long` with `128U` — on LP64 the unsigned promotes to `long`; on LLP64
  (`long` = 32-bit) `i − D_LAG` is evaluated in `unsigned long` and stored back into a
  non-negative `long`, fine for L < 2^31. Not Lag-specific: `blen = len * word_size`
  (`utils.h:519`) overflows a 32-bit `long` at 2^28 8-bit samples; C18 already records that
  the LLP64 `long` sweep has not been done.
- **Off-by-one in windows**: d = 128 is counted (`>= cutoff`), d = 129 is not — measured
  below (period 128 → 0.0014 bit; period 129 → 5.13 bit).
- **Minimum legal count**: L = 3 runs (N = 2), L = 2 declines — measured.
- **1-bit vs 8-bit paths**: at width 1 (or any width with exactly two observed values) only
  the Literal path runs with k = 2; at k > 2 both run (`non_iid_main.cpp:551–569`); with
  `-t` the bitstring is cut to 1,000,000 bits (`:344`) so bitstring Lag sees N = 999 999.
  `ea_restart` runs the same `lag_test` on the row and column concatenations
  (`restart_main.cpp:1034/1041`, L = 1 000 000 always).
- **Degenerate estimators and the final min()**: a −1.0 return sets `literal_not_run` /
  `bitstring_not_run` and is excluded from the min (`non_iid_main.cpp:558/569`); that is the
  F11/#255 design and is not an overstatement because the alternative is no figure at all.
  At L = 2 the only estimators that produced a figure were MCV (p_u = 1, H = −0) and
  Markov (H = 1; note its P_{0,0}, P_{1,0}, P_{1,1} = 0 at N = 2 — a Markov-component
  observation, not Lag's); the assessed figure was −0 from MCV.

### 2.5 Two LOW observations that are new to this record

1. **`-vvv` prints no estimator intermediates.** `verbose` starts at 1
   (`non_iid_main.cpp:97`) and each `-v` increments it (:176); the estimators print at
   `verbose == 2` or `verbose == 3` only (`utils.h:1240/1243`), so `-vvv` (level 4) prints
   the 17-digit summary lines (`:655–660`) but NO per-estimator lines. Measured on all 14
   inputs in the first probe pass (logs were then overwritten by the `-vv` pass; the exit
   codes log records the correction). An operator who asks for "more verbose" gets less,
   with no message. Direction: neutral. Severity LOW.
2. **`-0` is printed and stored for a zero estimate** (`-log2(1.0)` = −0.0): "Literal Lag …
   min entropy = -0", "H_original = -0", "Assessed min entropy: -0". Valid JSON, compares
   equal to 0; cosmetic. LOW.

---

## 3. Prior repairs touching this component, and how I tried to break them

| repair | where | attempts (measured unless stated) | result |
|---|---|---|---|
| #261 / F15 — `lag_test` declines at L < 3 (commit `21b0a31`) | `lag_test.h:43–49` | L = 2 at width 1; L = 3 at width 1 and width 8 (two values, mapped); boundary N = 2 feeds `(N−1) = 1` | L = 2: warning, exit 0, report written; L = 3: runs, finite P′ = 0.9, H = 0.152. Other entry points: bitstring path needs `alph_size > 2` which needs len ≥ 3; restart passes L = 10^6. Cannot be bypassed from a file. |
| F13 — `min(1.0, NaN)` argument order (`acedae5`) | `utils.h:1211–1229` | looked for any NaN producer at N ≥ 2: C ≤ N by construction, so none | unreachable; and the order is the fail-closed one |
| D-1 / C22c — ZALPHA not 2.576 (inherited) | `utils.h:75, :1229` | measured delta on every probe (compare log column "text-Z would be") | +1.73e-6 bit at N = 19 999, +3.67e-5 at N = 4 999; permissive, documented, shrinks as 1/√N |
| F08 — converged x not x10 (inherited, `ea1bcf7`/#133) | `utils.h:1099–1106` | both computed on 13 inputs incl. r ≈ N | identical to 17 digits everywhere |
| skip P_local when it cannot bind (inherited, `ea1bcf7`) | `utils.h:1233` | spec P_local vs curMax on all 11 skipped cases | spec P_local ≤ curMax every time |
| F24 — exterior root NaN/−inf (inherited) | `utils.h:1108` | two constructions driving the guard into p > r/(r+1) on the production binary | exit 0, skip, no assert |
| C18 — `long` on LLP64 | not this file | NOT RUN here (analysis phase; no Windows) | `lag_test` itself is LLP64-safe for L < 2^31; the `blen` product is not Lag's |

---

## 4. A crash hypothesis, tested negative

**Hypothesis.** Asserts are live in production (no `NDEBUG` anywhere in `cpp/`). If a
near-periodic input gives the Lag winner W = 7…14 evenly spaced wrong predictions, then
P′ < 1 but P′ > r/(r+1), the recurrence converges fast to x ≈ RN(1/p), and `assert(p*x <=
1.0L)` at `utils.h:1105` might fire (SIGABRT, no report) — fail-closed but a crash on a
plausible "stuck oscillator with a few glitches" capture.

**Test.** `lag-assert-search.py` simulated `:1099–1108` in IEEE double (= arm64 long double)
for 240 constructions (alternating 0101 with 3–8 flips, L = 20 000), both plain and
FMA-contracted forms. **All 240 reach the exterior root; 0 trip either assert.** The final
p·x is 1.0 or 1 − k·ulp, never above. **Reason:** for x ≤ RN(1/p), p·x = 1 + δ with |δ| ≤
2^−53, which is exactly half an ulp of 1.0, so round-to-nearest-even can never produce a
value above 1.0; and the iterate cannot exceed RN(1/p) because the rounding error of
q·p^r·x^(r+1) (≈ (x−1)·2^−52 ≪ ulp(1) when x ≈ 1) is too small to carry the sum past it. The
only regime where that error is O(ulp) is x ≈ 2 (p ≈ 0.5, r = 1, k = 2 — the C = 0 "anti-Lag"
case), where the double root makes convergence O(1/j) and 66 iterations leave x ≈ 1.94, far
from 2. **Confirmed on the production binary** with two of the constructions (exit 0, labels
above). The same half-ulp argument holds for 64-bit-mantissa x87 long double.

Residual (LOW, suspicion): `assert(x >= xlast)` at :1103 holds when ρ ≥ 2t where ρ ≈ (r+1)·t
is the convergence rate and t = x − 1, i.e. with margin (r+1)/2 — marginal only at r = 1 with
an interior root (k > 2, C = 0: `lag-counter8-5000.bin`, p = 1/256, passed). Not observed; a
run with r = 1, k = 3 (p = 1/3) is the closest construction and was not run.

---

## 5. Edge-case inputs that distinguish a correct from an incorrect Lag

All constructions have a tiny instance in `corpus/`; the 10^6 versions are for the
execution phase (`period-128` × 7 813 blocks is 1 000 064 bytes, within the 1 MB cap).

| name | construction | correct result | what a wrong implementation would do |
|---|---|---|---|
| **period-128 (8-bit)** | 128 random bytes repeated | Literal Lag C = N − 128 − (early misses), r ≈ N − 128, P′ ≈ 1, **H ≈ 1e-3 bit** (measured 0.001381 at L = 5000) | D = 127, an exclusive `> cutoff`, or `i − D_LAG − 1`: lag 128 never scores, C ≈ chance, **H ≈ 5 bit — OVERSTATES**. This is the single most valuable Lag test. |
| period-129 (8-bit) | 129 random bytes repeated | Lag is blind by design: C = 115, r = 2, **H = 5.13** at L = 5000 (MultiMMC/LZ78Y bind the assessment, measured H_original = −0) | D = 129 or an inclusive off-by-one the other way: H ≈ 0 — understates (conservative, but a spec departure) |
| period-127 | 127 random bytes repeated | lags 127 **and** 254 … only 127 is in range; C = 4871, r = 4872, H = 0.001380 | same as period-128 in the other direction |
| **tie-heavy k = 3** | iid draws from {0,0,0,1,1,2} | C = 1970, r = 8 at L = 5000 (the `≥`-largest-d rule) | a `>` rule, a descending-d scan, or comparing against a stale `scoreboard_winner` changes C (direction data-dependent; it is the one place the tie rule is observable) |
| period-4 `0011` binary | `(i//2)&1` | all even lags ≥ 4 score every step; winner migrates to **128** (largest tie); C = 19996, r = 19994, H = −0 | a `>` rule keeps winner 4 — same H here, so add glitches to make the winner observable: a flip at j gives misses at j and j + winner |
| alternating `0101` binary | `i&1` | lag 1 always wrong, lag 2 always right; C = N − 2, H = −0 | a predictor that used lag 1 forever (no scoreboard update) would report 1.0 bit — **OVERSTATES** |
| **anti-Lag binary** (F28) | adaptively pick s_i ≠ s_{i−winner}, simulating the scoreboard | C = 0, P′ = 1 − 0.01^(1/N) ≈ 4.6e-6, curMax = 1/2, r = 1, **H = 1.0** (spec-faithful blind spot); exercises the slow double-root path (66 iterations) | an implementation that aborts on `p*x <= 1` or hangs in the recurrence; also a "complement predictor" would be a spec departure |
| counter 0..255 | `i & 255` | Literal C = 0, r = 1, 1/k binds, **H = 8**; Bitstring C = 30367, r = 15, H = 0.387 (period 256 is beyond D) | nothing — documents the blind spot (F29) and the C = 0 branch of step 5 |
| **near-periodic, W = 8…18 misses** | alternating with 3–8 flips evenly spaced (`lag-assert-*.bin`) | P′ > r/(r+1), exterior root, p·x rounds to exactly 1.0 ⇒ `logl(0)`/NaN ⇒ P_local skipped, exit 0, H ≈ 1e-4 | an abort on a live assert, or a P_local = 1.0 from a NaN-tripped invariant (would print H = 0 — understates) |
| L = 3 / L = 2 | `[0,1,0]`, `[0,1]` | L = 3 runs (N = 2, P′ = 0.9, H = 0.152); L = 2 declines with the warning and still reports | an abort (the pre-#261 behaviour), or a NaN at N = 1 folded into the min |
| `-t` wiring (8-bit, 10^6 bytes) | first 125 000 bytes period-128, rest random | with `-t` the bitstring Lag sees only the periodic 10^6 bits ⇒ H_bitstring ≈ 0 and 8 × H_bitstring binds; with `-a` it sees all 8 × 10^6 bits ⇒ high | a path that ignored `-t`/`-a`, or that truncated the literal path |

For the differential driver: the labelled lines are `<Literal|Bitstring> Lag Prediction
Estimate: C | r | N | P_global | P_global' | P_local | min entropy`, printed at **`-vv`**
(not `-vvv`), plus the sentinel "P_local can't change the result." which the driver must
treat as "P_local ≤ max(P′, 1/k)" rather than as a missing value.

---

## 6. What this analysis does not establish

- Nothing was run at ≥ 10^6 samples; the 1/√N-scaled quantities (D-1 delta, C22a) and the
  long-double platform deltas (1e-10) are extrapolated from N ≤ 39 999 and from the prior
  campaign's measurements, not re-measured.
- No build was made; the production binary's behaviour under FMA contraction at :1101/:1108
  is inferred from the simulation agreeing with its printed P′ and from its exit status, not
  from disassembly.
- The half-ulp argument in §4 assumes round-to-nearest-even and that `p*x` in the assert is
  a single rounded product; a compiler that kept `p*x` in a wider register (x87 double
  rounding) is not covered by the measurement, only by the same argument at 64 bits.
- Windows / LLP64 and Linux x86-64 were NOT RUN.
