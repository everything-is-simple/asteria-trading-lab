# 原始立花法 v0.1 回测统计报告

## 报告定位

本报告统计 `原始立花义正交易法 v0.1` 最小回测原型的运行结果。

当前统计是 PM 状态回放统计，不是资金曲线、盈亏曲线或可交易策略绩效报告。v0.1 的目标是验证 1975-1976 全部月度交易谱能否被统一解析为日级回放、仓位状态、交易段和人工复核队列。

时点纪律：交易判断来自上一有效交易日收盘价；实际下单发生在下一交易日开盘前，`trade_price` 解释为成交日开盘价。交易行同日 `close_price` 只用于盘后记录和盯市，不得作为该行下单依据。

## 数据覆盖

| 项 | 结果 |
|---|---:|
| 覆盖月份 | 24 |
| 起始月份 | 1975-01 |
| 结束月份 | 1976-12 |
| 日级回放行数 | 729 |
| 1975 行数 | 365 |
| 1976 行数 | 364 |
| 有 `trade_raw` 的交易事实行 | 159 |
| 有 `position_raw` 的持仓事实行 | 159 |

输入来源为 `data/pioneer-1975-1976/json/1975-01.json` 至 `data/pioneer-1975-1976/json/1976-12.json`，不包含 `pioneer-1975-1976-combined.json`。

## PM 动作统计

| `pm_action` | 次数 |
|---|---:|
| `wait_no_action` | 570 |
| `add_on` | 58 |
| `rebalance` | 37 |
| `reduce_add_on` | 17 |
| `inventory_seed` | 15 |
| `clear` | 15 |
| `lock_candidate` | 9 |
| `unlock` | 8 |

## Method 动作统计

| `method_action` | 次数 |
|---|---:|
| `wait_no_action` | 570 |
| `trend_confirmation_add` | 58 |
| `inventory_rebalance` | 54 |
| `distribution_reduce` | 17 |
| `trend_probe_entry` | 15 |
| `exit_on_rhythm_failure` | 15 |

## 退出模式统计

| `exit_mode` | 次数 |
|---|---:|
| `none` | 689 |
| `staged_distribution` | 17 |
| `one_shot_clear` | 15 |
| `unlock_then_clear` | 8 |

## 交易段统计

| 项 | 结果 |
|---|---:|
| 交易段数量 | 15 |
| 最大多头库存 | 200 |
| 最大空头库存 | 150 |
| 人工复核队列条目 | 241 |
| 加码尺度警戒日期 | 1976-11-08、1976-11-09、1976-11-10、1976-11-27、1976-12-13 |

### 交易段摘要

| 段 | 起始 | 结束 | 中心方向候选 | 中心规模候选 | 最大多头 | 最大空头 | 退出模式 |
|---|---|---|---|---:|---:|---:|---|
| S001 | 1975-01-04 | 1975-07-29 | short | 10 | 40 | 40 | `one_shot_clear` |
| S002 | 1975-09-05 | 1975-09-22 | long | 1 | 3 | 0 | `one_shot_clear` |
| S003 | 1975-09-29 | 1975-10-08 | long | 1 | 2 | 0 | `one_shot_clear` |
| S004 | 1975-10-17 | 1975-10-31 | short | 2 | 6 | 6 | `one_shot_clear` |
| S005 | 1975-11-06 | 1975-12-25 | long | 2 | 20 | 2 | `one_shot_clear` |
| S006 | 1976-01-10 | 1976-01-29 | long | 1 | 5 | 0 | `one_shot_clear` |
| S007 | 1976-02-09 | 1976-03-24 | long | 2 | 12 | 0 | `one_shot_clear` |
| S008 | 1976-03-29 | 1976-05-21 | long | 2 | 20 | 10 | `one_shot_clear` |
| S009 | 1976-06-15 | 1976-07-02 | short | 2 | 0 | 10 | `one_shot_clear` |
| S010 | 1976-07-13 | 1976-08-11 | short | 2 | 0 | 15 | `one_shot_clear` |
| S011 | 1976-08-16 | 1976-08-24 | long | 2 | 5 | 0 | `one_shot_clear` |
| S012 | 1976-09-04 | 1976-09-13 | short | 2 | 0 | 2 | `one_shot_clear` |
| S013 | 1976-10-08 | 1976-11-13 | long | 10 | 200 | 0 | `one_shot_clear` |
| S014 | 1976-11-17 | 1976-11-18 | long | 5 | 5 | 0 | `one_shot_clear` |
| S015 | 1976-11-19 | 1976-12-24 | short | 5 | 5 | 150 | `one_shot_clear` |

## 强样本验证

| 样本 | 结果 |
|---|---|
| 1976-03 `reset_after_clear` | pass |
| 1976-04 `lock_candidate` | pass |
| 1976-05 `unlock_then_clear` | pass |
| 1976-10 `center_then_add_on` | pass |
| 1976-11 `add_on_scale_alert_clear` | pass |
| 1976-11 `probe_clear_probe_flip_candidate` | pass |
| 1976-12 `staged_distribution` | pass |

1976-11 的 `probe -> clear -> probe -> reversal_flip candidate` 仍保留为人工复核，不由 v0.1 原型自动确认反手。

## 输出文件

运行命令：

```powershell
$env:PYTHONPATH='src'; python -m original_tachibana.pm_state
```

生成文件：

| 文件 | 用途 |
|---|---|
| `data/pioneer-1975-1976/backtest-v0.1/daily_replay.jsonl` | 729 行日级回放，含 `decision_basis_date` 与 `execution_timing`。 |
| `data/pioneer-1975-1976/backtest-v0.1/summary.json` | 交易段、事件日志、强样本验证、人工复核队列。 |

以上输出目录已加入 `.gitignore`，可随时由原始 JSON 再生成。

## 当前限制

- 未计算资金曲线、盈亏、胜率、回撤、手续费、滑点。
- `center_position`、利润保护、锁单确认、反手确认仍需人工标注。
- MALF 暂未接入；v0.1 只保留 MALF 背景接口。
- A 股适配版未进入本轮回测。
