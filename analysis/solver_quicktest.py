import sys, time
import importlib.util
spec = importlib.util.spec_from_file_location(
    "solver_theory_m37",
    __file__.replace("solver_quicktest.py", "solver_theory_m37.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

mlo = int(sys.argv[1]); mhi = int(sys.argv[2]); tb = float(sys.argv[3]); seed = int(sys.argv[4])
rng = __import__("random").Random(seed)
for m in range(mlo, mhi + 1):
    found = 0; bests = []
    for t in range(3):
        edges = S.generate_2factor(m, rng)
        cells = S.orient(edges, rng)
        res = S.sa_search(m, time_budget=tb, rng=rng, init_edges=edges, init_cells=cells)
        if res["found"]:
            found += 1
        bests.append(res["best"])
        sys.stdout.write(f"  m={m} t={t}: found={res['found']} best={res['best']} cur={res['cur']}\n")
        sys.stdout.flush()
    sys.stdout.write(f"  m={m}: found {found}/3  bests={bests}\n")
    sys.stdout.flush()
