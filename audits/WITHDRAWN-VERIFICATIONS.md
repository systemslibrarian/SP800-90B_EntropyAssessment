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

## What this file does not do

It does not list **corrections** — a figure that was wrong and is now right
belongs in the chronology, not here. `OC-49`'s 683→684 and `OC-59`→`OC-62`'s
compression-versus-collision are corrections of *values*, not withdrawals of
*verifications*, and `OC-86` later turned the second into a verification that
now holds. The distinction is whether the thing withdrawn was a claim to have
checked.
