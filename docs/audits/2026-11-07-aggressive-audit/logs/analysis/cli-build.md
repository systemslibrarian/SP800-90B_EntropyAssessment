# Analysis: command-line and build hardening (ea_non_iid, ea_iid, ea_restart; Makefile; dependency pins)

Date: 2026-11-07. Branch `audit/2026-11-07`. Phase: ANALYSIS (no build, no run over 20,000 samples).
Binaries every probe here ran against (instrument rule 4):

```
1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  cpp/ea_non_iid   (mtime 2026-11-07 19:28:57)
22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  cpp/ea_iid       (mtime 2026-11-07 19:28:52)
4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  cpp/ea_restart   (mtime 2026-11-07 19:29:04)
```
Platform: Darwin arm64, Apple clang 21.0.0 (clang-2100.4.1.1), Xcode 27.2 (27B52), SDK 27.2.
Probe script: `logs/analysis/cli-probe.sh`; outputs `logs/analysis-cli-*.log`, exit statuses by label in
`logs/analysis-cli-exitcodes.log`; every probe input is 2,000 samples or a nonexistent path, with
`EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`. Nothing here is a compliant assessment.

Known documented divergences (FORK-DIVERGENCE-AND-TRUST.md A.3 `OC-104`, B `C23`/`C22c`, D-1..D-6, NOTICE,
FINDINGS-TRACKER N-04/N-08/N-09/N-10, F04/F05, A04/A05/F03, C14/C16) were read first and are NOT re-reported
below except where the code departs from the documented decision or where the repair can be broken.

---

## 1. The standard's intake and aggregation rules, transcribed

There is no estimator algorithm for this component; the normative text is the intake and the H_I
combination. Quoted from `reference/sp800-90b.pages.txt`.

**§3.1.1 Data Collection (heading PDF p. 17; items PDF p. 19)**
> 1. A sequential dataset of at least 1 000 000 sample values obtained directly from the noise source
>    (i.e., raw data) shall be collected for validation. If the generation of 1 000 000 consecutive
>    samples is not possible, the concatenation of several smaller sets of consecutive samples ... is
>    allowed. Smaller sets shall contain at least 1000 samples. The concatenated dataset shall contain
>    at least 1 000 000 samples.
> 2. If the entropy source includes a conditioning component that is not listed in Section 3.1.5.1.1, a
>    conditioned sequential dataset of at least 1 000 000 consecutive conditioning component outputs
>    shall be collected ... treated as a binary string for testing purposes.
> 3. For the restart tests ... the entropy source must be restarted 1000 times; for each restart, 1000
>    consecutive samples shall be collected ... stored in a 1000x1000 restart matrix M.

Constants: N_min = 1,000,000 samples (item 1); restart matrix exactly r = c = 1000 (item 3).
Bound direction: a lower bound on the sample count ("at least").

**§3.1.2 Determining the track (PDF p. 19-20)**: the IID track only when the submitter claims IID AND
§5 tests pass on the sequential dataset AND on the row and column datasets (AND the conditioned
dataset if a non-vetted conditioner is used); "If any of these conditions are not met, the estimation
process shall follow the non-IID track."

**§3.1.3 Initial Entropy Estimate (PDF p. 20)**
> ... a min-entropy estimate per sample, denoted as H_original, for the sequential dataset is calculated
> ... If the sequential dataset is not binary, an additional entropy estimation (per bit), denoted
> H_bitstring, is estimated. First, the sequential dataset that contains L samples (each having n bits)
> is considered as a bitstring of size nL. The bits after the first 1 000 000 bits may be ignored. ...
> Then, the entropy per sample is estimated to be n x H_bitstring.
> The initial entropy estimate of the noise source is calculated as H_I = min(H_original, n x H_bitstring,
> H_submitter) for non-binary sources and as H_I = min(H_original, H_submitter) for binary sources.

Equation: H_I = min(H_original, n*H_bitstring) (the tool does not take H_submitter). Rounding: none.
Truncation of the bitstring to 10^6 bits is OPTIONAL ("may be ignored").

**§3.1.4.2 Validation Testing (PDF p. 21)**
> If the minimum of H_r and H_c is less than half of H_I, the validation fails, and no entropy estimate
> is awarded. Otherwise, the entropy assessment of the noise source is taken as the minimum of the row,
> the column and the initial estimates, i.e., min(H_r, H_c, H_I).

**§3.1.4.3 Sanity Check (PDF p. 22)**: `p = 2^-H_I`, alpha = 0.000005; X_max = max over rows and columns of
the most-common-value count; step 5 as printed is the single-binomial tail (DOCUMENTED DIVERGENCE `C23`:
the fork decides on the exact multinomial maximum and records both).

**§3.1.5.2 Non-vetted conditioning (PDF p. 25)**
> Let the obtained entropy estimate per bit be h'. The output of the conditioning component (n_out) shall
> be treated as a binary string, for purposes of the entropy estimation.
> h_out = min(Output_Entropy(n_in, n_out, nw, h_in), 0.999 n_out, h' x n_out).

So h' is PER BIT.

---

## 2. Step-to-code map, and every disagreement found

### 2.1 ea_non_iid (`cpp/non_iid_main.cpp`)

| Spec step | Code | Agreement |
|---|---|---|
| §3.1.1 item 1, N >= 10^6 | `utils.h:294-317 dataset_meets_minimum()` called at `non_iid_main.cpp:320`; `MIN_SIZE 1000000` (`utils.h:42`); checks `dp->len` = samples actually loaded (so `-l` subsets count) | agrees; documented escape `EA_ALLOW_SHORT_DATASET=1` requires the exact string "1" (`utils.h:300`) and sets `nonCompliantShortDataset` |
| §3.1.3 "not binary" | `(data.alph_size > 2) \|\| !initial_entropy` gates every bitstring estimator (`:364, :386, :417, ...`) | binary is decided by the OBSERVED alphabet, not the declared width (F01 WITHDRAWN 2026-10-02; §4.4.2 defines binary by alphabet) |
| §3.1.3 bitstring of size nL, MSB-first within symbol | `utils.h:520-538`: `blen = len*word_size`, `bsymbols[i*ws+j] = (symbols[i] >> (ws-1-j)) & 1` | agrees (bit order is a convention, F21 NOT-A-BUG) |
| §3.1.3 "bits after the first 1 000 000 may be ignored" | `:344 if (!all_bits && (data.blen > MIN_SIZE)) data.blen = MIN_SIZE;` under `-t` | agrees; `-a` default uses all bits |
| §3.1.3 H_I = min(H_original, n*H_bitstring) | `:632-641 h_assessed = ws; if (alph>2 \|\| !initial) h = min(h, H_bitstring*ws); if (initial) h = min(h, H_original);` | agrees in the finite case; see 2.4 for NaN |
| per-estimator "cannot be computed" | each fallible estimator guarded `if (ret >= 0)` else `*_not_run = true` (`:391-397` collision, `:439-445` compression, `:469-475` t-tuple, `:496-502` LRS, `:525-531` MultiMCW, `:553-559` Lag, `:581-587` MultiMMC, `:609-615` LZ78Y) | MCV (`:365-376`) and Markov (`:418-429`) are UNGUARDED: they fold whatever they return |
| §3.1.5.2 h' per bit (under `-c`) | `:651 printf("\nh': %f\n", H_bitstring)` prints per bit; but `:636 h_assessed = min(ws, H_bitstring*ws)` and `:678 tcOverall.h_assessed = h_assessed` put n x h' into JSON `hAssessed` | DISAGREEMENT OF SCALE within one run (F23, tracker UNCONFIRMED): stdout says h' per bit, JSON `hAssessed` is per packing symbol. Measured in the output agent's `logs/analysis-output-q2-c.json`: `hAssessed 5.8609`, `hBitstring 0.7326`, `dataWordSize 8` (5.8609 = 8 x 0.7326). A consumer that reads `hAssessed` from a `-c` report as "entropy per bit" overstates by a factor of `bitsPerSymbol` (up to 8x). |

### 2.2 ea_iid (`cpp/iid_main.cpp`)

| Spec step | Code | Agreement |
|---|---|---|
| §3.1.1 N >= 10^6 | `:320 dataset_meets_minimum` | agrees |
| §3.1.2 cond. 2: §5 tests on the sequential dataset; §3.1.1 item 2: conditioned data as a binary string | `:378-386` `testdata` view = bitstring under `-c`; `:480` chi-square, `:504` LRS, `:517` permutation on `testdata` | agrees (documented repair, #271) |
| §6.1 H_original = MCV | `:441 most_common(data.symbols, sample_size, ...)` | `sample_size` is `int` (`:352`), guarded by `:393 testdata.len > INT_MAX` refusal | 
| fail-closed verdict | `:534-546 return 1` with `errorLevel 2`, no `hAssessed` | agrees (upstream #252 family) |
| h_assessed = min(ws, ws*H_bitstring, H_original) | `:455-463` | agrees |

### 2.3 ea_restart (`cpp/restart_main.cpp`)

| Spec step | Code | Agreement |
|---|---|---|
| §3.1.1 item 3: exactly 1000x1000 | `:694 if (data.len != MIN_SIZE)` refuse | agrees; NO `EA_ALLOW_SHORT_DATASET` escape here (correct: the matrix shape is fixed) |
| row/column datasets (§3.1.4.1) | `:763-787` `rdata[i*r+j]`, `cdata[j*c+i]` with `r = c = 1000` (`:370`) | agrees only because r == c; index arithmetic uses `r` where the stride is `c` |
| §3.1.4.3 steps 1-5 | `:740-759`; `alpha = 0.000005` (`:740`), `X_cutoff = exactMultinomialMaxBound` (`:754`) with `X_cutoff_printed` beside it | DOCUMENTED DIVERGENCE `C23` (B) -- not re-reported |
| §3.1.4.2 `min(H_r,H_c) < H_I/2` fails | `:1177` | agrees |
| §3.1.4.2 result = min(H_r,H_c,H_I) | `:1222` (printed only; JSON carries h_r, h_c, h_i separately) | agrees |
| H_I argument | `parseHIArgument :160-187`; `H_I <= 0` refused (`:581`); `/bit` scaling `:638`; bare number refused for ws>1 (`:640`); `H_I > ws` refused (`:660`) | documented `C16`; see 4.6 for the inferred-width hazard |
| `-s <simulation count>` | usage text `:205-206`: "Accepted for compatibility and ignored"; code `:449-458`: `if (!parse_unsigned_decimal) usage; if ((inul==0)\|\|(inul==ULONG_MAX)\|\|(inul < simulation_rounds)) print_usage(); else simulation_rounds = inul;` then `:753 (void) simulation_rounds;` | DISAGREEMENT WITH ITS OWN DOCUMENTATION: values below 5,000,000 (DEFAULT_SIMULATION_ROUNDS, `:27`) and 0 are REFUSED with a bare usage dump and no reason line; values >= 5,000,000 are accepted and ignored. MEASURED: `restart-s-1000 rc=255`, `restart-s-4999999 rc=255`, `restart-s-0 rc=255` (usage, no reason); `restart-s-5000000 rc=255` and `restart-s-6000000 rc=255` proceed to "Error reading file" (i.e. accepted). |

### 2.4 NaN in the aggregation (`std::min` semantics) -- cross-reference F13

`std::min(a, b)` returns `(b < a) ? b : a`. With `H_bitstring = min(ret, H_bitstring)`:
- `ret = NaN` -> `(H < NaN)` false -> returns NaN: H_bitstring becomes NaN.
- next estimator `min(ret2, NaN)` -> `(NaN < ret2)` false -> returns ret2: every minimum before the NaN is DISCARDED.
- final `h_assessed = min(h_assessed, NaN*ws)` -> `(NaN < ws)` false -> returns `h_assessed` = word_size: the entire bitstring bound vanishes.
Only MCV (`:365`) and Markov (`:418`) are unguarded (the `>= 0` guards elsewhere treat NaN as "not run",
which is the safe reading). F13 is UNCONFIRMED in the tracker ("no NaN producer at >= 10^6 in any tool");
this is recorded as the aggregation hazard the CLI files carry, direction OVERSTATES if a producer exists.
The estimator agents own the producers; the one-line hardening here is `if (std::isnan(ret)) -> not_run`.

---

## 3. Exit paths, enumerated (code in parentheses; `exit(-1)` and `return -1` are status 255)

### ea_non_iid
| Path | Line | Status | Report at `-o`? |
|---|---|---|---|
| option after operand (OC-104) | `:138-141` | 255 | nothing written |
| `--version` before first operand, before any unknown option | `:142-145` | **0** | nothing written (documented option; `version-then-Z rc=0` -- `--version -Z` prints the banner and exits 0 because the version precedes the unknown option, `versionOptionRequested` TestRunUtils.h:321) |
| `-o` aliases input (prescan) | `:156-158` | 255 | none |
| unknown short option / `--x` long option | getopt `?` -> `print_usage :236` -> `exit(-1) :64` | 255 | placeholder only if `-o` was parsed earlier |
| `-l` malformed / count 0 | `:182-224` | 255 | error report if `-o` already seen |
| `-o` claim fails (unwritable) | `:233` | 255 | none |
| argc not 1 or 2 | `:244-247` | 255 | placeholder if `-o` seen |
| `-o` aliases input (authoritative) | `:264` | 255 | placeholder |
| bits_per_symbol invalid | `:271-281` | 255 | error report |
| read_file_subset false | `:291-297` | 255 | **writes testRun as-is**: see 3.4 |
| fewer than 10^6 samples | `:320-327` | 255 | error report, `errorClass input` |
| alphabet size 1 | `:329-342` | 255 | error report |
| success, report unwritable | `:686-689` | 255 | placeholder stays |
| success | `:693` | **0** | full report |
| `assert` inside an estimator | SIGABRT | 134 | placeholder stays (C14) |

### ea_iid: identical shape (`:133-154`, `:156-235`, `:241-244`, `:261`, `:268-279`, `:287-294`, `:320-327`, `:329-341`, `:393-408` INT_MAX refusal -> 255), plus
`:534-546` IID battery failed -> **1** (report `errorLevel 2`, no `hAssessed`), `:578-581` report unwritable -> 255, `:585` -> 0.
`seed()` (`utils.h:794-811`) exits 255 if `/dev/urandom` cannot be opened/read -- after the report target was
claimed, so the placeholder stays (fail-closed).

### ea_restart: `:407-414` refusal/version, `:425-427` alias, getopt default `:460`, `-s` refusals `:451-456`,
argc `:469-472`, alias `:484`, bits `:506-521`, H_I parse `:547-575`, `H_I <= 0` `:581-598`, read_file `:601-624`,
bare H_I at ws>1 `:640-657`, `H_I > ws` `:660-675`, alphabet 1 `:677-692`, `len != 10^6` `:694-708`, malloc `:717-733`,
sanity fail `:810-825` (255), IID battery fail `:1149-1167` (**1**), validation fail `:1177-1193` (255),
report unwritable `:1211-1218` (255), success `:1227` (0).

### 3.1 Can any FAILURE exit 0?
No path that fails to assess returns 0 except the documented `--version`. The two test escapes that return
0 after a non-compliant run both mark themselves (`EA_ALLOW_SHORT_DATASET` -> `nonCompliantShortDataset`;
quiet mode prints nothing but the JSON still carries the flag). MEASURED: `quiet-success rc=0` with a 2,000-sample
file under the escape prints only the escape warnings (so `-q` is not silent under the escape -- harmless).

### 3.2 Status channel vs report channel: one disagreement (SOURCE-CONFIRMED, not executed)
`utils.h:523-532` (read_file_subset, bsymbols malloc failure):
```
dp->bsymbols = (uint8_t*)malloc(dp->blen);
if(dp->bsymbols == NULL){
    printf("Error: failure to initialize memory for bsymbols\n");
    free(dp->symbols); ... return false;
}
```
sets NEITHER `testRun->errorLevel` NOR `errorMsg`, unlike every other failure branch in that function and
unlike the same branch in `read_file` (`utils.h:710-720`, which does set `errorLevel = -1`). The caller
(`non_iid_main.cpp:291-297`, `iid_main.cpp:287-294`) then does `if (jsonOutput) writeJsonReport(outputfilename,
testRun.GetAsJson())` -> a report with `errorLevel: 0`, `filename`, `sha256`, `assessedSampleCount` (identity
was recorded at `:449` BEFORE the bsymbols malloc) and an EMPTY `testCases` array, exit 255. A consumer keyed
on `errorLevel == 0` reads success. Reachable only when `malloc(len)` and `malloc(len)` succeed and
`malloc(len*word_size)` fails -- i.e. a large 8-bit capture near the memory limit. Direction: no figure is
overstated (there is no `hAssessed`), but it is the "errorLevel 0 with nothing assessed" class C14 exists to
close. Severity MEDIUM (report channel fail-open), confidence HIGH on the source, NOT reproduced.
How to test: Linux with `ulimit -v` sized between 2*len and (2+ws)*len bytes on a 1e6-sample 8-bit file with
`-o r.json`; assert `errorLevel != 0` in r.json. (macOS ignores RLIMIT_AS for malloc; use a `DYLD_INSERT_LIBRARIES`
malloc shim that fails the third allocation of exactly `blen` bytes.)

### 3.3 The "narrower than described" warning never reaches the report
`utils.h:483-485`: `printf("Warning: Symbols appear to be narrower than described."); testRun->errorMsg = "Warning..."`
with `errorLevel` left 0; `GetBaseJson` (test_run_base.h:70-73) emits `errorMessage` only when `errorLevel != 0`.
So `bits-[08]` (1-bit data declared 8) prints the warning to stdout and the JSON carries `bitsPerSymbol 8,
bitsPerSymbolInferred false` and no warning. MEASURED `bits-[08] rc=0`. Conservative in effect (H_original <= 1
bit per 8-bit symbol), LOW; recorded because a declared-width mistake is invisible to a JSON-only consumer.

---

## 4. Option parsing: what was tried and what the code does

Optstrings are identical across the four argv readers in each tool (refuse / version / prescan / getopt):
non_iid `"icatvql:o:"` (`:138,:142,:154,:161`), iid `"icatvl:qo:"` (`:133,:137,:149,:156`), restart `"invqo:s:"`
(`:407,:411,:422,:430`). One shared walk `scanArgs` (TestRunUtils.h:174-223) feeds all three (OC-104's design).

4.1 **Missing flags**: no required flag; `argc` after getopt must be 1 or 2 (restart: 2 or 3). `ea_restart file 8`
is read as `<file> <H_I=8>` with an inferred width; refused by C16 at ws>1 (`:640`) and by `H_I > ws` at ws=1 (`:660`).

4.2 **Repeated flags**: `-v -v` increments; `-q` forces `verbose = 0` regardless of order (`:250-252`); repeated
`-l` -- last wins; repeated `-o` -- EVERY target is claimed with the fail-closed placeholder (`:233`) and only the
last receives the report. MEASURED `repeated-o rc=0`: `a.json` = placeholder (`errorLevel -1`, "Refuse this file"),
`b.json` = full report (`logs/analysis-cli-repeated-o-{a,b}.json`). Fail-closed; LOW.

4.3 **Conflicting flags**: `-i -c` and `-c -i`, `-a -t`: last wins, no diagnostic. MEASURED: `i-then-c` printed
`h': 0.790686` (conditioned mode), `c-then-i` printed `H_original: 0.790686`. LOW (operator error is silent).

4.4 **`-l` with bad values**: `5,` / `,5` / `5` / `0,0` -> 255 with the N-08/#260 messages (MEASURED).
`-l 18446744073709551615,1` -> "offset ... at or past the end" 255. `-l 0,18446744073709551615` -> ACCEPTED
(`rc=0`): index 0 passes the overflow guard `utils.h:374` (`0 > ULONG_MAX/size` is false), `len = min(fileLen, ULONG_MAX)`
= whole file, JSON records `subsetRequestedSamples 18446744073709551615`. Harmless; the record is honest.

4.5 **bits_per_symbol**: `0`, `9`, `1.0`, `"1 "`, `" 1"`, `256`, `2^64` -> 255 "Invalid bits per symbol"
(`parse_unsigned_decimal` utils.h:51-67 rejects leading space, sign, suffix, ERANGE). `01` -> accepted as
decimal 1 (N-08 decision: leading zeros keep decimal meaning), `08` -> 8 with the warning of 3.3. MEASURED.

4.6 **A negative number after the file operand**: `argLooksNumeric` (TestRunUtils.h:167-172, `strtod` must consume
the whole argument) exempts it from the OC-104 refusal. MEASURED: `ea_non_iid /nonexistent -1` -> "Invalid bits per
symbol" 255 (BSD getopt stops at the operand); `ea_restart -n f 1 -0.5` -> "H_I must be a finite decimal number:
'-0.5' (not a decimal number)" 255; `-inf` likewise. On glibc the same lines go through getopt's invalid-option
path (documented `OC-40` residue). Both refuse. Note `strtod` also accepts `-0x1p3`, `-infinity`, `-nan(x)`:
all refused downstream by `parseHIArgument`/`parse_unsigned_decimal` on BSD and by getopt on glibc.

4.7 **`--` already present, then an option-shaped operand** (`ea_non_iid -i -- /nonexistent 1 -q`): MEASURED
`dashdash-then-late-q rc=255` with the OC-104 message "... what this command line MEANS depends on the C library
... separate the operands with '--'". After `--` NEITHER glibc nor BSD permutes, so the stated reason is false
for this shape and the advice is already satisfied. Cause: `scanArgs :183` consumes the pre-operand `--` and the
late-option loop `:214-222` only stops at a `--` that appears AFTER the first operand. Both platforms would have
refused anyway (argc 3 -> usage), so this is a wrong-reason refusal. LOW; `regression-option-order.sh` tests
`-- capture.bin 1` without a trailing option-shaped operand, so it cannot see this.

4.8 **`-s` in ea_restart**: see 2.3. Documented as ignored; refuses `< 5,000,000` and `0` with a bare usage dump
(no reason line, unlike every other refusal). LOW (wrong refusal with no explanation; the documented text is
false). `regression-restart.sh:88-96` tests only the N-08 shapes (`5000000x`, `+5000000`, `0x5000000`) and so
cannot see it.

4.9 **`/bit` with an inferred width** (`ea_restart data.bin 0.9/bit`, no `bits_per_symbol`): `H_I = H_I * data.word_size`
(`:638`) where `word_size` was INFERRED from the restart data (`read_file`, utils.h:643-656). If the device is 8-bit
but the matrix happens to use only the low 4 bits, H_I becomes 3.6 instead of 7.2: the sanity cutoff is computed
at p = 2^-3.6 (HIGHER cutoff, more permissive -- fails to reject a source that the intended H_I would have rejected)
and the validation gate `min(H_r,H_c) < H_I/2` is easier to pass. The awarded figure `min(H_r,H_c,H_I)` is capped
at 3.6 per symbol, so the final number is not overstated, but the two gates are weakened by the data choosing the
scale. SUSPICION, LOW-MEDIUM, operator-error amplification rather than a spec deviation. Hardening: refuse `/bit`
unless `bits_per_symbol` was given explicitly (`bitsPerSymbolGiven != 0`, `:600`).

4.10 **`ea_restart -q` is not quiet**: `:735 printf("H_I: %f\n", H_I);` is unconditional. LOW, SOURCE-CONFIRMED only
(a run needs a 1e6 matrix, which is a heavy job in this phase).

4.11 **Environment knobs compiled into production binaries**: `EA_ALLOW_SHORT_DATASET` (documented test escape, marks
the report), `EA_TEST_RANDOM_SOURCE` (TestRunUtils.h:129-130, OC-121: redirects the temp-suffix random source; a
file of zeros makes every report write REFUSE, a file of a known constant makes the temp name predictable, which is
the F03 hazard re-opened by whoever controls the environment -- the operator, so LOW), `EA_TEST_INPUT_IDENTITY_MARKER`
(only under `-DEA_TEST_INPUT_IDENTITY_HOOK`, absent from production). OMP_NUM_THREADS: ea_non_iid has NO `#pragma omp`
(grep over cpp/non_iid, cpp/shared, non_iid_main.cpp: none), so its result cannot depend on thread count; ea_iid's
permutation battery and (unused in production) `simulateBound` jump the RNG by `omp_get_thread_num()` and are
urandom-seeded, so they are nondeterministic by design (BUILDING.md says so).

---

## 5. Build flags, dependency pins, and what changes a result per machine

5.1 **Makefile probe temp path is fixed and predictable** (`cpp/Makefile:45,49`):
`/tmp/.ea_fs_$$.c` and `/tmp/.ea_wf_$$.c`. In GNU make `$$` is a single `$`, so the shell receives `/tmp/.ea_fs_$.c`,
and `$.` is not a parameter expansion -- the path is LITERALLY `/tmp/.ea_fs_$.c` for every build on the machine.
MEASURED with a two-line makefile in the scratchpad: `shell-expanded=/tmp/.ea_fs_$.c`, `recipe-expanded=/tmp/.ea_fs_$.c`.
Consequences: (a) two concurrent builds race on the same file; (b) the `printf > /tmp/.ea_fs_$.c 2>/dev/null` follows
a planted symlink and its failure is silenced, after which `$(CXX) -x c++ -ffloat-store -c /tmp/.ea_fs_$.c` compiles
whatever is there: if the pre-existing file does not compile, clang's error output does not match the grep and
`FLOAT_STORE` is set to `-ffloat-store` on a compiler that will then FAIL the build under
`-Werror=ignored-optimization-argument` -- a denial of build, not a wrong figure; on GCC (which honours the flag) a
sabotaged probe can only ADD the flag, never drop it, so no numeric effect. LOW (build hygiene; the fix is
`mktemp`). Not the cause of the sha change (see 6).

5.2 **The dependency pin for OpenSSL is not honoured by the include/link order** (`Makefile:71-72`):
`INC += -I$(BREW_PREFIX)/include -I$(OPENSSL_PREFIX)/include` and `LDFLAGS += -L$(BREW_PREFIX)/lib -L$(OPENSSL_PREFIX)/lib`.
`/opt/homebrew/include` and `/opt/homebrew/lib` come FIRST, and Homebrew links the UNVERSIONED `openssl` formula there.
Today that is `openssl@4` (`/opt/homebrew/include/openssl -> ../Cellar/openssl@4/4.1.0/include/openssl`,
`/opt/homebrew/lib/libcrypto.dylib -> ../Cellar/openssl@4/4.1.0/lib/libcrypto.dylib`, both created 19:28:44-46).
MEASURED: `otool -L` on all three production binaries shows `/opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib`;
the October builds in the same directory (`ea_conditioning` 2026-10-20, `ea_transpose` 2026-10-15) show
`/opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib`. BUILDING.md's dependency table ("openssl@3 3.6.4") is therefore
FALSE for the binaries now in `cpp/`. OpenSSL is used only for the SHA-256 of the assessed bytes (`utils.h`
`record_assessed_data_identity`, EVP), so no estimator figure moves, but the binary's dependency differs from the
documented and pinned one and from the blessed build. MEDIUM (nondeterministic build input; a pin that cannot pin).
Fix: put `-I$(OPENSSL_PREFIX)/include` / `-L$(OPENSSL_PREFIX)/lib` BEFORE the generic prefix, or link
`$(OPENSSL_PREFIX)/lib/libcrypto.dylib` by path, and have `pin-check.sh`/`buildstate-lib.sh` print `otool -L | grep crypto`.

5.3 **`-march=native` on x86 (`Makefile:52-54`, default `ARCH=x86` everywhere but Darwin/arm64)** ties the binary to
the build host's ISA; with FMA present, GCC contracts `a*b+c` even at `-std=c++11 -O2` (BUILDING.md "Why the low
digits differ" MEASURED fmadd emission for GCC 16 and Apple clang 21 on arm64). So an x86 build on an FMA host and
one on a non-FMA host (or a VM without FMA passthrough) are different arithmetic. The x86 CI runner passes NIST's
reference exactly (OC-107), which fixes ONE point; the non-FMA x86 configuration is NOT RUN. Per-machine, documented
as a deliberate non-decision ("Adding -ffp-contract=off ... was deliberately not added"). Not re-reported; listed
in 6.3 as a measurement.

5.4 **`-ffloat-store` (OC-121)** is probed and dropped on clang; it never had an effect on clang (ignored) and has
none on x86-64 SSE or arm64. Zero codegen effect either way; `-Werror=ignored-optimization-argument` is diagnostic-only.
Neither can change a single byte of the output binary on this host.

5.5 **`long double` width and libm**: documented (BUILDING.md, known-platform-deltas.txt: eight 1e-10-scale predictor
deltas tolerated at 1e-9 on Darwin arm64 only). Not re-reported.

5.6 **Makefile forces `CXX = clang++` on Darwin (`:22`)** regardless of `CXX` in the environment, and the probes use
`$(CXX)`, so they are consistent with the compiler that builds. Fine. `brew --prefix` is evaluated at parse time
(`:23,:69,:70`): a missing brew falls back to `/opt/homebrew/...`.

5.7 Header dependencies are not tracked (`iid: iid_main.o` whose recipe writes `ea_iid`, never `iid_main.o`), so
`make` ALWAYS rebuilds -- no stale-object hazard, at the cost of a full compile each time.

---

## 6. The sha256 change (b61cf8c7.. -> 1ad1568c.. for ea_non_iid) with no C++ change since 2026-10-26

### 6.1 Timeline measured on this host (Homebrew INSTALL_RECEIPT times, file mtimes)
```
19:28:16  z3 5.3.3            installed as a dependency
19:28:22  llvm 23.1.5         dependency
19:28:36  lld 23.1.5          dependency
19:28:41  openssl@4 4.1.0     dependency            <-- new formula on this machine
19:28:44  /opt/homebrew/include/openssl -> openssl@4   (symlink mtime)
19:28:46  /opt/homebrew/lib/libcrypto.dylib -> openssl@4
19:28:50  sqlite 3.54.1       dependency
19:28:52  cpp/ea_iid          linked
19:28:53  python@3.15 3.15.2  dependency
19:28:57  cpp/ea_non_iid      linked
19:29:04  cpp/ea_restart      linked
19:29:08  afl++ 5.03c         installed ON REQUEST  <-- the audit's fuzzer (BUILD-LINES.md)
```
Installing AFL++ for this audit pulled `openssl@4` in as a transitive dependency, Homebrew re-pointed the generic
prefix symlinks, and the production binaries were rebuilt seconds later (concurrently or immediately after).

### 6.2 Candidates, ranked
1. **OpenSSL 3 -> 4 relink (CERTAIN, measured).** The `LC_LOAD_DYLIB` string changed from
   `/opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib` to `/opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib`
   (`otool -L`), and `ea_non_iid`/`ea_restart` were compiled against OpenSSL 4.1.0 headers (the include symlink moved
   at 19:28:44, before their compiles started). That alone changes the sha256. Mechanism: 5.2.
2. **Toolchain/SDK moved (CERTAIN that it differs from the October builds; UNKNOWN whether it differs from the blessed
   build).** `LC_BUILD_VERSION sdk 27.2` on today's binaries vs `sdk 27.0` on `ea_conditioning` (Oct 20) and
   `ea_transpose` (Oct 15); libc++ link version 2200.32.0 vs 2200.27.0; libSystem 1359.40.3 vs 1359.0.0. Xcode 27.2
   (27B52) is installed now. If Xcode was updated between the blessed build and today, codegen differs.
3. **Stale blessed binaries (UNKNOWN).** The last source change is `b53ff5d` 2026-10-26 08:16 (`cpp/shared/TestRunUtils.h`
   OC-121 random-source refusal, and `cpp/Makefile`). If the blessed sha was recorded against a build older than
   `b53ff5d` (e.g. at `36cafb3` OC-104, 2026-10-25), the rebuild legitimately differs. The repository does not contain
   the string `b61cf8c7` anywhere (grep over the working tree including ignored files), so the blessing is in an
   external log and its commit cannot be read here.
4. **Makefile flag probing (OC-121) -- RULED OUT as a byte-changer on clang.** Both probe outcomes are diagnostic-only
   on this compiler (5.4). The build log `logs/build-rebuild-2026-11-07.log` shows the line without `-ffloat-store`
   and with `-Werror=ignored-optimization-argument`, exactly as BUILD-LINES.md records.
5. **Non-reproducible link -- RULED OUT.** No `__DATE__`/`__TIME__`/`__TIMESTAMP__` in `cpp/*.cpp`, `cpp/shared`,
   `cpp/non_iid`, `cpp/iid` (grep). Mach-O executables carry no link timestamp; `LC_UUID` is a content hash under ld64.
   Identical inputs give identical bytes.

### 6.3 What to measure (none run here: each is a build or a heavy run)
- a. Rebuild out of tree with BUILD-LINES.md's exact line but `-I/opt/homebrew/opt/openssl@3/include` and
  `-L/opt/homebrew/opt/openssl@3/lib` placed FIRST (or `-lcrypto` replaced by the openssl@3 dylib path); compare
  `sha256` and `otool -L` with `1ad1568c..` and, if any copy survives, with `b61cf8c7..`. If the blessed binary is
  gone, compare `strings -a` of the two for the libcrypto path and for the OC-121 message "cannot read randomness from".
- b. Confirm the blessed build's commit: find the suite log that recorded `b61cf8c7..` and its `[build-state]` line
  date; compare with `b53ff5d`'s date (2026-10-26 08:16 -0400).
- c. Run `cpp/selftest/regression-subset.sh` and `regression-input-identity.sh` against the new binaries: they
  compare the report's `sha256` field with `shasum`, which is the only OpenSSL-dependent output. A match shows the
  OpenSSL 4 relink changed no reported value.
- d. Run `selftest --allow-known-platform-deltas` and `pin-check.sh` against `1ad1568c..`: the figures must be
  unchanged to the recorded deltas (the SDK move is the only candidate that could touch codegen).
- e. On x86 CI: build once with `-march=x86-64` (no FMA) and once with `-ffp-contract=off`, run
  `tools/compare-nist-reference.sh`, and record the deltas -- the non-FMA x86 configuration is otherwise NOT RUN.
- f. Record `otool -L` / `ldd` output in `buildstate-lib.sh`'s precondition line so a dependency swap is visible
  the next time it happens.

---

## 7. Prior repairs touching this component, and how to try to break each

| Repair | What it claims | Break attempt |
|---|---|---|
| OC-104 option-after-operand refusal (`refuseOptionAfterOperand`, regression-option-order.sh) | one command line means one thing on both platforms | (i) `-- file 1 -q`: refused for the WRONG reason (4.7, MEASURED); (ii) a non-numeric option-shaped operand that `strtod` fully consumes: `-infinity`, `-nan(abc)`, `-0x1p3` are exempt as "numeric" and go to getopt on glibc as options `-i -n -f ...` -- on glibc `ea_restart -n f 8 -0x1p3` is `-0`?`x`?... every letter must be in the optstring to be parsed; here `0` is not, so it is refused. Try `-inf` on glibc for ea_restart: `-i -n -f` -> `f` unknown -> refused. Try an argument built only from optstring letters that `strtod` accepts: none exist (`strtod` needs a digit, `.`, `inf` or `nan`; `i`,`n` are restart options but `f` is not). Residue is as documented (`OC-40`). (iii) `POSIXLY_CORRECT=1` on glibc makes getopt stop permuting, so the refusal then fires on lines glibc would have treated as BSD does -- the refusal is now stricter than either libc, by design. |
| A04/F04 `--version` prescan (`versionOptionRequested`) | version only before the first operand, after no unknown option | `--version -Z` -> banner, exit 0 (MEASURED): the version wins over a LATER unknown option. Harmless (operator asked for the version) but it is exit 0 on a malformed line; whether that is a hole depends on whether a harness ever appends options. |
| A05/F03 alias guard + atomic write (`outputTargetIsSafe`, `writeJsonReport`) | the input can never be truncated | (i) `-o` pointing at a HARD LINK of the input: `stat` identity (dev,ino) equal -> refused. (ii) `-o dir/` where `dir` is a symlink to the input's directory and the temp name collides: random suffix, O_EXCL -> cannot collide. (iii) `EA_TEST_RANDOM_SOURCE=/dev/zero`: `r2 == 0` -> refuses to write (fail-closed). (iv) `EA_TEST_RANDOM_SOURCE=<file of 8 known bytes>`: temp suffix becomes `time^pid<<16` + constant -> predictable; pre-creating the temp makes `O_EXCL` fail -> 8 attempts all collide -> "could not create a temporary output file" -> 255, input untouched. Still fail-closed; the knob exists in production, which is the only weakness. |
| C14 placeholder claim at `-o` parse | no stale success survives | repeated `-o`: the FIRST path keeps a permanent "Refuse this file" placeholder (MEASURED). A harness that passes `-o` twice by mistake reads a refusal where a report was expected -- fail-closed. |
| N-08 strict decimal parsing | no permissive numeric parse | `01`/`08` accepted as 1/8 (decision); `1.0`, `" 1"`, `"1 "`, `+8`, `0x8`, `8x`, `2^64` refused (MEASURED). `-l 0,ULONG_MAX` accepted (4.4) -- correct arithmetic, odd record. |
| N-04/C16 H_I grammar | finite, positive, scaled | `/bit` with inferred width (4.9): accepted and scaled by the data's width. `1e-300` accepted: `p = 2^-1e-300` rounds to 1.0L -> `printedBinomialBound` returns 1000, `exactMultinomialMaxBound` returns 1000, sanity check cannot fail, validation `min(H_r,H_c) < 5e-301` cannot fail, awarded figure `min(H_r,H_c,1e-300)` = 1e-300 -- conservative. |
| §3.1.1 intake (`dataset_meets_minimum`, regression-minsize.sh) | < 10^6 refused on the LOADED count | `-l` subsets: counted after loading (MEASURED earlier by the intake agent: `subset-last1 rc=255`). `-c` on an 8-bit conditioned file of 125,000 bytes (= 10^6 bits, which §3.1.1 item 2 counts as "conditioning component outputs") is refused because the check counts SYMBOLS: over-strict, conservative. `EA_ALLOW_SHORT_DATASET=true`/`yes` -> not "1" -> refused (string compare, `utils.h:300`). |
| OC-121 random-source refusal | no derivable temp name | see A05 row (iv). |
| C18 LLP64 `n_choose_2` | Windows LRS | `long len`/`long blen`/`ftell` remain 32-bit on LLP64: a >2 GiB capture on Windows wraps `fileLen` (`utils.h:351`) -- documented as "a sweep of the remaining long arithmetic has not been done" (A.1 C18). Not re-reported; listed as the open sweep. |

---

## 8. Edge-case inputs that distinguish a correct from an incorrect implementation of THIS component

1. **`-c` scale probe (overstatement by misreading)**: any 8-bit conditioned file (e.g. `bin/rand8_short.bin 8` under
   the escape, as the output agent did). Correct consumer behaviour: `hAssessed / dataWordSize == hBitstring`
   (5.8609 / 8 = 0.7326). An incorrect consumer -- or a report that ever drops `dataWordSize` -- reads 5.86 "bits per
   bit". Construction: 2,000 bytes random, run `-c -o r.json f 8`; assert the three fields' relation.
2. **NaN aggregation probe (F13; CRITICAL if a producer exists)**: an out-of-tree build with `markov_test` mutated to
   return `NAN` on a 2,000-sample 8-bit file; a correct aggregation reports `hAssessed <= min(MCV, collision)` of the
   bitstring; the current `std::min` chain reports `hAssessed = min(word_size, H_original)` with the whole bitstring
   bound dropped. This is a mutation test of the aggregation, not a claim of a reachable NaN.
3. **bsymbols-malloc report probe (3.2)**: 1e6-sample 8-bit file, `ulimit -v` or a malloc shim failing the third
   allocation; correct: `errorLevel != 0` in the JSON; current: `errorLevel 0`, empty `testCases`, exit 255.
4. **`/bit` with inferred width (4.9)**: a 1000x1000 matrix of 8-bit samples that uses only values 0..15, run
   `ea_restart -n M.bin 0.9/bit` (width omitted). Correct (hardened) tool refuses or uses 8; current tool prints
   `H_I: 3.600000` and computes the cutoff at p = 2^-3.6. Needs a 1e6 input: heavy, for the execution phase.
5. **`-s` documentation probe**: `ea_restart -n -s 1000 f 1 0.5` -> usage dump, no reason (MEASURED). Correct per the
   usage text: accepted and ignored.
6. **`--` then option-shaped operand**: `ea_non_iid -i -- f 1 -q` -> refused "depends on the C library" (MEASURED);
   correct: "Incorrect usage" (3 operands), or the refusal without the false reason.
7. **Repeated `-o`**: `-o a.json -o b.json f 1` -> `a.json` placeholder forever (MEASURED). A correct tool either
   refuses the second `-o` or does not claim the first.
8. **Dependency pin probe**: `otool -L cpp/ea_non_iid | grep crypto` must name `openssl@3` while BUILDING.md says so;
   today it names `openssl@4` (MEASURED).
9. **Build-probe temp path**: `ls -la /tmp/.ea_fs_\$.c` during a build; a correct Makefile uses `mktemp`.
10. **Width mismatch, declared wider (conservative)**: 1-bit data declared 8 -> runs with `word_size 8`, `alph 2`,
    `hAssessed <= 1` per 8-bit symbol; the JSON does not carry the warning (MEASURED `bits-[08] rc=0`).

---

## 9. Suspected deviations, ranked (the worst would overstate)

| # | Title | Direction | Severity | Confidence | Status |
|---|---|---|---|---|---|
| 1 | `-c` report `hAssessed` is per packing symbol (n x h') while stdout `h'` is per bit; a per-bit reading overstates up to 8x (F23 UNCONFIRMED in tracker) | overstates (consumer-dependent) | MEDIUM here (CRITICAL if ShannonPad reads it per bit) | high that the factor exists (measured 5.8609 = 8 x 0.7326); low that any consumer misreads it | MEASURED factor; consumer unknown |
| 2 | NaN from an unguarded estimator (MCV/Markov) discards earlier minima and the whole bitstring bound (F13) | overstates | MEDIUM (CRITICAL if a producer exists at >= 10^6) | high on the `std::min` semantics; low on reachability | SOURCE-CONFIRMED; mutation test proposed |
| 3 | `read_file_subset` bsymbols-malloc failure writes an `errorLevel 0` report with no test cases, exit 255 | neutral (report-channel fail-open) | MEDIUM | high (source), not reproduced | SOURCE-CONFIRMED |
| 4 | OpenSSL pin not honoured: generic Homebrew prefix precedes the pinned openssl@3 on both -I and -L; production binaries now link openssl@4 contrary to BUILDING.md | nondeterministic (build input) | MEDIUM | high | MEASURED (otool -L, receipts) |
| 5 | `ea_restart /bit` with an INFERRED width lets the data choose the H_I scale; weakens the sanity and validation gates | neutral on the awarded figure; permissive on the gates | LOW-MEDIUM | medium | SOURCE-CONFIRMED; needs a 1e6 matrix |
| 6 | `-s` documented "accepted and ignored" but refuses < 5,000,000 and 0 with a bare usage dump | wrong refusal, no reason | LOW | high | MEASURED |
| 7 | OC-104 refusal fires on `-- f 1 -q` with a false reason | wrong-reason refusal | LOW | high | MEASURED |
| 8 | Makefile probe temp path is the fixed `/tmp/.ea_fs_$.c` | build hygiene; possible denial of build | LOW | high | MEASURED (make expansion) |
| 9 | Repeated `-o` leaves a permanent placeholder at the first path | fail-closed | LOW | high | MEASURED |
| 10 | `ea_restart -q` still prints `H_I:` | cosmetic | LOW | high | SOURCE-CONFIRMED |
| 11 | "narrower than described" warning never reaches the JSON | conservative | LOW | high | MEASURED |
| 12 | `-i -c` / `-a -t` conflicts resolve silently to the last flag | neutral | LOW | high | MEASURED |
| 13 | `--version -Z` exits 0 with a banner on a malformed line | neutral | LOW | high | MEASURED |
| 14 | x86 `-march=native` + FMA contraction: non-FMA x86 configuration NOT RUN | nondeterministic across machines | LOW (documented non-decision) | high on mechanism; unmeasured magnitude | NOT RUN |

DOCUMENTED DIVERGENCES encountered and not reported: OC-104 (refusal itself), C23, C22c, D-6 (width refusal),
F01 (binary by alphabet), F20 (`-t` under `-c`), F21 (bit order), the >= 10^6 intake, the fail-closed IID battery,
`EA_ALLOW_SHORT_DATASET`.

## 10. Probe record
Script `logs/analysis/cli-probe.sh`; corpus `corpus/cli-rand1-2000.bin` (sha256 in `logs/analysis-cli-corpus-sha256.log`);
binaries `logs/analysis-cli-binaries-sha256.log`; exit statuses `logs/analysis-cli-exitcodes.log` (36 labelled rows);
per-case output `logs/analysis-cli-<label>.log`; JSON `logs/analysis-cli-repeated-o-{a,b}.json`.
Build provenance: `otool -L`, `otool -l` (LC_BUILD_VERSION), Homebrew `INSTALL_RECEIPT.json` times and symlink
mtimes as quoted in 6.1; make-expansion test file `scratchpad/mk-dollar-test.mk`.
