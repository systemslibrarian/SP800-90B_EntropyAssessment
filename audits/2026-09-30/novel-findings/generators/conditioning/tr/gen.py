import random, sys
def mk(name, seed, alph, n=10**6, extra=b""):
    r = random.Random(seed); open(name, "wb").write(bytes(r.randrange(alph) for _ in range(n)) + extra)
mk("r256.bin", 1, 256); mk("r2.bin", 2, 2); mk("r16.bin", 3, 16)
mk("r256x3.bin", 4, 256, 3 * 10**6)
mk("short.bin", 5, 256, 10**6 - 1); mk("long.bin", 6, 256, 10**6 + 1)
open("zero.bin", "wb").write(bytes(10**6))
open("const1.bin", "wb").write(bytes([1]) * 10**6)
