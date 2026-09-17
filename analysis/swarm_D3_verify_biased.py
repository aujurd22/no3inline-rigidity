import sys, json
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("st", "solver_theory_m37.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

rep = json.load(open("results/biased_nibble.json"))
m = 37
from collections import defaultdict

def brute(lifts):
    lp = defaultdict(set)
    N = len(lifts)
    for a in range(N):
        for b in range(a + 1, N):
            if lifts[a] == lifts[b]:
                continue
            lp[st.line_of(lifts[a], lifts[b])].add(a)
            lp[st.line_of(lifts[a], lifts[b])].add(b)
    return sum(len(S) * (len(S) - 1) * (len(S) - 2) // 6 for S in lp.values())

for key in ["m37_unbiased", "m37_biased"]:
    cfg = rep[key]["best_config"]
    cells = [(i, cfg[i]) for i in range(m)]
    edges = []
    deg = [0] * m
    bad2cycle = False
    seen = set()
    for (x, y) in cells:
        if x != y:
            e = (min(x, y), max(x, y))
            if e in seen:
                bad2cycle = True
            seen.add(e)
        edges.append((x, y))
        deg[x] += 1
        deg[y] += 1
    tworeg = all(d == 2 for d in deg)
    b = st.Board(m)
    b.build(edges, cells)
    incr = b.total_bad
    vt = b.verify_total()
    br = brute(b.lifts)
    ok = (tworeg and not bad2cycle and vt == 0 and br == 0)
    print(f"{key}: 2regular={tworeg} 2cycle={bad2cycle} "
          f"incr_total_bad={incr} verify_total={vt} brute={br} "
          f"-> {'VALID SOLUTION' if ok else 'NOT VALID'}")
