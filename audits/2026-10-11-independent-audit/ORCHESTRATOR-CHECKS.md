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
