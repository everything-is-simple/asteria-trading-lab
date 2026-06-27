# Tachibana A 股最小接入包验收报告 v0.1

## 版本定位

- 本文件承接 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md)、[Tachibana A 股候选股票数据接入审计 v0.1](./Tachibana-A股候选股票数据接入审计-v0.1.md) 与 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。
- 它不是新的字段定义，不下载数据，不生成 A 股候选结论。
- 它只回答：当前正式数据目录下的 A 股最小接入包，是否已经足够进入 MALF 结构审计与 Tachibana 前置过滤器。
- 本文件不定义 T+1、涨跌停、停牌、整手、融资融券或任何执行规则。
- 真实数据落盘前后的操作清单见 [Tachibana A 股最小接入包落盘准备清单 v0.1](./Tachibana-A股最小接入包落盘准备清单-v0.1.md)。
- 数据到位后的复核顺序见 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md)。
- 当前 pending 队列的阻断态判定底稿见 [Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1](./Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md)。

## 本轮验收对象

| 项目 | 路径或文件 | 当前状态 |
|---|---|---|
| 正式数据根目录 | `Z:\asteria-trading-labs-data` | 目录存在。 |
| A 股接入包目录 | `Z:\asteria-trading-labs-data\ashare` | 未发现可验收文件。 |
| 候选股票元数据 | `ashare\candidate-universe-v0.1.csv` | 缺失。 |
| 申万行业标签 | `ashare\sw-industry-membership-v0.1.csv` | 缺失。 |
| 日线窗口目录 | `ashare\daily-window-v0.1\` | 缺失。 |
| MALF 快照目录 | `ashare\malf-snapshots-v0.1\` | 缺失。 |

本轮验收基于当前文件系统状态：`Z:\asteria-trading-labs-data` 下文件数为 `0`。

## 总体验收结果

| 字段 | 当前值 | 说明 |
|---|---|---|
| `intake_package_status` | `missing` | 最小接入包必需文件均不存在。 |
| `contract_check_result` | `fail` | 无法执行字段完整性、主键唯一性、窗口一致性或跨文件升级校验。 |
| `eligible_for_malf_run` | `false` | 缺少日线窗口，无法生成 A 股 MALF 快照。 |
| `eligible_for_structure_candidate` | `false` | 缺少元数据、申万标签和日线窗口。 |
| `eligible_for_tachibana_candidate` | `false` | 缺少 `snapshot_quality_status=ready` 的 MALF 快照。 |

结论：当前接入包不能进入 MALF 结构审计，也不能填充真实 A 股结构资格样本。

## 文件级验收

| 文件 | 契约要求 | 当前证据 | 结果 | 阻断阶段 |
|---|---|---|---|---|
| `candidate-universe-v0.1.csv` | 必须提供唯一 `ts_code`、板块、上市日期、ST、新股窗口、来源引用。 | 文件缺失。 | `fail` | `universe_candidate` |
| `sw-industry-membership-v0.1.csv` | 必须提供样本窗口内有效申万一级/二级行业标签。 | 文件缺失。 | `fail` | `structure_candidate` |
| `daily-window-v0.1/<ts_code>.csv` | 必须提供可排序、可校验、可供 MALF 读取的 OHLCV 日线窗口。 | 目录与文件缺失。 | `fail` | `structure_candidate` |
| `malf-snapshots-v0.1/<ts_code>-<window>.json` | 必须提供 `snapshot_quality_status=ready` 的 MALF 结构事实快照。 | 目录与文件缺失。 | `fail` | `tachibana_candidate` |

## 未执行校验项

以下校验不是通过，而是因为缺少文件无法执行：

| 校验项 | 无法执行原因 |
|---|---|
| `ts_code` 主键唯一性 | `candidate-universe-v0.1.csv` 缺失。 |
| `board_type/list_date/is_st/is_new_stock_window` 完整性 | `candidate-universe-v0.1.csv` 缺失。 |
| 申万标签窗口覆盖 | `sw-industry-membership-v0.1.csv` 缺失。 |
| 日线窗口升序与 OHLC 合法性 | `daily-window-v0.1` 缺失。 |
| `adj_ref` 口径追溯 | 日线窗口缺失。 |
| `suspension_flag/corporate_action_flag/missing_bar_flag` 数据质量标记 | 日线窗口缺失。 |
| MALF 快照窗口一致性 | `malf-snapshots-v0.1` 缺失。 |
| `malf_background` 与 `wave_range_break_fields` 结构证据 | MALF 快照缺失。 |

## 对候选样本表的影响

| 目标表阶段 | 当前裁决 | 原因 |
|---|---|---|
| `universe_candidate` | 暂不能生成真实样本。 | 缺少候选股票元数据。 |
| `structure_candidate` | 暂不能生成真实样本。 | 缺少申万标签与日线窗口。 |
| `tachibana_candidate` | 暂不能生成真实样本。 | 缺少 MALF 快照与前置过滤器输出。 |
| `Backtest Input` | 不可进入。 | 没有 `tachibana_candidate`，不能绕过结构资格闸门。 |

因此，[Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md) 中的 `ASHARE-PENDING-001/002/003` 仍应保持待填状态，不得用人工判断、行业热度、流动性或制度规则补位。

三条 pending 记录的阻断态底稿见 [Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1](./Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md)。

## 禁止误读

| 禁止误读 | 正确解释 |
|---|---|
| `contract_check_result=fail` 说明立花法不适合 A 股。 | 错。它只说明当前缺数据，无法验收。 |
| 可以先用 A 股规则参考文档填候选样本。 | 错。规则不是个股结构事实。 |
| 可以先按行业或流动性选几只股票作为 `tachibana_candidate`。 | 错。没有 MALF 快照，不能生成适用性结论。 |
| 可以先进入 T+1、涨跌停、停牌规则设计。 | 错。当前主线仍是结构资格判定。 |

## 下一轮最小动作

下一轮不需要全市场数据，只需要一小批可复核样本。最小动作顺序如下：

1. 先按 [Tachibana A 股最小接入包落盘准备清单 v0.1](./Tachibana-A股最小接入包落盘准备清单-v0.1.md) 确认来源、窗口、路径和禁止字段。
2. 在 `Z:\asteria-trading-labs-data\ashare\` 放入 `candidate-universe-v0.1.csv`，先让 `universe_candidate` 可被识别。
3. 放入 `sw-industry-membership-v0.1.csv`，确保候选股票在样本窗口内有有效申万行业标签。
4. 放入 `daily-window-v0.1\<ts_code>.csv`，确保日线窗口可供 MALF 读取。
5. 生成 `malf-snapshots-v0.1\<ts_code>-<window>.json`，且 `snapshot_quality_status=ready`。
6. 按 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 重新复核，并更新本验收报告，把 `contract_check_result` 从 `fail` 推进到 `pass` 或 `warn`。
7. 通过验收后，再填充 A 股结构资格样本表；仍不进入制度规则改造。

## 当前结论

- A 股最小接入包当前状态为 `missing`，契约验收结果为 `fail`。
- 这一步没有否定 MALF、Tachibana Method 或 PM，只是锁住了结构资格闸门：没有可复核数据，就不能生成结构适用性结论。
- 下一步仍应补齐最小接入包并先验收字段，再运行 MALF 快照，最后才填 A 股结构资格样本。
