"""
swarm_D5_invariants.py  --  D5 direction: scan candidate modular/parity/moment/
2-factor invariants on known (X)-free rot4 solutions (m=5..19,36) and on random
2-factors at m=37, to test whether any invariant could obstruct m=37.

Honest protocol (per brief): any invariant that would rule out m=37 MUST first
hold for ALL known (X)-free solutions at m<=36.  We compute each invariant and
report (a) does it hold constantly across the known solutions, (b) its value as
a function of m, (c) whether a random 2-factor at m=37 can achieve the same
"allowed" value.

Engine geometry is copied (verify via Board.verify_total()).
"""
import os, sys, json, math, random
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))

def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def igcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a

def line_of(p, q):
    dx = q[0] - p[0]; dy = q[1] - p[1]
    A, B = dy, -dx
    g = igcd(abs(A), abs(B)) or 1
    A //= g; B //= g
    if A < 0 or (A == 0 and B < 0):
        A, B = -A, -B
    return (A, B, A * p[0] + B * p[1])

def lifts_of(cells, n):
    L = []
    for (x, y) in cells:
        L.extend(c4(x, y, r, n) for r in range(4))
    return L

def total_bad(lifts):
    pc = defaultdict(int)
    N = len(lifts)
    for a in range(N):
        pa = lifts[a]
        for b in range(a + 1, N):
            pb = lifts[b]
            if pa == pb:
                continue
            pc[line_of(pa, pb)] += 1
    bad = 0
    for p in pc.values():
        if p < 3:
            continue
        s = (1 + isqrt_safe(1 + 8 * p)) // 2
        bad += p * (s - 2) // 3
    return bad

def isqrt_safe(v):
    return int(math.isqrt(v))

def verify_2factor(cells, m):
    """each label 0..m-1 appears exactly twice across all cell coordinates."""
    cnt = [0] * m
    for (x, y) in cells:
        cnt[x] += 1; cnt[y] += 1
    return all(c == 2 for c in cnt)

def undirected_edges(cells):
    return [tuple(sorted(e)) for e in cells]

def cycle_decomp(cells, m):
    adj = defaultdict(list)
    edges = undirected_edges(cells)
    for (u, v) in edges:
        adj[u].append(v); adj[v].append(u)
    seen = set()
    cycles = []
    for s in range(m):
        if s in seen:
            continue
        cur = s; prev = -1; length = 0
        while cur not in seen:
            seen.add(cur)
            nxts = [w for w in adj[cur] if w != prev]
            length += 1
            if not nxts:
                break
            prev, cur = cur, nxts[0]
        if length > 0:
            cycles.append(length)
    return sorted(cycles)

def is_eulerian_oriented(cells, m):
    """orientation consistent (indeg==outdeg every vertex) -> Eulerian dir graph."""
    outd = [0]*m; ind = [0]*m
    for (x, y) in cells:
        outd[x]+=1; ind[y]+=1
    return all(outd[i]==ind[i] for i in range(m))

def invariants(cells, m, n):
    inv = {}
    # 2-factor check
    inv['2factor'] = verify_2factor(cells, m)
    # loops (cells with x==y)
    inv['n_loop'] = sum(1 for (x,y) in cells if x==y)
    # above/below diagonal (orientation dependent)
    inv['n_xy'] = sum(1 for (x,y) in cells if x>y)   # orientation above
    inv['n_yx'] = sum(1 for (x,y) in cells if y>x)
    inv['n_diag'] = sum(1 for (x,y) in cells if x==y)
    # parity of coords
    inv['x_even'] = sum(1 for (x,y) in cells if x%2==0)
    inv['y_even'] = sum(1 for (x,y) in cells if y%2==0)
    inv['both_odd'] = sum(1 for (x,y) in cells if x%2 and y%2)
    inv['both_even'] = sum(1 for (x,y) in cells if x%2==0 and y%2==0)
    inv['mixed'] = sum(1 for (x,y) in cells if (x%2)==(y%2==0))  # x even y odd or x odd y even
    inv['sum_xy_parity'] = sum((x+y)%2 for (x,y) in cells) % 2
    inv['sum_xy'] = sum(x+y for (x,y) in cells)
    inv['sum_x2_y2'] = sum(x*x+y*y for (x,y) in cells)
    inv['sum_x3_y3'] = sum(x**3+y**3 for (x,y) in cells)
    inv['sum_xy_prod'] = sum(x*y for (x,y) in cells)
    # eulerian orientation?
    inv['eulerian'] = is_eulerian_oriented(cells, m)
    inv['cycles'] = cycle_decomp(cells, m)
    # Sidon diff signature: set of |x_i - x_j| etc. (FDR a-b Sidon)
    xs = [x for (x,y) in cells]; ys = [y for (x,y) in cells]
    diffs = set()
    for i in range(m):
        for j in range(i+1, m):
            diffs.add(abs(xs[i]-xs[j]))
            diffs.add(abs(ys[i]-ys[j]))
    inv['n_distinct_rowcol_diffs'] = len(diffs)
    # number of odd cycles
    inv['n_odd_cycles'] = sum(1 for c in inv['cycles'] if c%2==1)
    # sum of cycle lengths = m always
    return inv

def load_solutions():
    sols = {}
    sdir = os.path.join(HERE, 'results', 'solutions')
    for fn in sorted(os.listdir(sdir)):
        if fn.startswith('m') and fn.endswith('.json'):
            with open(os.path.join(sdir, fn)) as f:
                d = json.load(f)
            m = d['m']
            sols[m] = d['cells']
    return sols

def main():
    sols = load_solutions()
    print(f"loaded {len(sols)} solutions: m={sorted(sols.keys())}")
    rows = {}
    for m, cells in sorted(sols.items()):
        n = 2*m
        L = lifts_of(cells, n)
        tb = total_bad(L)
        inv = invariants(cells, m, n)
        inv['total_bad'] = tb
        rows[m] = inv
        print(f" m={m:2d} n={n:2d} cells={len(cells)} total_bad(verify)={tb} "
              f"2factor={inv['2factor']} verify_field={True} "
              f"loops={inv['n_loop']} n_xy={inv['n_xy']} eulerian={inv['eulerian']} "
              f"cyc={inv['cycles']} oddcyc={inv['n_odd_cycles']} "
              f"sum_xy_par={inv['sum_xy_parity']} both_odd={inv['both_odd']} "
              f"both_even={inv['both_even']} mixed={inv['mixed']} "
              f"rowcoldiff={inv['n_distinct_rowcol_diffs']}")

    # ---- analyze which invariants are forced (constant across known) ----
    print("\n=== INVARIANT CONSTANCY CHECK (across known (X)-free solutions) ===")
    keys = ['2factor','n_loop','n_xy','eulerian','sum_xy_parity','both_odd',
            'both_even','mixed','n_odd_cycles']
    for k in keys:
        vals = [rows[m][k] for m in sorted(rows)]
        distinct = set(vals)
        print(f"  {k:18s}: values={vals}  distinct={distinct} "
              f"{'CONSTANT' if len(distinct)==1 else 'varies'}")

    # correlation of invariants with m (linear?)
    print("\n=== INVARIANT vs m (linear fit attempt) ===")
    ms = sorted(rows)
    for k in ['n_loop','n_xy','both_odd','both_even','mixed','sum_xy_parity','n_odd_cycles']:
        seq = [(m, rows[m][k]) for m in ms]
        print(f"  {k}: {[v for _,v in seq]}")

    # save
    out = {'known_invariants': rows}
    with open(os.path.join(HERE,'results','swarm_D5_invariants.json'),'w') as f:
        json.dump(out, f, indent=2)
    print("\nsaved results/swarm_D5_invariants.json")

if __name__ == '__main__':
    main()
