# GPU 并行工具 + AI 启发式（2026-07-13 晚）

用户要求：① 并行搞一个 GPU 工具；② 试 AI 启发式。约束：任何运行 ≤20 分钟。

## 1. GPU 工具：环境卡点 + 源码已就绪

- **环境**：本机有 NVIDIA RTX 4070 SUPER + CUDA 13.3 工具链（`nvcc` 可用）。
- **卡点**：`nvcc` 在 Windows 上需要 MSVC 的 `cl.exe` 作主机编译器，而本机只装了 VS Installer、未装 C++ 工作负载 → `nvcc fatal: Cannot find compiler 'cl.exe'`。因此 **CUDA 内核无法在本机编译运行**。
- **处置**：写了 `csearch_cuda.cu`（GPU 并行 SA：每 CUDA 线程一条独立 SA 链，每链一个局部哈希表增量算共线目标，host 循环多次发射核函数、回拷 best_bad、检测 0）。逻辑是已验证的 CPU `csearch2` 的逐行移植，**日后装好 MSVC Build Tools 即可 `nvcc -O3 -arch=sm_89 csearch_cuda.cu -o csearch_cuda.exe` 直接跑**。本机当前用 CPU 并行 harness 替代（见下）。
- 若用户要真·GPU，选项：(a) 我安装 VS C++ 工作负载（大下载，需授权）；(b) 你在别的带 MSVC 的机器上编译 `csearch_cuda.cu`。

## 2. 并行工具（CPU 多核，已发射）：`parallel_csearch.py`

- 用 `multiprocessing`/`ThreadPoolExecutor` 起 **N 个独立 `csearch2` worker**，各带独立 `--seed`，整体 **wall-clock 用 `subprocess` timeout 卡死**（默认 540s = 9 分钟，远在 20 分钟红线内）。
- 既支持随机初始化（默认），也支持 `--init-dir` 从给定构型启动（给 AI 启发式用）。
- 每个 worker 跑的是已验证的 `csearch2` SA（同目标、同 3 类 move、同退火表），所以结果可直接信。

## 3. AI 启发式：从已有解学"位置先验"

- 脚本 `ai_gen_inits.py`：
  - 载入 `results/solutions/` 里 m=5..19、m=36 共 17 个**已验证解**（216 个 cell 观测）。
  - 把每个 cell 的位置按 `(x/(m_s-1), y/(m_s-1))` 归一化，池化进 37×37 热度图 → 这就是"好 cell 通常落在基本域哪些区域"的**经验先验**（转移学习：用小 m 的解指导 m=37 的初始化）。
  - 对 m=37 采样 37 个互异 cell，按热度图双线性插值加权接受（带 2% 探索项）→ 生成 12 个**先验初始化**；另生成 12 个**均匀随机初始化**作基线。
- 实验设计（已发射，并发两任务，各 6 worker / 9 分钟，占满 12 核互不超额订阅）：
  - **PRIOR**（`parallel_csearch.py --init-dir results/ai_prior`，task `Ogt3SB`）
  - **RANDOM**（`parallel_csearch.py --init-dir results/ai_random`，task `0OAirx`）
  - 比较两组的 `best_bad` 分布与是否 FOUND → 检验"学出的先验"是否比随机初始化更快逼近解。

## 4. 顺带的重要纠错：m=37 "手术解"是假阳性

- `results/m37_surgery_result.json` 声称 `verify_no_collinear:true`，但用真·验证器 `verify_cells.py` 复核发现 **248 个共线三元组** → m=37 仍未解。
- 根因：`verify_cells.py` 的 `load_cells` 有 bug——`if not cells` 守卫在解析完第一行后 `cells` 已非空，导致后续行全部跳过，最终只验了**第 1 个 cell**（4 点当然无共线）。已用 `(x,y)` 括号单行格式重验确认 248 冲突。
- **后果**：之前任何依赖该弱验证器的"m=37 已解"结论都作废；必须用 `verify_cells.py` 的真·C4 提升复核。这个 bug 是本项目数据陷阱的新成员。

## 5. 状态

- PRIOR / RANDOM 两任务跑满 ~9 分钟，完成后系统会通知，再补 `best_bad` 对比结论。
- 若任一任务 FOUND → 直接拿到 m=37 解（构造即证书），并用 `verify_cells.py` 复核。

## 附：文件清单

- `csearch_cuda.cu` — GPU 并行 SA 内核（待 MSVC 编译）
- `parallel_csearch.py` — CPU 多核并行 harness（已用）
- `ai_gen_inits.py` — AI 先验/随机初始化生成器
- `csearch2.cpp` — 已加 `--init`（从给定构型启动），重编译通过
- `results/ai_prior/`, `results/ai_random/` — 生成的初始化
- `results/ai_prior_result.json` / `ai_random_result.json` — 待产出
