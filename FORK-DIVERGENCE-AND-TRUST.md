# Fork divergence and external trust

**Measured at commit `34ceb59`, 2026-10-25.** Every count in this document
names the commit and date it was taken at. Reproduce them with
`sh tools/measure-divergence.sh`; `cpp/selftest/regression-docs.sh` re-runs that
script and fails if the figures below disagree with it.

Supersedes the version dated 2026-10-09. **Seven statements in that version are
false, not merely out of date** — they are listed and corrected as false in §0,
because a reader who met them would have drawn a wrong conclusion, and
"superseded" does not say that.

**Revised 2026-10-25, after the external-validation campaign.** What changed:
**§2** is new and leads with the first evidence in this repository that does not
originate with the author of the code; **section D** is new, for differences
that are neither a code defect nor a standard defect; **`C-0`** is new and is
now the most important limitation in the document; **§4** names what is still
open; and §0 records the one statement this sweep found **false** as against the
several that were merely stale. **Read §2 and `C-0` together** — the first is the
strongest thing that can be said for this tool and the second is the strongest
thing that must be said against relying on it alone. Neither is complete without
the other.

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
| **D** | [Characterized differences](#d--characterized-differences-that-are-nobody-s-defect) | NIST's code and the publication differ, **and NIST's choice is correct or conservative** — so there is nothing to repair on either side |
| **C** | [What none of this establishes](#c--what-none-of-this-establishes) | claims no software estimator can produce, whatever it computes |

**Why D exists, added 2026-10-25.** `OC-108` checked this fork against another
implementation's documented list of intentional divergences and found items that
fit none of A, B or C: places where NIST's code departs from the publication's
text **and the code is right**, or where it takes the conservative branch of an
ambiguity. Filing those in A would call them defects in the implementation;
filing them in B would call them defects in the standard. **Both readings are
wrong, and conflating them is how a reader is misled** — a mistake this project
has already made once in its own advice. They get their own section, and every
entry there says explicitly that it is **not a repair**.

**A, B and D never share an entry, and an entry never drifts between them.** The
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
| **5** | the whole **quantified divergence** block: *"Fork repair branch: `repair/2026-10-09-verified-defects`… commit `9556649`… 66 commits ahead… 658 changed paths, 62,252 added text lines"* | **False as a description of this fork.** That branch was merged into `master` at `d226f18` on 2026-10-15 and no longer exists as a separate head. Measured at `11207ca`, 2026-10-25: **179 commits ahead, 0 behind, 1,033 text files, 108,859 insertions, 461 deletions.** (Those are the figures as of the commit named; §1 carries the current ones.) Every figure in that block was off by more than a factor of 1.5, and none of them said when it had been taken. |
| **6** | route item 7: *"Validate Linux and Windows before claiming support for those platforms"* | **False as a pending action.** Both are measured, by CI rather than by acquiring machines: x86-64 Linux on every push since 2026-10-19, Windows MinGW on 2026-10-20. What remains is not validation but **independent** validation — which §5 Decision 2 records as permanently declined, so nothing remains as a pending action at all. |
| **7** | route item 8: *"Submit generally applicable repairs upstream where practical"*, and *"Upstream acceptance would improve maintainability and external confidence"* | **Contradicts a standing decision, and was never a mere omission.** The owner decided on 2026-10-15 that **nothing is reported upstream**. The route list described a route the project has declined to take, which is worse than not listing it: a reader would have treated the absence of upstream reports as neglect rather than as policy. §5 states that decision and its consequences instead — and the first rewrite of §5 then made the same mistake with a different route, which §5 now records. |

**On item 7's framing.** Replies on this fork's upstream issues and pull
requests came from `@joshuaehill`, who is not a NIST account and who deferred
to "the NIST folks" on PR #268. No statement anywhere in this repository should
be read as NIST having reviewed, accepted or commented on anything here.

### The 2026-10-25 sweep: what was removed, and the difference that matters

Every statement was re-checked at `34ceb59`. **One was false; the rest were
stale-but-dated, which is not the same thing and must not be reported as if it
were.**

**FALSE, and corrected:** *"Binary reference artefacts | 2"*. It was true when
written at `11207ca`, became **false at `a9a269f`** when 34 generated streams
were committed into a directory named `--help`, and is true again at `34ceb59`
now that they are removed. **It was caught by
`tools/measure-divergence.sh` reporting `binary files=36` against the recorded
2** — the enforcement this document added for an unrelated reason, catching its
own author. Filed as `F15` in A.2.

**STALE BUT NEVER FALSE:** every count in §1 — the suite's 24 checks and 22
scripts, 74 live instruments, 91 orchestrator records, 2 register entries, 179
commits ahead and the divergence table. **Each named the commit and date it was
taken at, so each was a true statement about that commit and remains one.** They
are *updated*, not corrected, and they are deliberately not listed in the table
above: putting them there would dilute the word "false" to mean "out of date",
which is exactly the conflation §0 exists to refuse. **The mechanism worked** —
`regression-docs.sh` failed on the first edit of this rewrite because the
evidence insertion count had moved by 23 lines between two commits, and would
not pass until the figure matched.

**NO SURVIVING RECOMMENDATION TO SUBMIT ANYTHING UPSTREAM.** Swept at
`34ceb59`: the only remaining mentions of upstream are the policy statements in
§5 Decision 1 and the corrections in §0 items 6 and 7. **That decision is final
and this document does not carry a route to it.**

**Nothing was removed as merely inconvenient.** Sections A.1, A.2, B and C's
existing entries are unchanged by this pass except for the additions named in
§4.

---

## §1 — Quantified divergence

Measured at `11207ca`, **2026-10-25**, against upstream base
`87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289` (2026-05-26), which is the common
ancestor. The fork is **0 commits behind**, so `base..HEAD` is the whole
divergence.

| Category | Files | Insertions | Deletions |
|---|---:|---:|---:|
| Production C++ and build | 21 | 2,337 | 450 |
| Self-tests and regression harness | 53 | 7,951 | 7 |
| CI workflows and scripts | 4 | 1,467 | — |
| Audit and repair evidence | 951 | 99,218 | — |
| Other documentation | 8 | 2,270 | 4 |
| **total (text)** | **1,037** | **113,243** | **461** |
| Binary reference artefacts | 2 | — | — |

**197 commits ahead.** The headline is dominated by evidence: 88 % of the
insertions are audit and repair records. **The executable delta is 2,787 lines
of churn across 21 files** — not a cosmetic fork, and not a rewrite of the
estimators.

**That binary count read 36 four commits ago, and the discrepancy was a
defect.** `blindspot_streams.py` takes `sys.argv[1]` as its output directory
with no option handling, so running it with `--help` to discover its interface
created a directory literally named `--help` and wrote 34 generated streams,
33 MB, into it; a blanket `git add -A` committed them at `a9a269f`. Removed, and
the generator now refuses an option-shaped output directory. **The figure that
caught it is one this document added for an unrelated reason** — which is the
case for keeping counts that name their commit.

Two other counts, because they bear on how much of the above is *checked*
rather than merely written:

| | count | measured at |
|---|---:|---|
| enforced suite | **25** checks, **23** regression scripts | `34ceb59`, 2026-10-25 |
| instruments that a sweep must cover | **77** live, **79** frozen | `34ceb59`, 2026-10-25 (`audits/INSTRUMENT-INVENTORY.md`, enforced against its enumerator) |
| orchestrator records | **113** entries | `34ceb59`, 2026-10-25 |
| register entries, withdrawn or superseded | **7** (2 `WV-`, 5 `SV-`) | `audits/WITHDRAWN-VERIFICATIONS.md` |

**None of these is a measure of correctness.** A suite of 25 checks that all
pass establishes what `cpp/selftest/WHAT-A-GREEN-SUITE-ESTABLISHES.md` says it
establishes and nothing beyond it, and that document exists because the number
on its own invites the opposite reading. **The external validation in §2 is a
different kind of statement, and it is the only one here that does not
originate with the author of the code.**

---

## §2 — External validation: the strongest statement in this repository

**Everything else in this document is the author of the code reporting on the
code. This section is not, and it is placed before the defect sections because
it is the better answer to "should I trust this fork".**

### Against NIST's own published reference outputs

`tools/compare-nist-reference.sh` performs `selftest`'s own loop — the same
fixture list, the same `ea_non_iid -vv`, the same `compareresults.pl` — and
reports the per-dataset value count and worst delta that `selftest` discards.

| platform | datasets | values compared | result | worst delta |
|---|---|---:|---|---|
| **Linux x86-64 glibc** — the platform NIST produced its reference data on | 11 | **891** | **11 agreeing, 0 disagreeing** | **1.00808250635964e-13** |
| Darwin arm64 | 11 | **891** | 9 agreeing, 2 disagreeing | **3.65934130219792e-10** |

The 8 differing rows on Darwin arm64 are **exactly** those in
`cpp/selftest/known-platform-deltas.txt`, inside its `1e-9` tolerance, and all
8 are in **prediction estimators**. Linux x86-64 has deliberately no block in
that file, so its 11-of-11 is unexcused agreement. (`OC-107`, `OC-113`; CI run
40249281414, step 5e, gated on `datasets run: 11` **and** `disagreeing: 0`
separately so a loop that stopped early cannot pass as agreement.)

**EVERY PRIOR SELFTEST PASS IN THIS REPOSITORY'S HISTORY IS UNVERIFIED, AND
THESE TWO RUNS REPLACE IT.** Until `OC-73`/`OC-74`, `compareresults.pl` did not
compare the two **identity** lines of the reports it read, so it had no way to
tell that the output came from the same input, at the same sample count, at the
same symbol width, as the reference. Measured: a copy of `refdata/normal.res`
rewritten to claim `SOME-OTHER-FILE.bin` and *"42 samples of 3 distinct 2-bit
symbols"* compared **equal** to `normal.bin`'s real output — 1,000,000 samples,
179 distinct 8-bit symbols — reporting *"Maximum delta: 6.93e-15"*, 98 values
compared, **exit 0**. The identity lines **matched on all 11 datasets on both
platforms** in the runs above, which is the first time that has been true of a
comparator that checks which file it read.

**And the first run of this very check was wrong.** It omitted
`EA_ALLOW_SHORT_DATASET`, which `selftest` sets at its line 23 so the three
10,000-sample datasets can run against this fork's §3.1.1 minimum enforcement,
and it would have reported **three of eleven reference datasets as
disagreeing**. The three rows that use that escape are marked in the output as
**not a compliant assessment**. A check that nearly produced the alarm it was
built to detect belongs in the record beside its result.

### Against two independent implementations

Two other SP 800-90B implementations were built and run as **separate
binaries** — never vendored, no code copied, no license question. The Rust one
links `MPFR`, which this fork deliberately does not; running it out of process
is what preserves that property.

| implementation | identity | build |
|---|---|---|
| `walters-labs/sp-800-90b` | `ef6fd02`, v0.1.1 | `cargo --release`, 256-bit MPFR via `rug` |
| `EPI-Quantum-Crypto/libsp80090b` | `2429253`, C99 port of NIST 1.1.8 | `gcc-16 -std=c99 -O2 -ffloat-store`, portable `MARCH=` |

| corpus | rows compared | exceeding `1e-9` | worst |
|---|---:|---:|---:|
| NIST's 11 reference datasets | **891** | **0** | 3.659e-10 |
| this fork's outside-battery corpus, 5 streams | **295** | **0** | 6.217e-14 |
| 5 deliberately degenerate defect datasets | **503** | **10** | 4.165e-09 |
| **total** | **1,689** | **10** | |

Of 163 three-way rows on the reference datasets, **64 agree exactly**; of 728
rows this fork shares with the C99 port, **719 are bit-identical**.

**The 10 disagreements, all on degenerate inputs:**

- **6** where the **Rust** implementation is the outlier and this fork equals
  the C99 port **exactly** — 256-bit MPFR against binary64, which that project
  documents.
- **2** where **this fork** is the outlier — `saturated.bin`, Bitstring MultiMCW
  and Bitstring Lag min-entropy. See §4.
- **2** two-way only, because the Rust CLI keeps `P_local` API-only; their
  outlier column is empty by construction, not by agreement.

**All 10 are smaller than `C22a`.** The floor's measured `P_local` quantisation
term is `8.08e-15 x (n+1)` — **8.080e-09** bit at n = 1e6, **6.464e-08** at
n = 8e6 — against a worst disagreement of **4.165e-09**. So **no figure this
project publishes moves.**

**This does not upgrade `C22a`.** It is consistent with `C22a` being the right
*order of magnitude* and it is not a bound. `C22a` remains **MEASURED, not
PROVED**, and `WV-2`'s withdrawal of the supremacy claim **stands withdrawn**.
A reader must not infer from this section an upgrade that did not happen.

### What §2 does not establish

- **It is agreement, not correctness.** Three implementations of the same
  standard agreeing establishes that they implement the same standard. Where
  the standard is wrong — section B, and `D-3` — all three are wrong together.
- **`ea_non_iid` only.** The IID, restart and conditioning reference paths are
  not compared this way.
- The three-way runs were all on **one machine**. §2's platform conclusion
  rests on the two-platform reference comparison and on `OC-112`, not on the
  three-way alone.
- **Nothing was reported to NIST or to either project.**

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

#### `F15` — 33 MB of generated streams committed into a directory named `--help`

- **DEFECT.** `audits/2026-10-11-independent-audit/generators/blindspot_streams.py` took `sys.argv[1]` as
  its output directory with **no option handling**, so
  `blindspot_streams.py --help` — the obvious way to discover the interface, and
  what was run while probing it for `OC-114` — **created a directory literally
  named `--help`** and wrote 34 generated streams, **33 MB**, into it. A blanket
  `git add -A` committed all 34 at `a9a269f` and pushed them. Nothing referenced
  them; `cpp/selftest/outside-battery-corpus.txt` exists precisely so those
  streams are **regenerated from seeds** rather than stored.
- **ORIGIN.** **INTRODUCED BY THIS FORK**, by this campaign, four commits before
  it was found. The generator's missing option handling is older; the commit is
  mine.
- **EVIDENCE.** **EXECUTED.** Found by `tools/measure-divergence.sh` reporting
  `binary files=36` against this document's recorded **2** — a figure added for
  an unrelated reason, which is the argument for keeping counts that name their
  commit. Both states then observed directly: the pre-repair generator at
  `a9a269f` run as `--help mt00` exits 0 and **creates `--help/`**; the repaired
  one prints the usage and creates nothing.
- **STATUS.** **REPAIRED** (`34ceb59`). The 34 files are removed; **the blobs
  remain in history at `a9a269f` and history was not rewritten**, because the
  record should show that this happened. The generator now prints usage for
  `-h`/`--help`/`-help`/`--usage`, **refuses by name** any other output
  directory beginning with `-` — this script has no options, so an
  option-shaped operand is a mistake every time — and refuses unknown stream
  names instead of silently producing nothing. Verified in both directions:
  `-o` refused, 0 created; `./real mt00` still writes its file.
- **DOES NOT ESTABLISH.** That no other probe in this campaign had a side
  effect. This one was caught by a count that happened to cover it; **no sweep
  for probe side effects has been run**, and the four earlier self-introduced
  defects were each found by a different accident. A probe must not be able to
  create the thing it asks about, and only this one generator has been made to
  obey that.


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

## D — Characterized differences that are nobody's defect

**NIST's code and the publication's text differ, and NIST's code is correct or
takes the conservative branch.** Nothing here is repaired, nothing here should
be, and **no entry in this section is a repair** — each states what was
characterized and stops.

Four of these came from `OC-108`, which checked this fork against the Rust
implementation's own published list of intentional divergences from NIST. **That
list found 0 defects in this fork.** Four findings already in this record were
reached independently by a different team in a different language, which is
**the first external support any finding in this repository has had** — and on
one, `D-4`, the two projects reached **opposite** conclusions and both
documented theirs as deliberate.

#### `D-1` — the MCV confidence constant: binary64 against the publication's decimal

- **WHAT DIFFERS.** `cpp/shared/utils.h:75` defines
  `ZALPHA 2.5758293035489008`, the exact 0.995 standard-normal quantile in
  binary64, where SP 800-90B's text prints the rounded decimal **`2.576`**. The
  two give different results.
- **WHO IS RIGHT.** **NIST's code.** `2.576` is a *rounded printing* of the true
  quantile, so the implementation uses the correct number and the standard's
  text uses the rounding. **Not a defect in either**, and dispositioned
  NOT-A-BUG on exactly that reasoning (`F07`, `OC-8`).
- **MEASURED, on values harvested from a real run** rather than from a model of
  one — the recomputation of `P_global'` from the published `P_global` and `N`
  reproduces the tool's own printed value exactly on all three predictors:

  | predictor | with `ZALPHA` | with `2.576` | delta |
  |---|---|---|---|
  | Bitstring MultiMCW | 0.99911507785502614 | 0.99911499084098192 | **+8.70e-08** bit |
  | Literal MultiMCW | 7.9611632356166352 | 7.9611594334062937 | **+3.80e-06** bit |
  | Bitstring Lag | 0.998936306150716 | 0.99893621914778806 | **+8.70e-08** bit |

- **DIRECTION.** Permissive — the code's constant yields the **higher** estimate.
  The worst delta sits at the sixth decimal of a figure printed to 17
  significant digits, i.e. **far above** the printed precision floor and
  7.6e-06 relative against the project's 0.5 bit-per-bit threshold.
- **CORROBORATED.** The Rust implementation offers both constants and its
  **default is the binary64 one** — the same conclusion, reached independently.
- **NOT A REPAIR.** No change was made and none is recommended. The constant is
  also carried as the `C22c` floor term, where it is a *bound on the difference*
  rather than a correction to the constant; see `B`.

#### `D-2` — the Collision estimator clamps the adjusted mean to 2, where the publication would fall back

- **WHAT DIFFERS.** `cpp/non_iid/collision_test.h:69` is
  `if(X < 2.0) X = 2.0;` — carrying upstream's own comment *"2 is the smallest
  meaninful value here"* — and then solves on `[2, 2.5]`. SP 800-90B §6.3.2
  step 7 instead prescribes a **no-solution fallback** for a bound outside the
  solvable range.
- **WHICH WAY IT GOES, worked out because it decides whether it matters.** The
  solvable window gives entropy in `[0, 1]`:
  - **NIST's clamp:** `X < 2` becomes `X = 2`, so
    `p = 0.5 + sqrt(1.25 - 1.0) = 1.0` and `entEst = -log2(1.0) = ` **0 bits**.
  - **The publication's fallback:** `p = 0.5`, `entEst = ` **1 bit**.
- **SO THE CLAMP IS THE CONSERVATIVE BRANCH** — it awards **zero** entropy where
  conforming to the text would award a full bit. For an entropy *claim*, lower
  is safe. This is the rare entry in this document whose direction is the
  favourable one.
- **IT IS NOT `R-1`, AND NOT THE `C22` FLOOR.** `R-1` is the
  `assert(p_col >= 1/k)` / `p_colPower` underflow **abort** in
  `cpp/shared/lrs_test.h` on 80-bit `long double` — a crash on compliant data,
  found by five independent finders, 155 of 255 alphabet sizes on x86-64.
  Different file, different quantity, different failure mode. `C22` is
  `P_local`'s bisection quantisation. **The three share only the word "clamp"**,
  and conflating them would be the error this section exists to prevent.
- **EVIDENCE.** **SOURCE-CONFIRMED** and **DERIVED** — the direction is
  arithmetic on the published formula, not a run. Labelled as such.
- **NOT A REPAIR.** Nothing changed.

#### `D-3` — the Markov six-pattern table is not a minimum over all 128-step paths

- **WHAT DIFFERS.** `cpp/non_iid/markov_test.h` evaluates exactly the **six**
  candidate sequences §6.3.3 prescribes, in the standard's order —
  `-log2(P_0) - 127*log2(P_00)`, `-log2(P_0) - 64*log2(P_01) - 63*log2(P_10)`,
  and four more — then `entEst = fmin(H_min/128.0, 1.0)`. **That is exactly
  conformant.** The characterization is that six prescribed patterns are **not**
  the minimum over all 128-step Markov paths, so the published "Markov
  min-entropy" can exceed the true minimum over that model.
- **WHOSE IT IS.** The **standard's**, not the implementation's — which is why a
  reader might expect it in B. It sits here because there is nothing to diverge
  from: conforming is correct, and the limitation is a property of what §6.3.3
  asks for.
- **PROBABLY IMMATERIAL HERE, AND THE REASON IS MEASURED.** Compression binds on
  every stream this project has assessed, and the aggregation measurement found
  that a **40-sigma** defect in a non-binding estimator leaves the min-entropy
  figure unchanged. Markov has never bound.
- **EVIDENCE.** **SOURCE-CONFIRMED**, against the 2026-09-30 audit's
  verification of the six paths as conformant.
- **NOT A REPAIR**, and **not a candidate for one** — repairing it would mean
  departing from §6.3.3.

#### `D-4` — MultiMMC's run counter: the one place two implementations chose oppositely

- **WHAT DIFFERS.** §6.3.9 step 1 initialises `correct[]` to 0 and step 4.d sets
  `correct[i-2] = 1` only when the prediction equals the sample, so a **Null**
  prediction leaves it 0 — and the section's own **worked example** shows
  `prediction = Null, correct = 0` for its first two rounds. NIST's code reset
  the run counter only where the winner predicted and was **wrong**, so a Null
  from the winner carried the run straight across it.
- **WHAT THIS FORK DID.** **Repaired it** (`F09`), guarded by
  `cpp/selftest/regression-multimmc.sh`, which cites the worked example as its
  authority. Direction: the defect inflated `r`, which makes `P_local` larger
  and the estimate **smaller** — so it was **conservative**, and the repair
  raises estimates slightly.
- **WHAT THE OTHER IMPLEMENTATION DID.** **Deliberately preserved it**, for
  reference compatibility, with a targeted test demonstrating the difference.
- **SO THIS IS A GENUINE DIVERGENCE, DOCUMENTED AS INTENTIONAL ON BOTH SIDES.**
  It is listed here rather than in A because the *characterization* — that the
  quirk is real and that §6.3.9's worked example contradicts it — is
  independently corroborated, while the *choice* of remedy is a judgement two
  projects made differently. **The repair itself is recorded in A.1.**
- **NOT A REPAIR in this section**; `A.1` carries the repair.

#### `D-5` — the restart path after an IID rejection

- **WHAT DIFFERS.** The Rust project records that NIST's reference *"can reach
  its final validation-success message after printing IID failures"*.
- **WHAT THIS FORK DOES.** Closes it: `cpp/restart_main.cpp:1139` skips the
  permutation tests after an earlier required IID failure, and `:1155` awards
  **no IID restart entropy estimate**. In the `C03` neighbourhood (`OC-6`).
- **CORROBORATED, AND ALREADY FIXED HERE.** Listed in D because the finding was
  reached independently; the repair is in `A`.
- **NOT A REPAIR in this section.**

#### `D-6` — out-of-width values are rejected rather than masked

- **WHAT DIFFERS.** Nothing, between this fork and the Rust implementation —
  both **refuse** a sample that does not fit its declared width rather than
  masking it. Measured here: byte-valued data declared width 1 prints
  *"Incorrect bit width specification: Data (8) does not fit within described
  bit width: 1"* and exits 255.
- **WHY IT IS RECORDED.** Because it is the one item on their list where the two
  projects **agree without having coordinated**, and an agreement is as much a
  result as a divergence.
- **NOT A REPAIR.**


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

### C-0 — THE MOST IMPORTANT LIMITATION IN THIS DOCUMENT: the assessment cannot tell a noise source from a generator

**Measured 2026-10-25 (`OC-109`), on 1,000,000 samples at width 8:**

**AES-256-CTR under an all-zero key** — a stream whose entropy is **exactly
zero**, being a deterministic function of nothing — is assessed by this fork at

> **7.1449938481907544 of 8 bits, exit 0, `errorLevel 0`.**

All three independent implementations agree on the binding estimator (Bitstring
Compression) to **3.0e-14**. `/dev/urandom` gets 7.17; OpenSSL's CSPRNG gets
6.64.

**Why, stated as a property and not as a fault.** SP 800-90B §6.3 measures
**statistical structure**. It does not measure **computational
unpredictability**, and no estimator in §6.3 could distinguish AES-CTR output
from physical noise without breaking AES. **This is not a defect in this fork
and not a defect in NIST's tool: it applies to NIST's reference implementation
exactly as much as to this one, and to every conforming implementation.** It is
the reason the standard requires raw, unconditioned samples.

**The consequence, which is this document's job to state.** **No estimator in
this tool, repaired or not, can distinguish a raw noise source from a
conditioned or generated stream. A favourable assessment therefore establishes
nothing whatever about a source whose provenance is not independently
established.** The figure is only as meaningful as the evidence that the bytes
came off the physical source before any conditioning — and that evidence is not
something this tool can supply.

**And a threshold on the assessed rate cannot rescue it.** Five conditioned
streams were measured, and the span is stated as measured rather than rounded:

| stream | assessed | width | bits per bit |
|---|---|--:|---:|
| `openssl` | 6.6384051555787362 | 8 | **0.82980** |
| `urandom-1bit` | 0.83110942028961665 | 1 | 0.83111 |
| `drbg-zero-seed` | 7.1449938481907544 | 8 | 0.89312 |
| `urandom` | 7.1724559457456492 | 8 | 0.89656 |
| `urandom-4bit` | 3.6877536942326419 | 4 | **0.92194** |

**The measured span is 0.82980 to 0.92194 bits per bit** — a band 0.09 wide,
which already overlaps what a plausible raw source could report. Worse, the
lower end of it is not even a property of conditioning: the OpenSSL stream
assessed at 0.82980 only because its Literal Lag `P_local` bound, and **the
cause was a single integer** —

| stream | `C` | `r` | `P_global'` | `P_local` | min entropy |
|---|---:|---:|---|---|---|
| the measured OpenSSL stream | 3946 | **4** | 0.0041075 | **0.010038** | **6.6384** |
| a fresh stream, same command | 4007 | **3** | 0.0041697 | *did not bind* | **7.9058** |

Four fresh `openssl rand` streams from the identical command all gave Literal
Lag ≈ 7.91–7.95 and none of them bound on it. **The longest run of correct lag
predictions differed by one — `r = 4` against `r = 3` — and that single
increment moved the estimate by 1.27 bits.** `P_local` is a step function of a
max-of-runs statistic with a heavy tail, so an individual capture's assessed
rate carries more than a bit of noise from one integer. **A ceiling on bits per
bit cannot be stable against that**, and the band it would have to sit outside
is not even well defined.

**What does defend against it: provenance, and nothing else in this
repository.** See `audits/` for what the record carries; the qualification
procedure that must bind provenance to the capture is not this document's
subject.

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

---

## §4 — What is still open, named

**Every item here is open as of `34ceb59`, 2026-10-25.** An open item with no
name is an open item nobody tracks.

### The strongest open candidate the campaign produced

**Bitstring MultiMCW `P_local`, and the min-entropy derived from it.**
Implicated by **two independent routes**, which is why it ranks above everything
else open:

1. **It is one of the 2 rows of `known-platform-deltas.txt`'s 8 that an
   independent implementation does NOT reproduce.** `OC-112` ran the C99 port
   against NIST's own refdata on Darwin arm64 using this fork's comparator: **5
   of the 8 rows came back bit-identical to every printed digit**, which is
   strong evidence those 5 are a platform property. Bitstring MultiMCW `P_local`
   and its min entropy are **not** among the 5 — there, this fork differs from
   NIST and the C99 port does not.
2. **It is one of the 2 rows where this fork is the outlier three ways.**
   `OC-111`, on `saturated.bin`: Bitstring MultiMCW min-entropy, delta
   **2.305e-09**, with this fork low against a C99 and a Rust value that agree
   closely with each other.

**What is known:** it is **arm64-only** — the fork agrees with NIST on x86-64 to
1.01e-13 (§2), and `biased-random-bytes`'s worst delta falls from 3.66e-10 on
arm64 to **4.24e-14** on x86-64, a factor of 8,600. It is **sub-nanobit**, and
smaller than `C22a`. It is in a quantity computed by **bisection**, which is the
known-fragile one.

**What is NOT known:** which of the three is arithmetically closer to §6.3.7's
definition. That needs an independent high-precision computation of `P_local` on
that input, and **it has not been done**. The item is **located, twice, and
unresolved.**

### Queued, not repaired

- **`C22c`'s two copies.** `audits/2026-10-11-independent-audit/oracles/entropy_floor.py:188` holds the
  live table whose `max()` the published floor subtracts;
  `compression_ceiling_exact.py:215` holds **its own separate copy** and
  verifies *that* against NIST's worked example. Mutating the floor's copy
  `3.3599e-3 -> 3.3700e-3` leaves `oracle-selftest` **passing** (`OC-105`). The
  independent verification is real, correct, and verifies a different copy of
  the number than the one in use. **Two copies, one checked.** The fix is to
  wire them together and verify by breaking; it is not done.
- **`OC-67`'s per-family denominator** and **`mutation-lib`'s own
  `MUTATION-DID-NOT-APPLY` contract**, both also `NOT CAUGHT` by mutation in
  `OC-105`. The second is the mechanism adopted to stop this project reporting
  unearned verdicts, and it is the one mechanism with no case in which it fires.
- **`deadguard.py` reports `flags: 0` over an empty scan.** Run with `SP=.` it
  prints `files touched: 0` and the tree hash of the **empty string**
  (`e3b0c442...`) — `SHAPE-03` in the instrument built to find `SHAPE-03`. The
  suite is immune because `OC-95` made the provenance line a precondition; a
  human running it by hand is not.

### Open because it stopped reproducing without being understood

- **The Linux `regression-docs` failure.** It **did not reproduce** in the
  8e6941f run — `regression-docs: PASS` both inside the suite and in its own
  gated log — and it is therefore **still open, not closed**, with its four
  dead hypotheses recorded. A defect that stopped reproducing without being
  understood stays open.

### NOT RUN, and staying that way until the physical prerequisite exists

- **`binary128` on Linux aarch64.** No such host is available. **NOT RUN.**
- **`jent-raw` and `jent-restart`** of `OC-109`'s defect corpus need a
  `jitterentropy-library` checkout. **NOT RUN.**
- **The three-way differential on x86-64.** All three implementations were built
  and run on one machine; §2's platform conclusion rests on the two-platform
  reference comparison and on `OC-112`, not on a three-way x86-64 run. **NOT
  RUN.**

### The repair-interaction backlog, with its measured bands

`OC-94` found **94** pairs where a later repair deleted or rewrote a non-comment
line an earlier repair added, **29 declared**, leaving **65 undeclared**;
re-measured at `OC-100` as **66**, four commits having landed since. Banded:

| band | both facts | count |
|---|---|---:|
| **1** | the later repair rewrote the earlier one's lines **and** either reaches a figure | **27** |
| **2** | reaches a claim rather than a figure | **39** |

Band 1 collapses to **15 distinct earlier mechanisms**. `OC-105` mutated **9**
of those 15: **4 CAUGHT, 4 NOT CAUGHT, 1 control-failed**. **6 of the 15 were
not mutated at all** — the three canary entries, the two `C23` entries,
`210aed6`, and `5c3353f`, which has **no runnable case** — so the unguarded
count is a **floor, not a total**. **Band 2's 39 pairs are not examined.**


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
4. **What a date cannot police is marked instead.** Statuses in sections A, B
   and D are claims about the tree, so they carry the record entry that
   established them (`OC-nn`, `WV-n`, `SV-n`); a reader who doubts one reads
   that entry rather than trusting this summary.
5. **A figure that is true at its commit and false later is still false
   later**, and the 2026-10-25 sweep is the worked example: the binary-artefact
   count was true at `11207ca`, false at `a9a269f`, and true again at
   `34ceb59` — caught by the re-measurement in point 3, not by reading. **A
   count that names its commit is auditable; it is not self-correcting.** The
   distinction between *false* and *stale-but-dated* is drawn explicitly in §0,
   because collapsing it would make "false" mean "old".
6. **A superseded figure is kept with its correction, as false.** §0 is the
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
