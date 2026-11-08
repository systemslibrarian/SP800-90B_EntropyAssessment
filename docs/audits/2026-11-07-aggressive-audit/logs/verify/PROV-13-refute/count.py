import sys, collections
b = open(sys.argv[1], 'rb').read(); c = collections.Counter(b)
print("len", len(b), "distinct", len(c), "counts", {k: c[k] for k in sorted(c)})
