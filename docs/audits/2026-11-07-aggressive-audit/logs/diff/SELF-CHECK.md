# diff_driver --self-check

Written 2026-11-07T21:13:17-0500; harness sha256 6f7a21704487845217d17f3a3f5422711cf8055bab5ec966e35f554687241e2f.

Rule 7: a negative control is built by mutation of a passing artefact and the baseline is asserted accepted.  Rule 8: the self-comparison is the baseline.  Every row below must have observed == expected.

RESULT: PASS (14/14 rows)

| source | step | expected | observed | ok | detail |
|---|---|---|---|---|---|
| label-capture | baseline self-comparison | AGREE | AGREE | yes | mcv=AGREE, collision=NOT_RUN, markov=NOT_RUN, compression=NOT_RUN, ttuple=AGREE, lrs=AGREE, multimcw=AGREE, lag=AGREE, multimmc=AGREE, lz78y=AGREE |
| label-capture | mcv: reference min_entropy - 1e-6 | CPP_HIGHER | CPP_HIGHER | yes | !!! C++ min entropy 7.010454037736041 exceeds reference 7.010453037736041 by 1e-06 (tol 1e-09) |
| label-capture | mcv: reference min_entropy + 1e-6 | CPP_LOWER | CPP_LOWER | yes | C++ min entropy 7.010454037736041 below reference 7.010455037736041 by 1e-06 (tol 1e-09) |
| label-capture | mcv: reference min_entropy - 1e-10 (inside tolerance) | AGREE | AGREE | yes | min entropy 7.010454037736041 and 3 shared intermediates within tolerance |
| label-capture | mcv: reference p_hat + 1e-6 | INTERMEDIATE_DIFF | INTERMEDIATE_DIFF | yes | min entropy agrees (7.010454037736041); intermediates differ: p_hat |
| label-capture | mcv: reference mode_count + 1 (integer, exact) | INTERMEDIATE_DIFF | INTERMEDIATE_DIFF | yes | min entropy agrees (7.010454037736041); intermediates differ: mode_count |
| label-capture | mcv: reference module missing | NOT_RUN | NOT_RUN | yes | reference missing: ModuleNotFoundError (simulated); C++ printed min entropy = 7.010454037736041 |
| label-capture | mcv: reference min_entropy = nan | NOT_RUN | NOT_RUN | yes | reference gave no value (nan/absent) for min_entropy while the C++ printed 7.010454037736041; an applicability difference, not an agreement |
| label-capture | 'Assessed min entropy' line removed, exit 0 | TOOL_REFUSED | TOOL_REFUSED | yes | missing_assessed_line |
| label-capture | exit status 255 with full text | TOOL_REFUSED | TOOL_REFUSED | yes | nonzero exit |
| label-capture | assessed: C++ + 1e-6 vs reference | CPP_HIGHER | CPP_HIGHER | yes | !!! C++ Assessed min entropy 5.8608947444852495 exceeds reference 5.860893744485249 by 1e-06 |
| label-capture | assessed: reference incomplete and C++ lower | NOT_RUN | NOT_RUN | yes | reference incomplete (missing: ['lz78y']); on the available estimators C++ 5.860893744485249 vs reference 5.8608947444852495 (delta -1e-06) -- AGREE/CPP_LOWER not established |
| label-capture | assessed: reference incomplete and C++ HIGHER | CPP_HIGHER | CPP_HIGHER | yes | !!! C++ Assessed min entropy 5.8608947444852495 exceeds reference 5.860893744485249 by 1e-06 (established with modules missing: ['lz78y']; more modules could only lower the reference) |
| label-capture | lines shuffled: parse identical (by label, not position) | identical | identical | yes |  |
