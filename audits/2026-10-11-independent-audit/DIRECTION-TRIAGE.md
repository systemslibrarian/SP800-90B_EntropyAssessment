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
