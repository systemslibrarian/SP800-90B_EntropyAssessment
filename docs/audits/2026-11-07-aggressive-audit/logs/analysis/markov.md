# Markov estimate (SP 800-90B §6.3.3) — analysis-phase report

Date 2026-11-07. Branch `audit/2026-11-07`. Analysis phase: no builds, no heavy runs.
Binary measured: `cpp/ea_non_iid` sha256 `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`
(the production binary; never rebuilt by me). Every run below used `EA_ALLOW_SHORT_DATASET=1
OMP_NUM_THREADS=2` and is therefore NOT a compliant assessment; each wrote its full stdout+stderr
and exit status to a file under `logs/` (rule 17). Platform: Darwin arm64, Apple clang 21 build.

Files read line by line: `cpp/non_iid/markov_test.h` (all 114 lines), the call sites
`cpp/non_iid_main.cpp:414-430, 626-694`, `cpp/restart_main.cpp:880-930, 694-716`,
`cpp/conditioning_main.cpp:356-400`, and the parts of `cpp/shared/utils.h` the estimator depends
on (`data_t` :89-100, `dataset_meets_minimum` :294-316, the alphabet/translation/bitstring code
:499-546). Spec text: `reference/sp800-90b.pages.txt` PDF pp. 48, 51-53.

Headline: **the code is an exact transcription of §6.3.3 as written.** Three independent checks
agree to the last printed digit (17 significant figures) with a Python computation written from
the spec text alone (section 5). No path overstates relative to the standard. The one direction
in which the *published figure* can exceed the *fitted model's* true value is the standard's
own six-row table (`D-3`); I give it a mechanism, a construction, a measured instance and an
analytic ceiling of log2(φ)/128 ≈ 0.0054 bit/bit (section 2.9). Everything else is LOW.

---

## 1. The spec's algorithm, step by step

All quotes from SP 800-90B (Jan 2018), `reference/sp800-90b.pages.txt`.

**Scope.** §6.3.3 (PDF p. 51): *"This entropy estimation method is only applied to binary
inputs."* and *"Given the input S = (s1, …, sL), where si ϵ A = {0,1},"*. §6.2 (PDF p. 48)
frames the battery: *"Testing sequences with dependent values may result in overestimates of
entropy. However, a large, diverse battery of estimates minimizes the probability that such a
source's entropy is greatly overestimated."*

**Step 1** (PDF p. 51): *"Estimate the initial probabilities for each output value,
P0 = #{0 in S}/L and P1 = 1 − P0."*
  - Uses all L symbols. No rounding rule, no bound.

**Step 2** (PDF p. 52): *"Let T be the 2×2 transition matrix … where the probabilities are
calculated as P0,0 = #{00 in S}/(#{00 in S}+#{01 in S}), P0,1 = #{01 in S}/(#{00 in S}+#{01 in S}),
P1,0 = #{10 in S}/(#{10 in S}+#{11 in S}), and P1,1 = #{11 in S}/(#{10 in S}+#{11 in S})."*
  - `#{00}+#{01}` is the number of positions i ∈ [1, L−1] with s_i = 0, i.e. zeros among the
    first L−1 symbols (the last symbol starts no pair). Likewise for ones.
  - The spec is silent when a denominator is 0 (0/0). It is silent on zero-probability rows.

**Step 3** (PDF p. 52): *"Find the probability of the most likely sequence of outputs of length
128, as calculated below."* followed by the table

| Sequence | Probability |
|---|---|
| 00…0 | P0 × P0,0^127 |
| 0101…01 | P0 × P0,1^64 × P1,0^63 |
| 011…1 | P0 × P0,1 × P1,1^126 |
| 100…0 | P1 × P1,0 × P0,0^126 |
| 1010…10 | P1 × P1,0^64 × P0,1^63 |
| 11…1 | P1 × P1,1^127 |

  - 128 symbols = 1 start term + 127 transitions. Exponents in each row sum to 127. The phrase
    "as calculated below" makes the table the definition; the six rows are what the standard asks
    for (this matters for `D-3`, section 2.9).

**Step 4** (PDF p. 52): *"Let p̂max be the maximum of the probabilities in the table given above.
The min-entropy estimate is the negative logarithm of the probability of the most likely sequence
of outputs, p̂max: min-entropy = min(–log2(p̂max)/128, 1)"*
  - The only bound is the cap at 1 (an upper cap, i.e. conservative). There is no confidence
    interval, no ε, no minimum L, no tolerance, no iteration, no termination condition.

**Worked example** (PDF pp. 52-53): L = 40, S = (1,0,0,0,1,1,1,0,0,1,0,1,0,1,0,1,1,1,0,0,1,1,0,0,0,
1,1,1,0,0,1,0,1,0,1,0,1,1,1,0); *"P0 = 0.475 and P1 = 0.525. The transition matrix is …
0.389 0.611 / 0.571 0.429"*; row probabilities 3.9837e-53, 4.4813e-30, 1.4202e-47, 6.4631e-53,
4.6288e-30, 1.1021e-47; *"The resulting entropy estimate is min(– log2 (4.6288×10-30)/128,1) =
min(0.761,1) = 0.761."* Footnote 12: *"The test is designed for long sequences (i.e.,
L ≈ 1 000 000)"*. (The spec's row values are computed from the 3-digit rounded matrix; from the
exact counts the value is 0.76064 — the 2026-09-30 audit noted this and I reproduce it below.)

---

## 2. Map to the C++ (`cpp/non_iid/markov_test.h`, function `markov_test`)

Signature (line 6): `double markov_test(uint8_t* data, long len, const int verbose, const char *label)`.
Comment line 5: *"data is assumed to be binary (e.g., bit string)"*.

### 2.1 Step 1 — P0, P1 → lines 10-28, 47-52

```c
18	for(i = 0; i < len-1; i++){
19		if(data[i] == 0){
20			C_0++;
21			if(data[i+1] == 0) C_00++;
22		}
23		else if(data[i+1] == 0) C_10++;
24	}
26	//C_0 is now  the number of 0 bits from S[0] to S[len-2]
28	C_1 = len - 1 - C_0; //C_1 is the number of 1 bits from S[0] to S[len-2]
...
47	// account for the last symbol
48	if(data[len-1] == 0) C_0++;
51	P_0 = C_0 / (double)len;
52	P_1 = 1.0 - P_0;
```

Spec `P0 = #{0 in S}/L`: C_0 after line 48 is the count of zeros over all L symbols; line 51
divides by `len` (= L). **Matches.** `P_1 = 1.0 - P_0` matches the spec's `P1 = 1 − P0` literally.

### 2.2 Step 2 — transition matrix → lines 30-45

```c
31	if(C_0 > 0) {
32		P_00 = ((double)C_00) / ((double)C_0);
33		P_01 = 1.0 - P_00;
34	} else { P_00 = 0.0; P_01 = 0.0; }
39	if(C_1 > 0) {
40		P_10 = ((double)C_10) / ((double)C_1);
41		P_11 = 1.0 - P_10;
42	} else { P_10 = 0.0; P_11 = 0.0; }
```

Here C_0 is the pre-increment count (zeros among S[0..L-2]) = `#{00}+#{01}` exactly; C_1 =
`#{10}+#{11}` exactly. P_00 = #{00}/(#{00}+#{01}) **matches**. P_10 **matches**.

**Deviation 2.2-a (algebraic identity, floating-point not identical).** The spec defines
P0,1 = #{01}/(#{00}+#{01}); the code computes `1.0 - P_00` (line 33), likewise P_11 (line 41). Exact
arithmetic: identical. Doubles: identical whenever C_00/C_0 is exactly representable or the
rounding cancels; they differ by catastrophic cancellation when P_00 ≈ 1. Measured in Python
(`logs/analysis-markov-viterbi.log` §3):

| C_0 | C_00 | code P_01 | spec P_01 | relative | effect on 64·log2 row, per bit |
|---|---|---|---|---|---|
| 1,000,000 | 999,999 | 1.0000000000287557e-06 | 1e-06 | +2.9e-11 | 2.1e-11 bit/bit |
| 1,000,000,000 | 999,999,999 | 9.999999717180685e-10 | 1e-09 | −2.8e-08 | −2.0e-08 bit/bit |
| 1,000,000 | 1 | 0.999999 | 0.999999 | 0 | 0 |

Direction: either (sign depends on the rounding of the quotient). Magnitude at the 1e6 target:
~1e-11 bit/bit, below the 6-decimal `%f` output and only visible in `%.17g`. **LOW**; relevant as
a tolerance floor for the differential driver (guide rule 16): the Python reference, if it
follows the spec ratio literally, will differ from the C++ in the last digits on inputs with a
near-degenerate row. It cannot flip the estimator minimum except on a 1e-11 tie.

**2.2-b (0/0 handling).** When C_0 = 0 (no zeros among the first L−1 symbols) the spec's P0,0
and P0,1 are 0/0; the code sets both to 0.0 (lines 35-36), which then disables every row that
uses them (section 2.4). Same for C_1 = 0. This is a reasonable completion of an undefined case
and can only lower rows that the spec leaves undefined; the one consequence is the sentinel case
in 2.5.

### 2.3 Verbose output → lines 54-62, 107-110

`verbose == 2` prints a one-line summary; `verbose == 3` prints one labelled line per quantity
(`P_0, P_1, P_{0,0}, P_{0,1}, P_{1,0}, P_{1,1}, p-hat_max, min entropy`). **Operational note
(measured):** `non_iid_main.cpp:97` starts `verbose = 1` and `:176` increments per `-v`, so `-vv`
is level 3 and **`-vvv` is level 4, which matches no estimator print path** — my first three runs
at `-vvv` printed only `H_original`/`Assessed` (recorded in the log headers). Not a numerics
issue; the `reference/cpp-verbose-labels-*.txt` capture was made at `-vv`.

### 2.4 Step 3 — the six rows → lines 64-103

```c
64	H_min = 128.0;
70	if(P_00 > 0.0){ tmp = -log2(P_0) - 127.0*log2(P_00); ... }                        // 00…0
76	if((P_01 > 0.0) && (P_10 > 0.0)){ tmp = -log2(P_0) - 64.0*log2(P_01) - 63.0*log2(P_10); } // 0101…01
82	if((P_01 > 0.0) && (P_11 > 0.0)){ tmp = -log2(P_0) - log2(P_01) - 126.0*log2(P_11); }     // 011…1
88	if((P_10 > 0.0) && (P_00 > 0.0)){ tmp = -log2(P_1) - log2(P_10) - 126.0*log2(P_00); }     // 100…0
94	if((P_10 > 0.0) && (P_01 > 0.0)){ tmp = -log2(P_1) - 64.0*log2(P_10) - 63.0*log2(P_01); } // 1010…10
100	if(P_11 > 0.0){ tmp = -log2(P_1) - 127.0*log2(P_11); }                               // 11…1
```
each followed by `if(tmp_min_entropy < H_min) H_min = tmp_min_entropy;`.

Row-by-row against the table: exponents 127 / 64+63 / 1+126 / 1+126 / 64+63 / 127, start terms
P_0,P_0,P_0,P_1,P_1,P_1, all in the standard's order. **Matches exactly.** Computing
−log2 of each product (sum of −log2 terms) and taking the minimum is the same as taking the
maximum probability (log2 is monotone); working in the log domain avoids underflow, though none
occurs here (section 2.7).

**Zero-probability rows are skipped.** The spec has no such rule, but a row with a zero factor
has probability 0 and cannot be the maximum unless every row is 0/undefined; skipping is
equivalent except in that all-skipped case (2.5). The skip is also what keeps `log2(0)` out:

**Log-of-zero proof (why no NaN/inf can be produced).** For each admitted row every log2 argument
is strictly positive:
- `P_00 > 0` ⇒ C_00 ≥ 1 ⇒ some zero in S[0..L-2] ⇒ C_0 (final) ≥ 1 ⇒ P_0 > 0. (Comment lines 66-67.)
- `P_01 > 0` ⇒ C_0 > 0 ⇒ P_0 > 0. `P_11 > 0` ⇒ P_10 < 1 ⇒ C_10 < C_1 ⇒ C_1 ≥ 1 ⇒ P_1 > 0 (next bullet).
- `P_10 > 0` or `P_11 > 0` ⇒ C_1 ≥ 1 ⇒ final C_0 ≤ L − C_1 ⇒ P_0 ≤ 1 − 1/L; as a double P_0 < 1
  whenever L < 2^53, so `P_1 = 1.0 - P_0 ≥ 2^-53 > 0`.
- `P_11 = 1.0 - P_10` is 0 as a double iff C_10 = C_1 exactly (C_1 < 2^53), i.e. iff the spec's
  P1,1 is exactly 0. So `P_11 > 0.0` is the exact spec condition.
Hence every `log2` call sees an argument in (0, 1], every row value is finite and ≥ 0, and
`markov_test` **cannot return NaN, ±inf or a negative number** (−0.0 aside, 2.6). This is what
makes the unguarded fold at the call sites safe (section 3); the 2026-10-11 audit reached the same
conclusion (`EXCLUSION-MAP.md:196`). I re-derived it rather than relying on it.

### 2.5 Step 4 — p̂max and the cap → lines 105-113

```c
105	entEst = fmin(H_min/128.0, 1.0);
107	if(verbose == 2) printf("p_max = %.17g\n", pow(2.0, -H_min));
113	return entEst;
```
`min(−log2(p̂max)/128, 1)` **matches**; `fmin` is the right primitive (would also drop a NaN, moot).

**Deviation 2.5-a — the sentinel (LOW, measured).** `H_min` starts at 128.0 (line 64). If *no*
row is admitted, H_min stays 128.0 and the function returns `fmin(1.0, 1.0) = 1.0` — full
entropy — and prints `p-hat_max = 2^-128 = 2.9387358770557188e-39`, a value no row produced.
When can no row be admitted? Need P_00 = 0, P_11 = 0 and not (P_01 > 0 and P_10 > 0):
- C_1 = 0 (all first L−1 symbols are 0) ⇒ C_0 = L−1, C_00 = L−2 ⇒ P_00 > 0 for L ≥ 3. Fires.
- C_0 = 0 (all first L−1 symbols are 1) ⇒ C_1 = L−1, C_10 ≤ 1 < C_1 for L ≥ 3 ⇒ P_11 > 0. Fires.
- C_0, C_1 > 0 with C_00 = 0 and C_10 = C_1 ⇒ P_01 = P_10 = 1 ⇒ the alternating row fires.
So **the sentinel is reachable only at L = 2**, S = (0,1) or (1,0). Measured
(`logs/analysis-markov-len2-sentinel.log`): both len-2 files print `Literal Markov Estimate:
p-hat_max = 2.9387358770557188e-39` and `min entropy = 1`; the overall `H_original = -0` because
MCV's p_u saturates at 1 on two samples. The len-3 control `(0,1,0)` prints `p-hat_max =
0.66666666666666663`, `min entropy = 0.0045700195368840336` = log2(3/2)/128, the alternating row,
exactly as the spec table gives. Reachability in production: `dataset_meets_minimum`
(`utils.h:294-316`) refuses L < 1,000,000 unless `EA_ALLOW_SHORT_DATASET=1`; `restart_main.cpp:694`
requires `data.len == MIN_SIZE`; `ea_conditioning` has no intake rule (N-03/MS-04, EXCLUDED) but
its bitstring has blen = len × word_size ≥ 2 only when len ≥ 2 … a 2-byte conditioned file with
word_size 1 would reach it. Severity **LOW**: fail-open *by sentinel* is the wrong default for a
min-entropy tool (0.0 or a decline would be right), the printed p̂max is fabricated, but it needs
a 2-sample input. Suspicion, measured, test-path only.

### 2.6 Negative zero (cosmetic, partially measured)

If P_0 = 1 and P_00 = 1 (an all-zero input), row 1 gives `-log2(1.0) - 127*log2(1.0) = -0.0`,
`H_min = -0.0`, `entEst = -0.0`, printed `-0`. The value is correct (zero entropy); only the sign
is odd. Reachable on the Bitstring path with `-t` (`non_iid_main.cpp:344` truncates `blen` to
1,000,000) when the first 125,000 bytes of a multi-symbol 8-bit file are 0x00 — the alph_size>2
gate is satisfied by later bytes. Not run; the same `-log2(1.0)` mechanism was observed from MCV
(`H_original = -0`) in the len-2 log. **LOW/cosmetic**; MCV produces the same −0 first anyway.

### 2.7 Numerics, types, overflow

- All counters and `len` are `long`; on LP64 (this host, Linux) 64-bit: no overflow below 2^62
  samples. `C_0 / (double)len` (line 51) and the explicit casts (32, 40) are correct. Exponent
  constants are doubles (`127.0`, `64.0`, `63.0`, `126.0`): no int promotion issue.
- Windows LLP64: `long` is 32-bit. The estimator's own loop is safe for L ≤ 2^31−1, but
  `utils.h:520 dp->blen = dp->len * dp->word_size` overflows at L > 268,435,455 with 8-bit
  symbols before Markov is called. Outside this file; C18 neighbourhood (`CLOSING-INVENTORY`);
  Windows is not the target platform. Suspicion only, not measured.
- Range of H_min: the admitted-row minimum is ≤ 128 + log2(L) (one of P_00/P_01 ≥ ½ and one of
  P_10/P_11 ≥ ½, so some row has probability ≥ P_s·2^-127), so `pow(2.0, -H_min)` ≥ 2^-148 and
  the printed p̂max never underflows. The cap `min(…,1)` binds exactly when H_min ≥ 128, i.e.
  p̂max ≤ 2^-128.
- `assert(len > 1)` (line 15): the shipped Makefile/BUILD-LINES set no `-DNDEBUG`, so the assert
  is live. Under `-DNDEBUG` with len = 0, line 48 reads `data[-1]` — the known N-03/MS-10
  heap-buffer-overflow, reachable only through `ea_conditioning` (`EXCLUSION-MAP.md:378-380`,
  tracker `EXCLUDED-UNSUPPORTED`). `ea_non_iid` cannot reach it: a 0- or 1-sample file has
  alph_size ≤ 1 and is refused at `non_iid_main.cpp:329` even with the short-dataset escape.
- Determinism: no OpenMP, no RNG, no reduction order — bit-identical across thread counts.

### 2.8 The "binary" assumption and symbol translation

The code tests only `== 0` (lines 19, 21, 23, 48): any non-zero byte counts as "1". The callers
guarantee {0,1}:
- Bitstring path: `utils.h:536` builds `bsymbols[...] = (symbol >> (w-1-j)) & 0x1` — MSB first.
- Literal path (`non_iid_main.cpp:424`, only when `alph_size == 2`): `utils.h:542-544` maps the
  two raw values to {0,1} by ascending raw value. A two-valued 8-bit file {0x03, 0x07} becomes
  {0,1}; without translation it would yield C_0 = 0 ⇒ P_11 = 1 ⇒ estimate 0 (understated).
- Restart: `rdata = data.symbols` (translated) and `cdata` its transpose (`restart_main.cpp:714,
  782`), gated `alph_size == 2` (:883). Both calls are labelled `"Literal"` (:918, :923), so the
  `-vv` row and column lines are indistinguishable except by order — cosmetic, but a
  label-matching differential driver must use position.
- Conditioning: `bsymbols` (`conditioning_main.cpp:392`).
The six-row table is symmetric under 0↔1 (rows 1-3 ↔ 6-4), so the estimate is invariant under
complementing the data; label order cannot matter. (The 2026-09-30 metamorphic bijection test
found Markov invariant, consistent with this.)

### 2.9 `D-3` — the six rows are not the maximum over all 128-step paths: mechanism and bound

The task asked whether `D-3` can overstate *relative to the spec as written*. **It cannot**: step 3
says *"as calculated below"* and step 4 says *"the maximum of the probabilities in the table given
above"*; the code evaluates exactly those six. What follows bounds the overstatement relative to
the *stated intent* ("the most likely sequence of outputs of length 128" under the fitted chain),
which is the standard's property, recorded in `FORK-DIVERGENCE-AND-TRUST.md` §D-3 without a
mechanism or a bound. This is a DOCUMENTED DIVERGENCE, not a code finding.

**Mechanism.** The log-probability of a 128-path is linear in its transition counts
(n00, n01, n10, n11), Σ = 127, plus a start term. For a fixed (n01, n10) every split of the
stays between n00 and n11 is realizable (distribute them over the runs), so the optimum puts all
stays in the state with the larger stay probability. For start 0 the reachable (n01, n10) are
{(j,j)} ∪ {(j+1,j)}: a parallelogram with vertices (0,0), (1,0), (64,63), (63,63). A linear
objective is maximized at a vertex, so the candidates are, per start state and per stay state:

| start 0, stays in 0 | 0^128 ✓ | 0^127 1 ✗ | (01)^64 ✓ | **0(10)^63 0** ✗ |
|---|---|---|---|---|
| start 0, stays in 1 | 0 1^126 0 ✗ | 0 1^127 ✓ | (01)^64 ✓ | (0,63,63,1) ✗ |
| start 1, stays in 1 | 1^128 ✓ | 1^127 0 ✗ | (10)^64 ✓ | **1(01)^63 1** ✗ |
| start 1, stays in 0 | 1 0^126 1 ✗ | 1 0^127 ✓ | (10)^64 ✓ | (1,63,63,0) ✗ |

✓ = in the spec's table (6 distinct). Of the omitted vertices, pairwise comparison with the six
shows (derivation in `logs/analysis-markov-viterbi.log` and below) that **only 0(10)^63 0 and its
mirror 1(01)^63 1 can ever be the strict maximum**:
- `0^127 1` beats `0^128` iff P01 > P00 (so P00 < ½), beats `0 1^127` iff P00 > P11, beats
  `(01)^64` iff P00² > P01·P10; the three force P10 > P01 > P00 > P10 — contradiction.
- `(0,63,63,1)` needs P01·P10 > max(P00², P11²) with P01 < P11 and P10 > P11, which forces
  P01 > ½ and P10 > ½ while P01 + P10 < 1 — contradiction.
- `0 1^126 0` needs P11 > P00 (to beat 0^128) while P10 > P11 and P11 > P01 force P11 < ½ < P00 — contradiction.
- `0(10)^63 0` (counts (1,63,63,0)) beats `(01)^64` iff P00 > P01; beats `0^128` iff
  P01·P10 > P00²; beats `(10)^64` iff P00·P0 > P10·P1. Feasible: e.g. P00 = 0.61, P10 = 0.99.

**Bound.** Its margin over the best table row is ≤ log2(P00/P01); with P01·P10 > P00² and P10 ≤ 1,
P00² < 1 − P00, so P00 < (√5−1)/2 and the margin is < log2(φ) = 0.694 bits over 128 steps, i.e.
**< 0.0054 bit/bit**. Sweep (400×400 grid over (P00, P10), P0 stationary; and a 200×200×99 grid
with P0 free): largest gap 0.67573 bits/128 = 0.0052791 bit/bit — a lower bound on the supremum
(rule 9), consistent with the ceiling.

**Measured instance** (`logs/analysis-markov-d3-chain-20k.log`, `corpus/markov-d3-chain-20k-1bit.bin`
sha256 `fb4c30985e64f9d97239d3ea6153f631c7c1ae70d1a63e7adede6bfd4230c605`, 20,000 one-bit symbols
from a first-order chain P00 = 0.61, P10 = 0.99, `random.Random(20261107)`):
`Literal Markov Estimate: P_0 = 0.72055000000000002, P_{0,0} = 0.61561415683553089,
P_{1,0} = 0.9910538557881553, p-hat_max = 1.258508413704293e-27, min entropy = 0.69812768515899626`.
Spec-only Python on the same file: six-table 0.6981276851589963 (identical), exact Viterbi over
all 2^128 paths 0.6944530900440837 via the path `0(10)^63 0`. The conforming figure is **higher**
than the fitted model's true max-path value by 0.0037 bit/bit. The run's overall figure was
0.18528459933516281 (Compression bound); Markov did not bind — consistent with `D-3`'s
"probably immaterial" and the aggregation measurement.

Direction, if one insists on one: the *standard* overstates relative to its own model by at most
0.0054 bit/bit on the Markov estimator alone, which has never bound on this project's data. The
code is not the place to change it (repairing would depart from §6.3.3).

---

## 3. Where the result goes (the fold)

`non_iid_main.cpp:417-429`: Bitstring call when `(alph_size > 2) || !initial_entropy`; Literal
call when `initial_entropy && alph_size == 2`; both fold with `std::min(ret, H_*)` and **no
`>= 0` guard** (unlike the eight fallible estimators). `std::min(a,b)` is `(b < a) ? b : a`: a NaN
`ret` would become `H_*`, and the *next* estimator's `min(ret2, NaN)` would return `ret2`,
discarding every earlier minimum (positive control recorded by the 2026-10-11 audit:
`std::min(NaN,0.3)=NaN`, `min(8.0,NaN*8)=8`). Section 2.4 proves Markov cannot supply the NaN, so
the unguarded fold is safe *for this estimator*; the hazard is latent (tracker F13 `UNCONFIRMED`).
Then `h_assessed = min(word_size, H_bitstring × word_size, H_original)` (:633-641). In
`restart_main.cpp:918-926` the same unguarded fold into `H_r`/`H_c`.

---

## 4. Prior repairs touching this component, and how to try to break them

`git log --follow -- cpp/non_iid/markov_test.h`: 13 commits, **all upstream history**
(5f2bfdb "Adds Markov test" … 1f2d790 byte→uint8_t). `git blame` of the call site :414-430 is
upstream 2020-2022. **No fork repair has touched the estimator or its fold** (rule 12: no pair to
declare). Repairs *around* it, and the attack on each:

| repair / decision | where | how to try to break it |
|---|---|---|
| ≥ 1,000,000 intake (§3.1.1) | `utils.h:294` `dataset_meets_minimum` | `-l <i>,<n>` with n < 1e6 — refused on the loaded count by design (:281-284). `EA_ALLOW_SHORT_DATASET=1` is the only bypass and brands the run. A 999,999-sample file must refuse; 1,000,000 must run. |
| alphabet-of-1 refusal | `non_iid_main.cpp:329` | A 1e6 file with one symbol occurring once: alph_size 2, Markov runs, row 00…0 gives ≈1.1e-8 (1,0,0,…) or ≈1.4e-6 (0,…,0,1). Must not refuse, must not NaN. |
| F01 WITHDRAWN (gate on alph_size, not width) | `non_iid_main.cpp:417/424` | Two-valued 8-bit file declared width 8: Literal Markov runs on translated {0,1}; NO Bitstring Markov. Compare with the same data as a 1-bit file: identical `Literal Markov` lines. |
| F13 NaN fold UNCONFIRMED | `non_iid_main.cpp:421/428` | Needs a NaN producer; Markov cannot (2.4). A mutation test — make `markov_test` return NaN — would show the fold discard; that is a harness test of the guard, not a reachable input. |
| N-03/MS-10 (conditioning `word_size 0` → `data[-1]`) | `conditioning_main.cpp:364`, `markov_test.h:48` | `EXCLUDED-UNSUPPORTED`; only under `-DNDEBUG`; `ea_conditioning` is not in the supported set. Do not re-report. |
| `-t` truncation of the bitstring | `non_iid_main.cpp:344` (upstream, opt-in; default `-a`) | File whose first 125,000 bytes are 0x00 and the rest varied, `-t`: Bitstring Markov = −0 (2.6). Reverse (good prefix, constant tail) lowers nothing in Markov but H_original's MCV sees the tail. Aggregation agent's territory. |
| `D-3` NOT A REPAIR | — | Bounded here (2.9). Any "repair" (Viterbi) would print *lower* than §6.3.3 and would be a divergence. |

---

## 5. Edge-case inputs that separate a correct from an incorrect implementation

All at width 1 unless stated; "expected" is from the spec table (derived) or measured on the
production binary (stated).

1. **Spec worked example** — `corpus/markov-spec-example-40-1bit.bin` (sha256 `5065e301…`).
   Measured: `min entropy = 0.76063600625399386`, row 1010…10, `p-hat_max = 4.9124204535503759e-30`;
   spec prints 0.761 from a 3-digit-rounded matrix. Derived (Python, appended to
   `logs/analysis-markov-viterbi.log` §5): swapping the 64/63 exponents in the alternating rows
   gives 0.759879 (lower); 128 transitions instead of 127 gives 0.766187 (HIGHER); dividing by
   127 instead of 128 gives 0.766625 (HIGHER). Distinguishes exponent errors at the 3rd digit.
2. **Two samples** `(0,1)`, `(1,0)` — measured: Markov alone prints `min entropy = 1` (sentinel,
   fabricated p̂max 2^-128). A correct-by-intent implementation would print 0 or decline. Reachable
   only with the short-dataset escape.
3. **Three samples** `(0,1,0)` — measured 0.0045700195368840336 = log2(1.5)/128. Checks the
   alternating row and P_0 = 2/3 start term.
4. **D-3 chain** `corpus/markov-d3-chain-20k-1bit.bin` — measured 0.69812768515899626. A tool
   printing anything HIGHER on this file is wrong; a tool printing 0.69445 implemented Viterbi
   (lower; spec-divergent). Regenerate at 1e6 with the same generator for a compliant-size run.
5. **Period 2** `0101…` (1e6) — derived: P01 = P10 = 1, P00 = P11 = 0 ⇒ H = −log2 P0 = 1 ⇒
   **0.0078125**. An implementation that lets `log2(0)` through produces NaN/inf and, via the
   unguarded fold, could discard earlier minima or print 1.0.
6. **Period 4** `0011…` (1e6) — derived: all four transitions ½, P0 = ½ ⇒ every row 2^-128 ⇒ **1.0**
   (the F29 blind spot; spec-consistent). Must be caught by t-tuple/LRS/MultiMMC in the fold.
7. **Near-constant** `0^999999 1` — derived ≈1.44e-6 (row 00…0 only; rows needing P10/P11 are
   disabled). `1 0^999999` — derived ≈1.1e-8 (row 00…0 with P00 = 1 beats row 100…0 = 0.1557). A
   wrong implementation that evaluates `-log2(P_1)` for the disabled rows gets +inf and may pick
   the wrong minimum.
8. **Translation invariance** — same bit sequence as {0x00,0xFF} declared width 8, as {0x03,0x07}
   width 8, as 1-bit, and complemented: all four `Literal Markov` blocks must be identical
   (table symmetry + translation). Raw-`==0` without translation would print 0 for {0x03,0x07}.
9. **Cancellation row** — C_0 = 1e6, C_00 = 1e6−1 (a 1e6+1-sample file with one 01 pair): code and
   spec-ratio implementations differ by ~2e-11 bit/bit in the `%.17g` digits (2.2-a). Sets the
   differential tolerance; not a defect.
10. **Boundary 1,000,000 vs 999,999** — intake refusal, not Markov; include so the harness asserts
   the baseline is accepted (rule 7).

---

## 6. Probes run (all tiny, all logged, none compliant)

| log | input | result |
|---|---|---|
| `logs/analysis-markov-viterbi.log` | pure Python from the spec text; no binary | six-table = Viterbi on the worked example; D-3 construction; grid max 0.0052791 bit/bit < ceiling 0.0054238; FP cancellation table; corpus files written with sha256 |
| `logs/analysis-markov-worked-example.log` | 40-bit spec example, `-vv` | `min entropy = 0.76063600625399386`, exit 0 |
| `logs/analysis-markov-len2-sentinel.log` | len 2 ×2, len 3 | sentinel `1` with p̂max 2^-128 at len 2; 0.00457 at len 3; exit 0 |
| `logs/analysis-markov-d3-chain-20k.log` | 20k chain, `-vv` | `0.69812768515899626` = spec-only Python to 16 digits; overall 0.185 (Compression) |

What these probes cannot see: behaviour at 1e6+ (no heavy runs in this phase), Windows LLP64,
the `-t`/all-zero-prefix path, and `ea_restart`/`ea_conditioning` call sites (source-traced only).

---

## 7. Verdict for this component

- **CRITICAL/HIGH: none found.** No input-reachable path makes `markov_test` report more than
  §6.3.3 as written; no NaN/inf/negative return; no memory-safety issue in a supported binary
  (the `data[-1]` read is the known, excluded `ea_conditioning` + `-DNDEBUG` combination).
- **DOCUMENTED DIVERGENCE `D-3`**, now with mechanism, construction, measured instance and ceiling
  (≤ log2(φ)/128 ≈ 0.0054 bit/bit, Markov alone, never binding here).
- **LOW** (suspicions, measured where stated): len-2 sentinel returns 1.0 with a fabricated p̂max;
  `1.0 − P_00` cancellation ≤ 2e-11 bit/bit at L = 1e6; −0 on an all-zero (truncated) bitstring;
  `-vvv` prints no estimator lines; restart labels rows and columns both "Literal".
