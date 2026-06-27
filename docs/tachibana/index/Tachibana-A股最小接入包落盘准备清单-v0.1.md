# Tachibana A 股最小接入包落盘准备清单 v0.1

## 版本定位

- 本文件是把真实 A 股候选数据放入 `Z:\asteria-trading-labs-data\ashare\` 前后的操作清单。
- 它承接 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md)、[Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 与 [MALF-立花前置认知过滤器攻坚总控矩阵 v0.1](./MALF-立花前置认知过滤器攻坚总控矩阵-v0.1.md)。
- 它不是数据下载方案，不生成真实 A 股样本，不定义 T+1、涨跌停、停牌、整手或执行规则。
- 它只回答：真实数据落盘时，如何避免目录、文件、字段、窗口和升级边界出错。

## 目标

当前阻断点不是规则设计，而是正式数据目录缺少最小接入包。本清单把“补齐真实 A 股候选数据”拆成可检查的落盘动作，确保数据一旦到位，就能按固定流程从 `fail` 推进到 `warn/pass`。

## 目标目录

```text
Z:\asteria-trading-labs-data\
  ashare\
    candidate-universe-v0.1.csv
    sw-industry-membership-v0.1.csv
    daily-window-v0.1\
      <ts_code>.csv
    malf-snapshots-v0.1\
      <ts_code>-<window>.json
```

不得把真实 A 股接入包放入 `Z:\asteria-trading-lab` 仓库目录；仓库只保存定义、审计、模板和研究文档。

## 落盘前检查

| 检查项 | 要求 | 失败处理 |
|---|---|---|
| 数据来源 | 每个文件必须能写出 `source_ref`。 | 不落盘为正式接入包。 |
| 样本范围 | 先用小批候选股票，不需要全市场。 | 范围不清则保持草稿。 |
| 观察窗口 | 每只股票必须有明确 `sample_window_start / sample_window_end`。 | 不进入日线窗口目录。 |
| 复权口径 | 日线文件必须写 `adj_ref`。 | 不进入 MALF。 |
| 行业标签 | 样本窗口内必须有有效申万标签。 | 只能停在 `universe_candidate`。 |
| 禁止字段 | 原始数据不得包含买卖信号、目标仓位、T+1 动作或涨跌停策略字段。 | 先清洗，再落盘。 |

## 文件级落盘清单

### 1. `candidate-universe-v0.1.csv`

| 项目 | 检查 |
|---|---|
| 文件路径 | `Z:\asteria-trading-labs-data\ashare\candidate-universe-v0.1.csv` |
| 表头 | `ts_code,symbol_name,board_type,list_date,is_st,is_new_stock_window,data_quality_status,source_ref` |
| 主键 | `ts_code` 非空、唯一。 |
| 最低状态 | 可先有 `data_quality_status=incomplete`，但不能升级为 `structure_candidate`。 |

### 2. `sw-industry-membership-v0.1.csv`

| 项目 | 检查 |
|---|---|
| 文件路径 | `Z:\asteria-trading-labs-data\ashare\sw-industry-membership-v0.1.csv` |
| 表头 | `ts_code,sw_l1_name,sw_l2_name,valid_from,valid_to,source_ref` |
| 主键 | `ts_code + valid_from`。 |
| 窗口覆盖 | 样本观察窗口内必须能找到有效行业标签。 |

### 3. `daily-window-v0.1\<ts_code>.csv`

| 项目 | 检查 |
|---|---|
| 文件路径 | `Z:\asteria-trading-labs-data\ashare\daily-window-v0.1\<ts_code>.csv` |
| 表头 | `ts_code,trade_date,open,high,low,close,volume,amount,adj_ref,suspension_flag,corporate_action_flag,missing_bar_flag` |
| 文件一致 | 文件名 `<ts_code>` 必须与文件内 `ts_code` 一致。 |
| 日期 | `trade_date` 升序且不重复。 |
| OHLC | 正常交易行必须满足 OHLC 合法性。 |

### 4. `malf-snapshots-v0.1\<ts_code>-<window>.json`

| 项目 | 检查 |
|---|---|
| 文件路径 | `Z:\asteria-trading-labs-data\ashare\malf-snapshots-v0.1\<ts_code>-<window>.json` |
| 快照质量 | 只有 `snapshot_quality_status=ready` 才能支持 `tachibana_candidate`。 |
| 结构背景 | `malf_background=unknown` 不得被人工升级。 |
| 证据引用 | `source_daily_file` 与 `evidence_ref` 必须可追溯。 |

## 落盘后第一轮复核

真实数据放入目录后，先只做以下检查：

机器复核入口：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data
```

该验收器是只读工具，只报告接入包是否满足最低字段契约、路径要求、主键唯一性、基础值域和可机器判定的跨文件一致性要求；它不生成交易信号、不生成 MALF 快照、不写入正式数据目录。

| 顺序 | 动作 | 输出 |
|---|---|---|
| 1 | 检查四类路径是否存在。 | `intake_package_status=missing/partial/ready`。 |
| 2 | 检查表头、必填字段、主键、枚举、日期、布尔和非负数值。 | `failed_contract_items`。 |
| 3 | 检查 `ts_code` 跨文件一致性。 | 孤儿记录清单。 |
| 4 | 检查日线窗口 OHLC 与日期排序。 | `daily_window_quality`。 |
| 5 | 检查 MALF 快照窗口和质量。 | `snapshot_quality_status`。 |
| 6 | 生成按 `ts_code` 汇总的阶段摘要。 | `candidate_stage_summary`。 |
| 7 | 更新验收报告。 | `contract_check_result=fail/warn/pass`。 |

第一轮复核只决定数据能否进入 MALF / 结构资格审计，不决定任何股票适合立花法。

## 严禁动作

| 禁止动作 | 原因 |
|---|---|
| 用行业、板块或流动性直接生成 `tachibana_candidate`。 | 结构资格必须经 MALF 与前置过滤器。 |
| 在接入包内写 `buy_signal / sell_signal / trade_accept`。 | 接入包不是 Signal。 |
| 在接入包内写 `target_position / center_size`。 | 仓位属于 PM。 |
| 在接入包内写 `ashare_t1_action / limit_up_strategy / limit_down_strategy`。 | 制度执行约束后置。 |
| 用缺失文件的空模板冒充真实数据。 | 会污染验收报告。 |

## 与当前总控矩阵的关系

本清单只解决总控矩阵中的第一个缺口：

| 总控缺口 | 本清单能解决什么 | 本清单不能解决什么 |
|---|---|---|
| 正式 A 股接入包缺失。 | 规定真实数据如何落盘和复核。 | 不自动生成真实数据。 |
| A 股 MALF 快照缺失。 | 规定快照文件如何命名和验收。 | 不运行 MALF。 |
| `not_meaningful` 缺真实反例。 | 为未来真实反例提供数据入口。 | 不凭空制造反例。 |
| A 股制度约束仍是候选草案。 | 防止制度字段混入接入包。 | 不启动制度改造。 |

## 当前裁决

- 当前正式数据目录仍未提供 A 股最小接入包。
- 本清单可以作为下一次真实数据落盘前的准备标准。
- 只有真实文件落盘并通过复核流程后，才允许更新验收报告、生成 MALF 快照、填写结构资格判定记录。
- 在此之前，A 股制度规则改造继续后置。
