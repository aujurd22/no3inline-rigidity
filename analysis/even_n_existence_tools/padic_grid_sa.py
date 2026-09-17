"""
SA with CORRECT cost function: grid verification (counts ALL C(2n,3) collinear triples).
This fixes the count_colls blind spot that allowed degenerate (duplicate point) states.
"""
import itertools, json, time, random, math
from collections import Counter

def bitrev(n, k): return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]
def build_tps(perm, n, k):
    tps = set()
    for x in range(n):
        for b in range(k):
            y = x ^ (1 << b)
            if y > x:
                a, bb = perm[x], perm[y]
                tps.add((min(a, bb), max(a, bb)))
    return sorted(tps)

def grid_cost(p0, p1, n):
    """完整网格代价：C(2n,3) 共线 + 重复点惩罚"""
    pts = [(i, p0[i]) for i in range(n)] + [(i, p1[i]) for i in range(n)]
    unique = len(set(pts))
    degen = 2 * n - unique  # 重复点数
    collinear = 0
    for (x1, y1), (x2, y2), (x3, y3) in itertools.combinations(pts, 3):
        if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
            collinear += 1
    # Heavy penalty for degeneracy: 100 × degen (degeneracy is worse than collisions)
    # because consistent permutations don't have any duplicate points
    return collinear + 1000 * degen

def verify_ntil(p0, p1, n):
    pts = [(i, p0[i]) for i in range(n)] + [(i, p1[i]) for i in range(n)]
    unique = len(set(pts))
    if unique < 2 * n:
        return False, f"重复点{2*n-unique}"
    bad = sum(1 for (x1, y1), (x2, y2), (x3, y3) in itertools.combinations(pts, 3)
              if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1))
    return bad == 0, f"{bad}共线"

def sa_grid(p0, p1, all_tps, n, n_iter=8000, n_restarts=5):
    """SA with correct grid-based cost function"""
    cost = grid_cost(p0, p1, n)
    bp0, bp1 = p0[:], p1[:]
    bc = cost

    for rst in range(n_restarts):
        T = 50.0  # higher start T for the larger cost values
        alpha = (1.0 / T) ** (1.0 / n_iter)
        for it in range(n_iter):
            if cost == 0: break

            tp_type, a, b = random.choice(all_tps)
            if tp_type == 'p0':
                p0[a], p0[b] = p0[b], p0[a]
                nc = grid_cost(p0, p1, n)
            else:
                p1[a], p1[b] = p1[b], p1[a]
                nc = grid_cost(p0, p1, n)

            delta = nc - cost
            if delta <= 0 or random.random() < math.exp(-delta / T):
                cost = nc
                if cost < bc:
                    bp0, bp1 = p0[:], p1[:]
                    bc = cost
            else:
                # revert
                if tp_type == 'p0':
                    p0[a], p0[b] = p0[b], p0[a]
                else:
                    p1[a], p1[b] = p1[b], p1[a]

            T *= alpha

        # restart from best
        if cost > 0:
            p0[:], p1[:] = bp0[:], bp1[:]
            cost = bc

        ok, msg = verify_ntil(p0, p1, n)
        degen = 2*n - len(set([(i,p0[i]) for i in range(n)]+[(i,p1[i]) for i in range(n)]))
        print(f"  r{rst}: cost={cost} degen={degen} ntil={ok} ({msg})")

    p0[:], p1[:] = bp0[:], bp1[:]
    bc = grid_cost(p0, p1, n)
    return p0, p1, bc


random.seed(42)

for n in [8, 16]:
    k = n.bit_length() - 1
    p0o = bitrev(n, k)
    p1o = [n - 1 - x for x in p0o]

    tp0 = build_tps(p0o, n, k)
    tp1 = build_tps(p1o, n, k)
    at = [('p0', a, b) for a, b in tp0] + [('p1', a, b) for a, b in tp1]

    base_cost = grid_cost(p0o, p1o, n)
    print(f"\n{'='*64}")
    print(f"n={n}: base_cost={base_cost} |tps|={len(at)}")
    print(f"{'='*64}")

    n_iter = 8000 if n <= 16 else 4000
    n_rst = 8 if n <= 16 else 5

    t0 = time.time()
    p0f, p1f, fc = sa_grid(p0o, p1o, at, n, n_iter=n_iter, n_restarts=n_rst)
    elapsed = time.time() - t0

    ok, msg = verify_ntil(p0f, p1f, n)
    status = "★ NTIL" if ok else f"✗ {msg}"
    print(f"  最终: cost={fc} {status} ({elapsed:.1f}s)")

    if ok:
        json.dump({'n': n, 'p0': p0f, 'p1': p1f, 'time': elapsed},
                  open(f'ntil_n{n}_grid_sa.json', 'w'), indent=2)
        print(f"  → 已保存")
