"""
solve_m37_perm.py
=================
Proof-of-concept + attack for m=37 using the R9b 2-regular reformulation:
a rot4 NTIL <=> a permutation pi on the m odd vertices {1,3,...,2m-1}
(with a per-edge orientation) whose induced m cells satisfy (X)+(S).

We build the permutation cycle-by-cycle (backtracking), enforcing 2-regularity
by construction, and prune incrementally with the (X)+(S) quadratic forms
(shared memoised tables from solve_m37_backtrack) + FDR linear pruner.

This validates R9b: searching the TRUE combinatorial object (permutations, not
C(m^2,m) cell-subsets) should prune harder.  The fast production version is the
CP-SAT assignment model (see r9_modp_descent.md); this Python version proves
correctness and probes the landscape.

Usage:
  python solve_m37_perm.py --m 10 --timelimit 60
  python solve_m37_perm.py --m 37 --timelimit 3600 --restarts 30
"""
import os, sys, time, argparse, random
from collections import defaultdict
import math

# reuse geometry from solve_m37_backtrack by importing its tables
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_m37_backtrack as BT

def odd_vertices(m):
    return list(range(1, 2 * m, 2))

def cell_of_pair(a, b, m):
    # (a,b) odd -> cell (x,y) = (m-(a+1)/2, m-(b+1)/2)
    return ((m - (a + 1) // 2) * m) + (m - (b + 1) // 2)

def solve(m, timelimit, restarts, seed=0):
    BT.build(m)
    rng = random.Random(seed)
    odds = odd_vertices(m)
    start = time.time()
    deadline = start + timelimit
    nodes = [0]
    best = [0]

    def backtrack(edges, fdr_cnt, out_assigned, in_assigned, avail_src, avail_tgt):
        if time.time() > deadline:
            return None
        nodes[0] += 1
        d = len(edges)
        if d > best[0]:
            best[0] = d
        if d == m:
            # edges: list of (a,b) pairs; build cells, verify
            cells = [cell_of_pair(a, b, m) for (a, b) in edges]
            return list(cells)
        # pick next source: prefer an avail_src vertex
        src_choices = [i for i in avail_src]
        rng.shuffle(src_choices)
        for i in src_choices:
            tgt_choices = [j for j in avail_tgt if j != i]
            rng.shuffle(tgt_choices)
            for j in tgt_choices:
                # edge i->j, orientation bit
                for (a, b) in ((i, j), (j, i)):
                    cell = cell_of_pair(a, b, m)
                    dk = BT.cell_diff(cell)
                    if fdr_cnt.get(dk, 0) + fdr_cnt.get(-dk, 0) >= 2:
                        continue
                    # S: with each existing edge's cell
                    ok = True
                    ci = cell
                    for (ea, eb) in edges:
                        cj = cell_of_pair(ea, eb, m)
                        if BT.pair_s_bad(ci, cj) or BT.pair_s_bad(cj, ci):
                            ok = False
                            break
                    if not ok:
                        continue
                    # X: with each pair of existing edges' cells
                    ch = [cell_of_pair(ea, eb, m) for (ea, eb) in edges]
                    nch = len(ch)
                    broken = False
                    for p in range(nch):
                        for q in range(p + 1, nch):
                            if ci in BT.pair_x_bad(ch[p], ch[q]) or ci in BT.pair_x_bad(ch[q], ch[p]):
                                broken = True
                                break
                        if broken:
                            break
                    if broken:
                        continue
                    edges.append((a, b))
                    fdr_cnt[dk] = fdr_cnt.get(dk, 0) + 1
                    out_assigned.add(i); in_assigned.add(j)
                    avail_src.discard(i); avail_tgt.discard(j)
                    res = backtrack(edges, fdr_cnt, out_assigned, in_assigned, avail_src, avail_tgt)
                    if res is not None:
                        return res
                    avail_src.add(i); avail_tgt.add(j)
                    out_assigned.discard(i); in_assigned.discard(j)
                    fdr_cnt[dk] -= 1
                    if fdr_cnt[dk] == 0:
                        del fdr_cnt[dk]
                    edges.pop()
                    if time.time() > deadline:
                        return None
        return None

    for rs in range(restarts):
        if time.time() > deadline:
            break
        edges = []
        fdr_cnt = defaultdict(int)
        avail_src = set(odds)
        avail_tgt = set(odds)
        res = backtrack(edges, fdr_cnt, set(), set(), avail_src, avail_tgt)
        if res is not None:
            return res, nodes[0], best[0], rs
        print(f"[restart {rs}] none; nodes={nodes[0]} best={best[0]} t={time.time()-start:.1f}s", flush=True)
    return None, nodes[0], best[0], restarts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--m', type=int, default=37)
    ap.add_argument('--timelimit', type=int, default=3600)
    ap.add_argument('--restarts', type=int, default=30)
    ap.add_argument('--seed', type=int, default=777)
    args = ap.parse_args()
    print(f"[perm start] m={args.m} t={args.timelimit}s", flush=True)
    t0 = time.time()
    res, nodes, best, rs = solve(args.m, args.timelimit, args.restarts, args.seed)
    dt = time.time() - t0
    if res is not None:
        ok, info = BT.verify(res, args.m)
        print(f"[FOUND] restart={rs} nodes={nodes} best={best} t={dt:.1f}s verify_ntil={ok}", flush=True)
        out = "results/m37_perm_solution.txt"
        with open(out, 'w') as f:
            f.write(" ".join(str(c) for c in sorted(res)))
            f.write(f"\n# perm-model verify_ntil={ok} nodes={nodes} t={dt:.1f}s\n")
        print(f"[saved] {out}", flush=True)
    else:
        print(f"[TIMEOUT] nodes={nodes} best={best} t={dt:.1f}s", flush=True)

if __name__ == '__main__':
    main()
