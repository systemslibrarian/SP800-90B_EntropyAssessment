# What is left — closing inventory

Date: **2026-10-20**, rewritten after the Windows measurement (`OC-48`). State:
`master` at the commit adding this revision. Written to be read cold, by
someone who has not followed the work.

**The headline changed in this revision.** The previous version said the fork
had reached the hardware wall and the first bucket was down to one small item.
Measuring Windows **reopened the software work**: it confirmed a defect that
had been a reading of the source for a year (`C18`), and it found a new one in
two repairs this audit itself authored (`C24`). Neither is a wrong figure —
both are fail-closed — but neither existed as a *measured* item before today,
and the first bucket is no longer nearly empty.

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
| **`C24`** the atomic report write is not portable | Windows `rename()` refuses an existing destination (`errno 17`), and `C14` has already placed a placeholder at the `-o` path by the time any report is written, so **every** report write fails there: `Error: could not put the report in place`. Two repairs, each sound under POSIX, jointly non-portable. Measured on `windows-latest`, with a verbatim copy of `TestRunUtils.h:55-80` separating the three cases, and macOS passing all three as the control. | The repair is small, non-numeric and verifiable by the existing Windows job: `MoveFileEx(..., MOVEFILE_REPLACE_EXISTING)` under `_WIN32`, `rename()` elsewhere. **Not done today only because the round that found it forbade source changes.** The tempting `remove()`-then-`rename()` must be refused: it reopens exactly the window `C08` closed. |
| **`F13`** NaN into `std::min` | `shared/utils.h:1153` suppresses a NaN only because `1.0` is written as the **first** argument of `min`. Swap them — a change a reviewer would read as cosmetic — and the NaN reaches the returned estimate. | Carried `UNCONFIRMED` since the batch phase. The property is incidental and still unmarked at the site. A comment, or explicit `fmax`-style handling, plus a regression that fails against the swapped form. |
| **`C22c`** at other sample counts | `entropy_floor.py` refuses any `n` below 1,000,000 bits, and uses the value measured at the largest measured `n` not exceeding the actual one, because the `ZALPHA` ceiling was measured at 1e6 and 8e6 only. | One oracle run per additional `n`. Needed only if the project ever assesses a different length. |
| **`C06`** `h_out` exceeds the output's bit ceiling | `ea_conditioning` reports `h_out` 7.1552 for a 7-bit output. | The *measurement* needs nothing, which is why it is here; the tool it concerns is deliberately not built (see the last bucket). |

`oac-13` has left this bucket: the atomic write was implemented and measured
(`OC-47`), five runs of five leaving a complete document against one of five
before. `C24` is what that repair turned out to cost on a platform it had not
been run on — not a reason to undo it.

## Needs another platform — now genuinely empty, and measured rather than argued

**This bucket was never a machine.** Two CI jobs reach everything in it:

| job | host | trigger |
|---|---|---|
| `.github/workflows/x86-64-platform-facts.yml` | `ubuntu-latest` — x86-64 glibc, x87 80-bit `long double` | every push to `master` and every PR |
| `.github/workflows/windows-platform-facts.yml` | `windows-latest` — MSYS2 MINGW64, x87 80-bit, **LLP64** | manual only; it answers questions and gates nothing |

Everything that was in this bucket has left it:

| was | now |
|---|---|
| the four canary signatures | **observed.** Four of five exactly as argued; the fifth was the instrument's string match, fixed and verified on both libcs |
| **`R-1`** | **measured, diagnosed and repaired** (`OC-41`), and it is a `long double` **format** defect rather than a platform one: 117 of 255 alphabet sizes at 53 bits, **155 of 255 at x87 80-bit on Linux *and* independently on Windows** (`OC-48`) |
| the pinned figures | **confirmed on a second platform** |
| **`REPRO-01`** | the wide-format side of the LRS underflow is observed rather than argued |
| the Linux job's own coverage | the sanitizer build is platform-aware, so the Linux job runs the **whole** suite — "could not run" is never counted as a pass |
| **Windows** — "assessed and not started, pending the owner" | **measured** (`OC-48`). It needed no machine and no owner decision to *measure*; only to *repair*. |
| build state on an unmet platform | the probe **refused** on Windows as designed, and has since been taught PE/COFF as a calibrated fallback; it now gives a real verdict there, labelled `via=full` because that test is the weaker one |

**What Windows measured.** MSYS2 is preinstalled; `libdivsufsort` has no
`mingw-w64` package (`BUILDING.md` is right) and builds from source; `libgomp`
*is* packaged, in `mingw-w64-x86_64-gcc-libs`, which the preinstalled toolchain
does not pull in; all three tools **compile and link**; `ea_non_iid` runs the
complete non-IID battery and produces a figure. And two defects stop the route:
`C18` and `C24`, both **fail-closed**, both now in the owner-decision bucket
with measurements attached rather than readings of the source.

**`C18` is the one that was hiding.** It had sat as a source-only candidate —
"`n_choose_2` computes N in `long int`, which overflows on LLP64 and **would**
corrupt the §5.2.5 decision". It does: for a 1,000,000-sample input the true
N = 499,960,500,780 becomes **−403,189,204**, `Pr(X >= 1)` prints **−0.000367**
where macOS prints **+0.365370**, and the decision at `lrs_test.h:765` compares
against `logl()` of a negative number — **NaN** — so the LRS test fails
**whatever the data**. `reproducers/c18_llp64_overflow.c` reproduces the printed
value exactly from the integer arithmetic alone.

Linux **aarch64** (binary128, 113-bit significand) is not a standard
GitHub-hosted runner. R-1 is the only item that turned on `long double` width,
and it is now confirmed at two widths with the third reasoned from the same
mechanism; nothing else in the audit currently turns on it.

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
| **Does TruePad's harness ever invoke these tools on a user's Windows machine?** | The question has **changed shape** now that Windows is measured (`OC-48`). It no longer decides whether to *measure* Windows; it decides whether to *repair* what the measurement found. If yes: **`C18` must be repaired** — the §5.2.5 LRS test fails unconditionally there on any standards-sized input — and `C24` with it. If no: both close as will-not-be-done, and the measurement is still worth having, because it is what turned `C18` from a reading into a fact. Not answerable from this repository — it is a question about TruePad's deployment. |
| **`C18`: widen `n_choose_2()`'s arithmetic.** | Measured, not argued: `((n*n) - n) / 2` in `long int` wraps on LLP64 and the §5.2.5 decision is then taken against a NaN. The repair is to compute in a fixed-width 64-bit type. It is in the owner's hands rather than the first bucket because it changes an **estimator decision path** — the kind of change this project's hard rule reserves for a deliberate decision — even though the current behaviour is arithmetically indefensible and the direction of the fix is not in doubt. Affects LLP64 only; Linux and macOS are LP64 and unaffected. |
| **`OC-42`'s second half stays UNTESTED on Windows.** | `ea_iid` and `ea_restart` were predicted to die at `seed()`, which opens `/dev/urandom`. They never reach it: `seed()` is called in the permutation stage, and `C18` fails the LRS test first, so the stage is unreachable for any standards-sized input. Repairing `C18` is what would let that prediction be put to the question. Until then it is **untested, not refuted** — and fixing `seed()` remains an entropy-relevant change in its own right. |
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

**The software work is not finished, and that is a change from the previous
revision of this document.** The first bucket is **not empty**: `C24` sits in
it, repairable here and verifiable by the job that found it. `C18` sits one
decision away, with the measurement already in hand. Both arrived from the same
place — running the code somewhere it had never run — and neither was visible
from the development host by any amount of reading.

So the honest statement is two-part:

- **On the software**, the wall moved. It was not where the last revision put
  it, and the thing that moved it was a measurement rather than an argument.
  Whether it moves again depends on whether another platform or another
  instrument is ever pointed at this code, which is now cheap: both CI jobs
  exist and one of them runs on every push.
- **On the project's central claim**, nothing moved and nothing can. What this
  device's entropy actually is, whether its restart data is accepted, whether a
  per-device baseline exists — all wait on hardware arriving **January 2027**,
  and no software work substitutes for it. The physical bucket is still
  entirely **NOT RUN** and stays that way.

What the lists above are a record of: the software wall is made of two
measured, fail-closed, platform-specific defects and one owner decision; the
hardware wall is made of a device that does not exist here yet.

**A note on what this round is really evidence of.** Two repairs — `C14` and
`C08` — were reasoned about, given reproducers, and shown failing before and
passing after. Both arguments were correct. Neither was portable, and no amount
of re-reading either diff would have revealed that. `REPAIRED is not REVIEWED`
has a companion: **verified on the hosts it was verified on.** The Windows job
also caught *itself* in the same error class eight times across nine runs — a
gate that could not tell a missing header from a source incompatibility, two
gates contradicting each other in one verdict log, a probe defeated by a
filename, an input that could not reach the stage under test, four extraction
patterns that took the wrong text, and an `errno` printed one call early. Each
was found by running it, not by reviewing it.

## How to tell whether this document has gone stale

`OC-34` exists because the open list had not been checked against the tree since
the merge, and two entries were wrong when it was. The checks are cheap:

```sh
cd cpp && make non_iid iid restart && cd selftest
./run-all-checks.sh --allow-known-platform-deltas   # expect 20 passed, 0 failed
./harness-inventory-mutation-test.sh                # expect 5 of 5 mutations landed
./outside-battery-mutation-test.sh                  # expect 9 of 9 mutations landed
```

And the two platform jobs, which are the cheap way to find the class of claim
that is true only on the host you wrote it on:

```sh
gh workflow run x86-64-platform-facts.yml     # also runs on every push to master
gh workflow run windows-platform-facts.yml    # manual only; ~8 minutes
gh run download <id>                          # every log is an artefact
```

Read the Windows job's `verdict.log` first. A `GATE FAIL` there is a measured
finding, not a broken job: as of 2026-10-20 the expected failures are
`libdivsufsort` having no package, `C18`, and the three `C24` gates. Anything
else failing is new.
./regression-docs.sh                                # the prose claims that can be checked
```

A mutation harness that reports `MUTATION-DID-NOT-APPLY` is telling you the
harness is broken, not the guard (`mutation-lib.sh`, `OC-33`). An item in the
lists above is live **only** if it has been checked against the current tree;
that is the rule `OC-34` was written to establish, and this document is subject
to it too.
