# NTIL 解统一缓存（solutions_unified）

把分散、格式各异的 NTIL 解缓存**整合到一个目录、统一成同一种格式**。
由仓库根目录的 `consolidate_solutions.py` 生成（重跑：`python consolidate_solutions.py`）。

## 统一格式

每个 `(n, 对称类)` 来源一个 `.txt` 文件，文件内**每解一个块**：

```
# solution <序号>
# n=<阶> sym=<对称类> status=<状态> source=<原始来源>
# code=<原始编码或可溯源标识>
<x0> <y0>
<x1> <y1>
...
```

- 坐标 `(x,y)` 为 0 起、每行 `x`、列 `y`，每行两个点（行列各恰 2 点）。
- 一个 `.txt` 文件可含多个解块（按 `(n,对称类)` 聚合，避免每解一文件造成
  几十万文件爆炸；例如 `n20_iden.txt` 单文件即 117347 个解）。
- 附带 `index.json`（机器读）与 `INDEX.md`（人读）总索引。

## 已纳入的来源

| 来源 | 说明 | 处理 |
|------|------|------|
| `analysis/flammenkamp_cache/*.`（主缓存） | Flammenkamp 全枚举数据库，base62 紧凑编码 | 逐行解码为坐标 |
| `analysis/flammenkamp_cache/*.few` | 大 n（>62）的同一编码，**扩展字母表**（base62 + 10 个标点 `#$%&@?!()[` 覆盖列值 62..71）| 用 72 字符字母表解码；扩展字符映射由 `learn_few_alphabet.py` 以「NTIL 共线校验」严格反推 |
| `analysis/flammenkamp_cache/*.mvr` | 同一批解的 Mayorga 坐标格式 `(行 列)` 平铺 | 解析坐标对 |
| `analysis/mvr_cache/*.out` | Mayorga **Life RLE 位图**（用户所称「图示」形式）| RLE 解码为坐标；与已收录解 D4 归一化去重，**仅补入 flammenkamp 缺失者** |
| `analysis/results/n74_rot4_prellberg_verified_2026-07-22.md` | Prellberg 2026-07-20 的 n=74 rot4 解 | 解析 `行: c1,c2` 块 |
| `analysis/results/solution_m14_sat.json` / `solution_m37_sat.json` | C4 轨道 `cells` | 展开 4 点/轨道 |
| `analysis/results/*FALSEPOSITIVE*.json` 与 `solution_m37_{biased,unbiased}.json` | 已知假阳性（已 RETRACTED） | 展开/直取坐标，**标 `false-positive`** |

## 校验状态标签

- `verified`：解码/展开后通过 NTIL 校验（无三点共线、每行列恰 2 点、点数=2n）。
  - 主缓存：所有解做轻量结构校验（边界+行列度），并对每文件抽样做完整共线校验
    确认来源完整性（来源为权威数据库，已抽样验证）。
  - 研究解/FALSEPOSITIVE：数量少，做**完整**共线校验。
- `false-positive`：源声称是解，但校验发现共线（脏数据，已标脏保留以便追溯）。
- `mixed`：某 `(n,sym)` 文件内混有 `false-positive`（目前仅 `n74_rot4.txt`：
  Prellberg 真解 + 1 个 FALSEPOSITIVE）。

## 已知缺口（已补全）

原 `flammenkamp_cache/` 中 **5 个大 n 的 `.few` 文件**曾无法解码：

- `n64_rot4.few`(25 行)、`n66_rot4.few`(2)、`n68_rot4.few`(2)、`n70_rot4.few`(1)、`n72_rot4.few`(1)，合计 **31 行**，
  是这些 n 的 rot4 解**唯一**来源（主缓存无对应 `nXX_rot4`）。
- 它们并非「无解码器」：n>62 时列值 0..71 超出 base62（0..61），Flammenkamp 用 base62
  再加 10 个标点字符（`#$%&@?!()[`）构成 **72 字符扩展字母表**。映射顺序由
  `learn_few_alphabet.py` 以「每个解必须无三点共线」逐 n 反推并跨文件交叉验证确定。
- **现已全部解码并并入**（233 个 `.few` 行 0 非法）。这是偶数 n 解集合的真正缺口补全
  （n=64..72 的 rot4 现齐备）。

## mvr `*.out`（图示）冗余性结论

`mvr_cache/*.out` 是 **Life RLE 位图**（图示）形式的同一批解。逐文件 RLE 解码后，
与已收录的 flammenkamp 解做 **D4 归一化（8 种旋转/反射）比对**结论：

- 25 个文件、共 **85,724** 个解，归一化后与 flammenkamp 已收录解**完全等价**
  （交集=全集），**仅 `d4odd-47.out` 的 1 个解**（dia4-odd 对称类，奇数 n=47）是
  flammenkamp 缓存缺失的，已补入（`n47_dia4_odd.txt`）。
- 因此 mvr `*.out` 不增加偶数 n 解的完备性，只是同一批解的独立位图来源；
  合并脚本已用 D4 去重，避免把同解的不同朝向当作新解。

## 统计（生成时）

- 写入解总数：**349,840**（flammenkamp 行 349,833 + mvr 图示补入 1 + 研究/n74/FALSEPOSITIVE 6）
- 输出文件数：165
- 跨源重复组：423（`.mvr`/`.out` 与主缓存大量重叠，证实是同批解的不同编码）

## 注意

- 本目录含约 35 万个解、体积较大，**不建议直接 `git add`** 进仓库。
  应纳入版本控制的只是生成器 `consolidate_solutions.py` 与 `index.json`/`INDEX.md`；
  若需分发解数据，建议压缩或按需生成。
- `analysis/even_n_existence_tools/`（旧副本）、`analysis/results/` 内纯统计 JSON
  （如 `known_solutions_vectors.json`、`mine_solution_essence.json`）**不含坐标**，
  已正确排除。
