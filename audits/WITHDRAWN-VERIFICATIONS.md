# Withdrawn verifications

A **verification** is a claim that something was *checked*, as distinct from a
claim about what the thing *is*. When a verification is withdrawn, the thing it
was about does not automatically become wrong — but it stops being *verified*,
and anything that leaned on the verification leans on nothing.

This file exists because two verifications were withdrawn in the same week, and
a withdrawal recorded only in the entry that performed it is a withdrawal nobody
finds. **A withdrawn verification is recorded as withdrawn, with its date and
its reason** — and it sits beside the thing it was about, not only in the
chronology.

Every entry carries five fields, and `regression-docs.sh` fails if one is
missing: **CLAIM**, **WITHDRAWN** (date and the entry that did it), **REASON**,
**WHAT NOW STANDS**, and **WHAT LEANED ON IT**. The last is the one that is easy
to omit and the only reason the others matter.

---

## WV-1 — `C23`'s cutoff verification

- **CLAIM.** `regression-restart.sh` printed
  `C23 both cutoffs match the exact oracle: 32 H_I values x 2 columns (0.25 .. 8)`,
  asserting that the production cutoffs had been checked against the exact
  oracle at 32 values of `H_I`.
- **WITHDRAWN.** 2026-10-21, `OC-75`.
- **REASON.** The claim line was printed from an **empty loop**: `C23_PINS` held
  no entries, so nothing was compared and the sentence was produced
  unconditionally. The fifth vacuous member found in the enforced suite.
- **WHAT NOW STANDS.** `C23_PINS` carries 32 oracle-derived triples, the check
  refuses fewer than 32, and the claim line is **derived from the count** so an
  emptied list prints `0 comparisons made` instead of the old sentence.
- **WHAT LEANED ON IT.** `XR-13`'s conclusion that `C23` changes no verdict at
  width 1 — which now rests on `OC-49`'s boundary analysis instead, not on this
  check. See also [`F12`/`OC-85`](2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md),
  where the same conclusion's *premise* had to be replaced separately.

---

## WV-2 — `C22a`'s supremacy, and with it the floor's certification

- **CLAIM.** `OC-63`: that `C22a`'s constant is a **supremum** rather than a
  lower bound on one, because its argmax is interior in every swept axis and
  stayed bit-identical at 0.4991 when the last arbitrary axis was extended nine
  orders — and therefore that `eps_f <= c (N+1) 2^-52` is a **bound** and the
  floor's terms are all bounds at width 1.
- **WITHDRAWN.** 2026-10-21, `OC-78` (finding `F02` of the second independent
  AI audit).
- **REASON.** **The subtracted constant `8.08e-15` is a PRODUCT OF TWO GRID
  MAXIMA, `c × K`, and `OC-63` examined only `c`.** The second factor,
  `K = 1.6189e-14`, is attained at `N = 5, r = 2` — and `r = 2` is the **first
  value in its swept list** `[2, 3, 4, 5, 6, 8, …]`. `K` is largest where
  `|f'(p*)|·p*` is smallest, the sweep's own printed model puts that minimum at
  `r = 2`, and whether the true infimum lies at `r = 2` or at `r = 1` was never
  examined. Rule 9 applies to that factor and was never applied to it. The
  margin is also thin: the sweep's worst realised inflation reaches **92.8 %**
  of the ceiling it is supposed to bound.
- **WHAT NOW STANDS.** `C22a` is **MEASURED**, not PROVED. The floor takes the
  weakest status of its terms and prints `MEASURED FLOOR (C22a)`, naming the
  term that holds it there. **No figure changed**; what changed is the status
  claimed for it. Settling it means extending the `r` axis below 2 and the `N`
  axis below 5, or replacing `K`'s grid maximum with an analytic infimum for
  `|f'(p*)|·p*` — the sweep already prints a model, `0.01005·(r − p/q)`, as the
  starting point. **Not attempted.**
- **WHAT LEANED ON IT.** The term **"certified floor"**, now **retired**
  (`OC-78`): no reading of the entropy floor is certified, and
  `regression-docs.sh` fails both on the phrase without a retirement marker and
  on any **assertive** use of it that is not inside quotation marks. Also
  `CLOSING-INVENTORY.md`, which said *"both floor readings are certified
  floors at width 1"* — corrected there as false rather than as out of date.

---

## Superseded verifications — `SV-1` … `SV-6`

**The owner asked for the six "frozen class-1" dead-guard flags to be recorded
here as WITHDRAWN verifications, on the reasoning that freezing a script does
not retire the figures it produced. The measurement in `OC-98` says otherwise,
so recording them as withdrawn would be recording something false.**

Each of the six was re-read **in its surroundings** rather than classified by
what the construct does. **None of the six verifications is broken, so none is
withdrawn.** Two are closed as **SUPERSEDED** — the mechanism the detector
flagged is indeed dead, but the figure has **independent support**, which is the
owner's own stated condition for closing as superseded. Four are closed as
**VERIFICATION STANDS** — the guard is armed and the flag was the detector's
error or mine.

They are listed here, in the register, because *"a withdrawal recorded only in
the entry that performed it is a withdrawal nobody finds"* applies equally to a
**non**-withdrawal: a reader who was told six verifications were in doubt needs
to find the resolution in the same place.

Every entry carries the same five fields.

### `SV-1` — `issue272/repro.sh:11`, `:15`, `:18` — **SUPERSEDED**

- **CLAIM.** That upstream issue #272's mutant-survival figures were verified:
  that deleting the `n × H_bitstring` term and deleting `H_original` from the
  final assessment each leave `Assessed min entropy` **unchanged** on
  `normal.res`, `truerand_8bit.res`, `ringOsc-nist.res` and
  `biased-random-bits.res`.
- **SUPERSEDED.** 2026-10-25, `OC-106` (triage measured in `OC-98`).
- **REASON.** The flagged lines are `grep -h '^Assessed min entropy' …` in
  **statement position** (dead-guard pattern C) with no `set -e`. Their exit
  status is unread, so the *guard* is dead: a `grep` that matched nothing would
  not stop the script.
- **WHAT NOW STANDS.** **The figures, on independent support.** Those `grep`s
  do not verify anything — they **print into the transcript that IS the
  evidence**, and the transcript is recorded. A silent failure yields *visibly
  absent output*, not a wrong number, so the reader of the transcript is the
  check. The same conclusion is independently supported by
  `SP 800-90B aggregation blind spot`: the measurement that **a 40σ defect
  leaves the min-entropy figure unchanged** because Compression binds, which is
  the same phenomenon these mutants demonstrate, reached by a different route.
- **WHAT LEANED ON IT.** The claim that nine of the ten non-IID estimators are
  decorative at these widths, and the decision to store a per-estimator
  breakdown against a per-device baseline rather than rely on the aggregate.
  **Both still stand**, on the transcript and on the independent measurement.
  **What does NOT stand:** the figures would not be re-verified by *re-running*
  `repro.sh` unattended, because nothing in it would fail. Re-running it
  requires a human reading the output.

### `SV-2` — `widths.sh:6`, `:13`, `:14` — **SUPERSEDED**

- **CLAIM.** That the literal-path and bitstring-path figures for widths 2–8
  were verified against the C++ literal reference, via `cmpc.py`.
- **SUPERSEDED.** 2026-10-25, `OC-106`.
- **REASON.** Identical shape to `SV-1`: `python3 cmpc.py …` in statement
  position, status unread, no `set -e`. The fixture generation at `:6` is the
  same shape.
- **WHAT NOW STANDS.** The recorded transcript, for the same reason. Each
  `cmpc.py` call **prints its comparison**, so an absent comparison is visible
  as an absent line.
- **WHAT LEANED ON IT.** The width-2..8 literal-versus-bitstring agreement.
  **Note the asymmetry with `SV-1`:** these figures have **no second
  independent support** — no other instrument in this repository recomputes
  them. So `SV-2` is superseded by its transcript **alone**, which is weaker
  than `SV-1`, and is recorded as such.

### `SV-3` — `repairs/2026-10-09-ind-02/rerun.sh:45` — **VERIFICATION STANDS**

- **CLAIM.** That `ea_iid -i` on period-two data exits 1 with `errorLevel 2`,
  `IID false`, `assessmentComplete true` and **no** `hAssessed` — the `ind-02`
  report-shape claims.
- **SUPERSEDED.** Not superseded and not withdrawn. 2026-10-25, `OC-106`.
- **REASON THE FLAG WAS WRONG.** **`set -e` is active at that line** — `set -eu`
  at `:3`, `set +e` at `:40` for the measured command, `set -e` restored at
  `:43`, and the assertion `test "$period_status" -eq 1` is at `:45`. A failing
  assertion aborts. **The detector's own `has_set_e` field said `True` and its
  detail said `set -e present`. I classified the flag without reading the field
  that was answering the question.**
- **WHAT NOW STANDS.** All of it. The guard is armed.
- **WHAT LEANED ON IT.** The `ind-02` repair's acceptance. Unaffected.

### `SV-4` — `audits/2026-10-09-independent-audit/rerun.sh:71` — **VERIFICATION STANDS**

- **CLAIM.** That the TruePad unattested-tools comparison ran and its result was
  recorded.
- **SUPERSEDED.** Not superseded and not withdrawn. 2026-10-25, `OC-106`.
- **REASON THE FLAG WAS WRONG.** **The next line is
  `echo "$?" >"$out/truepad-unattested-tools.status"`** — the status is captured
  to a file the audit reads. The detector's `STATUSREAD` matcher does not
  recognise that form, so this is a **false positive**, the seventh instance of
  that one blind spot.
- **WHAT NOW STANDS.** All of it.
- **WHAT LEANED ON IT.** The TruePad unattested-tools count. Unaffected.
  **`~/repos/TruePad` was read by that script when it ran and has not been
  modified by any of this work.**

### `SV-5` — `.github/scripts/windows-facts.sh:719` — **VERIFICATION STANDS**
### `SV-6` — `.github/scripts/windows-facts.sh:732` — **VERIFICATION STANDS**

- **CLAIM.** That the Windows platform-facts tally is correct — the tally behind
  **`C18` CONFIRMED** (LLP64 overflow, NaN threshold, LRS fails whatever the
  data) and **`C24` NEW** (no report can be written on Windows).
- **SUPERSEDED.** Not superseded and not withdrawn. 2026-10-25, `OC-106`.
- **REASON THE FLAG WAS WRONG, TWICE OVER.** First, *"reachable only from
  Windows CI"* was **my assumption, not a property of the script**: the tally is
  pure `bash` reading two files and runs anywhere. Tested here, three paths —
  empty verdict log → exit 2 *"TALLY REFUSED"*; an unexpected `GATE FAIL` →
  exit 1; expected failures only → exit 0. Second, the flagged pipes can only
  fail silently if `$V` is unreadable, and **`$V`'s existence and non-emptiness
  are preconditions checked at `:703`**, whose comment reads *"A tally over
  nothing is not '0 failed'; it is 'nothing ran'."*
- **WHAT NOW STANDS.** All of it.
- **WHAT LEANED ON IT.** `C18` and `C24`, both awaiting an owner decision.
  Unaffected.

### The count, with the identity of what it counts

**6 flags examined; 0 verifications withdrawn; 2 superseded (1 with a second
independent support, 1 on its transcript alone); 4 verifications stand (3 the
detector's or my own false positives, 1 a guard that was armed all along).**

---

## What this file does not do

It does not list **corrections** — a figure that was wrong and is now right
belongs in the chronology, not here. `OC-49`'s 683→684 and `OC-59`→`OC-62`'s
compression-versus-collision are corrections of *values*, not withdrawals of
*verifications*, and `OC-86` later turned the second into a verification that
now holds. The distinction is whether the thing withdrawn was a claim to have
checked.
