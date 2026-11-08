# Limitations, not bugs — DRAFT for review before it enters FINDINGS.md

Audit 2026-11-07, branch `audit/2026-11-07` (HEAD `1151b22` at the time of writing; the
analysis logs cite `a2c3c81`/`5f79f74`, the same tree for every file named here). Drafted
in the phase that may not build, may not run anything over 20,000 samples and may not
start a sanitizer or fuzzer. Everything measured below was measured by the analysis-phase
agents (cited by file and log) or by the three tiny probes in §4 of this draft; every such
run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is **not a compliant
assessment** (the tool marks each one `nonCompliantShortDataset: true`). The production
binary every cited run executed is `cpp/ea_non_iid` sha256
`1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` (instrument rule 4;
`cpp/ea_iid` `22f1319a…`, `cpp/ea_restart` `4d7ba82b…` where named). Platform: Darwin
arm64, Apple clang 21, binary64 `long double`.

**What belongs here.** An entry is a *limitation* when the code does what SP 800-90B's
text says and the text itself leaves the gap: an estimator fooled by a crafted input
*within its own definition*, a quantity the text does not pin down, a unit the tool is
never told, a statistic the standard cannot measure. The test is the one
`FORK-DIVERGENCE-AND-TRUST.md` uses: *would conforming exactly to the text fix it?* If
yes, it is a code defect and belongs in FINDINGS, not here. Where an entry sits on the
line it says so.

**What this section is not.** Not a list of defects (none of the items below is reported
as a finding), not a restatement of the divergence record (§2 only points at it), and
not a statement about any physical device. Spec quotations are from
`reference/sp800-90b.pages.txt` (sha256 of the source PDF
`9b0dd771…5defe7`); subscripts garbled by the extraction are normalised silently and
the PDF page is given with every quote.

Target profile for every "what it means" paragraph: an Infinite Noise device, 1,000,000+
samples, 1 or 8 bits per symbol, `ea_non_iid -i` (default `-a`), consumed by a pad-sizing
pipeline that reads the assessed figure.

---

## 1. Limitations

Identifiers `L-01`…`L-17` are provisional for this draft; FINDINGS.md may renumber.

### L-01 — a constant *non-leading* bit inflates `n × H_bitstring`, and the standard's own `n` keeps the bit

**The text that creates it.** SP 800-90B §3.1.3 (PDF p. 20): *"If the sequential
dataset is not binary, an additional entropy estimation (per bit), denoted Hbitstring,
is estimated. First, the sequential dataset that contains L samples (each having n bits)
is considered as a bitstring of size nL. … Then, the entropy per sample is estimated to
be n×Hbitstring."* `n` is the sample width — for an 8-bit device, 8, stuck line
included. The only mechanism the standard offers for dropping a dead bit is §6.4 (PDF
p. 66), and it is submitter-driven: *"the submitter may provide the tester with an
ordered ranking of the bits in the n-bit samples … n-bit samples are mapped to m-bit
samples by simply taking the m-bits of greatest rank in order."* It applies only when
*"n exceeds the bit-length that can be handled by the test"*; nothing in the text ranks
or removes a bit of an 8-bit sample.

**What the tool does.** `cpp/shared/utils.h:518-538` builds `bsymbols` from every one
of the `word_size` bits of each masked, untranslated symbol, MSB first
(`dp->blen = dp->len * dp->word_size`, line 520). `cpp/non_iid_main.cpp:636`
`h_assessed = min(h_assessed, H_bitstring * data.word_size)` then multiplies by the
full width. No ranking input exists (`non_iid_main.cpp` usage; `intake.md` §1.4). This
is §3.1.3 exactly.

**Smallest construction.** An 8-bit file whose bit 0 is 0 in every sample and whose
bits 7..1 carry the real data; the same bits packed 7 per byte as the control
(`intake.md` §4 E1/E3; `aggregation.md` §4 item 2).

**Measured, on record.**

| construction | n | `H_bitstring` | `n × H_bitstring` | `H_original` | assessed | truth | log |
|---|---|---|---|---|---|---|---|
| 7 i.i.d. bits, P(1) = 0.9, no padding | 7 | 0.084891705450500551 | **0.5942** | 1.0305 | 0.594 | 1.064 | `logs/analysis-intake-skew09-7bit*.log` (`intake.md` §2.4) |
| same bits + constant LSB 0 | 8 | 0.16815618845789834 | **1.3452** | 1.0305 | 1.031 | 1.064 | `logs/analysis-intake-skew09-lsb0-8bit*.log` |
| uniform 7-bit values, `>> 1` (no pad) | 7 | 0.77087121065528141 | 5.396 | 6.486 | 5.396 | 7 | `logs/analysis-intake-lsb0-shifted-7bit.log` |
| same values, `<< 1` (LSB 0) | 8 | 0.54861603515464596 | 4.389 | 6.486 | 4.389 | 7 | `logs/analysis-intake-lsb0-8bit-inferred.log` |
| **this draft, E2:** bit-chain P(stay) = 0.9, 7 bits/symbol, no pad | 7 | 0.07543917930320973 | **0.52807425512246808** | 0.97823722115996492 | **0.528** | 1.064 | `logs/limitations-e2-chain-7bit-20000-vv.log` (§4) |
| **this draft, E2:** same chain + constant LSB 0 | 8 | 0.11972725651722681 | **0.95781805213781446** | 0.97823722115996492 | **0.958** | 1.064 | `logs/limitations-e2-chain-lsb0-8bit-20000-vv.log` (§4) |

So on the skewed i.i.d. construction the *bitstring term* rose 2.26× and above the true
min-entropy (1.345 > 1.064) and only `H_original` (1.031) kept the final figure under
it; on this draft's dependent-bit construction the *assessed figure itself* rose 1.81×
(0.528 → 0.958) on identical information, and stayed under the truth only because the
unpadded figure was itself 2× conservative (Collision's i.i.d. model on a correlated
chain). Mechanism (`intake.md` §2.4): the inserted zeros *balance* a 1-heavy bit stream
and break its runs, so every marginal bit statistic rises by more than the 8/7 factor
costs — MCV 0.339 vs 0.148, Collision 0.408 vs 0.147, Markov 0.373 vs 0.151 on the skewed
pair; Collision 0.175 vs 0.075, Markov 0.287 vs 0.155 on the chain pair. The uniform
pair shows the direction is not universal: with no bias to balance, the pad *lowers* the
term (4.389 vs 5.396).

**NOT YET MEASURED — execution-phase experiment:** a construction where
`H_original` *also* exceeds the truth, i.e. structure the symbol-level battery misses and
the padded bit-level battery still misses. Neither measured instance reaches the final
figure; `intake.md` S2 holds this as "CRITICAL only if such a dataset is found".

**Why a limitation.** The code implements "each having n bits" literally. A
§6.4-ranked implementation would give the unpadded figure in every row above, but §6.4
is the submitter's step, optional, and scoped to n > the tool's width. Conforming more
exactly changes nothing.

**Asymmetry worth stating (rule 18).** The same physical fault — one stuck line — is
treated two ways: a constant *leading* zero is removed by width inference
(`utils.h:458-470`, L-02) and never enters the bitstring; a constant *low or middle*
bit is kept. The tool cannot see which line is stuck; it sees a highest set bit.

**Target profile and mitigation.** A stuck line on an 8-bit Infinite Noise unit is a
degraded-device scenario and the direction here is *toward* overstatement. Mitigations
that touch no numerics: (i) always pass the width explicitly and refuse a report with
`bitsPerSymbolInferred: true`; (ii) compute the per-position bit bias of the capture
outside the tool (eight proportions; a stuck line is a 0 or 1) and refuse the capture
before assessment; (iii) at width 1 the mechanism does not exist (`blen = len`,
`bsymbols` aliases `symbols`, `utils.h:521`).

### L-02 — the standard does not say how `n` is learned; the tool infers it from the data (F02)

**The text.** §3.1.3 (PDF p. 20) "each having n bits" — `n` is a property of the
source; the text never says how a tester learns it. §3.2.2's documentation requirements
make it the submitter's declared width (tracker F02's reading).

**What the tool does.** With no width argument, `utils.h:458-470` sets `word_size` to
the position of the highest bit set anywhere in the loaded data. A constant top bit is
therefore dropped from the bitstring; `n` shrinks; `n × H_bitstring` changes.
Reported, not changed: `bitsPerSymbol`/`bitsPerSymbolInferred` (`test_run_base.h:76-79`,
commit `97571de`), inference itself left as upstream decided on #254 (tracker F02,
`FORK-FIXED` by visibility).

**Smallest construction.** `corpus/intake-lsb0-shifted-7bit-20000.bin` (20,000 bytes,
MSB never set) run with and without `8`.

**Measured** (`aggregation.md` §2.6, `logs/analysis-aggregation-probe4-*`,
`probe5-*`): inferred n = 7 → `H_bitstring` 0.77087121065528141, assessed
**5.39609847458697**; declared 8 → 0.55343895311860258, assessed **4.4275116249488207**;
ratio **1.219**; `H_original` identical (6.4858263215592542). Relative to the *truth*
(7 bits) the inferred figure is the accurate one and the declared one is conservative
(`intake.md` §2.4); the "+21.9 %" is relative to the declared-width computation the
standard prescribes.

**Why a limitation.** The text fixes neither the source of `n` nor what to do when the
capture under-fills the declared width. The decision to keep inference is recorded
(F02, #254) and is cross-listed in §2 below.

**Target profile and mitigation.** Pass `8` or `1` on every run; refuse
`bitsPerSymbolInferred: true`. With the width passed, L-02 is closed and L-01 remains.

### L-03 — "binary" and `k` are properties of the *observed* alphabet

**The text.** §4.4.2 (PDF p. 34): *"if the noise source is binary (that is, the noise
source produces only two distinct values)"*. §5.1 (PDF p. 38): *"when the input is
binary, i.e., k = 2."* §6.2 (PDF p. 49): *"The Collision, Markov and Compression
estimates are only applied to binary inputs."* §6 (PDF p. 48): *"each si comes from an
output space A = {x1, …, xk} that is specified by the submitter"*; glossary (PDF p. 69):
*"Alphabet size: The number of distinct symbols that the noise source produces."* The
two phrasings of `k` do not agree, and nothing defines "binary" by the sample width.

**What the tool does.** `read_file_subset` counts distinct values into `alph_size`
(`utils.h:515-517`) and translates them to `0..k−1` (`:542-544`). Every bitstring
branch is gated `(data.alph_size > 2) || !initial_entropy` (`non_iid_main.cpp:364, 386,
417, 437, 467, 495, 523, 551, 579, 607`); the binary-only trio runs literal when
`initial_entropy && alph_size == 2` (`:399, 424, 448`); the predictors' `1/k` floor
uses `alph_size` (`utils.h:1207`; `predictor-shared.md` §2.4). This is the withdrawn
F01 question, resolved in favour of the alphabet reading (NOTICE lines 340-364; tracker
F01 row 1101; PR #256 closed).

**Smallest constructions.** (a) 10^6 bytes from {0x00, 0x01} declared `8`: assessed on
the binary branch, `H_original ≤ 1`, no bitstring term (`mcv.md` E-7a). (b) the same
plus one 0xFF: the gate flips, the bitstring term appears, the figure drops ≈ 25 % on
one changed byte (`mcv.md` E-7b, derived). (c) measured at 2,000: 4-bit data plus one
0x80 with width inferred → 17 symbols, n = 8, assessed 1.4843161408205878 against
1.8196406830687593 clean (`logs/analysis-intake-4bit-one80-inferred.log`,
`intake.md` §5). (d) `1/k` with 100 distinct bytes: each predictor prints
`log2 100 = 6.6438561897747244`, not 8 (`predictor-shared.md` E3, derived).

**Why a limitation.** The standard's own definitions are by alphabet, and the two
readings of `k` are both in the text. The tool takes the conservative branch in every
case: the observed alphabet is never larger than the declared one, so `1/k` is larger
and the figure lower or equal; a two-valued 8-bit source has at most 1 bit per symbol
and is assessed at ≤ 1.

**What it cannot see (rule 18).** The classification cannot tell a *designed* binary
source from a device *degraded* to two values (a saturated ADC clipping to 0x00/0xFF
is "binary" to the tool and is correctly assessed at ≤ 1 bit — `OC-109`'s `saturated`
stream scored 1.7249 of 8 only because it was not perfectly two-valued). The figure is
right; the report does not say *why* the alphabet collapsed.

**Target profile and mitigation.** At width 1 the question does not arise. At width 8
the direction is conservative and discontinuous; a consumer should read
`assessedSampleCount` and the distinct-symbol count from the `-vv` text ("Loaded … of
k distinct …") and refuse a capture whose alphabet is far below 256.

### L-04 — Collision step 8 awards one full bit to anti-correlated data

**The text.** §6.3.2 step 7 (PDF p. 50-51): *"The bounds of the binary search should
be 1/2 and 1."* Step 8 (PDF p. 51): *"If the search does not yield a solution, then
the min-entropy estimation is: min-entropy = log2(2)=1."*

**What the tool does.** `cpp/non_iid/collision_test.h:78-86`: the step-7 equation
reduces exactly to `X̄′ = 2 + 2pq` (`collision.md` §1.1), solvable only for
2 ≤ X̄′ ≤ 2.5; `if(X < 2.5) { p = 0.5 + sqrt(1.25 - 0.5*X); entEst = -log2(p); } else
{ p = 0.5; entEst = 1.0; }`. X̄′ > 2.5 means more than half the collisions took three
steps — adjacent bits differ more often than not — and the text says 1 bit. (The X̄′ < 2
side is the clamp, documented divergence D-2, §2.)

**Smallest construction.** Strictly alternating `0101…` at width 1
(`corpus/collision-alt-L3000.bin`; scale to 10^6 for the execution phase).

**Measured** (`logs/analysis-collision-probe-collision-alt-L3000.log:12-19,60`,
`collision.md` §2.5, §5): `X-bar = 3`, `sigma-hat = 0`, `Could Not Find p`, `p = 0.5`,
`Literal Collision Estimate: min entropy = 1`; the run's `H_original = -0` because
Markov and the predictors bind. Compression's cousin (L-05) behaves the same way.

**Why a limitation.** Step 8 is explicit. An implementation that returned 0 or declined
would depart from the text; the fork's clamp on the *other* side (D-2) is already a
documented divergence and the record deliberately did not add one here.

**Target profile and mitigation.** None needed for the figure: a source whose adjacent
bits anti-correlate is caught by Markov (period 2 → 1/128 bit, `markov.md` §5 item 5)
and every predictor, and Collision has never bound on this project's data
(Compression binds, `OC-16`). It matters only to a reader of the per-estimator line.

### L-05 — Compression step 8 awards one full bit when `X̄′` exceeds the uniform expectation (F06), including a stuck-then-live capture

**The text.** §6.3.4 step 7 (PDF p. 55): *"The bounds of the binary search should be
2^−b and 1."* Step 8: *"If the search does not yield a solution, then the min-entropy
estimation is: min-entropy = 1."*

**What the tool does.** `cpp/non_iid/compression_test.h:168` searches only when
`com_exp(1/64, …) > X̄′` (the right-hand side is decreasing in p from its uniform value
to 0), otherwise `p = -1`; `:250-258` then sets `p = 1/alph_size, entEst = 1.0` and
prints "Could Not Find p. Proceeding with the lower bound for p." Tracker F06
`NOT-A-BUG` ("spec-literal behaviour … weakness of the standard").

**Smallest constructions and measurements** (`compression.md` §2.7, cases g and h;
`logs/analysis-compression-run-g.out`, `-h.out`): (g) 6-bit blocks cycling 0..63,
N = 2002 → `X̄ = 6` exactly > cap 5.2177 → **Compression = 1**, while LRS gives 1.9e-5
and binds; (h) **6,000 zero bits followed by 6,012 random bits** → the 63
first-occurrence distances are ≥ 1001, `X̄′ = 5.33` > cap → **Compression = 1** while
MCV says 0.39 and t-Tuple (−0) binds. Case h is the one that matters operationally: a
capture whose first stretch is dead gets *full* Compression entropy, not zero.

**Why a limitation.** Step 8 as written. Reachable only through the standard's own
fallback; the fork's two dormant `p = ldomain` exits are a separate LOW suspicion
(`compression.md` S5), not this.

**Target profile and mitigation.** Compression is the binding estimator on every
stream this project has assessed, so a Compression figure of 1.0 is exactly the case
where the final figure would come from the next-lowest estimator — the battery is the
mitigation and it worked in both cases. A warm-up stretch at the start of a capture is
a real device behaviour; the operator should discard it before assessment (and `OC-109`
measured the `warmup` stream as caught, 1.1043 of 8).

### L-06 — the Markov six-path table is not the maximum-probability 128-step path (D-3)

**The text.** §6.3.3 step 3 (PDF p. 52): *"Find the probability of the most likely
sequence of outputs of length 128, as calculated below."* followed by exactly six rows
(00…0, 0101…01, 011…1, 100…0, 1010…10, 11…1); step 4: *"Let p̂max be the maximum of the
probabilities in the table given above."*

**What the tool does.** `cpp/non_iid/markov_test.h:64-105` evaluates those six rows in
the log domain and `entEst = fmin(H_min/128.0, 1.0)`. Exactly conformant; three
independent checks agree to 17 digits (`markov.md` §5).

**Smallest construction.** A first-order chain with `P00 = 0.61`, `P10 = 0.99`
(`corpus/markov-d3-chain-20k-1bit.bin`, sha256 `fb4c3098…`), where the path
`0(10)^63 0` beats every table row.

**Measured** (`logs/analysis-markov-d3-chain-20k.log`; `markov.md` §2.9): six-table
**0.69812768515899626** (tool = spec-only Python to 16 digits); exact Viterbi over all
2^128 paths **0.6944530900440837**; the conforming figure is **+0.0037 bit/bit** above
the fitted model's true minimum. Analytic ceiling derived there: only `0(10)^63 0` and
its mirror can ever be the strict maximum, margin `< log2(φ)/128 ≈ 0.0054 bit/bit`;
grid sweep 0.0052791 (a lower bound on the supremum, rule 9).

**Why a limitation.** "As calculated below" makes the table the definition.
Repairing it (Viterbi) would print *lower* than §6.3.3 and be a divergence; recorded in
`FORK-DIVERGENCE-AND-TRUST.md` §D D-3 as nobody's defect.

**Target profile and mitigation.** Markov has never bound on this project's data and
the ceiling is 0.0054 bit/bit on that estimator alone. No action.

### L-07 — Compression's printed formulas: the outer-sum limit `L`, the σ̂ radicand, and an unspecified search

**The text.** §6.3.4 step 7 (PDF p. 55): *"G(z) = (1/v) Σ_{t=d+1}^{L} Σ_{u=1}^{t}
log2(u) F(z,t,u)"* — the outer limit is printed as `L`, the bit count. Step 5 (PDF
p. 54): *"σ̂ = c · sqrt( Σ(log2 Di)²/(v−1) − X̄² )"* — not the unbiased sample variance
(that would be `(Σx² − vX̄²)/(v−1)`). Step 7: *"Using a binary search"* with bounds
that *"should be"* 2^−b and 1 and no tolerance.

**What the tool does.** `compression_test.h:17-84` sums over block indices `d+1..N`,
`N = ⌊L/b⌋` (algebraically identical to the printed double sum with that limit,
verified to 2.6e-14, `compression.md` §1.2); `:153` uses the printed radicand;
`:185-196` bisects with a 4-ULP `relEpsilonEqual` stop (`utils.h:74 ITERMAX 1076`).

**What decides each reading.** The standard's own worked example (PDF p. 55, d = 4,
L = 48, v = 4, `p = 0.5715`, `H = 0.1345`): with the sum to N = 8 the solve gives
`p = 0.571484`; with the literal `L = 48` it gives `p = 0.720406, H = 0.0789`
(`logs/analysis-compression-gcheck.log`; `reference/py90b/tests/test_compression.py`
`test_the_literal_upper_limit_L_does_NOT_reproduce_the_example`). The printed radicand
gives the example's `σ̂ = 0.9074`; the unbiased form gives 0.1364
(`test_the_textbook_unbiased_sigma_does_NOT_reproduce_the_example`). So the code's
readings are the example's. Direction if the typos were taken literally: `L` →
**understates**; the printed radicand is *larger* than the unbiased one by
`c²·X̄²/(v−1)` → **conservative**, and at v ≈ 1.33e6 the difference is ~2e-5 relative.
The unspecified search tolerance quantises H by at most **9.8e-8 bit at the cap** and
below 1e-13 at H ≤ 0.95 (`compression.md` §2.4; `logs/analysis-compression-quantisation.log`),
either side; not carried in the floor.

**Why a limitation.** Two typographical ambiguities and one unspecified numeric, each
resolved by the standard's own example or by an implementer's choice; every known
implementation (the fork, the C99 port, the Rust one, the fork's oracle
`compression_ceiling_exact.py`) resolves them the same way.

**Target profile and mitigation.** None. A differential reference must use `⌊L/b⌋` and
the printed radicand or it will disagree at the third digit on the example and at the
~1e-5 level at scale.

### L-08 — errata in the standard's worked examples and tables (the code follows the formulas)

Each of these is a place where the text's *illustration* disagrees with the text's
*algorithm*. The tool follows the algorithm in every case; the reference implementation
records each so that nobody "fixes" code to a typo.

| where (PDF p.) | printed | correct by the text's own formula | record |
|---|---|---|---|
| §6.3.1 example (p. 50) | *"p_u = 0.4 + 2.576√0.012 = 0.6895. The min-entropy estimate is −log2(0.6822) = 0.5363."* | √0.012 is `p̂(1−p̂)/L`; the formula divides by `L−1` (√0.012632); −log2(0.6895) = 0.5364; "0.6822" is the L-divided value. Tool: `p_u = 0.68949822145123085`, `H = 0.53638126455028012` (`logs/analysis-mcv-probe1-noniid-spec-example.log`) | `mcv.md` §1.1 (`OC-32`); `tests/test_mcv.py::test_example_intermediates_are_an_erratum` |
| §6.3.3 example (p. 52-53) | six row probabilities, `0.761` | rows computed from the 3-digit-rounded matrix (3.5-12 % off the exact fractions); exact value 0.76064 (tool `0.76063600625399386`, `logs/analysis-markov-worked-example.log`) | `markov.md` §1, §5; `tests/test_markov.py` |
| Appendix G.2 Table 3 (p. 84) | rows labelled r = 55, 60, …, 155 | each holds the value for r − 5 (0.7092 is r = 50's); 115 other rows reproduce to 4 decimals | tracker F27 `NOT-A-BUG`; `tests/test_lag.py`, `test_lz78y.py`, `test_predictor_common.py` (A6) |
| §5.2.4 (p. 47) | *"the critical value at 0.001, which is 27.887"* | χ²₉ 0.999-quantile is 27.87716; the tool tests the exact quantile (stricter by 0.01 in T) | `iid-chisquare-lrs.md` §1.4, §2.6 |
| §5.1 prose vs Figure 4 (p. 37-38) | *"less than 5 … greater than 9995"* | Figure 4: `≤ 5`, `≥ 9995`; the tool follows the figure (`permutation_tests.h:735-739`) | `iid-permutation.md` §1.1; `reference/py90b/permutation.py` |
| §5.2.1/§5.2.2 (p. 43-45) | `p_i p_j L/2`, `e_i = c_i/10` | the counted pairs are `⌊L/2⌋`, the subsets `⌊L/10⌋`; identical at L = 10^6 | `iid-chisquare-lrs.md` §2.3(a), §2.4 |
| §6.3.7/§6.3.8 examples (p. 58-60) | `0.3908`, `0.6008` | −log2 of the *rounded* P′ (0.7627), and a truncation of 0.600859; within one unit of the last printed place | `predictor_common.py` A8 |

**Why a limitation.** None of these moves a figure; all of them can mislead a reader
comparing a tool's intermediates to the printed example. Neutral.

### L-09 — the `-c` minimum counts bytes, but §3.1.1 item 2 counts *conditioning component outputs* (borderline; owner decision)

**The text.** §3.1.1 item 2 (PDF p. 19): *"a conditioned sequential dataset of at
least 1 000 000 consecutive conditioning component outputs shall be collected for
validation. The output of the conditioning component shall be concatenated in the order
in which it was generated and treated as a binary string for testing purposes."*

**What the tool does.** `utils.h:294-317 dataset_meets_minimum` tests `dp->len >=
MIN_SIZE` where `len` is the number of **bytes** loaded, under `-i` and `-c` alike
(`non_iid_main.cpp:320`, `iid_main.cpp:320`). For an `n_out`-bit conditioner,
1,000,000 outputs are `125,000 × n_out` bytes; the tool accepts 1,000,000 bytes = only
`8,000,000 / n_out` outputs — for SHA-256 (`n_out = 256`), 31,250 outputs, a gate **32×
weaker** than the text's (`intake.md` §2.5). For `n_out ≤ 8` the tool is as strict or
stricter.

**Smallest construction.** 1,000,000 bytes of 256-bit conditioner output under `-c`
(intake E10). **NOT YET MEASURED — execution-phase experiment** (needs a compliant-size
run); the arithmetic is DERIVED from `utils.h:297`.

**Why it is listed here, and why it is borderline.** The standard's unit is a quantity
the tool is never told — `ea_non_iid` has no `n_out` input (only `ea_conditioning`
knows it). It cannot implement item 2's unit from a file alone, which is the sense in
which this is a limitation of the interface the standard assumes rather than of the
arithmetic. But the text is not ambiguous, and the intake agent recorded it as a
MEDIUM *compliance* suspicion needing an owner decision (take `n_out`, or count bits).
Direction: less data makes §6.3 more conservative, so the figure is not overstated; a
non-compliant assessment is accepted as compliant. **No documented decision covers it**
(grep over `FORK-DIVERGENCE-AND-TRUST.md`, `NOTICE`, the tracker: no hit). The
orchestrator should decide whether this line sits here or in FINDINGS.

**Target profile and mitigation.** Outside the profile (`-i` only). If `-c` is ever
used, the operator supplies ≥ `125,000 × n_out` bytes.

### L-10 — the restart sanity check's printed formula tests a single binomial cell, not the maximum it forms (C23 — documented; summary and pointers only)

**The text.** §3.1.4.3 (PDF p. 22): *"Only the experiment yielding the highest count
is tested. If that experiment passes the test, then the other 1999 experiments will
pass as well."* Step 5: *"Calculate P(X ≥ Xmax) = Σ_{j=Xmax}^{1000} C(1000,j) p^j
(1−p)^{1000−j}. If Pr(X ≥ Xmax) < α, the test fails."* with α = 0.000 005 per
experiment and *"0.01 over the entire sanity check"*. The statistic formed in steps 2-4
is the maximum over 2000 rows and columns of the maximum cell count; the tail printed
in step 5 is that of a single binomial cell at probability p.

**What the fork does.** `cpp/restart_main.cpp:754 X_cutoff =
exactMultinomialMaxBound(alpha, H_I)` decides; `:74-87 printedBinomialBound()` is still
computed and recorded as `restartXcutoffPrintedBinomial`; `restartCutoffMethod =
"exact-multinomial-maximum"` (`:805`). **DOCUMENTED DIVERGENCE** — decided in
`FORK-DIVERGENCE-AND-TRUST.md` §B C23, direction corrected at `OC-30`, verification
withdrawn once (`WV-1`) and re-established with 32 oracle-derived pins
(`regression-restart.sh`); independently re-derived this phase by a different method
with **32 of 32 pins matching** (`logs/analysis-restart-cutoff-xcheck.log`;
`restart.md` §2.3).

**Measured, on record.** Implementing the text rejects **83.2 %** of full-entropy 8-bit
matrices (`logs/c23/fullmatrix-false-reject.log`, 2,000 matrices; 82.5 % in a
20,000-matrix run — `restart.md` S10 notes both). The band the text rejects and the fork
accepts, per `H_I` (`restart.md` §2.2): `H_I = 1: Xmax ∈ [571, 572]`, `4: [100, 104]`,
`7: [24, 27]`, `8: [16, 19]`; at `H_I ∈ {0.25, 0.5, 0.75}` the cutoffs coincide. At
the device's operating point `H_I = 0.696` **both cutoffs are 684**, so the divergence
changes no verdict there (`FORK-DIVERGENCE` §B C23 "DOES NOT ESTABLISH"; nearest
disagreement at `H_I ≈ 0.888`).

**Why it is here.** It is the standard's defect, section B; this draft only points.

**What the restart test cannot see (rule 18, `restart.md` S8).** Rows and columns get
the Literal estimators only; no bitstring view exists for width > 1 — §3.1.4.2 invokes
§6.2's list, and the bitstring conversion is prescribed in §3.1.3 for the sequential
dataset. A restart-specific weakness visible only at the bit level is caught only by the
`min(H_r, H_c) < H_I/2` gate.

### L-11 — the standard cannot see a DRBG: a zero-entropy stream is assessed at 7.145 of 8 bits (C-0, `OC-109` — cite, do not re-run)

**The text.** §6 (PDF p. 48): *"the entropy estimation methods described in this
section rely on some statistical assumptions that may not hold for all types of noise
sources. The methods should not replace in-depth analysis of noise sources."* §6.2
(PDF p. 48): *"Testing sequences with dependent values may result in overestimates of
entropy. However, a large, diverse battery of estimates minimizes the probability that
such a source's entropy is greatly overestimated."* §3.1.1 item 1 (PDF p. 19): samples
*"obtained directly from the noise source (i.e., raw data)"*.

**What the tool does.** What every conforming implementation does: measures
statistical structure.

**Measured, on record** (`audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md`
`OC-109`, line 10191; `FORK-DIVERGENCE-AND-TRUST.md` C-0): **AES-256-CTR under an
all-zero key, 1,000,000 samples at width 8 — entropy exactly zero — assessed at
7.1449938481907544 of 8 bits, exit 0, `errorLevel 0`**; all three independent
implementations agree on the binding estimator (Bitstring Compression) to 3.0e-14.
`/dev/urandom` 7.1725, OpenSSL's CSPRNG 6.6384 (and 7.91-7.95 on four fresh draws of
the same command — the 6.64 came from one `r = 4` Lag run; `OC-115`). Five conditioned
streams span **0.82980 to 0.92194 bits per bit**, a band 0.09 wide against a measured
single-capture spread of 0.0894 on five draws of one source, so **no threshold on the
assessed rate can discriminate** (`FORK-DIVERGENCE` C-0). What *is* caught, from the
same record: saturation (1.7249), drift (2.4416), replay (1.594e-06), warm-up (1.1043),
a stuck source (refused), fast-sampled runs (0.1097).

**Why a limitation.** No estimator in §6.3 could distinguish AES-CTR output from noise
without breaking AES; the standard requires raw samples for exactly this reason. Not a
defect of the fork or of NIST's tool.

**Target profile and mitigation.** This is the ranking fact for the device: the figure
establishes nothing about a source whose provenance is not independently established.
The defence is provenance — the capture is bound to the physical source before any
conditioning — and nothing in this repository can supply it. (Memory note "SP 800-90B
cannot see a DRBG"; `CLOSING-INVENTORY.md:100-105`.)

### L-12 — MultiMMC's `maxEntries` cap is a designed ceiling on what the predictor learns, and the fork's saturation margin is a measurement, not a bound (F10/C01)

**The text.** §6.3.9 step 1 (PDF p. 61): *"let maxEntries = 100 000"*; step 4.a.i.2:
*"Else if entriesd < maxEntries, add a counter for [(si−d−1, …,si−2), si− 1] to the
set"*. Once a depth holds 100,000 `[context, next-symbol]` pairs, new pairs at that
depth are never counted and that depth predicts Null on every unseen context forever.
The reference implementation records the literal reading as counting *pairs*
(`reference/py90b/multimmc.py` AMBIGUITIES[0]) and notes that a contexts-counting
variant *"differ[s] materially at width 8 (tested)"*.

**What the tool does — two layers.** (1) The cap itself, per the text:
`multi_mmc_test.h:263-274` (`entries[d] < MAX_ENTRIES`). At width 8 with random data,
depth 2 (65,536 contexts × 256) and every deeper depth saturate after roughly 100,000
samples; thereafter the predictor's `P_global` is bounded by what it learned in the
first tenth of a compliant capture. (2) **Not the text:** `:236 if((d == 0) ||
found_x)` looks up depth d only if depth d−1 found its context, so after saturation a
deeper depth that *would* predict is treated as Null. That is the inherited code defect
`C01`/`F10` (`FORK-DIVERGENCE-AND-TRUST.md` A.1, **NOT REPAIRED**; tracker F10
`UNCONFIRMED`), listed in this section only for its *status*.

**Measured and derived, on record.** One executed overestimate, `f10_over_8bit_1M`,
margin **3.69e-4 bit** (`oracles/entropy_floor.py:88-107`, term `C01`); at width 1 a
**proof** excludes it (`entries[d] ≤ 2^(d+2)`, so the cap cannot bind below d = 15 and
d = 15 has no deeper depth to suppress — `entropy_floor.py:93-100`, re-derived in
`multimmc.md` §2.5). `multimmc.md` §4 E2 argues (derivation, **not measured**) that the
recorded margin is small only because the standard's scoreboard rule defeats the naive
periodic construction, and that a depth-15 ambiguity gadget should move the *Literal*
MultiMMC figure by order 0.5 bit — a change in the *size* of `C01`, not a new finding,
and one t-Tuple/LRS/Lag are argued to bind below.

**Why a limitation.** The cap is the standard's design and is why the floor oracle
*"refuses to call its output a floor at all"* above width 1 (`FORK-DIVERGENCE` A.1).
Conforming more exactly (removing the chain) is a numerics change the owner has not
made.

**Target profile and mitigation.** At width 1: excluded by proof — no exposure. At
width 8: MultiMMC has never bound; the exposure is the unbounded margin on a
non-binding estimator. **NOT YET MEASURED — execution-phase experiment:** E2's gadget
at 10^6 samples against the spec-literal reference, with the width-1 re-expression as
the negative control (`multimmc.md` E3).

### L-13 — an estimator the standard cannot compute is omitted, and the standard does not say what the minimum is then

**The text.** §6.3.6 step 2 (PDF p. 56): *"If v < u, this estimate cannot be
computed."* §6.3.5 step 1 (PDF p. 56) gives no value when no t has 35 occurrences;
§6.3.2 step 5 and §6.3.4 step 5 need v ≥ 2 for σ̂; §6.2 (PDF p. 49) says *"the minimum
of all the estimates is taken"* and nothing about a missing one.

**What the tool does.** Fallible estimators return `−1.0`; every fold in `ea_non_iid`
except MCV and Markov is guarded `if (ret_min_entropy >= 0)` and the decline is recorded
as `literalEstimateNotRun`/`bitstringEstimateNotRun` (F05, `test_case_base.h:37-47`);
the figure is the minimum over the estimators that produced a value, which, as the F05
comment says, *"can only make the figure higher"*. (`ea_restart` drops a decline with no
flag — `restart.md` S1, `prior-repairs.md` §3 F05 — that visibility gap is a FINDINGS
item, not this one.)

**Smallest construction at compliant size.** A de Bruijn B(100,3) sequence is exactly
1,000,000 samples; every 3-tuple occurs once and every 2-tuple ≈ 100 times, so
`u = 3 > v = 2` and LRS declines (`cpp/selftest/regression-notrun.sh:22,45`,
generator `audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py`;
pinned). t-Tuple cannot decline at ≥ 10^6 with k ≤ 256 (the most common symbol occurs ≥
3,906 times, `aggregation.md` §2.8); Collision, Compression and the predictors cannot
decline above their tiny thresholds (5, 6,012 bits, 4,096, 19, 18, 3 samples).

**Why a limitation.** The text defines the condition and is silent on the consequence;
upstream's position (#255, quoted at `test_case_base.h:32-36`) is that this is not an
error.

**Target profile and mitigation.** Only LRS can decline at compliant size, and only on a
pathologically repeat-free input. A consumer should refuse any report in which an
`*EstimateNotRun` field is `true`.

### L-14 — single-estimator blind spots, and a minimum that carries no information about the estimators it did not choose (F28, F29, `OC-16`)

**The text.** §6.2 (PDF p. 48): the battery is "diverse and conservative", and *"a
large, diverse battery of estimates minimizes the probability that such a source's
entropy is greatly overestimated"*; the assessment is the minimum (PDF p. 49). Each
estimator's model is explicit in its own section: Lag sees lags ≤ 128 (§6.3.8 step 1,
PDF p. 59, *"Let D = 128"*); MultiMMC contexts ≤ 16 (§6.3.9); LZ78Y contexts ≤ 16
(§6.3.10); Markov is first-order (§6.3.3); Collision and Compression assume
independence.

**What the tool does.** Each estimator, as specified; `min()` over them
(`non_iid_main.cpp` folds, §2.2 of `aggregation.md`).

**Measured, on record (per-estimator lines; every final figure was caught by another
estimator).**

| construction | blind estimator → its figure | what binds | log |
|---|---|---|---|
| 129 random bytes repeated, L = 5,000 | Lag (D = 128): **5.13** bits | MultiMMC/LZ78Y → `H_original = -0` | `lag.md` §5, `logs/analysis-lag-cpp-*` |
| counter 0..255, 8-bit | Lag: C = 0, `1/k` binds → **8.0** | MultiMMC/LZ78Y ≈ 0 | `lag.md` §5 (derived; tiny instance in `corpus/lag-counter8-5000.bin`) |
| adaptive "anti-Lag" bits (s_i ≠ s_{i−winner}) | Lag: C = 0 → **1.0** bit (F28) | the others | `lag.md` §5 |
| strictly alternating `0101…` | Collision → **1.0** (L-04); Lag-1 always wrong but lag-2 always right → −0 | Markov 1/128 | `collision.md` §2.5 |
| period-4 `0011…` | Markov: all transitions ½ → **1.0** (F29) | t-Tuple/LRS/MultiMMC | `markov.md` §5 item 6 (derived) |
| blocks cycling 0..63 / stuck-then-live | Compression → **1.0** (L-05) | LRS 1.9e-5 / t-Tuple −0 | `compression.md` §2.7 |

**The aggregation half.** `OC-16` ("the detection budget: nine of ten estimators cannot
affect the verdict on near-uniform data"): on fair-coin data **Compression binds in all
five** defect streams tested, only LRS ever bound on a defect (a 600 σ copy
correlation), and *"MCV, Markov, Lag, LZ78Y and MultiMMC never came within a factor of
five of their own headroom"* — the measurement `FORK-DIVERGENCE` D-3 cites as *"a
40-sigma defect in a non-binding estimator leaves the min-entropy figure unchanged"*.
`OC-16`'s own scope note: that is conditional on Compression binding, tested only at
≈ 1.0 bit/bit; *"At a real unit's 0.7-0.86 bit/bit the binding estimator is UNKNOWN
and must be measured."*

**Why a limitation.** Each blind spot is the model each section specifies; the minimum
is what §6.2 prescribes. The standard's claim is only that the battery *minimizes the
probability* of a gross overestimate.

**Target profile and mitigation.** The assessed figure says nothing about the nine
estimators that did not bind, so a defect in a non-binding estimator (or a source
structure visible only there) is invisible in the figure. Store the per-estimator
breakdown from `-vv` against a per-device baseline and alarm on movement in *any* row
(memory note "SP 800-90B aggregation blind spot"); measure which estimator binds on the
real unit before relying on `OC-16`'s headroom table.

### L-15 — "The bits after the first 1 000 000 bits may be ignored" (`-t`)

**The text.** §3.1.3 (PDF p. 20): *"The bits after the first 1 000 000 bits may be
ignored."*

**What the tool does.** `non_iid_main.cpp:344 if (!all_bits && (data.blen > MIN_SIZE))
data.blen = MIN_SIZE;` — opt-in `-t`; the default is `-a` (all bits, `:121-122,
163-174`). `data.len` is untouched, so `H_original` always sees every sample. Under
`-c` the same line applies (tracker F20 `NOT-A-BUG`, #127/#139/#140).

**Smallest construction.** 10^6 bytes whose first 125,000 are period-128 and the rest
random: with `-t` the bitstring estimators see only the periodic 10^6 bits and
`8 × H_bitstring ≈ 0` binds; with `-a` they see all 8 × 10^6 bits (`lag.md` §5 last
row). The reverse (good prefix, defective tail) is the operational hazard: under `-t`
the bitstring track is blind to anything after sample 125,000. **NOT YET MEASURED —
execution-phase experiment**; at 20,000 samples `-t` is a no-op (measured byte-identical,
`logs/analysis-aggregation-probe3-t-vs-a.diff`, `aggregation.md` §5).

**Why a limitation.** Permitted by the text ("may").

**Target profile and mitigation.** Never pass `-t` for the device; `-a` is the default
and the pipeline should assert the `commandline` field carries no `-t`.

### L-16 — numerics the standard leaves to the implementer: the predictors' `P_local` search, `x = x_10`, and the quantile constant

**The text.** §6.3.7 step 6 (PDF p. 58), identical in §6.3.8-§6.3.10: *"Use a binary
search to solve the following for P_local: 0.99 = (1 − P_local x)/((r + 1 − r x) q) ×
1/x^(N+1), where … x = x10, derived by iterating the recurrence relation … for j from 1
to 10 … Note that solving for P_local using the logarithm of these equations is robust
against overflows."* No bracket, tolerance, termination rule or precision is stated; the
confidence constant is printed as `2.576` where step 5 says it *"corresponds to the
Z(1−0.005) value"*.

**What the tool does.** `utils.h:1087-1109` iterates the recurrence to convergence (≤ 66
steps) instead of exactly ten (F08, upstream #133); `:1111-1198 calc_p_local` bisects on
`[max(1/k, P′), 1]` to a 4-ULP stop with every abnormal exit returning the upper
bracket; `ZALPHA 2.5758293035489008` (`:75`) for the printed 2.576 (D-1/C22c, §2).

**Measured, on record.**

| quantity | measurement | record |
|---|---|---|
| `x_10` vs converged | `|P_local(x_10) − P_local(x_∞)| ≤ 6.6e-17` over 84 (N, r) rows; identical to 17 digits on 13 Lag inputs; ≤ 9e-49 bit at N = 9,983 | `predictor-shared.md` §2.2 Q1; `lag.md` §2.3; `lz78y.md` Probe B |
| bisection vs exact root | **two-sided**: 33 of 84 rows below the exact root (overstating side), ≤ 2.37e-9 bit at N = 999,999 (r = 3), ≤ 7.6e-9 at N = 7,999,937; the floor's `C22a = 8.08e-15 (N+1)` is **exceeded 1.72× in the conservative direction** at (N = 4033, r = 3) — so the constant is not a bound on \|error\| and its MEASURED status is the right one | `predictor-shared.md` §2.3, `logs/analysis-predictor-shared-probe2.log`; `FORK-DIVERGENCE` §B "floor is MEASURED" |
| ill-conditioning of `ln(1+δ)` at δ ≈ 0.01/N | `2^-53 (N+1)` noise in F → ~1e-10 at N = 1e6 on binary64 `long double`; 2^11 smaller on x86-64 — the size of the arm64 platform deltas (1.25e-10 … 3.66e-10) | `predictor-shared.md` §2.2; `OC-116`; `reference/py90b/predictor_common.py` A9 |
| printed 2.576 vs exact quantile | +8.70e-08 (Bitstring MultiMCW), +3.80e-06 (Literal MultiMCW), +1.73e-06 (Lag, N = 19,999), +1.0e-6 … +1.4e-5 (t-Tuple/LRS probes); carried as `C22c` ≤ 3.36e-3 bit at n = 10^6 | `FORK-DIVERGENCE` D-1; `lag.md` §2.2; `ttuple-lrs.md` §5 |
| Collision/Compression searches | Collision solved in closed form, exact; Compression 4-ULP stop ≤ 9.8e-8 bit at the cap (L-07) | `collision.md` §2.5; `compression.md` §2.4 |

**Why a limitation.** The standard specifies an equation and leaves its numerical
solution, its precision and the rounding of its constant to the implementer; two
conforming implementations legitimately differ at the 1e-9 level and a platform's
`long double` width shows through. The fork bounds what it can (`C22a`, `C22c`) and the
record says which status each term holds.

**Target profile and mitigation.** Sub-nanobit at N ≤ 8e6; already inside the floor's
terms. A differential driver must carry both `z` constants and treat "P_local can't
change the result" as "P_local ≤ max(P′, 1/k)", not as a missing value.

### L-17 — the IID track's permutation verdict is nondeterministic and its power is the standard's (not in the target profile)

**The text.** §5.1 Figure 5 (PDF p. 38) names Fisher-Yates and no randomness source;
Figure 4 (PDF p. 37) fixes 10,000 permutations and the `≤ 5 / ≥ 9995` cutoffs; the
nineteen statistics are what §5.1.1-§5.1.11 define.

**What the tool does.** Seeds xoshiro256** from `/dev/urandom` (`utils.h:794-810`), does
not record the seed, early-terminates a decided statistic (verdict proved equivalent to
Figure 4, `iid-permutation.md` §2.1). Two runs on identical input differed in **19 of
19** counter rows (`logs/analysis-iid-perm-compare.log`, "seed liveness"); a borderline
matrix can flip between runs (`restart.md` S12). The battery sees what its statistics
see: a lag-3 arithmetic relation `s_{i+3} = s_i + 1 mod 256` is measured by none of them
and not by §5.2's pair test either (`iid-permutation.md` §5).

**Why a limitation.** Inherent to §5.1 as written: a randomised test with an
unspecified source and no replay requirement.

**Target profile and mitigation.** The device is assessed on the non-IID track
(`ea_non_iid -i`); the IID track is not used. If `ea_iid` or `ea_restart -i` is ever
run, the verdict is not reproducible after the fact and the consumer must not treat a
single pass as a stable property.

---

## 2. Documented divergences — pointers, not entries

These are places where the fork **knowingly** departs from the text, or where upstream's
code and the text differ and the record has characterized it. Per the brief's rule 8
they are not findings; the analysis-phase agents re-measured several and found the code
matching its documented decision in every case. Each row says where the decision lives.

| id | the text | what the fork does | direction and bound | decided where | code |
|---|---|---|---|---|---|
| **C23** | §3.1.4.3 step 5 (PDF p. 22): single-binomial tail of `Xmax` | decides on the exact distribution of the multinomial maximum; records the printed figure beside it | the text rejects 83.2 % of full-entropy 8-bit matrices; the fork accepts a band the text rejects (`H_I = 8: Xmax ∈ [16, 19]`); at the device point `H_I = 0.696` both cutoffs are 684 | `FORK-DIVERGENCE-AND-TRUST.md` §B C23; `OC-30` (direction corrected); `WV-1` (withdrawn verification); 32 pins in `cpp/selftest/regression-restart.sh`; re-derived `logs/analysis-restart-cutoff-xcheck.log` (32/32) | `restart_main.cpp:74-87, 113-150, 754, 805, 810` |
| **C22c / D-1** | `2.576` printed in §6.3.1 step 2, §6.3.2 step 6, §6.3.4 step 6, §6.3.5/6 step 4, §6.3.7-10 step 5 | `ZALPHA 2.5758293035489008` (`utils.h:75`), `ZALPHA_L` (`:76`) | **permissive**; worst measured +3.80e-06 bit (Literal MultiMCW); Compression-family ceiling `C22c` = 3.3599e-3 bit at n = 10^6, 2.1644e-3 at 8×10^6, carried in the floor as DERIVED; the Collision family 7.84e-4 / 4.66e-4 | §B C22c, §D D-1; tracker F07 `NOT-A-BUG`; `oracles/c22c_source.json` (single source, `OC-125`); `regression-constants.sh` pins a digest. `mcv.md` S-5 notes the literal is one ulp *above* the correctly rounded quantile (≲ 1e-19 bit, conservative) | every `ZALPHA` site |
| **D-2** | §6.3.2 step 8: no solution → 1 bit (also when `X̄′ < 2`) | `if(X < 2.0) X = 2.0;` → `p = 1`, **0 bits** | **conservative** — fires iff 1 ≤ n₃ ≤ 6 differing adjacent pairs in a million (`collision.md` §2.4); measured `corpus/collision-clamp-L3001.bin` → `p = 1`, `-0` | §D D-2 (upstream code, unchanged) | `collision_test.h:69` |
| **D-4** | §6.3.9 step 4.d: a Null prediction leaves `correct = 0` (worked example i = 3, 4) | NIST's code carried the run across a Null from the winner; the fork **repaired** it (F09) and the Rust implementation **kept** it | the defect was conservative; the repair raises estimates slightly | §D D-4; A.1 carries the repair; `regression-multimmc.sh` (worked example as authority) | `multi_mmc_test.h:144-149, 282-286` |
| **D-5** | §3.1.2: IID not verified → "shall follow the non-IID track"; NIST's reference could print IID failures and still report success | no IID restart estimate after any required IID failure; `errorLevel 2`, exit 1 | fail-closed, conservative | §D D-5; `OC-6` (C03 neighbourhood); #252 | `restart_main.cpp:1139-1167` |
| **D-6** | §3.1.1 says nothing about a sample wider than its declared width | refuse ("Incorrect bit width specification: Data (8) does not fit within described bit width: 1", exit 255) rather than mask; the mask at `utils.h:508-510` is dead code | fail-closed; agrees with the Rust implementation | §D D-6; measured `logs/analysis-intake-4bit-one80-declared4.log` | `utils.h:486-496` |
| **OC-104** | no spec clause; `getopt` permutes on glibc and stops on BSD | an option after `<file_name>` is refused on all three tools; numeric `H_I` values exempt | behaviour divergence from upstream, not a defect; 0 of 256 suite invocations used the refused shape | §A.3 `OC-104`; `regression-option-order.sh` (29 checks, verified by breaking) | `TestRunUtils.h:363-385` |
| **≥ 1,000,000 intake** | §3.1.1 item 1 "at least 1 000 000 sample values"; item 3 exactly 1000×1000 | refuse below 10^6 on the **loaded** count (`-l` subsets included); escape `EA_ALLOW_SHORT_DATASET=1` marks `nonCompliantShortDataset: true` and exits 0; `ea_restart` requires exactly 10^6 with no escape | fail-closed; the escape is the one exit-0 outcome the exit code does not express | brief rule 5; tracker F03/#255; `regression-minsize.sh`; `output.md` §2.5 | `utils.h:294-317`; `restart_main.cpp:694` |
| **fail-closed IID** | §5 intro: "If the hypothesis is rejected by any of the tests, the values in S are assumed to be non-IID" | `iid_test_suite_pass = chi && lrs && perm`; permutation tests skipped after a deterministic failure; no `hAssessed`, `errorLevel 2`, exit 1 | conservative | #252/#271 (N-02); `regression-iid-failclosed.sh`; D-5 for restart | `iid_main.cpp:514-546`; `restart_main.cpp:1123-1167` |

### 2.1 Tracker dispositions the analysis logs treated as documented

Not in the brief's rule-8 list, but each is a recorded decision the analysis agents
re-measured rather than re-reported; listed so the reviewer can see they were seen.

| id | disposition | what the analysis found | where |
|---|---|---|---|
| F01 | `NOT-A-BUG`, **withdrawn 2026-10-02** | binary is by alphabet; the `alph_size > 2` gate stands (L-03) | NOTICE 340-364; tracker row 1101 |
| F02 | `FORK-FIXED` (visibility); inference unchanged on #254 | +21.9 % inferred vs declared re-measured (L-02) | tracker 151, 184-200 |
| F04 | `RESOLVED-BY-GLOBAL-GUARD` | MultiMCW still declines below 4,096 (`multi_mcw_test.h:16-19`); unreachable at 10^6 | `multimcw.md` §2.1 |
| F05 | repaired (`dfe325a`) in `ea_non_iid` only | `ea_restart` sets no not-run flag (routed to FINDINGS) | `prior-repairs.md` §3 F05 |
| F06 | `NOT-A-BUG` | Compression step-8 fallback measured live (L-05) | `compression.md` §2.1 |
| F08 | `NOT-A-BUG`, "UNVERIFIED" | now measured ≤ 6.6e-17 — the analysis recommends closing UNVERIFIED (L-16) | `predictor-shared.md` §3 |
| F20 | `NOT-A-BUG` | `-t` under `-c` is the same line (L-15) | `aggregation.md` §2.1 |
| F23 | `UNCONFIRMED` | both sub-claims **confirmed**: `-c` `hAssessed = word_size × h′`, literal-only MCV intermediates — a consumer trap routed to FINDINGS, not a limitation | `mcv.md` S-1/S-2; `aggregation.md` §2.5; `output.md` §2.2 |
| F27 | `NOT-A-BUG` (spec erratum) | Table 3 labels shifted by 5 (L-08) | `predictor_common.py` A6 |
| F28, F29 | `NOT-A-BUG` (spec limitation) | long-memory deterministic sources and single-estimator blind spots (L-14) | `lag.md` §5; `markov.md` §5 |

---

## 3. Raised by the analysis logs but NOT in this section (code-versus-text; for FINDINGS)

Listed so a reviewer knows they were classified, not forgotten. None is a limitation of
the standard.

- `cpp/conditioning_main.cpp:388-389` folds Collision's `−1` decline into `h′`
  unguarded → `h′ = −1`, `h_out = −8`, exit 0 (reproduced; `collision.md` §3.1;
  `ea_conditioning` is outside supported scope).
- The C14 placeholder claim is skipped when an option error precedes `-o`, leaving a
  stale success report with rc 255 (reproduced on all three tools, `prior-repairs.md`
  §3; contradicts NOTICE's "never a stale success").
- `ea_restart` records no `*EstimateNotRun` flag for a declined estimator
  (`restart.md` S1; `prior-repairs.md` F05; `output.md` §2.9).
- `-c` `hAssessed` is `word_size × h′` with no unit field (F23 confirmed; `mcv.md`
  S-1; `aggregation.md` §2.5; `output.md` §2.2).
- §5.2.1 "do not apply the test" when df < 1 is reported as `df = -1, P-value = 1,
  Passed` (measured, LOW; `iid-chisquare-lrs.md` §2.3(d)).
- LLP64 `blen = len × word_size` wrap and `unsigned long` covariance wrap (Windows
  only; `intake.md` §2.6; `iid-permutation.md` §2.7).
- `std::min` folds not NaN-safe at the MCV/Markov sites and the final fold (no producer;
  F13 hardening gap; `aggregation.md` §2.2-2.3; `output.md` §2.7).
- `xoshiro_jump` accumulators not re-zeroed (threads ≥ 3; neutral; `iid-permutation.md`
  §2.1); bzip2 failure returns 0 (vacuous pass, unreachable at the profile; §2.8).
- `-vvv` prints no per-estimator lines; `-0` printed and serialised for a zero estimate;
  "narrower than described" warning never reaches JSON (several logs; LOW).

---

## 4. Probe record for this draft (instrument rules 2, 4, 5; rule 17)

One question needed a run the analysis phase had named but not made: `intake.md` §4 E2,
"the case where the bitstring term should bind" — does a stuck LSB on *dependent* bits
push the final figure over the truth? Three inputs, generated with
`random.Random(20261107)` by the Python block recorded in this session (bits forming a
first-order chain `P(b_t = b_{t−1}) = 0.9`, 7 chain bits per symbol MSB-first; empirical
`P(stay) = 0.90172` over 139,999 transitions):

| file (`corpus/`) | sha256 | samples | declared |
|---|---|---|---|
| `limitations-e2-chain-7bit-20000.bin` | `6628ee79bef462f4838bcd6817a29f7ed40f0c59c006f9dd26d68334b970c4d3` | 20,000 | 7 |
| `limitations-e2-chain-lsb0-8bit-20000.bin` (same values `<< 1`) | `d6fc18eb91eabecf145ce069a2ad3af4b05b4a8b92d8ed4a94de0b36114ccf2e` | 20,000 | 8 |
| `limitations-e2-chain-1bit-20000.bin` (first 20,000 chain bits) | `745643b13f8364dac061c9819a498092777ab2f1e34cd814a27bbe8938b1698f` | 20,000 | 1 |

Command: `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 cpp/ea_non_iid -i -a -vv <file>
<width> > logs/limitations-e2-<name>-vv.log 2>&1`. Binary
`1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`
(`logs/limitations-e2-binary.sha256`); exit codes all 0
(`logs/limitations-e2-exitcodes.log`). Design truths: conditional min-entropy per 7-bit
symbol `−log2(0.9^7) = 1.064022`; unconditional `−log2(0.5·0.9^6) = 1.912019`; per chain
bit `0.152003`.

Observed (verbatim lines):

```
chain-7bit-20000       (7): Loaded 20000 samples of 101 distinct 7-bit-wide symbols
                            H_bitstring = 0.07543917930320973
                            H_bitstring Per Symbol = 0.52807425512246808
                            H_original = 0.97823722115996492
                            Assessed min entropy: 0.52807425512246808
chain-lsb0-8bit-20000  (8): Loaded 20000 samples of 101 distinct 8-bit-wide symbols
                            H_bitstring = 0.11972725651722681
                            H_bitstring Per Symbol = 0.95781805213781446
                            H_original = 0.97823722115996492
                            Assessed min entropy: 0.95781805213781446
chain-1bit-20000       (1): Literal Markov Estimate: min entropy = 0.15272265095471277
                            Literal Collision Estimate: min entropy = 0.069204201558160677
                            Assessed min entropy: 0.069204201558160677
```

Binding estimators: 7-bit — Bitstring Collision (0.0754), Literal t-Tuple (0.9782);
8-bit — Bitstring t-Tuple (0.1197), Literal t-Tuple (0.9782, identical sequence);
1-bit — Collision. Per-estimator bitstring movement 7 → 8: MCV 0.983 → 0.828, Collision
0.075 → 0.175, Markov 0.155 → 0.287, Compression 0.103 → 0.149, t-Tuple 0.137 → 0.120,
LRS 0.263 → 0.243, MultiMCW 0.228 → 0.196, Lag 0.146 → 0.186, MultiMMC 0.146 → 0.175,
LZ78Y 0.146 → 0.186.

**Result.** The stuck bit raised the assessed figure **1.81×** (0.528 → 0.958) on
identical information; both figures are **below** the conditional truth 1.064, so this
instance does not overstate. It does not establish anything at 10^6 samples, on any
other platform, or for any other structure; the 1-bit control at 20,000 bits confirms
the chain's per-bit Markov figure (0.1527 against 0.1520 designed). The first attempt at
these three runs failed in the shell, not the tool: zsh does not word-split `set -- $spec`,
so the tool received a path ending in ` 7` and an empty width and exited 255 three times;
the three misnamed logs were deleted and the runs redone as explicit commands (memory
note "my own probes answer the wrong question"; the compression agent met the same fault).

---

## 5. What this draft does not establish

- Nothing at compliant size. Every number here is from ≤ 20,000-sample runs under the
  test escape, from DERIVED arguments, or from the prior campaign's records.
- Whether the L-01 mechanism can carry the *final* figure above the truth on any input
  (two constructions measured, neither does).
- The size of the L-12 margin at width 8 (one measured overestimate; a derivation that
  it is larger).
- Anything on Linux x86-64 or Windows; everything measured here is Darwin arm64.
- The consumer's actual read path (which field, which label, which verbose level) —
  outside this repository and not inspected.
