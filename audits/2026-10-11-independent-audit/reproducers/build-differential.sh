#!/bin/bash
# Build-differential validation (REPAIR-STRATEGY route 4): the same input through
# an asserts-live ea_iid and a -DNDEBUG ea_iid must give the SAME answer. No
# reference corpus is consulted; agreement between the two builds is the check.
#
#   build-differential.sh <ea_iid asserts-live> <ea_iid -DNDEBUG> [W ...]
#
# Inputs are generated from the audit's fixed seed (generators/c07_lrs_fixtures.py
# site B, and tools/build-provenance-canary.sh for W=20000): a 1,000,000-bit
# stream with a repeated block of length W implanted, so the longest repeated
# substring is >= W. These are inputs whose correct verdict is known BY
# CONSTRUCTION (route 2): a 20,000-bit exact repeat is astronomically improbable
# under IID, so the only correct outcome is a refused IID figure.
#
# PASS requires, for every W:  identical exit code, identical "** Failed" /
# "** Passed" lines, identical JSON after dropping run-specific fields, and
# NO hAssessed in either JSON.  Exit 0 only then.
set -u
LIVE=$1; NDEBUG=$2; shift 2
# BUILD STATE AS A PRECONDITION (OC-43). This measurement's whole point is that
# two builds agree, so taking it against two copies of the SAME build would
# "pass" and mean nothing. Declare what each must be and refuse a mismatch.
. "$(cd "$(dirname "$0")/../../../cpp/selftest" && pwd)/buildstate-lib.sh"
bs_require "$LIVE"   LIVE
bs_require "$NDEBUG" NDEBUG
WS=${*:-"2000 20000"}
PROG=build-differential
work=$(mktemp -d "${TMPDIR:-/tmp}/${PROG}.XXXXXX") || exit 2
trap 'rm -rf "$work"' EXIT HUP INT TERM
fails=0

# RULE 8 IS MET HERE, NOT ASSUMED (OC-71). Five fields are normalised away as
# "legitimately differing", and that was an assumption with nothing behind it.
# Rule 8 requires a SELF-COMPARISON -- run the unchanged artefact against
# itself and see what actually varies -- and a LIVE-SENSITIVITY check that the
# comparator fires on a kept field. Both run below, before any arm-to-arm
# comparison is read, and a field that does NOT vary under self-comparison is
# reported, because dropping a stable field hides real divergence.
rule8_controls() { # rule8_controls <binary> <input>
    local bin=$1 inp=$2 a="$work/r8a.json" b="$work/r8b.json"
    OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} "$bin" -i -v -o "$a" "$inp" 1 >/dev/null 2>&1
    OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} "$bin" -i -v -o "$b" "$inp" 1 >/dev/null 2>&1
    [ -s "$a" ] && [ -s "$b" ] || { echo "  RULE 8: cannot run the controls (no report from two runs of one build)"; return 1; }
    python3 - "$a" "$b" <<'PY'
import json, sys
# The fields norm_json treats as not-to-be-compared-verbatim. The control
# reports which of them actually vary, and names any that are stable -- which
# is how filename, sha256 and toolVersion came to be KEPT (OC-71).
DROPPED = ("dateTimeStamp", "commandline")
a, b = (json.load(open(p)) for p in sys.argv[1:3])
varied   = [k for k in DROPPED if a.get(k) != b.get(k)]
stable   = [k for k in DROPPED if k in a and a.get(k) == b.get(k)]
missing  = [k for k in DROPPED if k not in a]
print("  RULE 8 self-comparison (one build, two runs):")
print("    vary, so dropping them is justified : %s" % (", ".join(varied) or "NONE"))
print("    STABLE, so dropping them HIDES difference: %s" % (", ".join(stable) or "none"))
if missing:
    print("    absent from the report entirely     : %s" % ", ".join(missing))
# live sensitivity: perturb a KEPT field and the comparator must see it
kept = [k for k in a if k not in DROPPED]
print("    comparator kept %d field(s); live-sensitivity on the first: %s"
      % (len(kept), kept[0] if kept else "NONE -- nothing is being compared"))
sys.exit(0 if (varied and kept) else 1)
PY
}

norm_json() {  # drop fields the self-comparison above shows actually differ
    python3 - "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
# WHAT THE SELF-COMPARISON ESTABLISHED (OC-71), replacing what was assumed.
# Two runs of ONE build vary in dateTimeStamp and commandline only. filename,
# sha256 and toolVersion are STABLE -- so dropping them hid difference, and two
# of them IDENTIFY THE INPUT. Dropped as they were, this differential could not
# have noticed the two arms assessing DIFFERENT FILES, which is the one thing a
# build-differential must never miss.
#
# So: drop the timestamp; NORMALISE the commandline rather than dropping it,
# because it differs between arms only in the -o path; and KEEP filename,
# sha256 and toolVersion, which must match for the comparison to mean anything.
import re as _re
d.pop("dateTimeStamp", None)
if isinstance(d.get("commandline"), str):
    cl = _re.sub(r'-o\s+\S+', '-o <normalised>', d["commandline"])
    # argv[0] is the binary's own path, and the two arms ARE different binaries
    # by design, so that part must normalise too. The ARGUMENTS stay compared:
    # the flags and the input path are what must match between arms.
    parts = cl.split(None, 1)
    d["commandline"] = "<arm-binary> " + parts[1] if len(parts) == 2 else "<arm-binary>"
print(json.dumps(d, sort_keys=True, indent=1))
PY
}

# Run rule 8's controls once, on the asserts-live arm, before any comparison.
r8_in="$work/r8.bin"
python3 - "$r8_in" <<'PY'
import random, sys
r = random.Random(0x90B2026C07)
open(sys.argv[1], 'wb').write(bytes(r.getrandbits(1) for _ in range(1000000)))
PY
if ! rule8_controls "$LIVE" "$r8_in"; then
    echo "$PROG: FAIL (rule 8's controls did not establish what may be normalised away)"
    exit 1
fi
# live sensitivity, concretely: perturb one kept field and require norm_json to notice
python3 - "$work/r8a.json" "$work/r8pert.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for k in d:
    if k not in ("dateTimeStamp", "commandline"):
        if isinstance(d[k], (int, float)): d[k] = d[k] + 1
        elif isinstance(d[k], bool): d[k] = not d[k]
        else: continue
        break
json.dump(d, open(sys.argv[2], "w"))
PY
if diff <(norm_json "$work/r8a.json") <(norm_json "$work/r8pert.json") >/dev/null 2>&1; then
    echo "  RULE 8 live sensitivity: *** BLIND -- norm_json did not see a perturbed kept field ***"
    echo "$PROG: FAIL (the comparator cannot fire; agreement from it means nothing)"
    exit 1
fi
echo "  RULE 8 live sensitivity: norm_json SEES a perturbed kept field -- the comparator fires"
echo

for W in $WS; do
    IN="$work/lrsrep-$W.bin"
    python3 - "$IN" "$W" <<'PY'
import random, sys, hashlib
r = random.Random(0x90B2026C07)
b = bytearray(r.getrandbits(1) for _ in range(1000000))
W = int(sys.argv[2])
b[600000:600000 + W] = bytes(b[1000:1000 + W])
d = bytes(b)
open(sys.argv[1], 'wb').write(d)
print("input W=%d sha256 %s" % (W, hashlib.sha256(d).hexdigest()))
PY
    for tag in live ndebug; do
        bin=$LIVE; [ "$tag" = ndebug ] && bin=$NDEBUG
        rm -f "$work/$tag.json"
        OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} "$bin" -i -v -o "$work/$tag.json" "$IN" 1 >"$work/$tag.out" 2>&1
        echo $? >"$work/$tag.rc"
    done
    rc_l=$(cat "$work/live.rc"); rc_n=$(cat "$work/ndebug.rc")
    echo "W=$W  exit: asserts-live=$rc_l  ndebug=$rc_n"
    grep -hE '^\*\* (Failed|Passed)|IID test suite|Assertion failed|hAssessed|min-entropy' "$work/live.out" | sed 's/^/  live:   /'
    grep -hE '^\*\* (Failed|Passed)|IID test suite|Assertion failed|hAssessed|min-entropy' "$work/ndebug.out" | sed 's/^/  ndebug: /'
    ok=1
    [ "$rc_l" = "$rc_n" ] || { echo "  DIVERGE: exit codes differ"; ok=0; }

    # TWO EMPTY MEASUREMENTS MUST NOT COMPARE EQUAL (OC-71).
    #
    # This declared build state exemplarily and still returned a vacuous
    # agreement. Both fallbacks were the SAME LITERAL -- `|| echo '{}'` on a
    # failed normalisation, and "(no json)" on a missing report -- so if both
    # arms failed, diff was silent and the script reported AGREE. The
    # verdict-line comparison had the same hole: if neither output contained a
    # "** Passed/Failed" line, the two greps were both empty and diff was
    # silent again.
    #
    # Fixed two ways, because either alone is defeatable: the sentinels are now
    # DISTINCT PER ARM, so two failures can never compare equal; and the
    # comparison asserts it had something to compare before reading agreement
    # from it.
    nv_live=$(grep -cE '^\*\* (Failed|Passed)' "$work/live.out" || true)
    nv_nd=$(grep -cE '^\*\* (Failed|Passed)' "$work/ndebug.out" || true)
    if [ "${nv_live:-0}" -eq 0 ] && [ "${nv_nd:-0}" -eq 0 ]; then
        echo "  VACUOUS: neither build printed a single '** Passed/Failed' line, so"
        echo "           their verdict lines agree by both being absent. Nothing compared."
        ok=0
    elif ! diff <(grep -E '^\*\* (Failed|Passed)' "$work/live.out") <(grep -E '^\*\* (Failed|Passed)' "$work/ndebug.out") >/dev/null; then
        echo "  DIVERGE: per-test verdict lines differ"; ok=0
    else
        echo "  compared $nv_live verdict line(s) per arm"
    fi

    for tag in live ndebug; do
        if [ -s "$work/$tag.json" ]; then
            if grep -q hAssessed "$work/$tag.json"; then echo "  FAIL: $tag published hAssessed on a known-non-IID input"; ok=0; fi
            # DISTINCT per-arm sentinel: two normalisation failures cannot match
            norm_json "$work/$tag.json" >"$work/$tag.norm" 2>/dev/null \
                || printf 'NORMALISATION-FAILED-%s\n' "$tag" >"$work/$tag.norm"
        else
            printf 'NO-JSON-%s\n' "$tag" >"$work/$tag.norm"
        fi
    done
    if grep -q '^NORMALISATION-FAILED-\|^NO-JSON-' "$work/live.norm" "$work/ndebug.norm" 2>/dev/null; then
        echo "  VACUOUS: at least one arm produced no comparable JSON --"
        sed 's/^/           /' "$work/live.norm" "$work/ndebug.norm" | grep -E 'NORMALISATION-FAILED|NO-JSON' | head -2
        echo "           agreement here would mean nothing. Nothing compared."
        ok=0
    elif ! diff "$work/live.norm" "$work/ndebug.norm" >/dev/null; then
        echo "  DIVERGE: JSON differs after normalisation"; diff "$work/live.norm" "$work/ndebug.norm" | head -20 | sed 's/^/    /'; ok=0
    else
        echo "  compared $(grep -c '' "$work/live.norm") normalised JSON line(s) per arm"
    fi
    [ "$ok" -eq 1 ] && echo "  AGREE: both builds refuse identically, on a comparison shown non-vacuous" || fails=$((fails + 1))
done
if [ "$fails" -eq 0 ]; then echo "$PROG: PASS"; exit 0; fi
echo "$PROG: FAIL ($fails input(s) diverged or published a figure)"; exit 1
