# Cluster dispositions

Where a cluster's verification lenses disagreed, or where the result is a
disposition rather than a finding, the decision and its reason are recorded
here rather than left implicit in the report.

---

## C02 — `-c` reports `hAssessed` per symbol: **not reopened. Prior decision stands.**

### Disposition

`EXCLUSION-MAP.md:40` already records this as *reproduced and deliberately not
promoted*, filed under **F23**, and `audits/2026-10-09-independent-audit/REPORT.md:299`
states plainly: "The `hAssessed = n × h'` conditioned reporting issue is prior
F23 and was not promoted." `audits/2026-09-30/AUDIT.md:53` carries the original
observation and `FINDINGS-TRACKER.md:1056` carries F23 as an `UNCONFIRMED`
composite.

This round's two lenses disagreed about severity — the refutation lens argued
Low-to-Moderate misreport, the impact lens argued High at the low end. **A
disagreement between two lenses is not grounds to overturn a recorded
decision.** Both lenses agreed on the two facts that matter to the disposition:
nothing the tool computes is wrong, and the behaviour is not new. The prior
decision therefore stands unchanged, and this round contributes only the
promotion of F23 sub-claim (b) from `UNCONFIRMED` to **confirmed by
execution**.

No new finding ID is issued. No severity is assigned. F23 keeps its existing
disposition and its existing next action.

### Sub-claims filed as refuted

The refutation lens refuted or corrected six specific assertions made in
`output-automation-contracts-1`. They are recorded so the same claims are not
re-litigated by a future pass:

1. **Refuted, factual.** "`type` is empty and there is no mode field, so the
   only in-report discriminator is the free-text `commandline`." The report does
   discriminate the mode, through field presence: `hOriginal` is emitted iff
   `initial_entropy` (`non_iid_main.cpp:617-619` via `test_case_base.h:52-53`)
   and `hBitstring` iff `(alph_size > 2) || !initial_entropy` (`:612-614`). All
   four combinations of mode and width produce distinct field sets, so
   `hOriginal`'s absence identifies a `-c` run. The fair version of the
   complaint is that the discriminator is implicit, unnamed and undocumented —
   not that it is absent.
2. **Refuted, mis-located.** "The repair branch's `assessmentMode` is a start
   but is only on `IidTestRun`." It is a compile-time constant
   (`repair/cpp/iid/iid_test_run.h:21`, `json["assessmentMode"] = "IID"`) added
   for upstream #252. It carries no information about `-i` versus `-c` and
   would not disambiguate them on either tool. It is not "a start" on this
   problem.
3. **Overstated.** "If that value is then used in
   `h_out = min(Output_Entropy(…), 0.999·n_out, h'·n_out)` the conditioned-output
   entropy claim is inflated by the same factor." It cannot be, in general:
   `h_out` is a minimum of three terms, and the other two cap any inflation of
   the `h'·n_out` term. The risk is real; "inflated by the same factor" is not.
4. **Overstated.** `requirement_kind: specification requirement`. The quoted
   §3.1.5.2 text defines `h'`; it does not prescribe report fields. The defect
   class is misreport, with an overestimate only as a downstream consequence of
   a consumer error.
5. **Overstated.** "§3.1.5.2 multiplies `h'` by `n_out`, which is unrelated to
   the file's symbol width." They coincide whenever the operator packs the
   conditioned output at `word_size == n_out`, and in that case `word_size × h'`
   *is* the spec's `h'·n_out` term. The sound form of the objection is that the
   equality is an unstated assumption, and that `n_out` for a non-vetted
   conditioning component is usually far larger than the 8 bits/symbol the tool
   can represent.
6. **Overstated.** "At `-vv` the console itself switches to the per-symbol
   figure, so the same run presents two different numbers depending on
   verbosity." A `-vv` run prints, consecutively,
   `H_bitstring = 0.902880099395026`,
   `H_bitstring Per Symbol = 3.611520397580104`, and
   `Assessed min entropy: 3.611520397580104`. Both figures are present and the
   per-symbol one is labelled as such. The defect is the unqualified label
   "Assessed min entropy" on the per-symbol figure, not a verbosity-dependent
   substitution of the answer.

The one surviving substantive point, already covered by F23: the
machine-readable field named as the run's answer carries `word_size × h'` while
the console line, `print_usage` ("-c … Returns h' = min(H_bitstring)"),
`README.md:82` and §3.1.5.2 all give `h'` per bit.

---

## C04 — chi-square with `df < 1`: **partially refuted, downgraded to Low**

The refutation lens refuted the cluster's framing at high confidence, and the
correction is consequential enough to record in full, because the finding's
recommended repair would have introduced a defect.

**§5.2.1 says "do not apply the test", not "the test fails."** An unapplied
test cannot reject, and `p = 1` cannot reject, so the computed verdict already
matches the requirement. The only deviation is in the report text, about which
§5.2.1 says nothing.

**The claimed N-01 precedent is a misreading.** §5.2.3 says "If m is 1, the
test fails" — that is N-01's sentence. §5.2.1's sentence is deliberately
different. N-01's fail-closed treatment is not what this case lacks; it is what
this case must *not* have.

**The `IID decision` direction is refuted.** On master the chi-square boolean
gates nothing: with all three batteries Failed, `ea_iid` still exits 0 with
`errorLevel 0` and an `hAssessed` figure (measured 0.9375). `ea_restart`'s
verdict is `min(H_r, H_c)` against `H_I/2` only.

**The recommended repair is actively harmful on the repair branch.** Returning
false at `df < 1` would, at `iid_main.cpp:457-468`, set `errorLevel 2`, print
"IID test suite failed; no IID min-entropy estimate was awarded", and exit 1 —
on data SP 800-90B does not reject. Where the boolean does gate, the current
"not rejected" outcome is the correct one.

The fork had already rejected this on 2026-09-30 as spec-consistent. Disposition:
**Low**, reporting and transparency only — the report prints
`degrees of freedom = 0` or `-1` and says `Passed`, which is accurate about the
verdict and opaque about why. Recorded as spec-consistent, with the prior
rejection upheld.
