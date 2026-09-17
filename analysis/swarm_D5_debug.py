import os, sys, json, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as E
import swarm_D5_search as S

LONG = os.path.join(HERE, "results", "solver_theory_m37_long.json")
with open(LONG) as f:
    cfg = json.load(f)
edges = [tuple(e) for e in cfg["edges"]]
cells = [tuple(c) for c in cfg["cells"]]

rng = random.Random(7)

# (A) engine-only moves (flip + two_switch) for many steps; check consistency
b = E.Board(37)
b.build(edges, cells)
assert b.verify_total() == b.total_bad == 72
bad = 0
for step in range(2000):
    if rng.random() < 0.5:
        e = rng.randrange(37)
        if b.edges[e][0] != b.edges[e][1]:
            b.flip_orientation(e)
    else:
        e1 = rng.randrange(37); e2 = rng.randrange(37)
        if e1 != e2:
            d, u = b.two_switch(e1, e2)
            if u is None:
                continue
            if d > 0 and rng.random() > 0.1:
                b.undo_two_switch(u)
    if step % 200 == 0:
        if b.verify_total() != b.total_bad:
            bad += 1
            print(f"[A engine-only] step {step}: total_bad={b.total_bad} verify={b.verify_total()} MISMATCH")
print(f"[A engine-only] mismatches={bad} final total_bad={b.total_bad} verify={b.verify_total()}")

# (B) three_switch-only moves; check consistency
b2 = E.Board(37)
b2.build(edges, cells)
bad2 = 0
for step in range(2000):
    e1 = rng.randrange(37); e2 = rng.randrange(37); e3 = rng.randrange(37)
    if len({e1, e2, e3}) != 3:
        continue
    d, u = S.three_switch(b2, e1, e2, e3, rng)
    if u is None:
        continue
    if d > 0 and rng.random() > 0.1:
        S.undo_three_switch(b2, u)
    if step % 200 == 0:
        if b2.verify_total() != b2.total_bad:
            bad2 += 1
            print(f"[B three_switch] step {step}: total_bad={b2.total_bad} verify={b2.verify_total()} MISMATCH")
print(f"[B three_switch] mismatches={bad2} final total_bad={b2.total_bad} verify={b2.verify_total()}")
