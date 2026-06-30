# Tachibana A股制度研究准备层收口报告 v0.1

> 日期：2026-06-30
> 所属阶段：P3 制度研究准备层收口
> 当前系统位置：`candidate_table_update_audit_package_prepared`

## 1. 目标与边界

本报告收口 `execution_policy_research_agenda` 中的三类制度研究材料：

- `t1`
- `price_limit`
- `suspension_resume`

本报告只做研究准备层整理，不做以下事项：

- 不定义 A 股 T+1、涨跌停、停复牌交易规则。
- 不生成 signal。
- 不生成 `trade_accept`。
- 不定义 `target_position`、`position_size` 或仓位缩放。
- 不执行 backtest。
- 不写 candidate table。
- 不把 `candidate_table_update_audit_result=pass` 解释成真实更新完成。

当前所有硬闸继续保持关闭：

- `qualification_record_write_allowed=False`
- `candidate_table_update_allowed=False`
- `trading_layer_read_allowed=False`
- `institution_rule_definition_allowed=False`
- `signal_generation_allowed=False`
- `backtest_execution_allowed=False`

## 2. 已有材料索引

### 2.1 通用制度参考

- [A股市场交易规则-tushare版.md](../../a-share/reference/A股市场交易规则-tushare版.md)
- [A股涨跌停板制度-tushare版.md](../../a-share/reference/A股涨跌停板制度-tushare版.md)
- [Tachibana-A股适配版-雏形.md](./Tachibana-A股适配版-雏形.md)
- [Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md](./Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md)

### 2.2 price_limit 研究材料

- [Tachibana-A股-price_limit-研究问题拆解清单-v0.1.md](./Tachibana-A股-price_limit-研究问题拆解清单-v0.1.md)
- [Tachibana-A股-price_limit-add_on-三问研究结论-v0.1.md](./Tachibana-A股-price_limit-add_on-三问研究结论-v0.1.md)
- [Tachibana-A股-planned-event-price_limit-关系事实最小草案-v0.1.md](./Tachibana-A股-planned-event-price_limit-关系事实最小草案-v0.1.md)
- [Tachibana-A股-add_on-price_limit-样本池预筛清单-v0.1.md](./Tachibana-A股-add_on-price_limit-样本池预筛清单-v0.1.md)
- [Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md](./Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md)
- [Tachibana-A股-300750.SZ-add_on-price_limit-proximity-evidence-review-v0.1.md](./Tachibana-A股-300750.SZ-add_on-price_limit-proximity-evidence-review-v0.1.md)

### 2.3 suspension_resume 类比材料

- [MALF-立花1976-09制度资料口径审计-v0.1.md](./MALF-立花1976-09制度资料口径审计-v0.1.md)
- [Tachibana-A股制度改造启动闸门-v0.1.md](./Tachibana-A股制度改造启动闸门-v0.1.md)
- [Tachibana-A股首批结构资格样本接入作业单-v0.1.md](./Tachibana-A股首批结构资格样本接入作业单-v0.1.md)

## 3. t1 研究准备收口

### 3.1 已确认事实

A 股交易制度参考材料已明确 T+1 是执行约束，而不是 MALF 结构定义。T+1 的研究准备层应回答：

- 当 Method / PM 计划事件发生后，哪些股份在当日不可卖出。
- 若计划事件需要当日纠错或撤退，T+1 会把风险延后到下一交易日。
- T+1 影响的是执行可行性、持仓风险暴露和计划动作记录，不改变 `rhythm_meaning` 或 `tachibana_applicability`。

### 3.2 当前可承接字段

当前仓库已有执行事实与制度候选层，适合继续承接 T+1 的研究材料：

- `execution_policy_candidates`
- `execution_policy_review`
- `execution_policy_archive`
- `execution_policy_research_prep`

但当前不应新增 `ashare_t1_action` 这类执行动作字段。该字段仍属于禁止字段，不能进入 MALF、资格记录、candidate table audit package 或样本扩充审计。

### 3.3 P5 前置缺口

进入规则定义前，T+1 至少还需要整理以下材料：

- 买入日、可卖日、下一交易日的日历事实口径。
- 计划事件与持仓来源的关系：中心单、追加单、减仓单是否来自不同买入日期。
- 人工 Method / PM 计划中，哪些动作只是观察，哪些动作会受 T+1 影响。

### 3.4 当前收口结论

`t1` 已具备研究准备材料入口，但尚不具备规则定义条件。当前结论是：

`t1_research_status=prepared_for_rule_definition_later`

这不等于规则已经定义，也不等于交易层可以读取。

## 4. price_limit 研究准备收口

### 4.1 已确认事实

当前 price_limit 主线已经形成三条稳定口径：

1. `reviewed relation evidence` 是标准可选输入接口，不是临时笔记。
2. `reviewed relation evidence` 不是所有样本进入研究准备的硬前置。
3. 当前不升级 `close_limit_status / touched_limit_status` 为最小事实集硬要求。

对 `300750.SZ / add_on` 的已审证据支持：

- `price_limit_event_relation_status=relation_constrained`
- `price_limit_event_fill_blocking_status=fill_blocking_unknown`
- `price_limit_event_limit_proximity=not_near_limit`

它不支持：

- `near_limit`
- `at_limit`

### 4.2 当前推荐事实层

当前推荐事实层仍是：

`recommended_fact_layer=prefer_planned_event_relation_fact`

而不是：

`recommended_fact_layer=require_hybrid_fact_set`

也就是说，P5 之前应优先沉淀 planned-event 级 relation fact，而不是提前把所有 close/touched 日级状态升级为规则硬依赖。

### 4.3 P5 前置缺口

进入规则定义前，price_limit 至少还需要：

- 更多真实 `add_on / pullback_add` 样本。
- 至少一批能区分 `not_near_limit / near_limit / at_limit / proximity_unknown` 的 reviewed evidence。
- 明确何时 relation fact 分辨率不足，才允许升级到 hybrid fact set。

### 4.4 当前收口结论

`price_limit` 已完成研究准备层阶段性收口，但尚不具备规则定义条件。当前结论是：

`price_limit_research_status=prepared_with_sample_gap`

这表示材料框架已收口，样本覆盖仍是后续风险。

## 5. suspension_resume 研究准备收口

### 5.1 已确认事实

当前 A 股真实样本链路尚未形成充分的停复牌事件样本，但 1976-09 的资料口径审计提供了一个重要类比：

- 制度或资料口径扰动不能回流改写 MALF 主定义。
- 交易单位变化、除权、停牌、复牌、缺 bar 等事实应留在数据层或制度执行层。
- 当口径扰动强于结构证据时，结构资格应保持 `unknown` 或研究阻断，而不是强行升级。

### 5.2 当前推荐研究口径

`suspension_resume` 当前应作为：

`data_and_execution_continuity_constraint`

它研究的是：

- 连续日线是否被停牌或复牌跳空打断。
- MALF snapshot 的价格路径是否仍可比较。
- Method / PM 计划事件是否需要 carry forward 或重新审计。

它不研究：

- 停牌后应该买入或卖出。
- 复牌涨跌停如何产生信号。
- 停牌是否自动意味着结构失败。

### 5.3 P5 前置缺口

进入规则定义前，suspension_resume 至少还需要：

- 真实 A 股停牌/复牌样本，或可复核的合成最小样本。
- `suspension_flag / missing_bar_flag / trade_calendar` 在 execution fact package 中的稳定引用。
- 复牌后 planned-event 是否续传、重置或阻断的人工 review 口径。

### 5.4 当前收口结论

`suspension_resume` 已具备研究准备边界，但尚不具备规则定义条件。当前结论是：

`suspension_resume_research_status=prepared_as_carry_forward_constraint`

## 6. P3 总收口

P3 的制度研究准备层已经可以收口为以下状态：

| 议题 | 当前状态 | 是否进入规则定义 |
|---|---|---|
| `t1` | `prepared_for_rule_definition_later` | 否 |
| `price_limit` | `prepared_with_sample_gap` | 否 |
| `suspension_resume` | `prepared_as_carry_forward_constraint` | 否 |

总状态：

`execution_policy_research_closure_status=research_materials_closed_for_p3`

这表示：

- 三类制度研究材料已经整理到 P3 收口层。
- 后续可以进入 P4 真实持久化/候选表写入设计，也可以继续补样本。
- P5 制度规则定义仍需等待 P4 与更多样本证据，不应在本报告中启动。

## 7. 后续建议

### 7.1 P4 前建议

- 继续保持 `candidate_table_update_allowed=False`。
- 真实持久化写入必须独立设计入口，不复用 audit package。
- candidate table 写入必须显式调用，不允许由 P3 报告触发。

### 7.2 P5 前建议

- `price_limit` 优先补 `near_limit / at_limit` 样本。
- `t1` 优先整理可卖日与计划事件关系。
- `suspension_resume` 优先补真实停复牌或缺 bar 样本。

### 7.3 持续红线

- 不启用 `--fast-research`。
- 不合并审计步骤。
- 不把 persistence package 称为落库。
- 不把 candidate table update audit 称为真实更新。
- 不开放 trading layer read。
- 不生成 signal 或 backtest。
