#!/usr/bin/env python3
# analyze_gpu_pattern.py -- mine the GPU pattern-mining JSON for structure.
# Reads results/gpu_pattern.json produced by gpu_ntile.exe mine.
import json, sys, math

P = sys.argv[1] if len(sys.argv) > 1 else "results/gpu_pattern.json"
with open(P) as f:
    d = json.load(f)

hist = d["hist"]                 # count per bad-bin
sh   = d["sum_heat"]             # sum heatmap-alignment per bin
sx   = d["sum_x"]                # sum (X) conflicts per bin
ss   = d["sum_s"]                # sum (S) conflicts per bin
total = d.get("total_configs", sum(hist))
best  = d.get("best_bad")
print(f"mode={d['mode']} m={d['m']} threads={d['threads']} seconds={d['seconds']:.1f}")
print(f"total_configs={total}  best_bad_seen={best}")

# global (X)/(S) totals over ALL sampled configs
TX = sum(sx[b] for b in range(len(hist)))
TS = sum(ss[b] for b in range(len(hist)))
print(f"overall (X)/(S) ratio across all configs: X={TX:.0f}  S={TS:.0f}  -> S/(X+S)={TS/(TX+TS+1e-9):.4f}")

# --- how does (X)/(S) split vary with bad? ---
print("\n bad-bin | count | avg(x) | avg(s) | s/(x+s) | avg_heat")
rows = []
for b in range(len(hist)):
    if hist[b] == 0:
        continue
    ax = sx[b]/hist[b]; as_ = ss[b]/hist[b]
    ah = sh[b]/hist[b]
    ratio = as_/(ax+as_+1e-9)
    rows.append((b, hist[b], ax, as_, ratio, ah))
    print(f"  {b:4d}  | {hist[b]:8d} | {ax:6.2f} | {as_:6.2f} | {ratio:7.4f} | {ah:7.4f}")

# --- heatmap alignment vs bad: does low-bad correlate with high heat? ---
print("\nHeatmap-alignment by bad regime:")
def regime(maxb):
    cnt=0; hs=0.0
    for b in range(min(maxb+1, len(hist))):
        if hist[b]:
            cnt+=hist[b]; hs+=sh[b]
    return (hs/cnt if cnt else 0.0, cnt)
for lbl,mb in [("bad<50",49),("bad<100",99),("bad<200",199),("bad<400",399),("all",len(hist)-1)]:
    ah,cnt = regime(mb)
    print(f"  {lbl:8s}: avg_heat={ah:.4f}  (n={cnt})")

# --- fit: is log(count) linear in bad? (exponential decay of bad?) ---
print("\nBad-distribution decay (log-linear check):")
pts = [(b, hist[b]) for b in range(len(hist)) if hist[b] > 0]
# restrict to a smooth central window to estimate slope
xs=[]; ys=[]
for b,c in pts:
    if 1 <= b <= 400:
        xs.append(b); ys.append(math.log(c))
if len(xs) >= 2:
    n=len(xs); sx_=sum(xs); sy=sum(ys); sxx=sum(x*x for x in xs); sxy=sum(x*y for x,y in zip(xs,ys))
    slope=(n*sxy - sx_*sy)/(n*sxx - sx_*sx_)
    print(f"  slope(log count vs bad) over bad in [1,400] = {slope:.5f}  (more negative => bad decays faster)")
    print(f"  => each +1 bad multiplies count by exp({slope:.4f}) = {math.exp(slope):.4f}")
