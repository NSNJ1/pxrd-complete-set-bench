# Windows independent execution prompt

你是一名未参与本项目实现的外部执行人。请独立复现 Precursor Genome
open-library benchmark。不要读取、猜测或引用发送方已经得到的 AUROC、排序变化率
或显著性命中结论。你的任务是执行、核验和如实回传，不是证明预期结论。

该来源不是项目未曾接触过的新数据：102 条查询中 77 条与旧闭库队列重合，
25 条为新查询。你的报告必须把它称为“已有来源上的 open-library 新干预”，
不得称为 new external holdout。

## 硬约束

- 操作系统：Windows 10 或 11 x64；
- 使用 PowerShell，不依赖 WSL；
- Python 3.12；
- 不得修改查询谱、候选库、参考谱、案例划分、方法参数或评分定义；
- 正式运行前不要打开 `scores` 或发送方结果；
- 正式运行只能执行一次；如果失败，保留失败日志后再修复环境并重跑；
- 不要把失败重跑伪装成第一次运行；
- 报告实际耗时、退出码、文件哈希和所有偏离。

## 包内输入

- `dataset_v7/`：冻结数据；
- `cases_v8/`：418 个冻结案例；
- `selection_v3/`：来源选择和参考反应隔离记录；
- `run_profile_baseline_panel.py`：shifted Pearson 正对照；
- `external_runners/run_crystalshift_panel.py` 与
  `external_runners/run_crystalshift_open.jl`：CrystalShift 适配器；
- `run_xdecomposer_profile_panel.py`：官方 XDecomposer V_0.0.1 适配器；
- `EXPECTED_OUTPUT_HASHES.json`：预期输出哈希；
- `verify_outputs.py`：输出覆盖和哈希检查。

## 步骤 1：环境记录

记录：

```powershell
Get-ComputerInfo | Select-Object WindowsProductName,WindowsVersion,OsArchitecture
python --version
julia --version
```

Python 必须为 3.12.x。CrystalShift 使用 Julia 1.10.13，commit
`c4884ca1dbbd78135cd50f5e17141cdc0b6f43c8`。

## 步骤 2：确认输入未变

记录以下文件 SHA-256：

```text
dataset_v7/public/candidates.csv
dataset_v7/public/candidate_sticks.csv
dataset_v7/public/queries.csv
dataset_v7/evaluator/truth.csv
cases_v8/cases.csv
cases_v8/case_phase_truth.csv
cases_v8/manifest.json
```

可使用 PowerShell：

```powershell
Get-FileHash <file> -Algorithm SHA256
```

如果 `cases_v8/manifest.json` 的 `source_id` 不是
`precursor_genome`，停止。另请按 `PRIOR_PROJECT_OVERLAP_20261127.json`
核对 `PRIOR_PROJECT_QUERY_IDS.txt` 与 `dataset_v7/public/queries.csv`：
应为 416 个旧 ID、102 个新面板 ID、77 个交集和 25 个新 ID。

## 步骤 3：profile 正对照

```powershell
python run_profile_baseline_panel.py `
  --dataset dataset_v7 `
  --cases cases_v8 `
  --outdir outputs_profile
```

要求：

- 102 queries；
- 418 cases；
- 8,044 candidate rows；
- 进程退出码 0。

## 步骤 4：CrystalShift

准备 Julia 1.10.13、固定 commit 和完整 Julia depot。设置：

```powershell
$env:JULIA_DEPOT_PATH = "<Julia depot>"
```

执行：

```powershell
python external_runners/run_crystalshift_panel.py `
  --dataset dataset_v7 `
  --cases cases_v8 `
  --julia <julia.exe> `
  --julia-project <CrystalShift.jl> `
  --julia-depot $env:JULIA_DEPOT_PATH `
  --runner external_runners/run_crystalshift_open.jl `
  --outdir outputs_crystalshift `
  --workers 3 `
  --max-depth 3
```

该命令必须执行 full + 20 leave-one-family-out libraries。任何一个库失败，
都保留该库日志并报告失败。

## 步骤 5：XDecomposer

如本机已有官方 V_0.0.1 source 和 checkpoint，设置：

```powershell
$env:XDECOMPOSER_RELEASE_ROOT = "<V_0.0.1 source root>"
$env:XDECOMPOSER_CHECKPOINT_ROOT = "<checkpoint root>"
```

执行：

```powershell
python run_xdecomposer_profile_panel.py `
  --dataset dataset_v7 `
  --cases cases_v8 `
  --outdir outputs_xdecomposer
```

不要重新训练模型，不要改 checkpoint。

## 步骤 6：输出核验

```powershell
python verify_outputs.py `
  --profile outputs_profile `
  --crystalshift outputs_crystalshift `
  --xdecomposer outputs_xdecomposer
```

该脚本会检查：

- 行数和覆盖；
- 候选/案例表 SHA-256；
- 21 个 CrystalShift 库的逐库哈希；
- 重复结构是否完整。

哈希不一致时，不要调整数据和参数来“凑哈希”。保存原始输出并报告差异。

## 步骤 7：评分

只有在三个方法的正式输出完成后，才能运行：

```powershell
python score_precursor_genome.py `
  --cases cases_v8 `
  --profile-run outputs_profile `
  --crystalshift-run outputs_crystalshift `
  --xdecomposer-run outputs_xdecomposer `
  --outdir outputs_scores `
  --bootstrap-repeats 10000
```

不要查看发送方的 AUROC 后再选择某个子集。两个评分脚本采用冻结的全量口径。

## 回传

回传 ZIP 应包含：

- 环境版本和完整命令；
- 每个进程的退出码、开始/结束时间和耗时；
- candidate、case、per-library CSV；
- score JSON；
- 所有 SHA-256；
- 失败日志与偏离记录；
- `verify_outputs.py` 输出。

在报告中写：

> 我是 `<姓名>`，未参与该 benchmark 的实现。我按照冻结包独立执行上述流程。

不得写：“Codex 帮我独立复现”。你本人是执行人，工具只是软件环境的一部分。
