# Repair strategy — the nine permissive defects, sorted by treatment

State read: `master @ ea2b726` (== `origin/master`); repair branch
`repair/2026-10-09-verified-defects @ 2d4b135`; upstream `87c104d` (2026-05-26,
fork 84 ahead). Binaries built from each tree with that tree's `cpp/Makefile`
flags; the `-DNDEBUG` variants built by overriding `CXXFLAGS` with the same flags
plus `-DNDEBUG`. **No repairs made. Classification and recommendation only.**

---

## The inference that makes this urgent, stated precisely

A permissive defect means **reported H ≥ true H**. So a measured figure bounds
the truth **from above**. Chor–Goldreich needs a **floor** above ½ bit per
source. **A ceiling cannot establish a floor**, so the inference the whole
measurement exists to support does not survive an unrepaired permissive defect.

**But the conclusion is not "all nine must be repaired."** The floor survives
wherever the inflation is *bounded*:

> **floor = reported figure − Σ (bounds of the permissive defects in play)**

That is usable with **no patch at all**, and it keeps the reference tool's own
number comparable. It fails only where **no bound exists** — and the decisive
distinction is not severity but whether a defect *inflates a real figure* or
*fabricates one*. An inflation can be subtracted. A fabrication cannot, because
the test detected nothing and there is no quantity for the bound to apply to.

**One correction to the framing, and it matters for two entries below.** A single
measured overestimate is **not** a bound. `C03`'s **+42.59 %** and `C01`'s
**+3.69e-4** are both measurements, but only `C01`'s is a bound: `C01` is a
last-digit comparison defect whose error is intrinsically small, while `C03` is a
**track-selection** error — it awards the IID figure where the non-IID track was
mandated, and the gap between those two tracks is a property of the data, not of
the defect. **`C03` is therefore unboundable**, and its 42.59 % is one instance,
not a ceiling.

---

## Classification

| Defect | Treatment | Bound / configuration | Closed on repair branch? |
|---|---|---|---|
| **`C03`** IID verdict discards a failed test | **3 → NEEDS CODE** (unboundable) | none — track-selection gap is data-dependent | **YES — verified** |
| **`C07`** underflow → fabricated figure | **1 + 4** | asserts live ⇒ fail-closed; under `NDEBUG` **no bound exists** | **YES — verified, and build-independent** |
| **`C23`** restart cutoff above the exact binomial | **2 → BOUNDABLE** | exact oracle exists; slack measured | **no — untouched** |
| **`C22`** `ZALPHA` raises every prediction estimate | **2, bound NOT YET MEASURED** | boundable in principle; "tiny" is a claim | **no — untouched** |
| **`C01`** two-sided comparison error | **2 → BOUNDABLE** | **±3.69e-4 bit**, measured | no |
| **`C02`** `hAssessed` carries `word_size × h'` | **1 → CONFIGURATION/READING** | exact factor `word_size` ∈ 1..8 | no (F23 decision stands) |
| **`C06`** `h_out` 7.1552 vs a 7-bit ceiling | **3**, but **OFF-PATH** | — | no |
| **`C09`** `ea_conditioning` intake unenforced | **1 + 3**, but **OFF-PATH** | asserts live ⇒ abort instead of `h' = -0` | no |
| **`C08`** the harness excuses errors | **3 — PARTLY CLOSED TODAY** | — | partly, on master (`OC-21`) |

Unknown-direction, leaning permissive: `C14`, `C16`, `C20`, `C21`, `C18` —
**unclassifiable until direction is settled**, which is why unknown raises
priority rather than lowering it. `REPRO-01` (arch-dependent) is **Class 1**:
pinned architecture plus recorded provenance neutralises it.

---

## Class 1 — avoidable by configuration. The cheapest repair; changes no code.

| Defect | Configuration that neutralises it | What it becomes |
|---|---|---|
| **`C07`** | build **without `-DNDEBUG`** | fail-closed `SIGABRT`, no JSON — conservative |
| **`C09`** | build **without `-DNDEBUG`** | assert abort instead of a heap-overflow read and `h' = -0` with exit 0 |
| **`C02`** | read `h'`, not `hAssessed`, for a per-bit figure | exact; the factor is `word_size` |
| **`REPRO-01`** | pin the architecture **and record it** | removes the silent arm64/x86-64 divergence |

**Can TruePad enforce it? Yes, and the mechanism already exists for exactly
this.** `tools/build-provenance-canary.sh` classifies a binary `ASSERTS-LIVE` /
`NDEBUG` / `INDETERMINATE` on a digest-verified input, exits 0 / 3 / 2, and
treats `INDETERMINATE` as refusal rather than pass. `XR-04` already requires
build provenance for any figure. So the enforcement is: **refuse any figure
whose binary does not classify `ASSERTS-LIVE`.**

**Two limits on configuration as a strategy, both already recorded.** First,
`cpp/Makefile:31` *assigns* `CXXFLAGS`, so a packager who overrides it loses
`-ffloat-store` as well — configuration is enforceable on *our* builds, not on a
downstream rebuild. Second, the canary establishes **one bit** (NDEBUG state); it
does not establish the commit, the compiler, or that the binary is unmodified.
Building from a pinned commit with known flags is strictly stronger and is what
should actually be done.

---

## Class 2 — boundable. The figure stays usable with no patch.

**`C01` — bounded, measured: ±3.69e-4 bit.** Two-sided, and the sign is chosen
by the data, so a hostile submitter picks it. Against a 0.5 threshold this is
**four orders of magnitude** below any decision and can simply be subtracted.

**`C23` — boundable, and the oracle already exists.**
`oracles/restart_cutoff_exact.py` computes the exact §3.1.4.3 binomial cutoff
independently of the tool and reproduces 570, 312, 173, 99, 58, 36, 23, 19, 15.
The tool's simulated cutoff sits **above** it (H_I=1: 571–573 vs 570; H_I=7:
**27** vs 23), so it accepts restart matrices the standard rejects.

**What the bound applies to must be stated carefully, because it is not the
per-bit figure.** `C23` governs the **restart sanity check** — whether the
restart dataset is accepted — not the min-entropy estimate. So the correct
treatment is not "subtract 0.341 bit from H"; it is **recompute the restart
accept/reject decision against the exact oracle** and treat the tool's verdict
as advisory. That is strictly better than a subtraction because the oracle gives
the *right* answer rather than a conservative envelope.

**`C22` — boundable in principle; the bound is NOT measured.** `ZALPHA` is the
exact 0.995 quantile where the spec text prints 2.576, and by the finder's own
description it "raises every prediction estimate" — i.e. **permissive on the
figure itself**, which `C23` is not. **"Magnitudes tiny" is a claim, not a
measurement**, and it is the only unmeasured item standing between the current
figure and a defensible floor. **This is the highest-value open measurement in
this document**: quantifying it either moves `C22` into Class 2 with a usable
bound, or proves it needs code. It needs no hardware and no patch.

---

## Class 3 — needs code. And the validation problem is the hard part.

**`C03`** (unboundable; code written on the repair branch), **`C22`** if its
bound turns out to matter, **`C08`** (partly closed today), **`C06`**/**`C09`**
(off-path), and every unknown-direction cluster once its direction is settled.

### How a code fix could be validated, given that the corpus cannot vouch for it

This is the real obstacle, and the closing caveat of `OC-21` is binding: the
reference corpus is **more complete, not more trustworthy**; ten of eleven key
families are upstream-captured with no independent derivation; and regenerating
from these tools is forbidden because **a reference produced by its subject
cannot detect its subject changing**. So **"the selftest still passes" validates
nothing.** Five routes that do not depend on the corpus:

1. **Spec-derived oracles.** An independent implementation of the *standard's*
   arithmetic, not of the tool's. `oracles/restart_cutoff_exact.py` is the worked
   example: it reproduces the spec's own published cutoffs, so it is checkable
   against the document rather than against the tool. **This is the strongest
   route and it is the one to prefer wherever the quantity is closed-form.**
2. **Inputs whose correct verdict is known by construction.** The C07/C03
   verification below used one: a 20,000-sample repeat implanted in 1,000,000
   bits **must** fail the LRS test, because such a repeat is astronomically
   improbable under IID. No reference value is needed — the right answer follows
   from how the input was built. (This is instrument calibration with known
   input, licensed by Part 11.)
3. **Metamorphic relations — properties that must hold whatever the corpus
   says.** `min-of-ten ≤ every individual estimator`; a figure must never exceed
   `log2(alphabet)`; `H_bitstring Per Symbol == n × H_bitstring` (now pinned);
   adding entropy must not lower the figure. **`C06` was caught by exactly this
   route** — `h_out` 7.1552 against a 7-bit ceiling needs no reference at all.
4. **Build-differential testing.** A correct fix should give the **same answer
   under `-DNDEBUG` and with asserts live.** This is corpus-free, mechanical, and
   it is how the repair branch's fix was confirmed below.
5. **Two-figure reporting, which is also the governing constraint** — see below.
   The delta between the reference tool and the fork *is* the validation
   artefact: it is inspectable, and a patch that changes a figure it should not
   have changed shows up as an unexplained delta.

**What none of these give** is assurance that a fix is correct in cases none of
them covers. With no independent reviewer, that residual is real and should be
stated in any report rather than closed by assertion.

---

## Class 4 — no bound exists. These decide whether configuration is sufficient.

**`C07` under `-DNDEBUG` on master.** The 0.9954 figure is **not an inflation of
a real estimate — it is fabricated**: an underflow makes the LRS test return
*failure*, `C03` discards the failure, and a figure above the project's 0.5
threshold is published for data the tool could not evaluate. **There is nothing
to subtract**, because no measurement occurred. Treatment is therefore Class 1
(refuse NDEBUG builds) or Class 3 (fix the code) — **never a bound.**

**`C03` on master**, for the reason given above: the track-selection gap is a
property of the data.

**Nothing else is in this class.** Every other permissive defect either inflates
a quantity that was genuinely computed, or is neutralised by configuration.

**The consequence the question asked for:** on master, **configuration
enforcement is sufficient *only* if it is actually enforced** — an
`ASSERTS-LIVE` build makes `C07` conservative and `C09` an abort, leaving a
boundable residue. **Under an `NDEBUG` build the tool cannot be used at all for
a floor claim**, with or without bounds.

---

## The repair branch, assessed against this classification

**It closes both Class 4 entries, which is the most consequential thing in this
document.** Verified by building `2d4b135` in a throwaway worktree and running
the `C07` site-B input (digest `327773dd47cc4807…`, W = 20000):

| build | exit | `errorLevel` | `IID` | `hAssessed` |
|---|---:|---|---|---|
| **master, asserts live** | **134** | — | — | no JSON; `Assertion failed: (p_colPower >= LDBL_MIN)` at `lrs_test.h:683` |
| **master, `-DNDEBUG`** (`OC-10`) | **0** | **0** | **true** | **0.995373734104443 — fabricated** |
| **repair, asserts live** | **1** | **2** | absent | **absent** |
| **repair, `-DNDEBUG`** | **1** | **2** | absent | **absent** |

Both repair builds print `** Failed length of longest repeated substring test`
then `IID test suite failed: no IID min-entropy estimate was awarded.`

- **`C07` closed at the root.** `a3dde6f` deletes both asserts and computes in
  the **log domain** (`logCollisionPower = W · log(p_col)`), so the
  unrepresentable intermediate is never formed. **The NDEBUG divergence is gone**
  — identical output in both builds, which is validation route 4 passing.
- **`C03` closed.** The same commit adds
  `testRun.errorLevel = 2; errorMsg = "IID test suite failed; no IID min-entropy
  estimate was awarded."` and gates the figure behind a complete passing
  battery — *"Only a complete passing IID battery may expose the final IID
  entropy"*.
- **The `C07 → C03` chain is closed**, which is what produced 0.9954.
- **`C23` and `C22` are untouched** — confirmed by diffing the branch's `cpp/`
  changes for `ZALPHA`, `2.576`, `cutoff` and `simulateBound`: no hits. The two
  Class 2 items remain open on both branches.

### `REPAIR-BLOCK-01` — the premise no longer holds, and the block should be reconsidered

It was recorded as: the branch reports the underflow as
`** Failed length of longest repeated substring test`, *"an arithmetic limit
presented as a statistical rejection of the operator's hardware"*. **On the
evidence above that reading does not survive the rewrite.**

- There is **no longer an unrepresentable quantity being relabelled.** The log-
  domain form computes the probability correctly; the old `assert` was itself the
  defect, aborting on a case that was exactly decidable.
- In the deep regime the code sets `probabilityAtLeastOne = 0.0L` only when the
  *expected number* of collisions falls below `LDBL_MIN` — i.e. when a collision
  is astronomically improbable. Rejecting IID there is **the correct statistical
  conclusion**, not an artefact.
- **The regime is only reachable on genuinely non-IID data.** A large `W` *is* a
  long exact repeat; for truly IID 1,000,000-bit input `W ≈ 40` and nothing
  underflows. So "Failed" in that regime is always right. The test input used
  here has a deliberately implanted 20,000-sample repeat: the data **is** not
  IID, and failing is correct.

**This is a finding, not an authorisation.** The instruction that
`REPAIR-BLOCK-01` must be fixed before merge was explicit, and it should be
lifted deliberately rather than by my inference. Recorded so the decision can be
made on evidence; **the rebase remains NOT authorized.**

---

## Recommendation

**Repair, by rebasing — and the answer to "is the rebase worth reopening" is
yes, for a reason that was not visible before this assessment.**

1. **The repair branch is the only thing that closes the two unboundable
   defects.** `C03` and `C07` have no bound to subtract, so documentation and
   configuration cannot substitute for the code that already exists on that
   branch. It is written, and it now has corpus-free validation (build-
   differential plus a constructed input).
2. **Everything left after the rebase is Class 1 or Class 2** on the
   Chor–Goldreich path: `C22` (bound unmeasured), `C01` (±3.69e-4), `C02`
   (read `h'`), `C23` (use the exact oracle for the restart decision). That is a
   defensible floor; the current state is not.
3. **Before the rebase, two things that are cheaper than it and do not depend on
   it:** measure `C22`'s bound, and apply `C23`'s oracle to the restart
   decision. Both are free, neither touches the tools, and `C22` is the only
   unmeasured quantity between the figure and a floor.
4. **Enforce `ASSERTS-LIVE` regardless.** It is the cheapest treatment, it is
   already mechanised, and it remains necessary for `C09` and for any binary
   whose provenance is not ours.
5. **`REPAIR-BLOCK-01` needs an explicit decision**, not an inference, before the
   branch merges.

### The governing constraint: two figures, always

Whatever the fork reports, **the reference tool's own figure must remain
reportable alongside it, with the delta explained.** A figure only our patched
fork produces is self-authored measurement on top of self-authored code, and
there is **no independent reviewer** on this project to catch an error in the
patch — Paul has decided there will not be one.

So the reporting shape is fixed:

| | |
|---|---|
| **upstream figure** | `87c104d`, `ASSERTS-LIVE` build, stated verbatim |
| **fork figure** | our tree, same input, same build class |
| **delta** | with the specific defect each component is attributed to |
| **floor** | fork figure − Σ bounds of the Class 2 defects still in play |

**Two figures and a stated difference is a stronger position than one better
number**, and it is the only form in which a patched-tool figure is worth
anything without a reviewer. It also makes the patch falsifiable: a delta that
cannot be attributed to a named defect is evidence of an error in the patch.
