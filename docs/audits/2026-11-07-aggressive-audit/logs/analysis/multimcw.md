# MultiMCW prediction estimate (SP 800-90B §6.3.7) — analysis-phase record

Date: 2026-11-07. Branch `audit/2026-11-07`. Analysis phase: no builds, no runs over 20,000
samples. Platform: Darwin arm64, Apple clang 21 (production binary as found on disk).
Production binary measured: `cpp/ea_non_iid` sha256
`1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` (instrument rule 4).
Every probe below used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NON-COMPLIANT by
construction (brief ground rule 5). Every probe wrote a file under `logs/`; nothing was piped
into head/tail for a verdict (rule 17).

Files read in full: `cpp/non_iid/multi_mcw_test.h` (89 lines), `cpp/shared/utils.h`
lines 39-40, 60-200, 1040-1255 (`relEpsilonEqual`, `prediction_estimate_function`,
`calc_p_local`, `predictionEstimate`), lines 470-545 (`read_file_subset` masking,
`alph_size`, symbol translation, `bsymbols`); `cpp/non_iid_main.cpp` lines 24-40, 97-176,
249-251, 299-380, 515-545, 628-642; `cpp/restart_main.cpp` 1011-1025;
`cpp/conditioning_main.cpp` 413-418; `cpp/shared/test_case_base.h` 37-47.
Documents read: AUDIT-BRIEF.md; FORK-DIVERGENCE-AND-TRUST.md (D-1, D-2, §4 open item,
OC-111/112/116 context); audits/2026-09-30/FINDINGS-TRACKER.md (F04, F05, F07, F08, F13,
F24, F25); AUDIT.md rows F13/F24/F25; ORCHESTRATOR-CHECKS.md OC-112 and OC-116;
cpp/selftest/known-platform-deltas.txt; cpp/selftest/regression-estimator-guards.sh header.

---

## 1. The standard's algorithm, step by step

All quotes from `reference/sp800-90b.pages.txt`; section 6.3.7 spans PDF pp. 57-59.

**Preamble (PDF p. 57):** "Each subpredictor predicts the value that occurs most often in
that window of w previous outputs. The MultiMCW predictor keeps a scoreboard that records
the number of times that each subpredictor was correct, and uses the subpredictor with the
most correct predictions to predict the next value. In the event of a tie, the most common
sample value that has appeared most recently is predicted."

Input: "S = (s1, …, sL), where si ϵ A = {x1, …, xk}". §6 (PDF p. 48): A is "an output
space A = {x1, …, xk} that is specified by the submitter."

| step | text (SP 800-90B §6.3.7, PDF p. 57-58) | constants / rules |
|---|---|---|
| 1 | "Let window sizes be w1=63, w2=255, w3=1023, w4=4095, and N = L − w1. Let correct be an array of N Boolean values, each initialized to 0." | N = L − 63 |
| 2 | "Let scoreboard be a list of four counters, each initialized to 0. Let frequent be a list of four values, each initialized to Null. Let winner = 1." | winner starts at the 63-window |
| 3 | "For i = w1 + 1 to L:" | N iterations, i = 64..L |
| 3a.i | "If i > wj, let frequentj be the most frequent value in (si-wj, si-wj+1, …, si-1). If there is a tie, then the most frequent value that has appeared most recently is assigned to frequentj." | window = the wj symbols strictly before si; tie → most recent occurrence |
| 3a.ii | "Else, let frequentj = Null." | window j inactive until i > wj |
| 3b | "Let prediction = frequentwinner." | |
| 3c | "If (prediction = si), let correcti- w1 = 1." | Null never equals si |
| 3d | "Update the scoreboard. For j =1 to 4, i. If (frequentj = si) 1. Let scoreboardj = scoreboardj +1 2. If scoreboardj ≥ scoreboardwinner, let winner =j" | ≥, evaluated sequentially j = 1..4 with `winner` possibly already moved this step |
| 4 | "Let C be the number of ones in correct." | |
| 5 | "P_global = C/N. The upper bound of the 99 % confidence interval on P_global, denoted P'_global is calculated as: 1 − 0.01^(1/N), if P_global = 0; min(1, P_global + 2.576 sqrt(P_global(1−P_global)/(N−1))), otherwise — where 2.576 corresponds to the Z(1−0.005) value." | UPPER bound; denominator N−1; cap at 1 |
| 6 | "Let r be one greater than the length of the longest run of ones in correct. Use a binary search to solve the following for P_local: 0.99 = (1 − P_local x)/((r + 1 − r x) q) × 1/x^(N+1), where q = 1 − P_local and x = x10, derived by iterating the recurrence relation x_j = 1 + q P_local^r x_{j-1}^(r+1) for j from 1 to 10, and x0 = 1. Note that solving for P_local using the logarithm of these equations is robust against overflows. Table 3 given in Appendix G.2 provides some pre-calculated values of P_local." | r = longest run + 1; exactly ten recurrence iterations in the text; target 0.99; no tolerance or termination rule stated |
| 7 | "The min-entropy is the negative logarithm of the greater performance metric min-entropy = −log2(max(P'_global, P_local, 1/k))." | floor at 1/k |

**Worked example (PDF p. 58-59):** S = (1,2,1,0,2,1,1,2,2,0,0,0), L = 12, windows 3,5,7,9,
N = 9; "correct = (0, 0, 0, 1, 0, 1, 0, 0, 1). Then, P_global = 0.3333, P'_global = 0.7627,
P_local = 0.036, and the resulting min-entropy estimate is 0.3908." The table on p. 58 shows
the scoreboard tie at i = 7 moving `winner` from 1 to 2 (both windows correct, `≥`).

**Appendix G.2 (PDF p. 83-84):** "P'_global … the proportion corresponding to the 99th
percentile of the number of correct predictions"; P_local "the successful prediction
proportion for which the observed longest run of correct predictions is the 99th
percentile. This is effectively a one-tail hypothesis test that rejects P'_global in favor
of P_local if the observed longest run, given a success probability of P'_global, is beyond
the 99th percentile." Table 3 (L = 1,000,000) gives e.g. r=2 → 0.0001, r=4 → 0.0100,
r=10 → 0.1614, r=36 → 0.6157, r=100 → 0.8398, r=1000 → 0.9860, r=10000 → 0.9988.

Direction summary: P'_global is an UPPER confidence bound; P_local is the p at which the
observed longest run is at the 99th percentile; the estimate takes the LARGER of the two and
1/k, i.e. the most pessimistic probability. Any code path that lowers max(P', P_local, 1/k)
relative to the text OVERSTATES entropy.

---

## 2. Mapping to the C++

### 2.1 The predictor loop — `cpp/non_iid/multi_mcw_test.h:multi_mcw_test` (lines 7-88)

| spec | code | verdict |
|---|---|---|
| step 1 windows | line 9 `int W[NUM_WINS] = {63, 255, 1023, 4095};` | matches |
| N = L − w1 | line 21 `N = len-W[0];` | matches |
| step 2 scoreboard=0, winner=1 | lines 11, 22 `long scoreboard[NUM_WINS] = {0}; … winner = 0;` (0-based) | matches |
| frequent initialised Null | line 14 `uint8_t frequent[NUM_WINS];` — uninitialised, BUT lines 34-44 set every `frequent[j]` at i=0 because `max_cnts[j] (0) <= ++win_cnts (1)` is always true | no read-before-write; inactive windows are handled by the `i >= W[j]` guards at lines 57 and 64 rather than by a Null value |
| 3a.i window (s_{i−wj} … s_{i−1}) | initial counts lines 34-44 cover `data[0..W[j]-1]`; the update at lines 63-85 (after the prediction at i) removes `data[i-W[j]]` and adds `data[i]`, so at iteration i the window is `data[i-W[j] .. i-1]` | matches (0-based i_c = i_s − 1; "i > wj" ⇔ `i_c >= W[j]`) |
| 3a.i tie → most recent | lines 37 (`<=` on insertion: a tied newcomer, the most recent, takes over), 68 (same `<=` in case A), 72-83 (case B: when the departing symbol was the frequent one, rescan all k, strict `<` on count or `==` with `max_pos <= win_poses[j][k]`, i.e. the most recent last-occurrence wins) | matches (proved by differential, §2.6) |
| 3a.ii Null for i ≤ wj | guards `i >= W[j]` at lines 57 and 64; `winner` can only move to j inside line 58 which is inside that guard, so `frequent[winner]` at line 49 is always an active window | matches |
| 3b/3c prediction & correct | lines 49-53 `if(frequent[winner] == data[i]){ C++; if(++run_len > max_run_len) max_run_len = run_len; } else run_len = 0;` | matches; also computes the longest run of step 6 inline |
| 3d scoreboard, `≥`, sequential | lines 56-60 `for(j…) if((i >= W[j]) && (frequent[j] == data[i])){ if(++scoreboard[j] >= scoreboard[winner]) winner = j; }` | matches, including that `scoreboard[winner]` re-reads a `winner` moved earlier in the same j-loop (the p. 58 i=7 case) |
| step 4 C | counted inline, line 50 | matches |
| step 6 r = longest run + 1 | passed as `max_run_len` and `predictionEstimate` uses `max_run_len+1` everywhere (utils.h 1233, 1234, 1241-1242, 1245) | matches |
| guard | lines 16-19 `if(len < W[NUM_WINS-1]+1){ printf("… need more than %d …", W[NUM_WINS-1]+1); return -1.0; }` | DEPARTS from the text: the text runs for any L > 63 (3a.ii makes larger windows sit out); the code refuses L < 4096 and the message says "more than 4096" where the enforced rule is "at least 4096". This is tracker **F04**, FORK-FIXED by the 1,000,000 intake (`dataset_meets_minimum`, non_iid_main.cpp 317-325). Reachable only with `EA_ALLOW_SHORT_DATASET=1`. A dropped estimator can only RAISE the min — direction overstates, on a test-only path. |

Types: `long i, j, k, N, C, run_len, max_run_len, max_pos` (line 10), `long scoreboard[]`,
`long win_cnts[][]`, `long win_poses[][]` (lines 11-13); `uint8_t *data`. On LP64 (this
host, Linux) these are 64-bit; nothing here can overflow below 2^63 samples. On LLP64
(Windows) `long` is 32-bit — that is the documented C18 family (CLOSING-INVENTORY.md
lines 101, 273, 330-357) and is not re-reported; within 2^31 samples this file is fine
there too.

VLA (build log lines 81-98): line 13 `long win_cnts[NUM_WINS][alph_size],
win_poses[NUM_WINS][alph_size];` — these are ALPHABET-sized, not input-sized.
`alph_size` is 2 on the Bitstring path (non_iid_main.cpp 524) and `data.alph_size` on the
Literal path; `read_file_subset` masks every symbol to `word_size` bits (utils.h 510),
counts distinct values into `alph_size` (515-517), and maps symbols down to
`0..alph_size-1` when `alph_size < maxsymbol+1` (542-544). So every `data[i] < alph_size`
and `alph_size ≤ 256`: the two VLAs total at most 2 × 4 × 256 × 8 = 16 KiB of stack. The
intake refuses `alph_size <= 1` (non_iid_main.cpp 329). I find no out-of-bounds index on
these arrays. The task text's description "input-sized stack arrays" is not accurate for
this file; the Clang warning is about the C++ extension, not about size.

Minimum legal count on this fork (4096): the initialisation loop reads `data[0..4094]`
(line 34, needs len ≥ 4095); the prediction loop runs i = 63..len−1; at i = 4095 the
4095-window becomes active and the update reads `data[i-W[3]] = data[0]` — all in bounds.

### 2.2 The numerics — `cpp/shared/utils.h:predictionEstimate` (lines 1200-1255)

| spec | code | verdict |
|---|---|---|
| step 5 P_global = C/N | 1209 `p_global = (double)C/(double)N;` | matches |
| step 5, P_global = 0 branch | 1230 `else p_globalPrime = 1.0 - pow(0.01, 1.0/(double)N);` | matches |
| step 5, otherwise | 1229 `if(p_global > 0) p_globalPrime = min(1.0, p_global + ZALPHA*sqrt((p_global*(1.0-p_global))/((double)N-1.0)));` with utils.h:75 `#define ZALPHA 2.5758293035489008` | N−1 and the min(1,·) cap match. The constant is the binary64 0.995 quantile, not the printed 2.576 — **DOCUMENTED DIVERGENCE D-1 / F07** (FORK-DIVERGENCE-AND-TRUST.md 649-677): measured +3.80e-06 bit on Literal MultiMCW, +8.70e-08 on Bitstring MultiMCW, direction permissive. Not re-reported. |
| step 7 floor 1/k | 1207 `curMax = 1.0 / ((double)k);` then 1232 `curMax = fmax(curMax, p_globalPrime);` | matches; `k` is `alph_size` = the OBSERVED distinct-symbol count after translation, not the submitter's 2^bits. Smaller k → larger floor → lower or equal entropy: conservative, upstream behaviour ("Symbols have been translated", non_iid_main.cpp 348). |
| step 6 solve P_local | 1233-1236 `if((curMax < 1.0) && (prediction_estimate_function(curMax, max_run_len+1, N) > log(0.99))) { p_local = calc_p_local(max_run_len, N, curMax); curMax = fmax(curMax, p_local); }` | The solve is attempted only when F(curMax) > ln 0.99, i.e. when the root p* exceeds curMax; otherwise P_local cannot raise the max and is reported as "can't change the result". Equivalent for min-entropy; the verbose intermediate `P_local` is then ABSENT, which the differential driver must treat as "not binding", not as a mismatch. |
| step 7 | 1238 `entEst = -log2(curMax);` | matches |

`fmax` ignores a NaN operand, so curMax cannot become NaN from p_local; `p_global > 0` is
false for NaN so the F13 ordering comment (1211-1228) is right that min(1.0, NaN) is
unreachable (N = 1 is the only NaN source and MIN_SIZE forbids it). The caller
(non_iid_main.cpp 525, 536) folds with `if (ret_min_entropy >= 0)`; a NaN would be treated
as "not run" (F05 flag), but I find no producer of NaN for `entEst` on any path.

### 2.3 The function — `prediction_estimate_function` (utils.h 1083-1108)

```
q = 1.0L-p; x = 1.0L;
for(int i = 0; (i <= 65) && ((x - xlast) > (LDBL_EPSILON*x)); i++) {
    xlast = x;
    x = 1.0L + q*powl(p, r)*powl(x, r+1.0L);
    assert(x >= xlast);
    assert(p*x <= 1.0L);
}
return((double)(logl(1.0L-p*x) - logl((r+1.0L-r*x)*q) - (N+1.0L)*logl(x)));
```

- Recurrence matches step 6's `x_j = 1 + q p^r x_{j-1}^(r+1)`, x0 = 1, but iterates to
  convergence (≤ 66 steps) instead of exactly ten. **Tracker F08, NOT-A-BUG** ("effect
  < 1e-10. UNVERIFIED"). Argument why it cannot change a decision: the bisection only
  compares F(p) with ln 0.99; at any probe p the two variants differ in sign of F − ln 0.99
  only if |F − ln 0.99| is below the truncation error. Near the root, q p^r x^(r+1) ≈ 0.01/N
  so x_10 and x_∞ agree to ~((r+1)·0.01/N)^10 relative — far below double precision. Far
  from the root (large (r+1)q p^r) the truncation error can be O(1) in F, but there F is
  thousands of nats away from ln 0.99 and both variants agree on the sign. Neutral.
- Logarithmic form matches the text's note on overflow robustness.
- Log of zero / NaN: `logl(1-px)` is 0 and `logl((r+1-rx)q)` is of a negative number only
  when the smallest fixed point is x = 1/p, which happens iff (r+1)(1−p) ≤ 1, i.e.
  p ≥ r/(r+1). Mathematically, with longest run r−1, at most ⌈N/r⌉·(r−1) predictions can
  be correct, so P_global ≤ 1 − ⌊N/r⌋/N < r/(r+1): only the confidence term can push
  P'_global over r/(r+1), which needs Z√(Pq/(N−1)) > 1/(r(r+1)), i.e. r ≳ 53 at N = 10^6
  (r ≳ 8 at N = 4033). The root p* always lies below r/(r+1) (it needs the no-run
  probability to be 0.99), so if F(curMax) is −inf/NaN the correct decision is "P_local
  cannot bind", and `NaN > log(0.99)` / `-inf > log(0.99)` are both false — fail-safe.
  This is **AUDIT.md F24** ("FMA build gives NaN where non-FMA gives −inf. Guard decision
  unchanged"). Confirmed by probe (§2.7).
- The two `assert`s are LIVE in the production binary: `cpp/Makefile:51` has no `-DNDEBUG`
  and `nm cpp/ea_non_iid` shows `U ___assert_rtn`. Neither F24 nor F25 mentions them. In
  the x → 1/p regime the iterate approaches 1/p from below; a rounding overshoot to the
  double just above 1/p is possible when convergence is fast, but then `p*x` (rounded
  separately, not fused) is 1 + (< half an ulp of 1) and rounds back to exactly 1.0, so
  `p*x <= 1.0L` holds; and after an overshoot the loop exits on the (x − xlast) test before
  `x >= xlast` could be violated. I therefore EXPECT both asserts unreachable from the
  predictor's inputs. Measured: 10 in-regime instances, none fired (§2.7). **Suspicion,
  not reproduced; low confidence that it is reachable at all; crash direction if it were.**
  x86-64's 80-bit `long double` has a different ulp and the argument must be re-run there.
- No 0×inf: `powl(p,r)` underflowing to 0 gives x = 1 and F = 0 > ln 0.99, which is the
  mathematically right verdict (no-run probability ≈ 1 when p^r is astronomically small).

### 2.4 The bisection — `calc_p_local` (utils.h 1111-1198)

- Domain `[ldomain = curMax, hdomain = 1]`, first probe the midpoint, `log_alpha = log(0.99)`.
- Direction: `if(log_alpha < pVal) { lbound = p; … } else { hbound = p; … }` — F decreases
  in p, so F(p) > ln 0.99 means p < p* and the lower bound moves up. Correct.
- Termination: `relEpsilonEqual(pVal, log_alpha, DBL_MIN, DBL_EPSILON, 4)` (value within
  DBL_EPSILON relative or 4 ulp), `lbound >= hbound`, bracket-invariant failures, a
  repeated midpoint, or `ITERMAX 1076` iterations (utils.h:74 — more than the 53 a double
  bisection can use, so the cap never binds first).
- Every abnormal exit returns `hbound` or `hdomain` (lines 1148, 1159, 1165, 1175, 1183,
  1192) — the HIGHER p, i.e. lower entropy. The only exit that can return a p below p* is
  the equality break, by at most the tolerance. Conservative on every branch. This is what
  F25 describes ("always terminates on an invariant exit") — and its "not guaranteed ≥ true
  P_local" concern is bounded by the OC-116 envelope below.
- Evaluation error: `(N+1)·logl(x)` with x = 1 + ε discards ε's low bits at the 53-bit
  `long double` of arm64/MSVC. **OC-116** measured 1.18e-9 in P_local at N = 7,999,937 and
  predicted an envelope of ~1.8e-9 there (ulp(1)·(N+1)/|dF/dp|); on x86-64 (64-bit
  significand) ~8.8e-13. Two-sided. Sub-nanobit in entropy. Documented, closed, and it
  resolved the "Bitstring MultiMCW" open candidate of OC-111/112 — nothing in the predictor
  loop was involved (OC-116: "The predictor counted identically; the entire divergence is in
  solving P_local"). Not re-reported.

### 2.5 Call sites and what the final min() sees

- `non_iid_main.cpp` 523-543: Bitstring call `(data.bsymbols, data.blen, 2, …)` when
  `alph_size > 2 || !initial_entropy`; Literal call `(data.symbols, data.len,
  data.alph_size, …)` when `initial_entropy`. A −1 return sets
  `tc637.bitstring_not_run` / `literal_not_run` (F05) and is excluded from the min.
  1-bit data: only the Literal call runs (k = 2). 8-bit data: both; the Bitstring estimate is
  later multiplied by `word_size` (636). With `-t`, `blen` is truncated to MIN_SIZE (344).
- `restart_main.cpp` 1013-1025: rows and columns, `data.len` samples each. The `if
  (ret_min_entropy >= 0)` has NO else branch — a −1 would be dropped WITHOUT a not-run flag.
  Unreachable for MultiMCW (1000×1000 = 10^6 ≥ 4096), but it is a gap in the F05 repair's
  coverage worth a line in the limitations.
- `conditioning_main.cpp` 415-418: same pattern, no flag; outside the target profile.
- OpenMP: none in this estimator; deterministic.

### 2.6 Counting logic verified by differential (this phase)

`logs/analysis-multimcw-xcheck.log`: a line-by-line Python transcription of lines 21-86
against a literal transcription of §6.3.7 steps 1-4 (window rebuilt from scratch each step,
tie → most recent occurrence, Null for inactive windows). The spec's worked example
reproduces exactly (correct = (0,0,0,1,0,1,0,0,1), C = 3, N = 9, r = 2). 8,000
random/adversarial cases (alphabets 2-6, four window sets including [4,16,64,256],
uniform / drifting-majority / heavy-tie / periodic / vanishing-symbol generators): 0
mismatches in C, r or correct[].

The probe was shown able to fail (memory: prove the probe can fail): two behaviour-changing
mutants of the transcription — case-A tie `<=`→`<` (`…-mutant-m1.log`: worked example
MISMATCH, 5,679/8,000 mismatches) and case-B tie → least recent (`…-mutant-m2.log`:
MISMATCH, 6,099/8,000). A third mutant (`…-mutant.log`, case-B `<=`→`<`) produced 0
mismatches and is an EQUIVALENT mutant: `max_pos` starts at the departing position and no two
distinct symbols share a last-occurrence position, so the equality arm never decides. That
is a fact about the code (the `<=` at line 77 is not load-bearing), not a detector failure.

Limit (rule 18): the transcription is mine, not the compiled object; it cannot see compiler
or libm behaviour. It establishes that the ALGORITHM AS WRITTEN matches the text; the
execution-phase C++-vs-py90b differential establishes the binary.

### 2.7 The x → 1/p regime, probed on the production binary

Inputs: n zero bits with a 1 every M positions, 1 bit/symbol (so only the Literal path
runs, k = 2); the window majority is always 0, so the predictor misses exactly at the 1s and
r = M. `logs/analysis-multimcw-probe-assert-sweep.log` (and one per-run log each):

```
n=20000 M=1000 r=1000 P'=0.99957435763781333 (r+1)(1-P')=0.4261 exit=0 P_local can't change the result
n=20000 M=500  r=500  P'=0.99881000313155144 (r+1)(1-P')=0.5962 exit=0  "
n=20000 M=700  r=700  P'=0.99927876684537853 (r+1)(1-P')=0.5056 exit=0  "
n=20000 M=1500 r=1500 P'=0.99981363741185936 (r+1)(1-P')=0.2797 exit=0  "
n=20000 M=2000 r=2000 P'=0.99990688913262815 (r+1)(1-P')=0.1863 exit=0  "
n=20000 M=2500 r=2500 P'=0.99996410023048188 (r+1)(1-P')=0.0898 exit=0  "
n=17000 M=1000 r=1000 P'=0.99962303822266008 (r+1)(1-P')=0.3773 exit=0  "
n=13000 M=1000 r=1000 P'=0.99971268269192259 (r+1)(1-P')=0.2876 exit=0  "
n=9000  M=1000 r=1000 P'=0.9998572259258649  (r+1)(1-P')=0.1429 exit=0  "
n=20000 M=3300/5000/6600/9999: P'=1 exactly -> solve skipped by (curMax < 1.0), exit=0
```

Ten instances inside the regime ((r+1)(1−P') from 0.09 to 0.60), zero asserts, zero
non-zero exits, and the decision was the correct one every time (p* is far below P'
there). Control (`…-probe-mcw_control_every50_1bit-v3.log`): M = 50 gives
(51)(1−0.98254) = 0.89 — slow convergence, finite F, same decision, exit 0. F24's
"guard decision unchanged" is confirmed on this host and this binary; the asserts are
recorded as not reached. Note the verbosity lesson: `verbose` starts at 1 and `-v -v -v`
is level 4, which prints no per-estimator lines; level 3 is `-v -v`
(non_iid_main.cpp 97, 176). The first two probe logs (`…-probe-mcw_assert_every1000_1bit.log`,
`…-probe-mcw_control_every50_1bit.log`) are the level-4 runs and carry only the totals.

---

## 3. Prior repairs touching this component, and how to try to break them

| repair | what it is | how I would try to break it |
|---|---|---|
| **F04** (`c2f1dcd`, RESOLVED-BY-GLOBAL-GUARD) | the 4096 refusal is left in place; the 10^6 intake makes it unreachable | (a) `-l <index>,<samples>` with samples < 4096 — the intake comment at non_iid_main.cpp 317-320 says it checks "the count actually loaded (which a -l subset request can make smaller than the file)", so this should refuse; verify with a run. (b) `EA_ALLOW_SHORT_DATASET=1` at L = 4095 vs 4096 on an input where MultiMCW would bind (§4 E5 scaled down): the 4095 run must show the min rising and `literalEstimateNotRun` in JSON. (c) Bitstring path: needs `blen < 4096` with `len ≥ 10^6` — impossible. |
| **F05** (`dfe325a`, not-run flags) | −1 sets `literalEstimateNotRun`/`bitstringEstimateNotRun` in JSON | `restart_main.cpp` 1014-1025 was not given the flag; check whether `ea_restart` can ever hand MultiMCW fewer than 4096 samples (matrix dimension validation) — if yes, the F05 repair has a hole; if no, record it as a coverage gap only. |
| **F13 ordering comment** (OC-58) | `min(1.0, NaN)` unreachable because N = 1 is the only NaN source | Try to make N = 1 via `-l` or short-dataset: MultiMCW needs len ≥ 4096 so N ≥ 4033 — cannot. Try `C/N` NaN: impossible (N > 0). Stands. |
| **D-1 / F07** ZALPHA | binary64 quantile, deliberate | Nothing to break; recompute P' from the printed P_global and N with 2.576 and record the +delta per run (the differential driver should carry a `z` switch). |
| **F08** x to convergence | deliberate | Reference with exactly x_10 vs the tool's P_local; expect agreement to ≤ 1e-12 on every corpus file; any larger gap would falsify the "immaterial" argument in §2.3. |
| **F24** | NaN/−inf at x = 1/p, decision unchanged | Repeat §2.7 at 10^6 (M ≈ 38,000 gives (r+1)(1−P') ≈ 0.49) and on x86-64 CI (80-bit long double: redo the half-ulp argument); run under UBSan (`-fsanitize=undefined` reports nothing for NaN itself, but `assert` abort would show as SIGABRT). Execution phase, heavy. |
| **F25 / OC-116** | bisection envelope ~ulp(1)·(N+1)/\|dF/dp\| | Find the input that MINIMISES \|dF/dp\| at the root among binding cases (dF/dp ≈ −0.01(r/p − 1/q)): small r with P_local binding. Then the envelope could exceed OC-116's 1.8e-9. Still sub-nanobit at N ≤ 8e6 by the formula; measure, do not assume. |
| **known-platform-deltas.txt** rows for MultiMCW | 1e-9 tolerance, observed 1.25e-10 / 1.86e-10 / 1.55e-10 | A repair to `prediction_estimate_function` (e.g. `log1pl`) would MOVE these rows; the manifest's rule 3 ("every delta row … must actually be observed") would then fail CI — the manifest is a tripwire on this component, not a guard. Do not touch numerics (memory: hard rule). |

---

## 4. Edge-case inputs that separate a correct from an incorrect implementation

Each is stated as a construction; expected outputs are from the text/Table 3, not from the
tool. Where a wrong implementation reports HIGHER entropy, it is marked ▲.

- **E1 ▲ tie-break direction (3-symbol blocks, period 63).** Symbols in blocks
  `(a×21, b×21, c×21)` repeated, 8-bit file, alphabet {a,b,c} (k = 3). 63 = 3·21, so EVERY
  63-window holds exactly 21 of each symbol at every step and step 3a.i for w1 is decided by
  the tie rule alone. (A period-6 `(a,a,b,b,c,c)` does NOT tie: 63 = 10·6 + 3 gives
  22/21/20.) Correct rule (most recent) predicts s_{i−1}, which equals s_i except at the
  block boundary every 21st symbol → the w1 subpredictor is right 20/21 of the time.
  A "lowest symbol value" or "first in scan order" rule (the classic `>` instead of `>=`
  when scanning symbol counts) predicts `a` → right 1/3 of the time → ≈ 1.585 bits ▲
  against ≈ 0.07 for the text. A "least recent" rule predicts the departing s_{i−63} = s_i
  (period 63) → always right → 0 bits (understates). The 255/1023/4095 windows are not
  tied (255 = 4·63 + 3) and the scoreboard may move `winner` to them, so the exact expected
  C comes from the reference, not from this paragraph; the direction of each wrong rule is
  what the fixture is for. Pure period-3 `(a,b,c)` is the complementary fixture: all four
  windows tie (63, 255, 1023, 4095 are all multiples of 3), the text's rule predicts
  s_{i−1} ≠ s_i → C = 0 → the P_global = 0 branch → floored at 1/3 → 1.585 bits, while a
  "least recent" rule is always right → 0 bits.
  MEASURED through the verified transcription at L = 20,000 with the real windows
  (`logs/analysis-multimcw-e1-fixture.log`; entropy from P' and 1/k only, P_local not
  applied): period-63 blocks — correct rule C = 18987, r = 21, P' = 0.956236, 0.0646 bit;
  lowest-value-tie mutant C = 17865, P' = 0.90164, **0.1494 bit ▲** (the ▲ is smaller than
  the 1.585 a w1-only analysis suggests because the scoreboard moves `winner` to the untied
  255/1023/4095 windows). Period-3 — correct C = 0, r = 1, 1.585 bit; lowest-value mutant
  C = 6646, P' = 0.34195, 1.5481 bit (understates). So period-63 blocks is the ▲ fixture
  and period-3 the complementary one.
- **E2 window-activation boundaries.** Random 8-bit data of exactly L = 4096, 4097, 4158 and
  4159 (fork minimum, +1, 63+4095, +1), `EA_ALLOW_SHORT_DATASET=1`. Reference must agree on
  N = L − 63 and on C, r exactly. An off-by-one in `i >= W[j]` or in the initial window
  (`data[0..W[j]-1]`) shows up as a C difference at these lengths and nowhere else.
- **E3 scoreboard `≥` at a tie.** Drifting-majority data: 300 symbols of mostly-0 then
  mostly-1 then back, with noise, so the 63- and 255-windows disagree right after each change
  point and tie on the scoreboard before it. `>` instead of `≥` keeps the winner on the
  smaller (faster-adapting) window → more correct predictions → LOWER entropy; the reverse
  error (always prefer larger j) → higher ▲. Reference comparison on C decides.
- **E4 ▲ P_local must bind (Table 3 check).** 10^6 one-bit samples: alternating `0,1`
  everywhere (the 63-window majority is s_{i−1}, so no prediction is ever right) except one
  embedded block of exactly B zeros at position 500,000. Inside the block the majority flips
  to 0 after ~32 zeros and stays right for the remaining ≈ B − 32 positions, so r ≈ B − 31
  (tune B so the printed r hits a Table 3 row, e.g. r = 100 or 1000). Then C ≈ r − 1,
  P' ≈ 1e-3, and P_local from Table 3 (r = 100 → 0.8398, min-entropy 0.2519; r = 1000 →
  0.9860, 0.0203 bits). An implementation that drops P_local, forgets the +1 in r, bisects
  the wrong way, or clamps to curMax reports ≈ 1.0 bit instead ▲ — the largest single
  overstatement this estimator can produce. (Execution phase: 10^6 samples.)
- **E5 ▲ r off-by-one at small r.** 20,000-sample 1-bit file built so the longest correct
  run is exactly 1 (e.g. E1-style alternation with isolated single matches): r must print as
  2 and P_local as Table 3's 0.0001-order value (cannot bind, k = 2). If r printed 1,
  the P_global = 0 analysis and any P_local comparison would shift one row ▲.
- **E6 the x → 1/p regime (F24 / live asserts).** n zeros with a 1 every M (this phase: 12
  files ≤ 20,000, §2.7). At 10^6: M = 38,000 → P' ≈ 1 − 1.3e-5, (r+1)(1−P') ≈ 0.49, fast
  convergence. Expected: finite or −inf/NaN F, "P_local can't change the result", exit 0,
  min-entropy ≈ −log2(P') ≈ 1.9e-5 bit. A crash is the failure mode (MEDIUM), not a number.
- **E7 P' cap.** All-constant file (k would be 1 → refused at intake), so instead
  999,999 zeros and one 1 at position 0: P_global = 1 exactly for N = 10^6 − 63 → P' =
  min(1, 1 + 0) = 1 → 0 bits. Any implementation whose P' exceeds 1 yields log2 of a number
  > 1 → NEGATIVE entropy; the fold `min(ret, H)` would then carry a negative into the
  assessment (understates, but shows the cap is missing).
- **E8 F04 at the boundary.** The E4 construction scaled to L = 4095 and 4096: at 4095 the
  Literal MultiMCW line must be absent and `literalEstimateNotRun: true` present; the
  assessed min must be ≥ the 4096 run's. Test-only path (`EA_ALLOW_SHORT_DATASET=1`).
- **E9 8-bit Bitstring path.** 125,000 bytes → blen = 10^6, so the Bitstring MultiMCW runs
  at N = 999,937 with k = 2 while the Literal runs at N = 124,937 with k ≤ 256. Verify the
  Bitstring estimate is multiplied by 8 only at the fold (non_iid_main.cpp 636), and that
  `-t` truncation leaves N = MIN_SIZE − 63 when `blen > MIN_SIZE`.

---

## 5. Suspected deviations — summary with direction and confidence

1. ZALPHA 2.5758… vs printed 2.576 — DOCUMENTED DIVERGENCE D-1/F07; overstates ≤ 3.8e-6 bit
   (Literal 8-bit), 8.7e-8 (Bitstring); high confidence; not a finding.
2. Recurrence iterated to convergence vs x_10 — DOCUMENTED F08; neutral (sign-of-decision
   argument §2.3); high confidence; verify numerically in the differential.
3. P_local solved only on [curMax, 1] and only when it can bind — neutral for min-entropy;
   affects only which verbose lines exist; high confidence; driver must tolerate.
4. L < 4096 refusal (F04) — spec runs for L > 63; overstates on the test-only path by dropping
   an estimator; documented FORK-FIXED; high confidence.
5. Live `assert`s in `prediction_estimate_function` in the x → 1/p regime — crash direction;
   LOW confidence that it is reachable (half-ulp argument + 10/10 in-regime instances clean);
   re-test at 10^6 and on x86-64.
6. P_local 53-bit long double envelope — DOCUMENTED OC-116; two-sided; ~1e-9 in P_local at
   N = 8e6; nondeterministic across platforms (manifest rows); not a finding.
7. `ea_restart` MultiMCW: −1 dropped with no not-run flag (F05 gap) — overstates in principle,
   unreachable at 1000×1000; medium confidence it is a coverage gap, low that it matters.
8. 1/k uses observed alphabet, not the declared one — understates/neutral; upstream behaviour;
   high confidence.
9. Refusal message "need more than 4096" vs enforced "at least 4096" — LOW, part of F04.

No path was found by which this component lowers max(P'_global, P_local, 1/k) below the
text's value beyond items 1 and 6, both documented and both ≤ 4e-6 bit.

## 6. Logs written this phase

- `logs/analysis-multimcw-e1-fixture.log` (E1 directions through the transcription)
- `logs/analysis-multimcw-xcheck.log`, `…-xcheck-mutant.log` (equivalent mutant),
  `…-xcheck-mutant-m1.log`, `…-xcheck-mutant-m2.log`
- `logs/analysis-multimcw-probe-mcw_assert_every1000_1bit.log` and
  `…-probe-mcw_control_every50_1bit.log` (verbosity level 4 — totals only)
- `logs/analysis-multimcw-probe-mcw_assert_every1000_1bit-v3.log`,
  `…-probe-mcw_control_every50_1bit-v3.log` (level 3, with the MultiMCW labels)
- `logs/analysis-multimcw-probe-assert-sweep.log` and twelve
  `logs/analysis-multimcw-probe-sweep_n<N>_M<M>.log`
- Inputs (scratchpad, not committed): sha256 of the two named files are in the level-3 logs'
  first line; all are deterministic (`n` zero bytes, byte `1` at positions M−1, 2M−1, …).
