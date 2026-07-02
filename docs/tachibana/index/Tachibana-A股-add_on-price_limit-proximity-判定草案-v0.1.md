# Tachibana A股 add_on price_limit proximity 判定草案 v0.1

> 研究日期：2026-06-28
> 研究范围：A 股首批真实样本 `2026-03-24` 至 `2026-04-03` 窗口内，`300750.SZ / add_on` 的 `price_limit_event_limit_proximity` 研究语义；仅将 `000001.SZ / open_center` 作为边界对照

## 1. 目标与边界

本草案只回答一个问题：

**`price_limit_event_limit_proximity` 这组枚举，是否已经足够服务 `add_on` 的研究判断。**

本草案不做以下事情：

- 不定义 `limit_up_strategy / limit_down_strategy`
- 不生成 signal
- 不生成 `trade_accept`
- 不定义仓位
- 不把 `close_limit_status / touched_limit_status` 重新抬回研究入口硬闸
- 不讨论 `open_center` 的完整语义设计

这里的“足够”，只表示：它是否已经足以支撑 `add_on` 的 **研究准备层** 判断，而不是是否足以直接支撑规则定义。

## 2. 当前枚举范围

当前 `price_limit_event_limit_proximity` 的研究枚举为：

- `not_near_limit`
- `near_limit`
- `at_limit`
- `proximity_unknown`

对 `add_on` 而言，本轮不讨论 `not_applicable`，因为 `add_on` 天然需要 price-limit proximity 语义。

## 3. 真实锚点

已核实事实：

- `300750.SZ` 的 `planned_event` 是 `add_on`，`method_action` 是 `pullback_add`，并且当前 execution feasibility verdict 为 `constrained`。[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../method-pm-plans/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)、[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)
- 真实链路验证中，该样本当前的 relation 语义为：
  - `price_limit_event_relation_status = relation_constrained`
  - `price_limit_event_fill_blocking_status = fill_blocking_unknown`
  - `price_limit_event_limit_proximity = proximity_unknown`
- 尽管如此，`price_limit` research agenda 已经进入 `ready_for_research`，说明当前链路允许“研究先开始，再继续补 proximity 分辨率”。

研究推断：

- 眼下 `300750.SZ / add_on` 的问题，不是枚举值不存在，而是当前真实样本仍然落在 `proximity_unknown`。
- 因此本草案要判断的是：**如果后续 evidence 可以把它从 `proximity_unknown` 推到 `not_near_limit / near_limit / at_limit` 之一，这组枚举本身是否已经够用。**

## 4. 四值判定表

| proximity 值 | 能否支持 `add_on` 研究判断 | 当前含义 | 是否需要立刻升级到 `close/touched` |
|---|---|---|---|
| `not_near_limit` | 能 | 当前追加动作距离板边不近，price-limit 不是主要研究阻断 | 否 |
| `near_limit` | 能 | 当前追加动作已接近板边，需要更强约束审查，但仍不等于显式阻断 | 否 |
| `at_limit` | 能 | 当前追加动作已到板边，足以表达高约束或近阻断研究语义 | 否 |
| `proximity_unknown` | 不能独立完成判断，但能支撑“继续研究” | 当前还不知道是否近板，因此只能保留 `relation_constrained` 或继续补证据 | 否，先补 proximity evidence |

这张表的关键点是：

- `not_near_limit / near_limit / at_limit` 三个值，已经能形成一套研究级分辨率
- 真正不够的不是枚举设计本身，而是样本仍停在 `proximity_unknown`

## 5. 三个研究场景

### 场景 A：近板但未阻断

语义形状：

- `price_limit_event_fill_blocking_status = no_explicit_fill_blocking_fact`
- `price_limit_event_limit_proximity = near_limit`
- `price_limit_event_relation_status = relation_constrained`

研究判断：

- 这个 `add_on` 样本仍然可以进入研究
- 但研究者必须显式看到“接近板边”的约束
- 这里不必先知道 `close_limit_status / touched_limit_status`

结论：

- 现有 proximity 枚举足够表达这一场景

### 场景 B：到板边且可能阻断

语义形状：

- `price_limit_event_fill_blocking_status = explicit_fill_blocking_fact` 或仍待核实
- `price_limit_event_limit_proximity = at_limit`
- `price_limit_event_relation_status = relation_blocked` 或 `relation_constrained`

研究判断：

- 这个 `add_on` 样本已经是高约束甚至阻断候选
- 研究语义需要明确“已经到板边”
- 这依然可以由 `at_limit` 承载，而不必自动升级到 `close/touched`

结论：

- 现有 proximity 枚举足够表达这一场景

### 场景 C：信息不足

语义形状：

- `price_limit_event_fill_blocking_status = fill_blocking_unknown`
- `price_limit_event_limit_proximity = proximity_unknown`
- `price_limit_event_relation_status = relation_constrained`

研究判断：

- 当前只能说明“样本仍值得研究，但 proximity 证据不足”
- 这时缺的是 proximity evidence，不是缺新的状态字段契约

结论：

- 现有 proximity 枚举仍然足够表达“暂时不知道”
- 当前正确动作是继续补事件关系证据，而不是直接升级到 `close_limit_status / touched_limit_status`

## 6. 对照样本的边界意义

`000001.SZ / open_center` 当前使用的是：

- `relation_clear`
- `no_explicit_fill_blocking_fact`
- `not_applicable`

它的作用不是参与这次 proximity 判定，而是提醒我们：

- `open_center` 已经证明不是所有 planned-event 都要先拿到更高价格状态分辨率
- 因此 `add_on` 的 proximity 需求应被视为 **事件特异性的研究需求**
- 这进一步支持：先看 proximity 枚举是否够用，而不是直接把整条线拖去扩 `close/touched`

## 7. 判定结论

本草案的单一结论是：

**当前 `price_limit_event_limit_proximity` 这组枚举，已经足够服务 `add_on` 的研究判断。**

原因有三点：

1. `not_near_limit / near_limit / at_limit` 已经构成了足够清晰的研究级接近关系分辨率
2. `proximity_unknown` 也能稳定表达“当前证据不足但不必立刻扩字段”的状态
3. 当前真实样本 `300750.SZ / add_on` 暂时卡住的，是 evidence 仍为 `proximity_unknown`，不是枚举本身不够

因此本轮判断是：

- **继续坚持 `planned-event relation fact`**
- **不需要现在升级到 `close_limit_status / touched_limit_status`**
- **也不需要先扩 proximity 枚举**

## 8. 唯一后续闸门

只有当后续真实样本反复出现以下问题时，才应重开这一判定：

- `near_limit` 与 `at_limit` 仍不足以支撑 `add_on` 的研究差异
- 研究者必须额外知道更高价格状态分辨率，才能判断“近板但未阻断”和“已到板边”的不同研究含义

若真的出现这种重复歧义，下一轮才需要二选一：

1. 先扩 proximity 枚举
2. 再评估是否升级到 `close_limit_status / touched_limit_status`

但截至当前证据，本草案不支持立即走这一步。
