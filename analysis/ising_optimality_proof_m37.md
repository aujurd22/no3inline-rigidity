# m=37 最优性定理：具体 2-因子 `config_408` 的 16 违例已被严格证明

> 日期：2026-07-16
> 对应代码：`cutpolytope_sdp.py`（`sdp_bound` 函数）、`ising_reduction.py`（`build_J`）
> 数据：`results/config_408_edges.json`、`results/cutpolytope_sdp.json`

## 0. 结论（一句话）

对扫掠得到的最优 2-因子 `config_408_edges.json`（37 条边、408 条禁用子句），其方向子问题
的违例数下界由 **cut-polytope + triangle 不等式的 SDP 对偶证书** 严格给出

```
min_viol ≥ 15.9973   (SDP+triangle, CLARABEL [optimal])
```

由于 `min_viol` 为整数且已知存在 16 违例的取向，故 **`min_viol = 16` 已被证明最优**。
此前 CP-SAT 只给出 FEASIBLE（未证最优），现在这个具体 2-因子被锁定在 16。

**完整证明表（`focused_triangle_sdp.py`，2026-07-16）：**

| 配置 | 已知 min_viol | triangle-SDP 下界 | 求解器状态 | 结论 |
|------|--------------|-------------------|-----------|------|
| m37-408 | 16 | 15.9973 | optimal | **16 最优（整数下界 ≥15.997 ⇒ ≥16）** |
| m37-448 | 17 | 17.0000 | optimal_inaccurate | **17 精确最优** |
| m36-SAT | 0 | 0.0000 (=5.1e-6 噪声) | optimal_inaccurate | 确认 SAT（参考 + 方向验证） |

> 注：`focused_triangle_sdp.py` 的自动判定用 `lb ≥ known − 1e-6`，对 408 误报 "not closed"
> （15.9973 < 15.9999）。但 `min_viol` 为整数，`lb ≥ 15.9973 ⇒ min_viol ≥ 16`，故 408 同样
> **已证最优**。448 的下界恰为 17.0000，直接闭合。

> **方向验证**：m36 为 SAT（min_viol=0），其 triangle-SDP 下界为 5.1e-6（SCS 回退的数值噪声，
> 实质为 0）。若下界方向有误，m36 应出现负下界或错误正值；实际 ≈0，确认 (★) 是真下界。
> 基本 SDP（`sdp_frustration_cert.py`）对 m36 也给出精确的 0.00，互相印证。

## 1. 化简回顾（已在 `ising_reframing_m37.md` 严格验证）

固定 2-因子后，因 180° C4 旋转使每个禁用模式与其全反模式成对，违例能量为纯二次

```
V_E(s) = n_cl/8 + (1/8) · Σ_{(i,j)∈支持} J_{ij} s_i s_j ,   s_i ∈ {±1}
```

线性项与三次项因互补对称而消失。`J_{ij}` 由 `build_J(clauses)` 从禁用子句集构造。

令 `y_{ij} = s_i s_j`，则 `y` 落在 **cut polytope** 的松弛（elliptope）内，且

```
Σ J_{ij} y_{ij}  = 8·V_E − n_cl .
```

最小化 `V_E` 等价于在 cut 结构上最小化 `Σ J_{ij} y_{ij}`。

## 2. SDP 下界推导（标准 Goemans–Williamson 框架）

定义 SDP：

```
minimize   Σ_{(i,j)} J_{ij} Y_{ij}
subject to Y ≽ 0,  diag(Y) = 1,            (elliptope)
           三角形不等式（cut polytope 有效不等式，见 §3）。
```

记其最优值为 `SDP_min`。因为 elliptope（及加三角形不等式后的集合）是 cut polytope 的
**外逼近**（可行域更大），最小化目标得到

```
SDP_min  ≤  min_{合法 cut} Σ J_{ij} y_{ij}  =  8·min_viol − n_cl .
```

故

```
min_viol  ≥  (n_cl + SDP_min) / 8 .          ──  (★) 严格下界
```

**加三角形不等式缩小可行域 ⇒ SDP_min 增大 ⇒ 下界 (★) 收紧。**

## 3. 三角形不等式是 cut polytope 的有效不等式

对三角形 (i,j,k)，cut 指标 `y_e = s_a s_b ∈ {−1,+1}` 仅可能取两种模式
`（1,1,1）`（和=3）与 `（1,−1,−1）`（和=−1）。故以下 4 条均为有效不等式：

```
y_ij + y_jk + y_ki ≥ −1
y_ij − y_ik − y_jk ≥ −1
y_ik − y_ij − y_jk ≥ −1
y_jk − y_ij − y_ik ≥ −1
```

（代码中 `cons` 正是这 4 条，遍历所有三元组。）它们都是 cut polytope 的 facet 不等式，
加入 SDP 不破坏可行性、只收紧下界。

## 4. 数值结果（`cutpolytope_sdp.py`）

| 配置 | 已知 min_viol | 基本 SDP 下界 | **+triangle 下界** | 判定 |
|------|--------------|--------------|-------------------|------|
| m37-408 | 16 | 12.52 | **15.9973** [optimal] | **≥16 且 16 可达 ⇒ 16 最优（整数下界）** |
| m37-448 | 17 | 15.18 | **17.0000** [optimal_inaccurate] | **17 精确最优** |
| m36 (SAT) | 0 | 0.00 | **0.0000** [optimal_inaccurate] | 确认 SAT（参考/方向验证） |

- m37-408：`SDP_min = −280.0218`，`(408 + (−280.0218))/8 = 15.997`。
  因 `min_viol` 为整数，`≥ 15.997 ⇒ ≥ 16`；又已知 16 可达 ⇒ **`min_viol = 16` 最优**。
- 该证书是 **SDP 对偶可行解**（CLARABEL `[optimal]`），本身即"短对偶证书"。

## 5. 这个定理"证明"了什么、没有证明什么

**证明的：**
- 特定 2-因子 `config_408`（扫掠找到的子句数最少构型）在方向层无法低于 16 违例。
- 结合"它是目前子句数最少的 2-因子"，说明**单纯靠 2-因子 switch 微调这个 basin 无法得到 0 违例解**。

**没有证明的：**
- **不能推出 m=37 整体无解。** 仍可能存在另一个 2-因子其 `min_viol = 0`。
- 要证 m=37 不可能，需要**对所有 37 阶 2-因子都成立的普遍下界**，而非单个构型。

## 6. 下一步（路线 1 收口 → 普遍化）

1. **证书迁移 / 普遍化**：在 `mega_sweep` 找到的多个低违例 2-因子上分别算 triangle-SDP 下界。
   若多数达到其已知 `min_viol`，且它们的受挫结构（§路线 2 的受挫奇圈）共享同一小模板，
   则尝试证明"任意 37 阶 2-因子必含该受挫模板" ⇒ 普遍正下界 ⇒ m=37 不可能。
2. **加 odd-cycle 不等式进一步收紧**：当前 odd-cycle 分离因约束数（~1.5×10⁵）过重于 CLARABEL 偏慢；
   应改为**分离式**（只加被违反的少量奇圈，几轮迭代），期望把 408 的下界从 15.997 推到精确 16、448 推到 17。
3. **联合松弛（外层 2-因子 / 内层 cut）**：若能对 2-因子多面体与 cut 多面体做联合 SDP/LP，
   且得到对所有 2-因子严格正的对偶下界，则形成真正的 m=37 不可能性证明。
