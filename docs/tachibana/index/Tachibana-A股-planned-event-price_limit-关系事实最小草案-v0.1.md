# Tachibana A股 planned-event price_limit 关系事实最小草案 v0.1

> 研究日期：2026-06-28
> 研究范围：A 股首批真实样本 `2026-03-24` 至 `2026-04-03` 窗口内，`price_limit` 在 `planned-event` 关系层的最小事实表达；仅覆盖 `000001.SZ / open_center` 与 `300750.SZ / add_on`

## 1. 边界与目标

本草案只回答一个问题：在 `limit_up_price / limit_down_price` 已落地、`price_limit` 已推进到 `ready_for_research` 之后，下一轮最小事实补强应如何在 `planned-event` 关系层表达。

本草案是“研究语义 + 最小字段名”文档，不是代码实现，也不是规则定义。它不做以下事情：

- 不定义 `limit_up_strategy / limit_down_strategy`
- 不生成 signal
- 不生成 `trade_accept`
- 不定义仓位动作许可
- 不把 `price_limit_event_relation_*` 解释成成交结论

这里的目标只有两个：

- 用一套统一 schema 表达 `open_center` 与 `add_on` 的事件级 price-limit 关系事实
- 明确什么情况下坚持 `prefer_planned_event_relation_fact`，什么情况下必须升级到 `require_hybrid_fact_set`

这一定位必须继续服从既有仓库边界：制度约束只改变执行可行性，不改变结构资格，不抢占 Signal、Backtest 或规则定义权。[Tachibana-A股制度改造启动闸门-v0.1.md](./Tachibana-A股制度改造启动闸门-v0.1.md)、[Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md](./Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md)

## 2. 现状确认

已核实事实：

- `PR #4` 已完成两类推进：一是 `institution_facts` 侧补上 `limit_up_price / limit_down_price`，二是 `ashare_intake_validator` 侧把 `price_limit` 从“`close_limit_status / touched_limit_status = unknown` 必然阻断”推进到了 planned-event 级最小证据语义。[PR #4](https://github.com/everything-is-simple/asteria-trading-lab/pull/4)
- 当前 research agenda 已明确显示：`price_limit -> ready_for_research`，且样本数为 2。[README.md](../execution-policy-research-agenda/first-batch-v0.1/README.md)
- 当前研究清单已经把缺口收窄成：不是继续补通用边界价格字段，而是继续补“planned-event 当天的关系事实”。[Tachibana-A股-price_limit-研究问题拆解清单-v0.1.md](./Tachibana-A股-price_limit-研究问题拆解清单-v0.1.md)

研究推断：

- 当前缺口已经不再是“有没有 price limit 事实”，而是“planned-event 是否有足够的事件级事实来说明该动作没有被制度显式封死，或已经接近被封死”。
- 因此下一轮最小草案应优先挂在 `execution constraint snapshot -> candidate` 路径的事件关系层，而不是回写 `institution_facts-v0.1` 的主表契约。

未决问题：

- `300750.SZ / add_on` 是否最终会逼出对 `close_limit_status / touched_limit_status` 的升级需求，目前只能先通过关系事实 schema 试探，不能提前下结论。

## 3. 统一 schema 定义

本草案固定未来 `planned-event` 关系事实的最小字段名，不为 `open_center` 与 `add_on` 各自起新字段。

### 3.1 统一字段

| 字段 | 类型 | 取值 / 说明 |
|---|---|---|
| `price_limit_event_relation_status` | enum | `relation_clear / relation_constrained / relation_blocked / relation_unknown` |
| `price_limit_event_fill_blocking_status` | enum | `no_explicit_fill_blocking_fact / explicit_fill_blocking_fact / fill_blocking_unknown / not_applicable` |
| `price_limit_event_limit_proximity` | enum | `not_near_limit / near_limit / at_limit / proximity_unknown / not_applicable` |
| `price_limit_event_relation_reason` | list[str] | 研究理由码列表，不承载规则语义 |
| `price_limit_event_relation_ref` | list[str] | 样本、verdict、review、制度来源引用 |

### 3.2 字段含义

`price_limit_event_relation_status` 负责给出事件层总判断：

- `relation_clear`：当前事件不存在已知的 price-limit 显式阻断
- `relation_constrained`：当前事件不是明确阻断，但已经存在约束或接近约束的研究语义
- `relation_blocked`：当前事件存在显式阻断或显式无法继续执行的事实
- `relation_unknown`：当前事件关系事实仍不足以形成最小研究语义

`price_limit_event_fill_blocking_status` 只回答“有没有显式制度阻断事实”，不回答规则许可：

- `no_explicit_fill_blocking_fact`
- `explicit_fill_blocking_fact`
- `fill_blocking_unknown`
- `not_applicable`

`price_limit_event_limit_proximity` 只回答“事件与涨跌停边界的接近程度是否已知”，不直接等于 `close_limit_status / touched_limit_status`：

- `not_near_limit`
- `near_limit`
- `at_limit`
- `proximity_unknown`
- `not_applicable`

### 3.3 最小理由码

本草案固定以下最小理由码集合，避免后续实现阶段再自由扩散：

- `planned_event_has_no_explicit_price_limit_blocking_fact`
- `planned_event_has_explicit_price_limit_blocking_fact`
- `planned_event_limit_proximity_is_unknown`
- `planned_event_is_near_price_limit_boundary`
- `planned_event_is_at_price_limit_boundary`
- `planned_event_requires_higher_price_limit_resolution`

## 4. 事件语义口径

### 4.1 `open_center`

已核实事实：

- `000001.SZ` 的 `planned_event` 是 `open_center`，Method 动作为 `trend_probe_entry`，且当前 feasibility verdict 已是 `executable`。[ASHARE-000001.SZ-2026-03-24-2026-04-03.json](../method-pm-plans/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json)、[ASHARE-000001.SZ-2026-03-24-2026-04-03.json](../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json)

本草案对 `open_center` 的统一 schema 口径固定为：

- 主要依赖 `price_limit_event_fill_blocking_status`
- `price_limit_event_limit_proximity` 可以是 `not_applicable` 或 `proximity_unknown`
- 只要已经知道“没有显式制度阻断”，就允许 `price_limit_event_relation_status = relation_clear`
- 不先要求 `close_limit_status / touched_limit_status`

研究推断：

- `open_center` 当前需要知道的是“是否允许启动一个中心单候选动作”，而不是“收盘是否封板”。
- 因此它适合用最轻量的关系事实进入研究，而不需要先升级到状态补充层。

### 4.2 `add_on`

已核实事实：

- `300750.SZ` 的 `planned_event` 是 `add_on`，Method 动作为 `pullback_add`，当前 feasibility verdict 是 `constrained`。[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../method-pm-plans/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)、[ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)

本草案对 `add_on` 的统一 schema 口径固定为：

- 必须记录 `price_limit_event_fill_blocking_status`
- 也必须记录 `price_limit_event_limit_proximity`
- 若“是否近板”仍然无法表达，则先标记 `proximity_unknown`
- 仍不直接要求 `close_limit_status / touched_limit_status`

研究推断：

- `add_on` 比 `open_center` 更依赖“接近板边”的关系语义，因为它天然涉及已有仓位背景下的继续追加。
- 但第一步依然应该先试统一 schema，而不是立刻扩成通用状态字段。

## 5. 样本映射示例

### 5.1 `000001.SZ / open_center`

| 字段 | 内容 |
|---|---|
| `price_limit_event_relation_status` | `relation_clear` |
| `price_limit_event_fill_blocking_status` | `no_explicit_fill_blocking_fact` |
| `price_limit_event_limit_proximity` | `not_applicable` |
| `price_limit_event_relation_reason` | `planned_event_has_no_explicit_price_limit_blocking_fact` |
| `price_limit_event_relation_ref` | `ASHARE-CONSTRAINT-000001.SZ-2026-04-03-v0.1`; `../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json`; `../execution-policy-reviews/first-batch-v0.1/ASHARE-000001.SZ-2026-03-24-2026-04-03.json` |

解释：

- 这个样本当前已经满足“有边界、未停牌、无显式 price-limit 阻断”的最小语义。
- 这里不要求先表达“距离板边多近”，所以 `price_limit_event_limit_proximity = not_applicable` 即可。

### 5.2 `300750.SZ / add_on`

| 字段 | 内容 |
|---|---|
| `price_limit_event_relation_status` | `relation_constrained` |
| `price_limit_event_fill_blocking_status` | `fill_blocking_unknown` |
| `price_limit_event_limit_proximity` | `proximity_unknown` |
| `price_limit_event_relation_reason` | `planned_event_limit_proximity_is_unknown`; `planned_event_requires_higher_price_limit_resolution` |
| `price_limit_event_relation_ref` | `ASHARE-CONSTRAINT-300750.SZ-2026-04-03-v0.1`; `../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json`; `../execution-policy-reviews/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json` |

解释：

- 这个样本当前还不能被判成 `relation_clear`，因为 `add_on` 至少需要表达“是否近板”与“是否存在显式追加阻断”。
- 但它也还不应该直接升级成必须补 `close/touched` 的通用状态扩张。
- 因此在统一 schema 里，先用 `relation_constrained + proximity_unknown` 表达“研究已开始，但分辨率仍不足”。

## 6. 升级条件

当前总判断固定为：**优先坚持 `prefer_planned_event_relation_fact`。**

已核实事实：

- 当前两个样本已经证明，`close_limit_status / touched_limit_status = unknown` 并不会自动阻止 `price_limit` 进入 `ready_for_research`。[README.md](../execution-policy-research-agenda/first-batch-v0.1/README.md)
- 当前仓库边界明确要求：制度层应先表达执行可行性与研究语义，不应先抢成规则字段扩张。[Tachibana-A股制度改造启动闸门-v0.1.md](./Tachibana-A股制度改造启动闸门-v0.1.md)

研究推断：

- 只要统一 schema 还能表达 `open_center` 与 `add_on` 的事件差异，就应该继续优先走关系事实层。
- `close_limit_status / touched_limit_status` 只应作为升级条件出现，而不应先回到“最小字段集”里。

唯一升级闸门固定为：

- **若 `add_on` 在持续样本中反复出现“必须知道更高 price-limit 状态分辨率，才能表达近板但未明确阻断”的情况，则从 `prefer_planned_event_relation_fact` 升级到 `require_hybrid_fact_set`。**

这意味着：

- `open_center` 默认继续停留在统一关系事实 schema
- `add_on` 先用统一 schema 表达
- 只有当 `add_on` 的“近板但未明确阻断”语义持续无法表达时，才升级到混合方案，引入 `close_limit_status / touched_limit_status` 作为补充层，而不是主字段层

## 7. 最小挂接原则

本轮不改代码，但未来若要实现，这组字段的挂接原则必须保持固定：

- 它属于 `execution constraint snapshot -> candidate` 路径的事件关系层
- 它不属于 MALF、Method、PM、signal、backtest 层
- 它不回写 `institution_facts-v0.1` CSV 表头
- 它优先挂在现有 `price_limit_event_evidence_*` 附近，而不是另起一套独立制度主表

最终结论：

- 当前优先级仍是 `prefer_planned_event_relation_fact`
- `open_center` 与 `add_on` 都必须先尝试被同一组字段完整表达
- `add_on` 是唯一允许触发 `require_hybrid_fact_set` 的当前高风险事件类型
