"""
direction3b_focus.py — Focused cycle-type search.

config_408 has cycle structure [9, 28] and achieves 16 violations.
The clause-count proxy suggests [31, 6] may be even better.

We:
1. Generate many random 2-factors with the MOST promising cycle types.
2. For each, compute a BETTER clause count using the full R8 system.
3. Report minimum clause counts per cycle type.

Target cycle types (from proxy analysis):
- [31, 6]:  ~424  ← best proxy
- [28, 9]:  ~448  (same structure as config_408)
- [25, 12]: ~432
- [14, 13, 10]: ~428

Usage: python direction3b_focus.py
"""
import os, sys, json, random, time
from collections import defaultdict, Counter
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solver_theory_m37 import c4, line_of

M = 37

def generate_2factor_with_cycles(m, cycle_lengths, rng):
    vertices = list(range(m))
    rng.shuffle(vertices)
    edges = []
    pos = 0
    for clen in cycle_lengths:
        cycle_verts = vertices[pos:pos+clen]
        pos += clen
        for k in range(clen):
            u = cycle_verts[k]
            v = cycle_verts[(k + 1) % clen]
            edges.append(tuple(sorted((u, v))))
    return sorted(set(edges))

def count_x_violations(cells):
    """Count X-layer violations: return clause count AND triple count.
    cells: list of (x,y) pairs.
    Uses the 16-class reduction from R8 proof."""
    n = 2 * M
    # Precompute lifts
    lifts = []
    for (x, y) in cells:
        lifts.append([c4(x, y, r, n) for r in range(4)])
    
    # 16 rotation equivalence classes (one pattern each)
    r8_patterns = [
        (0,1,0),(0,1,1),(0,1,2),(0,1,3),
        (0,2,0),(0,2,1),(0,2,2),(0,2,3),
        (0,3,0),(0,3,1),(0,3,2),(0,3,3),
        (0,0,1),(0,0,2),(0,0,3),(0,0,0),
    ]
    
    clauses = 0
    viol_triples = 0
    
    m = len(cells)
    for i in range(m):
        for j in range(i + 1, m):
            for k in range(j + 1, m):
                for ri, rj, rk in r8_patterns:
                    pi = lifts[i][ri]
                    pj = lifts[j][rj]
                    pk = lifts[k][rk]
                    if pi == pj or pj == pk or pk == pi:
                        continue
                    det = (pj[0]-pi[0])*(pk[1]-pi[1]) - (pk[0]-pi[0])*(pj[1]-pi[1])
                    if det == 0:
                        clauses += 1
                        viol_triples += 1
                        break  # One violation per cell triple suffices for clause
    
    return clauses, viol_triples

def main():
    rng = random.Random(123)  # fixed seed for reproducibility
    
    target_types = [
        ([31, 6], 50),
        ([28, 9], 50),
        ([25, 12], 50),
        ([14, 13, 10], 50),
        ([27, 10], 50),
        ([24, 13], 50),
        ([23, 14], 50),
        ([37], 50),
    ]
    
    print(f"=== Focused Cycle-Type Clause Count Search (m={M}) ===", flush=True)
    print(f"{'Cycle type':^20s} {'Samples':>8s} {'Min cls':>8s} {'Min viol':>8s} {'Best found':>12s}", flush=True)
    print("-" * 60, flush=True)
    
    results = {}
    
    for cycle_type, n_samples in target_types:
        if sum(cycle_type) != M:
            continue
        
        min_cls = float('inf')
        min_viol = float('inf')
        best_edges = None
        
        t0 = time.time()
        for trial in range(n_samples):
            edges = generate_2factor_with_cycles(M, cycle_type, rng)
            # Use orientation (u,v) for each edge (arbitrary but consistent)
            cells = [(u, v) for (u, v) in edges]
            cls, viol = count_x_violations(cells)
            if cls < min_cls:
                min_cls = cls
                min_viol = viol
                best_edges = edges
            if cls == 0:
                print(f"  FOUND ZERO-VIOLATION config! cycle_type={cycle_type}", flush=True)
                break
        
        elapsed = time.time() - t0
        print(f"  {str(cycle_type):^20s} {n_samples:8d} {min_cls:8d} {min_viol:8d}  [{elapsed:.0f}s]", flush=True)
        results[str(cycle_type)] = {"samples": n_samples, "min_cls": min_cls, "min_viol": min_viol}
        
        # Save best config if promising
        if min_cls < 420:
            out_path = os.path.join(HERE, "results", f"best_{'_'.join(map(str,cycle_type))}_edges.json")
            with open(out_path, "w") as f:
                json.dump({"m": M, "edges": best_edges, "cls": min_cls, "viol": min_viol, "cycle_type": cycle_type}, f)
            print(f"       saved to results/best_{'_'.join(map(str,cycle_type))}_edges.json", flush=True)
    
    print("-" * 60, flush=True)
    print("\nBest results by cycle type:", flush=True)
    for ct, res in sorted(results.items(), key=lambda x: x[1]["min_cls"]):
        print(f"  {ct:20s}: min_cls={res['min_cls']:5d} min_viol={res['min_viol']}", flush=True)

if __name__ == "__main__":
    main()
