## 三群论与 transposition 地景的三个定理

### 定理 1 (连通性 → 全对称群)

**命题** [THEOREM, 计算验证]：bitrev 和 gray 的 Q_k 边 transposition 各自生成 S_n，联合生成 S_n × S_n。

**证明**：
- Q_k 的边 transposition 图是连通的
- 连通图的边 transposition 生成全对称群（标准群论结果）
- 验证：n=8,16 的 bitrev transposition 图连通分量数 = 1 ✅

**推论**：从任意初始排列对 (p0,p1)，存在 transposition 序列到达任意目标排列对。

---

### 定理 2 (地景 favorability)

**命题** [COMPUTATIONAL CERTIFICATE]：bitrev+gray 的 transposition 改善率约 83%。

| n | base collisions | improving tps | neutral | worsening |
|---|----------------|---------------|---------|-----------|
| 16 | 93 | 53/64 (82.8%) | 3/64 | 8/64 |

**推论**：随机 transposition 大概率减少碰撞——地景对局部搜索有利。

---

### 定理 3 (次模性不成立 → 贪心受阻)

**命题** [COMPUTATIONAL CERTIFICATE]：碰撞函数的 transposition 边际满足次模性的概率约 48%。

| n | 次模成立 | 违反幅度 (avg) |
|---|---------|---------------|
| 8 | 48% | 6.9 |
| 16 | 42% | 2.9 |

**推论**：贪心单步前瞻的边际估计错误率 >50%，导致"地板效应"——所有单 transposition 改善被局部耗尽后仍远未达 NTIL。

---

### "地板效应"的几何本质

**发现**：地板状态下的残存冲突是"索引空间共线"——特定行三元组的 x 坐标固有共线，无论怎样重排可用 y 值都无法避免。

例 (n=8)：行 (0,2,4) 在 SSS 和 SPS 类型下均共线——x 间距 (2,4) 与可用 y 值集合 {0,3,6}（来自 gray）不可避免产生斜率匹配。

**突破方向**：
1. **SA 接受恶化移动**穿越山脊（当前实现中）
2. **多起点并行**：随机初始化多对排列，SA 并行搜索
3. **3-步前瞻**：在卡住时穷举 3-transposition 序列（8→56³=175K，16→64³=262K）
