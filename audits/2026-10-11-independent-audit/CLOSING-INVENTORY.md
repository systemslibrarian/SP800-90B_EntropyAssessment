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
| **`F13`** NaN into `std::min` | `shared/utils.h:1153` suppresses a NaN only because `1.0` is written as the **first** argument of `min`. Swap them — a change a reviewer would read as cosmetic — and the NaN reaches the returned estimate. | Carried `UNCONFIRMED` since the batch phase. The property is incidental and still unmarked at the site. A comment, or explicit `fmax`-style handling, plus a regression that fails against the swapped form. |
| **`oac-13`** the report write is not atomic | A signal during the write leaves truncated JSON at the operator's path. `C14`'s placeholder narrowed this from "stale valid report" to "invalid JSON", which a consumer can detect, but did not close it. | Write to a temporary file and rename. Small, and the last fail-open-shaped item on the report channel. |
| **`C08`** residue | The named defect — the harness failing open on absent reference data — is **closed**. What remains of the 14-member cluster is that a failure's *cause* is not always distinguishable (`oac-5`: every failure is exit 255; `oac-12`: three file problems share one message). | Diagnosability, never a false success. Worth doing; nothing rests on it. |
| **`C22c`** at other sample counts | `entropy_floor.py` refuses any `n` below 1,000,000 bits because the `ZALPHA` ceiling was measured at 1e6 and 8e6 only. | One run of `OC-22`'s harness per additional `n`. Needed only if the project ever assesses a different length. |
| **`C06`** `h_out` exceeds the output's bit ceiling | `ea_conditioning` reports `h_out` 7.1552 for a 7-bit output. | Computable here, but the tool is not built (below). Listed here because the *measurement* needs nothing. |

## Needs an x86-64 host

One machine, briefly. These are all the same gap: every float-environment claim
in this audit is measured on Apple arm64, where `long double` **is** IEEE
double (53-bit, emin −1021) — the narrowest of the three formats a build can
land on. x87 extended (x86-64) and binary128 (Linux aarch64) share emin −16382.

| item | what one x86-64 run would settle |
|---|---|
| **provenance canary signatures** | `OC-24`/`OC-30` argue from the arithmetic that all four canary signatures hold on the wide formats: at W = 20000 the one underflowing quantity is below every subnormal floor, and the repaired decision has a 13 842 log-unit margin. **That is an argument from reading code, not an observation.** One run of `tools/build-provenance-canary.sh` against each tree on such a host converts it. |
| **`REPRO-01`** | The same input aborts on a 64-bit `long double` and is assessed on an 80-bit one. Pinned by recording the architecture; confirming the other side needs the other side. |
| **`R-1`** | Re-labelled by `OC-34`: it does **not** reproduce here at any of the five symbol counts its tracker entry names, the assert is still in the source, and the fork never touched the function — so it is rounding-sensitive, not hardware-blocked. Whether it fires on a wide `long double` is unknown. |
| **`C18`** LLP64 integer widths | `sizeof(long) = 8` here, so nothing in the cluster can overflow. On Windows/LLP64 `long` is 32-bit and `n_choose_2` could wrap. This one needs **Windows**, not merely x86-64, and the Windows build route is documented and has never been run. |

## Needs the physical device — arriving January 2027

Everything here is **NOT RUN** and stays NOT RUN. Synthetic data establishes
claims about instruments, never about sources.

| item | what it needs the device for |
|---|---|
| **the restart assessment** | A real restart dataset, decided with the corrected cutoff and **not** with §3.1.4.3's printed binomial formula, which rejects correctly-operating sources (`OC-30`, `XR-11`). The decision must be computed, recorded with `X_max`, `H_I`, the cutoff, the method and the binary's identity, and never upgraded by a later repair. |
| **the per-device baseline** | `XR-07`: a defect can be invisible to the estimator battery **and** to the outside-battery check at once, so the per-estimator breakdown needs a per-device baseline — and that baseline cannot be synthesised, by construction. |
| **the pinned figure** | `pin-check.sh` is pinned on an upstream sample. It is to be re-based on a real capture when one exists (steps in `BUILDING.md`). |
| **the 0.696 figure** | One unit's measurement, uninterpretable pending build provenance. |
| **health-test and operating-range evidence** | Not an estimator question at all; the estimator cannot produce it. |

## Needs a decision from the owner

| question | why it is a decision and not a task |
|---|---|
| **Upstream issue #253 is still open.** | `F01` was withdrawn and the PR closed, but closing the issue was never authorised. With "nothing upstream" standing, it stays open indefinitely unless the owner says otherwise. |
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
