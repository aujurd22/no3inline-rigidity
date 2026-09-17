#!/usr/bin/env python3
"""
Deep analysis: WHY does replacing (4,31)(7,28) with (4,7)(28,31)
reduce the clause count from 470 to 452?
"""
import sys, os, json, math
from collections import defaultdict, Counter

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_2factor_sat_pipeline as P

best72_edges = sorted([
    (15,34), (10,24), (3,23), (7,28), (2,23), (8,25), (16,30),
    (7,18), (3,29), (9,35), (11,17), (9,32), (12,36), (6,15),
    (6,31), (14,36), (1,19), (8,24), (20,25), (4,19), (12,27),
    (21,33), (5,35), (13,29), (1,27), (5,22), (21,32), (20,26),
    (0,33), (16,28), (14,22), (13,26), (10,17), (11,18), (2,34),
    (0,30), (4,31)
])

mutated452_edges = sorted([
    (0,30), (0,33), (1,19), (1,27), (2,23), (2,34), (3,23), (3,29),
    (4,7), (4,19), (5,22), (5,35), (6,15), (6,31), (7,18),
    (8,24), (8,25), (9,32), (9,35), (10,17), (10,24), (11,17), (11,18),
    (12,27), (12,36), (13,26), (13,29), (14,22), (14,36),
    (15,34), (16,28), (16,30), (20,25), (20,26), (21,32), (21,33), (28,31)
])

# Map edges to indices
edge_to_idx72 = {e: i for i, e in enumerate(best72_edges)}
edge_to_idx452 = {e: i for i, e in enumerate(mutated452_edges)}

# Find which edges changed
changed72 = [(4,31), (7,28)]
changed452 = [(4,7), (28,31)]
idx_changed72 = [edge_to_idx72[e] for e in changed72]
idx_changed452 = [edge_to_idx452[e] for e in changed452]

print("=" * 70)
print("CLAUSE ANALYSIS: best72 (470) vs mutated452 (452)")
print("=" * 70)

# Enumerate clauses
clauses72, cmap72 = P.enumerate_clauses(M, best72_edges, verbose=False)
clauses452, cmap452 = P.enumerate_clauses(M, mutated452_edges, verbose=False)

# Count clauses involving the changed edges
def clauses_involving_edge(clauses, edge_idx):
    """Count clauses where the given edge index appears."""
    return [(a,b,c,bits) for a,b,c,bits in clauses if a==edge_idx or b==edge_idx or c==edge_idx]

print("\nbest72:")
for idx in idx_changed72:
    e = best72_edges[idx]
    related = clauses_involving_edge(clauses72, idx)
    print(f"  Edge {e} (idx={idx}): {len(related)} clauses among {len(clauses72)} total")
    for a,b,c,bits in related[:5]:
        ea = best72_edges[a]
        eb = best72_edges[b]
        ec = best72_edges[c]
        print(f"    clause: edges ({ea},{eb},{ec}) forbid orient "
              f"({(bits>>0)&1},{(bits>>1)&1},{(bits>>2)&1})")

print("\nmutated452:")
for idx in idx_changed452:
    e = mutated452_edges[idx]
    related = clauses_involving_edge(clauses452, idx)
    print(f"  Edge {e} (idx={idx}): {len(related)} clauses among {len(clauses452)} total")
    for a,b,c,bits in related[:5]:
        ea = mutated452_edges[a]
        eb = mutated452_edges[b]
        ec = mutated452_edges[c]
        print(f"    clause: edges ({ea},{eb},{ec}) forbid orient "
              f"({(bits>>0)&1},{(bits>>1)&1},{(bits>>2)&1})")

# Total clause elimination analysis
print("\n" + "=" * 70)
print("CLAUSE SET DIFFERENCE")
print("=" * 70)

set72 = set(clauses72)
set452 = set(clauses452)

only72 = set72 - set452
only452 = set452 - set72

print(f"Clauses removed (in 72 but not 452): {len(only72)}")
print(f"Clauses added (in 452 but not 72):   {len(only452)}")
print(f"Net change: {len(only452) - len(only72)}")
# Should be 452-470 = -18

# Analyze patterns in only72
print("\nTop patterns in removed clauses (only72):")
edge_participation_72 = Counter()
for a,b,c,bits in only72:
    edge_participation_72[best72_edges[a]] += 1
    edge_participation_72[best72_edges[b]] += 1
    edge_participation_72[best72_edges[c]] += 1

for e, cnt in edge_participation_72.most_common(10):
    print(f"  Edge {e}: appears in {cnt} of {len(only72)} removed clauses")

print("\nTop patterns in added clauses (only452):")
edge_participation_452 = Counter()
for a,b,c,bits in only452:
    edge_participation_452[mutated452_edges[a]] += 1
    edge_participation_452[mutated452_edges[b]] += 1
    edge_participation_452[mutated452_edges[c]] += 1

for e, cnt in edge_participation_452.most_common(10):
    print(f"  Edge {e}: appears in {cnt} of {len(only452)} added clauses")

# ══════════════════════════════════════════════════════════════════════════════
# KEY INSIGHT: ANALYZE THE COLLINEARITY
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("GEOMETRIC ANALYSIS: Why does (4,7)+(28,31) beat (4,31)+(7,28)?")
print("=" * 70)

# Build cell lifts for the changed edges
n = 2 * M
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = n - 1 - y, x
        pts.append((x, y))
    return pts

# Compare the 4 lift points for each edge
print("\nLift points for each cell (n=74):")
for label, edges_list in [("best72 removed", [(4,31), (7,28)]), 
                           ("mutated452 added", [(4,7), (28,31)])]:
    print(f"\n  {label}:")
    for u, v in edges_list:
        pts0 = c4_lift(u, v)  # orientation 0
        pts1 = c4_lift(v, u)  # orientation 1
        print(f"    Cell ({u:2d},{v:2d}):")
        print(f"      orient 0: {pts0}")
        print(f"      orient 1: {pts1}")

# Check: do any lift points of (4,7) or (28,31) COINCIDE with lift points
# of the unchanged edges? If so, that might explain fewer collinearity issues.
print("\n\n=== Checking lift point collisions ===")
all_unchanged_edges72 = [e for e in best72_edges if e not in changed72]
all_unchanged_edges452 = [e for e in mutated452_edges if e not in changed452]

def get_all_lifts(edges_list):
    lifts = set()
    for u, v in edges_list:
        for orient in [0, 1]:
            pts = c4_lift(u, v) if orient == 0 else c4_lift(v, u)
            for p in pts:
                lifts.add(p)
    return lifts

unchanged_lifts72 = get_all_lifts(all_unchanged_edges72)
unchanged_lifts452 = get_all_lifts(all_unchanged_edges452)

# Check if new edges' lifts collide with unchanged edges' lifts
for label, old_removed, new_added, unchanged_lifts in [
    ("best72→452", changed72, changed452, unchanged_lifts452)]:
    print(f"\n{label}:")
    for u, v in new_added:
        new_lifts = set(c4_lift(u, v) + c4_lift(v, u))
        collisions = new_lifts & unchanged_lifts
        print(f"  New edge ({u:2d},{v:2d}): {len(new_lifts)} lift points, "
              f"{len(collisions)} collide with unchanged edges' lifts")
        for p in list(collisions)[:3]:
            print(f"    Collision at {p}")
    
    for u, v in old_removed:
        old_lifts = set(c4_lift(u, v) + c4_lift(v, u))
        collisions = old_lifts & unchanged_lifts
        print(f"  Old edge ({u:2d},{v:2d}): {len(old_lifts)} lift points, "
              f"{len(collisions)} collide with unchanged edges' lifts")
