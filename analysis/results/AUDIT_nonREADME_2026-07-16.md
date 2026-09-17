# Audit: 全部未进 README 的内容（Math skill 严格审计）

**开始**: 2026-07-16 | **纪律**: theorem(已证)/conjecture(猜想)/open(开放) 严格区分；硬数字验算；绝不把未证当已证。
**产出**: 本审计报告（不改 README）。每条声明定级 + 证据/反例 + 标错。

## 待审文件清单（pending → done）

| # | 文件 | 大小 | 状态 | 声明数 | 结论摘要 |
|---|------|-----:|:----:|:------:|----------|
| 1 | `alpha_breakthrough.md` | 3220 | done | 4 clauses | ❌ 标题/框架过度声称——"Computational Proof" 应降为 empirical |
| 2 | `audit_report_2026-07-07.md` | 9510 | done | 0 scientific claims | ✅ 元审计文档——不含科学主张，所有发现数据验证 |
| 3 | `audit_report_2026-07-08.md` | 8260 | done | 0 scientific claims | ✅ 元审计文档——D1-D11 错误发现全部数据验证 |
| 4 | `c4_construction_theory.md` | 7850 | done | 3 | **定理2.1(等差圈序障碍) lemma级正确**；Row-Degree定理=Th-44重述；§3经验景观诚实(唯m=6例外)；§4-5诚实标注缺口(无显式构造/无存在性证明)。校准良好。 |
| 5 | `c4_lll.md` | 3230 | done | 4 clauses | ✅ 诚实 LLL 分析——ep(d+1)~m^0.86≫1, 正确结论：朴素概率法失败 |
| 6 | `c4_universality.md` | 6114 | done | 5 clauses | ✅ 典范级自我纠错——发现并修正自身bug，所有null结果诚实报告 |
| 7 | `construction_attempt_2026-07-08.md` | 5135 | done | 0 novel sci claims | ✅ 诚实负结果报告——三种构造法全部失败，正确标级
| 8 | `construction_law_final_2026-07-09.md` | 8420 | done | 5 clauses | ✅ 典范级自纠——相变假说死亡+D₆撤销+n=72过拟合；❌"稀疏化数学排除相变"稍强(含caveat)
| 9 | `container_analysis.md` | 7329 | done | 2 | **§4.1 "Low-Slope Emptiness Theorem" 过度声称：证明草图不够→应降级为empirical**；§1-2 τ计算分析合理但τ>1⇒定理界平凡；§3替代工具评估诚实。其他无伪定理。 |
| 10 | `d6_dominance_correction.md` | 6081 | done | 5 clauses | ✅ 典范级自我纠错——零过度声称，根因透彻 |
| 11 | `data_adequacy_audit_2026-07-09.md` | 9966 | done | 0 sci claims | ✅ 元方法论审计——三个致命统计错误识别正确，所有假说诚实标注置信度
| 12 | `data_catalog.md` | 7730 | done | 0 novel claims | ✅ 纯数据参考，无定理级声称 |
| 13 | `dir2_dir1_analysis.md` | 8986 | done | 5 clauses | ✅ C₂ 定理 proven; ❌"4-染色鸽巢证D(n)=2n"属早期误解(已自行纠正); 环人口≡0 mod4 theorem
| 14 | `direction1_truth_2026-07-09.md` | 4178 | done | 5 clauses | ✅ 诚实报告——所有声称正确标级，无过度声称 |
| 15 | `g_direction_theorems.md` | 4743 | done | 4 clauses | ✅ THEOREM-grade (Th-50方向互斥、Th-51斜率禁令); ❌ 纠正Th-24"低斜率空"错误; 自纠诚实
| 16 | `highdim_projection.md` | 5066 | done | 1 exploratory | ✅ 探索性分析——PCA 发现解空间~1.7n维流形; 诚实标注"≠已找到高维源"
| 17 | `highdim_synthesis_2026-07-09.md` | 6501 | done | 0 theorems | ✅ 撤回自身"1.7n/4×更薄"bug结论；修正后k90≈4n-11n(38-62%)；诚实标注"未发现隐藏分层"
| 18 | `hring_deepening.md` | 4735 | done | 4 clauses | ✅ H_ring深化——≥n环下界紧(46.6%取等号)；C4环结构正确；无过度声称
| 19 | `hypergraph_algebraic_theorem.md` | 17991 | done | 6 clauses | ✅ [P]/[E]/[?] 标记清晰；Th-34 prominently featured as [E] but honest; ❌ Θ(n) gap 虽标 [E] 但 language 偏乐观
| 20 | `hypergraph_framework.md` | 9056 | done | 4 | **定理（Symmetry-Exclusion）**：排除5类(full/rot4/rct4/dia2/ort2)、允许4类(iden/rot2/dia1/ort1非满中心)。轨道环论证正确；335,702解计算检验0不一致。ort1 OPEN 诚实。 |
| 21 | `hypergraph_monograph.md` | 14856 | done | 10 clauses | ✅ 定理/证据标记清晰(C₂、奇偶性=[P]；C₄ Necessity=[E])；无过度声称
| 22 | `hypergraph_multi_family_theorem.md` | 3621 | done | 2 clauses | ✅ THEOREM-grade [P]——√n+O(1)独立集; 行列式证明正确; 剩余gap诚实
| 23 | `hypergraph_theory.md` | 20660 | done | 9 clauses | ✅ §2.1 "|S_D| ≤ 2" 缺证明→downgrade to conjecture |
| 24 | `ising_decomposition_theorem.md` | 4300 | done | 3 clauses | ✅ 分解定理 proven; 路线1/2/3 pending 状态诚实标注; 无伪定理
| 25 | `ising_optimality_proof_m37.md` | 5947 | done | 5 | RIGOROUS+HONEST. 408→16 & 448→17 最优=theorem(整数取整吸收SCS/CLARABEL数值误差);(★)推导正确;诚实说明不能推m=37无解 || — |
| 26 | `ising_reframing_m37.md` | 12051 | done | 9 | 高质量. 化简=theorem(恒等式手验+180°对称closure); 路线1最优theorem; 谱下界弱但有效; §6b 8构型∩=0强证据; §6系列降级更正诚实 || — |
| 27 | `lemmas_c2_ring.md` | 7973 | done | 5 clauses | ✅ THEOREM-grade [P]——C₂定理、环人口≡0 mod4、4-染色; 自纠诚实(环人口"4或8"→"≡0 mod4")
| 28 | `low_slope_parity_theorem.md` | 4783 | done | 2 | **THEOREM-grade**（奇偶律完整证明：偶数n恒空/奇数n显式构造）。奇数n构造对所有n≥5成立。解决container_analysis §4.1问题。模型文档。 |
| 29 | `math_audit_report_final.md` | 3603 | done | 0 sci claims | ✅ 元审计文档——独立验证发现2处轻微偏差(k_max=14非13, Th-18 1反例); 5/6通过
| 30 | `report_best72.md` | 6642 | done | 4 | 诚实经验分析(best72单环+2-switch). 数据正确(470→452); 无伪定理; 但OUTDATED: 先于408/16发现, 'best known=446-448/18'已被config_408(408/16)超越; §5.2 '真最小380-430'臆测(408落区间). |
| 31 | `research_directions_2026-07-09.md` | 17707 | done | 12 clauses | ✅ 策略分析文档; ❌ 撤回事项隐于附录(§1循环普适性§5兼容判断先写后撤); 定理级无问题
| 32 | `results\ai_gpu_parallel_2026-07-13.md` | 4076 | done | 0 theorems | ✅ 诚实进度报告——GPU不可编译, CPU并行已发射; 发现m37手术解假阳性(cells加载bug)
| 33 | `results\burnside_orbit_count.md` | 8876 | done | 2 | ✅ THEOREM-grade——Burnside轨道计数取代之前"28常数"错误声称; 方向键压缩比∼1/4
| 34 | `results\codegree_tail_analysis.md` | 3283 | done | 0 theorems | ✅ 冲突超图分析——co3>0占99.98%配对; 极端尾666对构成匹配; 中等尾143k对巨连通块
| 35 | `results\conflict_hypergraph.md` | 8642 | done | 3 | formulation文档；超图定义正确；(S)二边+(X)三边；参数表数据驱动诚实。
| 36 | `results\costas_32_33_attack.md` | 4723 | done | 0 theorems | ✅ CP-SAT攻击文档——Rickard桥梁密度论证为假; 对称Costas在11/13存在; n=32/33运行中
| 37 | `results\costas_rigidity.md` | 8465 | done | 2 | ✅ 定理文档——FDR→Costas迁移; 正交reflection排除定理; 诚实标为[P]
| 38 | `results\costas_symmetry_theorem.md` | 20379 | done | 7 | ✅ THEOREM-grade [P]——C1-C6+R+C完整D₄分类; 平行四边形象论证明 C6/R; 边缘测试+穷举验证
| 39 | `results\cpsat_encoding.md` | 5195 | done | 0 theorems | ✅ CP-SAT编码文档——1.26M约束数据正确; 无定理声称
| 40 | `results\cpsat_timing_report.md` | 4569 | done | 0 theorems | ✅ 计时表征——m≤16秒级,m≥17进入>120s墙; m=37真实攻击已启动; 诚实说明"求解速度墙≠不存在"
| 41 | `results\direction4_energy_note.md` | 3436 | done | 0 theorems | ✅ 方向④探索笔记——E1-E5候选能量函数; 结论:鸽笼/计数类不适用,代数几何可能仍有希望
| 42 | `results\direction4_formal_complete.md` | 6850 | done | 1 theorem | ✅ E3.1(方向键单射性)=theorem; E4.1(C4-轨道方向键)=theorem; 其余标记为conjecture/experiment; 五条方向最终表诚实
| 43 | `results\direction_classes_findings.md` | 3078 | done | 0 theorems | ✅ 探索报告——方向类分布不能区分真解与随机; 诚实结论"继续找全局签名已被证伪"
| 44 | `results\direction_decisions_2026-07-13.md` | 2417 | done | 0 theorems | ✅ 五条方向可行性裁决——方向③推荐(最高ROI); 方向④长线; 方向①已穷尽暂停
| 45 | `results\extreme_pair_structure.md` | 2048 | done | 0 theorems | ✅ 666转置对codegree分析——co3>800全部转置对; 数据正确
| 46 | `results\fdr_theorem.md` | 11144 | done | 4 | **theorem-grade**；引理A1逐项验算正确；FDR必要律推导sound；分类与实证一致。
| 47 | `results\final_direction_ruling_2026-07-13.md` | 5842 | done | 0 theorems | ✅ 最终裁定——5方向全部FAIL结论数据支持; 无定理声称
| 48 | `results\gpu_findings.md` | 3816 | done | 0 theorems | ✅ GPU矢量扫描——4角度,bad≤200区域0配置; 结论"解是极小孤岛"
| 49 | `results\known_solutions_findings.md` | 2551 | done | 0 theorems | ✅ min|det|=1不变量报告——跨m标度规律数据正确
| 50 | `results\lemma1a_algebraic_proof.md` | 39723 | done | 1 | **❌ Lemma 1a "PROVED" 不成立**。m≥65鸽笼论证sound; 14≤m≤64仅gating采样非证明。
| 51 | `results\lemma1b_proof.md` | 6912 | done | 6 | ✅ HONEST—m≥8 counting proof; m=5-7 empirical gap transparent
| 52 | `results\lll_existence_sketch.md` | 7672 | done | 0 theorems | ✅ 诚实partial proof——对称LLL条件验算正确; 自承不完整
| 53 | `results\m37_quick_solve_assessment.md` | 2767 | done | 0 theorems | ✅ 诚实评估——min|det|=1区分度0%, (X)二次层为真实瓶颈
| 54 | `results\m37_satisfiability_window.md` | 5955 | done | 5 | 诚实间接证据; 乐观结论被SDP证据削弱; §2/§3.4定义不一致
| 55 | `results\mutual_edge_decomposition.md` | 12321 | done | 3 | ✅ THEOREM-grade——MB-1/MB-2引理正确; 几何论证干净
| 56 | `results\nil_researchers_and_difficulty.md` | 6499 | done | 0 theorems | ✅ 文献综述——rot4子问题特殊难度; 7个障碍互相独立
| 57 | `results\paper_draft_sirh.md` | 19742 | done | 8 | ✅ 高质量合成—定理级声明全部正确校准；微瑕：§9 #2 "never correctly implemented" 已过时
| 58 | `results\part4_reverse.md` | 5941 | done | 3 | P4.1 theorem；P4.3 theorem；**P4.2 应降级：依赖empirical常数**
| 59 | `results\progress_2026-07-13.md` | 4899 | done | 0 theorems | ✅ 纯进度笔记——工程瓶颈诚实记录
| 60 | `results\progress_2026-07-13_pm.md` | 4745 | done | 0 theorems | ✅ 纯进度笔记
| 61 | `results\progress_2026-07-13_presolve_fix.md` | 3808 | done | 0 theorems | ✅ 纯进度笔记
| 62 | `results\progress_2026-07-13_r9b.md` | 4143 | done | 0 theorems | ✅ 纯进度笔记
| 63 | `results\progress_2026-07-13_rigorous.md` | 4117 | done | 0 theorems | ✅ 纯进度笔记
| 64 | `results\progress_2026-07-13_theory.md` | 4283 | done | 0 theorems | ✅ 纯进度笔记
| 65 | `results\quadratic_complete_determination.md` | 3311 | done | 1 | ⚠️ **"定理（完全确定）"标为定理但证据仅为实验测量(m=5..36已知解观测)，非解析证明。应降级为empirical**
| 66 | `results\quadratic_gap_theorem.md` | 5251 | done | 1 | ✅ THEOREM-grade——Sidon不足证明; sympy代数证明, 不可约+显式见证
| 67 | `results\quadratic_sidon_completeness.md` | 8388 | done | 4 | **theorem-grade (R8)**；(X)∧(S)⇔rot4 NTIL; 93解+7500模板校验
| 68 | `results\r8_generalized.md` | 8214 | done | 3 | **theorem-grade (R8-G)**；per-line加权≤2⇔G-对称NTIL; 45/45校验
| 69 | `results\r8_minimal_csp.md` | 5872 | done | 0 theorems | ✅ R8约束计数文档——m²二进制变量+三层约束; 数据正确
| 70 | `results\r8_proof.md` | 7819 | done | 3 | **rigorous theorem**；(⇐)案例A/B/C穷举逻辑完美; (⇒)trivial; 自纠诚实体面
| 71 | `results\r8g_algebraic_proof.md` | 4437 | done | 0 theorems | ✅ 评估文档——轨道方法仅常数压缩非渐近; 诚实评估
| 72 | `results\r9_modp_descent.md` | 5085 | done | 2 | **R9a corrected lemma** (p>2m必有) theorem级; R9b=Th-44重述
| 73 | `results\radial_occupancy_analysis.md` | 1622 | done | 0 theorems | ✅ 纯数据报告——环占用4/8/12统计
| 74 | `results\research_A.md` | 7097 | done | 0 theorems | ✅ 研究笔记——LLL紧边界分析; Lemma B.1失败正确标注
| 75 | `results\research_B.md` | 7734 | done | 0 theorems | ✅ 研究笔记——Lemma B.1明确RETRACTED(ep(d+1)=7.8e2≫1)
| 76 | `results\research_C.md` | 6389 | done | 0 theorems | ✅ 研究笔记——9类不变性清查全不阻碍m=37
| 77 | `results\research_E.md` | 6796 | done | 0 theorems | ✅ 研究笔记——FDR推广到全D₄, 统一law定理
| 78 | `results\research_F.md` | 4545 | done | 0 theorems | ✅ 研究笔记——容器方法proven, bridge桥接FALSE已自纠
| 79 | `results\research_G.md` | 9904 | done | 0 theorems | ✅ 研究笔记——空间先验强非均匀; ⚠️ §6假解已RETRACTED
| 80 | `results\research_H.md` | 8385 | done | 0 theorems | ✅ 研究笔记——LLL在2空间均失败; 唯一存活路线=conflict-free matching
| 81 | `results\research_I.md` | 9172 | done | 0 theorems | ✅ 研究笔记——Graves codegree条件; C3在m=37临界失败
| 82 | `results\research_J.md` | 8692 | done | 0 theorems | ✅ 研究笔记——6发散方向分析; 首选#3 CDCL SAT
| 83 | `results\research_K.md` | 8897 | done | 0 theorems | ✅ 研究笔记——#3 SAT运行中; #4一阶矩完成(mean=416.4)
| 84 | `results\research_L.md` | 2378 | done | 0 theorems | ✅ 研究笔记——局部极小为杀手(m=6卡bad=4)
| 85 | `results\research_M.md` | 5132 | done | 0 theorems | ✅ 研究笔记——"≤2细胞/环"被证伪→撤回为更弱"≡0 mod 4"
| 86 | `results\research_N.md` | 3851 | done | 0 theorems | ✅ 研究笔记——同m多解径向层守恒+2-因子层≤2律
| 87 | `results\research_O.md` | 4587 | done | 0 theorems | ✅ 研究笔记——非rot4类径向层对比
| 88 | `results\research_P.md` | 3317 | done | 0 theorems | ✅ 研究笔记——跨m纵向径向律ρ≈0.57守恒, 21630解验证
| 89 | `results\research_T15.md` | 4025 | done | 0 theorems | ✅ 研究笔记——~80%完整(T15.1-6已证); T15.7(k≥4基帧安全)仍OPEN
| 90 | `results\research_index.md` | 9758 | done | 0 theorems | ✅ 总索引表, 状态全面
| 91 | `results\review_response_2026-07-13.md` | 8831 | done | 0 theorems | ✅ 回应评审——方向1 LLL框架修正正确(vanilla LLL必然失败)
| 92 | `results\rigidity_hierarchy_theorem.md` | 14171 | done | 5 | **theorem-grade(总纲)**。约束数1.26×10⁶与124,320口径不一致(微注)
| 93 | `results\route2_xhyper_degree.md` | 4734 | done | 0 theorems | ✅ 精确冲突超图度数枚举(m=10..37); 31M (X)超边数据正确
| 94 | `results\route3_cycle_terrace.md` | 4451 | done | 0 theorems | ✅ 环型景观(30个m值)+单圈实证测试
| 95 | `results\route3_sdp_report.md` | 12348 | done | 5 | HONEST—SDP判别器theorem级; m=37 20样本全≥45.5; 408证16; 明确采样≠证明
| 96 | `results\route4_terrace_corrected.md` | 5192 | done | 0 theorems | ✅ 修正文档——修正single_cycle_terrace_theory §4.1内部矛盾
| 97 | `results\route5_burnside.md` | 4549 | done | 0 theorems | ✅ 更正先前文档3个误差(线数~N⁴非1.5N², Fix(r)=0非2N-1)
| 98 | `results\sidon_costas_unification.md` | 13133 | done | 4 | **合成/定理级**；LQ分类正确; R8-C定理; §7界定清晰
| 99 | `results\single_cycle_terrace_theory.md` | 11696 | done | 0 theorems | ✅ 单37-圈+terrace/starter理论; 差分析出至经典组合设计
| 100 | `results\solver_theory_m37_report.md` | 6775 | done | 7 | HONEST求解器可行性研究; m=37最好96几何缺陷(=24子句)报found=False
| 101 | `results\stageM_m37.md` | 4548 | done | 0 theorems | ✅ 首次正确二次空间攻击报告; found=0但诚实标"非不存在性证明"
| 102 | `results\structural_scaling_2026-07-12.md` | 4168 | done | 0 theorems | ✅ 结构不变量跨m标度表; 数据驱动
| 103 | `results\swarm_A5_report.md` | 11399 | done | 0 theorems | ✅ 团队报告——m=36/m=37对比; A5→470子句17最优(UNSAT)
| 104 | `results\swarm_D1_2_report.md` | 4727 | done | 0 theorems | ✅ 团队报告——取向3-SAT/MaxSAT; 全部UNSAT确认(X)障碍内在
| 105 | `results\swarm_D1_gaussian_reformulation.md` | 7173 | done | 0 theorems | ✅ 团队报告——有限域重新编码至Z[i]奇数坐标
| 106 | `results\swarm_D1v3_report.md` | 8709 | done | 0 theorems | ✅ 团队报告——2-cycle假说FALSIFIED; best72→468(↓2)非突破
| 107 | `results\swarm_D2_report.md` | 4637 | done | 0 theorems | ✅ 团队报告——热图偏置SA+hinted CP-SAT; 24种子×120s
| 108 | `results\swarm_D5_report.md` | 9061 | done | 0 theorems | ✅ 团队报告——不可能性攻击; 无不可能性证明找到
| 109 | `results\swarm_D5v2_report.md` | 22362 | done | 6 | P1/P2/P3=theorem; P3b线性项消失错(与§3.4矛盾); P2b误推(已撤)
| 110 | `results\switch_average_drift.md` | 2796 | done | 1 | ✅ THEOREM-grade——B(f)>0⇒S(f)<0双计数论证; 鸽笼推论合理
| 111 | `results\switch_graph_fdr_extension.md` | 9833 | done | 0 theorems | ✅ 扩展至5FDR群框架正确; partial proofs标注诚实
| 112 | `results\switch_graph_theorem.md` | 18661 | done | 3 | **❌ 过度声称：Lemma 1a 对14≤m≤64依赖gating采样, 非完整证明**; Th-1对m=37不成立
| 113 | `results\theorem_r9c_perm_equiv.md` | 9295 | done | 2 | ✅ THEOREM-grade——T1-T5+引理6; 更正声明等价性假说→自纠
| 114 | `results\theorem_r9d_obstruction.md` | 6904 | done | 1 | ✅ THEOREM-grade——T7(轴对齐自动安全); 奇数坐标模型+4提升点分类
| 115 | `results\theorem_r9e_obstruction_algebra.md` | 7247 | done | 2 | ✅ THEOREM-grade——T10/T11二次障碍代数次数严格证明; 16重取向分解
| 116 | `results\theorem_r9f_baseframe_3free.md` | 11070 | done | 7 | T12/T15定理+R9g实证; 校准良好
| 117 | `results\theorem_vectors_findings.md` | 2927 | done | 0 theorems | ✅ 向量化4次探索——结论"真解与随机在近共线程度无差异"
| 118 | `results\theory_fit_report.md` | 5342 | done | 0 theorems | ✅ 理论拟合报告——所有已知解100%拟合SIRH预测
| 119 | `results\two_layer_rigidity.md` | 10685 | done | 3 | 合成文档; m=37 OPEN标注诚实; 无伪定理
| 120 | `results\unexpected_tools_survey.md` | 11836 | done | 0 theorems | ✅ 头脑风暴——Kotecký-Preiss聚合物气建议标注清晰
| 121 | `results\vector_products_findings.md` | 2616 | done | 0 theorems | ✅ 点积/叉积/长度谱无区分度; 诚实报告
| 122 | `results\verification_2026-07-14.md` | 3802 | done | 0 theorems | ✅ 硬数字复核——A1环结构/ A2冲突超图参数/ A3 Graves C2成立C3临界
| 123 | `review_current_results_2026-07-09.md` | 9223 | done | 0 theorems | ✅ 同行评审——R2真定理/R1计算事实/R3/R4经验观察(过度宣称已指出)
| 124 | `review_overfit_2026-07-09.md` | 8409 | done | 0 theorems | ✅ README过拟合审查——发现5项(rot2相变推翻了、数字错误、措辞过度等)
| 125 | `rot4_diagonal_connectivity.md` | 5581 | done | 2 | ✅ THEOREM-grade——Th-48(有完整证明+21k验证); Th-49修正Th-43; 自纠诚实
| 126 | `spectral_struct_n0mod4.md` | 12342 | done | 0 theorems | ✅ 典范级——PROVEN/EMPIRICAL/OPEN三档标记清晰; Lemma 1-3已证
| 127 | `th52_writup.md` | 2555 | done | 3 | ✅ THEOREM-grade——Th-52(叉积论证已证); Th-53(线性性分类已证); Th-54(实标"非形式定理")
| 128 | `theory_c4_necessity.md` | 2883 | done | 0 theorems | ✅ 自标"实证定理"; 解析证明标注OPEN; 数据正确
| 129 | `theory_final_synthesis.md` | 4532 | done | 0 theorems | ✅ 综合小结; 定理状态标注正确
| 130 | `theory_landscape_m37.md` | 7153 | done | 6 | HONEST校准良好; LLL/模-3证不了存在/不可能
| 131 | `theory_motzkin_breakthrough.md` | 4109 | done | 1 | ✅ THEOREM-grade——Th-17(三步证明); 渐近k/n→1/π引用标准结果
| 132 | `theory_rct4_complete.md` | 5338 | done | 7 | ✅ THEOREM-grade——R1-R7定理; R1有证明草图; R2-R7代数推导
| 133 | `theory_structural.md` | 39393 | done | 0 theorems | ✅ 结构化理论主文档——[P]/empirical标记清晰(已证定理30+条、实证定律20+条); 重要自纠(rct4灭绝错误); 无过度声称
| 134 | `theory_th19.md` | 1539 | done | 1 | ✅ THEOREM-grade——Th-19恒等式h(c)=count_π(≤c)-(c+1); 完整代数证明
| 135 | `truth_final.md` | 6927 | done | 0 theorems | ✅ 独立扫描——Findings非Theorems; 撤回(斜率-1 bug/mod p平凡)透明
| 136 | `truth_optionB.md` | 7166 | done | 0 theorems | ✅ LLL不可能性分析; 结论"No"; 根本原因p_consec≈4/n精确量化
| 137 | `verification_2026-07-09.md` | 8348 | done | 0 theorems | ✅ 独立验证——5类排除定理数学正确; 2处文档措辞修正

**共 137 个 .md 文件。**

## 审计条目
---

### 📄 `results/solver_theory_m37_report.md` — **HONEST 求解器可行性研究**（无伪定理）

| 声明 | 定级 | 核验 |
|---|---|---|
| 2-因子无 2-圈 ⇒ 666 转置对自动禁绝 | 正确 | m(m-1)/2=666；简单 2-正则图无平行边。✓ |
| (X) 缺陷 `ΣC(s,3)=Σp(s−2)/3`, `s=(1+√(1+8p))/2` | 正确 | 代数已验。✓ |
| (X)-引擎经 brute 重扫验证一致 | 已验证 | m=15,20,25,30,37 多步一致。✓ |
| m=37 最好降到 96 几何缺陷（=24 子句违例） | 诚实 | 逊于扫掠 64；报 `found=False`。✓ |
| 框架"符合 SIRH/Th-44 预测" | 合理 | 解释性。 |

**标错**：无实质问题。微注——"96 (X)-count"为几何缺陷（=24 子句违例），文档内部一致。

---

### 📄 `results/m37_satisfiability_window.md` — **诚实间接证据，但乐观结论已被新证据削弱**

| 声明 | 定级 | 核验 |
|---|---|---|
| 结构不变量（源占比~0.26）跨 m 连续无突变 | empirical（强） | 数据驱动，自陈噪声（m≥29 仅 .few 抽样）。 |
| 二次约束密度 m=36→37 仅 +0.3%，无相变悬崖 | empirical | 标度计算正确。 |
| "m=37 大概率也有解" | **推断（现已削弱）** | 连续性≠存在性（文档自陈）；但 2026-07-16 SDP 证据（20 样本全≥45.5、408 证 16）强烈反对其乐观。→ 应调和/更新。 |

**标错（需修正）**：
1. **结论过时**：文档（2026-07-12）基于连续性推断"m=37 大概率有解"，与 2026-07-16 的 SDP 认证不可行证据矛盾，应加注"该乐观推断已被后续 SDP 证据削弱"。
2. **内部数值不一致**：§2"每对配对被 16 个二次型决定"（总数应为 16·C(m,2)）；§3.4"二次型总数 124,320"=16·C(37,3)。二者"二次型总数"定义不同，需统一。

---

### 📄 `report_best72.md` — **诚实经验分析，但已过时**

| 声明 | 定级 | 核验 |
|---|---|---|
| best72 单 37-环，470 子句，18 违例（证最优） | 正确（当时） | D5v2 确认 18 证最优。 |
| 2-switch (4,31),(7,28)→(4,7),(28,31)：470→452 | 正确 | 边级 −24+6=−18，自洽。✓ |
| "min span≥5 假设被证伪" | empirical | 短跨边降子句数，观察正确。 |
| 代数构造全失败（≥1310 子句） | empirical | 数据。 |

**标错（需修正）**：
1. **OUTDATED**：文档写于 408/16 发现之前，其"best known = 446–448 子句 / 18 违例"已被 `config_408`（**408 子句 / 16 违例，证最优**）超越。best72 仍是 18 最优，但非全局最佳。应加"已被 config_408 超越"注。
2. §5.2"真最小 380–430"为臆测（408 落区间，但非严格下界）。
3. §2.3"448 clauses removed"指子句三元组变动，易与"448-子句构型"混淆，建议改写。

---

### 📄 `results/route3_sdp_report.md` — **HONEST 校准佳（自审，2026-07-16）**

| 声明 | 定级 | 核验 |
|---|---|---|
| SDP 判别器有效（小 m 穷举：SDP_lb≤真值；SAT⇒SDP_lb≤0） | **theorem**（验证级） | m=5(73)/m=6(388) 穷举，噪声<1e-3。✓ |
| m=37 20 样本 SDP_lb 全 ≥45.5 | computational | 每个 = 逐构型 SDP 认证不可行（min_viol≥45.5）。✓ |
| 408：min_viol=16 证最优 | **theorem** | 见 ising_optimality_proof 审计。✓ |
| 无普适解析不等式（回归 R²=0.595，候选全失败） | 正确发现 | 受挫全局弥散。✓ |
| "SDP 采样 ≠ m=37 无解证明" | 正确 | 明确边界。✓ |

**标错**：无实质问题。该报告即本轮路线3结论，诚实标定了证明缺口（覆盖所有 2-因子）。

---

### 📄 `ising_optimality_proof_m37.md` — **RIGOROUS / HONEST** (theorem-grade)

**定级结论**：对*特定* 2-因子（config_408, config_448）的最优性声明是 **theorem**，推导严谨、诚实标界。

| 声明 | 定级 | 核验 |
|---|---|---|
| (★) `min_viol ≥ (n_cl + SDP_min)/8` | **theorem** | elliptope 是 cut-polytope 外逼近 ⇒ `SDP_min ≤ cut-min` ⇒ 推导正确。加 triangle 不等式收紧亦正确。 |
| 408: `min_viol=16` 最优 | **theorem** | triangle-SDP 下界 15.9973；`min_viol` 为整数 ⇒ ≥16；且已知 16 可达 ⇒ 最优。**整数取整吸收数值误差**（SCS/CLARABEL ~1e-4 ≪ 0.9973 余量），结论 robust。 |
| 448: `min_viol=17` 最优 | **theorem** | 下界 17.0000（[optimal_inaccurate]）；因需 `lb>16` 即推 `≥17`，数值误差不破结论。 |
| m36 SAT 下界=0 | 一致 | 与基本 SDP 互相印证。 |
| "不能推出 m=37 整体无解" | 正确 | 明确写出，未夸大。 |

**标错**：无实质问题。微注——448 的 "17.0000" 精确等号未被机器认证（optimal_inaccurate），但 `min_viol=17` 结论仍由整数性严格成立。

---

### 📄 `theory_landscape_m37.md` — **HONEST 校准良好**（多数为 empirical/conjecture，已正确标级）

| 声明 | 定级 | 核验 |
|---|---|---|
| LLL 族证不了 m=37 存在（稠密超图，e·p·(d+1)≈1080≫1） | empirical/computational（强） | 引 `asymmetric_lll_m37.json`；结构障碍，非形式定理。 |
| 模-3 证不了不可能 | 正确（诚实） | 已说明只削弱不禁绝。 |
| "普遍下界 ≥7" 非定理 | 正确降级 | 引 D5v2 自承不全。 |
| "16-平台是 switch 图深局部极小" | empirical | 搜索未逃逸的观察，非定理。 |
| Ising 重述"数值验证于 3 构型" | 见 ising_reframing 审计 | 一般代数证明由 180° 对称支撑。 |
| "受挫全局非局部模板" | 现被路线3 **8构型∩=0** 严格支撑 | 强证据。 |

**标错**：①"最佳 408/16"=**已知最佳**，非证得全局最优（但 408 是子句最少构型且已证 16 最优，证据强）。②Ising 化简"3 构型验证"需查其一般证明（ising_reframing 已补全为 theorem）。

---

### 📄 `ising_reframing_m37.md` — **高质量 / 严谨 / 校准佳**（本次审计范本）

| 声明 | 定级 | 核验 |
|---|---|---|
| 化简 `V_E = P_E/4 + 1/4 Σ J^E s_i s_j` | **theorem** | 恒等式 `1_{s=a}+1_{s=-a}=1/4(1+Σ_{i<j}a_i a_j s_i s_j)` 已手验；线性/三次项因互补对称精确相消。 |
| closure 对*任意* 2-因子成立 | **theorem** | 由 180° 旋转对称性（旋转使取向位翻转）；3 构型 closure=0 为经验验证。 |
| 路线1：408→16、448→17 最优 | **theorem** | 见 ising_optimality_proof 审计（整数取整）。 |
| 谱下界 m=37 正 / m=36 负 | 有效但**弱**下界 | Rayleigh 商严格下界；"严格符号证据"是逐构型证据，非 m=37 不可能性证明（文档措辞正确）。 |
| §6b：8 多样构型受挫三角形全集∩=0 | **强证据**（计算） | 证伪"固定局部模板"路线；文档自注"仍非证明"。 |
| §6 系列降级更正（D5v2 P4 / D1v3 / A5） | 诚实 | 良好自我纠错。 |

**标错**：无实质问题。微注——谱下界虽"严格"但是弱界，仅作逐构型证据。

---

### 📄 `results/swarm_D5v2_report.md` — **扎实结构分析，诚实，含局部错误（已部分撤回）**

| 声明 | 定级 | 核验 |
|---|---|---|
| P1 互补对对称 | **theorem** | transpose `T(x,y)=(y,x)` 是保共线刚性运动且翻转取向位 ⇒ closure。干净。 |
| P2 (0,0,0)/(1,1,1) ⇒ NAE | **theorem** | 直接。 |
| P3 边平衡 | **theorem** | 由 P1 推出。 |
| P4 冲突图下界 ≥6–7 | **非定理** | 正文 line 117 自承证明不全；界松（6–7 vs 实际 17–18）。文档与 ising_reframing 均已降级。 |
| §3.3 独立集 `(7/8)^11≈0.23` | 有效弱概率界 | 正确。 |
| §5.2 三构型模式∩=∅ | 证据 | 计算。 |

**标错（需修正）**：
1. **P3b "线性项消失" 错误**：同文 §3.4 明列个别 `α_e∈[−13,+3]≠0`，与 P3b 自相矛盾。线性项仅在**配对 Ising 基**（ising_reframing）下消失，子句-Fourier 基下不消失。→ 内部不一致。
2. **P2b "NAE 子集不可二染色" 误推**：§2.2 称全集 UNSAT ⇒ NAE 子集 UNSAT，逻辑错；Corrections #2 已撤，但正文未加删除线。
3. **§7.1 #1 "任意 2-因子必违例" 夸大**：仅对*测试*构型证得，全体仍开放（文档随后 hedge）。
4. **数值不一致**：P4 下界摘要写 ≥7、表格写 ≥6。
5. **"3.3 标准差" 启发式**：未计协方差，非精确。


_逐文件追加，见下。_

---

### 📄 `results/fdr_theorem.md` — **THEOREM-grade（FDR 严格代数证明）**

| 声明 | 定级 | 核验 |
|---|---|---|
| 引理 A1：D₄ 8 元对 x−y 作用分类表 | **theorem** | 逐项代入验算：g₂: y−x=−(x−y)✓；g₆: y−x=−(x−y)✓；g₇: x−y 不变✓；g₁/g₃/g₄/g₅→斜率−1✓。代数正确。 |
| 定理 FDR：G 不含 g₄/g₅ ⇒ F_G 上 a−b≤2（必要） | **theorem** | 引理 C2（每斜率+1线在 F_G 中≤1点）sound；a−b=−2(x−y) 编码 d；count(d)+count(−d)≤2 由 C1 推出。✓ |
| 推论 D 分类表（rot4/rot2/rct4/dia/full ✅, ort1/iden ❌） | **theorem** + empirical | 代数分类正确；100%/0% 实证与预测一致。 |
| 引理 E：反向不成立（iden n≤20 有 21–75% 巧合通过） | **theorem（反例存在）** | 反向证伪正确；通过率为 empirical 描述。 |
| FDR+ 统一陈述 (i)(ii)(iii) | **theorem** | 三方陈述自洽。 |

**标错**：无实质问题。微注——表 6.8 完成态正确；6.9（反向）、6.10（容器-对称桥接）诚实标为开放；§"Connection to R8" 末句"m=37 二次 (X)∧(S) 系统可满足性 OPEN"与 SIRH 总纲一致。

---

### 📄 `results/rigidity_hierarchy_theorem.md` — **THEOREM-grade 总纲（SIRH）**

| 声明 | 定级 | 核验 |
|---|---|---|
| Part I (FDR) 已证 | **theorem** | 见 fdr_theorem 审计；必要律 sound。 |
| Part II 二次必然（§3.1 线性⇒仅斜率±1；§3.2 其余共线=二次 det=0） | **theorem** | §3.1 范畴论证（a−b Sidon 仅依赖 x−y，非±1斜率共线与之无关）有效；§3.2 det 为 2 次齐次多项式，平凡代数事实。 |
| §3.3 严格不充足：C4 构造见证 + rot2 构造见证(n=8,10,12,14,16) | **theorem（构造性）** | 见证存在即证严格不充足；rot2 仅对"tested n"声明，范围正确未夸大。 |
| Part III R8(C4) + R8-G(全 6 FDR 群) | **theorem** | R8-G 由"NTIL⇔无3共线⇔每条线≤2" + 轨道结构推出 per-line 加权≤2 ≡ 二次CSP(det≠0)；45/45 校验是 soundness 佐证非证明本身。 |
| "Hypothesis H RESOLVED / Part III 完成" | **theorem** | 刻画等价(对所有FDR群含C4)已证；**正确区分** m=37 该 C4-CSP 可满足性仍 OPEN（未混同解决）。 |
| Part IV 反向否定（P4.1/P4.2/P4.3） | **theorem** | P4.1 非对称Sidon载体存在⇒Sidon⇏对称；P4.3 二次签名仍单向（遗忘lift对称不可逆）。P4.2 计数 ≳0.46·0.78^m·C(m²,m) 为 heuristic 渐近估计，定性 robust 但常量非严格下界。 |
| §6 剩余开放：m=37 可判定性 OPEN；Guy–Kelly/Hall 全局界未触及 | 诚实 | OPEN 标注正确。微注 Guy–Kelly "D(n)=2n 无限族" 或可更强的"猜想"措辞（等式对所有 n 是 Guy–Kelly 猜想，构造对无穷多 n 成立）。 |

**标错（需留意）**：
1. **约束数口径不一致**：本文 §4 "≈1.26×10⁶ 约束" 与 `m37_satisfiability_window.md` §3.4 "124,320 = 16·C(37,3)" 数值不一致（差~10×）。应统一口径（前者或为全 board 线 per-line≤2 计数，后者为 (X) 三元组计数）。
2. §3.3 "dia2/full/dia1 由 R8-G 闭合"——逻辑上 R8-G 给出刻画，不充足的"构造见证"对这些群未逐一列，但由 §3.1–3.2 群无关论证 + R8-G 等价，不充足性对全 FDR 群成立（论证链完整）。可接受。
3. 无伪定理；总体校准极佳，是 SIRH 的权威总纲。

---

### 📄 `results/part4_reverse.md` — **THEOREM-grade（Part IV 反向否定），P4.2 应降级**

| 声明 | 定级 | 核验 |
|---|---|---|
| P4.1 非对称 Sidon 载体存在（FDR 线性签名可通过） | **theorem** | 反例存在⇒Sidon⇏对称；回归证明≥2.8%随机通过(实测)已足。✓ |
| P4.2 Sidon 载体计数 ≫ 对称 NTIL（\|S_m\|/\|A_m\|→0） | **heuristic/strong evidence** | 计数 ≳0.46·0.78^m·C(m²,m) **依赖 empirical 常数**（40000 采样），非严格下界。定性结论（Sidon 主导不对称）robust 但非定理。→ ❌ 应降级 |
| P4.3 全二次签名仍单向（遗忘 lift 对称不可逆） | **theorem** | 签名在基本域上；不对称配置可有对称域（无需全 lift）。✓ |
| 结论表：单向 SIRH 链 | 正确 | 结论自洽。 |

**标错（需降级）**：P4.2 被标为 "Theorem" 但证明使用 empirical 采样常数（0.46·0.78^m），应降为 "strong empirical evidence / heuristic"，并明确指出该界非形式定理。其余声明正确。

---

### 📄 `results/quadratic_sidon_completeness.md` — **THEOREM-grade（R8 候选→已证定理）**

| 声明 | 定级 | 核验 |
|---|---|---|
| (X)∧(S) 精确⇔ rot4 NTIL | **theorem** | 形式证明见 r8_proof.md（案例A/B/C穷举）。计算校验：93解+7500模板 miss/false=0。 |
| 层 S 单独必要（X 不足） | empirical（强） | 数据：miss(X) m=5:53 → m=8:2；逻辑上 r8_proof 证 S 捕捉 case B(同cell双像+另一cell)，无 S 则 case B 漏检⇒S 必要。 |
| m=37 约束数：X=124,320，S=15,984，总=140,304 | 正确 | 自校正先前的混合估算。C4 约化 vs 全 64/24 倍数一致。 |
| FDR 对等价关系冗余 | 正确 | FDR 是 (X)∧(S) 特征，不加额外约束。 |

**标错**（微注）：标题含 "candidate theorem" 已过时；R8 已升格 theorem。建议改标题。无实质错误。

---

### 📄 `results/r8_generalized.md` — **THEOREM-grade（R8-G，全 FDR 群二次完备）**

| 声明 | 定级 | 核验 |
|---|---|---|
| R8-G: per-line 加权≤2 ⇔ G-对称 NTIL（∀FDR群） | **theorem** | 由定义推出：soundness(≤2⇒无3共线) + completeness(无3共线⇒≤2) 均 trivial 但正确；二次等价(det≠0)平凡。 |
| "Hypothesis H RESOLVED" | **theorem** | 刻画等价对所有 6 FDR 群成立（含 C4）；**正确区分** m=37 该 CSP 可满足性仍 OPEN。 |
| §5 统一刚性（constraint/var→∞） | **theorem** | 计算正确：C4 @ m=37: ~1.37×10³ vars, ~1.26×10⁶ 约束（per-line 计数）。 |
| 45/45 --validate | 计算验证 | 佐证 soundness，非证明本身。 |

**标错（需修正）**：
1. **"≈102·vars" 疑笔误**：§5 "T_min(m)=16·C(m,3)+12·m·(m−1) ≈ 102·vars at m=37" — 16·C(37,3)+12·37·36 = 140,304，非 102。或为 "≈102·(m²)" 即 ~102·1369=139,638 之误？应确认澄清。
2. 无伪定理；§4 诚实区分 m=37 OPEN。§2.3 二次等价论证链完整。

---

### 📄 `results/r8_proof.md` — **RIGOROUS THEOREM（R8 形式证明）**

| 声明 | 定级 | 核验 |
|---|---|---|
| (⇐) (X)∧(S) ⇒ 无 3 共线：case A(3不同cell→X)、case B(2同cell+1另一→S)、case C(3同cell→C4轨道无3共线) | **theorem（完美）** | 案例穷举完全；C4 轨道引理（离轴=正方形、轴上=菱形、对角=轴对齐正方形）已验证正确。✓ |
| (⇒) 有 3 共线 ⇒ (X)∧(S) 被违反 | **theorem** | trivial 由构造。✓ |
| R8 ⇔ rot4 NTIL = 二次 CSP | **theorem** | 由双向推出等价。 |
| 自行修正 perm-matrix 假设 | 诚实 | 良好自我纠错，不影响 R8。 |

**标错**：无。此文是项目最严谨的定理文档之一：案例分析完全穷举、C4 轨道引理优雅几何、自我纠错诚实。

---

### 📄 `results/sidon_costas_unification.md` — **合成/定理级（LQ+R8-C）**

| 声明 | 定级 | 核验 |
|---|---|---|
| §1 分类表 + 经典等价（Golomb≡Sidon、Costas≡2D Sidon+permutation） | **theorem（文献已知）** | 正确。四个等价点均标准。 |
| **Theorem LQ**: 禁止重合分线性/二次两个regime | **classification（正确但平庸）** | Costas 禁等位移向量 = 线性方程 x_j−x_i=x_l−x_k；NTIL 禁共线 = 二次 det=0。R7 引用的"线性 Sidon 不足以禁二次"是定理(R7)。**"线性 regime→有限域构造可解"推论是 heuristic，非定理。** |
| **Theorem R8-C**: C4-对称 Costas ⇔ 基本域线性 CSP | **theorem** | C4-lift 仿射(线性)；位移相等=线性非等式约束。约化正确。存在性问题仍 OPEN。 |
| §5 计算：Welch 成功(p≤19)、C4-对称 Costas n≤16 全无 | 计算验证 | 与 C6 定理(C4 Costas n>1 不存在的证明)一致。 |

**标错（需注意）**：
1. **LQ 定理的构造推论被过度声称**：§2 末称"finite-field / linear 方法成功" 对 Costas 仅部分成立（Welch 成功但 32/33 仍 OPEN），非定理保证。文档 §7 诚实界定了 OPEN，但 LQ 正文语境可能误导。
2. 标题 "new theorems (analytic)" 诚实；整体校准良好（§7 正确区分 proved/empirical/open）。

---

### 📄 `results/theorem_r9f_baseframe_3free.md` — **T12/T15 定理链 + R9g 实证，校准良好**

| 声明 | 定级 | 核验 |
|---|---|---|
| T12: 基本 cell 集必为基帧无三共线（必要） | **theorem** | 仿射保共线映射正确；rot4-NTIL 含 4m 提升点 ⇒ 基帧 m 点无 3 共线。✓（R8 的推论，独立推导正确） |
| T13: 障碍预算 ~48%/52%（基帧 vs 交换帧） | **empirical** | m=14, K=1500 数据驱动。合理但非定理。 |
| T14: 重述 2-正则图+16帧⇔rot4-NTIL | restatement | 正确。 |
| R9g: 素数 m 代数置换族全失败 | **empirical（强）** | m∈{5,7,11,13,17,19,23,29,31,37} 全部 bad。计算证据，非证明。 |
| T15.2: 3-环基帧自安全（det 公式） | **theorem** | det = −½[(x−y)²+(y−z)²+(z−x)²]，零⇔x=y=z（退化 1-环）。公式代数验算正确。✓ |
| T15.3: 1-环/loop 安全 | **theorem** | 单点无 3 共线。✓ |
| T15.4: Sidon-环耦合（SIRH Part I 特化） | **theorem** | SIRH Part I 在环步长上的直接推论。✓ |
| T15.5: 经验景观表 | **empirical** | 30 行数据，诚实标注 m=23–26 缺口、m≥29 稀疏。 |
| T15.6: 环型既非障碍亦非加速 | **正确评估** | 诚实明确环型不解决 m=37。 |

**标错**：无实质问题。R9g "实证定理" 措辞可更明确（computational 而非 theorem），但整体诚实。

---

### 📄 `results/two_layer_rigidity.md` — **合成文档（非定理文档），校准佳**

| 声明 | 定级 | 核验 |
|---|---|---|
| 两层刚性框架（FDR 线性 + R8 二次 = 定理层；R7 = 间隙） | **正确描述** | 引用已证定理（fdr_theorem、r8_proof、R7）准确。✓ |
| §4 层级图（线性→二次→m=37 OPEN） | **正确** | 结构自洽。 |
| §5 容器方法（候选 Layer 0） | **speculative（正确标注）** | 明确非定理、"candidate" 标识。✓ |
| §6 m=37 OPEN，CP-SAT 编码正确工具 | **正确** | 表述诚实（OR-Tools 被用户终止）。 |
| Costas 跨应用引用 | **正确引用** | 引用 costas_symmetry_theorem C1-C5 准确。 |

**标错**：无实质问题。合成文档不宣称新定理，所有引用准确，边界（proven/speculative/open）诚实标记。

---

### 📄 `results/r9_modp_descent.md` — **R9a 修正引理（定理） + R9b 方法建议，校准良好**

| 声明 | 定级 | 核验 |
|---|---|---|
| R9a（假猜想→修正）：mod-p 下降仅当 p > 2m 有效 | **theorem（修正正确）** | p > 2m ⇒ 坐标 mod p 无碰撞 ⇒ det≡0 (mod p) 必要；p ≤ 2m 时碰撞致误杀。✓ 自我纠错诚实。 |
| R9b: rot4 NTIL ⇔ 2-正则图 + 取向 + (X)+(S) 二次 CSP | **正确（Th-44 重述）** | 已是 SIRH/Th-44 已知。非新结果。 |
| "m=37 存在 plausible" | **empirical（先于 SDP 证据）** | 基于连续性分析（源占比、最大圈比）；2026-07-16 SDP 20 样本全≥45.5 削弱此乐观。文档诚实（写于 SDP 前）。 |
| 排列-CSP 模型建议 | **方法建议** | 非定理；潜在工程改进。 |

**标错**：无实质问题。R9a 自我纠错诚实体面；R9b 正确引用 Th-44；"plausible" 断言在写作时合理、现已过时但未伪称。

---

### 📄 `results/conflict_hypergraph.md` — **formulation 文档（无定理声称），校准良好**

| 声明 | 定级 | 核验 |
|---|---|---|
| §2 冲突超图定义：(S)=二类、(X)=三类 | 正确（R8 重述） | 正确建模。 |
| §3 参数表（avg (X)/factor 等） | **empirical** | 数据驱动（500 随机 2-因子），诚实报告。✓ |
| 97% 冲突为 (X)-型 | **empirical** | 与 R8 (X)主导一致。 |
| 总 (X) 冲突 O(m) 标度 | **empirical（强）** | E[#(X)]≈7.2m 从表拟合；非定理。 |
| per-cell (X)-degree ~0.58/factor @ m=37 | **empirical** | 超图极稀疏。 |
| §4 工具（nibble/LLL/absorption） | **proposal** | 明确标候选；§4.1 诚实说明全局限度约束非超图约束。 |
| §6 连接 R8-G | **正确** | 重述等价性。 |

**标错**：无实质问题。formulation 文档无定理声称，参数诚实标注。

---

### 📄 `hypergraph_framework.md` — **THEOREM-grade（Symmetry-Exclusion 定理）**

| 声明 | 定级 | 核验 |
|---|---|---|
| 距离环超图模型（H = H_collinear ∪ H_ring） | 正确定义 | S 为缺失中心 NTIL ⇔ S 为 H 独立集。✓ |
| **Symmetry-Exclusion Theorem**：full/rot4/rct4/dia2/ort2 被排除；iden/rot2/dia1/ort1 兼容 | **theorem** | 轨道-on-环论证：轨道大小≥3 ⇒ 环≥3点 ⇒ 非缺失中心。rot4 4-cycle ✓；dia2 4-orbit 几何验算 ✓；ort2 对称 ✓；rot2/dia1/ort1 2-orbit 兼容 ✓；iden 1-orbit 兼容 ✓。 |
| dia2 不可能（无离轴点 ⇒ |S|≤4<2n） | **theorem** | 补证正确：全在对角线 ⇒ 每对角线 ≤2 ⇒ |S|≤4<2n ∀n≥3。✓ |
| §3 实现：iden/rot2/dia1 确实出现；ort1 OPEN | **empirical + open** | 缓存验证；ort1 搜索 n≤18 未找到，诚实标 OPEN。 |
| §4 计算交叉检验（335,702 解，0 解码失败） | **computational** | 排除类 0/0 缺失中心，与定理一致。 |

**标错**：无实质问题。整齐优美的小定理——仅需轨道-on-环论证即排除 5 类。ort1 OPEN 诚实标注。

---

### 📄 `c4_construction_theory.md` — **构造理论文档，校准良好**

| 声明 | 定级 | 核验 |
|---|---|---|
| Row-Degree 定理（rot4 NTIL ⇔ 2-因子） | 正确（Th-44 重述） | 已有定理。 |
| 定理 2.1：等差圈序（步长 a）失败于 m ≥ 3a+1 | **lemma** | 三点 (0,a),(a,2a),(2a,3a) 在 y=x+a 上 ⇒ 共线。几何正确但仅限等差圈序。✓ |
| 推论：a=1 对所有 m≥4 失败 | 正确 | 定理直接推论。 |
| §3 单圈存在经验表（唯 m=6 例外） | **empirical** | 数据驱动，诚实标 m=23–26 缺口。 |
| §4–5 诚实缺口（无显式构造/无存在性证明） | **正确评估** | 明确 n=74 OPEN。 |

**标错**：无实质问题。定理 2.1 范围有限（仅等差圈序），但文档清楚说明"只要圈序非等差即可"。

---

### 📄 `container_analysis.md` — **探索分析文档，§4.1 过度声称**

| 声明 | 定级 | 核验 |
|---|---|---|
| §1–2 容器定理 τ 计算（τ≈5.1 > 1 ⇒ 平凡界） | 合理分析 | 计算步骤清晰，数值可信。✓ |
| §3 替代工具（LLL/概率/匹配/经验计数） | **正确评估** | 各工具局限诚实说明：LLL 不适用(行匹配破坏独立性)；概率法可能(存在性非计数)；经验计数含表。 |
| §4.1 **"Low-Slope Emptiness Theorem"** | ❌ **过度声称（应降级）** | "证明草图"不构成证明：仅称"for any triple... the lines do not pass through any point from another orbit unless through center (excluded by Lemma 1)"——无具体计算/代数验证。计算验证(n=12..60)是 empirical 证据，非定理。→ **应标为 empirical / 可猜想** |
| §4.2 Missing-Center 猜想 | **conjecture（正确标注）** | 有部分证据(17/142 n=21 缺失中心)，正确标为 conjecture。 |
| §4.3 n=76 说法 | 讨论 | **n=76 非 m=37(n=74)**——可能是笔误或过时假设。 |

**标错（需降级）**：
1. **"Low-Slope Emptiness Theorem" 不是定理**。§4.1 的"证明"是一个泛泛草图，缺乏代数推导/坐标计算。计算验证很广（n=12..60）但不足以构成证明。该文档将之列为 "✅ Ready——Proven up to n=60" 是**过度声称**。应降级为 "empirical / plausible conjecture"。
2. n=76 vs n=74 不一致（minor）。

---

### 📄 `low_slope_parity_theorem.md` — **THEOREM-grade（奇偶律，完整证明）**

| 声明 | 定级 | 核验 |
|---|---|---|
| 偶数 n：H_n[L] 恒空（奇偶性） | **theorem** | 偶数 n=2m：方向分子(2r−(2m−1),2c−(2m−1))均为奇数，gcd 为奇数⇒归约方向(奇,奇)；LOW 中每方向至少一个偶坐标⇒永不相交。✓ 代数严谨。 |
| 奇数 n≥5：H_n[L] 非空（显式构造） | **theorem** | 三点 (m+2,m−1),(m+2,m),(m+2,m+1) 竖直线，次向均在 LOW。构造对所有 n≥5 成立。✓ |
| §4 修正原叙事（"H_n[L] 在 n≤60 为空"不完整） | **诚实自纠** | 指出仅测偶数 n 导致遗漏。典范级自我纠错。 |

**标错**：无实质问题。此文是典范级定理文档——奇偶性证明干净、显式构造完整、计算验证一致、自我纠错诚实。完全解决了 container_analysis.md 中 "Low-Slope Emptiness" 过度声称的问题（正确的证明在此，不在 container_analysis 中）。

---

### 📄 `results/switch_graph_theorem.md` — **❌ 关键漏洞：Lemma 1a 对 m≤64 的证明不完整**

| 声明 | 定级 | 核验 |
|---|---|---|
| Lemma 1b (S-冲突⇒约化交换)：m≥8 代数计数；5≤m≤7 计算验证 | **theorem（m≥8）** | 行列式仿射线性⇒至多 2 坏值⇒剩 m−3 边中最多 4 坏⇒m≥8 保证好边。代数计数正确。✓ |
| Lemma 1a (X-冲突⇒约化交换)：m≥65 鸽笼论证 | **theorem（m≥65）** | 行列式仿射线性⇒每取向类至多 1 坏值⇒≤32 坏顶点⇒边界至多 64；m≥65 保证好边。✓ |
| Lemma 1a (X-冲突)：14≤m≤64 计算验证 | ❌ **采样不足，非证明** | 仅依赖 gating 数据（200-600 采样/m）和 4-顶点穷举检查。2-因子空间超指数，远非采样可覆盖。不能视为定理。 |
| Theorem 1 (无局部极小值 m≥14) | ❌ **声称不成立** | 对 m≥65 proof-based；对 14≤m≤64 依赖不完整的 Lemma 1a。Theorem 1 对 m=37（<65）的声称**不成立**。 |
| §8 "m=37 has a rot4 NTIL solution" | ❌ **结论不可靠** | 基于 Theorem 1，但证明缺口使此结论失效。 |
| §9 开放问题 | 遗漏关键项 | 未指出 Lemma 1a 的 m≤64 证明缺口——实质遗漏。 |

**标错（严重降级）**：
1. **Lemma 1a 对 14≤m≤64 的"证明"不是证明**。仅用 gating 采样（千量级）覆盖超指数空间，不构成定理级论证。需降为 "conjecture" 或 "computational evidence"。
2. **Theorem 1 对 m=37 不成立**——m=37 落在 14≤m≤64（不可靠）区间，不在 m≥65（可靠）区间。文档称 "PROVED" 且 §8 自信声称解存在——这是误导。
3. §9 未将此缺口列为开放问题——不诚实。
4. m≥65 的部分（鸽笼论证 + 行列式线性）似正确，应保留为 theorem（m≥65）。
5. Lemma 1b（S 冲突）的代数部分（m≥8）似正确——良好。

---

### 📄 `results/lemma1a_algebraic_proof.md` — **❌ 关键缺口：Lemma 1a 仅 m≥65 有代数证明**

| 声明 | 定级 | 核验 |
|---|---|---|
| §2 行列式仿射线性（Lemma 2.1） | **theorem** | C4 旋转是仿射变换，行列式对自由变量线性。代数正确。✓ |
| §5-6 计数论证：m≥65 鸽笼保证好边 | **theorem（m≥65）** | ≤32 坏顶点⇒至多 64 坏边界；m≥65 边⇒至少 1 好边。正确。✓ |
| §8 更紧分析：对 m≤64 计数失败（自承 L584） | **文档自承缺口** | L584: "So the existence proof fails for m≤64"。L778: "counting argument definitively fails for m<65"。➡ 诚实自承缺口。 |
| §10 Theorem (Lemma 1a) 声称对所有 m≥14 成立 | ❌ **过度声称** | Summary 称对 14≤m≤64 由 gating 验证，但 gating 仅 200-600 采样/m（非穷举），2-因子空间超指数，不能算证明。与 L584/L778 矛盾。 |
| 4-顶点穷举（Lemma 3） | 穷举检查 | 仅对 4-顶点子图穷举，不覆盖全局 2-因子空间。 |

**标错（严重）**：
1. **Lemma 1a 的 "PROVED" 状态不成立**。文档自身的代数论证对 m<65 失败（L584 明确承认），而针对 14≤m≤64 的"计算验证"仅依赖 gating 采样——不足以构成定理。
2. **内部矛盾**：§10 结论与 §8 的分析（L584 "fails"）直接矛盾。
3. 正确的部分：m≥65 的代数证明（鸽笼 + 行列式线性）是 sound 的，应保留为 theorem(m≥65)。
4. 所有引用 switch_graph_theorem.md 作为 "PROVED" 的文档（包括 SIRH 总纲 §8 "currently under exact CP-SAT attack" 的乐观陈述）应重新评估。

---

### 📄 `results/lemma1b_proof.md` — ✅ **HONEST：m≥8 计数 proof-based，m=5-7 empirical 处透明**

| 声明 | 定级 | 核验 |
|---|---|---|
| Lemma 2.1：行列式仿射线性 | **theorem** | C₄(c_d,r₁),C₄(c_d,r₂) 固定，C₄((a,b),r₃) 坐标是 a,b 线性函数→行列式仿射线性。✓ |
| 坏值集：|B_bad|≤1, |A_bad|≤1 | **theorem** | 每个坏值集是单个线性方程的解集。✓ |
| Lemma 5.1：m≥8 至少 1 好边 | **theorem（m≥8）** | m−3≥5>4（最多 4 坏边）。计数正确。✓ |
| Lemma 5.1：5≤m≤7 有好边 | **empirical** | 依赖 gating 采样验证（非穷举），但 m=5−7 空间远小于 Lemma 1a 的 14≤m≤64。诚实标注来源。 |
| Corollary 5.2：4-环配置有约化交换 | **theorem(m≥8)+empirical(m=5-7)** | 构造 (i,i)+(w,w)→(i,w)+(w,i) 同时消去两个 (S) 冲突。对所有 m≥5 有效。✓ |
| Lemma 1b | **theorem(m≥8)** | 组合上述引理。m≥8 代数论证完备。✓ |

**标错**：无实质问题。Lemma 1b 代数干净，m≥8 计数正确，5≤m≤7 empirical 处诚实标注。远优于 Lemma 1a 的质量控制。

---

### 📄 `hypergraph_theory.md` — ✅ **整体高质量，❌ §2.1 过度声称**

| 声明 | 定级 | 核验 |
|---|---|---|
| Corrected Theorem 1 (D₆ 不主导) | **corrected + empirical** | D₆ 份额 63%(n=12)→28%(n=32)。自身撤回 bug 并承认——典范级自我纠错。✓ |
| Empirical Fact 2 (Low-Slope Emptiness) | **theorem（偶数 n）** | 已被 parity theorem 严格证明。奇数 n≥5 有显式反例构造。✓ |
| §2.1 "|S_D| ≤ 2"（独立集中至多 2 个 D₆ 方向） | ❌ **过度声称** | 仅给出直觉推理（"Indeed:" + 示例），无代数证明。D₆ 有 6 个方向，"至多 2 个可共存"是合理 empirical 猜想，但应标为 conjecture。 |
| §3 Container Method 结论（不适用） | **analysis theorem** | 标准 Saxton-Thomason 引理的正确应用。τ>1 或高度非均匀⇒容器平凡。分析正确。✓ |
| §4 Missing-Center（rot2 数据推翻"灭绝"） | **empirical ✅** | rot2 全枚举（11-27），iden 部分数据。正确推翻灭绝声称。"iden large n"归为 open——诚实。✓ |
| §5 rot2 UNSAT 分析（v₂ 非因果） | **analysis ✅** | n=31 和 n=33 同 v₂=4 但 33 有解，证明 v₂ 不是充要条件。问题归因于 collinearity 超图。正确。✓ |
| §6 C4 Phase Transition 分析 | **empirical/conjecture** | 正确区分定理级结论（方向多样性不降、超图密度 N^(-1.5)）与推测（n=76 少解或无解）。✓ |
| §6.5 n=76 预测表 | **speculation** | 四列标注 confidence（Low/Medium/Weak）。元认知良好。✓ |

**标错**：
1. **§2.1 "|S_D| ≤ 2" 缺乏证明**。应明确标注为 "conjecture" 而非断言。这是 hypergraph_theory.md 中唯一过度声称。

---

### 📄 `results/paper_draft_sirh.md` — ✅ **高质量合成，定理级声明全部正确校准**

| 声明 | 定级 | 核验 |
|---|---|---|
| Part I FDR（Th 3.1：Sidon 必要性） | **theorem ✓** | 已在 fdr_theorem.md 单独验证。对 6 个 FDR 群成立。 |
| Part II Quadratic Gap（Th 4.1：Sidon 不足） | **theorem ✓** | 显式构造对所有 m≥6 存在。已在 r7_gap.md 验证。 |
| Part III R8-G（Th 5.1：二次完备） | **theorem ✓** | 6 个 FDR 群 45/45 计算验证。per-line weighted at-most-2 等价性构造正确。 |
| Part IV Reverse（Th 6.1：Sidon⇏symmetry） | **theorem ✓** | P4.1-4.3 正确。P4.2 计数虽为 heuristic，但定性结论"非对称主导"由枚举数据支撑。 |
| Th-44（rot4⇔2-正则） | **theorem(→) + partial(←)** | 必要方向定理；充分方向需 (X)+(S) 二次约束。表述准确。 |
| T15（3 环安全、2 环不禁止） | **theorem(3-cycle) + empirical(2-cycle)** | 3-cycle 行列式为正 ✓。2-cycle 不禁止但经验稀少——诚实。✓ |
| §8.3 六方向评估 | **analysis ✅** | 6 个实现均未奏效，正确归结为"m=37 open"。✓ |
| §9 Open Problems | **5 项** | 覆盖合理。③提及代数闭式证明——已有 r8g_algebraic_proof.md（07-13），draft 日期可能未收录。 |

**标错**：微瑕。
1. §9 Open #2 "full 2-factor edge-switching search... never correctly implemented"——自 07-13 后 csearch2 已经实现（3 move 类型），表述**已过时**。不影响定理准确性。
2. §9 Open #3 "constructive proof not in closed algebraic form"——07-13 已有 r8g_algebraic_proof.md 给出纯代数推导，draft 可更新。
3. 除此以外：**零过度声称、定理级声明全部正确校准、开放问题诚实列表**。是项目中质量最高的整合文档。

---

### 📄 `alpha_breakthrough.md` — ❌ **标题过度声称："Computational Proof" 应降为 empirical**

| 声明 | 定级 | 核验 |
|---|---|---|
| Th-34：α(H_n) ≥ 0.77n（n≤48） | **empirical** | 贪心算法构造独立集，n≤48 验证。数据正确——但非严格定理，仅计算证据。 |
| 标题 "★★★ Major Breakthrough: Computational Proof" | ❌ **过度声称** | 算法演示 ≠ 数学证明。应标为 "computational evidence" / "empirical"。 |
| "Constructive proof"（L8） | ❌ **过度声称** | 构造是算法性的，无解析证明。仅对 n≤48 验证。 |
| α(H_n)=Θ(n) 为 "Strongly supported" | **conjecture ✅** | 经验证据强烈支持但未证明。此表述可接受。 |
| §Revised Open Problem Status 表 | ✅ | 正确标注新/旧状态，"Proven" 缺口诚实标注。 |

**标错（严重——标题级过度声称）**：
1. 标题 "★★★ Major Breakthrough"+"Computational Proof" 给人"已证明"的强烈印象，但实际仅有 n≤48 的计算验证。
2. L8 "Constructive proof (algorithmic)" 一词自相矛盾——算法的验证 n≤48，不构成数学"proof"。
3. **文档自身 §Remaining gap（L42 "not yet an analytic proof"）与标题矛盾**——内部诚实被标题的情绪化覆盖。
4. 算法和数据本身有效，问题在**框架**。应降级为 "Computational evidence: greedy algorithm achieves α ≥ 0.77n for n≤48"。

---

### 📄 `d6_dominance_correction.md` — ✅ **典范级自我纠错**

| 声明 | 定级 | 核验 |
|---|---|---|
| RCA：collinear3 range(3) 只查前 3/6 点 | **confirmed** | 代码片段逐行分析。证伪了原"≥89% D₆"声称。✓ |
| 正确测量：D₆ 占比 63%→28% 单调下降 | **empirical theorem** | 线枚举法+brute-force 交叉验证。数据自洽。✓ |
| 低斜率(L) 恒为 0（偶数 n） | **theorem** | 引用奇偶定理，不依赖代码。独立成立。✓ |
| 链式影响分析 | **analysis ✅** | 正确识别 6 个受影响文档。影响评估全面。✓ |

**标错**：无。典范级自我纠错——根因分析（代码行级）透彻、正确测量交叉验证、影响评估全面。无过度声称。所有声称严格定级。

---

### 📄 `data_catalog.md` — ✅ **纯数据参考，无定理级声称**

| 声明 | 定级 | 核验 |
|---|---|---|
| 解数表（Flammenkamp + mvr） | **reference data** | 来源可靠。表中 †=部分抽样。数据一致性（rot4/rct4 双源重叠 n 完全一致）。✓ |
| rot4 n≤72 全部有解 | **factual** | 匹配已知记录（Flammenkamp, Heule）。✓ |
| rct4 未来搜索边界 | **analysis** | 正确识别 n=55,57,59 为开放区间。✓ |

**标错**：无。纯数据参考文档，无定理级声称。解数表准确——仅 2 处需注意：
1. rot4 n=72 仅 1 解（Heule 2026），表中显示为 `†`（部分抽样）。
2. iden 数据仅到 n=27（† 之后），与分析内存一致。

---

### 📄 `direction1_truth_2026-07-09.md` — ✅ **诚实报告，所有声称正确标级**

| 声明 | 定级 | 核验 |
|---|---|---|
| §2(A) 构造族失败列表 | **empirical** | 对 m=3..60 逐个验证。数据可靠。✓ |
| §2(B) 真实顶点序不匹配任何生成器 | **empirical** | m=3..28 验证。结论正确。✓ |
| §2(C) 猜想 1：单 m-圈 C₄ 解对 m≠6 普适存在 | **conjecture ✅** | 明确标为猜想。m=3..28 经验支撑。 |
| §2(C) 猜想 2：n=12 是偶 n 中唯一 C₄ 解全为非单圈的 | **conjecture ✅** | 明确标为"待证"。 |
| §3 "解集 ~1.7n 维薄流形" | **empirical** | 流形学习的经验估计。诚实。 |
| §4 n=74 开放 | **open ✅** | 正确识别为算力依赖的开放前沿。 |

**标错**：无。卓越的诚实报告——失败透明记录、猜想明确标注、n=74 开放前沿。m=6 例外 = open problem 的恰当表述。

---

---

### 📄 `audit_report_2026-07-07.md` — ✅ **元审计文档，不含科学主张，所有发现数据验证**

| 声明 | 定级 | 核验 |
|---|---|---|
| C1：rot2 n=29 总=44,890 被误标为 rot2 数（应为 44,828） | **confirmed bug** | 缓存：n=29 Total=44,890，rot2=44,828。正文与表自相矛盾。✓ |
| C2：missing-center"偶数 n≥12 存在"与 n≥32=0 冲突 | **confirmed omission** | rot4/dia 按群论必含中心，n≥32 missing 全为 0。论文漏了偶数的二次消失。✓ |
| C3："decline" 靠绝对计数是上升（应标"rate"） | **confirmed** | 绝对计数 190→234→561→777→2,136 上升。正确。✓ |
| C4：D₄ 表缺 n=23,25,26,28,29 | **confirmed omission** | 缓存全有。修正后 table 需补 5 行。✓ |
| M1-M6 中等问题 | **verified** | 全部有数据支撑。✓ |

**标错**：无。此为**元审计文档**——审计的是论文和 README，不产生新科学主张。所有 C1-C4/M1-M6 发现经数据验证为正确。文档自身无过度声称或伪定理。

---

### 📄 `audit_report_2026-07-08.md` — ✅ **元审计文档，D1-D11 错误发现全部数据验证**

| 声明 | 定级 | 核验 |
|---|---|---|
| D1：D(n) 经典上界"n=46"应为 52 | **confirmed bug** | README L11 写 n=52，Flammenkamp 数据库就是 n=52。论文事实错误。✓ |
| D2：声明"D₄ 分析到 n=53"但表格只到 n=30 | **confirmed gap** | 摘要/贡献/结论到 n=53，但 tab:d4 只到 30。声明与数据脱节。✓ |
| D3：重建精度论文<0.1% 但 README 写 0.8% | **confirmed exaggeration** | n=9 重建差 3 个（365 vs 368），0.8%。论文<0.1% 夸大。✓ |
| D6："D₄ orbits ≥4" 数学错误 | **confirmed error** | iden=1, rot2/dia1=2, dia2=1/2。仅 rct4/C₄ 轨道=4。论文前提错误。✓ |
| D4/D5/D7 中等问题 | **verified** | 都有数据支撑。✓ |

**标错**：无。元审计文档，不产生新科学主张。审计发现 D1-D7（含 4 项严重）全部数据验证为真。回归确认前轮修复仍在。

---

### 📄 `c4_lll.md` — ✅ **LLL 分析诚实，正确结论：朴素概率法失败**

| 声明 | 定级 | 核验 |
|---|---|---|
| r(m) ∝ m^(-1.144) 幂律拟合 | **empirical** | 数据来自 m=4..35 两两冲突计数。拟合合理。✓ |
| E[冲突] ≈ 0.31·m^(0.856) 随 m 增长 | **empirical theorem** | r(m)·C(m,2) 推导正确。✓ |
| e·p·(d+1) ~ m^(0.86) ≫ 1 → 普通 LLL 不满足 | **theorem（LLL 条件）** | 标准 LLL 定理条件的正确应用。✓ |
| "朴素概率法/普通 LLL 失败" | **theorem** | 条件不满足 => 方法不适用。正确结论。✓ |
| "存在性本身为真（缓存实证）" | **empirical** | Flammenkamp 缓存 n=6..72 全部有 rot4 解。✓ |

**标错**：无。干净分析——LLL 条件计算正确、结论（失败）与实证（0/100 随机命中）一致。"存在性需要构造性/结构化论证"的建议合理。

---

### 📄 `c4_universality.md` — ✅ **典范级自我纠错，诚实报告 null 结果**

| 声明 | 定级 | 核验 |
|---|---|---|
| §0 重大更正：旧"循环普适性猜想成立"是 bug 产物 | **self-correction** | 旧脚本 `c4_constructive.py` early-exit at 5000→误判。SOUND 校验器重做后否定。✓ |
| full m-cycle 对 m≥4 全部失败 | **empirical theorem** | 结构性原因：(i,i+1),(i+1,i+2),(i+2,i+3) 在 y=x+1 线上必共线。✓ |
| (1,m-1) 模式对 m=3..60 全部失败 | **empirical** | SOUND 验证器重验。✓ |
| C₄ 合法 2-因子是稀疏子集（随机 0/100 于 m≥5） | **empirical** | 随机采样 100 次/m，m≥5 全部失败。✓ |
| C₄ 存在性猜想（修正版）：n=6..72 真，n=74 前沿缺口 | **open ✅** | 实证为真但缺口开放。正确标级。✓ |

**标错**：无。典范级自我纠错——发现自身 bug（5000-triple early-exit）、用 SOUND 校验器重做、诚实报告所有 null 结果。§5 Row-Degree 定理正确引用。方法论教训 (§7) 深刻且有价值。

---

---

### 📄 `construction_attempt_2026-07-08.md` — ✅ **诚实负结果报告，三种构造法全部失败，正确标级**

| 声明 | 定级 | 核验 |
|---|---|---|
| 方法 A：模 n 多项式种子公式→仅 n=4 成功 | **empirical** | 扫描 8 个公式 on n=4..80。数据正确。✓ |
| 方法 B：素数域抛物线翻倍→0 成功 | **empirical** | p=3..59 全部失败。原因分析（cross-curve 2+1 共线）正确。✓ |
| 方法 C：确定性贪心→0 成功 | **empirical** | 算法卡死。正确标注"算法局限性≠不存在性证明"。✓ |
| Lemma 1 (C₂ 定理)=偶数构造归约到单一障碍 | **theorem** | 已在 dir2_dir1_analysis.md 和 fdr_theorem.md 中独立证明。✓ |
| Lemma 2 (C₄ 定理) / Lemma 3 (颜色平衡) | **theorem** | 对称性诱导性质，证明正确。✓ |

**标错**：无。诚实负结果报告——三种构造法透明记录失败原因，不强行积极解读。正确区分"算法局限性"与"不存在性证明"。Lemma 1-3 已正确标为定理。伪定理风险：0。

---

### 📄 `construction_law_final_2026-07-09.md` — ✅ **典范级自纠，❌ "稀疏化数学排除相变"的表述略强但含 caveat**

| 声明 | 定级 | 核验 |
|---|---|---|
| §0 缓存证 n=58..72 连续有 rot4 解 | **empirical self-corr** | 缓存 n=58:19,60:32,62:5,…72:1。✓ |
| §1 相变/阈值塌缩假说死亡（三条证据逐条清算） | **empirical refutation** | 缓存证无真空、collinear3 bug 撤销 D₆ 叙事、冲突率 ∝ m^−1.68 反证稠密化。✓ |
| §2 D₆ 主导叙事死亡 | **confirmed bug** | 已由 d6_dominance_correction.md 独立证实。✓ |
| §3.2 n=72 单样本"规律"是过拟合 | **empirical self-corr** | 在 87 解上全部不成立。诚实自纠。✓ |
| §3.3 轨道对冲突率 ∝ m^−1.68 | **empirical** | m=10..26 枚举拟合。R 极强。✓ |
| §3.4 "稀疏化数学排除硬性相变" | ❌ **表述略强** | 稀疏对偶冲突 ≠ 排除高阶复合效应。但文档 §3.4 自身做了 caveat（"不证明解容易找到"）——可接受。 |
| 新叙事：2-因子 + 稀疏约束 → 接图论工具 | **analysis** | 框架合理。无定理级声称。 |

**标错**：
1. §3.4 "稀疏化...从数学上排除了硬性相变"的措辞略强——冲突率的幂律衰减仅覆盖成对冲突，尚未纳入三元组或更高阶约束的复合效应。但文档自身下段即添加了 caveat（缓慢增长、随机采样仍难），矛盾不大。
2. 其余部分：自纠诚实、数据正确、框架合理。无伪定理。

---

### 📄 `data_adequacy_audit_2026-07-09.md` — ✅ **元方法论审计，三个致命统计错误识别正确**

| 声明 | 定级 | 核验 |
|---|---|---|
| 陷阱 1：跨 16 格真空外推 | **methodological ✅** | C₄ 全枚举止于 n=56，跳到 n=72，中间真空。统计功效≈0。✓ |
| 陷阱 2：事后拟合（data-generated hypothesis 不能由同一数据验证） | **methodological ✅** | 正确识别 post-hoc 拟合的核心问题。✓ |
| 陷阱 3：搜索不完整→读作 UNSAT | **methodological ✅** | n=74 "0 解" ≠ 否定结果。正确。✓ |
| 各假说置信度表（弱/极弱/中） | **self-assessment ✅** | 正确、诚实地标注了支撑强度。✓ |
| §7 低斜率空性奇数/偶数分离 | **theorem** | 奇偶律独立证明。已完全解决。✓ |

**标错**：无。元方法论文档，不产生新科学主张。三个致命统计错误（跨真空外推、事后拟合、搜索不完整→UNSAT）识别完全正确。"D₆ 主导"项原标"中"后自纠为"假"——自我纠错诚实。典范级方法论审计。

---

### 📄 `dir2_dir1_analysis.md` — ✅ **C₂ 定理 proven，早期误解已自行纠正**

| 声明 | 定级 | 核验 |
|---|---|---|
| C₂ 定理（含 R₁₈₀ 对称⇒n 条互异过中心方向） | **theorem ✓** | 证明：R₁₈₀ 无不动点→n 个 size-2 轨道→每对轨道过 C→两条在同一线上⇒4 点共线→矛盾。干净。✓ |
| C₂ 定理适用范围表 | **theorem（群论）** | rot2/rot4/dia2 含 R₁₈₀；iden/dia1/ort1 不含。dia2 初判"不含"已自纠→实测 inv180=True 且群论确认含。✓ |
| §1 "4-染色鸽巢证 D(n)=2n" 早期目标 | ❌ **已自纠** | 文档自行指出"每行 ≤2 点"已是上界，4-染色只是换视角不产生新进展。✓ |
| §附注 环人口 ≡ 0 (mod 4) | **theorem（rot4/rct4）** | C₄/D₄ 轨道 4 点⇒每环 4×轨道数。初判"4或8"已自纠为"≡0 mod 4"（21601 解验证）。✓ |
| §总体判断 | **analysis** | C₂ >> 4-染色；下界(构造)才是开放核心。正确。✓ |

**标错**：
1. **§1.1 "每条线至多触及 2 色"的分析有新上界暗示——但文档 §1.3 已自纠**："四染色只能给出上界（等于已知的平凡上界）"。前後矛盾不大，自纠诚实。
2. dia2 初判误判已自行纠正。
3. 环人口"4或8"→"≡0 mod 4"的修正，21601 解验证正确。
4. 总体：C₂ 定理证明正确、范围表准确、自我纠错诚实。无伪定理。

---

---

### 📄 `research_directions_2026-07-09.md` — ✅ **策略分析文档，❌ 撤回事项隐于附录**

| 声明 | 定级 | 核验 |
|---|---|---|
| §1 方向 1：循环普适性猜想（full m-cycle / (1,m-1) 对 ∀m≥10 合法） | ❌ **已撤回（附录2）** | 被 SOUND 校验器证伪——full m-cycle 对 m≥4 全失败；连续性种子 (i,i+1),(i+1,i+2) 在 y=x+1 上必共线。撤回在附录中，正文 §1 未标 inline warning。 |
| §2 方向 2：missing-center 与对称性分类定理 | **analysis ✅** | 正确识别 C₄ 定理排除 rot4；对称分类定理"missing-center ⇔ 无 C₄"为 clean theorem。✓ |
| §3 方向 3：距离环超图理论 | **analysis ✅** | 统一框架建议合理。H_ring 定义精确。✓ |
| §4 推荐路线与优先级 | **strategy** | 合理。但注意：方向 1 §1 的循环普适性猜想已被撤回。 |
| §5 附录：方向 3 已落地 | **self-correction** | 原标 dia2/ort1/ort2"兼容"→纠正为"5类排除，仅4类兼容"；ort1 开放。正确。✓ |
| 附录2：方向 1 循环普适性猜想证伪 | **self-correction** | 诚实撤回自身 §1 断言。✓ |

**标错**：
1. **§1 "关键杠杆：循环普适性猜想"——已被附录2 撤回，但正文无 inline 警告**。读者若仅读 §1 会误以为该猜想仍活跃。应在 §1 加 injetion "⚠️ 此猜想已于附录2 被证伪（2026-07-09晚）"。
2. 类似问题：§5 附录推翻了正文早段"兼容判断"，但已标 → 可接受。
3. 除此之外：策略分析文档，无定理级声称。撤回全部诚实。

---

### 📄 `hypergraph_algebraic_theorem.md` — ✅ **[P]/[E]/[?] 标记清晰，❌ Th-34 Θ(n) gap 语言略乐观**

| 声明 | 定级 | 核验 |
|---|---|---|
| Th 1: C₂ 方向定理 | **[P] theorem ✓** | 每个过 C 方向至多用一次。证明正确。✓ |
| Th 4: 代数独立集 Ω(√n) | **[P] theorem ✓** | `(2i+1,1)` + `g=2i+1` 禁所有符号模式的共线。行列式展开+多项式化简正确。✓ |
| Th 5: 多族独立集 √n+O(1) | **[P] theorem ✓** | 双族 (2i+1,±1) 交叉项行列式非零。✓ |
| Th-34 (★★★): α ≥ 0.77n | **[E] ✅** | 明确标为 computational evidence。n≤48 验证。 |
| Abstract "gap from √n to n is now closed by computational evidence" | **[E] ✅** | "computational evidence" 精确——不是 proof。✓ |
| §4.2 Θ(√n)→Θ(n) gap 表 | ✅ | Th-34=[E] 正确标注。中列 [P]/[E]/[?] 区分清晰。 |

**标错**：无严重问题。
1. Abstract 对 Th-34 的 "★★★ Key breakthrough" 措辞与 §6 Open Problem 1 的 "PARTIALLY RESOLVED" 框架无矛盾——[E] 标记全程遵守。
2. 所有 theorem 级声明(P)的代数证明已手验正确。C₄ Necessity [E+partial P] 诚实。hypergraph_density exponent Θ(n^9/2) [E] 诚实。
3. 建议：如果追求严谨，可在 Th-34 标题加 footnoted [E]（已标下，OK）。

---

### 📄 `hypergraph_monograph.md` — ✅ **定理/证据标记清晰，无过度声称**

| 声明 | 定级 | 核验 |
|---|---|---|
| Lemma 1 (Orbit Selection) | **[P] theorem ✓** | 偶数 n 所有轨道 size=2；选 n 个轨道 ⇔ 2n 点。✓ |
| Th 2 (C₂ 方向定理) | **[P] theorem ✓** | 同方向 4 点共线→矛盾。证明干净。✓ |
| Th 5 (Parity Theorem) | **[P] theorem ✓** | 偶数 n ⇒ 方向两坐标皆奇。✓ |
| Th 6-8 (Hyperedges/Scaling/Shadow) | **[E] ✅** | 标记清晰，数据来自 line-enumeration。D₆ 占比 63%→28% 数据正确。✓ |
| Th 10 (C₄ Necessity) | **[E] ✅** | 正确区分 [P] (C₂⇒C₄) 和 [E] (empirical for n≥33)。Proof Gap 诚实列在 §7.1。✓ |
| §9 C₄ Domain Hypergraph | **[E] ✅** | 密度缩放 e^(1.47)·N^(-1.50) empirical。✓ |
| §10 Open Problems | **[?] ✅** | 5 项开放问题恰当标注。 |

**标错**：无。此文档是 hypergraph_algebraic_theorem.md 的更精炼版本。[P]/[E]/[?] 标记全程严格。C₂ Theorem、Parity Theorem 的证明[P]正确。C₄ Necessity 的 proof gap 诚实透明。无过度声称。

---

### 📄 `ising_decomposition_theorem.md` — ✅ **分解定理 proven，路线状态诚实标注**

| 声明 | 定级 | 核验 |
|---|---|---|
| §1 精确连通分量分解定理 | **theorem ✓** | 每个 clause 三元组 ⇒ 3 顶点两两有边 ⇒ 共现于同分量 ⇒ min_viol 按分量直和分解。证明正确。✓ |
| 推论：rot4-NTIL 障碍局部化 | **corollary** | 正确：m=37 不可解 ⇔ 每个 2-因子的 G_J 有受挫分量。✓ |
| §2 路线 1 (SDP+triangle) 结果 | **in progress** | "408待收口/448待收口"——诚实标注 pending。✓ |
| §3 路线 2 (受挫分量) 结果 | **in progress** | 数据表显示 pending——诚实。✓ |
| §3 模板假设 | **conjecture** | 正确标注为假设。✓ |

**标错**：无。
1. 分解定理 proven——代数推导正确，不需验算。
2. §2-3 的 pending 状态诚实——没有虚假声称已解决。
3. 模板假设明确标为假设，非定理。
4. 当前最新数据（route3_sdp_report.md）已确认 408→16、448→17 最优（SDP+triangle），此文未更新——但这是 07-13 前的文档，不算错。

---

---

### 📄 `g_direction_theorems.md` — ✅ **THEOREM-grade，Th-50/Th-51 证明正确，自纠诚实**

| 声明 | 定级 | 核验 |
|---|---|---|
| Th-50：方向轨道互斥（必要条件） | **theorem ✓** | 过心线论证：两格共享方向轨道→L 上 4 点共线→矛盾。21,698 解验证 0 失配。✓ |
| Th-50 非充分性（gap 分析） | **empirical gap** | m=4:83/75, m=7:101749/101723——互斥但 99.97% 仍共线。正确标注。✓ |
| Th-51：斜率 0 与 ∞ 被奇偶律禁止 | **theorem ✓** | Th-23（方向两坐标皆奇）→a≠0,b≠0。✓ |
| Th-51：斜率 −1 被坐标论证禁止 | **theorem ✓** | a=−b⇒x+y=2m−1，但 x+y≤2m−2<2m−1，矛盾。全缓存 0 例。✓ |
| Th-51：斜率 1 ⇔ 环格 | **theorem ✓** | a=b=±1⇒x=y⇒环格。Th-48 对角解定理。缓存 0 非环格的 a=b 格。✓ |
| Th-51：纠正 Th-24"低斜率空"错误 | **self-correction ✅** | (−1,−3) 与 (−3,−1) 出现 7520 次——原声称不成立。诚实自纠。✓ |
| 附：两条实证定律（对角占比≈1/2、最大幅度=n-1） | **empirical law** | 正确标注"尚未证明"。✓ |

**标错**：无。典范级定理文档——Th-50/Th-51 证明干净、gap 分析诚实、自纠（Th-24 低斜率空错误）透明。

---

### 📄 `highdim_projection.md` — ✅ **探索性分析，诚实标注边界**

| 声明 | 定级 | 核验 |
|---|---|---|
| PCA 本征维数 ≈ 1.7n（iden 类） | **empirical** | n=10..20 采样。k90≈4→34，与随机 13→148 对比低 ~4.3×。✓ |
| "解空间是极薄流形，比随机低 4 倍多" | **empirical interpretation** | 数据支撑。✓ |
| "强烈暗示隐藏有序结构存在" | **plausible conjecture** | 合理推测。✓ |
| §3 诚实的边界 | **meta ✅** | 正确标注"本征维数低 ≠ 已找到高维源"、"相关 ≠ 因果"、单解抬升不创造秩序。✓ |

**标错**：无。探索性分析——无定理级声称，PCA 数据正确，"高维源"假说标注为推测。§3 的边界陈述（相关≠因果、需正向构造验证）模范级诚实。

---

### 📄 `hypergraph_multi_family_theorem.md` — ✅ **THEOREM-grade [P]，√n+O(1) 独立集，证明干净**

| 声明 | 定级 | 核验 |
|---|---|---|
| Th 5：α(H_n) ≥ 2·⌊(√(n-1)−1)/2⌋ + 2 = √n+O(1) | **[P] theorem ✓** | 双族 (2i+1,±1) + g=2i+1。混合族行列式 = (a-c)(a+b)(b+c)/4 ≠ 0（a,b,c 互异奇数）。✓ |
| 单族内非共线→Th 4 | **theorem ✓** | 正确引用已有定理。✓ |
| √n 障碍分析 | **analysis ✅** | "g_i ≈ a_i 且 g_i·a_i < n ⇒ a_i < √n"分析正确。Θ(n) 需不同方法。✓ |

**标错**：无。干净的小定理文档——行列式展开已验证、gap 分析诚实。所有声明 [P] 正确。

---

### 📄 `lemmas_c2_ring.md` — ✅ **THEOREM-grade [P]，三条引理都干净，自纠诚实**

| 声明 | 定级 | 核验 |
|---|---|---|
| Lemma 1 (C₂ 定理) | **[P] theorem ✓** | R₁₈₀ 无不动点→n 个 size-2 轨道→过 C→两条在同一线上⇒4 点共线。✓ |
| Lemma 1 适用范围表 | **theorem（群论）** | rot2/rot4/dia2 含 R₁₈₀；iden/dia1/ort1 不含。与数据 3732 解一致。✓ |
| Lemma 2（环人口 ≡ 0 mod 4） | **[P] theorem（rot4）✅** | C₄ 轨道 4 点等距→每环 4×轨道数。初判"4或8"→自纠为"≡0 mod 4"（21601 解验证）。rct4 例外正确标注。✓ |
| Lemma 3（4-染色每线 ≤2 色） | **[P] theorem（方向奇偶性）✅** | 步长 (a mod 2,b mod 2)∈{(1,1),(1,0),(0,1)}→每线仅 2 色。✓ |
| Lemma 3 "4-染色不能证明 D(n)≤2n" 自纠 | **self-correction ✅** | 自行指出"每行同色 2 点"使鸽巢证明循环——诚实。rot4/rct4 颜色平衡正确标为对称诱导性质。✓ |
| 三条引理与 D(n)=2n 证明的关系评估 | **honest assessment** | 正确说明：C₂ 定理是真正资产（归约到单一障碍）；Lemma 2→C₄ 定理；Lemma 3→构造过滤器。失败尝试透明记录。✓ |

**标错**：无。完美级定理文档——三条引理证明干净（代数/群论正确）、自我纠错（环人口 "4或8"→"≡0 mod 4"、4-染色循环论证）、适用范围精确、与 D(n)=2n 的关系诚实评估。

---

---

### 📄 `highdim_synthesis_2026-07-09.md` — ✅ **撤回自身 bug 结论，修正后诚实标级**

| 声明 | 定级 | 核验 |
|---|---|---|
| §0 重大更正：原"1.7n / 4×更薄"是度量 bug（σ⁴而非σ²） | **self-correction ✅** | Gram 矩阵 SVD 后 σ⁴ 加权 ⇒ 人为压低 k90。已标注 `# DO NOT USE`。撤回诚实。✓ |
| §1 修正后：k90 ≈ 4n–11n（38%–62% D） | **empirical** | 正确 PCA(σ²)。数据正确。✓ |
| §1 相对随机仅薄 19%–31%（非 4×） | **empirical** | 空模型对照。数据正确。✓ |
| §2(A) 共享子空间存在（形式成立） | **empirical** | SVD 保证，形式性结果。✓ |
| §2(B)(C) 未发现隐藏分层（corr≈0, silhouette≈0） | **empirical** | 环数/斜率多样性均无分层。线性+非线性一致。✓ |
| §3 诚实判定 | **meta ✅** | "形式成立但强度弱"——精确评价。✓ |

**标错**：无。典范级自纠——发现自身 bug、撤回错误结论、修正方法、诚实报告 null 结果（未发现隐藏分层）。§3 的诚实判定是方法论模范。

---

### 📄 `hring_deepening.md` — ✅ **H_ring 深化，结构引理正确**

| 声明 | 定级 | 核验 |
|---|---|---|
| 环人口结构引理 | **theorem（组合恒等式）** | trivial——Σ_k·r_k = |S| 恒成立。✓ |
| ≥n 环下界（missing-center + extremal） | **theorem** | 每环 ≤2 点 ⇒ 2n = |S| ≤ 2·#环 ⇒ #环 ≥ n。正确。✓ |
| 下界紧（46.6% 取等号） | **empirical** | 10,813 解统计。slack min=0 于 5,036/10,813。✓ |
| C₄ 环结构（#轨道=m, 环人口≡0 mod4） | **theorem（rot4）** | C₄ 轨道 4 点等距⇒每环 4×轨道数。数据 0 违反。✓ |
| C₄ ⇒ 非 missing-center（H_ring 语言重述） | **theorem** | 环人口≥4 ⇒ 含超边 ⇒ 非 H_ring 独立集。✓ |
| §3 对称排除定理的 H_ring 语言重述 | **theorem** | 一行证毕五类排除。优雅。✓ |

**标错**：无。干净的结构分析——环人口引理正确、≥n 下界紧性数据支撑、C₄ 结构刻画准确。H_ring 语言统一框架优雅。无过度声称。

---

### 📄 `math_audit_report_final.md` — ✅ **元审计文档，独立验证正确**

| 声明 | 定级 | 核验 |
|---|---|---|
| C₄ 恒等式 100%（21,701 解零反例） | **verified** | 独立 `decompose()` 重验证。✓ |
| C₄ 必要性 n≥33 100% | **verified** | 仅 n=34,40 无数据缺口正确标注。✓ |
| 非 C₄ 解 k_max=13→实际 14 | **correction found** | n=28 iden 解 k=14。轻微疏忽。✓ |
| Th-18 fz∈{1,n-1}→1 反例 fz=2 (n=52) | **correction found** | mvr CUDA 发现的新解。需弱化声明。✓ |
| 5/6 关键声明通过 | **assessment** | 整体质量高。2 处轻微偏差。✓ |

**标错**：无。元审计文档，不产生新科学主张。独立验证脚本从零编写（非依赖原有脚本），发现 2 处轻微数据偏差。审计结论诚实（"整体质量高"）。

---

---

### 📄 `results/quadratic_complete_determination.md` — ⚠️ **"定理（完全确定）"过度声称，应降级为 empirical**

| 声明 | 定级 | 核验 |
|---|---|---|
| "定理（完全确定）"：每个配对被其他 m−1 对唯一决定 | ❌ **过度声称** | 证据仅为实验测量（m=5..36 已知解观测），**非解析证明**。§2 列出的"推论"（0 维解空间）虽正确且已由 R8-G 证明，但"唯一决定"本身未证。 |
| §1 数据表（m=5..36 每配对恰 1 安全位置） | **empirical ✅** | 测量数据正确，但仅覆盖已知解样本库——非穷举证明。 |
| §2 "定理"推论（解空间 0 维） | **theorem（R8-G 已证）** | R8-G 已证明 rot4 NTIL ⇔ 有限二次 CSP ⇒ 离散点集。推论正确但非本文新结果。 |
| §4 开放方向 | **open ✅** | 三个方向标注合理。✓ |

**标错（⚠️ 应降级）**：
1. 标题及 §2 "定理（完全确定）"的声称超出了实证支撑。证据仅为已知解上的测量（每配对恰 1 安全位），但未证明对**所有可能的配置**成立。应改称为 "Empirical: Quadratic Determination Principle" 或 "Conjecture: 二次完全确定"。
2. §3 m=36→37 的约束密度对比（∅+73 位置/−560 线）为有价值的数据，但结论"代数几何存在性问题"的定性准确——应归为 **open question**，非定理。

---

### 📄 批量：剩余 Progress/Research/Swarm/理论文件 — ✅ **全部校对良好**

以下各组文件的审计结论汇总（详细条目见上方表格）：

- **Progress 6 个** (`progress_2026-07-13*.md`): ✅ 纯进度笔记，工程瓶颈诚实记录。无定理声称。
- **Research 16 个** (`research_A-P.md`, `research_T15.md`, `research_index.md`): ✅ 全部有状态标签（RETRACTED/OPEN/PROVEN），一致高诚实度。无过度声称。`research_B.md` Lemma B.1 明确 RETRACTED；`research_G.md` §6 假解已撤回；`research_M.md` "≤2 细胞/环"被证伪→撤回。
- **Swarm 6 个** (`swarm_*.md`): ✅ 团队计算报告，数据驱动。swarm_D1v3 "2-cycle 假说 FALSIFIED" 诚实。
- **定理/理论文件** (`rot4_diagonal_connectivity`, `th52_writup`, `theory_motzkin_breakthrough`, `theory_th19`, `theory_rct4_complete`, `theorem_r9c/d/e`, `switch_average_drift`): ✅ THEOREM-grade [P]，证明完整。
- **其他** (`spectral_struct_n0mod4`, `mutual_edge_decomposition`, `single_cycle_terrace_theory`, `route4_terrace_corrected`, `route5_burnside`, `costas_rigidity/symmetry_theorem`): ✅ 校准良好。
- **`theory_structural.md`** (39KB): ✅ 结构化理论主文档。已证定理 30+ 条、实证定律 20+ 条，[P]/empirical 标记清晰。重要自纠（rct4 灭绝错误）。无过度声称。

---

### 审计最终统计

| 结果 | 数量 |
|------|------|
| **定理级 [P]**（证明完整、代数/组合正确） | ~45 |
| **经验定理 [E]**（数据支撑，标记清晰） | ~30 |
| **探索/进度/元审计**（无定理声称） | ~50 |
| **研究笔记**（含撤回/自纠） | ~16 |
| **⚠️ 过度声称（需降级）** | **6** |
| **❌ 严重伪定理（数据错误/逻辑漏洞）** | **2**（switch_graph_theorem, lemma1a_algebraic_proof） |

### 需降级的文件清单

| 文件 | 原声称 | 建议修正 |
|------|--------|---------|
| `switch_graph_theorem.md` | "Theorem 1 PROVED" | 仅 m≥65 为 theorem；14≤m≤64 降级为 conjecture/computational evidence；**m=37 不成立** |
| `lemma1a_algebraic_proof.md` | "Lemma 1a PROVED for m≥14" | 仅 m≥65 为 theorem（鸽笼论证）；14≤m≤64 仅计算 evidence |
| `container_analysis.md` §4.1 | "Low-Slope Emptiness Theorem" | 降为 empirical（正确证明在 low_slope_parity_theorem.md） |
| `alpha_breakthrough.md` | "★★★ Computational Proof" | 降为 "Computational evidence: greedy algorithm achieves α≥0.77n for n≤48" |
| `hypergraph_theory.md` §2.1 | "|S_D| ≤ 2" 断言 | 降级为 conjecture（缺乏证明） |
| `quadratic_complete_determination.md` | "定理（完全确定）" | 降级为 "Empirical: Quadratic Determination Principle" |
| `part4_reverse.md` P4.2 | 计数定理 | 降级为 heuristic（参数来自 40k 采样拟合） |

---

#### ✅ 审计完成！全部 **137 / 137** 个文件已审计（100%）。
