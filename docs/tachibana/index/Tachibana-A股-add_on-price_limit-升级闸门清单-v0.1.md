# Tachibana A股 add_on price_limit 升级闸门清单 v0.1

> 研究日期：2026-06-28
> 研究范围：A 股首批真实样本 `2026-03-24` 至 `2026-04-03` 窗口内，`300750.SZ / add_on` 的 `price_limit` 研究语义升级闸门；以 `000001.SZ / open_center` 作为对照样本

## 1. 目标与边界

本清单只回答一个问题：

**对 `add_on` 而言，什么情况下 `planned-event relation fact` 仍然够用，什么情况下才必须升级到 `close_limit_status / touched_limit_status`。**

本清单不做以下事情：

- 不定义 `limit_up_strategy / limit_down_strategy`
- 不生成 signal
- 不生成 `trade_accept`
- 不定义仓位或 `position_size`
- 不把 `close_limit_status / touched_limit_status` 重新抬回“研究入口硬闸”

这里讨论的“升级”，只表示 **研究语义分辨率需要提高**，不表示进入规则定义层。仓库现有边界仍然成立：制度层只表达执行约束与研究准备，不抢占 Method、PM、Signal 或 Backtest 的定义权。

## 2. 当前已核实事实

### 2.1 `300750.SZ / add_on`

已核实事实：

- `300750.SZ` 的 `planned_event` 是 `add_on`，`method_action` 是 `pullback_add`，且 `pm_required=true`。[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../method-pm-plans/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)
- 当前 execution feasibility verdict 是 `constrained`，并保留了 `limit_state_unknown_on_planned_event` 这一 blocked reason。[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)
- 真实链路验证已经表明：`price_limit` candidate 可进入 `review_required`，其关系语义为 `relation_constrained + fill_blocking_unknown + proximity_unknown`。
- 同一轮真实链路里，`price_limit` research agenda 已经是 `ready_for_research`，且包含 `ASHARE-300750.SZ-2026-03-24-2026-04-03`。

研究推断：

- 当前 `add_on` 的缺口已经不是“没有 price-limit 边界”，而是“是否需要更高价格状态分辨率才能表达近板但未明确阻断的事件关系”。

### 2.2 `000001.SZ / open_center`

已核实事实：

- `000001.SZ` 的 `planned_event` 是 `open_center`，`method_action` 是 `trend_probe_entry`。[ASHARE-000001.SZ-2026-03-24-2026-04-03.json](../method-pm-plans/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json)
- 真实链路验证已经表明：`price_limit` candidate 可进入 `review_required`，其关系语义为 `relation_clear + no_explicit_fill_blocking_fact + not_applicable`。

研究推断：

- `open_center` 已经证明：只要能表达“无显式制度阻断”，就不必先升级到 `close/touched`。
- 它在本清单里的作用是对照样本，用来说明为什么 `add_on` 的升级闸门应更严格，但不能失焦成整条线都去扩张通用状态字段。

## 3. `planned-event relation fact` 仍然够用的情况

对 `add_on` 而言，只要以下三个条件同时成立，`planned-event relation fact` 仍然够用：

1. 已经能表达是否存在显式追加阻断事实  
   也就是当前至少能区分：
   `no_explicit_fill_blocking_fact / explicit_fill_blocking_fact / fill_blocking_unknown`

2. 已经能表达事件与涨跌停边界的研究级接近关系  
   也就是当前至少能区分：
   `not_near_limit / near_limit / at_limit / proximity_unknown`

3. 即使没有 `close_limit_status / touched_limit_status`，研究者仍然能对该 `add_on` 样本做出稳定的研究入口判断  
   换句话说，`relation_status + fill_blocking_status + limit_proximity` 已足以回答：
   - 这是无阻断的可研究样本
   - 这是受约束但仍可研究的样本
   - 这是存在显式阻断的样本

满足以上三点时，推荐继续坚持：

- `recommended_fact_layer = prefer_planned_event_relation_fact`

此时 `close_limit_status / touched_limit_status` 仍然只是可选补充，而不是必要前提。

## 4. 必须升级到 `close_limit_status / touched_limit_status` 的情况

只有当以下条件出现时，`add_on` 才必须升级：

1. `relation fact` 已经足够表达“有没有显式阻断”，但仍然无法稳定表达“接近板边但未明确阻断”的研究差异
2. 研究判断反复依赖更高价格状态分辨率，且这种分辨率不能再被 `limit_proximity` 的现有枚举稳定承载
3. 不引入 `close_limit_status / touched_limit_status` 时，研究者会持续遇到同一种歧义：
   - `near_limit` 与 `at_limit` 对 `add_on` 的研究判断不同
   - 这种不同会改变是否需要升级到更强约束审查
   - 这种不同又不能仅靠显式阻断事实解释

当以上三点同时成立时，才触发：

- `recommended_fact_layer = require_hybrid_fact_set`

这里的混合方案含义是：

- 继续保留 `planned-event relation fact` 作为第一层
- 额外引入 `close_limit_status / touched_limit_status` 作为第二层分辨率补充
- 但仍不把它们扩写成规则字段或研究入口硬闸

## 5. 唯一升级闸门

本清单把升级判据固定成一句话：

**只有当 `add_on` 的研究判断持续需要区分“近板但未明确阻断”与“已到板边或近似到板边”的更高状态分辨率，而该差异又不能由现有 `planned-event relation fact` 稳定表达时，才升级到 `close_limit_status / touched_limit_status`。**

这意味着：

- 不是因为“想更精细”就升级
- 不是因为 `close/touched` 目前是 `unknown` 就升级
- 不是因为 `open_center` 已经 ready，就顺手把 `add_on` 也拖进通用状态扩张

只有一种合法升级路径：

- `relation fact` 已经先被充分尝试
- `relation fact` 仍然无法承载 `add_on` 的关键研究差异
- 该差异确实需要更高价格状态分辨率

## 6. `add_on` 与 `open_center` 的闸门差异

| 维度 | `open_center` | `add_on` |
|---|---|---|
| 当前最小问题 | 是否有显式制度阻断 | 是否有显式制度阻断，以及是否已接近板边到影响追加研究 |
| 是否天然需要 proximity 语义 | 弱 | 强 |
| 是否应默认升级到 `close/touched` | 否 | 否 |
| 是否可能触发混合方案 | 低 | 高 |
| 当前推荐 | `prefer_planned_event_relation_fact` | 先 `prefer_planned_event_relation_fact`，若闸门触发再升 `require_hybrid_fact_set` |

结论：

- `open_center` 已经证明 relation fact 可以单独成立。
- `add_on` 不是一开始就需要 `close/touched`，而是 **唯一允许在后续样本中触发升级闸门的高敏感事件类型**。

## 7. 当前结论与下一步

当前结论：

- 对 `300750.SZ / add_on`，现阶段仍应优先采用 `planned-event relation fact`
- `close_limit_status / touched_limit_status` 现在还不应被提升为最小字段集
- 它们只作为 `add_on` 的升级闸门后备层存在

下一步最紧要的问题因此被进一步收窄成：

- 现有 `price_limit_event_limit_proximity` 枚举，是否足以承载 `add_on` 的“近板但未明确阻断”研究语义
- 如果不足，缺的究竟是更细的 `relation fact`，还是确实必须引入 `close/touched`

这也是本清单的最终判断：

- **默认继续：`prefer_planned_event_relation_fact`**
- **唯一升级条件：`add_on` 的关键研究差异无法由现有 relation fact 稳定表达**
