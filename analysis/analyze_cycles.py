#!/usr/bin/env python3
"""
analyze_cycles.py — Analyze the column-pairing cycle structure of
missing-center solutions. Two solutions with the same cycle decomposition
may be related by relabeling, even if they look different under D4.

Every 2-per-row No-Three-In-Line solution defines a 2-regular bipartite
graph between rows and columns: each row connects to 2 columns, each column
connects to 2 rows. This decomposes into disjoint even-length cycles.

If two solutions have the same cycle-length multiset, they may be "the same"
pattern under row/column relabeling.
"""

import sys
import os
import re
from collections import Counter, defaultdict


def parse_rle(content, n):
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


def get_cycle_decomposition(pts, n):
    """Extract the cycle structure of the column-pairing graph.
    
    Build a graph: each row is a node, each column is a node.
    Edges: (row, col) for each placed point.
    Since each row has degree 2 and each column has degree 2,
    the graph decomposes into disjoint cycles of even length.
    
    Returns: list of cycles, where each cycle alternates row-col-row-col-...
    """
    # Build adjacency
    row_to_cols = defaultdict(list)
    col_to_rows = defaultdict(list)
    for c, r in pts:
        row_to_cols[r].append(c)
        col_to_rows[c].append(r)
    
    # Find cycles
    visited_rows = set()
    visited_cols = set()
    cycles = []
    
    for start_row in range(n):
        if start_row in visited_rows:
            continue
        if len(row_to_cols[start_row]) == 0:
            continue
        
        # Start a cycle
        cycle = []
        r = start_row
        while r not in visited_rows:
            visited_rows.add(r)
            # Pick unvisited column connected to this row
            next_cols = [c for c in row_to_cols[r] if c not in visited_cols]
            if not next_cols:
                # All columns visited — we're done with this cycle
                break
            c = next_cols[0]
            visited_cols.add(c)
            cycle.append(('R', r))
            cycle.append(('C', c))
            # Move to the other row connected to this column
            next_rows = [rr for rr in col_to_rows[c] if rr != r]
            if not next_rows:
                break
            r = next_rows[0]
        
        if cycle:
            # Close the cycle
            cycles.append(tuple(cycle))
    
    # Return sorted cycle lengths
    cycle_lengths = tuple(sorted(len(c) // 2 for c in cycles))
    return cycle_lengths, cycles


def find_isomorphic_cycles(cycles_a, cycles_b, n):
    """Check if two cycle decompositions are isomorphic (same cycle length multiset)."""
    lens_a = tuple(sorted(len(c) // 2 for c in cycles_a))
    lens_b = tuple(sorted(len(c) // 2 for c in cycles_b))
    return lens_a == lens_b


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_cycles.py <rle_file>")
        sys.exit(1)
    
    rle_path = sys.argv[1]
    basename = os.path.basename(rle_path)
    m = re.search(r'(\d+)\.out', basename)
    n = int(m.group(1))
    
    with open(rle_path, 'r') as f:
        content = f.read()
    
    all_solutions = parse_rle(content, n)
    
    # Separate missing vs center
    missing_cycles = []
    center_cycles = []
    
    for idx, pts in enumerate(all_solutions):
        is_missing = check_missing_center(pts, n)
        cls, cycles = get_cycle_decomposition(pts, n)
        if is_missing:
            missing_cycles.append((idx, cls, cycles, pts))
        else:
            center_cycles.append((idx, cls, cycles, pts))
    
    print(f"n={n}")
    print(f"All solutions: {len(all_solutions)}")
    print(f"Missing-center: {len(missing_cycles)}")
    print(f"With center: {len(center_cycles)}")
    print()
    
    # === Analysis 1: Cycle length distribution for missing vs center ===
    print("=" * 70)
    print("Analysis 1: Cycle length distribution")
    print("=" * 70)
    
    missing_dist = Counter()
    for idx, cls, cycles, pts in missing_cycles:
        missing_dist[cls] += 1
    center_dist = Counter()
    for idx, cls, cycles, pts in center_cycles:
        center_dist[cls] += 1
    
    all_types = sorted(set(list(missing_dist.keys()) + list(center_dist.keys())))
    
    print(f"{'Cycle Type (sorted lengths)':<35s} {'Missing':>10s} {'Center':>10s}")
    print(f"{'-'*35} {'-'*10} {'-'*10}")
    for ct in all_types:
        m = missing_dist.get(ct, 0)
        c = center_dist.get(ct, 0)
        print(f"{str(ct):<35s} {m:>10d} {c:>10d}")
    print(f"{'-'*35} {'-'*10} {'-'*10}")
    print(f"{'TOTAL':<35s} {len(missing_cycles):>10d} {len(center_cycles):>10d}")
    
    # === Analysis 2: Do missing-center solutions cluster by cycle type? ===
    print()
    print("=" * 70)
    print("Analysis 2: Missing-center solution clustering by cycle type")
    print("=" * 70)
    
    # Group missing-center solutions by cycle type
    missing_by_type = defaultdict(list)
    for idx, cls, cycles, pts in missing_cycles:
        missing_by_type[cls].append((idx, cycles, pts))
    
    for ct, sols in sorted(missing_by_type.items(), key=lambda x: -len(x[1])):
        print(f"\n  Cycle type {ct}: {len(sols)} solutions")
        idxs = [s[0] for s in sols]
        print(f"    Indices: {idxs}")
        
        # Check if solutions with the same cycle type have similar distance ring usage
        if len(sols) >= 2:
            # Compute common distance rings
            ring_sets = []
            for _, _, pts in sols:
                ds = set()
                if n % 2 == 0:
                    cx2, cy2 = n - 1, n - 1
                else:
                    c = 2 * (n // 2)
                    cx2, cy2 = c, c
                for x, y in pts:
                    dx = 2 * x - cx2
                    dy = 2 * y - cy2
                    d = dx * dx + dy * dy
                    ds.add(d)
                ring_sets.append(ds)
            
            common = set.intersection(*ring_sets)
            print(f"    Common distance rings ({len(common)}): {sorted(common)}")
    
    # === Analysis 3: Most frequent column pairs ===
    print()
    print("=" * 70)
    print("Analysis 3: Most common column pairs in missing-center solutions")
    print("=" * 70)
    
    pair_counts = Counter()
    for idx, cls, cycles, pts in missing_cycles:
        # Get column pairs per row
        row_pairs = defaultdict(list)
        for c, r in pts:
            row_pairs[r].append(c)
        for r, cols in row_pairs.items():
            pair_counts[tuple(sorted(cols))] += 1
    
    print("  Most common (row) column pairs:")
    for pair, count in pair_counts.most_common(15):
        print(f"    {pair}: {count}/{len(missing_cycles)} solutions")
    
    # === Analysis 4: Shared structure in cycles ===
    print()
    print("=" * 70)
    print("Analysis 4: Do ANY two missing-center solutions share the same cycle type?")
    print("  (If yes, they may be 'the same' pattern under relabeling)")
    print("=" * 70)
    
    clusters = 0
    max_cluster = 0
    for ct, sols in missing_by_type.items():
        if len(sols) >= 2:
            clusters += 1
            max_cluster = max(max_cluster, len(sols))
    
    print(f"  {clusters} cycle types have multiple missing-center solutions")
    print(f"  Largest cluster: {max_cluster} solutions sharing the same cycle type")
    print()
    
    if clusters > 0:
        print("  ✅ Missing-center solutions DO cluster by cycle type!")
        print("  → They share a common 'skeleton' (column-pairing graph)")
        print("  → Different cluster = fundamentally different structure")
    else:
        print("  ❌ Each missing-center solution has a unique cycle type.")
        print("  → No two solutions share the same column-pairing skeleton.")


if __name__ == '__main__':
    main()
