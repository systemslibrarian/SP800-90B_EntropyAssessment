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
