"""
Part B -- Manifold learning on the NTIL solution space.

Tests the user's hypothesis: "low-D unordered configurations may be
projections of higher-D ordered structures."

Three complementary probes:
  (P1) Is the *collection* of solutions a thin manifold?
       -> PCA intrinsic dim (k90), participation ratio, vs random null.
  (P2) Is each *individual* solution a low-D halfspace cut
       (cut-and-project of a higher-D ordered lattice)?
       -> per-solution linear-separability in algebraic/polar feature space.
  (P3) Visual manifold: 2D t-SNE embedding coloured by ring-count.

Sound, reproducible. Uses cache iden solutions (Flammenkamp).
"""
import os, sys, json, time
import numpy as np

CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def decode(line, n):
    line = line.strip()
    if len(line) < 1 + 2 * n:
        return None
    body = line[1:1 + 2 * n]
    pts = []
    per = len(body) // n
    for y in range(n):
        for j in range(per):
            ch = body[y * per + j]
            if ch not in ALPHABET:
                return None
            pts.append((ALPHABET.index(ch), y))
    return pts

def load_iden(n, cap=None):
    path = os.path.join(CACHE, f'n{n}_iden')
    if not os.path.exists(path):
        return np.zeros((0, n * n))
    sols = []
    with open(path) as f:
        for line in f:
            pts = decode(line, n)
            if pts is None:
                continue
            v = np.zeros(n * n, dtype=np.float32)
            for (x, y) in pts:
                v[y * n + x] = 1.0
            sols.append(v)
            if cap and len(sols) >= cap:
                break
    return np.array(sols, dtype=np.float32)

def random_configs(n, N, seed=0):
    rng = np.random.default_rng(seed)
    sols = np.zeros((N, n * n), dtype=np.float32)
    cols = np.arange(n)
    for i in range(N):
        for y in range(n):
            c = rng.choice(cols, size=2, replace=False)
            sols[i, y * n + c[0]] = 1.0
            sols[i, y * n + c[1]] = 1.0
    return sols

# ---------- P1: manifold dim ----------
def pca_metrics(X):
    Xc = X - X.mean(0)
    C = (Xc.T @ Xc) / len(Xc)
    ev = np.linalg.eigvalsh(C)
    ev = np.clip(np.sort(ev)[::-1], 0, None)
    tot = ev.sum()
    if tot <= 0:
        return ev, X.shape[1], X.shape[1]
    cum = np.cumsum(ev) / tot
    k90 = int(np.searchsorted(cum, 0.90) + 1)
    pr = tot * tot / (ev * ev).sum()
    return ev, k90, pr

def two_nn_id(X, sample=3000, seed=1):
    from sklearn.neighbors import NearestNeighbors
    if sample and len(X) > sample:
        idx = np.random.default_rng(seed).choice(len(X), sample, replace=False)
        X = X[idx]
    nn = NearestNeighbors(n_neighbors=3).fit(X)
    d, _ = nn.kneighbors(X)
    r1 = d[:, 1]; r2 = d[:, 2]
    rat = np.log(r2 / r1)
    rat = rat[np.isfinite(rat)]
    return 1.0 / np.mean(rat)

def levina_bickel(X, k=20, sample=3000, seed=2):
    from sklearn.neighbors import NearestNeighbors
    if sample and len(X) > sample:
        idx = np.random.default_rng(seed).choice(len(X), sample, replace=False)
        X = X[idx]
    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)
    d, _ = nn.kneighbors(X)
    d = d[:, 1:]
    T = d[:, -1:]
    ln = np.log(T / d)
    est = -1.0 / ln.mean(0)  # per k
    return float(np.mean(est))

# ---------- P2: per-solution halfspace fit ----------
def feature_matrix(n, kind='monomial', deg=3):
    xs = np.arange(n)
    GX = np.tile(xs, n).astype(np.float64)    # cell k -> x = k % n
    GY = np.repeat(xs, n).astype(np.float64) # cell k -> y = k // n
    if kind == 'monomial':
        feats = [np.ones_like(GX)]
        for a in range(deg + 1):
            for b in range(deg + 1 - a):
                feats.append(GX ** a * GY ** b)
    else:  # polar
        cx = (n - 1) / 2.0; cy = (n - 1) / 2.0
        dx = 2 * (GX - cx); dy = 2 * (GY - cy)
        r2 = dx * dx + dy * dy; th = np.arctan2(dy, dx)
        feats = [np.ones_like(r2), r2, r2 * r2, r2 * r2 * r2,
                 np.cos(th), np.sin(th), np.cos(2 * th), np.sin(2 * th),
                 np.cos(3 * th), np.sin(3 * th)]
    return np.stack(feats, axis=1)

def fit_accuracy(F, L):
    w, *_ = np.linalg.lstsq(F, L, rcond=None)
    proj = F @ w
    order = np.argsort(proj)
    po = proj[order]; lo = L[order].astype(np.float64)
    n1 = np.cumsum(lo); n0 = np.cumsum(1 - lo)
    acc = (n1 + (n0[-1] - n0)) / len(L)
    return float(acc.max())

def per_solution_fit(n, sols, feats_specs):
    res = {}
    for name, kind, deg in feats_specs:
        F = feature_matrix(n, kind=kind, deg=deg)
        accs = [fit_accuracy(F, L) for L in sols]
        res[name] = float(np.mean(accs))
    return res

# ---------- P3: embedding ----------
def ring_count(vec, n):
    cx = (n - 1) / 2.0; cy = (n - 1) / 2.0
    occ = np.where(vec > 0.5)[0]
    r = set()
    for idx in occ:
        x = idx % n; y = idx // n
        dx = 2 * (x - cx); dy = 2 * (y - cy)
        r.add(round(dx * dx + dy * dy))
    return len(r)

def main():
    from sklearn.manifold import TSNE
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    figdir = os.path.join(os.path.dirname(__file__), 'figs')
    os.makedirs(figdir, exist_ok=True)
    out = []
    w = out.append
    w("=" * 78)
    w("PART B -- MANIFOLD LEARNING ON NTIL SOLUTION SPACE")
    w("=" * 78)
    NS = [10, 12, 14, 16, 18]
    feats_specs = [('mono_d1', 'monomial', 1), ('mono_d2', 'monomial', 2),
                   ('mono_d3', 'monomial', 3), ('mono_d4', 'monomial', 4),
                   ('mono_d5', 'monomial', 5), ('mono_d6', 'monomial', 6),
                   ('polar', 'polar', 0)]
    idrows = []
    fitrows = []
    for n in NS:
        w(f"\n{'#' * 70}\n# n={n}  (D=n^2={n * n})\n{'#' * 70}")
        cap = 4000 if n >= 18 else None
        sols = load_iden(n, cap=cap)
        if len(sols) == 0:
            w("  no iden solutions cached; skip")
            continue
        w(f"  loaded {len(sols)} iden solutions (cap={cap})")
        # P1
        ev, k90, pr = pca_metrics(sols)
        rnd = random_configs(n, min(2000, len(sols)), seed=n)
        evr, k90r, prr = pca_metrics(rnd)
        tnn = two_nn_id(sols, sample=min(3000, len(sols)))
        tnnr = two_nn_id(rnd, sample=min(3000, len(rnd)))
        lb = levina_bickel(sols, sample=min(3000, len(sols)))
        lbr = levina_bickel(rnd, sample=min(3000, len(rnd)))
        w(f"  [P1 manifold]  PCA k90={k90} (={k90 / n:.2f}*n)  "
          f"partic.ratio={pr:.1f}  two-NN={tnn:.2f}  Levina-Bickel={lb:.2f}")
        w(f"  [P1 random  ]  PCA k90={k90r} (={k90r / n:.2f}*n) "
          f"partic.ratio={prr:.1f}  two-NN={tnnr:.2f}  Levina-Bickel={lbr:.2f}")
        w(f"  [P1 thinness]  k90/D={k90 / (n * n):.4f}  "
          f"random k90/D={k90r / (n * n):.4f}  "
          f"ratio real/random={k90 / max(k90r,1):.3f}")
        idrows.append((int(n), int(k90), float(round(pr, 1)), float(round(tnn, 2)),
                       (float(round(lb, 2)) if np.isfinite(lb) else None),
                       int(k90r), float(round(prr, 1)), float(round(tnnr, 2)),
                       (float(round(lbr, 2)) if np.isfinite(lbr) else None)))
        # P2
        samp = sols[:min(800, len(sols))]
        fr = per_solution_fit(n, samp, feats_specs)
        sampr = rnd[:min(800, len(rnd))]
        frr = per_solution_fit(n, sampr, feats_specs)
        w("  [P2 per-solution halfspace accuracy (best threshold)]")
        for name, _, _ in feats_specs:
            w(f"      {name:10s}: real {fr[name] * 100:5.1f}%   "
              f"random {frr[name] * 100:5.1f}%")
        fitrows.append((n, fr, frr))
        # PC loadings PNG (n=14)
        if n == 14:
            Xc = sols - sols.mean(0)
            C = (Xc.T @ Xc) / len(Xc)
            evv, V = np.linalg.eigh(C)
            order = np.argsort(evv)[::-1]
            for pc in range(3):
                v = V[:, order[pc]].reshape(n, n)
                plt.figure(figsize=(4, 4))
                plt.imshow(v, cmap='RdBu_r', interpolation='nearest')
                plt.title(f'n=14 PC{pc + 1} loading')
                plt.colorbar(shrink=0.8)
                plt.savefig(os.path.join(figdir, f'pc{n}_p{pc + 1}.png'), dpi=90)
                plt.close()
    # P3 embedding n=14
    w("\n" + "=" * 78)
    w("P3 -- 2D t-SNE embedding (n=14, coloured by ring-count)")
    w("=" * 78)
    n = 14
    sols = load_iden(n)
    if len(sols) > 0:
        rc = np.array([ring_count(s, n) for s in sols])
        t0 = time.time()
        emb = TSNE(n_components=2, init='pca', perplexity=30,
                   method='barnes_hut', random_state=0).fit_transform(sols)
        w(f"  t-SNE done in {time.time() - t0:.1f}s on {len(sols)} pts")
        plt.figure(figsize=(6, 6))
        sc = plt.scatter(emb[:, 0], emb[:, 1], c=rc, cmap='viridis', s=6)
        plt.colorbar(sc, label='# distinct distance rings')
        plt.title('n=14 solution manifold (t-SNE, colour = ring count)')
        plt.savefig(os.path.join(figdir, 'tsne_n14.png'), dpi=110)
        plt.close()
        w("  saved figs/tsne_n14.png")
    report = "\n".join(out)
    print(report)
    with open(os.path.join(os.path.dirname(__file__), 'highdim_manifold.txt'), 'w') as f:
        f.write(report + "\n")
    with open(os.path.join(os.path.dirname(__file__), 'highdim_manifold.json'), 'w') as f:
        json.dump({'idrows': idrows,
                   'fitrows': [(n, {k: v for k, v in fr.items()},
                                {k: v for k, v in frr.items()})
                               for n, fr, frr in fitrows]}, f, indent=1)

if __name__ == '__main__':
    main()
