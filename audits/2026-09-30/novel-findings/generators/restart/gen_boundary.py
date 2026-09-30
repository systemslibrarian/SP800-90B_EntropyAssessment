# uniform 8-bit restart matrix, then force row 17 to contain value 0xA5 exactly X times (other entries of that row
# redrawn from the 255 other values), so X_R = X exactly (other rows/cols have max counts ~14-16).
import random, sys
from collections import Counter
X = int(sys.argv[1]); out = sys.argv[2]
r = random.Random(1234)
M = [[r.randrange(256) for j in range(1000)] for i in range(1000)]
row = [0xA5]*X + [r.choice([v for v in range(256) if v != 0xA5]) for _ in range(1000-X)]
r.shuffle(row); M[17] = row
d = [M[i][j] for i in range(1000) for j in range(1000)]
xr = max(max(Counter(d[i*1000:(i+1)*1000]).values()) for i in range(1000))
xc = max(max(Counter(d[j::1000]).values()) for j in range(1000))
open(out,'wb').write(bytes(d)); print(out, "X_R", xr, "X_C", xc)
