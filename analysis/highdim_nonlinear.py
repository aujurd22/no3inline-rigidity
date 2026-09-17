"""
Fairness follow-up to the "shared-source / hidden-structure" idea.
Linear tests (highdim_angles.py) found NO organization by ring-count.
That does not settle it: the hidden variable may be different, and the
structure may be NON-LINEAR.

This script:
  - uses a SECOND geometric label: slope-diversity = number of distinct
    reduced slopes among all C(2n,2) point pairs (a real NTIL complexity
    measure, sensitive to global arrangement, not just ring usage).
  - runs a NON-LINEAR t-SNE embedding of the SVD latent scores and checks
    whether ring-count OR slope-diversity organizes the cloud (silhouette).
"""
import os, time
import numpy as np

CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def decode(line, n):
    line = line.strip()
    if len(line) < 1 + 2 * n: return None
    body = line[1:1 + 2 * n]; pts = []; per = len(body) // n
    for y in range(n):
        for j in range(per):
            ch = body[y * per + j]
            if ch not in ALPHABET: return None
            pts.append((ALPHABET.index(ch), y))
    return pts

def load_iden(n, cap=None):
    path = os.path.join(CACHE, f'n{n}_iden')
    sols = []
    if not os.path.exists(path): return np.zeros((0, n * n))
    with open(path) as f:
        for line in f:
            pts = decode(line, n)
            if pts is None: continue
            v = np.zeros(n * n, dtype=np.float32)
            for (x, y) in pts: v[y * n + x] = 1.0
            sols.append(v)
            if cap and len(sols) >= cap: break
    return np.array(sols, dtype=np.float32)

def ring_count(vec, n):
    cx = (n - 1) / 2.0; cy = (n - 1) / 2.0
    occ = np.where(vec > 0.5)[0]; r = set()
    for idx in occ:
        x = idx % n; y = idx // n
        dx = 2 * (x - cx); dy = 2 * (y - cy)
        r.add(round(dx * dx + dy * dy))
    return len(r)

def slope_diversity(pts, n):
    # pts: list of (x,y). distinct reduced slopes among all pairs.
    from math import gcd
    s = set()
    m = len(pts)
    for a in range(m):
        x1, y1 = pts[a]
        for b in range(a + 1, m):
            x2, y2 = pts[b]
            dx = x2 - x1; dy = y2 - y1
            if dx == 0 and dy == 0: continue
            g = gcd(dx, dy) or 1
            s.add((dx // g, dy // g))
    return len(s)

def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE
    from sklearn.metrics import silhouette_score

    n = 16
    sols = load_iden(n)                 # 5683
    K = len(sols)
    Mc = sols - sols.mean(0)
    U, S, Vt = np.linalg.svd(Mc, full_matrices=False)
    V = Vt.T
    scores = Mc @ V                     # K x r
    # labels
    pts_list = []
    rings = np.zeros(K, int); slopes = np.zeros(K, int)
    for i in range(K):
        occ = np.where(sols[i] > 0.5)[0]
        plist = [(int(idx % n), int(idx // n)) for idx in occ]
        pts_list.append(plist)
        rings[i] = ring_count(sols[i], n)
        slopes[i] = slope_diversity(plist, n)
    rb = np.digitize(rings, np.quantile(rings, [.25, .5, .75]))
    sb = np.digitize(slopes, np.quantile(slopes, [.25, .5, .75]))
    # linear silhouette (SVD top2) for both labels
    sil_lin_ring = silhouette_score(scores[:2000, :2], rb[:2000])
    sil_lin_slope = silhouette_score(scores[:2000, :2], sb[:2000])
    corr_pc1_slope = np.corrcoef(scores[:, 0], slopes)[0, 1]
    # NON-LINEAR t-SNE on latent scores (top 60 dims, subsample 2500)
    sub = min(2500, K)
    idx = np.random.default_rng(3).choice(K, sub, replace=False)
    Z = scores[idx, :60]
    t0 = time.time()
    emb = TSNE(n_components=2, init='pca', perplexity=40,
               random_state=1).fit_transform(Z)
    dt = time.time() - t0
    rb_s = rb[idx]; sb_s = sb[idx]
    sil_tsne_ring = silhouette_score(emb, rb_s)
    sil_tsne_slope = silhouette_score(emb, sb_s)
    fig, axs = plt.subplots(1, 2, figsize=(12, 5))
    sc0 = axs[0].scatter(emb[:, 0], emb[:, 1], c=rb_s, cmap='viridis', s=6)
    axs[0].set_title(f'n=16 t-SNE(latent) colour=ring buckets\n'
                     f'silhouette={sil_tsne_ring:.3f}')
    fig.colorbar(sc0, ax=axs[0], label='ring bucket')
    sc1 = axs[1].scatter(emb[:, 0], emb[:, 1], c=sb_s, cmap='plasma', s=6)
    axs[1].set_title(f'n=16 t-SNE(latent) colour=slope-diversity bucket\n'
                     f'silhouette={sil_tsne_slope:.3f}')
    fig.colorbar(sc1, ax=axs[1], label='slope bucket')
    fig.tight_layout()
    figdir = os.path.join(os.path.dirname(__file__), 'figs')
    os.makedirs(figdir, exist_ok=True)
    fig.savefig(os.path.join(figdir, 'tsne_latent_n16_nonlin.png'), dpi=110)
    plt.close(fig)
    out = []
    w = out.append
    w("=" * 78)
    w("PART B++ -- NON-LINEAR / ALT-LABEL FAIRNESS TEST (n=16)")
    w("=" * 78)
    w(f"  K={K} solutions; latent dim r={V.shape[1]}")
    w(f"  [labels] ring-count range {rings.min()}..{rings.max()}  "
      f"slope-diversity range {slopes.min()}..{slopes.max()}")
    w(f"  corr(PC1, slope-diversity) = {corr_pc1_slope:+.3f}")
    w(f"  LINEAR  (SVD top2) silhouette:  ring={sil_lin_ring:.3f}   "
      f"slope={sil_lin_slope:.3f}")
    w(f"  NONLIN  (t-SNE latent) silhouette: ring={sil_tsne_ring:.3f}   "
      f"slope={sil_tsne_slope:.3f}   (t-SNE {dt:.1f}s)")
    w("  -> if ~0 for both labels & both views: the latent cloud is a")
    w("     fairly homogeneous blob with NO obvious hidden stratification")
    w("     (linear or non-linear) by these geometric parameters.")
    w("  saved figs/tsne_latent_n16_nonlin.png")
    report = "\n".join(out)
    print(report)
    with open(os.path.join(os.path.dirname(__file__), 'highdim_nonlinear.txt'), 'w') as f:
        f.write(report + "\n")

if __name__ == '__main__':
    main()
