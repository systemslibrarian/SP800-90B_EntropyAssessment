# Area report: noniid-estimators (ea_non_iid predictors, binary vs generic paths, dictionary limits)

Source audited: upstream 87c104d (SCR/audit/rel/cpp, g++ 13.3 -O2 -ffloat-store -march=native -fopenmp).
Work dir: SCR/audit/work/noniid/ (all generators, harnesses, logs; nothing outside it was written except this report).
SP 800-90B text was not available in the workspace; the spec pseudocode of §6.3.7–§6.3.10 was reconstructed from knowledge of the final (Jan 2018) text. Where a detail could not be re-read (the MultiMMC / LZ78Y count-tie rule) it is flagged as such.

**Bottom line: 0 confirmed novel findings.** Three prior local rows are now verified (F09, F10, F14), one is mechanism-verified but is a maintainer position (F20). Only F14 is in the dangerous direction, and only above 2^32 compression blocks (> 25.77 Gbit bitstring). F09 is conservative. F10 goes either way in a scaled model; at the shipped constants it changes sub-predictions and scoreboards but I could not make it change C or r.

---

## 1. Scope actually covered

Files and functions read line by line: `non_iid/multi_mcw_test.h` (multi_mcw_test), `non_iid/lag_test.h` (lag_test), `non_iid/multi_mmc_test.h` (binaryMultiMMCPredictionEstimate, multi_mmc_test), `non_iid/lz78y_test.h` (binaryLZ78YPredictionEstimate, LZ78Y_test), `non_iid/compression_test.h` (G, com_exp, compression_test), `shared/utils.h` (read_file_subset translation and bitstring, PostfixDictionary, BINARYDICTLOC, predictionEstimate, prediction_estimate_function, calc_p_local), `non_iid_main.cpp` (estimator dispatch, `-t`/`-c` handling). Not re-done because AUDIT-2026-09-30 already verified them: collision, Markov, MCV, t-tuple and LRS worked examples, and the compression G() algebra.

Independent references written for this audit:
- `ref90b.py`: a literal Python version of §6.3.7–§6.3.10 plus steps 5–7 of the predictor estimate (P_global′, P_local with the spec's x = x₁₀ in mpmath at 60 digits). It keeps the spec's structure: a separate "update dictionary" phase and "predict" phase, independent lookups per order, a `correct[]` array, and r computed from that array afterwards. MultiMCW recomputes the argmax with the most-recent tie rule at every step.
- `h/ref90b.cpp`: a C++ port of the same structure, cross-checked equal to the Python version, for large inputs. It adds diagnostics (orphan-context visits, final scoreboards) and an emulation mode that switches the tool's two MultiMMC semantics on one at a time: "chain" is F10, "noreset" is F09. The emulation is used only to attribute differences to a cause.
- `h/harness.cpp`: calls the **unmodified** upstream estimator headers on one file. It reproduces the full tool's C, r, N and entropy exactly and avoids running LRS on repetitive inputs, which is slow (F17).

### Conformance table

| Section | Algorithm/Test | Step | Code location | Matches? | Notes |
|---|---|---|---|---|---|
| 6.3.7 | MultiMCW | windows 63/255/1023/4095, N = L−63 | multi_mcw_test.h:9,21 | yes | L<4096 skip is known (#258) |
| 6.3.7 | MultiMCW | 3a: most frequent in window, tie → most recent | :34-44 (init), :63-84 (slide + rescan with win_poses) | yes | differential on tie-heavy inputs (tie_rot3/alt012/blocks/pairs, drift) |
| 6.3.7 | MultiMCW | 3d: scoreboard j ascending, `>= scoreboard_winner` | :56-60 | yes | |
| 6.3.8 | Lag | D=128, N=L−1, lag_d = s_{i−d} if d<i | lag_test.h:147-195 (ring buffer) | yes | periods 127/128/129/255/256 checked |
| 6.3.8 | Lag | scoreboard ascending d, `>=` | :163-185 (offsets visited ascending; highScore tracks scoreboard[winner]) | yes | |
| 6.3.9 | MultiMMC generic | 4a: increment existing (x,y); add new while entries_d < 100,000 | multi_mmc_test.h:231-241 | **no** (only after an absent lower order, F10) | chained-skip branch :235-242 neither increments existing pairs when the dictionary is full nor looks them up; `entries[d]++` is unconditional |
| 6.3.9 | MultiMMC generic | 4b: every order predicts independently | :199-210 | **no** (F10) | lookup only if the previous order was found |
| 6.3.9 | MultiMMC generic | 4c/4d: prediction = subpredict_winner; Null ⇒ correct=0 | :212-228 | **no** (F09) | run reset only for a non-Null wrong prediction |
| 6.3.9 | MultiMMC binary | same | :69-119 | chain exact for binary (orders ≤15 cannot fill: 2^(d+1) ≤ 65,536); F09 same pattern at :83-101 | |
| 6.3.9 | MultiMMC | ymax tie | utils.h PostfixDictionary (largest y), binary `>`→1 | consistent across paths | spec tie wording not re-read; see §6 |
| 6.3.10 | LZ78Y generic/binary | B=16, N=L−17, prefixes added B→1 while size<65,536; existing prefixes always incremented (new postfixes allowed) | lz78y_test.h:146-195, :42-105 | yes | dictionary-full semantics match the spec, including new y under an existing prefix |
| 6.3.10 | LZ78Y | `D[prev][y] > maxcount`, longest prefix wins ties | :173-177, :82-86 | yes | |
| 6.3.7 st.5 | all predictors | P_global′; C=0 ⇒ 1−0.01^{1/N} | utils.h:955-968 | yes | checked on C=0 (counter8: MCW, Lag) |
| 6.3.7 st.6 | all predictors | r = longest run + 1; P_local | utils.h:970-972, 842-953 | yes (10-step vs converged x is known F08/#133) | |dH| ≤ 4e-16 vs mpmath x₁₀ on all cases |
| 6.3.4 | compression | D_i = i − last index | compression_test.h:97,116,124-126 | **no above 2^32 blocks** (F14) | `unsigned int dict[]` |
| 3.1.3 / 3.1.5.2 | `-t` | truncation of the bitstring | non_iid_main.cpp:242 | maintainer position | F20 (§5) |

## 2. Tests actually run (commands in SCR/audit/work/noniid)

| Test | Command / script | Outcome |
|---|---|---|
| Literal Python reference vs tool (harness), literal and bitstring paths, 4 predictors | `battery.py --bits` (33 generated inputs: iid k=3,4,5,7,16,64,256 with scattered raw values; Markov k=3,5,8; periodic P=3,17,64,127,128,129,255,256 + 5% noise; four tie-heavy constructions; runs; counter8; gray8; counter mod 5; drift5; w2..w7) + `cmp.py data/r8_5k.bin 2` | 26 inputs completed (C, r, N identical on every estimator and both paths). The job reached its 50-minute background limit before drift5 and w2..w7; those widths are covered by the C++ run below |
| Widths 2..8, literal + bitstring, C++ reference vs harness | `widths.sh` (40k samples per width; bitstring up to 320k bits) | 56/56 identical |
| Dictionary-full regime, literal | `cmpc.py data/rand8_300k.bin 8 lit mmc,lz` | identical; MultiMMC entries 100,000 on orders 2..16, LZ78Y 65,536 |
| 1,000,000-sample 8-bit, literal + 8M-bit bitstring | `cmpc.py …/truerand_8bit.bin 8 lit`, `… bit` | 8/8 identical (bitstring MMC order 16 at 100,000; LZ78Y at 65,536) |
| MultiMMC on NIST 1M datasets (truerand_8bit, biased-random-bytes, normal, data.pi, ringOsc-nist, truerand_4bit) | `ref90b <f> 0 lit mmc` vs harness | 6/6 identical; orphan-context visits = 0 and winner-Null-after-correct = 0 on every file |
| Binary vs generic implementation of the same estimator (X on {0,1} goes binary; X+[2] forces generic) | `binv.py` (rand 1M bits, bias 0.8, sticky Markov, period-97+2% noise, 16-bit LFSR, tie-heavy, fill-then-periodic) | 28/28 identical C and r, generic N = binary N+1 as expected |
| Determinism, OMP_NUM_THREADS 1/2/4, repeats | `ea_non_iid -vv truerand_8bit.bin 8` ×7 | byte-identical stdout (md5 640bc3a9…). No OpenMP pragma or RNG on the ea_non_iid path (grep) |
| Metamorphic bijections, literal path | `meta.py 50000` (full-256 alphabet, k=5 Markov, k=3 tie-heavy; 1 order-preserving control + 5 arbitrary injective relabellings each) | control identical; MCV, t-tuple, LRS, MultiMCW and Lag invariant under every relabelling; MultiMMC and LZ78Y change (count-tie rule is "largest value"); H_original moved by up to 0.0046 bit (full256). See §6 |
| Scaled-model search (MAX_ENTRIES recompiled to 12/30/60/150 in a copy) | `search_mmc.py 3000 5000` + `400 1000` | emulation(chain+noreset) == tool in 3400/3400. F09 changes r in 149/3000 (tool higher in 129). F10 changes C in 78/3000 (tool lower in 12) and r lower in 20. Tool entropy **higher** than spec in 17/3000, max +0.71 bit (c6611, L=1093) |
| F09 at shipped constants, full tool twice | `f09gen.py 3 300 data/f09b.bin; ea_non_iid -vv data/f09b.bin 8` | §3a (F09 verified) |
| F10 at shipped constants, instrumented copy (one fprintf) | `orphgen2.py 5 99985 2000 data/orph3.bin`; `instr/harness_instr` vs `ref90b` | §3a (F10 verified) |
| F14 above 2^32 blocks | `h/f14 1000000000` (unmodified compression_test on a 31.8 Gbit virtual bitstring: a memfd pattern mapped repeatedly) | §3a (F14 verified) |
| F20 | `ea_non_iid -vv -c -t / -c -a / -i -t data/f20.bin 8` | §5 |

## 3. CONFIRMED NOVEL findings

None. Every deviation I could reproduce is either a prior local F-row (§3a) or a known or maintainer-position item (§5).

### 3a. Prior local audit rows now verified (not novel; listed in AUDIT-2026-09-30.md as UNVERIFIED)

### F09 — generic and binary MultiMMC: a Null prediction by the winner does not reset the run of correct predictions (r over-counted)
Category A, Confidence HIGH (mechanism and a full-tool reproduction at the shipped constants), ea_non_iid. Locations: `non_iid/multi_mmc_test.h:multi_mmc_test:212-228` (the reset `run_len = 0` at :227 sits inside `if(found_x)`); the binary path has the same pattern at `:83-101` (the reset is at :100). SP 800-90B §6.3.9 steps 4c–4d and step 7: prediction = subpredict_winner; if it is Null, correct_{i−2} stays 0, so the run is broken. Valid ≥1,000,000-sample case: the mechanism does not depend on L, but the triggering context is specific (see Impact). My reproduction is 114,146 samples. **DIRECTION: TOO LOW** (r only ever increases); the overall figure was unchanged on every input I tried.

Root cause. The tool updates `run_len` only when the winner made a non-Null prediction. The spec's `correct[]` array implicitly resets on Null.

When it can matter (derived and then checked empirically). Without the 100,000-entry cap, the winner can be Null at step i only if correct_{i−1} = 0 (a correct prediction at i−1 implies the order-d context at i was added at the earlier occurrence), so the missing reset is invisible. It shows only when the winning order's dictionary is full and its context is a "boundary" context: the continuation of the last pair added before the order filled. Diagnostic `winnerNullAfterCorrect` was 0 on all six NIST 1M files and on random data.

Minimal reproduction (deterministic): `f09gen.py` in the work dir. It writes 100,310 random bytes from {16..255}; then Y, 36 bytes over {1..8} with all bigrams distinct, placed so that the order-2 dictionary (2-symbol contexts) fills at Y offset 24; then 3,000 random bytes; then Y ×300.
```
python3 f09gen.py 3 300 data/f09b.bin      # sha256 1e2ae594015da8b51094790159d9e380b4d12b30e4eb9c708c4cd8dc90b1c534
ea_non_iid -vv data/f09b.bin 8             # run twice
```
Actual (both runs identical):
```
Literal MultiMMC Prediction Estimate: C = 7089
Literal MultiMMC Prediction Estimate: r = 6603
Literal MultiMMC Prediction Estimate: N = 114144
Literal MultiMMC Prediction Estimate: P_local = 0.99853730694489207
Literal MultiMMC Prediction Estimate: min entropy = 0.0021117648255997287
```
Expected (literal §6.3.9, `h/ref90b data/f09b.bin 8 lit mmc emu`): C = 7089, r = 24, so MultiMMC = 0.9319 bit. The emulation with only "noreset" switched on gives r = 6603, exactly the tool's value, which attributes the whole difference to this cause. A 139,346-sample variant (Y ×1000) gives tool r = 22,703 vs spec r = 24 (0.00053 vs 0.9445 bit).

Impact. Only a conservative MultiMMC figure: 0.0021 vs 0.93 on this input. H_original is unchanged here because t-tuple (0.00089) is lower anyway. It needs a full dictionary and data that revisits the ≤1–2 boundary contexts of the winning order, which natural data does not do.

Dedup. all.md grep: "found_x", "run_len", "Null", "null prediction", "scoreboard", "winner", "longest run", "MAX_ENTRIES" → no MultiMMC item. The nearest items are #114 (postfix counting, not a bug) and #118 (harmonization). The exclusion map lists F09 with no upstream item.

Fix direction. Add `else if (d == cur_winner) run_len = 0;` for the Null case, or track `correct` explicitly. Same in the binary path.

Regression test. `data/f09b.bin`: expect r = 24.

### F10 — generic MultiMMC: chained lookup skips deeper orders once a shallower context is absent
Category A, Confidence HIGH for the mechanism and LOW for any effect on C or r at the shipped constants. ea_non_iid, `non_iid/multi_mmc_test.h:multi_mmc_test:199-210` (lookup `if((d == 0) || found_x)`) and `:235-242` (the chained-skip branch: `M[d][x].incrementPostfix(data[i], true); entries[d]++` runs only while not full, increments `entries` even when the pair already existed, and never increments an existing pair once the dictionary is full). SP 800-90B §6.3.9 steps 4a and 4b: every order is updated and consulted independently. Valid ≥1,000,000-sample case: none found. **DIRECTION: either** (scaled model), and none observed at the shipped constants.

Root cause. The comment at :141-145 assumes that a longer context is present only if its shorter suffix is. That assumption fails when a shallower order's dictionary fills before a deeper one: the deeper order then holds "orphan" contexts whose suffix was never added.

Evidence at the shipped constants. On `data/orph3.bin` (`orphgen2.py 5 99985 2000`: a random fill with a crafted 40-byte window at the fill boundary, which the tail repeats 2,000 times), orphan contexts are visited 24,000 times. The spec's final scoreboard for orders 5..16 is 30,000 each. The tool's, from an instrumented copy with one `fprintf` of `scoreboard[]`, is 28,000, 26,000, …, 6,000: order e loses 2,000×(e−4) correct sub-predictions that it never made. C = 34,444 and r = 5 are identical because order 1 wins in both. On all six NIST 1M files, orphan visits = 0.

Scaled model (MAX_ENTRIES recompiled to 12–150 in a copy; tool == emulation in 3400/3400). F10 alone changes C in 78/3000 cases (tool lower in 12) and lowers r in 20. The tool's MultiMMC entropy exceeds the spec's in 17/3000 cases, by up to +0.71 bit (c6611, M=12, L=1093: tool C=61, r=6 vs spec C=63, r=8).

Why this does not carry over to 100,000. Orphans at order e relative to a full order f can only be created in the window after f fills, and that window allows at most (e − f) further additions to order e. That is at most Σ(e−f) ≤ 105 orphan entries per dataset (order 1 of 8-bit data can never fill: 256² < 100,000). They exist only if the deeper orders gained no "surplus" of distinct pairs before the fill, which in practice means near-random data with no repeated 3+-grams. Every construction I built to make an orphan order the winner (orph2/3/4, gadget variants) hit this conservation effect: the order whose orphan coverage ends is the one that becomes the winner. I report this as an unsuccessful search, not a proof.

Dedup. Same greps as F09. No upstream item; #114 and #40 are adjacent.

Fix direction. Look up every order independently (the spec's independent 4b), and in the not-found branch use find() plus increment, counting `entries` only for new pairs.

Regression test. `data/orph3.bin` final scoreboards (instrumented) must equal the spec's.

### F14 — compression estimate: `unsigned int dict[]` wraps above 2^32 blocks
Category A, Confidence HIGH, ea_non_iid (compression, bitstring or 1-bit literal path). `non_iid/compression_test.h:compression_test:97,116,126` (`dict[block] = i+1` stored in `unsigned int` while `i` is `long`); :124-125 compute `i+1-dict[block]` in `long`, so every D_i after the wrap is inflated by 2^32. SP 800-90B §6.3.4 step 3 (D_i = i − index of the last occurrence). Valid ≥1,000,000-sample case: yes in length, but it needs more than 2^32−1 six-bit blocks, i.e. a bitstring of at least 25.77 Gbit (a 3.22 GB file of 8-bit samples). Upstream explicitly supports >2^31-sample inputs since #217/#226 ("commonly relevant … for non-vetted conditioning functions"), but an end-to-end run needs about 25 B/bit for the 64-bit suffix array (~650 GB RAM). **DIRECTION: TOO HIGH.**

Reproduction (unmodified `compression_test`; data is the bit pattern 000001, so every block is identical, every true D_i = 1, and the correct estimate is 0):
```
h/f14ctl 6000000              # control, 10^6 blocks:  X-bar = 0, p = 1, min entropy = -0
h/f14 1000000000              # 2^32 + 10^9 blocks (31.8 Gbit, memfd-backed, ~2 MB physical)
```
Actual (two runs with different post-wrap fractions; 625 s and 584 s wall on the shared 2-core box):
```
len=31769803776 bits, num_blocks=5294967296 (2^32+1000000000)
F14 Compression Estimate: X-bar = 6.0434756732086861
F14 Compression Estimate: X-bar' = 6.0432137830922059
F14 Compression Estimate: Could Not Find p. Proceeding with the lower bound for p.
F14 Compression Estimate: min entropy = 1
len=27569803776 bits, num_blocks=4594967296 (2^32+300000000)
F14 Compression Estimate: X-bar = 2.0892427455796012
F14 Compression Estimate: p = 0.73792769362752775
F14 Compression Estimate: min entropy = 0.073074772530174456
```
Expected: X̄ = 0, p = 1, min-entropy 0, as in the control. The data is one repeated 6-bit block.

Impact. Beyond 2^32 blocks, every later D_i is about 2^32, so X̄ rises by about 32 × (fraction of blocks after the wrap). A deterministic bitstring was reported at 0.073 bit/bit with 6.5% of blocks past the wrap, and at 1.0 (full entropy) with 19%. Whether this raises the overall H_bitstring/h′ depends on compression being the binding estimator. Because it needs more than 25.77 Gbit plus about 650 GB of RAM for the LRS stage, this is a latent defect in the >2 GS range that upstream added in #217/#226. It is not reachable on typical hardware.

Dedup. grep "dict[block]", "unsigned int dict", "2^32", "4294967296" → none. The exclusion map records F14 with no upstream item (adjacent: #217/#226 large-file support, #170/#175 64-bit asserts).

Fix. Declare `long dict[alph_size]`.

Regression test. `h/f14 1000000000` must return about 0.

## 4. Suspected findings needing more work

- **F10 in the dangerous direction at the shipped MAX_ENTRIES.** In the scaled model the chained lookup lowers C in 12/3000 cases and r in 20/3000, and raises the MultiMMC entropy in 17/3000 (up to +0.71 bit). At 100,000 entries I could make orphan contexts recur 24,000 times and change scoreboards (F10 above), but not C or r. The open question is whether a ≥1,000,000-sample input exists in which an orphan-bearing order is the winner at orphan contexts, or in which the scoreboard difference flips the winner at a context where the two candidate orders predict differently. My constructions all failed because of the surplus-conservation effect described under F10. Scripts: `orphgen.py`, `orphgen2.py`, `orphgen3.py`, `trace_mmc.py`, `search_mmc.py`.

## 5. EXCLUDED AS ALREADY KNOWN

| Rediscovery | Maps to |
|---|---|
| F20: `-t` truncates the bitstring under `-c` (verified: data/f20.bin, `-c -t` assesses "Number of Binary Symbols: 1000000", h′ 0.8445; `-c -a` 2,000,000, h′ 0.0772) | local F20; maintainer position (#127/#139/#140, J in #139: under `-c` all data is the bitstring and `-t` truncates the H_bitstring bitstring). §3.1.3's truncation allowance has no §3.1.5.2 counterpart, so this is a spec-reading question, not novel |
| `-c -vv` prints "Assessed min entropy: 6.7557" = 8 × h′ while the default text prints h′ | local F23 (reporting) |
| MultiMCW skipped for L<4096 | #258 |
| x iterated to convergence instead of x₁₀ (entropy |Δ| ≤ 4e-16 in every comparison) | F08 / #133 |
| z = 2.5758293035489008 | F07 / #22 |
| LZ78Y and MultiMCW near-useless on periodic or LFSR binary data (per97noise LZ78Y 52% vs MMC 95%; lfsr16 LZ78Y 49.6%); LZ78Y 7.75 bit on a periodic 8-bit tail after its dictionary filled | F29 / F28 (spec limitation; J #70/#223) |
| Slow LRS on repetitive inputs (reason the harness was used) | F17 / #214 |
| Binary MultiMMC init over-read for tiny L (not re-tested) | #257 |

## 6. No-finding areas (attacked and held)

- **Binary vs generic implementations** (MultiMMC, LZ78Y): identical C and r on 7 inputs up to 10^6 bits, including both dictionaries full and a fill-then-periodic tail. In the binary MultiMMC, the chained lookup is exact, because orders ≤15 can never reach 100,000 entries (2^(d+1) ≤ 65,536). The overwrite `binaryDictEntry[y]=1` at :117 is therefore reachable only for genuinely absent entries.
- **Dictionary-full semantics.** LZ78Y (generic and binary) stops adding prefixes at 65,536, still increments existing prefixes and still adds new postfixes under existing prefixes, as the spec requires (checked on 300k literal, 1M-bit and 8M-bit inputs). MultiMMC (chain intact) stops adding pairs at 100,000 per order, still increments existing pairs and still predicts from them.
- **Bookkeeping:** N per estimator (L−63, L−1, L−2, L−17); r = longest run + 1; scoreboard updated in ascending order with `>=`; the MultiMCW most-recent tie rule; LZ78Y strict `>` with the longest prefix first; C = 0 ⇒ 1−0.01^{1/N} with the 1/k floor (counter8: 8.0 exact); P_local-dominated cases (r up to 8,744). All match the literal reference.
- **Bitstring path, widths 2..8**: MSB-first bits of the masked raw value; 56/56 match.
- **Determinism**: 7 runs across 1/2/4 threads, byte-identical.
- **Metamorphic relabelling.** Non-order-preserving bijections change MultiMMC and LZ78Y, because the count-tie rule is "largest symbol value", applied consistently in binary, generic and PostfixDictionary. The tool's translation is order-preserving, so its own relabelling never changes results. That the non-IID estimators are "categorical or invariant under any translation that preserves order" is a stated maintainer position (all.md line 5992, #147). I could not re-read the §6.3.9/§6.3.10 tie wording. If the spec mandates a label-independent rule, this would become a reporting/conformance question; the magnitude is small (≤0.005 bit on my inputs) and can go either way.
- **Scaled-model caveat**: the 17 TOO-HIGH scaled cases are from a modified MAX_ENTRIES and are evidence about the mechanism only (F10 above).
