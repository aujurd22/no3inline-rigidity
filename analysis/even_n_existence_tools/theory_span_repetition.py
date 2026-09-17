"""
理论推导：边缘跨度重复的充要条件及其与 UNSAT 的因果关系。

已知事实：
1. 任意 D=0/L=1 的 37 顶点 2-因子（1自环+36-cycle）必然有重复 span
2. 所有 D=0/L=1 2-因子经 GB 验证为 UNSAT (23/23)
3. m=36 纯 36-cycle 有解且无重复 span

问题：边缘跨度重复是否必然是 UNSAT 的根本原因？
方法：构造一个不含重复 span 的 37-cycle（如果能），验证其可行性。

鸽笼原理：37 个顶点上的 37-cycle 有 37 条边，每条边有 span ∈ {1,2,...,18,0(自环)}
总类别 = 19（18非零 + 1零跨度自环），变量 = 37
→ 至少 37/19 > 1.9 → 必有重复。37/18 ≈ 2.06 → 2-cycle 边必有至少 2 条同 span。

但 m=36 有 36 条边，36/18 = 2 → 理论下限也 ≥2。
而 m=36 解没有同 span 重复！说明"有重复"≠"UNSAT"。
关键在于：**哪些** span 重复？以及它们之间的共线性。

真正的代数刻画：
- Type 1 (a+b=const): 3 cell 的 6 点全在直线 y=-x+C 上。这是共线的"退化"情况
  （实际不是退化的——共线只能发生在每组 3 个点之间）
- Type 2 (|b-a|=const): 3 cell 有相等跨度。跨度相等 ⇒ 某种"平行四边形"
  结构，可能导致 rot4 镜像点之间的共线。

目标：精确刻画 Type 2 导致 UNSAT 的几何机制。
"""
import sys, itertools, time
from collections import Counter
sys.path.insert(0, '.')
from validate_solver import c4_lifts_n, load_negatives

N = 74

def find_t2_explanation():
    """深入分析 Type 2 全坏三元组的几何机制"""
    basins = load_negatives()
    
    # 取 V20_03: Type 2 三元组 (11,20),(16,25),(22,31) —— 均跨度9
    bid, edges = basins[2]  # V20_03 (index 2 in archive)
    
    # 找扩展的全坏三元组
    ncells = len(edges)
    cell_pts = {}
    for idx, (u, v) in enumerate(edges):
        cell_pts[(idx, 0)] = c4_lifts_n((u, v), N)
        cell_pts[(idx, 1)] = c4_lifts_n((v, u), N)
    
    # 找所有 span=9 的边
    span9_cells = []
    for idx, (u, v) in enumerate(edges):
        if abs(v - u) == 9:
            span9_cells.append((idx, u, v))
    
    print(f"V20_03: span=9 的边数 = {len(span9_cells)}")
    for idx, u, v in span9_cells:
        print(f"  cell{idx}: ({u},{v})")
    
    # 取前 3 个 span=9 的 cell，分析它们的 rot4 交互
    if len(span9_cells) >= 3:
        i1, a1, b1 = span9_cells[0]
        i2, a2, b2 = span9_cells[1]
        i3, a3, b3 = span9_cells[2]
        
        print(f"\n=== 3 span=9 cells 的 rot4 交互 ===")
        print(f"  cell{i1}: ({a1},{b1})")
        print(f"  cell{i2}: ({a2},{b2})")
        print(f"  cell{i3}: ({a3},{b3})")
        
        # 关键：这三个 cell 的所有点的"方向向量"
        # rot4 将 (x,y) 映射到 (N-1-y, x)，方向变为垂直
        # orientation 0: 点集包含方向向量 (b-a, a-b) ??? 不，直接是坐标
        # 重点是：三个 cell 的 rot4 点集之间是否有"重叠点"或"共线三点"
        
        for idx, u, v in [(i1, a1, b1), (i2, a2, b2), (i3, a3, b3)]:
            pts0 = c4_lifts_n((u, v), N)
            pts1 = c4_lifts_n((v, u), N)
            print(f"  cell{idx} ({u},{v}): o0={pts0} o1={pts1}")
        
        # 检查 rot4 点集之间的重叠
        for ci, cu, cv in [(i1, a1, b1), (i2, a2, b2), (i3, a3, b3)]:
            for cj, _cu2, _cv2 in [(i1, a1, b1), (i2, a2, b2), (i3, a3, b3)]:
                if ci >= cj:
                    continue
                for oi in [0, 1]:
                    for oj in [0, 1]:
                        pl = set(cell_pts[(ci, oi)]) & set(cell_pts[(cj, oj)])
                        if pl:
                            print(f"  ★ OVERLAP: cell{ci}o{oi} ∩ cell{cj}o{oj} = {pl}")
        
        # 最关键：这三条 span-9 边是否在基本域中"对齐"？
        # a1=11, b1=20; a2=16, b2=25; a3=22, b3=31
        # 三点 (11,20), (16,25), (22,31) 在基本域中是否共线？
        x1, y1 = a1, b1  # 对 orientation 0，cell 坐标就是 (a,b)
        x2, y2 = a2, b2
        x3, y3 = a3, b3
        det = (x2-x1)*(y3-y1) - (x3-x1)*(y2-y1)
        print(f"\n  基本域三点行列式: {det}")
        print(f"  斜率: ({y2-y1})/({x2-x1})={y2-y1}/{x2-x1}={5/5}=1")
        
        # 关键结论：三个 cell 在基本域中共线！(11,20)→(16,25)→(22,31) 在 y=x+9 上
        # 这加上 rot4（把直线旋转）→ 产生复杂的共线模式
        
        # 形式化：若三个 cell (a,b),(c,d),(e,f) 满足 c-a=d-b=e-c=f-d（等差），
        # 则它们共线（y=x+k），且 rot4 将此线映射到 y=-x+... → 全 8 种取向必然在某处产生共线

    # 取一个纯 Type 2 的因子，验证其最小 GB 障碍
    # ——但当前没找到纯 Type 2 的具体例子，先保理论分析

if __name__ == "__main__":
    find_t2_explanation()
