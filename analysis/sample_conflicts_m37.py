"""Direction #4 probe (vectorized): orbit-averaged / first-moment test for m=37.

Sample random 2-factors (stub-matching = uniform over all 2-factor space) and
measure the distribution of #(X) collinear triples fully selected.  Confirms
whether a non-trivial fraction of random 2-factors is already conflict-free
(orbit averaging suggests existence) vs the conflict hypergraph is dense in
expectation (plain LLL dies; need nibble threading).

Vectorized via reverse index + bincount (no scipy): per sample we only touch
the ~m selected cells' lines, ~1ms/sample.
"""
import os, sys, time, json, random, math
import numpy as np
sys.path.insert(0, ".")
from solve_m37_r9b import generate_constraints

m = 37
NSAMP = 4000
t0 = time.time()
reps, line_cons, twofactor = generate_constraints(m, True)
nvar = len(reps)
print(f"[gen] {nvar} cells, {len(line_cons)} lines ({time.time()-t0:.1f}s)",
      flush=True)

# lines with >=3 cells only
lines = [np.array(list(d.keys()), dtype=np.int32)
         for d in line_cons if len(d) >= 3]
nlines = len(lines)
print(f"[lines] {nlines} lines with >=3 cells "
      f"(triple-events={sum(math.comb(len(L),3) for L in lines):,})", flush=True)

# reverse index: cell -> list of line indices
t1 = time.time()
cell_to_lines = [[] for _ in range(nvar)]
for li, L in enumerate(lines):
    for c in L:
        cell_to_lines[c].append(li)
cell_to_lines = [np.array(x, dtype=np.int32) for x in cell_to_lines]
print(f"[revidx] built in {time.time()-t1:.1f}s", flush=True)

rng = random.Random(20260714)
conf = np.empty(NSAMP, dtype=np.int64)
zero = 0
for s in range(NSAMP):
    k = rng.randint(0, (m - 1) // 2)
    verts = list(range(m)); rng.shuffle(verts)
    o = [1] * m
    for i in verts[:k]:
        o[i] = 2
    for i in verts[k:2 * k]:
        o[i] = 0
    out_stubs = []; in_stubs = []
    for i in range(m):
        out_stubs += [i] * o[i]
        in_stubs += [i] * (2 - o[i])
    rng.shuffle(in_stubs)
    sel = np.zeros(nvar, dtype=np.int8)
    for a, b in zip(out_stubs, in_stubs):
        sel[a * m + b] = 1
    chosen = np.nonzero(sel)[0]
    all_lines = np.concatenate([cell_to_lines[c] for c in chosen])
    cnt = np.bincount(all_lines, minlength=nlines)
    c = int(sum(math.comb(int(x), 3) for x in cnt[cnt >= 3]))
    conf[s] = c
    if c == 0:
        zero += 1
    if (s + 1) % 500 == 0:
        print(f"[samp] {s+1}/{NSAMP} zero={zero} "
              f"mean={conf[:s+1].mean():.1f}", flush=True)

mean = float(conf.mean())
print(f"[result] NSAMP={NSAMP} mean_conflicts={mean:.2f} "
      f"min={int(conf.min())} max={int(conf.max())} "
      f"fraction_zero={zero/NSAMP:.6f}", flush=True)
if zero > 0:
    print(f"[result] {zero} random 2-factors conflict-free "
          f"-- strong evidence m=37 solvable by construction.", flush=True)
else:
    print(f"[result] 0/{NSAMP} conflict-free -- first moment ({mean:.0f}) "
          f"too high; need nibble/constructive threading (LLL dead).",
          flush=True)
json.dump({"m": m, "nsamp": NSAMP, "mean_conflicts": mean,
           "min": int(conf.min()), "max": int(conf.max()),
           "fraction_zero": zero / NSAMP},
          open("results/sample_conflicts_m37.json", "w"), indent=1)
print("[done] wrote results/sample_conflicts_m37.json", flush=True)
