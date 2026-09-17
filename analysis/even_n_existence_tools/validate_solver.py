#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建的求解器验证链 [VALIDATION HARNESS]

背景：另一 agent 审计发现 benders_subproblem.dpll_model 有致命 DPLL bug（unit_prop
把已假字面量当未赋值收集、回溯快照在赋值之后），导致 ~3 万随机 2-因子全部误判
UNSAT、"m=37 强烈疑似不存在" 等结论全部失效。本脚本是第一优先级的「重建验证器」：
用两个**独立成熟** SAT 求解器（z3 + pysat/Glucose4）判定同一批 3-CNF，并与项目内
已验证的 dpll_unsat 交叉一致，证明求解链本身可信。

字面量约定（与 build_full_3cnf 一致，关键点）：
  - 变量：cell i 的两种取向 bit a∈{0,1} 对应底层变量 y[2i+a]（0..2*ncells-1）。
  - build_full_3cnf 输出的子句字面量是「已取反」的：存储字面量 L=(2p+a)^1 表示
    `¬(x_p=a)`，即 z3/pysat 中的 `¬y[L^1]`。且每个 cell 必须**恰有一**个 bit 为真
    （y[2i] XOR y[2i+1]）。dpll_unsat 通过 unit_prop 的 `assign[L]=1; assign[L^1]=0`
    与分支赋值**内部强制**此不变式；z3/pysat 必须显式加入此不变式，否则会解出更弱的
    （允许两 bit 同真/同假）公式 —— 这正是初版误报 SAT 的根因。

测试电池（用户指定）：
  (A) 单测：平凡 SAT / UNSAT，验证字面量语义+恰有一不变式。
  (B) 6 个 V20 负例（m=37，N=74）→ 必须 UNSAT（关键回归：曾被误判）。
  (C) 正例 m=5/10/14/36（真实 rot4-NTIL 解，各用 N=2m）→ 必须 SAT，且通用几何
      oracle（c4_lifts 重建点集查无三点共线）复核 bad_triples==0。

所有结论标 [COMPUTATIONAL CERTIFICATE]，不当定理。
"""
from __future__ import annotations

import json
import sys
import time
import itertools
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent                       # no3inline-rigidity/analysis
ROOT = HERE.parent.parent.parent             # 2026-07-03-16-29-36
EXT = Path(r"C:/Users/djr82/Documents/Codex/2026-07-13/d-djr82-documents-workbuddy-2026-07-2/work/ising_m37/outputs")

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ANALYSIS))

# 仅用于第三方独立求解器（z3/pysat）与几何基元；dpll_unsat 为项目已验证手写求解器。
from exact_rot4_3sat import dpll_unsat
from prepare_v20_basin_archive import directed_cells
import rot4_loader

import z3
from pysat.solvers import Glucose4


# ─────────────────── N 参数化 3-CNF 构造（与 reaudit_k14 同逻辑，N 可配） ───────────────────
def c4_lifts_n(cell, N):
    x, y = cell
    out = []
    for _ in range(4):
        out.append((x, y))
        x, y = N - 1 - y, x
    return tuple(out)


def collinear(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) == (c[0] - a[0]) * (b[1] - a[1])


def combo_bad_n(P, cells_bits):
    n = len(cells_bits)
    if n == 3:
        (i, bi), (j, bj), (k, bk) = cells_bits
        A, B, C = P[(i, bi)], P[(j, bj)], P[(k, bk)]
        for a in A:
            for b in B:
                for c in C:
                    if collinear(a, b, c):
                        return True
        return False
    if n == 2:
        (i, bi), (j, bj) = cells_bits
        A, B = P[(i, bi)], P[(j, bj)]
        for a1, a2 in itertools.combinations(A, 2):
            for b in B:
                if collinear(a1, a2, b):
                    return True
        for b1, b2 in itertools.combinations(B, 2):
            for a in A:
                if collinear(a, b1, b2):
                    return True
        return False
    (i, bi) = cells_bits[0]
    A = P[(i, bi)]
    for a1, a2, a3 in itertools.combinations(A, 3):
        if collinear(a1, a2, a3):
            return True
    return False


def make_cnf(edges, N):
    """复制 build_full_3cnf 逻辑，N 可配（负例 N=74；正例 N=2m）。"""
    n = len(edges)
    P = {}
    for i, (u, v) in enumerate(edges):
        for b in (0, 1):
            cell = directed_cells([(u, v)], [b])[0]
            P[(i, b)] = c4_lifts_n(cell, N)
    clauses = []
    for p in range(n):
        for q in range(p + 1, n):
            for k in range(n):
                if k == p or k == q:
                    continue
                for a in (0, 1):
                    for b in (0, 1):
                        for c in (0, 1):
                            if combo_bad_n(P, [(p, a), (q, b), (k, c)]):
                                clauses.append([(2 * p + a) ^ 1,
                                                (2 * q + b) ^ 1,
                                                (2 * k + c) ^ 1])
    return clauses, n


# ───────────────────────── 成熟求解器封装 ─────────────────────────
def solve_z3(clauses, ncells):
    """z3 判定。返回 True=UNSAT / False=SAT / None=未知。"""
    nv = 2 * ncells
    y = [z3.Bool(f"y{idx}") for idx in range(nv)]
    s = z3.Solver()
    s.set("timeout", 120_000)
    # 恰有一不变式：y[2i] XOR y[2i+1]
    for i in range(ncells):
        s.add(z3.Or(y[2 * i], y[2 * i + 1]))
        s.add(z3.Or(z3.Not(y[2 * i]), z3.Not(y[2 * i + 1])))
    # 子句字面量 L 表示 ¬y[L^1]
    for cl in clauses:
        s.add(z3.Or(*[z3.Not(y[lit ^ 1]) for lit in cl]))
    r = s.check()
    if r == z3.sat:
        return False
    if r == z3.unsat:
        return True
    return None


def solve_pysat(clauses, ncells):
    """pysat/Glucose4 判定（独立代码库）。返回 True=UNSAT / False=SAT / None=未知。"""
    nv = 2 * ncells
    with Glucose4() as s:
        for i in range(ncells):
            s.add_clause([2 * i + 1, 2 * i + 2])          # y[2i] ∨ y[2i+1]
            s.add_clause([-(2 * i + 1), -(2 * i + 2)])    # ¬y[2i] ∨ ¬y[2i+1]
        for cl in clauses:
            # 子句字面量 L ⇒ ¬y[L^1] ⇒ pysat 负字面量 -( (L^1)+1 )
            s.add_clause([-( (lit ^ 1) + 1) for lit in cl])
        sat = s.solve()
        if sat is None:
            return None
        return not sat


def solve_dpll(clauses, ncells, node_budget=80_000_000):
    """项目内已验证手写求解器（内部强制恰有一不变式）。"""
    status, _ = dpll_unsat(clauses, ncells, node_budget=node_budget)
    return status


# ───────────────────────── 通用几何 oracle ─────────────────────────
def verify_ntil(edges, bits, N):
    """用 c4_lifts 重建 2N 点集，查无三点共线。返回 (ok, n_points, bad_triples)。"""
    import itertools
    pts = set()
    for (u, v), b in zip(edges, bits):
        cell = directed_cells([(u, v)], [b])[0]
        for p in c4_lifts_n(cell, N):
            pts.add(p)
    if len(pts) != 2 * N:
        return False, len(pts), None
    pl = list(pts)
    bad = 0
    for i in range(len(pl)):
        for j in range(i + 1, len(pl)):
            for k in range(j + 1, len(pl)):
                if collinear(pl[i], pl[j], pl[k]):
                    bad += 1
    return (bad == 0), len(pts), bad


# ───────────────────────── 正例构造 ─────────────────────────
def cycle_orient_to_edges_bits(cycle, orient, m):
    edges = [(int(cycle[k]), int(cycle[(k + 1) % m])) for k in range(m)]
    bits = [1 if orient[k] else 0 for k in range(m)]
    return edges, bits


def points_to_edges_bits(points, n):
    N = n
    pts = set((int(x), int(y)) for (x, y) in points)
    seen = set()
    edges = []
    for p in pts:
        if p in seen:
            continue
        orbit = []
        cur = p
        while cur not in seen:
            seen.add(cur)
            orbit.append(cur)
            x, y = cur
            cur = (N - 1 - y, x)
        edges.append(min(orbit))
    edges.sort()
    return edges, [0] * len(edges)


def load_positive(m):
    if m == 5:
        d = json.loads((EXT / "balanced_cpsat_m5_m6.json").read_text())
        run = d["runs"][0]
        return run["edges"], run["bits"], "balanced_cpsat_m5_m6.run0"
    if m == 36:
        d = json.loads((ROOT / "analysis" / "n72_new_sol_1.json").read_text())
        return cycle_orient_to_edges_bits(d["cycle"], d["orientation"], 36) + ("n72_new_sol_1.json",)
    sols, _ = rot4_loader.load_rot4(m * 2)
    pts = sols[0]
    edges, bits = points_to_edges_bits(pts, m * 2)
    return edges, bits, f"rot4_loader.load_rot4(n={m*2})"


def load_negatives():
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    return [(b["id"], [tuple(e) for e in b["edges"]]) for b in arch["archive"]]


# ───────────────────────── 主流程 ─────────────────────────
def main():
    results = {"unit": [], "negatives": [], "positives": [], "summary": {}}
    print("=" * 70)
    print("重建验证链：z3 + pysat/Glucose4 交叉 dpll_unsat（字面量已正确取反+恰有一）")
    print("=" * 70)

    # ---- (A) 单测 ----
    print("\n## (A) 单测")
    unit_cases = [
        ("空子句→SAT", [], 1, False),
        ("x0=0∧x0=1→UNSAT", [[0], [1]], 1, True),
        ("(x0∨x1)∧(¬x0∨¬x1)→SAT", [[0, 2], [1, 3]], 2, False),
        ("三变量单子句→SAT", [[0, 2, 4]], 3, False),
    ]
    for name, clauses, ncells, expect in unit_cases:
        z3r = solve_z3(clauses, ncells)
        pr = solve_pysat(clauses, ncells)
        dr = solve_dpll(clauses, ncells)
        ok = (z3r == expect) and (pr == expect) and (dr == expect)
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: z3={z3r} pysat={pr} dpll={dr} (期望={expect})")
        results["unit"].append({"name": name, "z3": z3r, "pysat": pr,
                                "dpll": dr, "expect": expect, "ok": ok})

    # ---- (B) 6 V20 负例 → 必须 UNSAT（N=74） ----
    print("\n## (B) 6 V20 负例 (m=37, N=74) → 期望 UNSAT")
    for bid, edges in load_negatives():
        t0 = time.time()
        clauses, ncells = make_cnf(edges, N=74)
        z3r = solve_z3(clauses, ncells)
        pr = solve_pysat(clauses, ncells)
        dr = solve_dpll(clauses, ncells)
        dt = time.time() - t0
        ok = (z3r is True) and (pr is True) and (dr is True)
        print(f"  [{'OK' if ok else 'FAIL'}] {bid}: cells={ncells} clauses={len(clauses)} "
              f"z3={z3r} pysat={pr} dpll={dr} ({dt:.1f}s)")
        results["negatives"].append({"id": bid, "ncells": ncells,
                                     "n_clauses": len(clauses), "z3": z3r,
                                     "pysat": pr, "dpll": dr, "ok": ok})

    # ---- (C) 正例 m=5/10/14/36 → 必须 SAT + 几何复核 ----
    print("\n## (C) 正例 m=5/10/14/36 → 期望 SAT + bad_triples==0")
    for m in (5, 10, 14, 36):
        try:
            edges, bits, src = load_positive(m)
        except Exception as e:
            print(f"  [SKIP] m={m}: 加载失败 {e!r}")
            results["positives"].append({"m": m, "ok": False, "error": repr(e)})
            continue
        N = m * 2
        t0 = time.time()
        clauses, ncells = make_cnf(edges, N=N)
        z3r = solve_z3(clauses, ncells)
        pr = solve_pysat(clauses, ncells)
        dr = solve_dpll(clauses, ncells)
        dt = time.time() - t0
        ok_geo, npts, bt = verify_ntil(edges, bits, N)
        sat_ok = (z3r is False) and (pr is False) and (dr is False)
        geo_ok = (bt == 0)
        ok = sat_ok and geo_ok
        print(f"  [{'OK' if ok else 'FAIL'}] m={m}: cells={ncells} clauses={len(clauses)} "
              f"z3={z3r} pysat={pr} dpll={dr} npts={npts} bad_triples={bt} "
              f"src={src} ({dt:.1f}s)")
        results["positives"].append({"m": m, "ncells": ncells,
                                     "n_clauses": len(clauses), "z3": z3r,
                                     "pysat": pr, "dpll": dr, "n_points": npts,
                                     "bad_triples": bt, "source": src, "ok": ok})

    # ---- 汇总 ----
    u_ok = all(r["ok"] for r in results["unit"])
    n_ok = all(r["ok"] for r in results["negatives"])
    p_ok = all(r["ok"] for r in results["positives"])
    all_ok = u_ok and n_ok and p_ok
    results["summary"] = {
        "unit_ok": u_ok, "negatives_ok": n_ok, "positives_ok": p_ok,
        "all_ok": all_ok,
        "verdict": "SOLVER_CHAIN_TRUSTWORTHY" if all_ok else "SOLVER_CHAIN_FAIL",
    }
    print("\n" + "=" * 70)
    print(f"汇总: 单测={u_ok} 负例={n_ok} 正例={p_ok} → {results['summary']['verdict']}")
    print("=" * 70)

    (HERE / "validate_solver_report.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(HERE / "validate_solver_report.md", "w", encoding="utf-8") as f:
        f.write("# 求解器验证链报告 [COMPUTATIONAL CERTIFICATE]\n\n")
        f.write(f"- 结论：**{results['summary']['verdict']}**\n")
        f.write(f"- 单测全过：{u_ok}；6 V20 负例全 UNSAT：{n_ok}；"
                f"正例 m=5/10/14/36 全 SAT+几何复核：{p_ok}\n\n")
        f.write("## 负例 (m=37, N=74, 关键回归)\n")
        for r in results["negatives"]:
            f.write(f"- {r['id']}: z3={r['z3']} pysat={r['pysat']} "
                    f"dpll={r['dpll']} ({r['n_clauses']} 子句) "
                    f"{'OK' if r['ok'] else 'FAIL'}\n")
        f.write("\n## 正例\n")
        for r in results["positives"]:
            f.write(f"- m={r.get('m')}: z3={r.get('z3')} pysat={r.get('pysat')} "
                    f"dpll={r.get('dpll')} npts={r.get('n_points')} "
                    f"bad_triples={r.get('bad_triples')} src={r.get('source')} "
                    f"{'OK' if r['ok'] else 'FAIL'}\n")
    print("写入 validate_solver_report.json / .md")


if __name__ == "__main__":
    main()
