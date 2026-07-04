#!/usr/bin/env python3
"""
方向 3.1: 距离环共线图分析 (Ring Collinearity Graph)

把每个距离环看作图中的一个节点。如果两个环之间存在至少三组共线的点
（即从环A选两点、环B选一点，或从环A选一点、环B选两点，三点共线），
则两节点之间连一条有权边（权重=共线关系的数量）。

这个图能揭示：
1. 哪些环之间"冲突"最严重（共线风险最高）
2. 缺失中心解对应图中的哪种结构（独立集？团？）
3. n=12 时图结构是否有相变

Usage:
    python ring_coll_graph.py <n>
"""

import sys
from collections import defaultdict, Counter
from itertools import combinations
import math

sys.path.insert(0, "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36")
from analyze_rle import parse_rle


def build_rings(n):
    """Build distance rings and return {d: [(r,c), ...]}."""
    cx2 = cy2 = n - 1
    rings = defaultdict(list)
    for r in range(n):
        for c in range(n):
            d = (2*c - cx2)**2 + (2*r - cy2)**2
            rings[d].append((r, c))
    return dict(sorted(rings.items()))


def collinear(p1, p2, p3):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    return x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2) == 0


def build_collinearity_graph(rings):
    """
    Build the ring collinearity graph.
    Returns adjacency dict: d -> {other_d: collision_weight}
    where collision_weight = number of collinear triples involving
    points from both rings.
    """
    ring_list = sorted(rings.keys())
    ring_points = {d: pts for d, pts in rings.items()}
    
    # For efficiency, compute all collinearities in the grid
    # between ANY three grid points
    # This is O(n^6) for the full grid, too expensive.
    # Instead, compute ring-ring collisions.
    
    # A "collision" between ring A (da) and ring B (db) occurs when:
    # 1. Pick two points from A, one from B: 3 collinear
    # 2. Pick one from A, two from B: 3 collinear
    # Only count distinct collinear line alignments (not all point combos)
    
    graph = defaultdict(lambda: defaultdict(int))
    
    n = int(math.sqrt(sum(len(pts) for pts in rings.values())))
    
    for da in ring_list:
        pts_a = ring_points[da]
        if len(pts_a) < 2:
            continue
        
        for db in ring_list:
            if db <= da:
                continue
            pts_b = ring_points[db]
            if len(pts_b) < 1:
                continue
            
            # Count collisions: (point from B) lies on line through (p1,p2 from A)
            collision_count = 0
            collinear_pairs = set()
            
            # Case 1: Two from A, one from B
            for p1, p2 in combinations(pts_a, 2):
                for p3 in pts_b:
                    if collinear(p1, p2, p3):
                        # Collision! This line has two points from A and one from B
                        # Normalize the line representation
                        line = normalize_line(p1, p2, p3)
                        collinear_pairs.add(line)
            
            # Case 2: One from A, two from B 
            for p1 in pts_a:
                for p2, p3 in combinations(pts_b, 2):
                    if collinear(p1, p2, p3):
                        line = normalize_line(p1, p2, p3)
                        collinear_pairs.add(line)
            
            if collinear_pairs:
                graph[da][db] = len(collinear_pairs)
                graph[db][da] = len(collinear_pairs)
    
    return dict(graph)


def normalize_line(p1, p2, p3):
    """Normalize a line to a canonical representation."""
    # Get all three points, sort by x then y
    pts = sorted([p1, p2, p3])
    return tuple(pts)


def analyze_graph(graph, rings):
    """Analyze graph structure."""
    all_nodes = sorted(graph.keys())
    
    print(f"  Nodes (rings): {len(all_nodes)}")
    
    # Degree distribution
    degrees = {d: len(neighbors) for d, neighbors in graph.items()}
    total_possible = len(all_nodes) - 1
    
    print(f"  Degrees (vs {total_possible} possible):")
    for d in sorted(degrees.keys()):
        deg = degrees[d]
        ring_size = len(rings[d])
        print(f"    d={d:4d}: deg={deg:2d}/{total_possible} ({100*deg/total_possible:.0f}%), ring_size={ring_size:2d}")
    
    # Edge weight distribution
    print(f"\n  Edge weights (collision counts):")
    all_weights = []
    for d, neighbors in graph.items():
        for nd, w in neighbors.items():
            if nd > d:
                all_weights.append((d, nd, w))
    
    all_weights.sort(key=lambda x: -x[2])
    for d, nd, w in all_weights[:15]:
        print(f"    d={d:4d} - d={nd:4d}: weight={w}")
    
    # Ring size vs degree correlation
    print(f"\n  Ring size vs degree:")
    size_deg = [(len(rings[d]), degrees[d]) for d in all_nodes]
    print(f"    avg size: {sum(s for s, _ in size_deg)/len(size_deg):.1f}")
    print(f"    avg deg:  {sum(d for _, d in size_deg)/len(size_deg):.1f}")
    
    # Find missing-center solution's "ring usage" and check against graph
    return graph


def check_against_missing_solutions(graph, rings, n):
    """
    For each missing-center solution, compute its ring set and
    check how it relates to the collinearity graph.
    """
    rle_file = f"D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/results_{n}.out"
    with open(rle_file) as f:
        sols = parse_rle(f.read(), n)
    
    def check_missing(pts, n):
        cx2 = cy2 = n - 1
        dc = Counter()
        for x, y in pts:
            d = (2*x - cx2)**2 + (2*y - cy2)**2
            dc[d] += 1
        return max(dc.values()) <= 2, dict(dc)
    
    missing_rings = []
    has_center_rings = []
    
    for pts in sols:
        is_miss, dc = check_missing(pts, n)
        used_rings = set(d for d, c in dc.items() if c > 0)
        if is_miss:
            missing_rings.append(used_rings)
        else:
            has_center_rings.append(used_rings)
    
    # Analyze: are missing-center solution's ring sets maximal independent
    # sets in the collinearity graph?
    # (i.e., no two used rings that have a collision edge between them)
    
    print(f"\n{'='*60}")
    print(f"Missing-Center Solutions vs Collinearity Graph")
    print(f"{'='*60}")
    print(f"  {len(missing_rings)} missing, {len(has_center_rings)} has-center")
    
    # Check: what fraction of used ring pairs have a collision edge?
    for label, ring_sets in [("Missing", missing_rings), ("HasCenter", has_center_rings[:50])]:
        collision_pairs = 0
        total_pairs = 0
        
        for rset in ring_sets:
            ring_list = sorted(rset)
            for i in range(len(ring_list)):
                for j in range(i+1, len(ring_list)):
                    total_pairs += 1
                    da, db = ring_list[i], ring_list[j]
                    if da in graph and db in graph[da]:
                        collision_pairs += 1
        
        if total_pairs > 0:
            print(f"  {label}: {collision_pairs}/{total_pairs} ring-pairs collide ({100*collision_pairs/total_pairs:.1f}%)")
    
    # What about skipped rings? Do they have many conflicts with used rings?
    print(f"\n  Skipped rings in missing-center solutions:")
    all_rings = set(rings.keys())
    avg_collisions_with_used = []
    
    for rset in missing_rings[:5]:
        skipped = all_rings - rset
        for sd in skipped:
            collisions = 0
            for ud in rset:
                if sd in graph and ud in graph[sd]:
                    collisions += graph[sd][ud]
            avg_collisions_with_used.append((sd, collisions, len(rset)))
    
    # Average collisions per skipped ring (across first 5 missing solutions)
    if avg_collisions_with_used:
        top_skipped = Counter()
        for sd, coll, _ in avg_collisions_with_used:
            top_skipped[sd] += coll
        print(f"    Most-colliding skipped rings:")
        for sd, coll in top_skipped.most_common(10):
            print(f"      d={sd:4d}: avg {coll/5:.0f} collisions with used rings")


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    
    print(f"{'='*60}")
    print(f"Ring Collinearity Graph Analysis: n={n}")
    print(f"{'='*60}")
    
    rings = build_rings(n)
    print(f"\nBuilding graph ({len(rings)} rings)...")
    
    graph = build_collinearity_graph(rings)
    
    print(f"Graph built: {sum(len(v) for v in graph.values())//2} edges")
    
    analyze_graph(graph, rings)
    check_against_missing_solutions(graph, rings, n)
