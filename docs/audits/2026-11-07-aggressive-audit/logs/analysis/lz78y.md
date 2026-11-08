# LZ78Y prediction estimate (SP 800-90B §6.3.10) — analysis-phase reading

Date 2026-11-07. Branch `audit/2026-11-07`. Analysis phase: no builds, no run over
20,000 samples. Every production run below used `EA_ALLOW_SHORT_DATASET=1` and
`OMP_NUM_THREADS=2` and is therefore NON-COMPLIANT by construction (brief rule 5).
Binary: `cpp/ea_non_iid` sha256
`1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`
(`logs/analysis-lz78y-binary.sha256`). Platform: Darwin arm64, Apple clang;
`long double` is `double` here.

Files read in full: `cpp/non_iid/lz78y_test.h` (210 lines),
`cpp/shared/utils.h` lines 1–200 and 1083–1336 (`relEpsilonEqual`,
`prediction_estimate_function`, `calc_p_local`, `predictionEstimate`,
`BINARYDICTLOC`, `compressedBitSymbols`, `PostfixDictionary`), `read_file`
(utils.h 549–740, for what `symbols`/`bsymbols`/`alph_size` are when they reach
the estimator), the LZ78Y call sites in `cpp/non_iid_main.cpp` 604–636 and
`cpp/restart_main.cpp` 1069–1088, and the option parsing at `non_iid_main.cpp`
161–180. Documented divergences read first: `FORK-DIVERGENCE-AND-TRUST.md` A, B, D;
`NOTICE`; `audits/2026-09-30/FINDINGS-TRACKER.md` (F08, F13, F15, F24, F25);
`cpp/selftest/regression-estimator-guards.sh`.

Headline: **I found no departure from §6.3.10 in either implementation, and no
path by which this estimator reports more min-entropy than the spec's algorithm
would.** The three places where the code's numbers differ from the printed text
are all documented already (D-1 ZALPHA; F08 recurrence-to-convergence; C22
bisection quantisation) and I re-measured the first two below. One suspicion
about a shared-helper `assert` was raised, emulated and probed, and **did not
reproduce** on this host; it is recorded as a suspicion with the x86-64 format
untested. Everything is labelled.

---

## 1. The spec's algorithm, step by step

All quotes from `reference/sp800-90b.pages.txt`, SP 800-90B §6.3.10, PDF pp. 63–65.

**Setup** (PDF p. 63): "Given the input S = (s1, …, sL), where si ϵ A = {x1, …, xk},"

**Step 1** (p. 63): "Let B = 16, and N = L – B – 1. Let correct be an array of N
Boolean values, each initialized to 0. Let maxDictionarySize = 65 536."
→ constants B = 16, cap 65,536; N = L − 17; a Null prediction leaves correct = 0.

**Step 2** (p. 63): "Let D be an empty dictionary. Let dictionarySize = 0."
→ ONE counter across all prefix lengths; it counts PREFIXES (keys of D), not
(prefix, postfix) pairs.

**Step 3** (p. 63–64): "For i = B+2 to L:"
- **3.a** "For j=B down to 1:
  i. If (si-j-1, …, si-2) is not in D, and dictionarySize < maxDictionarySize:
     1. Let D[si-j-1, …, si-2] be added to the dictionary.
     2. Let D[si-j-1, …, si-2][si-1] = 0.
     3. dictionarySize = dictionarySize + 1
  ii. If (si-j-1, … , si-2) is in D,
     1. Let D[si-j-1, …, si-2][si-1] = D[si-j-1, … ,si-2][si-1] + 1."
  Reading matters here: (i) then (ii) are SEQUENTIAL, not if/else, so a newly
  added prefix nets count 1 for the postfix s_{i-1}. **Verified against the
  spec's own worked example** (Probe A below): the sequential reading reproduces
  `correct = (0,0,1,1,0,1,1,0)`; the exclusive reading gives `(0,0,0,0,0,0,1,0)`.
  Adds happen in order j = B … 1, and the cap is tested before each add.
- **3.b** (p. 64): "Use the dictionary to predict the next value, si. Let
  prediction = Null, and let maxcount = 0. For j = B down to 1:
  i. Let prev = (si−j, … si−1).
  ii. If prev is in the dictionary, find the y ϵ {x1, …,xk} that has the highest
  D[prev][y] value. In the event of a tie, let the y be the symbol with the higher
  byte value. For example, if D[prev][1] and D[prev][5] both have the highest
  value, then y = 5.
  iii. If D[prev][y] > maxcount: 1. prediction = y. 2. maxcount = D[prev][y]."
  → strict `>`, so with j descending the LONGEST prefix wins a tie on maxcount;
  within a prefix, ties go to the HIGHER symbol value.
- **3.c** (p. 64): "If (prediction = si), let correcti−B−1 = 1." → Null never
  matches; `correct` index i−B−1 runs 1..N.

**Step 4** (p. 64): "Calculate the predictor's global performance as
P_global = C/N. The upper bound of the 99 % confidence interval on P_global,
denoted P'_global is calculated as:
  1 − 0.01^(1/N),                                   if P_global = 0,
  min(1, P_global + 2.576 √(P_global(1−P_global)/(N−1))),  otherwise
where 2.576 corresponds to the Z(1−0.005) value." → UPPER bound; direction is
conservative (higher P' → lower entropy).

**Step 5** (p. 64): "Let r be one greater than the length of the longest run of
ones in correct. Use a binary search to solve the following for P_local:
  0.99 = (1 − P_local x)/((r + 1 − r x) q) × 1/x^(N+1),
where q = 1 − P_local and x = x10, derived by iterating the recurrence relation
  x_j = 1 + q P_local^r x_{j−1}^(r+1)
for j from 1 to 10, and x0 = 1. Note that solving for P_local using the logarithm
of these equations is robust against overflows." → x is the TENTH iterate, not
the fixed point (the code differs: F08, re-measured in Probe B). No bracket or
tolerance is specified for the binary search.

**Step 6** (p. 64–65): "The min-entropy is the negative logarithm of the greater
performance metric: min-entropy = −log2(max(P'_global, P_local, 1/k))."

**Worked example** (p. 65): S = (2,1,3,2,1,3,1,3,1,2,1,3,2), L = 13, B = 4,
N = 8; "correct = (0, 0, 1, 1, 0, 1, 1, 0). Then, P_global = 0.5, P'_global =
0.9868, P_local = 0.1229, and the resulting min-entropy estimate is 0.0191."
Note P_local (0.1229) < P'_global (0.9868) in the spec's own example, i.e. the
`max` in step 6 is decided by P'_global; an implementation may legitimately skip
solving for P_local once it can show P_local ≤ P'_global.

---

## 2. Map to the C++ — step by step, with the lines that make it right

Two implementations: `binaryLZ78YPredictionEstimate` (`lz78y_test.h:7–125`,
taken when `alph_size == 2`, line 133) and the generic `LZ78Y_test`
(`lz78y_test.h:128–210`). Both end in `predictionEstimate` (`utils.h:1200–1256`).

### 2.1 Constants, N, guards

| spec | code |
|---|---|
| B = 16 | `#define B_len 16` (`lz78y_test.h:4`); `assert(B_len < 32)` :17 |
| cap 65 536 | `#define MAX_DICTIONARY_SIZE 65536` :5 |
| N = L − B − 1 | generic `N = len-B_len-1` :142; binary passes `L-B_len-1` at :124 |
| i = B+2 … L (1-indexed) | both loops `for(i=B_len+1; i<L; i++)` (:54, :158), 0-indexed: predicts S[17]..S[L−1] = s_18..s_L, i.e. L−17 = N predictions |

Guards (prior repair #261, commit 21b0a31): binary `if(L < B_len + 3) return -1.0`
(:28–31, needs L ≥ 19 so N ≥ 2); generic `if(len < B_len+2) return -1.0` (:137–140,
L ≥ 18, N ≥ 1). The caller folds the result only `if (ret_min_entropy >= 0)`
(`non_iid_main.cpp:606, 616`), so a decline never reaches the min. Both are far
below the 1,000,000 intake (`MIN_SIZE`, `utils.h:42`).

### 2.2 Step 2/3.a — dictionary, cap, counting

Generic: `array<map<array<uint8_t,B_len>, PostfixDictionary>, B_len> D` (:135) —
one map per prefix length, keys zero-padded (`memset`/`memcpy` :170–171), so
lengths cannot collide. `int dict_size` (:129, :148) is the single shared counter,
compared `dict_size < MAX_DICTIONARY_SIZE` (:192) before an add (:196–197) and
incremented per PREFIX, matching "dictionarySize" (prefixes, not pairs). An
existing prefix is always incremented, with a new postfix allowed
(`incrementPostfix(data[i], true)` :191; `PostfixDictionary::incrementPostfix`
`utils.h:1311–1335` creates the postfix with count 1 when `makeNew`). A new prefix
is created with the postfix count 1 (:196) — the SEQUENTIAL reading of 3.a.i/ii,
which the worked example requires.

Binary: `binaryDict[j] = new long[1U<<(j+2)]` (:38) — for prefix length d = j+1
that is 2^(d+1) longs, and `BINARYDICTLOC(d,b)` (`utils.h:1263`) indexes
`((b & ((1U<<d)-1)) << 1)` ≤ 2^(d+1) − 2, plus `[0|1]`, so the maximum offset is
2^(d+1) − 1: in bounds. "Present in D" ≡ `curCount != 0` (:86–90), exact because an
entry is only ever created with count 1 (:48, :104) and counts never decrease.
`long dictElems` is the shared prefix counter (:49, :105), checked at :101.

**Ordering equivalence (this is the subtle part).** The spec performs, at step i,
all B updates of the prefixes ending at s_{i−2} (postfix s_{i−1}) BEFORE the B
lookups of the prefixes ending at s_{i−1}. The code, at 0-indexed iteration i
(predicting S[i] = s_{i+1}), looks up prefix (S[i−j..i−1]) and then updates THAT
prefix with postfix S[i] (:183 then :191; :78–98 then :100/:104). That update is
exactly the spec's step-(i+2) update of (s_{i+1−j}..s_i) → s_{i+1}, done one step
early — after this step's lookups and before the next step's. Within a step, the
update of length j touches only D[length j], which no other j reads in that step,
and the shared counter advances in the same j = B..1 order as the spec's adds. The
dictionary state at every prediction is therefore identical to the spec's. The
init loop (:44–50, :151–155) performs the spec's first-step adds
(s_{17−j}..s_16) → s_17 for j = 1..16 (order irrelevant: 16 ≪ 65,536). The last
iteration also performs a never-consumed update — harmless.

### 2.3 Step 3.b — prediction and ties

Generic: `y = (curp->second).predict(count)` (:183) returns the running argmax
maintained in `incrementPostfix`: `if((curCount > curBest) || ((curCount ==
curBest) && (in > curPrediction)))` (`utils.h:1329`). Because counts only
increase, a running maximum with "tie → higher symbol" is exactly the spec's
argmax with its tie rule at every moment. Across j: `if(count > max_count)` (:185),
strict, j descending (:164) → longest prefix wins ties. The symbols compared are
the mapped-down ones (`read_file`, `utils.h:716–740`), and the map-down is
order-preserving (indices assigned in increasing raw value, :704–706), so "higher
byte value" is preserved. Binary: `if(dict[0] > dict[1]) predict 0 else predict 1`
(:78–84) — a tie predicts 1, the higher value; `if(curCount > maxCount)` (:94)
strict, j descending (:65).

### 2.4 Step 3.c — correct and runs

Generic :202–206, binary :110–116: `if(have_prediction && prediction == data[i])
{ C++; run++ } else run = 0`. A Null prediction resets the run, as the spec's
`correct = 0` implies — the LZ78Y code does NOT have the MultiMMC D-4 quirk.

### 2.5 Steps 4–6 — `predictionEstimate` (`utils.h:1200–1256`)

- P_global = C/N as doubles (:1209). `if(p_global > 0) p' = min(1.0, p + ZALPHA*
  sqrt(p(1-p)/(N-1))); else p' = 1 - pow(0.01, 1/N)` (:1229–1230). ZALPHA =
  2.5758293035489008 (`utils.h:75`), not the printed 2.576 — **documented
  divergence D-1** (permissive by ≤ ~4e-6 bit at N = 10^6 per the record).
  `min(1.0, NaN)` ordering is the F13 fail-closed point (comment :1211–1228);
  measured below at N = 1.
- `curMax = fmax(1/k, p')` (:1207, :1232); `if((curMax < 1.0) &&
  (prediction_estimate_function(curMax, r, N) > log(0.99)))` then
  `p_local = calc_p_local(max_run_len, N, curMax); curMax = fmax(curMax, p_local)`
  (:1233–1236). The skip is valid iff f(p) is decreasing in p: then f(curMax) ≤
  ln 0.99 ⇒ root ≤ curMax ⇒ the `max` is unchanged. **Probe C**: 64,262 grid
  points, 0 violations (evidence about the rows sampled, rule 6).
- `entEst = -log2(curMax)` (:1238). k is `alph_size` for the literal path (the
  OBSERVED alphabet after map-down) and 2 for the bitstring path — conservative
  relative to 2^word_size.
- `prediction_estimate_function` (:1087–1108): `q = 1-p; x = 1;` iterate
  `x = 1 + q·powl(p,r)·powl(x,r+1)` while `(i <= 65) && ((x - xlast) >
  LDBL_EPSILON*x)` (:1099–1101) — TO CONVERGENCE (≤ 66 steps), not x_10 —
  **F08, NOT-A-BUG in the tracker**; re-measured in Probe B: converged form is the
  permissive side but by ≤ 9e-49 bit at N = 9,983 and identical to 60 digits at
  N ≈ 10^6. Returns `logl(1-px) - logl((r+1-rx)q) - (N+1)logl(x)` (:1108), the
  log form the spec recommends. Asserts: `p > 0`, `p < 1` (:1089–1090; satisfied
  since 1/k ≤ curMax < 1 is checked), `x >= xlast` (:1103), `p*x <= 1.0L`
  (:1105) — see §2.7.
- `calc_p_local` (:1111–1197): bisection on [curMax, 1] (:1124–1125) for
  f(p) = ln 0.99 (:1120). Direction `if(log_alpha < pVal) lbound = p else hbound
  = p` (:1142–1148) is right for decreasing f. Termination: `relEpsilonEqual(pVal,
  log_alpha, DBL_MIN, DBL_EPSILON, 4 ULP)` (:1139) or bracket collapse (:1152), or
  ITERMAX = 1076 (`utils.h:74`) ≥ the halvings of [0,1] in binary64. Every
  invariant exit returns `hbound` or `hdomain = 1.0` (:1158–1194), i.e. a value AT
  OR ABOVE the root → lower entropy, fail-closed. The residual quantisation is the
  documented C22 floor term.

### 2.6 What the caller does with it

`non_iid_main.cpp:604–636`: bitstring run gated `(alph_size > 2) || !initial_entropy`
(the F01-withdrawn gate, documented), literal run gated `initial_entropy`;
`H_bitstring = min(ret, H_bitstring)`, `H_original = min(ret, H_original)` only when
`ret >= 0`. `restart_main.cpp:1075, 1082` runs the same function on the row- and
column-ordered 1,000,000 samples with `data.len`, `data.alph_size`. A one-symbol
alphabet is refused before any estimator (`non_iid_main.cpp:329`), so the
`prediction_estimate_function` precondition `p < 1` cannot be violated by k = 1.

### 2.7 Numerics audit items asked for in the brief

- **Bound direction**: P'_global is the upper bound (↑p → ↓H); P_local enters via
  max; all fallbacks move p up. Correct direction everywhere.
- **Bisection**: bracket [curMax, 1], lower bound is the ALREADY-binding value, so
  the only thing the search can do is raise curMax. Tolerance 4 ULP / DBL_EPSILON.
- **log of zero**: `logl(1-px)` at the fixed point x = 1/p gives −∞ (or NaN if a
  negative argument). Both compare `> log(0.99)` as false → skip, which is the
  correct decision there (the true no-run probability is ≪ 0.99). Reached in
  production by the P=4000 flips input (below): exit 0, "P_local can't change the
  result".
- **Division by small counts**: `(double)N-1.0` = 0 only at N = 1; measured (below):
  C=1 → 0/0 = NaN → `min(1.0, NaN)` = 1 → H = −0; C=0 → the P_global=0 branch →
  0.99 → H = 0.0145. Fail-closed. N = 1 is reachable only at L = 18 with the escape.
- **NaN into the final min**: impossible from this estimator: `entEst = -log2(curMax)`
  with curMax ∈ [1/k, 1] finite.
- **Integer widths**: counts, L, N, C, run lengths are `long`; `int dict_size` ≤
  65,536; `uint32_t curPattern` ≤ 2^16; shifts bounded by `B_len < 32`. On LP64 no
  overflow below 2^63. On LLP64 (Windows) `long` is 32-bit: fine up to 2^31
  samples within this file; the hazard there is `blen = len * word_size`
  (`utils.h:719`, outside this component) for len > 2^28 at width 8 — flagged for
  the intake agent, not reproduced.
- **Off-by-one**: N = L−17 predictions made (loop count); correct index implicit;
  r = max_run + 1 (:124/:209 → :1234, printed as `r` :1241/:1245).
- **Minimum legal count**: L = 18 generic (N=1), L = 19 binary (N=2): measured below.
- **1-bit vs 8-bit**: 8-bit data runs the generic path on `symbols` with k = alph_size
  and the binary path on `bsymbols` (k = 2). Two-symbol 8-bit data (e.g. {0x00,0xFF})
  dispatches the literal run to the binary path with k = 2 and SKIPS the bitstring
  run (gate `alph_size > 2`) — documented F01 withdrawal; H_original ≤ 1 then binds.
- **Degenerate estimators**: the only "skip" is a decline (−1) below 18/19 samples;
  the final min never sees it.
- **Determinism**: no OpenMP in this estimator; `std::map` iteration order unused.

---

## 3. Prior repairs touching this component, and how to break them

| repair | where | break attempts |
|---|---|---|
| #261 / F15 (21b0a31): asserts → decline | `lz78y_test.h:28–31`, `:137–140`; regression `regression-estimator-guards.sh:222–224` (b17/b18/b19 at width 1 only) | (a) generic boundary at width 8: L=17 three-symbol → declines, L=18 → runs with N=1 (MEASURED, see §5; fail-closed both arms). The regression script has NO width-8 L=17/18 case — add one. (b) 8-bit TWO-symbol data at L=18 dispatches to the binary path, which needs 19: the warning says "need at least 19" while the user supplied 8-bit data — check the message is not misleading. (c) `ea_non_iid -n -i` (conditioning path) never calls `dataset_meets_minimum` (COVERAGE.md item 3): a conditioned output of 17–18 bits reaches these guards without the escape variable; run it. (d) `ea_restart` passes `data.len`, so the guards are unreachable there (1,000,000 rows×cols) — confirm nothing passes a per-row length. (e) Mutate `B_len + 3` → `B_len + 2` in a scratch copy, build out of tree, run b18.bin: the regression must catch it (rule 7). |
| F13 (OC-58) `min(1.0, NaN)` ordering | `utils.h:1229` | Measured at the real boundary: N=1, C=1 → P'=1 → H=−0. Break: a build with `-ffast-math` (`-ffinite-math-only`) makes NaN comparisons undefined; the Makefile does not pass it — assert in `regression-docs.sh` or BUILD-LINES that it never does. |
| F08 NOT-A-BUG (x to convergence) | `utils.h:1099` | Quantified: permissive by ≤ 9e-49 bit at N=9,983, 0 at 60 digits for N ≈ 10^6 (Probe B). Cannot bind. At N=2, r=1, p=0.5 the recurrence is parabolic (5,001 iterations to 2^-63; cap 66) — the sign is still right (f ≪ ln 0.99). |
| D-1 ZALPHA | `utils.h:75` | Documented permissive constant; the instance on LZ78Y at N=7,999,983 is in the record (p_local_exact.py §4). Not re-measured. |
| C22 bisection quantisation | `utils.h:1139` | Covered by the floor; every early exit is ≥ root (read :1152–1194). |
| OC-104 option-order refusal | caller | my probes put every option before the operand; a probe with `1 -v` after the file would be refused by design. |

---

## 4. Edge-case inputs that separate a right from a wrong implementation

Ranked by "a wrong implementation reports HIGHER entropy" first.

1. **Spec worked example at B = 4** — S = (2,1,3,2,1,3,1,3,1,2,1,3,2), width 2.
   Correct: `correct = (0,0,1,1,0,1,1,0)`, C=4, N=8, r=3, P'=0.9868, H=0.0191.
   The EXCLUSIVE reading of 3.a.i/ii gives C=1 → P' ≈ 0.78 → H ≈ 0.36: an
   implementation with the wrong reading OVERSTATES. Needs a B-parameterised
   out-of-tree build (sed `B_len 16` → `4` in a scratch copy; `#define` has no
   `#ifndef`). The C++ at B=16 cannot be compared to the example directly.
2. **Dictionary-cap regime at width 8 within 20,000 samples** — seed-fixed random
   bytes: 16 new prefixes per step fill 65,536 after ≈ 4,100 samples. Append a
   periodic tail (period 100, 4,000 bytes) AFTER saturation: its predictability
   depends on whether existing prefixes keep being incremented and new postfixes
   accepted when full. A wrong implementation that freezes counts when full
   under-predicts → HIGHER entropy; one that keeps adding prefixes (no cap)
   over-predicts → lower. Compare C, r, N with the py90b reference.
3. **Within-prefix tie → higher symbol** — width 2 data where context (3) is
   followed equally often by 1 and 2, then by 2 repeatedly; a lower-symbol or
   first-seen tie rule misses those → HIGHER entropy. Must survive the map-down
   (order-preserving, so the same winner).
4. **Across-j tie → longest prefix** — arrange D[length-1 context] and
   D[length-16 context] with equal max counts but different winners, with the
   actual symbol equal to the long-context winner; a shortest-first or `>=` rule
   flips C.
5. **Null-prediction run reset** — corrects separated by unseen contexts; the
   MultiMMC-style "carry the run across Null" quirk inflates r → larger P_local →
   LOWER entropy (conservative), still a conformance check.
6. **N = 1 and N = 2 boundaries** (MEASURED, §5): L=18 width 8 three-symbol
   (C=1: H=−0; C=0: H=0.01450); L=19 width 1 (C=1,N=2: P'=min(1, 0.5+2.5758·0.5)=1
   → −0); L=17 width 8 and L=18 width 1 decline.
7. **P_global = 0 branch** — an online adversary emitting the opposite of the
   LZ78Y prediction at every step gives C=0 → P' = 1 − 0.01^(1/N) ≈ 4.6e-6 →
   H = 1 bit at width 1. The spec gives the same (estimator limitation, F28-class);
   it checks the branch and that 1/k binds.
8. **Near-perfect predictor with isolated misses** (MEASURED, §5): period-2 bits
   with same-phase single flips every P bits. Drives P'_global above r/(r+1) so
   the guard call's recurrence converges to x = 1/p and `logl(1−px)` → −∞. At
   P=4000 the MultiMMC triple reaches a = 0.0 exactly in emulation; the binary
   prints "P_local can't change the result" and exits 0.
9. **Two-symbol 8-bit data {0x00, 0xFF}** — literal run takes the binary path with
   k=2; bitstring run skipped; H_original ≤ 1 must bind (documented gate).

---

## 5. What was measured in this phase (all non-compliant: EA_ALLOW_SHORT_DATASET=1)

Corpus hashes: `logs/analysis-lz78y-corpus-sha256.log` and the two lines printed in
`logs/analysis-lz78y-cpp-probes-driver.log`/terminal for the flips files
(P500 `35bf0d62…`, P1000 `2707d542…`, P2500 `e73c4c29…`, P4000 `f5bcfd79…`).

**Probe A — spec transcription vs worked example** (`logs/analysis/lz78y-probe.py`,
`logs/analysis-lz78y-probe-spec.log`, /usr/local/bin/python3 with mpmath 1.4.1):
sequential reading → `[0,0,1,1,0,1,1,0]` MATCHES; exclusive → `[0,0,0,0,0,0,1,0]`
does not. Steps 4–6 on that vector: P'=0.986818 (2.576) / 0.986786 (exact z),
H=0.01914/0.01919, both print as the example's 0.9868/0.0191. P_local=0.122949
is found only by solving BELOW P' (on [1e-6,1)), confirming the example's P_local
is the non-binding metric and that a "cannot change the result" skip is faithful.

**Probe B — F08** (same log): P_local(x_10) − P_local(x_∞) = 3.1e-49 at N=9,983
r=19; 0.0 (60 digits) at N=999,983 r=73, N=7,999,983 r=583; 4e-56 at N=999,983
r=534. Direction: converged form is the permissive side; magnitude: nil.

**Probe C — monotonicity of f(p)** (same log): 64,262 grid points over
N ∈ {2…8e6}, r ∈ {1…600}: 0 violations.

**Boundary runs** (`logs/analysis/lz78y-cpp-probes.sh`, logs
`analysis-lz78y-cpp-lz78y_*.log`, `-i -v -v` = verbose 3):

| input | path | printed | note |
|---|---|---|---|
| w8 L18 C1 | generic, N=1 | `C = 1, r = 2, N = 1, P_global = 1, P_global' = 1, min entropy = -0` | 0/0 → NaN → min(1.0,NaN)=1: fail-closed, as F13 states |
| w8 L18 C0 | generic, N=1 | `C = 0, r = 1, P_global' = 0.98999999999999999, min entropy = 0.014499569695115089` | P_global=0 branch: 1−0.01^1 |
| w8 L17 | generic | `*** Warning: not enough samples to run LZ78Y test (need at least 18) ***` | declines, exit 0 |
| w1 L19 | binary, N=2 | `C = 1, r = 2, N = 2, P_global = 0.5, P_global' = 1, min entropy = -0` | 0.5+2.5758·√(0.25/1) clamps to 1 |
| w1 L18 | binary | `need at least 19` | declines, exit 0 |

No abort in any run (exit 0 throughout; `analysis-lz78y-cpp-probes-driver.log`).
Note my first attempt used `-v -v -v`, which is verbose 4 and prints no estimator
lines (verbose starts at 1 at `non_iid_main.cpp:97`); the rerun used `-v -v`.
Also: a zsh word-splitting slip produced five stray logs with a space in the name;
they were deleted and the driver rewritten as a bash script.

**Near-perfect-predictor runs** (`analysis-lz78y-cpp-period2-flipP{500,1000,2500,4000}.log`):
LZ78Y literal at L=20,000 bits: P=2500 → `C = 19968, r = 2499, N = 19983,
P_global' = 0.99974841858515984, P_local can't change the result, min entropy =
0.00036300092362757469`; P=4000 → `C = 19974, r = 3999, P_global' =
0.99993624284972249, min entropy = 9.198505691028556e-05`. All exit 0.
P500/P1000 had an unflipped 2,000-bit head, so r ≈ 1983 and P' < r/(r+1) — they
did not reach the intended region (recorded, not hidden).

**Assert emulation** (`logs/analysis/lz78y-assert-emulation.py`,
`logs/analysis-lz78y-assert-emulation.log`,
`logs/analysis-lz78y-assert-emulation-printed-triples.log`): double-precision
re-implementation of `utils.h:1087–1108` at the guard call, faithful only where
`long double == double` (this host). 1,584 scenario triples + a fine sweep at
N=19,983: **0 emulated `assert` aborts**, 150 triples reach the log-domain
(a ≤ 0 → −∞/NaN → skip). On the 16 printed production triples the emulation's
curMax equals the tool's printed P' bit-for-bit wherever P' > 1/k (12/12), and the
P4000 MultiMMC triple (C=19989, r=3999, N=19998) reaches `a = 0.0` at iteration
20 — the production binary completed that run with the skip, exit 0.

---

## 6. Suspicions (not findings)

**S-1 — `assert(p*x <= 1.0L)` at `utils.h:1105` on the GUARD call.** The
2026-09-30 numerics note excluded this assert by arguing bisection points stay
below ~1 − 3.3/r; but the FIRST evaluation is `prediction_estimate_function
(curMax, …)` at `:1233`, and curMax = P'_global EXCEEDS r/(r+1) whenever a
predictor is nearly perfect with sparse isolated misses (r ≳ √N/2.576 with ~1
miss per run; r ≳ 0.028·N to converge within 66 iterations). There x → 1/p and a
one-ULP overshoot would abort the process (crash, no report; fail-closed, not an
overstatement). **Emulated: 0 aborts in 1,584 + sweep triples; 4 production runs
in the region: no abort.** The iteration approaches 1/p from below and `fl(p·x)`
rounded ≤ 1 in every case tried. UNTESTED on x86-64 80-bit `long double` (the
CI route), where the final iterates and the product round differently. Direction
if it ever fired: crash. Confidence low. How to test: run
`corpus/lz78y_w1_L20000_period2_flipP4000.bin` (and P ∈ {3000, 5000, 6000}) through
the x86-64 CI binary; and run a UBSan/assert build here.

**S-2 — a 2-symbol 8-bit input is reported through the binary path with "need at
least 19" while an 8-bit user expects 18.** Cosmetic; LOW; neutral. Not probed.

**S-3 — LLP64 `blen = len * word_size` overflow** (`utils.h:719`) for > 2^28
8-bit samples on Windows — outside this component; passes a negative/garbage
`blen` into `LZ78Y_test(bsymbols, blen, 2…)`. Not reproduced; flagged to intake.

**Reporting difference, not numeric (LOW, neutral):** when P_local ≤ P'_global the
tool prints "P_local can't change the result" and the JSON carries no P_local,
whereas the spec's own worked example reports P_local = 0.1229 in that situation.
A differential driver must treat a missing P_local as "≤ P'", not as a mismatch.

---

## 7. Documented divergences encountered (not reported as bugs)

D-1 (ZALPHA, `utils.h:75`); F08 (recurrence to convergence, `utils.h:1099`,
re-measured: ≤ 1e-48 bit); C22 (bisection quantisation, `utils.h:1139`); F13
(`min(1.0, NaN)` ordering, measured fail-closed at N=1); the F01-withdrawn
`alph_size > 2` bitstring gate (`non_iid_main.cpp:605`); the ≥ 1,000,000 intake;
#261 decline guards.

## 8. What this analysis does not establish

- Bit-identity of the binary and generic implementations on the same data (the
  2026-09-30 report says identical C, r on 7 inputs; not re-run here — needs an
  out-of-tree build with the `alph_size==2` dispatch disabled).
- Anything about 80-bit `long double` arithmetic in `prediction_estimate_function`.
- The spec reading of 3.a.i/ii in the C++ at B = 16 against an independent
  reference at the cap (py90b LZ78Y module was not yet present under `reference/`).
- Probe C's monotonicity is a sampled property, not a proof.
