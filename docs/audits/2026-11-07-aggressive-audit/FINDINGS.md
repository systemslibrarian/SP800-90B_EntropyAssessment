# Aggressive security and correctness audit — findings

**Status: IN PROGRESS (this file is rewritten as phases complete; the final version is the one on the
tip of `audit/2026-11-07`).** Date begun 2026-11-07; host Darwin arm64 (macOS 25.6.0), Apple clang 21.0.0,
Homebrew libomp, jsoncpp 1.9.8, Python 3.14.7 / numpy 2.5.4 (venv), AFL++ 5.03c (installed for this
audit from the Homebrew bottle — see AA-15 for the side effect that install had on the build).

Subject: this fork of NIST's SP 800-90B Entropy Assessment, `master` at `04c1ccc` (audit branch
`audit/2026-11-07` carries only `docs/audits/2026-11-07-aggressive-audit/`). Production binaries
rebuilt from that tree on 2026-11-07: `ea_non_iid` sha256 `1ad1568c…`, `ea_iid` `22f1319a…`,
`ea_restart` `4d7ba82b…` (`logs/build-rebuild-2026-11-07.log`); the self-test on them reproduces every
reference figure up to the eight documented macOS platform deltas, all within the manifest.

Authority: NIST SP 800-90B (January 2018), downloaded from nvlpubs.nist.gov on 2026-11-07, sha256
`9b0dd77131ade3617a91cd8457fa09e0dc354c273bb2220a6afeaca16e5defe7` (byte-identical to
`audits/2026-09-30/reference/NIST.SP.800-90B.pdf`); text with PDF page markers at
`reference/sp800-90b.pages.txt`. Citations are `§x.y.z (PDF p. N)`.

Rules: this repository's own (`audits/BUG-REPAIR-GUIDE.md`, instrument rules 1–5, rules 6–18). Nothing
was sent upstream; every `gh` call named the fork. `master`, every tag and all published history are
untouched; fixes are on `fix/<topic>` branches, one per fix, unmerged.

Severity (the brief): **CRITICAL** — the tool can report more min-entropy than the data has;
**HIGH** — memory safety / undefined behaviour reachable from an input file; **MEDIUM** — wrong
result in the conservative direction, wrong refusal, nondeterminism; **LOW** — everything else.
Crafted inputs that fool an estimator *within the standard's own design* are **LIMITATIONS**, not bugs,
unless the code departs from the text.

---

## 0. Summary for Paul

_(written last — see the end of this file)_

---

## 1. Findings, ranked

Every entry carries a reproducer, observed vs expected, the spec citation, a negative control, the
binary sha256 and the platform. **No CRITICAL code defect was found**: nothing made the C++ report more
min-entropy than the standard's own algorithm gives (§1.4 below records the one case where the
standard's algorithm itself overstates — it is a LIMITATION, §2, and the headline for Paul). **No HIGH
defect was found** on this host (sanitizer and fuzzing coverage: §4). Entries marked PROVISIONAL are
awaiting the three-lens verification; the final file removes the marks or the entries.

### 1.1 MEDIUM

**AA-01 — the `-c` minimum counts BYTES, the standard counts conditioning-component OUTPUTS** (permissive
gate; `ea_non_iid -c`, `ea_iid -c`). Spec: §3.1.1 item 2 (PDF p. 19) — *"a conditioned sequential dataset of
at least 1 000 000 consecutive conditioning component outputs"*. Code: `cpp/shared/utils.h:297`
`if (dp->len >= MIN_SIZE) return true;` where `len` is bytes loaded, under `-i` and `-c` alike
(`non_iid_main.cpp:320`, `iid_main.cpp:320`). Reproducer (experiment X5, `harness/experiments/x5_c_gate.py`,
`logs/experiments/x5-c-1e6.*`): 1,000,000 bytes that are **31,250** SHA-256 outputs, `ea_non_iid -c -a -vv -o … f 8`
→ exit 0, `errorLevel 0`, no `nonCompliantShortDataset`, `Assessed min entropy: 7.1978448401477628`
(= `n × H_bitstring`). Expected: refusal (31,250 < 1,000,000 outputs). Negative control: the same stream at
999,999 bytes is refused (`x5-c-999999`, exit 255, `errorLevel -1`). Binary `1ad1568c…`, Darwin arm64. Direction:
permissive (a non-conforming dataset is assessed as compliant). Why MEDIUM not CRITICAL: the figure printed is the
standard's figure for the bits given; what is wrong is the compliance claim. Prior-fix interaction: the ≥ 1,000,000
intake (upstream #255 family, `regression-minsize.sh`) — this is its `-c` blind spot. The tool is never told
`n_out`, so the repair is an interface decision (an `n_out` argument, or a documented statement that `-c`'s gate is
on bytes); recorded for the owner, not fixed here.

**AA-02 — a stale SUCCESS report survives when an option error precedes `-o`** (all three tools). PROVISIONAL
(`repro/PROV-01`). NOTICE promises the `-o` file *"is never a stale success"* (C14). Mechanism: the C14 placeholder is
claimed when `getopt` reaches `-o`; an invalid option (`-Z`) or a malformed `-l` earlier in `argv` exits 255 before
that, so a previous complete report at the path survives byte-identical — `ea_non_iid`, `ea_iid`, `ea_restart`
(`logs/analysis/prior-repairs.md`, probes A–D; control `-o p -Z` is replaced as designed). Exit status is nonzero,
so a status-checking caller is safe; a file-reading consumer is not. Fix offered: `fix/stale-report-option-error`.

**AA-03 — under `-c`, JSON `hAssessed` is `word_size × h'` while stdout prints `h'` per bit; no unit or mode field**
(tracker F23, previously UNCONFIRMED). PROVISIONAL (`repro/PROV-02`). Spec: §3.1.5.2 (PDF p. 25) defines `h'` per
bit. Code: `non_iid_main.cpp:633-637` vs `:651`. A consumer reading `hAssessed` as the per-bit `h'` overstates by
`bitsPerSymbol` (up to 8×). Not on the `-i` target profile.

**AA-04 — `ea_restart` omits a declined row/column estimator with no not-run flag, and no JSON field carries the
awarded `min(H_r, H_c, H_I)`.** Reproducer at compliant size (experiment X6, `logs/experiments/x6-*.json`): de Bruijn
B(100,3), 1,000,000 bytes; `ea_non_iid` marks `LRS Test` `literalEstimateNotRun: true`; the restart JSON's `LRS Test`
case has `h_c` and **no `h_r` and no flag**; `Overall` has `h_r 6.583`, `h_c 6.373`, `h_i 0.5` and the awarded
0.5 appears only in text (suppressed by `-q`). Spec: §3.1.4.2 (PDF p. 21) — the validation minimum is over the
estimates "computed"; the standard is silent on omission, the fork's own F05 repair made omission visible in
`ea_non_iid` and not here. Direction: the row/column minimum is over fewer estimators (permissive for the
validation gate; the awarded figure is still ≤ `H_I`). Prior-fix interaction: R-2, F05, NOVEL-03. Fix offered:
`fix/restart-notrun-flags`.

**AA-05 — the Makefile's OpenSSL pin is defeated by include/link order; the production binaries link
`libcrypto.4`.** `cpp/Makefile` (Darwin block) puts `-I$(BREW_PREFIX)/include` / `-L$(BREW_PREFIX)/lib` BEFORE the
pinned `openssl@3` paths. Measured: `otool -L cpp/ea_non_iid` → `/opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib`
for all three tools, after `brew install afl++` (for this audit, 2026-11-07 19:24–19:28) pulled in `openssl@4`
4.1.0 and repointed `/opt/homebrew/lib/libcrypto.dylib` at 19:28 — the minute the binaries were rebuilt. This is
the measured cause of the sha256 change from the suite-blessed binaries (`b61cf8c7…` → `1ad1568c…`); builds are
otherwise byte-reproducible at a fixed output path (same path twice → identical; a different path changes only
the UUID/ad-hoc-signature bytes). libcrypto is used only for the report's input SHA-256
(`TestRunUtils.h:658-721`); no entropy figure depends on it, and the self-test on the relinked binaries matches
every reference figure. Direction: nondeterminism of provenance across machines. **Disclosure: this audit changed
the build environment of this machine by installing AFL++ and, through it, OpenSSL 4.** Fix offered:
`fix/openssl-pin-order`.

**AA-06 — `ea_restart -s` is documented "accepted for compatibility and ignored" but refuses every value below
5,000,000 with a bare usage dump.** PROVISIONAL (`repro/PROV-07`; `restart_main.cpp:449-459`). Wrong refusal.

**AA-07 — t-Tuple/LRS (`SAalgs32`) runtime grows pathologically on highly periodic 8-bit data.** OBSERVED, scaling
measurement pending (CHAIN-5): `lfsr16-tap8-8bit` at 999,999 samples ran 28+ minutes at 100 % CPU in `SAalgs32`
(`logs/experiments/sample-lfsr16-tap8-8bit-999999.txt`) where the 50,000-sample prefix completes in under a second;
the longest repeated substring on period-65,535 data is nearly the whole bitstring. Availability only; not reachable
by a physical source's data. LOW/MEDIUM pending the measurement.

### 1.2 LOW (reporting, CLI, hygiene) — PROVISIONAL, from `repro/PROV-*`

PROV-03 JSON `mcvEstimate*` carry only the Literal triple · PROV-04 the "narrower than described" warning never
reaches the JSON and leaks under `-q` · PROV-05 `-vvv` prints no per-estimator lines (estimators print at
`verbose == 3` exactly) · PROV-06 repeated `-o` leaves a permanent placeholder at the first path · PROV-08
`ea_restart -q` still prints `H_I` · PROV-09 IID-suite failure report lacks `errorClass` · PROV-11 `type` is the
empty string in completed reports · PROV-12 lossy UTF-8 transcoding of `filename`/`commandline` · PROV-13 non-binary
chi-square independence with `df ≤ 0` reported PASSED (short inputs only) · PROV-14 Makefile probes use the fixed
path `/tmp/.ea_fs_$.c` · PROV-16 zero estimates print as `-0` / `-0.0` · PROV-17 OC-104 refusal fires after `--`
with a false reason · PROV-19 `reportComplete` written only by the placeholder · PROV-20 contradictory mode flags
resolved silently by the last · PROV-21 `--version -Z` exits 0 · PROV-22 `xoshiro_jump(k)` is not k canonical jumps
(threads ≥ 2 start at a J-linear image of the seed; model-level) · PROV-23 partial permutation counters with no
field for the number evaluated · PROV-24 `ea_iid` aborts on `assert(n>=p)` for 3..31 samples under the escape ·
PROV-25 `utils.h` comment claims an INT_MAX refusal `non_iid_main.cpp` does not have · the three Lag ring-buffer
`uint8_t` truncations UBSan's implicit-conversion group flags (benign modular index arithmetic, `lag_test.h:86/108/111`).

### 1.3 Excluded scope (unsupported executable, recorded not filed)

PROV-18 `ea_conditioning` folds `collision_test()`'s `-1` "declined" sentinel into `h'` (`h' = -1`, `h_out = -8`,
exit 0). Not built or shipped by this fork; the tracker's `EXCLUDED-UNSUPPORTED` rows apply.

### 1.4 Where the standard's own algorithm overstates — the headline, filed as a LIMITATION

See **L-01** in §2: on a compliant 8-bit capture with one stuck (constant) bit line and bit-level structure the
symbol-level estimators cannot see, the tool — following §3.1.3 literally — reported **2.569 bits/sample against a
true conditional min-entropy of 1.064 (2.42×)**, while the same bits assessed at their real width gave 1.063.
**The C++ computes the standard's figure exactly**: the spec-only Lag reference (the binding bitstring estimator)
reproduces the tool on both files to the last printed digit of every intermediate — `C = 6400390, r = 81,
N = 7999999, P_global = 0.80004885000610626`, min-entropy `0.321183283` vs the tool's `0.321183326` (the 4e-8 residue
is the documented D-1 quantile) — and on the unpadded 7-bit file `C = 6298781, r = 161, 0.1518135` both ways
(`logs/experiments/x2b-ref-lag-*.json` vs `x2b-chain-lag20-*-inferred.stdout`). So this is not a code defect and
cannot be repaired in the code without departing from the text; it is the limitation an 8-bit consumer must
defend against operationally (L-01).

---

## 2. Limitations (the standard's own design, code follows the text)

Full entries, with the standard's text, the code site, the construction, the record paths and the mitigation, are in
`LIMITATIONS-DRAFT.md` (L-01…L-17), written from the analysis logs and revised here where this audit measured at
compliant size.

**L-01 — a stuck (constant) non-leading bit line inflates `n × H_bitstring`, and at compliant size the inflated term
can be the assessed figure, 2.42× the truth.** §3.1.3 (PDF p. 20): *"L samples (each having n bits) is considered as a
bitstring of size nL … the entropy per sample is estimated to be n × H_bitstring"*; §6.4's bit ranking is the
submitter's optional step for n above the tool's width and is not implemented. Experiment X2 (1,000,000 samples,
`harness/experiments/x2_stuck_lsb_chain.py`, truth derived in `x2-truth.json`): seven real bits forming a bit-level
Markov chain with `P(r_t = r_{t−20}) = 0.9` — true conditional min-entropy `−log2(0.9^7) = 1.0640` bits/sample —
stored with a constant bit 0 as 8-bit samples.

| run | n | H_original | n × H_bitstring | **Assessed** | vs truth 1.0640 |
|---|---|---|---|---|---|
| the 7 real bits, 7 per byte, width inferred 7 | 7 | 3.2278 | 1.0627 | **1.0627** | −0.0013 (≤ truth) |
| the same bits + constant LSB 0, width 8 | 8 | 3.2278 | 2.5695 | **2.5695** | **+1.5054 (2.42×)** |
| the 7-bit file DECLARED 8 (pad first) | 8 | 3.2278 | 2.5695 | **2.5695** | **+1.5054** |

Mechanism (derived in `harness/experiments/PLAN.md` X2 and confirmed by the Lag intermediates): the pad bit sits
between the real bits, so the real lag-20 dependence lands at bitstring lags 22/23; the Lag predictor is right on
6/8 of positions at 0.9 and guesses the pad and one bit at 0.5 → P ≈ 0.80 → 0.321 bit/bit × 8 = 2.57, while the
16-bit-context predictors (MultiMMC, LZ78Y) learn only the pad phase; at width 7 the lag is intact and Lag gives
0.152 × 7 = 1.063. `H_original` (3.23) cannot bind because the dependence is between shifted bit positions of
samples t−3 and t−2 — no symbol repeats, no tuple repeats, the depth-3 context space exceeds the dictionary cap.
The lag-1 variant (A) is bound by `H_original` at 1.0616 ≤ truth: the limitation needs structure the symbol-level
battery misses.

Why a limitation: the C++ is the text (§1.4). Target profile: an Infinite Noise unit at 8 bits with one stuck line is
a plausible degraded-device state, and the direction is toward overstatement. **Mitigation that touches no
numerics: assess at the real width.** Measure the eight per-position bit proportions of the capture before
assessment; a constant or near-constant line means the capture is refused or the line is stripped and the data
re-packed at the narrower width. **"Always declare 8" is the wrong rule here** (declared-8 on the 7-bit file gives
2.5695; inferred 7 gives 1.0627); "always declare the width" is right only when every line is live. At width 1 the
mechanism does not exist.

**L-02 — F02, width inference** (+38.5 % at compliant size, §3): both figures below the truth in every measured case;
the operational rule is the one above, not "declare 8".

**L-03…L-17** — as drafted: observed-alphabet "binary" (L-03); Collision step 8's 1-bit fallback on anti-correlated
data (L-04); Compression step 8's 1-bit fallback incl. a stuck-then-live capture (L-05); the Markov six-path table,
+0.0037 bit/bit measured (L-06); Compression's printed outer-sum limit `L` vs the worked example's `⌊L/b⌋` and the
σ̂ radicand (L-07); errata in the standard's worked examples (L-08); the `-c` byte count (L-09 — **moved to AA-01**,
because the text is not ambiguous and no decision covers it); C23 (L-10); the standard cannot see a DRBG — the
record's AES-CTR zero-key stream at 7.145 of 8 bits, `OC-109` (L-11); MultiMMC's cap and the margin being a
measurement (L-12 — **re-measured ±0.08 bit at width 8, §3**); omitted estimators and the minimum over fewer (L-13);
single-estimator blind spots (L-14); `-t` truncation (L-15); implementer-chosen numerics (L-16); the nondeterministic
permutation verdict (L-17).

---

## 3. Documented divergences re-measured

The fork knowingly departs from the text in the places below; this audit treats them as decisions, not bugs,
and reports only where the measured magnitude differs from the recorded one.

| divergence | where decided | recorded magnitude | this audit's measurement |
|---|---|---|---|
| **D-1 / C22c** — the exact binary64 0.995 quantile `2.5758293035489008` where the text prints `2.576` (MCV, t-Tuple, LRS, Collision, Compression, the four predictors' `P_global'`) | FORK-DIVERGENCE §B, §D | permissive, bounded by the floor's C22c term (3.36e-3 bit at n = 1e6) | 94 of 94 `CPP_HIGHER` records at 50,000 samples vanish when the reference is re-run with the exact constant (`logs/diff/SUMMARY.md`); at 5,000 samples the excess is 1e-6–4e-5 bit/symbol, shrinking as 1/√N. Consistent with the record. |
| **F02** — with the width omitted, `n` is inferred from the highest set bit (upstream #254 position; the fork repaired by REPORTING `bitsPerSymbolInferred`) | tracker F02, NOTICE | "up to 2.4×", +21.9 % at 20,000 | **+38.5 % at 1,000,000** (experiment X1: MSB-dead uniform 7-bit data, inferred `6.2727` vs declared-8 `4.5300`; both below the 7-bit truth; LSB-dead control identical either way, `4.5402`). Direction permissive relative to the declared-width computation; it reaches the TRUE figure in no measured case. See L-02 and the stuck-bit note under L-01 for why "always declare 8" is not the right mitigation. |
| **C01 / F10** — MultiMMC's chained prefix lookup (`multi_mmc_test.h:236`, `:267-274`) vs §6.3.9 step 4.b.i's independent per-depth lookup; **NOT REPAIRED** | FORK-DIVERGENCE §A.1 | one executed overestimate (`f10_over_8bit_1M`); margin 3.69e-4 bit at width 1 | **±0.08 bit at width 8, 1,000,000 samples**, on crafted compliant files (experiment X3): naive construction tool `1.1479` vs spec-literal reference `1.2406` (tool LOWER, ΔC = −28,087); gadget tool `0.9783` vs `0.9005` (tool **HIGHER** by 0.078 bit, ΔC = +28,121). Two independent models (text-as-written ≡ reference; C++-transcribed ≡ tool) agree the cause is the chained lookup with the 100,000-entry cap bound. The assessed figure did not move on these files (other estimators gave 0), so this is the estimator's margin, not a final-figure overstatement here; the prior record holds the one executed final-figure case. **The recorded margin is a width-1 number and does not bound width 8.** Fix offered for the owner's decision: `fix/multimmc-independent-lookup`. |
| **D-2** — Collision adjusted mean clamped to 2 instead of the text's 1-bit fallback | FORK-DIVERGENCE §D | conservative | code matches the decision; reproduced (`logs/analysis/collision.md`). |
| **D-3** — Markov six-path table (the standard's) | §D | — | +0.0037 bit/bit measured vs the fitted model's true max path, ceiling log2(φ)/128 = 0.0054 (L-06). |
| **C23** — restart sanity check decides on the exact multinomial maximum, not step 5's printed formula | §B | printed cutoff rejects correctly-operating 8-bit sources 82.5–83.2 % of the time | not re-measured; the two quoted false-reject rates differ (PROV/S10 doc note). |
| **OC-104** — an option after the file operand is refused | §A.3 | — | the refusal also fires after an explicit `--`, with a wrong reason (PROV-17, LOW). |
| the ≥ 1,000,000 intake, D-5 (no IID estimate after an IID failure), D-6 (out-of-width values refused) | tracker / §D | — | refusals exact at the boundary (X7: 20 cases, both tools, both widths, `-l` variants; `ea_restart` refuses 999,999 and 1,000,001); out-of-width files refused (18 `TOOL_REFUSED` records). |

---

## 4. What was tested and found clean

Each item says what was covered and what it cannot see (rule 18).

**4.1 Estimator arithmetic vs the standard — clean up to the documented quantile.** 156 differential records at
50,000 samples (26 families × widths 1, 8 × literal/bitstring/assessed; `logs/diff/SUMMARY.md`): 17 AGREE, 94
`CPP_HIGHER` **all** of which vanish when the reference uses the exact 0.995 quantile (D-1), 27 NOT_RUN (binary
sources have no bitstring term, by the text), 18 TOOL_REFUSED (single-symbol files refused with "1 symbol";
out-of-width files refused per D-6), **0 CPP_LOWER, 0 INTERMEDIATE_DIFF** — every printed intermediate (counts,
proportions, bounds, run lengths, tuple lengths) of all ten estimators matched the spec-only Python on every case
to 1e-9 or exactly. At 1,000,000 samples the Lag estimator was additionally matched exactly on the X2 files
(§1.4). Cannot see: intermediates the C++ does not print; the 1,000,000-sample reference for the other nine
estimators (pure Python, hours per module — run only where named); the 22-record partial 999,999 sweep.

**4.2 The final answer.** On every differential and experiment record the assessed figure equals the minimum of
the printed estimates (`fold-consistency OK` on all X4 runs; the driver's `assessed` pseudo-case AGREEs or is
D-1-explained). No NaN or ±inf was produced at compliant size on the degenerate inputs tried (strictly alternating
bits at widths 1 and 8, a two-symbol 8-bit alphabet, one symbol appearing once among 10⁶, a counter mod 256);
zero estimates print as IEEE `-0` (PROV-16, cosmetic); no not-run flag was set where it should not be. Cannot
see: a NaN producer that none of these inputs reached (the F13 mechanism — `std::min` folds in `main` are not
NaN-safe — remains a reasoned suspicion with no producer found at compliant size).

**4.3 Intake and refusals.** Exactly 1,000,000 is the boundary for both tools at both widths and for `-l` subsets
that load fewer (X7: 20 runs; exit 255, `errorLevel −1`, class `input`); `ea_restart` refuses 999,999 and 1,000,001;
`EA_ALLOW_SHORT_DATASET` does not relax the restart requirement. Out-of-width symbols are refused rather than masked.
Cannot see: the `-c` byte-vs-output count (AA-01 — not clean).

**4.4 Build reproducibility.** The same source built twice to the same path is byte-identical; a different output
path changes only the Mach-O UUID and ad-hoc signature. The pre-audit hash change was the OpenSSL relink (AA-05),
not non-determinism.

**4.5 Memory safety (ASan + UBSan), threading (TSan), fuzzing (AFL++), determinism across thread counts** —
_(filled in when the stages complete; interim: 60+ ASan/UBSan runs over the self-test corpus and the 50,000-sample
corpus show no AddressSanitizer report and no UBSan report other than the three benign `uint8_t` ring-buffer
truncations in `lag_test.h`.)_

---

## 5. Method, instruments, and their known blind spots

**Independence.** `reference/py90b/` (15 modules) was written from the standard's text by agents forbidden to open
any file under `cpp/` or the analysis notes; the only thing taken from the C++ is the NAMES of the printed
intermediates (`reference/cpp-verbose-labels-*.txt`) so the driver can match them. Every module carries the
standard's own worked examples as unit tests (all pass; the two Compression "failures" are deliberate variant
readings that document where the printed formula and the worked example disagree — L-07). The one shared piece
is `predictor_common.py` (the `P_global'`/`P_local` finish), imported by the four prediction modules.

**Differential.** `harness/gen_corpus.py` writes a deterministic corpus (SHA-256 counter mode under a fixed key; no
library RNG; sha256 per file in `corpus/MANIFEST.txt`): 26 families × widths 1 and 8 × sizes 1,000,000 /
999,999 / 50,000. `harness/diff_driver.py` runs the production `ea_non_iid -i -a -vv -o`, parses by LABEL (never
position), records the binary's sha256, runs every reference module, compares every shared key (abs 1e-9;
integer counts exact), classifies `AGREE / CPP_HIGHER / CPP_LOWER / INTERMEDIATE_DIFF / NOT_RUN /
TOOL_REFUSED`, and re-runs any D-1-shaped disagreement with the exact quantile before tagging it explained.
`--self-check` mutates a passing comparison fourteen ways and asserts each is reported (rule 7). Blind spots
(rule 18): it compares only what the C++ prints; a "binary" source has no bitstring term, so 27 cases are
NOT_RUN by construction; the Lag/LZ78Y/MultiMMC references at 8 million bits are pure Python and were not run
at compliant size except where named; the 999,999-sample sweep was accidental and partial (22 records).

**Experiments** (`harness/experiments/`): deterministic 1,000,000-sample generators with manifests, every run
through `run_one.sh` (stdout/stderr/rc/meta with binary and input sha256), decisions by labelled reads. The X3
construction was validated against the reference and two behavioural models BEFORE the heavy run, and the
analysis phase's prediction for it (+14 correct per period) was refuted by those models — recorded as such.

**Sanitizers** (`harness/sanitizers/`): out-of-tree ASan+UBSan (`-fsanitize=address,undefined,float-divide-by-zero,
implicit-conversion,nullability`, `-O1 -g`) and TSan builds of the three tools, sha256-recorded; the
`implicit-conversion` group fires on three deliberate `uint8_t` ring-buffer wraps in `lag_test.h` on every input,
so the harness runs a `halt_on_error=0` continue pass whenever the halt pass stops there; ASan still aborts in that
pass, so memory errors are not masked. LeakSanitizer is unavailable on this ASan runtime (probed). TSan on Homebrew
libomp (not TSan-instrumented, no OMPT) cannot see libomp's own synchronisation, so a `SAME_CRITICAL` report is a
platform artefact; the summariser classifies each report against the source's critical-section line ranges.

**Fuzzing** (`harness/fuzz/`): AFL++ 5.03c (`afl-clang-fast++`, which wraps Homebrew clang, not Apple clang), plain
and ASan variants, 216 seeds, eight targets, every run under `EA_ALLOW_SHORT_DATASET=1` (without it every input is
refused at the 1,000,000 gate and nothing is exercised); crashes are triaged under the ASan build and re-tiled to
1,000,000 bytes to check reachability without the escape. libFuzzer is not shipped with Apple clang 21.

**Determinism** (`harness/determinism/`): thread counts 1/2/10 and repeated runs, byte-compared after dropping
timestamps; `EA_TEST_RANDOM_SOURCE` does NOT seed the permutation tests (`utils.h` `seed()` opens `/dev/urandom` by a
literal string — it only names the report's temp file), so `ea_iid` has no reproducibility hook and its arm is
reported as such; the Linux side is the refdata the strict CI suite matches to `compareresults.pl`'s 1e-10, against
the eight known macOS deltas.

**Accidents of this audit, recorded because they cost evidence.** (i) `brew install afl++` pulled in OpenSSL 4
and relinked the production binaries (AA-05) — an environment change on the host, disclosed. (ii) The first
differential records embedded the LRS reference's per-W tables (up to 89 MB each, a 2 GB commit); the driver now
elides any table over 512 entries to a count/digest/range and the unpushed commit was rewritten
(`harness/compact_records.py`). (iii) zsh does not word-split an unquoted variable, so a two-option variable
reached argparse as one argument and a run died; (iv) a `pkill -f` pattern matched the orchestrator's own chain
shell and killed the sweep it was waiting on; (v) the 999,999-sample "refusal pass" was a full assessment pass
because the driver sets the escape for n < 1,000,000 — it is reported as the partial sweep it was.
