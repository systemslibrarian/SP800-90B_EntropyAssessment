import random, math
L=10**6
r=random.Random(20260930)
def w(fn, data): open(fn,'wb').write(bytes(data))
w('counter8.bin', [i%256 for i in range(L)])
w('drift8.bin', [min(255,max(0,int(128+100*math.sin(2*math.pi*i/L))+r.randrange(-20,21))) for i in range(L)])
# binary Markov: P(stay)=0.6
b=[0]; 
for i in range(L-1): b.append(b[-1] if r.random()<0.6 else 1-b[-1])
w('markov1.bin', b)
# 8-bit random walk with small steps
x=128; d=[]
for i in range(L): x=(x+r.randrange(-3,4))%256; d.append(x)
w('walk8.bin', d)
# sorted blocks of 1000 random bytes
d=[]
for k in range(L//1000): blk=sorted(r.randrange(256) for _ in range(1000)); d+=blk
w('sortedblk8.bin', d)
# weak lag-1 dependence: s_i = s_{i-1} with prob 0.01 else fresh uniform
d=[r.randrange(256)]
for i in range(L-1): d.append(d[-1] if r.random()<0.01 else r.randrange(256))
w('sticky8.bin', d)
# 4-bit data where every 2nd sample is the complement of the previous one's low bit pattern (pairwise dependence)
d=[]
for i in range(L//2): a=r.randrange(16); d+=[a, a^0xF if r.random()<0.05 else r.randrange(16)]
w('pair4.bin', d)
