#!/usr/bin/env python3
"""
Deep pattern analysis of rot4 NTIL solutions.
Focus: cycle structures, Sidon utilization, difference multiset patterns,
and theory compliance across the whole spectrum.
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

def pts_from_cells(cells, m):
    N = 2 * m
    return [c4((x, y), r, N) for (x, y) in cells for r in range(4)]

def collinear_count(pts):
    n = len(pts)
    bad = 0
    for i in range(n):
        xi, yi = pts[i]
        for j in range(i + 1, n):
            xj, yj = pts[j]
            dx1, dy1 = xj - xi, yj - yi
            for k in range(j + 1, n):
                xk, yk = pts[k]
                if dx1 * (yk - yi) == dy1 * (xk - xi):
                    bad += 1
    return bad

# ============================================================
# Analysis functions
# ============================================================

def analyze_cycle_structure(cells, m):
    """Full cycle analysis with type classification."""
    adj = [[] for _ in range(m)]
    for (i, j) in cells:
        adj[i].append(j)
        adj[j].append(i)
    
    visited = [False] * m
    cycle_lengths = []
    cycles_list = []
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
            cycles_list.append(comp)
            cycle_lengths.append(len(comp))
    
    # Categorize cycle types
    sig = tuple(sorted(cycle_lengths))
    has_loop = 1 in cycle_lengths
    has_mutual = 2 in cycle_lengths
    n_loops = sum(1 for L in cycle_lengths if L == 1)
    n_mutual_edges = sum(1 for L in cycle_lengths if L == 2)
    long_cycles = [L for L in cycle_lengths if L >= 3]
    
    return {
        'signature': sig,
        'n_cycles': len(cycle_lengths),
        'n_loops': n_loops,
        'n_mutual_edges': n_mutual_edges,
        'n_long_cycles': len(long_cycles),
        'max_cycle': max(cycle_lengths),
        'min_cycle': min(cycle_lengths),
        'has_loop': has_loop,
        'has_mutual_pair': has_mutual,
        'single_cycle': len(cycle_lengths) == 1
    }


def analyze_sidon_utilization(cells, m):
    """
    Analyze Sidon condition in detail.
    For the a-b Sidon: count(d) + count(-d) <= 2.
    Report: total utilized pairs, saturation level.
    """
    diffs = [-2 * (x - y) for (x, y) in cells]
    cnt = Counter(diffs)
    
    # Count how many ±-pairs are used
    used_pairs = set()
    for d in cnt:
        # Normalize to positive for pair identification
        used_pairs.add(abs(d))
    
    total_violations = 0
    for d in set(diffs):
        nd = -d
        total = cnt.get(d, 0) + cnt.get(nd, 0)
        if total > 2:
            total_violations += 1
    
    # For integer differences (not mod m), the Sidon space is:
    # d ∈ {-(m-1), ..., -1, 1, ..., m-1} → 2(m-1) values, (m-1) ±-pairs
    max_pairs = m - 1
    utilization = len(used_pairs) / max_pairs if max_pairs > 0 else 0
    
    return {
        'n_violations': total_violations,
        'n_used_pairs': len(used_pairs),
        'max_pairs': max_pairs,
        'pair_utilization': round(utilization, 4),
        'diff_counts': dict(cnt)
    }


def analyze_old_coord_pattern(cells, m):
    """
    Check the odd-coordinate representation: 
    a_i = 2(m - x_i) - 1, b_i = 2(m - y_i) - 1
    Analyze the multiset of a_i, b_i values.
    """
    a_vals = [2 * (m - x) - 1 for (x, y) in cells]
    b_vals = [2 * (m - y) - 1 for (x, y) in cells]
    
    a_cnt = Counter(a_vals)
    b_cnt = Counter(b_vals)
    
    # In a 2-factor, each vertex should have degree 2
    # The odd coordinates range: -2m+3, ..., 2m-3 (odd numbers)
    unique_a = len(a_cnt)
    unique_b = len(b_cnt)
    
    return {
        'unique_a': unique_a,
        'unique_b': unique_b,
        'a_repeats': sum(1 for c in a_cnt.values() if c > 1),
        'b_repeats': sum(1 for c in b_cnt.values() if c > 1),
        'a_range': (min(a_vals), max(a_vals)),
        'b_range': (min(b_vals), max(b_vals)),
    }


def analyze_parity_grid(cells, m):
    """Check parity distribution pattern."""
    parity = Counter((x % 2, y % 2) for (x, y) in cells)
    # Balanced parity is predicted by theory
    total = len(cells)
    return {
        'distribution': dict(parity),
        'balanced_4way': len(parity) == 4 and all(v >= total//8 for v in parity.values()),
        'diag_dominant': sum(v for (px, py), v in parity.items() if px == py) / total if total > 0 else 0
    }


def analyze_diag_cells(cells, m):
    """Analyze diagonal structure."""
    main_diag = [(x, y) for (x, y) in cells if x == y]
    anti_diag = [(x, y) for (x, y) in cells if x + y == m - 1]
    sum_const = Counter(x + y for (x, y) in cells)
    diff_const = Counter(x - y for (x, y) in cells)
    
    return {
        'n_main_diag': len(main_diag),
        'n_anti_diag': len(anti_diag),
        'max_sum_count': max(sum_const.values()),
        'max_diff_count': max(diff_const.values()),
        'sum_line_density': sum(1 for v in sum_const.values() if v >= 2),
        'diff_line_density': sum(1 for v in diff_const.values() if v >= 2)
    }


def analyze_single_cycle(cells, m):
    """For single-cycle solutions, extract the difference multiset."""
    # Build adjacency
    adj = [[] for _ in range(m)]
    for (i, j) in cells:
        adj[i].append(j)
        adj[j].append(i)
    
    # Trace cycle from vertex 0
    visited = set()
    cycle = []
    v = 0
    while v not in visited:
        visited.add(v)
        cycle.append(v)
        for nb in adj[v]:
            if nb not in visited:
                v = nb
                break
        else:
            break
    
    if len(cycle) != m:
        return {'is_single_cycle': False}
    
    # Integer differences
    diffs = [cycle[(i + 1) % m] - cycle[i] for i in range(m)]
    abs_diffs = [abs(d) for d in diffs]
    diff_cnt = Counter(abs_diffs)
    
    # Compute Sidon utilization for integer diffs
    # d ∈ {-(m-1)...-1, 1...(m-1)} → (m-1) possible ±-pairs
    used_abs = sorted(diff_cnt.keys())
    n_single = sum(1 for d, c in diff_cnt.items() if c == 1)
    n_double = sum(1 for d, c in diff_cnt.items() if c == 2)
    n_triple = sum(1 for d, c in diff_cnt.items() if c >= 3)
    
    # Check partition of diffs into "large" and "small" steps
    half_m = m // 2
    large_steps = sum(1 for d in abs_diffs if d > half_m)
    small_steps = sum(1 for d in abs_diffs if d <= half_m)
    
    return {
        'is_single_cycle': True,
        'cycle': cycle[:8],  # first 8 entries
        'diffs_sample': diffs[:8],
        'distinct_abs_diffs': len(used_abs),
        'n_single_occurrence': n_single,
        'n_double_occurrence': n_double,
        'n_triple_plus_occurrence': n_triple,
        'large_steps': large_steps,
        'small_steps': small_steps,
        'abs_diff_counts': dict(diff_cnt.most_common(10))
    }


# ============================================================
# Load solutions
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
    
    # m=36 from flammenkamp
    if 36 not in sols:
        try:
            exec(open('rot4_loader.py').read().split('def main')[0])
            line = open('flammenkamp_cache/n72_rot4.few').read().strip()
            pts = decode_line(line, 72)
            cells36 = sorted([(x, y) for (x, y) in pts if x < 36 and y < 36])
            sols[36] = cells36
        except: pass
    
    return sols


# ============================================================
# Cycle analysis JSON data
# ============================================================
def load_cycle_data():
    """Load cycle_analysis.json for broader m coverage."""
    b = json.load(open('results/cycle_analysis.json'))
    d = b['data']
    result = {}
    for k, info in d.items():
        m = int(k)
        result[m] = {
            'nsol': info['nsol'],
            'distinct_types': info['distinct_types'],
            'types': info['types']
        }
    return result


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 70)
    print("DEEP PATTERN ANALYSIS: rot4 NTIL Solutions Across All m")
    print("=" * 70)
    
    # Load data
    solutions = load_solutions()
    cycle_data = load_cycle_data()
    
    print(f"\nLoaded {len(solutions)} solution files + {len(cycle_data)} m from cycle analysis")
    
    # ==============================
    # ANALYSIS 1: Cycle type evolution
    # ==============================
    print("\n" + "=" * 70)
    print("ANALYSIS 1: Cycle Type Evolution Across m")
    print("=" * 70)
    print(f"{'m':>3} | {'nsol':>5} | {'types':>5} | {'[m] ratio':>9} | {'[1,m-1] ratio':>12} | {'Dominant type':>20}")
    print("-" * 70)
    
    for m in sorted(cycle_data.keys()):
        info = cycle_data[m]
        total = info['nsol']
        types = info['types']
        
        # [m] ratio (single cycle)
        single_cycle = sum(c for sig, c in types if isinstance(sig, list) and len(sig) == 1 and sig[0] == m)
        single_ratio = single_cycle / total if total > 0 else 0
        
        # [1,m-1] ratio
        one_m1 = sum(c for sig, c in types if isinstance(sig, list) and sorted(sig) == [1, m-1])
        one_m1_ratio = one_m1 / total if total > 0 else 0
        
        # Dominant type
        if types:
            dominant_sig, dominant_cnt = max(types, key=lambda x: x[1])
            dom_label = str(dominant_sig) if isinstance(dominant_sig, list) else str(dominant_sig)
        else:
            dom_label = "?"
        
        print(f"{m:3d} | {total:5d} | {info['distinct_types']:5d} | {single_ratio:9.4f} | {one_m1_ratio:12.4f} | {dom_label:>20}")
    
    # ==============================
    # ANALYSIS 2: Sidon utilization for known solutions
    # ==============================
    print("\n" + "=" * 70)
    print("ANALYSIS 2: Sidon Utilization Pattern")
    print("=" * 70)
    print("For each known solution, how many ±-pairs are used?")
    print(f"{'m':>3} | {'sig':>16} | {'used_pairs':>10} | {'max_pairs':>9} | {'util%':>6}")
    print("-" * 70)
    
    sidon_data = {}
    for m in sorted(solutions.keys()):
        cells = solutions[m]
        cycle_info = analyze_cycle_structure(cells, m)
        sidon_info = analyze_sidon_utilization(cells, m)
        sidon_data[m] = sidon_info
        
        util_pct = sidon_info['pair_utilization'] * 100
        sig_str = str(cycle_info['signature'])
        print(f"{m:3d} | {sig_str:>16} | {sidon_info['n_used_pairs']:10d} | {sidon_info['max_pairs']:9d} | {util_pct:5.1f}%")
    
    # ==============================
    # ANALYSIS 3: Single-cycle difference patterns
    # ==============================
    print("\n" + "=" * 70)
    print("ANALYSIS 3: Single-Cycle Difference Multiset")
    print("=" * 70)
    
    for m in sorted(solutions.keys()):
        cells = solutions[m]
        sc_info = analyze_single_cycle(cells, m)
        if sc_info['is_single_cycle']:
            print(f"\n  m={m}: single {m}-cycle")
            print(f"    Distinct |d|: {sc_info['distinct_abs_diffs']}/{m-1} "
                  f"(single={sc_info['n_single_occurrence']}, "
                  f"double={sc_info['n_double_occurrence']}, "
                  f"triple+={sc_info['n_triple_plus_occurrence']})")
            print(f"    Step sizes: {sc_info['small_steps']} small, {sc_info['large_steps']} large "
                  f"(threshold=m/2={m//2})")
            print(f"    Diffs sample: {sc_info['diffs_sample']}")
            print(f"    Top |d|: {sc_info['abs_diff_counts']}")
    
    # ==============================
    # ANALYSIS 4: What makes large-m solutions special?
    # ==============================
    print("\n" + "=" * 70)
    print("ANALYSIS 4: Large-m Solution Patterns (m=35, 36)")
    print("=" * 70)
    
    for m in [35, 36]:
        if m not in cycle_data: continue
        info = cycle_data[m]
        print(f"\n  m={m}: nsol={info['nsol']}, types={info['types']}")
    
    if 36 in solutions:
        cells36 = solutions[36]
        sc36 = analyze_single_cycle(cells36, 36)
        if sc36['is_single_cycle']:
            print(f"\n  m=36 single cycle details:")
            print(f"    Cycle first 10: {sc36['cycle'][:10]}")
            print(f"    Diffs first 10: {sc36['diffs_sample']}")
            print(f"    Distinct |d|: {sc36['distinct_abs_diffs']}/35")
            print(f"    Step size pattern: {sc36['small_steps']} small, {sc36['large_steps']} large")
            
            # Check diff signature - positive vs negative runs
            adj = [[] for _ in range(36)]
            for (i, j) in cells36:
                adj[i].append(j)
                adj[j].append(i)
            cycle = []
            v = 0
            visited = set()
            while v not in visited:
                visited.add(v)
                cycle.append(v)
                for nb in adj[v]:
                    if nb not in visited:
                        v = nb
                        break
                else:
                    break
            diffs = [cycle[(i+1)%36] - cycle[i] for i in range(36)]
            
            # Count sign changes
            signs = [1 if d > 0 else -1 for d in diffs]
            sign_changes = sum(1 for i in range(len(signs)) if signs[i] != signs[(i+1)%len(signs)])
            print(f"    Sign changes in diffs: {sign_changes}")
            
            # Count consecutive positive/negative runs
            runs = []
            current_run = signs[0]
            run_len = 1
            for s in signs[1:]:
                if s == current_run:
                    run_len += 1
                else:
                    runs.append((current_run, run_len))
                    current_run = s
                    run_len = 1
            runs.append((current_run, run_len))
            print(f"    Sign runs: {runs}")
    
    # ==============================
    # ANALYSIS 5: Trends and transitions
    # ==============================
    print("\n" + "=" * 70)
    print("ANALYSIS 5: Key Transitions")
    print("=" * 70)
    
    # Find where [m] type disappears
    print("\n  Single-cycle [m] type ratio:")
    prev = 1.0
    for m in sorted(cycle_data.keys()):
        info = cycle_data[m]
        total = info['nsol']
        single_cycle = sum(c for sig, c in info['types'] if isinstance(sig, list) and len(sig) == 1 and sig[0] == m)
        ratio = single_cycle / total if total > 0 else 0
        if ratio != prev:
            print(f"    m={m:2d}: {ratio:.4f} (was {prev:.4f})")
            prev = ratio
    
    # Find most diverse m
    max_types = max(cycle_data.items(), key=lambda kv: kv[1]['distinct_types'])
    print(f"\n  Most cycle-diverse: m={max_types[0]} with {max_types[1]['distinct_types']} types")
    
    # Find unique (nsol=1) m values
    unique_ms = [m for m, info in cycle_data.items() if info['nsol'] == 1]
    print(f"  Unique-solution m: {unique_ms}")
    
    # ==============================
    # ANALYSIS 6: What pattern would m=37 need?
    # ==============================
    print("\n" + "=" * 70)
    print("ANALYSIS 6: Extrapolation to m=37")
    print("=" * 70)
    
    # Check Sidon trend
    print("\n  Sidon pair utilization trend (extrapolated):")
    for m in sorted(sidon_data.keys()):
        s = sidon_data[m]
        print(f"    m={m:2d}: {s['n_used_pairs']:2d}/{s['max_pairs']:2d} pairs ({s['pair_utilization']*100:.0f}%), "
              f"violations={s['n_violations']}")
    
    # Check cycle type diversity trend
    print("\n  Cycle type diversity trend:")
    for m in sorted(cycle_data.keys()):
        info = cycle_data[m]
        print(f"    m={m:2d}: {info['distinct_types']:2d} types for {info['nsol']:4d} solutions")
    
    # For m=37, what do we need?
    print("\n  Required for m=37:")
    print("    - Sidon: 37 cells, need 37 distinct a-b differences")
    print(f"      Available ±-pairs: 36, each max 2 -> capacity 72")
    print(f"      Sidon is easily satisfiable")
    print(f"    - Cycle types possible: any 2-regular graph on 37 vertices")
    print(f"      (max {sum(1 for _ in range(1,38) for _ in range(38))} signatures)")
    print(f"    - The (X) constraints are the real bottleneck")
    
    # Save to file
    output = {
        'n_solutions': len(solutions),
        'sidon_data': {str(m): d for m, d in sidon_data.items()},
        'cycle_data': {str(m): d for m, d in cycle_data.items()},
    }
    with open('results/theory_fit_deep.json', 'w') as f:
        json.dump(output, f, indent=1)
    print(f"\n  Full data saved to results/theory_fit_deep.json")


if __name__ == '__main__':
    main()
