# `launch/b63aff1-windows` — ShannonPad's launch pin, made to run on native Windows, with every figure unchanged

**Base:** `b63aff1` (2026-10-21), the commit ShannonPad pins for launch.
**What this branch is:** `b63aff1` plus only the repairs the three tools need
to run correctly on native Windows under MSYS2 UCRT64, and the instruments
that measure them. **What it is not:** master. Master changes the `C22a`
floor and other figures (`OC-121`'s C22a work, `76875b5`/`76a21a6`'s C22c
source, `7a21378`'s C01 margin, `745b396`'s new `hAssessed` field); none of
that is here. This branch is not merged into master and must not be.

## The backport, each change with its source commit on master

| file | source | what |
|---|---|---|
| `cpp/shared/os_random.h` (new) | `7a51882`, hardened in `a05fce7` | one reader of OS randomness: `EA_TEST_RANDOM_SOURCE` override on every platform; else `/dev/urandom` on POSIX, read exactly as before; else `BCryptGenRandom(NULL, buf, n, BCRYPT_USE_SYSTEM_PREFERRED_RNG)` under `_WIN32`. Fail-closed, no weaker fallback |
| `cpp/shared/utils.h` — `seed()` | `7a51882` | reads it instead of `fopen("/dev/urandom")`, which `exit(-1)`'d on every native Windows run (`OC-42`, measured `OC-48`); still `exit(-1)` if the source fails |
| `cpp/shared/TestRunUtils.h` — the writer's temporary name | `b53ff5d` (`OC-121`, this file's hunk **only**) then `7a51882` | the derivable fallback (`r2 = (attempt*2654435761) ^ r1`, i.e. `r1` at attempt 0) removed; the suffix drawn through `os_random.h`; an unreadable source is a refusal with its reason named |
| `cpp/shared/TestRunUtils.h` — `removeStaleReportTarget` | `7a51882` | a refused `-o` claim removes whatever is at the path before the nonzero exit (never the input capture: A05's identity test first; never a directory or a device; `unlink`/`DeleteFile`, which do not follow a link) |
| `cpp/{non_iid,iid,restart}_main.cpp` | `7a51882` | `claimReportTarget` calls the removal when the write is refused — one line each |
| `cpp/Makefile` | `7a51882` | `-lbcrypt` when `uname -s` is `MINGW*`/`MSYS*`/`CYGWIN*`. **The pin's `CXXFLAGS` are untouched** (`-ffloat-store` stays unconditional; `OC-121`'s probe is not taken) |
| `cpp/selftest/regression-output-aliasing.sh` | master's copy: `b53ff5d`, `1f8c768`, `7a51882`, `a05fce7` | the unreadable-source refusals, the three byte-identical-survivor cases, platform skips counted; 49 declared |
| `cpp/selftest/launch-equivalence.sh` (new) | this branch | the measurement below |
| `.github/scripts/windows-facts.sh`, `.github/workflows/windows-platform-facts.yml` | master's copies: `a05fce7`, `01db092`, `afe86ab` | the MINGW64/UCRT64 matrix, the C25 report gate, the inverted `seed()` gate, the C++ `long double` print probe |
| `.github/workflows/launch-equivalence.yml` (new) | this branch | the Linux half of the measurement, fired on every push to `launch/*` |

Already in `b63aff1`, so not backported: `C18` (`int64_t` `n_choose_2`),
`C24` (`MoveFileEx`), `A05`'s Win32 identity path, `F03`'s guarded temporary.

**Not taken, by design:** `OC-104` (refusing an option after the operand),
`PROV-01` (the prescan claim), `AA-04` (restart not-run flags and
`hAssessed`), `PROV-15` (the macOS OpenSSL pin), `OC-121`'s Makefile and
oracle hunks, every `C22a`/`C22c`/`C01` change, every record and document
under `audits/`. The branch keeps the pin's oracle
(`audits/2026-10-11-independent-audit/oracles/entropy_floor.py` at
`b63aff1`) — so "the C22a floor is unchanged" is measured **with the pin's own
oracle**, which is the only comparison that means anything; master's oracle
would differ by 3.0e-8 bit at n = 10⁶ (`76875b5`), and that is exactly what
ShannonPad is declining.

## "Nothing changes any figure" — measured, not asserted

`cpp/selftest/launch-equivalence.sh` builds `b63aff1` and this tree side by
side on the host it runs on, runs the eleven `bin/` inputs the selftest uses
(digests checked against `fixture-manifest.txt`) plus three generated streams
from fixed seeds through all three tools with both builds, and compares:

- `ea_non_iid`: the `-vv` transcript **byte for byte** (every intermediate
  printed) and the JSON report (only `dateTimeStamp` and `commandline` set
  aside; the latter names the binary);
- `ea_iid` and `ea_restart`: the JSON report with the fields that the **same
  binary changes between two of its own runs** set aside — measured each run
  and printed; it is `.testCases[0].permutationTestResults` and nothing else,
  because the permutation tests seed from the OS — with the verdicts, the
  group count and every other field still compared. A verdict that the base
  binary flips between its own runs on a marginal input (the baseline-
  against-itself control, `OC-53`) is noted as seeded, not failed;
- the entropy floor (the pin's oracle) on both builds' reports: identical;
- every exit status;
- and the comparator is shown live: a 1e-15 perturbation of one figure must
  be reported, or the script refuses (exit 2).

**macOS arm64 (Apple clang 21), host run, five pieces** (the host could not
hold the whole corpus in one run; the pieces cover all 14 inputs once, with
the final script at `c198614`): 11 + 18 + 10 + 10 + 14 = **63 comparisons,
63 identical, 0 differences**. On the three 10,000-sample inputs the pin's
oracle refuses identically on both builds' reports, which is noted and not
counted as a floor comparison (an earlier script version had counted those
three as "identical", which was true of two refusals and not of a floor).
The one seeded verdict: `rand4_short` (a 10,000-sample, non-compliant test
input) flips its IID verdict between two runs of the *base* binary.
The `C22a` floor figures printed identical, e.g. `0.84129042387787445`
(`gen_bit`), `0.82631707515410624` (`truerand_1bit`),
`0.014406571036456107` (`biased-random-bits`), `0.56617758403918961`
(`data.pi`).

**Linux x86-64 (ubuntu-latest, GCC 13.3), one run over the whole corpus:**
run `42766135452` on `c198614` (the tool sources and the script of this
head) — **63 comparisons, 63 identical, `launch-equivalence: PASS`**: the
same measured seeded set (`.testCases[0].permutationTestResults`), the same
live check, the same three oracle refusals on the short inputs, the same one
seeded verdict on `rand4_short`. (An earlier run, `42762513870` on `4df5cd9`,
passed 66 of 66 with the script version that counted the three refusals.)
The floor figures agree with macOS to the known platform deltas and not
beyond (e.g. `biased-random-bits` `0.014406571036457113` on Linux against
`…456107` on macOS — a last-digit platform difference the fork documents,
present identically in both builds on each host).

**Windows (windows-latest, MSYS2 UCRT64 and MINGW64), run `42764657869` on
this head (`4df5cd9`; and `42761417112` on `8087899`, the backport commit):**
every gate green but the expected `libdivsufsort has NO mingw-w64 package`;
`A05` regression 49 of 49 with the three survivor cases `PASS`; the C++
`long double` print probe `PASS` by `printf` and `iostream`; `ea_non_iid`,
`ea_iid` and `ea_restart` each complete a real run to a figure and write a
complete `errorLevel 0` report at a fresh path and over an existing one.
`uname -s` is `MINGW64_NT-…` in both shells, so the Makefile's `-lbcrypt`
rule applies to both.

## What it does not establish

The quality of `BCryptGenRandom`'s output beyond Microsoft's statement that
the system-preferred RNG is an SP 800-90 `CTR_DRBG`; `F03`'s symlink limbs on
Windows (MSYS2's `ln -s` copies, six cases counted as `SKIP`); the pin's
late-option behaviour on Windows (`OC-104` is not here, and MinGW's `getopt`
is unmeasured); `seed()`'s second caller in `restart_main.cpp` is compiled
out (`EA_RESTART_WITHOUT_C23_FIX` unset), so "only the permutation stage
reads the seed" is true of the shipped build only. The pin's own
`run-all-checks.sh` tally carries the `F11` defect `OC-92` fixed in
`b572650` (it counts a could-not-run as a failure), so its summary line on
Linux reads one failure that is not one; the suite is run informationally in
the Linux job and is not the evidence — the equivalence measurement is.

Nothing here is reported upstream.
