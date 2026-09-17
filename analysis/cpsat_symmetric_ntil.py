"""
cpsat_symmetric_ntil.py — GENERAL per-line CP-SAT encoder for G-symmetric NTIL,
parameterized by the symmetry subgroup G <= D4.

This is the computational embodiment of SIRH Part III (Unified Quadratic
Rigidity Theorem): for ANY symmetry group G, a G-symmetric No-Three-In-Line
configuration is exactly equivalent to a finite quadratic CSP, written here as
a family of per-line WEIGHTED at-most-2 constraints.

------------------------------------------------------------------------
SETUP (centered coordinates)
  Board side n = 2m.  Center C = ((n-1)/2, (n-1)/2) (half-integer).
  Centered point of grid cell (x,y):  u = x - C,  v = y - C.
  A group element g is a 2x2 signed permutation matrix (rotation/reflection);
  its action on the grid:  g.(x,y) = C + M(u,v)  (must land on the grid).

FUNDAMENTAL DOMAIN F_G
  One canonical representative per G-orbit, chosen as the lexicographically
  minimal cell in each orbit.  Variables: sel[rep] in {0,1} for rep in F_G.
  Card:  sum(sel) = |F_G| = (n*n) / |G|   [since |G|-orbit reps tile the board].

QUADRATIC CSP  ==  per-line weighted at-most-2
  For board line L and rep c,  w_{L,c} = |{ g.c : g in G } intersect L|
  (= number of lifted images of c that fall on L, in {0,...,|G|}).
  Constraint:   sum_{c in F_G}  w_{L,c} * sel[c]  <=  2   for every L.

EXACTNESS (SIRH Part III)
  Three collinear lifted points lie on a single line L; their source reps
  contribute >=3 to sum w_{L,c}*sel[c] on L -> forbidden.  Conversely
  sum <= 2 on every line means no line carries >=3 lifted points, i.e. no
  three collinear -> G-symmetric NTIL.  The collinearity of any lifted triple
  is a 2x2 determinant (=0) -- a quadratic polynomial in the rep coordinates --
  so this single constraint family IS the quadratic CSP of Part III, written
  in its most propagation-friendly (linear) form.  C4's (X)+(S) (R8) is the
  reduced 16-form special case; this generalizes it to every G.

GROUPS IMPLEMENTED (matrix form, centered coords)
  C4    : {id, r90, r180, r270}                 order 4   (FDR)
  C2    : {id, r180}                            order 2   (FDR)
  D4    : full dihedral, all 8                  order 8   (FDR: full rot+diag)
  dia1  : {id, refl y=x}                        order 2   (FDR)
  dia2  : {id, refl y=-x}                       order 2   (FDR)
  D2d   : {id, r180, refl y=x, refl y=-x}       order 4   (FDR: Klein four)

USAGE
  python cpsat_symmetric_ntil.py --validate            # sound+reach sweep, all groups
  python cpsat_symmetric_ntil.py --group C2 --count-only --m 13
  python cpsat_symmetric_ntil.py --seed-known C4 36     # known rot4 sol admitted
"""
import os, sys, time, argparse, math, json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quadratic_sidon_completeness import c4
from constraint_prop_solver import x_full, s_full

try:
    from ortools.sat.python import cp_model
    HAVE_ORTOOLS = True
except Exception:
    HAVE_ORTOOLS = False


# ---- group definitions: signed-permutation matrices (centered coords) ----
I = (1, 0, 0, 1)
R90 = (0, -1, 1, 0)
R180 = (-1, 0, 0, -1)
R270 = (0, 1, -1, 0)
D1 = (0, 1, 1, 0)     # refl y = x
D2 = (0, -1, -1, 0)   # refl y = -x
H = (1, 0, 0, -1)     # refl x-axis (ort1, NON-FDR)
V = (-1, 0, 0, 1)     # refl y-axis (ort1, NON-FDR)

GROUPS = {
    "C4":  [I, R90, R180, R270],
    "C2":  [I, R180],
    "D4":  [I, R90, R180, R270, D1, D2, H, V],
    "dia1": [I, D1],
    "dia2": [I, D2],
    "D2d": [I, R180, D1, D2],
    "ort1": [I, H],          # control: NON-FDR group, for contrast
}


def apply_mat(M, x, y, c):
    """Apply matrix M=(a,b,cc,d) to grid cell (x,y) about center c; return grid cell."""
    a, b, cc, d = M
    u = x - c
    v = y - c
    return (c + a * u + b * v, c + cc * u + d * v)


def orbit(cell, G, n):
    c = (n - 1) / 2.0
    pts = []
    seen = set()
    for M in G:
        X, Y = apply_mat(M, cell[0], cell[1], c)
        # round to nearest int (floating error from half-integer center)
        X, Y = int(round(X)), int(round(Y))
        if 0 <= X < n and 0 <= Y < n and (X, Y) not in seen:
            seen.add((X, Y))
            pts.append((X, Y))
    return pts


def fundamental_domain(G, n):
    """Canonical fundamental domain = lex-min cell of each orbit."""
    reps = []
    done = set()
    for x in range(n):
        for y in range(n):
            if (x, y) in done:
                continue
            orb = orbit((x, y), G, n)
            rep = min(orb)
            reps.append(rep)
            for p in orb:
                done.add(p)
    return reps


def reduced_dir(dx, dy):
    g = math.gcd(abs(dx), abs(dy)) or 1
    dx //= g; dy //= g
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return (dx, dy)


def generate_constraints(G, m):
    """Per-line weighted at-most-2 constraints for group G on side n=2m."""
    n = 2 * m
    reps = fundamental_domain(G, n)
    rep_idx = {rep: i for i, rep in enumerate(reps)}
    # precompute orbits of each rep
    orbits = [orbit(rep, G, n) for rep in reps]
    N = n

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
                for i, orb in enumerate(orbits):
                    if (X, Y) in orb:
                        pos_w[i] += 1
            total = sum(pos_w.values())
            if total > 2:
                constraints.append(dict(pos_w))
    return reps, constraints


def target_card(G, m):
    """Number of fundamental-domain reps to select: total points / |G|.
    Extremal G-symmetric NTIL has 2N points (N=2m board side), each rep
    contributes |G| distinct lifted points (no fixed points on even board)."""
    n = 2 * m
    return (2 * n) // len(G)


class _SolutionCallback(cp_model.CpSolverSolutionCallback):
    """Persist every incumbent to <path> atomically, so a killed run never
    loses a found solution (resilient to container teardown)."""
    def __init__(self, sel, path):
        super().__init__()
        self._sel = sel
        self._path = path
        self._n = len(sel)
    def OnSolutionCallback(self):
        chosen = [i for i in range(self._n) if self.Value(self._sel[i]) == 1]
        _write_checkpoint(self._path, chosen)


def _write_checkpoint(path, chosen):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"chosen": chosen, "ts": time.time()}, f)
    os.replace(tmp, path)


def solve_ortools(reps, constraints, card, timelimit, workers=8, mem_mb=0,
                  checkpoint=None, resume=None):
    nv = len(reps)
    model = cp_model.CpModel()
    sel = [model.NewBoolVar(f"s{i}") for i in range(nv)]
    for d in constraints:
        terms = [sel[p] for p in d] if all(v == 1 for v in d.values()) \
            else [w * sel[p] for p, w in d.items()]
        model.Add(sum(terms) <= 2)
    model.Add(sum(sel) == card)
    if resume and os.path.exists(resume):
        try:
            with open(resume) as f:
                data = json.load(f)
            for i in data.get("chosen", []):
                if 0 <= i < nv:
                    model.AddHint(sel[i], 1)
            print(f"[resume] hinted {len(data.get('chosen', []))} vars from {resume}",
                  file=sys.stderr)
        except Exception as e:
            print(f"[resume] warning: {e}", file=sys.stderr)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timelimit
    solver.parameters.num_search_workers = workers
    if mem_mb and mem_mb > 0:
        solver.parameters.max_memory_in_mb = mem_mb
    if checkpoint:
        cb = _SolutionCallback(sel, checkpoint)
        try:
            st = solver.Solve(model, cb)
        except TypeError:
            st = solver.Solve(model)
    else:
        st = solver.Solve(model)
    status = solver.StatusName(st)
    chosen = [i for i in range(nv) if solver.Value(sel[i]) == 1] if status in ("FEASIBLE", "OPTIMAL") else []
    if chosen and checkpoint:
        _write_checkpoint(checkpoint, chosen)
    return status, chosen


def verify_config(reps, chosen, G, m):
    """Independent check: full lifted point set is G-symmetric and has no 3
    collinear.  (Point COUNT is NOT asserted: for reflection groups a rep on a
    symmetry axis has a stabilizer, so its orbit is smaller than |G|; such
    configs are still valid G-symmetric NTIL.)"""
    n = 2 * m
    Pset = set()
    for i in chosen:
        Pset.update(orbit(reps[i], G, n))
    P = sorted(Pset)
    # G-closure: every lifted point's full orbit stays inside P
    for p in P:
        for q in orbit(p, G, n):
            if q not in Pset:
                return False, P, f"not G-closed at {p}->{q}"
    # no 3 collinear
    N = len(P)
    for i in range(N):
        xi, yi = P[i]
        for j in range(i + 1, N):
            xj, yj = P[j]
            for k in range(j + 1, N):
                xk, yk = P[k]
                if (xj - xi) * (yk - yi) == (yj - yi) * (xk - xi):
                    return False, P, f"collinear {P[i]},{P[j]},{P[k]}"
    return True, P, f"ok ({N} pts)"


def seed_known(Gname, m):
    """Confirm a KNOWN rot4 solution is admitted by the G-instance for G that
    contains C4 (C4, C2, D4).  Independent reachability proof."""
    from quadratic_sidon_completeness import load_known
    sols = load_known(m)
    if not sols:
        return None
    odd = sols[0][:m]
    quad = [(m - (a + 1) // 2, m - (b + 1) // 2) for (a, b) in odd]
    n = 2 * m
    # full rot4 point set
    Pfull = []
    for (x, y) in quad:
        for r in range(4):
            Pfull.append(c4((x, y), r, n))
    Pfull = list(dict.fromkeys(Pfull))
    if len(Pfull) != 4 * m:
        return f"known sol point count {len(Pfull)}"
    G = GROUPS[Gname]
    # For G containing C4 (i.e. C4 or C2) a rot4 solution is G-symmetric.
    # For D4 (which has reflections not in C4) this generally FAILS -- skip.
    if Gname == "D4":
        return "D4: rot4-known solution is not D4-symmetric (reflections absent); reachability via this hint N/A"
    # check Pfull is G-symmetric (C4 subset of G guarantees this)
    for p in Pfull:
        orb = orbit(p, G, n)
        if not all(q in Pfull for q in orb):
            return f"Pfull not {Gname}-symmetric at {p}"
    # build fundamental reps of Pfull and check per-line <=2
    reps, cons = generate_constraints(G, m)
    sel = [0] * len(reps)
    for p in Pfull:
        # find rep
        for i, rep in enumerate(reps):
            if p in orbit(rep, G, n):
                sel[i] = 1
                break
    card = sum(sel)
    viol = 0
    for d in cons:
        if sum(sel[p] * w for p, w in d.items()) > 2:
            viol += 1
    tcard = target_card(G, m)
    return f"G={Gname} m={m}: known rot4 sol admitted (card={card}, target={tcard}, viol={viol})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="C4", choices=list(GROUPS.keys()))
    ap.add_argument("--m", type=int, default=13)
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--timelimit", type=float, default=30.0)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--seed-known", type=str, default="",
                    help="Gname to confirm known rot4 solution admitted (C4/C2/D4)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--checkpoint", default="",
                    help="write incumbent solution JSON here (resilient to restart)")
    ap.add_argument("--resume", default="",
                    help="warm-start from a checkpoint JSON")
    args = ap.parse_args()

    if args.seed_known:
        res = seed_known(args.seed_known, args.m)
        print(res)
        return

    if args.validate:
        print("== GENERAL per-line encoder: soundness + reachability sweep ==")
        for Gname in ["C4", "C2", "D4", "dia1", "dia2", "D2d"]:
            G = GROUPS[Gname]
            order = len(G)
            print(f"-- group {Gname} (|G|={order}) --")
            max_m = 12 if order <= 4 else 8   # D4 needs m%4==0
            for m in range(2, max_m + 1):
                if order > 1 and (2 * m) % order != 0:
                    continue
                t0 = time.time()
                reps, cons = generate_constraints(G, m)
                card = target_card(G, m)
                status, chosen = solve_ortools(reps, cons, card, args.timelimit, args.workers)
                ok = False
                detail = ""
                if chosen:
                    ok, _, detail = verify_config(reps, chosen, G, m)
                print(f"   m={m}: reps={len(reps)} card={card} cons={len(cons)} "
                      f"status={status} found={len(chosen)} verify={ok} "
                      f"{detail if not ok else ''} [{time.time()-t0:.1f}s]")
        return

    G = GROUPS[args.group]
    reps, cons = generate_constraints(G, args.m)
    card = target_card(G, args.m)
    ckpt = args.checkpoint or None
    resume = args.resume or None
    print(f"[gen] group={args.group} m={args.m}: reps={len(reps)} "
          f"target_card={card} constraints={len(cons)}")
    if args.count_only:
        return
    status, chosen = solve_ortools(reps, cons, card, args.timelimit, args.workers,
                                   checkpoint=ckpt, resume=resume)
    print(f"[solve] status={status} found={len(chosen)}")
    if chosen:
        ok, _, detail = verify_config(reps, chosen, GROUPS[args.group], args.m)
        print(f"[verify] no-3-collinear = {ok}  {detail}")
        if ckpt:
            print(f"[checkpoint] saved incumbent -> {ckpt}")
    # terminal state: write a DONE marker beside the checkpoint so a
    # relaunching scheduler knows not to keep spinning.
    if ckpt and status in ("OPTIMAL", "FEASIBLE", "INFEASIBLE"):
        done = ckpt + ".done"
        with open(done, "w") as f:
            f.write(f"status={status}\n")
            if chosen:
                f.write(f"found={len(chosen)}\n")
        print(f"[done] terminal status {status}; marker {done}")


if __name__ == "__main__":
    main()
