"""Analyze the 404-clause configuration found by mega_sweep_escape."""
import json
from collections import Counter

with open("results/mega_sweep_escape.json") as f:
    data = json.load(f)

edges = [tuple(e) for e in data['best_edges']]
print(f"Edges: {len(edges)}, unique: {len(set(edges))}")

# Degree check
deg = Counter()
for u, v in edges:
    deg[u] += 1
    deg[v] += 1
print(f"Degree range: {min(deg.values())}-{max(deg.values())}")
print(f"Vertices: {sorted(deg.keys())}")
print(f"Missing: {sorted(set(range(37)) - set(deg.keys()))}")

# Cycle decomposition
# Build adjacency
adj = {v: [] for v in range(37)}
for u, v in edges:
    adj[u].append(v)
    adj[v].append(u)

visited = set()
cycles = []
for v in range(37):
    if v in visited: continue
    # Follow the 2-regular cycle
    cyc = []
    cur = v
    prev = -1
    while cur not in visited:
        visited.add(cur)
        cyc.append(cur)
        # next vertex = the neighbor that's not prev
        nxt = [x for x in adj[cur] if x != prev][0]
        prev, cur = cur, nxt
        if cur == v: break
    cycles.append(cyc)

print(f"\nCycle decomposition: {[len(c) for c in cycles]} cycles")
for i, c in enumerate(cycles):
    print(f"  Cycle {i+1} (len={len(c)}): {c}")

# Compare with config_408
with open("results/config_408_edges.json") as f:
    c408 = json.load(f)
edges408 = [tuple(e) for e in c408['edges']]
same_edges = set(edges) & set(edges408)
diff_edges_new = set(edges) - set(edges408)
diff_edges_old = set(edges408) - set(edges)
print(f"\nShared edges with config_408: {len(same_edges)}/37")
print(f"New edges (not in config_408): {len(diff_edges_new)}")
print(f"Old edges (not in new config): {len(diff_edges_old)}")

# i/j value analysis
i_vals = [u for u, v in edges]
j_vals = [v for u, v in edges]
print(f"\ni-values set: {sorted(set(i_vals))}")
print(f"j-values set: {sorted(set(j_vals))}")
overlap = set(i_vals) & set(j_vals)
print(f"Overlap (vertices that are both i and j): {sorted(overlap)} ({len(overlap)}/37)")

# How many cells are "bipartite-like" (i from low set, j from high set)?
low_set = set(range(19))
high_set = set(range(19, 37))
bp = sum(1 for u, v in edges if (u in low_set and v in high_set) or 
          (u in high_set and v in low_set))
print(f"\nBipartite-like edges: {bp}/37")
