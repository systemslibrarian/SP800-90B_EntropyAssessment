# MultiMMC prediction estimate (SP 800-90B §6.3.9) — analysis-phase record

Audit: 2026-11-07 aggressive audit, branch `audit/2026-11-07`. Analysis only: no build, no run
over 20,000 samples. One tiny probe (9 samples, `EA_ALLOW_SHORT_DATASET=1`, `OMP_NUM_THREADS=2`),
recorded below with the binary's sha256; the run is NON-COMPLIANT by construction and is used only
to check the standard's own worked example.

Files read in full: `cpp/non_iid/multi_mmc_test.h` (290 lines), `cpp/shared/utils.h` lines 1–140
(constants, `relEpsilonEqual`), 496–548 (symbol translation), 1087–1336 (`prediction_estimate_function`,
`calc_p_local`, `predictionEstimate`, `BINARYDICTLOC`, `PostfixDictionary`); the call sites in
`cpp/non_iid_main.cpp:576-599`, `cpp/restart_main.cpp:1049-1066`, `cpp/conditioning_main.cpp:426-430`;
`cpp/selftest/regression-multimmc.sh`; `FORK-DIVERGENCE-AND-TRUST.md` (C01/F10, D-1, D-4);
`NOTICE` (F09, #257 entries); `audits/2026-09-30/FINDINGS-TRACKER.md` (F09, F10, F16);
`audits/2026-09-30/novel-findings/agent-reports/noniid-estimators.md` (F09/F10 mechanism);
`audits/2026-10-11-independent-audit/COVERAGE.md` predictors row, `oracles/entropy_floor.py` C01 term.
Spec text: `reference/sp800-90b.pages.txt`, PDF pages 60–63.

Production binary measured: `cpp/ea_non_iid` sha256
`1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` (instrument rule 4).

---

## 0. Headline

* The estimator body maps to §6.3.9 step for step. Every divergence I can show is already in the
  record: **F10/C01** (chained prefix lookup under the cap; NOT REPAIRED, documented as an
  unbounded overstating margin above width 1), **F09** (run counter; REPAIRED), **D-1** (ZALPHA),
  **F08** (x iterated to convergence rather than x_10), **C22a** (bisection quantisation).
* **No new overstatement path was found inside this component.** At width 1 (bitstring, and the
  Literal path on 1-bit data) the implementation is spec-exact including saturation, by the counting
  argument in §2.5 below, which I re-derived rather than took from the record.
* The one thing I add is an argument (§4, E2) that the documented F10 margin of 3.69e-4 bit is small
  **only because the standard's own scoreboard rule defeats the naive periodic construction**, and a
  construction that defeats the scoreboard rule in turn (a depth-15 ambiguity gadget) should move the
  Literal MultiMMC figure by order 0.5 bit at the shipped constants. This is a SUSPICION with a
  derivation, not a measurement; it is the documented path, so even if confirmed it is a change in the
  SIZE of C01, not a new finding. I also argue (not prove) it cannot move the headline figure because
  t-tuple/LRS/Lag bind lower on any data that exercises it.
* The tool reproduces the §6.3.9 worked example exactly (probe in §2.8).

---

## 1. The standard's algorithm, transcribed (SP 800-90B §6.3.9, PDF pp. 60–62)

Quoted from `reference/sp800-90b.pages.txt` lines 3216–3324 (ligature garbling of subscripts
normalised).

> "Given the input S = (s1, …, sL), where si ϵ A = {x1, …, xk},
> 1. Let D = 16, and N = L − 2. Let subpredict be a list of D values, each initialized to Null. Let
>    correct be an array of N values, each initialized to 0. Let entries be an array of D values, each
>    initialized to 0, and let maxEntries = 100 000.
> 2. For d = 1 to D, let Md be a set of counters, where Md[x, y] denotes the number of observed
>    transitions from output x to output y for the d th-order MMC.
> 3. Let scoreboard be a list of D counters, each initialized to 0. Let winner = 1.
> 4. For i = 3 to L:
>    a. For d = 1 to D:
>       i. If d < i−1:
>          1. If [(si-d-1, …,si-2), si-1] is in Md, increment Md[(si-d−1, …,si−2), si−1] by 1.
>          2. Else if entriesd < maxEntries, add a counter for [(si−d−1, …,si−2), si− 1] to the set,
>             let Md[(si−d−1,…,si−2), si− 1] = 1 and increment entriesd by 1.
>    b. For d = 1 to D:
>       i. If d < i, find the y value that corresponds to the highest Md[(si-d,…,si-1), y] value, and
>          denote that y as ymax. If there is a tie, let ymax be the greatest y in the tie. Let
>          subpredictd = ymax. If all possible values of Md [(si-d,…,si-1), y] are 0, then let
>          subpredictd = Null.
>    c. Let prediction = subpredictwinner.
>    d. If (prediction = si), let correcti-2 = 1.
>    e. Update the scoreboard. For d = 1 to D:
>       i. If (subpredictd = si)
>          1. Let scoreboardd = scoreboardd +1.
>          2. If scoreboardd ≥ scoreboardwinner, let winner = d.
> 5. Let C be the number of ones in correct.
> 6. Calculate the predictor's global performance as Pglobal = C/N. The upper bound of the 99 %
>    confidence interval on Pglobal, denoted P'global is calculated as:
>    P'global = 1 − 0.01^(1/N) if Pglobal = 0; min(1, Pglobal + 2.576 sqrt(Pglobal(1−Pglobal)/(N−1))) otherwise
>    where 2.576 corresponds to the Z(1−0.005) value." (SP 800-90B §6.3.9 steps 1–6, PDF p. 61)

> "7. Calculate the predictor's local performance, based on the longest run of correct predictions.
>    Let r be one greater than the length of the longest run of ones in correct. Use a binary search to
>    solve the following for Plocal: 0.99 = (1 − Plocal x) / ((r + 1 − r x) q) × 1/x^(N+1), where
>    q = 1 − Plocal and x = x10, derived by iterating the recurrence relation
>    xj = 1 + q Plocal^r xj−1^(r+1) for j from 1 to 10, and x0=1. Note that solving for Plocal using the
>    logarithm of these equations is robust against overflows.
> 8. The min-entropy is the negative logarithm of the greater performance metric
>    min-entropy = −log2(max(P'global, Plocal, 1/k))." (SP 800-90B §6.3.9 steps 7–8, PDF p. 62)

Constants, bounds and directions to carry into the mapping:

| item | spec value / rule | direction |
|---|---|---|
| D | 16 | — |
| N | L − 2 (one prediction per i = 3..L) | smaller N → wider CI → lower entropy |
| maxEntries | 100 000 **counters** (= (x,y) pairs), per depth | once full, NEW pairs are dropped, EXISTING pairs still increment (4.a.i.1 has no cap condition) |
| 4.a add condition | d < i − 1 | the pair added at i is the one ending at s_{i−1} |
| 4.b predict condition | d < i | M_d is empty when d = i − 1, so that sub-prediction is Null anyway |
| tie among y | greatest y | encoding-dependent by the standard's own text |
| scoreboard | ascending d, `≥`, winner updated in-loop | deepest tied depth wins |
| correct_{i−2} | 1 only when prediction = s_i; Null ⇒ stays 0 | a Null from the winner breaks a run (this is D-4/F09) |
| P'global | upper 99 % bound, Z = 2.576 (printed) | upper bound ⇒ lower entropy |
| r | 1 + longest run of ones | larger r ⇒ larger Plocal ⇒ lower entropy |
| Plocal | root of the step-7 equation with x = x_10 | upper bound on p from the run |
| floor | 1/k | — |

Worked example (PDF pp. 62–63): S = (2,1,3,2,1,3,1,3,1), L = 9, N = 7, D = 3;
"correct = (0, 0, 1, 1, 0, 1, 0). Then, Pglobal = 0.4286, P'global = 0.9490, Plocal = 0.1307, and the
resulting min-entropy estimate is 0.0755."

---

## 2. Mapping to the C++

### 2.1 Entry point and dispatch — `cpp/non_iid/multi_mmc_test.h:176-190`

```
176 double multi_mmc_test(uint8_t *data, long len, int alph_size, const int verbose, const char *label){
183 	if(alph_size == 2) return binaryMultiMMCPredictionEstimate(data, len, verbose, label);
187 	if(len < 3){ ... return -1.0; }
193 	N = len-2;                       // step 1
197 	winner = 0;                      // step 3 (0-indexed depth 1)
```

Callers (`non_iid_main.cpp:576-599`): Bitstring path `multi_mmc_test(data.bsymbols, data.blen, 2, …)`
when `alph_size > 2 || !initial_entropy`; Literal path `multi_mmc_test(data.symbols, data.len,
data.alph_size, …)` when `initial_entropy`. A return `< 0` sets `tc639.*_not_run` and the estimate is
omitted from `min()`. `restart_main.cpp:1054,1061` (rows, cols) and `conditioning_main.cpp:427`
(bitstring) call the same function. `k` passed to `predictionEstimate` is `alph_size`, the number of
**observed** distinct symbols after translation (`utils.h:506-517`), so 1/k ≥ 1/2^w: conservative or
equal relative to reading k as the full alphabet.

Symbol translation (`utils.h:502-517, 542-544`): the map-down table is built by scanning values
`0..2^w−1` in increasing order, so the relabelling is **order-preserving**; "greatest y" over translated
symbols equals "greatest y" over raw values. On the Literal path with `alph_size == 2` the symbols
are therefore exactly {0,1}, which the binary path relies on (`S[i]&1`, `curPrediction == S[i]`).

### 2.2 Generic path, steps 2–4 — `multi_mmc_test.h:185-287`

| spec | code | note |
|---|---|---|
| step 2, M_d | `array<map<array<uint8_t,16>, PostfixDictionary>,16> M` (185); depth d+1 lives in `M[d]`, key = d+1 bytes then zero padding (memset 205/227) | separate maps per depth, so padding cannot collide across depths |
| step 1, entries | `int entries[D_MMC]` (178), `entries[d] = 1` in init (210), `++` at 265 and 273 | **counts pairs**, as the spec's "counters" |
| step 4.a (first add per depth) | init loop 206–212: `M[d][S[0..d]].incrementPostfix(S[d+1], true)` for `d < N` | pre-adds the pair the spec adds at its iteration I = d+3 (0-idx i = d+2), i.e. one round before that depth is first consulted — see 2.4 |
| step 4.a (all later adds) | 263–266 (prefix found: increment-or-add under cap) and 267–274 (prefix not found: add under cap) executed **after** the prediction at the same i | equals spec's 4.a of the NEXT iteration; the pair ending at s_i is added at code iteration i and used from i+1 — see 2.4 |
| step 4.a.i.1 "increment if present", no cap | `incrementPostfix(data[i], entries[d] < MAX_ENTRIES)`: `utils.h:1317-1319` increments whenever the postfix exists regardless of `makeNew` | matches |
| step 4.a.i.2 cap on new pairs | `makeNew = entries[d] < MAX_ENTRIES` (263); `else if(entries[d] < MAX_ENTRIES)` (267) | matches **when the prefix lookup ran**; see F10 |
| step 4.b lookup every d independently | `if((d == 0) \|\| found_x)` (236): depth d is looked up only if depth d−1 was found | **DIVERGENCE = F10/C01**, documented, NOT REPAIRED |
| step 4.b argmax, greatest y on tie | `PostfixDictionary::incrementPostfix` tracks `(curBest, curPrediction)` with `(curCount > curBest) \|\| (curCount == curBest && in > curPrediction)` (`utils.h:1330-1333`) | invariant holds because counts only increase by 1 and only one y changes per call: new strict max → replace; join of the max set → keep the greater y; below max → unchanged. Equivalent to a fresh argmax with greatest-y tie-break |
| step 4.b "d < i" | loop bound `(i-2 >= d)` (229) ⇒ depth ≤ i−1 (0-idx) ⇒ spec depth ≤ I−2 | one depth stricter than the spec's d < I, but the omitted depth I−1 has an empty M at iteration I (its first add is at 4.a of I+1 since d < I−1 fails), so its sub-prediction is Null in the spec too — equivalent |
| step 4.c prediction = subpredict_winner; 4.d | `cur_winner = winner` (226); `if(d == cur_winner){ C++; winner_correct = true; }` inside `if(found_x)` (256–259) | Null (not found, or depth not reached) ⇒ no C, `winner_correct` stays false |
| step 4.e scoreboard, ascending d, `≥`, winner updated in-loop | `if(++scoreboard[d] >= scoreboard[winner]) winner = d;` (255), inside the ascending d loop | identical semantics including deepest-tie-wins |
| step 5–7 longest run | `winner_correct` → `run_len`/`max_run_len` (282–286) | F09 repair; resets on wrong, Null and not-reached |
| N | `N = len-2` (193) → `predictionEstimate(C, N, max_run_len, alph_size, …)` (289) | matches |

### 2.3 Binary specialisation — `multi_mmc_test.h:7-158`

| spec | code | note |
|---|---|---|
| L < 17 | 36–39 return −1.0 | fork decline (#257/F16); unreachable from a compliant run |
| M_d storage | `binaryDict[j] = new long[1U<<(j+2)]` (48): 2^(j+1) prefixes × 2 postfixes | `BINARYDICTLOC(d,b)` (`utils.h:1263`) masks b to d bits and ×2; max index 2^17−1 within the 2^17 allocation |
| init 4.a | 53–60: `curPattern = (curPattern<<1)\|(S[d]&1)`; `BINARYDICTLOC(d+1,curPattern)[S[d+1]&1] = 1; dictElems[d] = 1` | same pre-add as generic; bit orientation: most recent symbol in bit 0, identical to the main loop's `\|= (S[i-d-1]&1)<<d` (82) |
| 4.b chain | `if((d == 0) \|\| found_x)` (93) | same chain as generic; **provably harmless for binary** — see 2.5 |
| 4.b argmax, tie → greatest | `if(e[0] > e[1]) predict 0 else predict 1` (95–101) | tie predicts 1 = greatest |
| "x in M_d" | `curCount == 0 ⇒ found_x = false` (103) | a stored prefix always has a nonzero postfix count |
| 4.e | 112–113 | identical |
| 4.d / C | 116–119 | identical |
| 4.a counting | 123–138 | increment-if-present regardless of cap; add under cap; not-found add under cap |
| run | 144–149 | F09 repair |
| N, k | `predictionEstimate(correctCount, L-2, maxRunOfCorrects, 2, …)` (157) | matches |

### 2.4 Why the interleaved update equals steps 4.a/4.b (derivation, 0-indexed S, spec I = i+1)

Spec iteration I adds, for each d < I−1, the pair M_d[(S[I−d−2..I−3]), S[I−2]]. Code iteration i
(predicting S[i]) adds, for each depth index d ≤ min(15, i−2), the pair M_{d+1}[(S[i−d−1..i−1]), S[i]].
Setting d' = d+1 and I' = i+2 the two coincide: the code's add at i IS the spec's 4.a add at I' = i+2,
which precedes the spec's 4.b prediction at I' — and the code's prediction for S[i+1] is at code
iteration i+1 = I'−1, after that add. The prediction at code iteration i uses only pairs added at
iterations ≤ i−1, i.e. everything the spec's M holds after 4.a of iteration I = i+1. The prefix depth
d+1 is consulted at i only if d ≤ i−2 — the spec's 4.a add condition d' < I−1 = i. The init loop
(206–212 / 53–60) covers the one pair per depth that the code's main loop cannot reach (depth index d
needs i ≥ d+2 but its first pair ends at S[d+1], i.e. i = d+1): the spec adds it at I = d+3 (code
i = d+2), exactly the first round that depth is consulted, and before the prediction. So the init pair
is never used before the spec would have it.

### 2.5 Saturation under the chain (F10) — the counting argument, re-derived

Claim: a new pair at depth f at iteration i implies a new pair at every deeper depth e at the same
iteration (while e is covered and not full). Proof: if (x', y) existed at e it was added at j < i (or
init); then the depth-f suffix (x, y) was added or incremented at j (f is covered whenever e is and f
was not full at j ≤ i), contradicting (x,y) new at i; the init pair at e has its depth-f suffix added at
iteration e_idx+1 and is first consulted at e_idx+2. Hence
`entries[e] ≥ entries[f] − (e_idx − f_idx)` until e fills, and when f reaches 100 000 depth e has at
most (e−f) free slots. Each later occurrence of an ABSENT depth-f context sends every deeper depth down
the `else if(entries[d] < MAX_ENTRIES)` branch (267–274 / 133–138), which creates an "orphan" (prefix
present at e, suffix absent at f) and also `entries[d]++` even when the pair already existed. So at
most (e−f) orphan ENTRIES per depth e (≤ 105 in total), but each can be VISITED arbitrarily often, and
at every visit the code treats depth e as Null where the spec predicts. Direction when it bites:
code C ≤ spec C and code r ≤ spec r ⇒ **overstates**; scoreboard differences can move the winner
either way.

Binary: depth index d holds at most 2^(d+2) pairs; 2^16 = 65 536 < 100 000 for d ≤ 14, 2^17 = 131 072
for d = 15. Only the top depth can fill and there is no deeper depth to suppress, so no orphan can
exist and the chain lookup is exact. The Bitstring path and the Literal path on 1-bit data are
therefore spec-exact. Matches `FORK-DIVERGENCE-AND-TRUST.md` A.1 and `entropy_floor.py:93-100`.

### 2.6 Steps 6–8 — `cpp/shared/utils.h:1200-1256` (shared with Lag, MultiMCW, LZ78Y)

```
1208	curMax = 1.0 / ((double)k);
1209	p_global = (double)C/(double)N;
1229	if(p_global > 0) p_globalPrime = min(1.0, p_global + ZALPHA*sqrt((p_global*(1.0-p_global))/((double)N-1.0)));
1230	else p_globalPrime = 1.0 - pow(0.01, 1.0/(double)N);
1232	curMax = fmax(curMax, p_globalPrime);
1233	if((curMax < 1.0) && (prediction_estimate_function(curMax, max_run_len+1, N) > log(0.99))) {
1234		p_local = calc_p_local(max_run_len, N, curMax);
1235		curMax = fmax(curMax, p_local);
1236	}
1238	entEst = -log2(curMax);
```

* Step 6: `ZALPHA 2.5758293035489008` (`utils.h:75`) vs the printed 2.576 — **D-1**, documented; the
  binary64 quantile is smaller than 2.576 by 1.7e-4, so P'global is lower by ≤ 1.7e-4·sqrt(p(1−p)/(N−1))
  ≤ 8.5e-8 at N = 10^6: a higher entropy by < 1.3e-7 bit/bit. Recorded, not a bug.
* `(double)N-1.0` divides by zero only at N = 1 (L = 3 generic); `min(1.0, NaN)` returns 1.0
  (`std::min(a,b)` is `b<a?b:a`) ⇒ entropy 0: fail-closed (F13 note at 1211–1228). Unreachable at
  MIN_SIZE.
* `fmax` ignores a NaN argument; `p_global > 0` is false for NaN. No NaN path into `-log2`.
* Step 7 guard (1233): `prediction_estimate_function` is decreasing in p (longer runs become likelier),
  so f(curMax) > log 0.99 ⇔ the root p_local > curMax; otherwise p_local cannot raise the max.
  Correct direction, conservative shortcut.
* `prediction_estimate_function` (1087–1108) iterates `x = 1 + q p^r x^(r+1)` to convergence
  (≤ 66 steps, LDBL_EPSILON) instead of the spec's x_10 — **F08**, documented NOT-A-BUG, |ΔH| ≤ 4e-16
  measured in the 2026-09-30 audit. Asserts `x >= xlast` and `p*x <= 1` abort the process if violated;
  the 2026-10-11 audit ran ~1500 harness calls without firing. Not re-measured here.
* `calc_p_local` (1111–1197): bisection on [curMax, 1]; `log_alpha < pVal ⇒ lbound = p` is the right
  direction for a decreasing f. Every early exit sets `p = hbound` or `p = hdomain = 1.0`, i.e. a
  LARGER p ⇒ lower entropy: fail-closed. The `relEpsilonEqual(pVal, log_alpha, DBL_MIN, DBL_EPSILON, 4)`
  stop can return a p on the low side of the root by the quantisation documented as **C22a**
  (8.08e-15 × (N+1) bit); nothing new.
* Step 8: `curMax` is the max of 1/k, P'global and (if computed) Plocal; `-log2`. Matches.
* `-0.0` from curMax = 1 passes the caller's `>= 0` test, so an estimate of zero IS recorded.

### 2.7 Types, overflow, memory

* Accumulators `long` (LP64): `scoreboard`, `C`, `run_len`, `i`, `N`. `int entries[16]` is bounded by
  the `< MAX_ENTRIES` guard before every increment (the chain-skip `entries[d]++` at 273 is inside
  `else if(entries[d] < MAX_ENTRIES)`). `uint32_t curPattern` holds ≤ 16 bits (`assert(D_MMC < 31)`,
  41). `int winner` ∈ [0,15]. The Windows LLP64 `long` concern (C18) is recorded elsewhere; on this host
  `long` is 64-bit.
* `entries[d]` for `d ≥ N` is left uninitialised by the init loop (`if(d < N)`, 207) but the main loop's
  `d ≤ i−2 ≤ N−1` never reads it. Not a defect.
* Generic memory: ≤ 100 000 pairs per depth ⇒ ≤ 1.6 M map nodes total, order 200–300 MB worst case.
  Bounded; cannot be driven past the cap by input.
* Binary memory: Σ 2^(j+2) longs for j < 16 = 2^18 longs = 2 MB.

### 2.8 Probe: the standard's worked example

Input `corpus/mmc-worked-example-6-3-9.bin` = bytes (2,1,3,2,1,3,1,3,1), sha256
`52b6f5b32e289d53f9e6fb917ab36113e39a9f53989aee3390754435059ae5aa`. Command (non-compliant run):
`EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 cpp/ea_non_iid -vv <file> 2`, exit 0, log
`logs/analysis-multimmc-worked-example-vv.log`. Observed (verbatim):

```
Literal MultiMMC Prediction Estimate: C = 3
Literal MultiMMC Prediction Estimate: r = 3
Literal MultiMMC Prediction Estimate: N = 7
Literal MultiMMC Prediction Estimate: P_global = 0.42857142857142855
Literal MultiMMC Prediction Estimate: P_global' = 0.94896753363384267
Literal MultiMMC Prediction Estimate: P_local can't change the result.
Literal MultiMMC Prediction Estimate: min entropy = 0.07556936471861507
```

Expected from the spec (PDF p. 63): correct = (0,0,1,1,0,1,0) ⇒ C = 3, longest run 2 ⇒ r = 3, N = 7,
Pglobal = 3/7 = 0.428571; P'global = 0.428571 + Z·sqrt(0.428571·0.571429/6) = 0.428571 + Z·0.202031:
Z = 2.5758293 gives 0.948968 (tool), Z = 2.576 gives 0.949012 (spec prints 0.9490); Plocal = 0.1307
< P'global so it cannot bind (tool says the same); −log2(0.948968) = 0.07557 (spec 0.0755). Match,
with D = 16 instead of the example's D = 3 making no difference here because depths ≥ 4 never score.

The first attempt used `-vvv`: `verbose` is incremented per flag (`non_iid_main.cpp:175-177`) from a
base of 1, so `-vvv` gives 4, which matches neither `verbose == 2` nor `verbose == 3` in
`predictionEstimate` and prints NO per-estimator lines while still printing the final figures (log
`logs/analysis-multimmc-worked-example.log`). Reporting quirk, direction neutral, outside this component.

---

## 3. Prior repairs touching this component, and how to try to break them

| repair | what it did | break attempts / status |
|---|---|---|
| **F09** (`69b6094`; NOTICE 2026-09-30; tracker F09; D-4) | run of correct predictions ends on anything that is not a correct prediction by the winner (wrong, Null, depth not reached), both paths (144–149, 282–286) | (a) early rounds with `cur_winner > i−2`: `winner_correct` initialised false ⇒ reset: correct. (b) Null via the F10 chain while the winner's own context is an orphan: code resets, spec would extend ⇒ code r ≤ spec r — overstating, but it is F10's mechanism, not a regression of F09. (c) Could a Null from a non-winner reset the run? No: only `d == cur_winner` sets the flag and the reset is outside the d loop. (d) The regression's "independent reference" for the binary path (`regression-multimmc.sh:103-153`) mirrors the code's chained lookup (`if d == 0 or found`) and is spec-equivalent only because the cap cannot bite below the top depth for binary data; it would silently inherit F10 if `D_MMC` or `MAX_ENTRIES` were changed. Test-integrity note, LOW. (e) Lines 155/169/170 read with `head -1`, instrument rule 5. LOW. |
| **F16 / #257** (`ed88de9`) | binary path declines (returns −1.0) for L < 17 instead of reading `S[16]` | L = 17 exactly: init reads `S[0..16]`, in bounds; N = 15; the generic path's `len < 3` guard is independent. Omitting the estimate at L < 17 makes `min()` see one fewer estimator (higher figure) but only below MIN_SIZE and only with the escape set. |
| **`fix/multimmc-binary-overread`** (`1bb4468`, 2026-09-30, on upstream `87c104d`, NOT merged, 1 commit ahead) | bounds the init loop (`d+1 < L`) and keeps `assert(L>3)` | `git diff audit/2026-11-07 fix/multimmc-binary-overread -- cpp/non_iid/multi_mmc_test.h` shows it is pre-F09: merging it as-is would REMOVE the `winner_correct` logic in both paths and re-introduce F09 (understating) and replace the decline with a partial-model run. Process hazard, no effect on the shipped binary today. |
| **F10 / C01** | NOT repaired; documented | see §4 E2 for an attempt to show the documented margin is far from a bound. |

---

## 4. Edge-case inputs that separate a correct from an incorrect implementation

E1. **Spec worked example** (done, §2.8): 9 bytes (2,1,3,2,1,3,1,3,1), width 2, `EA_ALLOW_SHORT_DATASET=1`.
    Expected C=3, r=3, N=7, H=0.0756. Any F09-style or indexing error moves C or r.

E2. **F10 amplifier with a depth-15 ambiguity gadget** (8-bit Literal path, ≥ 1 000 000 samples). The
    naive periodic construction cannot move C: with a period W containing the orphan positions
    t = b+1..b+14 (b = offset where depth 2 fills), the spec's scoreboards per period are
    (b−e+1) pre-boundary hits + (e−2) orphan hits = b−1 for EVERY depth e ≥ 3, and within the period
    the winner at orphan position b+j is depth j+1, whose orphans stop at b+j−1 — so the winner's
    prediction is Null there in the spec as well, and C_spec = C_code. (This is why the earlier
    audits measured only 3.69e-4 bit.) To break the tie, give depth 16 a strict lead over depth 15 and
    everything shallower:
    * Fill: ≥ 100 000 symbols over {16..255} with ALL 3-grams distinct (greedy rejection), so depths
      2..16 fill in order 2,3,…,16 at consecutive iterations (entries[e] = entries[2] − (e−2) exactly).
      Use `audits/2026-09-30/novel-findings/generators/noniid/fillsteps.py` to find the boundary.
    * Period W (length P ≈ b+15, alphabet {1..8} disjoint from the fill), laid so that depth 2 fills
      at W offset b ≥ 48. Pre-boundary region contains a gadget `u X a … v X b` with X a 15-gram,
      u≠v, a≠b: depth ≤ 15 is ambiguous there (one of the two occurrences wrong under greatest-y), depth
      16 is right at both ⇒ +1 per period for depth 16 over depth 15, and similar gadgets for shorter
      contexts if needed. Orphan block = W[b+1..b+14] with in-period 16-contexts (b ≥ 15).
    * Repeat W for the remaining ~900 000 samples.
    Expected per period from §2.5: spec winner = depth 16 from period 2 on, C_spec − C_code ≈ 14
    (minus gadget losses), i.e. ΔP_global ≈ 14/P ≈ 0.2 and a Literal MultiMMC figure higher by order
    0.5 bit in the tool than in a spec-literal reference. Expected but to be verified: the headline is
    unchanged because t-tuple at t = P gives P ≈ (R/N)^{1/P} and Lag catches the period, both well
    above MultiMMC's p; MultiMMC can bind only if R·P/N > 1, which is impossible. Negative control:
    the same construction at width 1 (E3). Direction: overstates the per-estimator figure.

E3. **Width-1 negative control for E2**: the same tail re-expressed as bits. By §2.5 no orphan can
    exist; tool and spec-literal reference must agree on C and r exactly.

E4. **Binary length boundary**: 17 bits ⇒ runs (N = 15); 16 bits ⇒ `-1.0`, "not enough samples", and
    the estimate omitted from min(). Checks the #257 decline and the init's `S[16]` read.

E5. **All-zero bitstring, L = 1 000 000**: every depth predicts 0 from i = 2; C = N, r = N+1,
    P'global = 1 ⇒ H = −0 which the caller must record (`>= 0` is true for −0.0).

E6. **Period-17 aperiodic binary sequence** (longer than D = 16): every 16-context is deterministic, so
    depth 16 should be perfect after one period; expect H ≈ 0. A wrong depth bound (e.g. 15) would
    leave ambiguity and report more entropy.

E7. **Tie-break probe (8-bit)**: context (5,6) followed by 3 and by 7 equally often, then (5,6) once
    more followed by 7: the correct prediction is 7 (greatest y). Variant with an order-preserving
    relabelling {3,7}→{40,90} must give identical C and r; a non-monotone relabelling may not and is
    allowed to differ by the standard's own rule.

E8. **Scoreboard tie**: data where depths 1 and 2 reach equal scores at the same i and disagree at
    i+1; the deepest (depth 2) must supply the prediction (≥ with ascending d).

E9. **Bitstring saturation**: ≥ 200 000 random bits so depth 16 (131 072 possible pairs) hits the
    100 000 cap; tool vs spec-literal reference must agree on C and r (cap semantics: drop new pairs,
    keep incrementing existing ones).

E10. **Orphan revisit while NOT full (entries over-count)**: construct so that a depth-e orphan is
    revisited before e fills; the code's `entries[d]++` at 273 counts the revisit as a new pair and
    saturates e early. Tiny effect (≤ e−f slots) but a distinct observable (final `entries[]`), only
    visible with an instrumented build — execution phase only.

---

## 5. Suspicions, ranked by overstating potential

1. **F10/C01 margin is far larger than the recorded 3.69e-4** (SUSPICION, derivation in §2.5/§4 E2,
   not measured). Direction: overstates the Literal MultiMMC figure; headline believed unaffected.
   Documented divergence — a change in size, not a new finding, if confirmed.
2. **D-1 / F08 / C22a** numeric deviations in the shared step 6–8 helper: all documented, all
   ≤ 1e-7 bit, two of them overstating by construction (D-1, C22a's low-side stop). Not re-measured.
3. **Stale branch `fix/multimmc-binary-overread` would revert F09 if merged** (process; understates).
4. **`regression-multimmc.sh` binary reference is code-shaped, not spec-shaped** (test integrity; LOW).
5. **`-vvv` prints no per-estimator lines** (reporting; outside this component; LOW).

Nothing in the estimator body itself was found to depart from §6.3.9 apart from the recorded F10.
