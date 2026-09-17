"""Correctness + speed test for the incremental pair-count Board."""
import random, time
import importlib.util

spec = importlib.util.spec_from_file_location(
    "solver_theory_m37",
    __file__.replace("solver_bench.py", "solver_theory_m37.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def correctness(m, n_moves, seed):
    rng = random.Random(seed)
    edges = S.generate_2factor(m, rng)
    cells = S.orient(edges, rng)
    board = S.Board(m)
    board.build(edges, cells)
    if board.total_bad != board.verify_total():
        return f"BUILD fail m={m}"
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
            if board.total_bad != board.verify_total():
                return f"FLIP fail m={m} mv={mv} e={e}"
        else:
            e1 = rng.randrange(E); e2 = rng.randrange(E)
            if e1 == e2:
                continue
            delta, undo = board.two_switch(e1, e2)
            if undo is None:
                if board.total_bad != board.verify_total():
                    return f"2SW-refused fail m={m} mv={mv}"
                continue
            if rng.random() >= 0.5:
                board.undo_two_switch(undo)
            if board.total_bad != board.verify_total():
                return f"2SW fail m={m} mv={mv} e1={e1} e2={e2}"
    return "OK"


def benchmark_m37(n_moves=5000, seed=42):
    rng = random.Random(seed)
    edges = S.generate_2factor(37, rng)
    cells = S.orient(edges, rng)
    board = S.Board(37)
    board.build(edges, cells)
    t0 = time.time()
    for _ in range(n_moves):
        e = rng.randrange(37)
        if board.edges[e][0] == board.edges[e][1]:
            continue
        board.flip_orientation(e)
    dt = time.time() - t0
    per = dt / n_moves * 1000.0
    return per, dt


if __name__ == "__main__":
    for (m, nm, sd) in [(15, 5000, 1), (20, 5000, 2), (30, 3000, 3),
                        (15, 5000, 99), (25, 4000, 555), (37, 2000, 7)]:
        print(f"correctness m={m} n={nm} seed={sd}: {correctness(m, nm, sd)}")
    per, dt = benchmark_m37(5000)
    print(f"m=37 per-move (incremental pair-count): {per:.3f} ms "
          f"({5000} moves in {dt:.2f}s)")
    print(f"  -> ~{int(120.0/(per/1000.0))} moves per 120s restart")
