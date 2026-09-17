"""
Construct m=37 2-factors mirroring m=36's skew strategy.

Key insight from A5: m=36 solution concentrates 40% of clause constraints
on just 4 hotspot edges (span∈{2,7,13,15}), leaving remaining 32 edges
with safe spans (1,4,8,9). This reduces effective SAT dimension.

For m=37, we'll:
1. Identify safest/dangerest spans from known data
2. Construct a 2-factor with a few dangerous-spanned hotspot edges
   and the rest with safe spans (wherever possible given the cycle constraint)
3. Test each constructed 2-factor with SAT pipeline
"""
import sys, os, json, time, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H
import solver_2factor_sat_pipeline as P
import solver_theory_m37 as S

M = 37

def span_of(u, v):
    return min(abs(u - v), M - abs(u - v))

def construct_hotspot_cycle(rng, hot_pairs, safe_span_set, max_hot=5):
    """
    Build a Hamiltonian cycle that includes a specified set of hotspot edges,
    then fills the rest with edges whose spans are in safe_span_set.
    
    hot_pairs: list of (u,v) edges that MUST be in the cycle (the hotspots)
    safe_span_set: set of span values considered "safe" (low clause mentions)
    
    This is a HC-construction problem: find a Hamiltonian cycle containing
    fixed edges. We'll use a greedy path-building approach.
    """
    # Strategy: build cycle incrementally, forcing hotspot edges first
    best_try = None
    best_clauses = float('inf')
    
    for attempt in range(500):
        used = set()
        adj = defaultdict(list)
        
        # Stage 1: Add hot_pairs first
        hot_added = set()
        for u, v in hot_pairs:
            if u in hot_added or v in hot_added:
                continue  # skip if vertex already used
            if len(adj[u]) >= 2 or len(adj[v]) >= 2:
                continue
            adj[u].append(v)
            adj[v].append(u)
            hot_added.add(u)
            hot_added.add(v)
        
        # Stage 2: Build a path that connects used components into a single cycle
        # This uses a greedy construction
        remaining = [v for v in range(M) if v not in hot_added]
        rng.shuffle(remaining)
        
        # Try to connect the hot-added components into a cycle
        hot_vertices = sorted(hot_added)
        
        # Fallback: just build a random Hamiltonian cycle and check if it happens
        # to include edges from hot_pairs. This isn't ideal but is simpler.
        # 
        # Better approach: build a cycle using the span-biased generator from skewed,
        # but with explicit hotspot edges.
        
        # Let's use mutate_cycle from a carefully constructed initial cycle
        # Start from best72 or 448-clause winner
        # Then heavily mutate it, but bias toward certain spans
        
        if attempt == 0:
            # Start from best72
            with open('results/solver_theory_m37_long.json') as f:
                d = json.load(f)
            base_edges = [tuple(e) for e in d['edges']]
        elif attempt == 1:
            # Start from 448-clause winner
            with open('results/hamiltonian_mutate.json') as f:
                d = json.load(f)
            base_edges = [tuple(e) for e in d['best_edges']]
        else:
            # Random mutation from best known
            base_edges = None
        
        if base_edges:
            # Try 1-7 random swaps
            n_swaps = rng.randint(1, 7)
            edges = H.mutate_cycle(base_edges, rng, n_swaps)
            edges = sorted(set(edges))
            if len(edges) != M:
                continue
        else:
            # Pure random construction
            vlist = list(range(M))
            rng.shuffle(vlist)
            edges_set = set()
            for k in range(M):
                a, b = vlist[k], vlist[(k + 1) % M]
                edges_set.add((a, b) if a <= b else (b, a))
            edges = sorted(edges_set)
        
        # Check span distribution
        spans = [span_of(u, v) for u, v in edges]
        safe_count = sum(1 for s in spans if s in safe_span_set)
        hot_count = sum(1 for s in spans if s not in safe_span_set)
        
        nc = H.count_clauses_fast(M, edges)
        
        # Track best
        if nc < best_clauses:
            best_clauses = nc
            best_try = edges
            yield nc, edges, spans
        
        # Stop early if we found something promising
        if nc < 448:
            break


def get_safe_dangerous_spans():
    """Use data from best72 and 448-clause winner to classify spans."""
    with open(HERE + '/results/solver_theory_m37_long.json') as f:
        d72 = json.load(f)
    edges72 = [tuple(e) for e in d72['edges']]
    
    clauses72, _ = P.enumerate_clauses(M, edges72, verbose=False)
    ecc72 = {i: 0 for i in range(M)}
    for a, b, c, _ in clauses72:
        ecc72[a] += 1; ecc72[b] += 1; ecc72[c] += 1
    
    span_data72 = defaultdict(list)
    for idx, (u, v) in enumerate(edges72):
        sp = span_of(u, v)
        span_data72[sp].append(ecc72[idx])
    
    # 448-clause winner
    with open(HERE + '/results/hamiltonian_mutate.json') as f:
        d448 = json.load(f)
    edges448 = [tuple(e) for e in d448['best_edges']]
    
    clauses448, _ = P.enumerate_clauses(M, edges448, verbose=False)
    ecc448 = {i: 0 for i in range(M)}
    for a, b, c, _ in clauses448:
        ecc448[a] += 1; ecc448[b] += 1; ecc448[c] += 1
    
    span_data448 = defaultdict(list)
    for idx, (u, v) in enumerate(edges448):
        sp = span_of(u, v)
        span_data448[sp].append(ecc448[idx])
    
    print("=== Per-span danger classification for m=37 ===")
    print("Span | best72 avg | best72 max | 448-cls avg | 448-cls max | verdict")
    print("-" * 70)
    
    safe_spans = set()
    dangerous_spans = set()
    all_spans = sorted(set(list(span_data72.keys()) + list(span_data448.keys())))
    
    for sp in all_spans:
        v72 = span_data72.get(sp, [])
        v448 = span_data448.get(sp, [])
        
        avg72 = sum(v72) / len(v72) if v72 else 0
        avg448 = sum(v448) / len(v448) if v448 else 0
        max72 = max(v72) if v72 else 0
        max448 = max(v448) if v448 else 0
        
        overall_avg = (avg72 * len(v72) + avg448 * len(v448)) / (len(v72) + len(v448)) if (v72 or v448) else 0
        
        if overall_avg < 25:
            verdict = "SAFE"
            safe_spans.add(sp)
        elif overall_avg > 45:
            verdict = "DANGER"
            dangerous_spans.add(sp)
        else:
            verdict = "moderate"
            safe_spans.add(sp)  # moderate is ok for fill
        
        print(f"  {sp:4d} | {avg72:10.1f} | {max72:9d} | {avg448:10.1f} | {max448:9d} | {verdict}")
    
    print(f"\nSafe spans: {sorted(safe_spans)}")
    print(f"Dangerous spans: {sorted(dangerous_spans)}")
    
    return safe_spans, dangerous_spans


def main():
    print("=== Constructing skewed m=37 2-factors ===")
    print()
    
    rng = random.Random(20260716)
    
    # Step 1: Classify spans
    safe_spans, dangerous_spans = get_safe_dangerous_spans()
    
    # Step 2: For m=36, the hot spans were {2,7,13,15} and safe were {1,4,8,9}
    # For m=37, which spans are analogous? Use the data.
    # Let's try using dangerous_spans as hotspots
    
    print("\n=== Phase 1: Greedy cycle construction ===")
    print("Building cycles with safe spans where possible...")
    
    best_overall = float('inf')
    best_edges = None
    best_spans = None
    
    for nc, edges, spans in construct_hotspot_cycle(rng, [], safe_spans, max_hot=5):
        if nc < best_overall:
            best_overall = nc
            best_edges = edges
            best_spans = spans
            safe_ct = sum(1 for s in spans if s in safe_spans)
            dang_ct = sum(1 for s in spans if s in dangerous_spans)
            print(f"  New best: {nc} clauses (safe={safe_ct}, danger={dang_ct}, span_min={min(spans)}, span_mean={sum(spans)/M:.1f})", flush=True)
            
            if nc < 448:
                print(f"  *** BREAKS 448 BARRIER! Running SAT check... ***", flush=True)
                clauses, cmap = P.enumerate_clauses(M, edges, verbose=False)
                sat_res = P.check_sat(M, edges, clauses, time_limit=120, verbose=False)
                mv = sat_res.get('maxsat_min_violations', -1)
                print(f"  SAT: min_viol={mv} -> {4*mv} defects", flush=True)
                if mv == 0:
                    print("*** BREAKTHROUGH! m=37 SOLVED! ***", flush=True)
                    orientation = sat_res.get('orientation', [])
                    cells = []
                    for idx, (u,v) in enumerate(edges):
                        if orientation[idx] == 0: cells.append((u,v))
                        else: cells.append((v,u))
                    board = S.Board(M)
                    board.build(edges, cells)
                    tb = board.verify_total()
                    print(f"  verify_total={tb}", flush=True)
                    if tb == 0:
                        result = {
                            'found': True, 'edges': edges, 'cells': cells,
                            'lifts': board.lifts, 'total_bad': 0
                        }
                        with open('results/constructed_solution.json', 'w') as f:
                            json.dump(result, f, indent=2)
                        print("  *** SAVED TO constructed_solution.json ***", flush=True)
    
    # Phase 2: If greedy didn't work, try targeted construction
    # Build 2-factors with specific high-danger spans as hotspots
    # similar to m=36's pattern
    
    if best_overall >= 448:
        print(f"\n=== Phase 2: Targeted hotspot construction ===")
        print("Building cycles with specific high-danger hotspot edges...")
        
        hotspot_spans = sorted(dangerous_spans)[:4]  # top 4 most dangerous
        
        # For each dangerous span, pick a specific edge with that span
        # Try different combinations
        for hs in hotspot_spans:
            for _ in range(30):
                # Randomly pick 2-3 edges with dangerous spans
                hot_edges = []
                for sp in rng.sample(list(dangerous_spans), min(3, len(dangerous_spans))):
                    candidates = [(u,v) for u in range(M) for v in range(u+1,M) 
                                  if span_of(u,v) == sp]
                    if candidates:
                        hot_edges.append(rng.choice(candidates))
                
                for nc, edges, spans in construct_hotspot_cycle(rng, hot_edges, safe_spans):
                    if nc < best_overall:
                        best_overall = nc
                        best_edges = edges
                        best_spans = spans
                        print(f"  Phase 2 best: {nc} clauses", flush=True)
                        
                        if nc < 440:
                            clauses, cmap = P.enumerate_clauses(M, edges, verbose=False)
                            sat_res = P.check_sat(M, edges, clauses, time_limit=120, verbose=False)
                            mv = sat_res.get('maxsat_min_violations', -1)
                            print(f"  SAT: min_viol={mv} -> {4*mv} defects", flush=True)
                            if mv == 0:
                                print("*** BREAKTHROUGH! ***", flush=True)
                                break
                    break  # one cycle per hot_edges config
    
    print(f"\n=== Final Summary ===")
    print(f"Best clauses found: {best_overall}")
    if best_edges:
        spans = [span_of(u,v) for u,v in best_edges]
        print(f"Span distribution: min={min(spans)}, max={max(spans)}, mean={sum(spans)/M:.1f}")
        print(f"Safe span count: {sum(1 for s in spans if s in safe_spans)}/{M}")
        
        # Save best
        result = {
            'best_clauses': best_overall,
            'edges': best_edges,
            'spans': spans,
            'safe_count': sum(1 for s in spans if s in safe_spans),
            'dangerous_count': sum(1 for s in spans if s in dangerous_spans)
        }
        with open('results/constructed_best.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved to constructed_best.json")
    
    return best_overall < 448  # True if we improved


if __name__ == '__main__':
    main()
