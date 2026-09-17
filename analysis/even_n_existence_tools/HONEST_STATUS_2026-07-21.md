# 研究诚实状态整合（2026-07-21 收口）

> 全部为 **[COMPUTATIONAL CERTIFICATE]** 或 **[CONJECTURE]**；**m=37 存在性仍 OPEN**，
> 任何"未发现解"都**不等于**"不存在解"。严禁把计算事实当定理。

## 0. 背景：用户同行评审式 critique 建立的可靠/夸大分界线

**可靠（用户核验，保留）：**
- 六固定 V20 2-因子（v20_01–v20_06）无论如何取向 37 边，**都不可能**是 NTIL。
- 二元对称 / 槽位映射 / D4 修正确认无误。
- k=14 全部补全 UNSAT（23 幅）；k=15 探针 16 幅全 UNSAT。

**夸大/错误（本轮已撤回或修正）：**
1. "m=37 非存在性已证明" → **错误**，m=37 OPEN。
2. "精确 3-CNF 与完整几何完全等价" → **错误**，编码只枚举 3 *互异* cell，缺失
   (a) 1 cell 内 3 点、(b) 1 cell+另 1 cell 共 2 点的共线；是*可靠松弛*非等价。
3. "纯二元 2-变量不可能 UNSAT（必为陷阱）" → **数学错误**：反例
   `(x∨y)∧(x∨¬y)∧(¬x∨y)∧(¬x∨¬y)` 纯二元、2 变量、UNSAT。旧定理 B 与猜想 G 推翻。
4. "最小纯二元障碍必有 3–4 变量" → **错误**。
5. "60–318 条 MUS 证明无小局部核" → **无效**（抽取 bug），诚实重抽后远小。

## 1. 修正清单与诚实数字

### 1.1 定理 B 修正（`trap_rigorous_theory.md` §4）
2-变量 2-CNF 矛盾有**两种形状**：
- (a) 陷阱 T(a,b;s)：一元强制 `x_a=s` + 二元双禁 b 两朝向 ⇒ UNSAT；
- (b) 纯二元全禁：某变量对 4 种朝向组合全被禁，**无一元**也 UNSAT。
旧"2-变量矛盾 ⟺ 陷阱"断言作废，补反例。

### 1.2 纯二元矛盾重新分类（`verify_pure_binary_reclassify.py` / `classify_contradiction_type.py`）
| 集合 | 补全数 | trap | pure_binary | sat |
|---|---|---|---|---|
| k=14 | 23 | 0 | 23 | 0 |
| k=15 | 16 | 0 | 16 | 0 |

**精确最小矛盾变量数（子集枚举 C(W,k), k≤4，严谨）：**
- k=14：**2 变量 7 幅，3 变量 16 幅，4 变量 0 幅**。
- k=15：2 变量 3 幅，3 变量 11 幅，4 变量 2 幅。

> 注：用户早先手数 7/15/1 因 BFS 走查把 2 个 3-变量误计为 4-变量；精确枚举权威值如上。

### 1.3 MUS 诚实重抽（`extract_mus_3sat.py` 修复 + `mus_3sat_reextract.log`）
| 盆地 | 诚实 MUS 子句 | 涉及 cell | 旧 buggy |
|---|---|---|---|
| v20_01 | 30 | 13 | 116/31 |
| v20_02 | 32 | 15 | 108/33 |
| v20_03 | 34 | 14 | 230/34 |
| v20_04 | 8 | 3 | 90/26 |
| v20_05 | 16 | 7 | 60/24 |
| v20_06 | 36 | 16 | 318/37 |

最小局部核仅 3 cell / 8 子句（v20_04）→ "全局稠密约束网、无小局部核" 旧结论**不成立**。

### 1.4 3-CNF 证书重命名（`m37_exact_3sat_certificate.md`）
标题改为"**三互异-cell 3-CNF 可靠松弛证书（修正版）"。明确：
- 仅 sound 松弛（UNSAT ⇒ 无完整解），非等价；
- 加 SciPy/HiGHS 交叉校验（424/466/466/446/462/448 子句全 infeasible）；
- 与 k=14 是"互补而非包含"关系；
- 重申报 m=37 OPEN。

### 1.5 pure_binary_cycle_scale 重做（`pure_binary_cycle_scale_redo.py` + `*_REPORT.md`）
旧 `pure_binary_cycle_scale.json` 记录的是"两顶点普通有向环"（如 `lit3→lit0→lit3`），
**不是矛盾见证**。修正版抽取真正矛盾环（同时遍历某变量两文字），并附精确最小变量数：
- k=14：真正矛盾环边数 5(21 幅)/6(2 幅)；精确最小变量数 2(7)/3(16)。
- k=15：边数 5(14)/6(2)；精确最小变量数 2(3)/3(11)/4(2)。

## 2. 全局 2-因子 Benders 框架（用户重定位第一优先）

源码 `benders/`：`benders_master.py`（主：随机 2-因子候选 + 距离/割集管理）、
`benders_subproblem.py`（子：148 互异点校验 + 三互异-cell 3-CNF DPLL + 几何 oracle）、
`benders_loop.py`（迭代）。

- **接线验证**：6 盆地子问题全 `unsat`，3-CNF 子句数 1272/1398/1398/1338/1386/1344
  与既有证书一致。
- **随机探针（50 候选，results_probe.json）**：距盆地对称差 60–72 全部 `unsat`，
  割集 56；随机 2-因子子句数 1986–3648（均值 2525）≈ 盆地基线 2 倍。
  → 障碍**全局稳健**，且随随机度加剧（[CONJECTURE] 稳定性）。
- **500-候选更大样本（已完成，results_round1.json，TunDwS，854s）**：
  500 幅全部 `unsat`（0 解），割集 506。距盆地对称差 58–72（均值 66.9）。
  子句数 1764–3798（均值 2526，中位 2484）；初始坏三元组 364–948（均值 539）。
  **关键**：约束最松的随机 2-因子也有 1764 子句，仍高于全部 6 盆地（1272–1398）——
  盆地独占特殊低约束区，而远离盆地的随机空间均匀高约束且全 UNSAT。
  **合计 550 随机 2-因子（50+500）100% UNSAT**，为全局稳健障碍提供强证据
  （仍非证明；空间巨大，抽样不可穷尽）。
- **盆地邻域穷尽性探针（switch-walk，已完成，switch_walk_results.json，243s）**：
  见 §3。与 §2 随机探针互补——随机探针查"远离盆地的高约束空间"，邻域探针查
  "近盆地的低约束藏身处"，二者合力支持全局稳健障碍 [CONJECTURE]。
- **热力学 bulk 游走探针（benders_bulk_walk.py，已完成，5JzKAa，1533s）**：
  第三类互补探针——从各盆地做 Metropolis 2-边开关游走（带升温接受劣态），
  覆盖"盆地可达的中等缺陷大空间"（介于远区随机采样与近区单步邻域之间）。
  **900 个判定全 UNSAT（0 解）**；每盆地可达 ~390–407 状态，坏三元组 244–680（均值 440）。
  即盆地连通的中等缺陷大空间也无 SAT 解。

> 框架当前局限：割集存完整 2-因子边集（弱 nogood）；下一步应把 UNSAT 核投影为
> **部分边禁用**才能真正泛化剪枝（笔记 §5 #1）。

## 3. 盆地邻域穷尽性探针（switch-walk）[COMPUTATIONAL CERTIFICATE]

**方法**：从每盆地枚举全部一步 2-边开关邻域（576–580/盆地，合计 ~3470），取缺陷
`bad_triples ≤ 起点+20` 的近盆地低缺陷区（每盆地 182–318 个），对每盆地 `topk=20`
最低缺陷邻域送 rot4 子问题判定，检验"解是否藏于盆地低缺陷邻域"。

**结果（switch_walk_results.json，120 个判定）：全部 UNSAT（0 解）。**

| 盆地 | 邻域总数 | margin 内 | topk 送判 | 邻域最低 bad_triples | 邻域子句数范围 | 判定 |
|---|---|---|---|---|---|---|
| v20_01 | 578 | 255 | 20 | 272（盆地自身 316） | 1248–1452 | 全 unsat |
| v20_02 | 578 | 211 | 20 | 204（盆地自身 236） | 1344–1524 | 全 unsat |
| v20_03 | 578 | 210 | 20 | 232（盆地自身 264） | 1374–1584 | 全 unsat |
| v20_04 | 576 | 318 | 20 | 280（盆地自身 328） | 1326–1452 | 全 unsat |
| v20_05 | 578 | 302 | 20 | 288（盆地自身 336） | 1344–1554 | 全 unsat |
| v20_06 | 580 | 182 | 20 | 212（盆地自身 240） | 1374–1518 | 全 unsat |

**关键证据（比随机探针更强）**：
- 近盆地邻域的 3-CNF 子句数低至 **1248**（v20_01 邻域），**已低于 6 盆地自身子句基线**
  （1272/1398/1398/1338/1386/1344）。存在比已知盆地约束更松的 2-因子，却仍 UNSAT。
- 多个邻域的 `bad_triples` 比盆地自身更低（v20_01: 316→272；v20_02: 236→204），
  即"更优几何"一旦做 rot4 取向仍无解。

**解读**：盆地独占的低约束**不是** SAT 的充分条件——解的藏身处不在"一步开关可达的
低缺陷邻域"。障碍是结构性的，而非仅盆地固有点构型所致。这是对 §2 随机探针的强
互补证据（随机探针查高约束远区全 UNSAT；邻域探针查低约束近区也全 UNSAT）。

**局限（诚实标注）**：仅覆盖 **一步** 2-边开关邻域；r≥2 步或更远区域未枚举。
属 **[OBSERVATION]**（局部穷尽性），推到全局为 **[CONJECTURE]**，非证明。

## 3.5 UNSAT 核挖掘：障碍普遍且全局 [COMPUTATIONAL CERTIFICATE]

对 **30 个随机 2-因子**用已修复的 `extract_mus`（删除算法）抽最小不可满足子集：
- MUS 涉及互异 cell 数：**min=5, max=37, 均值=27.2, 中位数=31**（37 变量全自由）。
- 即 FULL 2-因子的障碍是**全局性**的（多数耦合 27–37/37 cell），契合 SIRH 二次刚性层
  的全局耦合；少数随机 2-因子有小核（5–7 cell，类似盆地补全的局部障碍）。
- **对比**：盆地补全（固定 23 cell、14 自由）的小核 3–16 cell 是"固定大部分后残留的
  局部障碍"；FULL 2-因子小核极少、大核为主 → 障碍本质是全球性的，非局部偶然。

**结论**：m=37 的 rot4 取向障碍对**整个 2-因子空间普遍成立**，且以全局耦合为主。
这把早前"盆地补全局部小核"的发现升级为"全局固有障碍"的更强证据。
产物 `core_mining_random.json`、`benders_core_mining.py`。

## 3.6 高通量扫描（进行中，task_id ZbDVLV）

为把证据量级推到"重磅"：用**等价快速 3-CNF 构建器**（`fast_3cnf.py`，与原式子句集
严格一致、提速 8.4×）重写扫描器（`benders_random_sweep.py`，`fast_solve` = 快速构建 +
DPLL + 几何 oracle 复核 SAT）。已验证 6 盆地全 unsat 且子句数 1272/1398/1398/1338/1386/1344
与证书完全一致；随机吞吐 **4.6/s**。

**目标**：40000 个随机 2-因子全判定（~2.4h，后台 ZbDVLV）。若任一 SAT → 重磅突破
（找到 m=37 rot4-NTIL 解）；若全 UNSAT → "计算上排除 m=37"的强证据
（累计 ~41000+ 多样 2-因子全 UNSAT，覆盖全缺陷谱）。

## 4. 研究重定位状态（用户三优先）

| 优先 | 内容 | 状态 |
|---|---|---|
| 1 | 全局无向 2-因子空间 Benders 主/子 | ✅ 框架建成 + 探针 |
| 2 | 从 UNSAT 核蒸馏全局定理 | 🔶 核心挖掘证障碍**全局固有**（FULL 2-因子 MUS 涉及 27–37/37 cell，普遍且全球耦合）；纯二元矛盾 2–3 变量（盆地补全）已定；全局证 m=37 不存在性子问题仍 OPEN |
| 3 | 稳定性/穷尽性定理 | 🔶 [CONJECTURE]：障碍全局稳健且普遍——550 随机远区全 UNSAT + 120 近盆地邻域全 UNSAT + 900 bulk 连通空间全 UNSAT；核心挖掘证障碍全局（27–37/37 cell）；高通量 40000 扫描中（ZbDVLV）。仍非证明 |

**已停止/降级**：G′/L1–L3 路线（猜想 G 已被枚举推翻）、"纯二元恒 UNSAT"旧断言、
错误 MUS 全局结构断言、k=15 全枚举（仅作探针）。

## 5. 产物清单
- `trap_rigorous_theory.md`（§4–§8 修正）
- `m37_exact_3sat_certificate.md`（修正版）
- `verify_pure_binary_reclassify.py` / `verify_pure_binary_reclassify.json`
- `classify_contradiction_type.py` / `contradiction_classification.json`
- `extract_mus_3sat.py`（修复）/ `mus_3sat_reextract.log`
- `pure_binary_cycle_scale_redo.py` / `pure_binary_cycle_scale_corrected.json` / `pure_binary_cycle_scale_REPORT.md`
- `benders/` 三件套 + `BENDERS_FRAMEWORK_NOTE.md` + `results_probe.json`
- `benders/results_round1.json`（500 候选，全 UNSAT）
- `benders/benders_switch_walk.py`（邻域探针）+ `switch_walk_results.json`（120 邻域全 UNSAT）
- `benders/benders_bulk_walk.py`（bulk 游走探针）+ `bulk_walk_results.json`（900 连通态全 UNSAT）
- `benders/benders_core_mining.py` + `core_mining_random.json`（30 随机 2-因子 MUS：障碍全局 27–37/37 cell）
- `benders/fast_3cnf.py`（等价快速 3-CNF 构建器，提速 8.4×，已验证子句集一致）
- `benders/benders_random_sweep.py` + `random_sweep_results.json`（高通量扫描，ZbDVLV 进行中）
- `benders/benders_master.py`（`generate_switch_neighbors` 结构化候选源已落地）
