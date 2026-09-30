import sys, hashlib
inp, out = sys.argv[1], sys.argv[2]
d = open(inp, "rb").read(); o = open(out, "rb").read()
for b in range(len(d) // 10**6):
    blk = d[b * 10**6:(b + 1) * 10**6]
    if o == bytes(blk[1000 * j + i] for i in range(1000) for j in range(1000)): print(out, "== transpose of block", b); break
else: print(out, "matches no full block; size", len(o))
