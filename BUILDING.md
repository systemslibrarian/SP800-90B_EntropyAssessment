# Building `ea_non_iid` from this fork

This fork exists to produce a reliable `ea_non_iid` binary on macOS and
Windows **without changing anything that can alter a reported min-entropy
figure**. Estimator logic, cut-offs, rounding, output formatting, and the
set of estimators that run are exactly upstream's. Every change is listed,
with dates, in [NOTICE](NOTICE).

Upstream baseline: `usnistgov/SP800-90B_EntropyAssessment` at
`87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`.

Only `ea_non_iid` is built and shipped. **Do not run plain `make`** (the
`all` target) for a shippable build: it also builds `ea_conditioning`,
the one program that links GNU MPFR and GMP (LGPL). See "LGPL isolation".

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
- The tool requires at least 1,000,000 samples for a normal assessment
  (it warns and continues below that).
- `-v` shows the per-estimator figures; `-vv` prints them with 17
  significant digits (what selftest and pin-check parse).
- **The JSON report and the `-vv` banner embed the SHA-256 of the input
  file** (`sha256_file` in `cpp/shared/TestRunUtils.h`, field `sha256`).
  This is upstream behaviour and is intentionally left in; the consuming
  tool redacts it downstream.

Run-to-run determinism: `ea_non_iid` contains no OpenMP pragmas (they
are only in `ea_iid` and `ea_restart`), so it is single-threaded and
gives bit-identical output on repeated runs on the same binary.

---

## LGPL isolation (MPFR / GMP)

Finding: MPFR and GMP are linked only into `ea_conditioning`.

Evidence, all from the upstream baseline:

- `cpp/Makefile`: `COND_LIB = -lmpfr -lgmp` is passed only in the
  `conditioning` rule; `LIB` and `SHARED_LIB` (used by every program)
  name only bz2, pthread, divsufsort, divsufsort64, jsoncpp, crypto.
- `grep -rln 'mpfr\|gmp' cpp/` → `cpp/Makefile`, `cpp/conditioning_main.cpp`
  only. No header under `cpp/shared/` or `cpp/non_iid/` includes them.
- Built binary: `otool -L cpp/ea_non_iid` lists libbz2, libSystem,
  libdivsufsort, libdivsufsort64, libomp, libjsoncpp, libcrypto, libc++
  and nothing else; `nm -u cpp/ea_non_iid | grep -c -E '_mpfr|gmp'` → 0.

`ea_non_iid` therefore carries no LGPL code. `make non_iid` never
compiles `conditioning_main.cpp`; MPFR/GMP need not even be installed.

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

## Windows — route documented, NOT verified

Nothing below has been run. No Windows machine was available; this
section is written to be executed and checked on one, and every line is
to be treated as unverified until then.

### Route: MSYS2 UCRT64 (MinGW-w64 GCC) — recommended

This is the only route that needs **no source changes**. `getopt.h`,
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
   `selftest` runs.
4. **Makefile targets `*_main.o` never produce a `.o`**, so every
   `make non_iid` relinks. Harmless.
5. **JSON report embeds the input file's SHA-256** (`sha256` field, from
   `sha256_file` in `cpp/shared/TestRunUtils.h`; also printed at `-vv`).
   Intentional upstream behaviour; left in place, redacted downstream.
6. Upstream issue #155 (Windows deltas / 32-bit `long`) and #219 (LRS
   probability wrong with a Visual-Studio-built divsufsort DLL) are the
   relevant prior art for the Windows route.
