# Aggregation: how H_original, H_bitstring and the assessed min-entropy are formed

Audit: 2026-11-07 aggressive audit, analysis phase. Component: `cpp/non_iid_main.cpp`
lines 344-680 (the `-a`/`-t` gate, the per-estimator `min()` folds, `h_assessed`,
the printed and JSON figures), with `cpp/non_iid/non_iid_test_run.h`,
`cpp/non_iid/non_iid_test_case.h`, `cpp/shared/test_run_base.h`,
`cpp/shared/test_case_base.h`, `cpp/shared/TestRunUtils.h` (report writer), and the
return conventions of every estimator the folds consume.

Branch `audit/2026-11-07`, HEAD `5f79f74`. Binary measured:
`cpp/ea_non_iid` sha256 `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`
(Darwin arm64, Apple clang 21, `-O2`, asserts ON: `cpp/Makefile` line 51 defines no
`NDEBUG`). Every probe below used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` on
inputs of 5,000 and 20,000 samples; **none is a compliant assessment** and every
report carries `nonCompliantShortDataset: true`.

Headline: **no code-versus-spec defect in the aggregation arithmetic itself.** The
folds compute exactly §3.1.3's `min(H_original, n x H_bitstring)` and §3.1.5.2's
`h'`, bit-for-bit (measured). What this component DOES expose, ranked by the brief:

| # | item | direction | status |
|---|---|---|---|
| 1 | width inference narrows `n` and RAISES `n x H_bitstring` (+21.9 % measured here) | overstates vs the spec at the declared `n` | re-measurement of tracker **F02**; the fork's repair was visibility only, the figure still rises; decision left upstream (#254) |
| 2 | `std::min` folds are not NaN-safe; a NaN at an unguarded site discards earlier minima, and a NaN reaching the final fold yields `word_size` | overstates IF reached | tracker **F13**, `UNCONFIRMED`; this analysis finds **no producer at >= 10^6** either (every estimator's codomain is bounded below); the OC-58 hardening was applied inside two helpers, NOT at the six folds in `main()` |
| 3 | under `-c`, the line labelled `Assessed min entropy` and JSON `hAssessed` are `word_size x h'`, labelled identically to the `-i` per-symbol figure; at verbose >= 3 no `h'` line exists | neutral in the code; 8x overstatement for a consumer that reads it as per-bit | tracker **F23** sub-claim, now **CONFIRMED by measurement** |
| 4 | `-t` keeps the first 1,000,000 bits for the bitstring estimators only | either (spec-permitted) | §3.1.3 "may be ignored"; under `-c` it is **F20**, `NOT-A-BUG` per maintainers |
| 5 | `utils.h` `n_choose_2` comment says `non_iid_main.cpp` refuses > INT_MAX samples; it does not | neutral | harmless: `n_choose_2` is reached only from the IID §5.2.5 test (`lrs_test.h:713`), never from `ea_non_iid` |
| 6 | "Symbols appear to be narrower than described" sets `errorMsg` with `errorLevel` 0, so JSON never carries it | neutral | LOW, reporting |

---

## 1. The spec, step by step

### 1.1 §3.1.3 Initial Entropy Estimate (PDF p. 20)

> "After determining the entropy estimation track, a min-entropy estimate per sample,
> denoted as Horiginal, for the sequential dataset is calculated using the methods
> described in Section 6.1 (for the IID track) or Section 6.2 (for the non-IID track).
> If the alphabet size is greater than 256, it shall be reduced to at most 256 symbols
> (see Section 6.4)."

> "If the sequential dataset is not binary, an additional entropy estimation (per
> bit), denoted Hbitstring, is estimated. First, the sequential dataset that contains
> L samples (each having n bits) is considered as a bitstring of size nL. The bits
> after the first 1 000 000 bits may be ignored. Then, the estimation is done based on
> the entropy estimation track, as specified in the previous paragraph, and Hbitstring
> is calculated. Then, the entropy per sample is estimated to be n x Hbitstring."

> "The initial entropy estimate of the noise source is calculated as
> HI = min (Horiginal, n x Hbitstring, Hsubmitter) for non-binary sources and as
> HI = min (Horiginal, Hsubmitter) for binary sources."

Steps, constants, directions:

| step | quantity | rule | bound direction |
|---|---|---|---|
| S1 | `H_original` | §6.2 minimum over the ten estimators on the L samples (alphabet A, `k <= 256`) | each estimator is an upper-confidence-bound on p_max, hence a lower bound on min-entropy; the min over them is a lower bound |
| S2 | binary? | "If the sequential dataset is not binary" — the standard defines binary by the alphabet (§4.4.2/§5; tracker F01 WITHDRAWN) | — |
| S3 | bitstring | the `L` samples of `n` bits read as `nL` bits; "the bits after the first 1 000 000 bits MAY be ignored" (permissive, not required) | — |
| S4 | `H_bitstring` | §6.2 minimum over the estimators on the bitstring (`k = 2`, so Collision/Markov/Compression apply) | per bit, `<= 1` |
| S5 | per-sample | `n x H_bitstring` | `<= n` |
| S6 | `H_I` | `min(H_original, n x H_bitstring, H_submitter)` non-binary; `min(H_original, H_submitter)` binary. The tool does not know `H_submitter` and reports the min of the other terms (usage text lines 49-50 says so). | min: lower bound |

No rounding rule, tolerance or termination condition is stated for this section; `n`
is "each having n bits", the submitter's sample width (§3.2.2 requirement 6 per
tracker F02).

### 1.2 §6.2 Non-IID Track (PDF p. 49)

> "For non-IID data, the following estimators shall be calculated on the outputs of
> the noise source and outputs of any conditioning component that is not listed in
> Section 3.1.5.1.1, and the minimum of all the estimates is taken as the entropy
> assessment of the entropy source for this Recommendation:" [ten estimators listed]
> "The Collision, Markov and Compression estimates are only applied to binary inputs."

So: ten estimators for binary input (all apply), seven for non-binary (`k > 2`), and
the assessment is the MINIMUM. The standard does not say what to do when an estimator
cannot be computed (e.g. LRS with `v < u`); upstream's position (#255, quoted in
`test_case_base.h` lines 32-36) is that this is not an error. The fork records it
(`literalEstimateNotRun` / `bitstringEstimateNotRun`, F05).

### 1.3 §3.1.5.2 Non-vetted Conditioning Components (PDF p. 25)

> "...the entropy of the conditioned sequential dataset (as described in item 2 of
> Section 3.1.1), which shall be computed using the methods described in either
> Section 6.1 (for IID data) or Section 6.2 (for non-IID data). Let the obtained
> entropy estimate per bit be h'."

> "The output of the conditioning component (nout) shall be treated as a binary
> string, for purposes of the entropy estimation."

> "hout = min(Output_Entropy(nin, nout, nw, hin), 0.999 nout, h' x nout)."

So under `-c` the standard's deliverable from THIS tool is `h'`, **per bit**, of the
conditioned output read as a bitstring. The multiplication by `nout` happens in
`hout`, with `nout` = the conditioning function's output width, which this tool does
not know (`ea_conditioning` does). Nothing in §3.1.5.2 multiplies `h'` by the packing
width of the file.

### 1.4 §6.4 Reducing the Symbol Space (PDF p. 66)

> "...it would be reasonable to truncate the 32-bit sample to a 4-bit string by taking
> the lower 4 bits, and perform the tests on the 4-bit strings. Of course, it must be
> noted that in this case, only a maximum of 4 bits of min-entropy per sample could be
> credited to the noise source."

> "Note that after the mapping is performed, the maximum amount of entropy possible per
> n-bit sample is m bits."

Relevant here only as the cap: the per-sample figure can never exceed the assessed
width. The tool's alphabet is at most 256 so no reduction is performed.

### 1.5 §3.1.1 (PDF p. 17-18) — intake

The ">= 1,000,000 samples" requirement is enforced at `utils.h:294`
`dataset_meets_minimum()` on the LOADED count (`-l` subsets included); the escape
`EA_ALLOW_SHORT_DATASET=1` marks the report non-compliant. Documented; not re-reported.

---

## 2. Code mapping, path by path

### 2.1 The gates (`non_iid_main.cpp`)

| line | code | meaning |
|---|---|---|
| 121-122, 163-174 | `initial_entropy = true; all_bits = true;` `-i`/`-c`, `-a`/`-t` | defaults are `-i -a` |
| 329-342 | `if (data.alph_size <= 1) { ... exit(-1); }` | single-symbol data refused (fail-closed) |
| 344 | `if (!all_bits && (data.blen > MIN_SIZE)) data.blen = MIN_SIZE;` | `-t`: keep the FIRST 1,000,000 bits (`MIN_SIZE` = 1000000, `utils.h:42`). `data.len` is untouched, so `H_original` always uses every sample. Matches §3.1.3's permissive "may be ignored" and keeps the first bits as the spec says. |
| 353-354 | `H_original = data.word_size; H_bitstring = 1.0;` | the caps: `H_original <= n`, `H_bitstring <= 1`. These are the only clamps; they also mean an estimator that returns MORE than the bound (LRS can: tracker "9.23 > 8") is harmless. |
| 364, 386, 417, 437, 467, 495, 523, 551, 579, 607 | `if ((data.alph_size > 2) \|\| !initial_entropy)` | bitstring estimators run for non-binary data under `-i`, and ALWAYS under `-c` |
| 371, 400/424/448 (`&& alph_size == 2`), 478, 505, 534, 562, 590, 618 | `if (initial_entropy)` | literal estimators run only under `-i`; Collision/Markov/Compression literal only when the (translated) alphabet is binary — §6.2's last sentence |

"Binary" is `data.alph_size == 2`, computed in `utils.h:read_file_subset` over the
TRANSLATED alphabet (lines 693-705 build the map-down table, 730-732 apply it). A
two-valued 8-bit file is therefore assessed on the binary branch; that is F01,
WITHDRAWN 2026-10-02 with upstream's reading of §4.4.2/§5 (NOTICE lines 59-70). Not
re-reported. Its effect is conservative (`H_original <= 1` bit per symbol; the
`n x H_bitstring` term, which would be computed on the UNTRANSLATED bits
(`utils.h:706-726`, "create bsymbols (bitstring) using the non-mapped data"), is not
needed to bound it).

### 2.2 The folds

Every estimator result enters the running minimum through

```
H_bitstring = min(ret_min_entropy, H_bitstring);     // lines 368, 394, 421, 442, 472, 499, 528, 556, 584, 612
H_original  = min(ret_min_entropy, H_original);      // lines 375, 405, 428, 453, 483, 509, 539, 567, 595, 623
```

`min` is `std::min<double>`, which the standard defines as `(b < a) ? b : a`. The
argument order is (new value, running minimum). Consequences, which are the whole of
the NaN story:

| `ret` | `min(ret, H)` | effect on the running minimum |
|---|---|---|
| finite, `>= 0` | the smaller | correct |
| `+inf` | `H` (since `H < inf`) | no effect: correct, inf is "no information" |
| `-inf` | `-inf` | the figure becomes `-inf`; fail-closed garbage, not an overstatement |
| negative finite | `ret` | understates; **but every site except MCV and Markov is behind `if (ret >= 0)`** which treats negatives as "declined" (`-1.0` is the decline sentinel of Collision, Compression, SAalgs, MultiMCW, Lag, MultiMMC, LZ78Y) |
| `NaN` | **`ret` = NaN** because `H < NaN` is false | the accumulated minimum is REPLACED by NaN |
| next finite `ret2` after a NaN | **`ret2`** because `NaN < ret2` is false | the NaN is REPLACED by the next value; everything folded before the NaN is lost |

Guarded sites (`if (ret_min_entropy >= 0)` / `>= 0.0`): Collision (391, 402),
Compression (439, 450), t-Tuple (469, 480), LRS (496, 506), MultiMCW (525, 536), Lag
(553, 564), MultiMMC (581, 592), LZ78Y (609, 620). A NaN at any of these is dropped —
`NaN >= 0` is false — and the case is marked `*_not_run = true`. That is a MISLABEL
(the estimator ran and produced NaN) but it is the conservative choice for the
minimum: nothing wrong enters it.

Unguarded sites: **MCV** (368, 375) and **Markov** (421, 428). Whether they can yield
NaN at a compliant size:

- `most_common.h:24-31`: `pmax = mode/(double)len`; `ubound = min(1.0, pmax + ZALPHA*sqrt(pmax*(1.0-pmax)/(len-1.0)))`; `entEst = -log2(ubound)`. With `len >= 2` (asserted line 14) the radicand is `>= 0`; `pmax in (0,1]`; `ubound in (0,1]`; `entEst in [0, log2(k)]`. The only NaN is `0/0` at `len == 1`, excluded by the assert and by intake; `min(1.0, NaN)` would return `1.0` anyway (the OC-58 argument order). `pmax == 1` (`entEst = -0.0`) needs a one-symbol alphabet, refused at line 329. **No NaN producer.**
- `markov_test.h:31-105`: every `-log2(P_x)` is behind a `P_xy > 0.0` test that implies the corresponding `P_x > 0` (comments lines 66-67; checked: `C_00 > 0 => C_0 >= 1 => P_0 >= 1/len`; `C_10 > 0 => C_1 > 0 => C_0(after increment) <= len-1 => P_1 = 1 - P_0 >= 1/len`, representable for any `len < 2^52`). `H_min` starts at 128 and only decreases; `entEst = fmin(H_min/128.0, 1.0)` — `fmin` is itself NaN-safe. Codomain `[0, 1]`. **No NaN producer.**

Every other estimator's codomain (checked at its return statement):
`collision_test.h:80-94` `-log2(p)` or `1.0`, or `-1.0` when `v < 2` (line 49);
`compression_test.h:247-273` `-log2(p)/b` with `p > 1/alph_size`, or `1.0`, or `-1.0`
when `num_blocks < d + 2` (line 130); `lrs_test.h:252-272, 342-346` `-log2l(pu)` with
`pu` clamped to `<= 1`, or `-1.0`; `utils.h:1200-1250` `predictionEstimate` returns
`-log2(curMax)` with `curMax in [1/k, 1]` (`fmax`, NaN-safe; `min(1.0, ...)`,
NaN-tolerant; `p_global > 0` excludes a NaN `p_global`). So at `>= 10^6` samples no
fold ever sees a NaN. This agrees with tracker F13 (`UNCONFIRMED`: "No NaN producer at
>= 10^6 in any tool") and with the OC-58 comment in `utils.h:1211-1228`. **What OC-58
did NOT do is harden the folds in `main()`**: the comment's own sentence "if one ever
did arrive, min(1.0, NaN) gives p' = 1 ... maximally conservative" is true of the two
helpers and FALSE of lines 368/375/421/428, where `min(NaN, H)` is NaN and the next
fold discards it. The exposure is bounded by the ordering: both unguarded sites are
early (1st and 3rd of ten), so a NaN there loses at most the MCV and Collision minima
and the remaining seven estimators restore a (possibly higher) minimum. It cannot
reach the final fold, because the last estimator (LZ78Y) is guarded.

### 2.3 The final figure

```
632  double h_assessed;
633  h_assessed = data.word_size;
635  if ((data.alph_size > 2) || !initial_entropy) {
636      h_assessed = min(h_assessed, H_bitstring * data.word_size);
637  }
639  if (initial_entropy) {
640      h_assessed = min(h_assessed, H_original);
641  }
```

Path by path (`n` = `data.word_size`, declared or inferred):

| path | bitstring block runs? | literal block runs? | `h_assessed` | spec |
|---|---|---|---|---|
| `-i`, `alph_size > 2`, any `n >= 2` | yes | yes | `min(n, n*H_bitstring, H_original)` = `min(H_original, n*H_bitstring)` since both caps hold | §3.1.3 non-binary, less `H_submitter`. **Measured equal bit-for-bit** (probe 1, probe 4: `hAssessed == min(hOriginal, hBitstring*dataWordSize)` is `True` at `n = 8` and `n = 7`). |
| `-i`, `alph_size == 2`, `n == 1` | no | yes (all ten estimators, binary) | `min(1, H_original)` = `H_original` | §3.1.3 binary. ✓ |
| `-i`, `alph_size == 2`, `n >= 2` (two-valued multi-bit) | no | yes (binary, on translated symbols) | `min(n, H_original)` with `H_original <= 1` | F01 (withdrawn): conservative |
| `-c`, any `alph_size >= 2`, any `n` | yes (on `bsymbols`, i.e. the bits of the untranslated masked symbols) | no | `min(n, H_bitstring * n)` = `n * h'` | §3.1.5.2 deliverable is `h'`; the tool's "Assessed min entropy" is `n x h'` — see 2.5 |
| `-t` on any of the above | `blen` capped at 10^6 bits BEFORE every bitstring estimator | `len` unchanged | same expressions on fewer bits | §3.1.3 "may be ignored"; under `-c` F20 |

Scaling: `H_bitstring * data.word_size` is `double * int` promoted to `double`; since
`H_bitstring <= 1.0` by the line-354 cap, the product is `<= n` and the `min` with
`h_assessed = n` is redundant but correct. `n` is `data.word_size` — §3.1.3's `n` IF
the width came from the command line; if it was inferred (`utils.h:643-656`, highest
set bit over all samples) it is the data's evident width, which is §2.6 below.

NaN at the final fold: `min(h_assessed, NaN)` returns `h_assessed` (`NaN < x` is
false). So a NaN `H_bitstring` would silently DROP the `n x H_bitstring` term (`-i`:
figure becomes `H_original`; `-c`: figure becomes `n`, full entropy); a NaN
`H_original` would drop the `H_original` term. Unreachable with the current estimator
set (2.2), but the fold is not fail-closed by construction: the safe spelling is
`fmin`, or an explicit `isnan` refusal with `errorClass = "internal"`.

### 2.4 Reporting (text)

`verbose` starts at 1 and `-v` increments it (line 97, 176); `-q` forces 0 (250-252).
So `-v` is level 2 and `-vv` (what `cpp/selftest/selftest` and `pin-check.sh` run) is
level 3:

| level | lines | what is printed |
|---|---|---|
| 1-2 (`-v` or none) | 643-652 | `-i`: `H_original: %f`, and if `alph_size > 2` `H_bitstring: %f`, `min(H_original, %d X H_bitstring): %f`. `-c`: `h': %f`. Six decimals, round-to-nearest (F23: can print above the computed value, e.g. 5.4606043587 -> `5.460604`; cannot round UP here but a value ending ...5 could). |
| >= 3 (`-vv`) | 653-664 | `H_bitstring = %.17g`, `H_bitstring Per Symbol = %.17g` (bitstring block), `H_original = %.17g` (`-i`), `Assessed min entropy: %.17g` (always). **No `h'` line.** |
| 0 (`-q`) | — | nothing; JSON only |

The printed `min(H_original, n X H_bitstring)` at level 2 (line 648) recomputes the
expression rather than printing `h_assessed`; equal because of the caps (2.3).

### 2.5 Reporting (JSON) — `non_iid_test_case.h`, `test_case_base.h`, `test_run_base.h`

`tcOverall` (lines 666-679): `hBitstring` (bitstring block only), `hOriginal` (`-i`
only), `dataWordSize = n`, `hAssessed = h_assessed`. Fields are omitted when equal to
the `-1.0` sentinel (`test_case_base.h:52-57`); a NaN is `!= -1` so it WOULD be
written (jsoncpp has no JSON spelling for NaN; what its writer emits for one -- `null` in the versions I know -- was not measured here); a legitimate `-0.0` would be
written as `-0`. `errorLevel = 0` is set at line 680 BEFORE the write; a failed write
returns `-1` (686-689), the fork's fix for the exit-0-with-no-report defect.

**Measured (probe 1, `-c -a -vvv ... lag-rand8-5000.bin 8`)**: text `H_bitstring =
0.68257554483830007`, `H_bitstring Per Symbol = 5.4606043587064006`, `Assessed min
entropy: 5.4606043587064006`; JSON `Overall`: `hBitstring 0.6825755448383001`,
`hAssessed 5.460604358706401`, `dataWordSize 8.0`, no `hOriginal`. Level-2 text
(probe 6, `-c -a -v`): `h': 0.682576` and nothing else. So under `-c` the quantity
labelled exactly like the `-i` per-symbol assessment, in text and in JSON, is
`word_size x h'`, where `word_size` is the FILE'S packing width (declared or
inferred), not §3.1.5.2's `n_out`. The code is unambiguous (line 636); the hazard is
in the consumer: a pipeline that reads `Assessed min entropy` or `hAssessed` from a
`-c` run and treats it as the per-bit `h'` the standard names is wrong by a factor of
`word_size` (8x for byte-packed conditioned output), in the dangerous direction. This
is tracker F23's second sub-claim, `UNCONFIRMED` there and **CONFIRMED here**; it is
inherited from upstream (identical lines at `upstream/master` 491-512). Mitigation
that does not touch numerics: label the `-c` line `Assessed min entropy per
<n>-bit symbol` or emit `hAssessedUnit`, and have every in-repo consumer assert the
run mode.

In this repository the figure's consumers are `cpp/selftest/selftest` ->
`compareresults.pl` (reads `Estimate:|Assessed|^H_original|^H_bitstring` lines from a
`-vv` run; `compareresults.pl:187`) and `pin-check.sh:64` (reads `Assessed min
entropy:` from `-vv`); both run `-i`, so neither is exposed. ShannonPad's reader is
outside this repository and was not examined.

### 2.6 Width inference and the `n` in `n x H_bitstring` — MEASURED, dangerous direction

`utils.h:643-656`: with no width argument, `word_size` becomes the index of the
highest bit set in ANY sample. The bitstring is then built from `word_size` bits per
symbol (`utils.h:723-725`), so a top bit that is constant 0 across the whole capture
is NOT part of the bitstring, whereas with the width declared it is a constant 0 bit
in every eighth position. Same bytes, two different `H_bitstring` and two different
`n`:

| run | `n` | `H_bitstring` | `n x H_bitstring` | `H_original` | Assessed |
|---|---|---|---|---|---|
| probe 4 `-i -a -vvv <f7>` (inferred) | **7** | 0.77087121065528141 | **5.39609847458697** | 6.4858263215592542 | **5.39609847458697** |
| probe 5 `-i -a -vvv <f7> 8` (declared) | **8** | 0.55343895311860258 | **4.4275116249488207** | 6.4858263215592542 | **4.4275116249488207** |

`<f7>` = `corpus/intake-lsb0-shifted-7bit-20000.bin`, sha256
`048d401955cf09c4ea9ee734bf3e3bf7daa527bc58f41ae77121bda1b3278956`, 20,000 samples,
128 distinct values, MSB never set. Inferred / declared = **1.219**. `H_original` is
identical (same translated symbol sequence; the cap differs but does not bind). The
declared-8 run printed `Warning: Symbols appear to be narrower than described.` on
stdout; the JSON of that run carries `bitsPerSymbol 8, bitsPerSymbolInferred false`
but NOT the warning, because `read_file_subset` stores it in `errorMsg` with
`errorLevel` still 0 and `GetBaseJson` (`test_run_base.h:69-72`) emits `errorMessage`
only when `errorLevel != 0` (item 6 in the headline table).

Reading against the spec: §3.1.3's `n` is the sample width ("each having n bits"),
which §3.2.2 makes the submitter's documented width (tracker F02's reading). For an
8-bit source whose capture happens to have a dead MSB, the spec's computation is at
`n = 8` and includes the constant bit; the tool's default omits it and reports a
figure 22 % higher on this file. This is exactly tracker **F02** ("Omitted
bits_per_symbol: width inferred from the data narrows n and changes n x H_bitstring
(up to 2.4x)", dangerous direction "too HIGH vs the declared-width computation"),
`FORK-FIXED` by REPORTING the width (`bitsPerSymbol`, `bitsPerSymbolInferred`,
commit 97571de) with the inference deliberately unchanged on the upstream
respondent's position (#254). It is therefore a DOCUMENTED DIVERGENCE, re-measured,
not a new finding. It matters for the target profile only when a bit line of the
device is stuck for the whole capture — which is precisely a degraded-device
scenario, where the conservative figure is the one wanted. Operational mitigation
that touches no numerics: the sizing pipeline always passes the device's width
explicitly (`8` or `1`) and refuses a report whose `bitsPerSymbolInferred` is true.
A stuck LOW bit (`corpus/intake-lsb0-8bit-20000.bin`) does not change the inferred
width and so does not trigger this.

### 2.7 Integer widths and overflow

`data.len`, `data.blen` are `long` (`utils.h:98-99`); `blen = len * word_size`
(`utils.h:707`). On LP64 (this host, Linux) that is 64-bit and every estimator takes
`long len`/`long int n` (`most_common.h:7`, `markov_test.h:6`, `collision_test.h:17`,
`compression_test.h:93`, `lrs_test.h:587`, predictors) — no narrowing anywhere on the
`ea_non_iid` path for `len <= 2^63/8`. `SAalgs` selects the 32-bit suffix array when
`n < SAINDEX_MAX` (`INT32_MAX`) and the 64-bit one otherwise (`lrs_test.h:588-592`).
On LLP64 (Windows) `long` is 32-bit and `blen` overflows at `len > 2^31/8`; that is
C18 territory, measured and documented (`FORK-DIVERGENCE-AND-TRUST.md` A.1), not
re-reported. `n_choose_2` (`utils.h:1027`, `assert(n <= INT_MAX)`) is called only from
`lrs_test.h:713`, inside the IID §5.2.5 LRS TEST (`len_LRS_test`), never from the
non-IID estimators; its comment "Callers refuse a sample count above INT_MAX
(iid_main.cpp, non_iid_main.cpp)" is true of `iid_main.cpp:393` and FALSE of
`non_iid_main.cpp` (no such refusal exists — I read all 694 lines and grepped). The
sufficiency argument for `ea_non_iid` is instead "never called"; the comment should
say so. LOW, neutral.

The `-l` subset counts (`unsigned long`) and `bits_per_symbol` are parsed by
`parse_unsigned_decimal` (`utils.h:51-67`), rejecting signs, whitespace, prefixes and
suffixes. `1 <= inint <= 8` is enforced at line 271.

### 2.8 Minimum legal sample count

At exactly `len = 1,000,000`: `-i` 8-bit: `blen = 8,000,000`; every bitstring
estimator's decline threshold is far below (Compression needs `num_blocks >= 1002`,
i.e. 6,012 bits; MultiMCW needs 4,096; Lag 3; MultiMMC/LZ78Y tens). `-i` 1-bit:
`len = 1,000,000` binary, same thresholds hold. `-t`: `blen > 1,000,000` is capped at
exactly 1,000,000 bits (a 1-bit `-c` file of exactly 10^6 samples is NOT truncated,
`>` not `>=`). Declines possible at compliant sizes: t-Tuple cannot (`u == 1` needs
the most common symbol under 35 occurrences; at `len >= 10^6, k <= 256` it occurs
`>= 3906` times); LRS can (`v < u`, `lrs_test.h:342-346`) — F05, de Bruijn at exactly
10^6, recorded by `bitstringEstimateNotRun`/`literalEstimateNotRun` and pinned by
`regression-notrun.sh`. The minimum is then over nine estimators, which "can only
raise the minimum" — documented, visible, not an error by upstream's position.

---

## 3. Prior repairs touching this component, and how to try to break each

| repair | what it did | break attempts (analysis) | result |
|---|---|---|---|
| **F04** (c2f1dcd, `RESOLVED-BY-GLOBAL-GUARD`): literal MultiMCW declined for `64 <= L <= 4095`; made unreachable by the 10^6 intake | `multi_mcw_test.h:16-19` still returns `-1.0` below 4,096 | (a) `-l <i>,4000` subset: `dataset_meets_minimum` checks the LOADED count (`utils.h:297`) -> refused. (b) `-t` with `-c` on 1-bit data: `blen` capped at 10^6 `>= 4096` -> runs. (c) `EA_ALLOW_SHORT_DATASET=1`: reachable by design, report says non-compliant. | holds without the escape |
| **F11** (c0ee84a): Compression requires `num_blocks >= d + 2` | `compression_test.h:130` returns `-1.0`; `main` guards at 439/450 | NaN path needs `v = 1` = exactly 1001 blocks = 6,006..6,011 bits; at `blen >= 10^6` impossible. With the escape, 1001 blocks now DECLINE and the fold skips them. | holds |
| **F12** (c217f20): Collision requires `v >= 2`; `main` gained the `>= 0` guard at 391/402 | the one estimator that was folded unconditionally | a NaN would need `v < 2`, i.e. `len <= 5`; refused at intake. The guard also filters NaN (`NaN >= 0` false). | holds |
| **F13 / OC-58** (`most_common.h:26-30`, `utils.h:1211-1228`): argument order `min(1.0, x)` inside two helpers | a NaN inside those helpers yields `p_u = 1`, entropy 0 | the folds at `non_iid_main.cpp` 368/375/421/428/636/640 use the OPPOSITE order semantics (`min(new, running)`) and were not changed; a NaN reaching them is not conservative (2.2, 2.3). No producer exists, so this cannot be reproduced on the shipped estimators; a MUTANT build is the only reproducer (4.5). | hardening gap, latent |
| **F05 / regression-notrun.sh**: `literalEstimateNotRun`/`bitstringEstimateNotRun` flags | visibility of a skipped estimator | the flags are set whenever `ret < 0` OR `ret` is NaN; a NaN would be labelled "not run" (mislabel, conservative). Flags are only set on the branches that execute, so under `-c` `literal*` is never set — correct. | holds; mislabel noted |
| **F02 / #254** (97571de): JSON `bitsPerSymbol`, `bitsPerSymbolInferred` | visibility of the width used | the FIGURE still rises when the width is omitted and the capture under-fills it: +21.9 % measured (2.6). The repair documents, it does not prevent. | documented divergence, dangerous direction |
| **F20**: `-t` under `-c` | `NOT-A-BUG` per #127/#139/#140 | `-t` is opt-in; default `-a`. `blen` cap is the only effect. | documented |
| **F23**: `-c` `hAssessed = n x h'`, text rounding | `UNCONFIRMED` | `hAssessed = word_size x h'` CONFIRMED (2.5); level-2 `%f` rounding confirmed by reading (line 648). | confirmed sub-claims; inherited |
| **#261** declines (SAalgs `v == 0`, Lag `L < 3`, LZ78Y, MultiMMC): asserts turned into `-1.0` returns | no SIGABRT on tiny input | all guarded at the fold; `v == 0` is impossible at 10^6 with `k <= 256` (pigeonhole). | holds |
| **C14 / A05 / F03 / C24 / C08** (`TestRunUtils.h` writer): placeholder claim, aliasing refusal, atomic rename | the report channel, not the arithmetic | success path returns `-1` when the write fails (686-689) so exit 0 implies a report on disk. Not exercised here (another agent's component). | — |
| **#272** (da0265c): `compareresults.pl` compares `H_original`, `H_bitstring`, `Assessed` | the regression that pins THIS component against NIST's refdata | reads a `-vv` run (level 3) by label; would not notice a `-c` labelling change and does not run `-c` at all. `refdata/*.res` lack `H_bitstring Per Symbol` (`compareresults.pl:138-139` says so), so that line is unpinned. | pins `-i` only |

---

## 4. Edge-case inputs that separate a correct from an incorrect aggregation

Each names the construction, the correct expectation from §3.1.3/§3.1.5.2, and what a
WRONG implementation would show. Sizes marked (C) are compliant (10^6) and belong to
the execution phase; sizes marked (S) are short and need the escape.

1. **MSB-dead 8-bit capture, width omitted vs declared** (C). `python3`: seed 7,
   10^6 bytes `r.randrange(128)`. Run `-i -vv f` and `-i -vv f 8`. Correct per spec at
   the submitter's `n = 8`: the declared figure. The inferred run reports HIGHER
   (measured +21.9 % at 20,000; expect the same sign at 10^6). Distinguishes "n is the
   declared width" from "n is the evident width". JSON must show
   `bitsPerSymbolInferred: true` on the first. Documented F02; this is the regression
   shape that would pin its DIRECTION, which nothing pins today.
2. **LSB-dead 8-bit capture** (C): `r.randrange(256) & 0xFE`. Inferred width stays 8;
   both runs identical. Control for (1): shows the effect is the top-bit inference and
   not the constant bit itself.
3. **`-c` on byte-packed conditioned output** (C): any 10^6-byte file with all 256
   values. Correct §3.1.5.2 deliverable: `h'` per bit. The tool's `Assessed min
   entropy` and `hAssessed` must equal `8 x h'` exactly (`hBitstring * dataWordSize`);
   a consumer reading them as `h'` overstates 8x. Measured at 5,000: 5.4606 = 8 x
   0.68258.
4. **`-t` vs `-a`, 8-bit, 10^6 samples** (C). `H_original` lines must be IDENTICAL;
   `H_bitstring` may differ (first 10^6 of 8 x 10^6 bits). A wrong implementation that
   truncated `len` too would change `H_original`. Also `-c -t` vs `-c -a` (F20: either
   direction; record, do not re-report). Under 20,000 samples `-t` is a no-op
   (measured: byte-identical logs, `diff` rc 0), so this needs the execution phase.
5. **NaN/inf/negative/over-bound injection by MUTATION** (S or C; needs an
   out-of-tree build per BUILD-LINES.md, execution phase). Five mutants of
   `markov_test.h:113` `return entEst;` -> `return NAN;`, `return -INFINITY;`,
   `return INFINITY;`, `return -0.5;`, `return 9.0;`, run `-c` and `-i` on a 1-bit
   and an 8-bit file. Correct (fail-closed) behaviour: a NaN is refused or treated as
   "cannot assess". Predicted on the current code (2.2): NaN -> `Markov` prints `nan`,
   the Bitstring MCV and Collision minima are DISCARDED, the figure is the min over
   the remaining seven (HIGHER whenever MCV or Collision was binding); `-inf` ->
   figure `-inf`; `+inf` -> no effect; `-0.5` -> figure `-0.5`; `9.0` -> no effect
   (cap). Baseline (unmutated) must be asserted first (rule 7). The same five mutants
   on a GUARDED site (`lz78y_test.h` return) predict: NaN/-inf/-0.5 -> labelled
   `bitstringEstimateNotRun`, figure unchanged; +inf/9.0 -> no effect. The contrast
   between the two sites IS the finding, if the owner wants the folds hardened.
6. **Two-valued 8-bit data** (C): `bytes(2*x)`/`{0,255}`. Expect the binary branch,
   `H_original <= 1`, no `Bitstring` lines, `hAssessed <= 1`. F01, withdrawn; include
   only as a control that the gate did not move (NOTICE says master gates on
   `alph_size > 2` identically to upstream).
7. **de Bruijn B(100,3), exactly 10^6 samples** (C; generator in
   `audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py`): LRS
   declines, `literalEstimateNotRun` set, `errorLevel 0`, figure = min over nine.
   Pinned by `regression-notrun.sh`. Control that the flag, not silence, records it.
8. **Single-valued and empty files** (S): refused before any fold (`alph_size <= 1`,
   `len == 0`). Fail-closed; JSON `errorLevel -1`.
9. **Exactly 10^6 one-bit samples under `-c -t`** (C): `blen == MIN_SIZE`, the `>`
   test at line 344 must NOT truncate; 10^6 + 1 samples must truncate to 10^6. Boundary
   of the `-t` gate.
10. **Label drift between verbose levels** (S, measured): `-v` prints `h': 0.682576`
    and no `Assessed` line; `-vv` prints `Assessed min entropy: 5.4606...` and no
    `h'` line. A consumer keyed on one label at the wrong level reads nothing or the
    other quantity. `pin-check.sh` and `compareresults.pl` key on `-vv` labels.

---

## 5. Probe record (this analysis)

Script: `logs/analysis-aggregation-probe.sh`; exit statuses:
`logs/analysis-aggregation-probe-exit.log` (all `rc=0`; `diff rc=0`); hashes:
`logs/analysis-aggregation-probe-sha256.log`. Inputs: `corpus/lag-rand8-5000.bin`
(sha256 `de1af1f8...2c45`, 5,000 samples, 256 distinct, declared 8) and
`corpus/intake-lsb0-shifted-7bit-20000.bin` (sha256 `048d4019...8956`, 20,000 samples,
128 distinct, MSB never set). Both runs non-compliant by size (escape set).

| log | command (after `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 cpp/ea_non_iid`) | observed |
|---|---|---|
| `analysis-aggregation-probe1-i-vvv.log`, `probe1-i.json` | `-i -a -vvv -o ... lag-rand8-5000.bin 8` | `H_bitstring = 0.68257554483830007`, `Per Symbol = 5.4606043587064006`, `H_original = 6.2956593158922249`, `Assessed = 5.4606043587064006`; JSON `hAssessed == min(hOriginal, hBitstring*8)` True |
| `probe1-c-vvv.log`, `probe1-c.json` | `-c -a -vvv -o ... lag-rand8-5000.bin 8` | same `H_bitstring`, `Assessed min entropy: 5.4606043587064006` (= 8 x h'), no `H_original`, no `h'` line; JSON `hAssessed 5.460604358706401`, `hBitstring 0.6825755448383001`, no `hOriginal` |
| `probe6-i-v.log`, `probe6-c-v.log` | `-i -a -v`, `-c -a -v` (level 2) | `H_original: 6.295659`, `H_bitstring: 0.682576`, `min(H_original, 8 X H_bitstring): 5.460604`; `-c`: `h': 0.682576` only |
| `probe3-i-t-vvv.log`, `probe3-t-vs-a.diff` | `-i -t -vvv lag-rand8-5000.bin 8` | byte-identical to `-a` (40,000 bits `<= 10^6`), `diff` rc 0 |
| `probe4-i-inferred-vvv.log`, `probe4-inferred.json` | `-i -a -vvv -o ... intake-lsb0-shifted-7bit-20000.bin` | `Loaded 20000 samples of 128 distinct 7-bit-wide symbols`; `Assessed 5.39609847458697`; JSON `bitsPerSymbol 7, bitsPerSymbolInferred true` |
| `probe5-i-declared8-vvv.log`, `probe5-declared8.json` | `-i -a -vvv -o ... intake-lsb0-shifted-7bit-20000.bin 8` | `Warning: Symbols appear to be narrower than described.`; `8-bit-wide`; `H_bitstring = 0.55343895311860258`; `Assessed 4.4275116249488207`; same `H_original` |
| `probe4-c-inferred-vvv.log`, `probe4-c-inferred.json` | `-c -a -vvv -o ... intake-lsb0-shifted-7bit-20000.bin` | `Assessed 5.39609847458697` = 7 x 0.77087121065528141; JSON `hAssessed == hBitstring*7` True |

## 6. What this analysis cannot see

- Truncation (`-t`) was not exercised: it needs `blen > 10^6`, i.e. > 125,000 8-bit
  samples, above the analysis cap.
- The NaN folds were reasoned about from the estimators' codomains and the C++
  standard's definition of `std::min`; no NaN was produced or injected. The mutant
  build in 4.5 is the only way to turn the reasoning into a measurement.
- Sizes: all probes are 5,000-20,000 samples. Every statement about `>= 10^6` is from
  reading, not running.
- Platform: Darwin arm64 / Apple clang 21 only. The LLP64 remarks are from the
  documented C18 record, not re-measured.
- ShannonPad's reader of the figure is outside this repository; whether it runs `-c`,
  which label it parses and at which verbose level, is unknown here.
