"""Test greedy descent with tabu on small m."""
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
    B = 0
    for s in lp.values():
        c = len(s)
        if c >= 3: B += c * (c - 1) * (c - 2) // 6
    return B

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
    # Diagonal constraint
    diag_idx = [i for i in range(m) if X[i] == Y[i]]
    while len(diag_idx) > 1:
        i = diag_idx[-1]; Y[i] = (Y[i] + 1) % m
        if X[i] == Y[i]: Y[i] = (Y[i] + 1) % m
        diag_idx = [idx for idx in range(m) if X[idx] == Y[idx]]
    return list(zip(X, Y))

def greedy_with_tabu(cells, m, max_steps=2000, tabu_tenure=3):
    cells = list(cells)
    B = compute_B(cells, m)
    tabu = {}  # (i,j,move_type) -> remaining steps
    
    for step in range(max_steps):
        if B == 0: return True, 0, step, cells
        
        # Decay tabu
        for k in list(tabu.keys()):
            tabu[k] -= 1
            if tabu[k] <= 0: del tabu[k]
        
        best_delta = 0
        best_ijmt = None
        
        xs = [x for x, _ in cells]
        ys = [y for _, y in cells]
        
        for ii in range(m):
            for jj in range(ii + 1, m):
                if (ii, jj, 0) in tabu and (ii, jj, 1) in tabu and (ii, jj, 2) in tabu:
                    continue
                xi, yi = xs[ii], ys[ii]
                xj, yj = xs[jj], ys[jj]
                
                for mt in range(3):
                    if (ii, jj, mt) in tabu: continue
                    
                    # Compute new cells
                    if mt == 0:  # YSWAP
                        new_i = (xi, ys[jj])
                        new_j = (xj, ys[ii])
                    elif mt == 1:  # XSWAP
                        new_i = (xs[jj], yi)
                        new_j = (xs[ii], yj)
                    else:  # XYSWAP
                        new_i = (xj, yj)
                        new_j = (xi, yi)
                    
                    new_cells = list(cells)
                    new_cells[ii] = new_i
                    new_cells[jj] = new_j
                    new_B = compute_B(new_cells, m)
                    delta = new_B - B
                    
                    if delta < best_delta:
                        best_delta = delta
                        best_ijmt = (ii, jj, mt)
        
        if best_delta >= 0:
            return False, B, step, cells  # stuck
        
        # Apply best move
        ii, jj, mt = best_ijmt
        tabu[(ii, jj, mt)] = tabu_tenure
        
        if mt == 0:
            cells[ii] = (xs[ii], ys[jj])
            cells[jj] = (xs[jj], ys[ii])
        elif mt == 1:
            cells[ii] = (xs[jj], ys[ii])
            cells[jj] = (xs[ii], ys[jj])
        else:
            cells[ii], cells[jj] = cells[jj], cells[ii]
        
        B = compute_B(cells, m)
        
        if step % 200 == 0:
            print(f'  step={step} B={B} delta={best_delta}', flush=True)
    
    return False, B, step, cells

# === Sidon pre-check ===
def sidon_ok(cells, m, ii, jj, mt):
    """Check if the move would violate Sidon condition."""
    xs = [x for x,_ in cells]; ys = [y for _,y in cells]
    # Current diffs
    diffs = [xs[i]-ys[i] for i in range(len(cells))]
    from collections import Counter
    dc = Counter(diffs)
    
    # New diffs after swap
    ndi, ndj = 0, 0
    if mt == 0:  # YSWAP
        ndi = xs[ii] - ys[jj]
        ndj = xs[jj] - ys[ii]
    elif mt == 1:  # XSWAP
        ndi = xs[jj] - ys[ii]
        ndj = xs[ii] - ys[jj]
    else:  # XYSWAP
        ndi = xs[jj] - ys[jj]
        ndj = xs[ii] - ys[ii]
    
    # Remove old counts
    odi = diffs[ii]; odj = diffs[jj]
    dc[odi] -= 1; dc[odj] -= 1
    if dc[odi] <= 0: del dc[odi]
    if dc[odj] <= 0: del dc[odj]
    
    # Check new diffs
    ok = True
    for nd in [ndi, ndj]:
        if nd != odi and nd != odj:  # Really new
            cnt = dc.get(nd, 0) + dc.get(-nd, 0)
            if cnt >= 2: ok = False
        elif nd == odi and nd == odj:
            pass  # both old diffs → already handled
    
    return ok

# === Diagonal constraint ===
def diag_count(cells):
    return sum(1 for x,y in cells if x == y)

# === Main test ===
print('=== m=14 with tabu (CRITICAL TEST - red_config_frac=1.0) ===')
for s in range(50):
    cells = random_2factor(14, s * 7 + 3)
    B0 = compute_B(cells, 14)
    found, Be, steps, final = greedy_with_tabu(cells, 14, max_steps=500, tabu_tenure=3)
    print(f'seed={s:2d}: B0={B0:3d} → found={found} B_end={Be:3d} steps={steps}', flush=True)
