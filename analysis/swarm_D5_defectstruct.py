"""swarm_D5_defectstruct.py -- characterize the 72 residual defect lines of the
m=37 deep local min: for each bad line (size 3), how many DISTINCT cells do its
3 lifts belong to?  If most are 2-cell, a 2-switch between those two cells is the
natural repair; if many are 3-cell, richer moves are needed.  Also: does pure
orientation-flipping (holding the 2-factor fixed) reduce the count at all? -- if
not, the min is structural (needs 2-factor change), not an orientation artifact."""
import os, sys, json, math
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as E

LONG = os.path.join(HERE, "results", "solver_theory_m37_long.json")
with open(LONG) as f:
    cfg = json.load(f)
board = E.Board(37)
board.build([tuple(e) for e in cfg["edges"]], [tuple(c) for c in cfg["cells"]])
assert board.verify_total() == 72

# defect lines: label -> set of lift indices
line_lifts = defaultdict(set)
for a in range(len(board.lifts)):
    for b in range(a+1, len(board.lifts)):
        if board.lifts[a] == board.lifts[b]:
            continue
        k = E.line_of(board.lifts[a], board.lifts[b])
        line_lifts[k].add(a); line_lifts[k].add(b)

cells_per_line = defaultdict(int)
for k, S in line_lifts.items():
    if len(S) >= 3:
        cells = {i >> 2 for i in S}
        cells_per_line[len(cells)] += 1

# can pure flipping reduce it? greedy hill-climb on flips only (hold 2-factor
# fixed). Keep iterations modest (fast incremental, but avoid 10^5 loop cost).
import random
rng = random.Random(1)
cur = board.total_bad
best = cur
for _ in range(6000):
    e = rng.randrange(37)
    if board.edges[e][0] == board.edges[e][1]:
        continue
    before = board.total_bad
    board.flip_orientation(e)
    if board.total_bad <= before:
        cur = board.total_bad
        best = min(best, cur)
    else:
        board.flip_orientation(e)
        cur = board.total_bad
flip_only_best = best
flip_only_final = cur

out = {
    "defect_lines_by_num_cells": dict(cells_per_line),
    "total_defect_lines": sum(cells_per_line.values()),
    "flip_only_greedy_best": flip_only_best,
    "flip_only_greedy_final": flip_only_final,
    "note": ("If flip_only_greedy_best==72, pure orientation changes cannot "
             "escape the min -> it is a 2-factor (structural) local min, "
             "consistent with needing two/three-switches to improve."),
}
print(json.dumps(out, indent=2))
with open(os.path.join(HERE, "results", "swarm_D5_defectstruct.json"), "w") as f:
    json.dump(out, f, indent=2)
