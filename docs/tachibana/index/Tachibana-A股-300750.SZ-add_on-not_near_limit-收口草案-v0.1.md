# Tachibana A股 300750.SZ add_on not_near_limit 收口草案 v0.1

> 研究日期：2026-06-29
> 研究对象：`300750.SZ / add_on`
> 研究目标：确认当前 `lc5` intraday evidence 是否已经足以把 `300750.SZ / add_on` 的 `price_limit_event_limit_proximity` 从研究 review 层收口到 `not_near_limit`

## 1. 目标与边界

本草案只回答一个问题：

**对当前真实样本 `300750.SZ / add_on` 而言，已有 `lc5` 事件日盘中证据是否足以支撑 `not_near_limit`。**

本草案不做以下事情：

- 不定义 `limit_up_strategy / limit_down_strategy`
- 不生成 signal
- 不生成 `trade_accept`
- 不定义仓位或 backtest
- 不把日线 `OHLC` 机械映射成 proximity 结论
- 不把 `close_limit_status / touched_limit_status` 升级为研究入口硬闸
- 不把当前单样本证据直接推广成所有 `add_on` 的通用规则

这里的“收口”，只表示研究准备层可以把当前样本的最佳 proximity 判断固定为 `not_near_limit`。它不等于进入规则定义层，也不等于自动修改机器态输出。

## 2. 当前证据锚点

上一轮 evidence review 已经核实：

- `300750.SZ` 的 planned event 是 `add_on`
- `method_action = pullback_add`
- 当前机器态仍输出：
  - `price_limit_event_relation_status = relation_constrained`
  - `price_limit_event_fill_blocking_status = fill_blocking_unknown`
  - `price_limit_event_limit_proximity = proximity_unknown`
- 事件日外部盘中数据存在：
  `Z:\new_tdx64\vipdoc\sz\fzline\sz300750.lc5`
- `2026-04-03` 当日 `lc5` 覆盖整日 5 分钟交易范围
- 当日涨跌停边界已经存在于 institution facts 中：
  - `limit_up_price = 481.40`
  - `limit_down_price = 320.94`

`lc5` review 给出的关键数值是：

| 项目 | 数值 | 与边界关系 |
|---|---:|---|
| 当日最高价 | `400.80` | 距涨停价 `481.40` 仍差 `80.60`，约 `16.74%` |
| 当日最低价 | `385.13` | 距跌停价 `320.94` 仍高 `64.19`，约 `20.00%` |

## 3. 为什么这条 evidence 足以支撑 `not_near_limit`

当前样本缺少 planned-event 的精确分钟锚点，因此不能用“事件发生时刻价格”直接判定 proximity。

但是，`lc5` evidence 在当前样本上提供了一种更强的反证：

- 盘中 5 分钟线覆盖了整个事件日
- 整日最高价仍远低于涨停价
- 整日最低价仍远高于跌停价
- 因此，不论 planned-event 的精确分钟落在当日哪个 5 分钟区间，价格都没有接近任一涨跌停边界

这使得当前样本可以从“缺少精确事件分钟”推进到一个稳定研究判断：

- `current_best_proximity = not_near_limit`

这里的关键不是“只要有 intraday 就能判断”，而是：

**当事件日完整 intraday 范围本身已经整体远离上下边界时，精确事件分钟缺失不再阻止 `not_near_limit` 判断。**

## 4. 为什么不支持 `near_limit / at_limit`

当前证据不能支持 `near_limit`，原因是：

- 没有 planned-event 级文字或结构化记录说明“接近板边”
- `lc5` 的整日最高价与最低价都远离上下边界
- 没有出现“接近边界但未到边界”的价格关系事实

当前证据也不能支持 `at_limit`，原因是：

- 当日最高价未触及涨停价
- 当日最低价未触及跌停价
- 没有显式 fill blocking fact 说明事件已被涨跌停边界阻断

因此，本轮不应为了追求更强状态而把当前样本改判为 `near_limit` 或 `at_limit`。

## 5. 适用范围

当前 `not_near_limit` 收口只适用于满足以下条件的样本：

1. planned event 已经明确为需要 proximity 审查的事件，例如当前 `add_on`
2. 事件日的涨跌停上下边界已经存在
3. 事件日 intraday 数据覆盖足以代表当天交易范围
4. 当日 intraday 最高价与最低价均明显远离对应边界
5. 没有相反的 planned-event 级近板、到板或显式阻断证据

若缺少第 3 或第 4 条，就不能照搬本草案结论。

## 6. 与 `close/touched` 升级闸门的关系

本草案不触发 `close_limit_status / touched_limit_status` 升级。

原因是：

- 当前缺口已经被 `lc5` 反证型 evidence 收窄为 `not_near_limit`
- 没有出现 `near_limit` 与 `at_limit` 无法由 relation fact 稳定表达的重复歧义
- 没有证据表明研究者必须依赖更高价格状态字段才能判断当前样本

因此，当前推荐仍然是：

- `recommended_fact_layer = prefer_planned_event_relation_fact`

`close_limit_status / touched_limit_status` 继续作为后备升级层，而不是当前最小字段集。

## 7. 当前收口结论

本草案的单一结论是：

**`300750.SZ / add_on` 当前已经可以把 research review 层的最佳 proximity 判断收口为 `not_near_limit`。**

更具体地说：

- `lc5` intraday evidence 足以作为当前样本的 `not_near_limit` 支撑来源
- 当前没有证据支持 `near_limit`
- 当前没有证据支持 `at_limit`
- 当前不应升级到 `close_limit_status / touched_limit_status`
- 当前不应进入 signal、仓位或 backtest

## 8. 下一步

下一步可以进入实现对齐设计，但实现前必须保留以下约束：

1. 机器态若要从 `proximity_unknown` 接住 `not_near_limit`，必须引用明确 evidence source，而不是凭日线价格推断
2. 实现只能把这类证据作为 planned-event relation evidence，而不是制度事实主字段
3. 任何实现都不得把 `lc5` 的当前单样本结论泛化成“所有 `add_on` 默认不近板”
4. 若后续找到直接支持 `near_limit / at_limit` 的 planned-event 级证据，应重新打开 review 表，而不是在本草案上直接覆盖结论
