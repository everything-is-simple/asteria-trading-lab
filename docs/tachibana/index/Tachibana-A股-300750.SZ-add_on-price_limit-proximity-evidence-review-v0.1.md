# Tachibana A股 300750.SZ add_on price_limit proximity evidence review v0.1

> 评审日期：2026-06-28
> 评审对象：`300750.SZ / add_on`
> 评审目标：基于当前真实证据，判断 `price_limit_event_limit_proximity` 是否仍应保持 `proximity_unknown`，或是否已经足以推进到 `not_near_limit / near_limit / at_limit`

## 1. 评审边界

本表只做一件事：

**把当前真实存在的证据逐条过一遍，并给出 `300750.SZ / add_on` 现在最稳妥的 proximity 判断。**

本表不做以下事情：

- 不把研究草案本身当成一手证据
- 不定义 `limit_up_strategy / limit_down_strategy`
- 不生成 signal
- 不生成 `trade_accept`
- 不把日线 `OHLC` 机械映射成 proximity 结论

## 2. 本次实际核对来源

本次 review 使用了以下真实来源：

- [ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../method-pm-plans/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)
- [ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../execution-feasibility-verdicts/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)
- [ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../execution-policy-reviews/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)
- [300750.SZ.csv](</Z:/asteria-trading-labs-data/ashare/institution-facts-v0.1/300750.SZ.csv>)
- [300750.SZ.csv](</Z:/asteria-trading-labs-data/ashare/daily-window-v0.1/300750.SZ.csv>)
- `Z:\new_tdx64\vipdoc\sz\fzline\sz300750.lc5`
- [Tachibana-A股首批真实样本结构资格判定记录-v0.1.md](</Z:/asteria-trading-lab/docs/tachibana/index/Tachibana-A股首批真实样本结构资格判定记录-v0.1.md>)
- [Tachibana-A股适配版-雏形.md](</Z:/asteria-trading-lab/docs/tachibana/index/Tachibana-A股适配版-雏形.md>)
- 一轮真实命令输出：
  `python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-policy-candidates Z:\asteria-trading-lab\docs\tachibana\execution-feasibility-verdicts\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data`

## 3. 最小 evidence review 表

| evidence_source | is_event_level | supports_not_near_limit | supports_near_limit | supports_at_limit | conflict_or_gap | current_best_proximity |
|---|---|---|---|---|---|---|
| `method-pm-plan: ASHARE-300750.SZ-2026-03-24-2026-04-03.json` | `true` | `false` | `false` | `false` | 明确了 `planned_event=add_on` 与 `method_action=pullback_add`，但没有任何 proximity 关系描述 | `proximity_unknown` |
| `qualification record: Tachibana-A股首批真实样本结构资格判定记录-v0.1.md` | `false` | `false` | `false` | `false` | 只说明 `limited / conditional / pm_required=true`，是结构资格与复杂度判断，不是事件级 price-limit 关系证据 | `proximity_unknown` |
| `institution facts: 300750.SZ.csv` | `false` | `false` | `false` | `false` | 提供了 `limit_up_price / limit_down_price` 与 `is_suspended=false`，但 `close_limit_status=unknown`、`touched_limit_status=unknown`，且没有事件级 proximity 关系 | `proximity_unknown` |
| `daily window: 300750.SZ.csv` | `false` | `false` | `false` | `false` | 提供了事件窗口内的日线 `open/high/low/close`，但没有 planned-event 时点或时段锚点；若直接拿日线 `OHLC` 映射 proximity，会退化成机械日线判断 | `proximity_unknown` |
| `intraday lc5 bars: sz300750.lc5 on 2026-04-03` | `true` | `true` | `false` | `false` | 5 分钟覆盖整日交易；当日最高价 `400.80`，离涨停价 `481.40` 仍差 `80.60`（约 `16.74%`）；当日最低价 `385.13`，离跌停价 `320.94` 仍高 `64.19`（约 `20.00%`）。虽然没有单独记录 planned-event 精确时点，但由于整日范围都远离两侧边界，可作为当前样本的事件日非近板证据 | `not_near_limit` |
| `execution-feasibility verdict: ASHARE-300750.SZ-2026-03-24-2026-04-03.json` | `true` | `false` | `false` | `false` | 明确记录了 `limit_state_unknown_on_planned_event`，说明问题已被识别，但仍未给出近板或到板判断 | `proximity_unknown` |
| `execution-policy review: ASHARE-300750.SZ-2026-03-24-2026-04-03.json` | `true` | `false` | `false` | `false` | 说明 `price_limit` 已可进入研究，但 review 结论没有把 proximity 从 unknown 推进到具体状态 | `proximity_unknown` |
| `real candidate audit run: price_limit candidate for 300750.SZ` | `true` | `false` | `false` | `false` | 机器态已明确输出 `price_limit_event_limit_proximity=proximity_unknown` 与 `planned_event_requires_higher_price_limit_resolution`，证明当前链路仍缺 proximity evidence | `proximity_unknown` |
| `A-share adaptation sketch: pullback_add requires distance check` | `false` | `false` | `false` | `false` | 只提供通用方法边界：`pullback_add` 需要当日涨跌停距离检查；它证明“应该检查”，但不提供 `300750.SZ / add_on` 的事件级结论 | `proximity_unknown` |

## 4. 当前跑表结果

本次实际 review 跑下来，结果已经发生变化：

- 已有一条当前证据可以支持 `not_near_limit`
- 没有一条当前证据可以支持 `near_limit`
- 没有一条当前证据可以支持 `at_limit`
- 当前最稳妥的综合判断已可推进到：
  `current_best_proximity = not_near_limit`

这次额外搜索还有一个明确结果：

- 当前仓库里**没有找到**能直接把 `300750.SZ / add_on` 判成 `near_limit / at_limit` 的现成 event-level proximity evidence
- 但在本地外部数据根中找到了 `Z:\new_tdx64\vipdoc\sz\fzline\sz300750.lc5`，它提供了足以支持 `not_near_limit` 的事件日 intraday evidence

## 5. 当前缺口到底是什么

本次 review 表明，缺口不是：

- 没有 `limit_up_price / limit_down_price`
- 没有 `planned_event`
- 没有进入 research agenda

真正缺的已经从“完全没有 proximity evidence”收窄成：

- **缺少能支持 `near_limit` 或 `at_limit` 的更强 proximity relation evidence**

更具体地说，当前缺少的是以下任一类明确证据：

- 明确说明“planned-event 已接近板边”的事件级关系证据
- 明确说明“planned-event 已到板边”的事件级关系证据

## 6. 当前最稳妥结论

本次 evidence review 的当前最稳妥结论是：

- `300750.SZ / add_on` 现在已经可以推进到 `current_best_proximity = not_near_limit`
- 当前仍然不能支持 `near_limit` 或 `at_limit`
- 当前正确动作是保留这条 `not_near_limit` 证据，并继续寻找是否存在更直接的 planned-event 级 proximity relation note

## 7. 下一步最具体动作

下一步不该做的是直接升级到 `close_limit_status / touched_limit_status`。

下一步最具体该做的是：

1. 把 `lc5` intraday 证据正式视为当前样本的 `not_near_limit` 支撑来源
2. 继续查找 `300750.SZ / add_on` 是否还有更直接的事件级研究记录，能说明“接近板边”或“已到板边”
3. 只有拿到上述任一类更强证据，才重跑这张 review 表，并尝试把 `current_best_proximity` 从 `not_near_limit` 再推进或修正
