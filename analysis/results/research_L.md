# Research L — 带理论先验的局部搜索（用户提出的构造思路）

## 用户原意（2026-07-14）
> 先根据所有已知理论固定一些点，再在概率高的区域随机放点；看共线数量，共线多就移动一个点，
> 看共线是否变少，变少再移另一个，如此迭代看能否快速构造，并在小 m 上找可复用规律。

本质 = **带理论先验的局部搜索 / 贪心爬山**（区别于之前的随机 nibble 与 SAT）。

## 实现（analysis/local_search_fix.py，坐标约定与 solve_m37_r9b 一致）
- 状态：m 个互不相同的"基本域 cell" `(x,y)∈[0,m)²`。
- 提升：`c4(cell,r,2m)` 生成 4m 点（C4 对称）。
- 目标：`bad` = 共线三元组总数（bad==0 ⇔ 无三点共线）。
- **关键定理桥接**：rot4-NTIL（4m 点、C4 对称、无三点共线）⇔ 2-因子 + 逐线≤2（R9b）。
  故 4m 个 C4 对称且无三点共线的点**自动是** 2-因子解，搜索中无需硬编码 2-因子约束。
- 理论先验三件套：
  1. **锚点固定**：随机选 `anchors*m` 个 cell 不移动（"先固定一些点"）。
  2. **高概率区初始化/候选偏置**：`prior_weight` 避开主对角线(x==y)、偏好中环(mid-ring ~0.62)。
  3. **Sidon 差异过滤**（FDR/Part-I 必要条件的硬剪枝）：每步保证 `{2(y-x)}` 为 Sidon 集。
- 移动方式：单 cell 重定位；`greedy`（只接受下降）/ `sa`（偶走上坡逃局部极小）。

## 扫描配置矩阵（analysis/ls_sweep.py）
m ∈ {4,5,6,7,8}，每配置 8 次重启，4000 迭代：
- C1 greedy / random / anc0
- C2 sa / random / anc0
- C3 sa / highprob / anc0
- C4 sa / highprob / anc0.4
- C5 sa / sidon-init / sidon-filter

## 初步现象（已确认）
- **局部极小是杀手**：m=6（SA+高概率+40%锚点）2000 迭代后卡在 bad=4；m=7 同法卡在 bad=4。
  纯单点下降在 m≥6 即陷入平台，与用户"这方法不一定靠谱"的直觉一致。
- 速度极快：m=6 单次 2000 迭代仅 ~0.07s（Python 全量重算）。

## 待补：完整扫描结果（results/local_search_sweep.json）
- 各配置 × 各 m 的求解率 / 平均 final_bad。
- 哪种理论先验真正提升收敛（C2 vs C3 vs C5）。
- 锚点是否帮助（C3 vs C4）。
- 典型下降曲线（results/local_search_trajectory.json）+ 落点热力（中环/避对角是否显著）。
