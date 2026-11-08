# Collision estimate (SP 800-90B §6.3.2) — analysis-phase record

Audit: 2026-11-07 aggressive audit, branch `audit/2026-11-07`. Phase: ANALYSIS (no builds, no heavy runs).
Component: `cpp/non_iid/collision_test.h` (`F`, `col_exp`, `collision_test`) and its three callers
(`cpp/non_iid_main.cpp:386-408`, `cpp/restart_main.cpp:883-907`, `cpp/conditioning_main.cpp:388-389`).
Spec authority: `reference/sp800-90b.pages.txt` — §6.3.2 at PDF p. 50-51, Appendix G.1.1 at PDF p. 82-83.

Binaries every probe here ran against (instrument rule 4):

| binary | sha256 |
|---|---|
| `cpp/ea_non_iid` (built 2026-11-07 19:28) | `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` |
| `cpp/ea_conditioning` (built 2026-10-20) | `b7a55528a8270672a89bd26265feb529293718a83d2a19a350cd035289d83460` |

Every probe below used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and inputs of ≤ 3,001 samples; every run is
therefore NON-COMPLIANT by construction and is cited only for the estimator's arithmetic. All outputs were written to
files under `logs/` (rule 17) and read back from those files; nothing was piped into `head`/`tail`.
Probe inputs are in `corpus/collision-*.bin` with sha256s in `logs/analysis-collision-corpus-sha256.log`.

Headline: **the estimator function is spec-conformant and numerically robust; no path inside `collision_test()`
overstates min-entropy beyond the already-documented ZALPHA divergence (D-1 / C22c family).** The one new defect
is at a CALLER: `cpp/conditioning_main.cpp:389` folds `collision_test()`'s −1 "declined" return into `h'` with no
`>= 0` guard, giving `h' = -1`, `h_out = -8`, exit 0 — reproduced, direction UNDERSTATES, outside the target
profile (ea_conditioning). Details in §3 and §5.

---

## 1. The spec's algorithm, step by step

All quotes are from SP 800-90B §6.3.2 (PDF p. 50-51) unless marked.

> "This entropy estimation method is only applied to binary inputs. Given the input S = (s1, …, sL), where si ϵ A = {0,1}," (PDF p. 50)

| step | spec text (quoted) | what it fixes |
|---|---|---|
| 1 | "Set v = 0, index =1." | counters |
| 2 | "Beginning with sindex, step through the input until any observed value is repeated; i.e., find the smallest j such that si = sj, for some i with index ≤ 𝑖 < 𝑗." | for binary data j − index ∈ {1, 2}: two equal bits → j = index+1; two different bits → the third bit must equal one of them → j = index+2 |
| 3 | "Set v = v + 1, tv = j – index + 1 and index = j + 1." | t ∈ {2, 3}; the scan restarts AFTER the collision (non-overlapping) |
| 4 | "Repeat steps 2-3 until the end of the dataset is reached." | a trailing fragment with no collision (`01`, or a single bit) is dropped |
| 5 | "Calculate the sample mean 𝑋̄, and the sample standard deviation 𝜎̂, of ti as 𝑋̄ = (1/v) Σ ti , 𝜎̂ = sqrt( (1/(v−1)) Σ (ti − 𝑋̄)² )." | SAMPLE sd with v−1 — needs v ≥ 2 |
| 6 | "Compute the lower-bound of the confidence interval for the mean, based on a normal distribution with a confidence level of 99 %, 𝑋̄′ = 𝑋̄ − 2.576 𝜎̂/√v." | LOWER bound; constant printed as 2.576 |
| 7 | "Using a binary search, solve for the parameter p, such that 𝑋̄′ = p q⁻² (1 + ½(p⁻¹ − q⁻¹)) F(q) − p q⁻¹ ½(p⁻¹ − q⁻¹). where q = 1 − p, p ≥ q, F(1/z) = Γ(3, z) z⁻³ e^z, and Γ(a,b) is the incomplete Gamma function defined as ∫_b^∞ t^(a−1) e^(−t) dt. An efficient implementation of F(1/z) is provided in Appendix G.1.1. The bounds of the binary search should be 1/2 and 1." (PDF p. 50-51) | solve on p ∈ [½, 1]; no tolerance or iteration cap is specified |
| 8 | "If the binary search yields a solution, then the min-entropy estimation is the negative logarithm of the parameter, p: min-entropy = –log2( p). If the search does not yield a solution, then the min-entropy estimation is: min-entropy = log2(2)=1." (PDF p. 51) | fallback is ONE FULL BIT |

Appendix G.1.1 (PDF p. 82-83): "The function F(1/z), used by the collision estimate (Section 6.3.2), can be
approximated by the following continued fraction" (a continued fraction derived from DLMF 8.9.2 follows).

Worked example (PDF p. 51): L = 40, "v=14, and the sequence (t1, … tv) is (3, 3, 3, 3, 3, 2, 3, 2, 2, 3, 3, 3, 3, 2).
Then 𝑋̄ = 2.7143, 𝜎̂ = 0.4688, and 𝑋̄′ = 2.3915. The solution to the equation is p = 0.7329, giving an estimated
min-entropy of 0.4483." Note Σt = 38 of L = 40: the trailing `(1, 0)` is dropped, confirming the reading of step 4.

### 1.1 Closed form of step 7 (derived here, verified exactly)

For a = 3 the upper incomplete gamma is exact: Γ(3, z) = e^(−z)(z² + 2z + 2). Hence
F(1/z) = (z² + 2z + 2)/z³ and, with z = 1/q, **F(q) = q(2q² + 2q + 1)** — so the continued fraction of G.1.1 is
unnecessary; the closed form is exact. Substituting into step 7 and simplifying (done by hand and checked in
exact rational arithmetic, `logs/analysis-collision-algebra.log`):

    X̄′(p) = −2p² + 2p + 2 = 2 + 2pq

which is exactly the expected time to first collision for a two-symbol source (t = 2 w.p. p² + q², t = 3 w.p. 2pq).
It is monotone decreasing on p ∈ [½, 1], from X̄′(½) = 2.5 down to X̄′(1) = 2. So:

- a solution exists in the spec's bounds iff **2 ≤ X̄′ ≤ 2.5**;
- the root with p ≥ ½ is **p = ½ + sqrt(1.25 − 0.5·X̄′)**;
- X̄′ > 2.5 (more than half the collisions take 3 steps — anti-correlated data) → no solution → spec says 1 bit;
- X̄′ < 2 → no solution in [½, 1] either → read literally, the spec says 1 bit (this is the D-2 question).

Log: `logs/analysis-collision-algebra.log` — max |spec expression − closed form| over a 99-point grid is 4.0e-12
(floating-point noise of the spec's own form near q → 0), and five exact rational checks are identical.

---

## 2. Map to the C++ and compare

File: `cpp/non_iid/collision_test.h` (95 lines; identical to the tag `unrepaired-reference-2026-10-15` except
for the v < 2 guard at :38-50, commit `c217f20`). Everything it calls from `cpp/shared/utils.h`: `ZALPHA` (:75),
`sqrt`, `log2`, `printf`.

### 2.1 F and the (dead) spec expression — :5-13

```c
double F(double q){                      // :5
   return q*(2.0*q*q+2.0*q+1.0);         // :6   == exact F(q) derived in 1.1  ✓
}
double col_exp(double p){ ... }          // :9-13  the spec's step-7 expression verbatim; NOT CALLED anywhere in cpp/
```

`col_exp` is dead code (grep over `cpp/` finds only its definition). It is still a faithful transcription of step 7
and would be the natural "spec oracle" for a differential driver. No defect.

### 2.2 The scan — steps 1-4 ↔ :23-36

```c
i = 0; v = 0; s = 0.0;                                   // :23-25   step 1
while(i < len-1){                                        // :28      needs data[i+1] to exist: i+1 <= len-1  ✓
    if(data[i] == data[i+1]) t_v = 2;                    // :29      j = index+1  ✓
    else if(i < len-2) t_v = 3;                          // :30      j = index+2, needs data[i+2] to exist  ✓ (never READ: binary assumed)
    else break;                                          // :31      trailing "01": dropped  ✓ (matches worked example: 38 of 40)
    v++;  s += t_v*t_v;  i += t_v;                       // :33-35   step 3; i accumulates Σt; s accumulates Σt²
}
```

- Correct for binary data. `data[i+2]` is never read, so there is no out-of-bounds access, but the t=3 branch
  *assumes* the third symbol collides — true only for a two-symbol alphabet. Every caller enforces that:
  `non_iid_main.cpp:399` gates the Literal call on `data.alph_size == 2`; the Bitstring calls (:386, restart,
  conditioning) pass `data.bsymbols`, which is 0/1 by construction (`utils.h:536`); `restart_main.cpp:883` gates
  on `data.alph_size == 2`. ✓
- Off-by-one check at the tail: i = len−3 → t=3 consumes the last three; i = len−2 with equal bits → t=2; with
  unequal bits → break. All three verified against the spec's reading. ✓
- Types: `long v, i; int t_v;` (:18-19). `t_v*t_v` ∈ {4, 9} as int, accumulated into a double `s` — every partial
  sum is an integer < 2^53 for any `len` < 2^53/9, so Σt² is exact. On LP64 (this host, Linux) `long` is 64-bit;
  on LLP64 (Windows) `long` is 32-bit, but the overflow would already have happened in `data_t.blen` at intake
  (C18 class, documented), not here.

### 2.3 Step 5 — :47-57

```c
if(v < 2){ printf("... not enough collisions ... (need at least 2, found %ld) ***\n", v); return -1.0; }  // :47-50 (c217f20)
X = i / (double)v;                                       // :54   X̄ = Σt / v  ✓ (i == Σt because break precedes i += t_v)
s = sqrt((s - (i*X)) / (v-1));                           // :56   σ̂² = (Σt² − (Σt)²/v)/(v−1)  — algebraically == spec's two-pass form  ✓
```

Numerical robustness of :56 (the one place a NaN could be born):
- With t ∈ {2,3}, the identity v·Σt² − (Σt)² = n₂·n₃ holds exactly (checked on 1000 random (n₂,n₃) in the algebra
  log), so the true value of `s − i*X` is n₂n₃/v: either exactly 0 (all t equal — and then `X` is exactly 2.0 or
  3.0 and `i*X` is exact, so the double subtraction is exactly 0) or ≥ (v−1)/v ≈ 1. The rounding error of `i*X`
  is ≤ ~2 ulp of 9·v ≈ 1e-6 at v = 5e8. **The argument of sqrt cannot go negative; no NaN.** ✓
- v ≥ 2 so `v-1 ≥ 1`; no division by zero. ✓ (Before `c217f20`, v = 1 gave 0/0 — F12/#264.)

### 2.4 Step 6 — :67-69

```c
X -= ZALPHA * s/sqrt(v);                                 // :67   lower bound, correct direction  ✓
//2 is the smallest meaninful value here.
if(X < 2.0) X = 2.0;                                     // :69   the D-2 clamp
```

- `ZALPHA` is `2.5758293035489008` (`utils.h:75`), the binary64 value of the 0.995 quantile; the spec prints
  `2.576`. **DOCUMENTED DIVERGENCE D-1 (and the C22c family).** Direction: PERMISSIVE — the code subtracts
  less, X̄′ is higher, p is lower, entropy is higher. Magnitude, measured in `logs/analysis-collision-algebra.log`
  on the spec's own example: 0.44838478567480144 (ZALPHA) vs 0.44833958779109057 (2.576) = **+4.5e-5 bit at
  v = 14**. At v ≈ 4e5 (1M bits, p ≈ 0.53) it is ~3e-6 bit; but dp/dX̄′ = −¼/sqrt(1.25 − 0.5X̄′) diverges as
  X̄′ → 2.5, which is why the fork's floor oracle carries a Collision-family C22c ceiling of **7.84e-4 bit at
  n = 1e6 and 4.66e-4 at n = 8e6** (`audits/2026-10-11-independent-audit/oracles/entropy_floor.py:219-221`;
  Compression's 3.36e-3 binds). Nothing to repair; already bounded.
- The clamp: **matches FORK-DIVERGENCE D-2 exactly** (`collision_test.h:69`, upstream code, unchanged). D-2's
  arithmetic is right: X̄′ < 2 → clamp → p = ½ + sqrt(1.25 − 1.0) = 1.0 → entropy 0; the literal spec fallback
  would award 1 bit. Conservative. Without the clamp, p would exceed 1 and `−log2(p)` would be NEGATIVE, which
  `min()` would then adopt — so the clamp is also what keeps the figure in [0, 1]. ✓
- When does the clamp fire? From the algebra log: for v ≥ 100 it fires iff the count of t = 3 collisions is
  **1 ≤ n₃ ≤ 6**, independent of v (n₃ = 0 gives X̄′ = 2 exactly, no clamp needed). That is a source emitting a
  differing adjacent pair at most six times in a million — MCV already reports ≈ 0 there. Reproduced on the
  binary: `corpus/collision-clamp-L3001.bin` (2998 zeros + `1,0,1`) → `X-bar = 2.0006666666666666`,
  `sigma-hat = 0.025819888974718957`, computed X̄′ = 1.99895 (my arithmetic), **printed `X-bar' = 2`**, `p = 1`,
  `min entropy = -0` (`logs/analysis-collision-probe-collision-clamp-L3001.log:14-19`).
  Note for the differential driver: the `X-bar'` label is printed AFTER the clamp (:71-72), so a reference that
  prints the unclamped value will disagree on exactly these inputs; that is not a defect.

### 2.5 Steps 7-8 — :78-86

```c
if(X < 2.5) {
    p = 0.5 + sqrt(1.25 - 0.5 * X);                      // :79   the exact root ≥ ½ of X̄′ = −2p²+2p+2 (derived in 1.1)  ✓
    entEst = -log2(p);                                   // :80
} else {                                                 // :82   X̄′ ≥ 2.5: no solution in [½,1]
    p = 0.5;  entEst = 1.0;                              // :84-85  spec's fallback "log2(2) = 1"  ✓
}
```

- No binary search: the closed form is exact to double precision and strictly more accurate than any bounded
  search. The spec's "bounds of ½ and 1" are respected: for 2 ≤ X < 2.5, `0.5*X` is exact (power-of-two scale),
  `1.25 − 0.5*X` is an exact subtraction of nearby doubles (Sterbenz) and lies in (0, 0.25], so the sqrt is in
  (0, 0.5] and **p ∈ (0.5, 1.0] always; `log2(p)` is never of zero or of a negative; entEst ∈ [0, 1).** ✓
- Boundary X̄′ = 2.5 exactly: the closed form would give p = 0.5 → 1.0, the same as the else-branch. Consistent.
- Worked example on the production binary (`logs/analysis-collision-probe-collision-spec-example-L40.log:12-19`):
  `v = 14`, `Sum t_i = 38`, `X-bar = 2.7142857142857144`, `sigma-hat = 0.46880723093849502`,
  `X-bar' = 2.3915497504223429`, `p = 0.73286288838891567`, `min entropy = 0.44838478567480233` — spec: 2.7143,
  0.4688, 2.3915, 0.7329, 0.4483. ✓ (The 4.5e-5 gap in the last figure is the ZALPHA constant, see 2.4.)
- Fallback branch on the binary: `corpus/collision-alt-L3000.bin` (0101…) → `X-bar = 3`, `sigma-hat = 0`,
  `Could Not Find p`, `p = 0.5`, `min entropy = 1`; the run's `H_original = -0` because Markov/predictors bind
  (`…probe-collision-alt-L3000.log:12-19,60`). Spec-conformant; see §5 for what this means.

### 2.6 `-0` output (LOW, neutral) — :80 and callers

When p == 1.0 exactly (X̄′ clamped to or equal to 2), `entEst = -log2(1.0)` is **−0.0**. Observed:
`Literal Collision Estimate: min entropy = -0`, `H_original = -0`, `Assessed min entropy: -0`
(`…probe-collision-pairs-L3000.log:19,60-61`; `…probe-collision-clamp-L3001.log:19,60-61`) and in JSON
`"hOriginal" : -0.0`, `"hAssessed" : -0.0` (`logs/analysis-collision-probe-clamp.json:15,59-60`). The `>= 0` fold
guard accepts −0.0 (correctly: it IS a measurement), and `test_case_base.h:52-57`'s `!= -1` writes it. Any numeric
consumer reads it as 0; a textual consumer sees a minus sign on an entropy figure. MCV (p_u = 1) and Markov produce
the same −0, so this is cross-cutting, not Collision-specific. Cosmetic; fix is `entEst = -log2(p) + 0.0` or at the
printer.

### 2.7 The callers — where the −1 goes

| caller | gate | fold guard | note |
|---|---|---|---|
| `non_iid_main.cpp:386-397` Bitstring | `(alph_size > 2) \|\| !initial_entropy` | `if (ret_min_entropy >= 0)` :391, else `tc632.bitstring_not_run = true` :396 | JSON key `bitstringEstimateNotRun` (`test_case_base.h:46-47`) |
| `non_iid_main.cpp:399-408` Literal | `initial_entropy && alph_size == 2` | `>= 0` :402, else `literal_not_run` :407 | observed `"literalEstimateNotRun" : true` in `…probe-clamp.json:30,42` for other estimators |
| `restart_main.cpp:896-907` rows/cols | `!iid && alph_size == 2` :881-883 | `>= 0` on both folds (R-2, `d892b90`) | comment at :892-895 explains why |
| **`conditioning_main.cpp:388-389`** Bitstring | none (non-IID path, §3.1.5.2 says bitstring) | **NONE** — `h_bitstring = min(ret_min_entropy, h_bitstring);` | **a −1 return becomes h' = −1** (§3) |

Aggregation (`non_iid_main.cpp:633-641`): `h_assessed = min(word_size, H_bitstring*word_size [if bitstring ran],
H_original [if -i])`. Collision's value enters H_bitstring (≤ 1, ×word_size ≤ word_size) or H_original (≤ 1 per
symbol, and only when the alphabet has two values). Both are per the §3.1.3 text (PDF p. 20): "the entropy per
sample is estimated to be n×Hbitstring … HI = min (Horiginal, n×Hbitstring, Hsubmitter) for non-binary sources
and as HI = min (Horiginal, Hsubmitter) for binary sources."

`-t` (`non_iid_main.cpp:344`, `data.blen = MIN_SIZE`) truncates the bitstring to 1,000,000 bits — permitted by
§3.1.3: "The bits after the first 1 000 000 bits may be ignored." Default is all bits (`-a` semantics).

`bsymbols` is built at `utils.h:519-537` from `dp->symbols` BEFORE the map-down at :540-542, i.e. from the masked
but UN-translated values, MSB-first within each symbol — so the bitstring Collision sees the raw bit patterns, as the
comment at :519 says. ✓ (Bit order within a symbol is not specified by the standard; MSB-first is a choice.)

### 2.8 Things the task asked me to look for, with the line that settles each

| concern | verdict | lines |
|---|---|---|
| direction of the confidence bound | lower bound, minus sign, correct | :67 |
| binary-search direction/tolerance/termination | replaced by an exact closed form on the correct root; bounds honoured | :78-86, derivation 1.1 |
| log of zero | impossible: p ∈ (0.5, 1] | :79-80 |
| division by small counts | v ≥ 2 enforced; v−1 ≥ 1 | :47, :54, :56 |
| NaN/inf propagation into `min()` | no NaN source remains; a −1 is filtered by `>= 0` in ea_non_iid / ea_restart, **not in ea_conditioning** | :56 analysis; callers table |
| int vs size_t / overflow at 1e6..1e9 | `long` counters, double Σt² exact to 2^53; LLP64 is an intake (C18-class) matter | :18-19, :34-35 |
| off-by-one in the scan | three tail cases verified; worked example Σt = 38 of 40 reproduced | :28-31 |
| minimum legal sample count | at L ≥ 1,000,000, v ≥ 333,333 — the decline path is unreachable on a compliant run | :47 |
| 1-bit vs 8-bit paths | 1-bit: Literal only (alph_size == 2). 8-bit: Bitstring (×8) unless the alphabet has exactly two values (F01, withdrawn/documented) | `non_iid_main.cpp:386,399,636,640` |
| skipped estimator and what `min()` sees | skip is recorded in JSON (`*EstimateNotRun`) and cannot happen at ≥ 1M samples; in ea_conditioning the skip is NOT filtered | callers table |

---

## 3. Prior repairs touching this component, and how I tried to break them

### 3.1 `c217f20` — F12 / upstream #264: `v < 2` guard and the `>= 0` fold in `non_iid_main.cpp`

Record: NOTICE 2026-09-30 ("the collision estimate requires at least two collisions instead of dividing by
v-1 = 0, and its result is guarded in the combination logic the way every other fallible estimator already was");
tracker F12 ("This also required guarding its result in non_iid_main.cpp: it was the one fallible estimator whose
value was folded into the minimum unconditionally"). Regression: `regression-estimator-guards.sh:147-164`.

Break attempts:
1. **Different caller — BROKEN.** The guard was added to `non_iid_main.cpp` (c217f20) and `restart_main.cpp`
   (R-2, d892b90: "The two collision folds are guarded as well, since collision_test became fallible in c217f20"),
   but `conditioning_main.cpp:388-389` was never touched (`git diff unrepaired-reference-2026-10-15 HEAD --stat --
   cpp/conditioning_main.cpp` is empty). Reproduced: `OMP_NUM_THREADS=2 cpp/ea_conditioning -n -i
   corpus/collision-v1-L5.bin 8 8 8 1.0` → `*** Warning: not enough collisions … found 1 ***`, `h' = -1`,
   `h' * n_out = -8`, `(Non-vetted) h_out = -8`, **exit 0**. Negative control: same command on
   `corpus/collision-spec-example-L40.bin` → `h' = 0.08779849548710680351426`, `h_out = 0.7023879638968544281141`,
   exit 0 (`logs/analysis-collision-conditioning-probe.log`). Direction: UNDERSTATES (a negative entropy figure
   with a success exit code). Reachability: the bitstring must have ≤ 5 bits — a truncated or empty conditioned
   file — and ea_conditioning has NO §3.1.1 minimum (`dataset_meets_minimum` is called only from
   `iid_main.cpp:320` and `non_iid_main.cpp:320`), so no escape variable was needed. The tracker marks
   ea_conditioning "outside supported scope under 876ba05" (F-row at tracker:841) and it is outside the brief's
   target profile. Rule-12 pair: c217f20 × d892b90 × 876ba05.
2. Width: on the 8-bit Bitstring path blen ≥ 8 for one byte, so v ≥ 2 always — unreachable. ✓
3. `-l index,count` with count ≤ 5: `read_file_subset` → `dataset_meets_minimum` refuses without the escape. ✓
4. Return-value shapes that slip the `>= 0` guard: −0.0 passes (correct — it is a real 0); NaN fails the
   comparison and would be treated as declined, but no NaN source remains (2.3). ✓
5. **Test-coverage gap (LOW):** the #264 arm asserts only that b5.bin DECLINES; it has no positive control that
   the estimator RUNS at v = 2 (rule 7's "baseline asserted accepted" shape; the #263 compression arm does have
   one). A guard mutated to `if (v < 2000000)` would pass this arm and silently drop Collision from every
   `min()`. Mitigation that exists: `pin-check.sh` is in `run-all-checks.sh:199` and pins the collision-binding
   ringOsc figure (0.126) at 1e-9 relative — that WOULD catch an always-declining guard. Suggest adding a 6- or
   7-sample positive control to the arm anyway so the arm is self-sufficient.

### 3.2 `d892b90` — R-2: `>= 0` guards on the restart folds

Verified present at `restart_main.cpp:897,903`. Gate `alph_size == 2` at :883 (rows and columns are permutations
of the same symbols, so binary is preserved). On a 1000×1000 restart matrix v ≥ 333,333; cannot decline. ✓

### 3.3 D-2 clamp — not a repair (upstream code, unchanged)

Code at :69 matches the D-2 text and arithmetic exactly; conservative; reproduced (2.4). Nothing to break.

### 3.4 D-1 / C22c — ZALPHA — not a repair

Collision uses it at :67. Permissive by ≤ 7.84e-4 bit at n = 1e6 (floor oracle's Collision-family ceiling), and
that family does not bind (Compression does). Documented; nothing to break. One check worth keeping: the floor's
Collision term is computed from a solve; the ceiling as X̄′ → 2.5 is singular, so any future change to how that
term is derived needs the `dp/dX̄′ = −¼/sqrt(1.25 − 0.5X̄′)` sensitivity stated.

---

## 4. Edge-case inputs that separate a correct from an incorrect implementation

Direction column says what a WRONG implementation would do relative to the correct figure.

| # | construction (exact) | correct result (this component) | what a wrong implementation does | wrong direction |
|---|---|---|---|---|
| E1 | spec worked example: `corpus/collision-spec-example-L40.bin` (40 bytes, p. 51 sequence) | v=14, Σt=38, X̄=2.7142857142857144, p=0.73286288838891567, H=0.44838478567480233 (reproduced) | any scan/formula error moves v, Σt or H | either — positive control |
| E2 | `0011` repeated, L = 1,000,000 (or `corpus/collision-pairs-L3000.bin`) | all t=2, σ̂=0, X̄′=2, p=1, **H=0** (reproduced at L=3000: `…probe-collision-pairs-L3000.log`) | an implementation applying the spec's fallback at X̄′ ≤ 2 (or whose binary search "fails" at the boundary) reports **1.0** | **OVERSTATES by 1 bit/bit** |
| E3 | 999,996 zeros + `0,1,0,x`, L = 1,000,000 (n₃ = 1; template `corpus/collision-clamp-L3001.bin`) | X̄′ computed < 2 → clamp → H=0 (reproduced at L=3001) | literal-spec fallback → **1.0**; an implementation without the clamp → **negative** H | **OVERSTATES** / nonsense |
| E4 | alternating `01`, L = 1,000,000 (`corpus/collision-alt-L3000.bin` template) | X̄′=3 → fallback **H=1.0** exactly; overall min must be ≈ 0 from Markov/predictors | an implementation that errors on the complex root (NaN) or clamps X̄′ down to 2.5 and reports 1−ε; or one that lets NaN into `min()` and drops Collision | NaN-into-min → **OVERSTATES** |
| E5 | X̄′ just below 2.5: choose v = 400,000, n₃ such that f − Z·sqrt(f(1−f)/(v−1)) = 0.5 − 10⁻⁹; emit `00` for each t=2 and `010` for each t=3 (order irrelevant to the statistic) | p = 0.5 + sqrt(5e-10) ≈ 0.5000224, H ≈ 0.99994 | a binary search with tolerance 1e-6 in X̄′ lands ~7e-4 away in p (singular slope) → ~2e-3 bit either way; a search that declares "no solution" within tolerance of 2.5 → 1.0 | either; shows where search tolerance matters |
| E6 | v = 1 (`corpus/collision-v1-L5.bin`) and v = 0 (`00`→ no: use `01`, L=2) | declines; JSON `literalEstimateNotRun: true`; final min from the other estimators (reproduced for L=5) | pre-c217f20: σ̂ = NaN → "Could Not Find p" → **1.0** unmeasured | **OVERSTATES** (estimator-level) |
| E7 | tail off-by-one trio at L = 1,000,001 / 1,000,002 / 1,000,003 on an otherwise fixed random prefix, tails `0`, `01`, `010` | Σt and v differ by exactly 0, 0, +3/+1 between the three | an implementation that counts a partial tail, or reads `data[len]` | either; memory-safety probe under ASan |
| E8 | 8-bit file with exactly two byte values {0x00, 0xFF}, L = 1,000,000, declared `8` | alph_size == 2 → Literal Collision on translated data, no Bitstring; H_original ≤ 1 bit per 8-bit symbol | an implementation gating on word_size runs Bitstring Collision ×8 on `00000000/11111111` runs → **≈ 0** from runs, but MCV… (F01 territory: withdrawn, documented) | documented |
| E9 | 8-bit random bytes, L = 2,000,000, with `-t` vs `-a` | `-t`: Collision on first 1,000,000 bits; `-a`: on all 16,000,000 | a reference that ignores the flag disagrees on v, Σt | neither — driver must honour the flag |
| E10 | −0 sanity: E2 through `-o` JSON | `"hOriginal" : -0.0` (observed) | a consumer that rejects or mis-sorts `-0.0` | neutral |

Expected (benign) differential disagreements the driver must tolerate on this component: σ̂ last digits (one-pass
`:56` vs two-pass spec formula — observed 0.46880723093849502 vs 0.46880723093849541); `X-bar'` printed post-clamp
on E2/E3; F exact vs truncated continued fraction (G.1.1); ZALPHA vs 2.576 (D-1, ≤ 7.84e-4 bit); any binary-search
tolerance near X̄′ → 2.5 (E5).

---

## 5. What is NOT a code defect but matters for the entropy claim

- **The spec's fallback is a full bit for anti-correlated data.** For any source whose adjacent bits differ more
  than half the time (X̄′ > 2.5), §6.3.2 step 8 says "min-entropy = log2(2) = 1" and the code does exactly that
  (E4 reproduced). In isolation that OVERSTATES — `0101…` has zero entropy — and the assessment relies on the
  other nine estimators to bind. They do (E4's overall `H_original = -0`). This is a property of the standard,
  in the same family as D-3, and belongs in the limitations section, not FINDINGS.
- **Collision is decorative on this project's data.** Per the campaign's aggregation measurement, Compression
  binds on every stream assessed; the Collision C22c family is 4.3× below Compression's at n = 1e6. A Collision
  defect would have to be large to move the published figure — which is also why E2/E3 (where Collision IS the
  honest minimum among the entropic statistics) are the fixtures worth keeping.

## 6. Candidate findings for the orchestrator (severity per the brief's table)

1. **MEDIUM, understates, REPRODUCED** — `cpp/conditioning_main.cpp:388-389`: `collision_test()`'s −1 decline is
   folded into `h'` unguarded; `h' = -1`, `h_out = -8`, exit 0. Spec: §6.3.2 step 5 needs v ≥ 2 (the guard is
   right) and §3.1.5.2 defines h′ as an entropy estimate per bit in [0, 1]. Reproducer and negative control:
   `logs/analysis-collision-conditioning-probe.log`, binary sha256 `b7a55528…`. Outside the target profile
   (ea_conditioning, "outside supported scope"); rule-12 pair c217f20 × d892b90 × 876ba05. Fix shape: the same
   `if (ret_min_entropy >= 0)` the other two programs use (markov_test at :392 is not fallible; compression at
   :396 is already guarded).
2. **LOW/MEDIUM, unknown direction, SUSPICION (reproduced as a fact, not as a wrong figure)** — ea_conditioning
   `-i` applies no §3.1.1 minimum (`dataset_meets_minimum` has two callers, neither in conditioning_main.cpp), so
   a 5-sample conditioned dataset is assessed with no non-compliance mark. Spec §3.1.1 (PDF p. 18): "a conditioned
   sequential dataset of at least 1 000 000 consecutive conditioning component outputs". Out of target profile.
3. **LOW, neutral, REPRODUCED** — `-0` printed and serialised for a zero estimate (`collision_test.h:80`, also MCV
   and Markov). Cosmetic.
4. **LOW, test gap** — `regression-estimator-guards.sh` #264 arm has no positive control that Collision runs at
   v = 2; mitigated by `pin-check.sh` in `run-all-checks.sh:199`.
5. **DOCUMENTED DIVERGENCE** — ZALPHA at `:67` (D-1 / C22c family, permissive ≤ 7.84e-4 bit at n = 1e6, bounded by
   the floor); the clamp at `:69` (D-2, conservative, code matches the text). Report in limitations only.

No CRITICAL or HIGH candidate was found inside `collision_test()`; every path was walked with line numbers above.
