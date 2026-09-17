"""
Verify the Switch Average Drift Theorem numerically.
For random configurations at various m, compute S(f) = sum of ΔB over all 2-switches.
Check if S(f) < 0 when B(f) > 0.
"""
import sys, math, random
from collections import defaultdict

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def line_of(p, q):
    x1, y1 = p; x2, y2 = q
    A = y2 - y1; B = x1 - x2; C = x2 * y1 - x1 * y2
    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
    if g: A //= g; B //= g; C //= g
    if A < 0 or (A == 0 and B < 0): A, B, C = -A, -B, -C
    return (A, B, C)

def compute_B(cells, m):
    N = 2 * m
    pts = [c4(c, r, N) for c in cells for r in range(4)]
    lp = defaultdict(set)
    for i in range(len(pts)):
        xi, yi = pts[i]
        for j in range(i + 1, len(pts)):
            xj, yj = pts[j]
            if xi == xj and yi == yj: continue
            k = line_of(pts[i], pts[j])
            lp[k].add(i); lp[k].add(j)
    B = 0; line_sizes = {}
    for k, s in lp.items():
        c = len(s)
        line_sizes[k] = c
        if c >= 3: B += c * (c - 1) * (c - 2) // 6
    return B, line_sizes

def compute_S(cells, m):
    """Compute S(f) = sum of ΔB over all valid 2-switches."""
    N = 2 * m
    B0, base_lines = compute_B(cells, m)
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    
    S = 0
    count_neg = 0
    count_pos = 0
    count_zero = 0
    
    for ii in range(m):
        for jj in range(ii + 1, m):
            for mt in range(3):
                # Compute the 8 affected point indices (4 from each cell)
                affected = set()
                for r in range(4):
                    affected.add(4 * ii + r)
                    affected.add(4 * jj + r)
                
                # Compute new cells after the switch
                if mt == 0:  # YSWAP
                    new_cells = list(cells)
                    new_cells[ii] = (xs[ii], ys[jj])
                    new_cells[jj] = (xs[jj], ys[ii])
                elif mt == 1:  # XSWAP
                    new_cells = list(cells)
                    new_cells[ii] = (xs[jj], ys[ii])
                    new_cells[jj] = (xs[ii], ys[jj])
                else:  # XYSWAP
                    new_cells = list(cells)
                    new_cells[ii], new_cells[jj] = cells[jj], cells[ii]
                
                B_new, _ = compute_B(new_cells, m)
                delta = B_new - B0
                S += delta
                if delta < 0: count_neg += 1
                elif delta > 0: count_pos += 1
                else: count_zero += 1
    
    return S, count_neg, count_pos, count_zero

def random_2factor(m, seed):
    rng = random.Random(seed)
    types = [1] * m
    conv = m * 35 // 100
    for _ in range(conv * 5):
        a = rng.randrange(m); b = rng.randrange(m)
        if a != b and types[a] == 1 and types[b] == 1:
            types[a] = 2; types[b] = 0; conv -= 1
            if conv == 0: break
    X, Y = [], []
    for v in range(m):
        if types[v] >= 1: X.append(v)
        if types[v] == 2: X.append(v)
        if types[v] <= 1: Y.append(v)
        if types[v] == 0: Y.append(v)
    while len(X) < m: X.append(rng.randrange(m))
    while len(Y) < m: Y.append(rng.randrange(m))
    X = X[:m]; Y = Y[:m]
    rng.shuffle(X); rng.shuffle(Y)
    cells = list(zip(X, Y))
    diag_idx = [i for i in range(m) if X[i] == Y[i]]
    while len(diag_idx) > 1:
        i = diag_idx[-1]; Y[i] = (Y[i] + 1) % m
        if X[i] == Y[i]: Y[i] = (Y[i] + 1) % m
        diag_idx = [idx for idx in range(m) if X[idx] == Y[idx]]
    return list(zip(X, Y))

print("=== Switch Average Drift: S(f) computation ===")
print("S(f) = sum of ΔB over all 3*C(m,2) valid 2-switches")
print()

for m in [5, 7, 10, 14]:
    print(f"--- m={m} ---")
    for s in range(5):
        cells = random_2factor(m, s * 7 + 3)
        B0, line_sizes = compute_B(cells, m)
        
        # Count lines by size
        size_dist = defaultdict(int)
        for sz in line_sizes.values():
            size_dist[sz] += 1
        
        S, neg, pos, zero = compute_S(cells, m)
        n_switches = 3 * m * (m - 1) // 2
        
        S_per_switch = S / n_switches if n_switches > 0 else 0
        print(f"  seed={s}: B={B0:3d}  S={S:+7d}  S̄={S_per_switch:+7.3f}  "
              f"neg={neg:3d} pos={pos:3d} zero={zero:3d}  "
              f"|Δ|≤2 lines: {size_dist.get(2,0):3d}  ≥3 lines: {size_dist.get(3,0)+size_dist.get(4,0)+size_dist.get(5,0):3d}")
    print()
