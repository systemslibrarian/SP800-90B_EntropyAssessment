#!/usr/bin/env python3
"""THE ONE SOURCE for every C22c family ceiling, and its fast validation.

WHY THIS EXISTS (OC-125, closing the two-copies linkage).

`C22c` is the term `entropy_floor.py` subtracts from a reported min-entropy
figure, and it is a MAX over three estimator families at two bitstring
lengths: six numbers. Until this file, those six numbers were recorded in
SEVEN places at three different precisions:

    entropy_floor.py       C22C_FAMILIES_BY_N   all 6     SUBTRACTED
    compression_ceiling_exact.py  SCAN          comp x2   compared
    compression_ceiling_exact.py  TABULATED     comp x2   compared
    zalpha_ceiling_by_n.py        REC_COLL      coll x2   compared
    zalpha_ceiling_by_n.py        REC_COMP      comp x2   printed
    regression-constants.sh                     all 6     pinned
    band1-pair-mutations.sh                     comp x2, coll x1   mutated

and NOTHING compared the copy that was subtracted against the copy the
derivation verified. That is the defect. `compression_ceiling_exact.py` would
recompute the ceiling from SP 800-90B 6.3.4 step 7, compare it against the
literal sitting beside it in its own file, print AGREES -- and be entirely
unaffected by whatever `entropy_floor.py` actually subtracted. Measured
(OC-105, and again by the band-1 battery on 2026-10-26): mutating the
subtracted copy `3.3599e-3 -> 3.3700e-3` leaves `oracle-selftest` GREEN.

THE FIX IS NOT A SECOND CHECK, IT IS ONE OBJECT. The value that is verified
and the value that is subtracted are now the same string in the same file,
`c22c_source.json`, and every consumer reads it. A second copy is the defect,
not a convenience -- which is why `regression-constants.sh` pins a DIGEST of
these values rather than the values themselves: a hash held outside the file
it covers detects any drift without being a second recording of the number.

WHAT CHANGED NUMERICALLY, AND IN WHICH DIRECTION. The carried values are the
derivations' own output, not the record's 3-to-5-figure roundings. C22c (the
max) rises by 3.0036931585923617932e-8 bit at n = 1e6 and
1.249454251229696301e-9 bit at n = 8e6, both from the COMPRESSION family,
which binds at both lengths. C22c is subtracted, so a larger C22c means a
LOWER reported floor: the previous values subtracted too little, and the floor
they produced was permissive by exactly that amount. No published figure
changes materially -- 3.0e-8 bit against a C22c of 3.36e-3 bit -- and that is
not the reason for the fix.

THE REASON FOR THE FIX is that the 3.0e-8 bound held only while the two copies
happened to agree. An undetected drift in the subtracted copy moved the floor
by the size of the drift, in either direction, with the verification still
green. The unbounded exposure is what closes here; the measured 3.0e-8 is
incidental.

PARTLY MITIGATED BEFORE THIS FIX, BY ACCIDENT. `regression-constants.sh` was
written for the mutation-landing hazard (OC-121, after a battery killed
mid-arm left a live C22c mutation in the tree) and has pinned these six
literals by value ever since. That closed the fast-suite half of this defect
without anyone intending to: the work was aimed at mutation landing, not at
the linkage. The half it did not close is the one this file closes -- nothing
tied the subtracted number to the derivation's output.

ROUNDING. The derivations produce more digits than any consumer can use, so
the carried values are truncated, and the truncation is CEILING -- always
toward a larger subtraction, never a smaller one. That holds all the way down
to the float the floor subtracts: if the decimal string does not convert to a
float at or above itself, the next float upward is used. A floor that rounds
down subtracts too little, which is the direction the previous n = 1e6 value
got wrong, at 60.1% of its own tolerance.

DIGITS. Twenty significant digits, which is a measured choice, not a taste.
The compression bisection terminates at a bracket width of 1e-40 on p*, which
bounds the ceiling's own error near 1e-37; and both derivations are recomputed
at working precision dps 80 by `c22c_derive.py`, which asserts the first
twenty digits are unchanged. So an exact comparison at twenty digits tests the
derivation and not the arithmetic's last bits.

WHAT IS AND IS NOT IN SCOPE. The one-source rule is applied to the SIX FAMILY
CEILINGS -- the quantities C22c maxes over and the floor subtracts -- and to
the record's three-figure publications of those same six, which are a
different claim (does the derivation reproduce what OC-22 Part 3 printed) and
so are carried here too rather than in the file that checks them. The
derivations' INPUTS are not collapsed: `z_tool`, `z_spec`, `d` and `b` are
stated independently in each derivation, because a disagreement between two
independent statements of an input surfaces as a disagreement between the
derivations, which is the behaviour wanted. `c22c-copy-sweep.sh` enforces the
first and cross-checks the second.

Usage:
    c22c_source.py              the table, the stamps, the digest
    c22c_source.py --digest     the values digest alone, for a pin
    c22c_source.py --validate   validate and say nothing on success
Exit 0 if the source is well-formed, 1 if it is not. There is no third
outcome: a source that cannot be validated is not a source.
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from decimal import Decimal, localcontext, ROUND_CEILING

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'c22c_source.json')

FAMILIES_CARRIED = ('compression', 'collision')
FAMILIES_ALL = ('compression', 'collision', 'proportion')
STAMP_FIELDS = ('derivation', 'entry_point', 'derivation_sha256', 'produced',
                'working_precision_dps', 'stability_control',
                'validated_against', 'stamped_at_repo_commit')


class C22cSourceError(Exception):
    """The source is absent, malformed, unstamped, or self-inconsistent."""


def _fail(msg):
    raise C22cSourceError(msg)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def round_up(value_text, digits):
    """Truncate a decimal string to `digits` significant digits, CEILING."""
    with localcontext() as ctx:
        ctx.prec = digits
        ctx.rounding = ROUND_CEILING
        return +Decimal(value_text)


def sigdigits(text):
    """Significant digits of a decimal string, from the TEXT not the value.

    A value cannot carry its own precision -- that is the mistake F02 fixed in
    zalpha_ceiling_by_n.py and the mistake rule 16 generalises. So this reads
    the characters.
    """
    mant = text.split('e')[0].split('E')[0]
    mant = mant.replace('-', '').replace('+', '').replace('.', '')
    mant = mant.lstrip('0')
    if not mant:
        return 0
    return len(mant)


def as_float_not_below(text):
    """float(text), nudged upward if the conversion landed below the decimal.

    CEILING truncation in the source is pointless if the float conversion
    rounds the last digit back down. float() rounds to nearest, so it can land
    half an ulp below -- 1e-19 bit here, numerically nothing, but it is the
    wrong DIRECTION, and the direction is the whole decision.
    """
    f = float(text)
    if Decimal(f) < Decimal(text):
        f = math.nextafter(f, math.inf)
    return f


def proportion_ceiling(z_tool_text, z_spec_text):
    """The PROPORTION family ceiling, in closed form, exactly.

    NOT CARRIED, AND THE REASON IS WORTH STATING. For a proportion estimator
    the tool forms ub = p + z*sqrt(p(1-p)/(n-1)), and at the domain's left
    edge p = 1/n that square root is EXACTLY 1/n:

        p(1-p)/(n-1) = (1/n)(1 - 1/n)/(n-1) = ((n-1)/n^2)/(n-1) = 1/n^2

    so ub = (1+z)/n with no approximation, and the entropy gap between the two
    quantiles is log2((1+z_spec)/(1+z_tool)) -- independent of n, closed, and
    exact. The gap grows as p falls, so the left edge is the maximum (the
    domain is p >= 1/n because p-hat is mode/n with mode >= 1; an earlier sweep
    that ran below 1/n reported its own grid edge as a worst case).

    Carrying a value for a quantity that is one line of exact arithmetic would
    add a copy and buy nothing, so it is computed. Two consequences, recorded:
    the exact form is 6.886711443818211e-5, marginally SMALLER than the
    6.886875815e-5 first-order form the record tabulated as 6.887e-5, so this
    is the one family where full precision lowers the value; and it cannot
    affect C22c either way, because compression is 48.8x larger at n = 1e6 and
    31.4x at n = 8e6 and C22c is the max. `c22c_derive.py` confirms the closed
    form against zalpha_ceiling_by_n.py's numerical maximisation, which finds
    its argmax at p = 1/n and agrees to 25 digits.

    THE SUBTRACTION IS DONE IN DECIMAL, EXACTLY, and that is not fussiness.
    z_spec - z_tool = 1.706964511e-4 out of two numbers near 2.576, so in
    double the difference loses about four of its sixteen digits to
    cancellation and the result is good to only ~2e-12 relative -- measured at
    2.3e-12 before this was fixed. Both quantiles arrive as decimal STRINGS, so
    the subtraction and the division can be done exactly first and rounded to
    double once, which leaves the closed form accurate to a couple of ulp.
    """
    dz = Decimal(z_spec_text) - Decimal(z_tool_text)        # exact
    one_plus = Decimal(1) + Decimal(z_tool_text)            # exact
    x = float(dz / one_plus)                                # one rounding
    return math.log1p(x) / math.log(2.0)


# Claims that could not be checked here. NOT failures, and NOT silence either:
# the CLI and regression-constants.sh print them, so "this ran in a tree with
# no git history" is visible rather than indistinguishable from a clean pass.
UNVERIFIED = []


def _git_available():
    try:
        rc = subprocess.run(['git', '-C', HERE, 'rev-parse', '--git-dir'],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
    except OSError:
        return False
    return rc == 0


def _git_object_exists(commit):
    """True, False, or None when it cannot be determined.

    THE THREE-WAY RETURN IS DELIBERATE. The first version refused whenever git
    could not be run, on the principle that an uncheckable provenance field is
    not provenance -- which made this module, and therefore
    regression-constants.sh, refuse in a release tarball with no git history.
    That contradicts regression-constants.sh's own stated design, which exists
    precisely so the constants can be checked without git. So: a commit git
    says it does not have is a REFUSAL; a commit git cannot be asked about is
    recorded as unverified and printed. The field's FORMAT is checked either
    way, and the derivation sha256 -- the stronger claim -- needs no git at all.

    THE THIRD CASE, AND IT COST A RED CI RUN (OC-127). "No git at all" and "git
    with the whole history" are not the only trees this runs in. A SHALLOW or
    otherwise truncated clone is a git repository, answers `rev-parse
    --git-dir`, and still says it does not have a commit that is unquestionably
    in the repository's history -- because it was never fetched. The first
    version read that denial as the refusal case and said the stamp "is not a
    commit in this repository". It was: `actions/checkout@v4` defaults to
    `fetch-depth: 1`, so the CI tree held exactly one commit, and the stamp
    cited an ancestor eight commits back. Proven both ways on one tree: a
    `--depth=1` clone REFUSED, a full clone of the same commit PASSED.

    So a negative is only a refusal when the tree can actually answer -- when
    its history is complete. Where it is truncated the answer is unverified,
    like the no-git case. This weakens the check exactly where it cannot be
    made, and nowhere else; CI is given `fetch-depth: 0` so the check stays
    LIVE there rather than going quiet, which is the dead-guard hazard this
    repository has already measured (OC-95).
    """
    if not _git_available():
        UNVERIFIED.append("the stamped repo commit %s was not confirmed to "
                          "exist: no git repository here" % commit[:12])
        return None
    try:
        rc = subprocess.run(['git', '-C', HERE, 'cat-file', '-e', commit + '^{commit}'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    except OSError as exc:
        UNVERIFIED.append("the stamped repo commit %s was not confirmed to "
                          "exist: git could not be run (%s)" % (commit[:12], exc))
        return None
    if rc == 0:
        return True
    # Absent. Only a complete history may call that a refusal; see the
    # docstring's third case. Asked only on the negative, so a complete tree
    # pays nothing and the common path is unchanged.
    incomplete = _history_is_incomplete()
    if incomplete is not False:
        UNVERIFIED.append("the stamped repo commit %s was not confirmed to "
                          "exist: this tree's history is incomplete (%s), so "
                          "git cannot be asked about an ancestor it never "
                          "fetched" % (commit[:12], incomplete or "undetermined"))
        return None
    return False


def _history_is_incomplete():
    """Why this tree cannot answer about an arbitrary ancestor, or False.

    Returns a short reason string when the history is known to be truncated,
    False when it is known to be complete, and None when that could not be
    determined -- and None is treated as incomplete by the caller, because the
    refusal is the destructive answer and it should need a positive result to
    fire.

    Two truncations are detected. A SHALLOW clone (`--depth=N`) reports itself
    through `rev-parse --is-shallow-repository`. A PARTIAL clone (`--filter=`)
    records a promisor remote in its config; its commits are normally all
    present, but it can lazily fetch, so it is reported rather than trusted.
    """
    try:
        r = subprocess.run(['git', '-C', HERE, 'rev-parse',
                            '--is-shallow-repository'],
                           capture_output=True, text=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    if r.stdout.strip() == 'true':
        return "shallow clone"
    if r.stdout.strip() != 'false':
        return None
    try:
        r = subprocess.run(['git', '-C', HERE, 'config', '--get-regexp',
                            r'^remote\..*\.promisor$'],
                           capture_output=True, text=True)
    except OSError:
        return None
    # rc 1 is "no such key", which is the ordinary full-clone answer.
    if r.returncode == 0 and r.stdout.strip():
        return "partial clone with a promisor remote"
    if r.returncode not in (0, 1):
        return None
    return False


def _tracked_by_git(path):
    """Is the one source actually in the repository?

    OC-125 ADDED THIS AFTER NEARLY SHIPPING WITHOUT IT. `.gitignore` carried a
    blanket `*.json`, so the file every entropy figure now depends on was
    INVISIBLE to git. Committing the rest of the fix would have produced a
    repository whose floor refuses at import on any fresh clone, while working
    perfectly on the machine that wrote it. Nothing in the suite could have
    seen it: the file is present locally, so every check passed. It was caught
    by `git status` not listing it -- which is not a check, and is the same way
    the OC-121 mutation was caught.
    """
    if not _git_available():
        UNVERIFIED.append("the one source was not confirmed to be tracked: no "
                          "git repository here")
        return None
    try:
        rc = subprocess.run(['git', '-C', HERE, 'ls-files', '--error-unmatch', path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
    except OSError:
        UNVERIFIED.append("the one source was not confirmed to be tracked: git "
                          "could not be run")
        return None
    return rc == 0


def read_raw(path=None):
    path = path or SOURCE
    if not os.path.exists(path):
        _fail("the C22c source %s does not exist. Nothing is assumed and no "
              "value is defaulted: the floor's subtracted term has no other "
              "home since OC-125." % path)
    try:
        with open(path) as fh:
            text = fh.read()
    except OSError as exc:
        _fail("cannot read the C22c source %s: %s" % (path, exc))
    # parse_constant catches NaN/Infinity, which json accepts by default and
    # which A08 found an oracle silently propagating into a printed floor.
    try:
        return json.loads(text, parse_constant=lambda c: _fail(
            "the C22c source contains the non-finite JSON token %r" % c))
    except ValueError as exc:
        _fail("the C22c source %s is not valid JSON: %s" % (path, exc))


def validate(path=None, check_git=True):
    """Validate the source completely. Return the raw document.

    Every defect is its own distinct refusal, because several refusals sharing
    one accidental cause look exactly like several working guards.
    """
    doc = read_raw(path)
    path = path or SOURCE
    if doc.get('schema') != 'c22c-source/1':
        _fail("the C22c source declares schema %r, not 'c22c-source/1'"
              % doc.get('schema'))
    digits = doc.get('digits')
    if not isinstance(digits, int) or not 1 <= digits <= 40:
        _fail("the C22c source declares digits = %r, which is not an integer "
              "in 1..40" % (digits,))
    if doc.get('rounding') != 'ceiling':
        _fail("the C22c source declares rounding = %r. Only 'ceiling' is "
              "accepted: a floor that rounds its subtracted term down "
              "subtracts too little." % doc.get('rounding'))
    inputs = doc.get('inputs')
    if not isinstance(inputs, dict):
        _fail("the C22c source has no 'inputs' object")
    for key in ('z_tool', 'z_spec'):
        if not isinstance(inputs.get(key), str) or not inputs[key].strip():
            _fail("the C22c source's inputs.%s is absent or not a string" % key)
    fams = doc.get('families')
    if not isinstance(fams, dict) or not isinstance(fams.get('proportion'), dict):
        _fail("the C22c source has no families.proportion object. The "
              "proportion family is COMPUTED rather than carried, and the "
              "reason it is not carried has to be stated where the values "
              "live, or the absence of a value reads as an omission.")
    prop = fams['proportion']
    if prop.get('carried') is not False:
        _fail("the C22c source's families.proportion sets carried = %r. Only "
              "false is accepted: this file computes it in closed form, and a "
              "carried proportion value would be a copy."
              % (prop.get('carried'),))
    for field in ('computed_inline', 'record_3fig', 'why_not_carried',
                  'validated_against'):
        if not isinstance(prop.get(field), str) or not prop[field].strip():
            _fail("the C22c source's families.proportion has no %s. A missing "
                  "provenance field is a refusal, never a warning or a "
                  "default." % field)
    rows = doc.get('rows')
    if not isinstance(rows, list) or not rows:
        _fail("the C22c source has no 'rows' array")

    seen_n = []
    for row in rows:
        n = row.get('n')
        if not isinstance(n, int) or n <= 0:
            _fail("a C22c row has n = %r, which is not a positive integer" % (n,))
        if n in seen_n:
            _fail("the C22c source has two rows for n = %d" % n)
        seen_n.append(n)
        for fam in FAMILIES_CARRIED:
            cell = row.get(fam)
            if not isinstance(cell, dict):
                _fail("the C22c row n = %d has no %s cell" % (n, fam))
            text = cell.get('value')
            if not isinstance(text, str):
                _fail("the C22c %s cell at n = %d carries value %r, not a "
                      "string. The precision IS part of the datum and a float "
                      "literal does not carry it." % (fam, n, text))
            if not re.fullmatch(r'0\.0*[1-9][0-9]*', text):
                _fail("the C22c %s value at n = %d is %r, which is not a plain "
                      "positive decimal below 1" % (fam, n, text))
            got = sigdigits(text)
            if got != digits:
                _fail("the C22c %s value at n = %d carries %d significant "
                      "digits, and the source declares %d. The stamp must "
                      "match the carried value." % (fam, n, got, digits))
            if not isinstance(cell.get('record_3fig'), str):
                _fail("the C22c %s cell at n = %d has no record_3fig string "
                      "(the record's own published value, a separate claim)"
                      % (fam, n))
            stamp = cell.get('stamp')
            if not isinstance(stamp, dict):
                _fail("the C22c %s cell at n = %d has no stamp" % (fam, n))
            for field in STAMP_FIELDS:
                v = stamp.get(field)
                if v is None or (isinstance(v, str) and not v.strip()):
                    _fail("the C22c %s stamp at n = %d has no %s. A missing "
                          "provenance field is a refusal, never a warning or a "
                          "default." % (fam, n, field))
            deriv = stamp['derivation']
            if os.path.basename(deriv) != deriv:
                _fail("the C22c %s stamp at n = %d names derivation %r; a bare "
                      "filename beside this file is expected" % (fam, n, deriv))
            # RESOLVED AGAINST THIS MODULE'S DIRECTORY, NOT THE SOURCE
            # FILE'S. The derivations are oracles and live here; a source
            # handed in from somewhere else -- which is how every negative
            # control in oracle-selftest.sh is built, as a mutated copy in a
            # temporary directory -- must still be checked against the real
            # derivations. Resolving against the source's own directory made
            # THREE separate fixtures refuse for one shared accidental reason,
            # "that file is not in the tree", instead of for the defect each
            # was built to exercise. That is the A08 fault, in the validator
            # written to close a different one.
            dpath = os.path.join(HERE, deriv)
            if not os.path.exists(dpath):
                _fail("the C22c %s stamp at n = %d names derivation %s, which "
                      "is not in the tree" % (fam, n, deriv))
            actual = sha256_file(dpath)
            if actual != stamp['derivation_sha256']:
                _fail("the C22c %s value at n = %d was produced by %s at "
                      "sha256 %s, and that file is now sha256 %s. The "
                      "derivation changed since the value was stamped: re-run "
                      "c22c_derive.py --restamp and record the result. The "
                      "carried value is NOT assumed to still be its output."
                      % (fam, n, deriv, stamp['derivation_sha256'][:16],
                         actual[:16]))
            if not re.fullmatch(r'[0-9a-f]{40}', stamp['stamped_at_repo_commit']):
                _fail("the C22c %s stamp at n = %d records "
                      "stamped_at_repo_commit %r, which is not a 40-hex commit "
                      "id" % (fam, n, stamp['stamped_at_repo_commit']))
            if check_git and _git_object_exists(stamp['stamped_at_repo_commit']) is False:
                _fail("the C22c %s stamp at n = %d records repo commit %s, "
                      "which is not a commit in this repository"
                      % (fam, n, stamp['stamped_at_repo_commit'][:12]))
            if not isinstance(stamp['working_precision_dps'], int):
                _fail("the C22c %s stamp at n = %d records "
                      "working_precision_dps %r, not an integer"
                      % (fam, n, stamp['working_precision_dps']))
    # SCOPED TO THE REAL SOURCE, AND THAT SCOPE IS THE FIX FOR A FAULT THIS
    # CHECK CAUSED. The claim is "the REPOSITORY's one source is in the
    # repository". Applied to any path handed in, it fired on every negative
    # control in oracle-selftest.sh -- each of which is a mutated COPY in a
    # temporary directory, and so untracked by construction. The row-order
    # fixture then refused for "not tracked by git" instead of for the row
    # order, which is the A08 fault again: several fixtures refusing for one
    # shared accidental reason, testing nothing. The others happened to fail
    # earlier in the loop and hid it.
    #
    # No fixture exercises this limb, deliberately: the only way to make the
    # real source untracked is to untrack it. It was observed failing against
    # the genuine condition instead -- `.gitignore`'s blanket *.json had hidden
    # the file, and `--validate` refused until it was staged (OC-125).
    if check_git and os.path.abspath(path) == os.path.abspath(SOURCE) \
       and _tracked_by_git(os.path.abspath(path)) is False:
        _fail("the C22c source %s is NOT TRACKED BY GIT. It is the only "
              "recording of the values entropy_floor.py subtracts, and that "
              "module refuses at import without it -- so a clone of this "
              "repository could not compute a floor at all. Check .gitignore: "
              "a blanket *.json rule once hid exactly this file." % path)
    if seen_n != sorted(seen_n, reverse=True):
        _fail("the C22c source's rows are not in descending n order: %s. The "
              "lookup takes the first row with n0 <= n, so the order is part "
              "of the meaning." % seen_n)
    return doc


def families_by_n(path=None, check_git=True):
    """((n0, {family: float}), ...) descending by n0 -- what the floor uses."""
    doc = validate(path, check_git=check_git)
    prop = proportion_ceiling(doc['inputs']['z_tool'], doc['inputs']['z_spec'])
    out = []
    for row in doc['rows']:
        fam = {f: as_float_not_below(row[f]['value']) for f in FAMILIES_CARRIED}
        fam['proportion'] = prop
        out.append((row['n'], fam))
    return tuple(out)


def values_digest(path=None, check_git=True):
    """sha256 over the carried family values, canonically.

    WHAT THIS IS FOR. `regression-constants.sh` has to detect a drift in these
    six numbers inside the fast suite, and it cannot re-run a derivation that
    takes forty seconds. If it held the values, it would be a second copy --
    the defect. So it holds this digest: a hash, kept outside the file it
    covers, which is a comparison of VALUES and not of markers while being one
    64-character string.

    The canonical form includes only n, family and the value text -- not the
    stamps, not the record figures, not whitespace or key order -- so the
    digest moves if and only if a subtracted number moves.
    """
    doc = validate(path, check_git=check_git)
    lines = []
    for row in sorted(doc['rows'], key=lambda r: r['n']):
        for fam in FAMILIES_CARRIED:
            lines.append('%d:%s=%s\n' % (row['n'], fam, row[fam]['value']))
    canon = ''.join(lines)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest(), canon


def value_text(family, n, path=None):
    """The carried value string for one family at one row, verbatim.

    EXISTS SO THAT NO CALLER HAS TO NAME A NUMBER. The mutation battery has to
    know the exact string it replaces, and `c22c-copy-sweep.sh` has to build a
    positive control containing a genuine family value. Both used to do that by
    carrying a literal -- which would make the sweep's own control, and the
    battery that proves the guard works, two more copies of the thing being
    collapsed. They ask for it instead.
    """
    doc = validate(path)
    if family not in FAMILIES_CARRIED:
        _fail("%r is not a carried family; carried: %s"
              % (family, ', '.join(FAMILIES_CARRIED)))
    for row in doc['rows']:
        if row['n'] == n:
            return row[family]['value']
    _fail("the C22c source has no row for n = %d; rows: %s"
          % (n, ', '.join(str(r['n']) for r in doc['rows'])))


def stamp_field(family, n, field, path=None):
    """One field of one stamp, verbatim -- for a caller that must break it."""
    doc = validate(path)
    for row in doc['rows']:
        if row['n'] == n:
            if family not in row:
                _fail("%r is not a carried family" % family)
            v = row[family]['stamp'].get(field)
            if v is None:
                _fail("the %s stamp at n = %d has no %s" % (family, n, field))
            return str(v)
    _fail("the C22c source has no row for n = %d" % n)


def perturb(text):
    """The same decimal with its 5th significant digit moved.

    THIS LIVES HERE RATHER THAN IN THE MUTATION BATTERY, for two reasons that
    are both about not writing a number down twice. The battery needs a value
    DIFFERENT from a carried one, and computing it from the carried string
    means the battery still names no number -- c22c-copy-sweep.sh reports it
    when it does. And the shell heredoc that used to do this made
    regression-deadguard.sh flag the battery twice as "heredoc carries
    assertions, status never read": the status IS read by the caller, but a
    baseline carrying a false positive is worse than one carrying none, so
    the code is written the way the detector can read it. Same decision as
    oracle-selftest.sh's single-line python3 invocation.

    A drift of about 1e-4 relative: far larger than any rounding this source
    performs, far smaller than a typo, and the size of change a guard on a
    subtracted constant has to see.
    """
    m = re.search(r'[1-9]', text)
    if not m:
        _fail("no significant digit in %r, so there is nothing to perturb" % text)
    seen = 0
    for i in range(m.start(), len(text)):
        if text[i].isdigit():
            seen += 1
            if seen == 5:
                return text[:i] + str((int(text[i]) + 1) % 10) + text[i + 1:]
    _fail("fewer than 5 significant digits in %r" % text)


def main(argv):
    path = None
    mode = 'show'
    want = []
    args = list(argv[1:])
    while args:
        a = args.pop(0)
        if a == '--digest':
            mode = 'digest'
        elif a == '--validate':
            mode = 'validate'
        elif a in ('--value', '--stamp-sha'):
            mode = a[2:]
            if len(args) < 2:
                sys.stderr.write("c22c_source.py: %s needs a family and an n\n" % a)
                return 1
            want = [args.pop(0), args.pop(0)]
        elif a == '--perturb':
            mode = 'perturb'
            if not args:
                sys.stderr.write("c22c_source.py: --perturb needs a value\n")
                return 1
            want = [args.pop(0)]
        elif a.startswith('-'):
            sys.stderr.write("c22c_source.py: unknown option %r\n" % a)
            return 1
        elif path is None:
            path = a
        else:
            sys.stderr.write("c22c_source.py: one path at most\n")
            return 1
    if mode == 'value':
        try:
            print(value_text(want[0], int(want[1]), path))
        except (C22cSourceError, ValueError) as exc:
            sys.stderr.write("c22c_source: REFUSED\n  %s\n" % exc)
            return 1
        return 0
    if mode == 'stamp-sha':
        try:
            print(stamp_field(want[0], int(want[1]), 'derivation_sha256', path))
        except (C22cSourceError, ValueError) as exc:
            sys.stderr.write("c22c_source: REFUSED\n  %s\n" % exc)
            return 1
        return 0
    if mode == 'perturb':
        try:
            print(perturb(want[0]))
        except (C22cSourceError, ValueError) as exc:
            sys.stderr.write("c22c_source: REFUSED\n  %s\n" % exc)
            return 1
        return 0
    try:
        digest, canon = values_digest(path)
        doc = validate(path)
    except C22cSourceError as exc:
        sys.stderr.write("c22c_source: REFUSED\n  %s\n" % exc)
        return 1
    if mode == 'digest':
        print(digest)
        return 0
    if mode == 'validate':
        return 0
    prop = proportion_ceiling(doc['inputs']['z_tool'], doc['inputs']['z_spec'])
    print("C22c -- the one source, %d significant digits, rounded %s"
          % (doc['digits'], doc['rounding']))
    print()
    print("| n | family | carried value | record 3 fig | derivation |")
    print("|---:|---|---:|---:|---|")
    for row in doc['rows']:
        for fam in FAMILIES_CARRIED:
            c = row[fam]
            print("| %d | %s | %s | %s | %s |"
                  % (row['n'], fam, c['value'], c['record_3fig'],
                     c['stamp']['derivation']))
        print("| %d | proportion | %.20g | %s | computed inline, closed form |"
              % (row['n'], prop, doc['families']['proportion']['record_3fig']))
    print()
    for row in doc['rows']:
        fam = {f: as_float_not_below(row[f]['value']) for f in FAMILIES_CARRIED}
        fam['proportion'] = prop
        binding = max(fam, key=lambda k: fam[k])
        runner = max((k for k in fam if k != binding), key=lambda k: fam[k])
        print("n >= %-9d C22c = %.17g  binding: %-12s %.3fx the runner-up (%s)"
              % (row['n'], fam[binding], binding,
                 fam[binding] / fam[runner], runner))
    print()
    print("values digest (sha256 of %d canonical lines): %s"
          % (len(canon.splitlines()), digest))
    for u in dict.fromkeys(UNVERIFIED):
        print("NOT VERIFIED HERE: %s" % u)
    print("the slow check that re-derives these: c22c_derive.py")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
