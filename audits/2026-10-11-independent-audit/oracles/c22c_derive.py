#!/usr/bin/env python3
"""THE SLOW CHECK: re-derive every C22c family ceiling and verify the one source.

WHY THIS IS SEPARATE FROM THE FAST VALIDATION (OC-125).

`c22c_source.py` validates the SHAPE of the one source in milliseconds -- every
stamp present, every stamp's derivation still at the sha256 it was stamped
against, every carried value at the declared precision. That belongs in a
suite that must stay fast, and it is what `regression-constants.sh` runs.

It cannot verify that a carried NUMBER is still the derivation's output,
because finding that out means re-running the derivation: the compression
ceiling is a bisection on a 6.3.4 step-7 sum at working precision 50, about
twenty seconds per bitstring length, twice over for the precision control. So
that check lives here, runs on demand, and runs in CI.

HOW SOMEONE KNOWS TO RUN IT. Three ways, none of them a memory:

  * `c22c_source.py` prints "the slow check that re-derives these:
    c22c_derive.py" at the foot of its table.
  * The fast validation REFUSES, by name, the moment a derivation file's
    sha256 stops matching its stamp: "re-run c22c_derive.py --restamp". So
    editing a derivation cannot quietly leave a stale value behind -- the fast
    suite fails until the slow check has been run and the value re-stamped.
  * `.github/workflows/c22c-source-check.yml` runs it on every push that
    touches the oracles and on manual dispatch.

WHAT IT CHECKS, AND WHY EACH ONE CAN FAIL

  1. EXACTNESS. For each carried family value: re-derive, round the derivation's
     output up to the declared digits, and require the carried string to equal
     that exactly. Not a tolerance -- an exact predicate on a declared rounding.
  2. PRECISION STABILITY. Re-derive at dps 80 and require the same rounded
     result. This is what makes "twenty digits" a measurement rather than a
     preference: if the carried digits were inside the arithmetic's noise, this
     fails.
  3. DIRECTION. Require carried >= derived, always. The rounding is ceiling
     because C22c is subtracted; a value rounded down subtracts too little.
  4. THE CLOSED FORM. The proportion family is computed, not carried, so its
     closed form is checked against zalpha_ceiling_by_n.py's numerical
     maximisation at both lengths, and the argmax is required to be p = 1/n.
  5. THE RECORD. The derivations are required to reproduce the record's own
     three-figure publications (OC-22 Part 3) to within half a unit in their
     last digit. This is the check that used to read literals inside the
     oracles themselves -- the same claim, now against the one source.

Usage:
    c22c_derive.py                 verify (exit 0 agree, 1 disagree, 2 cannot run)
    c22c_derive.py --restamp       re-derive and WRITE c22c_source.json
    c22c_derive.py --fast-families verify only the cheap families (no compression)
"""
import datetime
import json
import os
import subprocess
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from mpmath import mp, mpf, log, log1p
except ImportError as exc:  # pragma: no cover - environment
    sys.stderr.write("c22c_derive: mpmath is required to re-derive these "
                     "values (%s). This check CANNOT RUN; it is not passing.\n"
                     % exc)
    raise SystemExit(2)

import c22c_source as SRC

NS = (1_000_000, 8_000_000)
DPS_WORKING = 50
DPS_CONTROL = 80
DIGITS = 20

# THE RECORD'S PUBLISHED FIGURES ARE NOT WRITTEN HERE, AND THE SWEEP IS WHY.
#
# The first version of this file carried them as constants -- and
# c22c-copy-sweep.sh flagged all five on its first run, correctly: a generator
# that holds the record's numbers is a second copy of them, which is the defect
# this whole commit removes. It also means a generator could INVENT a published
# figure, and a published figure is historical data that no derivation
# produces.
#
# So --restamp reads them forward out of the existing source and REFUSES if one
# is missing. Adding a row for a new bitstring length therefore needs a human
# to supply the record figure with --record, or to state that the record
# published none; it cannot be defaulted.
def record_3fig(doc, family, n):
    for row in doc.get('rows', ()):
        if row.get('n') == n and isinstance(row.get(family), dict):
            v = row[family].get('record_3fig')
            if isinstance(v, str) and v.strip():
                return v
    return None

VALIDATED_AGAINST = {
    'compression':
        "SP 800-90B 6.3.4's own worked example: d=4, N=8, v=4, X'=1.4617, for "
        "which NIST publishes p = 0.5715 and min-entropy 0.1345. An external "
        "check of the derivation, not a comparison against the tool it audits.",
    'collision':
        "its own two controls in zalpha_ceiling_by_n.py -- every row recomputed "
        "at a second working precision, and a live-sensitivity perturbation of "
        "z_spec that the ceiling must follow -- plus the record's three-figure "
        "publication in OC-22 Part 3.",
}
ENTRY_POINT = {
    'compression': ('compression_ceiling_exact.py', 'ceiling_at'),
    'collision': ('zalpha_ceiling_by_n.py', 'worst_collision'),
}


def derive(family, n, dps):
    """The family ceiling at bitstring length n, at working precision dps."""
    mp.dps = dps
    if family == 'compression':
        import compression_ceiling_exact as CCE
        mp.dps = dps
        return CCE.ceiling_at(n, verbose=False)['ceiling']
    if family == 'collision':
        import zalpha_ceiling_by_n as Z
        g, _dx = Z.worst_collision(n, dps)
        return g
    raise ValueError('no derivation for family %r' % family)


def derived_text(value, digits=DIGITS):
    """The derivation's output as a decimal string with headroom to round.

    Rendered with twenty digits of headroom beyond what is carried, so the
    ceiling rounding below is deciding on real digits and not on the tail of
    the renderer.
    """
    return mp.nstr(value, digits + 20, strip_zeros=False)


def rounded(value, digits=DIGITS):
    return SRC.round_up(derived_text(value, digits), digits)


def half_unit_last_digit(text):
    """Half a unit in the last digit of a decimal string, as a Decimal."""
    d = Decimal(text)
    exponent = d.adjusted() - (SRC.sigdigits(text) - 1)
    return Decimal(5) * Decimal(10) ** (exponent - 1)


def git_head():
    out = subprocess.run(['git', '-C', HERE, 'rev-parse', 'HEAD'],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return out.stdout.strip()


# --------------------------------------------------------------------- restamp
def restamp(path, overrides):
    head = git_head()
    if not head:
        sys.stderr.write("c22c_derive: cannot read HEAD; a stamp without a "
                         "repo commit is not a stamp. Refusing to write.\n")
        return 2
    today = datetime.date.today().isoformat()
    prior = {}
    if os.path.exists(path):
        try:
            prior = SRC.read_raw(path)
        except SRC.C22cSourceError as exc:
            sys.stderr.write("c22c_derive: the existing source cannot be read, "
                             "so the record's published figures cannot be "
                             "carried forward: %s\n" % exc)
            return 2
    missing = [(f, n) for n in NS for f in SRC.FAMILIES_CARRIED
               if record_3fig(prior, f, n) is None and (f, n) not in overrides]
    prop_rec = (prior.get('families', {}).get('proportion', {}) or {}).get('record_3fig')
    prop_rec = overrides.get(('proportion', 0), prop_rec)
    if missing or not prop_rec:
        sys.stderr.write(
            "c22c_derive: the record's published three-figure value is missing "
            "for %s%s. It is historical data -- what OC-22 Part 3 printed -- "
            "and this generator will not invent one. Supply it with "
            "--record FAMILY:N=VALUE (N=0 for the n-independent proportion "
            "family) or restore the source from git.\n"
            % (', '.join('%s n=%d' % (f, n) for f, n in missing),
               '' if prop_rec else ' and for proportion'))
        return 2
    rows = []
    for n in sorted(NS, reverse=True):
        row = {'n': n}
        for family in SRC.FAMILIES_CARRIED:
            print("  deriving %-12s n = %-9d at dps %d ..." % (family, n, DPS_WORKING))
            v50 = derive(family, n, DPS_WORKING)
            print("  control  %-12s n = %-9d at dps %d ..." % (family, n, DPS_CONTROL))
            v80 = derive(family, n, DPS_CONTROL)
            r50, r80 = rounded(v50), rounded(v80)
            if r50 != r80:
                sys.stderr.write(
                    "c22c_derive: %s at n = %d rounds to %s at dps %d and %s at "
                    "dps %d. The carried digits are inside the arithmetic's own "
                    "noise; %d digits is not supportable. Refusing to write.\n"
                    % (family, n, r50, DPS_WORKING, r80, DPS_CONTROL, DIGITS))
                return 2
            script, entry = ENTRY_POINT[family]
            row[family] = {
                'value': format(r50, 'f'),
                'record_3fig': overrides.get((family, n))
                               or record_3fig(prior, family, n),
                'stamp': {
                    'derivation': script,
                    'entry_point': entry,
                    'derivation_sha256': SRC.sha256_file(os.path.join(HERE, script)),
                    'produced': today,
                    'working_precision_dps': DPS_WORKING,
                    'stability_control':
                        'recomputed at dps %d; the carried %d digits unchanged'
                        % (DPS_CONTROL, DIGITS),
                    'validated_against': VALIDATED_AGAINST[family],
                    'stamped_at_repo_commit': head,
                },
            }
        rows.append(row)
    doc = {
        'schema': 'c22c-source/1',
        'subject':
            'C22c -- the ZALPHA-rounding ceiling entropy_floor.py subtracts '
            'from a reported min-entropy figure. A MAX over three estimator '
            'families at two bitstring lengths.',
        'one_source_rule':
            'These are the only recordings of these values in the repository. '
            'entropy_floor.py subtracts them, compression_ceiling_exact.py and '
            'zalpha_ceiling_by_n.py verify them against their own fresh '
            'derivations, and regression-constants.sh pins a DIGEST of them '
            'rather than a second copy. c22c-copy-sweep.sh enforces that, with '
            'a positive control. Before OC-125 the same six numbers lived in '
            'seven places and nothing compared the copy that was subtracted '
            'against the copy the derivation verified.',
        'digits': DIGITS,
        'rounding': 'ceiling',
        'rounding_why':
            'C22c is SUBTRACTED, so a value rounded down subtracts too little '
            'and the floor it produces is permissive. Truncation is therefore '
            'always toward a larger subtraction, and the float conversion in '
            'c22c_source.py is nudged upward if it would land below the '
            'carried decimal.',
        'lookup':
            'The term used at bitstring length n is the first row with '
            'n0 <= n, rows descending. That is an upper bound because the '
            'ceiling falls with n (dX\' ~ sigma_max/sqrt(v), v ~ n/6), which '
            'zalpha_ceiling_by_n.py measures rather than asserts.',
        'inputs': {
            'z_tool': '2.5758293035489008',
            'z_spec': '2.576',
            'z_note':
                'the exact 0.995 normal quantile the tool uses, and the value '
                '6.3.4 step 6 prints. NOT collapsed into one source: each '
                'derivation states them independently, so a disagreement '
                'surfaces as a disagreement between derivations. '
                'c22c-copy-sweep.sh cross-checks that the statements are '
                'identical strings.',
            'compression_d': 1000,
            'compression_b': 6,
        },
        'families': {
            'proportion': {
                'carried': False,
                'computed_inline': 'log2((1 + z_spec) / (1 + z_tool))',
                'record_3fig': prop_rec,
                'why_not_carried':
                    'At the domain edge p = 1/n the standard error is exactly '
                    '1/n, so the gap is log2((1+z_spec)/(1+z_tool)) with no '
                    'approximation and no n dependence. Carrying a value for '
                    'one line of exact arithmetic would add a copy and buy '
                    'nothing. It is also the only family where full precision '
                    'LOWERS the value -- the exact form is 6.8867114e-5 '
                    'against the first-order 6.8868758e-5 the record rounded '
                    'to 6.887e-5 -- and it cannot affect C22c either way, '
                    'because compression binds by a factor of 48.8 at n = 1e6.',
                'validated_against':
                    "zalpha_ceiling_by_n.py's numerical maximisation over "
                    "p >= 1/n, which finds its argmax at p = 1/n exactly and "
                    "agrees with the closed form to 25 digits at both lengths.",
            },
        },
        'rows': rows,
    }
    tmp = path + '.new'
    with open(tmp, 'w') as fh:
        json.dump(doc, fh, indent=2)
        fh.write('\n')
    os.replace(tmp, path)
    print()
    print("c22c_derive: wrote %s" % path)
    try:
        digest, _ = SRC.values_digest(path)
    except SRC.C22cSourceError as exc:
        sys.stderr.write("c22c_derive: the file just written does not "
                         "validate: %s\n" % exc)
        return 2
    print("c22c_derive: values digest %s" % digest)
    print("c22c_derive: put that digest in cpp/selftest/regression-constants.sh")
    return 0


# ---------------------------------------------------------------------- verify
def verify(path, families):
    try:
        doc = SRC.validate(path)
    except SRC.C22cSourceError as exc:
        sys.stderr.write("c22c_derive: the one source does not validate, so "
                         "there is nothing to re-derive against:\n  %s\n" % exc)
        return 2
    digits = doc['digits']
    bad = 0
    print("C22c -- re-deriving the one source (%s)" % os.path.basename(path))
    print()
    print("| n | family | carried | re-derived (dps %d) | rounded %d | dps %d | verdict |"
          % (DPS_WORKING, digits, DPS_CONTROL))
    print("|---:|---|---:|---:|---:|---:|---|")
    for row in doc['rows']:
        n = row['n']
        for family in SRC.FAMILIES_CARRIED:
            if family not in families:
                continue
            carried = Decimal(row[family]['value'])
            v50 = derive(family, n, DPS_WORKING)
            v80 = derive(family, n, DPS_CONTROL)
            r50, r80 = rounded(v50, digits), rounded(v80, digits)
            exact = (r50 == carried)
            stable = (r80 == carried)
            direction = (carried >= Decimal(derived_text(v50, digits)))
            ok = exact and stable and direction
            if not ok:
                bad += 1
            verdict = 'AGREES' if ok else '*** %s ***' % (
                'NOT THE ROUNDED DERIVATION' if not exact else
                'UNSTABLE AT dps %d' % DPS_CONTROL if not stable else
                'CARRIED BELOW DERIVED')
            print("| %d | %s | %s | %s | %s | %s | %s |"
                  % (n, family, row[family]['value'],
                     mp.nstr(v50, digits + 4), r50, r80, verdict))
    print()

    # 5. THE RECORD. The derivation must reproduce what OC-22 Part 3 published.
    print("against the record's own three-figure publication (OC-22 Part 3)")
    print("| n | family | recorded | re-derived | residual | half a unit | agrees |")
    print("|---:|---|---:|---:|---:|---:|---|")
    for row in doc['rows']:
        n = row['n']
        for family in SRC.FAMILIES_CARRIED:
            if family not in families:
                continue
            rec_text = row[family]['record_3fig']
            rec = Decimal(rec_text)
            here = Decimal(derived_text(derive(family, n, DPS_WORKING), digits))
            tol = half_unit_last_digit(rec_text)
            ok = abs(here - rec) <= tol
            if not ok:
                bad += 1
            print("| %d | %s | %s | %s | %+.3e | %.1e | %s |"
                  % (n, family, rec_text, mp.nstr(mpf(str(here)), 8),
                     float(here - rec), float(tol), 'yes' if ok else '*** NO ***'))
    print()

    # 4. THE CLOSED FORM, against the numerical maximisation.
    mp.dps = DPS_CONTROL
    import zalpha_ceiling_by_n as Z
    closed = SRC.proportion_ceiling(doc['inputs']['z_tool'],
                                    doc['inputs']['z_spec'])
    # TWO CLAIMS, EACH AT THE PRECISION OF WHAT IT READS (rule 16).
    #
    # THE FIRST VERSION OF THIS BLOCK COMPARED THE FLOAT CLOSED FORM AGAINST
    # THE 80-DIGIT SWEEP AT 20 DIGITS AND REPORTED BOTH ROWS DISAGREEING. The
    # numbers were fine; the check was tighter than the number it reads. A
    # double carries about 17 significant digits, so a 20-digit comparison
    # against one can only ever fail -- the same mistake rule 16 was written
    # for, made in the check written to enforce the rest of this fix.
    #
    #   MATHEMATICS   the EXACT closed form, in mpmath at dps 80, against the
    #                 numerical maximisation, at 20 digits. This is the claim
    #                 that log2((1+z_spec)/(1+z_tool)) IS the maximum and that
    #                 the argmax is the domain edge p = 1/n.
    #   IMPLEMENTATION the float closed form c22c_source.py actually computes,
    #                 against that exact value, in UNITS IN THE LAST PLACE. The
    #                 bound is 4 ulp, derived rather than chosen: one rounding
    #                 for the Decimal-to-float conversion, about one for log1p,
    #                 and a half each for log(2) and the division. Measured at
    #                 0.39 ulp on this host -- the roundings largely cancel.
    mp.dps = DPS_CONTROL
    z_tool, z_spec = mpf(doc['inputs']['z_tool']), mpf(doc['inputs']['z_spec'])
    closed_exact = log1p((z_spec - z_tool) / (1 + z_tool)) / log(2)
    print("the proportion family: the closed form IS the maximum (dps %d)" % DPS_CONTROL)
    print("| n | exact closed form | swept maximum | argmax | argmax is 1/n | agrees to %d digits |"
          % digits)
    print("|---:|---:|---:|---:|---|---|")
    for n in sorted({row['n'] for row in doc['rows']}):
        g, p = Z.worst_proportion(n, DPS_CONTROL)
        at_edge = (p == mpf(1) / n)
        agree = (SRC.round_up(mp.nstr(g, digits + 20, strip_zeros=False), digits)
                 == SRC.round_up(mp.nstr(closed_exact, digits + 20, strip_zeros=False),
                                 digits))
        if not (at_edge and agree):
            bad += 1
        print("| %d | %s | %s | %s | %s | %s |"
              % (n, mp.nstr(closed_exact, digits), mp.nstr(g, digits), mp.nstr(p, 6),
                 'yes' if at_edge else '*** NO ***',
                 'yes' if agree else '*** NO ***'))
    print()
    # The implementation, in ulp of double.
    import math as _math
    ulp = _math.ulp(closed)
    err = abs(mpf(repr(closed)) - closed_exact)
    ulps = float(err / ulp)
    ok_impl = ulps <= 4.0
    if not ok_impl:
        bad += 1
    print("the float closed form c22c_source.py computes: %.20g" % closed)
    print("  against the exact value, in ulp of double: %.2f ulp (bound 4) -> %s"
          % (ulps, 'agrees' if ok_impl else '*** NO ***'))
    print()
    rec = Decimal(doc['families']['proportion']['record_3fig'])
    tol = half_unit_last_digit(doc['families']['proportion']['record_3fig'])
    ok = abs(Decimal('%.40g' % closed) - rec) <= tol
    if not ok:
        bad += 1
    print("proportion vs the record's %s: %+.3e, half a unit is %.1e -> %s"
          % (rec, float(Decimal('%.40g' % closed) - rec), float(tol),
             'agrees' if ok else '*** NO ***'))
    print()
    digest, canon = SRC.values_digest(path)
    print("values digest: %s" % digest)
    if bad:
        print()
        print("c22c_derive: FAIL (%d disagreement(s)) -- the carried values are "
              "NOT the derivations' output" % bad)
        return 1
    print()
    print("c22c_derive: PASS -- every carried value is its derivation's own "
          "output, ceiling-rounded to %d digits, stable at dps %d"
          % (digits, DPS_CONTROL))
    return 0


def main(argv):
    path = SRC.SOURCE
    mode = 'verify'
    families = set(SRC.FAMILIES_CARRIED)
    overrides = {}
    args = list(argv[1:])
    while args:
        a = args.pop(0)
        if a == '--restamp':
            mode = 'restamp'
        elif a == '--fast-families':
            families = {'collision'}
        elif a == '--record':
            if not args:
                sys.stderr.write("c22c_derive.py: --record needs "
                                 "FAMILY:N=VALUE\n")
                return 2
            spec = args.pop(0)
            try:
                lhs, val = spec.split('=', 1)
                fam, n_text = lhs.split(':', 1)
                overrides[(fam, int(n_text))] = val
            except ValueError:
                sys.stderr.write("c22c_derive.py: --record wants "
                                 "FAMILY:N=VALUE, got %r\n" % spec)
                return 2
        elif a.startswith('-'):
            sys.stderr.write("c22c_derive.py: unknown option %r\n" % a)
            return 2
        else:
            path = a
    if mode == 'restamp':
        return restamp(path, overrides)
    return verify(path, families)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
