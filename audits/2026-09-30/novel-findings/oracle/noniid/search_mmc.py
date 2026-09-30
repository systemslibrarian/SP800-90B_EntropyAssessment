#!/usr/bin/env python3
"""Scaled-model search: tool MultiMMC compiled with small MAX_ENTRIES vs literal spec ref (MAXE env).
Looks for C/r differences and their direction; also checks that ref's tool-emulation equals the tool."""
import os, random, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref90b
H = os.path.dirname(os.path.abspath(__file__))
def tool(path, M):
    out = subprocess.run([f'{H}/small/harness_{M}', path, '0', 'lit', 'mmc'], capture_output=True, text=True).stdout
    g = dict(re.findall(r'MultiMMC Prediction Estimate: (C|r|N|min entropy) = (\S+)', out))
    return g
def ref(path, M):
    out = subprocess.run([f'{H}/h/ref90b', path, '0', 'lit', 'mmc', 'emu'], capture_output=True, text=True, env=dict(os.environ, MAXE=str(M))).stdout
    res = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'^REF (mmc\S*) C=(\d+) r=(\d+) N=\d+', out, re.M)}
    return res
def gen(r):
    k = r.randrange(3, 10); L = r.randrange(200, 2500)
    S = []
    while len(S) < L:
        m = r.random()
        if m < 0.35 or len(S) < 20:
            S += [r.randrange(k) for _ in range(r.randrange(1, 60))]
        elif m < 0.7:
            a = r.randrange(len(S)); n = r.randrange(3, 60)
            seg = S[a:a + n]
            if r.random() < 0.3 and seg: seg[r.randrange(len(seg))] = r.randrange(k)
            S += seg * r.randrange(1, 6)
        else:
            per = [r.randrange(k) for _ in range(r.randrange(2, 20))]
            S += per * r.randrange(2, 30)
    return S[:L]
if __name__ == '__main__':
    n = int(sys.argv[1]); seed0 = int(sys.argv[2])
    os.makedirs(f'{H}/data/search', exist_ok=True)
    stats = dict(cases=0, emu_mismatch=0, diffC=0, diffr=0, toolC_lower=0, toolC_higher=0, toolr_higher=0, toolr_lower=0)
    worst = []
    for t in range(n):
        r = random.Random(seed0 + t); M = r.choice((12, 30, 60, 150))
        S = gen(r); p = f'{H}/data/search/c{seed0 + t}.bin'; open(p, 'wb').write(bytes(S))
        tt = tool(p, M); rr = ref(p, M)
        if 'C' not in tt or 'mmc' not in rr: continue
        stats['cases'] += 1
        tc, tr = int(tt['C']), int(tt['r'])
        if (tc, tr) != rr['mmcemu_chain_noreset']:
            stats['emu_mismatch'] += 1; print('EMU MISMATCH', p, M, (tc, tr), rr, flush=True)
        sc, sr = rr['mmc']
        if tc != sc: stats['diffC'] += 1; stats['toolC_lower' if tc < sc else 'toolC_higher'] += 1
        if tr != sr: stats['diffr'] += 1; stats['toolr_higher' if tr > sr else 'toolr_lower'] += 1
        if tc != sc or tr != sr:
            N = len(S) - 2; k = len(set(S))
            Ht = float(tt['min entropy']); Hs = ref90b.pred_estimate(sc, N, sr, k)['H']
            if Ht > Hs + 1e-12: stats['toolH_higher'] = stats.get('toolH_higher', 0) + 1
            worst.append((Ht - Hs, sc - tc, tr - sr, p, M, (tc, tr), rr))
    print(stats)
    worst.sort(key=lambda w: -w[0])
    for w in worst[:15]: print(w)
