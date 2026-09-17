"""
r9e_obstruction_density.py -- 量化 rot4-NTIL 二次层障碍 (R9d) 的密度与代数结构.

复用 (不重推):
  - orbit_c4 / c4        : 标准 2m x 2m 网格的 C4 提升 (与 brute_collinear 真值一致)
  - R9d (T7/T8/T9)        : 障碍精确定位在斜向非径向线, 轴对齐+径向仅 O(m) 条

本脚本做两件独立的事:
  (1) DENSITY: 对随机置换(=2-因子的置换子类, 合法解的严格子集)采样, 统计其
      4m 个提升点中 3-共线三元组的数量均值 E[#bad](m). 这是概率方法下界:
      若 E[#bad] 随 m 增长, 则随机/局部搜索几乎必然失败, m=37 必靠结构化构造.
  (2) ORIENTATION: 对坏三元组按 16 重 C4 取向类 (d2,d3) 分类, 验证 R9d 的
      "斜向(含 90°旋转)类携带几乎全部障碍" 猜想.

输出 (持久化, 从不截断):
  results/r9e_density.csv   每行一个 (m, sampler, K, mean_bad, std_bad, total_triples, collision_rate)
  results/r9e_density.json  完整数据 + 取向类分布
  results/r9e_density.log   人类可读日志

用法:
  python r9e_obstruction_density.py --m-max 22 --K 600 --seed 1
"""
import os, sys, math, json, argparse, random, time
from itertools import combinations
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solve_m37_r9b import orbit_c4   # 复用真实提升 (与真值一致)
from quadratic_sidon_completeness import c4

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)


def lift_selection(cells, m):
    """cells: list of (x,y) in top-left quadrant. 返回去重后的提升点列表,
    每点带 (cell_idx, r) 标签用于取向分类. n=2m."""
    n = 2 * m
    pts = []          # (X, Y, cell_idx, r)
    seen = {}
    for ci, (x, y) in enumerate(cells):
        for r in range(4):
            X, Y = c4((x, y), r, n)
            if (X, Y) in seen:
                continue
            seen[(X, Y)] = len(pts)
            pts.append((X, Y, ci, r))
    return pts


def line_key(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    a, b, c = -(y2 - y1), (x2 - x1), (y2 - y1) * x1 - (x2 - x1) * y1
    g = math.gcd(math.gcd(abs(a), abs(b)), abs(c))
    if g != 0:
        a, b, c = a // g, b // g, c // g
    # 首非零为正
    if a < 0 or (a == 0 and b < 0) or (a == 0 and b == 0 and c < 0):
        a, b, c = -a, -b, -c
    return (a, b, c)


def count_bad(pts):
    """返回 (total_bad_triples, orientation_class_counts{16}, axial_count, oblique_count)."""
    N = len(pts)
    line_map = defaultdict(list)   # line_key -> list of point indices
    for i in range(N):
        xi, yi, _, _ = pts[i]
        for j in range(i + 1, N):
            xj, yj, _, _ = pts[j]
            key = line_key((xi, yi), (xj, yj))
            line_map[key].append(i)
            line_map[key].append(j)
    total = 0
    cls = defaultdict(int)
    axial = 0
    oblique = 0
    for key, idxs in line_map.items():
        s = set(idxs)
        if len(s) < 3:
            continue
        lst = list(s)
        total += math.comb(len(lst), 3)
        for i1, i2, i3 in combinations(lst, 3):
            _, _, c1, r1 = pts[i1]
            _, _, c2, r2 = pts[i2]
            _, _, c3, r3 = pts[i3]
            t = (-r1) % 4
            d2 = (r2 - r1) % 4
            d3 = (r3 - r1) % 4
            cls[(d2, d3)] += 1
            if d2 in (0, 2) and d3 in (0, 2):
                axial += 1
            else:
                oblique += 1
    return total, cls, axial, oblique


def random_perm_cells(m, rng):
    perm = list(range(m))
    rng.shuffle(perm)
    return [(i, perm[i]) for i in range(m)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m-max", type=int, default=22)
    ap.add_argument("--m-min", type=int, default=6)
    ap.add_argument("--K", type=int, default=600)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--orient-m", type=int, default=14,
                    help="在哪个 m 上统计 16 重取向类分布 (小 m 更快)")
    ap.add_argument("--orient-K", type=int, default=1500)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    log = open(os.path.join(OUT, "r9e_density.log"), "w")
    csv_path = os.path.join(OUT, "r9e_density.csv")
    with open(csv_path, "w") as f:
        f.write("m,sampler,K,mean_bad,std_bad,total_triples,collision_rate\n")

    rows = []
    orient_classes = defaultdict(int)
    orient_total = 0
    orient_axial = 0
    orient_oblique = 0

    for m in range(args.m_min, args.m_max + 1, 2):
        t0 = time.time()
        bads = []
        for _ in range(args.K):
            cells = random_perm_cells(m, rng)
            pts = lift_selection(cells, m)
            b, _, _, _ = count_bad(pts)
            bads.append(b)
        mean = sum(bads) / len(bads)
        var = sum((x - mean) ** 2 for x in bads) / len(bads)
        std = math.sqrt(var)
        total_triples = math.comb(4 * m, 3)
        rate = mean / total_triples if total_triples else 0.0
        dt = time.time() - t0
        rows.append((m, "perm", args.K, mean, std, total_triples, rate))
        with open(csv_path, "a") as f:
            f.write(f"{m},perm,{args.K},{mean:.3f},{std:.3f},{total_triples},{rate:.3e}\n")
        msg = (f"[dens] m={m} K={args.K} mean_bad={mean:.2f} std={std:.2f} "
               f"total_triples={total_triples} collision_rate={rate:.3e} ({dt:.1f}s)")
        print(msg, flush=True)
        log.write(msg + "\n")

        # 取向类分布 (仅 orient-m)
        if m == args.orient_m:
            for _ in range(args.orient_K):
                cells = random_perm_cells(m, rng)
                pts = lift_selection(cells, m)
                _, cls, ax, ob = count_bad(pts)
                for k, v in cls.items():
                    orient_classes[k] += v
                orient_total += ax + ob
                orient_axial += ax
                orient_oblique += ob
            msg2 = (f"[orient] m={args.orient_m} K={args.orient_K} "
                    f"axial={orient_axial} oblique={orient_oblique} "
                    f"oblique_frac={orient_oblique/max(1,orient_total):.3f}")
            print(msg2, flush=True)
            log.write(msg2 + "\n")

    # 保存 JSON
    out = {
        "params": {"m_min": args.m_min, "m_max": args.m_max, "K": args.K,
                   "seed": args.seed, "orient_m": args.orient_m,
                   "orient_K": args.orient_K},
        "density_rows": [
            {"m": r[0], "sampler": r[1], "K": r[2], "mean_bad": r[3],
             "std_bad": r[4], "total_triples": r[5], "collision_rate": r[6]}
            for r in rows
        ],
        "orientation": {
            "m": args.orient_m, "K": args.orient_K,
            "axial": orient_axial, "oblique": orient_oblique,
            "oblique_frac": orient_oblique / max(1, orient_total),
            "class_counts": {f"({k[0]},{k[1]})": v
                             for k, v in sorted(orient_classes.items())},
        },
    }
    with open(os.path.join(OUT, "r9e_density.json"), "w") as f:
        json.dump(out, f, indent=2)
    log.write("DONE\n")
    log.close()
    print(f"[done] wrote {csv_path} and r9e_density.json", flush=True)


if __name__ == "__main__":
    main()
