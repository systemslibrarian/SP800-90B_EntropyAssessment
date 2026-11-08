# Analysis — Most Common Value estimate (§6.3.1) and the literal/bitstring pair

Audit: 2026-11-07 aggressive audit, analysis phase. Branch `audit/2026-11-07`,
source commit `a2c3c81314a76947bf3924a72854a867c5d12fa7`. Nothing was built; no
heavy job was run. Four tiny probes (20 to 20,000 samples) ran with
`EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`; every one is marked
non-compliant by the tool and their logs are under `logs/analysis-mcv-probe*.log`.

Binaries measured (instrument rule 4):

| binary | sha256 |
|---|---|
| `cpp/ea_non_iid` | `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` |
| `cpp/ea_iid` | `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349` |

Headline: **the arithmetic of `most_common()` is spec-exact** (the standard's
own worked example reproduces to the printed digits, and the one constant
difference is the documented `D-1`). Everything found is in how the result is
*reported* or *paired*, not in how it is computed. Nothing here overstates
min-entropy in the target profile (`ea_non_iid -i`, 1 or 8 bits, ≥ 10^6 samples).
One MEDIUM reporting hazard under `-c` was **measured** (previously tracker
`F23`, UNCONFIRMED). Two platform/size suspicions are stated as suspicions.

---

## 1. The standard, transcribed

### 1.1 §6.3.1 The Most Common Value Estimate — SP 800-90B §6.3.1 (PDF p. 49)

> "This method first finds the proportion p̂ of the most common value in the
> input dataset, and then constructs a confidence interval for this proportion.
> The upper bound of the confidence interval is used to estimate the min-entropy
> per sample of the source.
> Given the input S = (s1, …, sL), where si ϵ A = {x1, …, xk},
> 1. Find the proportion of the most common value p̂ in the dataset, i.e.,
>    p̂ = max_i #{x_i in S} / L.
> 2. Calculate an upper bound on the probability of the most common value p_u as
>    p_u = min( 1, p̂ + 2.576 · sqrt( p̂(1 − p̂) / (L − 1) ) ),
>    where 2.576 corresponds to the Z(1−0.005) value.
> 3. The estimated min-entropy is –log2(p_u)."

Properties the implementation must honour:

| item | value |
|---|---|
| statistic | maximum symbol count over the alphabet, divided by L |
| bound direction | **upper** bound on p (adds z·sd); larger p_u ⇒ smaller entropy |
| constant | 2.576 as printed; defined as the 0.995 normal quantile |
| variance denominator | **L − 1** (not L) |
| clamp | `min(1, …)` — p_u may not exceed 1 |
| rounding / tolerance / iteration / termination | none; closed form |
| domain | p̂ ∈ [1/k, 1]; p_u ∈ (0, 1]; entropy ∈ [0, log2 k] |

Worked example — SP 800-90B §6.3.1 (PDF p. 50):

> "If the dataset is S = (0, 1, 1, 2, 0, 1, 2, 2, 0, 1, 0, 1, 1, 0, 2, 2, 1, 0, 2, 1),
> with L = 20, the most common value is 1, with p̂ = 0.4.
> p_u = 0.4 + 2.576√0.012 = 0.6895. The min-entropy estimate is −log2(0.6822) = 0.5363."

The text is internally inconsistent: −log2(0.6895) = 0.5364 and −log2(0.6822)
= 0.5517, so "0.6822" is a misprint and 0.5363 is the figure for p_u = 0.6895.
(The prior campaign recorded this erratum as `OC-32`.) Also √0.012 is itself a
rounding of √(0.4·0.6/19) = √0.012632 = 0.11239, confirming the L − 1
denominator.

### 1.2 Where MCV is used — §6.1, §6.2 (PDF p. 48–49)

> §6.1: "For sources with IID outputs, the min-entropy estimation is determined
> using the most common value estimate described in Section 6.3.1."

> §6.2 (p. 49): "For non-IID data, the following estimators shall be calculated
> … and the minimum of all the estimates is taken as the entropy assessment …
> The Collision, Markov and Compression estimates are only applied to binary inputs."

### 1.3 The literal/bitstring pair — §3.1.3 (PDF p. 20)

> "After determining the entropy estimation track, a min-entropy estimate per
> sample, denoted as Horiginal, for the sequential dataset is calculated using the
> methods described in Section 6.1 (for the IID track) or Section 6.2 (for the
> non-IID track). If the alphabet size is greater than 256, it shall be reduced to
> at most 256 symbols (see Section 6.4).
> If the sequential dataset is not binary, an additional entropy estimation (per
> bit), denoted Hbitstring, is estimated. First, the sequential dataset that
> contains L samples (each having n bits) is considered as a bitstring of size nL.
> The bits after the first 1 000 000 bits may be ignored. Then, the estimation is
> done based on the entropy estimation track, as specified in the previous
> paragraph, and Hbitstring is calculated. Then, the entropy per sample is
> estimated to be n×Hbitstring.
> The initial entropy estimate of the noise source is calculated as
> HI = min (Horiginal, n×Hbitstring, Hsubmitter) for non-binary sources and as
> HI = min (Horiginal, Hsubmitter) for binary sources."

### 1.4 Intake — §3.1.1 item 1 (PDF p. 19)

> "A sequential dataset of at least 1 000 000 sample values obtained directly
> from the noise source (i.e., raw data) shall be collected for validation."

### 1.5 §6.4 Reducing the Symbol Space (PDF p. 66–67)

§6.4 describes mapping n-bit samples to m-bit samples by a submitter-supplied
bit ranking ("taking the m-bits of greatest rank in order"). **The tool does not
implement §6.4**: it accepts 1–8 bits per symbol and never reduces. What the
tool calls "translation" (`utils.h:541-544`) is a relabelling of the *observed*
alphabet onto {0..k−1}; it changes no count and is invisible to MCV. The
bitstring is the §3.1.3 "considered as a bitstring of size nL" step, not a §6.4
reduction.

### 1.6 Conditioned output — §3.1.5.2 (PDF p. 25)

> "… the entropy of the conditioned sequential dataset …, which shall be
> computed using the methods described in either Section 6.1 (for IID data) or
> Section 6.2 (for non-IID data). Let the obtained entropy estimate **per bit**
> be h'. The output of the conditioning component (nout) shall be treated as a
> binary string, for purposes of the entropy estimation. … hout = min(
> Output_Entropy(nin, nout, nw, hin), 0.999·nout, h′ × nout )."

The only unit §3.1.5.2 defines for the conditioned dataset is **per bit**.

---

## 2. Mapping to the C++

### 2.1 `cpp/shared/most_common.h` — `most_common()` lines 7–47

```c
 7  double most_common(uint8_t* data, const long len, const int alph_size, const int verbose, const char *label, TestCaseBase &tc){
 9      long counts[alph_size];
14      assert(len > 1);
16      for(i = 0; i < alph_size; i++) counts[i] = 0;
17      for (i = 0; i < len; i++) counts[data[i]]++;
19      mode = 0;
20      for(i = 0; i < alph_size; i++){
21          if(counts[i] > mode) mode = counts[i];
22      }
24      pmax = mode/(double)len;
30      ubound = min(1.0,pmax + ZALPHA*sqrt(pmax*(1.0-pmax)/(len-1.0)));
31      entEst = -log2(ubound);
40      string literal = "Literal";
41      tc.mcv_estimate_mode = mode;
42      tc.mcv_estimate_p_hat = pmax;
43      tc.mcv_estimate_p_u = ubound;
44      tc.literal_mcv_estimate = literal.compare(label);
46      return entEst;
```

| spec step | code | verdict |
|---|---|---|
| 1. p̂ = max count / L | `:17` counts, `:19-22` max, `:24` `mode/(double)len` | exact. Ties: `>` keeps the first maximum; the *value* of the mode is irrelevant, only its count is used. |
| 2. p_u = min(1, p̂ + z·√(p̂(1−p̂)/(L−1))) | `:30` | structurally exact: upper bound (adds), clamp at 1, **L − 1** denominator (`len-1.0`). Constant is `ZALPHA` (`utils.h:75` = `2.5758293035489008`), not the printed 2.576 → **documented `D-1`**, see §3.1 below. |
| 3. −log2(p_u) | `:31` | exact. |

Numerics, checked one by one:

- **Log of zero**: impossible. p̂ ≥ 1/k > 0 so `ubound ≥ pmax > 0`.
- **NaN**: `pmax*(1-pmax) ≥ 0`; `len-1.0 > 0` because `assert(len > 1)` at `:14` is
  *live* (`cpp/Makefile:51` has no `-DNDEBUG`). The only NaN route is 0/0 at
  `len == 1`, which the assert turns into an abort. Even if it arrived,
  `min(1.0, NaN)` returns `1.0` (`std::min(a,b)` is `b<a ? b : a`; `NaN < 1.0`
  is false), giving entropy 0 — fail-closed. Argument order is load-bearing and
  the comment at `:26-29` says so (`F13`/`OC-58`).
- **Clamp produces −0.0**: `-log2(1.0)` is IEEE `-0.0`. Measured (probe 2):
  `Literal Most Common Value Estimate: p_u = 1`, `min entropy = -0`, JSON
  `"hOriginal" : -0.0`. Cosmetic; numerically zero; conservative.
- **Division by small counts**: only `/len` and `/(len-1.0)`; `len ≥ 2`.
- **int vs long**: `len` is `long` throughout; `counts[]` and `mode` are `long`;
  on LP64 (this host) exact to 2^63 and `mode/(double)len` exact to 2^53. On
  LLP64 see suspicion S-6 (the overflow is in the *caller's* `blen`, not here).
- **Out-of-bounds index** `counts[data[i]]`: `counts` is a stack VLA of
  `alph_size` entries. Safe iff every `data[i] < alph_size`. Literal path:
  `read_file`/`read_file_subset` translate the alphabet onto {0..k−1} whenever a
  gap exists (`utils.h:541-544`, `:729-732`), and when no gap exists every
  symbol is already ≤ `maxsymbol = alph_size−1`. Bitstring path: `bsymbols` are
  built as `(sym >> …) & 0x1` (`utils.h:536`, `:724`), so ∈ {0,1}, with
  `alph_size = 2`. `ea_restart` passes `rdata = data.symbols` (`restart_main.cpp:714`).
  No unmapped caller exists. **An ASan run on a sparse alphabet (e.g. {0x00,
  0x07, 0xFF}) is the cheap executable check — see edge case E-11.**
- `:44 tc.literal_mcv_estimate = literal.compare(label)`: `std::string::compare`
  returns **0 on equality**, so this flag is `false` for "Literal" and `true` for
  "Bitstring" — inverted. It is **dead**: `test_case_base.h:66-67` has the only
  consumer commented out. LOW, neutral.

Verbose labels (`:32-38`) are exactly what `reference/cpp-verbose-labels-*.txt`
carry, so the differential harness can match on them.

### 2.2 Invocation in `cpp/non_iid_main.cpp`

```c
353  H_original = data.word_size;
354  H_bitstring = 1.0;
362  NonIidTestCase tc631;
364  if (((data.alph_size > 2) || !initial_entropy)) {
365      ret_min_entropy = most_common(data.bsymbols, data.blen, 2, verbose, "Bitstring", tc631);
367      tc631.h_bitstring = ret_min_entropy;
368      H_bitstring = min(ret_min_entropy, H_bitstring);
369  }
371  if (initial_entropy) {
372      ret_min_entropy = most_common(data.symbols, data.len, data.alph_size, verbose, "Literal", tc631);
374      tc631.h_original = ret_min_entropy;
375      H_original = min(ret_min_entropy, H_original);
376  }
...
632  double h_assessed;
633  h_assessed = data.word_size;
635  if ((data.alph_size > 2) || !initial_entropy) {
636      h_assessed = min(h_assessed, H_bitstring * data.word_size);
637  }
639  if (initial_entropy) {
640      h_assessed = min(h_assessed, H_original);
641  }
```

- **§3.1.3 composition**: `h_assessed = min(word_size, n×H_bitstring, H_original)`.
  The extra `word_size` cap is harmless (MCV ≤ log2 k ≤ word_size, so
  `H_original` is already below it after `:375`). `H_submitter` is external to
  the tool. **Conformant.**
- **"binary" gate** is `data.alph_size > 2` on the *translated* alphabet, not
  `word_size > 1`. A two-valued 8-bit file is treated as binary and gets no
  bitstring term. **Documented: `F01` WITHDRAWN** (NOTICE lines 340–358; tracker
  row F01), citing §4.4.2 "produces only two distinct values" and §5 "binary,
  i.e., k = 2". Not re-reported. The tracker's own residual stands: the figure
  is discontinuous at the alphabet boundary (a single rare third value switches
  the bitstring term on) — in the **conservative** direction only (E-7).
- **`-t`** (`:344`): `if (!all_bits && (data.blen > MIN_SIZE)) data.blen = MIN_SIZE;`
  — §3.1.3 "The bits after the first 1 000 000 bits may be ignored." Conformant;
  `-a` (all bits) is the default and is also allowed. (`F20` NOT-A-BUG covers `-t`
  under `-c`.)
- **Initialisers**: `H_original = word_size`, `H_bitstring = 1.0` can never
  survive to the report because MCV always runs on each active path and is folded
  first (`:368`, `:375`). In `ea_non_iid` the JSON only records values that were
  computed (`tc631.h_*` set inside the branches).
- **Fold order and NaN (context for `F13`)**: `H = min(ret, H)` with `ret = NaN`
  yields `NaN`; the *next* estimator's `min(ret2, NaN)` yields `ret2` — the NaN
  erases every earlier minimum and is then replaced. A NaN in the **last**
  estimator (LZ78Y) would make `h_assessed = min(word_size, NaN×n) = word_size`.
  MCV cannot produce a NaN (§2.1), so MCV is not the slot that matters; the
  dangerous slot is LZ78Y. `F13` is closed as unreachable (`OC-58`), which this
  analysis does not contradict; it is listed under "repairs to break".

### 2.3 Bitstring construction and width — `cpp/shared/utils.h`

```c
457  if(dp->word_size == 0) {                         // infer width = highest set bit
462      for(i = 0; i < dp->len; i++) datamask |= dp->symbols[i];
466      for(i=8; (i>0) && ((datamask & curbit) == 0); i--) curbit >>= 1;
470      dp->word_size = i;
...
520  dp->blen = dp->len * dp->word_size;
521  if(dp->word_size == 1) dp->bsymbols = dp->symbols;
523  else { dp->bsymbols = (uint8_t*)malloc(dp->blen);
534      for(i = 0; i < dp->len; i++)
535          for(j = 0; j < dp->word_size; j++)
536              dp->bsymbols[i*dp->word_size+j] = (dp->symbols[i] >> (dp->word_size-1-j)) & 0x1;
```
(`read_file_subset`; `read_file` is the same at `:643-727`.)

- Bitstring = MSB-first bits of the masked, **untranslated** symbol (built
  before the translation loop at `:541-544`), n = `word_size`. §3.1.3 fixes no
  bit order (`F21` NOT-A-BUG), and **MCV on the bitstring is bit-order-invariant
  anyway**: it depends only on the total count of 1-bits and nL. So for MCV the
  bitstring figure is a function of (popcount, n, L) alone — a useful invariant
  for the differential harness.
- n is the **inferred** width unless given on the command line. With a declared
  width wider than the data the tool keeps the declared width (warning at
  `:484`), with leading zero bits in the bitstring. Declared vs inferred changes
  n×H_bitstring (E-5, E-6) but never raises the figure above what the data has
  (a constant bit contributes zero entropy and the literal term is unaffected).
  Documented default ("By default this value is inferred from the data",
  usage line 31) and reported (`bitsPerSymbolInferred`, `regression-width.sh`).

### 2.4 The other callers

- `cpp/iid_main.cpp:436-463`: identical composition. `int sample_size = data.len;`
  (`:352`) narrows `long→int` but is used for the literal MCV only under `-i`,
  where `:393 if (testdata.len > INT_MAX)` has already refused larger inputs.
  Safe. The repair comment at `:448-470` (h_assessed computed outside the verbose
  branch; initialisers not reported) is confirmed by probe 2's JSON
  (`hOriginal` present, no `hBitstring` for binary `-i`).
- `cpp/restart_main.cpp:858-868`: rows and columns each get MCV with
  `data.len` (forced to exactly `MIN_SIZE` at `:694`) and `data.alph_size`.
  Because MCV is order-independent, the row and column MCV figures are
  identical by construction; the standard asks for both and both are computed.
- `cpp/conditioning_main.cpp:376,384`: bitstring MCV; this fork does not build
  `ea_conditioning` (tracker `N-03` records the `assert(len > 1)` path there).

### 2.5 Measured against the standard's worked example (probe 1)

`logs/analysis-mcv-probe1-noniid-spec-example.log` (exit 0) and
`…-probe1-iid-spec-example.log` (exit 134 — see §7), input
`088df27d16a3b5cc53a47049f924a13ac135c668ecc9805aec6f9d683acf1da1`
(the 20 bytes of §6.3.1's example; width inferred 2, alphabet 3):

```
Literal Most Common Value Estimate: Mode count = 8
Literal Most Common Value Estimate: p-hat = 0.40000000000000002
Literal Most Common Value Estimate: p_u = 0.68949822145123085
Literal Most Common Value Estimate: min entropy = 0.53638126455028012
Bitstring Most Common Value Estimate: Mode count = 26
Bitstring Most Common Value Estimate: p-hat = 0.65000000000000002
Bitstring Most Common Value Estimate: p_u = 0.84673221267997034
Bitstring Most Common Value Estimate: min entropy = 0.24002231957233899
```

Spec: p̂ = 0.4, p_u = 0.6895, H = 0.5363 — **matches** (0.68950 / 0.53638; the
4th-decimal difference from "0.6895" is the 2.576-vs-ZALPHA rounding, D-1).
Bitstring by hand: 0→00 ×6, 1→01 ×8, 2→10 ×6 ⇒ 26 zeros of 40, p̂ = 0.65,
p_u = 0.65 + 2.57583·√(0.65·0.35/39) = 0.84673, H = 0.24002 — **matches**.
`ea_iid` printed the identical eight lines before aborting elsewhere.

---

## 3. Prior repairs and decisions touching this component, and how to break them

| id | what | how I would try to break it |
|---|---|---|
| **D-1 / F07** (`FORK-DIVERGENCE` §D; tracker F07 NOT-A-BUG) | `ZALPHA 2.5758293035489008` instead of 2.576. Direction: permissive. | Recomputed here (`logs/analysis-mcv-zalpha-rounding.log`): Δp_u = (2.576−ZALPHA)·sd; ΔH ≈ 2.46e-7 bit (p̂=0.5, L=10^6), 3.78e-6 bit (p̂=1/256, L=10^6), 8.7e-8 (p̂=0.5, L=8·10^6). Consistent with the record's "≤ 5e-6 bit/bit". **One refinement to D-1's wording**: the literal is **not** the correctly rounded binary64 of Φ⁻¹(0.995). Exact value 2.575829303548900384…; the literal is `0x1.49b4c64d69161p+1` = 2.5758293035489008282…, and the next lower double `0x1.49b4c64d69160p+1` = 2.5758293035489003842… is within 4e-22 of the truth, so `ZALPHA` is **one ulp high**. Effect: p_u larger by ≤ 4.4e-16·sd ⇒ entropy lower by ≲ 1e-19 bit. Immaterial and conservative; stated for the record and because a Python reference using `NormalDist().inv_cdf(0.995)` gets `0x1.49b4c64d6915fp+1` (one ulp *low*), so bit-exact comparison of p_u against the C++ will differ at the 1e-19 level. Mutation to 2.576 would be caught by `selftest` refdata (relative ε = 1e-10, `compareresults.pl:22`) but **not** by `regression-constants.sh`, which pins the floor module's constants and does not read `ZALPHA` at all. |
| **F01** (WITHDRAWN 2026-10-02; NOTICE 340–358; upstream #253/PR #256) | two-symbol alphabet is binary regardless of declared width; no n×H_bitstring term. | Confirm the gate is on the translated alphabet (`non_iid_main.cpp:364`) and that a declared `8` changes nothing for `-i` (E-7a). Try to make the decision bite in the permissive direction: it cannot — for k = 2, H_original ≤ 1 bit already bounds the source's true min-entropy, and the bitstring term can only lower the figure further. Residual is the discontinuity (E-7b), conservative. |
| **F13 / OC-58** (NaN into `std::min`; closed as unreachable) | argument order `min(1.0, x)` at `most_common.h:30` and `utils.h:1229`. | MCV cannot emit NaN (§2.1). The fold order makes the **last** estimator the one whose NaN would set `h_assessed = word_size` (§2.2). Attack the predictors' NaN surface at N ∈ {0, 1} via `-l` subsets rather than MCV; MIN_SIZE blocks it on every supported path. The `f13_nan_reachability.c` probe demonstrates the detector fires at N = 1, so its silence at ≥ 10^6 is a measurement. |
| **F15** (asserts on tiny inputs; FORK-FIXED for three sites) | `most_common.h:14 assert(len > 1)` is **still an assert**. | Reach it: a 1-sample input needs `EA_ALLOW_SHORT_DATASET=1` and then `alph_size == 1` is refused at `non_iid_main.cpp:329` before MCV; `-l 0,1` likewise. `ea_restart` forces `len == MIN_SIZE`. Not reachable from any built CLI. (Reachable in `ea_conditioning`, not built — `N-03`.) |
| **F23** (tracker UNCONFIRMED) | (a) JSON keeps literal MCV intermediates only; (b) `-c` `hAssessed = n×h′`. | **Both measured** (probes 3 and 4) — see S-1 and S-2. |
| `iid_main.cpp:448-477` h_assessed/initialiser repair (upstream PR #251 analogue) | figure computed outside the verbose branch; initialisers not reported. | Probe 2 at `-vv`: `hOriginal` present, no `hBitstring`. Re-run at `-q` (verbose 0) and compare: the repair's whole point was verbosity independence. Not yet done at `-q` for `ea_iid`. |
| MIN_SIZE intake (`utils.h:294-317`) | refuses < 10^6 loaded samples; `-l` counted on loaded samples. | Boundary pair: `-l 0,1000000` on a 1,000,001-byte file (accept) vs `-l 1,1000000` (loads 1 ⇒ refuse). Not an MCV defect candidate; it is the guard MCV's `assert` relies on. |
| **C18** repair's stated non-coverage ("that no other 32-bit `long` arithmetic remains" — `FORK-DIVERGENCE` A.1) | | `utils.h:520`/`:707 dp->blen = dp->len * dp->word_size` is exactly such a site — S-6. |
| `regression-272.sh` mutants | drop `n×H_bitstring` / drop `H_original` in the final combination | They exercise the pairing at `:636`/`:640` and are caught by `selftest` on `truerand_8bit` / `biased-random-bits`. A third mutant worth adding: `len-1.0 → len` at `most_common.h:30` (overstates; relative Δp_u ≈ 1.3e-9 at L = 10^6, p̂ = 0.5 — above the 1e-10 ε by only ~13×, so it is a sharp test of the guard's margin). |

**Regression coverage gap**: there is no MCV-specific regression script; the only
guard on `most_common.h` and `ZALPHA` is the `selftest` refdata comparison
(bit-identity to 1e-10 relative on NIST's `bin/` samples), run in CI by
`run-all-checks.sh` (`x86-64-platform-facts.yml:393-395`).

---

## 4. Edge-case inputs that distinguish a correct from an incorrect MCV / pairing

Expected values use ZALPHA = 2.5758293035489008; a reference using 2.576 differs
at the 1e-7 level and must be reconciled via D-1.

| id | construction | why / what a wrong implementation shows |
|---|---|---|
| E-1 | `mcv_spec_example_L20.bin` — the 20 bytes of §6.3.1's example (width inferred 2). | Pins p̂ = 0.4, p_u = 0.68949822145123085, H = 0.53638126455028012; bitstring 26/40 → 0.24002231957233899. H_I from MCV alone = min(0.5364, 2×0.2400) = 0.4800. Using L instead of L−1 gives p_u = 0.68822; dropping the clamp/bound gives 1.3219. **Measured: matches.** |
| E-2 | 20,000 bytes: 19,999 × `0x00`, one `0x01` (width 1). | p_u clamps to exactly 1 ⇒ H = −0.0. An implementation without the `min(1, …)` clamp returns −log2(1.00008) = **negative** entropy, which `min()` would then pick as the figure. **Measured: `p_u = 1`, `min entropy = -0`, JSON `-0.0`.** |
| E-3 | exact tie: 500,000 × 0 and 500,000 × 1 (L = 10^6, width 1) — generate with a fixed seed and shuffle, or alternate. | p̂ = 0.5 exactly; p_u = 0.5 + 2.5758293·√(0.25/999,999) = 0.50128791…; H = 0.996288…. A `>=`/`>` slip or a mode chosen by *value* rather than count is invisible here, which is the point: MCV must be label-blind. Pair with E-4. |
| E-4 | 600,000 × `0x05` and 400,000 × `0x00` (width 3 inferred, alphabet 2 → translated {1,0}). | p̂ = 0.6 (count-based, the larger count belongs to the *higher* raw value); an implementation that returns the count of the smallest or first symbol reports 0.4 → H = 1.32 bits instead of 0.735: **overstates**. Also exercises translation: k = 2 so no bitstring term (F01). |
| E-5 | 10^6 bytes uniform over {0x00..0x0F}, run once with `… file 8` (declared) and once with width inferred (4). | Literal: k = 16, H_original ≈ 4 − ε either way. Bitstring declared-8: 4 constant 0 bits + 4 fair ⇒ p̂₀ = 0.75, H_bit ≈ 0.4150, n×H_bit ≈ 3.32 **binds**. Inferred-4: p̂₀ = 0.5, n×H_bit ≈ 3.99. A reference that infers n differently from the C++ disagrees by 0.67 bit on identical bytes — the harness must pass `bits_per_symbol` explicitly to both sides. |
| E-6 | 10^6 bytes uniform over {0x00..0x7F} (top bit stuck at 0), declared 8 vs inferred 7. | Declared: p̂₀ = (1 + 7·0.5)/8 = 0.5625 ⇒ H_bit = 0.830, 8×H_bit = 6.64 binds below H_original ≈ 7. Inferred: 7×1.0 ≈ 7.0. True min-entropy is 7 bits/sample, so the inferred width is the *accurate* one and the declared width is conservative; a wrong implementation would be one where n×H_bitstring exceeds the literal figure's cap, i.e. > 7 — impossible when n is the real width. |
| E-7a | 10^6 bytes from {0x00, 0x01} fair, declared `8`. | F01 territory (documented, not a bug): tool gives H_original ≈ 0.996 and **no** bitstring term; a literal reading of §3.1.3 would give 8 × H_bit with p̂₀ = 15/16 ⇒ 0.745. Record as DOCUMENTED DIVERGENCE if the reference implements the literal reading. |
| E-7b | same, plus a single `0xFF` (alphabet 3). | Gate flips: bitstring runs, p̂₀ ≈ 15/16 ⇒ n×H_bit ≈ 0.745 < H_original ≈ 0.996 ⇒ figure **drops** 25 % on one changed byte. Conservative discontinuity; a reference must reproduce the same gate to agree. |
| E-8 | 10^6 bytes, 8-bit, biased: P(0x00) = 0.30, rest uniform. `-a` vs `-t`. | Literal p̂ = 0.30. Bitstring under `-t` uses the first 10^6 **bits** = first 125,000 symbols; the confidence term is √8 larger than under `-a`, so H_bit(-t) < H_bit(-a) by ≈ 2.58·(√(p(1−p)/125,000) − √(p(1−p)/8·10^6))/ (p_u·ln2). An implementation that truncates to 10^6 *symbols* (not bits) shows no `-t` effect at all; one that truncates both paths lowers H_original too. |
| E-9 | L = 1,000,000 exactly vs 999,999 (same bytes minus the last). | Intake boundary that the `assert` and all small-count arithmetic rely on. 999,999 ⇒ refusal with "requires at least 1000000"; `-l 1,1000000` on a 1,000,001-byte file loads 1 sample ⇒ refusal (loaded count, not file size). |
| E-10 | one symbol at exactly L−1 of L? No: p̂ = (L−1)/L with L = 10^6, width 1. | p_u = 0.999999 + 2.5758·√(0.999999·1e-6/999,999) ≈ 0.999999 + 2.58e-6 = 1.0000016 ⇒ clamped to 1 ⇒ H = 0. Checks the clamp at scale, and that the −0.0 does not become a `NaN` or a tiny negative through `log2` libm differences across platforms (platform-delta class). |
| E-11 | sparse alphabet {0x00, 0x07, 0xFF}, 20,000 samples (tiny), under an **out-of-tree ASan/UBSan build**. | Translation maps to {0,1,2} so `counts[3]` is indexed in-range. A build or path that skipped translation would write `counts[255]` on a 3-entry stack VLA — stack smash. The production path is argued safe in §2.1; ASan turns the argument into a measurement. (Execution phase; not run here.) |
| E-12 | `-c` on 2,000 random bytes declared 8 (tiny). | Text `h'` vs JSON `hAssessed`. **Measured: h' = 0.658555 per bit; JSON `hAssessed = 5.268438942557462 = 8 × 0.65855486781968275`.** See S-1. |

---

## 5. Suspected deviations, ranked by the brief's severity order

None CRITICAL. None HIGH on this host.

### S-1 — `-c` JSON `hAssessed` is `word_size × h'`, in a unit §3.1.5.2 never defines (MEDIUM, reporting; overstates ×n if a consumer reads it as h')
- Spec: §3.1.5.2 (PDF p. 25) "Let the obtained entropy estimate **per bit** be h'. … hout = min(…, h′ × nout)." The conditioned dataset has no "symbol"; its width in the file is a packing artefact.
- Code: `non_iid_main.cpp:633-637` `h_assessed = data.word_size; if (… || !initial_entropy) h_assessed = min(h_assessed, H_bitstring * data.word_size);` and `:651 printf("\nh': %f\n", H_bitstring);` — the text prints per bit, the JSON `Overall.hAssessed` is per packed byte. `iid_main.cpp:455-458` is identical.
- Measured (probe 4, `logs/analysis-mcv-probe4-conditioned-unit.log`, exit 0 both runs, input `38e39cdd…08ba`): text `h': 0.658555`; JSON `"hAssessed" : 5.268438942557462, "hBitstring" : 0.65855486781968275, "dataWordSize" : 8.0`.
- Direction: a consumer that takes `hAssessed` as h' and forms `h'×n_out` overstates by the packing width (×8 here). `dataWordSize` is present, so the figure is recoverable; the hazard is the field *name*, which under `-i` means the per-sample figure.
- Prior-fix interaction: tracker **F23** (UNCONFIRMED → measured here); upstream PR #251; the `iid_main.cpp:448-470` h_assessed repair preserved this combination deliberately ("ea_non_iid already records only what it computed"). Not in the target profile (`-i`). A one-line owner decision: either document `hAssessed` under `-c` as per-packed-symbol or emit `hPrime` per bit.

### S-2 — the shared `tc631` makes the JSON MCV intermediates literal-only (LOW, neutral)
- `non_iid_main.cpp:362-376` passes the same `tc631` to the Bitstring call (`:365`) and then the Literal call (`:372`); `most_common.h:41-43` overwrite `mcv_estimate_mode/p_hat/p_u` each time.
- Measured (probe 3, `logs/analysis-mcv-probe3-noniid-json-shared-tc631.log`, exit 0): test case "Most Common Value" has `hBitstring 0.2400…`, `hOriginal 0.5364…`, and `mcvEstimateMode 8.0 / PHat 0.4 / PU 0.6895…` — the **literal** triple; the bitstring triple (26, 0.65, 0.8467) appears nowhere in the report. Under `-c` the triple is the bitstring's (probe 4), so the *meaning* of the three fields depends on the mode.
- F23 sub-claim (a), confirmed. The differential harness must use the verbose labels, not the JSON, for bitstring intermediates.

### S-3 — `literal_mcv_estimate` has inverted semantics and is dead (LOW, neutral)
- `most_common.h:44 tc.literal_mcv_estimate = literal.compare(label);` — `compare` is 0 on equality, so the flag is `false` for the literal run. Only consumer is commented out (`test_case_base.h:66-67`). Harmless unless someone un-comments it, at which point every report would label the runs backwards.

### S-4 — negative zero when p_u clamps (LOW, neutral/cosmetic)
- `most_common.h:31 -log2(1.0)` ⇒ `-0.0`; printed `-0`, JSON `-0.0` (probes 2, 3). Parses as 0; conservative; worth normalising only for report hygiene.

### S-5 — `ZALPHA` is one ulp above the correctly rounded quantile (LOW, understates by ≲ 1e-19 bit; D-1 wording)
- `utils.h:75 #define ZALPHA 2.5758293035489008` = `0x1.49b4c64d69161p+1`; correctly rounded binary64 of 2.575829303548900384… is `0x1.49b4c64d69160p+1`. `FORK-DIVERGENCE` D-1 calls the literal "the exact 0.995 standard-normal quantile in binary64" — it is one ulp high. Not a bug; a precision note for D-1 and a bit-exactness caveat for the Python reference.

### S-6 — SUSPICION, platform-specific: `blen = len * word_size` in 32-bit `long` on LLP64 (Windows) (crash / HIGH-if-reachable; not reproducible here)
- `utils.h:520` and `:707 dp->blen = dp->len * dp->word_size;` — both `long`; 32-bit on LLP64. For 8-bit data, `len ≥ 2^28` (268,435,456 samples) overflows (signed UB). At `len ≥ 2^29` the wrapped value can be a small positive: `malloc(blen)` succeeds and the fill loop at `:534-537` writes `len×8` entries — heap overflow before MCV runs; if it survived, the bitstring MCV would run over a bogus `blen`. `ftell` returns 32-bit `long` on Windows so files up to 2 GiB are accepted. Confidence low–medium (source-confirmed on the model of C18, not executed; LP64 here is unaffected). This is the "other 32-bit `long` arithmetic" that C18's entry says was not swept. Only the Windows CI job could measure it, with a ≥ 512 MiB synthetic input — an orchestrator decision.

### S-7 — SUSPICION, out of component: `ea_non_iid` has no `INT_MAX` sample-count refusal although `utils.h:1023-1026` says callers do (LOW here; crash direction)
- `grep INT_MAX cpp/non_iid_main.cpp` is empty; `iid_main.cpp:393` has the guard. `n_choose_2`'s `assert(n <= INT_MAX)` would abort (fail-closed) above 2^31−1 samples; estimators taking `int` counts may wrap earlier. MCV itself takes `long` and is unaffected. For the LRS/t-tuple agent.

---

## 6. Documented divergences in this component — NOT re-reported

| id | where documented | note |
|---|---|---|
| **D-1 / F07 / C22c** — `ZALPHA` vs 2.576 | `FORK-DIVERGENCE-AND-TRUST.md` §B C22c, §D D-1; tracker F07 | code departs from the *printed* text in the permissive direction by ≤ 3.8e-6 bit (recomputed §3). The code does what the record says. |
| **F01** — two-symbol alphabet is binary regardless of declared width | NOTICE 340–358; tracker F01 (withdrawn) | code does what the record says (`non_iid_main.cpp:364`). |
| **F20** — `-t` applies under `-c` | tracker F20 | `non_iid_main.cpp:344` is mode-independent. |
| **F21 / F22** — MSB-first bitstring from raw masked values | tracker F21, F22 | `utils.h:536`; MCV is bit-order-invariant anyway. |
| intake ≥ 10^6 | brief §8; `utils.h:294-317` | the guard MCV's `assert` depends on. |

---

## 7. Out-of-component observations from the probes (for the orchestrator)

1. `ea_iid` on the 20-sample file aborted: `Assertion failed: (n>=p), function periodicity, file permutation_tests.h, line 256.` exit 134 (`logs/analysis-mcv-probe1-iid-spec-example.log`). F15-class, tiny inputs only, requires `EA_ALLOW_SHORT_DATASET=1`. The eight MCV lines it printed first are bit-identical to `ea_non_iid`'s.
2. Final JSON reports carry `"type" : ""` (probes 2–4) although `claimReportTarget` writes `"type": "non-IID"` into the placeholder (`non_iid_main.cpp:82`); the success report does not set it. Cosmetic; `"IID": false` is present.
3. On 20 samples, `Literal LZ78Y … N = 3, C = 1, P_global' = 1 ⇒ min entropy = -0`, which drags `H_original` and `Assessed min entropy` to `-0` (probe 1). Conservative; tiny-input degeneracy, not reachable at MIN_SIZE.

## 8. Probe inventory (instrument rules 2, 4, 5, 17)

| log | binary sha256 (prefix) | input sha256 (prefix) | exit | question settled |
|---|---|---|---|---|
| `analysis-mcv-probe1-noniid-spec-example.log` | `1ad1568c` | `088df27d` | 0 | §6.3.1 worked example reproduces; bitstring pairing arithmetic |
| `analysis-mcv-probe1-iid-spec-example.log` | `22f1319a` | `088df27d` | 134 | same MCV lines from `ea_iid`; abort is in permutation tests |
| `analysis-mcv-probe2-iid-clamp.log` | `22f1319a` | `84188ddd` | 1 (IID failed) | p_u clamps to 1 ⇒ `-0` printed and `-0.0` in JSON |
| `analysis-mcv-probe3-noniid-json-shared-tc631.log` | `1ad1568c` | `088df27d` | 0 | JSON keeps literal MCV triple only |
| `analysis-mcv-probe4-conditioned-unit.log` | `1ad1568c` | `38e39cdd` | 0, 0 | `-c` text h' = 0.658555; JSON `hAssessed` = 8×h' |
| `analysis-mcv-zalpha-rounding.log` | — | — | — | `ZALPHA` is 1 ulp above the correctly rounded quantile; D-1 magnitudes |

All probes used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and are non-compliant
assessments by construction; they settle arithmetic and reporting questions only.
