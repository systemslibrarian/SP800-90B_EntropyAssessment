# Independent reference for SP 800-90B 3.1.5.1.2 Output_Entropy and 3.1.5.2 non-vetted h_out
import mpmath as mp, subprocess, json, re, sys, os, itertools
SCR = "/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad"
TOOL = os.environ.get("TOOL", SCR + "/audit/rel/cpp/ea_conditioning")
W = SCR + "/audit/work/conditioning/grid"

def output_entropy(n_in, n_out, nw, h_in, clamp=True, nwmin=True):
    """Literal spec steps. h_in given as mp string/decimal. nwmin: apply nw=min(nw,n_in) (#65)."""
    mp.mp.prec = max(4 * max(n_in, n_out, nw, 64) + 256, 512)
    h_in = mp.mpf(h_in)
    if nwmin: nw = min(nw, n_in)
    P_high = mp.power(2, -h_in)
    P_low = (1 - P_high) / (mp.power(2, n_in) - 1)
    n = min(n_out, nw)
    t = mp.power(2, n_in - n)
    psi = t * P_low + P_high
    U = t + mp.sqrt(2 * n * t * mp.log(2))
    omega = U * P_low
    m = max(psi, omega)
    if clamp: m = min(m, mp.mpf(1))
    return -mp.log(m, 2), psi, omega

def run_tool(args):
    js = W + "/o.json"
    if os.path.exists(js): os.remove(js)
    p = subprocess.run([TOOL] + args + ["-o", js], capture_output=True, text=True, timeout=120)
    out = p.stdout
    d = {"rc": p.returncode, "out": out, "err": p.stderr}
    m = re.search(r"Output_Entropy\(\*\) = ([^;\n]+)", out); d["oe"] = m.group(1) if m else None
    m = re.search(r"h_out = ([^\n]+)", out); d["hout"] = m.group(1) if m else None
    try:
        d["json"] = json.load(open(js))
    except Exception as e:
        d["json"] = None
    return d

if __name__ == "__main__":
    cases = []
    for n_in in [1, 2, 3, 8, 16, 63, 64, 65, 128, 256, 512, 1024, 4096]:
        outs = sorted(set([1, max(1, n_in // 2), n_in, 2 * n_in, 64, 128, 256]))
        for n_out in outs:
            for nw in sorted(set([n_out, n_in, 1, 2 * max(n_in, n_out)])):
                for h in ["1e-30", "1e-300", "0.5", "1", str(n_out), str(n_out + 64), str(n_in), str(max(n_in - 1e-9, 0.0))]:
                    try:
                        if mp.mpf(h) <= 0 or mp.mpf(h) > n_in: continue
                    except Exception: continue
                    cases.append((n_in, n_out, nw, h))
    cases = sorted(set(cases))
    worst = mp.mpf(-1e9); nbad = 0; rows = []
    for (n_in, n_out, nw, h) in cases:
        d = run_tool(["-v", str(n_in), str(n_out), str(nw), h])
        ref, psi, om = output_entropy(n_in, n_out, nw, h)
        mp.mp.prec = 256
        if d["hout"] is None:
            print("NOOUT", n_in, n_out, nw, h, d["rc"], d["out"][-300:], d["err"][-300:]); nbad += 1; continue
        tool = mp.mpf(d["hout"])
        jh = d["json"]["testCases"][0]["h_out"] if d["json"] else None
        diff = tool - ref
        rel = diff / ref if ref != 0 else diff
        jdiff = (mp.mpf(jh) - ref) if jh is not None else None
        rows.append((n_in, n_out, nw, h, mp.nstr(ref, 25), d["hout"], mp.nstr(rel, 5), jh, mp.nstr(jdiff, 5) if jdiff is not None else None))
        if rel > worst: worst = rel
        if diff > 0 and rel > mp.mpf(2) ** -63:
            print("HIGH", n_in, n_out, nw, h, mp.nstr(ref, 30), d["hout"], mp.nstr(rel, 5)); nbad += 1
        if jdiff is not None and jdiff > 0:
            print("JSONHIGH", n_in, n_out, nw, h, mp.nstr(ref, 30), repr(jh), mp.nstr(jdiff, 5))
        if rel < -mp.mpf(2) ** -60:
            print("LOW", n_in, n_out, nw, h, mp.nstr(ref, 30), d["hout"], mp.nstr(rel, 5))
    print("cases", len(cases), "bad", nbad, "max rel (tool-ref)/ref", mp.nstr(worst, 5))
    with open(W + "/grid.tsv", "w") as f:
        f.write("n_in\tn_out\tnw\th_in\tref\ttool_text\trel_diff\tjson_h_out\tjson_minus_ref\n")
        for r in rows: f.write("\t".join(map(str, r)) + "\n")
