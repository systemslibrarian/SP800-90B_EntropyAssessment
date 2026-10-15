# Defect shapes

Patterns this audit met more than once, stated generally so the next pass
recognises them in new code rather than rediscovering them per site. Each is
anchored to the instances that produced it.

---

## SHAPE-01 — an opt-in non-compliance flag cannot detect accidental non-compliance

`nonCompliantShortDataset` is **absent** from a 100-byte `ea_conditioning`
assessment (`OC-9`). Not false — absent. The flag exists to mark a
non-compliant assessment, but it is set by the `EA_ALLOW_SHORT_DATASET` escape
hatch, and the escape is never needed when the rule was never applied. So the
flag reports *"someone deliberately asked for a non-compliant run"*, not
*"this run is non-compliant"*.

**The general form:** a marker attached to the *mechanism that waives a rule*
can only ever detect deliberate waiver. It is structurally blind to a code path
where the rule is simply missing — which is the case that matters, because
deliberate waiver is already visible to whoever typed the environment variable.

**Where to look for it:** any flag, field or log line whose value is set inside
the branch that grants an exception. Ask what sets it on the path where no
exception was requested because no check existed.

**The fix shape:** compute compliance from the data, not from the waiver. A
field asserting *"this assessment used N samples and the minimum is M"* is
always populated and cannot be silently absent. Related rule: *a test that
asserts about a quantity must emit that quantity.*

**Instances:** `C09` (`nonCompliantShortDataset` absent, `bitsPerSymbol`
absent, on a 100-byte assessment with `errorLevel 0`).

---

## SHAPE-02 — a classification that rests on a build flag the project does not control

`C07` was filed CONSERVATIVE and fail-closed because `NDEBUG` is not defined in
`cpp/Makefile`. Built with `-DNDEBUG`, the same commit on the same data
publishes `hAssessed 0.995373734104443` with `"IID": true` instead of aborting
(`OC-10`). The classification was true of a build, not of the code.

**The general form:** whenever a safety property is enforced by `assert`, by a
sanitizer, or by any construct a compiler flag can remove, the finding has **two
directions** — one per build — and the project ships whichever build its
downstream produces. An aggregate over mixed evidence reports its floor, so the
weaker build's direction is the one to carry.

**Where to look for it:** every `assert()` in a production path; every finding
whose evidence is a sanitizer report rather than observed behaviour (`C11` was
called "an abort" when it is silent undefined behaviour outside ASan); every
"cannot happen" comment.

**The fix shape:** the fork already has it and used it four times — `F11`,
`F12`, `F15`, `F16` replaced an abort with a *declined estimator* returning the
`-1` sentinel, kept out of the minimum by an explicit guard. A documented,
expected limit is a decline-and-report case, not an assertion about a
programming error. Interim: `#if defined(NDEBUG)` → `#error`, which converts an
unknown into a build failure for one line of code.

**Instances:** `C07` sites A and B, `C09` (`most_common.h:14`), `C05`,
`C11`. Precedent in the fork's own records: `N-03` (2026-09-30) was already
filed as *"D in the shipped build; B under `-DNDEBUG`"*.

---

## SHAPE-03 — an empty accumulator reads as success

`compareresults.pl` iterates the **reference** hash, so a 0-byte reference file
produces zero comparisons, an untouched `$retstatus`, and `selftest: PASS`
(`OC-4`). `regression-docs.sh` drove four checks from `grep` extractions that
could return the empty set, so breaking the pattern made the script report that
*every* commit SHA resolves (`DEAD-GUARD-SWEEP.md`, class 3).

**The general form:** a check implemented as "iterate the expected set,
accumulate failures, pass if the accumulator is empty" cannot distinguish *no
failures* from *nothing examined*. The failure accumulator is empty in both
cases.

**Where to look for it:** any loop whose iteration count comes from an
extraction, a glob, a file read or a directory listing, where the loop body
holds the only code that can record failure.

**The fix shape:** assert the size of the examined set before trusting the
verdict over it. `verify-fixture-inventory.sh` already does this with an exact
`11`; `regression-docs.sh` now does it with floors, because documentation grows
and a hand-maintained exact count is itself `SHAPE-05`.

### The second direction, found 2026-10-15 (`OC-20`)

The same loop is blind on the **other** side, and `compareresults.pl` shows both
in one file. Missing keys are enforced; **extra keys are not**:

```perl
foreach my $newKey (keys %$newResults) {
   print "$ARGV[0]: Found extra data item: $newKey -> $newResults->{$newKey}\n";
}
```

No `$retstatus`. So a key present in new output and absent from the reference is
**announced and ignored** — the evidence is printed and the verdict is PASS.
Measured consequence: this fork extended the parser to collect the final combined
figures, naming *"dropping the n x H_bitstring term"* as the fault it was closing,
but the eleven references were never regenerated — so `H_bitstring Per Symbol`
(exactly `n × H_bitstring`, verified bit-identical) is emitted on 6 files,
present in 0 references, and compared on **none**. The one key with no reference
is the term the fix was written for.

**Fixed 2026-10-15 (`OC-21`)**, and the two halves needed different repairs: the
asymmetry was fixed in code (an extra key now fails, shown failing both ways),
while the missing value was **derived** from data already in the references
(`n × H_bitstring`, with both `n` and `H_bitstring` present in reference files
last written by upstream) rather than regenerated from the current tools —
because a reference produced by its subject cannot detect its subject changing.

**The general form, now stated for both directions:** a comparison driven by one
side's key set cannot see what is missing from that side. Iterating the reference
misses additions; iterating the new output would miss deletions. **A comparison
that must be total has to assert the two key sets are equal**, not iterate one of
them — and expected asymmetries have to be enumerated rather than left to a
print statement.

**Instances:** `C08` (`compareresults.pl`, truncated and emptied references, a
dropped `Assessed min entropy` key), `OC-20` (the same file's unenforced extra
keys, and eleven stale references), `regression-docs.sh` ×4,
`check-notices.sh:124` (**withdrawn** — it already had the floor).

---

## SHAPE-04 — a computed threshold compared against its own boundary case

`assert(p_col >= 1.0L / k)` holds mathematically with **equality** exactly when
the alphabet is perfectly uniform. So the assert compares two
differently-computed expressions for the same number, and the left side can land
one ULP low: 5 of 10 exactly-balanced alphabets abort, while `k = 32` and `64`
pass because `1/k` is an exact binary fraction (`OC-5`). The best possible
source is the one that trips it.

**The general form:** a bound that is tight — attained, not merely approached —
at some reachable input is not a safety check at that input; it is a
floating-point coin toss. The extreme case is where the check is weakest, which
is the opposite of what a check is for.

**Where to look for it:** any inequality justified by a mathematical bound whose
equality case is reachable. `p_col ≥ 1/k` (uniform), `p_colPower ≤ 1-ε`
(degenerate W), `X̄' ≥ 2` in the collision estimator, `p_u ≤ 1`.

**The fix shape:** compare with an explicit tolerance, or restructure so the
boundary case is handled by construction rather than by assertion. And
*demonstrate every computed threshold at its extremes* — the ±1-sample
perturbation test that showed site A needs exact balance is the pattern.

**Instances:** `C07` site A. Adjacent: the `-0` family (`C15`), which is the
same equality case surfacing in output rather than in a check.

---

## SHAPE-05 — a hand-maintained count of a growing thing

`audits/README.md` claims 585 tracked files and 118 subdirectories against an
actual **739** and **126** (`OC-3`), and nothing checks it. `BUILDING.md` says
"Three predictor values" where its own table says eight.

**The general form:** a number written in prose about a set that changes is
wrong from the first change onward, and its wrongness is invisible because
nothing recomputes it.

**The fix shape:** compute it, or assert a floor rather than an exact value when
the set legitimately grows. Exact counts are right only for a set frozen by
design — `verify-fixture-inventory.sh`'s `11` is correct because the corpus is
fixed.

**Instances:** `audits/README.md` counts, `BUILDING.md` predictor count,
`run-all-checks.sh`'s `EXPECTED_REGRESSION_SCRIPTS`/`EXPECTED_TOTAL_CHECKS`
(repair branch).

---

## SHAPE-06 — an arithmetic limit reported as a statistical verdict

Under `NDEBUG`, `C07` site B's underflow makes `len_LRS_test` **return false** —
the LRS test reports failure having detected nothing about the data
(`OC-10`). On the repair branch the same condition prints
`** Failed length of longest repeated substring test`
(`REPAIR-BLOCK-01`). In both cases a representability limit of the build
platform is presented as a property of the operator's entropy source.

**The general form:** when a computation cannot be represented, the honest
output is "not computed". Returning the *failing* value of the surrounding
predicate is conservative in direction and wrong in meaning, and it sends the
reader to debug the wrong system — their hardware instead of the arithmetic.

**Why it is worse than an abort:** an abort is obviously a tool failure. "Failed
length of longest repeated substring test" is a credible, actionable verdict
about a TRNG.

**And it chains.** A statistical failure that a *second* defect discards
(`C03`) becomes a passing assessment. `OC-10` measures that chain's ceiling:
`hAssessed 0.9954 bit/bit`, above the project's threshold, from an underflow.

**The fix shape:** a distinct "declined — not representable on this platform"
state, separate from pass and fail, excluded from the minimum. The `-1`
sentinel and the `nonCompliant*` fields are the existing precedents.

**Instances:** `C07` site B under `NDEBUG`; the repair branch's handling of the
same site; `C21`'s `-1` sentinels folded into `h'` giving `h_out = -256` is the
same shape with the sentinel leaking into a figure instead of a verdict.

---

## SHAPE-07 — an aggregate that discards the evidence of its own components

> **This shape was first written as "a bounded-reach instrument reporting an
> unbounded verdict" and that framing was REFUTED BY MEASUREMENT.** The reach
> bound is real but it is not the mechanism. `SECOND-SOURCE-SEARCH.md` Parts 8-9
> have the measurement; the corrected shape is below and the superseded text
> follows it for the record.

**Measured:** a binary stream carrying a **+40 σ** autocorrelation at lag 5000
produced `H_original = 0.856713`, inside the clean-control range
`[0.843936, 0.865774]` — statistically indistinguishable from a fair coin. The
one estimator that detected it, LRS at −0.0223, reads **0.1164 bit above the
binding minimum**, so its detection could not reach the verdict.

**The mechanism is the aggregation, not any component.** The SP 800-90B non-IID
verdict is `min` over ten estimators. On near-uniform data Compression binds
(0.8546 ± 0.0092 on a fair coin) and the other nine sit **0.060 to 0.143 bit
above it**. Each one's *headroom* is a detection budget it wastes: a defect must
move it by more than that headroom before the verdict changes at all. Five of the
ten never came within a factor of five of their own headroom on any defect
tested.

**The general form:** an aggregate reported as a single number, computed as an
extremum over components, **discards every component's evidence except the
extremum's**. A component that reliably sits far from the extremum can detect
anything and change nothing. The aggregate's resolution is the *most extreme*
component's noise, not the *most sensitive* component's signal.

**Why it is worse than a reach bound.** A reach bound is fixed by adding reach.
This is not fixed by adding components: a new, exquisitely sensitive estimator
that is not the minimum contributes exactly nothing. It is also not fixed by
buying a better source, because it is a property of the measurement, not the
measured.

**Where to look for it:** any `min`, `max`, or worst-case over a panel reported
without the panel. Any score that is "the weakest link" where the links' values
are computed but not emitted. Any consumer storing such an aggregate as a scalar.

**The fix shape:** **emit the components, not just the aggregate.** The breakdown
contains LRS's −0.0223; the minimum does not. Here it is free — the tools already
print it under `-v` — which makes it the cheapest mitigation in the audit
(`XR-06`). Where the aggregate cannot change, the gap must be closed by an
instrument *outside* the panel: `tools/outside-battery-check` finds at 40.21 σ
what the whole battery reports as clean. Related rule: *a test that asserts about
a quantity must emit that quantity* — here, about **each** quantity it computed.

**Instances:** the 40 σ stream invisible in `H_original` (Part 8); the headroom
table (Part 9); `C21`'s `-1` sentinels, where a declined estimator's
non-participation is likewise absent from the figure.

### Superseded framing, kept for the record

The original claim was that the battery's longest explicit window — MultiMCW's
4095 samples (`multi_mcw_test.h:9`), 13.65 ms at ~0.3 Mbit/s, a **73.3 Hz
floor** — put mains at 50/60 Hz (lags 6000/5000) in a blind spot. **The reach
figures are correct and the conclusion was wrong**, because a slow bias drift is
detected by *short* windows, not long ones: W = 63 on a period-5000 oscillation
sees a nearly-constant local bias and predicts it. Measured, MultiMCW fell 0.163
on exactly that stream. The error was assuming a window must exceed the period.
**Keep the reach table, discard the floor.**
