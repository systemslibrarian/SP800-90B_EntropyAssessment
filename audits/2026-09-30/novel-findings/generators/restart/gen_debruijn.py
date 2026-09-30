# Random-order de Bruijn sequence B(k,3) via Hierholzer on the order-2 de Bruijn graph.
# Linear length k^3 (k=100 -> exactly 1,000,000). Every 3-tuple occurs at most once,
# every 2-tuple ~k times -> LRS: u = 3, v = 2  => "v < u, cannot be computed" (SP 800-90B 6.3.6 step 2).
import random, sys
k = int(sys.argv[1]); seed = int(sys.argv[2]); out = sys.argv[3]
r = random.Random(seed)
nxt = {}
for a in range(k):
    for b in range(k):
        l = list(range(k)); r.shuffle(l); nxt[(a,b)] = l
start = (0,0)
stack = [start]; circuit = []
while stack:
    v = stack[-1]
    if nxt[v]:
        c = nxt[v].pop()
        stack.append((v[1], c))
    else:
        circuit.append(stack.pop())
circuit.reverse()
# circuit is a list of nodes (k^3 + 1 nodes); emit the second symbol of each node after the first
seq = [n[1] for n in circuit[1:]]
assert len(seq) == k**3, len(seq)
# sanity: 3-tuples in the linear sequence are unique
t3 = set()
for i in range(len(seq)-2):
    t = (seq[i], seq[i+1], seq[i+2]); assert t not in t3; t3.add(t)
open(out, 'wb').write(bytes(seq))
print("ok", len(seq), "max symbol", max(seq))
