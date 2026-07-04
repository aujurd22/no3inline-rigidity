#!/usr/bin/env python3
"""
方向 1.3: 近缺失解分析 (Near-Missing Solutions)

从 RLE 数据中找出"几乎"缺失中心的解——只有一个距离环有 3 个点，
其他所有环都 ≤2。然后尝试通过局部列交换修复为真缺失中心解。

Usage:
    python near_missing.py <n> [--fix]
"""

import sys
from collections import defaultdict, Counter
from itertools import combinations
import math

sys.path.insert(0, "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36")
from analyze_rle import parse_rle

def check_center_profile(pts, n):
    """Returns (is_missing, max_count, ring_counts, culprit_rings)
    - is_missing: True if max_count <= 2
    - max_count: max points on any ring
    - ring_counts: {d: count} dict
    - culprit_rings: list of d values with count >= 3
    """
    cx2 = cy2 = n - 1
    ring_counts = Counter()
    for x, y in pts:
        d = (2*x - cx2)**2 + (2*y - cy2)**2
        ring_counts[d] += 1
    
    max_count = max(ring_counts.values())
    culprit_rings = [d for d, c in ring_counts.items() if c >= 3]
    is_missing = max_count <= 2
    
    return is_missing, max_count, dict(ring_counts), sorted(culprit_rings)


def collinear(p1, p2, p3):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    return x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2) == 0


def verify_no_collinear(pts):
    for i in range(len(pts)):
        for j in range(i+1, len(pts)):
            for k in range(j+1, len(pts)):
                if collinear(pts[i], pts[j], pts[k]):
                    return False
    return True


def fix_by_swap(pts, n):
    """Try swapping columns between two points in a near-missing solution
    to transform it into a true missing-center solution.
    
    Strategy: swap the column of one point on a culprit ring with
    the column of another point on a different row.
    """
    cx2 = cy2 = n - 1
    
    # Get ring profile
    _, _, ring_counts, culprit = check_center_profile(pts, n)
    if not culprit:
        return None  # already missing-center
    
    # Build points-by-ring data
    ring_points = defaultdict(list)
    for x, y in pts:
        d = (2*x - cx2)**2 + (2*y - cy2)**2
        ring_points[d].append((x, y))
    
    # Focus on culprit ring
    c_d = culprit[0]  # first culprit ring
    c_points = ring_points[c_d]  # points on this ring
    
    # For each pair of points on the culprit ring, try swapping one
    # with a point from a different ring
    
    # Group points by row
    row_points = defaultdict(list)
    for x, y in pts:
        row_points[y].append((x, y))
    
    fixed_solutions = []
    
    for i, (x1, y1) in enumerate(c_points):
        for x2, y2 in pts:
            if (x2, y2) in c_points and (x2, y2) != (x1, y1):
                continue  # would just swap within culprit ring
            if y1 == y2:
                continue  # same row - can't swap (would give 3 on same row)
            
            # Try swapping: point (x1,y1) takes column x2, and (x2,y2) takes column x1
            # But we need to also keep both rows with exactly 2 points
            # Actually, the simplest swap: exchange columns of (x1,y1) and (x2,y2)
            
            # Check: is (x2, y1) valid? (would the new point at row y1 with col x2 work?)
            # Check: is (x1, y2) valid? (would the new point at row y2 with col x1 work?)
            
            # Build new point set
            new_pts = []
            for x, y in pts:
                if (x, y) == (x1, y1):
                    new_pts.append((x2, y1))
                elif (x, y) == (x2, y2):
                    new_pts.append((x1, y2))
                else:
                    new_pts.append((x, y))
            
            # Verify constraints
            # Row count (must be 2 each)
            rc = Counter()
            cc = Counter()
            for x, y in new_pts:
                rc[y] += 1
                cc[x] += 1
            if max(rc.values()) > 2 or max(cc.values()) > 2:
                continue
            if any(v != 2 for v in rc.values()):
                continue
            if any(v != 2 for v in cc.values()):
                continue
            
            # Collinearity
            if not verify_no_collinear(new_pts):
                continue
            
            # Check if now missing-center
            is_miss, max_r, rc_new, _ = check_center_profile(new_pts, n)
            if is_miss:
                fixed_solutions.append(((x1,y1), (x2,y2), new_pts, max_r))
    
    return fixed_solutions if fixed_solutions else None


def analyze_n(n, max_sols=None):
    """Analyze near-missing solutions for given n."""
    rle_file = f"D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/results_{n}.out"
    
    with open(rle_file) as f:
        sols = parse_rle(f.read(), n)
    
    if max_sols:
        sols = sols[:max_sols]
    
    print(f"n={n}: {len(sols)} solutions total")
    
    # Classify solutions by their center profile
    categories = Counter()
    missing_indices = []
    near_missing_indices = []
    has_center_indices = []
    
    for idx, pts in enumerate(sols):
        is_miss, max_c, r_counts, culprits = check_center_profile(pts, n)
        
        if is_miss:
            categories['missing'] += 1
            missing_indices.append(idx)
        else:
            num_culprits = len(culprits)
            if num_culprits == 1 and max_c == 3:
                categories['near_missing'] += 1
                near_missing_indices.append(idx)
            elif num_culprits == 1:
                categories[f'1_ring_{max_c}pts'] += 1
            elif num_culprits == 2:
                categories['2_culprit_rings'] += 1
            else:
                categories[f'{num_culprits}_culprit_rings'] += 1
            has_center_indices.append(idx)
    
    print(f"\nCategories:")
    for cat, cnt in sorted(categories.items()):
        print(f"  {cat}: {cnt}")
    
    print(f"\n  Missing-center: {len(missing_indices)}")
    print(f"  Near-missing (1 ring × 3pts): {len(near_missing_indices)}")
    print(f"  Has center (other): {len(has_center_indices) - len(near_missing_indices)}")
    
    # Analyze near-missing solutions
    if near_missing_indices:
        print(f"\n{'='*60}")
        print(f"Near-Missing Solution Analysis")
        print(f"{'='*60}")
        
        culprit_dist = Counter()
        max_other_ring = []
        
        for idx in near_missing_indices[:10]:  # First 10
            pts = sols[idx]
            _, max_c, r_counts, culprits = check_center_profile(pts, n)
            c_d = culprits[0]
            
            # Which ring is the culprit?
            culprit_dist[c_d] += 1
            
            # What's the max count on OTHER rings?
            other_ring_counts = {d: c for d, c in r_counts.items() if d != c_d}
            max_other = max(other_ring_counts.values())
            max_other_ring.append(max_other)
            
            print(f"\n  Near-missing #{idx}: culprit d={c_d} ({r_counts[c_d]} pts)")
            print(f"    Ring profile:")
            for d, cnt in sorted(r_counts.items()):
                marker = " ← CULPRIT" if d == c_d else ""
                print(f"      d={d:4d}: {cnt} pts{marker}")
        
        print(f"\n  Culprit ring distribution:")
        for d, cnt in sorted(culprit_dist.items()):
            print(f"    d={d:4d}: {cnt} solutions")
        
        # Now try to fix near-missing solutions
        print(f"\n{'='*60}")
        print(f"Trying to fix near-missing solutions via column swap")
        print(f"{'='*60}")
        
        fixed_count = 0
        for idx in near_missing_indices[:5]:  # First 5
            pts = sols[idx]
            result = fix_by_swap(pts, n)
            if result:
                fixed_count += 1
                print(f"\n  ✅ Near-missing #{idx}: FOUND {len(result)} fix(es)!")
                for (p1, p2, new_pts, max_r) in result[:3]:  # Show first 3
                    print(f"    Swap {p1} ↔ {p2}: max_ring={max_r}")
            else:
                print(f"\n  ❌ Near-missing #{idx}: no fix found")
        
        print(f"\n  Total fixed: {fixed_count}/{min(len(near_missing_indices), 5)}")
    
    return {
        'missing': missing_indices,
        'near_missing': near_missing_indices,
        'has_center': has_center_indices,
    }


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    analyze_n(n)
