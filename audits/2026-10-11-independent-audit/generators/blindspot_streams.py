#!/usr/bin/env python3
"""
Calibration and defect corpus for OC-15/16/17 -- what the SP 800-90B non-IID
battery does and does not see, and the calibration of
tools/outside-battery-check.

EVERY STREAM IS SEEDED AND REPRODUCIBLE. An earlier version drew the 20
secondary controls from os.urandom; those could not be regenerated, and a seed
that does not reproduce is not a pin. They are now produced by a SHA-256 counter
mode generator -- deterministic, and a completely different algorithm from
Mersenne Twister, so the calibration still does not rest on one RNG's quality.

1,000,000 one-bit samples per stream, one byte per sample (the layout
ea_non_iid reads for 1-bit symbols). ALL streams are globally unbiased, so the
most-common-value estimator cannot separate any of them from a fair coin --
every effect lives in the correlation.

CLEAN (25, must never fire the outside-battery check)
  mt00..mt04    Mersenne Twister
  sha00..sha19  SHA-256 counter mode

DEFECTS (must all fire)
  B_osc5000      P(1) = 0.5 + 0.10*sin(2*pi*i/5000). Slow bias drift, period
                 5000 samples = 60 Hz at 0.3 Mbit/s.
  C_osc500       same amplitude, period 500.
  D_lag5000      x_i = x_{i-5000} with prob 0.60 (P(agree) = 0.80). Strong, and
                 it creates exact repeated substrings, which is why LRS sees it.
  E_weaklag5000  x_i = x_{i-5000} with prob 0.04 (P(agree) = 0.52). A 40-sigma
                 autocorrelation with almost no exact repetition -- the stream
                 the battery's verdict misses entirely.

COMBINED-BLIND-SPOT CANDIDATES (OC-18)
  F_xor{p}       x_i = x_{i-1} XOR x_{i-2} with probability p, else fair coin.
                 In +/-1 terms x_i = x_{i-1}*x_{i-2}, so E[x_i x_{i-1}] =
                 E[x_{i-2}] = 0 and E[x_i x_{i-2}] = E[x_{i-1}] = 0: ZERO linear
                 correlation at every lag, by construction. The structure is
                 third-order. Tests whether a defect can sit below every
                 predictor's headroom AND below the outside check at once.

Usage: blindspot_streams.py <outdir> [name ...]     (no names = all)
"""
import random, math, hashlib, sys, os

N = 1000000
A = 0.10
LAG = 5000

def stats(b):
    agree = sum(1 for i in range(LAG, N) if b[i] == b[i-LAG]) / (N - LAG)
    se = 0.5 / math.sqrt(N - LAG)
    return sum(b)/N, agree, (agree-0.5)/se

def emit(outdir, name, samples):
    b = bytes(bytearray(samples))
    open(os.path.join(outdir, name + '.bin'), 'wb').write(b)
    p1, ag, sig = stats(b)
    print("%-16s P(1)=%.6f  P(agree@%d)=%.5f (%+7.1f sigma)  sha256=%s"
          % (name, p1, LAG, ag, sig, hashlib.sha256(b).hexdigest()))

# ---- generator 2: SHA-256 counter mode. Deterministic, not Mersenne Twister.
def sha_bits(seed, n):
    out = bytearray(n)
    i = 0
    ctr = 0
    key = ('sp90b-blindspot-%d' % seed).encode()
    while i < n:
        blk = hashlib.sha256(key + ctr.to_bytes(8, 'big')).digest()
        ctr += 1
        for byte in blk:
            for bit in range(8):
                if i >= n: break
                out[i] = (byte >> bit) & 1
                i += 1
            if i >= n: break
    return out

def build(name):
    if name.startswith('mt'):
        # These five seeds are the ones the published OC-16 baseline was
        # measured on, kept exactly so the baseline reproduces byte-for-byte.
        i = int(name[2:])
        r = random.Random(0xA if i == 0 else 0xC0 + i)
        return [r.getrandbits(1) for _ in range(N)]
    if name.startswith('sha'):
        return sha_bits(int(name[3:]), N)
    if name == 'B_osc5000' or name == 'C_osc500':
        T = 5000 if name == 'B_osc5000' else 500
        r = random.Random(0xB if T == 5000 else 0xC)
        return [1 if r.random() < 0.5 + A*math.sin(2*math.pi*i/T) else 0
                for i in range(N)]
    if name in ('D_lag5000', 'E_weaklag5000'):
        pcopy = 0.60 if name == 'D_lag5000' else 0.04
        r = random.Random(0xD if pcopy == 0.60 else 0xE)
        out = [r.getrandbits(1) for _ in range(LAG)]
        for i in range(LAG, N):
            out.append(out[i-LAG] if r.random() < pcopy else r.getrandbits(1))
        return out
    if name.startswith('F_xor'):
        # taps (1,2): PATHOLOGICAL, and instructive. a+b = 3 is itself a tap, so
        # the triple product x_{i-1}x_{i-2}x_{i-3} closes through the recurrence
        # and a strong LINEAR correlation appears at lag 3. This is why the
        # outside-battery check sees it (50+ sigma) -- it is the counterexample
        # that shows tap choice decides linear visibility.
        pi = int(name[5:])
        r = random.Random(0xF00 + pi)
        out = [r.getrandbits(1), r.getrandbits(1)]
        for i in range(2, N):
            out.append((out[i-1] ^ out[i-2]) if r.random() < pi/100.0
                       else r.getrandbits(1))
        return out
    if name.startswith('G_xor13_'):
        # taps (1,3), mixture p. a+b = 4 is NOT a tap, so the triple product
        # does not close and there is NO linear correlation at any lag --
        # measured max |z| ~4, indistinguishable from clean. The structure is
        # third-order. At p = 2% this is the COMBINED BLIND SPOT (OC-18):
        # MultiMMC drops 0.0266 (9x its 3sd) while H_original stays inside the
        # clean range and the outside-battery check stays silent.
        pi = int(name[8:])
        r = random.Random(0x400 + pi)
        out = [r.getrandbits(1) for _ in range(3)]
        for i in range(3, N):
            out.append((out[i-1] ^ out[i-3]) if r.random() < pi/100.0
                       else r.getrandbits(1))
        return out
    raise SystemExit('unknown stream %s' % name)

CLEAN  = ['mt%02d' % i for i in range(5)] + ['sha%02d' % i for i in range(20)]
DEFECT = ['B_osc5000', 'C_osc500', 'D_lag5000', 'E_weaklag5000']
FXOR   = ['F_xor30']                       # the taps-(1,2) counterexample
GXOR   = ['G_xor13_%02d' % p for p in (1, 2, 3, 5)]   # OC-18, keeper is 02
ALL    = CLEAN + DEFECT + FXOR + GXOR

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    outdir = sys.argv[1]
    # A PROBE MUST NOT BE ABLE TO CREATE THE THING IT ASKS ABOUT.
    #
    # This took sys.argv[1] as the output directory with no option handling, so
    # `blindspot_streams.py --help` -- the obvious way to discover the
    # interface -- created a directory literally named "--help" and wrote 34
    # streams, 33 MB, into it. A later `git add -A` committed all 34 (a9a269f),
    # and they reached the remote. Nothing referenced them; the corpus exists
    # precisely so these are REGENERATED from seeds and never stored.
    #
    # So: an outdir that looks like an option is refused, and the help flags
    # print the usage instead of becoming a directory. The refusal is the point
    # -- an option-shaped operand is a mistake every time here, because this
    # script has no options.
    if outdir in ('-h', '--help', '-help', '--usage'):
        raise SystemExit(__doc__)
    if outdir.startswith('-'):
        raise SystemExit("blindspot_streams.py: refusing to treat %r as an output "
                         "directory: it looks like an option, and this script has "
                         "none. Give a directory path." % outdir)
    names = sys.argv[2:] or ALL
    unknown = [n for n in names if n not in ALL]
    if unknown:
        raise SystemExit("blindspot_streams.py: unknown stream name(s): %s"
                         % ' '.join(unknown))
    os.makedirs(outdir, exist_ok=True)
    for n in names:
        emit(outdir, n, build(n))
