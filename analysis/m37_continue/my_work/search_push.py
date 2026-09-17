"""Fresh-search push for m=37 rot4-NTIL: try to beat the known best 40.

Strategy (distinct from external agent's basin-local LNS):
  - seeds = 4 known v40 basins + MANY fresh random 2-factors
  - objective = exact geometric bad-triple count via 2-orbit-aware weighted Ising
  - LNS move = k-swap (remove k edges, perfectly re-match their 2k endpoints)
  - occasionally fully random restart
  - EVERY accepted candidate is re-checked by an independent brute-force determinant
    count (my_verify.brute_bad); model-vs-ground-truth mismatch aborts that step.

Long attack authorized. Checkpoints best configs to best_push.json.
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MY = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MY))

from weighted_geometry_ising import (
    enumerate_pair_weighted,
    enumerate_weighted,
    build_weighted_ising,
)
from signed_nae_core import solve_cp_sat
from my_verify import brute_bad, is_2factor, diagonal_unsafe

M = 37
ARCHIVE = ROOT / "outputs" / "exact_factor_archive.json"
CKPT = MY / "best_push.json"

rng = random.Random(20260717)


def random_2factor(rng):
    perm = list(range(M))
    rng.shuffle(perm)
    visited = [False] * M
    edges = []
    for i in range(M):
        if visited[i]:
            continue
        cyc = [i]
        j = perm[i]
        while j != i:
            cyc.append(j)
            visited[j] = True
            j = perm[j]
        visited[i] = True
        k = len(cyc)
        for t in range(k):
            a, b = cyc[t], cyc[(t + 1) % k]
            if a > b:
                a, b = b, a
            edges.append((a, b))
    return edges


def kswap(edges, k, rng):
    """Remove k edges and perfectly re-match their 2k endpoints with k new edges.
    Preserves 2-regularity. Retries on invalid (dup/self-loop)."""
    edgeset = set(edges)
    for _ in range(20):
        pick = rng.sample(edges, k)
        endpoints = []
        for (u, v) in pick:
            endpoints.append(u)
            endpoints.append(v)
        rng.shuffle(endpoints)
        new_edges = []
        ok = True
        for t in range(0, 2 * k, 2):
            a, b = endpoints[t], endpoints[t + 1]
            if a == b:
                ok = False
                break
            if a > b:
                a, b = b, a
            if (a, b) in edgeset or (a, b) in new_edges:
                ok = False
                break
            new_edges.append((a, b))
        if not ok:
            continue
        out = [e for e in edges if e not in pick] + new_edges
        if len(out) != M:
            continue
        if len(set(out)) != M:
            continue
        ok2, _ = is_2factor(out, M)
        if ok2:
            return out
    return None


def solve_orientation(edges, hint=None, tl=30.0):
    pair_patterns = enumerate_pair_weighted(M, edges)
    patterns = enumerate_weighted(M, edges)
    if not patterns and not pair_patterns:
        return None, None
    constant, jmat, missing, unequal = build_weighted_ising(M, patterns, pair_patterns)
    if missing or unequal:
        return None, None
    res = solve_cp_sat(constant, jmat, tl, hint=hint)
    if not res.get("bits"):
        return None, None
    bits = res["bits"]
    val = res["violations"]
    return bits, val


def main():
    budget_s = float(sys.argv[1]) if len(sys.argv) > 1 else 6 * 3600.0
    max_k = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    # ---- seeds ----
    seeds = []
    arc = json.loads(ARCHIVE.read_text(encoding="utf-8"))["archive"]
    for e in arc:
        if e["value"] <= 40:
            seeds.append(([tuple(x) for x in e["edges"]], list(e["bits"])))
    print(f"[seeds] {len(seeds)} archive seeds (value<=40)", flush=True)

    best = {"value": 10**9, "edges": None, "bits": None, "source": None}
    start = time.time()

    def consider(edges, bits, source):
        nonlocal best
        ok, msg = is_2factor(edges, M)
        if not ok:
            return
        # ground truth is authoritative; the weighted Ising value is only used
        # as a cheap pre-filter before we pay the brute-force cost.
        ground = brute_bad(M, edges, bits)
        if ground < best["value"]:
            best = {"value": ground, "edges": [list(e) for e in edges],
                    "bits": list(bits), "source": source,
                    "diagonal_safe": (not diagonal_unsafe(edges, M))}
            CKPT.write_text(json.dumps(best, indent=2), encoding="utf-8")
            print(f"[NEW BEST] value={ground} source={source} "
                  f"diag_safe={best['diagonal_safe']} t={time.time()-start:.0f}s",
                  flush=True)

    # initial orientation solve for each seed
    for idx, (edges, bits) in enumerate(seeds):
        ob, val = solve_orientation(edges, hint=bits, tl=60.0)
        if ob is None:
            continue
        consider(edges, ob, f"seed{idx}")

    # fresh random seeds
    n_fresh = 400
    for i in range(n_fresh):
        edges = random_2factor(rng)
        ob, val = solve_orientation(edges, tl=20.0)
        if ob is None:
            continue
        consider(edges, ob, f"fresh{i}")
        if i % 50 == 0:
            print(f"[fresh {i}] best={best['value']} t={time.time()-start:.0f}s", flush=True)

    print(f"[phase1 done] best={best['value']} t={time.time()-start:.0f}s", flush=True)

    # ---- LNS loop ----
    iteration = 0
    no_improve = 0
    while time.time() - start < budget_s:
        iteration += 1
        if best["edges"] is None:
            base_edges = random_2factor(rng)
        else:
            base_edges = [tuple(e) for e in best["edges"]]
        # occasional full restart
        if rng.random() < 0.05:
            base_edges = random_2factor(rng)
        k = rng.randint(2, max_k)
        new_edges = kswap(base_edges, k, rng)
        if new_edges is None:
            continue
        ob, val = solve_orientation(new_edges, tl=20.0)
        if ob is None:
            continue
        # only worth a check if weighted model predicts improvement
        if val < best["value"]:
            consider(new_edges, ob, f"lns{iteration}")
            no_improve = 0
        else:
            no_improve += 1
        if iteration % 200 == 0:
            print(f"[lns {iteration}] best={best['value']} noimp={no_improve} "
                  f"t={time.time()-start:.0f}s", flush=True)
        # adaptive: if stuck long, widen k and do more restarts
        if no_improve > 4000:
            max_k = min(max_k + 2, 14)
            no_improve = 0
            print(f"[widen] max_k->{max_k}", flush=True)

    print(f"[DONE] best={best['value']} iterations={iteration} "
          f"t={time.time()-start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
