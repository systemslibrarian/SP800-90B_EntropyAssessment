#!/usr/bin/env python3
"""Metamorphic: literal-path estimates under symbol bijections (order-preserving and not)."""
import random, re, subprocess, sys
SCR = '/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad'
TOOL = SCR + '/audit/rel/cpp/ea_non_iid'
def lit(path):
    out = subprocess.run(['timeout', '600', TOOL, '-vv', path, '8'], capture_output=True, text=True).stdout
    d = {}
    for m in re.finditer(r'^Literal (.+?) (?:Estimate|Prediction Estimate): (min entropy|C|r) = (\S+)$', out, re.M):
        d[(m.group(1), m.group(2))] = m.group(3)
    h = re.search(r'^H_original = (\S+)$', out, re.M)
    d['H_original'] = h.group(1) if h else None
    return d
def run(name, base, R):
    p0 = f'data/meta/{name}_id.bin'; open(p0, 'wb').write(bytes(base))
    ref = lit(p0)
    syms = sorted(set(base))
    res = []
    for t in range(R):
        rnd = random.Random(t)
        img = rnd.sample(range(256), len(syms))   # arbitrary injective relabelling (not order-preserving)
        if t == 0: img = sorted(img)              # t=0: order-preserving control
        m = dict(zip(syms, img))
        p = f'data/meta/{name}_b{t}.bin'; open(p, 'wb').write(bytes(m[v] for v in base))
        d = lit(p)
        diffs = {k: (ref[k], d.get(k)) for k in ref if ref[k] != d.get(k)}
        res.append(diffs)
        print(name, 'bij', t, 'order-preserving' if t == 0 else 'permuted', 'DIFFS:' if diffs else 'identical', diffs if diffs else '', flush=True)
    return res
if __name__ == '__main__':
    r = random.Random(99)
    L = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    # full-byte alphabet, strong low-order structure with many count ties
    base = []
    s = 0
    for _ in range(L):
        s = (s * 31 + r.choice((1, 2, 3, 5))) % 256 if r.random() < 0.7 else r.randrange(256)
        base.append(s)
    run('full256', base, 6)
    # small alphabet (5 symbols), tie-heavy Markov
    base = [0]
    for _ in range(L - 1):
        base.append((base[-1] + r.choice((1, 1, 2, 3))) % 5 if r.random() < 0.8 else r.randrange(5))
    run('k5', base, 6)
    # 3 symbols with frequent equal-count ties in MMC/LZ dictionaries
    base = [r.choice((0, 1, 2)) if i % 4 else (i // 4) % 3 for i in range(L)]
    run('k3tie', base, 6)
