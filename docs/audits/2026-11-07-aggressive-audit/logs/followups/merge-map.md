# Merge map: fix/stale-report, fix/openssl-pin, fix/restart-notrun into master

Written 2026-11-08 from a read-only simulation. Nothing here was merged into
master; master is `04c1ccc` before and after this work.

| ref | tip | commits past master | role |
|---|---|---|---|
| `master` | `04c1ccc` | — | target |
| `fix/stale-report` | `c8b0bc6` | 1 | merge 1 (PROV-01) |
| `fix/openssl-pin` | `7d647e6` | 3 (`b62336b`, `ccaab67`, `7d647e6`) | merge 2 (PROV-15) |
| `fix/restart-notrun` | `745b396` | 1 | merge 3 (AA-04) |
| `fix/multimmc-lookup` | `3b1a418` | 2 | **NOT merged** — see section 7 |

All four branches fork from `04c1ccc` directly (`git merge-base` = master for
each), so merge 1 is trivially clean and every later conflict is between two
fix branches, not between a branch and master.

## 0. How this was derived, and the record

- Read first: `audits/BUG-REPAIR-GUIDE.md`, the table under "A clean merge is a
  statement about text, not about meaning" (line 111 at `04c1ccc`). Every file
  that table names as a drop-or-stale hazard was checked below; the three that
  matter here are `regression-script-inventory.txt`, the two expected counts in
  `run-all-checks.sh`, and the prose counts the guide does not list but
  `regression-docs.sh` compares (`CLOSING-INVENTORY.md`,
  `INSTRUMENT-INVENTORY.md`, `WHAT-A-GREEN-SUITE-ESTABLISHES.md`).
- Per-branch inputs: `diffstat-*.txt` and `diff-noncpp-*.patch` in this
  directory (one pair per branch, including `multimmc-lookup`).
- Simulation: a detached scratch worktree at `scratchpad/mergesim` on
  `04c1ccc`; the three merges performed there in order with `--no-ff`, each
  conflict resolved by a script that asserts every replacement landed exactly
  the expected number of times (`mergesim-resolve-step2.py`,
  `mergesim-resolve-step3.py`; the step-2 script carries an unused, speculative
  step-3 branch — the step-3 script is the one that ran). Simulation commits:
  `a8b3cfa` (merge 1, tree `1f3325c…`), `bf79f05` (merge 2 resolved, tree
  `61905d2…`), `46230d3` (merge 3 resolved, tree
  `5e955105de4d21855b45313f3eb08c478f054a88`). The worktree has been removed;
  those commits survive only as unreachable objects and may be garbage-collected,
  so the durable record is the patches and copies here:
  - `mergesim-step2-merge.log`, `mergesim-step2-conflicts.txt`,
    `mergesim-step2-hunks.txt` — what git produced at merge 2;
  - `mergesim-step3-merge.log`, `mergesim-step3-conflicts.txt`,
    `mergesim-step3-hunks.txt` — the same at merge 3;
  - `mergesim-step2-resolution.patch`, `mergesim-step3-resolution.patch` — the
    four count-bearing files, each resolved state against the previous merged
    state (153 and 158 lines);
  - `mergesim-final-vs-master-noncpp.patch` — the whole non-C++ delta of the
    final tree against master (322 lines);
  - `final-files/` — byte-exact final copies of `run-all-checks.sh`,
    `CLOSING-INVENTORY.md`, `INSTRUMENT-INVENTORY.md`,
    `WHAT-A-GREEN-SUITE-ESTABLISHES.md`, `regression-script-inventory.txt`,
    `NOTICE`, with `final-files.sha256`;
  - `mergesim-step2-enum.log`, `mergesim-step3-enum.log`,
    `mergesim-step3-enum-recheck.log` — the enumerator's readings, including
    the false 92 and its reproduction (section 6);
  - `mergesim-step3-verify.log` — the regression-docs.sh count checks
    replicated with that script's own regexes against the final tree.
- Not run, by instruction: `make`, `run-all-checks.sh`, `regression-docs.sh`,
  `harness-inventory-mutation-test.sh`. The count comparisons those scripts make
  were replicated with their exact extraction expressions (section 5) and the
  enumerator was run as-is.

## 1. The hazard, observed

All three branches edit the **same lines to the same values**: `24 -> 25`,
`26 -> 27`, `87 -> 88`, `21 -> 22` named defects, `3 of 24 -> 3 of 25`. Git
treats an identical change on both sides as no conflict, so at merge 2
`run-all-checks.sh` auto-merged with **zero conflicts to `25`/`27`** — the
counts for a tree with one new script, in a tree that had two. The same
happened on every count-bearing line where the two branches' wording
coincided: `runs 25 regression scripts`, `expect 27 passed, 0 failed` (both
occurrences), `**88 live instruments**`, `3 of 25` (twice), `22 named
defects`, `about 22 checks`, `21 of 27 checks`. Only the lines where the
branches' *wording* differed conflicted. **Every count in the four files must
be set by hand after each merge, whether or not git conflicted on it.** At
merge 3 the counts did conflict (my resolved `26/28` against the branch's
`25/27`), which is the safer outcome, but only because merge 2 had been
resolved to a value no branch carries.

What merged clean **and correct**, at both steps, and needs no edit:

| file | why clean | verified |
|---|---|---|
| `cpp/selftest/regression-script-inventory.txt` | each branch inserts its one line at a different alphabetical position | final listing in section 4; 27 non-comment entries, `regression-constants.sh` still last |
| `NOTICE` | each branch inserts its entry at a different place in the 2026 list (after the C23/OC-30 entry; after the `d892b90` entry; after the `25fbb54` entry) | final has three `2026-11-08` entries at lines 259, 280, 362; 528 -> 572 lines = +16 +14 +14 |
| `.github/workflows/x86-64-platform-facts.yml`, `cpp/Makefile` | only `fix/openssl-pin` touches them | `git diff --quiet fix/openssl-pin -- <both>` rc 0 on the final tree |
| `cpp/restart_main.cpp` | `fix/stale-report` (+23) and `fix/restart-notrun` (+57) touch disjoint regions | auto-merged; final differs from each branch by exactly the other's hunks |
| the three new scripts, `iid_main.cpp`, `non_iid_main.cpp`, `non_iid_test_case.h` | single-branch files | `git diff --quiet <branch> -- <files>` rc 0 for all three branches |
| `cpp/selftest/fixture-manifest.txt`, `known-platform-deltas.txt`, `outside-battery-corpus.txt`, `regression-docs.sh`, `.gitignore` | no branch touches them | diffstats |

## 2. Merge 1 — `fix/stale-report` (`c8b0bc6`) onto `04c1ccc`

**Conflicts: none** (base is master). Result = the branch's tree.

Values on that tree, all correct for it: `EXPECTED_REGRESSION_SCRIPTS=25`,
`EXPECTED_TOTAL_CHECKS=27`, enumerator **88** (measured on `a8b3cfa`:
`live:   88  (78 mechanical + 10 reviewed)`), inventory 25 entries with
`regression-stale-report.sh` after `regression-selftest-inventory.sh`.

Two wording nits in the branch's text, neither checked mechanically, both
overwritten by the merge-2 resolution so no edit is needed at this step:
- WHAT-A-GREEN precondition 3 still says "seven scripts source
  `buildstate-lib.sh` … a static count gives 7", but `regression-stale-report.sh`
  sources it, so the tree has eight;
- INSTRUMENT-INVENTORY says "**88** at `04c1ccc` with
  `cpp/selftest/regression-stale-report.sh` staged" — true when measured,
  odd once the script is committed.

Expected after merge 1 (clean build): see section 5 with N=27, S=25, L=88.

## 3. Merge 2 — `fix/openssl-pin` (`7d647e6`) onto the merge-1 result

**Conflicts (3 files, 6 hunks):** `audits/2026-10-11-independent-audit/CLOSING-INVENTORY.md`
(1), `audits/INSTRUMENT-INVENTORY.md` (2), `cpp/selftest/WHAT-A-GREEN-SUITE-ESTABLISHES.md`
(3). Raw hunks: `mergesim-step2-hunks.txt`.

**Clean-but-wrong lines to edit by hand (no markers):**

| file | auto-merged | must become |
|---|---|---|
| `cpp/selftest/run-all-checks.sh` | `EXPECTED_REGRESSION_SCRIPTS=25` / `EXPECTED_TOTAL_CHECKS=27` | `26` / `28` |
| CLOSING-INVENTORY.md line ~87 | `runs 25 regression scripts` | `runs 26 regression scripts` |
| CLOSING-INVENTORY.md lines ~88 and ~483 | `expect 27 passed, 0 failed` (2 occurrences) | `expect 28 passed, 0 failed` (both) |
| CLOSING-INVENTORY.md line ~89 | `**88 live instruments**` | `**89 live instruments**` |
| WHAT-A-GREEN header (lines 4–5) | `Counts re-derived 2026-11-08 when` / `` `regression-stale-report.sh` joined the suite (PROV-01). `` | see resolved text below |
| WHAT-A-GREEN mutation row and precondition 1 | `3 of 25` (2 occurrences) | `3 of 26` |
| WHAT-A-GREEN "So, plainly" | `**22 named defects` … `a statement about 22 checks` … `21 of 27 checks` | `23` … `23` … `21 of 28 checks` |
| INSTRUMENT-INVENTORY paragraph after "document was found to be four behind" | `**87 -> 88 at \`04c1ccc\` with one file staged (PROV-01, 2026-11-08).** …` (5 lines) | see resolved text below |

**Resolved content, hunk by hunk** (exact; also in `mergesim-step2-resolution.patch`):

CLOSING-INVENTORY.md, the enumerator bullet's continuation (replaces the whole
conflict block):

```
  2026-11-08 on the merged tree, `04c1ccc` with `c8b0bc6` and `7d647e6`
  merged, up two on `OC-128`'s 87 at `a5422cf`: one each for
  `cpp/selftest/regression-stale-report.sh` (PROV-01) and
  `cpp/selftest/regression-openssl-pin.sh` (PROV-15); the count has a
  hand-reviewed limb, `OC-126`);
```

INSTRUMENT-INVENTORY.md, both LIVE rows:

```
| **LIVE** | behaviour, present tense: is it run, sourced, compiled, or a workflow **now** | **89** at `04c1ccc` with `c8b0bc6` and `7d647e6` merged, 2026-11-08 |
```
```
| **LIVE** | **89** at `04c1ccc` with `c8b0bc6` and `7d647e6` merged, 2026-11-08 | `cpp/selftest`, `tools`, `.github`, `audits/2026-10-11-independent-audit`, `audits/2026-10-09-independent-audit`, `repairs/*/rerun.sh` — anything a sweep must cover today |
```

INSTRUMENT-INVENTORY.md, the "87 -> 88" paragraph (hand edit, not a conflict):

```
**87 -> 89 across the 2026-11-08 merges into master (PROV-01, PROV-15).** The
instruments are `cpp/selftest/regression-stale-report.sh`, the regression for
the stale-report ordering defect in the three tools' `-o` claim, and
`cpp/selftest/regression-openssl-pin.sh`, the regression for the openssl@3
pin's include and link order. Each fix branch counted 88 alone against the
same 87, so the branch figures do not sum: the merged tree is counted once,
by the enumerator, after each merge.
```

WHAT-A-GREEN header (hand edit):

```
the commands given. Counts re-derived 2026-11-08 when
`regression-stale-report.sh` (PROV-01) and `regression-openssl-pin.sh`
(PROV-15) joined the suite.
```

WHAT-A-GREEN behaviour-regressions row: take `fix/openssl-pin`'s side (it
carries the "A fourth, `regression-openssl-pin.sh` …" sentence) and set the
count cell to `| 26 |`.

WHAT-A-GREEN preconditions 2 and 3 (one conflict block, two rows):

```
| **2. every member's inputs exist before an absence is read** | **PARTLY ENFORCED, and it is the minority.** 5 of 26 assert presence or carry a third outcome. | `grep -lE 'HARNESS FAULT\|is absent or empty\|INPUT-DID-NOT-REACH' cpp/selftest/*.sh \| grep -c .` → 5 |
| **3. build state is recorded** | **ENFORCED where declared, and declared by few.** The aggregator now surfaces every declaration and prints the coverage; it is **7 of 28** — 5 of 26 measured 2026-10-27 from the `build-state:` line of `./run-all-checks.sh --allow-known-platform-deltas`, which is the only place this figure exists, plus `regression-stale-report.sh` and `regression-openssl-pin.sh` (added 2026-11-08), each of which declares through `bs_print`; DERIVED from the measurement by two, and the next run's `build-state:` line re-measures it. It is NOT derivable by reading the tree: nine scripts source `buildstate-lib.sh` and only seven of them are suite members that declare, so a static count gives 9 and is wrong (`OC-126`). The two `-DNDEBUG` arms are now distinguishable, where before they were byte-identical (`OC-66`). | the `build-state:` line in every run |
```

(Why 5, not 4: `regression-stale-report.sh` carries both `HARNESS FAULT` and
`is absent or empty`; `regression-openssl-pin.sh` carries neither. Measured on
the merged tree: 5. Why nine: the seven on master plus both new scripts source
`buildstate-lib.sh`. Measured: 9.)

WHAT-A-GREEN "So, plainly" tail (conflict block):

```
that do not say (21 of 26 measured 2026-10-27, same source as above; the two members
added 2026-11-08 declare, so the denominator moved and the numerator did not).
```

Measured on the resolved merge-2 tree: `live:   89  (79 mechanical + 10
reviewed)`; `n_pres` 5; sourcing scripts 9; inventory 26; prose forms
`3 of 26 scripts`, `5 of 26 assert`, `21 of 28 checks`.

Expected after merge 2 (clean build): section 5 with N=28, S=26, L=89; Linux
CI gate `26 passed, 0 failed, 2 could not run` and
`could-not-run: regression-openssl-pin regression-platform-deltas`.

## 4. Merge 3 — `fix/restart-notrun` (`745b396`) onto the merge-2 result

**Conflicts (4 files, 8 hunks):** `cpp/selftest/run-all-checks.sh` (1),
CLOSING-INVENTORY.md (2), INSTRUMENT-INVENTORY.md (2), WHAT-A-GREEN (3). Raw
hunks: `mergesim-step3-hunks.txt`. This time every count line conflicts
(`26/28/89` vs the branch's `25/27/88`), so nothing count-bearing auto-merges
wrong; three hand edits remain outside the markers.

**Resolved content** (exact; also `mergesim-step3-resolution.patch`, and the
whole files in `final-files/`):

`run-all-checks.sh`:

```
EXPECTED_REGRESSION_SCRIPTS=27
EXPECTED_TOTAL_CHECKS=29
```

CLOSING-INVENTORY.md, the two bullets (one conflict block):

```
- `cpp/selftest/run-all-checks.sh` runs 27 regression scripts
  (`./run-all-checks.sh --allow-known-platform-deltas` — expect 29 passed, 0 failed);
- `audits/enum-instruments.sh` prints **90 live instruments** (measured
  2026-11-08 on the merged tree, `04c1ccc` with `c8b0bc6`, `7d647e6` and
  `745b396` merged, up three on `OC-128`'s 87 at `a5422cf`: one each for
  `cpp/selftest/regression-stale-report.sh` (PROV-01),
  `cpp/selftest/regression-openssl-pin.sh` (PROV-15) and
  `cpp/selftest/regression-restart-notrun.sh` (AA-04); the count has a
  hand-reviewed limb, `OC-126`);
```

CLOSING-INVENTORY.md, the command block line (second conflict block):

```
./run-all-checks.sh --allow-known-platform-deltas   # expect 29 passed, 0 failed
```

INSTRUMENT-INVENTORY.md, both LIVE rows:

```
| **LIVE** | behaviour, present tense: is it run, sourced, compiled, or a workflow **now** | **90** at `04c1ccc` with `c8b0bc6`, `7d647e6` and `745b396` merged, 2026-11-08 |
```
```
| **LIVE** | **90** at `04c1ccc` with `c8b0bc6`, `7d647e6` and `745b396` merged, 2026-11-08 | `cpp/selftest`, `tools`, `.github`, `audits/2026-10-11-independent-audit`, `audits/2026-10-09-independent-audit`, `repairs/*/rerun.sh` — anything a sweep must cover today |
```

INSTRUMENT-INVENTORY.md paragraph (hand edit, replaces the merge-2 paragraph):

```
**87 -> 90 across the 2026-11-08 merges into master (PROV-01, PROV-15, AA-04).**
The instruments are `cpp/selftest/regression-stale-report.sh`, the regression
for the stale-report ordering defect in the three tools' `-o` claim;
`cpp/selftest/regression-openssl-pin.sh`, the regression for the openssl@3
pin's include and link order; and `cpp/selftest/regression-restart-notrun.sh`,
the regression for a declined restart row or column estimator that was
dropped from the report silently. Each fix branch counted 88 alone against
the same 87, so the branch figures do not sum: the merged tree is counted
once, by the enumerator, after each merge.
```

WHAT-A-GREEN header (hand edit):

```
the commands given. Counts re-derived 2026-11-08 when
`regression-stale-report.sh` (PROV-01), `regression-openssl-pin.sh`
(PROV-15) and `regression-restart-notrun.sh` (AA-04) joined the suite.
```

WHAT-A-GREEN first conflict block (three table rows): the merge-2 side with
the behaviour count cell `| 27 |` and the mutation row ending `They cover 3 of 27. |`;
the integrity row unchanged.

WHAT-A-GREEN second conflict block (preconditions 1–3):

```
| **1. every member can fail** | **BELIEVED, and known false five times.** 3 of 27 scripts are covered by a mutation harness; the rest rest on having been *observed* to fail once, at the time they were written, recorded in the commit if at all. | `ls cpp/selftest/*mutation-test.sh cpp/selftest/regression-deadguard.sh \| wc -l` → 3 |
| **2. every member's inputs exist before an absence is read** | **PARTLY ENFORCED, and it is the minority.** 5 of 27 assert presence or carry a third outcome. | `grep -lE 'HARNESS FAULT\|is absent or empty\|INPUT-DID-NOT-REACH' cpp/selftest/*.sh \| grep -c .` → 5 |
| **3. build state is recorded** | **ENFORCED where declared, and declared by few.** The aggregator now surfaces every declaration and prints the coverage; it is **8 of 29** — 5 of 26 measured 2026-10-27 from the `build-state:` line of `./run-all-checks.sh --allow-known-platform-deltas`, which is the only place this figure exists, plus `regression-stale-report.sh`, `regression-openssl-pin.sh` and `regression-restart-notrun.sh` (added 2026-11-08), each of which declares through `bs_print`; DERIVED from the measurement by three, and the next run's `build-state:` line re-measures it. It is NOT derivable by reading the tree: ten scripts source `buildstate-lib.sh` and only eight of them are suite members that declare, so a static count gives 10 and is wrong (`OC-126`). The two `-DNDEBUG` arms are now distinguishable, where before they were byte-identical (`OC-66`). | the `build-state:` line in every run |
```

WHAT-A-GREEN third conflict block ("So, plainly" tail):

```
at all, or that the binary measured was the one intended in the 21 of 29 checks
that do not say (21 of 26 measured 2026-10-27, same source as above; the three members
added 2026-11-08 declare, so the denominator moved and the numerator did not).
```

WHAT-A-GREEN hand edits: `**23 named defects` -> `**24 named defects`;
`a statement about 23 checks` -> `a statement about 24 checks`.

Final inventory, non-comment entries in file order (27; the OC-121 comment
block and `regression-constants.sh` stay last):

```
regression-271.sh  regression-272.sh  regression-chisquare.sh  regression-deadguard.sh
regression-docs.sh  regression-estimator-guards.sh  regression-iid-failclosed.sh
regression-iid-json.sh  regression-input-identity.sh  regression-minsize.sh
regression-multimmc.sh  regression-nonregular.sh  regression-notrun.sh
regression-openssl-pin.sh  regression-option-order.sh  regression-output-aliasing.sh
regression-output.sh  regression-outside-battery.sh  regression-platform-deltas.sh
regression-restart.sh  regression-restart-notrun.sh  regression-selftest-inventory.sh
regression-stale-report.sh  regression-subset.sh  regression-width.sh
regression-workflows.sh  regression-constants.sh
```

### Final expected values

| quantity | value | where it must appear | how it was established |
|---|---|---|---|
| `EXPECTED_REGRESSION_SCRIPTS` | **27** | `run-all-checks.sh:29` | 24 + 3; inventory non-comment count on the final tree = 27 |
| `EXPECTED_TOTAL_CHECKS` | **29** | `run-all-checks.sh:30` | 26 + 3 |
| live instruments | **90** (80 mechanical + 10 reviewed) | CLOSING-INVENTORY `**90 live instruments**` (1 occurrence); INSTRUMENT-INVENTORY `**90** at \`` (2 rows) | `sh audits/enum-instruments.sh .` on the committed final tree; `--list` differs from master by exactly the three scripts |
| regression scripts, prose | `runs 27 regression scripts` | CLOSING-INVENTORY (1 occurrence) | regression-docs.sh `inv_count` row 2 |
| passed line, prose | `expect 29 passed, 0 failed` | CLOSING-INVENTORY (2 occurrences: bullet and command block) | `inv_count` row 1 compares every occurrence |
| WHAT-A-GREEN count cell | `\| 27 \|` | behaviour-regressions row | `grep -q "\| 27 \|"` |
| WHAT-A-GREEN prose forms | `3 of 27 scripts`, `5 of 27 assert`, `21 of 29 checks` — nothing else of the form `N of M (scripts\|assert\|checks)` | preconditions 1–2, "So, plainly" | every M must be 27 or 29; at least 3 forms |
| WHAT-A-GREEN arrows | `→ 3`, `→ 5`, `→ 0` | preconditions 1, 2, 4 | `n_mut`=3, `n_pres`=5, `n_hard`=0 measured on the final tree |
| build-state coverage | `8 of 29` DERIVED; **read the `build-state:` line** at the first full run and correct if it differs | precondition 3 | 5 measured + 3 new members that call `bs_print` |
| scripts sourcing `buildstate-lib.sh` | ten (static count 10) | precondition 3 | measured: pin-check, option-order, openssl-pin, sanitizer-restart-c01, restart, stale-report, output-aliasing, output, restart-notrun, workflows |
| named defects | **24** | "So, plainly" (two places) | each branch added one to 21; see caveat in section 8 |
| x86-64 gate | `27 passed, 0 failed, 2 could not run` and `could-not-run: regression-openssl-pin regression-platform-deltas` | derived in the workflow from `EXPECTED_TOTAL_CHECKS`; the two names come from `run-all-checks.sh` in inventory order | `TOTAL - 2` with TOTAL=29; openssl-pin precedes platform-deltas in the inventory |
| macOS full-suite summary | `run-all-checks: 29 passed, 0 failed (27 regression scripts discovered)` | `run-all-checks.sh --allow-known-platform-deltas` | summary format at `run-all-checks.sh:319` |
| harness-inventory positive control | `run-all-checks: 29 passed, 0 failed (27 regression scripts discovered)`; `5 of 5 mutations landed` | `harness-inventory-mutation-test.sh` | its `EXPECTED_SUMMARY` is **derived** from `run-all-checks.sh` — nothing to edit |
| NOTICE | three `2026-11-08` entries (PROV-01 at ~259, AA-04 at ~280, PROV-15 at ~362) | `NOTICE` | auto-merged union, 572 lines |
| tree hash, if the final files are applied byte-exactly | `5e955105de4d21855b45313f3eb08c478f054a88` | `git rev-parse master^{tree}` after merge 3 | tree of simulation commit `46230d3`; the merge-commit SHA will differ, the tree need not |

## 5. What `regression-docs.sh` compares, so the documents satisfy it

`inv_count` rows (lines 1172–1202 at `04c1ccc`), all against
`audits/2026-10-11-independent-audit/CLOSING-INVENTORY.md`; each row requires
every occurrence to equal the script's own declaration and sums occurrences:

| row | regex on CLOSING-INVENTORY | declared by | value | occurrences |
|---|---|---|---|---|
| run-all-checks' total | `expect [0-9]+ passed, 0 failed` | `run-all-checks.sh` `EXPECTED_TOTAL_CHECKS` | **29** (was 26) | 2 |
| run-all-checks' script count | `run-all-checks\.sh[^0-9]*[0-9]+ regression scripts` | `run-all-checks.sh` `EXPECTED_REGRESSION_SCRIPTS` | **27** (was 24) | 1 |
| harness-inventory's declaration | `harness-inventory-mutation-test\.sh +# expect [0-9]+ of [0-9]+` | `harness-inventory-mutation-test.sh` `MUT_DECLARED` | 5 (unchanged) | 1 |
| outside-battery's declaration | `outside-battery-mutation-test\.sh +# expect [0-9]+ of [0-9]+` | `outside-battery-mutation-test.sh` `MUT_DECLARED` | 9 (unchanged) | 1 |
| platform-deltas' declaration | `regression-platform-deltas\.sh +# [0-9]+ cases` | `regression-platform-deltas.sh` `DECLARED_CASES` | 6 (unchanged) | 1 |
| oracle-selftest (command block) | `oracle-selftest\.sh +# [0-9]+ cases` | `oracles/oracle-selftest.sh` `DECLARED_CASES` | 33 (unchanged) | 1 |
| oracle-selftest (prose) | ``oracle-selftest\.sh` \([0-9]+ cases\)`` | same | 33 | 2 |
| output-aliasing's declaration | ``regression-output-aliasing\.sh` \([0-9]+ checks\)`` | `regression-output-aliasing.sh` `DECLARED_CASES` | 46 (unchanged) | 2 |
| the instrument enumerator | `\*\*[0-9]+ live instruments\*\*` | `sh audits/enum-instruments.sh .` `live:` | **90** (was 87) | 1 |

`INV_CHECKED_ROWS=9`; `inv_hits` must be 12 and the `inv_pairs` sweep (any
line naming one of those scripts and carrying a count-shaped number) must find
exactly 12 — it finds 12 on master and 12 on the final tree. The expected
note lines are therefore `the inventory's counts match the scripts'
declarations: yes (9 rows, 12 occurrences)` and `every script-count pair in
the inventory is checked: yes (12)`. None of the three branches touches the
five declaring scripts, so only rows 1, 2 and 9 change.

Also compared: INSTRUMENT-INVENTORY must contain the literal `**90** at \``
(OC-90 check, line 817); WHAT-A-GREEN's four arrow/cell checks and the
`N of M` denominator check (lines 1062–1118), satisfied by the values in
section 4; every commit SHA in NOTICE and the tracker must resolve (the new
NOTICE entries cite none that is new; the CLOSING-INVENTORY bullet cites
`04c1ccc`, `c8b0bc6`, `7d647e6`, `745b396`, `a5422cf`, all of which exist —
that document's SHAs are not checked mechanically, but they are true).

All nine rows, the sweep, the INVDOC literal and the scope checks were
replicated with these exact expressions against the final tree and pass
(`mergesim-step3-verify.log`; the one FAIL printed there is the false 92 of
section 6, re-measured as 90 in `mergesim-step3-enum-recheck.log`).

### Commands after each merge, with expected lines

Run on a clean build each time (the build is the orchestrator's; this map did
not run `make`):

```sh
cd cpp && make clean && make non_iid iid restart && cd selftest

./regression-docs.sh
#   ... the inventory's counts match the scripts' declarations: yes (9 rows, 12 occurrences)
#   ... every script-count pair in the inventory is checked: yes (12)
#   ... the suite's scope statement matches the tree: yes
#   ... the instrument inventory's live count matches the enumerator: L
#   regression-docs: PASS

./harness-inventory-mutation-test.sh
#   positive control accepts "run-all-checks: N passed, 0 failed (S regression scripts discovered)"
#   ... 5 of 5 mutations landed

./run-all-checks.sh --allow-known-platform-deltas
#   build-state: B of N checks declared the artefact they measured      <- READ B; expected 6 / 7 / 8
#   run-all-checks: N passed, 0 failed (S regression scripts discovered)

cd ../.. && sh audits/enum-instruments.sh .
#   live:   L  (M mechanical + 10 reviewed)                            <- run AFTER `git add` of the resolution (section 6)

git status --short                                                      # the guide's .gitignore row: nothing unexpected
```

| after merge | N (total) | S (scripts) | L (live) | M (mechanical) | B (build-state, derived) |
|---|---|---|---|---|---|
| 1 `fix/stale-report` | 27 | 25 | 88 | 78 | 6 |
| 2 `fix/openssl-pin` | 28 | 26 | 89 | 79 | 7 |
| 3 `fix/restart-notrun` | 29 | 27 | 90 | 80 | 8 |

On Linux (the x86-64 workflow, after merge 2 and 3): `(N-2) passed, 0 failed,
2 could not run` and `could-not-run: regression-openssl-pin
regression-platform-deltas`; after merge 1 the workflow is still master's and
expects `26 passed, 0 failed, 1 could not run` with `could-not-run:
regression-platform-deltas`.

The per-branch FAIL/PASS evidence the user asked for before each merge is the
branch's own regression against a pre-fix build (`regression-stale-report.sh`
takes `REGRESSION_STALE_REPORT_BINDIR`; the other two are run against a build
of the parent commit); it is outside this map but must precede each merge.

## 6. A measurement trap found while simulating: 92

The enumerator read **92** on the merge-3 tree twice, while `--list` showed
90 entries and only the three new scripts beyond master. Cause, reproduced
and logged (`mergesim-step3-enum-recheck.log`): both readings were taken while
the merge was **unresolved in the index**. `git ls-files`, which limb (a)
iterates, prints an unmerged path **once per stage**, so the conflicted
executable `run-all-checks.sh` was counted three times (+2; the three
conflicted `.md` files are excluded as data). At merge 2 only `.md` files
conflicted, so 89 was right by luck. On the committed tree the reading is 90.

**Rule for the real merges:** resolve, `git add` every conflicted file (so
`git ls-files -u` prints nothing), *then* run the enumerator and write the
number into the two documents, then commit. A count taken mid-conflict is not
a count of the tree.

## 7. `fix/multimmc-lookup` (`3b1a418`) — NOT merged; what must not leak

Its non-C++ diff (`diff-noncpp-multimmc-lookup.patch`) makes the same
`24->25 / 26->27 / 87->88 / 21->22` bumps (at `f46f2ea`), inserts
`regression-multimmc-lookup.sh` between `regression-minsize.sh` and
`regression-multimmc.sh`, and rewrites NOTICE's scope statement ("Two changes
alter results deliberately" -> "Three", "The two exceptions are F09 and N-01"
-> "three … F10 / C01", the closing "F09 and N-01 the two deliberate
exceptions" -> three) plus a new F10/C01 bullet and a 2026-11-08 entry.
**None of that goes to master.** The final counts are 27/29/90, not 28/30/91;
NOTICE keeps "Two changes" / "two exceptions" / "F09 and N-01"; the inventory
has no `regression-multimmc-lookup.sh`. If the branch is ever merged later it
will conflict on every one of these lines against the merged master, which is
the desired outcome; its WHAT-A-GREEN row-3 text ("6 of 27 EXPECTED", "seven
scripts source") is already stale against master+3.

For the separate task of recording the MultiMMC margin at ±0.08 bit while
keeping NOT-REPAIRED: the branch's NOTICE text is a usable source of the
figures (experiment X3, +0.078 bit on a crafted compliant 8-bit file; Literal
MultiMMC 0.97830188845975063 -> ~0.90052 on one crafted 1,000,000-sample
8-bit file and 1.1479041002434913 -> ~1.24064 on the other, with the
spec-literal reference at 0.9005162186024169 for Z = 2.576), but that record
belongs wherever the NOT-REPAIRED stance is stated, not in a merge of this
branch.

## 8. Caveats

- **Named defects = 24 is a judgement, not a measurement.** Master's 21 is
  24 scripts less three that are not about a defect (`workflows`,
  `option-order`, `constants`). Each branch added one; `fix/openssl-pin` added
  one while also describing its script as "about the BUILD rather than the
  tool". PROV-15 is a named defect, so 24 follows the branch authors; a reader
  who counts `regression-openssl-pin.sh` with the other three non-tool members
  gets 23. Nothing checks this number mechanically.
- **Build-state `8 of 29` is DERIVED.** The text says so and tells the reader
  to re-read the `build-state:` line; the first full run after merge 3 must
  confirm 8 or the number must be corrected to what was printed.
- **The main checkout moved under this task.** It was on `audit/2026-11-07`
  at my first command and on `master` (`04c1ccc`) a few commands later;
  `git reflog` shows `checkout: moving from audit/2026-11-07 to master` as
  HEAD@{0}, which I did not run (my worktree was created with `--detach` and
  all my git commands were `-C <worktree>`). `master`, the four fix tips and
  the index are unchanged; `docs/audits/` is untracked on master, so this
  directory's outputs sit in the working tree only.
- The tree hash in section 4 equals the real merged master's only if the four
  count-bearing files are applied byte-exactly from `final-files/`; any
  wording change moves it, and the merge-commit SHA differs regardless.
- A first extraction of the resolution patches produced empty files because
  the shell (zsh) did not word-split an unquoted variable; it was redone from
  the simulation commits by SHA with explicit paths
  (`mergesim-extract-redo.log`). The empty first attempt is the reason for the
  0-byte lines in `mergesim-extract-and-cleanup.log`.
