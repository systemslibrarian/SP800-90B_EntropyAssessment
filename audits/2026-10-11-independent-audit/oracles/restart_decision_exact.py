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

def decide(H_I, X_max, tool_cutoff=None, tool_said=None, tool_passed=None, label=''):
    """Three SEPARATE statements, never collapsed into one (F07 / OC-82).

    THE OLD VERSION DERIVED "THE TOOL SAID" FROM THE TOOL'S CUTOFF:

        tool = 'ACCEPT' if X_max <= tool_cutoff else 'REJECT'

    so "the tool said" was this script RE-DOING the tool's comparison with the
    tool's numbers, not the tool's verdict. The tool's actual verdict --
    passedRestartSanityCheck in the report, "Restart Sanity Check Passed/Failed"
    in the log -- was read, passed in, and printed as a decorative parenthetical
    that nothing compared against.

    So a tool whose own comparison was wrong -- an off-by-one, an inverted
    operator, a NaN path, a verdict written from a different variable --
    produced AGREE. Demonstrated by flipping one field of a genuine report:

        the tool said: ACCEPT  (its X_cutoff 605; printed "Restart Sanity Check Failed")
        => AGREE with the corrected decision                        [exit 0]

    One line asserting the tool said ACCEPT and that it printed Failed, and
    agreement declared anyway.

    The three statements, which answer three different questions:

      A  THE INDEPENDENT DECISION -- from the exact multinomial maximum, using
         only H_I and X_max. Needs nothing from the tool but its inputs.
      B  THE TOOL'S REPORTED VERDICT -- read from the field the tool wrote.
         This is the only thing that is "what the tool said". Absent => the
         comparison cannot be made and the evidence is INCOMPLETE, not
         agreeable.
      C  WHAT THE TOOL'S OWN NUMBERS IMPLY -- X_max against the tool's X_cutoff.
         Worth printing, because if it disagrees with B then the tool's verdict
         does not follow from the figures it reported, which is a finding about
         the tool and not a reason to prefer C.

    AGREEMENT is A against B. It is never A against C, because A and C share
    X_max and differ only in the cutoff, so they agree whenever the two cutoffs
    fall on the same side of X_max -- which is most of the time and has nothing
    to say about whether the tool decided correctly.
    """
    ALPHA = 0.000005                      # 3.1.4.3 step 1, and the alpha Hill's cutoffs target
    printed = binomial_cutoff(H_I, ALPHA)         # conformance figure only
    cut = maxcell_cutoff(H_I, ALPHA, start=printed)  # the deciding cutoff
    exact = 'ACCEPT' if X_max <= cut else 'REJECT'
    print('%s' % label)
    print('  inputs: H_I=%s  X_max=%d  alpha=%g  N=1000' % (H_I, X_max, ALPHA))
    print('  DECIDING cutoff (exact multinomial maximum, the statistic 3.1.4.3 forms): %d' % cut)
    print('  A. INDEPENDENT DECISION: %s  (X_max %s %d)'
          % (exact, '<=' if exact == 'ACCEPT' else '>', cut))
    print('  conformance only -- 3.1.4.3 step 5 as printed would give cutoff %d (%s);' % (
        printed, 'ACCEPT' if X_max <= printed else 'REJECT'))
    print('    the printed formula tests a single binomial and rejects correctly-operating')
    print('    sources, so it is recorded for traceability and is NOT the verdict (OC-30).')

    # B -- what the tool ITSELF reported.
    if tool_passed is None:
        reported = None
        print('  B. THE TOOL\'S REPORTED VERDICT: NOT REPORTED%s'
              % ('' if tool_said is None else ' (it printed "%s", which this reader could not '
                 'resolve to a verdict)' % tool_said))
    else:
        reported = 'ACCEPT' if tool_passed else 'REJECT'
        print('  B. THE TOOL\'S REPORTED VERDICT: %s%s'
              % (reported, '' if tool_said is None else '  (it printed "%s")' % tool_said))

    # C -- what the tool's own figures imply, which is NOT what it said.
    implied = None
    if tool_cutoff is not None:
        implied = 'ACCEPT' if X_max <= tool_cutoff else 'REJECT'
        print('  C. implied by the tool\'s OWN figures: %s  (X_max %d vs its X_cutoff %d)'
              % (implied, X_max, tool_cutoff))
        if abs(tool_cutoff - cut) <= 2:
            print('     (its cutoff is within 2 of the exact one, consistent with upstream\'s simulation')
            print('      of the same statistic -- see XR-11 item 4)')
    else:
        print('  C. implied by the tool\'s OWN figures: NO X_cutoff REPORTED')

    # The tool contradicting itself is a finding, and is reported before any
    # agreement claim, because an agreement with an internally inconsistent
    # instrument is not an agreement about anything.
    inconsistent = (reported is not None and implied is not None and reported != implied)
    if inconsistent:
        print('  !! THE TOOL CONTRADICTS ITSELF: it reported %s, and its own X_max %d against its'
              % (reported, X_max))
        print('     own X_cutoff %d implies %s. Its verdict does not follow from the figures it'
              % (tool_cutoff, implied))
        print('     wrote. Nothing below is evidence about the statistic; this is a defect in the')
        print('     tool or in the report it produced, and must be resolved before either.')

    # AGREEMENT: A against B, and only A against B.
    if reported is None:
        print('  => INCOMPLETE: the tool reported no verdict, so there is nothing to agree with.')
        print('     The independent decision above stands on its own; it is NOT corroboration.')
        verdict = 'INCOMPLETE'
    elif reported == exact:
        print('  => AGREE: the tool\'s reported verdict matches the independent decision')
        verdict = 'AGREE'
    else:
        print('  => DISAGREE: the tool reported %s where the corrected statistic says %s'
              % (reported.lower(), exact.lower()))
        verdict = 'DISAGREE'
    return dict(independent=exact, reported=reported, implied=implied,
                inconsistent=inconsistent, verdict=verdict)

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
    # THE FLAG ITSELF, as a tri-state, not only rendered into a string (F07).
    # It used to be read only to build `tool_said`, a parenthetical nothing
    # compared against, while the verdict was recomputed from the cutoff.
    passed = d.get('passedRestartSanityCheck')
    if passed is not None and not isinstance(passed, bool):
        return None, ("CANNOT DECIDE: %s carries passedRestartSanityCheck=%r, which is not a "
                      "boolean. The tool's verdict is the thing this oracle compares against, so "
                      "it is not guessed from a non-boolean (F07)." % (path, passed))
    return dict(H_I=repr(float(hi)), X_max=xm, tool_cutoff=d['restartXcutoff'],
                tool_passed=passed,
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
    # BOTH phrases present means the log is not a single run's verdict, and
    # picking the first match would silently choose one. Refuse (F07).
    nfail = t.count('Restart Sanity Check Failed')
    npass = t.count('Restart Sanity Check Passed')
    if nfail and npass:
        return None, ("CANNOT DECIDE: %s contains both 'Restart Sanity Check Passed' and "
                      "'...Failed'. That is not one run's verdict, and this reader will not "
                      "choose between them (F07)." % path)
    if nfail > 1 or npass > 1:
        return None, ("CANNOT DECIDE: %s states the restart verdict %d times; a single run states "
                      "it once, so this is not one run's log (F07)."
                      % (path, max(nfail, npass)))
    said = ('Restart Sanity Check Failed' if nfail else
            'Restart Sanity Check Passed' if npass else None)
    passed = True if npass else False if nfail else None
    return dict(H_I=h_text.rstrip('0').rstrip('.'), X_max=int(xm.group(1)),
                tool_cutoff=int(xc.group(1)) if xc else None, tool_said=said,
                tool_passed=passed, alpha=None, method=None), None

if __name__ == '__main__':
    import json
    if len(sys.argv) >= 4 and sys.argv[1] == '--manual':
        # --manual has no tool verdict by construction, so it is INCOMPLETE by
        # construction: it exercises limb A alone and says so.
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
        # THE EXIT STATUS FOLLOWS A-AGAINST-B (F07). It used to redo the
        # comparison here as well -- `theirs = 'ACCEPT' if X_max <= tool_cutoff`
        # -- so the status agreed with the printed verdict in being about a
        # recomputation rather than about what the tool decided.
        r = decide(got['H_I'], got['X_max'], got['tool_cutoff'], got['tool_said'],
                   got.get('tool_passed'), label=path)
        if r['verdict'] == 'INCOMPLETE':
            # Exit 2 is this oracle's "could not decide", and a missing verdict
            # is exactly that: the independent decision stands, but no
            # comparison was made. It must not read as agreement.
            print("CANNOT COMPARE: %s reports no restart verdict, so this run is evidence about "
                  "the statistic and not about the tool (F07)." % path, file=sys.stderr)
            if status == 0:
                status = 2
        elif r['verdict'] == 'DISAGREE' and status == 0:
            status = 1
        # An internally inconsistent tool is a disagreement found, reported
        # separately above and counted here.
        if r['inconsistent'] and status == 0:
            status = 1
    if decided == 0 and status == 0:
        status = 2
    sys.exit(status)
