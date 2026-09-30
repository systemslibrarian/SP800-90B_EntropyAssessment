# Independent literal implementation of SP 800-90B Section 5 statistics (from the spec text),
# used to cross-check ea_iid's unpermuted statistics, chi-square and LRS outputs.
import bz2, math
from fractions import Fraction
import mpmath

def conv1(bits):
    out=[]
    for i in range(0,len(bits),8):
        out.append(sum(bits[i:i+8]))
    return out
def conv2(bits):
    out=[]
    for i in range(0,len(bits),8):
        blk=list(bits[i:i+8])+[0]*(8-len(bits[i:i+8]))
        v=0
        for b in blk: v=(v<<1)|b
        out.append(v)
    return out
def excursion(s):
    L=len(s); X=Fraction(sum(s),L); run=0; best=Fraction(0)
    for i,x in enumerate(s,1):
        run+=x; d=abs(run-i*X)
        if d>best: best=d
    return float(best)
def sprime_dir(s): return [-1 if s[i]>s[i+1] else 1 for i in range(len(s)-1)]
def runs(sp):
    if not sp: return 0
    return 1+sum(1 for i in range(1,len(sp)) if sp[i]!=sp[i-1])
def longest(sp):
    if not sp: return 0
    b=c=1
    for i in range(1,len(sp)):
        c = c+1 if sp[i]==sp[i-1] else 1
        b=max(b,c)
    return b
def median(s):
    v=sorted(s); L=len(v)
    return v[L//2] if L%2 else Fraction(v[L//2-1]+v[L//2],2)
def collisions(s):
    C=[]; i=0; L=len(s)
    while i < L-1:
        seen=set(); j=None
        for t in range(i,L):
            if s[t] in seen: j=t-i+1; break
            seen.add(s[t])
        if j is None: break
        C.append(j); i+=j
    return C
def periodicity(s,p): return sum(1 for i in range(len(s)-p) if s[i]==s[i+p])
def covariance(s,p): return sum(s[i]*s[i+p] for i in range(len(s)-p))
def compression(s): return len(bz2.compress(' '.join(str(x) for x in s).encode(),5))
def stats(raw, binary):
    # raw: list of raw sample values; binary: k==2 (values mapped to 0/1 by order)
    if binary:
        lo=min(raw); b=[0 if x==lo else 1 for x in raw]
        c1=conv1(b); c2=conv2(b)
        dirs=c1; med_s=b; med=Fraction(1,2); col=c2; per=c1; cov=c1
    else:
        dirs=raw; med_s=raw; med=median(raw); col=raw; per=raw; cov=raw
    sp=sprime_dir(dirs)
    sm=[-1 if x<med else 1 for x in med_s]
    C=collisions(col)
    out={'excursion':excursion(raw),'numDirectionalRuns':runs(sp),'lenDirectionalRuns':longest(sp),
         'numIncreasesDecreases':max(sp.count(-1),sp.count(1)),'numRunsMedian':runs(sm),'lenRunsMedian':longest(sm),
         'avgCollision':(sum(C)/len(C) if C else float('nan')),'maxCollision':(max(C) if C else 0)}
    for p in (1,2,8,16,32): out[f'periodicity({p})']=periodicity(per,p)
    for p in (1,2,8,16,32): out[f'covariance({p})']=covariance(cov,p)
    out['compression']=compression(raw)
    return out

def pchi(T,df):
    return float(mpmath.gammainc(mpmath.mpf(df)/2, mpmath.mpf(T)/2, mpmath.inf, regularized=True))

def indep_nonbinary(s):
    # 5.2.1 with the tool's documented floor(L/2) deviation (#62) and tuple tie order (#63)
    L=len(s); syms=sorted(set(s)); k=len(syms); idx={v:i for i,v in enumerate(syms)}
    t=[idx[x] for x in s]
    cnt=[t.count(i) for i in range(k)]
    p=[c/L for c in cnt]
    e=[(p[i]*p[j]*(L//2), i*k+j) for i in range(k) for j in range(k)]
    e.sort()
    bins=[]; binof={}; cur=0.0; members=[]
    for ev,tup in e:
        if cur>=5.0:
            bins.append(cur); 
            for m in members: binof[m]=len(bins)-1
            cur=0.0; members=[]
        members.append(tup); cur+=ev
    if bins and cur<5.0:
        bins[-1]+=cur
        for m in members: binof[m]=len(bins)-1
    else:
        bins.append(cur)
        for m in members: binof[m]=len(bins)-1
    o=[0]*len(bins)
    for j in range(0,L-1,2): o[binof[t[j]*k+t[j+1]]]+=1
    T=sum((o[i]-bins[i])**2/bins[i] for i in range(len(bins)))
    return T, len(bins)-k
def gof_nonbinary(s):
    L=len(s); syms=sorted(set(s)); k=len(syms); idx={v:i for i,v in enumerate(syms)}
    t=[idx[x] for x in s]; cnt=[t.count(i) for i in range(k)]
    e=sorted([(cnt[i]/L*(L//10), i) for i in range(k)])
    bins=[]; binof={}; cur=0.0; members=[]
    for ev,sym in e:
        if cur>=5.0:
            bins.append(cur)
            for m in members: binof[m]=len(bins)-1
            cur=0.0; members=[]
        members.append(sym); cur+=ev
    if bins and cur<5.0:
        bins[-1]+=cur
        for m in members: binof[m]=len(bins)-1
    else:
        bins.append(cur)
        for m in members: binof[m]=len(bins)-1
    B=L//10; T=0.0
    for d in range(10):
        o=[0]*len(bins)
        for x in t[d*B:(d+1)*B]: o[binof[x]]+=1
        T+=sum((o[i]-bins[i])**2/bins[i] for i in range(len(bins)))
    return T, 9*(len(bins)-1)
def indep_binary(b):
    L=len(b); p1=sum(b)/L; p0=1-p1; mp=min(p0,p1)
    m=11
    while m>1 and not (mp**m*(L//m)>=5): m-=1
    if m==1: return None,None,'FAIL(m=1)'
    nb=L//m; occ=[0]*(1<<m)
    for i in range(nb):
        v=0
        for j in range(m): v=(v<<1)|b[i*m+j]
        occ[v]+=1
    T=0.0
    for tpl in range(1<<m):
        w=bin(tpl).count('1'); e=p1**w*p0**(m-w)*nb
        T+=(occ[tpl]-e)**2/e
    return T,2**m-2,m
def gof_binary(b):
    L=len(b); p=sum(b)/L; B=L//10; e0=(1-p)*B; e1=p*B; T=0.0
    for d in range(10):
        o1=sum(b[d*B:(d+1)*B]); o0=B-o1
        T+=(o0-e0)**2/e0+(o1-e1)**2/e1
    return T,9
def lrs(s):
    L=len(s); syms=set(s)
    pcol=mpmath.fsum([ (mpmath.mpf(s.count(v))/L)**2 for v in syms])
    # longest repeated substring (quadratic-ish, small inputs only)
    W=0
    sufs=sorted(range(L), key=lambda i: s[i:])
    for a,b2 in zip(sufs,sufs[1:]):
        x,y=s[a:],s[b2:]; n=0
        while n<len(x) and n<len(y) and x[n]==y[n]: n+=1
        W=max(W,n)
    N=(L-W+1)*(L-W)//2
    pr=1-(1-pcol**W)**N
    return float(pcol), W, float(pr)
