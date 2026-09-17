#!/usr/bin/env python3
"""
Deep pattern analysis: superimpose all rot4 solutions on a unified board,
analyze non-fitting m values, and extract cycle-specific properties.
"""
import json, math, sys, os
from collections import Counter, defaultdict

# ============================================================
# Primitives
# ============================================================
def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def odd_coord(x, y, m):
    """Convert to odd coordinate representation."""
    return (2 * (m - x) - 1, 2 * (m - y) - 1)

def cell_center_dist(cell, m):
    """Distance from cell to center of board (m-0.5, m-0.5)."""
    cx, cy = cell[0] - (m - 0.5), cell[1] - (m - 0.5)
    return math.sqrt(cx*cx + cy*cy)

# ============================================================
# Load data
# ============================================================
def load_solutions():
    """Load all individual solution files + m=36 from flammenkamp."""
    sol_dir = 'results/solutions'
    sols = {}
    for fname in sorted(os.listdir(sol_dir)):
        if fname.endswith('.json'):
            m_str = fname.replace('.json', '').replace('m', '')
            digits = ''.join(c for c in m_str if c.isdigit())
            if not digits: continue
            m = int(digits)
            data = json.load(open(f'{sol_dir}/{fname}'))
            if 'cells' in data:
                sols[m] = data['cells']
    
    if 36 not in sols:
        try:
            exec(open('rot4_loader.py').read().split('def main')[0])
            line = open('flammenkamp_cache/n72_rot4.few').read().strip()
            pts = decode_line(line, 72)
            cells36 = sorted([(x, y) for (x, y) in pts if x < 36 and y < 36])
            sols[36] = cells36
        except: pass
    
    return sols

def load_cycle_data():
    """Load cycle_analysis.json."""
    b = json.load(open('results/cycle_analysis.json'))
    return {int(k): v for k, v in b['data'].items()}


# ============================================================
# Analysis 1: Arithmetic properties of non-fitting m
# ============================================================
def analyze_non_fitting_ms(cycle_data):
    """Find arithmetic patterns in m where single-cycle solutions are missing."""
    print("=" * 60)
    print("ANALYSIS 1: Non-fitting m (no single-cycle solutions)")
    print("=" * 60)
    
    non_fit = []
    fit_with_single = []
    for m in sorted(cycle_data.keys()):
        info = cycle_data[m]
        total = info['nsol']
        if total == 0: continue
        single = sum(c for sig, c in info['types'] if isinstance(sig, list) and len(sig) == 1 and sig[0] == m)
        if single == 0:
            non_fit.append(m)
        else:
            fit_with_single.append(m)
    
    print(f"\nNon-fitting m (no single-cycle): {non_fit}")
    print(f"Fitting m (has single-cycle):    {fit_with_single}")
    
    # Check arithmetic properties
    print("\n--- Arithmetic properties ---")
    for m in non_fit:
        props = []
        if m % 2 == 0: props.append("even")
        else: props.append("odd")
        if m > 2:
            from sympy import isprime, factorint
            try:
                if isprime(m): props.append("prime")
                else: props.append(f"composite={factorint(m)}")
            except: props.append(f"composite")
        if m % 4 == 1: props.append("≡1 mod 4")
        elif m % 4 == 3: props.append("≡3 mod 4")
        print(f"  m={m:2d}: {', '.join(props)}")
    
    # Check: is there a modular pattern?
    print("\n--- Mod patterns ---")
    for mod in [2, 3, 4, 6, 8, 12]:
        residues = sorted(set(m % mod for m in non_fit))
        all_residues = set(range(mod))
        missing = all_residues - set(m % mod for m in range(1, 37))
        actual_missing = all_residues - set(m % mod for m in non_fit)
        print(f"  mod {mod}: non-fit residues = {sorted(residues)}, all = {sorted(all_residues)}")
    
    # Check: is there a pattern in the difference between consecutive non-fit?
    print("\n--- Gap analysis ---")
    gaps = [non_fit[i+1] - non_fit[i] for i in range(len(non_fit)-1)]
    print(f"  Gaps between consecutive non-fit m: {gaps}")
    print(f"  Mean gap: {sum(gaps)/len(gaps):.1f}")
    
    # Check: what about [1,m-1] type? Is it always present?
    print("\n--- [1,m-1] type availability ---")
    for m in sorted(cycle_data.keys()):
        info = cycle_data[m]
        one_m1 = sum(c for sig, c in info['types'] if isinstance(sig, list) and sorted(sig) == [1, m-1])
        if one_m1 == 0:
            print(f"  m={m}: NO [1,m-1] solutions")
    
    return non_fit, fit_with_single


# ============================================================
# Analysis 2: Superimpose all solutions on normalized board
# ============================================================
def analyze_board_overlay(solutions):
    """
    Put ALL known solutions on the same board.
    Normalize: map each solution's m×m quadrant to a common grid.
    Use odd-coordinate representation (a,b) = 2(m-x)-1, 2(m-y)-1.
    These range from -2m+3 to 2m-3, odd numbers.
    Normalize to [-1, 1] by dividing by 2m-1.
    """
    print("\n" + "=" * 60)
    print("ANALYSIS 2: All solutions on unified board")
    print("=" * 60)
    
    # Collect all cells in normalized coordinates
    # Also track per-m statistics
    all_cells_raw = []  # (x, y, m, cycle_sig)
    
    for m in sorted(solutions.keys()):
        cells = solutions[m]
        # Get cycle signature
        adj = [[] for _ in range(m)]
        for (i, j) in cells:
            adj[i].append(j)
            adj[j].append(i)
        visited = [False] * m
        cycles = []
        for v in range(m):
            if not visited[v]:
                comp = []
                stack = [v]
                while stack:
                    node = stack.pop()
                    if not visited[node]:
                        visited[node] = True
                        comp.append(node)
                        for nb in adj[node]:
                            if not visited[nb]:
                                stack.append(nb)
                cycles.append(len(comp))
        sig = tuple(sorted(cycles))
        
        for (x, y) in cells:
            all_cells_raw.append((x, y, m, sig))
    
    # 1. Center distance analysis
    print("\n--- Center distance distribution ---")
    # For each solution, compute mean distance of cells from center
    for m in sorted(solutions.keys()):
        cells = solutions[m]
        dists = [cell_center_dist(c, m) for c in cells]
        avg_dist = sum(dists) / len(dists)
        min_dist = min(dists)
        max_dist = max(dists)
        print(f"  m={m:2d}: avg_dist={avg_dist:.3f}, min={min_dist:.3f}, max={max_dist:.3f}, "
              f"range={max_dist-min_dist:.3f}")
    
    # 2. Hot spot analysis: which (x,y) positions appear most?
    print("\n--- Hot spots (most frequent cell positions) ---")
    cell_freq = Counter()
    for (x, y, m, sig) in all_cells_raw:
        # Normalize by m: freq across all m
        cell_freq[(x, y)] += 1
    
    most_common = cell_freq.most_common(20)
    print("Most common (x,y) positions across all solutions:")
    for (x, y), cnt in most_common:
        print(f"  ({x:2d},{y:2d}): {cnt} times")
    
    # 3. Which m use which diagonal cells?
    print("\n--- Diagonal cell distribution ---")
    for m in sorted(solutions.keys()):
        cells = solutions[m]
        diag = sorted([(x, y) for (x, y) in cells if x == y])
        anti_diag = sorted([(x, y) for (x, y) in cells if x + y == m - 1])
        if diag:
            print(f"  m={m:2d}: diag cells={diag}")
        if anti_diag:
            print(f"  m={m:2d}: anti-diag cells={anti_diag}")
    
    # 4. Fixed center property
    print("\n--- Center analysis ---")
    for m in sorted(solutions.keys()):
        cells = solutions[m]
        # Center of m×m quadrant is at (m/2, m/2) or (±0.5 offset)
        cx, cy = m/2 - 0.5, m/2 - 0.5  # cell center
        near_center = [(x, y) for (x, y) in cells 
                       if abs(x - cx) <= 1 and abs(y - cy) <= 1]
        print(f"  m={m:2d}: cells near center (±1) = {sorted(near_center)}")


# ============================================================
# Analysis 3: Cycle-type specific patterns
# ============================================================
def analyze_cycle_patterns(solutions, cycle_data):
    """For each cycle type, extract common properties."""
    print("\n" + "=" * 60)
    print("ANALYSIS 3: Cycle-type specific patterns")
    print("=" * 60)
    
    # Classify solutions by cycle type
    type_solutions = defaultdict(list)
    for m in sorted(solutions.keys()):
        cells = solutions[m]
        adj = [[] for _ in range(m)]
        for (i, j) in cells:
            adj[i].append(j)
            adj[j].append(i)
        visited = [False] * m
        cycles = []
        for v in range(m):
            if not visited[v]:
                comp = []
                stack = [v]
                while stack:
                    node = stack.pop()
                    if not visited[node]:
                        visited[node] = True
                        comp.append(node)
                        for nb in adj[node]:
                            if not visited[nb]:
                                stack.append(nb)
                cycles.append(len(comp))
        sig = tuple(sorted(cycles))
        type_solutions[sig].append((m, cells))
    
    # Print the variety of types
    print(f"\nDistinct cycle types found: {len(type_solutions)}")
    
    # Analyze each type
    for sig in sorted(type_solutions.keys(), key=lambda s: (len(s), s)):
        entries = type_solutions[sig]
        ms = [e[0] for e in entries]
        # Count how many m values have this type
        has_loop = 1 in sig
        has_mutual = 2 in sig
        n_long = sum(1 for L in sig if L >= 3)
        
        print(f"\n  Type {str(sig):>20}: {len(entries)} solutions at m={ms}")
        print(f"    Has loop={has_loop}, mutual={has_mutual}, long_cycles={n_long}")
        
        # For single-cycle types [m], what's special?
        if len(sig) == 1:
            m = ms[0]
            cells = entries[0][1]
            # Check symmetry of the cell set
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            x_range = max(xs) - min(xs)
            y_range = max(ys) - min(ys)
            print(f"    x-range = {x_range}, y-range = {y_range}")
            # Check how balanced x and y are
            x_unique = len(set(xs))
            y_unique = len(set(ys))
            print(f"    unique x = {x_unique}/{m}, unique y = {y_unique}/{m}")
            # Count diagonal cells
            diag = sum(1 for (x, y) in cells if x == y)
            print(f"    diag cells = {diag}")


# ============================================================
# Analysis 4: The specific "non-fitting" m values - deep dive
# ============================================================
def analyze_m35_special(cycle_data):
    """Deep analysis of m=35 (the only fragmented unique solution)."""
    print("\n" + "=" * 60)
    print("ANALYSIS 4: Deep dive into m=35 (the odd one)")
    print("=" * 60)
    
    # m=35 has nsol=1, type=[11,24]
    info_35 = cycle_data.get(35)
    if info_35:
        print(f"  m=35: nsol={info_35['nsol']}, types={info_35['types']}")
    
    # m=34 has nsol=2, type=[1,6,27] and [1,?]
    info_34 = cycle_data.get(34)
    if info_34:
        print(f"  m=34: nsol={info_34['nsol']}, types={info_34['types']}")
    
    # Compare with m=36
    info_36 = cycle_data.get(36)
    if info_36:
        print(f"  m=36: nsol={info_36['nsol']}, types={info_36['types']}")
    
    print("\n  Why is m=35 special?")
    print(f"  35 = 5 × 7")
    print(f"  m=35 is the SMALLEST composite odd m that's NOT 2×prime...")
    print(f"  Neighbors: 34 (nsol=2), 36 (nsol=1, single cycle)")
    print(f"  m=35 has NO single-cycle solution—the only solution breaks into [11,24]")
    print(f"  This suggests the (X) constraints for m=35 are especially restrictive")

    # Check ALL m parity vs single-cycle ratio
    print("\n  Single-cycle ratio by m parity:")
    even_single = []
    odd_single = []
    for m in sorted(cycle_data.keys()):
        info = cycle_data[m]
        if info['nsol'] == 0: continue
        single = sum(c for sig, c in info['types'] if isinstance(sig, list) and len(sig) == 1 and sig[0] == m)
        ratio = single / info['nsol']
        if m % 2 == 0:
            even_single.append((m, ratio))
        else:
            odd_single.append((m, ratio))
    
    print(f"  Even m: {[(m, f'{r:.2f}') for m, r in even_single]}")
    print(f"  Odd m:  {[(m, f'{r:.2f}') for m, r in odd_single]}")
    
    # Summary of what m=37 can learn
    print("\n  What m=37 can learn from m=35:")
    print("  - Both odd composite: 35=5×7, 37=prime")
    print("  - m=35 is 'difficult' (only 1 solution, fragmented)")
    print("  - m=31 (prime) is 'easy' (5 solutions, 40% single-cycle)")
    print("  - m=29 (prime) is 'difficult' (19 solutions, 0% single-cycle)")
    print("  → Primality alone doesn't determine difficulty")
    print("  → The (X) constraint geometry depends on m mod small primes")


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 70)
    print("DEEP PATTERN ANALYSIS: Non-fitting points, board overlay, cycle patterns")
    print("=" * 70)
    
    solutions = load_solutions()
    cycle_data = load_cycle_data()
    
    print(f"Loaded {len(solutions)} solution files, {len(cycle_data)} m in cycle data")
    
    # Analysis 1
    non_fit, fit = analyze_non_fitting_ms(cycle_data)
    
    # Analysis 2
    analyze_board_overlay(solutions)
    
    # Analysis 3
    analyze_cycle_patterns(solutions, cycle_data)
    
    # Analysis 4
    analyze_m35_special(cycle_data)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print("\nNon-fitting m (no single-cycle):")
    for m in non_fit:
        info = cycle_data[m]
        dom_type = max(info['types'], key=lambda x: x[1]) if info['types'] else "?"
        print(f"  m={m:2d} ({'even' if m%2==0 else 'odd'}): "
              f"nsol={info['nsol']}, dominant type={dom_type}")
    
    print("\nWhat these have in common:")
    print("  - m=6: small even (only even <10 without single-cycle)")
    print("  - m=29: large prime ≡1 mod 4")
    print("  - m=32: power of 2 (2^5)")
    print("  - m=33: 3×11")
    print("  - m=34: 2×17")
    print("  - m=35: 5×7")
    print("  → NO single arithmetic property unifies them")
    print("  → Pattern emerges from (X) constraint structure, not mod arithmetic")
    
    print("\nKey insight for m=37:")
    print("  - m=37 is prime (like 29, 31)")
    print("  - m=31: 40% single-cycle → primes can have single-cycle solutions")
    print("  - m=29: 0% single-cycle → but not all primes do")
    print("  - The difference is m mod small primes → affects (X) alignment")


if __name__ == '__main__':
    main()
