#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parity_lift_lazy.py — lazy cutting-loop solver (persistent cut library, resumable)
Idea: relaxation M_t = C1 (pair encoding) + C2 (eager) + accumulated C3 cuts.
  INFEASIBLE proves no-lift (relaxation is sound); a SAT candidate passing all C3 checks is a solution; otherwise add cuts and continue.
Usage: python parity_lift_lazy.py <k> <total seconds> <per-round seconds> [--fresh]
"""
import sys, json, time, itertools, os
from collections import Counter

CUTDIR = r"D:\djr82\Documents\workbuddy\night_research_20260904\outputs\T6_parity_lift"


def build_base(k, violated, hint=None, eager_c2=True):
    from ortools.sat.python import cp_model
    import itertools as it
    n = 2 * k
    m = cp_model.CpModel()
    f0 = [m.new_int_var(0, k - 1, f"f0_{r}") for r in range(n)]
    f1 = [m.new_int_var(0, k - 1, f"f1_{r}") for r in range(n)]
    if hint:
        for r, v in enumerate(hint[0]):
            if r < n: m.add_hint(f0[r], v)
        for r, v in enumerate(hint[1]):
            if r < n: m.add_hint(f1[r], v)
    rows = list(range(n))
    all_pairs = list(it.combinations(rows, 2))
    for f in (f0, f1):
        tag = f[0].name[:2]
        pair = {p: m.new_bool_var(f"p{tag}{p[0]}_{p[1]}") for p in all_pairs}
        for r in rows:
            m.add(sum(pair[p] for p in all_pairs if r in p) == 1)
        val = {}
        for p in all_pairs:
            for q in range(k):
                val[(p, q)] = m.new_bool_var(f"v{tag}{p[0]}_{p[1]}_{q}")
        for p in all_pairs:
            m.add(sum(val[(p, q)] for q in range(k)) == 1).only_enforce_if(pair[p])
            for q in range(k):
                m.add(val[(p, q)] == 0).only_enforce_if(pair[p].Not())
        for p in all_pairs:
            for q in range(k):
                vv = val[(p, q)]
                m.add(f[p[0]] == q).only_enforce_if(vv)
                m.add(f[p[1]] == q).only_enforce_if(vv)
        if eager_c2:
            for a, b, c in it.combinations(range(n), 3):
                det = ((b - a) * (f[c] - f[a]) - (c - a) * (f[b] - f[a]))
                s = m.new_bool_var(f"c2_{tag}_{a}_{b}_{c}")
                m.add(det <= -1).only_enforce_if(s.Not())
                m.add(det >= 1).only_enforce_if(s)
    for key, cut in enumerate(violated):
        if len(cut) == 4:
            cut = ['C3'] + list(cut)
        kind, eps, i, j, c = cut[0], cut[1], cut[2], cut[3], cut[4]
        f, g = (f0, f1) if eps == 0 else (f1, f0)
        if kind == 'C3':
            sign = (-(j - i)) if eps == 0 else (j - i)
            lin = 2 * ((j - i) * g[c] - (j - i) * f[i] - (c - i) * f[j] + (c - i) * f[i])
            s = m.new_bool_var(f"c3cut_{key}")
            m.add(lin - sign <= -1).only_enforce_if(s.Not())
            m.add(lin - sign >= 1).only_enforce_if(s)
        else:  # C2: forbid coarse same-orbit collinearity det=0 (det is linear in f)
            lin = (j - i) * f[c] - (j - i) * f[i] - (c - i) * f[j] + (c - i) * f[i]
            s = m.new_bool_var(f"c2cut_{key}")
            m.add(lin <= -1).only_enforce_if(s.Not())
            m.add(lin >= 1).only_enforce_if(s)
    return m, f0, f1


def all_violations(k, f0v, f1v, cap=80):
    """fully lazy mode: returns (kind, eps, i, j, c) — kind='C2' coarse collinear / 'C3' mixed"""
    n = 2 * k
    out = []
    for eps in (0, 1):
        f, g = (f0v, f1v) if eps == 0 else (f1v, f0v)
        for i, j, c in itertools.combinations(range(n), 3):
            D = (j - i) * (g[c] - f[i]) - (c - i) * (f[j] - f[i])
            if D == 0:  # C2: coarse orbit collinear (each eps checks its own f)
                out.append(['C2', eps, i, j, c])
                if len(out) >= cap: return out
    for eps in (0, 1):
        f, g = (f0v, f1v) if eps == 0 else (f1v, f0v)
        for i, j in itertools.combinations(range(n), 2):
            if (j - i) % 2 != 0: continue
            target = (-(j - i)) if eps == 0 else (j - i)
            for c in range(n):
                if c in (i, j): continue
                D = (j - i) * (g[c] - f[i]) - (c - i) * (f[j] - f[i])
                if 2 * D == target:
                    out.append(['C3', eps, i, j, c])
                    if len(out) >= cap: return out
    return out

def c3_violations(k, f0v, f1v, cap=60):
    n = 2 * k
    out = []
    for eps in (0, 1):
        f, g = (f0v, f1v) if eps == 0 else (f1v, f0v)
        for i, j in itertools.combinations(range(n), 2):
            if (j - i) % 2 != 0:
                continue
            target = (-(j - i)) if eps == 0 else (j - i)
            for c in range(n):
                if c in (i, j):
                    continue
                D = (j - i) * (g[c] - f[i]) - (c - i) * (f[j] - f[i])
                if 2 * D == target:
                    out.append([eps, i, j, c])
                    if len(out) >= cap:
                        return out
    return out


def run(k, total_limit, round_limit, init, eager_c2=True, hint=None):
    t0 = time.time()
    violated = [list(x) for x in init]
    history = []
    rnd = 0
    from ortools.sat.python import cp_model
    cutfile = os.path.join(CUTDIR, f"lazy_n{2*k}_cuts.json")
    while time.time() - t0 < total_limit:
        rnd += 1
        remain = total_limit - (time.time() - t0)
        m, f0, f1 = build_base(k, violated, hint=hint_holder[0], eager_c2=eager_c2)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(round_limit, remain)
        solver.parameters.num_search_workers = 4
        st = solver.solve(m)
        el = round(time.time() - t0, 1)
        if st == cp_model.INFEASIBLE:
            return {"k": k, "n": 2 * k, "verdict": "NO_ALL1_LIFT (relaxation INFEASIBLE; sound no-lift proof)",
                    "rounds": rnd, "cuts": len(violated), "total_elapsed": el, "history": history}
        if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            g0 = [solver.value(v) for v in f0]
            g1 = [solver.value(v) for v in f1]
            viols = all_violations(k, g0, g1) if not eager_c2 else [(["C3"] + v) for v in c3_violations(k, g0, g1)]
            history.append({"round": rnd, "status": "SAT", "new_violations": len(viols), "elapsed": el})
            if not viols:
                pts = [(r, 2 * g0[r]) for r in range(2 * k)] + [(r, 2 * g1[r] + 1) for r in range(2 * k)]
                bad = 0
                for i in range(len(pts)):
                    for j in range(i + 1, len(pts)):
                        for l in range(j + 1, len(pts)):
                            (x1, y1), (x2, y2), (x3, y3) = pts[i], pts[j], pts[l]
                            if (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) == 0:
                                bad += 1
                return {"k": k, "n": 2 * k, "verdict": f"SOLUTION (board bad-triples={bad})",
                        "f0": g0, "f1": g1, "rounds": rnd, "total_elapsed": el, "history": history}
            violated.extend(viols)
        else:
            history.append({"round": rnd, "status": "UNKNOWN", "cuts": len(violated), "elapsed": el})
            out = {"k": k, "n": 2 * k, "verdict": "UNKNOWN (round timeout)", "rounds": rnd,
                   "cuts": len(violated), "total_elapsed": el, "history": history}
            json.dump(violated, open(cutfile, 'w'))
            return out
        json.dump(violated, open(cutfile, 'w'))
    return {"k": k, "n": 2 * k, "verdict": "TIMEOUT", "rounds": rnd, "cuts": len(violated),
            "total_elapsed": round(time.time() - t0, 1), "history": history}


if __name__ == '__main__':
    k = int(sys.argv[1]); total = float(sys.argv[2]); rnd = float(sys.argv[3])
    fresh = '--fresh' in sys.argv
    cutfile = os.path.join(CUTDIR, f"lazy_n{2*k}_cuts.json")
    init = []
    if os.path.exists(cutfile) and not fresh:
        init = json.load(open(cutfile))
        print(f"loaded cut library: {len(init)} cuts")
    hint = None
    if '--hint30' in sys.argv:
        w = json.load(open(os.path.join(CUTDIR, 'witness_n30_all1.json')))
        hint = (w['f0'], w['f1'])
        print("hint: n=30 witness loaded")
    hint_holder = [hint]
    eager = '--fullylazy' not in sys.argv
    res = run(k, total, rnd, init, eager_c2=eager, hint=hint)
    slim = {kk: vv for kk, vv in res.items() if kk not in ('f0', 'f1')}
    print(json.dumps(slim, indent=1, ensure_ascii=False))
    out = os.path.join(CUTDIR, f"lazy_n{2*k}.json")
    json.dump(res, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if res['verdict'].startswith('SOLUTION'):
        pf = os.path.join(CUTDIR, f"SOLUTION_n{2*k}.json")
        json.dump({'f0': res['f0'], 'f1': res['f1']}, open(pf, 'w'), indent=1)
        print("points saved:", pf)
    print("saved:", out)
