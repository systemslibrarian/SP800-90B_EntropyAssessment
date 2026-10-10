# Independent audit report — 2026-10-09

## Executive result

Audit target: fork commit `106d31c4b010d9cd4ae94c0db14d9dcf11aeb353`
on macOS 26.6.2 arm64. Upstream `master` was fetched at
`87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`; that commit is also the merge
base, so the fork is 55 commits ahead and upstream is zero commits ahead.

Three genuinely new defects were verified:

| ID | Severity | Result |
|---|---:|---|
| `TP-AUD-01` | **High** | TruePad accepts unattested, ignored assessment executables and an arbitrary nonempty “selftest” record. A standards-dimensioned, deterministic period-two source was accepted at 1 bit/sample. |
| `TP-AUD-02` | **Medium** | TruePad's executable contract pins unmodified upstream `87c104d`, while its governing design record and this repository say the reviewed patched fork is the product dependency. The setup, qualification, lock, and tests therefore bypass all 55 fork commits. |
| `HARNESS-AUD-01` | **Low** | The repository selftest has no expected-fixture count. Removing one of eleven fixture/reference pairs still produces `PASS` and exit 0. |

No new mathematical defect that overestimates entropy on a supported,
standards-valid input was verified. The valid-input battery exercised every
supported width from 1 through 8 bits, dependent and drifting sources, a valid subset,
conditioned modes, the IID path, and a 1000×1000 restart matrix. Results were
plausible and conservative for the analytically constrained cases. This is
coverage evidence, not proof of estimator correctness for all inputs.

The fork is **not ready to be relied on by TruePad**. `TP-AUD-01` defeats the
assessment gate, `TP-AUD-02` selects the wrong code baseline, and existing
`C-01` remains a sanitizer-confirmed valid-input memory error in
`ea_restart`. Existing `N-07` also leaves a hash/assessment time-of-check gap.
Physical entropy, restart independence, operating-range characterization,
health-test thresholds, and extractor-seed assumptions remain unestablished.

## New findings

### TP-AUD-01 — TruePad does not authenticate assessment executables or validate the selftest verdict

**Severity:** High. **Affected TruePad SHA:**
`186a3376deca2e1608dbd1c8114c84113b048091`.

**Impact.** A writable, corrupted, incorrectly built, or deliberately replaced
`ea_non_iid`/`ea_restart` can return fabricated successful JSON. TruePad then
creates a successful qualification bundle and can budget extraction at the
fabricated rate. The reproduced case changed a real estimator result of zero
to an accepted rate of one bit per sample.

**Root cause.** `verifyToolsSource()` checks the source checkout's HEAD and
tracked diff, requires executable paths inside that checkout, and trusts exact
`--version` strings. It does not compare executable hashes with the hashes
created by setup. The normal executable paths (`cpp/ea_non_iid` and
`cpp/ea_restart`) are ignored by this repository's `.gitignore`, so replacing
them leaves `git status --porcelain` empty. Separately, qualification accepts
any nonempty `--selftest-record`; it hashes and marks that file for later
operator review but never parses a passing result.

Source locations:

- TruePad `src/cli/v2/infnoise-qualification.ts:133-165` — source and version
  checks, but no executable attestation.
- Same file `:247-252` and `:354-361` — only nonempty selftest validation.
- TruePad `scripts/setup-macos-rng-tools.mjs:137-145,180-189` — setup already
  calculates the missing authoritative selftest verdict and executable hashes.
- This repository `.gitignore:7-10` — assessment binaries are ignored.
- TruePad `docs/audit-fixes/QUEUE-NOTES.md:3248-3255` — documented contract
  requires the approved SHA-256 to be checked before assessment and a mismatch
  to be refused.

**Supported-input applicability.** The assessment input contains exactly
1,000,000 one-byte samples, each `0x00` or `0x01`, and the restart matrix is
exactly 1,000 rows × 1,000 one-bit samples. This tests a valid representation
and required dimensions. The sequences are deliberately deterministic; they
are negative controls, not physical entropy claims.

**Reproducer.** `reproducers/truepad-unattested-tools.mjs` uses only synthetic
data. It writes two executable files into a disposable, clean checkout of the
exact TruePad-pinned upstream SHA. Each executable self-reports version 1.1.8
and writes fabricated valid JSON. The supplied selftest file literally says it
is not a passing selftest.

```text
node reproducers/truepad-unattested-tools.mjs \
  /Users/gmcas/repos/TruePad PINNED_UPSTREAM_WORKTREE DISPOSABLE_DIRECTORY
```

Observed:

- TruePad exit: `0`.
- Qualification status:
  `assessment-tools-passed-independent-physical-review-pending`.
- Assessed and selected entropy: `1` bit/sample.
- `git status --porcelain` in the tools checkout: empty.
- Assessment SHA-256:
  `2ba607832cf7dd10179fb3b0f1dbf99393e5d3a1f12c1752b07dd62c8ca2ebc3`.
- Restart SHA-256:
  `46b7a4fc500549915a2b991f47409f947d3929a9d8dbc4d2b82872447ba7224f`.
- Fake-tool SHA-256:
  `32945cf9f24872c15dc33281c44997dacca06feac024d0d658e85b3c5b519b8b`.

The positive control ran the real fork `ea_non_iid` on the identical assessment
and returned `hAssessed = -0.0`, exit 0. The implementation substitution is the
meaningful mutation; the gate did not detect it. Evidence:
`logs/truepad-unattested-tools.log` and
`logs/truepad-spoof-real-tool-control.log`.

**Why this is new.** The entropy repository's canonical tracker contains tool
I/O and hash issues, but not TruePad's missing executable/setup attestation.
The TruePad audit records assert the opposite behavior and contain no prior
finding for this path. `N-07` concerns hashing and assessing different versions
of an input file; it does not cover executable identity or selftest validation.

**Expected behavior and repair strategy.** Qualification should consume one
reviewed setup manifest, validate its schema, source commit, build identity,
selftest verdict and exact expected fixture count, then compare each executable
against the manifest hash immediately before execution. It should reject any
mismatch before creating output. The execution/verification race should be
closed by executing the verified object rather than reopening an attacker-
replaceable pathname. Add negative controls for a changed executable, fake
version output, failed/incomplete selftest, missing fixture, and mismatched
manifest/source.

### TP-AUD-02 — TruePad pins unmodified upstream instead of its declared patched product dependency

**Severity:** Medium. **Affected TruePad SHA:**
`186a3376deca2e1608dbd1c8114c84113b048091`.

TruePad's qualification constants and lock file require
`usnistgov/SP800-90B_EntropyAssessment` at upstream commit `87c104d`. Its setup
script clones that lock and qualification rejects any different HEAD. The
reviewed fork at `106d31c` is therefore rejected even though:

- this repository's canonical tracker and NOTICE state that patched `master`
  is the TruePad product dependency; and
- TruePad's `QUEUE-NOTES.md:3135-3180` says TruePad chose the patched fork over
  unmodified upstream because dangerous-direction defects should not be carried
  into pad pricing.

Source locations:

- TruePad `src/cli/v2/infnoise-qualification.ts:37-39,142-145`.
- TruePad `third_party/sp800-90b-tools.lock.json:3-10`.
- TruePad `scripts/setup-macos-rng-tools.mjs:97-99,124-141`.
- TruePad `docs/audit-fixes/QUEUE-NOTES.md:3135-3180`.
- This repository `audits/2026-09-30/FINDINGS-TRACKER.md:3-21`.

The two revisions share the upstream commit as merge base; the selected build
omits every one of the fork's 55 commits, including estimator repairs,
minimum-size enforcement, reporting guards, and regression harness fixes. It
also retains known `C-01` and `N-07`. Those are existing findings and are not
relabelled as new defects here.

**Why this is new.** Prior repository audits established the fork repairs and
TruePad policy. They did not identify that the subsequently implemented setup,
lock, qualifier, and tests enforce the opposite commit. This is a distinct
integration contract failure, not a rediscovery of any omitted repair.

**Repair strategy.** Make one reviewed lock authoritative across setup,
qualification, documentation, and tests. It should name the fork URL, exact
reviewed fork SHA, upstream base SHA, expected regression set, build command,
and binary hashes. Do not use a moving branch name. Re-run qualification and
all product-specific controls after changing the pin.

### HARNESS-AUD-01 — selftest silently accepts a missing fixture/reference pair

**Severity:** Low. **Affected fork SHA:** `106d31c`.

`cpp/selftest/selftest` iterates whatever matches `../../bin/*` and succeeds if
every discovered item compares successfully. It never requires the intended 11
fixtures or a manifest. In an isolated copy, 11 controlled fixture/reference
pairs produced `PASS (11 files)`, then deleting one pair produced
`PASS (10 files)` and exit 0. Evidence: `logs/selftest-missing-fixture.log`.

`run-all-checks.sh` trusts that exit status. Its separate missing-binary guard
does work: a disposable missing-binary mutation exited 2
(`logs/wrapper-missing-binary.log`). TruePad's current setup parser expects 11
entries, so that particular setup path mitigates the missing-count defect; the
repository's advertised standalone strict suite does not.

This is not `NOVEL-01`: that finding was loss of comparison failure status and
insufficient comparison of final entropy fields. It is also not `REV-006`,
which covered vacuous platform-delta classification. Neither requires a
fixture manifest or exact fixture count.

Repair strategy: keep a versioned fixture manifest containing names and hashes,
verify exactly that set before execution, reject extras/missing files, and add
a deletion mutation to `run-all-checks.sh` coverage.

## Standards baseline and input scope

Primary authority: NIST SP 800-90B, January 2018, official PDF preserved at
`audits/2026-09-30/reference/NIST.SP.800-90B.pdf`. The CSRC publication page
currently links a 2025-05-29 *potential errata* sheet. The sheet proposes a
§5.2.4 critical-value correction (`27.887` → `27.877`) and a §6.3.1 worked-
example correction (`p_u=.6822`, entropy `.5518`). It explicitly says these are
potential updates, not a revised normative publication.

Relevant requirements applied in this audit:

- §3.1.1: sequential datasets contain at least 1,000,000 sample values; chunks,
  if concatenated, each contain at least 1,000 samples. A conditioned sequential
  dataset contains at least 1,000,000 outputs and is assessed as a bitstring.
- §3.1.2: an IID claim requires the Section 5 sequential tests and applicable
  restart row/column evidence; otherwise use the non-IID track.
- §3.1.3: for nonbinary raw data, the initial estimate is the minimum of
  `H_original`, `n × H_bitstring`, and the submitter estimate. One million
  symbols, bytes, and bits are not interchangeable.
- §3.1.4: restart evidence is 1,000 restarts with 1,000 samples each; row and
  column estimates and sanity checks constrain the final result.
- §6.3.1: the MCV confidence bound was independently implemented and checked.

The upstream restart program uses simulation rather than the literal binomial
critical value. Historical discussions #56, #95, #209 and PR #224 describe this
as an upstream policy responding to a claimed standard problem. It is not an
official NIST erratum, and this audit does not silently substitute it for the
published requirement.

Official sources:

- <https://csrc.nist.gov/pubs/sp/800/90/b/final>
- <https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-90b.pdf>
- <https://csrc.nist.gov/files/pubs/sp/800/90/b/final/docs/sp800-90b_errata_potential_updates.pdf>

Upstream comments associated with the fork's 2026 findings were made by
@joshuaehill of KeyPair Consulting, not a NIST account. They are upstream
contributor dispositions, not official NIST statements. Closing an issue was
not treated as proof of either repair or rejection; current source and actual
discussion were inspected.

## Build and suite results

The supported programs were explicitly built in a detached clean worktree:

```text
make clean
make non_iid iid restart
```

All built successfully. Apple clang 21 ignored `-ffloat-store`, so this flag
does not supply its intended floating-point constraint on the audited platform.
Other warnings included variable-length arrays and deprecated `sprintf` use.
TruePad's setup overrides the compiler flags and omits `-ffloat-store`; because
the audited clang ignores it, that omission has no effective floating-point
difference on this host, but the two recorded build commands are not identical.
TruePad actually invokes only `ea_non_iid` and `ea_restart`; `ea_iid` was built
and audited because it is part of the requested supported set. The Makefile can
also build `ea_conditioning` and `ea_transpose`, but TruePad neither builds nor
uses them. Conditioning-only tracker items remain deferred accordingly.

Strict suite:

```text
cpp/selftest/run-all-checks.sh
15 passed, 1 failed; exit 1; 14 regression scripts discovered
```

The sole strict failure was the already documented upstream #155 numerical
delta on `biased-random-bytes.bin` and `ringOsc-nist.bin` (2 of 11 reference
files). The explicit platform-exception run exited 0 with 16 passed and no
failures. The strict result remains the primary verdict; the exception run only
demonstrates that the allow-list is narrow. `BUILDING.md` still says “all eight”
regression scripts, but discovery now executes 14.

The wrapper propagated a missing supported executable with exit 2. All 14
regression scripts passed, including short-data refusal and JSON/write-error
guards. Historical immediate-parent/fixed/mutant evidence was reused from the
2026-10-01 re-audit rather than weakened or mechanically repeated.

Full logs: `logs/build-supported.log`, `logs/run-all-strict.log`,
`logs/run-all-platform-deltas.log`, and `logs/wrapper-missing-binary.log`.

## Mathematical and valid-input observations

The generator seed is `0x90b20261009`; exact sizes, descriptions, counts, and
SHA-256 hashes are in `logs/fixture-manifest.json`. Generated binary data stayed
outside the tracked repository.

Selected non-IID observations, all at 1,000,000 samples:

| Fixture | Width | Observed assessed entropy (bits/sample) | Interpretation |
|---|---:|---:|---|
| constant | 1 | no award; exit 255 | fail closed |
| one `1` among zeros | 1 | `-0.0` | conservative |
| Bernoulli p(1)=.01 | 1 | `0.00910507099` | below MCV-only oracle; compression binds |
| SHA-counter low bit | 1 | `0.8389091523` | stochastic software fixture only |
| alternating | 1 | `-0.0` | deterministic dependence detected |
| period `001011` | 1 | `-0.0` | deterministic dependence detected |
| Markov P(stay)=.99 | 1 | `0.00710507984` | strong dependence detected |
| p=.1 then p=.9 drift | 1 | `0.08640874558` | nonstationarity reflected |
| repeated 4,096-sample block | 1 | `0.000001594` | long repetition detected |
| approximately uniform 0..3 | 2 | `1.7746986436` | bitstring term binds |
| approximately uniform 0..7 | 3 | `2.6769916865` | bitstring term binds |
| sparse `{0,17,255}` | 8 | `0.7799495164` | `min(H_original,8h')`; bitstring binds |
| approximately uniform 0..15 | 4 | `3.6115203976` | bitstring term binds |
| approximately uniform 0..31 | 5 | `4.3631441645` | bitstring term binds |
| approximately uniform 0..63 | 6 | `5.5413245843` | bitstring term binds |
| approximately uniform 0..127 | 7 | `6.2437022842` | bitstring term binds |
| approximately uniform 0..255 | 8 | `7.4113079986` | bitstring term binds |

The valid second 1,000,000-sample subset of a 2,000,000-sample source reported
the requested and actual subset correctly and assessed `0.829437` bits/sample.
For 8-bit conditioned data, `-c -t` assessed exactly 1,000,000 bits and `-c -a`
assessed all 8,000,000 bits. The `hAssessed = n×h'` conditioned reporting issue
is prior F23 and was not promoted.

The independent §6.3.1 oracle uses the clause formula and reports both the
publication's printed 2.576 and the implementation's intentional full normal
quantile. On the biased fixture, implementation and full-quantile oracle were
identical at `0.013967921512015244`. The tiny 2.576 difference remains prior
F07/#22, not a new finding.

Before that comparison, the oracle returned exactly zero for the analytically
tractable constant source. It was also checked against the §6.3.1 worked
example. Applying the normative formula to `L=20`, `p̂=.4` gives
`p_u=.6895174`, entropy `.5363411`, matching the publication's original rounded
result. The 2025 potential errata's `.6822`/`.5518` instead follows its displayed
rounded intermediate `sqrt(.012)`. Because the potential errata does not change
the normative formula and is explicitly not official, this discrepancy was
recorded rather than used to alter the oracle or label the implementation.

The one-bit uniform IID control passed in release and sanitizer builds with an
identical assessed figure `0.993899`. A standards-sized alternating IID input
hit the already known upstream #153 LRS assertion (`p_colPower >= LDBL_MIN`)
and produced no JSON. With assertions disabled, the same alternating case
crossed that point, emitted `igamc: UNDERFLOW`, and was bounded after 10 minutes
8 seconds without producing JSON. The drift IID test was likewise interrupted
after ten minutes with no result. No correctness verdict is inferred from
either incomplete run. The valid-input #252 aggregate reporting problem remains
an existing blocker, not a new finding.

The non-IID restart control at 1,000×1,000 and supplied `H_I=.8` produced
`h_r=.838909`, `h_c=.829529`, and `h_i=.8`. A deterministic periodic restart
matrix was rejected by the sanity check with exit 255 and error level -1.
The IID restart mode on the same valid uniform matrix passed all required IID
tests and reported `h_r=h_c=.993899`, `h_i=.8`. Its one combined “Overall”
case contains two indistinguishable groups of permutation iterations and
mean/median zero, confirming existing `NOVEL-03`/`N-10` without creating a new
finding.

All supported symbol widths 1 through 8 were therefore exercised with exactly
1,000,000 symbols and an explicit width. Every JSON report recorded the same
effective width that was supplied.

## Memory safety, numeric behavior, and concurrency

ASan/UBSan builds of all three programs succeeded after explicitly adding the
Homebrew libomp include path. The initial missing-header failure is retained in
the same build log rather than erased.

- Valid non-IID and IID uniform controls were sanitizer-clean and exactly
  matched release results.
- A valid restart run reproduced existing `C-01`: `new uint16_t[]` at
  `restart_main.cpp:124` is released with scalar `delete` at line 161. ASan
  exited 6. This is not a new finding.
- Forty bounded invalid-input cases (lengths 0 through 999,999 across non-IID,
  IID, and restart entry points) rejected with expected status 255 and no new
  sanitizer diagnosis.
- A separate `-O2 -DNDEBUG` build of all three supported programs succeeded.
  Valid non-IID and restart final values exactly matched the assertion-enabled
  release build; IID passed the same required tests with the same entropy value
  (individual stochastic permutation counters differed). All three still
  rejected a 10,000-sample input with status 255. The additional alternating
  IID edge probe described above was bounded incomplete and is not counted as
  a pass.
- Clang static analysis completed for all three entry points; its only reports
  were dead stores in chi-square code.
- Non-IID output was byte-identical with `OMP_NUM_THREADS=1` and 8. Restart and
  IID stochastic decisions remain subject to their documented randomness and
  platform behavior. Failure to read `/dev/urandom` is checked and fails
  closed in the inspected seed path.
- macOS LeakSanitizer is unavailable. Linux/x86-64, Windows, big-endian,
  changing-file races, a current ThreadSanitizer run, and current cross-compiler
  comparisons were not run. Race assurance is therefore limited to source
  review and the observed thread-count comparison, not dynamic race detection.

Linked runtime libraries are system `libbz2`, `libSystem`, and `libc++`, plus
Homebrew libdivsufsort 2.0.1, libomp 23.1.2, jsoncpp 1.9.8, and OpenSSL 3.6.4.
`ea_non_iid` is linked with OpenMP and bz2 through common build flags even where
that program does not materially use all of them. NOTICE includes dependency
attribution. MPFR/GMP apply to the unbuilt conditioning program, not the
verified TruePad runtime path.

Homebrew's machine-readable formula metadata labels the installed libomp
formula `MIT`, while this repository's NOTICE identifies the LLVM runtime as
`Apache-2.0 WITH LLVM-exception`. The latter is the project's documented
licensing basis, but release evidence should normalize the metadata source so
the recorded license is not internally ambiguous. This audit found no bundled
third-party binary or confirmed runtime license violation.

## CLI, reporting, and provenance

Current fork guards correctly reject undersized ordinary input, record the
noncompliance under the explicit internal short-data override, propagate
missing binaries, reject JSON write failure in supported programs, and refuse
nonregular inputs. Text/JSON checks on the valid battery were mutually
consistent for final values.

No new stale-output or nonfinite-acceptance path was verified. TruePad itself
checks subprocess exit/signal, exact JSON version/IID/error fields, finite
one-bit ranges, input hashes, exact sample representation/counts, selected ≤
assessed entropy, restart dimensions, matching device serials, and a fresh
output directory. Those controls are real, but they trust the unauthenticated
programs described in `TP-AUD-01`.

Existing `N-07` remains: the tools hash the pathname before separately opening
and reading it for assessment, and do not prove both observations saw identical
bytes. TruePad pre-hashes too, but its later tool run still reopens the path; a
file-change race is therefore not closed by the integration. Existing `N-10`
and `NOVEL-03` reporting-label issues also remain.

## TruePad extraction contract and physical limits

Targeted TruePad qualification, Toeplitz, seed, extraction, and pre-RNG tests
passed: 10 files, 71 tests. The qualification command correctly uses one raw
source bit per file byte, passes explicit width 1, chooses the non-IID track,
and passes the conservative selected rate into restart testing.

TruePad's Toeplitz budgeting implements the documented leftover-hash-lemma
shape `m <= floor(n × h × (1-margin)) - 2e + 2`, with default security parameter
64 and margin 20%; the seed length is checked as `n+m-1`. Its documentation
correctly says an externally asserted seed must be uniform and independent,
and that a second raw capture does not establish those properties. The OS-CSPRNG
route is an explicitly computational alternative, not a physical assertion.

The OS-CSPRNG seed workflow creates fresh bytes for each request. The manual
external workflow records the seed-file SHA-256 but has no cross-extraction
registry that rejects the same seed again. Seed reuse is not automatically
unsafe for every strong-extractor composition, but its bound depends on the
joint source/side-information assumptions. Those assumptions are not
established here, so a conservative TruePad ceremony needs a documented fresh-
seed-per-extraction rule or a separate proof covering reuse. Assessment
captures, operational raw material, and seed files have distinct recorded
roles; that separation is necessary but does not by itself prove independence.

Software cannot establish that the Infinite Noise source has the assumed
conditional min-entropy, that separate captures are independent, that restart
operations model deployment, or that environmental and adversarial conditions
were covered. Offline SP 800-90B assessment does not replace startup and
continuous health tests. Toeplitz extraction is not classified here as a
NIST-vetted conditioning component. One-time-pad security additionally needs
uniform independent pad material, secret generation/transport/storage,
never-reused key material at least as long as the message, and correct endpoint
erasure—none follows from these software tests.

## Prioritized recommendations

1. Block production qualification until `TP-AUD-01` is fixed with manifest-
   bound executable and selftest verification plus substitution/deletion tests.
2. Resolve `TP-AUD-02` by selecting and independently reviewing one exact fork
   commit everywhere; then rebuild and repeat the whole product qualification.
3. Repair existing `C-01` and close or operationally eliminate `N-07` before
   trusting restart or provenance evidence.
4. Require consumers to reject anything other than a complete, authenticated,
   supported-version qualification bundle; never infer success from a report's
   existence or stale path.
5. Obtain independent physical-source, restart, health-test, operating-range,
   and extractor-seed evidence before assigning any production entropy budget.
6. Add an exact fixture manifest/count to the repository selftest and update
   BUILDING's obsolete regression count.
7. Complete current Linux/x86-64 and Windows strict/sanitizer coverage before
   claiming those platforms are supported.

## Scope statement

This was an audit, not a repair. No production source, historical report,
reference output, test expectation, TruePad file, commit, issue, PR, or remote
branch was changed. Builds and the executable-substitution experiment occurred
only in detached/disposable worktrees. The only working-checkout additions are
this new audit directory. No real pad material, extractor seed, private capture,
or sensitive data was used or preserved.

This report does **not** claim NIST approval, certification, guaranteed entropy,
physical unpredictability, extraction security, or one-time-pad security.
