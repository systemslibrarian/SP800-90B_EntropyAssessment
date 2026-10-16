# IND-02 regression-inventory remediation

This is repair-engineering evidence, not an independent audit. It does not
modify or supersede `audits/2026-10-09-independent-audit/` or its manifest.

## Source identity

- Repository: `https://github.com/systemslibrarian/SP800-90B_EntropyAssessment.git`
- Repair branch: `repair/2026-10-09-verified-defects`
- Prior independently reviewed tip: `99dfb82418bbdb68635368a5cd8fce242e181ab6`
- IND-02 code commit: `ea87f1e1321594a421b949c855bf4e59da0a72c5`
- IND-02 code tree: `f1b97935a6a6e0eea91fa15e4a1c65100ddb6789`

## Finding and repair

**IND-02:** `cpp/selftest/run-all-checks.sh` discovered whichever
`regression-*.sh` files remained and failed only when it found none. Removing
`regression-docs.sh` therefore produced:

```text
run-all-checks: 18 passed, 0 failed (16 regression scripts discovered)
exit 0
```

The same result was reproduced with the actual suite and with the isolated
control saved as `before-missing-script.log`.

The repair adds `regression-script-inventory.txt` as the authoritative
version-controlled list of 17 scripts. Before running any check, the standalone
harness now requires:

- exactly 17 well-formed, unique inventory entries;
- every listed script to exist and be executable;
- every discovered `regression-*.sh` to be listed;
- no missing, injected, renamed, or duplicate script; and
- exactly 17 executed regression scripts and 19 total checks.

Inventory/configuration failures exit 2. Test failures retain exit 1. The final
summary format remains compatible with TruePad's independent count parser.

`harness-inventory-mutation-test.sh` is a standalone, inexpensive mutation
control. It does not call the TruePad wrapper. It verifies a 19/19 positive
control and proves that deletion, injection, rename, and duplicate-inventory
mutations all return nonzero.

## Changed files

- `cpp/selftest/run-all-checks.sh`
- `cpp/selftest/regression-script-inventory.txt`
- `cpp/selftest/harness-inventory-mutation-test.sh`

No estimator implementation, reference output, fixture, platform tolerance, or
historical audit artifact changed.

## Verification

| Command/control | Result |
|---|---|
| Baseline missing-script reproduction | 18 passed, 0 failed, 16 scripts; exit 0 |
| `cpp/selftest/harness-inventory-mutation-test.sh` | PASS: complete, deletion, injection, rename, duplicate controls |
| `bash cpp/selftest/run-all-checks.sh` | 18 passed, 1 failed, 17 scripts; exit 1 |
| Strict failure classification | Exactly the documented macOS upstream #155 deltas: `biased-random-bytes.bin`, `ringOsc-nist.bin` |
| `bash cpp/selftest/run-all-checks.sh --allow-known-platform-deltas` | 19 passed, 0 failed, 17 scripts; exit 0 |
| 1,000,000-sample period-two `ea_iid -i` | Exit 1; `IID:false`; `errorLevel:2`; no `hAssessed`; LRS false |

The period-two input SHA-256 was
`2ba607832cf7dd10179fb3b0f1dbf99393e5d3a1f12c1752b07dd62c8ca2ebc3`;
the tool reported the same assessed-input digest and sample count 1,000,000.

Release-build hashes used for this repair validation are recorded in
`source-and-binaries.log`. They are evidence, not an approved production
artifact allowlist.

## Evidence files

- `before-missing-script.log` — isolated reproduction of the old 16-script
  green result.
- `inventory-mutation-controls.log` — standalone post-repair mutations.
- `strict-suite.log` — complete strict harness output.
- `platform-suite.log` — complete documented macOS-mode output.
- `period-two-result.json` — exact estimator result for the deterministic
  million-sample negative control.
- `source-and-binaries.log` — repository/commit/tree, binary hashes, and first
  version lines.
- `results.json` — machine-readable summary.
- `rerun.sh` — reproducible commands for an exact code checkout.
- `MANIFEST.sha256` — digest inventory for this new evidence directory.

## Limits

Validation ran on arm64 macOS with Apple clang 21. Linux and Windows were not
run. No Infinite Noise device or other physical entropy source was used. These
tests establish software coverage accounting and preserve estimator regressions;
they do not prove physical randomness, source stationarity, exact uniformity,
extractor-seed quality, or OTP security.
