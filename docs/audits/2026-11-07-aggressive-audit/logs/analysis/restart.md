# Restart tests (§3.1.4) — analysis-phase record, audit 2026-11-07

Component: `cpp/restart_main.cpp` (1228 lines, read in full) plus the helpers it calls in
`cpp/shared/utils.h` (`read_file`, `calc_stats`, `parse_unsigned_decimal`, `free_data`, `sum`),
`cpp/shared/most_common.h`, `cpp/non_iid/markov_test.h`, `cpp/shared/TestRunUtils.h`
(prescan/refusal/report writer), `cpp/shared/test_run_base.h`, `cpp/iid/iid_test_case.h`,
`cpp/non_iid/non_iid_test_case.h`, `cpp/iid/permutation_tests.h` (data-copy and label
plumbing only), and the return-value clamps of every estimator the restart path folds in.

Branch `audit/2026-11-07`. Production binary on this host (NOT run in this phase):
`cpp/ea_restart` sha256 `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`
(built 2026-11-07 19:29, compile line in `logs/build-rebuild-2026-11-07.log:110`).

**No `ea_restart` run was made.** `read_file()` reads the whole file (`utils.h` `read_file`,
`dp->len = ftell(file)`) and `restart_main.cpp:694` then requires `data.len == MIN_SIZE`
(1,000,000) unconditionally — `EA_ALLOW_SHORT_DATASET` is not consulted on this path — so
every `ea_restart` run is a 1,000,000-sample run, which the brief classes as heavy. The one
probe executed is pure Python (no tool, no build): `logs/analysis/restart-cutoff-xcheck.py`,
output `logs/analysis-restart-cutoff-xcheck.log` (83.5 s, exit 0).

Everything below that was not executed is labelled **SOURCE-CONFIRMED** (read) or
**DERIVED** (follows from arithmetic), per the repository's own evidence grades.

---

## 1. The standard's algorithm, transcribed

### 1.1 Data construction — SP 800-90B §3.1.4.1 (PDF p. 21)

> "the entropy source shall be restarted r = 1000 times; for each restart, c = 1000
> consecutive samples shall be collected directly from the noise source. … The output
> samples are stored in an r by c matrix M, where M[i][j] represents the jth sample from
> the ith restart."
>
> "The row dataset is constructed by concatenating the rows of the matrix M, i.e., the row
> dataset is M[1][1] ||…|| M[1][c] || M[2][1] ||…|| M[2][c] || … || M[r][1] ||…|| M[r][c]."
>
> "The column dataset is constructed by concatenating the columns of the matrix M, i.e., the
> column dataset is M[1][1] ||…|| M[r][1] || M[1][2] ||…|| M[r][2] || …|| M[1][c] ||…|| M[r][c]."

Constants: r = c = 1000; matrix size 1,000,000 samples. §3.1.1 item 3 (PDF p. 19) repeats
"1000×1000 restart matrix M".

### 1.2 Validation testing — §3.1.4.2 (PDF p. 21)

> "First, the sanity check described in Section 3.1.4.3 is performed on the matrix M. If the
> test fails, the validation fails and no entropy estimate is awarded."
>
> "If the noise source does not fail the sanity check, then the entropy estimation methods
> described in Section 6.1 (for the IID track) or Section 6.2 (for the non-IID track) are
> performed on the row and the column datasets, based on the track of the entropy source.
> Let Hr and Hc be the resulting entropy estimates of the row and the column datasets,
> respectively. … If the minimum of Hr and Hc is less than half of HI, the validation fails,
> and no entropy estimate is awarded. Otherwise, the entropy assessment of the noise source
> is taken as the minimum of the row, the column and the initial estimates, i.e.,
> min(Hr, Hc, HI)."

Order of operations: sanity check → (only if passed) estimate rows and columns → gate
`min(Hr, Hc) < HI/2` (strict "less than") → award `min(Hr, Hc, HI)`.

Track: §6.1 (PDF p. 48) — "For sources with IID outputs, the min-entropy estimation is
determined using the most common value estimate described in Section 6.3.1." §6.2 (PDF
p. 48–49) — the ten estimators 6.3.1–6.3.10, "the minimum of all the estimates is taken",
and "The Collision, Markov and Compression estimates are only applied to binary inputs."

IID track precondition for restart data — §3.1.2 item 3 (PDF p. 19): "The row and column
datasets described in item 3 of Section 3.1.1 are tested using the statistical tests
described in Section 5 to verify the IID assumption, and the IID assumption is verified."
And: "If any of these conditions are not met, the estimation process shall follow the
non-IID track."

### 1.3 Sanity check — §3.1.4.3 (PDF p. 21–22)

> "The probability of type I error, denoted α, is set at 0.01 over the entire sanity check,
> where each of the 2000 binomial experiments has type I error probability of 0.000 005."
>
> "Only the experiment yielding the highest count is tested. If that experiment passes the
> test, then the other 1999 experiments will pass as well."
>
> 1. "Let p = 2^−HI. Let α be 0.000 005."
> 2. "For each row (1≤ i ≤ 1000) of the matrix, count the number of occurrences of each
>    sample present in the row. Set XRi to the highest count value for row i. Let XR be the
>    maximum count value for all the rows, i.e., XR = max(XR1,…, XR1000)."
> 3. (same for columns) "XC = max(XC1,…, XC1000)."
> 4. "Let Xmax = max(XC, XR)."
> 5. "Calculate P(X ≥ Xmax) = Σ_{j=Xmax}^{1000} C(1000, j) p^j (1−p)^{1000−j}. If
>    Pr(X ≥ Xmax) < α, the test fails. Otherwise, the test passes."

Bound direction: a one-sided UPPER tail; the test fails when the observed maximum is too
LARGE. The threshold is strict (`< α` fails; equality passes). No rounding rule, no
tolerance, no iteration — a closed form.

---

## 2. Spec → code mapping, with disagreements quoted

### 2.1 Data construction (§3.1.4.1)

| spec | code | verdict |
|---|---|---|
| r = c = 1000 | `restart_main.cpp:370` `int r = 1000, c = 1000;` | ✓ |
| matrix has exactly r·c samples | `:694` `if (data.len != MIN_SIZE)` → refuse; `MIN_SIZE` is 1,000,000 (`utils.h:42`) | ✓ exact, both directions (a 1,000,001-byte file is refused) |
| row dataset = file as given | `:714` `rdata = data.symbols;` | ✓ (`read_file` translates symbols down to 0..k−1, a bijection — counts and estimates are unchanged) |
| M[i][j] at offset i·c + j | `:769` `rdata[i * r + j]` | ✓ numerically, because r == c; see S7 — the stride written is `r` where the row stride is `c` |
| column dataset = M[·][0] ‖ M[·][1] ‖ … | `:782` `cdata[j * c + i] = rdata[i * r + j];` for j in 0..c−1, i in 0..r−1 | ✓ column j occupies `cdata[j·1000 .. j·1000+999]`, element i = M[i][j] |
| raw (untranslated) column copy for the IID permutation tests | `:783` `crawdata[j * c + i] = data.rawsymbols[i * r + j];` | ✓ |

### 2.2 Sanity check (§3.1.4.3)

| step | code | verdict |
|---|---|---|
| 1. p = 2^−HI | `:76` `powl(2.0L, -(long double) H_I)`; `:117` same | ✓ (HI already on the per-symbol scale after `:636-658`) |
| 1. α = 0.000005 | `:740` `alpha = 0.000005;` | ✓ exact; recorded in the report as `restartAlpha` (`:795`) |
| 2. XRi, XR | `:762-772` per-row `counts[256]` reset, `X_i` running max, `X_r = max` | ✓ |
| 3. XCi, XC | `:775-787`, computed while transposing | ✓ |
| 4. Xmax | `:790` `X_max = max(X_r, X_c);` | ✓ |
| 5. printed formula | `:74-87` `printedBinomialBound()` — sums `P(X = x)` from x = 1000 down, returns the first x at which the tail reaches α, i.e. the LARGEST x with P(X ≥ x) ≥ α | ✓ exactly the spec's rule: Xmax ≤ that x ⇔ P(X ≥ Xmax) ≥ α ⇔ pass. Reported as `restartXcutoffPrintedBinomial` (`:798`) and printed (`:757`); **not the verdict** |
| 5. decision | `:810` `if (X_max > X_cutoff)` → "Restart Sanity Check Failed", `errorClass` "statistical", exit 255 | ✓ sign and strictness match "counts equal to the cutoff pass, larger fail" |
| 5. the deciding cutoff | `:754` `X_cutoff = exactMultinomialMaxBound(alpha, H_I);` (`:146-150`) — smallest m with P(max cell ≤ m) ≥ 1−α under the worst-case cell family, by Levin's representation (`:113-142`) | **DOCUMENTED DIVERGENCE `C23`** (FORK-DIVERGENCE-AND-TRUST.md §B). The code matches the documented decision: exact multinomial maximum decides, printed figure recorded beside it, `restartCutoffMethod` = `"exact-multinomial-maximum"` (`:805`). No build sets the audit knobs (`grep EA_RESTART_ cpp/Makefile .github/workflows/` → none). |

**Exact-equality convention.** Spec: pass iff P(X ≥ Xmax) ≥ α. Code: pass iff Xmax ≤ m*, m* =
min{m : cdf(m) ≥ 1−α}. These coincide except when P(max ≥ m*+1) equals α exactly, where the
spec passes and the code fails — the conservative side, and measure-zero in floating point.
Not a finding.

**Direction of the C23 divergence, stated plainly because the brief asks.** Wherever the two
cutoffs differ, the exact one is strictly larger, so there IS a band of Xmax values that
§3.1.4.3 step 5 as printed REJECTS and the fork ACCEPTS. From the probe log (every pin):

```
H_I=1     X_max in [571, 572]      H_I=4     X_max in [100, 104]      H_I=7     X_max in [24, 27]
H_I=2     X_max in [313, 316]      H_I=5     X_max in [59, 63]        H_I=8     X_max in [16, 19]
H_I=0.25/0.5/0.75: none (cutoffs coincide)
```

That band is the documented decision itself (the printed formula tests a single binomial
cell, the statistic formed is the max over cells; implementing the text rejects 82.5–83.2 %
of full-entropy 8-bit matrices). What this audit had to establish is that the fork accepts
NOTHING the correct statistic rejects — i.e. that `maxCellCdf()` is not permissive by
implementation error. That is the probe in §2.3.

**Worst-case family.** `:119-120` `kfloor = floor(1/p)`, `rem = 1 − kfloor·p` (used if
> 1e-15): floor(1/p) cells at probability p plus one remainder cell — Hill 3.a.i and
upstream's `k_effective`. For a fixed max-probability p this maximises P(max cell > m): any
redistribution of mass away from cells at p to cells below p lowers each such cell's
exceedance probability. Accepted as the modelling choice the documented decision names; not
re-derived here. Note it is a supremum over ALL alphabets of that shape, not over the
observed alphabet of the restart file (S9).

### 2.3 Independent cross-check of the deciding cutoff (EXECUTED, Python only)

`restart_main.cpp:maxCellCdf()` and the fork's oracle
`audits/2026-10-11-independent-audit/oracles/restart_multinomial_max.py` use the SAME
method (Levin's representation) in floating point, and the oracle's brute-force validation
reaches only n ≤ 20. So the 32 pins in `regression-restart.sh` are the method checked
against its own copy at n = 1000 ("an oracle can verify its own copy").

`logs/analysis/restart-cutoff-xcheck.py` recomputes every pinned cutoff by a different
method — direct coefficient extraction from the generating function
P(all cells ≤ m) = n!·[x^n] ∏_j E_m(p_j x), E_m(y) = Σ_{i≤m} y^i/i!, in 60-digit Decimal,
with the same cell family — plus the printed binomial from an exact `Fraction` (integer HI)
or 60-digit Decimal, plus a THIRD method for the two-cell (width-1) case, the closed form
P(n−m ≤ X ≤ m). Result (`logs/analysis-restart-cutoff-xcheck.log`):

```
pins: 32 checked, 0 mismatches          (deciding AND printed columns, each straddle verified:
                                          1-cdf(d-1) > 5e-6 >= 1-cdf(d) at every pin)
H_I=0.696               printed=684 deciding=684   MATCH  (device operating point)
H_I=0.9661822653793894  printed=581 deciding=582   MATCH  (OC-49 counterexample)
H_I=log2(3)             kfloor=2 rem=0.333 → 400 / 404   (kfloor-boundary robustness: same cells either way)
```

What this establishes: the integer cutoffs the regression asserts the C++ prints are the
correct quantiles of the stated statistic, by a computation that shares no code and no
algorithm with the C++ or the oracle. What it does not establish: that the C++ binary on
this host prints them — that link is `regression-restart.sh`'s C23 block (64 comparisons)
and the x86-64 CI gate `"restart regression" … "regression-restart: PASS"`
(`.github/workflows/x86-64-platform-facts.yml:400,493`), neither re-run here.

### 2.4 Validation testing (§3.1.4.2)

| spec | code | verdict |
|---|---|---|
| sanity check first; fail ⇒ no estimate | `:810-826` exits before any estimator runs | ✓ |
| IID track: §6.1 = MCV on rows and columns | `:858` `most_common(rdata, …)`, `:865` `most_common(cdata, …)`; H_r, H_c = min(MCV, word_size) (`:839-840, 863, 868`) | ✓ |
| IID track precondition (§3.1.2 item 3): §5 tests on row AND column datasets | `:1093-1095` chi-square rows ∧ cols; `:1118-1120` LRS rows ∧ cols; `:1127-1135` permutation rows ∧ cols (only if the first two passed) | ✓ both datasets, conjunction |
| §3.1.2: IID not verified ⇒ "shall follow the non-IID track" | `:1149-1167` awards NO IID restart estimate, h_r/h_c/h_i = −1, errorLevel 2, exit 1 | **DOCUMENTED (`D-5`)**: fail-closed; the operator must re-run `-n` with the non-IID HI. Conservative relative to the text. Line numbers cited in FORK-DIVERGENCE (`:1139`, `:1155`) are current. |
| non-IID track: ten estimators of §6.2 on rows and columns, min over all | `:858-1088`: MCV; if `alph_size == 2` Collision/Markov/Compression (`:883-951`); t-Tuple and LRS via `SAalgs` (`:964-1003`); MultiMCW, Lag, MultiMMC, LZ78Y (`:1013-1088`); each folded by `H_r = min(ret, H_r)` | ✓ all ten; binary-only trio gated on alphabet size, which is the spec's "binary inputs" |
| gate: min(Hr, Hc) < HI/2 ⇒ fail | `:1177` `if (min(H_r, H_c) < H_I / 2.0)` → exit 255, `errorClass` "statistical" | ✓ strict, direction correct |
| award min(Hr, Hc, HI) | `:1222` prints `min(min(H_r, H_c), H_I)`; JSON "Overall" carries `h_r`, `h_c`, `h_i` (`:1199-1205`) | ✓ computed; **the JSON has no field holding the minimum** (S2) |

**Initialisation and the `>= 0` guards (R-2).** H_r and H_c start at `word_size` (`:839-840`),
the maximum possible per-symbol min-entropy, so the min is over the estimators that produced
a value. Every fallible estimator is folded only `if (ret >= 0)`. That guard is exact —
no estimator can return a negative number other than the −1 sentinel, so nothing real is
ever dropped (the dropping direction would be an overstatement, so this was checked
estimator by estimator):

| estimator | final expression | range |
|---|---|---|
| MCV `most_common.h:30-31` | `ubound = min(1.0, …)`; `-log2(ubound)` | [0, log2 k] |
| Markov `markov_test.h:105` | `fmin(H_min/128.0, 1.0)`, every term `-log2(P)` with P ≤ 1 | [0, 1] |
| Collision `collision_test.h` | `X = max(X, 2.0)`; `p = 0.5 + sqrt(1.25 − 0.5X)` for X < 2.5 else p = 0.5 | p ∈ [0.5, 1] ⇒ [0, 1] (`-log2(1.0)` is `-0.0`, and `-0.0 >= 0` is true, so a zero estimate is kept) |
| Compression | `p = fmin(fmax(lbound, hbound), hdomain)`, `hdomain = 1.0` (`:170,201`); `-1.0` sentinel at `:38` | [0, 1] ∪ {−1} |
| t-Tuple / LRS `lrs_test.h:254-259, 326-331` | `pu` clamped to `1.0L` if above; `-log2l(pu)`; `-1.0` sentinel | [0, ∞) ∪ {−1} |
| four predictors → `predictionEstimate()` `utils.h` | `curMax = fmax(1/k, p_globalPrime ≤ 1, p_local)`; `calc_p_local` returns within `[ldomain, hdomain = 1.0]` on every exit path | (0, log2 k] |

**NaN.** `std::min(ret, H_r)` is `(H_r < ret) ? H_r : ret`, so a NaN `ret` would REPLACE
H_r and the next estimator would then replace the NaN, discarding every earlier minimum —
the hazard the brief names. It is unreachable here: MCV and Markov (the two unguarded
folds) cannot produce NaN with `alph_size ≥ 2` and `len = 10^6` (`alph_size ≤ 1` is refused
at `:677`; Markov's `-log2(P_0)`, `-log2(P_1)` need both symbols present, which `alph_size
== 2` guarantees, and every conditional branch is gated on the probability being > 0); the
guarded folds drop a NaN (`NaN >= 0` is false) rather than fold it. `predictionEstimate`'s
F13/OC-58 argument-order note covers its own NaN path. SOURCE-CONFIRMED.

**IID-mode shallow copy** (`:1131` `memcpy(&data_col, &data, sizeof(data))`, then
`symbols`/`rawsymbols` repointed at the column arrays): sound, because
`permutation_tests()` copies `dp->symbols`/`dp->rawsymbols` into fresh arrays before
shuffling (`permutation_tests.h:633-657`), reads `alph_size`, `len`, `maxsymbol` (all
permutation-invariant) and never touches `bsymbols`; `calc_stats` (mean of raw, median of
translated) is permutation-invariant so sharing it between rows and columns is correct.

### 2.5 HI intake (C16) and the scale

`:160-187 parseHIArgument()` — decimal grammar, optional `/symbol` or `/bit`, refuses hex,
inf, nan, whitespace, trailing text, ERANGE, non-finite. `:581` refuses `H_I <= 0`.
`:636-658` resolves `/bit` as `H_I * word_size` and REFUSES a bare number when
`word_size > 1`. `:660` refuses `H_I > word_size`. All after `read_file`, so `word_size`
may be INFERRED (`bitsPerSymbolInferred`, `:629,631`): the `/bit` multiplier is then the
data's evident width, never larger than the true width, so a wrong inference can only lower
HI (conservative).

### 2.6 Intake, report and exit paths touched by this component

- `:694` exact-size refusal; `:677` one-symbol alphabet refusal; `:601` read failure.
- Sanity-check inputs and verdict in every report (`test_run_base.h:85-93`):
  `restartHI` (full-precision double), `restartAlpha`, `restartXmax`, `restartXcutoff`,
  `restartXcutoffPrintedBinomial`, `restartCutoffMethod`, `passedRestartSanityCheck`.
- `-i` failure paths write `testRunIid`, `-n` paths write `testRunNonIid` (R-3 repair ✓ at
  `:601-624`, with the read error's message carried across).
- `-s`: parsed, `inul < 5,000,000` → `print_usage()` (`:454`), otherwise ignored (`:753`).

---

## 3. Prior repairs in this component and how to try to break each

Commits (git log of `cpp/restart_main.cpp`): `db7a2ba` N-04 · `23dca69` R-3 · `d892b90` R-2 ·
`fd83a43` N-06 · `47d6624` N-09 · `6f84ad7` C-01 · `c01fb43` N-07 · `a3dde6f`/`007d0e7`
IID #153/#252 · `031d7ee` N-08 · `094189c` N-10 · `25fbb54` NOVEL-03 · `a5005bd` C16+C23
(superseded) · `7a0be01` C23 corrected · `97bfc6c` C14 · `663f9ae` A05/A04 · `36cafb3` OC-104.
Regression: `cpp/selftest/regression-restart.sh` (N-04, N-06, N-08, N-10, R-2, R-3,
NOVEL-03, C16, C23), `sanitizer-restart-c01.sh` (C-01).

| repair | what it guarantees | how I would try to break it |
|---|---|---|
| **N-04 / C16** strict HI parse | finite decimal, > 0, scale stated for width > 1 | `$'3\n'`, `+3`, `3/BIT`, `.5`, `5.`, `3e+0`, `1e5/bit` (→ refused by `> word_size`), `1e-300` (ACCEPTED — see S3), `0x1p3`, `3 /symbol`. Width-inferred `/bit` (`ea_restart file 0.9/bit` with data max 3 → ×2). `-i` and `-n` both. Expected: all refused except `.5`, `5.`, `3e+0`, `1e-300`. |
| **C16 scale** | `/bit` × word_size equals `/symbol` | `0.875/bit` vs `7/symbol` at width 8 (pinned by the regression); at width 1 a bare `0.9` vs `0.9/bit` vs `0.9/symbol` must all give the same cutoff (the first is the only bare form accepted). |
| **C23 exact cutoff** | deciding = exact multinomial max; printed recorded; both pinned at 32 HI | Independent recomputation by a different method — DONE, 32/32 + 2 record points (§2.3). Remaining: knife-edge HI where \|cdf − (1−α)\| ≲ 1e-15 could differ between 64-bit and 80-bit `long double` (S13); `log2(3)`-type kfloor boundaries (checked: same cells either way). Forced-count matrices at `[printed+1, deciding]` and `deciding+1` (E1, E2). |
| **R-2** sentinel not folded | −1 never enters H_r/H_c | Any estimator returning a non-sentinel negative would be DROPPED (overstating) — checked every clamp, none can (§2.4 table). De Bruijn B(100,3) still declines LRS (precondition asserted by the regression). Also check the symmetric case: a declined estimator on COLUMNS only (transpose the de Bruijn matrix; E10). |
| **R-3** | `-i` read failure reports errorLevel −1 in the IID JSON | declared width narrower than the data (`r8.bin 4`) in both modes; absent file; FIFO/dir (regression-nonregular covers the other tools, not restart). |
| **N-06** | no invented sha256 | absent file both modes; a valid run's hash matches `shasum`. |
| **NOVEL-03** | permutation groups labelled `rows`/`columns` | the unit test `restart-report-label-test` builds the labels synthetically; a full `-i -o` run on a passing matrix would show 6 `permutationTestResults` with `dataLayout` alternating by group (heavy; not run). |
| **C-01** | `delete[]` | only compiled in the `EA_RESTART_WITHOUT_C23_FIX` build path; dead in production. `sanitizer-restart-c01.sh` is the control. |
| **D-5 / #252** | no IID estimate after any required IID failure | checkerboard `((i + i//1000) & 1)` fails an IID test deterministically before permutation (regression N-10 uses it); verify exit 1, errorLevel 2, `h_*` absent (−1 omitted), `IID: false`, `assessmentComplete: true`. Note S5: no `errorClass` on this path. |
| **C14 / A05 / F03 / N-09** report writer | placeholder claimed at `-o` parse; input never overwritten; failed write ⇒ nonzero exit | `-o <input>`; `-o <symlink to input>`; `-o /dev/full`; `-o` into a missing directory; all three failure classes should leave the capture byte-identical (regression-output-aliasing covers restart). |
| **OC-104** | option after operand refused; numeric after operand allowed | `ea_restart f 1 -q` refused; `ea_restart f 1 -1` → grammar refusal (not the option refusal); `ea_restart f 1 -inf` → grammar refusal on BSD, usage path on glibc (N-04 note). |

---

## 4. Edge-case inputs that distinguish a correct from an incorrect implementation

All are 1000×1000 (exactly 1,000,000 bytes), so each is a heavy run for the execution
phase. Generators exist for E1/E5 (`audits/2026-10-11-independent-audit/generators/c23_forced_count.py`,
`audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py`).

| id | construction | why it distinguishes |
|---|---|---|
| **E1** forced count at the C23 band, width 8 | uniform bytes seeded; in column 17 clear incidental zeros then force exactly X zeros; X ∈ {15, 16, 19, 20}, HI = `8/symbol` | 15 passes everywhere; 16–19 pass only on the exact statistic (printed rejects); 20 must fail on both. A wrong `maxCellCdf` that is too permissive would pass 20. |
| **E2** OC-49 point, width 1 | random bits; force one row to exactly 582 zeros (others ~500); HI = `0.9661822653793894` | exact cutoff 582 (pass), printed 581 (reject); X = 583 must fail on both. Width-1 case where the two-sided tail matters. |
| **E3** device operating point | as E2 with 684 then 685 zeros in one row, HI = `0.696` | 684 passes, 685 fails on BOTH cutoffs — the point the project's acceptance decision will be read at. |
| **E4** equality at the cutoff | X = 27 at HI = `7/symbol` (and 28) | "counts equal to the cutoff pass" convention; an off-by-one in `:810` (`>=`) would reject 27. |
| **E5** declined estimator visible? | de Bruijn B(100,3) (`gen_debruijn.py 100 11`), width 8, `-n -o` | LRS declines (`v<u`): H_r must not be −1 (R-2), AND the JSON should say the LRS literal estimate was not run — it currently cannot (S1). Compare with `ea_non_iid -o` on the same bytes, which carries `literalEstimateNotRun: true`. |
| **E6** validation-gate boundary | iid Bernoulli(p₀) bits, width 1, HI = `1`: p₀ = 0.7071 gives MCV p_u ≈ 0.7083 → H ≈ 0.4976 (fail); p₀ = 0.70 gives ≈ 0.512 (pass) | exercises `< H_I/2` strictness and the direction of the gate with the MCV bound at ZALPHA. |
| **E7** tiny HI | any passing 1-bit matrix with HI = `1e-300` | both cutoffs 1000, gate `min(H_r,H_c) < 5e-301` vacuous → exit 0 "Validation Test Passed" (S3). Negative controls: `1e-400` (ERANGE) and `0` refused. Figure printed ≤ 1e-300, so not an overstatement — a vacuous acceptance. |
| **E8** alphabet narrower than HI implies | width 8 declared, bytes uniform over 100 values, HI = `7/symbol` | sanity cutoff is computed for 128 cells (S9); sanity passes with appreciable probability although log2(100) = 6.64 < 7; the figure is still capped by H_r ≈ 6.5. Shows the gate's independence from `alph_size` and that the figure is not overstated. |
| **E9** restart-position dependence | random bits; first 50 samples of EVERY row biased p(0) = 0.9 (or constant 0) | columns 0..49 carry the bias → X_c ≈ 900+ (or 1000) → sanity fails at any HI > ~0.15 — the column view catching exactly the §3.1.4 bullet "independent of its position in the restart sequence". A row-only implementation would pass. |
| **E10** transpose symmetry | any matrix M and its transpose Mᵀ | X_max identical; H_r(M) = H_c(Mᵀ) and vice versa; any asymmetry is a construction bug (`:769,782`). Cheap and decisive for index errors. |
| **E11** alphabet of two with width 8 | bytes in {0,1} only, declared 8; HI `0.9/bit` vs `0.9/symbol` | `/bit` → 7.2 → sanity fails (X_max ≥ 500 vs cutoff ~25); `/symbol` → 0.9 → binary-only estimators run (`alph_size == 2`), labels print "/ 1 bit(s)". Confirms the scale is applied per symbol and that `alph_size`, not `word_size`, selects the binary trio (upstream `afad536`). |
| **E12** 1,000,001 and 999,999 bytes | otherwise valid data | both refused by `:694`; `EA_ALLOW_SHORT_DATASET=1` must NOT relax it. |

---

## 5. Suspicions and observations (labelled; nothing here was executed against the tool)

Ranked by the brief's table. **None overstates the figure.** The figure is
`min(H_r, H_c, H_I)` and the paths that could raise it — a dropped real estimate, a NaN
fold, a too-permissive cutoff — were each closed above (§2.3, §2.4).

| id | severity | direction | what | where | evidence grade |
|---|---|---|---|---|---|
| **S1** | LOW (report completeness; the project itself called this direction out) | neutral | A declined estimator is silently omitted from the restart JSON: `literal_not_run` is never set in `restart_main.cpp` (grep: 0 hits) while `non_iid_main.cpp` sets it at 16 sites. `test_case_base.h:26-31`: the flag exists so "a consumer could not tell that the reported minimum had been taken over fewer estimators than the standard lists, which can only make the figure higher". R-2 (`d892b90`) made the decline silent in restart. | `:972-1001` and every `if (ret >= 0)` block | SOURCE-CONFIRMED |
| **S2** | LOW | neutral | No field in the JSON carries `min(H_r, H_c, H_I)`; "Overall" has `h_r`, `h_c`, `h_i` only, and `-q` suppresses the one place the minimum is printed (`:1220-1223`). README says the tool "returns min(H_r, H_c, H_I)". A consumer reading `h_i` alone would overstate; that is a consumer error the report invites. | `:1199-1205`, `non_iid_test_case.h:40-45` | SOURCE-CONFIRMED |
| **S3** | LOW | neutral (vacuous acceptance; awarded figure ≤ HI) | For 0 < HI < ~1.6e-16 (binary64 `long double`, this host) `2^-HI` rounds to exactly 1.0L and both cutoffs return 1000 (`:77`, `:118`); for HI < 0.0176 the printed cutoff is 1000 by the statistic itself (p^1000 ≥ α). The validation gate at HI/2 is then vacuous and the run exits 0 "Validation Test Passed" on any 2-symbol input. C16 refuses `0` and `1e-400` (ERANGE) but accepts `1e-300`. Rounding fact executed in Python (probe log, last block). | `:581`, `:77`, `:118`, `:1177` | DERIVED + partial EXECUTED |
| **S4** | LOW | neutral | `-s` is documented "accepted for compatibility and ignored" (`:205-206`) but a value below 5,000,000 is refused through `print_usage()` with no reason (`:454-455`). | `:449-459` | SOURCE-CONFIRMED |
| **S5** | LOW | neutral | IID-suite failure report has `errorLevel 2` and NO `errorClass`, unlike every other failure path (`statistical`/`input`/`internal`). A consumer classifying by `errorClass` cannot file it. | `:1154-1155` | SOURCE-CONFIRMED |
| **S6** | LOW | neutral (fail-closed) | On validation failure in `-i` mode the report carries no test cases at all (`tcOverallIid` pushed only after the gate at `:1196`; `tc631Iid` is built at `:854-861` and never pushed) — no `h_r`/`h_c`/`h_i` to explain the failure. The `-n` failure report has the per-estimator cases but not "Overall". | `:1177-1193` | SOURCE-CONFIRMED |
| **S7** | LOW (latent) | neutral | Index arithmetic uses `i * r + j` for row i (stride should be `c`) and `j * c + i` for column j (stride should be `r`). Correct only because `r == c`. | `:769`, `:782-783` | SOURCE-CONFIRMED |
| **S8** | LOW (interpretive; identical to upstream) | unknown | Rows and columns get the Literal estimators only; no bitstring estimation for width > 1. §3.1.4.2 invokes §6.2, whose list (PDF p. 49) is the ten estimators; the bitstring conversion is prescribed in §3.1.3 for the sequential dataset. Defensible reading; the figure is capped by HI which already includes n×H_bitstring. A restart-specific weakness visible only in the bitstring view would be caught only by the HI/2 gate. | `:858-1088` | SOURCE-CONFIRMED |
| **S9** | LOW | neutral | Upstream's `simulateBound` asserted `k_effective <= alph_size` (`:303`); the exact method has no such check, so an HI exceeding log2(alph_size) of the restart file is accepted and the cutoff is computed for a hypothetical 2^HI-cell alphabet — a slightly weaker gate than a k-restricted model. The figure is still capped by H_r (MCV ≤ log2 k). Upstream #195 was the crash side of the same condition. | `:146-150` | DERIVED |
| **S10** | LOW (doc) | neutral | Two false-reject rates are quoted for the printed cutoff at 8 bits without naming the sample: 82.5 % (`:38`, 20,000-matrix run) and 83.2 % (FORK-DIVERGENCE §B C23, `restart_decision_exact.py` header; 2,000-matrix run). Both are in `logs/c23/fullmatrix-false-reject.log`. Also `regression-restart.sh` N-10 comment says "cutoff 570" at HI = 1; the deciding cutoff is 572. | — | SOURCE-CONFIRMED |
| **S11** | LOW (report) | neutral | Restart calls the `most_common()` wrapper with a dummy `TestCaseBase` (`most_common.h:51-55`), so the restart JSON's MCV case has no `mcvEstimateMode`/`PHat`/`PU` — H_r's MCV cannot be recomputed from the report. | `:858,865` | SOURCE-CONFIRMED |
| **S12** | — (by design) | nondeterministic | `-i` verdict depends on `/dev/urandom`-seeded permutations (`permutation_tests.h`); borderline matrices can flip between runs. Inherent to §5.1; not a defect. | `:1127,1134` | SOURCE-CONFIRMED |
| **S13** | — (negligible) | nondeterministic across platforms | `long double` is 64-bit on Darwin arm64 and 80-bit on x86-64; a cutoff could differ by one at an HI where \|cdf(m) − (1−α)\| ≲ 1e-15. The 32 pins pass on both (CI gate). Probability over a generic HI ~1e-9. | `:113-142` | DERIVED |

### Documented divergences met in this component (not findings)

- **C23** — the deciding cutoff is the exact multinomial maximum, not step 5's printed
  binomial; code matches the documented decision at `:146-150`, `:754`, `:805`; band of
  accepted-but-text-rejected Xmax values listed in §2.2; independently confirmed in §2.3.
- **D-5** — no IID restart estimate after an IID rejection; `:1125-1167` as documented.
- **D-6** — out-of-width data refused by `read_file` ("does not fit within described bit
  width"), reached through `:601`.
- **OC-104** — option after operand refused at `:407`; numeric values exempt.
- **≥ 1,000,000 intake** — stricter here: exactly 1,000,000, no escape.

### What this analysis does not establish

- That the production binary prints the pinned cutoffs: not run here (every run is heavy).
  The link is `regression-restart.sh` + the x86-64 CI gate, neither re-executed today.
- Anything about the estimators' internals (`SAalgs`, predictors, compression, collision)
  beyond their return-value clamps; other agents own those.
- That the near-uniform family is the worst case for the max-cell statistic; accepted from
  Hill 3.a.i / upstream, not proved here.
- Windows: `seed()` aborts `-i` there (recorded elsewhere); the `-n` path is unexamined by me.
