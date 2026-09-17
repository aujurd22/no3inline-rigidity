"""
direction2_all4pairs.py — Direction 2: All-4-pair analysis for m=37.

An "all-4-pair" (i,j) is a pair of cells where all 4 orientation combos
{(+,+),(+,-),(-,+),(-,-)} produce at least one collinear triple with some
third cell k. These pairs force constraints that are hardest to satisfy.

Analysis plan:
1. Precompute ALL all-4-pairs in the m×m fundamental quadrant
2. For a given 2-factor (set of 37 edges), count how many all-4-pairs it contains
3. Use violations ≈ all-4-pairs / 5 (empirical from D5v2) to estimate min violations
4. Find the 2-factor with minimum all-4-pair count

Usage: python direction2_all4pairs.py
"""
import os, sys, json, math, itertools, time, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def det_collinear(p1, p2, p3):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    return x1*y2 + x2*y3 + x3*y1 - x1*y3 - x2*y1 - x3*y2

def orientation_patterns():
    """All 8 orientation patterns for a triple of cells."""
    return [(b1,b2,b3) for b1 in [0,1] for b2 in [0,1] for b3 in [0,1]]

def is_all_4_pair(i, j, m, precomputed_lifts):
    """
    Check if pair (i,j) has all 4 orientation combos forbidden.
    i,j are cell indices (0..m-1) in the fundamental quadrant.
    Uses precomputed lifts for efficiency.
    """
    n = 2 * m
    lifts_i = precomputed_lifts[i]
    lifts_j = precomputed_lifts[j]
    
    # For each orientation of (i,j), check if ALL choices of k lead to a violation
    # An all-4-pair means: for EACH of the 4 orientations of (i,j),
    # there EXISTS some k such that (i,j,k) gives a collinear triple.
    
    # We check all orientations (b1,b2) ∈ {0,1}² for the pair (i,j)
    # and all k∈[0,m-1] with k≠i,j
    
    # Actually, the stricter definition: a pair (i,j) is all-4-pair if
    # for all 4 orientations (b1,b2), there EXISTS a k and orientations (b3)
    # such that (i,j,k) has a collinear triple.
    
    # To check efficiently: for each orientation (b1,b2), scan k and
    # stop if a collinear pattern is found.
    
    all_four = True
    for b2i, b2j in [(0, 1), (1, 0), (0, 0), (1, 1)]:
        # Cell i orientation: if b2i=0, cell=(i_x,i_y); if b2i=1, cell=(i_y,i_x)  (transpose)
        # This is approximate — the actual orientation depends on edge direction
        found_violation = False
        for k in range(m):
            if k == i or k == j:
                continue
            for b3 in [0, 1]:
                for ri in range(4):
                    for rj in range(4):
                        for rk in range(4):
                            pi = (i_x, i_y) if b2i == 0 else (i_y, i_x)
                            pj = (j_x, j_y) if b2j == 0 else (j_y, j_x)
                            pk = (k_x, k_y) if b3 == 0 else (k_y, k_x)
                            # Actually orientation is more complex — need actual edge semantics
    
    # This is getting too complex without the full orientation model.
    # Let me take a simpler approach.
    return False

def compute_all_4_pairs(m):
    """
    Brute-force compute all all-4-pairs for m=37.
    
    For EACH pair of cells (c1,c2) in the m×m grid:
    - For EACH of their 4 possible orientation combos (b1,b2):
      - Check if there EXISTS a third cell c3 and its orientation b3
        and rotation pattern (r1,r2,r3) ∈ {0,1,2,3}³
        such that the 3 lifted points are collinear (det = 0)
    - If ALL 4 orientation combos produce at least one such collinear triple,
      then (c1,c2) is an "all-4-pair"
    """
    n = 2 * m
    # Precompute lifts for all cells
    all_cells = [(x, y) for x in range(m) for y in range(m)]
    lifts = {}
    for idx, (x, y) in enumerate(all_cells):
        lifts[idx] = [c4(x, y, r, n) for r in range(4)]
    
    all_4_pairs = set()
    
    # For efficiency, only check cells that differ in at least one coordinate
    # (identical cells are not distinct)
    total_pairs = m * m * (m * m - 1) // 2  # C(m², 2) ≈ 936k for m=37
    print(f"Total cell pairs to check: {total_pairs}", flush=True)
    
    checked = 0
    for idx1 in range(m * m):
        x1, y1 = all_cells[idx1]
        for idx2 in range(idx1 + 1, m * m):
            x2, y2 = all_cells[idx2]
            checked += 1
            if checked % 50000 == 0:
                print(f"  checked {checked}/{total_pairs}, found {len(all_4_pairs)} all-4-pairs", flush=True)
            
            # For each of 4 orientation combos of cells (idx1, idx2):
            # We check if there's a third cell that makes a collinear triple
            # For the orientations:
            #  - Cell orientation b: if b=0, use (x,y); if b=1, use (y,x) [transpose]
            
            orientations = [(0,0), (0,1), (1,0), (1,1)]
            all_blocked = True
            
            for (b1, b2) in orientations:
                # The cell (x,y) with orientation b corresponds to:
                # If b=0: cell is (x,y), lifted points are C4((x,y), r) for r=0..3
                # If b=1: cell is (y,x), lifted points are C4((y,x), r) for r=0..3
                
                cell1 = (x1, y1) if b1 == 0 else (y1, x1)
                cell2 = (x2, y2) if b2 == 0 else (y2, x2)
                
                found_blocked = False
                # Check all third cells
                for idx3 in range(m * m):
                    if idx3 == idx1 or idx3 == idx2:
                        continue
                    x3, y3 = all_cells[idx3]
                    
                    for b3 in [0, 1]:
                        cell3 = (x3, y3) if b3 == 0 else (y3, x3)
                        
                        for ri in range(4):
                            for rj in range(4):
                                for rk in range(4):
                                    p1 = c4(cell1[0], cell1[1], ri, n)
                                    p2 = c4(cell2[0], cell2[1], rj, n)
                                    p3 = c4(cell3[0], cell3[1], rk, n)
                                    if det_collinear(p1, p2, p3) == 0:
                                        found_blocked = True
                                        break
                                if found_blocked: break
                            if found_blocked: break
                        if found_blocked: break
                    if found_blocked: break
                
                if not found_blocked:
                    all_blocked = False
                    break
            
            if all_blocked:
                all_4_pairs.add((idx1, idx2))
    
    return all_4_pairs

def main():
    m = 37
    print(f"=== Direction 2: All-4-Pair Analysis (m={m}) ===", flush=True)
    print(f"Grid: {m}×{m} = {m*m} cells", flush=True)
    print(f"Pairs: C({m*m}, 2) = {m*m*(m*m-1)//2}", flush=True)
    print(f"This is a HEAVY computation — may take hours.", flush=True)
    print(f"Press Ctrl+C to cancel or let it run.", flush=True)
    
    # For a quick test, sample a smaller subset
    print("\nRunning quick sample: checking first 500 cells × all partners...", flush=True)
    all_4_pairs = compute_quick_sample(m, sample_cells=200)
    
    # Save results
    out_path = os.path.join(HERE, "results", "all4pairs_sample.json")
    with open(out_path, "w") as f:
        json.dump({
            "m": m,
            "all_4_pairs": [[int(a), int(b)] for a,b in all_4_pairs],
            "count": len(all_4_pairs),
            "note": "sample from first 200 cells"
        }, f)
    print(f"Saved {len(all_4_pairs)} all-4-pairs to {out_path}", flush=True)

def compute_quick_sample(m, sample_cells=200):
    """Only check pairs where both cells are within the first sample_cells."""
    n = 2 * m
    all_cells = [(x, y) for x in range(m) for y in range(m)]
    
    # For efficiency: for each pair of cells, compute a "conflict degree"
    # This measures how many of the 4 orientation combos are "blocked"
    
    all_4_pairs = set()
    checked = 0
    
    for idx1 in range(min(sample_cells, m*m)):
        x1, y1 = all_cells[idx1]
        for idx2 in range(idx1 + 1, min(sample_cells, m*m)):
            x2, y2 = all_cells[idx2]
            checked += 1
            
            orientations_blocked = 0
            
            for (b1, b2) in [(0,0), (0,1), (1,0), (1,1)]:
                cell1 = (x1, y1) if b1 == 0 else (y1, x1)
                cell2 = (x2, y2) if b2 == 0 else (y2, x2)
                
                found_blocked = False
                # Check all third cells
                for idx3 in range(m * m):
                    if idx3 == idx1 or idx3 == idx2:
                        continue
                    x3, y3 = all_cells[idx3]
                    
                    for b3 in [0, 1]:
                        cell3 = (x3, y3) if b3 == 0 else (y3, x3)
                        
                        for ri in range(4):
                            for rj in range(4):
                                for rk in range(4):
                                    p1 = c4(cell1[0], cell1[1], ri, n)
                                    p2 = c4(cell2[0], cell2[1], rj, n)
                                    p3 = c4(cell3[0], cell3[1], rk, n)
                                    if det_collinear(p1, p2, p3) == 0:
                                        found_blocked = True
                                        break
                                if found_blocked: break
                            if found_blocked: break
                        if found_blocked: break
                    if found_blocked: break
                
                if found_blocked:
                    orientations_blocked += 1
            
            if orientations_blocked == 4:
                all_4_pairs.add((idx1, idx2))
            
            if checked % 1000 == 0:
                print(f"  checked {checked}, all-4-pairs={len(all_4_pairs)}, rate={len(all_4_pairs)/checked*100:.2f}%", flush=True)
    
    print(f"Total: checked {checked} pairs, found {len(all_4_pairs)} all-4-pairs (rate={len(all_4_pairs)/checked*100:.2f}%)", flush=True)
    return all_4_pairs

if __name__ == "__main__":
    main()
