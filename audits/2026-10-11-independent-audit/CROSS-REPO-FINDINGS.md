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
