# Area "restart" — adversarial audit of `ea_restart` (upstream 87c104d)

Work dir: `SCR/audit/work/restart/` (SCR = the session scratchpad). All inputs, generators, harnesses and raw outputs are there (`data/`, `gen*.py`, `cutoff_ref.py`, `worstcase.py`, `jumpcheck.py`, `src/simcut.cpp`, `asanfast/`). Binaries: `SCR/audit/rel/cpp/ea_restart` (release), `SCR/audit/asan/cpp/ea_restart` (ASan/UBSan), plus a reduced-simulation-rounds ASan copy (`asanfast/`, only `DEFAULT_SIMULATION_ROUNDS` changed, used to get through the full path in bounded time on a machine running at load 11–19).

Spec text: SP 800-90B (Jan 2018) PDF fetched read-only from nvlpubs.nist.gov into the work dir and text-extracted (pypdf); §3.1.1–§3.1.4.3, §6.1, §6.2, §6.3.6 quoted from that text. For dedup, besides `SCR/gh/all.md` and `reports/exclusion-map.md`, I fetched three public PR diffs read-only with curl (`pull/242.diff`, `pull/250.diff`, `pull/252.diff`) to see which files they touch. No `gh`, no GitHub writes. (One accidental side effect, reverted within the minute: a `pip download` wrote `mpmath-1.4.1-py3-none-any.whl` into the repo root because the shell's cwd was the repo; I moved it to the work dir and `git status` is clean again.)

## 1. Scope actually covered

Read in full: `cpp/restart_main.cpp` (all 888 lines); from shared code, the parts restart calls: `read_file`, `free_data`, `seed`, `xoshiro256starstar`, `xoshiro_jump`, `randomUnit`, `calc_stats` (utils.h); `sha256_file` (TestRunUtils.h); `most_common` (most_common.h); `SAalgs/SAalgs32/SAalgs64` return conventions (lrs_test.h); `permutation_tests`, `run_tests` data use, `populateTestCase` (permutation_tests.h); the JSON classes (`test_run_base.h`, `test_case_base.h`, `non_iid_test_run.h`, `non_iid_test_case.h`, `iid_test_run.h`, `iid_test_case.h`); `transpose_main.cpp` orientation. Estimator internals were not re-audited here (the other areas do that). I used the estimators as black boxes and checked metamorphically that the row and column runs reproduce `ea_non_iid`.

Spec comparison: §3.1.1 item 3, §3.1.2 (bullet 3), §3.1.3, §3.1.4, §3.1.4.1, §3.1.4.2, §3.1.4.3, §6.1, §6.2, §6.3.6 step 2.

| Section | Algorithm/Test | Step | Code location | Matches? | Notes |
|---|---|---|---|---|---|
| 3.1.1(3), 3.1.4.1 | restart data | r = c = 1000, M[i][j] = j-th sample of i-th restart; row dataset = file order | restart_main.cpp:170, 389-409, 456 | yes | exact `len != 1,000,000` refusal (tested 999,999 and 1,000,001, both modes: errorLevel −1, exit 255) |
| 3.1.4.1 | column dataset | concatenate columns | :463-474 (`cdata[j*c+i] = rdata[i*r+j]`) | yes | `r == c` hides the i*r vs i*c index form; matches `ea_transpose` byte-for-byte (verified on 10^6 cells) |
| 3.1.4.3 step 1 | p, α | p = 2^−H_I, α = 0.000005 | :127, :444 | **deviates, intended** | α' = 1−0.99^(1/2000) = 5.0251553e-6 (#95) |
| 3.1.4.3 steps 2-4 | X_R, X_C, X_max | per-row / per-column max count; X_max = max | :449-477 | yes | counts on translated symbols; translation is injective |
| 3.1.4.3 step 5 | cutoff | fail iff P_Bin(1000,p)(X ≥ X_max) < α | :445 (`simulateBound`), :479 | **deviates, intended** | tool: fail iff X_max > simulated (1−α') quantile of the max count under the "inverted near-uniform" model (#56/#98/#209/#224). Always ≥ spec U (table in §2) |
| 3.1.4.2 | validation track | §6.1 (IID: MCV only) or §6.2 (non-IID battery) on row and column datasets | :521-541 (MCV), :552-739 (non-IID) | yes (one defect) | literal estimators only; no §3.1.3 bitstring step, correctly: §3.1.4.2 invokes §6.1/§6.2, not §3.1.3. **t-tuple/LRS −1 "cannot be computed" not excluded → RESTART-03** |
| 6.2 | binary-only estimators | Collision/Markov/Compression "only applied to binary inputs" | :554 (`alph_size == 2`) | partly | gate is on the observed alphabet, as in #253; in restart the error direction is only *extra* estimators (conservative) |
| 3.1.4.2 | pass criterion | fail iff min(H_r,H_c) < H_I/2 | :834 | yes | #233 |
| 3.1.4.2 | final value | min(H_r, H_c, H_I) | :882 | yes (text) | not in JSON (see §4) |
| 3.1.2 bullet 3 | IID verification on row+column data | Section 5 tests on both datasets | :740-824 | computed, not gated | results reported but never change the verdict/exit code (#252 family) |
| — | H_I argument | nonneg, ≤ bits_per_symbol | :293-315, :343 | **NaN bypasses both checks → RESTART-01** | inf/−inf/1e400/−0.5/1.0000001 correctly refused |
| — | JSON on failure | errorLevel ≠ 0 | :268-499, :834-853 | **one path wrong in `-i` → RESTART-02** | all other failure paths correct in both modes |

## 2. Tests actually run

Release binary unless noted. "×2" = reproduced in two separate runs.

- **Structured matrices (tool must reject):** `colconst8` (every restart emits the same 1000-sample sequence, so columns are constant): X_cutoff 22, X_max 1000, sanity fail, JSON errorLevel −1. `rowconst8` (each restart emits one constant): same. `shift1` (M[i][j]=S[i+j], symmetric, rows and columns both windows of one 2000-bit sequence): passes sanity (X_max 539 vs cutoff 604) but H_r = H_c = 0.003214, validation FAIL. `altcol1` (M[i][j] = ((i+j)&1)^r_j: balanced rows and columns, alternating columns): sanity passes (529 ≤ 572), H_r 0.000001, H_c 0.000677, validation FAIL. All rejected.
- **Metamorphic row/column vs `ea_non_iid`:** `uni1` (10^6 random bits): ea_restart H_r 0.879026 / H_c 0.845975. `ea_non_iid` on the file gives H_original 0.87902612531918101, and on its `ea_transpose` output 0.84597504911067001, so both agree to the printed digits. **Transpose swap:** `ea_restart` on `uni1.T.bin` gives H_r 0.845975 / H_c 0.879026 (swapped exactly), X_max 558 both. The de Bruijn file (`db100`) gives the same row estimates as `ea_non_iid` on it for every estimator that ran.
- **Cutoff vs independent reference** (`cutoff_ref.py`: spec binomial tail at 50 digits with mpmath, and an exact sequential-binomial DP for P(max count > c) under the tool's own inverted-near-uniform model with α'):

  | H_I | spec U (largest passing X_max, α=5e-6) | exact model cutoff c* | tool X_cutoff observed | P_ideal(max>U) per experiment → overall false-fail of spec rule |
  |---|---|---|---|---|
  | 0.3 | 865 | 865 | — | — |
  | 0.9 | — | — | 604 | — |
  | 1 | 570 | 572 | 571, 571 (uni1, uni1.T), 572 (altcol1); harness 571×2, 572×4 | 7.97e-6 → 1.6 % |
  | 2 | 312 | 316 | — | 1.66e-5 → 3.3 % |
  | 4 | 99 | 104 | — | 5.67e-5 → 10.7 % |
  | 5.5 | 45 | 50 | 50 (db100) | — |
  | 6 | 36 | 40 | — | — |
  | 7 | 23 | 27 | — | 2.84e-4 → 43 % |
  | 7.5 | 19 | 22 | 22, 22 (colconst8, rowconst8) | — |
  | 8 | 15 | 19 | — | 8.72e-4 → 82.5 % |

  The simulation estimates exactly the quantity its model defines. The tool's cutoff is the order statistic `results[floor((1−α')N)−1]`, so P(tool cutoff ≤ c) = P(#{rounds with max > c} ≤ 26). At H_I = 1 this gives 570: 1.3 %, 571: 28 %, 572: 55 %, 573: 15 %, 574: 0.8 %; at H_I = 7.5, 22: 96.4 %, 23: 3.6 %. Premise check (H_I = 2, c = 316): the model {¼,¼,¼,¼} tail is 4.35e-6, which is larger than {¼,¼,¼,⅛,⅛} 3.27e-6, {¼,¼,.2,.2,.1} 2.18e-6 and {¼, 8×0.09375} 1.09e-6, so the "worst case" premise holds on the cases tried. Read literally, the spec rule would fail an ideal full-entropy 8-bit source 82.5 % of the time. This confirms the maintainers' #209 position (see §5).
- **Sanity boundary** (`gen_boundary.py`, H_I = 7.5, uniform 8-bit with row 17 forced to hold 0xA5 exactly X times): X = 22 → `X_cutoff: 22`, `X_max: 22`, "Restart Sanity Check Passed..."; X = 23 → `X_cutoff: 22`, `X_max: 23`, "*** Restart Sanity Check Failed ***", exit 255. The code comparison is `X_max > X_cutoff` ⇒ fail (equality passes), consistent with the `results[...]` quantile definition.
- **Thread count / repeatability** (`src/simcut.cpp` calls the unmodified `simulateBound`; OMP_NUM_THREADS = 1, 2, 4; 2 reps each at H_I = 7.5 (k = 256) and H_I = 1 (k = 2)): H_I = 7.5 → 22 in all six runs; H_I = 1 → 571, 572 (1 thread), 571, 572 (2 threads), 572, 572 (4 threads). Together with the three full-tool runs at H_I = 1 (571, 571, 572) that is 571×4 and 572×5, consistent with the predicted 28 % / 55 % split and with no thread-count dependence. No shared mutable state: `results[i]` writes are disjoint, RNG state and `counts` are thread-private. `xoshiro_jump` defect: see §4.
- **H_I / argument edge cases:** `nan`/`NAN` → SIGSEGV ×4 (RESTART-01); `-nan` is parsed by getopt as flags (usage, 255); `inf`, `1e400`, `1.0000001` (1-bit) → "must be at most" (255); `-inf`, `-0.5` → "must be nonnegative" (255); bits_per_symbol 0 and 9 → "Invalid bits per symbol".
- **JSON / exit status on every failure path, `-i` and `-n`:** sanity fail, validation fail, bad width, bad H_I, wrong length, empty file and nonexistent file. All errorLevel −1 except the read_file path in `-i` (RESTART-02). Sanity and validation failures exit 255, success exits 0.
- **Sanitizers:** the ASan/UBSan build with `nan` gives float-cast-overflow at :132 and :92, then "index −2147483648 out of bounds" at :92, then SEGV. Under ASan, `ea_restart` aborts on **every** run at the end of `simulateBound` (`alloc-dealloc-mismatch (operator new [] vs operator delete)`, :123/:160; known, PR #242). I observed this on the reduced-rounds copy, where only the rounds constant differs, so the code path is identical. The unmodified ASan run was stopped for time before reaching that point. The brief's "selftest clean under sanitizers" therefore never exercised ea_restart. With `ASAN_OPTIONS=alloc_dealloc_mismatch=0` and the reduced-rounds copy: `-n` uni1 (H_r 0.879026 / H_c 0.845975, pass), `-n` db100 (H_r −1, fail, i.e. RESTART-03 a third time) and `-i` uni1 (18 min, H_r = H_c 0.996133, pass, all IID tests passed) produced no ASan or UBSan report.
- **De Bruijn B(100,3) restart matrix** (`gen_debruijn.py 100 11`): RESTART-03, ×3 (two release runs, `-vv` and `-q -o`, plus one ASan run). `ea_non_iid` on the same file is used for comparison.

## 3. CONFIRMED NOVEL findings

### RESTART-01 — `H_I = nan` passes both range checks and drives an out-of-bounds stack write (SIGSEGV) in the cutoff simulation

Category B (memory/UB), Confidence HIGH, Affected executable `ea_restart` (both `-i` and `-n`), Source `cpp/restart_main.cpp:main:293-294` (atof, `H_I < 0`), `:343` (`H_I > data.word_size`), `simulateBound:127,132-133`, `simulateCount:92`. SP 800-90B section: §3.1.4.3 step 1 (p = 2^−H_I requires a real H_I). Valid ≥1,000,000-sample case? yes (any valid restart file). DIRECTION: none (crash, no figure and no JSON).

Root cause. `H_I = atof(argv)` accepts "nan"/"NAN". Both guards are ordered comparisons (`H_I < 0`, `H_I > word_size`), and those are false for NaN, so NaN reaches `simulateBound`: `p = pow(2,−NaN) = NaN`; `k_effective = ceil(1.0/p)` converts NaN to int (UB; INT_MIN on x86-64), so `assert(k_effective <= k)` passes. In every simulated round, `counts[(int)floor(randomUnit()/p)]++` indexes `counts[INT_MIN]` of a 256-entry stack array: an out-of-bounds write, SEGV.

Minimal reproduction (any valid file; `uni1.bin` = `python3 -c "import random;r=random.Random(2);open('uni1.bin','wb').write(bytes(r.randrange(2) for _ in range(10**6)))"`, `uni8.bin` = the same with `Random(1)` and `randrange(256)`):
```
ea_restart -n -q -o o.json uni1.bin 1 nan ; echo $?     # Segmentation fault, 139, no o.json
ea_restart -i -q -o o.json uni8.bin 8 nan ; echo $?     # Segmentation fault, 139
ASAN_OPTIONS=detect_leaks=0 asan/ea_restart -n uni8.bin 8 nan
```
Actual (×4 release, in `-n` and `-i`; ×1 ASan):
```
restart_main.cpp:132:23: runtime error: -nan is outside the range of representable values of type 'int'
restart_main.cpp:92:26: runtime error: -nan is outside the range of representable values of type 'int'
restart_main.cpp:92:67: runtime error: index -2147483648 out of bounds for type 'short unsigned int [256]'
==ERROR: AddressSanitizer: SEGV ... #0 simulateCount(int, double, unsigned long*) restart_main.cpp:92  #1 simulateBound ... :147
```
Expected: refuse with "H_I must be a finite number in [0, bits_per_symbol]", errorLevel −1 in the JSON and exit 255, as for `inf`, `-inf` and negative values (all correctly refused).

Impact: crash with no report. It is reached only through a non-finite H_I on the command line, for example a pipeline that forwards an upstream NaN (#168 shows `ea_conditioning` printing `h_out: nan`). The write address is fixed (INT_MIN × 2 bytes below `counts`), so this is a crash, not a controllable write. No figure is ever wrong.

Deduplication proof: grepped all.md for `nan`, `NaN`, `atof`, `strtod`, `isnan`, `isfinite`, `H_I`, `k_effective`, `simulateCount`, `simulateBound`, `out of bounds`. Hits: #168 (conditioning prints nan), #263/#264 (estimator NaN). None concerns H_I parsing or restart. #195 is a different trigger and a different symptom (a finite H_I with 2^H_I > alphabet gives an assert abort; here the assert is *passed* by INT_MIN and memory is written). PR #242's diff (fetched) touches `simulateBound` only for `delete[]` and the index type, not input validation. Not in AUDIT F-rows (those are `ea_non_iid`).

Suggested fix: `if (!std::isfinite(H_I) || H_I < 0 || H_I > word_size)` refuse, or parse with `strtod` + end-pointer check, and also assert `isfinite(p)` in `simulateBound`.
Regression test: `ea_restart -q -o o.json uni1.bin 1 nan` must exit non-zero with `errorLevel: -1`.

### RESTART-02 — in `-i` (IID) mode, every `read_file` failure writes a JSON report with `"errorLevel": 0` and no message

Category E (reporting), Confidence HIGH, Affected executable `ea_restart -i -o`, Source `cpp/restart_main.cpp:main:319-328` (line 324 sets `testRunNonIid.errorLevel = -1`, line 327 writes `testRunIid.GetAsJson()`; `read_file` was handed `&testRunNonIid` at :319, so its message also lands in the unused object). SP 800-90B section: none directly (report integrity of a §3.1.4 run). Valid ≥1,000,000-sample case? yes (a 10^6-sample file whose values exceed the declared width). DIRECTION: none. The run fails (exit 255), but the machine-readable report says no error.

Root cause. The `if (iid)` branch sets the error level on the wrong object. `git log -L` shows it was `testRunIid.errorLevel = -1` until merge 4d68e47 (2024-03-28, the FEATURE/ErrorReportSampleSize branch, PR #230) changed it. `IidTestRun.errorLevel` defaults to 0 (`test_run_base.h`), and `errorMessage` is emitted only when `errorLevel != 0`.

Minimal reproduction:
```
python3 -c "import random;r=random.Random(9);open('wide4.bin','wb').write(bytes(r.randrange(4) for _ in range(10**6)))"
ea_restart -i -q -o i.json wide4.bin 1 0.5 ; echo $?    # 255
ea_restart -n -q -o n.json wide4.bin 1 0.5 ; echo $?    # 255
: > empty.bin; ea_restart -i -o e.json empty.bin 1 0.5;  ea_restart -i -o x.json nonexist.bin 1 0.5
```
Actual (×2): `i.json`: `"IID" : true, "errorLevel" : 0, "testCases" : null` with no errorMessage. `n.json`: `"errorLevel" : -1, "errorMessage" : "Error: Incorrect bit width specification: Data (2) does not fit within described bit width: 1."`. The empty and nonexistent files in `-i` also give errorLevel 0. The `-i` "Symbols appear to be narrower than described" warning is likewise lost.
Expected: errorLevel −1 plus the read_file message, as in `-n` mode and as on every other `-i` failure path in the same function (:270, :298, :347, :370, :393, :422, :483, :838 all use `testRunIid`).

Impact: a consumer that trusts JSON `errorLevel` (for example batch tooling) sees a non-error run. It does not show a pass: there is no `Overall` case and no h_r/h_c, and the exit status is 255. It hides that the restart assessment never ran, and why.

Deduplication proof: grepped all.md for `testRunIid`, `testRunNonIid`, `Error reading file`, `errorLevel`, `JSON.*restart`, `restart.*JSON`. Relevant hits: #183 (closed 2022: some restart failure modes produced *no* JSON, fixed by PR #187), #221 (closed PR 2023: propagate read errors into JSON), #230 (closed PR 2024: width error in JSON, the merge that introduced this line). None reports an `-i` read failure being written as errorLevel 0. The bug postdates #183/#187 and was introduced by the #230 merge. PR #242's diff (fetched) rewrites the `read_file` messages in utils.h but does not touch restart_main.cpp:319-335. Adjacent family only: #255 (degraded runs not flagged); this is a failed run flagged as OK because the wrong object is written.

Suggested fix: pass `iid ? (TestRunBase*)&testRunIid : &testRunNonIid` to `read_file` and set `errorLevel` on the object that is written.
Regression test: `ea_restart -i -o i.json wide4.bin 1 0.5` must give `errorLevel: -1` and the width message.

### RESTART-03 — t-tuple/LRS "cannot be computed" (−1) is folded into H_r/H_c, so a restart test that passes per §3.1.4.2 is reported FAILED with `H_r: -1.000000`

Category A/C (assessment verdict), Confidence HIGH for the defect, MEDIUM for novelty (it is a residual location of closed #178; see dedup). Affected executable `ea_restart -n`. Source `cpp/restart_main.cpp:main:627-651`: `SAalgs(...)` results are used unguarded at :632 `H_r = min(row_t_tuple_res, H_r)`, :636, :647 `H_r = min(row_lrs_res, H_r)`, :651. `SAalgs32/64` set `lrs_res = -1.0` when v < u (`shared/lrs_test.h:330-331`, `:553-554`). Every other −1-capable estimator in the same function is guarded (`if (ret_min_entropy >= 0)`), as are the same two values in `non_iid_main.cpp:362/:381`. SP 800-90B section: §6.3.6 step 2 ("If v < u, this estimate cannot be computed"), §6.2 (minimum of the estimates), §3.1.4.2. Valid ≥1,000,000-sample case? **yes** (exactly 10^6 samples). DIRECTION: **TOO LOW / verdict wrongly FAIL**, not the dangerous direction.

Root cause. The −1 sentinel is used as if it were an entropy value. With 10^6 samples of ≤ 256 symbols the t-tuple estimate always runs (pigeonhole ≥ 3907 ≥ 35), so the reachable trigger is LRS v < u. Then H_r (or H_c) = −1 < H_I/2 for every H_I ≥ 0, and validation fails.

Minimal reproduction: a random-order de Bruijn sequence B(100,3) as the row dataset (every 3-tuple occurs at most once and every 2-tuple 99–100 times, so u = 3, v = 2). `gen_debruijn.py` (Hierholzer on the order-2 de Bruijn graph with shuffled out-edges, seed 11, output SHA-256 `4072d768…aba073d8`, X_R 30, X_C 27):
```
python3 gen_debruijn.py 100 11 db100.bin
ea_restart -n -vv -o r.json db100.bin 7 5.5
ea_non_iid -vv db100.bin 7                     # comparison: same row data through ea_non_iid
```
Actual (run 1 verbatim; run 2 with `-q -o` gives the identical verdict, exit 255, errorLevel −1, and the same per-estimator JSON values; run 3 under the reduced-rounds ASan build gives `H_r: -1.000000`, the same failure, and no sanitizer report): `ALPHA: 5.0251553006530614e-06, X_cutoff: 50` / `X_max: 30` / `Restart Sanity Check Passed...` / `LRS Estimate: v<u. Can't Run LRS Test.` / `LRS Test Estimate (Rows) = -1.000000 / 7 bit(s)` / `H_r: -1.000000` `H_c: 6.372686` `H_I: 5.500000` / `*** min(H_r, H_c) < H_I/2, Validation Testing Failed ***`, exit 255, JSON `errorLevel -1`, "min(H_r, H_c) < H_I/2, Validation Testing Failed.". In the JSON, every row value that *is* present is ≥ 6.5833 and the LRS case simply lacks `h_r`, so the report contradicts its own verdict. The row estimates that ran were MCV 6.6073, t-tuple 6.6073, MultiMCW 6.5977, Lag 6.5833, MultiMMC 6.6439, LZ78Y 6.6439. `ea_non_iid` on the same file skips LRS and reports `H_original = 6.5833315234342944` (Lag).
Expected per §3.1.4.2/§6.2/§6.3.6: H_r = 6.5833 (LRS excluded as "cannot be computed"), H_c = 6.3727, min = 6.37 ≥ H_I/2 = 2.75, so PASS and the validated entropy = min(6.58, 6.37, 5.5) = 5.5. With H_I = 4.776 (what `ea_non_iid` assesses for this file) the expected result is also PASS; the tool FAILS for any H_I.

Impact: a false restart failure ("no entropy estimate awarded") with a negative H_r in the text output. It is reachable only with restart data whose row or column dataset has the v < u structure (de Bruijn-like: some (u−1)-tuple occurs ≥ 35 times while no u-tuple repeats). That essentially never happens for physical noise sources, and such data is also deterministic (the high figures of the other estimators are the known F28/spec-limitation effect). Practical severity is low. It is an unambiguous code-vs-spec mismatch in the verdict.

Deduplication proof: grepped all.md for `v<u`, `v < u`, `lrs_res`, `t_tuple_res`, `SAalgs`, `-1`, `leak`, `invalid results`. Hits: #120 (make the v<u message visible), #166/#177 (unguarded compression −1 in non_iid_main, fixed), **#178 (closed 2022-01-31, "Check for invalid results for all tests that flag error"; it names only `conditioning_main.cpp:384` and `non_iid_main.cpp:341-350`)**, and #255 (open; skipped estimators *invisible* in JSON, which is the opposite handling). The exclusion map records the maintainer stance "the bugs fixed were cases where −1 leaked into the minimum" (#166 #177 #178). `restart_main.cpp:627-651` was never fixed (`git blame`: lines from bd56cd0 2020-09-29, untouched by the #178 fix). This is therefore the same *class* as #178, but a location that #178's fix left out and no item reports. File it as new, or as a comment reopening #178, at the user's choice. Not in AUDIT F-rows (F05 is the silent-skip direction in `ea_non_iid`).

Suggested fix: guard as in `non_iid_main.cpp`: `if (row_t_tuple_res >= 0) H_r = min(...)`, same for `col_t_tuple_res`, `row_lrs_res`, `col_lrs_res` (and ideally surface the skip, per #255).
Regression test: `db100.bin` (seed 11) must pass validation with H_r = 6.5833315234342944 and H_c = 6.3726857695387142 at H_I = 5.5.

### RESTART-04 — `-i` JSON reports `"mean": 0.0` and `"median": 0.0` (and omits `"binary"`) for every restart dataset

Category E (reporting), Confidence HIGH, Affected executable `ea_restart -i -o`. Source `cpp/restart_main.cpp:main:545-549` and `:857` (`tcOverallIid` is pushed with `mean`, `median`, `binary` never assigned; `calc_stats` computes `rawmean`/`median` at :509 but they are only passed to `permutation_tests`), `iid/iid_test_case.h` (defaults `mean = 0.0`, `median = 0.0`, `binary = false`; emitted unless −1). Contrast `iid_main.cpp:268-269` (`tc.mean = rawmean; tc.median = median;`). SP 800-90B section: §3.1.2 bullet 3 / §5 (the IID-test report for the row and column datasets). Valid ≥1,000,000-sample case? yes. DIRECTION: none (the values are not used in any decision).

Minimal reproduction: `ea_restart -i -q -o r.json uni1.bin 1 1` (uni1 as in RESTART-01; it runs the permutation tests on both datasets, about 3.5 min here).
Actual (×2: release 3 min 28 s, ASan 18 min): `{"h_c": 0.9961332374866155, "h_i": 1.0, "h_r": 0.9961332374866155, "mean": 0.0, "median": 0.0, "passedChiSquareTests": true, ... "testCaseDesc": "Overall"}`, while the data's mean is 0.500054 and `calc_stats` sets median = 0.5 for binary data. No `"binary": true`. `permutationTestResults` holds 6 unlabeled entries (3 per dataset, rows then columns).
Expected: the row and column datasets' statistics (they are permutation-invariant, so one mean/median serves both), or omit the fields. Same field semantics as `ea_iid`'s JSON.

Impact: small. It is a false statement of summary statistics in a machine-readable conformance report, and anyone cross-checking the IID tests' inputs (the excursion test uses the mean; the runs tests use the median) is misled. Verdicts and entropy figures are unaffected.

Deduplication proof: grepped all.md for `"mean"`, `mean.*json`, `median.*json`, `tc.mean`, `restart.*JSON`. No hit on restart JSON statistics. #199/#200 concern IID permutation *counts* in JSON (fixed); #251 concerns ea_iid `hAssessed`; #222 and `c20b0c1` ("Clean up JSON output for Restart IID tests") added this JSON without setting the fields. Not covered by PRs #242/#250/#252 (diffs checked).

Suggested fix: `tcOverallIid.mean = rawmean; tcOverallIid.median = median; tcOverallIid.binary = (data.alph_size == 2);` after :509, and label or split row/column permutation results.
Regression test: `-i -o` JSON for `uni1.bin` must show mean ≈ 0.500054 and median 0.5.

## 4. Suspected / observations that did not meet the bar

- **`xoshiro_jump(jump_count ≥ 2)` does not jump 2^128·n** (`shared/utils.h:551-575`): the accumulators `s0..s3` are initialised once outside the `j` loop. For n = 2 the state becomes J(S) ⊕ J²(S) instead of J²(S) (`jumpcheck.py`: tool == ref for n = 0, 1; DIFFER for n = 2, 3, 4; tool(2) == ref(1) xor ref(2) is True). This affects OpenMP threads ≥ 2 in `simulateBound` (and permutation testing in ea_iid). The char-poly of xoshiro256's transition is primitive, so J + J² = T^m for some m: the thread still gets a valid state on the full-period cycle at an unknown offset, and overlap with another thread's ~10^9-draw segment has probability ~2^−220. I found no output effect (thread-count runs above: no distributional difference between 1, 2 and 4 threads). The code does not do what its comment says, but it is not a demonstrable defect. Not in all.md (`jump`: 0 hits).
- **`sha256_file` return value ignored, uninitialised `hash[]` copied into the report** (`restart_main.cpp:246-254`; same pattern in iid_main.cpp:198, non_iid_main.cpp:178, conditioning_main.cpp:519): for a nonexistent file the JSON `sha256` is stack garbage (`"\u0232\ufffdW"` in one run, `"\u0232i\u001d\u03e1"` in another`), and it differs per run. This is shared I/O, so I leave it to the io area. It is *not* in the #259/#260 families; worth checking there.
- **Restart JSON never carries the final validated value** min(H_r, H_c, H_I), nor X_max or X_cutoff. On `-i` validation failure the JSON has no h_r/h_c at all (the Overall case is pushed only on success). These are reporting gaps (the unlabeled row/column permutation entries are noted under RESTART-04). The #238/#255 family is adjacent but does not name them. Low value.
- **`-s` accepts any value ≥ 5,000,000**: `-s 18446744073709551614` or `-s -5` (strtoul wraps) leads to `new uint16_t[huge]`, std::bad_alloc and an abort. This is a user-requested resource limit, not filed.

## 5. EXCLUDED AS ALREADY KNOWN

| Rediscovery | Known item |
|---|---|
| Sanity cutoff is not the §3.1.4.3 binomial: tool cutoff exceeds spec U by 0–5 counts (e.g. H_I = 7.5: X_max 20–22 pass the tool, fail the spec) | #56, #95, #98, #209, #224. Maintainers: spec formula wrong, simulation intended. My numbers confirm the spec rule would fail an ideal 8-bit source 82.5 % of the time |
| α' = 1−0.99^(1/2000) instead of 0.000005 | #95 |
| Cutoff is stochastic (/dev/urandom seed, ±1–2 counts; H_I = 1: 16 % of runs above the exact model cutoff 572) | #212, #247 (maintainer positions 17 and 20) |
| `assert(k_effective <= k)` abort (SIGABRT, no JSON) when ceil(2^H_I) > observed alphabet | #195 (open) |
| `delete results` on a `new[]` array (`restart_main.cpp:160`; gcc 13 `-Wmismatched-new-delete`; ASan alloc-dealloc-mismatch) | PR #242 (open; diff has `delete[] results`) |
| JSON errorMessage literally `"Error: could not open '%s'\n"` / `"'%s' is empty"` (comma-operator bug in read_file) | PR #242 (open; diff rewrites both with stringstream) |
| `-i`: IID tests on row/column data fail but the tool still prints "Validation Test Passed", min(H_r,H_c,H_I) and exits 0 / errorLevel 0 (§3.1.2 bullet 3 then requires the non-IID track) | #252 family ("IID figure after failed IID"). Note: PR #252's diff touches only README.md and iid_main.cpp, so the restart instance (`restart_main.cpp:740-834`) stays unfixed. Worth a comment on #252 |
| IID tests on column data used row data | #244, fixed by PR #250 (verified present at 87c104d: `data_col.symbols = cdata; rawsymbols = crawdata`) |
| Binary-only estimators run when a multi-bit restart dataset has 2 observed values | #253 family (gate on `alph_size`). In restart only extra estimators result (conservative); no bitstring term is owed here |
| Width inferred when bits_per_symbol omitted; H_I bound uses inferred width | #254 (restart variant → #195) |
| −1 estimators silently skipped / invisible in JSON | #255 (not reachable at 10^6 samples for the guarded estimators) |
| sha256_file unbounded read (/dev/zero, FIFO) | #259 |
| H_r from single 10^6 row dataset, pass iff min ≥ H_I/2 | #161, #233 (maintainer position 18) |

### Prior local audit row now verified

- **F05 (de Bruijn part, previously "NOT run")**: `ea_non_iid` skips the literal LRS estimate at a conforming sample count. Here the input is exactly 1,000,000 samples, a random-order de Bruijn B(100,3) (`db100.bin`, SHA-256 `4072d768…aba073d8`), not the row's B(128,3) at 2,097,154. `ea_non_iid -vv db100.bin 7` prints `LRS Estimate: v<u. Can't Run LRS Test.` and reports `H_original = 6.5833315234342944`, `Assessed min entropy: 4.7760652119354905` for a fully deterministic sequence. `-q -o` JSON: `errorLevel 0`, no errorMessage, and the LRS test case carries only `binLrsRes` (no literal value). This confirms the #255 mechanism at ≥ 10^6 samples (#255 left the de Bruijn claim out). The ea_restart consequence is the opposite handling (−1 *included*), which is RESTART-03.

## 6. No-finding areas (attacked and held)

- Orientation: rows are restarts; the column construction equals `ea_transpose` bit-for-bit; row and column runs reproduce `ea_non_iid` exactly; transposing the matrix swaps (H_r, H_c) exactly.
- Stale state between the row and column runs: no static or mutable globals in the estimators used (only a shuffle mutex and constants; the cephes `sgngam` is recomputed per call). Row and column runs are sequential. No OpenMP in the estimator path; the restart OpenMP region has disjoint writes and private RNG/`counts`.
- Exact 10^6-sample enforcement in both modes, with JSON errors; no `-l` option exists in ea_restart.
- H_I range: negative, ±inf, overflow and > width are all refused (exit 255 tested; the JSON writes on these paths use the correct object by code reading). NaN is the exception (RESTART-01). H_I = 0 (by code reading, not run) gives p = 1, k_effective = 1 and cutoff 1000, so the test passes with final 0, which is consistent with the spec (P(X ≥ X_max) = 1 ≥ α).
- Simulation index math: `k_effective = ceil(1/p)` and `floor(u/p) ≤ k_effective−1 ≤ 255` for every finite H_I ∈ [0, 8], including 1/p within 1 ulp of an integer. The quantile index `floor((1−α')N)−1` gives ≤ 26 exceedances of αN = 25.1. `uint16_t` counts fit 1000.
- The simulation matches an exact computation of its own model (H_I = 1, 5.5, 7.5). The worst-case premise holds against three alternative distributions at H_I = 2.
- Sanity inequality: equality passes, consistent with the quantile definition (boundary files).
- Structured degenerate matrices (constant columns, constant rows, symmetric shift, alternating columns) are all rejected, either by the sanity check or by validation.
- Pass/fail exit codes: 0 on pass, 255 on sanity or validation failure, both modes.
