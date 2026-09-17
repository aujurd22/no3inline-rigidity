"""
cpsat_m37.py — exact, COMPACT CP-SAT re-encoding of rot4 NTIL as the R8 (X)+(S) system.

VARIABLES
    sel[p] in {0,1}  for every quadrant position p in {0..m-1}^2   (m^2 vars)

CARDINALITY
    sum_p sel[p] = m                      # pick exactly m distinct C4-orbit reps

PER-LINE WEIGHTED at-most-2 CONSTRAINT  (replaces all X- and S-clauses)
    For every board line L (over the 2m x 2m grid), let
        w_p = number of C4-rotations r with c4(p, r) on L        # w_p in {1, 2}
    add   sum_{p on L}  w_p * sel[p]  <=  2.

WHY THIS IS EXACT (and == (X)^(S) by Theorem R8)
    Three collinear lifted points always lie on a single line L'; their source
    positions contribute >=3 to sum w_p*sel[p] on L'  -> forbidden.  Conversely,
    sum w_p*sel[p] <= 2 on every line means no line carries >=3 lifted points,
    i.e. no three collinear -> rot4 NTIL.  This single family of constraints
    captures BOTH layer X (3 distinct cells) and layer S (2 images of one cell
    + 1 of another): a position with w_p=2 already uses the budget of 2, so no
    other position on L may be selected -- exactly the S clause.

This collapses the earlier ~31M 3-literal clauses (for m=37) into ~tens of
thousands of efficient at-most-2 constraints with strong global propagation.

BACKENDS
    OR-Tools CP-SAT if importable (preferred); otherwise Z3.
    --seed-known m  : load a KNOWN rot4 solution for m, pass it as a solver hint,
                      and confirm the instance ADMITS it (reachability proof for
                      all m that have a cached solution, independent of discovery).

USAGE
    python cpsat_m37.py --count-only --m 37
    python cpsat_m37.py --validate                 # discovery sweep on small m
    python cpsat_m37.py --seed-known 36            # confirm instance admits known sol
    python cpsat_m37.py --m 37 --timelimit 1800     # the open-problem attack
"""
import os, sys, time, argparse
from collections import defaultdict
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quadratic_sidon_completeness import c4

try:
    from ortools.sat.python import cp_model
    HAVE_ORTOOLS = True
except Exception:
    HAVE_ORTOOLS = False

try:
    import z3
    HAVE_Z3 = True
except Exception:
    HAVE_Z3 = False


def reduced_dir(dx, dy):
    g = math.gcd(abs(dx), abs(dy))
    if g == 0:
        g = 1
    dx //= g; dy //= g
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return (dx, dy)


def generate_constraints(m):
    """Return list of dicts {pos_id: weight} -- one per board line L whose total
    weight exceeds 2 (i.e. a non-trivial at-most-2 constraint)."""
    n = 2 * m
    N = n
    inv = {}
    for x in range(m):
        for y in range(m):
            for r in range(4):
                Q = c4((x, y), r, n)
                inv[Q] = (x, y, r)
    flat = lambda x, y: x * m + y

    dirs = set()
    for dx in range(-(N - 1), N):
        for dy in range(0, N):
            if dx == 0 and dy == 0:
                continue
            if math.gcd(abs(dx), dy) != 1:
                continue
            dirs.add(reduced_dir(dx, dy))

    constraints = []
    for (dx, dy) in dirs:
        perp = (-dy, dx)
        groups = defaultdict(list)
        for X in range(N):
            for Y in range(N):
                key = perp[0] * X + perp[1] * Y
                groups[key].append((X, Y))
        for key, pts in groups.items():
            pos_w = defaultdict(int)
            for (X, Y) in pts:
                t = inv.get((X, Y))
                if t is None:
                    continue
                p = flat(t[0], t[1])
                pos_w[p] += 1
            total = sum(pos_w.values())
            if total > 2:
                constraints.append(dict(pos_w))
    return constraints


def solve_ortools(m, constraints, timelimit, workers=8, mem_mb=0):
    nv = m * m
    model = cp_model.CpModel()
    sel = [model.NewBoolVar(f"s{i}") for i in range(nv)]
    for d in constraints:
        terms = [sel[p] for p in d] if all(v == 1 for v in d.values()) \
            else [w * sel[p] for p, w in d.items()]
        model.Add(sum(terms) <= 2)
    model.Add(sum(sel) == m)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timelimit
    solver.parameters.num_search_workers = workers
    if mem_mb and mem_mb > 0:
        solver.parameters.max_memory_in_mb = mem_mb
    st = solver.Solve(model)
    status = solver.StatusName(st)
    chosen = [i for i in range(nv) if solver.Value(sel[i]) == 1] if status in ("FEASIBLE", "OPTIMAL") else []
    return status, chosen


def solve_z3(m, constraints, timelimit):
    nv = m * m
    sel = [z3.Bool(f"s{i}") for i in range(nv)]
    s = z3.Solver()
    s.set("timeout", int(timelimit * 1000))
    for d in constraints:
        terms = [sel[p] for p in d] if all(v == 1 for v in d.values()) \
            else [w * sel[p] for p, w in d.items()]
        s.add(z3.Sum(terms) <= 2)
    s.add(z3.PbEq([(sel[i], 1) for i in range(nv)], m))
    res = s.check()
    chosen = [i for i in range(nv) if s.model().eval(sel[i])] if res == z3.sat else []
    return str(res), chosen


def unflat(p, m):
    return (p // m, p % m)


def verify(m, chosen_ids):
    from constraint_prop_solver import x_full, s_full
    cells = [unflat(p, m) for p in chosen_ids]
    assert len(cells) == m, f"expected {m} cells, got {len(cells)}"
    return (not x_full(cells, m)) and (not s_full(cells, m)), cells


def known_hint(m):
    from quadratic_sidon_completeness import load_known
    sols = load_known(m)
    if not sols:
        return None
    # load_known returns odd-pairing values (a_i, b_i); invert to quadrant coords:
    #   x = m - (a+1)/2,  y = m - (b+1)/2   (see r8_proof.md setup)
    hint = [0] * (m * m)
    for (a, b) in sols[0][:m]:
        x = m - (a + 1) // 2
        y = m - (b + 1) // 2
        hint[x * m + y] = 1
    return hint


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--timelimit", type=float, default=900.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--mem-mb", type=int, default=0,
                    help="CP-SAT memory cap (MB); 0 = unlimited")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--seed-known", type=int, default=0,
                    help="load KNOWN rot4 solution for this m and hint the solver")
    ap.add_argument("--backend", choices=["auto", "ortools", "z3"], default="auto")
    args = ap.parse_args()

    backend = args.backend
    if backend == "auto":
        backend = "ortools" if HAVE_ORTOOLS else ("z3" if HAVE_Z3 else "none")

    # seed-known: validate reachability for a specific m that has a cached solution.
    # A solver is not required: we directly check that the KNOWN rot4 solution
    # (converted to quadrant sel-bits) satisfies every per-line at-most-2
    # constraint and the cardinality -> the instance ADMITS it (reachability
    # proof independent of discovery difficulty).
    if args.seed_known:
        m = args.seed_known
        t0 = time.time()
        cons = generate_constraints(m)
        hint = known_hint(m)
        if hint is None:
            print(f"no cached solution for m={m}"); return
        card_ok = (sum(hint) == m)
        viol = 0
        for d in cons:
            if sum(hint[p] * w for p, w in d.items()) > 2:
                viol += 1
        admitted = (viol == 0 and card_ok)
        print(f"[seed-known] m={m}: constraints={len(cons)} card_ok={card_ok} "
              f"violations={viol} -> known-solution-ADMITTED={admitted} "
              f"[{time.time()-t0:.1f}s]")
        return

    if args.validate:
        print("== discovery sweep (small m) ==")
        for m in range(3, 16):
            t0 = time.time()
            cons = generate_constraints(m)
            if backend == "ortools" and HAVE_ORTOOLS:
                status, chosen = solve_ortools(m, cons, 60.0, args.workers, args.mem_mb)
            elif backend == "z3" and HAVE_Z3:
                status, chosen = solve_z3(m, cons, 60.0)
            else:
                print(f"  m={m}: no backend"); continue
            ok = False
            if chosen:
                ok, _ = verify(m, chosen)
            print(f"  m={m}: constraints={len(cons)} vars={m*m} "
                  f"backend={backend} status={status} found={len(chosen)} "
                  f"verify={ok} [{time.time()-t0:.1f}s]")
        return

    t0 = time.time()
    cons = generate_constraints(args.m)
    print(f"[gen] m={args.m}: constraints={len(cons)} vars={args.m*args.m} "
          f"[{time.time()-t0:.1f}s]")
    if args.count_only:
        return

    t1 = time.time()
    if backend == "ortools" and HAVE_ORTOOLS:
        status, chosen = solve_ortools(args.m, cons, args.timelimit, args.workers, args.mem_mb)
    elif backend == "z3" and HAVE_Z3:
        status, chosen = solve_z3(args.m, cons, args.timelimit)
    else:
        print("NO BACKEND"); return
    print(f"[solve] backend={backend} status={status} found={len(chosen)} "
          f"[{time.time()-t1:.1f}s]")
    if chosen:
        ok, cells = verify(args.m, chosen)
        print(f"[verify] (X)+(S) satisfied = {ok}")
        print("cells =", cells)


if __name__ == "__main__":
    main()
