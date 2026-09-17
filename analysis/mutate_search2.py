"""
mutate_search2.py — Two-switch mutation search from config_408.
Each mutation: pick 2 cells, swap their y-coordinates (standard 2-switch).
Keeps the 2-factor constraint invariant.
"""
import os, sys, json, random, time, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver_theory_m37 import c4

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))

def count_gv(cells):
    """Fast geometric violation count (silent)."""
    n = 2*M
    lifts = {i: [c4(cells[i][0], cells[i][1], r, n) for r in range(4)]
             for i in range(M)}
    pats = [(0,1,0),(0,1,1),(0,1,2),(0,1,3),
            (0,2,0),(0,2,1),(0,2,2),(0,2,3),
            (0,3,0),(0,3,1),(0,3,2),(0,3,3),
            (0,0,1),(0,0,2),(0,0,3),(0,0,0)]
    total = 0
    for i in range(M):
        li = lifts[i]
        for j in range(i+1, M):
            lj = lifts[j]
            for k in range(j+1, M):
                lk = lifts[k]
                for ri, rj, rk in pats:
                    pi, pj, pk = li[ri], lj[rj], lk[rk]
                    if pi == pj or pj == pk or pk == pi: continue
                    if (pj[0]-pi[0])*(pk[1]-pi[1]) - (pk[0]-pi[0])*(pj[1]-pi[1]) == 0:
                        total += 1; break
    return total

def two_switch(cells, rng):
    existing = set(cells)
    for _ in range(200):
        a = rng.randint(0, M-1)
        b = rng.randint(0, M-1)
        while b == a:
            b = rng.randint(0, M-1)
        i1, j1 = cells[a]
        i2, j2 = cells[b]
        if len({i1, j1, i2, j2}) < 4:
            continue
        new_a = (i1, i2)
        new_b = (j1, j2)
        if new_a in existing or new_b in existing or new_a == new_b:
            continue
        new = list(cells)
        new[a] = new_a
        new[b] = new_b
        return new
    # Fallback: regenerate [9,28] from scratch
    from fast_clause_search import generate
    return generate(M, [9, 28], rng)

def main():
    rng = random.Random(777)
    
    with open(os.path.join(HERE, "results", "config_408_edges.json")) as f:
        d = json.load(f)
    cells = [tuple(e) for e in d["edges"]]
    
    best_gv = count_gv(cells)
    print(f"config_408 GV: {best_gv}", flush=True)
    
    n_iter = 3000
    report_interval = 200
    
    for trial in range(n_iter):
        new_cells = two_switch(cells, rng)
        gv = count_gv(new_cells)
        
        if gv < best_gv:
            best_gv = gv
            cells = new_cells
            print(f"  trial {trial}: GV = {best_gv}  NEW BEST!", flush=True)
            if best_gv < 70:
                out = os.path.join(HERE, "results", f"mutate_gv{best_gv}.json")
                with open(out, "w") as f:
                    json.dump({"m": M, "edges": cells, "gv": best_gv}, f)
        elif gv <= best_gv + 2:
            # Accept within 2 of best to explore landscape
            if rng.random() < 0.3:
                cells = new_cells
        # else: reject
        
        if trial % report_interval == 0 and trial > 0:
            print(f"  [{trial}/{n_iter}] current best GV = {best_gv}", flush=True)
    
    print(f"\nFinal best GV after {n_iter} iterations: {best_gv}", flush=True)

if __name__ == "__main__":
    main()
