# Resume note — paused 2026-10-12

Written at the owner's instruction before stopping. The audit is paused
mid-flight, not finished. Everything below is state a later session needs in
order to continue without redoing work.

**Nothing has been pushed.** `productionApprovalEnabled` is untouched and
remains `false`.

---

## 1. Batch 1 of verification: 14 of 15 lenses returned

Phase 2 verifies clustered candidates with up to three adversarial lenses each
(refute by spec and source, independent reproduction, impact and prior art).
Batch 1 covered the five highest-consequence clusters.

| Cluster | refute | repro | impact | Standing |
|---|---|---|---|---|
| `C01-multimmc-chained` | stands-with-corrections | yes | High | **Lenses disagree on severity; unsettled** |
| `C02-c-mode-hassessed` | stands-with-corrections | yes | High | **Not reopened** — prior F23 decision stands, see `DISPOSITIONS.md` |
| `C03-iid-verdict-not-in-status` | stands-with-corrections | yes | **Critical** | `ea_iid` half closed by the repair branch; `ea_restart -i` analogue **OPEN** |
| `C04-chisq-negative-df` | partially-refuted | **OUTSTANDING** | *(pending)* | Downgraded to Low; its proposed repair was harmful |
| `C05-restart-k-effective` | stands-with-corrections | yes | Medium | Upstream #195 open since 2022-08-23 |

**The one outstanding lens is `C04`'s reproduction.** Workflow run
`wf_ec9e4efc-9a3`; results are one `{"type":"result",…}` line per agent in
`~/.claude/projects/-Users-gmcas-repos-SP800-90B-EntropyAssessment/a3b01f18-b6b3-44a0-8c60-e2c7009fbc54/subagents/workflows/wf_ec9e4efc-9a3/journal.jsonl`.
Read that file before assuming anything about what returned.

`C04` cannot change the merge decision either way: it is a master-side
spec-consistency reporting item, now Low, and the refutation lens established
at high confidence that §5.2.1 says "do not apply the test" rather than "the
test fails", so the computed verdict already matches the requirement.

**Batches 2 and 3 have not run.** Script `verify3.js`, args
`{batch, items:[{key, lenses}]}`; cluster definitions in
`<shared-scratchpad>/wf/clusters.json`. Batch 2 is 9 clusters / 16 agents,
batch 3 is 9 clusters / 9 agents.

---

## 2. The repair-branch rebase is held — and what it rests on

**Not started.** Held at the owner's instruction pending `C04`.

When it runs: rebase `repair/2026-10-09-verified-defects` (`2d4b135`, 17
commits) onto `master` for linear history with no merge commit, then delete the
branch. `REGRESSION-LEDGER.md`'s **three tables are the merge record**, and the
branch lands on **Claim 1's evidence only**:

- **Claim 1 — 23 repairs whose guard was seen to fail**, each with the named
  guard and the assertion that failed against the unrepaired code. This is what
  the 25-of-28 mutation result and the pinned-literal checks are evidence for,
  and it is all they are evidence for.
- **Claim 2 — supported only by a guard that cannot fail, or by no guard:**
  C-01, N-07, N-08's `transpose_main.cpp` hunk, all of `ea_conditioning`, F14.
- **Claim 3 — guarded conditionally or partially:** F05, R-2, F09's binary
  path, F02 on `ea_restart`, F19's sha256-scope assertion, N-01 and N-02.

**Claim 2 and Claim 3 items are to be entered in the tracker as
`guard-rewrite-required` and left UNCLOSED** — in particular N-01 and N-02,
whose guards fail only below the 1,000,000-sample compliance minimum, and
F19's scope assertion, which both of the fork's two incompatible scope policies
satisfy.

The distinction the merge turns on: every production fix on the branch is
correct; two of its guards cannot fail. Land it on the code, not on the belief
that its suite will hold the code in place.

### Branch end-state plan (agreed, not yet executed)

Delete as obsolete: `fix/bitstring-gate-word-size` (holds the **withdrawn** F01
change), `fix/compression-min-test-blocks` and `fix/multimmc-binary-overread`
(both superseded on master by `c0ee84a` / `ed88de9` in a different form),
`origin/audits/2026-09-30-phase2-focused` (0 commits ahead). Cherry-pick the
466-line audit document from `origin/audits/2026-09-30-novel-findings` (2 ahead)
and drop its 1 MB PDF plus 7711-line source listing, then delete.

**`upstream/novel-03-restart-data-layout` is KEPT** by decision: it is the head
branch of **open upstream PR #273** at `usnistgov`, and deleting it on `origin`
would close that PR. Delete it only once #273 is merged or closed.

All remote operations — the `master` push and every `origin` branch deletion —
wait for explicit instruction.

---

## 3. Dead-guard sweep: 12 instances, and its resolution

`DEAD-GUARD-SWEEP.md`. Scope: tracked shell scripts in the fork at `master`
(32) and at `2d4b135` (40), and in TruePad at `HEAD` (28), plus every tracked
`Makefile`, `.mk`, `.yml`, `.yaml`, `dockerfile` for the class 4 sweep.
Detectors `deadguard.py`, `vacuous2.py`, `orfallback.py` are kept beside the
report.

- **Class 1** (assertions in a discarded-status heredoc under an unconditional
  PASS): instances 1-2, `sanitizer-restart-c01.sh` and
  `regression-input-identity.sh`, repair-branch only. Left for the guard
  rewrite.
- **Class 2** (a check skipped for want of its input, skip never reaching the
  exit status): instances 3-4 — **FIXED on master**.
- **Class 3** (vacuous success: the check passes by finding nothing to check):
  instances 5-7 in `regression-docs.sh` — **FIXED on master**.
- **Instance 8 WITHDRAWN**: `ios/scripts/check-notices.sh:124` already carries
  the floor assertion, at `:108-114`, 16 lines from its loop and so outside the
  detector's window.
- **Conditional lanes** 9-10: decided and recorded, not defects.
- **Class 4** (a stdout-writing `||` fallback on a command that prints *and*
  fails): instance 11, introduced by this sweep's own first fix and corrected;
  instance 12, `ios/scripts/gen-sbom.sh:249`, adjacent shape, **reported not
  fixed**.

### Stated resolution limits — 12 is a lower bound

Six categories these detectors could not see, recorded in full in the report:

1. **The ±8-line window failed in both directions.** It produced the
   `check-notices.sh` false positive, and the first version of `vacuous.py`
   **missed `regression-docs.sh` entirely** because `[ -z "${missing}" ]` fell
   inside the window and was mistaken for an emptiness check when it actually
   tests the failure accumulator.
2. **Shell only.** Perl (`compareresults.pl`), the Python harnesses, and
   TruePad's two load-bearing `.mjs` audit lanes were not scanned.
3. **Static only, so a tautological check is invisible.** Such guards exist
   here and were found by mutation testing instead: F09's binary-path check
   agrees with the tool on both sides of the repair, and F19's scope assertion
   is satisfied by both incompatible policies.
4. **Reachability never analysed** — half of why `sanitizer-restart-c01.sh` is
   dead is that no suite runs it.
5. **`set -e` used as a blanket dismissal** for four TruePad heredocs, without
   confirming each sits in plain statement position.
6. **Only the three fixed guards were mutation-tested.** Every "not an
   instance" means the path *reads* as fail-closed, not that it was broken and
   watched to fail.

---

## 4. Cross-repository note: `3f27453` in TruePad

**A commit was made to `~/repos/TruePad` from this session:** `3f27453` on
`master`, "audit: make the evidence manifest's own write a checked step",
with **only `audit-scripts/run-audit.sh` staged**. It adds a line-count check
on `EVIDENCE-SHA256SUMS.txt` so a failed or truncated hashing step cannot leave
an empty manifest while the script reports that every executed check passed.
Not pushed.

**That was a scope error.** `run-audit.sh` is TruePad's file and fixing it
belonged to the TruePad session, not to this fork audit. The commit is left in
place rather than reverted, on instruction. **The TruePad session should take
ownership of it**, review it, and decide whether to keep, amend or drop it.
Instance 12 (`gen-sbom.sh:249`) was deliberately left unfixed and is TruePad's
to triage.

TruePad's working tree carried unrelated pre-existing modifications before this
work began — `PRE-USB-RNG-TODO.md`, five `TruePadSPTTests` files, and untracked
`.github/workflows/entropy-tools.yml`, `tests/pinned-branch-heads.test.ts`,
`tests/sp800-90b-real-tool-pipeline.test.ts`. All were left untouched and none
is in `3f27453`. An earlier report in this session put that count at one file;
that figure was wrong.

**No further work in `~/repos/TruePad` from this session.**

---

## 5. Uncommitted state in this repository

Committed here: this note only.

Still uncommitted in the working tree:

- **`cpp/selftest/` guard fixes**, 4 files, +80/-8 — `regression-notrun.sh`,
  `regression-restart.sh`, `run-all-checks.sh`, `regression-docs.sh`. Each was
  demonstrated failing before passing; before/after logs are in
  `logs/deadguard/`.
- **The rest of this audit directory** — `REPORT.md` is **not yet written**.
  Present: `README`, `BASELINE`, `COVERAGE` (155 rows), `EXCLUSION-MAP` (122
  prior findings rechecked), `CLUSTERS` (119 candidates → 23 clusters),
  `REGRESSION-LEDGER` (the three tables), `ORCHESTRATOR-CHECKS` (OC-1 to OC-3),
  `DEAD-GUARD-SWEEP`, `DISPOSITIONS`, plus `generators/`, `logs/`, and the three
  detector scripts. Still to write: `REPORT.md`, `COMMANDS.md`, `results.json`,
  `MANIFEST.sha256`.

### Trap: `.gitignore` will silently omit the evidence

`.gitignore:2` ignores `*.log` and `:13` ignores `*.json`. So the audit's
`logs/` directory — including every before/after log behind the guard fixes in
`logs/deadguard/` — and a future `results.json` are **invisible to a plain
`git add`**. The 2026-10-09 audit's logs are tracked, so they were force-added.
Whoever commits this deliverable must use `git add -f` for `logs/` and
`results.json`, or the evidence for every claim in the report will be left out
of the commit without any warning.

## 6. Where the working material is

Shared scratchpad, reused across sessions, **do not recreate**:

```
/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/2744130e-74f7-4e44-aae2-a42d4e4f034c/scratchpad
```

`BRIEF.md` (the shared auditor brief), `wt/{master,repair,upstream,master-asan}`
with built binaries, `fixtures/valid` (1M-sample deterministic set, seed
`0x90b20261009`), `spec/`, `diffs/`, `agents/<name>/` (each finder's `LOG.md`
and `REPORT.md`), `wf/{candidates-all.json,clusters.json,ledgers.json}`.

Phase 1 runs: `wf_ba0929a6-7a7` (4 finders returned) and `wf_9ffc7e92-ca9` (the
7 resumed finders). A killed agent's work usually survives in
`agents/<name>/` — harvest before re-running, as was done for
`estimators-mcv-collision-markov-compression`.

Free disk is tight (~12 GB). Cap agent file creation at ~1 GB.
