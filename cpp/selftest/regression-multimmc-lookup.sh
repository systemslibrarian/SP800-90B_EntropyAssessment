#!/bin/bash
#
# Regression for F10 / C01: every MultiMMC depth is looked up independently.
#
# SP 800-90B 6.3.9 step 4.b.i (PDF p. 61) runs, for each d from 1 to D, "If
# d < i, find the y value that corresponds to the highest M_d[(s_{i-d}, ...,
# s_{i-1}), y] value" -- with no condition on any other depth. The tool
# consulted depth d only when depth d-1 had found its prefix
# (multi_mmc_test.h, `if((d == 0) || found_x)`), on the argument that a stored
# (d+1)-symbol prefix implies its d-symbol suffix is stored. That holds until a
# depth's dictionary reaches MAX_ENTRIES = 100,000 pairs and fails after it: a
# new pair is then refused at the full depth d-1 while the same round still adds
# the longer pair at depth d, so a prefix can be present at depth d with its
# suffix absent at d-1 (an "orphan"). Every later visit to that context went
# Null at depths >= d where the standard predicts. Fewer correct predictions is
# a smaller C and r, a smaller P_global and P_local, and a LARGER min-entropy:
# the overstating direction. The 2026-11-07 audit's experiment X3 measured it
# at +0.078 bit on a crafted compliant 8-bit file (Literal MultiMMC 0.97830 in
# the tool against 0.90052 in the spec-literal reference), and -0.093 bit on a
# second construction, both with the cap bound; the record is FINDINGS.md of
# that audit, logs/experiments/CHAIN-2.log 'X3', and FORK-DIVERGENCE-AND-TRUST.md
# A.1 (status there before this repair: NOT REPAIRED).
#
# WHY THERE IS NO 20,000-SAMPLE ARM THAT CAN FAIL. Without the cap the two
# readings are provably identical (a stored long pair implies its stored short
# pair), and no depth can hold 100,000 pairs before sample 100,000. So the
# smallest input on which this defect is observable at the shipped constants
# is ~100,000 symbols long. The decisive arm here is 104,000 samples: the X3
# construction (fill of 99,980 symbols over 16..255 with every 3-gram distinct,
# so depths 2..16 fill on consecutive rounds, then a 32-symbol word over 1..8
# repeated), truncated. 104,000 is the shortest sweep point at which the two
# models separate in C and r (at 100,240 only the scoreboards differ, because
# depth 1's head start from the fill keeps it the winner for ~50 more periods).
# The 20,000-sample arms are BASELINE CONTROLS (rule 7): on them the tool must
# agree with the spec-literal model exactly, before and after the repair, so a
# mismatch there is the fixture or the model, not the defect.
#
# EXPECTED VALUES, AND WHERE THEY COME FROM (2026-11-08):
#   * 104,000-sample arms: a spec-literal model of 6.3.9 (the one embedded
#     below, written from the text) and the audit's independent reference
#     reference/py90b/multimmc.py (--k-mode=observed) agree exactly:
#       gadget  sha256 b9c6998c89d42cc07c26d5f1c28e457e457a3cd467387c53b5e2dee575c9c543
#               C = 2409   r = 20   N = 103998   (reference winner: depth 3)
#       naive   sha256 5aecccef8df6303faeff2fe226812274804ea277a73269a440ff24b9364b4267
#               C = 1911   r = 16   N = 103998   (reference winner: depth 2)
#     The chained lookup gives C = 2288, r = 12 (gadget: tool C lower, the
#     overstating direction) and C = 1998, r = 17 (naive: the understating
#     direction), from a transcription of the C++ that reproduced the tool
#     EXACTLY on both 1,000,000-sample X3 files (CHAIN-2.log: "cpp == tool").
#   * 20,000-sample arms: computed live by the embedded model.
#   * The full-size X3 files (heavy arm): the reference's recorded values,
#     gadget C = 534409, r = 20 and naive C = 421911, r = 16 (x3-*-ref.stdout).
#   * The fixtures are regenerated here from a stdlib-only replica of the X3
#     generator (harness/experiments/x3_multimmc_orphans.py + common.keystream:
#     SHA-256 counter mode under a fixed key, no library RNG) and their sha256
#     is asserted against the X3 manifest before any figure is read, so a
#     drifted generator refuses rather than comparing the wrong file.
#
# OBSERVED FAILING. This file was written on 2026-11-08 without a build (the
# host's heavy slot was busy); the pre-repair figures above are the model's,
# and docs/audits/2026-11-07-aggressive-audit/repro/FIX-multimmc-lookup/
# TEST-PLAN.md is the procedure that records the observed failure against
# master's binary. Until that run is recorded in the commit, the decisive arm
# is an untested assertion that it can fail (guide step 5).
#
# RULE 12 DECLARATION. The repair touches ground three earlier changes touched,
# all in the same two loops of multi_mmc_test.h:
#   * F09 (commit 69b6094) -- a Null from the winner ends the run of correct
#     predictions. The repaired lookup changes WHEN the winner is Null (fewer
#     spurious Nulls), not what a Null does. PAIR TEST: r on the 104,000-sample
#     arms must equal the spec-literal model's, which applies both rules at
#     once (r = 20 needs both the orphan positions predicted AND the run broken
#     where the standard breaks it); the worked example's r = 3 is F09's own
#     case and must still hold.
#   * F10 / C01 -- this repair.
#   * #257 (commit ed88de9) -- the binary path declines below D_MMC+1 samples.
#     The binary lookup is made unconditional in the same function for
#     consistency; the decline is untouched. PAIR TEST: 16 one-bit samples
#     must still decline with the warning and no Literal MultiMMC figure, 17
#     must run and match the model, and the 20,000-bit arm must match the
#     model exactly (the binary path is proven unable to reach the mechanism:
#     depth index d holds at most 2^(d+2) pairs and 2^16 < MAX_ENTRIES).
#
# Platform: the expected values are integers from the standard's algorithm,
# so no tolerance applies and nothing here depends on floating point. Run so
# far on Darwin arm64 only; say so when reporting it (guide step 5).
#
# REGRESSION_MULTIMMC_LOOKUP_BINDIR points the checks at another build, so
# they can be shown FAILING against a build without the repair.
# EA_REGRESSION_HEAVY=1 adds the two 1,000,000-sample X3 files (about a
# minute each on this host); without it they are reported NOT RUN, which is a
# visible third outcome and not a pass.

set -u

here=$(cd "$(dirname "$0")" && pwd)
# instrument rule 5, mechanised (OC-73)
. "${here}/labelread-lib.sh"
# instrument rule 4: the artefact measured is declared before any result
. "${here}/buildstate-lib.sh"
bindir="${REGRESSION_MULTIMMC_LOOKUP_BINDIR:-${here}/..}"
tool="${bindir}/ea_non_iid"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regmmclookup.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM

export EA_ALLOW_SHORT_DATASET=1

fails=0
note() { printf '  %-62s %s\n' "$1" "$2"; }
bad()  { note "$1" "$2"; fails=$((fails + 1)); }
expect_eq() { # expect_eq <label> <got> <want>
    if [ -n "$2" ] && [ "$2" = "$3" ]; then note "$1" "$2"; else bad "$1" "got '${2}', expected ${3}"; fi
}

[ -x "${tool}" ] || { echo "regression-multimmc-lookup: ${tool} missing (run 'make non_iid')" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "regression-multimmc-lookup: python3 not on PATH" >&2; exit 2; }
bs_print "${tool}"

# The generator and the spec-literal model, in one stdlib-only program.
cat > "${work}/mmcref.py" <<'PY'
"""Fixtures and a spec-literal MultiMMC model for regression-multimmc-lookup.sh.

The model is SP 800-90B 6.3.9 steps 1-5 and 7 transcribed from the text (PDF
pp. 61-62), 0-based: position pos predicts s[pos], the standard's i = pos + 1.
Nothing here is taken from cpp/.  The fixtures replicate the 2026-11-07 audit's
X3 construction (harness/experiments/x3_multimmc_orphans.py) and its keystream
(common.keystream: SHA-256(KEY_PREFIX || label || counter_be64)), so that the
files' sha256 can be asserted against that audit's manifest.
"""
import hashlib, sys

KEY_PREFIX = b"aa-experiments-2026-11-07/"
D = 16                     # step 1: "Let D = 16"
MAX_ENTRIES = 100_000      # step 1: "let maxEntries = 100 000"
FILL_ALPHABET = list(range(16, 256))
PERIOD_ALPHABET = list(range(1, 9))
VARIANTS = {
    "naive":  dict(P=32, b=17, q=0, kind="distinct2", wlabel="x3/period32"),
    "gadget": dict(P=32, b=17, q=4, kind="distinct3", wlabel="w32-0"),
}


def keystream(label, nbytes):
    key = KEY_PREFIX + label.encode("utf-8")
    out = bytearray()
    i = 0
    while len(out) < nbytes:
        out += hashlib.sha256(key + i.to_bytes(8, "big")).digest()
        i += 1
    return bytes(out[:nbytes])


def fill_all_3grams_distinct(length, label):
    k = len(FILL_ALPHABET)
    ks = keystream(label, length + 8)
    seen = set()
    s = []
    for i in range(length):
        start = ks[i] % k
        if i < 2:
            s.append(FILL_ALPHABET[start])
            continue
        a, b = s[-2], s[-1]
        for off in range(k):
            c = FILL_ALPHABET[(start + off) % k]
            key = (a << 16) | (b << 8) | c
            if key not in seen:
                seen.add(key)
                s.append(c)
                break
        else:
            raise SystemExit("fixture: fill alphabet exhausted")
    return s


def period_word(length, label):
    k = len(PERIOD_ALPHABET)
    ks = keystream(label, 4 * length + 64)
    order = [[PERIOD_ALPHABET[(ks[i] + j) % k] for j in range(k)] for i in range(length + 1)]

    def dfs(w, used):
        if len(w) == length:
            return w if (w[-1], w[0]) not in used else None
        for c in order[len(w)]:
            if not w:
                r = dfs([c], used)
                if r:
                    return r
                continue
            g = (w[-1], c)
            if g in used:
                continue
            used.add(g)
            r = dfs(w + [c], used)
            if r:
                return r
            used.discard(g)
        return None

    w = dfs([], set())
    if w is None:
        raise SystemExit("fixture: no period word")
    return w


def random_word_3gram_distinct(length, label):
    ks = keystream(label, 64 * length + 64)
    k = len(PERIOD_ALPHABET)
    order = [[1 + (ks[i] + j) % k for j in range(k)] for i in range(length + 1)]

    def dfs(w, tri):
        if len(w) == length:
            t1 = (w[-2], w[-1], w[0])
            t2 = (w[-1], w[0], w[1])
            if t1 in tri or t2 in tri or t1 == t2:
                return None
            return w
        for c in order[len(w)]:
            if len(w) < 2:
                r = dfs(w + [c], tri)
                if r:
                    return r
                continue
            t = (w[-2], w[-1], c)
            if t in tri:
                continue
            tri.add(t)
            r = dfs(w + [c], tri)
            if r:
                return r
            tri.discard(t)
        return None

    w = dfs([], set())
    if w is None:
        raise SystemExit("fixture: no 3-gram-distinct word")
    return w


def build_x3(total, variant):
    """The X3 construction, `total` symbols (a prefix of the 1,000,000-sample file)."""
    v = VARIANTS[variant]
    p, b, q = v["P"], v["b"], v["q"]
    lf = MAX_ENTRIES + 1 - b - q
    fill = fill_all_3grams_distinct(lf, f"x3/fill-cap{MAX_ENTRIES}")
    w = period_word(p, v["wlabel"]) if v["kind"] == "distinct2" else random_word_3gram_distinct(p, v["wlabel"])
    pre = w[p - q:] if q else []
    full = max(total, lf + q + p)
    tail_len = full - lf - q
    tail = (w * (tail_len // p + 2))[:tail_len]
    return bytes(fill + pre + tail)[:total]


def mmc_text(s, bps_note=None):
    """Steps 1-5 and 7 of 6.3.9 as written.  Returns (C, r, N)."""
    L = len(s)
    N = L - 2                                     # step 1
    M = [None] + [dict() for _ in range(D)]       # step 2: M_d[x] -> {y: count}
    entries = [0] * (D + 1)                       # step 1
    scoreboard = [0] * (D + 1)                    # step 3
    winner = 1                                    # step 3
    C = 0
    run = best = 0
    for pos in range(2, L):                       # step 4: i = 3..L
        # 4.a: for d < i-1, the pair [(s_{i-d-1},...,s_{i-2}), s_{i-1}]
        y = s[pos - 1]
        for d in range(1, D + 1):
            if d >= pos:
                break
            ctx = s[pos - 1 - d:pos - 1]
            md = M[d]
            cnt = md.get(ctx)
            if cnt is not None and y in cnt:
                cnt[y] += 1                       # 4.a.i.1
            elif entries[d] < MAX_ENTRIES:        # 4.a.i.2
                if cnt is None:
                    md[ctx] = {y: 1}
                else:
                    cnt[y] = 1
                entries[d] += 1
        # 4.b: for d < i, every depth on its own; highest count, greatest y on a tie
        si = s[pos]
        sub = [None] * (D + 1)
        for d in range(1, D + 1):
            if d > pos:
                break
            cnt = M[d].get(s[pos - d:pos])
            if cnt:
                bc, by = -1, -1
                for yy, c in cnt.items():
                    if c > bc or (c == bc and yy > by):
                        bc, by = c, yy
                sub[d] = by
        # 4.c / 4.d: correct_{i-2} = 1 iff subpredict_winner = s_i (Null never equals a symbol)
        if sub[winner] == si:
            C += 1
            run += 1
            if run > best:
                best = run
        else:
            run = 0
        # 4.e: the scoreboard, d ascending, winner read as it stands
        for d in range(1, D + 1):
            if sub[d] == si:
                scoreboard[d] += 1
                if scoreboard[d] >= scoreboard[winner]:
                    winner = d
    return C, best + 1, N                         # step 5; step 7: r = 1 + longest run


def to_bits(s, bps):
    out = bytearray()
    for v in s:
        for sh in range(bps - 1, -1, -1):
            out.append((v >> sh) & 1)
    return bytes(out)


def main(argv):
    cmd = argv[1]
    if cmd == "x3":                       # x3 <variant> <total> <out>  -> prints sha256
        data = build_x3(int(argv[3]), argv[2])
    elif cmd == "bits":                   # bits <n> <out>  (prefixes of one stream)
        data = bytes(v & 1 for v in keystream("regression-multimmc-lookup/1bit-20000", 20000))[:int(argv[2])]
    elif cmd == "worked":                 # the standard's worked example, PDF p. 62
        data = bytes([2, 1, 3, 2, 1, 3, 1, 3, 1])
    elif cmd == "model":                  # model <file> <bps> [bitstring]
        with open(argv[2], "rb") as f:
            s = f.read()
        bps = int(argv[3])
        if len(argv) > 4 and argv[4] == "bitstring":
            s = to_bits(s, bps)
        C, r, N = mmc_text(s)
        print(f"C = {C}\nr = {r}\nN = {N}")
        return 0
    else:
        raise SystemExit(f"mmcref: unknown command {cmd!r}")
    with open(argv[-1], "wb") as f:
        f.write(data)
    print(hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
PY

# run_tool <tag> <file> <bps> -- outputs to files (rule 17); true iff exit 0
run_tool() {
    "${tool}" -vv "$2" "$3" > "${work}/$1.stdout" 2> "${work}/$1.stderr"
    rc=$?
    printf '%s\n' "${rc}" > "${work}/$1.rc"
    [ "${rc}" -eq 0 ]
}
# field <tag> <Literal|Bitstring> <C|r|N> -- a labelled read of one figure
field() {
    sed -n "s/^$2 MultiMMC Prediction Estimate: $3 = //p" "${work}/$1.stdout" | lr_one "$2 MultiMMC $3 ($1)"
}
# model_field <model-output> <C|r|N>
model_field() {
    printf '%s\n' "$1" | sed -n "s/^$2 = //p" | lr_one "model $2"
}
# gen <sha256-or-'-'> <mmcref args...> -- write a fixture; refuse a wrong digest
gen() {
    local want=$1; shift
    local got
    got=$(python3 "${work}/mmcref.py" "$@") || { echo "regression-multimmc-lookup: fixture generator failed ($*)" >&2; exit 2; }
    if [ "${want}" != "-" ] && [ "${got}" != "${want}" ]; then
        echo "regression-multimmc-lookup: FIXTURE DIGEST MISMATCH for '$*':" >&2
        echo "    got      ${got}" >&2
        echo "    expected ${want}  (the X3 manifest / this file's header)" >&2
        echo "  The expected figures below were derived on the expected bytes, so nothing" >&2
        echo "  can be concluded from a different file. Refusing to run the arm." >&2
        exit 2
    fi
}

# ------------------------------------------------------------ A. worked example
# The standard's own example (PDF pp. 62-63): correct = (0,0,1,1,0,1,0),
# so C = 3, the longest run is 2 and r = 3, N = 7. Both readings give this; it
# is the baseline that the estimator still implements the section at all.
gen - worked "${work}/worked.bin"
if run_tool worked "${work}/worked.bin" 2; then
    expect_eq "6.3.9 worked example C (spec: 3):" "$(field worked Literal C)" 3
    expect_eq "6.3.9 worked example r (spec: 3; F09's case):" "$(field worked Literal r)" 3
    expect_eq "6.3.9 worked example N (spec: 7):" "$(field worked Literal N)" 7
else
    bad "6.3.9 worked example: tool exit status" "$(cat "${work}/worked.rc")"
fi

# ------------------------------------------------------ B. 20,000-sample baseline
# The X3 fill phase alone: no depth can be full, so chained and independent
# lookup are identical and the tool must equal the model exactly, Literal and
# Bitstring. The digest is the X3 manifest's x3-mmc-orphan-fill-8bit-prefix20000.bin.
gen 5948b4706fc8961d0598eea1812a9ab3b83e38e8cd43ef9df2a8e2eff54f4489 x3 gadget 20000 "${work}/p20k.bin"
if run_tool p20k "${work}/p20k.bin" 8; then
    m=$(python3 "${work}/mmcref.py" model "${work}/p20k.bin" 8) || m=""
    for k in C r N; do
        expect_eq "BASELINE 20,000 x 8-bit, Literal ${k} == spec model:" "$(field p20k Literal "${k}")" "$(model_field "${m}" "${k}")"
    done
    m=$(python3 "${work}/mmcref.py" model "${work}/p20k.bin" 8 bitstring) || m=""
    for k in C r N; do
        expect_eq "BASELINE 20,000 x 8-bit, Bitstring ${k} == spec model:" "$(field p20k Bitstring "${k}")" "$(model_field "${m}" "${k}")"
    done
else
    bad "BASELINE 20,000 x 8-bit: tool exit status" "$(cat "${work}/p20k.rc")"
fi

# --------------------------------------------- C. the binary path and the #257 pair
gen - bits 20000 "${work}/b20k.bin"
if run_tool b20k "${work}/b20k.bin" 1; then
    m=$(python3 "${work}/mmcref.py" model "${work}/b20k.bin" 1) || m=""
    for k in C r N; do
        expect_eq "PAIR #257: binary path, 20,000 bits, ${k} == spec model:" "$(field b20k Literal "${k}")" "$(model_field "${m}" "${k}")"
    done
else
    bad "PAIR #257: binary path, 20,000 bits: tool exit status" "$(cat "${work}/b20k.rc")"
fi
# 16 samples: the decline must still be there (instrument rule 2: the positive
# marker is the warning line itself, on a run that exited 0).
gen - bits 16 "${work}/b16.bin"
if run_tool b16 "${work}/b16.bin" 1; then
    warn=$(grep -c 'not enough samples to run multiMMC test' "${work}/b16.stdout")
    lit=$(grep -c '^Literal MultiMMC Prediction Estimate: C = ' "${work}/b16.stdout")
    if [ "${warn}" -ge 1 ] && [ "${lit}" -eq 0 ]; then
        note "PAIR #257: 16 bits still decline (warning present, no figure):" "yes"
    else
        bad "PAIR #257: 16 bits still decline:" "warning lines ${warn}, Literal C lines ${lit}"
    fi
else
    bad "PAIR #257: 16 bits: tool exit status" "$(cat "${work}/b16.rc")"
fi
gen - bits 17 "${work}/b17.bin"
if run_tool b17 "${work}/b17.bin" 1; then
    m=$(python3 "${work}/mmcref.py" model "${work}/b17.bin" 1) || m=""
    for k in C r N; do
        expect_eq "PAIR #257: 17 bits run, ${k} == spec model:" "$(field b17 Literal "${k}")" "$(model_field "${m}" "${k}")"
    done
else
    bad "PAIR #257: 17 bits: tool exit status" "$(cat "${work}/b17.rc")"
fi

# ---------------------------------------- D. the defect: 104,000 samples, cap bound
# Expected values from the spec-literal model and py90b (header). A chained
# lookup prints C = 2288, r = 12 on the gadget file and C = 1998, r = 17 on the
# naive one.
gen b9c6998c89d42cc07c26d5f1c28e457e457a3cd467387c53b5e2dee575c9c543 x3 gadget 104000 "${work}/g104k.bin"
if run_tool g104k "${work}/g104k.bin" 8; then
    expect_eq "F10 gadget 104,000 x 8-bit: Literal C (chained: 2288):" "$(field g104k Literal C)" 2409
    expect_eq "F10 x F09 gadget 104,000 x 8-bit: Literal r (chained: 12):" "$(field g104k Literal r)" 20
    expect_eq "F10 gadget 104,000 x 8-bit: Literal N:" "$(field g104k Literal N)" 103998
else
    bad "F10 gadget 104,000 x 8-bit: tool exit status" "$(cat "${work}/g104k.rc")"
fi
gen 5aecccef8df6303faeff2fe226812274804ea277a73269a440ff24b9364b4267 x3 naive 104000 "${work}/n104k.bin"
if run_tool n104k "${work}/n104k.bin" 8; then
    expect_eq "F10 naive 104,000 x 8-bit: Literal C (chained: 1998):" "$(field n104k Literal C)" 1911
    expect_eq "F10 x F09 naive 104,000 x 8-bit: Literal r (chained: 17):" "$(field n104k Literal r)" 16
    expect_eq "F10 naive 104,000 x 8-bit: Literal N:" "$(field n104k Literal N)" 103998
else
    bad "F10 naive 104,000 x 8-bit: tool exit status" "$(cat "${work}/n104k.rc")"
fi

# ------------------------------------ E. the X3 files at compliant size (heavy)
if [ "${EA_REGRESSION_HEAVY:-0}" = "1" ]; then
    gen 095aeaf1e294a65c0fdbb2a1fff57a5e9ed0b7c5dc0a203a386f23de5f3c7116 x3 gadget 1000000 "${work}/g1m.bin"
    if run_tool g1m "${work}/g1m.bin" 8; then
        expect_eq "X3 gadget 1,000,000 x 8-bit: Literal C (reference; tool printed 506288):" "$(field g1m Literal C)" 534409
        expect_eq "X3 gadget 1,000,000 x 8-bit: Literal r (reference; tool printed 12):" "$(field g1m Literal r)" 20
    else
        bad "X3 gadget 1,000,000 x 8-bit: tool exit status" "$(cat "${work}/g1m.rc")"
    fi
    gen cf6e4f28c0c592dce6d53275452428cd350e61d5c55bd6923e7a9b18033652f7 x3 naive 1000000 "${work}/n1m.bin"
    if run_tool n1m "${work}/n1m.bin" 8; then
        expect_eq "X3 naive 1,000,000 x 8-bit: Literal C (reference; tool printed 449998):" "$(field n1m Literal C)" 421911
        expect_eq "X3 naive 1,000,000 x 8-bit: Literal r (reference; tool printed 17):" "$(field n1m Literal r)" 16
    else
        bad "X3 naive 1,000,000 x 8-bit: tool exit status" "$(cat "${work}/n1m.rc")"
    fi
else
    note "X3 files at 1,000,000 samples:" "NOT RUN (set EA_REGRESSION_HEAVY=1; a heavy job)"
fi

echo
if [ "${fails}" -eq 0 ]; then
    echo "regression-multimmc-lookup: PASS"
    exit 0
fi
echo "regression-multimmc-lookup: FAIL (${fails} checks)"
exit 1
