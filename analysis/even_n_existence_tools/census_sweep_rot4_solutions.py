"""
Broad census sweep: for many rot4 (C4-symmetric) solutions in solutions_unified,
verify the six-class census identity and the "diagonal-floor" pattern:
    N1 = 3m^2-2m, N2 = N4 = 0, N3 = N5 = N6 = m^2   (NTIL solutions)
Also stress-test the identity on a non-solution full-orbit board set.
"""

import json
import math
import os
import sys
import time

import numpy as np


def load_solutions(path, n, max_solutions=None):
    """Yield point lists for each solution block in the file."""
    blocks = []
    pts = []
    in_block = False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# solution"):
                if in_block and pts:
                    blocks.append(pts)
                    if max_solutions and len(blocks) >= max_solutions:
                        return blocks
                pts = []
                in_block = True
            elif in_block and line and not line.startswith("#"):
                x, y = map(int, line.split())
                pts.append((x, y))
    if in_block and pts:
        blocks.append(pts)
    return blocks


def centered_doubled(pts, n):
    return np.array([(2 * x - (n - 1), 2 * y - (n - 1)) for x, y in pts], dtype=np.int64)


def next_prime(v):
    def isp(x):
        if x < 2:
            return False
        for d in range(2, math.isqrt(x) + 1):
            if x % d == 0:
                return False
        return True

    x = v + 1
    while not isp(x):
        x += 1
    return x


def orbit_reps(pts, n):
    P = centered_doubled(pts, n)
    seen = set()
    reps = []
    for X, Y in P:
        key = (int(X), int(Y))
        if key in seen:
            continue
        orbit = []
        for h in range(4):
            x, y = key
            for _ in range(h):
                x, y = -y, x
            orbit.append((x, y))
            seen.add((x, y))
        reps.append(key)
    assert len(reps) * 4 == len(P)
    return np.array(reps, dtype=np.int64)


def census_forms(reps, Q):
    m = len(reps)
    X, Y = reps[:, 0], reps[:, 1]
    det = np.outer(X, Y) - np.outer(Y, X)
    inn = np.outer(X, X) + np.outer(Y, Y)
    N1 = N2 = N3 = N4 = N5 = N6 = 0
    for r in range(m):
        t1 = det + det[:, r][None, :] + det[r, :][:, None]
        t2 = inn + inn[:, r][None, :] + det[r, :][:, None]
        t3 = det - det[:, r][None, :] - det[r, :][:, None]
        t4 = inn + inn[:, r][None, :] - det[r, :][:, None]
        t5 = det - inn[:, r][None, :] + inn[r, :][:, None]
        t6 = det + inn[:, r][None, :] - inn[r, :][:, None]
        N1 += int(np.count_nonzero(t1 % Q == 0))
        N2 += int(np.count_nonzero(t2 % Q == 0))
        N3 += int(np.count_nonzero(t3 % Q == 0))
        N4 += int(np.count_nonzero(t4 % Q == 0))
        N5 += int(np.count_nonzero(t5 % Q == 0))
        N6 += int(np.count_nonzero(t6 % Q == 0))
    return N1, N2, N3, N4, N5, N6


def main():
    base = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\solutions_unified"
    results = {"solutions": [], "stress": None}
    t0 = time.time()

    # rot4 solution files for even n
    files = sorted(
        f for f in os.listdir(base) if f.startswith("n") and "rot4" in f and f.endswith(".txt")
    )
    files = [f for f in files if int(f[1:].split("_")[0]) % 2 == 0]
    cap = {"n6": 3, "n8": 3, "n10": 3, "n12": 3, "n14": 3, "n16": 3, "n18": 3, "n20": 3}

    for fname in files:
        n = int(fname[1:].split("_")[0])
        if n > 20:
            continue
        maxsol = cap.get(fname.split("_")[0], 2)
        sols = load_solutions(os.path.join(base, fname), n, max_solutions=maxsol)
        Q = next_prime(6 * (n - 1) ** 2)
        for idx, pts in enumerate(sols):
            assert len(pts) == 2 * n
            reps = orbit_reps(pts, n)
            m = len(reps)
            N1, N2, N3, N4, N5, N6 = census_forms(reps, Q)
            weighted = N1 + 3 * (N2 + N3 + N4 + N5 + N6)
            ok_identity = (4 * weighted == 12 * n * n - 4 * n)
            # diagonal floors
            floors = (N1 == 3 * m * m - 2 * m and N2 == 0 and N4 == 0
                      and N3 == m * m and N5 == m * m and N6 == m * m)
            results["solutions"].append({
                "n": n, "m": m, "file": fname, "idx": idx,
                "N1": N1, "N2": N2, "N3": N3, "N4": N4, "N5": N5, "N6": N6,
                "identity_ok": ok_identity, "at_floor": floors,
            })
            print(f"n={n} {fname}#{idx}: N=({N1},{N2},{N3},{N4},{N5},{N6}) "
                  f"floor={floors} id={ok_identity}")

    # stress test: full board orbit set (all n^2/4 orbits; NOT a valid NTIL
    # config, but the census identity must still hold for any C4-invariant set)
    n = 8
    allpts = [(x, y) for x in range(n) for y in range(n)]
    reps = orbit_reps(allpts, n)
    Q = next_prime(6 * (n - 1) ** 2)
    N1, N2, N3, N4, N5, N6 = census_forms(reps, Q)
    # for the full board the identity becomes 4*weighted = 6*C_col + 3N^2-2N
    # with N = n^2 points; C_col for the full board is computable:
    # every line with >=3 points... just brute force on n=8 board points (64)
    Ccol = 0
    P = [(x, y) for x in range(n) for y in range(n)]
    Npt = len(P)
    for i in range(Npt):
        xi, yi = P[i]
        for j in range(i + 1, Npt):
            xj, yj = P[j]
            dx, dy = xj - xi, yj - yi
            for k in range(j + 1, Npt):
                xk, yk = P[k]
                if dx * (yk - yi) - dy * (xk - xi) == 0:
                    Ccol += 1
    weighted = N1 + 3 * (N2 + N3 + N4 + N5 + N6)
    rhs = 6 * Ccol + 3 * Npt * Npt - 2 * Npt
    results["stress"] = {
        "n": n, "m": len(reps), "N1": N1, "N2": N2, "N3": N3, "N4": N4,
        "N5": N5, "N6": N6, "C_col": Ccol, "4weighted": 4 * weighted,
        "rhs": rhs, "identity_ok": 4 * weighted == rhs,
    }
    print("stress full-board n=8:", results["stress"])

    with open("census_sweep_rot4.json", "w") as f:
        json.dump(results, f, indent=1)
    print(f"elapsed {time.time()-t0:.1f}s  -> census_sweep_rot4.json")


if __name__ == "__main__":
    main()
