# Tachibana A股 add_on price_limit proximity evidence 采集清单 v0.1

> 研究日期：2026-06-28
> 研究范围：A 股首批真实样本 `2026-03-24` 至 `2026-04-03` 窗口内，`300750.SZ / add_on` 的 `price_limit_event_limit_proximity` 证据采集；目标是把 `proximity_unknown` 尽量推进到 `not_near_limit / near_limit / at_limit`

## 1. 目标与边界

本清单只回答一个问题：

**后续应该补哪些 evidence，才能把 `300750.SZ / add_on` 当前的 `proximity_unknown` 推进到更具体的 proximity 状态。**

本清单不做以下事情：

- 不定义 `limit_up_strategy / limit_down_strategy`
- 不生成 signal
- 不生成 `trade_accept`
- 不定义仓位
- 不把 `close_limit_status / touched_limit_status` 直接设为新的研究入口硬闸
- 不把普通日线 `OHLC` 直接等同于 `close_limit_status / touched_limit_status`

这里讨论的是 **evidence 采集顺序**，不是规则实现顺序。

## 2. 当前起点

已核实事实：

- 当前真实样本 `300750.SZ / add_on` 在链路中已经是：
  - `price_limit_event_relation_status = relation_constrained`
  - `price_limit_event_fill_blocking_status = fill_blocking_unknown`
  - `price_limit_event_limit_proximity = proximity_unknown`
- 当前 research agenda 已允许该样本进入 `ready_for_research`。
- 上一份 proximity 判定草案已经确认：现有 proximity 枚举本身是够用的，当前缺的是 evidence，不是枚举设计。

因此当前问题不是“要不要新枚举”，而是：

- 先补什么 evidence
- 用什么 evidence 才能把 `proximity_unknown` 推成可用状态

## 3. 目标状态与最小证据

| 目标 proximity 状态 | 最小需要回答的问题 | 最小可接受 evidence |
|---|---|---|
| `not_near_limit` | 事件日追加动作与涨跌停边界不近吗 | 存在明确的事件级价格关系证据，足以说明 planned-event 发生时不在板边附近 |
| `near_limit` | 事件日追加动作接近板边但未明确到板吗 | 存在明确的事件级接近边界证据，足以说明接近板边但不是显式 `at_limit` |
| `at_limit` | 事件日追加动作已经到板边吗 | 存在明确的事件级到板边证据，足以说明 planned-event 已处于板边状态 |
| `proximity_unknown` | 目前仍无法判断吗 | 现有证据不足以上述三种任一状态做出稳定判断 |

关键原则：

- 要推进到前三种状态，需要的是 **事件级 price-limit relation evidence**
- 如果只有“边界价格存在”而没有事件级关系证据，就应继续留在 `proximity_unknown`

## 4. 证据来源优先级

### 优先级 1：planned-event 级显式研究记录

最优先的 evidence 来源，是直接围绕 `add_on` 事件本身的人工研究记录或复核结论，例如：

- planned-event 当天追加动作是否已接近板边
- planned-event 当天是否已经到板边
- planned-event 当天是否存在“可研究但受板边压制”的显式说明

如果这类记录存在，它们最贴近当前字段语义，因为 `price_limit_event_limit_proximity` 本来就是 planned-event relation fact，而不是通用日线状态。

适用结论：

- 这类 evidence 可以直接把 `proximity_unknown` 推到
  - `not_near_limit`
  - `near_limit`
  - `at_limit`

### 优先级 2：与 limit bounds 对齐的事件级价格关系事实

第二优先级是：虽然没有直接写出 “near_limit / at_limit” 文字判断，但已经存在足够明确的事件级价格关系事实，例如：

- planned-event 对应时点或时段的价格相对 `limit_up_price / limit_down_price` 的关系
- planned-event 所在动作是否已明确贴近上边界或下边界
- planned-event 是否已经处在“再推进就会触边”的研究语义上

这类 evidence 仍然可以支撑 proximity 分类，但前提是它必须是 **事件级**，而不是只来自粗粒度日线终值。

适用结论：

- 若证据明确显示“离边界不近”，可推到 `not_near_limit`
- 若证据明确显示“接近边界但未到边界”，可推到 `near_limit`
- 若证据明确显示“已到边界”，可推到 `at_limit`

### 优先级 3：显式阻断 / 非阻断事实作为辅助

`price_limit_event_fill_blocking_status` 不单独决定 proximity，但它能帮助收窄：

- `explicit_fill_blocking_fact` 常常提示需要优先核查是否已 `at_limit`
- `no_explicit_fill_blocking_fact` 不能直接推出 `not_near_limit`
- `fill_blocking_unknown` 说明 proximity 仍然需要独立补证

适用结论：

- 这类 evidence 只能辅助 proximity 判断
- 它不能单独把 `proximity_unknown` 推进到具体 proximity 状态

## 5. 当前不应直接采用的“伪证据”

以下材料当前不应被直接拿来把 `proximity_unknown` 推成具体值：

1. 单纯知道 `limit_up_price / limit_down_price` 非空  
   这只能说明边界存在，不能说明事件与边界的关系。

2. 单纯知道 `is_suspended=false`  
   这只能说明没有停牌硬阻断，不能说明是否接近板边。

3. 单纯把日线 `close / high / low` 机械映射成 proximity  
   这会把事件级研究语义偷换成通用行情状态，边界太粗，容易滑向 `close/touched` 的伪实现。

4. 单纯因为 `add_on` 是高敏感事件，就默认设成 `near_limit`  
   这是先下研究结论，再补证据，顺序反了。

## 6. 面向 `300750.SZ / add_on` 的采集顺序

对当前真实样本，建议按以下顺序补证据：

1. 先看是否已有 planned-event 级人工研究记录  
   目标是找出有没有直接表达“接近板边 / 已到板边 / 明显不近”的文字或结构化结论。

2. 再看是否已有可与 `limit_up_price / limit_down_price` 对齐的事件级价格关系描述  
   目标是确认 planned-event 所在时点或时段，是否已经被明确描述为靠近边界。

3. 再把显式阻断事实拿来做辅助交叉核对  
   目标是避免把 “显式阻断” 和 “接近板边” 混成一个字段。

4. 如果以上三步都拿不到足够 evidence  
   保持 `proximity_unknown`，不要抢跑升级到 `close_limit_status / touched_limit_status`

## 7. 推进规则

### 推进到 `not_near_limit`

需要：

- 存在事件级 evidence，明确说明 planned-event 与板边不近
- 且没有相反的近板或到板边证据

### 推进到 `near_limit`

需要：

- 存在事件级 evidence，明确说明 planned-event 接近板边
- 但还不足以认定已经到板边

### 推进到 `at_limit`

需要：

- 存在事件级 evidence，明确说明 planned-event 已到板边
- 或存在等价的显式到板边关系事实

### 保持 `proximity_unknown`

需要：

- 没有足够事件级 evidence
- 或现有 evidence 彼此冲突
- 或现有 evidence 只能说明边界存在，但不能说明事件与边界关系

## 8. 当前结论

本清单的当前结论是：

- 对 `300750.SZ / add_on`，下一步最该补的是 **planned-event 级 proximity evidence**
- 当前没有必要先升级到 `close_limit_status / touched_limit_status`
- 当前也没有必要先扩 `price_limit_event_limit_proximity` 枚举

真正的缺口是：

- **还没有足够强的事件级 relation evidence，把当前样本从 `proximity_unknown` 推进到具体 proximity 状态**

## 9. 下一步最具体动作

这份清单落地后，下一步最具体该做的是：

1. 为 `300750.SZ / add_on` 建一个最小 evidence review 表
2. 逐项检查是否已有：
   - planned-event 级显式研究记录
   - 与 limit bounds 对齐的事件级价格关系事实
   - 可辅助 proximity 判断的显式阻断事实
3. 只输出一个结果：
   - 仍然 `proximity_unknown`
   - 或推进到 `not_near_limit / near_limit / at_limit`

如果这一步做完仍然长期停在 `proximity_unknown`，下一轮再重新评估是否需要升级事实层。
