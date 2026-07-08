#!/usr/bin/env python3
"""
C4 constraint structure deep dive.

Focus on:
1. The "direction-per-domain-cell" mapping — how many distinct directions 
   are actually available for C4 solutions?
2. What causes the solution count to collapse at n≈58?
3. Compatibility graph analysis for the row-matching constraint.
"""

import os, math, json
from collections import defaultdict, Counter

CACHE = r'D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\analysis\flammenkamp_cache'
ALPH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|'
VAL = {c: i for i, c in enumerate(ALPH)}

HEAVY_C4_GRP = {
    'diag': {(1,1), (1,-1), (-1,1), (-1,-1)},  # C4 orbit of (1,1)
    'slope3_a': {(3,1), (1,-3), (-3,-1), (-1,3)},  # C4 orbit of (3,1) 
    'slope3_b': {(3,-1), (1,3), (-3,1), (-1,-3)},  # C4 orbit of (3,-1)
}
HEAVY_C4_REPS = {(1,1), (3,1), (3,-1)}


def dir_of(pt, n):
    """Reduced direction from even-n center C((n-1)/2, (n-1)/2)."""
    a = 2*pt[0] - (n-1); b = 2*pt[1] - (n-1)
    g = math.gcd(a,b) or 1
    a //= g; b //= g
    if a < 0 or (a == 0 and b < 0):
        a, b = -a, -b
    if a == 0: b = 1
    if b == 0: a = 1
    return (a, b)


def dir_c4_reduced(d):
    """Map a direction to its C4-equivalence class representative.
    
    Under C4: (a,b) → (b,-a) → (-a,-b) → (-b,a)
    Take the lexicographically smallest as representative.
    """
    a, b = d
    orbit = [(a,b), (b,-a), (-a,-b), (-b,a)]
    # Normalize signs
    normalized = []
    for (x,y) in orbit:
        if x < 0 or (x == 0 and y < 0):
            x, y = -x, -y
        if x == 0: y = 1
        if y == 0: x = 1
        normalized.append((x,y))
    return min(normalized)


def dir_dihedral_reduced(d):
    """Map a direction to its D4-equivalence class (including reflections).
    
    D4: C4 rotations + reflections (a,b) → (b,a) (swap)
    """
    a, b = d
    # All D4 images
    orbit = set()
    for (a0,b0) in [(a,b), (b,a)]:  # original and reflected
        for _ in range(4):  # C4 rotations
            if a0 < 0 or (a0 == 0 and b0 < 0):
                orbit.add((-a0, -b0))
            else:
                orbit.add((a0, b0))
            a0, b0 = -b0, a0  # C4 rotation
    return min(orbit)


def decode_solution(line, n):
    line = line.rstrip()
    if not line: return None
    pre = line[0]
    body = line[1:] if pre in '.:/-ocx+*' else line
    if len(body) < 2*n: return None
    pts = []
    for r in range(n):
        c1 = VAL.get(body[2*r]); c2 = VAL.get(body[2*r+1])
        if c1 is None or c2 is None or c1 >= n or c2 >= n:
            return None
        pts.append((r, c1)); pts.append((r, c2))
    return pts


def load_rot4(n):
    sols = []
    for ext in ['', '.few']:
        p = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    c = decode_solution(line, n)
                    if c: sols.append(c)
    return sols


def c4_domain_directions(n):
    """For the C4 domain [0,N)×[0,N), compute ALL possible directions.
    
    Each domain cell (r,c) with 0≤r<N, 0≤c<N gives a C4 orbit.
    The representative direction is dir(r,c) reduced under C4.
    
    Returns: dict mapping C4-reduced direction → list of domain cells
    """
    N = n // 2
    dir_to_cells = defaultdict(list)
    
    for r in range(N):
        for c in range(N):
            # In C4 domain, (r,c) maps to (c,N-1-r) etc.
            # But we want direction from center
            d = dir_of((r, c), n)
            d_c4 = dir_c4_reduced(d)
            dir_to_cells[d_c4].append((r, c))
    
    return dict(dir_to_cells)


def analyze_direction_space(n):
    """Analyze the direction space for C4 solutions at given n."""
    dir_cells = c4_domain_directions(n)
    N = n // 2
    
    print(f"\n{'='*60}")
    print(f"n={n} (N={N}):")
    print(f"{'='*60}")
    print(f"  Total C4-inequivalent directions: {len(dir_cells)}")
    print(f"  C4 solutions need: {N} directions")
    
    # Count directions by prevalence
    cell_counts = sorted([(len(cells), d) for d, cells in dir_cells.items()], reverse=True)
    
    print(f"  Directions with exactly 1 cell: {sum(1 for c,d in cell_counts if c == 1)}")
    print(f"  Directions with ≥2 cells: {sum(1 for c,d in cell_counts if c >= 2)}")
    print(f"  Directions with ≥4 cells: {sum(1 for c,d in cell_counts if c >= 4)}")
    
    # Most "populous" directions
    print(f"  Top 10 directions by cell count:")
    for count, d in cell_counts[:10]:
        print(f"    {str(d):>12}: {count} cells")
    
    # Direction "diversity" — what fraction of the N directions needed 
    # can come from unique directions?
    # If a direction has k cells, it can be used at most k times (each in a different row)
    # But for most, each direction corresponds to exactly one cell
    single_cell = sum(1 for c, _ in cell_counts if c == 1)
    print(f"  Unique directions (1 cell each): {single_cell}/{N} ({single_cell/N*100:.1f}%)")
    
    heavy_dir_info = {}
    for d in HEAVY_C4_REPS:
        cells = dir_cells.get(d, [])
        heavy_dir_info[d] = cells
    
    return {
        'n': n,
        'N': N,
        'total_directions': len(dir_cells),
        'single_cell_dirs': single_cell,
        'needed': N,
        'dir_info': dir_cells,
        'heavy_info': heavy_dir_info,
    }


def row_matching_in_c4_solutions(n):
    """Deep analysis of row-matching in C4 solutions.
    
    Key question: in the FULL grid C4 solution, each row has 2 points.
    These define a 2-regular graph on n vertices.
    The graph structure is constrained by C4 symmetry.
    
    Under C4, if row r pairs with column c (has a point at (r,c)), then:
    - row c pairs with column n-1-r (has a point at (c, n-1-r))
    - etc.
    
    So the row-matching is really a 2-regular graph on N= n/2 vertices,
    plus the C4 images.
    """
    sols = load_rot4(n)
    if not sols:
        return None
    
    # For each solution, build the row-matching graph
    # The graph has n/2 vertices (domain rows), each with degree 2
    # Edges are to columns (which become C4 images)
    
    all_matches = []
    
    for pts in sols:
        # Domain rows and their columns
        N = n // 2
        domain_cols = defaultdict(list)
        for r, c in pts:
            if r < N and c < N:
                domain_cols[r].append(c)
        
        # Verify each domain row has exactly 2 domain columns
        if len(domain_cols) != N:
            continue
        
        ok = all(len(cols) == 2 for cols in domain_cols.values())
        if not ok:
            continue
        
        # The row-matching is a 2-regular bipartite graph on the set {0..N-1}
        # Each row connects to 2 columns
        matches = {}
        for r, cols in domain_cols.items():
            matches[r] = sorted(cols)
        
        all_matches.append(matches)
    
    return all_matches


def match_intersection_analysis(n_start=12, n_end=56):
    """Analyze how C4 solution structure changes with n.
    
    Key: track how many distinct direction-orbits are "available" vs "needed".
    """
    print(f"\n{'='*60}")
    print(f"C4 Phase Transition Analysis: n=10 through n=56")
    print(f"{'='*60}")
    print(f"{'n':>4} {'N':>4} {'dirs':>6} {'unique%':>8} {'avail/excess':>13} {'heavy_ok':>9}")
    print("-" * 50)
    
    results = []
    
    for n in range(10, n_end + 1, 2):
        ds = analyze_direction_space(n)
        
        # Load solutions 
        sols = load_rot4(n)
        
        # Available directions: how many have at least one cell?
        available = ds['total_directions']
        needed = ds['N']
        ratio = available / needed if needed else 0
        
        # How many heavy directions are usable?
        N = ds['N']
        heavy_count = sum(1 for d in HEAVY_C4_REPS if ds['dir_info'].get(d, []))
        
        results.append({
            'n': n,
            'N': N,
            'available_dirs': available,
            'needed': needed,
            'ratio': ratio,
            'single_cell_pct': ds['single_cell_dirs'] / available * 100 if available else 0,
            'num_solutions': len(sols),
            'heavy_usable': heavy_count,
        })
        
        unique_pct = ds['single_cell_dirs'] / needed * 100 if needed else 0
        avail_pct = (available - needed) / needed * 100 if needed else 0
        print(f"{n:>4} {N:>4} {available:>6} {unique_pct:>7.1f}%  {available - needed:>+7} ({avail_pct:+.0f}%)  {heavy_count:>3}/3")
    
    # Find the phase transition
    print(f"\n  Phase transition indicators:")
    print(f"  Early n (N≤28): many solutions, diverse direction usage")
    print(f"  Late n (N≥30): solution count collapses")
    print(f"  Key: at N≈29, available dirs / needed ratio crosses threshold")
    
    return results


def direction_excess_vs_solutions():
    """Plot direction excess vs solution count to find the threshold."""
    print(f"\n{'='*60}")
    print(f"Direction Excess vs Solution Count")
    print(f"{'='*60}")
    print(f"{'n':>4} {'avail-need':>11} {'excess%':>9} {'solutions':>12} {'growth':>8}")
    print("-" * 50)
    
    prev_count = None
    for n in range(10, 58, 2):
        ds = analyze_direction_space(n)
        sols = load_rot4(n)
        avail = ds['total_directions']
        need = ds['N']
        excess = avail - need
        excess_pct = excess / need * 100 if need else 0
        
        growth = ""
        if prev_count is not None and prev_count > 0:
            r = len(sols) / prev_count
            growth = f"{r:.3f}x"
        
        print(f"{n:>4} {excess:>+9}  {excess_pct:>+7.1f}%  {len(sols):>10,}  {growth}")
        prev_count = len(sols)


def c4_to_2regular_mapping(n):
    """Map the C4 domain cells to the 2-regular graph they participate in.
    
    For C4, each cell (r,c) in the domain [0,N)×[0,N) contributes to
    rows {r, c, N-1-r, N-1-c} in the full grid.
    
    The 2-regular graph constraint means: for each row r in [0,n), 
    exactly 2 cells in the domain must involve row r.
    """
    N = n // 2
    
    # For each domain cell, list which full-grid rows it touches
    cell_rows = {}
    for r in range(N):
        for c in range(N):
            rows = {r, c, N-1-r, N-1-c}
            cell_rows[(r,c)] = sorted(rows)
    
    # Row degree constraint: each row must have degree 2
    # Under C4, if row r has col c, then row c gets col N-1-r automatically
    # So the matching is highly constrained
    
    # Let's compute: for each row in domain [0,N), what columns are possible
    # given that the 2-regular graph must be C4-invariant?
    
    # Under the C4 constraint:
    # Selecting (r,c) in domain ⟹ columns s for row r and s for row c are locked
    
    return cell_rows


def main():
    print("=" * 60)
    print("C4 CONSTRAINT STRUCTURE DEEP ANALYSIS")
    print("=" * 60)
    
    # 1. Direction space analysis
    print("\n--- 1. Direction Space Analysis ---")
    for n in [12, 20, 28, 36, 44, 56, 76]:
        analyze_direction_space(n)
    
    # 2. Phase transition analysis
    phase_data = match_intersection_analysis(10, 56)
    
    # 3. Direction excess vs solutions
    direction_excess_vs_solutions()
    
    # 4. Predictive model with phase transition
    print(f"\n--- 4. Phase Transition Corrected Model ---")
    print(f"Observed: solution count peaks near n=56 (N=28)")
    print(f"At n=56: available directions = N²/2 = 28²/2 = 392")
    print(f"           needed = N = 28")
    print(f"           excess = 364 (1300%)")
    print(f"           solutions ≈ 10,441")
    print(f"At n=72: available directions = N²/2 = 36²/2 = 648")
    print(f"           needed = N = 36")
    print(f"           excess = 612 (1700%)")
    print(f"           solutions ≈ 1 (Heule)")
    print(f"At n=76: available directions = N²/2 = 38²/2 = 722")
    print(f"           needed = N = 38")
    print(f"           excess = 684 (1800%)")
    print(f"           solutions ? (our search)")
    
    print(f"\nConclusion: Direction excess is NOT the limiting factor.")
    print(f"The excess GROWS with n, yet solutions decrease.")
    print(f"The real bottleneck is the 2-regular graph + collinearity coupling.")


if __name__ == '__main__':
    main()
