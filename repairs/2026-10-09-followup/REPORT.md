# 2026-10-09 supported-path follow-up repairs

This is repair-engineering evidence, not an independent audit. It does not
alter the sealed evidence under `audits/2026-10-09-independent-audit/`.

## Baseline and environment

- Branch: `repair/2026-10-09-verified-defects`
- Source before these repairs: `95566494c25caa79eef693faef9671bd1e93c933`
- Source after the four root-cause commits: `876ba05da68f741df33d32ade7fb52611d4852e5`
- Upstream and merge base: `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`
- Host: Darwin 25.6.0, arm64, Apple M5
- Compiler: Apple clang 21.0.0 (`arm64-apple-darwin25.6.0`)
- Libraries reported by the package manager: jsoncpp 1.9.8, OpenSSL 3.6.4,
  libdivsufsort 2.0.1, libomp 23.1.2
- Supported compiler flags: `-std=c++11 -Xpreprocessor -fopenmp -O2
  -ffloat-store`; Apple clang warned that `-ffloat-store` is unsupported.

## Test-first record

### N-08 — permissive direct-CLI integer parsing

The permanent negative controls were added first and run against the old
source. The exact summaries were:

```text
regression-subset: FAIL (10 checks)
regression-width: FAIL (6 checks)
regression-restart: FAIL (6 checks)
```

Commit `031d7eefe6801c8370c9882cb81348d7cf1df388` adds one shared,
full-consumption, overflow-checked unsigned-decimal parser and uses it for the
integer arguments of `ea_non_iid`, `ea_iid`, `ea_restart`, and the unsupported
development utility `ea_transpose`. Signs, suffixes, hexadecimal notation,
empty values, and overflow are rejected; a leading zero does not switch the
base to octal. The supported tools return nonzero and do not perform an
assessment after a parse failure.

Post-fix: all three quoted regressions pass. This is a supported-scope repair,
not a claim that `ea_conditioning` was repaired.

### N-10 — ambiguous report statistics

The regression assertions were added before the source change. The exact
failures were:

```text
N-10 JSON uses explicit statistic names: ambiguous or missing fields
N-10 stdout labels the translated median: still says only Median
regression-iid-json: FAIL (2 checks)
N-10 restart reports actual named statistics: missing, zero, or ambiguously named
regression-restart: FAIL (1 checks)
```

Commit `094189cdc6dd2b2d975abcbe00d7018628c50bee` distinguishes
`rawMean` from `translatedSymbolMedian`, uses the explicit translated-domain
label in text, and assigns the actually calculated restart baseline values.
The positive control is a valid one-million-sample sparse-alphabet input whose
raw mean is 127.5 and whose translated-symbol median is 0.5, so equality or a
mere field rename cannot satisfy it.

Post-fix: `regression-iid-json.sh` and `regression-restart.sh` pass. The
conditioning-report instance remains deliberately excluded and unfixed.

### NOVEL-03 — ambiguous IID restart row/column labels

The deterministic report-population unit was written first. Before the source
change it failed to compile at the proposed labelled call, including:

```text
candidate function not viable: requires 2 arguments, but 3 were provided
```

Commit `25fbb54b69a81d96801c63d0acf8bb1282281e58` propagates a
`dataLayout` value with every permutation result. Standalone IID uses `input`;
IID restart uses `rows` for iterations 0, 1, 2 and `columns` for iterations 0,
1, 2. The deterministic unit now reports:

```text
restart-report-label-test: PASS (rows 0,1,2; columns 0,1,2)
```

The full restart regression also passes.

### Supported-build exclusion for conditioning findings

The build-plan assertion was added first. Before the Makefile change it failed
with:

```text
supported build plan drifted: exit 0; missing none; unexpected ea_conditioning ea_transpose
regression-docs: FAIL (1 checks)
```

Commit `876ba05da68f741df33d32ade7fb52611d4852e5` makes `make all`
expand to exactly `ea_non_iid`, `ea_iid`, and `ea_restart`; the documentation
and executable-linkage checks enforce that boundary. `ea_conditioning` and
`ea_transpose` remain explicit development targets, but are not supported
build products. This prevents the unfixed N-03, N-05, and N-11 conditioning
paths from silently entering this fork's supported-build claims. It does not
repair those findings.

## R-1 — blocked on hardware

No R-1 code change was attempted. This host reports `arm64` and
`sizeof(long double) == 8`. The reported defect requires the x86-64 80-bit
extended `long double` path; on this ABI its pre-fix control already passes.
R-1 is therefore `BLOCKED-HARDWARE`, not open repair work here. Verification
requires an x86-64 environment that first reproduces the failure and can
distinguish a repair from a no-op.

## Final verification

Commands and outcomes:

```text
make -C cpp clean && make -C cpp -j4
  exit 0; built ea_non_iid, ea_iid, ea_restart

cpp/selftest/run-all-checks.sh
  run-all-checks: 18 passed, 1 failed (17 regression scripts discovered)
  failed: selftest
  only mismatch: biased-random-bytes.bin ringOsc-nist.bin

cpp/selftest/run-all-checks.sh --allow-known-platform-deltas
  run-all-checks: 19 passed, 0 failed (17 regression scripts discovered)

EA_RESTART_SANITIZER_BIN=<ASan/UBSan build> \
  cpp/selftest/sanitizer-restart-c01.sh
  sanitizer-restart-c01: PASS
```

The strict failure is preserved rather than converted to a pass. The qualified
mode accepts exactly the two documented upstream #155 macOS/arm64 files and no
other failure. Full output is in `logs/`.

Release-build SHA-256 values from this local build are evidence identifiers,
not an approved TruePad allowlist:

| Executable | SHA-256 |
|---|---|
| `cpp/ea_non_iid` | `d4a480703efdb3ac3c50ec7b62393b678a4b8b6ae03a238eba2bf20326110217` |
| `cpp/ea_iid` | `36e6f79d99f8b9805f756a6d523c8d61739258524c0497eab0b0b3d30b102acd` |
| `cpp/ea_restart` | `0db49ca1e03169b42bd2523189e0998a79779d0df51bbe3c846a1dda4cdf3756` |

## Upstream maintenance analysis

[`UPSTREAM-CANDIDATES.md`](UPSTREAM-CANDIDATES.md) classifies every
production-code delta, not only the obvious repairs. The strongest small,
general submissions are:

- C-01: suitable for a one-token `delete[]` PR plus detector-positive and
  valid 1000×1000 sanitizer controls, after coordinating with open PR #242.
- IID #153 residual: suitable as a narrowly split log-domain change, preceded
  by an issue/reopen explaining the standards-valid residual.
- IID #252 fail-closed behavior: generally applicable, but should be
  contributed to the existing open PR #252 rather than opened as a competing
  PR; include restart parity and final-verdict semantics.
- NOVEL-03: suitable as a focused report-integrity PR with the deterministic
  six-result label unit.

No upstream issue, comment, or pull request was created or modified.

## Limits

These are repair-engineer tests written by the same process that wrote the
changes. They cannot provide independent confirmation of the interpretation,
the test oracle, or the release-governance trust boundary. Linux, Windows,
x86-64 80-bit `long double`, and `ea_conditioning` were not tested here.
Production approval must remain disabled until separate independent review.

