"""Consistency diagnostic for solver_theory_m37.Board.

Strategy: build a random 2-factor board, then apply a long random sequence of
flips + two_switches (with undo for rejected SA moves) exactly the way
sa_search does.  After EVERY committed move, recompute the ground-truth bad
count from scratch (independent brute) and compare to board.total_bad.

On first mismatch we dump: the move type, the off-by line signature, and the
lpts membership (incremental) vs the true (brute) membership for that line.
"""
import random
from collections import defaultdict
import importlib.util

spec = importlib.util.spec_from_file_location(
    "solver_theory_m37",
    __file__.replace("solver_diag.py", "solver_theory_m37.py"))
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


def brute_total(lifts, present):
    lp = brute_lpts(lifts, present)
    tot = 0
    for Sset in lp.values():
        s = len(Sset)
        if s >= 3:
            tot += s * (s - 1) * (s - 2) // 6
    return tot


def run(m, n_moves, seed, allow_undo=True):
    rng = random.Random(seed)
    edges = S.generate_2factor(m, rng)
    cells = S.orient(edges, rng)
    board = S.Board(m)
    board.build(edges, cells)
    E = m
    for mv in range(n_moves):
        if rng.random() < 0.7:
            # flip
            e = rng.randrange(E)
            if board.edges[e][0] == board.edges[e][1]:
                continue
            before = board.total_bad
            old_cell = board.cells[e]
            board.flip_orientation(e)
            newbad = board.total_bad
            delta = newbad - before
            T = max(0.01, 0.05)
            # simulate SA acceptance: small T so most big deltas rejected -> undo
            accept = (newbad <= before) or (rng.random() < S.math.exp(-delta / max(T, 1e-6))) \
                if allow_undo else True
            if not accept:
                board.undo_flip(e, old_cell)
            # ground truth
            gt = brute_total(board.lifts, board.present)
            if gt != board.total_bad:
                return ("flip", mv, gt, board.total_bad, e, old_cell)
        else:
            e1 = rng.randrange(E); e2 = rng.randrange(E)
            if e1 == e2:
                continue
            before = board.total_bad
            delta, undo = board.two_switch(e1, e2)
            if undo is None:
                # move refused; board unchanged
                gt = brute_total(board.lifts, board.present)
                if gt != board.total_bad:
                    return ("2switch-refused", mv, gt, board.total_bad, (e1, e2), None)
                continue
            newbad = board.total_bad
            T = max(0.05, 1.0)
            accept = (newbad <= before) or (rng.random() < S.math.exp(-delta / max(T, 1e-6))) \
                if allow_undo else True
            if not accept:
                board.undo_two_switch(undo)
            gt = brute_total(board.lifts, board.present)
            if gt != board.total_bad:
                return ("2switch", mv, gt, board.total_bad, (e1, e2), undo)
    return None


def dump_detail(m, seed):
    """Reproduce the failing move and print the offending line + membership."""
    rng = random.Random(seed)
    edges = S.generate_2factor(m, rng)
    cells = S.orient(edges, rng)
    board = S.Board(m)
    board.build(edges, cells)
    E = m
    # replay until first flip failure
    for mv in range(100000):
        if rng.random() < 0.7:
            e = rng.randrange(E)
            if board.edges[e][0] == board.edges[e][1]:
                continue
            before = board.total_bad
            old_cell = board.cells[e]
            board.flip_orientation(e)
            newbad = board.total_bad
            delta = newbad - before
            T = max(0.01, 0.05)
            accept = (newbad <= before) or (rng.random() < S.math.exp(-delta / max(T, 1e-6)))
            if not accept:
                board.undo_flip(e, old_cell)
            gt = brute_total(board.lifts, board.present)
            if gt != board.total_bad:
                print(f"FAILED flip at mv {mv} e={e}")
                print(f"  incr total={board.total_bad}  brute total={gt}")
                # find the differing line
                lp_incr = board.lpts
                lp_true = brute_lpts(board.lifts, board.present)
                # keys in incr not in true, or with different membership
                allk = set(lp_incr) | set(lp_true)
                for k in allk:
                    si = lp_incr.get(k, set())
                    st = lp_true.get(k, set())
                    if si != st:
                        print(f"  line {k}: incr={sorted(si)} true={sorted(st)}")
                        # print coords of all lifts on this line (true)
                        print("   true coords:")
                        for idx in sorted(st):
                            print(f"     {idx}: {board.lifts[idx]} present={board.present[idx]}")
                        incr_only = sorted(si - st)
                        true_only = sorted(st - si)
                        if incr_only:
                            print("   incr-only:")
                            for idx in incr_only:
                                print(f"     {idx}: {board.lifts[idx]}")
                        if true_only:
                            print("   true-only:")
                            for idx in true_only:
                                print(f"     {idx}: {board.lifts[idx]}")
                        break
                return
        else:
            e1 = rng.randrange(E); e2 = rng.randrange(E)
            if e1 == e2:
                continue
            before = board.total_bad
            delta, undo = board.two_switch(e1, e2)
            if undo is None:
                continue
            newbad = board.total_bad
            T = max(0.05, 1.0)
            accept = (newbad <= before) or (rng.random() < S.math.exp(-delta / max(T, 1e-6)))
            if not accept:
                board.undo_two_switch(undo)
            gt = brute_total(board.lifts, board.present)
            if gt != board.total_bad:
                print(f"FAILED 2switch at mv {mv} e1={e1} e2={e2} undo={undo is not None}")
                lp_incr = board.lpts
                lp_true = brute_lpts(board.lifts, board.present)
                allk = set(lp_incr) | set(lp_true)
                for k in allk:
                    si = lp_incr.get(k, set())
                    st = lp_true.get(k, set())
                    if si != st:
                        print(f"  line {k}: incr={sorted(si)} true={sorted(st)}")
                        for idx in sorted(st):
                            print(f"     {idx}: {board.lifts[idx]}")
                        break
                return
    print("no failure in 100000 moves")


if __name__ == "__main__":
    import sys
    m = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    nm = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 12345
    print(f"m={m} n_moves={nm} seed={seed}")
    res = run(m, nm, seed)
    print("result:", res[:4] if res else "CONSISTENT", res[4:] if res else "")
    if res:
        dump_detail(m, seed)
