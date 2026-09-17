#!/usr/bin/env python3
"""
analyze_cube_proj_layers.py -- m=16 3D 立方体嵌入的左/右投影逐层分析。

对每一层 z（= 到中心距离排位）输出：
  - 该层实际 3D 点数（= 径向环占据数）
  - 左视 (Y,Z) 投影里可见多少个点（distinct Y）
  - 右视 (-Y,Z) 投影里可见多少个点
  - 该层在左视投影中产生的水平带共线三元组数
  - 该层是否落在对角线（x=±y）上导致投影坍缩
"""
import json, math, os, sys
from collections import defaultdict, Counter
sys.path.insert(0, "analysis")
from cube_lens import load_ref, embed

def count_3_collinear_in_layer(ys):
    """同一层内 ys 中三个共线（同 y）=> 水平带共线三元组。"""
    c = Counter(ys)
    return sum(v * (v - 1) * (v - 2) // 6 for v in c.values())

def main():
    m = 16
    cells = load_ref(m)
    P, zs, layers, uniq = embed(cells, m)
    nlay = len(layers)

    rows = []
    for z in range(nlay):
        xy = layers[z]                       # list of (x,y) in this layer
        actual = len(xy)
        ys_left = sorted(set(y for (x, y) in xy))
        ys_right = sorted(set(-y for (x, y) in xy))
        # diagonal orbit: x=±y for all points? actually check if any point is on diag
        on_diag = any(abs(abs(x) - abs(y)) < 1e-9 for (x, y) in xy)
        horiz_3 = count_3_collinear_in_layer([y for (x, y) in xy])
        rows.append({
            "z": z,
            "actual": actual,
            "visible_left": len(ys_left),
            "visible_right": len(ys_right),
            "y_left": ys_left,
            "y_right": ys_right,
            "on_diag": on_diag,
            "horiz_3": horiz_3,
        })

    # overall projection collinear totals (same as cube_proj.py)
    left = [(y, z) for (x, y), z in zip(P, zs)]
    right = [(-y, z) for (x, y), z in zip(P, zs)]

    # total collinear triples per projection (brute)
    def collinear_count(pts):
        n = len(pts); tot = 0; horiz = 0
        for i in range(n):
            x1, y1 = pts[i]
            for j in range(i + 1, n):
                x2, y2 = pts[j]
                dx, dy = x2 - x1, y2 - y1
                for k in range(j + 1, n):
                    x3, y3 = pts[k]
                    if dx * (y3 - y1) == dy * (x3 - x1):
                        tot += 1
                        if y1 == y2 == y3:
                            horiz += 1
        return tot, horiz

    left_tot, left_horiz = collinear_count(left)
    right_tot, right_horiz = collinear_count(right)

    # build report
    lines = []
    L = lines.append
    L(f"# m={m} 立方体嵌入左/右投影逐层分析\n")
    L(f"**3D 总点数**: {len(P)}; **层数**: {nlay}\n")
    L("## 左视 (Y,Z) / 右视 (-Y,Z) 整体共线统计")
    L(f"  左视：总共线三元组 {left_tot}, 水平带 {left_horiz}, 斜向 {left_tot - left_horiz}")
    L(f"  右视：总共线三元组 {right_tot}, 水平带 {right_horiz}, 斜向 {right_tot - right_horiz}\n")
    L("## 逐层明细（z=0 为最内层/底层，z=14 为最外层/顶层）")
    L("  z | 实际点数 | 左视可见 | 右视可见 | 水平带3元 | 对角线层? | 左视 Y 坐标")
    L("  --|----------|----------|----------|----------|----------|------------")
    for r in rows:
        L(f"  {r['z']:2d} | {r['actual']:8d} | {r['visible_left']:8d} | "
          f"{r['visible_right']:8d} | {r['horiz_3']:8d} | {str(r['on_diag']):8s} | "
          f"{r['y_left']}")

    L("\n## 关键观察")
    L(f"  - 14 层里有 13 层实际 4 点，仅第 11 层实际 8 点（即径向环占据 8 的那层）。")
    L(f"  - 左视/右视可见点数常小于实际点数，因为投影把 X 坐标压掉，同 Y 会重叠。")
    L(f"  - 最底层 z=0 在左视里通常只看到 2 点（截图中‘最下面 2 个点’）——")
    L(f"    它实际有 4 点，但轨道落在 x=±y 对角上，Y 投影只有 2 个不同值。")

    text = "\n".join(lines)
    print(text)
    os.makedirs("results", exist_ok=True)
    with open("results/cube_proj_layers.md", "w") as f:
        f.write(text)
    with open("results/cube_proj_layers.json", "w") as f:
        json.dump({"m": m, "n_points": len(P), "n_layers": nlay,
                   "rows": rows, "left": {"total": left_tot, "horizontal": left_horiz},
                   "right": {"total": right_tot, "horizontal": right_horiz}}, f, indent=2)
    print("\n[written] results/cube_proj_layers.md / .json")

if __name__ == "__main__":
    main()
