"""
Four-matrix C4-orbit decomposition of tr(K_t^3) -- rigorous verification.

Setup (README 4.5 + 2026-08-13 addition):
  * n even, N = 2n points, C4-symmetric configuration.
  * Centred doubled coordinates X = 2x-(n-1), Y = 2y-(n-1).
  * omega(p,q) = X Y' - Y X'  (rotation-invariant determinant form).
  * K_t(i,j) = zeta^{t omega(r_i,r_j)},  zeta = exp(2pi i / Q).
  * Orbits O_1..O_m (m = n/2) of size 4 under rho(X,Y)=(-Y,X).
  * K_t^j(p,q) = sum_{h=0..3} i^{-jh} zeta^{t omega(rho^h p, q)}   (m x m)
  * tr(K_t^3) = sum_{j=0..3} tr((K_t^j)^3).

Four phase families (centred doubled coords):
  h=0:  det(p,q)                 -> matrix a(p,q)     = zeta^{t det(p,q)}
  h=1:  omega(rho p, q) = -<p,q> -> matrix c(p,q)     = zeta^{-t<p,q>}
  h=2:  -det(p,q)                -> matrix a_bar(p,q) = conj(a(p,q))
  h=3:  +<p,q>                   -> matrix c_bar(p,q) = conj(c(p,q))

  K_t^j = a + i^{-j} c + i^{-2j} a_bar + i^{-3j} c_bar.

Cube expansion (exact, for each t):
  tr(K_t^3) = sum_j tr((K_t^j)^3)
            = 4 * sum_{h1+h2+h3 == 0 (mod 4)} tr(Phi_{h1} Phi_{h2} Phi_{h3})
  with Phi_0=a, Phi_1=c, Phi_2=a_bar, Phi_3=c_bar.

This script verifies every step numerically, then computes the six exact
t-average census counts N_class = #{orbit-representative triples (p,q,r) :
form_class(p,q,r) == 0 mod Q} and checks
    4 * (N1+..+N6) = 6*C_col + 12 n^2 - 4 n.

The six classes:
  N1 (aaa):      T1 = det(p,q)+det(q,r)+det(r,p)            [area]
  N2 (abar c c): T2 = det(p,q)+<q,r>+<r,p>
  N3 (a abar abar): T3 = det(p,q)-det(q,r)-det(r,p)
  N4 (abar cbar cbar): T4 = -det(p,q)+<q,r>+<r,p>
  N5 (a c cbar): T5 = det(p,q)-<q,r>+<r,p>
  N6 (a cbar c): T6 = det(p,q)+<q,r>-<r,p>
"""

import json
import math
import os
import time

import numpy as np


# ---------------------------------------------------------------- helpers

def load_solution(path, n):
    pts = []
    found_header = False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# solution"):
                if found_header and pts:
                    break  # first solution block only
                found_header = True
                continue
            if not line or line.startswith("#"):
                continue
            if not found_header:
                continue
            x, y = map(int, line.split())
            pts.append((x, y))
    assert len(pts) == 2 * n, f"{path}: expected {2*n} points, got {len(pts)}"
    assert all(0 <= x < n and 0 <= y < n for x, y in pts)
    return pts


def centered_doubled(pts, n):
    return np.array([(2 * x - (n - 1), 2 * y - (n - 1)) for x, y in pts], dtype=np.int64)


def collinear_triples(pts):
    """Exact count of unordered collinear triples (brute force, small N only)."""
    N = len(pts)
    cnt = 0
    for i in range(N):
        xi, yi = pts[i]
        for j in range(i + 1, N):
            xj, yj = pts[j]
            dx, dy = xj - xi, yj - yi
            for k in range(j + 1, N):
                xk, yk = pts[k]
                if dx * (yk - yi) - dy * (xk - xi) == 0:
                    cnt += 1
    return cnt


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


def build_orbit_reps(pts, n):
    """Orbit representatives (one per 4-point orbit) in centred doubled
    coordinates, using rho(X,Y)=(-Y,X).  Verifies C4 invariance."""
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
        assert len(orbit) == 4
        assert len(set(orbit)) == 4, "degenerate orbit (central point?)"
        reps.append(key)
    assert len(reps) * 4 == len(P), (len(reps), len(P))
    return np.array(reps, dtype=np.int64)


def omega_matrix(P, t, Q):
    """Full N x N matrix K_t."""
    X = P[:, 0][:, None]
    Y = P[:, 1][:, None]
    W = X * P[:, 1][None, :] - Y * P[:, 0][None, :]  # det(p,q)
    return np.exp(2j * np.pi * t * W / Q)


def block_matrix(reps, t, Q, j):
    """K_t^j on orbit representatives."""
    m = len(reps)
    K = np.zeros((m, m), dtype=complex)
    for p in range(m):
        Xp, Yp = reps[p]
        for q in range(m):
            Xq, Yq = reps[q]
            s = 0.0 + 0.0j
            for h in range(4):
                x, y = Xp, Yp
                for _ in range(h):
                    x, y = -y, x
                w = x * Yq - y * Xq  # omega(rho^h p, q)
                s += (1j) ** (-j * h) * np.exp(2j * np.pi * t * w / Q)
            K[p, q] = s
    return K


def phase_matrices(reps, t, Q):
    """Return (a, c, a_bar, c_bar)."""
    X = reps[:, 0][:, None]
    Y = reps[:, 1][:, None]
    det = X * reps[:, 1][None, :] - Y * reps[:, 0][None, :]
    inn = X * reps[:, 0][None, :] + Y * reps[:, 1][None, :]
    a = np.exp(2j * np.pi * t * det / Q)
    c = np.exp(-2j * np.pi * t * inn / Q)
    return a, c, np.conj(a), np.conj(c)


def trace3(M):
    return np.trace(M @ M @ M)


def tr_prod(M1, M2, M3):
    """tr(M1 M2 M3)."""
    return np.trace(M1 @ M2 @ M3)


def census_forms(reps, Q):
    """Exact counts of representative triples with each of the six forms
    congruent to 0 mod Q.  Returns dict N1..N6."""
    m = len(reps)
    X, Y = reps[:, 0], reps[:, 1]
    det = np.outer(X, Y) - np.outer(Y, X)          # det(p,q)
    inn = np.outer(X, X) + np.outer(Y, Y)          # <p,q>
    N1 = N2 = N3 = N4 = N5 = N6 = 0
    for r in range(m):
        # canonical class forms (p = row, q = col, r = outer loop):
        # F1 = det(p,q) + det(q,r) + det(r,p)
        t1 = det + det[:, r][None, :] + det[r, :][:, None]
        # F2 = <p,q> + <q,r> + det(r,p)
        t2 = inn + inn[:, r][None, :] + det[r, :][:, None]
        # F3 = det(p,q) - det(q,r) - det(r,p)
        t3 = det - det[:, r][None, :] - det[r, :][:, None]
        # F4 = <p,q> + <q,r> - det(r,p)
        t4 = inn + inn[:, r][None, :] - det[r, :][:, None]
        # F5 = det(p,q) - <q,r> + <r,p>
        t5 = det - inn[:, r][None, :] + inn[r, :][:, None]
        # F6 = det(p,q) + <q,r> - <r,p>
        t6 = det + inn[:, r][None, :] - inn[r, :][:, None]
        N1 += int(np.count_nonzero(t1 % Q == 0))
        N2 += int(np.count_nonzero(t2 % Q == 0))
        N3 += int(np.count_nonzero(t3 % Q == 0))
        N4 += int(np.count_nonzero(t4 % Q == 0))
        N5 += int(np.count_nonzero(t5 % Q == 0))
        N6 += int(np.count_nonzero(t6 % Q == 0))
    return {"N1_area": N1, "N2": N2, "N3": N3, "N4": N4, "N5": N5, "N6": N6,
            "weighted_sum": N1 + 3 * (N2 + N3 + N4 + N5 + N6)}


# ---------------------------------------------------------------- main

def verify(n, pts, Q, out):
    m = n // 2
    reps = build_orbit_reps(pts, n)
    assert len(reps) == m, (len(reps), m)
    P = centered_doubled(pts, n)
    Ccol = collinear_triples(pts)

    results = {"n": n, "m": m, "Q": Q, "C_col": Ccol, "N": len(P)}
    max_err_block = 0.0
    max_err_expand = 0.0
    herm_ok = True
    sym_ok = True
    diag_a_ok = True
    real_checks = True

    for t in range(1, 4):  # a few t values
        K = omega_matrix(P, t, Q)
        herm_ok &= np.max(np.abs(K - K.conj().T)) < 1e-9
        tr_full = trace3(K)
        tr_blocks = sum(trace3(block_matrix(reps, t, Q, j)) for j in range(4))
        max_err_block = max(max_err_block, abs(tr_full - tr_blocks))

        a, c, ab, cb = phase_matrices(reps, t, Q)
        err_pf = 0.0
        for j in range(4):
            Kj = block_matrix(reps, t, Q, j)
            Kj2 = a + (1j) ** (-j) * c + (1j) ** (-2 * j) * ab + (1j) ** (-3 * j) * cb
            err_pf = max(err_pf, float(np.max(np.abs(Kj - Kj2))))
        results[f"maxerr_phasefamily_t{t}"] = err_pf

        Phis = [a, c, ab, cb]
        s16 = 0.0
        for h1 in range(4):
            for h2 in range(4):
                for h3 in range(4):
                    if (h1 + h2 + h3) % 4 == 0:
                        s16 += tr_prod(Phis[h1], Phis[h2], Phis[h3])
        max_err_expand = max(max_err_expand, abs(tr_blocks - 4 * s16))

        t_a3 = tr_prod(a, a, a)
        t_ab_c2 = tr_prod(ab, c, c)
        t_a_ab2 = tr_prod(a, ab, ab)
        t_ab_cb2 = tr_prod(ab, cb, cb)
        t_a_ccb = tr_prod(a, c, cb)
        t_a_cbc = tr_prod(a, cb, c)
        six = 4 * (t_a3 + 3 * t_ab_c2 + 3 * t_a_ab2 + 3 * t_ab_cb2
                   + 3 * t_a_ccb + 3 * t_a_cbc)
        results[f"maxerr_sixclass_t{t}"] = abs(tr_blocks - six)

        herm_ok &= np.max(np.abs(a - a.conj().T)) < 1e-9
        sym_ok &= np.max(np.abs(c - c.T)) < 1e-9
        diag_a_ok &= np.max(np.abs(np.diag(a) - 1)) < 1e-9
        real_checks &= abs(t_a3.imag) < 1e-9
        real_checks &= abs(t_a_ab2.imag) < 1e-9
        real_checks &= abs(t_a_ccb.imag) < 1e-9
        real_checks &= abs(t_a_cbc.imag) < 1e-9
        # conjugacy: tr(ab c c) == conj(tr(ab cb cb))  (proved algebraically)
        real_checks &= abs(t_ab_cb2 - t_ab_c2.conjugate()) < 1e-6 * max(1.0, abs(t_ab_c2))

    results["maxerr_block"] = max_err_block
    results["maxerr_expand16"] = max_err_expand
    results["hermitian_a"] = bool(herm_ok)
    results["symmetric_c"] = bool(sym_ok)
    results["diag_a_1"] = bool(diag_a_ok)
    results["six_terms_real"] = bool(real_checks)

    cen = census_forms(reps, Q)
    results["census"] = cen
    total = cen["weighted_sum"]
    results["census_sum"] = total
    results["rhs_4sum"] = 4 * total
    results["lhs_6C_baseline"] = 6 * Ccol + 12 * n * n - 4 * n
    results["census_identity_ok"] = abs(4 * total - (6 * Ccol + 12 * n * n - 4 * n)) == 0

    out.append(results)
    return results


if __name__ == "__main__":
    base = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\solutions_unified"
    out = []
    cases = []

    for n, fname in [(8, "n8_rot4.txt"), (10, "n10_rot4.txt"), (74, "n74_rot4.txt")]:
        path = os.path.join(base, fname)
        if os.path.exists(path):
            pts = load_solution(path, n)
            Q = next_prime(6 * (n - 1) ** 2)
            cases.append((n, pts, Q, fname))

    # a random C4-symmetric NON-solution: pick m random orbits, n=8
    rng = np.random.default_rng(20260814)
    n = 8
    all_reps = build_orbit_reps([(x, y) for x in range(n) for y in range(n)], n)
    chosen = rng.choice(len(all_reps), size=n // 2, replace=False)
    pts_rand = []
    for idx in chosen:
        X, Y = all_reps[idx]
        for h in range(4):
            x, y = X, Y
            for _ in range(h):
                x, y = -y, x
            pts_rand.append(((x + n - 1) // 2, (y + n - 1) // 2))
    pts_rand = [(int(x), int(y)) for x, y in pts_rand]
    assert len(pts_rand) == 16
    cases.append((n, pts_rand, next_prime(6 * (n - 1) ** 2), "random-C4-n8"))

    t0 = time.time()
    for n, pts, Q, fname in cases:
        print(f"== verifying {fname} (n={n}, Q={Q})")
        r = verify(n, pts, Q, out)
        print(json.dumps(r, indent=1)[:1400])
    print(f"elapsed {time.time()-t0:.1f}s")
    with open("four_matrix_verification.json", "w") as f:
        json.dump(out, f, indent=1)
    print("saved four_matrix_verification.json")
