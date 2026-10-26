# Orchestrator's own rechecks

Checks run directly by the coordinating session, independently of the finder
agents, on datasets the coordinator generated itself. They are recorded
separately so that the report's headline claims do not rest solely on a
subordinate agent's output.

This file is an **append-only dated record**. An entry is corrected by a later
entry, never by editing it: the earlier text is evidence of what was believed
when it produced a figure, and rewriting it would destroy the only account of
how a wrong figure got published.

> **RETIRED TERM — "certified floor".** Entries up to `OC-77` use the phrase
> *certified floor*. **It is retired as of `OC-78` (2026-10-21, F02).** No
> reading of the entropy floor is certified: `C22a` is a **product of two grid
> maxima** and `C22c`'s ceiling is a **scan maximum**, so the aggregate takes
> the weakest status of its terms and the label is now **MEASURED FLOOR**. The
> per-term status vocabulary — PROVED / DERIVED / MEASURED — is defined in
> `oracles/entropy_floor.py` beside the constants. Where an entry below says
> "certified floor", read "measured floor", and read `OC-78` for why.

---

## OC-1 — `ea_conditioning` width inference: `h_out` exceeds the output's bit ceiling

Rechecks finder candidate `conditioning-transpose-2` (High). **Confirmed, and
on a stronger basis than the finder claimed.**

### Construction

`generators/ct2_width_fixtures.py` builds two 1,000,000-byte files from one
SHA-256 counter stream (tag `orchestrator-ct2-recheck-2026-10-12`):

| File | Content | SHA-256 |
|---|---|---|
| `low7.bin` | seven pseudorandom bits per byte, MSB always **0** | `92e3e6060a67db94e0c8c887a8c11ed3def08ac15c661ea06dee56cfeaf3d014` |
| `msbset.bin` | the **same** seven bits per byte, MSB always **1** | `9f437ffa7628d4817a187585e75af62d6aaa78428cf380d0a16878bf03ee4561` |

The two files carry identical information — the same seven varying bits per
byte plus one constant bit. Any correct per-output-bit entropy rate must be the
same for both.

### Commands and results

```
ea_conditioning -n -i low7.bin   1024 8 8 1000
ea_conditioning -n -i msbset.bin 1024 8 8 1000
```

| File | inferred width | `h'` | `h' * n_out` | `(Non-vetted) h_out` |
|---|---:|---:|---:|---:|
| `low7.bin` | 7 | 0.8944051755544167869871 | 7.155241404435334295897 | **7.155241404435334295897** |
| `msbset.bin` | 8 | 0.5648118634409018401498 | 4.518494907527214721199 | 4.518494907527214721199 |

Identical on `master` (f069898), `repair/2026-10-09-verified-defects`
(2d4b135) and upstream (87c104d) — digit for digit. Raw output:
`logs/cond-width-inference-recheck.log`.

### Why this is a defect, stated minimally

Two consequences, the second of which needs no interpretation of the standard:

1. **Inconsistency.** Two inputs of identical entropy receive `h_out` figures
   differing by a factor of 1.5836. The difference is caused only by whether
   the constant bit is a 0 or a 1, because the width is inferred from the OR of
   all bytes (`shared/utils.h:342-355`) and a leading zero bit is therefore
   dropped from `bsymbols` (`utils.h:403-421`), while a leading one bit is kept.

2. **Bound violation.** `low7.bin` can carry at most 7 bits of entropy per
   8-bit output, yet the tool reports `h_out = 7.1552`. The reported figure
   exceeds the information-theoretic ceiling of the data it was computed from.
   This follows from the code alone: `h_p` is a per-bit rate measured over the
   7 retained bits (`conditioning_main.cpp:364` hard-codes `data.word_size = 0`,
   so the width is inferred), and it is then multiplied by the user-declared
   `n_out = 8` at `conditioning_main.cpp:661` (`statBound = h_p * n_out`).
   Multiplying a rate measured over a subset of the output bits by the full
   output width is wrong regardless of how §3.1.1 is read.

Point 2 is the form the report should use: the finder argued from §3.1.1 item 2
("concatenated in the order in which it was generated and treated as a binary
string"), which invites an argument about whether the constant bits are part of
the conditioned output. The ceiling violation does not.

`ea_conditioning` offers no bits-per-symbol option (getopt string `vnqo:i:c:`,
`conditioning_main.cpp:478`), so a caller cannot correct the inference.

**Relation to the fork.** Inherited from upstream and present unchanged on both
fork branches. `ea_conditioning` is not one of the programs the fork ships for
its own purpose, which is what holds the severity at High rather than Critical.

### Incidental confirmation

The first attempt used the documented option order
(`ea_conditioning -n 1024 8 8 1000 -i low7.bin`) and printed the usage text
instead of running, confirming finder candidate `conditioning-transpose-10`
(BSD `getopt` stops at the first positional argument, so the order shown in
the program's own usage message does not work on macOS).

---

## OC-2 — `ea_iid` on master reports success for a source that failed every IID test

Rechecks finder candidates `output-automation-contracts-2`, `-3` and the
`restart-1` family (cluster `C03`). **Confirmed at source on master; confirmed
closed on the repair branch.** Source inspection only — the reproduction lens
was running the end-to-end case in parallel; what follows needs no execution to
establish.

### Master (`f069898`)

`cpp/iid/iid_test_run.h:28`

```c++
const bool IID = true;
```

The JSON `"IID"` field is a compile-time constant. It records which binary was
invoked, not what the binary concluded.

`cpp/iid_main.cpp:446-516` runs the three Section 5 batteries and stores each
outcome on the test case — `tc.passed_chi_square_tests`,
`tc.passed_longest_repeated_substring_test`,
`tc.passed_iid_permutation_tests` — and then, with no reference to any of them:

```c++
testRun.testCases.push_back(tc);
testRun.errorLevel = 0;
...
return 0;
```

So for a source that fails chi-square, fails the longest-repeated-substring
test and fails the permutation battery, `ea_iid` exits **0**, reports
`errorLevel` **0**, `"IID": true`, and an `hAssessed` figure. The per-test
booleans are present in `testCases`, so a consumer that walks into the test
cases and checks all three can tell — but exit status, `errorLevel` and the
top-level verdict field all say the assessment succeeded.

### Why this one matters most here

This fork exists to price a one-time pad on the reported figure. A pipeline that
does the ordinary thing — run the tool, check the exit status, read `hAssessed`
and the `IID` flag — will accept a demonstrably non-IID source at its full
assessed entropy. Of everything in this audit, this is the finding most likely
to cause a real loss, because the failure is silent and the reported figure
looks exactly like a good one.

### Repair branch (`2d4b135`) — closed, and closed properly

`iid_main.cpp:455-471`:

```c++
const bool iid_test_suite_pass =
    chi_square_test_pass && len_LRS_test_pass && perm_test_pass;
testRun.assessmentComplete = true;
testRun.iidClaimAccepted = iid_test_suite_pass;

if (!iid_test_suite_pass) {
    testRun.errorLevel = 2;
    testRun.errorMsg = "IID test suite failed; no IID min-entropy estimate was awarded.";
    ...
    return 1;
}
```

and `iid/iid_test_run.h:19` replaces the constant with `json["IID"] =
iidClaimAccepted`, adding `assessmentComplete` to distinguish a genuine failed
verdict from a tool error before the battery finished. `hAssessed` is
deliberately withheld on a failed run while the component MCV values stay
available as diagnostics.

That is fail-closed in all three channels a consumer might read — exit status,
`errorLevel`, and the verdict field — and it withholds the figure rather than
publishing one nobody should use.

**Consequence for the merge.** The repair branch is not merely safe to land; it
closes the audit's most consequential finding. This is the strongest argument
for rebasing it onto master rather than leaving it unmerged.

---

## OC-3 — the documented audit-archive counts are wrong, as reported

Spot-check of one factual claim inside cluster `C19-docs-drift`, which received
only a single verification lens. **Confirmed exactly.**

`audits/README.md:21-22` states:

```
- Tracked files under `audits/`: **585**, including this README.
- Tracked subdirectories: **118**.
```

At `f069898`:

```
git ls-tree -r --name-only HEAD audits/ | wc -l                 ->  739
distinct directory prefixes, excluding `audits/` itself         ->  126
```

Both of the finder's numbers reproduce (739 and 126; the subdirectory count is
126 when every distinct prefix below `audits/` is counted, 107 when only
directories that directly contain a file are counted — the documented 118 is
neither). The claim stands, and nothing in the repository checks these
hand-maintained figures, which is the finding's actual point.

---

## OC-4 — C08: the harness **can** fail. What it cannot do is notice absent reference data.

Verification of cluster `C08-harness-cannot-fail` (14 members), run by the
coordinating session against the real harness with real binaries at HEAD
`1da491d`. **Verdict: confirmed, and the cluster's name is wrong.** The harness
is not inert. It fails exactly as designed when a reference value is wrong. Its
defect is narrower and more specific: it **fails open on absent reference data**,
and it **excuses by filename rather than by magnitude**.

### What the harness claims to check

| Component | Claim | Scale |
|---|---|---|
| `selftest` + `compareresults.pl` | this build's `ea_non_iid -vv` output matches `refdata/` for every sample in `bin/` | 11 reference files, **967 key comparisons** (65 keys for 1-bit files, 107 for multi-bit) |
| 14 × `regression-*.sh` | named prior defects stay repaired | **166 reported checks**, 81 failure-increment sites |
| `run-all-checks.sh` | one aggregate verdict over all of the above | discovers `regression-*.sh`, runs `pin-check` and `selftest` |

### Positive control first: the harness does fail

Corrupting one value in a real reference file (`Assessed min entropy` in
`rand8_short.res`) against a real `ea_non_iid -vv` run:

```
rand8_short.res: Significant difference for Assessed min entropy
    (reference: 7.9999999999 new: 5.8608937444852494 delta: 0.267388281930186)
selftest: FAIL (1 of 1 files): rand8_short.bin        exit 1
```

So "cannot fail" is false as stated. Everything below is measured against this
control.

### Found 1 — `compareresults.pl` is driven by the reference, and a missing key is never a failure

`compareresults.pl:20` iterates `keys %$refResults`. A key absent from the
reference is therefore never compared, and the extra-item loop at `:53-55`
prints `Found extra data item` **without setting `$retstatus`**. Three
mutations, each against a real `ea_non_iid -vv` output:

| Reference | Keys compared | Result |
|---|---:|---|
| pristine | 107 of 107 | exit 0 (correct) |
| **truncated to 40 lines** | 34 of 107 | **exit 0** |
| **emptied (0 bytes)** | 0 of 107 | **exit 0** |
| **one key dropped — `Assessed min entropy` itself** | 106 of 107 | **exit 0** |

End-to-end through the real `selftest`: a 0-byte reference file yields
`selftest: PASS (1 files)`, **exit 0**.

**The chain is reachable.** `generate-refdata` has no `set -e` and no status
check, and its redirection truncates the reference *before* running the tool.
Demonstrated: with the tool absent, a 6,160-byte reference became **0 bytes**,
and `selftest` then reported `PASS`, exit 0. The realistic trigger is not a
missing binary but a tool that aborts on *some* inputs — which `OC-5` below
shows this build does, on ordinary data.

Mechanism: **status plumbing — an empty accumulator reads as success.**

### Found 2 — one of the four final figures is compared against nothing, on every run

`H_bitstring Per Symbol` appears in **no** reference file, while every real
`-vv` run prints it. It therefore lands in the extra-item loop every time. This
is visible in the pristine baseline, i.e. in normal operation:

```
rand8_short.res: Found extra data item: H_bitstring Per Symbol -> 5.8608937444852494
Maximum delta: 3.4173055689894e-12
```

`compareresults.pl`'s own header comment says the final figures were added
because "the final figure is the number an assessment is actually reported
with, so it is the one that most needs checking." One of the four was added to
the collector and never to the references.

Mechanism: **status plumbing**, same root as Found 1.

### Found 3 — the documented macOS escape excuses any magnitude

`run-all-checks.sh:23` is `KNOWN_PLATFORM_FILES="biased-random-bytes.bin
ringOsc-nist.bin"`, matched by filename with no bound on the delta.
Demonstrated by corrupting `ringOsc-nist.res`'s assessed figure from
`0.12644573619605429` to `0.03` — an error of **0.096 bit**, four orders of
magnitude beyond any platform delta the fork documents (its own precision audit
measures ≤ 9.1e-12 and pins tolerance at 1e-9):

```
with --allow-known-platform-deltas:   selftest   PASS (only the known upstream #155 platform files)
without it:                           selftest   FAIL (1 of 1 files): ringOsc-nist.bin
```

`--allow-known-platform-deltas` is the invocation `BUILDING.md` documents for
this platform. (The aggregate still exited 1 in that run because the regression
scripts had been moved aside for speed and `run-all-checks` correctly flags
"none found"; the excusal of the corrupted figure is the `selftest` line.)

Mechanism: **evidence type — a filename stands in for a magnitude bound.**

### Found 4 — `reg-quality-5`: a guard that passes under both policies it is meant to distinguish

`regression-subset.sh:88-97` asserts "sha256 still identifies the whole file"
against `ok.json`, which comes from `-l 0,1000000` on a **1,000,000-sample**
file — the subset is the entire file, so the whole-file hash and the
assessed-bytes hash are the same bytes. Executed on both branches:

```
master  sha256=f9ea8832af4c4205f518845b264465800921688fc2c4d566fbc087664aeb2313  scope=(absent)
repair  sha256=f9ea8832af4c4205f518845b264465800921688fc2c4d566fbc087664aeb2313  scope=assessed-sample-bytes
```

Identical values, and equal to the whole-file hash, under two **incompatible**
policies. A tautological guard cannot be "shown failing"; the demonstration
that it is tautological is that it passes identically on both sides of the
policy change it was written to pin. Mechanism: **evidence type.**

### Found 5 — cosmetic, and correctly classified as such

`build-port-12`: `selftest:48-49` prints `FAILED (ea_non_iid exited $?)` from
inside `if ! ../ea_non_iid …`, where `$?` is the *negation's* status and so is
always 0. The message is wrong; `fail_count` still increments and the verdict
and exit status are correct. **Misreport, not a dead guard.**

### Also visible, already tracked

`HARNESS-AUD-01`: ten of the eleven fixtures were removed from `bin/` for speed
and `selftest` reported `PASS (1 files)`, exit 0 — no expected-fixture count on
master. Repaired only on the repair branch.

### Examined alongside found

Of the harness's **166 reported regression checks** and **967 reference-key
comparisons**: three confirmed defects in the `selftest` core (Found 1-3), one
confirmed tautological regression assertion (Found 4), one cosmetic misreport
(Found 5), two confirmed and now **fixed** on master (`reg-quality-4`,
`build-port-10` in part, commit `1da491d`), and four that are repair-branch-only
and so do not ship (`reg-quality-1`, `-2`, `-3`, `build-port-4`,
`build-port-13`). Two members remain unverified: `reg-quality-6` (the MultiMMC
binary-path check not discriminating) and `reg-quality-9` (coverage gaps in the
N-08 transpose hunk and all of `ea_conditioning`).

This is not a wholly inert harness. It is a harness whose 967 value comparisons
are all conditional on the reference containing the key, whose aggregate accepts
any magnitude of error in two named files, and which has at least one assertion
that cannot distinguish the policies it names.

### Consequence for batch 1 — it does not fall

The premise "if the harness cannot fail, every verdict is suspect" does not
transfer, because **batch 1 did not consume the harness.** Its fifteen lenses
ran the `ea_*` binaries directly and compared against independently
constructed references:

- `C04`'s reproduction matched every figure digit for digit against the tool's
  own stdout and JSON, on its own fixtures. Independent of the harness.
- `C01`'s refutation wrote a fresh SP 800-90B §6.3.9 implementation from the
  specification text and validated it against **the publication's own worked
  example** before using it. Independent of the harness.
- `C03`'s reproduction built its own 1M fixture and read exit status and JSON
  fields directly. Independent.
- `C05` reproduced an abort by exit status. Independent.
- `C02` ran the tools and read JSON fields. Independent.

What C08 **does** bear on is `REGRESSION-LEDGER.md`:

- **Claim 1** ("23 repairs whose guard was seen to fail") is weakened but not
  voided: its evidence is that each guard *did* fail under mutation with a named
  assertion, which is the opposite of inertness. The exposure is that a guard
  may have failed for a reason other than the one claimed.
- **Claim 3** is strengthened as a warning: `reg-quality-5` is now confirmed
  tautological by execution, and `build-port-4`'s mechanism is explained
  quantitatively by `OC-5` below.
- The fork's own "the suite is green" statement is worth less than it reads,
  for the three reasons above.

Nothing here changes an entropy figure. Every defect in this cluster is in the
*checking* of figures, not in their computation.

---

## OC-5 — C07: a fail-closed abort in the IID track, at **four** distinct asserts, not one

Verification of cluster `C07-lrs-underflow-abort` (5 members). **Verdict:
confirmed by independent reproduction, with the cluster's mechanism corrected:
it conflates two unrelated asserts, and the logs show four.**

`NDEBUG` is **not** defined anywhere in `cpp/Makefile`, and the assert strings
are present in the shipped `ea_iid`. Asserts are live in the release build, so
every site below is a `SIGABRT`.

### Fail-closed, decisively

```
ea_iid -i -o out.json bal125.bin   ->  rc=134,  out.json: NOT WRITTEN
ea_restart -i -q    bal125.bin     ->  rc=134
ea_non_iid -i -q    bal125.bin     ->  rc=0     (the conservative track is unaffected)
```

`len_LRS_test` is called only from `iid_main.cpp` and `restart_main.cpp`. **The
user gets no number, not a wrong one.** Fail-closed. This is a different class
from `C04`, which was a misreport: here nothing is published, and the fallback
to `ea_non_iid` yields a *lower*, conservative figure.

### Site A — `lrs_test.h:652`, `assert(p_col >= 1.0L / k)`: exact equidistribution

Mathematically `p_col = Σpᵢ² ≥ 1/k` with equality **iff** the alphabet is
perfectly uniform. The assert therefore compares two differently-computed
expressions for the same number at the boundary, and the left side can land one
ULP low. Ten exactly-balanced 1,000,000-sample alphabets (`a=[i%k …]` shuffled,
seed `0xB41A`, each symbol exactly `L/k` times — a construction independent of
the finder's seed 2501):

| k | 20 | 25 | 32 | 40 | 50 | 64 | 100 | 125 | 200 | 250 |
|---|---|---|---|---|---|---|---|---|---|---|
| rc | 0 | **134** | 0 | 0 | 0 | 0 | **134** | **134** | **134** | **134** |

Five of ten abort. The pattern is representability: `k = 32, 64` make `1/k` an
exact binary fraction and pass; `k = 25, 100, 125, 200, 250` do not.

**The threshold demonstrated at its extremes.** Perturbing two symbol counts by
±1 in 1,000,000 — the smallest possible departure from exact balance — clears
the assert, because any imbalance raises `Σpᵢ²` strictly above `1/k` by far more
than the rounding error:

| perturbation | ±1 | ±2 | ±10 | ±100 | ±1000 | exact |
|---|---|---|---|---|---|---|
| rc | 0 | 0 | 0 | 0 | 0 | **134** |

So site A needs *exact* equidistribution. That is not what a physical source
produces — but it is precisely what a synthetic test vector, a counter stream,
or a balanced permutation produces.

### Site B — `lrs_test.h:683`, `assert(p_colPower >= LDBL_MIN)`: underflow, and the dominant site in the logs

This is the site the code **intends**: its own comment says "There isn't
anything we can do about this error condition without moving to an arbitrary
precision calculation, so for now, we'll just detect this condition and abort
the calculation." The abort is deliberate. The defect is its reachability here.

`p_col^W < LDBL_MIN` with `p_col ≈ 0.5` requires `W > 1022` on this platform
(`sizeof(long double) = 8`, `LDBL_MIN = 2.225e-308`). On x86-64 with an 80-bit
`long double` the same bound is `W > 16382` — sixteen times higher. Bracketed by
implanting a repeated block of length `W` into a 1-bit stream:

| implanted W | 500 | 1000 | **1100** | **2000** |
|---|---|---|---|---|
| rc | 0 | 0 | **134 at :683** | **134 at :683** |

Predicted boundary `W > 1022`; measured between 1000 and 1100. **A repeated
substring longer than ~1022 bits in a 1-bit source makes `ea_iid` unassessable
on arm64 while an x86-64 build assesses it.** A 1024- or 2048-bit repeated block
is ordinary in real data. This is the consequential half of C07 and it needs no
exact balance.

### Sites C and D — observed, not reproduced here

The finders' logs show `lrs_test.h, line 684` (287 occurrences) and `line 683`
(242) dominating, against `line 652` (63), plus a few at `626` and `657`. Line
684 is `assert(p_colPower <= 1.0L - LDBL_EPSILON)`. I did not reproduce 684 and
do not claim it. The occurrence counts reflect how many log lines matched across
scanning loops, not how often each fires in practice.

**Correction to the cluster:** `memory-safety-fuzz-1` and
`estimators-ttuple-lrs-1` name site A; `build-portability-harness-docs-1` and
`restart-2` name site B. These are different defects with different triggers,
different platform dependence, and — as shown next — different fates on the
repair branch. They should not have been one cluster.

### Provenance checked, per the C04 lesson — this one holds up

Every evidence path cited by `memory-safety-fuzz-1` and `linux-x86-docker-1`
resolves to a real file under that agent's directory (`raw/verify/v1.log` 1,064
bytes; `out/T4-r1.log` 3,670 bytes; and so on). The `$A`/`$S` prefixes in the
records are unexpanded placeholders in the text, not missing evidence. Unlike
C04, no sanitizer claim here is sourced from outside this audit's builds.

### The repair branch fixes site B and **not** site A

| | master `f069898` | repair `2d4b135` |
|---|---|---|
| site B (`lrsrep-2000.bin`) | rc=134, no JSON | **rc=1**, JSON written: `errorLevel 2`, `IID: false`, `assessmentComplete: true`, `hAssessed` absent, "IID test suite failed; no IID min-entropy estimate was awarded." |
| site A (`bal125.bin`) | rc=134, no JSON | **still `Assertion failed: (p_col >= 1.0L / ((long double) k)) … line 652`**, no JSON |

So the repair branch converts the underflow into a proper fail-closed verdict
with a report, and leaves the exact-equidistribution abort untouched.

**One concern about how it fixes site B.** It reports the underflow as
`** Failed length of longest repeated substring test` with `Pr(X >= 1):
0.000000` — that is, it converts *"this platform's `long double` cannot
represent the intermediate"* into *"the source failed an independence test"*.
The direction is conservative and the report is honest about the verdict, but
the stated **reason** is wrong, and an operator debugging it would examine their
entropy source rather than their build platform. Worth recording against the
repair branch rather than treated as closed.

---

## OC-6 — C03's `ea_restart -i` half: the same mechanism, same shape, still open

**Verdict: the C03 mechanism does apply to the `-i` path. Source-confirmed and
now VERIFIED by compliant 1,000,000-sample execution.** It **misreports** — it
does not abort.

### The mechanism, at source

`restart_main.cpp` computes all three Section 5 tests in the `-i` branch:

```c
bool chi_square_test_pass = chi_square_test_pass_row && chi_square_test_pass_col;   // :794
tcOverallIid.passed_chi_square_tests = chi_square_test_pass;                        // :796
bool len_LRS_test_pass = len_LRS_test_pass_row && len_LRS_test_pass_col;            // :818
tcOverallIid.passed_longest_repeated_substring_test = len_LRS_test_pass;            // :820
bool perm_test_pass = perm_test_pass_row && perm_test_pass_col;                     // :840-852
```

and then **never reads any of them**. The only gate after the IID block is

```c
if (min(H_r, H_c) < H_I / 2.0) { … exit(-1); }     // :882
```

which is the §3.1.4.3 validation test on the *entropy estimates*, wholly
independent of the Section 5 outcomes. Control then falls through to

```c
testRunIid.testCases.push_back(tcOverallIid);
testRunIid.errorLevel = 0;      // :900  — unconditional
…
return 0;                       // :930  — unconditional
```

This is the same defect as the `ea_iid` half: the verdict is computed, stored,
printed, and discarded. Because `IidTestRun::IID` is the compile-time
`const bool IID = true`, the JSON also reports `"IID": true`.

**Misreport, not an abort.** A caller reading exit status, `errorLevel` and the
`IID` field sees success, and `h_r`/`h_c`/`h_i` are all published. Contrast
`OC-5`, where nothing is published at all.

### Incidental confirmation of the constant `IID` field

`ea_restart -i` on a 10,000-sample file is refused — the 1000×1000 matrix is
mandatory and `EA_ALLOW_SHORT_DATASET` does **not** bypass it:

```
rc=255   errorLevel: -1   IID: true
errorMessage: *** Error: data (len = 10000) does not contain 1000000 samples ***
```

`"IID": true` on a path where **no IID test was ever run**. That is
`output-automation-contracts-3` confirmed by execution, and it is the cleanest
possible demonstration that the field reports which binary was invoked rather
than any conclusion.

### C07 masks C03 on the obvious data

The first three candidate fixtures — `markov-stay99-1bit`, `period6-1bit`,
`alternating-1bit` — all abort with `rc=134` before reaching the unconditional
`errorLevel = 0`, because highly repetitive data has a long repeated substring
and trips `OC-5` site B. **The two defects interact: on exactly the data that
would demonstrate the misreport, the abort fires first.** Demonstrating C03's
restart half therefore requires data that fails an IID test *without* a long
repeat — weak serial correlation — which is what the pending run uses
(1,000,000-sample 1-bit streams at p(stay) = 0.55, 0.60, 0.70, seed
`0x90B2026C03`, no implanted repeat, not exactly balanced, with `H_I = 0.1` so
that `min(H_r,H_c) ≥ H_I/2` and validation passes on its own terms).

### Status of this check — now VERIFIED by compliant execution

The re-launched run completed in 19 min 28 s (22:51:07 → 23:10:35,
`OMP_NUM_THREADS=4`). `mk55-1bit.bin`: 1,000,000 samples, 1-bit, p(stay)=0.55,
seed `0x90B2026C03`, no implanted repeat, not exactly balanced, no
`EA_ALLOW_SHORT_DATASET`, plain CLI, `H_I = 0.1`:

```
H_I: 0.100000
** Failed chi square tests
** Passed length of longest repeated substring test
** Failed IID permutation tests
H_r: 0.994896
H_c: 0.994896
H_I: 0.100000
Validation Test Passed...
min(H_r, H_c, H_I): 0.100000
ea_restart rc=0
```

JSON: `errorLevel: 0`, `IID: true`, `errorMessage: None`, and the Overall test
case:

```json
{"h_r": 0.9948963727812402, "h_c": 0.9948963727812402, "h_i": 0.1,
 "passedChiSquareTests": false,
 "passedIidPermutationTests": false,
 "passedLongestRepeatedSubstringTest": true}
```

**Two of the three Section 5 IID tests failed, and the tool exits 0 with
`errorLevel 0`, `"IID": true`, no error message, and published `h_r`/`h_c`
figures.** The per-test booleans sit in the same JSON object as the figures they
should have invalidated. Nothing reads them, exactly as the source said.

This is the restart analogue of the `ea_iid` half, demonstrated on compliant
input. **Misreport, not an abort** — the figures are published, which is the
permissive case. Under §3.1.2 a source whose Section 5 tests fail is not IID
and the non-IID track is the mandated one, so awarding an *IID restart*
estimate here is a figure the standard does not sanction.

One honest qualification about magnitude. I set `H_I = 0.1` so that
`min(H_r,H_c) ≥ H_I/2` and validation would pass on its own terms, which also
caps the final `min(H_r, H_c, H_I)` at **0.1** — so the headline number in this
particular run is dominated by the submitter's own `H_I` claim rather than by
the defect. The awarded restart figures are `h_r = h_c = 0.9948963727812402`. A
submitter claiming a higher `H_I` would see the defect in the headline figure
directly. What is demonstrated here without qualification is that **the IID
verdict is computed, recorded, and then discarded** — not the size of any
particular resulting number.

**Correct and verified**: the mechanism, the unconditional `errorLevel = 0` and
`return 0`, the published figures alongside two false `passed*` booleans, on
1,000,000 compliant samples. Also verified earlier: `"IID": true` on a
10,000-sample *refusal* path where no IID test ran at all.

### Correction, made while writing this entry

I first wrote that this half is open "on master and on the repair branch", with
the `restart_main.cpp` check listed as not yet done. I then did it, and it
contradicts that sentence. The repair branch **does** close the restart half,
with the same shape as the `ea_iid` half:

```c
iid_test_suite_pass = chi_square_test_pass && len_LRS_test_pass && perm_test_pass;   // repair :823
testRunIid.assessmentComplete = true;
testRunIid.iidClaimAccepted = iid_test_suite_pass;                                   // :825

if (iid && !iid_test_suite_pass) {                                                   // :830
    tcOverallIid.h_r = -1.0;  tcOverallIid.h_c = -1.0;  tcOverallIid.h_i = -1.0;
    testRunIid.errorLevel = 2;
    testRunIid.errorMsg = "IID restart test suite failed; no IID restart entropy estimate was awarded.";
    …
    return 1;                                                                        // :846
}
```

It is stronger than the `ea_iid` half: besides `errorLevel 2`, exit 1 and
`IID: false`, it overwrites `h_r`, `h_c` and `h_i` with `-1.0` so no figure is
published even inside the test case. It also skips the permutation battery after
an earlier required test fails, and says so.

**Accurate status: OPEN on `master`, which is the branch that ships and the
branch every current assessment is produced by. Closed on the unmerged repair
branch.** It is not part of a closed finding — the fix exists only in code that
has not landed, and the rebase that would land it is not authorized.

So the C03 cluster as a whole: the `ea_iid` half and the `ea_restart -i` half
are both open on master and both closed on `2d4b135`. The audit's earlier
statement that the repair branch "partly closes it — two of the three halves
fully, one left" was wrong about which half remained; the `restart` gate is
present. What is genuinely left is the *class-wide* issue that the `IID` field
is a compile-time constant on master's error paths, demonstrated above.

---

## OC-7 — `restart-12`: the restart sanity check awards estimates the standard says must not be awarded

> **SUPERSEDED IN ITS CONCLUSION — 2026-10-19, see `OC-30`.** Every measurement
> in this entry stands: the tool's simulated cutoff does sit 2–5 counts above the
> cutoff §3.1.4.3's printed formula gives, systematically, at every H_I. What is
> wrong is the conclusion drawn from it. The printed formula is not the
> probability of the event being tested, and a cutoff computed from it **rejects
> correctly-operating sources** — 83.2 % of full-entropy 8-bit matrices,
> measured. Upstream's higher simulated cutoff is a deliberate correction
> (upstream issue #56), not an unsafe relaxation, so "effective α 2× to 821×
> smaller than intended" describes a test being made *less* trigger-happy than a
> formula that is itself wrong. This was the audit's top finding and that ranking
> was mistaken.

Verification of the item previously filed as **Info** inside
`C23-misc-reporting`. **Verdict: confirmed, permissive, and the "implementation
choice" defence does not survive the standard's own text. This is the audit's
top finding for the goal.**

### Impact lens — the standard specifies a formula, not a method

§3.1.4.3 does **not** sanction simulation. It gives a closed form:

> 1. Let p = 2^(−H_I). Let α be 0.000 005.
> 5. Calculate P(X ≥ X_max) = Σ_{j=X_max}^{1000} C(1000,j) p^j (1−p)^(1000−j).
>    **If Pr(X ≥ X_max) < α, the test fails.** Otherwise, the test passes.

and states the consequence of failure plainly:

> If this frequency is significantly greater than the expected value, given the
> initial entropy estimate H_I … the restart test fails. **In this case, the
> validation fails no entropy estimate is awarded.**

The finding's own `expected` field reads "a deterministic cutoff", and its
`uncertainty` field then dispositions it as "an implementation choice,
deliberately taken upstream, so it is Info rather than a defect." **That
disposition is wrong.** The standard prescribes a deterministic binomial tail.
A Monte Carlo estimate of that tail is not a permitted variation on a formula;
it is a different test, and here a weaker one.

### The implementation does simulate

`restart_main.cpp:108-163`, `simulateBound(alpha, k, H_I, rounds)`:
`p = 2^-H_I`, `k_effective = ceil(1/p)`, then `DEFAULT_SIMULATION_ROUNDS =
5000000` Monte Carlo trials of `simulateCount`, sorted, and the cutoff taken as
the empirical order statistic `results[floor((1-alpha)*rounds) - 1]`. With
α ≈ 5.03e-6 and 5e6 rounds that is the 4,999,974th of 5,000,000 samples — an
extreme-quantile estimate with roughly 26 observations above it.

`alpha = 1 - exp(log(0.99)/(r+c))` = 5.0251553006155243e-06, the exact Šidák
value for 2000 experiments where the standard prints the Bonferroni
approximation 0.000005. **That difference is immaterial**: recomputed at every
H_I below, both α values give the identical exact cutoff.

### Reproduction — by execution, against the real binaries

Exact cutoffs computed independently in `mpmath` at dps 60 (largest count that
PASSES, matching the tool's convention) against the tool's printed `X_cutoff`,
**three draws at each of nine H_I values — 27 runs, every gap positive**,
`ea_restart -i -v uniform-8bit.bin 8 <H_I>`:

| H_I | exact | tool draws | gap | effective α (median) | vs intended α | entropy-equivalent slack |
|---|---:|---|---:|---:|---:|---|
| 1 | 570 | 572, 572, 571 | +1…+2 | 2.18e-06 | 2× smaller | 0.0051 bit |
| 2 | 312 | 316, 316, 316 | +4 | 1.09e-06 | 5× smaller | 0.0184 bit |
| 3 | 173 | 179, 178, 178 | +5…+6 | 5.82e-07 | 9× smaller | 0.0411 bit |
| 4 | 99 | 103, 104, 104 | +4…+5 | 2.20e-07 | 23× smaller | 0.0711 bit |
| 5 | 58 | 63, 63, 63 | +5 | 1.08e-07 | 47× smaller | 0.1193 bit |
| 6 | 36 | 40, 40, 40 | +4 | 4.95e-08 | 102× smaller | 0.1520 bit |
| 7 | 23 | 27, 27, 27 | +4 | 1.47e-08 | 341× smaller | 0.2313 bit |
| 7.5 | 19 | 22, 23, 22 | +3…+4 | 2.03e-08 | 247× smaller | 0.2115 bit |
| 8 | 15 | 19, 19, 19 | +4 | 6.12e-09 | **821× smaller** | **0.3410 bit** |

Intended α = 5.0251553006155243e-06 throughout. The exact column is reproducible
with `oracles/restart_cutoff_exact.py`, which was written from the standard's
formula without reference to the finder's oracle and which reproduces their
"spec" values digit for digit at all nine points. The finder had H_I=8 as
"modelled 19"; it is now **measured** 19.

**The gap is systematic, not sampling noise at a few points.** All 27 draws are
above the exact cutoff. Several H_I values returned the same cutoff on all three
draws (2, 5, 6, 7, 8). The gap is +1 to +6 counts absolutely, and its *relative*
size grows sharply with H_I — 0.35 % at H_I=1 against 27 % at H_I=8. The
direction is permissive at every point.

**Effective α is the real type-I error of the tool's cutoff**, i.e. how often it
rejects a source that genuinely has the claimed H_I. It is **2× to 821×
smaller than intended**, worsening monotonically with H_I: the test rejects far
less often than the standard specifies, and most so exactly where a
high-entropy claim is being made.

### Acceptance of spec-rejected data — demonstrated, bracketed both sides

8-bit 1000×1000 matrices with column 17 forced to an exact count, H_I = 7
(exact cutoff 23, so the standard rejects X_max ≥ 24):

| forced X_max | tool | standard |
|---:|---|---|
| 24 | `X_cutoff: 27`, `X_max: 24`, **Restart Sanity Check Passed…** | fails |
| 25 | `X_cutoff: 27`, `X_max: 25`, **Restart Sanity Check Passed…** | fails |
| 28 | `X_cutoff: 27`, `X_max: 28`, `*** Restart Sanity Check Failed ***` | fails |

The X_max=28 row is the positive control: the comparison does fire, so the two
passes above are not a broken test but a wider one. At H_I=7 the window of
false acceptance is **X_max ∈ {24, 25, 26, 27}**.

### A second defect in the same mechanism: the verdict is not a function of the input

The cutoff is drawn from `/dev/urandom`-seeded simulation and **varies between
runs** — 571/572 at H_I=1, 178/179 at H_I=3, 103/104 at H_I=4. So a matrix with
`X_max = 572` at H_I=1 **passes or fails depending on the draw**. An assessment
that is not a deterministic function of its input is not reproducible, and
reproducibility is the whole of what a self-attested measurement has.

### Provenance — checked, and it holds

Every path `restart-12` cites resolves under this audit's own agent directory
(`out/cutoff_oracle.txt` 3,100 bytes, `cutoff_oracle.py` 5,896, `LOG.md`
38,159, `data/manifest.json` 8,117, and the `bnd1_master_X570…X573` output
pairs). Its `LOG.md` references `wt/master`, `wt/upstream` and `wt/repair` —
**this audit's builds**. Unlike C04, the cited execution is where it claims to
be. Its own positive control is sound: at H_I=0.05 the exact oracle and all
three builds agree on 988.

### Consequence for the goal

The restart half is one of the two halves of the assessment, and TruePad's
desktop harness now runs it. §3.1.4.3's failure consequence is categorical —
**no entropy estimate is awarded**. So the defect is not a shifted number: it is
that a restart matrix which the standard says must receive **no estimate at
all** receives one, and the run then proceeds to publish `min(H_r, H_c, H_I)`
as if the sanity check had been passed.

The size of the window, in the statistic the check actually measures: the tool
tolerates a most-common-value frequency corresponding to **0.005 bit (H_I=1) to
0.341 bit (H_I=8)** less entropy than the standard sanctions. For a project
whose threshold is 0.5 bit per bit per source, a **0.34-bit** tolerance in the
restart sanity check — two thirds of the entire threshold — is not a rounding
concern. And it is worst precisely at the high-H_I end, which is where a source
good enough to support the goal would be assessed.

**Correct and verified**: the spec reading, the simulation mechanism, the cutoff
gap at six H_I values with three draws each, the acceptance of X_max = 24 and
25 at H_I = 7 with a working positive control, the non-determinism, and the
provenance. **Not verified**: behaviour above H_I = 8 (`k_effective = ceil(2^H_I)` must not
exceed the 256-symbol alphabet, so H_I = 8 is the ceiling for byte data),
behaviour with `-s` above the default 5,000,000 rounds, and whether a larger round count would
close the gap or merely narrow it — the bias is a property of taking an extreme
order statistic, so more rounds should reduce it but the exact convergence was
not measured.

### Recommended disposition

Replace the simulation with the standard's closed form. The exact binomial tail
at n=1000 is a 1000-term sum computable in double precision, or in `long
double` with a log-gamma formulation; it is deterministic, far cheaper than
5,000,000 simulated experiments, and it is what §3.1.4.3 specifies. A
regression for it must assert the cutoff at several H_I against independently
computed values — and must be shown failing against the current simulated
cutoff, which it would be at every H_I in the table above.

---

## OC-8 — C22's `ZALPHA`: "tiny" measured. Merely small, not below precision — and not a defect.

`predictors-6` says `ZALPHA` is the exact 0.995 quantile `2.5758293035489008`
where the spec text prints `2.576`, which "raises every prediction estimate".
"Magnitudes tiny" was the finder's claim. Measured, on real values harvested
from a real run (`ea_non_iid -i -a -vv uniform-8bit.bin 8`):

| predictor | H with tool `ZALPHA` | H with spec `2.576` | delta |
|---|---|---|---|
| Bitstring MultiMCW | 0.99911507785502614 | 0.99911499084098192 | **+8.70e-08** bit |
| Literal MultiMCW | 7.9611632356166352 | 7.9611594334062937 | **+3.80e-06** bit |
| Bitstring Lag | 0.998936306150716 | 0.99893621914778806 | **+8.70e-08** bit |

My recomputation of `P_global'` from the published `P_global` and `N` reproduces
the tool's own printed `P_global'` **exactly** on all three predictors, which is
what validates the measurement against the real artifact rather than against my
model of it.

**Answering the question directly: "tiny" means merely small, not below the
reported precision.** The worst delta, 3.80e-06 bit, sits at the sixth decimal
place of a figure the tool prints to 17 significant digits — so it is far above
the printed precision floor. Against the project's 0.5 bit-per-bit threshold it
is 7.6e-06 relative. It would matter only to a measurement landing within four
millionths of a bit of the threshold.

**Direction: permissive, and nonetheless not a defect.** The sign is positive —
the tool's constant yields the higher estimate. But `2.576` is itself a
*rounded* printing of the true 0.995 quantile, so the tool uses the correct
constant and the standard's text uses the rounding. This is prior `F07`, already
dispositioned NOT-A-BUG on exactly that reasoning, and `predictors-6` restates
it. **No change recommended.** Recorded so that the permissive direction is
on file with a measured magnitude instead of an adjective.

The rest of `C22` — `P_local`'s bisection quantisation (claimed worst
non-conservative +1.6e-11 bit), the `x` recurrence iterated to convergence
rather than the spec's fixed 10 iterations, `P_global'` dividing by `N-1` at
`N == 1` — **remains unverified**.

---

# New findings raised by this pass

These are findings in their own right, not details inside clusters.

## REPRO-01 — an assessment whose verdict depends on the build host

**Severity: High. Direction: see below — this is the one case where the
direction question has a different answer on each architecture.**

The same input yields a verdict on one architecture and an abort on another:

| | arm64 (`sizeof(long double) == 8`) | x86-64 (80-bit `long double`) |
|---|---|---|
| `LDBL_MIN` | 2.225e-308 | 3.362e-4932 |
| `p_colPower = p_col^W` underflows at | **W > 1022** | W > 16382 |
| 1-bit source with a 2000-bit repeat | `SIGABRT`, no JSON, **no figure** | assessed normally |

Measured on arm64 (`OC-5`): implanted repeat W=1000 passes, **W=1100 aborts**,
against a predicted boundary of 1022. The x86-64 bound follows from
`LDBL_MIN` and is consistent with the `linux-x86-docker` agent's observation
that an x86 build assesses data arm64 refuses; I have **not** re-run the x86
side myself and do not claim it as my measurement.

Two separate consequences, which is why this is its own finding:

1. **Reproducibility.** A self-attested measurement has nothing going for it
   except that anyone can repeat it and get the same answer. Here two
   conforming builds of the same commit, on the same data, disagree about
   whether a figure exists at all. That is not a precision difference like
   upstream #155 — it is the difference between a number and no number.
2. **The direction is architecture-dependent.** On arm64 the defect is
   conservative (fail-closed, no figure). On x86-64 the same input is assessed
   and a figure is published. So which way this defect pushes a claim depends
   on the host that produced it, and a figure carries no record of which bound
   applied. Nothing in the JSON reports `sizeof(long double)`.

The fork's documented build platform is macOS arm64 — the stricter side — so
current local assessments fail closed. The hazard is a figure produced on x86
being compared with, or substituted for, one produced on arm64.

**Recommended:** record `sizeof(long double)` and the underflow bound in the
JSON provenance block, so a figure states the arithmetic that produced it; and
treat the underflow as a declined estimator rather than an abort, which is what
the fork already does for other representability limits (`F11`, `F12`, `F15`).

## REPAIR-BLOCK-01 — the repair branch must not merge while it reports an arithmetic limit as a hardware failure

**Blocks: the `repair/2026-10-09-verified-defects` rebase. Direction: NEUTRAL
for the figure, harmful for the operator.**

On the repair branch, `C07` site B no longer aborts — it reports:

```
	Pr(X >= 1): 0.000000
** Failed length of longest repeated substring test

** Skipped IID permutation tests after an earlier required IID test failure

IID test suite failed: no IID min-entropy estimate was awarded.
```

with `errorLevel 2`, `IID: false`, `hAssessed` withheld, exit 1. The
fail-closed plumbing is correct and is a real improvement over the `SIGABRT`.

**The stated reason is wrong.** `p_col^W` underflowing a 64-bit `long double`
is a representability limit of the build platform. The branch reports it as
`** Failed length of longest repeated substring test` — a statistical rejection
of the user's entropy source. An operator reading that will investigate their
TRNG. The correct message is that the tool ran out of exponent range on this
platform and declined to compute the test.

This is a misreport in the direction of alarming the user about the wrong
thing, and it is worse than the abort it replaces in one specific respect: an
abort is obviously a tool failure, whereas "Failed length of longest repeated
substring test" is a credible, actionable-looking verdict about the hardware.

**Must be fixed before that branch merges.** The fix is small: distinguish
"declined — not representable on this platform" from "failed", which the fork
already does elsewhere (the `-1` sentinel and the `nonCompliant*` flags are
precedents). Added to the merge record's blocking list alongside the Claim 2
and Claim 3 guard rewrites.

---

## OC-9 — C09: `ea_conditioning` enforces none of the intake discipline the other three tools do

**Verdict: all four members confirmed by execution. Direction: mixed, and the
permissive half is the fork's own compliance rule being absent from one tool.**

### Permissive half — sub-minimum data assessed with no marker

The fork added the §3.1.1 1,000,000-sample rule (F03/F04) and enforces it in
`ea_non_iid`, `ea_iid` and `ea_restart`. `ea_conditioning` does not have it.

```
ea_conditioning -n -i short125k.bin -o o.json 512 256 256 300    (125,000 bytes)
  rc=0   h' = 0.8330616146316409675876   (Non-vetted) h_out = 213.2637733457000877024
  JSON: errorLevel 0,  nonCompliantShortDataset ABSENT,  bitsPerSymbol ABSENT

ea_conditioning -n -i short100.bin  -o o.json 512 256 256 300    (100 bytes)
  rc=0   h' = 0.6375933997245808448894   (Non-vetted) h_out = 163.2239103294926962917
  JSON: errorLevel 0,  nonCompliantShortDataset ABSENT,  bitsPerSymbol ABSENT

ea_non_iid -q short125k.bin 8                                    (the same file)
  rc=255   "*** Error: dataset contains 125000 samples;
            SP 800-90B Section 3.1.1 requires at least 1000000 ***"
```

A **100-byte** file produces a complete `h'` and `h_out` with `errorLevel 0` and
no non-compliance marker of any kind. The fork's `EA_ALLOW_SHORT_DATASET`
escape sets `nonCompliantShortDataset` in the JSON precisely so that a consumer
can tell a non-compliant assessment apart; here there is nothing to tell it
with, because the rule was never applied and so the escape was never needed.

### Crash half — degenerate input, and what the assert is hiding

All-zero 1,000-byte input, shipped configuration (no `NDEBUG`):

```
master       rc=134   "Assertion failed: (len > 1), function most_common,
                       file most_common.h, line 14."   no JSON
master-asan  rc=134   same assert
```

Fail-closed and harmless in a shipped build. But the assert is masking a real
memory error. Built with **`-DNDEBUG`** plus ASan/UBSan — a configuration no
`cpp/Makefile` target produces, but one that **downstream packaging commonly
adds**:

```
ERROR: AddressSanitizer: heap-buffer-overflow
READ of size 1 at 0x60200000352f thread T0
    #0 markov_test(unsigned char*, long, int, char const*)  markov_test.h:48
    #1 computeEntropyOfConditionedData(...)                 conditioning_main.cpp:392
0x60200000352f is located 1 bytes BEFORE 1-byte region [0x602000003530,0x602000003531)
allocated by thread T0 here:
    #1 read_file_subset(char const*, data_t*, unsigned long, unsigned long, TestRunBase*)  utils.h:406
```

The mechanism is `OC-1`'s width inference taken to its degenerate limit:
all-zero input makes the inferred `word_size` **0**, so `blen = len * word_size`
is 0 and `bsymbols` is a zero-length allocation; `markov_test` then reads before
it. `conditioning_main.cpp:364` hard-codes `data.word_size = 0` to request
inference, and nothing rejects an inference of 0.

And the IID variant does not even abort:

```
ea_conditioning -n -c iid -i allzero1000.bin 512 256 256 300    (NDEBUG build)
  rc=0   h' = -0   (Non-vetted) h_out = -0
```

**Exit 0 on all-zero input, reporting negative-zero entropy.** A consumer
checking the exit status sees success.

### Direction

- **PERMISSIVE**: sub-minimum data assessed with `errorLevel 0` and no marker;
  and `-c iid` exiting 0 with `h' = -0` on degenerate input.
- **CONSERVATIVE** in the shipped configuration: the non-IID path aborts.
- **MEMORY-UNSAFE** under `-DNDEBUG`: an out-of-bounds read reaching a figure.

The cluster was filed Medium with mixed directions, which is why direction
triage put it third on the register. The permissive element is the sharper one:
the fork's compliance rule is enforced in three tools and absent from the
fourth, with no flag to say so.

### Relevance to the goal — off the critical path, and why it still matters

Chor–Goldreich two-source extraction needs **raw per-source min-entropy**, not
conditioned output, so `ea_conditioning` sits off the path to the 0.5 bit/bit
figure. `C09` therefore does not threaten that number *unless a conditioning
component enters the chain*, at which point `OC-1`'s width-inference
overestimate (`h_out` 7.1552 against a 7-bit ceiling) and this cluster's missing
intake rule compound: a short, degenerate conditioned dataset would be assessed
without complaint and scaled by an inferred width.

**Correct and verified**: all four members, by execution, on both the shipped
and the `NDEBUG` configuration. **Not verified**: whether any upstream issue
covers the missing intake rule, and the behaviour of the remaining
`ea_conditioning` items in `C21`.

---

## OC-10 — the NDEBUG re-classification: C07 flips from conservative to permissive

**This corrects the direction triage.** `C07` was classified CONSERVATIVE and
fail-closed on the explicit grounds that `NDEBUG` is not defined in
`cpp/Makefile`, so its asserts are live. That is a claim about a build, not
about the code. Built with `-DNDEBUG` — the same commit, the same data — one of
`C07`'s two sites **publishes an IID min-entropy figure instead of refusing**.

### Enumeration — every classification in this audit resting on an assert

| Finding | Assert | Classification that rested on it |
|---|---|---|
| `C07` site B | `lrs_test.h:683` `p_colPower >= LDBL_MIN` | CONSERVATIVE, fail-closed |
| `C07` site A | `lrs_test.h:652` `p_col >= 1.0L/k` | CONSERVATIVE, fail-closed |
| `C09` | `most_common.h:14` `len > 1` | CONSERVATIVE in shipped build |
| `C05` | `restart_main.cpp:134` `k_effective <= k` | CONSERVATIVE, abort with no report |
| `C11` | *none* — ASan `alloc_dealloc_mismatch`, not an assert | CONSERVATIVE, "observed as an abort under ASan" |

Also present but without direction consequence: `lrs_test.h:20,54,87-110,130-224`
(suffix-array preconditions), `conditioning_main.cpp:603` (`C21`, proven
unfireable).

### Measured, both builds, same commit and data

| Finding | asserts live (shipped `Makefile`) | `-O2 -DNDEBUG` (packager default) |
|---|---|---|
| **`C07` site B** `lrsrep-2000.bin` | `rc=134` SIGABRT, no JSON | **`rc=0`, `errorLevel 0`, `"IID": true`, `hAssessed 0.995373734104443`**, `passedLongestRepeatedSubstringTest: false` |
| **`C07` site A** `bal125.bin` | `rc=134` SIGABRT, no JSON | `rc=0`, all three tests **pass**, `hAssessed 6.79603697656858` |
| **`C05`** sparse 8-bit, `H_I=2` | `rc=134`, `Assertion failed: (k_effective <= k)` | `rc=255`, `X_cutoff: 316`, `X_max: 385`, `*** Restart Sanity Check Failed ***` |
| **`C09`** all-zero | `rc=134`, `Assertion failed: (len > 1)` | ASan: **heap-buffer-overflow READ**, `markov_test.h:48`; `-c iid`: `rc=0`, `h' = -0` |

### Re-classification, and why site B is the serious one

**`C07` site B — CONSERVATIVE with asserts live, PERMISSIVE under NDEBUG.**
The code path is predictable from the source and the execution confirms it:
`p_colPower` underflows to 0, `log1pl(-0.0)` is `-0.0`, and the verdict
`return logl(0.999L) >= ((long double)N) * logProbNoColsPerPair` becomes
`-1.0005e-3 >= -0.0`, which is **false** — so the LRS test reports **failure**.
It has not detected anything about the data; it ran out of exponent range.

That failure is then **discarded by `C03`**, which is open on master. The result
is a published `hAssessed` of **0.9954 bit/bit** with `errorLevel 0` and
`"IID": true`, on data the tool could not evaluate. **This is a chain, and it
reports its ceiling:** an arithmetic representability limit becomes a test
failure, and a defect that discards test failures turns that into a passing
assessment above the project's 0.5 bit/bit threshold.

**`C07` site A — the assert is the whole defect.** Under NDEBUG the run
completes, all three IID tests pass, and `hAssessed = 6.79603697656858` for a
125-symbol exactly-balanced alphabet, against a ceiling of `log2(125) = 6.966`.
That figure is *correct*. So site A's assert does nothing but deny a legitimate
assessment of a perfectly uniform source — the best kind of source there is.
Direction: CONSERVATIVE with asserts live, **harmless and correct** under
NDEBUG.

**`C05` — better under NDEBUG.** The abort becomes a clean `rc=255` refusal
naming the reason (`X_max: 385` against `X_cutoff: 316`), which is what the tool
should have done. The cutoff 316 matches `OC-7`'s measured value at `H_I=2`.
CONSERVATIVE in both builds, but only informative in one.

**`C11` — the classification was never about an assert.** The scalar `delete`
of an array is detected by ASan's `alloc_dealloc_mismatch`, not by a compiled-in
check. In a shipped build it is silent: `simulateBound` was called and returned
in all 27 `OC-7` cutoff runs and in the `C05` runs above, on both assert-live
and NDEBUG builds, with no crash. So `C11` is **not** conservative — it is
silent undefined behaviour with no observed effect. Re-classified NEUTRAL with a
memory-safety flag, and the earlier "observed as an abort" wording was an
artefact of only ever running it under a sanitizer.

### Can the fork assume NDEBUG is off downstream? No.

Structural facts, checked:

- **Nothing in the tracked tree sets, requires, or documents `NDEBUG`.** The
  only occurrences are in prior audit records. No `#error` guard, no build
  check, no note in `README.md`, `BUILDING.md` or `NOTICE`.
- **`cpp/Makefile:31` *assigns* `CXXFLAGS`** rather than appending:
  `CXXFLAGS = -std=c++11 … -O2 -ffloat-store …`. A packager who overrides
  `CXXFLAGS` on the `make` command line — the ordinary distribution build
  idiom — replaces the entire set. That silently drops `-ffloat-store` as well,
  which this audit's own platform work shows affects the numerics.
- `-DNDEBUG` is the default for release configurations in common build systems
  (CMake's `Release` and `RelWithDebInfo` add it unconditionally), so a
  downstream repackaging that does not reuse this Makefile verbatim is likely to
  define it.
- The repository offers **no way to tell from a built binary's output** whether
  asserts were live. Nothing in the JSON records it.

**Therefore the NDEBUG classification is the one that matters for anything
shipped, and the live-assert classification is the optimistic case.** An
aggregate over mixed evidence reports its floor: `C07` must be carried as
**PERMISSIVE**.

### This shape is already in the fork's own records

The 2026-09-30 audit filed `N-03` with exactly this two-build structure —
*"assert abort, no JSON; with `-DNDEBUG` a heap over-read and a wild write"*,
categorised *"D in the shipped build; B under `-DNDEBUG`"*, with
*"the NDEBUG+ASan build is clean"* as a stated regression requirement. The
repository already knows that asserts-versus-NDEBUG changes a finding's class
and already has a vocabulary for it. The 2026-10-11 audit's direction triage
did not apply it. `C09`'s crash half is a **re-confirmation of `N-03`**, at the
same site (`markov_test.h:48`; the allocation line has drifted from
`utils.h:329` to `utils.h:406`), not a new finding.

### Recommended repair

The fork already has the right pattern and applied it four times — `F11`, `F12`,
`F15`, `F16` all replaced an abort with a **declined estimator** returning the
`-1` sentinel, kept out of the minimum by an explicit guard. The safety-critical
asserts should be the same: a runtime check that declines and reports, not a
compiled-in abort that disappears under a flag the project does not control.
Specifically for site B, the condition is a known, documented, *expected*
representability limit — the code comment says so — which makes it exactly a
"decline, report, and do not fold into the minimum" case rather than an
assertion about a programming error.

Minimum interim mitigation: an `#if defined(NDEBUG)` `#error` in a shared
header, so a build that would silently remove these checks fails to compile
instead. That is one line and it converts an unknown into a build failure.

**Correct and verified**: all four rows of the measurement table, by execution,
on both builds, with the shipped-Makefile column matching what was reported
earlier. **Not verified**: whether any specific downstream packaging of this
fork defines `NDEBUG` — the claim made here is structural (nothing prevents it,
nothing detects it, and release configurations commonly add it), not a survey.

---

## OC-11 — C16 verified as a chain: a typed `1e-400` disables both restart gates and reports success

**Verdict: the chain is real and reaches its ceiling, but not through the link
the cluster named.** `N-04` is already repaired on master and repaired well.
What survives is narrower and sharper than the cluster claimed, and it composes
with `OC-7`.

### Link 1 — what the `H_I` parse actually accepts

`restart_main.cpp:317-355` is a strict parse and its own comment already
documents the NaN hazard in full, including the consequence I was asked to
check:

> *"Every comparison with NaN is false, so a NaN H_I passes both the `H_I < 0`
> check here and the `H_I > word_size` check further down. It then reaches
> `p = pow(2.0, -H_I)`, which is NaN, and the index expression
> `(int)floor(randomUnit(...) / p)` … converts that NaN to int. That conversion
> is undefined behaviour and the result indexes `counts[]` out of bounds."*

So the fail-open-on-NaN that the sibling session's JavaScript finding predicted
**was already found and fixed here**. Measured on master:

| argument | result |
|---|---|
| `nan`, `inf`, `1e400` | **rejected** — "H_I must be a finite decimal number" |
| `1.0abc`, `1.0 ` (trailing space), `0,7` (locale comma) | **rejected** — partial parse caught by `*H_I_end != '\0'` |
| `-0.5` | rejected by the `H_I < 0` check |
| `1.0`, `.5`, `+0.5` | accepted, correct |
| ` 1.0` (leading space) | **accepted** — `strtod` skips leading whitespace. Harmless. |
| `0x1` → 1.0, `0x0.8p0` → **0.5** | **accepted** — C99 hex-float syntax |
| `1e-400`, `1e-320` | **accepted as 0.000000** — `errno` is set to 0 before the call and **never tested**, so `ERANGE` on underflow is ignored |

Two holes remain: hex-float syntax, and the unchecked `ERANGE`. **Neither is
closed on the repair branch** — `0`, `1e-400` and `0x0.8p0` are accepted
identically there.

### Link 2 — what `H_I = 0` does to both gates

`H_I = 0` is reachable from a typed `1e-400`, which is the kind of string a
mis-scaled script or a hand-entered scientific-notation estimate produces. It is
also accepted directly. Executed on master, `uniform-1bit.bin`:

```
H_I: 0.000000
ALPHA: 5.0251553006530614e-06, X_cutoff: 1000
X_max: 558
Restart Sanity Check Passed...
H_r: 0.993899   H_c: 0.993899   H_I: 0.000000
Validation Test Passed...
min(H_r, H_c, H_I): 0.000000
rc=0    JSON errorLevel: 0   IID: true
```

**`X_cutoff: 1000` is the maximum attainable value.** With `H_I = 0`,
`p = 2^0 = 1` and `k_effective = ceil(1/p) = 1`, so the simulation draws a
one-symbol source whose every row count is 1000. The §3.1.4.3 sanity check
therefore **cannot fail for any input**. And `H_I/2 = 0` makes
`min(H_r,H_c) < 0` false, so the §3.1.4.3 validation test **cannot fail
either**. Both restart gates are disabled, and both report PASS.

### The chain, at its ceiling

1. `strtod`'s `ERANGE` is not checked → a typed `1e-400` becomes `H_I = 0`.
2. `H_I = 0` → `k_effective = 1` → simulated cutoff **1000** → the sanity check
   is unconditionally satisfied.
3. `H_I/2 = 0` → the validation test is unconditionally satisfied.
4. `rc=0`, `errorLevel 0`, `"IID": true`, "Restart Sanity Check Passed",
   "Validation Test Passed".
5. `OC-7` composes *on top*: even with a correctly typed `H_I` the cutoff is
   already more permissive than the standard sanctions, by up to 0.34 bit of
   equivalent slack. `H_I = 0` is that same mechanism driven to no constraint at
   all.

**Direction: PERMISSIVE for the verdict, conservative for the figure.** The
published `min(H_r, H_c, H_I)` is `0.000000`, so a consumer reading the *figure*
gets a useless number. A consumer reading the *restart verdict* — which is what
the reachability test says TruePad consumes, the restart assessment being one of
the two halves — sees a passed sanity check and a passed validation test on a
run where neither could have failed.

### A separate defect this exposed: the test emits neither quantity it asserts about

The JSON report contains **no sanity-check field at all**. The Overall test case
carries `h_c, h_i, h_r, mean, median, passedChiSquareTests,
passedIidPermutationTests, passedLongestRepeatedSubstringTest,
permutationTestResults, testCaseDesc` — and **neither `X_max` nor `X_cutoff`
nor any `passedRestartSanityCheck`**. On a *failure* the result reaches the
consumer as `errorLevel -1` with `errorMsg "Restart Sanity Check Failed."`; on a
*pass* there is no positive record and the two numbers that decided it are
stdout-only.

So a consumer cannot distinguish "passed with `X_max 558` against a legitimate
cutoff of 570" from "passed because the cutoff was 1000". The margin is
unauditable from the report. **A test that asserts about a quantity must emit
that quantity** — this one asserts about two and emits neither.

### Recommended repairs

1. Check `errno == ERANGE` after `strtod` and reject. One condition, alongside
   the three already there.
2. Reject hex-float syntax, or document that it is accepted. The existing
   strictness makes the hex acceptance look like an oversight rather than a
   choice.
3. **Reject `H_I = 0`** for the restart test, or flag it: an entropy claim of
   zero makes both gates vacuous, and there is nothing to validate against a
   claim of no entropy.
4. Emit `X_max`, `X_cutoff` and a `passedRestartSanityCheck` boolean in the
   JSON, so the margin is auditable and `OC-7`'s permissiveness is visible to a
   consumer.

A regression must be shown failing: construct `H_I = 1e-400`, assert the run is
refused, and confirm the assertion fails against current master, which accepts
it and reports `X_cutoff: 1000`.

**Correct and verified**: the parse table by execution on master; the repair
branch accepting the same three values; `H_I = 0` producing `X_cutoff: 1000`
with both gates passing and `rc=0`; the absence of sanity-check fields from the
JSON. **Not verified**: whether any realistic TruePad invocation path can
produce a mis-scaled `H_I` string — that is a question about TruePad's code,
which this session has not read and must not touch. The hazard is recorded in
`CROSS-REPO-FINDINGS.md` as `XR-03`.

---

## OC-12 — C22's remainder: conservative, not permissive. The cluster clears the register.

**Verdict: `C22` is re-classified from PERMISSIVE to CONSERVATIVE.** Its one
permissive-by-description item (`ZALPHA`, `OC-8`) is not a defect, and the
remainder under-reports entropy at every extreme tested. One fragility is
recorded.

### `predictors-9` — the `N == 1` division by zero does not escape

`utils.h:1043`:

```c
if(p_global > 0) p_globalPrime = min(1.0, p_global + ZALPHA*sqrt((p_global*(1.0-p_global))/((double)N-1.0)));
else              p_globalPrime = 1.0 - pow(0.01, 1.0/(double)N);
```

At `N == 1` the divisor `(double)N-1.0` is exactly zero. Tested at the extremes
through a harness calling the production header directly:

| `C` | `N` | `k` | `P_global` | `P_global'` | min entropy | `isnan` |
|---:|---:|---:|---|---|---|---:|
| 1 | 1 | 2 | 1 | 1 | **-0** | 0 |
| 1 | 1 | 256 | 1 | 1 | **-0** | 0 |
| 0 | 1 | 2 | 0 | 0.98999999999999999 | 0.014499569695115089 | 0 |
| 1 | 2 | 2 | 0.5 | 1 | -0 | 0 |
| 2 | 2 | 2 | 1 | 1 | -0 | 0 |
| 10⁶ | 10⁶ | 256 | 1 | 1 | -0 | 0 |

**No NaN and no Infinity reaches the returned estimate at any extreme.** At
`N == 1` with `C == N` the expression is `sqrt(0/0)` = NaN, and at `N == 1` with
`0 < C < N` it is `sqrt(positive/0)` = ∞; both are absorbed and the result is
`min entropy = -0` — **zero entropy, the maximally conservative answer**. The
`C == 0` case never divides, taking the documented `1 - 0.01^(1/N)` branch.

So `predictors-9` is **CONSERVATIVE**, matching the finder's own `underestimate`
direction, and the user's concern about an Infinity or NaN passing a comparison
silently does not materialise here. Three guards are responsible, and it is
worth separating the deliberate from the lucky:

| Guard | Form | NaN-safe? |
|---|---|---|
| `if(p_global > 0)` | NaN fails the test, takes the `else` | **deliberate** — this is the `!(x > 0)` idiom in its positive form |
| `fmax(curMax, p_globalPrime)` | `fmax` is specified to return the non-NaN operand | **deliberate** — measured: `fmax(0.5,NaN)` and `fmax(NaN,0.5)` both give 0.5 |
| `if(curMax < 1.0)` | NaN fails the test, `p_local` is skipped | **deliberate** |
| `min(1.0, …)` | returns the **first** argument when the comparison is false | **accidental** |

### The one fragility: NaN suppression depends on argument order

Measured:

```
std::min(1.0, NaN) = 1      <- the form at utils.h:1043
std::min(NaN, 1.0) = nan    <- the same expression, arguments swapped
```

`std::min(a,b)` returns `(b < a) ? b : a`, and every comparison with NaN is
false, so it returns `a`. The NaN at `N == 1, C == N` is suppressed **only
because `1.0` is written first**. Swap the arguments — a change a reviewer would
read as cosmetic — and NaN reaches `entEst`, is returned, and enters the `min()`
folds in `non_iid_main.cpp`. That is exactly prior finding **`F13` ("NaN into
std::min"), still carried as UNCONFIRMED**: the code is one argument-order edit
away from making it real. Worth a comment at the site, or `fmax`-style explicit
handling, so the property is stated rather than incidental.

I did **not** establish whether the division raises `FE_DIVBYZERO`/`FE_INVALID`
at runtime: my probe was constant-folded at `-O2` and reported no flags, which
is a compile-time artefact rather than a measurement. Unverified either way, and
the tool checks FP flags nowhere regardless.

### `predictors-5` — `P_local`'s quantisation, conservative at every extreme

`calc_p_local(maxrun, N, ldomain)` bisects for `p` where
`prediction_estimate_function(p, maxrun+1, N) = log(0.99)`. The harness reports
the achieved `f(p)` beside the target:

| call | returned `p` | `f(p)` | target `log(0.99)` | side |
|---|---|---|---|---|
| `cpl 23 1000000 0.5` | 0.50000000002910383 | -0.029801688496229006 | -0.010050335853501451 | below |
| `cpl 1000000 1000000 0.5` | 0.9999954705124896 | -0.010050335873434884 | -0.010050335853501451 | below by 2.0e-11 |
| `cpl 60 1000000 0.001` | 0.75675162425223963 | -0.01005033604720024 | -0.010050335853501451 | below by 1.9e-10 |
| `cpl 1 1000000 0.5` | 0.75 | -287700.98301988264 | — | below |
| `cpl 1 4503599627370496 0.5` | 0.75 | -1295604871231189 | — | below |
| `cpl 0 1 0.5` | 0.50000000000000011 | -1.3307755363153915 | — | below |

`prediction_estimate_function` is decreasing in `p`, so `f(p) < log(0.99)`
means the returned `p` is **at or above** the true root. A larger `p` raises
`curMax`, and `entEst = -log2(curMax)` is therefore **lower** — an
under-estimate. **Every extreme tested lands on the conservative side.**

**I did not reproduce the finder's worst non-conservative case of
+1.6e-11 bit.** That specific number remains their claim, unverified by me. What
is verified is that the quantisation exists, that its effect on `f` is at most
~2e-10 at these extremes, and that the sign at every extreme is conservative.

One extreme is worth naming: `cpl 1 1000000 0.999999` returns exactly **1.0**,
for which `f(1.0)` is NaN. In production that NaN is never computed — the
guard `if((curMax < 1.0) && (f(curMax) > log(0.99)))` evaluates `f` at `curMax`
*before* calling `calc_p_local`, never at the returned value — and
`fmax(curMax, 1.0) = 1.0` gives `entEst = -0`. Conservative. The NaN in the
table above is my harness evaluating `f` at the returned `p`, not a production
path; recorded so it is not mistaken for one.

### Register consequence

`C22` leaves the permissive register. Its three parts: `ZALPHA` measured at
+3.80e-06 bit and **not a defect** (`OC-8`); `predictors-9` **conservative**,
reporting zero entropy at `N == 1`; `predictors-5` **conservative** at every
extreme tested. The remaining members (`predictors-3`, `-4`, `-7`, and the
`estimators-mcv-*` and `estimators-ttuple-lrs-*` items already covered in that
dimension's own report) are all claimed conservative or neutral by their
finders and none is claimed permissive, so nothing in `C22` now sits on the
permissive register.

**Correct and verified**: the `N == 1` extremes, the three NaN guards, the
argument-order fragility, and the conservative sign of `P_local`'s quantisation
at six extremes. **Not verified**: the finder's +1.6e-11 bit non-conservative
case, and whether the `N == 1` division raises FP flags at runtime.

---

## OC-13 — C21's permutation statistics and C20's races: two more register entries clear

### C21 — the out-of-bounds reads are real, unreachable on a supported path, and guarded only by an assert

`permutation_tests.h`:

```c
unsigned int periodicity(const uint8_t data[], const unsigned int p, const unsigned int n){
	unsigned int T = 0;
	assert(n>=p);                        // :256  -- A GUARD EXISTS
	for(unsigned int i = 0; i < n-p; ++i){ …

unsigned long int covariance(const uint8_t data[], const unsigned int p, const unsigned int n){
	unsigned long int T = 0;
	for(unsigned int i = 0; i < n-p; ++i){ …   // :275  -- NO GUARD OF ANY KIND
```

`n` and `p` are both `unsigned`, and `p` comes from the fixed set {1, 2, 8, 16,
32}, so `n < p` makes `n-p` wrap to roughly 4·10⁹ and the loop runs far past the
buffer.

**Two corrections to the finder's claim.** `memory-safety-fuzz-6` says
*"covariance has no guard at all, so … the same in the assert-enabled build,
because covariance has no assert."* The first half is right; the second is wrong
for the path that actually executes:

| build | observed |
|---|---|
| assert-live (shipped) | `Assertion failed: (n>=p), function periodicity, file permutation_tests.h, line 256` — **`periodicity` aborts first**; `covariance` is never reached, because `periodicity_tests` runs before `covariance_tests` |
| `-DNDEBUG` + ASan | `heap-buffer-overflow READ of size 1` in **`periodicity`** ← `periodicity_tests` ← `run_tests` |

The finder's covariance-specific evidence came from a direct harness call
(`harness_ndebug covariance 31 32`), which bypasses `periodicity`. That is a
valid isolated test but not the production path, and the record presents it as
though it were.

**Reachability — unreachable on a supported path.** `conversion1` is applied
only for binary data and divides the length by 8, so a compliant 1,000,000-sample
input gives `cs1.size() ≈ 125,000`, far above 32. Reaching `n < 32` needs fewer
than ~256 samples. Measured:

```
200 samples, no escape          -> rc=255  "requires at least 1000000"
-l 0,200 subset of a 1M file    -> rc=255  "requires at least 1000000"
200 samples, EA_ALLOW_SHORT_DATASET=1, assert-live  -> rc=134, periodicity assert
200 samples, EA_ALLOW_SHORT_DATASET=1, NDEBUG+ASan  -> heap-buffer-overflow READ
```

**A `-l` subset cannot bypass the rule** — the §3.1.1 check applies to the count
actually loaded, after the subset. So this is reachable only with the test-only
escape set.

**Direction: NEUTRAL on a supported path** (unreachable), **memory-unsafe under
`-DNDEBUG` with the escape**. Another instance of `SHAPE-02`: the only guard is
an assert, so it exists in one build and not the other.

**One forward-looking note.** `covariance`'s missing guard is currently *masked*
by `periodicity`'s assert killing the process first. Repairing `periodicity`
alone — converting its assert to a decline, which is the right fix — would
**expose** `covariance` as the live out-of-bounds site. The two must be fixed
together, and a regression must exercise both.

### C20 — the races are real and cannot change a verdict

`test_status[]` is written inside `#pragma omp critical(resultUpdate)`
(`:670`) and read outside it, both at `:650` and inside `run_tests`. That is a
genuine data race. It cannot change the outcome, and the reason is structural
rather than statistical:

1. **`test_status[j]` is monotone.** Initialised `true` at `:598` and only ever
   assigned `false` at `:670`. Never set back.
2. **A stale `true` costs only redundant work.** A thread may compute statistic
   `j` for one extra round; the aggregation at `:661` re-reads `test_status[j]`
   *inside* the critical region and skips the update, so the extra result is
   discarded.
3. **An early-visible `false` drops a round that was already redundant.** The
   condition for setting `false` — `(C[j][0]+C[j][1] > 5) && (C[j][1]+C[j][2] > 5)`
   — is exactly the final pass condition, so once it is set the test has already
   met its threshold and further rounds cannot change its outcome.
4. **The verdict does not read `test_status[]` at all.** `:731-736` computes it
   from `C[][]`, and `C[][]` is modified only inside the critical region.

So every input to the verdict is protected, and the raced variable is not an
input to it. **Direction: NEUTRAL.**

The `completed` counter is a separate matter and genuinely inconsistent: it is
incremented inside the critical region at `:676` and via `#pragma omp atomic` at
`:720`, which do not synchronise with each other. Its only consumer is the
progress string at `:696` (`100.0*completed/PERMS`). **Consequence: a wrong
progress percentage.** Cosmetic.

**Correct and verified**: the guard asymmetry between `periodicity` and
`covariance`, both builds' behaviour on a 200-sample input, the refusal of both
a short file and a short `-l` subset on a supported path, and the four-step
argument that the verdict's inputs are all critical-region protected.
**Not verified**: I did not run ThreadSanitizer. The claim that these races
cannot change a verdict rests on the monotonicity and data-flow argument above,
which is a correctness argument rather than a sampling one — but it is an
argument, not a dynamic measurement, and is labelled as such.

---

## OC-14 — C14: the consumer contract, five of eight members verified

The last on-path cluster. `XR-01` (the stale report file) was verified earlier;
this completes the rest. Everything here is about what a harness reads, which is
why it is on-path.

### Verified by execution

**`oac-16` — `--version` anywhere in argv exits 0, including as the filename.**
`non_iid_main.cpp:91-97` scans **all of `argv` from `i=0`** for the literal
string, before `getopt`:

```
ea_non_iid -q -o v.json "--version" 1      -> rc=0, prints "noniid 1.1.8", NO JSON
ea_non_iid -q -o v.json -- "--version" 1   -> rc=0, same; the `--` separator does not help
```

A harness invoking the tool on a file named `--version`, or with that string
anywhere in its argument vector, gets **exit 0 with nothing assessed and no
output file**. On the exit-status channel that is a fail-open.

**`oac-5` — every failure is `255`, and the one outcome worth distinguishing is `0`.**

| invocation | rc | `errorLevel` |
|---|---:|---|
| `-l 5,0` (invalid argument) | 255 | -1 |
| nonexistent file | 255 | -1 |
| `-Z` (unknown option) | 255 | *no JSON at all* |

A harness cannot tell an invalid argument from a missing file from an unknown
option. And the outcome it most needs — a *statistical* rejection — is not 255
at all: on master `ea_iid` returns **0** for a failed IID suite (`C03`). So the
status channel conflates every error and excludes the one result that matters.

**`oac-12` — four distinct file problems, one message, no provenance.**

| path | rc | `errorMessage` | `filename` | `sha256` |
|---|---:|---|---|---|
| `/nonexistent/f.bin` | 255 | `Error: could not hash the input file.` | `None` | `None` |
| a directory | 255 | *identical* | `None` | `None` |
| mode-000 file | 255 | *identical* | `None` | `None` |
| `/dev/zero` | 255 | *identical* | `None` | `None` |

Nonexistent, directory, permission denied and not-a-regular-file are
indistinguishable, and the report does not record which path was attempted.

**`oac-6` / `restart-9` — `-q` strips the verdict from stdout, but the JSON keeps
the failure.** On a genuine sanity-check failure (forced `X_max = 28`, `H_I = 7`):

| | verbose | `-q` |
|---|---|---|
| stdout | `X_cutoff: 27`, `X_max: 28`, `*** Restart Sanity Check Failed ***` | **14 bytes: `H_I: 7.000000`** |
| rc | 255 | 255 |
| JSON | — | written: `errorLevel -1`, `errorMessage "Restart Sanity Check Failed."` |

**The finder's claim is partly overstated**: `-q` does remove the verdict and
both deciding numbers from stdout, but a harness using `-o` still learns that
the sanity check failed, and why. What it never learns — on either path, quiet
or not — is `X_max` and `X_cutoff`, which is the `OC-11` gap. Refined
statement: **the failure is machine-detectable; the margin never is.**

### Source-confirmed, not executed

**`oac-13` — the report write is not atomic.** `TestRunUtils.h:33-52`:
`output.open(path.c_str())` truncates the final path immediately, then writes,
then `close()` — with the close error correctly checked (that is `N-09`,
repaired). There is **no temp-file-and-rename**. So a signal or power loss
between open and close leaves a truncated, syntactically invalid JSON at the
path a consumer reads, and a concurrent reader can observe a partial file.
Labelled source-confirmed: I did not time a signal into the write window, and
I am not claiming an execution I did not perform. The fix is
write-temp-then-`rename`, which is atomic on POSIX.

### Not reached, with the reason

**`restart-8` — I could not construct an input that fails the §3.1.4.3
validation test while passing the sanity check**, so I cannot say what the
validation-failure JSON contains. The reason is structural and worth recording:
in `-i` mode both gates are driven by the same statistic. The sanity check
passes only if `X_max ≤ cutoff(H_I)`, and `H_r` is bounded below by roughly
`-log2(X_max/1000)`, so

| H_I | cutoff | implied `H_r` floor | `H_I/2` | can validation fail? |
|---:|---:|---|---:|---|
| 1 | 572 | 0.806 | 0.5 | no |
| 2 | 316 | 1.66 | 1.0 | no |
| 8 | 19 | 5.72 | 4.0 | no |

In every case the implied floor on `H_r` exceeds `H_I/2`, which suggests **the
validation test may be unreachable in `-i` mode whenever the sanity check
passed** — i.e. redundant. That is a hypothesis from three data points and the
relationship between `H_r` and `X_max`, **not a verified claim**: I have not
confirmed that `H_r` in `-i` mode is exactly the MCV estimate over rows, and a
counterexample at some other `H_I` would refute it. Recorded because if true it
is a more interesting finding than `restart-8` itself.

### C14 status

| member | status |
|---|---|
| `oac-4` stale report file | **VERIFIED** (`XR-01`) |
| `oac-5` uniform 255 | **VERIFIED** |
| `oac-12` collapsed file errors | **VERIFIED** |
| `oac-16` `--version` exit 0 | **VERIFIED** |
| `oac-6` / `restart-9` `-q` suppression | **VERIFIED**, finder partly overstated |
| `oac-13` non-atomic write | source-confirmed, not executed |
| `restart-8` validation-failure JSON | **not reached**; path may be unreachable |

Direction for the cluster: **UNKNOWN resolves to permissive-on-the-status-channel.**
Three independent ways for a harness to read success where there is none —
a stale file (`XR-01`), `exit 0` on a `--version`-named input (`oac-16`), and
`exit 0` for a failed IID suite (`C03`) — against one way to read failure
without a cause (`oac-5`, `oac-12`).

---

## OC-15 — the battery measured against known defects: my own blind-spot claim refuted, and the real mechanism found

**This is the most consequential check in the audit, and it began by refuting
something I had committed twenty minutes earlier.**

Parts 5-7 of `SECOND-SOURCE-SEARCH.md` argued from arithmetic that the estimator
battery could not see mains-frequency modulation, because MultiMCW's longest
window (4095 samples, `multi_mcw_test.h:9`) is shorter than a 60 Hz period at
0.3 Mbit/s (5000 samples) — a "73.3 Hz floor". Standing rule: **suspect the
instrument before the thing measured.** So I measured it.

**Method.** `cpp/ea_non_iid` built from `dd2996f` with `cpp/Makefile`'s own flags
(Apple clang, arm64, `-O2 -ffloat-store`, **`NDEBUG` absent — asserts live**).
Build provenance by construction, which `build-provenance-canary.sh`'s own header
calls strictly stronger than the canary. Five seeded streams from
`generators/blindspot_streams.py`, 1,000,000 one-bit samples each, **all globally
unbiased** so MCV cannot separate them, plus five independent clean controls.

**Result 1 — the claim was wrong.** A period-5000 bias oscillation is detected
*hard*: MultiMCW 0.998 → 0.835 (−0.163), Compression −0.235, Collision −0.128,
t-Tuple −0.104. **The error was assuming a window must exceed the period.** For a
slow drift the opposite holds — W = 63 sees a nearly-constant local bias and
predicts it successfully. There is no 73.3 Hz floor for bias drift, and the VREF
mechanism Part 5 found in the schematic **is** visible to the battery. A hardware
risk relieved by measurement.

**Result 2 — the reach argument survived its half.** Against a lag-5000
correlation, **every predictor was blind**: MultiMCW −0.003, Lag +0.000,
MultiMMC −0.003, LZ78Y −0.000, Markov −0.000. Exactly as the window bounds
predict. But **LRS caught it at −0.377**, because that construction copies
`x_{i-5000}` and so creates exact repeated substrings — the loophole my own
"obvious objection" section had already named, walked into by my own test case.

**Result 3 — the real blind spot.** Stream E: copy `x_{i-5000}` with probability
0.04, giving P(agree) = 0.5203, a **+40.4 σ** autocorrelation signal with almost
no exact repetition. Beyond predictor reach, not local bias, not repetition.

| | value |
|---|---|
| `H_original` on E | **0.856713** |
| clean range, 5 independent controls | **[0.843936, 0.865774]** |
| E's position | **+0.23 sd from the clean mean — inside** |
| only detector | LRS, −0.0223 |
| LRS above the binding minimum | **+0.1164 bit** |

**A 40 σ defect produced a verdict statistically indistinguishable from clean.**

**Correction made in place:** I first wrote that the figure "went UP" (0.847 →
0.857). It did not — +0.0097 is 0.23 sd of Compression's clean spread
(sd = 0.0092), so noise explains it, and claiming an increase would read a
direction into noise. **The correct claim is NO REDUCTION**, which is the finding
and does not need the figure to have risen.

**Mechanism: not reach — the `min` discards the detector.** Compression binds in
all five controls at 0.8546 ± 0.0092; LRS detected E but reads 0.973, 0.1164 bit
above the minimum. A detection only reaches the verdict if the detecting
estimator *is* the minimum. See `OC-16` for the budget, `SHAPE-07` for the
corrected general form.

**Status: VERIFIED as an instrument property.** No hardware claim upgraded; see
`OC-17` and Part 11 on why synthetic input is correct here.

---

## OC-16 — the detection budget: nine of ten estimators cannot affect the verdict on near-uniform data

Five independent clean fair-coin streams. **Headroom = clean mean − clean binding
minimum**, i.e. the detection budget an estimator wastes.

> ## ⚠ SCOPE OF THIS TABLE — read before using any number in it
>
> **This table characterises the INSTRUMENT on ideal input. It does not
> characterise any device.**
>
> Every figure below was measured on **fair-coin data at ~1.0 bit/bit**. The
> conclusion people will quote from it — *"nine estimators are decorative"* — is
> **conditional on Compression being the binding estimator**, and that has been
> tested **only at 1.0**.
>
> **At a real unit's 0.7–0.86 bit/bit the binding estimator is UNKNOWN and must
> be measured.** If it is not Compression, this table is not shifted, it is
> **invalidated**: every headroom is computed against Compression's clean
> minimum, so a different binder recomputes all ten rows and changes which
> estimators can reach a verdict. `cpp/selftest/regression-outside-battery.sh`
> pins the binding assumption on clean data precisely so that a change is
> reported rather than assumed away — but it pins it *at 1.0*, which is the only
> place it has ever been checked.
>
> **Consequence for the method, which runs in both directions:** synthetic data
> calibrated this instrument and that was legitimate. **It cannot produce a
> device baseline.** A per-device baseline is a claim about a **source**, so
> anything that synthesised one would be the exact claim upgrade the standing
> constraint forbids. Per-device baselines stay **NOT RUN** until hardware
> exists. See **Part 11** for the single statement of that distinction.

| estimator | clean mean | sd | headroom | binds on clean data? |
|---|---:|---:|---:|---|
| MCV | 0.994603 | 0.000464 | +0.1400 | no |
| Collision | 0.914996 | 0.014876 | +0.0604 | no |
| Markov | 0.997987 | 0.001125 | +0.1433 | no |
| **Compression** | **0.854637** | **0.009224** | **binds** | **YES, 5/5** |
| t-Tuple | 0.925195 | 0.009810 | +0.0706 | no |
| LRS | 0.993369 | 0.002444 | +0.1387 | no |
| MultiMCW | 0.998065 | 0.000725 | +0.1434 | no |
| Lag | 0.995904 | 0.001415 | +0.1413 | no |
| MultiMMC | 0.996306 | 0.000986 | +0.1417 | no |
| LZ78Y | 0.995533 | 0.000673 | +0.1409 | no |

**Compression binds in all five; no other estimator binds in any.** Only LRS was
ever binding on a defect stream (on D, a 600 σ copy correlation). **MCV, Markov,
Lag, LZ78Y and MultiMMC never came within a factor of five of their own headroom
on any defect tested** — decorative for verdict purposes on a near-uniform
source.

**The finding:** the battery has ten estimators, the verdict is determined by
one, and the other nine's detections are conditional on exceeding a headroom
**nobody publishes** — not in SP 800-90B, not in the tools' output, not
recoverable from a reported figure. The figure's resolution is its most
pessimistic estimator's sampling noise (0.0092), not its most sensitive
estimator's signal. **Adding estimators does not fix it**, which is why no
purchase can.

**Cheapest mitigation in the audit, and it is free: emit the per-estimator
breakdown, not the minimum.** The breakdown holds LRS's −0.0223; the minimum does
not. The tools already print it under `-v`. Filed as `XR-06`.

---

## OC-17 — the outside-the-battery check, built, calibrated, and shown failing

`tools/outside-battery-check.cpp`, self-contained C++11 with an inline radix-2
FFT so a consumer who did not build the repo can still run it. **Not an entropy
estimator; emits no figure.**

**Pre-registered thresholds.** Autocorrelation **5.731 σ** — Bonferroni,
family-wise α = 0.001 over 100,000 lags (per-lag two-sided 5×10⁻⁹); correct
because sample autocorrelations of a white process are asymptotically independent
across lags. **At an uncorrected 3 σ, 100,000 lags expect ~270 false hits.**
Lag range 1..100,000 bounded below by cost (free) and above by statistical power
(clamped to N/2) and physics (0.33 s ≈ 3 Hz at 0.3 Mbit/s, covering mains,
harmonics, USB frame and switching ripple).

**My analytic spectral model was measured and rejected.** Spectral check
isolated, 25 clean streams:

| threshold | source | fired |
|---|---|---:|
| 18.5× | analytic Exp(1), α = 0.01 | **2/25 — 8 %, nominal 1 %** |
| 20.8× | analytic, α = 0.001 | 0/25, but clean max 20.3× — a 2 % margin |
| **30×** | **empirical** | **0/25, margin 1.48×** |

The rejection is of the model's **tail shape** — 2× zero-padding correlates
adjacent bins, so no α delivers its stated rate — not of a single threshold.

**Calibration: 25 independent clean streams**, 5 Mersenne Twister + **20
`os.urandom`**, deliberately two generators. Autocorrelation max |z| 4.04..5.18
(mean 4.47, sd 0.28), **0/25** over 5.731. Spectrum 13.0..20.3, **0/25** over 30×.

**Demonstrated:** silent on all 25 controls; fires on all four defects.
**B's spectrum recovers the mechanism directly — 8538.7× at 59.938 Hz** from a
stream whose only structure is a period-5000 bias oscillation. **E reads 40.21 σ
at lag 5000 = 60.000 Hz.**

**The two checks are complementary and neither alone suffices:** E reads 15.7× on
the spectrum, *below* the 20.3× clean max — the spectrum does not see E. The
spectrum, conversely, names a frequency.

**Shown failing, three ways.** `--sigma 50` **misses E** (exit 0), so the
threshold is load-bearing with a 7× margin. `--no-correction` fires on **5/5**
clean streams (160 false lag hits on one control against ~270 predicted).
Lowering the spectral threshold: 30× → 0/25, **20× → 2/25**, **13× → 24/25**.

**Limits recorded in the tool's own header and in `XR-06`:** linear correlation
only — `x_i = x_{i-k} XOR x_{i-m}` has zero autocorrelation everywhere and
passes; only the lags tested; thresholds calibrated for 1,000,000 one-bit samples
and **not** universal; **a pass is the absence of one kind of evidence, not an
entropy claim.**

**Status: BUILT and VERIFIED against known input. NOT RUN on hardware.**

---

## OC-18 — the case both tools miss: REACHABLE, confirmed

`OC-16`'s headroom table and `OC-17`'s limits section combine to predict an
uncovered case: a structure that trips only the decorative predictors by less
than their headroom, and has no linear correlation, is invisible to the battery's
verdict *and* to the outside check. **It is reachable.** Full derivation in
`SECOND-SOURCE-SEARCH.md` Part 12.

`G_xor13_02`: `x_i = x_{i-1} XOR x_{i-3}` with probability 2 %, else a fair coin.

| | measurement |
|---|---|
| `H_original` | **0.860003 — INSIDE** the clean range [0.843936, 0.865774], +0.6 sd |
| Compression (binds) | +0.0054 — 0.3 × its 2 sd, **noise** |
| **MultiMMC** | **−0.0266 — 9.0 × its 3 sd, strongly real** |
| MultiMMC headroom | 0.1417 — the drop is **5× too small to bind** |
| outside check | **4.30 σ / 16.5× — silent on both** |

**Both tools report clean; the defect exists only in the per-estimator
breakdown.**

**The mechanism, found by being wrong first.** I predicted taps (1,2) would have
zero linear correlation; the outside check fired at **50 σ at lag 3**, because
**a+b = 3 is itself a tap** and the triple product closes through the recurrence.
Taps whose sum is not a tap — (1,3), (2,5), (3,7), (7,16), (11,16) — are all
linearly silent at max |z| ≈ 3. Tap choice decides linear visibility, and (1,2)
is kept in the corpus as `F_xor30`, the counterexample.

**The band is p ≈ 1–2 %**, bounded below by MultiMMC's noise and above by
Compression's, since Compression tracks MultiMMC at ≈0.76× with a 20× larger
noise floor. Narrow, real, and unannounced.

**Consequence, now in `XR-06`:** the breakdown is not merely useful but
**necessary** — and insufficient without a **baseline**, since `MultiMMC =
0.9697` is unremarkable in isolation and damning as −0.0266 against
0.996306 ± 0.000986. **The fair-coin baselines will not serve per device**: a
real source is not at 1.0 bit/bit, and at ~0.7–0.86 Compression may not be the
binding estimator at all, which would invalidate the headroom table rather than
shift it. Per-device baselines are required, from real captures with known
provenance — and being source claims, they must never be synthesised.

---

## OC-19 — the regression, with the corpus made reproducible and the checks shown failing

`cpp/selftest/regression-outside-battery.sh`, picked up automatically by
`run-all-checks.sh`. ~3 s in fast mode. Part 13 has the detail.

**First, a defect in my own earlier work, fixed.** The published calibration drew
20 of its 25 controls from `os.urandom`, which **cannot be regenerated** — so the
calibration rested on streams nobody could reproduce. Replaced with a seeded
SHA-256 counter-mode generator (still a second, different algorithm) and
**re-measured**: max |z| 5.18 → **5.01**, spectrum max 20.3× → **20.2×**, false
positives **0/25 either way**. No conclusion changed. The five Mersenne Twister
controls kept their original seeds, so the `OC-16` baseline **reproduces
byte-for-byte** — the full run returns Compression = 0.847017, 0.843936,
0.861222, 0.855238, 0.865774, exactly as published.

**It pins outcomes, not constants** — B's peak at 8538.7× / 59.938 Hz, E at
40.21 σ / lag 5000 — so an FFT or accumulator change fails it with every
threshold untouched. It also pins **Compression as the binding estimator on 5/5
clean streams at 0.8546 ± 0.0092**, because `OC-16`'s whole table assumes it; a
future build that changes this is told the table is invalid rather than left to
publish it. Digest mismatch is a failure, not a warning.

**Shown failing, with distinct named failures:**

| perturbation | result |
|---|---|
| bit-reversal permutation broken | FAIL — B's peak, 8538.9× |
| twiddle error 1e-3 | FAIL — B's peak, 8534.1× |
| `sqrt(N)` for `sqrt(N−k)` | FAIL — E's sigma, 40.31 |
| spectral threshold 30 → 13 | FAIL ×2 — 5/5 clean false positives **and** the OC-18 coverage check |
| **twiddle error ≤ 1e-5** | **PASS — not caught; a real limit, recorded** |

**Measurement corrected two assumptions.** E's sigma is **insensitive to every
FFT perturbation tried**, because `r = c[k]/c[0]` is a ratio in which the errors
cancel — so **B pins the FFT and E pins the accumulator**, and they are not
redundant. And the 1e-5 limit is below what matters for these statistics but is
stated rather than implied.

**One check guards a false negative:** `G_xor13_02` must stay **silent**. If a
future version fires on it, coverage has genuinely changed and `OC-18`/`XR-06`
must be re-documented. A check that fires on everything pins nothing.

---

## OC-20 — "pre-existing and known" interrogated: two possibilities closed, a third one found

State read: `master @ 7e24e8b` (== `origin/master`), binaries built from that tree
with `cpp/Makefile`'s own flags.

I labelled a `selftest` failure on `biased-random-bytes.bin` and
`ringOsc-nist.bin` as "the documented upstream #155 macOS arm64 delta". **The
label was doing work that the mechanism behind it cannot do**: `C08`/`OC-4`
already established that `--allow-known-platform-deltas` matches **by filename
with no magnitude bound**, demonstrated by corrupting `ringOsc-nist`'s assessed
figure by 0.096 bit and still getting PASS. So "known" cannot mean "bounded".
Three possibilities were put; they resolve differently.

### Possibility 1 — the allowance was not applied. CONFIRMED, and it is the whole explanation of the label.

`run-all-checks.sh:73` excuses selftest only when `--allow-known-platform-deltas`
is passed. **I did not pass it.** Re-run with the flag, same tree:

```
  selftest                           PASS (only the known upstream #155 platform files)
```

So the FAIL was the harness correctly refusing to excuse a known delta that
nobody asked it to excuse. Benign; the differing flag path is simply my omission.

### Possibility 2 — the delta has grown. REFUTED, with numbers.

Measured against what `BUILDING.md` documents:

| file | measured now | documented |
|---|---|---|
| `biased-random-bytes.bin` | **7 values, max 3.659e-10** | "3.7e-10, 7 predictor values > 1e-10" |
| `ringOsc-nist.bin` | **1 value, 1.547e-10** | "1.5e-10, 1 predictor value > 1e-10" |

Counts match exactly, magnitudes to two significant figures. The affected values
are MultiMCW / MultiMMC / Lag `min entropy` and `P_local` — the predictor family
upstream #155 concerns. **No drift.** Worth stating plainly because the allowance
could not have told us this: it was established by measuring, not by the flag.

### Possibility 3 — something else changed. CONFIRMED. This is a new finding.

**All eleven reference files predate this fork's own extension of
`compareresults.pl`.** The parser's comment says group-2 final figures "was
previously not collected at all, so a fault confined to the final combination
(for instance **dropping the n x H_bitstring term**, or failing to fold in
`H_original`) left every collected value unchanged and the comparison passed."
The collection was duly added. **The references were not regenerated.**

Consequence, measured:

- `H_bitstring Per Symbol` is emitted on **6 of 11** files (the multi-bit ones)
  and appears in **0 of 11** references.
- `compareresults.pl:53-55` prints extra keys and **never touches
  `$retstatus`**:
  ```perl
  foreach my $newKey (keys %$newResults) {
     print "$ARGV[0]: Found extra data item: $newKey -> $newResults->{$newKey}\n";
  }
  ```
  A key present in new output and absent from the reference is **announced and
  not enforced.** (The reverse — a key missing from new output — *is* enforced,
  `$retstatus = 1`.)
- So that value is compared on **zero** files. On 4 of the 6 it coincides with
  `Assessed min entropy`, which *is* compared, so it is incidentally covered. On
  **`normal` (4.1000957831102802 vs 4.1000957831103086)** and **`truerand_8bit`
  (7.2338614551796505 vs 7.233861455178495)** it differs from every compared
  value and is **genuinely unchecked**.

**And it is the worst possible key to have missed.** `H_bitstring Per Symbol` is
exactly `n × H_bitstring` — verified: `0.032217608875810141 × 8 ==
0.25774087100648113`, bit-identical to the emitted value. **The one group-2 key
with no reference to compare against is the very term the comment names as the
motivating fault.** A fault confined to that output path would print "Found extra
data item" and pass.

`H_original` is **not** affected: references use the `H_original:` colon form, the
parser's second regex collects it, and it is compared (delta 6e-17, far under the
1e-10 epsilon). So the gap is one key wide, not general.

**Direction: PERMISSIVE.** An unenforced extra key means *any* newly added output
field is unchecked until references are regenerated, and the harness reports PASS
while printing the evidence. **This is `SHAPE-03` in its second direction** —
`C08` found the comparison blind to an empty reference (nothing examined reads as
success); this is the same loop blind to additions on the other side.

**NOT FIXED in this pass**, following the dead-guard sweep's precedent: recorded,
not repaired. The fix is two separable things — set `$retstatus` on an extra key
(or classify expected additions explicitly), and regenerate the eleven references
against a build whose provenance is recorded (`XR-04`). Regenerating pinned
reference data is not a change to make unprompted.

**What the challenge was right about:** the substance of my earlier statement held
(the deltas are the documented ones and predate my work), but "pre-existing and
known" rested on a filename match I had myself shown to be unbounded, and
interrogating it surfaced a real third defect that the label would have buried.

---

## OC-21 — the key-set asymmetry fixed, and the missing reference DERIVED rather than regenerated

State read: `master @ 67177d2` (== `origin/master`). Binaries built from that
tree with `cpp/Makefile`'s own flags, `NDEBUG` absent. selftest invoked as
`./selftest` (no flags); `compareresults.pl` compared directly for the
controlled cases.

`OC-20` found two separable defects. **Only one has a safe repair, and they are
fixed by different means.**

### Defect 1 — the comparison was total in one direction only. FIXED.

`compareresults.pl` iterated the **reference** key set, so a key the output
produced and no reference contained was printed and ignored. Now an extra key
sets `$retstatus = 1`:

```perl
foreach my $newKey (keys %$newResults) {
   print "$ARGV[0]: No reference value for $newKey (output has it, reference does not): ...";
   $retstatus = 1;
}
```

**Shown failing both ways**, on four controlled file pairs (the old script kept
beside the new one):

| case | before | after |
|---|---|---|
| identical key sets, equal values | exit 0 | **exit 0** (no false positive) |
| **extra key in output** | **exit 0 — the defect** | **exit 1** |
| missing key in output | exit 1 | **exit 1** (unchanged) |
| both at once | exit 1 | **exit 1** |

Messages distinguish the two directions: *"No reference value for X (output has
it, reference does not)"* versus the pre-existing *"No corresponding value for
X"*.

### What that made fail, recorded before it was resolved

Enforcement on, references **not yet** touched — the loud failure, exactly as
predicted:

```
biased-random-bytes  exit=1  No reference value for H_bitstring Per Symbol
normal               exit=1  No reference value for H_bitstring Per Symbol
rand4_short          exit=1  No reference value for H_bitstring Per Symbol
rand8_short          exit=1  No reference value for H_bitstring Per Symbol
truerand_4bit        exit=1  No reference value for H_bitstring Per Symbol
truerand_8bit        exit=1  No reference value for H_bitstring Per Symbol
  -> 6 of 6 failed on the unreferenced key
```

**That is the correct report.** The comparison had been incomplete on those six
files since the collection was added and nothing said so. It was not suppressed.

### Defect 2 — the missing reference. DERIVED, not regenerated.

**Regenerating the eleven references from the current tools was rejected.** These
tools carry nine confirmed permissive defects; references regenerated from them
would record what this build produces rather than what is correct, and selftest
would then verify the tools against themselves. **A reference derived from its
subject cannot detect its subject changing.**

**First: is the identity by construction, or did it hold on the one file I
checked?** Settled from source, not from the coincidence — **two call sites, both
unconditional products:**

```c
non_iid_main.cpp:600   printf("H_bitstring Per Symbol = %.17g\n", H_bitstring * data.word_size);
iid_main.cpp:421       printf("H_bitstring Per Symbol = %.17g\n", H_bitstring * data.word_size);
```

**By construction.** And the emission guard is
`if ((data.alph_size > 2) || !initial_entropy)`, which is why exactly the six
multi-bit files are affected and the five 1-bit files emit neither `H_bitstring`
nor this key — so their references correctly lack it and the enforcement does not
fire on them.

**Both inputs already exist in the references and neither came from the current
build:**

- `H_bitstring = <v>` — already a reference line, already compared.
- `n` — recorded in each reference's own header: *"Loaded 1000000 samples of 256
  distinct **8-bit-wide** symbols"*.

And `git log -- cpp/selftest/refdata/` shows these files were last written by
**upstream** commits (`6950b6d`, `951f854`, `7f51b1c`), not by this fork. So the
expectation is pinned independently of the build it checks. The principle, in
full: **a reference must be fixed by something other than the artefact it is
used to judge, or agreement between them is circular and carries no
information.** (Cited as `RULE 12`, a rule number with **no definition in this
repository**, and ascribed a different principle at each of its three citation
sites; see `OC-68`.)

**Derived values, all six, computed from reference data only:**

| file | n | reference `H_bitstring` | derived `n × H_bitstring` | vs this build's output |
|---|---:|---|---|---|
| biased-random-bytes | 8 | 0.032217608875810141 | **0.25774087100648113** | identical |
| normal | 8 | 0.51251197288878858 | **4.1000957831103086** | δ 6.93e-15 |
| rand4_short | 4 | 0.80387206696918412 | **3.2154882678767365** | identical |
| rand8_short | 8 | 0.73261171806065617 | **5.8608937444852494** | identical |
| truerand_4bit | 4 | 0.90062659214175955 | **3.6025063685670382** | identical |
| truerand_8bit | 8 | 0.90423268189731187 | **7.233861455178495** | δ 1.6e-13 |

**A correction to my own first check.** I initially compared derived against
emitted as **exact strings** and called `normal` and `truerand_8bit`
mismatches. That is not the tool's criterion: `compareresults.pl` compares
numerically with `epsilon = 1e-10` on `min(absolute, relative)` delta. Under the
actual criterion **all six pass**, worst delta **1.6e-13**, a **626× margin**.
The two non-identical cases arise because those references' `H_bitstring`
already differs from this build's by a sub-epsilon amount (3.6e-15 and 1.4e-13)
that the comparison tolerates by design; multiplying by n = 8 scales it by 8 and
it stays four orders under epsilon. Four of the six are **bit-identical**,
because n ∈ {4, 8} are powers of two, so the product only changes the binary
exponent and cannot round.

**Marked as derived, in the reference files themselves**, so a later reader is
not misled into thinking these were captured:

```
# The next line was DERIVED, not captured from a run -- see
# ... OC-21.  non_iid_main.cpp:600 emits it as H_bitstring * data.word_size, so
# the expected value is computed from the H_bitstring value and the 8-bit-wide
# symbol width recorded ABOVE IN THIS FILE. Both predate the current tools ...
# It was NOT regenerated from the current binaries: those carry known permissive
# defects, and a reference produced by its subject cannot detect its subject
# changing.
H_bitstring Per Symbol = 0.25774087100648113
```

Verified that the comment lines are **not** parsed as keys: replicating
`resultsHash`'s filter and both value regexes collects 103 keys from
`biased-random-bytes.res`, **none** from a comment line, and
`H_bitstring Per Symbol` **is** among them.

**The other ten keys were not touched.** Only the one key with a safe,
independently-derivable expectation was filled in.

### Result

`./selftest` at this tree:

```
selftest: FAIL (2 of 11 files): biased-random-bytes.bin ringOsc-nist.bin
```

- **Unreferenced keys: 0.** The previously-unchecked `n × H_bitstring` term is
  now compared on all six files and passes.
- **No new failures.** The only reported differences are the **7** and **1**
  documented upstream #155 predictor deltas (`OC-20` possibility 2), unchanged.

**The guard needs no separate regression: selftest is the guard.** An output key
without a reference now fails it directly, and `OC-20`'s defect could not recur
silently.

### Still open, deliberately

The other ten keys' references remain upstream-captured and are **not** verified
against an independent derivation — they cannot be, since nothing derives a
predictor estimate from other reference data. That is the honest residual: this
fixes the *key-set completeness* defect and the *one* value that arithmetic could
pin. **It does not make the reference corpus trustworthy**, and the corpus still
must not be regenerated from these tools while they carry known permissive
defects.

## OC-22 — C22's bound: measured, and shown to be set by the arithmetic. The floor expression written out.

`REPAIR-STRATEGY.md` carried `C22` as "Class 2, bound NOT YET MEASURED" — the
one Class 2 entry without a number, and the hole in the floor-by-subtraction
route. `OC-12` had already shown the remainder of the cluster conservative *at
the extremes tested*; what it had not done was state a ceiling on the
**permissive** side and say whether that ceiling comes from the arithmetic or
from the data. This check does both, for all three parts of the cluster. Harness:
`reproducers/c22_bound.cpp` calls the production `calc_p_local`,
`prediction_estimate_function`, `predictionEstimate` and `com_exp` directly.
Oracle: `oracles/p_local_exact.py`, 50-digit `mpmath`, written from the
standard's §6.3.7 formula and **not** from the tool's code. Log:
`logs/c22/oc22-oracle.log`.

**The oracle is pinned independently of the tool.** The standard's P_local
equation is Feller's run-probability approximation; exponentiating the oracle's
`f` and comparing against an exact transfer-matrix computation of
*P(no run of r in N trials)* agrees to 1.5e-16 relative at four (p, r, N) points.
So the oracle computes what the standard says, checked against first principles,
not against the tool.

### Part 1 — `P_local`'s bisection quantisation (`predictors-5`)

**Mechanism.** The objective `f(p)` carries the term `(N+1)·log(x)` where `x` is
the fixed point of `x = 1 + q·p^r·x^(r+1)`, computed in `long double` which on
this build is 64-bit (`sizeof(long double) == 8`, `REPRO-01`). `x` lies in
`[1, 2)`, so it is representable only in steps of `2^-52`, and rounding it to
nearest leaves an error of at most `2^-53`; multiplied by `(N+1)` that is the
quantisation step of `f`. The bisection returns `hbound`, the side on which
*computed* `f ≤ ln 0.99`; when the computed `f` is below the exact `f` by up to
that step, `hbound` can sit **below** the exact root by `ε_f / |f'(p*)|`, and
`entEst = −log2(curMax)` is then too **high** by `ε_f / (|f'(p*)|·p*·ln 2)`.
That is the permissive path. The pre-guard
`prediction_estimate_function(curMax) > log(0.99)` can skip the search by the
same error, bounded by the same quantity.

**Measured, 592 near-root points** (`p* × (1 ± 10^-3 … 10^-12)`, N from 2 to
2^40, r from 2 to 256): the tool's `f` differs from the exact `f` by at most
**0.4991 × (N+1) × 2^-52**, i.e. the predicted half-ULP of `x` amplified by
`(N+1)`, at every N. The per-N maxima sit at 0.33–0.50 of that unit with no
trend. Far from the root the tool's `f` can be badly wrong — the 66-step
recurrence cap (`predictors-7`) lives there — but the bisection consumes only
the sign of `f − ln 0.99`, and at **0 of 238** far-from-root points is the sign
wrong.

**Measured, 634 sweep points** (`calc_p_local` versus the exact root, 18 values
of N from 2 to 2^53, 14 values of r from 2 to 1024, four `ldomain` values):

| N | worst permissive inflation (bit) | at r | ceiling `c·(N+1)·2^-52 / (|f'(p*)| p* ln 2)` |
|---:|---:|---:|---:|
| 1 000 | +4.1e-12 | 3 | 5.3e-12 |
| 100 000 | +2.8e-10 | 2 | 8.0e-10 |
| 1 000 000 | +1.1e-09 | 5 | 3.2e-09 |
| 7 999 937 (the harvested bitstring N) | +8.1e-09 | 10 | 1.3e-08 |
| 8 000 000 | **+4.0e-08** | 2 | **6.4e-08** |
| 1e9 | +3.0e-06 | 2 | 8.0e-06 |
| 2^53 | −3.3 (conservative) | 2 | — |

The realised inflation is at most **0.928** of the per-point ceiling across all
634 points. It is linear in N, as the mechanism says it must be.

**Is it bounded by the arithmetic, or by the data?** Both inputs to the ceiling
are pinned. `c = 0.4991` is the half-ULP of `x` — arithmetic. The denominator
`|f'(p*)|·p*` has a **minimum over the sweep of 1.979e-02 at r = 2, N = 5**, and
the analytic form `0.01005·(r − p/q)` explains it: it is smallest at the smallest
admissible `r`, and `r = 1` cannot reach `P_local` at all (a run length of 0 means
`C = 0`, which takes the `1 − 0.01^(1/N)` branch and fails the guard). So the
sensitivity is bounded below over every `(r, p*)` the search can be asked for.
What remains is `N`, the number of predictions — **a property of the
procedure (sample count × word size), not of the stream**. The ceiling is
therefore a function of a configured quantity, which is Class 2:

```
B_Plocal(N) = c · K · (N+1)  with  c = 0.4991,  K = 2^-52 / min(|f'(p*)| p* ln 2) = 1.619e-14 bit
            = 8.08e-15 · (N+1) bit         → 6.5e-08 bit at N = 8e6;  8.1e-09 bit at N = 1e6
```

It is **per-estimator** (each of the four predictors, each path), and because
the final figure is a minimum over estimators it bounds the final figure too.
Architecture: this is the 64-bit-`long double` value; on x86-64's 80-bit
`long double` the step is 2048× smaller, so the stated bound is valid on both.

The finder's "+1.6e-11 bit" (`CLUSTERS.md`) is consistent with this at
N ≈ 10^6 on a 64-bit `long double` and was presumably a single instance; the
ceiling above supersedes it.

### Part 2 — `P_global'` dividing by `N − 1` on the approach to `N == 1` (`predictors-9`)

Production `predictionEstimate` versus the standard's formula with the exact
quantile and with the literal `2.576`, every `C ∈ {0, 1, 2, N/2, N−1, N}` for
`N ∈ {1, 2, 3, 4, 5, 8, 16, 64, 1000, 10^6, 8·10^6}` and `k ∈ {2, 256}` (72
rows in the log):

- **tool − formula(exact z)**: between −5.9e-17 and +8.4e-15 at every row —
  rounding, nothing else. The code *is* the formula.
- **`N == 1`**: `−0` for every `C ≥ 1` (the `sqrt(0/0)`/`sqrt(x/0)` is absorbed,
  `OC-12`), and `0.0145` bit for `C == 0` from the documented branch. Zero
  entropy is the conservative end; there is **no inflation to bound**.
- **`N = 2 … 5`**: the `min(1, …)` clamp fires for every `C ≥ 2`, giving `−0`;
  the only non-clamped rows are `C = 1`, and those are where the literal-text
  delta sits.
- **tool − formula(literal 2.576)**: at most **+6.8867e-05 bit**, always at
  `C = 1`, independent of N. That is the `ZALPHA` item, Part 3.

**Conclusion: the `N − 1` divisor contributes 0 to the permissive bound at
every N ≥ 1.** `B_Pglobal' = 0`.

### Part 3 — `ZALPHA` versus the literal `2.576`, on every estimator that uses it

`OC-8` measured this on real values for three predictors and called it "not a
defect" (`F07`: `2.576` is the standard's rounding of the quantile the tool
uses). That disposition stands. But `ZALPHA` is in **eight** of the ten
estimators (`most_common.h`, `lrs_test.h` ×4, `collision_test.h`,
`compression_test.h`, `utils.h`), not only the predictors, and a floor that is
defensible against the *literal* text needs the ceiling, so it is measured here
and carried as a **separately labelled term** that a reader who accepts `F07`
sets to zero.

`Δz = 2.576 − 2.5758293035489008 = 1.70696e-04`.

**Closed-form estimators** — MCV, t-Tuple, LRS, and the predictors' `P_global'`
all use `p_u = min(1, p̂ + z·sqrt(p̂(1−p̂)/(n−1)))`. Since the count behind `p̂`
is at least 1, `p̂ ≥ 1/n`, which gives `sqrt(p̂(1−p̂)/(n−1)) ≤ p̂` exactly, and
hence

```
ΔH ≤ Δz / ((1 + z_tool)·ln 2) = 6.887e-05 bit     per estimator, any n, any p̂
```

attained at count = 1 (the grid in Part 2 hits 6.8867e-05 at `C = 1`). On the
harvested run the instances are +8.7e-08 (bitstring) and +3.7e-06 to +3.8e-06
(literal, per symbol) — the table in the log lists all fourteen.

**Collision** (bitstring only). `X' = X̄ − z·s/√v`, `p = ½ + sqrt(1.25 − X'/2)`,
capped at `H = 1` when `X' ≥ 2.5`. The sensitivity `dH/dX'` is **not** bounded —
it diverges as `X' → 2.5` — but the inflation is, because `H` is capped: scanning
every `X'` on the approach to the cap gives `max ΔH = (2/ln 2)·sqrt(ΔX'/2)` with
`ΔX' ≤ Δz·½/√(n/3)` (`t ∈ {2,3}` bounds `s ≤ ½`, and `v ≥ n/3`):

| n | ΔX' ≤ | ceiling (scan) | closed form | instance on the real run |
|---:|---:|---:|---:|---:|
| 1e6 | 1.48e-07 | **7.84e-04 bit** | 7.84e-04 | — |
| 8e6 | 5.23e-08 | **4.66e-04 bit** | 4.66e-04 | +2.5e-06 bit |

**Compression** (bitstring only). The solved quantity is `com_exp(p) = X'` with
`com_exp(p) = G(p) + 63·G((1−p)/63)`, which is **stationary at p = 1/64** (the
two `G'` terms cancel at the uniform point), so the sensitivity is quadratic on
the approach to the cap exactly as for collision, and a linearised bound would
be wrong. Measured by scanning `X'` from the cap `G(1/64)` downward through the
**production** solve (`comp` with `σ = 0`), with
`ΔX' ≤ Δz·σ_max/√v`, `σ_max = 0.5907·log2(num_blocks)/2` (Popoviciu, the
per-block values lie in `[0, log2 num_blocks]`):

| n | num_blocks | ΔX' ≤ | ceiling (scan) | where | instance on the real run |
|---:|---:|---:|---:|---|---:|
| 1e6 | 166 666 | 2.15e-06 | **3.36e-03 bit** | 1.0 ΔX' below the cap | — |
| 8e6 | 1 333 333 | 8.89e-07 | **2.16e-03 bit** | 1.0 ΔX' below the cap | +4.0e-06 bit |

The ceiling is reached only by a source whose compression statistic lands within
one `ΔX'` of the uniform expectation — a figure the estimator would print as
≈ 1.0 bit — whereas the harvested ideal-uniform run sits at 0.926 with an
instance of 4.0e-06. **It is a ceiling set by `Δz`, the cap, and `n`; nothing in
it is a statistic of the stream.** So `C22` does **not** move to Class 4.

**The final-figure `ZALPHA` term** is the maximum over estimators of these
per-estimator ceilings (a minimum is 1-Lipschitz in each argument). The
literal-path ceilings are per *symbol* and divide by the word size when the
per-bit figure is formed, so the bitstring compression term dominates:

```
B_z(n) = 3.36e-03 bit at n = 1e6 bits;  2.16e-03 bit at n = 8e6 bits;   0 under F07's reading
```

### What this settles

| part | direction | ceiling | set by | class |
|---|---|---|---|---|
| `P_local` quantisation | permissive, linear in N | `8.08e-15·(N+1)` bit; **6.5e-08 at N = 8e6** | half-ULP of `x` × (N+1), minimum sensitivity at r = 2 | 2 |
| `P_global'` at/near `N == 1` | conservative | **0** | `−0` at N = 1; clamp for N ≤ 5 | 2 |
| `ZALPHA` vs literal `2.576` | permissive | **3.36e-03 at n = 1e6, 2.16e-03 at n = 8e6** (compression binds) | `Δz`, the cap, `n` | 2, and 0 under `F07` |

All three are per-estimator ceilings that bound the final figure. The
floor-by-subtraction expression is now written out in `REPAIR-STRATEGY.md`
("The floor, as arithmetic").

**Verified**: the oracle against first principles; `c = 0.4991`; the sign check;
634 sweep points under the ceiling; `P_global'` at 72 rows; the closed-form
`ZALPHA` bound and its attainment at `C = 1`; collision and compression scans
through production code, with the production solve reproducing the harvested
run's printed `p` and `H` to the last digit. **Not verified**: the x86-64
`long double` value of `c` (argued from the format, not measured); any claim
about a *source* — every input here is synthetic, which is the licensed use for
a claim about an instrument.

## OC-23 — the outside-battery corpus could not count; now it is pinned, counted per family, and shown failing five ways

`OC-22`'s merge-rule sweep (`BUG-REPAIR-GUIDE.md`) listed the outside-battery
corpus as "digest mismatch caught, absent stream not". That is a detectable case
with half a detector, and it sat directly under published numbers: the
**0/25** false-positive figure behind the 5.731 σ and 30× thresholds
(`OC-17`), **B** at 8538.7× / 59.938 Hz, **E** at 40.21 σ / lag 5000, and the
Compression-binding figure 0.8546 ± 0.0092 on the five Mersenne Twister streams
that `OC-16`'s headroom table rests on. The expected set lived only in the
regression script's own lists, so deleting a stream from the list produced a
passing run whose "0 / 25" had quietly become 0 / 24. The families are not
interchangeable either: 5 MT and 20 SHA-256 counter-mode streams exercise
different generators by design, so losing one of the five is a larger loss of
coverage than 1/25.

**Fixed the way `compareresults.pl` was fixed in `OC-21`** — key sets required
equal, both directions. `cpp/selftest/outside-battery-corpus.txt` now pins
every stream's family, identity and digest (31 streams), and
`regression-outside-battery.sh` requires:

- per-**family** counts equal to separate expectations — mt 5, sha 20,
  defect 5, blindspot 1 — so a family cannot be hollowed out while a total holds;
- the three named inputs behind pinned figures (`B_osc5000`, `E_weaklag5000`,
  `G_xor13_02`) present by name;
- every listed stream regenerable from its seed and matching its digest;
- **no unlisted stream present** in the corpus directory;
- all of it **in every mode**: fast mode only *runs* the tool on a subset, the
  corpus behind every figure is verified whole (adds ≈1 min of generation).

Failing any of it is exit 1 — a regression, not "could not run".

**Shown failing, five ways** (`logs/obc/mutation-*.log`; baseline PASS in
`logs/obc/baseline-fast.log`):

| mutation | what the old script did | now |
|---|---|---|
| one stream removed from the manifest (`mt02`) | **passed** — this is the case that could not be counted | FAIL: `family mt short or long: 4 listed, 5 required` |
| one stream added to the manifest (`sha20`, any digest) | passed | FAIL: `family sha short or long: 21 listed, 20 required` |
| one unlisted file added to the corpus directory | passed | FAIL: `unlisted stream present in corpus: zz_extra` |
| one digest changed (`mt02`, last hex digit) | failed | FAIL: `DIGEST MISMATCH mt02` |
| a listed name the generator cannot build (`F_xor30` → `H_nonexistent`) | exit 2, could-not-run | FAIL, three problems: generator refuses, `F_xor30` now unlisted-present, `H_nonexistent` absent |

A first attempt at the digest mutation edited the wrong line and the run
passed; that was my sed, not the check, and the corrected mutation is the one
in the table. Recorded because a mutation that does not mutate is the same
vacuous-guard shape this project keeps finding.

**The other cited figures.** B and E are named inputs in the same corpus and now
carry their digests and family in the manifest; the Compression-binding figure
is measured on exactly the five `mt` streams, which is why that family's count
is a separate expectation. No cited figure in `OC-15`–`OC-19` rests on a corpus
the harness cannot now count. The `OC-21` reference corpus is counted by
`fixture-manifest.txt`; the `C07` fixtures and canary input are single
seed-generated files checked by digest.

## OC-24 — the `long double` argument named the wrong dimension: three formats, not two platforms

The canary and `XR-08` said the unrepaired signatures need `W > 1022` "on a
64-bit `long double` (arm64)" and `W > 16382` "on an 80-bit `long double`
(x86-64)", and treated arm64 as the other case. Printed on this machine
(Apple arm64, `logs/merge/tag-walk-2026-10-18.log` host line):

```
sizeof(long double)=8  LDBL_MANT_DIG=53  LDBL_MIN_EXP=-1021  LDBL_MIN=2.22507e-308  LDBL_TRUE_MIN=4.94066e-324
```

So "arm64" here means **Apple's arm64 ABI, where `long double` is IEEE
double** (`REPRO-01`). It is not binary128: that is the *Linux* aarch64 ABI. The
three formats a build of this tool can land on are:

| format | where | significand | emin | `LDBL_MIN` | subnormal floor |
|---|---|---:|---:|---|---|
| IEEE double | Apple arm64 (**measured here**) | 53 | −1021 | 2.2e-308 | 2^-1074 |
| x87 extended | x86-64 Linux, MSYS2/MinGW | 64 | −16382 | 3.36e-4932 | 2^-16445 |
| binary128 | Linux aarch64 | 113 | −16382 | 3.36e-4932 | 2^-16494 |

**Correction.** In the exponent dimension x87 extended and binary128 are
identical (15-bit exponent, emin −16382); the odd one out is the platform the
measurements were taken on, which has the *narrowest* range. So the earlier
framing had it backwards twice: "16382" is not an x86-64 number, it is the
number for both wide formats; and the measurement here does **not** settle the
exponent question for them, because this format underflows 2^-1021 earlier,
not later. What transfers is the chain's arithmetic, checked value by value
(`scratchpad chain probe`, numbers below are this machine's; the wide-format
numbers are computed from the format, not observed):

**Unrepaired signatures, W = 20000, `p_col ≈ 0.5`.** `p_colPower = powl(p_col, W)`
is 2^-20000, which is below the **subnormal floor of all three formats**
(2^-1074, 2^-16445, 2^-16494), so `powl` returns +0 — measured here, with
`FE_UNDERFLOW` raised — and every later step is identical on every format:
asserts live, `assert(p_colPower >= LDBL_MIN)` is false → abort 134; `-DNDEBUG`,
`N·log1pl(−0) = −0`, and `logl(0.999) = −0.0010005 ≥ −0` is false → the LRS
test reports failure and a figure is published. The subnormal floors differ by
49 binary orders between x87 and binary128, but 2^-20000 is 3500 orders below
the nearer one; a subnormal `p_colPower` would need W between 16382 and 16445
on x87 (16494 on binary128), and even then the signatures hold (a subnormal
fails the `≥ LDBL_MIN` assert too, and `N·log1pl(−tiny)` is still above
`logl(0.999)`). **Where the formats do diverge is W between 1022 and 16382**:
this machine aborts there and the wide formats do not — which is exactly why
the canary input is W = 20000 and not the W = 2000 used elsewhere.

**Repaired signature.** `logCollisionPower = W·logl(p_col) = −13862.9`,
representable on every format. Against `logl(LDBL_MIN)` — **−708.4 here,
−11355.1 on both wide formats** — it is below on all, so the `else` branch runs
on all; `logExpected = logl(N) + logCollisionPower = −13849.1`, below every
`logl(LDBL_MIN)`, so `probabilityAtLeastOne = 0` on all; the decision
`logCollisionPower ≥ logDecisionThreshold = −20.72` is false on all, by a
margin of **13842 log-units**. The `if`/`else` branch choice differs between
formats only for W in 1022..16382, and both branches compute the same
probability; the decision itself flips only at W ≤ 29.9. **This paragraph is an
argument from reading `lrs_test.h:679-741`, confirmed numerically on one
format; it is not an observation on the wide formats.**

**The three dimensions the question asked about:**

- *Significand precision* (53 / 64 / 113 bits). A signature could diverge only
  at a comparison near a rounding boundary. The nearest boundary in either
  chain is thousands of log-units away (−13863 vs −11355; −13849 vs −11355;
  −13863 vs −20.7); 53-bit rounding moves these by parts in 10^16. **Cannot
  plausibly matter.**
- *Subnormal floor* (2^-1074 / 2^-16445 / 2^-16494). The one quantity that
  underflows, 2^-20000, is below all three; and the signatures are insensitive
  to subnormal-versus-zero anyway (above). **Cannot matter at W = 20000.**
- *Double intermediates.* The symbol frequencies `p[i]` are `vector<double>`
  (`lrs_test.h:628`); `p_col` is accumulated from them in `long double` and is
  ≈ 0.5, nowhere near any underflow point; `W` and `N` are integers; every other
  intermediate in both chains is `long double`. **No double intermediate sits
  on an underflow path.**

**What the x86-64 item shrinks to.** Not "re-run everything": build once on an
x86-64 host and run the canary once against each tree. The only things the
argument above does not cover are the toolchain itself and `powl`'s underflow
behaviour returning +0 on that libm, which IEEE 754 and C11 Annex F require
and which was observed here on one libm. The same single run covers Linux
aarch64 if that platform is ever used. Until then the register carries this as
**a bounded argument, measured on one format**, not as an open platform risk.
The canary header, `XR-08` and `BUILDING.md` are corrected to say this.

## OC-25 — the tag built end to end from a fresh clone, following only what is at the tag

`OC-22`'s push check verified that `unrepaired-reference-2026-10-15` resolves
from a throwaway clone and then *argued* that the build steps work from either
place. That path had never been walked. Walked 2026-10-18,
`logs/merge/tag-walk-2026-10-18.log` — every command is in the log as run:

```
git clone --quiet --branch unrepaired-reference-2026-10-15 --depth 1 https://github.com/systemslibrarian/SP800-90B_EntropyAssessment.git <dir>
git describe --tags                      -> unrepaired-reference-2026-10-15
brew list --versions libomp libdivsufsort jsoncpp openssl@3
cd cpp && make non_iid iid restart       -> exit 0, three executables
cd selftest && ./selftest                -> exit 1: FAIL (2 of 11 files): biased-random-bytes.bin ringOsc-nist.bin
./pin-check.sh --prove-nonvacuous        -> exit 0
shasum -a 256 ea_iid ea_non_iid ea_restart
<master>/tools/build-provenance-canary.sh cpp/ea_iid          -> TREE UNREPAIRED, BUILD ASSERTS-LIVE, exit 0
make -B CXX="clang++ -DNDEBUG" iid; canary again              -> TREE UNREPAIRED, BUILD NDEBUG, exit 0
```

Nothing from master was used in the build; master's canary was used only to
classify the result. Binaries: `ea_iid 5bece408…`, `ea_non_iid 47796ac9…`,
`ea_restart d88e9d0e…`. **Verdict: the reference is buildable from the tag
alone, and the current canary classifies both of its builds as UNREPAIRED
with the build sub-result.** Three things about the instructions *at the tag*,
which are immutable there and corrected on master's `BUILDING.md`:

1. The macOS quick-start block says `make non_iid` only. `ea_iid`, the canary's
   subject, comes from the "Running the checks" block (`make non_iid iid
   restart`), which is what was run.
2. The quick-start's `./selftest` exits 1 on macOS arm64 for the two documented
   upstream #155 files. That is explained elsewhere in the same document and
   excused by `run-all-checks.sh --allow-known-platform-deltas`, but a reader
   following the block sees FAIL first. Not a build failure; `pin-check`
   passes.
3. The dependency line names four Homebrew packages; the walk's single
   `brew list --versions` printed three (`jsoncpp 1.9.8`, `libdivsufsort
   2.0.1`, `libomp 23.1.2`) and omitted `openssl@3`, though the link against it
   succeeded. A direct query shows `openssl@3 3.6.4` installed. Recorded as
   seen rather than smoothed over; the versions match the tag's own table.

## OC-26 — C23 applied as a recomputed decision: the script exists, and the flip is shown on a named matrix

> **SUPERSEDED — 2026-10-19, see `OC-30`.** The script computed the printed
> binomial decision and called it exact. Applying it as written would reject
> sound restart data. `oracles/restart_decision_exact.py` has been corrected to
> decide on the exact multinomial maximum and to report the printed-formula
> value beside it; the X_max 24 case at H_I 7 is **accepted** by the corrected
> statistic (cutoff 27), not rejected.

`C23`'s treatment was never a subtraction (`REPAIR-STRATEGY.md`, "The floor,
as arithmetic"): the tool's simulated restart cutoff sits above the exact
§3.1.4.3 binomial cutoff, so the correct response is to **recompute the
accept/reject decision** against the exact cutoff and treat the tool's verdict
as advisory. `oracles/restart_decision_exact.py` does that: it reads an
`ea_restart -v` log (or `--manual H_I X_max`), names every input the decision
depends on, and prints the exact decision beside the tool's.

**Inputs the decision depends on** — `H_I`, the initial estimate passed on the
command line (`p = 2^-H_I`); `X_max`, the largest symbol count in any row or
column of the 1000×1000 matrix, printed by the tool; `α = 1 − 0.99^(1/2000)`,
the tool's own Šidák value, which gives the same cutoff as the standard's
printed 0.000005 at every `H_I` in 1..8 (`OC-7`); and `N = 1000`. The cutoff
comes from `oracles/restart_cutoff_exact.py`, pinned against the standard's
closed form, not the tool.

**Demonstrated on three forced-count matrices** (`generators/c23_forced_count.py`,
column 17 forced to exactly X zeros; `H_I = 7`; `logs/c23/`):

| matrix (digest) | `X_max` | tool `X_cutoff` | tool said | exact cutoff | exact decision | |
|---|---:|---:|---|---:|---|---|
| X = 20 | 20 | 27 | Passed | 23 | **ACCEPT** | agree |
| X = 24 (`8da94167…`) | 24 | 27 | **Passed** | 23 | **REJECT**, P(X ≥ 24 \| H_I = 7) = 2.2e-06 < α | **the tool accepts a matrix the standard rejects** |
| X = 28 (`b1674405…`) | 28 | 27 | Failed | 23 | REJECT | agree |

The middle row is the `C23` defect as a decision rather than as a 0.341-bit
slack figure: with the exact cutoff the restart dataset is **not accepted and
no figure is awarded**, which is what the standard requires. (The X = 24 run
then fails the separate validation test, `min(H_r, H_c) < H_I/2`, for reasons
of its own — the forced column makes the matrix non-uniform — but that is the
second gate; the sanity check is the one `C23` governs.)

**What this does not do.** There is no real restart dataset to decide: the
physical items are NOT RUN and the device arrives in January 2027. When it
does, the restart run's `-v` log goes through this script, and the figure is
awarded only if the **exact** decision is ACCEPT. Synthetic matrices establish
that the instrument's decision differs from the standard's and that the script
computes the standard's; they say nothing about any source.

## OC-23 addendum — where the counts live, the coordinated edit, and the citation link

**Where the expected 5 is read from.** Not from the manifest. The manifest's
header *states* the counts as prose, but the regression reads them from its
own line `EXPECT_MT=5; EXPECT_SHA=20; EXPECT_DEFECT=5; EXPECT_BLINDSPOT=1`
(`regression-outside-battery.sh:122`). So the mt02 mutation failed because the
script's expectation disagreed with the manifest's count, not because the
manifest noticed its own edit.

**The coordinated edit, run** (`logs/obc/mutation-coordinated-manifest.log`):
mt02's line removed *and* the header's "mt 5" changed to "mt 4" in the same
file, the way a person tidying up would. **FAIL**: `family mt short or long: 4
listed, 5 required`. The expectation and the set it governs do not share a
file.

**The edit one level up, also run** — manifest as above *plus* the script's
`EXPECT_MT=5` changed to `4` (`logs/obc/mutation-coordinated-manifest-and-script.log`).
Before today that passed. It now **fails with six disagreements**, because the
counts are anchored in places a corpus-and-script edit does not reach, and the
regression checks every one of them before measuring anything:

| anchor | what it states | checked against |
|---|---|---|
| `tools/outside-battery-check.cpp:40-42` | "MEASURED on 25 independent clean streams … (5 Mersenne Twister, 20 SHA-256 counter mode)" | `EXPECT_MT + EXPECT_SHA`, `EXPECT_MT`, `EXPECT_SHA` |
| `generators/blindspot_streams.py` docstring | "CLEAN (25, …)", "mt00..mt04", "sha00..sha19" | the same three |
| `OC-17` | "Calibration: 25 independent clean streams", "**0/25** over 5.731" | the total |
| `OC-17` / this regression | 8538.7, 59.938, 40.21, 0.8546 | the figures this script pins must still be the ones the record cites |
| the generator | `B_osc5000`, `E_weaklag5000`, `G_xor13_` | the names behind the pinned figures must be names the generator defines |

**The citation link, closed.** A figure that names its input was, until today,
only as good as the document happening to agree with the manifest. Now a
document claiming "0/24" fails the regression
(`logs/obc/mutation-doc-count.log`: exactly one problem, `OC-17: 0/N false
positives … says 24, this script expects 25`). The chain is: document count ⇔
script expectation ⇔ manifest family count ⇔ files on disk ⇔ digests ⇔
generator names. Changing the corpus now requires touching the manifest, the
script, the tool header, the generator docstring and `OC-17` together — which
is the point: five deliberate edits in five files is a decision, one edit in
one file was an accident waiting to pass.

Two of my first extraction patterns took the wrong number from a match (256 from
"SHA-256", 731 from "5.731") and one looked for a literal `G_xor13_02` the
generator builds from a format string; those produced false failures on the
baseline, were fixed, and the baseline re-run passes
(`logs/obc/baseline-fast.log`). Recorded for the same reason as the sed in
`OC-23`: a check that fails for the wrong reason is as misleading as one that
passes for the wrong reason.

## OC-27 — C23's gap is not an off-by-one: the tool simulates a different statistic, systematically, at every H_I and every α

> **SUPERSEDED IN ITS DIRECTION — 2026-10-19, see `OC-30`.** The mechanism
> identified here is right and is the same one Hill/UL identified in 2018: the
> statistic is the maximum cell count of a multinomial, not one cell's binomial
> count. The direction is inverted. The defective side is the standard's printed
> formula; upstream's simulation compensates for it on purpose. The exact-model
> arithmetic in this entry is reused unchanged in `OC-30`.

`OC-26` showed one point: X_max 24 accepted by the tool and rejected by an exact
cutoff of 23 at H_I = 7. That point is now scoped, its mechanism named, and the
word "exact" anchored. `oracles/restart_cutoff_anchor.py`, `logs/c23/anchor.log`,
`logs/c23/sweep/` (the tool at H_I = 1 … 8 on this machine, one run each).

### Anchor first — is 23 the standard's number?

`restart_cutoff_exact.py` uses `mpmath`'s `binomial()`. Independently of it, and
of the tool: X ~ Binomial(1000, 2^-H_I) with the pmf built by the multiplicative
recurrence `f(j+1) = f(j)·(N−j)/(j+1)·p/q` from `f(0) = q^N`, in
**exact rational arithmetic** (`fractions.Fraction`; p is dyadic for integer
H_I, so no floating point exists anywhere in the computation) and in
80-digit `Decimal` for H_I = 7.5; cutoff = the largest x with
Pr[X ≥ x] ≥ α. **Agrees with `restart_cutoff_exact.py` at all nine H_I**
(570, 312, 173, 99, 58, 36, 23, 19, 15). "Exact" is now a cross-checked claim,
not a label.

### Mechanism — the lines

`restart_main.cpp`, `simulateCount()`:

```c
for (int j = 0; j < 1000; j++)
    counts[(int)floor(randomUnit(xoshiro256starstarState) / p)]++;   // k_eff cells, each at probability p
for (int j = 0; j < k_effective; j++)
    if (max_count < counts[j]) max_count = counts[j];               // the MAX over all cells
return max_count;
```

and `simulateBound()`: `k_effective = ceil(1.0 / p)`,
`returnIndex = floor((1 − α)·R) − 1`, `returnValue = results[returnIndex]`.

§3.1.4.3 defines the null as a **single** Binomial(1000, p) for the most
likely symbol and compares X_max against its tail. The tool instead simulates
the **maximum count over all k_eff = 2^H_I equiprobable symbols** in 1000 draws
and takes the (1 − α) order statistic of *that*. The maximum over k cells is
stochastically larger than any one cell's count, so its quantile sits above the
binomial's, and the tool accepts counts the standard rejects. It is not a strict
versus non-strict comparison, not a ceiling for a floor, and not a boundary
term in a tail sum: it is a different random variable. (The quantile index is a
0-based rank that leaves ≈ α·R = 25 simulated maxima above the cutoff, which
is the right convention for "counts equal to this value pass"; it contributes
at most ±1 of simulation noise.)

### Scope — the whole range, two α values, exact model against measurement

The anchor script also computes the tool's *intended* statistic exactly —
Pr[max over k_eff cells ≤ m] = 1000!·[x^1000] Π_j S_m(p_j x) by truncated
polynomial powering, 40 digits — so the mechanism can be separated from
simulation noise:

| H_I | k_eff | standard (single binomial) | tool's statistic, exact quantile | gap | tool measured today | OC-7's three draws |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 2 | 570 | 572 | +2 | 571 | 572, 572, 571 |
| 2 | 4 | 312 | 316 | +4 | 316 | 316, 316, 316 |
| 3 | 8 | 173 | 178 | +5 | 177 | 179, 178, 178 |
| 4 | 16 | 99 | 104 | +5 | 103 | 103, 104, 104 |
| 5 | 32 | 58 | 63 | +5 | 63 | 63, 63, 63 |
| 6 | 64 | 36 | 40 | +4 | 40 | 40, 40, 40 |
| 7 | 128 | 23 | 27 | +4 | 27 | 27, 27, 27 |
| 7.5 | 182 | 19 | 22 | +3 | 22 | 22, 23, 22 |
| 8 | 256 | 15 | 19 | +4 | 19 | 19, 19, 19 |

The exact quantile of the max-over-cells statistic reproduces every measured
tool cutoff to within ±1 — the simulation noise of a 5×10⁶-round order
statistic at a 5×10⁻⁶ tail. **The mechanism accounts for the whole gap.** It is
systematic across the usable range: +2 at H_I = 1 (two cells) rising to +5 and
settling at +4 as the per-cell probability shrinks; there is no boundary inside
the range where it appears or disappears.

At the standard's printed α = 0.000005 the table is identical (the Šidák and
Bonferroni values give the same cutoffs, as `OC-7` said). At an illustrative
α = 0.001 the gap moves to +3 … +7 — the disagreement is α-dependent in size
and present at every α, as a statistic mismatch must be and an off-by-one
would not be.

### Direction and standing

**Permissive, verified, systematic.** The tool accepts restart matrices with
X_max up to 2–5 counts above what §3.1.4.3 rejects, at every H_I. This is the
`C23` register entry with its mechanism named; the treatment stays as
`OC-26`: recompute the decision with the exact cutoff, never subtract. **The
"deliberate implementation choice" reading is now also mechanically precise**:
the tool's statistic is arguably the better-posed null for the quantity it
measures (the max over symbols *is* what X_max is), but it is not the
standard's test, and a figure claimed under SP 800-90B must pass the
standard's. Nothing here decides a real device: there is no restart dataset,
physical items stay NOT RUN. Measured on this machine; the mechanism and the
exact quantiles are arithmetic and transfer; the simulation noise is the
tool's and would be re-drawn anywhere.

## OC-28 — the five unknown-direction clusters: direction only

Direction decides whether a fix is owed; only permissive puts a figure at
risk. Each line says what fixes the direction and whether that is a
demonstration or an argument from reading code. Nothing here is a repair.

| cluster | direction | fixed by | demonstration or argument |
|---|---|---|---|
| **`C16`** permissive parsing | **PERMISSIVE on the restart gates**, given a mis-scaled `H_I` string; conservative on the *returned* value | Re-run today on master: `ea_restart -v <8-bit matrix> 8 1e-400` → `H_I: 0.000000`, `X_cutoff: 1000`, `Restart Sanity Check Passed`, `Validation Test Passed`, `min(H_r,H_c,H_I): 0.000000`, **exit 0** (`logs/c23/c16-HI-1e-400.log`). Both gates vacuous; the tool reports success. The returned minimum is 0, so a consumer using the tool's own output gets a conservative number; a consumer that keeps its own `H_I` and reads the exit status gets an accepted restart it should not have (`XR-03`). The other members (`atoi` width truncation, `-s` allocation, octal `n_in`) are all marked off the supported path by their finders. | **Demonstration** (today, master) |
| **`C14`** report contract | **PERMISSIVE on the status channel** | `OC-14`: three ways for a harness to read success where there is none — the stale `-o` file (`XR-01`), `exit 0` on a `--version`-named input, `exit 0` for a failed IID suite (`C03`, since closed by the merge) — against one way to read failure without a cause. No member changes a computed figure's value. | Demonstration (`OC-14`, by execution) |
| **`C18`** LLP64 overflow | **NEUTRAL on this host; UNKNOWN on LLP64** | `sizeof(long) = 8` printed on this build today, so no counter in the cluster can overflow here. On Windows/LLP64 (`long` = 32-bit) `n_choose_2`'s wrap sign depends on `L`, so the direction there is undecidable by reading. The Windows route is documented and NOT verified (`BUILDING.md`) and is not in use. | Demonstration for this host; argument for LLP64, which is out of scope until a Windows build exists |
| **`C20`** OpenMP races | **NEUTRAL** | `OC-13`: every input to the permutation verdict is written only inside the critical region, and the raced `test_status[]` is monotone and not an input to the verdict; the raced `completed` counter feeds only a progress percentage. | **Argument** (data-flow reading; ThreadSanitizer not run) |
| **`C21`** conditioning and permutation misc | **NEUTRAL on the supported path**; off-path members are misreport/crash in `ea_conditioning`, which is not built | `OC-13`: the `periodicity`/`covariance` over-read needs `n < p` and every supported path refuses such an input (short file and short `-l` subset both refused, measured). The `fesetround` member is off-path and measured ±1e-12 in both directions. | Demonstration for the on-path members; the off-path members stay off-path |

**Stop point.** `C16` is permissive, by demonstration, on the same gate `C23`
is permissive on, and the two compose: a lower `H_I` lowers the validation
threshold `H_I/2` *and* raises the sanity cutoff. **It is the next piece of
work.** `OC-11` already specified the regression — construct `H_I = 1e-400`,
assert the run is refused, and show the assertion failing against current
master, which today still accepts it with `exit 0` — and the four hardening
items. Not done here; direction only. `C14` is also permissive but on the
status channel, and two of its three routes are TruePad-side or already
closed; it ranks behind `C16`.

## OC-27 addendum — what anchors "exact", and conformance separated from correctness

### Where the standard column comes from

**Computed, not read.** SP 800-90B prints no cutoff values. §3.1.4.3 gives the
procedure and nothing else — quoted from the reference PDF
(`audits/2026-09-30/reference/NIST.SP.800-90B.pdf`, SHA-256 `9b0dd771…`, p. 14):

> *1. Let p = 2^−H_I. Let α be 0.000 005. … 5. Calculate
> P(X ≥ X_max) = Σ_{j=X_max}^{1000} C(1000, j) p^j (1−p)^{1000−j}. If
> Pr(X ≥ X_max) < α, the test fails. Otherwise, the test passes.*

There is no worked example and no table, so 570, 312, 173, 99, 58, 36, 23, 19
and 15 are **this project's evaluations of that sum**, three times over:
`restart_cutoff_exact.py` (mpmath `binomial()`), `restart_cutoff_anchor.py`
(exact rational recurrence, no binomial coefficients, no floating point), and
the finder's own oracle from the batch phase, which `OC-7` matched digit for
digit. Three implementations agreeing removes floating point and a shared code
path as failure modes. It does **not** remove a shared misreading of the
sentence. The two readings that could be mistaken are both pinned to the text:
the sum starts *at* `X_max` (inclusive, `j = X_max`), and equality passes
(*"if … < α the test fails, otherwise passes"*). No published validation table
and no third-party implementation's output for this test was located offline.

**So the claim is: exact and self-consistent across three implementations of
the standard's printed formula, pinned to the quoted text — not exact and
independently anchored to published values.** A reader who wants the stronger
claim needs an external number this project does not have.

### The conformance finding, stated on its own

`restart_main.cpp` does not implement the test §3.1.4.3 specifies. The
standard's step 5 is the tail of one Binomial(1000, p); the tool's
`simulateCount()` draws 1000 symbols over 2^H_I cells and returns the maximum
over all cells, and `simulateBound()` takes the (1−α) order statistic of that.
The two are different random variables; the tool's sits higher, by 2–5 counts
at every H_I in 1..8, and the tool therefore accepts restart matrices the
standard's test rejects. **That is the finding. It is permissive, it is
established by exact computation and by measurement, and a laboratory running
this binary is not running SP 800-90B's restart sanity check.**

### The correctness question, stated separately — a question about the standard, not a defence of the tool

Whether the tool's statistic is the *better* test is a different question with
a different audience, and it is open. `X_max` as the standard defines it *is*
a maximum over symbols within a row (step 2: *"Set X_Ri to the highest count
value for row i"*) and then over 2000 rows and columns. The standard corrects
for the 2000 rows and columns (α = 0.01 / 2000) but tests the resulting maximum
against the tail of a single cell's binomial. If the intended null is "no cell
is over-represented", then comparing a maximum over 2^H_I cells against one
cell's tail inflates the false-positive rate by roughly the number of cells, and
raising the cutoff to the quantile of the maximum — which is what the tool does
— is the conventional response. On that reading the tool's statistic is the
more defensible one and the standard's specification is the weaker choice.
This is **not shown here** either way: this audit computed the two cutoffs, it
did not evaluate which null is right for an entropy-source validation. It does
not soften the conformance finding, because conformance is to the text as
written. It is recorded so a reader does not take `OC-27` as a claim that the
tool's statistics are wrong — that is not what was shown.

### Upstream

`simulateCount()` and `simulateBound()` are upstream code, present unchanged on
`upstream/master` at `87c104d` (`git show upstream/master:cpp/restart_main.cpp`
contains both). This finding sits squarely on the upstream side of the line.
Nothing is sent upstream (decided 2026-10-15); the inventory row is marked.

## OC-29 — C16 and C23 repaired together on the restart gate, with the four-state matrix

> **SUPERSEDED FOR C23 — 2026-10-19, see `OC-30`.** The C23 half of this repair
> installed the defect instead of removing it: it made the printed binomial
> formula the deciding cutoff, which rejects correctly-operating sources. It is
> replaced by the exact distribution of the multinomial maximum. **The C16 half
> stands unchanged** — the H_I grammar, the scale requirement, the underflow and
> non-positive refusals are unaffected by any of this. The four-state matrix is
> rebuilt with the corrected C23 axis in `OC-30`.

Two permissive defects on one gate are worse together than apart: `C16` makes
the gate vacuous for a mis-scaled `H_I`, `C23` makes the cutoff too high when
`H_I` is sane. Both are repaired in `cpp/restart_main.cpp`; the regression is
the `C16 + C23` section of `cpp/selftest/regression-restart.sh`. **Self-authored
and unreviewed, like every repair on master.**

### What changed

**`C23`.** `X_cutoff` is now `exactBound(0.000005, H_I)`: §3.1.4.3 step 5
summed from the top in `long double` through `lgammal`, returning the largest
`x` with Pr[X ≥ x] ≥ α. α is the standard's literal 0.000005 (the Šidák value
the tool used gives the same cutoff at every H_I in 1..8, `OC-7`). `-s` is
accepted for compatibility and ignored, and the usage text says so. The report
now carries `restartHI`, `restartAlpha`, `restartXmax`, `restartXcutoff` and
`passedRestartSanityCheck` in both modes, so a consumer can recompute the
decision instead of reading it (`OC-11` item 4, `XR-10`).

**`C16`.** The `H_I` argument has an explicit grammar — digits, optional
fraction, optional exponent, optionally followed by `/symbol` or `/bit`;
hex floats, whitespace and trailing text are refused; `strtod` underflow or
overflow (`ERANGE`) is refused, so `1e-400` no longer becomes 0; `H_I ≤ 0` is
refused (an initial estimate of no entropy makes both gates vacuous); and
**for a symbol wider than one bit the scale must be stated**: `7/symbol` is
used as given, `0.875/bit` is multiplied by `bits_per_symbol`, and a bare `7`
is refused with a message naming both forms. A bare number stays accepted for
1-bit symbols, where the scales coincide. This is the answer to "a value of 0.5
that should have been 4.0 passes any range check": the scale cannot be
established from the number alone, so the number alone is refused. The
pre-repair tool accepted the bare `0.875` on an 8-bit symbol with a cutoff of
615 (matrix below) — the wrong scale, silently, with a cutoff thirty times
too permissive.

**The valid domain, stated:** a finite decimal, `0 < H_I ≤ bits_per_symbol`
after scale resolution, scale stated whenever `bits_per_symbol > 1`.

### The matrix — each fix shown against the other's state

Built four ways from the same source with the audit-only knobs
`EA_RESTART_WITHOUT_C16_FIX` / `EA_RESTART_WITHOUT_C23_FIX`
(`reproducers/c16-c23-matrix.sh`, `logs/c23/c16-c23-matrix.log`; the pre-C16
parse cannot take `/symbol`, so the sane input is `7` for those builds and
`7/symbol` for the C16 builds — same intent, the only syntax each accepts):

| build | sane: H_I 7, X_max 24 (exact cutoff 23) | underflow: H_I `1e-400`, X_max 20 | scale: `0.875` meant per bit, bare, 8-bit |
|---|---|---|---|
| neither (the tag) | **ACCEPTED**, cutoff 27 | **ACCEPTED**, cutoff 1000 | **ACCEPTED**, cutoff 615 |
| C16 only | **ACCEPTED, cutoff 27** — still too permissive | REFUSED | REFUSED |
| C23 only | REJECTED, cutoff 23 | **ACCEPTED, cutoff 1000** — correct cutoff, vacuous gate | **ACCEPTED, cutoff 614** — correct cutoff for the wrong H_I |
| both | REJECTED, cutoff 23 | REFUSED | REFUSED |

Each fix alone leaves the other's hole exactly where the other was: with `C16`
fixed and `C23` not, a sane `H_I` still reaches a cutoff four counts too high;
with `C23` fixed and `C16` not, the exact cutoff is reachable only when `H_I`
is in range and at the right scale, and a wrong-scale `H_I` gets an exact
cutoff for the wrong p. Only the bottom row closes the gate.

### The regression, shown failing

`regression-restart.sh` against the repaired build: PASS, including the
`C16 + C23` section (`logs/c23/regression-restart-repaired.log`): eight
refusals, `0.875/bit` resolving to the same cutoff as `7/symbol`, a 1-bit bare
`H_I` still accepted, **32 of 32 cutoffs equal to the exact-rational table**
at H_I = 0.25 … 8 in steps of 0.25 (`restart_cutoff_anchor.py`, α = 0.000005),
X_max 24 at H_I 7 rejected with the JSON saying `restartXcutoff 23,
passedRestartSanityCheck false`, X_max 20 still passing.
Against the tag build via `REGRESSION_RESTART_TOOL`: **FAIL**
(`logs/c23/regression-restart-vs-tag.log`): `1e-400` and `0` accepted with
exit 0, every cutoff absent or different, X_max 24 accepted.

Three of the script's older cases had to move: the N-10 case used `H_I = 0`
(now inadmissible) on a row-alternating matrix whose constant columns give
X_max = 1000, which passed only because the cutoff was 1000 — it now uses a
checkerboard at H_I = 1; a leading `-` now fails the grammar before any sign
check, so `-1` is refused with the grammar message; and every bare `H_I` on an
8-bit symbol in `regression-restart.sh` and `regression-output.sh` is written
`/symbol`. Those are the only callers in this repository; `regression-iid-
failclosed.sh` and `sanitizer-restart-c01.sh` use 1-bit symbols and are
unchanged.

### What the C23 repair does to published figures

**Nothing, and explicitly so.** No figure in this repository or its documents
rests on a restart acceptance: `pin-check.sh` and the selftest reference corpus
are `ea_non_iid` only; the 2026-09-30 and 2026-10-11 audit logs that contain
"Restart Sanity Check Passed" are synthetic instrument runs (alternating,
uniform, de Bruijn and forced-count matrices) made to test the tool, not
figures about any source; TruePad's restart evidence is physical and **NOT
RUN**. That absence is what makes this repairable without a claim revision —
and it is also why `XR-10` is time-sensitive: the first real restart run is
planned for January 2027, and it must not be the one decided by the old
cutoff.

**Measured on this machine.** The exact cutoff is arithmetic and transfers;
the `long double` summation is the only numeric step, and the 32-point check
against exact rational values is the guard on it. The tag build keeps the old
cutoff and the old bare-`H_I` syntax; it is the reference tool, not a repaired
one.

## OC-28 addendum — C14: what reads the status channel, and what it decides

`C14` was left as "permissive on the status channel". That is a disposition
only if nothing acts on the channel. Something does:

| reader | what it does with exit status / the `-o` report | consequence of a false success |
|---|---|---|
| `cpp/selftest/run-all-checks.sh` and every `regression-*.sh` | treat non-zero as FAIL, 2 as could-not-run | test-side only: a false 0 hides a regression from the suite, it does not produce a figure |
| TruePad's harness (per `XR-01`, `XR-04`, `XR-08`: it checks the exit status and then reads the `-o` file, and it refuses on the canary's INDETERMINATE) | decides whether to read a figure, and which figure, from these two channels | a stale `-o` file after an exit-255 run reads as a complete, errorLevel-0 figure (`XR-01`); `exit 0` on a `--version`-named input reads as success with no figure at all (`oac-16`) |

So the channel is acted on downstream and **`C14` is a third permissive path,
not a cosmetic finding.** It joins the queue behind `C16`/`C23` (now
repaired). Its two live routes are fork-side repairable: write the error
report on *every* failure path, or unlink the `-o` target before assessing,
so no stale report can survive; and stop scanning `argv` for `--version`
after `getopt` has started. The uniform `255` (`oac-5`) stays a
diagnosability gap, not a permissive one. Not repaired here; queued with its
direction fixed by execution (`OC-14`) and its consumer named by the cross-repo
record, which is an argument about TruePad's code that this session has not
read.

## OC-30 — C23 corrected: the printed formula is the defective side, the anchor is published, and the repair is the exact multinomial maximum

> **SCOPE, narrowed 2026-10-19 once the boundary was measured (`OC-39`,
> `XR-13`).** This entry is a conformance finding and a correctness argument,
> and its *magnitude* scales with the number of effective cells, `2^H_I` — it is
> a **wide-alphabet** phenomenon. At 8 bits the printed formula rejects 83 % of
> full-entropy matrices and at 4 bits 12 %. At **width 1 it vanishes below
> H_I ≈ 0.989**: the printed and corrected cutoffs are identical from 0.50 to
> 0.989, and at the 0.696 operating point this project actually uses both are
> **683** with a measured false-reject rate of **1.10 %** against the 1 %
> target.
>
> **BOTH FIGURES IN THAT SENTENCE ARE WRONG — SUPERSEDED BY `OC-49`.** The
> cutoff at 0.696 is **684**; 683 is the value at 0.70, a rounded stand-in that
> was then reported as the real operating point, and the cutoff is a step
> function. And the two cutoffs are NOT identical throughout 0.50–0.989: they
> differ on 36 narrow intervals totalling 0.217 % of that range, one of which
> an outside audit found and this session reproduced. The surviving conclusion
> — that `C23` changes no verdict at 0.696 — is now proved by boundary
> analysis instead of sampling. So at that point the repair bought **correctness, not a changed
> figure**. The conformance point stands at every width — a tool that does not
> implement the printed procedure is a problem whichever test is better — but
> the permissiveness is real only where the alphabet is wide, and the figures
> below should be read with that scope attached.

**This entry supersedes `OC-7`'s conclusion, `OC-26`, `OC-27` and the C23 half
of `OC-29`.** My own error, stated plainly: I treated closer adherence to
§3.1.4.3's printed formula as evidence of a better test, called upstream's
higher cutoff "permissive", and in commit `a5005bd` made the printed formula
the deciding cutoff. That installed the flaw rather than removing it. The
measurements I made were sound; the direction I drew from them was backwards,
and three implementations agreeing on the printed formula's value did nothing
to detect it, because they shared the same wrong choice of statistic.

### The external anchor, which "exact and self-consistent" was not

`OC-27`'s addendum said no published values existed and no third-party output
was located. Both exist:

- **Hill / UL, formal comments on SP 800-90B (final), v1.9, 2019-12-12**,
  `https://www.untruth.org/~josh/sp80090b/`, file
  *"UL SP800-90B-final comments v1.9 20191212.pdf"*, SHA-256
  `35ea31cede99b8432f5f61b36dfa10c88aa268cc7d70bf7e0cedc272926b9c93`,
  43 pages. Comment 3 (pp. 4–5) and Section 3.2 (pp. 21–25), Table 3 (p. 23).
- **Upstream issue usnistgov/SP800-90B_EntropyAssessment#56**, "The restart
  testing is more prone to failure than desired", opened 2018-09-21, closed
  2019-02-04: *"This implementation follows the January 2018 SP800-90B test
  specification, so as a result the restart testing has a higher than desired
  chance of failure. … The tool should attempt to establish the correct cutoff
  through simulation, given the specific assessment that is being used."*

So upstream's simulated cutoff is a **deliberate, requested correction**, and
`OC-27`'s "the defect is the silence" was the only part of that entry pointing
the right way.

**Anchor 1 — Hill's Table 3, both columns, all fifteen rows**
(`oracles/restart_multinomial_max.py`, `logs/c23/anchor-table3.log`):

| min entropy | series | Hill binomial | ours | Hill simulated | ours (exact) |
|---|---|---:|---:|---:|---:|
| 0.852803 | MedianEnt | 623 | **623** | 625 | 623 |
| 0.995319 | IIDMedianEnt | 571 | **571** | 572 | **572** |
| 1 | FullEnt | 570 | **570** | 572 | **572** |
| 1.86565 | MedianEnt | 338 | **338** | 343 | 341 |
| 1.9908 | IIDMedianEnt | 314 | **314** | 317 | **317** |
| 2 | FullEnt | 312 | **312** | 318 | 316 |
| 3.75695 | MedianEnt | 113 | **113** | 118 | **118** |
| 3.97586 | IIDMedianEnt | 100 | **100** | 105 | **105** |
| 4 | FullEnt | 99 | **99** | 104 | **104** |
| 7.41556 | MedianEnt | 19 | **19** | 23 | **23** |
| 7.87995 | IIDMedianEnt | 16 | **16** | 20 | **20** |
| 8 | FullEnt | 15 | **15** | 19 | **19** |
| 13.2812 | MedianEnt | 3 | **3** | 6 | **6** |
| 14.3163 | IIDMedianEnt | 3 | **3** | 5 | **5** |
| 16 | FullEnt | 3 | 2 | 4 | **4** |

**14 of 15 on the printed-formula column, 12 of 15 on the simulated column**,
and both discrepancies are diagnosed rather than left standing:

- **The three simulated-column deltas are simulation noise in the published
  table, not error in the exact computation.** All three sit where the
  distribution is flattest: one count of cutoff changes the tail by a factor of
  only ~1.35–1.41 there, so a 2,000,000-round order statistic with ~9 expected
  exceedances lands a count or two high (at 8-bit the factor is 5.26 and the
  table matches exactly). Two independent confirmations: Hill's own table is
  **non-monotonic** across one of them (H_I 1.9908 → 317 but H_I 2 → 318, when a
  *lower* min entropy cannot give a *smaller* cutoff), and **upstream's own
  5,000,000-round simulation lands on our value, not the table's**, at every one
  (`logs/c23/nist-sim-disputed-points.log`): H_I 0.852803 → 623, H_I 1.86565 →
  341, H_I 2 → 316. Eight repeat runs at H_I 1.86565 span 340–342 and never
  reach 343 (`logs/c23/determinism.log`).
- **The 16-bit printed-formula entry does not follow from the printed rule.**
  Pr[X ≥ 2 | Bin(1000, 2⁻¹⁶)] = 1.15e-04 ≥ α and Pr[X ≥ 3] = 5.84e-07 < α, so
  by step 5 ("if Pr(X ≥ X_max) < α, the test fails") 3 **fails** and the largest
  passing count is 2. Hill's 3 is the smallest *failing* count, a one-sided
  convention difference at the one row where the cutoff is small enough for it
  to show. Out of the tool's range regardless: it refuses symbols wider than
  8 bits.

**Anchor 2 — Hill's published failure-rate series, identified by computation.**
Hill reports 1.2 %, 1.7 %, 6.5 % and 32.4 % at 1, 2, 4 and 8 bits (v1.9 p. 22).
Computing the false-reject rate under each of his three hypotheses in turn
identifies which series those are — and it is **not** the full-entropy one:

| width | ours, FullEnt | ours, IIDMedianEnt | ours, MedianEnt | Hill's quoted |
|---:|---:|---:|---:|---:|
| 1 | 1.6 % | **1.2 %** | 0.0 % | 1.2 % |
| 2 | 3.3 % | **1.7 %** | 0.0 % | 1.7 % |
| 4 | 10.7 % | **6.4 %** | 0.0 % | 6.5 % |
| 8 | 82.5 % | **32.3 %** | 0.3 % | 32.4 % |

Four of four to within a tenth of a point, under IIDMedianEnt. The full-entropy
rates are **worse** than the published figures, which strengthens the finding
rather than weakening it, and matches Hill's own remark that the FullEnt track
"best shows the problems in this test construction" with "a theoretical failure
rate of nearly 100 % for wide data" (p. 4). Anyone repeating 32.4 % should say
which series it is.

**Anchor 3 — the method against brute force.** Levin's representation is
validated against exact enumeration of the multinomial at six (n, k, m) points,
agreeing to better than 1e-12 (`logs/c23/anchor-table3.log`, first table). This
is the method check; the two anchors above are the result checks.

**Anchor 4 — full matrices, with the dependence included.** The arithmetic above
treats the 2000 row and column experiments as independent, which they are not
(Hill comment 3.b). Measured instead on 2000 synthetic full-entropy 1000×1000
matrices per width, counting rows *and* columns exactly as the tool does
(`logs/c23/fullmatrix-false-reject.log`):

| width | printed-formula cutoff | rejects | corrected cutoff | rejects |
|---:|---:|---:|---:|---:|
| 8 | 15 | **83.20 %** | 19 | 0.20 % |
| 4 | 99 | **11.65 %** | 104 | 0.90 % |
| 2 | 312 | **3.15 %** | 316 | 0.65 % |
| 1 | 570 | **1.40 %** | 572 | 0.75 % |

Against the 1 % the standard targets. The measured rates track the computed ones
(83.20 vs 82.5, 11.65 vs 10.7, 3.15 vs 3.3, 1.40 vs 1.6), so the row/column
dependence shifts the rate by well under a point at every width — Hill's
judgement that it "seems safe to ignore this theoretical problem" is now
measured here rather than taken on trust, and it is recorded as a **known
approximation carried by every cutoff derived this way, the exact multinomial
one included**: the exactness is in the distribution of the maximum, not in the
independence of the 2000 experiments.

### Why the corrected cutoff is still more conservative than 1 %, which is not a defect

The table above has a number that needs accounting for before someone else
finds it: the corrected 8-bit cutoff rejects far fewer than the 1 % the standard
targets. Unexplained slack in an exact result is the same shape as the defect
just repaired, pointing the other way. Four candidates were checked and the
answer is **discreteness, with the first measurement's point estimate inflated
by sampling error**; the other two contribute nothing.

**1. The α the computation targets — correct, and consistent by design.** The
Levin computation is evaluated at the **per-test α = 0.000005** of §3.1.4.3
step 1, not at the 0.01 family-wise figure. Those two are the same requirement:
1 − (1 − 5e-6)^2000 = **0.995 %**, which is the 0.01 the standard's second
paragraph states for "the entire sanity check". So the per-test value is the
right one to compute a per-experiment cutoff at, and the family-wise rates in
the tables below are derived from it rather than targeted directly.

**2. Discreteness — this is the explanation.** The counts are integers and the
tail moves in large multiplicative steps, so the smallest count meeting the
per-test target can land well inside it. Both numbers, at every width:

| width | cutoff − 1 | per-test tail | family-wise | **cutoff used** | per-test tail | family-wise |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 571 | 5.914e-06 | **1.18 %** | 572 | 4.369e-06 | 0.87 % |
| 2 | 315 | 6.120e-06 | **1.22 %** | 316 | 4.354e-06 | 0.87 % |
| 4 | 103 | 6.258e-06 | **1.24 %** | 104 | 3.515e-06 | 0.70 % |
| 8 | 18 | 8.241e-06 | **1.63 %** | 19 | 1.568e-06 | 0.31 % |

At every width the next count down **exceeds** the target, so the value used is
the smallest that meets it and the undershoot is forced. At 8 bits the step is
coarsest — one count changes the tail by a factor of 5.26 there against ~1.4 at
1 bit — which is exactly why the undershoot is worst at 8 bits. A cutoff of 18
at 8 bits would be 1.6 times *too permissive*; 19 is three times too
conservative; there is nothing in between. **The correct statement is that the
8-bit cutoff is ~3× conservative by discreteness, not 5×** — the 5× reading
came from the first measurement's point estimate, which was four events.

**3. Sampling error — it accounted for the rest.** 0.20 % of 2000 matrices is
four rejections, an interval far too wide to compare against 0.31 %. Re-measured
at **20,000** matrices (`logs/c23/fullmatrix-false-reject.log`):

| 8-bit cutoff | rejects | rate | 95 % interval | computed (independence) |
|---:|---:|---:|---|---:|
| 15 (printed) | 16499 / 20000 | 82.50 % | 81.97 – 83.03 % | 82.5 % |
| 18 | 304 / 20000 | 1.52 % | 1.35 – 1.69 % | 1.63 % |
| 19 (used) | 53 / 20000 | **0.27 %** | **0.19 – 0.34 %** | 0.31 % |

The stable figure is 0.27 % with the computed 0.31 % inside its interval. The
2000-matrix intervals for the other widths also all contain their computed
values (1-bit 15/2000 = 0.75 %, 0.37–1.13 % against 0.87 %; 2-bit 13/2000 =
0.65 %, 0.30–1.00 % against 0.87 %; 4-bit 18/2000 = 0.90 %, 0.49–1.31 % against
0.70 %). Rates from small counts are reported with their intervals from here on.

**4. Row/column dependence — bounded, from the measurement that constrains it.**
Corrected 2026-10-19: this bound was first cited from the 82.5 % agreement at
the *printed* cutoff, which was the wrong measurement to cite. Rejection there
is a **bulk** event, and the independence approximation does its work in the
**tail**; agreement at an 82.5 % rate says almost nothing about behaviour at
0.3 %. The 82.5 % match is kept below as a check that the computation is right
where the probability is large, and it carries no part of the dependence claim.

The measurement that bounds it is the tail one, at the cutoff actually in use,
re-measured at **100,000** matrices:

| 8-bit cutoff | rejects | measured | 95 % interval | computed under independence |
|---:|---:|---:|---|---:|
| **19 (the cutoff in use)** | 293 / 100 000 | **0.293 %** | **0.260 – 0.327 %** | 0.31 % |
| 18 | 1636 / 100 000 | 1.64 % | 1.56 – 1.72 % | 1.63 % |
| 15 (printed) | 16 499 / 20 000 | 82.50 % | 81.97 – 83.03 % | 82.5 % |

The computed value sits inside the interval at the cutoff in use, so the data
are consistent with no dependence effect at all, and **any effect is below the
interval half-width: ±0.034 points at the corrected 8-bit cutoff.** The second
row is an independent tail check at a different rate — 1.64 % measured against
1.63 % computed, agreeing to 0.01 points — so the independence approximation
holds across two tail events two orders of magnitude apart in probability, not
only in the bulk. **The bound holds at the corrected cutoff specifically**; it
is not claimed for cutoffs far from it, and the 82.5 % row is evidence about the
computation rather than about the dependence.

That is a stronger and better-sited version of Hill's judgement that it "seems
safe to ignore this theoretical problem", and it remains a stated approximation
carried by every cutoff derived this way, the exact multinomial one included.

**And a fifth thing, checked because the operating point is not where the method
was validated.** Levin's representation was validated against brute-force
enumeration only at small (n, k), where enumeration is possible. Validated now
at the **actual parameters** — n = 1000, k = 256 — against 2,000,000 simulated
single 1000-sample experiments, the same statistic `simulateCount()` forms
(`logs/c23/levin-validation-at-operating-point.log`):

| m | exact (Levin) | empirical, 2e6 rounds | 95 % interval |
|---:|---:|---:|---|
| 15 | 8.719e-04 | 8.495e-04 | 8.09e-04 – 8.90e-04 |
| 18 | 8.241e-06 | 7.5e-06 | 3.70e-06 – 1.13e-05 |
| 19 | 1.568e-06 | 1.0e-06 | 0.00 – 2.39e-06 |

Agreement across five orders of magnitude of tail probability, every exact value
inside the simulated interval. The method is sound at the point it is used, not
only where it could be enumerated.

### The finding, in its corrected direction

**The defective side is the standard's printed formula.** §3.1.4.3 step 5 prints
the tail of a single Binomial(1000, p), but the value tested is the largest
count of the *row/column-specific* most likely symbol — the maximum cell count
of a multinomial, which is stochastically larger. Hill comment 3.a: *"The
underlying distribution for the existing test is really the maximum count of any
symbol of a multinomial distribution; our testing indicates that the binomial
distribution isn't a good approximation of the actual underlying
distribution."* And comment 3.c: the printed p-value equation *"is incorrect, as
this is not the probability of this event."* A cutoff computed from it
disqualifies correctly-operating noise sources, and under §3.1.4 a sanity-check
failure means **no entropy estimate is awarded at all** — Hill calls that
outcome "catastrophic" from the vendor's perspective, which is why he stresses
it is "vital to get this test 'right'".

**Upstream's simulation is the workaround, and the real upstream defect is that
it is silent.** `simulateCount()`/`simulateBound()` simulate the right statistic
and are unchanged on `upstream/master` at `87c104d`. Nothing in
`restart_main.cpp` records that the implementation deliberately departs from the
printed procedure, which formula it departs from, or why — so a reader of the
code cannot tell a deliberate correction from an error, and I could not either.
**That is the finding: a documentation defect, upstream's, not a safety one.**

**The conformance question, separately.** A tool that does not implement the
printed procedure is a problem whichever test is better, because a laboratory
using it is not running SP 800-90B's restart sanity check as written. That
remains true and is why both numbers are now reported. But it is a conformance
and traceability matter, not a reason to adopt the printed formula.

**The correctness question, stated as a question about the standard.** On the
evidence above the tool's statistic is the better-posed one and the standard's
printed specification is the weaker choice: the standard corrects α for the 2000
row/column experiments but then tests their maximum against one cell's binomial
tail. This audit did not evaluate which null is right for an entropy-source
validation; it computed both cutoffs and measured both false-reject rates.
Recorded as a question, not as a defence of the tool.

### The repair

`cpp/restart_main.cpp` now computes the deciding cutoff as the **exact
distribution of the multinomial maximum** — the first of the two exact methods
Hill names (Levin, *"A Representation for Multinomial Cumulative Distribution
Functions"*, Ann. Statist. 9(5), 1981), under his worst-case configuration
(⌊1/p⌋ symbols at probability p plus one holding the remainder, matching the
`k_effective` upstream already used). This is better than both the printed
formula and a simulation: it targets the correct statistic *and* is exact and
reproducible. Every factor in Levin's identity is a probability or a log-domain
scalar, so nothing underflows.

**Both numbers are reported.** `-v` prints the deciding cutoff and
`X_cutoff_printed_binomial` beside it; the report carries `restartXcutoff`,
`restartXcutoffPrintedBinomial` and `restartCutoffMethod`
(`exact-multinomial-maximum`), alongside `restartHI`, `restartAlpha`,
`restartXmax` and `passedRestartSanityCheck`. A reader can see the gap and which
figure the verdict used.

**Determinism and cost.** Upstream's simulated cutoff varies run to run where
the distribution is flat — measured 571/572/573 at H_I 1, 316/317 at H_I 2,
340/341/342 at H_I 1.86565 over eight runs each — while the exact method returns
one value every time, and that value sits inside the simulation's spread
(`logs/c23/determinism.log`). Cost is a modest improvement, not a dramatic one:
a full `ea_restart` run drops from 6.8 s to 5.3 s on this machine, the
difference being the 5,000,000-round simulation the exact method replaces.

**The five-state matrix** (`reproducers/c16-c23-matrix.sh`,
`logs/c23/c16-c23-matrix.log`). The C23 axis needs three states, not two,
because the superseded repair is itself one of them and the record has to be
able to show it (`EA_RESTART_C23_PRINTED_BINOMIAL`):

| C16 / C23 | full-entropy 8-bit, H_I 8 (correct answer: accept) | X_max 24 at H_I 7 | H_I `1e-400` | `0.875` bare, wrong scale |
|---|---|---|---|---|
| old / upstream-sim (the tag) | accept, cutoff 19 | accept, 27 | **accept, cutoff 1000** | **accept, cutoff 614** |
| strict / upstream-sim | accept, cutoff 19 | accept, 27 | REFUSED | REFUSED |
| strict / **printed-bin** (superseded `a5005bd`) | **REJECT, cutoff 15** | **REJECT, 23** | REFUSED | REFUSED |
| old / exact | accept, cutoff 19 | accept, 27 | **accept, cutoff 1000** | **accept, cutoff 614** |
| strict / exact (shipped) | accept, cutoff 19 | accept, 27 | REFUSED | REFUSED |

The first column is the one that settles it: the data is drawn uniformly, so the
correct verdict is known by construction, and the printed-formula build is the
only one that disqualifies it. The C16 columns are unchanged from `OC-29` — each
fix still leaves the other's hole exactly where it was.

A first run of this matrix printed a uniform wall of `REFUSED` because a broken
hex literal in its own generator meant no input files existed. That is the
false-green shape this project keeps finding, in my own harness: the script now
fails closed if an input is missing, prints each input's digest, and
distinguishes "no input" from "refused by the parse".

**The regression** (`cpp/selftest/regression-restart.sh`, `C16 + C23` section).
PASS on the shipped build: eight C16 refusals, `0.875/bit` resolving to the same
cutoff as `7/symbol`, **both cutoff columns matching the exact oracle at 32
values of H_I from 0.25 to 8**, the deciding cutoff strictly above the printed
one at all five widths, a full-entropy 8-bit matrix accepted, X_max 24 accepted
with both numbers in the JSON, X_max 28 still rejected. Shown failing against
the superseded printed-binomial build — 3 checks, including the full-entropy
matrix rejected at exit 255
(`logs/c23/regression-restart-vs-printed-binomial.log`) — and against the tag
build, 27 checks (`logs/c23/regression-restart-vs-tag.log`).

### Task 4's two ambiguities

**Mapped-down or original wide data (Hill comment 3.d).** Moot in this
implementation, and settled from the code rather than argued: `ea_restart`
refuses `bits_per_symbol` outside 1–8 (`restart_main.cpp:427`), reads one byte
per sample, and `read_file()` maps the observed symbols down to a contiguous
`alph_size` range (`utils.h:484-525`). Wide data cannot be loaded at all, so the
question never arises here; the cutoff tables being anchored against assume the
same 1000-sample, ≤256-symbol setting. One consequence of the repair worth
recording: upstream's `simulateBound()` asserts `k_effective <= k` where `k` is
the *observed* `alph_size`, which can abort when a dataset's observed alphabet
is smaller than the claimed H_I implies; the exact method takes the worst case
from H_I alone, as Hill specifies, and cannot abort there.

**Row/column non-independence (Hill comment 3.b).** Recorded as a known
approximation carried by every cutoff derived this way, the exact multinomial
one included, with its size measured in Anchor 4 above: under a point at every
width tested.

### Standing

`C23` leaves the permissive register entirely — it was never permissive in
substance. What remains is an upstream documentation defect, now recorded, and a
fork repair that implements the correct statistic exactly and reports the
printed-formula figure beside it. The repair is **self-authored and unreviewed**,
like every repair on master, and this entry is the second correction to my own
C23 conclusion. Measured on this machine; the cutoffs are arithmetic and
transfer, the simulation figures are upstream's and would be re-drawn anywhere.
Nothing here decides anything about a device: physical items stay **NOT RUN**.

## OC-31 — C14 repaired: both permissive routes on the status channel closed, each shown failing

`OC-28`'s addendum left `C14` as a live permissive path on the exit-status and
report channel, with two routes named and a consumer that acts on them. Both are
repaired in `cpp/non_iid_main.cpp`, `cpp/iid_main.cpp` and
`cpp/restart_main.cpp`. **Direction: permissive on the status channel, closed.**
Self-authored and unreviewed.

### Route 1 — a stale `-o` report could survive a failed run (`XR-01` / `oac-4`)

Error paths that never reached `writeJsonReport()` left the **previous run's**
report in place, so a harness that checks the exit status and then reads `-o`
could read a complete, `errorLevel 0` figure belonging to different data.

**Writing an error report on every failure path cannot close this**, which is
why that was not the fix chosen: a usage-path `exit()`, an `assert` abort or a
signal reaches none of them, and every new error path would have to remember.
Instead the target is **claimed the moment `-o` is parsed** — a fail-closed
placeholder (`errorLevel -1`, `reportComplete false`, and a message saying the
assessment did not complete and the file must be refused) is written, and every
completing path overwrites it. After any run, including an abort, the file is
either this run's report or a report saying the run did not finish. It is never
a stale success. A bonus property: an `-o` path that cannot be written now fails
**before** the assessment rather than after it.

Measured on the exact path that no "write on every error path" fix would have
caught — `ea_restart -o <file>` with no further arguments, which prints usage and
exits without ever reaching the writer:

| build | after the failed run |
|---|---|
| tag `unrepaired-reference-2026-10-15` | **the previous report survives byte-identical** (`cmp` equal) |
| master, repaired | `errorLevel -1`, `reportComplete false`, `testCases null` |

### Route 2 — `--version` was honoured as a filename (`oac-16`)

The scan ran over **all** of `argv`, including `argv[0]` and the input path, so a
file named `--version` — or that string anywhere in the argument vector — made
the tool print its version and **exit 0 with nothing assessed and no report
written**. On the exit-status channel that is a fail-open. It is now treated as
the option it is documented as: scanned from `argv[1]`, stopping at the `--`
separator and at the first operand. `ea_non_iid --version` and `-q --version`
still work; `-- --version` is a filename.

| build | `ea_non_iid -q -o out.json -- --version 1`, in a directory holding a file of that name |
|---|---|
| tag | prints the version banner, **exit 0, assessed nothing, no report** |
| master, repaired | assesses the file and writes a report |

### What stays open

`oac-5` (every failure is exit 255) and `oac-12` (three file problems collapse
to one message) are **diagnosability** gaps, not permissive ones: they lose the
*cause* of a failure, never turn a failure into a success. Recorded, not
repaired. `oac-13` (the report write is not atomic — a signal mid-write leaves
truncated JSON) is narrowed but not closed by route 1's placeholder: the window
is now "truncated JSON" rather than "stale valid JSON", which a consumer can
detect by parsing. Closing it properly needs write-to-temp-then-rename.

### The regression, both routes, shown failing

Added to `cpp/selftest/regression-output.sh` — which already owns the report and
output contracts — rather than as a new script, so the suite's authoritative
inventory and its expected counts stay as they are (`BUG-REPAIR-GUIDE.md`'s
enumerating-file rule). `REGRESSION_OUTPUT_BINDIR` points the checks at another
build. Against master: **PASS**. Against the tag:
**FAIL, 6 checks** — three tools leaving a stale report, two tools printing the
version for a filename, and one exit-status check
(`logs/c14/regression-output-repaired.log`,
`logs/c14/regression-output-vs-tag.log`). Full suite after the repair: **20
passed, 0 failed** (`logs/c14/run-all-checks-after-c14.log`).

My first version of the route-2 check passed `./--version` rather than
`--version`, which the pre-repair scan never matched — so it "passed" against
the tag and proved nothing until corrected. Recorded for the same reason as the
sed in `OC-23` and the hex literal in `OC-30`.

### Does anything already done rest on this channel being trustworthy?

**On the fork's side, no.** Nothing in this repository's record depends on it:
`pin-check.sh` and the self-test parse `ea_non_iid`'s stdout directly, and the
audit's own figures come from `-vv` output rather than from a report file read
after an exit-status check.

**On TruePad's side the exposure is prospective, not historical, and for the
same reason as `XR-11`.** The cross-repo record (`XR-01`, `XR-04`, `XR-08`)
establishes that its harness checks the exit status and then reads the `-o`
file, so the sequence is real. But every physical run is **NOT RUN** — the
device arrives January 2027 — so no figure of record has passed through it.
Whether TruePad has done anything else that rests on it is a question about
TruePad's code and records, which this session must not read; it is put to them
in `XR-12` rather than answered here.

## OC-32 — the OC-30 lesson applied to the rest of the fork: Hill's comment list against this project's readings

Chosen as the next item over `C22`'s bound (measured, `OC-22`), `C08` (partly
closed), the off-path conditioning clusters, `C-01` (**already fixed** — the
merge brought `delete[]` in `simulateBound`, so the memory's "live carried
defect" note is stale) and the x86-64 canary run (no such host available).
Reason: `OC-30` showed that a repair built on *reading the standard's printed
text* can be confidently wrong, and this project has made roughly twenty such
repairs. I now hold a published third-party list of defects in that same text
(Hill/UL v1.9, 33 numbered comments). Cross-checking the two is the same class
of error, looked for systematically instead of one at a time — and it is the
only item on the list whose value comes from evidence that did not exist here
last week.

**Scope.** Most of Hill's 33 comments concern the standard's *requirements*
(documentation, health tests, conditioning-component rules) and bear on no
computation this tool performs. Three touch readings this project has recorded.

**Comment 3 — the restart sanity check.** Already handled: it is `OC-30`, and it
is the one that inverted.

**Comment 33 — §6.3.1's worked example: corroborated, from an independent
direction.** Hill: *"In Section 6.3.1, there is a typo in the worked example.
The last line should be −log₂(0.6895) = 0.5363."* This project reached the same
value twice, independently and years later: the 2026-09-30 audit ran the example
on the built binary and recorded **0.5363**, "reproduc[ing] to the printed
digits", and `EST-5` / `estimators-mcv-collision-markov-compression-5` found the
**2025-05-29 errata item 2** for that same example arithmetically inconsistent
with the step-2 formula, such that "a validator trusting it would wrongly judge
the tool off by 1.1 %". So two independent parties, seven years apart, both say
the published text of that example is wrong and both land on 0.5363 for its
result — Hill against the 2018 original, this project against the 2025 errata
that was meant to fix it. (The two printed figures are consistent with each
other: −log₂(0.6895) = 0.53638, and 0.5363 is what the unrounded p_u gives,
2^−0.5363 = 0.689537, so 0.6895 is the printed rounding of the same quantity.)
**No change recommended.** Recorded because a reading corroborated by an
independent published source is in a different evidentiary class from one this
project reached alone, and `OC-30` is the reason that distinction now gets
written down.

**Comment 2.b — the bitstring representation is unspecified, which qualifies a
withdrawn finding's reasoning.** Hill: *"This document does not specify how to
represent the dataset as a bitstring of size L×n so this procedure is not
completely specified. How are the symbols to be arranged, and how is each symbol
to be encoded?"* This project independently found the same gap from the other
end — `intake-noniid-aggregation-6` records that the tool's **MSB-first** order
within the declared width (`utils.h:419`) is documented nowhere in the README,
`BUILDING.md`, `NOTICE` or the usage text. The nuance worth recording: `F01` was
**withdrawn** in part on the reasoning that the bitstring is "a deterministic
symbol-wise expansion [that] can carry no structure the symbol battery hasn't
seen". The withdrawal itself stands — it turned on what the standard means by
"binary" (the alphabet, §4.4.2 and §5), which is settled text, not on the bit
order. But "deterministic" is deterministic *given a choice the standard does
not make*, and Hill says so in print. So the withdrawal's conclusion is
unaffected and one clause of its supporting argument is weaker than it reads.
Recorded rather than acted on: nothing is reported upstream, and reopening a
withdrawn finding on a clause that does not carry its conclusion would be
churn.

**What the cross-check did not find.** No other repair or conclusion in this
project rests on a printed-text reading that Hill identifies as defective. The
estimator repairs are about the code failing to implement its own formula
(underflow, truncation, a Null prediction ending a run), not about which formula
to implement; the one place this project *chose* a reading over the printed text
was `C23`, and that is the one that went wrong. The check was worth running for
that reason and the result is a negative one, stated as such.

**Limits.** Hill's document is v1.9 of a comment set on the final standard; it
is one party's analysis, not an erratum, and this project's agreement with it is
corroboration rather than confirmation. Measured and read on this machine; no
claim here is about any source, and physical items stay **NOT RUN**.

## OC-33 — "show that the mutation landed" mechanised, because the base rate says it is being missed

Counting the instrument errors this project has caught: a sed that edited the
wrong line (`OC-23`), two extraction patterns that took the wrong number out of
a longer string and one that searched for a name built from a format string
(`OC-23`), a broken hex literal that printed a wall of `REFUSED` meaning "no
input" (`OC-30`), a route-2 test that passed the wrong string and so passed
against the build it was meant to fail (`OC-31`) — and **two more today**: an
`R-1` recheck that declared the wrong symbol width, so the tool printed its
usage text while the log recorded "no LRS line seen" (`OC-34`), and the first
version of `entropy_floor.py`, which read `testCases[0]` and computed a floor
from the Most Common Value estimator instead of the Overall case (`OC-35`).

That is roughly one per round of work, every round, found only by looking. **A
process with that base rate must not assume it finds them all.** The rule
adopted after `OC-23` was right and was a thing to remember; it is now a thing
that cannot be skipped.

### The contract, in `cpp/selftest/mutation-lib.sh`

A mutation that did not land may produce **neither a pass nor a fail**. It
produces a third outcome, `MUTATION-DID-NOT-APPLY`, counted separately, which
fails the harness and says the harness is broken rather than the guard. The
guard's response is evaluated only after the mutation is shown to have taken
effect, by the means appropriate to what was mutated:

| what was mutated | how landing is proved |
|---|---|
| a file or a directory | digest before and after; a missing target digests as `ABSENT`, itself a change |
| an argument or an input value | the value the **code under test received**, read back from the system — the tool's own recorded command line, or a failure mode that could only occur if the string arrived — never the harness's own variable, which is exactly what `OC-31` got wrong |
| a rebuild with different flags | the binary differs from every other variant's |

### Wired in, and what the count says

| harness | mutations + controls | landing asserted by | result |
|---|---:|---|---|
| `regression-selftest-inventory.sh` (fixtures and references) | 7 + 2 | directory digests | **9 of 9 land, all caught** |
| `harness-inventory-mutation-test.sh` (the script inventory) | 4 + 1 | directory and file digests | **5 of 5 land, all caught** |
| `outside-battery-mutation-test.sh` (**new**: the `OC-23` corpus mutations, previously ad-hoc shell commands that were not repeatable) | 7 + 2 | file digests, plus an explicit `cmp` on the digest-mutation case that would have caught the original sed | **9 of 9 land, all caught** |
| `reproducers/c16-c23-matrix.sh` (build-flag mutations) | 5 builds | all five binaries' digests distinct, printed | **5 of 5 land** |
| `regression-output.sh` route 2 (an argument value) | 2 | the operand confirmed in the tool's own recorded `commandline`, or the version banner, which only prints if the string arrived | **2 of 2 reach the tool** |

**All 25 land today.** That is the measurement asked for, and the honest reading
of it is narrow: it says nothing was silently inert *at this moment*. The value
is not the 25, it is that none of them can stop landing without saying so. The
ones that historically failed to land are now the ones most tightly checked:
the `OC-23` sed case carries its own `cmp`, the matrix fails closed on a missing
input and prints every input digest, and the route-2 string is read back from
the tool.

**Shown failing, as the rule requires of itself.** A copy of
`regression-selftest-inventory.sh` with one `mv` replaced by a no-op reports
`8 of 9 mutations landed and were caught, 1 DID NOT APPLY`, names the mutation,
says "the harness is broken, not the guard", and exits non-zero — where the old
harness printed `FAIL (mutation passed)` and blamed the verifier.

`mutation-lib.sh` and `outside-battery-mutation-test.sh` are deliberately named
so they do not match `regression-*.sh`: `run-all-checks.sh`'s authoritative
inventory does not discover them, so its counts are unchanged
(`BUG-REPAIR-GUIDE.md`'s enumerating-file rule). Suite after the change: **20
passed, 0 failed**.

## OC-34 — the open-items list audited against the current tree; two entries were stale and one was mislabelled

`C-01` was found fixed only incidentally. The whole carried list is now checked
against master rather than assumed. **Two stale entries and one wrong label.**

| item | carried as | checked against master | verdict |
|---|---|---|---|
| **`C-01`** `new uint16_t[]` freed with scalar `delete` in `ea_restart` | "the live carried defect" in the project memory | `restart_main.cpp:326` is `delete[] results;`; tracker already says `FORK-FIXED` via `6f84ad7`/`b3db7ab` | **STALE — fixed by the 2026-10-15 merge `d226f18`.** The memory note was wrong, the tracker was right. Corrected. |
| **`R-1`** `assert(p_col >= 1/k)` aborts for perfectly balanced alphabets | **`BLOCKED-HARDWARE`** in the tracker | **Does not reproduce.** The tracker's own reproducer (balanced k symbols, `random.Random(7)`) run at all five named counts — k = 3, 6, 7, 9, 12, each at a width that fits — completes with `rc = 0` and reaches the test battery (`logs/mutation/r1-recheck.log`) | **MISLABELLED, twice.** It is not a hardware item: the reproducer needs none, and it ran here in minutes. And it no longer reproduces. The assert is still at `lrs_test.h:652` and `calc_collision_proportion` is **unchanged from upstream** (`git log -S` shows only upstream's own commits), so nothing in the fork fixed it — which makes it rounding- and platform-sensitive, the `REPRO-01` shape. Correct state: **not reproducible on this build; reachability on other float environments unknown**, and it belongs with the x86-64 items, not the hardware ones. |
| **`C08`** the harness fails open on absent reference data (`OC-4`) | "partly closed" | `cpp/selftest/selftest:31` now calls `verify-fixture-inventory.sh` **before** any comparison and exits 1 if the manifest is not satisfied; `regression-selftest-inventory.sh` proves seven ways that it does | **The named defect is CLOSED** (`HARNESS-AUD-01`, carried in by the merge). What remains of the 14-member cluster is the diagnosability residue, not a fail-open. |
| **`C22`** `P_local`, `P_global'`, `ZALPHA` | Class 2, bound measured (`OC-22`) | still a subtraction, and until today still performed by hand | **LIVE as arithmetic, now mechanised** (`OC-35`). |
| **`C02`** `hAssessed` carries `word_size × h'` | Class 1, a reading | reproduced today: `hAssessed 7.2338614551796505 = 8 × 0.9042326818974563` on an 8-bit control | **LIVE and correct as recorded**; now checked mechanically by `entropy_floor.py`. |
| **`C03`**, **`C07`** | closed by code, merged | `iid_main.cpp` fail-closed verdict and the log-domain LRS are on master; build-differential passes | **CLOSED on master; NOT closed at the tag.** |
| **`C23`**, **`C16`** | repaired | `OC-30`, `OC-29`; regression passes, fails against the tag | **CLOSED on master, C23 after one wrong attempt.** |
| **`C14`** | permissive, queued | both routes closed (`OC-31`), shown failing against the tag | **CLOSED on master.** |
| **`C06`** `h_out` 7.1552 against a 7-bit ceiling, **`C09`** `ea_conditioning` intake | off-path | `cpp/Makefile:63` `SUPPORTED_TARGETS := iid non_iid restart` — `ea_conditioning` is not built | **LIVE but unreachable on the supported build.** Active work before that scope can expand, which is what `EXCLUDED-UNSUPPORTED` means in the tracker (3 entries: `N-03`, `N-05`, `N-11`). |
| **`C18`** LLP64 integer widths | unknown direction | `sizeof(long) = 8` here | **NEUTRAL on this host; unknown on Windows/LLP64**, which is documented and NOT verified. |
| **`C20`**, **`C21`** | neutral (`OC-13`) | unchanged | **NEUTRAL**; `C21`'s off-path members stay off-path. |
| **`F13`** NaN into `std::min` | `UNCONFIRMED`, "one argument-order edit away" | `utils.h:1153` is still `min(1.0, p_global + …)` — the NaN suppression is still incidental to the argument order | **LIVE as a fragility**, unchanged, and still unmarked at the site. |
| **`REPRO-01`** architecture-dependent verdict | Class 1, pin the architecture | unchanged | **LIVE**, neutralised by pinning plus provenance. |
| **`F01`** | withdrawn; upstream issue #253 still open | unchanged; `OC-32` notes Hill comment 2.b weakens one clause of the withdrawal's argument without touching its conclusion | **WITHDRAWN, stands.** |
| physical items | NOT RUN | unchanged | **NOT RUN.** |

Two tracker-state corrections follow from this and are applied: `R-1` from
`BLOCKED-HARDWARE` to not-reproducible-here, and the memory's `C-01` note.

## OC-35 — the floor computed from a report instead of reconstructed from a document

Chosen over `C08` as the most valuable remaining software item, with the reason:
`C08`'s named defect is already closed (above), so work there is verification of
a residue; whereas **every measurement in this audit exists to support one
number — the floor — and that number was the only thing still produced by
hand.** Two of the three steps in producing it are recorded defects of this
project: finding the right field (`C02`) and remembering the terms (`C22`).

`oracles/entropy_floor.py` reads an `ea_non_iid` JSON report and prints the
floor with every term, its value and its source. On the 8-bit control
(`logs/floor/floor-demo.log`):

| | value |
|---|---|
| `H_original / word_size` | 0.98313975036244872 |
| **`H_bitstring`** | **0.90423268189745631 ← binds** |
| `h'` per bit | 0.90423268189745631 |
| C01 | 3.690e-04 |
| C22a, at n = 8 000 000 | 6.464e-08 |
| C22b | 0 |
| C22c (literal reading) | 2.160e-03 |
| **floor, literal-text reading** | **0.90170361725744819** |
| **floor, `F07` reading** | **0.90386361725744824** |

It also **checks** `C02` rather than restating it: the report's
`hAssessed = 7.2338614551796505` is confirmed to equal `word_size × h'` to
within 1e-12 relative, and is reported as not used.

**Its guards, shown failing.** It refuses a report carrying
`reportComplete: false` (the `C14` placeholder — "the run did not finish"), a
report with non-zero `errorLevel`, a report with no `Overall` case, and any
`n` below 1,000,000 bits rather than extrapolating the `ZALPHA` ceiling it was
not measured at. It states what it does **not** establish: build provenance,
and the restart decision, which is `C23`'s separate accept/reject and never a
subtraction.

**My own error in it, recorded.** The first version read `testCases[0]`. A
non-IID report carries **one test case per estimator** and the assessment is the
one labelled `Overall`; reading the first gave 0.983 instead of 0.904 on the
8-bit control, because Compression binds and Most Common Value does not. That
is the `C02` reading trap one field over, in the script written to stop people
falling into it. The case is now selected by name, and a report without an
`Overall` case is refused rather than guessed at.

## OC-36 — the two rules the landing detector does not cover, swept and controlled

`OC-33` mechanised "show that the mutation landed". **Neither of the two errors
found that same day was a mutation that failed to land**, so neither would have
been caught by it. Both are separate classes, both generalise, and both are now
rules beside the landing rule in `BUG-REPAIR-GUIDE.md` — with the explicit note
that one mechanisation did not close all three.

### Rule 2 — a conclusion from absence needs a well-formed report first

The instance was mine: an `R-1` recheck declared the wrong symbol width, so
`ea_iid` printed its usage text and exited 255, and my log recorded **"no LRS
line seen"** — a statement about the arguments dressed as a statement about the
data. A usage message, an empty file, a crash, a timeout and a completed run
that happens to lack a line are **five** outcomes and only the last is evidence.

**Swept** every harness that draws a verdict from a missing line. Three sites,
and the honest result is mixed:

| site | old behaviour on a malformed run | live false-pass window? |
|---|---|---|
| `regression-272.sh`, baseline and `assert_caught` — "no `Significant difference` line ⇒ clean" | `compareresults.pl` exiting 0 while comparing **zero keys** reads as cleanliness | **YES.** This is `OC-20`'s defect shape — a comparison total in one direction only — seen from the harness side. Now requires comparison output before reading absence. |
| `regression-iid-json.sh` — "no bare `Median` line ⇒ the label repair is present" | a usage message has neither label, so the old test already said FAIL | no: it failed safe. The shape check closes the narrower window where the run died *after* printing the first label. |
| the `R-1` recheck (mine) | reported absence as a data fact | **YES, and it did.** Fixed, and the same classification is built into the new CI job's R-1 step. |

So the sweep found one live false-pass window in a shipped harness, one narrow
one, and one that had already fired. **Negative control**: a usage message is
now classified `NOT A WELL-FORMED REPORT` rather than contributing to a verdict.

### Rule 3 — a labelled read is never a positional read

The instance was also mine, and worse: `entropy_floor.py` read `testCases[0]`
where the assessment is the case labelled `Overall`, producing 0.983 against
0.904 on an 8-bit control — inside the script written to stop people making
exactly that reading error (`OC-35`). No layout shifted; the ordinal was simply
wrong, which is why "it works today" is not evidence for a positional read.

**Swept** `head -1`, `tail -1`, `[0]`, line numbers and `awk` field positions
across every harness and oracle. Converted, in order of what a wrong read would
cost:

| site | was | now |
|---|---|---|
| `pin-check.sh` — **the pinned figure**, and the input digest beside it | `sed … \| head -1` on each | label-anchored with the match **count asserted**: two `Assessed min entropy` lines, or two digests, now FAIL instead of silently using the first |
| `regression-iid-json.sh`, `regression-iid-failclosed.sh`, `regression-restart.sh` — `testCases[0]` on `ea_iid`/`ea_restart` reports | took the first of however many | these reports carry **exactly one** case by design and carry no label to anchor to, so the count is now asserted; a second case is an error |
| `entropy_floor.py` | `testCases[0]` | selected by `testCaseDesc == "Overall"`; a report without that case is **refused**, never guessed at |
| `entropy_floor.py --from-log` (**new**) | — | added so figures produced by hand from a `-vv` text log can be recomputed by the tool that replaced them (`OC-37`); every field is read by its printed label and a missing label is an error |

**Negative control**: a file with the pinned label printed twice now fails the
read rather than resolving it by position.

Left as positional deliberately: `regression-272.sh:122`'s
`ls bin/* | head -1`, which picks an arbitrary fixture on purpose and asserts
nothing about which, and index arithmetic inside the Python reference models,
where the position *is* the meaning.

## OC-37 — the one floor figure this project ever published, recomputed by the tool that replaced the hand process

`OC-35` found the reading trap inside the calculator. The question that follows
is whether the **hand** process — which produced every floor figure before the
calculator existed — fell into the same one, and nobody had asked.

**Searched**: every tracked document, every commit message on every branch, the
cross-repo findings sent to TruePad, and the project memory notes. **There is
exactly one published floor figure**, in `REPAIR-STRATEGY.md`'s worked example:
**0.9239** under the literal reading and **0.9260** under `F07`, from the
harvested ideal-uniform run with `h' = 0.92641`.

**Recomputed through the calculator** (`entropy_floor.py --from-log`, against
`logs/c22/predictor-intermediates.log`, the log it was derived from):

| | |
|---|---|
| `H_original / word_size` | 0.98512337745550083 |
| **`H_bitstring`** | **0.92641349982744703 ← binds** |
| floor, literal reading | **0.9238844351874389** |
| floor, `F07` reading | **0.92604443518743895** |

**It matches.** 0.9238844 → 0.9239 and 0.9260444 → 0.9260. The published figure
is correct, in neither direction wrong. That is the negative result, and it
closes the question.

**Why the hand process survived where the script did not**, which is the part
worth keeping: the `-vv` **text** output prints a labelled aggregate,
`H_bitstring = …`, which is already the minimum over bitstring estimators. The
**JSON** has no such top-level field — the aggregate exists only inside the case
labelled `Overall`, and must be selected. So the two surfaces do not carry the
same trap: the text log hands you the right number under a label, and the JSON
makes you choose. The hand process read the text log and was safe; the script
read the JSON and was not. **The JSON is the more dangerous surface**, and
`C02`'s warning should be read as applying to it in particular.

## OC-38 — C08's last item: what a consumer sees when a run fails, and a format string that was being published

`OC-34` found `C08`'s named defect closed and only diagnosability left, which
made it the last software item on the list. Done, and it had a live bug in it.

**The bug.** Four sites in `cpp/shared/utils.h` read
`testRun->errorMsg = "Error: could not open '%s'\n", file_path;` — a **comma
operator**, not a format call. The report received the **format string**. So an
operator whose input file was empty got, in the JSON:

```
"errorMessage": "Error: '%s' is empty\n"
```

a literal `%s`, a stray newline, and no indication of which file. That is
`oac-12`'s "those reports carry neither filename nor sha256", reproduced and
now fixed: the message is built by concatenation, and the filename is recorded
on the failure path.

**The field.** `errorClass` is added to every report, emitted only on failure,
with three values — `input` (the data or the invocation was rejected before
assessment), `statistical` (the data was assessed and a required test rejected
it), `internal` (allocation, I/O or hashing failed; the run is inconclusive).
That is `oac-5`: nothing had distinguished those three, because every failure
was exit 255 with `errorLevel -1`. **Exit codes are unchanged** — a consumer
that keys on 255 keeps working, and one that wants the cause now has it.

**Concretely, what a person sees that they did not see before**
(`logs/c08/diagnosability.log`, each case run against both builds):

| failure | the tag build says | master says |
|---|---|---|
| empty input file | `"Error: '%s' is empty\n"` | `Error: '/…/empty.bin' is empty.` + `errorClass input` |
| file does not exist | `Error: could not hash the input file.`, **no filename** | `Error: could not stat the input file.` + filename + `errorClass input` |
| input is a character device | `Error: could not hash the input file.` — **the same message as above**, so the two were indistinguishable | `Error: input is not a regular file.` + `errorClass input` |
| declared width too narrow for the data | correct message, no class | same message + `errorClass input` |
| a required IID test rejects the data | `errorLevel -1`, no class | + `errorClass statistical` |

The second and third rows are the point: two different problems produced one
message, which is what "collapse to one errorMessage" meant, and a consumer
could not tell a missing file from an unusable one.

**Still open, and now the only thing left in `C08`:** `oac-13`, the report write
is not atomic. `C14`'s placeholder narrowed it from "stale valid report" to
"invalid JSON", which a consumer can detect by parsing, and closing it properly
needs write-to-temp-then-rename. Listed in `CLOSING-INVENTORY.md`.

## OC-39 — the width-1 cutoff table, and the prediction that the C23 correction vanishes below full entropy

Computed for `XR-13`, which is where the table and its use live. Recorded here
for the method and the result.

**Method.** Both cutoffs at every H_I from 0.50 to 1.00 in steps of 0.02 plus a
fine sweep near the boundary: the printed §3.1.4.3 binomial tail, and the exact
multinomial maximum by Levin's representation. False-reject rates measured on
2000 full 1000×1000 matrices per H_I (4000 at the two boundary rows) whose most
likely symbol has probability exactly `2^-H_I`, rows and columns both counted,
so every rejection is false and the row/column dependence is included.

> **SUPERSEDED BY `OC-49`.** This result is a SWEEP in steps of 0.02 reported
> as an interval, and it is false as stated: the two cutoffs differ on 36
> narrow intervals within 0.50–0.989, totalling 0.217 % of the range, the
> widest 5.4e-04 near H_I = 0.9862. Read the sentence below as "zero at every
> H_I this sweep sampled", which is what it measured.

**Result: the correction is exactly zero at every H_I from 0.50 to 0.989.** At
width 1 and H_I < 1 the worst case is one cell at `p` plus a remainder cell at
`1 − p`; the maximum over two asymmetric cells converges to the dominant cell's
count, and the second cell's contribution to the tail is negligible. At H_I = 1
the cells are equal, symmetry doubles the tail, and the gap is the familiar +2.
The boundary sits **between 0.989 and 0.990**.

**And the printed formula's over-rejection at width 1 is real but small**:
measured 1.70 % [1.30–2.10] at the printed cutoff 570 against 0.93 %
[0.63–1.22] at the corrected 572, at H_I = 1. Compare 83.2 % at 8 bits
(`OC-30`). So the size of the `C23` defect is driven by the number of effective
cells, `2^H_I`: it is a **wide-alphabet** phenomenon, and a one-bit source is
affected only within about 1 % of full entropy.

One consequence for the register: `C23` was, at the operating point this
project actually uses, never going to change a verdict. That does not reduce
the defect — a validation tool that does not implement the printed procedure is
a problem at any width, and at 8 bits the printed procedure disqualifies five
sound sources in six — but it does mean the `C23` work bought correctness
rather than a changed figure. Worth stating because the opposite impression
would be easy to form from `OC-30`'s 83 % alone.

## OC-40 — x86-64 measured: R-1 is live there, one canary signature did not travel, and the arithmetic argument held

`CLOSING-INVENTORY.md` listed three items as needing "one x86-64 machine
briefly". The machine is a workflow file: `ubuntu-latest` is x86-64 Linux on
glibc. `.github/workflows/x86-64-platform-facts.yml`, run 2026-10-19
(`logs/x86-64/`). **Three results, and the most important one inverts an open
item.**

### The platform, printed rather than argued

```
Linux 6.17.0 x86_64 / gcc 13.3.0
sizeof(long double) = 16   LDBL_MANT_DIG = 64   LDBL_MIN_EXP = -16381
LDBL_MIN = 3.3621e-4932    LDBL_TRUE_MIN = 3.6452e-4951
LDBL_EPSILON = 1.0842e-19  FLT_EVAL_METHOD = 0
```

x87 80-bit extended, as expected. One note for anyone comparing this against
the audit's prose: the documents say "emin −16382", meaning `LDBL_MIN = 2^−16382`,
which `3.3621e-4932` confirms; C's `LDBL_MIN_EXP` is one greater by definition
(`−16381`). Both numbers describe the same format.

### R-1 is live, on both platforms — RESTATED 2026-10-19 (`OC-43`)

> **This section's original claim was wrong and is replaced rather than
> amended.** It said R-1 was live on x86-64 and invisible on arm64, and that
> the CI run had disproved two sessions' reasoning. **R-1 reproduces end to
> end on both platforms.** The arm64 "non-reproduction" was a measurement
> against the tag worktree's `-DNDEBUG` binary, with the assert compiled out
> (`OC-42`). What genuinely differs by platform is the *size of the affected
> set* — 117 of 255 alphabet sizes on a 53-bit `long double`, 155 on x87
> 80-bit — and that difference is the real precision effect, because a wider
> `long double` makes the threshold the more accurate side of the comparison.
> Nothing about the platform hid R-1; a build state did.

### R-1 as first measured here, at five symbol counts on x86-64

`OC-34` re-labelled `R-1` from `BLOCKED-HARDWARE` to not-reproducible-here
because its reproducer completes on this Mac. On x86-64 it **aborts every
time**:

```
k = 3, 6, 7, 9 and 12, each at a width that fits:
  shared/lrs_test.h:652: Assertion `p_col >= 1.0L / ((long double) k)' failed.
```

So the item is more serious than either previous label suggested (and the
state is now `FORK-FIXED`, after `OC-41`'s repair; it was briefly
`REPRODUCIBLE-ON-X86-64`, which `OC-43` corrects — it reproduces on both): `ea_iid` aborts with SIGABRT and
writes no report on **perfectly balanced, entirely valid data**. The direction
is fail-closed rather than permissive — it denies an assessment, it does not
inflate one — but a sound dataset gets no figure. The assert is upstream code
and `calc_collision_proportion` is unchanged from upstream, so this is an
**upstream defect reachable on every platform tested**, at a
platform-dependent set of alphabet sizes. It is **not** an instance of the rule
that a platform fact must be printed on the platform — nothing about the
platform hid it. It is an instance of `OC-43`'s rule, a measurement being about
the artefact it ran against, because the reading that called it unreachable was
taken against a binary whose asserts were compiled out.

### The canary: four of five outcomes as argued, and the fifth was the instrument

| binary | expected from `OC-24`/`OC-30` | measured on x86-64 |
|---|---|---|
| master, asserts live | REPAIRED / NOT-DISTINGUISHED | **as argued** |
| master, `-DNDEBUG` | REPAIRED / NOT-DISTINGUISHED | **as argued** |
| tag, `-DNDEBUG` | UNREPAIRED / NDEBUG | **as argued** |
| `/bin/ls` | INDETERMINATE | **as argued** |
| **tag, asserts live** | UNREPAIRED / ASSERTS-LIVE | **INDETERMINATE** |

**The arithmetic argument was right and the string match was wrong.** The tag's
asserts-live build aborted at exactly the predicted place —
`lrs_test.h:683`, `p_colPower >= LDBL_MIN`, which is what `OC-24` said would
happen at W = 20000 on an 80-bit `long double` — and the canary still reported
INDETERMINATE, because it matched the literal `"Assertion failed"`, which is
macOS/clang's wording. glibc writes ``Assertion `expr' failed.`` So the
signature was macOS-only and would have refused every unrepaired Linux binary
it was shown. Direction conservative (INDETERMINATE means refuse the figure),
but a detector that cannot identify the build it exists to identify is a defect.
Fixed to match both wordings and verified against each; the four-outcome
classification on macOS is unchanged.

That distinction is worth keeping separate: `OC-24`'s *reasoning* about the wide
formats survived contact with the platform intact. What did not survive was an
implementation detail of the instrument, which no amount of reading the
arithmetic would have caught.

### The suite on a second platform

`regression-outside-battery` **PASS** — so the pinned corpus figures (0/25
clean, B at 8538.7×/59.938 Hz, E at 40.21 σ, Compression binding at
0.8546 ± 0.0092) hold on x86-64 as well as arm64, which is the first
independent-platform confirmation any of them has had. Both mutation harnesses
**PASS** on the second platform too.

`regression-estimator-guards` reported COULD NOT RUN: it builds its own clang
sanitizer binary and Ubuntu's clang has no `omp.h` without `libomp-dev`. That
is neither a pass nor a failure and also not a measurement; the package is now
installed in the workflow.

`regression-restart` **FAILED 2 checks**, and the suite prints only each
regression's last four lines, so the cause was not in the artifact — a
truncated failure is not a diagnosis. The workflow now runs it standalone; see
the addendum.

### Addendum — both x86-64 failures diagnosed, and the C23 repair is portable

**The C23 cutoffs are platform-independent, which was the thing most at risk.**
The full standalone log shows every C23 check passing on x86-64: *"both cutoffs
match the exact oracle: 32 H_I values × 2 columns"*, the deciding cutoff above
the printed one at all five widths, the full-entropy 8-bit matrix accepted, and
X_max 24 accepted with both numbers reported. So `exactBound` and `maxCellCdf`
— written in `long double`, and therefore the obvious candidates for a
platform-dependent verdict — give identical integers on a 53-bit and a 64-bit
significand at all 64 pinned points. **`REPRO-01`'s shape does not recur in the
repair.**

**Failure 1 and 2 were both the same thing, and it is a CLI difference, not
arithmetic.** The two failing checks are `N-04 H_I='-inf'` and `N-04 negative
H_I`. An argument beginning with `-` is consumed differently by the two getopt
implementations: **BSD getopt (macOS) stops scanning at the first operand**, so
`-inf` in the H_I position reaches the H_I parser and gets its specific message;
**GNU getopt (glibc) permutes** and keeps looking for options after operands, so
`-inf` is read as `-i -n -f`, `-f` is unknown, and the tool exits through
`print_usage()`. **Both refuse — only the message differs**, so there is no
safety consequence; the expectation had been written against BSD behaviour and
was platform-specific. This is `C21`'s *"BSD getopt stops at the first
positional, so a trailing `-o` makes the run 'Incorrect usage'"* finding seen
from the other side, and it is the second time in this entry that an expectation
travelled worse than the thing it was checking.

The check now requires a refusal and accepts either the grammar message or the
usage path for arguments beginning with `-`, while still demanding the specific
message for every other malformed value. **An owner decision is available and
not taken**: prefixing each `getopt` optstring with `+` disables GNU permutation
and makes argument handling identical on both platforms. That is a one-character
change per tool and strictly better for reproducibility, but it *is* a
behaviour change on Linux — options after the filename would stop being
recognised there, which is already the macOS behaviour — so it is listed in
`CLOSING-INVENTORY.md` under owner decisions rather than made here.

**`regression-estimator-guards` could not run for a second reason**, found only
because the standalone log was uploaded: after `libomp-dev` supplied `omp.h`,
the sanitizer build failed on `json/json.h`. `cpp/Makefile` passes
`-I/usr/include/jsoncpp` for the normal build and this regression's own build
command did not. Added. **Confirmed on x86-64** (`logs/x86-64/`, third run):
`regression-restart` **PASS**, `regression-outside-battery` **PASS**, and the
canary now gives all five outcomes correctly — two REPAIRED, two UNREPAIRED,
one INDETERMINATE.

**One gap remains and it is honest about itself.** After the include path was
added, `regression-estimator-guards` fails at the **link** step on Linux: its
sanitizer build command carries Homebrew library paths and macOS-specific
OpenMP flags, so that regression is macOS-only. It reports **COULD NOT RUN
(exit 2)** rather than passing, which is the designed behaviour — a check that
did not execute supports no claim — and `run-all-checks.sh`'s total-count
check then fails closed, which is also correct. Making that one build command
portable is small and is listed in `CLOSING-INVENTORY.md`. Everything else in
the suite runs on both platforms.

## OC-41 — R-1 diagnosed, scoped and repaired; and the rule the CI run established

### The rule first, because it is the general lesson

**A platform claim established by reading the source is provisional until the
source has been run on that platform, and "we could not reproduce it here" is a
statement about here.** `OC-34` concluded R-1 was not reproducible, from two
sessions' reasoning on one host. One CI run disproved it. Recorded as a rule in
`BUG-REPAIR-GUIDE.md` beside the other three.

### What the assert asserts, and why a wider long double is stricter

`lrs_test.h` computed `p_col = Σ p_i²` and asserted `p_col >= 1/k`. By
Cauchy–Schwarz `Σ p_i² ≥ (Σ p_i)²/k = 1/k`, **with equality exactly at the
uniform distribution**, so the mathematical quantity can never be below `1/k`
and any shortfall is rounding.

The mechanism is the same one the canary work turned on: **`p[]` is accumulated
in `double` by `calc_proportions()` while the threshold `1/k` is formed in
`long double`.** On a wider `long double` the threshold is the *more accurate*
of the two, so the comparison is **stricter** and more alphabet sizes fail. That
is the inverse of the usual expectation and it is why the defect is worse on
x86-64 than on arm64. Worked at k = 3: the double `p` is 0.33333333333333331483,
below the true ⅓; in 80-bit the threshold is 0.3333333333333333333, so the sum
sits below it and the assert fires, while in 53-bit both sides round to the same
value and it does not.

### The blast radius, measured through the production functions

A first harness re-implemented `calc_proportions` and
`calc_collision_proportion` by hand. **It disagreed with the tool** and was
discarded: a re-implementation is not the instrument. The harness now calls the
production functions compiled with the project's own flags
(`reproducers/r1_pcol_sweep.cpp`, `logs/r1/blast-radius-arm64.txt`):

| | |
|---|---|
| alphabet sizes affected at exact balance, arm64 | **117 of 255** (k = 17, 21, 23, 25, 27, 29, 34 … 254) |
| powers of two | **none affected, by arithmetic**: `1/2^j` is exactly representable, so `p = 1/k` exactly and `p_col = k·(1/k)² = 1/k` exactly |
| **width 1** | **unaffected.** It can only yield k = 1, refused earlier, or k = 2 |
| with **one sample** moved off exact balance | **0 of 117 still abort** — `p_col` rises by about `2/L² = 2e-12` against a rounding deficit of order 1e-17 |
| which tools reach it | **`ea_iid` and `ea_restart` only.** `ea_non_iid` never calls `len_LRS_test` |

**Reproduction and repair, both demonstrated at the function level on arm64**:
calling the production `len_LRS_test` directly at k = 17 and k = 25 aborts on
the tag tree (`Assertion failed: (p_col >= 1.0L / ((long double) k))`,
`lrs_test.h:652`) and returns normally on the repaired tree.

**The end-to-end gap is closed — see `OC-42`.** It was my own instrument error:
the arm64 "could not reproduce" came from running the tag worktree's `-DNDEBUG`
binary, left there by the canary tests, with the assert compiled out. With
asserts live the end-to-end run aborts on arm64 too. **The end-to-end radius is
the function-level set**, platform by platform.

### What an operator sees, and the direction

`ea_iid` or `ea_restart -i` dies with SIGABRT, exit 134, and **writes no
report**. The direction is fail-closed: the tool refuses rather than publishing
a wrong figure. But it refuses **valid data**, so a sound dataset is denied an
assessment, and on the affected platform-and-alphabet combinations a validation
tool is unusable for it. That is worth saying plainly rather than as a
rounding-sensitivity note. What keeps the practical exposure small is the
**exact-balance** requirement: real noise never produces exactly equal counts,
while a counter-mode or round-robin source, or a constructed test vector, does
so reliably — so the realistic victims are test corpora and deterministic
sources, which for a validation tool is still a real problem.

**Upstream and platform-specific.** The assert is upstream code and
`calc_collision_proportion` is unchanged from upstream (`git log -S` shows only
upstream's own commits), so a reader on Linux is looking at an inherited defect,
not one this fork introduced. Nothing is sent upstream (decided 2026-10-15).

### The repair, and why it cannot move a figure

The assert is replaced by a clamp to the proven bound, with the Cauchy–Schwarz
justification at the site. It is **exact, not a tolerance**: it substitutes the
value the mathematics requires for an abort. It **cannot change any published
figure**, because `p_col` feeds only the §5.2.5 LRS decision and every affected
case previously produced no figure at all — there is nothing to change. That is
the test the decision turned on. Self-authored and unreviewed, like every repair
here.

### Task 3's sweep: guards coupled to the host's wording

`OC-40` found the canary matching macOS's phrasing of an assertion failure,
which on Linux produced a **false third outcome** — INDETERMINATE for a
legitimately unrepaired binary, which looks like honesty and is not. Swept every
guard that matches runtime-emitted text. **Two existed**, and both are now
structural first:

| site | was | now |
|---|---|---|
| `tools/build-provenance-canary.sh` | the literal `"Assertion failed"` | exit status 134 **plus** wording-independent confirmation; fixed in `OC-40` and verified against both libcs |
| `regression-estimator-guards.sh:170` | `rc == 134` **or** the literal `"Assertion failed"` | the structural signal (exit 134, which is the thing being detected) with the text as wording-independent secondary confirmation |

Nothing else in the project matches libc error strings, compiler diagnostics,
signal descriptions or locale-sensitive formatting for a verdict.

**Keep the distinction `OC-40` drew**: the arithmetic argument held at exactly
the predicted site. The model was right and the instrument was parochial.

### Task 5: the Linux job can now run the whole suite

`regression-estimator-guards` built its sanitizer binary with Homebrew paths and
the macOS OpenMP flag form, so on Linux it reported COULD NOT RUN and the
suite's count check failed closed — both correct, and both leaving the Linux job
unable to run the suite that had just found three things. The build now detects
its platform the way `cpp/Makefile` does. **"Could not run" is never counted as
a pass**, which is why the count check failing was the right behaviour and why
it had to be fixed rather than excused.

### Task 6: the workflow runs on every push

Promoted from manual-only. The class it detects — a claim true only on the
development host — is invisible from that host by construction.

## OC-42 — the end-to-end gap was a stale NDEBUG binary; the corpora are clean; and what Windows would cost

### Task 2 — the gap, explained by instrumenting rather than reasoning

`OC-41` reported that the production `len_LRS_test` aborts on arm64 at k = 25
when called directly, while the end-to-end `ea_iid` run did not, and bounded
the radius by measurement rather than explaining it. Instrumented the call site
on a scratch copy (never committed) to record what the function actually
receives:

```
[TRACE] len_LRS_test k=25 L=1000025 nonzero=25
        p_min=p_max=0.040000000000000000833
        p_col=0.0399999999999999938938  thr=0.0400000000000000008327  WOULD_ABORT=1
```

So the end-to-end path presents **exactly the violating values** — all 25
proportions equal, `p_col` below the threshold. None of the three candidate
explanations applies: the path does present equal counts, nothing upstream
perturbs or clamps them, and it does reach k = 25.

**The gap was mine.** The arm64 run I compared against was the tag worktree's
`-DNDEBUG` binary, left in that worktree by the canary tests, with the assert
compiled out. Rebuilt with asserts live, the same input on the same host gives
`rc=134`, `Assertion failed: (p_col >= 1.0L / ((long double) k)), lrs_test.h:652`.

The instrument built for exactly this question would have said so immediately:
run against that binary, the provenance canary reports `BUILD NDEBUG`. I did not
run it. **That is this round's instrument error, and it is the fourth of its
kind to be a stale or mis-built artefact rather than a wrong idea.**

**Consequences.** R-1 is reproducible end-to-end on **both** platforms; only the
*set of affected alphabet sizes* differs — 117 of 255 on arm64, 155 of 255 on
x86-64. The end-to-end radius is the function-level set, and `OC-41`'s caveat is
withdrawn. The repair is unaffected and still demonstrated against the tag on
both.

### Task 3 — the fork's own evidence sets, scanned

R-1 needs exactly equal counts, which makes **constructed** data the exposed
case — and constructed data is what this project's corpora are. Scanned with
`reproducers/r1_corpus_scan.py`, which checks every file for exactly equal
counts and tests the observed alphabet size against both platforms' measured
affected sets (`logs/r1/corpus-scan.log`):

| | |
|---|---:|
| files examined | **57** |
| exactly balanced | **7** |
| would abort on some platform | **6** |

**All six are the R-1 reproducers themselves** — `bal3`, `bal6`, `bal7`,
`bal9`, `bal12` (x86-64) and `bal25` (arm64) — which exist in order to be
exposed. The seventh balanced file is the checkerboard restart matrix at k = 2,
safe by the power-of-two argument.

**Nothing in the fork's committed evidence is exposed**: the eleven reference
fixtures under `bin/`, the 31 outside-battery calibration streams (1-bit,
k = 2), the forced restart matrices (column 17 forced, so counts are not equal),
and the uniform test matrices are all either not exactly balanced or at a
power-of-two alphabet. **The answer is none**, and the count is stated beside
it. One generator to watch: `generators/c07_lrs_fixtures.py` builds `bal<k>.bin`
for k ∈ {20, 25, 32, 40, 50, 64, 100, 125, 200, 250} deliberately — those are
C07 site-A reproducers and are the same family; they are inputs to a regression
that expects a refusal, not evidence anything reads a figure from.

### Task 5 — what Windows would cost, and the question that decides whether it matters

**Assessment only. No Windows work started**, per instruction.

**Does it build today?** Unknown, and that status is now explicit: nothing in
`BUILDING.md`'s Windows section has ever been run anywhere. What can be said
from the source:

| | |
|---|---|
| **MinGW-w64 / MSYS2 UCRT64** | the plausible route. The code needs `getopt.h` (5 sites), `unistd.h`, `signal.h`, `sys/stat.h`, `__int128`, `__builtin_inf`, VLAs and `<omp.h>` — all GCC features MinGW provides. `uname -s` reports `MINGW64_NT-…`, so the Makefile takes its non-Darwin path unchanged. |
| **MSVC** | not a route without source work: no `getopt.h`, no `unistd.h`, and the GCC builtins and VLAs are unavailable. |
| **a dependency that is not packaged** | `libdivsufsort` must be built from source for Windows; `jsoncpp`, `bzip2` and OpenSSL are packaged for MSYS2. |

**`BUILDING.md`'s claim that the MSYS2 route "needs no source changes" is
wrong, and this is a defect found without running anything.** `seed()` at
`utils.h:795` opens **`/dev/urandom`** and calls `exit(-1)` if it cannot. A
native MinGW/UCRT64 binary has no `/dev/urandom` — the MSYS2 POSIX emulation
layer does, but binaries built for UCRT64 do not use it. `seed()` is called from
`permutation_tests.h:606` and `restart_main.cpp:298`, so **`ea_iid` and
`ea_restart` would exit at the permutation stage on Windows while `ea_non_iid`,
which never calls it, would run.** A Windows port therefore needs a seeding
source (`BCryptGenRandom`, or `std::random_device`), which is a source change to
an entropy-relevant code path and so an owner decision in its own right.
`BUILDING.md` is corrected to say so.

**What R-1 would do there.** On **MSVC** `long double` is the same width as
`double`, so the precision asymmetry behind R-1 does not arise and the affected
set would be empty or near it. On **MinGW** `long double` is x87 80-bit, so it
would behave like Linux — the 155-size set. Either way the fork's clamp removes
it; this is about what an *unrepaired* Windows build would do.

**Cost, if the answer to the next question is yes:** a `windows-latest` job is a
workflow file like the Linux one, *provided* the build succeeds — so the honest
estimate is one session to attempt the MSYS2 build in CI and find out, plus
whatever the `/dev/urandom` change turns out to require, plus a decision about
making that change at all. If the build fails for a reason not listed above,
that is unbounded and should be re-estimated then rather than guessed now.

**The question for the owner, which is not mine to answer.** TruePad's desktop
app targets Windows and Mac. **If its harness ever invokes these tools on a
user's Windows machine, the Windows build is a product requirement**, and the
`/dev/urandom` failure means `ea_iid` and `ea_restart` do not run there at all
today. **If the tools only ever run on the owner's own machine for
qualification, Windows is moot** and the bucket closes as will-not-be-done. This
session cannot answer it: it is a question about TruePad's deployment, and
reading TruePad is out of scope.

## OC-43 — build state as a printed precondition, and the rule R-1 actually belongs under

### The rule, restated under its own heading

`R-1` was filed as the worked example of "a platform claim from reading the
source is provisional until it has been run there". **That filing was wrong.**
The rule is good and stays — its real worked example is the canary's fourth
signature (`OC-40`), where the reasoning held and the instrument did not — but
nothing about the platform hid `R-1`. **A build state did.** Filing a false
example under a true rule is worse than having no example, because the next
reader reasons from the example.

The rule `R-1` belongs under, now rule 4 in `BUG-REPAIR-GUIDE.md`:
**a measurement is about the artefact it ran against, and an artefact whose
build state was not established is not evidence about the source.** Four
instances, none of them a wrong idea — the `-DNDEBUG` binary (`OC-42`), the
missing input files (`OC-30`), the file whose `sed` missed (`OC-23`), and the
hand re-implementation standing in for the production functions (`OC-41`).

### Mechanised rather than remembered

The principle, in full: **a rule that depends on a person remembering it will
be forgotten at the rate this project forgets things, so it is built into an
instrument that fails when the rule is broken.** (Cited as `RULE 12`, a rule
number with **no definition in this repository**; see `OC-68`.)

`cpp/selftest/buildstate-lib.sh`. The probe is structural: `assert` leaves an
undefined symbol (`__assert_fail` on glibc, `___assert_rtn` on Darwin) in any
binary built without `-DNDEBUG` and none in one built with it — a linker
symbol, not emitted text, so it works for all three tools and survives the
source changing. The canary is stronger where it applies, because it also
separates the repaired tree from the unrepaired one, but it classifies `ea_iid`
only.

| function | what it does |
|---|---|
| `bs_print <binary>…` | one `[build-state] <name> asserts=LIVE\|NDEBUG sha256=…` line per binary, **before** the results, so a result without it is visibly incomplete. A missing binary prints `MISSING — no measurement against this binary is interpretable` |
| `bs_require <binary> LIVE\|NDEBUG` | for a measurement that deliberately uses a particular build: declares it and **refuses** a mismatch with exit 2 |
| `bs_canary <ea_iid> REPAIRED\|UNREPAIRED` | adds the canary's tree verdict where it applies |

Wired into every harness that draws a conclusion from running a tool binary:
`pin-check.sh` (the project's highest-value claim), `regression-restart.sh` and
`regression-output.sh` (both accept a build override, which is exactly how
`OC-42` happened), `reproducers/c16-c23-matrix.sh` (five variants, each
printed beside its digest) and `reproducers/build-differential.sh`.

**`build-differential.sh` gains a real guard from this, not just a line.** Its
whole claim is that two *different* builds agree, so running it against two
copies of the same build would "pass" and mean nothing. It now declares `LIVE`
and `NDEBUG` and refuses: shown refusing when handed the same binary twice.

### The sweep of conclusions already on the record

Of the 71 measurement logs under `logs/`, **10 record a build state** — the
eight canary logs under `logs/merge/` and two under `logs/x86-64/`. So the
great majority did not establish it, and the honest reading of that number is
narrower than it looks:

- **Most were produced by a binary `make` had just built in the repository
  tree, where no Makefile target sets `-DNDEBUG`**, so asserts-live is the
  default and the artefact was what it seemed.
- **The exposure is confined to runs against a shared worktree** — the tag
  clone — where earlier work can leave a different build. That is
  `logs/c23/regression-restart-vs-tag.log`,
  `logs/c14/regression-output-vs-tag.log`, `logs/c08/diagnosability.log` and
  the `logs/ndebug/` pair.
- **Of those, only one conclusion could have been wrong, and it was.** The
  others compare error messages, report fields, cutoffs and parse behaviour —
  none of which is assert-dependent, so an `-DNDEBUG` binary would have given
  the same answer. `R-1`'s was the assert-dependent one, and it was wrong and
  is corrected.

**Count: one invalidated conclusion, found and corrected; the rest
re-measurable but not in doubt.** The two vs-tag regression logs have been
re-run so they now carry their build-state lines, which is the cheap half of
making the record complete.

### Cleaning up after a worktree

The committed scripts that build an `-DNDEBUG` binary already restore the tree
afterwards — `c16-c23-matrix.sh` ends with `make -B restart`, and the CI job
rebuilds live after its NDEBUG step. The `-DNDEBUG` binary that caused `OC-42`
was left by interactive work, not by a script. What now prevents a repeat is
the precondition itself: the harnesses that can be pointed at a worktree print
what they found there, and `bs_require` refuses a build that is not the one the
measurement needs.

## OC-44 — the deliberately-balanced fixtures: who reads them, and a label at the definition

`OC-42`'s corpus scan flagged `generators/c07_lrs_fixtures.py` as building
exactly-balanced inputs, which is the condition that trips `R-1`. Closing that
loop.

**Who consumes them: nothing that reads a figure.** The only references to
`bal<k>.bin` anywhere in the project are the `R-1` and `C07`-site-A
*reproduction recipes* — `audits/2026-09-30/FINDINGS-TRACKER.md`'s reproduce
block, the 2026-09-30 novel-findings report, and that dimension's agent report.
No regression script, no pinned figure and no document reads an estimate
derived from them. **So the answer is none**, and that is the end of it: there
is nothing to re-check against the repaired build.

**Labelled at the definition**, because a future reader would otherwise take
them for ordinary multi-symbol test data: the generator's docstring now says
that these files trip `R-1` by construction, that the affected alphabet sizes
differ by platform (k ∈ {25, 100, 125, 200, 250} on arm64, k ∈ {3, 6, 7, 9, 12}
on x86-64), that moving one sample off balance removes the abort at every k,
and that any new consumer needs a binary carrying the `OC-41` repair and should
print its build state first.

## OC-45 — the build-state probe moved the parochialism one layer down; now it calibrates or refuses

`OC-43`'s probe matched an undefined symbol instead of `assert`'s message text,
which is a real improvement — structural rather than textual, so it survives the
source changing and works for all three tools. **But the symbol name is itself
platform-specific**: `__assert_fail` on glibc, `__assert_rtn` on Darwin and the
BSDs, `_wassert` on MSVC. A probe keyed on a name list can fail exactly the way
the message-text canary failed, one layer down — and worse, **silently**, because
"no symbol I recognise" would have been reported as a confident `NDEBUG`.
Absence of a symbol it was not looking for is no answer at all.

**The probe now calibrates itself on the host before any verdict is trusted.**
It compiles two tiny programs, one with a reachable `assert` and one with
`-DNDEBUG`, and requires its pattern to match the first and not the second.
`NDEBUG` is returned only when that discrimination has been demonstrated *and*
`nm` produced undefined symbols to look through; a stripped or unreadable
binary is `UNKNOWN` too. If calibration fails — no compiler, no `nm`, an
unfamiliar naming scheme — every verdict is `UNKNOWN` and `bs_require`
**refuses**. That is the canary's INDETERMINATE rule applied one level down: a
probe that cannot establish its answer reports that it cannot.

**Both paths shown on this host:**

```
[build-state] calibration: OK -- pattern /assert/i discriminates;
              asserts-live symbol here is ___assert_rtn
[build-state] ea_iid              asserts=LIVE    sha256=2ccff357fd30950c
[build-state] ea_iid.tag.ndebug   asserts=NDEBUG  sha256=7e6afd4735d60f59

# with the pattern forced to something this host does not use:
[build-state] calibration: FAILED -- pattern /zzz_nope/i does NOT discriminate
              (live=0 ndebug=0); the symbol is named something this probe does not know
[build-state] ea_iid              asserts=UNKNOWN sha256=2ccff357fd30950c
[build-state] REFUSED: the build state of cpp/ea_iid CANNOT BE ESTABLISHED here.
```

**The real test is a platform it has never met**, which is why
`.github/workflows/windows-platform-facts.yml` runs the probe on Windows and
gates on it: calibrating and giving a verdict passes, failing to calibrate and
refusing also passes, and **concluding anything without calibrating fails** —
a defect that would outrank the Windows question itself.

## OC-46 — the sweep's unchecked premise, checked: asserts are the only thing NDEBUG changes here

`OC-43`'s sweep concluded that of the 61 logs without a recorded build state
only one conclusion could have been wrong, because the rest compare messages,
report fields, cutoffs and parse behaviour, **none of which is
assert-dependent**. That is the right kind of argument — about the nature of the
conclusion rather than about the build — and it rested on one premise nobody had
verified: *that asserts are the only thing `NDEBUG` changes in this source.*

**Checked, and it holds.** Grepping the whole tree for `#ifdef NDEBUG`,
`#ifndef NDEBUG` and `#if defined(NDEBUG)`:

| | |
|---|---:|
| NDEBUG conditionals in the C++ source | **0** |
| `assert()` call sites | **98** across 12 files (**84** in the three supported tools; 14 are in `conditioning_main.cpp`, which is not built) |
| reliance on standard-library debug modes (`_GLIBCXX_DEBUG`, `_LIBCPP_DEBUG`, `_ITERATOR_DEBUG_LEVEL`) | **none** — the project neither sets nor reads them |
| `static_assert` | 1, in `compression_test.h` — compile-time, unaffected by `NDEBUG` |

Every other mention of `NDEBUG` anywhere in the repository is in a shell
script, a workflow file, a comment, or the three audit-only build knobs. So
**`NDEBUG` reaches `assert()` and nothing else here**, the premise is verified
rather than plausible, and the sweep's conclusion stands as written: one
invalidated conclusion, `R-1`'s, found and corrected.

## OC-47 — `oac-13`: the report write is atomic, and the truncation window measured before and after

The last item in `C08`, and the last software item on the list.

**The failure mode, concretely.** `writeJsonReport` opened the operator's `-o`
path and streamed into it, so a signal, a full device or an I/O error part-way
through left **truncated JSON at that path** — syntactically invalid, and a
consumer that checks the exit status and then reads the file either parse-fails
or reads a prefix. `C14`'s placeholder (`OC-31`) narrowed the window from "a
stale *valid* report" to "an invalid one", which a consumer can at least detect
by parsing, but did not close it.

**Could anything downstream consume one?** Yes, and that is why it matters:
`XR-01` establishes that TruePad's harness checks the exit status and then reads
the `-o` file. A truncated report is detectable by a consumer that parses before
trusting; one that does not parse first could read a prefix. On the fork's own
side nothing consumes a report file this way.

**The repair.** The content goes to a sibling temporary file, is flushed and
checked, and only then `rename()`d over the target. `rename(2)` within a
directory is atomic, so the path a reader opens holds either the previous
content or the complete new content and never a prefix. The temporary is removed
on every failure path, so a failed write leaves no debris beside the operator's
file. It must be a **sibling**: `rename()` across filesystems fails, and a
temporary in `/tmp` would silently reintroduce a non-atomic copy. That also
preserves the existing failure behaviour — an unwritable directory or `/dev/full`
fails at the temporary, which is still a failed run, and the regressions that
assert those failures pass unchanged.

**Shown failing, measured both ways** (`reproducers/atomic_report_write.cpp`
compiles both implementations; a known-good report is pre-placed, a 400 MB
report written over it, and the writer killed after 120 ms;
`logs/c08/atomic-write.log`):

| implementation | runs leaving a COMPLETE document | runs leaving a TRUNCATED one |
|---|---:|---:|
| old (stream into the target) | 1 of 5 | **4 of 5** |
| new (temporary + rename) | **5 of 5** | 0 of 5 |

The new implementation also left no temporary behind in any run. **`C08` is now
closed in full**, and with it the last item in the first bucket of
`CLOSING-INVENTORY.md`.

---

## OC-48 — Windows, measured: `windows-latest`, six runs, and what each run's instrument got wrong

**The question, and why a workflow rather than a machine.** Everything the
project said about Windows was an argument from reading the source.
`BUILDING.md`'s Windows section had never been run anywhere. Four claims were
worth replacing with measurements, and a manually-triggered GitHub Actions job
on `windows-latest` can take all four without anyone owning a Windows machine:

1. does every library the `Makefile` links have a `mingw-w64` package?
2. does the source compile, per tool?
3. what is the float environment — and is the `R-1` affected set 155 of 255, as
   the x87 80-bit prediction says it must be?
4. what happens at **runtime**: `OC-42` predicts `ea_non_iid` runs while
   `ea_iid` and `ea_restart` die at `seed()`, which opens `/dev/urandom`.

And one more that **outranks all four**: Windows is a platform
`cpp/selftest/buildstate-lib.sh` has never met, so this is the test of whether
it **refuses** rather than reading "no symbol I recognise" as a confident
`NDEBUG`. Changing no source was a precondition throughout: fixing `seed()`
means touching an entropy-relevant path, and that stays gated on the owner.

### The premise, checked against the runner rather than taken on trust

MSYS2 **is** preinstalled, at `C:\msys64`, with `pacman`, and the job detects it
rather than depending on an action pin it could not verify. If it were absent the
job says so and stops, because a job that fails on an unverifiable pin fails for
a reason unrelated to the Windows question.

### What is now measured

| | measured on `windows-latest` |
|---|---|
| MSYS2 | preinstalled, `C:\msys64`, gcc 16.2.0 (Rev6, MSYS2) |
| `libdivsufsort` | **no `mingw-w64` package**, under any of four candidate names. `BUILDING.md` is right. |
| `libgomp` | packaged, in `mingw-w64-x86_64-gcc-libs`, which the preinstalled toolchain does **not** pull in |
| every other `Makefile` dependency | packaged |
| `ea_non_iid`, `ea_iid`, `ea_restart` | all three **compile and link** natively, with OpenMP |
| `sizeof(long double)` | 16 |
| `LDBL_MANT_DIG` | **64** — x87 80-bit extended, as predicted for MinGW |
| `LDBL_MIN` / `LDBL_TRUE_MIN` | 3.3621e-4932 / 3.6452e-4951 |
| `FLT_EVAL_METHOD` | 0 |
| `sizeof(long)` | **4** — LLP64. This is `C18`'s precondition, confirmed. |
| `R-1` affected set | **155 of 255**, the x87 prediction **confirmed** on a third host |
| `R-1` powers of two | all safe (2 … 256) |
| `R-1` at width 1 | unaffected: width 1 gives only k=1 (refused earlier) or k=2 |
| `R-1` fragility | 0 of 155 still abort with one sample moved off exact balance |
| `ea_non_iid` at runtime | runs the **whole non-IID battery to completion**, exit 0 |
| the build-state probe | **refused** correctly, then was taught PE/COFF and now **calibrates and gives a real verdict** |
| §5.2.5 LRS test | **FAILS unconditionally** on standards-sized input: `C18`, measured |

So `R-1` is not an x86-64 defect and not a Linux defect: it is a **long double
format** defect, and the same 155 alphabet sizes abort on Apple arm64's absence
of the problem, Linux's x87, and Windows's x87. The restatement in
`audits/BUG-REPAIR-GUIDE.md` is now carried by three measured hosts.

`C18`'s precondition — `long` is 32 bits on Windows where it is 64 on the
project's other targets — is measured rather than assumed.

### The finding that is about a repair this audit wrote

All three tools, having run, failed at **`cpp/shared/TestRunUtils.h:79`** — the
`rename()` branch of the atomic report write added for `C08` (`OC-47`):

```
Error: could not put the report in place at 'C:/msys64/tmp/n.json'.
```

The temporary file was created and written; placing it failed. POSIX
`rename(2)` **replaces** an existing destination atomically, which is the whole
basis of `OC-47`'s argument; Windows `rename()` is not specified to, and
`MoveFileEx(..., MOVEFILE_REPLACE_EXISTING)` is the platform primitive. So a
repair justified by a POSIX guarantee was carried to a platform that does not
give it, and **running it somewhere new is what found that** — no amount of
re-reading the diff would have. The job now measures the cause rather than
arguing it: each tool writes a report twice over the same path, and a
standalone probe mimicking those exact lines prints `errno` for both an absent
and an existing destination. On macOS that probe reports `rc=0` for both, which
is the positive control.

### Six runs, and the instrument defect each one exposed

Every run in this sequence failed for a different reason, and each named the
next precisely. The point is not that the script was wrong six times; it is that
**a gate that cannot distinguish two causes will report the one it was written
for**, and the only way to find that is to run it somewhere it does not already
agree with you.

| run | what failed | the defect, and the rule it broke |
|---|---|---|
| 1 | three gates wrong at once | `"does NOT compile"` conflated **a missing header** with source incompatibility; `"no tool died at seed(): prediction BROKEN"` concluded from absence **with no binary present** — the absence rule (`OC-36`), broken inside the workflow that applies it; `python3` assumed on `PATH` |
| 2 | nothing new | a `git commit` **silently failed**, so the run used the un-pushed script and repeated run 1's verdicts. A result from an artefact you did not push is not a result. |
| 3 | `cmake` policy error | `libdivsufsort`'s `CMakeLists.txt` requires a policy version modern CMake refuses; `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 4 | `CMAKE_MAKE_PROGRAM is not set` | the `MinGW Makefiles` generator wants `mingw32-make`; the Unix generator with MSYS2's own `make` is the simpler correct choice inside the MINGW64 shell |
| 5 | **two gates contradicting each other in one verdict log** | `"the OpenMP runtime ships with the toolchain"` was concluded from `find /mingw64 -name 'libgomp*'`, which matched exactly one file: `/mingw64/lib/libgomp.spec`. A spec file is not a library. The same glob then told the `R-1` stage to keep `-fopenmp`, and that link failed with `cannot find -lgomp` **in the same run**. Concluding from a signal weaker than the question. The test is now a **link** test. |
| 5 | the `seed()` gate measured the wrong thing, and said so | every tool had died at a later step for an unrelated reason, and `-q` had suppressed every progress marker the classifier looks for. The gate reported `"read the log before concluding anything"` — the rule working — but the measurement was still of the wrong thing. The two questions are now **separate passes**: pass 1 runs with no `-o` and verbose, so nothing but `seed()` and the battery is in the path. |
| 6 | **the probe was defeated by a filename** | calibration compiled `-o $d/live`; MinGW gcc wrote `$d/live.exe` and returned 0. `nm` on a missing file reports no symbols, which is **indistinguishable from "the pattern does not discriminate here"** — so it refused, in the same shell where the diagnostic beside it showed the full listing discriminating 2 to 0. Right outcome, wrong reason. |
| 6 | the `rename` probe did not compile | its C source lost a `\n` to the generator that wrote it, leaving an unterminated string literal. It measured nothing and reported that it had measured nothing. |
| 6 | `head -30` | cut every run off before its end, so `ea_iid`'s exit 1 at the chi-square stage was unreadable and the figure markers never matched |

Three of those — run 1's absence-rule break, run 5's contradiction, run 6's
filename — are the same error at three different depths: **a measurement
reporting on something other than what it was asked about.** That is the error
this whole audit exists to catch, and the Windows job caught it in itself three
times.

### The probe: it earned its keep twice, and is now taught the platform

It **refused** on Windows rather than guessing, which is what it was built to
do. And the diagnostic printed beside the refusal **measured that an extension
exists**: on PE/COFF a linked `.exe` resolves imports through an import table,
so `nm -u` is blind, while a full listing discriminates —

```
nm cal_live.exe | grep -i assert  ->  __imp__assert, _assert   (2)
nm cal_nd.exe   | grep -i assert  ->                           (0)
```

So the platform can be taught, and that is an **improvement, not a
correction**: refusing was right. It is taught as a **calibrated fallback,
never a replacement**. The undefined-symbol listing is tried first, because
nothing unrelated can masquerade as an undefined symbol; the full listing is
weaker — any symbol whose name merely contains `assert` would read as `LIVE` —
so it is only ever the fallback, it must pass the same calibration, and every
line produced through it is marked `via=full` so a reader can see which
question was answered. Verified three ways:

| control | required | observed |
|---|---|---|
| macOS, unchanged | `undefined` mode, byte-identical output | `undefined`, `___assert_rtn`, no `via=` field |
| undefined listing forced blind, as PE/COFF is | fall back, discriminate, label itself | `full` mode, `LIVE` vs `NDEBUG`, `via=full` on both lines |
| **both** listings blind | `UNKNOWN`, and `bs_require` refuses | `UNKNOWN`; `bs_require` exits 2 |

Calibration now also resolves the artefact **with the tool that will read
it**, and that detail took two attempts worth recording. MinGW gcc appends
`.exe` when `-o` carries no suffix, so the first attempt resolved the name with
`[ -f ]` — and the MSYS runtime resolves `live` to `live.exe` for `stat()`, so
the shell said the bare name existed while native `nm`, handed the same string,
looked for a Win32 path that was not there and printed nothing. With stderr
suppressed that is **indistinguishable from "this pattern does not
discriminate"**, which is what it reported. `BS_DEBUG` printed the
contradiction in a single block: `ls` listing `live.exe`, the resolver claiming
`live`. The resolution test is now the use — pick the candidate `nm` can read,
and if it can read neither, say so and quote what `nm` said.

**Result:** the probe now **calibrates on Windows and gives a real verdict.**

```
calibration: OK -- pattern /assert/i discriminates in the full-symbol listing;
  asserts-live symbol here is 0000000140007198 I __imp__assert
  -- NOTE: the undefined-symbol listing is blind on this platform (PE/COFF),
     so this is the weaker full-listing test
ea_iid.exe       asserts=LIVE  sha256=924e575672ca38d6  via=full
```

Build state is therefore establishable on all three platforms the fork has
measured, and on the one where the weaker test was needed, every line says so.

### `seed()`: what it took to ask the question at all

`OC-42` predicts `ea_non_iid` runs while `ea_iid` and `ea_restart` die at
`seed()`, which opens `/dev/urandom` and calls `exit(-1)`. Three separate
instrument faults stood between the job and that question, and each one
produced a confident wrong gate before it was found:

1. **A gate reading a per-tool prediction out of a whole log.** It declared the
   prediction BROKEN because "a tool produced a figure" — and the tool that did
   was `ea_non_iid`, which `OC-42` predicts **runs**. Each tool is gated
   separately now.
2. **An input that could not reach the stage under test.** The generator was an
   LCG mod 2³² emitting bit 16, and bit 16 of such an LCG has period
   2¹⁷ = 131072. `ea_iid` duly reported a longest repeated substring of
   **868928 = 1000000 − 131072**, failed the LRS test, and printed `** Skipped
   IID permutation tests after an earlier required IID test failure`. `seed()`
   is called **in** the permutation stage. Replaced with splitmix64 bit 0,
   verified locally first: LRS length 40, chi square passed, permutation tests
   reached and passed.
3. **An extraction pattern that ended its range at the first blank line**, and
   the runs' own output contains blank lines, so every tool's "how far" came
   back empty and the gates read that as "reached neither".

And then the replacement input **still** did not reach `seed()` — for a reason
that turned out to be the most important thing in this whole exercise. See
`C18` below.

So `OC-42`'s first half is confirmed — `ea_non_iid` runs the complete non-IID
battery and produces a figure — and the second half remains **UNTESTED on
Windows, not refuted**: the permutation stage is unreachable there for any
standards-sized input, because `C18` makes the LRS test fail first.

### And the finding that was hiding behind it: `C18`, measured

`ea_iid` and `ea_restart` failed the §5.2.5 LRS test on an input macOS passes,
with the **same** `P_col` and the **same** LRS length, printing a **negative
probability**:

| host | `P_col` | LRS | `Pr(X >= 1)` | verdict |
|---|---|---:|---:|---|
| macOS arm64 (LP64) | 0.500000 | 40 | **+0.365370** | `** Passed` |
| Windows MinGW (LLP64) | 0.500000 | 40 | **−0.000367** | `** Failed` |

`C18` has been a source-only candidate since the clustering phase:
*"`n_choose_2` computes N = C(L−W+1, 2) in `long int`, which overflows for
large L on LLP64 targets (Windows) and **would** corrupt the §5.2.5
decision."* It does. `cpp/shared/utils.h:997` computes `((n*n) - n) / 2` in
`long int`, and for n = 999961 the product alone is 999,922,001,521, so on a
32-bit `long`:

| | |
|---|---:|
| true N | 499,960,500,780 |
| N as 32-bit `long` | **−403,189,204** |

`reproducers/c18_llp64_overflow.c` reproduces the printed value **exactly**
from the integer arithmetic alone, with no floating-point platform difference
involved:

```
CORRECT    Pr(X>=1) = 0.365369   threshold = -33.8451   decision = PASS
WINDOWS    Pr(X>=1) = -0.000367   threshold = nan       decision = FAIL
```

**And the decision is worse than the printed probability suggests.** The
verdict at `lrs_test.h:765-766` is

```
logCollisionPower >= logl(-expm1l(logl(0.999L) / (long double)N))
```

A negative N makes `logl`'s argument negative, so the threshold is **NaN**, and
every comparison against NaN is false. The LRS test therefore returns **FAIL
unconditionally, whatever the data**.

**Direction: fail-closed throughout.** A wrapped N is always smaller in
magnitude than the true one, so `Pr(X >= 1)` is understated and the test errs
toward rejection. It **denies** an assessment; it never awards one it should
not, and no published figure is wrong. But the overflow begins around
L − W + 1 = 46,342, and 1,000,000 is the standard input size, so **every
standards-sized assessment on Windows is affected**. Not reproducible on Linux
or macOS — both LP64, `long` is 64 bits — which is exactly why the x86-64 CI
job never saw it.

A standing gate now reads the **sign** of `Pr(X >= 1)`, which no correct
probability can have, and reports UNMEASURED rather than PASS when no such line
was printed.

**Deviations, both labelled.** `libdivsufsort` is built from source, which is
the route `BUILDING.md` already documents, not a package. A serial link via a
two-line link-time shim was written for the case where `libgomp` could not be
found; the link test showed it was packaged, so **the shim was never used**.

**`BUILDING.md`'s Windows section is no longer unverified.** Its central claim —
`libdivsufsort` is the one unpackaged dependency — is confirmed, and two facts
it does not mention are now measured: the preinstalled toolchain needs
`mingw-w64-x86_64-gcc-libs` for OpenMP, and `libdivsufsort`'s `CMakeLists.txt`
needs both a policy override and a generator that is not `MinGW Makefiles`.

---

## C24 — the atomic report write is not portable: `C14`'s placeholder makes every later `C08` write fail on Windows

**Status: OPEN. Not repaired, because this round forbids source changes. The
repair is identified below.** This is a defect **in two repairs this audit
authored**, found by running them on a platform they had never run on.

**Where.** `cpp/shared/TestRunUtils.h:55-80`, `writeJsonReport()`.

**The two repairs, each sound on its own.**

- `C14` (`OC-31`) **claims** the `-o` path the moment it is parsed, writing a
  placeholder, so that a harness checking the exit status and then reading the
  file cannot be handed the *previous* run's complete, `errorLevel`-0 figure.
- `C08` (`OC-47`) writes every report to a **sibling temporary** and `rename()`s
  it over the target, so a reader never sees a truncated prefix.

`C08`'s whole justification is that **`rename(2)` replaces an existing
destination atomically**. That is POSIX. It is not Windows.

**Measured, on `windows-latest`, MinGW gcc 16.2.0:**

| case | result |
|---|---|
| `rename()`, destination absent | `rc=0` |
| `rename()`, destination **exists** | **`rc=-1  errno=17 (File exists)`** |

and then the same three cases through a verbatim copy of
`TestRunUtils.h:55-80`:

| case | Windows | macOS (control) |
|---|---|---|
| 1. first write to a fresh path — *the `C14` placeholder* | **OK** | OK |
| 2. second write over it — *every later report* | **FAILED, `errno=17`** | OK |
| 3. single write to a fresh path | OK | OK |

**So the interaction is the defect, not either repair.** `C14` guarantees the
destination exists before any real report is written, and `C08` then guarantees
that writing it fails. Each is correct under its own assumptions; jointly, on
Windows, **no tool can ever write a report**:

```
Error: could not put the report in place at 'rep_iid.json'.
```

All three tools reproduce it, and they reproduce it even when the operator's
`-o` path did not exist beforehand — which is what made it look at first like
something other than `rename()` semantics.

**Severity.** It cannot produce a *wrong figure*: the failure is loud, on
stderr, and the report is absent rather than stale or truncated. A Windows
operator simply cannot get a `-o` report at all. The tools' own assessment
output on stdout is unaffected, as is every figure. So this is availability on
one platform, not integrity on any — but it would make the fork unusable with
`-o` on Windows, and `XR-01` establishes that TruePad's harness reads the `-o`
file.

**The repair, when a source change is authorised.** On Windows the primitive
that is specified to replace is `MoveFileEx(..., MOVEFILE_REPLACE_EXISTING)`,
which is atomic for the reader. A portable `writeJsonReport` wants that under
`_WIN32` and `rename()` elsewhere. The tempting one-liner — `remove(path)`
before `rename()` — must be **refused**: it reopens exactly the window `C08`
closed, during which the path does not exist at all, and it would be a
regression justified by convenience.

**What this item is really evidence of.** Two repairs were reviewed, reasoned
about, given reproducers, and shown failing before and passing after. Both
arguments were correct. Neither argument was portable, and no amount of
re-reading either diff would have revealed that — **only running them somewhere
new did.** `REPAIRED is not REVIEWED` has a companion: *verified on the hosts
it was verified on.*

---

## OC-49 — the cutoff at 0.696 is 684, not 683; and the zero-gap interval is withdrawn

> **This entry supersedes the scope banner on `OC-30`, the result in `OC-39`,
> and `XR-13`'s interval claim.** Two separate errors, both mine, both found by
> an outside read-only audit and both reproduced here before being accepted.

### Error 1: the number was computed at a rounded H_I and reported at the real one

The project reported **683** as the restart cutoff at its operating point
`H_I = 0.696`. The correct value is **684**. The production C++ has always said
684, and so has `oracles/restart_cutoff_exact.py`; the error was in the prose.

Its root cause is worth more than the correction. `XR-13` computed at
**H_I = 0.70** — a rounded stand-in — and got 683, which is right *at 0.70*.
`OC-30`'s scope banner then transcribed that as the value "at the 0.696
operating point this project actually uses". **The cutoff is a step function of
H_I, so rounding the input by 0.004 moved the output by a whole count:**

| H_I | tail at the cutoff | tail one below | cutoff |
|---|---:|---:|---:|
| 0.70 | 3.896719e-06 | 5.314981e-06 | **683** |
| 0.696 | 4.757131e-06 | 6.472471e-06 | **684** |

Both certified: the two-sided tail straddles `alpha = 5e-6` at `m` and `m-1`,
and the computation is stable when the working precision is raised from 60 to
120 decimal digits. A rounded input is not an approximation of an integer
quantile; it is a different question.

### The convention, written down, because the answers differ by one and so do conventions

- `n = 1000` trials per row or column of the 1000×1000 restart matrix.
- `alpha` is the **per-test** level. §3.1.4.3 step 1 sets `0.000005`, and
  `1 − (1 − 5e-6)^2000 = 0.00995` — the Sidak correction for 2000 tests at a
  1 % family-wise rate, which is where that number comes from.
- The cutoff is the **smallest `m` with `P(X_max ≤ m) ≥ 1 − alpha`**.
- **Counts at the cutoff are ACCEPTED**: the check fails iff
  `X_max > cutoff` (`restart_main.cpp:795`). This is the audit's stated
  convention too, so the disagreement was never about the convention.
- At width 1, `p = 2^-H_I ∈ (0.5, 1)`, so `floor(1/p) = 1` and the worst case
  is exactly two cells, `p` and `1 − p`. Then `max(X, n−X) ≤ m` iff
  `n − m ≤ X ≤ m`, so the exact tail is **two-sided**. The printed §3.1.4.3
  formula uses the **majority cell's one-sided tail only**, which is why it can
  be one lower.

New tool: `oracles/restart_cutoff_certified.py`, which derives both cutoffs
from that definition in exact rational arithmetic and certifies the integer
boundary rather than reading it off a float. It exists because "two of my own
tools agree" is not an argument when they share a design.

### Error 2: a sampled table was reported as an interval, and it is false

The claim was: *the printed and corrected cutoffs are **identical at every H_I
from 0.50 to 0.989***. That was a sweep in steps of 0.02 with a fine sweep near
the boundary — **sampled rows, read as an interval.** The audit produced a
counterexample inside the claimed range, and it reproduces exactly:

| | printed | exact |
|---|---:|---:|
| `H_I = 0.9661822653793894` | **581** | **582** |

in the production C++ and in the independent certified computation alike. The
mechanism is exactly as the audit states: the majority tail alone is
`4.6e-06 < alpha`, while the majority **plus** minority tails sum to
`5.000833e-06`, which is above `5e-06` by a factor of 1.0002. The audit found a
point inside a window **3.2e-06 wide**. No sweep in steps of 0.02 could have
found it, and no sweep ever licenses a statement about every point.

**Replaced with a quantile-boundary analysis, which does license one.** Both
cutoffs are non-increasing step functions of `H_I`, and the two-sided tail
strictly exceeds the one-sided tail, so for each integer `m` the exact cutoff
steps at a higher `H_I` than the printed one and the two disagree exactly on
the interval between those two crossings. Locating every crossing by bisection
(not sampling) over `[0.50, 0.989]`:

| | |
|---|---|
| intervals where the two cutoffs differ | **36** |
| total measure | **1.0614e-03**, i.e. **0.217 %** of the range |
| widest | 5.436e-04, at cutoff 574, near `H_I = 0.9862` |
| the audit's counterexample | inside the cutoff-581 interval, `(0.9661806581243831, 0.9661838745579914)` |
| lowest `H_I` with any disagreement | ≈ 0.888; below that the two crossings coincide to better than 1e-18 |

So the corrected statement is: **the two cutoffs agree on about 99.78 % of
`[0.50, 0.989]` and differ on 36 narrow intervals clustered at the
high-entropy end.** At the project's operating point, 0.696, they agree at 684,
and the nearest disagreement is at `H_I ≈ 0.888` — so the practical conclusion
that `C23` changes no verdict for this device survives, now proved by boundary
analysis rather than asserted from samples.

**One nuance the analysis exposes, which matters for anyone rerunning it.** The
counterexample is `alpha`-sensitive. Under the spec's flat `5e-6` the two
cutoffs are 581 and 582; under the Sidak `5.0251553e-6` both are 581, because
`5.000833e-06` falls below that threshold. The production code uses the spec's
`5e-6`. An oracle that silently used the other one would have "failed to
reproduce" a real finding.

### The rule this changes

A sweep is evidence about the rows it sampled. Where a statement about an
interval is wanted, the boundaries have to be solved for, because the quantity
is an integer quantile and integer quantiles move at boundaries that sampling
steps straight over. Added to `audits/BUG-REPAIR-GUIDE.md` as the sixth
instrument rule. The project's operating practice is unchanged and already
correct on the other half of the audit's prescription: the tool computes the
cutoff from the H_I it is actually given, every run.

---

## OC-50 — C18 from the source: one caller, no estimator, uniformly conservative, and Windows DOES build

Item 5 of the outside audit asks four questions about `C18` and one correction
to the Windows record. Taken in order.

### Which estimators reach the multiplication? None. One test does.

`n_choose_2` has exactly **one caller in the entire tree**:

```
cpp/shared/utils.h:997    long int n_choose_2(const long int n) { return ((n*n) - n) / 2; }
cpp/shared/lrs_test.h:709 long int N = n_choose_2(L - W + 1);
```

and that line is inside `len_LRS_test()`, the **§5.2.5 longest-repeated-substring
pass/fail test**, which is reached from:

| caller | what it gates |
|---|---|
| `cpp/iid_main.cpp:489` | the IID test suite's required LRS test |
| `cpp/restart_main.cpp:1103-1104` | the restart test suite, rows **and** columns |

**No §6.3.x entropy estimator reaches it.** `ea_non_iid`'s "LRS Test Estimate"
is the §6.3.6 *estimator*, a different function that does not call
`n_choose_2`. That is why `ea_non_iid` ran the complete non-IID battery to
completion on Windows while `ea_iid` and `ea_restart` both failed: the overflow
is in a **gate**, not in an estimate. `len_LRS_test` returns a `bool`. It
cannot corrupt an entropy figure, because it never computes one.

### What does the overflow produce?

For a 1,000,000-sample input whose longest repeated substring is 40, so
`n = L - W + 1 = 999961`: the product `n*n` is **999,922,001,521**, which does
not fit in a 32-bit signed `long`, and the whole expression evaluates before
the division by 2:

| | |
|---|---:|
| true `N` | 499,960,500,780 |
| `N` as a 32-bit `long` | **−403,189,204** |

Measured consequence, `ea_iid` on `windows-latest` against an input macOS
passes: `Pr(X >= 1)` printed as **−0.000367** where macOS prints **+0.365370**,
same `P_col`, same LRS length. Reproduced exactly from the integer arithmetic
alone by `reproducers/c18_llp64_overflow.c` — no floating-point platform
difference is involved.

And the decision is worse than the printed probability. `lrs_test.h:765-766` is

```
logCollisionPower >= logl(-expm1l(logl(0.999L) / (long double) N))
```

so a negative `N` makes `logl`'s argument negative and the threshold **NaN**,
and every comparison against NaN is false.

### Permissive, conservative, or unknown? **Conservative, in every case.**

Not asserted — enumerated over everything a wrapped `N` can be, with the
threshold computed from the production expression:

| `N` | threshold | verdict | |
|---|---:|---|---|
| 499,960,500,780 (true) | −33.8451 | PASS | the correct answer |
| **−403,189,204** (measured wrap) | **NaN** | **FAIL** | every comparison false |
| 1,744,294,444 (a positive wrap) | −28.1869 | PASS | still passes, but from a **higher** bar |
| 1 (smallest positive wrap) | −6.90776 | FAIL | |
| −1 | NaN | FAIL | |
| 0 | 0 | FAIL | `logCollisionPower < 0` always, since `p_col < 1` |

The general argument, not just the table: a wrapped `N` is always **smaller in
magnitude** than the true one, because the true value exceeds 2³¹ whenever it
overflows at all. A smaller `N` makes `log(0.999)/N` more negative,
`-expm1l()` of it larger, and its logarithm **higher** — a higher bar to clear.
So the test can only become harder to pass, never easier. **There is no
permissive case.** `C18` denies assessments on valid data; it never awards one
it should not, and no published figure is wrong.

That is the same direction as `R-1`, in the same file, for an unrelated reason.

### What does fixing it cost?

The type change is three characters wide and the regression evidence is not.

- **The change.** `n_choose_2` should compute in a fixed-width 64-bit type —
  `uint64_t`/`int64_t` from `<cstdint>` — and `N` should hold it. `long long`
  would also work but `long` is exactly the mistake being corrected, so a
  fixed-width type is the right spelling. While there: `data_t` holds
  `long len` and `long blen` with `blen = len * word_size` (`utils.h:518,705`),
  which is the same defect at a larger threshold — it overflows on LLP64 once
  `len * word_size` exceeds 2³¹, i.e. beyond 268,435,455 8-bit samples. Not
  reached at this project's 1,000,000, and it should be fixed in the same pass
  rather than left as a second instance of a known bug.
- **Why it is not a free change.** It is **estimator-adjacent arithmetic** that
  decides a required test. The project's hard rule reserves that for a
  deliberate decision even when the current behaviour is indefensible, and it
  is indefensible here.
- **The evidence a repair owes.** On LP64 the value of `N` must not change for
  any input, so every figure and every verdict must be **bit-identical** before
  and after — the full suite plus the pinned figures, on macOS arm64 and on the
  x86-64 CI job. On LLP64 the `Pr(X >= 1)` sign must become positive and the
  LRS verdict must match the LP64 verdict on the same input, which the Windows
  job already measures and gates. A reproducer exists; a regression that fails
  against the unfixed arithmetic does not yet, and should be written with the
  repair rather than after it.

### The Windows record, corrected in the direction the audit did not expect

The audit reports the workflow **green while all three executables failed to
build**, on the missing `libdivsufsort` package. That was true of the commit it
was pinned at. It is not true now, and the owner's cost estimate should rest on
the current measurement:

| | |
|---|---|
| **Windows builds today.** | All three executables **compile and link** on `windows-latest`, with OpenMP. Gated and green in `.github/workflows/windows-platform-facts.yml`. |
| two dependency steps are needed, and neither is in `BUILDING.md`'s original text | `libdivsufsort` has **no** `mingw-w64` package and must be built from source — with `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` and a generator that is **not** `MinGW Makefiles` — and `libgomp` comes from `mingw-w64-x86_64-gcc-libs`, which the preinstalled toolchain does not pull in. |
| the audit is right that the green-while-broken state existed | It did, for several runs, and `OC-48` records it as one of nine instrument faults in that job, along with the "nothing ran, therefore the prediction was refuted" narrative the audit notes was already corrected. |

So the blocker is **not** the absence of a build, and it is **not** `seed()`.
It is two measured, fail-closed defects — `C18` and `C24` — in a tree that
otherwise builds and runs there. `seed()` is not even reached: it is called in
the permutation stage, and `C18` fails the LRS test first, so `OC-42`'s
prediction about it remains **UNTESTED on Windows rather than refuted**.
Repairing `C18` is what would let that question be asked at all.

**The owner's decision, stated as it now is.** Windows tier support costs: one
estimator-adjacent type change with two-platform bit-identity evidence
(`C18`), one portability change at a single choke point (`C24`,
`MoveFileEx` with `MOVEFILE_REPLACE_EXISTING`), two documented dependency
steps, and then `seed()` — which is a genuine entropy-path decision and is
still unmeasured because nothing has yet reached it. It is more than "the
blocker is small", and less than "there is no build".

---

## OC-51 — C14 is improved, not closed; the members that remain; and the consumer rule

`C14` has been described in this record as closed. It is not, and the outside
audit's `A04` is the proof: `ea_non_iid -o --version absent-data 1` exited **0**,
printed version information, assessed nothing and left any previous report in
place. Exit status 0 beside a stale report is precisely the fail-open `C14`
exists to prevent, reached through the option parser rather than through an
error path. Repaired now, and the closure claim is withdrawn.

### Members, with their state

| member | state |
|---|---|
| **route 1** — error paths that never reached the writer left the previous run's report in place | **CLOSED.** The `-o` target is claimed with a fail-closed placeholder as soon as the path is known, and every completing path overwrites it. |
| **route 2** — `--version` matched anywhere in `argv`, including `argv[0]` and the input filename | **CLOSED** for that shape (`OC-31`), and **re-opened and re-closed** for a shape the first fix did not cover: the prescan did not know that `-o` and `-l`/`-s` consume a following element, so `--version` as an option's ARGUMENT was honoured as an option (`A04`). The prescan now walks `argv` the way `getopt` will. |
| **route 3** — a report write that silently failed | **CLOSED** (`N-09`): every write is checked, and a failure fails the run. |
| **the atomic write** (`oac-13`) | **CLOSED on POSIX** (`OC-47`), and **NOT PORTABLE**: see `C24`. On Windows the placeholder makes every later write fail. |
| **argument-parse failures above the claim** | **OPEN, and small.** A usage error that exits before `-o` has been parsed writes no report and leaves any previous one in place. The exit status is nonzero, so a consumer following the rule below is not misled; but the file at the path is stale, and that is a real residue. |
| **a signal or `_exit` between the claim and the final write** | **OPEN by design, and covered.** The placeholder is what a reader finds, which is the fail-closed outcome rather than a stale success. This is the member the placeholder exists for, not a gap. |

So: **three routes closed, one closed twice, one closed only on POSIX, one
small residue open, one covered by design.** `C14` is improved, not closed.

### The consumer rule, recorded because it is the durable lesson

The audit names it and it is worth more than any of the individual repairs:

> **A consumer must require a successful process AND a complete, fresh,
> identity-bound result. Never exit status alone.**

Concretely, for anything reading a report from these tools:

1. **a successful process** — exit status 0, and not killed by a signal;
2. **complete** — the JSON parses, and `reportComplete` is not `false`;
3. **fresh** — the report's own `dateTimeStamp` belongs to the run just made,
   not to a previous one;
4. **identity-bound** — the report's `filename` and `sha256` identify the input
   that was meant to be assessed, and the `commandline` is the one issued;
5. **errorLevel 0**, present. A missing `errorLevel` is not a zero one — that
   mistake was live in this audit's own floor oracle until `A08` found it.

Every one of those five exists because some path through these tools can
satisfy the other four. `C14` route 1 defeats exit-status-alone; `A04` defeats
it again by a different route; the placeholder is what makes (2) meaningful;
`C24` is why (3) matters on Windows, where the report can be the *previous* run's
because the new one could not be written; and `A05` is why (4) matters, because
the thing at the path was briefly the input capture itself.

---

## OC-52 — accepted-pending: A02 and A06, with the audit's acceptance criteria

Both are **accepted as real and queued**, not disputed. Recorded here so that
the queue is not mistaken for a disagreement. Neither is repaired in this round
because both change figures or guard behaviour and each needs its own evidence.

### A02 — the `C01` floor subtraction is justified by the wrong mechanism

**The finding, as the audit states it.** The floor term for `C01` is justified
as a one-ULP effect, but the mechanism is **dictionary saturation**, not
rounding. An observed discrepancy of **3.69e-04** is therefore **not a bound**:
it is one measurement of a quantity whose size is set by how the dictionary
fills, and nothing in the one-ULP argument constrains it.

**Acceptance criteria, quoted from the audit's framing:** an observed maximum
is not a bound. The subtraction must either be re-derived from the saturation
mechanism, with an argument that bounds it, or be replaced by a term that is
honestly labelled as a measured maximum over a stated input set and not as a
bound.

**Why queued.** It changes the floor, which is a published figure, and the
re-derivation is a piece of analysis rather than an edit.

### A06 — `--allow-known-platform-deltas` accepts an enormous change because it only inspects filenames

**The finding.** The flag is meant to tolerate the known upstream `#155`
platform deltas. It decides what to tolerate by looking at **filenames**, so a
change from **0.85 to 0.01** in a tolerated file is accepted. A guard that
cannot distinguish a known 1e-10 platform delta from a 0.84 collapse is not
guarding.

**Acceptance criteria.** The tolerance must be bounded by **magnitude**, not by
file identity: a delta is tolerated only if it is within the measured size of
the known platform difference for that quantity, and anything larger fails
however familiar the filename. The guard must be shown failing against an
injected large change in a tolerated file.

**Why queued.** It is a change to what the suite accepts, so it needs the
measured magnitudes for each tolerated quantity first, and those come from the
two platform jobs.

### A11 — out of scope, as the audit itself says

The IID-track races stay out of scope while the IID battery is excluded from
TruePad's path. Recorded, not queued.

---

## OC-53 — C18 repaired, and the Windows blocker moved to `seed()` as a measurement

### The change

`cpp/shared/utils.h:997` was `long int` in the **parameter, the product and the
return**, and `long` is 32 bits on LLP64 and 64 on LP64, so one source computed
two different things. Now `int64_t` throughout, with the argument cast before
it is formed at `cpp/shared/lrs_test.h:709`.

**Every step, not just the final type.** `n*n` is evaluated before the
subtraction and the division, so widening only the return value would have
changed nothing — the overflow is in the product. For n = 999961 the product
alone is 999,922,001,521.

**`int64_t` rather than `long long`**, because `long` is the mistake being
corrected and a fixed-width type is the right spelling. `N` is used only after
a cast to `long double` and is never printed, so there is no format-specifier
hazard — which is precisely why `data_t`'s `long len` and `long blen` are **not**
swept into this change: they are printed with `%ld` in many places, which would
be wrong for `int64_t` on LLP64, and their overflow threshold is 268,435,455
samples, far above anything this project assesses. Recorded separately rather
than bundled into a change that must prove bit-identity across the tree.

**Sufficiency is provable.** Callers already refuse a sample count above
`INT_MAX`, so n ≤ 2³¹−1 and n·n ≤ 4.61e18, inside `INT64_MAX` = 9.22e18. An
assert states that bound where it is relied on.

### LP64 bit-identity, and the control that made the comparison mean anything

Nine reports, three fixtures, all three tools, against a pre-fix worktree.

The first comparison said **five of nine differed** — all in
`permutationTestResults`. Instead of waving that away, I ran the baseline
**against itself**: the same binary differs from itself across runs in exactly
that field, because the permutation tests seed from `/dev/urandom`. So the
field is excluded **by evidence rather than by assumption**, the exclusion is
shown complete by re-running baseline-against-baseline through the same filter,
and the comparator is shown **live** — a 1e-15 perturbation of `hAssessed` is
caught, so it is not vacuous.

| | |
|---|---|
| reports identical, before vs after | **9 of 9** |
| exclusion complete (baseline vs baseline, same filter) | yes |
| comparator live (1e-15 perturbation caught) | yes |

No LP64 figure or verdict changes. Full suite 21 passed, 0 failed.

### What fails next on Windows — measured, not predicted

| tool | before the fix | after the fix |
|---|---|---|
| `ea_non_iid` | completed, figure produced | completed, figure produced, exit 0 |
| `ea_iid` | **failed the §5.2.5 LRS test** (`Pr(X >= 1) = −0.000367`) | **passes** chi square and LRS, then **dies at `seed()`** |
| `ea_restart` | failed the LRS tests | **restart sanity check PASSES**, chi square and LRS pass, then **dies at `seed()`** |

```
** Passed chi square tests
        Pr(X >= 1): 0.365370
** Passed length of longest repeated substring test
Can't open random source. Reverting to a deterministic seed.: No such file or directory
```

Two things in that are worth more than the gate going green.

1. **Windows now prints exactly macOS's figure.** `Pr(X >= 1) = 0.365370` on
   both, where Windows previously printed `−0.000367`. Cross-platform
   agreement on the repaired quantity, not merely a plausible-looking number.
2. **`ea_restart` gets past the restart sanity check.** `Restart Sanity Check
   Passed`, with both LRS passes (rows 0.365370, columns 0.973688). That is
   the check January's acceptance decision depends on, and it now runs on
   Windows.

So the blocker **moved** rather than disappearing, exactly as expected — and
`OC-42` is now **CONFIRMED for both tools** instead of untested. The observed
exit status is 127 for both; the mapping from `exit(-1)` to that value under
the MSYS2 shell is not established here and nothing is claimed about it.

### Costing the `seed()` fix

`cpp/shared/utils.h:792-798`: `seed()` opens `/dev/urandom` and calls
`exit(-1)` if it cannot. A native MinGW binary has no `/dev/urandom` — MSYS2's
emulation serves MSYS-runtime programs, not MINGW64 ones.

**Not implemented here.** It is an entropy-relevant path and stays gated on the
owner, which is the standing constraint.

**The change.** Keep `/dev/urandom` on POSIX and add `BCryptGenRandom` (or
`RtlGenRandom`) under `_WIN32`. **`std::random_device` must be refused as the
portable shortcut**: its quality is implementation-defined, and on MinGW
libstdc++ it has historically been a deterministic PRNG, which would be the
worst outcome available — a seed that looks fixed and silently makes the
permutation tests' p-values mean nothing.

**Where the seed goes, and why that sets the bar.** It feeds the xoshiro256\*\*
state used to shuffle in the IID permutation tests. A constant or low-entropy
seed does not crash anything; it makes a statistical test report a
randomisation it did not perform. So the acceptance criteria are about
behaviour, not about linking:

| the repair owes | how it is checked, with instruments that already exist |
|---|---|
| POSIX behaviour byte-for-byte unchanged | the same before/after comparison used here, with the measured exclusion and the live comparator |
| the Windows source is not constant | two runs on Windows must differ in `permutationTestResults`, exactly as two runs on macOS do — the baseline-against-itself control, pointed at Windows |
| the seed is not merely varying but unpredictable | the bytes come from the platform CSPRNG, named in the code, with the failure path still fail-closed rather than falling back to a weak seed |
| the permutation verdicts remain sound | the IID battery's verdicts on the pinned fixtures must match LP64's on the same inputs |

**Scale.** One function, two branches, one new library on one platform, and a
nondeterminism control that is already written. The honest summary for the
owner: smaller than `C18` was feared to be, larger than "small", and the only
remaining item that touches an entropy path at all.

---

## OC-54 — four refusals for the wrong reason: a new failure shape, mechanised, and swept for

### The shape

Reproducing `A08` (the floor oracle emitting a figure for malformed reports), I
built four negative fixtures by hand, each targeting a different property.
**All four were refused.** That looked like four working guards and a finding
that was already fixed.

They were all refused for **one shared accidental reason**: my fixtures used
the wrong key for the test-case label, so every one died on *"no test case
labelled Overall"* and **not one of the four properties was exercised**.
Rebuilt by mutating a genuine report one field at a time, all four reproduced
exactly as reported.

**Had I stopped at the first attempt I would have told an outside audit it was
wrong when it was right.** That is the specific trap inside "reproduce before
accepting": a negative fixture built from scratch can be refused for a reason
that has nothing to do with the property under test, and a *set* of such
fixtures can share that reason silently. A wall of refusals is not evidence of
thoroughness.

### Mechanised, so it is not a thing to remember

`cpp/selftest/mutation-lib.sh` gains `mut_baseline <label> <cmd...>`: it asserts
the **unmutated** artifact is **accepted**, and records that it did.
`mut_summary` now **fails any harness that never asserted a baseline**, so a
fixture set that refuses everything fails as broken rather than passing as
thorough. A `mut_expect_pass` that succeeds **before any negative has been
tried** is recognised as the baseline automatically — after a negative it is a
*restored* control, which is a weaker and different claim (the mutations did
not leak, not that the construction was ever sound).

Verified both ways:

| | |
|---|---|
| baseline accepted | all three mutation harnesses pass (5/5, 9/9, 9/9) |
| baseline deliberately broken | `*** REFUSED -- the FIXTURES are broken, not the guard ***`, harness FAILS |
| baseline never asserted | `*** NEVER ASSERTED -- this harness cannot attribute its refusals ***`, harness FAILS |

**A corollary found in the same pass.** A **hardcoded expected count** inside a
harness is the same trap in other clothes. `harness-inventory-mutation-test.sh`
compared against the literal `20 passed, 0 failed (18 regression scripts
discovered)`; registering one new regression script made its **positive control
fail for a reason unrelated to any mutation**, which invalidates every negative
beneath it. It now derives those numbers from `run-all-checks.sh`'s own
constants and refuses to run if it cannot read them.

### The sweep: how many other from-scratch negative-fixture sets are there?

28 scripts examined — every `cpp/selftest/regression-*.sh`, the three mutation
harnesses, the fixture-inventory verifier, `pin-check.sh`, the oracle self-test,
and the audit's reproducers. A script counts only if **all four** conditions
hold: two or more negatives, each targeting a **different** property, built
**from scratch** rather than by mutating a genuine artifact, and **no assertion
anywhere that the unmutated baseline is accepted**.

**One script matched.** `reproducers/c16-c23-matrix.sh`.

Most scripts failed the fourth condition — they already assert an accepted
baseline (`regression-output.sh`'s "writable `-o` still works",
`regression-restart.sh`'s "valid H_I still runs",
`regression-nonregular.sh`'s regular-file case, and so on). Several failed the
third because their negatives are already mutations of committed artifacts
(`regression-272.sh` mutates a copied `cpp/` tree, `regression-minsize.sh` uses
`bin/rand8_short.bin`, `regression-selftest-inventory.sh` mutates a copy of the
real corpus). Several failed the second because all their negatives test one
property (`regression-width.sh`'s three malformed widths are all the width
grammar; `regression-iid-failclosed.sh`'s eight fixtures differ only in repeat
length).

`build-differential.sh` is the near miss: two from-scratch negatives and **no**
positive control, but both test the same property — an implanted repeated
substring differing only in length — so it fails condition 2. Worth noting
rather than ignoring.

### The one that matched, and what fixing it found

`c16-c23-matrix.sh` **had no assertions at all.** Its `run()` classified and
printed; the expectations were **echoed as prose and never compared**; and its
exit status came from a timing print at the end. Nothing in it could fail, so it
could not detect its own fixtures being broken — and its two negatives
(an underflowing `H_I` of `1e-400`, and a bare `0.875` with an unstated scale)
**shared one generic classifier pattern**, `'must be|must state'`, so two
refusals for one reason would have been indistinguishable in the table.

Repaired: each refusal is classified by the specific message that names its own
property, every cell has an expected classification, the baseline (a uniform
matrix accepted by a build whose statistic is correct) is asserted **first**,
and the exit status is the assertions' verdict.

**And the assertions immediately caught a wrong expectation of mine.** I had
expected the `oldparse` builds to refuse the underflow. They **accept** it,
with cutoff 1000 — and that acceptance *is* the `C16` defect the matrix exists
to demonstrate. The table now asserts the unfixed build's defective behaviour
as its expected behaviour, which is what a differential matrix is for. A script
with no assertions could not have told me that in four rounds of reading it.

---

## OC-55 — A02: the `C01` floor term, and which of the three options this took

> **Supersedes the `C01` half of `REPAIR-STRATEGY.md`'s "one correction to the
> framing" paragraph.**

### The label was wrong twice

The term read: `C01 = 3.69e-4  # two-sided last-digit comparison error, measured
bound`.

It is **not a last-digit comparison error**. The 3.69e-4 figure comes from
**`F10`** — MultiMMC's **chained prefix lookup** under the `MAX_ENTRIES` cap
(`multi_mmc_test.h:236/:93`). §6.3.9 step 4.b.i requires an independent lookup
of M_d at every depth; the code looks up depth d only if depth d−1 hit, and
when the cap refuses a prefix entry at depth d, every later recurrence of that
context suppresses all depth ≥ d predictions. The figure's own provenance says
so: `COVERAGE.md` records it as `f10_over_8bit_1M`, "tool 0.00037 bit HIGH".

And it is **not a bound**. The size of the effect is set by **how the dictionary
fills**, which is a property of the data. The superseded paragraph applied its
own correct rule — *"a single measured overestimate is not a bound"* — to `C03`
and then exempted `C01` on a mechanism `C01` does not have.

### Which of the three options: the third, and at width 1 it is a proof

The audit offered three: prove a bound over the supported inputs, correct the
algorithm, or exclude the affected path.

**Proving a bound is not available.** The suppressed-prediction count is
data-dependent, and the direction is not fixed either — the same cluster
measured 0.082 bit **low** on one fixture and 0.00037 bit **high** on another.
Claiming a bound here would be the same error a second time.

**Correcting the algorithm is the owner's call.** It is a change to estimator
numerics, which this project's hard rule reserves for a deliberate decision.
Recorded, not taken.

**So: exclude the affected path** — and at **width 1** the exclusion is not a
judgement but a counting proof, from the two shipped constants:

> `D_MMC = 16`, `MAX_ENTRIES = 100000` (`multi_mmc_test.h:4-5`); the loop runs
> `d = 0..15`. For **binary** data, depth `d` has at most `2^(d+1)` distinct
> prefixes and at most 2 postfixes each, so `entries[d] ≤ 2^(d+2)`.
>
> | depth | `entries[d]` ceiling | cap binds? |
> |---|---:|---|
> | `d ≤ 14` | `2^16` = 65,536 | **no** — below 100,000 |
> | `d = 15` | `2^17` = 131,072 | yes, but `d = 15` is the **top** depth and the defect needs a `d+1` to suppress |
>
> So at width 1 **no suppression is reachable** and `F10` cannot move the
> figure.

That is this project's path and this device's: a 1-bit source at `H_I` 0.696.
It is also consistent with what was already measured independently — binary
data was observed immune in a 10-fixture binary-versus-generic differential,
which at the time was recorded as a curiosity rather than as the reason.

### "Certified floor" and "evaluated margin" are now different outputs

A reading is a certified floor only where **every subtracted term is a bound**;
anything else is an evaluated margin. That turned out to depend on the reading
as well as the width — `OC-59` found `C22c`'s tabulated value is not
independently reproduced, so the **literal** reading is a margin at every
width. `oracles/entropy_floor.py`:

| width | `C01`/`F10` term | literal reading | F07 reading |
|---|---|---|---|
| 1 | `0.000e+00`, **EXCLUDED: unreachable at width 1**, with the proof printed | EVALUATED MARGIN (it subtracts `C22c`) | **CERTIFIED FLOOR** |
| > 1 | `3.690e-04`, **EVALUATED MARGIN, *not* a bound** | **EVALUATED MARGIN (not a floor)**, with an explicit do-not-publish-as-a-floor line |

The bit width is a **required input** to the report rather than something
inferred inside it: if it cannot be established, nothing is called a floor at
all. Measured: at width 1 the F07 reading prints a certified floor of
0.84465042387787448 while the literal reading prints an evaluated margin of
0.84129042387787445; at width 8 both are margins and both say so.

---

## OC-56 — A06: the platform exception is an expected-result manifest, not a filename list

### What it was

`--allow-known-platform-deltas` excused a failing `selftest` whenever every
named file was one of two **filenames**. It inspected neither the estimator, the
field, the magnitude, the direction, nor the platform. An isolated controller
fed it a deliberate change from **0.85 to 0.01** in one of those files and it
was **accepted**. A guard that cannot tell a 1e-10 last-digit platform
difference from a 0.84 collapse is not guarding.

### What it is

`cpp/selftest/known-platform-deltas.txt` — an expected-result manifest keyed by
**platform identity** — checked by `cpp/selftest/check-platform-deltas.py`,
which parses `selftest`'s own printed numbers. A run is excused only when **all
three** hold:

1. a `platform` block matches this host: `uname -s`, `uname -m`, and a
   substring of the compiler identity;
2. **every** reported difference matches a row on **file, estimator and field**
   and its `|delta|` is within that row's tolerance;
3. **every** row listed for this platform was actually **observed** — a
   comparison that silently stopped happening must not pass as an absence of
   difference.

Eight rows for this host, one per observed difference. **Tolerances are
labelled as measured magnitudes with headroom, not bounds** (rule 6): observed
1.25e-10 to 3.66e-10, row tolerance 1e-9. The manifest's own text forbids
widening a row to swallow a delta that exceeded it — *that is the finding, not
the obstacle.*

Linux x86-64 deliberately has **no block**, because it is the platform NIST's
reference data was produced on and `selftest` is expected to pass there
outright. With no block, a `selftest` failure on Linux is **not excused**, even
though the x86-64 CI job passes the flag.

### The four failures the audit required, each with the flag enabled

`cpp/selftest/regression-platform-deltas.sh`, registered in the authoritative
inventory. Its negatives are **mutations of a genuine `selftest` transcript**,
one field at a time, and the unmutated transcript is asserted **accepted
first** (rule 7), so each refusal is attributable.

| case | result |
|---|---|
| a **large** delta in a named file (0.85 → 0.01) | `delta TOO LARGE: ... 0.84 > tolerance 1e-09` |
| an **unexpected estimator** in a named file | `UNEXPECTED difference, no manifest row` |
| a listed comparison that **stops being reported** | `MISSING comparison, a listed row was never reported` |
| the **wrong platform** | `the exception does NOT apply on this platform: no manifest block matches` |
| an **unreadable manifest** | refuses, exit 2 |
| **control**: unmodified transcript, right platform | `8 expected platform delta(s), all within tolerance` |

**One instrument error found and fixed while building it.** The difference
parser was anchored at the line start, and `selftest` prints the first
difference for a file on the same line as the filename
(`ringOsc-nist.bin: ringOsc-nist.res: Significant difference for ...`). Those
lines were silently skipped and then reported as **MISSING comparisons** — the
right verdict for the wrong reason, and one that would have read as "the
comparison stopped happening". Unanchored, and the baseline control is what
surfaced it.

---

## OC-57 — C24 repaired: the report is put in place with the primitive specified to replace

`cpp/shared/TestRunUtils.h`, `writeJsonReport`. `C08`'s argument is that
`rename(2)` replaces an existing destination atomically. That is POSIX.
Windows `rename()` refuses one — measured, `errno 17` — and `C14` has already
placed a placeholder at the `-o` path before any real report is written, so on
Windows the placeholder **guaranteed** that every later write failed and no
tool could produce a `-o` report at all.

Now `MoveFileEx` with `MOVEFILE_REPLACE_EXISTING` under `_WIN32`, plus
`MOVEFILE_WRITE_THROUGH` so the placement is durable before returning. The
POSIX path is untouched; macOS builds and the suite are unchanged.

**Verified on Windows, with the contrast kept beside it** rather than asserted.
The replication probe copies the *current* writer and keeps a bare-rename arm:

| case | Windows | macOS (control) |
|---|---|---|
| 1. current writer, fresh path (the `C14` placeholder) | OK | OK |
| 2. current writer, second write over it | **OK** | OK |
| 3. current writer, single write to a fresh path | OK | OK |
| 4. **old** bare-rename writer, fresh path | OK | OK |
| 5. **old** bare-rename writer, second write over it | **FAILED, `errno 17`** | OK |

and every tool now puts its report in place there. The gates were re-pointed
from expecting the defect to measuring the repair, and `rename()`'s semantics
are reported as a **platform fact** either way — depending on POSIX semantics
there was the defect, and that is what changed.

**The one-liner refused, recorded at the site.** `remove(path)` before
`rename()` would "work" on both platforms and reopens exactly the window `C08`
closed: an interval in which the path does not exist at all, so a reader finds
nothing where it should find the previous report.

The Windows job is now **20 gates passing and one failing**, and the one that
fails is the ecosystem fact that `libdivsufsort` has no `mingw-w64` package.

---

## OC-58 — F13 closed as UNREACHABLE: reachability came before repair

`shared/utils.h` `predictionEstimate` and `shared/most_common.h` both compute
an upper confidence bound as `min(1.0, p + ZALPHA*sqrt(p(1-p)/(n-1)))`. The
concern was that `std::min` suppresses a NaN **only by argument order** —
`min(1.0, NaN)` returns 1.0, `min(NaN, 1.0)` returns NaN — so a reviewer could
swap them and read the change as cosmetic.

**The first question is reachability, and it settles it.**

1. `p_global > 0` already excludes a NaN `p_global`, because `NaN > 0` is
   false. The guard that matters is already there, for a different reason.
2. The only other NaN source is `0/0` in the variance term, which needs
   **`N == 1` exactly**.
3. `MIN_SIZE` is 1,000,000 on every supported path, and a one-symbol alphabet
   is refused earlier, so `N == 1` is not reachable.

Measured, not just argued: `reproducers/f13_nan_reachability.c` evaluates the
expression **73,745** times over the supported domain — exact boundaries
`p = 1/N` and `p = 1`, `N` from 999,999 up to 2³¹−1 — and finds **no NaN**. And
**the same probe fires at `N == 1`, `p == 1`**, so its silence on the supported
domain is a measurement rather than blindness. A probe that never produces the
thing it is looking for has established nothing.

**And the direction, if one ever did arrive:** `min(1.0, NaN)` gives `p' = 1`
and an entropy of 0 — maximally conservative. The ordering is incidentally
**fail-closed**, not incidentally permissive.

**Closed as unreachable, not repaired.** Both sites now carry a comment saying
the argument order is load-bearing and must not be swapped, with the
reachability argument beside it, because that is where the next person looks.
Fixing something that cannot happen would have been a change to estimator
arithmetic bought for nothing.

---

## OC-59 — C22c: the monotonicity premise holds; the tabulated magnitudes do not reproduce

`entropy_floor.py` subtracts the `C22c` term **at the largest tabulated `n` not
exceeding the actual `n`**, and justified that as an upper bound by asserting
the ceiling falls with `n`. That premise was an analytic sketch. It is now
measured — and the measurement found something else.

**New tool:** `oracles/zalpha_ceiling_by_n.py`, with both controls the method
requires: every value recomputed at two working precisions (self-comparison),
and `z_spec` perturbed to prove the computation responds to its own input
(live sensitivity).

### The premise holds

| family | behaviour in `n` | |
|---|---|---|
| proportion estimators (MCV, t-Tuple, LRS, the `P_global'` terms) | **level** — the gap is the closed form `dz/((1+z)ln2)` = 6.887e-05, attained at `p = 1/n` and independent of `n` | |
| **Collision** estimator — the family that **binds** | **falls**: 7.49e-04 at n=1e6 → 2.65e-04 at n=64e6 | its sensitivity near the `X' = 2.5` clamp is what gives this term its 1e-3 magnitude |

So the largest-tabulated-`n` rule is sound as a rule.

### The magnitudes do not

| n | tabulated | independent derivation | ratio |
|---:|---:|---:|---:|
| 1,000,000 | 3.360e-03 | **7.493e-04** | 4.48 |
| 8,000,000 | 2.160e-03 | **4.456e-04** | 4.85 |

A **consistent** factor at both lengths, which says the two calculations differ
systematically rather than one being noisy. **The direction is safe:** the
tabulated values are *larger*, so the floor subtracts more than this derivation
requires and the published figure is not overstated. But an unreproduced
subtrahend is not a bound, and this is the same shape as `A02` — a term carried
on a justification that does not reconstruct.

### Two instrument errors found getting there, both of the usual family

1. **The first sweep searched outside the realisable domain.** It swept `p` down
   to 1e-6 and then refined to `p0/4`, reporting its maximum at
   **`p = 2.5e-07` — below `1/n`**, a proportion no count can produce. The gap
   grows without limit as `p → 0`, so an unconstrained sweep reports the edge
   of its own grid and calls it a worst case. Found by comparing against the
   recorded number instead of accepting my own output.
2. **A strict comparison on a theoretically constant quantity** reported
   `*** RISES ***` for the proportion family, whose gap is the closed form and
   therefore level. Spurious non-monotonicity from which candidate `p` happened
   to hit the maximum.

### What this changes in the output

A reading is a **certified floor** only where **every** subtracted term is a
bound. The **literal** reading subtracts `C22c`, so it is an **evaluated
margin at every width**; the **F07** reading does not subtract it, so at width
1 — where `C01`/`F10` is excluded by proof — it is a certified floor. Labelling
the whole report with one word would have blurred exactly the distinction the
oracle exists to keep.

| | literal reading | F07 reading |
|---|---|---|
| width 1 | EVALUATED MARGIN, 0.84129042387787445 | **CERTIFIED FLOOR**, 0.84465042387787448 |
| width > 1 | EVALUATED MARGIN | EVALUATED MARGIN |

**And the distinction is now enforced rather than remembered.**
`regression-docs.sh` fails if any document writes "certified floor" without a
width or reading qualifier in the same paragraph — 178 mentions of the word
across the tree is too many to police by hand. It found one on its first run (a
section heading) and that is fixed. Its own pattern then needed fixing twice:
silencing a `SyntaxWarning` by replacing `\s` with `[ \t]` broke matching
across a wrapped line, which is a behaviour change bought for a cosmetic
warning.

---

## OC-60 — `seed()` is DEFERRED, not a blocker; and what Windows can and cannot do today

### Why it is deferred

The owner adopted a **vendor reference qualification** as the default path
(2026-10-19). Under it **no NIST binary runs on a user's machine**: the owner
measures on his own hardware and ships a signed record, and Windows users reach
the hardware tier through that record. So `seed()` is **not on the product's
path**.

It matters only for the **self-assertion path** — a user running their own
assessment — and that path is an expert opt-in for which macOS and Linux are
sufficient.

**So this is not "Windows is blocked".** It is a small, well-understood fix
gated on a decision that has gone the other way. Recorded as deferred so that
nobody re-derives it, and so that nobody re-prices Windows on the strength of
it.

### What it would be, if revisited

A **platform entropy source**: `BCryptGenRandom`, or `RtlGenRandom`
(`SystemFunction036`), under `_WIN32`, keeping `/dev/urandom` elsewhere.
`cpp/shared/utils.h:792-798` is the site.

> **`std::random_device` MUST BE REFUSED. It is the obvious wrong answer and it
> looks right.** It is portable, it is standard, and on MinGW libstdc++ it has
> historically been a **deterministic PRNG**. A deterministic seed there does
> not crash anything and produces no error: it makes the IID permutation tests
> report a randomisation they did not perform, so their p-values mean nothing
> while every surface indication says the tool worked. That failure is silent,
> and it is worse than the current loud `exit(-1)`.

The seed feeds the xoshiro256\*\* state used to shuffle in the permutation
tests, so the acceptance bar is **behavioural**, not "it links":

| the repair owes | checked with |
|---|---|
| POSIX behaviour byte-for-byte unchanged | the before/after comparison of `OC-53`, with its measured exclusion and live comparator |
| the Windows source is **not constant** | two Windows runs must differ in `permutationTestResults`, exactly as two macOS runs do — the baseline-against-itself control, pointed at Windows |
| unpredictable, not merely varying | the bytes come from the platform CSPRNG, named in the code, with the failure path still **fail-closed** rather than falling back to a weak seed |
| the verdicts remain sound | the IID battery's verdicts on the pinned fixtures must match LP64's on the same inputs |

### What Windows can and cannot do today, stated plainly

This is the sentence someone sizing the work will read, and it must not be
summarised as "Windows is unsupported":

> **All three tools build and link** on `windows-latest` (MSYS2 MINGW64, gcc
> 16.2.0), with OpenMP. **`ea_non_iid` runs the complete non-IID battery and
> produces a figure**, exit 0. **`ea_iid` and `ea_restart` run through chi
> square, the §5.2.5 LRS test and — for `ea_restart` — the restart sanity
> check, all passing, and then exit at `seed()`.** Reports are written
> correctly (`C24` repaired). The §5.2.5 figures match macOS exactly
> (`Pr(X >= 1) = 0.365370`).

Two caveats belong with it. `libdivsufsort` has **no `mingw-w64` package** and
must be built from source — with `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` and a
generator that is *not* `MinGW Makefiles` — and `libgomp` comes from
`mingw-w64-x86_64-gcc-libs`, which the preinstalled toolchain does not pull in.
Both are documented in `BUILDING.md` and both are automated in the job.

### One live limit worth naming, since it is not absent

`data_t` holds `long len` and `long blen` with `blen = len * word_size`
(`utils.h:518,705`). On LLP64 that overflows once `len * word_size` exceeds
2³¹ — i.e. beyond **268,435,455 8-bit samples**. That is far above anything
this project assesses, and it was deliberately left out of the `C18` repair
because those fields are printed with `%ld` in many places, which would be
wrong for `int64_t` on LLP64. **It is a live limit, not an absent one**, and a
Windows run on an input that large would be wrong rather than refused.

---

## OC-61 — C18 had upstream prior art, filed as "platform / library" at LOW severity

Sweeping for stale "Windows is unsupported" wording turned up a row this audit
has carried since the first pass, in
`audits/2026-09-30/novel-findings/agent-reports/exclusion-map.md`:

> | 219 | I | open | **Windows MinGW: `ea_iid` LRS test `Pr(X≥1)` negative → Failed** | `ea_iid` (Windows) | `lrs_test.h len_LRS_test` (+ user `seed()` change) | **platform / library** | wrong IID verdict | IID verdict | verdict (**LOW**) | open; Windows not supported |

That is `C18`, exactly: the symptom, the tool, and the function. **Upstream
issue #219 is prior art, it is still open, and it has been there for about a
year.** Three things about that are worth keeping.

**It was mis-attributed, which is why it sat at LOW.** The cause was recorded
as "platform / library" — the same category as a differently-built
`libdivsufsort` — when the actual mechanism is a **32-bit `long`** in
`n_choose_2`'s product. A negative probability from an integer overflow and a
negative probability from a mismatched library look identical from the outside;
only the arithmetic distinguishes them, and `reproducers/c18_llp64_overflow.c`
reproduces the printed value from the integer arithmetic alone with no
floating-point platform difference involved.

**The reporter's sequence is this session's in reverse.** They patched `seed()`
to get a Windows run at all — the row says "+ user `seed()` change" — and
*then* hit the LRS failure. This session repaired `C18` first and *then* reached
`seed()`. Both orders land on the same two items, which is some corroboration
that the Windows path has exactly these two obstacles and not more.

**And it had been sitting in this audit's own records.** The exclusion map knew
the symptom before any of the Windows work began; what it did not have was the
mechanism, and no amount of re-reading the row would have supplied one. The
measurement did. That is the same lesson as `OC-48` and it is slightly worse
here, because the evidence was already in the tree.

**Nothing is reported upstream** — the standing decision of 2026-10-15 holds,
and `UPSTREAM-REPORT-INVENTORY.md` records what is wrong with the tool being
run without sending it.

### Cited as corroboration: what it does and does not establish

| | |
|---|---|
| **issue** | upstream **#219** |
| **age** | open for approximately one year at the time of this entry (2026-10-20) |
| **symptom recorded** | "Windows MinGW: `ea_iid` LRS test `Pr(X≥1)` negative → Failed" |
| **site recorded** | `lrs_test.h len_LRS_test` (+ a user `seed()` change) |
| **classification recorded** | **platform / library**, severity **LOW**, "Windows not supported" |

**What it establishes.** That the symptom exists **in the wild**, hit
independently by someone who is not this project, on the same platform, in the
same function. `C18` is therefore **real and reachable**, not an artifact of
this tree, this toolchain, or this session's instruments. That is independent
external corroboration and it is worth more than a second run of my own
reproducer.

**What it does not establish.** It does **not** validate the repair. #219
contains no mechanism — that is precisely what it lacked — so it cannot confirm
that widening `n_choose_2` is the right fix, only that something on that path
was wrong. The repair rests on its own evidence: the exact reproduction of the
printed value from the integer arithmetic alone, the LP64 bit-identity
measurement, and the Windows run now printing macOS's figure. **And nothing is
being sent anywhere.**

### What the pair demonstrates about severity triage

A symptom classified as a **low-severity platform/library issue** was in fact
an **integer overflow producing a negative probability**, which made a required
§5.2.5 test fail unconditionally whatever the data. The misclassification was
reasonable on the evidence available — a negative probability from an integer
overflow and one from a mismatched library look identical from outside — and
that is the point: **the category a symptom falls into is a guess until the
mechanism is known, and severity inherited from that guess is a guess too.**

The practical rule, recorded in `audits/BUG-REPAIR-GUIDE.md`: a finding whose
**mechanism is unknown** should carry its severity as *unestablished* rather
than as a number inferred from the category it was filed under. "Platform"
is a hypothesis about a cause, not an observation.

---

## OC-62 — the C22c factor found: it is compression versus collision, and OC-59's conclusion was wrong

> **This entry supersedes `OC-59`'s conclusion.** `OC-59` reported that
> `C22c`'s tabulated values "are not independently reproduced", on the strength
> of a derivation that came out a consistent 4.5–4.9× below them. The ratio was
> a mechanism, as a consistent ratio always is, and the mechanism is that **the
> two derivations were bounding different estimators.** The tabulated values
> are correct.

### The factor

`OC-22` Part 3 derives the `ZALPHA` ceiling **per estimator** and takes
`C22c` as the **maximum over estimators**. There are three families, and they
differ by more than an order of magnitude:

| family | mechanism | ceiling at n = 1e6 | at n = 8e6 |
|---|---|---:|---:|
| proportion (MCV, t-Tuple, LRS, `P_global'`) | `p_u = p̂ + z·sqrt(p̂(1−p̂)/(n−1))`; closed form `Δz/((1+z)ln2)` | 6.887e-05 | 6.887e-05 |
| **Collision** | `dH/dX'` diverges at the `X' = 2.5` cap but `H` is capped, so `max ΔH = (2/ln2)·sqrt(ΔX'/2)` | 7.84e-04 | 4.66e-04 |
| **Compression — THIS IS THE ONE THAT BINDS** | `com_exp` is **stationary at p = 1/64**, so the sensitivity is quadratic on the approach to its cap, and `σ_max` carries a `log2(num_blocks)` | **3.36e-03** | **2.16e-03** |

`OC-59` computed the **Collision** family and compared it against the
**Compression** tabulation. The "unexplained" ratio was simply
compression/collision, 4.29 and 4.64 from the record's own rows — and it
*drifted* precisely because `σ_max = 0.5907·log2(num_blocks)/2` grows with `n`
while the collision bound has no such factor. A clean constant would have meant
a single misplaced multiplier; the drift said the expressions differ in form,
which they do.

### Reproduced, where it can be checked independently

`oracles/zalpha_ceiling_by_n.py` now computes all three families, bounding each
quantity the way the record bounds it:

| quantity | n | recorded | derived here | |
|---|---:|---:|---:|---|
| collision ΔX' | 1e6 | 1.480e-07 | 1.478e-07 | ✓ |
| collision ceiling | 1e6 | 7.840e-04 | 7.845e-04 | ✓ |
| collision ceiling | 8e6 | 4.660e-04 | 4.664e-04 | ✓ |
| compression `num_blocks` | 1e6 | 166 666 | 166 667 | ✓ |
| compression ΔX' | 1e6 | 2.15e-06 | 2.142e-06 | ✓ |
| compression ΔX' | 8e6 | 8.89e-07 | 8.884e-07 | ✓ |
| compression ceiling | both | 3.36e-03 / 2.16e-03 | **not reimplemented, deliberately** | — |

The final compression ceiling comes from scanning `X'` down from the cap
`G(1/64)` **through the production solve**. This script does not reimplement
that solve, and that is a choice rather than a gap: a harness that
re-implemented production functions instead of calling them, and disagreed with
the tool, is `OC-41`. What can be checked without reimplementing production —
`num_blocks`, `σ_max`, `ΔX'`, and the collision family's *entire* ceiling to
0.07 % — reproduces.

**And the second error in `OC-59`'s derivation, which rule 9 now covers:** its
collision figure used `v = n/2.5`, a *typical* collision count, where the record
bounds `v ≥ n/3`. That alone accounts for the residual 4.6 %. **A bound
computed from a typical value is not a bound**, even when the arithmetic is
right.

### What this changes

**No entropy is recovered, because nothing was being thrown away.** `OC-59`
said the term was "conservative by a factor of roughly 4.7" and invited the
question of how much entropy the correction would recover at the operating
point. The answer is **none**: the tabulated value is the correct ceiling for
the binding estimator, and the factor was my own misidentification. At the
width-1 operating point the term stands at **3.36e-03 bit** under the literal
reading and **0** under `F07`'s, exactly as before.

**`C22c` is a bound, so the floor labels revert.** It is a *derived ceiling* —
from `Δz`, the estimator's cap, `n`, Popoviciu's `σ_max` and `v ≥ n/3` — not an
observed maximum. So at width 1, where `C01`/`F10` is excluded by proof, **both
readings are certified floors** again:

| | literal reading | F07 reading |
|---|---|---|
| width 1 | **CERTIFIED FLOOR**, 0.84129042387787445 | **CERTIFIED FLOOR**, 0.84465042387787448 |
| width > 1 | EVALUATED MARGIN (`C01`/`F10`) | EVALUATED MARGIN (`C01`/`F10`) |

The propagation machinery built for `OC-59` was right and is kept: labels
follow the **terms**, not the report, and `regression-docs.sh` still refuses any
document that writes "certified floor" without saying which width or reading.
What changed is one input to it.

### The lesson, which is not the one OC-59 drew

`OC-59` treated a disagreement between my derivation and the record as evidence
against **the record**. A consistent ratio between two derivations is evidence
that they are computing **different things**, and the first question is which —
not which one is wrong. Had I asked that, the answer was one line away in
`OC-22` Part 3's own table, which lists the collision and compression ceilings
side by side with compression 4.3× larger.

---

## OC-63 — the grid-edge sweep across the audit's tooling: 29 examined, 2 at risk, both feeding `C22a`

Rule 9 says a sweep reporting its extremum at a boundary of its own domain has
found the edge of where it looked, not an extremum. `OC-59` made that error
once. This is the sweep for others.

**Every parameter sweep in the audit's tooling was examined** — nine files: the
six oracles, `c22_bound.cpp`, `r1_corpus_scan.py`, and
`f13_nan_reachability.c`. 29 sweeps.

| verdict | count | meaning |
|---|---:|---|
| **AT-EDGE-RISK** | **2** | an arbitrary domain whose extremum could sit at the edge, with no interiority check |
| SAFE-BOUNDED | 10 | the domain edge **is** the physical or mathematical limit, so an extremum there is legitimate |
| NO-EXTREMUM | 17 | sweeps that tabulate every row, or solve for a root, and report no extremum |

**Most are safe for a reason worth stating**, because it is the distinction rule
9 turns on. A probability from a non-zero count cannot go below `1/n`; a count
is an integer in `[0, N]`; an alphabet size is `2..256`; `H_I ≤ 8` because the
tool supports 1–8 bit symbols; `h_col` is *exactly* 1 above `X' = 2.5`, so
there is zero sensitivity beyond that cap. An extremum on one of those edges is
the answer, not an artefact — and several of them are independently confirmed
by a closed form evaluated **at** the edge, which is the strongest version of
the check.

Two more earn a mention. `restart_cutoff_anchor.py`'s `tool_model_cutoff()` has
**no fixed upper window at all**: it steps `m` upward until the predicate
holds, which is rule 9's first remedy implemented rather than argued.
`zalpha_ceiling_by_n.py`'s `worst_proportion()` is the fixed version of the
very sweep that produced the rule, and its docstring carries the error it was
fixed from.

### The two that are at risk, both in `oracles/p_local_exact.py`

Both feed **`C22a`** — the `P_local` quantisation term — which
`entropy_floor.py` **does** subtract.

**1. The constant `c` (lines 107-113, reported at 132 and 140-141).**
`c := max near-root ratio` is a maximum over **four** axes, every one an
author-chosen list: `N` ending at `2^40`, `r` ending at `256`, and the
root-offset exponent `k` ending at `12` — `k` being a pure refinement window,
`p = p*(1 ± 10^-k)`. It is then asserted as a universal bound,
`eps_f ≤ c·(N+1)·2^-52`, multiplied into the `P_local` ceiling, **and applied
at `N = 2^53`, beyond the top of its own calibration grid.** No interiority
check, no extension, and the argmax's `r` and `k` are never printed.

**2. The inflation and `K` maxima (lines 150-152, reported six times at
176-185).** `rs` is truncated at `1024`; `lds` is truncated **at the top** at
`1/2`, while production's `ldomain = curMax` ranges over `[1/k, 1)` with
`k ≤ 256` (`utils.h:1207,1232,1234`) — so the largest swept `ldomain` is short
of the physical maximum. The sharp edge is circular: line 164 builds the
ceiling from finding 1's grid maximum, and line 178 then validates *"worst
ratio inflation/ceiling … must be ≤ 1 for the ceiling to hold"* as a maximum
over **this** grid. **A bound calibrated from one grid maximum and validated
against another is a bound only if both maxima are interior, and neither is
checked.**

Partial credit where it is due: line 181 anchors `min |f'(p*)|·p*` to an
analytic model which independently predicts that `K`'s maximum belongs at
`r = 2`, the smallest physically meaningful run length. That covers `K`'s
`r`-direction and nothing else.

### Direction, and what it costs

If either maximum sits at an edge, `c` is a **lower bound** on the true error
constant, every ceiling built from it is **too small**, and the `C22a` term the
floor subtracts is **too small** — which is permissive, the direction that
matters. The magnitude is reassuring and does not settle it: `C22a` is
`8.08e-15·(N+1)`, i.e. **8.08e-09 bit** at `n = 1e6`, five to six orders below
the `C22c` term beside it. Even a large multiplicative error in `c` would not
move the floor at this length. **That is a reason not to panic, not a reason
not to check**, and the asserted form of the claim — a universal bound — is
wrong independent of its size.

### Measured, not left as a warning

`OC-59`'s lesson is that the answer here is to extend the grid and look, so the
`c22_bound` production harness was rebuilt and the oracle run.

**Where each maximum actually sits:**

| maximum | argmax | at an edge? |
|---|---|---|
| `c` = **0.4991** | `N = 10 000` (5th of 12), `r = 3` (2nd of 7) | **interior in both axes** |
| worst inflation, **+3.0097e-06 bit** | `N = 1e9` (15th of 18), `r = 2`, `ldomain = 2^-30` | `N` interior; `r = 2` is the **physical minimum** run length; `ldomain` is at the **smallest** swept value |
| `K` = 1.6189e-14 | `N = 5`, `r = 2` | `N` interior; `r = 2` physical minimum |
| inflation/ceiling ratio | — | **0.928**, so the ceiling holds with 7 % margin |

Two of the three concerns dissolve on measurement:

- **`c`'s argmax is interior in `N` and `r`.** The two axes whose truncation
  looked most suspect — `N` ending at `2^40`, `r` ending at `256` — are not
  where the maximum lives, and nothing about extending them can raise it.
- **The `ldomain` truncation does not bind.** The worry was that `lds` stops at
  `1/2` while production's `ldomain = curMax` reaches toward 1. But the maximum
  sits at the **other end**, `2^-30`, which is *below* production's physical
  range of `[1/256, 1)` — so the sweep is **wider than production needs** in
  the direction that matters, and the top truncation is irrelevant to the
  maximum. `r = 2` is likewise the physical floor, not an arbitrary edge.

**And the last axis closed too.** The root-offset refinement window
`p = p*(1 ± 10^-k)` was truncated at `10^-12` — the one axis on which a closer
approach to the root could still raise `c`. Extended to `10^-21` on the
oracle's own grid, the same oracle with one list changed and nothing
reimplemented:

| | near-root points | `c` | argmax |
|---|---:|---:|---|
| published grid, `k ≤ 12` | 592 | **0.4991** | `N = 10 000`, `r = 3`, `p = 0.01005119221829661` |
| extended, `k ≤ 21` | **1036** | **0.4991** | **identical** — same `N`, same `r`, same `p` |

Nearly double the points, nine extra orders of approach to the root, and the
maximum does not move by a digit. **The argmax is interior in every swept
axis**, so the grid value is the **supremum** rather than a lower bound on it,
and `eps_f ≤ c·(N+1)·2^-52` is a bound. (`c` = 0.4991 sitting just under ½ is
what a half-ULP evaluation error looks like, which is some corroboration of the
form as well as the value.)

**`C22a`'s supremacy is established.** So at width 1, where `C01`/`F10` is
excluded by proof and `C22c` is a derived ceiling, **both readings are
certified floors**:

| | literal reading | F07 reading |
|---|---|---|
| width 1 | **CERTIFIED FLOOR**, 0.84129042387787445 | **CERTIFIED FLOOR**, 0.84465042387787448 |
| width > 1 | EVALUATED MARGIN (`C01`/`F10`) | EVALUATED MARGIN (`C01`/`F10`) |

### The label moved four times in two rounds, and that is the point

Down for `C22c`, back up when `C22c` proved to be a bound, down for `C22a`, back
up when `C22a`'s argmax proved interior. Each move was forced by a measurement
and each was recorded rather than smoothed over. A label that never moves under
this much scrutiny is not a label anyone checked.

### Why the label was downgraded first, and why that was right

`C22a` is subtracted by **both** readings. While its supremacy was
unestablished, a certified claim rested on an uncertified input, so neither
reading could be called a certified floor — and the fact that 8.08e-09 bit
cannot move the figure was **not** a defence, because that is precisely the
argument rejected for `C22c`. **The question is whether every subtracted term
IS a bound, not whether an unbounded one is small.** The downgrade stood for as
long as the question did, which was about an hour.

---

## OC-64 — three live false passes, two inside the enforced suite; and the shape swept

An outside session audited the instruments against the standing rules, in a
clone, unprimed. Nine of its findings were observed under deliberate mutation
rather than inferred. Each is reproduced here before being accepted.

### The three, all reproduced

**1. `regression-input-identity.sh` — in the enforced suite.** Its assertions
sit in a `python3 - … <<'PY'` block in **statement position** with the status
discarded, the script sets only `set -u`, and line 70 is an unconditional
`PASS`. Mutating the `sha256Scope` the block asserts:

```
Traceback (most recent call last):
  File "<stdin>", line 6, in <module>
AssertionError
regression-input-identity: PASS (replacement rejected as result identity; …)
exit=0
```

`N-07`'s regression test established nothing.

**2. `sanitizer-restart-c01.sh` — the same shape.** Driven with a stand-in
binary writing `errorLevel = 1`, which is the **first thing it asserts
against**: traceback, then `PASS`, exit 0. It also violated rule 4 —
`EA_RESTART_SANITIZER_BIN` defaults to `../ea_restart` and nothing declared
which artefact was measured.

**3. `regression-estimator-guards.sh` — a different mechanism, same family.**
`check_no_abort` asked only *"did it abort?"*, so a run that never happened
answered *"no"* and counted as a pass. With the six inputs removed immediately
before the checks, **seven checks reported non-failures**. An absent input is a
broken harness, not a guard holding.

### Repaired, and shown failing

| | mutated | unmutated |
|---|---|---|
| `regression-input-identity.sh` | **FAIL**, exit 1 | PASS |
| `sanitizer-restart-c01.sh` | **FAIL**, exit 1 | — |
| `regression-estimator-guards.sh` | **6 × HARNESS FAULT**, exit 1 | PASS |

The assertions now gate the verdict (`if ! python3 … then … exit 1; fi`),
`sanitizer-restart-c01.sh` declares the build state of the binary it actually
uses, and `check_no_abort` requires the input to be present before it will
interpret an absence.

**One repair of mine overshot and was caught by its own control.** I first
added a positive output marker to `check_no_abort` — requiring assessment text
in the output — and every legitimate check failed, because those runs use `-q`
and print nothing to match. Removed, with the reason recorded at the site: the
discriminator that works is the input-presence test, because *neither* the
abort test *nor* the exit status can tell a run from a non-run here — both are
0 either way.

### The sweep: the shape, not the instances

Two mechanical patterns, swept across every shell instrument in
`cpp/selftest`, `tools`, `.github/scripts`, the oracles and the reproducers:

- **A** — an interpreter heredoc containing assertions, in statement position,
  status not read (not in `if`/`while`, not negated, not captured, not chained)
  in a script without `set -e`.
- **B** — an unconditional top-level `PASS` with no counter or status guard.

> **THE DENOMINATOR IN THIS TABLE IS WRONG — CORRECTED IN `OC-65`.** "53" both
> omitted whole directories (`.github/workflows`, the generators, the
> 2026-10-09 audit, `repairs/`) and inflated the remainder with four
> `__pycache__` files. The live instrument set is **70**, and the three
> extensionless shell instruments — `selftest`, `generate-refdata`,
> `compareresults.pl` — were never swept. They have since been swept and the
> conclusion below held, but it held by luck of the denominator rather than by
> the sweep's design. The inclusion rule is now written down once in
> `audits/INSTRUMENT-INVENTORY.md`.

| | |
|---|---|
| instruments in the repository | ~~53~~ **70 live / 79 frozen** (`OC-65`) |
| shell instruments swept for A and B | **33** of the live set, then the 4 missed runnable artefacts swept separately |
| Python instruments checked for the analogous unconditional success print | all; **none found** |
| **pattern A remaining after the repairs** | **0** |
| **pattern B remaining after the repairs** | **0** |

Four hits were adjudicated by hand and all four are **false positives of my
detector**, which is worth recording because the raw count would have been
misleading:

- `tools/build-provenance-canary.sh:175` — the heredoc is the **last statement
  of a function**, so its status *is* the return value and the caller reads it.
- `verify-fixture-inventory.sh:107` — every prior check `exit 1`s on failure,
  so reaching the `PASS` means they all passed.
- the two repaired files — their `PASS` is now after a `fi`, which the detector
  does not model.

So the sweep's value is the **denominator plus the adjudication**, not the
count. The honest statement: **two instances existed, both are repaired, and no
third exists among the 33 shell instruments under either pattern.**

### And the record that let them sit there

`DEAD-GUARD-SWEEP.md` had both of the first two, correctly described, filed as
*"both on the repair branch"* and therefore not live. **The 2026-10-15 merge
put them on `master`**, and one went into the enforced suite. Nothing re-read
the sweep when the branch merged. Corrected with a supersession banner and the
"repair only" column struck through on both rows.

**A sweep that records a finding's location as a branch has to be re-read when
that branch merges.** That is a new obligation and it belongs with the merge
rule that already covers files enumerating other files.

---

## OC-65 — the denominator: two readers disagreed by seventeen, and the rule was never written down

An outside session counted **70 live instruments and 79 frozen**. `OC-64`
reported **53**. A disagreement about the denominator is a disagreement about
what every *"count examined alongside count found"* figure in this repository
means, so it is settled here before any further sweep.

### Mine was wrong twice over

| | |
|---|---|
| **omitted** | `.github/workflows` (CI workflow definitions, which emit verdicts the record cites), `audits/2026-10-11-independent-audit/generators`, the whole `audits/2026-10-09-independent-audit`, and `repairs/*/rerun.sh` |
| **inflated** | by four `__pycache__/*.pyc` files, which a `grep -v __pycache__` on the wrong path component failed to drop |
| **missed, and this is the substantive one** | four **runnable artefacts an extension-matched glob cannot see**: `cpp/selftest/selftest` and `cpp/selftest/generate-refdata` (Bourne-Again shell, no extension), `cpp/selftest/compareresults.pl` (Perl), and `truepad-unattested-tools.mjs` (node). **`selftest` is the instrument the entire suite calls.** |

**The frozen counts matched exactly at 79 on the first attempt.** That is what
localised the disagreement: it was confined to the live set, so it was about the
**rule**, not about the tree.

### The rule, now written down once

`audits/INSTRUMENT-INVENTORY.md`:

> An instrument is a **runnable** artefact that produces a number or a verdict
> which a document or a claim then cites.

with the three consequences that were each got wrong once — membership decided
by `file -b` and the executable bit rather than by extension; **sources** counted
and their compiled artefacts not (`outside-battery-check` and
`restart-report-label-test` are Mach-O outputs of counted `.cpp` sources, and
counting them double-counts); and **producers** counted, not the manifests and
reference data they cite.

Applying it gives **70 live**, their number exactly, with the one apparent
residual explained by the artefact rule. Frozen stays **79**, counted apart
because it is **dated evidence**: re-running it would not re-date it, and
changing it would destroy it.

### What it cost, and what it did not

`OC-64` swept 33 shell files against an unstated denominator. **33 of 70 is
under half.** The four missed runnable artefacts have since been swept for both
patterns: none has an interpreter heredoc at all, and `selftest`'s `PASS` is
guarded by `fail_count -eq 0`. So `OC-64`'s conclusion — zero remaining
instances of either pattern — **survives the correct denominator**. It held by
luck of which files happened to carry the pattern, not by the sweep's design,
and that distinction is the finding.

**Two careful readers disagreeing by seventeen is itself the finding**, and the
reason is that neither inventory was written down. One of the two had been the
basis of a reported sweep. Now a sweep cites the inventory file and the rule it
applied, and a reader can reproduce the count with the command in it.

---

## OC-66 — the aggregator discarded its components' evidence, an abstention counted as a pass, and SHAPE-07/03 swept over the tooling itself

### The aggregator, and the consequence measured

`run-all-checks.sh` captured each script's output and, on success, printed only
the label. So every `[build-state]` line the five declaring scripts emit was
**thrown away one layer up**. Rule 4's stated point is that a result *without*
that line is visibly incomplete; the aggregator made every result look the same.

**Measured, not argued.** Binaries built `-DNDEBUG` — all three digests
differing, the probe reporting `asserts=NDEBUG` against `asserts=LIVE` — then
the full suite run on both arms:

| | arm A (asserts live) | arm B (`-DNDEBUG`) |
|---|---|---|
| summary | 22 passed, 0 failed | 22 passed, 0 failed |
| per-check verdicts | **identical, check for check** | |
| occurrences of `build-state` in the output | **0** | **0** |

The suite could not distinguish a build with **every assert in `lrs_test.h`
compiled out**, and said nothing about which it had measured. No verdict
flipped, so this was **not a live false pass** — it is `OC-42`'s exact error
made undetectable again, which is worse, because `OC-42` was caught by looking
and this could not be.

**Fixed, and verified by re-running both arms.** Declarations are surfaced under
each check, the summary reports `build-state: N of M checks declared the
artefact they measured`, and a run where **none** did says so on stderr. The two
arms now **differ** — `asserts=LIVE` against `asserts=NDEBUG`, with the digests
— where before they were byte-identical. The summary line itself is unchanged
because the coverage count prints above it: the inventory mutation harness
matches that line exactly and depends on it.

Today's coverage is **4 of 22**. That is now a visible number rather than an
invisible one, and raising it is a separate piece of work.

### An abstention counted as a pass

`regression-platform-deltas.sh` printed `SKIPPED (not a pass)` and **returned
0**. On Linux — the platform the x86-64 gate runs on, and where `selftest`
reports no differences at all — that abstention contributed one of the 22
without exercising anything. **Saying "not a pass" in prose while returning the
pass code is the defect, not the prose.**

It now exits **2**, which `run-all-checks.sh` already reports as `COULD NOT
RUN`, apart from both pass and fail, with its own comment that a check which did
not execute supports no claim. The right channel existed and was not used.

**Consequence for the record, stated plainly:** `A06`'s *"four failures the
audit required"* were established **on macOS and not on Linux**, where that
check has never exercised the manifest at all.

The x86-64 gate expects the abstention rather than breaking on it: `N-1` passed
with exactly one could-not-run, a gate naming **which** check abstained, and a
gate that build state reached the summary. **An abstention is allowed; an
unexplained one is not.**

### SHAPE-07 and SHAPE-03, swept over the audit tooling

The observation that drove this: the shapes are right and **the sweep's
denominator was the wrong set.** `SHAPE-07` was written from the ten-estimator
battery and applied to production, never to the instruments. Nine aggregates in
the tooling were examined.

**`SHAPE-07` — an aggregate reported as one number, computed as an extremum over
components, discards every component's evidence except the extremum's.**

| instrument | verdict |
|---|---|
| `run-all-checks.sh` | **INSTANCE, fixed above.** The clearest case: a per-check pass/fail tally that discarded the build-state evidence entirely. |
| `zalpha_ceiling_by_n.py` / the `C22c` term | **INSTANCE, and it already cost something.** `C22c` is a **max over estimator families**, and the non-binding families' values were not carried — which is exactly how `OC-62` happened: I derived the Collision family, compared it against the Compression tabulation, and reported the record as unreproduced. The aggregate had discarded the evidence that would have told me which family bound. Now all three families print with their own rows, so the binding one is identifiable. |
| `entropy_floor.py`'s `h'` | **not an instance.** It is a `min` over candidates, but both are printed with `<- binds` marking the extremum, so the component evidence is carried. |
| `mutation-lib.sh`, `oracle-selftest.sh`, `check-platform-deltas.py`, `c16-c23-matrix.sh`, `windows-facts.sh` | **not instances.** Each names its failing components (`MUT_FAIL_LABELS`, per-case lines, per-row problems, per-cell expectations, per-gate verdicts) rather than reporting only a count. |

**`SHAPE-03` — an empty accumulator reads as success.** Its own worked example
is `compareresults.pl`, which **my `OC-64` sweep never covered**, because it has
a `.pl` extension and the sweep was extension-matched on `.sh` (`OC-65`).
Measured today:

| case | before | after |
|---|---|---|
| reference non-empty, output empty | exit 1 | exit 1 |
| output non-empty, reference empty | exit 1 | exit 1 |
| **both empty** | **exit 0, `Maximum delta: 0`** | **exit 2, "NO COMPARISONS WERE MADE"** |

The two single-sided holes were already closed by the second loop. Both-empty
was still reachable: zero comparisons, zero status, agreement reported. It needs
a corrupted reference, which the fixture manifest's digests also guard, but **a
comparison tool must not report agreement when it compared nothing.** It now
counts comparisons, refuses zero, and prints the count it made (59 on a genuine
pair).

---

## OC-67 — every reported denominator, re-derived; and SHAPE-07's third instance fixed

`OC-65` corrected one sweep's denominator. The deeper point is that **every
sweep this project has reported had a denominator, and every one was derived by
hand in the command line that produced it.** None was reproducible. So each is
re-derived here against `audits/INSTRUMENT-INVENTORY.md`.

This is a counting exercise. Where a denominator was understated, the sweep's
conclusion is not automatically wrong — but it held **by luck of which files
carried the pattern**, not by design, and each is marked accordingly rather
than silently re-run.

### The pairs

| sweep | its enumeration rule, as actually used | reported | canonical rule, same scope | understated? |
|---|---|---:|---:|---|
| **`DEAD-GUARD-SWEEP.md`**, fork at `f069898` | "every tracked shell script" = `git ls-files '*.sh'` | **32** | 36 shell-family instruments | **yes, by 4** |
| **`OC-64`** shape sweep | `*.sh` under five named directories | **33** | 70 live instruments | **yes** (corrected in `OC-65`) |
| **`OC-63`** parameter sweeps | nine files named by hand | **9 files / 29 sweeps** | 36 live instruments contain a sweep construct | **yes, as a candidate set** |
| **rule-7 negative-fixture sweep** | `regression-*.sh` plus named extras | **28 scripts** | 36 shell-family instruments | **yes, by ~8** |
| **`OC-66`** SHAPE-07/03 aggregates | nine aggregates named by hand | **9** | — | hand-picked, but exhaustive for "reports one number over components" |
| **instrument inventory** | extension-matched glob | **53** | **70 live / 79 frozen** | **yes** (`OC-65`) |
| "792 status-bearing commands" | *the outside session's figure, not mine* | — | — | **cannot re-derive**: I do not have its enumeration rule |

### The sharpest one, because the sweep could not see its own example

`DEAD-GUARD-SWEEP.md`'s method lists, in its own words, *"a check driven by an
extraction that can return the empty set, with no assertion on the size of that
set"*. That is **exactly** `compareresults.pl`'s defect — and
`compareresults.pl` is `SHAPE-03`'s named worked example. Its rule was
`git ls-files '*.sh'`, so **the file that exemplified the pattern was invisible
to the sweep that defined the pattern**, and it was still broken when `OC-66`
finally looked at it yesterday.

All four files that rule could not see existed at `f069898`, the sweep's own
commit: `cpp/selftest/selftest`, `cpp/selftest/generate-refdata`,
`cpp/selftest/compareresults.pl`, `truepad-unattested-tools.mjs`. One of the
four was genuinely broken. **A hit rate of one in four among the invisible set,
against seven real dead guards found in the thirty-two visible ones**, is not a
reason to assume the rest are clean.

### Which are worth re-running on the corrected set, and which are not

| sweep | re-run? | why |
|---|---|---|
| **`DEAD-GUARD-SWEEP.md`** | **YES, highest value** | a demonstrated hit among the four it could not see, and its detectors (`deadguard.py`, `vacuous2.py`) cover only `.sh` by construction — which is the Group 4 item about wiring or retiring them |
| **`OC-63`** parameter sweeps | **YES** | the generators sweep parameters and were excluded entirely by a hand-picked file list |
| **`OC-64`** shape sweep | **already done** | the four missed artefacts were swept in `OC-65`; conclusion held |
| **rule-7 negative fixtures** | **low value** | the missed artefacts hold no negative fixtures: `selftest` and `generate-refdata` build and compare, they do not construct inputs expected to be refused |
| **`OC-66`** aggregates | **no** | enumerated by behaviour ("reports one number over components") rather than by file type, so the extension blind spot does not apply |

**The general defect is not an extension pattern and is not fixed by adding
`.pl` to one.** It is that a sweep's scope was expressed as a glob in a shell
history rather than as a rule in a file. `audits/INSTRUMENT-INVENTORY.md` is the
fix; citing it is the obligation.

### SHAPE-07's third instance, fixed

`C22c` was stored as the maximum over estimator families, with the components
discarded — and that is how `OC-59` happened. The same remedy as the other two:
**emit the components, name the binding one, keep the margin.**

```
  C22c ZALPHA vs the literal 2.576         3.360e-03    derived ceiling, at n = 1000000
      compression  3.360e-03   <- BINDS
      collision    7.840e-04
      proportion   6.887e-05
      binding family: compression; margin to collision: 2.576e-03 bit (4.3x)
```

A figure whose binding family cannot be identified cannot be audited by anyone,
including by me next month. `C22C_BY_N` is now **derived** from the family
table rather than stored beside it, so the maximum cannot drift from its
components.

### The diagnostic method, recorded because it is reusable

> **When two inventories disagree, find the subset where they agree.**

The outside session counted 70 live and 79 frozen; I had 53. The **frozen
counts matched exactly at 79 on the first attempt**, and that single fact did
all the work: it localised the disagreement to the live set, which meant the
disagreement was about the **rule** and not about the tree — because an
inventory that mis-enumerated the tree would have missed in both halves.

That is faster than arguing about totals, and it points at the definition
instead of the count. Recorded as its own entry in
`audits/BUG-REPAIR-GUIDE.md`, deliberately not attached to any numbered rule
while the numbering is being repaired (Group 3).

**Why it works, stated generally:** an inventory that mis-enumerates the *tree*
misses in every subset. An inventory that applies the wrong *rule* misses only
where the rule bites. So agreement on one subset and disagreement on another
localises the fault to the definition — and names the subset where the
definitions differ.

---

## OC-68 — the rule inventory repaired: numbering, a rule that does not exist, a false worked example

Fixed before anything cites a rule number again.

### The numbering

The guide's instrument list was headed **"Three rules about instruments"** and
contained **five**, with its entries numbered **1, 2, 3, 4, 5, 4** — six list
items, because the labelled-read rule appeared **twice**: once as a bare stub
numbered 5, then again in full numbered 4, which also numbered the build-state
rule.

Consequences, all live until today:

- **build-state and labelled-read were both "rule 4"**;
- **rule 3's own text cited "rule 4"**, which had two referents, and meant the
  one that is *not* numbered 4 in both places;
- the same rule carried **three different numbers** across the repository, so
  following "rule 3" from `ORCHESTRATOR-CHECKS` landed a reader on the platform
  rule.

Repaired canonically: **five rules, numbered 1–5**, the duplicate stub removed,
the heading corrected, and rule 3's citation now naming its referent
("instrument rule 4, build state").

### A cited rule that does not exist

**`RULE 12` was cited three times and is defined nowhere in this repository**,
with **a different principle ascribed at each site**:

| site | the principle actually relied on |
|---|---|
| `BUG-REPAIR-GUIDE.md` instrument rule 2 | an absent or malformed result is not a result *about the subject* |
| `OC-?` (the refdata pinning argument) | a reference must be fixed by something **other than** the artefact it judges, or agreement is circular |
| `OC-?` (the build-state mechanisation) | a rule that depends on being remembered will be forgotten, so it is built into an instrument |

Its canonical text lives in TruePad. Until it arrives, **each citation is
replaced by the principle that citation relies on, stated in full, so the text
stands without the reference.** A rule cited with three meanings is worse than
one uncited.

**The same is true of `V1`/`V2`**, which the round's instructions asked me to
reconcile: **no V-series rule exists in this repository.** The obligation said
to have been lost in restatement cannot be restored here, because neither
version is here. Stated rather than guessed at.

### Rule 10 (vacated) is not an instrument rule

It is about how a **finding is ranked in the record**, and it applies to **0 of
the 70 instruments** — the test being whether a harness could break it, and
none can. Moved to a new **Record discipline** section as **R1**, numbered in
its own namespace so a citation can never again be mistaken for an instrument
rule. **Rule 10's number is vacated and is not reused.**

### Rule 7's worked example was filed in error

Three findings were filed under rule 7 as evidence it is load-bearing. **None
is an instance of it.** Two were instances of **instrument rule 1** (a mutation
that did not land) and the third was rule 7's own **staleness corollary** about
hardcoded counts. Rule 7 says: *build a negative fixture by mutating a genuine
artefact and assert its baseline is accepted.* No filed finding did that.

`OC-43`'s warning applies to the filing itself — *a measurement is about the
artefact it ran against* — and **a worked example is a measurement about a
rule**. Filing a near-miss under a rule makes the rule look tested when it is
not.

**Replaced with a real instance:** `cpp/selftest/regression-platform-deltas.sh`.
Its negatives are mutations of a genuine `selftest` transcript, one field at a
time; it asserts the unmutated transcript is accepted **first** and refuses to
read its own negatives if that baseline fails; and it carries a third outcome
for a platform where the premise does not hold. It was written **before** the
rule was, which is why it is the example rather than the exhibit.

### And the check, so the next one is caught

`regression-docs.sh` now **fails on a cited rule number with no definition**.
Definitions are the numbered entries of the instrument list and the `### Rule N`
headings; a heading reading `VACATED` is **not** a definition. Record-discipline
citations are checked in their own namespace.

It found two on its first run:

- `FINDINGS-TRACKER.md:128` cited "instrument rule 10 (vacated)" — **a citation I
  orphaned myself**, minutes earlier, by vacating that number. Repointed to
  Record discipline R1.
- `EXCLUSION-MAP.md:497` — a **false positive**: the prose *"raw 2.0 vs rule
  0.5"* matched as a citation of rule 0. The pattern now requires `[1-9]` and
  rejects a following decimal.

Both controls verified: a citation of a nonexistent rule 47 fails the check,
and a citation of the **vacated** rule 10 fails it too.

---

## OC-69 — the two unnumbered regression rules: the lost obligation restored, and how I failed to find them

### I searched for the label instead of the location

I reported that **no V-series rule exists in this repository**. That was wrong,
and the way it was wrong is the same shape as several findings in this round.
`V1` and `V2` are labels an outside session **coined** for two rules it found
**stated without numbers**, so a search for the identifiers came back empty and
I concluded the rules were absent. The citation gave me a location —
`FINDINGS-TRACKER.md:1308` and `:1313` — and I searched for the name instead of
reading the line.

**That is the extension-glob error in another medium.** An enumeration keyed on
how a thing is *named* cannot see a thing that is *unnamed*, whether the naming
is a file suffix or a rule label. `cpp/selftest/selftest` was invisible to a
`*.sh` sweep for the same reason these two were invisible to a `grep V2`.

**The quotation was accurate on both sides**, which is worth recording because
the instruction allowed that it might not be: the tracker's text reads exactly
as quoted, and the guide's step 5 keeps the platform claim and the
platform-independent-source instruction and **drops "Say so when reporting
it."** No finding against the audit.

### The rules, and the sentence that went missing

| | |
|---|---|
| **tracker** (`FINDINGS-TRACKER.md`, "a regression is assumed vacuous until it has failed") | *"A regression that has only been run on one platform is evidence about that platform. **Say so when reporting it.** Where a figure is compared, read the expected value from a platform-independent source (`refdata/`) with a stated tolerance…"* |
| **guide** (step 5, third bullet) | *"compare figures against a platform-independent source … A check carrying one platform's value is evidence about that platform: REV-005 passed on macOS…"* |

The reporting obligation existed in **one** statement of the rule and nowhere
else, for an unknown length of time. **Paraphrase is how it went missing**, so
the repair is not to paraphrase more carefully.

### Canonical: the guide. Pointer: the tracker.

The guide's step 5 is now the **only copy of the rule's text**, with the
obligation restored in capitals, because step 5 is the document consulted
*while doing the work* and "say so when reporting" is an instruction to the
person doing it. The tracker keeps all of its **evidence** — the seven guards,
`REV-005`, the shared-sitting diagnosis — and its statement of the rule becomes
a pointer. A rule stated twice with different content is the condition that
produced this finding, and it is the condition just repaired for the numbered
rules (`OC-68`).

**And the rule now applies to itself.** `A06`'s four required failures were
established on macOS and **not** on Linux, and that is said at the site
(`OC-66`) because of this obligation — which had been missing from the
statement a reader follows.

### They do not join the numbered series, deliberately

They are about **regressions** specifically rather than instruments generally,
they predate the numbering, and the next free number is **12** — already cited
three times here as a rule whose canonical text lives in TruePad (`OC-68`).
Manufacturing that collision to tidy a list would reintroduce exactly the
ambiguity the numbering repair removed. The citation check keys on numbers, so a
named lesson is outside its scope by construction and nothing dangles.

### The timing of a check is part of the check

Recorded at the check itself. `regression-docs.sh` **passed when I ran it
directly and failed in the suite**, because I ran it **before writing the text
it would judge**. A check run before the writing it judges is the same shape as
reading a figure in the command that writes it. **The suite run is the one that
counts**, and it runs after the text exists.

---

## OC-71 — build-differential.sh: a vacuous agreement, and rule 8 met rather than assumed

It declared build state exemplarily — `bs_require LIVE` and `bs_require NDEBUG`,
refusing a mismatch — and still returned an agreement that could mean nothing.

### Two empty measurements compared equal

Both fallbacks were the **same literal**: `norm_json … || echo '{}'` on a failed
normalisation, and `"(no json)"` on a missing report. If **both** arms failed,
`diff` was silent and the script printed `AGREE`. The verdict-line comparison
had the same hole: if neither output contained a `** Passed/Failed` line, the
two `grep`s were both empty and `diff` was silent again.

Closed two ways, because either alone is defeatable:

- the sentinels are now **distinct per arm** (`NO-JSON-live` against
  `NO-JSON-ndebug`), so two failures **cannot** compare equal — a construction,
  not a test;
- each comparison **asserts it had something to compare** and reports the count
  (`compared 2 verdict line(s) per arm`, `compared 33 normalised JSON line(s)
  per arm`) before agreement is read from it.

### Rule 8's obligation, met — and it changed the instrument

Five fields were normalised away as "legitimately differing between
runs/builds". That was an assumption. Rule 8 requires a **self-comparison** and
a **live-sensitivity check**, so both now run before any arm-to-arm comparison.

**The self-comparison found three of the five were STABLE:**

| field | two runs of one build | disposition |
|---|---|---|
| `dateTimeStamp` | varies | dropped |
| `commandline` | varies | **normalised, not dropped** — only the `-o` path and `argv[0]` differ, and `argv[0]` differs *by design* because the two arms are different binaries; the flags and the input path stay compared |
| `filename` | **stable** | **kept** |
| `sha256` | **stable** | **kept** |
| `toolVersion` | **stable** | **kept** |

**Two of those identify the input.** Dropped as they were, this differential
**could not have noticed the two arms assessing different files** — which is
the one thing a build-differential must never miss. It now compares 33
normalised JSON lines where it compared 29, and the self-comparison reports
`STABLE, so dropping them HIDES difference: none`.

**The live-sensitivity check is not decorative, and a control proved it.**
Breaking `norm_json` so that both arms' normalisations fail makes their outputs
identical and `diff` silent — the exact vacuous condition — and the sensitivity
check **fires first**, reporting that the comparator cannot see a perturbed
kept field and failing the run before any agreement is read:

```
build-differential: FAIL (the comparator cannot fire; agreement from it means nothing)
```

So the vacuous path is guarded twice, and the outer guard is the one that
catches a globally broken comparator. The inner sentinels catch the case the
outer one cannot: **one** arm producing no report while the other does.

---

## OC-74 — the comparator sweep: 20 comparators, 15 with assumed exclusions, 10 blind to identity

`build-differential.sh`'s result generalises: **every comparator has an
exclusion list, and every exclusion is an unstated claim that the field
legitimately differs.** Those claims are checkable, and when its five were
checked, three were false (`OC-71`). So all 21 candidate comparators were
inventoried.

| | |
|---|---:|
| files examined | **21** |
| comparators | **20** (`generate-refdata` writes, it does not compare) |
| with at least one **assumed** exclusion | **15** |
| **exclusions touching input, instrument or build identity** | **10** |

Fully justified — every exclusion measured or proved:
`outside-battery-mutation-test.sh`, `outside-battery-check.cpp`,
`build-provenance-canary.sh`, `entropy_floor.py`, `build-differential.sh`.

### The serious category, reported first

An exclusion touching identity does not weaken a comparison, it **voids** it.
Ten comparators, in two tiers.

**Tier 1 — identity excluded from the comparison outright:**

1. **`compareresults.pl`** — its line filter selects only
   `/(Estimate:|Assessed|^H_original|^H_bitstring)/i`, so *"Opening file"* and
   *"Loaded N samples of K distinct W-bit-wide symbols"* were never compared.
2. **`selftest`** — delegates to it, and pairs output with reference by a
   **filename transform alone**. Its only instrument check is `[ ! -x ../ea_non_iid ]`.
3. `check-platform-deltas.py` — `b['cc'] in cc`, a **substring** of a compiler
   identity read from the host's current `$CXX` rather than from the build under test.
4. `verify-fixture-inventory.sh` — input↔reference bound by filename only; the
   manifest's own digest **printed, never verified**.
5. `p_local_exact.py` — `HARNESS = sys.argv[1]`; the binary supplying every
   tool-side number is never identified.
6. `restart_decision_exact.py` — reads `restartCutoffMethod` and **drops it**,
   so agreement with an exact build and with a printed-binomial build report identically.
7. `regression-outside-battery.sh` — tool taken from the environment or built
   in-line with unrecorded flags, while pinning FFT output to four significant figures.

**Tier 2 — identity reported but not compared**, because `bs_print` has no
failure path: `regression-output.sh`, `regression-restart.sh`,
`regression-subset.sh`, `regression-iid-json.sh`.

### Two were live and are repaired, both reproduced first

**1. The flagship self-test could not tell which file it read.** Measured: a
copy of `refdata/normal.res` with its identity lines rewritten to claim
`SOME-OTHER-FILE.bin` and *"42 samples of 3 distinct 2-bit-wide symbols"*
compared **equal** to `normal.bin`'s real output — 1,000,000 samples, 179
distinct 8-bit symbols:

```
Maximum delta: 6.93196230865696e-15
normal.out: 98 value(s) compared
exit=0
```

`compareresults.pl` now extracts and compares the basename, sample count,
distinct-symbol count and symbol width, **refusing (exit 2)** when either side
lacks them and failing on a mismatch. Verified three ways: the genuine pair
passes reporting `identity normal.bin / 1000000 samples / 8-bit matched`, the
identity lie fails, and a wrong fixture fails **on identity** rather than
incidentally on its numbers.

One detail worth keeping: the tool now prints `Loaded file: '<path>' (SHA-256
hash …)` where the committed references, which predate that change, say
`Opening file: '<path>'`. The same field in two spellings — so the match is on
the **field**, not on one side's wording, which is instrument rule 3's
corollary applied to a comparator's own input.

**2. `regression-restart.sh` claimed 64 comparisons from zero.** `for triple in
; do` iterated nothing, `cbad` was never touched, and the check printed *"C23
both cutoffs match the exact oracle: 32 H_I values × 2 columns"* — in the
enforced suite, with the claim text hard-coded, while its own header said the
pins came from `restart_multinomial_max.py`. They were absent.

Populated from that oracle's own `--pins` output, 32 values, five seconds to
regenerate. **All 64 comparisons now happen and agree.** And an empty list now
refuses: emptied deliberately, it reports `HARNESS FAULT -- 0 pins, expected
32; nothing was compared` and the claim line reads `0 comparisons made` instead
of 64.

### What a wrong agreement would have looked like

| comparator | the wrong agreement |
|---|---|
| `compareresults.pl` + `selftest` | a mispaired reference, or one correct for a different fixture, reported as a clean self-test — **demonstrated above** |
| `regression-restart.sh` | "both cutoffs match the exact oracle" with the oracle never consulted — **demonstrated above** |
| `check-platform-deltas.py` | a platform exception honoured under a different Apple clang than the one that built the binary |
| `verify-fixture-inventory.sh` | a `.res` edited together with its manifest digest |
| `p_local_exact.py` | "the exact formula agrees with the tool" where the tool is an unidentified binary |
| `restart_decision_exact.py` | agreement with a build using the printed binomial, reported as agreement with the exact statistic |

The remaining eight are recorded here with their quoted exclusions rather than
repaired in this round, and `restart_decision_exact.py`'s dropped
`restartCutoffMethod` is the cheapest of them to close next.

---

## OC-75 — C23's verification is WITHDRAWN; and the fifth vacuous member of the enforced suite

### The withdrawal, recorded beside the claim it carried

`regression-restart.sh` printed:

```
C23 both cutoffs match the exact oracle:  32 H_I values x 2 columns (0.25 .. 8)
```

with the string hard-coded and `for triple in ; do` iterating **nothing**. Its
own header said the pins came from `oracles/restart_multinomial_max.py`. They
were absent. `cbad` was never touched, so the branch printing that sentence was
the only reachable one.

**So `C23`'s "verified against the exact oracle across the 1–8 bit range" was
not a weak verification or a narrow one. It was a string.** That is a
**withdrawn verification**, and it is recorded as withdrawn rather than quietly
replaced by the working version:

| | |
|---|---|
| **claimed** | 32 H_I values × 2 columns, 64 comparisons against the exact multinomial-maximum oracle |
| **actually performed, until 2026-10-21** | **zero comparisons** |
| **status of the claim in the interim** | **WITHDRAWN.** Not disproved — unevidenced. |
| **now** | the pins are the oracle's own `--pins` output, 32 values; **all 64 comparisons run and agree**; an emptied list reports `HARNESS FAULT -- 0 pins, expected 32` and the claim line reads `0 comparisons made` |

**The `C23` repair itself is probably sound and is now evidenced** — 64
comparisons agree, and `OC-62` reproduced the record's figures independently by
a separate route. But for the period between the repair and today, the stated
evidence for it did not exist. A reader of the record in that window would have
been told a verification had happened that had not.

### Five vacuous members of the enforced suite in two days

This is the count that matters, and it is why a scope statement for the suite
is now necessary rather than optional:

| # | member | how it passed while testing nothing | found by |
|---|---|---|---|
| 1 | `regression-input-identity.sh` | assertions in a heredoc in statement position, status discarded, unconditional `PASS`, no `set -e` | the fresh outside audit |
| 2 | `sanitizer-restart-c01.sh` | the same shape; a stand-in writing `errorLevel = 1` — the first thing it asserts against — produced `PASS`, exit 0 | the fresh outside audit |
| 3 | `regression-estimator-guards.sh` | `check_no_abort` asked only *"did it abort?"*, so a run that never happened answered *"no"*; **seven** checks reported non-failures with the inputs removed | the fresh outside audit |
| 4 | `compareresults.pl` / `selftest` | identity excluded from the comparison: a reference claiming a different file and 42 samples compared equal to a 1,000,000-sample run | the comparator sweep (`OC-74`) |
| 5 | `regression-restart.sh` | an empty pin list reporting 64 agreements, claim text hard-coded | the comparator sweep (`OC-74`) |

Plus one in the audit's own tooling, outside the enforced suite:
`build-differential.sh` returning a vacuous agreement because both arms'
fallbacks were the same literal (`OC-71`).

**Three of the five were found by an outside session reading the instruments in
a clone, and two by sweeping a shape this project had already written down.**
None was found by the suite itself, which is the definition of the problem:
**a suite cannot detect its own vacuous members, because a vacuous member
passes.** That is what `OC-76` is for.

---

## OC-76 — the remaining comparators, ranked by whether a wrong agreement can reach a published figure

`restartCutoffMethod` closed first, as the worst of the four shapes: the field
naming **which statistic the tool used** was read into the result and dropped,
so agreement with an `exact-multinomial-maximum` build and with a
`printed-binomial` build were reported **identically** — across exactly the
distinction `C23` exists to draw. It now refuses with exit 2 on any other
method, and notes an absent one as an unidentified cutoff. Verified both ways:
the genuine report decides and exits 0; a report relabelled `printed-binomial`
reports `INSTRUMENT MISMATCH` and refuses.

### The ranking, and its reason per item

Ranked by **reach to a published figure**, not by effort. Three tiers.

**TIER A — a wrong agreement CAN reach a published figure.**

| comparator | the path to a figure |
|---|---|
| **`check-platform-deltas.py`** | `b['cc'] in cc` is a substring of a compiler identity read from the host's **current** `$CXX`, not from the build under test. It gates whether a `selftest` failure is **excused**, so a wrongly-excused delta becomes "the suite is green", and the agreement claim in `BUILDING.md`'s precision-audit table rests on exactly that. **Fix: compare the full identity string, and read it from the build, not the host.** |
| **`verify-fixture-inventory.sh`** | input↔reference bound by filename transform, and the manifest's own digest **printed, never verified**. A `.res` edited together with its manifest digest passes, and `refdata/` **is** the platform-independent source every figure comparison reads. A corrupted reference propagates to every delta in the table. **Fix: verify the manifest digest against a committed expectation, and bind each pair by the identity lines now that `compareresults.pl` has them.** |
| **`regression-outside-battery.sh`** | the tool is taken from `$OUTSIDE_BATTERY_TOOL` or **built in-line with unrecorded flags**, while pinning FFT magnitude and frequency to four significant figures (`8538.7`, `59.938`) which are cited in the record. A differently-built checker changing those figures would read as the corpus changing. **Fix: `bs_print` plus a digest of the checker, and record the build line it was compiled with.** |

**TIER B — a wrong agreement reaches a verdict, not a figure.**

| comparator | why it stops short of a figure |
|---|---|
| `p_local_exact.py` | `HARNESS = sys.argv[1]` is never identified, so "the exact formula agrees with the tool" is agreement with *some* binary. It feeds `C22a`'s constant — which **is** in the floor — but that constant's own supremacy is separately measured (`OC-63`), and the floor prints the canary instruction beside it. **Fix: digest the harness and print it with the result.** |
| `regression-output.sh`, `regression-restart.sh`, `regression-subset.sh`, `regression-iid-json.sh` | identity is **reported** by `bs_print` and not compared, because `bs_print` has no failure path. These decide pass/fail on behaviour, and none of their numbers is published. **Fix: `bs_require` where the check depends on a particular build; otherwise state that the print is a record, not a gate.** |

**TIER C — recorded, no reach.** `oracle-selftest.sh`'s two empty-fragment
cases compare exit status only, and `c16-c23-matrix.sh` matches expectations by
prefix so a cutoff value is excluded from every assertion. Both are
self-checking harnesses whose output is read by a person, not cited.

### The standard each fix must meet

The one that corrected `build-differential.sh`: **an exclusion is justified by
self-comparison showing the field actually differs — never by the field's name
sounding like metadata — and where self-comparison shows a field stable, it
comes back into the comparison.** Three of that script's five "obviously
metadata" fields were stable, and two of the three identified the input.

`bs_print`'s lack of a failure path is the single change that would move four
Tier B entries at once, and it is deliberately not made here: `bs_print` is
called by six instruments as a **record**, and turning it into a gate would
change what each of them asserts. The honest fix is per-caller — `bs_require`
where the check genuinely depends on a build — and that is six decisions, not
one edit.

## OC-77 — F03: the temporary was the second front door, and the guard's reassurance was false

**Second independent AI audit, 2026-10-21, fork pin 32920f49, finding F03.**
**Status: REPRODUCED end to end against a real binary, REPAIRED, and the
repair's test shown failing against the pre-repair build. REPAIRED IS NOT
REVIEWED.**

### What the audit said, and what was actually worse

F03 said the temporary output path still destroys the input. It does. What the
reproduction added is the shape of the failure, which is worse than the finding
states in three ways.

The pre-repair writer (`HEAD:cpp/shared/TestRunUtils.h:273`) named its
temporary `path + ".tmp." + std::to_string((long)getpid())` and opened it with
`std::ios::out | std::ios::trunc | std::ios::binary`. `trunc` **follows a
symlink**. So:

1. **The capture is destroyed.** Measured on all three tools: a 1,000,000-byte
   capture came back **798–802 bytes** of report JSON, written through a symlink
   planted at the temporary's name.
2. **`rename()` renames the symlink, not its target.** After the run, the `-o`
   path was itself a symlink to the capture:
   `lrwxr-xr-x report.json -> .../capture.bin`. The attack therefore **persists
   without the attacker**: every later run with the same `-o` path destroys the
   capture again, with nothing left in the directory to notice.
3. **The A05 guard fired, and lied.** `writeJsonReport` is called **twice** in a
   normal run — the C14 early claim and the final report; this was observed, not
   inferred, by polling the directory and catching both temporary names
   (`rep1.json.tmp.7795446bd40f4c55`, `rep1.json.tmp.7795446b1db21902`: same
   `r1`, different `r2`). The first write destroyed the capture through the
   planted link. The second write found the `-o` path now aliased to the input,
   refused, and printed:

   > `Nothing has been written; the input is untouched.`

   Both halves of that sentence were false when it was printed. Exit 255. **A
   guard that reports the state of the world must check the world, not its own
   entry conditions.**

This is the constraint stated as a rule and then violated inside my own repair:
**a guard checks every write path, not the entry point.** `writeJsonReport` has
**54 call sites** across the three mains, which is exactly why the A05 guard was
correctly placed inside it — and the temporary was a 55th write that the guard
inside it did not cover.

### The repair, and what each part closes

`cpp/shared/TestRunUtils.h`. Four changes, none of them sufficient alone:

| change | what it closes |
|---|---|
| `O_CREAT\|O_EXCL` instead of `ofstream(trunc)` | `O_EXCL` **fails** if anything exists at the path, a symlink included. This alone defeats the planted link. |
| `O_NOFOLLOW` where defined | makes the refusal explicit rather than incidental to `O_EXCL`. |
| a random suffix from `/dev/urandom`, not the pid | the path cannot be guessed and pre-created at all. Eight attempts, then refuse. |
| the temporary is identity-checked against the protected input, and `fstat`ed after opening for `S_ISREG`, `st_uid == getuid()`, `st_nlink == 1` | **an open that succeeded is not proof of what it opened.** |

**A divergence the repair introduced and then removed.** Creating the temporary
at `0600` delivered reports at mode **0600** where the pre-repair writer
delivered **0644** — measured, at umask 022. That is a silent behavioural change
this repair has no business making. The temporary is now created `0666` so the
**process umask decides**, exactly as the `ofstream` did: measured 644 at umask
022 and 600 at umask 077. The narrow mode bought nothing — another user who
could read the temporary can read the finished report a moment later at the same
mode, and at 0644 cannot write to it.

### The test, and why it is deterministic

`cpp/selftest/regression-output-aliasing.sh`, three new cases (one per tool).

The pid is **not guessed**. A planter is compiled, plants a symlink at
`<report>.tmp.<its own pid>`, and then `execv`s the tool, which **inherits that
pid** — so the planted name is exactly the name the pre-repair writer computes.

Two earlier attempts covered a pid **range** instead and both missed, for the
same reason: the 2500 `ln` processes doing the planting **consumed the very pid
range being planted into**. A range test that misses is indistinguishable from
the repair working, which is rule 7's failure shape exactly. The case also fails
if the planted link has **vanished** — because a test that cannot show its
mechanism fired supports no claim.

### Sensitivity, per rule 8

The identical script against a build of `HEAD` (`REGRESSION_OUTPUT_BINDIR`):

```
  ea_non_iid symlink planted at the temp path   FAIL  THE CAPTURE WAS DESTROYED THROUGH THE TEMPORARY
  ea_iid     symlink planted at the temp path   FAIL  THE CAPTURE WAS DESTROYED THROUGH THE TEMPORARY
  ea_restart symlink planted at the temp path   FAIL  THE CAPTURE WAS DESTROYED THROUGH THE TEMPORARY
  regression-output-aliasing: FAIL (3 case(s))
```

Three for three, and **only** those three: every A05 alias case still passed on
that build, which isolates F03 from the finding A05 already closed.

### Both cases the task required, with their arms

| case | pre-repair | repaired |
|---|---|---|
| **direct-alias control** `-o <input> <input>` | exit 255, capture intact | exit 255, capture intact |
| **temporary-symlink** planted at `<report>.tmp.<pid>` | exit 255, **capture 1,000,000 → 798 bytes**, `-o` path left a symlink to it | exit 0, capture intact, planted link untouched, a valid 2,372-byte report written |

The control passes on **both** arms, which is what makes it a control: A05 was
already closed, and it confirms this repair did not reopen it.

### What this does NOT establish

- **Executed on Darwin arm64 only.** `O_NOFOLLOW` is conditional on the macro
  and the `fstat` limbs are **source-confirmed, not executed** — a wrong `st_uid`
  or `st_nlink` cannot be arranged at a path whose name is unpredictable by
  design, and that is the repair working against its own test. Windows takes the
  `MoveFileExA` branch and has no `symlink()`; the case **SKIPs** there on the
  behaviour test the script already performs (`SYMLINK_IS_ALIAS`), not on a
  platform name. **Windows is NOT RUN for F03.**
- The random suffix's two draws are **not** a cryptographic claim. `r1` is
  `time ^ (pid << 16)` and collides across runs in the same second — observed.
  Unpredictability is a second line of defence here; `O_EXCL|O_NOFOLLOW` is the
  one that does the work, and it holds against an attacker who guesses the name.
- Nothing here was reported upstream.

### Suite

`run-all-checks.sh --allow-known-platform-deltas`: **23 passed, 0 failed**,
21 regression scripts, build-state declared by 4 of 23.

## OC-78 — F02: the floor was never certified, and the helper that said so was the wrong one

**Second independent AI audit, 2026-10-21, finding F02. REPRODUCED, and the
reproduction is worse than the finding. The term "certified floor" is
RETIRED.** The task text is paraphrased from my own notes; the original message
is not recoverable from this session's transcript, so this entry does not quote
it.

### The contradiction, in one sentence of my own file

`oracles/entropy_floor.py` printed `CERTIFIED FLOOR` — the phrase this entry
retires — on the strength of this:

> every term is now a bound at width 1: `C01`/`F10` excluded by proof, **`C22a`
> a measured supremum**, `C22b` zero, `C22c` a derived ceiling.

A measured supremum is not a proved bound. The list **named its own exception
and then called the aggregate certified anyway** — against the standing
constraint that *a certified claim resting on an uncertified input is not
certified*, which the same file quotes four lines further down.

### What the reproduction added

Reproduced with `oracles/p_local_exact.py` against a `c22_bound` built from
production headers, `sha256 9619117ec68ee3fe`.

**`8.08e-15` is a PRODUCT OF TWO GRID MAXIMA, and `OC-63` examined one of them.**

| factor | value | where its maximum sits | status |
|---|---|---|---|
| `c` | 0.4991 | `N` = 10⁴ (5th of 12), `r` = 3 (2nd of 7) — **interior**, and bit-identical when the refinement window is extended nine orders | as good as a measurement gets |
| `K` | 1.6189e-14 | **`N` = 5, `r` = 2** — and `r` = 2 is the **first value in the swept list** `[2, 3, 4, 5, 6, 8, …]` | **rule 9 never applied to it** |

`K = sup 2^-52/(|f'(p*)|·p*·ln 2)` is largest where `|f'(p*)|·p*` is smallest;
the script's own printed model puts that minimum at `r` = 2; and whether the
true infimum is at `r` = 2 or at `r` = 1 — which the standard admits when the
longest run of correct predictions is zero — **was never examined**. Declaring
the product a bound from an interiority argument for one factor is the gap.

**And the margin is thin.** The sweep's own worst realised inflation reaches
**92.8 %** of the ceiling it is supposed to bound (realised multiplier 0.463
against `c` = 0.499). A grid maximum that its own grid approaches to within
7.2 % is not a comfortable bound.

**`C22c` is split, not simply derived.** `dX' ≤ dz·σ_max/√v` **is** DERIVED:
Popoviciu bounds `σ_max`, and `v` is exact. The **ceiling** on top of it is a
maximum over an **801-point scan** of step `dX'/8` — MEASURED. Its argmax is at
`cap − 1.0 dX'`, where the upper evaluation point lands on `G(1/64)` exactly;
that is *structurally explained*, which is the best case for a scan maximum,
and is still not a proof.

### The helper that "independently reproduced" C22c was wrong

| | `v` | `num_blocks` |
|---|---|---|
| production, `cpp/non_iid/compression_test.h` | `num_blocks − d`, `d = 1000` | `len/b`, integer, `b` = 6 |
| `oracles/p_local_exact.py` — **the source of the tabulated values** | `nb_ − 1000` ✓ | `n // 6` ✓ |
| `oracles/zalpha_ceiling_by_n.py` — **the independent check** | `num_blocks` ✗ | `mpf(n)/6` ✗ |

**Production is right**, and so is the record: SP 800-90B 6.3.4 makes the first
`d` = 1000 blocks the dictionary and averages the statistic over the remaining
`v = num_blocks − d` test blocks. The only one of the three that was wrong was
**the helper whose entire job is to check the other two**.

The direction matters. Too large a `v` makes `dX'` too **small**, the
subtracted term too small, and the floor too **high** — the unsafe direction.

| n | `dX'` correct | `dX'` as the helper had it | error |
|---|---|---|---|
| 10⁶ | 2.1486e-06 | 2.1422e-06 | **0.300 % low** |
| 8×10⁶ | 8.8868e-07 | 8.8835e-07 | 0.038 % low |

**And its comparator agreed anyway, because the tolerance was wider than the
figure.** `ok = abs(rv - mv) <= 0.01 * rv` — a flat **1 %** against values the
record states to **three significant figures**. The helper's 2.1422e-06 rounds
to **2.14e-06** where the record says **2.15e-06**: wrong in exactly the digit
the record claims, and inside 1 %, so it printed *"THE RECORD'S C22c IS
REPRODUCED."*

This is the comparator lesson of `OC-74`/`OC-76` one step over: **a comparator
whose resolution is coarser than the precision it checks cannot establish
agreement — it can only fail to find disagreement.**

### The repairs

**1. The label is composite, and takes the weakest status of its terms.**
`CERTIFIED FLOOR` is retired and no longer printed anywhere. A three-word
vocabulary is defined once, beside the constants:

- **PROVED** — holds for every input in the supported domain by an argument.
- **DERIVED** — follows from a PROVED inequality evaluated at numerical inputs.
- **MEASURED** — a maximum over an author-chosen grid or scan; rule 9 governs.

At width 1: `C01`/`F10` PROVED EXCLUSION, `C22a` **MEASURED**, `C22b` PROVED,
`C22c` DERIVED + MEASURED. Weakest is MEASURED, so the oracle now prints

```
  MEASURED FLOOR (C22a), literal  0.84129042387787445   (h' - 0.00336001)
  MEASURED FLOOR (C22a), F07      0.84465042387787448   (h' - 8.08001e-09)
```

The label **names the term holding it there**, so a reader learns what would
have to change to strengthen it. Above width 1 the `EVALUATED MARGIN (not a
floor)` verdict is unchanged — verified on a real 8-bit report, not asserted.

**2. The helper is fixed and its tolerance is derived, not chosen.**
`v = nb − COMPRESSION_D`, `nb = n // 6`, and the tolerance is now **half a unit
in the last significant digit of the recorded value** — the width within which
two numbers round to the same recorded figure. Significant figures are counted
from `repr()`, the shortest round-tripping decimal, because `%.17e` of a
recorded `2.15e-06` prints `2.14999999999999996e-06` and counting *its* digits
gave 18 significant figures and a tolerance of zero. **A check that can never
pass is as useless as one that can never fail**, and that draft was in the file
for one run before this was caught.

Sensitivity, per rule 8 — the tightened tolerance against both defects and both
corrections:

| value compared with the recorded 2.15e-06 / 166666 | verdict |
|---|---|
| old `v = num_blocks` → 2.1422e-06 | **DISAGREES (caught)** |
| new `v = num_blocks − 1000` → 2.1486e-06 | agrees |
| old `mpf(n)/6` → 166666.667 | **DISAGREES (caught)** |
| new `n // 6` → 166666 | agrees |

Every row of the helper's record comparison still agrees at the tightened
tolerance (0.056 %–0.338 % per row, printed per row so the resolution is
visible beside the verdict).

**3. The phrase is retired, with a convention and a check.** `"certified
floor"` now behaves like `rule N (vacated)`: an occurrence must sit in a
paragraph that marks it retired, superseded or false, and `regression-docs.sh`
fails otherwise. `ORCHESTRATOR-CHECKS.md` carries a **file-level retirement
notice** at its head instead, because it is an append-only dated record and
entries `OC-1`–`OC-77` must not be edited to say something their authors did
not know.

### What this does NOT establish

- **No number changed.** The floor's arithmetic is identical; only its status
  label is. A measured floor remains the most defensible figure available and
  is still worth computing.
- **`C22a` is not shown wrong** — it is shown *unproved*. Settling it means
  either extending the `r` axis to `r` = 1 and below the `N` = 5 point, or
  replacing `K`'s grid maximum with an analytic infimum for `|f'(p*)|·p*`. The
  script already prints a model (`0.01005·(r − p/q)`) that is the natural
  starting point. **Not attempted here**, and it is the single change that
  would move the floor from MEASURED to DERIVED.
- The stored `C22c` values are **unchanged and confirmed** — the helper was the
  wrong one, not the record. No floor figure anywhere in this repository moves.
- Executed on Darwin arm64 only. Nothing reported upstream.

## OC-79 — five of nineteen checks in the enforced suite reported success without running

**Found by this repository's own dead-guard detector while `regression-docs.sh`
was being edited for `OC-78`. A LIVE FALSE PASS, measured, not a pattern
report.**

`regression-deadguard.sh` failed with a moved flag set. One flag had
disappeared and one was new, and reading both by hand — which is what the
baseline exists to force — turned up a defect that had nothing to do with F02.

### The mechanism

Every scan in `regression-docs.sh` has this shape:

```sh
floorbad=$(python3 - "${repo}" <<'PY' ... PY
)
if [ -z "${floorbad}" ]; then note "...:" "yes"; else bad "...:" "${floorbad}"; fi
```

**An empty accumulator is reported as success.** It is therefore
indistinguishable from a scanner that crashed, was killed, or never started —
a missing `python3`, a syntax error inside the heredoc, an unreadable
repository. The scan's exit status is the only thing that separates *found
nothing* from *did not look*, and it was never read. SHAPE-03, in the enforced
suite.

### Measured

`python3` replaced on `PATH` by `#!/bin/sh` / `exit 127`, against the committed
`regression-docs.sh` at `de61365`. Quoted verbatim, so the third line carries
the label this round retires -- read `OC-78` for why it is no longer printed:
```
  no previously-corrected claim has reappeared:        none
  no NIST attribution in cpp/ comments:                none
  every "certified floor" mention carries its qualifier: yes
  every cited rule number has a definition:            yes
  the suite's scope statement matches the tree:        yes
regression-docs: PASS
```

**Five scans, all green, none of them run.** The file invokes `python3` exactly
five times and all five are accumulator scans, so the count is exact rather
than estimated: the other fourteen check lines are shell-driven and were
genuinely unaffected.

Two of those five are checks written in the last two days *to stop a claim from
rotting* — the rule-citation check and the scope-statement check. Both would
have gone on printing "yes" indefinitely on a host without `python3`.

### The repair

A `scanned()` helper, and every one of the five scans now reads its status:

```sh
floorbad=$( ... )
floorrc=$?
if ! scanned "${floorrc}" "\"certified floor\" retirement scan"; then :
elif [ -z "${floorbad}" ]; then ...
```

Verified by the same mutation — the broken `python3` on `PATH`:

```
  stale-claim scan -- THE SCAN DID NOT RUN (exit 127), so its silence means nothing
  NIST-attribution scan -- THE SCAN DID NOT RUN (exit 127), so its silence means nothing
  "certified floor" retirement scan -- THE SCAN DID NOT RUN (exit 127), so its silence means nothing
  entropy_floor.py literal scan -- THE SCAN DID NOT RUN (exit 127), so its silence means nothing
  rule-citation scan -- THE SCAN DID NOT RUN (exit 127), so its silence means nothing
regression-docs: FAIL (5 checks)
```

### The baseline moved by exactly one line, and why

- **GONE:** `cpp/selftest/regression-docs.sh|B|no set -e, status never read` —
  at `de61365` this was line 340, the old "certified floor" qualifier scan. It
  is gone because the construct was **repaired**, not because a guard was
  deleted; the detector cannot tell those apart, which is the stated reason the
  baseline requires a human sentence.
- **NEW, and withdrawn rather than baselined:** a pattern-C flag on
  `grep -q ... || vocabbad=...`, whose status *is* read via `||`. That is a
  **false positive** of the detector's pattern. Rather than pin it, the code was
  rewritten as an explicit `if !`, which the detector does not flag. **A
  baseline carrying a false positive is worse than one carrying none**, because
  the next reader has to re-derive that it is harmless.

Baseline 42 → 41 flags, one deletion, no additions.

### What this does NOT establish

- The other **36 flags** in the baseline are still **unresolved patterns**, not
  cleared guards. This entry resolved one of them and withdrew one new one.
- The four `regression-docs.sh` scans that remain flagged (`B`/`D`) are flagged
  for the heredoc and pipe patterns, which are **not** repaired here; only the
  unread exit status is.
- Executed on Darwin arm64. The defect is platform-independent by construction —
  it needs only a `python3` that fails — but it was demonstrated on one host.

## OC-80 — F04: the `--version` prescan only ever covered the two-character spelling

**Second independent AI audit, 2026-10-21, finding F04. REPRODUCED on all three
tools, REPAIRED, and a third open spelling found by the repair's own controls.**

### The defect

`versionOptionRequested()` inspected `a[n - 1]` — the **last** character of the
cluster — and then required `n == 2`:

```c
const char last = a[n - 1];
const char *p = strchr(optstring, last);
if (p != NULL && p[1] == ':' && n == 2) i++;
```

The `n == 2` was there to stop the last-character test misfiring on `-oout`,
whose last character is `t`. It also meant the skip fired for `-o` **and for
nothing else**. `-vo --version` and `-qo --version` are the same request written
as a cluster, `n == 3`, so `--version` was read as an option rather than as
`-o`'s argument.

### Measured, all three tools

| spelling | exit | version banner | assessed | report at the `-o` path |
|---|---|---|---|---|
| `-o --version data.bin 1` | 0 | no | **yes** | written |
| `-vo --version data.bin 1` | **0** | **YES** | **no** | **absent** |
| `-qo --version data.bin 1` | **0** | **YES** | **no** | **absent** |

Exit status 0, nothing assessed, no report written — and any previous report at
that path left in place. **A04 verbatim, through a different spelling of the
same options.**

### The repair

Testing the last character was the wrong idea rather than an incomplete one, so
it is replaced by the cluster walk getopt actually performs: **left to right
from the first character, and the first letter that takes an argument ends the
cluster** — argument attached if characters follow it, in the next element if
none do. That is correct for every cluster length, which is why no length test
remains.

### A third spelling, found by the controls rather than by the audit

`-Z --version data.bin 1` printed the banner and **exited 0 on the pre-repair
build too**. The operator supplied operands, so they asked for an assessment and
got success with nothing done — the same class, through an invalid option.

`--version` is implemented **only** by this prescan: plain `getopt()` would read
`--version` as the cluster `-` + `-version` and reject it, so the prescan
defines the whole semantics. An unrecognised option therefore now makes the
prescan **return false**, handing the element to getopt, which reports it and
fails the run. A legitimate `--version` request contains no invalid options, so
this costs nothing: whichever comes first — a `--version` or an unrecognised
option — decides.

### Controls, and what they establish

Nine rows run on both arms. The six defective cases flip; **every control is
byte-identical on both builds**, which is what makes them controls — the cluster
walk narrowed nothing:

| control | both arms |
|---|---|
| `--version` alone | banner, exit 0 |
| `-i --version data 1` | banner, exit 0 (a real request with a flag before it) |
| `-o NAME` separate argument | assesses, `errorLevel 0` |
| `-oNAME` **attached** argument | assesses — the case `n == 2` existed to protect |
| `-vo NAME`, `-qo NAME` clusters | assess |
| `-l0,1000`, `-vl0,1000` attached comma arguments | identical non-zero exit on both |

Sensitivity, per rule 8: against a build of `de61365`,
`regression-output-aliasing.sh` fails exactly the nine new cases and no
controls.

### Two instrument faults in my own testing, both recorded because they mattered

1. **A `head -8` on the tool's output.** It closed the pipe, killed the tool with
   SIGPIPE, and made `$?` the status of `head`. Every number in that run was
   about the wrong process, and it briefly looked as though the defect did not
   reproduce.
2. **A zsh loop with an unquoted `$a`.** zsh does **not** word-split unquoted
   expansions, so `-i --version` arrived as a **single argv element**. Every row
   of that run was meaningless, and two of them read as *the defect is not
   present*. The probe was rewritten in bash with an argument **array**.

Both are the same shape as the faults this audit keeps finding in the tree: the
instrument answered a different question from the one asked, and the answer
looked plausible.

### What this does NOT establish

- Executed on Darwin arm64. The prescan is pure C with no platform branch, but
  **Windows is NOT RUN**.
- `getopt` **permutation** is untouched and unexamined: glibc permutes
  non-options by default, so on Linux a `--version` placed *after* the first
  operand may still reach getopt where this prescan stops. Not reproduced, not
  repaired, and recorded here as the next thing to measure.
- The `-l0,1000` rows exit non-zero on both arms **with an error report
  written** (`errorLevel -1`, "No assessment was performed"). That is the tool
  behaving correctly; an earlier draft of the probe scored it as *assessed*
  because it keyed on `assessedSampleCount`, a field an error report also
  carries. The regression now keys on `errorLevel 0`.

## OC-81 — F05: the platform-delta filter discarded every diagnostic it did not recognise

**Second independent AI audit, 2026-10-21, finding F05. REPRODUCED in the
source, REPAIRED, five refusals each shown firing on its own defect.**

### The defect

`check-platform-deltas.py` decides whether a failing `selftest` is the known
upstream #155 platform difference, and `--allow-known-platform-deltas` is the
**documented macOS invocation**, so it is the path normally run. Its parse loop
was:

```python
mt = DIFF.search(ln.strip())
if not mt:
    continue
```

Every line that was not a `Significant difference` in exactly that shape was
**silently discarded**. A difference reported in any other form — a new
diagnostic, a harness error, a comparison announcing it could not run — left no
trace; the recognised rows were all within tolerance; and the script printed
*"N expected platform delta(s), all within tolerance"* and exited 0, excusing
the run.

**A filter refuses what it does not recognise rather than discarding it.**

### The repair, built from measured output

`./selftest` on this host emits **33 lines in six shapes**, so the benign set is
enumerable rather than guessable. Every line is now classified, and anything
matching none of the six is reported as `UNRECOGNISED ... refusing to judge
this run`.

Two of the six shapes do double duty as **completeness** evidence, which closes
the second half of the finding:

- `fixture-inventory: PASS (11 inputs, 11 references; manifest SHA-256 …)`
  declares the reference count, and must say `PASS` — if the references
  themselves are in question, no difference can be excused.
- eleven `<file>.res: N value(s) compared; identity <file>.bin / N samples /
  N-bit matched` lines must number exactly that count.

The old check required every manifest **row** to have been observed. That caught
a delta that stopped being reported, but **not** a selftest that compared fewer
**files**, because a file with no listed delta row contributes no row to miss.
The count now comes from selftest's own output rather than from a number
written here a second time.

And the two readings cross-check each other: the file list in
`selftest: FAIL (k of n files): …` must equal the set of files for which a
difference was actually parsed, in both directions.

### Sensitivity — five mutations, five refusals

| mutation | refusal |
|---|---|
| an `ESTIMATOR ABSENT: … could not be compared` line appended | `UNRECOGNISED selftest output, refusing to judge this run` |
| one `value(s) compared` line removed | `INCOMPLETE comparison: 11 reference(s) declared, 10 file(s) actually compared` |
| the identity limb changed from `… matched` to `identity NOT ESTABLISHED` | `UNRECOGNISED` **and** `INCOMPLETE` — correct, it is both |
| `fixture-inventory: PASS` → `FAIL` | `fixture-inventory did not PASS (FAIL): the references themselves are in question` |
| the summary made to name a third file | `selftest names normal.bin as differing, but no difference for it was parsed` |

Unmodified output: **8 expected platform delta(s), all within tolerance**,
exit 0. The exception still applies exactly where it did.

### An instrument fault worth stating

The taxonomy pass that produced the benign list normalised every filename to a
single `FILE` token — and the `Maximum delta` lines carry the **`.bin`** name
while the comparison summaries carry the **`.res`** name. The first draft
accepted only `.res` and refused nine legitimate lines. **When measuring the
shapes a filter must accept, do not normalise away the part the filter keys
on.**

### What this does NOT establish

- The benign taxonomy is **measured on one host, one selftest build**. A
  selftest change that adds a legitimate line shape will make this refuse —
  which is the intended direction, and the refusal names the line.
- Nothing here validates the **tolerances** in the manifest; they remain
  measured magnitudes with headroom, not bounds (rule 6), and the script still
  says so in its own output.
- Executed on Darwin arm64. Nothing reported upstream.

## OC-82 — F07: "the tool said" was this oracle redoing the tool's comparison

**Second independent AI audit, 2026-10-21, finding F07. REPRODUCED, REPAIRED,
and the repair's key case shown failing against the pre-repair oracle.**

### The defect

`restart_decision_exact.py` decided whether the tool's restart verdict agreed
with the exact multinomial-maximum decision. It established "what the tool said"
like this:

```python
tool = 'ACCEPT' if X_max <= tool_cutoff else 'REJECT'
```

That is **this oracle re-doing the tool's comparison with the tool's numbers**,
not the tool's verdict. The tool's actual verdict —
`passedRestartSanityCheck` in the report, `Restart Sanity Check Passed/Failed`
in the log — *was* read, *was* passed in, and was printed as a **decorative
parenthetical that nothing compared against**. The exit status at the bottom of
the file performed the same recomputation a second time.

So a tool whose own comparison was wrong — an off-by-one, an inverted operator,
a NaN path, a verdict written from the wrong variable — produced AGREE.

### Measured, by flipping one field of a genuine report

`passedRestartSanityCheck: true → false`, nothing else touched:

```
  the tool said: ACCEPT  (its X_cutoff 605; printed "Restart Sanity Check Failed")
  => AGREE with the corrected decision                                   [exit 0]
```

**One line asserts that the tool said ACCEPT and that it printed Failed, and
agreement is declared anyway.** The contradiction is inside the oracle's own
output.

### The repair: three statements that answer three different questions

| | statement | source |
|---|---|---|
| **A** | **INDEPENDENT DECISION** | the exact multinomial maximum, from `H_I` and `X_max` alone — needs nothing from the tool but its inputs |
| **B** | **THE TOOL'S REPORTED VERDICT** | the field the tool wrote. The only thing that is "what the tool said" |
| **C** | **what the tool's OWN figures imply** | `X_max` against the tool's `X_cutoff` |

**Agreement is A against B, and never A against C** — A and C share `X_max` and
differ only in the cutoff, so they agree whenever the two cutoffs fall on the
same side of `X_max`, which is most of the time and says nothing about whether
the tool decided correctly.

C is still printed, because **if C disagrees with B the tool's verdict does not
follow from the figures it reported** — a finding about the tool, not a reason
to prefer C. That is now reported before any agreement claim:

```
  !! THE TOOL CONTRADICTS ITSELF: it reported REJECT, and its own X_max 17 against its
     own X_cutoff 605 implies ACCEPT. Its verdict does not follow from the figures it
     wrote. Nothing below is evidence about the statistic.
```

**Incomplete evidence is its own outcome.** A report with no verdict field now
gives `INCOMPLETE: the tool reported no verdict, so there is nothing to agree
with. The independent decision above stands on its own; it is NOT
corroboration.` — exit 2, this oracle's established "could not decide". It used
to exit **0**.

Two further refusals, both exit 2: a `passedRestartSanityCheck` that is present
but **not a boolean** (`'yes'` used to produce a confident AGREE), and a log
containing **both** verdict phrases or either of them more than once — not one
run's verdict, and this reader will not choose between them.

### The fixtures are one-change-each

The single old fixture changed the cutoff **and** the verdict flag together and
was labelled *"a wrong tool cutoff exits 1"*. Under the three-statement
structure it still exits 1 — but because the **flag** disagrees, not the cutoff,
so the label named the wrong cause. There are now two fixtures, one per cause,
which is the discipline `A08` produced after four fixtures once refused for one
shared accidental reason.

### Sensitivity

`oracle-selftest.sh` against `HEAD`'s oracles: **nine cases fail**, including
every F07 case. The flipped-verdict fixture exits **0** with `=> AGREE` there
and exits **1** with `=> DISAGREE` here.

### What this does NOT establish

- Nothing about any **real** disagreement. Every fixture here is an edited
  report; the genuine report still agrees, exit 0, and `C23`'s own verification
  remains withdrawn (`OC-75`).
- The `restartCutoffMethod` gate from `OC-76` is untouched and still refuses a
  report produced by a different statistic before any of this runs.
- Executed on Darwin arm64. Nothing reported upstream.

## OC-83 — F08: three ways the floor oracle emitted figures from evidence it had rejected

**Second independent AI audit, 2026-10-21, finding F08. All three REPRODUCED on
fixtures built from a genuine report, all three REPAIRED, each refusing for its
own stated reason.**

`A08`'s rule for this file is **validate the evidence before emitting
anything**. Three things got through.

### 1. A note that said "stop" above a floor that did not

The `C02` consistency check compares `hAssessed` against `word_size × h'` — two
readings of the same measurement. When they disagreed it did this:

```python
notes.append("hAssessed ... is NOT word_size * h' ... stop and resolve it before using either.")
```

and then printed the floor. On a genuine report edited to `hOriginal` 0.8 and
`hAssessed` 0.1:

```
  NOTE: hAssessed 0.1 is NOT word_size * h' (0.8). ... stop and resolve it before using either.
  MEASURED FLOOR (C22a), literal  0.79663999191999191
  MEASURED FLOOR (C22a), F07      0.79999999191999194                    [exit 0]
```

**The script told the reader to stop and did not stop itself.** If the two
readings disagree then at least one is wrong and the report does not say which,
so `h'` is unestablished and nothing may be derived from it. Now a refusal.

### 2. A width that cannot exist

```python
w = d.get('bitsPerSymbol')
if not w: raise SystemExit(...)
```

Only **truthiness** was tested. `bitsPerSymbol: 1.5` was accepted and used three
times — in `h_orig / w`, in `w × h'`, and in `n = samples × w`, which printed
`n (bitstring length) 1500000 bits` for a width no run can produce. The tool's
own usage text says *"Must be between 1-8, inclusive"*, so that is now the test:
an integer in that range, with `bool` rejected explicitly because `True == 1` in
Python and `bitsPerSymbol: true` must not read as a 1-bit symbol.

### 3. A bit count standing in for a sample count

Two different requirements were being satisfied by one check:

- **SP 800-90B 3.1.1 item 1** requires at least 1,000,000 **samples** — whether
  there is a compliant assessment at all;
- the **C22c/ZALPHA** term was measured at bitstring lengths from 1,000,000
  **bits** up — whether this script may avoid extrapolating.

Only the second was checked, as `n < 1_000_000` on the bit count. So **125,000
eight-bit samples** — one eighth of the standard's minimum — gave exactly
1,000,000 bits and passed. The refusal now names both facts in one breath:

```
REFUSED: 125000 samples is below the 1,000,000 SP 800-90B 3.1.1 item 1 requires, so
there is no compliant assessment to floor. Note that 125000 samples at 8 bits is
1000000 bits, which satisfies the separate ZALPHA length requirement -- a bit count
is not a sample count (F08).
```

The sample minimum is checked **first**, and **independently of
`nonCompliantShortDataset`**, which this oracle already refuses. The same fact
checked twice by different means is the point: a figure must not rest on one
field having been set correctly.

### Sensitivity, and the distinctness that makes it mean something

Three new `oracle-selftest.sh` cases, each with a **distinct** expected fragment
— `C02 relation does not hold`, `integer width of 1-8`, `is not a sample count`
— because four refusals for one shared accidental reason is exactly how the
first version of those fixtures looked while testing nothing (`A08`). All three
exit **0** against `HEAD`'s oracle and **1** here, and the genuine report still
produces a floor at exit 0.

### What this does NOT establish

- These are **validation** repairs. They change no figure: the genuine report's
  floor is byte-identical before and after.
- The width gate accepts 1–8 because that is what **this tool** accepts. It is
  not a statement about the standard, which admits wider symbols that this
  implementation does not.
- Executed on Darwin arm64. Nothing reported upstream.

## OC-84 — F11: a tally that disagreed with itself, and a syntax error that silenced five gates

**Second independent AI audit, 2026-10-21, finding F11. Both halves
REPRODUCED and REPAIRED. The finding named the wrong file for the second half
and is corrected here.**

### Part 1 — the tally omitted a category, and three numbers went wrong

`run-all-checks.sh` had `total=$((pass + fail))` while the build-state line
thirteen lines below counted `pass + fail + cannot`. **The same script
disagreed with itself about how many checks it had run.**

Measured, with one regression made to exit 2:

```
run-all-checks: executed 22 total checks; expected 23
build-state: 4 of 24 checks declared the artefact they measured
run-all-checks: 22 passed, 1 failed, 1 could not run (21 regression scripts discovered)
failed: total-check-count
```

Three wrong numbers from one missing term:

1. **The total is false.** 23 checks did execute; one of them could not run.
2. **The failure is manufactured.** `total-check-count` is not a defect in
   anything — the guard invented it by comparing a two-category total against a
   three-category expectation. The condition it claimed to detect was already
   reported on its own `could-not-run:` line.
3. **The build-state denominator became 24** — the correctly-counting line was
   corrupted by having the failure the broken guard had just invented added to
   it.

A check that could not run **was** executed and supports no claim; it belonged
in the total all along, and already counted against the exit status. The total
is now computed **once** and both sites read it, so they cannot drift again.

After: `22 passed, 0 failed, 1 could not run`, total 23, build-state
denominator 23, **suite exit 1** — measured, not assumed, and measured through a
file rather than a pipe after a `tail` once made `$?` the status of `tail`.

### Part 2 — an empty `if` aborted the gating step

The finding said the **Windows** workflow. It is
`.github/workflows/x86-64-platform-facts.yml`, in the step that gates the job:

```sh
gate "oracle self-test" logs/07-oracle-selftest.log "oracle-selftest: PASS"
if true; then
fi
gate "outside-battery regression" ...
```

An empty `if … then … fi` is a bash **syntax error**. Measured on a two-line
reproduction: bash executes the lines *before* it, then aborts at that point
with **exit 2**.

So in that step:

- the five gates **after** the empty block never ran — outside-battery,
  script-inventory mutations, corpus mutations, restart regression, estimator
  guards;
- `exit "${fail}"` never ran, so the step's status was **bash's 2** rather than
  the accumulated verdict.

The job therefore goes **red**, so this was not a silent false pass — but it
goes red for a reason that has nothing to do with what any gate found, and
"it failed, so a gate caught something" would be wrong twice over.

`git log -S` places it exactly: commit **`1502012`**, dated **2026-10-21** —
the commit that *wired the oracle self-test because nothing ran it*. Both lines
were added together: a leftover wrapper from that edit. **The commit that
fixed "a detector nothing runs" introduced a syntax error that stopped five
gates running.**

### The check: `cpp/selftest/regression-workflows.sh`

`bash -n` over every workflow shell block, plus every `.sh` under `.github/`.
Registered in the authoritative inventory; the suite's expected counts move
21 → 22 scripts and 23 → 24 checks, and it is also gated by the x86-64 workflow
itself, because that is the file it was written for.

**The shell is resolved, not assumed.** `windows-platform-facts.yml` declares
`defaults: run: shell: cmd` for its whole job, so all ten of its blocks are
`cmd` and `bash -n` on them would be checking the wrong language. Each block's
shell is resolved as GitHub resolves it — the step's own `shell:`, else the
job's `defaults.run.shell`, else the workflow's, else the runner default (pwsh
on a windows runner, bash elsewhere) — and **every block is printed with the
shell it resolved to**, so a block excluded from the bash check is excluded
*visibly*, and because of what the workflow declares rather than by a filename
or a guess. That is `F05`'s lesson applied one directory over.

Current reading: **10 blocks checked with `bash -n`, 10 not bash-checked by
declaration, 0 expressions substituted**, across 19 run-blocks in 2 workflow
files and 1 script.

Three ways it refuses rather than passing quietly:

- **PyYAML absent → exit 2**, not 0. A check that did not run supports no
  claim, and the suite now counts "could not run" as its own category — which
  is Part 1 of this same finding.
- **a workflow file with no `run:` blocks → FAIL.** A workflow this check
  cannot see is not a workflow it has checked.
- **zero blocks checked → exit 2.** SHAPE-03: an empty accumulator reads as
  success.

Sensitivity needed no mutation: run against the tree as it stood, it printed

```
  x86-64-platform-facts.yml   6. The full suite and the  bash  SYNTAX ERROR
        x86-64-platform-facts.yml / 6. The full suite ... line 65: syntax error near unexpected token `fi'
```

and passes now that the two lines are gone.

### What this does NOT establish

- It establishes only that **bash can parse** these blocks. It says nothing
  about whether the gates are correct, whether their log files exist, or
  whether the workflows do what they claim. A `gate` line pointed at a log that
  is never written parses perfectly.
- **The ten `cmd` blocks are unchecked by any syntax tool.** `cmd` has no
  `-n`-equivalent available here, and the Windows job is the one this project
  cannot run locally at all. Recorded as a gap, not closed.
- **The five gates that never ran have still never run.** Fixing the syntax
  error makes the next run of that workflow the first to reach them. Whether
  they pass is **NOT RUN**, and nothing in this entry should be read as
  evidence that they do.
- Executed on Darwin arm64. Nothing reported upstream.

## OC-85 — F12: the withdrawn interval claim survived in three places, and the check's scope was the hole

**Second independent AI audit, 2026-10-21, finding F12. REPRODUCED at the site
the audit named and at TWO MORE it did not. The enforcement was scoped to seven
hand-listed files.**

### The site the audit named

`CLOSING-INVENTORY.md:233` at the audit's pin `32920f49` — in the
**forward-looking planning table**, under *"Needs the physical device"*:

> **At the width-1 operating point the two cutoffs are identical below
> H_I ≈ 0.989, so for this device the `C23` repair changes no verdict** — the
> table to read a cutoff out of is `XR-13`

Every clause of that is a problem. The premise is the interval claim `OC-49`
withdrew — a sweep in steps of 0.02 read as a statement about every point, with
a counterexample inside the range at `H_I = 0.9661822653793894` (printed 581,
exact 582). The conclusion is drawn **from** that premise. And the pointer sends
a reader to `XR-13`'s table, whose interval claim the same entry supersedes.

Corrected in place, keeping the superseded wording beside its correction, and
the conclusion re-grounded on evidence that licenses it: at the operating point
`H_I = 0.696` both cutoffs are **684**, the lowest `H_I` with any disagreement
is **≈ 0.888**, and a cutoff is read from
`oracles/restart_cutoff_certified.py`.

### Two more sites, in a file the audit did not name

A repository-wide sweep for the withdrawn claim found four occurrences. One was
the site above; two were correct quotation-with-correction in `OC-49` itself and
in `BUG-REPAIR-GUIDE.md`'s lesson. The fourth was live, in
`CROSS-REPO-FINDINGS.md`, and it was two defects, not one.

**(a) An endorsement of the withdrawn claim.** The text read *"**That holds**,
and the convergence is faster than 'well above'. The two cutoffs are
**identical at every H_I from 0.50 to 0.989**."* — four lines below a blockquote
saying the claim was superseded. A reader meeting the note and then the
assertion gets a contradiction inside one screen.

**(b) A third false statement the superseding note did not list.** That note was
headed **"SUPERSEDED IN TWO PLACES"** and enumerated the interval claim and the
683. It missed a whole section:

> *[withdrawn text, quoted]* ### Where the gap first becomes non-zero
> **Between H_I = 0.989 and H_I = 0.990.** … So a future one-bit device is
> affected only if its assessed entropy exceeds about 0.989 bits per bit.

The lowest `H_I` with any disagreement is **≈ 0.888**. **No new computation is
needed to see it is false:** `OC-49`'s own counterexample sits at
`H_I = 0.9661822653793894`, which is **below 0.989** — the section was already
contradicted by the entry that superseded it, in the same file, a few hundred
lines apart.

And it was **forward-looking advice about which devices are affected**, wrong by
about **0.1 bit in the permissive direction**: it would have told the owner a
0.95-bit device was unaffected, when 0.95 sits above 0.888.

**A superseding note that enumerates its sites is itself a claim about how many
there are.** The note now says three, and the section is withdrawn in place with
the corrected boundary analysis beside it.

### The enforcement, and why it did not fire

`regression-docs.sh` has carried a stale-claim registry since the 2026-10-02
sweep: a list of withdrawn phrases, searched with `\s+` between words so a line
wrap cannot hide one, exempting paragraphs that frame the phrase as a
correction. It works. It ran over

```sh
DOCS="README.md NOTICE BUILDING.md audits/README.md audits/BUG-REPAIR-GUIDE.md
      audits/2026-09-30/README.md audits/2026-09-30/FINDINGS-TRACKER.md"
```

**seven files named by hand — and none of the three surviving sites was in
one of them.** The pattern list was not the defect; **the scope was.** A rule
that says *a withdrawn claim is withdrawn everywhere or nowhere* cannot be
enforced over a hand-picked subset of everywhere.

Scope is now **every tracked markdown file plus `NOTICE`**, from `git ls-files`
rather than a list — **45 files**, with **28 dated reports excluded**, both
counts printed beside the verdict so the scope is visible rather than implied.

**The exclusion is stated and is per file, not per directory.** Guide rule 2
forbids editing the dated audit reports, because they are evidence of what was
believed when they produced a figure. A repository-wide sweep finds exactly one
unexempted hit inside them — `audits/2026-10-01-re-audit/REPORT.md:16`, where
a figure that had been corrected elsewhere, *"0.94 ms per thousand bits"*, still
stands as that report wrote it — and correcting it there would destroy the
record of the error. But `audits/2026-09-30` is in the canonical frozen set
while its `README.md` and `FINDINGS-TRACKER.md` are living documents that happen
to sit in a dated directory, so they stay in scope; the tracker has been edited
this campaign.

Three further changes, each from something the sweep exposed:

- **Seven registry entries added** — the interval claim in three phrasings, the
  683 in three, and `gap first becomes non-zero`.
- **The marker list learned the framings honest quotations use.** Three of the
  four sites were correct quotation-with-correction and were reported as
  defects because `EXEMPT` did not know *"The claim was …"*, *"The project
  claimed …"*, *"It read: …"*. **A check that cannot tell a quotation from an
  assertion fails the honest writer and nobody else.** The window deliberately
  stays **one paragraph**: widening it to include the paragraph above was the
  other option and is a real loosening, since a superseding note two paragraphs
  up would then exempt everything below it.
- **A scope of zero finds nothing.** `git ls-files` failing — not a work tree,
  no index — would make the check examine no files and report "none". It now
  fails if the list comes back implausibly small.

### Sensitivity

The withdrawn claim replanted in `CLOSING-INVENTORY.md`, both checks run against
the identical tree. The quoted output names the withdrawn phrase, so this block
is itself a quotation and not an assertion:
```
widened:        stale claims present again: ...CLOSING-INVENTORY.md:402:"identical below H_I"
HEAD's version: no previously-corrected claim has reappeared: none
```

### The check caught its own author, three times, writing this entry

The widened check failed on `OC-85` itself, in three places: the blockquote
quoting the withdrawn section heading, the sentence justifying the frozen-report
exclusion (which wrote *"a corrected '0.94 ms per thousand bits'"*, and
`corrected` as an adjective is not one of the marker phrasings), and the
sensitivity output block quoting the phrase the check had just caught.

All three were quotations, all three needed the marker **in the same
paragraph**, and all three are now written that way. This is the third time a
check written this round has first fired on the text that introduced it — the
rule-citation check did it twice, and the certified-floor check did it on
`OC-79`'s quoted output. **A check whose first catch is its author is working;
the alternative is a check whose author exempted themselves.**

### What this does NOT establish

- The registry catches **the phrasings it lists**. A withdrawn claim restated in
  new words is not caught, and nothing here changes that — it is a registry, not
  a semantic check.
- **`XR-13`'s own table is untouched.** Its interval claim is superseded and the
  pointers to it are redirected, but the table still sits in the record with its
  sampled rows; each row is correct at the point computed, and what does not
  follow is the behaviour between them.
- **The ≈ 0.888 boundary is `OC-49`'s, not re-derived here.** This entry
  establishes only that the old 0.989 statement is false, which needs no new
  computation because the counterexample already on file is below it.
- Executed on Darwin arm64. Nothing reported upstream.

## OC-86 — C22c re-established: the value the floor subtracts had never been computed by anything but production

**Owner's item 1 of 2026-10-21. The vindication is RE-ESTABLISHED, on better
evidence than it previously rested on, and the gap found on the way was larger
than the one that prompted the re-check.**

### Why it needed redoing, and what the re-check found instead

`F02` showed that `zalpha_ceiling_by_n.py` — the independent check on `C22c` —
used `v = num_blocks` instead of `num_blocks − 1000`, was **0.300 % low in the
unsafe direction**, and that its comparator agreed anyway on a flat 1 %
tolerance. So `OC-62`'s conclusion rested on a comparator that could not detect
the error it needed to detect.

Redoing it exposed something the helper's arithmetic had nothing to do with.
The helper's own output, for the two cells that matter:

> `| compression ceiling | 1000000 | 3.360e-03 | (production solve, not reimplemented here) | n/a |`

**The compression ceiling is the value `entropy_floor.py` subtracts, and nothing
outside production had ever computed it.** What `OC-62` reproduced was `dX'` and
`num_blocks` — the *inputs* to the ceiling. `OC-62`'s sentence
("reproduced where it can be checked independently") was true; the conclusion
drawn from it was broader than the check.

### The independent computation

New: `oracles/compression_ceiling_exact.py`, which implements `G(z)` from
**SP 800-90B 6.3.4 step 7 as written**:

```
G(z) = (1/v) sum_{t=d+1}^{N} sum_{u=1}^{t} log2(u) F(z,t,u)
F(z,t,u) = z^2 (1-z)^(u-1)  if u < t ;   z (1-z)^(t-1)  if u = t
X' = G(p) + (2^b - 1) G(q),  q = (1-p)/(2^b - 1),  b = 6
```

and is **validated against the standard's own worked example**, which is the
point: `OC-41` is the record of a harness that re-implemented a production
function, disagreed with it, and had no third party to adjudicate. 6.3.4's
example *is* that third party.

| | NIST publishes | this file |
|---|---|---|
| `p` for `d=4, N=8, v=4, X'=1.4617` | **0.5715** | **0.57148426** |
| min-entropy | **0.1345** | **0.134536** |

The double sum is reordered once (swapping the order of summation gives a count
of `N−d` for `u ≤ d` and `N−u` above, so one pass with running sums); the
truncation is bounded rather than guessed, since `(1−z)^(u−1)` at `z ≈ 1/64` is
below `1e-45` by `u ≈ 7500`.

### The three things the owner asked for

**Agreement:** yes, and at four separate precisions.

| quantity | production | independent | residual | tolerance | used |
|---|---|---|---|---:|---:|
| cap `com_exp(2^-6)`, n=1e6 | 5.2177052498567909 | 5.2177052498567894 | 1.5e-15 | — | 16 figures agree |
| cap, n=8e6 | 5.2177052498607601 | 5.2177052498607593 | 8e-16 | — | 16 figures agree |
| ceiling vs **production's scan**, n=1e6 | 3.3599e-3 | 3.3599300e-3 | **3.0e-8** | 5.0e-8 | 60.1 % |
| ceiling vs **production's scan**, n=8e6 | 2.1644e-3 | 2.1644012e-3 | **1.25e-9** | 5.0e-8 | 2.5 % |
| ceiling vs the **tabulated** figure, n=1e6 | 3.36e-3 | 3.3599300e-3 | −7.0e-8 | 5.0e-6 | 1.4 % |
| ceiling vs the **tabulated** figure, n=8e6 | 2.16e-3 | 2.1644012e-3 | **4.4e-6** | 5.0e-6 | **88.0 %** |

**Tolerance:** half a unit in the last significant digit of the recorded value,
taken from the recorded value **as text** — 5.0e-8 against a 5-figure figure,
5.0e-6 against a 3-figure one. In relative terms **0.0015 %** and **0.231 %**,
both narrower than the **0.300 %** error that had been hidden, which is the
condition a tolerance has to meet.

*The first draft of that tolerance was wrong in the same way `F02` was.* It
counted significant figures by rendering `mpf("3.36e-3")` to twenty places, read
six figures out of the binary noise, derived a tolerance of `5e-9`, and declared
both rows DISAGREE. Keeping the recorded values as **strings** removes the
class of error entirely: a string cannot carry binary noise.

### And the ceiling is no longer a scan maximum

`OC-78` recorded `C22c` as `DERIVED + MEASURED`, the measured part being
production's 801-point scan — a grid maximum, which rule 9 says can only
under-estimate a continuous supremum, the unsafe direction. **The argmax is now
derived rather than searched for:**

- `com_exp` is **stationary** at `p = 2^-b` by exact cancellation:
  `d/dp com_exp = G'(p) − G'(q)` because `dq/dp = −1/(2^b − 1)`, and at
  `p = 2^-b` we have `q = 2^-b`, so the two terms are identical. Proof, not
  observation.
- therefore `|dH/dX'| = 1/(6 ln2 · p · |com_exp'(p)|)` diverges at the cap.
  `p·|com_exp'(p)|` was measured monotone increasing away from it
  (1.40e-6 → 8.95e-5 over `p − 2^-6` of 1e-6 → 6.4e-5), so `H` is convex in
  `X'` there and **the fixed-width interval with the largest rise is the one
  ending at the cap.**
- measured with this implementation, not production's: the cap-ending interval
  gives **0.00335993** and the next three give **41 %, 31 %, 26 %** of it.

So the value is **one exact solve**, not a maximum over a grid, and `C22c` is
**DERIVED** throughout. The floor's weakest term is now `C22a` alone — which the
label already said, so the printed label does not change.

### What changed in the numbers

`C22c`'s compression entries are now carried to **five** figures —
`3.3599e-3` and `2.1644e-3` — because the three-figure rounding discarded
**4.4e-6 bit at n = 8e6, 88 % of what three figures permits, in the direction of
subtracting too little.** The floor at width 1, n = 1e6, moves from
`0.84129042387787445` to `0.84129052387787451`: **up by 1.0e-7 bit**, because
the rounded `3.36e-3` was over-subtracting.

The oracle is wired into `oracle-selftest.sh` (~55 s, last, skippable by
`EA_SKIP_SLOW_ORACLES=1` — which reports **SKIP**, not pass).

### What this does NOT establish

- `C22c` is confirmed **at two bitstring lengths**, 1e6 and 8e6, which are the
  two the record tabulates. Its fall with `n` is still measured rather than
  proved, and the value used at an intermediate `n` is the one tabulated at the
  largest `n` not exceeding it.
- The `dX'` bound itself is unchanged and still rests on Popoviciu's inequality
  plus `v`; this entry re-derives what sits **on top** of it.
- Nothing here touches `C22a`, which remains **MEASURED** and remains the term
  holding the floor's label. Executed on Darwin arm64. Nothing reported upstream.

## OC-87 — the tolerance sweep: 12 comparators, 2 where the slack is not established to be narrower than the error

**Owner's item 1, second half. Third instance this round of slack defeating
detection — after a floor of 9 against a count of 10, and a flat 1 % against
three significant figures.**

A comparator is in scope if **a numeric slack decides its verdict**. Production
estimator code is excluded, and the exclusion is stated: it is the thing under
test, not a comparator, and this project never touches its numerics.

For each: the tolerance, the smallest difference it must distinguish, and
whether the first is below the second.

| comparator | tolerance | must pass (noise) | must catch | narrower? |
|---|---|---|---|---|
| `compareresults.pl` | **1e-10** (min of abs, rel) | largest benign delta **8.22e-12**, measured | smallest delta it does flag **1.25e-10**, measured | **yes** — it sits between them |
| `pin-check.sh` | **1e-9** rel | cross-platform spread **4.4e-14**, measured | **7e-5**, by its own `--prove-nonvacuous` perturbation | **yes**, by 5 orders — the gap between is unprobed |
| `regression-estimator-guards.sh` | **1e-9** rel | **7.8e-15** (Linux vs macOS), measured | **1.9e-2**, by an observed 1 % `G()` mutation | **yes** — the model entry: all three numbers established |
| `known-platform-deltas.txt` (8 rows) | **1e-9**, uniform | observed deltas **1.25e-10 – 3.66e-10** | **NOT ESTABLISHED** | **NO** |
| `entropy_floor.py` (C02) | **1e-12** rel | double rounding, ~1e-16 | 0.8 against 0.1 → **0.875** rel | **yes** |
| `restart_decision_exact.py` (alpha) | **1e-12** abs | — | spec 5e-6 vs Sidak 5.0251553e-6 → **2.5e-8** | **yes** |
| `restart_multinomial_max.py` | **1e-12** rel | Levin vs brute force, **5.3e-16 – 1.0e-14**, measured | a structurally wrong Levin term, **O(1)** rel | **yes** |
| `zalpha_ceiling_by_n.py` | **derived**, 0.056 – 0.338 % | — | the **0.300 %** `v` error; binding row's tolerance is 0.233 % | **yes** |
| `compression_ceiling_exact.py` | **derived**, 0.0015 – 0.231 % | — | the same 0.300 % | **yes** |
| `regression-outside-battery.sh` | **±0.05** on 8538.7 (5.9e-6 rel) | — | bit-reversal break → **0.2**; 1e-3 twiddle → **4.6** | **yes** |
| `p_local_exact.py` (ratio ≤ 1) | **1.0** | — | the grid's own worst realised ratio is **0.928** | **NO** — 7.2 % margin (`OC-78`) |
| `restart_cutoff_certified.py` | **none** — exact rational arithmetic | — | — | n/a, and the right answer |

**12 examined, 2 found.**

### The two, and what was done

**`known-platform-deltas.txt`.** A uniform `1e-9` across eight rows whose
observed magnitudes run 1.25e-10 to 3.66e-10 — so the headroom is **2.7× on one
row and 8.0× on another**, and the uniform figure concealed that. Worse, "the
excused differences are negligible" cannot be asserted: **1e-9 is the same order
as `C22a` (8.08e-9 bit at n = 1e6), the floor's own quantisation term.**

Each row now carries the **measured magnitude beside the allowed one** as a
fifth field, four fields is malformed, a row whose observed magnitude exceeds
its own tolerance is refused, and the checker **prints the headroom**:

```
8 expected platform delta(s), all within tolerance, on Darwin arm64 (... headroom
used: 2.7x-8.0x, widest at biased-random-bytes.bin | Bitstring MultiMCW
Prediction Estimate | P_local where 1.25e-10 is allowed 1e-09)
```

**The tolerance is deliberately NOT retuned.** The smallest real defect in those
cells has never been measured, and retuning without that number would swap one
unjustified figure for another. What changed is that the slack is now auditable;
the unestablished limb is recorded as unestablished.

**`p_local_exact.py`.** Already `OC-78`: the ceiling's own sweep reaches 92.8 %
of it. Not a tolerance to retune — the 7.2 % is the margin itself, and closing
it means replacing `K`'s grid maximum with an analytic infimum.

### One more thing the sweep turned up, in a file it was reading

`oracle-selftest.sh` built its mutated fixtures in three `python3` heredocs
**whose exit status was never read**. A builder that died would leave the
fixtures absent — and an oracle handed a path that does not exist **refuses and
exits 1**, which is the *expected* status for most of those cases. Measured
against `HEAD` with `python3` replaced by `exit 127`: **exit 1, "FAIL (19
case(s))"** — not a false pass, but 19 case failures reported where the actual
fault is a missing interpreter. The builders' status is now read and every
fixture asserted present, giving **exit 2, could not run**. `A08`'s own lesson,
in the file `A08` produced.

Dead-guard baseline **41 → 40**: the `B` flag on `oracle-selftest.sh` is gone
because that construct was **repaired**. A pattern-C false positive on the new
`chk` call was avoided rather than baselined, by writing the call on one line.

### What this does NOT establish

- "Must catch" is **established by measurement for 7 of 12** and by construction
  for 2 more (the derived tolerances, which equal the precision the record
  claims and so cannot reject a correctly-rounded value). For `pin-check.sh` the
  catch is demonstrated 5 orders above the tolerance and **nothing probes the
  gap between**.
- The sweep covers **numeric** slack. Non-numeric slack is out of scope here and
  already recorded: `check-platform-deltas.py`'s `b['cc'] in cc` substring match
  (`OC-76`, Tier A) and `c16-c23-matrix.sh`'s prefix matching (Tier C).
- Executed on Darwin arm64; every "noise" figure is this host's. Nothing
  reported upstream.

## OC-88 — F02's relabel had not reached the oracle's own comments, and a withdrawn verification had no register

**Owner's item 2 of 2026-10-21. Three parts: carry the label everywhere, invert
the guard, and record the withdrawal as a withdrawal.**

### Part 1 — the first place the relabel had not propagated was inside the oracle

373 mentions of "floor" live in non-frozen files. Of those, the ones that
**assert or imply certification** are all in two places, and the live one was
`oracles/entropy_floor.py` itself.

Its label block carried, in sequence, as **flat present-tense assertions** above
the new F02 reasoning:

1. *"A reading is a CERTIFIED FLOOR only when EVERY term it subtracts is a
   bound"* — the definition of a term `OC-78` retired;
2. *"C22c at ANY width — the tabulated 3.36e-3 / 2.16e-3 are NOT reproduced by
   an independent derivation, which gives 7.49e-4 / 4.46e-4"* — `OC-59`'s claim,
   corrected by `OC-62` and **settled by `OC-86`**;
3. *"at width 1 the F07 reading is a certified floor and the literal reading is
   not"*;
4. *"the literal reading is a certified floor again"*.

**So the file asserted four times that a reading is a certified floor while
printing `MEASURED FLOOR`** — and restated a "not reproduced" claim after
`OC-86` had computed the thing independently. That is exactly the shape `OC-73`
removed from this same file once before, **reintroduced by the edit that retired
the label.**

The block is now split in two: one **CURRENT** statement, which is the only
thing the file asserts, and a **SUPERSEDED** list of five dated entries with
what each said and what replaced it. A live instrument's comments must not
contradict its behaviour; a record of what they used to say is a different thing
and belongs where it cannot be read as the present tense. The flag
`certified = (w == 1)` is renamed `c01_excluded`, because it never meant
certification and now cannot be read as meaning it.

### Part 2 — the guard, inverted, and then made stricter than the inversion

The old guard permitted `"certified floor"` **if qualified by a width or
reading**. It now fails on the phrase unless the paragraph marks it retired —
the `rule N (vacated)` convention, chosen over an absolute ban because an
absolute ban makes the history unrecordable.

**And a second, tighter check answers "no reading is certified" properly.** The
paragraph rule governs the *phrase*; it does not stop a sentence that **asserts**
the retired claim while a marker sits elsewhere in the paragraph — which is
precisely how the oracle's comment block passed while asserting it four times.
So the **assertive forms** — `is a certified floor`, `are certified floors`,
`prints a certified floor` and their kin — must additionally be **inside
quotation marks at the site**: a quote, backtick or emphasis marker within 90
characters on *both* sides. **Reported speech is allowed; assertion is not.**

Measured: `At width 1 the F07 reading is a certified floor, retired or not.`
**FAILS** — the retirement word in the same sentence does not save it. `The
entry said "the F07 reading is a certified floor", which is retired.` **passes.**

*A bash fault worth recording:* the check's `QUOTE` literal mixed a single quote
and a backtick inside a `$( … )` heredoc. **`bash -n` passed and the script died
at run time** — bash defers parsing inside command substitution — with
`unexpected EOF while looking for matching` the quote character itself. Built
from code points instead. `bash -n` is not a complete syntax check for a script
containing `$( )`, which is worth knowing given that `regression-workflows.sh`
is built on `bash -n`.

### Part 3 — a withdrawn verification now has a register

The owner's point: this is the **second withdrawn verification this week**, and
a withdrawal recorded only in the chronological entry that performed it is a
withdrawal nobody finds.

New: **`audits/WITHDRAWN-VERIFICATIONS.md`**, with five required fields per
entry — **CLAIM**, **WITHDRAWN** (date and entry), **REASON**, **WHAT NOW
STANDS**, **WHAT LEANED ON IT**. The last is the one easy to omit and the only
reason the others matter, so `regression-docs.sh` fails on its absence like any
other.

| | claim | withdrawn | reason |
|---|---|---|---|
| **WV-1** | `C23`'s cutoffs checked against the exact oracle at 32 `H_I` values | 2026-10-21, `OC-75` | the claim line was printed from an **empty loop** |
| **WV-2** | `C22a`'s constant is a **supremum**, so the term is a bound and the floor's terms are all bounds at width 1 | 2026-10-21, `OC-78` | the constant is a **product of two grid maxima** and only `c` was examined; `K` is attained at `r = 2`, the **first value in its swept list**, and rule 9 was never applied to it. The sweep reaches **92.8 %** of its own ceiling |

Both are linked from where `C22a` is described — in the oracle beside the
constant, and in `CLOSING-INVENTORY.md` beside the correction — so the
withdrawal is found by someone reading about the term, not only by someone
reading the chronology.

The register states what it is **not** for: `OC-49`'s 683→684 and
`OC-59`→`OC-62` are corrections of **values**, not withdrawals of
**verifications**, and `OC-86` turned the second into a verification that now
holds. The distinction is whether the thing withdrawn was a claim to have
*checked*.

Sensitivity: dropping `WHAT LEANED ON IT` from `WV-2` gives
`WV-2:missing-WHAT-LEANED-ON-IT`; removing every entry gives
`the-register-has-no-entries`, because an empty register would pass a field
check trivially (SHAPE-03).

### What this does NOT establish

- The register has **two** entries because two withdrawals are known. It is not
  a claim that no verification before this week was withdrawn — earlier ones, if
  any, were not recorded as such and are not reconstructed here.
- The assertive-form check is **syntactic**. A sentence that conveys
  certification without the phrase — "all the subtracted terms are bounds" —
  passes it, and only the status vocabulary in the oracle stops that being
  written next to a `MEASURED FLOOR` label.
- `C22a` is still **MEASURED** and nothing here attempts to settle it. Suite:
  24 passed, 0 failed. Executed on Darwin arm64. Nothing reported upstream.

## OC-89 — the interpreter sweep: nothing else reports a false pass, and thirteen report the wrong kind of failure

**Owner's item 4 of 2026-10-21. `OC-79` found one script reporting PASS when
`python3` could not run; the question was whether the pattern was confined to
it.**

### The answer, measured rather than grepped

Two sweeps, because a grep for `command -v` is a proxy for the question and not
the question.

**Behaviour.** Every regression script, mutation harness and `pin-check.sh` run
with `python3` replaced on `PATH` by a stub that exits 127:

| outcome | count | scripts |
|---|---:|---|
| **COULD NOT RUN (exit 2)** — correct | 4 | `regression-271`, `-deadguard`, `-multimmc`, `-notrun`, `-restart`, `-workflows`, `outside-battery-mutation-test` |
| **FAIL (exit 1)** — never a false pass, but the wrong kind of answer | 13 | `-chisquare`, `-docs`, `-estimator-guards`, `-iid-failclosed`, `-iid-json`, `-input-identity`, `-minsize`, `-nonregular`, `-output`, `-outside-battery`, `-platform-deltas`, `-subset`, `-width` |
| **PASS, and correctly** — does not use `python3` at all | 4 | `-272` (perl), `-selftest-inventory`, `-output-aliasing`, `pin-check` |

**No script reports a false pass.** `OC-79`'s was the only one, and it is fixed.
`regression-output-aliasing.sh` is worth naming: it passes without `python3`
because it deliberately does not use it — its own comment says *"The first
version used python3, which is NOT on"* every supported platform. The `uses=yes`
flag beside it in the first run of the sweep was **my grep matching that
comment**, not a dependency.

**Static.** The `OC-79` shape specifically — an accumulator filled from a
command substitution whose **emptiness is read as success**: **21
interpreter-backed accumulators examined, 0 fail-open.** Seven are
`regression-docs.sh`'s, now reading their status; the rest test emptiness and
fail closed.

*The static detector was wrong twice before it was right,* and both are the same
class as the defects it hunts:

1. It scanned up to 120 lines past a substitution that **closed on its own
   line**, found an unrelated `python3` below, and reported two false positives
   in `regression-multimmc.sh`.
2. It then reported a third — the real multi-line one — without asking **which
   way the empty branch goes**. `regression-multimmc.sh` treats an empty value
   as `fails=$((fails + 1))`. A detector that cannot tell a fail-closed branch
   from a fail-open one is measuring the wrong thing.

### The repair: a third outcome, at the two levels where it belongs

**`regression-docs.sh`** now distinguishes them itself. An unrunnable scan
increments `cannot`, not `fails`, and the script exits **2**:

```
regression-docs: COULD NOT RUN (7 scan(s) did not execute; 0 of the rest failed)
```

reported **above** pass/fail, because an incomplete run's verdict on the checks
it did reach is not the verdict on the file.

**`run-all-checks.sh`** gains a **preflight**, which is where the thirteen are
answered without thirteen edits: a missing `python3` is a property of the host,
not of any one member, and refusing the whole run once is more honest than
thirteen members each discovering it separately.

```
run-all-checks: COULD NOT RUN -- these tools are absent or do not work: python3
                No check below is reported, because a suite that cannot run its
                members has no verdict on them. Install them and re-run.
```

Exit **2**, which `F11`/`OC-84` made a counted category — so this repair had to
wait for that one.

**AND EACH TOOL IS RUN, NOT MERELY FOUND.** `command -v` answers a different
question, and the sweep's own stub proves it: a file on `PATH` with the execute
bit set, so `command -v python3` **succeeds** and `python3 -c pass` exits 127.
Demonstrated side by side. "Present" and "works" are different claims and only
the second one matters.

*And the preflight was broken in its first draft, in a way that would have
refused every run:* `req_run python3 python3 -c pass` did not shift the label
off, so it executed `python3 python3 -c pass` — python3 trying to run a **file**
named `python3`. Caught because the test printed `python3 perl` as missing on a
host where both plainly work. **A precondition that fails closed on a healthy
host is worse than no precondition**, because the first thing it teaches an
operator is to bypass it.

Verified both ways: healthy host → silent, `24 passed, 0 failed`; broken
`python3` → exit 2 and the message above.

### One more thing the sweep found, in a check written this round

`regression-docs.sh`'s document scope came from `git ls-files`, which lists
**tracked** files. So a new document was outside every check in that file **until
the commit that added it** — which is exactly the window in which it is being
drafted. Observed: `audits/WITHDRAWN-VERIFICATIONS.md` passed this script while
untracked and failed the assertive-form check the moment it was committed.

Scope is now `git ls-files --cached --others --exclude-standard`: tracked **and**
untracked-but-not-ignored, 45 → **46** files. `--exclude-standard` keeps
`.gitignore` honoured so build output does not enter scope.

And the thing it caught was the register's own wording — the retired phrase
*"both readings were certified floors at width 1"* in `WV-2`'s
WHAT-LEANED-ON-IT field, written as an assertive form rather than inside
quotation marks. Now quoted. **That is the fourth check this round whose first
catch was its author.**

### What this does NOT establish

- The sweep broke **`python3`**. A missing **compiler** was not swept, and
  `regression-output-aliasing.sh` and `regression-estimator-guards.sh` compile;
  the preflight runs `cc --version`, which covers the suite path but the
  per-script behaviour under a broken `cc` is **NOT MEASURED**.
- The preflight's required set — `python3`, `perl`, `shasum`-or-`sha256sum`,
  `cc` — is a **reviewed list**, derived from the sweep and then read by hand. A
  pattern-derived list was tried and was wrong: it missed three scripts that do
  use `python3` and demanded both `shasum` **and** `sha256sum` where either will
  do.
- The thirteen scripts still exit 1 when run **standalone** without `python3`.
  The suite path is fixed; the standalone path is recorded, not repaired.
- Executed on Darwin arm64. Nothing reported upstream.

## OC-90 — the instrument count had drifted, and a Linux-only failure was illegible

Two small things found while gathering figures for the fork-divergence rewrite,
both instances of the same discipline the owner asked that document to follow:
**every count names the commit and date it was measured at.**

### The instrument inventory stated a count the enumerator contradicted

`audits/INSTRUMENT-INVENTORY.md` stated **70 live** in six places. The
enumerator printed **73**. None of the six named when it had been measured, so
nothing in the tree could tell which was current.

The count is now stated **once**, with its commit and date, and the enumerator
is made the authority rather than described as one — `regression-docs.sh` fails
if the stated figure and the enumerator's disagree:

```
  the instrument inventory's live count matches the enumerator: 73
```

Measured **`live: 73` (63 mechanical + 10 reviewed) at `ae023b0`, 2026-10-22**,
against `live: 70` (60 + 10) at `32920f49`, 2026-10-21. The frozen figure keeps
no date because it cannot change: dated evidence does not grow.

**The three added instruments were listed by diffing the enumerator's own
`--list` output across the two commits, in a throwaway worktree.** The first
draft of that sentence named them from recollection and got one wrong — it
credited a sibling of `zalpha_ceiling_by_n.py` that does not exist. The real
three are `cpp/selftest/regression-deadguard.sh`,
`cpp/selftest/regression-workflows.sh` and
`oracles/compression_ceiling_exact.py`. **A list of what changed is a
measurement, not a memory.**

The historical section that reconciles 53 against 70 is now explicitly dated to
`32920f49`, 2026-10-21, and reads in the past tense, so its figures cannot be
mistaken for current ones. That is the same separation `OC-88` made inside
`entropy_floor.py`.

Sensitivity: changing the stated **73** back to **70** gives
`the inventory's stated live count disagrees with the enumerator: enumerator
says 73; no '**73** at <commit>' in the inventory`.

*And the check itself was wrong once:* its `sed` used `\+`, a GNU extension
that BSD `sed` treats as a literal plus, so on macOS it matched nothing and
reported `the enumerator printed no live count: cannot compare`. That failed
closed, correctly, and was still the wrong answer. `[0-9][0-9]*` and
`[[:space:]]` instead — the enumerator pads its label with several spaces.

### A failure that reproduced only on Linux was illegible

`regression-docs.sh` **passed** on Linux at `32920f49` and **failed** at
`1fa9c82`, and the artifact could not say which of its twenty-odd checks had
failed, because `run-all-checks.sh` prints a failing member's **last four
lines** — which showed the last check, and that one had passed.

Two changes, both so the next one is legible rather than guessed at:

- `run-all-checks.sh` prints **20** lines of a FAILing member, not 4. A member
  that fails is the one place where more output is worth the noise. The COULD
  NOT RUN branch keeps its short tail: its reason is in its last line by
  construction.
- the x86-64 workflow runs `regression-docs.sh` **separately, logged in full,
  and gates it**. The suite still runs it too, and the two must agree.

**This is item 3's own lesson one level down.** Five gates that had never run
were worse than five failing ones; a failure whose reason is not recorded is
worse than one that is. Four hypotheses were tried analytically — the
pinned-figure check against a different platform's build figure, `otool` versus
`ldd`, the `make -Bn` plan, a `lr_one` refusal — and **none of them was
confirmed**, which is exactly why the instrument was changed instead of the
guess being committed.

### What this does NOT establish

- **The Linux `regression-docs` failure is NOT diagnosed.** This entry makes it
  legible on the next run; it does not say what it is. Nothing here should be
  read as having identified it.
- The instrument count is enforced to **match the enumerator**, which is not the
  same as enforced to be **right**: if the enumerator's rule is wrong, both
  agree and both are wrong. The rule's own justification is
  `INSTRUMENT-INVENTORY.md`'s subject and is unchanged.
- Executed on Darwin arm64. Nothing reported upstream.

## OC-91 — the fork-divergence document, rewritten against its own figures

**Owner's item 5 of 2026-10-21, deferred until items 1–4 were done because
`F02`'s relabel and `OC-86`'s re-establishment both change what it must say.**

`FORK-DIVERGENCE-AND-TRUST.md` is replaced. The previous version was dated
2026-10-09 with a 2026-10-15 note bolted into the middle, and **seven of its
statements were false** — not stale. They are listed and corrected **as false**
in its §0, because "superseded" does not tell a reader they would have been
wrong.

### The seven

| | the claim | why false |
|---|---|---|
| 1 | `R-1` "remains unverified and unfixed" | `FORK-FIXED`, repaired 2026-10-19, **executed** on Linux x86-64 and Windows MinGW — and it is a `long double` **format** defect, not a platform one |
| 2 | `N-08` "remains in direct CLI paths" | `SUPPORTED-SCOPE-FIXED` |
| 3 | `N-10` "ambiguous report semantics remain" | `SUPPORTED-SCOPE-FIXED` |
| 4 | `NOVEL-03` "retain ambiguous labels" | `FORK-FIXED`; what remains is independent verification, a different statement |
| 5 | the whole quantified-divergence block | described a branch merged and deleted on 2026-10-15; said 66 commits ahead where it is **179**, 62,252 insertions where it is **108,859** |
| 6 | "Validate Linux and Windows before claiming support" | both measured, by CI; what remains is **independent** validation |
| 7 | "Submit generally applicable repairs upstream" | **contradicts the owner's standing decision** of 2026-10-15 that nothing is reported upstream |

Item 7 mattered most: a reader would have read the absence of upstream reports
as neglect rather than as policy.

### Three sections that cannot share an entry

**A — code defects**, **B — standard defects**, **C — what none of this
establishes**. A and B are separated by a single mechanical test, stated in the
document: *would conforming exactly to the standard's text fix it?* Yes → code.
If conforming faithfully is what produces the wrong behaviour → standard.

`C18` and `C23` are the worked pair. `C18` is code: the standard says nothing
about `long` width and 64-bit arithmetic fixes it. `C23` is standard: §3.1.4.3
step 5's printed formula tests the wrong statistic, and implementing it
faithfully is what rejects 83.2 % of correctly-operating sources. **Their
remedies are opposite** — a code defect is fixed by changing the fork, a
standard defect can only be diverged from, documented and bounded — which is
why an entry must not drift between them.

Section C carries prose. There is nothing in it to repair.

### Five fields per entry, each answering a standing constraint

**DEFECT** (behaviour, not a code location) · **ORIGIN** (INHERITED, or
INTRODUCED BY THIS FORK and by which repair) · **EVIDENCE** (EXECUTED naming
platforms / DERIVED / SOURCE-CONFIRMED — three strengths, never collapsed) ·
**STATUS** (NOT REPAIRED / REPAIRED / REPAIRED AND INDEPENDENTLY REVIEWED —
**and nothing is in the third state**) · **DOES NOT ESTABLISH**.

**Section A.2 exists because of the ORIGIN field.** Four defects this fork
**introduced**: `A05` and `F03` (the report writer destroying the assessment
input, by `C14`'s and `C08`'s repairs respectively), `C24` (no report writable
on Windows at all, by those same two interacting), and `F04` (`A04`'s own
prescan repair covering one spelling). Three of the four came from **one repair
interacting with another**. A fork that listed only inherited defects would be
claiming it never broke anything.

### The staleness mechanism is a mechanism

New: `tools/measure-divergence.sh`, which prints §1's figures from `git` at
`HEAD`; and a `regression-docs.sh` check that **re-runs it and fails if the
document disagrees**. Sensitivity — three separate drifts, each caught and
named:

```
  **179 commits ahead → **66 commits ahead   figures have drifted: ahead(179)
  | 2,188 | → | 1,063 |                      figures have drifted: production(2,188)
  `11207ca` → `9556649`                      figures have drifted: commit(11207ca)
```

Every count in the document names the commit and date it was taken at **at the
point of use**, not once at the top — a single date on a document mixing
vintages is the mechanism by which items 1–5 survived.

### And a property of the enumerator worth writing down

Adding `tools/measure-divergence.sh` moved the live instrument count 73 → 74,
which the `OC-90` check caught. `git ls-files` lists tracked **and staged**
paths, so **a new instrument begins to count the moment it is staged** — not
when it is written, not after the commit. That is what lets the stated count and
the tree be consistent *at commit time*: stage everything, re-run the
enumerator, write the number it prints. Recorded in
`INSTRUMENT-INVENTORY.md`, because the rule that an untracked file is not part
of the record is deliberate and this is its useful consequence.

### What this does NOT establish

- **The document is not a review**, and says so: it is written by the author of
  the repairs it describes, and every entry carries its own
  DOES-NOT-ESTABLISH for that reason.
- **Only §1's figures are enforced.** The prose will go stale in the ordinary
  way; where it makes a claim about the tree it cites the record entry that can
  be checked instead of asserting it.
- **It is not the defect record and not the instrument record.** Instrument
  defects are a third category and a large one, but they are not divergence
  from upstream, so they are deliberately not filed there — §5 item 6 and
  section C exist so a reader cannot miss that they exist.
- Nothing reported upstream. No change made to the consuming project.

## OC-92 — the five gates ran: all five pass, and the tally defect was what had been failing CI

**Owner's item 3 of 2026-10-21: "five unknown gates is a worse state than five
failing ones". They are no longer unknown.**

Triggered by pushing to the fork — `origin`, `systemslibrarian`, never
`upstream`. **A near-miss worth recording first:** `gh` resolved the repository
to **`usnistgov`** by default, because both remotes are configured and it
picked upstream. The first `gh run list` returned
`HTTP 404: … not found on the default branch` for *NIST's* repository. Every
call is now explicit with `-R`, and the default is pinned. **Nothing was sent
upstream, and the default would have aimed every query there.**

### What the five did

| gate | before | now |
|---|---|---|
| outside-battery regression | **never ran** | **PASS** |
| script-inventory mutations | **never ran** | **PASS** |
| corpus mutations | **never ran** | **PASS** |
| restart regression | **never ran** | **PASS** |
| estimator guards | **never ran** | **PASS** |

Plus the two added since: **workflow shell syntax** PASS (`OC-84`) and **docs
checks, logged in full** PASS (`OC-90`).

**Run `40228895652`, conclusion `success` — green for the first time in this
campaign, after seven consecutive failures.**

### And the tally defect was not hypothetical: it was what had been failing CI

`OC-84` reproduced `F11`'s tally locally by making one regression exit 2. The
artifacts show it was doing that on **every push**, and that it was the reason
the job was red. At `39690146243`:

```
run-all-checks: 22 passed, 1 failed, 1 could not run (21 regression scripts discovered)
could-not-run: regression-platform-deltas
failed: total-check-count
```

`failed: total-check-count` is the **manufactured** failure — the guard
comparing a two-category total against a three-category expectation — and it
also inflated the build-state denominator to 24. The gate wanted
`22 passed, 0 failed, 1 could not run` and got `1 failed`, so it failed.

At `40228895652`, with the fix:

```
run-all-checks: 23 passed, 0 failed, 1 could not run (22 regression scripts discovered)
could-not-run: regression-platform-deltas
```

**Linux is where a check legitimately abstains** — `regression-platform-deltas`
has no manifest block for that platform and exits 2 — so the defect fired there
and never on macOS, where nothing abstains. That is exactly the class this
workflow exists to detect: **a claim that is true only on the development host
is invisible from that host by construction.** It was detected, and then it sat
in a red job for five pushes while the redness was attributed elsewhere.

### The Linux-only `regression-docs` failure: GONE, and NOT DIAGNOSED

`regression-docs.sh` failed on Linux at `1fa9c82` and **passes at
`11207ca`**. **I did not identify the cause and this entry does not claim to.**

The two candidate changes between those commits are the stale-claim scan's
scope (`git ls-files` → `--cached --others --exclude-standard`) and the
`scanned` outcome (`bad` → `cannot`, exit 1 → exit 2). **Neither is confirmed,
and the second is argued against by the evidence:** at `11207ca` the Linux run
reports **PASS**, not COULD NOT RUN, so no scan failed there — which is what the
`scanned` change would have produced if a failing scan had been the cause.

Four hypotheses were tried analytically before the instrument was changed
instead — the pinned-figure check against another platform's build figure,
`otool` versus `ldd`, the `make -Bn` plan, an `lr_one` refusal — and none
survived. **A defect that stops reproducing without being understood is not a
defect that was fixed**, and if it returns the workflow now logs that script in
full and gates it, so it will name itself.

### What this does NOT establish

- **That the five gates passing means what they check is sound.** They assert
  that the mutation harnesses land their mutations, that the corpus matches its
  manifest, that the restart regressions hold and that the estimator guards
  reject their mutants — on x86-64 Linux, at one commit. Each one's own scope
  is in `WHAT-A-GREEN-SUITE-ESTABLISHES.md`.
- **That the workflow being green means the fork is correct.** Six of the seven
  earlier failures were a tally bug and a syntax error in the gating step
  itself — the job was red for reasons that had nothing to do with the
  estimators, and it is now green for reasons that say nothing about them
  either.
- The Windows job is unchanged by any of this, and its ten `cmd` blocks are
  still checked by no syntax tool.
- Nothing reported upstream.

## OC-93 — the gh default: one call did answer about NIST's repository, and one was a request sent there

**Owner's item 1 of 2026-10-25: "a gh call without an explicit repository does
not fail loudly when the wrong repository happens to answer." It did not fail
loudly. It answered.**

### The sweep

| | count |
|---|---:|
| `gh` subcommand invocations matched across every session transcript | **336** |
| of those, real invocations of a **default-resolving** subcommand with no `-R` | **6** |
| recorded `gh` commands in tracked documentation with no repository named | **4** |
| CI run identities cited on the record | **2** |
| of those, read with an explicit `-R` naming the fork | **2** |
| figures on the record whose provenance cannot now be established | **0** |

`gh api` with an explicit path, `gh auth`, and `gh repo set-default` (which takes
the repository positionally — that one is the fix, not the hazard) do not
resolve a default and are excluded by name, with the reason.

### The one that answered

An unqualified
`gh repo view --json name,visibility,defaultBranchRef,hasIssuesEnabled`
returned:

```
{"defaultBranchRef":{"name":"master"},"hasIssuesEnabled":true,
 "name":"SP800-90B_EntropyAssessment","visibility":"PUBLIC"}
```

**That is upstream's answer, not the fork's**, and it is provable from one
field. Queried explicitly, just now:

| | `hasIssuesEnabled` | `isFork` | name | visibility | default branch |
|---|---|---|---|---|---|
| `systemslibrarian/…` | **false** | true | SP800-90B_EntropyAssessment | PUBLIC | master |
| `usnistgov/…` | **true** | false | SP800-90B_EntropyAssessment | PUBLIC | master |

**Every field anyone looked at was identical between the two.** The only
discriminator was `hasIssuesEnabled`, which was not the field being read — the
call was establishing whether Actions could run. The accompanying
Actions/billing answer, `{"enabled":true,"allowed_actions":"all",…}`, was
upstream's too.

**Nothing was recorded from it.** A sweep for claims about Actions being
enabled, allowed actions, billing or runner availability finds **none** in any
tracked document. The answer was used transiently to decide whether to continue
building the workflow, and the decision happened to be the same either way. So
**no published figure rests on it** — and that is luck, not design: had upstream
differed from the fork on the field being read, the conclusion would have been
wrong, recorded, and unrecoverable.

### And one was a request sent to NIST's repository

```
gh workflow run x86-64-platform-facts.yml        # no -R
HTTP 404: workflow x86-64-platform-facts.yml not found on the default branch
          (https://api.github.com/repos/usnistgov/SP800-90B_EntropyAssessment/
           actions/workflows/x86-64-platform-facts.yml)
```

**That is an attempted workflow dispatch at `usnistgov`.** It was refused,
because the workflow does not exist there and the account has no write access.
**Nothing ran, nothing was created, nothing was posted** — but a request was
made at a third party's repository, unintentionally, and the owner should know
that rather than read "nothing reported upstream" as meaning no request ever
left this machine. The standing decision is intact; the near-miss is recorded.

Three further unqualified calls — `gh workflow list` twice and
`gh run list --limit 2/3` — produced output that is no longer visible: they sat
in compound commands whose `head` truncation was consumed by the 404 above.
**I cannot prove what they returned.** No document cites a workflow list or a
run list, so no figure depends on them; that is an absence of dependency, not a
recovered provenance, and it is stated as the weaker claim.

### The run identities, which were the real worry

Both run identities cited on the record — `39690146243` and `40228895652` in
`OC-92` — were read with `-R` naming the fork, on every one of the eleven calls
that touched them. The two apparent "without `-R`" hits in the transcript sweep
are **the heredoc that writes `OC-92` itself**, whose prose contains the run
numbers and the phrase `gh run list` — written unqualified there because the
entry is quoting the hazard, not issuing a command. **No run identity on the
record was read from upstream's repository.**

### The repairs

**Four recorded commands now name their target.** Named unqualified here only
to say which they were — `BUILDING.md`'s
`gh workflow run windows-platform-facts.yml`, and `CLOSING-INVENTORY.md`'s three
(`x86-64`, `windows`, `gh run download`) — each of which now carries `-R`.
A command recorded in documentation is a command someone will run.

**And `regression-docs.sh` enforces it.** A `gh` invocation of a
default-resolving subcommand must name a repository. The check distinguishes **a
command from a mention**: inside a fenced block `-R` is required with no
exemption, because a fence is an instruction; outside one, the surrounding
paragraph must mark the hazard. Both forms shown failing —
`BUILDING.md:853 (in a code fence)` and `BUILDING.md:852` in prose.

**And a third draft was wrong by being too absolute.** "Inside a fence, `-R` is
required with no exemption" flagged `OC-93`'s own verbatim quotation of the
unqualified call it was reporting — **a record must be able to quote a bad
command, in a fence, because that is what the evidence is.** The convention is
now a label **on the command**: a trailing `# no -R`, `# unqualified` or
`# NOT A COMMAND`. It cannot smuggle a runnable instruction through, because the
label is the statement that it is not one. Verified three ways: unlabelled in a
fence → flagged; labelled in a fence → exempt; unlabelled in prose → flagged.
**Fifth check this campaign whose first catch was its author.**

*Two earlier drafts were wrong by being too literal:* a single-line
marker window flagged two passages that exist to explain this very defect, one
of them because the word "bare" sat at the end of the previous line; and the
marker `resolves to` missed a paragraph saying `resolved the repository to`.
**That is the second stemming slip in this file** — the certified-floor check
made the same one with `retire`/`retires` — so stems are now the default there.

### What this does NOT establish

- **Only the transcripts of this project's sessions were swept.** A `gh` call
  made outside them, or in a session whose transcript is not on this machine, is
  not covered.
- The check governs **tracked documentation**. It cannot see a command someone
  types, and `gh repo set-default` having been pinned is a property of this
  machine's `gh` config, not of the repository.
- **`hasIssuesEnabled` being the discriminator is a happy accident.** If the two
  repositories had agreed on every field, the sweep could not have determined
  which answered, and the honest verdict would have been "provenance not
  establishable" rather than "answered about upstream".
- Nothing reported upstream.

## OC-94 — rule 12: the dominant mode of self-inflicted defect, measured and made declarable

**Owner's item 2 of 2026-10-25. "Three of four self-introduced defects came from
repair interaction" was an observation in a document section; it is now a rule
with a measurement behind it.**

### The measurement, and what it is not

File-level overlap was tried first and is not the measurement: **nineteen
commits touch `entropy_floor.py`**, which says nothing about interaction. **Line
provenance is the question** — for every line a commit deleted, blame the parent
for which commit introduced it.

Every commit since 2026-10-11:

| | count |
|---|---:|
| repairs that landed on an earlier repair's lines | **51** |
| (later, earlier) pairs | **102** |
| narrowed to pairs where the later repair deleted a **non-comment** line | **94** |
| of those, **declared** by the later commit's own message | **29** |
| **NOT declared** | **65** |

The deleted-code subset is the dangerous shape: that is how a mechanism gets
silently narrowed. The 65 is a count of **undeclared interactions**, which is a
documentation defect — **it is not a claim that 65 behavioural defects exist**,
and most are comment rewrites and list extensions.

### Rule 12, in two halves

**Name the pair** — by identifier, in the commit message, not only as prose
about the interaction. `F11` described its interaction with the build-state line
and named neither `OC-66` nor its commit, so no tool can check it and no reader
can find it.

**Test the pair, not the case** — exercise the case the *earlier* mechanism was
built for. The suite exercises it incidentally and would pass a mechanism that
had been quietly narrowed, which is exactly what `F03` and `OC-88` were.

The acceptance condition in `BUG-REPAIR-GUIDE.md` step 8 now carries the
mechanical way to find the pairs, so they are found rather than remembered.

### The worked example, including what it cost

`F07` restructured `restart_decision_exact.py`, deleting code introduced by
`OC-26` and `fix(C23)`. Two mechanisms lived in that ground and **neither was
named in `F07`'s message**:

| mechanism | tested | result |
|---|---|---|
| `OC-76`'s `restartCutoffMethod` gate | a report relabelled `printed-binomial` | **intact** — exit 2, `INSTRUMENT MISMATCH` |
| `A07`'s six-decimal precision guard | a log whose printed `H_I` does not determine the cutoff | **intact** — exit 2, identical message before and after `F07` |

**And the second test took work, which is the finding.** The first attempt used
`H_I = 0.966182` — adjacent to `OC-49`'s counterexample and therefore plausible
— and the oracle **decided, exit 0**. That looks exactly like a broken guard and
was not: `0.966182` does not straddle a cutoff step, so the test established
nothing in either direction.

A straddling value had to be **constructed**: bisect for the step between
`H_I` 0.696 (cutoff **684**) and 0.700 (**683**), find it at
**0.698044238717**, and take `H_I = 0.698044`, whose half-ULP interval gives
684 at the bottom and 683 at the top. Only then does the guard have something to
refuse — and it refused, identically on both sides of `F07`.

**A plausible case that a guard correctly passes is indistinguishable from a
guard that has stopped working.** That is instrument rule 1 and rule 7 arriving
from a third direction, and it is the cost this rule imposes: testing a pair
means constructing the earlier mechanism's own case, which is harder than
running the suite.

### What this does NOT establish

- **Two of 65 undeclared pairs were tested.** Both intact. The other 63 are
  **not examined**, and this entry does not imply they are sound — only that the
  undeclared ones are now findable by the command in step 8.
- The rule governs repairs made **from here on**. The 65 are not retrofitted
  with declarations; doing so would be writing history rather than recording it.
- The five realised instances are the five known. A sixth is not excluded, and
  the search above was for *undeclared* pairs rather than for *broken* ones.
- Nothing reported upstream.

## OC-95 — the dead-guard backlog, triaged: and a correction to my own figure first

**Owner's item 3 of 2026-10-25: bound the backlog before working it.**

### The correction I owe

I reported *"a dead-guard baseline of 40 flags is pinned, of which 36 remain
unresolved patterns rather than cleared guards."* **That was wrong, and wrong in
the flattering direction.** A resolved flag **leaves** the baseline — the
baseline *is* the unresolved set. So all 40 pinned signatures were unresolved;
none of them was among the four I had counted as resolved. Two flags were
resolved during this campaign and left (42 → 41 → 40). The "36" described
nothing.

### The unit matters: 40 signatures, 68 flagged lines

The baseline deduplicates by `file|pattern|detail`, deliberately, so that a line
number moving does not move the baseline. One signature can therefore cover
several lines **in different groups** — `regression-docs.sh|D` covers three
lines, one a false positive and two benign. **So the triage is by flagged line,
68 of them, and the signature count is reported beside it rather than used as
the denominator.**

### The three groups

| group | lines | share |
|---|---:|---:|
| **1 — a wrong result could reach a figure or a claim** | **9** | 13 % |
| **2 — it could not: a silent failure produces a downstream failure** | **48** | 71 % |
| **3 — false positive of the detector** | **11** | **16 %** |

**Group 2's test**, applied uniformly: does a silent failure leave an absent
fixture, an empty digest, an unlanded mutation that a *separate* landing proof
catches, or a report line the job's expected-gates file requires? All four end
in a failure, not a pass. Item 4's sweep measured the first of those directly:
no script reports a false pass when `python3` cannot run.

### The detector's own false-positive rate: 16 %, and it has one blind spot

Eleven of 68, and **six of them are one blind spot**: a construct whose status
is read by a mechanism the pattern matcher cannot see.

| the construct | why the status is read |
|---|---|
| `python3 … <<'PY'` as the **last statement of a function** | its exit status **is** the function's return value — `build-provenance-canary.sh`'s `json_check()`, `build-differential.sh`'s `rule8_controls()` |
| `grep -q … \` continued onto `\|\| …` | the `\|\|` is on the next line, which the matcher reads as a separate statement — `regression-outside-battery.sh` ×2, `regression-docs.sh` ×1 |
| a multi-line `var=$( … python3 …` | the `python3` line is not itself an assignment, so `ASSIGN.match` misses it — `regression-docs.sh` ×2 |
| an `assert` **inside** an interpreter heredoc | matched as if it were a shell verification command — `regression-iid-json.sh` |
| a terminal `echo "… PASS"` **guarded by an `if ! … exit 1; fi` above it** | all three class-**A** flags, the detector's most alarming class, are this |

**All three class-A flags are false positives.** That is worth saying plainly:
the class whose detail reads *"exit status is the message, not the
verification"* is, in this tree, 3 for 3 wrong. Add the two withdrawn before
they ever entered the baseline — a `grep -q … ||` and a `chk` continuation — and
**12 of 70 flags encountered this campaign were noise**. A detector whose flags
are mostly noise trains people to dismiss them; at 16 % this one is worth
reading, and the five shapes above are worth teaching it.

### Group 1, resolved and unresolvable

**One tested, confirmed and repaired.** `regression-deadguard.sh:46` —
`grep '^provenance: fork @' … | sed …` in statement position, status unread.
The test: suppress the provenance print inside `deadguard.py` and run it.

```
  flags now                                    40
  flags in the pinned baseline                 40
regression-deadguard: PASS (flag set unchanged)        exit 0
```

**No provenance line, and a PASS.** Instrument rule 4's exact shape — a
measurement whose artefact was never declared — **inside the script whose job is
to find dead guards**, and introduced by my own `OC-72` wiring. Now a
precondition: absent, it refuses with exit 2 and says the flag set is about an
unidentified tree. Verified both ways. Baseline **40 → 39**, one deletion: that
flag is repaired, not deleted.

**Six are in frozen evidence and cannot be resolved.** `repairs/2026-10-09-ind-02/rerun.sh`,
`audits/2026-09-30/…/issue272/repro.sh` ×2, `audits/2026-09-30/…/widths.sh` ×2,
`audits/2026-10-09-independent-audit/rerun.sh`. Guide rule 2 forbids editing
dated evidence, and that is the right rule: these scripts produced figures the
record cites, and changing them now would destroy the account of how those
figures were produced. **The consequence is recorded instead: the figures those
six lines helped produce carry an unverified-status caveat, and re-deriving them
would mean re-running the scripts in a copy rather than repairing them in
place.**

**Two are reachable only from Windows CI.** `.github/scripts/windows-facts.sh:719`
and `:732` — `grep … | while read` loops that drive the `GATE` logic. Resolvable
in principle; **not resolved, because the only honest test runs on a platform
this project cannot run locally**, and a `cmd`-shell script cannot be exercised
here at all (item 4).

### What group 2 would cost

48 lines, and the cost is not the editing — it is the **testing**. Each one needs
its own constructed failure: break the generator and confirm the downstream
check fails rather than passes; suppress the digest and confirm the comparison
refuses; un-land the mutation and confirm the landing proof fires. Item 4's
sweep did exactly this for `python3` across 22 scripts and took one background
run of several minutes plus a static pass; the compiler was **not** swept and
that alone is a comparable piece of work.

**Estimate: the 48 are roughly four sweeps** — one per tool class (`python3`
done, compiler, `perl`, `grep`/`sed` in pipes) — and the honest return is low,
because the class has no known realised instance: **every realised false pass
this campaign found was group 1 or group 3 in shape, never group 2.** That is
the argument for leaving them classified and not resolved, and it is an argument
from the absence of instances rather than from cost.

### What this does NOT establish

- **Eight of the nine group-1 lines are untested.** Six cannot be tested without
  re-running frozen evidence, two need Windows. Their assignment to group 1 is
  **reasoned from the construct's role, not measured** — which is a weaker claim
  than the one tested line carries, and is marked as such.
- The group-2 assignment rests on item 4's sweep for `python3` and on reasoning
  for the other tools. **A compiler sweep could move lines from 2 to 1.**
- The 16 % false-positive rate is **this tree's**, measured on 68 flags, and the
  five shapes are not a complete taxonomy of what the detector cannot see.
- Nothing reported upstream.

## OC-96 — the Windows `cmd` blocks are 26 lines, not ten; and the permutation fix the record recommended is not portable

**Owner's item 4 of 2026-10-25.**

### The `cmd` blocks: measured before choosing between the two options offered

The owner offered two honest answers — convert to PowerShell, which has a
parser, or record them as unchecked with the reason. **Measuring first changed
which answer applies.**

| | |
|---|---:|
| `cmd` blocks in `windows-platform-facts.yml` | **10** |
| of those, a **single line** invoking `bash .github/scripts/windows-facts.sh <subcommand>` through MSYS2 | **8** |
| blocks carrying real `cmd` logic | **2** |
| lines of `cmd` no syntax tool here can parse | **26** |

**Eight of the ten delegate**, and `windows-facts.sh` **is** `bash -n` checked by
`regression-workflows.sh`. So their substance is checked; only the wrapper line
is not. **Including the gating step** — *"8. Tally — THIS GATES"* is one line of
`cmd` calling into the bash script, so the hazard that bit the x86-64 job (a
syntax error aborting a gating step and hiding five gates) has almost no surface
here: there is nothing in that step to get wrong.

The two real blocks are step 0 (MSYS2 discovery, 16 lines) and step 7 (the
verdict summary, 10 lines). **Neither gates a verdict**, and a failure in either
is loud rather than silent: step 0 sets `MSYS2_ROOT`, so breaking it breaks every
later step's `bash.exe` path; step 7 writes the step summary.

**So: recorded as unchecked, with the number, and not converted.** The reason is
not "no tool exists":

- `pwsh` **is not installed on the development host** — measured. Converting
  would buy a parser that cannot be invoked here, only on the runner, which is
  the same place the conversion would first be tested.
- 8 of the 10 blocks have nothing to convert: one line each, and the substance
  is already checked.
- The job is **the only Windows evidence this project has**, and it cannot be
  run locally. Rewriting ten steps of it to gain a parse check over 26
  non-gating lines risks that evidence for no checkable gain.

`regression-workflows.sh` now reports this rather than printing a blanket
`not bash-checked (declared shell)`:

```
  11 block(s) checked with bash -n; 10 not, of which 8 delegate to a checked bash script
  UNCHECKED SURFACE: 2 block(s), 26 line(s) of shell no syntax tool here can parse
```

**A blanket skip and a measured one read the same and are not the same.**

### getopt permutation: the decision's facts, and a wrong mechanism in the record

The decision was already in the owner-decision bucket. What it lacked was
measurements, and what it carried was a **mechanism that does not work**.

**Measured on Darwin arm64.** `-i -a data.bin 1 -q -o out.json` → **exit 255,
no report**: BSD getopt stops at the first non-option, so the five trailing
words become operands and the operand count is wrong. Options-first → exit 0,
report written.

**Measured in this tree.** **0 of 16** real invocations put an option after an
operand. The 24 initial hits were prose, JSON issue bodies, log text and *label
strings* — `check_fail "ea_restart -o /dev/full" "${bindir}/ea_restart" -n -o …`
counts the label, not the command. So enforcing the documented order **costs
nothing here**, which is the fact the decision most needed.

**And the record's recommended fix is not portable.** The row said *"a
one-character change per tool"* — a leading `+` on each optstring. Measured with
a four-line probe:

| | glibc | macOS |
|---|---|---|
| leading `+` in optstring | *stop permuting* | **accepted as an option character** — `-+` taken as valid |

So `"+icatvql:o:"` would **silently add a `-+` option to all three tools** on the
development platform. The portable enforcement is a **prescan refusal** of an
option appearing after the first operand — which these tools already have a
prescan to carry, and which behaves identically everywhere. The row is
corrected; **the decision is still the owner's and is not made here.**

**The missing half is now measured, not argued.** Step **5c** of the x86-64 job
records whether glibc accepts the line macOS refuses, and — the part that
matters for `A05` — whether a permuted `-o` is **invisible to the pre-getopt
prescan**, since the prescan stops at the first operand while getopt does not.
`writeJsonReport`'s own guard is the authoritative one; 5c records whether the
**early** one fired, and gates that the capture survived the alias-after-operand
form either way.

### What this does NOT establish

- **The 26 unchecked `cmd` lines are unchecked.** Recording a number is not
  checking them. If one acquires a syntax error, step 0 will fail loudly and
  step 7 will not — and step 7's failure would be silent in exactly the way this
  entry says is tolerable only because it gates nothing.
- **Step 5c has not run.** The Linux permutation behaviour is **NOT RUN** and
  the prediction above is a prediction. Nothing in the decision row should be
  read as measured on glibc until that log exists.
- The `+` probe tested **macOS only**. That `+` means "stop permuting" on glibc
  is from its documentation, not from a run here.
- Nothing reported upstream.

## OC-97 — the probe I added to measure permutation aborted the job and skipped the full suite

**`OC-96` added step 5c to measure getopt permutation on glibc. Its first run
failed, and step 6 — the full suite and the outside-battery regression — was
SKIPPED.**

```
  ✓ 5b. R-1's blast radius through the production functions
  X 5c. getopt PERMUTATION: is an option after the first operand honoured?
  - 6. The full suite and the outside-battery regression
```

**That is `OC-84`'s failure mode exactly** — a step dying and taking the gates
after it — **caused by me, four commits after writing that entry.** The cause
differs: `OC-84` was an empty `if … then … fi`; this was a non-zero exit status.

### Why it died: a probe that cannot survive what it measures

GitHub runs `run:` blocks as **`bash -e`**. Step 5c measures **exit statuses**,
and the first non-zero one — **255, the tool's usage status, the very thing
being measured** — aborted the step before `rc=$?` could read it.

**A probe whose subject is failure must not run under `set -e`.** Step 5c now
sets `set +e` and ends with `exit 0`. Its own status is the wrong instrument
here, because every interesting outcome is a non-zero one; what judges it is the
**gate on its log** — a probe that did not measure leaves no
`PERMUTATION options-after:` line and the gate fails.

### Two more faults in the same probe, both of them mistakes already on this record

Found by running the probe **locally** before pushing again, which is the part
that should have happened first.

**The fixture did not satisfy its declared width.** It wrote `os.urandom` and
declared width 1, so the tool refused the file for carrying 8-bit symbols —
**exit 255 on the CONTROL arm**. A probe whose control fails measures nothing,
and every row would have been meaningless in the same direction. Now `b & 1`
bytes.

**The signal was file presence, not `errorLevel 0`.** `[ -s logs/perm.json ]`
was **true on a run that exited 255**, because `C14` claims the `-o` path with a
placeholder as soon as it is known — a failed run still leaves a report there.
**`OC-80` records this exact mistake being made in `F04`'s controls**, with the
sentence *"an assertion must key on a signal only the thing it is testing can
produce"*. It was made again here, in a probe written four days later.

### What the probe now measures, verified on Darwin arm64

```
PERMUTATION options-before: exit=0   assessed=YES      <- the control works
PERMUTATION options-after:  exit=255 assessed=no
PERMUTATION verdict: no permutation observed -- same as Darwin arm64
PERMUTATION alias-after-operand: exit=255
PERMUTATION capture-intact: YES
```

Run locally by extracting the step's `run:` body from the YAML and executing it,
so only the platform-specific answer needs the runner. **The glibc half is still
NOT RUN.**

### What this does NOT establish

- **The Linux suite did not run for `8c480ce`.** Step 6 was skipped, so that
  commit has no Linux suite result; the next run covers it.
- The glibc permutation answer is **NOT RUN**, and `OC-96`'s decision row
  still carries a prediction rather than a measurement.
- **Three faults in one 50-line probe**, two of them repeats of mistakes on this
  record. The lesson is not a new rule — it is that `bash -e` is the default in
  a `run:` block and the checklist for a new probe is already written in
  `OC-80`: run it where you can, make the control pass first, and key the signal
  on something only the subject can produce.
- Nothing reported upstream.

## OC-98 — the triage redone by mutation: group 1 is ONE, not nine, and the detector has a measured false negative

**Owner's items 1–3 of the return. `OC-95`'s group assignment was made by
inspection and is corrected here by measurement. It was wrong in the alarming
direction, which is the better direction to be wrong in and is still wrong.**

### Item 2 — the three class-A flags, broken rather than inspected

Each was given the treatment the group-1 flag got: break the thing the guard is
supposed to catch, run the guard, report whether it fails. **Three confirmed, none
confirmed-broken, none unmutable.**

| flag | mutation | control | mutant |
|---|---|---|---|
| `regression-input-identity.sh` | `test_run_base.h`: `if(!sha256.empty())` → `if(false)` — the **pre-`N-07` defect**, a report with no byte-binding | exit **0**, PASS | exit **1**, `KeyError: 'sha256'` |
| `sanitizer-restart-c01.sh` | `restart_main.cpp`: `h_i = H_I` → `2.0 * H_I` at both sites, rebuilt, pointed at via `EA_RESTART_SANITIZER_BIN` | exit **0**, PASS | exit **1**, `FAIL (the report assertions above did not hold)` |
| `verify-fixture-inventory.sh` | three separate mutations: a manifest line removed; an unlisted `sneaked.bin` added to `bin/`; one fixture's first byte changed | exit **0**, `PASS (11 inputs, 11 references; …)` | exit **1** each, and **each with its own distinct reason**: `found 10 and 11` / `unexpected input 'sneaked.bin'` / `SHA-256 mismatch` |

The third is the one that matters most, because its `PASS` line **states counts**
and the detail that flagged it reads *"exit status is the message, not the
verification"*. Three mutations, three distinct refusals — the message is reached
only when all of it holds.

### Item 1 — the six "frozen and unresolvable" flags: NONE is group 1

The owner's objection was right and the answer is better than the objection
expected: *"freezing the script does not retire the figures it produced"* — so
each of the six was read in its surroundings instead of classified by its role.
**All six are group 2 or 3, and no verification needs withdrawing.**

| flag | what the surroundings say |
|---|---|
| `repairs/2026-10-09-ind-02/rerun.sh:45` | **`set -e` is active at that line** — `set -eu` at :3, `set +e` at :40, `set -e` restored at :43 — so a failing assertion aborts. **The detector's own `has_set_e` field said `True` and its detail said `set -e present`. I did not read the field that was answering the question.** → group 2 |
| `issue272/repro.sh:11`, `:15`, `:18` | the flagged commands **print the figures into the transcript that IS the evidence**. A silent failure yields visibly absent output, not a wrong number — the recorded transcript is its own witness. → group 2 |
| `widths.sh:6`, `:13`, `:14` | same shape: `python3 cmpc.py …` prints into the recorded transcript. → group 2 |
| `audits/2026-10-09-independent-audit/rerun.sh:71` | the **next line is `echo "$?" >"$out/truepad-unattested-tools.status"`** — the status is captured to a file the audit reads. The matcher's `STATUSREAD` does not recognise that form. → **group 3**, a seventh instance of the one blind spot |

**And the two "reachable only from Windows CI" were not.** `windows-facts.sh`'s
tally is pure `bash` reading two files, so it runs here. Tested, three paths:

```
empty verdict log      -> exit 2  "TALLY REFUSED: ... no stage recorded a verdict."
an unexpected GATE FAIL -> exit 1  "UNEXPECTED FAILURE: a brand new failure nobody expected"
an expected failure only-> exit 0  "every failure is a documented platform fact"
```

The pipes at `:719` and `:732` can only fail silently if `$V` is unreadable, and
`$V`'s existence and non-emptiness are **preconditions checked at `:703`** with
the comment *"A tally over nothing is not '0 failed'; it is 'nothing ran'."* →
group 2. **"Needs Windows" was my assumption, not a property of the script.**

### The corrected triage

On the 67 lines the detector now reports:

| group | `OC-95` said | measured |
|---|---:|---:|
| 1 — reaches a figure or a claim | 9 | **1** |
| 2 — does not | 48 | **54** |
| 3 — false positive | 11 | **12** |

**Group 1 is the one line already tested and repaired** —
`regression-deadguard.sh`'s provenance declaration. Every other line I had put
in group 1 was there because I reasoned from what the construct *does* rather
than reading what surrounds it.

### Item 3 — the re-run, and a measured FALSE NEGATIVE

**The re-run after repairing `regression-deadguard.sh`:** 68 → **67** flagged
lines, 40 → **39** signatures. The change is exactly the repaired flag plus a
line shift (`B:48` → `B:66`). **No group assignment changed**, and the mis-wiring
was in the *wrapper* that runs the detector, not in the scanning, so it could not
have affected other files.

**But a positive control found a real false negative.** One planted dead guard of
each class, scanned:

```
   detected: ABC   MISSED: D
```

The planted class-D pipe was reported as **C**. Cause:
`has_pipefail = 'pipefail' in src` — **a substring search over the whole file,
comments included**. My control's comment said *"no pipefail"*, which the
detector read as having it. And where a file also has `set -e`, the `D` branch is
skipped and `elif not has_e` is false, so such a pipe is flagged as **nothing** —
a silent miss, not a misclassification. `set -o errexit` was unanchored the same
way.

Fixed to require an actual setting. **Its reach in this tree today is zero
files** — one file mentions `pipefail` and does set it — so the flag set is
**unchanged by the fix**, which is how the fix is verified as safe. The control
now reports `detected: ABCD   MISSED: none`.

**So the floor framing is no longer theoretical.** `1` is a **floor on the live
surface**, not a count: the detector has a measured 16 % false-positive rate, a
*demonstrated* false negative, and four patterns that between them do not claim
to cover every dead-guard shape. **Every appearance of a group-1 count in this
record is a floor**, and `OC-95`'s text is corrected to say so.

### What this does NOT establish

- **One class of false negative was measured, not the rate.** The control tested
  the four shapes the detector claims; it says nothing about shapes it does not
  claim.
- The three class-A confirmations rest on **one mutation each** for two of them
  and three for the third. A guard can catch one break and miss another.
- The `issue272` and `widths` flags are group 2 because **the transcript is the
  witness** — which holds for evidence already recorded and would not hold for a
  future re-run whose output nobody reads.
- Nothing reported upstream.

## OC-99 — the gh conclusion restated as what is establishable, and the discriminator recorded as a standing hazard

**Owner's item 4 of the return: `"0 figures whose provenance cannot be
established"` is one claim too strong when three calls' output is gone.**

### The claim, withdrawn and replaced

`OC-93` reported:

> | figures on the record whose provenance cannot now be established | **0** |

**That is not establishable and is withdrawn.** Three unqualified calls —
`gh workflow list` twice and `gh run list --limit 2/3` — produced output that no
longer exists; it sat in compound commands whose `head` truncation was consumed
by a 404. **If the output is unrecoverable, it cannot be compared against any
document figure**, so a claim about what it did or did not support is not
available in either direction.

**The establishable statement, which is narrower:**

> **Every figure, run identity and CI conclusion in any document is accounted
> for by an `-R`-qualified call.** Separately, **three calls' output is
> unrecoverable**, and whether they returned anything a document relies on
> cannot be determined — only that no document's content requires them.

The difference matters: the first version claimed a property of the *three
calls*. The replacement claims a property of the *documents*, which is what the
evidence supports. The three remain visible as unrecoverable rather than
absorbed into a zero.

### The discriminator is a standing hazard, not a detail of one sweep

| | `systemslibrarian/…` (the fork) | `usnistgov/…` (upstream) |
|---|---|---|
| name | `SP800-90B_EntropyAssessment` | `SP800-90B_EntropyAssessment` |
| visibility | `PUBLIC` | `PUBLIC` |
| default branch | `master` | `master` |
| `hasIssuesEnabled` | **false** | **true** |
| `isFork` | **true** | **false** |

**Three of the five fields are identical, and the two that differ are not the
ones anyone reads.** `OC-93` identified which repository had answered *only*
because `hasIssuesEnabled` happened to be in the field list — it was not the
field being queried for, and nothing in the method would have caught it
otherwise. Had the query asked for name, visibility and branch alone, the sweep's
honest verdict would have been **"provenance not establishable"**.

So this is a property of the pair of repositories, permanent for as long as both
remotes are configured, and it applies to **every future call**:

- a wrong-target answer is **well-formed and plausible**, never an error;
- `isFork` and `hasIssuesEnabled` are the **only** cheap discriminators, and a
  query that omits them cannot tell the two apart;
- **so the target is named, never inferred from the answer.** `-R` on every
  call, `gh repo set-default` pinned, and recorded commands carrying the
  repository — all three enforced by `regression-docs.sh` for the third.

### What this does NOT establish

- **The three unrecoverable calls stay unrecoverable.** Nothing here recovers
  them; the claim about them is withdrawn rather than resolved.
- The discriminator table is **today's**. If upstream disabled issues, or the
  fork enabled them, the cheap discriminators would narrow to `isFork` alone.
- Nothing reported upstream.

## OC-100 — the undeclared-pair backlog, banded: 27 reach a figure, over 15 mechanisms, 14 of them already tested

**Owner's item 5. Band sizes first, as asked, then the top band only.**

### The two facts, and the bands

**Fact (a) — did the later repair delete or rewrite a non-comment line the
earlier one added?** **True for all of them by construction**: that is how the
set was selected, and a rewrite appears as a deletion in a unified diff.

**Fact (b) — does either repair sit on a path that reaches a figure?** Defined by
path, and the definition is stated rather than assumed: **FIGURE** = production
code (`cpp/` outside `selftest`), the oracles, and the figure-producing tools —
these compute or certify numbers the record cites. **CLAIM** = the harness and
CI, where a wrong result reaches *"the suite is green"* rather than a number.

| band | both facts | count |
|---|---|---:|
| **1** | (a) and (b) — **reaches a figure** | **27** |
| **2** | (a) only — reaches a claim | **39** |
| | total undeclared | **66** |

(66, not 65: four more commits have landed since `OC-94` measured it.)

### Band 1 collapses to 15 mechanisms, and that is the real unit

27 pairs, but only **15 distinct earlier mechanisms** — seven pairs all touch
the same one. **Testing a mechanism once discharges every pair that touched it**,
so the work is 15, not 27.

| earlier mechanism | pairs | the case that exercises it | status |
|---|---:|---|---|
| `65b00d8` mutation landing + the labelled read | **7** | `mutation-lib.sh`'s `MUTATION-DID-NOT-APPLY` third outcome; `oracle-selftest`'s labelled-read refusals | tested — suite green, 3 mutation harnesses pass |
| `c2f2b94` `A02`/`A06`: the width-1 exclusion, the platform manifest | 3 | `entropy_floor.py` at width 1 **and** width 8; `regression-platform-deltas.sh`'s 6 cases | tested (`OC-78`, and again here) |
| `acedae5` `F13` unreachable, `C22c` values | 3 | `compression_ceiling_exact.py`, `zalpha_ceiling_by_n.py` | tested (`OC-86`) |
| `b12247c` canary re-signatured 3-way | 2 | `build-provenance-canary.sh` | **tested here** |
| `5074fff` `C23` as a recomputed decision | 2 | `oracle-selftest`'s restart cases; `restart_multinomial_max.validate()` | tested (`OC-82`, `OC-87`) |
| `b072bf7` the oracles' exit contract | 1 | `oracle-selftest`, 18 cases | tested (`OC-82`/`OC-83`) |
| `7a0be01` `fix(C23)`'s cutoff method | 1 | the `restartCutoffMethod` gate | tested (`OC-94`) |
| `6b4717e` `OC-67`'s per-family denominators | 1 | `entropy_floor.py`'s family table | tested (`OC-78`) |
| `ada37a1` `OC-62`'s compression-vs-collision | 1 | `zalpha`, `compression_ceiling_exact` | tested (`OC-86`) |
| `feef1a1` the outside battery's figures | 1 | `regression-outside-battery.sh` | tested — in the suite |
| `210aed6` `oac-13`'s atomic report write | 1 | `regression-output-aliasing.sh`'s `F03` cases | tested (`OC-77`), shown failing pre-repair |
| `8ff739d` the canary itself | 1 | `build-provenance-canary.sh` | **tested here** |
| `9aa991d` the canary widened to both `long double` formats | 1 | same | **tested here** |
| `4ad3095` the divergence-figure enforcement | 1 | three drift mutations | tested (`OC-91`) |
| `5c3353f` two instrument rules published | 1 | **none — it is rule text, not a mechanism** | **no runnable case; declared as such** |

**14 of the 15 have a runnable case, and all 14 were exercised this campaign.
One has no runnable case at all.** So the backlog was a **declaration** gap, not
a coverage gap — which is what rule 12 says the obligation is, and the reason it
is about declaring rather than about testing more.

### What the canary run established, and a gap it exposed

```
canary: TREE    REPAIRED
canary: BUILD   NOT-DISTINGUISHED
canary: NOTE    REPAIRED is not REVIEWED: the repairs are self-authored and unreviewed.
```

Exit 0, digest matched. Three of the fifteen mechanisms discharged at once.

**And the canary is not in the enforced suite** — not in
`regression-script-inventory.txt`, not run by `run-all-checks.sh`. It is run by
hand and by **step 4 of the x86-64 job**. So a mechanism that three band-1 pairs
touched is exercised by CI and not locally, which means a local green suite says
nothing about it. **Recorded, not changed:** it is slow, CI runs it on every
push, and adding a 25th check for something already gated is a worse trade than
saying where it runs.

### What this does NOT establish

- **Band 2's 39 pairs are not examined.** They reach a claim rather than a
  figure, and nothing here says they are sound.
- "Tested this campaign" means **the mechanism's own case was run and passed**,
  not that the pair was tested as a pair in the rule-12 sense for all 27. The
  seven pairs on `65b00d8` share one case; if that case is too weak for one of
  the seven, this entry would not have found it.
- The FIGURE/CLAIM split is **by path**. A harness whose output is cited as a
  figure would be misfiled by it, and `regression-outside-battery.sh` pins
  four-significant-figure values that **are** cited — it is in band 1 only
  because `tools/outside-battery-check.cpp` is.
- Nothing reported upstream.

## OC-101 — two standing decisions recorded, and the route list contradicted one of them twice

**Owner's constraints of 2026-10-25: no independent cryptographer or security
review, ever — `C8` stays WILL NOT BE DONE; and the verdict stays partially
established, permanently.**

### The first decision was already in the record, and I contradicted it anyway

`CLOSING-INVENTORY.md`'s will-not-be-done bucket has said since 2026-10-15:
*"Independent review of any repair. The owner has decided there will be none."*

**`FORK-DIVERGENCE-AND-TRUST.md` §5, as I rewrote it in `OC-91`, led with
"Independent review of the production delta" and listed three more items asking
for independent review.** §0 item 7 of that same document exists to correct the
previous version for recommending a declined route — and the rewrite made the
identical error with a different route, in the section written to fix it.

That is worth stating plainly rather than softening: **the correction of a
contradiction reproduced the contradiction.** The check that catches the
upstream version of this (`regression-docs.sh`'s stale-claim registry) has no
entry for "independent review", because the declined-route class was treated as
a one-off rather than as a class.

### What §5 says now

No route list. Two decisions and what they settle:

**Decision 1 — nothing is reported upstream** (2026-10-15). Extended with a
clause `OC-93` made necessary: **no request of any kind is sent there** — not an
issue, pull request, comment, workflow dispatch, or unqualified `gh` call,
because one such call did reach `usnistgov` and was refused only by a 404.

**Decision 2 — no independent review of any kind, ever** (`C8`, restated
2026-10-25). Its consequences are larger than Decision 1's and are now stated
rather than implied:

- **`REPAIRED` never becomes `REVIEWED`.** The third status in the entry
  vocabulary is named only to say what is permanently absent.
- every *"independent verification remains"* note in the tracker, `C-01`'s
  included, **resolves here and nowhere else**;
- the four defects in section A.2 were introduced by this fork's own repairs,
  three of them by one repair interacting with another, and **that mechanism is
  reviewed by nobody but its author** — rule 12 is the whole of the mitigation;
- the instruments are in the same position: two withdrawn verifications, a
  five-of-nineteen false pass inside the enforced documentation check, and a
  detector with a measured 16 % false-positive rate **and a demonstrated false
  negative**, all written by the same author.

**And the verdict is therefore PERMANENTLY PARTIALLY ESTABLISHED** — not
"pending independent review", because there is no pending:

| | |
|---|---|
| established | that specific defects reproduce, that specific repairs change the reproduced behaviour, and that specific figures re-derive — each on the platforms its entry names, by instruments this project wrote |
| permanently not established | that the repairs are correct, the instruments sound, the figures right, or that any of it would survive a reviewer |

The readiness statement no longer says the code is "a suitable candidate for
independent review". It says it **is not, and will not become, independently
reviewed software**, and that only reversing Decision 2 would change that.

### What this does NOT establish

- **`C8` has no prior definition in this repository.** The label is the owner's;
  the decision it names is recorded in the will-not-be-done bucket and in §5,
  and the two are now cross-referenced. If `C8` means more elsewhere, this
  entry records only the part stated.
- **The declined-route class is now checked, which it was not when this entry
  was first written.** Seven phrases joined the stale-claim registry —
  `Independent review of the production delta`,
  `suitable candidate for independent review`, `route to external trust`,
  `Submit generally applicable repairs upstream` and three siblings — so a
  document that *recommends* a closed route fails the suite unless its paragraph
  says the route is closed. Verified: appending
  *"The next step is an Independent review of the production delta."* to the
  divergence document gives
  `stale claims present again: FORK-DIVERGENCE-AND-TRUST.md:559`.

  *Two drafts of that were wrong.* The markers went into the certified-floor
  check's regex instead of the stale-claim check's `EXEMPT` — two checks, two
  exemption lists, and I edited the one I had most recently been reading. Then
  the surviving hit was `OC-91`'s own correction table, whose cell says
  *"contradicts the owner's standing decision"* — a phrasing the marker list did
  not know. **Third stemming-or-phrasing miss in this file**, and the lesson is
  the same each time: the exemption list must learn the words the corrections
  actually use, not the words the check's author expects.
- Nothing reported upstream.

## OC-102 — glibc permutes, measured; and the permuted `-o` bypassed the early guard while the choke point held

**Run `40241103943`, conclusion `success`. Step 5c's measurement is in, and it
settles both halves of `OC-96`'s open question.**

### Half one: glibc permutes

```
PERMUTATION options-before: exit=0   assessed=YES
PERMUTATION options-after:  exit=0   assessed=YES
PERMUTATION verdict: glibc PERMUTES -- an option after the operand is honoured
                     here and refused on Darwin
```

Against Darwin arm64, measured in `OC-96`:

| `-i -a data.bin 1 -q -o out.json` | exit | assessed |
|---|---:|---|
| **x86-64 Linux, glibc** | **0** | **YES** |
| **Darwin arm64, BSD getopt** | **255** | **no** |

**The same command line assesses on one supported platform and is a usage error
on the other.** That is no longer a prediction, and `CLOSING-INVENTORY.md`'s
owner-decision row is updated from prediction to measurement. The decision —
enforce the documented order by a prescan refusal, or leave it platform-dependent
— **remains the owner's and is not made here.**

### Half two: the early guard WAS bypassed, and the choke point caught it

This is the half that mattered, and it is the better result.

With `-o` placed **after** the operand, `prescanOutputAndOperand()` stops at the
first operand and never sees `-o` — so on a permuting platform the **early**
identity guard is not armed, while getopt honours the option anyway. Measured:

```
PERMUTATION alias-after-operand: exit=255
PERMUTATION capture-intact: YES
  alias stderr: Error: refusing to write the report to 'logs/permalias.bin': it is
               the same file as the input 'logs/permalias.bin' ... Writing it would
               destroy the input capture. Nothing has been written.
```

**That refusal comes from `writeJsonReport`'s own guard, not from the prescan.**
It is the choke-point check — the one moved inside `writeJsonReport` for `A05`
and hardened for `F03`, covering all 54 report-write call sites — firing on the
platform where the early guard was genuinely bypassed. **The design's whole
premise is that the authoritative check sits at the write, not at the entry
point, and this is the first measurement in which the entry point actually
failed and the write still held.**

**And this time the sentence is true.** `F03` recorded the same guard printing
*"Nothing has been written; the input is untouched"* when both halves were false.
Here the capture's SHA-256 is compared before and after and is **unchanged** —
`capture-intact: YES` — so the message is accurate. The gate asserts that
specific line, not merely that the step ran.

### The rest of the run

The Linux suite: **23 passed, 0 failed, 1 could not run** —
`regression-platform-deltas` abstaining, as that platform's manifest requires.
The suite stayed green through the detector's `has_pipefail` repair, the
stale-claim registry's seven new declined-route entries, and the widened
document scope.

### What this does NOT establish

- **Two platforms, two `getopt` implementations.** binary128 on Linux aarch64 is
  still **NOT RUN**, and nothing here says what a third libc would do.
- **It does not establish that the prescan is harmless.** It establishes that on
  the one aliasing case measured, the choke point caught what the prescan
  missed. A different early-guard function — the `--version` prescan, say — has
  no second line of defence behind it, and `OC-80`'s note that permutation may
  let a late `--version` reach getopt is **still unmeasured**.
- The permutation measurement is of **`ea_non_iid`**. `ea_iid` and `ea_restart`
  share the prescan but were not run in step 5c.
- Nothing reported upstream.

## OC-103 — a late `--version` measured on both platforms, and every prescan consumer enumerated

**Owner's items 1–4 of the 2026-10-25 return. Measurement only; `OC-104` is the
fix, as a separate pass.**

### Item 1 — the measurement, both platforms, all three tools

**There is no short version spelling to measure.** None of the three optstrings
(`"icatvl:qo:"`, `"icatvql:o:"`, `"invqo:s:"`) contains `V`, and `--version` is
implemented **only** by the prescan — so `-V` is simply an unknown option. It is
measured anyway, because "there is no short spelling" is itself a result.

The probe was wrong twice before it was right, and both faults are the recorded
ones:

- **a reused output path.** The first run reported *"report written YES"* at
  exit 255 with nothing assessed. There was no write: the previous row's report
  was still there. One fresh directory per row.
- **urandom declared width 1.** The control arm exited 255 — *"Data (8) does not
  fit within described bit width: 1"* — so every row was being compared against
  a control that did not work. `OC-80` records this exact fixture mistake; it
  was made again here. Fixed to 0x00/0x01 bytes.

With a working control and a negative control, so the `assessed` signal is
**observed in both polarities**:

| tool | form | exit | banner | assessed | report |
|---|---|---:|---|---|---|
| all three | `control` (options first) | **0** | no | **YES** | written, `errorLevel 0` |
| all three | `neg-control` (absent input) | 255 | no | no | written (the `C14` error report) |
| all three | `<in> <w> --version` | **255** | no | no | **no** |
| all three | `<in> <w> -o r --version` | **255** | no | no | **no** |
| all three | `<in> <w> -V` | **255** | no | no | **no** |
| all three | `<in> <w> -o r` | **255** | no | no | **no** |

**Darwin arm64, measured 2026-10-25.** On glibc, CI step 5d measured the same
four forms: `LATEVERSION VERDICT: no vacuous run observed`. **So the outcome
that would have ranked above everything else — exit 0 with nothing assessed on
Linux — does NOT occur.** Every late form fails closed on both platforms,
through `print_usage()`: with BSD `getopt` the options stay as operands and
`argc - optind` is 4 rather than 1 or 2; with glibc they are permuted into
unknown options and rejected. **The hazard was real and the outcome was benign**,
which is why it was measured before it was repaired.

### Item 2 — every prescan consumer, with its backstop or without one

The prescan family is **two walks of argv with the same stopping rule**, and
between them they produce **three** things. The products are what matters, because
permutation does not corrupt all of them equally.

| product | produced by | corrupted when options follow the operand? |
|---|---|---|
| `*operand` | `prescanOutputAndOperand` | **no** — permutation does not move *which element is the first operand* |
| `*outPath` | `prescanOutputAndOperand` | **YES** — a `-o` after the operand is never seen; `outPath` is empty |
| the `--version` verdict | `versionOptionRequested` | **YES** — the walk returns false |

**Six consumers read those three products:**

| # | consumer | site | reads | corrupted? | second line of defence at the point of effect |
|---:|---|---|---|---|---|
| 1 | arms the protected input path | `non_iid:140`, `iid:135`, `restart:409` | `*operand` | no | the authoritative `protectInputPath(file_path)` post-`getopt` (`:248`/`:245`/`:468`) — **but that runs AFTER the `C14` placeholder write**, which `claimReportTarget` performs inside the `getopt` loop, so for that one write the early arming is the *only* arming |
| 2 | the early aliasing refusal | `non_iid:141`, `iid:136`, `restart:410` | `*outPath` **and** `*operand` | **YES** | **two**: `writeJsonReport`'s choke point at `TestRunUtils.h:312`, measured to hold under permutation (`OC-102`), and the post-`getopt` `outputTargetIsSafe(outputfilename, file_path)` |
| 3 | the `inPath == NULL` short-circuit inside that refusal | `TestRunUtils.h:165` | `*operand` | no | same as 2 |
| 4 | the report-path choke point | `TestRunUtils.h:312` | the armed state from 1 | no | **none — it IS the last line**, by design |
| 5 | the temp-path choke point | `TestRunUtils.h:361` | the armed state from 1 | no | **none — it IS the last line**, by design |
| 6 | print the banner and `exit(0)` | `non_iid:127`, `iid:122`, `restart:396` | the `--version` verdict | **YES** | **UNPROTECTED** — nothing else implements `--version` at all |

**The answer to "class or instance": a class, and the class has exactly two
members.** `*outPath` and the `--version` verdict are the only two products
whose correctness depends on *position*, so they are the only two things
permutation can take away. `*operand` does not depend on position, which is why
consumers 1, 3, 4 and 5 are sound and why `OC-102` found the capture intact.

**Count, with the identity of what it counts: 1 of 6 consumers has no second
line of defence** — consumer 6. Consumers 4 and 5 also have nothing behind
them, but they are *terminal by design*, which is the opposite of unprotected.
And consumer 6's lack of a backstop **costs nothing today only by accident**:
the fallback is `getopt`'s invalid-option path, measured above as exit 255. It
is fail-closed because `--version` happens not to be in any optstring, not
because anything was arranged to catch it.

### Item 3 — the one that could not run

**`regression-platform-deltas`**, and it is the **expected abstention**, not the
undiagnosed failure: its `known-platform-deltas.txt` block is `platform Darwin
arm64 Apple clang`, there is deliberately **no Linux block**, and the script
abstains rather than inventing one. `regression-docs` **PASSED** on Linux in
that run, both inside the suite and in its own gated log — so **the undiagnosed
Linux `regression-docs` failure did not reproduce, and stays OPEN with its four
dead hypotheses**, because a defect that stopped reproducing without being
understood stays open.

### Item 4 — what 5c establishes about the two-platform reporting rule

The rule has been *"a correct repair argument is still a per-platform claim"*.
**5c establishes something stronger and worse: a COMMAND LINE does not
necessarily denote the same OPERATION across supported platforms.** The
reporting rule therefore binds one level earlier than it was written — not only
"the same test may give different answers on two platforms", but "the same
*request* may not be the same request". Evidence: `ea_non_iid -i -a f 1 -q -o r`
**assessed and wrote `r`** on x86-64 glibc and **died on the usage path with
nothing assessed** on Darwin arm64.

**And the freshly checked result, not the number carried forward.** The previous
answer was *0 of 16 real invocations*, from reading scripts. Reading scripts is
the wrong instrument: a regex over the tree found "65 sites", almost all of them
English prose, and a stricter regex found 7, because the selftest scripts invoke
through `"${ea_non_iid}"` rather than by name. So an **argv logger was compiled
into all three tools** and the full suite was run under it.

**256 real invocations captured**, across five tool-binary names (`ea_non_iid`
87, `ea_restart` 95, `ea_iid` 54, `ea_asan` 19, `ea_non_iid_identity_test` 1;
0 unmapped). **2 of the 256 place an option-shaped argument after the first
operand**, and **both are numeric `H_I` values** — `ea_restart -n r8.bin 8 -inf`
and `... 8 -1`, in `regression-restart.sh`'s `N-04`. **0 of 256 use a genuine
option spelling after the operand.**

So the expected answer *"none"* is confirmed as a checked result at sixteen times
the coverage — **and the two it did find are ones the earlier method could never
have found**, because `OC-40` had already recorded them as a platform note and
they are not a "comparison or recorded delta" at all. The hazard is recorded as
**latent for genuine options** and **live-but-benign for numeric operands**: for
those two, `OC-40`'s divergence is real, present today, and both platforms
refuse.

### What this does NOT establish

- **Nothing about shapes not measured.** Four forms, three tools, two platforms.
- The 256 invocations are **the suite's**, not an operator's. A January runbook
  command typed by hand is not in that population; the documented examples were
  read separately and all put options first.
- `ea_asan` and `ea_non_iid_identity_test` were mapped to the optstrings of the
  tools they are built from. That mapping is **by inspection of the build rules**,
  not measured from the binaries.
- Nothing reported upstream.

## OC-104 — the prescan refusal, authorized and landed: one walk of argv, and a test verified by breaking it

**Owner's item 3, authorized explicitly. This is a BEHAVIOUR CHANGE, not a
repair, and it is the only change in this fork that refuses a command line
upstream accepts.**

### What it does

All three tools refuse a command line with an option placed after
`<file_name>`, naming the offending argument and printing the correct form. The
portable prescan refusal, **not** the leading `+` in the optstring — `OC-96`
measured that `+` does not work on macOS.

```
Error: '-q' looks like an option but appears after the file operand 'capture.bin'.
       Refusing to run: what this command line MEANS depends on the C
       library. glibc rearranges it and parses '-q'; BSD and macOS treat
       it as another operand and fail on the usage path. One line, two
       supported platforms, two different operations -- and guessing which
       was wanted is worse than refusing. Nothing has been written.
```

### THE NUMERIC EXEMPTION, which the measurement forced

The argv logger of `OC-103` found that **2 of 256 real invocations** put an
option-shaped argument after the operand, and both are **numeric `H_I` values**:
`ea_restart -n r8.bin 8 -inf` and `... 8 -1`. A number after the operand is a
**value**, not an option — no optstring here contains a digit — and refusing
`-1` with *"put every option before the file"* would be a wrong message about
something the operator meant as a value. So `argLooksNumeric` (a full-string
`strtod`) exempts them.

**This is the single most important consequence of measuring before repairing.**
The text sweep had said the only affected sites were step 5c's own probes. Had
the refusal landed on that basis it would have broken `N-04`, which is a check
that `ea_restart` refuses a malformed `H_I` — a guard, broken by a guard.

**It also means `OC-40`'s divergence REMAINS for exactly these arguments**, and
that is recorded rather than changed: `-inf` still reaches the `H_I` parser on
BSD and still goes through `getopt`'s invalid-option path on glibc. Both refuse;
the message differs.

### RULE 12 DECLARATION — the two pairs, both tested

**`A04`/`F04` — `versionOptionRequested`'s cluster walk.** Rather than add a
*fourth* copy of the walk-to-the-first-operand logic, the refusal, the identity
prescan and the `--version` gate now share **one** walk, `scanArgs`, which
collects every product any caller needs. **Three copies of that walk is
precisely how `F04` happened**: the cluster arithmetic was repaired in the
prescan and left wrong in the version gate, so the bypass stayed fully open
through a different spelling of the same options. A unified walk makes that
class of defect structurally impossible rather than merely fixed.

*Pair test:* the four `F04` cluster forms (`-o`, `-vo`, `-qo` `--version`, and
`-Z --version`) must behave exactly as `F04` left them, and the new refusal must
stay silent on all of them — they put their options before the operand. **4 of 4
PASS.**

**`A05`/`F03` — the identity prescan and the `writeJsonReport` choke point.**
The refusal fires earlier than both.

*Pair test:* the permuted aliasing form `perm.bin 1 -o perm.bin` must now be
refused **by option order**, with the capture byte identical; and the ordinary
form `-o perm.bin perm.bin 1` must still be refused **by identity**, not by
option order — the earlier repair still doing its own job is the other half of
the pair. **2 of 2 PASS.**

### THE TEST IS VERIFIED BY BREAKING IT, AND BOTH RUNS ARE RECORDED

`cpp/selftest/regression-option-order.sh`, 29 checks. The mutation removes the
`refuseOptionAfterOperand` **call** from all three mains, leaving the function
compiled but unreachable — the state the tree was in before this entry.

| build | `build-state` sha256 (`ea_non_iid`) | result |
|---|---|---|
| refusal present | `2dc6b5bb4453b955` | **`regression-option-order: PASS`**, 29 of 29 |
| refusal removed | `47fd9e5ae3322d53` | **`regression-option-order: FAIL (10)`** |

The two builds are distinguished by digest, so "the mutation landed" is shown
and not assumed. The ten failures are the nine refusal rows (three forms ×
three tools) plus the `A05` permuted-alias pair row.

**And on macOS the mutant still exits 255 on every one of those rows.** What the
refusal changes *here* is the message and the cross-platform agreement, not the
exit status — BSD `getopt` was already failing these lines on the usage path.
The exit-status difference is a **glibc** effect, which is why the assertion
moved into CI as well.

### THE TEST'S OWN DEAD ASSERTION, found by running it

The first version of the regression reported **6 failures against the repaired
build**. Cause: `-q` was in its lead options, and quiet mode **suppresses the
result line**. So `assessed()` could never read `YES` — every *"nothing was
assessed"* assertion would have passed whatever the tool did, and every control
arm failed. `-q` was removed so the signal is live in **both** polarities.

**This is the sixth instrument in this fork whose failing state had never been
observed, and it was caught only because the owner required the break-run.** A
test whose failing state was never observed is not a test.

### CI: the measurement had to move OUT of the tools

Step 5c measured permutation **by running `ea_non_iid` with an option after the
operand**. With the refusal in place that probe would report
*"no permutation observed"* — **false**, and worse than no measurement, because
the refusal fires before `getopt` is reached. A `getopt` property is a property
of the C library, so 5c now measures it with a **twenty-line C program** that
calls `getopt` and nothing else, and asserts the tools' refusal separately.

Step 5d's gate moves from *"it measured"* to the outcome the fix pass owed: **no
vacuous run, all nine late forms refused by name, and no control wrongly
refused** — counted rather than grepped, so a form that stopped being measured
cannot pass as a form that was refused.

Writing 5c cost two further instrument errors, both caught before pushing: a
**heredoc** whose closing delimiter must sit at column 1 **terminated the YAML
block scalar** (the workflow stopped parsing), and a `\n` that survived three
escaping layers as `\\n` so the C program printed a **literal** `\n`.

### Checked against every existing invocation before landing

- **256 real invocations** under the argv logger: **0** use a genuine option
  spelling after the operand (`OC-103`).
- **The January re-pin procedure** — `ea_non_iid -vv bin/ringOsc-nist.bin` —
  options first, unaffected.
- **The documented examples** in `BUILDING.md` — options first.
- **The two sites it does break** are step 5c's own permutation probes in
  `.github/workflows/x86-64-platform-facts.yml`, whose purpose was to exercise
  this exact shape. Converted to assert the refusal.
- **Nothing TruePad invokes was read or changed.** `~/repos/TruePad` was not
  touched.

### Documented where a user would find it

The tools' own `print_usage()` (a user who hits the refusal reads that text),
`BUILDING.md`'s *Operator command line* section, and a new
`FORK-DIVERGENCE-AND-TRUST.md` **§A.3**, which exists because a deliberate
divergence is neither an inherited defect nor one this fork introduced.

### What this does NOT establish

- **Nothing about operands that begin with `-` and are not numbers.** A file
  genuinely named `-weird.bin` now needs `--`; it needed `./` before.
- The refusal is **not** a fix for the unarmed guard, it is a fix for the
  ambiguity. Consumer 2 of `OC-103`'s table is still unarmed on a permuting
  platform *for any line that reaches it* — there are now simply no such lines.
- **The 29 checks run on Darwin arm64.** Their glibc behaviour is asserted by CI
  steps 5c and 5d, not by this script's own 29 rows.
- Nothing reported upstream.

## OC-105 — the band-1 pairs tested by BREAKING the earlier mechanism: 4 of 9 are unguarded, and C22c is one of them

**Owner's item 4, and the owner was right that it is the item that matters
most. `OC-100` reported that 14 of band 1's 15 mechanisms "were exercised this
campaign". That claim is true and it is not a pair test.**

### What was wrong with `OC-100`'s reassurance

"Exercised" meant **the mechanism's own case was run and it passed**. A passing
test cannot distinguish *"the earlier mechanism still works"* from *"nothing
checks the earlier mechanism any more"* — and the second is exactly the risk a
repair-interaction pair carries. So each mechanism was given the treatment the
class-A dead-guard flags got in `OC-98`: **break the earlier mechanism, run the
case that is supposed to catch it, and report whether it fails.**

`audits/2026-10-11-independent-audit/reproducers/band1-pair-mutations.sh`, with
four outcomes rather than two — `CAUGHT`, `NOT CAUGHT`,
`MUTATION-DID-NOT-APPLY`, `CONTROL FAILED` — because a mutation that did not
land and a case that was already failing each earn no verdict. It refuses to
run on a dirty tree, since it restores with `git checkout --`.

### The result

```
  A02/A06 platform-delta manifest    CAUGHT      control 0, mutant 1 (c2f2b94)
  A02/A06 the tolerance itself       CAUGHT      control 0, mutant 1 (c2f2b94)
  C22c compression ceiling, n=1e6    NOT CAUGHT  control 0, mutant 0 (acedae5+ada37a1)
  C22c compression ceiling, n=8e6    NOT CAUGHT  control 0, mutant 0 (acedae5+ada37a1)
  OC-67 per-family denominator       NOT CAUGHT  control 0, mutant 0 (6b4717e)
  the oracles' exit contract         CAUGHT      control 0, mutant 1 (b072bf7)
  outside-battery pinned figures     CAUGHT      control 0, mutant 1 (feef1a1)
  the divergence-figure enforcement  CONTROL FAILED  exit 1 before any mutation (4ad3095)
  mutation-lib's landing contract    NOT CAUGHT  control 0, mutant 0 (65b00d8)

band1-pair-mutations: 4 CAUGHT, 4 NOT CAUGHT, 0 no-apply/restore, 1 control-failed
```

**4 CAUGHT, 4 NOT CAUGHT, 1 CONTROL FAILED, out of 9 mechanisms mutated.** Six
of band 1's fifteen mechanisms were not mutated at all and are declared as such
below. So the honest count is: **of 9 band-1 mechanisms tested by mutation, 4
are guarded, 4 are not, and 1 could not be judged.**

### THE ONE THAT MATTERS: `C22c` HAS TWO COPIES AND THE ORACLE CHECKS THE OTHER ONE

The owner called `C22c` *"the strongest result in this project"*. Mutating
`3.3599e-3` to `3.3700e-3` in `entropy_floor.py` leaves `oracle-selftest`
**passing**. The mechanism, located:

- `entropy_floor.py:188` holds `C22C_FAMILIES_BY_N`, and
  `C22C_BY_N = tuple((n0, max(f.values())) for n0, f in C22C_FAMILIES_BY_N)`
  makes `3.3599e-3` the term **the published floor actually subtracts** for any
  report with n >= 1,000,000. The constant is **live**, not dead code.
- `compression_ceiling_exact.py:215` holds **its own separate copy**,
  `SCAN = {10 ** 6: "3.3599e-3", 8 * 10 ** 6: "2.1644e-3"}`, kept as strings
  because their precision is part of the claim — and it verifies **that** copy
  against the standard's own worked example.

**So the independent verification is real, correct, validated against NIST's
published example, and it verifies a different copy of the number than the one
the floor uses.** Two copies, one checked. `OC-86` established that `C22c`
agrees with an exact computation; it did not establish that the agreement is
*enforced* on the consumer, and nothing has since.

This is the same shape as `F02`/`WV-2`, where a verification was found to rest
on a different thing than the figure it was cited for — and it is the third
time in this campaign that an instrument has been found to check its own copy
of a value rather than the one in use.

**Not repaired in this pass**, because measurement and repair are separate
passes and the owner's list ends at item 5. **Recorded as the top of the queue:**
the two copies must be wired together — the oracle should read
`entropy_floor.py`'s table, or the table should be derived from the oracle —
and until they are, `C22c`'s agreement is a statement about
`compression_ceiling_exact.py`, not about the floor.

### `OC-67`'s per-family denominator: the same shape

`'collision': 7.84e-4 -> 7.90e-4` is likewise not caught. It is a non-binding
family member at these n (compression binds), so the *floor* does not move —
but that is an argument about this input, not a guard, and the entry that
introduced the family table was justified by `SHAPE-07` precisely so that the
non-binding members would be visible rather than hidden.

### `mutation-lib`'s landing contract has no negative control of its own

Renaming `MUTATION-DID-NOT-APPLY` is not caught by
`harness-inventory-mutation-test.sh`, because every mutation that harness
performs **does** apply. So the mechanism adopted to stop the project reporting
unearned verdicts — the third outcome itself — is the one mechanism with no case
in which it fires. `OC-98` measured a false negative in the dead-guard detector
by planting one of each class; the same treatment is owed here and is queued.

### The `CONTROL FAILED` arm was caused by this very campaign

`regression-docs.sh` exited 1 **before** any mutation. Diagnosed: the
instrument inventory's stated live count said **74** while the enumerator said
**76**, because `OC-104` added `regression-option-order.sh` and this entry added
`band1-pair-mutations.sh` and neither updated `audits/INSTRUMENT-INVENTORY.md`.
**The enforcement `OC-91` added worked exactly as designed, and caught its
author.** Fixed to `**76** at `36cafb3``, and the arm is re-run below.

### The six band-1 mechanisms NOT mutated, declared

`5074fff` and `7a0be01` (`C23`), `210aed6` (the atomic report write), `8ff739d`,
`9aa991d` and `b12247c` (the three canary entries), and `5c3353f` (two
instrument rules — **no runnable case exists**, as `OC-100` already declared).
The canary trio needs a four-build setup and `C23`/`210aed6` need a rebuild per
mutation; they are queued, not claimed. **Counts in this entry are therefore a
floor on the unguarded mechanisms, not a total.**

### What this does NOT establish

- **9 of 15 mechanisms mutated, one mutation each.** A mechanism that catches
  one break can miss another.
- **Band 2's 39 pairs are untouched**, as in `OC-100`.
- A `NOT CAUGHT` result says **no case in the suite notices this change**. It
  does not say the value is wrong — all four mutated values are believed
  correct, and three of the four were independently computed.
- Nothing reported upstream.

## OC-106 — the dead-guard work closed out: 0 verifications withdrawn, and the register's own rule was not enforced on its new entries

**Owner's item 5, in three parts.**

### Part 1 — the six frozen class-1 flags: the figures named, and NOTHING withdrawn

The owner asked for these to be recorded as **withdrawn** verifications, on the
reasoning that freezing a script does not retire the figures it produced. The
measurement in `OC-98` says otherwise, and recording a withdrawal that did not
happen would be recording something false. So each is recorded in
`audits/WITHDRAWN-VERIFICATIONS.md` with all five fields, under the branch the
owner's own instruction provides — *"if a figure has independent support, name
it and close as superseded instead"*.

| entry | flag | figures it guarded | outcome |
|---|---|---|---|
| `SV-1` | `issue272/repro.sh:11,:15,:18` | upstream #272's mutant-survival figures: dropping `n x H_bitstring` and dropping `H_original` each leave `Assessed min entropy` unchanged on four reference files | **SUPERSEDED** — the transcript is the witness, **and** the same conclusion is independently supported by the aggregation-blind-spot measurement (a 40-sigma defect leaves the figure unchanged because Compression binds), reached by a different route |
| `SV-2` | `widths.sh:6,:13,:14` | the literal-vs-bitstring agreement for widths 2–8 against the C++ literal reference | **SUPERSEDED on its transcript ALONE** — no other instrument in this repository recomputes these, which is weaker than `SV-1` and is recorded as such |
| `SV-3` | `repairs/2026-10-09-ind-02/rerun.sh:45` | `ind-02`'s report-shape claims: `errorLevel 2`, `IID false`, `assessmentComplete true`, no `hAssessed` | **VERIFICATION STANDS** — `set -e` is active at that line, and the detector's own `has_set_e` field said so |
| `SV-4` | `audits/2026-10-09-independent-audit/rerun.sh:71` | the TruePad unattested-tools count | **VERIFICATION STANDS** — the next line captures `$?` to a file the audit reads; the matcher's `STATUSREAD` does not recognise that form |
| `SV-5` | `windows-facts.sh:719` and `:732` | the Windows tally behind **`C18` CONFIRMED** and **`C24` NEW** | **VERIFICATION STANDS** — `$V`'s existence and non-emptiness are preconditions checked at `:703`, and `OC-98` exercised three paths |

**6 flagged lines, 5 register entries, 0 verifications withdrawn, 2 superseded
(one with a second independent support, one on its transcript alone), 3 entries
where the verification stands.**

### AND THE REGISTER'S OWN RULE WAS NOT BEING ENFORCED ON THEM

`regression-docs.sh` checks that every register entry carries its five fields.
It split on `^## (WV-\d+)`, so **six entries added to satisfy that rule sat
outside the rule's enforcement**. Extended to both prefixes, with the second
field being `WITHDRAWN` for a `WV-` entry and `SUPERSEDED` for an `SV-` one.

**It immediately caught a real gap of mine:** `SV-5` and `SV-6` had been written
as two consecutive headings sharing one field block, so `SV-5` had no fields of
its own. They are one verification over two flagged lines and are now one entry.
The check went from **2 entries** to **7**.

### Part 2 — the three class-A determinations, re-established by breaking

Already done by mutation in `OC-98`, with the mutation text recorded there:
`regression-input-identity.sh` (`if(!sha256.empty())` -> `if(false)`),
`sanitizer-restart-c01.sh` (`h_i = H_I` -> `2.0 * H_I` at both sites, rebuilt,
reached via `EA_RESTART_SANITIZER_BIN`), and `verify-fixture-inventory.sh`
(three separate mutations: a manifest line removed, an unlisted `sneaked.bin`
added, one fixture's first byte changed). **Three confirmed false positives,
none confirmed-broken, none unmutable** — control exit 0 and PASS, mutant exit 1
with a distinct reason in every case, three distinct reasons for the third.
Those are results by mutation, not by inspection.

### Part 3 — the detector re-run after its own repair

```
provenance: fork @ master 8e6941f
flags: 67
by pattern: {'B': 21, 'C': 29, 'D': 14, 'A': 3}
files touched: 27
```
Baseline signatures: **39**.

**No change** — not in the flag count, not in the pattern mix, not in the group
assignment, and not in the 68 -> 67 deduplication. `OC-98` predicted this: the
`has_pipefail` fix's reach in this tree is zero files, because the one file that
mentions `pipefail` also sets it. The prediction is now a measurement.

**And a dead-guard shape in the detector's own reporting, found while doing
this.** Run with `SP=.` — a plausible invocation — it prints

```
provenance: fork @ COMMIT-UNESTABLISHED (tree sha256 e3b0c44298fc1c14)
flags: 0
files touched: 0
```

`e3b0c442...` is the SHA-256 of the **empty string**: it scanned nothing and
reported `flags: 0`. That is `SHAPE-03` verbatim in the instrument built to find
`SHAPE-03`. `regression-deadguard.sh` is immune because `OC-95` made the
provenance line a **precondition** — which is the one reason the suite cannot
be fooled by it — but a human running the detector by hand can be, and
`flags: 0` from an empty scan is the most reassuring possible wrong answer.
**Queued, not repaired:** `deadguard.py` should refuse a scan that found no
files, rather than reporting zero flags over zero files.

### What this does NOT establish

- `SV-2`'s figures rest on **one** support, a recorded transcript nobody re-reads.
- The `67` is a **floor**, as `OC-98` established: a measured 16% false-positive
  rate, a demonstrated false negative, and four patterns that do not claim to
  cover every shape.
- Nothing reported upstream.

## OC-108 — the Rust implementation's divergence list, checked item by item against this fork: the first external corroboration this repository has had

**New-task item 3. Two independent SP 800-90B implementations were cloned as
comparison oracles — `walters-labs/sp-800-90b` at `ef6fd02` (Rust, MPFR) and
`EPI-Quantum-Crypto/libsp80090b` at `2429253` (C99 port of NIST 1.1.8). Neither
is vendored; both are built and run as separate binaries, so no license
question arises. The Rust project documents the places where it intentionally
differs from NIST's reference implementation. Each is checked here against this
fork's own source and record.**

Note on `MPFR`: the Rust implementation links `MPFR` through `rug`. This fork
**deliberately avoids `MPFR`/`GMP`** for LGPL isolation, and `regression-docs.sh`
asserts that no built program links them. Running the Rust tool as a **separate
binary** leaves that property untouched, and it is the only reason this
comparison is possible at all without changing what this fork links.

### 1. The MCV confidence constant — **EXHIBITS IT, AND ALREADY FOUND HERE**

Their statement: NIST's MCV uses the binary64 constant `2.5758293035489008`
where the publication prints decimal `2.576`, and *"the two intentionally
produce different results."*

This fork: `cpp/shared/utils.h:75` defines
`#define ZALPHA 2.5758293035489008` — **the identical value** — and
`:76` `ZALPHA_L 2.575829303548900384158L`. Used by `most_common.h:30`,
`utils.h:1229` and four sites in `lrs_test.h`.

**Found here independently, twice over.** `OC-8` measured it on real values
harvested from a real run and reported the magnitudes rather than an adjective:

| predictor | tool `ZALPHA` | spec `2.576` | delta |
|---|---|---|---|
| Bitstring MultiMCW | 0.99911507785502614 | 0.99911499084098192 | **+8.70e-08** bit |
| Literal MultiMCW | 7.9611632356166352 | 7.9611594334062937 | **+3.80e-06** bit |
| Bitstring Lag | 0.998936306150716 | 0.99893621914778806 | **+8.70e-08** bit |

and `entropy_floor.py:469` carries it as a standing floor term,
`C22c ZALPHA vs the literal 2.576 ... DERIVED`.

**This fork went further than their note in two ways**, and both matter: it
determined the **direction** (permissive — the tool's constant yields the higher
estimate) and it determined **which constant is correct** — `2.576` is a
*rounded printing* of the true 0.995 quantile, so the tool uses the right number
and the standard's text uses the rounding. Dispositioned **NOT-A-BUG** on that
reasoning (prior `F07`, restated by `predictors-6`).

**And their default agrees with that conclusion:**
`ConfidenceConstant::NistReference` is the Rust default, with `Publication`
offered as an option. So this is **corroboration of the mechanism and agreement
on the resolution**, from a project that reached it independently.

### 2. The Collision estimator's boundary policy below 2 — **EXHIBITS IT; NEW HERE AS A CHARACTERIZATION; and it is NOT R-1**

Their statement: the implementation *"clamps the adjusted mean to at least 2 and
solves `E[T] = 2 + 2p(1-p)` directly. A bound of 2 gives zero entropy; a bound
at or above 2.5 gives one bit per sample. **This differs from applying the
publication's no-solution fallback to a bound below 2.**"*

This fork: `cpp/non_iid/collision_test.h:69`

```c
	X -= ZALPHA * s/sqrt(v);
	//2 is the smallest meaninful value here.
	if(X < 2.0) X = 2.0;
```
then `if(X < 2.5) { p = 0.5 + sqrt(1.25 - 0.5 * X); ... } else { p = 0.5; entEst = 1.0; }`.

**The direction, worked out here because it decides whether this matters.** The
solvable window is `X` in `[2, 2.5]`, giving entropy in `[0, 1]`:

- **NIST's clamp:** `X < 2` becomes `X = 2`, so `p = 0.5 + sqrt(0.25) = 1.0` and
  `entEst = -log2(1.0) = ` **0 bits**.
- **The publication's no-solution fallback:** `p = 0.5`, `entEst = ` **1 bit**.

**So the clamp is the CONSERVATIVE branch** — it awards zero entropy where the
publication's fallback would award a full bit. For an entropy *claim*, lower is
safe. That is the opposite of the usual finding in this record and it is why
this one is recorded without alarm.

**It is NOT the same issue as `R-1`.** `R-1` is the
`assert(p_col >= 1/k)` / `p_colPower` underflow **abort** in `lrs_test.h` on
80-bit `long double` — a crash on compliant data, five independent finders, 155
of 255 alphabet sizes on x86-64. Different file, different quantity, different
failure mode. **Nor is it the `C22` floor**, which is `P_local`'s bisection
quantisation. The only thing the three share is the word "clamp".

**New here as a characterization.** The 2026-09-30 audit verified §6.3.2's
arithmetic against a literal implementation and this fork's own comment block
documents the `v < 2` NaN path (upstream #264). Neither records that the clamp
**diverges from the publication's fallback**. Recorded now, with the direction.

### 3. MultiMMC's `longest_correct_run` quirk — **EXHIBITS IT, ALREADY REPAIRED HERE, AND THE TWO PROJECTS WENT OPPOSITE WAYS**

Their statement: *"This implementation deliberately preserves a reference-code
quirk: an unavailable winning prediction leaves the run counter unchanged, while
an incorrect available prediction resets it."*

**This fork found the same quirk and REPAIRED it, as `F09`.**
`cpp/non_iid/multi_mmc_test.h:67`:

```c
      // See the generic path below: SP 800-90B 6.3.9 leaves correct[i-2] at 0
      // for a Null prediction, so a Null from the winner ends the run. The
      // run counter was only reset where the winner predicted and was wrong.
```

guarded by `cpp/selftest/regression-multimmc.sh`, whose header cites §6.3.9
step 1 and step 4.d and **the worked example in that section**, which shows
`prediction = Null, correct = 0` for its first two rounds.

**So: independent corroboration that the quirk is real, and a genuine
divergence in what to do about it.** The Rust project preserves it for
reference compatibility; this fork follows the publication's own worked example.
Neither is a bug in the other — it is a documented, deliberate difference on
both sides, which is the most useful possible outcome of this comparison.

This fork also recorded the direction: *"an inflated r makes `P_local` larger
and the estimate smaller, so the defect was conservative"* — i.e. upstream's
quirk is permissive in the counter and conservative in the figure.

### 4. LRS's negative sentinel — **EXHIBITS IT, AND ALREADY FOUND HERE**

Their statement: *"An empty range returns `NoRepeatedSubstringRange` instead of
NIST's negative sentinel."*

This fork: `cpp/shared/lrs_test.h` sets `t_tuple_res = -1.0` and
`lrs_res = -1.0` (`:157`, `:158`, `:271`) and `Pmax = -1.0` (`:241`).

**Found here as `R-2`** — `cpp/selftest/regression-restart.sh:270` asserts
*"the `-1` sentinel is not folded in"*, i.e. that a sentinel never reaches the
minimum as if it were an entropy value. **Corroborated**; the two projects chose
different remedies (a typed error vs a guard against folding it in).

### 5. The Markov six-pattern table — **EXHIBITS IT; NEW HERE AS A CHARACTERIZATION**

Their statement: *"This follows NIST's six-pattern table, not a general
optimization over all 128-bit Markov paths. The two calculations can differ on
some inputs."*

This fork: `cpp/non_iid/markov_test.h` evaluates exactly six candidates in the
specification's order —
`-log2(P_0) - 127*log2(P_00)`, `-log2(P_0) - 64*log2(P_01) - 63*log2(P_10)`,
`-log2(P_0) - log2(P_01) - 126*log2(P_11)`, and the three with `P_1` leading —
then `entEst = fmin(H_min/128.0, 1.0)`. **Verbatim the structure they describe.**

The 2026-09-30 audit recorded `| 6.3.3 | Markov | 6 paths, min/128 | yes |` with
the no-path case noted, i.e. it verified the six paths **as conformant to the
standard**, which they are. **What is new here is the limitation**: six
prescribed patterns are not the minimum over all 128-step paths, so the
published "Markov min-entropy" can exceed the true minimum over that model.
That is a **standard** defect, section B territory, not an implementation one.

**Probably immaterial to any figure in this record**, and the reason is already
measured: Compression binds on every stream this project has assessed, and the
aggregation measurement found that a 40-sigma defect in a non-binding estimator
leaves the min-entropy figure unchanged. Recorded as a characterization, with
that caveat stated rather than assumed.

### 6. The restart API after an IID rejection — **EXHIBITS IT, ALREADY REPAIRED HERE**

Their statement: *"sanity failure short-circuits; IID rejection and incomplete
estimation prevent a validated output. **The reference can reach its final
validation-success message after printing IID failures.**"*

**This fork closed exactly that.** `cpp/restart_main.cpp`:

```
:1139  "** Skipped IID permutation tests after an earlier required IID test failure"
:1155  "IID restart test suite failed; no IID restart entropy estimate was awarded."
```

so an IID failure short-circuits the permutation tests and **no IID restart
estimate is awarded**. In the `C03` neighbourhood (`OC-6`). **Corroborated, and
already fixed here.**

### 7. Out-of-width values: rejected, not masked — **AGREES WITH THIS FORK'S CHOICE**

Their statement: *"out-of-width values are rejected rather than masked."* This
fork refuses too — measured: `ea_non_iid -o r in.bin 1` on byte-valued data
prints *"Incorrect bit width specification: Data (8) does not fit within
described bit width: 1"* and exits 255. **Same choice, independently.**

### The tally, with the identity of what it counts

**7 items from their list checked against this fork's source and record:**

| outcome | count | items |
|---|---:|---|
| exhibits it, **already found here** under another name | **4** | MCV constant (`C22`/`OC-8`/`C22c`), LRS sentinel (`R-2`), MultiMMC quirk (`F09`, **repaired**), restart-after-IID (**repaired**, `C03` neighbourhood) |
| exhibits it, **new here as a characterization** | **2** | the Collision `X < 2` clamp vs the publication's fallback; the Markov six-pattern limitation |
| **agrees** with a choice this fork already made | **1** | out-of-width rejected rather than masked |
| exhibits it and is a **defect in this fork** | **0** | — |

**This is the first external support any finding in this repository has had.**
Four findings in this record were reached independently by a different team in a
different language, and on the two where this fork took a position — the MCV
constant's correctness and MultiMMC's run counter — the positions are
reasoned from the publication on both sides and differ only on MultiMMC, where
the disagreement is documented as deliberate by both projects.

### What this does NOT establish

- **Their list is their list.** Seven items are checked; their "Intentional
  compatibility differences" section also covers arithmetic precision, seeding,
  permutation minimums and conditioning, which bear on quantities this fork does
  not publish.
- **Nothing is validated by agreement with them.** Two implementations agreeing
  that NIST's code does X is evidence that it does X. It is not evidence that X
  is right.
- The Collision and Markov characterizations are **determinations by reading the
  code and the standard**, labelled as such — not measurements. The Collision
  direction (0 bits vs 1 bit) is arithmetic on the published formula, not a run.
- **Nothing reported upstream, to NIST or to either project.**

## OC-109 — the defect datasets: saturation, drift and replay are CAUGHT; a zero-entropy DRBG is awarded 7.14 of 8 bits

**New-task item 4. The C99 project's `lab/gen_data.sh` generates datasets
spanning good sources and specific defects. This fork's outside-battery corpus
is 31 streams in four families — and the brief's *"no defect classes at all"*
is **not right**, as `OC-114` measures: 5 of them are injected-signal defects
and 1 is a deliberate blind-spot case. What **is** right, and is the point, is
that **none** of saturation, drift, replay, warm-up, fading or DRBG output
appears in it. The corpus exercises the outside battery's detector; it does not
exercise the source model. And January is about a real hardware source. 22 of the 24 were generated at 1,000,000 samples with `--seed 20261025`
into a directory outside this repository. **Not added to any pinned corpus or
fixture manifest**: they are generated, not captured, and their provenance is a
script.**

**The two NOT generated stay NOT RUN:** `jent-raw` and `jent-restart` require
`JENT_SRC` (a jitterentropy-library checkout), which is absent. A physical
dependency that is not present is a third outcome, not a pass.

**And their generator does not run under macOS `/bin/sh`.** It sets
`GROUPS=...`, and in `bash` — which is what `/bin/sh` is on macOS — `GROUPS` is
a **special read-only variable**, so the assignment is ignored, `set -e` sees a
failure, and the script exits silently: `--list` exited 1 printing nothing, and
a generate request exited 0 having written no file. Measured:
`bash -c 'GROUPS="a b c"; echo $GROUPS'` prints **`20`**, the real group id. Run
under `dash` it works. A portability defect in their script, recorded here
because it is the reason the datasets exist at all; **not reported to them.**

### The raw datasets, 18 of them, at their declared widths

`ea_non_iid -i -a -v -v <file> <width>`. "Caught" means the assessed figure is
driven well below the width, or the run is refused.

| dataset | w | what it simulates | assessed min entropy | caught? |
|---|--:|---|---:|---|
| `thermal` | 8 | good raw source, IID | 4.0948 | — (good source) |
| `thermal-lsb` | 1 | LSB of the same ADC | 0.8384 | — (good) |
| `ringosc-slow` | 1 | ring osc sampled slowly | 0.8591 | — (good) |
| `saturated` | 8 | ADC gain too high, clipped to 0/255 | **1.7249** | **YES** |
| `lowpass` | 8 | sampled faster than the noise bandwidth | 3.2476 | YES |
| `ringosc-fast` | 1 | sampled too fast, long runs | **0.1097** | **YES** |
| `biased-1bit` | 1 | comparator offset, P(1) = 1/4 | **0.2498** | **YES, conservatively** |
| `interference` | 8 | mains tone over weak noise | 3.4375 | YES |
| `aging` | 8 | noise fades over the file | 3.3017 | YES |
| `warmup` | 8 | source not settled at start | **1.1043** | **YES** |
| `drift` | 8 | law changes halfway (4 bits, then 8) | **2.4416** | **YES** |
| `stuck` | 8 | dead source, one symbol | **exit 255, REFUSED** | **YES** |
| `replay` | 8 | one 4 KiB block repeated | **1.594e-06** | **YES, ~zero** |
| `urandom` | 8 | kernel DRBG output | 7.1725 | **NO** |
| `urandom-4bit` | 4 | same, folded | 3.6878 | **NO** |
| `urandom-1bit` | 1 | same, folded | 0.8311 | **NO** |
| `openssl` | 8 | OpenSSL DRBG output | 6.6384 | **NO** |
| `drbg-zero-seed` | 8 | **AES-256-CTR, all-zero key: ZERO entropy** | **7.1450** | **NO** |

**The three the owner named are all caught.** A **saturated** source loses
6.3 of 8 bits; a **drifting** source loses 5.6 of 8; a **replayed** source is
driven to **1.6e-06 bits**, which is as close to a refusal as a number gets.
`stuck` is refused outright.

**`biased-1bit` is conservative in the safe direction.** An IID source with
P(1) = 1/4 has true min-entropy `-log2(0.75) = 0.4150` bit; the fork reports
**0.2498**, an *underestimate*. Lower is safe for a claim.

### THE ONE THAT IS NOT CAUGHT, AND IT IS THE SHARPEST RESULT HERE

**`drbg-zero-seed` is AES-256-CTR keyed with all zeros. Its entropy is exactly
zero — the stream is a deterministic function of nothing. This fork assesses it
at 7.1450 bits per 8-bit symbol and exits 0.**

This is **not a defect in this fork**, and saying so precisely matters: SP 800-90B
measures *statistical structure*, not *computational unpredictability*, and no
estimator in §6.3 could distinguish AES-CTR output from noise without breaking
AES. It is exactly why the standard says raw, unconditioned samples must be
assessed and why their own table annotates this row *"passes every test, zero
entropy"*. **The value of having the number is that the failure mode is now
quantified rather than known in principle:** the tool will certify a
zero-entropy stream at 89% of full entropy, silently, with `errorLevel 0`.

**For January this is the ranking fact.** The battery catches the defects a
hardware source actually develops — saturation, drift, replay, warm-up, fading,
correlation, periodic interference, a stuck output. What it cannot catch is a
source that is *not raw noise at all*, and the only defence against that is
provenance: knowing the bytes came from the physical source before any
conditioning. No amount of estimator agreement substitutes for it, and three
independent implementations agreeing on 7.145 bits for an all-zero-key AES
stream is the proof.

### The four restart datasets, which match their table exactly

`ea_restart -i -v <file> 8 <H_I>/symbol`. **The `/symbol` suffix is required** —
this fork's `C16` repair refuses a bare `H_I` above width 1, which my first
invocation tripped.

| dataset | `H_I` | exit | `H_r` | `H_c` | result | their expectation |
|---|---|--:|---|---|---|---|
| `restart-thermal` | 4.0 | **0** | 5.6097 | 5.6097 | **Validation Test Passed** | "passes the restart test" ✓ |
| `restart-warmup` | 1.0 | 255 | — | — | **Sanity Check Failed** | "fails" ✓ |
| `restart-urandom` | 7.0 | **0** | 7.8713 | 7.8713 | **Validation Test Passed** | "fresh bytes at every restart" ✓ |
| `restart-frozen` | 1.0 | 255 | — | — | **Sanity Check Failed** | "fails" ✓ |

**All four agree with what their table says should happen** — independent
corroboration that this fork's restart path, including the `C16`, `C23` and
`A07` repairs, behaves correctly on datasets a different team designed to
exercise those exact failure modes.

**And a characterization, not a bug, recorded because it nearly became one.**
`restart-thermal` at my first arbitrary `H_I = 7.0/symbol` FAILED the sanity
check. That is correct behaviour: `thermal.bin` assesses at 4.0948 bits, so
`H_I = 7.0` is a false claim and §3.1.4.3 exists to refuse it. Re-run at a
source-matched `H_I` it passes. **A disagreement is characterized before it is
called anyone's bug** — including when the bug would have been mine.

### What this does NOT establish

- **22 of 24 datasets, one seed, one generator.** Their published
  `lab/data.sha256` digests are not reproduced here: the files were generated
  with Homebrew `gawk` under `dash`, and byte-identity with their published set
  was not checked, so these are datasets of the same *classes*, not the same
  *bytes*.
- **"Caught" is a judgement about the figure's magnitude**, not a threshold test.
  This fork has no pass/fail threshold for a raw assessment; the operator
  compares the figure against a requirement.
- The restart rows use an `H_I` **I chose** from the matching raw assessment.
  A different `H_I` moves the verdict, as the `restart-thermal` row shows.
- Nothing is added to any pinned corpus, manifest, or baseline.
- Nothing reported upstream, to NIST or to either project.

## OC-110 — the three-way differential: 891 values, three independent implementations, 0 disagreements beyond 1e-9

**New-task item 2, and the owner is right that this is the strongest statement
this project can make about any figure. Three implementations, written
independently in three languages, over NIST's own 11 reference datasets.**

| implementation | identity | build |
|---|---|---|
| this fork | `ea_non_iid 1.1.8`, Darwin arm64 | Apple clang, `-O2 -ffloat-store` |
| C99 port | `EPI-Quantum-Crypto/libsp80090b` @ `2429253` | `gcc-16 -std=c99 -O2 -fopenmp -ffloat-store -ffp-contract=fast`, `MARCH=` (portable) |
| Rust | `walters-labs/sp-800-90b` @ `ef6fd02`, v0.1.1 | `cargo 1.98.0 --release`, 256-bit MPFR via `rug` |

Neither oracle is vendored. Both were cloned into their own directories outside
this repository and are run as **separate binaries**. The Rust implementation
links `MPFR`, which this fork deliberately **does not** — `regression-docs.sh`
asserts no built program links `MPFR`/`GMP` — so running it out of process is
the only way this comparison is possible without changing what this fork links.

### THE COMPARISON HAD TO BE MADE COMPARABLE FIRST, AND THAT IS WHERE IT COULD HAVE GONE WRONG

NIST and the C99 port print `Literal Most Common Value Estimate: min entropy =
<v>`. The Rust implementation prints `Literal MostCommonValue: <v>`. Keyed on
the raw label, **every row would have read `ONLY-1` and the summary would have
reported perfect agreement over zero three-way comparisons** — `SHAPE-03` with
extra steps, and it would have looked like the strongest result in the project.

Measured before and after widening: with the fork's own line filter the Rust
column was **entirely empty**. The canonical key is
`(Literal|Bitstring, estimator) min-entropy`, and only min-entropy rows are
canonicalised because min entropy is the only per-estimator quantity all three
expose. The extraction otherwise **mirrors `cpp/selftest/compareresults.pl`
exactly** — the same line filter, the same two separator forms, the same
trailing-space strip — so a disagreement cannot be an artefact of a different
parser. Comparison uses the full 77-digit MPFR strings; only the display is
shortened.

### THE RESULT

```
rows with ALL THREE implementations: 163
rows with exactly two:               728
total:                               891

labels exceeding 1e-09:                0
```

**891 value-rows compared across the 11 datasets. Every one agrees to 1e-9.
Zero disagreements.**

| | three-way (163 rows) | fork vs C99 (728 rows) |
|---|---:|---:|
| agree **exactly** | **64** | **719** |
| exceed 1e-12 | 9 | 5 |
| **worst delta** | **3.659e-10** | **1.266e-10** |

The 728 two-way rows are the intermediate diagnostics — `Mode count`, `p-hat`,
`p_u`, `X-bar`, `sigma-hat`, `P_0`, `P_{0,0}`, `P_local`, `v`, `Sum t_i` — which
the Rust CLI keeps API-only. **719 of those 728 are bit-identical between this
fork and an independently written C99 port.**

### THE WORST THREE-WAY ROWS ARE EXACTLY THE DOCUMENTED PLATFORM DELTAS

| dataset | row | three-way delta |
|---|---|---:|
| `biased-random-bytes.bin` | Bitstring MultiMMC min-entropy | **3.659e-10** |
| `ringOsc-nist.bin` | Literal MultiMCW min-entropy | 3.206e-10 |
| `biased-random-bytes.bin` | Literal Lag min-entropy | 3.149e-10 |
| `biased-random-bytes.bin` | Bitstring LZ78Y min-entropy | 1.881e-10 |
| `biased-random-bytes.bin` | Bitstring MultiMCW min-entropy | 1.858e-10 |

Compare `cpp/selftest/known-platform-deltas.txt`, which lists
`biased-random-bytes.bin|Bitstring MultiMMC Prediction Estimate|min entropy|1e-9|`
**`3.65934130219792e-10`**. **The same row, the same magnitude, to every digit
printed.** Every one of the five is a prediction estimator, and the prediction
estimators are precisely the eight rows that manifest lists.

### WHICH IS THE OUTLIER, AND THE HONEST ANSWER

**None of the three is an outlier anywhere.** No row exceeded the tolerance, so
the outlier column is empty by construction, and the owner's instruction — *"where
this fork is the outlier, that is a candidate defect in this fork"* — finds
nothing to act on.

**And a limit on what the agreement separates.** All three implementations ran
on the **same machine**, Darwin arm64. So this measurement does **not**
distinguish *"these differences are platform-dependent"* from *"these
differences are implementation-dependent"*: it establishes that three
independent implementations on one platform spread by at most 3.66e-10,
concentrated in exactly the quantities the platform manifest names. That is
consistent with the platform explanation and does not prove it. Proving it needs
the same three implementations on x86-64, which is **NOT RUN**.

**One characterization, not a contradiction.** The C99 project claims a
`7.2e-14` maximum gap on non-IID against NIST. Measured here, fork versus C99,
the worst gap is **1.266e-10** — larger. The builds differ: this was `gcc-16`
with `MARCH=` (their Makefile warns that a portable build "may then differ from
a `-march=native` NIST build") on Darwin arm64, against Apple clang. Their claim
is presumably an x86-64 figure. **Different platform, different compiler,
different flags — so this is a different measurement, not a refutation.**

### What this establishes, stated plainly

**Across the ten non-IID estimators, both the literal and bitstring paths, and
all 11 of NIST's reference datasets, this fork's figures agree with two
independently written implementations to better than 4e-10 everywhere, and
exactly on 64 of 163 three-way rows and 719 of 728 two-way rows.** For the
figures this project actually publishes, that is worth more than any
self-authored test in this repository, and it is the first time any figure here
has had support that does not originate with its author.

### What this does NOT establish

- **It is agreement, not correctness.** Three implementations of the same
  standard agreeing says they implement the same standard. Where the standard
  itself is wrong — section B of the divergence document — all three are wrong
  together. `OC-108`'s Markov six-pattern item is exactly such a case.
- **One platform.** See above; the x86-64 three-way is NOT RUN.
- **`ea_non_iid` only.** The IID, restart and conditioning paths were not
  compared three ways; `OC-109` compares the restart path against the C99
  project's *expectations*, not against its figures.
- The Rust implementation's per-estimator figures come from its
  `examples/non_iid` binary, which the project's own docs warn is "not an
  IID/restart/source-validation tool" and whose exit status must not be read as
  an assessment verdict. Only its printed figures are used here.
- **Nothing reported upstream, to NIST or to either project.**

## OC-111 — the three-way differential on DEGENERATE inputs: 10 disagreements in 503, all smaller than the floor's own quantisation term

**`OC-110` found zero disagreements over NIST's eleven reference datasets, all
of which are reasonable sources. The defect datasets of `OC-109` are
deliberately degenerate — clipped, drifting, replayed, unsettled — and that is
where three implementations should be expected to part company. Five of them
were run three ways.**

```
labels compared across >=2 implementations: 503
labels where every implementation agrees to 1e-09: 493
labels exceeding 1e-09:                             10
```

### The disagreement list, with the outlier named

| dataset | row | delta | outlier | fork | c99 | rust |
|---|---|---:|---|---|---|---|
| `saturated` | Bitstring MultiMCW `P_local` | 1.265e-09 | *(two-way)* | 0.7916290836 | 0.791629082335 | — |
| `saturated` | Bitstring MultiMCW min-entropy | 2.305e-09 | **fork** | 0.337103478467 | 0.337103480772 | 0.337103480615 |
| `saturated` | Bitstring Lag `P_local` | 1.524e-09 | *(two-way)* | 0.79162900416 | 0.791629002636 | — |
| `saturated` | Bitstring Lag min-entropy | 2.778e-09 | **fork** | 0.33710362324 | 0.337103626018 | 0.337103625445 |
| `saturated` | Bitstring LZ78Y min-entropy | 2.025e-09 | rust | 0.337103586045 | 0.337103586045 | 0.33710358807 |
| `drift` | Literal MultiMMC min-entropy | 4.066e-09 | rust | 3.77987410628 | 3.77987410628 | 3.77987411034 |
| `drift` | Literal LZ78Y min-entropy | 4.165e-09 | rust | 3.77987097957 | 3.77987097957 | 3.77987098373 |
| `drift` | `H_original` / Literal minimum | 4.165e-09 | rust | 3.77987097957 | 3.77987097957 | 3.77987098373 |
| `replay` | Literal LZ78Y min-entropy | 1.954e-09 | rust | 2.18413376771 | 2.18413376771 | 2.18413376966 |
| `warmup` | Literal MultiMCW min-entropy | 2.249e-09 | rust | 1.62517503233 | 1.62517503233 | 1.62517503458 |

**Characterized before being called anyone's bug, in three groups.**

**(a) Six rows where `rust` is the outlier and fork and C99 agree EXACTLY.**
This is 256-bit MPFR against binary64, and the Rust project documents it:
*"High-precision arithmetic also means the default need not be bit-for-bit
identical to NIST's binary64 operations."* Two independent binary64
implementations landing on the same bits while the high-precision one differs
by 2e-09 is the expected signature, not a defect in anyone.

**(b) Two rows where THIS FORK is the outlier** — `saturated`, Bitstring
MultiMCW and Bitstring Lag min-entropy. Per the owner's rule these are
candidate defects in this fork and are investigated rather than explained away.
What the investigation finds:

- Both sit **immediately downstream of a `P_local` row that also disagrees**
  (1.265e-09 and 1.524e-09, fork versus C99), so the min-entropy difference is
  inherited, not independently generated.
- Both are **Bitstring prediction estimators**, and `P_local` is the quantity
  computed by **bisection**.
- That is **exactly the family and exactly the quantity** that
  `known-platform-deltas.txt` lists for Darwin arm64 — Bitstring MultiMCW
  `P_local`, Bitstring MultiMMC `P_local`, Bitstring Lag min entropy, Literal
  Lag `P_local`. Same estimators, same quantity, on a different input.
- The magnitude is an order larger here (2e-09 against 3e-10) and the input
  explains the direction: `saturated` is clipped to 0 and 255, so `P_local`
  sits at 0.79 with very long runs, which is where the bisection is most
  sensitive.

**So this fork is the outlier on two rows, in the one quantity it had already
identified as numerically fragile, on the most degenerate input in the set.**
It is a candidate defect and it stays open as one; what it is **not** is a new
mechanism.

**(c) Two `P_local` rows are two-way only**, because the Rust CLI keeps that
diagnostic API-only. Their outlier column is empty by construction, not by
agreement.

### AND EVERY ONE IS SMALLER THAN THE CORRECTION THE FLOOR ALREADY APPLIES

`C22a` is the floor's **MEASURED** `P_local` quantisation term, `8.08e-15 x (n+1)`:

| | value |
|---|---:|
| `C22a` at n = 1e6 bits | **8.080e-09** bit |
| `C22a` at n = 8e6 bits (an 8-bit source at 1e6 samples) | **6.464e-08** bit |
| worst three-way disagreement, NIST datasets (`OC-110`) | 3.659e-10 bit |
| **worst three-way disagreement, degenerate datasets** | **4.165e-09** bit |
| worst row where **this fork** is the outlier | 2.778e-09 bit |

**Every disagreement three independent implementations produce, on the most
degenerate inputs available, is smaller than the quantisation correction this
project already subtracts.** Two consequences, and they point in opposite
directions, so both are stated:

1. **The floor absorbs them.** No figure this project publishes moves, because
   `C22a` is subtracted before the floor is reported and it is larger than the
   spread.
2. **It is independent support for `C22a`'s ORDER OF MAGNITUDE, and nothing
   more.** A different team's implementation differs from this one by less than
   `C22a`, which is consistent with `C22a` being the right size. It does **not**
   make `C22a` a bound — `WV-2` withdrew that claim and it stays withdrawn.
   `C22a` remains **MEASURED, not PROVED**.

### What this does NOT establish

- **Five datasets, one width, one platform.** 17 of the 22 defect datasets were
  not run three ways, and the three-way on x86-64 is **NOT RUN**.
- The two rows where this fork is the outlier are **not diagnosed**, only
  located. Nothing here says which of the three is arithmetically closer to the
  §6.3.7 definition — that needs an independent high-precision computation of
  `P_local` on this input, which is **not done**.
- `fork == c99` **exactly** on 493 of 503 rows including every assessed figure,
  which is strong agreement between two binary64 implementations and says
  nothing about whether binary64 is adequate here.
- **Nothing reported upstream, to NIST or to either project.**

## OC-112 — an independent implementation reproduces 5 of this fork's 8 platform deltas BIT-IDENTICALLY, and the other 3 do not survive

**`OC-110` had to state a limit: all three implementations ran on one machine,
so the measurement could not separate *"these differences are
platform-dependent"* from *"these differences are implementation-dependent"*.
This separates them, and the answer is "mostly the platform, and not entirely".**

### The experiment

`known-platform-deltas.txt` excuses a failing `selftest` on Darwin arm64 for 8
named rows. Its premise is that those differences belong to the **platform** —
`-ffloat-store`, arm64 `long double`, instruction reassociation — and not to
this fork. That premise has never been tested against anything but this fork.

So the **independently written C99 port** was run against **NIST's own reference
outputs**, on Darwin arm64, using **this fork's own comparator**. The C99 tool
prints NIST's exact output format, including the two identity lines
`compareresults.pl` checks, so the comparator reads it with no adaptation — which
is also why no new parser can be blamed for the result.

- if the C99 port shows the **same** deltas, they belong to the **platform**, and
  the manifest records a property rather than excusing a defect;
- if the C99 port matches refdata where this fork does not, they belong to
  **this fork**, and the manifest has been excusing a defect.

```
C99 port vs NIST refdata on Darwin arm64: 11 run, 5 agreeing, 6 disagreeing
```

**And 4 of those 6 are not arithmetic.** They are key-set differences: the C99
port emits an `H_bitstring` line for 1-bit data where NIST's refdata has none —
`"No reference value for H_bitstring (output has it, reference does not): 1"`.
A reporting difference between that port and NIST, with max numeric deltas of
8.22e-12, 4.33e-15, 2.14e-14 and 5.31e-14. **The genuine numeric disagreements
are on `biased-random-bytes.bin` and `ringOsc-nist.bin` — the same two datasets
as this fork.**

### THE RESULT, ROW BY ROW

**Bit-identical to this fork's manifest — every printed digit (5 of 8):**

| dataset | row | field | delta |
|---|---|---|---|
| `biased-random-bytes` | Bitstring MultiMMC | `P_local` | `2.46381248736327e-10` |
| `biased-random-bytes` | Bitstring MultiMMC | min entropy | `3.65934130219792e-10` |
| `biased-random-bytes` | Bitstring Lag | min entropy | `1.33402060231713e-10` |
| `biased-random-bytes` | Literal Lag | `P_local` | `1.57978075066012e-10` |
| `biased-random-bytes` | Literal Lag | min entropy | `3.14868464634799e-10` |

**Same row, different magnitude (1):**

| dataset | row | fork | C99 |
|---|---|---|---|
| `ringOsc-nist` | Literal MultiMCW min entropy | `1.5468587521994e-10` | `3.20619142346601e-10` |

**In the manifest, NOT in the C99 run — the C99 port agrees with refdata where
this fork does not (2):**

| dataset | row | field | the fork's delta |
|---|---|---|---|
| `biased-random-bytes` | Bitstring MultiMCW | `P_local` | `1.25069510303888e-10` |
| `biased-random-bytes` | Bitstring MultiMCW | min entropy | `1.85757652315655e-10` |

**In the C99 run, NOT in the manifest — this fork agrees with refdata where the
C99 port does not (2):**

| dataset | row | field | the C99 delta |
|---|---|---|---|
| `biased-random-bytes` | Bitstring LZ78Y | min entropy | `1.2912356600614e-10` |
| `ringOsc-nist` | Literal MultiMCW | `P_local` | `1.8170209781232e-10` |

### WHAT THIS ESTABLISHES, AND WHAT IT COSTS THE MANIFEST

**Five of the eight rows are vindicated as a platform property, and the evidence
is as strong as this kind of evidence gets.** A C99 program written by a
different team, compiled by a different compiler (`gcc-16` versus Apple clang)
with a portable `MARCH=`, differs from NIST's published reference outputs by the
**same amount to every printed digit** on five rows. Agreement to 15 significant
figures on five independent quantities is not coincidence: it is the same
floating-point reassociation on the same hardware, reached through different
source code. For those five rows `known-platform-deltas.txt` records a property
of the platform, **not** a defect it excuses — which is exactly what the file has
always claimed and has never until now had evidence for.

**And the other three do not survive, which is the part that matters.** The
effect is **not purely** the platform:

- **2 rows the manifest lists, the C99 port does not exhibit.** Bitstring
  MultiMCW `P_local` and its min entropy. There, this fork differs from NIST and
  an independent implementation on the same machine does not. Those two rows are
  **a fork-specific observation**, and the manifest's blanket framing — *"a
  difference this manifest excuses cannot be dismissed as negligible"* — now has
  a sharper reading for them: they are not shown to be the platform's.
- **1 row differs in magnitude by a factor of 2.07.** `ringOsc-nist` Literal
  MultiMCW min entropy: `1.55e-10` here, `3.21e-10` there. Both drift, by
  different amounts, in the same quantity.
- **2 rows the C99 port exhibits that the manifest does not list**, where this
  fork matches refdata and the C99 port does not. Symmetry: each implementation
  has rows the other does not.

**Recorded, not repaired.** The manifest is unchanged by this entry: all 8 rows
remain within its 1e-9 tolerance and every figure this project publishes is
unmoved. What changes is what the file is **known** to be recording — **5 of 8
rows: a measured platform property, independently corroborated; 3 of 8 rows:
a fork-specific numerical difference of the same order, not corroborated.** The
file should say so, and that is queued.

**It also narrows `OC-111`.** The two rows where this fork was the outlier on
`saturated.bin` were Bitstring **MultiMCW** min-entropy and Bitstring **Lag**
min-entropy. Bitstring MultiMCW is one of the two rows the C99 port does **not**
reproduce here. So the `saturated.bin` outlier and the `biased-random-bytes`
uncorroborated row are **the same estimator**, found twice by two different
routes — which is now the strongest candidate defect in this fork that this
campaign has produced, and it stays **OPEN**.

### What this does NOT establish

- **One platform still.** This says the five rows are reproducible by another
  implementation *here*. It does not say what any of them do on x86-64, which is
  where the reference data was produced and where `selftest` is expected to pass
  outright. **NOT RUN.**
- **Two implementations is not many.** Five identical rows is strong; it is
  still n = 2.
- The 4 key-set failures mean the C99 port and NIST **disagree about what to
  report** for 1-bit data. That is unexamined here and is not this fork's
  business, but it does mean "5 agreeing, 6 disagreeing" must not be read as
  "the C99 port is worse".
- Nothing here diagnoses the Bitstring MultiMCW difference. It is **located**,
  twice, and left open.
- **Nothing reported upstream, to NIST or to either project.**

## OC-113 — on the platform NIST's reference data was produced on, this fork reproduces all 11 reference outputs: 891 values, worst delta 1.01e-13

**The Linux half of `OC-107`, and it settles both `OC-107` and `OC-112`.**

CI step 5e, run 40249281414 at `289bb16`, `Linux x86_64`, `LDBL_MANT_DIG: 64`:

| dataset | result | compared | max delta |
|---|---|---:|---|
| `biased-random-bits.bin` | PASS | 60 | 4.18241830058008e-14 |
| `biased-random-bytes.bin` | PASS | 103 | **4.24382751162966e-14** |
| `data.pi.bin` | PASS | 59 | 4.32986979603811e-15 |
| `normal.bin` | PASS | 98 | 6.93196230865691e-15 |
| `rand1_short.bin` | PASS | 59 | 4.77395900588817e-15 † |
| `rand4_short.bin` | PASS | 98 | 2.44249065417534e-15 † |
| `rand8_short.bin` | PASS | 99 | 7.7715611723761e-16 † |
| `ringOsc-nist.bin` | PASS | 60 | **5.60662627435704e-15** |
| `truerand_1bit.bin` | PASS | 59 | 5.30686605770825e-14 |
| `truerand_4bit.bin` | PASS | 98 | 3.47499806707674e-14 |
| `truerand_8bit.bin` | PASS | 98 | 1.00808250635964e-13 |

† the short-dataset escape; **not a compliant assessment**.

```
datasets run: 11   agreeing: 11   disagreeing: 0
```

**All 17 gates PASS**, including the two new ones — `all 11 reference datasets
ran` and `every reference dataset agrees on glibc`, gated separately so a loop
that stopped early cannot pass as agreement.

### THE ANSWER TO "DOES THE TOOL WORK CORRECTLY", STATED PLAINLY

**On Linux x86-64 with glibc — the platform NIST's reference data was produced
on — this fork reproduces every one of NIST's published reference outputs across
all 11 datasets, 891 compared values, to a worst discrepancy of 1.01e-13, with
the identity of each input verified. Zero disagreements.**

On Darwin arm64 the same 891 values agree except for 8, worst 3.66e-10, all
inside the 1e-9 tolerance `known-platform-deltas.txt` records, and all in the
prediction estimators.

That sentence, with that measurement behind it, is what *"the tool works
correctly"* means for this fork — and it is now said of a comparator that
**checks the identity of what it read**, which every pass before `OC-73`/`OC-74`
did not.

### AND IT SETTLES `OC-112`

The two datasets that disagree on Darwin arm64 agree on glibc, and the size of
the change is the whole argument:

| dataset | row | Darwin arm64 | Linux x86-64 | ratio |
|---|---|---:|---:|---:|
| `biased-random-bytes` | worst | **3.66e-10** | **4.24e-14** | **8,600x smaller** |
| `ringOsc-nist` | worst | **1.55e-10** | **5.61e-15** | **27,500x smaller** |

**A fork defect does not shrink by four and a half orders of magnitude when the
architecture changes.** Combined with `OC-112` — where an independently written
C99 port reproduced 5 of the 8 Darwin rows **bit-identically** — the platform
explanation for `known-platform-deltas.txt` is now supported from two
independent directions:

1. the differences **vanish** on the reference architecture, and
2. a **different implementation** reproduces most of them exactly on the
   non-reference one.

**`OC-112`'s three uncorroborated rows are narrowed accordingly.** Bitstring
MultiMCW `P_local` and its min entropy, and the `ringOsc` MultiMCW magnitude,
are **arm64-only differences between two implementations that both agree with
NIST on x86-64**. That is a far weaker thing than a defect: it is two
implementations reassociating differently on one architecture, in a quantity
computed by bisection, with both correct where the reference data was made.

**The `saturated.bin` outlier of `OC-111` is therefore downgraded but not
closed.** It is the same estimator (Bitstring MultiMCW), it is still the only
quantity where this fork is the outlier against two independent
implementations, and it is still arm64-only and sub-nanobit. **It stays OPEN as
a candidate, with its direction and platform now known.**

### What this does NOT establish

- **It is agreement with NIST's outputs, not correctness of the standard.**
  `OC-108`'s Markov six-pattern item and section B of the divergence document
  are untouched by any amount of agreement.
- **The three short datasets used the escape** on both platforms, so their rows
  are not compliant assessments and are marked as such in the output.
- `ea_non_iid` only. The IID, restart and conditioning reference paths are not
  compared this way.
- **binary128 on Linux aarch64 stays NOT RUN.**
- Nothing reported upstream.

## OC-114 — the outside-battery corpus, three ways; and the premise that it holds no defect classes is wrong

**The second half of new-task item 2, and a correction to the brief.**

### The corpus does contain defect classes — just not physical ones

The item said this fork's outside-battery corpus *"is 5 Mersenne Twister
streams and 20 SHA-256 counter-mode streams, which contain no defect classes at
all."* `cpp/selftest/outside-battery-corpus.txt` declares **four** families:

```
  mt         5   Mersenne Twister clean streams
  sha       20   SHA-256 counter-mode clean streams
  defect     5   B_osc5000 (8538.7x at 59.938 Hz), C_osc500, D_lag5000,
                 E_weaklag5000 (40.21 sigma at lag 5000), F_xor30
  blindspot  1   G_xor13_02, the OC-18 case that must stay silent
```

**31 streams in four families, 5 of them defect streams and 1 a deliberate
blind-spot case.** The brief's 25 is the *clean* subset — the false-positive
denominator behind the `0 of 25` figure.

**The substance of the point stands, and is worth restating precisely:** those 5
defects are **injected signal** defects — periodic oscillation, lag correlation,
XOR mixing — built to exercise the *outside battery's own detector*. They are not
the failure modes of a physical source. **None of saturation, drift, replay,
warm-up, fading or DRBG output appears anywhere in this repository's pinned
corpus**, which is exactly why `OC-109` was worth doing. The corpus tests a
detector; it does not test the source model.

### The three-way result

Regenerated from seeds by `blindspot_streams.py` into a directory outside this
repository — one clean stream of each generator, two defect streams, and the
blind-spot case:

```
labels compared across >=2 implementations: 295
labels where every implementation agrees to 1e-09: 295
labels exceeding 1e-09:                              0
```

| stream | what it is | fork | C99 | delta |
|---|---|---|---|---:|
| `mt00` | clean Mersenne Twister | 0.8470166039320538 | 0.8470166039319968 | 5.695e-14 |
| `sha00` | clean SHA-256 counter | 0.8680418041013173 | 0.8680418041012551 | 6.217e-14 |
| `B_osc5000` | 8538.7x oscillation at 59.938 Hz | 0.6121263459047682 | 0.6121263459047682 | **0.000e+00** |
| `E_weaklag5000` | 40.21 sigma lag at 5000 | 0.856713069515719 | 0.8567130695156596 | 5.940e-14 |
| `G_xor13_02` | the `OC-18` case that must stay silent | 0.8600027307935295 | 0.8600027307935897 | 6.017e-14 |

**Zero disagreements, worst 6.2e-14 — and the strongest injected defect in the
corpus, `B_osc5000`, agrees bit-for-bit between two independent
implementations.**

Note what that row also shows: `B_osc5000` carries an **8538.7x** oscillation
that the outside battery detects at 59.938 Hz, and `ea_non_iid` assesses it at
**0.612** against `mt00`'s 0.847 — so the non-IID battery does register it,
by about 0.235 bit. The outside battery exists because 0.235 bit is not how
you want to find a 8538x spectral spike.

### The complete item-2 tally, with the identity of what it counts

| corpus | rows compared | exceeding 1e-9 | worst |
|---|---:|---:|---:|
| NIST's 11 reference datasets (`OC-110`) | **891** | **0** | 3.659e-10 |
| the outside-battery corpus, 5 streams | **295** | **0** | 6.217e-14 |
| the defect datasets, 5 degenerate (`OC-111`) | **503** | **10** | 4.165e-09 |
| **total** | **1,689** | **10** | |

**1,689 value-rows compared across three independently written implementations.
Ten disagreements, all of them on deliberately degenerate inputs, all smaller
than the quantisation term the floor already subtracts.**

### What this does NOT establish

- **5 of 31 streams**, chosen to span the four families, not the whole corpus.
- The corpus is **regenerated from seeds**; the generated bytes were not checked
  against `outside-battery-corpus.txt`'s pinned digests in this run, so these
  are the right streams by construction and not by verification.
- The `B_osc5000` 0.235-bit observation is **one stream at one width**, not a
  claim about the non-IID battery's sensitivity to oscillation in general.
- **Nothing reported upstream, to NIST or to either project.**

## OC-115 — the single-capture variance, separated from the estimator jump; and a tolerance 9.7x narrower than it

**Two numbers were being conflated downstream, and the smaller one is the one
that matters. Measured on five `openssl rand` streams from the identical
command, width 8, 1,000,000 samples each.**

### The two quantities are not the same

| quantity | value | what it is |
|---|---:|---|
| the **Lag estimator's** jump, `r = 3 -> 4` | **1.2674253400228785** bit/sample | one estimator's step at that `C`/`N`. It reaches the reported figure **only when Lag is the minimum**. |
| the **assessed figure's** spread, 5 draws of one source | **0.7153525775424896** bit/sample (**0.08942** bit/bit) | what a single capture's reported figure actually varies by |

Using `1.27` as the variance of a *reported* figure **overstates it by 77 %**.
The assessed figure is the minimum over all estimators, and Lag bound in only
one of the five draws.

| draw | assessed | bit/bit | did Lag bind? |
|---|---|---:|---|
| the `OC-109` stream | 6.6384051555787362 | **0.82980** | **yes**, `r = 4`, `P_local = 0.010038` |
| `ossl1` | 7.3143196724744621 | 0.91429 | no, `r = 3` |
| `ossl2` | 7.1377117056905979 | 0.89221 | no |
| `ossl3` | 7.3337658725840837 | 0.91672 | no |
| `ossl4` | 7.3537577331212258 | 0.91922 | no |

**And "range" is the wrong summary, because the distribution is heavy-tailed.**
Four draws cluster within **0.216** bit/sample (7.1377–7.3538); the fifth sits
**0.68** below their median. `-log2(0.010037855160187185) = 6.638405155578736`,
matching the printed figure exactly, so `P_local` did bind.

**`n = 5`. The spread is a lower bound on the true variance, not a bound** —
rule 6: an observed maximum is not a bound. And it is characterized for *an
OpenSSL CSPRNG at width 8*: which estimator binds is source-dependent, so this
figure does not transfer to a physical source.

### Does anything in THIS repository treat one assessment as a source's rate?

Swept. **No** — and the reason each is safe is worth recording, because "it
pins a figure" and "it claims a source's rate" look alike:

- **`cpp/selftest/pin-check.sh`** pins `0.12644573619605429` at `RELTOL=1e-9`,
  but against `SAMPLE_SHA256=7d37dc37...`, **verified before comparing**. Fixed
  bytes, so re-running is deterministic and single-draw variance cannot apply.
  Correctly scoped.
- **`known-platform-deltas.txt`** records differences between implementations on
  the *same* bytes. Not a source rate.
- **`regression-outside-battery.sh`** is the one place a **cross-stream**
  statistic is pinned, and **it already carries its spread**:
  *"Compression binds 5 of 5 clean streams at 0.8546 +/- 0.0092"*.

### BUT THAT SPREAD IS 9.7x TOO NARROW, AND THE MARGIN IS 0.0028

`regression-outside-battery.sh:337` accepts Compression in **`[0.8270, 0.8822]`**,
derived as 3 sd from `0.8546 +/- 0.0092` — measured on 5 clean streams.

| | bit/bit |
|---|---:|
| spread on their 5 clean streams (the `+/- 0.0092`) | 0.0092 |
| spread on my 5 `openssl` streams | **0.0894** |
| **ratio** | **9.7x** |
| my `P_local`-excursion draw | **0.82980** |
| its margin inside the window's lower bound `0.8270` | **0.00280** |

**Their five streams happened not to contain a `P_local` excursion; mine
contained one.** So `+/- 0.0092` is a lower bound measured on a sample that
missed the tail, and the 3-sd window built on it is correspondingly narrow — an
ordinary clean draw lands within **a third of one sd** of breaching it.

**LATENT, NOT LIVE, and the scoping is the point.** The 25 clean streams are
generated from **fixed seeds** (`random.Random(0xA ...)`, `sha_bits` keyed on a
format string) and the corpus is **digest-pinned over 31 entries**, so every run
produces the same bytes and the same Compression values. **The window is never
sampled afresh, so it cannot fail today.** It becomes live the moment the corpus
is **re-seeded or extended** — which is exactly when someone would trust it most.

**Direction: a false FAIL, not a false pass.** The window is too narrow, so it
would report a defect where there is none. That is the safe direction for a
detector and it is still an instrument defect, and by this project's own rule a
count from an instrument with unmeasured error is a **floor**.

**Not repaired in this pass.** Widening it from `n = 5` would be swapping one
under-sampled figure for another; the honest fix is to measure the spread on
enough draws to see the tail, and that is queued, not claimed.

### What this does NOT establish

- **`n = 5` on one source at one width.** Nothing here characterizes the
  variance of a physical source's assessment, which is what January needs.
- It does not say the `0.8546` centre is wrong — only that the `+/- 0.0092`
  beside it is an under-sampled spread.
- The sweep covered this repository's pinned figures. **Whatever consumes an
  assessment as a device property lies outside this repository** and is not
  examined here.
- Nothing reported upstream.

## OC-116 — the Bitstring MultiMCW candidate RESOLVED: upstream's algorithm, platform-visible, quantitatively explained

**Owner's item 1. Verdict: NOT this fork's defect. It is an upstream numerical
fragility, invisible on x86-64 and worth ~1.8e-9 on any target whose
`long double` is 53-bit. Resolved, not unresolved.**

### (a) Has this fork modified MultiMCW, or anything it calls? NO

| file / function | upstream `87c104d` | this fork | code-only comparison |
|---|---|---|---|
| `cpp/non_iid/multi_mcw_test.h` | — | — | **BYTE-IDENTICAL**, sha256 `43cb164e0ece5658` |
| `prediction_estimate_function` | 397 ch | 397 ch | **IDENTICAL** `99f83bc857a5a3f2` |
| `calc_p_local` | 1212 ch | 1212 ch | **IDENTICAL** `b7161513faf980e3` |
| `relEpsilonEqual` | 1002 ch | 1002 ch | **IDENTICAL** `8f0e7056eef244ab` |
| `predictionEstimate` | 1767 ch | 1767 ch | **IDENTICAL** `595d1722d5b3ece9` |

`predictionEstimate` grew 39 -> 57 lines, which **looks** like a modification and
is **entirely the `F13` comment block**: comment- and whitespace-stripped, the
two hash identically. `F09` repaired **MultiMMC**'s run counter — a different
estimator — and the names must not be allowed to collapse.

**Positive control for the comparison method**, because a sweep that finds
nothing needs one: the same strip-and-compare reports ***DIFFERS*** on
`read_file_subset` (4362 -> 5641 ch) and `calc_stats` (382 -> 446 ch), and
IDENTICAL on `std_dev` and `free_data`. The method detects code changes and
reports none here.

**So this fork cannot be the origin, and the question is upstream-or-platform.**

### (b) An independent oracle, and it does NOT agree with this fork

**The decomposition first, because it says where to look.** On `saturated.bin`,
Bitstring MultiMCW, this fork and the C99 port agree **exactly** on every
integer and on `P_global'`:

```
  C = 4337056      r = 81      N = 7999937
  P_global  = 0.54213626932312087
  P_global' = 0.54258999794492346
```

and differ **only** in `P_local`. **The predictor counted identically; the
entire divergence is in solving `P_local`.**

`audits/2026-10-11-independent-audit/oracles/plocal_exact.py` solves the same
§6.3.7 equation the production code states —
`f(p) = ln(1-px) - ln((r+1-rx)q) - (N+1)ln(x)` with `x` the root of
`x = 1 + q p^r x^(r+1)` — at **80 decimal digits**, finding `x` by a bracketed
root-find rather than a capped iteration, and bisecting `p` far below the
quantity in dispute. It implements no part of either tool.

| | `P_local` | \|delta\| from the oracle |
|---|---|---:|
| **ORACLE (80 dps)** | **0.7916290824210893820486581** | — |
| the C99 port | 0.79162908233501794 | **8.607e-11** |
| **this fork** | 0.79162908359969442 | **1.179e-9** |

**The C99 port is 13.7x closer. The oracle's min-entropy is
0.3371034806146510**, against the Rust implementation's `0.337103480615` —
agreement to ~1e-13, the best of the three, consistent with its 256-bit MPFR.
**This fork is the least accurate of the three on this input.**

### (c) Is it the `long double` format? YES, and the amplifier is identified

**The stopping rule is NOT the explanation**, which had to be eliminated first:
`relEpsilonEqual(pVal, log_alpha, ..., 4)` is a 4-ulp test on the function
value, `|df/dp| = 0.98012409` near the root, so the rule admits only
**9.108e-18** of slack in `p` — **nine orders of magnitude tighter** than the
1.18e-9 spread. The bracket at break is 5.078e-17 wide. The error is in
*evaluating* `f`, not in stopping early.

**THE MECHANISM.** At the root `q*p^r = 1.2563137e-9`, so

> **`x = 1.0000000012563138425` — `x` sits just above 1.0.**

Float spacing near 1.0 is `2^-52` at 53-bit and `2^-63` at 64-bit; `d(log x)/dx`
is ~1 there, so `log(x)` inherits that **absolute** error; and the term
**`(N+1)*log(x)` with `N+1 = 7,999,938` multiplies it by eight million**.
`|df/dp| ~ 0.98` then passes it into `p` almost 1:1:

| `long double` | spacing near 1.0 | predicted error in `p` | measured |
|---|---|---:|---|
| **53-bit** — Apple arm64, MSVC | 2.22045e-16 | **1.81237e-9** | this fork **1.17861e-9**, C99 **8.60714e-11** |
| **64-bit** — x86-64 x87 | 1.0842e-19 | **8.84944e-13** | vs NIST refdata **1.01e-13** (`OC-113`) |

**Every measured value sits inside its platform's predicted envelope.** The two
arm64 implementations differ because they land at different points *within* the
same 1.8e-9 envelope — different `libm` (Apple clang vs `gcc-16`), different
operation order — **not because either is wrong**. An emulation of the
production algorithm at 53-bit inner precision lands at 9.574e-11, also inside
the envelope, which is why the emulation reproduces the *envelope* and not any
particular implementation's digit.

**This is `R-1`'s format difference appearing as an accuracy loss instead of a
crash.** `R-1` is the `assert(p_col >= 1/k)` abort in `lrs_test.h` on 80-bit
`long double`; this is the same type, the same platform axis, a different
failure mode.

### THE VERDICT, and it closes `OC-112`'s open question too

**Upstream's defect, platform-visible, quantitatively explained.** Specifically:
§6.3.7's recommended evaluation computes `(N+1)*log(x)` where `x = 1 + eps` with
`eps ~ 1.3e-9`, which discards most of `eps`'s significance before multiplying
by `N`. Carrying the increment separately — `log1p` of the increment, or solving
in terms of `x-1` — would remove the amplification. **Not reported upstream**,
per the standing decision.

**`OC-112`'s three non-surviving rows are now explained.** It found 5 of the 8
Darwin rows reproduced **bit-identically** by the C99 port and 3 not. Both
outcomes are the same phenomenon: inside a 1.8e-9 envelope, two independent
implementations sometimes land on the same float and sometimes do not. **The 5
identical rows are where the rounding coincided; the 3 others are where it did
not. Neither is evidence of a defect in either implementation.**

**Direction and magnitude.** Two-sided — this fork reads high on this row and
the C99 port low. **Sub-nanobit, and smaller than the floor's own correction**:
`C22a` is `8.08e-15 x (n+1)`, which at `n = 8e6` is **6.464e-08**, fifty-five
times the worst error here. **No figure this project publishes moves.**

**`OC-111`'s `saturated.bin` outlier is CLOSED by this entry** — same estimator,
same mechanism, and the oracle names which implementation is closer. **The
"strongest open candidate the campaign produced" was a 53-bit `long double`
envelope in upstream's root-finder.**

### What this does NOT establish

- **One input, one row.** `saturated.bin` Bitstring MultiMCW at `r = 81`,
  `N = 7999937`. The envelope argument generalizes; the specific digits do not.
- The oracle solves the equation **the production code states**. If §6.3.7's
  text and that equation differ, the oracle inherits the discrepancy — it was
  not independently re-derived from the publication here.
- **Bitstring Lag on `saturated.bin`** (2.778e-09) was not run through the
  oracle. It is the same estimator family, the same `P_local` solver and the
  same envelope, so it is **expected** to be the same finding — expected is not
  measured, and it is recorded as not measured.
- **binary128 on Linux aarch64 stays NOT RUN**, and that is the one platform
  where this envelope would be ~113-bit and the effect negligible.
- Nothing reported upstream.

## OC-117 — the top band named and worked: 6 CAUGHT, 5 NOT CAUGHT, and "9 of 15" corrected to 8

**Owner's item 3, and the two numbers stated plainly first because the report
did not.**

### Which band is which, and what the 15 counts

| band | the two facts | pairs |
|---|---|---:|
| **1 — THE TOP BAND** | the later repair rewrote a non-comment line the earlier one added, **and** either reaches a **figure** | **27** |
| 2 | reaches a **claim** (the harness, CI) rather than a figure | **39** |
| | total undeclared | **66** |

**The 15 counts DISTINCT EARLIER MECHANISMS, not pairs and not tests.** Band 1's
27 pairs touch only 15 distinct earlier repairs — seven pairs all touch
`65b00d8` — and testing a mechanism once discharges every pair that touched it.

### AND "9 of 15 mutated" WAS WRONG: nine ARMS covered EIGHT mechanisms

`OC-105` ran nine mutation arms and reported them as "9 of 15". **It conflated
arms with mechanisms**: `c2f2b94` took two arms, and `acedae5`/`ada37a1` shared
two more. Audited:

```
  arms run                     9
  mechanisms covered           8  of 15
  mechanisms NOT covered       7  of 15   (one with no runnable case)
```

**It is not the dead-guard count either.** The three **class-A** dead-guard
determinations are a separate set of three flags, settled by mutation in
`OC-98`. Nothing in this repository has a "9 of 15" that refers to them.

### The six workable mechanisms, worked

| mechanism | pairs | mutation | result |
|---|--:|---|---|
| `8ff739d` the canary itself | 1 | `EXPECTED_SHA` last digit `...468c -> ...468d` | **CAUGHT** (control 0, mutant 2) |
| `5074fff` `C23` as a recomputed decision | 2 | `C23_PINS` triple `1:572:570 -> 1:572:571` | **CAUGHT** (mutant 1) |
| `7a0be01` `fix(C23)`'s cutoff method | 1 | the gate's expected `restartCutoffMethod`, `exact-multinomial-maximum -> printed-binomial-SUPERSEDED` | **CAUGHT** (mutant 1) |
| `210aed6` `oac-13`'s atomic report write | 1 | `int flags = O_WRONLY \| O_CREAT \| O_EXCL;` -> drop `O_EXCL`, **rebuilt** | **NOT CAUGHT** |
| `b12247c` canary re-signatured 3-way | 2 | — | **NOT MUTATED**, needs four builds; declared |
| `9aa991d` canary widened to both `long double` formats | 1 | — | **NOT MUTATED**, needs an 80-bit host; binary128 stays **NOT RUN** |

The `210aed6` arm carries its own control: the tree is copied, built
**unmutated**, and `regression-output-aliasing.sh` is required to pass against
that copy before the mutation is applied — so a later failure cannot be blamed
on the copy or the compiler.

### THE NEW FINDING: removing `O_EXCL` is not caught

**`F03`'s own regression does not notice when the temporary's `O_EXCL` is
removed.** Control 0, mutant 0. `O_EXCL` is the primitive `oac-13` introduced so
the temporary cannot land on a file that already exists — the guard against the
symlink-aliasing half of `F03` — and nothing in
`regression-output-aliasing.sh`'s 3 `F03` cases distinguishes a build that has
it from one that does not.

**Why the existing cases miss it.** They plant a symlink at the temporary's
*predicted* path and check the capture survives. With `O_EXCL` gone the open
still **fails** on the planted symlink for a different reason — `O_NOFOLLOW` is
also set — so the capture survives and the case passes. **The two guards are
redundant for exactly the input the test uses**, which is why removing one is
invisible. A case that distinguishes them needs a **regular file** at the
temporary's path, not a symlink.

**Queued, not repaired**: measurement and repair are separate passes, and adding
that case needs its own break-verification and rebuild cycle.

### The running total for band 1

```
  CAUGHT        6   c2f2b94 x2, b072bf7, 8ff739d, 5074fff, 7a0be01
  NOT CAUGHT    5   acedae5+ada37a1 x2, 6b4717e, 65b00d8, 210aed6
  no verdict    2   (see below)
  not mutated   2   b12247c, 9aa991d
  no case       1   5c3353f
```

**12 of the 15 mechanisms now have a mutation verdict**, against 8 before.
**5 are unguarded.** The top band is **not empty**, and what remains is named:
two canary mechanisms needing builds this host cannot provide, and one rule-text
entry with nothing to run.

### TWO ARMS PRODUCED NO VERDICT, AND THE CAUSE WAS ME

`outside-battery pinned figures` and `the divergence-figure enforcement` both
reported **RESTORE FAILED**. The battery restores with `git checkout --`, and
**I edited both of those files in the working tree while the battery was
running**, so the restore reverted them to committed state — which differs from
what the arm measured — and **the digest check refused to earn a verdict.**

**The guard worked and it cost me the edits**: the new Compression window and the
`F15` blob entry were both destroyed and had to be re-applied. The battery
refuses to *start* on a dirty tree; it does not refuse to *continue* when the
tree becomes dirty under it. **That is the defect, and it is in the battery**:
recorded here, not repaired, because the arms it affected are the two already
shown CAUGHT in `OC-105`.

### What this does NOT establish

- **Band 2's 39 pairs remain unexamined.**
- `NOT CAUGHT` means **no case in the suite notices this change**. It does not
  mean the value or the code is wrong — all five mutated things are believed
  correct.
- One mutation per mechanism. A mechanism that catches one break can miss
  another, and `210aed6` is the proof in the other direction: it survived
  `OC-105`'s claim of coverage precisely because nobody had broken it.
- Nothing reported upstream.

## OC-118 — the Compression window reset from 300 draws, not 5; and guide rule 13

**Owner's items 2 and 5.**

### The tail, measured

`audits/2026-10-11-independent-audit/reproducers/compression-window-tail.sh`
draws fresh clean streams from the **same two generators and the same seeding
discipline** as the corpus — imported from `blindspot_streams.py` rather than
reimplemented — with seeds from **900000**, which cannot collide with the pinned
`0xA`, `0xC0+i` or `sha 0..19`. It records what the check reads: **which
estimator binds and its value.**

**n = 300**, 150 Mersenne Twister and 150 SHA-256 counter mode, 1,000,000
one-bit samples each:

| | |
|---|---|
| binding estimator | **Compression 284**, Collision **11**, LRS **3**, t-Tuple **2** |
| mean / median | **0.854784** / 0.851422 |
| **stdev** | **0.025732** |
| min … max | **0.805141** … **0.941540** |
| p0.5 / p5 / p50 / p95 / p99.5 | 0.80831 / 0.81882 / 0.85205 / 0.89672 / 0.93383 |

**Two things follow, and they point opposite ways.**

1. **The pinned centre was right.** `0.8546` sits at **percentile 54.0** of this
   sample. `OC-16` measured the centre correctly from five draws.
2. **The tolerance was 2.8x too small**, and the consequences are large:
   **96 of 300 draws — 32.0% — fall outside `[0.8270, 0.8822]`** (45 below, 51
   above), and a further **5.3%** bind on something other than Compression,
   which failed the check outright. **The check as written would reject about a
   third of ordinary clean streams.**

It never fired because the corpus is seeded and digest-pinned: the same bytes,
the same values, every run. `OC-115` called that latent; this is the rate.

### The window, set from the measurement

```
  [0.805141 - 0.025732,  0.941540 + 0.025732]  =  [0.7794, 0.9672]
```

**The observed range widened by one sample standard deviation each side.** Rule 9
— a sweep's extremum is a **lower bound** on the spread, not the spread — so the
range cannot be used as-is; **one sd is a margin chosen and stated, not derived.**
`n = 300` and the method are recorded in the check itself, beside the numbers.

**And the binder requirement was wrong in kind, not degree.** Four estimators
were observed binding, so demanding one is a false requirement. Any of the four
is accepted, and the **Compression share** is counted against a floor derived
from the measured rate at corpus size: `94.7% - 3*sqrt(p(1-p)/25) = 81.3%`, so
**80%**.

**Verified by observing failure, both directions:**

| value | new window | old window |
|---|---|---|
| **0.82980** — the `OC-115` draw | **PASS** | PASS |
| 0.805141 — the measured minimum | **PASS** | **FAIL** |
| 0.941540 — the measured maximum | **PASS** | **FAIL** |
| 0.7793 / 0.9673 — just outside | **FAIL** | FAIL |

and the share floor: `24/25` PASS, `20/25` PASS, **`19/25` FAIL**. End to end,
`OUTSIDE_BATTERY_FULL=1` reports
`binding estimator in [0.7794, 0.9672], Compression 5/5` and the script **PASSES**.

### WHAT THE NEW WINDOW STILL CANNOT COVER

- **It is not a bound.** `n = 300` gives a range, and **2 of the 300 fall outside
  a 3-sd window computed from the same sample** (`[0.7776, 0.9320]` against a
  max of 0.9415) — so the distribution is **heavier-tailed than Gaussian** and
  the true extremes are not known.
- **A window 0.19 wide is a weak instrument.** It will not notice a systematic
  shift smaller than the per-stream variance. The better instrument for the same
  purpose is a bound on the **mean** over the corpus, whose standard error is
  `0.025732/sqrt(25) = 0.0051` — five times tighter than the old per-stream
  window pretended to be. **Not changed here**, because that is a redesign of
  what the check asserts rather than a correction of its numbers.
- **It is measured on two pseudorandom generators at width 1.** A physical source
  is not one of them, and this figure is not quoted as a property of one.

### Guide rule 13, and the sweep

`--help` taken as a positional path is the **third** instance of one class, now
written down as **rule 13** in `audits/BUG-REPAIR-GUIDE.md`: *a program that
does not parse its arguments does something irreversible with one of them.*
`A04`/`F04` (exit 0 with nothing assessed), `OC-104` (one command line, two
operations on two platforms), `F15` (33 MB under a directory named `--help`).
**In all three the detection was accidental** — none was found by looking.

**The sweep, with its blind spot named.** Of **123** tracked `.sh` and `.py`
files, **44** read a positional argument as a path with no option handling —
a **floor on candidates, not a count of defects**, because the method cannot
distinguish "takes `$1` as a work directory" from "would do something
irreversible with an option-shaped `$1`". Narrowed to **create or destroy at an
unvalidated positional path: 5 of 123**, and **all five are under
`audits/2026-09-30`**, which `audits/enum-instruments.sh` lists as **FROZEN** —
dated evidence that guide rule 2 forbids editing and that nothing invokes now.
**Recorded, not repaired**, and unreachable rather than tolerated.

**Both controls fired**, because a sweep reporting a small number needs one: the
method **FLAGS** `blindspot_streams.py` as it stood at `a9a269f` and **does not
flag** the repaired version at `HEAD`.

### What this does NOT establish

- The `F15` blobs are described in `FORK-DIVERGENCE-AND-TRUST.md` so the history
  is not a mystery; **they are still in the history** and still cost every clone.
- The 5 frozen hits were **not executed** to confirm they would misbehave. They
  are flagged by shape, and the shape is the rule's definition.
- Nothing reported upstream.

## OC-119 — the tail measurement replicated after a memory-pressure kill, and the replication caught a defect in OC-118's own fix

**A background job was killed for low memory while `OC-118`'s sample was being
analysed. The arithmetic is deterministic from the log, so re-running it would
only reproduce itself; what needed redoing was the MEASUREMENT, because an
OOM-killed tool run would have put a wrong figure in the record.**

### First, the existing sample was checked for corruption rather than trusted

An OOM-killed `ea_non_iid` produces no estimator lines, and the harness's
extractor prints `NONE 0` for that case — so corruption is visible, not silent:

```
  rows where no estimator was parsed (NONE):  0
  rows with value 0.000000000:                0
  data rows:                                  300
  distinct seeds:                             300   (900000..900299, no gaps)
```

### Then an INDEPENDENT 300 draws, because a re-run of the same seeds tests nothing

`compression-window-tail.sh` gained a **second argument**, the seed base, so a
replication is a different sample rather than the same one again.

| | first, seeds 900000+ | replication, seeds 910000+ |
|---|---|---|
| draws / corrupt rows | 300 / **0** | 300 / **0** |
| Compression binds | 284 (94.7%) | 285 (95.0%) |
| other binders | Collision 11, LRS 3, t-Tuple 2 | Collision 11, t-Tuple 2, **Lag 2** |
| mean / median | 0.854784 / 0.851422 | 0.853658 / 0.851569 |
| stdev | 0.025732 | 0.024596 |
| min / max | 0.805141 / 0.941540 | **0.795197** / 0.935128 |
| outside the ORIGINAL window | 96 (32.0%) | 82 (27.3%) |
| outside `OC-118`'s window | **0** | **0** |

**Welch `t = 0.547` on the two means** (difference 0.001126), so the samples are
**indistinguishable**. **The memory pressure did not corrupt the first
measurement**, and `OC-118`'s conclusion — centre right, tolerance 2.8x too
small, about a third of clean draws rejected — replicates.

### AND THE REPLICATION CAUGHT A DEFECT IN `OC-118`'s OWN FIX

`OC-118` replaced the "must be Compression" requirement with an **allowlist of
the four estimators seen binding in n = 300**. The independent sample found a
**fifth — `Lag`, twice — which that allowlist would have rejected.**

**An allowlist built from a sample is the same under-sampling error `OC-118` was
repairing, one level up.** So it is **removed, not extended**: extending it would
only wait for a sixth. Any estimator may bind; what is checked is the
**Compression share** against a floor, plus the value window. **A fix made from
n = 300 lasted exactly as long as it took to draw another 300.**

### The window re-derived from the pooled sample

```
  POOLED n=600:  mean 0.854221   stdev 0.025177   min 0.795197   max 0.941540
  window = [0.795197 - 0.025177,  0.941540 + 0.025177]  =  [0.7700, 0.9667]
```

The share floor is re-derived at the pooled rate: `94.8% - 3*sqrt(p(1-p)/25) =
81.4%`, so **80%** stands.

**Verified by observing failure, both directions:**

| value | pooled window | original window |
|---|---|---|
| **0.795197** — the replication's minimum | **PASS** | **FAIL** |
| **0.941540** — the pooled maximum | **PASS** | **FAIL** |
| 0.82980 — the `OC-115` draw | PASS | PASS |
| 0.7699 / 0.9668 — just outside | **FAIL** | FAIL |

**All 600 draws fall inside `[0.7700, 0.9667]`**, and
`OUTSIDE_BATTERY_FULL=1` reports
`binder in [0.7700, 0.9667], Compression 5/5` with the script **PASSING**.

### What this does NOT establish

- **`n = 600` is still a sample.** The pooled range is a **lower bound** on the
  spread (rule 9), and the replication's minimum already sat **below** the first
  sample's — which is the whole reason the allowlist failed. A third sample may
  find a sixth binder or a lower minimum.
- **The margin is shrinking as n grows.** `OC-118`'s window had 0.0257 of
  headroom below the then-minimum; the pooled one has 0.0252 below a minimum
  that moved down by 0.0099. The window is not converging quickly.
- **The deeper point stands unaddressed**: a per-stream window this wide is a
  weak instrument, and a bound on the **mean** (pooled standard error
  `0.025177/sqrt(25) = 0.0050`) is the better one. Still **not changed**, because
  that is a redesign of what the check asserts.
- Two pseudorandom generators at width 1. **Not a property of a physical source.**
- Nothing reported upstream.

## OC-120 — rule 14, the sample-derived-constraint sweep, the mean bound, the 13.7x gap, and two gaps closed

### Item 1 — rule 14, and a numbering correction

**The owner asked for this "where RULE 31 lives". No rule numbered 31 exists in
this repository**: `audits/BUG-REPAIR-GUIDE.md` runs 6–13 with 10 VACATED, and a
repository-wide search for `rule 3[0-9]` returns nothing. That numbering belongs
to another rule set. Recorded as **rule 14**, the next real slot, with the
mismatch noted in the rule itself so the two schemes can be reconciled.

**Rule 14: a constraint derived from a sample is validated against an
independent sample.** The allowlist is its worked example, and the rule records
the part that matters most — `OC-119`'s two samples were statistically
**indistinguishable** (Welch `t = 0.547`) **and the replication still broke the
fix**, because what failed was not the central estimate but an **enumeration at
the edge**. So validation compares the constraint's *decision*, not its
statistics.

### The sweep for sample-derived constraints

| | |
|---|---:|
| candidate lines | **105** across **27** files |
| **enforced** by the suite | see below |

**105 is a FLOOR on candidates, and the blind spot is named**: the method keys
on a numeric constraint near a measurement word (`measured`, `observed`, `n=`,
`draws`, `streams`), so it (a) cannot distinguish an *enforced* constraint from
a figure quoted in prose — 28 of the 105 are in `ORCHESTRATOR-CHECKS.md`, which
enforces nothing — and (b) misses any constraint whose provenance is not stated
in words near it. **Both positive controls fired**: the Compression window and
`known-platform-deltas.txt`'s `1e-9` were both found.

The enforced ones, with provenance and replication status:

| constraint | from what measurement | n | independent sample? |
|---|---|---|---|
| Compression window `[0.7700, 0.9667]` | clean-stream draws | **600** | **YES** (`OC-119`) |
| Compression share floor 80 % | same | **600** | **YES** |
| mean bound, 3 SE of 0.854221 | same | **600** | **YES** |
| `known-platform-deltas.txt` `1e-9`, 8 rows | one run per row, Darwin arm64 | **1** | **PARTIAL** — `OC-112` reproduced 5 of 8 rows bit-identically with an independent *implementation*, not an independent *sample* |
| `outside-battery-check.cpp` 5.731 sigma, 30x | the 25-stream corpus | **25** | **NO** |
| `pin-check.sh` `EXPECTED` at `RELTOL=1e-9` | one run on digest-verified bytes | **1** | **N/A** — fixed bytes, deterministic, variance zero by construction |
| **`C22a` = `c x K` = 8.08e-15** | two grid maxima | see below | **NO** |

### `C22a`, scoped and NOT restatused

Its status is unchanged in this pass, as instructed. What it rests on:

- **`c = 0.4991`** — max over **592 near-root points**, argmax at `N = 10,000`,
  `r = 3`, **INTERIOR**, and bit-identical when the refinement window is
  extended nine orders (`OC-63`). *"As good as a measurement gets."*
- **`K = 1.6189e-14`** — sup over an `(N, r, ldomain)` sweep of
  `2^-52/(|f'(p*)| p* ln 2)`, **attained at `N = 5`, `r = 2`**, and **`r = 2` is
  the FIRST value in the swept list `[2, 3, 4, 5, 6, 8, ...]`**. Whether the true
  infimum lies at `r = 2` or at **`r = 1`** — which the standard admits when the
  longest run of correct predictions is 0 — **was never examined.**

**So `K` is a boundary-attained maximum from a single grid, which is exactly the
shape that just failed**, and `C22a`'s own comment already says rule 9 "applies
to this factor and was never applied to it". The margin is thin: the sweep's
worst realised inflation reaches **92.8 %** of the ceiling.

**Can an independent grid be run? In principle yes, and the tooling now exists**
— `reproducers/c22_bound.cpp` evaluates `calc_p_local` from production headers,
and `oracles/plocal_exact.py` supplies the exact root and derivative, so the
integrand is computable wherever the root lies in the domain.

**What it would cost is not compute — it is recovering the grid.** Attempted
here at `r in {1,2,3}`, `N in {5,10,50,1000}`, `ldomain = 1/2`: **all twelve
points were REFUSED by the oracle** — `target not bracketed: f(lo) = -4.158` and
similar — because at those `(r, N)` the root lies **below** the domain floor and
there is no `P_local` to solve for. The original sweep's `(N, r, ldomain)` choices
are therefore **load-bearing and are not in the repository** — only the two
outputs and a prose description of the `r`-list survive. **The grid must be
reconstructed before any replication means anything**, and that is the cost.

**The refusal is itself the result worth keeping**: the oracle declined twelve
times rather than returning a number. A less careful probe would have returned
garbage and it would have looked like a replication.

**What it would establish:** whether `K`'s maximum sits at `r = 2` because that
is the true infimum of `|f'(p*)| p*`, or merely because `r = 2` was the smallest
`r` tried. If `r = 1` admits an in-domain root with a larger integrand, **`C22a`
is too small and the floor subtracts too little** — the permissive direction.

### Item 2 — the mean bound added, the window frozen

**Two checks with different jobs, because only one improves with measurement.**

- **The window is the gross-failure detector.** Derived from the observed
  **range**, which does not converge — `OC-119`'s minimum sat 0.0099 below the
  first sample's. Set wide from the pooled `n = 600` and **no longer
  re-derived**; its job is stated in the check. Chasing a non-converging
  extremum is work with no end.
- **The mean bound is the shift detector.** Standard error `stdev/sqrt(n)`
  shrinks at a known rate, so it **is** re-derived as `n` grows. Centre
  `0.854221`, `sd 0.025177`, bound **3 SE at the number of streams actually
  examined** — computed from `comp_ok`, not assumed, so a loop that stopped
  early cannot pass as a tighter bound.

**And section 6 now examines every clean stream the mode selected**, not just
the five MT ones: 25 in full mode makes the bound **2.2x tighter** at ~0.6 s per
run.

**Control, on the real corpus in full mode:**
```
  mean within 3 SE of the pooled centre:  mean=0.848290 centre=0.854221 tol=0.015106 n=25
  binder in [0.7700, 0.9667], Compression 24/25
  regression-outside-battery: PASS
```
24 of 25 bind on Compression — consistent with the measured 94.8 % — which the
old `5/5` requirement would have **failed**.

### THE DEMONSTRATION, which is the reason for having two checks

A systematic shift applied to every one of the 25 real corpus values:

| shift | window | mean bound |
|---|---|---|
| **+0.0215** | **PASS** | **FAIL** |
| **+0.0300** | **PASS** | **FAIL** |
| **+0.0520** | **PASS** | **FAIL** |
| **-0.0095** | **PASS** | **FAIL** |
| -0.0310 | FAIL | FAIL |

**The window tolerates `+0.053 / -0.030` before any stream leaves it; the mean
bound catches `+0.0210 / -0.0092`.** So the band where **only the mean bound
fires** is `+0.021..+0.053` upward and `-0.009..-0.030` downward — a shift of
two to five per-stream standard errors that the window cannot see at all. **That
band is the new check's entire reason for existing.**

The asymmetry is worth stating rather than hiding: the corpus mean is
**0.848290** against a pooled centre of **0.854221**, an offset of
**-0.005931**, so the bound is 0.0210 away upward and only 0.0092 downward. The
25 pinned streams sit slightly low relative to 600 draws.

**My first attempt at this demonstration was wrong and the correction is the
point**: it reported that `+0.016` fails the mean bound. It does not — the offset
has to be overcome first, and the crossover is `+0.0210`. Computed, not
estimated.

**What each cannot see**, stated as required: the **mean bound is blind to one
bad stream** (one outlier moves a 25-stream mean by a twenty-fifth of its
excursion, so a single stream could go to zero and the mean would shift 0.034 —
caught, but a single stream at 0.80 would not be); the **window is blind to any
shift smaller than the per-stream spread**, 0.025, and in fact to anything below
`+0.053 / -0.030` on this corpus.

### Item 3 — the 13.7x gap: the compiler, and NOT safely adjustable

The two builds, compared:

| | this fork | the C99 port |
|---|---|---|
| compiler | **Apple clang 21.0.0** | **Homebrew GCC 16.2.0** |
| optimization | `-O2` | `-O2` |
| `-ffloat-store` | passed | passed |
| `-ffp-contract` | not set | `fast` |
| `-march` | none on arm64 | none (`MARCH=`) |
| fast-math / unsafe-math / mfpmath | **none** | **none** |

**`-ffp-contract` is NOT the cause — measured.** The fork was rebuilt at
`fast`, `on` and `off`; all three produce the **identical**
`P_local = 0.79162908359969442`. FMA contraction changes nothing here.

**AND THE FLAG THAT DOES DIFFER IS ONE APPLE CLANG SILENTLY IGNORES.** Every
compile of `ea_non_iid` emits

```
clang++: warning: optimization flag '-ffloat-store' is not supported
         [-Wignored-optimization-argument]
```

**The Makefile has passed `-ffloat-store` for the life of this fork and Apple
clang has discarded it every time**, while GCC honours it. It is visible on
every build and had not been read. On arm64 there is no x87 excess precision for
it to suppress, so it would be expected to be a no-op even if honoured — which
is consistent with the fork's value not moving — but **a flag the project
believes is setting its floating-point behaviour is not set.**

**Testing it by building this fork with GCC is blocked**: Homebrew GCC cannot
link `jsoncpp` here, which is a recorded property of this host, so the
compiler-isolated comparison on the tool is **NOT RUN**.

**VERDICT: the difference is code generation and `libm`, and it is not safely
adjustable.** The one flag that varies is not implemented by this compiler, and
the one that is implemented does nothing. **No flag was adopted.** Nothing that
disables IEEE semantics was tried or considered.

**And the envelope is not wider than it needs to be.** Both arm64 values —
1.179e-9 and 8.607e-11 — sit inside the **1.812e-9** envelope the 53-bit format
imposes (`OC-116`). The fork lands at a worse point *within* the format's
envelope, not outside it, so the envelope is the format's and the estimators are
not paying for a build flag.

### Item 4(a) — the battery re-checks before every arm

It refused to **start** dirty but not to **continue** when the tree went dirty
under it, which is how `OC-117` lost two edits. Each arm now re-checks the file
it is about to mutate and **refuses rather than restoring over** it.

**Verified by observing it fire**, with the start gate disabled so the per-arm
check is what decides:
```
  A02/A06 platform-delta manifest   REFUSED  cpp/selftest/known-platform-deltas.txt
                                             has uncommitted changes; restoring
                                             would destroy them
```
and the edit survived.

**It cost one more lesson on the way.** That verification ran in the background
past a restore, and the battery left a **live `C22c` mutation**
(`3.3599e-3 -> 3.3700e-3`) in `entropy_floor.py`. Found by `git status`, the
processes killed, both files restored from git, and the constant confirmed back
at `3.3599e-3`. **A mutation battery must not be run in the background while the
tree is being edited** — the per-arm guard prevents it restoring over edits; it
does not prevent it leaving its own mutation behind if it is killed mid-arm.
Recorded.

### Item 4(b) — the `O_EXCL` case CANNOT be built as specified, and the reason is the repair working

The case asked for is "a regular file at the temporary's path". **That path
cannot be planted at.** The suffix is `.tmp.%08lx%08lx` where

- the first half is `r1 = time(NULL) ^ (getpid() << 16)` — **predictable**;
- the second is **8 bytes read from `/dev/urandom` per attempt** —
  **unpredictable**, 32 bits in the suffix, so planting is 1 in 4,294,967,296
  per attempt.

**So `O_EXCL` is a second line the test cannot reach precisely because the first
line holds.** `F03` replaced a predictable `getpid()` temp with an unpredictable
one, and the unpredictable suffix is the guard the `F03` cases *do* test. That
`O_EXCL` removal is undetectable through the tool's interface is **defence in
depth, not an untested half.**

**The one condition where `O_EXCL` is load-bearing, named and NOT RUN.** If
`fopen("/dev/urandom")` fails, `r2` stays 0 and
`r2 = (attempt * 2654435761) ^ r1`, which at **attempt 0 is `0 ^ r1 = r1`** —
verified arithmetically. The path becomes `.tmp.<r1><r1>` with `r1` fully
predictable, and **`O_EXCL` is then the only remaining guard**. Reaching it
needs a sandbox with no readable `/dev/urandom`; **NOT RUN here**, with that as
the reason.

So `OC-117`'s "`NOT CAUGHT`" stands as a *measurement* and is **re-interpreted**:
not a gap to bolt a case onto, but an unreachable second layer plus one named
condition that is physically out of reach on this host.

### What this does NOT establish

- The 105 is a **floor on candidates**, with the blind spot named; the enforced
  table is seven rows and was assembled **by reading**, so a constraint whose
  provenance is not stated near it is missed by both.
- **`C22a`'s status is unchanged.** Nothing here replicates it; the entry scopes
  what replication would cost and what it would establish.
- The `-ffloat-store` finding is that the flag is **ignored**, not that honouring
  it would change any figure. On arm64 it is expected to be a no-op, and that
  expectation is **not measured** — the GCC build that would measure it is
  blocked.
- Nothing reported upstream.

## OC-121 — C22a's attainment point ANSWERED and justified; the asymmetry removed; the mutation hazard closed; and -ffloat-store read for the first time

### Item 1 — C22a at r = 1: OUTCOME 1, the safe one

**The grid was not recovered. The domain was taken from the mathematics**:
`p in [1/k, 1)` with `k` the alphabet size — `calc_p_local`'s own `1/k` floor
(`utils.h:1089`, `c22_bound.cpp:70`) — and `k <= 256` because §3.1.1 symbols
are 1–8 bits. `r` is `max_run_len + 1` (`utils.h:1234`), so **`r = 1` means the
longest run of correct predictions is zero**, which is reachable whenever no
prediction is ever correct.

`audits/2026-10-11-independent-audit/oracles/c22a_rscan.py`, 60 digits:

| axis | result |
|---|---|
| **`r = 1`** | **NO IN-DOMAIN ROOT at any (N, k).** `f(1/k)` is already below `ln(0.99)`, so the root lies **below** the domain floor and `P_local` cannot be solved at all. |
| **`r = 2`** | **THE MAXIMUM: 1.61892e-14**, which reproduces the recorded `K = 1.6189e-14` to **1.00001x**. |
| `r >= 3` | monotone decreasing — 0.679x, 0.512x, 0.400x, 0.301x, 0.068x — collapsing to ~1e-45 by `r = 12`, **no resurgence out to `r = 200`**. |
| **`N`** | **`N = 5` is an INTERIOR maximum, not a boundary.** Every integer 2–10 scanned: the integrand **rises** 2→5 (0.985, 0.998, 0.9999, **1.00001**) and **falls** 5→10, with 100, 1000, 10^4 and 10^6 all lower. |
| `k` | the integrand is **k-independent** once `1/k < p*`; `k` only gates admissibility. |

**And the `r = 1` exclusion is not fragile.** It would first become admissible
at **`k = 498`**, which is **1.95x the largest alphabet the standard permits**,
and `k <= 256` is a constraint of §3.1.1 rather than a tunable.

**So `r = 2` is the GENUINE BOUNDARY of the admissible domain, not merely the
smallest value tried.** `C22a`'s attainment point is justified on both axes, and
an independent computation over a domain defined from the mathematics
reproduces `K` to five significant figures **at exactly the recorded point**.

**`C22a`'s STATUS: still MEASURED, not PROVED** — monotonicity in `r` and in
large `N` is established by **scan**, not analytically, and `K` remains a
supremum over a finite grid. **What changed is that the gap `F02` named is
CLOSED**: both factors of the product now have an attainment argument, where
before only `c` did. The comment block in `entropy_floor.py` is rewritten to
say so, and `WV-2`'s withdrawal of the *supremacy* claim **stands**.

**The twelve-point refusal stays in the record.** `OC-120`'s probe at
`ldomain = 1/2` was refused at all twelve points — `target not bracketed` —
because the root lay below the domain floor there. That refusal is why this
entry exists: a less careful probe would have returned numbers that looked like
a replication.

### Item 2 — the asymmetry removed, deliberately

| centring | catches upward | catches downward | ratio |
|---|---|---|---|
| pooled **population** centre 0.854221 | +0.021037 | −0.009175 | **2.29x downward** |
| **corpus** mean at the pin 0.848290 | **+0.015106** | **−0.015106** | **1.00x** |

**The old bound was 2.29x more sensitive DOWNWARD — the conservative
direction — leaving the permissive direction the loosely-guarded one.** For an
entropy instrument that is backwards, and an asymmetry favouring the permissive
direction must not be incidental.

**The question this check now asks: "has this tool drifted from its established
behaviour on these pinned bytes."** That is a regression question, which is the
job it has in a regression suite. It does **not** ask "does this tool agree with
the population of clean streams" — a different question, and the one that
produced the asymmetry. Control: `mean=0.848290 centre=0.848290 tol=0.015106
n=25`, Compression 24/25.

**And what the tolerance costs, stated in the check**: the 25 streams are
digest-pinned and seed-regenerated, so the corpus mean is **deterministic to
~1e-13** locally and ~1e-9 across the two platforms. A tolerance of 0.0151 is
six to eight orders looser than that. **It will never false-fire and will miss
any drift below 0.015** — a gross detector by construction. A ~1e-9 bound would
catch real estimator changes and still clear the platform delta; **not adopted**,
because that redesigns what the check asserts.

### Item 3 — the mutation hazard closed, three ways

**The battery had NO TRAP AT ALL**, which is why a kill could leave a live
mutation. Now: `MUTATING` tracks the file under mutation and
`trap 'restore_mutating' EXIT HUP INT TERM` restores it on **every** exit path.

**`cpp/selftest/regression-constants.sh`** is new, runs **LAST** in the suite,
and asserts that no mutated constant survives. It **compares values against
recorded ones rather than searching for a marker**, because every mutation these
batteries perform substitutes one numeric literal for another and **leaves no
marker at all** — a marker search would pass trivially. It **imports** the floor
oracle rather than grepping it, so a renamed symbol or a syntax error fails here
instead of passing silently, and it refuses if fewer than 7 constants were
actually compared (`SHAPE-03`).

**Verified by breaking it, with the exact mutation that survived the kill:**
```
  C22C 1e6 compression HAS BEEN CHANGED   recorded 3.3599e-3, found 0.00337
  regression-constants: FAIL (1)                                    exit 1
  ... after `git checkout --`:
  regression-constants: PASS (7 floor constants + the manifest)      exit 0
```

**It is deliberately LAST and out of alphabetical order**, because
`run-all-checks.sh` runs the inventory in **file order** and this must run after
anything that could leave a mutation. The rationale is recorded **in the
inventory** so nobody sorts it back to the front.

**And that exposed a second defect**: `regression-docs.sh` counted the inventory
with `grep -c ''`, i.e. **lines, not scripts**, so the first comment block ever
added to that file inflated the count by five and failed the check. Fixed to
count non-comment, non-blank lines.

**The operational rule is guide rule 15**: a mutation battery runs in the
foreground, on a clean tree re-checked per arm, and restores on every exit path
— placed where a future session reads it before starting one.

### Item 4 — the `O_EXCL` NOT RUN ELIMINATED rather than left untested

The fallback is **removed**. If the random source cannot be read, the write is
**refused** with the reason named, instead of falling back to
`r2 = (attempt * 2654435761) ^ r1` — which at attempt 0 is `0 ^ r1 = r1`
exactly, making the suffix `.tmp.<r1><r1>` with
`r1 = time(NULL) ^ (getpid() << 16)`, fully derivable from the clock and the
pid. **That was the one condition in which `O_EXCL` was load-bearing, and it no
longer exists.**

`EA_TEST_RANDOM_SOURCE` exists only so the refusal is testable — not an option,
not documented as one.

**Verified by observing it fail, on all three tools:**

| | exit | report | capture | stray temps |
|---|---|---|---|---|
| readable source (control) | **0** | written, `errorLevel 0` | — | — |
| **unreadable source** | **255** | **none** | **byte-identical** | **0** |

with stderr naming the reason. Six cases added to
`regression-output-aliasing.sh` — three refusals and three controls, so the
refusal cannot pass as "this tool never writes a report". **The item closes as
ELIMINATED, not untested.**

### Item 5 — the build warnings, read for the first time

```
  27 warnings across the three tools, before:
     19  [-Wvla-cxx-extension]          variable-length arrays, upstream style
      5  [-Wdeprecated-declarations]    all `sprintf` -- TestRunUtils.h:659,
                                        permutation_tests.h:303
      3  [-Wignored-optimization-argument]   one per tool, ALL -ffloat-store
```

**`-ffloat-store` was the ONLY silently-ignored flag**, and it had been in the
Makefile unconditionally for the life of this fork while Apple clang discarded
it on **every single build**, announcing so each time. **So any claim that this
fork controlled excess precision through that flag WAS NEVER TRUE on macOS.** It
was true on Linux/GCC, which honours it.

The flag is now **probed** — compiled against an empty translation unit and kept
only if the compiler does not complain — so it is still passed where it is
honoured and dropped where it is not. **Warnings 27 → 24**, and the three
ignored-flag warnings are gone.

**And a silently-ignored flag now FAILS the build**, so this cannot recur:
`-Werror=ignored-optimization-argument`, itself probed because only clang has
that warning name. **Verified by breaking it** — forcing `-ffloat-store` back in
gives
`clang++: error: optimization flag '-ffloat-store' is not supported
[-Werror,-Wignored-optimization-argument]`
and the build **fails** instead of warning.

**The GCC comparison stays NOT RUN**, with jsoncpp linkage as the reason. On
arm64 there is no x87 excess precision for the flag to suppress, so dropping it
is **expected** to change nothing — and that expectation is **not measured**,
because the build that would measure it is the one that cannot link.

### Item 6 — the two unreplicated constraints, named, and one of them was not sampled at all

**`OC-120`'s table was wrong about the first of them.**

| | what produced it | n | status |
|---|---|---|---|
| **`5.731 sigma`** (`outside-battery-check.cpp`) | **DERIVED** — Bonferroni over 100,000 lags at family-wise alpha 0.001 | — | **rule 14 does not apply.** The 25 clean streams were its **validation**, not its source: max \|z\| 5.01, mean 4.31, sd 0.25, zero exceedances. A threshold not built from a sample needs its derivation checked, not a second sample. |
| **`30.0x` spectral ratio** (same file) | **EMPIRICAL** — "1.48x the observed clean max of 20.2 over 25 clean streams" | **25** | **was genuinely unreplicated. NOW REPLICATED.** |

**The 30x threshold, against an independent sample** — 100 fresh draws,
seeds 920000+, clear of the 900000/910000 bases:

```
  n = 100   min 12.6   max 19.5   mean 14.51   sd 1.30   unreadable 0
  draws above the recorded clean max 20.2 :   0 of 100
  draws above the threshold 30.0          :   0 of 100
  margin recorded 30.0/20.2 = 1.49x   measured 30.0/19.5 = 1.54x
```

**The threshold survives, and comfortably**: it sits ~12 standard deviations
above the mean of a tight distribution (9 % coefficient of variation). Unlike
the Compression window, this one was **not** marginal.

**The probe failed first and the tool caught it.** Two of the first three draws
read `UNREADABLE`, because the stream generator was written inline as
`bytes(random.Random(seed).getrandbits(1) for _ in range(N))` — which
**constructs a new identically-seeded generator on every draw**, so every bit
came out the same. `outside-battery-check` refused it: *"degenerate input (zero
variance)"*. A probe fault, found by the subject's own guard rather than by me.

**And what an independent sample would add to the PARTIAL row: nothing.**
`known-platform-deltas.txt`'s eight rows are **deterministic for fixed bytes** —
re-running reproduces the same digits, so a second sample is a **repeat, not a
replication**. What is meaningful for a deterministic quantity is an independent
**implementation** (`OC-112`: 5 of 8 bit-identical), an independent **platform**
(`OC-113`: deltas shrink 8,600x and 27,500x on x86-64), or an independent
**computation of the true value** (`OC-116`: an 80-digit oracle placed both
inside the 53-bit envelope). **All three are done and none is a sample.** Rule 14
now carries that distinction explicitly, because demanding "an independent
sample" of a deterministic quantity is a category error that would look like
diligence.

### What this does NOT establish

- **`C22a` is still MEASURED, not PROVED**, and the floor's status is unchanged.
  The `r` and large-`N` monotonicity is a scan, not a proof.
- The `c22a_rscan` domain is **mine**, derived from the code's `1/k` assertion
  and §3.1.1's symbol widths. If the original sweep's `ldomain` meant something
  else, this answers a different question than the one that produced `K` — the
  agreement to 1.00001x is the evidence that it does not.
- **24 build warnings remain** (19 VLA, 5 `sprintf`). Neither is a silently
  ignored flag; neither was addressed.
- The `-ffloat-store` finding is that the flag was **ignored**, not that
  honouring it would move any figure. **NOT MEASURED.**
- The spectral replication is **100 draws from the same two generators**. A
  physical source is not among them.
- Nothing reported upstream.

## OC-122 — the deterministic check that did not exist, and the 24 warnings classified

### Item 1, established first: NONE

**No enforced check compared this corpus's per-stream figures against recorded
values at numerical tolerance.** The inventory of what does exist:

| check | tolerance | what it covers |
|---|---|---|
| `compareresults.pl` via `selftest` | `1e-10` | the **11 NIST datasets** under `bin/` |
| `pin-check.sh` | `RELTOL=1e-9` | **one** value, `ringOsc-nist.bin` — a NIST dataset |
| `known-platform-deltas.txt` | `1e-9`, 8 rows | the NIST datasets again |
| `outside-battery-corpus.txt` | — | the corpus's **BYTES**, by digest |
| the four pinned figures `8538.7 59.938 40.21 0.8546` | — | **`grep -q` that the string still appears in `ORCHESTRATOR-CHECKS.md`** — a documentation-citation check, not a recomputation |

**So the figures were pinned nowhere.** And the predicted gap is real, measured
on the corpus's own 25 values with a uniform `+0.005` shift:

```
  window  [0.7700, 0.9667]  PASSES
  mean bound +/-0.015106     PASSES  (mean 0.853290, offset exactly 0.005000)
  pin-check                  UNAFFECTED -- different file
  corpus digests             UNAFFECTED -- the bytes did not change
```

One qualification the owner's framing did not include, and it matters: a change
in `ea_non_iid` **would** be caught by `selftest` at `1e-10` — **on the eleven
NIST datasets.** The gap is specific: a change confined to a path these 1-bit
MT/SHA streams exercise and the NIST set does not would pass everything.

### The gap closed

`cpp/selftest/outside-battery-figures.txt` records all **25** clean streams as
`<stream> <binding-estimator> <figure>` at 17 significant digits, measured on
Darwin arm64, with the binder named so a change in **which** estimator binds is
visible too. Compared at **`1e-9` relative** — `pin-check`'s `RELTOL` and the
platform manifest's per-row allowance — because the prediction estimators differ
between the two supported platforms by up to `3.66e-10` (`OC-112`) and a tighter
bound would false-fail on x86-64. Measured headroom on one platform: ~`1e-13`,
so roughly four orders. An absent figures file is a **refusal**, not a skip.

**Verified by observing failure**, with the perturbation the owner specified:

```
  perturbed mt00 by +1e-6:  0.8470166039320538 -> 0.8470176039320538
  FIGURE DRIFTED on mt00    rel 1.181e-06 > 1e-9      regression-outside-battery: FAIL
  restored                                             regression-outside-battery: PASS
```

**And the check caught two defects in itself before it caught anything else.**

1. **Six decimals, not seventeen.** The script ran `ea_non_iid -v` and parsed
   the verbose-1 summary — `Compression Test Estimate = 0.847017` — so **all 25
   streams reported `DRIFTED` by ~`1e-7` on the first run, from display
   quantisation alone.** A check cannot be tighter than the number it reads.
   Switched to `-v -v` and the `min entropy = ` lines at 17 digits, which is the
   form the recorded file uses.
2. **My own figure generator was truncated by a pipe.** `mkfig.sh | tee | head -8`
   SIGPIPE'd the generator at 8 of 25 streams. The recorded-figure file would
   have been short and the check would have refused 17 streams for having no
   recorded value. **The same SIGPIPE fault this record has catalogued four
   times, committed again, against my own script.**

### Each check's honest job, in the code

| check | job | status on the pinned corpus |
|---|---|---|
| **per-stream figures at `1e-9`** | **deterministic regression** — sees any behavioural change | **ENFORCED.** This is what a digest-pinned corpus is for. |
| the band `[0.7700, 0.9667]` | gross-failure detector from 600 **fresh** draws | **informational.** Subsumed, by six orders. |
| the mean bound `+/-0.015106` | population shift detector | **informational.** Subsumed. |
| the Compression share floor 80 % | fresh-draw acceptance | **informational.** Subsumed. |

The three statistical checks still compute and print, labelled
`[fresh-draw criterion, not enforced]`, and **no longer fail the suite**. They
are the right acceptance criteria for a fresh-draw campaign — `n = 600`, method
in `reproducers/compression-window-tail.sh` — and **enforcing a statistical band
against deterministic input is the same category error as demanding an
independent sample of a deterministic quantity, inverted.** The suite now reports
`ENFORCED 25/25 figures match at 1e-9 rel`.

### Item 2 — the 24 warnings classified, and all are bounded

**19 VLA warnings resolve to FIVE distinct sites**, repeated across the three
tools. **Every one is sized by the ALPHABET, none by the sample count or the
file length:**

| site | declaration | size | bytes at the maximum |
|---|---|---|---:|
| `non_iid/compression_test.h:104` | `int64_t dict[alph_size]` | `alph_size` | 2,048 |
| `non_iid/multi_mcw_test.h:13` | `long win_cnts[NUM_WINS][alph_size]`, `win_poses[...]` | `4 x alph_size`, twice | **16,384** |
| `shared/most_common.h:9` | `long counts[alph_size]` | `alph_size` | 2,048 |
| `shared/utils.h:503` | `int symbol_map_down_table[max_symbols]` | `1 << word_size` | 1,024 |
| `shared/utils.h:690` | same | `1 << word_size` | 1,024 |

**The bound is verified on both paths, not assumed:**

- **command line:** all three mains refuse outside 1–8 —
  `!parse_unsigned_decimal(argv[1], inint) || inint < 1 || inint > 8`.
- **inferred:** `utils.h:466` is `for(i=8; (i>0) && ((datamask & curbit) == 0); i--)`
  over a **`uint8_t`** OR-reduction, so it **starts at 8 and counts down** —
  `word_size <= 8` by construction.
- `alph_size` is then **counted up** over `max_symbols = 1 << word_size <= 256`
  entries, so `alph_size <= 256`.

**Largest VLA in the supported tools: 16 KB of stack. No input-derived VLA
exists, so there is no stack-overflow exposure from this class, and nothing is
repaired.**

**The 5 `sprintf` warnings are TWO distinct sites** (the rest are the `#include`
lines that pull them in):

**`iid/permutation_tests.h:303`** — destination is **heap**:
`new char[(size_t)(floor(log10(max_symbol))+2.0)*sample_size+1]`, written
`"%u "` per element from a `uint8_t`.

- **The sizing is exact**, not generous: `max_symbol = 255` gives
  `floor(log10(255))+2 = 4` and `"255 "` is 4 chars; `max_symbol = 1` gives 2 and
  `"1 "` is 2. It depends on `data[i] <= max_symbol`, which holds because
  `max_symbol` is `dp->maxsymbol`, the maximum over the same array.
- **The degenerate case is `max_symbol = 0`**, where `log10(0) = -inf` and the
  cast is undefined. **It is unreachable, doubly.** Measured: a 1,000,000-byte
  all-zero file gives `ea_iid` **exit 255** —
  *"Symbol alphabet consists of 1 symbol. No entropy awarded"* — before the
  permutation tests run. And `compression()` itself carries
  **`assert(max_symbol > 0)`** at line 292.
- **Largest safe input: any, at any size.** The buffer scales with
  `sample_size`, so it is a heap allocation that grows with the file rather than
  a fixed buffer that overruns.
- **The one caveat, already on record:** `assert` vanishes under `-DNDEBUG`,
  which no supported target sets and which `C09` already records as a hazard
  class with a measured heap-buffer-overflow at `markov_test.h:48`.

**`shared/TestRunUtils.h:659`** — `sha256_hash_string` writes
`sprintf(outputBuffer + i*2, "%02x", hash[i])` for exactly
`SHA256_DIGEST_LENGTH = 32` iterations: offsets 0..62, two chars each, NUL at 64,
so it **requires 65 bytes**.

- **Not input-derived at all** — a fixed 32-iteration loop over a digest.
- **Its only caller is `conditioning_main.cpp:521`**, with
  `char hash[2*SHA256_DIGEST_LENGTH+1]` = **exactly 65**.
- And `ea_conditioning` is **not one of the three supported programs** —
  `make all` builds `ea_non_iid ea_iid ea_restart`, which `regression-docs.sh`
  asserts. **So this call site is not reachable from the supported product at
  all**; the warning appears only because the definition is compiled.

**Split: 5 of 5 VLA sites constant-bounded at 256; 2 of 2 `sprintf` sites exactly
sized with their degenerate case unreachable. Nothing repaired, because nothing
input-derived can be reached.**

### What this does NOT establish

- The figures are recorded **on Darwin arm64**. The x86-64 run will exercise the
  `1e-9` tolerance against the platform delta for the first time **in CI**; if
  any row exceeds it there, that is a finding and the tolerance must not simply
  be widened.
- The deterministic check covers the **25 clean streams**. The 5 defect streams
  and the blindspot case have no recorded figure.
- The VLA classification is **by reading the declarations and verifying the
  bounds**, not by fuzzing. A 16 KB stack frame is fine on a default 8 MB stack
  and was not tested against a constrained one.
- The `sprintf` analysis covers **reachability from the three supported tools**.
  `ea_conditioning` is out of scope and is where the only 65-byte buffer lives.
- Nothing reported upstream.

