# Execution-phase overstatement experiments X1–X7 — run plan

Audit 2026-11-07, branch `audit/2026-11-07`. Written in the planning phase, during which the
machine's heavy-job slot was taken: **nothing here over 20,000 samples has been run**. Every
"expected" figure below is labelled by its evidence grade:

| label | meaning |
|---|---|
| **DERIVED** | arithmetic from the construction (stated with the formula) |
| **MODEL** | output of a Python model validated against an independent party (X3 only) |
| **PROBE-20k** | measured on a 20,000-sample prefix with `EA_ALLOW_SHORT_DATASET=1` — NON-COMPLIANT, indicative only |
| **MEASURED** | compliant-size measurement — none yet; the execution phase produces these |

Rule 10 of the brief: record what is measured, not what is expected. The expectations here
exist so the execution phase can tell a surprise from a confirmation; they decide nothing.

## 0. What was done now, and the tooling

* Generators (`harness/experiments/x*_*.py`, all SHA-256-counter-mode deterministic under the
  key prefix `aa-experiments-2026-11-07/` + a per-stream label; no library RNG) wrote 30 files
  to `corpus/experiments/` (23 MB, gitignored) and `harness/experiments/MANIFEST.txt` (name,
  declared bps, n, sha256, generator sha256, experiment, construction). `generate_all.sh`
  regenerates everything; `<gen>.py --check` re-hashes what is on disk
  (`logs/experiments/generate-all.log`: every file `ok`).
* `run_one.sh <name> [--short] -- <cmd...>`: stdout/stderr/rc/meta files under
  `logs/experiments/` (guide rule 17), binary and input sha256 in `.meta` (instrument rule 4),
  `OMP_NUM_THREADS=2`, the escape only with `--short`.
* `check_run.py <name> --json <report>`: labelled reader (instrument rule 5) → `<name>.check.json`
  + one summary line: rc, well-formed, accepted/refused, compliant, Loaded n/k/width, Assessed,
  H_original, n×H_bitstring, refusal text, degenerate tokens (nan/inf/-0), JSON errorLevel/width/
  inferred, notRun flags, and a fold-consistency check (Assessed = min(H_original, n×H_bitstring),
  H_original = min of the printed Literal estimates, H_bitstring = min of the printed Bitstring
  estimates). `check_run.py --compare A B --truth T` compares two runs' Assessed figures.
* `run_experiments.sh X1|…|X7|X7-refusals|checks`: the exact commands below, serial, with the
  checks appended. `REF=1` adds the py90b differential (hours); `OPTIONAL=1` adds the very heavy
  `ea_iid`/`ea_restart` acceptances in X7.
* **Light probes run now** (`light_probes.sh`, log `logs/experiments/light-probes.log`): nine
  `ea_non_iid` runs on ≤ 20,000 samples with the escape, binary `cpp/ea_non_iid` sha256
  `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` (recorded in each `.meta`).
  Results are quoted under X2 and X3 as PROBE-20k.

Production binaries at planning time (Darwin arm64, Apple clang 21, `-O2`, asserts on):
`cpp/ea_non_iid` `1ad1568c…e16f`, `cpp/ea_iid` `22f1319a…7349`, `cpp/ea_restart` `4d7ba82b…419c`
(full digests in `logs/analysis-intake-binaries-sha256.log`; `run_one.sh` re-records them per run).

Costs (estimates, not measured here): `ea_non_iid -i` on 10⁶ 8-bit samples ≈ several minutes with
`OMP_NUM_THREADS=2` (the 8·10⁶-bit bitstring predictors dominate); 1-bit 10⁶ ≈ a minute;
`ea_restart -n` ≈ two literal passes; `ea_iid -i` at 10⁶ = the full §5.1 battery, hours. Refusals
cost nothing. The py90b references at 10⁶ symbols / 8·10⁶ bits are pure Python and can take hours
per module — run them only where a decision needs them (X3), after the main differential ends.

Shared variables in the commands: `T=cpp/ea_non_iid`, `I=cpp/ea_iid`, `S=cpp/ea_restart`,
`D=corpus/experiments`, `L=logs/experiments`, `R=harness/experiments/run_one.sh`,
`V=<scratchpad venv>/bin/python`, `DD=harness/diff_driver.py`, all relative to the audit dir;
`PYTHONPATH=reference` for `python -m py90b.<module>`.

---

## X1 — the F02 width-inference pair (uniform 7-bit data)

**Question.** `n` in §3.1.3's `n × H_bitstring` ("L samples (each having n bits)", PDF p. 20): the
tool infers `n` from the highest set bit when the width is omitted (`utils.h` read_file). On a
capture whose top bit is dead the inferred run (n = 7) was 21.9 % above the declared run (n = 8)
at 20,000 samples (aggregation.md 2.6; tracker F02, repaired by REPORTING only, #254). Pin the
direction at compliant size against the truth and against the declared-n figure.

**Files** (`x1_f02_pair.py`): `x1-uniform7-msbdead-8bit-1000000.bin` = v uniform on 0..127
(sha256 `6c49635a…6a39`); `x1-uniform7-lsbdead-8bit-1000000.bin` = v << 1 (sha256 `d5048d32…04ec`) —
the SAME symbol sequence relabelled order-preservingly, so every Literal estimate is identical by
construction. **Truth: 7 bits/sample exactly (IID uniform on 128 values).**

**Production commands** (`run_experiments.sh X1`):
```
$R x1-msbdead-inferred  -- $T -i -a -v -v -o $L/x1-msbdead-inferred.json  $D/x1-uniform7-msbdead-8bit-1000000.bin
$R x1-msbdead-declared8 -- $T -i -a -v -v -o $L/x1-msbdead-declared8.json $D/x1-uniform7-msbdead-8bit-1000000.bin 8
$R x1-lsbdead-inferred  -- $T -i -a -v -v -o $L/x1-lsbdead-inferred.json  $D/x1-uniform7-lsbdead-8bit-1000000.bin
$R x1-lsbdead-declared8 -- $T -i -a -v -v -o $L/x1-lsbdead-declared8.json $D/x1-uniform7-lsbdead-8bit-1000000.bin 8
$V check_run.py <each> --json $L/<each>.json
$V check_run.py --compare x1-msbdead-declared8 x1-msbdead-inferred --truth 7
$V check_run.py --compare x1-lsbdead-inferred  x1-lsbdead-declared8 --truth 7
```
**Reference** (optional, `REF=1`; the driver passes the width explicitly, so `:7` stands for the
inferred run): `$V $DD run --file $D/x1-uniform7-msbdead-8bit-1000000.bin:7 --file …msbdead…:8 --file …lsbdead…:8 --ref-timeout 7200 …`
→ the `assessed` pseudo-cases must be AGREE (or D-1-explained); a CPP_HIGHER not explained by
D-1 would be a code finding, separate from F02.

**What decides.** `Assessed min entropy` (text, 17 significant digits; = JSON `hAssessed`):
1. `Assessed(msbdead-inferred) / Assessed(msbdead-declared8)` — the F02 ratio at compliant size
   (JSON: `bitsPerSymbol 7, bitsPerSymbolInferred true` vs `8, false`; the declared run also prints
   `Warning: Symbols appear to be narrower than described.`).
2. each Assessed vs **7.0**: either above 7 → the tool reports more than the data has.
3. `H_original` identical across all four runs (same translated symbols) — a difference is a bug.

**Negative control.** `x1-lsbdead-inferred` vs `x1-lsbdead-declared8`: the same dead bit in a
non-leading position; inference gives 8 either way; the two runs must be byte-identical in every
printed estimate (`--compare` ratio 1.000000, `H_bitstring` equal). Shows the effect is the
top-bit inference, not the dead bit itself.

**Expected.** PROBE-20k (analysis phase, aggregation.md 2.6, same construction at 20,000):
inferred 5.396, declared 4.428, ratio 1.219, both < 7. DERIVED: at compliant size the ratio stays
> 1 (the constant eighth bit dilutes every bit-level statistic) and both stay below 7 (the
bit-level MCV alone gives 8 × −log2(0.5625) = 6.64 for the padded stream, 7 × 1 for the pure
stream minus the confidence term). **If positive (Assessed > 7): CRITICAL** — the tool reports
more min-entropy than IID-uniform-7-bit data has; not expected. If only the ratio > 1 is
confirmed: a re-measurement of DOCUMENTED F02 at compliant size (the fork's repair was
visibility; the figure still moves with the declared width) — not a new finding.

**What this cannot see (rule 18).** Whether the inferred figure is "wrong": both runs are
below the truth; the standard's `n` is the submitter's width and the tool has no submitter.

---

## X2 — stuck-LSB structured: can the padded `8 × H_bitstring` exceed the true min-entropy?

**Question** (intake.md E2 / S2). A constant non-leading bit is NOT removed by inference and
enters the bitstring as every eighth bit. The analysis measured that padding a 1-heavy IID stream
raised `n × H_bitstring` above the true per-sample min-entropy (1.345 vs 1.064) while
`H_original` still bound the final figure. X2 makes the real bits a Markov chain so the
bit-level estimators carry the structure, and adds a variant where `H_original` cannot bind.

**Files** (`x2_stuck_lsb_chain.py`; 7,000,000 real bits per source, written two ways):

| source | real bits | packed7 (bits 6..0; width omitted → 7, or declared 8) | lsbpad (bits 7..1, bit 0 = 0; width 8) |
|---|---|---|---|
| A | lag-1 chain, P(r_t = r_{t−1}) = 9/10 exactly | `x2a-chain-lag1-p09-packed7-1000000.bin` `641cffc7…0574` | `x2a-chain-lag1-p09-lsbpad-8bit-1000000.bin` `2a1ec87c…fec9` |
| B | lag-20 chain, P(r_t = r_{t−20}) = 9/10 exactly | `x2b-chain-lag20-p09-packed7-1000000.bin` `33f11d85…20f4` | `x2b-chain-lag20-p09-lsbpad-8bit-1000000.bin` `19d8865d…1db` |

**Truth** (`x2-truth.json`, DERIVED): each real bit is 9/10-predictable given the past, so the
conditional min-entropy per sample is **H_true = −log2(0.9⁷) = 7 × 0.1520031 = 1.0640217
bits/sample** for BOTH sources, padded or not (the pad is constant). Unconditional per-sample
min-entropy: A 1.912 (p_max = 0.5·0.9⁶), B 7.000 (the 7 bits of a sample lie in 7 residue
classes mod 20 and are marginally independent uniform) — the conditional figure is the one an
assessment must not exceed.

**Why B is the variant where `H_original` cannot bind.** For A the symbol-level estimators see
the structure (P(byte_t = "continue the run" | byte_{t−1}) = 0.9⁷ = 0.478: Literal MultiMMC
depth 1 / Lag 1 / LZ78Y land near 1.06, MCV at 1.86). For B the dependence is 20 real bits back
— bits of samples t−3 and t−2 in SHIFTED positions: no symbol repeats an earlier symbol beyond
chance (Lag, MultiMCW), the depth-3 context space (128³ ≈ 2.1 M) cannot be learned from 10⁶
samples under the 100,000-entry cap (MultiMMC, LZ78Y), no tuple repeats (t-Tuple, LRS), so every
Literal estimate is near 6.5–7. Bit level: the pad shifts the real-lag-20 pair to bitstring lag
23 for 6 of 7 real bits and 22 for the 7th (derivation in the generator docstring), so the Lag
predictor's best single lag (23) is right on 6/8 of all positions at 0.9 and guesses the rest
at 0.5 → accuracy 0.80, `H_bitstring ≈ −log2(0.80) = 0.32`, **× 8 = 2.575 (DERIVED)**, while
MultiMMC/LZ78Y (16-bit contexts) cannot reach 22–23 bits back and learn only the pad phase
(0.5625 → 0.83 × 8 = 6.6). The 7-bit stream has lag 20 intact: 0.9 → 0.152 × 7 = 1.064 = truth.

**Production commands** (`run_experiments.sh X2`), per source v ∈ {a-chain-lag1, b-chain-lag20}:
```
$R x2$v-packed7-inferred  -- $T -i -a -v -v -o $L/x2$v-packed7-inferred.json  $D/x2$v-p09-packed7-1000000.bin
$R x2$v-packed7-declared8 -- $T -i -a -v -v -o $L/x2$v-packed7-declared8.json $D/x2$v-p09-packed7-1000000.bin 8
$R x2$v-lsbpad-inferred   -- $T -i -a -v -v -o $L/x2$v-lsbpad-inferred.json   $D/x2$v-p09-lsbpad-8bit-1000000.bin
$V check_run.py --compare x2$v-packed7-inferred  x2$v-lsbpad-inferred --truth 1.0640216541153495
$V check_run.py --compare x2$v-packed7-declared8 x2$v-lsbpad-inferred --truth 1.0640216541153495
```
**Reference** (optional, `REF=1`, hours): `$V $DD run --file $D/x2b-…-lsbpad-8bit-1000000.bin:8 --file $D/x2b-…-packed7-1000000.bin:7 …`.
The decision does not need it; its role is to show the tool computes the standard's figure
(AGREE). A CPP_HIGHER not explained by D-1 would turn X2 into a CODE finding.

**What decides** — three comparisons per source, on `Assessed min entropy` and the
`H_bitstring Per Symbol` line:
1. `n × H_bitstring`(lsbpad) > Assessed(packed7-inferred)? (the padded bitstring term vs the 7-bit figure)
2. `n × H_bitstring`(lsbpad) > **1.0640217**? (the padded term vs the true conditional min-entropy)
3. **Assessed(lsbpad) > 1.0640217?** — the final figure overstates the truth only if `H_original`
   does not bind; this is the question for B.
Also `x2$v-packed7-declared8` (pad FIRST, the F02 pair arm) vs `x2$v-lsbpad-inferred` (pad LAST):
same 7 million bits, two pad positions — expected nearly equal (PROBE-20k: 2.54246 vs 2.54263).

**Negative control.** The 7-bit packed run of the same bits (no padding), width inferred 7:
`Assessed(packed7-inferred) ≤ 1.064` is the baseline that shows the estimators DO see the
structure when it is not padded; and source A is the control for B (same chain strength, the
structure visible to the Literal estimators, `H_original` binds).

**Expected.** PROBE-20k (this phase, `logs/experiments/x2*-probe-*.stdout`, non-compliant):

| run | Assessed | H_original | n×H_bitstring | binding bitstring estimator |
|---|---|---|---|---|
| x2a packed7 inferred (n=7) | 0.53867 | 1.06134 | 0.53867 | Collision 0.0770 |
| x2a packed7 declared 8 | 1.06134 | 1.06134 | 1.07987 | t-Tuple 0.13498 |
| x2a lsbpad inferred (n=8) | 1.06134 | 1.06134 | 1.07987 | t-Tuple 0.13498 |
| x2b packed7 inferred (n=7) | 1.04223 | 4.47450 | 1.04223 | Lag 0.14889 |
| x2b packed7 declared 8 | **2.54246** | 4.47450 | 2.54246 | Lag 0.31781 |
| x2b lsbpad inferred (n=8) | **2.54263** | 4.47450 | 2.54263 | Lag 0.31783 |

So at 20,000: A's padded term (1.080) is above the truth (1.064) by 1.5 % but `H_original`
(1.061, Literal MultiMMC) binds just below it; B's padded ASSESSED figure is 2.39 × the truth
and `H_original` (4.47, Literal LRS at this size) is nowhere near binding. DERIVED for 10⁶:
B lsbpad ≈ 2.57 (Lag's confidence term shrinks), B packed7 ≈ 1.061 (≤ truth), A lsbpad: the
bit-level predictors learn the pad phase and converge to 8 × −log2(0.9125 + ε) = 1.054 < truth
(Jensen: −8 log2((7p+1)/8) ≤ −7 log2 p), so A's padded term is expected to drop BELOW the truth
at compliant size while `H_original` ≈ 1.06 binds either way. **The measurement decides.**

**If positive for B (Assessed(lsbpad) > 1.064 at 10⁶, reference agreeing): CRITICAL by the
brief's definition** (the tool reports ~2.4 × the min-entropy the data has, on a capture that
follows §3.1.3 literally: n = 8, the samples as stored). The mechanism is the STANDARD's
`n × H_bitstring` on a padded capture, not the code; the py90b reference must reproduce it (if
it does not, the code is the finding instead). Filed as a §B-type standard observation
(FORK-DIVERGENCE §B, beside C23/C22c) with the operational rule it forces: assess at the real
width — strip dead bit lines before assessment (§6.4), and note that "always declare 8", the
mitigation aggregation.md 2.6 suggested for F02, is the WRONG way round here (declared 8 on
B-packed7 gives 2.54; inferred 7 gives 1.04). Positive for A on question 2 only: the padded
term exceeds the truth but the final figure does not — the intake.md S2 observation re-measured.

**What this cannot see.** A real device's dead bit is a fault; whether ShannonPad's capture
path can produce one is outside this repository. The "truth" is the conditional min-entropy of
the generating model; the standard's estimators approximate it from below only when the
dependence is within their reach (lag ≤ 128 symbols/bits, 16-symbol contexts, 100,000 entries).

---

## X3 — MultiMMC chained lookup (F10 / C01): the size of the documented margin

**Question.** `multi_mmc_test.h:236` looks depth d up only if depth d−1's prefix was found; §6.3.9
step 4.b (PDF p. 61) looks every depth up independently. With the 100,000-pair cap a pair can be
stored deep while its suffix pair was refused at a full shallower depth ("orphan"); the tool then
treats deeper depths as Null where the text predicts → smaller C, r → HIGHER figure. The record
measured 3.69 × 10⁻⁴ bit; multimmc.md E2 argued a "scoreboard-aware" construction should move it
by ~0.5 bit (+14 correct per period). X3 builds that family and measures it.

**Construction** (`x3_multimmc_orphans.py`): fill of L_f symbols over {16..255} with ALL 3-grams
distinct (every pair new at every depth ≥ 2, so depths 2..16 fill at CONSECUTIVE steps, depth 1
never fills), then a word W over {1..8} (disjoint alphabet) repeated; L_f = 100,001 − b − q so
that depth 2 fills at W offset b = 17 of period 1 and depth 16 at offset 31; offsets 18..31 are
the orphans (stored at depths j+2..16, refused at 2..j+1; their 2-gram contexts never stored).
Two variants, both P = 32:

| variant | file (10⁶, declare 8) | W | q | MODEL per period (text / C++) |
|---|---|---|---|---|
| naive | `x3-mmc-orphan-naive-P32-b17-q0-8bit-1000000.bin` `cf6e4f28…52f7` | all 32 cyclic 2-grams distinct | 0 | **15 / 16** → tool LOWER |
| gadget | `x3-mmc-orphan-gadget-P32-b17-q4-8bit-1000000.bin` `095aeaf1…7116` | 3 repeated 2-grams (free depth-2 ambiguities), pre-roll of W's last 4 symbols | 4 | **19 / 18** → tool HIGHER |

**What the models found (MODEL, this phase; `x3-validation.json`, `logs/experiments/x3-search.out`).**
Two models of steps 1–5 were written: the text as written (`mmc_text`) and the C++ as written
(`mmc_cpp`, transcribed from `multi_mmc_test.h:176-290` and `utils.h PostfixDictionary`). On the
SCALED construction (cap 3,000, 20,000 symbols, `x3-mmc-orphan-{naive,gadget}-scaled-cap3000-8bit-20000.bin`):
* `mmc_text` equals **py90b.multimmc** (`estimate(..., max_entries=3000, k_mode='observed')`)
  EXACTLY on C, r, N, scoreboard, winner and entries, on both variants.
* `mmc_cpp` equals the **production binary** EXACTLY on (C, r) on all three ≤ 20,000-sample
  probes where the real cap cannot bite (`x3-probe-vs-model.json`: prefix 96/2, naive-scaled
  16982/16969, gadget-scaled 16985/16971 — tool and model identical).
* The analysis phase's "+14 per period" does not survive the scoreboard: every depth d ≥ 2
  stores exactly b−1 in-period pairs (the pairs ending at offsets d..b+d−2), so every depth's
  per-period credit is equal in the text, and the text's winner ROTATES — at orphan offset b+j
  the start-of-step winner is depth j+1 whose stored pairs end at b+j−1 → Null (exactly
  multimmc.md's own caveat). Text C = offsets 3..17 = 15/period; the C++ (depth 2 strictly leads,
  no orphan credit) C = offsets 2..17 = 16/period. **The naive construction makes the tool
  LOWER.** The gadget variant (repeated 2-gram contexts with two successors: new pairs, so the
  fill order is untouched; depth 2 wrong once per repeat) pushes the C++ winner to depth 3, which
  then loses the orphan at b+1 that the text's depth 3 keeps: **+1 per period for the text**. A
  search over P ∈ {32,40,48}, b, pre-roll q ∈ {0..15} and words found no variant above +1
  (`x3-search.out`). Reason (DERIVED): orphans need a shallow depth full and a deeper one not — a
  window of ≤ 14 steps that exists only while EVERY pair is new; any repeated pair at a depth
  below the gadget's erodes it, so the deep depths' lead and the orphan window cannot both be
  widened. C01's margin on this family is O(1/P) in P_global, either sign.

**Production commands** (`run_experiments.sh X3`), per variant:
```
$R x3-naive-tool   -- $T -i -a -v -v -o $L/x3-naive-tool.json  $D/x3-mmc-orphan-naive-P32-b17-q0-8bit-1000000.bin 8
$R x3-gadget-tool  -- $T -i -a -v -v -o $L/x3-gadget-tool.json $D/x3-mmc-orphan-gadget-P32-b17-q4-8bit-1000000.bin 8
# spec-literal reference (stdout is the JSON), k = observed alphabet as the tool uses:
PYTHONPATH=reference $R x3-naive-ref  -- $V -m py90b.multimmc $D/x3-mmc-orphan-naive-P32-b17-q0-8bit-1000000.bin 8 --k-mode=observed
PYTHONPATH=reference $R x3-gadget-ref -- $V -m py90b.multimmc $D/x3-mmc-orphan-gadget-P32-b17-q4-8bit-1000000.bin 8 --k-mode=observed
# the two models at the real cap (heavy: ~1 GB, minutes); stdout JSON has text_model / cpp_model:
$R x3-naive-model  -- $V harness/experiments/x3_multimmc_orphans.py --model $D/x3-mmc-orphan-naive-P32-b17-q0-8bit-1000000.bin
$R x3-gadget-model -- $V harness/experiments/x3_multimmc_orphans.py --model $D/x3-mmc-orphan-gadget-P32-b17-q4-8bit-1000000.bin
```
**What decides.** The `Literal MultiMMC Prediction Estimate:` lines `C`, `r`, `N`, `P_global`,
`P_global'`, `min entropy` of the tool vs the reference's `C`, `r`, `min_entropy` (same k).
Exact predictions: the tool's C must equal `cpp_model.C` and the reference's C must equal
`text_model.C` from `--model` (both deterministic). Expected from the scaled rates (DERIVED,
`derived_full_size` in `x3-validation.json`, 28,125.5 periods, N = 999,998):

| variant | text C ≈ | C++ C ≈ | text H | C++ H | tool − reference |
|---|---|---|---|---|---|
| naive | 421,882 | 450,008 | 1.2407 | 1.1479 | **−0.093 bit** (tool lower, conservative) |
| gadget | 534,384 | 506,259 | 0.9006 | 0.9784 | **+0.078 bit** (tool higher, overstating) |

**Negative control.** The naive variant IS the control for the gadget variant (same fill, same
P, b; the sign flips with three repeated 2-grams), and the three ≤ 20,000 probes are the
no-saturation control (tool = both models). At width 1 the chain is provably exact (binary
dictionaries hold ≤ 2^(d+2) pairs < 100,000 for d ≤ 14; multimmc.md 2.5) — no width-1 run is
planned because no orphan can exist there.

**What moves, and what does not.** Only the Literal MultiMMC figure. The headline does not:
on the periodic tail t-Tuple and LRS see every tuple repeat ~28,000 times (PROBE-20k on the
scaled naive file: Literal t-Tuple printed `-0`, LRS 4.0e-5, Lag 4.5e-4, MultiMMC 4.5e-4, while
MCV/MultiMCW/LZ78Y stayed at 2.4-2.6; `H_original = -0`, `Assessed min entropy: -0`), and the
bitstring term is ~10⁻⁴ (Bitstring t-Tuple 9.1e-6). Expected headline at 10⁶: `-0`
or ~0 for both variants, binding estimator not MultiMMC (`check_run.py` prints
`min_of_printed.Literal.binding`). For C01 to reach the headline the data would need MultiMMC
to be the minimum AND the orphan effect to bite — the search shows the effect is ≤ 1/P in
P_global while any periodic structure hands t-Tuple a figure near 0, and non-periodic
re-use of fill segments hands the C++'s shallow winner the credit the text's deep winner
forgoes (SUSPICION, reasoned not measured: C01 cannot move the headline).

**If positive (gadget: tool Literal MultiMMC exceeds the reference by ~0.08 bit, D-1 cannot
explain it): the SIZE of DOCUMENTED DIVERGENCE C01/F10 is re-measured** — reported in the
limitations section, not as a new finding; naive variant positive (tool lower by ~0.09) is the
same divergence in the conservative direction. A MISMATCH between the tool's C and
`cpp_model.C`, or between the reference's C and `text_model.C`, is a NEW finding (model or
code) and stops the record until explained.

---

## X4 — NaN / inf / −0 / silent-drop hunt at compliant size

**Question** (aggregation.md 2.1–2.3). The ten `std::min` folds in `non_iid_main.cpp` are not
NaN-safe: a NaN at the unguarded MCV or Markov sites REPLACES the running minimum and the next
estimate discards it; a NaN at a guarded site is dropped and MISLABELLED `*EstimateNotRun`. No
producer at ≥ 10⁶ was found by reading; X4 looks with inputs built to reach every estimator's
degenerate corner.

**Files** (`x4_degenerate.py`; corpus-identical where noted):

| file | width | corner |
|---|---|---|
| `x4-alternating-1bit-1000000.bin` `2ba60783…ebc3` (= corpus alternating-1bit) | 1 | Collision v = 500,000, X̄ = 2, σ̂ = 0 exactly |
| `x4-alternating-0-255-8bit-1000000.bin` `1154f321…3ac5` (= corpus alternating-8bit) | 8 | two-valued → translated to {0,1}, binary branch, no Bitstring block |
| `x4-two-symbol-0-255-random-8bit-1000000.bin` `f6a4699d…4263` | 8 | the same branch with a non-degenerate sequence (control) |
| `x4-one-symbol-once-1bit-1000000.bin` `3db5c15a…9241` | 1 | 999,999 zeros + one 1 at 500,000: MCV p_u → 1 (−0), Markov P₁₁ = 0, t-Tuple/LRS u,v ≈ 500,000 |
| `x4-one-symbol-once-8bit-1000000.bin` `9e8789bf…0fc` | 8 | uniform 0..254 with 255 exactly once: 256 symbols, one of count 1 |
| `x4-counter-mod256-8bit-1000000.bin` `67870dfc…0cd` (= corpus counter-8bit) | 8 | period 256: every predictor P_global = 1 (−0), t-Tuple u ≈ 991,296 |

**Production commands** (`run_experiments.sh X4`):
```
$R x4-alt1  -- $T -i -a -v -v -o $L/x4-alt1.json  $D/x4-alternating-1bit-1000000.bin 1
$R x4-alt8  -- $T -i -a -v -v -o $L/x4-alt8.json  $D/x4-alternating-0-255-8bit-1000000.bin 8
$R x4-two8  -- $T -i -a -v -v -o $L/x4-two8.json  $D/x4-two-symbol-0-255-random-8bit-1000000.bin 8
$R x4-once1 -- $T -i -a -v -v -o $L/x4-once1.json $D/x4-one-symbol-once-1bit-1000000.bin 1
$R x4-once8 -- $T -i -a -v -v -o $L/x4-once8.json $D/x4-one-symbol-once-8bit-1000000.bin 8
$R x4-ctr8  -- $T -i -a -v -v -o $L/x4-ctr8.json  $D/x4-counter-mod256-8bit-1000000.bin 8
$V check_run.py <each> --json $L/<each>.json
```
**Reference** (optional, `REF=1`): `$V $DD run --file <each>:<bps> --ref-timeout 7200 …` — the
driver records a reference NaN as "declined" and never counts it as agreement; the t-Tuple/LRS
references on the one-symbol-once files (u ≈ 500,000) may be very slow in pure Python.

**What decides** (per run, from `<name>.check.json`):
1. `degenerate`: any `nan`, `inf`, `-inf` token on an estimate or summary line → finding; `-0`
   is a legitimate zero (`-log2(1.0)`) → RECORD (reporting oddity, LOW), and the Assessed figure
   must then be `-0`/0 too.
2. `not_run_flags`: none expected on any of these files (no `v < u` LRS decline here; t-Tuple
   cannot decline at 10⁶) — a flag means an estimator produced NaN or a negative and was
   dropped from the fold while the assessed figure stayed high: finding (MEDIUM/CRITICAL by direction).
3. `fold-consistency`: `H_original` = min of the printed Literal `min entropy` values,
   `H_bitstring` = min of the printed Bitstring values, Assessed = min(H_original, n×H_bitstring)
   — FAIL means a NaN went through an unguarded fold: finding.
4. estimate counts: binary files (alt1, alt8, two8, once1) print 10 Literal and 0 Bitstring
   blocks; non-binary 8-bit (once8, ctr8) print 7 Literal and 10 Bitstring.
5. the Assessed figure itself: alt1/alt8/ctr8 → 0 (−0); once1 → ~0 (MCV −0); two8 → ≤ 1 (binary
   branch, F01 withdrawn: control that the gate did not move); once8 → ≈ 6.5–7.

**Negative control.** `x4-two8` (non-degenerate two-symbol data on the same translation path)
against `x4-alt8`; and the main differential's 50,000-sample results on the corpus twins of
alt1/alt8/ctr8 (`logs/diff/SUMMARY.md`: AGREE/D-1-explained, Assessed 0) as the baseline that
these inputs are accepted and processed.

**If positive: CRITICAL** if a NaN raised the assessed figure (the unguarded MCV/Markov folds),
**MEDIUM** if an estimator was silently dropped/mislabelled with the figure unchanged, **LOW** for
the `-0` print. Expected: no nan/inf (every estimator's codomain is bounded below by reading),
several `-0` prints.

---

## X5 — the `-c` byte-count gate vs §3.1.1 item 2

**Question** (intake.md E10 / 2.5). "a conditioned sequential dataset of at least 1 000 000
consecutive conditioning component outputs" (PDF p. 19) vs `dataset_meets_minimum()` counting
BYTES loaded. For a 256-bit conditioner the tool's gate admits 31,250 outputs.

**Files** (`x5_c_gate.py`): `x5-sha256-outputs-31250-1000000.bin` `bb73f194…c146` = 31,250
consecutive SHA-256(KEY‖counter) outputs = 1,000,000 bytes; `x5-sha256-outputs-31250-999999.bin`
`98a8f905…fecb` = its first 999,999 bytes.

**Production commands** (`run_experiments.sh X5`):
```
$R x5-c-999999 -- $T -c -a -v -v -o $L/x5-c-999999.json $D/x5-sha256-outputs-31250-999999.bin 8    # control, refused, light
$R x5-c-1e6    -- $T -c -a -v -v -o $L/x5-c-1e6.json    $D/x5-sha256-outputs-31250-1000000.bin 8   # heavy
$V check_run.py x5-c-999999 --json $L/x5-c-999999.json ; $V check_run.py x5-c-1e6 --json $L/x5-c-1e6.json
```
**Reference.** None (a gate question; no estimator figure is in dispute). The `h'` line and
`hAssessed = 8 × h'` of the accepted run are recorded as the F23 labelling re-measurement.

**What decides.** `x5-c-1e6`: rc 0, `Loaded 1000000 samples`, JSON `errorLevel 0`, no
`nonCompliantShortDataset`, an `Assessed min entropy` line → the tool ACCEPTED 31,250
conditioner outputs as a compliant `-c` assessment. **Negative control** `x5-c-999999`: rc 255,
JSON `errorLevel -1`, `errorClass "input"`, the §3.1.1 message naming 999999 and 1000000 —
shows the gate is on bytes and sits exactly at 10⁶ bytes.

**If positive (accepted): MEDIUM** — a non-compliant conditioned dataset is accepted as
compliant (direction neutral: fewer outputs make the estimators more conservative, not less).
Owner decision: `-c` could take `n_out` or count bits. Not an overstatement finding.
**What this cannot see:** the tool has no way to know `n_out`; the standard's own text treats
the conditioned output "as a binary string" (§3.1.5.2) while counting "outputs" in §3.1.1.

---

## X6 — a declined estimator in the restart path

**Question** (restart.md E5/S1, prior-repairs.md E3). `ea_non_iid` records a declined LRS as
`literalEstimateNotRun: true` (F05); `restart_main.cpp` never sets that flag, so a declined
row/column estimator leaves the JSON silent and `min(H_r, H_c)` is taken over nine estimators
with nothing saying so.

**File** (`x6_restart_decline.py` → `gen_debruijn.py 100 11`): `x6-debruijn-k100-seed11-1000000.bin`
`4072d768…73d8`, exactly 10⁶ bytes over 0..99, every 3-tuple at most once → on the row dataset
§6.3.6 gives u = 3, v = 2, "If v < u, this estimate cannot be computed" (PDF p. 56); on the
column dataset (symbols 1000 apart) 3-tuples repeat and LRS is computable. Declared 8 (prints
the "narrower than described" warning; values ≤ 99).

**Production commands** (`run_experiments.sh X6`):
```
$R x6-noniid  -- $T -i -a -v -v -o $L/x6-noniid.json  $D/x6-debruijn-k100-seed11-1000000.bin 8
$R x6-restart -- $S -n -v -o $L/x6-restart.json $D/x6-debruijn-k100-seed11-1000000.bin 8 0.5/symbol
$V check_run.py x6-noniid --json $L/x6-noniid.json ; $V check_run.py x6-restart --json $L/x6-restart.json --tool restart
```
(`0.5/symbol` keeps the §3.1.4.3 sanity check and the H_I/2 gate far from binding so the run
completes and writes the full report; `-l` is not a restart option.)

**Reference** (optional): `PYTHONPATH=reference $V -m py90b.lrs $D/x6-…bin 8` → u = 3, v = 2,
NaN (cannot be computed) — pure-Python suffix work at 10⁶ may be slow.

**What decides.** From the two `.check.json`: `x6-noniid` → `not_run_flags` contains
`{"case": "LRS Test", "literal": true}` and the JSON `LRS Test` case has `binLrsRes` but no
`lrsRes`; `x6-restart` → `not_run_flags` EMPTY, `restart_cases_with_h_r` lacks `"LRS Test"` while
`restart_cases_with_h_c` contains it, `Overall.h_r` present, text `min(H_r, H_c, H_I)` printed
and `Validation Test Passed`. **Negative control:** the same bytes through `ea_non_iid`, which
flags the decline — the two reports on one input, one labelled, one silent.

**If positive (restart JSON silent): LOW** — report completeness, direction neutral (the declined
estimate has no value; R-2 keeps −1 out of the fold). Documented as restart.md S1
(SOURCE-CONFIRMED) — this makes it MEASURED.

---

## X7 — 999,999 / 1,000,000 / 1,000,001: refusal exactness, both tools, both widths, `-l`

**Question.** §3.1.1 "at least 1 000 000 sample values" (PDF p. 17); `dataset_meets_minimum()`
on the LOADED count (so `-l` subsets are judged by what they load); `ea_restart` requires
EXACTLY 10⁶ (`data.len != MIN_SIZE`) and the escape does not apply there.

**Files** (`x7_boundary.py`; prefixes of one stream per width): `x7-csprng-{1,8}bit-{999999,1000000,1000001}.bin`
(sha256 in the manifest: 1-bit `0fb1061c…`, `144bd755…`, `78f65869…`; 8-bit `3ae46276…`, `0e60994a…`, `a72bdda1…`).

**Production commands** (`run_experiments.sh X7-refusals` = light part; `run_experiments.sh X7`
adds the `ea_non_iid` acceptances; `OPTIONAL=1` adds `ea_iid` and `ea_restart` acceptances). Per
width W ∈ {1, 8} and tool ∈ {`ea_non_iid`, `ea_iid`} (B = the binary):
```
$R x7-<tool>-<W>bit-999999               -- $B -i -a -v -v -o $L/….json              $D/x7-csprng-<W>bit-999999.bin  <W>   # refused
$R x7-<tool>-<W>bit-l1-1000000-on-1000001 -- $B -i -a -v -v -l 1,1000000 -o $L/….json $D/x7-csprng-<W>bit-1000001.bin <W>   # loads 1 → refused
$R x7-<tool>-<W>bit-l0-999999-on-1000000  -- $B -i -a -v -v -l 0,999999  -o $L/….json $D/x7-csprng-<W>bit-1000000.bin <W>   # refused
$R x7-<tool>-<W>bit-l1-500000-on-1000000  -- $B -i -a -v -v -l 1,500000  -o $L/….json $D/x7-csprng-<W>bit-1000000.bin <W>   # loads 500,000 → refused
$R x7-restart-<W>bit-999999  -- $S -n -v -o $L/….json $D/x7-csprng-<W>bit-999999.bin  <W> <H_I>    # refused (H_I: 0.9 at W=1, 7/symbol at W=8)
$R x7-restart-<W>bit-1000001 -- $S -n -v -o $L/….json $D/x7-csprng-<W>bit-1000001.bin <W> <H_I>    # refused (exactly 10⁶ required)
# heavy acceptances (ea_non_iid, minutes each):
$R x7-non_iid-<W>bit-1000000               -- $T -i -a -v -v -o … $D/x7-csprng-<W>bit-1000000.bin <W>
$R x7-non_iid-<W>bit-1000001               -- $T -i -a -v -v -o … $D/x7-csprng-<W>bit-1000001.bin <W>
$R x7-non_iid-<W>bit-l0-1000000-on-1000001 -- $T -i -a -v -v -l 0,1000000 -o … $D/x7-csprng-<W>bit-1000001.bin <W>
# OPTIONAL=1, very heavy: x7-iid-<W>bit-{1000000,1000001} (full §5.1 battery, hours each); x7-restart-<W>bit-1000000
```
**Reference.** None (the question is the gate, not a figure).

**What decides** (from `.check.json`): every refusal case → rc 255, `refusal` text present,
JSON `errorLevel -1`, `errorClass "input"` (the restart refusal: `errorLevel -1` and the "does not
contain 1000000 samples" message; record whether it carries `errorClass`), NO `Loaded` line
followed by estimates, and no `nonCompliantShortDataset` (the escape is never set here); every
acceptance → `Loaded 1000000` / `Loaded 1000001` / (subset) `subsetActualSamples 1000000`,
`errorLevel 0`, `compliant` true. **Negative controls** are built in: each refused `-l` case has
an accepted sibling on the same file (`-l 0,1000000` vs `-l 1,1000000` on the 1,000,001 file;
the 1,000,000 file whole vs `-l 0,999999`).

**If positive (any acceptance of < 10⁶ loaded samples without the escape, or any refusal of
≥ 10⁶ by `ea_non_iid`/`ea_iid`, or `ea_restart` accepting ≠ 10⁶): MEDIUM** (wrong refusal /
wrong acceptance). Expected: all exact (the 999,999-class is pinned by `regression-minsize.sh`;
the ±1 pair and the `-l` variants are the new measurements). The main differential's
`--only '*-999999.bin'` pass covers the corpus 999,999 files with the driver; X7 adds 1,000,001
and `-l`.

---

## Order of execution and the heavy-job budget

Serial, one at a time (brief rule 4), suggested order by value per minute:
1. `X7-refusals` (20 runs, seconds), `X5` control (seconds) — then `X5` 1e6 (one heavy).
2. `X2` (6 heavy, 8-bit) — the CRITICAL-shaped question; then its `--compare` lines.
3. `X3` (2 heavy tool runs + 2 reference runs + 2 model runs).
4. `X1` (4 heavy), `X4` (6 heavy), `X6` (2 heavy), `X7` acceptances (6 heavy).
5. Optional: `REF=1` driver runs (after the main differential has finished — shared `logs/diff/`),
   `OPTIONAL=1 X7` (`ea_iid` hours).
After each experiment: `run_experiments.sh checks` re-reads every record; FINDINGS entries
quote `<name>.stdout` / `<name>.check.json` lines and the binary sha256 from `<name>.meta`.
