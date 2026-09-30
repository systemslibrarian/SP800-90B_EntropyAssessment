import sys,re,glob,os
SCR='/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad'
ref_dir=SCR+'/audit/rel/cpp/selftest'
W=SCR+'/audit/work/num'
num=re.compile(r'^(.*?)(?:=|:)\s*(-?[0-9.]+(?:e[-+]?[0-9]+)?|-?inf|-?nan)\s*$')
def parse(fn):
    d={}
    for line in open(fn,errors='replace'):
        line=line.rstrip()
        m=num.match(line)
        if m:
            k=m.group(1).strip()
            # disambiguate repeated keys
            kk=k; i=1
            while kk in d: i+=1; kk=f"{k}#{i}"
            try: d[kk]=float(m.group(2))
            except: pass
    return d
builds=sys.argv[1:]
for b in builds:
    worst=[]
    for f in sorted(glob.glob(f"{W}/runs/{b}_*.res")):
        base=os.path.basename(f)[len(b)+1:]
        ref=f"{ref_dir}/{base}"
        if not os.path.exists(ref): continue
        A=parse(ref); B=parse(f)
        for k in A:
            if k not in B: continue
            a,bv=A[k],B[k]
            if a==bv: continue
            den=max(abs(a),abs(bv),1e-300)
            rel=abs(a-bv)/den
            worst.append((rel,base,k,a,bv))
        missing=[k for k in A if k not in B]
        if missing: print(b,base,'MISSING keys',missing[:3])
    worst.sort(reverse=True)
    print(f"== {b}: {len(worst)} differing values; top:")
    for w in worst[:12]: print("  %.3g  %s | %s | ref=%.17g got=%.17g"%w)
