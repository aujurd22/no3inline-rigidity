"""
greedy_repair_m37.py -- Directed "repair" local search on the rot4-NTIL model.

Implements the user's idea:
  start from a low-collinearity configuration; repeatedly pick a 3-line (a
  geometric line carrying >=3 of the 4m C4-lifts), move ONE of its points off
  that line (in our model a "point" is a C4-lift of a cell, so moving it = flip
  the cell's orientation, which relocates its 4 lifts; or restructure the
  2-factor via a two-switch), subject to keeping the row/col<=2 invariant
  (which the 2-factor enforces for free).  Observe how the residual (X) count
  changes after each move.

This is the DIRECTED counterpart of the random-walk SA: instead of proposing
random flips/two-switches, it always attacks the worst current defect line.
Answers "does greedy directed repair converge better than SA?"

Usage:
  python greedy_repair_m37.py --start results/solver_theory_m37_long.json \
        --m 37 --maxsteps 500000 --out results/greedy_repair_m37.json
  python greedy_repair_m37.py --m 10 --random --seed 1 --maxsteps 200000
"""
import os, sys, time, json, argparse, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as S

def defect_lines(board):
    return [(k, len(pts)) for k, pts in board.line_pts.items() if len(pts) >= 3]

def eval_flip(board, e):
    if board.edges[e][0] == board.edges[e][1]:
        return None
    before = board.total_bad
    orig = board.cells[e]
    board.flip_orientation(e)
    delta = board.total_bad - before
    board.undo_flip(e, orig)
    return delta

def eval_two_switch(board, e1, e2):
    before = board.total_bad
    delta, undo = board.two_switch(e1, e2)
    if undo is None:
        return None
    delta = board.total_bad - before
    board.undo_two_switch(undo)
    return delta

def greedy_repair(board, maxsteps=500000, verbose=True):
    traj = [board.total_bad]
    steps = 0
    stuck = False
    E = len(board.edges)
    while board.total_bad > 0 and steps < maxsteps:
        dlines = defect_lines(board)
        if not dlines:
            break
        # all cells touching ANY defect line
        defect_cells = sorted({i >> 2 for k, pts in board.line_pts.items()
                               if len(pts) >= 3 for i in pts})
        best = None
        # 1) flip orientation of every defect cell
        for e in defect_cells:
            d = eval_flip(board, e)
            if d is not None and (best is None or d < best[0]):
                best = (d, ("flip", e))
        # 2) two-switch every defect cell against ALL other cells
        for e1 in defect_cells:
            for e2 in range(E):
                if e2 == e1:
                    continue
                d = eval_two_switch(board, e1, e2)
                if d is not None and (best is None or d < best[0]):
                    best = (d, ("ts", e1, e2))
        if best is None or best[0] >= 0:
            stuck = True
            if verbose:
                print(f"  stuck at total_bad={board.total_bad} after {steps} steps "
                      f"(defect_cells={len(defect_cells)})", flush=True)
            break
        kind = best[1][0]
        if kind == "flip":
            board.flip_orientation(best[1][1])
        else:
            board.two_switch(best[1][1], best[1][2])
        board._recompute_total()
        traj.append(board.total_bad)
        steps += 1
        if verbose and steps % 2000 == 0:
            print(f"  step {steps}: total_bad={board.total_bad}", flush=True)
    return traj, steps, stuck

def svg_chart(vals, path, title):
    W, H = 760, 320
    if not vals:
        return
    mx = max(vals); n = len(vals)
    xstep = (W - 60) / max(1, n - 1)
    y0, y1 = 30, H - 30
    def X(i): return 40 + i * xstep
    def Y(v): return y0 + (y1 - y0) * (1 - v / max(1, mx))
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">']
    svg.append(f'<text x="40" y="20" font-size="13">{title}</text>')
    svg.append(f'<line x1="40" y1="{y0}" x2="40" y2="{y1}" stroke="#888"/>')
    svg.append(f'<line x1="40" y1="{y1}" x2="{W-20}" y2="{y1}" stroke="#888"/>')
    svg.append(f'<polyline fill="none" stroke="#c0392b" stroke-width="1.5" points="{pts}"/>')
    svg.append(f'<text x="{W-20}" y="{y1+18}" font-size="10" text-anchor="end">step {n-1}</text>')
    svg.append(f'<text x="40" y="{y0-6}" font-size="10">max={mx}</text>')
    svg.append('</svg>')
    with open(path, "w") as f:
        f.write("\n".join(svg))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--start", default=None, help="JSON with edges/cells")
    ap.add_argument("--random", action="store_true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--maxsteps", type=int, default=500000)
    ap.add_argument("--out", default="results/greedy_repair_m37.json")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    if args.random:
        edges = S.generate_2factor(args.m, rng)
        cells = S.orient(edges, rng)
        print(f"random start, edges={edges[:3]}...", flush=True)
    else:
        with open(args.start) as f:
            h = json.load(f)
        edges, cells = h["edges"], h["cells"]
    board = S.Board(args.m)
    board.build(edges, cells)
    print(f"start total_bad={board.total_bad}", flush=True)

    t0 = time.time()
    traj, steps, stuck = greedy_repair(board, maxsteps=args.maxsteps)
    dt = time.time() - t0
    print(f"DONE steps={steps} stuck={stuck} final_total_bad={board.total_bad} "
          f"time={dt:.1f}s", flush=True)

    out = {"m": args.m, "start_bad": traj[0], "final_bad": board.total_bad,
           "steps": steps, "stuck": stuck, "time": dt,
           "edges": board.edges, "cells": board.cells,
           "trajectory": traj}
    with open(args.out, "w") as f:
        json.dump(out, f)
    svg_chart(traj, args.out.replace(".json", ".svg"),
              f"greedy repair m={args.m}: residual (X) vs step")
    print(f"saved -> {args.out}")
