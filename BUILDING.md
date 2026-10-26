# Building `ea_non_iid` from this fork

This fork began as a reliable `ea_non_iid` build for macOS and Windows that
changed nothing able to alter a reported min-entropy figure. **It is no
longer only that.** After the defects reported upstream from this fork's
audit were reviewed on the upstream threads by @joshuaehill (not a NIST
account; see NOTICE, "Correction of upstream attributions"), the estimator
sources were corrected here too, so they are no longer byte-identical to
upstream. What that means in practice is in
"Repairs made in this fork" below; every change is listed, with dates, in
[NOTICE](NOTICE), and the per-finding status is in
[audits/2026-09-30/FINDINGS-TRACKER.md](audits/2026-09-30/FINDINGS-TRACKER.md).

**Correction (2026-10-02).** Until 2026-10-02 this introduction and "Repairs made in this fork" said "After NIST reviewed the defects". The replies were @joshuaehill's; no NIST account has replied. NOTICE records the correction.

No estimator formula, cut-off, rounding rule or confidence bound was
altered. Two changes do alter results deliberately, F09 and N-01, and both
are described below.

Upstream baseline: `usnistgov/SP800-90B_EntropyAssessment` at
`87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`.

`ea_non_iid`, `ea_iid` and `ea_restart` are the supported build; the repairs
and regression suite cover all three. Plain `make` now builds exactly those
three. `cpp/selftest/regression-docs.sh` inspects the expanded forced dry-run
plan and fails if `ea_conditioning` or `ea_transpose` enters it, or if a
supported executable disappears. `ea_conditioning` remains an explicit
unsupported development target and is the one program that links GNU MPFR and
GMP (LGPL).
None of the three supported programs links either; see "LGPL isolation".

---

## macOS — verified 2026-09-30

Verified on: macOS 26.6.2, Apple silicon (arm64), Apple clang 21.0.0
(Xcode toolchain), GNU Make 3.81, Homebrew.

```sh
brew install libomp libdivsufsort jsoncpp openssl@3
cd cpp
make non_iid
cd selftest
./selftest                         # upstream's own regression check
./pin-check.sh --prove-nonvacuous  # this fork's pinned-output check
```

Package versions used for the verified build:

| Package        | Version | Role                                  |
|----------------|---------|---------------------------------------|
| libomp         | 23.1.2  | OpenMP runtime for Apple clang        |
| libdivsufsort  | 2.0.1   | suffix arrays (t-tuple, LRS)          |
| jsoncpp        | 1.9.8   | JSON report                           |
| openssl@3      | 3.6.4   | SHA-256 of the input file             |
| libbz2 (SDK)   | 1.0.8   | on the link line; unused by ea_non_iid|

The compile line `make non_iid` runs on this machine (for the record):

```
clang++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 -ffloat-store -I/usr/include/jsoncpp  -I/opt/homebrew/include -I/opt/homebrew/opt/openssl@3/include non_iid_main.cpp -o ea_non_iid -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto
```

Warnings you will see, all harmless and all upstream code:

- `optimization flag '-ffloat-store' is not supported` — clang ignores it.
  The flag only affects x87 (32-bit Intel) code generation; it is a no-op
  on x86-64 (SSE math) and on arm64 with any compiler. It is kept so the
  flag list stays identical to upstream.
- `variable length arrays in C++ are a Clang extension` (utils.h) and
  `'sprintf' is deprecated` (TestRunUtils.h).
- `expression result unused` at utils.h:184 and utils.h:226 — an upstream
  bug in an error-message string; see "Upstream observations".

### Why Apple clang and not Homebrew GCC

Upstream says GCC is the only tested compiler, so Homebrew GCC 16.2 was
tried first. It compiles but cannot link: Homebrew's `libjsoncpp.dylib`
is built against libc++ and exports `std::__1::basic_string` signatures,
while GCC emits libstdc++ `std::__cxx11::basic_string` references
(`Undefined symbols ... Json::StyledWriter::write[abi:cxx11]`). Apple
clang links every Homebrew library cleanly. The Makefile therefore
selects `clang++` on Darwin; every other platform keeps upstream's
`g++`.

### What the three Makefile commits do (and do not do)

1. Add Homebrew include/lib prefixes (`brew --prefix`, `brew --prefix
   openssl@3`) to `INC`/`LDFLAGS` on Darwin only.
2. On Darwin only, use `clang++`, replace the bare `-fopenmp` (rejected
   by Apple clang) with `-Xpreprocessor -fopenmp` plus libomp, and link
   `-lomp`.
3. On Darwin/arm64 only, default `ARCH` to `arm64` so the Makefile's
   x86-only `-march=native` is omitted, exactly as upstream already does
   for any non-x86 `ARCH`. Intel Macs and Linux keep `ARCH=x86`.

`-std=c++11 -O2 -ffloat-store` are untouched. No flag that changes
floating-point semantics (`-ffast-math`, `-ffp-contract`, `-mfma`, …)
was added or removed.

---

## Operator command line

```sh
cd cpp
./ea_non_iid -i -a -v  <capture.bin> <bits_per_symbol>
./ea_non_iid -i -a -q -o report.json <capture.bin> <bits_per_symbol>   # JSON report
```

- Give `bits_per_symbol` explicitly (1–8). If omitted the tool infers it
  from the data, which can change which estimators run on a marginal file.
- `-i` initial estimate, `-a` use all data. Both are the defaults; state
  them so the evidence is unambiguous. `-c` (conditioned data) and `-t`
  (truncate the bitstring to 1,000,000 bits) change the figure.
- The tool now **refuses** a dataset of fewer than 1,000,000 samples, which
  is the minimum SP 800-90B Section 3.1.1 requires. It exits nonzero and,
  with `-o`, writes a JSON report carrying `errorLevel` and `errorMessage`.
- **Every option must come BEFORE `<file_name>`.** This fork **refuses** a
  command line with an option after the file operand — a behaviour change from
  upstream, made 2026-10-25 (`OC-104`), and the one change here that will
  reject a command line that worked on Linux before it. The reason is measured,
  not stylistic: **glibc `getopt` permutes** such a line and parses the option,
  while **BSD/macOS `getopt` stops at the first operand** and treats it as
  another operand. So `ea_non_iid -i -a capture.bin 1 -q -o r.json` *assessed
  and wrote a report* on Linux and *died on the usage path* on macOS — one
  command line naming two different operations on two supported platforms, with
  every guard that reads the pre-`getopt` prescan unarmed on the permuting side.
  Rather than guess which was meant, all three tools now refuse it, name the
  offending argument, and print the correct form.
  - What still works unchanged: options before the file (every documented
    example, including the January re-pin procedure), `--version` on its own,
    and `--` to end the options explicitly.
  - **A negative number after the file is still a value, not an option**, so
    `ea_restart -n r8.bin 8 -1` and `... 8 -inf` reach the `H_I` parser as
    before. Those two are the only shapes an argv logger found among 256 real
    invocations of the full suite, and they are exempt by design.
  - If a script of yours puts options last, move them before the file. If an
    operand of yours genuinely begins with `-` and is not a number, put `--`
    before the operands.
  It used to warn on stdout and assess the data anyway with `errorLevel` 0.
  The count checked is the number of samples actually loaded, so a `-l`
  subset smaller than the minimum is refused too.
- `EA_ALLOW_SHORT_DATASET=1` permits a short run for test purposes only. It
  is not a documented command-line option and does not produce a compliant
  assessment: the run says so on stdout and sets `nonCompliantShortDataset`
  in the JSON. The three short samples under `bin/` need it, which is why
  the selftest harness sets it.
- `-v` shows the per-estimator figures; `-vv` prints them with 17
  significant digits (what selftest and pin-check parse).
- **The JSON report and the `-vv` banner embed the SHA-256 of the input
  file** (`sha256_file` in `cpp/shared/TestRunUtils.h`, field `sha256`).
  This is upstream behaviour and is intentionally left in; the consuming
  tool redacts it downstream. It remains a hash of the **whole file** even
  when `-l` selects a subset, which is what the upstream respondent
  (@joshuaehill) asked for on upstream #260; the subset itself is
  identified by the `subsetIndex`,
  `subsetRequestedSamples` and `subsetActualSamples` fields beside it.
- The JSON report also records `bitsPerSymbol`, the symbol width the
  assessment used, and `bitsPerSymbolInferred`, which says whether that
  width came from the command line or was inferred from the data.

Run-to-run determinism: `ea_non_iid` contains no OpenMP pragmas (they
are only in `ea_iid` and `ea_restart`), so it is single-threaded and
gives bit-identical output on repeated runs on the same binary. `ea_iid`
is not deterministic: its permutation tests seed themselves from
`/dev/urandom`, and on a marginal dataset the pass/fail verdict can
differ between runs of the same binary.

### Running the checks

```sh
cd cpp && make non_iid iid restart
cd selftest && ./run-all-checks.sh
```

`run-all-checks.sh` runs `pin-check.sh`, `selftest`, and every
`regression-*.sh` in that directory, and fails if any of them fails.

It **discovers** the regression scripts rather than listing them. That is
deliberate. An earlier version of this section listed them by hand and fell
six scripts behind, so anyone following it ran half the suite believing they
had run all of it. Adding a `regression-*.sh` file is now enough to get it
run; there is no list to update.

To check the documentation's own claims as well:

```sh
cd cpp/selftest && ./regression-docs.sh
```

That verifies what can be verified mechanically: commit SHAs resolve,
referenced paths and links exist, the tracker's counts match its own
sections, the pinned figure quoted in these documents matches both
`pin-check.sh` and the current build, no built program links MPFR or GMP, and
none of the claims that were previously corrected has reappeared.

> **WHAT THE REFERENCE SELF-TEST ESTABLISHED, AND WHAT IT DID NOT, BEFORE
> 2026-10-21 (`OC-74`).** Its comparator, `compareresults.pl`, filtered the
> report to lines matching the estimate labels, so *"Opening file"* and
> *"Loaded N samples of K distinct W-bit-wide symbols"* were **never
> compared**. Measured: a reference rewritten to claim a different file and
> *"42 samples of 3 distinct 2-bit-wide symbols"* compared **equal** to a real
> 1,000,000-sample 179-symbol 8-bit run.
>
> So every run of the reference self-test up to that date established **that
> some 98-ish estimate values agreed with some reference to within the stated
> epsilon** — and did **not** establish **that the reference described the
> input**. `selftest` pairs each output with a reference by a filename
> transform alone, so a mispaired or wrong-fixture reference is exactly the
> case it could not see. **No figure is thereby wrong, and none is thereby
> established either.**
>
> **The pinned figure did not rest on it.** `pin-check.sh` is independent: it
> binds its input by **SHA-256** (`SAMPLE_SHA256`, compared), asserts exactly
> one `Assessed min entropy` line, and compares against a literal expected
> value with a relative tolerance. The project's main cited number is unaffected.
>
> **What rested on it** is the agreement claim in this section and the
> precision-audit table below — the 1.3e-10 to 3.7e-10 deltas against NIST's
> reference data — and `audits/2026-09-30/AUDIT.md`'s *"selftest vs refdata ->
> max deltas 3.6e-15 .. 3.7e-10"*.
>
> **Re-run, and they stand.** With identity now compared, all **11 of 11**
> fixtures verify identity (`identity <file> / <samples> samples / <width>-bit
> matched`), zero mismatches and zero refusals, and the only failures are the
> same two known platform files. So the figures below are now established
> rather than merely unrefuted — but they were the latter until this run.

**`selftest` exits 1 on macOS arm64, and that is expected here.** Three
predictor values on `biased-random-bytes.bin` and `ringOsc-nist.bin`
differ from NIST's Linux reference data by 1.3e-10 to 3.7e-10 against an
epsilon of 1e-10. That is the platform difference recorded in upstream
issue #155 and in the precision audit below; it is not introduced by any
change here, and was previously invisible only because the harness
discarded the comparison's exit status. Every other sample passes and
every discovered regression script passes. On a Linux x86-64 build, selftest is
expected to pass outright.

---

## LGPL isolation (MPFR / GMP)

Finding: MPFR and GMP are linked only into `ea_conditioning`.

Evidence. The first two points were established at the upstream baseline
and re-checked after this fork's repairs; the third was re-run on
2026-10-01 against all three programs the fork now builds.

- `cpp/Makefile`: `COND_LIB = -lmpfr -lgmp` is passed only in the
  `conditioning` rule; `LIB` and `SHARED_LIB` (used by every program)
  name only bz2, pthread, divsufsort, divsufsort64, jsoncpp, crypto.
  Unchanged by the repairs.
- `grep -rln 'mpfr\|gmp' cpp/` → `cpp/Makefile`, `cpp/conditioning_main.cpp`
  only. No header under `cpp/shared/`, `cpp/non_iid/` or `cpp/iid/`
  includes them, and none of the repairs added such an include.
- Built binaries: for each of `ea_non_iid`, `ea_iid` and `ea_restart`,
  `otool -L` lists no MPFR or GMP library and
  `nm -u <binary> | grep -c -E '_mpfr|gmp'` → 0.

None of the three supported programs carries LGPL code. `make` (equivalently,
`make non_iid iid restart`) never compiles `conditioning_main.cpp`; MPFR and
GMP need not be installed to build or run the supported tools. The separate
`make conditioning` target is outside the supported product scope and retains
known, unfixed N-03, N-05, and N-11 defects.

---

## Verification results (macOS arm64, 2026-09-30)

Upstream `selftest` (tolerance 1e-10 relative per reported value) against
upstream's Linux x86-64 reference outputs:

| Sample                  | Max relative delta | Notes                          |
|-------------------------|--------------------|--------------------------------|
| biased-random-bits.bin  | 8.2e-12            |                                |
| biased-random-bytes.bin | 3.7e-10            | 7 predictor values > 1e-10     |
| data.pi.bin             | 4.3e-15            |                                |
| normal.bin              | 3.6e-15            |                                |
| rand1_short.bin         | 4.8e-15            |                                |
| rand4_short.bin         | 2.4e-15            |                                |
| rand8_short.bin         | 3.4e-12            |                                |
| ringOsc-nist.bin        | 1.5e-10            | 1 predictor value > 1e-10      |
| truerand_1bit.bin       | 5.3e-14            |                                |
| truerand_4bit.bin       | 3.5e-14            |                                |
| truerand_8bit.bin       | 1.4e-13            |                                |

The only values outside upstream's 1e-10 are Lag, MultiMCW and MultiMMC
predictor figures, at 1.3e-10 to 3.7e-10. Upstream issue #155 reports the
same estimators at the same magnitude (up to 3.2e-10) for a Windows 10
build, and the maintainer's reply there attributes such deltas to
platform math libraries. All entropic-statistic and tuple estimators
(MCV, collision, Markov, compression, t-tuple, LRS) agree to ≤ 1.5e-12.

Overall assessed min-entropy, exact digits per platform:

| Sample            | Linux x86-64 GCC (upstream refdata) | macOS arm64 Apple clang 21 (this build) | Windows      |
|-------------------|-------------------------------------|------------------------------------------|--------------|
| ringOsc-nist.bin  | 0.12644573619605429                 | 0.12644573619604868                      | not verified |
| truerand_1bit.bin | 0.82967708323406131                 | 0.82967708323411438                      | not verified |
| truerand_8bit.bin | 7.233861455178495                   | 7.2338614551796505                       | not verified |
| biased-random-bytes.bin | 0.25774087100648113           | 0.25774087100648113                      | not verified |

`pin-check.sh --prove-nonvacuous` output on this machine:

```
sample: platform=Darwin arm64 expected=0.12644573619605429 got=0.12644573619604868 reldelta=4.43e-14 tol=1e-9
sample: PASS
perturbed: platform=Darwin arm64 expected=0.12644573619605429 got=0.12643698121829336 reldelta=6.92e-05 tol=1e-9
perturbed: FAIL
perturbed: expected FAIL observed (check is not vacuous)
```

---

## Why the low digits differ between platforms, and why no flag was added

- **`-ffloat-store`** only matters for x87 excess precision. On x86-64
  GCC uses SSE and the flag is a no-op; on arm64 it is meaningless. It is
  *not* what makes the low digits platform-sensitive.
- **FMA contraction.** Measured with a one-line `a*b+c` at
  `-std=c++11 -O2`: Homebrew GCC 16 and Apple clang 21 both emit `fmadd`
  on arm64. Upstream's `-march=native` on any FMA-capable x86 machine
  enables the same contraction under GCC. Adding `-ffp-contract=off`
  would make this fork's arithmetic differ from an upstream x86 build in
  the other direction, so it was deliberately not added.
- **`long double` width.** 80-bit x87 extended under GCC on x86-64
  (Linux, MinGW); 64-bit (same as `double`) on arm64 macOS and under
  MSVC on every architecture. `ea_non_iid` uses `long double` in three
  places: the t-tuple/LRS `p_u` chain (`cpp/shared/lrs_test.h`), the
  compression estimate's G() series (`cpp/non_iid/compression_test.h`),
  and the predictor p-value function `prediction_estimate_function`
  (`cpp/shared/utils.h`) shared by Lag, MultiMCW, MultiMMC and LZ78Y.
  Measured against a 113-bit `__float128` build of the same sources
  (which reproduces the x86 reference to ≤ 6e-13), the 64-bit build
  diverges by: predictors up to 1.5e-15 × (bits assessed) relative, so
  ~1e-9 for 10^6 bits, ~1e-8 for 10^6 8-bit samples (the bitstring
  predictors see 8×10^6 bits), ~1e-7 for 10^8 bits; compression ≤ 1e-11
  and t-tuple/LRS ≤ 3e-11 at 10^6 samples, worst on near-constant data
  where the estimate itself is near zero. The predictor divergence comes
  from the fixed-point loop in `prediction_estimate_function` stopping at
  `LDBL_EPSILON`, so its error is ~N × ε and the bisection in
  `calc_p_local` inherits it. Direction is not systematic: the 64-bit
  result was lower in about two thirds of cases, higher in the rest. See
  "Precision audit" below for the full measurements.
- **libm.** `log2`, `pow`, `exp`, `log1p` implementations differ between
  macOS libm, glibc, and mingw-w64/UCRT. This is the residual source of
  the 1e-10-scale predictor deltas above.

The pinned-output tolerance of 1e-9 relative is valid for the pinned
sample (1-bit, 10^6 samples, collision estimate binding: measured
cross-platform delta 4.4e-14). It is **not** a general figure: for an
input where a predictor is the minimum, the cross-platform divergence
scales with the number of bits assessed (≈ 1.5e-15 × bits), so a
re-based pin on a 10^7-sample 8-bit capture needs a tolerance nearer
1e-7. A genuine change to the input or estimator moves the figure by
≥ 1e-5, so even that tolerance is not vacuous.

---

## The pinned-output check and its sample

`cpp/selftest/pin-check.sh` asserts the "Assessed min entropy" that
`ea_non_iid -vv` reports for `bin/ringOsc-nist.bin` against
`0.12644573619605429`, upstream's own value in
`cpp/selftest/refdata/ringOsc-nist.res`, to 1e-9 relative, after checking
the sample's SHA-256 (`7d37dc3795e9b2927beb779008d7f4b4630dd7f2c058a2b14cee9d41a658dd68`).

**Sample provenance, stated plainly.** No local capture exists yet (the
operator's device arrives January 2027). The pinned sample is upstream's
own: added to `usnistgov/SP800-90B_EntropyAssessment` as
`bin/ringOsc-nist.bin` in commit `7f51b1c` (2019-04-20, Joshua E. Hill),
1,000,000 one-bit samples, and discussed as ring-oscillator output by the
same author in upstream issue #245 ("I have no idea what the parameters
were for this particular design, but ... all ring oscillator designs have
essentially this behavior"). Upstream does not document the capture
hardware. What can be verified from the data itself: MCV estimate 0.99
(unbiased) but collision estimate 0.126 and Markov 0.258, i.e. heavy
serial correlation typical of a periodically sampled ring oscillator. A
CSPRNG or `/dev/urandom` stream scores ≈ 1.0 on every estimator and
cannot produce this profile. It is therefore real physical noise as far
as the data can show, published by NIST, citable by repository, path,
commit and hash — but its capture parameters are not on record.

Observation for anyone re-pinning: on this sample, flipping a single bit
at most offsets (0, 1, 2, 3, 7, 500000, 999999 were tried) leaves the
assessed figure bit-identical, because the collision estimate (the
minimum here) depends only on the multiset of collision-segment lengths,
which a lone flip inside a long run often does not change. A flip at
offset 123457 moves it by 3.5e-5; zeroing 64 bytes moves it by 6.9e-5.
The non-vacuity proof uses the 64-byte perturbation.

**When the January capture exists**, re-base the pin:

1. Capture ≥ 1,000,000 raw (unconditioned) samples at the device's
   native symbol width; commit as `bin/<device>-<YYYYMMDD>.bin` with a
   short provenance note (device, firmware, sampling parameters).
2. Run the same fork on a Linux x86-64 GCC build (the reference
   platform, e.g. the upstream `dockerfile`) **and** on the macOS build;
   record both 17-digit figures in the table above.
3. Set `SAMPLE`, `SAMPLE_SHA256` and `EXPECTED` in `pin-check.sh` to the
   Linux figure, keep `RELTOL=1e-9`, rerun `--prove-nonvacuous`, and
   confirm the perturbation still fails. Keep the ringOsc pin as a second
   guard or retire it explicitly in NOTICE.

---

## Windows — MEASURED on `windows-latest`, 2026-10-20

This section was unverified for the life of the fork. It is now measured, by a
manually-triggered GitHub Actions job — `.github/workflows/windows-platform-facts.yml`
with `.github/scripts/windows-facts.sh` — which needs no Windows machine.
Run it with
`gh workflow run windows-platform-facts.yml -R systemslibrarian/SP800-90B_EntropyAssessment`;
it uploads every log as an artefact. **The `-R` is not optional.** This
checkout has two remotes, `origin` (the fork) and `upstream` (`usnistgov`),
and `gh` with no `-R` resolves to **upstream** — measured: a bare
`gh workflow run` here returned
`HTTP 404: … not found on the default branch` for
`api.github.com/repos/usnistgov/…`, which is an attempted dispatch at NIST's
repository (`OC-93`). The full account is `OC-48` in
`audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md`.

**What is measured** (MSYS2 MINGW64, gcc 16.2.0):

| | |
|---|---|
| MSYS2 | **preinstalled** on the runner at `C:\msys64`, with `pacman` |
| `libdivsufsort` | **no `mingw-w64` package**, under any of four candidate names. The claim below is confirmed. |
| OpenMP runtime | `libgomp` **is** packaged, in `mingw-w64-x86_64-gcc-libs`, which the preinstalled toolchain does **not** pull in. Install it explicitly or the link fails with `cannot find -lgomp`. |
| every other `Makefile` dependency | packaged |
| `ea_non_iid`, `ea_iid`, `ea_restart` | all three **compile and link**, with OpenMP |
| `long double` | x87 80-bit: `LDBL_MANT_DIG` 64, `LDBL_MIN` 3.3621e-4932, `FLT_EVAL_METHOD` 0 |
| `sizeof(long)` | **4** — LLP64 confirmed |
| `R-1` affected set | **155 of 255** alphabet sizes, the x87 prediction confirmed independently of Linux |
| `ea_non_iid` at runtime | runs the **complete non-IID battery**, exit 0 |
| `ea_iid`, `ea_restart` at runtime | **fail the §5.2.5 LRS test on valid data** — see `C18` below |
| any `-o` report | **cannot be written at all** — see `C24` below |
| build state | establishable; the probe needs the full symbol listing here, since `nm -u` is blind on PE/COFF |

**Two defects make this route unusable as it stands**, and both are
fail-closed — they deny assessments rather than producing wrong figures:

- **`C18` (LLP64 integer overflow).** `n_choose_2()` at
  `cpp/shared/utils.h:997` computes `((n*n) - n) / 2` in `long int`. For a
  1,000,000-sample input with a longest repeated substring of 40, the true
  N = 499,960,500,780 becomes **−403,189,204** in a 32-bit `long`. The printed
  `Pr(X >= 1)` goes negative (−0.000367 where macOS prints +0.365370), and the
  decision at `lrs_test.h:765` compares against `logl()` of a negative number,
  i.e. **NaN**, so the LRS test fails **unconditionally whatever the data**.
  Overflow begins around L − W + 1 = 46,342, so every standards-sized
  assessment is affected. Reproducer:
  `audits/2026-10-11-independent-audit/reproducers/c18_llp64_overflow.c`.
- **`C24` (`rename()` is not POSIX here).** Windows `rename()` refuses an
  existing destination (`errno 17`). `C14` claims the `-o` path with a
  placeholder as soon as it is parsed, and `C08` then writes every report via
  temporary + `rename()`, so the placeholder guarantees every later write
  fails: `Error: could not put the report in place`. The two repairs are each
  sound and jointly non-portable. `MoveFileEx(..., MOVEFILE_REPLACE_EXISTING)`
  is the platform primitive.

**Both are now repaired (2026-10-20).** `C18` widened `n_choose_2` to `int64_t`
in the parameter, the product and the return, with LP64 bit-identity measured
(nine reports, three fixtures, all three tools; `OC-53`). `C24` writes the
report with `MoveFileEx(..., MOVEFILE_REPLACE_EXISTING)` under `_WIN32`
(`OC-57`). After both, on Windows: `Pr(X >= 1) = 0.365370`, **exactly macOS's
figure**, and every tool puts its report in place.

**What Windows can and cannot do today.** All three tools build and link, with
OpenMP. `ea_non_iid` runs the complete non-IID battery and produces a figure,
exit 0. `ea_iid` and `ea_restart` run through chi square, the §5.2.5 LRS test
and — for `ea_restart` — the restart sanity check, **all passing**, and then
exit at `seed()`, which opens `/dev/urandom`. **That is not "Windows is
unsupported" and should not be summarised as such.**

`seed()` is **deferred, not blocking** (`OC-60`): the owner's vendor reference
qualification means no NIST binary runs on a user's machine, so `seed()` sits
only on the expert-opt-in self-assertion path, for which macOS and Linux are
sufficient. If revisited, the fix is a **platform entropy source**
(`BCryptGenRandom` or `RtlGenRandom`) — and **`std::random_device` must be
refused**, because on MinGW libstdc++ it has historically been a deterministic
PRNG, which would make the IID permutation tests' p-values meaningless while
every surface indication said the tool worked.

**One live limit.** `data_t` holds `long len` and `long blen` with
`blen = len * word_size`, which overflows on LLP64 above **268,435,455** 8-bit
samples. Deliberately outside the `C18` repair, because those fields are
printed with `%ld` in many places and `int64_t` would make that wrong on LLP64.
Far above anything this project assesses, but a **live** limit rather than an
absent one: an input that large would be wrong on Windows rather than refused.

**One prediction remains untested here rather than refuted.** `OC-42` says
`ea_iid` and `ea_restart` die at `seed()`. They do not reach it: `seed()` is
called in the permutation stage, and `C18` fails the LRS test first, so the
permutation stage is unreachable on Windows for any standards-sized input. The
`ea_non_iid` half of that prediction is confirmed.

### Route: MSYS2 UCRT64 (MinGW-w64 GCC) — recommended

**Correction (2026-10-19, `OC-42`), itself narrowed on 2026-10-20 by `OC-48`:
the reasoning below is sound but UNTESTED on Windows, because `C18` stops both
tools before the permutation stage that calls `seed()`. Treat it as a reading
of the source, not a measurement. This route does NOT work without a source
change for `ea_iid` and `ea_restart`** — though as measured, `C18` and `C24`
are what stop it first. `seed()` at `cpp/shared/utils.h:795`
opens `/dev/urandom` and calls `exit(-1)` if it cannot. A native UCRT64 binary
has no `/dev/urandom` — the MSYS2 POSIX emulation layer does, but binaries built
for UCRT64 do not use it — and `seed()` is called from
`cpp/iid/permutation_tests.h:606` and `cpp/restart_main.cpp:298`. So those two
tools would exit at the permutation stage, while `ea_non_iid`, which never calls
`seed()`, would run. A Windows port needs a seeding source (`BCryptGenRandom`,
or `std::random_device`); that is a change to an entropy-relevant code path and
so a deliberate decision, not a build detail. Nothing below has been run.

Apart from that, this is the route that needs **the fewest source changes**. `getopt.h`,
`__int128`, `__builtin_inf`, `__builtin_popcount`, VLAs and `<omp.h>` are
all GCC features the code relies on, and MinGW-w64 GCC provides them, an
80-bit `long double` like Linux GCC, `libgomp` for OpenMP, and
`winpthreads` for `-lpthread`. `uname -s` reports `MINGW64_NT-…`/`UCRT64`,
so the Makefile takes its upstream (non-Darwin) path unchanged; GCC adds
`.exe` to `-o ea_non_iid` automatically.

1. Install MSYS2 (https://www.msys2.org), open the **UCRT64** shell, and
   install the packaged dependencies (all confirmed to exist in the MSYS2
   repository on 2026-09-30: `mingw-w64-jsoncpp` 1.9.8, `mingw-w64-bzip2`,
   `mingw-w64-openssl` 3.x):

   ```sh
   pacman -S --needed \
     mingw-w64-ucrt-x86_64-toolchain mingw-w64-ucrt-x86_64-cmake \
     mingw-w64-ucrt-x86_64-bzip2 mingw-w64-ucrt-x86_64-jsoncpp \
     mingw-w64-ucrt-x86_64-openssl make git perl
   ```

   Confirm OpenSSL is 3.x (`openssl version`) — not 1.1.x (advertising
   clause; end-of-life).

2. **libdivsufsort has no MSYS2 package and no vcpkg port** (checked
   2026-09-30: packages.msys2.org search empty, `msys2/MINGW-packages`
   has no `mingw-w64-libdivsufsort`, `microsoft/vcpkg` has no
   `ports/libdivsufsort`). Build it from the upstream source, tag 2.0.1,
   the same version Homebrew ships, with the 64-bit variant enabled
   (`ea_non_iid` links both `-ldivsufsort` and `-ldivsufsort64`). Its
   `CMakeLists.txt` declares `cmake_minimum_required(VERSION 2.4.4)`, so
   CMake ≥ 4 needs the policy override (Homebrew uses the same one):

   ```sh
   git clone --branch 2.0.1 https://github.com/y-256/libdivsufsort.git
   cd libdivsufsort
   cmake -S . -B build -G "MinGW Makefiles" \
     -DCMAKE_INSTALL_PREFIX=/ucrt64 \
     -DBUILD_DIVSUFSORT64=ON -DBUILD_EXAMPLES=OFF \
     -DBUILD_SHARED_LIBS=OFF \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   cmake --build build && cmake --install build
   ```

   `BUILD_SHARED_LIBS=OFF` gives static `libdivsufsort.a` /
   `libdivsufsort64.a`, so the resulting `ea_non_iid.exe` does not need a
   `divsufsort.dll` beside it. (Upstream issue #219 reports a wrong LRS
   probability from a DLL built with Visual Studio; a MinGW static build
   avoids that toolchain mix.)

3. Build and check, from the UCRT64 shell:

   ```sh
   cd cpp
   make non_iid                     # ARCH defaults to x86 → -march=native, as on Linux
   cd selftest
   ./selftest
   ./pin-check.sh --prove-nonvacuous ../ea_non_iid.exe
   ```

   To ship a binary that runs on other x86-64 machines, build with
   `make non_iid ARCH=generic` to drop `-march=native` (note this can
   change FMA contraction and thus low digits versus a `-march=native`
   build on the same machine; record which was used).

4. Record, on the Windows machine: `gcc --version`, package versions,
   `selftest` deltas per file, the 17-digit `pin-check` figure, and
   `sizeof(long)` / `LDBL_EPSILON` (see caveats).

### Windows caveats to check before trusting a figure

- **`long` is 32-bit on Windows** (LLP64), 64-bit on Linux/macOS.
  Audited by building the sources with every `long` forced to 32 bits
  (scratch copy, not shipped) and comparing all 30 audit inputs: every
  reported value was bit-identical to the 64-bit build. The only `long`
  products on the ea_non_iid path are the bitstring length
  `len × bits_per_symbol` and the `-l` offset `index × samples`. Measured
  consequences: 8-bit inputs of 268,435,456 samples (256 MiB) or more are
  refused at the bitstring allocation; at 536,870,912 samples (512 MiB)
  the product wraps to 0 and the tool crashes (SIGBUS); 1-bit inputs have
  no product and are limited only by the CRT's 32-bit `ftell`. One
  wrong-rather-than-refuse case exists: an `-l index,samples` request
  whose byte offset is ≥ 4 GiB wraps, reads the wrong block silently and
  reports its figure, where the 64-bit build refuses ("file read
  failure"); it needs a request beyond the end of any file Windows can
  open, so it is an operator error, not a valid-input hazard. Whether
  Windows `ftell` refuses or truncates for files ≥ 2 GiB is not stated in
  Microsoft's documentation; do not feed a Windows build files that
  large until tested (a truncating `ftell` on a ≥ 4 GiB file would assess
  a silently shortened sample).
- Expected deltas: issue #155's MinGW build agreed with the reference
  within 3.2e-10 on the predictors and better elsewhere.
- Run under the MSYS2 shell so `/dev/zero` (used by `pin-check.sh`) and
  `perl` (used by `selftest`) exist.

### Route not recommended: MSVC + vcpkg

vcpkg provides bzip2, jsoncpp, openssl, pthreads; it has no libdivsufsort
port. Beyond that, MSVC cannot compile the upstream sources as they are:
no `<getopt.h>`, no `__int128` (`__SIZEOF_INT128__` guard leaves
`uint128_t` undefined where it is used), no `__builtin_inf`, no C++ VLAs
(`utils.h:309`), and `long double` is 64-bit. Every one of those needs a
source change, which this fork forbids. If a native MSVC binary is ever
required, clang-cl with the MinGW-style flags would be the next thing to
try, but it is untested here.

---

## Precision audit (2026-09-30)

Method: a scratch copy of the sources with `long double` replaced by
`__float128` (113-bit, via Homebrew GCC + libquadmath), run beside the
shipped macOS build on the 11 upstream samples, 19 synthetic classes
(near-constant bits, biased bytes, periodic-with-noise, uniform, small n)
and three 10^7-sample inputs. On the 11 upstream samples the 128-bit
build reproduces the x86 (80-bit) reference to ≤ 6e-13 on predictors and
exactly on compression, so it stands in for the x86 result.

Worst 64-bit-vs-128-bit relative divergence per family, 10^6-sample
inputs (bitstring runs on 8-bit data assess 8×10^6 bits):

| Family                | Worst   | Input class                    | Lower / higher |
|-----------------------|---------|--------------------------------|----------------|
| MultiMMC predictor    | 8.7e-9  | biased bytes (bitstring)       | 6 / 2          |
| LZ78Y predictor       | 7.9e-9  | 8-bit, p(0)=0.9999 (bitstring) | 3 / 3          |
| MultiMCW predictor    | 6.5e-9  | 8-bit, p(0)=0.9999 (bitstring) | 10 / 4         |
| Lag predictor         | 4.5e-9  | 8-bit, p(0)=0.99 (bitstring)   | 4 / 6          |
| t-tuple               | 2.2e-11 | near-constant bits (H ≈ 1e-5)  | 13 / 12        |
| compression           | 9.1e-12 | 8-bit, p(0)=0.9999 (bitstring) | 15 / 4         |
| LRS                   | 1.3e-12 | near-constant bits             | 16 / 9         |
| Assessed figure       | 8.2e-10 | uniform 8-bit (predictor min)  | 13 / 1         |

Scaling with size (predictor p_local, from a grid of run length,
sample count and p_global' restricted to states the tool's own guard
can reach): max 1.7e-11 at N=10^4, 1.6e-9 at 10^6, 1.3e-7 at 10^8; on
real 10^7-sample inputs MultiMCW reached 5.4e-9 and compression 3.7e-12.
The guard decision (whether p_local is computed at all) never differed
between precisions on 1,533 grid points. Outside the guard the two
precisions take different bisection exit paths and differ by a factor
of two, but those states are unreachable from data.

Interpretation for the pricing use: on Apple silicon the figure can sit
up to ~1e-8 relative from the x86 reference at 10^6 8-bit samples and
~1e-7 at 10^8 bits, in either direction. That is far below any digit
that changes a pad length, but it is above upstream's own 1e-10
selftest threshold, and a pin tolerance must be chosen from the bits
assessed, not from a fixed number.

---

## Repairs made in this fork (2026-09-30)

After the defects this fork reported upstream had been reviewed there by
@joshuaehill (not a NIST account), ten repairs were made here. The estimator sources are therefore **no longer**
byte-identical to upstream `87c104d`; the statement of changes in
[NOTICE](NOTICE) lists each one with its upstream issue and commit, and
[audits/2026-09-30/FINDINGS-TRACKER.md](audits/2026-09-30/FINDINGS-TRACKER.md)
carries the per-finding status.

What was checked, stated as scope rather than as a guarantee: no
unintended numerical change was observed on the datasets tested. The
pinned check is unchanged at 0.12644573619604868, NIST's reference data
under `cpp/selftest/refdata/` is untouched and still reproduced exactly,
and no estimator formula, cut-off, rounding or confidence bound was
altered.

Most of the estimator changes only turn producing an unmeasured number,
reading out of bounds, or aborting the process into declining to produce
an estimate, which the combination logic already handled. **Two change
results on purpose:**

- **F09** corrects the MultiMMC run of correct predictions. Where the
  defect bit, the MultiMMC estimate rises. Because the reported figure
  is a minimum over the estimators, an input on which MultiMMC was the
  binding minimum will report a **higher** figure after this change. The
  earlier value was too low, so the higher figure is the correct one,
  but a before-and-after comparison must expect it. Not demonstrated on
  a concrete input: on the audit's own dataset the overall figure is
  unchanged because a different estimator binds.
- **N-01** makes a binary chi-square independence test with m = 1 fail,
  as SP 800-90B 5.2.3 requires, where it previously passed. That changes
  an IID verdict, not a min-entropy figure.

One finding was raised and then **withdrawn**: the treatment of a two-symbol
alphabet as binary regardless of declared sample width (upstream #253 and
PR #256). The upstream respondent held the current behaviour correct, answered
the fork's clarifying question on 2026-10-01, and is right on the standard's
text: §4.4.2 and §5 define "binary" by the alphabet, not the sample width, and
§6.2's binary-only estimators already run on the translated two-symbol data.
PR #256 was closed on 2026-10-02. The patch was never on master, so no figure
this build reports changed in either direction. Until 2026-10-02 this paragraph
said the finding was "deliberately not repaired ... pending their reading". The
full record is in [NOTICE](NOTICE) and in the tracker under "Withdrawn
findings".

---

## The unrepaired reference tool — tag `unrepaired-reference-2026-10-15`

On 2026-10-15 `repair/2026-10-09-verified-defects` was merged into master
(merge commit `d226f18`), closing `C07` (the LRS `p_col^W` underflow, which
aborted with asserts live and **fabricated** a figure under `-DNDEBUG`) and `C03`
(a failed IID battery still awarded a figure). From that commit on, master
builds the **repaired** tool. The standing reporting rule is two figures, always:
whatever the repaired fork reports, the reference tool's own figure must stay
reportable with the delta explained (`audits/2026-10-11-independent-audit/
REPAIR-STRATEGY.md`, "The governing constraint"). The reference figure is only
producible if the pre-merge tool can be built, so the last pre-merge master is
pinned by an annotated tag. "It is in git history" is not a build instruction;
this is:

```sh
git worktree add /tmp/unrepaired unrepaired-reference-2026-10-15
cd /tmp/unrepaired/cpp && make non_iid iid restart
/tmp/unrepaired/cpp/ea_non_iid -i -a -vv <capture.bin> <bits-per-symbol>
```

Asserts are live in that build (no Makefile target sets `-DNDEBUG`); do not add
it. The corrections the tag itself cannot carry are in
[docs/TAG-unrepaired-reference-2026-10-15.md](docs/TAG-unrepaired-reference-2026-10-15.md),
named for the tag so a search for the tag name finds them. **Walked end to end
from a fresh clone on 2026-10-18** (`OC-25`,
`logs/merge/tag-walk-2026-10-18.log`): it builds, and the canary classifies the
result UNREPAIRED / ASSERTS-LIVE. Two things the instructions *at the tag* do not
say at the point you read them: the quick-start block builds only `ea_non_iid`,
so use `make non_iid iid restart` as above; and its `./selftest` exits 1 on macOS
arm64 for the two documented upstream #155 files — that is the platform delta,
not a build failure, and `run-all-checks.sh --allow-known-platform-deltas` is
the documented invocation. `tools/build-provenance-canary.sh` run against `/tmp/unrepaired/cpp/ea_iid`
reports `ASSERTS-LIVE`; against a `-DNDEBUG` build of the same tag it reports
`NDEBUG` — those are the signatures it was calibrated on.

**The canary was re-signatured on 2026-10-18.** Its old question — asserts
live or NDEBUG — is moot on the repaired tree, where both builds refuse the
canary input identically, and the old two-signature version reported
`INDETERMINATE` for both builds of master (measured, `logs/merge/canary-*.log`),
which TruePad's harness treats as a refusal (`CROSS-REPO-FINDINGS.md` `XR-08`).
It now answers the question that has something behind it: **repaired tree or
unrepaired tree**, with the build kept as a sub-result under UNREPAIRED.
Demonstrated on all four builds plus a control, `logs/merge/canary3-*.log`:

| binary | `canary: TREE` | `canary: BUILD` |
|---|---|---|
| master `d226f18`, asserts live | REPAIRED | NOT-DISTINGUISHED |
| master `d226f18`, `-DNDEBUG` | REPAIRED | NOT-DISTINGUISHED |
| tag, asserts live | UNREPAIRED | ASSERTS-LIVE |
| tag, `-DNDEBUG` | UNREPAIRED | NDEBUG |
| `/bin/ls` | INDETERMINATE | INDETERMINATE (exit 3) |

`NOT-DISTINGUISHED` is the expected value for a repaired binary, not a gap.
REPAIRED is not reviewed. Measured on Apple arm64, where `long double` is
IEEE double — the narrowest of the three formats a build can land on; the x87
and binary128 sides are a bounded argument from the arithmetic (`OC-24`),
settled by one canary run on such a host, not by re-running everything.

**The tag's `ea_restart` is the pre-repair one.** It takes a bare `H_I` at any
scale, so a per-bit figure given bare yields a wrong cutoff silently; master's
requires `/symbol` or `/bit` (`OC-29`). Its *cutoff* is upstream's simulation of
the multinomial maximum, which targets the **correct** statistic and lands
within a count or two of master's exact value — so a restart decision from the
tag's binary is sound, it simply varies run to run and records neither the
cutoff nor `X_max` in its report (`OC-30`, `XR-11`). What must **not** be used
is §3.1.4.3's printed single-binomial formula, which rejects correctly-operating
sources; the fork briefly made that the verdict in `a5005bd` and corrected it
the next day.

**Evidentiary standing.** The repairs are self-authored and unreviewed; the
merge changes nothing about that. Figures from the repaired build are to be
reported with that statement beside them.

## Cost of conditioned IID testing (`ea_iid -c`)

Since the #271 repair, `-c` runs the Section 5 batteries on the conditioned
output as a binary string, which is what SP 800-90B 3.1.1 item 2 and 3.1.5.2
require. For multi-bit samples that is eight times as much data as the
previous (incorrect) behaviour, and the permutation battery dominates.

Measured on this machine (Apple silicon, 10 cores), on conditioned data that
**fails** the tests. These are measurements of one workload on one machine, and
the rows below them are extrapolations from it, not predictions for other
hardware or other data:

| Bits tested | Wall clock |
|---|---|
| 100,000 | 93.3 s |
| 200,000 | 191.8 s |
| 400,000 | 374.9 s |

That is linear: 2.06x and 1.95x the time for 2x the data. Extrapolating at
0.94 **seconds** per thousand bits (937 ms per thousand bits from the last
row; this said "0.94 ms" until 2026-10-01, which is a factor of 1000 out.
The extrapolated run times below were always computed from the measured
rate, so they were and remain correct):

| Run | Bits | Extrapolated |
|---|---|---|
| `-c -t` | 1,000,000 | about 16 minutes (extrapolated) |
| `-c -a` on 10^6 8-bit samples | 8,000,000 | about 2 hours (extrapolated) |

**No safe shortcut was identified within this pass, and the behaviour was not
changed for speed.** That is not a claim that none exists: the measurements
below establish the cost, not impossibility. Computing the statistics
incrementally, or reducing per-permutation allocation, might preserve
semantics, but each would need its own investigation and an equivalence
argument before it could be trusted here.

What was ruled out, and why it is not simply "more data":

- The battery already short-circuits. `permutation_tests()` skips the
  remaining permutations once all 19 tests have passed decisively, and a
  passing test can never un-pass because its counters only rise. Data that
  passes is therefore already fast.
- The slow case is data that **fails**. A failure is only known after all
  10,000 permutations, so none can be skipped. Short-circuiting a failure
  early would mean deciding it before the evidence is in.
- It is already parallel: `#pragma omp parallel for` over the permutations,
  across all 10 cores here.
- Anything further would mean computing the 19 statistics incrementally
  rather than over the whole array per permutation, which is a rewrite of the
  statistical code rather than an optimisation of it.

So the cost is inherent to testing the right data, and it falls on exactly the
datasets an operator most wants an answer about. `-t` bounds the work to
1,000,000 bits, but that is an operator decision with its own consequence,
namely that the verdict then covers only the first 1,000,000 bits of the
conditioned output. It is not applied by default and should not be.

---

## Upstream observations (not patched here)

None of these affect a reported figure on a valid input. They are
recorded so nobody rediscovers them.

1. **Error message never formatted** — `cpp/shared/utils.h:184` and
   `:226`:
   `testRun->errorMsg = "Error: could not open '%s'\n", file_path;`
   The comma operator discards `file_path`; the JSON `errorMsg` field is
   the literal template with `%s`. Cosmetic; error paths only. Suggested
   upstream issue title: "errorMsg in read_file_subset uses the comma
   operator instead of formatting the filename". Not filed from this
   session — it is not an estimator issue; file it if wanted.
2. **`-march=native` makes the reference itself machine-dependent** on
   x86 (FMA contraction on and off across CPUs). Not a bug, but the
   reason two "reference" Linux builds can disagree at 1e-10.
3. **README says selftest passes below 1.0E-6**; `compareresults.pl`
   actually uses 1.0E-10. The script is the stricter and is what
   `selftest` runs. Note that this fork *has* changed that script and
   the harness around it (#272): what it collects and the exit status
   it propagates. The 1.0E-10 epsilon itself is untouched, which is why
   the observation still stands.
4. **Makefile targets `*_main.o` never produce a `.o`**, so every
   `make non_iid` relinks. Harmless.
5. **JSON report embeds the input file's SHA-256** (`sha256` field, from
   `sha256_file` in `cpp/shared/TestRunUtils.h`; also printed at `-vv`).
   Intentional upstream behaviour; left in place, redacted downstream.
6. Upstream issue #155 (Windows deltas / 32-bit `long`) and #219 (LRS
   probability wrong with a Visual-Studio-built divsufsort DLL) are the
   relevant prior art for the Windows route.
