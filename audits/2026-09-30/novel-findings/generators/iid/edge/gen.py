import random, sys
r=random.Random(7)
Ls=list(range(0,41))+[47,48,63,64,100,255,256,257,300,1000]
pats={}
for L in Ls:
    pats[('rand8',L)]=bytes(r.randrange(256) for _ in range(L))
    pats[('bin',L)]=bytes(r.randrange(2) for _ in range(L))
    pats[('const',L)]=bytes([5]*L)
    pats[('two',L)]=bytes(r.choice([3,200]) for _ in range(L))
    pats[('distinct',L)]=bytes((i*37)%256 for i in range(L))
for (p,L),b in pats.items():
    open(f'{p}_{L}.bin','wb').write(b)
