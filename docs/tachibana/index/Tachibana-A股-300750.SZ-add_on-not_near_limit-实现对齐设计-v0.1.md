# Tachibana A股 300750.SZ add_on not_near_limit 实现对齐设计 v0.1

> 设计日期：2026-06-29
> 设计对象：`300750.SZ / add_on`
> 设计目标：说明机器态如何在不越过制度审计边界的前提下，从 `proximity_unknown` 接住已审定的 `not_near_limit` evidence

## 1. 背景

当前研究文档已经把 `300750.SZ / add_on` 的最佳 proximity 判断收口为：

- `current_best_proximity = not_near_limit`

证据来源是事件日 `lc5` intraday bars：

- `Z:\new_tdx64\vipdoc\sz\fzline\sz300750.lc5`
- `2026-04-03` 当日 5 分钟线覆盖整日交易
- 当日最高价 `400.80`，距涨停价 `481.40` 仍约 `16.74%`
- 当日最低价 `385.13`，距跌停价 `320.94` 仍约 `20.00%`

但当前代码里的 `_price_limit_event_relation()` 对 `planned_event == "add_on"` 仍固定输出：

- `price_limit_event_relation_status = relation_constrained`
- `price_limit_event_fill_blocking_status = fill_blocking_unknown`
- `price_limit_event_limit_proximity = proximity_unknown`
- `price_limit_event_relation_reason = planned_event_limit_proximity_is_unknown; planned_event_requires_higher_price_limit_resolution`

因此，当前差距不是枚举不够，也不是缺涨跌停边界，而是：

**机器态还没有一个受控入口来读取已经审定过的 planned-event proximity evidence。**

## 2. 设计边界

本设计不做以下事情：

- 不让 `ashare_intake_validator.py` 直接解析 `lc5` 原始行情
- 不把日线 `OHLC` 或任意 intraday 数据机械映射为 proximity
- 不把 `not_near_limit` 设为所有 `add_on` 的默认值
- 不新增 signal、仓位、成交许可或 backtest 字段
- 不把 `close_limit_status / touched_limit_status` 升级为最小字段集
- 不改变三道硬闸：
  - `institution_rule_definition_allowed = false`
  - `signal_generation_allowed = false`
  - `backtest_execution_allowed = false`

本设计只允许机器态消费一类输入：

**已经被研究文档或人工 review 明确审定的 planned-event relation evidence。**

## 3. 推荐实现形状

推荐新增一个小型 evidence artifact，而不是让 validator 直接推导行情关系。

建议路径：

`docs/tachibana/price-limit-event-relations/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json`

建议最小字段：

```json
{
  "record_type": "ASharePriceLimitEventRelationEvidence",
  "schema_version": "v0.1",
  "ashare_sample_id": "ASHARE-300750.SZ-2026-03-24-2026-04-03",
  "ts_code": "300750.SZ",
  "trade_date": "2026-04-03",
  "planned_event": "add_on",
  "method_action": "pullback_add",
  "price_limit_event_relation_status": "relation_constrained",
  "price_limit_event_fill_blocking_status": "fill_blocking_unknown",
  "price_limit_event_limit_proximity": "not_near_limit",
  "price_limit_event_relation_reason": [
    "planned_event_intraday_range_far_from_limit_bounds",
    "planned_event_not_near_limit_supported_by_reviewed_lc5_evidence"
  ],
  "price_limit_event_relation_ref": [
    "Z:\\new_tdx64\\vipdoc\\sz\\fzline\\sz300750.lc5",
    "docs/tachibana/index/Tachibana-A股-300750.SZ-add_on-price_limit-proximity-evidence-review-v0.1.md",
    "docs/tachibana/index/Tachibana-A股-300750.SZ-add_on-not_near_limit-收口草案-v0.1.md"
  ],
  "boundary_warning": [
    "relation_evidence_is_research_input_not_execution_rule",
    "do_not_emit_signal_from_relation_evidence",
    "do_not_infer_trade_accept_from_relation_evidence"
  ]
}
```

这个 artifact 的职责是：

- 保存已审定 proximity 结论
- 保存 evidence source
- 让 validator 消费“审定结果”，而不是自行解释行情

## 4. Validator 对齐方式

`ashare_intake_validator.py` 当前的最小变更点在 `_price_limit_event_relation(record, fact)` 附近。

推荐不要把外部原始行情读取塞进该函数。

更稳的设计是：

1. 在 execution policy candidate audit 的入口增加可选 relation evidence 目录参数
2. 读取 relation evidence JSON，按以下键匹配：
   - `ashare_sample_id`
   - `ts_code`
   - `trade_date`
   - `planned_event`
3. 若匹配到合法 evidence，`_price_limit_event_relation()` 使用 evidence 中的 relation fields
4. 若没有匹配 evidence，保持当前默认逻辑：
   - `add_on` 仍输出 `relation_constrained + proximity_unknown`
5. 若 evidence 字段非法或枚举越界，audit 应 blocked，而不是静默回退

这能保留当前默认安全行为，同时让已审定的 `not_near_limit` 进入机器态。

## 5. 预期机器态变化

当 relation evidence 存在且合法时，`300750.SZ / add_on` 的 price-limit candidate 应变成：

```json
{
  "candidate_constraint_type": "price_limit",
  "candidate_status": "review_required",
  "price_limit_event_relation_status": "relation_constrained",
  "price_limit_event_fill_blocking_status": "fill_blocking_unknown",
  "price_limit_event_limit_proximity": "not_near_limit",
  "price_limit_event_relation_reason": [
    "planned_event_intraday_range_far_from_limit_bounds",
    "planned_event_not_near_limit_supported_by_reviewed_lc5_evidence"
  ]
}
```

保持不变的是：

- `candidate_status = review_required`
- `institution_rule_definition_allowed = false`
- `signal_generation_allowed = false`
- `backtest_execution_allowed = false`
- 不输出 `trade_accept`
- 不输出 `position_size`
- 不输出 `limit_up_strategy / limit_down_strategy`

## 6. 测试要求

若后续进入实现，至少补三类测试。

### 6.1 pass：合法 evidence 推进到 `not_near_limit`

输入：

- `planned_event = add_on`
- price-limit bounds 存在
- relation evidence JSON 匹配当前样本
- evidence proximity 为 `not_near_limit`

期望：

- `candidate_status = review_required`
- `price_limit_event_relation_status = relation_constrained`
- `price_limit_event_fill_blocking_status = fill_blocking_unknown`
- `price_limit_event_limit_proximity = not_near_limit`
- reason/ref 来自 relation evidence

### 6.2 blocked：非法 proximity evidence 不允许静默消费

输入：

- relation evidence JSON 匹配当前样本
- `price_limit_event_limit_proximity = unsupported_value`

期望：

- audit blocked 或 candidate evidence incomplete
- 输出明确 reason，例如：
  `invalid_price_limit_event_relation_evidence_enum`
- 不回退成看似正常的 `proximity_unknown`

### 6.3 禁用字段校验：三道硬闸仍为 false

输入：

- 合法 relation evidence 推进到 `not_near_limit`

期望：

- `institution_rule_definition_allowed = false`
- `signal_generation_allowed = false`
- `backtest_execution_allowed = false`
- candidate 不包含：
  - `trade_accept`
  - `position_size`
  - `limit_up_strategy`
  - `limit_down_strategy`

## 7. 当前结论

本设计推荐的下一步实现方向是：

**新增一个已审定 planned-event relation evidence artifact，并让 validator 可选消费它。**

这条路线比直接解析 `lc5` 更稳，因为它保留了研究层与审计层边界：

- 研究层负责解释 `lc5` 是否足以支撑 `not_near_limit`
- 审计层只负责读取已审定 relation evidence，并保持所有交易相关硬闸关闭

因此，当前不需要升级 `close_limit_status / touched_limit_status`，也不需要进入 signal、仓位或 backtest。
