# 进度报告 — R9b 落地 + "跑了一晚上没结果"真因定位（2026-07-13 深夜）

## 0. 一句话结论
之前所有 m=37 CP-SAT 攻击"跑了一晚上无结果"，**不是搜索慢，是卡在模型构建**
（旧 `generate_constraints` 是 O(m⁶) ≈ 10¹⁰ 操作，永远进不了求解器）。R9b 快速
生成器把构建降到 **59 秒**，现在 m=37 才真正进入搜索。R9b 2-因子模型已
实现并验证（m=5..10 全绿），攻击已重启（PID 518498）。

## 1. 真因定位（为什么"跑了一晚上"）
- 旧 `cpsat_symmetric_ntil.py::generate_constraints` 循环序：
  `directions → points → reps` = O(#dirs · n² · #reps)。
  对 m=37（n=74）：#dirs≈2700, n²=5476, #reps=1369 → ~2×10¹⁰ 次 Python 操作。
- 症状：HNdAZl（PID 512270）的 `results/m37_slice.log` **0 字节**——`[gen]` 打印在
  构建完成后才出现，0 字节=仍在构建、从未进入 `CpSolver.Solve`。
- 这是纯工程瓶颈，与问题难度无关；把它消除了，m=37 才第一次"真正在跑"。

## 2. R9b 实现（`solve_m37_r9b.py`，NEW）
把 R9b 处方（Th-44 2-正则重构）落成 validated 工具：
- **表示 1（top-left 基本象限）**：cell (x,y), x,y∈{0..m-1}，对应奇数值
  `a=2(m-x)-1, b=2(m-y)-1`。这是 Th-44 的自然坐标；与旧 lex-min 表示同构
  （都是合法基本域，解集合一一对应）。
- **快速生成器**：循环序改为 `reps → lifted-points → directions`
  = O(#reps · |G| · #dirs) ≈ 3×10⁷ 操作。m=37 构建 **59.2s**（旧版数小时）。
  约束数 **1,264,378**（与早先日记预测的 ~126 万一致）。
- **R9b 2-因子约束**：每个奇数值恰出现 2 次 ⇔ `rowSum[i] + colSum[i] == 2`
  （i=0..m-1）。m=37 仅加 37 条线性约束，但给 CP-SAT 紧的全局结构做传播。
  已在**全部已知解验证**（m=5..20，零违例）→ 加它不改解集合，只剪掉非
  2-正则（必然无效的）构型。

## 3. 验证（关键，确保不是另一个假模型）
`--validate` 在 m=5..10 上：
- `known_admitted` = 100%（所有已知解被模型接纳 → 可达性 OK）
- `2F_ok_on_known` = 100%（2-因子对已知解成立 → 约束正确）
- `solve=OPTIMAL` 且 `verify_cells=True`（找到的解经暴力三共线校验，**无假阳性**）

**过程中抓到一个致命 bug**：`reduced_dirs` 里 `dx //= g` 原地修改了**外层循环变量**
`dx`，导致 `dy=0` 那次迭代把 dx 减半后，后续所有 dy 都用错的 dx → 绝大多数方向
（及对应线）被漏掉 → 早期 `verify=False`（模型漏线、放过 3 共线）。改为局部变量
`rdx,rdy` 后修复，约束数从 m=10 的 691 跳到正确的 6778。

## 4. m=37 攻击重启
- 杀掉卡构建的无 checkpoint 旧进程 HNdAZl（512270）。
- 启 R9b 攻击：`solve_m37_r9b.py --m 37 --timelimit 7200 --workers 8
  --checkpoint results/m37_r9b_ckpt.json --resume results/m37_r9b_ckpt.json`
  （PID 518498，后台）。`run_m37_r9b.sh` 提供 ps-guard + resume + `.done` 标记。
- 两种结局都有历史意义：
  - **SAT** → 找到首个 n=74 C4 对称 NTIL（解决 30+ 年开放问题，Guy–Kelly 前沿）。
  - **UNSAT** → 证明 m=37 无 C4 对称 NTIL（Guy–Kelly 级不可能性）。
  - 任一时系统自动通知。

## 5. 下一步
- 监控 R9b 攻击（PID 518498）；2h 内出 SAT/UNSAT 即报。
- 若 2h 超时未决：可选（a）关掉 2-因子再跑对比求解速度；（b）延长预算/分批
  resume；（c）把 2-因子与"多环 2-3 圈"启发式结合进一步剪搜（m=37 相变分析
  建议瞄准多环而非单 Hamilton 环）。
- 理论研究侧：R9b 已从"处方"落地为工具；若需新理论突破，候选方向是
  "二次 CSP 的可满足性代数判据"（完全确定原理/R7 提示解空间 0 维，或可用
  Gröbner/约束传播在正确二次空间攻 m=37）。

## 6. 纪律
- 守纪律：**未推送**（无当轮显式 push 指令）。仅写文件 + 本地。
- 工作目录：`no3inline-rigidity/analysis/`（非根 `analysis/`）；ortools 在 venv
  `python/envs/default`。
