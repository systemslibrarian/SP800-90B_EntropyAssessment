# Dead-guard sweep — every script that can exit 0 without its check running

Commissioned after two instances of one pattern turned up in the repair
branch, on the reasoning that the pattern is a sweep and not two fixes. Scope:
every tracked shell script in the fork at `master` (`f069898`, 32 scripts) and
at `repair/2026-10-09-verified-defects` (`2d4b135`, 40 scripts), and every
tracked shell script in TruePad at `HEAD` (28 scripts).

The classes 2 and 3 guards on `master` have since been **fixed**; see
"Fixes applied" at the end. The two class 1 guards live only on the unmerged
repair branch and are left for its guard rewrite.

## Method

Two static detectors, then every flag read by hand. The detectors
(`deadguard.py`, `vacuous2.py`, kept with this report) flag:

- an interpreter heredoc or verification command whose exit status is never
  read, in a script without `set -e`;
- a script whose last command is an unconditional success message, with no
  `set -e`;
- a check skipped when its input is absent, where the skip does not reach the
  exit status;
- a check driven by an extraction that can return the empty set, with no
  assertion on the size of that set;
- a verification command upstream of a pipe without `pipefail`.

75 flags from the first detector and 23 from the second, across 40 files.
Reading them resolved to **7 real dead guards in 5 scripts**, plus **2
conditional-lane observations** (an eighth, `check-notices.sh:124`, was
reported in the first pass and is withdrawn below). The rest were false positives, and the reasons
they were false are recorded below so that the next sweep does not re-litigate
them.

A note on what counts. `set -e` was decisive in most dismissals: an unchecked
verification heredoc in a script with `set -e` is not a dead guard, because
errexit aborts the script on the heredoc's nonzero exit. 25 of TruePad's 28
scripts set `-e`; only 3 do not. In the fork, the `cpp/selftest` scripts
deliberately do not use `set -e` — they use a `fails` counter and
`exit 1` when it is nonzero — which is a sound idiom with one specific hole,
described in class 2 below.

---

## Class 1 — assertions in a heredoc whose status is discarded, under an unconditional PASS

> **STALE AND CORRECTED, 2026-10-21 (`OC-64`).** This section says both
> instances are "on the repair branch" and therefore not live. **The
> 2026-10-15 merge (`d226f18`) put both on `master`, and
> `regression-input-identity.sh` is in the ENFORCED suite**, counted toward
> "22 passed" every run. Both were still live today and both were measured
> producing a false pass: `regression-input-identity.sh` printed an
> `AssertionError` traceback and then `PASS` with exit 0 when its
> `sha256Scope` assertion was mutated, and `sanitizer-restart-c01.sh` did the
> same when driven with a stand-in writing `errorLevel = 1` — the first thing
> it claims to catch. Repaired in `OC-64`.
>
> **The stale record is what let them sit there.** A sweep that records a
> finding's location as a branch has to be re-read when that branch merges,
> and nothing re-read this one. The "repair only" column below is wrong for
> rows 1 and 2.

The originally reported pattern. **Two instances, both on the repair branch,
and no others in either repository.**

### 1. `cpp/selftest/sanitizer-restart-c01.sh` (repair branch only)

`set -u` at line 6; no `set -e`. Line 32 opens
`python3 - "$work/result.json" <<'PY'` carrying four assertions
(`errorLevel == 0`, finiteness of `h_r`/`h_c`/`h_i`, `h_i == 0.8`). Its exit
status is never read. Line 42 is `echo "sanitizer-restart-c01: PASS"`, whose own
status becomes the script's. Any failing assertion prints a Python traceback
and the script then prints PASS and exits 0.

This script guards **C-01**, and it carries three further defects that compound:
it passes against an ordinary non-sanitizer release build of the defective code;
it passed against an unrepaired ASan build before `b3db7ab` added
`alloc_dealloc_mismatch=1`; and it is in no inventory, so `run-all-checks.sh`
never runs it at all.

### 2. `cpp/selftest/regression-input-identity.sh` (repair branch only)

Same shape. `set -u` at line 9, no `set -e`. Line 58 opens
`python3 - "$work/result.json" "$a_hash" "$b_hash" "$(hash_file ...)" <<'PY'`
carrying six assertions (including `doc["sha256"] == sys.argv[2]` and
`doc["sha256Scope"] == "assessed-sample-bytes"`, which are the whole point of
the test). Status never read. Line 70 prints PASS unconditionally.

Reverting the production hunk yields `AssertionError` followed by `PASS` and
exit 0. This script is the only guard on **N-07**.

Note that both scripts *do* check status elsewhere — `make ... || exit 2`, and
an explicit `rc=$?` test after the tool run. The author was status-conscious
and missed exactly the verification step.

### Not instances

Four unchecked verification heredocs in TruePad are under `set -e`, which
catches them: `ios/scripts/ci-ui-tests.sh:23` and `:87`,
`android/tools/selftest-dependency-verification.sh:25`,
`android/tools/verify-instrumentation.sh:63`. Likewise
`repairs/2026-10-09-ind-02/rerun.sh:45` in the fork. Unchecked heredocs that
only *generate data* (nine of them) are not guards; a failed generator makes the
following comparison fail, which is counted.

---

## Class 2 — a check skipped for want of its input, where the skip does not reach the exit status

The `fails`-counter idiom is sound when every check either passes or increments
the counter. It has one hole: a check that is **skipped** increments nothing, so
the script reports PASS having verified less than it claims.

### 3. `cpp/selftest/regression-notrun.sh:43-60` (master and repair)

```sh
if [ -f "${gen}" ] && python3 "${gen}" 100 11 "${work}/db100.bin" >/dev/null 2>&1; then
        ... two checks, each able to increment fails ...
else
        note "de Bruijn case:" "skipped (generator unavailable)"
fi
```

The `else` branch notes the skip on stdout and does **not** increment `fails`.
This is the script's only 1,000,000-sample case — the compliant-input half of
the **F05** guard — and the comment three lines above it says "The skip must be
visible", which it is on stdout and is not in the exit status.

### 4. `cpp/selftest/regression-restart.sh:157` (master), `:227` (repair)

Identical construction guarding **R-2**: the de Bruijn 1,000,000-sample case in
which the LRS estimate must decline and its `-1` sentinel must not be folded
into `H_r`. Generator absent, block skipped, `fails` unchanged, PASS.

`gen` in both scripts points at
`audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py`.
**That file is present at `f069898`, so both checks do run today** — I verified
it with `git cat-file -e`. The defect is that the guard's existence is
contingent on a file inside a frozen audit archive: prune or move the archive
and the suite stays green while two 1,000,000-sample checks evaporate.

### Not instances

`regression-minsize.sh:61` looks identical but its `else` branch increments
`fails` — fail-closed. `regression-multimmc.sh:48` exits 2 when its generators
are missing — fail-safe, and distinguishable from a test failure.

---

## Class 3 — vacuous success: the check passes by finding nothing to check

A loop whose iteration set comes from an extraction, where the loop body holds
the only code that can record a failure, and nothing asserts that the set is
non-empty. If the extraction stops matching, zero iterations run and the script
reports success.

### 5, 6, 7. `cpp/selftest/regression-docs.sh:39`, `:47`, `:63` (master and repair)

```sh
shas=$( { grep -ohE 'Commit [0-9a-f]{7,40}\.' NOTICE | sed ...
          grep -ohE '^- \*\*Fork fix commit:\*\* `[0-9a-f]{7,40}`' "${TRACKER}" | grep -ohE '[0-9a-f]{7,40}'
          grep -ohE '`87c104d[0-9a-f]*`' NOTICE "${TRACKER}" | tr -d '`'
        } | sort -u )
for h in ${shas}; do
    git cat-file -e "${h}^{commit}" 2>/dev/null || missing="${missing} ${h}"
done
if [ -z "${missing}" ]; then note "every commit SHA in NOTICE and the tracker resolves:" "yes"
```

Three extraction-driven loops in this script — commit SHAs (`:39`), referenced
file paths (`:47`), markdown links (`:63`) — and none asserts a minimum count.
Reword `NOTICE`'s "Commit <sha>." phrasing, or rename the tracker's
"**Fork fix commit:**" field, and `shas` is empty, `missing` stays empty, and
the script announces that *every* commit SHA resolves. The failure accumulator
being empty is indistinguishable from there having been nothing to accumulate.

This is a mechanism behind the separately reported
`build-portability-harness-docs-10`, which said this script "cannot pass on the
reference platform, and has seven further silent-skip or scope gaps".

The repository already contains the fix for this shape:
`verify-fixture-inventory.sh:74` asserts `[ "$input_count" -ne 11 ] || [ "$reference_count" -ne 11 ]`
and fails if the count is wrong, rather than trusting a loop to have run.

### 8. `ios/scripts/check-notices.sh:124` (TruePad) — **withdrawn, not an instance**

Reported in the first pass as a weaker instance. That was wrong, and the
correction matters because it is the opposite conclusion: the script already
carries exactly the floor assertion this class calls for, sixteen lines above
the loop at `:108-114`:

```sh
PATCH_FILE_COUNT="$(printf '%s\n' "$PATCHED_FILES" | grep -c . | tr -d ' ')"
if [ "$PATCH_FILE_COUNT" -gt 0 ]; then
    pass "the patch probe works ($PATCH_FILE_COUNT patched file(s) seen)"
else
    fail "no patched files parsed -- this probe is not working"
fi
```

An empty extraction fails with "this probe is not working". The detector missed
it because its emptiness-check window was ±8 lines and the probe sits 16 lines
away. **Decision: an empty set is not treated as legitimate here, the script
already enforces that, and nothing is changed.**

### Not instances

Fourteen further loops flagged by the detector iterate over **literal lists**
(`for tool in "${non_iid}" "${ea_iid}"`, `for s in "${m1_sample}" "${m2_sample}"`,
`TOOLS="ea_non_iid ea_iid"`), which cannot silently empty under `set -u`.
`verify-fixture-inventory.sh:95` and `:100` glob over a directory but carry
`[ -e "$candidate" ] || { ...; exit 1; }` for the no-match case.

---

## Conditional lanes — exit 0 does not mean "everything ran"

Not dead guards, but the same hazard one level up: a caller keying on exit
status cannot tell a full run from a partial one.

### 9. `audit-scripts/run-audit.sh` (TruePad)

Correctly guarded internally — `run_check` captures each status, increments
`failures`, and the script exits 1 when `failures > 0`. But lanes whose
toolchain is absent are recorded via `not_run` as NOT RUN rows in `SUMMARY.md`
and do not affect the exit status. A `--quick` run and a `--full` run with
Playwright, swtpm, Java, adb, swift and xcodebuild all missing both exit 0. The
final line does tell a human to "review NOT RUN and NOT PROVED rows before
making any claim" — which is honest, and is the right disclosure — but CI
treating exit 0 as "the audit passed" cannot see the difference.

Also unguarded in that script: the `find … | xargs shasum -a 256 >
EVIDENCE-SHA256SUMS.txt` at the end. If it fails, the evidence manifest is
truncated or empty and the script still reports that all executed checks
passed.

### 10. `ios/scripts/check-app-project.sh` (TruePad)

No `set -e`, but a `FAIL` counter with `exit "$FAIL"`. Its BINARY half is
skipped when no `.app` argument is given, so running it with no argument exits
0 having made none of the binary assertions. This one is **documented** — the
header says the binary half is "Skipped, loudly, if not" — and the same header
shows the author already understood this class of problem: "every symbol check
below therefore matches a PRECISE name, and the probes prove they can fire
before their silence is trusted." Listed for completeness, not as a defect.

---

## Summary

| # | Script | Branch / repo | Class | Guards |
|---|---|---|---|---|
| 1 | `cpp/selftest/sanitizer-restart-c01.sh` | ~~repair only~~ **ON MASTER since `d226f18`; REPAIRED `OC-64`** | 1 | C-01 |
| 2 | `cpp/selftest/regression-input-identity.sh` | ~~repair only~~ **ON MASTER since `d226f18`, in the ENFORCED SUITE; REPAIRED `OC-64`** | 1 | N-07 |
| 3 | `cpp/selftest/regression-notrun.sh` | master + repair | 2 | F05 (1M case) |
| 4 | `cpp/selftest/regression-restart.sh` | master + repair | 2 | R-2 (1M case) |
| 5 | `cpp/selftest/regression-docs.sh:39` | master + repair | 3 | commit SHAs in NOTICE/tracker |
| 6 | `cpp/selftest/regression-docs.sh:47` | master + repair | 3 | referenced file paths |
| 7 | `cpp/selftest/regression-docs.sh:63` | master + repair | 3 | markdown links |
| ~~8~~ | `ios/scripts/check-notices.sh:124` | TruePad | — | **withdrawn**: already guarded by the `PATCH_FILE_COUNT` probe at `:108` |
| 9 | `audit-scripts/run-audit.sh` | TruePad | lane | whole audit's exit status |
| 10 | `ios/scripts/check-app-project.sh` | TruePad | lane (documented) | iOS binary assertions |
| 11 | `audit-scripts/run-audit.sh` | TruePad | 4 | the evidence manifest — introduced by this sweep's own first fix, corrected in `3f27453` |
| 12 | `ios/scripts/gen-sbom.sh:249` | TruePad | 4 (adjacent) | the vendored patch's digest in the SBOM |

The two scripts in class 1 are the two already known. The sweep's new material
is classes 2 and 3 — **four more dead guards on `master` itself**, where the
earlier finding had been read as a repair-branch problem only — and class 4,
which this sweep introduced into TruePad and then caught.

These counts are a lower bound. See "The sweep's resolution" for the six
categories of instance these detectors could not see, including tautological
checks, non-shell harnesses, and whether a script is reachable at all.

## The pattern that is already right

`cpp/selftest/regression-272.sh` is the reference implementation. It injects
each mutant with `perl -0pi`, and then — instead of trusting the substitution —
verifies it took effect:

```sh
if ! grep -q 'regression-272 mutant 1' "${work}/m1/non_iid_main.cpp"; then
        note "mutant 1:" "SOURCE PATTERN NOT FOUND — update this script"
        fails=$((fails + 1))
```

A mutation control that cannot confirm it mutated anything is vacuous, and this
script knows it. Every dead guard above is an instance of the same question
left unasked.


---

---

## Class 4 — a `||` fallback that prints, on a command that prints *and* fails

### 11. `audit-scripts/run-audit.sh` — introduced by this sweep's own first fix, since corrected

Recorded as a finding in its own right rather than as a corrected line, because
it is this sweep's subject reproduced one level down: the guard written to
catch vacuity was itself vacuous, and only the before/after demonstration
exposed it.

**Mechanism.** `grep -c .` on an empty file prints `0` on stdout **and exits
1**. The two are independent: the nonzero status is not a signal that nothing
was printed. So in

```sh
manifest_lines="$(grep -c . "$file" 2>/dev/null || echo 0)"
```

the fallback fires *alongside* the successful print. Command substitution
captures both, and `manifest_lines` becomes `"0\n0"` — three bytes, measured:

```
$ x=$(grep -c . /dev/null || echo 0);  printf '[%s] %s bytes\n' "$x" ...   ->  [0
0] 3 bytes
$ y=$(grep -c . /dev/null || true);    ...                                  ->  [0] 1 bytes
$ z=$(grep -c . /dev/null 2>/dev/null) || z=0; ...                          ->  [0] 1 bytes
```

`[[ "0\n0" -lt 1 ]]` then raises `arithmetic syntax error (error token is
"0")`, the `if` evaluates **false**, and control falls through to the success
branch. The check reported PASS on precisely the input it existed to reject.

Corrected by assigning from `grep` and applying `||` only to the command's
failure, so exactly one value is ever produced:

```sh
manifest_lines=$(grep -c . "$file" 2>/dev/null) || manifest_lines=0
```

Committed as TruePad `3f27453`, which records the mechanism in its message so
the broken form is not reintroduced.

### Sweep for the same shape across both repositories — no further instances

`orfallback.py` (kept with this report) looks for a `||` fallback that itself
writes to stdout, applied to a command that can print and still exit nonzero:
`grep -c`, `diff`, `cmp`, `comm`, `find`, `timeout`, `make`, `jq`, and any
`python3 -c`/`perl -e`/`node -e` that prints before failing. Scope: tracked
shell scripts in the fork at `master` and at `2d4b135`, tracked shell scripts in
TruePad, plus every tracked `Makefile`, `.mk`, `.yml`, `.yaml`, `dockerfile`.

**No instance of the broken shape exists in either repository.** The three
candidate families all turned out to be correct, and each was checked by
execution rather than by reading:

| Family | Sites | Verdict |
|---|---|---|
| `"$(grep -c … \|\| true)"` | 8, all TruePad: `check-app-project.sh:197,204,211`, `inspect-release-binary.sh:167`, `set-build-number.sh:26`, `ci-normalize-avd.sh:91`, `physical-device-check.sh:119,120` | **Correct.** `true` writes nothing, so the captured value stays `0`. This is the right idiom for `grep -c` and must not be "fixed" into `\|\| echo 0`. |
| `$(shell brew --prefix X 2>/dev/null \|\| echo <default>)` | 3, fork `cpp/Makefile:23,49,50` | **Correct.** Measured: `brew --prefix` on an unknown formula writes 0 bytes to stdout and exits 1, so the fallback is the only output. |
| `compareresults.pl:87` | 1 | Not shell — a Perl regex alternation. |

### 12. `ios/scripts/gen-sbom.sh:249` — adjacent shape, reported not fixed

Not the exact shape (the failing command prints nothing), but the same family
and worth listing: a `||` fallback converting a missing input into a value that
reads as legitimate inside an artifact reviewers trust.

```sh
PATCH_DIGEST="$(file_digest "$VENDOR/EXPECTED-PATCH.diff" 2>/dev/null || echo "")"
```

`file_digest` is `shasum -a 256 "$1" | awk '{print $1}'` under `set -euo
pipefail`, so a missing `EXPECTED-PATCH.diff` fails the pipeline; `|| echo ""`
catches it, which also stops `set -e` aborting, and `PATCH_DIGEST` becomes
empty. It is emitted unchecked at `:314` as
`{ "name": "truepad:patch-digest", "value": "" }`. Because `gen-sbom.sh --check`
compares a regenerated SBOM against the committed one, a missing patch file
yields empty on both sides and the comparison passes. The vendored patch's
digest — the thing that detects a changed patch — can therefore be absent while
the SBOM check reports agreement. **Not fixed in this pass.**

---

# The sweep's resolution — what these detectors could not see

"7 dead guards in 5 scripts" is a **lower bound from two static detectors plus
hand review**, not an exhaustive count. The false positive at
`check-notices.sh:124` showed the mechanism: the emptiness-check window was
±8 lines and the floor assertion sat 16 lines from its loop, so a real guard
read as absent. The same window fails in the other, worse direction too — the
first version of `vacuous.py` **missed** `regression-docs.sh` entirely because
`[ -z "${missing}" ]` fell inside the window and was taken for an emptiness
check, when it actually tests the failure accumulator rather than the extracted
set. One window, both error directions. A later reader should assume
instances remain.

Specifically unexamined or unexaminable by this method:

1. **Window-dependent misses.** Any floor or emptiness assertion more than 8
   lines from the loop it protects reads as absent (false positive), and any
   unrelated count test within 8 lines reads as present (false negative). Only
   the second version of the detector required the check to name the extracted
   variable, and only `regression-docs.sh` was re-found that way. Scripts whose
   guards sit at a distance were resolved by hand or not at all.

2. **Shell only.** Tracked `.sh` files, plus `Makefile`/`.yml`/`dockerfile` for
   the class 4 sweep. **Not scanned:** Perl (`compareresults.pl`, which
   `build-portability-harness-docs-3` separately reports as exiting 0 on an
   empty reference file), the Python harnesses, and TruePad's Node checks —
   `audit-scripts/independent-otp-checks.mjs` and
   `source-and-supply-chain-checks.mjs` are load-bearing audit lanes in which a
   swallowed `catch`, an assertion inside a callback that is never invoked, or a
   `for` over an empty array would be exactly this defect in another language.
   TruePad also has an **untracked** `.github/workflows/entropy-tools.yml`,
   outside the tracked-content scope used here.

3. **Static only — a tautological check is invisible.** These detectors ask
   whether a check *can run*, never whether running it *could fail*. A guard
   that executes but compares a value with itself, or against an expectation
   derived from the same code under test, passes every detector here. Such
   guards exist in this repository and were found by a different method
   entirely — mutation testing, by the `regression-quality-reconciliation`
   dimension: F09's binary-path check "agrees with the tool on both sides of
   the repair", and F19's sha256-scope assertion "is satisfied by both of the
   fork's two incompatible scope policies". Neither would ever appear in this
   sweep.

4. **Reachability was not analysed.** `sanitizer-restart-c01.sh` is dead partly
   because *no suite ever runs it*, which is a property of the inventory, not of
   the script. No detector here asks whether every script is reachable from
   `run-all-checks.sh` or from CI. That gap is what `IND-02` addresses for
   `regression-*.sh` only, and `regression-quality-reconciliation-3` reports
   three harness programs still outside it.

5. **`set -e` was used as a blanket dismissal.** Four unchecked verification
   heredocs in TruePad were dismissed because their scripts set `-e`. That is
   sound for a plain statement, but errexit does **not** abort for a command in
   a condition, in a `&&`/`||` chain, in a subshell whose status is discarded,
   or inside a function invoked where errexit is suppressed. Each of those four
   sites was dismissed on the `set -e` line alone, without confirming it sits in
   plain statement position.

6. **Only the three fixed guards were mutation-tested.** For everything listed
   as "not an instance", the evidence is that the code path *reads* as
   fail-closed. That is not the same as having broken what it guards and watched
   it fail. The three fixes in this pass were each demonstrated failing before
   passing; the dismissals were not.

# Fixes applied

Changed on `master` after the sweep, each shown failing before it passes. Raw
logs under `logs/deadguard/`.

## Decision: a missing generator is a failure to run, reported as such

The question the skip raised was whether an absent generator is a failure or a
documented NOT RUN. **Decided: a failure to run** — the suite's claim is that
these repairs are guarded, and a guard that did not execute supports no part of
that claim, so the suite must not report success. It is reported *separately*
from a regression because the cause is environmental and tells the operator to
fix the environment rather than the code. `exit 2` carries it, which is the
convention `regression-multimmc.sh:48` and `verify-fixture-inventory.sh`
already use for an absent prerequisite.

`regression-notrun.sh` and `regression-restart.sh` gain a `cannot_run` counter
alongside `fails`, and a verdict that distinguishes three outcomes. The de
Bruijn branch now reads `COULD NOT RUN (no generator at …)` and increments it.

`run-all-checks.sh` classifies `exit 2` as COULD NOT RUN, counts it apart from
FAIL, prints a `could-not-run:` list, and **exits nonzero for it**. Its summary
line stays byte-identical when the count is zero, because the repair branch's
`harness-inventory-mutation-test.sh` matches that line exactly.

| Condition | Pre-fix | Post-fix |
|---|---|---|
| `regression-restart.sh`, generator absent | `skipped (generator unavailable)` → **PASS, exit 0** | `COULD NOT RUN (1 case(s) had no input; 0 of the cases that ran failed)` → **exit 2** |
| `regression-restart.sh`, generator present | PASS, exit 0 | PASS, exit 0 — `H_r 6.583332`, all four R-2 checks run (unchanged) |
| `regression-notrun.sh`, generator absent | `skipped (generator unavailable)` → **PASS, exit 0** | `COULD NOT RUN` → **exit 2** |
| `regression-notrun.sh`, generator present | PASS, exit 0 | PASS, exit 0 (unchanged) |
| `run-all-checks.sh`, a script exits 2 | `FAIL (exit 2)`, lumped with regressions | `COULD NOT RUN (exit 2)`, counted apart, `could-not-run:` list, exit 1 |
| `run-all-checks.sh`, all pass | `run-all-checks: 3 passed, 0 failed (1 regression scripts discovered)` | byte-identical |

## Floors on every extraction in `regression-docs.sh`

Five extractions now declare the minimum they must find, via a `floor` helper
that reports the count it saw. **A floor, not an exact count**: these documents
grow, and a hand-maintained exact total is the defect `audits/README.md` already
demonstrates (585 claimed against 739 actual).
`verify-fixture-inventory.sh` can assert an exact 11/11 because its corpus is
frozen by design; documentation references are not. Each floor sits well under
the count at `f069898`, recorded in a comment beside it.

| Extraction | Count at `f069898` | Floor |
|---|---:|---:|
| commit SHAs in NOTICE and the tracker | 22 | 10 |
| repo paths referenced in the docs | 64 | 20 |
| markdown link targets | 11 | 5 |
| regression scripts the tracker names | 14 | 8 |
| pinned figures across the docs | 2 | 1 |

Shown failing before passing, by renaming the tracker's
`**Fork fix commit:**` field and NOTICE's `Commit <sha>.` phrasing so the
extraction collapsed from 22 items to 0:

- **pre-fix:** `every commit SHA in NOTICE and the tracker resolves: yes` → **PASS, exit 0**
- **post-fix:** `extracted only 0 item(s), floor is 10 - the pattern no longer matches, so this check verifies nothing` → **exit 1**

One pre-existing failure is unrelated to this change and was present before it:
in a checkout with no built binaries, `pinned figures matching neither
reference nor build` fails because `observed` is empty. Pre-fix and post-fix
both exit 1 with that same single failing check, which independently reproduces
`build-portability-harness-docs-10` ("cannot pass on the reference platform").
Not fixed here — it belongs to that finding.

## TruePad conditional lanes — decided

**`run-audit.sh` exiting 0 whether 14 lanes ran or 4: accepted, not a defect.**
The profile-driven design is the point of `--quick`, lanes are gated on
toolchain availability, `not_run` records every skipped lane in `SUMMARY.md`,
and the closing line tells the reader to review the NOT RUN and NOT PROVED rows
before making any claim. The disclosure is honest and in the right place.
Nothing in the repository parses its stdout — `package.json:20` invokes it and
consumes only the exit status. The residual hazard is a CI that reads exit 0 as
"the audit passed"; that is a property of such a caller, not of this script, and
is recorded here rather than papered over by failing a deliberately partial run.

**`run-audit.sh`'s unchecked `find | xargs shasum`: a real defect, fixed.** The
manifest is what a reviewer checks the rest of the evidence directory against,
so writing it is a check and not a formality. A failed or truncated hashing step
left an empty manifest while the script still reported that every executed check
had passed.

### The first attempt at this fix was itself a dead guard

Worth recording, because it is the same mistake one level down and the
demonstration is what caught it. The first version read:

```sh
manifest_lines="$(grep -c . "$file" 2>/dev/null || echo 0)"
if [[ "$manifest_lines" -lt 1 ]]; then ...
```

`grep -c .` on an empty file prints `0` **and exits 1**, so the `|| echo 0`
fallback also fired, `manifest_lines` became `"0\n0"`, `[[ … -lt 1 ]]` raised
`arithmetic syntax error`, the `if` was false, and the script fell through to
reporting success. A guard against vacuity that was itself vacuous. Corrected
to:

```sh
manifest_lines=$(grep -c . "$file" 2>/dev/null) || manifest_lines=0
```

| Condition | Pre-fix | First attempt | Corrected |
|---|---|---|---|
| hashing step fails, manifest empty (0 bytes) | "All executed checks passed", **exit 0** | arithmetic error, "All executed checks passed", **exit 0** | `evidence manifest is empty or was not written`, **exit 1** |
| hashing step works | exit 0 | — | exit 0, 2 files hashed |

Evidentiary limit: this was demonstrated with a harness replicating the exact
block, not an end-to-end `--quick` run, which needs `npm ci` and the full
vitest suite. The block under test is reproduced verbatim from the script.

That change is in TruePad's working tree and is **not committed**. TruePad's
tree also carried one unrelated pre-existing edit before this work began
(`ios/.../SourceClaimImportTests.swift`), which was left untouched.
