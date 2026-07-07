"""
Extend cycle decomposition analysis to n=20-31 using Flammenkamp cache.
"""
import os
from collections import Counter, defaultdict

CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')
ALPH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.'
c2v = {c:i for i,c in enumerate(ALPH)}

def decode_flam(line, n):
    """Decode Flammenkamp line to list of (col, row) points."""
    rest = line.strip()[1:]
    pts = []
    for row in range(n):
        c1 = c2v[rest[2*row]]
        c2 = c2v[rest[2*row+1]]
        pts.append((c1, row))
        pts.append((c2, row))
    return pts

def has_center(n, pts):
    X = n - 1
    rings = Counter()
    for c, r in pts:  # pts are (col, row)
        d2 = (2*r - X)**2 + (2*c - X)**2
        rings[d2] += 1
    return any(v >= 3 for v in rings.values())

def get_cycle_decomposition(pts, n):
    """Extract cycle structure from point list."""
    row_to_cols = defaultdict(list)
    col_to_rows = defaultdict(list)
    for c, r in pts:
        row_to_cols[r].append(c)
        col_to_rows[c].append(r)
    
    visited_rows = set()
    visited_cols = set()
    cycles = []
    
    for start_row in range(n):
        if start_row in visited_rows:
            continue
        if len(row_to_cols[start_row]) == 0:
            continue
        
        cycle = []
        r = start_row
        while r not in visited_rows:
            visited_rows.add(r)
            next_cols = [c for c in row_to_cols[r] if c not in visited_cols]
            if not next_cols:
                break
            c = next_cols[0]
            visited_cols.add(c)
            cycle.append(r)
            cycle.append(c)
            next_rows = [rr for rr in col_to_rows[c] if rr != r]
            if not next_rows:
                break
            r = next_rows[0]
        
        if cycle:
            cycles.append(tuple(cycle))
    
    # Return sorted cycle HALF-lengths (each full cycle is row-col-row-col-...)
    half_lens = tuple(sorted(len(c) // 2 for c in cycles))
    return half_lens

def format_cycle_type(ct):
    """Format cycle type as human-readable string."""
    parts = []
    for l in ct:
        parts.append(str(l))
    return '(' + ','.join(parts) + ')'

# Analyze n=20 to 31
print(f"{'n':>3} {'Missing':>8} {'Unique types':>12} {'Largest cluster':>16} {'Top 3 cycle types'}")
print("-" * 85)

for n in range(20, 32):
    # Get all Flammenkamp files for this n
    files = sorted([f for f in os.listdir(CACHE) if f.startswith(f'n{n}_')])
    
    missing_cycle_types = Counter()
    
    for fname in files:
        with open(os.path.join(CACHE, fname)) as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines or '<html' in lines[0].lower():
            continue
        
        for line in lines:
            try:
                pts = decode_flam(line, n)
                if not has_center(n, pts):
                    ct = get_cycle_decomposition(pts, n)
                    missing_cycle_types[ct] += 1
            except (KeyError, IndexError):
                pass
    
    if missing_cycle_types:
        total = sum(missing_cycle_types.values())
        largest = max(missing_cycle_types.values())
        top3 = missing_cycle_types.most_common(3)
        top3_str = ' ≫ '.join([f"{format_cycle_type(ct)}×{cnt}" for ct, cnt in top3])
        print(f"{n:>3} {total:>8} {len(missing_cycle_types):>12} {largest:>16} {top3_str}")
    else:
        print(f"{n:>3} {'0':>8} {'--':>12} {'--':>16} (no missing-center solutions)")
