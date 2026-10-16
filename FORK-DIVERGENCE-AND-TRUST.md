# Fork divergence and external trust assessment

Date: 2026-10-09

## Executive answer

This repository contains a meaningful fork of NIST's SP 800-90B reference
implementation. It does **not** modify or redefine the SP 800-90B standard
itself.

The accurate description is:

> A patched fork of NIST's SP 800-90B reference implementation.

It must not be described as NIST-approved, NIST-certified, the official NIST
tool, or a customized version of the SP 800-90B standard.

Most executable changes are general correctness, safety, reporting, and
fail-closed repairs rather than TruePad-specific estimator mathematics.
TruePad motivated the stricter provenance and production trust boundary, but
the artifact allowlist, executable attestation, immutable input snapshot, and
production approval policy live primarily in the TruePad repository.

The fork is reviewable and unusually well documented, but it is not currently
an independently trusted production entropy authority. Production approval
must remain disabled.

## Quantified divergence from NIST upstream

This comparison uses:

- NIST upstream repository: `https://github.com/usnistgov/SP800-90B_EntropyAssessment`
- NIST upstream `master`: `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`
- Fork repair branch: `repair/2026-10-09-verified-defects`
- Repair branch commit: `9556649077f23e5e7978abb3e77f98122555f967`
- Common ancestor: `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`

The repair branch is 66 commits ahead of NIST upstream and zero commits behind
it.

The complete repository diff contains 658 changed paths, 62,252 added text
lines, and 364 removed text lines. That headline is misleading because audit
evidence dominates it:

| Category | Files | Insertions | Deletions |
|---|---:|---:|---:|
| Production C++ and build code | 17 | 1,063 | 358 |
| Self-tests and regression harness | 27 | 2,907 | 6 |
| Audit and repair evidence | 609 | 57,070 | 0 |
| Other documentation | 4 | 1,212 | 0 |

These categories account for 657 text files. The remaining changed path is a
binary reference artifact and therefore has no textual line count.

The meaningful executable delta is approximately 1,400 lines of production
code churn across 17 files. This is not a cosmetic fork, but it is also not a
62,000-line rewrite of the estimators.

## Why the implementation diverged

### General implementation repairs

The fork repairs behavior that is useful beyond TruePad:

- estimator bounds, convergence, and legitimate no-result handling;
- IID decision and aggregate fail-closed behavior;
- restart-test memory safety;
- strict minimum sample requirements;
- input-size, subset, and symbol-width handling;
- nonregular-file and output-write failures;
- numeric edge cases and nonfinite values;
- accurate final verdict and JSON reporting; and
- regression tests that detect missing fixtures, scripts, binaries, and failed
  comparisons.

Some of these changes alter estimator or verdict behavior. They are intended as
correctness repairs, not product-specific tuning, but they require independent
mathematical review because they touch security-relevant calculations.

### TruePad-driven hardening

TruePad requires properties that a research/reference CLI does not necessarily
provide as a production contract:

- binding results to the exact assessed bytes;
- reporting effective symbol width, sample count, subset, and entropy units;
- failing closed on incomplete or malformed evidence;
- identifying the precise source repository, commit, tree, build, and binary;
- requiring complete authoritative self-tests; and
- separating candidate build evidence from production approval.

The strongest TruePad-specific controls are implemented in TruePad rather than
inside the entropy estimators. The entropy fork supplies stricter tools and
structured evidence; TruePad decides whether a particular reviewed artifact is
eligible to participate in an assessment.

## What the fork does not establish

Neither a favorable entropy estimate nor a passing regression suite proves:

- that a physical source is independent, stationary, or stable across its
  operating range;
- that continuous health tests are appropriate for the deployed source;
- that an extractor seed is uniform, independent, or safely managed;
- that pad material is transferred, stored, consumed, and erased securely;
- that pad bytes are never reused;
- that a compiled artifact came from an uncompromised compiler, dependency
  chain, or build host; or
- that the producer is organizationally independent from the authority that
  approves the artifact.

Those are physical, operational, supply-chain, and governance claims rather
than conclusions the estimator can produce.

## Current unresolved implementation scope

The October 9 audit and subsequent repair work do not close every historical
item:

- `N-08`: permissive numeric parsing remains in direct CLI paths;
- `N-10`: ambiguous report semantics remain;
- `NOVEL-03`: IID restart row and column results retain ambiguous labels;
- `R-1`: the x86-64 80-bit `long double` IID path remains unverified and
  unfixed; and
- `N-03`, `N-05`, and `N-11`: conditioning-tool findings remain deferred while
  `ea_conditioning` is outside the supported TruePad build.

These do not recreate the arbitrary-executable TruePad bypass, but they prevent
an honest claim that every known implementation issue is fixed.

**2026-10-15.** `repair/2026-10-09-verified-defects` is merged into master
(`d226f18`), so the IID fail-closed verdict and the log-domain LRS probability
are now master behaviour (audit clusters `C07` and `C03` closed in fact). The
unrepaired tool is pinned at tag `unrepaired-reference-2026-10-15` for the
two-figure reporting rule. The merge closes those two items and nothing else on
this list; the repairs are self-authored and unreviewed.

The later `IND-01`, `IND-02`, and `IND-03` findings have repair-engineering
fixes and regression evidence. Their remediation commits still require a
separate independent review.

## Will outside reviewers trust the fork?

Not automatically. A security-sensitive fork carries a higher review burden,
especially when it modifies central assessment code while retaining the names
and version conventions of the NIST tools.

Technically sophisticated reviewers can evaluate this fork because the source
revisions, finding history, negative controls, and repair evidence are recorded.
Trust should nevertheless be based on independent evidence rather than the
repair process's own tests.

The strongest route to external trust is:

1. Independently review the production-code delta against normative SP 800-90B
   clauses and independently derived mathematical oracles.
2. Independently verify the later `IND-01`/`IND-02`/`IND-03` remediation.
3. Reproduce or otherwise independently verify each supported platform build.
4. Bind approval to the exact repository, commit, source tree, compiler,
   dependencies, flags, and executable digests.
5. Ensure release governance prevents the artifact producer from approving
   their own artifact.
6. Resolve the remaining supported-path findings or publish an explicit,
   enforced scope that excludes them.
7. Validate Linux and Windows before claiming support for those platforms.
8. Submit generally applicable repairs upstream where practical, reducing the
   long-term private patch surface.
9. Keep physical-source qualification and OTP operational claims separate from
   software estimator correctness.

Upstream acceptance would improve maintainability and external confidence, but
it would not itself constitute NIST certification of TruePad, a physical entropy
source, or generated pad material.

## Current readiness statement

The repaired code — on master since the 2026-10-15 merge — is a suitable
candidate for independent review. It is not sufficient evidence for production
entropy approval.

Until independent source review, build verification, artifact approval,
physical-source evidence, and release-governance requirements are satisfied,
TruePad must retain:

```json
{
  "productionApprovalEnabled": false,
  "approvedBuilds": []
}
```

Merging repair code and approving an entropy-assessment artifact are separate
decisions.
