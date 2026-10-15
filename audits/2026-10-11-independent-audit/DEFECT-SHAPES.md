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

**Instances:** `C08` (`compareresults.pl`, truncated and emptied references, a
dropped `Assessed min entropy` key), `regression-docs.sh` ×4,
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

## SHAPE-07 — a bounded-reach instrument reporting an unbounded verdict

The SP 800-90B estimator battery has a **finite lag reach**. The longest
explicit window in the whole battery is MultiMCW's **4095 samples** (§6.3.7);
Markov reaches lag 1, MultiMMC and LZ78Y reach depth 16, the Lag predictor
reaches 128. At the Infinite Noise's ~0.3 Mbit/s that longest window is
13.65 ms, a **frequency floor of 73.3 Hz** (`SECOND-SOURCE-SEARCH.md` Part 5,
Question 4).

The output is `min-entropy = H` bit/bit, with **no stated reach**. Nothing in
the JSON, the console output, or the standard's reporting requirements says
*"periodicity slower than 73.3 Hz was not examined."* So a source with a clean
figure and a 60 Hz mains component in it produces the same output as a source
with neither — and the mains fundamental (5000-6000 samples) is beyond 4095
while its own rectified second harmonic (2500-3000 samples) is inside. **The
battery can see the harmonic of a defect it cannot see.**

**The general form:** an instrument whose coverage is bounded along some
dimension — lag, frequency, alphabet size, time, input length — emits a verdict
phrased as a property of the thing measured rather than of the measurement. The
bound is real, documented in the algorithm, and absent from the result. Readers
then treat silence about the unexamined region as evidence about it.

**Why it is distinct from `SHAPE-06`:** `SHAPE-06` is a limit *reached and
mislabelled* — the arithmetic underflows and the tool says "test failed."
`SHAPE-07` is a limit *never reached and never mentioned* — nothing goes wrong,
no code path is exercised, and the figure is correct about everything it looked
at. `SHAPE-06` produces a wrong answer; `SHAPE-07` produces a right answer to a
narrower question than the reader thinks was asked. That makes it harder to
find, because there is no failure to notice.

**Where to look for it:** any aggregate presented without its support. Every
estimator with a fixed window, depth, or `D`/`k` cap; every "passed" that is
really "passed within the examined range"; `ea_restart`'s 1000×1000 matrix,
which examines exactly the restart structure it samples and nothing about
longer-period drift; and — the reason this matters past this repo — **any
consumer that stores a min-entropy figure as a scalar property of a source.**
A downstream system cannot recover a bound the upstream figure never carried.

**The fix shape:** emit the reach alongside the verdict. A field recording the
longest lag actually examined turns an unbounded claim into a bounded one and
costs nothing, since the battery already knows its own windows — the same
principle as *a test that asserts about a quantity must emit that quantity*,
applied to the test's domain instead of its subject. Where the standard's output
cannot be changed, the gap must be closed **outside** the battery: a long-lag
autocorrelation, a spectrum, or an estimator family the standard does not
include. No additional *source* closes it, because the bound belongs to the
instrument and a second source is measured with the same instrument
(`SECOND-SOURCE-SEARCH.md` Part 7).

**Instances:** the 73.3 Hz floor against mains (Part 5, Question 4); the
cross-check argument it invalidates (Part 7); `C21`'s `-1` sentinels, where a
*declined* estimator's non-participation is likewise not reported in the figure.
