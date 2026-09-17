# m=37 距离 6 分区精确枚举结果

时间：2026-07-17（Asia/Shanghai）

源研究目录保持只读；程序与结果均位于独立工作空间。

## 结论

`v40_02` 十三边硬邻域的距离 6 已完整闭合：

```text
原始允许匹配：9395970
FDR 可行匹配：10089
唯一匹配数：10089
精确取向子问题：10089 个 OPTIMAL
最低真实几何缺陷：56
目标 36：不存在
```

结合已经闭合的距离 2--5：

```text
d=2:   12 个，最低 64
d=3:   42 个，最低 56
d=4:  278 个，最低 60
d=5: 1679 个，最低 56
d=6:10089 个，最低 56
```

距离 2--6 合计 12100 个 FDR 可行替代匹配，全部严格高于原构型的 40。

因此得到新的严格必要条件：

> 这个十三边邻域里的任何 36，必须至少更换 7 条原匹配边，即最多保留 6 条。

## 分区方法

选择受影响端点 1。它有 25 条允许搭档边，按排序后的搭档边轮转分为 8 组：

```text
group i = partner_edges[i::8]
```

每个匹配在端点 1 上恰好选择一个搭档，因此八组互斥且完整。程序对每组加入：

```text
该组中的有向单元选择和 = 1
```

正确性先在距离 2 上交叉验证：八分区合计恰好 12 个匹配，目标分布与原未分区完整枚举完全一致。

## 八个距离 6 分区

| 分区 | 端点1的搭档组 | FDR可行匹配 | 最低值 | 状态 | 时间 |
|---:|---|---:|---:|---|---:|
| 0 | 2, 12, 22, 35 | 736 | 60 | INFEASIBLE闭合 | 128.354秒 |
| 1 | 3, 13, 24 | 759 | 56 | INFEASIBLE闭合 | 133.876秒 |
| 2 | 4, 14, 25 | 1112 | 68 | INFEASIBLE闭合 | 196.398秒 |
| 3 | 5, 16, 27 | 561 | 60 | INFEASIBLE闭合 | 98.348秒 |
| 4 | 6, 17, 28 | 322 | 72 | INFEASIBLE闭合 | 54.992秒 |
| 5 | 8, 19, 29 | 6182 | 60 | INFEASIBLE闭合 | 1712.260秒 |
| 6 | 9, 20, 33 | 417 | 68 | INFEASIBLE闭合 | 63.833秒 |
| 7 | 10, 21, 34 | 0 | — | INFEASIBLE闭合 | 0.004秒 |

分区 5 包含原匹配边 `(1,19)`，因此远大于其他分区。这说明后续距离 7 若继续计算，应把“保留原搭档”单独拿出并按第二端点再次分区。

## 目标分布底部

```text
56×1
60×6
64×4
68×15
72×17
76×80
80×114
84×228
```

最低 56 只出现一次。汇总 JSON 保存了这个匹配的完整边、取向和独立几何复核结果。

## 时间

硬件为 Ryzen 5 7600X，同时保留源端 `mega_sweep_escape.py` 运行。

- 每次并行两个分区；
- 每个分区使用 3 个 CP-SAT worker；
- 八个分区内部耗时之和约 39.8 分钟；
- 四批并行的实际墙钟约 35.2 分钟；
- 主要时间集中在分区 5。

## 复现命令

每个分区的基本命令为：

```powershell
$py = 'C:\Users\djr82\.workbuddy\binaries\python\envs\ntilsat\Scripts\python.exe'

& $py matching_master_enumerate.py `
  --distance 6 `
  --partition-parts 8 `
  --partition-index 0 `
  --max-matchings 100000 `
  --master-time-limit 30 `
  --orientation-time-limit 1 `
  --workers 3 `
  --checkpoint-every 100 `
  --out matching_master_distance6_p8_b0.json
```

将 `partition-index` 与输出文件名依次改为 0--7。只有八个输出都满足：

```text
enumeration_closed = true
final_master_status = INFEASIBLE
```

才构成距离 6 的完整闭合。

## 关键文件

- `matching_master_enumerate.py`：新增 `--partition-parts` 与 `--partition-index`。
- `matching_master_distance6_p8_b0.json` 至 `b7.json`：八个完整分区。
- `matching_master_distance6_p8_summary.json`：跨分区去重与统计汇总。
- `distance6_p8_b0.log` 至 `b7.log`：运行日志。

## 下一步

不建议直接沿用相同八分区枚举距离 7，因为“保留原搭档”分区会继续膨胀。更合理的是：

1. 把完整模型的原边保留上界从 7 收紧为 6；
2. 对分区 5 增加第二端点的精确搭档分区；
3. 比较距离 3、5、6 三个唯一的 56 极小匹配，提取共同的 FDR/直线冲突模式；
4. 只有在这些割仍不足时，再启动距离 7 的分层枚举。
