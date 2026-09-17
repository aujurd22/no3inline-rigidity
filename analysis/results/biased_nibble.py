"""
Direction G -> Gap B lever test (FIXED).

Use the empirical spatial prior found in research_G.md (free cells avoid the diagonal,
board centre and board corner; prefer a mid-radius ring; no parity bias) as a BIAS in a
2-regular (permutation) local search, and test whether it accelerates closing Gap B
(finding a conflict-free rot4 base set = a solution).

Model (Th-44 / R9b): a rot4 solution's fundamental quadrant is a PERMUTATION
cols[i] = column of the single cell in row i. Moves = 2-swaps (transpositions), which
preserve the permutation / 2-regular structure. Conflicts:
  (X) = any 3 lifted points collinear  (precomputed once per m as cell-triples)
  (S) = any slope+-1 line of the quadrant holding >=3 cells
A config with bad_X=bad_S=0 is a valid rot4 solution.

We compare UNBIASED SA (objective = bad_X+bad_S) vs BIASED SA (objective = bad_X+bad_S
+ LAMBDA*penalty, where penalty pushes cells toward the high-prior annular/anti-diagonal
region). Validate the lever on m=36 (known solvable); then attack m=37 (OPEN).

IMPORTANT: a config is "solved" iff bad_X==0 AND bad_S==0. The biased objective never
reaches 0 because of the penalty term, so we must detect solves by VALIDITY, not by
objective==0.
"""
import os, sys, json, random, math, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'biased_nibble.json')
PROG = os.path.join(HERE, 'biased_nibble_progress.log')

# Aggregate board-radial profile from cell_distribution.json (rho 0..1 from board centre;
# 1.0 = uniform). Used as the continuous prior for arbitrary m.
AGG_RADIAL = [0.55, 0.83, 0.77, 0.81, 0.93, 1.02, 1.39, 1.33, 0.44, 0.14]
RAD_BINS = [0.05 * (i * 2 + 1) for i in range(10)]  # 0.05..0.95
DIAG_R = 0.50      # x==y
NEAR_R = 0.70      # |x-y|<=1
OFF_R = 1.06       # off-diagonal

LAMBDA = 0.5
TS = lambda: time.strftime('%H:%M:%S')


def prior_ratio(x, y, m):
    """Continuous extrapolation of the empirical P(cell)/(1/m) for arbitrary m."""
    cx, cy = m - 0.5, m - 0.5
    d = math.hypot(x - cx, y - cy)
    dmax = math.hypot(m - 0.5, m - 0.5)
    rho = d / dmax
    if rho <= RAD_BINS[0]:
        rad = AGG_RADIAL[0]
    elif rho >= RAD_BINS[-1]:
        rad = AGG_RADIAL[-1]
    else:
        for i in range(9):
            if RAD_BINS[i] <= rho <= RAD_BINS[i + 1]:
                t = (rho - RAD_BINS[i]) / (RAD_BINS[i + 1] - RAD_BINS[i])
                rad = AGG_RADIAL[i] * (1 - t) + AGG_RADIAL[i + 1] * t
                break
    if x == y:
        diag = DIAG_R
    elif abs(x - y) <= 1:
        diag = NEAR_R
    else:
        diag = OFF_R
    return rad * diag


def lifted_points(x, y, m):
    return [(x, y), (2 * m - 1 - y, x), (2 * m - 1 - x, 2 * m - 1 - y), (y, 2 * m - 1 - x)]


_PRECOMP = {}   # cache keyed by m


def precompute(m):
    if m in _PRECOMP:
        return _PRECOMP[m]
    cells = [(x, y) for x in range(m) for y in range(m)]
    lift = {}
    for c in cells:
        for p in lifted_points(c[0], c[1], m):
            lift[p] = c
    pts = list(lift.keys())
    ptset = set(pts)
    Xset = set()
    for i in range(len(pts)):
        p1 = pts[i]
        c1 = lift[p1]
        for j in range(i + 1, len(pts)):
            p2 = pts[j]
            c2 = lift[p2]
            if c2 <= c1:
                continue
            for p3 in ((2 * p2[0] - p1[0], 2 * p2[1] - p1[1]),
                      (2 * p1[0] - p2[0], 2 * p1[1] - p2[1])):
                if p3 in ptset:
                    c3 = lift[p3]
                    if c3 != c1 and c3 != c2:
                        Xset.add(tuple(sorted([c1, c2, c3])))
    Xtriples = list(Xset)
    cell_triples = defaultdict(list)
    for t in Xtriples:
        for c in t:
            cell_triples[c].append(t)
    line_of = {}
    for (x, y) in cells:
        line_of[(x, y)] = ('p', x - y), ('m', x + y)
    cidx = {c: i for i, c in enumerate(cells)}
    res = (cells, Xtriples, cell_triples, line_of, cidx)
    _PRECOMP[m] = res
    return res


class Search:
    def __init__(self, m, biased, lam=LAMBDA):
        self.m = m
        self.biased = biased
        self.lam = lam
        (self.cells, self.Xtriples, self.cell_triples,
         self.line_of, self.cidx) = precompute(m)
        self.grid = [[0] * m for _ in range(m)]
        self.line_count = defaultdict(int)
        self.bad_X = 0
        self.bad_S = 0
        self.pen = 0.0
        self.order = list(range(m))

    def init_config(self, cols):
        self.cols = list(cols)
        self.grid = [[0] * self.m for _ in range(self.m)]
        self.line_count = defaultdict(int)
        self.bad_X = 0
        self.bad_S = 0
        self.pen = 0.0
        for i in range(self.m):
            x, y = i, self.cols[i]
            self.grid[x][y] = 1
            for key in self.line_of[(x, y)]:
                self.line_count[key] += 1
        self._recompute_X()
        self._recompute_S()
        self._recompute_pen()

    def _recompute_X(self):
        self.bad_X = sum(1 for t in self.Xtriples
                         if self.grid[t[0][0]][t[0][1]] and self.grid[t[1][0]][t[1][1]]
                         and self.grid[t[2][0]][t[2][1]])

    def _recompute_S(self):
        self.bad_S = sum(1 for c in self.line_count.values() if c >= 3)

    def _recompute_pen(self):
        self.pen = 0.0
        if self.biased:
            for i in range(self.m):
                x, y = i, self.cols[i]
                self.pen += max(0.0, 1.0 - prior_ratio(x, y, self.m))

    def valid(self):
        return self.bad_X == 0 and self.bad_S == 0

    def objective(self):
        return self.bad_X + self.bad_S + (self.lam * self.pen if self.biased else 0.0)

    def propose(self, i, j):
        oi, oj = self.cols[i], self.cols[j]
        R = [(i, oi), (j, oj)]
        A = [(i, oj), (j, oi)]
        cand = set()
        for c in R + A:
            cand.update(self.cell_triples[c])
        oldX = 0
        for t in cand:
            if (self.grid[t[0][0]][t[0][1]] + self.grid[t[1][0]][t[1][1]]
                    + self.grid[t[2][0]][t[2][1]]) == 3:
                oldX += 1
        for (x, y) in R:
            self.grid[x][y] = 0
            for key in self.line_of[(x, y)]:
                self.line_count[key] -= 1
        for (x, y) in A:
            self.grid[x][y] = 1
            for key in self.line_of[(x, y)]:
                self.line_count[key] += 1
        newX = 0
        for t in cand:
            if (self.grid[t[0][0]][t[0][1]] + self.grid[t[1][0]][t[1][1]]
                    + self.grid[t[2][0]][t[2][1]]) == 3:
                newX += 1
        dX = newX - oldX
        oldS = self.bad_S
        self.bad_S = sum(1 for c in self.line_count.values() if c >= 3)
        dS = self.bad_S - oldS
        dpen = 0.0
        if self.biased:
            for (x, y) in R:
                dpen -= max(0.0, 1.0 - prior_ratio(x, y, self.m))
            for (x, y) in A:
                dpen += max(0.0, 1.0 - prior_ratio(x, y, self.m))
        self.cols[i], self.cols[j] = oj, oi
        self.bad_X += dX
        self.pen += dpen
        self._last = (i, j, oi, oj, dX, dS, oldS, dpen)
        return dX + dS + (self.lam * dpen if self.biased else 0.0)

    def revert(self):
        i, j, oi, oj, dX, dS, oldS, dpen = self._last
        A = [(i, oj), (j, oi)]
        R = [(i, oi), (j, oj)]
        for (x, y) in A:
            self.grid[x][y] = 0
            for key in self.line_of[(x, y)]:
                self.line_count[key] -= 1
        for (x, y) in R:
            self.grid[x][y] = 1
            for key in self.line_of[(x, y)]:
                self.line_count[key] += 1
        self.cols[i], self.cols[j] = oi, oj
        self.bad_X -= dX
        self.bad_S = oldS
        self.pen -= dpen

    def run(self, moves, T0, Tend):
        best_cols = list(self.cols)
        best_obj = self.objective()
        best_bad = self.bad_X + self.bad_S
        cur = best_obj
        found = False
        first_step = None
        for step in range(moves):
            T = T0 * (Tend / T0) ** (step / moves)
            i, j = random.sample(self.order, 2)
            d = self.propose(i, j)
            if d <= 0 or random.random() < math.exp(-d / max(T, 1e-9)):
                cur += d
                if self.bad_X + self.bad_S < best_bad:
                    best_bad = self.bad_X + self.bad_S
                    best_cols = list(self.cols)
                if cur < best_obj:
                    best_obj = cur
                if self.valid():
                    found = True
                    first_step = step
                    break
            else:
                self.revert()
                cur = self.objective()
        return found, best_obj, best_bad, best_cols, first_step


def attack(m, biased, restarts, moves, seed=1, logf=None):
    random.seed(seed)
    solves = 0
    bests = []
    steps_to_sol = []
    best_config = None
    best_bad = None
    for r in range(restarts):
        s = Search(m, biased)
        cols = list(range(m))
        random.shuffle(cols)
        s.init_config(cols)
        found, best_obj, best_bad_r, best_cols, first_step = s.run(moves, T0=2.0, Tend=0.01)
        bests.append(best_obj)
        if found:
            solves += 1
            steps_to_sol.append(first_step)
        if best_bad is None or best_bad_r < best_bad:
            best_bad = best_bad_r
            best_config = best_cols
        if logf is not None:
            logf.write(f"  [{TS()}] m={m} {'biased ' if biased else 'unbiased'} "
                       f"r{r+1}: found={found} best_bad={best_bad_r} "
                       f"first_step={first_step}\n")
            logf.flush()
    rep = {'m': m, 'biased': biased, 'restarts': restarts, 'moves': moves,
           'solves': solves, 'solve_rate': solves / restarts,
           'best_bad_hist': bests, 'min_best': min(bests),
           'steps_to_sol': steps_to_sol}
    if best_config is not None:
        rep['best_config'] = best_config
    return rep


def main():
    report = {}
    with open(PROG, 'w') as logf:
        logf.write(f"[{TS()}] start biased_nibble\n")
        # Validate lever on m=36 (known solvable)
        logf.write(f"[{TS()}] === m=36 validation (known solvable) ===\n"); logf.flush()
        rep_un = attack(36, False, restarts=4, moves=15000, seed=1, logf=logf)
        rep_bi = attack(36, True, restarts=4, moves=15000, seed=2, logf=logf)
        report['m36_unbiased'] = rep_un
        report['m36_biased'] = rep_bi
        # Attack m=37 (OPEN) -- both unbiased and biased for a clean lever comparison
        logf.write(f"[{TS()}] === m=37 attack (OPEN) ===\n"); logf.flush()
        rep37u = attack(37, False, restarts=4, moves=25000, seed=3, logf=logf)
        rep37b = attack(37, True, restarts=4, moves=12000, seed=4, logf=logf)
        report['m37_unbiased'] = rep37u
        report['m37_biased'] = rep37b
        with open(OUT, 'w') as f:
            json.dump(report, f, indent=2)
        logf.write(f"[{TS()}] saved {OUT}\n")
        # Lever verdict
        su, sb = rep_un['solve_rate'], rep_bi['solve_rate']
        mu = (rep_un['steps_to_sol'][0] if rep_un['steps_to_sol'] else None)
        mb = (rep_bi['steps_to_sol'][0] if rep_bi['steps_to_sol'] else None)
        lever = ("BIASED helps" if (sb >= su and (mb is not None)
                                    and (mu is None or mb <= mu))
                 else "no clear lever / neutral")
        logf.write(f"[{TS()}] Lever verdict (m=36): {lever} "
                   f"(unbiased rate={su:.2f} steps={mu}, biased rate={sb:.2f} steps={mb})\n")
        logf.write(f"[{TS()}] m=37: unbiased rate={rep37u['solve_rate']:.2f} "
                   f"biased rate={rep37b['solve_rate']:.2f} "
                   f"biased min_best_bad={rep37b['min_best']:.3f}\n")
        logf.flush()
    print(f"Lever verdict (m=36): {lever}")
    print(f"m=37: unbiased_rate={rep37u['solve_rate']:.2f} biased_rate={rep37b['solve_rate']:.2f}")


if __name__ == '__main__':
    main()
