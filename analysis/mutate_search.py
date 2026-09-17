"""
mutate_search.py — Mutation-based search starting from config_408's [9,28] edges.
Try small perturbations and keep improvements.
"""
import os, sys, json, random, copy, time
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

def load_edges(path):
    with open(path) as f:
        d = json.load(f)
    return [tuple(e) for e in d["edges"]]

def extract_cycles(cells):
    """Extract cycles from 2-factor cells."""
    adj = {i: [] for i in range(M)}
    for i, (u, v) in enumerate(cells):
        adj[u].append((v, i))
        adj[v].append((u, i))
    visited_v = set()
    visited_e = set()
    cycles = []
    for v in range(M):
        if v in visited_v:
            continue
        cyc = []
        cur = v
        prev = -1
        while cur not in visited_v:
            visited_v.add(cur)
            cyc.append(cur)
            nxt = None
            for nb, ei in adj[cur]:
                if ei not in visited_e:
                    nxt = nb
                    visited_e.add(ei)
                    break
            if nxt is None or nxt == prev:
                break
            prev = cur
            cur = nxt
        if len(cyc) >= 2:
            cycles.append(cyc)
    return cycles

def vertex_swap(cells, rng):
    """Swap one vertex from a short cycle to a long cycle."""
    cycles = extract_cycles(cells)
    if len(cycles) < 2:
        return cells
    # Pick two cycles
    ci, cj = rng.sample(range(len(cycles)), 2)
    cyc1, cyc2 = cycles[ci], cycles[cj]
    
    # Rebuild cells from reorganized cycles
    vs = list(range(M))
    # Regenerate: keep same cycle structure but swap random vertices
    clens = [len(c) for c in cycles]
    rng.shuffle(vs)
    new_cells = []
    pos = 0
    for cl in clens:
        cv = vs[pos:pos+cl]
        pos += cl
        for k in range(cl):
            u = cv[k]; v = cv[(k+1)%cl]
            new_cells.append((u, v))
    return new_cells

def permute_ordering(cells, rng):
    """Permute how vertices are arranged within each cycle."""
    cycles = extract_cycles(cells)
    new_cells = []
    for cyc in cycles:
        if len(cyc) <= 2:
            new_cells.extend([(cyc[0], cyc[1])] if len(cyc) == 2 else [(cyc[0], cyc[0])])
            continue
        # Pick a random rotation and/or reversal
        start = rng.randint(0, len(cyc)-1)
        rev = rng.choice([False, True])
        ordered = cyc[start:] + cyc[:start]
        if rev:
            ordered = [ordered[0]] + ordered[:0:-1]
        for k in range(len(ordered)):
            u = ordered[k]; v = ordered[(k+1)%len(ordered)]
            new_cells.append((u, v))
    return new_cells

def main():
    rng = random.Random(999)
    
    # Start from config_408
    cells = load_edges(os.path.join(HERE, "results", "config_408_edges.json"))
    best_gv = count_gv(cells)
    print(f"config_408 GV: {best_gv} (baseline)", flush=True)
    
    n_iter = 50000
    stall = 0
    
    for trial in range(n_iter):
        # Alternate between mutation types
        if rng.random() < 0.5:
            new_cells = vertex_swap(cells, rng)
        else:
            new_cells = permute_ordering(cells, rng)
        
        gv = count_gv(new_cells)
        
        if gv < best_gv:
            best_gv = gv
            cells = new_cells
            stall = 0
            print(f"  trial {trial}: NEW BEST GV = {best_gv}", flush=True)
            if gv < 70:
                out = os.path.join(HERE, "results", f"mutate_best_gv_{gv}.json")
                with open(out, "w") as f:
                    json.dump({"m": M, "edges": cells, "gv": gv, "trial": trial}, f)
                print(f"    Saved to {out}", flush=True)
        elif gv == best_gv:
            # Accept equal solutions with 50% probability
            if rng.random() < 0.5:
                cells = new_cells
        # Otherwise: reject (keep current)
        
        # Track stall
        if trial % 1000 == 0:
            print(f"  progress: trial {trial}, GV={best_gv}", flush=True)
    
    print(f"\n{'='*50}", flush=True)
    print(f"After {n_iter} mutations: best GV = {best_gv}", flush=True)

if __name__ == "__main__":
    main()
