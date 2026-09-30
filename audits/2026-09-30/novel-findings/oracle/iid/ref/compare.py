import sys, subprocess, random, re, math, os
sys.path.insert(0, os.path.dirname(__file__))
import ref90b as R
BIN=sys.argv[1]; outdir=sys.argv[2]
os.makedirs(outdir, exist_ok=True)
r=random.Random(90)
cases=[]
def add(name, data): cases.append((name, bytes(data)))
for L in (300, 1001, 4007):
    add(f'r8_{L}', [r.randrange(256) for _ in range(L)])
    add(f'r3_{L}', [r.choice([7,50,51]) for _ in range(L)])
    add(f'r4_{L}', [r.randrange(16) for _ in range(L)])
    add(f'bin_{L}', [r.randrange(2) for _ in range(L)])
    add(f'binb_{L}', [1 if r.random()<0.2 else 0 for _ in range(L)])
    add(f'two_{L}', [r.choice([3,200]) for _ in range(L)])
    add(f'geo_{L}', [min(255,int(r.expovariate(0.3))) for _ in range(L)])
    add(f'per_{L}', [(i*13)%29 for i in range(L)])
    add(f'drift_{L}', [min(255,(i*256)//L + r.randrange(8)) for i in range(L)])
    add(f'binper_{L}', [(i//3)%2 for i in range(L)])
mism=0
for name,data in cases:
    fn=f'{outdir}/{name}.bin'; open(fn,'wb').write(data)
    out=subprocess.run(['timeout','300',BIN,'-vvv',fn],capture_output=True,text=True).stdout
    if 'Assertion' in out or 'Unpermuted' not in out:
        err=subprocess.run(['timeout','300',BIN,'-vvv',fn],capture_output=True,text=True).stderr.strip().splitlines()
        print(name,'ABORT',err[-1] if err else out[-200:]); continue
    tool={m.group(1):float(m.group(2)) for m in re.finditer(r'Unpermuted result (\S+) = (\S+)',out)}
    raw=list(data); binary=len(set(raw))==2
    ref=R.stats(raw,binary)
    for k,v in ref.items():
        tv=tool.get(k)
        ok = (tv is not None) and ((math.isnan(v) and math.isnan(tv)) or abs(tv-v)<=1e-9*max(1,abs(v)))
        if not ok:
            mism+=1; print(f'MISMATCH {name} {k}: tool={tv} ref={v}')
    g=lambda pat: [float(x) for x in re.findall(pat,out)]
    Ti=g(r'Chi square independence: T = (\S+)'); dfi=g(r'Chi square independence: df = (\S+)'); pi=g(r'Chi square independence: P-value = (\S+)')
    Tg=g(r'Chi square goodness of fit: T = (\S+)'); dfg=g(r'Chi square goodness of fit: df = (\S+)'); pg=g(r'Chi square goodness of fit: P-value = (\S+)')
    if binary:
        b=[0 if x==min(raw) else 1 for x in raw]
        rT,rdf,m=R.indep_binary(b); gT,gdf=R.gof_binary(b)
    else:
        rT,rdf=R.indep_nonbinary(raw); m=None; gT,gdf=R.gof_nonbinary(raw)
    note=''
    if rT is None:
        note=f'binary m=1: spec says FAIL; tool T={Ti} df={dfi} p={pi}'
    else:
        if abs(Ti[0]-rT)>1e-7*max(1,rT) or dfi[0]!=rdf: mism+=1; print(f'MISMATCH {name} indep: tool T={Ti} df={dfi} ref T={rT} df={rdf}')
        if rdf>0:
            rp=R.pchi(rT,rdf)
            if abs(pi[0]-rp)>1e-9: mism+=1; print(f'MISMATCH {name} indep p: tool={pi[0]} ref={rp}')
    if abs(Tg[0]-gT)>1e-7*max(1,gT) or dfg[0]!=gdf: mism+=1; print(f'MISMATCH {name} gof: tool T={Tg} df={dfg} ref T={gT} df={gdf}')
    if gdf>0:
        rp=R.pchi(gT,gdf)
        if abs(pg[0]-rp)>1e-9: mism+=1; print(f'MISMATCH {name} gof p: tool={pg[0]} ref={rp}')
    pc=g(r'Longest Repeated Substring results: P_col = (\S+)'); Wt=g(r'Longest Repeated Substring results: W = (\S+)'); pr=g(r'Pr\(X >= 1\) = (\S+)')
    rpc,rW,rpr=R.lrs(raw)
    if not pc or abs(pc[0]-rpc)>1e-15 or Wt[0]!=rW or abs(pr[0]-rpr)>1e-9*max(1e-300,rpr): mism+=1; print(f'MISMATCH {name} lrs: tool {pc} {Wt} {pr} ref {rpc} {rW} {rpr}')
    verdict=[l for l in out.splitlines() if l.endswith('Passed') or l.endswith('Failed')]
    print(name, 'indep_df', dfi, 'm' if binary else '', m, '|', '; '.join(verdict), '|', note)
print('TOTAL MISMATCHES', mism)
