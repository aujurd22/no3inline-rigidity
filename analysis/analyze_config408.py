"""
Analyze the structure of config_408's 2-factor.
What makes it special vs random 2-factors?
"""
import json, sys
from collections import defaultdict, Counter

M = 37

# Load config_408 edges
with open("D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis\\results\\config_408_edges.json") as f:
    data = json.load(f)

edges = [tuple(e) for e in data["edges"]]
assert len(edges) == M

# Build adjacency
adj = defaultdict(list)
for u, v in edges:
    adj[u].append(v)
    adj[v].append(u)

print("=== Degree check ===")
for v, nbs in sorted(adj.items()):
    assert len(nbs) == 2, f"Vertex {v} has degree {len(nbs)}"
print("All vertices have degree 2. ✓")

# Find cycles
visited = set()
cycles = []
for start in range(M):
    if start in visited:
        continue
    # Trace cycle
    cycle = [start]
    visited.add(start)
    prev = start
    cur = adj[start][0]
    while cur != start:
        cycle.append(cur)
        visited.add(cur)
        nbs = adj[cur]
        nxt = nbs[0] if nbs[1] == prev else nbs[1]
        prev, cur = cur, nxt
    cycles.append(cycle)

print(f"\n=== Cycle structure ({len(cycles)} cycles) ===")
cycle_lens = sorted([len(c) for c in cycles], reverse=True)
print(f"Cycle lengths: {cycle_lens}")
print(f"Partition: {cycle_lens[0]}+{cycle_lens[1]} = {sum(cycle_lens)}")

for i, c in enumerate(cycles):
    print(f"  Cycle {i} (len={len(c)}): {c}")

# Edge degree statistics  
print(f"\n=== Vertex degree features ===")
# What vertex values appear most?
flat_vals = [v for e in edges for v in e]
val_counts = Counter(flat_vals)
print(f"Vertex values: min={min(flat_vals)}, max={max(flat_vals)}")
print(f"Most common values: {val_counts.most_common(5)}")

# Check: are any vertices repeated within a single edge?
dup_edges = [(u,v) for u,v in edges if u == v]
print(f"\nLoop edges (u==v): {len(dup_edges)}")

# Check for symmetry in edge structure
print(f"\n=== Edge analysis ===")
# Difference distribution
diffs = Counter(abs(u - v) for u, v in edges)
print(f"Edge length distribution (|u-v|):")
for d in sorted(diffs):
    print(f"  |u-v|={d:2d}: {diffs[d]} edges")

# Consecutive vertex span
max_span = max(max(u,v) for u,v in edges) - min(min(u,v) for u,v in edges)
print(f"\nFull span: {max_span} (0..{max(flat_vals)})")

# Are there "clusters" of nearby vertices?
# Check vertex density
print(f"\n=== Vertex coverage ===")
covered = set(flat_vals)
missing = [v for v in range(M) if v not in covered]
print(f"Covered: {len(covered)}/{M} vertices")
print(f"Missing: {missing}")

# Analyze the 2-factor connectivity - is it a "ladder"?
print(f"\n=== Pattern analysis ===")
# Check: parallel edges (u1≈u2, v1≈v2)
for u1, v1 in edges:
    for u2, v2 in edges:
        if (u1, v1) >= (u2, v2):
            continue
        if abs(u1 - u2) <= 2 and abs(v1 - v2) <= 2:
            print(f"  Nearby edges: ({u1},{v1}) ~ ({u2},{v2})")

print(f"\nDone.")
