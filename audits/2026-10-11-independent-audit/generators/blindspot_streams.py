#!/usr/bin/env python3
"""
Generators for OC-15: what the SP 800-90B non-IID battery does and does not see.

Each produces 1,000,000 one-bit samples. All five are GLOBALLY UNBIASED, so the
most-common-value estimator cannot distinguish any of them from a fair coin --
the structure is entirely in the correlation.

  A_control      fair coin, no structure
  B_osc5000      P(1) = 0.5 + 0.10*sin(2*pi*i/5000)   slow bias drift,
                 period 5000 samples = 60 Hz at 0.3 Mbit/s
  C_osc500       same amplitude, period 500
  D_lag5000      x_i = x_{i-5000} with prob 0.60, else fair coin.
                 P(agree) = 0.80 -- STRONG, and note it produces exact
                 repeated substrings, which is why LRS catches it.
  E_weaklag5000  x_i = x_{i-5000} with prob 0.04, else fair coin.
                 P(agree) = 0.52 -- a 40-sigma autocorrelation signal that
                 produces almost no exact repetition. This is the one the
                 battery misses.

Usage: python3 blindspot_streams.py [outdir]
Digests are printed so a rerun can be confirmed identical.
"""
import random, math, hashlib, sys, os

N = 1000000
A = 0.10
LAG = 5000

def emit(outdir, name, samples):
    b = bytes(bytearray(samples))
    p = os.path.join(outdir, name)
    open(p, 'wb').write(b)
    agree = sum(1 for i in range(LAG, N) if b[i] == b[i-LAG]) / (N - LAG)
    se = 0.5 / math.sqrt(N - LAG)
    print("%-20s P(1)=%.6f  P(agree@%d)=%.5f (%+.1f sigma)  sha256=%s"
          % (name, sum(b)/N, LAG, agree, (agree-0.5)/se,
             hashlib.sha256(b).hexdigest()))

def main(outdir='.'):
    r = random.Random(0xA)
    emit(outdir, 'A_control.bin', [r.getrandbits(1) for _ in range(N)])

    for name, seed, T in (('B_osc5000.bin', 0xB, 5000), ('C_osc500.bin', 0xC, 500)):
        r = random.Random(seed)
        emit(outdir, name,
             [1 if r.random() < 0.5 + A*math.sin(2*math.pi*i/T) else 0
              for i in range(N)])

    for name, seed, pcopy in (('D_lag5000.bin', 0xD, 0.60),
                              ('E_weaklag5000.bin', 0xE, 0.04)):
        r = random.Random(seed)
        out = [r.getrandbits(1) for _ in range(LAG)]
        for i in range(LAG, N):
            out.append(out[i-LAG] if r.random() < pcopy else r.getrandbits(1))
        emit(outdir, name, out)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
