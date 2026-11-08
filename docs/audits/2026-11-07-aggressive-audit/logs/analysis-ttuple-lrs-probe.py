#!/usr/bin/env python3
"""Analysis-phase probe for SP 800-90B 6.3.5 (t-Tuple) and 6.3.6 (LRS).

Brute-force implementation written from the spec text (overlapping tuple
counts via a dictionary of slices -- no suffix array, no LCP array), run
against cpp/ea_non_iid on tiny inputs with EA_ALLOW_SHORT_DATASET=1, comparing
the labelled verbose-3 fields.  Every output is written to a file; nothing is
piped into head/tail.  All runs are NON-COMPLIANT (short dataset) by design.

Usage: analysis-ttuple-lrs-probe.py <repo> <scratch_dir> <log_dir>
"""
import hashlib, json, math, os, random, subprocess, sys

Z_CODE = 2.5758293035489008      # ZALPHA (binary64 0.995 quantile) -- what the code uses
Z_TEXT = 2.576                   # what the standard prints (D-1 / C22c)

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def tuple_stats(S, cutoff=35):
    """Spec 6.3.5/6.3.6 quantities by brute force.
    Returns dict with Q (1-indexed list), v, u, t, and S_W sums for W in u..v."""
    L = len(S)
    Q = [None]  # Q[0] unused
    SW = {}     # W -> sum_i C(c_i,2)
    W = 1
    while W <= L:
        counts = {}
        for i in range(L - W + 1):
            key = S[i:i+W]
            counts[key] = counts.get(key, 0) + 1
        q = max(counts.values())
        Q.append(q)
        SW[W] = sum(c*(c-1)//2 for c in counts.values())
        if q < 2:
            break
        W += 1
    v = len(Q) - 1 if Q[-1] >= 2 else len(Q) - 2   # largest W with Q[W] >= 2
    if v < 0: v = 0
    # u: smallest W with Q[W] < cutoff (Q[W]=1 for W>v, so u <= v+1)
    u = 1
    while u <= v and Q[u] >= cutoff:
        u += 1
    t = u - 1
    return {'Q': Q, 'v': v, 'u': u, 't': t, 'SW': SW, 'L': L}

def ttuple(st, Z):
    L, Q, t = st['L'], st['Q'], st['t']
    if t < 1:
        return None
    pmax = max((Q[i] / (L - i + 1)) ** (1.0 / i) for i in range(1, t + 1))
    pu = min(1.0, pmax + Z * math.sqrt(pmax * (1 - pmax) / (L - 1)))
    return {'t': t, 'p_hat_max': pmax, 'p_u': pu, 'H': -math.log2(pu)}

def lrs(st, Z):
    L, u, v, SW = st['L'], st['u'], st['v'], st['SW']
    if v < u:
        return None
    phat = 0.0
    per_W = {}
    for W in range(u, v + 1):
        denom = (L - W + 1) * (L - W) // 2
        PW = SW[W] / denom
        pm = PW ** (1.0 / W)
        per_W[W] = (PW, pm)
        phat = max(phat, pm)
    pu = min(1.0, phat + Z * math.sqrt(phat * (1 - phat) / (L - 1)))
    return {'u': u, 'v': v, 'p_hat': phat, 'p_u': pu, 'H': -math.log2(pu), 'per_W': per_W}

def bits_of(raw, word_size):
    out = bytearray()
    for b in raw:
        for j in range(word_size):
            out.append((b >> (word_size - 1 - j)) & 1)
    return bytes(out)

def parse_labels(text):
    """Labelled reads only (instrument rule 5)."""
    got = {}
    for line in text.splitlines():
        for lab in ('Literal', 'Bitstring'):
            for est in ('t-Tuple Estimate', 'LRS Estimate'):
                pre = f'{lab} {est}: '
                if line.startswith(pre):
                    k, _, val = line[len(pre):].partition(' = ')
                    got[(lab, est, k.strip())] = val.strip()
        if 'No strings are repeated 35 times' in line:
            got['msg_tt_fail'] = line.strip()
        if "v<u. Can't Run LRS Test" in line:
            got['msg_lrs_vu'] = line.strip()
        if 'no repeated substrings' in line:
            got['msg_norepeat'] = line.strip()
        if line.startswith('H_original') or line.startswith('H_bitstring') or line.startswith('min(') or line.startswith('H_I'):
            got.setdefault('summary', []).append(line.strip())
    return got

def relclose(a, b, tol=1e-12):
    a = float(a); b = float(b)
    if a == b: return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))

def main():
    repo, scratch, logdir = sys.argv[1:4]
    os.makedirs(scratch, exist_ok=True); os.makedirs(logdir, exist_ok=True)
    tool = os.path.join(repo, 'cpp', 'ea_non_iid')
    tool_sha = sha256(tool)
    env = dict(os.environ, EA_ALLOW_SHORT_DATASET='1', OMP_NUM_THREADS='2')
    report = []
    def say(s=''):
        report.append(s)

    say(f'# t-Tuple / LRS brute-force probe (analysis phase, 2026-11-07)')
    say(f'binary: {tool}')
    say(f'binary sha256: {tool_sha}')
    say(f'env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2  (every run below is NON-COMPLIANT: short dataset)')
    say(f'tolerance for floats: rel 1e-12; integers exact; brute force uses Z={Z_CODE!r} (ZALPHA) for the code comparison')
    say()

    # ---- spec cross-check of the brute force itself (cutoff 3, Z=2.576) ----
    spec_S = bytes([2,2,0,1,0,2,0,1,2,1,2,0,1,2,1,0,0,1,0,0,0])
    st3 = tuple_stats(spec_S, cutoff=3)
    tt3 = ttuple(st3, Z_TEXT); lr3 = lrs(st3, Z_TEXT)
    say('## Brute force vs the standard\'s worked examples (cutoff 3, Z = 2.576) -- validates the probe, not the code')
    say(f'6.3.5 example expects t=3, Q=[9,4,3], p_hat_max=0.5405, p_u=0.8276, H=0.273')
    say(f'   brute force: t={st3["t"]} Q[1..3]={st3["Q"][1:4]} p_hat_max={tt3["p_hat_max"]:.4f} p_u={tt3["p_u"]:.4f} H={tt3["H"]:.3f}')
    say(f'6.3.6 example expects u=4, v=5, P4=0.0131, P5=0.0074, Pmax4=0.3381, Pmax5=0.3744, p_hat=0.3744, p_u=0.6531, H=0.6146')
    say(f'   brute force: u={lr3["u"]} v={lr3["v"]} P4={lr3["per_W"][4][0]:.4f} P5={lr3["per_W"][5][0]:.4f} '
        f'Pmax4={lr3["per_W"][4][1]:.4f} Pmax5={lr3["per_W"][5][1]:.4f} p_hat={lr3["p_hat"]:.4f} p_u={lr3["p_u"]:.4f} H={lr3["H"]:.4f}')
    say()

    rng = random.Random(20261107)
    cases = []
    # A: the standard's example sequence, width 2 (k=3 => Bitstring path also runs)
    cases.append(('A_spec_example_w2', spec_S, 2))
    # B: biased bits, width 1
    cases.append(('B_bits_p03_n4000_w1', bytes(1 if rng.random() < 0.3 else 0 for _ in range(4000)), 1))
    # C: 4 raw symbols spread over the byte, biased, width 8
    syms = [3, 17, 128, 255]; probs = [0.5, 0.3, 0.15, 0.05]
    cases.append(('C_k4_biased_n1200_w8', bytes(rng.choices(syms, probs)[0] for _ in range(1200)), 8))
    # D: cutoff boundary: 'AB' exactly 35 times, 'ABC' exactly 34 times, filler from 200 other values
    A, B, C = 250, 251, 252
    filler_alpha = list(range(0, 200))
    seq = bytearray()
    for i in range(35):
        seq += bytes(rng.choice(filler_alpha) for _ in range(20))
        seq += bytes([A, B]) + (bytes([C]) if i < 34 else b'')
    seq += bytes(rng.choice(filler_alpha) for _ in range(20))
    cases.append(('D_cutoff35_boundary_w8', bytes(seq), 8))
    # E: period-7 over 7 distinct symbols 0..6, width 3 (v = n-7, stresses the flush loop)
    pat = bytes([0, 3, 1, 6, 2, 5, 4])
    cases.append(('E_period7_n300_w3', (pat * 60)[:300], 3))
    # F: constant zeros, width 1 (p_hat = 1 exactly; checks the -0.0 path)
    cases.append(('F_const0_n500_w1', bytes(500), 1))
    # G: full 8-bit random, n=2000: Q[1] < 35 so t-Tuple must decline while LRS runs with u=1
    cases.append(('G_rand8_n2000_w8', bytes(rng.randrange(256) for _ in range(2000)), 8))

    manifest = {}
    for name, data, w in cases:
        path = os.path.join(scratch, name + '.bin')
        with open(path, 'wb') as f:
            f.write(data)
        manifest[name] = {'path': path, 'sha256': sha256(path), 'n': len(data), 'w': w}
        out_path = os.path.join(logdir, f'analysis-ttuple-lrs-{name}.out')
        with open(out_path, 'w') as of:
            rc = subprocess.run([tool, '-i', '-a', '-v', '-v', path, str(w)], env=env,
                                stdout=of, stderr=subprocess.STDOUT, cwd=repo).returncode
        text = open(out_path).read()
        got = parse_labels(text)
        say(f'## {name}: n={len(data)} width={w} sha256={manifest[name]["sha256"]}')
        say(f'   cmd: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 {tool} -i -a -v -v {path} {w}   -> exit {rc}; stdout at {out_path}')
        k = len(set(data))
        masked = bytes(b & ((1 << w) - 1) for b in data)
        views = [('Literal', masked)]
        if k > 2:
            views.append(('Bitstring', bits_of(masked, w)))
        else:
            say(f'   alph_size={k} <= 2 under -i: Bitstring path not run by design (non_iid_main.cpp:467)')
        for lab, S in views:
            st = tuple_stats(S)
            tt = ttuple(st, Z_CODE); lr = lrs(st, Z_CODE)
            say(f'   [{lab}] brute force: L={st["L"]} v={st["v"]} u={st["u"]} t={st["t"]} Q[1..min(v,6)]={st["Q"][1:min(st["v"],6)+1]}')
            # t-tuple
            if tt is None:
                say(f'   [{lab}] t-Tuple: brute force says UNDEFINED (Q[1]={st["Q"][1]} < 35); code message: {got.get("msg_tt_fail") or got.get("msg_norepeat") or "NONE FOUND"}')
                if (lab, 't-Tuple Estimate', 't') in got:
                    say(f'   [{lab}] !!! MISMATCH: code printed a t-Tuple estimate where the spec defines none: t={got[(lab,"t-Tuple Estimate","t")]}')
            else:
                ct = got.get((lab, 't-Tuple Estimate', 't')); cp = got.get((lab, 't-Tuple Estimate', 'p-hat_max'))
                cu = got.get((lab, 't-Tuple Estimate', 'p_u')); ch = got.get((lab, 't-Tuple Estimate', 'min entropy'))
                ok = (ct is not None and int(ct) == tt['t'] and relclose(cp, tt['p_hat_max']) and relclose(cu, tt['p_u']) and relclose(ch, tt['H']))
                say(f'   [{lab}] t-Tuple: brute t={tt["t"]} p_hat_max={tt["p_hat_max"]!r} p_u={tt["p_u"]!r} H={tt["H"]!r}')
                say(f'   [{lab}] t-Tuple: code  t={ct} p_hat_max={cp} p_u={cu} H={ch}  => {"MATCH" if ok else "!!! MISMATCH"}')
                tt_text = ttuple(st, Z_TEXT)
                say(f'   [{lab}] t-Tuple with the text\'s 2.576 instead: H={tt_text["H"]!r} (code - text = {tt["H"]-tt_text["H"]:+.3e} bit; D-1 direction)')
            # LRS
            if lr is None:
                say(f'   [{lab}] LRS: brute force says CANNOT COMPUTE (v={st["v"]} < u={st["u"]}); code message: {got.get("msg_lrs_vu") or got.get("msg_norepeat") or "NONE FOUND"}')
                if (lab, 'LRS Estimate', 'u') in got:
                    say(f'   [{lab}] !!! MISMATCH: code printed an LRS estimate where the spec defines none')
            else:
                cu_ = got.get((lab, 'LRS Estimate', 'u')); cv = got.get((lab, 'LRS Estimate', 'v'))
                cp = got.get((lab, 'LRS Estimate', 'p-hat')); cpu = got.get((lab, 'LRS Estimate', 'p_u')); ch = got.get((lab, 'LRS Estimate', 'min entropy'))
                ok = (cu_ is not None and int(cu_) == lr['u'] and int(cv) == lr['v'] and relclose(cp, lr['p_hat']) and relclose(cpu, lr['p_u']) and relclose(ch, lr['H']))
                say(f'   [{lab}] LRS: brute u={lr["u"]} v={lr["v"]} p_hat={lr["p_hat"]!r} p_u={lr["p_u"]!r} H={lr["H"]!r}')
                say(f'   [{lab}] LRS: code  u={cu_} v={cv} p_hat={cp} p_u={cpu} H={ch}  => {"MATCH" if ok else "!!! MISMATCH"}')
        for s in got.get('summary', []):
            say(f'   summary line: {s}')
        say()

    with open(os.path.join(logdir, 'analysis-ttuple-lrs-probe-manifest.json'), 'w') as f:
        json.dump({'binary_sha256': tool_sha, 'cases': manifest}, f, indent=2)
    with open(os.path.join(logdir, 'analysis-ttuple-lrs-probe.log'), 'w') as f:
        f.write('\n'.join(report) + '\n')

if __name__ == '__main__':
    main()
