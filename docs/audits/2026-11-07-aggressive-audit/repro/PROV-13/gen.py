# Deterministic generator shared by run.sh and control.sh (same algorithm as logs/analysis-iid-chisq-probe.py place()).
import random, sys
def place(L, counts, seed):
    r = random.Random(seed); data = bytearray(L); pos = list(range(L)); r.shuffle(pos); i = 0
    for sym, c in enumerate(counts):
        for _ in range(c):
            data[pos[i]] = sym; i += 1
    assert i == L
    return bytes(data)
out, L, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); counts = [int(x) for x in sys.argv[4].split(',')]
open(out, 'wb').write(place(L, counts, seed)); print("ok", L, counts, seed)
