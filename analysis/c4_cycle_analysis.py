#!/usr/bin/env python3
"""Analyze C4 graph patterns: cycle structure distribution across all even n."""
import os, sys
sys.path.insert(0, '.')
from collections import Counter

ALPH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|'
VAL = {c: i for i, c in enumerate(ALPH)}
CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')

def load_solutions(n):
    """Load all C4 rot4 solutions for n."""
    sols = []
    for ext in ['', '.few']:
        p = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if not os.path.exists(p):
            continue
        with open(p) as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue
                pre = line[0]
                body = line[1:] if pre in '.:/-ocx+*' else line
                if len(body) < 2 * n:
                    continue
                pts = []
                ok = True
                for r in range(n):
                    c1 = VAL.get(body[2*r])
                    c2 = VAL.get(body[2*r+1])
                    if c1 is None or c2 is None or c1 >= n or c2 >= n:
                        ok = False
                        break
                    pts.append((r, c1))
                    pts.append((r, c2))
                if ok:
                    sols.append(pts)
    return sols

def extract_orbits(pts, n):
    N = n // 2
    used = set()
    orbits = []
    for p in pts:
        if p in used:
            continue
        r, c = p
        # Generate all 4 C4 orbit points
        orbit = [(r,c), (c, n-1-r), (n-1-r, n-1-c), (n-1-c, r)]
        used.update(orbit)
        # Find the canonical cell in the fundamental domain [0,N)×[0,N)
        for cell in orbit:
            if cell[0] < N and cell[1] < N:
                orbits.append(cell)
                break
    return orbits

def cycle_decomposition(edges, m):
    """Given edges of a 2-regular graph on m vertices, return cycle lengths."""
    adj = {i: [] for i in range(m)}
    for i, j in edges:
        adj[i].append(j)
        adj[j].append(i)
    visited = set()
    cycles = []
    for v in range(m):
        if v in visited:
            continue
        # Walk the cycle
        cyc = [v]
        visited.add(v)
        prev = v
        cur = adj[v][0]
        while cur != v:
            cyc.append(cur)
            visited.add(cur)
            nxt = adj[cur][0] if adj[cur][1] == prev else adj[cur][1]
            prev, cur = cur, nxt
        cycles.append(len(cyc))
    return tuple(sorted(cycles))

print(f"{'n':>4} {'m':>3} {'sols':>6} {'graphs':>6} {'cycle_types':>40}")
print("="*60)

results = {}
for n in range(12, 58, 2):
    pts_list = load_solutions(n)
    if not pts_list:
        continue
    m = n // 2
    # Count distinct cycle decompositions
    cyc_counter = Counter()
    for pts in pts_list:
        orbits = extract_orbits(pts, n)
        if len(orbits) != m:
            continue
        edges = [(min(i,j), max(i,j)) for (i,j) in orbits]
        cyc = cycle_decomposition(edges, m)
        cyc_counter[cyc] += 1
    
    num_graphs = len(cyc_counter)
    top_cyc = cyc_counter.most_common(3)
    cyc_str = ", ".join([f"{c[0]}×{c[1]}" for c in top_cyc[:2]])
    
    print(f"{n:>4} {m:>3} {len(pts_list):>6} {num_graphs:>6}  {cyc_str}")
    results[n] = {
        'm': m, 'total_sols': len(pts_list),
        'num_graphs': num_graphs,
        'top_cycles': top_cyc
    }

# Summary: what fraction have full m-cycle?
print("\n=== CYCLE PATTERN SUMMARY ===")
full_m_cycle = 0
hamiltonian = 0 # includes (m-1, 1) i.e. almost full cycle
for n, r in results.items():
    m = r['m']
    cycs = r['top_cycles']
    for cyc, count in cycs:
        if cyc == (m,):
            full_m_cycle += count
        elif len(cyc) == 2 and min(cyc) == 1:
            hamiltonian += count

total = sum(r['total_sols'] for r in results.values())
print(f"Total C4 solutions analyzed: {total}")
print(f"Full m-cycle solutions: {full_m_cycle} ({full_m_cycle/total*100:.1f}%)")
print(f"(m-1,1) near-cycle solutions: {hamiltonian} ({hamiltonian/total*100:.1f}%)")
print(f"Combined: {(full_m_cycle+hamiltonian)/total*100:.1f}% of all known C4 solutions")
