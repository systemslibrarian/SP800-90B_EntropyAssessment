# Output integrity — JSON and text outputs vs the computed numbers, escaping, partial/failed runs, exit codes

Analysis phase, 2026-11-07. Branch `audit/2026-11-07` (HEAD `a2c3c81`). No build, no run over
20,000 samples. Tiny probes used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` on the three
10,000-sample fixtures under `bin/`; every such run is NOT a compliant assessment and the tool
itself marks it so (`nonCompliantShortDataset: true`). All probe output is under
`docs/audits/2026-11-07-aggressive-audit/logs/analysis-output-*` (the driver log is
`analysis-output-probe.log`, the `std::min` check is `analysis-output-stdmin-nan.log`, the
per-estimator identity check is `analysis-output-q1-vv-peridentity.log`).

Binaries measured (instrument rule 4):

```
1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  cpp/ea_non_iid
22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  cpp/ea_iid
4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  cpp/ea_restart   (source-read only; needs exactly 1,000,000 samples, not probed)
```

jsoncpp 1.9.8 (`/opt/homebrew/include/json/version.h`), `Value::defaultRealPrecision = 17`
(`value.h:261`), `valueToString(double, precision = defaultRealPrecision, ...)` (`writer.h:350`).

Platform: Darwin arm64, Apple clang (this host). Nothing else measured.

**Headline.** I found no path by which the written JSON figure differs from the computed figure:
on the probed fixture all 17 per-estimator values and the three Overall values in the JSON are
bit-identical (IEEE-754 pattern) to the `%.17g` text. The real exposure in this component is
*semantic*: which field a consumer reads, what units it is in, and three latent folding hazards
in the `min()` combination that have no producer today. Ranked list in §5.

---

## 1. The spec, transcribed for this component

There is no output format in SP 800-90B. What the standard fixes is *which quantities exist*
and *how they combine*:

**SP 800-90B §3.1.3 (PDF p. 20):**

> "After determining the entropy estimation track, a min-entropy estimate per sample, denoted as
> H_original, for the sequential dataset is calculated using the methods described in Section 6.1
> (for the IID track) or Section 6.2 (for the non-IID track)."
>
> "If the sequential dataset is not binary, an additional entropy estimation (per bit), denoted
> H_bitstring, is estimated. First, the sequential dataset that contains L samples (each having n
> bits) is considered as a bitstring of size nL. The bits after the first 1 000 000 bits may be
> ignored. Then, the estimation is done based on the entropy estimation track, as specified in the
> previous paragraph, and H_bitstring is calculated. Then, the entropy per sample is estimated to
> be n×H_bitstring."
>
> "The initial entropy estimate of the noise source is calculated as H_I = min(H_original,
> n×H_bitstring, H_submitter) for non-binary sources and as H_I = min(H_original, H_submitter) for
> binary sources."

So the reportable quantities are: `H_original` (per sample), `H_bitstring` (**per bit**), `n`,
`n×H_bitstring` (per sample), and the tool's `H_I` without `H_submitter` = `min(H_original,
n×H_bitstring)` for non-binary and `H_original` for binary. Units: per sample, except
`H_bitstring`.

**SP 800-90B §6.2 (PDF p. 49):**

> "For non-IID data, the following estimators shall be calculated ... and the minimum of all the
> estimates is taken as the entropy assessment ... The Collision, Markov and Compression estimates
> are only applied to binary inputs."

So the combination is a **minimum over all ten estimators** (seven for non-binary literal). Any
mechanism that drops an estimate from the minimum can only raise the figure.

**SP 800-90B §3.1.5.2 (PDF p. 25)** (conditioned data, the `-c` mode):

> "The output of the conditioning component (n_out) shall be treated as a binary string, for
> purposes of the entropy estimation."

So `h'` is a **per-bit** figure.

**SP 800-90B §6.1 (PDF p. 48):** "For sources with IID outputs, the min-entropy estimation is
determined using the most common value estimate described in Section 6.3.1." — the IID tool's
`H_original`/`H_bitstring` are MCV only.

Restart (§3.1.4, PDF pp. 20–22): the tool reports `H_r`, `H_c`, `H_I` and the §3.1.4.3 sanity
check; the validated figure is `min(H_r, H_c, H_I)` after `min(H_r, H_c) >= H_I/2`.

---

## 2. Code map, step by step, with the places the code and the spec (or the code and itself) differ

### 2.1 Where the figures are computed and written — `cpp/non_iid_main.cpp`

| spec quantity | code | lines |
|---|---|---|
| `H_original` init = n | `H_original = data.word_size;` | 353 |
| `H_bitstring` init = 1 | `H_bitstring = 1.0;` | 354 |
| per-estimator fold | `H_bitstring = min(ret_min_entropy, H_bitstring);` / `H_original = min(ret, H_original)` | 368, 377, 394, 405, 421, 430, 442, 453, 472, 483, 499, 509, 528, 539, 556, 567, 584, 595, 612, 623 |
| `H_I` | `h_assessed = data.word_size; if (alph>2 || !initial) h_assessed = min(h_assessed, H_bitstring*word_size); if (initial) h_assessed = min(h_assessed, H_original);` | 641–650 |
| text (verbose 1/2) | `printf("\nH_original: %f\n")`, `"H_bitstring: %f"`, `"min(H_original, %d X H_bitstring): %f"`, `-c`: `"h': %f"` | 652–661 |
| text (verbose > 2) | `"H_bitstring = %.17g"`, `"H_bitstring Per Symbol = %.17g"`, `"H_original = %.17g"`, `"Assessed min entropy: %.17g"` | 662–673 |
| JSON Overall | `tcOverall.h_bitstring / h_original / data_word_size / h_assessed; testCaseNumber = "Overall"` | 675–688 |
| success marker | `testRun.errorLevel = 0;` then `writeJsonReport(...)`, `return -1` if it fails, else `return 0` | 689–702 |

JSON serialisation: `NonIidTestRun::GetAsJson()` (`cpp/non_iid/non_iid_test_run.h:15–28`) →
`TestRunBase::GetBaseJson()` (`cpp/shared/test_run_base.h:61–103`) + per-case
`NonIidTestCase::GetAsJson()` (`cpp/non_iid/non_iid_test_case.h:29–63`) →
`TestCaseBase::GetBaseJson()` (`cpp/shared/test_case_base.h:41–70`), then
`Json::StyledWriter().write(json)`.

**Doubles.** Every figure is stored in `Json::Value` as `double` and written by jsoncpp's
`valueToString(double)` at `defaultRealPrecision = 17` significant digits (`%.17g`), i.e. the
same conversion the `-vv`/`-vvv` text uses. **Measured:** on `bin/rand8_short.bin` (sha
`17d2eaf9...`) all three Overall values and all 17 per-estimator values in the JSON are
bit-identical to the `%.17g` text (`analysis-output-probe.log` Q1,
`analysis-output-q1-vv-peridentity.log`: "17 identical, 0 not identical"). jsoncpp appends
`.0` to an integral double (`"dataWordSize": 8.0`) — harmless. There is **no `float`** anywhere
in the writers (`grep float` over the eight target files: no hits). The only narrowing casts are
`(Json::UInt64)`/`(Json::Int64)` of `unsigned long`/`long` counters, which are widenings or
same-width on LP64.

**Default-verbosity text is `%f` (6 decimals, round-to-nearest).** Measured: `H_bitstring`
0.7326117180606562 prints `0.732612` (nearest), not `0.732611` (truncation) — Q1b. The rounding
can go UP by at most 5e-7 bit; the JSON is unaffected. LOW.

### 2.2 The `-c` unit: text says per bit, JSON says per symbol (F23 sub-claim, now CONFIRMED)

Code: in `-c` mode `initial_entropy == false`, so `h_assessed = min(word_size, H_bitstring *
word_size)` (646) — **per symbol** — while the text prints `h': %f` = `H_bitstring` (660) —
**per bit**, which is what §3.1.5.2 (p. 25) defines. **Measured** (Q2): `-c -vvv -o` on the
8-bit fixture gives text `H_bitstring = 0.73261171806065617` (`h'`) and JSON
`"hAssessed": 5.860893744485249` = `8 × h'`, with `"hOriginal"` absent and `"dataWordSize":
8.0`. The JSON carries no unit and no mode marker other than the reconstructed `commandline`.
A consumer that reads `hAssessed` from a `-c` report as "`h'` per bit" overstates by a factor of
`n`. The tool's own figure is internally consistent (per symbol); this is a **consumer trap**,
not an arithmetic error. The same holds for `ea_iid -c` (`iid_main.cpp:455–463`). Tracker F23
listed this as UNCONFIRMED; this probe confirms the sub-claim. ShannonPad's documented path is
`-i`, so this does not touch the target profile unless a `-c` report is ever read.

### 2.3 Which field IS the assessed min-entropy, and can two fields disagree?

- The assessed figure is `testCases[i].hAssessed` on the element whose `testCaseDesc ==
  "Overall"` (last element). It is per sample, at `bitsPerSymbol`.
- `hOriginal` and `hBitstring` on the same element are the two inputs; `hBitstring` is **per
  bit**. **Measured** (Q1): `min(dataWordSize, dataWordSize*hBitstring, hOriginal)` recomputed
  from the JSON is bit-identical to `hAssessed`, so the fields cannot disagree by construction
  (641–650 and 668–678 read the same variables). On this fixture `hOriginal - hAssessed =
  0.7755 bit/sample`: a consumer that reads `hOriginal` (the "literal" figure a reader might
  expect to be "the" estimate) instead of `hAssessed` overstates by that much, because
  Compression on the bitstring binds. **A consumer must read `hAssessed` and nothing else.**
- The per-estimator elements also carry `hBitstring`/`hOriginal` keys (same names as the
  Overall ones). A consumer that searches the document for the first `hOriginal` gets the MCV
  value (7.0105 on this fixture, against 5.8609 assessed). Key names are not unique to the
  Overall element; only `testCaseDesc` disambiguates.
- `mcvEstimateMode/PHat/PU` on the MCV element are the **Literal** MCV intermediates under `-i`
  (the Literal call at 381 overwrites the Bitstring call at 374 into the same `tc631`) and the
  Bitstring ones under `-c` (F23, already recorded).
- I did not inspect the consumer (TruePad/ShannonPad); its working tree is out of scope for this
  session. The contract above is what the code offers.

### 2.4 Failed and partial runs: can a file look like success?

The only assignments of `errorLevel = 0` are on the success paths (`non_iid_main.cpp:680`,
`iid_main.cpp:572`, `restart_main.cpp:1197,1205`), each immediately before the final write and
after every estimator has run. Every error path sets `-1` (or `2` for the IID statistical
rejection) before writing. The `-o` path is claimed at option-parse time with a placeholder
(`claimReportTarget`, `non_iid_main.cpp:77–92`) carrying `errorLevel -1`, `reportComplete:
false`, no `testCases`; **measured** (Q4a): `ea_non_iid -o x.json` with no operand exits 255 and
leaves exactly that placeholder. The final write is atomic (`writeJsonReport`,
`TestRunUtils.h:418–611`: `O_CREAT|O_EXCL|O_NOFOLLOW` temp, random suffix, `write` loop,
`close` checked, `rename`), and on any failure the temp is removed and the placeholder stays, with
`return -1` (`non_iid_main.cpp:695–698`). So: **no path leaves `errorLevel 0` with assessment
fields unless the success path ran to completion and the write succeeded.** A signal or
`assert` mid-run leaves the placeholder.

Asymmetry worth knowing: the placeholder says `reportComplete: false`; the success report has
**no** `reportComplete` key (measured Q1: "reportComplete present: False"). A consumer that
requires `reportComplete == true` rejects every valid report; one that tests `!= false` works.

Error-report shape (Q4b, missing input): `errorLevel -1`, `errorClass "input"`,
`errorMessage`, `filename`, `"testCases": null`, `"type": ""`.

### 2.5 Can a run exit 0 after an error?

- All `exit(-1)`/`print_usage()` paths are 255; IID statistical failure is `return 1`
  (`iid_main.cpp:545`, `restart_main.cpp:1166`); `--version` is a deliberate exit 0 with nothing
  assessed, now honoured only as a pre-operand option (C14 route 2 / A04 / F04, `TestRunUtils.h
  :312–324`).
- Two exit-0 outcomes carry a condition the exit code does not express:
  1. `EA_ALLOW_SHORT_DATASET=1` → exit 0, `nonCompliantShortDataset: true` in JSON and a stdout
     banner (`utils.h:294–317`). Deliberate test escape; the exit code is silent about it.
  2. `read_file_subset` "Warning: Symbols appear to be narrower than described."
     (`utils.h:483–485`) sets `testRun->errorMsg` **without** setting `errorLevel`, and
     `GetBaseJson` emits `errorMessage` only when `errorLevel != 0` (`test_run_base.h:69`).
     **Measured** (Q4d): `rand4_short.bin` declared 8-bit → stdout prints the warning, exit 0,
     JSON `errorLevel 0`, **no `errorMessage`**, `bitsPerSymbol 8`, `bitsPerSymbolInferred
     false`. The JSON reader cannot see that the declared width was wrong. On this fixture the
     mis-declaration is conservative per sample (1.5157 at width 8 vs 3.2155 at width 4, because
     the bitstring gains four constant zero bits), but the warning is lost. Text and JSON
     disagree. LOW, neutral-to-conservative.

### 2.6 Escaping of `filename` and `commandline`

`filename` is `argv[optind]` verbatim (`non_iid_main.cpp:275`); `commandline` is
`recreateCommandLine()` (`utils.h:1293–1302`): argv joined by single spaces, **no quoting**.
jsoncpp 1.9.8 `valueToQuotedString` escapes `"`, `\`, `\b\f\n\r\t`, other control bytes as
`\uXXXX`, and transcodes bytes ≥ 0x80 through `utf8ToCodepoint`.

**Measured** (Q3): filenames containing `"`, `\`, newline, tab, space and UTF-8 `é` all produce
parseable JSON whose `filename` round-trips exactly; `commandline` round-trips to the
space-join. A filename containing byte `0xFF` **cannot be created on APFS** ("Illegal byte
sequence"), so that case is NOT RUN on this host. Invalid UTF-8 injected through `argv[0]`
(`exec -a`) IS reachable in `commandline`: bytes `ff fe` became two U+FFFD; bytes `80 'Z' 'q'`
became `U+FFFD 'q'` — **the ASCII `Z` after a stray continuation byte is consumed as its
continuation and lost.** Still valid JSON, no crash. On a Linux filesystem (ext4 accepts such
names) the same transcoding applies to `filename`, so the report could name a file that does
not exist, or a different one (`x\x80Z.bin` → `x�.bin`). The `sha256` field is the real
identity and is unaffected. LOW.

Because `commandline` is a space-join, `-o "a b.json"` is indistinguishable from `-o a
b.json`; the field is informational only. LOW.

### 2.7 `std::min` argument order and the F13 mechanism (latent; no producer found)

`std::min(a, b)` returns `(b < a) ? b : a`. The mains fold every estimate as
`H = min(ret, H)` (ret FIRST). **Measured** (`analysis-output-stdmin-nan.log`):

```
after MCV  min(0.30, 1.0)   H=0.30
after NaN  min(NaN, 0.30)   H=nan
after next min(0.70, NaN)   H=0.70   <-- running minimum 0.30 is gone
guard (NaN  >= 0) = 0  -> treated as 'not run', flagged, H kept
guard (+inf >= 0) = 1  -> folded: min(+inf, 0.30) = 0.30, no flag
```

So a NaN from an estimator that is folded WITHOUT the `>= 0` guard — **MCV** (368, 377) and
**Markov** (421, 430) in `ea_non_iid`; `most_common` in `ea_iid` (441, 445, with `min(h,
H_bitstring*w)` at 458 dropping a NaN immediately); MCV and Markov rows/cols in `ea_restart`
(863, 868, 921, 926) — would erase every estimate folded before it and the figure would restart
from the next estimator. In `ea_non_iid` the order is MCV → Collision → **Markov** → Compression
..., so a Markov NaN would discard the MCV and Collision minima; that is the F13 case the
tracker holds as UNCONFIRMED ("no NaN producer at ≥ 10^6").

I re-derived the producers and agree there is none at len > 1 with ≥ 2 symbols present:

- `most_common` (`most_common.h:24–31`): `pmax = mode/len ∈ (0, 1]`, `len > 1` asserted, so
  `pmax*(1-pmax)/(len-1) ≥ 0`, `ubound = min(1.0, pmax + …) ∈ (0, 1]`, `-log2(ubound)` finite.
  The argument order `min(1.0, X)` there is the fail-closed one (comment at 26–29).
- `markov_test` (`markov_test.h:31–45, 70–105`): every `P_xy` is guarded `> 0` before `log2`,
  `P_0, P_1 > 0` whenever the path guard holds (comment 66–67, verified case by case: with both
  bits present at least one of the six paths is taken, so `H_min < 128` and finite; with one
  bit absent path 1 or 6 is taken). `fmin(H_min/128, 1.0)` finite.
- `+inf` producers (would pass the `>= 0` guard and be dropped silently, **without** the
  `*EstimateNotRun` flag): `-log2(p)` with `p == 0`. Collision `p ≥ 0.5`
  (`collision_test.h:79`), Compression `p > 1/alph_size` or the lower bound
  (`compression_test.h:250–256`), LRS `pu ≥ Pmax ≥ S[v]^{1/v}/… > 0` because `S[v] ≥ 1` by the
  definition of `v` (`lrs_test.h:549–567`), prediction `curMax ≥ 1/k` (`utils.h:1207, 1232`).
  None reaches 0.

So this is a **hardening gap with no known trigger**, not a reproduced defect. It is listed
because the direction, if a trigger ever appears (a future estimator change, a platform where
a `long double` path returns NaN), is an overstatement with no flag in the report. A one-line
robust form is `if (std::isfinite(ret) && ret >= 0) { fold } else { not_run = true }` at every
fold site, which also closes the `+inf` silent drop.

### 2.8 `ea_iid` specifics (`cpp/iid_main.cpp`)

- `h_assessed` is computed independently of verbosity (455–463) and emitted only on a complete
  pass (570) — NOVEL-02 repair; **measured** (Q4c): failed battery → exit 1, `errorLevel 2`,
  `errorClass "statistical"`, `IID false`, `assessmentComplete true`, **no `hAssessed`**, but
  `hOriginal 7.0105` and `hBitstring 0.9834` present as diagnostics (README line 103 documents
  this). A consumer must check `errorLevel`/`IID` before reading any `h*` key.
- `int sample_size = data.len;` (352) is a `long → int` narrowing, guarded by the
  `testdata.len > INT_MAX` refusal at 393–408 (under `-i`, `testdata.len == data.len`). Fine.

### 2.9 `ea_restart` specifics (`cpp/restart_main.cpp`, source only)

- **No `hAssessed`.** The report's Overall element carries `h_r`, `h_c`, `h_i`
  (1199–1204; IID 873–876) and the text prints `min(H_r, H_c, H_I): %f` (1222). A consumer must
  compute the minimum. `h_i` is `H_I` **after** the `/bit` scaling at 638–639, i.e. per symbol.
- **Statistical rejections are encoded differently from `ea_iid`:** sanity-check failure
  (810–825) and validation failure (1177–1193) write `errorLevel -1`, `errorClass
  "statistical"`, `exit(-1)` → 255; the IID-battery failure writes `errorLevel 2` **without**
  `errorClass` and returns 1 (1149–1167). `ea_iid` uses (`2`, `"statistical"`, exit 1). A
  consumer that maps exit 255 to "operational error, retry" misreads a restart rejection. LOW,
  neutral.
- `printf("H_I: %f\n", H_I);` at 735 is unconditional — it prints under `-q`. LOW, text only.
- Declined estimators (`ret < 0`) are skipped at 897–907, 937–948, 972–982, 991–1001,
  1014–1025, 1035–1046, 1055–1066, 1076–1087 **without** setting `literal_not_run`, so the
  restart report cannot show that `H_r`/`H_c` were minima over fewer estimators (the F05 flag
  exists only in `ea_non_iid`). Direction: the figure is unchanged, the report is less
  informative. LOW.
- Success-path figures in the restart text at verbose 1/2 are `%f`; JSON is 17-digit. Same as
  2.1.

### 2.10 Miscellany measured or read

- `"type"` is `""` in every real `ea_non_iid`/`ea_iid` report (never assigned; measured Q1, Q4b,
  Q4c) but `"non-IID"`/`"IID"` in the C14 placeholder and `"Restart"` in restart reports. A
  consumer cannot use `type` to identify the producing tool; `ea_iid` adds `assessmentMode:
  "IID"`, `ea_non_iid` adds nothing (`IID: false` is a constant there,
  `non_iid_test_run.h:30`). LOW.
- `-vvv` (verbose = 4) **suppresses** every per-estimator line, because each estimator prints at
  `verbose == 3` exactly (`most_common.h:33`, `markov_test.h:55`, `utils.h:1243`, etc.) while
  the main's summary lines print at `verbose > 2`. Measured: 17 `min entropy =` lines at `-vv`,
  0 at `-vvv`. The usage text says "-v ... Can be used multiple times." Text only; JSON
  unaffected. LOW.
- `getCurrentTimestamp()` (`TestRunUtils.h:613–655`) is local time with no zone, and
  dereferences `localtime()` without a NULL check. LOW.
- `"testCases": null` (not `[]`) on error reports; `"permutationTestResults": null` when none
  ran. Consumers must accept null. LOW.
- The `-t` truncation (bitstring cut to 1,000,000 bits, `non_iid_main.cpp:344`) is not recorded
  in the JSON except through `commandline`; `assessedSampleCount` is the symbol count. LOW.

---

## 3. Prior repairs touching this component, and how I would try to break each

| repair | where | break attempt |
|---|---|---|
| **C14** placeholder claim at `-o` parse (`claimReportTarget`, all three mains) | `non_iid_main.cpp:77–92,242`; `iid_main.cpp:75–90,230`; `restart_main.cpp:348–363,447` | `-o a.json -o b.json`: `a.json` keeps a placeholder (fail-closed, fine) — assert it. `-o x -l 0,0`: the `-l` error path fires AFTER the claim so the placeholder is replaced by an error report — assert errorLevel −1. Kill −9 between claim and final write on a 1e6 run (execution phase) — assert placeholder survives. A `-o` on a **different filesystem** from CWD is irrelevant (temp is a sibling); a `-o` into a directory without write permission but with an existing file → claim fails → exit before assessing: assert. |
| **C08 / N-09** atomic checked write (`writeJsonReport`) | `TestRunUtils.h:418–611` | `/dev/full`, missing dir (covered by `regression-output.sh`). New: a `-o` path whose **directory** is writable but a sibling temp name collides 8 times — unreachable with 64 random bits. `-o` on a filesystem where `rename` over an existing file fails (SMB/FAT on macOS?) → final write fails → exit −1 with placeholder in place: fail-closed; measure on such a mount if available. **ENOSPC after `write` returns short**: covered by the loop; `close` checked. `fsync` is NOT called before `rename`, so a power loss can leave a zero-length `x.json` after a successful exit (not a stale-success, but an unparseable file) — MEDIUM-LOW durability gap, not an overstatement. |
| **A05 / F03** input-alias refusal + `O_EXCL|O_NOFOLLOW` temp | `TestRunUtils.h:64–134, 244–271, 419–549` | Covered by `regression-output-aliasing.sh` (29 checks). New angle: `-o` equal to the input **via a bind/`hardlink` created after the prescan but before the final write** (TOCTOU on the final `rename` target): `rename(tmp, path)` replaces `path`'s directory entry, which never follows the link, so the capture inode survives — fine; assert with a hardlink planted mid-run (execution phase). |
| **N-07** digest of the consumed buffer | `utils.h:212–248` | Covered by `regression-input-identity.sh`. Nothing new. |
| **NOVEL-02** `ea_iid` `hAssessed` independent of verbosity; fields omitted when not computed | `iid_main.cpp:448–477, 570` | Covered by `regression-iid-json.sh`. New: `-c` with 1-bit input (bsymbols aliases symbols, `blen == len`): assert `hBitstring` present, `hOriginal` absent, `hAssessed == 1×hBitstring`. |
| **F05 / dfe325a** `literalEstimateNotRun` / `bitstringEstimateNotRun` | `test_case_base.h:33–40`, all `else { …_not_run = true; }` in `non_iid_main.cpp` | The flag is set for `ret < 0` **and for NaN** (NaN fails `>= 0`) but **not for +inf** (passes). No producer, see 2.7. `ea_restart` has no flag at all (2.9). |
| **C16 / C23** restart report fields (`restartHI`, `restartXcutoff`, `restartCutoffMethod`, `passedRestartSanityCheck`) | `test_run_base.h:50–58, 85–93`; `restart_main.cpp:794–809` | `restartXcutoff >= 0` gates the block; `-1` default is correct before the check. If the sanity check fails the report still carries the block (good). Assert `h_i == restartHI` on a `/bit` run (both post-scaling). |
| **F03-tracker / c2f1dcd** minimum-size refusal writes `errorLevel −1` | `utils.h:294–317` | With `EA_ALLOW_SHORT_DATASET=1` exit is 0 and only the JSON flag says non-compliant (2.5). A harness that trusts exit status + `hAssessed` and ignores `nonCompliantShortDataset` accepts a non-compliant figure. Documented escape; worth a line in the consumer contract. |
| **OC-104** option-after-operand refusal | `TestRunUtils.h:363–385` | `-o` after the operand never reaches `claimReportTarget`, so no placeholder: the refusal happens before anything is written (by design). Assert nothing is written and exit 255. |

---

## 4. Edge-case inputs that distinguish a correct from an incorrect implementation of THIS component

1. **Unit trap, `-c` (CONFIRMED on 10k).** `ea_non_iid -c -o c.json bin/truerand_8bit.bin 8`
   and `-vv` text: a correct consumer reads `hAssessed` as per symbol (`= 8 × h'`); an incorrect
   one reads it as `h'` and overstates by 8×. Expected: `hAssessed == dataWordSize × hBitstring`
   bit-identical; text `h'` equals `hBitstring`.
2. **Field-choice trap, `-i` 8-bit.** Any 8-bit file where Compression binds (all real captures
   so far): `hOriginal − hAssessed` is positive by ~0.7–0.8 bit/sample (measured 0.7755 on the
   10k fixture). A consumer reading `hOriginal`, or the first `hOriginal` key in document order
   (the MCV element's), overstates. Expected: read `testCaseDesc == "Overall"` → `hAssessed`.
3. **Width mis-declaration.** `bin/truerand_4bit.bin` declared `8`: stdout warning, JSON silent
   (`errorLevel 0`, no `errorMessage`). A correct report would carry a warning field; this one
   does not. Measured on the 10k fixture (Q4d).
4. **Placeholder vs success key asymmetry.** `ea_non_iid -o p.json` (no operand) →
   `reportComplete: false`; a successful run → key absent. A consumer requiring `== true` fails
   closed on every valid report (safe but wrong); one testing `== false` works.
5. **Exit code of statistical rejection differs by tool.** `ea_iid` on `bin/rand8_short.bin 8`
   → exit 1 / `errorLevel 2`; `ea_restart` sanity-check or validation failure → exit 255 /
   `errorLevel −1` / `errorClass "statistical"`; `ea_restart -i` battery failure → exit 1 /
   `errorLevel 2` / no `errorClass`. A consumer must not infer the class from the exit code.
6. **Lossy `commandline` on invalid UTF-8.** `exec -a $'ea_\x80Zq' ea_non_iid -q -o x.json
   bin/truerand_1bit.bin 1` → `commandline` begins `ea_�q`: the `Z` is gone. On Linux the
   same applies to `filename`. Valid JSON, no crash.
7. **NaN/inf folding (no producer; hardening).** If any estimator ever returned NaN at an
   unguarded fold (MCV, Markov), the earlier minima are erased (2.7). A build-time mutation that
   makes `markov_test` return `NAN` on a 1e6 binary file where MCV < Compression would show
   `hAssessed` rising with `errorLevel 0` and no flag. This distinguishes the current code from
   the `isfinite`-guarded form; it does not reproduce on the shipped code.
8. **`fsync` absence.** Not an overstatement; a crash/power loss after exit 0 may leave an
   unparseable report. Execution-phase check only if durability matters to the consumer.

---

## 5. Ranked findings for this component (all are suspicions or confirmed non-numeric behaviours; none is a reproduced overstatement by the tool itself)

| # | title | severity | direction | status |
|---|---|---|---|---|
| 1 | `-c` JSON `hAssessed` is per symbol (`n×h'`) while §3.1.5.2 and the text define `h'` per bit; no unit in the report | LOW–MEDIUM (consumer-dependent) | overstates ×n if misread | CONFIRMED on 10k (Q2); F23 sub-claim |
| 2 | `hOriginal`/`hBitstring` keys are reused on every element; a consumer not keyed on `testCaseDesc=="Overall"`→`hAssessed` reads a higher figure | LOW–MEDIUM (consumer-dependent) | overstates | measured 0.7755 bit/sample gap on 10k |
| 3 | `std::min(ret, H)` order erases prior minima on a NaN at MCV/Markov folds; `+inf` passes the `>=0` guard and is dropped with no flag | LOW (no producer found; F13 UNCONFIRMED stands) | overstates if ever triggered | mechanism measured; producers re-derived as absent |
| 4 | Width-mismatch warning dropped from JSON (`errorMsg` without `errorLevel`) | LOW | neutral/conservative | CONFIRMED (Q4d) |
| 5 | `type` field empty in real `ea_non_iid`/`ea_iid` reports; placeholder/restart populate it | LOW | neutral | CONFIRMED |
| 6 | Statistical-rejection encoding differs across tools (exit 1/`2` vs 255/`−1`), `errorClass` missing on restart-IID failure | LOW | neutral | source |
| 7 | Invalid UTF-8 in `filename`/`commandline` transcoded lossily (following ASCII byte swallowed) | LOW | neutral | CONFIRMED via argv[0]; filename case NOT RUN (APFS) |
| 8 | `-vvv` suppresses per-estimator lines; `commandline` unquoted; `H_I:` printed under `-q`; local-time stamp; `testCases: null` | LOW | neutral | measured / source |
| 9 | No `fsync` before `rename` | LOW | neutral (durability) | source |

**Documented divergences encountered, not re-reported:** F05 not-run flags (errorLevel untouched
by design, @joshuaehill on #255), F23 (now partly confirmed, see #1), N-10/NOVEL-02 (fixed),
C14/C08/A05/F03/C24 (repairs read and found consistent with their descriptions), OC-104.

**What this analysis does not establish:** anything about `ea_restart`'s runtime output (source
only); anything on Linux/Windows; the consumer's actual key path (not inspected); the `0xFF`
filename case (filesystem refused it here).
