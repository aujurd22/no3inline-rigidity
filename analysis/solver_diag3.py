"""Pinpoint pair-count incremental bug: compare self.pc to a full rescan
after every move; on first mismatch dump the offending line + which pairs
differ."""
import random
import importlib.util

spec = importlib.util.spec_from_file_location(
    "solver_theory_m37",
    __file__.replace("solver_diag3.py", "solver_theory_m37.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def full_pc(lifts):
    from collections import defaultdict
    pc = defaultdict(int)
    N = len(lifts)
    for a in range(N):
        pa = lifts[a]
        for b in range(a + 1, N):
            pb = lifts[b]
            if pa[0] == pb[0] and pa[1] == pb[1]:
                continue
            pc[S.line_of(pa, pb)] += 1
    return pc


def dump_pc_diff(board, tag, mv, extra=""):
    true = full_pc(board.lifts)
    incr = board.pc
    keys = set(true) | set(incr)
    for k in keys:
        t = true.get(k, 0)
        ic = incr.get(k, 0)
        if t != ic:
            print(f"{tag} mv={mv} {extra}: line {k}: true_pc={t} incr_pc={ic}")
            # find a pair on this line in true
            # enumerate lifts on line k: A*x+B*y==L
            A, B, L = k
            on = [i for i, (x, y) in enumerate(board.lifts)
                  if A * x + B * y == L]
            print(f"   points on line (true): {on}")
            for i in on:
                print(f"     {i}: {board.lifts[i]}")
            return True
    return False


def run(m, n_moves, seed):
    rng = random.Random(seed)
    edges = S.generate_2factor(m, rng)
    cells = S.orient(edges, rng)
    board = S.Board(m)
    board.build(edges, cells)
    if dump_pc_diff(board, "BUILD", -1, f"m={m}"):
        return
    E = m
    for mv in range(n_moves):
        if rng.random() < 0.7:
            e = rng.randrange(E)
            if board.edges[e][0] == board.edges[e][1]:
                continue
            old_cell = board.cells[e]
            board.flip_orientation(e)
            if rng.random() >= 0.5:
                board.undo_flip(e, old_cell)
            if dump_pc_diff(board, "FLIP", mv, f"e={e}"):
                return
        else:
            e1 = rng.randrange(E); e2 = rng.randrange(E)
            if e1 == e2:
                continue
            delta, undo = board.two_switch(e1, e2)
            if undo is None:
                if dump_pc_diff(board, "2SW-ref", mv):
                    return
                continue
            if rng.random() >= 0.5:
                board.undo_two_switch(undo)
            if dump_pc_diff(board, "2SW", mv, f"e1={e1} e2={e2}"):
                return
    print(f"OK m={m} {n_moves} moves seed={seed}")


if __name__ == "__main__":
    import sys
    m = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    nm = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    sd = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    run(m, nm, sd)
