#!/usr/bin/env python3
"""The tree-shape classification in c22c_source.py, driven by stubbed git.

WHY THIS EXISTS, AND WHY IT IS NOT A CLONE TEST (OC-128, rule 18).

`OC-127` was not a bug in how git was called. Every git call was correct and
every answer git gave was true. The defect was the CASE LIST: the code
enumerated "no git" and "git with the whole history" and branched as though
those were the only trees, so a SHALLOW clone -- which is a git repository, and
answers `rev-parse --git-dir` -- took the branch meant for a commit that
genuinely does not exist. A correct rule with an incomplete enumeration.

So what needs a standing test is the ENUMERATION, and the enumeration is a pure
function of what git returns. This fixture replaces `subprocess.run` with a
table of scripted git answers and checks the classification for each tree shape,
including the one that was missing. It runs in milliseconds and needs no clone.

WHAT THIS DOES NOT TEST, stated because the gap is the point:

  * It does NOT test the real git interaction. Whether `git rev-parse
    --is-shallow-repository` actually prints `true` in a `--depth=1` clone, or
    whether a promisor remote actually sets `remote.origin.promisor`, is NOT
    checked here -- those were measured by hand against real clones in
    `OC-127`, and that measurement is dated evidence, not a test.
  * It therefore cannot catch git changing its interface. If a future git
    renamed `--is-shallow-repository`, this fixture would still pass while the
    real classification silently degraded to "complete history" -- which, note,
    is the DESTRUCTIVE direction. A clone-based test is the only thing that
    would catch that, and it is not built.
  * It covers five shapes plus an exception path. "Truncated history" is not
    enumerated: grafts and replace refs are not tried, with the reason given in
    `OC-127` -- they were never measured, so nothing here would be evidence.

It DOES catch the failure that actually happened: the case list losing a shape.
"""
import importlib.util, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location(
    'c22c_source_under_test', os.path.join(HERE, 'c22c_source.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

COMMIT = 'a' * 40


class FakeCompleted:
    def __init__(self, rc, out=''):
        self.returncode = rc
        self.stdout = out
        self.stderr = ''


def stub(shape):
    """A fake subprocess.run answering git the way `shape` would."""
    def run(argv, **kw):
        if argv[0] != 'git':
            raise AssertionError('the module shelled out to %r, not git' % argv[0])
        if shape == 'no-git-binary':
            raise OSError('no git here')
        sub = argv[3] if len(argv) > 3 else ''
        rest = argv[4:] if len(argv) > 4 else []
        # git works for the availability probe, then disappears before the
        # object lookup. This is the ONLY way to reach the "git could not be
        # run" limb: with no git at all, `_git_available()` is asked first and
        # answers no, so that limb is otherwise unreachable. Writing this
        # fixture is what established that -- the first version expected "could
        # not be run" for a missing binary and the fixture said otherwise.
        if shape == 'git-vanishes-midway' and sub == 'cat-file':
            raise OSError('git went away')

        if sub == 'rev-parse' and '--git-dir' in rest:
            return FakeCompleted(128 if shape == 'no-repo' else 0, '.git\n')
        if sub == 'rev-parse' and '--is-shallow-repository' in rest:
            if shape == 'shallow':
                return FakeCompleted(0, 'true\n')
            if shape == 'ancient-git':          # the option is not understood
                return FakeCompleted(129, '')
            return FakeCompleted(0, 'false\n')
        if sub == 'config':
            if shape == 'promisor':
                return FakeCompleted(0, 'remote.origin.promisor true\n')
            return FakeCompleted(1, '')         # no such key: the ordinary answer
        if sub == 'cat-file':
            return FakeCompleted(0 if shape == 'full-present' else 1, '')
        raise AssertionError('unscripted git call: %r' % (argv,))
    return run


# shape, expected _git_object_exists(COMMIT), expected substring in UNVERIFIED
CASES = [
    ('full-present', True,  None),
    ('full-absent',  False, None),              # the REFUSAL must stay live
    ('shallow',      None,  'shallow clone'),
    ('promisor',     None,  'partial clone with a promisor remote'),
    ('no-repo',      None,  'no git repository here'),
    ('ancient-git',  None,  'undetermined'),    # cannot be determined -> not a refusal
    # NOT 'git could not be run': `_git_available()` is asked first and a
    # missing binary fails there, so this is the no-repository note. The
    # distinction is recorded because the first draft of this fixture got it
    # wrong and the fixture corrected it.
    ('no-git-binary', None, 'no git repository here'),
    ('git-vanishes-midway', None, 'git could not be run'),
]

real_run = subprocess.run
fails = []
for shape, want, want_note in CASES:
    mod.UNVERIFIED[:] = []
    subprocess.run = stub(shape)
    try:
        got = mod._git_object_exists(COMMIT)
    except Exception as exc:                    # noqa: BLE001 - a raise is a failure here
        got = 'raised %r' % (exc,)
    finally:
        subprocess.run = real_run
    notes = ' | '.join(mod.UNVERIFIED)

    if got is not want:
        fails.append('%-14s returned %r, wanted %r' % (shape, got, want))
        continue
    if want_note is None:
        if notes:
            fails.append('%-14s recorded an unverified note it should not: %s'
                         % (shape, notes))
        continue
    if want_note not in notes:
        fails.append('%-14s note was %r, wanted a mention of %r'
                     % (shape, notes or '(none)', want_note))

print('git-classification: %d tree shapes driven by stubbed git' % len(CASES))
for shape, want, note in CASES:
    print('  %-14s -> %-5s %s' % (shape, want, note or '(no note expected)'))

if fails:
    print('\ngit-classification: FAIL')
    for f in fails:
        print('  ' + f)
    sys.exit(1)
print('\ngit-classification: PASS -- every shape classified, and the refusal '
      'is live on a complete history')
