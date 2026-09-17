"""
seed_search.py — Generate many [9,28] 2-factors (config_408's type)
and find the one with the LOWEST clause count.

The SDP bound for config_408 is 12.52 (≡ 16 violations optimal).
If we find a [9,28] config with < 408 clauses, it might have SDP bound < 12.5
→ potentially fewer than 16 violations.
"""
import sys, os, json, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver_2factor_sat_pipeline import enumerate_clauses

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))

def generate_2factor(m, cycle_lengths, rng):
    """Generate 2-factor with specific cycle types. Returns list of (u,v) cells."""
    vertices = list(range(m))
    rng.shuffle(vertices)
    cells = []
    pos = 0
    for clen in cycle_lengths:
        cycle_verts = vertices[pos:pos+clen]
        pos += clen
        for k in range(clen):
            u = cycle_verts[k]
            v = cycle_verts[(k + 1) % clen]
            cells.append((u, v))
    return cells

def main():
    rng = random.Random(789)
    
    # Load config_408 baseline
    with open(os.path.join(HERE, "results", "config_408_edges.json")) as f:
        d408 = json.load(f)
    edges_408 = [tuple(e) for e in d408["edges"]]
    cls_408, _ = enumerate_clauses(M, edges_408, verbose=False)
    print(f"config_408: {cls_408} clauses (baseline)", flush=True)
    
    # Search [9,28] configs
    print(f"\nSearching [9,28] configs (~30s per ~500 samples)...", flush=True)
    
    best_cls = cls_408
    best_edges = None
    best_idx = -1
    
    n_samples = 2000
    t0 = time.time()
    
    for trial in range(n_samples):
        cells = generate_2factor(M, [9, 28], rng)
        cls, _ = enumerate_clauses(M, cells, verbose=False)
        
        if cls < best_cls:
            best_cls = cls
            best_edges = cells
            best_idx = trial
            print(f"  trial {trial}: NEW BEST {cls} clauses!", flush=True)
        
        if trial % 200 == 199:
            elapsed = time.time() - t0
            print(f"  {trial+1}/{n_samples} done [{elapsed:.0f}s], best={best_cls}", flush=True)
    
    total_time = time.time() - t0
    print(f"\n{'='*50}")
    print(f"Best [9,28] config: {best_cls} clauses (baseline: {cls_408})")
    print(f"Found at trial {best_idx}, time={total_time:.0f}s")
    
    if best_cls < cls_408:
        print(f"\n✅ Found better [9,28] config with {best_cls} clauses!")
        print(f"   Running SDP certification...")
        
        # Save the best
        out_path = os.path.join(HERE, "results", f"best_{best_cls}_cls_edges.json")
        with open(out_path, "w") as f:
            json.dump({"m": M, "edges": best_edges, "clauses": best_cls}, f)
        print(f"   Saved to {out_path}")
        
        # Run SDP
        from sdp_frustration_cert import sdp_min_viol_lb
        r = sdp_min_viol_lb(37, best_edges)
        print(f"   SDP min_viol_lb = {r['min_viol_lb_sdp']:.3f}")
        print(f"   (config_408 SDP lb = 12.524)")
    else:
        print(f"\n❌ No improvement over config_408 found in {n_samples} trials")
        print(f"   config_408 seems to be a particularly good [9,28] config")

if __name__ == "__main__":
    main()
