# For a byte sequence, report (spec semantics, 1-indexed step i) when each MultiMMC order d fills to 100,000
import sys
def fill_steps(S, D=16, MAXE=100000):
    L=len(S); seen=[set() for _ in range(D+1)]; ent=[0]*(D+1); full=[None]*(D+1); orphans=[]
    for i in range(3, L+1):
        for d in range(1, D+1):
            if d < i-1:
                key=(bytes(S[i-d-2:i-2]), S[i-2])
                if key in seen[d]: continue
                if ent[d] < MAXE:
                    seen[d].add(key); ent[d]+=1
                    if ent[d]==MAXE: full[d]=i
        if all(full[d] for d in range(2,D+1)): break
    return full
if __name__=='__main__':
    S=open(sys.argv[1],'rb').read()
    print(fill_steps(S))
