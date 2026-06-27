# TachibanaBacktestInput 1975-06 段级样本试填审计 v0.1

## 版本定位

- 本文件承接 [Tachibana Backtest Input 适配层草案 v0.1](./Tachibana-Backtest-Input-适配层草案-v0.1.md) 与 [TachibanaBacktestInput 1976 段级样本试填审计 v0.1](./TachibanaBacktestInput-1976段级样本试填审计-v0.1.md)。
- 它用 [MALF-立花 1975-06 交易段结构资格审计 v0.1](./MALF-立花1975-06交易段结构资格审计-v0.1.md) 的四个段级样本，试填 `TachibanaBacktestInputSnapshot`。
- 本文件不修改 MALF 主定义，不输出交易信号，不写 A 股制度适配。
- 它专门检验：母单候选、双侧库存、月末库存延续是否能由 Backtest Input 承接，而不污染 MALF。

## 试填口径

| 口径 | 裁决 |
|---|---|
| `snapshot_granularity` | 继续使用 `segment_summary`。 |
| `bar_dt` | 使用该交易段第一笔动作日期作为锚点。 |
| `gross_long / gross_short / net_position` | 记录该段结束后的库存状态；双侧库存必须保留两侧总量。 |
| `center_side / center_size` | 只记录 PM 候选状态；不能由 MALF 或前置过滤器确认。 |
| `lock_status` | 双侧库存阶段统一先标 `candidate`，除非书页和 PM 标注明确支持正式锁单。 |

## 总表

| sample_id | 主规则 | 辅规则 | 试填状态 | 关键原因 |
|---|---|---|---|---|
| `1975-06-A` | `Q-ALIVE-PM-MIXED` | none | `fit_pass` | 有向推进存在，但母单/中心单只能由 PM 候选承接。 |
| `1975-06-B` | `Q-LOCK-CANDIDATE` | `Q-ALIVE-PM-MIXED` | `fit_warn` | 从单侧库存进入双侧库存，需要同时保留原母单候选背景。 |
| `1975-06-C` | `Q-LOCK-CANDIDATE` | `Q-REDUCE-WINDOW` | `fit_warn` | 双侧库存内发生兑现与反向测试，必须保留两侧库存，不得净额化。 |
| `1975-06-D` | `Q-LOCK-CANDIDATE` | `Q-SEED-AFTER-CLEAR` | `fit_warn` | 月末双侧库存延续可作为下一段种子，但不是清零后新种子。 |

## 代表性试填

### 1975-06-A：母单候选推进段

```yaml
adapter_version: tachibana_backtest_input_v0.1
snapshot_granularity: segment_summary
mode: observed_replay
sample_id: 1975-06-A
segment_id: S001-mother-candidate-build
symbol: pioneer_electronics
bar_dt: 1975-06-06
timeframe: daily
malf_snapshot_ref: null
malf_background:
  - alive_wave
  - mother_build_candidate
qualification_rule_id: Q-ALIVE-PM-MIXED
secondary_rule_ids: []
tachibana_applicability: conditional
boundary_warning:
  - do_not_call_mother_position_from_malf_only
evidence_level:
  - E2_monthly_fact
  - E3_book_statement
  - E4_research_mapping
method_action: trend_confirmation_add
method_candidates:
  - trend_confirmation_add
  - open_center_candidate
method_status: observed
pm_required: true
pm_action: add_on
gross_long: 40
gross_short: 0
net_position: 40
center_side: long
center_size: null
lock_status: none
scale_alert: none
reset_after_clear: false
execution_intent: replay_observed_action
execution_event_type: add
backtest_notes:
  - center_side=long 是 PM 候选方向，不是 MALF 输出。
  - center_size 暂不自动填，因为母单/中心单规模需要 PM 或书页证据确认。
```

### 1975-06-C：双侧库存兑现与反向测试段

```yaml
adapter_version: tachibana_backtest_input_v0.1
snapshot_granularity: segment_summary
mode: observed_replay
sample_id: 1975-06-C
segment_id: S001-dual-inventory-rebalance
symbol: pioneer_electronics
bar_dt: 1975-06-24
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
  - reverse_probe
  - inventory_rebalance
method_status: observed
pm_required: true
pm_action: rebalance
gross_long: 25
gross_short: 20
net_position: 5
center_side: mixed
center_size: null
lock_status: candidate
lock_candidate_size: 20
scale_alert: none
reset_after_clear: false
execution_intent: replay_observed_action
execution_event_type: rebalance
backtest_notes:
  - net_position=5 只用于执行计算；结构资格仍必须读取 gross_long/gross_short。
  - lock_candidate_size=20 只是双侧重叠规模，不确认锁单目的。
```

### 1975-06-D：月末双侧库存延续段

```yaml
adapter_version: tachibana_backtest_input_v0.1
snapshot_granularity: segment_summary
mode: observed_replay
sample_id: 1975-06-D
segment_id: S001-month-end-dual-inventory-seed
symbol: pioneer_electronics
bar_dt: 1975-06-30
timeframe: daily
malf_snapshot_ref: null
malf_background:
  - transition
  - next_segment_seed
qualification_rule_id: Q-LOCK-CANDIDATE
secondary_rule_ids:
  - Q-SEED-AFTER-CLEAR
tachibana_applicability: conditional
boundary_warning:
  - do_not_treat_month_end_inventory_as_malf_reversal
  - do_not_net_dual_inventory_into_single_direction
evidence_level:
  - E2_monthly_fact
  - E3_book_statement
  - E4_research_mapping
method_action: inventory_rebalance
method_candidates:
  - inventory_seed
  - trend_confirmation_add
method_status: observed
pm_required: true
pm_action: rebalance
gross_long: 27
gross_short: 20
net_position: 7
center_side: mixed
center_size: null
lock_status: candidate
lock_candidate_size: 20
scale_alert: none
reset_after_clear: false
execution_intent: replay_observed_action
execution_event_type: rebalance
backtest_notes:
  - 这里是月末库存延续，不是 clear 后的新种子；secondary_rule_ids 只提示下一段种子语义。
```

## 审计发现

| 编号 | 发现 | 处理 |
|---|---|---|
| `F-1` | 1975-06 四段都能进入现有 Backtest Input 字段，不需要新增字段。 | 保持 `snapshot_granularity / secondary_rule_ids` 的 v0.1 设计。 |
| `F-2` | `1975-06-A` 证明 `Q-ALIVE-PM-MIXED` 可以承接母单候选，但不能自动填 `center_size`。 | Backtest Input 应允许 `center_side` 有方向，`center_size=null`。 |
| `F-3` | `1975-06-B/C/D` 证明双侧库存必须保留 `gross_long / gross_short / lock_candidate_size`。 | 强化 `do_not_net_dual_inventory_into_single_direction`。 |
| `F-4` | `1975-06-D` 不是 clear 后的新种子，而是月末库存延续种子。 | `Q-SEED-AFTER-CLEAR` 只能作为辅规则提醒，不能作为主规则。 |

## 当前结论

- `1975-06` 试填结果为 `fit_pass` 1 个、`fit_warn` 3 个、`fit_gap` 0 个。
- 1976 试填后补入的 `secondary_rule_ids` 足以承接 `1975-06` 的复合段，不需要继续扩展 Backtest Input 字段。
- `Q-ALIVE-PM-MIXED` 和 `Q-LOCK-CANDIDATE` 可以承接母单候选与双侧库存，但必须保留 PM 候选性质。
- 本轮进一步确认：MALF 主定义不需要修订；立花仓位艺术由 Method / PM / Backtest Input 承接。

## 下一步

- 把本试填审计回链到 Backtest Input、样本表和阅读导航。
- A 股候选股票样本表已建立为 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)；下一轮按 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md) 导入并验收最小接入包，仍不进入 T+1、涨跌停、停牌规则改造。
