# Tachibana A股 price_limit 研究问题拆解清单 v0.1

> 研究日期：2026-06-28
> 研究范围：A 股首批真实样本 `2026-03-24` 至 `2026-04-03` 窗口内的 `price_limit` 研究准备语义；仅覆盖 `000001.SZ / open_center` 与 `300750.SZ / add_on`

## 1. 研究边界

本清单只回答一个问题：当前 `price_limit` 议题下一轮应该优先补哪类事实，才能继续推进制度研究。

本清单不做以下事情：

- 不定义 `limit_up_strategy / limit_down_strategy`
- 不生成 signal
- 不生成 `trade_accept`
- 不定义仓位或 `position_size`
- 不把 `ready_for_research` 解释成规则已转正

这里的 `ready_for_research` 只表示：样本已经具备进入人工制度研究准备的最小证据语义，后续可以围绕执行约束继续调查，但仍然处在“执行后置、规则后置”的边界内。这个边界已经被仓库内多份文档反复固定，例如 [Tachibana-A股制度改造启动闸门-v0.1.md](./Tachibana-A股制度改造启动闸门-v0.1.md)、[Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md](./Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md) 与 [Tachibana-分层边界审计-v0.1.md](./Tachibana-分层边界审计-v0.1.md)。

## 2. 时间锚点

本轮样本的事件窗口固定为 `2026-03-24` 到 `2026-04-03`，因此制度口径必须先按样本期解释，不能把后续新规直接反投到样本上。

已核实事实：

- 上交所与深交所普通风险警示股票涨跌幅限制调整，是 `2025-06-27` 发布公开征求意见，并在 `2026-07-06` 起生效；它属于样本期之后的制度变化，应作为“后续制度背景”单独备注，而不是样本期的直接事实来源。[上交所公告](https://www.sse.com.cn/disclosure/announcement/general/c/c_20250627_10783197.shtml)、[深交所公告](https://www.szse.cn/lawrules/publicadvice/t20250627_614642.html)
- 创业板涨跌幅限制的制度锚点应继续按创业板特别规定理解，样本 `300750.SZ` 属于创业板样本。[深交所创业板交易特别规定](https://docs.static.szse.cn/www/disclosure/notice/general/W020200612831351578076.pdf)
- 本轮 `000001.SZ` 与 `300750.SZ` 的制度事实导出已经在本地链路中形成非空 `limit_up_price / limit_down_price`，并进入 [docs/daily-status/2026-06-28.md](../daily-status/2026-06-28.md) 所记录的 `ready_for_research` 状态。

研究推断：

- 对当前问题而言，样本期最重要的不是“制度百分比本身是否能背出来”，而是“planned-event 当天是否已经有足够事实表明该事件可被研究，而不需要先跨进规则定义层”。

未决问题：

- 若后续把 `price_limit` 研究扩到主板风险警示样本，需要重新区分样本发生时点与 `2026-07-06` 生效后的制度口径，不能继续沿用本清单的简单时间边界。

## 3. 研究问题拆解

本轮把 `price_limit` 拆成三层，不再把所有缺口都堆到 `close_limit_status / touched_limit_status` 上。

### 3.1 通用事实层

当前已经具备或已明确缺失语义的字段包括：

- `limit_up_price / limit_down_price`
- `is_suspended`
- `planned_event`
- `method_action`
- `pm_action`
- `close_limit_status`
- `touched_limit_status`

其中前五类已经足以说明“样本存在计划事件、存在价格边界、且没有停牌硬阻断”；后两类当前允许为 `unknown`，且现有代码已经不再把它们直接当作研究入口的绝对门槛。

### 3.2 事件关系层

这一层问的不是“当天收盘是不是封板”，而是：

- planned-event 是否需要知道“距离涨跌停有多近”
- planned-event 是否需要知道“是否存在显式封死、无法成交、无法追加”的制度性事实
- planned-event 是否只需要一个更轻量的“事件日无显式制度阻断”结论

这是当前最接近真实缺口的一层，因为 `open_center` 与 `add_on` 对执行约束的敏感度本来就不同。

### 3.3 状态补充层

`close_limit_status / touched_limit_status` 的价值在于补充“当日价格状态”。

但它们是否必须先补，取决于一个更基础的问题：没有这些状态字段时，我们是否已经能用更轻量的 planned-event 关系事实表达“事件日没有被制度事实显式封死”。

如果答案是可以，那么 `close/touched` 更适合留在第二优先级；如果答案是不可以，才应升级成优先补的通用状态字段。

## 4. 两类事件的最小证据定义

### 4.1 `open_center`

已核实事实：

- `000001.SZ` 的 Method/PM 计划把事件类型定义为 `open_center`，方法动作是 `trend_probe_entry`，`pm_required=false`。[ASHARE-000001.SZ-2026-03-24-2026-04-03.json](../method-pm-plans/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json)
- 当前 execution feasibility verdict 已给出 `executable`，原因包括：`tradable_and_unsuspended_on_planned_event` 与 `no_known_institution_fact_blocks_open_center_replay`。[ASHARE-000001.SZ-2026-03-24-2026-04-03.json](../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json)

研究推断：

- `open_center` 当前更像“是否允许启动一个中心单候选动作”的研究问题。
- 对这类事件，最小制度证据优先关注“是否存在显式制度阻断”，而不是先要求知道“收盘是否封板”。
- 换句话说，只要存在价格边界、未停牌、且没有显式“无法成交/无法发起”的制度事实，就足以进入研究准备。

未决问题：

- 未来如果 `open_center` 研究需要落到具体成交方式、执行窗口或首笔进入尺度，可能还会需要更细的 price-limit 距离信息；但那已经更接近事件关系事实，而不是通用 `close/touched` 状态。

### 4.2 `add_on`

已核实事实：

- `300750.SZ` 的 Method/PM 计划把事件类型定义为 `add_on`，方法动作是 `pullback_add`，且 `pm_required=true`。[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../method-pm-plans/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)
- 当前 execution feasibility verdict 为 `constrained`，原因包含 `add_on_event_requires_pm_scale_and_pressure_review`，blocked reason 还保留了 `limit_state_unknown_on_planned_event`。[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)
- 尽管如此，candidate review / research agenda 已经把该样本的 `price_limit` 推进到 `review_required -> ready_for_research`。[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../execution-policy-reviews/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)、[first-batch-v0.1/README.md](../execution-policy-research-agenda/first-batch-v0.1/README.md)

研究推断：

- `add_on` 明显比 `open_center` 更依赖“事件当天的价格关系语义”，因为它天然涉及在已有节奏与已有仓位背景上继续追加。
- 但即便如此，本轮还不需要立刻把问题定义成“必须先补 `close_limit_status / touched_limit_status`”。
- 更贴近当前缺口的问法是：是否需要一个 planned-event 级的显式关系事实，来说明“这次 add_on 是否遇到封板、接近板边、或存在追加失败的显式制度性约束”。

未决问题：

- 如果后续发现 `add_on` 对“是否触板”高度敏感，且该敏感性不能用轻量的 planned-event 关系事实表达，那么它会成为最可能推动 `require_hybrid_fact_set` 的事件类型。

## 5. 样本级证据矩阵

### 5.1 `000001.SZ / open_center`

| 字段 | 内容 |
|---|---|
| `ashare_sample_id` | `ASHARE-000001.SZ-2026-03-24-2026-04-03` |
| `planned_event` | `open_center` |
| `method_action` | `trend_probe_entry` |
| `pm_action` | `null` |
| `current_limit_bounds_ready` | `true` |
| `current_suspension_fact_ready` | `true` |
| `current_close_limit_status` | `unknown` |
| `current_touched_limit_status` | `unknown` |
| `event_needs_explicit_fill_blocking_fact` | `true` |
| `event_needs_close_limit_status` | `false` |
| `event_needs_touched_limit_status` | `false` |
| `current_minimum_research_semantics_ready` | `true` |
| `next_missing_fact` | `planned_event 是否存在显式封板/无法发起中心单的事件关系事实` |
| `recommended_fact_layer` | `prefer_planned_event_relation_fact` |
| `evidence_ref` | `ASHARE-CONSTRAINT-000001.SZ-2026-04-03-v0.1`; `../method-pm-plans/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json`; `../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json`; `../execution-policy-reviews/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json` |

结论：

- `000001.SZ / open_center` 当前已经说明：价格边界存在、停牌硬阻断不存在、研究入口已打开。
- 对这个样本来说，`close_limit_status / touched_limit_status` 不是当前最短缺口。
- 下一轮最该补的是一个更贴事件的问题：**如果 `open_center` 遇到板边/封板，系统需要记录什么显式“事件阻断事实”。**

### 5.2 `300750.SZ / add_on`

| 字段 | 内容 |
|---|---|
| `ashare_sample_id` | `ASHARE-300750.SZ-2026-03-24-2026-04-03` |
| `planned_event` | `add_on` |
| `method_action` | `pullback_add` |
| `pm_action` | `add_on` |
| `current_limit_bounds_ready` | `true` |
| `current_suspension_fact_ready` | `true` |
| `current_close_limit_status` | `unknown` |
| `current_touched_limit_status` | `unknown` |
| `event_needs_explicit_fill_blocking_fact` | `true` |
| `event_needs_close_limit_status` | `conditional` |
| `event_needs_touched_limit_status` | `conditional` |
| `current_minimum_research_semantics_ready` | `true` |
| `next_missing_fact` | `planned_event 是否接近涨跌停边界、是否存在显式追加失败或无法继续加码的事件关系事实` |
| `recommended_fact_layer` | `prefer_planned_event_relation_fact` |
| `evidence_ref` | `ASHARE-CONSTRAINT-300750.SZ-2026-04-03-v0.1`; `../method-pm-plans/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json`; `../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json`; `../execution-policy-reviews/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json` |

结论：

- `300750.SZ / add_on` 已经证明：仅靠“有边界、未停牌”就能进入研究准备，但还不足以回答“追加动作是否受板边关系影响”。
- 对这个样本，planned-event 关系事实仍然是第一缺口；只是它比 `open_center` 更有可能在后续逼出 `close/touched` 的补充需求。
- 因此当前推荐仍然是 `prefer_planned_event_relation_fact`：先补事件关系事实，再观察后续样本是否真的重复证明必须升级到 `close/touched` 支撑。

## 6. 三路方案对比矩阵

| 路线 | 是否符合“执行后置、规则后置”边界 | 是否直接服务 `open_center` | 是否直接服务 `add_on` | 是否需要新增通用 CSV 契约 | 是否容易误滑向规则定义 | 是否能复用到 `reduce / clear / rebalance` | 当前判断 |
|---|---|---|---|---|---|---|---|
| `补 close_limit_status / touched_limit_status` | 中 | 弱 | 中 | 高 | 中高 | 中 | 不作为第一优先 |
| `补 planned-event 关系事实` | 高 | 高 | 高 | 低到中 | 低 | 高 | 第一优先 |
| `混合方案` | 中高 | 中 | 高 | 中 | 中 | 高 | 作为第二优先候选 |

已核实事实：

- 当前代码和文档已经允许 `close_limit_status / touched_limit_status = unknown` 的情况下进入 `ready_for_research`，说明这两个字段不再是研究入口硬闸。[docs/daily-status/2026-06-28.md](../daily-status/2026-06-28.md)、[README.md](../execution-policy-research-agenda/first-batch-v0.1/README.md)
- 仓库既有边界明确要求：制度约束只改变执行可行性，不得反向定义结构资格或抢跑成正式规则。[Tachibana-A股制度改造启动闸门-v0.1.md](./Tachibana-A股制度改造启动闸门-v0.1.md)、[Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md](./Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md)

研究推断：

- 单独补 `close/touched` 的问题在于，它更像“日线状态补丁”，不一定直接回答 planned-event 是否被制度阻断。
- planned-event 关系事实更贴近当前研究问题，也更容易复用到未来的 `reduce / clear / rebalance`，因为这些事件共享的是“计划动作与制度阻断关系”，而不是统一共享某个收盘状态。
- `add_on` 这类高敏感动作可能最终仍需混合方案，但不应该在第一步就把整条线拖回通用状态字段扩张。

## 7. 总判断

本轮总判断如下：

- `000001.SZ / open_center`：`prefer_planned_event_relation_fact`
- `300750.SZ / add_on`：`prefer_planned_event_relation_fact`
- 当前总议题的下一轮事实补强优先级：`prefer_planned_event_relation_fact`

原因是：

1. 它最符合当前仓库已经建立的“执行后置、规则后置”边界。
2. 它最贴近现有缺口的真实形状，也就是“planned-event 当天是否存在显式制度阻断或接近阻断的关系事实”。
3. 它能先服务 `open_center`，并继续在后续 `add_on` 样本中验证是否真的需要升级到混合方案。

因此，下一轮最紧要的工作不应是先把 `close_limit_status / touched_limit_status` 做成新的通用硬字段，而应先把以下研究问题写清：

- 对 `open_center`，什么样的事件关系事实足以表达“没有显式 price-limit 阻断”
- 对 `add_on`，什么样的事件关系事实足以表达“追加动作仍可研究”，以及在哪些情况下必须升级到 `close/touched`

这也是当前最稳妥的事实补强顺序：**先 planned-event 关系事实，后 `close/touched` 状态补充；若 `add_on` 类事件持续显示关系事实不足，再升级为混合方案。**
