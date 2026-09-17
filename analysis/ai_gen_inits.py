#!/usr/bin/env python3
"""AI heuristic: learn an empirical prior over cell positions from known
small-m solutions, then sample initial 37-cell configurations biased by it.

Hypothesis: good cells for rot4-NTIL live in characteristic regions of the
fundamental domain; pooling the m=5..19,36 solutions into a normalized
heat-map and sampling from it should give SA a better starting point than
uniform random init (transfer learning across m).

Output: results/ai_prior/seedNN.txt  and  results/ai_random/seedNN.txt
each line "x y" (m cells), ready for csearch2 --init.
"""
import json, glob, os, random, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SOL = os.path.join(HERE, "results", "solutions")
G = 37  # heat-map resolution on normalized [0,1]^2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--seed", type=int, default=12345)
    a = ap.parse_args()
    random.seed(a.seed)

    heat = [[0.0] * G for _ in range(G)]
    files = sorted(glob.glob(os.path.join(SOL, "m*.json")))
    ncell = 0
    for f in files:
        d = json.load(open(f))
        m_s = d["m"]
        cells = d.get("cells", [])
        if m_s < 3:
            continue
        for (x, y) in cells:
            u = x / (m_s - 1)
            v = y / (m_s - 1)
            gi = min(G - 1, int(u * (G - 1) + 0.5))
            gj = min(G - 1, int(v * (G - 1) + 0.5))
            heat[gi][gj] += 1.0
            ncell += 1

    mx = max(max(row) for row in heat) or 1.0
    w = [[heat[i][j] / mx for j in range(G)] for i in range(G)]

    m = a.m

    def weight(cx, cy):
        u = cx / (m - 1)
        v = cy / (m - 1)
        fx = u * (G - 1)
        fy = v * (G - 1)
        i0 = int(fx)
        j0 = int(fy)
        i1 = min(G - 1, i0 + 1)
        j1 = min(G - 1, j0 + 1)
        tx = fx - i0
        ty = fy - j0
        return (w[i0][j0] * (1 - tx) * (1 - ty) + w[i1][j0] * tx * (1 - ty) +
                w[i0][j1] * (1 - tx) * ty + w[i1][j1] * tx * ty)

    os.makedirs(os.path.join(HERE, "results", "ai_prior"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "results", "ai_random"), exist_ok=True)
    prior = []
    rnd = []
    for s in range(a.k):
        chosen = set()
        tries = 0
        while len(chosen) < m and tries < 200000:
            cx = random.randrange(m)
            cy = random.randrange(m)
            if (cx, cy) in chosen:
                tries += 1
                continue
            wt = weight(cx, cy)
            if random.random() < (wt + 0.02) / 1.02:
                chosen.add((cx, cy))
            tries += 1
        while len(chosen) < m:
            chosen.add((random.randrange(m), random.randrange(m)))
        prior.append(sorted(chosen))
        rset = set()
        while len(rset) < m:
            rset.add((random.randrange(m), random.randrange(m)))
        rnd.append(sorted(rset))

    for s, ch in enumerate(prior):
        with open(os.path.join(HERE, "results", "ai_prior", "seed%02d.txt" % s), "w") as f:
            for (x, y) in ch:
                f.write(f"{x} {y}\n")
    for s, ch in enumerate(rnd):
        with open(os.path.join(HERE, "results", "ai_random", "seed%02d.txt" % s), "w") as f:
            for (x, y) in ch:
                f.write(f"{x} {y}\n")
    print(f"generated {a.k} prior + {a.k} random inits (m={m}, cells/each={m}, source_cells={ncell})")


if __name__ == "__main__":
    main()
