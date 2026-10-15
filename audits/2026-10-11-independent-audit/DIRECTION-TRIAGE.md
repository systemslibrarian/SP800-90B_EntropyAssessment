# Direction triage — the audit re-sorted by what a defect can do to a claim

Severity labels measure how bad a defect feels. They do not measure which way it
pushes a number, and that is the only property that matters to a secrecy claim.
Under the severity scheme, `restart-12` — a restart cutoff more permissive than
the standard's, which can let a source pass a test it should fail — is filed as
**Info** inside a **Low** cluster called `misc-reporting`, while `C07`, which
can only ever refuse to produce a figure, is **High**. That ordering is
backwards for the goal, so this file re-sorts the audit on direction.

## The three directions

- **PERMISSIVE** — can make a source look better than it is: raise an estimate,
  accept data the standard rejects, or let an assessment pass that should fail.
  **These threaten the claim itself.**
- **CONSERVATIVE** — refuses, aborts, or lowers a figure. Costs performance and
  can block the goal; cannot inflate it.
- **NEUTRAL** — misreports a diagnostic, cosmetic, documentation.
- **UNKNOWN** — direction cannot be settled without verifying. Treated as
  *higher* priority than conservative, not lower: an unknown direction is an
  unquantified risk to the claim.

## Counts

| Direction | Clusters | Verified | **Unverified** |
|---|---:|---:|---:|
| **PERMISSIVE** | 8 | 5 | **3** |
| **UNKNOWN** | 5 | 0 | **5** |
| CONSERVATIVE | 3 | 2 | 1 |
| NEUTRAL | 7 | 1 | 6 |
| **total** | **23** | **8** | **15** |

## The risk register — permissive and unknown, unverified

This is the list that matters. Nothing else in the audit comes close.

| Cluster | Direction | Why it threatens the claim |
|---|---|---|
| **`C23` / `restart-12`** | PERMISSIVE | The §3.1.4.3 restart cutoff is obtained by simulation and claimed to sit **at or above** the exact binomial cutoff — H_I=1: spec 570 vs tool 571-573; H_I=7: spec 23 vs tool **27**. A more permissive cutoff accepts restart data the standard rejects. The restart half is one of the two halves of the assessment. **Top item.** |
| **`C22`** | PERMISSIVE | `ZALPHA` is the exact 0.995 quantile where the spec text prints 2.576, which by the finder's own description "raises every prediction estimate". "Magnitudes tiny" is their claim, not a measurement. |
| **`C09`** | PERMISSIVE | `ea_conditioning -i` applies no 1,000,000-sample rule, no single-symbol and no width check: a 125,000-byte file is assessed with `errorLevel 0` and no non-compliance flag. Accepts data the standard rejects. |
| **`C14`** | UNKNOWN → leans permissive | A stale `-o` file survives an error path. The consumer reads a *previous* run's number; whether that is higher or lower depends on history, so the direction is unknowable in general — and a stale number that looks valid is the permissive case. **Crosses into TruePad's desktop harness.** |
| **`C16`** | UNKNOWN (mixed) | The demonstrated instance is an *under*estimate (hAssessed 0.7264 vs 1.7747), so conservative. But `H_I` is parsed with `strtod` and accepts hex floats and leading whitespace, and `H_I` sets the restart validation threshold `H_I/2` — a mis-parsed **lower** `H_I` makes validation *easier* to pass. Mixed direction in one cluster. |
| **`C20`** | UNKNOWN | Data races on `test_status[]` and the `completed` counter in the `ea_iid` permutation region. If a race can flip a failed test to passed, it is permissive. Claimed benign by monotonicity — unverified. |
| **`C21`** | UNKNOWN (mixed) | Contains `fesetround(FE_TOWARDZERO)` left in effect during the h' battery (either direction), `-1` sentinels folded into `h'` giving `h_out = -256`, and out-of-bounds reads in `periodicity()`/`covariance()` — which are **permutation statistics**, so corruption there could flip an IID verdict. |
| **`C18`** | UNKNOWN | LLP64-only integer overflows (`long` is 32-bit on Windows). Not reachable on the platform in use, so not urgent — but the direction of a wrapped `N` in `n_choose_2` is undetermined. |

## Verified permissive — already established, listed for completeness

| Cluster | Measured direction |
|---|---|
| `C03` | **+42.59 %** overestimate: `ea_iid` exits 0 with `errorLevel 0`, `"IID": true` and `hAssessed 0.00435833449306757` on a source whose chi-square test failed, where the mandated non-IID track gives `0.003056517595468432`. Open on `master`. |
| `C06` | `h_out` **7.1552** against a 7-bit information ceiling (OC-1). Inherited, unrepaired on both branches. |
| `C01` | Two-sided; demonstrated overestimate **+3.69e-4 bit**, and the sign is chosen by the data, so a submitter who shapes the stream picks it. |
| `C02` | The machine-readable `hAssessed` carries `word_size × h'` (up to 8×) where console, usage text, README and §3.1.5.2 give `h'` per bit. Prior decision stands (F23); not reopened. |
| `C08` | Permissive **about the instrument rather than about a figure** — the harness accepts a 0-byte reference as a pass and excuses a 0.096-bit error by filename. It cannot inflate an estimate; it can let a build that inflates one ship. |

## Conservative — cost, not risk

| Cluster | Direction |
|---|---|
| `C07` | Fail-closed `SIGABRT`, no JSON. Denies the IID track and forces the lower `ea_non_iid` figure. **Blocks reaching 0.5 bit/bit; cannot fake it.** Verified. |
| `C05` | `assert(k_effective <= k)` abort, no report. Upstream #195, open since 2022. |
| `C11` | C-01 scalar `delete` of an array — observed as an abort under ASan. Classified conservative on the observed behaviour; heap corruption is not in principle direction-bounded, which is why it stays on the list. |

## Neutral

`C04` (verdict identical to a spec-correct implementation — verified), `C10`,
`C12` (memory-safety, but the figure is unaffected), `C13`, `C15`, `C17`
(last-digit), `C19`.

## What changes because of this re-sort

1. **`restart-12` is promoted from Info to the audit's top unverified item** and
   is no longer filed under `misc-reporting`.
2. **`C22`'s "tiny" is now a claim to be measured**, not a reason to deprioritise.
3. **Unknown direction raises priority.** Five clusters cannot be placed without
   verification, and three of them (`C14`, `C16`, `C21`) contain a path that is
   permissive on inspection.
4. **`C07` drops in priority for the claim** while staying high for usability: it
   is the single largest obstacle to *obtaining* a figure and no threat at all to
   the figure's integrity.
5. `C08` is permissive one level up. It cannot move an estimate, but it is the
   reason to distrust every "the suite is green" statement about the tool that
   produces estimates — which is the rule "suspect the instrument before the
   thing measured" in its strongest form so far: the harness accepts a **0-byte
   reference file** as a pass.

---

# Status update — 2026-10-14, after verifying C23, C22's ZALPHA item and C14

Three register entries moved. The counts above are the triage as first written;
these are the changes.

| Cluster | Was | Now |
|---|---|---|
| **`C23` / `restart-12`** | PERMISSIVE, unverified, top of the register | **PERMISSIVE, VERIFIED** (`OC-7`). The standard specifies a deterministic binomial tail and the tool takes a Monte Carlo order statistic; the gap is systematic at every H_I sampled, +1 to +6 counts, effective type-I error 2.3× to 340× smaller than intended. Acceptance of spec-rejected data demonstrated at H_I=7 for X_max = 24 and 25 with a working positive control at 28. **Still the audit's top finding**, now with numbers. The "deliberate implementation choice" defence is refuted by §3.1.4.3's own text. |
| **`C22`** | PERMISSIVE, unverified | **Partially verified.** The `ZALPHA` item is measured (`OC-8`): worst +3.80e-06 bit, permissive in sign, and **not a defect** — `2.576` is the standard's rounding of the quantile the tool uses correctly, which is prior `F07`. The rest of the cluster (`P_local` quantisation, the `x` recurrence, `P_global'` at `N == 1`) is unverified and stays on the register. |
| **`C14`** | UNKNOWN, unverified | **One member verified** (`XR-01`, `CROSS-REPO-FINDINGS.md`): the stale `-o` file survives byte-identical, exit 255, and a consumer reading the file sees `errorLevel 0` with a complete figure. Direction confirmed as history-dependent: the stale number may be higher or lower than the truth, so the cluster stays UNKNOWN. Seven members unverified. |

## Two new findings, outside the cluster scheme

| ID | Direction | Summary |
|---|---|---|
| **`REPRO-01`** | **architecture-dependent** | The same input aborts on arm64 (`W > 1022`) and is assessed on x86-64 (`W > 16382`). Conservative on one host, permissive on the other, and the JSON records nothing about which bound applied. This is the only finding whose direction is not a property of the defect. |
| **`REPAIR-BLOCK-01`** | NEUTRAL for the figure | The repair branch reports the `long double` underflow as `** Failed length of longest repeated substring test` — an arithmetic limit presented as a statistical rejection of the operator's hardware. **Blocks the rebase.** |

## Revised register — permissive or unknown, still unverified

1. ~~**`C09`**~~ — **VERIFIED 2026-10-15** (`OC-9`), all four members. Permissive half confirmed: a **100-byte** file yields `h' = 0.6375933997245808448894` and `h_out = 163.22` with `errorLevel 0` and no marker, while `ea_non_iid` exits 255 on the same data. Also found: under `-DNDEBUG` — which no Makefile target sets but downstream packaging commonly adds — the shipped assert is replaced by a **heap-buffer-overflow READ** at `markov_test.h:48`, and `-c iid` exits **0** reporting `h' = -0`. Off the Chor–Goldreich path (raw per-source min-entropy is what the goal needs), so it threatens the figure only if a conditioner enters the chain.
2. **`C22`** remainder — PERMISSIVE. `P_local` quantisation and `P_global'` at `N == 1`.
3. **`C16`** — UNKNOWN, mixed. `H_I` via `strtod` sets the restart threshold `H_I/2`; a mis-parsed lower `H_I` is permissive, and `OC-7` now shows the restart sanity check is the wrong place to be adding slack.
4. **`C21`** — UNKNOWN, mixed. Out-of-bounds reads in `periodicity()`/`covariance()`, which are permutation statistics.
5. **`C20`** — UNKNOWN. Races on `test_status[]` in the permutation region.
6. **`C14`** remainder — UNKNOWN. Seven members.
7. **`C18`** — UNKNOWN, platform not in use.

`C16` rises in importance because of `OC-7`: the restart validation threshold
is `H_I/2`, `H_I` is user-supplied and parsed permissively, and the sanity
check guarding it is now known to be more permissive than the standard. Those
two defects compose in the same direction on the same test.

---

# CORRECTION 2026-10-15 — the NDEBUG re-classification, and the TruePad reachability test

## `C07` moves from CONSERVATIVE to PERMISSIVE

`OC-10` invalidates the classification this file originally gave `C07`. It was
filed conservative *because* `NDEBUG` is not set in `cpp/Makefile` — a claim
about a build, not about the code. Measured under `-O2 -DNDEBUG`:

| | asserts live | `-DNDEBUG` |
|---|---|---|
| `C07` site B, `lrsrep-2000.bin` | `rc=134`, no JSON | **`rc=0`, `errorLevel 0`, `"IID": true`, `hAssessed 0.995373734104443`** |
| `C07` site A, `bal125.bin` | `rc=134`, no JSON | `rc=0`, all tests pass, `hAssessed 6.79603697656858` (correct) |
| `C05` | `rc=134` assert | `rc=255`, clean refusal naming `X_max: 385` vs `X_cutoff: 316` |
| `C09` | `rc=134` assert | heap-buffer-overflow READ; `-c iid` `rc=0`, `h' = -0` |

Site B under NDEBUG is a **chain reporting its ceiling**: an underflow makes the
LRS test return *failure*, and `C03` discards test failures, so the run publishes
**0.9954 bit/bit** — above the project's 0.5 threshold — on data the tool could
not evaluate. Since the fork cannot assume `NDEBUG` is off downstream (nothing
sets, requires, documents or detects it, and `cpp/Makefile:31` *assigns*
`CXXFLAGS` so an overriding packager loses `-ffloat-store` too), the NDEBUG
column is the one to carry.

`C11` is also re-classified: its "abort" was only ever an ASan report.
`simulateBound` returned normally in all 27 `OC-7` runs and the `C05` runs, both
builds. **NEUTRAL with a memory-safety flag**, not conservative.

Revised counts: **PERMISSIVE 9** (was 8), **CONSERVATIVE 1** (was 3 — `C05`
remains, `C07` moved out, `C11` moved out), NEUTRAL 8, UNKNOWN 5.

## Reachability test — what TruePad actually consumes

Standing instruction, 2026-10-15: verify while useful to TruePad. A cluster is
worth verifying if a defect in it could change, suppress or inflate the
min-entropy figure per bit per source, the restart assessment, the health-test
verdicts, the exit statuses and output files the desktop harness reads, or the
memory safety of a tool TruePad invokes on user data.

### On-path, unverified — the remaining work, in order

| Cluster | Why TruePad reaches it |
|---|---|
| **`C16`** (chain) | `H_I` is user-supplied, parsed with `strtod`, and sets the restart validation threshold `H_I/2`. `OC-7` proved the sanity check guarding that same test is already more permissive than the standard. Two permissive defects on one gate — **chains outrank items**. |
| **`C22`** remainder | `P_local` quantisation and `P_global'` at `N == 1` are in the estimators that produce the min-entropy figure. |
| **`C20`** | Races on `test_status[]` in the `ea_iid` permutation region — a health-test verdict TruePad consumes. |
| **`C21`** (partial) | Only the `periodicity()`/`covariance()` out-of-bounds reads: they are permutation statistics, so on-path for a verdict and for memory safety on user data. The `ea_conditioning` members are **not**. |
| **`C14`** remainder | Seven members about exit statuses and output files — precisely what the desktop harness reads. `XR-01` is verified; the rest are not. |

### Set aside as unverified-because-unreachable

Recorded with the specific reason and what would put each back on the path.
**None of these has been checked and found fine. They have not been checked.**

| Cluster | Reason TruePad cannot reach it | What would make it reachable again |
|---|---|---|
| `C06`, `C09` (already verified), `C12`, and the `ea_conditioning` members of `C21` | TruePad does not ship `ea_conditioning`, and Chor–Goldreich two-source extraction consumes **raw per-source min-entropy**, not conditioned output, so `h'`/`h_out` enter no TruePad figure | TruePad adding a conditioning component to the chain, or any use of `h_out` as an input to the secrecy claim. `C06`'s `h_out 7.1552` against a 7-bit ceiling would then be directly on-path. |
| `C18` | LLP64-only: `long` is 32-bit on Windows, 64-bit on the macOS arm64 and Linux x86-64 builds in use | A Windows build of the tools, or any build where `sizeof(long) == 4` |
| `C17` | Last-digit platform divergence, ≤ 2e-14 bit — below any decision the 0.5 bit/bit threshold makes. **Note:** this is *not* the same as `REPRO-01`, which is a different-figure-or-no-figure divergence and is on-path | A threshold decision at a precision where 1e-14 matters, which the goal does not have |
| `C10`, `C13`, `C15`, `C19` | Diagnostics, `errorMessage` text, negative-zero presentation, documentation. None changes a figure, a verdict, an exit status, or memory safety | A consumer parsing `errorMessage` text or the sign of a zero as control flow — which `XR-01` shows is the kind of thing a harness does do, so `C15` would move on-path if TruePad branched on a figure's string form |
| `C04` | Verified NEUTRAL: the computed verdict is identical to a spec-correct implementation's on every `df < 1` input | Nothing; this one is closed, not set aside |
