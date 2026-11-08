# Differential summary: cpp/ea_non_iid vs py90b reference

Written 2026-11-07T21:16:09-0500 by harness/diff_driver.py (sha256 d47647773aaba47cb1f33c5a54392fbf93cdab244d774b04605b632e7c5a11dd).
Binaries measured (sha256): 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f.
Tolerance: abs 1e-09 for probabilities/entropies, exact for integer counts (C, Mode count, N, Sum t_i, r, t, u, v); widened to the printed half-ulp only where a value was printed with fewer digits (recorded per comparison).

Classes, worst first: TOOL_REFUSED (nonzero exit / signal / timeout / missing 'Assessed min entropy' line; the sub-outcome is in the record) > **CPP_HIGHER (C++ min-entropy above the reference: the dangerous direction)** > CPP_LOWER > INTERMEDIATE_DIFF > NOT_RUN (a side had no value; never agreement) > AGREE.

What this table cannot see: estimators neither side valued; intermediates the C++ does not print; differences under the tolerance; whether the C++ used translated symbols; and, where reference modules were missing, AGREE/CPP_LOWER on the assessed figure (reported NOT_RUN) -- only CPP_HIGHER is established with an incomplete reference.  Rows marked [EA_ALLOW_SHORT_DATASET=1] are non-compliant runs (n < 1,000,000).

Counts: CPP_HIGHER: 3 (CPP_HIGHER explained by D-1: 0)

## !!! CPP_HIGHER cases NOT explained by documented divergence D-1 (C++ reports MORE min-entropy)

- csprng-8bit-5000-b8-assessed: !!! CPP_HIGHER -- Assessed cpp=6.179101871317015 ref=6.179062988162769 [CPP_HIGHER: !!! C++ Assessed min entropy 6.179101871317015 exceeds reference 6.179062988162769 by 3.88832e-05]; D-1 recheck with z = 2.575829303548901: CPP_HIGHER -- residual delta 3.888315424571687e-05: NOT explained by D-1 [EA_ALLOW_SHORT_DATASET=1]
- csprng-8bit-5000-b8-bitstring: !!! CPP_HIGHER (cpp_higher 9, agree 1); cpp_higher in: mcv (+1.21e-06; p_u D-1), collision (+4.86e-06; p,x_bar' D-1?), compression (+1.5e-05; p,x_bar' D-1), ttuple (+1.14e-06; p_u D-1?), lrs (+1.22e-06; p_u D-1), multimcw (+1.22e-06; p_global' D-1), lag (+1.22e-06; p_global' D-1), multimmc (+1.22e-06; p_global' D-1), lz78y (+1.21e-06; p_global' D-1); NOT all explained by D-1 -- needs a human eye [EA_ALLOW_SHORT_DATASET=1]
- csprng-8bit-5000-b8-literal: !!! CPP_HIGHER (cpp_higher 7, not_run 3); cpp_higher in: mcv (+2.89e-05; p_u D-1), ttuple (+2.89e-05; p_u D-1?), lrs (+3.41e-05; p_u D-1), multimcw (+4.07e-05; p_global' D-1), lag (+3.82e-05; p_global' D-1), multimmc (+3.82e-05; p_global' D-1), lz78y (+3.67e-05; p_global' D-1); NOT all explained by D-1 -- needs a human eye [EA_ALLOW_SHORT_DATASET=1]

## CPP_HIGHER cases that vanish with z = 2.575829303548901 (documented divergence D-1: the fork's binary64 quantile against the printed 2.576; class kept, cause tagged)

- none

## All cases

| case | n | bps | mode | class | C++ figure | reference | delta | short-dataset | verdict |
|---|---:|---:|---|---|---|---|---|---|---|
| csprng-8bit-5000-b8-assessed | 5000 | 8 | assessed | CPP_HIGHER | 6.17910187132 | 6.17906298816 | 3.88831542457e-05 | yes | csprng-8bit-5000-b8-assessed: !!! CPP_HIGHER -- Assessed cpp=6.179101871317015 ref=6.179062988162769 [CPP_HIGHER: !!! C++ Assessed min entropy 6.179101871317015 exceeds reference 6.179062988162769 by 3.88832e-05]; D-1 recheck with z = 2.575829303548901: CPP_HIGHER -- residual delta 3.888315424571687e-05: NOT explained by D-1 [EA_ALLOW_SHORT_DATASET=1] |
| csprng-8bit-5000-b8-bitstring | 5000 | 8 | bitstring | CPP_HIGHER | 0.772387733915 | 0.77238287352 | 4.86039428071e-06 | yes | csprng-8bit-5000-b8-bitstring: !!! CPP_HIGHER (cpp_higher 9, agree 1); cpp_higher in: mcv (+1.21e-06; p_u D-1), collision (+4.86e-06; p,x_bar' D-1?), compression (+1.5e-05; p,x_bar' D-1), ttuple (+1.14e-06; p_u D-1?), lrs (+1.22e-06; p_u D-1), multimcw (+1.22e-06; p_global' D-1), lag (+1.22e-06; p_global' D-1), multimmc (+1.22e-06; p_global' D-1), lz78y (+1.21e-06; p_global' D-1); NOT all explained by D-1 -- needs a human eye [EA_ALLOW_SHORT_DATASET=1] |
| csprng-8bit-5000-b8-literal | 5000 | 8 | literal | CPP_HIGHER | 6.63847342315 | 6.63844449263 | 2.89305292123e-05 | yes | csprng-8bit-5000-b8-literal: !!! CPP_HIGHER (cpp_higher 7, not_run 3); cpp_higher in: mcv (+2.89e-05; p_u D-1), ttuple (+2.89e-05; p_u D-1?), lrs (+3.41e-05; p_u D-1), multimcw (+4.07e-05; p_global' D-1), lag (+3.82e-05; p_global' D-1), multimmc (+3.82e-05; p_global' D-1), lz78y (+3.67e-05; p_global' D-1); NOT all explained by D-1 -- needs a human eye [EA_ALLOW_SHORT_DATASET=1] |
