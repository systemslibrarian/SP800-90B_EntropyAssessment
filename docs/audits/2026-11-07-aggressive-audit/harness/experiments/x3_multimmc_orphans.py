#!/usr/bin/env python3
"""x3_multimmc_orphans.py -- X3: the MultiMMC chained-lookup divergence (tracker F10 / divergence
C01) driven to its maximum with a scoreboard-aware periodic construction, plus two predictor
MODELS (the standard's text, and the C++'s chained lookup) used to validate the construction
at a scaled-down dictionary cap against the independent reference reference/py90b/multimmc.py.

Mechanism (multimmc.md 2.2-2.5, re-derived here).  cpp/non_iid/multi_mmc_test.h:236 looks up
depth d only if depth d-1's prefix was found (`if((d == 0) || found_x)`), whereas SP 800-90B
6.3.9 step 4.b looks every depth up independently.  Without the 100,000-entry cap the chain is
harmless (a stored deep pair implies its shallow suffix pair is stored).  With the cap, a pair
can be stored at depth e while its suffix pair was refused at a FULL shallower depth f -- an
"orphan".  Whenever that context recurs the C++ breaks the chain at f (prefix absent) and treats
depths f+1..16 as Null where the text predicts.  Direction: fewer correct predictions ->
smaller C and r -> LARGER min-entropy = the tool overstates the Literal MultiMMC figure.

Construction (8-bit symbols):
  fill    Lf = 100,001 - b symbols over {16..255} with ALL 3-grams distinct (greedy, keystream-
          driven, deterministic).  Then every (d+1)-gram, d >= 2, is new at every step, so the
          depth-d pair count is entries_2 - (d-2): depths 2..16 fill at CONSECUTIVE steps.  Depth 1
          (240^2 = 57,600 possible pairs, +64 later) never fills.
  tail    a word W of length P = 32 over {1..8} (alphabet disjoint from the fill) with all 32
          cyclic 2-grams distinct, repeated to 1,000,000 symbols.  Depth 2 fills at W offset
          b = 17 of period 1 (entries_2 = Lf - 2 + t + 1 reaches 100,000 at t = 100,001 - Lf);
          depth d fills at offset b + d - 2, depth 16 at b + 14 = 31 = the last offset.
          Offsets b+1 .. b+14 are the ORPHANS: at offset b+j the pair is stored at depths
          j+2..16 and refused at depths 2..j+1, and its 2-gram prefix is absent from M_2 for
          ever (M_2 is full and the 2-gram occurs nowhere else in W).
  period >= 2, what the MODELS show (validated against py90b at a scaled cap; the derivation
  in the analysis phase, "+14 per period", does NOT survive the scoreboard dynamics):
      every depth d >= 2 stores exactly b-1 in-period pairs (the pairs ending at offsets
      d .. b+d-2), so every depth's per-period credit is the same b-1 in the text: the d-2
      orphan positions a deep depth gains are exactly the d-2 start positions (offsets 2..d-1)
      it cannot predict.  The text's winner therefore rotates: at orphan offset b+j the winner
      at the start of the step is depth j+1, whose stored pairs end at b+j-1 -> Null.  Text
      C = offsets 3..b = b-2 per period.  The C++ (no orphan credit at all; depth 2 strictly
      leads) has winner 2 and C = offsets 2..b = b-1 per period: ONE MORE than the text.
      Direction on the naive word: the tool is LOWER (conservative) by ~1/P in P_global.
  variant G ("gadget"): W has repeated 2-grams with different successors (free: the pairs are
      new, so the fill order is unchanged); depth 2 is wrong at the losing successor each
      period, the C++ winner becomes depth 3, and the C++ then loses the orphan at offset b+1
      that the text's depth 3 collects: text C exceeds C++ C by ONE per period (the search over
      P, b, pre-roll q and words found no variant above +1; see x3-search.out).  Direction: the
      tool is HIGHER by ~1/P in P_global -- the overstating direction, ~0.08 bit at P = 32.
  Bound (derived, checked by the search): orphans exist only while shallow depths are full and
  deep ones are not, a window of <= 14 steps that requires EVERY pair new until depth 2 fills;
  any repeated pair at a depth < g erodes the window, so no construction can both widen the
  deep depths' lead and keep the orphans.  The headline does NOT move either way: t-Tuple,
  LRS and Lag (period <= 128) report ~0 on the periodic tail (PLAN.md X3 says what moves).

Validation NOW (light): the identical construction scaled to max_entries = 3,000 and 20,000
symbols; the text model here must match py90b.multimmc.estimate(..., max_entries=3000) exactly
on C, r, scoreboard and winner; the C++ model is then applied to the same input.  The C++ model
is itself checked against the PRODUCTION binary on a 20,000-symbol prefix (no saturation at the
real cap, so the two models and the tool must all agree there).

Usage:
  x3_multimmc_orphans.py                 write the full-size file, its 20,000 prefix, the scaled
                                         file, and run the scaled validation (writes x3-validation.json)
  x3_multimmc_orphans.py --check         re-hash the files against the manifest
  x3_multimmc_orphans.py --model FILE [--max-entries M] [--n N]
                                         run both models on a file (first N symbols) and print C, r
                                         (execution phase: the full file at M = 100000 is a heavy job)
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

EXPERIMENT = "X3"
N = common.N_COMPLIANT
D = 16
MAX_ENTRIES = 100_000
B = 17                      # W offset at which depth 2 fills (period 1)
P = 32                      # period length = B + 15
# variants: (P, b, q = pre-roll length, word kind, word label).  'distinct2' = all cyclic 2-grams
# distinct (no ambiguity); 'distinct3' = all cyclic 3-grams distinct, 2-gram repeats allowed.
VARIANTS = {
    "naive": dict(P=32, b=17, q=0, kind="distinct2", wlabel="x3/period32",
                  expect="cpp C = text C + 1 per period (tool LOWER, conservative)"),
    "gadget": dict(P=32, b=17, q=4, kind="distinct3", wlabel="w32-0",
                   expect="text C = cpp C + 1 per period (tool HIGHER, overstating)"),
}
PREFIX = 20_000
SCALED_CAP = 3_000
SCALED_N = 20_000
FILL_ALPHABET = list(range(16, 256))      # 240 symbols
PERIOD_ALPHABET = list(range(1, 9))       # 8 symbols, disjoint


# ----------------------------------------------------------------------------------------
# construction
# ----------------------------------------------------------------------------------------
def fill_all_3grams_distinct(length: int, label: str) -> list[int]:
    """Greedy sequence over FILL_ALPHABET in which every 3-gram occurs at most once; the next
    symbol is the first candidate (keystream-chosen start, then cyclic scan) whose 3-gram is new."""
    k = len(FILL_ALPHABET)
    ks = common.keystream(label, length + 8)
    seen = set()
    s: list[int] = []
    for i in range(length):
        start = int(ks[i]) % k
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
            raise RuntimeError("no fresh 3-gram available (alphabet exhausted)")
    return s


def period_word(length: int, label: str) -> list[int]:
    """A word over PERIOD_ALPHABET whose `length` CYCLIC 2-grams are all distinct (depth-first
    search on the de Bruijn graph B(8,2), keystream-ordered candidates; deterministic)."""
    k = len(PERIOD_ALPHABET)
    if length > k * k:
        raise ValueError("at most 64 distinct 2-grams over 8 symbols")
    ks = common.keystream(label, 4 * length + 64)
    order = [[PERIOD_ALPHABET[(int(ks[i]) + j) % k] for j in range(k)] for i in range(length + 1)]

    def dfs(w: list[int], used: set) -> list[int] | None:
        if len(w) == length:
            wrap = (w[-1], w[0])
            return w if wrap not in used else None
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
        raise RuntimeError("no period word found")
    return w


def random_word_3gram_distinct(length: int, label: str) -> list[int]:
    """A word over PERIOD_ALPHABET whose `length` CYCLIC 3-grams are all distinct; 2-grams MAY
    repeat (each repeated 2-gram context with two successors is a free depth-2 ambiguity).
    Depth-first search, keystream-ordered candidates; deterministic (same as the search script)."""
    ks = common.keystream(label, 64 * length + 64)
    k = len(PERIOD_ALPHABET)
    order = [[1 + (int(ks[i]) + j) % k for j in range(k)] for i in range(length + 1)]

    def dfs(w: list[int], tri: set) -> list[int] | None:
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
        raise RuntimeError("no 3-gram-distinct word found")
    return w


def build(total: int, max_entries: int, variant: str = "naive", label: str = "x3") -> tuple[list[int], dict]:
    v = VARIANTS[variant]
    p, b, q = v["P"], v["b"], v["q"]
    lf = max_entries + 1 - b - q               # so that depth 2 still fills at W offset b of period 1
    fill = fill_all_3grams_distinct(lf, f"{label}/fill-cap{max_entries}")
    w = period_word(p, v["wlabel"]) if v["kind"] == "distinct2" else random_word_3gram_distinct(p, v["wlabel"])
    pre = w[p - q:] if q else []
    tail_len = total - lf - q
    tail = (w * (tail_len // p + 2))[:tail_len]
    s = fill + pre + tail
    assert len(s) == total
    d2 = len(set((w[i], w[(i + 1) % p]) for i in range(p)))
    info = {"variant": variant, "fill_length": lf, "pre_roll": q, "period": p, "b_offset": b, "period_word": w,
            "distinct_cyclic_2grams": d2, "repeated_2grams": p - d2,
            "orphan_offsets": list(range(b + 1, b + 15)), "max_entries": max_entries,
            "fill_alphabet": [16, 255], "period_alphabet": [1, 8], "total": total,
            "period1_start": lf + q, "periods_in_tail": tail_len / p, "expect": v["expect"]}
    return s, info


# ----------------------------------------------------------------------------------------
# model 1: SP 800-90B 6.3.9 as written (0-based position p predicts s[p]; spec i = p + 1)
# ----------------------------------------------------------------------------------------
def mmc_text(S: list[int], D: int = D, max_entries: int = MAX_ENTRIES, upto: int | None = None) -> dict:
    L = len(S) if upto is None else min(upto, len(S))
    Nn = L - 2
    M = [dict() for _ in range(D + 1)]            # M[d][ctx] -> {y: count}
    entries = [0] * (D + 1)
    scoreboard = [0] * (D + 1)
    winner = 1
    correct = bytearray(max(Nn, 0))
    fill_step = [None] * (D + 1)
    T = tuple(S[:L])
    for pos in range(2, L):                        # spec i = pos + 1, from 3 to L
        # step 4.a: for d = 1..D with d < i-1 = pos: pair ((s_{i-d-1..i-2}), s_{i-1}) = (T[pos-1-d:pos-1], T[pos-1])
        for d in range(1, D + 1):
            if d >= pos:
                break
            ctx = T[pos - 1 - d:pos - 1]
            y = T[pos - 1]
            md = M[d]
            cnt = md.get(ctx)
            if cnt is not None and y in cnt:
                cnt[y] += 1
            elif entries[d] < max_entries:
                if cnt is None:
                    md[ctx] = {y: 1}
                else:
                    cnt[y] = 1
                entries[d] += 1
                if entries[d] == max_entries:
                    fill_step[d] = pos
        # step 4.b: for d = 1..D with d < i = pos+1: context T[pos-d:pos]
        sub = [None] * (D + 1)
        for d in range(1, D + 1):
            if d > pos:
                break
            cnt = M[d].get(T[pos - d:pos])
            if cnt:
                best = None
                for y, c in cnt.items():           # highest count; tie -> greatest y
                    if best is None or c > best[0] or (c == best[0] and y > best[1]):
                        best = (c, y)
                sub[d] = best[1]
        # 4.c, 4.d
        si = T[pos]
        if sub[winner] == si:
            correct[pos - 2] = 1
        # 4.e
        for d in range(1, D + 1):
            if sub[d] == si:
                scoreboard[d] += 1
                if scoreboard[d] >= scoreboard[winner]:
                    winner = d
    C = sum(correct)
    run = best_run = 0
    for v in correct:
        run = run + 1 if v else 0
        if run > best_run:
            best_run = run
    return {"C": C, "r": best_run + 1, "N": Nn, "scoreboard": scoreboard[1:], "winner": winner,
            "entries": entries[1:], "fill_step": fill_step[1:], "correct": bytes(correct)}


# ----------------------------------------------------------------------------------------
# model 2: cpp/non_iid/multi_mmc_test.h:176-290 (generic path), transcribed
# ----------------------------------------------------------------------------------------
class _Postfix:
    __slots__ = ("post", "best", "pred")

    def __init__(self):
        self.post = {}
        self.best = 0
        self.pred = 0

    def increment(self, y: int, make_new: bool) -> bool:       # PostfixDictionary::incrementPostfix
        c = self.post.get(y)
        new = False
        if c is not None:
            c += 1
            self.post[y] = c
        elif make_new:
            new = True
            c = self.post[y] = 1
        else:
            return False
        if c > self.best or (c == self.best and y > self.pred):
            self.pred = y
            self.best = c
        return new


def mmc_cpp(S: list[int], D: int = D, max_entries: int = MAX_ENTRIES, upto: int | None = None) -> dict:
    L = len(S) if upto is None else min(upto, len(S))
    Nn = L - 2
    M = [dict() for _ in range(D)]                 # M[d] : prefix tuple of d+1 symbols -> _Postfix
    entries = [0] * D
    scoreboard = [0] * D
    winner = 0
    C = 0
    run_len = max_run = 0
    T = tuple(S[:L])
    fill_step = [None] * D
    for d in range(D):                              # init loop (lines 206-212)
        if d < Nn:
            M[d][T[0:d + 1]] = pf = _Postfix()
            pf.increment(T[d + 1], True)
            entries[d] = 1
    correct = bytearray(max(Nn, 0))
    for i in range(2, L):
        found_x = False
        winner_correct = False
        cur_winner = winner
        d = 0
        while d < D and i - 2 >= d:
            curp = None
            if d == 0 or found_x:
                x = T[i - d - 1:i]
                curp = M[d].get(x)
                found_x = curp is not None
            if found_x:
                if curp.pred == T[i]:                           # predict() == data[i]
                    scoreboard[d] += 1
                    if scoreboard[d] >= scoreboard[winner]:
                        winner = d
                    if d == cur_winner:
                        C += 1
                        winner_correct = True
                        correct[i - 2] = 1
                if curp.increment(T[i], entries[d] < max_entries):
                    entries[d] += 1
                    if entries[d] == max_entries:
                        fill_step[d] = i
            elif entries[d] < max_entries:
                x = T[i - d - 1:i]
                pf = M[d].get(x)
                if pf is None:
                    M[d][x] = pf = _Postfix()
                pf.increment(T[i], True)
                entries[d] += 1                                  # counted even if the pair existed (E10)
                if entries[d] == max_entries:
                    fill_step[d] = i
            d += 1
        if winner_correct:
            run_len += 1
            if run_len > max_run:
                max_run = run_len
        else:
            run_len = 0
    return {"C": C, "r": max_run + 1, "N": Nn, "scoreboard": scoreboard, "winner": winner + 1,
            "entries": entries, "fill_step": fill_step, "correct": bytes(correct)}


def _steps_6_to_8(C: int, r: int, Nn: int, k: int) -> dict:
    """steps 6-8 via the reference's own helper functions (the comparison of interest is C, r)."""
    sys.path.insert(0, common.REFERENCE_DIR)
    from py90b import multimmc as ref
    pg, pgp = ref.p_global_prime(C, Nn)
    pl = ref.p_local(r, Nn)
    cands = {"P_global'": pgp, "P_local": pl, "1/k": 1.0 / k}
    binding = max(cands, key=cands.get)
    return {"P_global": pg, "P_global'": pgp, "P_local": pl, "binding": binding,
            "min_entropy": -math.log2(cands[binding])}


def summarize(tag: str, m: dict, k: int) -> dict:
    out = {"tag": tag, "C": m["C"], "r": m["r"], "N": m["N"], "winner": m["winner"],
           "scoreboard": m["scoreboard"], "entries": m["entries"], "fill_step": m["fill_step"]}
    out.update(_steps_6_to_8(m["C"], m["r"], m["N"], k))
    return out


# ----------------------------------------------------------------------------------------
# validation against py90b at the scaled cap
# ----------------------------------------------------------------------------------------
def validate_scaled(S: list[int], cap: int) -> dict:
    sys.path.insert(0, common.REFERENCE_DIR)
    from py90b import multimmc as ref
    k_obs = len(set(S))
    t0 = time.time()
    ref_res = ref.estimate(np.asarray(S, dtype=np.int64), 8, max_entries=cap, k_mode="observed")
    t_ref = time.time() - t0
    t0 = time.time()
    txt = mmc_text(S, max_entries=cap)
    t_txt = time.time() - t0
    t0 = time.time()
    cpp = mmc_cpp(S, max_entries=cap)
    t_cpp = time.time() - t0
    agree = {
        "C": int(ref_res["C"]) == txt["C"],
        "r": int(ref_res["r"]) == txt["r"],
        "N": int(ref_res["N"]) == txt["N"],
        "scoreboard": [int(v) for v in ref_res["scoreboard"]] == txt["scoreboard"],
        "winner": int(ref_res["winner"]) == txt["winner"],
        "entries": [int(v) for v in ref_res["entries"]] == txt["entries"],
    }
    # per-period steady-state check on the C++ vs text correct arrays
    return {
        "cap": cap, "L": len(S), "k_observed": k_obs,
        "py90b": {"C": int(ref_res["C"]), "r": int(ref_res["r"]), "N": int(ref_res["N"]),
                  "winner": int(ref_res["winner"]), "scoreboard": [int(v) for v in ref_res["scoreboard"]],
                  "entries": [int(v) for v in ref_res["entries"]],
                  "P_global": float(ref_res["P_global"]), "P_global'": float(ref_res["P_global'"]),
                  "P_local": float(ref_res["P_local"]), "min_entropy": float(ref_res["min_entropy"]),
                  "seconds": round(t_ref, 2), "module_sha256": common.sha256_file(ref.__file__)},
        "text_model": {**summarize("text", txt, k_obs), "seconds": round(t_txt, 2)},
        "cpp_model": {**summarize("cpp", cpp, k_obs), "seconds": round(t_cpp, 2)},
        "text_model_equals_py90b": agree,
        "all_agree": all(agree.values()),
        "delta_C_text_minus_cpp": txt["C"] - cpp["C"],
        "delta_r_text_minus_cpp": txt["r"] - cpp["r"],
    }


def per_period_table(S: list[int], info: dict, txt: dict, cpp: dict, periods: int = 3) -> list[dict]:
    """Which offsets of periods 2..(1+periods) the two models mark correct (for the record)."""
    lf, p = info["period1_start"], info["period"]
    rows = []
    for per in range(1, 1 + periods):
        base = lf + per * p
        tx = [t for t in range(p) if base + t - 2 < len(txt["correct"]) and txt["correct"][base + t - 2]]
        cp = [t for t in range(p) if base + t - 2 < len(cpp["correct"]) and cpp["correct"][base + t - 2]]
        rows.append({"period_index": per + 1, "text_correct_offsets": tx, "cpp_correct_offsets": cp,
                     "text_count": len(tx), "cpp_count": len(cp)})
    return rows


# ----------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------
def steady_rates(S: list[int], info: dict, txt: dict, cpp: dict, first: int = 3) -> dict:
    """mean correct-per-period of each model over periods first..last-1 (steady state)."""
    start, p = info["period1_start"], info["period"]
    nper = (len(S) - start) // p
    t = c = 0
    for per in range(first, nper - 1):
        base = start + per * p
        for off in range(p):
            i = base + off - 2
            if 0 <= i < len(txt["correct"]):
                t += txt["correct"][i]
                c += cpp["correct"][i]
    n = max(1, nper - 1 - first)
    return {"text_per_period": t / n, "cpp_per_period": c / n, "gap_text_minus_cpp": (t - c) / n, "periods_used": n}


def derived_full_size(rates: dict, info_full: dict, k: int) -> dict:
    """DERIVED (not measured) full-size figures from the steady-state per-period rates:
    C ~ rate x periods, r ~ the per-period run (bounded by the period), steps 6-8 via py90b."""
    periods = info_full["periods_in_tail"]
    Nn = info_full["total"] - 2
    out = {}
    for side in ("text", "cpp"):
        C = int(round(rates[f"{side}_per_period"] * periods))
        r = int(round(rates[f"{side}_per_period"])) + 1
        out[side] = {"C_approx": C, "r_approx": r, **_steps_6_to_8(C, r, Nn, k)}
    out["delta_min_entropy_cpp_minus_text"] = out["cpp"]["min_entropy"] - out["text"]["min_entropy"]
    out["note"] = "DERIVED from the scaled model's steady-state rates; the execution phase measures the tool and runs the reference"
    return out


def generate() -> None:
    rows = common.read_manifest()
    report = {"variants": {}, "search_record": "scratchpad x3_search.out (copied to logs/experiments/x3-search.out)"}
    prefix_written = False
    for variant in VARIANTS:
        S, info = build(N, MAX_ENTRIES, variant)
        arr = np.asarray(S, dtype=np.uint8)
        name = f"x3-mmc-orphan-{variant}-P{info['period']}-b{info['b_offset']}-q{info['pre_roll']}-8bit-1000000.bin"
        common.write_data_file(
            name, arr, 8, EXPERIMENT,
            f"[{variant}] fill {info['fill_length']} symbols over 16..255 with all 3-grams distinct, pre-roll {info['pre_roll']}, "
            f"then W={info['period_word']} (period {info['period']}, alphabet 1..8, {info['repeated_2grams']} repeated 2-grams) "
            f"repeated; depth 2 fills at W offset {info['b_offset']} of period 1, depth 16 at {info['b_offset'] + 14}; "
            f"orphans at offsets {info['b_offset'] + 1}..{info['b_offset'] + 14}; model expects: {info['expect']}",
            __file__, rows)
        if not prefix_written:        # both variants share the fill, so one prefix serves both
            common.write_data_file(
                f"x3-mmc-orphan-fill-8bit-prefix{PREFIX}.bin", arr[:PREFIX], 8, EXPERIMENT,
                f"first {PREFIX} symbols (fill phase only, shared by both variants; no saturation): light probe to "
                "check the C++ model against the production binary (non-compliant run)", __file__, rows)
            prefix_written = True
        Ss, info_s = build(SCALED_N, SCALED_CAP, variant)
        sname = f"x3-mmc-orphan-{variant}-scaled-cap{SCALED_CAP}-8bit-{SCALED_N}.bin"
        common.write_data_file(
            sname, np.asarray(Ss, dtype=np.uint8), 8, EXPERIMENT,
            f"[{variant}] the same construction scaled to max_entries={SCALED_CAP}: fill {info_s['fill_length']}, pre-roll "
            f"{info_s['pre_roll']}, then W repeated ({info_s['periods_in_tail']:.2f} periods); validates the models against "
            f"py90b (--max-entries={SCALED_CAP}); the production binary (cap 100,000) sees NO saturation on it",
            __file__, rows)

        v = validate_scaled(Ss, SCALED_CAP)
        txt_s = mmc_text(Ss, max_entries=SCALED_CAP)
        cpp_s = mmc_cpp(Ss, max_entries=SCALED_CAP)
        v["per_period_offsets"] = per_period_table(Ss, info_s, txt_s, cpp_s)
        v["steady_state"] = steady_rates(Ss, info_s, txt_s, cpp_s)
        v["construction_scaled"] = info_s
        v["construction_full"] = info
        v["full_size_file"] = name
        v["scaled_file"] = sname
        v["derived_full_size"] = derived_full_size(v["steady_state"], info, len(set(S)))
        txt_nc = mmc_text(Ss, max_entries=MAX_ENTRIES)
        cpp_nc = mmc_cpp(Ss, max_entries=MAX_ENTRIES)
        v["scaled_file_at_real_cap_no_saturation"] = {
            "text": {"C": txt_nc["C"], "r": txt_nc["r"], "winner": txt_nc["winner"]},
            "cpp": {"C": cpp_nc["C"], "r": cpp_nc["r"], "winner": cpp_nc["winner"]},
            "equal": (txt_nc["C"], txt_nc["r"]) == (cpp_nc["C"], cpp_nc["r"]),
            "note": "what the production binary must print on the scaled file (C, r) -- PLAN.md X3 light probe"}
        report["variants"][variant] = v
        print(f"[{variant}] text==py90b: {v['all_agree']}  steady text/cpp per period: "
              f"{v['steady_state']['text_per_period']:.3f}/{v['steady_state']['cpp_per_period']:.3f}  "
              f"scaled C,r text=({txt_s['C']},{txt_s['r']}) cpp=({cpp_s['C']},{cpp_s['r']})  "
              f"derived full-size H text={v['derived_full_size']['text']['min_entropy']:.4f} "
              f"cpp={v['derived_full_size']['cpp']['min_entropy']:.4f}")
        for row in v["per_period_offsets"]:
            print("   ", row)
        print("    scaled @ real cap:", v["scaled_file_at_real_cap_no_saturation"])
        if not v["all_agree"]:
            print(f"TEXT MODEL DOES NOT MATCH py90b on variant {variant} -- do not trust the construction", file=sys.stderr)
            sys.exit(2)
    S0, _ = build(N, MAX_ENTRIES, "naive")
    txt_p = mmc_text(S0[:PREFIX], max_entries=MAX_ENTRIES)
    cpp_p = mmc_cpp(S0[:PREFIX], max_entries=MAX_ENTRIES)
    report["prefix20000_at_real_cap"] = {
        "text": {"C": txt_p["C"], "r": txt_p["r"], "winner": txt_p["winner"]},
        "cpp": {"C": cpp_p["C"], "r": cpp_p["r"], "winner": cpp_p["winner"]},
        "equal": (txt_p["C"], txt_p["r"]) == (cpp_p["C"], cpp_p["r"]),
        "note": "what the production binary must print on the prefix file (C, r)"}
    print("prefix 20000 @ real cap:", report["prefix20000_at_real_cap"])
    with open(os.path.join(common.HERE, "x3-validation.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)


def model_cli(argv: list[str]) -> int:
    path = argv[argv.index("--model") + 1]
    cap = MAX_ENTRIES
    n = None
    if "--max-entries" in argv:
        cap = int(argv[argv.index("--max-entries") + 1])
    if "--n" in argv:
        n = int(argv[argv.index("--n") + 1])
    raw = np.fromfile(path, dtype=np.uint8)
    S = raw.tolist() if n is None else raw[:n].tolist()
    k = len(set(S))
    t0 = time.time()
    txt = mmc_text(S, max_entries=cap)
    t1 = time.time()
    cpp = mmc_cpp(S, max_entries=cap)
    t2 = time.time()
    out = {"file": path, "sha256": common.sha256_file(path), "L": len(S), "k_observed": k, "max_entries": cap,
           "text_model": {**summarize("text", txt, k), "seconds": round(t1 - t0, 1)},
           "cpp_model": {**summarize("cpp", cpp, k), "seconds": round(t2 - t1, 1)},
           "delta_C_text_minus_cpp": txt["C"] - cpp["C"], "delta_r_text_minus_cpp": txt["r"] - cpp["r"]}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    if "--model" in sys.argv:
        sys.exit(model_cli(sys.argv))
    sys.exit(common.standard_main(sys.argv[1:], EXPERIMENT, generate))
