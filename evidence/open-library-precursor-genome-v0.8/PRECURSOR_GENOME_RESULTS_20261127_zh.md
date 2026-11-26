# Precursor Genome 第三实测来源结果（已消费来源）

日期：2026-11-27

## 结论先行

第三实测面板通过准入、重复运行和本地发布审计。它的主结果支持当前论文的窄结论：

> 完整候选库输出不能自动作为缩减候选库部署时的可用证据。候选排序与
> deployment-available unknown evidence 是两个不同端点，而且不同方法的
> 表现并不相同。

这不是一个新外部来源。本项目旧闭库 benchmark 已经使用过 Precursor Genome
的 416 条查询；本面板 102 条查询中有 77 条 ID 与旧队列重合，只有 25 条新。
在查看 open-library 方法分数前，本面板的选择规则和案例语义已经冻结，但它
只能写作“已有来源上的新干预”，不能写作 new external holdout 或 prospective。

## 来源与隔离

- Zenodo DOI：`10.5281/zenodo.21285546`；
- 版本：1.0；
- 许可：CC BY 4.0；
- 原始规模：1,035 个 A-Lab 反应、1,351 条扫描、1,950 个精修案例；
- ledger SHA-256：
  `f8b8aabb5b8718ad912075b9aa10373a5e81659b496348f14c926e432eb42dac`；
- `raw_scans.zip` 大小 23,008,523 bytes，MD5
  `e22405e733fc79ff4b14b679f87a33d5`；
- `refinement_pkls.zip` 大小 291,408,941 bytes，MD5
  `49447823b4e017524fd963ec3734af74`。

准入规则：

1. 活动精修案例 accepted；
2. 人工质量分 1 或 2；
3. 完整真值相数 2-4；
4. 样品相集与活动精修相集一致；
5. 没有 physical-failure 标记；
6. 扫描和精修 pickle 均存在。

从 883 个合格反应中，按出现反应数选出前 20 个相家族。完整覆盖该候选库的
114 个反应中，20 个反应仅用于构造参考谱且全部排除，最终得到：

- 102 个独立查询反应；
- 92 个二相、10 个三相反应；
- 80 个 quality-1、22 个 quality-2；
- 87 个 unreacted、15 个 transformed；
- 214 条真实相权重记录，最小值 `0.0089783733`；
- 只有 8 条真实相权重低于 5%。

20 个参考反应与 102 个查询反应完全不相交。每个物理反应只使用一条活动扫描，
重复扫描不进入独立样本数。

候选参考谱来自 source-fitted refinement profiles，不应写成从零开始的结构模拟或
ab initio 纯相计算。它们是公开数据中的拟合峰位、积分强度和 h/k/l 表示。

## 数据拆分修正

最终数据不是最初草稿中的 `dataset_v6` 和 `cases_v7`：

- `dataset_v7` 的公开 `queries.csv` 只含 query ID、cluster ID、谱路径和波长；
- 源真值派生的 `quality_score`、`phase_count` 和扫描 lineage 移入
  evaluator-only `query_metadata.csv`；
- `cases_v8` 使用准确的 `reference_profile_file` 字段，不再把参考谱路径
  命名为 `cif_file`。

与旧版相比：

- candidate profiles、sticks、全部谱文件和 truth 逐字节不变；
- cases、case truth、provenance 和 library manifest 逐字节不变；
- 旧版与最终版 CrystalShift 的 21 个库、63 个底层输出逐字节一致；
- 四张 assembled candidate/case 输出也逐字节一致。

因此，命名和公开/私密拆分修正没有改变任何数值结果。

## 主结果

### Unknown evidence

2 个真实/不存在删相对照端点的 AUROC：

| 方法 | 实际缩减库 | 完整 residual 复用 | 直接差 | 10,000 次簇 bootstrap 95% CI |
| --- | ---: | ---: | ---: | --- |
| shifted Pearson 正对照 | 0.7082 | 0.5071 | +0.2011 | `[0.1848, 0.2167]` |
| CrystalShift | 0.8044 | 0.5024 | +0.3019 | `[0.2737, 0.3318]` |
| XDecomposer | 0.5633 | 0.5061 | +0.0571 | `[0.0329, 0.0839]` |

三种方法的可用 unknown evidence 都高于完整 residual 复用，且置信区间全部
高于零。最强的 CrystalShift 效应约比 XDecomposer 大五倍。

不可用 shortcut 仍显著乐观：

- profile baseline：0.9671；
- CrystalShift：0.9436；
- XDecomposer：0.9728。

这些分数只能在分析阶段通过完整库中已删除候选的信息计算，部署时不可获得。

### Ranking

214 个真实删相案例中，只有 30 个在删除后仍至少保留两个真实相，因此可估计
“剩余真实相之间的顺序”：

| 方法 | 剩余真实相排序变化 | 完整候选排序变化 |
| --- | ---: | ---: |
| shifted Pearson 正对照 | 0/30 | 0/214 |
| CrystalShift | 4/30 = 13.3% | 174/214 |
| XDecomposer | 0/30 | 0/214 |

CrystalShift 的 4/30 区间为 `[0.0333, 0.2424]`。这再次说明：

- 完整候选列表变化很大；
- 但剩余真实相的相对顺序只在少数案例中变化；
- 不能把 `174/214` 写成“剩余真实相排序变化”。

## 预先冻结的敏感性

| 子集 | 方法 | 实际 AUROC | 复用 AUROC | 直接差 | 95% CI |
| --- | --- | ---: | ---: | ---: | --- |
| quality 1，80 queries | profile | 0.7076 | 0.5092 | +0.1984 | `[0.1798, 0.2166]` |
| quality 1，80 queries | CrystalShift | 0.7997 | 0.5039 | +0.2959 | `[0.2664, 0.3272]` |
| quality 1，80 queries | XDecomposer | 0.5533 | 0.5048 | +0.0486 | `[0.0215, 0.0788]` |
| unreacted，87 queries | profile | 0.7061 | 0.5000 | +0.2061 | `[0.1864, 0.2245]` |
| unreacted，87 queries | CrystalShift | 0.8091 | 0.5000 | +0.3091 | `[0.2758, 0.3443]` |
| unreacted，87 queries | XDecomposer | 0.5635 | 0.5000 | +0.0635 | `[0.0355, 0.0944]` |
| omitted weight ≥5% | profile | 0.7234 | 0.5145 | +0.2090 | `[0.1906, 0.2268]` |
| omitted weight ≥5% | CrystalShift | 0.8227 | 0.5091 | +0.3136 | `[0.2848, 0.3435]` |
| omitted weight ≥5% | XDecomposer | 0.5611 | 0.5087 | +0.0524 | `[0.0276, 0.0796]` |

所有 sensitivity 的直接差均为正，95% 区间均不跨零。unreacted 子集全部为二相，
因此其剩余真实相排序不可估计，不能强行给出 `0/0` 以外的解释。

## 这项结果补上了什么

结合修正后的 Algarve 和 Dara 结果，三来源证据形成以下模式：

| 来源 | CrystalShift retained-order change | CrystalShift actual-minus-reused CI |
| --- | ---: | --- |
| Algarve | 2/9 | `[+0.2440, +0.3201]` |
| Dara | 15/30 | `[+0.3044, +0.4036]` |
| Precursor Genome | 4/30 | `[+0.2737, +0.3318]` |

排序变化比例跨来源不同，但 unknown evidence 端点分离方向一致。正对照也有作用：
XMatcher、profile correlation 和 XDecomposer 的候选排序不变，但完整 residual
复用并不因此自动有效。

## 不能写的话

不能写：

- “三个来源证明所有 PXRD 方法都有同样问题”；
- “Precursor Genome 是时间前瞻实验”；
- “XDecomposer 是强 unknown-phase detector”；
- “CrystalShift 在 174/214 个案例中破坏剩余真实相排序”；
- “候选库会改变结果是本文首次发现”；
- “本 benchmark 已证明某个模型达到 SOTA”。

可以写：

- 三来源的 unknown evidence 都显示完整 residual 复用失效；
- 排序端点依赖方法；
- 正对照和失败对照同时存在；
- 结果在不同化学体系、仪器和候选表示上方向复现；
- 绝对性能不跨来源池化，不是 SOTA leaderboard。

## 复现与审计

- CrystalShift：Julia 1.10.13，commit
  `c4884ca1dbbd78135cd50f5e17141cdc0b6f43c8`，21 个库全部完成；
- profile baseline：CPU，确定性；
- XDecomposer：官方 V_0.0.1 checkpoint，CUDA deterministic inference；
- 10,000 次 bootstrap 全部主指标完成；
- 21 个库重复运行 63 个底层文件，0 mismatch；
- 四张 assembled 输出，0 mismatch；
- 本地 release audit：9,855 checks passed；
- audit SHA-256：
  `bbae068e9f54c33a783b20fd77097a90e17a61f0cce6ad96b9fbab90519e4215`。

核心文件：

- `dataset_v7/manifest.json`；
- `cases_v8/manifest.json`；
- `crystalshift_run_v8/execution_status.json`；
- `profile_baseline_run_v8/execution_status.json`；
- `xdecomposer_run_v8/execution_status.json`；
- `scores_v8/summary.json`；
- `sensitivity_v8/summary.json`；
- `selection_v3/SELECTION_MANIFEST.json` 中的 `claim_correction`；
- `RELEASE_AUDIT_20261127.json`。

## 当前定位

第三来源增加了大规模同任务复测，但没有增加 102 个全新项目外样本；其中
77/102 已被旧闭库 benchmark 使用。它不能替代真正的前瞻实验，也没有完成外部
人员的独立回传。当前可诚实判断为：

> 已形成跨三个实测来源族、144 个物理样品和 970 个案例的 focused
> benchmark-validity study；其定义、数据拆分、候选库、指标、敏感性、重复运行
> 和发布审计达到一区论文所需的严谨度。其中 67 个样品/反应未被本项目使用过，
> 77 个来自已消费的 Precursor Genome 旧队列。剩余主要门槛是外部独立复现和
> 最终写作，不是继续增加相似模型。
