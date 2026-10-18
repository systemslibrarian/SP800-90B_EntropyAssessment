#!/usr/bin/env python3
"""C23: recompute the SP 800-90B 3.1.4.3 restart sanity-check DECISION exactly.

The tool's X_cutoff is an order statistic of 5,000,000 simulated experiments and
sits above the exact binomial cutoff (OC-7: H_I = 7 gives 27 against 23), so it
accepts restart matrices the standard rejects. C23 governs ACCEPTANCE, not the
per-bit figure: the treatment is not a subtraction, it is this recomputation.

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

def decide(H_I, X_max, tool_cutoff=None, tool_said=None, label=''):
    a = alpha_tool()
    cut = exact_cutoff(H_I, a)
    exact = 'ACCEPT' if X_max <= cut else 'REJECT'
    p = power(2, -mpf(H_I))
    print('%s' % label)
    print('  inputs: H_I=%s  X_max=%d  alpha=%.10g (Sidak, tool\'s own)  N=1000' % (H_I, X_max, float(a)))
    print('  exact cutoff (largest passing count): %d   P(X >= X_max | H_I) = %.3e' % (cut, float(tail(X_max, p))))
    print('  EXACT decision:  %s  (X_max %s %d)' % (exact, '<=' if exact == 'ACCEPT' else '>', cut))
    if tool_cutoff is not None:
        tool = 'ACCEPT' if X_max <= tool_cutoff else 'REJECT'
        print('  tool  decision:  %s  (simulated X_cutoff %d%s)' % (tool, tool_cutoff, ('; tool printed "%s"' % tool_said) if tool_said else ''))
        print('  => %s' % ('AGREE' if tool == exact else 'DISAGREE: the tool %s a matrix the standard %ss' % ('accepts' if tool == 'ACCEPT' else 'rejects', exact.lower())))
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
