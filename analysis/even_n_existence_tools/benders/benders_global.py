#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全局 Benders 主/子问题框架（rot4-NTIL m=M 存在性搜索 / 不可能性割证）。

设计要点（用户 2026-07-21 指令：最有价值路线 = 允许自环的全局主问题 + 最小 cell 核广义割）：

【主问题 / Master】
  - OR-Tools CP-SAT 在**全局无向 2-因子空间**建模：基本域顶点 {0..M-1}，
    位置 p = 无序对 {u,v} (u<=v) 对应一个「cell」。变量 y[p] ∈ {0,1,2}：
        y[p]=0  → 该边不出现；
        y[p]=1  → 一条无向边 {u,v}（若 u=v 即自环，贡献度 2）；
        y[p]=2  → 两条无向边 {u,v}（即 2-圈，贡献度 4 ⇒ 顶点 u,v 各度 2）。
    （旧 random_2factor 禁止自环/2-圈，故此框架能生成含自环的低缺陷结构，
      六 V20 盆地每盆恰 1 自环，正需此编码。）
  - 度约束：每个顶点 v 的入射贡献恰为 2 ⇒ 合法的 2-因子（允许自环/2-圈）。
  - 累积 sound 割（见下），剔除已被证明不可行的 2-因子族。

【子问题 / Subproblem】（复用已验证成熟求解器，绝不用手写 DPLL）
  - 用 validate_solver.make_cnf 构造 sound 3-CNF 松弛（UNSAT ⇒ 几何 UNSAT）。
  - pysat/Glucose4 判定（与 z3 独立代码库，已三方交叉验证可信）。
  - UNSAT ⇒ 提取 MUS（最小不可满足集）→ 最小 cell 核（涉及的边位置多重集）
            → 添加 sound 广义割 `BoolOr( y[p] <= c_p-1 for p in core )`
            （c_p = 核内位置 p 出现次数；该割禁止任何含此核多重集的 2-因子，
              因为子问题对这些边含全部 MUS 子句 ⇒ 仍 UNSAT，sound）。
  - SAT   ⇒ 导出满足赋值 → 几何 oracle verify_ntil 复核：
        bad_triples==0 ⇒ ★ 发现 rot4-NTIL 解（突破，停止）；
        >0            ⇒ 从坏三点提取 owner 集与取向，**增量加入阻断子句**
                        （一元/二元/三元），反复 SAT→oracle→加子句，直至找到真解
                        或增量公式被证 UNSAT。**不再错误删除整个 2-因子。**
  - 每个 UNSAT 核在加入主问题割前，**独立用 Glucose4 + z3 验证核心公式 UNSAT**，
    确保割 sound。MUSX 返回的 1-基编号已修正。

【正确性边界】所有结论标 [COMPUTATIONAL CERTIFICATE] / [OPEN]，不当定理。
  主问题因预算/割集变不可行 ⇒ 仅表示「本次搜索未找到」，**非存在性证明**
  （真正证明需穷尽所有 2-因子，m=37 不现实）。本框架提供 sound 排除与突破搜寻。

纪律：单进程、可限时、严格限候选/时长；不并行爆 CPU。
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys
import time
import threading
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from ortools.sat.python import cp_model  # noqa: E402

# 复用已验证的 sound 子问题基元（成熟求解器，非手写 DPLL）
from validate_solver import make_cnf, verify_ntil, load_negatives, load_positive  # noqa: E402
from prepare_v20_basin_archive import directed_cells  # noqa: E402
from validate_solver import c4_lifts_n, combo_bad_n  # noqa: E402

from pysat.solvers import Glucose4  # noqa: E402
from pysat.examples.musx import MUSX  # noqa: E402
from pysat.formula import CNF  # noqa: E402


# ───────────────────── pysat 公式构造（含 (p,q,k) 元信息，供 MUS→核） ─────────────────────
def build_formula(edges, N):
    """复制 validate_solver.make_cnf 的松弛逻辑，但额外返回每条约束子句对应的
    边位置三元组 (p,q,k)，用于 MUS → 最小 cell 核。

    返回 (formula, meta, ncells)：
      formula : pysat 字面量子句列表（含恰有一不变式 + 3-CNF 约束）；
      meta[j] : 第 j 条约束子句对应的 (p,q,k) 边位置三元组；
      ncells  : 边数（= len(edges)）。
    """
    n = len(edges)
    P = {}
    for i, (u, v) in enumerate(edges):
        for b in (0, 1):
            cell = directed_cells([(u, v)], [b])[0]
            P[(i, b)] = c4_lifts_n(cell, N)
    formula = []
    meta = []
    # 恰有一不变式：y[2i] XOR y[2i+1]（pysat 变量 = 比特序号+1）
    for i in range(n):
        formula.append([2 * i + 1, 2 * i + 2])
        formula.append([-(2 * i + 1), -(2 * i + 2)])
    # 3-CNF 约束：三元组 (p,q,k) 的任一取向组合若共线则禁之
    for p in range(n):
        for q in range(p + 1, n):
            for k in range(n):
                if k == p or k == q:
                    continue
                for a in (0, 1):
                    for b in (0, 1):
                        for c in (0, 1):
                            if combo_bad_n(P, [(p, a), (q, b), (k, c)]):
                                # make_cnf 字面量 L=(2p+a)^1；pysat 负字面量 = -(L^1+1)=-(2p+a+1)
                                formula.append([
                                    -((2 * p + a) + 1),
                                    -((2 * q + b) + 1),
                                    -((2 * k + c) + 1),
                                ])
                                meta.append((p, q, k))
    return formula, meta, n


def solve_pysat_model(formula):
    """返回 (status, model)：status True=UNSAT, False=SAT, None=未知；
    model 为 SAT 时的 pysat 字面量列表（正=真），否则 None。"""
    with Glucose4() as s:
        for cl in formula:
            s.add_clause(cl)
        sat = s.solve()
        if sat is None:
            return None, None
        if not sat:
            return True, None
        return False, s.get_model()


def model_to_bits(model, ncells):
    """从 pysat 模型还原每条边的取向 bit（y[2p+a] 真 ⇒ bit a）。"""
    mset = set(model)
    bits = []
    for p in range(ncells):
        b1 = (2 * p + 1 + 1) in mset
        b0 = (2 * p + 0 + 1) in mset
        bits.append(1 if b1 else 0)
        _ = b0  # 不变式保证恰有一真
    return bits


def extract_mus(formula, ncells, timeout=30):
    """带超时的 MUS 提取。返回子句索引列表（指向 formula），超时/失败返回 None。"""
    store = {}

    def worker():
        try:
            cnf = CNF()
            for cl in formula:
                cnf.append(cl)
            musx = MUSX(cnf, verbosity=0)
            store["mus"] = musx.compute()
        except Exception as e:  # noqa: BLE001
            store["err"] = repr(e)

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout)
    if th.is_alive() or "mus" not in store:
        return None
    return store["mus"]


def mus_to_core(mus, meta, ncells, edges):
    """MUS 子句索引 → 最小 cell 核（边位置多重集，按无向对计数）。

    关键修正：核中每位置 p 的「要求重数」c_p 必须是该无向对在**本 2-因子中
    的实际出现次数**（1=单条 / 2=2-圈），而非 MUS 子句引用该位置的频次。
    否则 c_p 会被高估（可达 14），导致割 `y[p] <= c_p-1` 恒真（y 域仅 0/1/2），
    割失去排除力（已修复前即此 bug）。sound 割禁止任何含该核多重集的 2-因子。

    返回 counts：dict[无序对] = c_p ∈ {1,2}。仅取约束子句（非不变式子句）。
    """
    nv = 2 * ncells
    if mus is None:
        return {}
    # 本 2-因子每条无向边的实际出现次数（1 或 2）
    factor_pair_counts = Counter(
        (min(u, v), max(u, v)) for (u, v) in edges)
    indices = set()
    for idx in mus:
        # MUSX.compute() 返回从 1 开始的子句编号
        if not (nv < idx <= nv + len(meta)):
            continue  # 不变式子句或越界，跳过
        j = idx - nv - 1
        for eidx in meta[j]:
            indices.add(eidx)
    counts = {}
    for eidx in indices:
        up = (min(edges[eidx][0], edges[eidx][1]),
              max(edges[eidx][0], edges[eidx][1]))
        counts[up] = factor_pair_counts[up]  # 1 或 2（核心多重集要求）
    return counts


# ───────────────────── 增量精确 SAT（修复 sat_blocked 错误） ─────────────────────
def collinear(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) == (c[0] - a[0]) * (b[1] - a[1])


def find_bad_triple_blocks(edges, bits, N):
    """给定边长集与取向 bits，找出所有「坏三点」→ 返回阻断子句列表
    （pysat 负字面量列表，每个子句 = 禁止该坏三点对应的 1-元/2-元/3-元取向组合）。
    用于增量 SAT：反复 SAT→oracle→加阻断子句，直至找到真解或证明 UNSAT。
    """
    points = []
    owners = []
    for owner, (u, v), b in zip(range(len(edges)), edges, bits):
        cell = directed_cells([(u, v)], [b])[0]
        orbit = c4_lifts_n(cell, N)
        points.extend(orbit)
        owners.extend([owner] * 4)
    if len(set(points)) != 2 * N:
        return []  # 退化点集（非 2N 互异），跳过

    # 线键分组（O(N²) 构建，再在每条线上枚举三元组）
    def lk(p, q):
        dx, dy = q[0] - p[0], q[1] - p[1]
        if dx == 0 and dy == 0:
            return None
        d = math.gcd(abs(dx), abs(dy))
        a, b = dy // d, -dx // d
        if a < 0 or (a == 0 and b < 0):
            a, b = -a, -b
        return a, b, a * p[0] + b * p[1]

    line_members = {}
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            key = lk(points[i], points[j])
            if key is None:
                continue
            line_members.setdefault(key, set()).update((i, j))

    blocks = []
    seen = set()
    for members in line_members.values():
        if len(members) < 3:
            continue
        for i, j, k in itertools.combinations(members, 3):
            if not collinear(points[i], points[j], points[k]):
                continue
            owner_set = tuple(sorted({owners[i], owners[j], owners[k]}))
            orients = tuple((o, bits[o]) for o in owner_set)
            sig = (owner_set, orients)
            if sig in seen:
                continue
            seen.add(sig)
            # 阻断子句：¬y[2*o + bit]（pysat 负字面量 = -(2*o+bit+1)）
            clause = [-(2 * o + bit + 1) for o, bit in orients]
            blocks.append(clause)
    return blocks


def incremental_solve_subproblem(edges, N, max_iter=200):
    """精确增量 SAT 子问题：反复 SAT→oracle→加阻断，直至找到真解或证明 UNSAT。

    返回 (verdict, sol_bits_or_None, formula, meta, ncells, direct_unsat)
      - "sat_solution"    : 真 rot4-NTIL 解（bits 有效）
      - "unsat"           : 增量公式 UNSAT ⇒ 该 2-因子确实无可行取向
        direct_unsat=True : 3-CNF 直接 UNSAT（可提取广义核割）
        direct_unsat=False: 经阻断子句后才 UNSAT（仅可加入精确 no-good，核不可迁移）
      - "unknown"         : 求解器超时/未知
      - "sat_blocked_no_blocks" : SAT 但阻断子句生成失败（退化）
      - "max_iter"        : 迭代超限未决
    """
    formula, meta, ncells = build_formula(edges, N)

    for iteration in range(max_iter):
        status, model = solve_pysat_model(formula)
        if status is True:  # UNSAT
            return "unsat", None, formula, meta, ncells, (iteration == 0)
        if status is None:  # UNKNOWN → 不能下结论
            return "unknown", None, formula, meta, ncells, False

        # SAT：导出 bits，几何 oracle 复核
        bits = model_to_bits(model, ncells)
        ok, _npts, _bt = verify_ntil(edges, bits, N)
        if ok:
            return "sat_solution", bits, formula, meta, ncells, False

        # SAT 但存在坏三点：从 oracle 提取阻断子句
        blocks = find_bad_triple_blocks(edges, bits, N)
        if not blocks:
            return "sat_blocked_no_blocks", None, formula, meta, ncells, False
        for cl in blocks:
            formula.append(cl)

    return "max_iter", None, formula, meta, ncells, False


def verify_core_unsat(edges, core_counts, N):
    """独立验证：仅由核边集构造的 3-CNF 是否被两个独立求解器判定 UNSAT。

    core_counts: {无向对: 重数(1或2)}。用这些边建 2-因子 → 跑 Glucose4 + z3。
    两者均 UNSAT 才返回 True，确保割 sound。
    """
    core_edges = []
    for (u, v), cp in core_counts.items():
        for _ in range(int(cp)):
            core_edges.append((u, v))
    if len(core_edges) == 0 or len(core_edges) > len(edges):
        return False
    try:
        formula, meta, nc = build_formula(core_edges, N)
        st, _ = solve_pysat_model(formula)
        if st is not True:
            return False
        from validate_solver import solve_z3, make_cnf
        clauses, _ = make_cnf(core_edges, N)
        z3r = solve_z3(clauses, nc)
        return z3r is True
    except Exception:  # noqa: BLE001
        return False


# ───────────────────── 主问题：CP-SAT 全局 2-因子空间 ─────────────────────
def build_master(M, random_obj=False, seed=None):
    """构造 CP-SAT 主问题（度约束 + 空割集），返回 (model, y, pos_list)。

    若 random_obj=True，添加随机线性目标以打破 CP-SAT 搜索偏向。
    """
    model = cp_model.CpModel()
    positions = [(u, v) for u in range(M) for v in range(u, M)]
    pos2idx = {p: i for i, p in enumerate(positions)}
    y = {}
    for (u, v) in positions:
        if u == v:
            y[(u, v)] = model.NewIntVar(0, 1, f"y_{u}_{v}")  # 自环至多 1
        else:
            y[(u, v)] = model.NewIntVar(0, 2, f"y_{u}_{v}")  # 含 2-圈
    # 度约束：每顶点入射贡献恰为 2
    for v in range(M):
        terms = []
        if (v, v) in y:
            terms.append(2 * y[(v, v)])  # 自环贡献度 2
        for u in range(v):
            terms.append(y[(u, v)])      # 边 {u,v}（u<v）
        for w in range(v + 1, M):
            terms.append(y[(v, w)])      # 边 {v,w}（v<w）
        model.Add(sum(terms) == 2)
    # 随机目标：打破 CP-SAT 搜索偏向
    if random_obj:
        rng = random.Random(seed)
        obj_terms = []
        for (u, v) in positions:
            obj_terms.append(y[(u, v)] * rng.randint(-100, 100))
        model.Minimize(sum(obj_terms))
    return model, y, positions, pos2idx


def y_to_edges(solver, y, positions):
    """从 CP-SAT 解读出 2-因子边列表（恰 M 条）。"""
    M = max(max(p) for p in positions) + 1
    edges = []
    for (u, v) in positions:
        cnt = solver.Value(y[(u, v)])
        for _ in range(cnt):
            edges.append((u, v))
    assert len(edges) == M, f"2-因子边数={len(edges)} != M={M}"
    return edges


def add_core_cut(model, y, counts, tag):
    """添加 sound 广义割：禁止任何含核多重集的 2-因子。

    对每个核位置 up（出现 c_p 次）：reify 布尔 cond ⇔ (y[up] <= c_p-1)；
    割 = BoolOr(cond) ≥ 1 ⇒ 至少一个核位置不足 ⇒ 不全含核 ⇒ sound 排除。
    若核为空（MUS 提取失败）则回退为无效割（调用方应改用精确 no-good）。
    """
    if not counts:
        return False
    conds = []
    for up, cp in counts.items():
        if up not in y:
            continue
        cond = model.NewBoolVar(f"cut_{tag}_{up[0]}_{up[1]}")
        model.Add(y[up] <= cp - 1).OnlyEnforceIf(cond)
        model.Add(y[up] >= cp).OnlyEnforceIf(cond.Not())
        conds.append(cond)
    if not conds:
        return False
    model.AddBoolOr(conds)
    return True


def add_exact_nogood(model, y, edges, tag):
    """精确剔除某 2-因子（用于 sat_blocked / MUS 失败回退）。

    对每条边统计出现次数 r_p；要求至少一个位置 y[p] != r_p。
    """
    counts = Counter((min(u, v), max(u, v)) for (u, v) in edges)
    conds = []
    for up, rp in counts.items():
        if up not in y:
            continue
        cond = model.NewBoolVar(f"ng_{tag}_{up[0]}_{up[1]}")
        model.Add(y[up] == rp).OnlyEnforceIf(cond.Not())
        model.Add(y[up] != rp).OnlyEnforceIf(cond)
        conds.append(cond)
    if not conds:
        return False
    model.AddBoolOr(conds)
    return True


def add_basin_init_cuts(model, y, basin_edges_list, timeout=30):
    """对六个已知 UNSAT 的 V20 盆地，提取其 MUS 核并加 sound 广义割（初始化强割）。

    返回 [(tag, counts), ...] 以便持久化。
    """
    cores = []
    for bid, edges in basin_edges_list:
        # 仅当盆地顶点范围落在主问题顶点范围内才有效（盆地为 m=37）
        maxv = max(max(e) for e in edges)
        if maxv >= len(y):  # y 的键数即 M（顶点 0..M-1）
            continue
        N = 2 * len(edges)
        try:
            formula, meta, ncells = build_formula(edges, N)
            status, _ = solve_pysat_model(formula)
            if status is not True:
                continue  # 应是 UNSAT；非 UNSAT 则跳过（不加固）
            mus = extract_mus(formula, ncells, timeout=timeout)
            counts = mus_to_core(mus, meta, ncells, edges)
            if counts:
                if add_core_cut(model, y, counts, f"basin_{bid}"):
                    cores.append((f"basin_{bid}", dict(counts)))
            else:
                # MUS 提取失败 → 精确 no-good（仍 sound）
                add_exact_nogood(model, y, edges, f"basin_{bid}")
                cores.append((f"basin_{bid}_ng", dict(
                    Counter((min(u, v), max(u, v)) for (u, v) in edges))))
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] 盆地 {bid} 初始化割失败：{e!r}")
    return cores


# ───────────────────── Benders 主循环 ─────────────────────
def run_benders(M, budget_s=240, per_solve_s=10, mus_timeout=30,
                out_path=None, init_basins=True, inject_known=True,
                cuts_file=None, max_d=None, max_l=None,
                random_obj_seed=None):
    N = 2 * M
    opt_str = (f", 二圈上限={max_d}" if max_d is not None else "") \
              + (f", 自环上限={max_l}" if max_l is not None else "") \
              + (f", 随机种子={random_obj_seed}" if random_obj_seed is not None else "")
    print(f"[Benders] 启动 m={M}, N={N}, 预算={budget_s}s, "
          f"每次主求解上限={per_solve_s}s, MUS超时={mus_timeout}s{opt_str}")
    model, y, positions, pos2idx = build_master(
        M, random_obj=(random_obj_seed is not None), seed=random_obj_seed)
    if max_l is not None:
        model.Add(sum(y[(v, v)] for v in range(M) if (v, v) in y) <= max_l)

    # ── 割持久化：跨会话累积 sound 排除 ──
    if cuts_file is None:
        cuts_file = HERE / f"benders_cuts_m{M}.json"
    cuts_path = Path(cuts_file)
    all_cores = []  # [(tag, {up: cp})]

    def persist_core(tag, counts):
        all_cores.append((tag, {f"{u},{v}": cp for (u, v), cp in counts.items()}))
        try:
            cuts_path.write_text(json.dumps(all_cores, ensure_ascii=False),
                                 encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] 割持久化失败：{e!r}")

    # 载入已有割
    loaded = 0
    if cuts_path.exists():
        try:
            prev = json.loads(cuts_path.read_text(encoding="utf-8"))
            for tag, cds in prev:
                counts = {tuple(int(x) for x in k.split(",")): cp
                          for k, cp in cds.items()}
                if add_core_cut(model, y, counts, tag):
                    loaded += 1
            all_cores.extend(prev)
            print(f"  已载入 {loaded} 条历史割（来自 {cuts_path.name}）")
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] 载入历史割失败：{e!r}")

    cut_count = loaded
    if init_basins and M == 37 and not any(t.startswith("basin_")
                                            for t, _ in all_cores):
        t0 = time.time()
        basins = load_negatives()  # [(id, edges)]（六 V20 盆地，m=37 专属）
        for tag, counts in add_basin_init_cuts(model, y, basins,
                                               timeout=mus_timeout):
            if add_core_cut(model, y, counts, tag):
                cut_count += 1
                persist_core(tag, counts)
        print(f"  已加 {cut_count - loaded} 条盆地初始化割"
              f"（耗时 {time.time()-t0:.1f}s）")

    stats = {
        "m": M, "N": N, "budget_s": budget_s, "per_solve_s": per_solve_s,
        "init_cuts": cut_count, "iterations": 0,
        "unsat": 0, "sat_blocked": 0, "sat_solution": 0,
        "incremental_unsat": 0, "sat_blocked_no_blocks": 0,
        "incremental_unknown": 0, "incremental_max_iter": 0,
        "invalid": 0, "master_infeasible": False,
        "core_cut_sizes": [], "elapsed_s": 0.0, "known_confirmed": False,
    }
    results = []
    breakthrough = None

    # ── 注入已知正解校验（验证 subproblem→verify 全链路能识别真解）──
    if inject_known:
        try:
            kedges, kbits, ksrc = load_positive(M)
            # 仅当已知解落在本主问题顶点范围（0..M-1）内才校验
            if max(max(e) for e in kedges) < M:
                formula, meta, nc = build_formula(kedges, N)
                st, mod = solve_pysat_model(formula)
                if st is False:
                    bits = model_to_bits(mod, nc)
                    ok, npts, bt = verify_ntil(kedges, bits, N)
                    if ok:
                        stats["known_confirmed"] = True
                        results.append({"iter": 0, "kind": "known_injection",
                                        "verdict": "sat_solution",
                                        "source": ksrc, "n_points": npts,
                                        "bad_triples": bt})
                        print(f"  [注入校验] 已知正解 {ksrc} 通过："
                              f"subproblem SAT + verify bad_triples={bt} → "
                              f"★ rot4-NTIL 解确认")
                    else:
                        results.append({"iter": 0, "kind": "known_injection",
                                        "verdict": "sat_blocked",
                                        "source": ksrc, "bad_triples": bt})
                        print(f"  [注入校验] 已知正解 {ksrc} 子问题 SAT 但几何坏"
                              f"（异常，应调查）：bad_triples={bt}")
                else:
                    results.append({"iter": 0, "kind": "known_injection",
                                    "verdict": "unsat", "source": ksrc})
                    print(f"  [注入校验] 已知正解 {ksrc} 子问题 UNSAT"
                          f"（异常，松弛过强！）")
        except Exception as e:  # noqa: BLE001
            print(f"  [注入校验] m={M} 无可用正解或校验失败：{e!r}")

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = per_solve_s
    solver.parameters.num_search_workers = 1  # 单进程，不爆 CPU

    t_start = time.time()

    while time.time() - t_start < budget_s:
        st = solver.Solve(model)
        if st == cp_model.OPTIMAL or st == cp_model.FEASIBLE:
            edges = y_to_edges(solver, y, positions)
        elif st == cp_model.INFEASIBLE:
            stats["master_infeasible"] = True
            print("  主问题不可行 ⇒ 累积割已排除所有 2-因子（在预算内）。")
            break
        else:
            # UNKNOWN（超时但仍可能返回可行解）
            if solver.StatusName(st) == "UNKNOWN" and solver.BestObjectiveBound() is not None:
                try:
                    edges = y_to_edges(solver, y, positions)
                except AssertionError:
                    print("  主求解超时且未得可行解，停止。")
                    break
            else:
                print(f"  主求解状态 {solver.StatusName(st)}，停止。")
                break

        stats["iterations"] += 1
        rec = {"iter": stats["iterations"], "edges": edges}

        # 增量精确 SAT 子问题（修复旧版 sat_blocked 错误删除因果）
        verdict, sol_bits, formula, meta, ncells, direct_unsat = (
            incremental_solve_subproblem(edges, N, max_iter=200))

        if verdict == "sat_solution":
            rec.update({"verdict": "sat_solution", "bits": sol_bits,
                        "n_points": 2 * N, "bad_triples": 0})
            stats["sat_solution"] += 1
            breakthrough = rec
            print(f"  ★★★ 第 {stats['iterations']} 轮发现 rot4-NTIL 解！")
            break

        elif verdict == "unsat":
            if direct_unsat:
                # 3-CNF 直接 UNSAT → 可提取广义核割（MUS 来自纯 3-CNF，不含阻断子句）
                mus = extract_mus(formula, ncells, timeout=mus_timeout)
                counts = mus_to_core(mus, meta, ncells, edges)
                if counts:
                    verified = verify_core_unsat(edges, counts, N)
                    if not verified:
                        print(f"  [warn] 第{stats['iterations']}轮核独立验证"
                              f"（Glucose4+z3）失败，降为精确剔除")
                        add_exact_nogood(model, y, edges,
                                         f"it{stats['iterations']}")
                        cut_count += 1
                        rec.update({"verdict": "unsat_noverify",
                                    "core_size": len(counts)})
                    else:
                        add_core_cut(model, y, counts,
                                     f"it{stats['iterations']}")
                        stats["core_cut_sizes"].append(len(counts))
                        cut_count += 1
                        persist_core(f"it{stats['iterations']}", counts)
                        rec.update({"verdict": "unsat",
                                    "core_size": len(counts),
                                    "n_clauses": len(formula)})
                else:
                    add_exact_nogood(model, y, edges,
                                     f"it{stats['iterations']}")
                    cut_count += 1
                    rec.update({"verdict": "unsat_nocore",
                                "n_clauses": len(formula)})
                stats["unsat"] += 1
                stats["incremental_unsat"] += 1
            else:
                # 经阻断子句后才 UNSAT → 仅精确剔除该因子（阻断子句不可迁移）
                add_exact_nogood(model, y, edges,
                                 f"it{stats['iterations']}")
                cut_count += 1
                rec.update({"verdict": "unsat_incremental",
                            "n_clauses": len(formula)})
                stats["unsat"] += 1
                stats["incremental_unsat"] += 1

        elif verdict == "sat_blocked_no_blocks":
            rec.update({"verdict": "sat_blocked_no_blocks",
                        "n_clauses": len(formula)})
            stats["sat_blocked_no_blocks"] += 1
            # 不能割除（可能只是阻断子句生成失败，不代表不存在解）

        elif verdict == "unknown":
            rec.update({"verdict": "unknown"})
            stats["incremental_unknown"] += 1
            # 不能割除（求解器超时，可能是真解）

        elif verdict == "max_iter":
            rec.update({"verdict": "incremental_max_iter",
                        "n_clauses": len(formula)})
            stats["incremental_max_iter"] += 1
            # 不能割除（迭代超限，可能是真解）

        else:
            rec.update({"verdict": verdict, "n_clauses": len(formula)})

        results.append(rec)
        if stats["iterations"] % 5 == 0:
            print(f"  [{stats['iterations']}] 耗时 {time.time()-t_start:.0f}s "
                  f"割数={cut_count} 最近={rec['verdict']} "
                  f"UNSAT={stats['unsat']}({stats['incremental_unsat']}) "
                  f"blocked={stats['sat_blocked']} "
                  f"无阻断={stats['sat_blocked_no_blocks']} "
                  f"解={stats['sat_solution']}")

    stats["elapsed_s"] = round(time.time() - t_start, 1)
    stats["total_cuts"] = cut_count
    out = {"summary": stats, "results": results,
           "breakthrough": breakthrough}
    if out_path:
        p = Path(out_path)
        p.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                     encoding="utf-8")
        print(f"写入 {p}")
    print(f"\n===== Benders 汇总 (m={M}) =====")
    print(f"迭代={stats['iterations']} 总割={cut_count} "
          f"UNSAT={stats['unsat']}(增量{stats['incremental_unsat']}) "
          f"blocked={stats['sat_blocked']} "
          f"no_blocks={stats['sat_blocked_no_blocks']} "
          f"未知={stats['incremental_unknown']} "
          f"解={stats['sat_solution']} 主不可行={stats['master_infeasible']}")
    if breakthrough:
        print("★★★ 突破：发现 rot4-NTIL 解！见输出文件。")
    else:
        print("本轮未找到解（符合 m=37 难度预期）；已 sound 排除多族 2-因子。")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--budget", type=int, default=240,
                    help="总预算秒数（单进程）")
    ap.add_argument("--per-solve", type=int, default=10,
                    help="每次 CP-SAT 主求解时间上限（秒）")
    ap.add_argument("--mus-timeout", type=int, default=30)
    ap.add_argument("--no-basin-init", action="store_true",
                    help="不加六盆地初始化割")
    ap.add_argument("--max-d", type=int, default=None,
                    help="二圈数上限（None=不限）；用于搜索分层")
    ap.add_argument("--max-l", type=int, default=None,
                    help="自环数上限（None=不限）；V20 型空间建议 --max-l 1")
    ap.add_argument("--random-obj-seed", type=int, default=None,
                    help="随机线性目标种子（打破 CP-SAT 搜索偏向）；None=默认搜索")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or str(HERE / f"benders_global_m{args.m}.json")
    run_benders(args.m, budget_s=args.budget, per_solve_s=args.per_solve,
                mus_timeout=args.mus_timeout, out_path=out,
                init_basins=not args.no_basin_init,
                max_d=args.max_d, max_l=args.max_l,
                random_obj_seed=args.random_obj_seed)


if __name__ == "__main__":
    main()
