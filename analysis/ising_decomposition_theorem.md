# Ising 分解定理与受挫模板路线

> 配套：`ising_reduction.py`（化简验证）、`cutpolytope_sdp.py`（路线 1：cut-polytope
> 下界）、`frustrated_components.py`（路线 2：受挫连通分量）。
> 数据：`results/cutpolytope_sdp.json`、`results/frustrated_components.json`。

## 1. 精确连通分量分解定理（已严格成立）

固定一个 2-因子，其带符号 Ising/MaxCut 能量为

```
V_E(s) = n_cl/8 + (1/8) Σ_{(a,b,c,bits)} [ a_i a_j s_i s_j + a_i a_k s_i s_k + a_j a_k s_j s_k ].
```

定义**支撑图** `G_J`：顶点 = cell（37 个方向变量），边 (i,j) 存在 ⟺ 某个 clause
同时含 i 与 j（即 `J_{ij} ≠ 0`）。

**定理.** 每个 clause 的 3 个顶点两两有边，故必落在 `G_J` 的同一连通分量内。
因此不同连通分量的变量从不共现于任何 clause，`V_E` 的能量按 `G_J` 的连通分量
**直和分解**：

```
min_viol(整图) = Σ_{c ∈ comps(G_J)}  min_viol(G_J[c]) ,
```

其中 `min_viol(G_J[c])` 是分量 c 内部 clause 子集的最小违例数。

**推论.**
- rot4-NTIL 的取向障碍被**精确局部化**到 `G_J` 的「受挫连通分量」
  （`min_viol(c) > 0` 的分量）。m=37 不可解 ⟺ 每个 2-因子的 `G_J` 至少有一个
  受挫分量。
- 这与先前的「缺陷全局分布」（408 的 16 违例分布于 30/37 边）**不矛盾**：全局
  分布指的是 *边层面*；而 `G_J` 分量层面，障碍可能集中在少数（甚至单个）小分量，
  只是该分量内部边很多、且与大量 cell 相邻。
- 这把用户的「第二方向」（最小不可满足核 / 受挫 signed cycles / 通用模板）
  **精确化**：通用障碍 = 一个在 *所有* m=37 的 2-因子中都出现的受挫分量结构。

## 2. 路线 1 — cut-polytope / SDP 对偶证书（进行中）

在 GW MAX-CUT SDP 中加入 cut-polytope 有效不等式，缩小可行集以抬高下界：

```
min_viol ≥ n_cl/8 + (1/8) · SDP_min( Σ J_code Y_ij ),
   Y ⪰ 0, diag(Y)=1,
   + triangle:  Y_ij+Y_jk+Y_ki ≥ −1,  Y_ij−Y_ik−Y_jk ≥ −1 (及轮换),
   + odd-cycle:  Σ_{边∈C} Y_e − Σ_{非边∈C} Y_e ≤ (|C|−1)/2  (C 奇圈).
```

若某配置的证书下界达到其已知 `min_viol`，即**证明该配置最优**。

| 配置 | 已知 | SDP(纯) | SDP+triangle | SDP+tri+oddcyc | 结论 |
|------|------|---------|--------------|----------------|------|
| m37-408 | 16 | 12.52 | _(pending)_ | _(pending)_ | 待收口 |
| m37-448 | 17 | 15.18 | _(pending)_ | _(pending)_ | 待收口 |
| m36 | 0 | 0.00(紧) | _(pending)_ | _(pending)_ | 验证 |

> 注：纯 SDP 下界 12.52/15.18 来自 `sdp_frustration_cert.py`。triangle/odd-cycle
> 加强下界由 `cutpolytope_sdp.py` 计算（`results/cutpolytope_sdp.json`）。
> triangle 不等式严格强于纯 SDP，故加强下界 ≥ 纯 SDP 值。

## 3. 路线 2 — 受挫分量与通用模板（进行中）

`frustrated_components.py` 计算三个配置的 `G_J` 连通分量及每分量精确 `min_viol`
（≤20 变量暴力解，更大用 CP-SAT），并验证分解定理（分量 `min_viol` 之和 = 全局值）。

| 配置 | 分量数 | 分量大小 | 受挫分量（大小/违例） |
|------|--------|----------|----------------------|
| m37-408 | _(pending)_ | _(pending)_ | _(pending)_ |
| m37-448 | _(pending)_ | _(pending)_ | _(pending)_ |
| m36 | _(pending)_ | _(pending)_ | 无（全可满足） |

**模板假设.** 若 m37-408 与 m37-448 的受挫分量共享一个小的带符号子图结构
（例如同一 5–10 节点的受挫奇圈型 signed graph），则该结构很可能是 *几何强制*
的——即对任意 m=37 的 2-因子都出现。下一步将：
1. 提取两配置受挫分量内的最小受挫子集（MFS，贪心删除 + 小分量暴力）；
2. 在多个突变 2-因子上复现，求同构交集；
3. 尝试用「37 奇数 + 2-正则 + rot4 共线几何」证明该模板不可避免。

## 4. 路线 3 — 联合松弛（远期）

外层选 2-因子、内层 cut/Ising 的联合 LP/SDP。若松弛对所有 2-因子给严格正下界
⇒ m=37 不可能性证明；若给零点 ⇒ 构造方向。这是真正收口的方向，但需要把
2-因子多面体与 cut-polytope 联合建模，工程量最大，留待路线 1/2 收敛后。
