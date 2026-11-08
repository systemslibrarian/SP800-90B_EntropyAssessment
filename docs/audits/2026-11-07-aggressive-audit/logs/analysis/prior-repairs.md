# Attack map for the prior repairs — analysis phase, 2026-11-07

Component: every fork repair in `NOTICE` and `audits/2026-09-30/FINDINGS-TRACKER.md`
(F02..F19, N-01..N-11, R-1..R-3, NOVEL-01..03, C-01, C07/C03 via the tag, C08, C14,
C16, C18, C23, C24, A04..A08), what each one guards, the regression script that
covers it, and how to try to get around it.

Branch `audit/2026-11-07` at `a2c3c81`. Binaries read (sha256):

```
1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  cpp/ea_non_iid
22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  cpp/ea_iid
4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  cpp/ea_restart
```

Host: Darwin arm64, Apple clang (BSD `getopt`, 53-bit `long double`). Everything
about glibc permutation or LLP64 below is SOURCE-CONFIRMED only, not executed.

Files read in full: `NOTICE`, `FINDINGS-TRACKER.md`, `FORK-DIVERGENCE-AND-TRUST.md`
§A/A.3/B/D, every `cpp/selftest/regression-*.sh` header and the bodies of the
tool-facing scripts, `cpp/shared/{utils.h,TestRunUtils.h,test_run_base.h,
test_case_base.h,lrs_test.h,most_common.h}`, `cpp/non_iid_main.cpp`,
`cpp/iid_main.cpp`, `cpp/restart_main.cpp`, `cpp/non_iid/*.h`,
`cpp/iid/{chi_square_tests.h,permutation_tests.h,iid_test_case.h,iid_test_run.h,
permutation_test_result.h}`. Spec pages 17–25, 43–47, 48–65 of
`reference/sp800-90b.pages.txt`.

Probes run (tiny, `EA_ALLOW_SHORT_DATASET=1`, `OMP_NUM_THREADS=2`, 10,000-sample
fixture `bin/rand8_short.bin` sha256 `17d2eaf9…2803`): one log,
`logs/analysis-prior-repairs-c14-order-probe.log`. Nothing else was executed.

---

## 1. The spec clauses each repair cites, transcribed

The component is cross-cutting, so this section transcribes the exact clauses the
repairs lean on rather than one estimator's algorithm. Each is quoted and paged.

### 1.1 Intake (F03, F04, F11, F12, F15, F16 via `c2f1dcd`)

SP 800-90B §3.1.1 item 1 (PDF p. 19): *"A sequential dataset of at least 1 000 000
sample values obtained directly from the noise source (i.e., raw data) shall be
collected for validation. … The concatenated dataset shall contain at least
1 000 000 samples."*

§3.1.1 item 2 (PDF p. 19): *"a conditioned sequential dataset of at least 1 000 000
consecutive conditioning component outputs shall be collected for validation. The
output of the conditioning component shall be concatenated in the order in which it
was generated and treated as a binary string for testing purposes."*

§3.1.1 item 3 (PDF p. 19): *"the entropy source must be restarted 1000 times; for
each restart, 1000 consecutive samples shall be collected … stored in a 1000×1000
restart matrix M."*

Constants: 1,000,000 samples (sequential), 1000 × 1000 (restart). No tolerance.

### 1.2 Initial estimate and the bitstring (F01 withdrawn; gates for every
bitstring branch)

§3.1.3 (PDF p. 20): *"If the sequential dataset is not binary, an additional entropy
estimation (per bit), denoted H_bitstring, is estimated. First, the sequential
dataset that contains L samples (each having n bits) is considered as a bitstring of
size nL. The bits after the first 1 000 000 bits may be ignored. … Then, the entropy
per sample is estimated to be n×H_bitstring. The initial entropy estimate of the
noise source is calculated as H_I = min(H_original, n×H_bitstring, H_submitter) for
non-binary sources and as H_I = min(H_original, H_submitter) for binary sources."*

§6.2 (PDF p. 49): the ten estimators, then *"The Collision, Markov and Compression
estimates are only applied to binary inputs."*

§6.1 (PDF p. 48): *"For sources with IID outputs, the min-entropy estimation is
determined using the most common value estimate described in Section 6.3.1."*

### 1.3 Restart (R-2, R-3, N-04, C16, C23, C-01)

§3.1.4.2 (PDF p. 21): *"First, the sanity check described in Section 3.1.4.3 is
performed on the matrix M. If the test fails, the validation fails and no entropy
estimate is awarded. If the noise source does not fail the sanity check, then the
entropy estimation methods … are performed on the row and the column datasets … Let
H_r and H_c be the resulting entropy estimates … If the minimum of H_r and H_c is
less than half of H_I, the validation fails, and no entropy estimate is awarded.
Otherwise, the entropy assessment of the noise source is taken as … min(H_r, H_c,
H_I)."*

§3.1.4.3 steps 1–5 (PDF p. 22): *"1. Let p = 2^−H_I. Let α be 0.000 005. 2. For each
row … Set X_Ri to the highest count value for row i. Let X_R be the maximum … 3. For
each column … X_C … 4. Let X_max = max(X_C, X_R). 5. Calculate P(X ≥ X_max) =
Σ_{j=X_max}^{1000} C(1000,j) p^j (1−p)^{1000−j}. If Pr(X ≥ X_max) < α, the test
fails. Otherwise, the test passes."*

Bound direction: the test fails when the tail probability is BELOW α (the observed
maximum is too large). α = 5e-6 per experiment, 0.01 overall.

### 1.4 Conditioned data (N-02, F20)

§3.1.5.2 (PDF p. 25): *"the entropy of the conditioned sequential dataset (as
described in item 2 of Section 3.1.1), which shall be computed using the methods
described in either Section 6.1 (for IID data) or Section 6.2 (for non-IID data).
Let the obtained entropy estimate per bit be h'. The output of the conditioning
component (n_out) shall be treated as a binary string, for purposes of the entropy
estimation. … h_out = min(Output_Entropy(n_in, n_out, nw, h_in), 0.999 n_out,
h'×n_out)."*

### 1.5 IID battery (N-01, #153, #252, R-1, C18)

§5.2.3 (PDF p. 46): *"2. Find the maximum integer m such that min(p0, p1)^m ⌊L/m⌋ ≥
5. If m is greater than 11, set m = 11. If m is 1, the test fails. … The test is
applied if m ≥ 2."* and *"The test fails if the test statistic T is greater than the
critical value of chi-square with 2^m − 2 degrees of freedom, when the type I error
is chosen as 0.001."*

§5.2.5 (PDF p. 47): *"1. Find the proportion p_i … 2. Calculate the collision
probability as p_col = Σ p_i². 3. Find the length of the longest repeated substring
W … 4. … the number of pairs of overlapping subsequences is C(L−W+1, 2). 5. Let X be a
binomially distributed random variable with parameters N = C(L−W+1, 2) and a
probability of success p_col^W. Calculate … Pr(X ≥ 1) = 1 − (1 − p_col^W)^N. The test
fails if Pr(X ≥ 1) is less than 0.001."*

Bound direction: fails when Pr(X ≥ 1) < 0.001 (the observed repeat is too long for
the collision probability). Mathematically p_col ≥ 1/k by Cauchy–Schwarz, with
equality at uniform.

### 1.6 Estimator-level guards (F11, F12, F15, F16, F09, F14, F05)

§6.3.2 step 5 (PDF p. 50): *"σ̂ = sqrt( (1/(v−1)) Σ_{i=1}^{v} (t_i − X̄)² )"* — needs
v ≥ 2. Step 8 (PDF p. 51): *"If the search does not yield a solution, then the
min-entropy estimation is: min-entropy = log2(2) = 1."*

§6.3.4 step 2b (PDF p. 54): *"Use the remaining v = ⌊L/b⌋ − d observations … for
testing."* Step 5: *"σ̂ = c · sqrt( Σ(log2 D_i)²/(v−1) − X̄² ), c = 0.5907"* — needs
v ≥ 2. Step 8 (PDF p. 55): *"If the search does not yield a solution, then the
min-entropy estimation is: min-entropy = 1."* Step 4b.ii: D_i is a block INDEX,
hence must hold the full range of i (F14).

§6.3.6 step 2 (PDF p. 56): *"If v < u, this estimate cannot be computed."* (F05's
compliant-input case; R-2's sentinel.)

§6.3.7 step 1 (PDF p. 57): *"Let window sizes be w1=63, w2=255, w3=1023, w4=4095,
and N = L − w1."* Step 3a.ii: *"Else, let frequent_j = Null."* (F04: defined for L >
63; the code requires L ≥ 4096.)

§6.3.9 step 1 (PDF p. 61): *"Let correct be an array of N values, each initialized to
0."* Step 4.d: *"If (prediction = s_i), let correct_{i−2} = 1."* Worked example (PDF
p. 62): rounds i=3,4 show `prediction Null, correct 0`. (F09.)

### 1.7 Output integrity (N-09, C08, C14, A04, A05, F03, F04, C24, OC-104)

No spec clause; these repairs enforce the project's own statement (NOTICE,
2026-10-19 entry): *"After any run, including an abort, the file is either this
run's report or a report saying the assessment did not complete. It is never a
stale success."* That sentence is the contract tested in §3 below.

---

## 2. Where each clause lands in the code, and where the code departs

| Clause | Code | Agreement |
|---|---|---|
| §3.1.1 item 1, 1e6 | `utils.h:dataset_meets_minimum():294-317` (`MIN_SIZE` 42); called `non_iid_main.cpp:320`, `iid_main.cpp:320` after `read_file_subset`, on `dp->len` (the LOADED count, so `-l` subsets are checked) | agrees; `EA_ALLOW_SHORT_DATASET` must be exactly `"1"` (`strcmp`, :300); flag `nonCompliantShortDataset` emitted `test_run_base.h:73-75` |
| §3.1.1 item 3, 1000×1000 | `restart_main.cpp:694` `if (data.len != MIN_SIZE)` — exact, no escape | agrees (stricter: exact) |
| §3.1.3 min() | `non_iid_main.cpp:632-641`; `iid_main.cpp:455-463` | agrees. Gate for bitstring branches is `data.alph_size > 2 \|\| !initial_entropy` (F01 withdrawn, documented) |
| §3.1.3 "first 1 000 000 bits may be ignored" | `-t` → `data.blen = MIN_SIZE` at `non_iid_main.cpp:344`, `iid_main.cpp:343`, applied also under `-c` (F20 NOT-A-BUG, documented) | agrees for `-i`; `-c` is the documented F20 position |
| §6.2 binary-only | Collision/Markov/Compression literal branch gated `initial_entropy && data.alph_size == 2` (`non_iid_main.cpp:400,424,448`); restart `data.alph_size == 2` (`:883`) | agrees |
| §3.1.4.2 sanity then H_r/H_c then min < H_I/2 | sanity `restart_main.cpp:810-826`; estimators 858-1089; `if (min(H_r, H_c) < H_I / 2.0)` :1177; final `min(min(H_r,H_c),H_I)` :1222 | agrees |
| §3.1.4.3 steps 2–4 | `:762-790` | agrees |
| §3.1.4.3 step 5 | `printedBinomialBound()` :74-87 computes the printed tail and is REPORTED (`restartXcutoffPrintedBinomial`); the VERDICT uses `exactMultinomialMaxBound()` :146-150 (`X_cutoff` :754, method string :805) | DOCUMENTED DIVERGENCE C23 (FORK-DIVERGENCE §B). The cutoff takes no `k`: the worst-case configuration assumes ceil(1/p) symbols exist. For an operator-supplied H_I > log2(alph_size) this is a smaller (more conservative) cutoff than any real alphabet of that size could produce; upstream's `simulateBound` would have hit `assert(k_effective <= k)` :303 instead. Direction conservative. |
| §3.1.5.2 "treated as a binary string" | `iid_main.cpp:378-386` `testdata` view; `non_iid_main.cpp` runs bitstring estimators under `!initial_entropy` | agrees (N-02 repair) |
| §5.2.3 m rule | `chi_square_tests.h:475-483` (`pow(min_p,m) * (sample_size / m)`, integer division = ⌊L/m⌋), `:488-499` returns false for m<2; `:663-676` fails the battery | agrees (N-01 repair) |
| §5.2.5 steps 1–5 | `lrs_test.h:len_LRS_test():643-771`; clamp `:674-677` (R-1); log-domain decision `:704,:768-770` (#153); `N = n_choose_2((int64_t)L - W + 1)` `:713` with `utils.h:1027-1030` int64 (C18) | agrees; the decision `W·log p_col ≥ log(−expm1(log 0.999 / N))` is algebraically `Pr(X≥1) ≥ 0.001` |
| §6.3.2 step 5 v≥2 | `collision_test.h:47-50` returns −1.0 for v<2; folded only `if (ret >= 0)` `non_iid_main.cpp:391,402`, `restart_main.cpp:897,904` | agrees (F12 + R-2 guards) |
| §6.3.4 step 2b v≥2 | `compression_test.h:128-131` `num_blocks < d + 2` → −1.0; `dict` is `int64_t` with `static_assert` `:104-108` | agrees (F11, F14) |
| §6.3.6 step 2 v<u | `lrs_test.h:342-346` → `lrs_res = -1.0`; `:155-160` v==0 → both −1.0 (F15) | agrees |
| §6.3.7 L > 63 | `multi_mcw_test.h:16-19` declines below 4096 | DEPARTS (F04), RESOLVED-BY-GLOBAL-GUARD: unreachable at ≥1e6 |
| §6.3.9 Null → correct 0 | `multi_mmc_test.h:141-150` (binary), `:277-287` (generic): `winner_correct` resets the run | agrees (F09) |
| F05: declined estimator visible | `test_case_base.h:37-38,44-47`; set at 16 sites in `non_iid_main.cpp` (grep, this session) | agrees for `ea_non_iid`; `restart_main.cpp` sets it at ZERO sites (grep, this session) — see §3 row F05 |

### 2.1 The combination logic, and what a NaN or −1 would do to it

`non_iid_main.cpp:353-354` initialises `H_original = word_size`, `H_bitstring =
1.0`; every estimator then does `H = min(ret, H)` (`std::min(a,b)` returns `b < a ?
b : a`). Eight estimators are guarded by `if (ret >= 0)` (false for −1 AND for NaN,
which then sets `*_not_run` and is dropped). Two are unguarded: `most_common`
(`:365-368,:372-375`) and `markov_test` (`:418-421,:425-428`). Checked each:

- `most_common.h:30` `ubound = min(1.0, pmax + ZALPHA*sqrt(pmax*(1-pmax)/(len-1)))`
  — argument order keeps NaN out (OC-58); `len ≥ 2` always (alph ≥ 2 ⇒ len ≥ 2).
- `markov_test.h:70-103`: every `log2()` argument is guarded `> 0.0` and the
  implication P_0X > 0 ⇒ P_0 > 0 holds (comment :66-67, verified: P_0 counts all
  zeros including the last symbol, so C_0 > 0 ⇒ P_0 ≥ 1/len). P_1 ≥ 1/len whenever
  C_1 > 0. No NaN. If no branch fired, `H_min` stays 128 and `entEst =
  fmin(1.0, 1.0)` — unreachable for a two-symbol string of length ≥ 2.
- `collision_test.h:56` `sqrt((Σt² − (Σt)²/v)/(v−1))`: non-negative by
  Cauchy–Schwarz; `Σt² − (Σt)·X̄` with `X̄ = Σt/v` in double is exact for the
  alternating case (Σt² = 9v, X̄ = 3.0) so gives exactly 0, not −ε. No NaN.
- `compression_test.h:153` `sqrt(Σx²/(v−1) − X̄²)`: `Σx²/(v−1) ≥ Σx²/v ≥ X̄²`, and
  the gap `Σx²/(v(v−1))` is ~1e-5 relative for v ≈ 1.6e5 — far above rounding. No
  NaN for v ≥ 2.
- `predictionEstimate` (`utils.h:1200-1256`): `curMax ≥ 1/k > 0`, `entEst =
  −log2(curMax) ∈ [0, log2 k]`. No NaN, never negative (−0.0 passes `>= 0`).

So at ≥ 1e6 samples with alph ≥ 2 nothing reaches the unguarded folds as NaN, and a
hypothetical NaN in a guarded estimator is DROPPED and flagged, not propagated. The
F13 closure (OC-58) holds on this reading. `h_assessed = min(h_assessed,
H_bitstring*word_size)` at `:636` would keep `h_assessed = word_size` if
`H_bitstring` were NaN — the one place where a NaN would OVERSTATE — but no producer
exists; this is the mechanism to keep in mind if any estimator ever gains a NaN path.

### 2.2 `ea_iid -c` aliasing, checked

`iid_main.cpp:380-381` sets `testdata.symbols = testdata.rawsymbols =
data.bsymbols` (the same pointer). `FYshuffle` (`utils.h:869-879`) swaps `data[r]`
and `rawdata[r]` with the same `r`; on one shared buffer the second swap would undo
the first and every permutation would be the identity — a vacuous battery that
always passes. It is NOT so: `permutation_tests.h:633-644` copies `dp->symbols` and
`dp->rawsymbols` into two separately allocated buffers per thread before shuffling,
so the two copies receive the same permutation and the statistics are genuine. The
initial `run_tests(dp, dp->symbols, dp->rawsymbols, …)` at `:608` reads the shared
buffer read-only. N-02's repair (`134d377`) holds here; recorded because the
aliasing is one `new[]` away from being the defect.

---

## 3. The attack map: each repair, what it guards, who covers it, how to get around it

Legend for "break attempts": each bullet is a concrete variation (width, flag,
entry point, size, path). **VERIFIED** = read to the line or executed this session
and found closed. **OPEN** = not closed by code or script; the gap is stated.
**REPRODUCED** = executed this session and the gap is real.

### F03 / F04 / F11 / F12 / F15 / F16 — the §3.1.1 intake check (`c2f1dcd`)

Guards: `dataset_meets_minimum()` refuses `len < 1,000,000` in `ea_non_iid` and
`ea_iid`, after the subset is loaded. `ea_restart` requires exactly 1e6
(`restart_main.cpp:694`). Script: `regression-minsize.sh` — both tools on
`rand8_short.bin` (8-bit, 10,000), `-l 0,5000` on `ea_non_iid` only, escape flag
in text and JSON.

- `ea_iid -l 0,5000 long.bin` — same shared code path (`iid_main.cpp:287,320`);
  the script tests only `ea_non_iid`. VERIFIED by reading; coverage gap only.
- `-c` on 125,000 packed bytes = 1e6 conditioned bits: refused (len counts bytes).
  Fail-closed; consistent with "1 000 000 consecutive conditioning component
  outputs" when an output is one byte. VERIFIED.
- `EA_ALLOW_SHORT_DATASET=true|yes|2`: ignored (`strcmp(allow,"1")`), still refused.
  VERIFIED. The 2026-10-11 audit measured the same.
- 1-bit input with exactly 999,999 bytes: refused. Exactly 1,000,000: assessed.
  `-t` truncation happens AFTER the check (`:344`), so `-c -t` on 1e6 8-bit symbols
  assesses the first 1e6 of 8e6 bits — that is F20 (NOT-A-BUG, documented).
- `ea_restart` with `EA_ALLOW_SHORT_DATASET=1` and 999,000 samples: the variable is
  never read in `restart_main.cpp`; refused by `:694`. VERIFIED.
- Width inferred on a `-l` subset only (`read_file_subset` infers from the loaded
  bytes, `utils.h:458-470`): the subset's `len` still must be ≥ 1e6. VERIFIED.

### F02 — width recorded in JSON (`97571de`)

Guards: `bitsPerSymbol`, `bitsPerSymbolInferred` (`test_run_base.h:76-79`; set
`non_iid_main.cpp:312-313`, `iid_main.cpp:312-313`, `restart_main.cpp:628-631`).
Script: `regression-width.sh` — `truerand_4bit.bin` inferred 4 / declared 8, both
tools; N-08 width spellings.

- `ea_restart` is not in `regression-width.sh`; the field is set (read) but not
  asserted anywhere. Coverage gap only.
- The inference itself is unchanged by design. A `-l` subset whose bytes happen to
  all be < 128 on an 8-bit file infers 7 and the figure changes (F02's measured
  2.4×); the JSON says so. DOCUMENTED.
- "Symbols appear to be narrower than described" (`utils.h:483-485`) sets
  `errorMsg` but leaves `errorLevel = 0`, so `GetBaseJson()` (`test_run_base.h:69`)
  never emits it: the warning is lost in `-q -o` runs. Pre-existing upstream
  behaviour, not a repair regression. LOW.

### F05 — a declined estimator is visible (`dfe325a`)

Guards: `literal_not_run` / `bitstring_not_run` → `literalEstimateNotRun` /
`bitstringEstimateNotRun`, `errorLevel` untouched. Script: `regression-notrun.sh`
— de Bruijn B(100,3) at 1e6 (LRS declines), four clean fixtures carry no flag, a
2000-sample input names Compression and MultiMCW. `ea_non_iid` only.

- **`ea_restart`: OPEN (SOURCE-CONFIRMED).** `grep -n not_run cpp/restart_main.cpp`
  → 0 hits; `cpp/non_iid_main.cpp` → 16 hits. Every fallible fold in
  `restart_main.cpp` (`:897,:904,:937,:944,:972,:978,:991,:997,:1014,:1021,:1035,
  :1042,:1055,:1062,:1076,:1083`) has no `else`. On the R-2 fixture
  (`gen_debruijn.py 100 11`, width 8) the restart JSON omits `lrsRes` for rows and
  columns with no marker, while `ea_non_iid -o` on the same bytes carries
  `literalEstimateNotRun: true`. The figure `min(H_r,H_c,H_I)` is then a minimum
  over fewer estimators than §6.2 lists — exactly the "can only make the figure
  higher" the F05 comment names (`test_case_base.h:26-31`) — and the report cannot
  say so. Direction: neutral on the number, overstating in visibility. LOW-MEDIUM.
  Also raised independently this cycle by `logs/analysis/restart.md` S1 and
  `output.md` 2.9; not in `CLOSING-INVENTORY.md`.
- A NaN from a guarded estimator would set the flag (NaN fails `>= 0`) — fine; +inf
  would pass `>= 0` and be folded. No +inf producer (every estimate is −log2 of a
  value ≥ 1/k). VERIFIED.
- `-c` mode: the flags are set on the bitstring branch too (`:396,:444,…`). VERIFIED.

### F09 — MultiMMC run resets on Null (`69b6094`)

Guards: `winner_correct` in both implementations. Script: `regression-multimmc.sh`
— generic path r=24 on the audit fixture (8-bit, short), binary path against an
inline Python oracle (200,000 bits), `truerand_8bit` still matches refdata.

- Widths 2–7 use the generic path; identical code to width 8. VERIFIED.
- `-c` on multi-bit data drives the BINARY path (alph forced to 2 via the bitstring);
  covered by the 1-bit oracle check. VERIFIED.
- `ea_restart` rows/columns call the same functions (`:1054,:1061`). VERIFIED.
- The generic path's d-loop bound `(i-2 >= d)` excludes d = i−1, which the spec's
  4.b.i would evaluate but whose model M_{i−1} is necessarily empty at round i (step
  4.a.i updates only d < i−1), so subpredict is Null either way. Equivalent.

### F11 / F12 / F15 / F16 — estimator-level guards (`c0ee84a`, `c217f20`,
`21b0a31`, `ed88de9`)

Script: `regression-estimator-guards.sh` — builds its own ASan `ea_non_iid`, L = 4,
5, 8, 12, 16 (binary MultiMMC), v=1 NaN and inf compression inputs, v=1 collision,
repeat-free and tiny inputs, F14 build guard, compression figure vs refdata.

- All reachable only under `EA_ALLOW_SHORT_DATASET=1`. The binary paths are reached
  from 8-bit data under `-c` as well as from 1-bit data; same functions. VERIFIED.
- The ASan build is `non_iid_main.cpp` only: `ea_iid`'s `len_LRS_test` and
  `ea_restart`'s paths are not sanitizer-covered by this script (C-01 has its own,
  `sanitizer-restart-c01.sh`). Coverage gap only.
- `lz78y_test.h` binary path needs `L ≥ B_len+3 = 19`, generic needs `≥ 18`: the
  one-sample asymmetry is commented (`:25-27`) and both are far below 1e6.
- Restart: `collision_test` cannot decline on 1e6 binary samples (needs < 2
  collisions); the guard is there anyway (`:892-901`). VERIFIED.

### F14 — 64-bit compression dictionary (`6b60f9d`)

`static_assert(sizeof(dict[0]) >= 8)`; the script narrows a scratch copy and
asserts the build fails. Unreachable end-to-end here (> 25.8 Gbit). No attack.

### F18 / N-06 / N-07 — regular file, hash status, hash of the consumed bytes
(`cdb5cd6`, `fd83a43`, `c01fb43`)

Guards: `input_path_is_regular()` (`utils.h:250-266`) before `fopen`;
`record_assessed_data_identity()` (`:212-248`) hashes the loaded buffer and sets
`assessedSampleCount`; a hash failure is `errorLevel −1, errorClass internal`.
Scripts: `regression-nonregular.sh` (both tools, four non-regular kinds, absent
file), `regression-restart.sh` N-06 block, `regression-input-identity.sh` (test
build with a SIGSTOP hook).

- `ea_restart` on `/dev/zero`: `read_file()` calls `input_path_is_regular` at
  `:555`; not in any script. Coverage gap only.
- `-l` subset: the hash is of the SUBSET bytes (`sha256Scope:
  assessed-sample-bytes`), by design; the tracker's F19 text ("still hashes the
  whole file") predates `c01fb43` and is stale against the code — the regression
  (`regression-subset.sh` "short-block hash binds consumed bytes") asserts the new
  contract. Documentation drift, not a code defect.

### F19 / N-08 — `-l` overflow, zero, strict decimals (`0e1ffcd`, `031d7ee`)

Guards: `parse_unsigned_decimal()` (`utils.h:51-67`: first char must be a digit, no
sign/space/prefix, `ERANGE` refused, full consumption); `-l` index `,` count
(`non_iid_main.cpp:181-229`); `subsetIndex > ULONG_MAX/subsetSize` (`utils.h:374`);
offset ≥ fileLen (`:385`); `-l index,0` refused (`:214`). Script:
`regression-subset.sh` (seven checks incl. `010` as decimal, `+0,1`, `0,1x`).

- `-l ,5`, `-l 5,`, `-l 5,5,5`: refused at the first/second parse (`end != '\0'`).
  VERIFIED by reading.
- `-l 0,18446744073709551615`: index 0 passes the overflow test, len =
  min(fileLen, huge) = fileLen — assesses the whole file under block 0, which is
  what was asked. VERIFIED.
- `ea_restart` has no `-l` (optstring `invqo:s:`). VERIFIED.
- `-l 0,999999` on a 1e6 file: 999,999 loaded → refused by intake. VERIFIED (same
  code as the script's `-l 0,5000`).

### N-01 — binary chi-square m = 1 fails (`c8799f4`)

Guards: `binary_chi_square_independence()` returns `false` for m < 2;
`chi_square_tests()` fails. Script: `regression-chisquare.sh` — `ea_iid -i`, width 1,
L = 100,000, 999 vs 1200 ones; truerand controls.

- `ea_iid -c` on bytes whose bitstring is extremely biased (e.g. 1e6 bytes of 0x00
  with ~3,000 bytes of 0x01 → p1 ≈ 3.75e-4 over 8e6 bits): same function, alph
  forced to 2 (`iid_main.cpp:383`). VERIFIED by reading; not in any script.
- `ea_restart -i` on a biased binary matrix: `chi_square_tests(rdata, 1e6, 2, …)`
  (`restart_main.cpp:1093-1094`), same function. VERIFIED by reading; not in any
  script.
- Boundary: m = 1 iff `min_p² · ⌊L/2⌋ < 5`; at L = 1e6, `min_p < sqrt(1e-5)` ≈
  3162.3 ones. The tracker's 3162/3163 pair is the right boundary probe.

### N-02 — `ea_iid -c` tests the bitstring (`134d377`)

Guards: `testdata` view (`iid_main.cpp:378-386`), `INT_MAX` guard on `blen`
(`:393-408`). Script: `regression-271.sh` — nibble-duplicate, 10,000 bytes, chi and
LRS verdicts under `-c` fail / `-i` pass.

- Aliasing of `symbols`/`rawsymbols` in the permutation shuffle: VERIFIED closed
  (§2.2).
- `-c -t` on 8-bit: `blen` truncated to 1e6 before `testdata` is built (`:343` then
  `:378`), so `H_bitstring` and the §5 tests see the same 1e6 bits. VERIFIED.
- `-c` on 1-bit data: `testdata == data`. VERIFIED.
- The permutation verdict is seeded from `/dev/urandom` and not asserted by the
  script; only chi-square and LRS are. That half of N-02 has no regression that can
  fail. Coverage gap only (the script header says so).

### N-04 / C16 — `H_I` parse and scale (`db7a2ba`, `a5005bd`→`7a0be01`)

Guards: `parseHIArgument()` (`restart_main.cpp:160-187`: digits, optional fraction,
optional exponent, then exactly `/symbol` or `/bit` or end; `ERANGE` and non-finite
refused); `H_I <= 0` refused (`:581`); bare number refused for `word_size > 1`
(`:640-657`); `/bit` scaled (`:638-639`); `H_I > word_size` refused (`:660`) AFTER
scaling. Script: `regression-restart.sh` — nan/NAN/inf/−inf/abc/1.5x/""/3.2e, −1,
1e-400, 0, 0x1p3, ' 3', '3 ', 3/sym, bare 7 and 3.2 at width 8, 0.875/bit ≡
7/symbol by X_cutoff.

- `1e308/bit` at width 8: value finite, ×8 = +inf, then `inf > 8` → refused. VERIFIED
  by reading.
- `.5/bit`, `5./symbol`, `1e0/bit`: all parse (intDigits or fracDigits ≥ 1). VERIFIED.
- Inferred width + `/bit`: `H_I *= data.word_size` uses the INFERRED width when
  `bits_per_symbol` is omitted (`argc == 2` path). An operator who computed h per
  bit against a declared-8 `ea_non_iid` run and feeds `ea_restart` without the width
  gets `×7` on a stuck-top-bit file. The JSON records `bitsPerSymbolInferred: true`
  so it is detectable; the lower H_I is the EASIER sanity check (larger cutoff) and
  the easier validation (`< H_I/2`), while the reported figure is `min(H_r,H_c,H_I)`
  ≤ the lower H_I. Net: gate easier, number not higher. LOW, documented by the
  `bitsPerSymbolInferred` field. Not in any script.
- `-nan`, `-inf`, `-1` after the operand: `argLooksNumeric()` exempts them from the
  OC-104 refusal; BSD then rejects them in `parseHIArgument` ("not a decimal
  number" / "must be greater than zero"), glibc rejects them in `getopt`. Both
  refuse (REV-004, OC-40). VERIFIED by reading, consistent with the script.

### R-2 / R-3 — restart sentinels and the right report object (`d892b90`,
`23dca69`)

Guards: `>= 0` on every fallible fold in `restart_main.cpp`; the read-failure branch
sets the error on `testRunIid` when `-i` (`:605-620`). Script: `regression-restart.sh`
R-2 (de Bruijn, H_r not −1, validation passes), R-3 (`-i`/`-n` width-4 misdeclare →
errorLevel −1 with message).

- MCV and Markov are unguarded (`:863,:868,:921,:926`) and cannot return −1 or NaN
  (§2.1). VERIFIED.
- In `-i` mode `tcOverallIid.h_r/h_c/h_i` are captured at `:873-875` BEFORE the IID
  battery; on failure they are overwritten with −1 (`:1150-1152`) and omitted. On
  success they are the MCV-only figures, which is what §6.1 prescribes. VERIFIED.
- `tc631Iid` (`:854-861`) is built and never pushed — dead code, harmless.

### NOVEL-01 — selftest compares the final figures (`da0265c`)

Harness only (`compareresults.pl`, `selftest`). Script: `regression-272.sh` with the
two preserved mutants. Not an estimator path; no attack here beyond the harness
agent's remit.

### NOVEL-02 / N-10 — `ea_iid` JSON carries only what was computed (`9f64f62`,
`094189c`)

Guards: `tc.h_original` only under `-i`, `tc.h_bitstring` only when the bitstring
branch ran (`iid_main.cpp:471-477`); `h_assessed` computed outside the verbosity
branch (`:455-463`); `rawMean`/`translatedSymbolMedian`. Script:
`regression-iid-json.sh` — binary `-i` omits `hBitstring`, `-c` omits `hOriginal`,
`-q` hAssessed equals `-vvv` text.

- Under `-c`, `hAssessed = H_bitstring × word_size` (`:458`) and the `-c` test case
  carries no `dataWordSize` (never assigned in `iid_main.cpp`); only the top-level
  `bitsPerSymbol` says what the multiplier was. `ea_non_iid -c` is the same
  (`tcOverall.data_word_size` IS set, `:676`). A consumer reading `hAssessed` from a
  `-c` report as the per-bit h′ of §3.1.5.2 overstates by `word_size`. This is F23
  (UNCONFIRMED in the tracker, upstream-inherited); the text output prints `h'`
  correctly (`:559,:651`). LOW; documented-ish; worth a sentence in the consumer
  contract. Not a repair regression.

### NOVEL-03 — `dataLayout` on permutation results (`25fbb54`)

`permutation_tests.h:484-495`, `populateTestCase(tc, C, dataLayout)`; restart passes
`"rows"`/`"columns"` (`:1127,:1134`), standalone `"input"` (`iid_main.cpp:517`).
Script: `restart-report-label-test.cpp` via `regression-restart.sh`. No numeric
surface. No attack.

### C-01 — `delete[]` (`6f84ad7`)

`restart_main.cpp:333`. `simulateBound()` is now only compiled in under
`EA_RESTART_WITHOUT_C23_FIX` (`:742-747`); the production build never calls it, so
the repaired site is dead code in the shipped binary. The sanitizer script
`sanitizer-restart-c01.sh` therefore exercises a path the shipped tool does not
take; the 2026-10-11 audit already recorded that script's heredoc defect. No numeric
surface.

### #153 / #252 (C07/C03 neighbourhood, via the tag) — IID fails closed, LRS in the
log domain (`a3dde6f`, `007d0e7`)

Guards: `iid_test_suite_pass = chi && lrs && perm` (`iid_main.cpp:529-530`), perm
skipped after a deterministic failure, `errorLevel 2`, no `hAssessed`
(`:534-546`); restart `:1149-1167`. Script: `regression-iid-failclosed.sh` — widths
1–8 at 1e6 with a 2,100-sample duplicated region, restart `-i` on a checkerboard,
truerand positives.

- `-c` with chi pass, LRS fail: perm skipped, suite fails. VERIFIED by reading.
- The duplicated-region fixture is platform-coupled on x86-64 (W ≥ 2100 never
  reaches the underflow there; 2026-10-11 COVERAGE.md). Known.
- `#153` decision: `W·log(p_col) ≥ log(−expm1(log(0.999)/N))` — equivalent to the
  spec's inequality (derivation in §2). VERIFIED. For N ≈ 5e11 the RHS is ≈ −33.8;
  nothing underflows.

### R-1 — clamp `p_col` to 1/k (`0adef7a`)

`lrs_test.h:674-677`. Mathematically exact; raises `p_col` only by rounding (order
1e-17 relative), so `W·log p_col` moves by ≤ W·1e-17 — the decision flips only if it
was within that of the threshold. Direction of the clamp: makes the test slightly
MORE likely to pass (larger p_col^W). Negligible and provably bounded. No attack at
width 1 (k = 2 is exact in binary). VERIFIED.

### C18 — `n_choose_2` in `int64_t` (`473cd5f`)

`utils.h:1027-1030` with `assert(n ≤ INT_MAX)`; argument `L − W + 1 ≤ L ≤ INT_MAX`
by `iid_main.cpp:393`. LP64 here is bit-identical to before. LLP64 not measurable on
this host; the CI job owns it. No attack.

### C23 — exact multinomial cutoff (`7a0be01`)

`restart_main.cpp:113-150`. Script pins 32 H_I values (0.25 … 8, both cutoffs) and
checks deciding > printed at five widths, plus accept/reject at X_max 20/24/28 for
H_I 7. DOCUMENTED DIVERGENCE.

- H_I not on the pinned grid (e.g. 0.696, the device's) is covered by the closing
  record's bisection, not by the script. Coverage note only.
- `kfloor = floorl(1/p)` at an H_I where 1/p is an exact integer in reals but not in
  binary (H_I = log2 3): floorl may give 2 or 3; with 2 the remainder is ≈ 1/3 and
  the configuration is still three ≈-equal cells; with 3 the remainder is ~1e-19 <
  1e-15 and dropped. Same distribution either way. VERIFIED by reasoning.
- The cutoff ignores `alph_size` (see §2 table). Direction conservative for an
  inconsistent H_I. VERIFIED.
- Tiny H_I (p rounds to 1.0L): both bounds return 1000; sanity passes trivially;
  the figure is `min(H_r,H_c,H_I) ≈ H_I ≈ 0`. Conservative.

### C08 / N-09 — checked, atomic report write (`47d6624`, `210aed6`)

`writeJsonReport()` (`TestRunUtils.h:418-611`): identity choke point, random-suffix
temp with `O_CREAT|O_EXCL|O_NOFOLLOW`, `fstat` (regular, owned, `nlink == 1`), full
write + close checked, `rename()`. Scripts: `regression-output.sh` (`/dev/full`,
missing dir), `regression-output-aliasing.sh` (planted symlink at the temp path,
unreadable random source).

- A `-o` that is a symlink to a THIRD file (not the input): `rename(tmp, path)`
  replaces the symlink itself; the target is untouched. POSIX semantics; not a
  destruction path. VERIFIED by reading.
- Three of six `regression-output.sh` cases skip on macOS (no `/dev/full`); the
  write-fails-midway half is Linux-only evidence. Known.

### C14 / A04 / A05 / F03 / F04 / OC-104 — the output-path contract
(`97fbc6c`, `663f9ae`, `de61365`, `b63aff1`, `36cafb3`)

Guards, in execution order (`non_iid_main.cpp:138-159`, same in the other two):
1. `refuseOptionAfterOperand()` (`TestRunUtils.h:363-385`) — any non-numeric
   option-shaped argument after the first operand is refused.
2. `versionOptionRequested()` (`:312-324`) — `--version` honoured only before the
   operand, not after an unknown option or `--`, and never when it is `-o`'s
   argument.
3. `prescanOutputAndOperand()` + `protectInputPath()` + `outputTargetIsSafe()`
   (`:230-271`) — refuse before anything is written if `-o` identifies the input.
4. `claimReportTarget()` inside the `getopt` loop at `case 'o'`
   (`non_iid_main.cpp:230-234`) — fail-closed placeholder written through the
   choke point.
5. `protectInputPath(file_path)` again with getopt's operand (`:263-264`).
6. `writeJsonReport()` refuses any target identical to the protected input.

Scripts: `regression-output.sh` (C14: `-o <stale>` with no operand on all three
tools; a file literally named `--version`; `--version` alone), `regression-output-
aliasing.sh` (46 cases: six alias spellings × three tools, planted temp symlink,
`-o/-vo/-qo/-Z --version`, unreadable random source), `regression-option-order.sh`
(29 checks: `-q`, `-o`, `--version` after the operand refused and named; `--`
honoured; A04 and A05 pair tests).

Break attempts:

- **REPRODUCED — an option error BEFORE `-o` skips the C14 claim and leaves the
  previous success in place.** The claim is bound to `getopt`'s traversal order, so
  any `print_usage()` exit reached while parsing an EARLIER option never claims the
  target. `logs/analysis-prior-repairs-c14-order-probe.log`:

  ```
  CONTROL  ea_non_iid -o stale.json -Z rand8_short.bin 8      rc=255  replaced (errorLevel -1, reportComplete False)
  PROBE A  ea_non_iid -Z -o stale.json rand8_short.bin 8      rc=255  STALE SUCCESS SURVIVED (byte-identical to good.json)
  PROBE B  ea_non_iid -l 5x,10 -o stale.json rand8_short.bin 8 rc=255  STALE SUCCESS SURVIVED
  PROBE C  ea_iid     -Z -o stale.json rand8_short.bin 8      rc=255  STALE SUCCESS SURVIVED
  PROBE D  ea_restart -Z -o stale.json rand8_short.bin 8 3/symbol rc=255 STALE SUCCESS SURVIVED
  ```

  `good.json` was a complete `errorLevel 0` report with 11 test cases
  (`EA_ALLOW_SHORT_DATASET=1` on the 10,000-sample fixture; the escape only matters
  for producing the baseline, the probes themselves exit at option parsing). The
  negative control is the exact shape `regression-output.sh` tests; it passes. The
  probes differ by one thing — the offending option precedes `-o`. All three tools.
  Exit status is nonzero in every case, so a caller that checks the status is safe;
  the file-channel promise in NOTICE ("It is never a stale success") is false for
  this ordering. The 2026-10-11 COVERAGE.md:238 recorded "four paths write no report
  (bad option, wrong arg count, and -l errors when -l precedes -o)" without drawing
  the C14 consequence; `regression-output.sh` cannot see it. The prescan already
  knows `outPath` before `getopt` runs (`scanArgs` fills `s->outPath`), so claiming
  from the prescan result — after `outputTargetIsSafe` — would close it; rule 12
  pairs: A05 (the claim must still go through the choke point), A04, OC-104.
  Severity: MEDIUM (report integrity; overstates only for a consumer that reads the
  report without the exit status — C14's own threat model). Platform: Darwin arm64;
  glibc permutation does not change this (the option is already before the operand).

- **VERIFIED — doubled `-o` whose FIRST value is the input.** `scanArgs` records only
  the LAST `-o` (`:199,:201` overwrite), so `outputTargetIsSafe(preOut)` sees the
  harmless one. `getopt` then reaches the first `-o` and `claimReportTarget("cap.bin")`
  goes through `writeJsonReport`, where `g_protectedInputPath` (armed at `:155`
  from the prescan operand) catches it. Probe E: rc=255, capture sha unchanged,
  `rep.json` absent, stderr names the refusal. The choke point, not the prescan, is
  what holds here — which is the design (`TestRunUtils.h:111-125`).

- `-o -- file 1`: `--` becomes `-o`'s argument in both the prescan (`:200-202`) and
  `getopt`; the file is still the operand and protected. VERIFIED by reading.
- `-o x.json -- x.json 1`: `dashDashAt` set, operand after it, identity refusal
  fires. VERIFIED by reading.
- `-Zo --version data 1`: `rejectAt < versionAt` → no banner; `getopt` rejects `Z`.
  VERIFIED (the `-Z` case is in `regression-output-aliasing.sh`).
- `--version=1`: not `--version`, falls to `getopt` as an illegal cluster → usage.
  VERIFIED by reading.
- `-o--version`: attached argument; a report named `--version` is written. Consistent
  with `getopt`. VERIFIED by reading.
- `-` alone: operand in both walkers. VERIFIED.
- `file 1 -5,10` (option-shaped, not fully numeric): refused by OC-104. `file -0.5`:
  numeric, exempt, then refused by the numeric parsers on both platforms. VERIFIED by
  reading.
- `-o` to a hard link of the input under a different directory: `(st_dev, st_ino)`
  identity. Covered by the aliasing script's `hardlink.bin`.
- Windows (`MoveFileExA`, `GetFileInformationByHandle`): NOT RUN here; CI owns it.

### C24 — Windows rename (`a09c597`)

`#ifdef _WIN32` branch only (`TestRunUtils.h:594-601`). Not exercisable here.

### A06 / A07 / A08 — harness classifiers (`check-platform-deltas.py`,
`known-platform-deltas.txt`, `regression-platform-deltas.sh`)

Not tool code; the harness agent's remit. Read the header only: negatives by
mutation with the baseline asserted accepted (rule 7). No attack here.

---

## 4. Edge-case inputs that distinguish a correct from an incorrect implementation
of these repairs

Each is exact, small enough for the analysis phase where marked, and states the
direction a wrong implementation would err.

| # | Construction | Guards it probes | Correct outcome | Wrong outcome (and direction) |
|---|---|---|---|---|
| E1 | `cp good.json stale.json; ea_non_iid -Z -o stale.json f.bin 8` and `-l 5x,10 -o …`; control `-o stale.json -Z …` | C14 claim ordering | `stale.json` replaced by the placeholder (as the control is) | stale success survives byte-identical with rc 255 — **REPRODUCED**, all three tools |
| E2 | `ea_non_iid -o cap.bin -o rep.json cap.bin 8` | A05 prescan-vs-getopt | rc 255, capture sha unchanged, nothing written | capture truncated (first `-o` claimed) — VERIFIED closed |
| E3 | de Bruijn B(100,3) 1e6 bytes (`gen_debruijn.py 100 11`), `ea_restart -n -o r.json db100.bin 8 0.5/symbol` vs `ea_non_iid -o n.json db100.bin 8` | F05 in restart | both reports mark the LRS literal estimate as not run | restart JSON silently omits `lrsRes` — SOURCE-CONFIRMED (0 flag sites) |
| E4 | 1e6 bytes 0x00 with exactly 3,162 bytes 0x01 at random positions, declared 1; and 3,163 | N-01 boundary | 3,162 → chi-square FAILS (m = 1); 3,163 → m = 2, statistic computed | both pass — IID wrongly accepted (overstates) |
| E5 | 1e6 bytes where byte = 0x00 except ~24,000 bytes 0x80 (bitstring p1 ≈ 3e-3 over 8e6 bits), `ea_iid -c f.bin 8` | N-01 through the `-c` view | `min_p² · ⌊8e6/2⌋` = 9e-6·4e6 = 36 ≥ 5 so m = 2 here; raise bias to ~2,500 bytes (p1 ≈ 3.1e-4, m=1) → battery fails | m = 1 read as pass under `-c` |
| E6 | nibble-duplicate bytes `(x<<4)\|x`, 1e6, `ea_iid -c -o c.json f.bin 8` | N-02 full battery incl. permutation | chi-square and LRS fail; `IID: false`, no `hAssessed` | perm battery vacuous (if the shuffle aliased) → would need chi/LRS to also pass to overstate; they do not |
| E7 | 8-bit full-entropy matrix 1000×1000 (`random.Random(0xF0113E7)`), `ea_restart -n f.bin 8 8/symbol` | C23 direction | sanity passes (deciding cutoff 19 at H_I 8; printed 15) | rejected 83.2 % of the time under the printed formula — documented |
| E8 | same matrix, `ea_restart -n f.bin 8 1e308/bit` | C16 overflow after scaling | refused (`inf > 8`) | accepted → `p = 2^-inf = 0` → division by zero in cutoff |
| E9 | `ea_restart -n f.bin 8 0.875/bit` vs `7/symbol` | C16 scaling | identical `X_cutoff` | differ → scale applied wrongly |
| E10 | 1e6 bytes all < 128, `ea_restart -n f.bin 0.5/bit` (no width) | C16 + F02 interaction | H_I = 0.5×7 = 3.5 with `bitsPerSymbolInferred: true` in JSON | silent ×8 — not a defect, but the JSON field is what makes it detectable |
| E11 | 999,999-byte file; and a 1e6 file with `-l 0,999999`; both tools | intake on loaded count | refused, no `Estimate:` line, errorLevel −1 | assessed — figure for non-conforming data |
| E12 | strictly alternating `0101…` 1e6 bits, width 1 | §2.1 NaN audit of unguarded folds | Collision σ̂ = 0 exactly, X̄′ = 3 → "could not find p" → 1.0 (F06, spec-literal); Markov binds low | σ̂ = NaN → 1.0 unmeasured (the F12 shape) |
| E13 | `printf '\x00\x01' > two.bin; ea_non_iid two.bin` with and without `EA_ALLOW_SHORT_DATASET=1` | F15 + intake | without: refused at intake; with: declines t-tuple/LRS, still reports | abort (rc 134) |
| E14 | 1e6 symbols from 3 equiprobable values (`bal3.bin`), `ea_iid bal3.bin 2` | R-1 clamp | completes; LRS test decided | `assert(p_col >= 1/k)` abort on 117/255 (arm64) or 155/255 (x87) alphabets |
| E15 | `ea_non_iid f.bin 1 -q` on both platforms | OC-104 | refused with the offending `-q` named | glibc assesses, BSD usage-exits — one line, two operations |

---

## 5. Suspected deviations, ranked (the brief's order: overstatement first)

1. **MEDIUM — C14 claim skipped when an option error precedes `-o` (REPRODUCED).**
   `non_iid_main.cpp:230-234`, `iid_main.cpp:227-231`, `restart_main.cpp:444-448`
   (claim inside `getopt`); `print_usage()` exits at `:182-192`, `:236` before the
   claim. Contradicts NOTICE's "never a stale success". Direction: overstates on the
   file channel for a caller that ignores exit status; neutral otherwise. Prior-fix
   interaction: C14, A04, A05, OC-104 (rule 12). Regression gap:
   `regression-output.sh` tests `-o` first only.
2. **LOW-MEDIUM — F05 flags absent from `ea_restart` (SOURCE-CONFIRMED).** A
   declined estimator leaves the restart JSON silent; `min(H_r,H_c,H_I)` is over fewer
   estimators with nothing saying so. Direction: neutral on the figure, overstating
   in visibility. Also raised by `restart.md` S1 this cycle.
3. **LOW — `-c` `hAssessed` is `h′ × word_size` with no per-case `dataWordSize` in
   `ea_iid` (F23, inherited).** `iid_main.cpp:458`. Direction: overstates by up to 8×
   for a consumer that reads `hAssessed` as h′. Documented as UNCONFIRMED in the
   tracker; the text output is correct.
4. **LOW — "narrower than described" warning never reaches JSON** (`utils.h:483-485`
   sets `errorMsg` at `errorLevel 0`; `test_run_base.h:69` gates on `errorLevel`).
   Inherited. Neutral.
5. **LOW — C-01's repaired `delete[]` is in dead code in the shipped build**
   (`simulateBound` only under `EA_RESTART_WITHOUT_C23_FIX`); the sanitizer control
   tests a path the production binary never takes. Neutral; record-only.
6. **LOW — tracker text for F19 ("sha256 still hashes the whole file") is stale
   against `c01fb43`** (hash is of the consumed bytes, `sha256Scope` says so).
   Documentation; the script asserts the current contract.

Nothing found that makes an estimator report a higher figure than its inputs
warrant at ≥ 1,000,000 samples on this host. The two guards that could — a NaN
reaching the unguarded MCV/Markov folds (`:636` keeps `word_size`), and a vacuous
permutation battery under `-c` — were checked to the line and are closed (§2.1,
§2.2).

## 6. What this analysis does not establish

- Anything on glibc (permutation) or LLP64 (C18, C24) — SOURCE-CONFIRMED only.
- Whether the C14 gap is reachable from the January procedure: that invocation
  (`ea_non_iid -vv bin/ringOsc-nist.bin`) has no `-o`, so the file channel is not
  used there.
- F14 end-to-end (> 25.8 Gbit).
- The permutation half of N-02 (non-deterministic, unasserted by any script).
