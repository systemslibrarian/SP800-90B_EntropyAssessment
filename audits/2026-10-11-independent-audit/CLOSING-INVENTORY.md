# What is left — closing inventory

Date: 2026-10-19. State: `master` at the commit adding this file.
Written to be read cold, by someone who has not followed the work.

## What this repository is, in four sentences

It is a patched fork of NIST's SP 800-90B reference implementation, which
estimates the min-entropy of a noise source. The figure it reports prices the
output length of a one-time pad in a separate tool, so the number has to be
defensible rather than merely produced. Three executables are built and
supported — `ea_non_iid`, `ea_iid`, `ea_restart`; `ea_conditioning` and
`ea_transpose` are deliberately not. **Every repair in this fork is
self-authored and unreviewed, the owner has decided there will be no
independent human review and that nothing will be reported upstream, and no
physical noise source has been measured.**

## The two numbers, and how to get them

A figure from this fork is only interpretable with its provenance and its floor.

```sh
# 1. which tree is this binary from?
tools/build-provenance-canary.sh cpp/ea_iid          # expect TREE REPAIRED
# 2. the assessment
cpp/ea_non_iid -i -a -q -o report.json <capture.bin> <bits_per_symbol>
# 3. the floor, with every subtracted term named
python3 audits/2026-10-11-independent-audit/oracles/entropy_floor.py report.json
# 4. if a restart dataset exists, the acceptance decision -- NOT a subtraction
cpp/ea_restart -i -v -o restart.json <restart.bin> <bits_per_symbol> <H_I>/symbol
python3 audits/2026-10-11-independent-audit/oracles/restart_decision_exact.py restart.json
```

The reference tool's own unrepaired figure must be reportable alongside the
fork's, with the difference explained. Build it from tag
`unrepaired-reference-2026-10-15`; the steps, and the two gaps in the
instructions the tag itself carries, are in
[docs/TAG-unrepaired-reference-2026-10-15.md](../../docs/TAG-unrepaired-reference-2026-10-15.md).

## Needs nothing — can be done here, now

| item | what it is | why it is still open |
|---|---|---|
| **`oac-13`** the report write is not atomic — the last item in `C08` | A signal during the write leaves truncated JSON at the operator's path. `C14`'s placeholder narrowed this from "stale valid report" to "invalid JSON", which a consumer can detect by parsing, but did not close it. The rest of `C08` is **done** (`OC-38`): `errorClass` distinguishes `input` / `statistical` / `internal`, the filename is recorded on failure paths, and a comma-operator bug that was publishing the literal string `"Error: '%s' is empty"` to operators is fixed, with exit codes unchanged. | Write to a temporary file and rename. Small. |
| **`R-1`** `assert(p_col >= 1/k)` aborts on valid balanced data | **Moved here from the x86-64 bucket on 2026-10-19 (`OC-40`): it is a live defect, measured.** On x86-64 `ea_iid` aborts with SIGABRT and writes no report for perfectly balanced alphabets at k = 3, 6, 7, 9 and 12. Invisible on arm64, which is why it sat mislabelled for so long. Upstream code at `lrs_test.h:652`, unchanged by this fork. | The repair shape is known — clamp `p_col` to `1/k` when the shortfall is within rounding, or accumulate `Σcᵢ²/L²` exactly — and the `C07` precedent (`a3dde6f` replaced asserts with log-domain arithmetic) shows this project does repair this class. **Needs an owner decision first**, because it changes an upstream assert in an estimator path and the standing rule is that estimator logic must never change by accident. A regression must fail against the current build, which now means it must run on x86-64 — the CI job is the place for it. |
| **`F13`** NaN into `std::min` | `shared/utils.h:1153` suppresses a NaN only because `1.0` is written as the **first** argument of `min`. Swap them — a change a reviewer would read as cosmetic — and the NaN reaches the returned estimate. | Carried `UNCONFIRMED` since the batch phase. The property is incidental and still unmarked at the site. A comment, or explicit `fmax`-style handling, plus a regression that fails against the swapped form. |
| **`C22c`** at other sample counts | `entropy_floor.py` refuses any `n` below 1,000,000 bits, and uses the value measured at the largest measured `n` not exceeding the actual one, because the `ZALPHA` ceiling was measured at 1e6 and 8e6 only. | One oracle run per additional `n`. Needed only if the project ever assesses a different length. |
| **`regression-estimator-guards` is macOS-only** | Its sanitizer build command carries Homebrew library paths and macOS OpenMP flags, so on Linux it fails at the link step and reports COULD NOT RUN (`OC-40`). That is the correct outcome — a check that did not execute supports no claim — but it means one regression has no second-platform coverage, and the suite's total-count check fails closed on Linux as a result. | Make the build command detect its platform the way `cpp/Makefile` already does. Small. |
| **`C06`** `h_out` exceeds the output's bit ceiling | `ea_conditioning` reports `h_out` 7.1552 for a 7-bit output. | The *measurement* needs nothing, which is why it is here; the tool it concerns is deliberately not built (see the last bucket). |

## Needs an x86-64 host — which turned out to be a workflow file, not a machine

**This bucket was wrong.** It read "one machine briefly", and nobody has an
x86-64 machine. `ubuntu-latest` on GitHub Actions is x86-64 Linux on glibc,
where `long double` is x87 80-bit extended — the exact format every
float-environment claim in this audit argues about from the source rather than
observing. The repository is public and Actions is enabled, so the whole bucket
is reachable for free.

`.github/workflows/x86-64-platform-facts.yml`, manually triggered
(`workflow_dispatch`), prints the float environment rather than assuming it,
builds both configurations of master and of the tag, runs the canary on all
four plus a non-tool control, runs `R-1` at all five symbol counts, and runs the
full suite and the outside-battery regression so the pinned figures get a second
platform. Logs upload as artifacts. Its R-1 step classifies on positive markers,
so a usage message, a crash, a timeout and a completed run are distinguishable
(`OC-36`'s absence rule, applied in the code that would otherwise repeat the
error that taught it).

**It has been run (`OC-40`, 2026-10-19), and the bucket is answered:**

| item | what the job found |
|---|---|
| the float environment | x87 80-bit extended confirmed: `LDBL_MANT_DIG 64`, `LDBL_MIN 3.3621e-4932`, `FLT_EVAL_METHOD 0`. **Printed, not argued.** |
| the canary signatures | Four of five outcomes exactly as argued. The fifth — the tag's asserts-live build — aborted at the predicted site but was reported INDETERMINATE because the signature matched macOS/clang's `"Assertion failed"` wording and glibc words it differently. **The arithmetic held; the instrument's string match did not.** Fixed and verified on both wordings. |
| **`R-1`** | **LIVE on x86-64**, aborting at all five symbol counts on valid balanced data, and invisible on arm64. Tracker state is now `REPRODUCIBLE-ON-X86-64`. This is the one item that moved from "probably nothing" to "a real upstream defect on the platform most users run". **It is now in the first bucket**: it needs no hardware, only a decision about whether this fork repairs an upstream assert it did not write. |
| the pinned figures | `regression-outside-battery` **PASS** on x86-64 — the first independent-platform confirmation of the 0/25, B, E and Compression-binding figures. Both mutation harnesses pass there too. |
| **`REPRO-01`** | partially: the wide-format side of the LRS underflow is now observed rather than argued. |

**What CI still cannot reach.** `C18` needs **Windows/LLP64**, where `long` is
32 bits — not merely x86-64 — and the Windows build route is documented and has
never been run; a `windows-latest` job with an MSYS2 toolchain is the obvious
next step and is not written. Linux **aarch64** (binary128, 113-bit
significand) is not a standard GitHub-hosted runner.

## Needs the physical device — arriving January 2027

Everything here is **NOT RUN** and stays NOT RUN. Synthetic data establishes
claims about instruments, never about sources.

| item | what it needs the device for |
|---|---|
| **the restart assessment** | A real restart dataset, decided with the corrected cutoff and **not** with §3.1.4.3's printed binomial formula, which rejects correctly-operating sources (`OC-30`, `XR-11`). The decision must be computed, recorded with `X_max`, `H_I`, the cutoff, the method and the binary's identity, and never upgraded by a later repair. **At the width-1 operating point the two cutoffs are identical below H_I ≈ 0.989, so for this device the `C23` repair changes no verdict** — the table to read a cutoff out of is `XR-13`, and the entropy figure itself is still unmeasured. |
| **the per-device baseline** | `XR-07`: a defect can be invisible to the estimator battery **and** to the outside-battery check at once, so the per-estimator breakdown needs a per-device baseline — and that baseline cannot be synthesised, by construction. |
| **the pinned figure** | `pin-check.sh` is pinned on an upstream sample. It is to be re-based on a real capture when one exists (steps in `BUILDING.md`). |
| **the 0.696 figure** | One unit's measurement, uninterpretable pending build provenance. |
| **health-test and operating-range evidence** | Not an estimator question at all; the estimator cannot produce it. |

## Needs a decision from the owner

| question | why it is a decision and not a task |
|---|---|
| **Upstream issue #253 is still open.** | `F01` was withdrawn and the PR closed, but closing the issue was never authorised. With "nothing upstream" standing, it stays open indefinitely unless the owner says otherwise. |
| **Force POSIX argument order (`+` on each `getopt` optstring).** | GNU getopt permutes and BSD does not, so an argument beginning with `-` is consumed differently on Linux and macOS (`OC-40`). Both platforms refuse bad input, so this is reproducibility rather than safety. A one-character change per tool, but a behaviour change on Linux: options after the filename would stop being recognised there, which is already the macOS behaviour and already what `C21` documents. |
| **Hill's third proposal.** | `OC-30` implements the exact multinomial maximum. Hill also proposes a *corrected binomial* restart check — count one fixed symbol, chosen from the whole dataset — which is easier to model but has less statistical power. Adopting it, or offering it, is a design choice. |
| **Whether the fork's figure is ever reported alone.** | The standing rule is two figures, always. Relaxing it would be an owner decision, and nothing in the audit supports relaxing it. |
| **`productionApprovalEnabled`.** | Stays `false` with `approvedBuilds` empty. Flipping it depends on independent review, build verification and physical evidence, none of which exist; it is listed here because it is the decision everything else feeds. |

## Will not be done — and why, permanently

This bucket is not a queue. Nothing here is pending.

| item | why not |
|---|---|
| **Independent review of any repair.** | The owner has decided there will be none. Every "independent verification remains" note in `audits/2026-09-30/FINDINGS-TRACKER.md` — including `C-01`'s, which is otherwise fixed — resolves here. **REPAIRED is not REVIEWED, and on this project it never becomes REVIEWED.** |
| **Any upstream report.** | Decided 2026-10-15, on the basis that an earlier upstream PR went unacknowledged. This includes the strongest findings the audit produced: the `C07`/`C03` chain, `C23`'s undocumented departure from the printed formula (`OC-30`), and the §6.3.1 errata inconsistency that Hill independently corroborates (`OC-32`). `UPSTREAM-REPORT-INVENTORY.md` is kept as documentation of what is wrong with the tool being run, and is not sent. |
| **Regenerating the reference corpus from these tools.** | A reference produced by its subject cannot detect its subject changing. The corpus is made more complete only by derivation from data that predates the current build (`OC-21`). |
| **Trusting the reference corpus.** | Ten of eleven key families are upstream-captured with no independent derivation. It is more complete than it was; it is not more trustworthy. "The selftest still passes" validates nothing on its own — use build-differential, spec-derived oracles, inputs whose verdict is known by construction, and metamorphic relations. |
| **`ea_conditioning` / `ea_transpose` findings** (`N-03`, `N-05`, `N-11`, `C06`, `C09`, most of `C21`) | Not built, deliberately. They become active work before that scope can expand, and expanding it is not planned. |

## The wall

**With `C08` finished and the x86-64 bucket handed to CI, the fork is at the
hardware wall.** What is left in the first bucket is one small item
(`oac-13`'s atomic write) plus measurements nobody needs until the sample length
changes. What is left in the second is Windows, which needs a route that has
never been run. Everything that would move the project's central claim — what
this device's entropy actually is, whether its restart data is accepted, whether
a per-device baseline exists — waits on hardware arriving in January 2027, and
nothing in software substitutes for it.

That is the honest end state of the software work. The lists above are not a
backlog implying progress is pending; they are a record of what the wall is made
of.

## How to tell whether this document has gone stale

`OC-34` exists because the open list had not been checked against the tree since
the merge, and two entries were wrong when it was. The checks are cheap:

```sh
cd cpp && make non_iid iid restart && cd selftest
./run-all-checks.sh --allow-known-platform-deltas   # expect 20 passed, 0 failed
./harness-inventory-mutation-test.sh                # expect 5 of 5 mutations landed
./outside-battery-mutation-test.sh                  # expect 9 of 9 mutations landed
./regression-docs.sh                                # the prose claims that can be checked
```

A mutation harness that reports `MUTATION-DID-NOT-APPLY` is telling you the
harness is broken, not the guard (`mutation-lib.sh`, `OC-33`). An item in the
lists above is live **only** if it has been checked against the current tree;
that is the rule `OC-34` was written to establish, and this document is subject
to it too.
