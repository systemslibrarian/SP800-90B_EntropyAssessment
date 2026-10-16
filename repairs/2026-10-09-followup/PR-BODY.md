## Summary

Repairs the verified entropy-fork findings without modifying the sealed
independent-audit evidence:

- HARNESS-AUD-01, C-01, N-07, and the applicable IID #153/#252 family;
- IND-02 regression-inventory completeness;
- N-08 strict direct-CLI integer parsing;
- N-10 explicit raw/translated statistic semantics in supported reports;
- NOVEL-03 explicit `input`/`rows`/`columns` permutation-result labels;
- enforced supported-build scope: `ea_non_iid`, `ea_iid`, and `ea_restart`
  only. `ea_conditioning` remains unsupported, so N-03/N-05/N-11 are excluded,
  not represented as repaired.

R-1 was not changed. It is recorded as blocked until x86-64 hardware with an
80-bit `long double` can reproduce and verify that path.

## Verification

- clean supported build: pass;
- strict suite: 18 pass / 1 documented macOS #155 reference delta / 17
  regressions;
- documented macOS mode: 19 pass / 0 fail / 17 regressions;
- exact 1,000,000-sample C-01 ASan/UBSan control: pass;
- authoritative supported-build-plan and no-MPFR/GMP-linkage checks: pass.

The new test-first failures, full logs, hashes, results, and rerun command are
under `repairs/2026-10-09-followup/`. General upstream candidates and the
smallest defensible submissions are in `UPSTREAM-CANDIDATES.md`; no upstream
issue, comment, or pull request was created or modified.

### A-1 evidence correction — 2026-10-10

The hostile review found that the committed N-10 IID regression, transported
onto parent `031d7ee`, fails three checks rather than the two stated in the
original repair report. This branch now preserves the original statement as
superseded and records the reproducible result: ambiguous JSON names,
ambiguous stdout median semantics, and the sparse-alphabet domain control all
fail on the parent (`FAIL (3 checks)`, exit 1). No committed revision of the
intermediate two-control test exists. On reviewed production head `baa51b3`,
the IID JSON and restart regressions both pass; the sparse control reports raw
mean 127.5 and translated median 0.5. Complete correction evidence is under
`repairs/2026-10-09-followup/a1-correction/`.

## Independent-audit boundary

This branch includes the independent audit's findings and their remediation,
but the later remediation still requires separate independent verification.
`INDEPENDENT-REVIEW-BOUNDARY.md` records why self-authored regressions cannot
establish independent correctness or release governance.

The independent audit's own **Not tested** list was:

> Linux/Windows builds; physical Infinite Noise hardware;
> `ea_conditioning`/`ea_transpose` directly; static analyzers (not installed).

Production approval remains disabled. No artifact is approved by this PR, and
no claim of NIST approval or physical-source validation is made.
