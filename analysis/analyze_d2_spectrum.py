#!/usr/bin/env python3
"""
Direction 2: Circumcircle Spectrum Analysis.
Compute ALL triple circumcenters for missing-center and has-center solutions,
compare their distributions and look for structural patterns.
"""

import sys
from collections import defaultdict, Counter
import math

sys.path.insert(0, "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36")
from analyze_rle import parse_rle, check_missing_center

def build_rings(n):
    from collections import defaultdict
    cx2 = cy2 = n - 1
    rings = defaultdict(list)
    for r in range(n):
        for c in range(n):
            d = (2*c - cx2)**2 + (2*r - cy2)**2
            rings[d].append((r, c))
    return dict(sorted(rings.items()))

def circumcenter(p1, p2, p3):
    """Compute circumcenter of three points.
    Returns (cx_num_x, cx_num_y, denom) as reduced fractions.
    Uses floating point for speed, then rounds to check for exactness.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    
    # Compute using integer arithmetic where possible
    # D = 2 * (x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
    D = x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)
    
    if D == 0:
        return None  # Collinear
    
    D2 = 2 * D
    
    x1sq = x1*x1 + y1*y1
    x2sq = x2*x2 + y2*y2
    x3sq = x3*x3 + y3*y3
    
    Ux_num = x1sq * (y2 - y3) + x2sq * (y3 - y1) + x3sq * (y1 - y2)
    Uy_num = x1sq * (x3 - x2) + x2sq * (x1 - x3) + x3sq * (x2 - x1)
    
    # The circumcenter is at (Ux_num / D2, Uy_num / D2)
    # Reduce fraction
    gx = math.gcd(abs(Ux_num), abs(D2)) if Ux_num != 0 else abs(D2)
    gy = math.gcd(abs(Uy_num), abs(D2)) if Uy_num != 0 else abs(D2)
    
    cx_num = Ux_num // gx
    cy_num = Uy_num // gy
    denom = D2 // gx  # same denominator (after reduction)
    
    # Actually, denominators might differ after reduction
    # Return as fractions
    return (Ux_num, Uy_num, D2)


def circumcenter_float(p1, p2, p3):
    """Compute circumcenter as float values."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    
    D = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if D == 0:
        return None
    
    x1sq = x1*x1 + y1*y1
    x2sq = x2*x2 + y2*y2
    x3sq = x3*x3 + y3*y3
    
    Ux = (x1sq * (y2 - y3) + x2sq * (y3 - y1) + x3sq * (y1 - y2)) / D
    Uy = (x1sq * (x3 - x2) + x2sq * (x1 - x3) + x3sq * (x2 - x1)) / D
    
    return (Ux, Uy)


def analyze_spectrum(pts, label=""):
    """Compute the circumcenter spectrum for a set of points."""
    k = len(pts)
    
    # Track all circumcenters (as floats rounded to 6dp for grouping)
    cc_float_counts = Counter()
    cc_exact = {}  # (x, y) -> count
    
    total_triples = 0
    collinear_count = 0
    center_count = 0
    
    grid_center = ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)
    # Actually, grid center is fixed for the grid: (n-1)/2, (n-1)/2
    # Let's approximate from min/max
    
    min_x = min(p[0] for p in pts)
    max_x = max(p[0] for p in pts)
    min_y = min(p[1] for p in pts)
    max_y = max(p[1] for p in pts)
    n = max_x + 1  # grid size
    
    cx = cy = (n - 1) / 2  # grid center
    
    for i in range(k):
        for j in range(i + 1, k):
            for m in range(j + 1, k):
                total_triples += 1
                result = circumcenter_float(pts[i], pts[j], pts[m])
                if result is None:
                    collinear_count += 1
                    continue
                
                ux, uy = result
                # Round to 6 decimal places for grouping
                key = (round(ux, 6), round(uy, 6))
                cc_float_counts[key] += 1
                
                # Check if center
                if abs(ux - cx) < 0.001 and abs(uy - cy) < 0.001:
                    center_count += 1
    
    return {
        'total_triples': total_triples,
        'collinear': collinear_count,
        'center_triples': center_count,
        'unique_centers': len(cc_float_counts),
        'cc_counts': cc_float_counts,  # { (x,y): frequency }
        'most_common': cc_float_counts.most_common(10),
    }


# ============ Main Analysis ============

def analyze_n(n, max_sols=20):
    """Analyze circumcenter spectrum for n×n grid solutions."""
    rle_file = f"D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/results_{n}.out"
    
    with open(rle_file) as f:
        text = f.read()
    
    sols = parse_rle(text, n)
    print(f"n={n}: {len(sols)} solutions total")
    
    missing = []
    has_center = []
    
    for pts in sols[:max_sols]:
        result = check_missing_center(pts, n)
        if isinstance(result, tuple):
            is_miss = result[0]
        else:
            is_miss = result
        
        if is_miss:
            missing.append(pts)
        else:
            has_center.append(pts)
        
        if len(missing) >= 5 and len(has_center) >= 5:
            break
    
    print(f"  {len(missing)} missing-center, {len(has_center)} has-center (analyzed)")
    
    # Analyze up to 5 of each
    m_results = []
    for i, pts in enumerate(missing[:5]):
        spec = analyze_spectrum(pts, f"Missing #{i}")
        m_results.append(spec)
    
    c_results = []
    for i, pts in enumerate(has_center[:5]):
        spec = analyze_spectrum(pts, f"HasCenter #{i}")
        c_results.append(spec)
    
    if m_results:
        avg_m_center = sum(r['center_triples'] for r in m_results) / len(m_results)
        avg_m_unique = sum(r['unique_centers'] for r in m_results) / len(m_results)
        print(f"\n  Missing-center solutions (avg of {len(m_results)}):")
        print(f"    Total triples: {m_results[0]['total_triples']}")
        print(f"    Center triples: {avg_m_center:.1f} (should be 0)")
        print(f"    Unique circumcenters: {avg_m_unique:.0f}")
        print(f"    Collinear triples: {m_results[0]['collinear']}")
        
        # Most common circumcenters across missing-center solutions
        combined_cc = Counter()
        for r in m_results:
            for cc, cnt in r['cc_counts'].items():
                combined_cc[cc] += cnt
        print(f"\n    Top 10 circumcenters (all missing sols combined):")
        for (cx, cy), cnt in combined_cc.most_common(10):
            print(f"      ({cx:.4f}, {cy:.4f}): {cnt}")
    
    if c_results:
        avg_c_center = sum(r['center_triples'] for r in c_results) / len(c_results)
        avg_c_unique = sum(r['unique_centers'] for r in c_results) / len(c_results)
        print(f"\n  Has-center solutions (avg of {len(c_results)}):")
        print(f"    Total triples: {c_results[0]['total_triples']}")
        print(f"    Center triples: {avg_c_center:.1f}")
        print(f"    Unique circumcenters: {avg_c_unique:.0f}")
        print(f"    Collinear triples: {c_results[0]['collinear']}")
        
        combined_cc_c = Counter()
        for r in c_results:
            for cc, cnt in r['cc_counts'].items():
                combined_cc_c[cc] += cnt
        print(f"\n    Top 10 circumcenters (all has-center sols combined):")
        for (cx, cy), cnt in combined_cc_c.most_common(10):
            print(f"      ({cx:.4f}, {cy:.4f}): {cnt}")


# Also: detailed comparison of two specific solutions (one missing, one has-center)

def detailed_comparison(n):
    """Compare one missing-center and one has-center solution in detail."""
    rle_file = f"D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/results_{n}.out"
    
    with open(rle_file) as f:
        text = f.read()
    
    sols = parse_rle(text, n)
    
    missing_sol = None
    center_sol = None
    
    for pts in sols:
        result = check_missing_center(pts, n)
        is_miss = result[0] if isinstance(result, tuple) else result
        missing_sol = pts  # Use first one regardless for comparison
    
    # Pick first two solutions for comparison
    if len(sols) >= 2:
        spec1 = analyze_spectrum(sols[0], "Solution #0")
        spec2 = analyze_spectrum(sols[1], "Solution #1")
        
        print(f"\n  Detailed comparison of two n={n} solutions:")
        print(f"    Sol#0: {spec1['unique_centers']} unique centers, {spec1['center_triples']} at grid center")
        print(f"    Sol#1: {spec2['unique_centers']} unique centers, {spec2['center_triples']} at grid center")
        
        # Find common circumcenters
        common = set(spec1['cc_counts'].keys()) & set(spec2['cc_counts'].keys())
        print(f"    Shared circumcenters: {len(common)}")
        
        # What about half-integer centers?
        half_int1 = sum(1 for (cx, cy) in spec1['cc_counts'] 
                       if abs(cx - round(cx)) == 0.5 or abs(cy - round(cy)) == 0.5)
        half_int2 = sum(1 for (cx, cy) in spec2['cc_counts']
                       if abs(cx - round(cx)) == 0.5 or abs(cy - round(cy)) == 0.5)
        print(f"    Half-int centers: Sol#0={half_int1}, Sol#1={half_int2}")


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    max_sols = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    print(f"={60*'='}")
    print(f"Direction 2: Circumcircle Spectrum Analysis for n={n}")
    print(f"={60*'='}")
    
    analyze_n(n, max_sols=max_sols)
    print()
    detailed_comparison(n)
