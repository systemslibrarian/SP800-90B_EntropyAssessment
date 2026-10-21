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

Usage:  restart_decision_exact.py <ea_restart JSON report> [...]
        restart_decision_exact.py --from-log <ea_restart -v log> [...]
        restart_decision_exact.py --manual <H_I> <X_max>

EXIT STATUS, so that "it exited 0" means something:
  0  decided, and the decision AGREES with the tool's
  1  decided, and the decision DISAGREES with the tool's
  2  COULD NOT DECIDE -- missing, unreadable or unrecognised input, OR a report
     produced with a different restartCutoffMethod, because agreement across
     methods is not evidence about either (OC-76)

The JSON report is the preferred input and the only one that carries H_I at
full precision. The verbose log prints H_I to six decimal places, and the
cutoff is an integer quantile, so six places is not always enough to determine
it; the log reader checks that explicitly and refuses when it is not.

Inputs the decision depends on, each named in the output:
  H_I     the initial entropy estimate passed to ea_restart (p = 2^-H_I)
  X_max   the largest symbol count in any row or column of the 1000x1000 matrix
  alpha   0.000005, from 3.1.4.3 step 1 -- which is what this script and the
          production tool BOTH use. (An earlier version of this header claimed
          the Sidak value 1 - 0.99^(1/2000) = 5.0251553e-06 while the code used
          0.000005; the code was right and the header was wrong, reported by an
          outside audit as A07. The two are not interchangeable: at
          H_I = 0.9661822653793894 the spec alpha gives an exact cutoff of 582
          and the Sidak alpha gives 581, so an oracle silently using the other
          one would fail to reproduce a real finding -- see OC-49.)
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

REQUIRED = ('restartHI', 'restartXmax', 'restartXcutoff')

def from_report(path):
    """Read the decision inputs from a report, BY SCHEMA, at full precision.

    A07: given a genuine fork report carrying restartXmax 1000, cutoff 683 and
    a failed sanity check, the old reader printed "no H_I/X_max lines" and
    exited 0, having decided nothing -- and an unrelated JSON document behaved
    identically. It only ever parsed the human-readable LOG, and silently
    continued when the pattern did not match. So it could not tell "there is
    nothing to check here" from "I do not understand this file", and both came
    out as success."""
    def _nonfinite(tok):
        raise SystemExit("CANNOT DECIDE: %s contains the JSON token %r; a nonfinite value is not "
                         "a decision input." % (path, tok))
    try:
        with open(path) as fh:
            d = json.load(fh, parse_constant=_nonfinite)
    except SystemExit:
        raise
    except Exception as e:
        return None, "CANNOT DECIDE: %s is not readable JSON (%s)." % (path, e)
    if not isinstance(d, dict):
        return None, "CANNOT DECIDE: %s is not a JSON object." % path
    missing = [k for k in REQUIRED if k not in d]
    if missing:
        return None, ("CANNOT DECIDE: %s carries none of the restart fields this decision needs "
                      "(missing %s). If this is an ea_restart report, the tool that wrote it "
                      "predates those fields; if it is not a restart report, it is the wrong "
                      "input. Either way nothing is decided (A07)."
                      % (path, ", ".join(missing)))
    hi, xm = d['restartHI'], d['restartXmax']
    if not isinstance(hi, (int, float)) or hi != hi or not (0.0 < hi <= 8.0):
        return None, "CANNOT DECIDE: %s has restartHI = %r, outside (0, 8]." % (path, hi)
    if not isinstance(xm, int) or not (0 <= xm <= 1000):
        return None, "CANNOT DECIDE: %s has restartXmax = %r, outside [0, 1000]." % (path, xm)
    return dict(H_I=repr(float(hi)), X_max=xm, tool_cutoff=d['restartXcutoff'],
                tool_said=('Restart Sanity Check Passed'
                           if d.get('passedRestartSanityCheck') is True else
                           'Restart Sanity Check Failed'
                           if d.get('passedRestartSanityCheck') is False else None),
                alpha=d.get('restartAlpha'), method=d.get('restartCutoffMethod')), None

def from_log(path):
    """The verbose log, label-anchored, with the precision actually checked."""
    try:
        t = open(path).read()
    except Exception as e:
        return None, "CANNOT DECIDE: %s is not readable (%s)." % (path, e)
    hi = re.search(r'^H_I:\s*([0-9.]+)', t, re.M)
    xm = re.search(r'^X_max:\s*(\d+)', t, re.M)
    xc = re.search(r'X_cutoff:\s*(\d+)', t)
    if not (hi and xm):
        return None, ("CANNOT DECIDE: %s has no H_I/X_max lines. This reader is label-anchored; a "
                      "file without those labels is unrecognised, not a run with nothing to "
                      "check. Run ea_restart with -v, or pass the JSON report (A07)." % path)
    h_text = hi.group(1)
    # The log prints six decimals. The cutoff is an INTEGER QUANTILE, so a
    # rounded H_I can give a different integer -- exactly the error that made
    # this project report 683 where the truth was 684 (OC-49). Check it here
    # instead of hoping: if the cutoff differs anywhere in the half-ulp
    # interval the printed text admits, refuse and ask for the report.
    try:
        import decimal
        q = decimal.Decimal(h_text)
        half = decimal.Decimal(1).scaleb(q.as_tuple().exponent) / 2
        lo, hi_v = float(q - half), float(q + half)
    except Exception:
        lo = hi_v = float(h_text)
    ALPHA = 0.000005
    c_lo = maxcell_cutoff(repr(lo), ALPHA, start=binomial_cutoff(repr(lo), ALPHA))
    c_hi = maxcell_cutoff(repr(hi_v), ALPHA, start=binomial_cutoff(repr(hi_v), ALPHA))
    if c_lo != c_hi:
        return None, ("CANNOT DECIDE: %s prints H_I as %s, and the cutoff is not determined by "
                      "that many digits -- it is %d at the bottom of the printed interval and %d "
                      "at the top. Pass the JSON report, which carries H_I at full precision "
                      "(A07, OC-49)." % (path, h_text, c_hi, c_lo))
    said = ('Restart Sanity Check Failed' if 'Restart Sanity Check Failed' in t
            else 'Restart Sanity Check Passed' if 'Restart Sanity Check Passed' in t else None)
    return dict(H_I=h_text.rstrip('0').rstrip('.'), X_max=int(xm.group(1)),
                tool_cutoff=int(xc.group(1)) if xc else None, tool_said=said,
                alpha=None, method=None), None

if __name__ == '__main__':
    import json
    if len(sys.argv) >= 4 and sys.argv[1] == '--manual':
        decide(sys.argv[2], int(sys.argv[3]), label='manual')
        sys.exit(0)
    use_log = len(sys.argv) > 1 and sys.argv[1] == '--from-log'
    paths = sys.argv[2:] if use_log else sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(2)
    status = 0
    decided = 0
    for path in paths:
        got, why = (from_log(path) if use_log else from_report(path))
        if got is None:
            print(why, file=sys.stderr)
            status = 2
            continue
        if got.get('alpha') is not None and abs(float(got['alpha']) - 0.000005) > 1e-12:
            print("NOTE: %s records restartAlpha = %.17g; this oracle decides at 0.000005 "
                  "(3.1.4.3 step 1). The two are not interchangeable at a quantile boundary."
                  % (path, float(got['alpha'])), file=sys.stderr)
        # THE INSTRUMENT'S OWN STATEMENT OF WHICH STATISTIC IT USED (OC-76).
        # restartCutoffMethod was read into the result and then dropped, so
        # agreement with an exact-multinomial-maximum build and agreement with
        # a printed-binomial build were reported IDENTICALLY -- across exactly
        # the distinction C23 exists to draw. An exclusion that touches the
        # instrument's identity voids a comparison rather than weakening it
        # (instrument rule 8), and this one voided it along the one axis that
        # matters here.
        meth = got.get('method')
        if meth is None:
            print("NOTE: %s records no restartCutoffMethod, so WHICH statistic the tool "
                  "used is unestablished. The agreement below is with an unidentified "
                  "cutoff method." % path, file=sys.stderr)
        elif meth != 'exact-multinomial-maximum':
            print("INSTRUMENT MISMATCH: %s was produced with restartCutoffMethod=%r, not "
                  "'exact-multinomial-maximum'. This oracle decides on the exact "
                  "multinomial maximum, so agreement or disagreement below is ACROSS "
                  "METHODS and is not evidence about either (OC-76)."
                  % (path, meth), file=sys.stderr)
            status = 2
            continue
        decided += 1
        mine = decide(got['H_I'], got['X_max'], got['tool_cutoff'], got['tool_said'], label=path)
        if got['tool_cutoff'] is not None:
            theirs = 'ACCEPT' if got['X_max'] <= got['tool_cutoff'] else 'REJECT'
            if theirs != mine and status == 0:
                status = 1
    if decided == 0 and status == 0:
        status = 2
    sys.exit(status)
