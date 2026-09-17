# NTIL 解统一缓存索引

- 格式：每解一个块，`#` 头注释 + 每行 `x y` 一个点
- 主来源：`analysis/flammenkamp_cache/`（Flammenkamp 全枚举数据库）
- 写入解总数：**349840**（flammenkamp 行数 349833）
- 跨源重复组数：423

## 按 (n,对称类) 文件

| 文件 | n | 对称类 | 解数 | 校验通过 |
|------|---|--------|------|----------|
| n2_full.txt | 2 | full | 1 | 1 |
| n3_dia2.txt | 3 | dia2 | 1 | 1 |
| n4_dia2.txt | 4 | dia2 | 1 | 1 |
| n4_full.txt | 4 | full | 1 | 1 |
| n4_ort1.txt | 4 | ort1 | 1 | 1 |
| n4_rot2.txt | 4 | rot2 | 1 | 1 |
| n5_dia1.txt | 5 | dia1 | 2 | 2 |
| n5_iden.txt | 5 | iden | 3 | 3 |
| n6_dia2.txt | 6 | dia2 | 2 | 2 |
| n6_iden.txt | 6 | iden | 4 | 4 |
| n6_rot2.txt | 6 | rot2 | 2 | 2 |
| n6_rot4.txt | 6 | rot4 | 3 | 3 |
| n7_dia1.txt | 7 | dia1 | 1 | 1 |
| n7_iden.txt | 7 | iden | 11 | 11 |
| n7_rot2.txt | 7 | rot2 | 10 | 10 |
| n8_dia1.txt | 8 | dia1 | 5 | 5 |
| n8_iden.txt | 8 | iden | 40 | 40 |
| n8_ort1.txt | 8 | ort1 | 1 | 1 |
| n8_rot2.txt | 8 | rot2 | 7 | 7 |
| n8_rot4.txt | 8 | rot4 | 4 | 4 |
| n9_dia1.txt | 9 | dia1 | 3 | 3 |
| n9_iden.txt | 9 | iden | 41 | 41 |
| n9_rct4.txt | 9 | rct4 | 1 | 1 |
| n9_rot2.txt | 9 | rot2 | 6 | 6 |
| n10_dia1.txt | 10 | dia1 | 3 | 3 |
| n10_dia2.txt | 10 | dia2 | 1 | 1 |
| n10_full.txt | 10 | full | 1 | 1 |
| n10_iden.txt | 10 | iden | 132 | 132 |
| n10_rot2.txt | 10 | rot2 | 13 | 13 |
| n10_rot4.txt | 10 | rot4 | 6 | 6 |
| n11_dia1.txt | 11 | dia1 | 6 | 6 |
| n11_iden.txt | 11 | iden | 122 | 122 |
| n11_rot2.txt | 11 | rot2 | 30 | 30 |
| n12_dia1.txt | 12 | dia1 | 3 | 3 |
| n12_dia2.txt | 12 | dia2 | 2 | 2 |
| n12_iden.txt | 12 | iden | 524 | 524 |
| n12_rot2.txt | 12 | rot2 | 33 | 33 |
| n12_rot4.txt | 12 | rot4 | 4 | 4 |
| n13_dia1.txt | 13 | dia1 | 9 | 9 |
| n13_dia2.txt | 13 | dia2 | 1 | 1 |
| n13_iden.txt | 13 | iden | 407 | 407 |
| n13_rot2.txt | 13 | rot2 | 82 | 82 |
| n14_dia1.txt | 14 | dia1 | 5 | 5 |
| n14_dia2.txt | 14 | dia2 | 3 | 3 |
| n14_iden.txt | 14 | iden | 1284 | 1284 |
| n14_rot2.txt | 14 | rot2 | 61 | 61 |
| n14_rot4.txt | 14 | rot4 | 13 | 13 |
| n15_dia1.txt | 15 | dia1 | 13 | 13 |
| n15_dia2.txt | 15 | dia2 | 1 | 1 |
| n15_iden.txt | 15 | iden | 3681 | 3681 |
| n15_rot2.txt | 15 | rot2 | 283 | 283 |
| n16_dia1.txt | 16 | dia1 | 14 | 14 |
| n16_dia2.txt | 16 | dia2 | 1 | 1 |
| n16_iden.txt | 16 | iden | 5683 | 5683 |
| n16_rot2.txt | 16 | rot2 | 189 | 189 |
| n16_rot4.txt | 16 | rot4 | 13 | 13 |
| n17_dia1.txt | 17 | dia1 | 12 | 12 |
| n17_iden.txt | 17 | iden | 6800 | 6800 |
| n17_rct4.txt | 17 | rct4 | 1 | 1 |
| n17_rot2.txt | 17 | rot2 | 281 | 281 |
| n18_dia1.txt | 18 | dia1 | 14 | 14 |
| n18_dia2.txt | 18 | dia2 | 2 | 2 |
| n18_iden.txt | 18 | iden | 18853 | 18853 |
| n18_rot2.txt | 18 | rot2 | 328 | 328 |
| n18_rot4.txt | 18 | rot4 | 7 | 7 |
| n19_dia1.txt | 19 | dia1 | 16 | 16 |
| n19_iden.txt | 19 | iden | 31967 | 31967 |
| n19_rct4.txt | 19 | rct4 | 2 | 2 |
| n19_rot2.txt | 19 | rot2 | 592 | 592 |
| n20_dia1.txt | 20 | dia1 | 17 | 17 |
| n20_dia2.txt | 20 | dia2 | 2 | 2 |
| n20_iden.txt | 20 | iden | 117347 | 117347 |
| n20_rot2.txt | 20 | rot2 | 675 | 675 |
| n20_rot4.txt | 20 | rot4 | 16 | 16 |
| n21_dia1.txt | 21 | dia1 | 13 | 13 |
| n21_iden.txt | 21 | iden | 142 | 142 |
| n21_rct4.txt | 21 | rct4 | 1 | 1 |
| n21_rot2.txt | 21 | rot2 | 2412 | 2412 |
| n22_dia1.txt | 22 | dia1 | 18 | 18 |
| n22_dia2.txt | 22 | dia2 | 1 | 1 |
| n22_iden.txt | 22 | iden | 2 | 2 |
| n22_rot2.txt | 22 | rot2 | 1248 | 1248 |
| n22_rot4.txt | 22 | rot4 | 8 | 8 |
| n23_dia1.txt | 23 | dia1 | 34 | 34 |
| n23_dia2.txt | 23 | dia2 | 1 | 1 |
| n23_rct4.txt | 23 | rct4 | 1 | 1 |
| n23_rot2.txt | 23 | rot2 | 3967 | 3967 |
| n24_dia1.txt | 24 | dia1 | 43 | 43 |
| n24_dia2.txt | 24 | dia2 | 2 | 2 |
| n24_rot2.txt | 24 | rot2 | 2852 | 2852 |
| n24_rot4.txt | 24 | rot4 | 23 | 23 |
| n25_dia1.txt | 25 | dia1 | 55 | 55 |
| n25_dia2.txt | 25 | dia2 | 2 | 2 |
| n25_rct4.txt | 25 | rct4 | 3 | 3 |
| n25_rot2.txt | 25 | rot2 | 8980 | 8980 |
| n26_dia1.txt | 26 | dia1 | 42 | 42 |
| n26_ort1.txt | 26 | ort1 | 1 | 1 |
| n26_rot2.txt | 26 | rot2 | 4870 | 4870 |
| n26_rot4.txt | 26 | rot4 | 36 | 36 |
| n27_dia1.txt | 27 | dia1 | 44 | 44 |
| n27_iden.txt | 27 | iden | 1 | 1 |
| n27_rct4.txt | 27 | rct4 | 9 | 9 |
| n27_rot2.txt | 27 | rot2 | 17332 | 17332 |
| n28_dia1.txt | 28 | dia1 | 59 | 59 |
| n28_ort1.txt | 28 | ort1 | 1 | 1 |
| n28_rot2.txt | 28 | rot2 | 12085 | 12085 |
| n28_rot4.txt | 28 | rot4 | 60 | 60 |
| n29_dia1.txt | 29 | dia1 | 53 | 53 |
| n29_dia2.txt | 29 | dia2 | 1 | 1 |
| n29_rct4.txt | 29 | rct4 | 8 | 8 |
| n29_rot2.txt | 29 | rot2 | 44828 | 44828 |
| n30_dia1.txt | 30 | dia1 | 88 | 88 |
| n30_dia2.txt | 30 | dia2 | 1 | 1 |
| n30_rot2.txt | 30 | rot2 | 24744 | 24744 |
| n30_rot4.txt | 30 | rot4 | 92 | 92 |
| n31_dia1.txt | 31 | dia1 | 65 | 65 |
| n31_dia2.txt | 31 | dia2 | 2 | 2 |
| n31_rct4.txt | 31 | rct4 | 5 | 5 |
| n32_dia1.txt | 32 | dia1 | 73 | 73 |
| n32_dia2.txt | 32 | dia2 | 1 | 1 |
| n32_rot4.txt | 32 | rot4 | 101 | 101 |
| n33_rct4.txt | 33 | rct4 | 14 | 14 |
| n33_rot2.txt | 33 | rot2 | 1 | 1 |
| n34_rot4.txt | 34 | rot4 | 172 | 172 |
| n35_dia2.txt | 35 | dia2 | 1 | 1 |
| n35_rct4.txt | 35 | rct4 | 23 | 23 |
| n36_dia2.txt | 36 | dia2 | 1 | 1 |
| n36_rot4.txt | 36 | rot4 | 281 | 281 |
| n37_rct4.txt | 37 | rct4 | 21 | 21 |
| n38_dia2.txt | 38 | dia2 | 1 | 1 |
| n38_rot4.txt | 38 | rot4 | 337 | 337 |
| n39_rct4.txt | 39 | rct4 | 33 | 33 |
| n40_rot4.txt | 40 | rot4 | 541 | 541 |
| n41_rct4.txt | 41 | rct4 | 70 | 70 |
| n42_dia2.txt | 42 | dia2 | 1 | 1 |
| n42_rot4.txt | 42 | rot4 | 746 | 746 |
| n43_rct4.txt | 43 | rct4 | 126 | 126 |
| n44_dia2.txt | 44 | dia2 | 1 | 1 |
| n44_rot4.txt | 44 | rot4 | 2032 | 2032 |
| n45_rct4.txt | 45 | rct4 | 212 | 212 |
| n46_rot4.txt | 46 | rot4 | 1366 | 1366 |
| n47_dia4_odd.txt | 47 | dia4_odd | 1 | 1 |
| n47_rct4.txt | 47 | rct4 | 105 | 105 |
| n48_rot4.txt | 48 | rot4 | 2124 | 2124 |
| n49_rct4.txt | 49 | rct4 | 196 | 196 |
| n50_rot4.txt | 50 | rot4 | 3381 | 3381 |
| n51_rct4.txt | 51 | rct4 | 264 | 264 |
| n52_rot4.txt | 52 | rot4 | 5062 | 5062 |
| n53_rct4.txt | 53 | rct4 | 377 | 377 |
| n54_rot4.txt | 54 | rot4 | 7696 | 7696 |
| n56_rot4.txt | 56 | rot4 | 10441 | 10441 |
| n58_rot4.txt | 58 | rot4 | 19 | 19 |
| n60_rot4.txt | 60 | rot4 | 32 | 32 |
| n61_sporadic.txt | 61 | sporadic | 1 | 1 |
| n62_rot4.txt | 62 | rot4 | 5 | 5 |
| n63_sporadic.txt | 63 | sporadic | 1 | 1 |
| n64_rot4.txt | 64 | rot4 | 25 | 25 |
| n64_sporadic.txt | 64 | sporadic | 1 | 1 |
| n66_rot4.txt | 66 | rot4 | 2 | 2 |
| n66_sporadic.txt | 66 | sporadic | 1 | 1 |
| n68_rot4.txt | 68 | rot4 | 2 | 2 |
| n68_sporadic.txt | 68 | sporadic | 1 | 1 |
| n70_rot4.txt | 70 | rot4 | 1 | 1 |
| n72_rot4.txt | 72 | rot4 | 1 | 1 |
| n74_rot4.txt | 74 | rot4 | 4 | 1 |

## 其他来源 / 备注

- `mvr_cache/*.out`: {'note': 'RLE位图(图示)解码', 'files': 26, 'new_added': 1, 'verdict': '与flammenkamp已收录解等价，仅补入缺失对称类/朝向'}
- `D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\analysis\results\solution_m14_sat.json`: {'note': 'cells_expanded', 'm_claimed': 14, 'n_actual': 28, 'verify': True, 'status': 'verified'}
- `D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\analysis\results\solution_m37_sat.json`: {'note': 'cells_expanded', 'm_claimed': 14, 'n_actual': 28, 'verify': True, 'status': 'verified'}
- `D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\analysis\results\solution_m37_biased.json`: {'note': 'full_points', 'n_actual': 74, 'valid_flag': False, 'RETRACTED': True, 'status': 'false-positive'}
- `D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\analysis\results\solution_m37_unbiased.json`: {'note': 'full_points', 'n_actual': 74, 'valid_flag': False, 'RETRACTED': True, 'status': 'false-positive'}
- `D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\analysis\results\m37_surgery_result_FALSEPOSITIVE.json`: {'note': 'FALSEPOSITIVE_included', 'n_actual': 74, 'status': 'false-positive'}
