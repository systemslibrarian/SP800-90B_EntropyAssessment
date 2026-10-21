# What is left — closing inventory

Date: **2026-10-20**, rewritten after the Windows measurement (`OC-48`) and
again after an outside read-only audit (`OC-49`–`OC-52`). State:
`master` at the commit adding this revision. Written to be read cold, by
someone who has not followed the work.

**An outside read-only audit, 2026-10-20, pinned at fork `769115d8`,
reproduced defects in this tree and in this audit's own oracles.** Everything
it reported that was checked here held, with one correction in the fork's
favour: Windows now builds. Its highest-priority item was a **data-destroying
regression introduced by one of this audit's own repairs** — `-o <input>` with
the output path equal to the input replaced a 1,000,000-byte capture with a
602-byte error report before a single sample was read (`A05`). Repaired, with
18 alias cases shown refused and shown failing against the pre-fix build. In
January the input is a capture that cannot be recreated, so that item mattered
more than everything else on the list put together.

**Where this revision leaves it.** `C18` is **repaired**, not merely
characterised: the Windows blocker moved to `seed()`, which is now **measured**
rather than predicted. `A02` and `A06` are **closed**. The remaining software
items are `C24` (portability, repairable here) and `seed()` (an entropy path,
the owner's call). The needs-nothing bucket is **not** empty.

**The headline changed two revisions ago.** The version before that said the fork
had reached the hardware wall and the first bucket was down to one small item.
Measuring Windows **reopened the software work**: it confirmed a defect that
had been a reading of the source for a year (`C18`), and it found a new one in
two repairs this audit itself authored (`C24`). Neither is a wrong figure —
both are fail-closed — but neither existed as a *measured* item before today,
and the first bucket is no longer nearly empty.

## What this repository is, in four sentences

It is a patched fork of NIST's SP 800-90B reference implementation, which
estimates the min-entropy of a noise source. The figure it reports prices the
output length of a one-time pad in a separate tool, so the number has to be
defensible rather than merely produced. Three executables are built and
supported — `ea_non_iid`, `ea_iid`, `ea_restart`; `ea_conditioning` and
`ea_transpose` are deliberately not. **Every repair in this fork is
self-authored and unreviewed, the owner has decided there will be no
independent human review and that nothing will be reported upstream, and no
physical noise source has been measured.**

## The two numbers, and how to get them

A figure from this fork is only interpretable with its provenance and its floor.

```sh
# 1. which tree is this binary from?
tools/build-provenance-canary.sh cpp/ea_iid          # expect TREE REPAIRED
# 2. the assessment
cpp/ea_non_iid -i -a -q -o report.json <capture.bin> <bits_per_symbol>
# 3. the floor, with every subtracted term named. At width 1 this prints
#    CERTIFIED FLOOR; above width 1 it prints EVALUATED MARGIN (NOT A FLOOR),
#    because the C01/F10 term is a measurement there and not a bound (A02).
python3 audits/2026-10-11-independent-audit/oracles/entropy_floor.py report.json
# 4. if a restart dataset exists, the acceptance decision -- NOT a subtraction
cpp/ea_restart -i -v -o restart.json <restart.bin> <bits_per_symbol> <H_I>/symbol
python3 audits/2026-10-11-independent-audit/oracles/restart_decision_exact.py restart.json
```

The reference tool's own unrepaired figure must be reportable alongside the
fork's, with the difference explained. Build it from tag
`unrepaired-reference-2026-10-15`; the steps, and the two gaps in the
instructions the tag itself carries, are in
[docs/TAG-unrepaired-reference-2026-10-15.md](../../docs/TAG-unrepaired-reference-2026-10-15.md).

## Needs nothing — can be done here, now

**This bucket is empty.**

Every item that was in it has closed, and the closures are below with their
evidence. **The fork has reached the hardware wall: the next thing that moves
it is the device in January 2027.** The two items that remain anywhere are an
owner decision each, and one of them is unreachable for this device by proof.

This claim was made once, withdrawn within the hour when rule 9 — written
earlier the same day — found `C22a`'s constant to be an unchecked grid maximum,
and is restored now on the measurement that closed it: the argmax is interior
in every swept axis, and extending the one arbitrary axis nine orders left it
bit-identical (`OC-63`). The withdrawal is left in the record. *"The bucket is
empty"* should cost something to say, and this time it did.

**`C22a`'s boundary question has left this bucket: measured and closed**
(`OC-63`). The constant `c` = 0.4991 is a supremum, not a lower bound on one,
so `C22a` is a bound and both floor readings are certified floors at width 1
again.

**`C22c` has left this bucket: the factor was found and the record is
vindicated** (`OC-62`). The consistent 4.5–4.9× ratio was a **mechanism**, as a
consistent ratio always is: the two derivations were bounding **different
estimators**. The tabulated term is the **Compression** ceiling — `com_exp` is
stationary at `p = 1/64`, so the sensitivity is quadratic on the approach to
its cap and `σ_max` carries a `log2(num_blocks)` that makes the ratio *drift* —
while the derivation it was compared against computed the **Collision** family,
which is 4.3–4.6× smaller. Everything checkable without reimplementing the
production compression solve now reproduces, including the collision family's
entire ceiling to 0.07 %. **No entropy is recovered, because none was being
thrown away**, and `C22c` is a derived ceiling and therefore a **bound**, so
both readings are certified floors at width 1 again.

**`C24` has left this bucket: it is repaired** (`OC-57`). `writeJsonReport` uses
`MoveFileEx` with `MOVEFILE_REPLACE_EXISTING` under `_WIN32`, and the Windows
job now gates on the repair rather than on the defect: the current writer
replaces an existing report there, the old bare-rename writer still fails
beside it with `errno 17` as the contrast, and every tool puts its report in
place. The POSIX path is untouched.

**`F13` has left it: closed as UNREACHABLE, not repaired** (`OC-58`).
Reachability came before repair and settled it. `p_global > 0` already excludes
a NaN `p_global`, since `NaN > 0` is false; the only other NaN source is `0/0`
in the variance term, which needs `N == 1` exactly, and `MIN_SIZE` is
1,000,000 on every supported path. 73,745 evaluations over the supported
domain produce no NaN, and **the same probe fires at `N == 1`**, so its silence
is a measurement rather than blindness. Both sites now carry a comment saying
the argument order is load-bearing and must not be swapped, because that is
where the next person will look.

**`C06` was listed in two buckets at once** — here and under "will not be
done". That was double-counting: it concerns `ea_conditioning`, which is
deliberately not built, so it belongs only in the last bucket. Removed from
this one.

`oac-13` has left this bucket: the atomic write was implemented and measured
(`OC-47`), five runs of five leaving a complete document against one of five
before. `C24` is what that repair turned out to cost on a platform it had not
been run on — not a reason to undo it.

**`C18` has left the owner-decision bucket entirely: it is repaired** (`OC-53`).
It was never the large change it was feared to be — `int64_t` in the parameter,
the product and the return — and the evidence is what took the work: nine
reports across three fixtures and all three tools are **bit-identical** on
LP64, with the one differing field excluded **by measurement** (the baseline
differs from itself there, because the permutation tests seed from
`/dev/urandom`) and the comparator shown live against a 1e-15 perturbation. On
Windows it turned a §5.2.5 test that failed whatever the data into one that
prints **exactly macOS's figure**.

`A02` and `A06` have left it, **closed** this round (`OC-55`, `OC-56`). `A02`
took the third of its three options — exclude the affected path — and at width
1 the exclusion is a counting **proof** from the two shipped constants, so the
floor oracle now prints `CERTIFIED FLOOR` there and `EVALUATED MARGIN (not a
floor)` above it. `A06`'s filename exception is replaced by a platform-keyed
expected-result manifest, with all four required failures demonstrated.

`A05` and `A04` have left it, repaired in the previous round, with
`cpp/selftest/regression-output-aliasing.sh` (27 checks) holding them and shown
failing against a pre-fix build. `A07` and `A08` have left it too: this audit's
own oracles were exiting 0 on malformed and unrelated input, and
`oracles/oracle-selftest.sh` (12 cases) now holds each refusal against the
reason it is supposed to fail for.

## Needs another platform — now genuinely empty, and measured rather than argued

**This bucket was never a machine.** Two CI jobs reach everything in it:

| job | host | trigger |
|---|---|---|
| `.github/workflows/x86-64-platform-facts.yml` | `ubuntu-latest` — x86-64 glibc, x87 80-bit `long double` | every push to `master` and every PR |
| `.github/workflows/windows-platform-facts.yml` | `windows-latest` — MSYS2 MINGW64, x87 80-bit, **LLP64** | manual only; it answers questions and gates nothing |

Everything that was in this bucket has left it:

| was | now |
|---|---|
| the four canary signatures | **observed.** Four of five exactly as argued; the fifth was the instrument's string match, fixed and verified on both libcs |
| **`R-1`** | **measured, diagnosed and repaired** (`OC-41`), and it is a `long double` **format** defect rather than a platform one: 117 of 255 alphabet sizes at 53 bits, **155 of 255 at x87 80-bit on Linux *and* independently on Windows** (`OC-48`) |
| the pinned figures | **confirmed on a second platform** |
| **`REPRO-01`** | the wide-format side of the LRS underflow is observed rather than argued |
| the Linux job's own coverage | the sanitizer build is platform-aware, so the Linux job runs the **whole** suite — "could not run" is never counted as a pass |
| **Windows** — "assessed and not started, pending the owner" | **measured** (`OC-48`). It needed no machine and no owner decision to *measure*; only to *repair*. |
| build state on an unmet platform | the probe **refused** on Windows as designed, and has since been taught PE/COFF as a calibrated fallback; it now gives a real verdict there, labelled `via=full` because that test is the weaker one |

**Windows, stated plainly, because this is the sentence someone sizing the work
will read:** all three tools build and link, with OpenMP; `ea_non_iid` runs the
complete non-IID battery and produces a figure; `ea_iid` and `ea_restart` run
through chi square, the §5.2.5 LRS test and (for `ea_restart`) the restart
sanity check, all passing, then exit at `seed()`; reports are written correctly
(`C24` repaired); and the §5.2.5 figures match macOS exactly. **That is not
"Windows is unsupported" and must not be summarised as such.** `seed()` is
**DEFERRED** rather than blocking, because the owner's vendor reference
qualification means no NIST binary runs on a user's machine (`OC-60`).

**The remaining Windows facts.** With `C18`
repaired, `ea_iid` and `ea_restart` pass chi square **and** the §5.2.5 LRS test
on Windows — printing `Pr(X >= 1) = 0.365370`, **exactly macOS's figure**,
where they previously printed `−0.000367` — and `ea_restart` gets past the
**restart sanity check**, which is the check January's acceptance decision
depends on. Both then die at `seed()`. So `OC-42` is confirmed for both tools
rather than predicted, and the remaining Windows work is one entropy-path
decision (`seed()`) plus one portability fix (`C24`). `OC-53`.

**Windows builds today, and the owner's cost estimate should rest on that.**
An outside audit, pinned at an earlier commit, found the workflow green while
all three executables failed to build on the missing `libdivsufsort` package.
That was true then and is not true now: all three **compile and link**, with
OpenMP, gated and green. The blocker is **not** the absence of a build and it
is **not** `seed()` — it is `C18` and `C24`, two measured fail-closed defects
in a tree that otherwise builds and runs there. `seed()` is not even reached,
because `C18` fails the LRS test before the permutation stage that calls it
(`OC-50`).

**What Windows measured.** MSYS2 is preinstalled; `libdivsufsort` has no
`mingw-w64` package (`BUILDING.md` is right) and builds from source; `libgomp`
*is* packaged, in `mingw-w64-x86_64-gcc-libs`, which the preinstalled toolchain
does not pull in; all three tools **compile and link**; `ea_non_iid` runs the
complete non-IID battery and produces a figure. And two defects stop the route:
`C18` and `C24`, both **fail-closed**, both now in the owner-decision bucket
with measurements attached rather than readings of the source.

**`C18` is the one that was hiding.** It had sat as a source-only candidate —
"`n_choose_2` computes N in `long int`, which overflows on LLP64 and **would**
corrupt the §5.2.5 decision". It does: for a 1,000,000-sample input the true
N = 499,960,500,780 becomes **−403,189,204**, `Pr(X >= 1)` prints **−0.000367**
where macOS prints **+0.365370**, and the decision at `lrs_test.h:765` compares
against `logl()` of a negative number — **NaN** — so the LRS test fails
**whatever the data**. `reproducers/c18_llp64_overflow.c` reproduces the printed
value exactly from the integer arithmetic alone.

Linux **aarch64** (binary128, 113-bit significand) is not a standard
GitHub-hosted runner. R-1 is the only item that turned on `long double` width,
and it is now confirmed at two widths with the third reasoned from the same
mechanism; nothing else in the audit currently turns on it.

## Needs the physical device — arriving January 2027

Everything here is **NOT RUN** and stays NOT RUN. Synthetic data establishes
claims about instruments, never about sources.

| item | what it needs the device for |
|---|---|
| **the restart assessment** | A real restart dataset, decided with the corrected cutoff and **not** with §3.1.4.3's printed binomial formula, which rejects correctly-operating sources (`OC-30`, `XR-11`). The decision must be computed, recorded with `X_max`, `H_I`, the cutoff, the method and the binary's identity, and never upgraded by a later repair. **At the width-1 operating point the two cutoffs are identical below H_I ≈ 0.989, so for this device the `C23` repair changes no verdict** — the table to read a cutoff out of is `XR-13`, and the entropy figure itself is still unmeasured. |
| **the per-device baseline** | `XR-07`: a defect can be invisible to the estimator battery **and** to the outside-battery check at once, so the per-estimator breakdown needs a per-device baseline — and that baseline cannot be synthesised, by construction. |
| **the pinned figure** | `pin-check.sh` is pinned on an upstream sample. It is to be re-based on a real capture when one exists (steps in `BUILDING.md`). |
| **the 0.696 figure** | One unit's measurement, uninterpretable pending build provenance. |
| **health-test and operating-range evidence** | Not an estimator question at all; the estimator cannot produce it. |

## Needs a decision from the owner

| question | why it is a decision and not a task |
|---|---|
| **Upstream issue #253 is still open.** | `F01` was withdrawn and the PR closed, but closing the issue was never authorised. With "nothing upstream" standing, it stays open indefinitely unless the owner says otherwise. |
| **Force POSIX argument order (`+` on each `getopt` optstring).** | GNU getopt permutes and BSD does not, so an argument beginning with `-` is consumed differently on Linux and macOS (`OC-40`). Both platforms refuse bad input, so this is reproducibility rather than safety. A one-character change per tool, but a behaviour change on Linux: options after the filename would stop being recognised there, which is already the macOS behaviour and already what `C21` documents. |
| **Does TruePad's harness ever invoke these tools on a user's Windows machine?** | The question has **changed shape** now that Windows is measured (`OC-48`). It no longer decides whether to *measure* Windows; it decides whether to *repair* what the measurement found. If yes: **`C18` must be repaired** — the §5.2.5 LRS test fails unconditionally there on any standards-sized input — and `C24` with it. If no: both close as will-not-be-done, and the measurement is still worth having, because it is what turned `C18` from a reading into a fact. Not answerable from this repository — it is a question about TruePad's deployment. |
| **`seed()`: a Windows entropy source — DEFERRED, not a blocker.** | **The owner adopted a vendor reference qualification as the default path, under which no NIST binary runs on a user's machine**, so `seed()` is not on the product's path; it matters only for the expert-opt-in self-assertion path, for which macOS and Linux suffice (`OC-60`). The fix is small and well understood: a **platform entropy source** (`BCryptGenRandom` or `RtlGenRandom`) under `_WIN32`. **`std::random_device` must be refused** — on MinGW libstdc++ it has historically been deterministic, which would make the permutation tests' p-values meaningless while every surface indication said the tool worked. Previously described here as the measured blocker; With `C18` repaired, `ea_iid` and `ea_restart` pass chi square and the §5.2.5 LRS test on Windows and then die at `seed()`, which opens `/dev/urandom` and calls `exit(-1)`; `OC-42` is **CONFIRMED for both tools** rather than predicted (`OC-53`). The change is `BCryptGenRandom` (or `RtlGenRandom`) under `_WIN32`, keeping `/dev/urandom` elsewhere. **`std::random_device` must be refused** as the portable shortcut: on MinGW libstdc++ it has historically been a deterministic PRNG, which would silently make the permutation tests' p-values mean nothing. The seed feeds the xoshiro256** state used to shuffle, so the bar is behavioural: POSIX byte-identical, two Windows runs must differ in `permutationTestResults` as two macOS runs do, the failure path stays fail-closed, and the IID verdicts on the pinned fixtures must match LP64's. One function, two branches, one library on one platform, and a nondeterminism control that is already written. |
| **`F10`/`C01`: correct MultiMMC's chained prefix lookup.** | §6.3.9 step 4.b.i requires an independent lookup of M_d at every depth; the code looks up depth d only if depth d−1 hit, and the `MAX_ENTRIES` cap then suppresses all depth ≥ d predictions for a recurring context (`OC-55`). **Unreachable at width 1 by proof**, so it changes nothing for this device, and the floor oracle excludes it there. Above width 1 it is an evaluated margin rather than a bound, and the only way to make it a bound is to correct the algorithm — which is estimator numerics, and therefore the owner's call, not a task. |
| **Hill's third proposal.** | `OC-30` implements the exact multinomial maximum. Hill also proposes a *corrected binomial* restart check — count one fixed symbol, chosen from the whole dataset — which is easier to model but has less statistical power. Adopting it, or offering it, is a design choice. |
| **Whether the fork's figure is ever reported alone.** | The standing rule is two figures, always. Relaxing it would be an owner decision, and nothing in the audit supports relaxing it. |
| **`productionApprovalEnabled`.** | Stays `false` with `approvedBuilds` empty. Flipping it depends on independent review, build verification and physical evidence, none of which exist; it is listed here because it is the decision everything else feeds. |

## Will not be done — and why, permanently

This bucket is not a queue. Nothing here is pending.

| item | why not |
|---|---|
| **Independent review of any repair.** | The owner has decided there will be none. Every "independent verification remains" note in `audits/2026-09-30/FINDINGS-TRACKER.md` — including `C-01`'s, which is otherwise fixed — resolves here. **REPAIRED is not REVIEWED, and on this project it never becomes REVIEWED.** |
| **Any upstream report.** | Decided 2026-10-15, on the basis that an earlier upstream PR went unacknowledged. This includes the strongest findings the audit produced: the `C07`/`C03` chain, `C23`'s undocumented departure from the printed formula (`OC-30`), and the §6.3.1 errata inconsistency that Hill independently corroborates (`OC-32`). `UPSTREAM-REPORT-INVENTORY.md` is kept as documentation of what is wrong with the tool being run, and is not sent. |
| **Regenerating the reference corpus from these tools.** | A reference produced by its subject cannot detect its subject changing. The corpus is made more complete only by derivation from data that predates the current build (`OC-21`). |
| **Trusting the reference corpus.** | Ten of eleven key families are upstream-captured with no independent derivation. It is more complete than it was; it is not more trustworthy. "The selftest still passes" validates nothing on its own — use build-differential, spec-derived oracles, inputs whose verdict is known by construction, and metamorphic relations. |
| **`ea_conditioning` / `ea_transpose` findings** (`N-03`, `N-05`, `N-11`, `C06`, `C09`, most of `C21`) | Not built, deliberately. They become active work before that scope can expand, and expanding it is not planned. |

## The wall

**The needs-nothing bucket is empty, and the fork has reached the hardware
wall.** Everything that could be done here has been done:

| item | disposition |
|---|---|
| **`C18`** LLP64 overflow | **repaired** (`OC-53`); nine reports bit-identical on LP64; Windows now prints macOS's figure exactly; corroborated in the wild by upstream #219 (`OC-61`) |
| **`C24`** the atomic write is not portable | **repaired** (`OC-57`); `MoveFileEx` under `_WIN32`, verified on Windows with the old writer failing beside it |
| **`F13`** NaN into `std::min` | **closed as unreachable** (`OC-58`); a probe that fires below the size floor, so its silence is a measurement |
| **`C22c`** the `ZALPHA` ceiling | **closed** (`OC-62`); the factor was compression-versus-collision, the record is vindicated, and it is a bound |
| **`A02`**, **`A06`** | **closed** (`OC-55`, `OC-56`) |
| **`A05`**, **`A04`**, **`A07`**, **`A08`** | **repaired** in the preceding round |
| **`C06`** | was double-counted; it concerns a tool deliberately not built |

**Two owner decisions remain, and neither is work.** `seed()` is **deferred**,
because the vendor reference qualification means no NIST binary runs on a
user's machine (`OC-60`). `F10` is **unreachable at width 1 by proof**, so it
changes nothing for this device; correcting it is what would turn an evaluated
margin into a bound above width 1, and that is estimator numerics.

**Windows is in a much better position than "unsupported" and must not be
described as unsupported.** All three tools build; `ea_non_iid` produces a
figure; `ea_iid` and `ea_restart` pass chi square, the §5.2.5 LRS test and the
restart sanity check before exiting at `seed()`; reports write correctly; the
§5.2.5 figures match macOS exactly.

### What actually moved this document, across five revisions

None of it was moved by an argument.

- **Running the code where it had never run** found `C18` (a year old, filed
  "Low, expect to refute") and `C24` (in a repair this audit wrote and had
  reproducers for).
- **Reproducing an outside audit instead of assessing it** found that one of
  this audit's own repairs **destroyed the input capture**, and that **four
  refusals for one shared accidental reason** look exactly like four working
  guards.
- **Asking an instrument to print its workings** found a probe defeated by a
  filename, a sweep reporting the edge of its own grid as a worst case, and a
  harness asserting the opposite of the defect it was built to demonstrate.
- **Running the baseline against itself** turned "the fix changed something"
  into "this field is nondeterministic by design" (rule 8).
- **Asking what a consistent ratio was made of**, rather than which side was
  wrong, turned a claim that the record was unreproduced into a reconciliation
  of it (rule 9's corollary, `OC-62`).

Four of those five were instruments catching **themselves**. That is the only
reason to believe the rest.

**On the project's central claim, nothing moved and nothing can.** What this
device's entropy actually is, whether its restart data is accepted, whether a
per-device baseline exists — all wait on hardware arriving **January 2027**.
The physical bucket is entirely **NOT RUN** and stays that way.

## How to tell whether this document has gone stale

`OC-34` exists because the open list had not been checked against the tree since
the merge, and two entries were wrong when it was. The checks are cheap:

```sh
cd cpp && make non_iid iid restart && cd selftest
./run-all-checks.sh --allow-known-platform-deltas   # expect 20 passed, 0 failed
./harness-inventory-mutation-test.sh                # expect 5 of 5 mutations landed
./outside-battery-mutation-test.sh                  # expect 9 of 9 mutations landed
```

And the two platform jobs, which are the cheap way to find the class of claim
that is true only on the host you wrote it on:

```sh
./regression-platform-deltas.sh                      # 6 cases; the platform exception
cd ../../audits/2026-10-11-independent-audit/oracles && ./oracle-selftest.sh  # 12 cases
```

And the two platform jobs, which are the cheap way to find the class of claim
that is true only on the host you wrote it on:

```sh
gh workflow run x86-64-platform-facts.yml     # also runs on every push to master
gh workflow run windows-platform-facts.yml    # manual only; ~8 minutes
gh run download <id>                          # every log is an artefact
```

Three instruments now refuse rather than guess, and a reader should know what
each refusal means:

| instrument | refuses when |
|---|---|
| `mutation-lib.sh` | no unmutated **baseline** was asserted accepted, so refusals are unattributable (rule 7) |
| `entropy_floor.py` | the bit width is not established, or the report fails validation; and it says **EVALUATED MARGIN** rather than **CERTIFIED FLOOR** above width 1 |
| `restart_decision_exact.py` | the restart fields are absent, or a six-decimal `H_I` does not determine the integer cutoff (exit 2, never a guess) |
| `check-platform-deltas.py` | no platform block matches, a delta exceeds its row, a row was never observed, or the manifest is unreadable |

Read the Windows job's `verdict.log` first. A `GATE FAIL` there is a measured
finding, not a broken job: as of 2026-10-20 the expected failures are
`libdivsufsort` having no package, `C18`, and the three `C24` gates. Anything
else failing is new.
./regression-docs.sh                                # the prose claims that can be checked
```

A mutation harness that reports `MUTATION-DID-NOT-APPLY` is telling you the
harness is broken, not the guard (`mutation-lib.sh`, `OC-33`). An item in the
lists above is live **only** if it has been checked against the current tree;
that is the rule `OC-34` was written to establish, and this document is subject
to it too.
