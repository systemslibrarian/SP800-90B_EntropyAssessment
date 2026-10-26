# What a green run of `run-all-checks.sh` establishes

Measured at `d8060c9`, 2026-10-21, on macOS arm64. Recompute every count with
the commands given.

**Why this file exists.** *"22 passed, 0 failed"* has been the basis of a great
many claims here, and **five of the suite's members have now been found to pass
while testing nothing**, all within two days (`OC-75`). None was found by the
suite. That is not bad luck: **a suite cannot detect its own vacuous members,
because a vacuous member passes.** So the number needs its meaning written down
before it is cited again.

This is not a reassurance. It is the content.

## What each family establishes when it passes

| family | members | a pass establishes | a pass does NOT establish |
|---|---:|---|---|
| **reference comparison** (`selftest` → `compareresults.pl`) | 1 | that ~60–103 estimate values per fixture agree with `refdata/` within 1e-10, **and** that both sides name the same input, sample count and symbol width (`OC-74`, since 2026-10-21) | that `refdata/` is **right**. Ten of eleven references are upstream-captured with no independent derivation. "The self-test passes" validates agreement with a reference, never the reference. |
| **pinned figure** (`pin-check.sh`) | 1 | that one named input, **bound by SHA-256**, still yields 0.12644573619605429 within tolerance, with exactly one `Assessed min entropy` line | that the figure is correct for any device. It is an upstream sample, to be re-based on a real capture in January. |
| **behaviour regressions** (`regression-*.sh`) | 23 | that the specific defect each names does not reproduce, on the inputs each generates | anything about inputs it does not generate, or defects it does not name. Several assert only that a tool did not abort. One member, `regression-workflows.sh`, is not about the tool at all: it `bash -n`s the shell blocks in the CI workflow definitions, and says nothing about whether those workflows' gates are *correct* — only that bash can parse them (`OC-84`). Another, `regression-option-order.sh`, guards a deliberate BEHAVIOUR CHANGE rather than a defect: `OC-104` makes all three tools refuse an option placed after the file operand, because glibc permutes such a line and BSD does not, so one command line named two different operations on two supported platforms. |
| **inventory and corpus integrity** (`verify-fixture-inventory.sh`, `regression-selftest-inventory.sh`, `regression-outside-battery.sh`) | 3 | that the fixture and corpus sets match their manifests, both directions | that a manifest is right. `verify-fixture-inventory.sh` **prints its manifest's digest and does not verify it** (`OC-76`, Tier A). |
| **mutation harnesses** | 3 | that the guards they mutate **can fail**, with each mutation shown to land and a baseline shown accepted | that any *other* member can fail. They cover 3 of 22. |

## What has to be true for the aggregate to mean anything

Five preconditions, with what is mechanically enforced today and what is
believed:

| precondition | status | evidence |
|---|---|---|
| **1. every member can fail** | **BELIEVED, and known false five times.** 3 of 22 scripts are covered by a mutation harness; the rest rest on having been *observed* to fail once, at the time they were written, recorded in the commit if at all. | `ls cpp/selftest/*mutation-test.sh cpp/selftest/regression-deadguard.sh \| wc -l` → 3 |
| **2. every member's inputs exist before an absence is read** | **PARTLY ENFORCED, and it is the minority.** 4 of 22 assert presence or carry a third outcome. | `grep -lE 'HARNESS FAULT\|is absent or empty\|INPUT-DID-NOT-REACH' cpp/selftest/*.sh \| grep -c .` → 4 |
| **3. build state is recorded** | **ENFORCED where declared, and declared by few.** The aggregator now surfaces every declaration and prints the coverage; it is **4 of 24**. The two `-DNDEBUG` arms are now distinguishable, where before they were byte-identical (`OC-66`). | the `build-state:` line in every run |
| **4. no member's claim text is hard-coded** | **ENFORCED, 0 remaining.** `regression-restart.sh` printed "32 H_I values × 2 columns" from an empty loop; its claim line now derives from the pin count and reads `0 comparisons made` when emptied. | `grep -lE 'echo .*[0-9]+ (of\|values\|comparisons\|files\|checks)' cpp/selftest/*.sh \| wc -l` → 0 |
| **5. the suite's own inventory is complete** | **ENFORCED.** Discovery is checked against `regression-script-inventory.txt` and the expected counts; an unlisted script is an inventory error, not a silent addition. A mutation harness proves 5 of 5 inventory mutations are caught. | `./run-all-checks.sh` refuses on a mismatch |

## So, plainly

A green run establishes that **21 named defects do not reproduce on
generated inputs, one pinned figure is unchanged on a digest-bound input, the
fixture and corpus sets match their manifests, and ~98 estimate values per
fixture agree with an upstream reference that describes the same input.**

It does **not** establish that the references are right, that the figure is
right for any device, that members not covered by a mutation harness can fail
at all, or that the binary measured was the one intended in the 19 of 23 checks
that do not say.

**Precondition 1 is the weak one and it is the one that has failed.** Until
every member has been observed to fail against a known-wrong build — the
obligation in the guide's step 5, which the tracker's evidence section records
seven prior violations of — a green suite is a statement about 21 checks
that were each believed to work.

## Re-reading this file

Its truth depends on repository state (instrument rule 11). Re-read it when a
member is added, removed or repaired, when `EXPECTED_TOTAL_CHECKS` changes, or
when the `build-state:` coverage count changes. `regression-docs.sh` checks
that the counts above still match the commands beside them.
