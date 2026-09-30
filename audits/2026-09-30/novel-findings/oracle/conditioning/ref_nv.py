import sys, random
sys.path.insert(0, "/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/work/conditioning")
from ref import output_entropy, run_tool
import mpmath as mp
r = random.Random(11); bad = 0; n = 0; worst = -1
cases = [(512,256,256,"300","0.5"),(512,256,256,"300","1"),(512,256,256,"300","0.999"),(512,256,256,"300","0.9990001"),(512,256,256,"260","1"),
         (4096,64,64,"64","1"),(64,64,64,"64","1"),(8,8,8,"8","1"),(8,8,8,"8","0.1"),(1,1,1,"1","1"),(16,32,8,"12","0.75")]
for _ in range(120):
    n_in = r.choice([8,16,64,128,256,512,1024,2048]); n_out = r.choice([1,8,32,64,128,256,512,1024]); nw = r.choice([1,8,64,128,256,512,4096])
    h = repr(r.uniform(1e-3, n_in)); hp = repr(r.uniform(1e-6, 1.0))
    cases.append((n_in, n_out, nw, h, hp))
for (n_in, n_out, nw, h, hp) in cases:
    d = run_tool(["-n", str(n_in), str(n_out), str(nw), h, hp])
    oe, _, _ = output_entropy(n_in, n_out, nw, h)
    mp.mp.prec = 300
    ref = min(oe, mp.mpf("0.999") * n_out, mp.mpf(hp) * n_out)
    if d["hout"] is None: print("NOOUT", n_in, n_out, nw, h, hp, d["out"][-200:]); bad += 1; continue
    tool = mp.mpf(d["hout"]); rel = (tool - ref) / ref if ref else tool - ref
    n += 1; worst = max(worst, rel)
    if rel > mp.mpf(2) ** -63: print("HIGH", n_in, n_out, nw, h, hp, mp.nstr(ref, 25), d["hout"], mp.nstr(rel, 4)); bad += 1
    jh = d["json"]["testCases"][0]["h_out"]
    if mp.mpf(jh) > ref * (1 + mp.mpf(2) ** -63): print("JSONHIGH", n_in, n_out, nw, h, hp, mp.nstr(ref, 25), jh)
print("non-vetted cases", n, "flagged", bad, "max rel", mp.nstr(worst, 4))
