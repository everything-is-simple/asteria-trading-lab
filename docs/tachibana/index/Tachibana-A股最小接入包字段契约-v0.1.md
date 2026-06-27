# Tachibana A 股最小接入包字段契约 v0.1

## 版本定位

- 本文件承接 [Tachibana A 股候选股票数据接入审计 v0.1](./Tachibana-A股候选股票数据接入审计-v0.1.md) 与 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。
- 它定义 A 股候选股票进入 MALF / Tachibana 前置过滤器前，最小接入包必须交付哪些字段、如何复核、哪些字段不得提前混入。
- 本文件不是数据下载方案，不生成真实样本，不定义 T+1、涨跌停、停牌、整手、融资融券或执行规则。
- 它只回答：一批 A 股候选数据怎样才算具备被 MALF 结构审计接收的最低条件。
- 当前接入包验收结果见 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md)。
- 数据到位后的复核顺序见 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md)。
- 真实数据落盘前后的操作清单见 [Tachibana A 股最小接入包落盘准备清单 v0.1](./Tachibana-A股最小接入包落盘准备清单-v0.1.md)。

## 总体目录契约

最小接入包放在正式数据目录下，建议保持如下结构：

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

接入包整体状态使用：

| 字段 | 允许值 | 含义 |
|---|---|---|
| `intake_package_status` | `missing / partial / ready / invalid` | 最小接入包是否存在、是否完整、是否可验收。 |
| `contract_check_result` | `pass / warn / fail` | 字段与跨文件复核是否通过。 |

`ready` 只表示数据包可进入结构审计，不表示任何股票适合立花法。

## 1. candidate-universe-v0.1.csv

### 字段

主键：`ts_code`。

| 字段 | 类型 | 必填 | 允许值或格式 | 含义 |
|---|---|---:|---|---|
| `ts_code` | string | 是 | 非空 | 股票代码。 |
| `symbol_name` | string | 是 | 非空 | 股票简称。 |
| `board_type` | enum | 是 | `main / gem / star / bse / unknown` | 所属板块。 |
| `list_date` | date | 是 | `YYYY-MM-DD` | 上市日期。 |
| `is_st` | boolean | 是 | `true / false` | 是否 ST 或 *ST。 |
| `is_new_stock_window` | boolean | 是 | `true / false` | 是否处于新股特殊观察窗口。 |
| `data_quality_status` | enum | 是 | `ready / incomplete / source_missing / disputed` | 元数据质量状态。 |
| `source_ref` | string | 是 | 非空 | 数据来源引用。 |

### 表头样例

```csv
ts_code,symbol_name,board_type,list_date,is_st,is_new_stock_window,data_quality_status,source_ref
```

### 校验

| 校验项 | 要求 |
|---|---|
| 主键唯一 | `ts_code` 不得为空，不得重复。 |
| ready 条件 | `data_quality_status=ready` 时，`board_type/list_date/is_st/is_new_stock_window/source_ref` 均不得为空。 |
| 阶段边界 | 元数据 `ready` 只能支持 `universe_candidate`，不能直接升级为 `structure_candidate` 或 `tachibana_candidate`。 |

## 2. sw-industry-membership-v0.1.csv

### 字段

主键：`ts_code + valid_from`。同一 `ts_code` 在同一观察窗口内不得出现相互冲突的有效行业标签。

| 字段 | 类型 | 必填 | 允许值或格式 | 含义 |
|---|---|---:|---|---|
| `ts_code` | string | 是 | 非空 | 股票代码。 |
| `sw_l1_name` | string | 是 | 非空 | 申万一级行业。 |
| `sw_l2_name` | string/null | 是 | 可空但字段必须存在 | 申万二级行业。 |
| `valid_from` | date | 是 | `YYYY-MM-DD` | 行业标签生效日期。 |
| `valid_to` | date/null | 是 | `YYYY-MM-DD` 或空 | 行业标签失效日期，空表示开放结束。 |
| `source_ref` | string | 是 | 非空 | 分类来源引用。 |

### 表头样例

```csv
ts_code,sw_l1_name,sw_l2_name,valid_from,valid_to,source_ref
```

### 校验

| 校验项 | 要求 |
|---|---|
| 时间有效 | `valid_to` 非空时必须大于等于 `valid_from`。 |
| 窗口覆盖 | 样本观察窗口内必须能找到有效行业标签，才可从 `universe_candidate` 升级。 |
| 边界约束 | 行业标签只作为样本分层事实，不能生成买卖判断、热度打分或 Tachibana 适用结论。 |

## 3. daily-window-v0.1/<ts_code>.csv

### 字段

主键：`ts_code + trade_date`。即使文件名包含 `ts_code`，文件内也必须保留 `ts_code` 字段。

| 字段 | 类型 | 必填 | 允许值或格式 | 含义 |
|---|---|---:|---|---|
| `ts_code` | string | 是 | 与文件名一致 | 股票代码。 |
| `trade_date` | date | 是 | `YYYY-MM-DD` | 交易日期。 |
| `open` | number/null | 是 | 非负 | 开盘价。 |
| `high` | number/null | 是 | 非负 | 最高价。 |
| `low` | number/null | 是 | 非负 | 最低价。 |
| `close` | number/null | 是 | 非负 | 收盘价。 |
| `volume` | number | 是 | 大于等于 0 | 成交量。 |
| `amount` | number | 是 | 大于等于 0 | 成交额。 |
| `adj_ref` | string | 是 | 非空 | 复权或原始价口径引用。 |
| `suspension_flag` | boolean | 是 | `true / false` | 是否停牌或无正常交易。 |
| `corporate_action_flag` | boolean | 是 | `true / false` | 是否存在除权、分红、送转等公司行为标记。 |
| `missing_bar_flag` | boolean | 否 | `true / false` | 是否存在缺失交易行或补齐行。 |

### 表头样例

```csv
ts_code,trade_date,open,high,low,close,volume,amount,adj_ref,suspension_flag,corporate_action_flag,missing_bar_flag
```

### 校验

| 校验项 | 要求 |
|---|---|
| 文件一致 | 文件名中的 `<ts_code>` 必须与文件内 `ts_code` 一致。 |
| 日期排序 | `trade_date` 应按升序排列，且同一日期不得重复。 |
| OHLC 合法 | 正常交易行中 `open/high/low/close` 不得为空，`high >= max(open, close)`，`low <= min(open, close)`。 |
| 成交合法 | `volume` 与 `amount` 必须大于等于 0。 |
| 质量标记 | `suspension_flag/corporate_action_flag/missing_bar_flag` 只标记数据质量和结构证据风险，不定义 T+1、涨跌停或停牌执行规则。 |

## 4. malf-snapshots-v0.1/<ts_code>-<window>.json

### 字段

JSON 文件记录某个 A 股样本窗口对应的 MALF 结构事实快照。

| 字段 | 类型 | 必填 | 允许值或格式 | 含义 |
|---|---|---:|---|---|
| `malf_snapshot_ref` | string | 是 | 非空 | MALF 快照唯一引用。 |
| `ts_code` | string | 是 | 与文件名一致 | 股票代码。 |
| `window_start` | date | 是 | `YYYY-MM-DD` | 快照窗口起点。 |
| `window_end` | date | 是 | `YYYY-MM-DD` | 快照窗口终点。 |
| `source_daily_file` | string | 是 | 非空 | 对应日线窗口文件。 |
| `generated_at` | datetime | 是 | ISO 8601 | 快照生成时间。 |
| `malf_version` | string | 是 | 非空 | MALF 定义或实现版本。 |
| `malf_background` | enum/list | 是 | `alive_wave / pullback / range / break_birth / stagnation / transition / unknown` | 结构背景。 |
| `wave_range_break_fields` | object | 是 | JSON object | 波段、区间、突破等结构证据字段。 |
| `evidence_ref` | string/list | 是 | 非空 | 支撑证据引用。 |
| `snapshot_quality_status` | enum | 是 | `ready / incomplete / source_missing / disputed` | 快照质量状态。 |

### JSON 样例

```json
{
  "malf_snapshot_ref": "TBD",
  "ts_code": "TBD",
  "window_start": "YYYY-MM-DD",
  "window_end": "YYYY-MM-DD",
  "source_daily_file": "daily-window-v0.1/TBD.csv",
  "generated_at": "YYYY-MM-DDTHH:mm:ssZ",
  "malf_version": "MALF_Definitive_v2_0",
  "malf_background": "unknown",
  "wave_range_break_fields": {},
  "evidence_ref": ["TBD"],
  "snapshot_quality_status": "incomplete"
}
```

### 校验

| 校验项 | 要求 |
|---|---|
| 文件一致 | 文件名中的 `<ts_code>` 必须与 JSON 内 `ts_code` 一致。 |
| 窗口一致 | `window_start/window_end` 必须落在对应日线窗口范围内。 |
| ready 条件 | 只有 `snapshot_quality_status=ready` 的快照，才能支持 `tachibana_candidate` 判定。 |
| unknown 约束 | `malf_background=unknown` 不得被人工经验改写成 `suitable / conditional`。 |

## 跨文件升级闸门

| 目标阶段 | 必须具备 | 不足时状态 |
|---|---|---|
| `universe_candidate` | `candidate-universe-v0.1.csv` 中有唯一 `ts_code`，且元数据字段可复核。 | `unknown` 或 `blocked_by_missing_metadata`。 |
| `structure_candidate` | 元数据 `ready`，样本窗口内有有效申万标签，日线窗口可被 MALF 读取。 | 保持 `universe_candidate`。 |
| `tachibana_candidate` | 已有 `snapshot_quality_status=ready` 的 MALF 快照，且前置过滤器输出 `suitable / conditional`。 | 保持 `structure_candidate`。 |
| `Backtest Input` | `tachibana_candidate` 已有 `qualification_rule_id/boundary_warning/evidence_level`，Method / PM 可承接。 | 只保留研究记录。 |

## 禁止字段

最小接入包不得提前写入以下字段：

| 禁止字段 | 原因 |
|---|---|
| `buy_signal` | 接入包不是 Signal。 |
| `trade_accept` | 数据可用不等于交易裁决。 |
| `target_position` | 仓位属于 PM，不属于 Data / MALF 接入。 |
| `ashare_t1_action` | T+1 是执行约束，后置处理。 |
| `limit_up_strategy / limit_down_strategy` | 涨跌停策略不属于结构资格接入。 |
| `industry_hot_score` | 行业热度不能替代 MALF 结构事实。 |
| `liquidity_rank_as_applicability` | 流动性排序不能替代 Tachibana 适用性判定。 |

## 验收输出

最小接入包导入后，应先生成一份数据质量报告，再填 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。

| 输出 | 用途 |
|---|---|
| `intake_package_status` | 判断接入包是否完整。 |
| `contract_check_result` | 判断字段契约是否通过。 |
| `failed_contract_items` | 列出缺失字段、重复主键、窗口不一致、质量状态不合格等问题。 |
| `eligible_for_malf_run` | 只表示可运行 MALF，不表示适合 Tachibana。 |

## 当前结论

- 当前正式数据目录仍未提供上述接入包，验收报告见 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md)；因此本文件只定义验收契约，不生成真实 A 股样本。
- 下一步应先按 [Tachibana A 股最小接入包落盘准备清单 v0.1](./Tachibana-A股最小接入包落盘准备清单-v0.1.md) 落盘一小批可复核 A 股候选数据，再按 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 生成 `contract_check_result`，最后运行 MALF 快照。
- 只有通过接入包验收并生成 MALF 快照后，才允许填充 A 股结构资格样本表；仍不进入 T+1、涨跌停、停牌等制度规则改造。
