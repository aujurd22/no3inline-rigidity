  m= 5 nsol=  6 cells=  30 diag_frac=0.067 peak_angle=30°(6)
  m= 6 nsol=  4 cells=  24 diag_frac=0.125 peak_angle=18°(3)
  m= 7 nsol= 13 cells=  91 diag_frac=0.033 peak_angle=8°(7)
  m= 8 nsol= 13 cells= 104 diag_frac=0.058 peak_angle=30°(9)
  m= 9 nsol=  7 cells=  63 diag_frac=0.048 peak_angle=22°(4)
  m=10 nsol= 16 cells= 160 diag_frac=0.044 peak_angle=16°(9)
  m=11 nsol=  8 cells=  88 diag_frac=0.045 peak_angle=35°(6)
  m=12 nsol= 23 cells= 276 diag_frac=0.014 peak_angle=86°(13)
  m=13 nsol= 36 cells= 468 diag_frac=0.034 peak_angle=47°(20)
  m=14 nsol= 58 cells= 812 diag_frac=0.039 peak_angle=42°(33)
  m=15 nsol= 92 cells=1380 diag_frac=0.026 peak_angle=42°(64)
  m=16 nsol=101 cells=1616 diag_frac=0.028 peak_angle=47°(51)
  m=17 nsol=172 cells=2924 diag_frac=0.028 peak_angle=45°(83)
  m=18 nsol=281 cells=5058 diag_frac=0.029 peak_angle=45°(147)
  m=19 nsol=337 cells=6403 diag_frac=0.026 peak_angle=45°(169)
  m=36 nsol=  1 cells=  36 diag_frac=0.000 peak_angle=56°(3)

## 1. 极角分布 (mod 90°) -- 全局
- 总 cell 采样: 19533
- 均匀期望/桶: 217.0
- 最大桶偏差: 343.0 (158.0% of mean)
- theta=45°(对角)桶: 560  vs 均匀期望: 217.0  -> 比 = 2.580
- 近轴窗口(1-3°,86-88°)均/桶: 232.3  -> 对角/近轴 = 2.410
- Top-5 角度峰: 45°(560), 71°(477), 30°(430), 42°(402), 47°(401)

## 2. 半径壳层 (归一化 R/(m√2))
- 归一化半径分 20 桶, 非空桶: 19/20
- 半径分布(每桶占比): 0 1 2 3 3 5 5 6 7 7 9 9 10 10 8 5 4 3 2 0
- 半径空隙区间(归一化): [(0.95, 1.0)]

## 3. 包络形状 (|Y|≤R 三角是否被填满)
- m=16 代表解: 平均每层 Y 覆盖 [-R,R] 比例 = 0.898
  (1.0=满三角/角均匀; 越小=角聚集越严重)

## 4. 跨解壳层一致性 (同一 m 不同解是否共享 (R,theta) 壳)
- m=8: nsol=13, 总壳数=43, 全解共有壳=0, ≥80%解共有壳=0
- m=12: nsol=23, 总壳数=104, 全解共有壳=0, ≥80%解共有壳=0
- m=16: nsol=101, 总壳数=240, 全解共有壳=0, ≥80%解共有壳=0
- m=19: nsol=337, 总壳数=355, 全解共有壳=0, ≥80%解共有壳=0

## 5. 对角 cell 偏好 (theta≈45°)
- m=5: diag_frac=0.067 (2/30)
- m=6: diag_frac=0.125 (3/24)
- m=12: diag_frac=0.014 (4/276)
- m=16: diag_frac=0.028 (45/1616)
- m=19: diag_frac=0.026 (169/6403)
- m=36: diag_frac=0.000 (0/36)
