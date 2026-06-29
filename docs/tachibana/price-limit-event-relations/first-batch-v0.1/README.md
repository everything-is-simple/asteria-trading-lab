# 首批 reviewed price limit event relations

本目录保存首批真实样本在 `price_limit` 研究准备层使用的 reviewed planned-event relation evidence。

边界保持不变：

- 这里只记录 **已审定的 planned-event relation judgment**
- 不直接存原始行情解析逻辑
- 不生成 `buy_signal / sell_signal / trade_accept / target_position / position_size`
- 不定义 `ashare_t1_action / limit_up_strategy / limit_down_strategy`
- 不把 relation evidence 回写成 `institution-facts-v0.1` 主字段契约

## 当前定位

本目录中的 JSON 应被视为：

- `price_limit` 研究准备层的**标准可选输入接口**
- 用于承接人工 review 后的样本级 relation judgment

它不是：

- 所有样本都必须先具备的硬前提
- validator 自行解析原始 `lc5` 的替代实现
- 规则定义层或交易执行层输入

## 当前覆盖

当前首批样本只落地了 1 份 reviewed relation evidence：

| 样本 | planned_event | 当前结论 |
|---|---|---|
| `300750.SZ` | `add_on` | `price_limit_event_limit_proximity = not_near_limit` |

这意味着：

- 目录接口已经成立
- 但当前覆盖面仍然是单样本

## JSON 契约要点

当前 validator 会校验以下核心字段：

- `record_type`
- `schema_version`
- `ashare_sample_id`
- `ts_code`
- `trade_date`
- `planned_event`
- `price_limit_event_relation_status`
- `price_limit_event_fill_blocking_status`
- `price_limit_event_limit_proximity`
- `price_limit_event_relation_reason`
- `price_limit_event_relation_ref`

非法 evidence 会在 candidate audit 上游直接触发 `blocked`，而不是静默回退。

## 使用方式

CLI 入口：

```powershell
$env:PYTHONPATH='src'
python -m ashare_intake_validator `
  --root Z:\asteria-trading-labs-data `
  --audit-first-batch-execution-policy-candidates Z:\asteria-trading-lab\docs\tachibana\execution-feasibility-verdicts\first-batch-v0.1 `
  --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 `
  --institution-fact-root Z:\asteria-trading-labs-data `
  --price-limit-event-relation-dir Z:\asteria-trading-lab\docs\tachibana\price-limit-event-relations\first-batch-v0.1
```

## 当前结论

本目录当前应被理解为：

- `relation_fact_minimum_semantics` 之上的 reviewed override 输入层
- 用来把研究层已审定结论稳定接回机器态

它的默认策略应当是：

- 没有 reviewed evidence 时，保持现有最小关系语义输出
- 有合法 reviewed evidence 时，消费它并保留三道硬闸为 `false`
