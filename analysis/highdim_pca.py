"""
Probe for the hypothesis:
  "Low-dimensional (apparently disordered) NTIL point sets might be the
   projection / shadow of a higher-dimensional ORDERED structure."

We test the SET-level version: take ALL real NTIL solutions for a fixed n
(as binary n*n vectors in R^{n^2}) and ask whether they lie near a
low-dimensional manifold. A small intrinsic dimension supports the idea
that the solution space is the "shadow" of a higher-D ordered object.

We compare against a NULL model: random 2-per-row placements (same row
constraint, no collinearity constraint) -- these should be LESS structured
(higher intrinsic dimension). If real NTIL solutions have markedly lower
intrinsic dimension, that is evidence of hidden order.

Intrinsic dimension = number of principal components needed to explain
90% (and 95%) of variance.
"""

import os, math, random, time
import numpy as np

ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
CACHE = 'flammenkamp_cache'

def decode(line, n):
    line = line.strip()
    if len(line) < 2 or line[0] != '.':
        return None
    body = line[1:]
    if len(body) != 2 * n:
        return None
    pts = []; per = len(body) // n
    for y in range(n):
        for j in range(per):
            ch = body[y * per + j]
            if ch not in ALPHABET:
                return None
            pts.append((ALPHABET.index(ch), y))
    return pts

def intrinsic_dim(X):
    # X: (M, D) float. Intrinsinc dim via SVD of Gram matrix.
    # BUG (retained for historical record, DO NOT USE): this squares the
    # Gram singular values a second time, i.e. weights variance by sigma^4,
    # which massively over-weights top PCs and yields an ARTIFICIALLY SMALL
    # k90. The correct metric (covariance eigenvalues ~ sigma^2) is in
    # highdim_manifold.py / highdim_angles.py. Numbers produced by this
    # function (the "1.7n / 4x thinner" claim) are INVALID.
    G = X.T @ X
    s = np.linalg.svd(G, compute_uv=False)
    var = s ** 2
    tot = var.sum()
    if tot == 0:
        return len(s), len(s)
    cum = np.cumsum(var) / tot
    k90 = int((cum < 0.90).sum()) + 1
    k95 = int((cum < 0.95).sum()) + 1
    return k90, k95, len(s)

def main():
    random.seed(12345)
    ns = [10, 12, 14, 16, 18, 20]
    out = []
    for n in ns:
        f = f'{CACHE}/n{n}_iden'
        if not os.path.exists(f):
            out.append(f"n={n}: no iden cache (skip)"); print(out[-1], flush=True); continue
        sols = []
        with open(f) as fh:
            for line in fh:
                p = decode(line, n)
                if p:
                    sols.append(p)
        M = len(sols)
        if M < 20:
            out.append(f"n={n}: only {M} iden sols (too few)"); print(out[-1], flush=True); continue
        X = np.zeros((M, n * n), dtype=float)
        for r, p in enumerate(sols):
            for (x, y) in p:
                X[r, y * n + x] = 1.0
        k90, k95, nsing = intrinsic_dim(X)
        # NULL: random 2-per-row placements, same count M
        Xn = np.zeros((M, n * n), dtype=float)
        for r in range(M):
            for y in range(n):
                cols = random.sample(range(n), 2)
                for c in cols:
                    Xn[r, y * n + c] = 1.0
        k90n, k95n, _ = intrinsic_dim(Xn)
        d2 = n * n
        out.append(f"n={n} M={M} D={d2}  REAL k90={k90} k95={k95}  "
                   f"NULL k90={k90n} k95={k95n}  ratio_REAL/D={k90/d2:.3f}")
        print(out[-1], flush=True)
    with open(os.path.join(os.path.dirname(__file__), 'highdim_pca.txt'), 'w') as fo:
        fo.write('\n'.join(out) + '\n')
    print("\nInterpretation: if k90(REAL) << k90(NULL) and << D, the solution set")
    print("clusters near a low-D manifold -> consistent with 'shadow of high-D order'.")

main()
