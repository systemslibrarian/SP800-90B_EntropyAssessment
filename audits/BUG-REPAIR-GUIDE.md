# Bug repair guide

This guide explains how to work through the defect queue in [`2026-09-30/FINDINGS-TRACKER.md`](2026-09-30/FINDINGS-TRACKER.md), whether you are a person or a coding agent. That tracker is the canonical list of confirmed defects in this fork's copy of `usnistgov/SP800-90B_EntropyAssessment`, and the only place their state is recorded.

The goal is not to file issues; it is to get every confirmed defect **technically resolved**. A defect is resolved only when:

- **(A)** the upstream code is actually corrected and the finding's regression test passes against it, or
- **(B)** this fork contains the correction and a regression test proving it.

A closed, rejected, abandoned or stale upstream issue is **not** a resolution. If upstream closes a confirmed bug without fixing it, the finding becomes `FORK-FIX-REQUIRED`.

## Ground rules

1. **Never delete a finding** from the tracker. Change its state and record why.
2. **Do not edit the historical record.** `2026-09-30/AUDIT.md`, the two `REPORT.md` files, and everything under `novel-findings/` and `phase2-focused/` are evidence as captured on 2026-09-30. Only `FINDINGS-TRACKER.md` (and this guide) are living documents.
3. **One finding per commit.** Two findings may share a commit only when one code change fixes both (a shared root cause); name both IDs in the message. Candidate shared causes:
   - F19 + N-07: hash the loaded buffer.
   - F03 + F05: JSON warnings for a degraded run.
   - F18 + N-06: `sha256_file()` hardening.
   - F15 + N-03: intake length validation.
4. **Reproduce before fixing** and **test after fixing**. A fix without a regression test does not count as resolved.
5. **Do not change `cpp/selftest/refdata/`** to make a test pass. The exception is a fix that intentionally changes a reported figure: then regenerate only the affected files and explain the change in the commit.
6. **Do not act upstream without the owner's explicit approval.** That means no pushing to `usnistgov`, and no opening, closing or commenting on upstream issues or PRs. Push only to this fork, never with `--force`.
7. **Keep the numbers honest.** Record measured outputs, not expected ones. If a reproduction does not show the stated failure, do not "fix" it: record that in the tracker and stop.

## Two standing facts about this queue (recorded 2026-10-02)

**"Already known upstream" is no longer a reason to leave a defect out.** The
2026-09-30 audits excluded defects that upstream already knew about, recording
them as rediscoveries rather than queueing them. That was sound while master
was pinned to upstream behaviour: an upstream defect was not this fork's to
answer. It stopped being sound on 2026-09-30, when master became the patched
build and that build became a product dependency, and nothing recorded the
change until now. If you find a defect in this fork's shipped programs,
upstream knowing about it is a fact to record, not grounds for omitting it.
One such defect is carried today: the scalar `delete` of an array at
`cpp/restart_main.cpp` lines 124 and 161, in `ea_restart`, which this fork
builds and ships. It has no tracker row of its own, no repair and no
regression; `../NOTICE` describes it under "Known upstream defects carried into
the shipped build".

**There is no CI. Every check in step 6 and step 7 is manual.** No workflow,
no pipeline, no commit hook exists in this repository. A green suite means
someone ran it once, on one machine, at a moment you cannot recover from the
history. Nothing runs it for you, nothing records which commits it was run
against, and nothing will tell you if a later commit breaks it. Run it
yourself, and say in the commit message what you ran and on what.

## Setup

```sh
git clone https://github.com/systemslibrarian/SP800-90B_EntropyAssessment.git && cd SP800-90B_EntropyAssessment
git remote add upstream https://github.com/usnistgov/SP800-90B_EntropyAssessment.git
git fetch upstream
cd cpp && make                 # supported targets only; see BUILDING.md (no MPFR/GMP required)
cd selftest && ./selftest      # baseline; compare the "Assessed min entropy" lines too (NOVEL-01)
./pin-check.sh                 # pinned figure on real noise (bin/ringOsc-nist.bin)
```

The fork's C++ sources were identical to upstream `87c104d` when this guide was written. They no longer are: two repair passes on 2026-09-30 corrected defects in `cpp/shared/`, `cpp/non_iid/`, `cpp/iid/` and the `*_main.cpp` programs. Each change is listed in [`../NOTICE`](../NOTICE) with its upstream issue and commit, and every repaired finding below records its commit. Line references in older findings may therefore be a few lines out; the surrounding code is still recognisable. No unintended numerical change was observed on the datasets tested, and `cpp/selftest/refdata/` is untouched and still reproduced exactly; two changes alter results on purpose (F09 raises the MultiMMC estimate where its defect bit, and N-01 makes an m = 1 chi-square test fail), both described in [`../NOTICE`](../NOTICE). All tracker commands run from `cpp/`. The generators they call live under `audits/2026-09-30/`.

## Selecting work

Take findings whose **State** is:

- `FIXED-UPSTREAM-VERIFY`: verify first; this is usually the cheapest work.
- `FORK-FIX-REQUIRED`: upstream will not fix it; the fork must.
- `NEEDS-FIX`: everything else confirmed. Prefer rows marked "yes" in **Dangerous direction?** (the figure can come out too high or IID can be wrongly accepted), then memory safety, then report integrity, then cosmetics.

`UPSTREAM-FIX-PENDING` rows are not in the queue; only their status is checked (see below). `NOT-A-BUG` and `UNCONFIRMED` rows are not in the queue. An `UNCONFIRMED` item enters the queue as `NEEDS-FIX` once someone reproduces it and fills in all the fields.

`EXCLUDED-UNSUPPORTED` and `SUPPORTED-SCOPE-FIXED` rows do not authorize work
on the excluded executable. They become active before supported scope expands.
`BLOCKED-HARDWARE` is not actionable until the required architecture is
available; do not write an untestable numerical repair on a different ABI.

## Procedure for one finding

1. **Reproduce.** Run the finding's **Reproduce** block from `cpp/` on current fork `master` and confirm each `BUG:` line.
   - If it does not reproduce, investigate before anything else: build flags, platform, or an already-merged fix.
2. **Check upstream.** Run `git fetch upstream`, read the affected source on `upstream/master`, and query the issue and PR:
   ```sh
   gh issue view <N> -R usnistgov/SP800-90B_EntropyAssessment --json state,stateReason,closedAt
   gh pr view <N> -R usnistgov/SP800-90B_EntropyAssessment --json state,mergedAt,mergeCommit
   ```
3. **Decide.** Judge by the code, not the issue state.
   - **Upstream code is corrected:** build `upstream/master` and run the reproduction and regression check against it. If they pass, bring the upstream change into the fork (merge or cherry-pick) together with the regression test, and set the finding to `VERIFIED`.
   - **Upstream closed it without a fix, or has a fix only in an unmerged PR:** repair it in the fork. If upstream closed it, first set `FORK-FIX-REQUIRED`.
4. **Fix** in the fork with the smallest correct change. If a fix branch already exists (see **Current fork status**), start from it and re-check it against current `master`.
5. **Add a permanent regression test** in `cpp/selftest/`, named `regression-<topic>.sh`, using small generated inputs rather than committed binaries where possible. A test must:
   - exit 0 when the behaviour is correct and non-zero when the defect is present;
   - **be observed to fail against a known-wrong build, not reasoned to fail.** Build the mutant or check out the pre-fix commit, run the check, read the failure, and put the two numbers in the commit message. A check that has only ever been seen passing is an untested assertion that it can fail at all. Seven guards across this project and TruePad have read green while proving nothing; the tracker's "a regression is assumed vacuous until it has failed" section records them and why;
   - **compare figures against a platform-independent source**, `cpp/selftest/refdata/` with a stated tolerance, never against a literal pasted from this machine. A check carrying one platform's value is evidence about that platform: REV-005 passed on macOS and would have failed a correct Linux build;
   - use the finding's expected values with a stated tolerance where a figure is compared (see `BUILDING.md`, "Precision audit");
   - assert its own precondition where one exists, so that it cannot pass vacuously if the input stops exercising the defect.

   One script may cover several findings that share a cause, as `regression-estimator-guards.sh` and `regression-restart.sh` do; name each finding in a section comment, and record the script against every finding it covers in this tracker. `cpp/selftest/run-all-checks.sh` checks discovery against the authoritative `regression-script-inventory.txt`; adding, deleting, or renaming a script requires updating that inventory and the expected counts deliberately. Earlier versions of this guide described a `cpp/regression/` directory with a hand-maintained `run-all.sh`; it was never created.

   **A clean merge is a statement about text, not about meaning.** Any file that enumerates other files — a script inventory, a fixture manifest, an exclusion list, a pinned-file list, a digest list — will merge with **zero textual conflicts while silently losing entries**, because each side's list is internally consistent and neither side's lines overlap the other's. The 2026-10-15 merge of `repair/2026-10-09-verified-defects` had zero textual conflicts and two semantic ones of exactly this shape: the branch's `regression-script-inventory.txt` lacked master's `regression-outside-battery.sh` (would have dropped a regression script from the suite's own inventory), and its `fixture-manifest.txt` pinned six `refdata/*.res` hashes master had amended in OC-21 (would have reverted reference amendments). A merge that touches any file in the table below is not done until its enumerating files have been re-derived from the merged tree and the detector named for each has been run. Sweep of this repository, 2026-10-18:

   | file that enumerates other files | could a merge silently drop or stale an entry? | what detects it |
   |---|---|---|
   | `cpp/selftest/regression-script-inventory.txt` | **yes** — a script added on one side is absent from the other's list | `run-all-checks.sh` fails closed on `unexpected script`; `harness-inventory-mutation-test.sh` |
   | `cpp/selftest/fixture-manifest.txt` (HARNESS-AUD-01) | **yes** — a fixture or reference amended on one side keeps the other side's hash | `verify-fixture-inventory.sh` (run by `selftest` first); `regression-selftest-inventory.sh` |
   | expected counts in `run-all-checks.sh` (`EXPECTED_REGRESSION_SCRIPTS`, `EXPECTED_TOTAL_CHECKS`) and the summary string in `harness-inventory-mutation-test.sh` | **yes** — each side bumps its own count; the merge keeps one | `run-all-checks.sh` count check; the mutation test's positive control |
   | `KNOWN_PLATFORM_FILES` in `run-all-checks.sh` | yes in principle; the list is two files and has not changed | strict-mode `selftest` naming any other file |
   | `DOCS=` and `TRACKER=` lists in `regression-docs.sh` | **yes** — a document added to the claims check on one side is dropped | nothing mechanical: a dropped document silently leaves the check. Re-derive after any merge touching `regression-docs.sh` |
   | `SUPPORTED_TARGETS` in `cpp/Makefile` | yes — an executable added or removed on one side | `regression-docs.sh` inspects the forced dry-run build plan for exactly `ea_non_iid ea_iid ea_restart` |
   | `.gitignore` | yes — a pattern added on one side is lost; the symptom is an untracked or wrongly tracked artefact | nothing mechanical; `git status` after the merge |
   | `cpp/selftest/outside-battery-corpus.txt` (was inline lists in `regression-outside-battery.sh`) | **yes** — a stream added on one side is absent from the other's list | since 2026-10-18 (OC-23): per-family counts as separate expectations in the script, set equality both directions, digests; the counts are further anchored in the tool header, the generator docstring and OC-17's text, so a coordinated manifest-plus-script edit still fails; shown failing seven ways |
   | `repairs/*/MANIFEST.sha256` | sealed evidence, by design never re-derived | not applicable — a mismatch there means the evidence was edited, which is the thing it exists to catch |
   | `audits/2026-10-11-independent-audit/EXCLUSION-MAP.md` and the tracker's `EXCLUDED-UNSUPPORTED` rows | yes — prose lists of excluded items; a row added on one side is lost | `regression-docs.sh` checks the tracker's per-state counts against its sections; the exclusion map has no check |
   | `bin/` + `refdata/` as a directory pair | the pair is the thing `fixture-manifest.txt` enumerates; a file added to one directory without a manifest entry | `verify-fixture-inventory.sh` rejects extra and missing files both ways |

   **Three rules about instruments, not about code. The landing rule below is one of them, and it does not cover the other two** — recorded together so nobody later assumes one mechanisation closed all three. Each exists because this project made the mistake, and each has a negative control.

   1. **A mutation that did not land reports neither a pass nor a fail.** Mechanised in `cpp/selftest/mutation-lib.sh` (`OC-33`): file mutations prove landing by digest, value mutations by the value the code under test *received*, build-flag mutations by the binaries differing. The third outcome is `MUTATION-DID-NOT-APPLY`, which fails the harness and says the harness is broken rather than the guard. Negative control: a copy of a harness with one `mv` replaced by a no-op must report it. **Does not cover rules 2 or 3.**

   2. **A conclusion from ABSENCE requires the output to be a well-formed report of the expected kind first.** A usage message, an empty file, a crash, a timeout, and a completed run that lacks a given line are five distinguishable outcomes, and **only the last may be read as evidence about the data**. Assert a positive structural marker before reading any missing line as a fact. This is `RULE 12`'s principle moved from corpora to invocations: a corpus that is short and a tool that never ran are the same error. The instance: an `R-1` recheck declared the wrong symbol width, the tool printed its usage text, and the log recorded "no LRS line seen" as though it were a fact about the data (`OC-34`, `OC-36`).

   3. **A platform claim from reading the source is provisional until the source has been run on that platform.** The worked example is the provenance canary: `OC-24` argued from the arithmetic that all four of its signatures hold on the wide `long double` formats, and three did — while the fourth matched macOS's own wording of an assertion failure and returned a false INDETERMINATE on glibc for a legitimately unrepaired binary (`OC-40`). The *reasoning* survived contact with the platform; the *instrument* did not. A corollary: **a guard matches the thing, not the host's wording of it** — prefer a structural signal (exit status plus the predicted side effect) and treat matched text as secondary confirmation. `.github/workflows/x86-64-platform-facts.yml` runs the suite on the other format on every push, because this class is invisible from the development host by construction. **(`R-1` is NOT an instance of this rule — see rule 4. Nothing about the platform hid it; a build state did. It was filed here and the filing was wrong.)**

   4. **A measurement is about the artefact it ran against, and an artefact whose build state was not established is not evidence about the source.** Four of this project's instrument errors are this one shape, and none is a wrong idea:

      | the artefact that was not what it seemed | what it produced |
      |---|---|
      | the tag worktree's `-DNDEBUG` binary, left there by earlier canary work (`OC-42`) | a "`R-1` does not reproduce on arm64" that stood for two sessions |
      | no input files at all, from a broken hex literal in the harness's own generator (`OC-30`) | a uniform, plausible column of `REFUSED` |
      | a file whose `sed` edited the wrong line (`OC-23`) | an "unmutated" control that was the mutant's twin, and a passing run |
      | a hand **re-implementation** of two production functions instead of a call to them (`OC-41`) | a blast-radius figure that disagreed with the tool |

      Mechanised in `cpp/selftest/buildstate-lib.sh`: any harness that concludes from running a tool binary prints `[build-state] <name> asserts=LIVE|NDEBUG sha256=…` **before** its results, so a result without that line is visibly incomplete; `bs_require` declares the build a measurement needs and refuses a mismatch; `bs_canary` adds the canary's tree verdict where it applies. A measurement that deliberately uses a particular build declares which. **Covered by none of the rules above**, and rule 1's landing detector does not reach it either.

   5. **A labelled read is never a positional read.**

   4. **A labelled read is never a positional read.** Where the output carries a label, anchor to the label and make a missing label an error — never a fallback to position. Where no label exists (an `ea_iid` report's single test case), assert the count rather than taking the first of however many there are. `head -1`, `tail -1`, `[0]`, a line number, and an `awk` field position standing in for a named column are all the same defect waiting for a layout change. The instance: `entropy_floor.py` read `testCases[0]` and computed a floor from the Most Common Value estimator instead of the case labelled `Overall` — 0.983 where the answer is 0.904 — inside the script written to stop people making `C02`'s reading error (`OC-35`).

      The TruePad `verify-vectors` exclusion list that existed in two copies is the same family seen from another angle: two copies of an enumerating list cannot disagree textually and will disagree in meaning the first time one is edited.
6. **Run the tests:** `cd cpp && make non_iid iid restart && cd selftest && ./run-all-checks.sh`

   That runs `pin-check.sh`, `selftest` and every regression script, and fails if any fails. Two things to know about its output:
   - `selftest` exits non-zero on macOS arm64 for the pre-existing platform deltas in upstream #155. `./run-all-checks.sh --allow-known-platform-deltas` excuses them **only** against `cpp/selftest/known-platform-deltas.txt`, an expected-result manifest keyed by platform: every reported difference must match a row on file, estimator and field and be within its tolerance, every listed row must have been observed, and the host's `uname` and compiler must match a platform block. It used to be a list of two FILENAMES that inspected nothing else, and a deliberate 0.85-to-0.01 change in one of those files was accepted (`A06`, `OC-56`). Do not widen a tolerance to swallow a delta that exceeded it — that is the finding, not the obstacle.
   - For memory or UB findings also build with sanitizers, `make <tool> CXXFLAGS='-std=c++11 -fopenmp -O1 -g -fsanitize=address,undefined -I/usr/include/jsoncpp'`, and run the reproduction inputs. `regression-estimator-guards.sh` builds its own sanitizer binary and is the model for this.
7. **Check the documentation claims:** `cd cpp/selftest && ./regression-docs.sh`

   The prose has drifted out of true twice, both times still telling a reader the fork was unmodified after it had been modified. This script checks what can be checked mechanically: that commit SHAs resolve, referenced paths and links exist, the tracker's counts match its own sections, the pinned figure quoted in the documents matches both `pin-check.sh` and the current build, no built program links MPFR or GMP, and no previously-corrected claim has reappeared. If a repair changes what the documents assert, update them and re-run it.
8. **Commit** the fix and its regression test together in one commit:
   - Message form: `fix(<ID>): <what was wrong>`.
   - In the body: the affected source, the reproduction before and after, and the regression-test path.
9. **Update the tracker** in a separate commit, `audits: <ID> -> <STATE>`. Fill in:
   - **State:** `FORK-FIXED`
   - **Current fork status**
   - **Fork fix commit:** the SHA from step 8
   - **Regression test:** its path
   - **Verification:** the command and its result
   - **Last upstream-status check:** today's date
   - **Required next action**
   Then update the queue table and the summary counts at the top.
10. **Verify independently.** In a fresh clone of fork `master`, do a clean build, run `cpp/selftest/run-all-checks.sh` and `cpp/selftest/regression-docs.sh`, and re-run the finding's Reproduce block, which must no longer show the `BUG:` lines. Then set `VERIFIED` and record the date.

## State transitions

| From | Event | To |
|---|---|---|
| `NEEDS-FIX` | an upstream PR proposing a fix is opened | `UPSTREAM-FIX-PENDING` |
| `NEEDS-FIX` / `UPSTREAM-FIX-PENDING` | upstream merges a fix, or closes the issue as completed | `FIXED-UPSTREAM-VERIFY` |
| `UPSTREAM-FIX-PENDING` | the PR is closed unmerged, or goes stale by the owner's judgement | `FORK-FIX-REQUIRED` |
| `NEEDS-FIX` | upstream closes the issue as not planned, won't fix, or as a duplicate of something unfixed | `FORK-FIX-REQUIRED` |
| `FIXED-UPSTREAM-VERIFY` | verification shows the upstream code is still wrong | `FORK-FIX-REQUIRED` |
| `FIXED-UPSTREAM-VERIFY` | upstream code corrected, regression test passes against it, change brought into the fork | `VERIFIED` |
| `NEEDS-FIX` / `FORK-FIX-REQUIRED` | fork fix and regression test committed | `FORK-FIXED` |
| `FORK-FIXED` | independent clean-clone verification passes | `VERIFIED` |
| `NEEDS-FIX` in an excluded executable | supported-build exclusion and drift guard committed | `EXCLUDED-UNSUPPORTED` (not fixed; reactivate before scope expansion) |
| supported instances fixed, excluded instance remains | fix regressions plus supported-build exclusion guard pass | `SUPPORTED-SCOPE-FIXED` |
| platform-specific failure cannot reproduce on the available ABI | evidence identifies the required ABI and a repair cannot be distinguished from a no-op | `BLOCKED-HARDWARE` |
| any confirmed state | the finding turns out to be spec-consistent, with the reason and evidence recorded | `NOT-A-BUG` (move the row; never delete it) |

## Periodic upstream-status check

For every row with an upstream issue or PR, re-query GitHub (step 2), apply the transitions above, and set **Last upstream-status check** to the date of the check. Record the stateReason for closed issues: `completed` does not prove a fix, so verify the code.

## Deduplication

Deduplicating files (identical copies of upstream sources, logs or reports in the audit archive) is housekeeping. It never removes or resolves a finding. Before removing any audit file, confirm that the tracker's evidence paths for every finding still resolve.

### Rule 6 — a sweep is evidence about the rows it sampled

A sampled table is **sampled rows**, never an interval. Where a claim about
every point in a range is wanted, the boundaries must be solved for.

**How this was learned.** The project claimed the printed and corrected restart
cutoffs were "identical at every H_I from 0.50 to 0.989", on the strength of a
sweep in steps of 0.02 with a fine sweep near one boundary. An outside audit
produced a counterexample inside the range, at `H_I = 0.9661822653793894`,
where the printed cutoff is 581 and the exact one 582. It reproduced in the
production C++ immediately. The window it sits in is **3.2e-06 wide** — no
sweep in steps of 0.02 could find it, and a finer sweep would only have moved
the goalposts, because the quantity is an **integer quantile** and integer
quantiles move at boundaries that sampling steps straight over. Solving for the
crossings instead showed 36 such intervals, totalling 0.217 % of the range
(`OC-49`).

The same entry carries the companion error: the cutoff reported for
`H_I = 0.696` had been computed at **0.70**, a rounded stand-in. A step
function does not tolerate a rounded input — 0.70 gives 683 and 0.696 gives
684. **Compute at the value you will actually use, every time.**

| do | instead of |
|---|---|
| solve for the boundary and report the interval you proved | sweeping and reporting the gaps between samples |
| compute at the measured input on every run | computing at a round number near it |
| state "zero at every point this sweep sampled" | state "zero throughout the range" |

The project's tool already does the right thing at runtime: the cutoff is
computed from the `H_I` the operator supplies, every run. The failure was in
the prose about it.

### Rule 7 — a negative fixture is built by mutation, and its baseline is asserted accepted

**Four refusals for the wrong reason are indistinguishable from four working
guards.**

**How this was learned.** An outside audit reported that the floor oracle
emitted a figure and exit 0 for four malformed reports. Reproducing it, I built
four negative fixtures by hand — one missing `errorLevel`, one flagged as a
short dataset, one claiming 10 bits from a one-bit sample, one carrying a
nonfinite value. **All four were refused.** It looked like four working guards
and a finding that was already fixed. They were all refused for **one shared
accidental reason**: my fixtures used the wrong key for the test-case label, so
every one died on "no test case labelled Overall" and **not one of the four
properties was exercised**. Rebuilt by mutating a genuine report one field at a
time, all four reproduced exactly as reported. Had I stopped at the first
attempt I would have told an outside audit it was wrong when it was right.

**The method.**

| do | instead of |
|---|---|
| copy a genuine artifact and change **one field** | write a fixture from scratch that resembles one |
| assert the **unmutated** baseline is **accepted** before any negative | assume the construction is sound because the negatives refuse |
| check each refusal **names the property under test** | count nonzero exits |

**Mechanised**, so it is not a thing to remember: `mutation-lib.sh` provides
`mut_baseline <label> <cmd...>`, which asserts the unmutated artifact is
accepted and records that it did. `mut_summary` **fails any harness that never
asserted a baseline**, so a fixture set that refuses everything fails as broken
rather than passing as thorough. Verified both ways: with the baseline accepted
the harnesses pass, and with the baseline deliberately broken the harness
reports `the FIXTURES are broken, not the guard` and fails.

**THIS RULE EARNED ITS KEEP ON ITS FIRST APPLICATION — three findings, which
is why it is load-bearing rather than ceremonial.**

1. The sweep found a script with **no assertions at all**
   (`reproducers/c16-c23-matrix.sh`): it classified and printed, its
   expectations were echoed as prose and never compared, and its exit status
   came from a timing print. Nothing in it could fail.
2. Adding assertions to it **immediately caught a wrong expectation of mine**.
   I expected the pre-`C16` builds to refuse an underflowing `H_I`. They
   **accept** it, with cutoff 1000 — and that acceptance *is* the defect the
   matrix exists to demonstrate. **The harness had been asserting the opposite
   of the thing it was built to show**, and four rounds of reading it had not
   told me. That is precisely the failure mode this rule exists for, and it was
   sitting in the tree.
3. The corollary below then bit twice more, in a harness and in a CI gate.

A corollary found in the same pass: a **hardcoded expected count** inside a
harness is the same trap wearing different clothes. The inventory harness
compared against the literal `20 passed, 0 failed (18 regression scripts
discovered)`, and registering one new regression script made its positive
control fail for a reason unrelated to any mutation — which invalidates every
negative result beneath it. It now derives those numbers from
`run-all-checks.sh`'s own constants, and refuses to run if it cannot read them.

### Rule 8 — a bit-identity claim carries a self-comparison and a live-sensitivity check

Two checks, neither optional, and the pair is the standing method:

1. **Self-comparison.** Run the *unchanged* artefact against itself and see
   what differs. Anything that differs there is nondeterministic by design and
   is excluded **by evidence**; anything else is attributable to the change.
2. **Live sensitivity.** Perturb the quantity under test by the smallest amount
   that should register and confirm the comparator catches it. A comparator
   that cannot fail has proved nothing.

**How this was learned.** Checking that widening `n_choose_2` changed nothing
on LP64, the first comparison said **five of nine reports differed**. Running
the baseline against itself showed the same binary differs from itself in
exactly that field, because the permutation tests seed from `/dev/urandom`.
That converted "the fix changed something" into "this field is
nondeterministic by design" — and a 1e-15 perturbation of `hAssessed` then
proved the comparator was not simply blind to everything. With both checks,
nine of nine identical (`OC-53`).

Applied again the same day to the `C22c` ceiling (`OC-59`): both controls
passed, the monotonicity premise held, and the comparison against the recorded
values then showed the **magnitudes do not reproduce** — which only became a
finding because the measurement was trustworthy enough to believe.

| do | instead of |
|---|---|
| run the unchanged thing against itself first | assume which fields are stable |
| exclude a field because it was *measured* to vary | exclude it because it looks like it might |
| perturb and confirm the comparator fires | report "identical" from a comparator you never tested |

### Rule 9 — a sweep's extremum at a boundary is a lower bound, not an extremum

A sweep that reports its maximum at the first or last point of its own range
has not found a maximum. It has found **the edge of where it looked**, and the
true extremum is outside that range or at least unbounded by the search.

**The obligation.** Any sweep reporting an extremum at a domain boundary must
either

- **extend the domain until the extremum moves inside**, or
- **state that the result is a boundary value**, and therefore a *lower bound
  on* the extremum rather than the extremum itself.

**The exception, and it is the common case here.** A boundary that is a
**physical or mathematical limit** is not an arbitrary edge: a proportion from
a non-zero count cannot go below `1/n`; a count is an integer in `[0, N]`; an
alphabet size is `2..256`. An extremum sitting on *that* kind of edge is
legitimate, and the right thing is to say which limit it is. What is not
legitimate is an extremum sitting on a window the author chose.

**How this was learned.** Deriving the `C22c` ceiling, a sweep over `p` ran
down to `1e-6` and then refined to `p0/4`, reporting its worst case at
**`p = 2.5e-07`** — below `1/n`, a proportion no count can produce. The gap
grows without limit as `p → 0`, so the sweep reported the edge of its own grid
and called it a worst case (`OC-59`, corrected in `OC-62`). Constraining the
domain to `p ≥ 1/n` moved the maximum onto that physical edge, where it
belongs, and it then matched the closed form exactly.

| do | instead of |
|---|---|
| bound the domain by the physical limit and say which limit | pick a search window and sweep it |
| check the extremum is interior, or name the limit it sits on | report `max(...)` over a grid |
| extend until the extremum moves inside | refine around a boundary value |

A corollary from the same correction: **a bound computed from a typical value
is not a bound.** The collision ceiling came out 4.6% low because the sweep
used `v = n/2.5`, a typical collision count, where the record bounds
`v ≥ n/3`. The arithmetic was right and the quantity was not a ceiling.

### Rule 10 — severity inherited from an unknown mechanism is a guess

A finding whose **mechanism is unknown** carries its severity as
**unestablished**, not as a number inferred from the category it was filed
under. "Platform", "library", "environment" are **hypotheses about a cause**,
not observations, and a severity derived from one inherits its uncertainty.

**How this was learned.** Upstream issue #219 recorded exactly the `C18`
symptom — `ea_iid`'s §5.2.5 test printing a negative `Pr(X≥1)` on Windows
MinGW — and filed it as **platform / library, severity LOW**. It sat open for
about a year. The actual mechanism is a **32-bit `long`** overflowing inside
`n_choose_2`'s product, which makes a required test fail **unconditionally
whatever the data**. This audit's own clustering had it as "`C18`, Low, expect
to refute" for the same reason.

The misclassification was reasonable on the evidence available: a negative
probability from an integer overflow and one from a mismatched library look
identical from outside. That is exactly why the severity could not be inferred
from it.

| do | instead of |
|---|---|
| record severity as unestablished until the mechanism is | assign severity from the suspected category |
| treat "platform" as a hypothesis to test | treat it as a classification that caps impact |
| re-rank when the mechanism lands | leave the original rank in place |

The companion observation is that **external corroboration of a symptom is not
validation of a fix**: #219 confirms the symptom exists in the wild, and
confirms nothing about whether widening the type is correct. That rests on its
own evidence.

### Rule 11 — a record whose truth depends on repository state names that state, and something re-reads it when the state changes

A finding filed as *"on branch X"*, *"in file Y"*, *"at tag Z"* is true only
while that state holds. The record must **name the state it depends on**, and
something must **re-read it when that state changes**.

The changes that invalidate such a record:

| change | what it can do to a record |
|---|---|
| **a branch merges** | "not live, repair branch only" becomes false, possibly into the enforced suite |
| **a branch closes unmerged** | "pending on the repair branch" becomes permanently false |
| **a file is deleted or renamed** | a finding's location, and any citation of it, dangles |
| **a tag is re-pointed** | "measured at tag T" now describes different bytes |
| **a repository is re-cloned or a submodule updated** | a path-based claim may resolve elsewhere |

**How this was learned.** `DEAD-GUARD-SWEEP.md` recorded two false-pass guards
accurately and filed them *"both on the repair branch"*, therefore not live. The
2026-10-15 merge put both on `master` and **one into the enforced suite**, where
it was counted toward "22 passed" for six days. Nothing re-read the sweep when
the branch merged. Both were still producing false passes when an outside
session found them (`OC-64`).

The companion case is the **denominator**: `OC-64`'s sweep reported "53
instruments" against an inventory that existed only in that one command line, so
nothing could re-read it either. The inventory is now a file
(`audits/INSTRUMENT-INVENTORY.md`) with the rule and a reproduction command, and
a sweep cites it (`OC-65`).

| do | instead of |
|---|---|
| name the state: "on `repair/...` as of `<sha>`" | "on the repair branch" |
| re-read every state-dependent record at a merge | assume the record ages gracefully |
| put the inventory a count rests on in a file | derive it inline and report the number |

This generalises the earlier merge rule about files that enumerate other files:
**that** was about a file whose content lists other files, **this** is about a
record whose truth references repository state of any kind.

### Diagnostic — when two inventories disagree, find the subset where they agree

Not a rule about instruments; a method for resolving a disagreement about
counts, which is what every *"N examined"* figure rests on.

**The method.** Two readers report different totals for the same thing. Do not
argue about the totals, and do not recount from scratch. **Partition both
inventories and find a subset where they agree exactly.**

**Why it works.** An inventory that mis-enumerates the *tree* misses in every
subset. An inventory that applies the wrong *rule* misses only where the rule
bites. So agreement on one subset and disagreement on another **localises the
fault to the definition**, and names the subset where the two definitions
differ.

**How this was learned.** An outside session counted 70 live instruments and 79
frozen; this session had reported 53. The **frozen counts matched exactly at 79
on the first attempt**, and that single fact did all the work: the disagreement
was confined to the live set, so it was about the rule rather than the tree.
Comparing the two live enumerations then produced the answer in one step — an
extension-matched glob cannot see `cpp/selftest/selftest`,
`cpp/selftest/generate-refdata` or `compareresults.pl` (`OC-65`).

**The corollary.** Write the inventory down, in a file, with the rule and a
reproduction command — `audits/INSTRUMENT-INVENTORY.md`. A denominator that
exists only in the shell history that produced it cannot be re-derived, cannot
be cited, and cannot be found wrong. Every sweep this project had reported was
in that state (`OC-67`).
