#!/bin/bash
#
# Build-provenance canary for the SP 800-90B assessment tools.
#
# THE QUESTION THIS ANSWERS -- changed 2026-10-18
#
# Until the 2026-10-15 merge (master d226f18) this script answered one question:
# were asserts compiled in, or was the binary built -DNDEBUG? That mattered
# because the UNREPAIRED tool gave a different answer in each build on one
# input -- asserts live aborted, -DNDEBUG fabricated a figure (XR-04, OC-10).
# The repair closes that: both builds of the repaired tool refuse the same
# input identically (build-differential, REPAIR-STRATEGY.md). So on master the
# NDEBUG question has nothing behind it, and a canary that keeps asking it
# reports INDETERMINATE for every repaired binary -- measured, both builds,
# audits/2026-10-11-independent-audit/logs/merge/canary-*.log, and TruePad's
# harness treats INDETERMINATE as a refusal (XR-08).
#
# The question that matters now is: IS THIS BINARY FROM THE REPAIRED TREE OR
# THE UNREPAIRED ONE? The same control input discriminates it, because the two
# trees cannot both be right about it:
#
#   REPAIRED     refuses -- exit 1, errorLevel 2, "IID test suite failed", no
#                hAssessed -- in EITHER build. The build is not distinguished
#                because the repaired tree gives the same answer in both.
#   UNREPAIRED   the old tool, in one of two builds, both reported as
#                UNREPAIRED with the build kept as a sub-result (it still
#                matters for the reference figure built from the tag):
#                  ASSERTS-LIVE  aborts, SIGABRT 134, assert at lrs_test.h:683
#                  NDEBUG        exit 0, LRS failure reported, figure published
#   INDETERMINATE matches none of the three. Still not a pass.
#
# WHAT THIS DOES NOT ESTABLISH -- read this before relying on it
#
#   * It does not establish the commit the binary was built from, only which of
#     the two trees' behaviours it has on this input.
#   * It does not establish the compiler, its version, or any flag. It says
#     nothing about -ffloat-store, which cpp/Makefile sets and which a packager
#     overriding CXXFLAGS loses.
#   * It does not establish that the binary is unmodified.
#   * REPAIRED does not mean reviewed: the repairs are self-authored and
#     unreviewed, and this canary does not change that.
#   * A result is a statement about the binary you passed in, at the moment you
#     ran this. It is not a property of a figure produced earlier.
#
# Building the tools yourself from a pinned commit with known flags is strictly
# stronger and should be preferred whenever possible. The unrepaired tool is at
# tag unrepaired-reference-2026-10-15 (BUILDING.md, "The unrepaired reference
# tool"); the repaired one is master at or after d226f18.
#
# EXIT STATUS
#   0  positively identified; the identification is on stdout as
#        canary: TREE    REPAIRED | UNREPAIRED
#        canary: BUILD   ASSERTS-LIVE | NDEBUG | NOT-DISTINGUISHED
#   3  INDETERMINATE -- matched no signature. Not a pass. Refuse the figure.
#   2  usage or environment error (tool missing, cannot generate the input)
#
# USAGE
#   tools/build-provenance-canary.sh <path-to-ea_iid> [work-directory]
#
# Environment: CANARY_TIMEOUT (seconds, default 1800), OMP_NUM_THREADS

set -u

PROG=$(basename "$0")

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $PROG <path-to-ea_iid> [work-directory]" >&2
    exit 2
fi

TOOL=$1
WORK=${2:-}

if [ ! -x "$TOOL" ]; then
    echo "$PROG: not an executable: $TOOL" >&2
    exit 2
fi

if [ -z "$WORK" ]; then
    WORK=$(mktemp -d "${TMPDIR:-/tmp}/sp90b-canary.XXXXXX") || exit 2
    trap 'rm -rf "$WORK"' EXIT HUP INT TERM
else
    mkdir -p "$WORK" || exit 2
fi

INPUT="$WORK/canary-lrsrep-20000.bin"
EXPECTED_SHA="327773dd47cc480794f205f306aadd20972e258d9b0b880b7d12ad992e0b468c"

# ---------------------------------------------------------------- the input
#
# 1,000,000 one-bit samples from a fixed seed, with a 20000-sample block copied
# over a later position so the longest repeated substring is at least 20000.
#
# PLATFORM LIMIT (corrected 2026-10-18, OC-24). Three long double formats:
#   IEEE double    Apple arm64 (MEASURED here)   53-bit, emin -1021,  floor 2^-1074
#   x87 extended   x86-64                        64-bit, emin -16382, floor 2^-16445
#   binary128      Linux aarch64                113-bit, emin -16382, floor 2^-16494
#
#   UNREPAIRED side. p_colPower = p_col^W must fall below LDBL_MIN: W > 1022 on
#   IEEE double, W > 16382 on BOTH wide formats (they share the exponent
#   range; the narrow one is the measured platform). At W = 20000, 2^-20000 is
#   below the subnormal floor of all three, so powl returns +0 everywhere and
#   the abort / fabrication signatures follow identically. The formats DO
#   diverge for W in 1022..16382 -- which is why this input is W = 20000.
#
#   REPAIRED side. The log-domain LRS forms W*log(p_col) ~ -13863 (always
#   representable) and the decision compares it against ~ -20.7: false by a
#   13842 log-unit margin on every format; no comparison sits near a rounding
#   boundary and no double intermediate is on an underflow path. This is an
#   ARGUMENT from reading lrs_test.h, confirmed numerically on one format.
#
#   Measured on IEEE double only (all five outcomes, logs/merge/canary3-*.log).
#   What would settle the wide formats is one canary run on an x86-64 host.
#
# The file is generated rather than shipped so this script stays self-contained
# and the input is verifiable from its seed.

python3 - "$INPUT" <<'PY' || { echo "$PROG: could not generate the canary input" >&2; exit 2; }
import random, sys, hashlib
r = random.Random(0x90B2026C07)
b = bytearray(r.getrandbits(1) for _ in range(1000000))
W = 20000
b[600000:600000 + W] = bytes(b[1000:1000 + W])
d = bytes(b)
open(sys.argv[1], 'wb').write(d)
sys.stderr.write("canary input sha256 %s\n" % hashlib.sha256(d).hexdigest())
PY

if [ ! -s "$INPUT" ]; then
    echo "$PROG: canary input was not written" >&2
    exit 2
fi

# The input must be the one the signatures below were calibrated against. A
# declared-but-unchecked expected digest would be a dead assertion, which is the
# exact defect shape this canary exists because of.
if command -v shasum >/dev/null 2>&1; then
    ACTUAL_SHA=$(shasum -a 256 "$INPUT" | cut -d' ' -f1)
elif command -v sha256sum >/dev/null 2>&1; then
    ACTUAL_SHA=$(sha256sum "$INPUT" | cut -d' ' -f1)
else
    echo "$PROG: no SHA-256 utility; cannot confirm the canary input" >&2
    exit 2
fi
if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
    echo "$PROG: canary input digest mismatch -- the generator or python RNG differs" >&2
    echo "$PROG:   expected $EXPECTED_SHA" >&2
    echo "$PROG:   actual   $ACTUAL_SHA" >&2
    echo "$PROG: refusing to classify against an input the signatures were not calibrated on" >&2
    exit 2
fi
echo "canary: digest  $ACTUAL_SHA (matches)"

# ---------------------------------------------------------------- the probe

OUT="$WORK/canary.out"
JSON="$WORK/canary.json"
rm -f "$JSON"

OMP_NUM_THREADS=${OMP_NUM_THREADS:-2} timeout "${CANARY_TIMEOUT:-1800}" \
    "$TOOL" -i -v -o "$JSON" "$INPUT" 1 >"$OUT" 2>&1
RC=$?

# ------------------------------------------------------- the three signatures
#
# Deliberately behavioural rather than numeric. Pinning the unrepaired NDEBUG
# figure (about 0.9959 here) would make the canary fail on any build whose
# arithmetic differs slightly, and a canary that reports INDETERMINATE for a
# legitimate build is a canary nobody keeps using.

# json_check <mode>: REPAIRED needs errorLevel 2 and NO hAssessed;
#                    NDEBUG needs a figure AND the LRS test reported failed.
json_check() {
    [ -s "$JSON" ] || return 1
    python3 - "$JSON" "$1" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
tcs = d.get('testCases') or []
has_figure = any('hAssessed' in t for t in tcs)
lrs_failed = any(t.get('passedLongestRepeatedSubstringTest') is False for t in tcs)
if sys.argv[2] == 'REPAIRED':
    sys.exit(0 if (d.get('errorLevel') == 2 and not has_figure) else 1)
sys.exit(0 if (has_figure and lrs_failed) else 1)
PY
}

repaired=0
unrep_live=0
unrep_ndebug=0

# REPAIRED (either build): exit 1, the suite-failed line, errorLevel 2, no figure.
if [ "$RC" -eq 1 ] && grep -q "IID test suite failed" "$OUT" \
   && grep -qiE "Failed length of longest repeated substring" "$OUT" \
   && json_check REPAIRED; then
    repaired=1
fi

# UNREPAIRED, asserts live: aborted, and the abort names the site.
#
# The two libcs word an assertion failure differently, and the first version of
# this matched only one of them:
#   macOS/clang  Assertion failed: (p_colPower >= LDBL_MIN), function ..., file lrs_test.h, line 683.
#   glibc        ea_iid: shared/lrs_test.h:683: ...: Assertion `p_colPower >= LDBL_MIN' failed.
# Matching the literal "Assertion failed" made this signature macOS-only, so on
# x86-64 Linux an UNREPAIRED asserts-live build aborted at exactly the predicted
# site -- lrs_test.h:683, p_colPower >= LDBL_MIN, which is what OC-24 argued
# would happen -- and this canary nonetheless reported INDETERMINATE. MEASURED
# on the x86-64 CI job of 2026-10-19, not argued (OC-40). The direction was
# conservative (INDETERMINATE means refuse the figure), but it is a defect in
# the instrument: match both wordings.
if [ "$RC" -eq 134 ] \
   && grep -qi "assertion" "$OUT" && grep -qi "failed" "$OUT" \
   && grep -q "lrs_test.h" "$OUT"; then
    unrep_live=1
fi

# UNREPAIRED, -DNDEBUG: completed, LRS failure reported, and a figure published.
if [ "$RC" -eq 0 ] && grep -qiE "Failed length of longest repeated substring" "$OUT" \
   && json_check NDEBUG; then
    unrep_ndebug=1
fi

echo "canary: tool    $TOOL"
echo "canary: input   $INPUT (1,000,000 one-bit samples, implanted repeat W=20000)"
echo "canary: exit    $RC"

matched=$((repaired + unrep_live + unrep_ndebug))

if [ "$matched" -eq 1 ] && [ "$repaired" -eq 1 ]; then
    echo "canary: TREE    REPAIRED"
    echo "canary: BUILD   NOT-DISTINGUISHED"
    echo "canary: meaning the binary has the repaired tree's behaviour: the IID verdict"
    echo "canary:         fails closed (errorLevel 2) and the LRS probability is formed in"
    echo "canary:         the log domain, so asserts-live and -DNDEBUG give the same"
    echo "canary:         answer and the build cannot be told apart from here -- by design."
    echo "canary: NOTE    REPAIRED is not REVIEWED: the repairs are self-authored and"
    echo "canary:         unreviewed. This does not establish the commit, the compiler,"
    echo "canary:         other flags, or that the binary is unmodified. Building from"
    echo "canary:         the pinned commit is stronger."
    exit 0
fi

if [ "$matched" -eq 1 ] && [ "$unrep_live" -eq 1 ]; then
    echo "canary: TREE    UNREPAIRED"
    echo "canary: BUILD   ASSERTS-LIVE"
    echo "canary: meaning the old tool (tag unrepaired-reference-2026-10-15 or earlier),"
    echo "canary:         with the assert at shared/lrs_test.h:683 compiled in. On this"
    echo "canary:         input it aborts and publishes no figure. This is the reference"
    echo "canary:         build for the two-figure rule; it carries C07 and C03."
    echo "canary: NOTE    This does not establish the commit, the compiler, other flags,"
    echo "canary:         or that the binary is unmodified."
    exit 0
fi

if [ "$matched" -eq 1 ] && [ "$unrep_ndebug" -eq 1 ]; then
    echo "canary: TREE    UNREPAIRED"
    echo "canary: BUILD   NDEBUG"
    echo "canary: meaning the old tool with asserts compiled OUT. On this input it"
    echo "canary:         published a min-entropy figure derived from an underflow, after"
    echo "canary:         reporting an LRS failure it did not detect."
    echo "canary:         ANY FIGURE FROM THIS BINARY IS UNINTERPRETABLE."
    exit 0
fi

echo "canary: TREE    INDETERMINATE"
echo "canary: BUILD   INDETERMINATE"
echo "canary: The outcome matched none of the three signatures ($matched matched). NOT a pass."
echo "canary: Refuse any figure from this binary until provenance is established"
echo "canary: by other means. Known causes of a legitimate INDETERMINATE:"
echo "canary:   * a timeout (CANARY_TIMEOUT, currently ${CANARY_TIMEOUT:-1800}s)"
echo "canary:   * a tool that is not ea_iid"
echo "canary:   * a long double format other than the three in the header (W=20000"
echo "canary:     is below every known subnormal floor; see OC-24)"
echo "canary: ---- captured output (last 10 lines) ----"
tail -10 "$OUT" | sed 's/^/canary:   /'
exit 3
