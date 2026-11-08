# Analysis — Data intake and sample representation (§3.1.1, §3.1.2, §6.4)

Audit: 2026-11-07 aggressive audit, analysis phase. Branch `audit/2026-11-07`,
source commit `a2c3c81314a76947bf3924a72854a867c5d12fa7`. Nothing was built; no
heavy job was run. Nineteen tiny probes (1 to 20,000 samples) ran with
`EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`; every one is marked non-compliant
by the tool. Driver: `logs/analysis/intake-probe.sh`; outputs
`logs/analysis-intake-*.log`; exit codes `logs/analysis-intake-exitcodes.log`;
corpus digests `logs/analysis-intake-corpus-sha256.log`.

Binaries measured (instrument rule 4), `logs/analysis-intake-binaries-sha256.log`:

| binary | sha256 |
|---|---|
| `cpp/ea_non_iid` | `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` |
| `cpp/ea_iid` | `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349` |

Headline: **no deviation from the standard that overstates min-entropy was found
in the intake path for the target profile** (`ea_non_iid -i`, 1 or 8 bits,
≥ 10^6 samples, Darwin arm64 / Linux x86-64 LP64). Every refusal probed is
fail-closed; the width mask is dead code because the width check precedes it;
symbol translation is a bijection on the observed alphabet; the bitstring is
built from the untranslated bits. The four VLAs the build log flags are all
bounded by the 1..8 bit cap, not by the input length. What was found:

1. a **suspected HIGH memory-safety defect on LLP64 (Windows) only** —
   `blen = len * word_size` in 32-bit `long` wraps for multi-bit inputs of
   ≥ 2^28 samples, and in alternating 256 MiB windows wraps to a *small
   positive* value, so `bsymbols` is under-allocated and the fill loop indexes
   it with a wrapped negative offset (§2.6). Not reproducible on this host;
   it is a concrete instance of the sweep `C18`'s entry says was never done;
2. a **spec-level observation, measured**: a constant *non-leading* bit
   inflates the §3.1.3 `n × H_bitstring` term above the true min-entropy
   (1.345 vs truth 1.064 bits/sample on the probe), while the same data with
   the bit removed gives 0.594; `H_original` (1.031) rescued the final figure
   this time. The tool conforms to the text here; the asymmetry — a constant
   *leading* zero bit is dropped by width inference, any other constant bit
   is kept — is tool behaviour and is only half-recorded in `F02` (§2.4, §4);
3. a **-c compliance gap**: §3.1.1 item 2 counts conditioning component
   *outputs*; the tool counts *bytes*, so for `n_out > 8` the ≥ 1,000,000 gate
   is weaker than the standard's by `n_out/8`. No documented decision covers
   it (§2.5);
4. several LOW items: a false claim in a load-bearing comment
   (`utils.h:1023-1025`), a stdout warning that ignores `-q` and never reaches
   JSON, two near-identical copies of the intake function, a stat/fopen
   TOCTOU, and `-0` printed for a zero estimate under the test escape.

---

## 1. The standard, transcribed

### 1.1 §3.1.1 Data Collection — SP 800-90B §3.1.1 (PDF p. 17, 19)

> "The submitter provides the following inputs for entropy estimation,
> according to the requirements presented in Section 3.2.4." (p. 17)
>
> "1. A sequential dataset of at least 1 000 000 sample values obtained
> directly from the noise source (i.e., raw data) shall be collected for
> validation 2. If the generation of 1 000 000 consecutive samples is not
> possible, the concatenation of several smaller sets of consecutive samples
> (generated using the same noise source) is allowed. Smaller sets shall
> contain at least 1000 samples. The concatenated dataset shall contain at
> least 1 000 000 samples.
> 2. If the entropy source includes a conditioning component that is not
> listed in Section 3.1.5.1.1, a conditioned sequential dataset of at least
> 1 000 000 consecutive conditioning component outputs shall be collected for
> validation. The output of the conditioning component shall be concatenated
> in the order in which it was generated and treated as a binary string for
> testing purposes. …
> 3. For the restart tests (see Section 3.1.4), the entropy source must be
> restarted 1000 times; for each restart, 1000 consecutive samples shall be
> collected directly from the noise source. … This data is stored in a
> 1000×1000 restart matrix M, where M[i][j] represents the jth sample from the
> ith restart." (p. 19)
>
> Footnote 2: "Providing additional data beyond what is required will result
> in more accurate entropy estimates. Lack of sufficient data may result in
> lower entropy estimates due to the necessity of mapping down the output
> values (see Section 6.4). … it is assumed in subsequent text that only the
> required data has been collected." (p. 19)

Properties the implementation must honour:

| item | value |
|---|---|
| minimum count, sequential raw dataset | **≥ 1 000 000 samples** (inclusive: "at least") |
| unit of the count | *sample values* for item 1; *conditioning component outputs* for item 2 |
| concatenation | allowed, pieces ≥ 1000 — **not checkable from a file**, the tool cannot see piece boundaries |
| restart matrix | exactly 1000 × 1000 = 1 000 000 samples |
| conditioned data | treated **as a binary string** |

### 1.2 §3.1.2 Determining the track — SP 800-90B §3.1.2 (PDF p. 19–20)

> "The IID track shall be used only when all of the following conditions are
> satisfied: 1. The submitter makes an IID claim … 2. The sequential dataset
> described in item 1 of Section 3.1.1 is tested using the statistical tests
> described in Section 5 … 3. The row and column datasets described in item 3
> … 4. If a conditioning component that is not listed in Section 3.1.5.1.1 is
> used, the conditioned sequential dataset … is tested … If any of these
> conditions are not met, the estimation process shall follow the non-IID
> track."

Intake consequence: the track is a *procedural* decision, split across three
programs (`ea_iid`, `ea_restart`, and the non-IID tool). There is no numeric
step in §3.1.2 for intake to get wrong; what intake must deliver to §5 is the
dataset "as a binary string" under item 4 (the `-c` view, §2.7).

### 1.3 §3.1.3 — the two sentences that fix the sample representation (PDF p. 20)

> "If the sequential dataset is not binary, an additional entropy estimation
> (per bit), denoted Hbitstring, is estimated. First, the sequential dataset
> that contains L samples (each having n bits) is considered as a bitstring of
> size nL. The bits after the first 1 000 000 bits may be ignored. Then … the
> entropy per sample is estimated to be n×Hbitstring."
>
> "If the alphabet size is greater than 256, it shall be reduced to at most
> 256 symbols (see Section 6.4)."

| item | value |
|---|---|
| `n` | bits per sample — **a property of the source, "each having n bits"**; the text does not say how `n` is learned |
| bitstring length | `nL`; truncation to the first 1 000 000 bits is *permitted* ("may") |
| "binary" | defined by the alphabet (two distinct values), see `F01` withdrawal in NOTICE |
| alphabet cap | 256 ⇒ 8 bits per sample is the ceiling the tool enforces |

### 1.4 §6.4 Reducing the Symbol Space — SP 800-90B §6.4 (PDF p. 66–67)

> "The algorithm given below provides an example of a method for mapping the
> n-bit samples, collected as specified in Section 3.1.1, to m-bit samples,
> where n ≥ m. … Note that after the mapping is performed, the maximum amount
> of entropy possible per n-bit sample is m bits.
> Given a noise source that produces n-bit samples, where n exceeds the
> bit-length that can be handled by the test, the submitter may provide the
> tester with an ordered ranking of the bits in the n-bit samples (see Section
> 3.2.2). The rank of '1' corresponds to the bit assumed to be contributing
> the most entropy …
> 1. Set M = {a1, a2, …, an}. 2. For i = 1 to n: a. Choose an output bit a
> from M such that no other bit in M is assumed to contribute more entropy …
> b. Set the ranking of a to i. c. Remove a from M.
> Given the ranking, n-bit samples are mapped to m-bit samples by simply
> taking the m-bits of greatest rank in order …"
>
> "The submitter is allowed to use an alternative method to reduce symbol
> size." (p. 67)

| item | value |
|---|---|
| when it applies | `n` exceeds what the test can handle (here: `n > 8`) |
| who ranks | the **submitter**; the tool has no input for a ranking |
| what the tool implements | nothing of §6.4 — it refuses `n > 8` and infers `n ≤ 8` from the highest set bit |
| bound direction | after mapping, entropy per sample ≤ m — an **upper** cap, honoured by `h_assessed = word_size` initialiser |

---

## 2. Mapping to the C++

### 2.1 Step → code

| spec step | code | note |
|---|---|---|
| §3.1.1 regular file, readable | `cpp/shared/utils.h:250-266 input_path_is_regular`, `:326`, `:328-339 fopen` | stat + `S_ISREG`; FIFO/char-dev refused before open (fork hardening, #259) |
| file length | `:341-361` `fseek(SEEK_END)`, `ftell` → `long fileLen` | `long`: 64-bit LP64, **32-bit LLP64** (§2.6) |
| `-l index,samples` subset | `:363-405`; overflow guard `:374`, past-end `:385`, `len = min(fileLen - offset, size)` `:404` | upstream #260 repair |
| empty | `:407-416` | refused |
| load | `:418-447` two `malloc(len)` + `fread(len)`; short read refused `:437` | |
| identity | `:449 record_assessed_data_identity(symbols, len)` → SHA-256 of the **raw bytes consumed** | N-07 |
| `n` (bits per sample) inferred | `:458-470`: OR of all bytes, highest set bit → `word_size` | `F02`; see §2.4 |
| `n` declared, data narrower | `:483-485` stdout warning, `errorMsg` set, **errorLevel unchanged** | §2.8 |
| `n` declared, data wider | `:486-496` refuse "Incorrect bit width specification" | `D-6` |
| raw copy | `:499 memcpy(rawsymbols, symbols)` — **unmasked** bytes | used by IID `rawmean` |
| mask to width | `:502-513` `mask = (1<<word_size)-1; symbols[i] &= mask` | **dead**: the width check guarantees fit; `D-6` "rejected rather than masked" is exact |
| dense alphabet | `:515-517` `symbol_map_down_table[i] = alph_size++` | `alph_size` = number of distinct values |
| bitstring of size `nL` | `:520 blen = len * word_size`; `:521` alias when `n == 1`; `:523-538` MSB-first unpack of the **masked, untranslated** symbol | §3.1.3 "considered as a bitstring of size nL" |
| translate symbols | `:542-544` only if `alph_size < maxsymbol + 1` | bijection on the observed alphabet; estimators are label-invariant |
| ≥ 1 000 000 | `:294-317 dataset_meets_minimum` `if (dp->len >= MIN_SIZE)`; `MIN_SIZE 1000000` `:42` | inclusive, correct; counts **loaded** samples (after `-l`) |
| test escape | `:299-306` `EA_ALLOW_SHORT_DATASET == "1"` → `nonCompliantShortDataset = true`, banner | brief rule 5 |
| "first 1 000 000 bits may be ignored" | `non_iid_main.cpp:344`, `iid_main.cpp:343` `if (!all_bits && blen > MIN_SIZE) blen = MIN_SIZE` | `-t`; conformant ("may") |
| alphabet > 256 | `non_iid_main.cpp:271`, `iid_main.cpp:268` `inint < 1 \|\| inint > 8` → refuse; `uint8_t` symbols | `n ≤ 8` enforced, §6.4 never invoked |
| binary ⇒ no bitstring | `non_iid_main.cpp:364,386,…` gate `alph_size > 2 \|\| !initial_entropy` | `F01` withdrawn; conformant |
| restart matrix exactly 10^6 | `restart_main.cpp:694 if (data.len != MIN_SIZE)` | exact, correct |

### 2.2 Argument handling (both mains)

`non_iid_main.cpp:138-297`, `iid_main.cpp:133-294` are structurally identical:

1. `refuseOptionAfterOperand` (`TestRunUtils.h:363-385`) — `OC-104`, documented divergence.
2. `versionOptionRequested` (`:312-324`) — `A04`/`F04` repairs.
3. prescan + `protectInputPath` + `outputTargetIsSafe` (`:230-271`) — `A05`.
4. `getopt` loop; `-l` parsed with `parse_unsigned_decimal` (`utils.h:51-67`): digits only,
   no sign, no base prefix, no suffix, ERANGE refused; `index,samples` both
   required; `samples == 0` refused (`non_iid_main.cpp:214-224`).
5. `argc` after `optind` must be 1 or 2; `argv[0]` is the file, `argv[1]` the
   width, `1..8` inclusive (`:269-285`).
6. `bitsPerSymbolGiven = data.word_size` is saved **before** `read_file_subset`
   so the JSON can say whether the width was inferred (`:289, :312-313`).

Checked and found correct: `-l 010,1` is decimal 10 (regression-subset.sh);
`8x`, `+8`, `0x8` refused (regression-width.sh); probes `bits-0`, `bits-9`
refused with exit 255 (`analysis-intake-bits-0.log`, `-bits-9.log`).

### 2.3 Order of checks, and what each later check can rely on

```
regular? → open → length → [-l arithmetic] → empty? → malloc×2 → fread → hash
  → width (infer | check) → mask (no-op) → alphabet → bitstring → translate
  → return
main: → ≥ 1,000,000 ? → alph_size ≤ 1 ? → [-t] → estimators
```

Consequences verified in source:

- `most_common.h:14 assert(len > 1)` is unreachable from either main: a
  loaded count of 1 has `alph_size == 1` and is refused at
  `non_iid_main.cpp:329` / `iid_main.cpp:329` first (probe `subset-last1`:
  "Loaded 1 samples of 1 distinct 2-bit-wide symbols … Symbol alphabet
  consists of 1 symbol", exit 255).
- `most_common.h:17 counts[data[i]]++` with `long counts[alph_size]` is
  in-bounds for the Literal call because translation guarantees
  `symbols[i] < alph_size` (either translated to dense indices, or
  `alph_size == maxsymbol + 1` so every value ≤ maxsymbol < alph_size).
- The Bitstring calls receive `bsymbols` ∈ {0,1} with `alph_size = 2`.
- The width-0 path exists: an all-zero file with inferred width gives
  `word_size = 0`, `max_symbols = 1`, `blen = 0`, `malloc(0)` (non-NULL on
  Darwin), `alph_size = 1` → refused downstream (probe `allzero-inferred`:
  "Loaded 2000 samples of 1 distinct 0-bit-wide symbols", exit 255). On a
  libc where `malloc(0)` returns NULL the refusal comes one step earlier
  ("failure to initialize memory for bsymbols"). Both fail closed. This is
  the same path `N-03` records for the unsupported `ea_conditioning`, which
  lacks the `alph_size ≤ 1` gate.

### 2.4 Where code and spec disagree — the width `n`

**Spec:** "the sequential dataset that contains L samples (each having n
bits)" — SP 800-90B §3.1.3 (PDF p. 20). `n` is a property of the source.

**Code:** `utils.h:458-470`

```c
for(i = 0; i < dp->len; i++) { datamask = datamask | dp->symbols[i]; }
for(i=8; (i>0) && ((datamask & curbit) == 0); i--) { curbit = curbit >> 1; }
dp->word_size = i;
```

`n` becomes the position of the highest bit set anywhere in the data. This is
`F02` (tracker, `FORK-FIXED` by *reporting* `bitsPerSymbol`/`bitsPerSymbolInferred`;
the inference itself deliberately unchanged on @joshuaehill's reply to #254).
**Documented divergence; not re-reported.** What the record does not say, and
the probes measure:

*Direction relative to the truth.* Dropping constant leading-zero bits cannot
push `n × H_bitstring` above the data's entropy: the remaining bits are the
real bits, and the computation on them is exactly §3.1.3 for an `n`-bit
source. `F02`'s "too HIGH" is relative to the declared-width computation,
not to the truth. Measured on the same 20,000 uniform 7-bit values
(`analysis-intake-lsb0-shifted-7bit.log`, inferred `n = 7`):
`H_bitstring = 0.77087121065528141`, `× 7 = 5.39609847458697`,
`H_original = 6.4858263215592542`, assessed **5.396**; true min-entropy 7.
Padded with a constant low bit (`analysis-intake-lsb0-8bit-inferred.log`,
`n = 8`): `H_bitstring = 0.54861603515464596`, `× 8 = 4.3889282812371677`,
assessed **4.389**. Both under 7; the padded one is further under.

*The asymmetry that is not in the record.* A constant **high** bit is removed
by inference (n shrinks); a constant **low or middle** bit is kept (n stays
8, and the bit enters the bitstring as a perfectly predictable symbol every
8th position). The same physical fault — one stuck line on an 8-bit device —
is treated two ways depending on which line. §6.4 would rank the stuck bit
last and drop it in either case, but §6.4 is submitter-driven and the tool
offers no ranking input; and §3.1.3 read literally says `n = 8` for an 8-bit
device, stuck bit included. So the tool conforms to §3.1.3 *and* the result
can be inflated — by the **standard's** term, not by the code. Measured
(`analysis-intake-skew09-*.log`; construction: 7 independent bits each 1
with probability 0.9, so the true per-sample min-entropy is
`-log2(0.9^7) = 1.064`):

| file | `n` | `H_bitstring` | `n × H_bitstring` | `H_original` | assessed |
|---|---|---|---|---|---|
| 7 real bits, no padding (`skew09-7bit`) | 7 | 0.084891705450500551 | **0.5942419381535039** | 1.0305347188697431 | 0.594 |
| same bits + constant LSB 0 (`skew09-lsb0-8bit`) | 8 | 0.16815618845789834 | **1.3452495076631867** | 1.0305347188697431 | 1.031 |

The constant bit raised the bitstring term 2.26× and **above the true
min-entropy (1.345 > 1.064)**; `H_original` bound the final figure at 1.031
(< 1.064, so this instance does not overstate). The mechanism: padding zeros
*balance* a 1-heavy bit stream, so every marginal statistic (MCV 0.339 vs
0.148, Collision 0.408 vs 0.147, Markov 0.373 vs 0.151, Compression 0.173 vs
0.085) rises by more than the 8/7 factor costs. The final figure overstates
only if `H_original` also overstates — i.e. on data whose structure the
symbol-level estimators miss and the bit-level ones catch, which is the very
case the bitstring term exists for. **Suspicion, not a finding** (§4 gives
the construction). This belongs with the §B-type standard observations
(`C23`, `C22c`), and the inference asymmetry belongs beside `F02`.

### 2.5 Where code and spec disagree — what the ≥ 1,000,000 counts under `-c`

**Spec:** "a conditioned sequential dataset of at least 1 000 000 consecutive
conditioning component outputs" — SP 800-90B §3.1.1 item 2 (PDF p. 19).

**Code:** `utils.h:297 if (dp->len >= MIN_SIZE) return true;` where `len` is
the number of **bytes** loaded, under `-i` and `-c` alike (`non_iid_main.cpp:320`,
`iid_main.cpp:320`). The `-c` path then forms `blen = len × word_size` bits.

For a conditioner with `n_out` bits per output, 1,000,000 outputs are
`125,000 × n_out` bytes; the tool accepts `1,000,000` bytes, i.e. only
`8,000,000 / n_out` outputs. For SHA-256 (`n_out = 256`) that is 31,250
outputs where the standard requires 1,000,000 — the gate is **32× weaker**.
For `n_out ≤ 8` the tool's gate is as strict or stricter. No entry in
`FORK-DIVERGENCE-AND-TRUST.md`, `NOTICE` or the tracker records a decision on
this (grep for "conditioning component outputs", "n_out", "1 000 000
consecutive" over those files: no hit outside `ea_conditioning` usage text).
Direction: less data makes the §6.3 estimators *more* conservative on the
whole (wider confidence terms), so this is a **compliance** gap (MEDIUM: a
non-compliant assessment is accepted as compliant), not an arithmetic one.
Outside the target profile (`-i`). **Suspicion**; owner decision needed on
whether `-c` should take `n_out` or count bits.

### 2.6 Integer widths, overflow, and the LLP64 `blen` suspicion

`data_t` (`utils.h:91-100`): `int word_size, alph_size; uint8_t maxsymbol;
long len, blen`. Every length in intake is `long` or `unsigned long`.

**LP64 (this host, Linux x86-64):** `ftell` returns up to 2^63; `len × 8`
cannot overflow; `malloc(blen)` for an 8-bit file is 8× the file size plus 2×
for `symbols`/`rawsymbols`, so a 1 GiB capture needs ~10 GiB and on this
16 GB machine fails or swaps — on NULL the tool refuses ("failure to
initialize memory for bsymbols", `:523-532`). `-l` arithmetic: `subsetIndex >
ULONG_MAX / subsetSize` (`:374`) is exact; `subsetOffset >= (unsigned long)
fileLen` (`:385`) makes the later `long fseek(…, subsetOffset, …)` and
`fileLen - subsetOffset` (long/unsigned long → unsigned long, positive by the
check) well-defined; `min(fileLen - subsetOffset, subsetSize)` is unsigned
long → long, ≤ fileLen. `fread` returns `size_t` into `long rc` and is
compared to `len`: fine. The non-IID estimators all take `long len`
(`collision_test.h:17`, `compression_test.h:93`, `lag_test.h:31`,
`lz78y_test.h:128`, `markov_test.h:6`, `multi_mcw_test.h:7`,
`multi_mmc_test.h:176`, `most_common.h:7`); `SAalgs` (`lrs_test.h:587-593`)
dispatches to a 64-bit suffix array at `n ≥ SAINDEX_MAX = INT32_MAX`
(`lrs_test.h:8`). `grep 'for *( *int'` over the non-IID estimators finds only
loops over `k` and `d`. The IID path narrows to `int` (`iid_main.cpp:352,
413`; `chi_square_tests(const int)`, `len_LRS_test(const int L)`,
`permutation_tests.h:633 for(int i = 0; i < dp->len; ++i)`, `FYshuffle(…,
const int sample_size)`, `utils.h:882 sum(…, const int)`) and is guarded by
`iid_main.cpp:393 if (testdata.len > INT_MAX)` → refuse. **No LP64 overflow
reachable from a file was found in intake.**

One comment is false. `utils.h:1023-1025`:

> "Callers refuse a sample count above INT_MAX (iid_main.cpp,
> non_iid_main.cpp), so n <= 2^31 - 1 …"

`grep -n INT_MAX cpp/non_iid_main.cpp` matches nothing. The claim is
harmless today only because `n_choose_2` is called solely from
`len_LRS_test` (`lrs_test.h:713`), which is IID-only, and `SAalgs` has its
own 64-bit route. If a future repair made `ea_non_iid` call `n_choose_2`
(or any `int`-length helper) the comment would license it. **LOW,
documentation.**

**LLP64 (Windows MinGW — a platform this fork measures in CI and has repaired
for, `C18`/`C24`):** `long` is 32 bits.

- `ftell` returns `long`: a file ≥ 2 GiB yields −1 → "ftell failed", fail
  closed. So `len < 2^31` always.
- `utils.h:520 dp->blen = dp->len * dp->word_size;` — `long × int` in 32-bit
  signed arithmetic. For `word_size = 8` it overflows at
  `len ≥ 2^28 = 268,435,456` samples (256 MiB), undefined behaviour; in
  practice two's-complement wrap. The wrapped value alternates sign in
  256 MiB bands:

  | `len` (8-bit samples) | file size | `len×8 mod 2^32` as signed | `malloc(blen)` | outcome |
  |---|---|---|---|---|
  | `[2^28, 2^29)` | 256–512 MiB | negative | `(size_t)` huge → NULL | refused (fail-closed) |
  | `[2^29, 2^29+2^28)` | **512–768 MiB** | **0 … 2^31−1, positive and too small** | succeeds, under-sized | fill loop `:534-538` writes `len×8` bytes through `bsymbols[i*8+j]` where `i*8` is itself 32-bit `long` and wraps **negative** for `i ≥ 2^28` → out-of-bounds heap write / crash |
  | `[2^29+2^28, 2^30)` | 768 MiB–1 GiB | negative | NULL | refused |
  | `[2^30, 2^30+2^28)` | 1–1.25 GiB | positive, too small | succeeds | same hazard |

  For `word_size = 1` there is no multiplication hazard (`blen = len`,
  `bsymbols` aliases `symbols`). For widths 3–7 analogous positive windows
  exist below 2 GiB; for width 2 the wrapped value is negative throughout
  `[2^30, 2^31)` so only the refusal arm is reachable.
- Exactly at `len = 2^29`, `blen` wraps to 0: `malloc(0)` is non-NULL on
  Windows, the fill loop then smashes the heap, and if it survived,
  `most_common(bsymbols, 0, …)` would hit `assert(len > 1)`.

This is **not reproducible on this host** (LP64) and a ≥ 512 MiB run is a
heavy job; it is recorded as a **suspicion, HIGH if confirmed** (memory
safety reachable from an input file), Windows-only, exposure low (a
268M-sample multi-bit capture). `FORK-DIVERGENCE-AND-TRUST.md` `C18` "DOES NOT
ESTABLISH … a sweep of the remaining `long` arithmetic on LLP64 has **not**
been done" and `utils.h:1019-1021` ("widening data_t's `long len`/`long
blen` [is] a separate and larger change") are the record this sits under.
How to measure without a Windows machine: the arithmetic is reproducible in
a 20-line C program compiled with `-m32`-equivalent `int32_t` for `long`, the
way `reproducers/c18_llp64_overflow.c` did it for `C18`; the behaviour needs
the Windows CI job with a generated 512 MiB + 8 B file of bytes declared `8`
(expected crash) and the same size of {0,1} bytes declared `1` as the
negative control (expected: an assessment, since `blen = len`).

### 2.7 The `-c` view and the sample representation under §3.1.1 item 2

`iid_main.cpp:378-386` builds `testdata` with `symbols = rawsymbols =
data.bsymbols`, `len = blen`, `alph_size = 2`, `word_size = 1`, `maxsymbol =
1`. Two things checked:

- The comment's claim that both bit values are necessarily present when
  `alph_size ≥ 2` is true: two distinct symbols differ in at least one bit,
  so the bitstring contains both a 0 and a 1.
- Aliasing `symbols` and `rawsymbols` to one buffer does **not** neutralise
  the permutation shuffle: `permutation_tests.h:627-636` copies each into its
  own `new uint8_t[dp->len]` before `FYshuffle(data, rawdata, …)` (`:647`),
  so the two swaps act on two buffers and both are permuted identically, as
  intended. (I checked this because `utils.h:869-879 FYshuffle` swaps both
  arrays with the same index, which would cancel on a single buffer.)

`non_iid_main.cpp` under `-c` runs the bitstring estimators on
`data.bsymbols, data.blen` — the same quantities `-i` uses for
`H_bitstring`. So every `-i -vv` probe log's `H_bitstring` line is also what
`-c` would print as `h'` for that file; §2.4's padding effect applies to `h'`
verbatim.

**The `-c` + inferred-width route to an overstated per-output figure.**
`h'` is per bit of the bitstring the tool built. If the conditioned output
is stored one 8-bit value per byte and the top bit is constant (a conditioner
that emits 7-bit values, or a byte-packing bug), inference gives `n = 7`, the
constant bit is dropped, and `h'` is per bit of the 7 real bits (≈ 1.0 for a
good conditioner). The spec's binary string of 8-bit outputs **includes** the
constant bit ("treated as a binary string"), so the spec's `h'` is lower
(≈ 0.83 by the MCV arithmetic at §2.4). A consumer that multiplies `h'` by
the declared `n_out = 8` then claims 8 bits per output where the data has at
most 7. The JSON does record `bitsPerSymbol: 7, bitsPerSymbolInferred: true`,
so a careful consumer can see it; the tool prints no warning. This is `F02`'s
mechanism on the `-c` path; `F02`'s record names the `ea_conditioning -i`
route but not this one. **Suspicion, LOW–MEDIUM; outside the target profile.**

### 2.8 Reporting of the declared-wider-than-data case

`utils.h:483-485`:

```c
if( i < dp->word_size ) {
    printf("Warning: Symbols appear to be narrower than described.\n");
    testRun->errorMsg = "Warning: Symbols appear to be narrower than described.";
```

Measured (`analysis-intake-4bit-declared8-json.log`, run with `-q`): the line
is printed even under `-q` (the `printf` is unconditional and runs before
`quietMode` matters), and the JSON (`analysis-intake-4bit-declared8.json`)
has `errorLevel: 0`, `bitsPerSymbol: 8`, `bitsPerSymbolInferred: false` and
**no `errorMessage`** — `test_run_base.h:69-72` emits `errorMsg` only when
`errorLevel != 0`. So:

- a labelled-read harness driving `-q` sees an unexpected stdout line;
- the JSON cannot tell a consumer the data was narrower than declared;
- `errorMsg` is left populated with a *warning* at `errorLevel 0`. Every later
  `errorLevel = -1/2` assignment in both mains also sets `errorMsg`, so no
  stale emission was found; it is a hazard for a future path that sets the
  level alone.

Direction is conservative (declared-wide lowers the figure: 4-bit data
assessed 1.8196406830687593 inferred vs 1.5197909534677914 declared `8`,
`analysis-intake-4bit-inferred.log` / `-4bit-declared8-vv.log`). **LOW.** The
documented decision (`test_run_base.h:38-43`, `F02`) covers the *inferred*
warning that was deliberately not added, not this pre-existing one.

### 2.9 Two copies of the intake function

`read_file_subset` (`utils.h:319-547`) and `read_file` (`:549-735`) are the
same code twice; `ea_restart` uses the second (`restart_main.cpp:601`). The
`F04` entry in `FORK-DIVERGENCE-AND-TRUST.md` is the recorded consequence of
exactly this pattern ("the arithmetic was repaired in one of them and left
wrong in the other"). Today the two bodies agree line for line on every
check I compared (regular, open, length, empty, malloc, fread, hash, width,
mask, alphabet, bitstring, translate). **LOW, maintenance hazard**, and a
place for the fuzzing phase to diff behaviour between `ea_restart` and
`ea_non_iid` on identical files.

### 2.10 Smaller items

- `input_path_is_regular` stats the path, then `fopen` reopens it
  (`utils.h:326-328`). Between the two a symlink can be repointed at a FIFO,
  and `fopen` blocks — the hang #259 closed, reopened through a race. N-07's
  hash-of-consumed-bytes still binds the *result* to what was read.
  Hardening only; **LOW**. An `open`+`fstat`+`fdopen` sequence would close it.
- `-l` offset is `index × samples` bytes and the last block may be short; the
  short block is counted by `dataset_meets_minimum` on the loaded count, so a
  short final block below 10^6 is refused (`regression-minsize.sh` check 4;
  probe `subset-straddle`: `-l 1,1500` on 2000 bytes loads 500 — under the
  escape only).
- `EA_ALLOW_SHORT_DATASET` is read from the environment on every run
  (`utils.h:299`). A consumer whose environment inherits it from a test rig
  gets non-compliant figures with exit 0; the only machine-readable mark is
  `nonCompliantShortDataset: true`. The consumer **must** refuse that flag.
- Under the escape, a 2-sample file assesses to `-0` (`analysis-intake-two-samples.log`:
  "Assessed min entropy: -0") — IEEE negative zero from `-log2(1.0)`;
  cosmetic, but a string compare against `0` fails. The same log shows the
  Markov estimate printing `min entropy = 1` on two samples with
  `p-hat_max = 2.9387358770557188e-39`; that is the Markov agent's, and only
  reachable under the escape.
- `maxsymbol` is `uint8_t` and `dp->maxsymbol + 1` promotes to `int`, so the
  translate condition at `:542` cannot wrap at 255.
- `symbol_map_down_table[i] = (uint8_t)dp->alph_size++` stores ≤ 255 into an
  `int` table; fine.

---

## 2b. Every input-dependent allocation and index (for the fuzzing phase)

Sizes are controlled by the file length `L` (after `-l`), the width `n`
(declared 1..8 or inferred 0..8), and the alphabet `k ≤ 2^n`.

| file:line | allocation / index | size expression | bound | controlled by |
|---|---|---|---|---|
| `utils.h:418` | `malloc(symbols)` | `L` bytes | `L < 2^63` LP64; `< 2^31` LLP64 (ftell) | file length / `-l` |
| `utils.h:419` | `malloc(rawsymbols)` | `L` | same | same |
| `utils.h:436` | `fread(symbols, 1, L)` | `L` | exact; short read refused | file |
| `utils.h:503`, `:690` | **VLA** `int symbol_map_down_table[1 << n]` | `4 × 2^n` bytes, **≤ 1 KiB** | `n ≤ 8` (`non_iid_main.cpp:271`, `iid_main.cpp:268`, `restart_main.cpp:506`); `n = 0` → 4 bytes | width |
| `utils.h:512`, `:543` | `symbol_map_down_table[symbols[i]]` | index `< 2^n` | `symbols[i] &= mask` at `:510` | data (masked) |
| `utils.h:523`, `:710` | `malloc(bsymbols)` | `blen = L × n` | **LLP64: wraps for `L × n ≥ 2^31`** (§2.6) | length × width |
| `utils.h:536`, `:724` | `bsymbols[i*n + j]` | index `< L × n` | LLP64: `i*n` wraps negative for `i ≥ 2^31/n` | same |
| `utils.h:923` | `vector<uint8_t> v(L)` (`calc_stats`) | `L` (or `blen` under `-c`) | IID only, `≤ INT_MAX` by `iid_main.cpp:393` | length |
| `most_common.h:9` | **VLA** `long counts[k]` | `8k`, **≤ 2 KiB** | `k ≤ 256` (`uint8_t`, `alph_size`) | alphabet |
| `most_common.h:17` | `counts[data[i]]` | `< k` | translation (§2.3) | data |
| `multi_mcw_test.h:13` | **VLA** `long win_cnts[4][k], win_poses[4][k]` | `2 × 4 × 8k`, **≤ 16 KiB** | `k ≤ 256` | alphabet |
| `multi_mcw_test.h:37` | `win_cnts[j][data[i]]` | `< k` | translation | data |
| `compression_test.h:104` | **VLA** `int64_t dict[1 << 6]` | **512 bytes, constant** | `b = 6` literal | none (constant) |
| `permutation_tests.h:627-628` | `new uint8_t[L]` ×2 per OpenMP thread | `L` (or `blen`) × threads | `≤ INT_MAX`; `OMP_NUM_THREADS` | length, threads |
| `lrs_test.h:118-119, 165-171` | `vector<saidx_t>` `n+1`, `n+2`, `v+1..v+3` | `4(n+1)` … | 32-bit route `n < INT32_MAX`, else 64-bit | length |

So the four VLAs the build log names (`utils.h:503`, `:690`,
`most_common.h:9`, `compression_test.h:104`; plus `multi_mcw_test.h:13`) are
bounded by the width cap and the byte-wide symbol type, **not** by the input
length — they are a portability wart, not a stack-exhaustion vector. The one
input-length-sized hazard found is the LLP64 `blen` product.

---

## 3. Prior repairs touching intake, and how to try to break each

| repair | where | what it fixed | how to attack it |
|---|---|---|---|
| **≥ 1,000,000 intake** (`c2f1dcd`, `regression-minsize.sh`) | `utils.h:294-317`; mains `:320` | sub-minimum data assessed with errorLevel 0 (`F03`/#255) | (a) `-c` with `n_out > 8` bytes counted, not outputs (§2.5); (b) `-l` block that straddles EOF — counted on the loaded count, OK; (c) `EA_ALLOW_SHORT_DATASET` set to `"1 "`/`"true"` — only exact `"1"` passes, OK; (d) `-t` truncation after the check — permitted by §3.1.3; (e) restart `!= MIN_SIZE` exact — try 1,000,001 bytes (refused). |
| **`-l` arithmetic** (`0e1ffcd`, #260, `regression-subset.sh`) | `utils.h:363-405`, mains' `-l` case | offset wrap, `samples == 0` sentinel, past-end | `-l 4294967296,1` on LLP64 (`strtoul` ERANGE → refused there, accepted on LP64 and then past-end → refused); `-l 0,18446744073709551615` (ULONG_MAX: index 0 passes the guard, `min(fileLen, size)` = whole file; fine); `-l 1,<fileLen-1>` loads 1 sample → `alph_size 1` refusal (probe `subset-last1`); index given, size omitted → parser refuses. |
| **width in JSON** (`97571de`, `F02`, `regression-width.sh`) | `test_run_base.h:44-45,76-79`; mains `:289,:312-313` | inferred width invisible | `bitsPerSymbol` is emitted only when `> 0`: an all-zero file inferred to width 0 would omit it — but that run is refused (`alph_size ≤ 1`) before any success report. Check the *error* report of that run omits it (it does, by `:76`). |
| **width check / D-6** (upstream, kept) | `utils.h:471-497` | wider-than-declared masked silently | one out-of-width byte at any position → whole file refused (probe `4bit-one80-declared4`); the *inferred* case instead widens `n` for everything (probe `4bit-one80-inferred`: 17 symbols, `n = 8`, assessed 1.484 vs 1.820 clean) — conservative, as NOTICE's "single rare third value" note says. |
| **N-08 decimal parsing** (`031d7ee`) | `utils.h:51-67` | base-0 octal, signs, suffixes | `-l 1,1\0x` cannot be typed; `-l ,5` → `input[0]` not a digit → refused; `-l 5,` → second field empty → refused; width `"8\t"` refused; width `"٨"` (Arabic digit) refused (`< '0'`). Leading zeros `"008"` accepted as 8 — by design. |
| **non-regular input** (`cdb5cd6`, #259, `regression-nonregular.sh`) | `utils.h:250-266` | hang on FIFO / char device | stat→fopen TOCTOU with a symlink repointed to a FIFO (§2.10); `/dev/stdin` with a regular file redirected — `stat` follows to the regular file, accepted, correct. |
| **N-07 identity** (`c01fb43`, `regression-input-identity.sh`) | `utils.h:212-248` | hash of pathname, not of consumed bytes | hash is over `symbols` *before* mask/translate = raw bytes of the loaded slice; cannot be broken by width or `-l` — the regression covers the slice. Nothing found. |
| **A05/F03 output aliasing**, **C14 claim**, **OC-104**, **A04/F04** | `TestRunUtils.h`, mains `:138-159` | capture destroyed; stale report; permutation; `--version` bypass | out of this component's spec scope; one intake interaction: `-o` is claimed **before** `read_file_subset`, so a run that fails intake leaves the placeholder — correct. |
| **iid `-c` bitstring view** (`134d377`, N-02/#271) | `iid_main.cpp:378-386` | §5 tests ran on packed symbols | aliasing checked (§2.7): no cancellation. `-c -t` runs the battery on 10^6 bits — permitted. |
| **INT_MAX refusal** (`iid_main.cpp:393-408`) | IID only | `int` wrap in §5 code | the comment at `utils.h:1023-1025` claims the same for `ea_non_iid`; it is absent there (§2.6). |

---

## 4. Edge-case inputs that separate a correct from an incorrect intake

Constructions are exact; all can be generated by `logs/analysis/intake-probe.sh`'s
Python block pattern with a fixed seed. "Correct" means the standard's text.

| # | name | construction | what a wrong implementation does | measured here? |
|---|---|---|---|---|
| E1 | **stuck-LSB 8-bit, skewed** | 20,000 (or 10^6) bytes, bits 7..1 each 1 w.p. 0.9 (seed 7), bit 0 = 0 | spec-literal `n = 8`: `n×H_bitstring` 1.345 > truth 1.064; with the bit removed 0.594. A §6.4-ranked implementation reports ≤ 1.064. The *final* figure overstates only if `H_original` also does | yes, 20k: assessed 1.031 vs 0.594 |
| E2 | **stuck-LSB 8-bit, structured** | as E1 but bits 7..1 form a bit-level Markov chain `P(b_t = b_{t-1}) = 0.9` across symbol boundaries, LSB 0; compare with the same bits packed 7 per byte | this is the case where the bitstring term should bind; if the padded `8×H_bitstring` exceeds the 7-bit figure **and** exceeds `-log2` of the true conditional max, the final figure overstates | no — differential phase |
| E3 | **stuck-MSB vs stuck-LSB, same bits** | file A: `v << 1` (LSB 0); file B: `v` (MSB 0), `v` uniform 7-bit | A: `n = 8`, B: `n = 7` — the same fault treated two ways; a §6.4 implementation gives identical figures | yes: A 4.389, B 5.396 (truth 7) |
| E4 | **one wide byte** | 10^6 4-bit values + one `0x80` at position 1234 | declared `4` → refuse (D-6); inferred → `n = 8`, 17 symbols, figure drops (1.484 vs 1.820). A masking implementation would silently assess `0x00` at that position | yes, 2k |
| E5 | **all-zero** | `bytes(10^6)` | correct: refuse (one symbol). Wrong: `n = 0`, `blen = 0`, `malloc(0)`, estimators on an empty bitstring | yes: refused via `alph_size ≤ 1` |
| E6 | **exactly 999,999 / 1,000,000 / 1,000,001** | random bits, three files | `>=` vs `>`; restart must take only 1,000,000 | covered by regression-minsize.sh (999,999-class via rand8_short); run the ±1 pair |
| E7 | **`-l` last-block short** | 10^6-byte file, `-l 1,700000` → loads 300,000 | must be refused without the escape; JSON `subsetRequestedSamples 700000 / subsetActualSamples 300000` with it | regression-subset.sh |
| E8 | **`-l` ULONG_MAX size** | `-l 0,18446744073709551615` | whole file assessed as block 0; `subsetRequestedSamples` shows the request — fine; `-l 1,…` → past end, refused | not run (compliant file is a heavy job) |
| E9 | **LLP64 `blen` wrap** | 536,870,920 random bytes declared `8` (Windows CI); control: same count of `{0,1}` bytes declared `1` | correct: assessment or clean refusal; suspected: crash in `utils.h:534-538`; control assesses | not run (platform, size) |
| E10 | **`-c` output count** | 1,000,000 bytes from a 256-bit conditioner (31,250 outputs) under `-c`; control 999,999 bytes | spec: refuse (< 10^6 outputs); tool: accepts; control refused — shows the gate is on bytes | not run |
| E11 | **declared 8, data 4-bit, `-q -o`** | 4-bit uniform, `… -q -o r.json f 8` | stdout warning leaks under `-q`; JSON silent | yes |
| E12 | **two-symbol non-{0,1} alphabet, declared 8** | bytes ∈ {33, 211}, 10^6 | `alph_size = 2` → binary path, translated to {0,1}; `H_bitstring` not produced; `F01` (withdrawn) — confirm the three binary-only estimators run on the translated data | regression / `F01` record |
| E13 | **symlink → FIFO race** | symlink to a regular file; after `stat`, repoint to a FIFO | hang in `fopen` (hardening; N-07 still binds the result) | not run |

---

## 5. Probe record

All with `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`, `cpp/ea_non_iid`
`1ad1568c…` (and `cpp/ea_iid` `22f1319a…` for one case). Exit codes from
`logs/analysis-intake-exitcodes.log`; corpus sha256 in
`logs/analysis-intake-corpus-sha256.log`.

| probe | input | exit | observed (verbatim lines from the log) |
|---|---|---|---|
| `allzero-inferred` | 2000 × `0x00` | 255 | `Loaded 2000 samples of 1 distinct 0-bit-wide symbols` / `Symbol alphabet consists of 1 symbol. No entropy awarded...` |
| `allzero-declared1` | same, `1` | 255 | `Warning: Symbols appear to be narrower than described.` / `… 1 distinct 1-bit-wide symbols` / 1-symbol refusal |
| `lsb0-8bit-inferred` | 20,000 uniform bytes `& 0xFE` | 0 | `128 distinct 8-bit-wide symbols`; `H_bitstring = 0.54861603515464596`; `H_bitstring Per Symbol = 4.3889282812371677`; `H_original = 6.4858263215592542`; `Assessed min entropy: 4.3889282812371677` |
| `lsb0-shifted-7bit` | same values `>> 1` | 0 | `128 distinct 7-bit-wide symbols`; `H_bitstring = 0.77087121065528141`; `Per Symbol = 5.39609847458697`; `H_original = 6.4858263215592542`; `Assessed min entropy: 5.39609847458697` |
| `skew09-lsb0-8bit` | 7 bits p(1)=0.9, `<< 1` | 0 | `90 distinct 8-bit-wide symbols`; `H_bitstring = 0.16815618845789834`; `Per Symbol = 1.3452495076631867`; `H_original = 1.0305347188697431`; `Assessed min entropy: 1.0305347188697431` |
| `skew09-7bit` | same, unshifted | 0 | `90 distinct 7-bit-wide symbols`; `H_bitstring = 0.084891705450500551`; `Per Symbol = 0.5942419381535039`; `H_original = 1.0305347188697431`; `Assessed min entropy: 0.5942419381535039` |
| `two-samples` | `00 01` | 0 | `Loaded 2 samples of 2 distinct 1-bit-wide symbols`; `Literal Most Common Value Estimate: min entropy = -0`; `Literal Markov Estimate: min entropy = 1`; `Assessed min entropy: -0` |
| `two-samples-iid` | same, `ea_iid` | 1 | `Chi square independence: m = 1, test fails per SP 800-90B 5.2.3`; `IID test suite failed` |
| `4bit-declared8-json` | 2000 × `randrange(16)`, `-q -o`, `8` | 0 | stdout under `-q` still carries `Warning: Symbols appear to be narrower than described.`; JSON `errorLevel 0`, `bitsPerSymbol 8`, `bitsPerSymbolInferred false`, no `errorMessage`, `nonCompliantShortDataset true` |
| `4bit-declared8-vv` | same, `-vv 8` | 0 | `16 distinct 8-bit-wide symbols`; `Per Symbol = 1.5197909534677914`; `Assessed … 1.5197909534677914` |
| `4bit-inferred` | same, no width | 0 | `16 distinct 4-bit-wide symbols`; `H_bitstring = 0.45491017076718981`; `Per Symbol = 1.8196406830687593`; `Assessed … 1.8196406830687593` |
| `4bit-one80-declared4` | + one `0x80`, `4` | 255 | `Incorrect bit width specification: Data (8) does not fit within described bit width: 4.` / `Error reading file.` |
| `4bit-one80-inferred` | same, no width | 0 | `17 distinct 8-bit-wide symbols`; `Per Symbol = 1.4843161408205878`; `Assessed … 1.4843161408205878` |
| `subset-last1` | `-l 1999,1` on 2000 B | 255 | `block 1999 of size 1`; `Loaded 1 samples of 1 distinct 2-bit-wide symbols`; 1-symbol refusal (no assert) |
| `subset-past-end` | `-l 2000,1` | 255 | `Error: subset offset 2000 is at or past the end of the 2000-byte file.` |
| `subset-straddle` | `-l 1,1500` | 0 | `block 1 of size 1500`; `Loaded 500 samples of 16 distinct 4-bit-wide symbols` |
| `bits-0`, `bits-9` | width 0 / 9 | 255 | `Invalid bits per symbol: expected an unsigned decimal integer from 1 through 8.` |
| `empty-file` | 0 bytes | 255 | `Error: '…/intake-empty.bin' is empty` |

Negative-control discipline (rule 7): each refusal above has an accepting
sibling that differs minimally (e.g. `4bit-one80-declared4` refused vs
`4bit-declared8-vv` accepted on the same 2000-byte base; `subset-past-end`
refused vs `subset-straddle` accepted on the same file). Every accepted probe
is below 10^6 samples and is **not** a compliant assessment.

---

## 6. Suspicions, ranked (none is a reproduced finding on the target profile)

| # | title | severity if confirmed | direction | confidence | where |
|---|---|---|---|---|---|
| S1 | LLP64 `blen = len × word_size` wraps; positive-wrap windows under-allocate `bsymbols` and the fill loop indexes it with a wrapped-negative offset | HIGH (memory safety from an input file), Windows only | crash | medium (arithmetic is certain; behaviour unmeasured) | `utils.h:520, 523, 534-538`; `:707, 710, 722-726` |
| S2 | A constant non-leading bit inflates `n × H_bitstring` above the true min-entropy (measured 1.345 vs 1.064); inference removes a constant *leading* bit only | CRITICAL **only if** a dataset is found where `H_original` also overstates; otherwise a §B standard observation | overstates (the term; final figure not shown to) | medium that the mechanism is real (measured); low that it reaches the final figure on real data | `utils.h:458-470, 520-538`; `non_iid_main.cpp:636` |
| S3 | `-c` gate counts bytes, §3.1.1 item 2 counts conditioning outputs — weaker by `n_out/8` | MEDIUM (non-compliant assessment accepted) | neutral/understates | high that the code does this; the decision is the owner's | `utils.h:297`; mains `:320` |
| S4 | `-c` with inferred width drops a constant high bit from the conditioned binary string; `h' × n_out` at the declared `n_out` then overstates | MEDIUM, `-c` only, consumer-side multiplication | overstates | low–medium | `utils.h:458-470`; `non_iid_main.cpp:651` |
| S5 | `utils.h:1023-1025` falsely states `non_iid_main.cpp` refuses `> INT_MAX` | LOW (documentation that could license a future `int` narrowing) | neutral | high | `utils.h:1023-1025` vs `non_iid_main.cpp` (no `INT_MAX`) |
| S6 | "narrower than described" warning ignores `-q` and never reaches JSON; `errorMsg` left set at `errorLevel 0` | LOW | neutral (conservative figure) | high (measured) | `utils.h:483-485`; `test_run_base.h:69-72` |
| S7 | `read_file` / `read_file_subset` duplicated | LOW (maintenance; the `F04` class) | — | high | `utils.h:319-547` vs `:549-735` |
| S8 | stat→fopen TOCTOU reopens the #259 hang | LOW (hardening) | crash/hang | medium | `utils.h:326-328` |
| S9 | `-0` printed for a zero estimate; Markov prints 1.0 on two samples (escape only) | LOW | neutral | high (measured) | `non_iid_main.cpp:663`; Markov agent |

## 7. Documented divergences touched, and not re-reported

- `D-6` out-of-width values rejected rather than masked — confirmed; the mask
  at `utils.h:508-510` is dead code because of it.
- `F02` width inference and its JSON reporting — the inference is unchanged by
  decision; §2.4 adds the direction-vs-truth analysis and the asymmetry.
- The ≥ 1,000,000 intake with `EA_ALLOW_SHORT_DATASET` — conformant for `-i`;
  §2.5 is the `-c` question.
- `OC-104` option-after-operand refusal; `A04`/`A05`/`F03`/`F04`/`C14` report
  plumbing — exercised only as the path intake runs under.
- `F01` (withdrawn): binary is by alphabet; the `alph_size > 2` gate stands.
- `N-03` (`ea_conditioning`, unsupported): the width-0 path it describes is
  reachable in the supported tools and fails closed there (§2.3).
