# Cross-repository findings — for the TruePad session to act on

Findings verified **in this repository** that have consequences **in TruePad**.
A finding may cross repos; a commit may not. Nothing here has been changed in
`~/repos/TruePad`, and nothing here should be fixed from a session scoped to
this fork — the earlier `3f27453` was exactly that mistake.

---

## XR-01 — a failed run leaves the previous run's report on disk, reporting success

**Verified by execution in this repository, on `master` `f069898` and on the
repair branch `2d4b135` — identical on both.** Cluster `C14`, member
`output-automation-contracts-4`.

### Why TruePad needs this

TruePad's desktop harness invokes these tools and reads their output files. If
it reads `RESULT.json` **without first checking the tool's exit status**, it
will silently consume a stale number from a previous run. The number looks
completely valid — it is a real assessment, of different data.

### What was demonstrated

```
# 1. a good run writes a real report
ea_non_iid -q -o RESULT.json uniform-1bit.bin 1
  rc=0        RESULT.json: errorLevel 0, hAssessed 0.8389091522985468

# 2. a FAILING run against the same -o path
ea_non_iid -l 5,0 -o RESULT.json uniform-1bit.bin 1
  rc=255
  "Error: -l requires a sample count greater than zero."
  (usage dump follows)

# 3. what is on disk afterwards
RESULT.json is BYTE-IDENTICAL to the previous successful run
```

**What a consumer reading the file rather than the status sees:**

| Field | Value it reads | Truth |
|---|---|---|
| `errorLevel` | `0` | the run failed |
| `hAssessed` | `0.8389091522985468` | nothing was assessed |
| `filename`, `sha256` | the **previous** run's | not what was submitted |
| `dateTimeStamp`, `commandline` | the **previous** run's | not this invocation |

The tool writes **nothing** on this path — it does not truncate, does not write
an error report, and does not remove the file. The error goes to stdout/stderr
and the exit status only.

### Direction

**Unknown, leaning permissive.** Whether the stale figure is higher or lower
than the truth depends entirely on what ran before. The dangerous case — a
stale figure *higher* than the data deserves — is as likely as the safe one,
and a consumer has no way to tell from the file's contents alone that it is
reading history.

### What the TruePad session can do about it, in order of strength

1. **Check the exit status.** This is the complete fix on the consumer side and
   costs nothing. `255` means the file is not this run's.
2. **Cross-check provenance.** The stale file carries the *previous* run's
   `filename` and `sha256`. A consumer that compares those against the input it
   actually submitted catches this even without the exit status. That is a
   second, independent check and worth having regardless.
3. **Delete the output path before invoking the tool.** Then a missing file is
   itself the error signal, and there is no stale state to read.

Fixing it on the tool side (truncate or write an error report on every error
path) belongs to this fork and is tracked under `C14`. It is not fixed here —
`C14` has eight members and only this one is verified.

### Scope of this verification

- **Correct and verified**: the stale file survives, the exit status is 255, the
  contents are byte-identical, and a consumer reading the file sees
  `errorLevel 0` with a complete figure. Demonstrated on both branches.
- **Not verified**: the other seven members of `C14` (no exit status
  distinguishes statistical rejection from invalid input; `-q` suppressing
  verdict lines; three file problems collapsing to one message; non-atomic
  writes; `--version` anywhere in argv short-circuiting). Those remain
  finder claims.
- **Not established**: whether TruePad's harness actually reads the file without
  checking status. That is a question about TruePad's code, which this session
  did not read. The finding states the hazard; confirming the exposure is the
  TruePad session's to do.

---

## XR-02 — `gen-sbom.sh` can record an empty patch digest, and `--check` will agree with it

**Reported, not fixed.** From the dead-guard sweep, instance 12.

`ios/scripts/gen-sbom.sh:249`:

```sh
PATCH_DIGEST="$(file_digest "$VENDOR/EXPECTED-PATCH.diff" 2>/dev/null || echo "")"
```

`file_digest` is `shasum -a 256 "$1" | awk '{print $1}'` under `set -euo
pipefail`, so a missing `EXPECTED-PATCH.diff` fails the pipeline; `|| echo ""`
catches it — which also prevents `set -e` from aborting — and `PATCH_DIGEST`
becomes empty. It is emitted unchecked at `:314` as
`{ "name": "truepad:patch-digest", "value": "" }`.

Because `gen-sbom.sh --check` compares a regenerated SBOM against the committed
one, a missing patch file yields empty on **both** sides and the comparison
passes. The digest that would detect a changed vendored patch can be absent
while the SBOM check reports agreement.

The fix has the same shape as the one already applied to `run-audit.sh` in
`3f27453`: assert the digest is non-empty before emitting it. **Left for the
TruePad session.**

---

## Note on `3f27453`

That commit (TruePad `master`, `audit-scripts/run-audit.sh`, the evidence
manifest check) was made from this fork's session and was a scope error. It is
left in place rather than reverted, on instruction. The TruePad session should
take ownership of it, review it, and decide whether to keep, amend or drop it.
Its commit message records the mechanism — `grep -c .` printing `0` while
exiting `1`, so a `|| echo 0` fallback fires alongside a successful print — so
the broken form is not reintroduced.

---

## XR-03 — a mis-scaled `H_I` argument silently disables both restart gates

**Verified in this repository on both branches** (`OC-11`). Reported for the
TruePad session because `H_I` is an argument *the caller supplies*, and
TruePad's desktop harness is the caller.

`ea_restart` takes the initial entropy estimate `H_I` as a command-line
argument. On master and on the repair branch:

```
ea_restart -i -v <1M file> 1 1e-400
  H_I: 0.000000
  ALPHA: 5.0251553006530614e-06, X_cutoff: 1000     <-- maximum possible
  X_max: 558
  Restart Sanity Check Passed...
  Validation Test Passed...
  min(H_r, H_c, H_I): 0.000000
  rc=0    errorLevel 0    "IID": true
```

`1e-400` underflows to zero. `errno` is set before the `strtod` call and never
tested, so `ERANGE` is ignored and `H_I` becomes `0`. With `H_I = 0` the §3.1.4.3
sanity-check cutoff is computed as **1000** — no constraint — and the validation
threshold `H_I/2` is `0`, so neither gate can fail. Both report PASS, exit
status is 0, `errorLevel` is 0.

### What this means for the harness

The published figure is `0.000000`, so a consumer reading
`min(H_r, H_c, H_I)` gets a useless number and will not mistake it for a good
one. **The exposure is in the verdict channel, not the figure.** If the harness
treats "the restart assessment passed" as a gate — exit status 0, `errorLevel 0`,
no error message — it will record a passed restart test for a run in which
neither restart test could have failed.

`0x0.8p0` is also accepted, as `0.5`, via C99 hex-float syntax. So is a leading
space. Trailing garbage, `nan`, `inf`, overflow and a locale comma are all
correctly rejected — the parse is strict apart from these.

### What the TruePad session can check

1. **How is `H_I` produced?** If it is formatted from a float, a very small or
   mis-scaled value becomes `1e-400`-shaped text rather than an error. If it is
   a literal or comes from a validated field, this is not reachable and should
   be recorded as such.
2. **Is `H_I = 0` meaningful to the harness?** An entropy claim of zero makes
   both gates vacuous. Rejecting it caller-side costs one comparison.
3. **Does the harness consume the restart verdict separately from the figure?**
   If it reads only `min(H_r,H_c,H_I)`, the conservative `0.000000` protects it.
   If it reads the pass/fail, it does not.

### A related gap the harness cannot work around

The JSON report contains **no `X_max`, no `X_cutoff`, and no
`passedRestartSanityCheck` field**. A sanity-check *failure* surfaces as
`errorLevel -1` with `errorMsg "Restart Sanity Check Failed."`; a *pass* has no
positive record, and the two numbers that decided it are stdout-only. So the
harness cannot audit the margin — it cannot distinguish a pass against a
legitimate cutoff from a pass against a cutoff of 1000. Fixing that is this
fork's work, tracked in `OC-11`; it is listed here so the harness does not
assume the information is available.

---

## XR-04 — a figure from these tools is uninterpretable without build provenance

**The most serious cross-repo finding so far — more serious than `XR-01`.**
Verified in this repository as `OC-10`, at fork commit `596cc2a`.

### The finding

The tools behave differently depending on whether they were compiled with
`-DNDEBUG`, which **no target in `cpp/Makefile` sets** but which release
configurations in common build systems add by default. On one input the
difference is not a rounding detail:

| build | same commit, same data |
|---|---|
| asserts live | `rc=134` SIGABRT, no JSON, **no figure** |
| `-DNDEBUG` | `rc=0`, `errorLevel 0`, `"IID": true`, **`hAssessed 0.995373734104443`** |

The chain: `p_colPower` underflows to zero at `shared/lrs_test.h:683`,
`log1pl(-0.0)` is `-0.0`, and the verdict
`logl(0.999) >= N*logProbNoColsPerPair` evaluates **false** — so the
longest-repeated-substring test reports **failure having detected nothing about
the data**. A second defect (`C03`, open on `master`) discards that failure, and
the tool publishes **≈0.9954 bit/bit**, above the 0.5 threshold Chor–Goldreich
needs.

**Nothing in the JSON records which build produced it.** Not the flags, not
`sizeof(long double)`, not the NDEBUG state. So a figure carries no evidence of
its own interpretability.

### Why this outranks XR-01

`XR-01` was about **freshness** — a figure that was true of different data.
`XR-04` is about **interpretability** — a figure that may be an artefact of the
arithmetic. The same shape applies to both: **unknowable means refuse, not
assume.** But a stale figure is at least a real measurement of something,
whereas an NDEBUG figure on this path measures nothing at all, and it is high
rather than low — it clears the threshold twice over.

### What this fork has provided: a canary

`tools/build-provenance-canary.sh` in this repository, committed with this
finding. It takes a path to `ea_iid` and reports `ASSERTS-LIVE`, `NDEBUG`, or
`INDETERMINATE`. Demonstrated on all three outcomes, each guard shown failing:

| case | result | exit |
|---|---|---:|
| shipped Makefile build | `BUILD ASSERTS-LIVE` | 0 |
| `-O2 -DNDEBUG` build | `BUILD NDEBUG` | 0 |
| wrong tool (`ea_non_iid`) | `BUILD INDETERMINATE` | **3** |
| expected input digest deliberately wrong | refuses to classify | **2** |

It generates its input from a fixed seed (1,000,000 one-bit samples, implanted
repeat W=2000, SHA-256 `a803412ee2c496a6d1c8c047be641c5d8b502a9c7556f66d678b541ec19fb5f2`)
and **verifies that digest before classifying** — a declared-but-unchecked
expected digest would be the dead-assertion shape this canary exists because of.

**What the canary does not establish, and this matters:** it identifies the
NDEBUG state *only*. Not the commit, not the compiler, not any other flag — in
particular not `-ffloat-store`, which `cpp/Makefile` sets and which a packager
overriding `CXXFLAGS` also loses. Not that the binary is unmodified. And it is a
statement about the binary passed to it at the moment it ran, **not a property
of a figure produced earlier by some other binary**. A consumer that treats a
canary pass as full provenance has substituted one unknown for another.

**Platform coverage — corrected 2026-10-15.** The underflow bound is
`W > 1022` on a 64-bit `long double` (arm64) and `W > 16382` on 80-bit (x86-64).
The first version used `W = 2000` and was **arm64-only**. It now uses
**`W = 20000`**, which clears the stricter bound by 3618 binary orders and so
discriminates on either platform. Input digest is now
`327773dd47cc480794f205f306aadd20972e258d9b0b880b7d12ad992e0b468c`; all four
guards re-demonstrated at the new width.

**Honest limit on that claim:** the arm64 behaviour is measured (asserts-live
`rc=134`; NDEBUG `rc=0` with `hAssessed 0.9959462013452722` and the LRS test
reporting failure). **The x86-64 side is an exponent-range argument, not an
observation** — no x86-64 build was run against it here. The audit has a
working Docker amd64 route if that measurement is wanted.

See `REPRO-01` for the separate finding that this same divergence is itself a
reproducibility defect: two conforming builds of one commit disagree about
whether a figure exists.

### What the harness session needs to decide — not done here

These are TruePad's, and this session has not touched them:

1. **Refuse any figure whose build provenance cannot be established.** Same
   shape as the `XR-01` freshness rule.
2. **Establish provenance by the strongest available means, and record which.**
   Building the tools from the pinned commit with known flags is strictly
   stronger than the canary. The canary is for consumers who did not compile
   them, and it answers one bit.
3. **Add the failure shape** — distinct from the existing four.
4. **Test it with the defect staged**, as was done for `XR-01`: a figure
   present, provenance unestablishable, harness refuses, and the figure appears
   nowhere in the output.
5. **`docs/WHAT-IS-LEFT.md`** is TruePad's file. Its current statement — that no
   min-entropy figure should be treated as a floor until `C23` and `C22` are
   verified — is **stale in one part and understated in another**:
   - `C22` was re-classified **CONSERVATIVE and closed** at fork commit
     `44baeba` (`OC-12`): its `ZALPHA` item measured +3.80e-06 bit and is not a
     defect, `N == 1` yields zero entropy, and `P_local`'s quantisation is
     conservative at every extreme tested.
   - `C23` was **verified permissive** at fork commit `301fae0` (`OC-7`): the
     restart cutoff is a Monte Carlo order statistic where §3.1.4.3 prescribes a
     closed form, more permissive at all nine H_I values tested, up to 0.341 bit
     of equivalent slack, with a window of false acceptance demonstrated.
   - The stronger statement, from `OC-10` at fork commit `596cc2a`: **no figure
     from these tools is interpretable at all until build provenance is
     established**, and because the `C07`/`C03` chain publishes ≈0.9954 bit/bit
     from an underflow, **a wrong figure can be high rather than low.** A floor
     is the wrong frame — the failure is not conservative.

Fork commits for each fact, per the provenance mechanism being added:
`596cc2a` (`OC-10`, the NDEBUG flip and the chain), `301fae0` (`OC-7`, C23),
`44baeba` (`OC-12`, C22 closed), `d6004a9` (`OC-11`, the H_I chain),
and this commit for the canary.

---

## XR-05 — two hard requirements for OneRNG raw capture, both from firmware source

Established from `github.com/OneRNG/firmware` `cdc_app.c` (repo last pushed
2015-06-18). Full working in `ONERNG-RAW-MODE-FROM-SOURCE.md`. Relevant only if
a OneRNG is acquired; recorded now so it is not rediscovered during capture.

Raw avalanche with the whitener off and RF off is **`cmd1`** — the mode digit is
a bitmask (bit 0 disables CRC16 whitening, bit 1 enables RF, bit 2 disables
avalanche), and the firmware permits it with no restriction.

### 1. Re-send the mode command every session; it cannot be read back

The mode lives in three `__bit` RAM variables with compile-time initialisers
(`no_crc=0`, `no_avalanche=0`, `rf_source=0`). The device therefore powers up in
**`cmd0` — avalanche, whitened** — and there is **no persistence**: no flash or
EEPROM write of the mode exists in the firmware. A selection survives only until
the next power-cycle, re-plug or host reset.

**A reverted mode produces whitened output that is indistinguishable from raw
output at the byte level.** The firmware offers no command to read the current
mode back, so the harness cannot verify it — only re-assert it. Send the mode at
the start of **every** capture session, not once at setup.

### 2. Do not let the device's pool overflow, or the data is XOR-mixed

`queue_pool_data` has two paths, and **the whitener setting gates neither**:

- pool not full → `*pool_in++ = x`, stored verbatim
- **pool full → `*pool_update++ ^= x`, XORed into an existing stored byte**

`POOL_SIZE = 7168` (`Makefile:61`). At the community figure of 0.35 Mbit/s
(≈43,750 B/s) the pool fills in **≈0.164 s**, so a read gap beyond roughly
**160 ms** begins silently XOR-mixing samples.

**The direction matters:** XOR-combining independent samples *raises* apparent
entropy per bit. An overflowing capture measures a min-entropy rate **higher
than the source deserves** — permissive, which is the dangerous direction. This
happens with `cmd1` set, because the overflow path ignores the whitener bit.

So raw capture must sustain reads without stalling for a sixth of a second. A
disk flush, a log write or a scheduler hiccup crosses that threshold.

*(7168 is exact, from the Makefile. The 160 ms derives from a community
throughput figure rather than a vendor specification, so treat it as the right
order of magnitude and leave margin.)*

### Not established

Whether a currently-shipping hardware **V3** unit runs firmware matching this
2015 source. Note the naming trap: hardware "V3" and firmware "Version 3" are
unrelated and the coincidence is misleading. `cmdv` reports the firmware version
and should be checked on receipt, before the unit is trusted for assessment.

No min-entropy-per-bit claim exists for this device in any source examined, so
there is nothing to record even as a claim. The real figure waits for the tools —
and, per `XR-04`, for build provenance.

---

## XR-06 — the SP 800-90B verdict can be unchanged by a 40 σ defect, so the tools' output is not sufficient on its own

**Finding only. Reported, not acted on — this is TruePad's file and TruePad's
change to make.** Evidence: `SECOND-SOURCE-SEARCH.md` Parts 8-10 (OC-15, OC-16,
OC-17), reproducible from `generators/blindspot_streams.py`.

### The measurement

A 1,000,000-sample binary stream carrying a **+40.4 σ** autocorrelation at lag
5000 was assessed by `cpp/ea_non_iid` built from `dd2996f` with the repository's
own flags (asserts live):

| | value |
|---|---|
| `H_original` on the defective stream | **0.856713** |
| clean fair-coin range, 5 independent streams | **[0.843936, 0.865774]** |
| position within that range | **+0.23 sd from the clean mean** |
| estimator that detected it | LRS, −0.0223 |
| LRS's distance above the binding minimum | **+0.1164 bit** |
| `tools/outside-battery-check` on the same stream | **40.21 σ at lag 5000** |

**The verdict was statistically indistinguishable from clean.** Not because any
estimator is individually blind, but because the verdict is `min` over ten
estimators, Compression binds at 0.8546 ± 0.0092 on near-uniform data, and the
nine others sit 0.060-0.143 bit above it. A detection that is not the minimum
does not reach the figure. `DEFECT-SHAPES.md` `SHAPE-07`.

### What this means for the harness

1. **A passing SP 800-90B figure is not sufficient evidence that a source is
   sound.** The harness currently treats the tools' output as the authority on
   the source. On this evidence it cannot be the only authority.
2. **Run an outside-the-battery check alongside the tools**, and **refuse — or at
   minimum flag — when it fires regardless of what the battery reports.** A
   figure that passes the battery and fails autocorrelation is the exact case
   this finding exists to catch, and the battery will not mention it.
3. **Store the per-estimator breakdown, not the minimum — and COMPARE each
   estimator against a baseline.** Storing it is necessary but not sufficient.
   `OC-18` found a case that makes this concrete: `G_xor13_02` (a third-order
   XOR structure at 2 %) produces `H_original = 0.860003`, **inside** the clean
   range, **and** a silent outside-battery check, while **MultiMMC drops 0.0266,
   which is 9× its 3 sd**. The defect exists *only* in the breakdown. But a
   logged reading of `MultiMMC = 0.9697` is unremarkable in isolation — it is
   meaningful only as **−0.0266 against 0.996306 ± 0.000986**. **A harness that
   logs the breakdown without a baseline holds the evidence and cannot read
   it.** A drop of 0.05 bit in MultiMMC is invisible in the scalar and
   significant against the baseline.

   **Which baseline — and this is the part that constrains the design.** The
   fair-coin baselines measured here are tight enough to serve as the method's
   noise-floor reference (predictor sd 0.0005–0.0010, so a 0.027 bit drop is
   27 sd) but they are **the wrong baseline for a real device**: a real source is
   not at 1.0 bit/bit, and at ~0.7–0.86 the estimators stand in different
   relationships — **Compression may not be the binding estimator at all**, which
   would invalidate the headroom table rather than shift it. The baselines also
   depend on sample count and symbol width. **So the harness needs per-device
   baselines**, taken from that unit's own real captures when believed healthy,
   with known build provenance (`XR-04`) — a drift detector, not an absolute
   one. Per-device baselines are claims about a **source**, so they must never be
   synthesised.
4. **Keep the two checks separate in the record.** The spectrum reads this same
   stream at 15.7×, *below* the clean maximum of 20.3× — it does not see it.
   Autocorrelation and spectrum are complementary; neither alone suffices, and a
   harness that runs one and reports "outside-battery check passed" is making a
   claim it has not tested.

### Scope limits the harness must carry forward

`tools/outside-battery-check` finds **linear** correlation at the **lags
tested**. It is blind to nonlinear structure (`x_i = x_{i-k} XOR x_{i-m}` has
zero autocorrelation everywhere) and to lags above `--max-lag`. Its thresholds
are calibrated for 1,000,000 one-bit samples and are **not** universal. **A pass
is the absence of one kind of evidence, not an entropy claim** — if the harness
surfaces it as "verified independent" it will have overstated it exactly the way
the battery does.

### Pinned, so it cannot rot between now and January

`cpp/selftest/regression-outside-battery.sh` pins the measured outcomes — not
the threshold constants — and is itself **shown failing** against perturbed
builds: a broken bit-reversal and a 1e-3 twiddle error each fail B's spectral
peak; `sqrt(N)` for `sqrt(N−k)` fails E's sigma; lowering the spectral threshold
fails both the clean-stream check and the `OC-18` coverage check. Measured
coverage limit, recorded: a twiddle error of 1e-5 or smaller is **not** caught.
The corpus regenerates from seeds and is digest-verified, because a seed that
does not reproduce is not a pin.

### Status

**Instrument claim, VERIFIED** against known input — see Part 11 for why
synthetic data is the correct and only way to establish that, and why it does
not breach *no claim upgrades from synthetic evidence* (which governs claims
about **sources**). **No hardware claim is upgraded; physical items stay NOT
RUN; the 0.696 stays uninterpretable pending build provenance.**

---

## XR-07 — a defect can be invisible to the battery AND to the outside check; the breakdown needs a per-device baseline, and that baseline can never be synthesised

**Finding only. Reported, not acted on — TruePad's file, TruePad's change.**
State read: `master @ 7e24e8b` (== `origin/master`). Evidence:
`SECOND-SOURCE-SEARCH.md` Parts 12-13, `ORCHESTRATOR-CHECKS.md` OC-18/OC-19.
Reproduce with `generators/blindspot_streams.py`.

**Sent now because TruePad is building the baseline comparison, and the second
half changes what should be built.**

### Half 1 — the case is real, so storing the breakdown is not sufficient

`G_xor13_02`: `x_i = x_{i-1} XOR x_{i-3}` with probability 2 %, else a fair coin.
1,000,000 one-bit samples, globally unbiased.

| | measurement |
|---|---|
| `H_original` | **0.860003 — INSIDE** the clean range [0.843936, 0.865774], +0.6 sd |
| Compression (binds) | +0.0054 — 0.3 × its 2 sd, **noise** |
| **MultiMMC** | **−0.0266 — 9.0 × its 3 sd, strongly real** |
| MultiMMC headroom | 0.1417 — the drop is **5× too small to bind** |
| `outside-battery-check` | **4.30 σ / 16.5× — SILENT on both checks** |

**Both tools report clean. Only the per-estimator breakdown sees it.** The band
is p ≈ 1–2 %, bounded below by MultiMMC's noise and above by Compression's
(Compression tracks MultiMMC at ≈0.76× with a 20× larger noise floor).

**Therefore:** storing the breakdown is necessary but **not sufficient** — the
harness must **compare each estimator against a baseline**, because
`MultiMMC = 0.9697` is unremarkable in isolation and damning as **−0.0266 against
0.996306 ± 0.000986**. **A scalar figure without that comparison cannot be
published**, and a harness that logs the breakdown without a baseline holds the
evidence and cannot read it.

### Half 2 — the baselines are NOT transferable. This is a constraint on the store.

The baselines in `OC-16` were measured on **fair-coin data at ~1.0 bit/bit**.
They are a **method demonstration**: they establish the noise floors (predictor
sd 0.0005–0.0010, so a 0.027 bit drop is 27 sd) and nothing about any device.

**At a real unit's 0.7–0.86 bit/bit, Compression may not be the binding estimator
at all — which would invalidate the headroom table rather than shift it.** The
noise floors also depend on sample count and symbol width, so they are a function
of the capture configuration, not constants.

**A real unit needs its own baseline, from its own real captures, with known
build provenance (`XR-04`) — and those are SOURCE claims, which stay NOT RUN
until hardware exists.**

**So the baseline store must, by construction:**

1. **Be keyed per device**, not per model. Two units of one design are two
   sources, so unit A's baseline is synthetic evidence with respect to unit B.
   Record serial and batch markings alongside (Part 4 item 1).
2. **Refuse to compare a capture against a baseline measured on a different
   device.** Not warn — refuse.
3. **Refuse to compare against a baseline derived from synthetic data**, which
   means the store must record each baseline's provenance as *real capture* or
   *synthetic*, and never silently promote the latter. A synthetic baseline is
   worse than none: it yields confident-looking deltas against a reference that
   measured nothing.
4. **Refuse to compare across capture configurations** (sample count, symbol
   width) or across assessing-binary provenance, since both move the baseline.
5. **Record the binding estimator per baseline.** If it is not Compression for a
   given device, any headroom reasoning imported from this audit does not apply
   to that device.

These are design constraints, not notes for the user of the store. The canonical
statement of why (3) is non-negotiable is `SECOND-SOURCE-SEARCH.md` Part 11:
synthetic data establishes claims about **instruments**, never about **sources**,
and a per-device baseline is a source claim.

### The thing that makes the band findable — needed by whoever builds detection

**Tap choice decides whether the structure is linearly visible, and a naive
attempt to reproduce this case will fail without knowing it.**

In ±1 terms XOR is multiplication, so the pairwise correlation
`E[x_i x_{i-d}] = p·E[x_{i-a} x_{i-b} x_{i-d}]` is a **triple** product, which
vanishes **unless the three indices close through the recurrence**.

- **Taps whose sum is itself a tap CLOSE the triple product and fire the
  autocorrelation check.** Taps (1,2): `a+b = 3` is a tap, so
  `x_{i-1}x_{i-2}x_{i-3}` closes and the check fires at **+50 σ at lag 3**. I
  predicted silence here and was wrong; that is how the mechanism was found.
- **Taps whose sum is not a tap are silent.** Measured at p = 0.3, max |z| over
  lags 1..400: (1,3) −3.51, (2,5) +3.28, (3,7) +2.98, (7,16) −3.17, (11,16)
  −2.82 — all indistinguishable from clean.

So (1,2) is the counterexample, not the case; it is kept in the corpus as
`F_xor30` for exactly that reason. **Anyone reproducing this must pick taps whose
sum is not a tap**, or they will get a 50 σ autocorrelation hit and conclude the
combined blind spot does not exist.

### Status

**Instrument claim, VERIFIED** and pinned by
`cpp/selftest/regression-outside-battery.sh`, which is itself shown failing
against perturbed builds (OC-19) and which asserts `G_xor13_02` stays **silent**
— if a future check fires on it, coverage has changed and this finding must be
re-documented rather than the change accepted. **No hardware claim is upgraded.
Physical items stay NOT RUN. 0.696 stays uninterpretable pending build
provenance.**

## XR-08 — INDETERMINATE from the pre-2026-10-18 canary against merged master means the canary is stale, not that provenance is unknowable; here is the replacement

**Finding only. Reported, not acted on — TruePad's harness, TruePad's change.**
State read: fork `master @ 9560e8f` plus this commit; the merge is `d226f18`.
Evidence: `logs/merge/canary-*.log` (old canary, both builds INDETERMINATE),
`logs/merge/canary3-*.log` (new canary, all five outcomes),
`logs/ndebug/postmerge-build-differential.log`.

**Sent now because the integration is broken as of `d226f18`.** TruePad built
a refusal around the canary's `XR-04` answer — INDETERMINATE ⇒ refuse the
figure — and that was right. But the repair merged on 2026-10-15 makes
asserts-live and `-DNDEBUG` builds of `ea_iid` behave identically on the
canary input (that was the point: `C07` closed at the root, build-differential
PASS), so the old canary, which only knew the two *unrepaired* signatures,
returns INDETERMINATE for **every** binary built from master at or after
`d226f18`. Measured, both builds. Under the existing refusal rule TruePad now
rejects every figure the repaired tool produces.

### What changed and why the old question is moot

The old canary asked "asserts live or NDEBUG?" because the unrepaired tool gave
a different answer in each build. On the repaired tree the answer is the same
in both, so the question has nothing behind it. **The question with something
behind it is: is this binary from the repaired tree or the unrepaired one?**
The same control input (1,000,000 bits, a 20,000-bit exact repeat implanted,
digest `327773dd…`) discriminates it, because the two trees cannot both be
right about it.

### The replacement — `tools/build-provenance-canary.sh`, re-signatured, three outcomes

| outcome | signature on the control input | stdout | exit |
|---|---|---|---|
| **REPAIRED** | exit 1, `IID test suite failed`, JSON `errorLevel 2`, **no** `hAssessed` — identical in either build | `canary: TREE    REPAIRED` / `canary: BUILD   NOT-DISTINGUISHED` | 0 |
| **UNREPAIRED** / asserts live | SIGABRT 134, `Assertion failed` naming `lrs_test.h` | `canary: TREE    UNREPAIRED` / `canary: BUILD   ASSERTS-LIVE` | 0 |
| **UNREPAIRED** / NDEBUG | exit 0, LRS failure reported, a figure published | `canary: TREE    UNREPAIRED` / `canary: BUILD   NDEBUG` | 0 |
| **INDETERMINATE** | none of the above | `canary: TREE    INDETERMINATE` / `canary: BUILD   INDETERMINATE` | 3 |

The build distinction is kept as a sub-result under UNREPAIRED because it still
matters for the reference figure built from tag `unrepaired-reference-2026-10-15`.

**Demonstrated, all four builds plus a control, arm64, 2026-10-18:**

| binary | from | canary says | exit |
|---|---|---|---|
| `ea_iid` asserts live | master `d226f18` | TREE REPAIRED, BUILD NOT-DISTINGUISHED | 0 |
| `ea_iid -DNDEBUG` | master `d226f18` | TREE REPAIRED, BUILD NOT-DISTINGUISHED | 0 |
| `ea_iid` asserts live | tag `unrepaired-reference-2026-10-15` (`655bd10`) | TREE UNREPAIRED, BUILD ASSERTS-LIVE | 0 |
| `ea_iid -DNDEBUG` | tag | TREE UNREPAIRED, BUILD NDEBUG | 0 |
| `/bin/ls` (guard shown failing) | — | INDETERMINATE | 3 |

The last row matters: `ls` exits 1 too, and the REPAIRED signature did **not**
fire on a bare exit 1 — it needs the suite-failed line, `errorLevel 2` and the
absence of `hAssessed` together.

**Platform limit, corrected in `OC-24` (2026-10-18).** "arm64" here is Apple
arm64, where `long double` is IEEE double (53-bit, emin −1021) — the
*narrowest* of the three formats a build can land on; x87 extended (x86-64) and
binary128 (Linux aarch64) share emin −16382. At W = 20000, `p_col^W = 2^-20000`
is below the subnormal floor of all three, so the unrepaired signatures are
format-independent by the arithmetic; the REPAIRED signature is a verdict with
a 13842 log-unit margin, not an underflow. **Measured on the IEEE-double
format only; the wide formats are a bounded argument (`OC-24`), and the one
thing that would settle them is a single canary run on an x86-64 host.**

### What TruePad should change

1. **Parse `canary: TREE`** and treat `REPAIRED` as the acceptable provenance
   for a figure from the repaired fork, `UNREPAIRED` as the provenance for the
   reference figure (two-figure rule), and `INDETERMINATE` as a refusal, as now.
   The old `canary: BUILD   ASSERTS-LIVE | NDEBUG` strings still appear, under
   UNREPAIRED only; `NOT-DISTINGUISHED` is new and is the expected value for a
   repaired binary.
2. **Do not read `BUILD NOT-DISTINGUISHED` as a gap.** It is the repair working.
   NDEBUG provenance on the repaired tree is not establishable by behaviour on
   this input and does not need to be: the two builds agree.
3. **Keep the standing caveats.** `REPAIRED` is not `REVIEWED` — the repairs are
   self-authored and unreviewed, and a canary result is about the binary at the
   moment it ran, not about a figure produced earlier. `productionApprovalEnabled`
   stays false and `approvedBuilds` stays empty on this finding's account; it
   restores the ability to *interpret* a figure, not the authority to approve one.

## XR-09 — the build-state gap in TruePad's qualification record is moot for a repaired binary; the field it needs is TREE first, BUILD only under UNREPAIRED

**Finding only. Reported, not acted on — TruePad's record, TruePad's change.**
State read: fork `master @ b12247c` plus this commit. Evidence:
`logs/merge/canary3-*.log`, `logs/ndebug/postmerge-build-differential.log`,
`OC-24`, `OC-25`.

TruePad's `QUALIFICATION-BINDING.md` names exactly one gap in its qualification
record: the **build state of the binary** (`XR-04`), which the CLI path does not
record. That gap was real when it was recorded, because the unrepaired tool
gave a different answer in each build on one input. **Post-repair it is moot —
for a repaired binary.** `XR-08`'s table shows master's asserts-live and
`-DNDEBUG` builds both classified `TREE REPAIRED, BUILD NOT-DISTINGUISHED`, and
the build-differential shows them refusing identically. There is no build state
to record for a repaired binary because the two builds are identical in the
dimension that used to matter; a field demanding one would stay empty forever
and read as an open gap that is not one.

**Scope, precisely.** The question is moot **only when `TREE` is REPAIRED.** An
UNREPAIRED binary — the reference build from tag
`unrepaired-reference-2026-10-15`, which the two-figure rule requires TruePad to
keep producing — still has a build state that changes its behaviour: asserts
live aborts, `-DNDEBUG` fabricates a figure silently (`XR-04`). So:

| `TREE` | `BUILD` | meaning for the record |
|---|---|---|
| REPAIRED | NOT-DISTINGUISHED | the expected pair for a figure from the repaired fork; no build state exists to record |
| UNREPAIRED | ASSERTS-LIVE | the reference tool, fail-closed on the canary input; its figure is reportable *as the reference* |
| UNREPAIRED | NDEBUG | the reference tool with the defect firing silently; **any figure uninterpretable** |
| INDETERMINATE | — | refuse, as now |

**What the field should hold instead.** `TREE` first, with `BUILD` meaningful
only when `TREE` is UNREPAIRED — plus enough to identify the binary itself,
which the canary deliberately does not establish: **the SHA-256 of the
executable**, or the commit plus compiler and flags. The canary result is a
statement about the binary at the moment it ran; the hash is what ties a stored
figure to that binary later. `OC-25` shows the shape: a tag-built `ea_iid`
with its digest `5bece408…` and its canary line beside it.

**Standing caveats, unchanged.** `REPAIRED` is not `REVIEWED` — the repairs are
self-authored and unreviewed. `OC-24`: every canary signature is measured on
the IEEE-double `long double` format only; the wide formats are a bounded
argument, and if TruePad ever runs on x86-64 the one thing to do is run the
canary once there. `productionApprovalEnabled` stays false and `approvedBuilds`
stays empty on this finding's account.

## XR-10 — the restart acceptance decision must not come from an unrepaired ea_restart; January's run is the one at risk

> **SUPERSEDED — 2026-10-19, see `XR-11`. What changed: the direction.** This
> finding told TruePad to decide restart acceptance with §3.1.4.3's printed
> binomial formula, which I had called exact. That formula is not the
> probability of the event being tested and rejects correctly-operating sources
> — 83.2 % of full-entropy 8-bit matrices, measured (`OC-30`) — so following
> this guidance would have disqualified a sound device in January. Kept, not
> deleted, because a cross-repo finding that silently changed meaning is worse
> than one that was wrong. **The gap table below is still correct arithmetic;
> only its interpretation is inverted** — the "counts the old tool accepts that
> the standard rejects" column is in fact a list of counts the standard wrongly
> rejects.

**Finding only. Reported, not acted on — TruePad's procedure, TruePad's change.**
State read: fork `master` after `OC-29`. Evidence: `OC-27` (mechanism, exact
model, anchor), `OC-29` (repair and matrix), `logs/c23/`.

**Why this is time-sensitive.** TruePad's restart evidence is physical and NOT
RUN; the hardware testing is planned for January 2027. When it happens, the
restart acceptance decision will come from `ea_restart`, and every `ea_restart`
built before the `C23` repair takes a cutoff 2–5 counts above the one SP 800-90B
§3.1.4.3 specifies. A restart matrix could therefore pass in January and be
recorded as accepted when the standard's own test rejects it. **Nothing is
contaminated today precisely because nothing has been run.** That is the only
reason this is cheap now.

### 1. The size of the correction at each H_I

Exact cutoffs at the standard's α = 0.000005 (`restart_cutoff_anchor.py`,
exact rational arithmetic, cross-checked three ways) against the pre-repair
tool's measured cutoffs:

| H_I | standard's cutoff | pre-repair tool | counts the old tool accepts that the standard rejects |
|---:|---:|---:|---|
| 1 | 570 | 571–572 | 571–572 |
| 2 | 312 | 316 | 313–316 |
| 3 | 173 | 177–179 | 174–178 |
| 4 | 99 | 103–104 | 100–104 |
| 5 | 58 | 63 | 59–63 |
| 6 | 36 | 40 | 37–40 |
| 7 | 23 | 27 | 24–27 |
| 7.5 | 19 | 22–23 | 20–22 |
| 8 | 15 | 19 | 16–19 |

Non-integer H_I in steps of 0.25 are in `regression-restart.sh`'s pinned
table. The device's H_I is not known yet; whichever row it lands on, the
window of counts the old tool wrongly accepts is the last column.

### 2. Compute the decision with the exact oracle until the repair is in the binary you invoke

Until the `ea_restart` TruePad actually invokes carries the `C23` repair
(`OC-29`), **the acceptance decision is to be computed from the data, not read
from the tool's verdict**: take `X_max` and `H_I`, and decide with
`oracles/restart_decision_exact.py` (or any evaluation of §3.1.4.3 step 5 at
α = 0.000005). A repaired `ea_restart` prints the exact cutoff and writes
`restartXmax`, `restartXcutoff` and `passedRestartSanityCheck` into its report,
so the same recomputation can be made from the report; an unrepaired one prints
`X_max` only with `-v` and writes none of them.

**Which binary has the repair is a question of the binary's identity, per
`XR-09`** — the executable's hash, or the commit plus compiler and flags —
not of the canary, which classifies `ea_iid`, and not of the tool's output
looking plausible. A quick discriminator for `ea_restart` specifically: the
repaired tool refuses a bare `H_I` on a multi-bit symbol and prints
`X_cutoff: … (exact binomial tail, SP 800-90B 3.1.4.3 step 5)`; the
unrepaired tool accepts the bare number and prints the simulated cutoff.

**The `C16` half of the same repair changes the call.** For a symbol wider
than one bit the repaired `ea_restart` requires the scale: `<value>/symbol`
or `<value>/bit`; a bare `H_I` is refused. If TruePad passes the per-bit
figure from `ea_non_iid` (`h'`, see `C02`), write it as `<h'>/bit`; if it
passes the per-symbol figure, `/symbol`. A bare number that used to be accepted
at the wrong scale produced a cutoff tens of counts too permissive (`OC-29`
matrix, 615 against 23) with no error.

### 3. A run made before the repair is not upgraded by the repair landing afterwards

A restart assessment decided by an unrepaired binary stays an unrepaired
decision when the repair is merged or deployed. It has to be **re-decided from
its data** — `X_max` and `H_I` through the exact test — or the capture re-run
through a repaired binary. The record of a restart acceptance should therefore
carry `X_max`, `H_I`, the cutoff used and the binary's identity, so that
re-deciding is a computation and not a repeat of the physical test.

**Standing caveats.** The repair is self-authored and unreviewed; merging it
does not change that. This finding decides nothing about any device: physical
items stay NOT RUN. The conformance finding is upstream's (`OC-27` addendum);
whether the standard's single-binomial test or the tool's max-over-cells
statistic is the better null is an open question about the standard and does
not change what a lab claiming SP 800-90B conformance has to run.

## XR-11 — decide restart acceptance with the corrected cutoff, and record the printed-formula value beside it (supersedes XR-10)

**Finding only. Reported, not acted on — TruePad's procedure, TruePad's change.**
Supersedes `XR-10`, whose direction was inverted. Evidence: `OC-30`; Hill/UL
formal comments on SP 800-90B (final) v1.9, 2019-12-12, Table 3 and Section 3.2;
upstream issue usnistgov/SP800-90B_EntropyAssessment#56.

**Still time-sensitive, and for the opposite reason.** TruePad's restart
evidence is physical and NOT RUN, with hardware testing planned for January
2027. `XR-10` would have had TruePad decide that run with SP 800-90B
§3.1.4.3's printed binomial formula. That formula tests the wrong distribution:
the value measured is the maximum count of the row/column-specific most likely
symbol — a multinomial maximum — not one symbol's binomial count. A cutoff
derived from it **fails correctly-operating sources**, measured on synthetic
full-entropy data at 2000 matrices per width:

| symbol width | printed-formula cutoff | false rejects | corrected cutoff | false rejects |
|---:|---:|---:|---:|---:|
| 1-bit | 570 | 1.40 % | 572 | 0.75 % |
| 2-bit | 312 | 3.15 % | 316 | 0.65 % |
| 4-bit | 99 | 11.65 % | 104 | 0.90 % |
| 8-bit | 15 | **83.20 %** | 19 | 0.20 % |

against the 1 % the standard targets. A sanity-check failure means **no entropy
estimate is awarded at all**, so at 8-bit symbols `XR-10`'s instruction had
roughly five-in-six odds of disqualifying a sound device.

### What to do instead

1. **Decide with the corrected cutoff** — the exact distribution of the
   multinomial maximum at α = 0.000005 under the worst-case symbol
   configuration. `oracles/restart_multinomial_max.py` computes it standalone;
   `oracles/restart_decision_exact.py` applies it to an `ea_restart -v` log; and
   an `ea_restart` carrying the fork's `OC-30` repair computes it itself and
   writes `restartXcutoff` with `restartCutoffMethod =
   exact-multinomial-maximum`. The cutoffs for integer widths are 572 (1-bit),
   316 (2-bit), 104 (4-bit) and 19 (8-bit) at full entropy; the full table in
   0.25-bit steps is pinned in `cpp/selftest/regression-restart.sh`.
2. **Record the printed-formula value beside it, for traceability, not for the
   verdict.** A repaired `ea_restart` reports it as
   `restartXcutoffPrintedBinomial` / `X_cutoff_printed_binomial`. A laboratory
   claiming SP 800-90B conformance needs to be able to show what the printed
   procedure would have said and why it was not used; that is the conformance
   record, and the reason is `OC-30`.
3. **Treat a verdict computed from the printed binomial formula alone as not
   decisive in either direction.** It is too strict to use as a rejection and it
   is not the tool's own statistic, so it supports neither outcome by itself.
4. **Upstream's unrepaired `ea_restart` is acceptable for this decision**, which
   `XR-10` got wrong: its simulated cutoff targets the correct statistic
   (upstream issue #56 asked for exactly that) and lands within a count or two
   of the exact value. Two caveats: it varies run to run where the distribution
   is flat — measured 571/572/573 at H_I 1 over eight runs — and it records
   neither the cutoff nor `X_max` in its report, so the decision cannot be
   re-checked from the report afterwards. Prefer a repaired binary; if one is
   not available, capture the `-v` output.
5. **`XR-09`'s binary-identity requirement still holds**, with "repair" now
   meaning the corrected statistic. A quick discriminator for `ea_restart`:
   the repaired tool prints `X_cutoff: … (exact distribution of the multinomial
   maximum …)` plus an `X_cutoff_printed_binomial` line, and refuses a bare
   `H_I` on a multi-bit symbol; upstream's prints a simulated cutoff and accepts
   the bare number. The identity itself is still the executable's hash, or the
   commit plus compiler and flags.
6. **A pre-repair run is not upgraded by the repair landing afterwards** — also
   unchanged. It is re-decided from its data (`X_max` and `H_I` through the
   corrected test) or the capture is re-run. Record `X_max`, `H_I`, the cutoff
   used, the method, and the binary's identity, so re-deciding is a computation
   and never a repeat of the physical test.

### The C16 half of the fork's repair is unaffected and still changes the call

For a symbol wider than one bit the repaired `ea_restart` requires the scale:
`<value>/symbol` or `<value>/bit`; a bare `H_I` is refused. Pass `ea_non_iid`'s
per-bit figure as `<h'>/bit` (see `C02` on reading `h'` rather than
`hAssessed`), or the per-symbol figure as `/symbol`. A bare number that used to
be accepted at the wrong scale produced a cutoff tens of counts wrong with no
error — measured 614 where 27 was intended (`OC-30` matrix).

**Standing caveats.** The repair is self-authored and unreviewed. This finding
decides nothing about any device: physical items stay NOT RUN. The upstream
defect is a documentation one — nothing in upstream's code records that it
deliberately departs from the printed procedure — and nothing is sent upstream
(decided 2026-10-15). Whether the standard's printed test or the multinomial
maximum is the right null is an open question about the standard, recorded in
`OC-30` as a question.

## XR-12 — the exit-status-then-report sequence is repaired on the fork side; does anything already recorded rest on it?

**Finding only, and a question. Reported, not acted on — TruePad's records,
TruePad's answer.** Evidence: `OC-31`; `XR-01`, `XR-04`, `XR-08`.

`C14`'s two permissive routes are closed on master (`OC-31`): a stale `-o`
report can no longer survive a failed run — including a usage-path exit, an
assert or a signal, which no "write an error report on every failure path" fix
would have caught — and `--version` is no longer honoured as a filename. Both
are shown failing against tag `unrepaired-reference-2026-10-15`.

**What this changes for TruePad.** The harness sequence `XR-01` describes —
check the exit status, then read the `-o` file — is now safe against both
routes **when the binary carries the repair**. Against an unrepaired binary it
is not, and the discriminator is the binary's identity (`XR-09`), not the
file's contents: a stale report is byte-identical to a valid one.

**A new field a consumer can use.** A repaired tool's placeholder carries
`reportComplete: false` with `errorLevel -1`. A report lacking `reportComplete`
is a *completed* report from a repaired binary (the key is written only by the
placeholder) — but it is **also** what every unrepaired binary writes, so the
key's absence is not evidence of either. Use it only in the positive direction:
`reportComplete: false` means refuse, unconditionally.

**The question, which this session cannot answer because it must not read
TruePad.** Does anything already in TruePad's records rest on that channel
having been trustworthy? On the fork's side the answer is no: nothing in this
repository's record reads a report file after an exit-status check, and every
physical run is NOT RUN, so no figure of record has passed through the
sequence. If the same is true on TruePad's side the exposure is entirely
prospective, like `XR-11`'s, and closing it is a matter of rebuilding before
January. If any stored verdict, approval record or cached figure was produced by
reading an `-o` file after an exit-status check from an unrepaired binary, that
record cannot be distinguished from a stale one after the fact and should be
re-derived from the inputs rather than trusted.

**Standing caveats.** The repair is self-authored and unreviewed.
`productionApprovalEnabled` stays false and `approvedBuilds` empty on this
finding's account. Nothing is sent upstream.

## XR-13 — at width 1, C23's correction is zero below H_I ≈ 0.989, so at TruePad's operating point the defect has no effect; here is the table to read a cutoff out of

**Finding only, and a table to use. Reported, not acted on — TruePad's
procedure, TruePad's change.** Evidence: `OC-30` (the mechanism and the exact
method), `OC-39`, `logs/width1/`. Supersedes `XR-11`'s implicit framing that the
C23 correction matters at every operating point; `XR-11`'s instructions stand,
and this says where they change nothing.

**The operating point.** TruePad invokes at **width 1**, raw one-bit-per-byte,
with `H_I` in bits per sample — which at width 1 is bits per bit — as a bare
number. So the 8-bit rows that carry C23's large effects are unreachable, and
not by a hard-coded literal: the width reaches `argv` from the record's own
value. `XR-11`'s table was computed at integer widths and its H_I = 1 row is
full entropy, which is not the device either. The device is quoted at roughly
**0.696 bits per bit** — a figure taken from the vendor's repository that this
project has never measured, and which stays **NOT RUN** until the hardware
arrives.

### The prediction, confirmed, and sharper than expected

The expectation put to this session was: as H_I falls below 1 the two cells
become asymmetric, the second cell's tail moves far out, the maximum over cells
converges to the dominant cell's count, and so the multinomial-maximum
correction shrinks toward zero — coinciding, or differing by one count,
somewhere well above 0.696, and identical at 0.696 itself.

**That holds, and the convergence is faster than "well above".** The two
cutoffs are **identical at every H_I from 0.50 to 0.989**. The gap is +1 at
0.99 and reaches +2 only at 0.999 and above. The mechanism is exactly as
described: at width 1 and H_I < 1 the worst case is **one** cell at
`p = 2^-H_I` plus a remainder cell at `1 − p`, and `P(max > m)` is
`P(n₁ > m) + P(n₁ < 1000 − m)`, whose second term is negligible once `p` is
clear of ½. At H_I = 1 exactly the cells are equal and symmetry doubles the
tail, which is the whole of the +2.

**At TruePad's quoted operating point the C23 defect has no effect.** At
H_I = 0.70 the printed-formula cutoff and the corrected cutoff are both **683**,
and the measured false-reject rate is 1.10 % against the 1 % the standard
targets. **The repair matters for the tool's correctness, not for this device.**

### Where the gap first becomes non-zero

**Between H_I = 0.989 and H_I = 0.990.** Computed: gap 0 at 0.982, 0.984,
0.985, 0.986, 0.988 and 0.989; gap +1 at 0.990 and 0.995; gap +2 at 0.999,
0.9999, 0.99999 and 1.000. So a future one-bit device is affected only if its
assessed entropy exceeds about 0.989 bits per bit — within roughly 1 % of full
entropy. **That boundary is the thing to re-check if a different device is
characterised**, and it is specific to width 1: at 8-bit the gap is 4 counts
and the printed formula rejects 83 % of full-entropy matrices (`OC-30`), so the
defect is a wide-alphabet phenomenon driven by the number of effective cells,
`2^H_I`.

### The table — read a cutoff out of this once the device is measured

Width 1, α = 0.000005 per experiment (SP 800-90B §3.1.4.3 step 1; family-wise
1 − (1 − α)²⁰⁰⁰ = 0.995 %, the standard's stated 1 % target). "Printed" is
step 5 as written; "corrected" is the exact multinomial maximum (Levin) that
the fork's repaired `ea_restart` computes. Measured rates are on 2000 full
1000×1000 matrices per row whose most likely symbol has probability exactly
`p`, so every rejection is a false one, with rows and columns both counted so
the dependence is included. 95 % intervals in brackets.

| H_I (bits/bit) | p = 2^−H_I | printed cutoff | corrected cutoff | gap | measured false-reject, printed | measured, corrected |
|---:|---:|---:|---:|---:|---|---|
| 0.50 | 0.707107 | 769 | 769 | **0** | 0.7500 % [0.3719–1.1281] | same cutoff |
| 0.52 | 0.697372 | 760 | 760 | **0** | 1.2500 % [0.7631–1.7369] | same cutoff |
| 0.54 | 0.687771 | 751 | 751 | **0** | 1.0000 % [0.5639–1.4361] | same cutoff |
| 0.56 | 0.678302 | 742 | 742 | **0** | 1.2000 % [0.7228–1.6772] | same cutoff |
| 0.58 | 0.668964 | 734 | 734 | **0** | 0.6500 % [0.2978–1.0022] | same cutoff |
| 0.60 | 0.659754 | 725 | 725 | **0** | 0.9000 % [0.4861–1.3139] | same cutoff |
| 0.62 | 0.650671 | 716 | 716 | **0** | 0.9500 % [0.5249–1.3751] | same cutoff |
| 0.64 | 0.641713 | 708 | 708 | **0** | 1.0500 % [0.6033–1.4967] | same cutoff |
| 0.66 | 0.632878 | 699 | 699 | **0** | 1.1500 % [0.6827–1.6173] | same cutoff |
| 0.68 | 0.624165 | 691 | 691 | **0** | 1.2500 % [0.7631–1.7369] | same cutoff |
| 0.70 | 0.615572 | 683 | 683 | **0** | 1.1000 % [0.6429–1.5571] | same cutoff ← TruePad's quoted operating point |
| 0.72 | 0.607097 | 675 | 675 | **0** | 0.9500 % [0.5249–1.3751] | same cutoff |
| 0.74 | 0.598739 | 666 | 666 | **0** | 1.2000 % [0.7228–1.6772] | same cutoff |
| 0.76 | 0.590496 | 659 | 659 | **0** | 0.9000 % [0.4861–1.3139] | same cutoff |
| 0.78 | 0.582367 | 651 | 651 | **0** | 0.9000 % [0.4861–1.3139] | same cutoff |
| 0.80 | 0.574349 | 643 | 643 | **0** | 1.1500 % [0.6827–1.6173] | same cutoff |
| 0.82 | 0.566442 | 635 | 635 | **0** | 1.1000 % [0.6429–1.5571] | same cutoff |
| 0.84 | 0.558644 | 628 | 628 | **0** | 1.1000 % [0.6429–1.5571] | same cutoff |
| 0.86 | 0.550953 | 620 | 620 | **0** | 1.0500 % [0.6033–1.4967] | same cutoff |
| 0.88 | 0.543367 | 613 | 613 | **0** | 0.7000 % [0.3346–1.0654] | same cutoff |
| 0.90 | 0.535887 | 605 | 605 | **0** | 1.1500 % [0.6827–1.6173] | same cutoff |
| 0.92 | 0.528509 | 598 | 598 | **0** | 1.2000 % [0.7228–1.6772] | same cutoff |
| 0.94 | 0.521233 | 591 | 591 | **0** | 1.0500 % [0.6033–1.4967] | same cutoff |
| 0.96 | 0.514057 | 584 | 584 | **0** | 0.7500 % [0.3719–1.1281] | same cutoff |
| 0.98 | 0.506980 | 577 | 577 | **0** | 0.8000 % [0.4096–1.1904] | same cutoff |
| 0.99 | 0.503478 | 573 | 574 | +1 | 1.20 % [0.86–1.54] | 0.90 % [0.61–1.19] |
| **1.00** | 0.500000 | 570 | **572** | **+2** | 1.70 % [1.30–2.10] | 0.93 % [0.63–1.22] |

The last two rows are the boundary, measured on 4000 matrices each. **At full
entropy the printed formula over-rejects**: 1.70 % against a 1 % target, which
the correction brings to 0.93 %. That is the same defect `OC-30` measured at
83 % on 8-bit data, here reduced to a factor of 1.7 because there are only two
cells.

### How to use it

1. **Measure the device**, then read the row. The cutoff to decide with is the
   **corrected** column; below 0.99 the printed column is the same number, so
   either reading gives the same verdict.
2. **Any H_I outside 0.50 to 1.00 needs a fresh computation, not
   interpolation.** The cutoff is an integer order statistic of a discrete
   distribution: it steps, and the step locations are not linear in H_I.
   `oracles/restart_multinomial_max.py` computes both columns at any H_I, and
   the fork's repaired `ea_restart` computes and reports both itself
   (`restartXcutoff`, `restartXcutoffPrintedBinomial`, `restartCutoffMethod`).
3. **A bare `H_I` is still refused by the repaired tool for widths above 1** —
   but at width 1 a bare number is accepted, because per-bit and per-symbol
   coincide there (`OC-29`). TruePad's invocation needs no change on that
   account.
4. **`XR-11`'s other items are unchanged**: record `X_max`, `H_I`, the cutoff,
   the method and the binary's identity; a decision made by an unrepaired
   binary is re-decided from its data, never upgraded by a later repair.

**Standing caveats.** The 0.696 figure is the vendor's and has never been
measured here; every number above is an instrument claim on synthetic data and
says nothing about any source. Physical items stay **NOT RUN**. The repairs are
self-authored and **unreviewed**. Nothing is sent upstream.

## XR-14 — R-1 does NOT reach TruePad's path: width 1 is not among the affected alphabet sizes, and the tool TruePad ships never calls the function

**Finding only, and an explicit all-clear with the list rather than safety
inferred from silence. Reported, not acted on.** Evidence: `OC-40`, `OC-41`,
`logs/r1/`, `logs/x86-64/05-r1.log`.

`R-1` is a live defect: on x86-64 Linux `ea_iid` aborts with SIGABRT and writes
no report on perfectly valid data whose symbol counts are exactly equal. The
entropy-tools gate runs on Linux, so the question is immediate.

### The answer is no, on three independent grounds

**1. The symbol counts observed to abort end-to-end are k = 3, 6, 7, 9 and 12,
and width 1 is not among them.** `k` is the number of **distinct observed
symbols** (`data.alph_size`), not `2^width`. Width 1 can only produce k = 1,
which the tool refuses earlier with "Symbol alphabet consists of 1 symbol", or
k = 2. **No power-of-two alphabet is affected, and that is arithmetic rather
than luck**: `1/2^j` is exactly representable, so every `p_i` equals `1/k`
exactly, `p_col = k·(1/k)²= 1/k` exactly, and the comparison holds with
equality. Measured through the production functions: of 255 alphabet sizes from
2 to 256, the affected set on arm64 is 117 values and **k = 2, 4, 8, 16, 32,
64, 128 and 256 are all safe**.

**2. `ea_non_iid` never calls the function.** `len_LRS_test` is called only from
`iid_main.cpp` and `restart_main.cpp` — the §5.2.5 IID test. The fork's record
is that TruePad **ships only `ea_non_iid`**, which cannot reach the assert at
any width or alphabet size. If the gate also invokes `ea_iid` or
`ea_restart -i`, those two can reach it — at affected alphabet sizes only, and
width 1 is not one.

**3. It requires EXACT balance.** Every symbol count must be exactly equal.
Moving **one sample** off balance clears it at every affected alphabet size (0
of 117), because `p_col` rises by about `2/L² = 2e-12` against a rounding
deficit of order 1e-17. Real noise never produces exactly equal counts; a
counter-mode or round-robin source, or a constructed test vector, does so
reliably.

So TruePad's January path is clear on the tool it ships, clear at the width it
invokes, and clear on the data a physical source produces. **That is an explicit
all-clear with the list, not an inference from silence.**

### What would change the answer

- Invoking `ea_iid` or `ea_restart -i` **at a width above 1** on data whose
  observed alphabet lands on an affected size **and** is exactly balanced. The
  affected set is platform-dependent: on x86-64 it includes small sizes
  (3, 6, 7, 9, 12) that arm64 does not.
- A **deterministic or counter-mode** source, or a synthetic test vector, at
  such a width — that is the realistic victim, and for a validation tool's own
  corpus it is a real problem.

### Status in the fork

**Repaired** (`OC-41`): the assert is replaced by a clamp to the Cauchy–Schwarz
bound `Σp² ≥ 1/k`, which is exact rather than a tolerance. It cannot change any
published figure, because `p_col` feeds only the §5.2.5 LRS decision and every
affected case previously produced no figure at all. The assert is **upstream
code**, unchanged by this fork until now, so a reader on Linux is looking at an
inherited defect. Nothing is sent upstream. Self-authored and **unreviewed**.
Physical items stay **NOT RUN**.
