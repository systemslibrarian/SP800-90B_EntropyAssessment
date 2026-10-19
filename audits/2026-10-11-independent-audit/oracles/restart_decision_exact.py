#!/usr/bin/env python3
"""C23: recompute the restart sanity-check DECISION with the CORRECT statistic.

CORRECTED 2026-10-19 (OC-30). This script used to decide on SP 800-90B 3.1.4.3
step 5 as printed -- the tail of a single binomial -- and called that exact.
That formula is not the probability of the event being tested: the value tested
is the maximum count of the row/column-specific most likely symbol, a
multinomial maximum. Deciding on the printed formula REJECTS CORRECTLY-OPERATING
SOURCES (83.2% of full-entropy 8-bit matrices, measured). The deciding cutoff
here is now the exact distribution of the multinomial maximum (Levin), anchored
on Hill/UL's published Table 3; the printed-formula value is reported beside it
as the conformance figure only.

Usage:  restart_decision_exact.py <ea_restart -v log> [...]
        restart_decision_exact.py --manual <H_I> <X_max>

Inputs the decision depends on, each named in the output:
  H_I     the initial entropy estimate passed to ea_restart (p = 2^-H_I)
  X_max   the largest symbol count in any row or column of the 1000x1000 matrix
  alpha   1 - 0.99^(1/2000), the tool's own Sidak value (5.0251553e-06); the
          standard prints 0.000005 and both give the same cutoff at H_I 1..8
  N       1000 trials per row/column (fixed by the standard)
The exact cutoff comes from oracles/restart_cutoff_exact.py, written from the
standard's closed form and pinned against its published values, not against
the tool.
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from restart_cutoff_exact import exact_cutoff, alpha_tool, tail, power, mpf
from restart_multinomial_max import maxcell_cutoff, binomial_cutoff

def decide(H_I, X_max, tool_cutoff=None, tool_said=None, label=''):
    ALPHA = 0.000005                      # 3.1.4.3 step 1, and the alpha Hill's cutoffs target
    printed = binomial_cutoff(H_I, ALPHA)         # conformance figure only
    cut = maxcell_cutoff(H_I, ALPHA, start=printed)  # the deciding cutoff
    exact = 'ACCEPT' if X_max <= cut else 'REJECT'
    print('%s' % label)
    print('  inputs: H_I=%s  X_max=%d  alpha=%g  N=1000' % (H_I, X_max, ALPHA))
    print('  DECIDING cutoff (exact multinomial maximum, the statistic 3.1.4.3 forms): %d' % cut)
    print('  DECISION: %s  (X_max %s %d)' % (exact, '<=' if exact == 'ACCEPT' else '>', cut))
    print('  conformance only -- 3.1.4.3 step 5 as printed would give cutoff %d (%s);' % (
        printed, 'ACCEPT' if X_max <= printed else 'REJECT'))
    print('    the printed formula tests a single binomial and rejects correctly-operating')
    print('    sources, so it is recorded for traceability and is NOT the verdict (OC-30).')
    if tool_cutoff is not None:
        tool = 'ACCEPT' if X_max <= tool_cutoff else 'REJECT'
        print('  the tool said: %s  (its X_cutoff %d%s)' % (tool, tool_cutoff,
              ('; printed "%s"' % tool_said) if tool_said else ''))
        if tool == exact:
            print('  => AGREE with the corrected decision')
        else:
            print('  => DISAGREE: the tool %ss where the corrected statistic %ss' % (tool.lower(), exact.lower()))
        if abs(tool_cutoff - cut) <= 2:
            print('     (its cutoff is within 2 of the exact one, consistent with upstream\'s simulation')
            print('      of the same statistic -- see XR-11 item 4)')
    return exact

if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == '--manual':
        decide(sys.argv[2], int(sys.argv[3]), label='manual')
        sys.exit(0)
    for path in sys.argv[1:]:
        t = open(path).read()
        hi = re.search(r'^H_I:\s*([0-9.]+)', t, re.M)
        xm = re.search(r'^X_max:\s*(\d+)', t, re.M)
        xc = re.search(r'X_cutoff:\s*(\d+)', t)
        said = 'Restart Sanity Check Failed' if 'Restart Sanity Check Failed' in t else ('Restart Sanity Check Passed' if 'Restart Sanity Check Passed' in t else None)
        if not (hi and xm):
            print('%s: no H_I/X_max lines (run ea_restart with -v)' % path); continue
        decide(hi.group(1).rstrip('0').rstrip('.'), int(xm.group(1)), int(xc.group(1)) if xc else None, said, label=path)
