#!/usr/bin/env python3
"""
find_hidden_symmetries.py — Search for hidden affine/linear relationships
between missing-center solutions in No-Three-In-Line.

For prime n (p), GL(2,p) acts on Z_p² and preserves collinearity.
Two solutions related by an affine transform (M ∈ GL(2,p), t ∈ Z_p²)
are "the same" under this larger symmetry group.

Algorithm:
  For each pair of missing-center solutions (A, B):
    Pick the first point p in A.
    For each M in GL(2,p):
      For each point q in B:
        Compute t = q - M(p)  (the translation that maps p→q)
        If affine transform T(x)=Mx+t maps all of A to B:
          FOUND: solution B = T(solution A)
"""

import sys
import os
import re
from collections import Counter


def parse_rle(content, n):
    solutions = []
    raw_sols = content.split('!')
    for raw in raw_sols:
        raw = raw.strip()
        if not raw:
            continue
        # Expand RLE
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
        pts = [(c, r) for r, row in enumerate(rows)
               if r < n for c, ch in enumerate(row)
               if c < n and ch == 'o']
        if len(pts) == 2 * n:
            solutions.append(pts)
    return solutions


def check_missing_center(pts, n):
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


def generate_gl2(p):
    """Generate all 2×2 invertible matrices over Z_p."""
    matrices = []
    for a in range(p):
        for b in range(p):
            for c in range(p):
                for d in range(p):
                    det = (a * d - b * c) % p
                    if det != 0:
                        matrices.append((a, b, c, d))
    return matrices


# Pre-compute D4 matrices mod p
def get_d4_matrices(p):
    mats = []
    for a, b, c, d in [(1,0,0,1), (0,-1,1,0), (-1,0,0,-1), (0,1,-1,0),
                        (-1,0,0,1), (1,0,0,-1), (0,1,1,0), (0,-1,-1,0)]:
        mats.append(((a % p, b % p, c % p, d % p)))
    return set(mats)


def apply_affine(pt, M, t, p):
    """Apply x → Mx + t mod p to a single point. Returns None if outside grid."""
    a, b, c, d = M
    x, y = pt
    nx = (a * x + b * y + t[0]) % p
    ny = (c * x + d * y + t[1]) % p
    if 0 <= nx < p and 0 <= ny < p:
        return (nx, ny)
    return None


def transform_all(pts, M, t, p):
    """Apply affine transform to all points. Returns set or None."""
    result = set()
    for pt in pts:
        q = apply_affine(pt, M, t, p)
        if q is None:
            return None
        result.add(q)
    if len(result) == len(pts):
        return result
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_hidden_symmetries.py <rle_file>")
        sys.exit(1)
    
    rle_path = sys.argv[1]
    basename = os.path.basename(rle_path)
    m = re.search(r'(\d+)\.out', basename)
    n = int(m.group(1))
    
    # Check if n is prime
    if n < 2 or any(n % i == 0 for i in range(2, int(n**0.5) + 1)):
        print(f"n={n} is NOT prime (field Z_n not a field). Analysis would be unreliable.")
        # Still try for odd n with some caveats...
        if n % 2 == 0:
            print("Even n — GL(2,n) analysis not possible (non-field).")
            sys.exit(1)
        print("n is odd composite — analysis may have issues with non-invertible elements.")
    
    with open(rle_path, 'r') as f:
        content = f.read()
    
    all_solutions = parse_rle(content, n)
    print(f"Total solutions loaded: {len(all_solutions)}")
    
    # Identify missing-center solutions
    missing_pts_list = []
    missing_indices = []
    for idx, pts in enumerate(all_solutions):
        if check_missing_center(pts, n):
            missing_pts_list.append(pts)
            missing_indices.append(idx)
    
    n_missing = len(missing_pts_list)
    print(f"Missing-center solutions: {n_missing}")
    print()
    
    if n_missing < 2:
        print("Need at least 2 missing-center solutions for comparison.")
        sys.exit(0)
    
    # Generate GL(2,n) and D4 matrices
    gl2 = generate_gl2(n)
    d4_set = get_d4_matrices(n)
    
    print(f"GL(2,{n}) size: {len(gl2)}")
    print()
    
    # Build set of missing-center solutions for fast lookup
    # Use frozensets as keys
    missing_set = {frozenset(pts): idx for pts, idx in zip(missing_pts_list, missing_indices)}
    
    # === Analysis 1: Are missing-center solutions GL(2,n)-related? ===
    # Strategy: For each solution A, compute all its affine transforms
    # T(A) = M*A + t (M ∈ GL(2,n), t ∈ Z_n²), and check if any other
    # missing-center solution matches.
    print("=" * 70)
    print("Analysis 1: GL(2,n) + translation relations between missing-center solutions")
    print("=" * 70)
    print(f"  Checking all missing-center solutions for affine relations...")
    
    found_relations = []
    
    # Pre-build a lookup: frozenset(sorted(pts)) -> index, for all missing solutions
    missing_fset_to_idx = {}
    for i, pts in enumerate(missing_pts_list):
        missing_fset_to_idx[frozenset(pts)] = missing_indices[i]
    
    # To avoid redundant checks, only search for transforms that map from
    # a solution to a SOLUTION WITH LOWER INDEX (prevents double-counting)
    for i in range(n_missing):
        pts_a = missing_pts_list[i]
        idx_a = missing_indices[i]
        a_fset = frozenset(pts_a)
        p0 = pts_a[0]  # reference point for translation
        
        # For progress tracking
        if i % 5 == 0:
            print(f"  [{i+1}/{n_missing}] Checking solution #{idx_a}...     \r", end='', flush=True)
        
        for M in gl2:
            if M in d4_set:
                continue  # Skip D4 symmetries (already factored)
            
            a, b, c, d = M
            
            # Precompute M(p) for all points of A
            # While doing this, check if all M(p) stay in grid
            m_pts = []
            valid = True
            for x, y in pts_a:
                nx = (a * x + b * y) % n
                ny = (c * x + d * y) % n
                if 0 <= nx < n and 0 <= ny < n:
                    m_pts.append((nx, ny))
                else:
                    valid = False
                    break
            
            if not valid or len(set(m_pts)) != len(pts_a):
                continue  # M(p) not bijective or goes outside grid
            
            m0 = m_pts[0]  # M(p0)
            
            # Now try all translations t ∈ Z_n²
            # For each other missing-center solution B, check if ∃t: M(A)+t = B
            # Instead of iterating all t, use the fact that B and M(A) determine t:
            # t = q - M(p0) for any point q in B
            
            for j in range(n_missing):
                if j == i:
                    continue
                pts_b = missing_pts_list[j]
                idx_b = missing_indices[j]
                
                # Try to find t from point correspondences
                # For each point q in B, t = q - m0
                for q in pts_b:
                    tx = (q[0] - m0[0]) % n
                    ty = (q[1] - m0[1]) % n
                    
                    if tx == 0 and ty == 0:
                        # Pure matrix transform: check if M(A) = B
                        if set(m_pts) == set(pts_b):
                            found_relations.append((idx_a, idx_b, M, (0,0)))
                            if len(found_relations) <= 10:
                                print(f"\n  ✅ #{idx_a} → #{idx_b}: M=({a},{b},{c},{d}), t=(0,0)")
                            break
                    else:
                        # Verify: shift M(A) by t and check against B
                        b_set = set(pts_b)
                        all_ok = True
                        for pt in m_pts:
                            qx = (pt[0] + tx) % n
                            qy = (pt[1] + ty) % n
                            if qx >= n or qy >= n or (qx, qy) not in b_set:
                                all_ok = False
                                break
                        if all_ok:
                            # Full verification
                            transformed = set()
                            for pt in m_pts:
                                qx = (pt[0] + tx) % n
                                qy = (pt[1] + ty) % n
                                transformed.add((qx, qy))
                            if transformed == b_set:
                                found_relations.append((idx_a, idx_b, M, (tx, ty)))
                                if len(found_relations) <= 10:
                                    print(f"\n  ✅ #{idx_a} → #{idx_b}: M=({a},{b},{c},{d}), t=({tx},{ty})")
                                break
    
    print(f"\n  Total relations found: {len(found_relations)}")
    if not found_relations:
        print("  ❌ No GL(2,n) relations found among missing-center solutions.")
    
    # === Analysis 2: Stabilizers (hidden self-symmetries) ===
    print()
    print("=" * 70)
    print("Analysis 2: Hidden self-symmetries (non-D4 stabilizers in GL(2,n))")
    print("=" * 70)
    
    found_stabilizers = 0
    for i in range(min(n_missing, 20)):
        pts_a = missing_pts_list[i]
        idx_a = missing_indices[i]
        a_set = set(pts_a)
        
        for M in gl2:
            if M in d4_set:
                continue
            
            # Apply matrix (no translation)
            m_set = set()
            a, b, c, d = M
            valid = True
            for x, y in pts_a:
                nx = (a * x + b * y) % n
                ny = (c * x + d * y) % n
                if 0 <= nx < n and 0 <= ny < n:
                    m_set.add((nx, ny))
                else:
                    valid = False
                    break
            
            if valid and len(m_set) == len(a_set) and m_set == a_set:
                print(f"  🌀 Solution #{idx_a}: hidden self-symmetry M={M}")
                found_stabilizers += 1
    
    if found_stabilizers == 0:
        print("  ❌ No hidden self-symmetries found (excluding D4).")
    else:
        print(f"  ✅ {found_stabilizers} hidden self-symmetries detected!")
    
    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"  n = {n} ({'prime' if all(n%i!=0 for i in range(2,int(n**0.5)+1)) else 'composite'})")
    print(f"  Missing-center solutions: {n_missing}")
    print(f"  GL(2,n) relations found: {len(found_relations)}")
    print(f"  Hidden stabilizers found: {found_stabilizers}")
    
    if found_relations:
        print("\n  ⚠️  CONCLUSION: Some missing-center solutions ARE related")
        print("     by GL(2,n) affine transformations beyond D4!")
    if found_stabilizers:
        print("\n  ⚠️  CONCLUSION: Some missing-center solutions have")
        print("     non-D4 symmetries in GL(2,n)!")
    if not found_relations and not found_stabilizers:
        print("\n  ✅ CONCLUSION: No non-D4 relations found (limited search).")


if __name__ == '__main__':
    main()
