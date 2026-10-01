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

## Setup

```sh
git clone https://github.com/systemslibrarian/SP800-90B_EntropyAssessment.git && cd SP800-90B_EntropyAssessment
git remote add upstream https://github.com/usnistgov/SP800-90B_EntropyAssessment.git
git fetch upstream
cd cpp && make                 # dependencies: see BUILDING.md (jsoncpp, libdivsufsort, openssl, mpfr, gmp, bz2, OpenMP)
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
5. **Add a permanent regression test** under `cpp/regression/`, named after the finding (for example `cpp/regression/N-01.sh`, with small generated inputs rather than committed binaries where possible). A test must:
   - exit 0 when the behaviour is correct and non-zero when the defect is present;
   - be shown to fail on the unfixed code and pass on the fixed code (record both in the commit message);
   - use the finding's expected values with a stated tolerance where a figure is compared (see `BUILDING.md`, "Precision audit").

   If no `cpp/regression/run-all.sh` exists yet, the first fix adds it; it runs every `cpp/regression/*.sh` and fails if any fails.
6. **Run the tests:**
   - `cd cpp && make && ./regression/run-all.sh`
   - `cd selftest && ./selftest`, plus a check that the "Assessed min entropy" lines are unchanged (until NOVEL-01 is fixed, `./selftest` alone cannot detect a change in the final figure)
   - `./pin-check.sh`
   - for memory or UB findings: an ASan/UBSan build, `make <tool> CXXFLAGS='-std=c++11 -fopenmp -O1 -g -fsanitize=address,undefined -I/usr/include/jsoncpp'`, run on the reproduction inputs
7. **Commit** the fix and its regression test together in one commit:
   - Message form: `fix(<ID>): <what was wrong>`.
   - In the body: the affected source, the reproduction before and after, and the regression-test path.
8. **Update the tracker** in a separate commit, `audits: <ID> -> <STATE>`. Fill in:
   - **State:** `FORK-FIXED`
   - **Current fork status**
   - **Fork fix commit:** the SHA from step 7
   - **Regression test:** its path
   - **Verification:** the command and its result
   - **Last upstream-status check:** today's date
   - **Required next action**
   Then update the queue table and the summary counts at the top.
9. **Verify independently.** In a fresh clone of fork `master`, do a clean build, run every regression test and the selftest, and re-run the finding's Reproduce block, which must no longer show the `BUG:` lines. Then set `VERIFIED` and record the date.

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
| any confirmed state | the finding turns out to be spec-consistent, with the reason and evidence recorded | `NOT-A-BUG` (move the row; never delete it) |

## Periodic upstream-status check

For every row with an upstream issue or PR, re-query GitHub (step 2), apply the transitions above, and set **Last upstream-status check** to the date of the check. Record the stateReason for closed issues: `completed` does not prove a fix, so verify the code.

## Deduplication

Deduplicating files (identical copies of upstream sources, logs or reports in the audit archive) is housekeeping. It never removes or resolves a finding. Before removing any audit file, confirm that the tracker's evidence paths for every finding still resolve.
