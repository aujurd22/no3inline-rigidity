import re, os
from collections import Counter

BASE = 'no3line-publish/analysis'

def parse_rot4_html(filepath):
    with open(filepath, 'r') as f:
        html = f.read()
    
    pre_match = re.search(r'<pre>\s*\n(.*?)</pre>', html, re.DOTALL)
    if not pre_match:
        return None
    pre_content = pre_match.group(1)
    
    enc_match = re.search(r'Encoding:\s*(\S+)', pre_content)
    encoding = enc_match.group(1) if enc_match else 'N/A'
    
    lines = pre_content.split('\n')
    grid_rows = []
    for l in lines:
        stripped = l.strip()
        cells = stripped.split()
        if len(cells) >= 4:
            all_cells = all(c in '.o' for c in cells)
            if all_cells:
                grid_rows.append(cells)
    
    n = len(grid_rows)
    points = []
    for row_idx, row in enumerate(grid_rows):
        for col_idx, cell in enumerate(row):
            if cell == 'o':
                points.append((row_idx, col_idx))
    
    return {'n': n, 'points': points, 'encoding': encoding}

def analyze(n, points):
    point_set = set(points)
    c4_ok = all(((n-1-j, i) in point_set) for (i,j) in points)
    
    orbits = {}
    for (i,j) in points:
        orbit = tuple(sorted([(i,j), (n-1-j,i), (n-1-i,n-1-j), (j,n-1-i)]))
        orbits.setdefault(orbit, set()).add((i,j))
    
    orbit_sizes = Counter(len(v) for v in orbits.values())
    num_orbits = len(orbits)
    
    center = ((n-1)/2.0, (n-1)/2.0)
    rings = Counter()
    for (i,j) in points:
        d2 = int(round((i-center[0])**2 + (j-center[1])**2))
        rings[d2] += 1
    
    unique_rings = len(rings)
    ring_per_orbit = num_orbits / unique_rings if unique_rings > 0 else 0
    avg_ring_pop = sum(rings.values()) / unique_rings if unique_rings > 0 else 0
    max_ring_pop = max(rings.values()) if rings else 0
    
    orbit_ring_counts = []
    for orbit, orbit_pts in orbits.items():
        orbit_rings = set()
        for (i,j) in orbit_pts:
            d2 = int(round((i-center[0])**2 + (j-center[1])**2))
            orbit_rings.add(d2)
        orbit_ring_counts.append(len(orbit_rings))
    
    pure_orbits = sum(1 for c in orbit_ring_counts if c == 1)
    mixed_orbits = sum(1 for c in orbit_ring_counts if c > 1)
    
    row_counts = Counter(p[0] for p in points)
    col_counts = Counter(p[1] for p in points)
    
    return {
        'n': n, 'points': len(points), 'target': 2*n, 'c4_ok': c4_ok,
        'orbits': num_orbits, 'orbit_sizes': dict(orbit_sizes),
        'unique_rings': unique_rings, 'ring_per_orbit': ring_per_orbit,
        'avg_ring_pop': avg_ring_pop, 'max_ring_pop': max_ring_pop,
        'pure_orbits': pure_orbits, 'mixed_orbits': mixed_orbits,
        'row_uniform': all(v==2 for v in row_counts.values()),
        'col_uniform': all(v==2 for v in col_counts.values()),
        'rings_ge3': sum(1 for v in rings.values() if v >= 3)
    }

files = {
    12: f'{BASE}/n12_rot4.html',
    14: f'{BASE}/n14_rot4.html',
    16: f'{BASE}/n16_rot4.html',
    18: f'{BASE}/n18_rot4.html',
    72: f'{BASE}/n72_raw.html'
}

results = {}
for n_val, filepath in files.items():
    data = parse_rot4_html(filepath)
    if data:
        results[n_val] = analyze(data['n'], data['points'])
        results[n_val]['encoding'] = data['encoding']

print("=" * 100)
print("C4 (rot4) Solution Evolution Across Even n")
print("=" * 100)
print()

header = f"{'n':>4} {'Pts':>5} {'Orbits':>7} {'Rings':>7} {'R/O':>6} {'AvgPop':>7} {'MaxPop':>7} {'Pure':>7} {'Mixed':>7} {'R>=3':>5} {'Row2':>5} {'Col2':>5}"
print(header)
print("-" * len(header))

for n_val in sorted(results.keys()):
    r = results[n_val]
    pure_pct = r['pure_orbits']/r['orbits']*100 if r['orbits'] > 0 else 0
    print(f"{r['n']:>4} {r['points']:>5} {r['orbits']:>7} {r['unique_rings']:>7} {r['ring_per_orbit']:>6.2f} {r['avg_ring_pop']:>7.1f} {r['max_ring_pop']:>7} {pure_pct:>6.1f}% {r['mixed_orbits']:>7} {r['rings_ge3']:>5} {str(r['row_uniform']):>5} {str(r['col_uniform']):>5}")

print()
print("=" * 100)
print("Orbit Size Distribution")
print("=" * 100)
for n_val in sorted(results.keys()):
    r = results[n_val]
    sizes = r['orbit_sizes']
    size_str = ', '.join(f'{cnt}x{sz}' for sz, cnt in sorted(sizes.items()))
    print(f"n={n_val}: {size_str}")

print()
print("=" * 100)
print("Scaling Analysis")
print("=" * 100)
ns = sorted(results.keys())
for n in ns:
    r = results[n]
    theory_max = n // 2
    print(f"n={n}: orbits={r['orbits']} (theory max=n/2={theory_max}), actual/theory={r['orbits']/theory_max:.3f}")
    print(f"       rings={r['unique_rings']} (orbits/rings={r['ring_per_orbit']:.3f})")
    print(f"       pure orbits: {r['pure_orbits']}")

print()
print("=" * 100)
print("n=72 Full Coordinate List")
print("=" * 100)
data72 = parse_rot4_html(f'{BASE}/n72_raw.html')
pts = sorted(data72['points'])
for row in range(72):
    row_pts = sorted([col for (r,col) in pts if r == row])
    print(f"  Row {row:2d}: {row_pts}")
