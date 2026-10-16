# Independent review boundary: where testing stops

This document records claims that the repair engineer's regressions cannot
establish. It is a review boundary, not another test report and not an approval
of an entropy-assessment build or of TruePad pad material.

## The two most important limits

1. **The same process wrote the fixes and their evidence.** The implementation,
   regressions, expected outcomes, and repair narrative can share one mistaken
   interpretation or omitted assumption. IND-01 is a concrete example: the
   repair process's own model of the version output did not match the real
   reviewed executables. Green self-authored regressions therefore cannot serve
   as independent confirmation of the model they encode.

2. **The producer must not approve its own artifact.** Release governance must
   separate the party producing a candidate build from the authority approving
   it for production. Whether the project owner has that independent authority,
   and who may add, revoke, or distribute an approval, are facts about people,
   roles, and operational control rather than facts the code can prove about
   itself.

## Nine matters requiring independent evidence or judgment

1. **Source-to-binary trust.** A digest identifies bytes; it does not prove that
   those bytes were produced from the reviewed source by the declared compiler,
   dependencies, flags, and build host, or that the supply chain was
   uncompromised. Every supported production artifact needs an independently
   reproduced or otherwise independently verified provenance chain.

2. **Independence of the correctness argument.** A reviewer must independently
   derive the security requirements and mathematical expectations from NIST SP
   800-90B and the TruePad threat model. Reusing the repair's assumptions or
   expected outputs does not supply an independent result.

3. **Completeness of the trust boundary.** Regressions demonstrate specified
   attacks, not the absence of unmodeled paths such as alternate executables,
   legacy parsers, packaging differences, update mechanisms, policy
   replacement, rollback, path or canonicalization ambiguities, and
   platform-specific filesystem or process behavior.

4. **Trustworthiness of the approval authority.** An independent review must
   establish who may approve or revoke a build, how the manifest is
   authenticated and distributed, how rollback and compromise are handled, and
   how governance prevents the producer from approving its own artifact.

5. **Mathematical correctness across the supported domain.** Finite regression
   cases cannot prove that no untested estimator boundary, numeric condition,
   representation, or aggregation path can overestimate entropy. This requires
   independent code review and independently derived oracles, especially for
   decisions that can increase the accepted entropy bound.

6. **The actual release integration.** Repository tests cannot prove that a
   packaged TruePad release executes the reviewed binary, ships the reviewed
   policy, uses the intended invocation and parser, and exposes no alternate
   approval route on every supported platform.

7. **Physical entropy-source assumptions.** Software assessment cannot
   establish source independence, stationarity, environmental stability,
   health-test suitability, capture authenticity, or continued behavior in
   production.

8. **Extraction and one-time-pad prerequisites.** Tests cannot prove Toeplitz
   seed independence or quality, correct operational entropy budgeting, pad
   secrecy, non-reuse, secure transfer, endpoint integrity, or erasure.

9. **Genuine independent approval.** Passing repair-engineer tests cannot make
   the repair independently verified. A separate reviewer must reproduce the
   evidence from clean checkouts, examine the assumptions rather than merely
   the expected outputs, and issue an approval decision through a separately
   controlled process.

## Production consequence

Merging repair code is not approval of any assessment executable. TruePad's
`productionApprovalEnabled` setting must remain `false`, and its production
allowlist must remain empty, until independent review and artifact approval are
complete.
