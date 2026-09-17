# 求解器验证链报告 [COMPUTATIONAL CERTIFICATE]

- 结论：**SOLVER_CHAIN_TRUSTWORTHY**
- 单测全过：True；6 V20 负例全 UNSAT：True；正例 m=5/10/14/36 全 SAT+几何复核：True

## 负例 (m=37, N=74, 关键回归)
- v20_01: z3=True pysat=True dpll=True (1272 子句) OK
- v20_02: z3=True pysat=True dpll=True (1398 子句) OK
- v20_03: z3=True pysat=True dpll=True (1398 子句) OK
- v20_04: z3=True pysat=True dpll=True (1338 子句) OK
- v20_05: z3=True pysat=True dpll=True (1386 子句) OK
- v20_06: z3=True pysat=True dpll=True (1344 子句) OK

## 正例
- m=5: z3=False pysat=False dpll=False npts=20 bad_triples=0 src=balanced_cpsat_m5_m6.run0 OK
- m=10: z3=False pysat=False dpll=False npts=40 bad_triples=0 src=rot4_loader.load_rot4(n=20) OK
- m=14: z3=False pysat=False dpll=False npts=56 bad_triples=0 src=rot4_loader.load_rot4(n=28) OK
- m=36: z3=False pysat=False dpll=False npts=144 bad_triples=0 src=n72_new_sol_1.json OK
