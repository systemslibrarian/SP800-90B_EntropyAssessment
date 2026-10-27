# What is left — closing inventory

Date: **2026-10-27**. **This is the closing revision. The campaign is closed,
nothing further is planned, and the next thing that moves this repository is
the device in January 2027.** State: `master` at the commit adding this
revision. Written to be read cold, by someone who has not followed the work.
The buckets below are unchanged by this revision; the previous headline — the
Windows measurement and the outside audit, 2026-10-20 — is in this file's
history and in `OC-48`–`OC-58`.

**The closing revision was not the last commit.** Pushing it fired
`c22c-source-check` for the first time in its existence, and that run —
`40496388177` — **went red**: the stamp-provenance limb read a shallow CI
checkout (`actions/checkout`'s default `fetch-depth: 1`, one commit) as proof
that a stamped ancestor "is not a commit in this repository". The stamps, the
digest and every carried value were correct; the instrument was wrong about the
tree it stood in. **And it was not confined to a provenance line: because
`entropy_floor.py` validates at import, the floor could not be LOADED in a
shallow clone — measured — so a clone made the ordinary CI way could not
compute an entropy figure at all.** Repaired in the revision after this one,
in two halves —
the probe now reports an unanswerable question as unverified instead of
refusing, and the workflow is given full history so the limb stays live rather
than going quiet (`OC-127`). Sweeping for the mechanism rather than the bug
then found **the same fault in two more limbs of `regression-docs.sh`**, where
a shallow clone made the suite's own documentation check declare 27 documented
commit SHAs bogus; both are gated and skip with a printed reason. Those two had
never been wrong in CI only because the x86-64 workflow already passes
`fetch-depth: 0` for an unrelated reason — **correct by an accident of someone
else's requirement**, which the new workflow did not inherit. **A closing claim
of green was disproved by the first run on a platform no local tree
resembles**, which is the rule in `OC-41` arriving once more, about clone depth
this time. The other run on the closing revision, **x86-64 `40496388186`,
PASSED** — so the platform facts and the nine commits' worth of claims that had
never been measured off Darwin arm64 are measured and green; it is the new
workflow alone that was red. Local suite on the repaired tree:
**26 passed, 0 failed**. The repair is `302812d`, and both workflows passed on
it — `c22c-source-check` `40501921020`, the first green run in its existence,
and x86-64 `40501921056` — with the gated limbs confirmed **live** in those
runs rather than skipped: no `NOT VERIFIED HERE` line in the one, and
`every commit SHA in NOTICE and the tracker resolves: yes` in the other's
artefact log.

## What the campaign established

Three findings lead, because they are the ones that would survive an outside
reader's scepticism:

1. **The figures agree with three independent references.** This fork matches
   NIST's published reference outputs on **Linux x86-64 with GCC — the
   platform NIST produced that data on — with no exceptions claimed**: the
   platform-delta manifest deliberately lists **no block** for Linux, so a
   `selftest` failure there is not excused and the x86-64 CI job fails rather
   than adopting macOS's eight documented last-digit deltas. And across
   **1,689 value-rows** compared against **two independently written
   implementations**, there were **10** disagreements, every one of them
   separated into a platform effect or an identified fork defect (`OC-110`–`OC-114`,
   the three-way differential).
2. **`C22a`'s attainment point is justified on both axes, not merely
   sampled.** `K` = 1.6189e-14 is attained at `N` = 5, `r` = 2; `N` = 5 is an
   **interior** maximum, and `r` = 2 is the **genuine boundary of the
   admissible domain** — at `r` = 1 the root of `P_local` falls below the
   `1/k` floor the code itself imposes, so it cannot be solved at all, and
   `r` = 1 would first become admissible at `k` = 498, **1.95x the largest
   alphabet §3.1.1 permits**. An independent computation over a domain taken
   from the mathematics reproduces the recorded constant to five significant
   figures at exactly the recorded point (`OC-121`). It remains **MEASURED,
   not PROVED**: monotonicity in `r` and at large `N` is established by scan.
3. **`C22c`'s six family values have one source, and the oracle can no longer
   verify its own copy.** The values are derived once, pinned by digest, and
   the defect that made this necessary — a sweep that mutated one copy while
   the check read another — is closed (`OC-125`). No entropy was recovered,
   because none was being thrown away: the 4.5–4.9x ratio was Compression
   versus Collision, a mechanism, as a consistent ratio always is (`OC-62`).

Beyond those, the instruments. Each count below is compared against the
script that declares it by `cpp/selftest/regression-docs.sh`, or is dated and
attributed, because hand-typed counts in this document drifted six times
before that rule existed (`OC-126`):

- `cpp/selftest/run-all-checks.sh` runs 24 regression scripts
  (`./run-all-checks.sh --allow-known-platform-deltas` — expect 26 passed, 0 failed);
- `audits/enum-instruments.sh` prints **87 live instruments** (measured
  2026-10-27 at `a5422cf`, up one for `oracles/git-classification-test.py`,
  `OC-128`; the count has a hand-reviewed limb, `OC-126`);
- three mutation harnesses — `harness-inventory-mutation-test.sh`,
  `outside-battery-mutation-test.sh`, and the band-1 pair battery
  `band1-pair-mutations.sh`, which on 2026-10-27 measured **12 CAUGHT, 2 NOT
  CAUGHT** over the undeclared repair-interaction pairs, the two named below;
- `oracles/oracle-selftest.sh` (33 cases), each refusal against its own reason;
- `cpp/selftest/regression-output-aliasing.sh` (46 checks), the input capture
  shown preserved against every alias of its own path.

And: a **measured floor** with every subtracted term named and its status
printed; `C18` and `C24` repaired and **measured on Windows**; `R-1` live on
x86-64 via CI; and the standard's own blind spot quantified — **an AES-CTR
stream with an all-zero key, entropy exactly zero, is assessed at 7.145 of 8
bits** (`OC-109`), which is why provenance and not estimator agreement is the
defence.

## What remains permanently open, and why

- **No independent review, ever** (`C8`). The owner has decided there will be
  none. **REPAIRED is not REVIEWED, and on this project it never becomes
  REVIEWED.** The consequence is stated rather than implied: **the verdict is
  partially established, PERMANENTLY.** That is the ceiling, not a waypoint.
  Every repair, every instrument, and every one of the four defects this
  fork's own repairs introduced (`FORK-DIVERGENCE-AND-TRUST.md` section A.2)
  is reviewed by nobody but its author. Rule 12 — the repair-interaction
  declaration — is the whole of the mitigation.
- **Nothing is reported upstream**, including the strongest findings the
  campaign produced. `UPSTREAM-REPORT-INVENTORY.md` is documentation of what
  is wrong with the tool being run, and is not sent.
- **Two withdrawn verifications stand withdrawn** (`WV-1`, `WV-2`), each
  naming what leaned on it.
- **Two mechanisms are measured unguarded**, and that count is a floor:
  `mutation-lib`'s own landing contract, and the `O_EXCL` atomic write whose
  load-bearing condition has been eliminated (`OC-117`, `OC-126`).
- **`F10`/`C01`** is unreachable at width 1 by proof and is estimator numerics
  above it; **`seed()`** is deferred under the vendor reference qualification.
  Both are owner decisions, not tasks.

## What waits on the device

Everything that could make a statement about a **source** rather than an
**instrument**: the restart assessment decided with the corrected cutoff and
recorded with its method and the binary's identity; the per-device baseline,
which cannot be synthesised by construction; the re-based pinned figure; and
the health-test and operating-range evidence the estimator cannot produce.
Synthetic data establishes claims about instruments, never about sources.
**All of it is NOT RUN and stays NOT RUN.** The table is below.

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
# 3. the floor, with every subtracted term named and ITS STATUS. At width 1
#    this prints MEASURED FLOOR (C22a) -- the aggregate takes the weakest
#    status of its terms, and C22a is a product of two grid maxima (OC-78);
#    above width 1 it prints EVALUATED MARGIN (NOT A FLOOR), because the
#    C01/F10 term is a measurement there and not even a ceiling (A02).
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

**`C22a`'s boundary question is PARTLY closed, and the claim made here was
wrong** (`OC-63`, corrected by `OC-78`). What was measured is that the factor
`c` = 0.4991's argmax is interior in every swept axis. What this entry went on
to say — *"so `C22a` is a bound and both floor readings are certified floors at
width 1 again"* — **is false, and false as written, not merely out of date.**

`8.08e-15` is `c × K`, a **product of two grid maxima**, and `OC-63` examined
only `c`. The second factor, `K` = 1.6189e-14, is attained at `N` = 5, `r` = 2,
where `r` = 2 is the **first value in the swept list** — and rule 9 was never
applied to it. The sweep's own worst realised inflation reaches **92.8 %** of
the ceiling it is supposed to bound. `C22a` is **MEASURED**, and the word
*certified* has been retired from the floor (`OC-78`). The readings are
**MEASURED FLOORS**.

**And what was withdrawn was a VERIFICATION, not just a label.** `OC-63`
claimed the constant had been *checked* to be a supremum. That claim is
withdrawn with its date and its reason as **`WV-2`** in
[`audits/WITHDRAWN-VERIFICATIONS.md`](../WITHDRAWN-VERIFICATIONS.md), beside
**`WV-1`** — `C23`'s cutoff check, printed from an empty loop (`OC-75`) — the
two withdrawn in the same week. Each entry names what leaned on it, which is
the field that is easy to omit and the only reason the others matter.

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
thrown away.**

`C22c`'s status is **split**, and calling it simply a bound here was wrong
(`OC-78`). Its `dX' ≤ dz·σ_max/√v` **is** derived — Popoviciu bounds `σ_max`
and `v = num_blocks − 1000` is exact — but the **ceiling** built on top of it
is a maximum over an **801-point scan** of step `dX'/8`, which is MEASURED. Its
argmax is at `cap − 1.0 dX'`, where the upper evaluation point lands on
`G(1/64)` exactly; that is structurally explained, which is the best a scan
maximum gets, and is still not a proof. The readings are **MEASURED FLOORS**,
not certified ones.

**And the helper that certified this was itself wrong** (`F02`, `OC-78`).
`oracles/zalpha_ceiling_by_n.py` used `v = num_blocks`, omitting the `d = 1000`
dictionary blocks that production subtracts, and `mpf(n)/6` where production
floor-divides. Its `dX'` at n = 10⁶ was 2.1422e-06 against the correct
2.1486e-06 — 0.300 % low, in the **unsafe** direction — and it **reported
agreement** because its tolerance was a flat 1 % on values the record states to
three significant figures. The record was right; the independent reproduction
was the wrong one. Fixed, with the tolerance now derived from the recorded
precision.

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
floor oracle prints `PROVED EXCLUSION` for that term there and `EVALUATED
MARGIN (not a floor)` above it. The **aggregate** label at width 1 is
`MEASURED FLOOR (C22a)`, not a certified one: that claim was retired at
`OC-78`. `A06`'s filename exception is replaced by a platform-keyed
expected-result manifest, with all four required failures demonstrated.

`A05` and `A04` have left it, repaired in the previous round, with
`cpp/selftest/regression-output-aliasing.sh` (46 checks) holding them and shown
failing against a pre-fix build. `A07` and `A08` have left it too: this audit's
own oracles were exiting 0 on malformed and unrelated input, and
`oracles/oracle-selftest.sh` (33 cases) now holds each refusal against the
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
| **the restart assessment** | A real restart dataset, decided with the corrected cutoff and **not** with §3.1.4.3's printed binomial formula, which rejects correctly-operating sources (`OC-30`, `XR-11`). The decision must be computed, recorded with `X_max`, `H_I`, the cutoff, the method and the binary's identity, and never upgraded by a later repair. **WITHDRAWN CLAIM, KEPT WITH ITS CORRECTION (`F12`, `OC-85`).** This cell read: *"At the width-1 operating point the two cutoffs are identical below H_I ≈ 0.989, so for this device the `C23` repair changes no verdict."* **The premise is false** — it was a sweep in steps of 0.02 read as an interval, and `OC-49` found a counterexample inside the range at `H_I = 0.9661822653793894` (printed 581, exact 582). Bisection on the crossings, not sampling, gives **36 intervals of disagreement totalling 0.217 % of [0.50, 0.989]**, clustered at the high-entropy end. **The conclusion survives on different evidence:** at this project's operating point, `H_I = 0.696`, both cutoffs are **684**, and the lowest `H_I` with any disagreement is **≈ 0.888** — a statement about one point and one boundary, both solved for. Read a cutoff from `oracles/restart_cutoff_certified.py`, **not** from `XR-13`'s table, whose interval claim this supersedes. The entropy figure itself is still unmeasured. |
| **the per-device baseline** | `XR-07`: a defect can be invisible to the estimator battery **and** to the outside-battery check at once, so the per-estimator breakdown needs a per-device baseline — and that baseline cannot be synthesised, by construction. |
| **the pinned figure** | `pin-check.sh` is pinned on an upstream sample. It is to be re-based on a real capture when one exists (steps in `BUILDING.md`). |
| **the 0.696 figure** | One unit's measurement, uninterpretable pending build provenance. |
| **health-test and operating-range evidence** | Not an estimator question at all; the estimator cannot produce it. |

## Needs a decision from the owner

| question | why it is a decision and not a task |
|---|---|
| **Upstream issue #253 is still open.** | `F01` was withdrawn and the PR closed, but closing the issue was never authorised. With "nothing upstream" standing, it stays open indefinitely unless the owner says otherwise. |
| **Force POSIX argument order.** Still a decision, now with its facts measured, and **the mechanism this row used to recommend is wrong** (`OC-96`). GNU getopt permutes and BSD does not, so an option after the filename is consumed differently on Linux and macOS (`OC-40`). **Measured on Darwin arm64:** `-i -a data.bin 1 -q -o out.json` exits **255** and writes no report — the five trailing words are read as operands. **Measured in this tree:** **0 of 16** real invocations put an option after an operand, so enforcing the documented order costs nothing here. **NOT the one-character change this row recommended:** a leading `+` in the optstring means *stop permuting* on glibc but is **accepted as an option character** on macOS — measured, `-+` taken as a valid option — so `+ab` would silently add a `-+` option to all three tools. The portable enforcement is a **prescan refusal** of an option after the first operand, which the tools already have a prescan to carry and which behaves identically everywhere. **The Linux half is now MEASURED** (`OC-102`, run `40241103943`): glibc **does** permute — `-i -a data.bin 1 -q -o out.json` exits **0 and assesses** there and exits **255 assessing nothing** on Darwin, so the same command line is valid on one supported platform and a usage error on the other. And a permuted `-o` **is** invisible to the early identity prescan — but `writeJsonReport`'s own guard caught the alias anyway, exit 255 with the capture's SHA-256 unchanged, which is the choke-point design working on the platform where the entry-point check failed. Both platforms refuse bad input, so this remains reproducibility rather than safety. |
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
| **Independent review of any repair — and `C8`, any independent cryptographer or security review.** | The owner has decided there will be none, **ever**; restated 2026-10-25 with `C8` named explicitly as `WILL NOT BE DONE`. Every "independent verification remains" note in `audits/2026-09-30/FINDINGS-TRACKER.md` — including `C-01`'s, which is otherwise fixed — resolves here. **REPAIRED is not REVIEWED, and on this project it never becomes REVIEWED.** The consequence is stated rather than left implicit: **the verdict is partially established, PERMANENTLY** — that is the ceiling, not a waypoint, and `FORK-DIVERGENCE-AND-TRUST.md` §5 carries the full statement. Three things this closes that were previously phrased as pending: the four defects in that document's section A.2 were introduced by this fork's own repairs and **are reviewed by nobody but their author** (rule 12 is the whole of the mitigation); the instruments are in the same position, with two withdrawn verifications and a detector whose false-negative rate is demonstrated non-zero; and no "route to external trust" list belongs in this repository, because the routes are closed. |
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

### What actually moved this document, across six revisions

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
- **Measuring this document's own counts against the scripts that know them**
  found the staleness section — whose purpose is to detect staleness — wrong
  by six about the suite and by twenty about the oracle self-test, three of
  the replacement counts wrong in the same session, and a sixth instance of
  the defect in the suite's own scope statement (`OC-126`). Every such count
  is now derived from its script or dated and attributed, and the check that
  enforces it was itself found unable to fail by its negative control.

Four of the first five were instruments catching **themselves**; the sixth was
a reader catching an instrument's absence, and the instrument then built caught
its author's counts wrong twice on its first run. That is the only reason to
believe the rest.

**On the project's central claim, nothing moved and nothing can.** What this
device's entropy actually is, whether its restart data is accepted, whether a
per-device baseline exists — all wait on hardware arriving **January 2027**.
The physical bucket is entirely **NOT RUN** and stays that way.

## How to tell whether this document has gone stale

`OC-34` exists because the open list had not been checked against the tree since
the merge, and two entries were wrong when it was. The checks are cheap:

```sh
cd cpp && make non_iid iid restart && cd selftest
./run-all-checks.sh --allow-known-platform-deltas   # expect 26 passed, 0 failed
./harness-inventory-mutation-test.sh                # expect 5 of 5 mutations landed
./outside-battery-mutation-test.sh                  # expect 9 of 9 mutations landed
./regression-docs.sh                                # the prose claims that can be checked
```

And the two platform jobs, which are the cheap way to find the class of claim
that is true only on the host you wrote it on:

```sh
./regression-platform-deltas.sh                      # 6 cases; the platform exception
cd ../../audits/2026-10-11-independent-audit/oracles && ./oracle-selftest.sh  # 33 cases
```

**Every `gh` command here names the repository, and that is load-bearing**
(`OC-93`): this checkout has an `upstream` remote, `gh` with no `-R` resolves to
it, and the name, visibility and default branch of the two repositories are
identical — so a bare call returns a plausible answer about the wrong tree.

```sh
FORK=systemslibrarian/SP800-90B_EntropyAssessment
gh workflow run x86-64-platform-facts.yml  -R "$FORK"   # also runs on every push to master
gh workflow run windows-platform-facts.yml -R "$FORK"   # manual only; ~8 minutes
gh run download <id>                       -R "$FORK"   # every log is an artefact
```

Three instruments now refuse rather than guess, and a reader should know what
each refusal means:

| instrument | refuses when |
|---|---|
| `mutation-lib.sh` | no unmutated **baseline** was asserted accepted, so refusals are unattributable (rule 7) |
| `entropy_floor.py` | the bit width is not established, or the report fails validation; and it says **EVALUATED MARGIN** rather than any kind of floor above width 1. At width 1 it says **MEASURED FLOOR**, naming the term that holds the status there — the certified label was retired at `OC-78` |
| `restart_decision_exact.py` | the restart fields are absent, or a six-decimal `H_I` does not determine the integer cutoff (exit 2, never a guess) |
| `check-platform-deltas.py` | no platform block matches, a delta exceeds its row, a row was never observed, or the manifest is unreadable |

Read the Windows job's `verdict.log` first. A `GATE FAIL` there is a measured
finding, not a broken job: as of 2026-10-20 the expected failures are
`libdivsufsort` having no package, `C18`, and the three `C24` gates. Anything
else failing is new.

A mutation harness that reports `MUTATION-DID-NOT-APPLY` is telling you the
harness is broken, not the guard (`mutation-lib.sh`, `OC-33`). An item in the
lists above is live **only** if it has been checked against the current tree;
that is the rule `OC-34` was written to establish, and this document is subject
to it too.
