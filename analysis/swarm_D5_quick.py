import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as E

def rotate_normal(A, B):
    g = E.igcd(abs(-B), abs(A)) or 1
    rA, rB = (-B)//g, A//g
    if rA < 0 or (rA == 0 and rB < 0):
        rA, rB = -rA, -rB
    return (rA, rB)

def orbit_grouping(cfg):
    b = E.Board(cfg["m"]); b.build(cfg["edges"], cfg["cells"])
    defects = []
    for k, p in b.pc.items():
        s = (1 + math.isqrt(1 + 8 * p)) // 2
        if s >= 3:
            defects.append(k)
    n = len(defects)
    dset = set(defects); seen = set(); pairs = 0; fixed = 0
    for k in defects:
        if k in seen:
            continue
        A, B, L = k
        rA, rB = rotate_normal(A, B)
        n1 = cfg["n"]
        if -B != 0:
            t = rA / (-B)
        else:
            t = rB / A
        Lp = int(round((L - B*(n1-1)) * t))
        rk = (rA, rB, Lp)
        if rk == k:
            fixed += 1; seen.add(k)
        elif rk in dset:
            pairs += 1; seen.add(k); seen.add(rk)
    tb = b.verify_total()
    return dict(n_defect_lines=n, n_pairs=pairs, n_fixed=fixed,
                total_bad=tb, even_lines=(n % 2 == 0), even_bad=(tb % 2 == 0))

def diag_constraint(cells, m):
    n = 2*m
    return sum(1 for (u, v) in cells if u == v or u + v == n - 1)

cfg = json.load(open(os.path.join(HERE, "results", "solver_theory_m37_long.json")))
cfg["n"] = 2 * cfg["m"]
og = orbit_grouping(cfg)
print("72-config orbit grouping:", og)

sd = os.path.join(HERE, "results", "solutions")
print("\nDiagonal constraint (loops + sum-(n-1) edges) on known solutions (must be <=1):")
allok = True
for fn in sorted(os.listdir(sd)):
    if fn.startswith('m') and fn.endswith('.json'):
        d = json.load(open(os.path.join(sd, fn)))
        c = d['cells']; m = d['m']
        cnt = diag_constraint([tuple(x) for x in c], m)
        ok = cnt <= 1; allok = allok and ok
        print(f"  m={m:2d}: diag_cells={cnt} -> {'OK' if ok else 'VIOLATION'}")
print("  all known solutions satisfy diag<=1:", allok)

c72 = [tuple(x) for x in cfg['cells']]
print("\n72-config diag_cells =", diag_constraint(c72, 37), "(<=1 expected)")
