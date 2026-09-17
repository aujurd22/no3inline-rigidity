# m=37 R9b 攻击：根因定位与修复（presolve 无上限卡死）

**时间**：2026-07-13 深夜（延续 R9b 攻击）
**结论**：之前「跑了一晚上无结果」的真正原因已定位并修复。现在 m=37 真正进入可观测、可复活、有实时 checkpoint 的求解阶段。

---

## 1. 根因（为什么之前无结果）

不是搜索慢，而是 **ortools presolve（预处理）阶段不受 `max_time_in_seconds` 约束**。

- 模型规模：m=37 → `reps=1369` 个基本象限格，`line_cons=1,264,378` 条 per-line 加权 at-most-2 约束（R8/SIRH Part III 的精确编码）。
- 旧代码：`solver.parameters.max_time_in_seconds = 7200` 只约束**搜索阶段**，**不约束 presolve 阶段**。
- 1.26M 约束的模型 presolve 可能跑数小时乃至卡死，`solver.Solve()` 永不返回 → 日志永远停在 `[gen] build=58s`，无 `[solve]` 行、无 checkpoint、无 `.done`。
- **旧进程 518498 实际一直存活**（被误判为死，是 Git Bash 下 `ps -o -p` 的假阴性；经 `kill -0` 成功 + `/proc/518498` 存在确认），卡在 presolve 长达 8h53m，做无用功。

## 2. 修复（4 处）

1. **presolve 上限**：`solve_ortools` 加 `solver.parameters.max_presolve_iterations = 3`
   → 保证 `Solve()` 必在 `(presolve + timelimit)` 内返回，2h 后一定出阶段性结论。
2. **构建进度 + solve 起点标记**：`[build] per-line k/N (Ts)` 每 20 万条打印；`[build] model complete`；`[solve] start ...` → 卡点可定位（build 还是 solve）。
3. **实时 checkpoint callback**：注册 `CpSolverSolutionCallback`，每找到一个可行解立即原子写 `results/m37_r9b_ckpt.json` → resume 真正暖启动；即使返回 UNKNOWN（未找到解），也不丢过程中发现的任何可行解。
4. **ps-guard 真判活**：`run_m37_r9b.sh` 的存活检测从 `ps -ef | grep` 改为 `kill -0` 扫描 → 避免僵尸/defunct 进程导致守护脚本误「SKIP」而永不重启。

## 3. 验证

- m=8 冒烟测试（带 checkpoint）：`[gen]→[build]→[solve] start live_ckpt=True→2 solutions live-checkpointed→status=OPTIMAL found=8→verify no-3-collinear=True`。新代码路径全部正常。
- m=37 重启（PID 522008，live）：日志
  ```
  [gen] m=37: reps=1369 line_cons=1264378 2F_on=True build=58.0s
  [build] adding 1264378 per-line constraints...
  [build] per-line ... (3s..16s)
  [build] model complete (16s)
  [solve] start timelimit=7200.0s workers=8 live_ckpt=True
  ```
  → 已真正进入求解阶段。

## 4. 当前状态与韧性

- 进程 PID 522498→（实际 522008）存活，2-因子约束开启，8 并行 worker。
- 守护：`automation-1783904231224`（HOURLY）跑 `run_m37_r9b.sh`；进程死则重启，`.done` 出现即终局。
- 本次自动化已升级：终局（`.done`）出现时通过微信主动通知（见 automation prompt）。

## 5. 预期与下一步

- **≤ 2h10m 内**返回阶段性结论：
  - **SAT** → 首个 n=74 C4-对称 NTIL（解决 30+ 年开放问题）；
  - **UNSAT** → 该类（C4 对称 + 2-因子）的不可能性（Guy–Kelly 量级）；
  - **UNKNOWN**（2h 超时）→ 延长时间预算 / 分批 resume / 关 2-因子对比求解速度 / 结合「多环 2-3 圈」启发式。
- 理论线（SIRH）已在 Part I–IV 收口；本攻击是 R9b（2-正则重构 + 快速编码）的可操作化。
- **纪律**：未收到逐轮显式 push 指令，不 push git。

## 6. 关键文件

- `analysis/solve_m37_r9b.py`（改进：presolve 上限 + 进度 + live checkpoint）
- `analysis/run_m37_r9b.sh`（改进：kill -0 ps-guard）
- `analysis/results/m37_r9b.log`（实时日志）
- `analysis/results/m37_r9b_ckpt.json`（实时 checkpoint）
- `analysis/results/m37_r9b_ckpt.json.done`（终局标记）
