"""
Half-turn (central symmetry) NTIL search via the two-class census.

For a centrally symmetric 2n-point configuration (n orbits of size 2 under
(x,y) -> (n-1-x, n-1-y)), with representatives r_1..r_n in the lower half
(y <= (n-2)/2), the exact census identity is
    2*N1 + 6*N2 = 6*C_col + 12 n^2 - 4 n
where N1 = #{(p,q,r): det(p,q)+det(q,r)+det(r,p) == 0},
      N2 = #{(p,q,r): det(p,q)-det(q,r)-det(r,p) == 0}
(centred doubled coordinates).  Universal floors:
    N1 >= 3n^2-2n,  N2 >= n^2,
and NTIL  <=>  N1 = 3n^2-2n  and  N2 = n^2.

Search: simulated annealing over lower-half representatives, incremental
O(n^2) evaluation of the excess  E = (N1-(3n^2-2n)) + 3*(N2-n^2),
which equals 3*C_col.  A solution has E = 0.
"""

import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np


def lower_half_cells(n):
    """All cells of the fundamental domain y <= (n-2)/2."""
    return [(x, y) for x in range(n) for y in range((n - 1) // 2 + 1)]


class HTSearch:
    def __init__(self, n, seed_reps=None, rng=None):
        self.n = n
        self.rng = rng or np.random.default_rng(1)
        self.cells = lower_half_cells(n)
        self.used = set()
        self.reps = []          # list of (x,y)
        self.cx = []            # doubled-centred coords
        self.cy = []
        self.det = None         # n x n int64
        if seed_reps is not None:
            for p in seed_reps:
                self._add(p)
        else:
            self._init_random()

    def _init_random(self):
        n = self.n
        cells = self.cells[:]
        self.rng.shuffle(cells)
        for p in cells[:n]:
            self._add(p)

    def _add(self, p):
        x, y = p
        self.used.add((x, y))
        self.reps.append((x, y))
        self.cx.append(2 * x - (self.n - 1))
        self.cy.append(2 * y - (self.n - 1))
        self._rebuild_det()

    def _rebuild_det(self):
        n = self.n
        CX = np.array(self.cx, dtype=np.int64)
        CY = np.array(self.cy, dtype=np.int64)
        self.det = np.outer(CX, CY) - np.outer(CY, CX)

    def _contrib(self, i):
        """Contribution of all ordered triples containing rep index i to (N1, N2),
        with the (p,p,p) triple counted once (inclusion-exclusion)."""
        n = self.n
        det = self.det
        d_pq = det[i, :]
        d_rp = det[:, i]
        # slot 1: (p, q, r)
        m1 = d_pq[:, None] + det + d_rp[None, :]
        m2 = d_pq[:, None] - det - d_rp[None, :]
        c1 = int(np.count_nonzero(m1 == 0))
        c2 = int(np.count_nonzero(m2 == 0))
        # slot 2: (q, p, r): F(q,p,r) = det(q,p)+det(p,r)+det(r,q)
        #         det(q,p) = -det(p,q) = -d_pq[q]; det(p,r) = d_pq[r];
        #         det(r,q) = -det(q,r)
        m1 = (-d_pq)[:, None] + d_pq[None, :] - det
        m2 = (-d_pq)[:, None] - d_pq[None, :] + det
        c1 += int(np.count_nonzero(m1 == 0))
        c2 += int(np.count_nonzero(m2 == 0))
        # slot 3: (q, r, p): F(q,r,p) = det(q,r)+det(r,p)+det(p,q)
        #         det(r,p) = d_rp[r]; det(p,q) = d_pq[q]
        m1 = det + d_rp[None, :] + d_pq[:, None]
        m2 = det - d_rp[None, :] - d_pq[:, None]
        c1 += int(np.count_nonzero(m1 == 0))
        c2 += int(np.count_nonzero(m2 == 0))
        # Every ordered triple is counted exactly three times across the three
        # slots (once per position), so sum over i of C(i) = 3*N exactly.
        # No inclusion-exclusion correction is needed.
        return c1, c2

    def census(self):
        """Total N1, N2."""
        n = self.n
        N1 = N2 = 0
        for i in range(n):
            c1, c2 = self._contrib(i)
            N1 += c1
            N2 += c2
        return N1 // 3, N2 // 3

    def excess(self):
        n = self.n
        N1, N2 = self.census()
        return (N1 - (3 * n * n - 2 * n)) + 3 * (N2 - n * n), N1, N2

    def _try_move(self, p, newp):
        """Move rep p to newp; returns new excess or None if invalid."""
        if newp in self.used:
            return None
        i = self.reps.index(p)
        # recompute det slices for new position
        nx, ny = newp
        ncx = 2 * nx - (self.n - 1)
        ncy = 2 * ny - (self.n - 1)
        old_det = self.det.copy()
        # update row and column i
        CX = np.array(self.cx, dtype=np.int64)
        CY = np.array(self.cy, dtype=np.int64)
        newrow = ncx * CY - ncy * CX
        newcol = CX * ncy - CY * ncx
        self.det[i, :] = newrow
        self.det[:, i] = newcol
        self.det[i, i] = 0
        self.cx[i] = ncx
        self.cy[i] = ncy
        c1_new, c2_new = self._contrib(i)
        # restore rep p's coords to compute old contribution
        self.cx[i] = 2 * p[0] - (self.n - 1)
        self.cy[i] = 2 * p[1] - (self.n - 1)
        self.det[i, :] = self.cx[i] * CY - self.cy[i] * CX
        self.det[:, i] = CX * self.cy[i] - CY * self.cx[i]
        self.det[i, i] = 0
        c1_old, c2_old = self._contrib(i)
        # restore
        self.det = old_det
        self.cx[i] = 2 * p[0] - (self.n - 1)
        self.cy[i] = 2 * p[1] - (self.n - 1)
        # delta over N1, N2 (each triple counted in 3 contribs, so delta/3)
        return (c1_new - c1_old) / 3.0, (c2_new - c2_old) / 3.0

    def apply_move(self, p, newp):
        i = self.reps.index(p)
        self.used.discard(p)
        self.used.add(newp)
        self.reps[i] = newp
        self.cx[i] = 2 * newp[0] - (self.n - 1)
        self.cy[i] = 2 * newp[1] - (self.n - 1)
        CX = np.array(self.cx, dtype=np.int64)
        CY = np.array(self.cy, dtype=np.int64)
        self.det[i, :] = CX[i] * CY - CY[i] * CX
        self.det[:, i] = CX * CY[i] - CY * CX[i]
        self.det[i, i] = 0

    def _try_swap(self, i, j):
        """Exchange reps i,j; returns ((dN1,dN2)) delta or None if equal."""
        if i == j:
            return None
        old_det = self.det.copy()
        old_cx_i, old_cy_i = self.cx[i], self.cy[i]
        old_cx_j, old_cy_j = self.cx[j], self.cy[j]
        c1_i, c2_i = self._contrib(i)
        c1_j, c2_j = self._contrib(j)
        # swap
        self.cx[i], self.cx[j] = old_cx_j, old_cx_i
        self.cy[i], self.cy[j] = old_cy_j, old_cy_i
        CX = np.array(self.cx, dtype=np.int64)
        CY = np.array(self.cy, dtype=np.int64)
        self.det = np.outer(CX, CY) - np.outer(CY, CX)
        c1n_i, c2n_i = self._contrib(i)
        c1n_j, c2n_j = self._contrib(j)
        # restore
        self.cx[i], self.cx[j] = old_cx_i, old_cx_j
        self.cy[i], self.cy[j] = old_cy_i, old_cy_j
        self.det = old_det
        return ((c1n_i + c1n_j - c1_i - c1_j) / 3.0,
                (c2n_i + c2n_j - c2_i - c2_j) / 3.0)

    def apply_swap(self, i, j):
        self.cx[i], self.cx[j] = self.cx[j], self.cx[i]
        self.cy[i], self.cy[j] = self.cy[j], self.cy[i]
        self.reps[i], self.reps[j] = self.reps[j], self.reps[i]
        CX = np.array(self.cx, dtype=np.int64)
        CY = np.array(self.cy, dtype=np.int64)
        self.det = np.outer(CX, CY) - np.outer(CY, CX)


def run(n, seed_reps=None, steps=200000, seed=1, start_temp=30.0, cool=0.999995,
        report_every=10000, log=None, swap_prob=0.1):
    rng = np.random.default_rng(seed)
    st = HTSearch(n, seed_reps=seed_reps, rng=rng)
    E, N1, N2 = st.excess()
    T = start_temp
    best = (E, N1, N2, [p for p in st.reps])
    t0 = time.time()
    cells = lower_half_cells(n)
    if log:
        log.write(f"n={n} start E={E} N1={N1} N2={N2} ({time.time()-t0:.1f}s)\n")
    for it in range(steps):
        if rng.random() < swap_prob and n >= 2:
            # swap two random reps (both must stay in lower half; allowed)
            i = int(rng.integers(0, n)); j = int(rng.integers(0, n))
            if i == j:
                continue
            d = st._try_swap(i, j)
            dE = d[0] + 3 * d[1]
            if dE <= 0 or rng.random() < math.exp(-dE / T):
                st.apply_swap(i, j)
                E += dE
        else:
            p = st.reps[rng.integers(0, n)]
            newp = cells[rng.integers(0, len(cells))]
            d = st._try_move(p, newp)
            if d is None:
                continue
            dE = d[0] + 3 * d[1]
            if dE <= 0 or rng.random() < math.exp(-dE / T):
                st.apply_move(p, newp)
                E += dE
        if E < best[0]:
            N1, N2 = st.census()
            E = (N1 - (3 * n * n - 2 * n)) + 3 * (N2 - n * n)
            best = (E, N1, N2, [p for p in st.reps])
            if log:
                log.write(f"  step {it}: E={E} N1={N1} N2={N2}\n")
                log.flush()
            if E == 0:
                break
        T *= cool
        if it % report_every == 0 and log:
            log.write(f"  ... step {it} E~{E:.1f} T={T:.2f} elapsed {time.time()-t0:.0f}s\n")
            log.flush()
    N1, N2 = st.census()
    E = (N1 - (3 * n * n - 2 * n)) + 3 * (N2 - n * n)
    if E < best[0]:
        best = (E, N1, N2, [p for p in st.reps])
    if log:
        log.write(f"done: E={best[0]} N1={best[1]} N2={best[2]} elapsed {time.time()-t0:.1f}s\n")
        log.flush()
    return best


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--steps", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--temp", type=float, default=30.0)
    ap.add_argument("--cool", type=float, default=0.999995)
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--seedfile", type=str, default="")
    args = ap.parse_args()

    seed_reps = None
    if args.seedfile and os.path.exists(args.seedfile):
        with open(args.seedfile) as f:
            data = json.load(f)
        seed_reps = [tuple(p) for p in data["reps"]]

    log = sys.stdout
    best = run(args.n, seed_reps=seed_reps, steps=args.steps, seed=args.seed,
               start_temp=args.temp, cool=args.cool, log=log)
    E, N1, N2, reps = best
    out = {"n": args.n, "E": E, "N1": N1, "N2": N2, "solution": E == 0, "reps": reps}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)
        print("saved", args.out)
