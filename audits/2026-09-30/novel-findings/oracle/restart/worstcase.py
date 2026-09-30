import sys; sys.argv=['x']
exec(open('cutoff_ref.py').read().split("if __name__")[0])
import math
a = 1 - math.exp(math.log(0.99)/2000)
# (1) spec-literal cutoff applied to the tool's own worst-case model: per-experiment and overall false-fail rates
for H, U in [(1.0,570),(2.0,312),(4.0,99),(7.0,23),(8.0,15)]:
    p = 2.0**-H; pr = model_probs(p)
    t = 1.0 - p_max_le(U, pr)
    print(f"H_I={H}: spec U={U}: P(row/col max > U | ideal source at H_I) = {t:.4g}; overall false-fail over 2000 = {1-(1-t)**2000:.4g} (target 0.01)")
# (2) premise check: inverted near-uniform tail >= other distributions with the same max probability
for probs in ([0.25]*4, [0.25,0.25,0.25,0.125,0.125], [0.25,0.25,0.2,0.2,0.1], [0.25]+[0.75/8]*8):
    print("probs", [round(x,4) for x in probs], "P(max>316) =", f"{1-p_max_le(316, probs):.4g}")
