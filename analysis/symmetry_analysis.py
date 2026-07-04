#!/usr/bin/env python3
"""
symmetry_analysis.py — Analyze symmetry properties of missing-center solutions.

For each solution in an RLE file, determine:
  1. What D4 symmetries it possesses
  2. Whether it's missing-center
  3. Cross-tabulation of symmetry × center status

D4 symmetries of the square (centered at grid center):
  - Identity (trivial)
  - Rot90: rotation by 90°
  - Rot180: rotation by 180°
  - Rot270: rotation by 270°
  - ReflectH: horizontal reflection (across vertical axis)
  - ReflectV: vertical reflection (across horizontal axis)
  - ReflectD1: reflection across main diagonal (y=x)
  - ReflectD2: reflection across anti-diagonal (y=-x)
"""

import sys
import os
import re
from collections import Counter, defaultdict


def parse_rle(content, n):
    """Parse RLE content into a list of (x,y) point lists."""
    solutions = []
    raw_sols = content.split('!')
    for raw in raw_sols:
        raw = raw.strip()
        if not raw:
            continue
        expanded = []
        i = 0
        while i < len(raw):
            if raw[i].isdigit():
                j = i
                while j < len(raw) and raw[j].isdigit():
                    j += 1
                count = int(raw[i:j])
                i = j
            else:
                count = 1
            if i < len(raw):
                ch = raw[i]
                if ch in 'bo':
                    expanded.append(ch * count)
                elif ch == '$':
                    expanded.append('\n')
                i += 1
        rle_str = ''.join(expanded)
        rows = rle_str.split('\n')
        pts = set()
        for r, row in enumerate(rows):
            if r >= n:
                break
            for c, ch in enumerate(row):
                if c >= n:
                    break
                if ch == 'o':
                    pts.add((c, r))
        pts_list = sorted(pts)
        if len(pts_list) == 2 * n:
            solutions.append(pts_list)
    return solutions


def check_missing_center(pts, n):
    """Check if grid center is NOT a circumcenter."""
    if n % 2 == 0:
        cx2, cy2 = n - 1, n - 1
    else:
        c = 2 * (n // 2)
        cx2, cy2 = c, c
    dist_counts = Counter()
    for x, y in pts:
        dx = 2 * x - cx2
        dy = 2 * y - cy2
        d = dx * dx + dy * dy
        dist_counts[d] += 1
    return max(dist_counts.values()) < 3


def transform_point(p, transform, n):
    """Apply a D4 transformation to a point (x,y)."""
    x, y = p
    if transform == 'id':
        return (x, y)
    elif transform == 'rot90':
        return (y, n - 1 - x)   # (x,y) -> (y, n-1-x)
    elif transform == 'rot180':
        return (n - 1 - x, n - 1 - y)
    elif transform == 'rot270':
        return (n - 1 - y, x)
    elif transform == 'refl_h':  # reflect across vertical axis (x -> n-1-x)
        return (n - 1 - x, y)
    elif transform == 'refl_v':  # reflect across horizontal axis (y -> n-1-y)
        return (x, n - 1 - y)
    elif transform == 'refl_d1': # reflect across main diagonal (y=x)
        return (y, x)
    elif transform == 'refl_d2': # reflect across anti-diagonal (y = n-1-x)
        return (n - 1 - y, n - 1 - x)
    return (x, y)


def check_symmetries(pts_set, n):
    """Check which D4 symmetries a solution possesses."""
    symmetries = {}
    for name in ['id', 'rot90', 'rot180', 'rot270',
                 'refl_h', 'refl_v', 'refl_d1', 'refl_d2']:
        transformed = set()
        for p in pts_set:
            transformed.add(transform_point(p, name, n))
        symmetries[name] = (transformed == pts_set)
    return symmetries


def classify_d4_symmetry(sym):
    """Classify into Flammenkamp's symmetry categories."""
    # All 8
    if all(sym.values()):
        return '* (all 8)'
    # Full C4 (quarter rotation) - rot90 implies all rotations
    if sym['rot90']:
        # Check for diagonal reflections too
        if sym['refl_d1'] and sym['refl_d2']:
            return 'o (C4 + both diagonals)'
        return 'c (C4, no diagonals)'
    # C2 (180° rotation)
    has_c2 = sym['rot180']
    # Reflection symmetries
    has_h = sym['refl_h']
    has_v = sym['refl_v']
    has_d1 = sym['refl_d1']
    has_d2 = sym['refl_d2']
    
    both_orth = has_h and has_v
    both_diag = has_d1 and has_d2
    one_diag = has_d1 or has_d2
    one_orth = has_h or has_v
    
    if has_c2:
        if both_orth:
            return '+ (C2 + both orthogonal)'
        if both_diag:
            return 'x (C2 + both diagonals)'
        if one_orth:
            return ': (C2 + 1 orthogonal)'
        if one_diag:
            return ': (C2 + 1 diagonal)'
        return ': (C2 only)'
    else:
        if both_orth and both_diag:
            # This would be * (all 8) which we already caught
            return '* (all 8)'
        if both_orth:
            return '+ (both orthogonal)'
        if both_diag:
            return 'x (both diagonals)'
        if one_diag:
            return '/ (1 diagonal)'
        if one_orth:
            return '- (1 orthogonal)'
        return '. (asymmetric)'


def main():
    if len(sys.argv) < 2:
        print("Usage: python symmetry_analysis.py <rle_file>")
        sys.exit(1)
    
    rle_path = sys.argv[1]
    basename = os.path.basename(rle_path)
    m = re.search(r'(\d+)\.out', basename)
    if not m:
        print("Cannot determine n from filename.")
        sys.exit(1)
    n = int(m.group(1))
    
    with open(rle_path, 'r') as f:
        content = f.read()
    
    solutions = parse_rle(content, n)
    print(f"n={n}: {len(solutions)} solutions loaded.")
    
    # Cross-tabulation
    sym_missing = Counter()
    sym_present = Counter()
    sym_total = Counter()
    
    missing_by_class = defaultdict(list)
    present_by_class = defaultdict(list)
    
    for idx, pts in enumerate(solutions):
        pts_set = set(pts)
        sym = check_symmetries(pts_set, n)
        cls = classify_d4_symmetry(sym)
        is_missing = check_missing_center(pts, n)
        
        sym_total[cls] += 1
        if is_missing:
            sym_missing[cls] += 1
            missing_by_class[cls].append(idx)
        else:
            sym_present[cls] += 1
            present_by_class[cls].append(idx)
    
    # Print symmetry categories
    categories = [
        '. (asymmetric)',
        '- (1 orthogonal)',
        '/ (1 diagonal)',
        ': (C2 only)',
        ': (C2 + 1 orthogonal)',
        ': (C2 + 1 diagonal)',
        '+ (both orthogonal)',
        'x (both diagonals)',
        'c (C4, no diagonals)',
        'o (C4 + both diagonals)',
        '* (all 8)',
    ]
    
    print(f"\n{'='*70}")
    print(f"Symmetry Analysis for n={n}")
    print(f"{'='*70}")
    print(f"{'Symmetry Class':<30s} {'Total':>8s} {'Missing':>10s} {'Present':>10s} {'Miss%':>8s}")
    print(f"{'-'*30} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")
    
    for cat in categories:
        if cat in sym_total:
            t = sym_total[cat]
            m = sym_missing.get(cat, 0)
            p = sym_present.get(cat, 0)
            pct = 100 * m / t if t > 0 else 0
            print(f"{cat:<30s} {t:>8d} {m:>10d} {p:>10d} {pct:>7.1f}%")
    
    total = sum(sym_total.values())
    total_m = sum(sym_missing.values())
    print(f"{'-'*30} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")
    print(f"{'TOTAL':<30s} {total:>8d} {total_m:>10d} {total - total_m:>10d} {100*total_m/total:>7.1f}%")
    
    # Missing-center solution symmetry distribution
    print(f"\n{'='*70}")
    print(f"Missing-Center Solution Symmetry Breakdown:")
    print(f"{'='*70}")
    for cat, indices in sorted(missing_by_class.items(), key=lambda x: -len(x[1])):
        print(f"  {cat}: {len(indices)} solutions (indices: {indices[:10]}{'...' if len(indices)>10 else ''})")
    
    # Check if missing-center solutions tend to have specific symmetries
    print(f"\n{'='*70}")
    print("Key Question: Do missing-center solutions have higher/lower symmetry?")
    print(f"{'='*70}")
    # Compute average "symmetry level" for missing vs present
    # Asymmetric = 0, reflection = 1, C2 = 2, C4 = 4, D4 = 8
    sym_level = {
        '. (asymmetric)': 0,
        '- (1 orthogonal)': 1,
        '/ (1 diagonal)': 1,
        ': (C2 only)': 2,
        ': (C2 + 1 orthogonal)': 3,
        ': (C2 + 1 diagonal)': 3,
        '+ (both orthogonal)': 4,
        'x (both diagonals)': 4,
        'c (C4, no diagonals)': 4,
        'o (C4 + both diagonals)': 8,
        '* (all 8)': 8,
    }
    
    def avg_sym(counts):
        total_s = sum(counts.values())
        if total_s == 0:
            return 0
        weighted = sum(sym_level.get(c, 0) * cnt for c, cnt in counts.items())
        return weighted / total_s
    
    avg_missing = avg_sym(sym_missing)
    avg_present = avg_sym(sym_present)
    avg_all = avg_sym(sym_total)
    
    print(f"  Average symmetry level (missing-center): {avg_missing:.2f}")
    print(f"  Average symmetry level (with center):    {avg_present:.2f}")
    print(f"  Average symmetry level (all solutions):  {avg_all:.2f}")
    print(f"  Ratio missing/all:                       {total_m/total:.3f}")


if __name__ == '__main__':
    main()
