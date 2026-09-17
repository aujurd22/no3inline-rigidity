"""
Circumcircle analysis for rot4 NTIL solutions.
For each m=5..19 with known solutions:
  1. Lift m cells to 4m C4-symmetric points
  2. For every triple (i,j,k) among 4m points, compute the circumcenter
  3. Count how many triples produce (near) the same circumcenter = "thick" circles
  4. Check if thick-circle centers are collinear / have directional patterns
"""

import json, math, os, sys
from collections import defaultdict, Counter

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def circumcenter(p1, p2, p3):
    """Compute circumcenter. Returns None if collinear."""
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    d = 2 * (x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
    if abs(d) < 1e-12:
        return None
    s1, s2, s3 = x1*x1+y1*y1, x2*x2+y2*y2, x3*x3+y3*y3
    ux = (s1*(y2-y3) + s2*(y3-y1) + s3*(y1-y2)) / d
    uy = (s1*(x3-x2) + s2*(x1-x3) + s3*(x2-x1)) / d
    return (ux, uy)

def radius_sq(center, p):
    cx, cy = center
    px, py = p
    return (px-cx)**2 + (py-cy)**2

def analyze_circles(m, cells):
    N = 2 * m
    pts = [c4(c, r, N) for c in cells for r in range(4)]
    n = len(pts)
    
    print(f"m={m}: {n} points, C({n},3) = {n*(n-1)*(n-2)//6} triples")
    
    # Count circumcenters by rounding to 0.5 grid
    center_counts = Counter()
    # Also track: which pair basis produced each center
    center_pairs = defaultdict(set)  # (rx,ry) -> set of (i,j) pairs
    
    checked = 0
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                cc = circumcenter(pts[i], pts[j], pts[k])
                if cc:
                    checked += 1
                    # Round to 0.5 grid for clustering
                    rx, ry = round(cc[0]*2)/2, round(cc[1]*2)/2
                    center_counts[(rx, ry)] += 1
                    center_pairs[(rx, ry)].add((min(i,j), max(i,j)))
                    center_pairs[(rx, ry)].add((min(i,k), max(i,k)))
                    center_pairs[(rx, ry)].add((min(j,k), max(j,k)))
    
    # Top "thick" circles
    top_n = min(30, len(center_counts))
    top_centers = center_counts.most_common(top_n)
    
    print(f"  Total non-collinear triples: {checked}")
    print(f"  Distinct circumcenters (rounded): {len(center_counts)}")
    print(f"  Top {top_n} thickest circles:")
    for (cx, cy), cnt in top_centers[:10]:
        n_pairs = len(center_pairs[(cx, cy)])
        print(f"    center=({cx:.1f},{cy:.1f}): {cnt:5d} triples, {n_pairs} distinct pairs")
    
    return {
        'm': m,
        'n_pts': n,
        'n_triples': n*(n-1)*(n-2)//6,
        'n_noncollinear': checked,
        'n_distinct_centers': len(center_counts),
        'top_centers': [(list(c), int(cnt)) for c, cnt in top_centers],
        'center_pairs': {str(c): len(center_pairs[c]) for c, _ in top_centers},
        'grid_center': ((N-1)/2, (N-1)/2)
    }

def find_collinear_centers(center_list, threshold_deg=5):
    """Check if a set of points is approximately collinear."""
    if len(center_list) < 3:
        return None
    
    pts = center_list[:10]  # Use top 10
    # For each pair as baseline, check if all other points are near the line
    best_alignment = 0
    best_dir = None
    
    for a in range(len(pts)):
        for b in range(a+1, len(pts)):
            x1, y1 = pts[a]
            x2, y2 = pts[b]
            dx, dy = x2-x1, y2-y1
            length = math.hypot(dx, dy)
            if length < 0.5: continue
            
            # Count how many other points are within 1 unit of this line
            aligned = 2
            for c in range(len(pts)):
                if c == a or c == b: continue
                x0, y0 = pts[c]
                # Distance from point to line
                dist = abs(dx*(y1-y0) - dy*(x1-x0)) / length
                if dist < 1.0:
                    aligned += 1
            
            if aligned > best_alignment:
                best_alignment = aligned
                best_dir = (dx/max(length,1e-12), dy/max(length,1e-12))
    
    return best_alignment, best_dir

def main():
    sol_dir = 'results/solutions'
    out = {}
    
    for fname in sorted(os.listdir(sol_dir)):
        if not fname.endswith('.json'): continue
        data = json.load(open(f'{sol_dir}/{fname}'))
        if 'cells' not in data: continue
        cells = data['cells']
        m = data.get('m', len(cells))
        
        result = analyze_circles(m, cells)
        out[str(m)] = result
        
        # Check collinearity of top centers
        top_pts = [list(c) for c, _ in result['top_centers']]
        coll = find_collinear_centers(top_pts)
        if coll:
            align, (dx, dy) = coll
            angle = math.degrees(math.atan2(dy, dx))
            print(f"  Collinearity of top centers: {align}/{min(10,len(top_pts))} aligned, "
                  f"direction ≈ {angle:.0f}° from horizontal")
        
        # Compute distance from grid center
        gc = result['grid_center']
        top_with_dist = []
        for c, cnt in result['top_centers']:
            cx, cy = c
            d = math.hypot(cx-gc[0], cy-gc[1])
            top_with_dist.append((c, cnt, d))
        top_with_dist.sort(key=lambda x: -x[1])
        print(f"  Top center distances from grid center ({gc[0]:.1f},{gc[1]:.1f}):")
        for c, cnt, d in top_with_dist[:5]:
            print(f"    center=({c[0]:.1f},{c[1]:.1f}): count={cnt}, dist={d:.1f}")
        print()
    
    json.dump(out, open('results/circumcenter_analysis.json', 'w'), indent=1)

if __name__ == '__main__':
    main()
