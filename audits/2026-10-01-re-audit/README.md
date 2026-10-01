# Independent re-audit — 2026-10-01

An independent re-audit of the 2026-09-30 findings and of the repairs made in
response to them. It was run by a separate reviewer against a clean checkout;
no source or documentation in this repository was modified by it, and it made
no commits.

Reviewed snapshot: `34fb906196f8d47da774c88928eff0d8ec08d618`.
Tip at review time: `328ec20c146e43b4eed86424847a106539c70a5a`.

## What is here, and what is not

These are the re-audit's **summary documents**, copied verbatim. The full
evidence archive is 1.3 GB across 35,443 files, most of it disposable build
trees, checkpoints and captured outputs; it is not in this repository and is
not reproducible from it. It was at:

```
/Users/gmcas/reviews/SP800-90B_EntropyAssessment/2026-10-01-astra-7dcecac1/
```

A reader should treat the claims in these documents as resting on evidence
that is **not** verifiable from this checkout alone. What *is* verifiable from
here is the outcome: the five defects the re-audit found are recorded in
[`../2026-09-30/FINDINGS-TRACKER.md`](../2026-09-30/FINDINGS-TRACKER.md) under
"Independent re-audit findings (REV series)", each with the commit that fixed
it, and each fix has a regression test that fails against the build before it.

| File | What it is |
|---|---|
| `REPORT.md` | Full narrative and probe ledger |
| `POSITIVE-REPAIRS.md` | The parent / fixed / mutant triples for the verified repairs |
| `PRIORITY-1-CHECKPOINT.md` | Interim checkpoint |
| `REV-002.md` … `REV-006.md` | Per-finding write-ups |
| `KNOWN-242.md` | Pre-existing upstream issue #242, not a new finding |
| `inventory.json` | Machine-readable index of the archive |

## Scope, in the re-audit's own words

The evidence is solid "scoped to the exact fixtures/platforms/mutations
exercised — this is not a universal-compatibility or production-security
certification."

Three of its claims are **BLOCKED** rather than confirmed or refuted, because
the evidence they depend on could not be located: F14's end-to-end behaviour
above 2^32 blocks, a `checkpoint-6` archive, and a `candidate-25.bin` fixture.
They are not counted as findings in either direction.
