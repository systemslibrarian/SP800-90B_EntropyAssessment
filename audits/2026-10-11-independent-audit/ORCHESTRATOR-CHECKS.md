# Orchestrator's own rechecks

Checks run directly by the coordinating session, independently of the finder
agents, on datasets the coordinator generated itself. They are recorded
separately so that the report's headline claims do not rest solely on a
subordinate agent's output.

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

**Verdict: the C03 mechanism does apply to the `-i` path. Source-confirmed;
the compliant execution was still running when this was written and is marked
below.** It **misreports** — it does not abort.

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

### Status of this check

- **Correct**: the mechanism is established from the source with no ambiguity —
  three booleans computed and never read, then an unconditional `errorLevel = 0`
  and `return 0`.
- **Verified**: not yet, for the compliant 1,000,000-sample case, and the
  reason is runtime rather than evidence. The first attempt
  (`mk55-1bit.bin`, `timeout 900`, `OMP_NUM_THREADS=2`) **timed out at
  `rc=124`** — but not before establishing that the dataset reaches exactly the
  state the demonstration needs:

  ```
  ** Failed chi square tests
  ** Passed length of longest repeated substring test
  rc=124   json=no
  ```

  So chi-square **fails** (one of the three Section 5 tests is negative) and the
  LRS test **passes** (site B of `OC-5` is not masking this case, which was the
  construction goal). It timed out inside the permutation battery, which
  `ea_restart -i` runs **twice** — once on rows, once on columns — at 10,000
  permutations each over 1,000,000 samples. The unconditional `errorLevel = 0`
  sits after that battery, so the decisive line was never reached.

  Re-launched with `timeout 7200` and `OMP_NUM_THREADS=4`. The short-matrix
  shortcut is unavailable: `ea_restart` mandates exactly 1,000,000 samples and
  `EA_ALLOW_SHORT_DATASET` does not bypass that check, as the refusal quoted
  above shows. There is no flag to reduce the permutation round count (`-s`
  controls the §3.1.4.3 simulation rounds, not the battery).
- The `"IID": true` constant is verified by execution, on an error path.

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
