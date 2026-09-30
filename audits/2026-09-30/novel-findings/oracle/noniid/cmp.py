#!/usr/bin/env python3
"""Run ea_non_iid -vv on a file and compare predictor C, r, N (and entropy) with ref90b."""
import os
import re
import subprocess
import sys

import ref90b

SCR = '/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad'
TOOL = os.environ.get('EA_NON_IID', SCR + '/audit/rel/cpp/ea_non_iid')
NAMES = {'MultiMCW': 'mcw', 'Lag': 'lag', 'MultiMMC': 'mmc', 'LZ78Y': 'lz'}


def run_tool(path, bits=None, extra=()):
    cmd = [TOOL, '-vv'] + list(extra) + [path] + ([str(bits)] if bits else [])
    out = subprocess.run(['timeout', '900'] + cmd, capture_output=True, text=True).stdout
    res = {}
    for m in re.finditer(r'^(Literal|Bitstring) (\S+) Prediction Estimate: (C|r|N|min entropy|P_global\'|P_local) = (\S+)$', out, re.M):
        lab, est, key, val = m.groups()
        res.setdefault((lab, est), {})[key] = float(val) if key in ('min entropy', "P_global'", 'P_local') else int(val)
    return res, out


HARNESS = SCR + '/audit/work/noniid/h/harness'
SHORT = {'MultiMCW': 'mcw', 'Lag': 'lag', 'MultiMMC': 'mmc', 'LZ78Y': 'lz'}


def run_harness(path, bits, which, modes=('lit',)):
    res = {}
    out = ''
    for mode in modes:
        cmd = ['timeout', '900', HARNESS, path, str(bits or 0), mode] + [SHORT[w] for w in which]
        out += subprocess.run(cmd, capture_output=True, text=True).stdout
    for m in re.finditer(r'^(Literal|Bitstring) (\S+) Prediction Estimate: (C|r|N|min entropy|P_global\'|P_local) = (\S+)$', out, re.M):
        lab, est, key, val = m.groups()
        res.setdefault((lab, est), {})[key] = float(val) if key in ('min entropy', "P_global'", 'P_local') else int(val)
    return res, out


def translate(raw, bits):
    mask = (1 << bits) - 1
    vals = [v & mask for v in raw]
    alph = sorted(set(vals))
    tab = {v: i for i, v in enumerate(alph)}
    return [tab[v] for v in vals], len(alph)


def bitstring(raw, bits):
    out = []
    for v in raw:
        for j in range(bits):
            out.append((v >> (bits - 1 - j)) & 1)
    return out


def ref_all(S, k, which):
    res = {}
    for est in which:
        f = NAMES[est]
        if f == 'mcw':
            if len(S) < 4096:
                continue
            C, N, r, kk = ref90b.multi_mcw(S, k)
        elif f == 'lag':
            C, N, r, kk = ref90b.lag(S, k)
        elif f == 'mmc':
            C, N, r, kk, _ = ref90b.multi_mmc(S, k)
        elif f == 'lz':
            C, N, r, kk, _ = ref90b.lz78y(S, k)
        pe = ref90b.pred_estimate(C, N, r, k)
        res[est] = pe
    return res


def compare(path, bits, which=('MultiMCW', 'Lag', 'MultiMMC', 'LZ78Y'), do_bitstring=False, quiet=False):
    raw = list(open(path, 'rb').read())
    if os.environ.get('FULLTOOL', '0') == '1':
        tool, _ = run_tool(path, bits)
    else:
        tool, _ = run_harness(path, bits, which, ('lit', 'bit') if do_bitstring else ('lit',))
    if bits is None:
        m = 0
        for v in raw:
            m |= v
        bits = max(1, m.bit_length())
    S, k = translate(raw, bits)
    bad = []
    sets = [('Literal', S, k)]
    if do_bitstring and k > 2:
        sets.append(('Bitstring', bitstring(raw, bits), 2))
    for lab, seq, kk in sets:
        ref = ref_all(seq, kk, which)
        for est in which:
            t = tool.get((lab, est))
            r = ref.get(est)
            if t is None and r is None:
                continue
            if t is None or r is None:
                bad.append((lab, est, 'missing', t, r))
                continue
            same = (t['C'] == r['C'] and t['r'] == r['r'] and t['N'] == r['N'])
            dH = t['min entropy'] - r['H']
            if not quiet or not same or abs(dH) > 1e-9:
                print(f"{os.path.basename(path)} {lab:9s} {est:8s} tool C={t['C']} r={t['r']} N={t['N']} H={t['min entropy']:.12g} | ref C={r['C']} r={r['r']} N={r['N']} H={r['H']:.12g} | {'OK' if same else 'DIFF'} dH={dH:.3g}")
            if not same:
                bad.append((lab, est, t, r))
    return bad


if __name__ == '__main__':
    path = sys.argv[1]
    bits = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != '-' else None
    which = sys.argv[3].split(',') if len(sys.argv) > 3 else ('MultiMCW', 'Lag', 'MultiMMC', 'LZ78Y')
    bad = compare(path, bits, which, do_bitstring=os.environ.get('BITS', '0') == '1')
    print('MISMATCHES:', len(bad))
