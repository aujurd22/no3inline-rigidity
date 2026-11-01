# -*- coding: utf-8 -*-
"""P318: Layer-B certificate stability across m=7,8,9 — the breakthrough-point survey.

Question: do the m=7 certificate TYPES (anti-band pair / main-band pair /
off-diagonal steep pair / fam-involved) persist at m=8, 9?  Stability ⟹ the
parameterized Layer-B lemma program is viable (the route to a general-m proof
of Open Problem 5.1).  Instability with new classes ⟹ the phase-transition
runs deeper.

Method: for each counting-feasible colpat, phase-1 soft-slack LP/IP gives the
dual certificate (which constraints carry infeasibility).  Classify each
certificate's constraint set; tabulate types per m.
判定文本从 verdict JSON 现读。運行解释器: Python313。
"""
import sys, os, json, time
from math import gcd
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t42m_mus5 import build_groups
from t43a_lp_potential import FAMS5
from ortools.sat.python import cp_model

def phase1(m, groups, colpat, h, cap=45):
    model = cp_model.CpModel()
    v = {}
    for x in range(m):
        for y in range(m):
            v[(x, y)] = model.NewBoolVar(f"v{x}_{y}")
    slack = {}
    for kind, key, payload in groups:
        if kind in ("row", "col"):
            model.Add(sum(v[c] for c in payload) == 2)
        elif kind == "line":
            s = model.NewIntVar(0, 4, f"s{len(slack)}")
            model.Add(sum(v[c] for c in payload) <= 2 + s)
            slack[(kind, key)] = s
        elif kind == "cent":
            s = model.NewIntVar(0, 4, f"s{len(slack)}")
            model.Add(sum(v[c] for c in payload) <= 1 + s)
            slack[(kind, key)] = s
        elif kind == "famself":
            s = model.NewIntVar(0, 4, f"s{len(slack)}")
            model.Add(sum(v[c] for c in payload) <= 1 + s)
            slack[(kind, key)] = s
        elif kind == "fam":
            cC, cS = payload
            s = model.NewIntVar(0, 4, f"s{len(slack)}")
            model.Add(sum(v[c] for c in cC) + sum(v[c] for c in cS) <= 2 + s)
            slack[(kind, key)] = s
    for x in range(m):
        upper = [v[(x, y)] for y in range(h, m)]
        if (colpat >> x) & 1:
            model.Add(sum(upper) == 2)
            for y in range(0, h):
                model.Add(v[(x, y)] == 0)
        else:
            model.Add(sum(upper) <= 1)
    model.Minimize(sum(slack.values()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cap
    solver.parameters.num_workers = 1
    st = solver.StatusName(solver.Solve(model))
    if st in ("OPTIMAL", "FEASIBLE"):
        total = int(solver.ObjectiveValue())
        cert = [(k, int(solver.Value(s))) for k, s in slack.items() if solver.Value(s) > 0]
        return total, cert
    return None, None

def classify(cert, m):
    """Classify a certificate into lemma types."""
    kinds = Counter()
    for (kind, key), s in cert:
        if kind == "line":
            dx, dy, c = key
            if (dx, dy) == (1, -1): kinds["anti_band"] += 1
            elif (dx, dy) == (1, 1): kinds["main_band"] += 1
            elif (dx, dy) in ((1, 0), (0, 1)): kinds["rowcol_line"] += 1
            else: kinds["steep_line"] += 1
        elif kind == "fam": kinds["fam_pair"] += 1
        elif kind == "famself": kinds["famself"] += 1
        elif kind == "cent": kinds["cent"] += 1
    return kinds

def main():
    out = {"P": "P318", "date": time.strftime("%Y-%m-%d %H:%M")}
    for m in (7, 8, 9):
        h = (m + 1) // 2
        groups = build_groups(m, FAMS5)
        type_tab = Counter()
        cert_count = 0
        feas = 0
        t0 = time.time()
        for nd in range(0, m // 2 + 1):
            for bits in range(1 << m):
                if bin(bits).count("1") != nd: continue
                total, cert = phase1(m, groups, bits, h)
                if cert is None:
                    print(f"m={m} colpat={bits:0{m}b}: solver-cap", flush=True)
                    continue
                if total == 0:
                    feas += 1
                    print(f"m={m} colpat={bits:0{m}b}: LP-FEASIBLE (residual!)", flush=True)
                    continue
                cert_count += 1
                type_tab.update(classify(cert, m))
        out[f"m={m}"] = {
            "certificated_patterns": cert_count,
            "lp_feasible_residuals": feas,
            "type_table": dict(type_tab),
            "elapsed_s": round(time.time() - t0, 1),
        }
        print(f"m={m}: {cert_count} certificates, types={dict(type_tab)}, residuals={feas} ({out[f'm={m}']['elapsed_s']}s)", flush=True)
        json.dump(out, open("p318_verdicts.json", "w"), ensure_ascii=False, indent=1)
    print("done -> p318_verdicts.json")

if __name__ == "__main__":
    main()
