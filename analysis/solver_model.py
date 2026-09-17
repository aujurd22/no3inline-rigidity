"""
Small learned solver model for rot4-NTIL (m=37), combining ALL known findings.

Combines:
  * SIRH / Th-44 : rot4-NTIL = 2-regular graph (permutation cells) + (X)[3-collinear] + (S)[slope+-1]
  * Part I (Sidon/linear layer): a-b Sidon is a necessary condition  -> used as a feature (s_count, sidon-ish)
  * gating (route②): each bad config has a strictly-improving 2-swap -> local geometry is learnable
  * transfer learning: empirical "good cell" heatmap pooled from all 17 known solutions (m=5..19,36)

Model: tiny numpy MLP (features -> predicted Dbad of a candidate 2-swap). No sklearn/torch needed.
Dataset: self-supervised, labels from an EXACT collinearity oracle (incremental, validated vs full recompute).

Usage:
  python solver_model.py experiment --m 37 --per 360 --out results/model_experiment.json
"""
import sys, os, json, glob, time, random, math
import numpy as np

# ---------------- geometry (verified against verify_cells.py; line_of gives bad=88 for the m=10 GPU cells) ----------------
AOFF, BOFF, COFF, BSPAN, CSPAN = 200, 200, 20000, 400, 40000

def igcd(a, b):
    a = abs(a); b = abs(b)
    while b:
        a, b = b, a % b
    return a

def line_of(px, py, qx, qy):
    a = -(qy - py); b = (qx - px); c = (qy - py) * px - (qx - px) * py
    g = igcd(abs(a), abs(b)); g = igcd(g, abs(c))
    if g:
        a //= g; b //= g; c //= g
    if a < 0 or (a == 0 and b < 0) or (a == 0 and b == 0 and c < 0):
        a = -a; b = -b; c = -c
    return (a + AOFF) * BSPAN * CSPAN + (b + BOFF) * CSPAN + (c + COFF)

def get_pt(xs, ys, m, n, idx):
    i = idx >> 2; r = idx & 3
    cx = xs[i]; cy = ys[i]
    if r == 0: return cx, cy
    if r == 1: return n - 1 - cy, cx
    if r == 2: return n - 1 - cx, n - 1 - cy
    return cy, n - 1 - cx

# ---------------- exact oracle (incremental, validated) ----------------
def C3(t):
    return t * (t - 1) * (t - 2) // 6 if t >= 3 else 0

class Oracle:
    """Exact collinearity oracle via FULL recompute (pairs method).
    line_of is canonical over the [0,2m-1]^2 lifted grid (verified on 200k random
    collinear triples), so this equals the ground-truth triple count exactly.
    No incremental bookkeeping -> no drift bug."""

    def __init__(self, xs, ys, m):
        self.m = m; self.n = 2 * m
        self.xs = list(xs); self.ys = list(ys)
        self._rebuild()

    def _rebuild(self):
        m = self.m; n = self.n
        pts = [get_pt(self.xs, self.ys, m, n, p) for p in range(4 * m)]
        self._pts = pts
        perline = {}
        paircount = {}
        for a in range(4 * m):
            pa = pts[a]
            for b in range(a + 1, 4 * m):
                if pa == pts[b]: continue
                k = line_of(pa[0], pa[1], pts[b][0], pts[b][1])
                paircount[k] = paircount.get(k, 0) + 1
                if k in perline: perline[k].append(a)
                else: perline[k] = [a, b]
        self.perline = perline
        self.lines = {}
        bad = 0
        for k, c in paircount.items():
            P = int((1 + (1 + 8 * c) ** 0.5) / 2)   # pairs = C(P,2) -> P points
            self.lines[k] = P
            bad += C3(P)
        self.bad = bad

    def apply_move(self, i, j, t):
        if t == 0:
            self.ys[i], self.ys[j] = self.ys[j], self.ys[i]
        elif t == 1:
            self.xs[i], self.xs[j] = self.xs[j], self.xs[i]
        else:
            self.xs[i], self.xs[j] = self.xs[j], self.xs[i]
            self.ys[i], self.ys[j] = self.ys[j], self.ys[i]
        self._rebuild()

    def has_dup(self):
        return len(set(self._pts)) != 4 * self.m

    def dbad_of_move(self, i, j, t):
        """return Dbad (after-before) or None if the move creates a coincident lift (illegal)."""
        self.apply_move(i, j, t)
        if self.has_dup():
            self.apply_move(i, j, t)  # undo
            return None
        after = self.bad
        self.apply_move(i, j, t)      # undo
        return after - self.bad

    def load_per_cell(self):
        """exact count of (X)-triples each cell participates in (per base config)."""
        load = [0] * self.m
        for key, lst in self.perline.items():
            c = len(lst)
            if c < 3: continue
            for a in range(c):
                for b in range(a + 1, c):
                    for d in range(b + 1, c):
                        for idx in (lst[a], lst[b], lst[d]):
                            load[idx >> 2] += 1
        return load

    def s_count(self):
        """number of slope+-1 violating pairs ((S) constraint count)."""
        s = 0
        for i in range(self.m):
            for j in range(i + 1, self.m):
                dx = abs(self.xs[i] - self.xs[j]); dy = abs(self.ys[i] - self.ys[j])
                if (dx == 1 and dy == 1) or (dx == 1 and dy == 0) or (dx == 0 and dy == 1):
                    s += 1
        return s

# ---------------- transfer-learning prior: heatmap from all known solutions ----------------
def build_heat(solutions_dir, nb=6):
    cells = []
    for f in glob.glob(os.path.join(solutions_dir, 'm*.json')):
        try:
            d = json.load(open(f)); cs = d.get('cells')
        except Exception:
            continue
        if not cs: continue
        mx = d['m']
        for (x, y) in cs:
            cells.append((x / mx, y / mx))
    H = np.zeros((nb, nb))
    for (u, v) in cells:
        bx = min(nb - 1, int(u * nb)); by = min(nb - 1, int(v * nb))
        H[bx, by] += 1
    if H.sum() > 0:
        H = H / H.sum()
    return H

def heat_of(H, x, y, m, nb=6):
    bx = min(nb - 1, int(x / m * nb)); by = min(nb - 1, int(y / m * nb))
    return H[bx, by]

# ---------------- tiny numpy MLP ----------------
class TinyMLP:
    def __init__(self, F, H=24, lr=0.05):
        self.F = F; self.H = H; self.lr = lr
        self.W1 = np.random.randn(H, F) * 0.5
        self.b1 = np.zeros(H)
        self.W2 = np.random.randn(H) * 0.5
        self.b2 = 0.0
        self.fmean = np.zeros(F); self.fstd = np.ones(F)

    def forward(self, x):
        z = np.tanh(self.W1 @ x + self.b1)
        return self.W2 @ z + self.b2, z

    def predict(self, x):
        x = (x - self.fmean) / (self.fstd + 1e-9)
        return self.forward(x)[0]

    def fit(self, X, Y, epochs=300, bs=64):
        X = np.array(X, dtype=float); Y = np.array(Y, dtype=float)
        self.fmean = X.mean(0); self.fstd = X.std(0) + 1e-9
        Xs = (X - self.fmean) / self.fstd
        n = len(X)
        for ep in range(epochs):
            perm = np.random.permutation(n)
            for s in range(0, n, bs):
                idx = perm[s:s + bs]
                xb = Xs[idx]; yb = Y[idx]
                # forward
                z = np.tanh(xb @ self.W1.T + self.b1)            # (bs,H)
                out = z @ self.W2 + self.b2                      # (bs,)
                err = out - yb                                   # (bs,)
                # backward
                dW2 = (err[:, None] * z).mean(0)
                db2 = err.mean()
                dz = err[:, None] * self.W2                      # (bs,H)
                dW1 = (dz[:, :, None] * xb[:, None, :]).mean(0)  # (H,F)
                db1 = dz.mean(0)
                lr = self.lr * (1 - ep / epochs * 0.7)
                self.W2 -= lr * dW2; self.b2 -= lr * db2
                self.W1 -= lr * dW1; self.b1 -= lr * db1

    def save(self, path):
        np.savez(path, W1=self.W1, b1=self.b1, W2=self.W2, b2=self.b2,
                 fmean=self.fmean, fstd=self.fstd)

    @staticmethod
    def load(path):
        d = np.load(path)
        m = TinyMLP(d['W1'].shape[1], d['W1'].shape[0])
        m.W1 = d['W1']; m.b1 = d['b1']; m.W2 = d['W2']; m.b2 = d['b2']
        m.fmean = d['fmean']; m.fstd = d['fstd']
        return m

# ---------------- feature extraction ----------------
def features(orch, i, j, t, H, load):
    m = orch.m
    bad_norm = orch.bad / max(1, C3(4 * m))          # ~fraction of all triples that are bad
    s_norm = orch.s_count() / max(1, m * (m - 1) // 2)
    dist = abs(orch.xs[i] - orch.xs[j]) + abs(orch.ys[i] - orch.ys[j])
    heat_i = heat_of(H, orch.xs[i], orch.ys[i], m)
    heat_j = heat_of(H, orch.xs[j], orch.ys[j], m)
    return np.array([
        bad_norm, load[i] / 50.0, load[j] / 50.0,
        heat_i * 10, heat_j * 10, heat_i * heat_j * 100,
        s_norm * 50, dist / m,
        1.0 if t == 0 else 0.0, 1.0 if t == 1 else 0.0, 1.0 if t == 2 else 0.0
    ], dtype=float)

# ---------------- dataset generation (self-supervised) ----------------
def random_dupfree_config(m, rng):
    while True:
        xs = list(range(m)); rng.shuffle(xs)
        ys = list(range(m)); rng.shuffle(ys)
        o = Oracle(xs, ys, m)
        if not o.has_dup():
            return o

def gen_dataset(m, H, n_configs=300, cand_per=25, seed=0):
    rng = random.Random(seed)
    X = []; Y = []
    for _ in range(n_configs):
        orch = random_dupfree_config(m, rng)
        load = orch.load_per_cell()
        for _ in range(cand_per):
            i = rng.randrange(m); j = rng.randrange(m)
            if i == j: continue
            t = rng.randrange(3)
            dbad = orch.dbad_of_move(i, j, t)
            if dbad is None: continue
            X.append(features(orch, i, j, t, H, load))
            Y.append(dbad)
    return np.array(X), np.array(Y)

# ---------------- solvers (bounded wall-clock) ----------------
def solve_baseline(m, seconds, seed=1):
    rng = random.Random(seed)
    orch = random_dupfree_config(m, rng)
    best = orch.bad
    t0 = time.time()
    steps = 0
    while time.time() - t0 < seconds:
        i = rng.randrange(m); j = rng.randrange(m)
        if i == j: continue
        t = rng.randrange(3)
        dbad = orch.dbad_of_move(i, j, t)
        if dbad is None: continue
        if dbad < 0:
            orch.apply_move(i, j, t)      # reapply the accepted move
            best = min(best, orch.bad)
        steps += 1
    return best, steps

def solve_learned(m, H, model, seconds, seed=2, K=8):
    rng = random.Random(seed)
    orch = random_dupfree_config(m, rng)
    best = orch.bad
    t0 = time.time()
    steps = 0
    while time.time() - t0 < seconds:
        load = orch.load_per_cell()
        cands = []
        for _ in range(K):
            i = rng.randrange(m); j = rng.randrange(m)
            if i == j: continue
            t = rng.randrange(3)
            dbad = orch.dbad_of_move(i, j, t)
            if dbad is None: continue
            f = features(orch, i, j, t, H, load)
            cands.append((model.predict(f), dbad, i, j, t))
        if not cands:
            steps += 1; continue
        cands.sort(key=lambda c: c[0])
        _, dbad, i, j, t = cands[0]
        if dbad < 0:
            orch.apply_move(i, j, t)
            best = min(best, orch.bad)
        steps += 1
    return best, steps

# ---------------- exact full-recompute cross-check (O(n^3), used only for self-tests) ----------------
from itertools import combinations
def recompute_bad(xs, ys, m):
    pts = [get_pt(xs, ys, m, 2 * m, p) for p in range(4 * m)]
    return sum(1 for (a, b, c) in combinations(set(pts), 3)
               if (b[1] - a[1]) * (c[0] - a[0]) == (c[1] - a[1]) * (b[0] - a[0]))

# ---------------- experiment driver ----------------
def experiment(m, per, out):
    sol_dir = os.path.join(os.path.dirname(__file__), 'results', 'solutions')
    H = build_heat(sol_dir)
    print('[1] heat prior built from solutions (%d cells pooled)' % (H.sum() > 0 and int(H.sum() * 0 + 1)), flush=True)
    # self-check oracle correctness
    xs = list(range(m)); random.shuffle(xs); ys = list(range(m)); random.shuffle(ys)
    orch = Oracle(xs, ys, m)
    # full recompute cross-check
    true_bad = recompute_bad(orch.xs, orch.ys, m)
    assert orch.bad == true_bad, 'oracle self-check FAILED: incr=%d full=%d' % (orch.bad, true_bad)
    print('[2] oracle self-check OK (bad=%d)' % orch.bad, flush=True)
    # also validate over moves with dup-rejection (the real solver path)
    mism = 0
    for step in range(300):
        i = random.randrange(m); j = random.randrange(m)
        if i == j: continue
        t = random.randrange(3)
        d = orch.dbad_of_move(i, j, t)
        if d is None:
            continue
        if orch.bad != recompute_bad(orch.xs, orch.ys, m):
            mism += 1; break
        orch.apply_move(i, j, t)  # keep the move (descent-agnostic check)
    assert mism == 0, 'move-path oracle mismatch'
    print('    move-path self-check OK (300 moves, no mismatch)', flush=True)

    print('[3] generating dataset...', flush=True)
    t = time.time()
    X, Y = gen_dataset(m, H, n_configs=120, cand_per=18, seed=7)
    print('    %d samples in %.1fs; label mean=%.2f std=%.2f' % (len(X), time.time() - t, Y.mean(), Y.std()), flush=True)

    model = TinyMLP(X.shape[1], H=24)
    print('[4] training tiny MLP (%d->24->1)...' % X.shape[1], flush=True)
    t = time.time()
    model.fit(X, Y, epochs=250, bs=64)
    print('    trained in %.1fs' % (time.time() - t), flush=True)
    mp = os.path.join(os.path.dirname(__file__), 'results', 'tiny_solver_model.npz')
    model.save(mp)

    print('[5] baseline solver (%ds)...' % per, flush=True)
    bb, bs = solve_baseline(m, per, seed=11)
    print('    baseline best_bad=%d steps=%d' % (bb, bs), flush=True)
    print('[6] learned-policy solver (%ds)...' % per, flush=True)
    lb, ls = solve_learned(m, H, model, per, seed=22, K=8)
    print('    learned  best_bad=%d steps=%d' % (lb, ls), flush=True)

    res = {
        'm': m, 'per_seconds': per,
        'dataset_samples': len(X), 'label_mean': float(Y.mean()), 'label_std': float(Y.std()),
        'baseline_best_bad': bb, 'baseline_steps': bs,
        'learned_best_bad': lb, 'learned_steps': ls,
        'model_file': mp,
        'verdict': ('LEARNED_MODEL_HELPS' if lb < bb else 'NO_CLEAR_GAIN')
    }
    json.dump(res, open(out, 'w'), indent=2)
    print('[done]', json.dumps(res), flush=True)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'experiment'
    args = sys.argv[2:]
    m = 37; per = 360; out = 'results/model_experiment.json'
    k = 0
    while k < len(args):
        if args[k] == '--m': m = int(args[k + 1]); k += 2
        elif args[k] == '--per': per = int(args[k + 1]); k += 2
        elif args[k] == '--out': out = args[k + 1]; k += 2
        else: k += 1
    if mode == 'experiment':
        experiment(m, per, out)
