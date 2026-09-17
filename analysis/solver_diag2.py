"""Pinpoint the FIRST move that introduces a line-membership discrepancy
(full lpts dict vs brute), not just a total_bad scalar difference.

This catches corruption on size-2 lines that the scalar test hides.
"""
import random, sys
from collections import defaultdict
import importlib.util

spec = importlib.util.spec_from_file_location(
    "solver_theory_m37",
    __file__.replace("solver_diag2.py", "solver_theory_m37.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def brute_lpts(lifts, present):
    lp = defaultdict(set)
    N = len(lifts)
    for a in range(N):
        if not present[a]:
            continue
        for b in range(a + 1, N):
            if not present[b]:
                continue
            if lifts[a] == lifts[b]:
                continue
            k = S.line_of(lifts[a], lifts[b])
            lp[k].add(a)
            lp[k].add(b)
    return lp


def lpts_equal(lp_incr, lp_true):
    # Singletons (size-1 lines) are harmless for total_bad and are never
    # produced by the brute (pair-only) scan; prune them from BOTH sides so we
    # only compare real multi-member lines.  A real bug shows as a size>=2 key
    # that disagrees (incremental missing a member -> size1 vs size2).
    def multi(d):
        return {k: v for k, v in d.items() if len(v) >= 2}
    mi = multi(lp_incr); mt = multi(lp_true)
    keys = set(mi) | set(mt)
    for k in keys:
        si = mi.get(k, set())
        st = mt.get(k, set())
        if si != st:
            return False, k, si, st
    return True, None, None, None


def replay(m, n_moves, seed):
    rng = random.Random(seed)
    edges = S.generate_2factor(m, rng)
    cells = S.orient(edges, rng)
    board = S.Board(m)
    board.build(edges, cells)
    # sanity: build should be exact
    ok, k, si, st = lpts_equal(board.lpts, brute_lpts(board.lifts, board.present))
    if not ok:
        print(f"BUILD itself inconsistent on line {k}: incr={sorted(si)} true={sorted(st)}")
        return
    E = m
    for mv in range(n_moves):
        if rng.random() < 0.7:
            e = rng.randrange(E)
            if board.edges[e][0] == board.edges[e][1]:
                continue
            old_cell = board.cells[e]
            board.flip_orientation(e)
            # always ACCEPT in this diagnostic (no undo) to isolate flip logic
            ok, k, si, st = lpts_equal(board.lpts, brute_lpts(board.lifts, board.present))
            if not ok:
                print(f"FLIP discrepancy at mv {mv}, edge {e}")
                print(f"  line {k}: incr={sorted(si)} true={sorted(st)}")
                # locals
                for idx in sorted(st):
                    print(f"   TRUE   {idx}: {board.lifts[idx]} present={board.present[idx]}")
                for idx in sorted(si):
                    print(f"   INCR   {idx}: {board.lifts[idx]}")
                return
        else:
            e1 = rng.randrange(E); e2 = rng.randrange(E)
            if e1 == e2:
                continue
            delta, undo = board.two_switch(e1, e2)
            if undo is None:
                continue
            ok, k, si, st = lpts_equal(board.lpts, brute_lpts(board.lifts, board.present))
            if not ok:
                print(f"2SWITCH discrepancy at mv {mv}, e1={e1} e2={e2}")
                print(f"  line {k}: incr={sorted(si)} true={sorted(st)}")
                for idx in sorted(st):
                    print(f"   TRUE   {idx}: {board.lifts[idx]} present={board.present[idx]}")
                for idx in sorted(si):
                    print(f"   INCR   {idx}: {board.lifts[idx]}")
                return
    print(f"CONSISTENT for {n_moves} moves (m={m}, seed={seed})")


if __name__ == "__main__":
    m = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    nm = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 12345
    replay(m, nm, seed)
