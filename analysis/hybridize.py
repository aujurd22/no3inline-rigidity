#!/usr/bin/env python3
"""
方向 1.2: 双解杂交实验 (Solution Hybridization)

取两个缺失中心解，将解 A 的前 k 行与解 B 的后 n-k 行拼接，
检查是否能生成新的有效解（甚至缺失中心解）。

Usage:
    python hybridize.py <n>
"""

import sys
from collections import defaultdict, Counter

sys.path.insert(0, "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36")
from analyze_rle import parse_rle

def check_missing(pts, n):
    cx2 = cy2 = n - 1
    dc = Counter()
    for x, y in pts:
        d = (2*x - cx2)**2 + (2*y - cy2)**2
        dc[d] += 1
    return max(dc.values()) <= 2, dict(dc)

def collinear(p1, p2, p3):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    return x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2) == 0

def verify(pts, n):
    """Full verification: returns (ok, reason)."""
    k = len(pts)
    if k != 2 * n:
        return False, f"wrong size: {k}"
    
    row_cnt = Counter()
    col_cnt = Counter()
    for x, y in pts:
        row_cnt[y] += 1
        col_cnt[x] += 1
    
    if any(v != 2 for v in row_cnt.values()):
        return False, f"row counts wrong: {dict(row_cnt)}"
    if any(v != 2 for v in col_cnt.values()):
        return False, f"col counts wrong: {dict(col_cnt)}"
    
    for i in range(k):
        for j in range(i+1, k):
            for m in range(j+1, k):
                if collinear(pts[i], pts[j], pts[m]):
                    return False, f"collinear: {pts[i]}, {pts[j]}, {pts[m]}"
    
    return True, "OK"


def pts_to_rows(pts, n):
    """Convert flat point list to row dict {row: [col1, col2]}."""
    by_row = defaultdict(list)
    for x, y in pts:
        by_row[y].append(x)
    return dict(by_row)


def hybridize(solution_a, solution_b, n, k):
    """Take first k rows from A, last n-k rows from B.
    Then fix column counts by swapping where needed.
    Returns list of valid solutions found.
    """
    rows_a = pts_to_rows(solution_a, n)
    rows_b = pts_to_rows(solution_b, n)
    
    # Simple hybrid: take rows 0..k-1 from A, rows k..n-1 from B
    hybrid = []
    for r in range(n):
        if r < k:
            for c in rows_a[r]:
                hybrid.append((c, r))
        else:
            for c in rows_b[r]:
                hybrid.append((c, r))
    
    # Verify basic constraints
    rc = Counter()
    cc = Counter()
    for x, y in hybrid:
        rc[y] += 1
        cc[x] += 1
    
    if max(rc.values()) > 2:
        return []  # some row has >2
    if any(v < 2 for v in rc.values()):
        return []  # some row has <2
    if max(cc.values()) > 2:
        return []  # some col has >2
    
    # If column counts aren't all 2, try to fix by swapping within rows
    # that have columns outside the valid set
    problems = [c for c, cnt in cc.items() if cnt != 2]
    
    if len(problems) == 0:
        # All good! Check collinearity
        ok, reason = verify(hybrid, n)
        if ok:
            is_miss, _ = check_missing(hybrid, n)
            return [(hybrid, is_miss, "perfect")]
        return []
    
    # Need to fix column imbalances
    # Find rows with "wrong" columns and swap
    extra_cols = [c for c, cnt in cc.items() if cnt > 2]
    missing_cols = [c for c, cnt in cc.items() if cnt < 2]
    
    # Also columns with count 0 that should have count 2
    all_cols = set(range(n))
    used_cols = set(cc.keys())
    zero_cols = [c for c in all_cols if c not in used_cols]
    missing_cols.extend(zero_cols)
    
    # For each extra column, find where it appears and try to replace with missing
    results = []
    
    # Simple strategy: find a row that has an extra column and a missing column
    # and swap that column
    for extra_c in extra_cols:
        rows_with_extra = [y for (x, y) in hybrid if x == extra_c]
        for r in rows_with_extra:
            for miss_c in missing_cols:
                # Can we replace extra_c with miss_c at row r?
                new_hybrid = []
                for x, y in hybrid:
                    if (x, y) == (extra_c, r):
                        new_hybrid.append((miss_c, r))
                    else:
                        new_hybrid.append((x, y))
                
                ok, reason = verify(new_hybrid, n)
                if ok:
                    is_miss, _ = check_missing(new_hybrid, n)
                    tag = "missing" if is_miss else "has_center"
                    results.append((new_hybrid, is_miss, f"swap {extra_c}→{miss_c} at row {r}"))
    
    return results


def analyze_hybrids(n, max_pairs=10):
    """Try hybridizing pairs of missing-center solutions."""
    rle_file = f"D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/results_{n}.out"
    with open(rle_file) as f:
        sols = parse_rle(f.read(), n)
    
    # Find missing-center solutions
    missing = []
    for pts in sols:
        is_miss, _ = check_missing(pts, n)
        if is_miss:
            missing.append(pts)
    
    print(f"n={n}: {len(missing)} missing-center solutions")
    print(f"Trying hybridizations (first {max_pairs} pairs)...\n")
    
    results_summary = []
    
    for i in range(min(len(missing), max_pairs)):
        for j in range(i+1, min(len(missing), max_pairs)):
            a = missing[i]
            b = missing[j]
            
            for k in range(1, n):
                results = hybridize(a, b, n, k)
                if results:
                    for hybrid_pts, is_miss, method in results:
                        tag = "✅ Missing!" if is_miss else "Has center"
                        results_summary.append((i, j, k, is_miss, method))
                        print(f"  {tag} Pair ({i},{j}) k={k}: {method}")
    
    if not results_summary:
        print("  No valid hybrids found.")
    else:
        missing_hybrids = sum(1 for r in results_summary if r[3])
        print(f"\nSummary: {len(results_summary)} valid hybrids, {missing_hybrids} missing-center")
    
    return results_summary


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    analyze_hybrids(n)
