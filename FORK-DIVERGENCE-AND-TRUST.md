# Fork divergence and external trust

**Measured at commit `11207ca`, 2026-10-25.** Every count in this document
names the commit and date it was taken at. Reproduce them with
`sh tools/measure-divergence.sh`; `cpp/selftest/regression-docs.sh` re-runs that
script and fails if the figures below disagree with it.

Supersedes the version dated 2026-10-09. **Seven statements in that version are
false, not merely out of date** — they are listed and corrected as false in §0,
because a reader who met them would have drawn a wrong conclusion, and
"superseded" does not say that.

## How to read this

The fork is **a patched fork of NIST's SP 800-90B reference implementation**. It
does not modify or redefine the standard. It must not be described as
NIST-approved, NIST-certified, the official NIST tool, or a customised version
of SP 800-90B.

Defects are filed in **three sections that do not overlap**:

| | section | what belongs in it |
|---|---|---|
| **A** | [Code defects](#a--code-defects) | the implementation does something other than what SP 800-90B specifies, or other than what it itself claims |
| **B** | [Standard defects](#b--standard-defects) | the implementation does what SP 800-90B specifies **and the specified thing is wrong or ambiguous** |
| **C** | [What none of this establishes](#c--what-none-of-this-establishes) | claims no software estimator can produce, whatever it computes |

**A and B never share an entry, and an entry never drifts between them.** The
test is single and mechanical: *would conforming exactly to the standard's text
fix it?* If yes, it is a **code** defect. If conforming exactly to the text is
what produces the wrong behaviour, it is a **standard** defect. `C18` is a code
defect — the standard says nothing about `long` width, and 64-bit arithmetic
fixes it. `C23` is a standard defect — §3.1.4.3 step 5's printed formula tests
the wrong statistic, and implementing it faithfully is what rejects
correctly-operating sources. The two have opposite remedies, which is why they
must not sit together: a code defect is fixed by changing the fork, a standard
defect can only be *diverged from*, documented and bounded.

Section C carries **prose, not entries** — there is nothing to repair in it.

### Every entry in A and B carries five fields

| field | what it must say |
|---|---|
| **DEFECT** | the behaviour, stated as behaviour rather than as a code location |
| **ORIGIN** | **INHERITED** from upstream, or **INTRODUCED BY THIS FORK** — and if introduced, by which repair. A fork that only inherited defects would be a fork that never broke anything, and this one did. |
| **EVIDENCE** | **EXECUTED** (naming the platforms it ran on), **DERIVED** (follows from a proved argument), or **SOURCE-CONFIRMED** (read in the code, never run). These are three different strengths and are never collapsed. |
| **STATUS** | **NOT REPAIRED**, **REPAIRED** (with the record entry), or **REPAIRED AND INDEPENDENTLY REVIEWED**. **REPAIRED IS NOT REVIEWED.** Nothing in this fork is in the third state **and nothing ever will be** — §5 Decision 2 records that there will be no independent review of any kind, ever. The third state is named only to say what is permanently absent. |
| **DOES NOT ESTABLISH** | what a reader must not conclude from the repair. Every entry has one; an entry without one is incomplete. |

---

## §0 — Statements in the 2026-10-09 version that are FALSE

Each is quoted, then corrected **as false**. None of these was a matter of
emphasis or staleness: a reader acting on any of them would have been wrong
about the state of the tree.

| # | the previous version said | correction |
|---|---|---|
| **1** | *"`R-1`: the x86-64 80-bit `long double` IID path remains unverified and unfixed"* | **False on both halves.** `R-1` is `FORK-FIXED` in the tracker, repaired 2026-10-19, and it was **executed** on Linux x86-64 *and* Windows MinGW. It is also not a platform defect but a `long double` **format** defect: 117 of 255 alphabet sizes on a 53-bit `long double`, 155 on x87 80-bit. |
| **2** | *"`N-08`: permissive numeric parsing remains in direct CLI paths"* | **False.** `SUPPORTED-SCOPE-FIXED`. The supported CLIs and the transpose path are fixed; the `ea_conditioning` instance stays excluded by `876ba05`, which is a scope decision and not a remaining defect in the supported product. |
| **3** | *"`N-10`: ambiguous report semantics remain"* | **False.** `SUPPORTED-SCOPE-FIXED`, with the conditioning half excluded by the same commit. |
| **4** | *"`NOVEL-03`: IID restart row and column results retain ambiguous labels"* | **False.** `FORK-FIXED`. Independent verification of `25fbb54` remains outstanding — which is a different statement, and is the one this document should have made. |
| **5** | the whole **quantified divergence** block: *"Fork repair branch: `repair/2026-10-09-verified-defects`… commit `9556649`… 66 commits ahead… 658 changed paths, 62,252 added text lines"* | **False as a description of this fork.** That branch was merged into `master` at `d226f18` on 2026-10-15 and no longer exists as a separate head. Measured at `11207ca`, 2026-10-25: **179 commits ahead, 0 behind, 1,033 text files, 108,859 insertions, 461 deletions.** Every figure in that block was off by more than a factor of 1.5, and none of them said when it had been taken. |
| **6** | route item 7: *"Validate Linux and Windows before claiming support for those platforms"* | **False as a pending action.** Both are measured, by CI rather than by acquiring machines: x86-64 Linux on every push since 2026-10-19, Windows MinGW on 2026-10-20. What remains is not validation but **independent** validation — which §5 Decision 2 records as permanently declined, so nothing remains as a pending action at all. |
| **7** | route item 8: *"Submit generally applicable repairs upstream where practical"*, and *"Upstream acceptance would improve maintainability and external confidence"* | **Contradicts a standing decision, and was never a mere omission.** The owner decided on 2026-10-15 that **nothing is reported upstream**. The route list described a route the project has declined to take, which is worse than not listing it: a reader would have treated the absence of upstream reports as neglect rather than as policy. §5 states that decision and its consequences instead — and the first rewrite of §5 then made the same mistake with a different route, which §5 now records. |

**On item 7's framing.** Replies on this fork's upstream issues and pull
requests came from `@joshuaehill`, who is not a NIST account and who deferred
to "the NIST folks" on PR #268. No statement anywhere in this repository should
be read as NIST having reviewed, accepted or commented on anything here.

---

## §1 — Quantified divergence

Measured at `11207ca`, **2026-10-25**, against upstream base
`87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289` (2026-05-26), which is the common
ancestor. The fork is **0 commits behind**, so `base..HEAD` is the whole
divergence.

| Category | Files | Insertions | Deletions |
|---|---:|---:|---:|
| Production C++ and build | 21 | 2,188 | 450 |
| Self-tests and regression harness | 50 | 7,303 | 7 |
| CI workflows and scripts | 4 | 1,258 | — |
| Audit and repair evidence | 950 | 96,284 | — |
| Other documentation | 8 | 1,826 | 4 |
| **total (text)** | **1,033** | **108,859** | **461** |
| Binary reference artefacts | 2 | — | — |

**179 commits ahead.** The headline is dominated by evidence: 88 % of the
insertions are audit and repair records. **The executable delta is 2,638 lines
of churn across 21 files** — not a cosmetic fork, and not a rewrite of the
estimators.

Two other counts, because they bear on how much of the above is *checked*
rather than merely written:

| | count | measured at |
|---|---:|---|
| enforced suite | **24** checks, **22** regression scripts | `11207ca`, 2026-10-25 |
| instruments that a sweep must cover | **74** live, **79** frozen | `11207ca`, 2026-10-25 (`audits/INSTRUMENT-INVENTORY.md`, enforced against its enumerator) |
| orchestrator records | **91** entries | `11207ca`, 2026-10-25 |
| withdrawn verifications | **2** | `audits/WITHDRAWN-VERIFICATIONS.md` |

**None of these is a measure of correctness.** A suite of 24 checks that all
pass establishes what `cpp/selftest/WHAT-A-GREEN-SUITE-ESTABLISHES.md` says it
establishes and nothing beyond it, and that document exists because the number
on its own invites the opposite reading.

---

## A — Code defects

The implementation does something other than what SP 800-90B specifies, or
other than what it itself claims. **Conforming exactly to the standard's text
would fix every entry here.**

Split by **origin**, because the two halves mean different things to a reviewer:
the first is what the fork found in what it inherited, and the second is what
the fork broke itself. A fork that listed only the first would be claiming it
never broke anything.

### A.1 — Inherited from upstream

#### `C18` — the LRS test fails whatever the data, on any LLP64 target

- **DEFECT.** `n_choose_2` computed `N` in `long int`. On LLP64 targets —
  Windows — `long` is 32 bits, so for a 1,000,000-sample input the true
  `N = 499,960,500,780` became **−403,189,204**, `Pr(X ≥ 1)` printed
  **−0.000367** where macOS printed **+0.365370**, and the §5.2.5 decision
  compared against `logl()` of a negative number — **NaN**. The LRS test
  therefore failed **whatever the data was**.
- **ORIGIN.** INHERITED. It had sat in the record as a source-only candidate
  whose consequence was stated in the conditional: `long int` "**would**
  overflow".
- **EVIDENCE.** **EXECUTED on Windows MinGW** via CI, 2026-10-20 (`OC-48`), and
  the printed value reproduced exactly from the integer arithmetic alone by
  `reproducers/c18_llp64_overflow.c`. Before that it was **SOURCE-CONFIRMED
  only** — and the gap between the two is the whole point of the Windows job.
- **STATUS.** **REPAIRED** (`OC-53`): `int64_t n_choose_2(const int64_t n)`
  with an assertion bounding `n` to `INT_MAX`.
- **DOES NOT ESTABLISH.** That no other 32-bit `long` arithmetic remains. The
  repair fixes the one site the reproducer exercised; a sweep of the remaining
  `long` arithmetic on LLP64 has **not** been done.

#### `R-1` — a `long double` FORMAT defect, not a platform one

- **DEFECT.** An unclamped probability in `lrs_test.h` aborts on an assertion
  for a wide band of alphabet sizes.
- **ORIGIN.** INHERITED (upstream #246, PR #248 merged and incomplete).
- **EVIDENCE.** **EXECUTED** on Linux x86-64 and Windows MinGW: **117 of 255**
  alphabet sizes affected on a 53-bit `long double` (Apple arm64), **155 of
  255** on x87 80-bit. It had been labelled NOT-REPRODUCIBLE-HERE because its
  assert does not fire on the development host — which is the class of claim a
  single-platform project cannot evaluate about itself.
- **STATUS.** **REPAIRED** 2026-10-19, clamping to `1.0L/k`.
- **DOES NOT ESTABLISH.** Independent verification of the clamp remains
  outstanding. And the figure is per-format, not per-platform: a third format
  (binary128, Linux aarch64) is **NOT RUN**.

#### `C01`/`F10` — MultiMMC chained-lookup saturation

- **DEFECT.** Dictionary saturation can make the MultiMMC estimator overstate
  entropy.
- **ORIGIN.** INHERITED.
- **EVIDENCE.** One **EXECUTED** overestimate (`f10_over_8bit_1M`), and at
  width 1 a **DERIVED** exclusion: with `D_MMC = 16` and
  `MAX_ENTRIES = 100000`, binary data gives `entries[d] ≤ 2^(d+2)`, so the cap
  cannot bind below `d = 15` and `d = 15` has no `d+1` to suppress. **A proof,
  not a measurement.**
- **STATUS.** **NOT REPAIRED.** Excluded from the entropy floor at width 1 by
  the proof above; above width 1 it contributes an **evaluated margin** of
  3.69e-4 and the floor oracle then refuses to call its output a floor at all.
- **DOES NOT ESTABLISH.** Anything above width 1. The margin is one measured
  overestimate over the inputs tried; the mechanism is data-dependent, so
  nothing bounds it.

### A.2 — Introduced by this fork, and repaired

**These are the entries a reviewer should read first.** Each was introduced by
a repair this fork made, which means the fork's repairs are exactly as capable
of creating defects as of removing them.

#### `A05` / `F03` — the report writer destroyed the assessment input

- **DEFECT.** Two defects in one write path, four days apart.
  **`A05`:** `C14`'s placeholder claimed the `-o` path as soon as it was known,
  so `-o capture.bin capture.bin` replaced a 1,000,000-byte capture with a
  ~600-byte error report **before a single sample was read**.
  **`F03`:** with that closed, the *temporary* beside the report was still
  named `<report>.tmp.<pid>` and opened with `std::ios::trunc`, **which follows
  a symlink**. Measured on all three tools: the capture came back **798 bytes**
  of report JSON; `rename()` renamed **the symlink**, leaving the `-o` path a
  permanent alias of the capture so every later run would destroy it again with
  nothing in the directory to notice; and the `A05` guard then fired on the
  second write and printed *"Nothing has been written; the input is
  untouched"* — **both halves false when it printed.**
- **ORIGIN.** **INTRODUCED BY THIS FORK.** `A05` by `C14`'s fail-closed repair;
  `F03` by `C08`'s atomic-write repair. Two repairs, each correct in its own
  terms, combining into the one failure the project cannot absorb — in January
  the input is a physical capture that cannot be recreated.
- **EVIDENCE.** **EXECUTED** on Darwin arm64 against a build of the
  pre-repair commit, all three tools, with the capture's SHA-256 before and
  after. `regression-output-aliasing.sh` fails exactly these cases on that
  build and passes on this one.
- **STATUS.** **REPAIRED** (`OC-77`): `O_CREAT|O_EXCL` — which does not follow
  a symlink — plus `O_NOFOLLOW`, a random suffix from `/dev/urandom` instead of
  the pid, the temporary identity-checked against the protected input like any
  other write target, and an `fstat` after opening, because an open that
  succeeded is not proof of what it opened.
- **DOES NOT ESTABLISH.** Windows is **NOT RUN** for `F03`: it takes the
  `MoveFileExA` branch and has no `symlink()`. The `fstat` limbs are
  **SOURCE-CONFIRMED, not executed** — a wrong `st_uid` cannot be arranged at a
  path whose name is unpredictable by design, which is the repair working
  against its own test.

#### `C24` — no report could be written on Windows at all

- **DEFECT.** `C14`'s placeholder created the `-o` file, and `C08`'s atomic
  write then used `rename()`, which on Windows **refuses an existing
  destination** (errno 17). The two together meant **no report could be written
  on Windows**, by any invocation.
- **ORIGIN.** **INTRODUCED BY THIS FORK**, by the interaction of two of its own
  repairs. Neither is wrong alone.
- **EVIDENCE.** **EXECUTED on Windows MinGW** via CI, 2026-10-20, with the old
  writer failing beside the new one in the same job.
- **STATUS.** **REPAIRED** (`OC-57`): `MoveFileExA` with
  `MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH` under `_WIN32`.
- **DOES NOT ESTABLISH.** That the Windows path is otherwise sound. The job
  measures what it measures; the ten `cmd` blocks in that workflow are checked
  by **no syntax tool**, because `cmd` has no `-n` equivalent available here.

#### `F04` — the `--version` prescan covered one spelling of the same request

- **DEFECT.** `-vo --version data 1` and `-qo --version data 1` printed the
  version banner, **exited 0, assessed nothing and wrote no report** — leaving
  any previous report in place with a success status. The prescan tested the
  cluster's **last** character and then required the cluster to be exactly two
  characters, so it fired for `-o` and for nothing else.
- **ORIGIN.** **INTRODUCED BY THIS FORK**, by `A04`'s own repair.
- **EVIDENCE.** **EXECUTED**, all three tools, both arms.
- **STATUS.** **REPAIRED** (`OC-80`) by walking the cluster the way `getopt`
  does. A third spelling, `-Z --version`, was open on the pre-repair build too
  and was found by the repair's own controls, not by the audit.
- **DOES NOT ESTABLISH.** `getopt` **permutation** is unexamined: glibc permutes
  non-options by default, so on Linux a `--version` placed after the first
  operand may still reach `getopt` where this prescan stops. **Not reproduced,
  not repaired.**

#### `C16` — `H_I` without a stated scale

- **DEFECT.** `ea_restart` accepted a bare `H_I` whose scale was ambiguous
  between per-symbol and per-bit — a factor of `word_size`.
- **ORIGIN.** INHERITED in form; the fork's own restart work surfaced it.
- **EVIDENCE.** **EXECUTED.**
- **STATUS.** **REPAIRED** (`OC-29`): a bare number is accepted only at width 1,
  where the two coincide; otherwise `/symbol` or `/bit` must be stated.
- **DOES NOT ESTABLISH.** That any figure computed before the repair used the
  scale its author intended.

---

## A.3 — A deliberate behaviour divergence from upstream, which is not a defect

**One entry, and it is the only change in this fork that will REFUSE a command
line upstream accepts.** It is recorded in section A because that is where a
reader looks for differences in the code's behaviour, and separated into its
own subsection because calling it a defect would be wrong in both directions:
it was not a defect that it existed, and it is not a repair that it is gone.

#### `OC-104` — an option after the file operand is refused

- **WHAT CHANGED.** All three tools refuse a command line with an option
  placed after `<file_name>`, naming the offending argument and printing the
  correct form. Upstream accepts such a line, as did this fork until
  2026-10-25.
- **WHY, AND IT IS MEASURED NOT STYLISTIC.** `getopt` disagrees across the two
  supported platforms. **glibc PERMUTES** the command line and parses the
  option; **BSD/macOS stops at the first operand** and treats it as another
  operand. Measured both ways: `ea_non_iid -i -a f 1 -q -o r` **assessed and
  wrote `r`** on x86-64 glibc (CI step 5c) and **died on the usage path with
  nothing assessed** on Darwin arm64. One command line, two supported
  platforms, two different operations. Worse, every guard reading the
  pre-`getopt` identity prescan is **unarmed by construction** on the permuting
  side, because the prescan stops where BSD `getopt` stops — so a `-o` after
  the operand never reached `outputTargetIsSafe`. `OC-102` measured that
  `writeJsonReport`'s choke point still caught it, so no capture was ever at
  risk; but an unarmed guard is recorded as unarmed, not as passing.
- **EVIDENCE.** **EXECUTED**, on both platforms. `regression-option-order.sh`,
  29 checks, **verified by breaking it**: 10 failures against a build with the
  refusal removed, 0 with it in place, the two builds distinguished by
  `build-state` sha256. CI step 5c now measures the `getopt` fact with a
  standalone C program — *not* through the tools, which would report "no
  permutation" now that they refuse first — and asserts the refusal separately.
- **WHAT IT COSTS, re-measured rather than carried forward.** An argv logger
  compiled into all three tools captured **256 real invocations** across the
  full suite. **2 of 256** put an option-shaped argument after the operand, and
  **both are numeric `H_I` values** (`-inf`, `-1`) in `regression-restart.sh`'s
  `N-04`, which the refusal **exempts** — a number after the operand is a value,
  not an option. **0 of 256 use a genuine option spelling after the operand.**
  The two sites the change does break are CI step 5c's own permutation probes,
  whose purpose was to exercise this shape; they are converted to assert the
  refusal. The January re-pin procedure is unaffected.
- **DOES NOT ESTABLISH.** That the divergence `OC-40` recorded is gone. For
  **numeric** arguments after the operand it **REMAINS**: `ea_restart f 8 -inf`
  still reaches the `H_I` parser on BSD and still goes through `getopt`'s
  invalid-option path on glibc. Both refuse; the message differs. That is
  unchanged, deliberately, because refusing `-1` with *"put every option before
  the file"* would be a wrong message about a value the operator meant as a
  value.

---

## B — Standard defects

**The implementation does what SP 800-90B specifies, and the specified thing is
wrong or ambiguous.** Conforming more faithfully would make these worse, not
better. They cannot be "fixed" in a fork — they can only be **diverged from,
with the divergence documented and bounded**, which is what makes this section
the one an outside reviewer should weigh most carefully: every entry here is a
place where this fork deliberately does **not** do what the text says.

#### `C23` — §3.1.4.3 step 5's printed formula rejects correctly-operating sources

- **DEFECT.** The restart sanity check forms the **maximum over cells** of a
  1000×1000 matrix, but step 5's printed formula tests a **single binomial
  tail**. Implemented faithfully, it rejects sources that are operating
  correctly: **83.2 % of full-entropy 8-bit matrices**, measured.
- **ORIGIN.** **THE STANDARD.** Upstream implements the text. There is no
  implementation error to find.
- **EVIDENCE.** **EXECUTED** (the 83.2 % rejection rate) and **DERIVED** (the
  exact cutoff from Levin's representation for the multinomial maximum, in
  exact rational arithmetic, cross-checked against brute-force enumeration to
  better than 1e-12 on six configurations).
- **STATUS.** **DIVERGED, deliberately.** The fork decides on the exact
  multinomial maximum and records `restartCutoffMethod` in the report so a
  consumer can tell which statistic produced a verdict. The printed binomial
  figure is still computed and recorded **for traceability, and is not the
  verdict**.
  *The direction was inverted once:* an earlier entry had it backwards, and the
  correction is `OC-30`. *And the verification was withdrawn once:* `WV-1`, a
  claim to have checked 32 `H_I` values that was printed from an **empty loop**.
  It now carries 32 oracle-derived triples and refuses fewer.
- **DOES NOT ESTABLISH.** That the fork's cutoff is the one a certifier would
  accept. It is a **documented divergence from the published text**, which is
  precisely the kind of thing an accreditation body decides and this project
  cannot. At the operating point `H_I = 0.696` both cutoffs give 684 and the
  divergence changes no verdict for this device — proved by bisection on the
  crossings, with the nearest disagreement at `H_I ≈ 0.888`.

#### `C22c` — §6.3.4 step 6 prints a rounded quantile

- **DEFECT.** The text prints `2.576` where the exact 0.995 normal quantile is
  `2.5758293035489008`. A tool that uses the printed constant and a tool that
  uses the exact one give different figures.
- **ORIGIN.** **THE STANDARD** — a literal-text parity issue, not an error in
  anyone's code.
- **EVIDENCE.** **DERIVED.** The resulting ceiling on the entropy difference is
  `dz·σ_max/√v` with `σ_max` bounded by Popoviciu's inequality and
  `v = num_blocks − 1000` exact; the ceiling itself is an exact solve at a
  **derived** argmax, computed independently from §6.3.4 step 7 as written and
  **validated against the standard's own worked example** — NIST publishes
  `p = 0.5715` for `d=4, N=8, v=4, X'=1.4617` and the independent
  implementation gets `0.57148426` (`OC-86`).
- **STATUS.** **DIVERGED:** the fork uses the exact quantile. The difference is
  carried in the entropy floor as `C22c` — 3.3599e-3 bit at n = 10⁶, 2.1644e-3
  at n = 8×10⁶ — so a figure from this fork and a figure from a literal-text
  implementation can be reconciled.
- **DOES NOT ESTABLISH.** Confirmation at **two** bitstring lengths only, the
  two the record tabulates. The term's fall with `n` is measured, not proved,
  and the value used at an intermediate `n` is the one tabulated at the largest
  `n` not exceeding it.

#### The entropy floor itself is **MEASURED**, not certified

Not a defect, but it belongs here because it is the quantity a reader is most
likely to over-read, and its status is set by the two entries above plus one
term of the fork's own.

The floor subtracts four terms. Their statuses are **not** the same, and the
aggregate takes the **weakest**:

| term | status |
|---|---|
| `C01`/`F10` | **PROVED EXCLUSION** at width 1 — unreachable, by the counting proof in A.1 |
| `C22a` | **MEASURED** — `8.08e-15` is `c × K`, a **product of two grid maxima** |
| `C22b` | **PROVED** — zero; conservative at every `N` |
| `C22c` | **DERIVED** — `dX'` bounded, the ceiling an exact solve at a derived argmax (`OC-86`) |

So the oracle prints **`MEASURED FLOOR (C22a)`**, naming the term that holds the
status there, and **"certified floor" is a retired term**: no reading of the
floor is certified, and `regression-docs.sh` fails both on the phrase without a
retirement marker and on any assertive use of it outside quotation marks.

**The certification was a WITHDRAWN VERIFICATION, not a relabel.** `OC-63`
claimed `C22a`'s constant had been *checked* to be a supremum. That claim is
withdrawn with its date and reason as **`WV-2`** in
`audits/WITHDRAWN-VERIFICATIONS.md`: the interiority argument examined `c` and
not `K`, `K` is attained at `r = 2` — the **first value in its swept list** —
and the sweep reaches **92.8 %** of the ceiling it is supposed to bound.
**No figure changed**; what changed is the status claimed for it.

- **DOES NOT ESTABLISH.** That the floor is a lower bound in the sense a
  certifier would want. Settling `C22a` means extending the `r` axis below 2 and
  the `N` axis below 5, or replacing `K`'s grid maximum with an analytic
  infimum. **Not attempted.**

---

## C — What none of this establishes

Prose, not entries: there is nothing here to repair, and nothing a software
estimator can produce however carefully it is built.

Neither a favourable entropy estimate nor a green suite shows:

- that a physical source is independent, stationary, or stable across its
  operating range;
- that continuous health tests are appropriate for the deployed source;
- that an extractor seed is uniform, independent, or safely managed;
- that pad material is transferred, stored, consumed and erased securely;
- that pad bytes are never reused;
- that a compiled artefact came from an uncompromised compiler, dependency
  chain or build host; or
- that the producer is organisationally independent from the authority that
  approves the artefact.

Those are physical, operational, supply-chain and governance claims.

**Three further limits belong here, because they are about this fork rather than
about estimators in general.**

**Every repair in sections A and B is self-authored and PERMANENTLY
UNREVIEWED.** Not one entry is in the `REPAIRED AND INDEPENDENTLY REVIEWED`
state, and **§5 Decision 2 records that none ever will be**. The external audits
this project has run were **read-only**: they found defects, and the repairs
answering them were written by the same author as the code. **The verdict is
partially established, permanently** — not pending.

**The evidence has itself been defective, repeatedly, and the record says so.**
Two verifications have been withdrawn (`WV-1`, `WV-2`). A five-of-nineteen
false-pass was found inside the enforced documentation check. A dead-guard
baseline of **39 flags** is pinned, covering **67 flagged lines**, and **all 39
are unresolved** — a resolved flag leaves the baseline, so the earlier
"36 of 40" described nothing (`OC-95`). Triaged by mutation (`OC-98`): **1**
line could reach a figure or a claim and is repaired, **54** could not, **12**
are false positives of the detector. **The 1 is a FLOOR, not a count**: the
detector has a measured 16 % false-positive rate and a *demonstrated* false
negative — a class-D pipe was silently missed because the word `pipefail`
appeared in a comment. Confidence in the repairs cannot exceed confidence
in the instruments that checked them, and that is lower than a green suite
looks.

**A figure from an unidentified binary is uninterpretable** whatever the
arithmetic says. The build-provenance canary exists for this, and the suite
reports that **4 of 24** checks declare the artefact they measured — so twenty
do not.

---

## §5 — Two standing decisions, and what they settle permanently

The 2026-10-09 version listed nine "routes to external trust", two of which
described routes this project has **declined** (§0, items 6 and 7). **The first
rewrite of this section removed the upstream route and then led with four items
asking for independent review — which the owner had already declined, in
`CLOSING-INVENTORY.md`'s will-not-be-done bucket, on 2026-10-15.** That is the
same error as §0 item 7, made again in the correction of it. Corrected here, and
the shape of the section changes with it: there is no route list, because the
routes are closed.

### Decision 1 — nothing is reported upstream

Decided **2026-10-15**, on the basis that an earlier upstream PR went
unacknowledged. Its consequences are owned rather than regretted:

- the private patch surface is **permanent**, and every rebase onto a future
  upstream release is this project's work;
- the standard defects in section B stay **this fork's documented divergences**
  and will never be resolved by upstream adopting them;
- no reviewer will find corroboration of these findings in an upstream issue
  tracker, so the evidence in `audits/` carries the whole weight;
- **no statement anywhere may imply NIST involvement.** Replies on this fork's
  upstream issues came from `@joshuaehill`, not a NIST account;
- and **no request of any kind is sent there.** Not an issue, a pull request, a
  comment, a workflow dispatch, or an unqualified `gh` call — the last because
  one such call did reach `usnistgov` and was refused only by a 404 (`OC-93`).

### Decision 2 — there will be no independent review, of any kind, ever

Recorded in the will-not-be-done bucket and restated **2026-10-25**: **no
independent cryptographer or security review, ever.** It is not a queue item, not
pending, and not a gap.

**This settles what the fork can ever establish about itself**, and the
consequences are larger than the first decision's:

- **REPAIRED never becomes REVIEWED.** Every entry in sections A and B is in the
  `REPAIRED` state, every one of them is self-authored, and **none will ever move
  to `REPAIRED AND INDEPENDENTLY REVIEWED`.** That third state exists in the
  field vocabulary only to name what is permanently absent.
- Every *"independent verification remains"* note in
  `audits/2026-09-30/FINDINGS-TRACKER.md` — including `C-01`'s, which is
  otherwise fixed — **resolves here and nowhere else.**
- The four defects in **section A.2** were introduced by this fork's own repairs,
  three of them by one repair interacting with another. **The mechanism that
  produces those is reviewed by nobody but its author**, and rule 12 — declare
  the pair, test the pair — is the whole of the mitigation.
- The instruments are in the same position. Two withdrawn verifications
  (`WV-1`, `WV-2`), a five-of-nineteen false pass inside the enforced
  documentation check, a dead-guard detector with a measured 16 % false-positive
  rate **and a demonstrated false negative** — all of it found by the same author
  who wrote the instruments.

### What follows: the verdict is PERMANENTLY PARTIALLY ESTABLISHED

Not "pending independent review". There is no pending.

| | |
|---|---|
| **what is established** | that specific defects reproduce, that specific repairs change the reproduced behaviour, and that specific figures re-derive — each on the platforms named in its entry, by instruments this project wrote |
| **what is permanently not established** | that the repairs are correct, that the instruments are sound, that the figures are right, or that any of it would survive a reviewer |
| **what the verdict therefore is** | **partially established, permanently** — and that is the ceiling, not a waypoint |

A reader who wants more than this cannot get it from this repository, and the
honest thing is to say so in the document rather than to list routes nobody will
walk.

### Readiness

**The repaired code is not, and will not become, independently reviewed
software.** It is not sufficient evidence for production entropy approval, and
no future work in this repository changes that — only a decision to reverse
Decision 2 would, and that decision is recorded as permanent.

TruePad must retain:

```json
{
  "productionApprovalEnabled": false,
  "approvedBuilds": []
}
```

That is a statement of what the consuming project must keep, quoted here for
completeness. **Nothing in this repository changes it, and no change to it is
made from here.**

Merging repair code and approving an entropy-assessment artefact are separate
decisions — and on this project the second one has no path to yes.
---

## §6 — Dates, and how this document goes stale

The previous version carried one date at the top, a 2026-10-15 note bolted into
the middle, and seven statements that had become false. **A single date on a
document that mixes measurements of different vintages tells a reader nothing**:
it was the mechanism by which §0's items 1–5 survived.

So:

1. **Every count names the commit and date it was measured at**, at the point
   of use. Not once at the top.
2. **Every count that can be re-derived, is** — by
   `sh tools/measure-divergence.sh`, which prints the §1 figures from `git` at
   the current `HEAD`.
3. **A check enforces it.** `cpp/selftest/regression-docs.sh` re-runs that
   script and fails if the figures in §1 disagree with it. This document cannot
   go stale in its divergence figures without the suite going red.
4. **What a date cannot police is marked instead.** Statuses in sections A and
   B are claims about the tree, so they carry the record entry that established
   them (`OC-nn`, `WV-n`); a reader who doubts one reads that entry rather than
   trusting this summary.
5. **A superseded figure is kept with its correction, as false.** §0 is the
   mechanism, and `audits/WITHDRAWN-VERIFICATIONS.md` is the same mechanism for
   verifications. "Out of date" is not available as a description of a statement
   that was wrong.

The enforced figures are §1's divergence table and the derived counts beside it.
**The prose is not enforced** and will go stale in the ordinary way; where it
makes a claim about the tree it cites the entry that can be checked.

---

## §7 — What this document is not

- **Not a certification, and not evidence of one.** Not NIST-approved, not
  NIST-certified, not the official NIST tool, not a customised version of
  SP 800-90B.
- **Not a review.** It is written by the author of the repairs it describes.
  Every entry in A and B says what it does not establish for that reason.
- **Not the defect record.** The record is `audits/`, and in particular
  `audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md` (90 entries at
  `11207ca`) and `audits/2026-09-30/FINDINGS-TRACKER.md`. This document selects
  the entries that bear on **divergence and trust** and will omit defects that
  do not.
- **Not the instrument record.** Defects in this project's own verification
  tools are a third category, and a large one — but they are not divergence
  from upstream, so they are not filed here. They are in the orchestrator
  record, and §5 item 6 and section C exist so that a reader of this document
  cannot miss that they exist.
- **Not a statement about any physical device.** Section C.
- **Not a scope boundary.** `INDEPENDENT-REVIEW-BOUNDARY.md` is that.
- **Not a decision about TruePad.** The JSON in §5 is quoted, not set. No
  change to the consuming project is made from this repository.
