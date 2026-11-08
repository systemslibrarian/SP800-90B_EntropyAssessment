# Independent generator (my own, not the reproducer's): symbols placed at seeded shuffled positions.
import random, sys
out, L, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); counts = [int(x) for x in sys.argv[4].split(',')]
assert sum(counts) == L
r = random.Random(seed); pos = list(range(L)); r.shuffle(pos); data = bytearray(L); i = 0
for sym, c in enumerate(counts):
    for _ in range(c): data[pos[i]] = sym; i += 1
open(out, 'wb').write(bytes(data))
