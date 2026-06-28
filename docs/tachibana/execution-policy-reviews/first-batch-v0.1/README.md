# 首批人工 Execution Policy Reviews

本目录保存首批真实样本在 `execution policy candidates` 之后的人工复核输入。

边界保持不变：

- 这里只记录“候选约束是否值得继续归档/研究”。
- 不生成 `buy_signal / sell_signal / trade_accept / target_position / position_size`。
- 不定义 `ashare_t1_action / limit_up_strategy / limit_down_strategy`。

## 本批复核

| 样本 | 候选 | review_status | 说明 |
|---|---|---|---|
| `000001.SZ` | `t1` | `review_required` | `open_center` 属于真实执行动作，值得进入后续 T+1 事实研究。 |
| `000001.SZ` | `price_limit` | `review_required` | 已具备 planned-event 级最小证据语义，可进入涨跌停执行政策研究准备。 |
| `300750.SZ` | `t1` | `review_required` | `add_on` 属于真实执行动作，值得进入后续 T+1 事实研究。 |
| `300750.SZ` | `price_limit` | `review_required` | 已具备 planned-event 级最小证据语义，可进入涨跌停执行政策研究准备。 |

说明：

- `suspension_resume` 在本批两个样本上都属于 `not_triggered_in_fact_window`，merge 时自动归档为 `carry_forward_required`，不要求人工 JSON 显式填写。
- `600000.SH` 当前上游 outcome 为 `carry_forward_required`，本层不单独生成人工候选复核文件。

## 验证命令

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-policy-review-merge Z:\asteria-trading-lab\docs\tachibana\execution-policy-reviews\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data
```

预期结果：

- `execution_policy_review_count=6`
- `execution_policy_review_blocked_count=1`
- `price_limit` 在两条真实样本上进入 `review_required`
- `000001.SZ` 生成 3 条 review records
- `300750.SZ` 生成 3 条 review records
- `600000.SH` 不生成 review record，只保留 blocked item
