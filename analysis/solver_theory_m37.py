"""
solver_theory_m37.py  --  Theory-guided solver for rot4-NTIL (m=37), built on the
Th-44 decomposition and ALL established structural theory.

Decomposition (SIRH / Th-44):
  rot4-NTIL  <=>  2-factor (simple 2-regular graph on {0..m-1})
                  + orientation (per edge: cell (u,v) or (v,u))
                  + (X)  no 3 of the 4m C4-lifts collinear
                  + (S)  [subsumed by (X) on the fundamental domain]

Why this is strictly better than blind / csearch2:
  * The 2-factor constraint rowSum[i]+colSum[i]==2 is NECESSARY (Part I/FDR
    linear layer).  Enforcing it keeps every searched configuration inside the
    feasible subset, so "row/col has exactly 2 points" is automatic.
  * A simple 2-regular graph has NO 2-cycles (parallel edges {u,v},{v,u}).
    Those 666 transposed pairs (m(m-1)/2=666) are EXACTLY the 2-cycles, so the
    high-codegree anomaly we found is forbidden for FREE.
  * (X) is the only remaining hard part; it is checked incrementally.

Validation strategy: recover known solutions for m=5..12 (proves the framework
+ (X)-checker are correct), then attack m=37 and report the residual (X) count.

Representation note: a 2-factor edge e={u,v} (u<=v, loops u=v) maps to ONE
fundamental cell.  Orientation chooses (u,v) vs (v,u) (loops fixed to (u,u)).
The m cells produce 4m lifts via C4 rotation about the n=2m board.
"""
import os, sys, time, json, math, random
from collections import defaultdict
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# geometry (consistent with csearch2.cpp / asymmetric_lll_m37.py)
# ---------------------------------------------------------------------------
def c4(x, y, r, n):
    if r == 0:
        return (x, y)
    if r == 1:
        return (n - 1 - y, x)
    if r == 2:
        return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def igcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a

def line_of(p, q):
    """Canonical line signature through p,q.

    Robust form: the primitive normal (A,B) = (dy, -dx) of the direction
    p->q, reduced and sign-canonicalized, together with the invariant level
    L = A*x + B*y (constant along the whole line).  Two points on the SAME
    geometric line always yield the identical (A,B,L); non-collinear points
    do not.  (The earlier (A,B,C)-divided-by-gcd(A,B,C) form could flip the
    sign of C when gcd(A,B,C) != gcd(A,B), silently splitting one line into
    several signatures -- the source of the incremental drift.)"""
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    A, B = dy, -dx
    g = igcd(abs(A), abs(B)) or 1
    A //= g; B //= g
    if A < 0 or (A == 0 and B < 0):
        A, B = -A, -B
    L = A * p[0] + B * p[1]
    return (A, B, L)

# ---------------------------------------------------------------------------
# 2-factor generation (simple 2-regular graph, loops allowed, NO 2-cycles)
# ---------------------------------------------------------------------------
def generate_2factor(m, rng, maxtries=2000):
    """Return list of edges as (u,v) with u<=v (loop: u=v). Simple graph:
    no multiedge, no 2-cycle {u,v}+{v,u}. Exactly m edges, 2-regular."""
    for _ in range(maxtries):
        stubs = []
        for v in range(m):
            stubs.append(v); stubs.append(v)
        rng.shuffle(stubs)
        edges = []
        seen = set()
        ok = True
        for k in range(0, 2 * m, 2):
            a, b = stubs[k], stubs[k + 1]
            if a == b:
                e = (a, a)            # loop allowed
            else:
                u, v = (a, b) if a < b else (b, a)
                e = (u, v)
                if e in seen:         # would create multiedge or 2-cycle -> reject
                    ok = False; break
            seen.add(e); edges.append(e)
        if ok and len(edges) == m:
            return edges
    return None

def orient(edges, rng):
    """Random orientation: non-loop edge -> (u,v) or (v,u); loop -> (u,u)."""
    cells = []
    for (u, v) in edges:
        if u == v:
            cells.append((u, u))
        else:
            cells.append((u, v) if rng.getrandbits(1) else (v, u))
    return cells

# ---------------------------------------------------------------------------
# incremental (X) board
# ---------------------------------------------------------------------------
class Board:
    def __init__(self, m):
        self.m = m
        self.n = 2 * m
        self.edges = []          # list of (u,v), u<=v
        self.cells = []          # list of (x,y), one per edge (same index)
        self.lifts = []          # list of 4m points
        self.present = []
        # INCREMENTAL pair-count: pc[line_sig] = number of point-PAIRS on that
        # geometric line.  A line with s points has p=C(s,2) pairs; total (X)
        # defects = sum over lines of C(s,3) = sum p*(sqrt(1+8p)-3)/6.
        # This is algebraically exact (each pair is counted exactly once and a
        # move only changes pairs touching the moved lifts), so it cannot drift
        # the way a membership-set incremental did.  Cost per move O(|M|*n).
        self.pc = defaultdict(int)
        self.hot = defaultdict(int)  # per-edge count of defect lines (s>=3) it touches
        self.line_pts = defaultdict(lambda: defaultdict(int))  # line_sig -> lift -> #pairs on it
        self.line_hot = {}   # line_sig -> set of edges currently counted in hot for this line
        self.total_bad = 0

    def _lift_cell(self, cell):
        return [c4(cell[0], cell[1], r, self.n) for r in range(4)]

    @staticmethod
    def _c3_from_pairs(p):
        # p = C(s,2).  Return C(s,3) = p*(s-2)/3, s = (1+sqrt(1+8p))/2.
        if p < 3:
            return 0
        s = (1 + isqrt(1 + 8 * p)) // 2
        return p * (s - 2) // 3

    def _rebuild_pc(self):
        """Full pair-count rebuild from current lifts (used at build() and as a
        correctness reference).  O(n^2).  Also rebuilds self.hot = per-edge count
        of defect lines (s >= 3) it participates in."""
        self.pc.clear()
        self.hot.clear()
        self.line_pts.clear()
        L = self.lifts
        N = len(L)
        for a in range(N):
            pa = L[a]
            for b in range(a + 1, N):
                pb = L[b]
                if pa[0] == pb[0] and pa[1] == pb[1]:
                    continue
                k = line_of(pa, pb)
                self.pc[k] += 1
                self.line_pts[k][a] += 1
                self.line_pts[k][b] += 1
        for k, pts in self.line_pts.items():
            if len(pts) >= 3:
                edges = {i >> 2 for i in pts}
                self.line_hot[k] = edges
                for e in edges:
                    self.hot[e] += 1

    def _recompute_total(self):
        self.total_bad = sum(self._c3_from_pairs(p) for p in self.pc.values())

    def _reconcile_hot(self, k):
        """Reconcile self.hot / self.line_hot for line k against its CURRENT point
        set.  Called after every pair add/remove on line k, so membership swaps
        that do not cross the s=3 threshold are still tracked correctly."""
        lp = self.line_pts.get(k)
        npts = len(lp) if lp else 0
        new_edges = {i >> 2 for i in lp} if lp else set()
        old = self.line_hot.get(k)
        if npts >= 3:
            if old is None:
                old = set()
            for e in new_edges - old:
                self.hot[e] += 1
            for e in old - new_edges:
                self.hot[e] -= 1
                if self.hot[e] == 0:
                    del self.hot[e]
            self.line_hot[k] = new_edges
        else:
            if old:
                for e in old:
                    self.hot[e] -= 1
                    if self.hot[e] == 0:
                        del self.hot[e]
                del self.line_hot[k]

    def _adjust(self, M, pos, sign):
        """Add (sign=+1) or remove (sign=-1) all pairs that touch a moved lift.

        Each unordered touched pair is processed EXACTLY ONCE, by splitting into
        (a) cross pairs: one endpoint in M, the other not -- iterate i in M over
        all non-M j; (b) within-M pairs: both endpoints in M -- iterate i<j over
        M only.  This avoids the earlier double-count bug (processing each
        endpoint independently would count within-M pairs twice, breaking pc)."""
        N = len(self.lifts)
        Mset = set(M)
        # (a) cross pairs
        for i in M:
            pi = pos[i]
            for j in range(N):
                if j in Mset or j == i:
                    continue
                pj = self.lifts[j]
                if pj[0] == pi[0] and pj[1] == pi[1]:
                    continue
                k = line_of(pi, pj)
                if sign < 0:
                    self.pc[k] -= 1
                    if self.pc[k] == 0:
                        del self.pc[k]
                    lp = self.line_pts.get(k)
                    if lp is not None:
                        lp[i] -= 1
                        if lp[i] == 0:
                            del lp[i]
                        lp[j] -= 1
                        if lp[j] == 0:
                            del lp[j]
                        if not lp:
                            del self.line_pts[k]
                else:
                    self.pc[k] += 1
                    lp = self.line_pts.setdefault(k, defaultdict(int))
                    lp[i] += 1
                    lp[j] += 1
                self._reconcile_hot(k)
        # (b) within-M pairs (count once via i<j)
        ms = sorted(M)
        L = len(ms)
        for a in range(L):
            ia = ms[a]
            pia = pos[ia]
            for b in range(a + 1, L):
                ib = ms[b]
                pib = pos[ib]
                if pia[0] == pib[0] and pia[1] == pib[1]:
                    continue
                k = line_of(pia, pib)
                if sign < 0:
                    self.pc[k] -= 1
                    if self.pc[k] == 0:
                        del self.pc[k]
                    lp = self.line_pts.get(k)
                    if lp is not None:
                        lp[ia] -= 1
                        if lp[ia] == 0:
                            del lp[ia]
                        lp[ib] -= 1
                        if lp[ib] == 0:
                            del lp[ib]
                        if not lp:
                            del self.line_pts[k]
                else:
                    self.pc[k] += 1
                    lp = self.line_pts.setdefault(k, defaultdict(int))
                    lp[ia] += 1
                    lp[ib] += 1
                self._reconcile_hot(k)

    def build(self, edges, cells):
        self.edges = [tuple(e) for e in edges]
        self.cells = [tuple(c) for c in cells]
        self.lifts = []
        for c in cells:
            self.lifts.extend(self._lift_cell(c))
        self.present = [True] * len(self.lifts)
        self._rebuild_pc()
        self._recompute_total()

    # ---- moves that PRESERVE the 2-factor (edges unchanged) ----
    def flip_orientation(self, eidx):
        """Toggle cell of non-loop edge eidx between (u,v) and (v,u)."""
        u, v = self.edges[eidx]
        if u == v:
            return 0
        old = self.cells[eidx]
        new = (v, u) if old == (u, v) else (u, v)
        M = [4 * eidx + r for r in range(4)]
        oldpos = {i: self.lifts[i] for i in M}
        self._adjust(M, oldpos, -1)
        self.cells[eidx] = new
        for r in range(4):
            self.lifts[M[r]] = self._lift_cell(new)[r]
        newpos = {i: self.lifts[i] for i in M}
        self._adjust(M, newpos, +1)
        self._recompute_total()
        return 0  # delta tracked via total_bad directly

    def undo_flip(self, eidx, old_cell):
        M = [4 * eidx + r for r in range(4)]
        newpos = {i: self.lifts[i] for i in M}
        self._adjust(M, newpos, -1)
        self.cells[eidx] = old_cell
        for r in range(4):
            self.lifts[M[r]] = self._lift_cell(old_cell)[r]
        oldpos = {i: self.lifts[i] for i in M}
        self._adjust(M, oldpos, +1)
        self._recompute_total()

    def two_switch(self, e1, e2):
        """Replace edges {a,b},{c,d} with {a,d},{c,b} (all 4 distinct).
        Restructures the 2-factor; preserves 2-regular simple graph.
        Returns (delta, undo_info).  undo_info is None if the move was refused
        (would create a multiedge / 2-cycle)."""
        a, b = self.edges[e1]
        c, d = self.edges[e2]
        if len({a, b, c, d}) != 4:
            return 0, None
        new1 = (min(a, d), max(a, d))   # edge e1 reconnects a--d
        new2 = (min(c, b), max(c, b))   # edge e2 reconnects c--b
        others = self._other_edges({e1, e2})
        if new1 in others or new2 in others:
            return 0, None               # would create a multiedge
        before = self.total_bad
        old_edges = (self.edges[e1], self.edges[e2])
        old_cells = (self.cells[e1], self.cells[e2])
        M = [4 * e1 + r for r in range(4)] + [4 * e2 + r for r in range(4)]
        oldpos = {i: self.lifts[i] for i in M}
        self._adjust(M, oldpos, -1)
        self.edges[e1] = new1
        self.edges[e2] = new2
        self.cells[e1] = self._orient_edge(new1)
        self.cells[e2] = self._orient_edge(new2)
        for eidx in (e1, e2):
            nl = self._lift_cell(self.cells[eidx])
            for r in range(4):
                self.lifts[4 * eidx + r] = nl[r]
        newpos = {i: self.lifts[i] for i in M}
        self._adjust(M, newpos, +1)
        self._recompute_total()
        delta = self.total_bad - before
        undo = (e1, e2, old_edges, old_cells)
        return delta, undo

    def undo_two_switch(self, undo):
        if undo is None:
            return
        e1, e2, old_edges, old_cells = undo
        M = [4 * e1 + r for r in range(4)] + [4 * e2 + r for r in range(4)]
        newpos = {i: self.lifts[i] for i in M}
        self._adjust(M, newpos, -1)
        self.edges[e1], self.edges[e2] = old_edges
        self.cells[e1], self.cells[e2] = old_cells
        for eidx in (e1, e2):
            nl = self._lift_cell(self.cells[eidx])
            for r in range(4):
                self.lifts[4 * eidx + r] = nl[r]
        oldpos = {i: self.lifts[i] for i in M}
        self._adjust(M, oldpos, +1)
        self._recompute_total()

    def _other_edges(self, skip):
        s = set()
        for k, e in enumerate(self.edges):
            if k not in skip:
                s.add(e)
        return s

    def _orient_edge(self, e):
        u, v = e
        if u == v:
            return (u, u)
        return (u, v)

    # ---- verification helpers (diagnostics only) ----
    def verify_total(self):
        """Recompute total_bad from a full scan of lifts; must equal self.total_bad."""
        from collections import defaultdict as _dd
        pc = _dd(int)
        L = self.lifts
        N = len(L)
        for a in range(N):
            pa = L[a]
            for b in range(a + 1, N):
                pb = L[b]
                if pa[0] == pb[0] and pa[1] == pb[1]:
                    continue
                pc[line_of(pa, pb)] += 1
        return sum(self._c3_from_pairs(p) for p in pc.values())

# ---------------------------------------------------------------------------
# brute verifier (for small-m validation)
# ---------------------------------------------------------------------------
def brute_bad(lifts):
    from collections import defaultdict as dd
    lp = dd(set)
    N = len(lifts)
    for a in range(N):
        for b in range(a + 1, N):
            if lifts[a] == lifts[b]:
                continue
            lp[line_of(lifts[a], lifts[b])].add(a)
            lp[line_of(lifts[a], lifts[b])].add(b)
    tot = 0
    for S in lp.values():
        s = len(S)
        if s >= 3:
            tot += s * (s - 1) * (s - 2) // 6
    return tot

# ---------------------------------------------------------------------------
# SA search (Iterated Local Search): geometric cooling + perturbation-from-best
# when stuck.  The perturbation is the escape mechanism that prevents the
# thrashing we saw with plain reheat/restore; it kicks the current config off
# the local optimum (applied to a COPY of the best) so SA can re-explore.
# ---------------------------------------------------------------------------
def sa_search(m, time_budget, rng, init_edges=None, init_cells=None,
              T0=8.0, Tend=0.02, flip_frac=0.6, perturb=12,
              defect_directed=False, dd_prob=0.6, logprefix=""):
    t0 = time.time()
    board = Board(m)
    if init_edges is None:
        edges = generate_2factor(m, rng)
        if edges is None:
            return None
        cells = orient(edges, rng)
    else:
        edges, cells = init_edges, init_cells
    board.build(edges, cells)
    best = board.total_bad
    best_edges = list(board.edges); best_cells = list(board.cells)
    cur = best
    E = m  # number of edges
    stuck = 0
    STUCK_LIMIT = 2500
    while time.time() - t0 < time_budget and cur > 0:
        frac = (time.time() - t0) / time_budget
        T = T0 * (Tend / T0) ** frac          # geometric cooling
        if stuck >= STUCK_LIMIT:
            # ILS perturbation: rebuild from best, apply `perturb` random moves.
            board.build(best_edges, best_cells)
            cur = best
            for _ in range(perturb):
                if rng.random() < flip_frac:
                    e = rng.randrange(E)
                    if board.edges[e][0] != board.edges[e][1]:
                        board.flip_orientation(e)
                else:
                    e1 = rng.randrange(E); e2 = rng.randrange(E)
                    if e1 != e2:
                        board.two_switch(e1, e2)   # undo dropped; perturbation is one-way
            cur = board.total_bad
            stuck = 0
            T = max(T, T0 * 0.5)                   # reheat after perturbation
        dd = defect_directed and board.hot and rng.random() < dd_prob
        if rng.random() < flip_frac:
            if dd:
                cand = [e for e in board.hot if board.edges[e][0] != board.edges[e][1]]
                e = rng.choice(cand) if cand else rng.randrange(E)
            else:
                e = rng.randrange(E)
            if board.edges[e][0] == board.edges[e][1]:
                continue
            before = board.total_bad
            board.flip_orientation(e)
            newbad = board.total_bad
            delta = newbad - before
            if newbad <= before or rng.random() < math.exp(-delta / max(T, 1e-6)):
                cur = newbad
            else:
                board.flip_orientation(e)  # revert
                cur = board.total_bad
        else:
            if dd:
                e1 = rng.choice(list(board.hot)); e2 = rng.choice(list(board.hot))
            else:
                e1 = rng.randrange(E); e2 = rng.randrange(E)
            if e1 == e2:
                continue
            before = board.total_bad
            delta, undo = board.two_switch(e1, e2)
            if undo is None:
                continue
            newbad = board.total_bad
            if newbad <= before or rng.random() < math.exp(-delta / max(T, 1e-6)):
                cur = newbad
            else:
                board.undo_two_switch(undo)
                cur = board.total_bad
        if cur < best:
            best = cur
            best_edges = list(board.edges); best_cells = list(board.cells)
            stuck = 0
        else:
            stuck += 1
    return {"best": best, "cur": cur, "edges": best_edges, "cells": best_cells,
            "time": time.time() - t0, "found": best == 0}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--validate", action="store_true",
                    help="validate m=5..12 (recover known solutions)")
    ap.add_argument("--time", type=float, default=120.0,
                    help="seconds budget per restart for m=37")
    ap.add_argument("--restarts", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260715)
    ap.add_argument("--out", default="results/solver_theory_m37.json")
    ap.add_argument("--defect-directed", action="store_true",
                    help="bias SA moves toward edges currently involved in defects")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    if args.validate:
        print("== validation: recover known solutions for m=5..10 ==")
        for m in range(5, 11):
            ok_all = True
            for trial in range(3):
                edges = generate_2factor(m, rng)
                cells = orient(edges, rng)
                board = Board(m)
                board.build(edges, cells)
                # run short SA
                res = sa_search(m, time_budget=15.0, rng=rng,
                                init_edges=edges, init_cells=cells)
                # rebuild best and brute-check
                b2 = Board(m); b2.build(res["edges"], res["cells"])
                bb = brute_bad(b2.lifts)
                # verify 2-factor (exactly 2 per index)
                rs = [0] * m; cs = [0] * m
                for (x, y) in res["cells"]:
                    rs[x] += 1; cs[y] += 1
                twf = all(rs[i] + cs[i] == 2 for i in range(m))
                status = "OK" if (res["found"] and bb == 0 and twf) else "FAIL"
                if status == "FAIL":
                    ok_all = False
                print(f"  m={m} trial={trial}: found={res['found']} "
                      f"incr_bad={res['best']} brute_bad={bb} 2factor={twf} -> {status}",
                      flush=True)
            print(f"  m={m}: {'ALL OK' if ok_all else 'SOME FAIL'}", flush=True)
        return

    # m=37 attack
    print(f"== m=37 theory-guided attack (restarts={args.restarts}, "
          f"{args.time}s each) ==")
    overall_best = None
    found = False
    for rs in range(args.restarts):
        res = sa_search(args.m, time_budget=args.time, rng=rng,
                        defect_directed=args.defect_directed)
        if res is None:
            print(f"  restart {rs}: 2-factor gen failed", flush=True); continue
        print(f"  restart {rs}: best_bad={res['best']} cur={res['cur']} "
              f"time={res['time']:.1f}s found={res['found']}", flush=True)
        if res["found"]:
            overall_best = res; found = True
        if overall_best is None or res["best"] < overall_best["best"]:
            overall_best = res
        # incremental save after every restart (resumable, pause-safe)
        _write_out(args.out, args.m, found, overall_best)
    # final save (covers the found-break case too)
    _write_out(args.out, args.m, found, overall_best)
    print(f"== {'FOUND' if found else 'not found'}, best_bad="
          f"{overall_best['best'] if overall_best else None} ; saved {args.out}")

def _write_out(path, m, found, overall_best):
    """Write the running best to JSON (called after every restart so a paused
    run still leaves a usable result)."""
    out = {
        "m": m,
        "found": found,
        "best_bad": overall_best["best"] if overall_best else None,
        "edges": overall_best["edges"] if overall_best else None,
        "cells": overall_best["cells"] if overall_best else None,
        "note": ("2-factor-constrained SA: row/col=2 automatic, 666 transposed "
                 "pairs auto-forbidden (no 2-cycles). (X) is the only residual."),
    }
    if overall_best is not None:
        bb = Board(m)
        bb.build(overall_best["edges"], overall_best["cells"])
        defects = []
        maxs = 0
        for k, p in bb.pc.items():
            s = (1 + isqrt(1 + 8 * p)) // 2
            if s >= 3:
                maxs = max(maxs, s)
                defects.append({"line": list(k), "points": s,
                                "triples": bb._c3_from_pairs(p)})
        defects.sort(key=lambda d: -d["points"])
        out["lifts"] = bb.lifts
        out["n_defect_lines"] = len(defects)
        out["max_line_size"] = maxs
        out["defect_lines"] = defects[:50]  # top 50 worst lines
        out["n_lifts"] = len(bb.lifts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
