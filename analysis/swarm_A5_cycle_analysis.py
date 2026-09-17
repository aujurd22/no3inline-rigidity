#!/usr/bin/env python
"""Simple cycle analysis for m=36 and m=37 2-factors."""
import json, sys
from collections import defaultdict

with open('results/solutions/m36.json') as f:
    m36 = json.load(f)
edges_m36 = [tuple(sorted(c)) for c in m36['cells']]

with open('results/swarm_D1_2_best72_clauses.json') as f:
    m37 = json.load(f)
edges_m37 = [tuple(e) for e in m37['edges']]

def cycles(edges, m):
    adj = defaultdict(list)
    for u,v in edges:
        adj[u].append(v); adj[v].append(u)
    visited = [False]*m
    cycles = []
    for v in range(m):
        if not visited[v]:
            cyc = [v]; visited[v] = True
            prev = v; cur = adj[v][0]
            while cur != v:
                cyc.append(cur); visited[cur] = True
                nxt = adj[cur][0] if adj[cur][0] != prev else adj[cur][1]
                prev, cur = cur, nxt
            cycles.append(cyc)
    return cycles

def span(x, y, m):
    d = abs(x - y)
    return min(d, m - d)

for label, edges, m in [("m=36", edges_m36, 36), ("m=37", edges_m37, 37)]:
    c = cycles(edges, m)
    print(f"\n=== {label}: {len(c)} cycles ===")
    for i, cyc in enumerate(c):
        L = len(cyc)
        sp = [span(cyc[k], cyc[(k+1)%L], m) for k in range(L)]
        print(f"  Cycle {i}: len={L:2d}  vertices={cyc}")
        print(f"            spans={sp}")
    
    # Edge-span histogram
    from collections import Counter
    hist = Counter(span(u, v, m) for u,v in edges)
    print(f"  Span histogram: {dict(sorted(hist.items()))}")
    
    # Check for loops
    loops = [(u,v) for u,v in edges if u==v]
    print(f"  Loops: {len(loops)}")
    
    # Adjacency pattern
    print(f"  Degree check: all {all(len([e for e in edges if u in e])==2 for u in range(m))}")
