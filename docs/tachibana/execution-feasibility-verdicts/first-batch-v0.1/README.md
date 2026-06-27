# 首批人工 Execution Feasibility Verdict

本目录保存首批 3 条 A 股真实样本的人工 `AShareExecutionFeasibilityVerdict` 复核输入。

边界保持不变：

- 这里只记录执行可行性事实状态。
- 不生成 `buy_signal / sell_signal / trade_accept / target_position / position_size`。
- 不定义 `ashare_t1_action / limit_up_strategy / limit_down_strategy`。

## 本批裁决

| 样本 | status | 说明 |
|---|---|---|
| `000001.SZ` | `executable` | 计划事件为 `open_center`；制度事实显示事件日可交易、未停牌、整手单位明确，当前没有已知制度事实直接阻断该 replay。 |
| `300750.SZ` | `constrained` | 计划事件为 `add_on`；事件日可交易，但涨跌停价与触板状态仍是 `unknown`，且该样本本身属于 `Q-PRESSURE-ADJUST`，需要额外 PM/约束复核。 |
| `600000.SH` | `carry_forward_required` | 计划事件为 `lock_candidate`，Method 动作为 `wait_no_action`；它更像 PM 台账延续，不像已可回放的成交事件，因此先续传，不硬判成交可行。 |

## 验证命令

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-feasibility-verdict-merge Z:\asteria-trading-lab\docs\tachibana\execution-feasibility-verdicts\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data
```

预期结果：

- `execution_feasibility_verdict_ready_count=3`
- `000001.SZ -> executable`
- `300750.SZ -> constrained`
- `600000.SH -> carry_forward_required`

