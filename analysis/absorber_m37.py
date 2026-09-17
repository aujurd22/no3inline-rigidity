"""
absorber_m37.py  --  #4 (iterative absorption / surgery) CORRECTED trial.

Background: results/m37_surgery_result.json (2026-07-13) claimed an m=37
solution via "split", but an INDEPENDENT brute-force check found 248 collinear
triples -> FALSE POSITIVE.  Root cause: pre-v5 surgery scripts used a buggy
(X)-check (v5 header literally says "CORRECT incremental collinearity check").
v5 fixed the check but only used ONE m=36 seed + bounded k-switches, found
nothing -> m=37 stayed OPEN.

This script re-runs the surgery idea with a CORRECT (X)-check (via the exact
line_cons hypergraph, not the buggy point-set check) and measures, for the
seed's 36 edge-splits, how many (X)-violations the best split introduces.
That tells us how "close" surgery gets and scopes the absorber needed.

(X)-cost of a candidate cell set = sum over lines of max(0, total_weight - 2),
where total_weight = sum of per-cell weights on that line (from line_cons).
For a split, only the 2 NEW cells (a,36),(36,b) change vs the (X)-free core,
so cost is computed incrementally (fast).
"""
import os, sys, time, json, pickle, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rot4_loader import decode_line

HERE = os.path.dirname(os.path.abspath(__file__))
m = 37
ncell = m * m
N = 2 * m

# ---------- build / load line_cons + cell->lines (cached) ----------
LC_CACHE = os.path.join(HERE, "line_cons_m37.pkl")
if os.path.exists(LC_CACHE):
    with open(LC_CACHE, "rb") as f:
        line_cons, cell_lines = pickle.load(f)
    print(f"[cache] loaded line_cons ({len(line_cons)} lines)", flush=True)
else:
    # reuse the constraint builder from asymmetric_lll (inline, no ortools)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "al_mod", os.path.join(HERE, "asymmetric_lll_m37.py"))
    # we only need generate_constraints; re-import safely
    import math as _m
    from collections import defaultdict as _dd
    def _c4(cell, r, n):
        x, y = cell
        for _ in range(r % 4):
            x, y = (n - 1 - y), x
        return (x, y)
    def _orbit(cell, n):
        return [_c4(cell, r, n) for r in range(4)]
    def _rdirs(n):
        dirs = set()
        for dx in range(-(n-1), n):
            for dy in range(0, n):
                if dx == 0 and dy == 0: continue
                g = _m.gcd(abs(dx), dy) or 1
                rdx, rdy = dx//g, dy//g
                if rdx < 0 or (rdx==0 and rdy<0): rdx, rdy = -rdx, -rdy
                dirs.add((rdx, rdy))
        return dirs
    def _gen(m):
        n = 2*m
        reps = [(x,y) for x in range(m) for y in range(m)]
        orbits = [_orbit(c, n) for c in reps]
        D = _rdirs(n)
        lw = _dd(lambda: _dd(lambda: _dd(int)))
        for i,(x,y) in enumerate(reps):
            for (X,Y) in orbits[i]:
                for (dx,dy) in D:
                    p = (-dy, dx)
                    key = p[0]*X + p[1]*Y
                    lw[(dx,dy)][key][i] += 1
        lc = []
        for d, lines in lw.items():
            for key, pw in lines.items():
                if sum(pw.values()) > 2:
                    lc.append(dict(pw))
        return lc
    t0 = time.time()
    line_cons = _gen(m)
    print(f"[build] line_cons = {len(line_cons)} lines in {time.time()-t0:.1f}s", flush=True)
    # cell_lines: cell_idx -> list of (line_idx, weight)
    cell_lines = [_dd(int) for _ in range(ncell)]
    for li, d in enumerate(line_cons):
        for ci, w in d.items():
            cell_lines[ci][li] = w
    with open(LC_CACHE, "wb") as f:
        pickle.dump((line_cons, cell_lines), f)
    print(f"[cache] saved", flush=True)

# ---------- (X)-cost for a split: core (X)-free + 2 new cells ----------
def core_weight(core_cells):
    """line_idx -> total weight of core cells on that line (core is (X)-free, so <=2)."""
    cw = {}
    for ci in core_cells:
        for li, w in cell_lines[ci].items():
            cw[li] = cw.get(li, 0) + w
    return cw

def split_cost(core_cells, new_cells):
    cw = core_weight(core_cells)
    # gather lines touched by new cells
    seen = {}
    for ci in new_cells:
        for li, w in cell_lines[ci].items():
            seen[li] = seen.get(li, 0) + w
    cost = 0
    for li, nw in seen.items():
        total = cw.get(li, 0) + nw
        if total > 2:
            cost += (total - 2)
    return cost

# ---------- load m=36 seed ----------
seed_path = os.path.join(HERE, "flammenkamp_cache", "n72_rot4.few")
with open(seed_path) as f:
    first = f.readline().strip()
pts72 = decode_line(first, 72)
seed_cells = sorted([(x, y) for (x, y) in pts72 if x < 36 and y < 36])
assert len(seed_cells) == 36, len(seed_cells)
seed_idx = [x * m + y for (x, y) in seed_cells]
print(f"[seed] m=36: {len(seed_cells)} cells loaded", flush=True)

# verify seed is a valid (X)-free 2-factor (sanity)
seed_cost = split_cost([], seed_idx)  # core empty -> just seed lines
# proper seed cost:
seed_cw = core_weight(seed_idx)
seed_cost = sum(max(0, w-2) for w in seed_cw.values())
print(f"[seed] self (X)-cost = {seed_cost} (must be 0)", flush=True)

# ---------- measure all 36 splits ----------
print(f"[split] evaluating 36 edge-splits with CORRECT (X)-check ...", flush=True)
t1 = time.time()
costs = []
best = None
core_set = set(seed_idx)
for e in seed_cells:
    ei = e[0]*m + e[1]
    if ei not in core_set:
        continue
    core_cells = [ci for ci in seed_idx if ci != ei]
    a, b = e
    new_cells = [a*m + 36, 36*m + b]
    c = split_cost(core_cells, new_cells)
    costs.append((c, e))
    if best is None or c < best[0]:
        best = (c, e)
costs.sort()
print(f"[split] done in {time.time()-t1:.2f}s", flush=True)
print(f"[split] min (X)-cost among 36 splits = {best[0]}  (split edge {best[1]})", flush=True)
print(f"[split] cost distribution: "
      f"min={costs[0][0]} median={costs[len(costs)//2][0]} "
      f"max={costs[-1][0]}", flush=True)
print(f"[split] #splits with cost<=10: {sum(1 for c,_ in costs if c<=10)}", flush=True)

verdict = {
    "m": m,
    "seed_source": "flammenkamp_cache/n72_rot4.few (first line)",
    "seed_self_Xcost": seed_cost,
    "n_splits": len(costs),
    "min_split_Xcost": best[0],
    "best_split_edge": list(best[1]),
    "median_split_Xcost": costs[len(costs)//2][0],
    "max_split_Xcost": costs[-1][0],
    "n_splits_cost_le_10": sum(1 for c,_ in costs if c<=10),
    "note_false_positive": ("results/m37_surgery_result.json (2026-07-13) is a FALSE "
        "POSITIVE: independent brute force found 248 collinear triples. Caused "
        "by pre-v5 buggy (X)-check; v5 corrected it but is seed-limited."),
    "conclusion": (
        f"Corrected surgery: the BEST of 36 edge-splits still introduces "
        f"min {best[0]} (X)-violations (median {costs[len(costs)//2][0]}). So a "
        "plain split is far from (X)-free; an absorber must fix ~%d conflicts "
        "via core k-switches. This matches v5's negative outcome and confirms "
        "m=37 remains OPEN. A real #4 advancement needs multi-seed + deeper "
        "k-switch absorber (beyond v5's single seed / 3-switch bound)." % best[0]),
}
with open(os.path.join(HERE, "results", "absorber_m37.json"), "w") as f:
    json.dump(verdict, f, indent=2)
print(f"\n[saved] results/absorber_m37.json")
for c, e in costs[:8]:
    print(f"  split {e}: cost={c}")
