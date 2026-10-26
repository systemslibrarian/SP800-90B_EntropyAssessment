# What counts as an instrument

Written once, so a sweep does not have to re-derive it. Every
"count examined alongside count found" figure in this repository is meaningless
without this, and two careful readers once disagreed by seventeen because it
was not written down (`OC-65`).

## The rule — behaviour, not extension

> **An instrument is a RUNNABLE artefact that produces a number or a verdict
> which a document or a claim then cites.**

**Enumerate by what a thing DOES, never by what it is named.** The one sweep in
this project that needed no denominator correction was the one enumerated by
behaviour (`OC-66`'s aggregates); every sweep enumerated by extension was
understated (`OC-67`). `audits/enum-instruments.sh` implements it:

| limb | test | mechanical? |
|---|---|---|
| **a** | the executable bit is set, or the first two bytes are `#!` | yes |
| **b** | a CI workflow definition — emits verdicts, never run locally | yes |
| **c** | something in the tree **invokes** it: sourced, or compiled then run | **no — a reviewed list of 10, each with its reason** |
| — | **excluded:** compiled outputs (`Mach-O`/`ELF`), pure data, untracked files | yes |

**THE RULE COUNTS THE GIT INDEX, AND THAT IS LOAD-BEARING.** `git ls-files`
lists tracked **and staged** paths, so a new instrument begins to count the
moment it is staged — not when it is written, and not after the commit. That
is what lets the stated count and the tree be consistent *at commit time*:
stage everything, re-run the enumerator, write the number it prints. A new
instrument that is merely present on disk is deliberately **not** counted,
because an untracked file is not part of the record.

`sh audits/enum-instruments.sh . ` prints the live count. **THE ENUMERATOR IS
THE AUTHORITY AND THIS FILE IS NOT**: every figure below names the commit and
date it was measured at, and `regression-docs.sh` fails if the stated figure and
the enumerator's disagree. **Measured `live: 74 (64 mechanical + 10 reviewed)`
at `11207ca`, 2026-10-25.** It read 73 (63 + 10) at `ae023b0`, 2026-10-22 and
70 (60 + 10) at `32920f49`, 2026-10-21. The fourth added since `32920f49` is
`tools/measure-divergence.sh`, which enforces the fork-divergence figures
(`OC-91`); the first three were `cpp/selftest/regression-deadguard.sh`,
`cpp/selftest/regression-workflows.sh` and
`audits/2026-10-11-independent-audit/oracles/compression_ceiling_exact.py` —
**listed by diffing the enumerator's own `--list` output across the two
commits, not by recollection**: the first draft of this sentence named one of
them wrongly. Limbs (a) and (b) find
`cpp/selftest/selftest`, `generate-refdata`, `compareresults.pl` and a `.mjs`
reproducer **without naming them**, which is the whole point: those four were
invisible to every extension-matched sweep this project ran.

### Why limb (c) is a reviewed list and not a pattern

Two mechanisations were tried and both failed, recorded so neither is tried
again:

- **`git grep` for the basename near an invocation verb** took the live count
  from 61 to **112** — admitting every prose mention of a filename in a `.md`
  file — while *still* missing the C++ reproducers, whose only build line lives
  in a comment inside themselves. Wrong by 51.
- **`file -b`** cannot stand in for it either: asked about these it answers
  `c program text, ASCII text` for **both** a C++ reproducer **and** a POSIX
  shell library, so a "compilable source" test would admit
  `buildstate-lib.sh`.

So limb (c) is ten named members with the behaviour that qualifies each — two
sourced libraries, which produce no verdict alone and every verdict through
their callers, and eight compilable sources whose built form produces a cited
figure. **A judgement that cannot be mechanised without false positives is
better stated than approximated.**

### A behaviour rule is present-tense, so it is wrong for frozen evidence

The same enumerator gives **frozen: 32**, against 79 by extension. That gap is
not an error in either count — it is the rule not applying. Frozen artefacts are
**dated evidence**: nothing invokes them now, and nothing should. What qualified
them was being invoked **then**. So:

| set | rule that applies | count |
|---|---|---:|
| **LIVE** | behaviour, present tense: is it run, sourced, compiled, or a workflow **now** | **82** at `b53ff5d`, 2026-10-26 |
| **FROZEN** | historical: was it an instrument when the evidence was dated | **79**, and fixed: dated evidence does not grow |

Counting frozen by the live rule would silently retire 47 artefacts that were
instruments when they produced the evidence the record still cites.

Three consequences the rule settles, each of which was got wrong once:

1. **Runnable, not source-shaped.** Membership is decided by `file -b` and the
   executable bit, **not** by extension. `cpp/selftest/selftest`,
   `cpp/selftest/generate-refdata` (both Bourne-Again shell) and
   `cpp/selftest/compareresults.pl` (Perl) are instruments and were missed by an
   extension-matched glob — and `selftest` is the one the entire suite calls.
2. **Sources, not their build artefacts.** `tools/outside-battery-check` and
   `cpp/selftest/restart-report-label-test` are compiled Mach-O binaries built
   from counted `.cpp` sources. They are **outputs**, not separate instruments;
   counting them double-counts.
3. **Producers, not inputs.** Manifests and reference data —
   `known-platform-deltas.txt`, `regression-script-inventory.txt`,
   `outside-battery-corpus.txt`, `fixture-manifest.txt`, `refdata/*.res` — are
   **cited by** instruments and do not produce anything themselves. They are
   excluded, and they have their own integrity guards
   (`verify-fixture-inventory.sh`, `regression-selftest-inventory.sh`).

**CI workflow definitions ARE instruments.** `.github/workflows/*.yml` contain
gates that emit verdicts the record cites, so they are in. This was the second
thing an extension-matched glob missed.

## The two sets, and why they are counted apart

| set | count | what it is |
|---|---:|---|
| **LIVE** | **82** at `b53ff5d`, 2026-10-26 | `cpp/selftest`, `tools`, `.github`, `audits/2026-10-11-independent-audit`, `audits/2026-10-09-independent-audit`, `repairs/*/rerun.sh` — anything a sweep must cover today |
| **FROZEN** | **79**, fixed | `audits/2026-09-30`, `audits/2026-10-01-re-audit`, `audits/2026-10-02-doc-review` — **dated evidence**, N/A to a live sweep. Re-running them would not re-date them, and changing them would destroy the evidence. |

Reproduce both counts with `sh audits/enum-instruments.sh .`; add `--list` for
the members and `--why` for limb (c)'s reasons.

## Eight families

oracles · generators · reproducers · detectors · regression scripts ·
CI workflows · rerun scripts · libraries (`buildstate-lib.sh`,
`mutation-lib.sh`, which produce no verdict alone but every verdict through
their callers, so they are in).

## How the disagreement was found and settled

**This section is dated: the figures in it are those of 2026-10-21, at
`32920f49`, and are not the current count.** An outside session counted
**70 live / 79 frozen**. I had reported **53**, and
mine was wrong twice over: it omitted `.github/workflows`, the generators, the
2026-10-09 audit and `repairs/`, **and** it inflated the remainder with four
`__pycache__` files. The frozen counts matched exactly at 79 on the first
attempt, which is what showed the disagreement was confined to the live set and
was about the rule rather than the tree. Applying the rule above gave **70**,
their number exactly, with the one apparent residual explained by consequence
(2). The live set has since grown to 74; the rule is unchanged.

**The cost, stated plainly:** `OC-64`'s shape sweep reported "33 shell
instruments swept" against an unstated denominator. 33 of **70**, the count at the time, is under half,
and the three extensionless shell instruments were never swept. They have since
been swept and the conclusion held — but it held by luck of the denominator,
not by the sweep's design.
