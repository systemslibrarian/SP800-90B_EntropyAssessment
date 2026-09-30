import sys
inp, out, idx = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None
d = open(inp, "rb").read()
if idx is not None: d = d[idx * 10**6:(idx + 1) * 10**6]
o = open(out, "rb").read()
exp = bytes(d[1000 * j + i] for i in range(1000) for j in range(1000))
print("MATCH" if o == exp else "MISMATCH", len(o))
