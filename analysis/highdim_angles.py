"""
USER'S NEW IDEA (Part B extension):
"Can different solutions of the SAME n be high-dimensional projections from
different angles?  Or: take ALL solutions, project them from different angles
and reconstruct -- is there hidden structure?"

Operationalization:
  Stack all K solutions of fixed n into M in {0,1}^{K x n^2} (rows=solutions,
  cols=grid cells).  Truncated SVD  M = U S V^T :
    - V (n^2 x r)  = SHARED spatial basis = the "hidden high-D source directions"
    - scores = M V = U S (K x r) = each solution's COEFFICIENTS in that basis
      = literally its "projection angle / viewpoint" in the shared latent space.
  If only ~1.7n basis vectors reconstruct all solutions, then every solution IS
  a projection (linear combo) of a common low-D source seen from its own angle.

Three probes:
  (A) SVD intrinsic dim k90  -> how few shared directions suffice (cf Part B).
  (B) Latent scatter of scores[:, :2] coloured by #distance-rings: does one
      projection angle *order* solutions by a hidden parameter?  (PC1~ring corr)
  (C) RANDOM-ANGLE SWEEP: many random 2D projections of the solution cloud;
      measure silhouette w.r.t. ring-count buckets; compare to SVD-top-2.
      If some random angles separate better -> structure is viewpoint-dependent
      -> "different angles reveal different hidden things".

Also saves the top-6 shared basis patterns as n x n heatmaps (the hidden source
directions made visible).
"""
import os, json, time
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
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE
    from sklearn.metrics import silhouette_score
    from sklearn.random_projection import GaussianRandomProjection

    figdir = os.path.join(os.path.dirname(__file__), 'figs')
    os.makedirs(figdir, exist_ok=True)
    out = []; w = out.append
    w("=" * 78)
    w("PART B+ -- SAME-n SOLUTIONS AS PROJECTIONS OF A SHARED HIGH-D SOURCE")
    w("=" * 78)
    NS = [14, 16, 18]
    json_out = {}
    for n in NS:
        w(f"\n{'#' * 70}\n# n={n}  (D=n^2={n*n}, K solutions)\n{'#' * 70}")
        cap = 4000 if n >= 18 else None
        sols = load_iden(n, cap=cap)
        K = len(sols)
        if K == 0:
            w("  no iden cache; skip"); continue
        w(f"  loaded {K} solutions")
        D = n * n
        Mc = sols - sols.mean(0)
        t0 = time.time()
        U, S, Vt = np.linalg.svd(Mc, full_matrices=False)
        dt = time.time() - t0
        V = Vt.T                       # D x r  (r = min(K, D))
        scores = Mc @ V                # K x r  (= U * S)
        var = (S * S); cum = np.cumsum(var) / var.sum()
        k90 = int(np.searchsorted(cum, 0.90) + 1)
        w(f"  SVD in {dt:.1f}s  | r=min(K,D)={V.shape[1]}  total var={var.sum():.1f}")
        w(f"  [A] intrinsic dim k90 = {k90}  (= {k90/n:.2f}*n,  k90/D = {k90/D:.4f})")
        w(f"      -> only {k90} shared directions reconstruct 90% of ALL {K} solutions")
        # semantic label: number of distinct distance-rings
        rc = np.array([ring_count(s, n) for s in sols])
        # (B) latent scatter coloured by ring-count
        fig, ax = plt.subplots(figsize=(6, 5))
        sc = ax.scatter(scores[:1200, 0], scores[:1200, 1], c=rc[:1200],
                        cmap='viridis', s=7)
        ax.set_xlabel('latent dim 1 (shared-basis coeff)')
        ax.set_ylabel('latent dim 2 (shared-basis coeff)')
        ax.set_title(f'n={n}: solutions in shared latent space (colour=ring count)')
        fig.colorbar(sc, label='# distance rings')
        fig.savefig(os.path.join(figdir, f'angles_latent_{n}.png'), dpi=110)
        plt.close(fig)
        # correlation PC1 vs ring-count
        corr = np.corrcoef(scores[:, 0], rc)[0, 1]
        w(f"  [B] corr(PC1, ring-count) = {corr:+.3f}  "
          f"(>0.3 => one angle orders solutions by hidden param)")
        # (C) random-angle sweep (silhouette w.r.t. ring buckets)
        buckets = np.digitize(rc, np.quantile(rc, [0.25, 0.5, 0.75]))  # 4 buckets
        # SVD-top-2 baseline
        sil_svd = silhouette_score(scores[:1500, :2], buckets[:1500])
        rng = np.random.default_rng(7)
        nrep = 60
        sils_rand = []
        best = -1; best_seed = -1
        sub = min(1500, K)
        idx = rng.choice(K, sub, replace=False) if K > sub else np.arange(K)
        Mcs = Mc[idx]; bs = buckets[idx]
        for t in range(nrep):
            R = rng.standard_normal((2, D))
            R /= np.linalg.norm(R, axis=1, keepdims=True)
            proj = Mcs @ R.T
            try:
                s = silhouette_score(proj, bs)
            except Exception:
                s = -1
            sils_rand.append(s)
            if s > best:
                best = s; best_seed = t
        sils_rand = np.array(sils_rand)
        w(f"  [C] ring-bucket silhouette:  SVD-top2 = {sil_svd:.3f}   "
          f"random-angle max = {sils_rand.max():.3f} (seed {best_seed})   "
          f"mean = {sils_rand.mean():.3f}")
        w(f"      -> random angles {'EXPOSE' if sils_rand.max() > sil_svd + 0.02 else 'do NOT exceed'} "
          f"the optimal SVD angle (structure is {'viewpoint-dependent' if sils_rand.max() > sil_svd + 0.02 else 'concentrated in top SVD dirs'})")
        # top-6 shared basis patterns (the hidden source directions)
        fig, axs = plt.subplots(2, 3, figsize=(9, 6))
        for k in range(6):
            pat = V[:, k].reshape(n, n)
            axs[k // 3, k % 3].imshow(pat, cmap='RdBu_r', interpolation='nearest')
            axs[k // 3, k % 3].set_title(f'shared basis #{k+1} (σ={S[k]:.1f})')
            axs[k // 3, k % 3].axis('off')
        fig.suptitle(f'n={n}: top-6 SHARED spatial basis patterns (hidden source directions)')
        fig.tight_layout()
        fig.savefig(os.path.join(figdir, f'angles_basis_{n}.png'), dpi=110)
        plt.close(fig)
        w(f"  saved: figs/angles_latent_{n}.png, figs/angles_basis_{n}.png")
        json_out[str(n)] = {
            'K': K, 'D': D, 'r': int(V.shape[1]), 'k90': k90,
            'k90_over_n': round(k90 / n, 3), 'k90_over_D': round(k90 / D, 4),
            'corr_PC1_ring': round(float(corr), 3),
            'sil_svd_top2': round(float(sil_svd), 3),
            'sil_rand_max': round(float(sils_rand.max()), 3),
            'sil_rand_mean': round(float(sils_rand.mean()), 3),
        }
    report = "\n".join(out)
    print(report)
    with open(os.path.join(os.path.dirname(__file__), 'highdim_angles.txt'), 'w') as f:
        f.write(report + "\n")
    with open(os.path.join(os.path.dirname(__file__), 'highdim_angles.json'), 'w') as f:
        json.dump(json_out, f, indent=1)

if __name__ == '__main__':
    main()
