"""
math_audit_exploration.py — Math skill audit of today's exploration code.
Check for bugs, invalid configurations, and incorrect assumptions.
"""
import os, sys, json, random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
M = 37

def check_config(edges, name):
    """Verify a 2-factor configuration is valid."""
    print(f"\n{'='*60}")
    print(f"AUDIT: {name}")
    print(f"{'='*60}")
    
    # 1. Check count
    n_edges = len(edges)
    print(f"  Edge count: {n_edges} (need {M}) {'✅' if n_edges == M else '❌'}")
    
    # 2. Check for duplicate cells
    edge_set = set(edges)
    n_unique = len(edge_set)
    has_duplicates = n_unique < n_edges
    print(f"  Unique cells: {n_unique}/{n_edges} {'❌ DUPLICATES!' if has_duplicates else '✅ no duplicates'}")
    
    if has_duplicates:
        dupes = [item for item, count in Counter(edges).items() if count > 1]
        print(f"  Duplicate cells: {dupes}")
    
    # 3. Check degree condition (2-regular)
    deg = Counter()
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1
    
    bad_deg = [k for k, v in deg.items() if v != 2]
    print(f"  Degree check: {len(bad_deg)} vertices with deg≠2 {'✅ all good' if not bad_deg else f'❌ {bad_deg}'}")
    
    # 4. Check coordinate ranges
    out_of_range = [(u,v) for (u,v) in edges if u < 0 or u >= M or v < 0 or v >= M]
    print(f"  Coordinate range [0,{M-1}]: {'✅' if not out_of_range else f'❌ {out_of_range}'}")
    
    # 5. Check cycle structure (should decompose into cycles)
    adj = {i: [] for i in range(M)}
    for idx, (u, v) in enumerate(edges):
        adj[u].append((v, idx))
        adj[v].append((u, idx))
    
    visited_v = set()
    visited_e = set()
    cycles = []
    isolated = []
    
    for v in range(M):
        if v in visited_v:
            continue
        # Start a new cycle
        cyc = []
        cur = v
        prev_e = -1
        while cur not in visited_v:
            visited_v.add(cur)
            cyc.append(cur)
            # Find next vertex via an unvisited edge
            found = False
            for nb, ei in adj[cur]:
                if ei != prev_e and ei not in visited_e:
                    visited_e.add(ei)
                    cur = nb
                    found = True
                    break
            if not found:
                break
        
        if len(cyc) >= 2:
            cycles.append(cyc)
        elif len(cyc) == 1:
            isolated.append(cyc[0])
    
    cycle_summary = [f"{c[0]}" + (f"-{c[-1]}" if len(c) > 1 else "") + f"({len(c)})" for c in cycles]
    print(f"  Cycles: {len(cycles)} cycle(s)", flush=True)
    for c in cycles:
        print(f"    {c} (len={len(c)})", flush=True)
    print(f"  Cycle lengths: {sorted([len(c) for c in cycles])}")
    
    # 6. Count pairwise comparisons of cells - are there many shared coordinates?
    xs = [e[0] for e in edges]
    ys = [e[1] for e in edges]
    x_counts = Counter(xs)
    y_counts = Counter(ys)
    max_x = max(x_counts.values())
    max_y = max(y_counts.values())
    print(f"  Max x frequency: {max_x} (should be 2 for 2-factor)")
    print(f"  Max y frequency: {max_y} (should be 2 for 2-factor)")
    
    return {
        "valid": n_edges == M and not has_duplicates and not bad_deg and max_x <= 2 and max_y <= 2,
        "duplicates": has_duplicates,
        "bad_deg": bad_deg,
        "cycles": [len(c) for c in cycles],
    }

# Load config_408 (known good)
print("\n--- Loading config_408 ---")
with open(os.path.join(HERE, "results", "config_408_edges.json")) as f:
    d408 = json.load(f)
edges_408 = [tuple(e) for e in d408["edges"]]
r408 = check_config(edges_408, "config_408")

# Load GV=23 config (mutation result)
print("\n--- Loading GV=23 config (mutation) ---")
try:
    with open(os.path.join(HERE, "results", "mutate_gv23.json")) as f:
        d23 = json.load(f)
    edges_23 = [tuple(e) for e in d23["edges"]]
    r23 = check_config(edges_23, "GV=23 (mutation)")
except FileNotFoundError:
    print("mutate_gv23.json not found")
    r23 = None

# Load older mutation configs for comparison
for gv in [24, 27, 28, 30]:
    try:
        with open(os.path.join(HERE, "results", f"mutate_gv{gv}.json")) as f:
            data = json.load(f)
        print(f"\n--- Loading GV={gv} ---")
        r = check_config([tuple(e) for e in data["edges"]], f"GV={gv}")
    except FileNotFoundError:
        pass

# Summary
print("\n" + "=" * 60)
print("AUDIT CONCLUSION")
print("=" * 60)
if r23:
    if r23["duplicates"]:
        print("❌ GV=23 config has DUPLICATE cells — result is INVALID!")
        print("   The two_switch mutation created duplicate cells without checking.")
        print("   This means the SDP certification at SDP_lb=27.0 is also invalidated.")
    if r23["bad_deg"]:
        print("❌ GV=23 config has degree violations — 2-factor constraint broken!")
    if not r23["bad_deg"] and not r23["duplicates"]:
        print("✅ GV=23 config is structurally valid")

print(f"\nconfig_408 valid: {'✅' if r408['valid'] else '❌'}")
print(f"config_408 cycles: {r408['cycles']}")
