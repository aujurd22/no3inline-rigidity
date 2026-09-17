"""
solve_perm.py -- R9c: 置换(permutation)子类的 rot4-NTIL 启发式求解器.

⚠️ 重要更正 (见 results/theorem_r9c_perm_equiv.md 定理 2):
    2-因子约束 rowSum[i]+colSum[i]==2 的解集 **真包含** 置换模型
    (rowSum=colSum=1). 置换模型是其**严格子集**, 可能漏掉真实的非置换
    2-因子解 (m=8/12/18 的实际解均非置换, 已实证). 故本脚本:
      - 可作为**启发式**: 找到置换型解即合法构造;
      - **不可**用于存在性否定 (UNKNOWN/UNSAT 不可信).
    完整且正确的攻击见 solve_m37_r9b.py (保留 2-因子 out+in=2 约束).

用法:
  python solve_perm.py --m 20 --timelimit 120 --workers 8
  python solve_perm.py --sweep 20 30 --per-m 150 --workers 8
"""
import sys, os, json, time, math, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solve_m37_r9b import generate_constraints, verify_cells, _write_ckpt
HAVE_OR = True
try:
    from ortools.sat.python import cp_model
except Exception:
    HAVE_OR = False


def build_model(m):
    n = 2 * m
    reps, line_cons, _ = generate_constraints(m, use_2factor=False)
    model = cp_model.CpModel()
    x = [[model.NewBoolVar(f"x{i}_{j}") for j in range(m)] for i in range(m)]
    for i in range(m):
        model.Add(sum(x[i]) == 1)            # 每行恰一个 cell
        model.Add(sum(x[r][i] for r in range(m)) == 1)  # 每列恰一个 cell
    t = time.time()
    for idx, d in enumerate(line_cons):
        terms = [w * x[reps[k][0]][reps[k][1]] for k, w in d.items()]
        model.Add(sum(terms) <= 2)
    build = time.time() - t
    return model, x, reps, line_cons, build


def solve_perm(m, timelimit, workers=8, ckpt=None, resume=None, verbose=False):
    model, x, reps, line_cons, build = build_model(m)
    if resume and os.path.exists(resume):
        try:
            with open(resume) as f:
                data = json.load(f)
            for (i, j) in data.get("cells", []):
                if 0 <= i < m and 0 <= j < m:
                    model.AddHint(x[i][j], 1)
        except Exception:
            pass
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timelimit
    solver.parameters.max_presolve_iterations = 3
    solver.parameters.num_search_workers = workers
    if verbose:
        solver.parameters.log_search_progress = True
    print(f"[solve] m={m}: line_cons={len(line_cons)} perm-build={build:.1f}s "
          f"tl={timelimit}s workers={workers}", flush=True)
    t0 = time.time()
    st = solver.Solve(model)
    status = solver.StatusName(st)
    cells = []
    if status in ("FEASIBLE", "OPTIMAL"):
        for i in range(m):
            for j in range(m):
                if solver.Value(x[i][j]) == 1:
                    cells.append((i, j))
    ts = time.time() - t0
    print(f"[solve] m={m}: status={status} found={len(cells)} t={ts:.1f}s", flush=True)
    if cells:
        vf, nc = verify_cells(cells, m)
        print(f"[verify] m={m}: no3collinear={vf} pts={4*len(cells)}", flush=True)
        if ckpt:
            _write_ckpt(ckpt, cells)
            with open(ckpt + ".done", "w") as f:
                f.write(f"status={status}\nfound={len(cells)}\n")
    return status, cells, ts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=20)
    ap.add_argument("--timelimit", type=float, default=120.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--checkpoint", default="")
    ap.add_argument("--resume", default="")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--sweep", nargs=2, type=int, metavar=("A", "B"))
    ap.add_argument("--per-m", type=float, default=150.0)
    args = ap.parse_args()

    if args.sweep:
        a, b = args.sweep
        log = open("results/perm_sweep.csv", "w")
        log.write("m,n,line_cons,build_s,solve_s,status,found,ts\n")
        for m in range(a, b + 1):
            ck = f"results/perm_m{m}.json"
            status, cells, ts = solve_perm(m, args.per_m, args.workers,
                                           ckpt=ck, resume=ck)
            log.write(f"{m},{2*m},{len(generate_constraints(m,False)[1])},"
                      f"0,{ts:.1f},{status},{len(cells)},{time.strftime('%H:%M:%S')}\n")
            log.flush()
            if status in ("OPTIMAL", "FEASIBLE"):
                print(f"  >> m={m} SOLVED", flush=True)
        log.close()
        return

    solve_perm(args.m, args.timelimit, args.workers,
               ckpt=args.checkpoint or None, resume=args.resume or None,
               verbose=args.verbose)


if __name__ == "__main__":
    main()
