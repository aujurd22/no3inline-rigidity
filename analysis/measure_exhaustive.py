"""
measure_exhaustive.py -- measure the COMPLETE (exhaustive) DFS search-tree size
for rot4-NTIL as a function of m, to estimate how long a full brute-force /
exhaustive nibble search would take at m=37.

We measure the permutation type (k=0: every vertex o_i=1) exhaustive tree, which
is the SMALLEST of all 2-factor types (it is the single densest / most pruned
slice). This gives a strict LOWER BOUND on the full exhaustive tree, whose true
size = SUM over all type multisets {o_i} of the per-type tree.

For each m we count:
  * nodes  = every (i,j) placement attempt in the complete DFS (no node budget,
             no randomness, no early stop) for the fixed order out_list=[0..m-1].
  * sols   = number of complete no-3-collinear permutation 2-factors of that type.
Then we fit nodes(m) ~ c * r^m and extrapolate to m=37.
"""
import sys, time, math, json, os

sys.path.insert(0, ".")
from quadratic_sidon_completeness import c4, brute_collinear


def orbit_c4(cell, n):
    return [c4(cell, r, n) for r in range(4)]


def reduced_dirs(n):
    dirs = set()
    for dx in range(-(n - 1), n):
        for dy in range(0, n):
            if dx == 0 and dy == 0:
                continue
            g = math.gcd(abs(dx), dy) or 1
            rdx, rdy = dx // g, dy // g
            if rdx < 0 or (rdx == 0 and rdy < 0):
                rdx, rdy = -rdx, -rdy
            dirs.add((rdx, rdy))
    return dirs


def generate_constraints(m):
    n = 2 * m
    reps = [(x, y) for x in range(m) for y in range(m)]
    orbits = [orbit_c4(c, n) for c in reps]
    D = reduced_dirs(n)
    line_w = {}
    for i, (x, y) in enumerate(reps):
        for (X, Y) in orbits[i]:
            for (dx, dy) in D:
                perp = (-dy, dx)
                key = perp[0] * X + perp[1] * Y
                d = line_w.setdefault((dx, dy), {})
                k = d.setdefault(key, {})
                k[i] = k.get(i, 0) + 1
    line_cons = []
    for d, lines in line_w.items():
        for key, pos_w in lines.items():
            if sum(pos_w.values()) > 2:
                line_cons.append(dict(pos_w))
    return reps, line_cons


def exhaustive_count(m):
    reps, line_cons = generate_constraints(m)
    cell_index = {}
    for i, (a, b) in enumerate(reps):
        cell_index[(a, b)] = i
    ncell, nline = len(reps), len(line_cons)
    cell_deg = [0] * ncell
    for d in line_cons:
        for c in d:
            cell_deg[c] += 1
    cell_off = [0] * (ncell + 1)
    for c in range(ncell):
        cell_off[c + 1] = cell_off[c] + cell_deg[c]
    total_inc = cell_off[-1]
    cell_line = [0] * total_inc
    cell_w = [0] * total_inc
    cursor = cell_off[:]
    for L, d in enumerate(line_cons):
        for c, w in d.items():
            p = cursor[c]
            cell_line[p] = L
            cell_w[p] = w
            cursor[c] += 1
    load = [0] * nline

    def can_place(c):
        for idx in range(cell_off[c], cell_off[c + 1]):
            if load[cell_line[idx]] + cell_w[idx] > 2:
                return False
        return True

    def place(c):
        for idx in range(cell_off[c], cell_off[c + 1]):
            load[cell_line[idx]] += cell_w[idx]

    def unplace(c):
        for idx in range(cell_off[c], cell_off[c + 1]):
            load[cell_line[idx]] -= cell_w[idx]

    in_avail = [1] * m
    stats = {"nodes": 0, "sols": 0}

    def dfs(pos):
        if pos == m:
            stats["sols"] += 1
            return
        i = pos  # fixed order 0..m-1, k=0 permutation type
        for j in range(m):
            if in_avail[j] <= 0:
                continue
            c = cell_index[(i, j)]
            if not can_place(c):
                continue
            stats["nodes"] += 1
            place(c)
            in_avail[j] -= 1
            dfs(pos + 1)
            in_avail[j] += 1
            unplace(c)

    t0 = time.time()
    dfs(0)
    dt = time.time() - t0
    return stats["nodes"], stats["sols"], nline, dt


def main():
    mmax = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    rows = []
    for m in range(3, mmax + 1):
        nodes, sols, nline, dt = exhaustive_count(m)
        rows.append((m, nodes, sols, nline, dt))
        print(f"m={m:2d}  nodes={nodes:>15,}  sols={sols:>10,}  "
              f"lines={nline:>7,}  time={dt:8.3f}s", flush=True)
        # stop if a single m already takes too long
        if dt > 90:
            print(f"[stop] m={m} exceeded 90s wall; enough data to fit.",
                  flush=True)
            break
    # fit nodes ~ c * r^m on the last several points (log-linear)
    pts = [(m, n) for (m, n, s, nl, dt) in rows if n > 0]
    if len(pts) >= 3:
        tail = pts[-6:] if len(pts) >= 6 else pts
        xs = [p[0] for p in tail]
        ys = [math.log(p[1]) for p in tail]
        k = len(xs)
        sx = sum(xs); sy = sum(ys)
        sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
        slope = (k * sxy - sx * sy) / (k * sxx - sx * sx)
        intercept = (sy - slope * sx) / k
        r = math.exp(slope)
        c = math.exp(intercept)
        print(f"\n[fit] nodes(m) ~ {c:.4g} * ({r:.4f})^m  "
              f"(on m={xs[0]}..{xs[-1]})", flush=True)
        for M in (20, 25, 30, 37):
            est = c * r ** M
            print(f"   extrapolate m={M}: nodes ~ {est:.3e}", flush=True)
        out = {
            "rows": [{"m": m, "nodes": n, "sols": s, "lines": nl, "time_s": dt}
                     for (m, n, s, nl, dt) in rows],
            "fit": {"c": c, "r": r, "range": [xs[0], xs[-1]]},
            "extrapolation_k0_permtype": {
                str(M): c * r ** M for M in (20, 25, 30, 37)},
        }
        os.makedirs("../results", exist_ok=True)
        with open("../results/exhaustive_tree_growth.json", "w") as f:
            json.dump(out, f, indent=2)
        print("[saved] ../results/exhaustive_tree_growth.json", flush=True)


if __name__ == "__main__":
    main()
