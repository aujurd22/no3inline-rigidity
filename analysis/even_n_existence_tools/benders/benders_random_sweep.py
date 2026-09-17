#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高通量随机 2-因子 SAT 扫描（2026-07-21，重磅结果直击）。

对每个随机 2-因子用 **fast_solve** 判定：
  fast_build_3cnf（等价快速构建，见 fast_3cnf.py）+ dpll_model + 完整几何 oracle。
  - sat_solution → ★突破：找到 m=37 rot4-NTIL 解（重磅）。
  - unsat → 该 2-因子被排除（sound 松弛，真实障碍）。
积累大规模 UNSAT 证据即"计算上排除 m=37"的重磅结果。

增量落盘：每 save_every 次写 progress JSON。
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from scan_new_basins import random_2factor  # noqa: E402
from fast_3cnf import fast_build_3cnf  # noqa: E402
from benders_subproblem import dpll_model  # noqa: E402
from prepare_v20_basin_archive import geometry_and_defects, directed_cells  # noqa: E402


def fast_solve(edges):
    """等价快速判定。返回 (verdict, n_clauses)。
    dpll_model 约定：status True=UNSAT, False=SAT, None=超预算。
    """
    clauses, nvars = fast_build_3cnf(edges)
    status, model = dpll_model(clauses, nvars)
    if status is True:
        return "unsat", len(clauses)
    if status is None:
        return "unknown", len(clauses)
    # status False → 松弛 SAT，model 是长度 nvars 的位赋值 list
    bits = list(model)
    try:
        geom, _ = geometry_and_defects(edges, bits)
    except AssertionError:
        return "sat_unverified", len(clauses)
    bad = geom.get("bad_triples", 0) if isinstance(geom, dict) else 0
    if bad == 0:
        return "sat_solution", len(clauses)
    return "sat_unverified", len(clauses)


def rng_state_to_json(rng):
    """把 random.Random 内部状态序列化（JSON 友好）。"""
    version, internalstate, gauss = rng.getstate()
    return {"version": version, "internalstate": list(internalstate), "gauss": gauss}


def rng_state_from_json(d):
    return (d["version"], tuple(d["internalstate"]), d["gauss"])


def save_progress(path, target, tested, verdicts, elapsed, breakthrough,
                  rng, extra=None):
    out = {"target": target, "tested": tested, "verdicts": dict(verdicts),
           "elapsed_seconds": elapsed, "breakthrough": breakthrough is not None,
           "rate_per_sec": tested / elapsed if elapsed > 0 else 0.0,
           "rng_state": rng_state_to_json(rng)}
    if extra:
        out.update(extra)
    Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40000, help="目标判定数")
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--save-every", type=int, default=500)
    ap.add_argument("--out", default=str(HERE / "random_sweep_results.json"))
    ap.add_argument("--resume", action="store_true",
                    help="若 out 存在且未突破，则从断点续跑（恢复 RNG 状态）")
    args = ap.parse_args()

    out_path = Path(args.out)
    start = 0
    verdicts = Counter()
    rng = random.Random(args.seed)
    if args.resume and out_path.exists():
        old = json.loads(out_path.read_text(encoding="utf-8"))
        if not old.get("breakthrough"):
            start = old.get("tested", 0)
            st = old.get("rng_state")
            if st:
                rng.setstate(rng_state_from_json(st))
            if old.get("verdicts"):
                verdicts.update(old["verdicts"])
            print(f"[续跑] 从 {start}/{args.n} 继续（verdicts={old.get('verdicts')}）")
        else:
            print("[警告] 已有突破记录，忽略 --resume，从头重跑")
            start = 0
    print(f"[随机扫描] 目标={args.n} seed={args.seed} out={args.out} start={start}")

    t0 = time.time()
    tested = start
    breakthrough = None

    while tested < args.n:
        edges = random_2factor(rng)
        v, nc = fast_solve(edges)
        verdicts[v] += 1
        tested += 1
        if v == "sat_solution":
            breakthrough = {"idx": tested - 1, "edges": [list(e) for e in edges],
                            "n_clauses": nc}
            (HERE / "sat_solution_found.json").write_text(
                json.dumps(breakthrough, ensure_ascii=False, indent=2),
                encoding="utf-8")
            print(f"\n★★★ 突破！第 {tested - 1} 个随机 2-因子是 rot4-NTIL 解")
            save_progress(out_path, args.n, tested, verdicts,
                          time.time() - t0, breakthrough, rng,
                          extra={"breakthrough_detail": breakthrough})
            break
        if tested % args.save_every == 0:
            el = time.time() - t0
            save_progress(out_path, args.n, tested, verdicts, el, None, rng)
            print(f"  进度 {tested}/{args.n}  判定={dict(verdicts)}  "
                  f"速率={tested / el:.1f}/s")

    if not breakthrough:
        el = time.time() - t0
        save_progress(out_path, args.n, tested, verdicts, el, None, rng,
                      extra={"breakthrough_detail": None})
        print(f"\n写入 {args.out}  耗时 {el:.0f}s  判定 {tested}")
        print(f"未找到解：{tested} 个随机 2-因子全 UNSAT"
              f"（含 sat_unverified={verdicts.get('sat_unverified', 0)}）")


if __name__ == "__main__":
    main()
