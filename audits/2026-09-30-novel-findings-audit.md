# SP800-90B_EntropyAssessment: adversarial novel-findings audit, 2026-09-30

Audited tree: `usnistgov/SP800-90B_EntropyAssessment` master **87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289**. That was upstream HEAD on the day of the audit, and its `cpp/` is identical to the fork except for the Makefile. The tree was extracted with `git archive` into a scratch directory, so the repository was never built in or modified. Nothing was posted to GitHub.

The generated inputs, harnesses, per-area agent reports and the coordinator's verification log lived in a temporary session workspace and are **not** preserved in this repository. Each finding below carries its own self-contained reproduction commands (Python generators inline), to be run from a build of upstream `87c104d`. "Coordinator" means the owner's session, which re-ran every claim on a clean build; "agent" means evidence from one of the seven parallel auditors that the coordinator did not re-run.

---

## 1. Executive result

**Confirmed novel findings: 11.** Only two affect a decision or figure in the dangerous direction. Both are in `ea_iid` and both reproduce with conforming 1,000,000-sample datasets:

| # | Finding | Cat. | Direction | ≥10^6? |
|---|---|---|---|---|
| N-01 | Binary chi-square independence reports **Passed** when m = 1; §5.2.3 says "If m is 1, the test fails" | A | **TOO HIGH** (IID wrongly accepted; 1.42× in repro) | yes |
| N-02 | `ea_iid -c` runs the §5 IID tests on packed symbols, not on the conditioned **binary string** required by §3.1.1(2)/§3.1.5.2 | A | **TOO HIGH** (IID wrongly accepted; h′ 2.47× in repro) | yes |
| N-03 | `ea_conditioning -n -i` on an all-zero conditioned dataset: assert abort, no JSON; under `-DNDEBUG` a heap over-read and a wild write | D/B | none (correct h′ = 0) | yes |
| N-04 | `ea_restart` H_I = `nan` passes both range checks, then UB float→int and OOB `counts[]` write → SIGSEGV; H_I = `abc` → 0 → "Validation Test Passed" | B/D | none | yes |
| N-05 | `ea_conditioning` JSON binds the `-i` file's name and SHA-256 to an h′ that did not come from it (CLI h′ given too, or vetted mode) | C | report shows 253.44 vs 213.63 from that file | yes |
| N-06 | `sha256_file()` return ignored in all four mains: uninitialised stack bytes land in the JSON `sha256` | B/C | none | yes |
| N-07 | The hash and the assessed bytes come from two separate opens (TOCTOU): a concurrent rewrite makes the report bind one file's hash to another file's figure | C (hardening) | none | yes |
| N-08 | Numeric CLI arguments parsed permissively (`atoi`, `strtoul` base 0, no end check): `-l 010,…` assesses block 8, `bits 8x` and `4294967304` become 8, `0256` becomes 174 in conditioning, negatives wrap | D/E | none or lower | n/a |
| N-09 | Output write failures never checked (`-o /dev/full`, missing directory → exit 0; `ea_transpose` truncated column file with exit 0) | E | none | n/a |
| N-10 | Reporting-only: ea_iid "Median" is of translated indices; conditioning JSON hard-codes `"IID": false` and omits vetted/track; restart `-i` JSON mean/median always 0.0 | E | none | yes |
| N-11 | `ea_conditioning` aborts (assert) for accepted n_in/n_out ≥ 1,073,741,823 (MPFR emax) | D | none | n/a |

**Residuals of closed fixes: 3.** These share a known root cause, so they are not counted as novel, but the earlier fix is demonstrably incomplete and they reproduce at 10^6:
- R-1: #246 (`p_col ≥ 1/k` assert on exactly balanced counts).
- R-2: #178 (−1 sentinel folded into the minimum, in `restart_main.cpp`).
- R-3: #183 (restart JSON not flagging failure; regressed by merge 4d68e47).

**Prior local rows now verified:**
- F09: TOO LOW.
- F14: mechanism shown, TOO HIGH, but it needs more than 25.8 Gbit of input.
- F10: mechanism only; no effect at the shipped constants.

**What held:** no finding makes `ea_non_iid`'s assessed figure too high. The dangerous-direction issues are confined to the `ea_iid` gate.

---

## 2. New confirmed findings (strongest first)

### N-01: Binary independence test with m = 1 is reported as Passed (§5.2.3)

- **Category:** A (entropy correctness / IID decision).
- **Confidence:** HIGH.
- **Executable:** `ea_iid`. Also reachable through `ea_restart -i`, which calls the same `chi_square_tests`; not run.
- **Source:** `cpp/iid/chi_square_tests.h`
  - `binary_chi_square_independence`:485-489: `if (m < 2) { score = 0.0; df = 0; return; }`
  - `chi_square_tests`:649 computes `chi_square_pvalue(0, 0)` = 1.
  - :664 fails only if `pvalue < 0.001`.
- **SP 800-90B:** §5.2.3 step 2. "Find the maximum integer m such that min(p0,p1)^m·⌊L/m⌋ ≥ 5 … **If m is 1, the test fails.** … The test is applied if m ≥ 2."
- **Valid ≥1,000,000-sample case:** yes.
- **DIRECTION:** TOO HIGH. The spec requires the IID claim to fail, which forces the non-IID track.

**Root cause.** The m = 1 branch is coded as "not applicable" (T = 0, df = 0) instead of "fail". The chi-square p-value with 0 degrees of freedom is 1, so the test passes.

**Trigger.** Any binary dataset with min(p0,p1)^2·⌊L/2⌋ < 5. At L = 10^6 that means ≤ 3,162 minority bits.

**Reproduction.** Coordinator runs, clean release build:
```sh
python3 - <<'EOF'
import random
for n in (3162,3163):
    r=random.Random(n); b=bytearray(1000000)
    for i in r.sample(range(1000000),n): b[i]=1
    open(f'ones_{n}.bin','wb').write(b)
EOF
./ea_iid -vvv ones_3162.bin 1 | grep 'independence'     # boundary
./ea_iid -vvv ones_3163.bin 1 | grep 'independence'
./ea_iid -v -o o.json ones_3162.bin 1                    # full run
./ea_non_iid -v ones_3162.bin 1                          # non-IID track
```

**Actual.**
- `ones_3162`: `T = 0, df = 0, P-value = 1`.
- `ones_3163`: `T = 0.9594, df = 2, P-value = 0.619`. The boundary is exactly where the spec's inequality puts it.
- Full run: `Passed chi square tests / Passed LRS / Passed IID permutation tests`, JSON `"IID": true`, errorLevel 0, `H_original = 0.004360`.
- `ea_non_iid` on the same file: `0.003068`.

**Expected.** The chi-square battery fails, so the data is not IID and the non-IID track figure (0.003068) applies.

**Impact.** This is a genuine conformance defect in the IID gate. It is not exaggerated: it applies only to extremely biased binary sources (≤ 0.32 % minority bits at 10^6). The absolute error is small (+0.0013 bit/bit here, 1.42× relative). The permutation tests may still catch a sparse source that is dependent.

**Deduplication.**
- all.md was searched for "m is 1", "df = 0", "degrees of freedom … 0", "test fails", and binary independence.
- Only #28 turns up. It is draft-era Python about overlapping tuples; "m is 1, the test fails" appears there only as a quoted spec comment inside JEH's replacement code, which handled it by *not applying* the test.
- #93 is a different statistic bug (block iteration).
- No maintainer position covers it. For the non-binary case the spec says "do not apply" and the tool matches, which was checked and is correct.

**Fix direction.** In `binary_chi_square_independence`, signal failure for m = 1, for example `score = +inf; df = 1`, or return a flag that `chi_square_tests` treats as fail. Print "m = 1: test fails (§5.2.3)".

**Regression test.** `ones_3162.bin` must fail the chi-square tests; `ones_3163.bin` must compute df = 2.

### N-02: `ea_iid -c` tests the wrong representation of conditioned data

- **Category:** A.
- **Confidence:** HIGH.
- **Executable:** `ea_iid` (`-c`).
- **Source:** `cpp/iid_main.cpp`. Under `-c` (`initial_entropy = false`), h′ comes from the bitstring at :282 (`most_common(data.bsymbols, data.blen, …)`), but all three IID batteries receive the packed byte symbols:
  - :316 `chi_square_tests(data.symbols, …)`
  - :334 `len_LRS_test(data.symbols, …)`
  - :352 `permutation_tests(&data, …)`, which uses `dp->symbols`/`rawsymbols`.
- **SP 800-90B:**
  - §3.1.1 item 2: "The output of the conditioning component shall be concatenated … and **treated as a binary string for testing purposes**."
  - §3.1.5.2: "The output of the conditioning component (n_out) shall be treated as a binary string, for purposes of the entropy estimation."
  - Maintainer #139 (JEH): under `-c` "all such data is treated as a binary string only".
- **Valid ≥1,000,000-sample case:** yes.
- **DIRECTION:** TOO HIGH (IID wrongly accepted, and h′ inflated).

**Reproduction.** Coordinator runs:
```sh
python3 -c "import random; r=random.Random(4242); open('nib_dup.bin','wb').write(bytes(((x<<4)|x) for x in (r.randrange(16) for _ in range(1000000))))"
./ea_iid -c -v -o c.json nib_dup.bin 8
./ea_non_iid -c -v nib_dup.bin 8
# control: the same data as the binary string the spec requires (first 10^6 bits)
python3 -c "d=open('nib_dup.bin','rb').read(); open('bits.bin','wb').write(bytes(((x>>k)&1) for x in d for k in range(7,-1,-1))[:1000000])"
./ea_iid -vvv bits.bin 1
```

**Actual.**
- `ea_iid -c`: all three batteries Passed, JSON `"IID": true`, **h′ = 0.998640**.
- `ea_non_iid -c`: **h′ = 0.403507**.
- By construction the true value is 0.5 bit/bit: the high nibble copies the low nibble.
- Control (IID tests on the bitstring): independence `T = 330211.8, df = 2046, p = 0`, giving `Chi square tests: Failed`; LRS `W = 67, Pr = 3.39e-9`, giving `Failed`.

**Expected.** The IID tests run on the conditioned binary string and fail. The non-IID track then gives h′ ≈ 0.40.

**Impact.** A non-vetted conditioner whose outputs are independent word-to-word but have intra-word bit dependence passes as IID. h′·n_out then over-credits by up to 2.47× in this example, capped by Output_Entropy and 0.999·n_out.

**Deduplication.**
- Searched: ea_iid + conditioned/-c/binary string/bitstring/3.1.5.2 → #139 only.
- #139 concerns `-t` truncation in ea_non_iid; its maintainer comment *supports* this finding.
- The #253 gate (`alph_size > 2`) is a different root cause; this happens with `alph_size = 16`.
- No item on IID tests under `-c`.

**Fix direction.** When `!initial_entropy`, pass `data.bsymbols, data.blen, 2` to the three batteries, with binary chi-square and permutation handling. Equivalently, refuse `-c` in ea_iid and document that the bitstring be supplied at 1 bit/sample.

**Regression test.** `ea_iid -c nib_dup.bin 8` must fail the IID tests.

### N-03: `ea_conditioning -n -i` crashes on an all-zero conditioned dataset

- **Category:** D in the shipped build; B under `-DNDEBUG`.
- **Confidence:** HIGH.
- **Source:**
  - `conditioning_main.cpp:computeEntropyOfConditionedData:364-384` has no single-symbol or length guard.
  - `utils.h:read_file_subset` infers `word_size = 0` for all-zero data, so `blen = 0`.
  - The abort is at `most_common.h:14` (`assert(len > 1)`).
- **SP 800-90B:** §3.1.5.2 and §6.3.1.
- **≥10^6:** yes.
- **DIRECTION:** none. The correct result is h′ = 0.

**Reproduction.** Coordinator, two runs:
```sh
python3 -c "open('zero1e6.bin','wb').write(bytes(1000000))"
./ea_conditioning -n 512 256 256 300 -i zero1e6.bin -o z.json
```
- Shipped build: `most_common.h:14 … Assertion 'len > 1' failed`, rc 134, no z.json.
- `ea_non_iid` and `ea_iid` on the same file refuse cleanly ("1 symbol. No entropy awarded", JSON written).
- `-DNDEBUG` + ASan: `heap-buffer-overflow … markov_test.h:48`, with the allocation at `utils.h:329`. With recover enabled, the agent also saw a SEGV on a write at `lag_test.h:53`.
- One non-zero byte in the same file gives h′ = −0 correctly.

**Impact.** A stuck-at-zero conditioner is exactly the failure this assessment should report as 0. The shipped build core-dumps with no JSON; a hardened (NDEBUG) build corrupts memory.

**Deduplication.**
- Searched all-zero/constant/stuck + conditioning, `computeEntropyOfConditionedData` (#211 leak only), `len > 1`: 0 relevant items.
- Adjacent: #261 (tiny inputs; this input is 10^6) and #254 (width narrowing changes values, not a zero-width empty bitstring).
- If the maintainers treat "missing input validation" as one family, this could also go as a comment on #261. The facts that make it new are the ≥10^6 reproducer and the zero-width mechanism.

**Fix direction.** Guard `blen < 2`, or a single-valued bitstring, and return h′ = 0 (or errorLevel −1 with JSON). Never infer width 0.

**Regression test.** zero1e6.bin gives h′ = 0 or a JSON refusal, and the NDEBUG+ASan build is clean.

### N-04: `ea_restart` accepts H_I = `nan` (UB, SIGSEGV) and garbage H_I as 0

- **Category:** B/D.
- **Confidence:** HIGH.
- **Source:**
  - `restart_main.cpp:293`: `H_I = atof(argv[0])`.
  - :294 `H_I < 0` and :343 `H_I > data.word_size` are both false for NaN.
  - `simulateBound`:127 then does `p = pow(2,-NaN)`, and `simulateCount`:92 does `counts[(int)floor(u/p)]++`, a float→int conversion of NaN (UB) that indexes `counts[INT_MIN]`.
- **≥10^6:** yes (any valid restart file).
- **DIRECTION:** none.

**Reproduction.** Coordinator: `./ea_restart -n r1e6.bin 8 nan` (r1e6.bin = 10^6 random bytes) gives **SIGSEGV, rc 139**, twice. ASan/UBSan pin the lines (agent runs). `./ea_restart -n r1e6.bin 8 abc` gives "Validation Test Passed … min(H_r, H_c, H_I): 0.000000", rc 0.

**Impact.** A crash and an out-of-bounds stack write from a command-line typo. The `abc` case yields a vacuous "passed" with a final value of 0, which is conservative but misleading.

**Deduplication.** H_I + nan/atof/negative gives 0 items. #195 is the `k_effective` assert, a different path; NaN passes it.

**Fix direction.** Use `strtod` with an end-pointer check and `std::isfinite(H_I)`, and require `H_I > 0`, or state that 0 is permitted.

### N-05: Conditioning JSON binds a file's SHA-256 to an h′ that did not come from it

- **Category:** C.
- **Confidence:** HIGH for the behaviour, MEDIUM for severity.
- **Source:**
  - `conditioning_main.cpp:515-523` hashes and records `-i` whenever it is given.
  - :558-576 uses the command-line h′ whenever argc == 5.
  - Vetted mode never reads the file.

**Reproduction.** Coordinator:
```sh
./ea_conditioning -n 512 256 256 300 -i cond8.bin -o measured.json          # h_p 0.83447, h_out 213.625
./ea_conditioning -n 512 256 256 300 0.99 -i cond8.bin -o both.json         # same filename + sha256, h_p 0.99, h_out 253.44, errorLevel 0
./ea_conditioning -v 512 256 256 300 -i cond8.bin -o vet.json               # same filename + sha256, no data used
```

**Impact.** A reviewer reading the JSON (filename + hash + h_p, errorLevel 0) would take h_p as measured from the hashed dataset. It requires contradictory arguments, and `commandline` does show the 0.99.

**Deduplication.** #218 added the hash and is not about misattribution. #260 is the ea_non_iid `-l` subset hash, a different mechanism.

**Fix direction.** Reject h′ together with `-i`, and `-i` under `-v`, or record `hpSource` and omit the hash when the file is unused.

### N-06: `sha256_file()` failure is ignored, so uninitialised bytes go into the JSON

- **Category:** B/C.
- **Confidence:** HIGH.
- **Source:** `TestRunUtils.h:62` returns −1 on error, and every caller ignores it: `non_iid_main.cpp:179`, `iid_main.cpp:199`, `restart_main.cpp:247`, `conditioning_main.cpp:521`. `char hash[65]` is uninitialised.

**Reproduction.** Coordinator: `ea_conditioning -n 512 256 256 300 0.9 -i nope.bin -o nf.json` exits 0 with errorLevel 0 and `"sha256": "��…"`, which differs between runs. Valgrind confirms the uninitialised read (agent). For `ea_non_iid`/`ea_iid` with a missing file the hash is also garbage, but errorLevel is −1.

**Impact.** Low; the JSON has an unreliable provenance field. Fix: check the return value and set errorLevel/message, and zero-initialise `hash`.

### N-07: TOCTOU between the hash pass and the data pass (hardening)

- **Category:** C.
- **Confidence:** HIGH that it reproduces, LOW–MEDIUM on severity.
- **Source:** The hash `fopen` at `TestRunUtils.h:72` and the data `fopen` at `utils.h:181` are separate. The same pattern is in all four mains.

**Evidence (agent).** An LD_PRELOAD shim rewrites the file between the two opens. The JSON then has truerand_8bit.bin's sha256 but biased-random-bytes.bin's `hAssessed` 0.2577. An append variant was also shown.

**Assessment.** This needs a concurrent writer: a copy or acquisition job still running, or a watch-folder pipeline. It is distinct from #260, which is subset scope, and from #259, which is non-regular files. Fix: hash the buffer that is assessed.

Coordinator status: **reproduced ×2** with the same shim on the clean build. The JSON has `sha256` c7e56911… (truerand_8bit.bin) and `hAssessed` 0.25774087100648113, identical to a direct run on biased-random-bytes.bin (sha256 146bd749…).

### N-08: Numeric CLI arguments parsed permissively

- **Category:** D/E.
- **Confidence:** HIGH.
- **Direction:** none, or a lower or different assessment.

Examples verified by the coordinator:
- `ea_non_iid -l 010,20000` equals `-l 8,20000` (6.36327, octal via `strtoull(…, 0)` at `non_iid_main.cpp:120`) and differs from `-l 10,20000` (6.37041).
- `-l 1,20000abc` is accepted (the second field has no end check, :137).
- bits_per_symbol `8x` and `4294967304` are both treated as 8 (`atoi`, `non_iid_main.cpp:186`; the same pattern is at `iid_main.cpp:179` and `restart_main.cpp:265`).
- `ea_conditioning -v 512 0256 256 300` gives n_out = 174 (`strtoul` base 0, `conditioning_main.cpp:104`); `0x100` gives 256; `-- -18446744073709551615` gives n_in = 1.
- `ea_transpose -l abc` reads block 0 (agent).

**Impact.** A zero-padded index or width from a lab script silently assesses a different block or conditioner size. The JSON `commandline` shows the literal text, not the interpreted value.

**Deduplication.** Searched octal/leading zero/strtoul/atoi/base 0/trailing: 0 items. #191 was a getopt crash; #102 was non-integer conditioning values; #260 is `-l` arithmetic and hash scope.

**Fix.** Parse decimal only (`strtoul(…, 10)`), check the end pointer and errno, and reject signs.

### N-09: Output-file write failures are never checked

- **Category:** E.
- **Confidence:** HIGH.
- **Coordinator:** `ea_non_iid -o /dev/full …` exits 0, and `-o /nonexistent_dir/x.json` exits 0.
- **Agent:** `ea_transpose` under `ulimit -f` with SIGXFSZ ignored leaves a 999,424-byte column file and exits 0 (`fclose` unchecked at `transpose_main.cpp:112`). A downstream pipeline sees exit 0 and a missing, stale or truncated report.

**Deduplication.** ofstream/disk full/fclose/unwritable: 0 items. Fix: check stream state after `close()` and the `fclose` return, and exit non-zero.

### N-10: Reporting-only defects

- **Category:** E.
- **Confidence:** HIGH.

(a) **ea_iid "Median" is the median of translated symbol indices.** It is computed by `calc_stats` on `dp->symbols` and printed next to a *raw* mean ("Raw Mean: 70.56 / Median: 8.0"). This is visible but unremarked in open #167's log. The permutation tests themselves are consistent: the median tests use translated data with the translated median, and the excursion test uses raw data with the raw mean. Verdicts are unaffected.

(b) **Conditioning JSON hard-codes `"IID": false`** (`non_iid_test_run.h:30`, reused per the TODO at `conditioning_main.cpp:509`) even with `-c iid`, and records neither vetted/non-vetted nor the h′ track. `-c iid` gave h′ 0.9944 vs 0.8345 non-IID on the same file.

(c) **ea_restart `-i` JSON always shows `"mean": 0.0, "median": 0.0`** and no `binary` field: `restart_main.cpp` never assigns them on `tcOverallIid`. Coordinator confirmed this by code reading; the agent confirmed it by running.

### N-11: ea_conditioning aborts for accepted n_in/n_out ≥ 1,073,741,823

- **Category:** D.
- **Confidence:** HIGH.
- **Relevance:** LOW (a 2^30-bit conditioning input is unrealistic).
- **Coordinator:** `ea_conditioning -v 1073741823 256 256 300` triggers `conditioning_main.cpp:602: Assertion 'mpfr_get_emax() > maxval' failed`; 1073741822 runs. The accepted range is up to UINT_MAX. Fix: range-check against emax, or call `mpfr_set_emax`.

---

## 3. Previously known upstream findings encountered (rediscoveries, not counted)

**Residuals of closed fixes.** These are actionable, but the root cause is already known:

- **R-1 → #246 (closed, fixed by #248).** `ea_iid` still aborts at `lrs_test.h:626` `assert(p_col >= 1/k)` when every symbol count is equal and 1/k rounds down. That is 155 of the 247 non-power-of-two k (3, 6, 7, 9, 12, …).
  - Coordinator: a 1,000,002-sample shuffled balanced k = 3 file aborts in 0.32 s with no JSON, twice.
  - Control: changing one symbol gives a complete run that passes every test.
  - The agent's `-DNDEBUG` run completes cleanly.
  - #248 fixed accumulation drift only. JEH's alternative in #246, "p_col values sufficiently close to 1/k should just be taken as 1/k", was not implemented.
- **R-2 → #178 (closed, "Check for invalid results for all tests that flag error").**
  - The fix patched `conditioning_main.cpp` and `non_iid_main.cpp` only.
  - `restart_main.cpp:632/636/647/651` still fold t-tuple/LRS −1 into H_r/H_c.
  - Coordinator, two runs: a 10^6-sample de Bruijn B(256,3) prefix gives `LRS Estimate: v<u`, `H_r: -1.000000`, and "Validation Testing Failed" (rc 255). Every estimate that ran is ≥ 0.585 > H_I/2 = 0.25.
  - DIRECTION: TOO LOW (false restart failure).
- **R-3 → #183 (closed, "When in JSON mode, ea_restart testing may not flag failure").**
  - In `-i` mode a `read_file` failure writes `"errorLevel": 0`, because :324 sets `testRunNonIid.errorLevel` and then writes `testRunIid`. Exit is 255.
  - `git blame`: line 324 comes from merge **4d68e47** (2024-03-28, the #230 branch), after #183 was closed. This is a regression.
  - Coordinator reproduced it with an unreadable file.

**Plain rediscoveries mapped to existing items:**
- **#253:** the `alph_size > 2` bitstring gate also exists in `iid_main.cpp:280-299`; same root cause.
- **#254:** width inference in the `ea_conditioning -i` path (+46 % in the agent's example; no width option exists there).
- **#255:** no sample-count warning in the conditioning `-i` path. The de Bruijn LRS skip at exactly 10^6 in `ea_non_iid` (errorLevel 0) is the F05 claim, now verified by the restart agent: #255 mechanism plus maintainer position 12.
- **#257, #259, #260, #261, #263, #264:** tiny-input asserts and NaN in `ea_iid`/`ea_conditioning`, `/dev/zero` hang in every tool, `-l` arithmetic.
- **#153:** the IID LRS test aborts on one duplicated ≥2,049-byte region at 10^6 (2,040 bytes → FAIL; 2,100 → abort; `-DNDEBUG` → correct FAIL). Known and "detect" by design.
- **#195:** restart `k_effective` assert.
- **#251:** ea_iid JSON hAssessed at default verbosity.
- **#252:** ea_iid/restart `-i` report a figure when the IID tests fail; `"IID": true` constant.
- **#56/#95/#209/#224:** restart cutoff above the spec's binomial U (intended; the literal rule would fail an ideal 8-bit source 82.5 % of the time).
- **#212/#220/#247/#239:** stochastic cutoff and permutation results, early exit.
- **#242 (open PR):** `delete` vs `new[]` at `restart_main.cpp:160`, and the comma-operator error strings.
- **#22, #133/#134, #127/#139/#140, #71/#125, #214/#163/#52, #217/#226, #155/#170:** constants, predictor iteration, `-t`/`-c` semantics, bit order, LRS time, large files, platform stance.

---

## 4. Prior local F01–F30 rows encountered

| Row | Status now | Direction | Evidence |
|---|---|---|---|
| F09 (MultiMMC: a Null winner prediction does not reset the run) | **VERIFIED** (coordinator ×2 + literal §6.3.9 reference) | TOO LOW | f09b.bin (sha256 1e2ae594…c534, 114,146 samples: 100,310 random bytes from {16..255}, a 36-byte all-distinct-bigram block Y over {1..8} placed so the order-2 dictionary fills inside it, 3,000 random bytes, then Y×300; the generator script was not preserved): tool r = 6603, spec r = 24, and a "noreset-only" emulation gives 6603. MultiMMC 0.0021 vs 0.93; assessed figure unchanged (t-tuple binds). `multi_mmc_test.h:211-228`: `run_len = 0` only inside `if(found_x)`. No upstream item. |
| F10 (MultiMMC chained lookup skips deeper orders) | mechanism verified (agent, instrumented) | either in a scaled model; none observed at 100,000 | Scoreboard deltas, but C and r unchanged at the shipped constants; in a scaled-down build 17/3000 cases up to +0.71 bit. Needs more work. |
| F14 (compression `unsigned int dict[]`) | mechanism verified (agent, unmodified function on 2^32+10^9 blocks) | TOO HIGH | 1.0 vs 0 (control). Needs > 25.77 Gbit and about 650 GB RAM end-to-end; latent in the size range #217/#226 enabled. Fix: `long dict[]`. |
| F13 (NaN folded by std::min) | no producer at ≥10^6 in any tool | — | numerics agent |
| F20 (`-t` under `-c`) | mechanism reproduces | — | maintainer position #127/#139/#140 |
| F23 (`-c -vv` prints 8×h′; JSON literal-only) | partly reproduces | — | partly #179/#251 |
| F05 (de Bruijn LRS v<u at ≥10^6) | VERIFIED at exactly 10^6 | TOO HIGH per #255 visibility | #255 + maintainer position 12 |

---

## 5. Rejected / false-positive candidates

| Candidate | Reason |
|---|---|
| IID-04: ThreadSanitizer race on `test_status[]` | Unsynchronised access shown, but no incorrect result at 1/2/4/8 threads (every undecided test ran exactly 10,000 rounds, verdicts matched). Per the threading rule: hardening only. |
| MultiMMC/LZ78Y change under non-order-preserving relabelling | Maintainer position #147: estimators are invariant only under the tool's order-preserving translation. |
| Non-binary independence with df < 1 reported Passed | Spec-consistent: §5.2.1 says the test is not applied. |
| Restart X_cutoff above the spec's binomial U | Intended deviation, #56/#95/#209/#224. |
| LRS estimate > bits/symbol (9.23 > 8 on de Bruijn columns) | Spec-consistent; the minimum over estimators clamps it. |
| `xoshiro_jump` for n ≥ 2 not a true 2^128·n jump | No output effect found; insufficient evidence. |
| ea_conditioning FE_TOWARDZERO rounding | ≤ 5.8e-12, always lower; harmless. |
| ea_iid sample count in `int` above 2^31 | Not demonstrable on a 7 GB host; LP64 or large-memory only. Insufficient evidence. |
| ea_conditioning `-i` on constant 0xFF (long LRS) | #214/#163 family (known, expected expensive). |
| `TESTCASE_H` include-guard collision | Dead include, no runtime effect. |
| `-s` huge in restart → `new[]` failure | Hostile command line, trivial. |
| `-o` equal to the input path overwrites the input | User-directed. |
| IID LRS printed `Pr(X≥1)` = 0 by cancellation | Display only; the decision uses logs. |
| Compiler/FMA/clang/-O0 dependence | ≤ 2.2e-13, no decision flips. |
| COND-03, TRANS-01, TRANS-02, IO-02, IO-04, IO-05, IO-07, IO-08, NUM-02, NUM-04, RESTART-01..04 | Merged into N-03/N-04/N-05/N-08/N-09/N-10 or R-2/R-3; not separate defects. |

---

## 6. Coverage matrix

| Area | Spec comparison | Differential / reference | Boundaries & structures | Sanitizers & NDEBUG | Threads |
|---|---|---|---|---|---|
| ea_iid | §5.1 (19 statistics, conversions, median rule, C0/C1/C2 counts, reject rule), §5.2.1–§5.2.5, §3.1.1(2), §3.1.3 | Literal implementation of all statistics, chi-square T/df/p and LRS on 30 inputs (0 mismatches); p-values vs mpmath (≤ 6.4e-11 up to df 65,280); shuffle/Lemire bias tests | 256 edge-length files; 7 non-IID 10^6 constructions; m = 1 boundary; balanced k sweep 2..256 | ASan/UBSan (256 files); TSan; `-DNDEBUG` for asserts | 1/2/4/8 |
| ea_non_iid | §6.3.1–§6.3.10 (the prior audit covered 6.3.1–6.3.6; this one 6.3.7–6.3.10 literally) | Literal Python and C++ reference, C/r/N exact; binary vs generic 28/28; widths 2..8 56/56; full dictionaries; NIST 10^6 files | Dictionary-full, orphan contexts, 2^32-block compression | ASan/UBSan build (selftest clean) | 1/2/4, 7 runs byte-identical |
| ea_restart | §3.1.4.1–§3.1.4.3, §3.1.2(3) | Row/column = ea_non_iid to the printed digits; column = ea_transpose; cutoff vs exact model at H_I 1/5.5/7.5 | Sanity boundary 22/23; degenerate matrices; de Bruijn; H_I edge values (0, −0, denormal, inf, nan, text) | ASan/UBSan (alloc_dealloc_mismatch=0) | 1/2/4 |
| ea_conditioning | §3.1.5.1.1, §3.1.5.1.2, §3.1.5.2 | mpmath Output_Entropy: 1,849 vetted and 131 non-vetted cases (≤ 6.7e-20 relative, never high) | n_in = n_out, tiny/large h_in, n_in to 2^30, all-zero/constant `-i` | ASan/UBSan; `-DNDEBUG`+ASan | — |
| ea_transpose | (restart helper) | Python transpose, alphabets 2/16/256 and constant | short/odd sizes, `-l` parsing, write failure | ASan/UBSan | — |
| Shared I/O / CLI / JSON / hash | §3.1.1 provenance | strace of opens; LD_PRELOAD TOCTOU shim; valgrind | Empty, 1-byte, /dev/null, /proc, directory, spaces/unicode/leading `-`, every option malformed | ASan matrix of 18 error-path commands | — |
| Numerics / asserts | all estimator formulas | GCC FMA/no-FMA, clang-18 native/fast/SSE2, -O0: ≤ 2.2e-13 | All 104 asserts classified (I / R-tiny / R) with minimal inputs | `-DNDEBUG`+ASan for every reachable assert | — |

---

## 7. Negative evidence (attacked and held)

- **Baseline.** Release build: selftest on 11 NIST files, max delta 1.0e-13. ASan/UBSan build: same deltas and no sanitizer output.
- **No `ea_non_iid` path produced a too-high assessed figure.** Every predictor matched the literal §6.3.7–§6.3.10 reference exactly, apart from the prior rows F09 (too low) and F10 (no effect at the shipped constants).
- **Conditioning math.** Every step and MPFR rounding direction matched mpmath; the non-vetted min includes 0.999·n_out and h′·n_out with h′ per bit.
- **Restart.** Orientation, exact-length enforcement, sanity inequality, disjoint OpenMP writes, stale state (none), and pass/fail exit codes all held.
- **IID permutation machinery.** Rank and tie counting, early-exit equivalence, RNG quality and seeding, bz2 compression statistic buffers all held.
- **NaN at ≥10^6.** No producer in any executable. jsoncpp writes valid JSON for NaN, inf and −0. No verbosity-dependent JSON outside #251.
- **Thread count.** No effect on any deterministic output.
- **Compilers and platforms.** No decision flips across compilers, FMA settings or rounding modes.

---

## 8. Recommended GitHub actions (DRAFTS, NOT POSTED)

Priority order: N-01, N-02, R-2, R-1, N-03, N-04, then optional low-severity items.

### Draft A (N-01)
**Title:** `ea_iid`: binary chi-square independence reports "Passed" when m = 1; SP 800-90B §5.2.3 says the test fails

**Body:**
> §5.2.3 step 2: "Find the maximum integer m such that min(p0,p1)^m·⌊L/m⌋ ≥ 5 … If m is 1, the test fails."
>
> `binary_chi_square_independence` (cpp/iid/chi_square_tests.h:485-489) returns `score = 0, df = 0` for m < 2, and `chi_square_tests` then computes `chi_square_pvalue(0,0) = 1` and passes.
>
> Reproduction at 87c104d (10^6 1-bit samples with 3162 ones; 3163 is the boundary):
> ```
> python3 -c "import random;r=random.Random(3162);b=bytearray(1000000)
> for i in r.sample(range(1000000),3162): b[i]=1
> open('ones_3162.bin','wb').write(b)"
> ./ea_iid -vvv ones_3162.bin 1   # Chi square independence: T = 0, df = 0, P-value = 1 ... Chi square tests: Passed
> ```
> Full run: all IID tests pass, "IID": true, H_original = 0.004360. Per §5.2.3 the dataset should fail and go to the non-IID track, where ea_non_iid gives 0.003068.
>
> Scope: only extremely biased binary data (≤ ~0.32 % minority bits at L = 10^6).
>
> Suggested fix: treat m = 1 as a failure in `chi_square_tests`.

### Draft B (N-02)
**Title:** `ea_iid -c`: IID tests run on packed symbols instead of the conditioned binary string (§3.1.1 item 2, §3.1.5.2)

**Body:**
> In -c mode h' is computed from the bitstring (iid_main.cpp:282), but `chi_square_tests`, `len_LRS_test` and `permutation_tests` receive `data.symbols` (:316/:334/:352).
>
> §3.1.1 item 2 requires conditioned output to be "treated as a binary string for testing purposes", and §3.1.5.2 repeats this (see also the maintainer comment in #139).
>
> Reproduction (1e6 bytes (r<<4)|r, r a uniform nibble; true 0.5 bit/bit):
> - `ea_iid -c nib_dup.bin 8` passes all IID tests, h' = 0.998640.
> - `ea_non_iid -c` gives 0.403507.
> - The same data as a 1-bit bitstring fails independence (T = 330212, df = 2046, p = 0) and LRS (Pr = 3.4e-9).
>
> Suggested fix: run the §5 tests on `data.bsymbols` when `!initial_entropy`, or refuse `-c` in ea_iid.

### Draft C (R-2, reference #178)
**Title:** `ea_restart`: t-tuple/LRS "cannot run" (−1) still folded into H_r/H_c; the #178 fix did not cover restart_main.cpp

**Body:**
> restart_main.cpp:632/636/647/651 use `H_r = min(row_lrs_res, H_r)` etc. without the `>= 0` guard added elsewhere by #178.
>
> Reproduction: a 10^6-sample prefix of a de Bruijn B(256,3) sequence, `ea_restart -vv db256_3.bin 8 0.5`, gives "LRS Estimate: v<u", H_r = −1.000000, "Validation Testing Failed". The lowest estimate that ran is 0.585 > H_I/2.
>
> Fix: guard all four folds.

### Draft D (R-1, comment on #246 or new issue referencing it)
> The #248 fix removes accumulation drift, but the assert still fires when all symbol counts are exactly equal and 1/k rounds down in double (k = 3, 6, 7, 9, 12, … — 155 of the 247 non-power-of-two k).
>
> Reproduction: 1,000,002 shuffled samples of i%3, `ea_iid bal3.bin 2` gives lrs_test.h:626 assert, no JSON. Changing one symbol gives a normal run that passes. With -DNDEBUG the run completes.
>
> Suggest the "close to 1/k → 1/k" clamp you proposed in #246, or an exact integer Σc²/L².

### Draft E (N-03)
**Title:** `ea_conditioning -n -i`: all-zero conditioned dataset aborts (assert) instead of h' = 0; heap over-read with -DNDEBUG

### Draft F (N-04)
**Title:** `ea_restart`: H_I = "nan" passes validation and causes a float→int UB / SIGSEGV; non-numeric H_I is silently 0

### Optional (low)
- One "input/output hardening" issue collecting N-05, N-06, N-07, N-08, N-09 and N-11.
- One reporting issue for N-10.
- R-3 as a short note referencing #183 and commit 4d68e47.
- F09 and F14 are prior-local rows with no upstream item. F09 is too low and F14 needs > 25.8 Gbit; file only if you want completeness.

---

## Housekeeping

- **Repository.**
  - `git status --short` shows `?? NIST.SP.800-90B.pdf` and `?? full_source.txt`, plus ignored in-repo builds `cpp/ea_*` (15:52–15:54) and `cpp/selftest/*.res` (15:55–16:04).
  - **None of these were created by this audit.** All seven agent transcripts were checked; every build and run here used the scratch tree.
  - Timing and content (a concatenated source dump, and a spec PDF with its server timestamp) suggest the other audit session. Tracked files are unchanged: `git diff --stat HEAD` is empty.
  - HEAD `1d26ab310e4afd76f2c1e8783f1f8aedbe54cf33`.
- **Disclosures.**
  - apt packages installed at baseline: libdivsufsort-dev, libjsoncpp-dev, libmpfr-dev.
  - Agents fetched the SP 800-90B PDF from nvlpubs.nist.gov and three open PR diffs (read-only, curl/WebFetch).
  - One agent's `pip download` briefly placed a wheel in the repo root; it was moved out within a minute and is not present.
  - No GitHub writes of any kind during Phase 2.
- **Environment.** Linux 6.8.0-1064-azure x86_64, 2 vCPU. g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1), `-std=c++11 -fopenmp -O2 -ffloat-store -march=native` (upstream Makefile), libgomp. Sanitizer build `-O1 -g -fsanitize=address,undefined,float-divide-by-zero,float-cast-overflow`. clang-18 was used for differential checks.
