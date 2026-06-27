# TachibanaBacktestInput 1976 段级样本试填审计 v0.1

## 版本定位

- 本文件承接 [Tachibana Backtest Input 适配层草案 v0.1](./Tachibana-Backtest-Input-适配层草案-v0.1.md)。
- 它用 `1976-03/04/05/07/11/12` 已拆分交易段，试填 `TachibanaBacktestInputSnapshot` 字段。
- 本文件不新增交易规则，不修改 MALF 主定义，不写 A 股制度适配。
- 它只回答：当前字段契约能否稳定承接“结构资格 -> Method -> PM -> Backtest Input”。

## 试填口径

| 口径 | 裁决 |
|---|---|
| `snapshot_granularity` | 本轮使用 `segment_summary`，即每个交易段先生成一条段级快照。 |
| `bar_dt` | 段级快照使用该段第一笔动作日期作为锚点。后续逐笔回放再拆成 `event_row`。 |
| `gross_long / gross_short / net_position` | 段级快照默认记录该段结束后的库存状态。 |
| `qualification_rule_id` | 必须有一个主规则。若同时存在清零、减仓、重建等状态，使用 `secondary_rule_ids` 保存辅规则。 |
| `execution_event_type` | 段级快照记录该段主执行类型；复杂段允许写 `rebalance`，具体逐笔动作留给 event 级回放。 |

## 试填判定

| fit_status | 含义 |
|---|---|
| `fit_pass` | 当前字段可以承接，不需要改契约。 |
| `fit_warn` | 可以承接，但需要 `secondary_rule_ids`、边界警告或后续 event 级拆分。 |
| `fit_gap` | 当前矩阵或字段契约缺少必要表达，需要修订后再进入执行型回测输入。 |

## 总表

| sample_id | 主规则 | 辅规则 | 试填状态 | 关键原因 |
|---|---|---|---|---|
| `1976-03-A` | `Q-PRESSURE-ADJUST` | `Q-REDUCE-WINDOW` | `fit_gap` | `—10 -> —5 -> —10 -> —12` 是旧段压力调整，原矩阵没有专门主规则。 |
| `1976-03-B` | `Q-CLEAR-RESET` | `Q-REDUCE-WINDOW` | `fit_warn` | 清零可填，但段内包含分批回补，需辅规则保真。 |
| `1976-03-C` | `Q-SEED-AFTER-CLEAR` | none | `fit_pass` | 清零后新库存种子，字段契约可直接承接。 |
| `1976-04-A` | `Q-LOCK-CANDIDATE` | none | `fit_pass` | 双侧库存扩张，锁单候选可由 PM 承接。 |
| `1976-04-B` | `Q-LOCK-WAIT` | `Q-NO-TRADE` | `fit_warn` | 无交易不是空仓等待，必须保留双侧库存压力。 |
| `1976-04-C` | `Q-LOCK-CANDIDATE` | `Q-REDUCE-WINDOW` | `fit_warn` | 双侧库存收束，不能只用净仓位表达。 |
| `1976-05-A` | `Q-LOCK-CANDIDATE` | none | `fit_pass` | 跨月双侧库存延续，可继续标锁单候选。 |
| `1976-05-B` | `Q-UNLOCK` | none | `fit_pass` | 解除一侧库存，PM 状态机可承接。 |
| `1976-05-C` | `Q-CLEAR-RESET` | none | `fit_pass` | 单侧库存清零，旧段闭合。 |
| `1976-07-A` | `Q-CLEAR-RESET` | none | `fit_pass` | 旧段清零，触发 reset。 |
| `1976-07-B` | `Q-SEED-AFTER-CLEAR` | none | `fit_pass` | 清零后新段分批扩张。 |
| `1976-07-C` | `Q-REDUCE-WINDOW` | none | `fit_pass` | 月底部分减仓，不反推利润原因。 |
| `1976-11-A` | `Q-EXTREME-ADDON` | `Q-ALIVE-PM-MIXED` | `fit_warn` | 同向推进存在，但 `—200` 尺度必须标警戒。 |
| `1976-11-B` | `Q-CLEAR-RESET` | none | `fit_pass` | 极端仓位一次清零，清仓原因不进 MALF。 |
| `1976-11-C` | `Q-SEED-AFTER-CLEAR` | `Q-CLEAR-RESET` | `fit_warn` | 小段内同时出现 `—5 -> 0 -> —5`，event 级回放要拆。 |
| `1976-11-D` | `Q-SEED-AFTER-CLEAR` | `Q-ALIVE-PM-MIXED` | `fit_warn` | 反手后新仓位骨架形成，需 PM 重置中心单候选。 |
| `1976-12-A` | `Q-ALIVE-PM-MIXED` | none | `fit_pass` | 承接 11 月中心单候选继续小额推进。 |
| `1976-12-B` | `Q-EXTREME-ADDON` | `Q-ALIVE-PM-MIXED` | `fit_warn` | 加码加速，必须保留 `scale_alert`。 |
| `1976-12-C` | `Q-NO-TRADE` | none | `fit_pass` | 大仓位等待，不能反推 range。 |
| `1976-12-D` | `Q-REDUCE-WINDOW` | `Q-CLEAR-RESET` | `fit_warn` | 三段式减仓最终清零，需要主辅规则。 |

## 代表性试填

### 1976-03-A：压力调整缺口

```yaml
adapter_version: tachibana_backtest_input_v0.1
snapshot_granularity: segment_summary
mode: observed_replay
sample_id: 1976-03-A
segment_id: S007-pressure-adjust
symbol: pioneer_electronics
bar_dt: 1976-03-01
timeframe: daily
malf_snapshot_ref: null
malf_background:
  - stagnation
  - pressure_transition
qualification_rule_id: Q-PRESSURE-ADJUST
secondary_rule_ids:
  - Q-REDUCE-WINDOW
tachibana_applicability: conditional
boundary_warning:
  - do_not_merge_pressure_adjustment_into_clean_wave
evidence_level:
  - E2_monthly_fact
  - E4_research_mapping
method_action: inventory_rebalance
method_candidates:
  - trend_confirmation_add
  - distribution_reduce
method_status: observed
pm_required: true
pm_action: rebalance
gross_long: 0
gross_short: 12
net_position: -12
center_side: short
lock_status: none
scale_alert: none
reset_after_clear: false
execution_intent: replay_observed_action
execution_event_type: rebalance
backtest_notes:
  - 原横向矩阵缺少 pressure adjust 主规则，应先补矩阵再进入系统化回测。
```

### 1976-04-C：双侧库存收束

```yaml
adapter_version: tachibana_backtest_input_v0.1
snapshot_granularity: segment_summary
mode: observed_replay
sample_id: 1976-04-C
segment_id: S008-dual-inventory-rebalance
symbol: pioneer_electronics
bar_dt: 1976-04-23
timeframe: daily
malf_snapshot_ref: null
malf_background:
  - transition
  - inventory_rebalance
qualification_rule_id: Q-LOCK-CANDIDATE
secondary_rule_ids:
  - Q-REDUCE-WINDOW
tachibana_applicability: conditional
boundary_warning:
  - do_not_net_dual_inventory_into_single_direction
evidence_level:
  - E2_monthly_fact
  - E3_book_statement
  - E4_research_mapping
method_action: inventory_rebalance
method_candidates:
  - distribution_reduce
  - inventory_rebalance
method_status: observed
pm_required: true
pm_action: rebalance
gross_long: 4
gross_short: 5
net_position: -1
center_side: mixed
lock_status: candidate
scale_alert: none
reset_after_clear: false
execution_intent: replay_observed_action
execution_event_type: rebalance
backtest_notes:
  - 净仓位为 -1 只服务执行计算，不能代表结构方向。
```

### 1976-12-D：分批退出并清零

```yaml
adapter_version: tachibana_backtest_input_v0.1
snapshot_granularity: segment_summary
mode: observed_replay
sample_id: 1976-12-D
segment_id: S012-distribution-clear
symbol: pioneer_electronics
bar_dt: 1976-12-20
timeframe: daily
malf_snapshot_ref: null
malf_background:
  - stagnation
  - exit_window
qualification_rule_id: Q-REDUCE-WINDOW
secondary_rule_ids:
  - Q-CLEAR-RESET
tachibana_applicability: conditional
boundary_warning:
  - do_not_encode_profit_protection_in_malf
  - do_not_encode_clear_reason_in_malf
evidence_level:
  - E2_monthly_fact
  - E4_research_mapping
method_action: distribution_reduce
method_candidates:
  - distribution_reduce
  - clear
method_status: observed
pm_required: true
pm_action: clear
gross_long: 0
gross_short: 0
net_position: 0
center_side: none
lock_status: none
scale_alert: none
reset_after_clear: true
execution_intent: replay_observed_action
execution_event_type: close
backtest_notes:
  - 段级主规则是分批退出，辅规则记录最终清零。
```

## 审计发现

| 编号 | 发现 | 处理 |
|---|---|---|
| `F-1` | `1976-03-A` 暴露了压力调整类样本，不能被硬塞进 clean alive 或 clear reset。 | 横向矩阵应新增 `Q-PRESSURE-ADJUST`。 |
| `F-2` | 单个交易段可能同时具备主规则与辅规则，如 `1976-12-D = reduce + clear`。 | Backtest Input 应新增 `secondary_rule_ids`。 |
| `F-3` | 段级快照与逐笔回放不是同一粒度。 | Backtest Input 应新增 `snapshot_granularity`。 |
| `F-4` | `net_position` 必须保留，但只能用于执行计算，不能代表结构方向。 | 双侧库存样本必须保留 `gross_long / gross_short / lock_status`。 |
| `F-5` | 大仓位等待与无仓等待不同。 | `Q-NO-TRADE` 的 PM 承接规则要强调持仓压力。 |

## 当前结论

- 20 个 1976 段级样本中，`fit_pass` 10 个，`fit_warn` 9 个，`fit_gap` 1 个。
- 唯一明确缺口是 `Q-PRESSURE-ADJUST`，说明横向矩阵需要补一种“压力调整/库存再平衡但未清零”的结构资格规则。
- `TachibanaBacktestInputSnapshot` 的主体字段成立，但需要补 `snapshot_granularity` 与 `secondary_rule_ids`，否则复杂段会被迫单标签化。
- 这一步继续证明：MALF 主定义不需要修订；需要修订的是 Tachibana 研究接缝的判读矩阵和适配字段。

## 下一步

- 把 `Q-PRESSURE-ADJUST` 写入横向判读矩阵。
- 把 `snapshot_granularity` 与 `secondary_rule_ids` 写入 Backtest Input 适配层。
- 同一口径抽查 `1975-06` 的结果见 [TachibanaBacktestInput 1975-06 段级样本试填审计 v0.1](./TachibanaBacktestInput-1975-06段级样本试填审计-v0.1.md)。
