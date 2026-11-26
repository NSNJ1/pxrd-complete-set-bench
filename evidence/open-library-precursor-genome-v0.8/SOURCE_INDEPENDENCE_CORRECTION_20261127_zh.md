# Precursor Genome 来源独立性更正

日期：2026-11-27

## 发现

公开仓库中的旧闭库输入 `data/query_phase_scores.csv` 已经包含 416 个
Precursor Genome 查询。旧输入 SHA-256 为：

`70a7e11872f50a9cddbe83ca84614462edebf99a1089a8b512a525a049ba2c2b`

新的 open-library 面板包含 102 个查询：

- 77 个 query ID 与旧闭库队列完全相同；
- 25 个是项目此前未使用的新 query ID。

因此，旧措辞：

> previously unused external measured retrospective holdout

是错误的。它最多只能描述“未用于本次 open-library 干预”，不能描述为本项目从未
接触过的新来源。

## 数值影响

这项更正只影响来源独立性和论文叙事，不改变：

- 102 个查询或 418 个案例；
- 三个方法的任何 candidate/case 分数；
- AUROC；
- retained-true order 的 4/30；
- 10,000 次 bootstrap；
- 三项 sensitivity。

## 已更正对象

- `selection_v3/SELECTION_MANIFEST.json` 新增原始措辞和重叠计数；
- `dataset_v7/manifest.json` 更新 claim boundary；
- `score_precursor_genome.py` 和 `scores_v8/` 更新 claim boundary；
- `PREREGISTRATION_ADMISSION.md`；
- `ACTIVE_PROGRESS_20261127.md`；
- `README.md`；
- `PRECURSOR_GENOME_RESULTS_20261127_zh.md`；
- manuscript、reviewer-risk register、submission README 和科学审查。

## 机器可读证据

- `PRIOR_PROJECT_OVERLAP_20261127.json`；
- `PRIOR_PROJECT_QUERY_IDS.txt`；
- `RELEASE_AUDIT_20261127.json`；
- `scores_v8/summary.json`。

## 对一区判断的影响

来源证据从表面上的“3 个独立新来源族”下降为：

- 1 个项目前瞻来源（Algarve）；
- 1 个新外部实测 holdout（Dara）；
- 1 个已消费来源上的大规模新干预（Precursor Genome）。

总评估样品数仍是 144，但真正未被本项目使用过的是 67 个。内部质量分应从
三来源初判的 `90/100` 下调到 `87/100`。这比隐藏重叠后声称“三个全新来源”
更符合一区论文的诚实标准。
