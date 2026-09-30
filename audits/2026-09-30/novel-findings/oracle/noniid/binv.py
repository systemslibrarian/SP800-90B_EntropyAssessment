#!/usr/bin/env python3
"""Binary path vs generic path of the SAME tool estimator: X over {0,1} runs the binary
implementation (alph_size==2); X+[2] (one extra symbol at the very end) forces the generic
implementation.  The extra final symbol can only affect the last prediction, so C and r must agree."""
import os, random, re, subprocess, sys
H = os.path.dirname(os.path.abspath(__file__))
def run(path, ests):
    out = subprocess.run(['timeout', '1800', f'{H}/h/harness', path, '0', 'lit'] + ests, capture_output=True, text=True).stdout
    res = {}
    for m in re.finditer(r'^Literal (\S+) Prediction Estimate: (C|r|N) = (\d+)$', out, re.M):
        res.setdefault(m.group(1), {})[m.group(2)] = int(m.group(3))
    return res
def lfsr(n, taps=(16, 14, 13, 11), seed=0xACE1):
    s = seed; out = []
    for _ in range(n):
        b = 0
        for t in taps: b ^= (s >> (16 - t)) & 1
        s = (s >> 1) | (b << 15); out.append(s & 1)
    return out
def cases():
    r = random.Random(4242)
    yield 'rand1M', [r.randrange(2) for _ in range(1000000)]
    yield 'bias0.8_300k', [1 if r.random() < 0.8 else 0 for _ in range(300000)]
    s = []; st = 0
    for _ in range(300000):
        st = st if r.random() < 0.9 else 1 - st; s.append(st)
    yield 'sticky_300k', s
    per = [r.randrange(2) for _ in range(97)]
    yield 'per97noise_300k', [per[i % 97] ^ (1 if r.random() < 0.02 else 0) for i in range(300000)]
    yield 'lfsr16_300k', lfsr(300000)
    yield 'tiny_ties_50k', [(i // 3) % 2 if i % 5 else r.randrange(2) for i in range(50000)]
    # filling phase then periodic tail (dictionary-full semantics in both paths)
    yield 'fill_then_per', [r.randrange(2) for _ in range(250000)] + per * 1500
if __name__ == '__main__':
    ests = ['mmc', 'lz', 'lag', 'mcw']
    for name, X in cases():
        p1 = f'{H}/data/binv/{name}.bin'; p2 = f'{H}/data/binv/{name}_plus2.bin'
        open(p1, 'wb').write(bytes(X)); open(p2, 'wb').write(bytes(X + [2]))
        a = run(p1, ests); b = run(p2, ests)
        for e in ('MultiMMC', 'LZ78Y', 'Lag', 'MultiMCW'):
            x, y = a.get(e), b.get(e)
            ok = x and y and x['C'] == y['C'] and x['r'] == y['r'] and y['N'] == x['N'] + 1
            print(f"{name:16s} {e:8s} binary C={x and x['C']} r={x and x['r']} N={x and x['N']} | generic C={y and y['C']} r={y and y['r']} N={y and y['N']} {'OK' if ok else 'DIFF'}", flush=True)
