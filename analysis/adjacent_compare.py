#!/usr/bin/env python3
"""
Systematic comparison of adjacent m solutions.
Look for: shared cells, transformation patterns, structural invariants.
"""
import json, os
from collections import Counter

sol_dir = 'results/solutions'
all_sols = {}
for fname in sorted(os.listdir(sol_dir)):
    if not fname.endswith('.json'): continue
    data = json.load(open(f'{sol_dir}/{fname}'))
    if 'cells' not in data: continue
    m = data.get('m', len(data['cells']))
    all_sols[m] = sorted(data['cells'])

print("=" * 80)
print("ADJACENT m COMPARISON: cell-by-cell")
print("=" * 80)

ms = sorted([m for m in all_sols.keys() if m < 30])  # skip m=36 for now

for idx in range(len(ms)-1):
    m1, m2 = ms[idx], ms[idx+1]
    if m2 != m1 + 1: continue  # only adjacent pairs
    
    cells1 = all_sols[m1]
    cells2 = all_sols[m2]
    
    print(f"\n--- m={m1} vs m={m2} ---")
    print(f"  m={m1}: {cells1}")
    print(f"  m={m2}: {cells2}")
    
    # 1. Common cells (exact match)
    set1 = set(tuple(c) for c in cells1)
    set2 = set(tuple(c) for c in cells2)
    common = set1 & set2
    only1 = set1 - set2
    only2 = set2 - set1
    
    print(f"  Common cells ({len(common)}): {sorted(common) if common else 'NONE'}")
    print(f"  Only in m={m1}: {sorted(only1)}")
    print(f"  Only in m={m2}: {sorted(only2)}")
    
    # 2. Shift pattern: cells in m1 offset by (+1,0), (0,+1), or (+1,+1)?
    shifted = {}
    for (x1, y1) in only1:
        for (x2, y2) in only2:
            dx, dy = x2 - x1, y2 - y1
            key = (dx, dy)
            shifted[key] = shifted.get(key, 0) + 1
    
    if shifted:
        best_shift = max(shifted.items(), key=lambda kv: kv[1])
        print(f"  Best shift from m={m1}-only to m={m2}-only: {best_shift[0]} ({best_shift[1]} matches)")
    
    # 3. Cycle structure comparison
    # Build cycle signature for each m
    def get_cycle_sig(cells, m):
        adj = [[] for _ in range(m)]
        for (i, j) in cells:
            adj[i].append(j)
            adj[j].append(i)
        visited = [False] * m
        cycles = []
        for v in range(m):
            if not visited[v]:
                comp = []
                stack = [v]
                while stack:
                    node = stack.pop()
                    if not visited[node]:
                        visited[node] = True
                        comp.append(node)
                        for nb in adj[node]:
                            if not visited[nb]:
                                stack.append(nb)
                cycles.append(len(comp))
        return tuple(sorted(cycles))
    
    sig1 = get_cycle_sig(cells1, m1)
    sig2 = get_cycle_sig(cells2, m2)
    print(f"  Cycle sig m={m1}: {sig1}")
    print(f"  Cycle sig m={m2}: {sig2}")
    
    # 4. Check: does removing one cell from m2 give something like m1?
    # Or does adding one cell to m1 give m2?
    # For each cell in m2, check if m2 \ {cell} is "close" to m1
    for rem in cells2:
        reduced = sorted(c for c in cells2 if c != rem)
        # Check if reduced has same structure as m1
        if reduced == cells1:
            print(f"  *** m={m2} minus {rem} = EXACT m={m1}! ***")
        # Check intersection count
        common_with_m1 = len(set(tuple(c) for c in reduced) & set1)
        if common_with_m1 >= len(cells1) - 1:
            print(f"  m={m2} minus {rem}: {common_with_m1}/{len(cells1)} cells match m={m1}")

print("\n" + "=" * 80)
print("MULTI-M COMPARISON: any cell appearing in MANY m?")
print("=" * 80)

# Count how many m values each cell appears in
cell_freq = Counter()
for m, cells in all_sols.items():
    for c in cells:
        if m <= 19:  # only smaller m
            cell_freq[tuple(c)] += 1

# Most frequent cells
print("Cells appearing in multiple m values:")
for (x, y), cnt in cell_freq.most_common(20):
    if cnt >= 2:
        # Which m values?
        appearances = [m for m, cells in all_sols.items() if [x, y] in cells and m <= 19]
        print(f"  ({x:2d},{y:2d}): {cnt} times at m={appearances}")

# Also check if some cell types "grow" with m
# e.g., (0, m-1) appears in many solutions?
print()
print("Corner cells (0,y) or (x,0) across m:")
for m in sorted(all_sols.keys()):
    if m >= 20: continue
    cells = all_sols[m]
    top_row = sorted([(x,y) for (x,y) in cells if x == 0])
    left_col = sorted([(x,y) for (x,y) in cells if y == 0])
    print(f"  m={m}: top_row(x=0)={top_row}, left_col(y=0)={left_col}")
