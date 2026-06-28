# 首批 Execution Policy Research Agenda

本目录保存首批真实样本在 `execution_policy_research_prep` 之后继续收口的分组研究议题。

边界保持不变：

- 这里只记录“哪些执行政策主题已经进入研究准备，哪些还要补证据”。
- 不生成 `buy_signal / sell_signal / trade_accept / target_position / position_size`。
- 不定义 `ashare_t1_action / limit_up_strategy / limit_down_strategy`。

## 本批议题

| 议题 | agenda_status | 样本数 | 说明 |
|---|---|---:|---|
| `t1` | `ready_for_research` | 2 | `000001.SZ` 与 `300750.SZ` 都已具备进入 T+1 研究准备的条件。 |
| `price_limit` | `ready_for_research` | 2 | 两条样本都已具备 planned-event 级最小证据语义，可进入涨跌停研究准备。 |
| `suspension_resume` | `carry_forward_required` | 2 | 本窗口未触发停复牌事实，先续传。 |

说明：

- `600000.SH` 继续作为上游 blocked item 透传，不单独生成 agenda item。
- `ready_for_research` 只表示可以进入制度研究准备，不表示允许交易。
- `carry_forward_required` 是正常研究状态，不是系统错误。

## 验证命令

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-policy-research-agenda Z:\asteria-trading-lab\docs\tachibana\execution-policy-reviews\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data
```

预期结果：

- `execution_policy_research_agenda_count=3`
- `execution_policy_research_agenda_blocked_count=1`
- `agenda_status_counts.ready_for_research=2`
- `agenda_status_counts.carry_forward_required=1`
- `next_action=action:prepare_execution_policy_research`
