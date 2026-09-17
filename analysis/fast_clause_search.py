"""
fast_clause_search.py — Fast silent search for [9,28] and other cycle types.
Counts X-layer clauses using the 16-class R8 reduction (no verbose output).
Tests thousands of 2-factors and reports minimum clause counts.
"""
import os, sys, json, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver_theory_m37 import c4

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))

def generate(m, cycles, rng):
    vs = list(range(m))
    rng.shuffle(vs)
    cells = []
    pos = 0
    for cl in cycles:
        cv = vs[pos:pos+cl]
        pos += cl
        for k in range(cl):
            u = cv[k]; v = cv[(k+1)%cl]
            cells.append((u, v))
    return cells

def count_clauses(cells):
    """Fast silent clause count using 16 R8 patterns."""
    n = 2 * M
    lifts = {i: [c4(cells[i][0], cells[i][1], r, n) for r in range(4)]
             for i in range(M)}
    patterns = [(0,1,0),(0,1,1),(0,1,2),(0,1,3),
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
                for ri, rj, rk in patterns:
                    pi, pj, pk = li[ri], lj[rj], lk[rk]
                    if pi == pj or pj == pk or pk == pi:
                        continue
                    det = (pj[0]-pi[0])*(pk[1]-pi[1]) - (pk[0]-pi[0])*(pj[1]-pi[1])
                    if det == 0:
                        total += 1
                        break
    return total

def main():
    rng = random.Random(111)
    
    types = {
        "2-cycle_28_9": [28, 9],        # config_408 type — 3000 samples
        "3-cycle_15_12_10": [15, 12, 10],
        "3-cycle_13_12_12": [13, 12, 12],
        "3-cycle_14_13_10": [14, 13, 10],
        "3-cycle_16_13_8": [16, 13, 8],
    }
    
    ns_408 = 5000  # more samples for config_408's type
    ns_other = 2000
    print(f"Fast silent clause search: {ns_408} samples for [28,9], {ns_other} for others", flush=True)
    print(f"{'Type':<18s} {'Samples':>8s} {'Min cl':>8s} {'Best':>12s}", flush=True)
    print("-" * 50, flush=True)
    
    results = {}
    for name, cyc in types.items():
        ns = ns_408 if name == "2-cycle_28_9" else ns_other
        best_cl = 1e9
        best_cells = None
        t0 = time.time()
        for t in range(ns):
            cells = generate(M, cyc, rng)
            cl = count_clauses(cells)
            if cl < best_cl:
                best_cl = cl
                best_cells = cells
                if cl < 400:
                    print(f"  {name}: trial {t}: {cl} clauses!", flush=True)
        elapsed = time.time() - t0
        print(f"{name:<18s} {ns:8d} {best_cl:8d}  [{elapsed:.0f}s]", flush=True)
        results[name] = {"min_cl": best_cl, "type": cyc}
        if best_cl < 408:
            out = os.path.join(HERE, "results", f"fast_{name.replace(' ','_')}_{best_cl}cl.json")
            with open(out, "w") as f:
                json.dump({"m": M, "type": cyc, "edges": best_cells, "clauses": best_cl}, f)
            print(f"  -> Saved to {out}", flush=True)
    
    print("\n" + "=" * 50)
    for n, r in sorted(results.items(), key=lambda x: x[1]["min_cl"]):
        print(f"  {n:<18s}: min_cl={r['min_cl']:5d}  {r['type']}")

if __name__ == "__main__":
    main()
