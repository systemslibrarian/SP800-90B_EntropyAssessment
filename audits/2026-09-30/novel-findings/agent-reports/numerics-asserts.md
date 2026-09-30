# Area report: numerics-asserts

Upstream source: `usnistgov/SP800-90B_EntropyAssessment` at `87c104d`, extracted to `SCR/audit/rel/cpp` (release build) and `SCR/audit/asan/cpp` (ASan/UBSan build). All work files are under `SCR/audit/work/num/` (SCR = `/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad`). The repository was not modified, nothing was written to GitHub, and `gh` was not run. SP 800-90B text: I worked from knowledge of the January 2018 final text because the PDF is not in the repo. Section numbers are cited from that.

**Summary.** I found 5 confirmed novel findings. None moves an entropy figure too HIGH and none wrongly accepts IID. The numerics that decide those directions held under attack (section 6). The findings are:
- 3 aborts or UB on inputs the tool accepts: NUM-01, NUM-02, NUM-04.
- 1 conservative assessment-integrity defect: NUM-03, a false restart failure.
- 1 parameter-reachable abort: NUM-05.

NUM-01 and NUM-03 are leftovers from closed fixes (#246/#248 and #178). They are labelled that way so the coordinator can decide whether to file them as new issues or as reopen requests.

---

## 1. Scope actually covered

**Read in full:**
- `shared/utils.h`: `relEpsilonEqual`, `read_file(_subset)` width inference and translation, xoshiro/`randomRange64`/`FYshuffle`, `sum`, `calc_stats`, `calc_proportions`, `divide`, `prediction_estimate_function`, `calc_p_local`, `predictionEstimate`, `compressedBitSymbols`, `PostfixDictionary`.
- `shared/lrs_test.h`: `sa2lcp32/64`, `calcSALCP32/64`, `SAalgs32/64` for t-tuple and LRS, `len_LRS32/64`, `calc_collision_proportion`, `len_LRS_test`.
- `shared/most_common.h`.
- `non_iid/*.h`: collision, compression (`G`, `com_exp`, bisection), markov, lag, multi_mcw, multi_mmc, lz78y.
- `iid/chi_square_tests.h`: cephes `lgam`/`igam`/`igamc`, binning, all 4 tests, p-value decision.
- `iid/permutation_tests.h`: all 19 statistics, counters, OpenMP loop.
- `restart_main.cpp`: all of it. `conditioning_main.cpp`: all of it. `iid_main.cpp` and `transpose_main.cpp`. The `non_iid_main.cpp` fold and guard logic.

**Conformance table** (numerics only; the estimator logic was already cross-checked by prior agents):

| Section | Algorithm/Test | Step | Code location | Matches? | Notes |
|---|---|---|---|---|---|
| 6.3.1 | MCV | p_u = min(1, p̂+z·sqrt(p̂(1−p̂)/(L−1))) | most_common.h:24-27 | yes | p̂=1 gives −0. Cosmetic. |
| 6.3.2 | Collision | σ̂ with 1/(v−1); X̄′ clamp; closed form | collision_test.h:40-72 | yes | v≤1 is #264. Numerator Σt²−(Σt)²/v cannot go negative (checked analytically). |
| 6.3.3 | Markov | 6 paths, min/128 | markov_test.h | yes | No-path case (H_min=128 → 1.0) only at L=2. |
| 6.3.4 | Compression | σ̂, X̄′, step-8 search, G() | compression_test.h:98-165, 211-317 | yes | Full-entropy exits reachable only with NaN X̄′ (#263). `dict[]` width is F14 (verified below). |
| 6.3.5 | t-Tuple | P_i=Q_i/(L−i+1), P_max=max P_i^{1/i}, p_u | lrs_test.h:229-247 | yes | P_max≤1 exactly, so the sqrt argument is never negative. |
| 6.3.6 | LRS estimate | P_W=ΣC(C_i,2)/C(L−W+1,2), W∈[u,v] | lrs_test.h:262-318 | yes | v<u returns −1. Folding that −1 is NUM-03 (restart). |
| 6.3.7–6.3.10 | Predictors | P_global′, P_local (x recurrence, bisection) | utils.h:842-993 | yes (x to convergence, #133) | All bisection fallback exits are conservative (p=hbound/hdomain). |
| 5.2.1–5.2.4 | Chi-square | T, df, p = Q(df/2, T/2) | chi_square_tests.h | yes | p-value accuracy ≤6.4e-11 rel vs mpmath. df≤0 gives p=1 (vacuous pass). NaN T gives pass (tiny inputs only). |
| 5.2.5 | LRS IID test | Pr(X≥1)=1−(1−p_col^W)^N ≥ 1/1000 | lrs_test.h:617-716 | yes (log1p form) | Asserts at :626 (NUM-01) and :657 (known, #153). |
| 5.1 | Permutation stats | counters C0/C1/C2, >5 rule | permutation_tests.h | yes | Integer statistics are exact. The float excursion cannot create false ties at 10^6. |
| 3.1.4.2/.3 | Restart | X_cutoff (simulation), min(H_r,H_c) < H_I/2 | restart_main.cpp | partial | NUM-03 (−1 folded), NUM-04 (H_I=NaN). |
| 3.1.5.1.2/3.1.5.2 | Conditioning | Output_Entropy (MPFR); h′ from data | conditioning_main.cpp | partial | NUM-02 (all-zero data), NUM-05 (emax assert). |

## 2. Tests actually run (compact)

**Builds.** All were built from a copy in `work/num/src`, using `work/num/build.sh` and the Makefile LIBS. clang builds use a serial `omp.h` stub, because clang-18 has no libomp here; ea_non_iid has no OpenMP pragmas.
- `gcc_nocontract`: g++-13 -O2 -march=native -ffloat-store -ffp-contract=off
- `clang_native`: clang-18 -O2 -march=native
- `clang_fast`: clang-18 -O2 -march=native -ffp-contract=fast
- `clang_sse2_nocontract`: clang-18 -O2 -ffp-contract=off
- `gcc_O0`: g++-13 -O0 -march=native
- `gcc_ndebug_san`: g++-13 -O1 -g **-DNDEBUG** -fsanitize=address,undefined,float-divide-by-zero,float-cast-overflow (ea_non_iid, ea_iid, ea_restart, ea_conditioning)
- `cond_recover`: -DNDEBUG -fsanitize=address -fsanitize-recover=address (ea_conditioning)

**FMA contraction check.** `g++ -std=c++11 -O2 -march=native` does emit `vfmadd` for `a*b+c` on this AMD EPYC (FMA/AVX2), and so does clang-18. This confirms the fork's BUILDING.md claim that upstream's x86 build contracts.

**Differential runs.** `ea_non_iid -vv` on all 11 NIST samples, for each build against the release build's `selftest/*.res`. Every numeric `key = value` line was compared (`work/num/cmp.py`; outputs in `work/num/runs/`):
- `gcc_nocontract`: 27 values differ. The maximum relative difference is **2.2e-13** (truerand_1bit Literal Compression p). The assessed figure differs by at most 6.4e-14.
- `clang_native` and `clang_fast`: **0** values differ.
- `clang_sse2_nocontract`: the same 27 values and the same digits as `gcc_nocontract`, again with a maximum of 2.2e-13.
- `gcc_O0` (6 files: rand1/4/8_short, ringOsc-nist, truerand_1bit, biased-random-bits; the 8-bit files were skipped for time under load average 10–19): 15 values differ, maximum 2.2e-13. It matches the no-FMA builds.
- **Conclusion.** The only compiler-visible factor is FMA contraction. The worst case is truerand_1bit, where the Literal Compression p differs by 2.2e-13 and the assessed figure 0.82967708323411438 vs 0.82967708323406131 by 6.4e-14.
- No decision flipped. Nothing is anywhere near the 1e-9 threshold.

**Other checks:**
- **Thread count.** `ea_non_iid -vv rand8_short.bin` gives byte-identical output with `OMP_NUM_THREADS` = 1, 2, 4. The permutation and restart simulations are stochastic by design (#220/#247), so they were not diffed.
- **Round-toward-zero.** `ea_conditioning` calls `fesetround(FE_TOWARDZERO)` in `main` (conditioning_main.cpp:459), and its `-i` path then runs the full estimator battery in that mode. The harness `work/num/rz.cpp` ran 3000 random (C, N, r, k) through `predictionEstimate` in RN vs RZ: 2509 differ, worst **5.8e-12** relative, and RZ was always the lower (conservative) figure. For ringOsc-nist, truerand_1bit and biased-random-bits, `ea_conditioning -n -i` h′ is identical to `ea_non_iid -c -vv` H_bitstring to 17 digits.
- **Chi-square p-values.** `work/num/chi/chi.cpp` compared `chi_square_pvalue` against `mpmath.gammainc(df/2, x/2, ∞, regularized)` for df ∈ {1…100000} and x from 0 to ∞, including the 0.001 critical region. Worst relative error is 6.4e-11 (df=10^5). Underflow returns 0 (fail); df≤0 returns 1; NaN returns NaN.
- **p_col vs 1/k for balanced counts.** `work/num/pcol.cpp` and `pcol2.cpp` sweep k=2..256.
- **F14 reduced-width.** `work/num/f14/` holds a copy of `compression_test.h` with `dict[]` as `uint16_t`.
- **Assert sweep.** Every `assert(` in `cpp/` was enumerated (104 sites; table in section 5a), classified by reading callers, and the reachable ones were driven with the release build (asserts live) and with `gcc_ndebug_san`.
- **Crafted inputs.** All are in `work/num/inp/`:

| File | Contents | SHA-256 |
|---|---|---|
| bal3.bin | k=3, exactly 333,334 of each, shuffled | `c846814d581b…` |
| bal6.bin | k=6, balanced | `1b870d2f6bfc…` |
| rep2040.bin / rep2100.bin | 10^6 random bytes plus a 2,040 / 2,100-byte copy | `5343b7e9401e…` / `42dc0f2c51b2…` |
| zero1e6.bin | 10^6 zero bytes | `d29751f2649b…` |
| one01.bin | 999,999 zeros and one 0x01 | `2515fe0c5dd2…` |
| ff1e6.bin | 10^6 × 0xFF | `bfa872a3021d…` |
| db256_3.bin | FKM de Bruijn B(256,3) prefix, 10^6 samples | `c5484038e515…` |
| b200.bin, k20.bin, d3.bin | tiny inputs | |

---

## 3. CONFIRMED NOVEL findings

### NUM-01 — ea_iid aborts (no verdict, no JSON) on any dataset whose symbol counts are exactly equal, for 155 of the 247 alphabet sizes that are not powers of two; closed #246's fix (#248) does not cover this

- **Category:** D robustness (+C: IID assessment not produced)
- **Confidence:** HIGH
- **Affected:** `ea_iid`. `ea_restart -i` calls the same code but is not affected, because no failing k divides 10^6.
- **Source:** `cpp/shared/lrs_test.h:len_LRS_test:626` (`assert(p_col >= 1.0L/k)`), fed by `utils.h:calc_proportions:751-762` and `lrs_test.h:calc_collision_proportion:602-609`. Caller: `iid_main.cpp:334`.
- **SP 800-90B:** §5.2.5 (LRS test), §5 IID testing.
- **Valid ≥1,000,000-sample case?** Yes: L = 1,000,002, k = 3.
- **DIRECTION:** none (abort). The IID decision and the MCV figure already computed are discarded.

**Root cause.** With every count equal to c, `p[i] = c / (double)L` rounds `1/k`, and for most k it rounds *down*. Then `p_col = Σ p[i]²` (summed in long double) comes out below `1.0L/k` by about 1e-17. The assert has zero tolerance for a quantity that is only exactly equal to its bound. The #248 fix (counts, then one division) removed the accumulation drift reported in #246, but not this single-rounding case. The trigger does not depend on L; only exact balance and the value of k matter.

k values that fail (all balanced L): 3 6 7 9 12 14 15 17 18 19 21 23 24 27 28 29 30 31 34 35 36 38 39 42 43 46 47 48 49 51 53 54 55 56 57 58 59 60 62 63 67 68 70 72 73 76 78 79 81 84 85 86 87 89 92 94 95 96 97 98 102 103 106 107 108 110 111 112 113 114 116 118 119 120 124 126 127 129 131 133 134 136 137 140 141 143 144 145 146 147 149 152 155 156 158 161 162 165 168 169 170 171 172 173 174 175 177 178 181 183 184 187 188 189 190 192 194 195 196 197 201 204 205 206 207 209 212 214 215 216 217 219 220 222 223 224 225 226 228 229 231 232 233 236 237 238 239 240 248 249 251 252 253 254 255. That is 155 of the 247 alphabet sizes that are not powers of two; powers of two are exact and never fail.

**Minimal reproduction.**
```
python3 -c "
import random; r=random.Random(20260930); a=[i%3 for i in range(1000002)]; r.shuffle(a)
open('bal3.bin','wb').write(bytes(a))"
./ea_iid -v -o bal3.json bal3.bin 2 ; echo $? ; ls bal3.json
```
Even smaller: `printf '\x00\x01\x02' > d3.bin; ./ea_iid d3.bin` (tiny input).

**Actual (run twice, identical).**
```
ea_iid: shared/lrs_test.h:626: bool len_LRS_test(...): Assertion `p_col >= 1.0L / ((long double) k)' failed.
Aborted   exit=134   ls: cannot access 'bal3.json'
```
- Same abort with bal6.bin (k=6).
- Same abort with the clang-18 (FMA and SSE2-no-contract) and gcc no-contract builds.
- With `-DNDEBUG` (sanitizer build), the run completes with no sanitizer report. It prints `P_col = 0.333333333333333296344` (below 1/3), `W = 28`, `Pr(X >= 1) = 0.0216`, then "Chi square tests: Passed", "Length of longest repeated substring test: Passed", "IID permutation tests: Passed", `Assessed min entropy: 1.1662112590438269`, exit=0. So the assert throws away a complete, valid IID assessment; nothing unsafe lies behind it.

**Expected.** §5.2.5 is fully defined here: p_col = 1/k, and the test proceeds to a pass/fail verdict. The JSON report should be written.

**Impact.** A random source essentially never produces exactly balanced counts (about 1e-6 per dataset for k=3 at 10^6). Structured sources do, deterministically: a counter mod k, a shuffled balanced multiset, or cyclic dividers. For a counter the correct outcome is an IID FAIL. For a shuffled balanced multiset a complete assessment exists (the NDEBUG run above passes every test). Either way the shipped build aborts after the chi-square stage and writes no JSON. When stdout is redirected, the buffered output, including the MCV and chi-square results already printed, is also lost. No figure is wrong.

**Dedup.**
- Searched all.md for `p_col`, `calc_proportions`, `1.0L / ((long double) k)`, `balanced`, `equal counts`, `len_LRS_test`. Hits: #246 (same assert; cause identified as rounding, fix #248 changes accumulation), #248, #151/#152/#153 (LRS test precision), #219 (Windows). No item mentions exact balance or a non-power-of-two k.
- Joshua Hill's first idea in #246 ("p_col values sufficiently close to 1/k should just be taken as 1/k") was not implemented.
- This is a reproducible residual of #246 after its fix, on a ≥10^6-sample input. The coordinator should decide between "new issue" and "reopen #246".

**Suggested fix.** Clamp before the check, with an explicit tolerance: `p_col = max(p_col, 1.0L/k)`, or `assert(p_col >= (1.0L/k)*(1 - 8*LDBL_EPSILON))`. Better still, compute p_col exactly as `Σ c_i² / L²` in integer or `__int128` arithmetic.

**Regression test.** bal3.bin and d3.bin must produce a verdict and JSON. Also sweep k=2..256 with balanced counts.

### NUM-02 — ea_conditioning -n -i: an all-zero conditioned-output file (any length, including 10^6 bytes) aborts; with -DNDEBUG it reads out of bounds and makes a wild write

- **Category:** D robustness / B memory-UB (under NDEBUG)
- **Confidence:** HIGH
- **Affected:** `ea_conditioning` (`-n -i`, both `-c iid` and non-IID paths)
- **Source:** `cpp/conditioning_main.cpp:computeEntropyOfConditionedData:364-376/384`. It calls `utils.h:read_file_subset:265-277` (width inference gives `word_size = 0` for all-zero data, so `blen = 0`) and then `most_common.h:14` (`assert(len > 1)`). Under NDEBUG: `markov_test.h:48` (heap over-read) and `lag_test.h:53` (SEGV, write through `ringBuffers[S[0]]` with S[0] read out of bounds).
- **SP 800-90B:** §3.1.5.2 (h′ from the conditioned sequential dataset using §6), §6.3.1.
- **Valid ≥1,000,000-sample case?** Yes (any length).
- **DIRECTION:** none. Abort (asserts live) or memory corruption (NDEBUG). The correct h′ is 0.

**Root cause.**
- For all-zero bytes, width inference returns 0 bits, so the bitstring has length 0.
- ea_non_iid, ea_iid and ea_restart refuse `alph_size <= 1` ("Symbol alphabet consists of 1 symbol…"). `computeEntropyOfConditionedData` has no such refusal and no length check, so it hands a zero-length buffer to every estimator.
- A single non-zero byte removes the problem: `one01.bin` gives `h' = -0` (correct).

**Minimal reproduction.**
```
python3 -c "open('zero1e6.bin','wb').write(bytes(1000000))"
./ea_conditioning -n -o c_zero.json -i zero1e6.bin 512 256 512 256 ; echo $?
./ea_conditioning -n -c iid -o cz_iid.json -i zero1e6.bin 512 256 512 256
```

**Actual.**
- Run twice, identical: `ea_conditioning: shared/most_common.h:14: … Assertion 'len > 1' failed.` then Aborted, exit=134, and no JSON is written. The IID path does the same.
- NDEBUG+ASan: `most_common.h:24 runtime error: division by zero`, `collision_test.h:40/53 division by zero`, then `ERROR: AddressSanitizer: heap-buffer-overflow … READ of size 1 … markov_test.h:48`. With `halt_on_error=0` it continues to `SEGV … lag_test.h:53`.

**Expected.** h′ = 0, because the MCV of a constant bitstring gives p̂ = 1, and therefore h_out = min(Output_Entropy, 0.999·n_out, 0·n_out) = 0. Alternatively, a refusal with errorLevel −1 and a JSON message, as the other tools do.

**Impact.** A stuck or broken conditioner that emits all-zero output is a realistic failure mode. The tool crashes instead of reporting zero entropy. Nothing is over-credited. In a hardened build (-DNDEBUG) the same file gives heap memory corruption.

**Dedup.**
- Searched all.md for `computeEntropyOfConditionedData`, `conditioning` + `zero`/`constant`/`-i`, `word_size = 0`, `all-zero`. Hits: #210 (h′ logic), #211 (leak in `computeEntropyOfConditionedData`), #168 (p_low underflow), #178 (bin_lrs_res guard). None is about degenerate conditioned data.
- #261 covers aborts from *tiny* inputs. This one is a large input with a width inferred as 0, in a tool that lacks the constant-data refusal. #254 covers width narrowing that changes values, not a zero-width empty bitstring.

**Suggested fix.** In `computeEntropyOfConditionedData`, if `data.blen < 2`, or the bitstring has only one symbol, return h′ = 0 (or refuse with errorLevel −1) before calling any estimator. Also treat an inferred width of 0 as width 1 in `read_file_subset`.

**Regression test.** zero1e6.bin under `-n -i` and `-n -c iid -i` must give h′ = 0 (or a JSON refusal) with no sanitizer report.

### NUM-03 — ea_restart (non-IID) folds the LRS "cannot run" sentinel −1 into H_r/H_c, so restart validation fails spuriously; the JSON omits the −1 and the failure is unexplained

- **Category:** C assessment integrity
- **Confidence:** HIGH (mechanism). The trigger is a structured input.
- **Affected:** `ea_restart` without `-i`
- **Source:** `cpp/restart_main.cpp:main:632,636,647,651` (`H_r = min(row_t_tuple_res, H_r)`, `H_r = min(row_lrs_res, H_r)`, and the column versions), with no `>= 0` guard. In the same function, every other estimator that can signal "could not run" (compression, MultiMCW, and also Lag, MultiMMC and LZ78Y) is guarded with `if (ret_min_entropy >= 0)`. SAalgs sets `lrs_res = -1` when v<u (`lrs_test.h:329-331`).
- **SP 800-90B:** §3.1.4.2 (validation: H_r and H_c are the §6.3 estimates on the row/column datasets; fail if min < H_I/2), §6.3.6.
- **Valid ≥1,000,000-sample case?** Yes. Restart data is exactly 10^6 samples.
- **DIRECTION:** TOO LOW (a false restart failure; conservative). In the repro, H_r becomes −1 instead of 0.585, which flips pass to fail.

**Root cause.** This is the same pattern as #166/#177/#178 ("estimators that return < 0 must be ignored"). The #178 fix covered `conditioning_main.cpp` and `non_iid_main.cpp` but not `restart_main.cpp`. t-tuple = −1 is unreachable at L = 10^6 (Q_1 ≥ 35 always holds). LRS = −1 happens whenever v<u.

**Minimal reproduction.** The input is a 10^6-sample prefix of an FKM de Bruijn B(256,3) sequence: no 3-tuple repeats, so v=2, while 2-tuples repeat ≥35 times, so u=3.
```
python3 - <<'EOF'
def debruijn(k,n,limit):
    a=[0]*k*n; seq=[]
    def db(t,p):
        if len(seq)>=limit: return
        if t>n:
            if n%p==0: seq.extend(a[1:p+1])
        else:
            a[t]=a[t-p]; db(t+1,p)
            for j in range(a[t-p]+1,k):
                if len(seq)>=limit: return
                a[t]=j; db(t+1,t)
    db(1,1); return seq[:limit]
open('db256_3.bin','wb').write(bytes(debruijn(256,3,1000000)))
EOF
./ea_restart -vv db256_3.bin 8 0.5
./ea_restart -v -o db_restart2.json db256_3.bin 8 0.5
```

**Actual (two runs; X_cutoff 770 / 769, X_max 589, sanity passed both times).**
```
LRS Estimate: v<u. Can't Run LRS Test.
	LRS Test Estimate (Rows) = -1.000000 / 8 bit(s)
	Lag Prediction Test Estimate (Rows) = 0.585208 / 8 bit(s)      <- true row minimum
	Lag Prediction Test Estimate (Cols) = 1.558172 / 8 bit(s)
H_r: -1.000000
H_c: 1.558172
*** min(H_r, H_c) < H_I/2, Validation Testing Failed ***      exit=255
```
The JSON has `"errorLevel": -1` and `"errorMessage": "min(H_r, H_c) < H_I/2, Validation Testing Failed."`. The LRS test case has no h_r (the −1 is omitted), and every h_r listed is ≥ 0.585, which is above H_I/2 = 0.25.

**Expected.** Skip the undefined LRS estimate, as ea_non_iid does (maintainer position: "<0 = could not run, excluded"). Then H_r = 0.585 and H_c = 1.558, both ≥ 0.25, so validation passes with min(H_r, H_c, H_I) = 0.5.

**Impact.** Only a source whose data has frequent short tuples but no long repeats hits this: de Bruijn-like data, or some deterministic generators with small state. The result is a spurious rejection of the claim. It does not over-credit.

**Dedup.**
- Searched all.md for `restart_main`, `H_r`, `lrs_res`, `v<u`, `-1.000000`, `>= 0`, `ret_min_entropy >= 0`. Hits: #178 (lists conditioning_main.cpp and non_iid_main.cpp lines only), #166/#177 (compression in non_iid), #120 ("v<u should be reported"), #161/#233 (restart semantics).
- No item names restart_main.cpp's t-tuple/LRS folds. This is an unfixed instance of the known #178 family; the coordinator should decide whether it counts as new.

**Suggested fix.** `if (row_lrs_res >= 0) H_r = min(row_lrs_res, H_r);` and the same for the other three folds.

**Regression test.** db256_3.bin with H_I=0.5 passes validation, and H_r = 0.585208.

### NUM-04 — ea_restart accepts H_I = "nan"; the result is a float-to-int UB and an out-of-bounds stack access at index −2^31 (SIGSEGV)

- **Category:** B memory-UB
- **Confidence:** HIGH
- **Affected:** `ea_restart` (all modes; it crashes before any test)
- **Source:** `cpp/restart_main.cpp:main:293-294,343` (`atof`, with `H_I < 0` and `H_I > word_size` both false for NaN). Then `simulateBound:127,132-133` (`p = pow(2,-NaN)`, `k_effective = ceil(1/p)` gives (int)NaN = INT_MIN, and `assert(k_effective <= k)` *passes*). Then `simulateCount:92` (`counts[(int)floor(u/NaN)]++`, index −2147483648).
- **SP 800-90B:** §3.1.4 (H_I is the submitter's initial estimate).
- **Valid ≥1,000,000-sample case?** Yes: any valid restart file.
- **DIRECTION:** none (crash)

**Repro.** `./ea_restart -o r.json bin/truerand_8bit.bin 8 nan`

**Actual.**
- Run twice: `Segmentation fault`, exit=139, no JSON.
- ASan/UBSan build: `restart_main.cpp:132:23: runtime error: -nan is outside the range of representable values of type 'int'`, `restart_main.cpp:92:67: runtime error: index -2147483648 out of bounds for type 'short unsigned int [256]'`, then `AddressSanitizer: SEGV … simulateCount … restart_main.cpp:92`.

**Expected.** A refusal like the one for negative H_I (JSON errorLevel −1). ea_conditioning already does this with `strtold` + `isfinite` (conditioning_main.cpp:70-81).

**Impact.** The command line must contain NaN. That is plausible from a script that pipes an ea_non_iid result that failed to parse (Python formats a missing float as "nan"). The memory access is a read-modify-write of a wild stack address. There is no wrong verdict: it crashes before validation.

**Dedup.** Searched for `atof`, `nan`+`H_I`, `isnan`, `isfinite`, `strtod`, `simulateCount`, `k_effective`. Only #195 is related (k_effective assert when data are narrower than claimed). The NaN path passes that assert. #168 is a NaN *output* in conditioning. Nothing covers NaN input.

**Fix.** Parse with `strtod`, and reject non-finite values or trailing characters.

**Regression test.** `nan`, `-nan`, `inf` and `abc` must each give a usage error with JSON.

### NUM-05 — ea_conditioning aborts on accepted parameter values n_in or n_out ≥ 1,073,741,823 (MPFR default emax)

- **Category:** D robustness
- **Confidence:** HIGH (abort verified). Relevance LOW.
- **Affected:** `ea_conditioning`
- **Source:** `conditioning_main.cpp:main:602-603` (`assert(mpfr_get_emax() > maxval)`). The parser accepts up to UINT_MAX (`:536-542`). Also `precision = 2*maxval` (`:599`) wraps for maxval ≥ 2^31.
- **SP 800-90B:** §3.1.5.1.2.
- **Valid ≥1,000,000-sample case?** Not data-driven; this is a parameter.
- **DIRECTION:** none

**Repro.** `./ea_conditioning -v 1073741823 256 256 256` and `./ea_conditioning -v 512 1073741823 512 256` both print `Assertion 'mpfr_get_emax() > maxval' failed` and abort with no JSON. A huge nw alone is fine, because it is clamped to n_in.

**NDEBUG (analysis, not run: it would need about 7 GB of MPFR storage).** `mpfr_ui_pow_ui(2, n_in)` overflows emax, so it returns a non-zero ternary, so the function recurses with precision doubled, without bound. The result would be memory exhaustion.

**Dedup.** Searched for `emax`, `mpfr_get_emax`, `maxval`, `n_in` + `large`. Hits: #102 (non-integer inputs), #128/#129/#136/#168 (precision, all smaller parameters). None covers this bound.

**Fix.** Reject parameters above `mpfr_get_emax()-1` with a message, or raise emax with `mpfr_set_emax`.

---

## 4. Suspected findings needing more work

- **S-1 — ea_iid narrows the sample count to `int`** (`iid_main.cpp:250 int sample_size = data.len`). Every IID routine then takes `const int sample_size`: utils.h:655/668/751, lrs_test.h:617, chi_square_tests.h, permutation_tests.h. Also `permutation_tests.h:638 for(int i=0; i<dp->len; ++i)` (int overflow UB) and `excursion/FYshuffle(dp->len → int)`. Consequences by reading:
  - For 2^31 ≤ L < 2^32, `sample_size` is negative, so `most_common` asserts (abort). Also `calc_stats` computes rawmean = 0.
  - For L ≥ 2^32+2, the MCV, chi-square and LRS test silently assess only the first `L mod 2^32` samples, the shuffle covers only that prefix, and the copy loop overflows.
  - PR #217/#226 advertises support for more than 2G samples (aimed at ea_non_iid). ea_non_iid is long-clean apart from F14.
  - **Not executed:** a ≥2^31-sample run needs ≥ 6.5 GB (1-bit) to ≥ 17 GB of RAM; this host has 7 GB with about 4 GB free under shared load. Maintainer position #15/#22 (memory limits, LP64 only) may classify it as unsupported. Next step: run on a ≥32 GB host with a 2^32+10^6-byte 1-bit file and compare H_original with `-l 0,1000000`.
- **S-3 (passing observation; belongs to the restart area)** — `restart_main.cpp:123` allocates `results = new uint16_t[simulation_rounds]`, and `:160` frees it with `delete results;`. That is new[]/delete mismatched: invalid C++ and UB on every ea_restart run. ASan's `alloc-dealloc-mismatch` should flag it. Not executed here (the ASan simulation of 5×10^6 rounds is slow under the current load), and there is no all.md hit for `delete results` or `alloc-dealloc`. It is harmless in practice with glibc for a trivially destructible type.
- **S-2 — ea_conditioning `-i` with constant non-zero data** (e.g. 10^6 × 0xFF) is not refused, and the LRS on an all-ones bitstring is Θ(n²). The command was still running at a 120 s timeout (12.6 s CPU under load average 19). This is the F17/#214 family plus the missing constant-data guard from NUM-02; the time was not quantified to completion.

## 5. EXCLUDED AS ALREADY KNOWN

- **IID LRS test aborts on a long repeat** (`lrs_test.h:657 assert(p_colPower >= LDBL_MIN)`). This is #153 item 2 ("p_col^W could be smaller than LDBL_MIN … can be detected"), and the code comment at :650-655 documents the abort. Verified:
  - 10^6 random bytes with a 2,040-byte copy give "Failed" with JSON.
  - A 2,100-byte copy gives Aborted, exit 134, no JSON.
  - Under -DNDEBUG+ASan, the 2,100-byte file gives `W = 2100 … Length of longest repeated substring test: Failed` with no sanitizer report.
  - Added value, if anyone refiles: the verdict is certain (FAIL) whenever p_col^W underflows, so no arbitrary precision is needed.
- **Tiny/repeat-free inputs in ea_iid** hit the #261 family (no minimum-length validation):
  - `iid/permutation_tests.h:256 assert(n>=p)` fires for non-binary L<32 or binary L<249 (b200.bin, k20.bin).
  - `lrs_test.h:658` fires for W=0.
  - Under -DNDEBUG+ASan: a heap over-read at `permutation_tests.h:259`; `chi_square_tests.h:439` and `utils.h:839` divide by zero, so the p-value is NaN and the test passes; the W=0 case makes log1pl(−1) = −inf, so the LRS test passes.
  - `lag_test.h:41`, `markov_test.h:15`, `most_common.h:14` on 1–2-byte ea_conditioning `-i` files; `lrs_test.h:149`, `multi_mmc_test.h:21`, `lz78y_test.h:17/18` belong to #261/#262/#257.
- **Restart `assert(k_effective <= k)`** when H_I > log2(observed k): #195.
- **Compression v=1 NaN / collision v≤1 NaN:** #263 / #264.
- **Prior local audit row now verified: F14** (mechanism, reduced width). `work/num/f14/` holds `compression_test.h` with `dict[]` as `uint16_t` instead of `unsigned int`. Otherwise identical; the bitstring is Bernoulli(0.9).

  | Bits | Blocks | 32-bit dict | 16-bit dict |
  |---|---|---|---|
  | 390,000 | 65,000 | 0.0855227 | 0.0855227 |
  | 394,000 | 65,666 | 0.0855557 | 0.0869327 (starts diverging past 2^16) |
  | 600,000 | 100,000 | 0.0860178 | **1** |
  | 1,000,000 | 166,666 | 0.0860682 | **1** |

  So the truncated D_i do drive the estimator to full entropy once the block index exceeds the stored width. At real width this needs >2^32 blocks (≥25.8 Gbit bitstring, about 26 GB of bsymbols), which is outside the maintainers' supported memory envelope (#96/#228). Direction is TOO HIGH for the compression estimator only; the whole-tool figure rises only if compression was the binding estimator.
- **F13** (NaN folded by std::min): no producer found at any size. Every estimator converts its NaN intermediates to a finite return before returning:
  - collision and compression give 1.0;
  - `predictionEstimate`'s `min(1.0, NaN)` gives 1.0, and `fmax` drops NaN;
  - `markov_test` guards its logs;
  - t-tuple/LRS P_max ≤ 1 exactly.

  Restart's final `min(H_r, H_c) < H_I/2` would pass on a NaN in the last fold, but no producer exists at 10^6. The mechanism is real; reachability is nil. F13 stays theoretical.
- **F24/F08/F25 and the BUILDING.md precision audit** were not duplicated. An additional analytic note: for N ≥ r, the true P(no run ≥ r) ≤ 1 − p^r ≤ 0.63 whenever p > (r+1)/(r+2). So even where the fixed point reaches x = 1/p and pVal becomes −inf, the bisection moves in the correct direction. And bisection points never exceed about 1 − 3.3/r when the guard fires, so the 1/p region, and `assert(p*x <= 1)`, are not reached from data.
- **Chi-square df ≤ 0 gives p = 1** (vacuous pass). The C++ counterpart of py #12/#14. It needs p_max ≳ 1 − 3e-3 (binary m<2) or an equally extreme non-binary skew, where MCV already gives H ≈ 0. Not dangerous.

### 5a. Full assert table (104 `assert(` sites in cpp/)

Legend: **I** = internal invariant, not reachable from input under the tool's own guards. **R-tiny** = reachable only below 10^6 samples (#261 family). **R** = reachable from a valid or large input or a parameter.

| Site | Condition | Class | Minimal input / note | Asserts on | -DNDEBUG |
|---|---|---|---|---|---|
| lrs_test.h:20, :54 | n>1 (sa2lcp) | R-tiny | a 1-byte bitstring from ea_conditioning -i (0x01 aborts at MCV first) | abort | — |
| :87,:88,:89,:90 (dup),:95 | 32-bit SA preconditions; divsufsort rc | I (:95 only on OOM) | :89/:90 are identical duplicates | — | — |
| :102-:110 | 64-bit SA preconditions | I | n ≥ 2^31 only | — | — |
| :130-:133, :352-:355 | n>0, k>0, width, mult-overflow | I | | — | — |
| :140, :362 | L[0]==0 | I | | — | — |
| :149, :371 | v>0 && v<n | R-tiny #261 | 2-byte `\x00\x01`; 256 distinct bytes | abort | continues (then #257 over-reads) |
| :164-:211, :386-:433 | Kaufer algorithm invariants | I | | — | — |
| :221-:223, :443-:445 | u bounds | I | | — | — |
| :279, :501 | A[t] ≥ 0 | I | | — | — |
| :290, :512 | S[t] no-wrap | I (ΣC(c,2) ≤ C(n,2) < 2^61) | | — | — |
| :626 | p_col ≥ 1/k | **R (NUM-01)** | bal3.bin (10^6), d3.bin | abort, no JSON | correct verdict |
| :627, :640 | p_col ≤1, <1 | I | | — | — |
| :657 | p_col^W ≥ LDBL_MIN | R, known #153 | rep2100.bin | abort, no JSON | correct FAIL |
| :658 | p_col^W ≤ 1−ε | R-tiny (W=0) | repeat-free ≤256 samples | abort | log1p(−1) = −inf, test PASSES |
| :669 | log term < 0 | follows :657 | | — | FAIL (correct) |
| utils.h:87-89 | relEpsilonEqual args | I | | — | — |
| utils.h:160 | Bint > Aint | I (equal and sign cases return earlier) | | — | — |
| utils.h:844-845 | 0<p<1 | I (min 1−curMax ≈ 0.18/N ≫ 2^-53) | | — | — |
| utils.h:858 | x monotone | I (contraction dominates rounding by ~(r+1)·2/3) | | — | — |
| utils.h:860 | p·x ≤ 1 | I (1/p region unreachable, see §5) | | — | — |
| utils.h:1007, :1012 | ≤32 bits; S∈{0,1} | I | | — | — |
| utils.h:1047 | curBest>0 | I | | — | — |
| lag_test.h:40, :42 | S≠NULL, k≥2 | I | | — | — |
| lag_test.h:41 | L>2 | R-tiny | ea_conditioning -i on a 1-byte `\x03` file (blen 2) | abort | NUM-02 path: SEGV at :53 |
| lag_test.h:84, :105 | ring buffer | I | | — | — |
| markov_test.h:15 | len>1 | R-tiny (MCV fires first) | | — | over-read :48 (NUM-02) |
| multi_mmc_test.h:21 | L>3 | R-tiny #261 | 3-sample binary | abort | #257 over-read |
| multi_mmc_test.h:22; lz78y_test.h:19 | constants | I | | — | — |
| lz78y_test.h:17, :18 | L>16, L−16>2 | R-tiny #261 | binary 4–18 samples | abort | over-read |
| compression_test.h:29, :30 | d>0, blocks>d | I (caller guard) | | — | — |
| most_common.h:14 | len>1 | **R (NUM-02)** | zero1e6.bin via ea_conditioning -n -i | abort, no JSON | div0, then OOB read/write |
| chi_square_tests.h:385, :433 | sizes | I | | — | — |
| permutation_tests.h:256 | n≥p | R-tiny | ea_iid non-binary L<32, binary L<249 | abort | heap over-read :259 |
| permutation_tests.h:292, :304, :311, :697-:709 | internal | I | | — | — |
| restart_main.cpp:115 | 1<k≤256 | I (alph≤1 refused) | | — | — |
| restart_main.cpp:133 | k_eff ≤ k | R, known #195. **Bypassed by NaN** (NUM-04) | H_I > log2(k) | abort | lower cutoff, no UB |
| restart_main.cpp:152-:156 | simulation bounds | I | | — | — |
| conditioning_main.cpp:64-:71, :100-:105 | parser | I | | — | — |
| conditioning_main.cpp:256, :291 | ψ, ω ≥ 0 | I | | — | — |
| conditioning_main.cpp:602, :603 | emax/emin > maxval | **R (NUM-05)** | n_in or n_out ≥ 1,073,741,823 | abort | unbounded precision recursion (analysis) |
| conditioning_main.cpp:609-:612 | output bounds | I (recursion retries until they hold) | | — | — |

## 6. No-finding areas (attacked and held)

- **Compiler/FMA/optimisation dependence.** GCC FMA vs no-FMA: ≤2.2e-13. clang-18 native/fast: bit-identical to the GCC release build. SSE2 no-contract and -O0 are identical to GCC no-FMA (≤2.2e-13). No decision flips anywhere near threshold. The IID decisions depend on chi-square p-values (accurate to ≤6e-11) and on the LRS log form, so no plausible compile-flag flip exists.
- **Rounding mode.** ea_conditioning's `FE_TOWARDZERO`: estimator deltas are ≤5.8e-12 and always lower (conservative).
- **Root finding.**
  - Every compression-search exit that yields "full entropy" requires a NaN X̄′ (#263 only). X̄′ stays inside [hvalue, lvalue] by construction. All other exits are conservative.
  - All calc_p_local fallbacks are conservative (p = hbound or 1).
  - The guard misfire (1/p root at curMax) happens only where the true probability < 0.99, so it is correct.
- **IID LRS test.** Uses log1pl, and the decision uses logs. The printed Pr(X≥1) suffers cancellation (it prints 0 for tiny values); that is display only.
- **Chi-square.** Extremes underflow to p=0 (fail); igam/igamc recursion is disjoint (no loop); the continued fraction's `relEpsilonEqual(qk,0)` absolute threshold cannot stall (qk ~ x after rescaling).
- **NaN producers at ≥10^6.** None in any executable. NaN reaches the JSON only via the tiny-input families.
- **Integers in the non-IID path.**
  - All lengths are `long`. SA dispatch is correct at 2^31. S[t]/choices are 64-bit with proven bounds.
  - There are no input-controlled shifts: word_size ≤ 8, m ≤ 11, d ≤ 16. VLAs are ≤ 256 entries.
  - Restart indices are fixed at 1000×1000. `-s` huge gives a `new[]` failure and std::terminate (trivial, hostile command line; not reported).
- **Permutation-test float statistic (excursion).** Distinct values differ by ≥ 1/L ≫ rounding at 10^6, so there are no false ties. Integer statistics are exact in long double, and in double on 64-bit-long-double platforms (< 2^53).
- **Thread count.** No effect on deterministic outputs.
- **Restart H_I edge values.** 0, −0, denormal, just below word_size, inf (rejected), text (becomes 0): all safe except NaN (NUM-04).
