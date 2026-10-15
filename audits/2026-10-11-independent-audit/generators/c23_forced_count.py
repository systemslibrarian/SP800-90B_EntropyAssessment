#!/usr/bin/env python3
"""Forced-count restart matrices for OC-7's acceptance demonstration.

An 8-bit 1000x1000 matrix in which column 17 is forced to contain exactly X
copies of symbol 0, so X_max = X. At H_I = 7 the exact 3.1.4.3 cutoff is 23, so
the standard rejects X_max >= 24, while the tool's simulated cutoff is 27:

    X = 24  ->  tool "Restart Sanity Check Passed..."   standard: fail
    X = 25  ->  tool "Restart Sanity Check Passed..."   standard: fail
    X = 28  ->  tool "*** Restart Sanity Check Failed ***"  (positive control)

Column j of the matrix is at indices i*1000 + j, matching rdata[i*r + j] in
restart_main.cpp with r = 1000.
"""
import random, hashlib, collections, sys

def build(X, seed=0xC23ACC):
    r = random.Random(seed)
    d = bytearray(r.getrandbits(8) for _ in range(1000000))
    col = [i * 1000 + 17 for i in range(1000)]
    for idx in col:                      # clear incidental zeros so the count is exact
        if d[idx] == 0: d[idx] = 1
    for idx in col[:X]: d[idx] = 0
    return bytes(d)

def xmax(d):
    m = 0
    for i in range(1000):
        m = max(m, max(collections.Counter(d[i*1000:(i+1)*1000]).values()))
    for j in range(1000):
        m = max(m, max(collections.Counter(bytes(d[i*1000+j] for i in range(1000))).values()))
    return m

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    for X in (24, 25, 28):
        d = build(X)
        open(f'{out}/forced-X{X}.bin', 'wb').write(d)
        print(f'forced-X{X}.bin  X_max={xmax(d)}  sha256={hashlib.sha256(d).hexdigest()}')
