# Tachibana A股 price_limit add_on 三问研究结论 v0.1

> 研究日期：2026-06-29
> 研究范围：围绕 A 股首批真实样本窗口 `2026-03-24` 至 `2026-04-03`，回答当前 `price_limit / add_on` 线最紧要的三个问题

## 1. 目标与边界

本结论只回答以下三个问题：

1. 当前样本面里，除 `300750.SZ / add_on` 之外，是否已经存在可直接支持 `near_limit / at_limit` 的真实证据
2. `reviewed relation evidence` 应该被视为少量样本收口技巧，还是 `price_limit` 研究准备层的标准输入接口
3. `close_limit_status / touched_limit_status` 现在是否已经需要升级进最小事实集

本结论不做以下事情：

- 不定义 `limit_up_strategy / limit_down_strategy`
- 不生成 signal
- 不生成 `trade_accept`
- 不定义仓位、`position_size` 或 backtest
- 不把 `ready_for_research` 解释成执行许可
- 不把单样本结论直接推广成所有未来样本的默认规则

## 2. 当前样本盘面

已核实事实：

- 当前首批真实样本只有 3 条 `tachibana_candidate`：
  - `000001.SZ / open_center`
  - `300750.SZ / add_on`
  - `600000.SH / lock_candidate`
  [Tachibana-A股首批真实样本结构资格判定记录-v0.1.md](./Tachibana-A股首批真实样本结构资格判定记录-v0.1.md)
- 这 3 条样本对应的 Method/PM 计划中，只有 `300750.SZ` 落在：
  - `method_action = pullback_add`
  - `pm_action = add_on`
  - `execution_event_type = add_on`
  [README.md](../method-pm-plans/first-batch-v0.1/README.md)
- 当前仓库里唯一落地的 reviewed price-limit relation evidence 文件，也只对应：
  - `ASHARE-300750.SZ-2026-03-24-2026-04-03`
  [ASHARE-300750.SZ-2026-03-24-2026-04-03.json](../price-limit-event-relations/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json)

研究推断：

- 现阶段并不是“我们已经审过很多 add_on 样本，但都没有 `near_limit / at_limit`”。
- 更准确的现状是：**当前首批真实样本里，只有 1 条真实 `add_on` 样本进入了这条 price-limit 研究线。**

## 3. 问题一：有没有其他 `near_limit / at_limit` 真实证据

### 3.1 当前已核实证据

`300750.SZ / add_on` 当前已经完成的 review 结论是：

- `price_limit_event_relation_status = relation_constrained`
- `price_limit_event_fill_blocking_status = fill_blocking_unknown`
- `price_limit_event_limit_proximity = not_near_limit`

证据来源是事件日 `2026-04-03` 的整日 `lc5` 覆盖：

- 当日最高价 `400.80`
- 涨停价 `481.40`
- 当日最低价 `385.13`
- 跌停价 `320.94`

它支持：

- `not_near_limit`

它不支持：

- `near_limit`
- `at_limit`

见：

- [Tachibana-A股-300750.SZ-add_on-price_limit-proximity-evidence-review-v0.1.md](./Tachibana-A股-300750.SZ-add_on-price_limit-proximity-evidence-review-v0.1.md)
- [Tachibana-A股-300750.SZ-add_on-not_near_limit-收口草案-v0.1.md](./Tachibana-A股-300750.SZ-add_on-not_near_limit-收口草案-v0.1.md)

### 3.2 当前没找到什么

当前仓库、首批数据根与 reviewed relation evidence 目录里，都**没有找到**：

- 第二条真实 `add_on` 样本
- 能直接支持 `near_limit` 的 event-level reviewed evidence
- 能直接支持 `at_limit` 的 event-level reviewed evidence

这意味着：

- 当前不能把“`near_limit / at_limit` 不存在”当作已被充分证伪的研究结论
- 只能把它表述为：**在当前首批真实样本覆盖面内，还没有采到这两类真实证据**

### 3.3 当前结论

对问题一，本轮最稳妥的结论是：

**当前首批真实样本里，还没有找到 `near_limit / at_limit` 的真实 event-level evidence；但原因首先是样本面仍然很窄，而不是已经完成了对多条 `add_on` 样本的反证。**

因此，下一轮样本扩展应优先寻找：

1. 新的 `add_on / pullback_add` 真实样本
2. 已接近涨跌停但未到板的 planned-event
3. 存在显式追加阻断或近阻断描述的 planned-event 记录

## 4. 问题二：`reviewed relation evidence` 是技巧还是标准接口

### 4.1 当前代码与目录事实

已核实事实：

- `ashare_intake_validator.py` 已新增可选参数：
  - `--price-limit-event-relation-dir`
- validator 会读取 `ASharePriceLimitEventRelationEvidence` JSON，并把其作为 optional evidence index 透传到：
  - `execution_constraint_snapshots`
  - `execution_feasibility_gate`
  - `execution_feasibility_verdicts`
  - `execution_feasibility_outcomes`
  - `execution_policy_candidates`
- 若 evidence 枚举非法，audit 会 `blocked`，而不是静默回退

这说明它已经不是“笔记层临时技巧”，而是**受控、可验证、可阻断的正式输入口**。

### 4.2 但它也不该被误读成“所有样本必须先有 relation evidence”

当前同一条链路同时证明了另一件事：

- 即使没有 reviewed relation evidence，`000001.SZ / open_center` 仍可进入 `price_limit -> ready_for_research`
- 即使 `300750.SZ / add_on` 在早先阶段还是 `proximity_unknown`，整条研究准备链路也已允许它先进入 `review_required / ready_for_research`

这说明 `reviewed relation evidence` 的定位应当是：

- **标准输入接口**
- 但不是**研究准备的通用硬前置**

更准确地说，它应该服务于：

- 已经存在人工 review 或研究结论的样本
- 需要把样本级 planned-event relation judgment 显式接回机器态的场景

### 4.3 当前结论

对问题二，本轮结论是：

**`reviewed relation evidence` 应被固定为 `price_limit` 研究准备层的标准可选输入接口，而不是少量样本专用技巧，也不是所有样本必须先补齐的硬门槛。**

推荐口径是：

- `default_mode = relation_fact_minimum_semantics`
- `reviewed_relation_evidence = optional_reviewed_override_input`

它的职责是：

1. 保存已审定的 planned-event relation judgment
2. 保存可追溯 evidence source
3. 让 validator 消费“审定结果”，而不是直接解释原始行情

## 5. 问题三：是否现在升级 `close_limit_status / touched_limit_status`

### 5.1 当前反对立即升级的证据

已核实事实：

- `close_limit_status / touched_limit_status = unknown` 已经不再阻止 `price_limit` 进入 `ready_for_research`
- `300750.SZ / add_on` 已经在不升级 `close/touched` 的前提下，稳定收口到 `not_near_limit`
- 现有 proximity 枚举：
  - `not_near_limit`
  - `near_limit`
  - `at_limit`
  - `proximity_unknown`
  已被现有文档明确判断为足以承载 `add_on` 的研究级分辨率

因此，当前缺口并不是“没有 `close/touched` 就完全无法表达”，而是：

- 当前还缺更多真实 `add_on` 样本
- 当前还缺 `near_limit / at_limit` 的真实 reviewed evidence

### 5.2 合法升级闸门

只有当以下条件在后续样本中反复出现时，才应该升级：

1. `planned-event relation fact` 已经被充分尝试
2. `near_limit / at_limit` 的差异仍无法稳定表达关键研究判断
3. 不引入 `close_limit_status / touched_limit_status` 时，研究者会持续遇到同一种分辨率歧义

也就是说，升级的前提不是“想更细”，而是：

**关系事实层已经不够用了，而且这种不够用在多个后续 `add_on` 样本中重复出现。**

### 5.3 当前结论

对问题三，本轮结论是：

**现在还不应把 `close_limit_status / touched_limit_status` 升级进最小事实集。**

当前推荐仍然是：

- `recommended_fact_layer = prefer_planned_event_relation_fact`

而不是：

- `recommended_fact_layer = require_hybrid_fact_set`

`require_hybrid_fact_set` 目前只能保留为：

- 后续样本扩展中的升级候选
- 而不是当前收口结论

## 6. 三问总收口

本轮三问的总结论如下：

1. **关于 `near_limit / at_limit`：**
   当前还没有找到真实 event-level evidence，但主要因为首批真实 `add_on` 样本仍只有 `300750.SZ` 这一条

2. **关于 `reviewed relation evidence`：**
   它应当成为 `price_limit` 研究准备层的标准可选输入接口，专门承接样本级 reviewed relation judgment

3. **关于 `close_limit_status / touched_limit_status`：**
   现在还不该升级进最小事实集；只有后续多个 `add_on` 样本重复证明 relation fact 分辨率不足时，才触发混合方案

## 7. 下一步

下一步最紧要的动作因此被收窄为：

1. 扩展真实 `add_on / pullback_add` 样本池，优先寻找能支持 `near_limit / at_limit` 的样本
2. 在 `price-limit-event-relations` 目录层固定 reviewed evidence 的接口说明与使用边界
3. 继续保持 `close_limit_status / touched_limit_status` 在后备层，直到重复歧义真正出现
