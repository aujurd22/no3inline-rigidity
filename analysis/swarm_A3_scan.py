"""
swarm_A3_scan.py — Phase 1: Find all 2-switches from best72 with best clause counts.
"""
import sys, os, json, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
sys.path.insert(0, HERE)

import swarm_D1v3_twocycle_test as T

def load_best72_edges():
    path = os.path.join(RESULTS, "swarm_D1v3_2factor_analysis.json")
    with open(path) as f:
        data = json.load(f)
    return [tuple(e) for e in data["best72"]["edges"]]

def enumerate_2switches(edges):
    E = len(edges)
    for i in range(E):
        a, b = edges[i]
        for j in range(i+1, E):
            c, d = edges[j]
            if len({a, b, c, d}) < 4:
                continue
            for (x1, y1), (x2, y2) in [((a, c), (b, d)), ((a, d), (b, c))]:
                e1 = (min(x1, y1), max(x1, y1))
                e2 = (min(x2, y2), max(x2, y2))
                if e1 == e2:
                    continue
                other = set(edges)
                other.discard(edges[i])
                other.discard(edges[j])
                if e1 in other or e2 in other:
                    continue
                yield sorted(edges[:i] + edges[i+1:j] + edges[j+1:] + [e1, e2]), (i, j, edges[i], edges[j], e1, e2)

def main():
    print("=" * 60)
    print("A3 SCAN: FIND BEST 2-SWITCH VARIANTS")
    print("=" * 60)
    
    best72 = load_best72_edges()
    print(f"Loaded best72: {len(best72)} edges")
    
    # First, get the baseline clause count for best72
    baseline = T.enumerate_clauses_fast(37, best72)
    print(f"Baseline best72: {baseline['n_clauses']} clauses")
    
    # Scan all 2-switches
    best_by_nc = {}
    total = 0
    t0 = time.time()
    
    for new_edges, info in enumerate_2switches(best72):
        total += 1
        result = T.enumerate_clauses_fast(37, new_edges)
        nc = result["n_clauses"]
        
        if nc <= 472:  # track anything close to best72's 470
            if nc not in best_by_nc or len(best_by_nc[nc]) < 5:  # keep up to 5 per nc
                best_by_nc.setdefault(nc, []).append({
                    "edges": [list(e) for e in new_edges],
                    "info": list(info),
                    "nc": nc,
                })
        
        if total % 200 == 0:
            elapsed = time.time() - t0
            print(f"  checked {total}/{1332} ({elapsed:.0f}s), best: {min(best_by_nc.keys()) if best_by_nc else 'N/A'}", flush=True)
    
    elapsed = time.time() - t0
    print(f"\nTotal: {total} 2-switches in {elapsed:.1f}s")
    
    print(f"\nBest clause counts found:")
    for nc in sorted(best_by_nc.keys()):
        print(f"  {nc} clauses: {len(best_by_nc[nc])} variants")
    
    # Save results
    output = {
        "baseline_clauses": baseline["n_clauses"],
        "total_switches_checked": total,
        "best_by_clause_count": {str(k): v for k, v in sorted(best_by_nc.items())},
        "time_s": round(elapsed, 2),
    }
    
    out_path = os.path.join(RESULTS, "swarm_A3_scan.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_path}")

if __name__ == "__main__":
    main()
