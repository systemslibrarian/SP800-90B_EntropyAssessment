#!/usr/bin/env python3
"""Fixtures for OC-5 (cluster C07, the len_LRS_test aborts). Audit 2026-10-14.

Site A — assert(p_col >= 1.0L/k) at lrs_test.h:652.
  bal<k>.bin: 1,000,000 samples, each of k symbols exactly L/k times, shuffled.
  k must divide L (1e6 = 2^6 * 5^6). Aborts for k in {25,100,125,200,250};
  passes for k in {20,32,40,50,64}. near125-d<d>.bin perturbs two counts by +/-d
  to show that ANY departure from exact balance clears the assert.

Site B — assert(p_colPower >= LDBL_MIN) at lrs_test.h:683.
  lrsrep-<W>.bin: a 1-bit stream with a repeated block of length W implanted, so
  the longest repeated substring is >= W. On a 64-bit long double the abort needs
  W > 1022; measured boundary between W=1000 (passes) and W=1100 (aborts).
"""
import random, hashlib, sys

def site_a(out='.'):
    L = 1000000
    for k in (20, 25, 32, 40, 50, 64, 100, 125, 200, 250):
        assert L % k == 0, k
        a = [i % k for i in range(L)]
        random.Random(0xB41A).shuffle(a)
        b = bytes(a)
        open(f'{out}/bal{k}.bin', 'wb').write(b)
        print(f'bal{k}.bin', hashlib.sha256(b).hexdigest())

def site_a_near(out='.'):
    L, k = 1000000, 125
    base = L // k
    for d in (1, 2, 10, 100, 1000):
        a = []
        for i in range(k):
            a += [i] * (base + (d if i == 0 else (-d if i == 1 else 0)))
        assert len(a) == L
        random.Random(0xB41A).shuffle(a)
        b = bytes(a)
        open(f'{out}/near{k}-d{d}.bin', 'wb').write(b)
        print(f'near{k}-d{d}.bin', hashlib.sha256(b).hexdigest())

def site_b(out='.'):
    r = random.Random(0x90B2026C07)
    for W in (500, 1000, 1100, 2000):
        b = bytearray(r.getrandbits(1) for _ in range(1000000))
        b[600000:600000 + W] = bytes(b[1000:1000 + W])
        d = bytes(b)
        open(f'{out}/lrsrep-{W}.bin', 'wb').write(d)
        print(f'lrsrep-{W}.bin', hashlib.sha256(d).hexdigest())

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    site_a(out); site_a_near(out); site_b(out)
