"""
Directed repair for the half-turn NTIL census:
  - enumerate exact violating triples (N1: collinear; N2: F2' zeros),
  - remove reps involved,
  - greedily reinsert them at cells minimizing the exact census excess.
"""

import argparse
import json
import math
import random
import sys
import time

import numpy as np


def lower_half_cells(n):
    return [(x, y) for x in range(n) for y in range((n - 1) // 2 + 1)]


def census_and_violations(reps, n):
    """Exact N1, N2 and the violating (p,q,r) triples beyond the floors.
    Returns (N1, N2, v1_triples, v2_triples, det0_pairs)."""
    m = len(reps)
    R = np.array(reps, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    N1 = N2 = 0
    v1 = []
    v2 = []
    for r in range(m):
        t1 = det + det[:, r][None, :] + det[r, :][:, None]
        t2 = det - det[:, r][None, :] - det[r, :][:, None]
        N1 += int(np.count_nonzero(t1 == 0))
        N2 += int(np.count_nonzero(t2 == 0))
        z1 = np.argwhere(t1 == 0)
        z2 = np.argwhere(t2 == 0)
        for (p, q) in z1:
            # p=q slice contributes to floor; collect only distinct triples
            if p != q and q != r and r != p:
                v1.append((p, q, r))
        for (p, q) in z2:
            if p != q and q != r and r != p:
                v2.append((p, q, r))
    # det0 pairs (p!=q)
    det0 = []
    for i in range(m):
        for j in range(i + 1, m):
            if det[i, j] == 0:
                det0.append((i, j))
    return N1, N2, v1, v2, det0


def insert_delta(reps, n, cand):
    """Exact change in (N1, N2) when adding candidate cell cand to reps.
    C(new) = raw slot sums over the augmented index set.  Triples containing
    the new rep more than once are over-counted by C(new):
      * (new,new,q),(new,q,new),(q,new,new): counted twice, need once
      * (new,new,new): counted thrice, need once
    F1 vanishes on all of these, so dN1 = C1 - 3m - 2.
    For F2' only (new,new,q) always vanishes; (new,q,new) and (q,new,new)
    equal +-2 det(new,q), so dN2 = C2 - m - 2 z - 2 with
    z = #{q : det(new,q) = 0}.
    """
    m = len(reps)
    R = np.array(reps, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    Px, Py = 2 * cand[0] - (n - 1), 2 * cand[1] - (n - 1)
    # augment to m+1 indices; the new rep sits at index m
    nCX = np.append(CX, Px)
    nCY = np.append(CY, Py)
    ndet = np.outer(nCX, nCY) - np.outer(nCY, nCX)
    d_pq = ndet[m, :]
    d_rp = ndet[:, m]
    # C(new) = sum over the three slots with q,r over ALL m+1 indices;
    # each ordered triple containing the new rep is counted once per position,
    # so dN = C/3 exactly.
    c1 = int(np.count_nonzero((d_pq[:, None] + ndet + d_rp[None, :]) == 0))
    c2 = int(np.count_nonzero((d_pq[:, None] - ndet - d_rp[None, :]) == 0))
    c1 += int(np.count_nonzero(((-d_pq)[:, None] + d_pq[None, :] - ndet) == 0))
    c2 += int(np.count_nonzero(((-d_pq)[:, None] - d_pq[None, :] + ndet) == 0))
    c1 += int(np.count_nonzero((ndet + d_rp[None, :] + d_pq[:, None]) == 0))
    c2 += int(np.count_nonzero((ndet - d_rp[None, :] - d_pq[:, None]) == 0))
    z = int(np.count_nonzero(d_pq[:m] == 0))   # only old reps: det(a,q)=0
    return c1 - 3 * m - 2, c2 - m - 2 * z - 2


def pair_insert_delta(reps, n, ca, cb):
    """Exact (dN1, dN2) when adding cells ca and cb (distinct, not in reps).
    Inclusion-exclusion: dN(a,b) = dN(a) + dN(b) - J(a,b), where J counts
    ordered triples containing both new cells (each such triple is counted
    once in dN(a) and once in dN(b))."""
    d1a, d2a = insert_delta(reps, n, ca)
    d1b, d2b = insert_delta(reps, n, cb)
    m = len(reps)
    R = np.array(reps, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    def cc(c):
        return (2 * c[0] - (n - 1), 2 * c[1] - (n - 1))
    Ax, Ay = cc(ca)
    Bx, By = cc(cb)
    dA = Ax * CY - Ay * CX          # det(a, q)
    dB = Bx * CY - By * CX          # det(b, q)
    dBA = Bx * Ay - By * Ax         # det(b, a)
    # helper: F1/F2' values for triples (u,v,w) with u,v in {a,b} and w in old
    def both_count(A, B, dBA):
        """ordered triples containing both a and b (a in A-position set)."""
        # A = vector det(a,q) over q in old; B = vector det(b,q); dBA = det(b,a)
        j1 = j2 = 0
        # triples (a,b,q): F1 = det(a,b)+det(b,q)+det(q,a) = -dBA + B[q] - A[q]
        f1 = (-dBA) + B - A
        f2 = (-dBA) - B + A
        j1 += int(np.count_nonzero(f1 == 0))
        j2 += int(np.count_nonzero(f2 == 0))
        # (b,a,q): det(b,a)+det(a,q)+det(q,b) = dBA + A[q] - B[q]
        f1 = dBA + A - B
        f2 = dBA - A + B
        j1 += int(np.count_nonzero(f1 == 0))
        j2 += int(np.count_nonzero(f2 == 0))
        # (a,q,b): det(a,q)+det(q,b)+det(b,a) = A[q] - B[q] + dBA
        f1 = A - B + dBA
        f2 = A + B - dBA
        j1 += int(np.count_nonzero(f1 == 0))
        j2 += int(np.count_nonzero(f2 == 0))
        # (b,q,a): det(b,q)+det(q,a)+det(a,b) = B[q] - A[q] - dBA
        f1 = B - A - dBA
        f2 = B + A + dBA
        j1 += int(np.count_nonzero(f1 == 0))
        j2 += int(np.count_nonzero(f2 == 0))
        # (q,a,b): det(q,a)+det(a,b)+det(b,q) = -A[q] - dBA + B[q]
        f1 = -A - dBA + B
        f2 = -A + dBA - B
        j1 += int(np.count_nonzero(f1 == 0))
        j2 += int(np.count_nonzero(f2 == 0))
        # (q,b,a): det(q,b)+det(b,a)+det(a,q) = -B[q] + dBA + A[q]
        f1 = -B + dBA + A
        f2 = -B - dBA - A
        j1 += int(np.count_nonzero(f1 == 0))
        j2 += int(np.count_nonzero(f2 == 0))
        return j1, j2
    J1, J2 = both_count(dA, dB, dBA)
    # degenerate triples using only {a,b}: (a,b,a),(a,a,b),(b,a,b),(b,b,a),
    # (a,b,b),(b,a,a) -- 6 triples; each counted in both singles' deltas.
    # Compute their F values directly.
    def f1v(p, q, r):
        return (p[0]*q[1]-p[1]*q[0]) + (q[0]*r[1]-q[1]*r[0]) + (r[0]*p[1]-r[1]*p[0])
    def f2v(p, q, r):
        return (p[0]*q[1]-p[1]*q[0]) - (q[0]*r[1]-q[1]*r[0]) - (r[0]*p[1]-r[1]*p[0])
    Pca = np.array([2*ca[0]-(n-1), 2*ca[1]-(n-1)])
    Pcb = np.array([2*cb[0]-(n-1), 2*cb[1]-(n-1)])
    trip = [(Pca, Pca, Pcb), (Pca, Pcb, Pca), (Pcb, Pca, Pcb),
            (Pcb, Pcb, Pca), (Pca, Pcb, Pcb), (Pcb, Pca, Pca)]
    for (u, v, w) in trip:
        if f1v(u, v, w) == 0:
            J1 += 1
        if f2v(u, v, w) == 0:
            J2 += 1
    return d1a + d1b - J1, d2a + d2b - J2


def run(n, reps, rounds=30, seed=1, log=None):
    rng = random.Random(seed)
    cells = lower_half_cells(n)
    used = set(reps)
    m = len(reps)
    t0 = time.time()
    for rnd in range(rounds):
        N1, N2, v1, v2, det0 = census_and_violations(reps, n)
        E = (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)
        if log:
            log.write(f"round {rnd}: E={E} N1={N1} N2={N2} "
                      f"v1={len(v1)} v2={len(v2)} det0={len(det0)} ({time.time()-t0:.0f}s)\n")
            log.flush()
        if E == 0:
            return reps, E
        # collect reps involved in violations
        marked = set()
        for (p, q, r) in v1 + v2:
            marked.update([p, q, r])
        for (i, j) in det0:
            marked.update([i, j])
        marked = sorted(marked)
        # remove them (in a random order, keep the rest fixed)
        keep = [reps[i] for i in range(m) if i not in marked]
        removed = [reps[i] for i in marked]
        rng.shuffle(removed)
        used = set(keep)
        for cand_rep in removed:
            # find best cell for this rep given current set
            best = None
            for cell in cells:
                if cell in used:
                    continue
                d1, d2 = insert_delta(keep, n, cell)
                # adding a rep increases floors: floor1: 3(m+1)^2-2(m+1) vs
                # 3m^2-2m -> +6m+1; floor2: (m+1)^2-m^2 = 2m+1
                # excess change = (d1 - (6*m+1)) + 3*(d2 - (2*m+1))
                mcur = len(keep)
                dE = (d1 - (6 * mcur + 1)) + 3 * (d2 - (2 * mcur + 1))
                if best is None or dE < best[0]:
                    best = (dE, cell)
            if best is None:
                # no free cell? (should not happen)
                keep.append(cand_rep)
                used.add(cand_rep)
                continue
            _, cell = best
            keep.append(cell)
            used.add(cell)
        reps = keep
        m = len(reps)
    N1, N2, v1, v2, det0 = census_and_violations(reps, n)
    E = (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)
    return reps, E


def best_improvement(n, reps, max_sweeps=50, log=None, move_budget=8):
    """Local search restricted to reps involved in violations; each sweep
    tries every lower-half cell for each violating rep (exact delta) and
    applies the best improving move."""
    cells = lower_half_cells(n)
    m = len(reps)
    t0 = time.time()
    for sweep in range(max_sweeps):
        N1, N2, v1, v2, det0 = census_and_violations(reps, n)
        E = (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)
        if log:
            log.write(f"sweep {sweep}: E={E} N1={N1} N2={N2} v1={len(v1)} "
                      f"v2={len(v2)} det0={len(det0)} ({time.time()-t0:.0f}s)\n")
            log.flush()
        if E == 0:
            return reps, E
        marked = set()
        for (p, q, r) in v1 + v2:
            marked.update([p, q, r])
        for (i, j) in det0:
            marked.update([i, j])
        # rank reps by number of violations
        from collections import Counter
        cnt = Counter()
        for (p, q, r) in v1:
            cnt[p] += 1; cnt[q] += 1; cnt[r] += 1
        for (p, q, r) in v2:
            cnt[p] += 1; cnt[q] += 1; cnt[r] += 1
        for (i, j) in det0:
            cnt[i] += 1; cnt[j] += 1
        used = set(reps)
        improved = False
        # single moves for top violators
        for i, _ in cnt.most_common(move_budget):
            p = reps[i]
            best = None
            for cell in cells:
                if cell in used:
                    continue
                # exact delta of moving rep i to cell
                d = move_delta(n, reps, i, cell)
                if d is None:
                    continue
                dE = d[0] + 3 * d[1]
                if dE < 0 and (best is None or dE < best[0]):
                    best = (dE, cell)
            if best is not None:
                dE, cell = best
                used.discard(p)
                used.add(cell)
                reps[i] = cell
                improved = True
        # swap moves: exchange two reps (keep set unchanged)
        if not improved:
            best_swap = None
            for i in range(m):
                for j in range(i + 1, m):
                    d = swap_delta(n, reps, i, j)
                    dE = d[0] + 3 * d[1]
                    if dE < 0 and (best_swap is None or dE < best_swap[0]):
                        best_swap = (dE, i, j)
            if best_swap is not None:
                _, i, j = best_swap
                reps[i], reps[j] = reps[j], reps[i]
                improved = True
        if not improved:
            if log:
                log.write(f"  no improving move found at sweep {sweep}\n")
            break
    N1, N2, v1, v2, det0 = census_and_violations(reps, n)
    E = (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)
    return reps, E


def full_improvement(n, reps, max_sweeps=20, log=None, scope="all"):
    """Best-improvement over ALL reps (every lower-half cell), optionally
    restricted to violators + their neighbours."""
    cells = lower_half_cells(n)
    m = len(reps)
    t0 = time.time()
    for sweep in range(max_sweeps):
        N1, N2, v1, v2, det0 = census_and_violations(reps, n)
        E = (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)
        if log:
            log.write(f"fsweep {sweep}: E={E} ({time.time()-t0:.0f}s)\n")
            log.flush()
        if E == 0:
            return reps, E
        used = set(reps)
        best = None
        for i in range(m):
            p = reps[i]
            for cell in cells:
                if cell in used:
                    continue
                d = move_delta(n, reps, i, cell)
                dE = d[0] + 3 * d[1]
                if dE < 0 and (best is None or dE < best[0]):
                    best = (dE, i, cell)
        if best is None:
            if log:
                log.write(f"  no improving move (sweep {sweep})\n")
            break
        dE, i, cell = best
        used.discard(reps[i])
        used.add(cell)
        reps[i] = cell
    N1, N2, v1, v2, det0 = census_and_violations(reps, n)
    E = (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)
    return reps, E


def swap_delta(n, reps, i, j):
    """Exact (dN1, dN2) when reps i and j are exchanged."""
    m = len(reps)
    R = np.array(reps, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    def slot_counts(det, d_pq, d_rp):
        o1 = int(np.count_nonzero((d_pq[:, None] + det + d_rp[None, :]) == 0))
        o2 = int(np.count_nonzero((d_pq[:, None] - det - d_rp[None, :]) == 0))
        o1 += int(np.count_nonzero(((-d_pq)[:, None] + d_pq[None, :] - det) == 0))
        o2 += int(np.count_nonzero(((-d_pq)[:, None] - d_pq[None, :] + det) == 0))
        o1 += int(np.count_nonzero((det + d_rp[None, :] + d_pq[:, None]) == 0))
        o2 += int(np.count_nonzero((det - d_rp[None, :] - d_pq[:, None]) == 0))
        return o1, o2
    old1 = old2 = 0
    for k in (i, j):
        o1, o2 = slot_counts(det, det[k, :], det[:, k])
        old1 += o1; old2 += o2
    # swapped coords
    nCX = CX.copy(); nCY = CY.copy()
    nCX[i], nCX[j] = CX[j], CX[i]
    nCY[i], nCY[j] = CY[j], CY[i]
    ndet = np.outer(nCX, nCY) - np.outer(nCY, nCX)
    new1 = new2 = 0
    for k in (i, j):
        o1, o2 = slot_counts(ndet, ndet[k, :], ndet[:, k])
        new1 += o1; new2 += o2
    return (new1 - old1) / 3.0, (new2 - old2) / 3.0


def move_delta(n, reps, i, cell):
    """Exact (dN1, dN2) when rep i moves to cell."""
    m = len(reps)
    R = np.array(reps, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    if cell in set(reps):
        return None
    # old contributions of rep i
    d_pq = det[i, :]
    d_rp = det[:, i]
    def slot_counts(det, d_pq, d_rp):
        o1 = int(np.count_nonzero((d_pq[:, None] + det + d_rp[None, :]) == 0))
        o2 = int(np.count_nonzero((d_pq[:, None] - det - d_rp[None, :]) == 0))
        o1 += int(np.count_nonzero(((-d_pq)[:, None] + d_pq[None, :] - det) == 0))
        o2 += int(np.count_nonzero(((-d_pq)[:, None] - d_pq[None, :] + det) == 0))
        o1 += int(np.count_nonzero((det + d_rp[None, :] + d_pq[:, None]) == 0))
        o2 += int(np.count_nonzero((det - d_rp[None, :] - d_pq[:, None]) == 0))
        return o1, o2
    old1, old2 = slot_counts(det, d_pq, d_rp)
    # new: recompute row/col
    Px, Py = 2 * cell[0] - (n - 1), 2 * cell[1] - (n - 1)
    nCX = CX.copy(); nCY = CY.copy()
    nCX[i] = Px; nCY[i] = Py
    ndet = np.outer(nCX, nCY) - np.outer(nCY, nCX)
    d_pq = ndet[i, :]
    d_rp = ndet[:, i]
    new1, new2 = slot_counts(ndet, d_pq, d_rp)
    # each ordered triple containing i is counted 3x across slots, so delta/3
    return (new1 - old1) / 3.0, (new2 - old2) / 3.0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seedfile", type=str, required=True)
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--mode", type=str, default="repair",
                    choices=["repair", "improve"])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()
    with open(args.seedfile) as f:
        data = json.load(f)
    reps = [tuple(p) for p in data["reps"]]
    if args.mode == "repair":
        reps, E = run(args.n, reps, rounds=args.rounds, seed=args.seed, log=sys.stdout)
    else:
        reps, E = best_improvement(args.n, reps, max_sweeps=args.rounds, log=sys.stdout)
    out = {"n": args.n, "E": E, "solution": E == 0, "reps": reps}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)
    print("final E:", E)
