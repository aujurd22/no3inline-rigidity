"""
parallel_repair_m37.py -- COORDINATED multi-line repair on the rot4-NTIL model.

User's refined idea: instead of moving ONE point on ONE 3-line at a time
(single-move greedy, which got stuck at 72 on step 0), move ONE point on
EVERY 3-line SIMULTANEOUSLY -- i.e. for each current defect line, flip one of
its cells (relocating that cell's 4 C4-lifts to the other orbit), and apply all
such flips together as one coordinated batch.  Observe whether the coordinated
batch can escape the basin that single-move greedy (and SA) are stuck in.

In our rot4/2-factor model a "point" is a C4-lift of a cell, so "moving it to a
place without collinearity" is faithfully implemented as flipping the cell's
orientation (the only other location its 4 lifts can occupy).  The coordination
is what differs from greedy_repair_m37.py: there, only the single worst line's
cells were considered; here, every defect line contributes one flip and they are
applied jointly, so a flip that worsens its own line can still be accepted if
another flip elsewhere compensates.

We sample many coordinated batches per step (random selection of one cell per
line) plus a few deterministic candidates, keep the best-improving batch, apply
it, repeat until stuck (no improving batch exists) or time limit.

Usage:
  python parallel_repair_m37.py --start results/solver_theory_m37_long.json \
        --m 37 --time 240 --out results/parallel_repair_m37.json
"""
import os, sys, time, json, argparse, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as S
from greedy_repair_m37 import defect_lines


def _flip_batch(board, cells):
    """Apply flips to a set of (distinct) cells; return list of (e, old) for undo."""
    flipped = []
    for e in cells:
        old = board.cells[e]
        board.flip_orientation(e)
        flipped.append((e, old))
    return flipped


def _undo_batch(board, flipped):
    for e, old in reversed(flipped):
        board.undo_flip(e, old)


def parallel_repair(board, time_budget, rng, samples=200, verbose=True):
    start = time.time()
    traj = [board.total_bad]
    steps = 0
    stuck = False
    E = len(board.edges)
    while time.time() - start < time_budget and board.total_bad > 0:
        dlines = defect_lines(board)
        if not dlines:
            break
        # line -> list of cells touching it
        line_cells = {k: sorted({i >> 2 for i in board.line_pts[k]}) for k, _ in dlines}

        best = None  # (delta, frozenset(cells to flip))

        # (a) random coordinated batches: one cell per line, applied jointly
        for _ in range(samples):
            chosen = set()
            for cells in line_cells.values():
                if cells:
                    chosen.add(rng.choice(cells))
            if not chosen:
                continue
            before = board.total_bad
            flipped = _flip_batch(board, chosen)
            delta = board.total_bad - before
            if best is None or delta < best[0]:
                best = (delta, set(chosen))
            _undo_batch(board, flipped)

        # (b) deterministic candidate: per line pick the cell whose own flip is
        # most negative (greedy local), assemble jointly.
        det = set()
        for cells in line_cells.values():
            bcell = None
            bdelta = 0
            for e in cells:
                before = board.total_bad
                flipped = _flip_batch(board, [e])
                d = board.total_bad - before
                _undo_batch(board, flipped)
                if bcell is None or d < bdelta:
                    bcell, bdelta = e, d
            if bcell is not None:
                det.add(bcell)
        if det:
            before = board.total_bad
            flipped = _flip_batch(board, det)
            delta = board.total_bad - before
            if best is None or delta < best[0]:
                best = (delta, set(det))
            _undo_batch(board, flipped)

        if best is None or best[0] >= 0:
            stuck = True
            if verbose:
                print(f"  STUCK at total_bad={board.total_bad} after {steps} steps "
                      f"({len(dlines)} defect lines, {len(line_cells)} mapped)",
                      flush=True)
            break

        # apply best coordinated batch
        for e in best[1]:
            board.flip_orientation(e)
        board._recompute_total()
        traj.append(board.total_bad)
        steps += 1
        if verbose and steps % 500 == 0:
            print(f"  step {steps}: total_bad={board.total_bad}", flush=True)

    return traj, steps, stuck


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--start", default="results/solver_theory_m37_long.json")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--time", type=float, default=240)
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--out", default="results/parallel_repair_m37.json")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    with open(args.start) as f:
        h = json.load(f)
    edges, cells = h["edges"], h["cells"]
    board = S.Board(args.m)
    board.build(edges, cells)
    print(f"start total_bad={board.total_bad}", flush=True)

    t0 = time.time()
    traj, steps, stuck = parallel_repair(board, time_budget=args.time,
                                         rng=rng, samples=args.samples)
    dt = time.time() - t0
    print(f"DONE steps={steps} stuck={stuck} final_total_bad={board.total_bad} "
          f"time={dt:.1f}s", flush=True)

    out = {"m": args.m, "start_bad": traj[0], "final_bad": board.total_bad,
           "steps": steps, "stuck": stuck, "time": dt,
           "edges": board.edges, "cells": board.cells, "trajectory": traj}
    with open(args.out, "w") as f:
        json.dump(out, f)
    print(f"saved -> {args.out}")
