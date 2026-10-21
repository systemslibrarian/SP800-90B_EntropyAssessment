# What counts as an instrument

Written once, so a sweep does not have to re-derive it. Every
"count examined alongside count found" figure in this repository is meaningless
without this, and two careful readers once disagreed by seventeen because it
was not written down (`OC-65`).

## The rule

> **An instrument is a RUNNABLE artefact that produces a number or a verdict
> which a document or a claim then cites.**

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
| **LIVE** | **70** | `cpp/selftest`, `tools`, `.github`, `audits/2026-10-11-independent-audit`, `audits/2026-10-09-independent-audit`, `repairs/*/rerun.sh` — anything a sweep must cover today |
| **FROZEN** | **79** | `audits/2026-09-30`, `audits/2026-10-01-re-audit`, `audits/2026-10-02-doc-review` — **dated evidence**, N/A to a live sweep. Re-running them would not re-date them, and changing them would destroy the evidence. |

Reproduce the live count with:

```sh
find cpp/selftest tools .github audits/2026-10-11-independent-audit \
     audits/2026-10-09-independent-audit repairs -type f \
  \( -name "*.sh" -o -name "*.py" -o -name "*.yml" -o -name "*.c" -o -name "*.cpp" \) \
  | grep -vE '__pycache__|\.pyc$' | wc -l          # 66 extension-matched
# plus the four runnable artefacts an extension glob misses:
#   cpp/selftest/selftest, cpp/selftest/generate-refdata,
#   cpp/selftest/compareresults.pl,
#   audits/2026-10-09-independent-audit/reproducers/truepad-unattested-tools.mjs
# = 70.  The two compiled Mach-O files are build artefacts, excluded per (2).
```

## Eight families

oracles · generators · reproducers · detectors · regression scripts ·
CI workflows · rerun scripts · libraries (`buildstate-lib.sh`,
`mutation-lib.sh`, which produce no verdict alone but every verdict through
their callers, so they are in).

## How the disagreement was found and settled

An outside session counted **70 live / 79 frozen**. I had reported **53**, and
mine was wrong twice over: it omitted `.github/workflows`, the generators, the
2026-10-09 audit and `repairs/`, **and** it inflated the remainder with four
`__pycache__` files. The frozen counts matched exactly at 79 on the first
attempt, which is what showed the disagreement was confined to the live set and
was about the rule rather than the tree. Applying the rule above gives **70**,
their number exactly, with the one apparent residual explained by consequence
(2).

**The cost, stated plainly:** `OC-64`'s shape sweep reported "33 shell
instruments swept" against an unstated denominator. 33 of **70** is under half,
and the three extensionless shell instruments were never swept. They have since
been swept and the conclusion held — but it held by luck of the denominator,
not by the sweep's design.
