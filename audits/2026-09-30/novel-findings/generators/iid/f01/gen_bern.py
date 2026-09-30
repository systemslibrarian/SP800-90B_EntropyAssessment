# IID Bernoulli(p) bits, one bit per byte, 1,000,000 samples (seeded, deterministic)
import random, sys
p=float(sys.argv[1]); seed=int(sys.argv[2]); out=sys.argv[3]
r=random.Random(seed)
open(out,'wb').write(bytes(1 if r.random()<p else 0 for _ in range(10**6)))
