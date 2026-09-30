#!/bin/bash
# literal + bitstring paths for widths 2..8 (C++ literal reference vs tool headers)
cd "$(dirname "$0")"
mkdir -p data/w
for b in 2 3 4 5 6 7 8; do
  python3 -c "
import random; r=random.Random($b*7)
k=1<<$b; S=[]; s=0
for i in range(40000):
    s = (s + r.choice((1,1,2,3))) % k if r.random()<0.6 else r.randrange(k)
    S.append(s)
open('data/w/w$b.bin','wb').write(bytes(S))"
  python3 cmpc.py data/w/w$b.bin $b lit
  python3 cmpc.py data/w/w$b.bin $b bit
done
