#!/bin/bash
#
# Build-provenance canary for the SP 800-90B assessment tools.
#
# WHY THIS EXISTS
#
# These tools behave differently depending on whether they were compiled with
# -DNDEBUG, which no target in cpp/Makefile sets but which release
# configurations in common build systems add by default. On one specific input
# the difference is not a rounding detail, it is a different answer:
#
#   asserts live   ea_iid aborts (SIGABRT, exit 134), writes no JSON, and
#                  therefore publishes no figure.
#   -DNDEBUG       the assert at shared/lrs_test.h:683 is compiled out,
#                  p_colPower underflows to zero, log1pl(-0.0) is -0.0, and the
#                  verdict `logl(0.999) >= N*logProbNoColsPerPair` evaluates
#                  false -- so the longest-repeated-substring test reports
#                  FAILURE having detected nothing about the data. On master a
#                  second defect discards that failure, and the tool exits 0
#                  with errorLevel 0, "IID": true and a published min-entropy
#                  figure of roughly 0.9954 bit/bit.
#
# Nothing in the tools' JSON records which build produced it. A figure is
# therefore not interpretable without establishing build provenance separately.
# This script establishes ONE BIT of that provenance: whether asserts are live.
#
# WHAT THIS DOES NOT ESTABLISH -- read this before relying on it
#
#   * It does not establish the commit the binary was built from.
#   * It does not establish the compiler, its version, or any flag other than
#     the presence or absence of NDEBUG. In particular it says nothing about
#     -ffloat-store, which cpp/Makefile sets and which a packager overriding
#     CXXFLAGS also loses.
#   * It does not establish that the binary is unmodified.
#   * A reported build is a statement about the binary you passed in, at the
#     moment you ran this. It is not a property of a figure produced earlier by
#     some other binary.
#
# Building the tools yourself from the pinned commit with known flags is
# strictly stronger than this canary and should be preferred whenever possible.
# This exists for consumers who did not compile them.
#
# EXIT STATUS
#   0  the build was positively identified; the identification is on stdout
#   3  INDETERMINATE -- the outcome matched no known signature. This is not a
#      pass. An unidentifiable build means refuse the figure, not assume it.
#   2  usage or environment error (tool missing, cannot generate the input)
#
# USAGE
#   tools/build-provenance-canary.sh <path-to-ea_iid> [work-directory]

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

INPUT="$WORK/canary-lrsrep-2000.bin"
EXPECTED_SHA="a803412ee2c496a6d1c8c047be641c5d8b502a9c7556f66d678b541ec19fb5f2"

# ---------------------------------------------------------------- the input
#
# 1,000,000 one-bit samples from a fixed seed, with a 2000-sample block copied
# over a later position so the longest repeated substring is at least 2000.
#
# The threshold that matters: p_colPower = p_col^W underflows a 64-bit long
# double once W exceeds about 1022 (p_col is about 0.5, LDBL_MIN is 2.225e-308).
# W = 2000 clears that with margin. On an 80-bit long double the same bound is
# W > 16382, so THIS CANARY DOES NOT DISCRIMINATE ON SUCH A PLATFORM -- see the
# INDETERMINATE note at the bottom.
#
# The file is generated rather than shipped so this script stays self-contained
# and the input is verifiable from its seed.

python3 - "$INPUT" <<'PY' || { echo "$PROG: could not generate the canary input" >&2; exit 2; }
import random, sys, hashlib
r = random.Random(0x90B2026C07)
b = bytearray(r.getrandbits(1) for _ in range(1000000))
W = 2000
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

# --------------------------------------------------------- the two signatures
#
# Deliberately behavioural rather than numeric. The figure under NDEBUG is about
# 0.9954 on this platform, but pinning that number would make the canary fail on
# any build whose arithmetic differs slightly, and a canary that reports
# INDETERMINATE for a legitimate build is a canary nobody keeps using.

asserts_live=0
ndebug=0

# ASSERTS LIVE: aborted, and the abort names the site.
if [ "$RC" -eq 134 ] && grep -q "Assertion failed" "$OUT" && grep -q "lrs_test.h" "$OUT"; then
    asserts_live=1
fi

# NDEBUG: completed, the LRS test reported failure, and a figure was published.
if [ "$RC" -eq 0 ] && grep -qiE "Failed length of longest repeated substring" "$OUT"; then
    if [ -s "$JSON" ] && python3 - "$JSON" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
tcs = d.get('testCases') or []
has_figure = any('hAssessed' in t for t in tcs)
lrs_failed = any(t.get('passedLongestRepeatedSubstringTest') is False for t in tcs)
sys.exit(0 if (has_figure and lrs_failed) else 1)
PY
    then
        ndebug=1
    fi
fi

echo "canary: tool    $TOOL"
echo "canary: input   $INPUT (1,000,000 one-bit samples, implanted repeat W=2000)"
echo "canary: exit    $RC"

if [ "$asserts_live" -eq 1 ] && [ "$ndebug" -eq 0 ]; then
    echo "canary: BUILD   ASSERTS-LIVE"
    echo "canary: meaning the assert at shared/lrs_test.h:683 is compiled in."
    echo "canary:         On this input the tool fails closed and publishes no figure."
    echo "canary: NOTE    This identifies the NDEBUG state only. It does not establish"
    echo "canary:         the commit, the compiler, other flags, or that the binary is"
    echo "canary:         unmodified. Building from the pinned commit is stronger."
    exit 0
fi

if [ "$ndebug" -eq 1 ] && [ "$asserts_live" -eq 0 ]; then
    echo "canary: BUILD   NDEBUG"
    echo "canary: meaning asserts are compiled OUT."
    echo "canary:         On this input the tool published a min-entropy figure derived"
    echo "canary:         from an underflow, after reporting an LRS failure it did not"
    echo "canary:         detect. ANY FIGURE FROM THIS BINARY IS UNINTERPRETABLE."
    echo "canary: NOTE    This identifies the NDEBUG state only; see the header."
    exit 0
fi

echo "canary: BUILD   INDETERMINATE"
echo "canary: The outcome matched neither signature. This is NOT a pass."
echo "canary: Refuse any figure from this binary until provenance is established"
echo "canary: by other means. Known causes of a legitimate INDETERMINATE:"
echo "canary:   * an 80-bit long double platform (x86-64), where the underflow"
echo "canary:     bound is W > 16382 and W=2000 does not reach it, so an"
echo "canary:     asserts-live build completes normally and looks like neither"
echo "canary:     signature. This canary discriminates on 64-bit long double"
echo "canary:     platforms (arm64) only."
echo "canary:   * a timeout (CANARY_TIMEOUT, currently ${CANARY_TIMEOUT:-1800}s)"
echo "canary:   * a tool that is not ea_iid"
echo "canary: ---- captured output (last 10 lines) ----"
tail -10 "$OUT" | sed 's/^/canary:   /'
exit 3
