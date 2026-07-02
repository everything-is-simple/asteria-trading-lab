# 03_Design — 系统设计文档

**版本**: v0.2  
**日期**: 2026-06-28

## 1. 总体设计

系统采用单向管道设计：

`Data -> MALF/front filter -> Method/PM -> institution feasibility -> execution policy audit`

下游不得反写上游，制度层不得改写结构层。

## 2. 已落地模块

### Data

- `src/data_sources/tdx_local/readers.py`
- `src/data_sources/tdx_local/first_batch.py`
- `src/data_sources/tdx_local/institution_facts.py`
- `src/data_sources/tdx_local/audit.py`

### 立花原始回测

- `src/original_tachibana/pm_state.py`
- `src/original_tachibana/performance.py`
- `src/original_tachibana/major_trades.py`
- `src/original_tachibana/single_trades/`

### MALF 前置接口层

- `src/tachibana_front_filter.py`

### A 股审计总协调器

- `src/ashare_intake_validator.py`

## 3. 当前真实链路状态

已落地并验证通过的链路为：

`readiness -> front_filter_run -> record_drafts -> sample_table_trial -> method_pm_plan_merge -> backtest_input_snapshots -> institution_feasibility_records -> execution_constraint_snapshots -> execution_feasibility_gate -> execution_feasibility_verdicts -> verdict_merge -> execution_feasibility_outcomes -> execution_policy_candidates -> execution_policy_review_merge -> execution_policy_archive -> execution_policy_research_prep -> execution_policy_research_agenda`

当前下一步动作是：

- `action:prepare_execution_policy_research`

## 4. 设计边界

- MALF 只输出结构事实与结构资格
- Method/PM 只解释交易动作与仓位语义
- 制度层只审计执行事实
- Signal / Backtest 仍未开放

三道硬闸当前必须保持：

- `institution_rule_definition_allowed=false`
- `signal_generation_allowed=false`
- `backtest_execution_allowed=false`

## 5. 未落地但已有定义

- MALF 完整 Core/Range/Lifespan/Probability 引擎
- Signal 模块
- A 股适配版完整回测执行层

这些部分当前应明确标记为“定义已存在，代码未实现”。

另需固定当前项目口径：

- `PAS` 虽在历史 Definitive 文档体系中出现，但在本项目当前路线中已明确搁置。
- 因此当前真实主线不再按 `MALF -> PAS -> Signal -> Backtest` 组织施工，而是按本文档上方所列的实际审计链路推进。
