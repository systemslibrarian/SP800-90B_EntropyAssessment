# Verified-defect remediation handoff

This directory records repair-engineering evidence for the findings assigned
on 2026-10-09. It does not alter or supersede the sealed independent audit in
`audits/2026-10-09-independent-audit/`, and it is not an independent
verification.

The production-code revision selected by TruePad is
`b3db7ab17692d5b577f8558f4fecee6a5cb98ce6`, tree
`5697a86c5f3bf79e3296f03d67dbe243527150ee`. Later commits in this repair
branch contain handoff evidence only; TruePad intentionally pins the reviewed
code revision rather than a moving branch.

| Finding | Root cause | Repair commits | Permanent controls | Repair-engineer status |
|---|---|---|---|---|
| HARNESS-AUD-01 | The selftest discovered whatever pairs remained on disk, so deleting a complete pair reduced coverage without failure. | `65de84c` | Authoritative 11-pair hash manifest and seven mutation cases in `regression-selftest-inventory.sh`. | Repaired; independent verification pending. |
| C-01 | `simulateBound()` allocated `new uint16_t[]` and freed it with scalar `delete`. | `6f84ad7`, `b3db7ab` | Exact 1000×1000 ASan/UBSan control; detector is forced with `alloc_dealloc_mismatch=1`. | Fixed build passes; vulnerable parent aborts at line 161; independent verification pending. |
| N-07 | The report hashed a pathname in a separate pass from the estimator read. | `c01fb43` | Hash the exact loaded sample buffer; deterministic pathname replacement regression; subset identity regression. | Repaired in all three supported tools; independent verification pending. |
| IID #153/#252 | The IID LRS test formed an underflowing `p_col^W`; failed required tests did not gate the aggregate verdict or final entropy. | `a3dde6f`, `007d0e7` | Log-domain §5.2.5 oracle, widths 1–8 at exactly 1,000,000 samples, binary/nonbinary positive controls, and IID restart rejection. | Repaired; independent verification pending. |

## Final verification on the selected code revision

- Clean supported build: `ea_non_iid`, `ea_iid`, and `ea_restart` built with
  Apple clang 21.0.0 on arm64 macOS 26.6.2.
- Strict suite: `18 passed, 1 failed (17 regression scripts discovered)`.
  The only failure was the unwaived, documented macOS #155 reference delta for
  `biased-random-bytes.bin` and `ringOsc-nist.bin`.
- Documented platform mode: `19 passed, 0 failed (17 regression scripts
  discovered)`.
- C-01 sanitizer: fixed exact-dimension run passed ASan/UBSan. The vulnerable
  parent `65de84c` aborted with status 134 and
  `alloc-dealloc-mismatch (operator new [] vs operator delete)` at
  `restart_main.cpp:161`.
- IID negative controls at widths 1–8 returned status 1, `IID:false`, omitted
  `hAssessed`, and matched an independent log-domain LRS decision. The
  reviewed one-million-sample binary and nonbinary controls passed.

Release-build SHA-256 values from the final local build:

| Executable | SHA-256 |
|---|---|
| `cpp/ea_non_iid` | `51552d829c342cda967f3f36587079617147ae9ffb43ca46626fedf3bb8c63d1` |
| `cpp/ea_iid` | `92284eeda542cb21f667d6fb29ade644290253e4c8ca280bf4347139754c6cba` |
| `cpp/ea_restart` | `43b532b4da52183f2ed36dbbc569ae576b71ee41e86912858de8552dbc784fbb` |

These local hashes are test evidence, not an approved TruePad artifact
allowlist. TruePad production approval remains disabled pending a separate
independent build review.

## Deterministic fixture identities

`regression-iid-failclosed.sh` generates one million samples with Python's
`random.Random(153000 + width)`, then duplicates samples `[0,2100)` at
`[500000,502100)`. Its SHA-256 values for widths 1 through 8 are, in order:

1. `886dabfe0c8c2d54c6282ad9f661161d99d7374bf59db87d9d48014cdcbfb3e9`
2. `9a2dca2ef661f10b049e32eccbd79cd607b9f0c60e2f9ac155dbd66d2398cb77`
3. `d50720256a465bc56c6e8820330c1cb7962392524c6e7292b6817ceb07273cd3`
4. `7cf9183572156e8539fedc88d813359e01349e4c39d98776848a6e9dcfa4acc1`
5. `8bea6923d387c562712258539981130f6e079888fb4781cdbaf8f775699e1eaf`
6. `4670379dafcf29e3eeedc275beade7afeb1c6cf2115a195fdb2a1a9f6c58f0db`
7. `829e8d56e95693c1262ce94a498d4ec39664ab6ebd537638b46f5276f3f2b1b2`
8. `d61c4b3a57479b6ed4e94f05269bfe12c5f910582b2c3fffedd41492d120491c`

The exact 1000×1000 checkerboard restart control is
`fa54573ed95090d473e6296b7bb945c97e3cced2e4a80ed40fc008536b9aa01d`.
Generated sample files and sanitizer build trees remain outside tracked source.

## Limits

Linux and Windows builds were not available in this repair environment.
Passing software controls do not validate a physical entropy source,
stationarity, operating conditions, health-test suitability, extractor-seed
quality or independence, pad transfer, or one-time-pad security.

## Merged into master — 2026-10-15

Authorised by Paul on 2026-10-15, lifting `REPAIR-BLOCK-01` on the finding
(`audits/2026-10-11-independent-audit/REPAIR-STRATEGY.md`) that its premise did
not survive the log-domain rewrite. Merge commit `d226f18`, a true `--no-ff`
merge so the hashes this directory pins (`b3db7ab`, tree `5697a86`) are
unchanged. The last pre-merge master is tagged
**`unrepaired-reference-2026-10-15`**; how to build the reference figure from it
is in `BUILDING.md` ("The unrepaired reference tool").

Two semantic conflicts were resolved in the merge commit: master's
`regression-outside-battery.sh` was added to `regression-script-inventory.txt`
(now 18 scripts, 20 checks), and six `fixture-manifest.txt` hashes were re-pinned
to the reference files master had amended in `OC-21` (derived line appended;
provenance in each file). Post-merge validation — build-differential (asserts
live vs `-DNDEBUG` agree and refuse), the full suite in both modes, and the
inventory mutation controls — is recorded in
`audits/2026-10-11-independent-audit/logs/merge/` and `REPAIR-STRATEGY.md`
("Register after the merge").

The repairs remain **self-authored and unreviewed**. Merging does not change
their evidentiary standing; "independent verification pending" in the table
above still holds.
