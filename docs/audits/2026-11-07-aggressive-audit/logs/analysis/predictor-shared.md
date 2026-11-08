# Shared prediction-estimate machinery — analysis (2026-11-07 aggressive audit)

Component: `cpp/shared/utils.h` — `prediction_estimate_function` (lines 1087–1109),
`calc_p_local` (1111–1198), `predictionEstimate` (1200–1256) — and the four callers
`multi_mcw_test.h`, `lag_test.h`, `multi_mmc_test.h`, `lz78y_test.h`.
Branch `audit/2026-11-07` at commit `a2c3c81314a76947bf3924a72854a867c5d12fa7`.

Files as read (sha256):

| file | sha256 |
|---|---|
| `cpp/shared/utils.h` | `a5462f85e296d8fcd908e0f7f56f445aa0905724d840ea69082cdbc97ffdc60e` |
| `cpp/non_iid/multi_mcw_test.h` | `43cb164e0ece56582ee8ea101635f1785ad76c407c88a0741e9a4264ef44dc65` |
| `cpp/non_iid/lag_test.h` | `621c9b38ed23fc84114519d05599dd57339e592abb2f97028b2ef3eb48d09577` |
| `cpp/non_iid/multi_mmc_test.h` | `bbcd1d0d02e5bae073f82ae4254490bf7192a45502b8d2f921183b6f100ae9f5` |
| `cpp/non_iid/lz78y_test.h` | `793d78d3d3993d0478a2435f414602098db19d5b8e462ba28331d8f0c5f81696` |
| `cpp/ea_non_iid` (production binary, instrument rule 4) | `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` |

Probes written by this analysis (all under `logs/`; none runs on more than 4 samples):

| artefact | sha256 |
|---|---|
| `logs/analysis/predictor-shared-probe.py` (transliteration probe Q1–Q5) | `6acc405696471fcf1b71f41c22aac6a52cbb3073e3c6d6229a46110c3c690a0c` |
| `logs/analysis/predictor-shared-probe2.py` (dense C22a sweep + degenerate states) | `42bbc7686baa7e5c317d94914f22ffd54c82c627d7006047c029280fbce5aa23` |
| `logs/analysis-predictor-shared-probe.log` | `c1223df7e94a2e965e4080e8dab04858f7899e69973c8e5fa25629bc9aa7566b` |
| `logs/analysis-predictor-shared-probe2.log` | `9112763c4bcdb5388986f20fa3fca549c9ed5efbe9f0fac8e8a592d18712947f` |
| `logs/analysis-predictor-shared-tinyN-vv-L3.log`, `-L4.log`, `-vv-exit.log`, `-sha256.log` | tool runs on 3- and 4-sample files, `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`, NON-COMPLIANT by construction |
| `logs/analysis-predictor-shared-tinyN-L3.log`, `-L4.log` | the same runs with `-vvv`, kept because they show the verbose-4 silence noted in §6 |

**The probes are a TRANSLITERATION of the C++ into Python, not an independent reference.**
They exist to answer numeric questions about the C++ that reading cannot settle. The
independent reference (`reference/py90b/`) must not be derived from them.

---

## 0. Verdict in one paragraph

The shared machinery implements §6.3.7 steps 4–7 (and the identical text of §6.3.8–§6.3.10)
faithfully in structure: `P_global = C/N`; the 99 % upper bound with the `P_global = 0`
branch; `r = max_run_len + 1`; a bisection for `P_local` on `[max(1/k, P'_global), 1]`;
`−log2(max(P'_global, P_local, 1/k))`. Every bound points the conservative way, every NaN
path is fail-closed by construction (`std::min(1.0, NaN)` = 1.0; `fmax` drops NaN; a broken
bisection invariant returns `p = 1`), and the four callers pass `N`, `C`, the longest run
(not `+1`) and the observed alphabet size exactly as the standard defines them. Three
departures from the literal text exist and all three were already in the record: `ZALPHA`
for the printed `2.576` (D-1/C22c, documented divergence, permissive by ≤ 3.8e-6 bit); the
recurrence iterated to convergence instead of `x = x_10` (tracker F08, NOT-A-BUG,
"UNVERIFIED") — **now measured at ≤ 6.6e-17 in `P_local`, i.e. zero at double precision**;
and the bisection's answer being the root of a rounding-noisy function (floor term C22a).
On the last, this analysis adds one datum the record does not have: the noise error is
**two-sided**, the tool's `P_local` lands below the exact root in 33 of 84 grid rows (the
overstating side), and while the overstating magnitude stays within the floor's
`8.08e-15 × (N+1)` on every row tried (≤ 0.29× at N ≈ 1e6), the formula is exceeded by 1.72×
in the **conservative** direction at `(N = 4033, r = 3)` — so the C22a constant is not a
bound on |error| and its "MEASURED, not PROVED" status is the right one. **No CRITICAL or
HIGH candidate was found in this component.** Everything below is the evidence.

---

## 1. The standard's algorithm, transcribed

The four predictor sections share this text verbatim (quoted from §6.3.7, PDF p. 57–58;
the same steps are §6.3.8 steps 4–7 p. 59–60, §6.3.9 steps 5–8 p. 61–62, §6.3.10 steps 4–6
p. 64–65).

**S1 — count.** §6.3.7 step 4 (PDF p. 58): *"Let C be the number of ones in correct."*
`correct` is an array of `N` Booleans; `N` is fixed per estimator in each section's step 1:

| estimator | `N` | citation |
|---|---|---|
| MultiMCW | `N = L − w1`, `w1 = 63` | §6.3.7 step 1 (PDF p. 57): *"Let window sizes be w1=63, w2=255, w3=1023, w4=4095, and N = L − w1."* |
| Lag | `N = L − 1` | §6.3.8 step 1 (PDF p. 59): *"Let D = 128, and N = L −1."* |
| MultiMMC | `N = L − 2` | §6.3.9 step 1 (PDF p. 61): *"Let D = 16, and N = L − 2."* |
| LZ78Y | `N = L − B − 1`, `B = 16` | §6.3.10 step 1 (PDF p. 63): *"Let B = 16, and N = L – B – 1."* |

**S2 — global performance and its upper bound.** §6.3.7 step 5 (PDF p. 58):
*"Calculate the predictor's global performance as P_global = C/N. The upper bound of the
99 % confidence interval on P_global, denoted P'_global is calculated as:
P'_global = 1 − 0.01^(1/N), if P_global = 0; min(1, P_global + 2.576 √(P_global(1−P_global)/(N−1))), otherwise,
where 2.576 corresponds to the Z(1−0.005) value."*
Direction: an UPPER bound on the success probability (lower bound on entropy). Constant:
the printed `2.576`. Clamp: `min(1, ·)`.

**S3 — local performance.** §6.3.7 step 6 (PDF p. 58):
*"Calculate the predictor's local performance, based on the longest run of correct
predictions. Let r be one greater than the length of the longest run of ones in correct.
Use a binary search to solve the following for P_local:
0.99 = (1 − P_local x) / ((r + 1 − r x) q) × 1/x^(N+1),
where q = 1 − P_local and x = x_10, derived by iterating the recurrence relation
x_j = 1 + q P_local^r x_{j−1}^(r+1) for j from 1 to 10, and x_0 = 1. Note that solving for
P_local using the logarithm of these equations is robust against overflows. Table 3 given in
Appendix G.2 provides some pre-calculated values of P_local."*
Rounding/termination: none stated beyond "binary search"; `x` is **exactly** the tenth
iterate. Appendix G.2 (PDF p. 84) restates the convention: *"for different r (length of the
longest run of ones +1) values when the length of the input sequence is 1 000 000"*, and
G.2 (PDF p. 83) states the meaning: *"P_local is the successful prediction proportion for
which the observed longest run of correct predictions is the 99th percentile. This is
effectively a one-tail hypothesis test that rejects P'_global in favor of P_local if the
observed longest run, given a success probability of P'_global, is beyond the 99th
percentile."* So `P_local` is also an upper-bound-type quantity; the equation's right-hand
side is Feller's approximation to Pr(no run of length r in N trials), which is decreasing
in `P_local`, so the root is unique where it exists.

**S4 — the estimate.** §6.3.7 step 7 (PDF p. 58):
*"The min-entropy is the negative logarithm of the greater performance metric
min-entropy = −log2(max(P'_global, P_local, 1/k))."*
`k` is the alphabet size of the input, §6.3.7 preamble (PDF p. 57): *"Given the input
S = (s1, …, sL), where si ϵ A = {x1, …, xk}"*. The `1/k` term caps the estimate at
`log2 k` — a predictor cannot be credited with doing worse than chance.

**S5 — worked examples that pin the arithmetic** (used in §2.7 to validate the
transcription): §6.3.7 (PDF p. 59) `N = 9, C = 3, longest run 1 → P_global = 0.3333,
P'_global = 0.7627, P_local = 0.036, estimate 0.3908`; §6.3.8 (PDF p. 60) `N = 9, C = 2,
run 2 → 0.2222, 0.6008, 0.1167, 0.735`; §6.3.9 (PDF p. 63) `N = 7, C = 3, run 2 → 0.4286,
0.9490, 0.1307, 0.0755`; §6.3.10 (PDF p. 65) `N = 8, C = 4, run 2 → 0.5, 0.9868, 0.1229,
0.0191`. Note the spec computes `P_local` even where it cannot bind.

---

## 2. Mapping to the code, step by step

### 2.1 `predictionEstimate(long C, long N, long max_run_len, long k, …)` — utils.h:1200–1256

| spec step | code | agreement |
|---|---|---|
| S4 `1/k` | `:1207 curMax = 1.0 / ((double)k);` | ✓ initialises the max with the floor |
| S2 `P_global = C/N` | `:1209 p_global = (double)C/(double)N;` | ✓ |
| S2 otherwise-branch | `:1229 if(p_global > 0) p_globalPrime = min(1.0, p_global + ZALPHA*sqrt((p_global*(1.0-p_global))/((double)N-1.0)));` | formula ✓; **constant `ZALPHA` = 2.5758293035489008 (utils.h:75) where the text prints 2.576** — DOCUMENTED DIVERGENCE D-1 / C22c / tracker F07 (permissive, measured ≤ +3.80e-6 bit on Literal MultiMCW in FORK-DIVERGENCE §D-1). The branch test `p_global > 0` is equivalent to the text's `P_global = 0` test for a non-negative ratio; `C ≥ 1` gives `p_global ≥ 1/N ≥ 4.7e-10 > 0`, so no rounding-to-zero case. |
| S2 zero-branch | `:1230 else p_globalPrime = 1.0 - pow(0.01, 1.0/(double)N);` | ✓ |
| S4 max | `:1232 curMax = fmax(curMax, p_globalPrime);` … `:1235 curMax = fmax(curMax, p_local);` | ✓; `fmax` returns the non-NaN operand, so a NaN `p_local` could never lower `curMax` |
| S3 guard | `:1233 if((curMax < 1.0) && (prediction_estimate_function(curMax, max_run_len+1, N) > log(0.99)))` | **shortcut, not in the text**: `P_local` is solved only when `F(curMax) > ln 0.99`, i.e. when the root exceeds `curMax`. Because `F` is decreasing in `p` this is exactly the condition under which `P_local` can be the maximum; otherwise the text's `max()` would pick `P'_global` or `1/k` anyway. Equivalent in result; it changes the VERBOSE OUTPUT (prints `P_local can't change the result.`), which the differential driver must treat as "spec's `P_local ≤ max(P'_global, 1/k)`", not as a mismatch. |
| S3 `r = run + 1` | `:1233`/`:1234` pass `max_run_len+1`; `calc_p_local` passes `max_run_len+1` at `:1133` and `:1188`; verbose prints `r = max_run_len+1` at `:1241`, `:1242`, `:1245` | ✓ one convention everywhere; callers pass the raw longest run (§2.4) |
| S4 `−log2` | `:1238 entEst = -log2(curMax);` | ✓; `curMax ∈ [1/k, 1]` so `entEst ∈ [0, log2 k]`, never NaN, never negative except `−0.0` when `curMax == 1` (prints `-0`; passes the caller's `>= 0` guard, see §2.5) |

The F13/OC-58 comment at `:1211–1228` on the argument order of `min(1.0, …)` is correct
as far as it goes: `std::min(a, b)` is `b < a ? b : a`, so `min(1.0, NaN)` yields `1.0`
(fail-closed) and swapping the arguments would yield NaN. The only NaN producer is `0/0` in
the variance term at `N == 1` with `p_global == 1`. The comment's "a 1-symbol alphabet is
refused earlier" is at `non_iid_main.cpp:329 if (data.alph_size <= 1)` (verified). Beyond
that, `N == 1` with `C == 1` is impossible in practice: only generic MultiMMC reaches
`N = 1` (a 3-sample file), and its single prediction at `i = 2` can be correct only when
`S[1] == S[0]` is a seen prefix and `S[2]` equals its successor, which with `L = 3` forces a
constant file — refused at `:329`. The NaN is therefore unreachable even with the test
escape; the 3-sample run in §2.7 reached `N = 1` with `C = 0` and printed
`P_global' = 0.98999999999999999`, `min entropy = 0.014499569695115089`.

### 2.2 `prediction_estimate_function(long double p, long r, long N)` — utils.h:1087–1109

```c
assert(p > 0.0L); //In fact, it is >= 1/k
assert(p < 1.0L);
q = 1.0L-p;
x = 1.0L;
for(int i = 0; (i <= 65) && ((x - xlast) > (LDBL_EPSILON*x)); i++) {
    xlast = x;
    x = 1.0L + q*powl(p, r)*powl(x, r+1.0L);
    assert(x >= xlast);
    assert(p*x <= 1.0L);
}
return((double)(logl(1.0L-p*x) - logl((r+1.0L-r*x)*q) - (N+1.0L)*logl(x)));
```

* The return value is `ln` of the right-hand side of S3's equation — the "logarithm of these
  equations" the text recommends. Target `ln 0.99` is compared by the callers. ✓
* **Deviation from S3: `x` is iterated to convergence (≤ 66 steps, stop when the increment is
  ≤ `LDBL_EPSILON·x`) instead of exactly `x_10`.** Tracker F08: NOT-A-BUG, upstream #133 /
  PR #134, "effect < 1e-10. UNVERIFIED." Direction in sign: the sequence is monotone up, so
  `x_code ≥ x_10`; `∂F/∂x ≈ −(N+1)/x + r/(r+1−rx) − p/(1−px) < 0` for `r < N`, so `F_code ≤
  F_spec`, the root moves DOWN, `P_local` is smaller, the estimate is HIGHER — permissive
  in sign. **Magnitude measured (probe Q1, 84 rows, N ∈ {20, 100, 1000, 4033, 999937,
  999999, 7999937}, r from 2 to 987): |P_local(x_10) − P_local(x_∞)| ≤ 6.6e-17.** At the
  root `q p^r ≈ 0.01/N`, so the fixed-point contraction factor is `(r+1) q p^r x^r ≈
  (r+1)·0.01/N`; ten iterations already leave an error far below 2^-53 for any `N ≥ 20`.
  The deviation is real against the literal text and numerically zero. F08's "UNVERIFIED"
  can be closed on this measurement.
* **`assert(p*x <= 1.0L)` (`:1105`) and the regime `p > r/(r+1)`** (tracker F24). For
  `g(x) = 1 − x + q p^r x^{r+1}`, `x = 1/p` is always a root (`g(1/p) = (p − 1 + q)/p = 0`)
  and `g'(1/p) = (r+1)q − 1`, so for `p > r/(r+1)` the root `1/p` is the SMALLER one and the
  monotone iteration converges to it: `1 − p·x → 0`, `F → −∞` (or NaN under FMA contraction
  when the fused `1.0L − p*x` is exactly computed as a tiny negative; F24's observation).
  Either way the guard at `:1233` reads `F > ln 0.99` as FALSE, which is the conservative
  branch. Whether the assert can fire depends on whether `fl(p·x)` exceeds 1 by an ulp
  after `x` has converged to `fl(1/p)`: probe Q4 evaluated 871 `(p, r)` points above the
  threshold in binary64 and `p·x` never exceeded 1 (`p·x_max ≤ 1 − 9e-13` where the cap of
  66 iterations stops convergence; where convergence completes, `fl(p·fl(1/p)) ≤ 1` by
  round-to-nearest). **Reachability from the bisection**: probes above `r/(r+1)` require
  `lbound > (r−1)/(r+1)` with `F(lbound) > ln 0.99`, i.e. `Pr(no run of r) > 0.99` at a `p`
  for which `p^r ≥ (1 − 2/(r+1))^r ≥ 1/9` — impossible for `r ≤ N − 1`, and for `r ∈ {N, N+1}`
  `P'_global = 1` (shown in §2.6) and no bisection happens. Probe Q5 (265,914 reachable
  `(C, run, N, k)` states, `N ≤ 80`) recorded `max_probe > r/(r+1)` ZERO times. The one
  place the regime IS entered is the guard evaluation itself at tiny `N` (e.g. `N = 1,
  p = 0.99, r = 1`; `N = 2, p = 0.9, r = 1`), which the 3-sample tool run exercised without
  an abort (`exit=0`). **Not reproduced as a crash on this host; 80-bit `long double`
  (x86-64) not measured** — see suspicion 5.
* `assert(x >= xlast)` (`:1103`): monotone map of a monotone sequence; holds unless `powl`
  is non-monotone in its argument, which no evaluation in either probe showed.
* `assert(p < 1.0L)` (`:1090`): `calc_p_local`'s first probe is `(curMax + 1)/2`, which
  rounds to exactly `1.0` only for `curMax = 1 − 2^-53`, where `F(curMax) = −∞` fails the
  guard first. Unreachable.
* **Precision mechanism (this is the C22a term):** `x = 1 + δ` with `δ ≈ 0.01/N`, so `x`
  carries an absolute rounding error of up to ½ ulp(1) = 2^-53 regardless of how small `δ`
  is; `logl(x)` then has absolute error ≈ 2^-53 and `(N+1)·logl(x)` has error ≈ 2^-53 (N+1)
  ≈ 1.1e-10 at N = 1e6. The bisection consumes `F − ln 0.99` whose true magnitude near the
  root is of that same order, so the final decisions are made in noise. A `log1pl` on a
  tracked `δ` would remove the loss; the fork's rule is never to touch estimator numerics,
  and the floor absorbs it as C22a instead. On Darwin arm64 `long double` IS binary64
  (`LDBL_EPSILON = 2^-52`); on x86-64 it is 80-bit (`2^-63`), so the noise there is 2^11
  smaller — which is the size of the arm64-only platform deltas in
  `cpp/selftest/known-platform-deltas.txt` (1.25e-10 … 3.66e-10 on arm64 vs 4.24e-14 on
  x86-64 per FORK-DIVERGENCE §4). Clang's default `-ffp-contract=on` (no flag in
  `BUILD-LINES.md` or `cpp/Makefile`) may fuse `1.0L + a*b` into an FMA, which changes the
  rounding of `x` by up to ½ ulp per iteration relative to an unfused build — the same class
  of effect, and the reason F24 saw NaN on one build and −∞ on another.

### 2.3 `calc_p_local(long max_run_len, long N, double ldomain)` — utils.h:1111–1198

| aspect | code | assessment |
|---|---|---|
| bracket | `:1122 hdomain = 1.0; :1124 lbound = ldomain; :1125 hbound = hdomain;` — `ldomain` is `curMax ≥ max(1/k, P'_global)` | the root is sought only above `curMax`; correct given the guard (root > curMax) and harmless otherwise |
| direction | `:1142 if(log_alpha < pVal) { lbound = p; …} else { hbound = p; …}` | `F(p) > ln 0.99` ⇒ Pr(no run) too high ⇒ `p` too small ⇒ raise the lower bound. ✓ (F decreasing in p) |
| tolerance | `:1139 relEpsilonEqual(pVal, log_alpha, ABSEPSILON=DBL_MIN, RELEPSILON=DBL_EPSILON, 4)` | equality within 1 ulp relative or 4 ulps — effectively never (64 of 49,196 computed states in probe Q5) |
| iteration cap | `:1137 for(j=0; j<ITERMAX; j++)` with `ITERMAX 1076` (`:74`) | never reached in either probe; the bracket collapses after ≤ ~53 halvings and one of the invariant exits fires |
| exits and what they return | `:1152 lbound >= hbound → p = fmin(fmax(lbound,hbound), hdomain)`; `:1158` domain invariant → `p = hdomain = 1.0`; `:1164` target not bracketed → `p = 1.0`; `:1174` midpoint not strictly inside → `p = hbound`; `:1182` `lastP == p` → `p = hbound`; `:1191` new `pVal` outside `[hvalue, lvalue]` ("non-monotone") → `p = hbound` | every exit returns the UPPER bracket or `1.0` (entropy 0) — conservative with respect to the computed `F`. Probe Q5 exit counts: non-monotone 40,777; midpoint-collapse 8,355; relEpsilonEqual 64; others 0. The dominance of "non-monotone" is the noise of §2.2 making `F` non-monotone at the ulp scale; it is the normal termination, not a fault. |
| NaN `pVal` | `log_alpha < NaN` is false → `hbound = p, hvalue = NaN`; then `INCLOSEDINTERVAL(log_alpha, lvalue, NaN)` is false → `:1165 p = hdomain` → `P_local = 1` → entropy 0 | fail-closed |
| what "hbound" means for the ANSWER | `hbound` is the last `p` where the NOISY `F(p) ≤ ln 0.99`; relative to the EXACT root it can be on either side | **measured (probe Q2, binary64 transliteration): 33 of 84 rows have `P_code` below the exact root by more than 2 ulp**, i.e. on the overstating side. Magnitudes: `|P_code − P_exact| ≤ 3.5e-10` at N ≈ 1e6, `≤ 3.1e-9` at N ≈ 8e6; in bits, the overstating maximum is `2.37e-9` at `(N = 999999, r = 3)`, `1.34e-9` at `(999937, 7)`, `7.6e-9` at `(7999937, 7)`, `1.15e-11` at `(4033, 2)` (probe2). |

### 2.4 The four callers — what reaches `predictionEstimate`

| caller | `C` | `N` | `max_run_len` | `k` | spec check |
|---|---|---|---|---|---|
| `multi_mcw_test.h:88 predictionEstimate(C, N, max_run_len, alph_size, …)` with `:21 N = len-W[0]` (`W[0] = 63`), predictions for `i = W[0] … len−1` (`:47`), `C++` and run tracking at `:49–53` | `long` | `L − 63` ✓ §6.3.7 step 1 | longest run (`:51`), not +1 ✓ | `alph_size` (Literal) / `2` (Bitstring) | ✓; declines for `len < 4096` (`:16`) — tracker F04, cannot occur at ≥ 1e6 |
| `lag_test.h:117 predictionEstimate(correctCount, L-1, maxRunOfCorrects, k, …)`; predictions for `i = 1 … L−1` (`:65`) | `long` | `L − 1` ✓ §6.3.8 step 1 | `:72–75` longest run ✓ | `k` = alph_size / 2 (`assert(k >= 2)` `:41`, unreachable: one-symbol alphabets refused at `non_iid_main.cpp:329`) | ✓; declines `L < 3` (`:46`) |
| `multi_mmc_test.h:157 (correctCount, L-2, maxRunOfCorrects, 2, …)` (binary) and `:289 (C, N, max_run_len, alph_size, …)` with `:193 N = len-2`; predictions for `i = 2 … len−1` | `long` | `L − 2` ✓ §6.3.9 step 1 | `:144–149` / `:282–286` — reset on anything but a correct prediction by the winner (F09 repair) ✓ §6.3.9 step 4.d | `2` / `alph_size` | ✓; declines `L < 17` binary (`:36`), `L < 3` generic (`:187`) |
| `lz78y_test.h:124 (correctCount, L-B_len-1, maxRunOfCorrects, 2, …)` and `:209 (C, N, max_run_len, alph_size, …)` with `:142 N = len-B_len-1`; predictions for `i = B_len+1 … len−1` | `long` | `L − 17` ✓ §6.3.10 step 1 | `:110–116` / `:202–206` ✓ | `2` / `alph_size` | ✓; declines `L < 19` binary (`:28`), `L < 18` generic (`:137`) |

`C ≤ N` and `max_run_len ≤ C` hold by construction in each (one increment per predicted
position). `k`: Literal calls pass `data.alph_size` (`non_iid_main.cpp:535, 563, 591, 619`),
the OBSERVED alphabet after `read_file`'s map-down (`utils.h:541–544`); Bitstring calls
pass `2` (`:524, 552, 580, 608`). The text's `k = |A|` is the alphabet of the input; using
the observed alphabet (≤ 2^word_size) makes `1/k` LARGER, so the choice can only lower the
estimate relative to the declared width — conservative or equal.

### 2.5 Combination in `non_iid_main.cpp`

Each predictor result is folded as (e.g. `:524–528`)
```c
ret_min_entropy = multi_mcw_test(data.bsymbols, data.blen, 2, verbose, "Bitstring");
if (ret_min_entropy >= 0) { … H_bitstring = min(ret_min_entropy, H_bitstring); }
else { tc637.bitstring_not_run = true; }
```
`predictionEstimate` returns a finite value in `[−0.0, log2 k]`, never NaN and never −1, so
a predictor is omitted from the minimum ONLY via the callers' size declines in §2.4, all of
which are below the §3.1.1 intake. `−0.0 >= 0` is true, so an estimate of exactly 0 is
folded (printed `-0`). Final: `:636 h_assessed = min(h_assessed, H_bitstring * word_size)`
and `:640 min(h_assessed, H_original)` with `h_assessed` initialised to `word_size` — the
"`min(…, bits)` clamp" of the task is this initialisation; since each predictor is already
≤ `log2 k ≤ word_size` it never binds against a predictor.

### 2.6 Degenerate states (the task's `r >= N`, `r == 0`, `C == 0`, `C == N`, `N` tiny)

Derivations, each confirmed by probe Q5 / probe2 / the tool runs:

* `r == 0` cannot occur: `r = max_run_len + 1 ≥ 1`.
* `C == 0` ⇒ `max_run_len = 0`, `r = 1`, zero-branch `P' = 1 − 0.01^{1/N}`. For `r = 1`
  and `p < 1/2` Feller's expression is exact, `F = N ln(1 − p)`; the guard needs
  `N ln(1 − curMax) > ln 0.99` while `curMax ≥ 1 − 0.01^{1/N}` gives `N ln(1 − curMax) ≤
  ln 0.01`. For `p ≥ 1/2` the §2.2 regime applies (`F → −∞`). So **`P_local` is never
  computed for `C = 0`** and the estimate is `−log2(max(1/k, 1 − 0.01^{1/N}))`: at
  `N = 1e6`, `k = 2` → exactly 1 bit; `k = 256` → exactly 8 bits (probe2 lines 1–2); on
  the tool, `N = 2`: `0.15200309344504995`, `N = 1`: `0.014499569695115089`,
  `N = 3`: `0.3500506909694473` (tinyN logs).
* `C == N` ⇒ `p_global = 1`, variance 0, `P' = min(1, 1) = 1`, `curMax = 1`, guard
  `curMax < 1.0` false, `entEst = −log2(1) = −0.0`. Tool: Bitstring Lag `C = 3, N = 5`
  → `P_global' = 1`, `min entropy = -0`.
* `r ≥ N` ⇔ `max_run_len ≥ N − 1` ⇒ `C ≥ N − 1` ⇒ `P' ≥ (N−1)/N + 2.576/N > 1` ⇒ `1`.
  More generally `P' = 1` whenever `(N − C)(N − 1) ≤ 2.576² C`, i.e. `C ≥ N − 6` at
  `N ≈ 1e6` (probe2: `C = N − 6 → P' = 1`, `C = N − 7 → P' = 0.99999981497`, `H = 2.67e-7`).
* `N == 1` (generic MultiMMC on 3 samples): `(double)N − 1.0 = 0`; `C = 0` takes the
  zero-branch (no division); `C = 1` would give `0/0 = NaN → min(1.0, NaN) = 1.0 → −0`,
  and is unreachable (§2.1). `N == 2` (Lag on 3 samples): `N − 1 = 1`, no hazard.
* `N` at the minimum legal count: width 1, `L = 1e6` → `N = 999937` (MCW), `999999`
  (Lag), `999998` (MMC), `999983` (LZ78Y); width 8 bitstring `L = 8e6` → `7999937` etc.
  All probe rows at those `N` behave as at any large `N`.

Types: `C, N, max_run_len, k` are `long`; all floating work is `double`/`long double`;
there is no integer product in this component. On LP64 `long` covers 1e6–1e9 samples and
8e9 bits. On LLP64 (Windows) `long` is 32-bit: `N ≤ 2^31 − 1` holds for the target
profile, but `blen = len * word_size` (`utils.h:520`, `:707`) overflows above 2^28 8-bit
samples — an intake concern outside this component (the predictors would then see a
negative `len` and decline).

### 2.7 Probe results (the measurements behind §2.1–2.6)

`logs/analysis-predictor-shared-probe.log`:

* **Q3 (transcription validity):** the transliteration reproduces all four worked examples
  with the text's 2.576 — `P'_global` 0.762667/0.600859/0.949002/0.986818, `P_local`
  (unconditional, exact) 0.035968/0.116701/0.130737/0.122949, estimates
  0.390875/0.734902/0.075517/0.019144 against the printed 0.3908/0.735/0.0755/0.0191 — and
  reproduces Appendix G.2 Table 3 at `r = 2…49, 1000, 10000`; the rows labelled 55, 60,
  100 hold the values for 50, 55, 95 (the F27 erratum, confirmed: computed `r = 55` →
  0.7328 is the table's `r = 60` entry). So the probe's `F` is the standard's.
* **Q1 (F08):** `|P_local(x_10) − P_local(x_∞)| ≤ 6.589e-17` over 84 `(N, r)` rows.
* **Q2 (bisection vs exact root):** `|P_code − P_exact| ≤ 3.146e-9` (at N = 8e6); 33 of 84
  rows below the root.
* **Q4 (assert :1105):** 871 evaluations with `p > r/(r+1)`: `fl(p·x) > 1` never; `F` is
  a large negative number (−3.4e4 … −4.3e5 at the cap of 66 iterations).
* **Q5 (reachable states, N = 2…80, k ∈ {2, 3, 256}):** 265,914 states, `P_local`
  computed in 49,196, **0 violations** of: no probe above `r/(r+1)`; `P_local ≥ curMax`;
  estimate finite and in `[0, log2 k]`; `:1105` never would fire.

`logs/analysis-predictor-shared-probe2.log` (dense sweep, overstating direction vs the
floor's `C22a = 8.08e-15 (N+1)`):

| N | rows | worst overstating dH (bit) | at r | C22a(N) | ratio | worst understating dH | ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 999937 | 116 | 1.341e-9 | 7 | 8.079e-9 | 0.17 | 7.567e-9 | 0.94 |
| 999999 | 107 | 2.368e-9 | 3 | 8.080e-9 | 0.29 | 3.194e-9 | 0.40 |
| 4033 | 110 | 1.149e-11 | 2 | 3.259e-11 | 0.35 | **5.605e-11** | **1.72** |
| 7999937 | 71 | 7.582e-9 | 7 | 6.464e-8 | 0.12 | 5.659e-8 | 0.88 |

**Caveat that limits what these numbers assert about the binary:** the probe is Python
binary64 without FMA contraction; the production build on arm64 is binary64 WITH clang's
default contraction, so individual `P_local` values can differ from the probe's in the
last bits — by the very mechanism being measured. The probe shows the mechanism, the size
class and the two-sidedness; the tool's own values must come from the binary
(`oracles/p_local_exact.py` did that through `reproducers/c22_bound.cpp` for the record's
grid). The 3- and 4-sample tool runs agree with the probe to all 17 printed digits on
the states they reach, which are not noise-sensitive.

`logs/analysis-predictor-shared-tinyN-vv-L3.log` / `-L4.log` (tool, non-compliant escape):
`exit=0` both; Literal MultiMMC `N = 1, C = 0 → P' = 0.98999999999999999, H =
0.014499569695115089`; Literal Lag `N = 2 → 0.9, 0.15200309344504995`; Bitstring Lag `C =
3, N = 5 → P' = 1, −0`. No assert fired on the `p = 0.99, r = 1` guard evaluation.

---

## 3. Prior repairs touching this component, and how to try to break each

| repair / record | what it claims | how to attack it |
|---|---|---|
| **F08** (tracker: NOT-A-BUG, "effect < 1e-10. UNVERIFIED") — convergence vs `x_10` | immaterial | Now measured ≤ 6.6e-17. To break it one would need a root where `(r+1) q p^r x^r` is not small, but at any root `q p^r ≈ 0.01/N`. No path; recommend the record's UNVERIFIED be closed on probe Q1 (the reference's `tests/` should compute Table 3 rows both ways). |
| **F13 / OC-58** (comment at utils.h:1211–1228; `reproducers/f13_nan_reachability.c`) — `min(1.0, NaN)` order | NaN unreachable on supported paths; order fail-closed | The argument-order claim is correct; the "unreachable" claim is stronger than the reproducer shows (it only scans `p, N`), but §2.1 closes it structurally: `N = 1 ∧ C = 1` needs a constant 3-sample file, refused at `non_iid_main.cpp:329`. Mutation to prove the guard matters: swap the arguments and inject `N = 1, C = 1` through a unit harness (not reachable from a file) — expected NaN estimate dropped by `>= 0`, i.e. a silently omitted predictor. |
| **F24** (tracker NOT-A-BUG) — `x → 1/p`, FMA NaN vs −∞ | guard decision unchanged | Confirmed in both probe Q4 (871 points) and on the build (3-sample file). Remaining attack: Linux x86-64 (80-bit `long double`) and MinGW runs of `corpus/predictor-shared-tinyN-L3.bin` to show the `:1105` assert stays quiet on those formats; and a grid evaluation of `fl(p·x)` in 80-bit. |
| **F25** (UNCONFIRMED) — termination via invariant exits; `hbound ≥ P_local` not guaranteed | — | Confirmed in substance by probe Q5 (invariant exits dominate) and probe Q2 (33/84 rows below the exact root). The quantity is exactly C22a; see next row. |
| **C22a floor term** (`oracles/entropy_floor.py`, `8.08e-15 (N+1)`, MEASURED) | overstatement from the bisection ≤ `c·K·(N+1)` | New datum: the error's magnitude exceeds the formula by 1.72× at `(N = 4033, r = 3)` in the conservative direction, so the constant is not a bound on |error|; whether the permissive side can exceed it at some `(N, r)` outside the record's grid is open. Attack: run the record's `c22_bound` harness (production headers, FMA as built) over a dense `r = 2…300` at `N ∈ {4033, 999937, 999999, 7999937}` and report BOTH signs against `8.08e-15 (N+1)`; any permissive exceedance is a finding against the floor. Also test `ldomain` values other than the probe's `1e-12` (the record swept `1/2, 1/256, 1/65536, 2^-30`) — the bracket's start changes the rounding path. |
| **D-1 / C22c** — `ZALPHA` | documented | Code matches the documented decision (`:1229`). Nothing to break; the differential driver must carry both constants. |
| **F09** (`regression-multimmc.sh`; REV-003) — Null prediction ends the run | `r` is per §6.3.9 step 4.d | Feeds `max_run_len`. Attack the binary path with a planted novel 17-bit context after a correct run (the winner's prefix unseen ⇒ Null ⇒ run must reset) and compare `r` with the independent reference; REV-003 did this on two fixtures only. |
| **#261 declines** (`lag_test.h:46`, `multi_mmc_test.h:36/:187`, `lz78y_test.h:28/:137`, `multi_mcw_test.h:16`) | decline instead of abort | They decide which `(C, N)` reach this component. Boundary files at `L ∈ {3, 4, 17, 18, 19, 4095, 4096}` × widths {1, 8} under the escape; assert exit 0 and the declined estimator's absence from JSON with its presence at `L + 1` as the rule-7 baseline. Note LZ78Y's binary/generic thresholds differ by one (`19` vs `18`) — deliberate per the comment at `:25–27`. |
| **known-platform-deltas.txt / regression-platform-deltas.sh** (A06/OC-56/OC-87) — 8 rows, `|Δ| ≤ 1e-9` on Darwin arm64 | platform property | §2.2 supplies the mechanism (binary64 `long double` + contraction ⇒ `2^-53 (N+1)` noise in `F`). Attack: compute the exact root for the printed `(C, r, N)` of `biased-random-bytes.bin`'s Bitstring MultiMCW/MultiMMC and `ringOsc-nist.bin`'s Literal MultiMCW; the x86-64 refdata value should be the closer one. This also settles FORK-DIVERGENCE §4's "strongest open candidate" at the arithmetic level. |
| **C18** `n_choose_2` (utils.h:1027–1030) — comment `:1023` "Callers refuse a sample count above INT_MAX (iid_main.cpp, non_iid_main.cpp)" | sufficiency of the `INT_MAX` assert | **The refusal exists only in `iid_main.cpp:393`** (and is scoped to the Section 5 tests); `grep INT_MAX cpp/non_iid_main.cpp` finds nothing. On LP64 a > 2^31-sample `ea_non_iid` run would abort in the LRS test's assert — fail-closed, LOW, not this component's math, but the comment is false as written. |

---

## 4. Edge-case inputs that distinguish a correct implementation of THIS component

Each names the quantity moved, the correct value, and what a wrong implementation would
print. Table 3 values are the spec's (PDF p. 84), `N ≈ 1e6`.

**E1 — `P_local` binds (1-bit, planted run).** 1,000,000 bits from a fixed-seed PRNG,
bits `[500000, 500064)` forced to 0. Expected for Lag/MultiMMC/LZ78Y/MultiMCW: `C/N ≈ 0.50`,
`P' ≈ 0.5013`, longest run ≈ 60 (the winner's lag/depth shortens it by a few), so `r ≈ 61`
and `P_local ≈ 0.737` (Table 3: `r = 60 → 0.7328, 65 → 0.7531`) ⇒ estimate ≈ 0.44 bit —
`P_local` is the maximum. A wrong implementation: skip `P_local` → `−log2(0.5013) = 0.996`
(overstates by ≈ 0.55 bit); use `r = run` instead of `run + 1` → `P_local(60) = 0.7328` →
0.4485 (overstates ≈ 0.008 bit); return the lower bracket → smaller `P_local` (overstates
at the ulp scale). NIST's refdata never exercises this: in
`reference/cpp-verbose-labels-non_iid.txt` seven of eight predictor blocks print
`P_local can't change the result.`

**E2 — off-by-one in `r` moves the FINAL figure (8-bit).** i.i.d. uniform bytes, each
byte copied from its predecessor with probability 0.03, plus one planted run of 7 equal
bytes. Lag-1 is correct ≈ 2.9 % of the time: `P' ≈ 0.0304`; natural longest repeat run ≈ 4
(expected count of a 5-run ≈ 0.02), so the planted run sets `max_run = 6`, `r = 7`,
`P_local(7) = 0.0728` ⇒ Lag estimate `3.78` bits, which BINDS `H_original` (MCV ≈ 7.0,
others 7–8). Wrong `r = 6` → `0.0468` → 4.42 (overstates 0.64 bit); skipped `P_local` →
5.04 (overstates 1.26 bits).

**E3 — the `1/k` floor with a sparse alphabet (8-bit).** Exactly 100 distinct byte values,
uniform, 1e6 samples. Every predictor is at chance (`P' < 1/100`), so each must print
`min entropy = 6.6438561897747244` (= `log2 100`); an implementation using `k = 2^8`
prints 8.0 (overstates 1.36 bit per estimator; the final figure is capped by MCV anyway).

**E4 — `C = 0` for Lag.** `s_i = i mod 256`, 1e6 samples. No lag `d ≤ 128` ever predicts
`s_i`, so Lag has `C = 0`, `P' = 1 − 0.01^{1/999999} = 4.6052e-6 < 1/256`, estimate exactly
8.0; an implementation without the `1/k` term prints `−log2(4.6e-6) = 17.7` or `inf`.
(MultiMMC and LZ78Y predict the counter perfectly, `C ≈ N`, estimate `−0`; the final figure
is 0 — the test is of the per-estimator line.)

**E5 — tiny-`N` states (needs `EA_ALLOW_SHORT_DATASET=1`, non-compliant).** Already run:
`corpus/predictor-shared-tinyN-L3.bin` (bytes `01 02 03`) gives Literal MultiMMC `N = 1,
C = 0, P' = 0.99, H = 0.014499569695115089` and Literal Lag `N = 2, P' = 0.9,
H = 0.15200309344504995`; control `-L4.bin` (`01 02 03 01`) gives `N = 2 → 0.9` and
`N = 3 → 0.78455653099681166`. These are the only inputs that evaluate `F` in the
`p > r/(r+1)` regime; any abort, NaN or a `P_local` line here is a finding.

**E6 — the `min(1, ·)` clamp boundary.** 1e6 ones with 3 isolated zeros (Lag: each costs 2
wrong predictions ⇒ `C = N − 6` ⇒ `P' = 1 ⇒ −0`) versus 4 zeros (`C = N − 8 ⇒ P' =
1 − 7e-7 ⇒ 1.0e-6` bit). Distinguishes clamping before vs after the logarithm.

**E7 — resolve the arm64 `P_local` deltas.** Not a new input: take the printed `(C, r, N)`
of `biased-random-bytes.bin` Bitstring MultiMCW/MultiMMC from `-vv`, compute the exact
root at 50+ digits with the independent reference, and report `P_local(arm64 build) −
exact` and `P_local(x86-64 refdata) − exact`. §2.2 predicts the x86-64 value is closer and
the arm64 value is off by `O(2^-53 (N+1) / |F'(p*)|)`.

---

## 5. Suspicions, ranked for the structured return

1. **Two-sided bisection error vs the C22a floor term** — overstates; LOW severity by
   magnitude (≤ 2.4e-9 bit at N ≈ 1e6 on the transliteration, within the floor's term);
   confidence MEDIUM on mechanism, LOW that the floor constant is ever exceeded
   permissively. Test: §3 C22a row.
2. **F08 convergence vs `x_10`** — permissive in sign, ZERO in magnitude (≤ 6.6e-17);
   confidence HIGH; recommend closing "UNVERIFIED".
3. **`ZALPHA` vs 2.576** — DOCUMENTED DIVERGENCE (D-1/C22c); code matches the decision.
4. **`P_local` computed conditionally** — neutral; a driver-contract note.
5. **`assert(p*x <= 1.0L)` on 80-bit `long double`** — crash; LOW confidence; not
   reproduced on arm64 (871-point grid + build run); x86-64/MinGW NOT RUN.
6. **`long blen` on LLP64 above 2^28 8-bit samples** — cross-component (intake); neutral
   (predictors decline on a negative length).
7. **utils.h:1023 comment cites a non-existent refusal in `non_iid_main.cpp`** —
   cross-component, LOW, crash (assert) not overstatement.
8. **`-vvv` (`verbose = 4`) prints no per-estimator lines** — LOW, neutral; the
   differential driver must use `-vv`.

## 6. Cross-component notes found on the way

* `non_iid_main.cpp` has no `INT_MAX` sample-count refusal (only `iid_main.cpp:393`);
  `utils.h:1023` says it does.
* With `-vvv`, `verbose` becomes 4 and both `verbose == 2` and `verbose == 3` branches in
  every estimator are skipped while the `verbose > 2` overall block still prints
  (`logs/analysis-predictor-shared-tinyN-L3.log` lines 19–22 show the summary with no
  estimator lines). Harmless, but a harness that greps `-vvv` output sees nothing.

## 7. What this analysis does not establish

* Anything about the production binary's `P_local` to the last digit: the probe is an
  un-fused binary64 transliteration; the record's `c22_bound` harness is the instrument
  for that.
* Anything on x86-64 or Windows: every measurement here is Darwin arm64, Apple clang 21,
  binary64 `long double`.
* Anything about the predictors' counting of `C` and the run (that is the four estimator
  components); this analysis takes `(C, N, max_run_len, k)` as given at the call sites.
* The direction claims about the bisection rest on `F` being monotone decreasing in `p`
  in the reachable regime, argued from the Feller form and observed in every probe row;
  not proved analytically for all `(r, N)`.
