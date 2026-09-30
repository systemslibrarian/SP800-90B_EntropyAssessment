#!/usr/bin/env python3
"""Fast comparator: tool estimator headers (harness) vs C++ literal reference (h/ref90b)."""
import os, re, subprocess, sys
H = os.path.dirname(os.path.abspath(__file__)) + '/h/'
def tool(path, bits, mode, ests):
    out = subprocess.run(['timeout', '1800', H + 'harness', path, str(bits), mode] + ests, capture_output=True, text=True).stdout
    res = {}
    for m in re.finditer(r'^(?:Literal|Bitstring) (\S+) Prediction Estimate: (C|r|N|min entropy) = (\S+)$', out, re.M):
        est, key, val = m.groups()
        res.setdefault(est, {})[key] = val
    return res
def ref(path, bits, mode, ests, env=None):
    e = dict(os.environ); e.update(env or {})
    out = subprocess.run(['timeout', '3600', H + 'ref90b', path, str(bits), mode] + ests, capture_output=True, text=True, env=e).stdout
    res = {}
    for m in re.finditer(r'^REF (\S+) C=(\d+) r=(\d+) N=(\d+)$', out, re.M):
        est, C, r, N = m.groups(); res[est] = dict(C=C, r=r, N=N)
    info = re.findall(r'^REFINFO .*$', out, re.M)
    return res, info
MAP = {'mcw': 'MultiMCW', 'lag': 'Lag', 'mmc': 'MultiMMC', 'lz': 'LZ78Y'}
def compare(path, bits, mode, ests, env=None, show=True):
    t = tool(path, bits, mode, ests); r, info = ref(path, bits, mode, ests, env)
    bad = 0
    for e in ests:
        tt = t.get(MAP[e]); rr = r.get(e)
        if tt is None or rr is None:
            if show: print(f'{os.path.basename(path)} {mode} {e}: missing tool={tt} ref={rr}')
            continue
        same = all(tt[k] == rr[k] for k in ('C', 'r', 'N'))
        bad += (not same)
        if show: print(f"{os.path.basename(path)} {mode} {e:4s} tool C={tt['C']} r={tt['r']} N={tt['N']} H={tt['min entropy']} | ref C={rr['C']} r={rr['r']} N={rr['N']} {'OK' if same else 'DIFF'}")
    if show:
        for i in info: print('   ', i)
    return bad
if __name__ == '__main__':
    path, bits, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    ests = sys.argv[4].split(',') if len(sys.argv) > 4 else ['mcw', 'lag', 'mmc', 'lz']
    sys.exit(compare(path, bits, mode, ests))
