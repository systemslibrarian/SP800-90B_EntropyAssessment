import random, sys
def w(name, data):
    assert len(data)==10**6, (name, len(data))
    open(name,'wb').write(bytes(data))
R=1000;C=1000
kind=sys.argv[1]
if kind=='uni8':      # iid uniform bytes
    r=random.Random(1); w('uni8.bin',[r.randrange(256) for _ in range(R*C)])
elif kind=='uni1':
    r=random.Random(2); w('uni1.bin',[r.randrange(2) for _ in range(R*C)])
elif kind=='colconst8':  # every restart emits the same 1000-sample sequence -> columns constant
    r=random.Random(3); s=[r.randrange(256) for _ in range(C)]; w('colconst8.bin', s*R)
elif kind=='rowconst8':  # each restart emits a constant (restart-specific) value -> rows constant
    r=random.Random(4); v=[r.randrange(256) for _ in range(R)]; w('rowconst8.bin',[v[i] for i in range(R) for j in range(C)])
elif kind=='shift8':   # M[i][j] = S[i+j]: rows and columns are windows of one sequence
    r=random.Random(5); S=[r.randrange(256) for _ in range(R+C)]; w('shift8.bin',[S[i+j] for i in range(R) for j in range(C)])
elif kind=='shift1':
    r=random.Random(6); S=[r.randrange(2) for _ in range(R+C)]; w('shift1.bin',[S[i+j] for i in range(R) for j in range(C)])
elif kind=='colconst1':
    r=random.Random(7); s=[r.randrange(2) for _ in range(C)]; w('colconst1.bin', s*R)
if kind=='altcol1':   # M[i][j] = ((i+j)&1) ^ r_j : balanced rows/cols (passes sanity), columns alternate -> predictable
    r=random.Random(8); rj=[r.randrange(2) for _ in range(C)]
    w('altcol1.bin',[((i+j)&1)^rj[j] for i in range(R) for j in range(C)])
