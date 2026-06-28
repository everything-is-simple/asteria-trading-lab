# 首批人工 Execution Policy Archive

本目录保存首批真实样本在 `execution policy review merge` 之后的只读归档结果。

边界保持不变：

- 这里只记录“候选约束归档后的研究准备状态”。
- 不生成 `buy_signal / sell_signal / trade_accept / target_position / position_size`。
- 不定义 `ashare_t1_action / limit_up_strategy / limit_down_strategy`。

## 本批预期归档

| 样本 | 归档候选 | archive_status | 说明 |
|---|---|---|---|
| `000001.SZ` | `t1` | `review_required` | 进入后续执行政策研究准备。 |
| `000001.SZ` | `price_limit` | `review_required` | 已具备事件级最小证据语义，进入执行政策研究准备。 |
| `000001.SZ` | `suspension_resume` | `carry_forward_required` | 本窗口未触发，自动续传。 |
| `300750.SZ` | `t1` | `review_required` | 进入后续执行政策研究准备。 |
| `300750.SZ` | `price_limit` | `review_required` | 已具备事件级最小证据语义，进入执行政策研究准备。 |
| `300750.SZ` | `suspension_resume` | `carry_forward_required` | 本窗口未触发，自动续传。 |

说明：

- `600000.SH` 继续作为上游 blocked item 透传，不生成 archive record。
- `review_required` 只表示进入 `action:prepare_execution_policy_research`，不表示允许交易。
- `carry_forward_required` 仍是有效归档结果，不是系统错误。

## 验证命令

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-policy-archive Z:\asteria-trading-lab\docs\tachibana\execution-policy-reviews\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data
```

预期结果：

- `execution_policy_archive_count=6`
- `execution_policy_archive_blocked_count=1`
- `archive_status_counts.review_required=4`
- `archive_status_counts.carry_forward_required=2`
- `000001.SZ` 生成 3 条 archive records
- `300750.SZ` 生成 3 条 archive records
- `600000.SH` 不生成 archive record，只保留 blocked item
- `next_action=action:prepare_execution_policy_research`
