#!/usr/bin/env python3
"""
D2 Spectrum: Deep analysis of circumcenter distributions.
Compare ALL missing-center vs has-center solutions for n=12,14.
"""
import sys, math
from collections import defaultdict, Counter
sys.path.insert(0, "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36")
from analyze_rle import parse_rle

def check_missing(pts, n):
    from collections import Counter
    cx2 = cy2 = n - 1
    dc = Counter()
    for x, y in pts:
        d = (2*x - cx2)**2 + (2*y - cy2)**2
        dc[d] += 1
    return max(dc.values()) <= 2

def circumcenter(p1, p2, p3):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    D = 2 * (x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
    if D == 0: return None
    x1sq = x1*x1 + y1*y1
    x2sq = x2*x2 + y2*y2
    x3sq = x3*x3 + y3*y3
    Ux = (x1sq*(y2-y3) + x2sq*(y3-y1) + x3sq*(y1-y2)) / D
    Uy = (x1sq*(x3-x2) + x2sq*(x1-x3) + x3sq*(x2-x1)) / D
    return (round(Ux, 8), round(Uy, 8))

def full_spectrum(pts):
    k = len(pts)
    cc = Counter()
    collinear = 0
    for i in range(k):
        for j in range(i+1, k):
            for m in range(j+1, k):
                c = circumcenter(pts[i], pts[j], pts[m])
                if c is None:
                    collinear += 1
                else:
                    cc[c] += 1
    return cc, collinear

def analyze_n(n, max_missing=20, max_regular=20):
    rle_file = f"D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/results_{n}.out"
    with open(rle_file) as f:
        sols = parse_rle(f.read(), n)
    
    print(f"n={n}: {len(sols)} total solutions")
    
    cx = cy = (n - 1) / 2  # grid center
    
    missing_sols = []
    regular_sols = []
    
    for pts in sols:
        if check_missing(pts, n):
            missing_sols.append(pts)
        else:
            regular_sols.append(pts)
    
    print(f"  {len(missing_sols)} missing-center, sampling {min(max_missing, len(missing_sols))}")
    print(f"  {len(regular_sols)} has-center, sampling {min(max_regular, len(regular_sols))}")
    
    # === Analysis 1: Spectra ===
    print(f"\n{'='*60}")
    print(f"Analysis 1: Circumcenter Spectrum Size")
    print(f"{'='*60}")
    
    m_sizes = []
    m_center_counts = []
    m_dist_to_center = []
    
    for pts in missing_sols[:max_missing]:
        cc, coll = full_spectrum(pts)
        m_sizes.append(len(cc))
        # Count center occurrences
        center_count = sum(cnt for (ux, uy), cnt in cc.items() 
                          if abs(ux-cx) < 0.001 and abs(uy-cy) < 0.001)
        m_center_counts.append(center_count)
        # Average distance to center
        avg_dist = sum(math.sqrt((ux-cx)**2 + (uy-cy)**2) for (ux, uy) in cc) / len(cc)
        m_dist_to_center.append(avg_dist)
    
    r_sizes = []
    r_center_counts = []
    r_dist_to_center = []
    
    for pts in regular_sols[:max_regular]:
        cc, coll = full_spectrum(pts)
        r_sizes.append(len(cc))
        center_count = sum(cnt for (ux, uy), cnt in cc.items()
                          if abs(ux-cx) < 0.001 and abs(uy-cy) < 0.001)
        r_center_counts.append(center_count)
        avg_dist = sum(math.sqrt((ux-cx)**2 + (uy-cy)**2) for (ux, uy) in cc) / len(cc)
        r_dist_to_center.append(avg_dist)
    
    if m_sizes:
        print(f"  Missing-center: avg {sum(m_sizes)/len(m_sizes):.0f} unique centers, "
              f"{sum(m_center_counts)/len(m_center_counts):.1f} at center, "
              f"avg dist from center={sum(m_dist_to_center)/len(m_dist_to_center):.2f}")
    if r_sizes:
        print(f"  Has-center:     avg {sum(r_sizes)/len(r_sizes):.0f} unique centers, "
              f"{sum(r_center_counts)/len(r_center_counts):.1f} at center, "
              f"avg dist from center={sum(r_dist_to_center)/len(r_dist_to_center):.2f}")
    
    # === Analysis 2: Do missing solutions share circumcenters? ===
    print(f"\n{'='*60}")
    print(f"Analysis 2: Shared Circumcenters Among Missing-Center Solutions")
    print(f"{'='*60}")
    
    if len(missing_sols) >= 2:
        all_m_cc = []
        for pts in missing_sols[:max_missing]:
            cc, _ = full_spectrum(pts)
            all_m_cc.append(set(cc.keys()))
        
        # Pairwise sharing
        total_pairs = 0
        total_shared = 0
        for i in range(len(all_m_cc)):
            for j in range(i+1, len(all_m_cc)):
                shared = len(all_m_cc[i] & all_m_cc[j])
                avg_size = (len(all_m_cc[i]) + len(all_m_cc[j])) / 2
                total_pairs += 1
                total_shared += shared
                if total_pairs <= 3:
                    print(f"    Pair ({i},{j}): {shared} shared / avg {avg_size:.0f} unique ({100*shared/avg_size:.1f}%)")
        
        print(f"    Avg sharing: {total_shared/total_pairs:.0f} centers ({100*total_shared/avg_size/total_pairs:.1f}%)")
    
    # === Analysis 3: Half-integer centers ===
    print(f"\n{'='*60}")
    print(f"Analysis 3: Circumcenter Coordinates Distribution")
    print(f"{'='*60}")
    
    # Check a single missing-center solution
    if missing_sols:
        cc, _ = full_spectrum(missing_sols[0])
        int_centers = sum(1 for (ux, uy) in cc if abs(ux-round(ux)) < 0.01 and abs(uy-round(uy)) < 0.01)
        half_int_centers = sum(1 for (ux, uy) in cc 
                              if (abs(ux-round(ux)-0.5) < 0.01 or abs(uy-round(uy)-0.5) < 0.01)
                              and not (abs(ux-round(ux)) < 0.01 and abs(uy-round(uy)) < 0.01))
        other_centers = len(cc) - int_centers - half_int_centers
        print(f"  Missing sol #0: {int_centers} integer, {half_int_centers} half-int, {other_centers} other")
    
    if regular_sols:
        cc, _ = full_spectrum(regular_sols[0])
        int_centers = sum(1 for (ux, uy) in cc if abs(ux-round(ux)) < 0.01 and abs(uy-round(uy)) < 0.01)
        half_int_centers = sum(1 for (ux, uy) in cc 
                              if (abs(ux-round(ux)-0.5) < 0.01 or abs(uy-round(uy)-0.5) < 0.01)
                              and not (abs(ux-round(ux)) < 0.01 and abs(uy-round(uy)) < 0.01))
        other_centers = len(cc) - int_centers - half_int_centers
        print(f"  Has-center sol #0: {int_centers} integer, {half_int_centers} half-int, {other_centers} other")
    
    # === Analysis 4: Unique to missing (vs regular) ===
    print(f"\n{'='*60}")
    print(f"Analysis 4: Circumcenter 'Signature' of Missing-Center Solutions")
    print(f"{'='*60}")
    
    # Combine spectra
    m_all = Counter()
    for pts in missing_sols[:max_missing]:
        cc, _ = full_spectrum(pts)
        for k, v in cc.items():
            m_all[k] += v
    
    r_all = Counter()
    for pts in regular_sols[:max_regular]:
        cc, _ = full_spectrum(pts)
        for k, v in cc.items():
            r_all[k] += v
    
    m_set = set(m_all.keys())
    r_set = set(r_all.keys())
    
    unique_to_missing = m_set - r_set
    unique_to_regular = r_set - m_set
    
    print(f"  {len(unique_to_missing)} circumcenters unique to missing-center solutions")
    print(f"  {len(unique_to_regular)} circumcenters unique to has-center solutions")
    print(f"  {len(m_set & r_set)} shared")
    
    if unique_to_missing:
        print(f"\n  Top 15 unique-to-missing circumcenters (by frequency):")
        for (ux, uy), cnt in sorted(m_all.items(), key=lambda x: -x[1]):
            if (ux, uy) in unique_to_missing:
                print(f"    ({ux:.4f}, {uy:.4f}): {cnt}")
    
    # Check center position
    center_key = (round(cx, 8), round(cy, 8))
    if center_key in m_set:
        print(f"\n  ⚠️ Grid center ({cx}, {cy}) appears as circumcenter in missing solutions! Count: {m_all[center_key]}")
    elif center_key in r_set:
        print(f"\n  ✅ Grid center ONLY in has-center solutions (count: {r_all[center_key]})")
    
    # === Analysis 5: Nearest center approaches ===
    print(f"\n{'='*60}")
    print(f"Analysis 5: Nearest circumcenters to grid center")
    print(f"{'='*60}")
    
    if missing_sols:
        cc, _ = full_spectrum(missing_sols[0])
        distances = [(math.sqrt((ux-cx)**2 + (uy-cy)**2), ux, uy) for (ux, uy) in cc]
        distances.sort()
        print(f"  Missing sol #0 - 10 nearest to center:")
        for dist, ux, uy in distances[:10]:
            print(f"    ({ux:.4f}, {uy:.4f}) d={dist:.4f}")
    
    if regular_sols:
        cc, _ = full_spectrum(regular_sols[0])
        distances = [(math.sqrt((ux-cx)**2 + (uy-cy)**2), ux, uy) for (ux, uy) in cc]
        distances.sort()
        print(f"\n  Has-center sol #0 - 10 nearest to center:")
        for dist, ux, uy in distances[:10]:
            print(f"    ({ux:.4f}, {uy:.4f}) d={dist:.4f}")


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    analyze_n(n, 20, 20)
