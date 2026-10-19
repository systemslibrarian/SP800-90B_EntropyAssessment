# Upstream report inventory — what is publishable, and what our own changes obscure

State read: upstream `87c104d` (2026-05-26, "Merge pull request #248 from
joshuaehill/proportionRounding"); fork `master @ ea2b726`, **84 commits ahead**.
Every "upstream presence" row below was probed against `upstream/master` with
`git grep` / `git show`, not inferred. **Nothing sent. Inventory only.**

> **Decision, 2026-10-15 (Paul): no upstream report.** The fork is to be
> repaired and documented instead. Basis: a previous upstream PR went
> unacknowledged. This inventory is **kept, not sent** — it documents what is
> wrong with the tool being run, and its separation of upstream defects from
> fork-specific ones is what makes the repair work legible. The sequencing
> recommendation at the end of this document is therefore moot as a sending
> plan; it stands as a priority order for the repair record. `C22`'s bound,
> which item 4 of that recommendation was waiting on, is now measured in
> `ORCHESTRATOR-CHECKS.md` `OC-22`.

**The criterion that sorts this document:** a defect reproducible on **clean
upstream at a named commit** is a strong report. A defect reproducible only on
our modified tree is a weak report, because the reader must first accept 84
commits of our changes before the reproduction means anything.

---

## Where each finding lives

| Finding | Reference implementation or standard? | Present on `87c104d`? | Reproduction depends on fork code? |
|---|---|---|---|
| **`C07`** sites A & B — `assert(p_colPower >= LDBL_MIN)`, `assert(p_col >= 1/k)` | implementation | **PRESENT** (`cpp/shared/lrs_test.h`) | **no** |
| **`C03`** — failed battery still yields `errorLevel 0` and a figure | implementation | **PRESENT** (`iid_main.cpp:341` prints the failure, `:370` sets `errorLevel = 0`) | **no** |
| **`C23`** — upstream simulates the multinomial maximum where §3.1.4.3 prints a single binomial, **deliberately** (upstream #56) and **without recording it**; the printed formula is the defective side and rejects good sources (`OC-30`). Upstream defect is the **silence**, not the statistic. | **both** | **PRESENT** (`restart_main.cpp`) | **no** |
| **`C22`** — `ZALPHA` exact quantile vs printed 2.576 | **both** | **PRESENT** (`cpp/non_iid/collision_test.h`) | **no** |
| **`C05`** — `assert(k_effective <= k)` | implementation | **PRESENT** | no — **already filed as upstream #195, open since 2022** |
| **`C21`** — `fesetround(FE_TOWARDZERO)` left in effect; `periodicity()`/`covariance()` OOB reads | implementation | **PRESENT** | **no** (needs ASan) |
| **`C11`** — `delete results` on an array | implementation | **PRESENT** | **no** (needs ASan) |
| **`C20`** — races on `test_status[]` in the permutation region | implementation | **PRESENT** (`cpp/iid/permutation_tests.h`, 57 references) | **no** (needs TSan) |
| **`C06`** — `h_out` 7.1552 against a 7-bit ceiling | implementation | **PRESENT** (`conditioning_main.cpp`) | **no** |
| **`NEW-UP-01`** — the self-test never compares the final assessed figure | implementation | **PRESENT, and demonstrated below** | **no** |
| **`NEW-UP-02`** — `compareresults.pl` ignores extra keys | implementation | **PRESENT** | **no** |
| **`C16`** — `H_I` parsed permissively | implementation | **DIFFERENT MECHANISM** — upstream uses `atof`, not `strtod` | **yes — must be reframed** |
| **`C09`** — `ea_conditioning` enforces no intake rule | **standard-compliance gap** | intake rules are **absent upstream entirely** | **yes — framing changes** |
| **`C02`** — `hAssessed` carries `word_size × h'` where §3.1.5.2 gives `h'` per bit | **both** | **PRESENT** (`iid_main.cpp:303`) | no |
| **`C08`** — harness excuses a 0-byte reference / filename-matched allowance | implementation | partly — the allowance flag is **ours** | **yes, in part** |
| **`C18`** — LLP64 integer overflows | implementation | **PRESENT** | no, but needs a Windows build |
| **`REPRO-01`** — arm64 vs x86-64 divergence | implementation | **PRESENT** | **no** |
| **`REPAIR-BLOCK-01`** | our repair branch only | n/a | **yes — not an upstream finding at all** |

---

## NEW-UP-01 — upstream's self-test never compares the number an assessment is reported with. Demonstrated.

**This is the strongest new item, it is entirely upstream's, and it needs none of
our code.** Demonstrated using upstream's own `compareresults.pl` and upstream's
own `refdata/biased-random-bytes.res`, with no build:

`resultsHash` filters lines on `/(Estimate:|Assessed)/i` but its **only** value
regex requires the ` = ` form:

```perl
if ( $line =~ /(Estimate:|Assessed)/i ) {
   if($line =~ /^([^=]+) = ([-+]?[0-9]*\.?[0-9]+(...))$/ ) {
```

The final figure is printed with a **colon**: `Assessed min entropy: <v>`. So the
filter matches and the regex does not. Measured against upstream's own reference
file — **99 keys collected, and not one of them a final figure:**

| key | collected by upstream's parser |
|---|---|
| `Assessed min entropy` | **False** |
| `H_bitstring` | **False** |
| `H_bitstring Per Symbol` | **False** |
| `H_original` | **False** |

**The demonstration.** Corrupt *only* the final assessed figure in a copy of
upstream's reference and run upstream's comparator against the original:

```
< Assessed min entropy: 0.25774087100648113
> Assessed min entropy: 0.00000000000000001
upstream comparator exit=0        <-- NOT detected
Maximum delta: 0
```

**The entire reported figure can be replaced by a different number and upstream's
self-test passes, reporting a maximum delta of zero.** Only per-estimator lines
are compared, so any fault confined to the final combination — dropping the
`n × H_bitstring` term, failing to fold in `H_original`, an error in the `min()`
— leaves every compared value unchanged.

**`NEW-UP-02`**, same file: the extra-key loop prints `Found extra data item` and
never sets `$retstatus`, so a key the output produces and the reference lacks is
announced and ignored. Upstream emits `H_bitstring Per Symbol`
(`iid_main.cpp:303`) and **no** upstream reference file contains it (checked:
`biased-random-bytes`, `normal`, `truerand_8bit` all 0) — so even if the filter
were widened, that key would still be unenforced.

**Report-ready as it stands.** Inspection plus a sed one-liner on upstream
artefacts; no fork code, no build, no hardware.

---

## Report-ready as they stand

Reproducible on `87c104d` with no fork dependency:

1. **`NEW-UP-01` / `NEW-UP-02`** — demonstrated above. No build required.
2. **`C07` site B** — the canary input is generated by a **self-contained 6-line
   Python snippet from a fixed seed** (digest `327773dd47cc4807…`), so the
   reproduction carries no fork code. On upstream, asserts live: `SIGABRT` at
   `lrs_test.h:683`. Under `-DNDEBUG`: the fabricated figure. **Strongest
   substantive finding** — and note the fix is already written on our repair
   branch (log-domain, `a3dde6f`), so the report can offer a patch.
3. **`C07` site A** — the ±1-sample perturbation fixtures are generated, not
   fork artefacts: 5 of 10 exactly-balanced alphabets abort while `k = 32` and
   `64` pass because `1/k` is an exact binary fraction.
4. **`C03`** — upstream's own source shows it: the failure is printed at
   `iid_main.cpp:341` and `errorLevel = 0` is set at `:370`. **Chains with
   `C07`**, and the chain is the compelling form: an underflow makes the LRS test
   report failure, `C03` discards it, a figure is published.
5. **`C23`** — `oracles/restart_cutoff_exact.py` is standalone and reproduces the
   standard's own published cutoffs (570, 312, 173, 99, 58, 36, 23, 19, 15),
   against the tool's 571–573 and **27**. The oracle checks against the
   *document*, so it does not inherit our tree.
6. **`C06`** — `h_out` 7.1552 against a 7-bit information ceiling. A metamorphic
   violation: needs no reference value, only the arithmetic.
7. **`C11`**, **`C21`**, **`C20`** — memory-safety and concurrency, reproducible
   under ASan/TSan on upstream. **Weaker as reports** until direction is
   established; `C20` and `C21` are still UNKNOWN-direction in our own triage and
   should not be sent claiming a figure impact we have not shown.
8. **`REPRO-01`** — the arm64/x86-64 `long double` divergence, with the exponent
   arithmetic (`W > 1022` vs `W > 16382`). **Honest caveat required**: the x86-64
   side is an exponent-range argument, **not measured on that platform**.

### Standard's text, for the erratum query rather than a code report

- **`C22`** — the prose/footnote discrepancy on the 0.995 quantile (2.576 vs the
  exact value). **The erratum query document is already drafted.**
- **`C23`** — the standard's claim that the simulated cutoff sits at or above the
  exact binomial cutoff, which our oracle contradicts at every tabulated `H_I`.
- **`C02`** — §3.1.5.2 gives `h'` per bit while the machine-readable field
  carries `word_size × h'`. Arguably a documentation defect in the tool rather
  than the standard; our own prior decision (F23) left it as-is.

---

## Needs reframing before it can be sent

**`C16` — do not send as filed.** We filed it against `strtod`; **upstream uses
`atof`** (`restart_main.cpp:293`: `H_I = atof(argv[0])`). The `strtod` call is
*our* change, introduced to add validation (N-04). The underlying permissiveness
is nonetheless **worse** upstream — `atof` accepts hex floats and leading
whitespace exactly as `strtod` does **and reports no error at all**, silently
yielding `0.0` on garbage, and `H_I` sets the restart validation threshold
`H_I/2`. So the finding is real upstream and must be re-written against `atof`,
with our `strtod` version presented as the *proposed fix* rather than as the bug.

**`C09` — framing changes entirely.** We filed it as "`ea_conditioning` applies
no 1,000,000-sample rule, no single-symbol and no width check" — but **the intake
rules are ours**: `EA_ALLOW_SHORT_DATASET` and `nonCompliantShortDataset` are
**absent from upstream**. Upstream enforces no intake rule in *any* tool, so the
upstream finding is the broader "§3.1.1's minimum is not enforced anywhere",
which is a different and larger claim than the one we verified.

---

## What our own changes obscure — reproductions that must be rewritten against clean upstream

| Our change | What it breaks for an upstream reader |
|---|---|
| **`compareresults.pl` extended** (group-2 collection) **and fixed today** (`OC-21`, extra keys now fail) | Any `NEW-UP-01`/`NEW-UP-02` reproduction run on **our** tree shows different behaviour. **Use `git show upstream/master:cpp/selftest/compareresults.pl`** — which is what the demonstration above did. |
| **`refdata/*.res` now carry `DERIVED` lines** on 6 files (`OC-21`) | Our references are no longer byte-equal to upstream's. Any reproduction touching reference data must use `git show upstream/master:cpp/selftest/refdata/<f>.res`. |
| **The 1,000,000-sample intake rule and `EA_ALLOW_SHORT_DATASET`** | Every short-input reproduction we have depends on fork-only machinery. Upstream refuses nothing, so those repros must be rebuilt as "upstream accepts a 125,000-byte file with `errorLevel 0`" — which is a *simpler* repro, but a different one. |
| **`nonCompliantShortDataset`** and the other `nonCompliant*` JSON fields | Absent upstream; any repro asserting on their absence is circular on our tree. |
| **15 `regression-*.sh` scripts, `run-all-checks.sh`, `verify-fixture-inventory.sh`, `pin-check.sh`** | All ours. **No upstream reproduction may invoke them.** Each must be reduced to the underlying tool invocation. |
| **`tools/build-provenance-canary.sh`** | Ours. The `C07` NDEBUG report must state the build flags directly rather than cite the canary. |
| **`--allow-known-platform-deltas`** | Ours. The `C08` filename-allowance half **is not an upstream defect**; only the 0-byte-reference half is. |
| **`a3dde6f` (repair branch)** | Our fix for `C07`/`C03`. Useful as an *offered patch*; must not be present in the tree used to reproduce the bug. |

---

## Recommendation on sequencing

1. **Send `NEW-UP-01` first.** It is demonstrated, needs no build, is entirely
   upstream's, and it is the finding that explains why the others survived: the
   self-test cannot see a wrong final figure. It also makes every subsequent
   report more credible, because it answers "why didn't your tests catch this?"
2. **Then `C07` + `C03` as a chain, with the patch offered.** The chain is the
   compelling artefact (a published 0.9954 from an underflow), the reproduction
   is seed-generated, and `a3dde6f` is a working fix whose NDEBUG-independence we
   have measured.
3. **Then `C23`, with the oracle**, and the erratum query alongside, since the
   code and text defects are the same finding seen twice.
4. **Hold `C22` until its bound is measured.** "Raises every prediction estimate"
   with no magnitude is the weakest possible form of a real finding, and
   measuring it is free.
5. **Hold `C20`, `C21`, `C18`** until direction is settled. Sending an
   unknown-direction memory-safety report invites "benign" and spends credibility
   we need for items 1–3.
6. **Do not send `C09` or `C16` as filed**, per the reframing section.

### Standing caveat for anything sent

There is **no independent reviewer** on this project. Every finding above was
established by the same party proposing it, and several corrections in this audit
were to my own earlier conclusions — `C07`'s direction, the 73.3 Hz blind spot,
the exact-string criterion in `OC-21`, and `REPAIR-BLOCK-01`'s premise. Any
upstream report should say so plainly and supply the reproduction rather than the
conclusion, so a reader can check it without trusting us.
